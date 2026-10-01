"""Drive the game for testing: launch through the Republic Mod Loader, take
DPI-aware screenshots of the primary monitor, click and type. Windows only.

    python tools/gamectl.py launch            # RepublicModLoader.exe -launch
    python tools/gamectl.py shot out.png      # screenshot (primary monitor, physical pixels)
    python tools/gamectl.py click X Y         # left click at physical pixel
    python tools/gamectl.py key ESC | type "text"
    python tools/gamectl.py procs             # list steam/game/loader processes
    python tools/gamectl.py log [N]           # tail of rml-runtime.log
"""
import ctypes
import os
import subprocess
import sys
import time

RML_DIR = os.path.join(os.environ.get('WRSR_WORKSHOP', r'C:\Program Files (x86)\Steam\steamapps\workshop\content\784150').rstrip('/\\'), '3787969749')
RML_EXE = os.path.join(RML_DIR, 'RepublicModLoader.exe')
RML_LOG = os.path.join(RML_DIR, 'rml', 'logs', 'rml-runtime.log')

user32 = ctypes.windll.user32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:  # noqa: BLE001
    user32.SetProcessDPIAware()

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002
VK = {'ESC': 0x1B, 'ENTER': 0x0D, 'TAB': 0x09, 'SPACE': 0x20, 'BACK': 0x08, 'F1': 0x70, 'F5': 0x74, 'F9': 0x78,
      'UP': 0x26, 'DOWN': 0x28, 'LEFT': 0x25, 'RIGHT': 0x27, 'PGUP': 0x21, 'PGDN': 0x22, 'HOME': 0x24, 'END': 0x23}


def screen_size():
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def shot(path):
    from PIL import ImageGrab
    w, h = screen_size()
    im = ImageGrab.grab(bbox=(0, 0, w, h), all_screens=True)
    im.save(path)
    return im


def move(x, y):
    user32.SetCursorPos(int(x), int(y))


def click(x, y, button='left', hold=0.06):
    move(x, y)
    time.sleep(0.05)
    down, up = (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP) if button == 'left' else (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP)
    user32.mouse_event(down, 0, 0, 0, 0)
    time.sleep(hold)
    user32.mouse_event(up, 0, 0, 0, 0)


def wheel(x, y, clicks):
    move(x, y)
    user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, int(clicks * 120), 0)


def key(name, hold=0.05):
    vk = VK.get(name.upper())
    if vk is None:
        vk = user32.VkKeyScanW(ord(name)) & 0xFF
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(hold)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def type_text(text, delay=0.03):
    for ch in text:
        key(ch)
        time.sleep(delay)


def procs():
    out = subprocess.run(['tasklist', '/fi', 'imagename eq SOVIET64.exe'], capture_output=True, text=True).stdout
    out += subprocess.run(['tasklist', '/fi', 'imagename eq RepublicModLoader.exe'], capture_output=True, text=True).stdout
    out += subprocess.run(['tasklist', '/fi', 'imagename eq steam.exe'], capture_output=True, text=True).stdout
    return '\n'.join(l for l in out.splitlines() if '.exe' in l)


def foreground_title():
    hwnd = user32.GetForegroundWindow()
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    rect = ctypes.wintypes.RECT() if hasattr(ctypes, 'wintypes') else None
    return buf.value


def launch():
    subprocess.Popen([RML_EXE, '-launch'], cwd=RML_DIR)


def log_tail(n=40):
    try:
        lines = open(RML_LOG, 'r', encoding='utf-8', errors='replace').read().splitlines()
    except OSError as e:
        return str(e)
    return '\n'.join(lines[-n:])


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'procs'
    if cmd == 'launch':
        launch(); print('launched')
    elif cmd == 'shot':
        im = shot(sys.argv[2]); print(im.size, sys.argv[2])
    elif cmd == 'click':
        click(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else 'left'); print('clicked')
    elif cmd == 'key':
        key(sys.argv[2]); print('key', sys.argv[2])
    elif cmd == 'type':
        type_text(sys.argv[2]); print('typed')
    elif cmd == 'wheel':
        wheel(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])); print('wheel')
    elif cmd == 'procs':
        print(procs()); print('foreground:', foreground_title())
    elif cmd == 'log':
        print(log_tail(int(sys.argv[2]) if len(sys.argv) > 2 else 40))
