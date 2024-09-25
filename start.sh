#!bin/sh

cd /app
python3 prestart.py
fastapi run app/main.py --port 80 --workers 4
