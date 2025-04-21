from .base import *

DEBUG = False

DB_ENGINE = get_local_setting('DB_ENGINE', 'sqlite3')
DATABASES = {
    'default': {
        'ENGINE': f'django.db.backends.{DB_ENGINE}',
        'NAME': get_local_setting('DB_NAME', join_path(BASE_DIR, 'db.sqlite3')),
        # The following settings are not used with sqlite3:
        'USER': get_local_setting('DB_USER'),
        'PASSWORD': get_local_setting('DB_PASSWORD'),
        'HOST': get_local_setting('DB_HOST'),
        'PORT': get_local_setting('DB_PORT'),
    }
}
