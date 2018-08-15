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

from django.core.urlresolvers import reverse
from django.test import override_settings
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from cirs.models import CriticalIncident, PublishableIncident, LabCIRSConfig

from .base import FunctionalTest


DEFAULT_WAIT = 5


class OrganizationNameTest(FunctionalTest):
    """Testing customization of the name of the organization.

    The name the organization should be interchengable and will be set in
    the local_config.json but if missing, LabCIRS should be used as default.
    """

    @override_settings(ORGANIZATION='')
    def test_default_organization_name(self):
        self.browser.get(self.live_server_url)
        # assume default name is LabCIRS
        organization = self.browser.find_element_by_class_name(
            'navbar-brand').text
        self.assertEqual(organization, "LabCIRS")

    # enter the organization name into the settings
    ORGANIZATION = 'MyFunnyLab'

    @override_settings(ORGANIZATION=ORGANIZATION)
    def test_custom_organization_name(self):
        self.browser.get(self.live_server_url)
        # assume default name is LabCIRS
        organization = self.browser.find_element_by_class_name(
            'navbar-brand').text
        self.assertEqual(organization, self.ORGANIZATION)


class ConfigurationInBackend(FunctionalTest):
    """Reviewer can specify information about login data for the reporter."""

    LOGIN_INFO = "You can find the login data for this demo installation at "
    LINK_TEXT = "the demo login data page"

    def test_reviewer_can_set_the_message_text(self):
        login_url = self.live_server_url + reverse('demo_login_data_page')

        self.quick_backend_login(self.reviewer)
        self.click_link_with_text('LabCIRS configuration')
        self.click_link_case_insensitive('Add LabCIRS configuration')
        self.find_input_and_enter_text('id_login_info_en', self.LOGIN_INFO)
        self.find_input_and_enter_text('id_login_info_de', self.LOGIN_INFO)
        self.find_input_and_enter_text('id_login_info_url', login_url)
        self.find_input_and_enter_text('id_login_info_link_text_en', self.LINK_TEXT)
        self.find_input_and_enter_text('id_login_info_link_text_de', self.LINK_TEXT)
        self.browser.find_element_by_name('_save').click()
        self.logout()
        time.sleep(2)
        self.browser.get(self.live_server_url)
        current_login_info = self.browser.find_element_by_class_name('alert-success').text
        self.assertIn(self.LOGIN_INFO, current_login_info)
        self.browser.find_element_by_link_text(self.LINK_TEXT)


class EmailSettingsInBackend(FunctionalTest):
    """Settings for sending notifications."""

    def setUp(self):
        super(EmailSettingsInBackend, self).setUp()

        # make simple config in advance and go to the config page
        self.config = LabCIRSConfig.objects.create(
            login_info_en="English", login_info_de="Deutsch",
            send_notification=False)
        self.quick_backend_login(self.reviewer)
        admin_url = reverse(
            'admin:{}_{}_change'.format(
                self.config._meta.app_label, self.config._meta.model_name
            ),
            args=(self.config.pk,)
        )
        self.browser.get(self.live_server_url + admin_url)

    @override_settings(EMAIL_HOST='localhost')
    def test_reviewer_can_switch_email_notifications(self):
        """Email notifications can be (de)activatet if email settings are set.

        Notifications are only send if a valid(?) SMTP server is defined
        and differs from localhost.
        """

        self.browser.find_element_by_id('id_send_notification').click()
        self.browser.find_element_by_name('_save').click()
        error_msg = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, 'errorlist')))
        # could also import the errormessage and check for equality
        self.assertIn('distinct from localhost', error_msg.text)

    def test_only_reviewers_in_the_recipient_list(self):
        recipient_select = Select(
            self.browser.find_element_by_id('id_notification_recipients_from'))
        self.assertEqual(recipient_select._el.text, 'reviewer')

    @override_settings(EMAIL_HOST='smtp.example.com')
    def test_no_notifications_if_no_recipient(self):
        self.browser.find_element_by_id('id_send_notification').click()
        self.browser.find_element_by_name('_save').click()
        error_msg = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, 'errorlist')))
        self.assertIn('at least one notification recipient', error_msg.text)

    @override_settings(EMAIL_HOST='smtp.example.com')
    def test_no_notifications_if_no_sender(self):
        self.config.notification_recipients.add(self.reviewer)
        self.config.save()
        self.browser.find_element_by_id('id_send_notification').click()
        self.browser.find_element_by_name('_save').click()
        error_msg = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, 'errorlist')))
        self.assertIn('sender email', error_msg.text)

    def test_enter_sender_email(self):
        self.find_input_and_enter_text('id_notification_sender_email', 'a@test.edu')
        self.browser.find_element_by_name('_save').click()
        time.sleep(2)
        config = LabCIRSConfig.objects.first()
        self.assertEqual(config.notification_sender_email, "a@test.edu")

    def test_reviewer_can_enter_notification_text(self):
        self.find_input_and_enter_text('id_notification_text', "New incident")
        self.browser.find_element_by_name('_save').click()
        time.sleep(2)
        config = LabCIRSConfig.objects.first()
        self.assertEqual(config.notification_text, "New incident")
