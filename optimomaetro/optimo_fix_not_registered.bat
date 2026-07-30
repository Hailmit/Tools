@echo off
setlocal EnableExtensions EnableDelayedExpansion
title OttimoCut - Diagnose, repair and start

rem ================================================================
rem HUONG DAN SU DUNG
rem
rem   Bam dup file:
rem       Tu dong sua loi, test lai tung muc, sau do mo OttimoCut.
rem
rem   Chi kiem tra, khong thay doi he thong:
rem       Repair_and_Start_OttimoCut.cmd /test
rem
rem   Sua loi va test lai:
rem       Repair_and_Start_OttimoCut.cmd /repair
rem
rem   Xem huong dan:
rem       Repair_and_Start_OttimoCut.cmd /help
rem
rem Script KHONG thay Kala.dll, KHONG xoa du lieu va KHONG tu dong
rem tat OttimoCut de tranh mat cong viec dang mo.
rem ================================================================

set "MODE=REPAIR"
if /I "%~1"=="/test" set "MODE=TEST"
if /I "%~1"=="-test" set "MODE=TEST"
if /I "%~1"=="/repair" set "MODE=REPAIR"
if /I "%~1"=="-repair" set "MODE=REPAIR"
if /I "%~1"=="/help" goto :usage
if /I "%~1"=="-help" goto :usage
if /I "%~1"=="/?" goto :usage

if not "%~1"=="" (
    if /I not "%~1"=="/test" if /I not "%~1"=="-test" if /I not "%~1"=="/repair" if /I not "%~1"=="-repair" (
        echo [ERROR] Tham so khong hop le: %~1
        goto :usage_error
    )
)

rem Repair mode needs Administrator privileges. Test mode is read-only.
if /I "%MODE%"=="REPAIR" (
    fltmc >nul 2>&1
    if errorlevel 1 (
        echo Dang yeu cau quyen Administrator...
        powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
            "Start-Process -FilePath '%~f0' -ArgumentList '/repair' -Verb RunAs"
        exit /b
    )
)

set "OTTIMO_DIR=C:\OTTIMOCUT"
set "OTTIMO_APP=%OTTIMO_DIR%\OttimoCUT.exe"
set "SCMCOM_DLL=%OTTIMO_DIR%\Univ\scmcom.dll"
set "KALA_DLL=%OTTIMO_DIR%\Kala.dll"
set "REGSVR32_32=C:\Windows\SysWOW64\regsvr32.exe"
set "REG_32=C:\Windows\SysWOW64\reg.exe"
set "PS32=C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
set /A PASS_COUNT=0
set /A WARN_COUNT=0
set /A FAIL_COUNT=0

echo.
echo ================================================================
echo  OTTIMOCUT - KIEM TRA VA SUA LOI "NOT REGISTERED"
echo ================================================================
if /I "%MODE%"=="TEST" (
    echo  Che do: TEST - chi kiem tra, khong thay doi he thong
) else (
    echo  Che do: REPAIR - sua loi va test lai tung muc
)
echo.
echo HUONG DAN NHANH:
echo  - Bam dup file de sua va mo OttimoCut.
echo  - Chay voi /test neu chi muon kiem tra.
echo  - Script khong thay Kala.dll va khong xoa du lieu.
echo ================================================================
echo.

echo CASE 1/7 - Kiem tra cac file bat buoc
if exist "%OTTIMO_APP%" (
    call :pass "Tim thay OttimoCUT.exe"
) else (
    call :fail "Khong tim thay %OTTIMO_APP%"
)

if exist "%SCMCOM_DLL%" (
    call :pass "Tim thay Univ\scmcom.dll"
) else (
    call :fail "Khong tim thay %SCMCOM_DLL%"
)

if exist "%KALA_DLL%" (
    for /f "usebackq delims=" %%V in (`powershell.exe -NoProfile -Command "(Get-Item -LiteralPath '%KALA_DLL%').VersionInfo.FileVersion"`) do set "KALA_VERSION=%%V"
    call :pass "Tim thay Kala.dll - version !KALA_VERSION!"
) else (
    call :warn "Khong tim thay %KALA_DLL%"
)
echo.

echo CASE 2/7 - Kiem tra dung bo cong cu 32-bit
if exist "%REGSVR32_32%" (
    call :pass "Tim thay SysWOW64\regsvr32.exe"
) else (
    call :fail "Khong tim thay regsvr32 32-bit"
)

if exist "%PS32%" (
    call :pass "Tim thay Windows PowerShell 32-bit"
) else (
    call :fail "Khong tim thay Windows PowerShell 32-bit"
)
echo.

echo CASE 3/7 - Kiem tra Sentinel LDK License Manager
sc.exe query hasplms | findstr /I "RUNNING" >nul
if errorlevel 1 (
    if /I "%MODE%"=="REPAIR" (
        echo [ACTION] Dang khoi dong dich vu hasplms...
        net.exe start hasplms >nul 2>&1
        sc.exe query hasplms | findstr /I "RUNNING" >nul
        if errorlevel 1 (
            call :fail "Khong khoi dong duoc dich vu hasplms"
        ) else (
            call :pass "Da khoi dong dich vu hasplms"
        )
    ) else (
        call :fail "Dich vu hasplms khong chay"
    )
) else (
    call :pass "Dich vu hasplms dang chay"
)
echo.

