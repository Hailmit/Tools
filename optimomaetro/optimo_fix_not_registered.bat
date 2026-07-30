@echo off
setlocal EnableExtensions DisableDelayedExpansion
title OttimoCut - Diagnose, repair and start safely

rem =====================================================================
rem OTTIMOCUT DIAGNOSE / REPAIR
rem
rem   Double-click:
rem       Elevate only the repair worker, verify again as the normal user,
rem       then start OttimoCut without Administrator privileges.
rem
rem   Test only:
rem       Repair_and_Start_OttimoCut.cmd /test
rem
rem   Repair:
rem       Repair_and_Start_OttimoCut.cmd /repair
rem
rem   Optional:
rem       /nopause
rem
rem Exit codes:
rem   0 = success
rem   1 = one or more checks failed
rem   2 = invalid arguments
rem   3 = elevation failed or was cancelled
rem   4 = OttimoCut could not be started or exited immediately
rem
rem The script does not replace Kala.dll, delete application data, or
rem automatically terminate OttimoCut.
rem =====================================================================

set "MODE="
set "NO_PAUSE=0"
set "INTERNAL_ELEVATED=0"
set "POST_REPAIR=0"
set "BAD_ARG="

:parse_args
if "%~1"=="" goto :args_done

if /I "%~1"=="/test" goto :arg_test
if /I "%~1"=="-test" goto :arg_test
if /I "%~1"=="/repair" goto :arg_repair
if /I "%~1"=="-repair" goto :arg_repair
if /I "%~1"=="/help" goto :usage
if /I "%~1"=="-help" goto :usage
if /I "%~1"=="/?" goto :usage
if /I "%~1"=="/nopause" goto :arg_nopause
if /I "%~1"=="/elevated" goto :arg_elevated
if /I "%~1"=="/postrepair" goto :arg_postrepair

set "BAD_ARG=%~1"
goto :usage_error

:arg_test
if defined MODE if /I not "%MODE%"=="TEST" (
    set "BAD_ARG=Khong the dung /test va /repair cung luc"
    goto :usage_error
)
set "MODE=TEST"
shift
goto :parse_args

:arg_repair
if defined MODE if /I not "%MODE%"=="REPAIR" (
    set "BAD_ARG=Khong the dung /test va /repair cung luc"
    goto :usage_error
)
set "MODE=REPAIR"
shift
goto :parse_args

:arg_nopause
set "NO_PAUSE=1"
shift
goto :parse_args

:arg_elevated
set "INTERNAL_ELEVATED=1"
shift
goto :parse_args

:arg_postrepair
set "POST_REPAIR=1"
shift
goto :parse_args

:args_done
if not defined MODE set "MODE=REPAIR"

rem ---------------------------------------------------------------------
rem Fixed application paths
rem ---------------------------------------------------------------------
set "OTTIMO_DIR=C:\OTTIMOCUT"
set "OTTIMO_APP=%OTTIMO_DIR%\OttimoCUT.exe"
set "SCMCOM_DLL=%OTTIMO_DIR%\Univ\scmcom.dll"
set "KALA_DLL=%OTTIMO_DIR%\Kala.dll"

rem ---------------------------------------------------------------------
rem Resolve trusted Windows executables with absolute paths.
rem Sysnative bypasses WOW64 redirection when this script is started by
rem a 32-bit parent process on 64-bit Windows.
rem ---------------------------------------------------------------------
set "NATIVE_SYS32=%SystemRoot%\System32"
if exist "%SystemRoot%\Sysnative\cmd.exe" set "NATIVE_SYS32=%SystemRoot%\Sysnative"

set "PS_NATIVE=%NATIVE_SYS32%\WindowsPowerShell\v1.0\powershell.exe"
set "SC_EXE=%NATIVE_SYS32%\sc.exe"
set "TASKLIST_EXE=%NATIVE_SYS32%\tasklist.exe"
set "FINDSTR_EXE=%NATIVE_SYS32%\findstr.exe"
set "TIMEOUT_EXE=%NATIVE_SYS32%\timeout.exe"

if exist "%SystemRoot%\SysWOW64\regsvr32.exe" (
    set "OS_BITS=64"
    set "REGSVR32_32=%SystemRoot%\SysWOW64\regsvr32.exe"
    set "PS32=%SystemRoot%\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
) else (
    set "OS_BITS=32"
    set "REGSVR32_32=%SystemRoot%\System32\regsvr32.exe"
    set "PS32=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
)

