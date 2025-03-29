# Copyright (C) 2018-2025 Sebastian Major
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

from django.contrib.auth.models import User
from django.urls.base import reverse
from model_mommy import mommy
from parameterized import parameterized
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from cirs.models import Reviewer
from cirs.tests.helpers import create_role

from .base import FunctionalTest
from .test_multiorganization import get_admin_url


class CriticalIncidentBackendTest(FunctionalTest):
    """
    Added when incident was extended with category
    """

    def test_reviewer_can_chose_category_of_incident(self):
        ci = mommy.make_recipe('cirs.public_ci')
        ci.department.reviewers.add(create_role(Reviewer, self.reviewer))
        admin_url = reverse('admin:cirs_criticalincident_change', args=(ci.pk,))
        self.quick_login(self.reviewer, admin_url)
        # uncollapse the review panel
        self.click_link_with_text('Show')
        Select(self.browser.find_element(By.ID,
            'id_status')).select_by_value("in process")
        self.browser.find_element(By.ID, 'id_category')
    
    


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
        self.find_input_and_enter_text('id_login_info', self.LOGIN_INFO)
        self.find_input_and_enter_text('id_login_info_url', login_url)
        self.find_input_and_enter_text('id_login_info_link_text', self.LINK_TEXT)
        self.browser.find_element(By.NAME, '_save').click()
        self.logout()
        self.browser.get(self.live_server_url + dept.get_absolute_url())
        current_login_info = self.browser.find_element(By.CLASS_NAME, 'alert-success').text
        self.assertIn(self.LOGIN_INFO, current_login_info)
        self.browser.find_element(By.LINK_TEXT, self.LINK_TEXT)


class AccessRestriction(FunctionalTest):
    
    def setUp(self):
        super(AccessRestriction, self).setUp()
        self.rev, self.rev2 = mommy.make_recipe('cirs.reviewer', _quantity=2)
        self.dept, self.dept2 = mommy.make_recipe('cirs.department', _quantity=2)
        self.dept.reviewers.add(self.rev)
        self.dept2.reviewers.add(self.rev2)
    
    @parameterized.expand(['rep2', 'rev1', 'rev2'])
    def test_reviewer_can_see_only_users_which_are_reporters_in_his_departments(self, username):
        # check if the username really exist. Now we relay on model mommy
        if User.objects.get(username=username):
            self.check_admin_table_for_items(self.rev.user, User, self.dept.reporter.user.username, username)
        else:
            self.fail('user {} does not exist'.format(username))

    WANTED_INPUTS = ['csrfmiddlewaretoken', 'username', 'first_name', 'last_name', '_save', '_continue']
    PROHIBITED_INPUTS = ['email', 'is_active', 'is_staff', 'is_superuser', 'last_login_0',
                         'last_login_1', 'date_joined_0', 'date_joined_1', 'initial-date_joined_0',
                         'initial-date_joined_1']

    @parameterized.expand(WANTED_INPUTS)
    def test_reviewer_can_change_only_username_and_password_of_reporter_user(self, input_name):
        target = get_admin_url(self.dept.reporter.user)
        self.quick_login(self.rev.user, target)
        inputs = self.browser.find_elements(By.TAG_NAME, 'input')
        input_names  = [inpt.get_attribute('name') for inpt in inputs]
        self.assertIn(input_name, input_names)

    @parameterized.expand(PROHIBITED_INPUTS)
    def test_reviewer_cannot_see_important_fields_of_reporter_user(self, input_name):
        target = get_admin_url(self.dept.reporter.user)
        self.quick_login(self.rev.user, target)
        inputs = self.browser.find_elements(By.TAG_NAME, 'input')
        input_names  = [inpt.get_attribute('name') for inpt in inputs]
        self.assertNotIn(input_name, input_names)
        
    def test_reviewer_cannot_see_select_boxes_in_reporter_user_change_page(self):
        target = get_admin_url(self.dept.reporter.user)
        self.quick_login(self.rev.user, target)
        selects = self.browser.find_elements(By.TAG_NAME, 'select')
        self.assertEqual(len(selects), 0)
        
    def test_reviewer_cannot_access_unlisted_users_by_direct_link(self):
        target = get_admin_url(self.dept2.reporter.user)
        self.quick_login(self.rev.user, target)
        redirect_url = '{}{}'.format(self.live_server_url, reverse('admin:index'))
        self.assertEqual(self.browser.current_url, redirect_url)
