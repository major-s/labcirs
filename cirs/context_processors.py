# -*- coding: utf-8 -*-

import cirs
from django.conf import settings


def cirs_data(request):
    return {'APP_VERSION': cirs.__version__,
            'AUTHOR': cirs.__AUTHOR__,
            'ORGANIZATION': settings.ORGANIZATION
            }