rem Only internal child/test processes may inherit the parent log path.
rem Normal invocations always replace any externally pre-seeded value.
if /I not "%MODE%"=="TEST" set "POST_REPAIR=0"
if "%INTERNAL_ELEVATED%"=="0" if "%POST_REPAIR%"=="0" set "OTTIMOCUT_LOG=%TEMP%\OttimoCut_Repair_%RANDOM%_%RANDOM%.log"
if not defined OTTIMOCUT_LOG set "OTTIMOCUT_LOG=%TEMP%\OttimoCut_Repair_%RANDOM%_%RANDOM%.log"
set "LOG_FILE=%OTTIMOCUT_LOG%"

>>"%LOG_FILE%" echo.
>>"%LOG_FILE%" echo =====================================================================
>>"%LOG_FILE%" echo Start: %DATE% %TIME%
>>"%LOG_FILE%" echo Script: "%~f0"
>>"%LOG_FILE%" echo Mode: %MODE%  ElevatedWorker=%INTERNAL_ELEVATED%  PostRepair=%POST_REPAIR%
>>"%LOG_FILE%" echo Windows: %OS_BITS%-bit
>>"%LOG_FILE%" echo =====================================================================

rem ---------------------------------------------------------------------
rem Repair orchestration:
rem - A normal user process starts an elevated worker and waits for it.
rem - The normal user process then runs TEST again.
rem - OttimoCut is started only by the normal user process.
rem ---------------------------------------------------------------------
if /I not "%MODE%"=="REPAIR" goto :run_main

call :is_admin
if not errorlevel 1 goto :run_main

if "%INTERNAL_ELEVATED%"=="1" goto :admin_required_error
goto :orchestrate_repair


:orchestrate_repair
echo.
echo =====================================================================
echo  OTTIMOCUT - SAFE REPAIR ORCHESTRATOR
echo =====================================================================
echo  Log: "%LOG_FILE%"
echo.
call :info "Dang yeu cau quyen Administrator cho tien trinh repair..."

call :run_elevated_worker
set "WORKER_RC=%ERRORLEVEL%"

if not "%WORKER_RC%"=="0" goto :worker_failed

call :info "Repair worker da hoan tat. Dang test lai bang quyen nguoi dung..."
echo.

call "%~f0" /test /postrepair /nopause
set "VERIFY_RC=%ERRORLEVEL%"

if not "%VERIFY_RC%"=="0" goto :post_verify_failed

call :launch_app_user
set "LAUNCH_RC=%ERRORLEVEL%"

if not "%LAUNCH_RC%"=="0" goto :launch_failed

echo.
call :info "Repair, verification va khoi dong OttimoCut da hoan tat."
echo [INFO] Log: "%LOG_FILE%"
call :maybe_pause
exit /b 0


:worker_failed
echo.
echo [ERROR] Repair worker that bai hoac UAC bi huy. Exit code: %WORKER_RC%
>>"%LOG_FILE%" echo [ERROR] Repair worker failed. Exit code: %WORKER_RC%
echo Log: "%LOG_FILE%"
call :maybe_pause
if "%WORKER_RC%"=="1223" exit /b 3
exit /b 1


:post_verify_failed
echo.
echo [ERROR] Repair da chay nhung buoc test lai van con loi.
>>"%LOG_FILE%" echo [ERROR] Post-repair verification failed. Exit code: %VERIFY_RC%
echo Log: "%LOG_FILE%"
call :maybe_pause
exit /b 1


:launch_failed
echo.
echo [ERROR] Khong mo duoc OttimoCut hoac chuong trinh thoat ngay.
>>"%LOG_FILE%" echo [ERROR] Application launch verification failed. Exit code: %LAUNCH_RC%
echo Hay mo OttimoCut bang shortcut binh thuong va xem log:
echo "%LOG_FILE%"
call :maybe_pause
exit /b 4


:admin_required_error
echo [ERROR] Repair worker khong co token Administrator.
echo Hay chay lai script va chap nhan hop thoai UAC.
>>"%LOG_FILE%" echo [ERROR] Internal repair worker is not elevated.
call :maybe_pause
exit /b 3


:run_main
set /A PASS_COUNT=0
set /A WARN_COUNT=0
set /A FAIL_COUNT=0
set "APP_RUNNING=0"

