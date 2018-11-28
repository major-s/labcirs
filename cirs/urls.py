# -*- coding: utf-8 -*-

from django.conf.urls import url
from django.views.generic import TemplateView

from cirs.views import IncidentCreate, PublishableIncidentList, IncidentSearch, IncidentDetailView, DepartmentList

urlpatterns = [
    url(r'^$', DepartmentList.as_view(), name='departments_list'),
    url(r'^(?P<dept>.+)/create/$', IncidentCreate.as_view(), name='create_incident'),
    url(r'^(?P<dept>.+)/create/success/$',
        TemplateView.as_view(template_name="cirs/success.html"),
        name='success'),
    url(r'^(?P<dept>.+)/search/$', IncidentSearch.as_view(), name='incident_search'),
    url(r'^(?P<dept>.+)/(?P<pk>[0-9]+)/$', IncidentDetailView.as_view(), name='incident_detail'),
    url(r'^(?P<dept>.+)/$', PublishableIncidentList.as_view(), name='incidents_for_department'),
]
