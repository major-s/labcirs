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

from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


DEFAULT_WAIT = 8


class FunctionalTest(StaticLiveServerTestCase):

    REPORTER = 'reporter'
    REPORTER_EMAIL = 'reporter@example.com'
    REPORTER_PASSWORD = 'reporter'

    REVIEWER = 'reviewer'
    REVIEWER_EMAIL = 'reviewer@example.com'
    REVIEWER_PASSWORD = 'reviewer'

    ADMIN = 'admin'
    ADMIN_EMAIL = 'admin@example.com'
    ADMIN_PASSWORD = 'admin'

    def setUp(self):
        # generate reporter user
        self.reporter = User.objects.create_user(
            self.REPORTER, self.REPORTER_EMAIL, self.REPORTER_PASSWORD)
        permission = Permission.objects.get(codename='add_criticalincident')
        self.reporter.user_permissions.add(permission)
        # Generate reviewer user
        self.reviewer = User.objects.create_user(
            self.REVIEWER, self.REVIEWER_EMAIL, self.REVIEWER_PASSWORD)
        self.reviewer.is_staff = True
        self.reviewer.save()
        for codename in ('change_criticalincident', 'add_publishableincident',
                         'change_publishableincident',
                         'add_labcirsconfig', 'change_labcirsconfig'):
            permission = Permission.objects.get(codename=codename)
            self.reviewer.user_permissions.add(permission)
        self.admin = User.objects.create_superuser(
            self.ADMIN, self.ADMIN_EMAIL, self.ADMIN_PASSWORD)
        # Initialise browser for testing
        # the noninternationalized version is checked
        if settings.BROWSER == 'Chrome':
            chrome_driver_location = settings.CHROME_DRIVER
            options = webdriver.ChromeOptions()
            options.add_argument('--lang=en')
            self.browser = webdriver.Chrome(
                executable_path=chrome_driver_location, chrome_options=options)
        elif settings.BROWSER == 'Firefox':
            profile = webdriver.FirefoxProfile()
            profile.set_preference('intl.accept_languages', 'en')
            self.browser = webdriver.Firefox(profile)

        self.browser.implicitly_wait(DEFAULT_WAIT)
        self.maxDiff = None
        self.wait = WebDriverWait(self.browser, DEFAULT_WAIT)


    def tearDown(self):
        time.sleep(1)
        self.browser.quit()
        time.sleep(1)

    def click_link_with_text(self, link_text):
        self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, link_text)),
            message=('could not find ' + link_text)
        ).click()
    
    def click_link_case_insensitive(self, link_text):
        try:
            self.click_link_with_text(link_text)
        except:
            self.click_link_with_text(link_text.upper())

    def find_input_and_enter_text(self, identifier, text, method=By.ID):
        self.wait.until(
            EC.presence_of_element_located((method, identifier)),
            message=('could not find {} {}'.format(identifier, method))
        ).send_keys(text)

    def quick_login(self, user, target_url=''):
        self.client.force_login(user)
        cookie = self.client.cookies['sessionid']
        self.browser.get(self.live_server_url + target_url)
        self.browser.add_cookie({'name': 'sessionid', 'value': cookie.value, 'secure': False, 'path': '/'})
        self.browser.get(self.live_server_url + target_url)

    def quick_login_reporter(self, target_url=''):
        self.quick_login(self.reporter, target_url)

    def quick_backend_login(self, user=None, target_url='/admin/'):
        if user is None:
            user = self.admin
        self.quick_login(user, target_url)
    
    def login_user(self, username=REPORTER, password=REPORTER_PASSWORD):
        """Loggs user into the frontend of the webproject"""
        self.browser.get(self.live_server_url)
        self.find_input_and_enter_text('username', username, By.NAME)
        self.find_input_and_enter_text('password', password, By.NAME)
        self.find_input_and_enter_text('password', Keys.RETURN, By.NAME)
        
    def logout(self):
        self.click_link_case_insensitive("Log out")

    def enter_test_incident(self, with_photo=False, wait_for_success=False):
        # usable on incident create page
        self.find_input_and_enter_text('id_date', "07/24/2015")
        self.find_input_and_enter_text('id_incident', "A strang incident happened")
        self.find_input_and_enter_text('id_reason', "No one knows")
        self.find_input_and_enter_text('id_immediate_action', "No action possible")
        Select(self.browser.find_element_by_id(
            'id_preventability')).select_by_value("indistinct")
        self.browser.find_element_by_id('id_public_0').click()  # true
        # upload photo
        if with_photo is True:
            self.find_input_and_enter_text('id_photo',
                os.path.join(os.getcwd(), "cirs", "tests", "test.jpg"))
        # submit
        for button in self.browser.find_elements_by_class_name("btn-danger"):
            if "Send" in button.text:
                button.click()
        if wait_for_success:
            # wait for the success page
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, 'alert-info')))