from .base import *

DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': get_local_setting('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': get_local_setting('DB_NAME', join_path(BASE_DIR, 'db.sqlite3')),
        # The following settings are not used with sqlite3:
        'USER': get_local_setting('DB_USER'),
        'PASSWORD': get_local_setting('DB_PASSWORD'),
        'HOST': get_local_setting('DB_HOST'),
        'PORT': get_local_setting('DB_PORT'),
    }
}
