@echo off
title SpamAnalizor - Windows Servis Kurulumu
color 1F

echo ===================================================
echo      SpamAnalizor Servis Kurulum Sihirbazi
echo ===================================================

:: Yonetici hakki kontrolu
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [HATA] Lutfen bu dosyaya sag tiklayip "Yonetici olarak calistir" deyin.
    pause
    exit
)

:: NSSM kontrolu
if not exist "nssm.exe" (
    echo [HATA] nssm.exe bulunamadi!
    echo Lutfen nssm.exe dosyasini indirip bu klasore atin.
    pause
    exit
)

set BASE_DIR=%~dp0
set PYTHON_EXE=%BASE_DIR%.venv\Scripts\python.exe

:: --- API SERVISI KURULUMU ---
echo [1/2] API Servisi kuruluyor...
nssm install SpamFilterAPI "%PYTHON_EXE%" "%BASE_DIR%MyAPI\api_server.py"
nssm set SpamFilterAPI AppDirectory "%BASE_DIR%MyAPI"
nssm set SpamFilterAPI Description "MailEnable Spam Analiz API"
nssm start SpamFilterAPI

:: --- WATCHDOG SERVISI KURULUMU ---
echo [2/2] Watchdog Servisi kuruluyor...
:: Burada agent_entry.py yerine MailPrep.py yazdım
nssm install SpamFilterWatchdog "%PYTHON_EXE%" "%BASE_DIR%SpamAnalizor\MailPrep.py"
nssm set SpamFilterWatchdog AppDirectory "%BASE_DIR%SpamAnalizor"
nssm set SpamFilterWatchdog Description "MailEnable Dosya Takip Ajanı"
nssm start SpamFilterWatchdog

echo.
echo [TAMAM] Servisler basariyla kuruldu ve baslatildi!
pause