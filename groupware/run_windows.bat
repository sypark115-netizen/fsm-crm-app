@echo off
chcp 65001 >nul
setlocal
title Groupware

rem ================================================================
rem  현장 그룹웨어 - Windows 원클릭 실행기
rem  1) Python 확인(없으면 자동 설치)  2) 최신 코드 다운로드
rem  3) 패키지 설치  4) 데모 데이터  5) 앱 실행 + 브라우저 열기
rem  데이터는 %USERPROFILE%\fsm-groupware\data 에 보존됩니다.
rem ================================================================

set "BASE=%USERPROFILE%\fsm-groupware"
set "ZIPURL=https://codeload.github.com/sypark115-netizen/fsm-crm-app/zip/refs/heads/claude/lightweight-groupware-platform-aus4y5"
set "GW_DATA_DIR=%BASE%\data"
if not exist "%BASE%" mkdir "%BASE%"

echo.
echo [1/5] Python 확인...
set "PY="
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul
    if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo   Python이 없어 설치합니다. 1~3분 걸립니다...
    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PY (
    echo.
    echo   [오류] Python 자동 설치에 실패했습니다.
    echo   https://www.python.org/downloads/ 에서 설치 후 다시 실행해 주세요.
    echo   설치 첫 화면에서 "Add python.exe to PATH" 를 꼭 체크하세요.
    pause
    exit /b 1
)

echo [2/5] 최신 코드 다운로드...
if exist "%BASE%\tmp" rmdir /s /q "%BASE%\tmp"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%ZIPURL%' -OutFile '%BASE%\src.zip'; Expand-Archive -Path '%BASE%\src.zip' -DestinationPath '%BASE%\tmp' -Force"
if errorlevel 1 (
    echo   [오류] 다운로드 실패. 인터넷 연결을 확인해 주세요.
    pause
    exit /b 1
)
if exist "%BASE%\app" rmdir /s /q "%BASE%\app"
for /d %%D in ("%BASE%\tmp\fsm-crm-app-*") do move "%%D\groupware" "%BASE%\app" >nul
rmdir /s /q "%BASE%\tmp"
del "%BASE%\src.zip"
cd /d "%BASE%\app"

echo [3/5] 패키지 설치 (처음 한 번은 2~5분)...
%PY% -m pip install --user --disable-pip-version-check -q streamlit sqlalchemy pandas openpyxl pillow streamlit-js-eval
if errorlevel 1 (
    echo   [오류] 패키지 설치 실패. 위 메시지를 캡처해서 보내 주세요.
    pause
    exit /b 1
)

echo [4/5] 데모 데이터 준비...
%PY% demo_data.py

echo [5/5] 앱 실행 - 잠시 후 브라우저가 열립니다.
echo.
echo   주소: http://localhost:8501
echo   로그인: A001 / M001 / W001 / W002   비밀번호: test1234
echo   종료: 이 창을 닫으면 앱도 꺼집니다.
echo.
rem headless: 첫 실행 이메일 입력 프롬프트를 건너뛰고, 브라우저는 직접 연다
start "" /min cmd /c "timeout /t 8 /nobreak >nul & start http://localhost:8501"
%PY% -m streamlit run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false
pause
