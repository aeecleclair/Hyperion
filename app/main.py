"""File used by Uvicorn to start the application."""

from app.app import get_application
from app.dependencies import get_settings

# The application is started with the following function call:
# We dissociate this step from the app.py file so that during tests we can initialize it with the mocked settings
app = get_application(settings=get_settings())
