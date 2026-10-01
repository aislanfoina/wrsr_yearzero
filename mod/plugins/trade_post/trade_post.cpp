// trade_post - make the Survival Trade Post charge for what it sells.
//
// THE DESIGN
//
// The trade post is an ordinary FACTORY. It makes goods from nothing at a rate
// set by its workers, holds them in real storages, and runs dry when you buy
// faster than it restocks. All of that is vanilla data in building.ini and needs
// no code at all.
//
// The one thing vanilla will not do is make you PAY for a factory's output. That
// is this plugin, and it is the whole of it: watch the post's storages, and when
// the contents go down - which only happens when a vehicle loads - take the
// money.
//
//
// WHY THIS WORKS WHERE THE CUSTOMS HOUSE DID NOT
//
// Four attempts to measure purchases at a customs house failed, because a
// customs house never holds anything: goods are minted at load time, its
// storages read 0.000 with a 1 tonne capacity, and asphalt is sold there despite
// having no storage slot at all. There was simply nothing to observe.
//
// A factory's storage is real. The goods are in it, the vanilla building window
// shows them, and the number drops when a truck takes some. Measuring the sale
// is a subtraction.
//
//
// ESTABLISHED FACTS THIS RELIES ON (SOVIET64.exe 1.1.1.9)
//
//   0x1D1E80          FactoryTick(context, building), reached from the building
//                     dispatcher's BUILDINGTYPE_FACTORY (6) arm at 0x13DD69.
//                     19-byte prologue, no rip-relative operands, and claimed by
//                     no other installed plugin.
//   building+0x318    type descriptor; +0x360 within it is BUILDINGTYPE
//   building+0x970    std::vector<Storage>, stride 0xE0
//   storage+0x00/0x08 begin/end of a slot vector, stride 16
//   slot              { resource*, float content, float limit }
//   resource+0x00     32-byte NUL-terminated name
//   resource+0x64     the price the customs house UI shows and charges
//   game+0x588        RUB balance, a double  (game+0x580 is USD)
//
// All confirmed in game, most of them by matching numbers read off the screen.

#include "../../../vendor/TesmioLoader/src/tesmio_api.h"

#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

static const TsmHost* H;

// --------------------------------------------------------------- tuning -----

// Defaults. Every one of these can be overridden by trade_post.ini sitting
// beside this DLL; see LoadConfig below for why the file is found by hand.
#define DEF_PRICE_MULT 1.35f
#define DEF_USD_RATE   1.0f

#define MAX_OVERRIDE 32

typedef struct Config
{
    float priceMult;                       // global multiple of market price
    int   useUsd;                          // 0 = charge roubles, 1 = charge dollars
    float usdRate;                         // roubles per dollar, when useUsd
    int   overrides;
    char  ovName[MAX_OVERRIDE][32];        // per-resource price multiplier
    float ovMult[MAX_OVERRIDE];
    char  path[MAX_PATH];
    int   loaded;
} Config;

static Config g_cfg;

// The products this plugin bills for. A storage holding anything else is left
// alone, so the post can be given non-traded contents later without confusion.
static const char* kGoods[] = {
    /* Survival Trade Post - construction materials */
    "gravel", "bricks", "boards", "steel", "cement",
    /* Survival Goods Post - consumer goods. "eletronics" is the game's own
       spelling, like "eletric"; the resource does not exist under any other
       name and a mismatch here would silently fail to bill. */
    "food", "alcohol", "clothes", "eletronics"
};

// A building only counts as a trade post if it exports at least this many of
// them. No vanilla factory produces this combination, which is what makes the
// fingerprint safe.
static const int MIN_MATCH = 3;

// --------------------------------------------------------------- offsets ----

#define OFF_TYPEDESC   0x318
#define OFF_BUILDTYPE  0x360
#define OFF_STORAGES   0x970
#define STORAGE_STRIDE 0xE0
#define SLOT_STRIDE    16
#define OFF_RES_PRICE  0x64
#define OFF_MONEY_RUB  0x588
#define OFF_MONEY_USD  0x580
#define GAME_RVA       0x9D4F10

// ---------------------------------------------------------------- state -----

#define MAX_POSTS 16
#define MAX_SLOTS 24

