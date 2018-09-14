# -*- coding: utf-8 -*-
#
# Copyright (C) 2016-2018 Sebastian Major
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

import time
from unittest import skip

from datetime import date
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import override_settings
from model_mommy import mommy
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from cirs.models import (CriticalIncident, PublishableIncident, LabCIRSConfig,
                         Organization, Reviewer, Reporter)
from cirs.tests.helpers import create_role
from cirs.tests.tests import generate_three_incidents

from .base import FunctionalTest


DEFAULT_WAIT = 5


incident_date = date(2015, 7, 24)
test_incident = {'date': incident_date,
                 'incident': 'A strang incident happened',
                 'reason': 'No one knows',
                 'immediate_action': 'No action possible',
                 'preventability': 'indistinct',
                 'public': True,
                 }


class FunctionalTestWithBackendLogin(FunctionalTest):

    def go_to_test_incident_as_reviewer(self):
        self.org.reviewers.add(create_role(Reviewer, self.reviewer))
        self.login_user(username=self.REVIEWER, password=self.REVIEWER_PASSWORD)
        self.wait.until(EC.presence_of_element_located((By.ID, 'site-name')))
        self.assertIn("/admin/", self.browser.current_url)
        self.click_link_with_text('Critical incidents')
        self.click_link_with_text(test_incident['incident'])


class CriticalIncidentListTest(FunctionalTestWithBackendLogin):
    
    @skip('Tested extensivly in test_multiorganization')
    def test_reporter_login(self):
        self.login_user()
        # # TODO: check if user is authenticated
        # # instead checking for the title of the table
        self.wait.until(EC.presence_of_element_located((By.ID, 'tableIncidents')))
        table_title = self.browser.find_element_by_tag_name('h2').text
        self.assertEqual('Critical incidents', table_title)

    @override_settings(DEBUG=True)
    def test_user_can_add_incident_with_photo(self):
        LabCIRSConfig.objects.create(send_notification=True)
        create_role(Reporter, self.reporter)
        self.org = mommy.make(Organization,reporter=self.reporter.reporter)
        self.quick_login_reporter()
        self.click_link_with_text('Add incident')

        # change to besser test
        self.assertIn("incidents/create", self.browser.current_url)

        # the reporter enters incident data
        self.enter_test_incident(with_photo=True)
        # check for success
        time.sleep(2)
        self.assertIn("/incidents/create/success/", self.browser.current_url)

        # the reporter has to logout and the reviewer has to "publish" the incident
        self.logout()
        self.go_to_test_incident_as_reviewer()
        Select(self.browser.find_element_by_id(
            'id_status')).select_by_value("in process")
        for field in ('incident', 'description', 'measures_and_consequences'):
            for lang in ('de', 'en'):  # TODO: import languages from settings
                self.find_input_and_enter_text(
                    'id_publishableincident-0-{}_{}'.format(field, lang), "a")
        self.browser.find_element_by_id('id_publishableincident-0-publish').click()
        self.browser.find_element_by_name('_save').click()
        headers1 = self.browser.find_elements_by_tag_name('h1')
        self.assertIn("Select Critical incident to change", [header1.text for header1 in headers1])
        # logout and check as normal user if photo is visible
        self.logout()
        self.quick_login_reporter()
        # check if all expected fields are present in the table
        table = self.wait.until(EC.presence_of_element_located((By.ID, 'tableIncidents')))
        EXPECTED_HEADERS = [u'Incident', u'Description', u'Measures and consequences', u'Photo']
        header_elements = table.find_elements_by_tag_name('th')
        table_headers_list = []
        for header in header_elements:
            table_headers_list.append(header.text)
        self.assertListEqual(EXPECTED_HEADERS, table_headers_list)

        all_images = self.browser.find_elements_by_tag_name('img')
        self.assertGreater(len(all_images), 0)

    def test_new_publishes_incidents_are_displayed_first(self):
        """ Creates new critical incidents with published incidents and checks
        if the new appear in the upper row independent of the order of the
        critical incidents."""
        # import the generator from unit test
        create_role(Reporter, self.reporter)
        organization = mommy.make(Organization, reporter=self.reporter.reporter)
        generate_three_incidents(organization)

        # Now reporter goes to the list and should see the list of
        # published incidents in order b, a, c
        self.quick_login_reporter()
        table = self.browser.find_element_by_id('tableIncidents')
        rows = table.find_elements_by_tag_name('tr')

        self.assertIn('b', rows[1].text)
        self.assertIn('a', rows[2].text)
        self.assertIn('c', rows[3].text)

    @override_settings(EMAIL_HOST='smtp.example.com')
    def test_send_email_after_reviewer_creates_an_incident(self):
        config = LabCIRSConfig.objects.create(send_notification=True)
        config.notification_recipients.add(self.reviewer)
        config.notification_sender_email = 'labcirs@labcirs.edu'
        config.save()
        create_role(Reporter, self.reporter)
        self.org = mommy.make(Organization,reporter=self.reporter.reporter)
        self.quick_login_reporter(reverse('create_incident'))

        # reporter enters incident data
        self.enter_test_incident(wait_for_success=True)

        # check if incident was sent by email
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'New critical incident')


class CriticalIncidentBackendTest(FunctionalTestWithBackendLogin):

    def test_reviewer_can_chose_category_of_incident(self):
        self.org = mommy.make(Organization)
        CriticalIncident.objects.create(organization=self.org, **test_incident)
        self.go_to_test_incident_as_reviewer()
        Select(self.browser.find_element_by_id(
            'id_status')).select_by_value("in process")
        category_field = self.browser.find_element_by_id('id_category')
