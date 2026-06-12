import win32gui, win32con, win32process, psutil, time, ctypes
from PIL import ImageGrab

# Re-find the Outlook Chrome window
def find_all():
    results = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                results.append((hwnd, title))
    win32gui.EnumWindows(cb, None)
    return results

wins = find_all()
outlook_hwnd = None
for h, t in wins:
    if ('mail' in t.lower() or 'outlook' in t.lower()) and 'chrome' in t.lower():
        outlook_hwnd = h
        print(f"Found Outlook: hwnd={h} title={t[:60]}")
        break

if not outlook_hwnd:
    print("Outlook Chrome window not found. All windows:")
    for h, t in wins:
        if 'chrome' in t.lower():
            print(f"  {h}: {t[:80]}")
    # take screenshot anyway
else:
    win32gui.ShowWindow(outlook_hwnd, win32con.SW_RESTORE)
    time.sleep(0.3)
    ctypes.windll.user32.AllowSetForegroundWindow(-1)
    try:
        win32gui.SetForegroundWindow(outlook_hwnd)
        time.sleep(1.5)
        print(f"Foreground: {win32gui.GetWindowText(win32gui.GetForegroundWindow())}")
    except Exception as e:
        print(f"SetForegroundWindow error: {e}")

img = ImageGrab.grab()
img.save('C:/Users/Admin/OneDrive/Documents/max/outlook_screen.png')
print(f"Screenshot: {img.size}")
