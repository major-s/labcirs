# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Sebastian Major
#
# This file is part of LabCIRS.
#
# LabCIRS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# LabCIRS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LabCIRS.
# If not, see <http://www.gnu.org/licenses/old-licenses/gpl-2.0>.

from collections import OrderedDict
from datetime import date

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase

from cirs.models import CriticalIncident, PublishableIncident
from cirs.views import IncidentDetailView

from .tests import generate_three_incidents 


class SecurityTest(TestCase):

    def setUp(self):
        self.username = 'reporter'
        self.email = 'reporter@test.edu'
        self.password = 'reporter'
        self.reporter = User.objects.create_user(self.username, self.email,
                                                 self.password)
        generate_three_incidents()
        self.ci = CriticalIncident.objects.first()

    def test_reporter_cannot_acces_incident_directly(self):
        """Tests if reporter gets redirected to the search page
        if he tries to access the detail view of an incident."""

        login = self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.ci.get_absolute_url(), follow=True)
        print response.redirect_chain
        self.assertRedirects(response, reverse('incident_search'))
            
    def test_incident_search_sets_session_var_on_success(self):
        login = self.client.login(username=self.username, password=self.password)
        response = self.client.post(reverse('incident_search'), {'incident_code':self.ci.comment_code}, follow=True)
        self.assertEqual(self.client.session['accessible_incident'], self.ci.id)
        
    def test_reporter_can_acces_incident_if_session_var_is_set(self):
        """Tests if reporter gets redirected to the detail view of incident
        if 'accessible_incident' is set to the id of the incident.id."""
        login = self.client.login(username=self.username, password=self.password)
        session = self.client.session
        session['accessible_incident'] = self.ci.id
        session.save()
        response = self.client.get(self.ci.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)