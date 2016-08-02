# -*- coding: utf-8 -*-

from django.conf.urls import url
from django.views.generic import TemplateView

from cirs.views import IncidentCreate, PublishableIncidentList

urlpatterns = [
    url(r'^$', PublishableIncidentList.as_view(), name='incidents_list'),
    url(r'^create/$', IncidentCreate.as_view(), name='create_incident'),
    url(r'^create/success/$',
        TemplateView.as_view(template_name="cirs/success.html"),
        name='success'),
]
