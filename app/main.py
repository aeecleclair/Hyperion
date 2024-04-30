"""File used to start the application. It is used by uvicorn and gunicorn"""

from fastapi import FastAPI

from app.app import get_application
from app.dependencies import get_settings

# When using uvicorn or gunicorn, the application is started with the following command:
# We dissociate this step from the app.py file so that during tests we can initialize it with the mocked settings
app: FastAPI = get_application(settings=get_settings())
