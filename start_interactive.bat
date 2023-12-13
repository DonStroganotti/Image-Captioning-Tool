@echo off
echo Activating virtual environment
call .\venv\Scripts\activate.bat

echo Running Interactive Script 
python .\scripts\tag_editor_interactive.py ^
--path "" ^
--keywords "" ^
--backup "backup"
