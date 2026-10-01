// crashlog.cpp - first-chance exception logger, compiled into fallout.dll.
//
// Republic Mod Loader reports "WRSR exited abnormally with code 0xC0000005"
// but neither it nor Windows Error Reporting leaves a dump behind, so a crash
// in the game (or in one of our plugins) has no location. This vectored
// exception handler logs the first few hard faults with the faulting address
// as module+offset, the registers, and every stack slot that points into a
// loaded module (a cheap stand-in for a stack walk). It never handles the
// exception itself - EXCEPTION_CONTINUE_SEARCH - so game behaviour is
// unchanged.
#include "../../../vendor/TesmioLoader/src/tesmio_api.h"
#include <windows.h>
#include <stdio.h>
#include <string.h>

static const TsmHost* g_clHost = NULL;
static volatile LONG g_clReported = 0;

static void DescribeAddress(char* out, size_t n, const void* addr)
{
    HMODULE m = NULL;
    char path[MAX_PATH] = { 0 };
    if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCSTR)addr, &m) && m
        && GetModuleFileNameA(m, path, MAX_PATH))
    {
        const char* base = strrchr(path, '\\');
        base = base ? base + 1 : path;
        _snprintf_s(out, n, _TRUNCATE, "%s+0x%llX", base, (unsigned long long)((const unsigned char*)addr - (const unsigned char*)m));
    }
    else
        _snprintf_s(out, n, _TRUNCATE, "%p", addr);
}

static int InModule(unsigned long long v)
{
    HMODULE m = NULL;
    return v > 0x10000 && GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCSTR)v, &m) && m;
}

static LONG CALLBACK CrashLogHandler(EXCEPTION_POINTERS* ep)
{
    if (!ep || !ep->ExceptionRecord || !ep->ContextRecord) return EXCEPTION_CONTINUE_SEARCH;
    DWORD code = ep->ExceptionRecord->ExceptionCode;
    if (code != EXCEPTION_ACCESS_VIOLATION && code != EXCEPTION_ILLEGAL_INSTRUCTION && code != EXCEPTION_STACK_OVERFLOW
        && code != EXCEPTION_INT_DIVIDE_BY_ZERO && code != EXCEPTION_PRIV_INSTRUCTION && code != 0xC0000409)
        return EXCEPTION_CONTINUE_SEARCH;
    if (InterlockedIncrement(&g_clReported) > 4 || !g_clHost) return EXCEPTION_CONTINUE_SEARCH;

    char where[200], line[512];
    DescribeAddress(where, sizeof where, ep->ExceptionRecord->ExceptionAddress);
    const CONTEXT* c = ep->ContextRecord;
    unsigned long long av_kind = 0, av_addr = 0;
    if (code == EXCEPTION_ACCESS_VIOLATION && ep->ExceptionRecord->NumberParameters >= 2)
    {
        av_kind = ep->ExceptionRecord->ExceptionInformation[0];
        av_addr = ep->ExceptionRecord->ExceptionInformation[1];
    }
    _snprintf_s(line, sizeof line, _TRUNCATE, "crashlog  exception 0x%X at %s (%s %p) thread %u", (unsigned)code, where,
                av_kind == 0 ? "reading" : av_kind == 1 ? "writing" : "executing", (void*)av_addr, (unsigned)GetCurrentThreadId());
    g_clHost->log("%s", line);
    _snprintf_s(line, sizeof line, _TRUNCATE, "crashlog  rax=%p rbx=%p rcx=%p rdx=%p rsi=%p rdi=%p r8=%p r9=%p r12=%p r14=%p rsp=%p rbp=%p",
                (void*)c->Rax, (void*)c->Rbx, (void*)c->Rcx, (void*)c->Rdx, (void*)c->Rsi, (void*)c->Rdi, (void*)c->R8, (void*)c->R9,
                (void*)c->R12, (void*)c->R14, (void*)c->Rsp, (void*)c->Rbp);
    g_clHost->log("%s", line);

    // stack slots that point into a loaded module: return addresses and the odd data pointer
    const unsigned long long* sp = (const unsigned long long*)c->Rsp;
    int shown = 0;
    for (int i = 0; i < 1024 && shown < 16; ++i)
    {
        if (!g_clHost->readablePtr(sp + i, 8)) break;
        unsigned long long v = sp[i];
        if (!InModule(v)) continue;
        DescribeAddress(where, sizeof where, (const void*)v);
        _snprintf_s(line, sizeof line, _TRUNCATE, "crashlog   stack[%d] %s", i, where);
        g_clHost->log("%s", line);
        ++shown;
    }
    return EXCEPTION_CONTINUE_SEARCH;
}

void InstallCrashLog(const TsmHost* host)
{
    g_clHost = host;
    if (AddVectoredExceptionHandler(1, CrashLogHandler))
        host->log("%s", "crashlog  first-chance exception logger armed (first 4 hard faults are logged with module+offset)");
}
