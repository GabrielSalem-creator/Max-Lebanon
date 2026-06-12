import sys
sys.stdout = open('C:/Users/Admin/OneDrive/Documents/max/outlook_log.txt', 'w')
sys.stderr = sys.stdout

import win32gui, win32con, win32process, psutil, time
import ctypes

def find_chrome_windows():
    results = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                p = psutil.Process(pid)
                name = p.name().lower()
                if 'chrome' in name:
                    results.append((hwnd, title))
            except Exception as e:
                pass
    win32gui.EnumWindows(cb, None)
    return results

print("Searching for Chrome windows...")
wins = find_chrome_windows()
print(f"Found {len(wins)} Chrome windows:")
for h, t in wins:
    print(f"  hwnd={h} title={repr(t[:80])}")

sys.stdout.flush()

if not wins:
    print("ERROR: No Chrome windows found")
    sys.exit(1)

# Pick the first Chrome window
hwnd = wins[0][0]
print(f"\nUsing hwnd={hwnd}")

# Restore and bring to foreground
win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
time.sleep(0.3)

# Use AllowSetForegroundWindow trick
ctypes.windll.user32.AllowSetForegroundWindow(-1)
win32gui.SetForegroundWindow(hwnd)
time.sleep(1.0)

# Now use keyboard shortcut to navigate
import pyautogui, pyperclip

pyperclip.copy('https://outlook.live.com/mail/0/')
print("Clipboard set to Outlook URL")

# Click on address bar area (Chrome address bar is typically at y~38 for full height)
rect = win32gui.GetWindowRect(hwnd)
print(f"Window rect: {rect}")
x_center = (rect[0] + rect[2]) // 2
y_addr = rect[1] + 45  # address bar y position
print(f"Clicking address bar at ({x_center}, {y_addr})")
pyautogui.click(x_center, y_addr)
time.sleep(0.5)
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.3)
pyautogui.press('enter')
print("Navigation command sent!")
sys.stdout.flush()