call :is_app_running
set "APP_CHECK_RC=%ERRORLEVEL%"
if "%APP_CHECK_RC%"=="0" goto :app_running_initial
if "%APP_CHECK_RC%"=="1" goto :app_not_running_initial
set "APP_RUNNING=UNKNOWN"
goto :app_state_initial_done

:app_running_initial
set "APP_RUNNING=1"
goto :app_state_initial_done

:app_not_running_initial
set "APP_RUNNING=0"

:app_state_initial_done
echo.
echo =====================================================================
echo  OTTIMOCUT - KIEM TRA VA SUA LOI COM "NOT REGISTERED"
echo =====================================================================
if /I "%MODE%"=="TEST" (
    echo  Che do: TEST - khong dang ky DLL va khong khoi dong service
) else (
    echo  Che do: REPAIR - khoi dong service va dang ky lai COM 32-bit
)
echo  Windows: %OS_BITS%-bit
echo  Log: "%LOG_FILE%"
echo =====================================================================
echo.

if "%APP_RUNNING%"=="1" (
    call :info "OttimoCut dang chay. Script se khong tat ung dung."
    if /I "%MODE%"=="REPAIR" call :info "Dang ky lai COM se bi bo qua de tranh sua khi ung dung dang mo."
)
if "%APP_RUNNING%"=="UNKNOWN" call :info "Khong xac dinh duoc trang thai OttimoCut; repair COM se bi chan an toan."

rem =====================================================================
echo CASE 1/7 - Kiem tra file va kien truc binary
rem =====================================================================
if exist "%OTTIMO_APP%" (
    call :pass "Tim thay OttimoCUT.exe"
) else (
    call :fail "Khong tim thay %OTTIMO_APP%"
)

if not exist "%SCMCOM_DLL%" goto :case1_scm_missing
call :pass "Tim thay Univ\scmcom.dll"
call :check_pe_machine "%SCMCOM_DLL%"
set "PE_RC=%ERRORLEVEL%"
if "%PE_RC%"=="0" goto :case1_scm_x86
if "%PE_RC%"=="2" goto :case1_scm_x64
if "%PE_RC%"=="3" goto :case1_scm_unknown
call :fail "Khong doc duoc PE header cua scmcom.dll"
goto :case1_scm_done

:case1_scm_x86
call :pass "scmcom.dll la binary x86/32-bit"
goto :case1_scm_done

:case1_scm_x64
call :fail "scmcom.dll la binary x64, khong phu hop COM 32-bit"
goto :case1_scm_done

:case1_scm_unknown
call :fail "Khong nhan dien duoc kien truc scmcom.dll"
goto :case1_scm_done

:case1_scm_missing
call :fail "Khong tim thay %SCMCOM_DLL%"

:case1_scm_done

if exist "%KALA_DLL%" (
    call :pass "Tim thay Kala.dll"
    call :report_file_version "%KALA_DLL%" "Kala.dll"
    if errorlevel 1 call :warn "Kala.dll khong co FileVersion hop le"
) else (
    call :warn "Khong tim thay %KALA_DLL%"
)
echo.

rem =====================================================================
echo CASE 2/7 - Kiem tra bo cong cu Windows 32-bit
rem =====================================================================
if exist "%REGSVR32_32%" (
    call :pass "Tim thay regsvr32 32-bit: %REGSVR32_32%"
) else (
    call :fail "Khong tim thay regsvr32 32-bit"
)

if exist "%PS32%" (
    call :pass "Tim thay Windows PowerShell 32-bit: %PS32%"
) else (
    call :fail "Khong tim thay Windows PowerShell 32-bit"
)

if exist "%PS_NATIVE%" (
    call :pass "Tim thay Windows PowerShell native"
) else (
    call :fail "Khong tim thay Windows PowerShell native"
)

if not exist "%SC_EXE%" goto :case2_native_tools_missing
if not exist "%TASKLIST_EXE%" goto :case2_native_tools_missing
if not exist "%FINDSTR_EXE%" goto :case2_native_tools_missing
if not exist "%TIMEOUT_EXE%" goto :case2_native_tools_missing
call :pass "Tim thay sc.exe, tasklist.exe, findstr.exe va timeout.exe native"
goto :case2_done

:case2_native_tools_missing
call :fail "Thieu mot hoac nhieu cong cu Windows native bat buoc"

:case2_done
echo.

rem =====================================================================
echo CASE 3/7 - Kiem tra Sentinel LDK License Manager
rem =====================================================================
call :service_exists
set "SERVICE_RC=%ERRORLEVEL%"
if "%SERVICE_RC%"=="2" goto :service_tool_missing
if not "%SERVICE_RC%"=="0" goto :service_missing

