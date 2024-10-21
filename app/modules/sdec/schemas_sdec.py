"""Schemas file for endpoint /sdec"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.schemas_core import CoreUserSimple
from app.modules.booking.types_booking import Decision
