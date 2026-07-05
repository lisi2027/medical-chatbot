$env:PYTHONPATH = "$PWD"
& "$PWD\venv\Scripts\streamlit.exe" run "$PWD\streamlit_ui_bot.py" --server.port 8501