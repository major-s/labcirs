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

import time
from unittest import skip

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy, reverse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from cirs.models import Reporter, Reviewer, Organization
from cirs.tests.test_multiorganization import create_role, create_user
from parameterized import parameterized

from .base import FunctionalTest


def get_admin_url(instance, operation='change'):
    """Return the admin url for an object instance.

    Parameters
    ----------
    instance: object
        Object instance which should be accessed in the backend
    operation: str
        Desired operation to perform. Default is 'change' as the most common one.

    Returns
    -------
    str
        Url of the object in the backend

    """
    admin_url = reverse(
        'admin:{}_{}_{}'.format(
            instance._meta.app_label, instance._meta.model_name, operation
        ),
        args=(instance.pk,)
    )
    return admin_url


class MultipleOrganizationBackendTest(FunctionalTest):
    
    def setUp(self):
        super(MultipleOrganizationBackendTest, self).setUp()
        self.user = create_user('cirs_user')
        self.reporter = Reporter.objects.create(user=self.reporter)
        self.reviewer = Reviewer.objects.create(user=self.reviewer)
        self.en_dict = {
            'label': 'EN',
            'name': 'Experimenting Nerds',
            'reporter': self.reporter,
        }
        
        # quick login for the  admin
        self.quick_backend_login()
         
    @parameterized.expand([
        ('reporter', 'Reporters'), 
        ('reviewer', 'Reviewers')
    ])
    def test_admin_can_set_user_role_as(self, role, class_name):
        self.click_link_with_text(class_name)
        self.click_link_case_insensitive('Add {}'.format(role))
        Select(
            self.browser.find_element_by_id('id_user')
        ).select_by_visible_text(self.user.username)
        self.browser.find_element_by_name('_save').click()
        self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, self.user.username)),
            message=('could not find %s' % self.user.username)
        )


    # Admin can chose only use who does not has any role assigned 
    # (including superuser)
    @parameterized.expand([('reporter',), ('reviewer',)])
    def test_only_user_without_role_in_select(self, role):
        self.browser.get(self.live_server_url + '/admin/cirs/{}/add/'.format(role))
        select = Select(self.browser.find_element_by_id('id_user'))
        options = [opt.text for opt in select.options]
        # there is also an empty choice
        self.assertItemsEqual(options, [self.user.username, '---------'])


    def test_admin_can_set_organization(self):
        # Admin goes to the backend 
        self.click_link_with_text("Organizations")
        self.click_link_case_insensitive("Add organization")
        # Now he enters the data for the new organization
        self.find_input_and_enter_text('id_label', self.en_dict['label'])
        self.find_input_and_enter_text('id_name', self.en_dict['name'])
        Select(
            self.browser.find_element_by_id('id_reporter')
        ).select_by_visible_text(str(self.en_dict['reporter']))
        Select(
            self.browser.find_element_by_id('id_reviewers_from')
        ).select_by_visible_text('reviewer')
        self.browser.find_element_by_id('id_reviewers_add_link').click()
        self.browser.find_element_by_name('_save').click()
        # The name of the organization is equal to the label set
        self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, self.en_dict['label'])),
            message=('could not find {}'.format(self.en_dict['label']))
        )
        
    @parameterized.expand([('reporter', 'id_reporter'), 
                           ('reviewer', 'id_reviewers_from')])
    def test_only_role_user_in_role_select_for(self, role, id):
        # In the select dialogs only users assigned to roles are visible
        self.browser.get(self.live_server_url + '/admin/cirs/organization/add/')
        select = Select(self.browser.find_element_by_id(id))
        options = [opt.text for opt in select.options]
        expected = [role, '---------']
        if role == 'reviewer':
            expected = [role]
        self.assertItemsEqual(options, expected,
            'found {} instead {}'.format(', '.join(options), ', '.join(expected)))


    def test_assigned_reporter_not_visible_for_new_org(self):
        # If a reporter is assigned to an organization, he is not visible in
        # the dialog for a new organization anymore 
        Organization.objects.create(**self.en_dict)
        new_reporter = create_role(Reporter, 'new_reporter')
        self.browser.get(self.live_server_url + '/admin/cirs/organization/add/')
        select = Select(self.browser.find_element_by_id('id_reporter'))
        options = [opt.text for opt in select.options]
        expected = [str(new_reporter), '---------']
        self.assertItemsEqual(options, expected,
            'found {} instead {}'.format(', '.join(options), ', '.join(expected)))

    def test_admin_can_modify_organizations_name(self):
        org = Organization.objects.create(**self.en_dict)
        self.browser.get(self.live_server_url + get_admin_url(org))
        self.find_input_and_enter_text('id_name', 'The best lab in the world')
        self.browser.find_element_by_name('_save').click()
        self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, self.en_dict['label'])),
            message=('could not find {}'.format(self.en_dict['label']))
        )