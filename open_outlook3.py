import sys, win32gui, win32con, win32process, psutil, time, ctypes
import pyautogui, pyperclip

log = open('C:/Users/Admin/OneDrive/Documents/max/outlook_log2.txt', 'w')
def p(msg):
    print(msg)
    log.write(msg + '\n')
    log.flush()

def find_chrome_windows():
    results = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                if 'chrome' in proc.name().lower():
                    results.append((hwnd, title))
            except:
                pass
    win32gui.EnumWindows(cb, None)
    return results

wins = find_chrome_windows()
p(f"Chrome windows: {[(h, t[:50]) for h,t in wins]}")

hwnd = wins[0][0]
p(f"Focusing hwnd={hwnd}")

# Restore and set foreground
win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
time.sleep(0.5)
ctypes.windll.user32.AllowSetForegroundWindow(-1)
win32gui.SetForegroundWindow(hwnd)
time.sleep(1.5)

p("Checking foreground window...")
fg = win32gui.GetForegroundWindow()
p(f"Foreground: {win32gui.GetWindowText(fg)}")

# Set clipboard
pyperclip.copy('https://outlook.live.com/mail/0/')

# Use Ctrl+L to focus address bar (Chrome shortcut)
pyautogui.hotkey('ctrl', 'l')
time.sleep(0.8)

# Select all and paste
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.3)
pyautogui.press('enter')
p("Done - Enter pressed")
log.close()