call :service_running
set "SERVICE_RC=%ERRORLEVEL%"
if "%SERVICE_RC%"=="2" goto :service_tool_missing
if "%SERVICE_RC%"=="0" goto :service_already_running

if /I "%MODE%"=="TEST" goto :service_not_running_test

call :action "Dang khoi dong service hasplms..."
"%SC_EXE%" start hasplms >>"%LOG_FILE%" 2>&1
call :wait_service_running 15
if errorlevel 1 (
    call :fail "Khong khoi dong duoc service hasplms trong 15 giay"
) else (
    call :pass "Da khoi dong service hasplms"
)
goto :service_case_done

:service_tool_missing
call :fail "Khong the kiem tra hasplms vi thieu sc.exe hoac findstr.exe"
goto :service_case_done

:service_missing
call :fail "Khong tim thay service hasplms"
goto :service_case_done

:service_already_running
call :pass "Service hasplms dang RUNNING"
goto :service_case_done

:service_not_running_test
call :fail "Service hasplms ton tai nhung khong RUNNING"

:service_case_done
echo.

rem =====================================================================
echo CASE 4/7 - Kiem tra Sentinel tai TCP 127.0.0.1:1947
rem =====================================================================
if not exist "%PS_NATIVE%" goto :port_no_powershell
if not exist "%TIMEOUT_EXE%" goto :port_no_powershell

call :wait_port_1947 10
if errorlevel 1 (
    call :fail "TCP 127.0.0.1:1947 khong phan hoi sau 10 giay"
) else (
    call :pass "TCP 127.0.0.1:1947 dang phan hoi"
)
goto :port_case_done

:port_no_powershell
call :fail "Khong the test TCP 1947 vi thieu PowerShell native"

:port_case_done
echo.

rem =====================================================================
echo CASE 5/7 - Dang ky va xac minh SCMCOM.SCM 32-bit
rem =====================================================================
if /I not "%MODE%"=="REPAIR" goto :case5_check_registry
if "%APP_RUNNING%"=="1" goto :case5_app_running
if "%APP_RUNNING%"=="UNKNOWN" goto :case5_app_unknown
if not exist "%SCMCOM_DLL%" goto :case5_missing_dll
if not exist "%REGSVR32_32%" goto :case5_missing_regsvr
if not exist "%PS_NATIVE%" goto :case5_missing_native_ps

call :action "Dang ky lai SCMCOM 32-bit voi timeout 20 giay..."
call :register_com_with_timeout
set "REGSVR_RC=%ERRORLEVEL%"
if "%REGSVR_RC%"=="0" goto :case5_register_ok
if "%REGSVR_RC%"=="124" goto :case5_register_timeout
call :fail "regsvr32 khong dang ky duoc scmcom.dll"
call :detail "regsvr32 exit code: %REGSVR_RC%"
goto :case5_check_registry

:case5_register_ok
call :pass "DllRegisterServer cua scmcom.dll tra ve thanh cong"
goto :case5_check_registry

:case5_register_timeout
call :fail "Dang ky scmcom.dll bi timeout sau 20 giay"
goto :case5_check_registry

:case5_app_running
call :fail "Bo qua dang ky COM vi OttimoCut dang chay; hay luu, dong ung dung va chay lai"
goto :case5_check_registry

:case5_app_unknown
call :fail "Bo qua dang ky COM vi khong xac dinh duoc trang thai OttimoCut"
goto :case5_check_registry

:case5_missing_dll
call :fail "Bo qua dang ky COM vi thieu scmcom.dll"
goto :case5_check_registry

:case5_missing_regsvr
call :fail "Bo qua dang ky COM vi thieu regsvr32 32-bit"
goto :case5_check_registry

:case5_missing_native_ps
call :fail "Bo qua dang ky COM vi thieu PowerShell native de dat timeout"
goto :case5_check_registry

:case5_check_registry
if not exist "%PS32%" goto :case5_no_ps32

call :check_com_registry
set "COM_REG_RC=%ERRORLEVEL%"

if "%COM_REG_RC%"=="0" (
    call :pass "Registry COM 32-bit tro dung den scmcom.dll"
) else (
    call :fail "Registry COM 32-bit khong hop le hoac tro sai DLL"
)
goto :case5_done

:case5_no_ps32
call :fail "Khong the xac minh Registry COM 32-bit vi thieu PowerShell 32-bit"

