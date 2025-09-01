@echo off
echo Setting up Python virtual environment...
python -m venv venv
call .\venv\Scripts\activate.bat
pip install -r requirements.txt
echo.
echo Virtual environment setup complete!
echo.
echo To activate the virtual environment, run:
echo .\venv\Scripts\activate
echo.
echo Then start the server with:
echo uvicorn main:app --reload
pause
