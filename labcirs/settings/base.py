"""
Django settings for labcirs project.

Upgraded from 1.6 to 1.9

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import json
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from os.path import dirname, abspath, join as join_path
BASE_DIR = dirname(dirname(dirname(abspath(__file__))))

local_config_file = join_path(BASE_DIR, "labcirs/settings/local_config.json")


def get_local_setting(setting_item, default=None, config_file=local_config_file):
    try:
        f = open(config_file)
        try:
            local_config = json.loads(f.read())
            try:
                setting_value = local_config[setting_item]
                if (setting_value == '') and (default is not None):
                    return default
                else:
                    return setting_value
            except KeyError:
                error_msg = "Set the {0} environment variable in {1}".format(
                    setting_item, local_config_file)
                raise ImproperlyConfigured(error_msg)
        except ValueError as (msg):
            raise Exception("JSON error: {0}".format(msg))
    except IOError as (errno, strerror):
        raise Exception("Cannot open {0}: {1}. ".format(config_file, strerror))

# SECURITY WARNING: keep the secret key used in production secret!
# The secret key has to be generated separately for each server, e.g. in the django shell
# a custom management command is provided:
#
#   python manage.py shell makesecretkey
#
# generates a secret key and stores it in the local config json file.

SECRET_KEY = get_local_setting('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = get_local_setting('ALLOWED_HOSTS')  # ['*',] #local


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cirs',
    'multiselectfield',
    'parler',
]

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware', #local
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'labcirs.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [join_path(BASE_DIR, 'templates'), ],  # local
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',  # local
                'cirs.context_processors.cirs_data',  # local
            ],
        },
    },
]

WSGI_APPLICATION = 'labcirs.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': join_path(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Change in the local settings file only if LabCIRS is not mounted in the root of the web server
# needed for static and media url

ROOT_URL = get_local_setting('ROOT_URL')

LOGIN_URL = ROOT_URL + '/login/'

STATIC_URL = ROOT_URL + '/static/'

STATIC_ROOT = join_path(dirname(BASE_DIR), 'static')

TIME_ZONE = get_local_setting('TIME_ZONE', 'UTC')

STATICFILES_DIRS = (join_path(BASE_DIR, 'static'),)


LANGUAGES = tuple((k, _(v)) for k, v in get_local_setting('LANGUAGES').iteritems())

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 60 * 60 # one hour, not logged out users will leave a ghost session in db!
SESSION_SAVE_EVERY_REQUEST = True
# SESSION_COOKIE_SECURE = True # will not work if the server has no https!!!

MEDIA_ROOT = join_path(dirname(BASE_DIR), 'media')
MEDIA_URL = ROOT_URL + '/media/'
# get local name of the organization. Default is LabCIRS if the value in the json file is empty
ORGANIZATION = get_local_setting('ORGANIZATION', 'LabCIRS')

# Email settings
EMAIL_HOST = get_local_setting('EMAIL_HOST', 'localhost')
EMAIL_HOST_PASSWORD = get_local_setting('EMAIL_HOST_PASSWORD')
EMAIL_HOST_USER = get_local_setting('EMAIL_HOST_USER')
EMAIL_PORT = get_local_setting('EMAIL_PORT', 25)
EMAIL_SUBJECT_PREFIX = '[LabCIRS] '

# Parler
PARLER_DEFAULT_LANGUAGE_CODE = get_local_setting('PARLER_DEFAULT_LANGUAGE_CODE', 'en')

PARLER_LANGUAGES = {
    None: (
        tuple({'code': lang,} for lang in get_local_setting('PARLER_LANGUAGES'))
    ),
    'default': {
        'fallbacks': get_local_setting('PARLER_LANGUAGES'), # use all languages
        'hide_untranslated': False,   # the default; let .active_translations() return fallbacks too.
    }
}

ALL_LANGUAGES_MANDATORY_DEFAULT = get_local_setting('ALL_LANGUAGES_MANDATORY_DEFAULT', True)

if ALL_LANGUAGES_MANDATORY_DEFAULT is True:
    DEFAULT_MANDATORY_LANGUAGES = get_local_setting('PARLER_LANGUAGES')
else:
    DEFAULT_MANDATORY_LANGUAGES = PARLER_DEFAULT_LANGUAGE_CODE