:case5_done
echo.

rem =====================================================================
echo CASE 6/7 - Test khoi tao doi tuong COM voi timeout
rem =====================================================================
if not exist "%PS32%" goto :case6_no_ps32
if not exist "%PS_NATIVE%" goto :case6_no_native_ps

call :test_com_with_timeout
set "COM_TEST_RC=%ERRORLEVEL%"

if "%COM_TEST_RC%"=="0" goto :case6_ok
if "%COM_TEST_RC%"=="124" goto :case6_timeout

call :fail "Khong tao duoc doi tuong COM SCMCOM.SCM"
goto :case6_done

:case6_ok
call :pass "Tao va release doi tuong COM SCMCOM.SCM thanh cong"
goto :case6_done

:case6_timeout
call :fail "Khoi tao COM SCMCOM.SCM bi timeout sau 15 giay"
goto :case6_done

:case6_no_ps32
call :fail "Khong the test COM vi thieu PowerShell 32-bit"
goto :case6_done

:case6_no_native_ps
call :fail "Khong the dat timeout COM vi thieu PowerShell native"

:case6_done
echo.

rem =====================================================================
echo CASE 7/7 - Kiem tra trang thai OttimoCut
rem =====================================================================
call :is_app_running
set "APP_CHECK_RC=%ERRORLEVEL%"
if "%APP_CHECK_RC%"=="0" goto :case7_running
if "%APP_CHECK_RC%"=="1" goto :case7_not_running
call :fail "Khong xac dinh duoc trang thai OttimoCut vi thieu cong cu he thong"
goto :case7_done

:case7_running
call :warn "OttimoCut dang chay"
goto :case7_done

:case7_not_running
call :pass "OttimoCut hien khong chay"

:case7_done
echo.

echo =====================================================================
echo  KET QUA: PASS=%PASS_COUNT%  WARNING=%WARN_COUNT%  FAIL=%FAIL_COUNT%
echo =====================================================================
>>"%LOG_FILE%" echo RESULT: PASS=%PASS_COUNT% WARNING=%WARN_COUNT% FAIL=%FAIL_COUNT%

if not "%FAIL_COUNT%"=="0" goto :main_failed
if /I "%MODE%"=="TEST" goto :test_succeeded
goto :repair_succeeded


:main_failed
echo Co muc kiem tra that bai.
echo Xem chi tiet tai:
echo "%LOG_FILE%"
call :maybe_pause
exit /b 1


:test_succeeded
if "%POST_REPAIR%"=="1" (
    echo Test sau repair da PASS.
) else (
    echo Tat ca test bat buoc da PASS.
)
echo Luu y: COM test co the khoi tao cache/log cua thanh phan COM.
call :maybe_pause
exit /b 0


:repair_succeeded
echo Repair va kiem tra trong tien trinh Administrator da PASS.
if "%INTERNAL_ELEVATED%"=="1" (
    echo Cua so thuong se test lai va mo OttimoCut khong elevated.
) else (
    echo Script khong mo OttimoCut tu cua so Administrator.
    echo Hay mo bang shortcut binh thuong de tranh loi mapped drive va ACL.
)
call :maybe_pause
exit /b 0


rem =====================================================================
rem Subroutines
rem =====================================================================

:is_admin
if not exist "%PS_NATIVE%" exit /b 1
"%PS_NATIVE%" -NoProfile -ExecutionPolicy Bypass -Command ^
    "$p=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent()); if($p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){exit 0}else{exit 1}" >nul 2>&1
exit /b %ERRORLEVEL%


:run_elevated_worker
if not exist "%PS_NATIVE%" exit /b 3
set "__OTTIMO_SELF=%~f0"
set "__OTTIMO_ARGS=/repair /elevated /nopause"

"%PS_NATIVE%" -NoProfile -ExecutionPolicy Bypass -Command ^
    "try{$p=Start-Process -FilePath $env:__OTTIMO_SELF -ArgumentList $env:__OTTIMO_ARGS -Verb RunAs -Wait -PassThru -ErrorAction Stop; exit $p.ExitCode}catch{Write-Host ('[ERROR] '+$_.Exception.Message); exit 1223}"

set "__ELEVATE_RC=%ERRORLEVEL%"
set "__OTTIMO_SELF="
set "__OTTIMO_ARGS="
exit /b %__ELEVATE_RC%


