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

from django.core.urlresolvers import reverse
from django.test import override_settings
from model_mommy import mommy
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from cirs.models import Reporter, Reviewer, Department, CriticalIncident, PublishableIncident
from cirs.tests.helpers import create_role, create_user
from parameterized import parameterized, param

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


class AddRolesAndDepartmentBackendTest(FunctionalTest):
    
    def setUp(self):
        super(AddRolesAndDepartmentBackendTest, self).setUp()
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


    def test_admin_can_set_department(self):
        # Admin goes to the backend 
        self.click_link_with_text("Departments")
        self.click_link_case_insensitive("Add department")
        # Now he enters the data for the new department
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
        # The name of the department is equal to the label set
        self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, self.en_dict['label'])),
            message=('could not find {}'.format(self.en_dict['label']))
        )
        
    @parameterized.expand([('reporter', 'id_reporter'), 
                           ('reviewer', 'id_reviewers_from')])
    def test_only_role_user_in_role_select_for(self, role, elem_id):
        # In the select dialogs only users assigned to roles are visible
        self.browser.get(self.live_server_url + '/admin/cirs/department/add/')
        select = Select(self.browser.find_element_by_id(elem_id))
        options = [opt.text for opt in select.options]
        expected = [role, '---------']
        if role == 'reviewer':
            expected = [role]
        self.assertItemsEqual(options, expected,
            'found {} instead {}'.format(', '.join(options), ', '.join(expected)))


    def test_assigned_reporter_not_visible_for_new_dept(self):
        # If a reporter is assigned to an department, he is not visible in
        # the dialog for a new department anymore 
        Department.objects.create(**self.en_dict)
        new_reporter = create_role(Reporter, 'new_reporter')
        self.browser.get(self.live_server_url + '/admin/cirs/department/add/')
        select = Select(self.browser.find_element_by_id('id_reporter'))
        options = [opt.text for opt in select.options]
        expected = [str(new_reporter), '---------']
        self.assertItemsEqual(options, expected,
            'found {} instead {}'.format(', '.join(options), ', '.join(expected)))

    def test_admin_can_modify_departments_name(self):
        dept = Department.objects.create(**self.en_dict)
        dept.reviewers.add(self.reviewer)
        self.browser.get(self.live_server_url + get_admin_url(dept))
        self.find_input_and_enter_text('id_name', 'The best lab in the world')
        self.browser.find_element_by_name('_save').click()
        self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, self.en_dict['label'])),
            message=('could not find {}'.format(self.en_dict['label']))
        )

   
class SecurityFrontendTest(FunctionalTest):
    """
    User without role sees error message
    Reporter without department sees error message
    Reporter with department sees only incidents belonging to his department
    """
 
    def test_log_out_and_error_message_for_user_without_role(self):
        from cirs.views import MISSING_ROLE_MSG  # necessary only here so far
        user = create_user('cirs_user')
        self.login_user(username=user.username, password=user.username)

        error_alert = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, 'alert-danger')))

        self.assertEqual(error_alert.text, MISSING_ROLE_MSG)
        
        with self.assertRaises(NoSuchElementException):
            nav = self.browser.find_element_by_id('navbarMenu')
            self.assertNotIn('View incidents', nav.text)

    
    @parameterized.expand([
        ('rep', Reporter), 
        ('rev', Reviewer)
    ])
    def test_log_out_and_error_message_for_role_without_department(self, name, role_cls):
        from cirs.views import MISSING_DEPARTMENT_MSG  # necessary only here so far
        role = create_role(role_cls, name)
        self.login_user(username=role.user.username, password=role.user.username)

        error_alert = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, 'alert-danger')))
        self.assertEqual(error_alert.text, MISSING_DEPARTMENT_MSG)
        
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_id('navbarMenu')

    def test_reporter_with_department_is_redirected_to_incident_list(self):
        reporter = create_role(Reporter, 'rep')
        mommy.make(Department, reporter=reporter)
        self.login_user(username=reporter.user.username, password=reporter.user.username)
        time.sleep(2)
        redirect_url = '{}{}'.format(self.live_server_url, reverse('incidents_list'))
        self.assertEqual(self.browser.current_url, redirect_url)
        
    def test_reviewer_with_department_is_redirected_to_admin(self):
        reporter = create_role(Reporter, 'rep')
        reviewer = create_role(Reviewer, 'rev')
        dept = mommy.make(Department, reporter=reporter)
        dept.reviewers.add(reviewer)
        self.login_user(username=reviewer.user.username, password=reviewer.user.username)
        time.sleep(2)
        redirect_url = '{}{}'.format(self.live_server_url, reverse('admin:index'))
        self.assertEqual(self.browser.current_url, redirect_url)
        
