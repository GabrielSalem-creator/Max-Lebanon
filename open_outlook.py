import win32gui, win32con, win32process, psutil, pyautogui, pyperclip, time, subprocess

# Find Chrome main windows
def find_chrome_windows():
    results = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                p = psutil.Process(pid)
                if 'chrome' in p.name().lower():
                    results.append((hwnd, win32gui.GetWindowText(hwnd)))
            except:
                pass
    win32gui.EnumWindows(cb, None)
    return results

wins = find_chrome_windows()
print("Chrome windows found:")
for h, t in wins:
    print(f"  hwnd={h} title={t[:60]}")

if wins:
    hwnd = wins[0][0]
    print(f"\nBringing hwnd={hwnd} to foreground...")
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(1)

    pyperclip.copy('https://outlook.live.com/mail/0/')
    pyautogui.hotkey('ctrl', 'l')
    time.sleep(0.6)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.2)
    pyautogui.press('enter')
    print("Navigation sent.")
else:
    print("No Chrome window found!")
