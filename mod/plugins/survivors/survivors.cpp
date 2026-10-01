// survivors - population comes from the wasteland, not from a purchase.
//
// THE DESIGN
//
// Vanilla has three ways people cross the border, and this plugin re-purposes
// all three without replacing any of the engine's own pathing, housing or
// bookkeeping:
//
//   tourists   Arrive at a customs house on a timer that the game scales by
//              visa research, an advertising campaign and how many earlier
//              tourists went home satisfied. The player picks them up, shelters
//              them, and they visit attractions. In the wasteland they are
//              SURVIVORS: when one reaches a customs house to go home, a new
//              citizen is spawned there instead - the survivor decided to stay.
//              The vanilla feedback loop then works for us: settled survivors
//              raise next month's arrivals ("word of the refuge spreads").
//
//   immigrants Vanilla sells them for money. Here buying is blocked (the same
//              bytes Permissions_ImmigrantAllowPurchase* writes) and instead a
//              small trickle arrives free at every customs house whose border
//              has the "distress call" (tourist visa) researched, doubled by
//              the "distress broadcast" (advertising campaign).
//
//   foreign    Vanilla pays them in money every time one goes home, at the
//   workers    live price of the `workers` resource. Here they are MERCENARIES:
//              a Mercenary Camp holds food, meat, clothes and alcohol; a
//              mercenary only arrives if the camp can pay, and the wage is
//              taken from the camp in kind while the money price is pinned to
//              zero around the game's own payment.
//
//
// ESTABLISHED FACTS THIS RELIES ON (SOVIET64.exe 1.1.1.9)
//
//   0x1854E0  CustomsHouseTick(ctx, building). Accumulates dt into +0xFC0,
//             spawns tourists (and foreign workers from the +0x1234 demand)
//             every 20 units, resets +0xFC0 and the +0x1230/+0x1234 counters
//             when +0xFC0 passes 120.
//   0x185100  tourists per batch; reads building+0x1230 (tourists that went
//             home this cycle), ctx+0x11767/8 (visa researched, soviet /
//             western), ctx+0x11769/A (advertising campaign active).
//   0x823330  SpawnPerson(ctx, building, char expert, char immigrantRUB,
//             char immigrantUSD, char foreignWorker). All false = tourist.
//             The invite buttons charge ctx+0xE7C/0xE80 x ctx+0x1369C, then
//             call this - money is the caller's business, so it is free.
//   0x831120  PersonBoardsAtBuilding(ctx, person, vehicle) -> bool. When a
//             tourist (person+0x71C != 0) boards at a customs house it counts
//             "returned" (ctx+0x1161C/0x11620, building+0x1230). When a
//             foreign worker (person+0x748: 1 soviet, 2 western) boards, the
//             wage is ctx+0xC2C8 = ResourceGet("workers"): +0x5C RUB for
//             soviet, +0x58 USD for western.
//   0x1CADC0  StorageTick(ctx, building), BUILDINGTYPE_STORAGE (5) arm.
//   building+0x9EC  border side: 3 soviet (RUB), 4 western (USD)
//   ctx+0x13690 / 0x13698   immigrant purchase allowed, RUB / USD
//   building+0x970 vector<Storage> stride 0xE0; storage+0x00/0x08 slot vector
//   stride 16 of { Resource*, float content, float limit }; resource+0x00 name.

#include "../../../vendor/TesmioLoader/src/tesmio_api.h"

#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>

static const TsmHost* H;

// ---------------------------------------------------------------- tuning ----

// Free survivors per 120-unit cycle at a customs house whose border has the
// distress call researched; doubled while the distress broadcast runs.
static const int TRICKLE = 2;

// One in this many settlers is an "expert" (higher education).
static const int EXPERT_EVERY = 5;

// What a mercenary costs the camp, per arrival and again per departure.
struct Wage { const char* res; float tons; };
static const Wage kWage[] = {
    { "food",    0.06f },
    { "meat",    0.03f },
    { "clothes", 0.02f },
    { "alcohol", 0.02f },
};
static const int kWageN = 4;

// --------------------------------------------------------------- offsets ----

