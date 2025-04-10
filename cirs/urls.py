from django.urls import re_path
from django.views.generic import TemplateView

from cirs.views import (DepartmentList, IncidentCreate, IncidentDetailView,
                        IncidentSearch, PublishableIncidentList)

urlpatterns = [
    re_path(r'^$', DepartmentList.as_view(), name='departments_list'),
    re_path(r'^(?P<dept>.+)/create/$', IncidentCreate.as_view(), name='create_incident'),
    re_path(r'^(?P<dept>.+)/create/success/$',
        TemplateView.as_view(template_name="cirs/success.html"),
        name='success'),
    re_path(r'^(?P<dept>.+)/search/$', IncidentSearch.as_view(), name='incident_search'),
    re_path(r'^(?P<dept>.+)/(?P<pk>[0-9]+)/$', IncidentDetailView.as_view(), name='incident_detail'),
    re_path(r'^(?P<dept>.+)/$', PublishableIncidentList.as_view(), name='incidents_for_department'),
]