typedef struct Post
{
    void*          building;
    int            slots;
    unsigned char* slot[MAX_SLOTS];
    float          last[MAX_SLOTS];
    double         charged;        // cumulative, for the log
    float          sold;
    float          logged;         // `sold` at the last line printed
} Post;

static Post      g_post[MAX_POSTS];
static int       g_posts;
static ULONGLONG g_logAt;

// ------------------------------------------------------------- utilities ----

static void LogLine(const char* fmt, ...)
{
    // The host formatter is not printf and mishandles width-modified string
    // conversions; format here and hand it a single "%s".
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    _vsnprintf_s(buf, sizeof(buf), _TRUNCATE, fmt, ap);
    va_end(ap);
    H->log("%s", buf);
}

static int Readable(const void* p, size_t n) { return p && H->readablePtr(p, n); }

// ------------------------------------------------------------- config ------
//
// TsmHost::configInt and configString resolve their file name against
// TsmHost::baseDir. Under Republic Mod Loader's compatibility host that folder
// is neither rml\plugins nor the Workshop item, so a plugin ini placed anywhere
// sensible is simply never read - a trap that cost this project real time before
// it was understood.
//
// So the file is located by hand instead: ask Windows which module this very
// function lives in, take that path, and read the ini beside it. That is
// rml\plugins\trade_post.ini no matter how the host was configured.

static void Trim(char* s)
{
    char* e = s + strlen(s);
    while (e > s && (e[-1] == ' ' || e[-1] == '\t' || e[-1] == '\r' || e[-1] == '\n')) *--e = 0;
    char* b = s;
    while (*b == ' ' || *b == '\t') ++b;
    if (b != s) memmove(s, b, strlen(b) + 1);
}

static void ConfigPath(char* out, size_t n)
{
    HMODULE self = NULL;
    out[0] = 0;
    if (!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                            GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                            (LPCSTR)&ConfigPath, &self))
        return;

    char path[MAX_PATH];
    DWORD len = GetModuleFileNameA(self, path, MAX_PATH);
    if (!len || len >= MAX_PATH) return;

    char* slash = strrchr(path, '\\');
    if (!slash) return;
    *slash = 0;
    _snprintf_s(out, n, _TRUNCATE, "%s\\trade_post.ini", path);
}

static void LoadConfig(void)
{
    g_cfg.priceMult = DEF_PRICE_MULT;
    g_cfg.useUsd    = 0;
    g_cfg.usdRate   = DEF_USD_RATE;
    g_cfg.overrides = 0;
    g_cfg.loaded    = 0;

    ConfigPath(g_cfg.path, sizeof(g_cfg.path));
    if (!g_cfg.path[0]) return;

    FILE* f = NULL;
    if (fopen_s(&f, g_cfg.path, "r") != 0 || !f) return;

    char line[256], section[64] = "";
    while (fgets(line, sizeof(line), f))
    {
        char* hash = strpbrk(line, ";#");
        if (hash) *hash = 0;
        Trim(line);
        if (!line[0]) continue;

        if (line[0] == '[')
        {
            char* end = strchr(line, ']');
            if (end) *end = 0;
            strncpy_s(section, sizeof(section), line + 1, _TRUNCATE);
            continue;
        }

        char* eq = strchr(line, '=');
        if (!eq) continue;
        *eq = 0;
        char* key = line;
        char* val = eq + 1;
        Trim(key); Trim(val);
        if (!key[0] || !val[0]) continue;

        if (_stricmp(section, "general") == 0)
        {
            if (_stricmp(key, "price_multiplier") == 0)
                g_cfg.priceMult = (float)atof(val);
            else if (_stricmp(key, "currency") == 0)
                g_cfg.useUsd = (_stricmp(val, "USD") == 0);
            else if (_stricmp(key, "usd_rate") == 0)
                g_cfg.usdRate = (float)atof(val);
        }
        else if (_stricmp(section, "price") == 0)
        {
            if (g_cfg.overrides < MAX_OVERRIDE)
            {
                strncpy_s(g_cfg.ovName[g_cfg.overrides], 32, key, _TRUNCATE);
                g_cfg.ovMult[g_cfg.overrides] = (float)atof(val);
                ++g_cfg.overrides;
            }
        }
        // [production] is consumed by build.ps1 at install time, not here: the
        // rate lives in building.ini, which only the game's own parser reads.
    }
    fclose(f);

    if (g_cfg.priceMult <= 0.0f) g_cfg.priceMult = DEF_PRICE_MULT;
    if (g_cfg.usdRate   <= 0.0f) g_cfg.usdRate   = DEF_USD_RATE;
    g_cfg.loaded = 1;
}

