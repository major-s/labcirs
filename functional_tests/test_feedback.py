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

import os
import time
from datetime import date

from django.conf import settings
from django.core import mail
from django.test import override_settings
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from cirs.models import CriticalIncident, LabCIRSConfig
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


class CriticalIncidentFeedbackTest(FunctionalTest):

    @override_settings(DEBUG=True)
    def test_user_can_see_feedback_code(self):
        LabCIRSConfig.objects.create(send_notification=True)
        self.login_user()

        self.browser.find_element_by_link_text("Add incident").click()

        # change to better test
        self.assertIn("incidents/create", self.browser.current_url)

        # the reporter enters incident data
        date_field = self.browser.find_element_by_id('id_date')
        # TODO: change to variable
        date_field.send_keys("07/24/2015")
        incident_field = self.browser.find_element_by_id('id_incident')
        incident_field.send_keys(test_incident['incident'])
        reason_field = self.browser.find_element_by_id('id_reason')
        reason_field.send_keys(test_incident['reason'])
        immediate_action_field = self.browser.find_element_by_id(
            'id_immediate_action')
        immediate_action_field.send_keys(test_incident['immediate_action'])
        preventability_select = Select(self.browser.find_element_by_id(
            'id_preventability'))
        preventability_select.select_by_value(test_incident['preventability'])
        self.browser.find_element_by_id('id_public_0').click()  # true


        for button in self.browser.find_elements_by_class_name("btn-danger"):
            if "Send" in button.text:
                button.click()
        # check for success
        time.sleep(2)
        # TODO: Add check for feedback message:
        # User sees the success page with code for feedback
        
        # feedback code seen by user is saved with the 
               
        code_info = self.browser.find_element_by_class_name("alert-info")
           
        #there should be only one object in the database
        ci = CriticalIncident.objects.get(pk=1)
        comment_code = ci.comment_code
        
        self.assertIn(comment_code, code_info.text)
