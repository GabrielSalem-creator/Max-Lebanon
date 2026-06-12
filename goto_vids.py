import pyautogui
import time

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.4

# Chrome is already active - open new tab
print("Opening new Chrome tab...")
pyautogui.hotkey('ctrl', 't')
time.sleep(1.5)

print("Navigating to Google Vids...")
pyautogui.typewrite('https://docs.google.com/videos/create?usp=vids_alc&authuser=0', interval=0.03)
pyautogui.press('enter')
time.sleep(6)

pyautogui.screenshot('C:/tmp/vids_01.png')
print("Screenshot saved.")
