@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo   Arret du generateur de jeux d'animation...
echo.
REM Sans "-v" : le volume de la base est conserve, donc les jeux deja
REM generes - et payes - sont toujours la au prochain demarrage.
docker compose down
echo.
echo   Arrete. Les jeux generes sont conserves.
echo   Pour redemarrer : double-clic sur demarrer.bat
echo.
pause