echo CASE 4/7 - Kiem tra Sentinel License Manager tai cong 1947
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
    "$c=New-Object Net.Sockets.TcpClient; try{$c.Connect('127.0.0.1',1947); exit 0}catch{exit 1}finally{$c.Dispose()}"
if errorlevel 1 (
    call :fail "Cong 1947 khong phan hoi"
) else (
    call :pass "Cong 1947 dang phan hoi"
)
echo.

echo CASE 5/7 - Kiem tra va dang ky SCMCOM.SCM
if /I "%MODE%"=="REPAIR" (
    if exist "%SCMCOM_DLL%" if exist "%REGSVR32_32%" (
        echo [ACTION] Dang ky lai SCMCOM 32-bit...
        "%REGSVR32_32%" /s "%SCMCOM_DLL%"
        if errorlevel 1 (
            call :fail "regsvr32 khong dang ky duoc scmcom.dll"
        ) else (
            call :pass "Lenh dang ky scmcom.dll thanh cong"
        )
    )
)

if exist "%REG_32%" (
    "%REG_32%" query "HKCR\SCMCOM.SCM" >nul 2>&1
    if errorlevel 1 (
        call :fail "Khong tim thay SCMCOM.SCM trong Registry 32-bit"
    ) else (
        call :pass "SCMCOM.SCM co trong Registry 32-bit"
    )
) else (
    call :fail "Khong co cong cu kiem tra Registry 32-bit"
)
echo.

echo CASE 6/7 - Test tao doi tuong COM that
if exist "%PS32%" (
    "%PS32%" -NoProfile -ExecutionPolicy Bypass -Command ^
        "$o=$null; try{$o=New-Object -ComObject 'SCMCOM.SCM'; if($null -eq $o){exit 2}; exit 0}catch{exit 1}finally{if($null -ne $o){[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($o)}}"
    if errorlevel 1 (
        call :fail "Windows khong tao duoc doi tuong COM SCMCOM.SCM"
    ) else (
        call :pass "Tao doi tuong COM SCMCOM.SCM thanh cong"
    )
) else (
    call :fail "Khong the test COM vi thieu PowerShell 32-bit"
)
echo.

echo CASE 7/7 - Kiem tra trang thai OttimoCut
tasklist /FI "IMAGENAME eq OttimoCUT.exe" 2>nul | findstr /I "OttimoCUT.exe" >nul
if not errorlevel 1 (
    call :warn "OttimoCut dang mo - can dong va mo lai de ap dung sua loi"
    set "APP_RUNNING=1"
) else (
    call :pass "OttimoCut hien khong chay"
    set "APP_RUNNING=0"
)
echo.

echo ================================================================
echo  KET QUA: PASS=%PASS_COUNT%  WARNING=%WARN_COUNT%  FAIL=%FAIL_COUNT%
echo ================================================================

if not "%FAIL_COUNT%"=="0" (
    echo Co muc kiem tra that bai.
    echo Hay chup anh cua so nay de tiep tuc chan doan.
    echo.
    pause
    exit /b 1
)

if /I "%MODE%"=="TEST" (
    echo Tat ca test bat buoc da PASS. He thong san sang chay OttimoCut.
    echo.
    pause
    exit /b 0
)

if "%APP_RUNNING%"=="1" (
    echo Sua loi thanh cong.
    echo Hay luu cong viec, dong OttimoCut va bam dup script mot lan nua.
) else (
    echo Sua loi va kiem tra thanh cong.
    if exist "%OTTIMO_APP%" (
        echo Dang mo OttimoCut...
        start "" "%OTTIMO_APP%"
    )
)

echo.
pause
exit /b 0

:pass
echo [PASS] %~1
set /A PASS_COUNT+=1
exit /b

:warn
echo [WARNING] %~1
set /A WARN_COUNT+=1
exit /b

:fail
echo [FAIL] %~1
set /A FAIL_COUNT+=1
exit /b

:usage
echo.
echo HUONG DAN SU DUNG
echo.
echo   %~nx0
echo       Sua loi, test lai tung case, sau do mo OttimoCut.
echo.
echo   %~nx0 /test
echo       Chi test, khong sua va khong thay doi he thong.
echo.
echo   %~nx0 /repair
echo       Dang ky lai SCMCOM, kiem tra Sentinel va mo OttimoCut.
echo.
echo   %~nx0 /help
echo       Hien huong dan nay.
echo.
echo Khi gap "Not registered": luu cong viec, dong OttimoCut, sau do
echo bam dup file nay va chon Yes khi Windows hoi quyen Administrator.
echo.
pause
exit /b 0

:usage_error
call :usage
exit /b 2
