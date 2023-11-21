from jinja2 import Environment
from django.conf import settings
from datetime import datetime


def jinja2_date_float_tostring(value):
    """Format a float to (Default)"""
    # The date is stored as a float in the database, the float has the format YYYYMMDDHHMMSS.microseconds
    # This function converts the float to a string in the format YYYY-MM-DD HH:MM:SS
    if value is None:
        return ""
    return format(datetime.strptime(str(value), "%Y%m%d%H%M%S.%f"), "%d-%m-%Y")


def environment(**options):
    env = Environment(**options)
    env.filters["date_float_tostring"] = jinja2_date_float_tostring
    return env
