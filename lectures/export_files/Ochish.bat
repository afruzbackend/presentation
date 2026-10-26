@echo off
rem Elektron darslikni ochish: videolar darslik ichida ijro etilishi uchun kichik mahalliy server (Python kerak emas)
title Elektron darslik
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0server.ps1"
