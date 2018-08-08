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

import os
import time
from datetime import date

from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import override_settings

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC

from cirs.models import CriticalIncident, PublishableIncident, LabCIRSConfig
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
        self.login_user(username=self.REVIEWER, password=self.REVIEWER_PASSWORD)
        self.wait.until(EC.presence_of_element_located((By.ID, 'site-name')))
        self.assertIn("/admin/", self.browser.current_url)
        self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Critical incidents")))
        self.browser.find_element_by_link_text("Critical incidents").click()
        self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, test_incident['incident'])))
        self.browser.find_element_by_link_text(test_incident['incident']).click()


class CriticalIncidentListTest(FunctionalTestWithBackendLogin):
    
    def test_login(self):
        self.login_user()
        # # TODO: check if user is authenticated
        # # instead checking for the title of the table
        self.wait.until(EC.presence_of_element_located((By.ID, 'tableIncidents')))
        table_title = self.browser.find_element_by_tag_name('h2').text
        self.assertEqual('Critical incidents', table_title)

    @override_settings(DEBUG=True)
    def test_user_can_add_incident_with_photo(self):
        LabCIRSConfig.objects.create(send_notification=True)
        self.login_user()
        self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Add incident")))
        self.browser.find_element_by_link_text("Add incident").click()

        # change to besser test
        self.assertIn("incidents/create", self.browser.current_url)

        # the reporter enters incident data
        date_field = self.browser.find_element_by_id('id_date')
        date_field.send_keys("07/24/2015")
        incident_field = self.browser.find_element_by_id('id_incident')
        incident_field.send_keys("A strang incident happened")
        reason_field = self.browser.find_element_by_id('id_reason')
        reason_field.send_keys("No one knows")
        immediate_action_field = self.browser.find_element_by_id(
            'id_immediate_action')
        immediate_action_field.send_keys("No action possible")
        preventability_select = Select(self.browser.find_element_by_id(
            'id_preventability'))
        preventability_select.select_by_value("indistinct")
        self.browser.find_element_by_id('id_public_0').click()  # true
        # upload photo
        photo_field = self.browser.find_element_by_id('id_photo')
        photo_field.send_keys(os.path.join(os.getcwd(), "cirs", "tests", "test.jpg"))
        # submit
        for button in self.browser.find_elements_by_class_name("btn-danger"):
            if "Send" in button.text:
                button.click()
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
                self.browser.find_element_by_id(
                    'id_publishableincident-0-' + field + '_' + lang).send_keys("a")
        self.browser.find_element_by_id('id_publishableincident-0-publish').click()
        self.browser.find_element_by_name('_save').click()
        headers1 = self.browser.find_elements_by_tag_name('h1')
        self.assertIn("Select Critical incident to change", [header1.text for header1 in headers1])
        # logout and check as normal user if photo is visible
        self.logout()
        self.login_user()
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

        generate_three_incidents()

        # Now user goes to the list and should see the list of
        # published incidents in order b, a, c
        self.login_user()
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
        self.login_user()
        self.browser.find_element_by_link_text("Add incident").click()
        # labcirs enters incident data
        # copied from test_user_can_add_incident_with_photo
        # refactor later if needed
        date_field = self.browser.find_element_by_id('id_date')
        date_field.send_keys("07/24/2015")
        incident_field = self.browser.find_element_by_id('id_incident')
        incident_field.send_keys("A strang incident happened")
        reason_field = self.browser.find_element_by_id('id_reason')
        reason_field.send_keys("No one knows")
        immediate_action_field = self.browser.find_element_by_id(
            'id_immediate_action')
        immediate_action_field.send_keys("No action possible")
        preventability_select = Select(self.browser.find_element_by_id(
            'id_preventability'))
        preventability_select.select_by_value("indistinct")
        self.browser.find_element_by_id('id_public_0').click()  # true
        # submit
        for button in self.browser.find_elements_by_class_name("btn-danger"):
            if "Send" in button.text:
                button.click()
        # check if incident was sent by email
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'New critical incident')


class CriticalIncidentBackendTest(FunctionalTestWithBackendLogin):

    def test_reviewer_can_chose_category_of_incident(self):
        CriticalIncident.objects.create(**test_incident)
        self.go_to_test_incident_as_reviewer()
        Select(self.browser.find_element_by_id(
            'id_status')).select_by_value("in process")
        category_field = self.browser.find_element_by_id('id_category')