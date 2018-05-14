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

import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings

DEFAULT_WAIT = 5


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
        self.admin = User.objects.create_user(
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
        self.wait = WebDriverWait(self.browser, 120)

    def tearDown(self):
        time.sleep(1)
        self.browser.quit()
        time.sleep(1)

    def login_user(self, username=REPORTER, password=REPORTER_PASSWORD):
        """Loggs user into the frontend of the webproject"""
        self.browser.get(self.live_server_url)
        self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
        username_input = self.browser.find_element_by_name("username")
        username_input.send_keys(username)
        password_input = self.browser.find_element_by_name("password")
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        
    def logout(self):
        self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Log out")))
        self.browser.find_element_by_link_text("Log out").click()
 