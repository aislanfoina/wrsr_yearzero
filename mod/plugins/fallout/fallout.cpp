// fallout - contamination instead of crime.
//
// THE DESIGN
//
// The vanilla "Crime & Justice" chain (crime level per citizen -> case at the
// home -> police car comes and investigates -> court verdict -> prison term,
// escapes, prison work) is left running untouched. What this plugin changes is
// WHERE the crime level comes from: not from unmet needs but from radiation.
//
//   zones     Three ground zeros (the Korea Year Zero craters) carry a
//             radiation field that falls off with distance, decays with a long
//             half-life, and shrinks as the ruin pieces inside the zone are
//             demolished (cleanup = mining the ruins).
//   hot       Any building that stores waste near a crater radiates a halo
//   salvage   proportional to the tonnage (dumps, the crusher yard).
//   dose      Every citizen standing in a building inside the field gains dose;
//             dose IS the vanilla crime level (person+0x10C), so the police,
//             court and prison machinery treats the citizen as a case of the
//             matching class. Far from the zones the level decays back to zero.
//   acute     Above the acute threshold the citizen's health drops as well, so
//             untreated serious cases fall into the vanilla sickness chain.
//   arrivals  A newcomer first seen at a customs house gets a random dose: the
//             wastes are hot too.
//
// The field is also written into the game's own air-pollution grid (column 0,
// radioactivity), so living buildings show it in their radiation readout and
// the vanilla effects of radioactivity apply.
//
// ESTABLISHED FACTS THIS RELIES ON (SOVIET64.exe 1.1.1.9)
//
//   0x139A70  TickAllBuildings(game). Once per simulation tick; walks
//             game+0x11B08 (vector<Building*>) and dispatches the per-type ticks.
//   game+0x126A8  vector<Person*> (the scripting VM's Person.GetDataByIndex).
//   game+0x120A8  pollution cells, 12 bytes each: float radioactivity, float
//             air pollution, 4 bytes bookkeeping. Cell = 200 m, x-major:
//             index = xi*height + zi with xi = (x + sizeX/2)/200 (0x4D57A0 /
//             0x4D5C30). +0x120B0/+0x120B4 terrain size, +0x120B8 width,
//             +0x120BC height, +0x120C0 count, game+0x5D4 pollution enabled.
//             Radioactivity decays 0.005 per pollution update (0x4D5F50), which
//             also samples it into living buildings' +0x11B4.
//   building+0x318 typedesc; typedesc+0x00 ident string, +0x360 type.
//   building+0x320 C3D_NODE (world position via the engine's GetPosition).
//   building+0x970 vector<Storage>, stride 0xE0; slots of 16 { Resource*,
//             float content, float limit }; resource+0x00 name.
//   person+0x58 building the person is in (NULL in transit), +0x5A0 C3D_NODE,
//   person+0xD8.. status floats: +0xE0 health, +0x10C crime (VM accessor 30000).

#include "../../../vendor/TesmioLoader/src/tesmio_api.h"

#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

static const TsmHost* H;

// ---------------------------------------------------------------- tuning ----

struct Zone { float x, z, inner, scorch, ash; };
static Zone kZones[] = {
    { -3709.0f, -3717.0f, 120.0f, 480.0f, 1150.0f },   // the capital
    {  3940.0f,   758.0f,  75.0f, 380.0f,  900.0f },   // east port town
    {  2400.0f, -5207.0f,  65.0f, 330.0f,  800.0f },   // north gate town
};
static const int kZoneN = 3;

static const float PEAK        = 1.5f;     // radioactivity at ground zero (vanilla clamps building readings at 3)
static const float HALF_LIFE_TICKS = 2.4e6f; // zone half-life in simulation ticks (about eight years at ~300 ticks/day)
static const float CLEANUP_FLOOR = 0.25f;  // a fully demolished zone keeps this share of its field
static const float HOT_RADIUS  = 500.0f;   // waste stored this close to a crater is hot
static const float HOT_TONS    = 150.0f;   // tonnage that makes a full-strength hotspot
static const float HOT_HALO    = 160.0f;   // hotspot fall-off distance
static const float DOSE_PER_TICK    = 0.00045f; // crime level gained per tick at field 1.0
static const float RECOVER_PER_TICK = 0.00012f; // crime level lost per tick with no exposure
static const float ACUTE       = 0.85f;    // above this the citizen's health erodes
static const float ACUTE_HEALTH_PER_TICK = 0.0004f;
static const float ARRIVAL_CHANCE = 0.15f; // newcomers at a customs house that arrive contaminated
static const int   REFRESH_TICKS = 40;     // recompute every N ticks