:is_app_running
if not exist "%TASKLIST_EXE%" exit /b 2
if not exist "%FINDSTR_EXE%" exit /b 2
"%TASKLIST_EXE%" /FI "IMAGENAME eq OttimoCUT.exe" /NH 2>nul | "%FINDSTR_EXE%" /I /B /C:"OttimoCUT.exe" >nul
exit /b %ERRORLEVEL%


:launch_app_user
if not exist "%OTTIMO_APP%" exit /b 2

call :is_app_running
set "__APP_RC=%ERRORLEVEL%"
if "%__APP_RC%"=="0" goto :launch_app_already_running
if not "%__APP_RC%"=="1" exit /b 5

call :info "Dang mo OttimoCut voi working directory %OTTIMO_DIR%..."
start "" /D "%OTTIMO_DIR%" "%OTTIMO_APP%"
if errorlevel 1 exit /b 3

call :wait_app_running 10
if errorlevel 1 exit /b 4

call :info "OttimoCut da khoi dong bang quyen nguoi dung thuong."
exit /b 0

:launch_app_already_running
call :info "OttimoCut da dang chay; khong mo them instance."
exit /b 0


:wait_app_running
set /A __WAIT_APP=%~1

:wait_app_loop
call :is_app_running
set "__APP_RC=%ERRORLEVEL%"
if "%__APP_RC%"=="0" exit /b 0
if "%__APP_RC%"=="2" exit /b 2
if %__WAIT_APP% LEQ 0 exit /b 1
"%TIMEOUT_EXE%" /t 1 /nobreak >nul 2>&1
set /A __WAIT_APP-=1
goto :wait_app_loop


:service_exists
if not exist "%SC_EXE%" exit /b 2
"%SC_EXE%" query hasplms >nul 2>&1
exit /b %ERRORLEVEL%


:service_running
if not exist "%SC_EXE%" exit /b 2
if not exist "%FINDSTR_EXE%" exit /b 2
"%SC_EXE%" query hasplms 2>nul | "%FINDSTR_EXE%" /R /C:"STATE *: *4" >nul
exit /b %ERRORLEVEL%


:wait_service_running
set /A __WAIT_SERVICE=%~1

:wait_service_loop
call :service_running
set "__SERVICE_RC=%ERRORLEVEL%"
if "%__SERVICE_RC%"=="0" exit /b 0
if "%__SERVICE_RC%"=="2" exit /b 2
if %__WAIT_SERVICE% LEQ 0 exit /b 1
"%TIMEOUT_EXE%" /t 1 /nobreak >nul 2>&1
set /A __WAIT_SERVICE-=1
goto :wait_service_loop


:test_port_1947
if not exist "%PS_NATIVE%" exit /b 1
"%PS_NATIVE%" -NoProfile -ExecutionPolicy Bypass -Command ^
    "$c=New-Object Net.Sockets.TcpClient; try{$a=$c.BeginConnect('127.0.0.1',1947,$null,$null); if(-not $a.AsyncWaitHandle.WaitOne(1000,$false)){exit 2}; $c.EndConnect($a); exit 0}catch{exit 1}finally{$c.Close()}" >nul 2>&1
exit /b %ERRORLEVEL%


:wait_port_1947
if not exist "%TIMEOUT_EXE%" exit /b 2
set /A __WAIT_PORT=%~1

:wait_port_loop
call :test_port_1947
if not errorlevel 1 exit /b 0
if %__WAIT_PORT% LEQ 0 exit /b 1
"%TIMEOUT_EXE%" /t 1 /nobreak >nul 2>&1
set /A __WAIT_PORT-=1
goto :wait_port_loop


:check_pe_machine
set "__PE_FILE=%~1"
"%PS_NATIVE%" -NoProfile -ExecutionPolicy Bypass -Command ^
    "$rc=4;$fs=$null;$br=$null;try{$fs=[IO.File]::OpenRead($env:__PE_FILE);$br=New-Object IO.BinaryReader($fs);$fs.Position=0x3c;$pe=$br.ReadInt32();$fs.Position=$pe+4;$m=$br.ReadUInt16();if($m -eq 0x14c){$rc=0}elseif($m -eq 0x8664){$rc=2}else{$rc=3}}catch{$rc=4}finally{if($br){$br.Close()}elseif($fs){$fs.Close()}};exit $rc" >nul 2>&1
set "__PE_RC=%ERRORLEVEL%"
set "__PE_FILE="
exit /b %__PE_RC%


