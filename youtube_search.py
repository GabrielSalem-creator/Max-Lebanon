import pyautogui
import time
import subprocess

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

print("Step 1: Opening Chrome and going to YouTube...")
# Click the address bar (approximate position)
pyautogui.click(480, 38)
time.sleep(0.5)

# Select all and type YouTube URL
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.3)
pyautogui.typewrite('https://www.youtube.com', interval=0.05)
pyautogui.press('enter')
time.sleep(3)

print("Step 2: Taking screenshot after navigation...")
pyautogui.screenshot('C:/tmp/yt_loaded.png')

print("Step 3: Clicking the YouTube search bar...")
# YouTube search bar is usually around x=480, y=55 on a 1280x720 screen
time.sleep(2)
pyautogui.click(480, 55)
time.sleep(0.5)

print("Step 4: Typing search query...")
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.typewrite('viral cool animations 2024', interval=0.08)
time.sleep(0.5)
pyautogui.press('enter')
time.sleep(3)

print("Step 5: Taking final screenshot...")
pyautogui.screenshot('C:/tmp/yt_results.png')
print("Done!")
