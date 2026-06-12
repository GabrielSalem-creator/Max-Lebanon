import win32gui, win32ui, win32con
from PIL import Image
import ctypes

hwnd = 66732  # Inbox - Gabriel Salem - Outlook - Google Chrome

# Get window dimensions
rect = win32gui.GetWindowRect(hwnd)
w = rect[2] - rect[0]
h = rect[3] - rect[1]
print(f"Window size: {w}x{h}")

# Use PrintWindow to capture without focus
hwndDC = win32gui.GetWindowDC(hwnd)
mfcDC = win32ui.CreateDCFromHandle(hwndDC)
saveDC = mfcDC.CreateCompatibleDC()
saveBitmap = win32ui.CreateBitmap()
saveBitmap.CreateCompatibleBitmap(mfcDC, w, h)
saveDC.SelectObject(saveBitmap)

# PrintWindow with PW_RENDERFULLCONTENT (2) for modern Chrome
result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
print(f"PrintWindow result: {result}")

bmpinfo = saveBitmap.GetInfo()
bmpstr = saveBitmap.GetBitmapBits(True)
img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)
img.save('C:/Users/Admin/OneDrive/Documents/max/outlook_capture.png')
print(f"Saved: {img.size}")

win32gui.DeleteObject(saveBitmap.GetHandle())
saveDC.DeleteDC()
mfcDC.DeleteDC()
win32gui.ReleaseDC(hwnd, hwndDC)