#define OFF_TYPEDESC       0x318
#define OFF_BUILDTYPE      0x360
#define OFF_STORAGES       0x970
#define STORAGE_STRIDE     0xE0
#define SLOT_STRIDE        16
#define OFF_SIDE           0x9EC
#define OFF_ACCUM          0xFC0
#define OFF_RETURNED       0x1230
#define OFF_PERSON_TOURIST 0x71C
#define OFF_PERSON_FOREIGN 0x748
#define CTX_VISA_SOV       0x11767
#define CTX_VISA_WEST      0x11768
#define CTX_ADS_SOV        0x11769
#define CTX_ADS_WEST       0x1176A
#define CTX_ALLOW_RUB      0x13690
#define CTX_ALLOW_USD      0x13698
#define CTX_RES_WORKERS    0xC2C8
#define RES_PRICE_USD      0x58
#define RES_PRICE_RUB      0x5C
#define RES_PRICE_SHOWN    0x60
#define RES_PRICE_CHARGED  0x64
#define BUILDINGTYPE_STORAGE 5

#define RVA_CUSTOMS_TICK   0x1854E0
#define RVA_SPAWN_PERSON   0x823330
#define RVA_BOARD          0x831120
#define RVA_STORAGE_TICK   0x1CADC0

// ---------------------------------------------------------------- state -----

#define MAX_CUSTOMS 16
#define MAX_CAMPS   8

typedef struct Customs
{
    void* building;
    int   lastReturned;
    float lastAccum;
    int   settled, trickled;
} Customs;

typedef struct Camp
{
    void*          building;
    unsigned char* slot[kWageN];   // storage slot per wage resource, or NULL
} Camp;

static Customs   g_customs[MAX_CUSTOMS];
static int       g_ncustoms;
static Camp      g_camp[MAX_CAMPS];
static int       g_ncamps;
static int       g_mercsHired, g_mercsRefused, g_mercsPaid;
static ULONGLONG g_logAt;

typedef void (*SpawnPersonFn)(void* ctx, void* building, char expert, char immRUB, char immUSD, char foreign);
typedef void (*TickFn)(void* ctx, void* building);
typedef char (*BoardFn)(void* ctx, void* person, void* vehicle);

static TickFn        g_origCustoms;
static SpawnPersonFn g_origSpawn;
static BoardFn       g_origBoard;
static TickFn        g_origStorage;

// ------------------------------------------------------------- utilities ----

static void LogLine(const char* fmt, ...)
{
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    _vsnprintf_s(buf, sizeof(buf), _TRUNCATE, fmt, ap);
    va_end(ap);
    H->log("%s", buf);
}

static int Readable(const void* p, size_t n) { return p && H->readablePtr(p, n); }

static int LooksLikePointer(const void* p)
{
    ULONG_PTR v = (ULONG_PTR)p;
    if (v < 0x10000 || v > 0x00007FFFFFFFFFFFull || (v & 7)) return 0;
    return H->readablePtr(p, 16);
}

static const char* ResourceName(const void* p)
{
    if (!Readable(p, 32)) return NULL;
    const char* s = (const char*)p;
    int i = 0;
    for (; i < 24; ++i)
    {
        char c = s[i];
        if (c == 0) break;
        if (c < 0x20 || c > 0x7E) return NULL;
    }
    return (i >= 2 && s[i] == 0) ? s : NULL;
}

static int BuildingType(unsigned char* b)
{
    if (!Readable(b + OFF_TYPEDESC, 8)) return -1;
    unsigned char* t = *(unsigned char**)(b + OFF_TYPEDESC);
    if (!Readable(t + OFF_BUILDTYPE, 4)) return -1;
    return *(int*)(t + OFF_BUILDTYPE);
}

// ---------------------------------------------------------------- camps -----

