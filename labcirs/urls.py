from django.conf import settings
from django.conf.urls import include, url
from django.views.generic import TemplateView
from django.contrib import admin
from django.views.static import serve
from django.views.generic.base import RedirectView

from cirs.views import login_user, logout_user

cirs_url = settings.ROOT_URL + '/incidents/'

urlpatterns = [
    url(r'^$', RedirectView.as_view(url=cirs_url), name='labcirs_home'),
    url(r'^incidents/', include('cirs.urls')),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^login/$',  login_user, name='login'),
    url(r'^logout/$', logout_user, name='logout'),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^demo_data.html$', TemplateView.as_view(), name='demo_login_data_page'),
]

# TODO: has to change to construct commented below as this
# syntax will be removed in next django version
if settings.DEBUG:
    urlpatterns += [
        url(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
    ]
