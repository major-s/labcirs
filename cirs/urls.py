# -*- coding: utf-8 -*-

from django.conf.urls import url
from django.views.generic import TemplateView

from cirs.views import IncidentCreate, PublishableIncidentList, IncidentSearch, IncidentDetailView

urlpatterns = [
    url(r'^$', PublishableIncidentList.as_view(), name='incidents_list'),
    url(r'^create/$', IncidentCreate.as_view(), name='create_incident'),
    url(r'^create/success/$',
        TemplateView.as_view(template_name="cirs/success.html"),
        name='success'),
    url(r'^search/$', IncidentSearch.as_view(), name='incident_search'),
    url(r'^(?P<pk>[0-9]+)/$', IncidentDetailView.as_view(), name='incident_detail')
]
