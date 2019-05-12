# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 Sebastian Major
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

from django.core import mail
from django.contrib.auth.models import User
from django.urls.base import reverse
from model_mommy import mommy
from parameterized import parameterized

from .test_frontend import FrontendBaseTest
from .test_multiorganization import get_admin_url

import time
from registration.models import SupervisedRegistrationProfile


class SelfRegistrationTest(FrontendBaseTest):
    """
    Tests for self registration of reviewer and department
    """
    
    def go_to_view(self, view, *args):
        if args is None:
            my_url = reverse(view)
        else:
            my_url = reverse(view, args=args)
        self.browser.get(self.live_server_url + my_url)
    
    def test_new_reviewer_can_register_new_department(self):
        # New user visits the LabCIRS page 
        self.browser.get(self.live_server_url)
        # He cannot find his department 
        # TODO: Hint for missing department needed
        
        # He clicks on the "Register" link
        self.click_link_with_text('Register')
        # and finds the registration form where he enters the data
        self.find_input_and_enter_text('id_username', 'rev')
        self.find_input_and_enter_text('id_email', 'rev@localhost')
        self.find_input_and_enter_text('id_password1', 'rev')
        self.find_input_and_enter_text('id_password2', 'rev')
        self.find_input_and_enter_text('id_department_label', 'dept')
        self.find_input_and_enter_text('id_department_name', 'Dept')
        self.find_input_and_enter_text('id_reporter_name', 'rep')
        self.browser.find_element_by_id("id_tos").click()

        # finally he clicks on the "Submit" button
        # TODO: Change to "Register"?
        self.browser.find_element_by_class_name("btn-danger").click()

        # and lands on the success page
        self.assertCurrentUrlIs(reverse('registration_complete'))
        
        # User clicks on the confirmation link in the email
        self.go_to_view('registration_activate',
                        SupervisedRegistrationProfile.objects.last().activation_key)
        
        # Then admin activates the accounts and the department 
        self.quick_backend_login()
        self.go_to_view('registration_admin_approve',
                        SupervisedRegistrationProfile.objects.last().id)
        self.logout()

        # now the new department label is in the list
        labels = self.get_column_from_table_as_list('table_departments')
        self.assertIn('dept', labels)
        time.sleep(5)
        # we do not need to test everything, but
        
    # TODO: Add tests for double entries which should be unique
    # Add tests for proper email domain
