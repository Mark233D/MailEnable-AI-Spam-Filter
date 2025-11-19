@echo off
title SpamAnalizor - Otomatik Baslatma
color 0A

echo ===================================================
echo      SpamAnalizor Sistemi Baslatiliyor...
echo ===================================================

:: 1. Sanal Ortam Kontrolu
if not exist ".venv" (
    echo [KURULUM] Sanal ortam bulunamadi, olusturuluyor...
    python -m venv .venv
    echo [KURULUM] Gerekli kutuphaneler yukleniyor...
    call .venv\Scripts\activate
    pip install -r requirements.txt
) else (
    echo [BILGI] Sanal ortam hazir. Sistem baslatiliyor.
    call .venv\Scripts\activate
)

:: 2. Uygulamalari Baslat (API ve Watchdog)
echo.
echo 1. API Sunucusu aciliyor...
:: MyAPI klasörüne girip oradan çalıştırır
start "API_Server" cmd /k "cd MyAPI && ..\.venv\Scripts\python api_server.py"

timeout /t 3 >nul

echo 2. Watchdog aciliyor...
:: SpamAnalizor klasörüne girip oradan çalıştırır (MailPrep.py olarak düzelttim)
start "Watchdog_Agent" cmd /k "cd SpamAnalizor && ..\.venv\Scripts\python MailPrep.py"

echo.
echo [TAMAM] Sistem aktif! Pencereleri kapatana kadar calisir.
pause