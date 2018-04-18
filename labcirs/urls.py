from django.conf.urls import include, url
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

from cirs.views import login_user, logout_user

from django.contrib import admin
admin.autodiscover()

# TODO: try to use reverse URL resolution to get rid of hardcoded urls
# actually all cirs related stuff should go to cirs url
from django.conf import settings
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
    url(r'^comments/', include('django_comments_xtd.urls')),
]

# TODO: has to change to construct commented below as this
# syntax will be removed in next django version
from django.conf import settings
if settings.DEBUG:
    urlpatterns += [
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
    ]