// --------------------------------------------------------------- offsets ----

#define CTX_BUILDINGS   0x11B08
#define CTX_PERSONS     0x126A8
#define CTX_POLL_CELLS  0x120A8
#define CTX_POLL_SIZEX  0x120B0
#define CTX_POLL_SIZEZ  0x120B4
#define CTX_POLL_W      0x120B8
#define CTX_POLL_H      0x120BC
#define CTX_POLL_N      0x120C0
#define CTX_POLL_ON     0x5D4
#define BLD_TYPEDESC    0x318
#define BLD_NODE        0x320
#define BLD_STORAGES    0x970
#define BLD_RADIO       0x11B4
#define TD_TYPE         0x360
#define STORAGE_STRIDE  0xE0
#define SLOT_STRIDE     16
#define PER_BUILDING    0x58
#define PER_NODE        0x5A0
#define PER_HEALTH      0xE0
#define PER_CRIME       0x10C
#define TYPE_CUSTOMS    20
#define RVA_TICK_ALL    0x139A70

typedef void (*TickAllFn)(void* ctx);
typedef float* (*GetPositionFn)(void* node, float* out);

static TickAllFn     g_origTick;
static GetPositionFn g_getPos;

// ---------------------------------------------------------------- state -----

#define MAX_HOT   64
#define MAX_BLD   4096
#define MAX_SEEN  16384

struct Hot { float x, z, amount; };
static Hot   g_hot[MAX_HOT];
static int   g_nhot;
static int   g_ruinsInitial[3], g_ruinsLive[3];
static float g_zoneStrength[3];
static unsigned g_ticks;
static int   g_refreshAt;
static ULONGLONG g_logAt;
static void* g_seen[MAX_SEEN];
static int   g_nseen, g_seenWrap;
static int   g_dosed, g_arrivalsHot, g_mild, g_medium, g_serious;

struct BldField { void* b; float x, z, f; };
static BldField g_bf[MAX_BLD];
static int g_nbf;

// -------------------------------------------------------------- helpers -----

static void LogLine(const char* fmt, ...)
{
    char buf[512];
    va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof buf, fmt, ap); va_end(ap);
    H->log("%s", buf);
}

static int Readable(const void* p, size_t n) { return p && H->readablePtr(p, n); }

static int LooksLikePointer(const void* p)
{
    ULONG_PTR v = (ULONG_PTR)p;
    if (v < 0x10000 || v > 0x00007FFFFFFFFFFFull || (v & 7)) return 0;
    return H->readablePtr(p, 16);
}

static const char* CString(const void* p, int max)
{
    if (!Readable(p, max)) return NULL;
    const char* s = (const char*)p;
    int i = 0;
    for (; i < max; ++i)
    {
        char c = s[i];
        if (c == 0) break;
        if (c < 0x20 || c > 0x7E) return NULL;
    }
    return (i >= 2 && i < max) ? s : NULL;
}

static unsigned char* Typedesc(unsigned char* b)
{
    if (!Readable(b + BLD_TYPEDESC, 8)) return NULL;
    unsigned char* t = *(unsigned char**)(b + BLD_TYPEDESC);
    return LooksLikePointer(t) ? t : NULL;
}

static int BuildingType(unsigned char* b)
{
    unsigned char* t = Typedesc(b);
    if (!t || !Readable(t + TD_TYPE, 4)) return -1;
    return *(int*)(t + TD_TYPE);
}

static int NodePosition(unsigned char* node, float* xz)
{
    if (!g_getPos || !Readable(node, 0x100)) return 0;
    float out[4] = { 0, 0, 0, 0 };
    float* r = g_getPos(node, out);
    if (!r) return 0;
    xz[0] = r[0]; xz[1] = r[2];
    return 1;
}

// The radiation field at a point: crater zones plus hot-salvage halos.
static float Field(float x, float z)
{
    float f = 0.0f;
    for (int i = 0; i < kZoneN; ++i)
    {
        float dx = x - kZones[i].x, dz = z - kZones[i].z;
        float d2 = dx * dx + dz * dz;
        float s = kZones[i].scorch * 0.7f;
        float v = PEAK * g_zoneStrength[i] * expf(-d2 / (s * s));
        if (v > f) f = v;
    }
    for (int i = 0; i < g_nhot; ++i)
    {
        float dx = x - g_hot[i].x, dz = z - g_hot[i].z;
        float d2 = dx * dx + dz * dz;
        float v = g_hot[i].amount * expf(-d2 / (HOT_HALO * HOT_HALO));
        if (v > f) f = v;
    }
    return f;
}

