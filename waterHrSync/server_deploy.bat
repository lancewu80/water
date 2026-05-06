@echo off
setlocal

REM 強制 Maven 使用 JDK
set "JAVA_HOME=D:\java\jdk\openjdk-17.0.14"
set "PATH=%JAVA_HOME%\bin;%PATH%"

REM 專案目錄 = bat 所在目錄
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

set "JAR_NAME=waterHrSync.jar"
set "TARGET_JAR=%PROJECT_DIR%\target\%JAR_NAME%"
set "DEPLOY_DIR=C:\chainsea\ecp\apache-tomcat\webapps\ecp\WEB-INF\lib"

echo [DEBUG] JAVA_HOME=%JAVA_HOME%
echo [DEBUG] PROJECT_DIR=%PROJECT_DIR%

echo [DEBUG] where java
where java
echo [DEBUG] where javac
where javac

echo [DEBUG] mvn -v
call mvn -v
if errorlevel 1 goto :fail

echo [1/3] Build jar...
cd /d "%PROJECT_DIR%" || goto :fail
call mvn clean package -DskipTests
if errorlevel 1 goto :fail

echo [2/3] Copy jar...
if not exist "%TARGET_JAR%" (
  echo [ERROR] Jar not found: "%TARGET_JAR%"
  goto :fail
)

if not exist "%DEPLOY_DIR%" (
  echo [ERROR] Deploy dir not found: "%DEPLOY_DIR%"
  goto :fail
)

copy /Y "%TARGET_JAR%" "%DEPLOY_DIR%\%JAR_NAME%"
if errorlevel 1 goto :fail

echo [3/3] Deploy OK
goto :eof

:fail
echo.
echo Deploy failed.
exit /b 1