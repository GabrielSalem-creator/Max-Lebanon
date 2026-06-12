import pyautogui
import time

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.3

# Click address bar
pyautogui.click(480, 38)
time.sleep(0.5)

# Select all and type YouTube URL
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.typewrite('https://www.youtube.com', interval=0.05)
pyautogui.press('enter')
time.sleep(3)

print("Navigated to YouTube")