// A Mercenary Camp is any storage building with slots for the wage goods.
static Camp* FindCamp(unsigned char* b, int adopt)
{
    for (int i = 0; i < g_ncamps; ++i)
        if (g_camp[i].building == b) return &g_camp[i];
    if (!adopt || g_ncamps >= MAX_CAMPS) return NULL;
    if (!Readable(b + OFF_STORAGES, 16)) return NULL;

    unsigned char* begin = *(unsigned char**)(b + OFF_STORAGES);
    unsigned char* end   = *(unsigned char**)(b + OFF_STORAGES + 8);
    if (!LooksLikePointer(begin) || end < begin) return NULL;
    int recs = (int)((SIZE_T)(end - begin) / STORAGE_STRIDE);
    if (recs < 1 || recs > 32) return NULL;

    unsigned char* found[kWageN] = { 0 };
    int n = 0;
    for (int i = 0; i < recs; ++i)
    {
        unsigned char* r = begin + (SIZE_T)i * STORAGE_STRIDE;
        if (!Readable(r, STORAGE_STRIDE)) continue;
        unsigned char* sb = *(unsigned char**)(r + 0x00);
        unsigned char* se = *(unsigned char**)(r + 0x08);
        if (!LooksLikePointer(sb) || se < sb || (SIZE_T)(se - sb) > 0x800) continue;
        int slots = (int)((SIZE_T)(se - sb) / SLOT_STRIDE);
        for (int j = 0; j < slots; ++j)
        {
            unsigned char* sl = sb + (SIZE_T)j * SLOT_STRIDE;
            if (!Readable(sl, SLOT_STRIDE)) continue;
            const char* nm = ResourceName(*(void**)sl);
            if (!nm) continue;
            for (int k = 0; k < kWageN; ++k)
                if (!found[k] && strcmp(nm, kWage[k].res) == 0) { found[k] = sl; ++n; }
        }
    }
    if (n < 3) return NULL;     // an ordinary warehouse

    Camp* c = &g_camp[g_ncamps++];
    c->building = b;
    for (int k = 0; k < kWageN; ++k) c->slot[k] = found[k];
    LogLine("survivors  mercenary camp adopted at %p (%d of %d wage goods stocked)", b, n, kWageN);
    return c;
}

// Can any camp cover one wage? Returns the camp, or NULL.
static Camp* CampThatCanPay(void)
{
    for (int i = 0; i < g_ncamps; ++i)
    {
        Camp* c = &g_camp[i];
        int ok = 1;
        for (int k = 0; k < kWageN && ok; ++k)
        {
            if (!c->slot[k]) continue;                 // resource not stocked here: not required
            if (!Readable(c->slot[k], SLOT_STRIDE)) { ok = 0; break; }
            if (*(float*)(c->slot[k] + 8) < kWage[k].tons) ok = 0;
        }
        if (ok) return c;
    }
    return NULL;
}

static void CampPay(Camp* c)
{
    for (int k = 0; k < kWageN; ++k)
    {
        if (!c->slot[k] || !Readable(c->slot[k], SLOT_STRIDE)) continue;
        float* content = (float*)(c->slot[k] + 8);
        *content -= kWage[k].tons;
        if (*content < 0.0f) *content = 0.0f;
    }
}

// --------------------------------------------------------------- customs ----

static Customs* TrackCustoms(void* b)
{
    for (int i = 0; i < g_ncustoms; ++i)
        if (g_customs[i].building == b) return &g_customs[i];
    if (g_ncustoms >= MAX_CUSTOMS) return NULL;
    Customs* c = &g_customs[g_ncustoms++];
    memset(c, 0, sizeof(*c));
    c->building = b;
    return c;
}

static void Settle(unsigned char* ctx, unsigned char* b, int count, int why, Customs* c)
{
    int side = *(int*)(b + OFF_SIDE);
    for (int i = 0; i < count; ++i)
    {
        char expert = (rand() % EXPERT_EVERY) == 0;
        // Spawn as an immigrant of the border's own bloc; the game houses them
        // exactly as it houses a bought one.
        g_origSpawn(ctx, b, expert, side == 3, side == 4, 0);
    }
    if (why == 0) c->settled += count; else c->trickled += count;
}

