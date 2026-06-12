@echo off
cd /d "C:\Users\Admin\OneDrive\Documents\max"

:restart
taskkill /F /IM cloudflared.exe >nul 2>&1

start "MAX Server" /min python main.py
timeout /t 4 /nobreak >nul
start "MAX Tunnel" /min "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --protocol http2 --config "C:\Users\Admin\.cloudflared\config.yml" run max

:watch
timeout /t 30 /nobreak >nul
tasklist /FI "IMAGENAME eq cloudflared.exe" 2>nul | find /I "cloudflared.exe" >nul || goto restart
goto watch
