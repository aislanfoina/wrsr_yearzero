import ctypes, ctypes.wintypes as w, subprocess, time, sys
u=ctypes.windll.user32
def game_pids():
    out=subprocess.run(['tasklist','/fi','imagename eq SOVIET64.exe','/fo','csv','/nh'],capture_output=True,text=True).stdout
    return [int(l.split('","')[1]) for l in out.splitlines() if 'SOVIET64' in l]
def snapshot(pids):
    res=[]
    @ctypes.WINFUNCTYPE(ctypes.c_bool, w.HWND, w.LPARAM)
    def cb(h,l):
        pid=w.DWORD(); u.GetWindowThreadProcessId(h,ctypes.byref(pid))
        if pid.value in pids:
            buf=ctypes.create_unicode_buffer(128); u.GetWindowTextW(h,buf,128); r=w.RECT(); u.GetWindowRect(h,ctypes.byref(r))
            res.append((hex(h),buf.value[:30],int(u.IsWindowVisible(h)),int(u.IsIconic(h)),(r.left,r.top,r.right,r.bottom)))
        return True
    u.EnumWindows(cb,0); return res
def fg():
    h=u.GetForegroundWindow(); buf=ctypes.create_unicode_buffer(128); u.GetWindowTextW(h,buf,128); return buf.value[:30]
last=None; t0=time.time(); dur=float(sys.argv[1]) if len(sys.argv)>1 else 120
while time.time()-t0<dur:
    pids=game_pids(); s=(tuple(snapshot(pids)),fg(),tuple(pids))
    if s!=last:
        print('%6.1fs pids=%s fg=%r windows=%s'%(time.time()-t0,s[2],s[1],list(s[0])),flush=True); last=s
    time.sleep(1)
print('done')
