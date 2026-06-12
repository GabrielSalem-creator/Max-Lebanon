import win32gui, win32con, time, ctypes
import pyautogui

# Bring Outlook window to front
hwnd = 66732  # Mail - Gabriel Salem - Outlook - Google Chrome
win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
time.sleep(0.5)
ctypes.windll.user32.AllowSetForegroundWindow(-1)
win32gui.SetForegroundWindow(hwnd)
time.sleep(1.5)

fg = win32gui.GetWindowText(win32gui.GetForegroundWindow())
print(f"Foreground: {fg}")

# Take screenshot immediately
import PIL.ImageGrab
img = PIL.ImageGrab.grab()
img.save('C:/Users/Admin/OneDrive/Documents/max/outlook_screen.png')
print(f"Screenshot saved: {img.size}")
