@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo   Journal de l'application. Ctrl+C pour quitter.
echo   En cas de probleme, c'est ce texte qu'il faut copier.
echo.
docker compose logs -f --tail 100
pause
