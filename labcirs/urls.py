from django.conf import settings
from django.conf.urls import include, url
from django.views.generic import TemplateView
from django.views.static import serve

from cirs.views import login_user, logout_user, DepartmentList, RegistrationViewWithDepartment
from cirs.admin import admin_site


urlpatterns = [
    url(r'^$', DepartmentList.as_view(), name='labcirs_home'),
    url(r'^incidents/', include('cirs.urls')),
    url(r'^admin/logout/$', logout_user, name='logout_admin'),
    url(r'^admin/', include(admin_site.urls)),
    url(r'^login/$',  login_user, name='login'),
    url(r'^logout/$', logout_user, name='logout'),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^accounts/register/$', RegistrationViewWithDepartment.as_view(), name='registration_register'),
    url(r'^accounts/', include('registration.backends.admin_approval.urls')),
    #url(r'^docs/', include('docs.urls')),
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
