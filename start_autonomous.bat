@echo off
echo === ZERO HUMAN DROPSHIP - FULL AUTONOMY ===
powercfg /change standby-timeout-ac 0
powershell -ExecutionPolicy Bypass -File "%~dp0supervisor.ps1"
