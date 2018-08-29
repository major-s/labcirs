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

import itertools
from unittest import skip

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User, Permission
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.db import IntegrityError
from django.test import TestCase
from parameterized import parameterized

from cirs.models import Organization, Reporter, Reviewer, CriticalIncident
from cirs.admin import OrganizationAdmin
from django.core.management import call_command

from model_mommy import mommy


class AdminRegistration(TestCase):
    
    @parameterized.expand([(Organization,), (Reporter,), (Reviewer,)])
    def test_registration(self, model):
        self.assertTrue(admin.site.is_registered(model), "{} not registered".format(model))


def create_user(name=None, superuser=False):
    if superuser is True:
        user = User.objects.create_superuser(name, '%s@localhost' % name, name)
    else:
        user = User.objects.create_user(name, '%s@localhost' % name, name)
    return user

def create_role(role_cls, name):
    return role_cls.objects.create(user=create_user(name))


def create_user_with_perm(name, codename):
    user = create_user(name)
    permission = Permission.objects.get(codename=codename)
    user.user_permissions.add(permission)
    return user

class OrganizationBase(TestCase):
    
    def setUp(self):

        self.user = create_user('cirs_user')
        self.reporter = create_role(Reporter, 'reporter')
        self.reviewer = create_role(Reviewer, 'reviewer')
        self.admin = create_user('admin', superuser=True)
    
        self.en_dict = {
            'label': 'EN',
            'name': 'Experimenting Nerds',
            'reporter': self.reporter,
        }
        

class OrganizationTest(OrganizationBase):

    def test_organization_admin_name_is_label(self):
        org = Organization.objects.create(**self.en_dict)
        self.assertEqual(str(org), org.label)


    @parameterized.expand([('label',), ('name',), ('reporter')])
    def test_unique_org_field(self, field):
        fe_dict = {
            'label': 'FE',
            'name': 'Experimenting Noobs',
            'reporter': create_role(Reporter, 'reporter_fe'),
        }
        # create first organization
        Organization.objects.create(**self.en_dict)
        # create second organization object
        org = Organization(**fe_dict)
        # and set fields equal to first organization
        setattr(org, field, self.en_dict[field])
        with self.assertRaises(IntegrityError):
            org.save()


    def test_assigned_reporter_does_not_appear_in_admin_form_for_new_org(self):
        Organization.objects.create(**self.en_dict)
        form = OrganizationAdmin(Organization, admin.AdminSite()).get_form(None)
        self.assertNotIn(
            self.reporter, form().fields['reporter'].choices.queryset,
            '''Found {} in select for new organization although he already is 
            the reporter for {}'''.format(
                str(self.reporter), self.reporter.organization
            )
        )

    def test_assigned_reporter_appears_in_admin_form_for_his_org(self):
        org = Organization.objects.create(**self.en_dict)
        form = OrganizationAdmin(Organization, admin.AdminSite()).get_form(org)
        self.assertIn(
            org.reporter, form().fields['reporter'].choices.queryset,
            'Did not found {} in select for {} although he is assigned'.format(
                str(org.reporter), org
            )
        )

    def test_reviewers_use_filter_horizontal(self):
        self.assertIn('reviewers', OrganizationAdmin.filter_horizontal)

class ReviewerReporterModel(OrganizationBase):
    """
    User can be assigned only to one role. Superuser cannot be assigned to any role.
    """

    def gen_test_cases():
        # don't has access to users generated in setUp! 
        return [
        ('reporter', Reporter),
        ('reviewer', Reviewer)
    ]

    @parameterized.expand(gen_test_cases)
    def test_role_has_username(self, _, role_cls):
        role = role_cls.objects.create(user=self.user)
        self.assertEqual(str(role), self.user.username)
    
    @parameterized.expand(gen_test_cases)
    def test_user_can_have_role_only_once(self, _, role_cls):
        role1 = role_cls.objects.create(user=self.user)
        with self.assertRaises(IntegrityError):
            role2 = role_cls.objects.create(user=self.user)

    @parameterized.expand(gen_test_cases)
    def test_superuser_cannot_have_cirs_role(self, _, role_cls):
        with self.assertRaises(ValidationError):
            role = role_cls(user=self.admin)
            role.full_clean()

    @parameterized.expand([
        ('reporter', Reporter, Reviewer),
        ('reviewer', Reviewer, Reporter)
    ])
    def test_user_cannot_be_reporter_and_reviewer(self, _, class1, class2):
        role1 = class1.objects.create(user=self.user)
        with self.assertRaises(ValidationError):
            role2 = class2(user=self.user)
            role2.full_clean()

    @parameterized.expand(
        list(itertools.product((Reporter, Reviewer), (Reviewer, Reporter)))
    )
    def test_user_with_role_does_not_apear_in_admin_form(self, model_cls, role_cls):
        role = role_cls.objects.create(user=self.user)
        form = admin.ModelAdmin(model_cls, admin.AdminSite()).get_form(None)
        self.assertNotIn(
            self.user.username, form().as_p(),
            'found {} in {} select although he already is a {}'.format(
                self.user.username, model_cls.__name__, type(role).__name__
            )
        )
        
    @parameterized.expand(gen_test_cases)            
    def test_superuser_does_not_apear_in_admin_form_for(self, _, role_cls):
        form = admin.ModelAdmin(role_cls, admin.AdminSite()).get_form(None)
        self.assertNotIn(
            self.admin.username, form().as_p(),
            'found {} in {} select although he already is a superuser'.format(
                self.admin.username, role_cls.__name__
            )
        )