// ---------------------------------------------------------------- refresh ---

static void ScanBuildings(unsigned char* ctx)
{
    g_nbf = 0; g_nhot = 0;
    int live[3] = { 0, 0, 0 };
    if (!Readable(ctx + CTX_BUILDINGS, 16)) return;
    unsigned char** begin = *(unsigned char***)(ctx + CTX_BUILDINGS);
    unsigned char** end   = *(unsigned char***)(ctx + CTX_BUILDINGS + 8);
    if (!LooksLikePointer(begin) || end < begin) return;
    SIZE_T n = (SIZE_T)(end - begin);
    if (n > MAX_BLD) n = MAX_BLD;
    for (SIZE_T i = 0; i < n; ++i)
    {
        if (!Readable(begin + i, 8)) break;
        unsigned char* b = begin[i];
        if (!LooksLikePointer(b)) continue;
        float xz[2];
        if (!NodePosition(b + BLD_NODE, xz)) continue;
        unsigned char* td = Typedesc(b);
        const char* ident = td ? CString(td, 0x40) : NULL;
        // workshop types are registered as "<item id>/<object>": match on the object part
        if (ident) { const char* slash = strrchr(ident, '/'); if (slash) ident = slash + 1; }
        // ruins left standing in each zone drive the cleanup factor
        if (ident && ident[0] == 'm' && ident[1] == 'm' && ident[2] == '_')
            for (int k = 0; k < kZoneN; ++k)
            {
                float dx = xz[0] - kZones[k].x, dz = xz[1] - kZones[k].z;
                if (dx * dx + dz * dz <= kZones[k].scorch * kZones[k].scorch) ++live[k];
            }
        // hot salvage: waste stored near a crater
        float nearest = 1e9f;
        for (int k = 0; k < kZoneN; ++k)
        {
            float dx = xz[0] - kZones[k].x, dz = xz[1] - kZones[k].z;
            float d = sqrtf(dx * dx + dz * dz);
            if (d < nearest) nearest = d;
        }
        if (nearest <= HOT_RADIUS && g_nhot < MAX_HOT && Readable(b + BLD_STORAGES, 16))
        {
            unsigned char* sb0 = *(unsigned char**)(b + BLD_STORAGES);
            unsigned char* se0 = *(unsigned char**)(b + BLD_STORAGES + 8);
            float tons = 0.0f;
            if (LooksLikePointer(sb0) && se0 >= sb0 && (SIZE_T)(se0 - sb0) <= 32 * STORAGE_STRIDE)
            {
                int recs = (int)((SIZE_T)(se0 - sb0) / STORAGE_STRIDE);
                for (int r = 0; r < recs; ++r)
                {
                    unsigned char* rec = sb0 + (SIZE_T)r * STORAGE_STRIDE;
                    if (!Readable(rec, STORAGE_STRIDE)) continue;
                    unsigned char* sb = *(unsigned char**)(rec + 0x00);
                    unsigned char* se = *(unsigned char**)(rec + 0x08);
                    if (!LooksLikePointer(sb) || se < sb || (SIZE_T)(se - sb) > 0x800) continue;
                    int slots = (int)((SIZE_T)(se - sb) / SLOT_STRIDE);
                    for (int j = 0; j < slots; ++j)
                    {
                        unsigned char* sl = sb + (SIZE_T)j * SLOT_STRIDE;
                        if (!Readable(sl, SLOT_STRIDE)) continue;
                        const char* nm = CString(*(void**)sl, 32);
                        if (nm && strncmp(nm, "waste", 5) == 0)
                        {
                            float c = *(float*)(sl + 8);
                            if (c > 0 && c < 1e6f) tons += c;
                        }
                    }
                }
            }
            if (tons > 1.0f)
            {
                Hot* h = &g_hot[g_nhot++];
                h->x = xz[0]; h->z = xz[1];
                h->amount = PEAK * 0.6f * (tons >= HOT_TONS ? 1.0f : tons / HOT_TONS);
            }
        }
        BldField* bf = &g_bf[g_nbf++];
        bf->b = b; bf->x = xz[0]; bf->z = xz[1]; bf->f = 0.0f;
    }
    for (int k = 0; k < kZoneN; ++k)
    {
        g_ruinsLive[k] = live[k];
        if (g_ruinsInitial[k] < live[k]) g_ruinsInitial[k] = live[k];
    }
    // now the field per building (needs the hotspots)
    for (int i = 0; i < g_nbf; ++i) g_bf[i].f = Field(g_bf[i].x, g_bf[i].z);
}

