@echo off
set "TARGET=%~dp0run.bat"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
powershell -NoProfile -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%STARTUP%\Raqmiat.lnk');$s.TargetPath='%TARGET%';$s.WorkingDirectory='%~dp0';$s.Save()"
echo تم إعداد تشغيل رقميات عند تسجيل الدخول إلى ويندوز.
pause
