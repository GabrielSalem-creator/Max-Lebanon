import win32gui, win32con, time, ctypes
import pyautogui

log = []
def p(msg):
    print(msg)
    log.append(msg)

def find_all_windows():
    results = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                results.append((hwnd, title))
    win32gui.EnumWindows(cb, None)
    return results

wins = find_all_windows()
p("All visible windows:")
for h, t in wins:
    if 'chrome' in t.lower() or 'outlook' in t.lower() or 'mail' in t.lower():
        p(f"  {h}: {t[:80]}")

# Find Outlook/Mail Chrome window
outlook_hwnd = None
for h, t in wins:
    if ('mail' in t.lower() or 'outlook' in t.lower()) and 'chrome' in t.lower():
        outlook_hwnd = h
        p(f"Found Outlook window: {h} - {t}")
        break

if outlook_hwnd:
    win32gui.ShowWindow(outlook_hwnd, win32con.SW_RESTORE)
    time.sleep(0.3)
    ctypes.windll.user32.AllowSetForegroundWindow(-1)
    win32gui.SetForegroundWindow(outlook_hwnd)
    time.sleep(1.0)
    p(f"Foreground: {win32gui.GetWindowText(win32gui.GetForegroundWindow())}")
else:
    p("No Outlook window found - bringing MAX Chrome to front")
    # Use MAX Chrome window
    for h, t in wins:
        if 'max' in t.lower() and 'chrome' in t.lower():
            win32gui.SetForegroundWindow(h)
            time.sleep(1.0)
            break

with open('C:/Users/Admin/OneDrive/Documents/max/outlook_focus_log.txt', 'w') as f:
    f.write('\n'.join(log))
