import pyautogui
import time

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.4

print("Clicking Chrome in taskbar...")
pyautogui.click(365, 524)
time.sleep(1)

print("Pressing Ctrl+L to open address bar...")
pyautogui.hotkey('ctrl', 'l')
time.sleep(0.5)

print("Navigating to YouTube search...")
pyautogui.hotkey('ctrl', 'a')
pyautogui.typewrite('youtube.com/results?search_query=how+to+make+automated+AI+videos+with+good+editing', interval=0.04)
pyautogui.press('enter')
time.sleep(5)

pyautogui.screenshot('C:/tmp/yt_ai_results.png')
print("Done! Search results loaded.")