static void AfterCustomsTick(unsigned char* ctx, unsigned char* b)
{
    Customs* c = TrackCustoms(b);
    if (!c || !Readable(b + OFF_RETURNED, 8) || !Readable(b + OFF_ACCUM, 4)) return;

    // Nobody buys people in the wasteland.
    if (Readable(ctx + CTX_ALLOW_RUB, 1)) *(ctx + CTX_ALLOW_RUB) = 0;
    if (Readable(ctx + CTX_ALLOW_USD, 1)) *(ctx + CTX_ALLOW_USD) = 0;

    // 1. Survivors who "went home" stay: one new citizen per returned tourist.
    int now = *(int*)(b + OFF_RETURNED);
    int base = (now < c->lastReturned) ? 0 : c->lastReturned;   // the tick zeroes it each cycle
    if (now > base) Settle(ctx, b, now - base, 0, c);
    c->lastReturned = now;

    // 2. The organic trickle, once per cycle, when the accumulator wraps.
    float acc = *(float*)(b + OFF_ACCUM);
    if (acc < c->lastAccum)
    {
        int side = *(int*)(b + OFF_SIDE);
        int visa = (side == 3) ? (Readable(ctx + CTX_VISA_SOV, 1) && ctx[CTX_VISA_SOV])
                 : (side == 4) ? (Readable(ctx + CTX_VISA_WEST, 1) && ctx[CTX_VISA_WEST]) : 0;
        int ads  = (side == 3) ? (Readable(ctx + CTX_ADS_SOV, 1) && ctx[CTX_ADS_SOV] == 1)
                 : (side == 4) ? (Readable(ctx + CTX_ADS_WEST, 1) && ctx[CTX_ADS_WEST] == 1) : 0;
        if (visa) Settle(ctx, b, TRICKLE * (ads ? 2 : 1), 1, c);
    }
    c->lastAccum = acc;

    ULONGLONG t = GetTickCount64();
    if (t - g_logAt < 30000) return;
    g_logAt = t;
    for (int i = 0; i < g_ncustoms; ++i)
        if (g_customs[i].settled || g_customs[i].trickled)
            LogLine("survivors  customs %p: %d survivors settled, %d arrived on their own",
                    g_customs[i].building, g_customs[i].settled, g_customs[i].trickled);
    if (g_mercsHired || g_mercsRefused)
        LogLine("survivors  mercenaries: %d hired, %d paid off, %d turned away (camp could not pay)",
                g_mercsHired, g_mercsPaid, g_mercsRefused);
}

// ----------------------------------------------------------------- hooks ----

static void DetourCustoms(void* ctx, void* building)
{
    g_origCustoms(ctx, building);
    if (building)
    {
        __try { AfterCustomsTick((unsigned char*)ctx, (unsigned char*)building); }
        __except (H->faultFilter("survivors", GetExceptionInformation())) {}
    }
}

static void DetourSpawn(void* ctx, void* building, char expert, char immRUB, char immUSD, char foreign)
{
    if (foreign)
    {
        Camp* c = NULL;
        __try { c = CampThatCanPay(); }
        __except (H->faultFilter("survivors", GetExceptionInformation())) { c = NULL; }
        if (!c) { ++g_mercsRefused; return; }     // no camp, or an empty one: no mercenary
        __try { CampPay(c); } __except (H->faultFilter("survivors", GetExceptionInformation())) {}
        ++g_mercsHired;
    }
    g_origSpawn(ctx, building, expert, immRUB, immUSD, foreign);
}

static char DetourBoard(void* ctx, void* person, void* vehicle)
{
    unsigned char* p = (unsigned char*)person;
    unsigned char* g = (unsigned char*)ctx;
    int foreign = 0;
    __try { foreign = Readable(p + OFF_PERSON_FOREIGN, 4) && *(int*)(p + OFF_PERSON_FOREIGN) != 0; }
    __except (H->faultFilter("survivors", GetExceptionInformation())) { foreign = 0; }
    if (!foreign) return g_origBoard(ctx, person, vehicle);

    // A mercenary going home: the game pays money at the `workers` price.
    // Pin every price column to zero for the duration, pay the camp in kind.
    unsigned char* res = NULL;
    float saved[4] = { 0, 0, 0, 0 };
    static const int cols[4] = { RES_PRICE_USD, RES_PRICE_RUB, RES_PRICE_SHOWN, RES_PRICE_CHARGED };
    __try
    {
        if (Readable(g + CTX_RES_WORKERS, 8)) res = *(unsigned char**)(g + CTX_RES_WORKERS);
        if (res && Readable(res, 0x80))
            for (int i = 0; i < 4; ++i) { saved[i] = *(float*)(res + cols[i]); *(float*)(res + cols[i]) = 0.0f; }
        else res = NULL;
    }
    __except (H->faultFilter("survivors", GetExceptionInformation())) { res = NULL; }

    char r = g_origBoard(ctx, person, vehicle);

    __try
    {
        if (res) for (int i = 0; i < 4; ++i) *(float*)(res + cols[i]) = saved[i];
        Camp* c = CampThatCanPay();
        if (!c && g_ncamps) c = &g_camp[0];       // take what is left
        if (c) { CampPay(c); ++g_mercsPaid; }
    }
    __except (H->faultFilter("survivors", GetExceptionInformation())) {}
    return r;
}

