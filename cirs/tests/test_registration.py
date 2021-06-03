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

import time

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from parameterized import parameterized
from registration.models import SupervisedRegistrationProfile

from cirs.models import  Department, Reporter, Reviewer

      
@override_settings(REGISTRATION_RESTRICT_USER_EMAIL=False, REGISTRATION_OPEN=True) 
class SelfRegistrationTest(TestCase):
    
    def setUp(self):
        super(SelfRegistrationTest, self).setUp()
        self.test_registration = {
            'username': 'rev',
            'first_name': 'Mighty',
            'last_name': 'Reviewer',
            'email': 'rev@localhost',
            'password1': 'rev',
            'password2': 'rev',
            'department_label': 'dept',
            'department_name': 'Dept',
            'reporter_name': 'rep',
            'tos': True
        } 
    
    def test_registration_view_uses_right_template(self):
        response = self.client.get(reverse('registration_register'), follow=True)
        self.assertTemplateUsed(response, 'registration/registration_form.html')

    @parameterized.expand([
        # The first two entries actually test the built-in functionality! 
        # But at least email should be tested
        ('username', 'A user with that username already exists.'),
        ('email', 'This email address is already in use. Please supply a different email address.'),
        ('department_label', 'Department with this label already exists!'),
        ('department_name', 'Department with this name already exists!'),
        ('reporter_name', 'This user already exists!')
    ])
    def test_no_double_entries_for(self, field, error):
        # register user and department first
        self.client.post(
            reverse('registration_register'), self.test_registration, follow=True)
       
        # repeat the registration
        response = self.client.post(
            reverse('registration_register'), self.test_registration, follow=True)
        
        # and test for errors on single fields
        self.assertFormError(response, 'form', field, [error])
    
    @parameterized.expand([
        ('reporter', 'reporter_name'),
        ('label', 'department_label'),
        ('name', 'department_name')
    ])
    def test_department_created_during_registration_has_correct(self, dept_attr, dict_key):
        self.client.post(
            reverse('registration_register'), self.test_registration, follow=True)
        # only one department exists
        dept = Department.objects.get()
        self.assertEqual(str(getattr(dept, dept_attr)), self.test_registration[dict_key])
        
    def test_registered_department_is_inactive(self):
        self.client.post(
            reverse('registration_register'), self.test_registration, follow=True)
        dept = Department.objects.get()
        self.assertEqual(dept.active, False)
        
    
    @parameterized.expand([
        ('department',),
        ('reporter',),
    ])
    @override_settings(ADMINS=('admin', 'admin@localhost'))
    def test_user_activation_activates_also(self, obj):
        # new reviewer registers new department
        self.client.post(
            reverse('registration_register'), self.test_registration, follow=True)
        
        # and activates it
        activation_key = SupervisedRegistrationProfile.objects.last().activation_key
        
        self.client.get(
            reverse('registration_activate', args=[activation_key]), follow=True)
        
        # superuser finally approves the activation
        activation_id = SupervisedRegistrationProfile.objects.last().id
        admin = User.objects.create_superuser('admin', 'admin@localhost', 'password')
        
        self.client.force_login(admin)
        self.client.get(
            reverse('registration_admin_approve', args=[activation_id]), follow=True)
        dept = Department.objects.get()
        if obj == 'department':
            self.assertEqual(dept.active, True)
        elif obj == 'reporter':
            self.assertEqual(dept.reporter.user.is_active, True)
        
    def test_disallow_foreign_email_domains(self):
        allowed_domains = ['example.org']
        with self.settings(REGISTRATION_RESTRICT_USER_EMAIL=True), self.settings(REGISTRATION_EMAIL_DOMAINS=allowed_domains):
            response = self.client.post(
                reverse('registration_register'), self.test_registration, follow=True)

            self.assertFormError(
                response, 'form', 'email', 
                ['You cannot register with this email domain! Only @example.org is allowed!'])
            
    def test_allow_multiple_email_domains(self):
        allowed_domains = ['example.org', 'nowhere.org']
        with self.settings(REGISTRATION_RESTRICT_USER_EMAIL=True), self.settings(REGISTRATION_EMAIL_DOMAINS=allowed_domains):
            response = self.client.post(
                reverse('registration_register'), self.test_registration, follow=True)

            self.assertFormError(
                response, 'form', 'email', 
                ['You cannot register with this email domain! Allowed domains are @example.org, @nowhere.org'])

    def test_create_user_with_email_from_allowed_domain(self):
        allowed_domains = ['localhost']
        with self.settings(REGISTRATION_RESTRICT_USER_EMAIL=True), self.settings(REGISTRATION_EMAIL_DOMAINS=allowed_domains):
            self.client.post(
                reverse('registration_register'), self.test_registration, follow=True)

            self.assertEqual(User.objects.last().email, self.test_registration['email'])

    def test_reporter_user_is_converted_to_lowercase(self):
        upper_case_rep = 'Reporter'
        test_registration = self.test_registration.copy()
        test_registration['reporter_name'] = upper_case_rep
        self.client.post(
            reverse('registration_register'), test_registration, follow=True)
        self.assertEqual(Reporter.objects.last().user.username, upper_case_rep.lower())

    def test_reporter_user_is_inactive_upon_registration(self):
        self.client.post(
            reverse('registration_register'), self.test_registration, follow=True)
        rep = Reporter.objects.get()
        self.assertEqual(rep.user.is_active, False)

    @parameterized.expand([
        ('first_name',),
        ('last_name',),
    ])
    def test_reviewer_has(self, name):
        self.client.post(
            reverse('registration_register'), self.test_registration, follow=True)
        rev_user = Reviewer.objects.last().user
        self.assertEqual(getattr(rev_user, name), self.test_registration[name])