:report_file_version
set "__VER_FILE=%~1"
set "__VER_LABEL=%~2"
set "__VER_OUT=%TEMP%\OttimoCut_ver_%RANDOM%_%RANDOM%.tmp"

"%PS_NATIVE%" -NoProfile -ExecutionPolicy Bypass -Command ^
    "try{$v=(Get-Item -LiteralPath $env:__VER_FILE -ErrorAction Stop).VersionInfo.FileVersion;if([string]::IsNullOrWhiteSpace($v)){Write-Output ('[DETAIL] '+$env:__VER_LABEL+': FileVersion rong');exit 2};Write-Output ('[DETAIL] '+$env:__VER_LABEL+' version: '+$v);exit 0}catch{Write-Output ('[DETAIL] '+$_.Exception.Message);exit 1}" >"%__VER_OUT%" 2>&1

set "__VER_RC=%ERRORLEVEL%"
if exist "%__VER_OUT%" (
    type "%__VER_OUT%"
    type "%__VER_OUT%" >>"%LOG_FILE%"
    del /q "%__VER_OUT%" >nul 2>&1
)
set "__VER_FILE="
set "__VER_LABEL="
set "__VER_OUT="
exit /b %__VER_RC%


:register_com_with_timeout
set "__REGSVR_OUT=%TEMP%\OttimoCut_regsvr_%RANDOM%_%RANDOM%.tmp"

"%PS_NATIVE%" -NoProfile -ExecutionPolicy Bypass -Command ^
    "$psi=New-Object Diagnostics.ProcessStartInfo;$psi.FileName=$env:REGSVR32_32;$psi.Arguments='/s '+[char]34+$env:SCMCOM_DLL+[char]34;$psi.WorkingDirectory=$env:OTTIMO_DIR+'\Univ';$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$p=New-Object Diagnostics.Process;$p.StartInfo=$psi;try{if(-not $p.Start()){Write-Output '[DETAIL] Cannot start regsvr32';exit 3};if(-not $p.WaitForExit(20000)){try{$p.Kill()}catch{};Write-Output '[DETAIL] regsvr32 timeout';exit 124};Write-Output ('[DETAIL] regsvr32 exit code: '+$p.ExitCode);exit $p.ExitCode}catch{Write-Output ('[DETAIL] regsvr32 error: '+$_.Exception.Message);exit 4}" >"%__REGSVR_OUT%" 2>&1

set "__REGSVR_RC=%ERRORLEVEL%"
if exist "%__REGSVR_OUT%" (
    type "%__REGSVR_OUT%"
    type "%__REGSVR_OUT%" >>"%LOG_FILE%"
    del /q "%__REGSVR_OUT%" >nul 2>&1
)
set "__REGSVR_OUT="
exit /b %__REGSVR_RC%


:check_com_registry
set "__REG_OUT=%TEMP%\OttimoCut_registry_%RANDOM%_%RANDOM%.tmp"

"%PS32%" -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';try{$root=[Microsoft.Win32.Registry]::ClassesRoot;$p=$root.OpenSubKey('SCMCOM.SCM\CLSID');if($null -eq $p){Write-Output '[DETAIL] Missing HKCR\SCMCOM.SCM\CLSID';exit 10};$clsid=[string]$p.GetValue('');$p.Close();if([string]::IsNullOrWhiteSpace($clsid)){Write-Output '[DETAIL] ProgID CLSID is empty';exit 11};Write-Output ('[DETAIL] Effective CLSID: '+$clsid);$k=$root.OpenSubKey(('CLSID\'+$clsid+'\InprocServer32'));if($null -eq $k){Write-Output '[DETAIL] Missing effective InprocServer32';exit 12};$raw=[string]$k.GetValue('');$k.Close();if([string]::IsNullOrWhiteSpace($raw)){Write-Output '[DETAIL] InprocServer32 is empty';exit 13};$raw=[Environment]::ExpandEnvironmentVariables($raw).Trim().Trim([char]34);Write-Output ('[DETAIL] Effective InprocServer32: '+$raw);if(-not (Test-Path -LiteralPath $raw -PathType Leaf)){Write-Output '[DETAIL] Registered COM DLL does not exist';exit 14};$actual=(Get-Item -LiteralPath $raw).FullName;$expected=(Get-Item -LiteralPath $env:SCMCOM_DLL).FullName;Write-Output ('[DETAIL] Expected InprocServer32: '+$expected);if(-not [string]::Equals($actual,$expected,[StringComparison]::OrdinalIgnoreCase)){exit 15};exit 0}catch{Write-Output ('[DETAIL] Registry check error: '+$_.Exception.Message);exit 20}" >"%__REG_OUT%" 2>&1