static float BuildingField(void* b)
{
    for (int i = 0; i < g_nbf; ++i)
        if (g_bf[i].b == b) return g_bf[i].f;
    return 0.0f;
}

static void UpdateZones(void)
{
    float decay = powf(0.5f, (float)g_ticks / HALF_LIFE_TICKS);
    for (int k = 0; k < kZoneN; ++k)
    {
        float cleanup = 1.0f;
        if (g_ruinsInitial[k] > 0)
            cleanup = CLEANUP_FLOOR + (1.0f - CLEANUP_FLOOR) * (float)g_ruinsLive[k] / (float)g_ruinsInitial[k];
        g_zoneStrength[k] = decay * cleanup;
    }
}

static void WriteGrid(unsigned char* ctx)
{
    if (!Readable(ctx + CTX_POLL_ON, 4) || *(int*)(ctx + CTX_POLL_ON) == 0) return;
    if (!Readable(ctx + CTX_POLL_CELLS, 8) || !Readable(ctx + CTX_POLL_SIZEX, 0x14)) return;
    float* cells = *(float**)(ctx + CTX_POLL_CELLS);
    int w = *(int*)(ctx + CTX_POLL_W), h = *(int*)(ctx + CTX_POLL_H), n = *(int*)(ctx + CTX_POLL_N);
    float sx = *(float*)(ctx + CTX_POLL_SIZEX), sz = *(float*)(ctx + CTX_POLL_SIZEZ);
    if (!LooksLikePointer(cells) || w <= 0 || h <= 0 || n != w * h || n > 1000000) return;
    if (!Readable(cells, (size_t)n * 12)) return;
    float cell = sx / (float)w;
    for (int xi = 0; xi < w; ++xi)
        for (int zi = 0; zi < h; ++zi)
        {
            float x = -sx * 0.5f + (xi + 0.5f) * cell;
            float z = -sz * 0.5f + (zi + 0.5f) * cell;
            float f = Field(x, z);
            if (f < 0.01f) continue;
            float* c = cells + (SIZE_T)(xi * h + zi) * 3;
            if (c[0] < f) c[0] = f;
        }
}

static int Seen(void* p)
{
    for (int i = 0; i < g_nseen; ++i) if (g_seen[i] == p) return 1;
    if (g_nseen < MAX_SEEN) g_seen[g_nseen++] = p;
    else { g_seen[g_seenWrap] = p; g_seenWrap = (g_seenWrap + 1) % MAX_SEEN; }
    return 0;
}

static void DosePersons(unsigned char* ctx, int dt)
{
    if (!Readable(ctx + CTX_PERSONS, 16)) return;
    unsigned char** begin = *(unsigned char***)(ctx + CTX_PERSONS);
    unsigned char** end   = *(unsigned char***)(ctx + CTX_PERSONS + 8);
    if (!LooksLikePointer(begin) || end < begin) return;
    SIZE_T n = (SIZE_T)(end - begin);
    if (n > 200000) return;
    int dosed = 0, mild = 0, medium = 0, serious = 0;
    for (SIZE_T i = 0; i < n; ++i)
    {
        if (!Readable(begin + i, 8)) break;
        unsigned char* p = begin[i];
        if (!LooksLikePointer(p) || !Readable(p + PER_CRIME, 4) || !Readable(p + PER_BUILDING, 8)) continue;
        float* crime = (float*)(p + PER_CRIME);
        if (!(*crime >= 0.0f && *crime <= 1.0f)) continue;   // NaN or not a citizen record
        unsigned char* b = *(unsigned char**)(p + PER_BUILDING);
        float f = 0.0f;
        if (LooksLikePointer(b))
        {
            f = BuildingField(b);
            // newcomers: first seen at a customs house
            if (!Seen(p) && BuildingType(b) == TYPE_CUSTOMS && (rand() % 1000) < (int)(ARRIVAL_CHANCE * 1000))
            {
                *crime = 0.35f + 0.4f * (rand() % 1000) / 1000.0f;
                ++g_arrivalsHot;
            }
        }
        else Seen(p);
        if (f > 0.02f) { *crime += f * DOSE_PER_TICK * dt; ++dosed; }
        else           { *crime -= RECOVER_PER_TICK * dt; }
        if (*crime < 0.0f) *crime = 0.0f;
        if (*crime > 1.0f) *crime = 1.0f;
        if (*crime >= ACUTE && Readable(p + PER_HEALTH, 4))
        {
            float* hp = (float*)(p + PER_HEALTH);
            if (*hp > 0.05f && *hp <= 1.0f) *hp -= ACUTE_HEALTH_PER_TICK * dt;
        }
        if (*crime > 0.33f) ++mild;
        if (*crime > 0.66f) ++medium;
        if (*crime > ACUTE) ++serious;
    }
    g_dosed = dosed; g_mild = mild; g_medium = medium; g_serious = serious;
}