static void DetourStorage(void* ctx, void* building)
{
    g_origStorage(ctx, building);
    if (building)
    {
        __try { FindCamp((unsigned char*)building, 1); }
        __except (H->faultFilter("survivors", GetExceptionInformation())) {}
    }
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

static const unsigned char kCustomsPro[15] = {
    0x48, 0x8B, 0xC4, 0x48, 0x89, 0x58, 0x18, 0x56, 0x48, 0x81, 0xEC, 0x90, 0x00, 0x00, 0x00 };
static const unsigned char kSpawnPro[15] = {
    0x48, 0x89, 0x54, 0x24, 0x10, 0x48, 0x89, 0x4C, 0x24, 0x08, 0x57, 0x48, 0x83, 0xEC, 0x30 };
static const unsigned char kBoardPro[15] = {
    0x48, 0x89, 0x5C, 0x24, 0x20, 0x48, 0x89, 0x54, 0x24, 0x10, 0x55, 0x56, 0x57, 0x41, 0x54 };
// 10 bytes of prologue then a 7-byte `mov rax,[rdx+0xBB0]`: steal all 17 so
// the trampoline never splits an instruction.
static const unsigned char kStoragePro[17] = {
    0x48, 0x89, 0x5C, 0x24, 0x08, 0x57, 0x48, 0x83, 0xEC, 0x20, 0x48, 0x8B, 0x82, 0xB0, 0x0B, 0x00, 0x00 };

extern "C" __declspec(dllexport) unsigned TsmPluginApiVersion(void) { return TSM_API_VERSION; }

extern "C" __declspec(dllexport) int TsmPluginInit(const TsmHost* host, TsmPluginInfo* info)
{
    H = host;
    info->name    = "survivors";
    info->version = "0.1";
    return 0;
}

extern "C" __declspec(dllexport) int TsmPluginStart(void)
{
    struct { unsigned rva; void* detour; void** tramp; const unsigned char* pro; size_t len; const char* label; } hooks[] = {
        { RVA_SPAWN_PERSON, (void*)&DetourSpawn,   (void**)&g_origSpawn,   kSpawnPro,   15, "survivors SpawnPerson" },
        { RVA_CUSTOMS_TICK, (void*)&DetourCustoms, (void**)&g_origCustoms, kCustomsPro, 15, "survivors CustomsHouseTick" },
        { RVA_BOARD,        (void*)&DetourBoard,   (void**)&g_origBoard,   kBoardPro,   15, "survivors PersonBoards" },
        { RVA_STORAGE_TICK, (void*)&DetourStorage, (void**)&g_origStorage, kStoragePro, 17, "survivors StorageTick" },
    };
    for (int i = 0; i < 4; ++i)
    {
        unsigned char live[32];
        const unsigned char* expect = LiveOrPristine(H->exeBase + hooks[i].rva, hooks[i].pro, hooks[i].len, live, hooks[i].label);
        if (!H->installInlineHook(H->exeBase + hooks[i].rva, hooks[i].detour, hooks[i].tramp, expect, hooks[i].len, hooks[i].label))
        {
            LogLine("survivors  hook %s at 0x%X did not match - not installed", hooks[i].label, hooks[i].rva);
            return 1;
        }
    }
    // The tick's spawn goes through the SpawnPerson trampoline too, so our
    // own settlers use the untouched original.
    srand((unsigned)GetTickCount64());
    LogLine("survivors  active: returning tourists settle, %d free arrivals per cycle with the distress call, mercenaries paid in kind", TRICKLE);
    return 0;
}

BOOL APIENTRY DllMain(HMODULE, DWORD, LPVOID) { return TRUE; }
