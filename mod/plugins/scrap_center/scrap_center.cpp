// scrap_center - disassembling a vehicle teaches you how to build it.
//
// THE DESIGN
//
// Vanilla already has everything but the last step. A scrapyard
// ($TYPE_SCRAPYARD) accepts any vehicle the player sends to it with the
// "Send to scrapyard" button - road vehicles drive in, trains use its
// pass-through track, and brand-new vehicles can arrive as cargo - takes it
// apart over a few days and puts scrap metal in its storages. Blueprints, on
// the other hand, are normally BOUGHT from abroad, which a wasteland has no
// abroad to buy from.
//
// This plugin joins the two: while a scrapyard is disassembling a vehicle, the
// blueprint of that vehicle's type is marked as owned. Park a mystery truck you
// found in the ruins, send it to the Scrap Center, and your production line can
// build that truck from then on. The scenario can forbid purchases with
// Permissions_BlueprintAllowUSD/RUB, leaving scrapping as the only source.
//
//
// ESTABLISHED FACTS THIS RELIES ON (SOVIET64.exe 1.1.1.9)
//
//   BUILDINGTYPE_SCRAPYARD = 109 (0x6D)   from the "$TYPE_SCRAPYARD" parser branch
//   0x14B920   ScrapyardTick(context, building), reached from the building
//              dispatcher's type-109 arm at 0x13E1BA. 19-byte prologue, no
//              rip-relative operands.
//   building+0x11C8   VehicleTypes* of the vehicle being disassembled. Set from
//                     vehicle+0x1708 when a delivered vehicle is accepted (the
//                     vehicle object is destroyed at that moment), cleared when
//                     the progress returned by 0x1B07A0 reaches 1.0.
//   VehicleTypes      stride 0x9F08 (0x1FEFF0 is `base + index * 0x9F08`)
//     +0x200   ident, NUL-terminated (the folder name, e.g. "personal_s110r")
//     +0x294   nVehicleType (VEHICLETYPE enum)
//     +0x85BC  nCostUSD      +0x85C0  nCostRUB      +0x8604  fResourceCapacity
//     +0x9C88  bBlueprintPurchased - the byte the scenario VM's
//              Scenario_AddRoadVehicleBlueprint (0x5AD20A) writes 1 to and
//              Scenario_RemoveRoadVehicleBlueprint (0x5AD3AC) writes 0 to, and
//              the purchase button (0x812A40) writes 1 to after taking the money.
//              The three dwords after it are nBrandNewSoldForRUB/USD and
//              nBuiltInProductionLine, in the VM's declared order.

#include "../../../vendor/TesmioLoader/src/tesmio_api.h"

#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

static const TsmHost* H;

// --------------------------------------------------------------- offsets ----

#define OFF_SCRAP_TYPE     0x11C8   // building -> VehicleTypes* being scrapped
#define OFF_TYPE_IDENT     0x200
#define OFF_TYPE_VEHTYPE   0x294
#define OFF_TYPE_BLUEPRINT 0x9C88
#define TYPE_STRIDE        0x9F08

#define RVA_SCRAPYARD_TICK 0x14B920

// ---------------------------------------------------------------- state -----

#define MAX_YARDS 32

typedef struct Yard
{
    void* building;
    void* lastType;     // what we last saw in +0x11C8, to log transitions once
} Yard;

static Yard g_yard[MAX_YARDS];
static int  g_yards;
static int  g_learned;

// ------------------------------------------------------------- utilities ----

static void LogLine(const char* fmt, ...)
{
    // The host formatter is not printf; format here and hand it one "%s".
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    _vsnprintf_s(buf, sizeof(buf), _TRUNCATE, fmt, ap);
    va_end(ap);
    H->log("%s", buf);
}

static int Readable(const void* p, size_t n) { return p && H->readablePtr(p, n); }

