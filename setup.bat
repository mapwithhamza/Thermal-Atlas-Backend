@echo off

:: Create virtual environment
python -m venv venv

:: Activate and install dependencies
call venv\Scripts\activate
pip install -r requirements.txt

echo Setup complete. Run 'venv\Scripts\activate' to start working.
