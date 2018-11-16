# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Sebastian Major
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

from __future__ import unicode_literals

from model_mommy import mommy
from selenium.webdriver.support.select import Select

from cirs.models import Reviewer
from cirs.tests.helpers import create_role

from .base import FunctionalTest
from django.urls.base import reverse





class CriticalIncidentBackendTest(FunctionalTest):
    """
    Added when incident was extended with category
    """

    def test_reviewer_can_chose_category_of_incident(self):
        ci = mommy.make_recipe('cirs.public_ci')
        ci.department.reviewers.add(create_role(Reviewer, self.reviewer))
        admin_url = reverse('admin:cirs_criticalincident_change', args=(ci.pk,))
        self.quick_login(self.reviewer, admin_url)
        Select(self.browser.find_element_by_id(
            'id_status')).select_by_value("in process")
        self.browser.find_element_by_id('id_category')
    
    


class ConfigurationInBackend(FunctionalTest):
    """Reviewer can specify information about login data for the reporter."""

    LOGIN_INFO = "You can find the login data for this demo installation at "
    LINK_TEXT = "the demo login data page"

    def test_reviewer_can_set_the_message_text(self):
        login_url = self.live_server_url + reverse('demo_login_data_page')
        dept = mommy.make_recipe('cirs.department')
        reviewer = mommy.make_recipe('cirs.reviewer')
        dept.reviewers.add(reviewer)
        self.quick_backend_login(reviewer.user)
        self.click_link_with_text('LabCIRS configuration')
        self.click_link_with_text(str(dept.labcirsconfig))
        self.find_input_and_enter_text('id_login_info_en', self.LOGIN_INFO)
        self.find_input_and_enter_text('id_login_info_de', self.LOGIN_INFO)
        self.find_input_and_enter_text('id_login_info_url', login_url)
        self.find_input_and_enter_text('id_login_info_link_text_en', self.LINK_TEXT)
        self.find_input_and_enter_text('id_login_info_link_text_de', self.LINK_TEXT)
        self.browser.find_element_by_name('_save').click()
        self.logout()
        #time.sleep(1)
        self.browser.get(self.live_server_url + dept.get_absolute_url())
        current_login_info = self.browser.find_element_by_class_name('alert-success').text
        self.assertIn(self.LOGIN_INFO, current_login_info)
        self.browser.find_element_by_link_text(self.LINK_TEXT)
        