#     @parameterized.expand([
#         param('cirs_user'),
#         param('rep', Reporter),
#         param('rev', Reviewer),
#         param('superman', superuser=True)
#     ]) 
    def test_reporter_can_access_create_incident_view(self):
        user = create_role(Reporter, 'rep').user
        self.quick_login(user, reverse('create_incident'))
        target_url = '{}{}'.format(self.live_server_url, reverse('create_incident'))
        self.assertEqual(self.browser.current_url, target_url)
        
    def test_redirect_reviewer_from_create_incident_view_to_list(self):
        user = create_role(Reviewer, 'rev').user
        self.quick_login(user, reverse('create_incident'))
        target_url = '{}{}'.format(self.live_server_url, reverse('incidents_list'))
        self.assertEqual(self.browser.current_url, target_url)

    def test_user_cannot_access_create_incident_view(self):
        user = create_user('cirs_user')
        self.quick_login(user, reverse('create_incident'))
        target_url = '{}{}'.format(self.live_server_url, reverse('login'))
        self.assertEqual(self.browser.current_url, target_url)
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_id('navbarMenu')
        
    def test_redirect_admin_from_create_incident_view_to_admin(self):
        user = create_user('superman', superuser=True)
        self.quick_login(user, reverse('create_incident'))
        target_url = '{}{}'.format(self.live_server_url, reverse('admin:index'))
        self.assertEqual(self.browser.current_url, target_url)
        
    def test_anonymous_cannot_access_create_incident_view(self):
        self.browser.get('{}{}'.format(self.live_server_url,
                                       reverse('create_incident')))
        target_url = '{}{}'.format(self.live_server_url, reverse('login'))
        self.assertEqual(self.browser.current_url, target_url)
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_id('navbarMenu')

# TODO: Reviewer should not see departments and reviewers(?). Probably also not reporters
# although he should may change reporter password for own department

@override_settings(DEBUG=True)
class AccessDataWithMultipleDepts(FunctionalTest):
    # if the class is run in isolation, the tests pass with following set to true
    serialized_rollback = True
    # if run as whole suite, there are exceptions with unique constraint!
        
    def check_admin_table_for_items(self, user, cls_name, present=None, absent=None):
        admin_url = reverse('admin:cirs_{}_changelist'.format(cls_name._meta.model_name))
        self.quick_backend_login(user, admin_url)
        self.wait.until(EC.url_contains(admin_url))
        if present:
            self.browser.find_element_by_link_text(present)
        if absent:
            with self.assertRaises(NoSuchElementException):
                self.browser.find_element_by_link_text(absent)



    def setUp(self):
        super(AccessDataWithMultipleDepts, self).setUp()
        self.rep = create_role(Reporter, 'rep')
        self.rep2 = create_role(Reporter, 'rep2')
        self.rev = create_role(Reviewer, 'rev')
        self.rev2 = create_role(Reviewer, 'rev2')
        self.dept = mommy.make(Department, reporter=self.rep)
        self.dept.reviewers.add(self.rev)
        self.dept2 = mommy.make(Department, reporter=self.rep2)
        self.dept2.reviewers.add(self.rev2)
        self.ci = mommy.make_recipe('cirs.public_ci', department=self.dept)
        self.ci2 = mommy.make_recipe('cirs.public_ci', department=self.dept2)
        self.pi = mommy.make_recipe('cirs.published_incident', critical_incident=self.ci)
        self.pi2 = mommy.make_recipe('cirs.published_incident', critical_incident=self.ci2)
    
    def get_test_cases():  # @NoSelf
        return[
            ('rep', 'pi', 'pi2'),
            ('rep2', 'pi2', 'pi'),
            ('rev', 'pi', 'pi2'),
            ('rev2', 'pi2', 'pi'),
        ]
    
    @parameterized.expand(get_test_cases)
    def test_role_sees_only_published_incidents_from_his_department(self, user, pi1, pi2):
       
        # first reporter logs in and sees only incidents associated with his 
        # department
        role = getattr(self, user)
        own_pi = getattr(self, pi1)
        alien_pi = getattr(self, pi2)
        self.quick_login(role.user)
        table = self.wait.until(EC.presence_of_element_located((By.ID, 'tableIncidents')))
        rows = table.find_elements_by_tag_name('tr')
        
        self.assertIn(own_pi.incident_en, [row.text for row in rows])
        self.assertNotIn(alien_pi.incident_en, [row.text for row in rows])


    def get_test_reviewers():  # @NoSelf
        return [
            ('rev',),
            ('rev2',)
        ]

    @parameterized.expand(get_test_reviewers)
    def test_reviewer_sees_only_cis_of_his_dept_in_backend(self, user):
        role = getattr(self, user)
        own_item = CriticalIncident.objects.filter(
            department__in=role.departments.all()).first().incident
        foreign_item = CriticalIncident.objects.exclude(
            department__in=role.departments.all()).first().incident
        self.check_admin_table_for_items(role.user, CriticalIncident, own_item, foreign_item)

    @parameterized.expand(get_test_reviewers)
    def test_reviewer_sees_only_pis_of_his_dept_in_backend(self, user):
        role = getattr(self, user)
        own_item = PublishableIncident.objects.filter(
            critical_incident__department__in=role.departments.all()).first().incident_de
        foreign_item = PublishableIncident.objects.exclude(
            critical_incident__department__in=role.departments.all()).first().incident_de
        self.check_admin_table_for_items(role.user, PublishableIncident, own_item, foreign_item)

    @parameterized.expand([
        (CriticalIncident, 'incident'),
        (PublishableIncident, 'incident_de')
    ])
    def test_admin_sees_no_incidents(self, model_cls, field):
        admin = create_user('superman', superuser=True)
        for incident in model_cls.objects.all():
            self.check_admin_table_for_items(admin, model_cls, absent=getattr(incident, field))
