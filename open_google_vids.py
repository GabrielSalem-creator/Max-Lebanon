import pyautogui
import time

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

print("Clicking Chrome in taskbar...")
pyautogui.click(365, 524)
time.sleep(1)

print("Opening Google Vids URL...")
pyautogui.hotkey('ctrl', 'l')
time.sleep(0.5)
pyautogui.hotkey('ctrl', 'a')
pyautogui.typewrite('https://docs.google.com/videos/create?usp=vids_alc&authuser=0', interval=0.04)
pyautogui.press('enter')
time.sleep(5)

pyautogui.screenshot('C:/tmp/google_vids_loaded.png')
print("Screenshot saved: C:/tmp/google_vids_loaded.png")
