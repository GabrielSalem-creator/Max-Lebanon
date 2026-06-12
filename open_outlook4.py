import win32gui, win32con, win32process, psutil, time, ctypes
import pyautogui, pyperclip

log = open('C:/Users/Admin/OneDrive/Documents/max/outlook_log3.txt', 'w')
def p(msg):
    print(msg)
    log.write(msg + '\n')
    log.flush()

# Use MAX Chrome window specifically
hwnd = 66732  # MAX - Google Chrome
p(f"Title: {win32gui.GetWindowText(hwnd)}")
p(f"Rect: {win32gui.GetWindowRect(hwnd)}")

# Restore and focus
win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
time.sleep(0.5)
ctypes.windll.user32.AllowSetForegroundWindow(-1)
win32gui.SetForegroundWindow(hwnd)
time.sleep(1.0)

fg = win32gui.GetForegroundWindow()
p(f"Foreground now: {win32gui.GetWindowText(fg)}")

rect = win32gui.GetWindowRect(hwnd)
p(f"Rect: {rect}")

# Click directly on address bar (y ~ 55 from top of window)
x = (rect[0] + rect[2]) // 2
y = rect[1] + 55
p(f"Clicking address bar at ({x}, {y})")
pyautogui.click(x, y)
time.sleep(0.5)

# Check if address bar is focused by pressing F6 (Chrome address bar shortcut)
pyautogui.press('f6')
time.sleep(0.5)

# Select all and paste URL
pyperclip.copy('https://outlook.live.com/mail/0/')
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.3)
pyautogui.press('enter')
p("Done!")
log.close()