static void Refresh(unsigned char* ctx, int dt)
{
    UpdateZones();
    ScanBuildings(ctx);
    WriteGrid(ctx);
    DosePersons(ctx, dt);
    ULONGLONG t = GetTickCount64();
    if (t - g_logAt < 60000) return;
    g_logAt = t;
    LogLine("fallout  zones %.2f/%.2f/%.2f (ruins %d/%d, %d/%d, %d/%d) hotspots %d | citizens exposed %d, cases mild %d medium %d acute %d, hot arrivals %d, ticks %u",
            g_zoneStrength[0], g_zoneStrength[1], g_zoneStrength[2],
            g_ruinsLive[0], g_ruinsInitial[0], g_ruinsLive[1], g_ruinsInitial[1], g_ruinsLive[2], g_ruinsInitial[2],
            g_nhot, g_dosed, g_mild, g_medium, g_serious, g_arrivalsHot, g_ticks);
}

// ------------------------------------------------------------------ hook ----

static void DetourTickAll(void* ctx)
{
    g_origTick(ctx);
    ++g_ticks;
    if ((int)(g_ticks - g_refreshAt) < REFRESH_TICKS) return;
    int dt = (int)(g_ticks - g_refreshAt);
    g_refreshAt = g_ticks;
    __try { Refresh((unsigned char*)ctx, dt); }
    __except (H->faultFilter("fallout", GetExceptionInformation())) {}
}


// The loader chains a hook onto a target another plugin already patched, but
// only when the request presents the bytes that are there now. Try the pristine
// prologue first; if the site was patched, present the live bytes instead.
static const unsigned char* LiveOrPristine(const unsigned char* target, const unsigned char* pristine, size_t len, unsigned char* buf, const char* label)
{
    if (!H->readablePtr(target, len)) return pristine;
    if (memcmp(target, pristine, len) == 0) return pristine;
    memcpy(buf, target, len);
    LogLine("%s: target already patched by another plugin, chaining onto the live bytes", label);
    return buf;
}

// --------------------------------------------------------------- exports ----

// mov rax,rsp; push rbp; push r12; push r13; push r14; push r15; lea rbp,[rax-0x588]
static const unsigned char kTickPro[19] = {
    0x48, 0x8B, 0xC4, 0x55, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57, 0x48, 0x8D, 0xA8, 0x78, 0xFA, 0xFF, 0xFF };

extern "C" __declspec(dllexport) unsigned TsmPluginApiVersion(void) { return TSM_API_VERSION; }

extern "C" __declspec(dllexport) int TsmPluginInit(const TsmHost* host, TsmPluginInfo* info)
{
    H = host;
    info->name    = "fallout";
    info->version = "0.1";
    return 0;
}

void InstallCrashLog(const TsmHost* host);   // crashlog.cpp

extern "C" __declspec(dllexport) int TsmPluginStart(void)
{
    InstallCrashLog(H);
    HMODULE c3d = GetModuleHandleA("C3DDLL64.dll");
    if (c3d) g_getPos = (GetPositionFn)GetProcAddress(c3d, "?GetPosition@C3D_NODE@@QEAA?AVC3DVECTOR3@@XZ");
    if (!g_getPos) { LogLine("fallout  C3D_NODE::GetPosition not found - not installed"); return 1; }
    unsigned char live[19];
    const unsigned char* expect = LiveOrPristine(H->exeBase + RVA_TICK_ALL, kTickPro, 19, live, "fallout TickAllBuildings");
    if (!H->installInlineHook(H->exeBase + RVA_TICK_ALL, (void*)&DetourTickAll, (void**)&g_origTick, expect, 19, "fallout TickAllBuildings"))
    {
        LogLine("fallout  hook TickAllBuildings at 0x%X did not match - not installed", RVA_TICK_ALL);
        return 1;
    }
    for (int k = 0; k < kZoneN; ++k) g_zoneStrength[k] = 1.0f;
    srand((unsigned)GetTickCount64());
    LogLine("fallout  active: %d radiation zones, dose -> crime level, hot salvage halos, contaminated arrivals", kZoneN);
    return 0;
}

BOOL APIENTRY DllMain(HMODULE, DWORD, LPVOID) { return TRUE; }
