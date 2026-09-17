@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo   Test de la cle d'API, telle que l'application la lit.
echo.

docker version >nul 2>&1
if errorlevel 1 (
  echo   [ARRET] Docker Desktop n'est pas demarre. Ouvre-le et attends
  echo   que la baleine passe au vert, puis relance ce fichier.
  echo.
  pause
  exit /b 1
)

REM --no-deps : le diagnostic ne touche pas a la base, inutile de la demarrer.
docker compose run --rm --no-deps app python -m scripts.tester_cle

echo.
pause
