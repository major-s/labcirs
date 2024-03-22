# -*- coding: utf-8 -*-
#
# Copyright (C) 2018-2024 Sebastian Major
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

from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.test import tag
from django_migration_testcase import MigrationTest
from django_migration_testcase.base import idempotent_transaction
from model_mommy import mommy
from parameterized import parameterized

from cirs.models import Reporter, Reviewer

from .helpers import create_user_with_perm

@tag('migration')
class DataMigrationForDepartment(MigrationTest):
    
    app_name = 'cirs'
    before = '0005'
    after = '0006'

    def gen_test_role_classes():  # @NoSelf
        return [
        ('reporter', Reporter),
        ('reviewer', Reviewer)
    ]

    @parameterized.expand(gen_test_role_classes)
    def test_migration_goes_further_if_there_is_no_fitting_user(self, _, role_cls):
        # important for initial migration
        self.run_migration()
        self.assertEqual(role_cls.objects.count(), 0)
     
    @parameterized.expand([
        ('reporter', 'add_criticalincident', Reporter),
        ('reviewer', 'change_criticalincident', Reviewer)
    ])        
    def test_migration_creates_role_based_on_user_perms(self, name, codename, role_cls):
        user = create_user_with_perm(name, codename)
        permission = Permission.objects.get(codename=codename)
        self.run_migration()
        self.assertEqual(role_cls.objects.first().user, user)        
        self.assertIn(permission, role_cls.objects.first().user.user_permissions.all())
    
    @idempotent_transaction
    def test_migration_stops_if_there_is_more_than_one_user_with_reporter_rights(self):
        create_user_with_perm('reporter', 'add_criticalincident')
        create_user_with_perm('reporter2', 'add_criticalincident')

        with self.assertRaises(MultipleObjectsReturned):
            self.run_migration()
    
    def test_all_users_with_reviewer_permissions_are_assigned_to_reviewer_role(self):
        create_user_with_perm('reviewer', 'change_criticalincident')
        create_user_with_perm('reviewer2', 'change_criticalincident')

        self.run_migration()
        self.assertEqual(Reviewer.objects.count(), 2)

    @idempotent_transaction
    def test_no_omnipotent_users(self):
        # generates exception if any user has add and change permissions 
        # afterwards no reperter and no reviewer should be present
        user = create_user_with_perm('user', 'add_criticalincident')
        permission = Permission.objects.get(codename='change_criticalincident')
        user.user_permissions.add(permission)

        with self.assertRaises(ValidationError):
            self.run_migration()

    @parameterized.expand([
        ('none', ''),
        ('reporter', 'add_criticalincident'),
        ('reviewer', 'change_criticalincident')
    ])
    @idempotent_transaction
    def test_users_with_role_permission_has_to_exist_if_there_are_incidents(self, name, codename):
        # tests if there are users for all roles
        CriticalIncident = self.get_model_before('CriticalIncident')
        mommy.make(CriticalIncident, public=True)
        if name != 'none':
            create_user_with_perm(name, codename)

        with self.assertRaises(ValidationError):
            self.run_migration()

    def test_dont_create_department_without_valid_configuration(self):
        # Department should be created only if there is valid configuration.
        # As anyway only the first one was used, there is no need for a check of
        # multiple configurations.
        # Actually there should be no running installation without
        create_user_with_perm('rep', 'add_criticalincident')
        create_user_with_perm('rev', 'change_criticalincident')
        
        self.run_migration()
        
        Department = self.get_model_after('Department')
        self.assertEqual(Department.objects.count(), 0)
    
    @parameterized.expand([
        ('none', ''),
        ('reporter', 'add_criticalincident'),
        ('reviewer', 'change_criticalincident')
    ]) 
    def test_dont_create_department_without_valid_roles(self, name, codename):
        if name != 'none':
            create_user_with_perm(name, codename)
        
        self.run_migration()

        Department = self.get_model_after('Department')
        self.assertEqual(Department.objects.count(), 0)

    def test_create_department(self):
        reporter = create_user_with_perm('rep', 'add_criticalincident')
        reviewer = create_user_with_perm('rev', 'change_criticalincident')
        LabCIRSConfig = self.get_model_before('LabCIRSConfig')
        mommy.make(LabCIRSConfig, send_notification=False)

        self.run_migration()
        # there should be department with label equal to organization in settings
        Department = self.get_model_after('Department')
        dept = Department.objects.get(label=settings.ORGANIZATION)

        # fortunatelly user names are unique...
        self.assertEqual(str(reporter), dept.reporter.user.username)
        self.assertIn(reviewer.username, [rev.user.username for rev in dept.reviewers.all()])


@tag('migration')
class TestBeforeAddingOrganizationToIncidents(MigrationTest):
    
    app_name = 'cirs'
    before = '0006'
    after = '0007'
    
    def make_instance(self, cls_name):
        if cls_name._meta.model_name == 'criticalincident':
            return mommy.make(cls_name, public=True)
        else:
            return mommy.make(cls_name) 
    
    @parameterized.expand([
        ('CriticalIncident',),
        ('LabCIRSConfig',),
    ])
    @idempotent_transaction
    def test_migration_stops_if_there_is_no_department_but(self, model_name):
        cls_name = self.get_model_before(model_name)
        self.make_instance(cls_name)

        with self.assertRaises(ValidationError):
            self.run_migration()

    @parameterized.expand([
        ('CriticalIncident',),
        ('LabCIRSConfig',),
    ])
    def test_pk_of_existing_department_is_used_for(self, model_name):
        Department = self.get_model_before('Department')
        dept = mommy.make(Department, pk=2)

        cls_name = self.get_model_before(model_name)
        self.make_instance(cls_name)
        
        self.run_migration()
        
        cls_name_after = self.get_model_after(model_name)
        instance = cls_name_after.objects.first()

        self.assertEqual(dept.pk, instance.department.pk)

    @parameterized.expand([
        ('none',),
        ('CriticalIncident',),
        ('LabCIRSConfig',),
    ])
    @idempotent_transaction
    def test_migration_stops_if_there_are_multiple_departments_and(self, model_name):
        Department = self.get_model_before('Department')
        mommy.make(Department, _quantity=2)
        if model_name != 'none':
            cls_name = self.get_model_before(model_name)
            self.make_instance(cls_name)

        with self.assertRaises(MultipleObjectsReturned):
            self.run_migration()
    
    @idempotent_transaction
    def test_migration_stops_if_there_are_multiple_configurations(self):
        Department = self.get_model_before('Department')
        mommy.make(Department)
        LabCIRSConfig = self.get_model_before('LabCIRSConfig')
        mommy.make(LabCIRSConfig, _quantity=2)
        with self.assertRaises(MultipleObjectsReturned):
            self.run_migration()
    
    def test_migration_runs_on_empty_database(self):
        self.run_migration()
        CriticalIncident = self.get_model_after('CriticalIncident')
        self.assertEqual(CriticalIncident.objects.count(), 0)