set "__REG_RC=%ERRORLEVEL%"
if exist "%__REG_OUT%" (
    type "%__REG_OUT%"
    type "%__REG_OUT%" >>"%LOG_FILE%"
    del /q "%__REG_OUT%" >nul 2>&1
)
set "__REG_OUT="
exit /b %__REG_RC%


:test_com_with_timeout
set "__COM_OUT=%TEMP%\OttimoCut_com_%RANDOM%_%RANDOM%.tmp"
set "__COM_CODE=$o=$null;try{$o=New-Object -ComObject 'SCMCOM.SCM' -ErrorAction Stop;if($null -eq $o){Write-Output 'COM returned null';exit 2};Write-Output 'COM object created successfully';exit 0}catch{Write-Output ('COM error: '+$_.Exception.Message);exit 1}finally{if($null -ne $o){try{[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($o)}catch{}}}"

"%PS_NATIVE%" -NoProfile -ExecutionPolicy Bypass -Command ^
    "$code=$env:__COM_CODE;$enc=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($code));$psi=New-Object Diagnostics.ProcessStartInfo;$psi.FileName=$env:PS32;$psi.Arguments='-NoProfile -ExecutionPolicy Bypass -EncodedCommand '+$enc;$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true;$p=New-Object Diagnostics.Process;$p.StartInfo=$psi;if(-not $p.Start()){Write-Output '[DETAIL] Cannot start 32-bit PowerShell';exit 3};if(-not $p.WaitForExit(15000)){try{$p.Kill()}catch{};Write-Output '[DETAIL] COM activation timeout';exit 124};$out=$p.StandardOutput.ReadToEnd();$err=$p.StandardError.ReadToEnd();if($out){Write-Output ('[DETAIL] '+$out.Trim())};if($err){Write-Output ('[DETAIL] '+$err.Trim())};exit $p.ExitCode" >"%__COM_OUT%" 2>&1

set "__COM_RC=%ERRORLEVEL%"
if exist "%__COM_OUT%" (
    type "%__COM_OUT%"
    type "%__COM_OUT%" >>"%LOG_FILE%"
    del /q "%__COM_OUT%" >nul 2>&1
)
set "__COM_CODE="
set "__COM_OUT="
exit /b %__COM_RC%


:pass
echo [PASS] %~1
>>"%LOG_FILE%" echo [PASS] %~1
set /A PASS_COUNT+=1
exit /b 0


:warn
echo [WARNING] %~1
>>"%LOG_FILE%" echo [WARNING] %~1
set /A WARN_COUNT+=1
exit /b 0


:fail
echo [FAIL] %~1
>>"%LOG_FILE%" echo [FAIL] %~1
set /A FAIL_COUNT+=1
exit /b 0


:action
echo [ACTION] %~1
>>"%LOG_FILE%" echo [ACTION] %~1
exit /b 0


:detail
echo [DETAIL] %~1
>>"%LOG_FILE%" echo [DETAIL] %~1
exit /b 0


:info
echo [INFO] %~1
>>"%LOG_FILE%" echo [INFO] %~1
exit /b 0


:maybe_pause
if "%NO_PAUSE%"=="1" exit /b 0
echo.
pause
exit /b 0


:usage
echo.
echo HUONG DAN SU DUNG
echo.
echo   %~nx0
echo       Repair, test lai bang quyen user, sau do mo OttimoCut.
echo.
echo   %~nx0 /test
echo       Chi test; khong dang ky DLL va khong khoi dong service.
echo.
echo   %~nx0 /repair
echo       Chay repair co UAC, test lai va mo OttimoCut khong elevated.
echo.
echo   %~nx0 /test /nopause
echo       Phu hop automation, deployment hoac remote support.
echo.
echo Khi OttimoCut dang mo, script se khong tu dong tat ung dung va
echo se khong dang ky lai COM. Hay luu cong viec, dong OttimoCut va chay lai.
echo.
call :maybe_pause
exit /b 0


:usage_error
echo.
echo [ERROR] Tham so khong hop le: "%BAD_ARG%"
goto :usage_error_body

:usage_error_body
echo Dung: %~nx0 [/test ^| /repair] [/nopause]
echo.
call :maybe_pause
exit /b 2
