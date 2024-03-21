from django.conf import settings
from django.urls import include, re_path
from django.views.generic import TemplateView
from django.views.static import serve

from cirs.views import login_user, logout_user, DepartmentList, RegistrationViewWithDepartment
from cirs.admin import admin_site


urlpatterns = [
    re_path(r'^$', DepartmentList.as_view(), name='labcirs_home'),
    re_path(r'^incidents/', include('cirs.urls')),
    re_path(r'^admin/logout/$', logout_user, name='logout_admin'),
    re_path(r'^admin/', admin_site.urls),
    re_path(r'^login/$',  login_user, name='login'),
    re_path(r'^logout/$', logout_user, name='logout'),
    re_path(r'^i18n/', include('django.conf.urls.i18n')),
    re_path(r'^accounts/register/$', RegistrationViewWithDepartment.as_view(), name='registration_register'),
    re_path(r'^accounts/', include('registration.backends.admin_approval.urls')),
    #re_path(r'^docs/', include('docs.urls')),
    re_path(r'^demo_data.html$', TemplateView.as_view(), name='demo_login_data_page'),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
    ]
