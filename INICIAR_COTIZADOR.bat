@echo off
title COTIZADOR SOAT 2026 - INICIANDO...
color 0A

:: 1. Nos aseguramos de estar en la carpeta correcta
cd /d "%~dp0"

echo ======================================================
echo      INICIANDO SISTEMA DE COTIZACION SOAT
echo ======================================================
echo.

:: 2. Verificamos si Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    cls
    color 0C
    echo [ERROR CRITICO]
    echo No se detecto Python en esta computadora.
    echo Por favor instala Python 3.10 o superior y marca la casilla "ADD TO PATH".
    echo.
    pause
    exit
)

:: 3. Instalamos las librerias necesarias (solo si faltan)
echo Verificando librerias necesarias...
echo Esto puede tardar un poco la primera vez...
pip install -r requirements.txt >nul 2>&1

:: 4. Ejecutamos la aplicacion
cls
echo ======================================================
echo      LIBRERIAS LISTAS. ABRIENDO APLICACION...
echo ======================================================
echo.
echo No cierres esta ventana negra mientras usas el cotizador.
echo.

streamlit run web_soat.py

:: 5. Si algo falla, que no se cierre la ventana para leer el error
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo OCURRIO UN ERROR INESPERADO.
    echo Revisa el mensaje de arriba.
    pause
)

pip install PyMuPDF
pip install openpyxl