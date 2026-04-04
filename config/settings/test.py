"""
Test settings for the taxi platform.
These settings ensure that tests run in an environment identical 
to production but with optimizations for speed.
"""

from .base import *

# IMPORTANT: We are using PostGIS, the latest SQLite is not supported
# geospatial data types are not sufficient for our taxi
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
        'ATOMIC_REQUESTS': True, 
        'TEST': {
            'NAME': 'test_taxi_db', # Name of the temporary database for tests
        },
    }
}

# Optimization: using MD5 speeds up user-related tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable DEBUG for tests to detect potential environment errors
DEBUG = False

# It is better not to disable migrations completely so that Django can correctly
# initialize the GIS extension in the test database