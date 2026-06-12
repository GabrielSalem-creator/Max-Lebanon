import pyautogui
import time

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.4

print("Focusing Chrome via taskbar click...")
# Click Chrome icon in taskbar (bottom of screen)
pyautogui.click(365, 524)
time.sleep(1)

print("Using Ctrl+L to focus address bar...")
pyautogui.hotkey('ctrl', 'l')
time.sleep(0.5)

print("Typing YouTube URL...")
pyautogui.hotkey('ctrl', 'a')
pyautogui.typewrite('youtube.com', interval=0.06)
pyautogui.press('enter')
time.sleep(4)

pyautogui.screenshot('C:/tmp/yt_step1.png')
print("YouTube loaded. Pressing Ctrl+L for search bar...")

# Focus YouTube search with keyboard
pyautogui.hotkey('ctrl', 'l')
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'a')
pyautogui.typewrite('youtube.com/results?search_query=viral+cool+animations+2024', interval=0.04)
pyautogui.press('enter')
time.sleep(4)

pyautogui.screenshot('C:/tmp/yt_step2.png')
print("Search results loaded!")
