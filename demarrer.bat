@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Generateur de jeux d'animation

echo.
echo   ================================================
echo     Generateur de jeux d'animation
echo   ================================================
echo.

REM --- 1. Docker Desktop tourne-t-il ? ---------------------------------
REM "docker version" interroge le demon, pas seulement le programme :
REM c'est ce qui distingue "Docker installe" de "Docker demarre".
docker version >nul 2>&1
if errorlevel 1 (
  echo   [ARRET] Docker Desktop n'est pas demarre.
  echo.
  echo   Ouvre Docker Desktop depuis le menu Demarrer, attends que la
  echo   petite baleine en bas a gauche de sa fenetre passe au vert,
  echo   puis relance ce fichier.
  echo.
  pause
  exit /b 1
)

REM --- 2. Configuration : le fichier .env et la cle d'API ---------------
REM On boucle jusqu'a ce que la cle soit collee, plutot que de demander
REM de relancer le fichier : un double-clic doit suffire.
:configuration
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo   Un fichier de configuration vient d'etre cree.
  echo.
)

REM findstr renvoie 0 quand il TROUVE. Trouver le texte d'exemple signifie
REM donc que la vraie cle n'a pas encore ete collee.
findstr /c:"ANTHROPIC_API_KEY=sk-ant-..." ".env" >nul 2>&1
if errorlevel 1 goto configuration_ok

echo   [A FAIRE] Il manque ta cle d'API.
echo.
echo   Appuie sur une touche : le Bloc-notes va s'ouvrir.
echo   Sur la ligne qui commence par ANTHROPIC_API_KEY, remplace
echo   tout ce qui suit le signe = par ta vraie cle.
echo   Puis enregistre avec Ctrl+S et ferme le Bloc-notes.
echo.
pause
notepad .env
echo.
goto configuration

:configuration_ok

REM --- 3. Construction et demarrage ------------------------------------
echo   Demarrage en cours.
echo   La toute premiere fois, compter 2 a 3 minutes : Docker telecharge
echo   Python et Postgres. Les fois suivantes, quelques secondes.
echo.
docker compose up -d --build
if errorlevel 1 (
  echo.
  echo   [ARRET] Le demarrage a echoue. Le detail est juste au-dessus.
  echo   Si tu ne comprends pas le message, lance journal.bat et copie
  echo   ce qui s'affiche.
  echo.
  pause
  exit /b 1
)

REM --- 4. Attendre que l'application reponde vraiment -------------------
REM Le conteneur est lance bien avant que l'application ne serve : on
REM interroge /sante jusqu'a reponse, plutot que d'ouvrir un navigateur
REM sur une page d'erreur.
where curl >nul 2>&1
if errorlevel 1 (
  echo   Attente de l'application ^(30 secondes^)...
  timeout /t 30 >nul
  goto pret
)

echo   Attente de l'application...
set /a essais=0
:attente
set /a essais+=1
curl -s -o NUL http://localhost:8000/sante
if not errorlevel 1 goto pret
if !essais! geq 60 goto echec
timeout /t 2 >nul
goto attente

:echec
echo.
echo   [ARRET] L'application n'a pas repondu apres deux minutes.
echo   Lance journal.bat pour voir ce qui s'est passe.
echo.
pause
exit /b 1

:pret
echo.
echo   ================================================
echo     C'est pret :  http://localhost:8000
echo   ================================================
echo.
echo   Le navigateur va s'ouvrir tout seul.
echo.
echo   Pour generer un jeu, la case "Code de generation" attend le
echo   code de la ligne CODE_GENERATION du fichier .env.
echo   Par defaut, c'est :  animation
echo.
echo   Pour tout arreter : double-clic sur arreter.bat
echo.
start "" http://localhost:8000
pause
