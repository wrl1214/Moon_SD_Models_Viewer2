@echo off
chcp 65001 > nul

echo Installing required packages...
py -m pip install -r requirements.txt

echo Starting program...
py safetensors_viewer.py
::pause