static float PriceMultFor(const char* name)
{
    for (int i = 0; i < g_cfg.overrides; ++i)
        if (_stricmp(g_cfg.ovName[i], name) == 0) return g_cfg.ovMult[i];
    return g_cfg.priceMult;
}

static int LooksLikePointer(const void* p)
{
    ULONG_PTR v = (ULONG_PTR)p;
    if (v < 0x10000 || v > 0x00007FFFFFFFFFFFull) return 0;
    if (v & 7) return 0;
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

static int IsGood(const char* n)
{
    for (int i = 0; i < (int)(sizeof(kGoods) / sizeof(kGoods[0])); ++i)
        if (strcmp(n, kGoods[i]) == 0) return 1;
    return 0;
}

// --------------------------------------------------------------- the post ---

// Identify a trade post by what it exports. Checking the resource set is far
// more robust than trying to recognise a building.ini or a mesh, and it keeps
// working if the post is renamed or re-skinned.
static Post* Adopt(unsigned char* b)
{
    for (int i = 0; i < g_posts; ++i)
        if (g_post[i].building == b) return &g_post[i];
    if (g_posts >= MAX_POSTS) return NULL;

    if (!Readable(b + OFF_STORAGES, 16)) return NULL;
    unsigned char* begin = *(unsigned char**)(b + OFF_STORAGES);
    unsigned char* end   = *(unsigned char**)(b + OFF_STORAGES + 8);
    if (!LooksLikePointer(begin) || end < begin) return NULL;

    int recs = (int)((SIZE_T)(end - begin) / STORAGE_STRIDE);
    if (recs < 1 || recs > 32) return NULL;

    unsigned char* found[MAX_SLOTS];
    int n = 0;

    for (int i = 0; i < recs && n < MAX_SLOTS; ++i)
    {
        unsigned char* r = begin + (SIZE_T)i * STORAGE_STRIDE;
        if (!Readable(r, STORAGE_STRIDE)) continue;

        unsigned char* sb = *(unsigned char**)(r + 0x00);
        unsigned char* se = *(unsigned char**)(r + 0x08);
        if (!LooksLikePointer(sb) || se < sb || (SIZE_T)(se - sb) > 0x800) continue;

        int slots = (int)((SIZE_T)(se - sb) / SLOT_STRIDE);
        for (int j = 0; j < slots && n < MAX_SLOTS; ++j)
        {
            unsigned char* sl = sb + (SIZE_T)j * SLOT_STRIDE;
            if (!Readable(sl, SLOT_STRIDE)) continue;
            const char* nm = ResourceName(*(void**)sl);
            if (nm && IsGood(nm)) found[n++] = sl;
        }
    }

    if (n < MIN_MATCH) return NULL;      // an ordinary factory; leave it alone

    Post* p = &g_post[g_posts++];
    memset(p, 0, sizeof(*p));
    p->building = b;
    p->slots = n;
    for (int i = 0; i < n; ++i)
    {
        p->slot[i] = found[i];
        p->last[i] = *(float*)(found[i] + 8);
    }

    LogLine("trade_post  adopted building %p with %d tradeable slots", b, n);
    return p;
}

static void Charge(Post* p)
{
    unsigned char* game = H->exeBase + GAME_RVA;
    const int off = g_cfg.useUsd ? OFF_MONEY_USD : OFF_MONEY_RUB;
    if (!Readable(game + off, 8)) return;

    for (int i = 0; i < p->slots; ++i)
    {
        unsigned char* sl = p->slot[i];
        if (!Readable(sl, SLOT_STRIDE)) continue;

        float now = *(float*)(sl + 8);
        float sold = p->last[i] - now;
        p->last[i] = now;

        // Only a DECREASE is a sale. An increase is the post restocking itself,
        // which is free - the production rate is the restock rule.
        if (sold <= 0.0005f) continue;

        unsigned char* rec = *(unsigned char**)sl;
        const char* nm = ResourceName(rec);
        if (!nm || !Readable(rec + OFF_RES_PRICE, 4)) continue;

        float unit = *(float*)(rec + OFF_RES_PRICE);
        if (unit < 0.0f) unit = -unit;          // waste prices are negative
        double cost = (double)sold * unit * PriceMultFor(nm);

        // The price field is denominated in roubles. Charging dollars therefore
        // needs a conversion, and the game does not expose one we have found, so
        // usd_rate is a config knob: roubles per dollar.
        if (g_cfg.useUsd) cost /= (double)g_cfg.usdRate;

        double* money = (double*)(game + off);
        *money -= cost;

        p->charged += cost;
        p->sold    += sold;
    }
}

static void Tick(unsigned char* b)
{
    Post* p = Adopt(b);
    if (!p) return;
    Charge(p);

    ULONGLONG now = GetTickCount64();
    if (now - g_logAt < 5000) return;
    g_logAt = now;

    // Only report a post whose total actually moved since the last line. The
    // old code re-printed an unchanged total every five seconds, which buried
    // the interesting lines during debugging.
    for (int i = 0; i < g_posts; ++i)
    {
        if (g_post[i].sold < 0.01f) continue;
        if (g_post[i].sold - g_post[i].logged < 0.01f) continue;
        g_post[i].logged = g_post[i].sold;
        LogLine("trade_post  %p sold %.2f t for %.0f %s so far",
                g_post[i].building, g_post[i].sold, g_post[i].charged,
                g_cfg.useUsd ? "USD" : "RUB");
    }
}

// ---------------------------------------------------------------- hook ------

// FactoryTick(context, building), from the dispatcher's type-6 arm at 0x13DD69.
#define RVA_FACTORY_TICK 0x1D1E80

static const unsigned char kPrologue[19] = {
    0x48, 0x8B, 0xC4,               // mov  rax, rsp
    0x55,                           // push rbp
    0x56,                           // push rsi
    0x57,                           // push rdi
    0x41, 0x54,                     // push r12
    0x41, 0x55,                     // push r13
    0x41, 0x56,                     // push r14
    0x41, 0x57,                     // push r15
    0x48, 0x8D, 0x6C, 0x24, 0x80    // lea  rbp, [rsp-0x80]
};

typedef void (*FactoryTickFn)(void* context, void* building);
static FactoryTickFn g_orig;

static void Detour(void* context, void* building)
{
    // Charge AFTER the game has run its tick, so the storage figures reflect
    // whatever loading happened this frame.
    g_orig(context, building);

    if (building)
    {
        __try { Tick((unsigned char*)building); }
        __except (H->faultFilter("trade_post", GetExceptionInformation())) {}
    }
}

// --------------------------------------------------------------- exports ----

extern "C" __declspec(dllexport) unsigned TsmPluginApiVersion(void)
{
    return TSM_API_VERSION;
}

extern "C" __declspec(dllexport) int TsmPluginInit(const TsmHost* host, TsmPluginInfo* info)
{
    H = host;
    info->name    = "trade_post";
    info->version = "1.0";
    LoadConfig();
    return 0;
}

extern "C" __declspec(dllexport) int TsmPluginStart(void)
{
    unsigned char* target = H->exeBase + RVA_FACTORY_TICK;

    if (!H->installInlineHook(target, (void*)&Detour, (void**)&g_orig,
                              kPrologue, sizeof(kPrologue), "trade_post FactoryTick"))
    {
        H->log("trade_post  factory tick 0x1D1E80 did not match - not installed");
        return 1;
    }

    if (g_cfg.loaded)
        LogLine("trade_post  config read from %s", g_cfg.path);
    else
        LogLine("trade_post  no config at %s - using built-in defaults",
                g_cfg.path[0] ? g_cfg.path : "(path unresolved)");

    LogLine("trade_post  active: billing output at %.2fx market price in %s%s",
            g_cfg.priceMult, g_cfg.useUsd ? "USD" : "RUB",
            g_cfg.overrides ? " (with per-resource overrides)" : "");
    return 0;
}

BOOL APIENTRY DllMain(HMODULE, DWORD, LPVOID) { return TRUE; }