from django.core.management import call_command
from django.utils.six import StringIO

class DataMigrationForOrganization(TestCase):

    def setUp(self):
        # has to perform forward migration, so 
        out = StringIO()
        call_command('migrate', 'cirs', '0005', stdout=out)
        #print out.getvalue()

    def gen_test_role_classes():
        return [
        ('reporter', Reporter),
        ('reviewer', Reviewer)
    ]

    @parameterized.expand(gen_test_role_classes)
    def test_migration_goes_further_if_there_is_no_fitting_user(self, _, role_cls):
        # important for initial migration
        out = StringIO()
        call_command('migrate', 'cirs', '0006', stdout=out)
        #print out.getvalue()
        self.assertEqual(role_cls.objects.count(), 0)
     
    @parameterized.expand([
        ('reporter', 'add_criticalincident', Reporter),
        ('reviewer', 'change_criticalincident', Reviewer)
    ])        
    def test_migration_creates_role_based_on_user_perms(self, name, codename, role_cls):
        user = create_user_with_perm(name, codename)
        permission = Permission.objects.get(codename=codename)
        out = StringIO()
        call_command('migrate', 'cirs', '0006', stdout=out)
        self.assertEqual(role_cls.objects.first().user, user)        
        self.assertIn(permission, role_cls.objects.first().user.user_permissions.all())
        
    def test_migration_stops_if_there_is_more_than_one_user_with_reporter_rights(self):
        reporter = create_user_with_perm('reporter', 'add_criticalincident')
        reporter2 = create_user_with_perm('reporter2', 'add_criticalincident')
        out = StringIO()
        with self.assertRaises(MultipleObjectsReturned):
            call_command('migrate', 'cirs', '0006', stdout=out)

    
    def test_all_users_with_reviewer_permissions_are_assigned_to_reviewer_role(self):
        reviewer = create_user_with_perm('reviewer', 'change_criticalincident')
        reviewer2 = create_user_with_perm('reviewer2', 'change_criticalincident')

        out = StringIO()
        call_command('migrate', 'cirs', '0006', stdout=out)
        self.assertEqual(Reviewer.objects.count(), 2)

    def test_no_omnipotent_users(self):
        # generates exception if any user has add and change permissions 
        # afterwards no reperter and no reviewer should be present
        user = create_user_with_perm('user', 'add_criticalincident')
        permission = Permission.objects.get(codename='change_criticalincident')
        user.user_permissions.add(permission)
        out = StringIO()
        with self.assertRaises(ValidationError):
            call_command('migrate', 'cirs', '0006', stdout=out)
        #print out.getvalue()


# TODO: If there are no suitable users, check if the incident count is equal to zero
# if not raise exception
    
    
    @parameterized.expand([
        ('none', ''),
        ('reporter', 'add_criticalincident'),
        ('reviewer', 'change_criticalincident')
    ])   
    def test_users_with_role_permission_has_to_exist_if_there_are_incidents(self, name, codename):
        ci = mommy.make(CriticalIncident, public=True)
        if name != 'none':
            create_user_with_perm(name, codename)
        out = StringIO()
        with self.assertRaises(ValidationError):
            call_command('migrate', 'cirs', '0006', stdout=out)
        #print out.getvalue()
        
    def test_create_organization(self):
        reporter = create_user_with_perm('rep', 'add_criticalincident')
        reviewer = create_user_with_perm('rev', 'change_criticalincident')
        out = StringIO()
        call_command('migrate', 'cirs', '0006', stdout=out)
        # there should be Organization with label equal to organization in settings
        org = Organization.objects.get(label=settings.ORGANIZATION)
        self.assertEqual(org.reporter.user, reporter)
        self.assertIn(reviewer.reviewer, org.reviewers.all())
        print out.getvalue()
