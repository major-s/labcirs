from django.conf import settings

import cirs


def cirs_data(request):
    return {'APP_VERSION': cirs.__version__,
            'AUTHOR': cirs.__AUTHOR__,
            'ORGANIZATION': settings.ORGANIZATION
            }