// A VehicleTypes record has a printable ident at +0x200 and a small enum at
// +0x294. Anything else in +0x11C8 is not something we should write to.
static int LooksLikeVehicleType(const unsigned char* t)
{
    ULONG_PTR v = (ULONG_PTR)t;
    if (v < 0x10000 || v > 0x00007FFFFFFFFFFFull || (v & 7)) return 0;
    if (!Readable(t, TYPE_STRIDE)) return 0;

    const char* s = (const char*)(t + OFF_TYPE_IDENT);
    int i = 0;
    for (; i < 96; ++i)
    {
        char c = s[i];
        if (c == 0) break;
        if (c < 0x20 || c > 0x7E) return 0;
    }
    if (i < 2 || s[i] != 0) return 0;

    int vt = *(const int*)(t + OFF_TYPE_VEHTYPE);
    return vt >= 0 && vt < 64;
}

static Yard* Track(void* b)
{
    for (int i = 0; i < g_yards; ++i)
        if (g_yard[i].building == b) return &g_yard[i];
    if (g_yards >= MAX_YARDS) return NULL;
    Yard* y = &g_yard[g_yards++];
    y->building = b;
    y->lastType = NULL;
    return y;
}

// ---------------------------------------------------------------- work ------

static void AfterTick(unsigned char* b)
{
    if (!Readable(b + OFF_SCRAP_TYPE, 8)) return;
    unsigned char* type = *(unsigned char**)(b + OFF_SCRAP_TYPE);

    Yard* y = Track(b);
    void* last = y ? y->lastType : NULL;
    if (y) y->lastType = type;

    if (!type)
    {
        if (last) LogLine("scrap_center  %p finished disassembling", b);
        return;
    }
    if (!LooksLikeVehicleType(type)) return;

    unsigned char* flag = type + OFF_TYPE_BLUEPRINT;
    const char* ident = (const char*)(type + OFF_TYPE_IDENT);

    if (type != last)
        LogLine("scrap_center  %p disassembling '%s' (blueprint %s)",
                b, ident, *flag ? "already owned" : "NOT owned yet");

    if (*flag) return;

    // Reverse-engineered, in the literal sense: the vehicle is being taken
    // apart on the yard floor, and now we know how it goes together.
    *flag = 1;
    ++g_learned;
    LogLine("scrap_center  learned blueprint '%s' (%d so far this session)", ident, g_learned);
}

// ---------------------------------------------------------------- hook ------

static const unsigned char kPrologue[19] = {
    0x48, 0x8B, 0xC4,                           // mov  rax, rsp
    0x57,                                       // push rdi
    0x41, 0x54,                                 // push r12
    0x41, 0x55,                                 // push r13
    0x41, 0x56,                                 // push r14
    0x41, 0x57,                                 // push r15
    0x48, 0x81, 0xEC, 0x50, 0x01, 0x00, 0x00    // sub  rsp, 0x150
};

typedef void (*ScrapyardTickFn)(void* context, void* building);
static ScrapyardTickFn g_orig;

static void Detour(void* context, void* building)
{
    // Let the game accept, advance or finish the scrapping first; then read
    // what it is working on.
    g_orig(context, building);

    if (building)
    {
        __try { AfterTick((unsigned char*)building); }
        __except (H->faultFilter("scrap_center", GetExceptionInformation())) {}
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
    info->name    = "scrap_center";
    info->version = "0.1";
    return 0;
}

extern "C" __declspec(dllexport) int TsmPluginStart(void)
{
    unsigned char* target = H->exeBase + RVA_SCRAPYARD_TICK;

    if (!H->installInlineHook(target, (void*)&Detour, (void**)&g_orig,
                              kPrologue, sizeof(kPrologue), "scrap_center ScrapyardTick"))
    {
        H->log("scrap_center  scrapyard tick 0x14B920 did not match - not installed");
        return 1;
    }

    LogLine("scrap_center  active: scrapping a vehicle grants its blueprint");
    return 0;
}

BOOL APIENTRY DllMain(HMODULE, DWORD, LPVOID) { return TRUE; }
