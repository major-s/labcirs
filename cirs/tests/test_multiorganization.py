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
from django.contrib import admin, auth
from django.contrib.auth.models import Permission
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.test import TestCase, RequestFactory
from django.utils.six import StringIO
from parameterized import parameterized

from cirs.models import Organization, Reporter, Reviewer, CriticalIncident, LabCIRSConfig, PublishableIncident
from cirs.admin import OrganizationAdmin, RoleAdmin
from cirs.views import PublishableIncidentList, IncidentCreate
from django.core.management import call_command

from model_mommy import mommy

from .helpers import create_user, create_user_with_perm, create_role

class AdminRegistration(TestCase):
    
    @parameterized.expand([(Organization,), (Reporter,), (Reviewer,)])
    def test_registration(self, model):
        self.assertTrue(admin.site.is_registered(model), "{} not registered".format(model))




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
        form = OrganizationAdmin(Organization, admin.AdminSite()).get_form(None, obj=org)
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
        form = RoleAdmin(model_cls, admin.AdminSite()).get_form(None)
        self.assertNotIn(
            self.user.username, form().as_p(),
            'found {} in {} select although he already is a {}'.format(
                self.user.username, model_cls.__name__, type(role).__name__
            )
        )
        
    @parameterized.expand(gen_test_cases)            
    def test_superuser_does_not_apear_in_admin_form_for(self, _, role_cls):
        form = RoleAdmin(role_cls, admin.AdminSite()).get_form(None)
        self.assertNotIn(
            self.admin, form().fields['user'].choices.queryset,
            'found {} in {} select although he already is a superuser'.format(
                self.admin.username, role_cls.__name__
            )
        )


    @parameterized.expand(gen_test_cases)            
    def test_user_apears_in_admin_in_asigned_role(self, _, role_cls):
        role = role_cls.objects.create(user=self.user)
        form = RoleAdmin(role_cls, admin.AdminSite()).get_form(None, obj=role)
        self.assertIn(
            role.user, form().fields['user'].choices.queryset,
            'Did not found {} in select for {} although he is assigned'.format(
                role.user, role_cls.__name__
            )
        )
        
    @parameterized.expand(gen_test_cases)            
    def test_assifned_user_does_not_apears_in_admin_in_new_role(self, _, role_cls):
        role = role_cls.objects.create(user=self.user)
        form = RoleAdmin(role_cls, admin.AdminSite()).get_form(None)
        self.assertNotIn(
            role.user, form().fields['user'].choices.queryset,
            'Found {} in select for {} although he is assigned as {}'.format(
                role.user, role_cls.__name__, role
            )
        )

class DataMigrationForOrganization(TestCase):

    def setUp(self):
        # has to perform forward migration, so 
        out = StringIO()
        call_command('migrate', 'cirs', '0005', stdout=out)
        #print out.getvalue()
        self.out = StringIO()

    def gen_test_role_classes():
        return [
        ('reporter', Reporter),
        ('reviewer', Reviewer)
    ]

    @parameterized.expand(gen_test_role_classes)
    def test_migration_goes_further_if_there_is_no_fitting_user(self, _, role_cls):
        # important for initial migration
        call_command('migrate', 'cirs', '0006', stdout=self.out)
        self.assertEqual(role_cls.objects.count(), 0)
     
    @parameterized.expand([
        ('reporter', 'add_criticalincident', Reporter),
        ('reviewer', 'change_criticalincident', Reviewer)
    ])        
    def test_migration_creates_role_based_on_user_perms(self, name, codename, role_cls):
        user = create_user_with_perm(name, codename)
        permission = Permission.objects.get(codename=codename)
        call_command('migrate', 'cirs', '0006', stdout=self.out)
        self.assertEqual(role_cls.objects.first().user, user)        
        self.assertIn(permission, role_cls.objects.first().user.user_permissions.all())
        
    def test_migration_stops_if_there_is_more_than_one_user_with_reporter_rights(self):
        reporter = create_user_with_perm('reporter', 'add_criticalincident')
        reporter2 = create_user_with_perm('reporter2', 'add_criticalincident')
        with self.assertRaises(MultipleObjectsReturned):
            call_command('migrate', 'cirs', '0006', stdout=self.out)

    
    def test_all_users_with_reviewer_permissions_are_assigned_to_reviewer_role(self):
        reviewer = create_user_with_perm('reviewer', 'change_criticalincident')
        reviewer2 = create_user_with_perm('reviewer2', 'change_criticalincident')

        call_command('migrate', 'cirs', '0006', stdout=self.out)
        self.assertEqual(Reviewer.objects.count(), 2)

    def test_no_omnipotent_users(self):
        # generates exception if any user has add and change permissions 
        # afterwards no reperter and no reviewer should be present
        user = create_user_with_perm('user', 'add_criticalincident')
        permission = Permission.objects.get(codename='change_criticalincident')
        user.user_permissions.add(permission)

        with self.assertRaises(ValidationError):
            call_command('migrate', 'cirs', '0006', stdout=self.out)

    
    @parameterized.expand([
        ('none', ''),
        ('reporter', 'add_criticalincident'),
        ('reviewer', 'change_criticalincident')
    ])
    # TODO: Use historical model? Or remove?
    @skip('worked for migration testeing before organization for ci was introduced')  
    def test_users_with_role_permission_has_to_exist_if_there_are_incidents(self, name, codename):
        # tests if there are users for all roles
        ci = mommy.prepare(CriticalIncident, public=True)
        if name != 'none':
            create_user_with_perm(name, codename)

        with self.assertRaises(ValidationError):
            call_command('migrate', 'cirs', '0006', stdout=self.out)

                

    
    def test_dont_create_organization_without_valid_configuration(self):
        # Organization should be created only if there is valid configuration.
        # As anyway only the first one was used, there is no need for a check of
        # multiple configurations.
        # Actually there should be no running installation without
        reporter = create_user_with_perm('rep', 'add_criticalincident')
        reviewer = create_user_with_perm('rev', 'change_criticalincident')
        
        call_command('migrate', 'cirs', '0006', stdout=self.out)

        self.assertEqual(Organization.objects.count(), 0)
    
    @parameterized.expand([
        ('none', ''),
        ('reporter', 'add_criticalincident'),
        ('reviewer', 'change_criticalincident')
    ]) 
    def test_dont_create_organization_without_valid_roles(self, name, codename):
        if name != 'none':
            create_user_with_perm(name, codename)

        call_command('migrate', 'cirs', '0006', stdout=self.out)

        self.assertEqual(Organization.objects.count(), 0)

    def test_create_organization(self):
        reporter = create_user_with_perm('rep', 'add_criticalincident')
        reviewer = create_user_with_perm('rev', 'change_criticalincident')
        config = mommy.make(LabCIRSConfig, send_notification=False)

        call_command('migrate', 'cirs', '0006', stdout=self.out)
        # there should be Organization with label equal to organization in settings
        org = Organization.objects.get(label=settings.ORGANIZATION)

        self.assertEqual(reporter, org.reporter.user)
        self.assertIn(reviewer.reviewer, org.reviewers.all())

class SecurityTest(TestCase):
    
    def gen_test_role_classes():
        return [
        ('reporter', Reporter),
        ('reviewer', Reviewer)
    ]
    
    def test_user_without_role_is_redirected_to_login_page(self):
        user = create_user('cirs_user')
        response = self.client.post(
            reverse('login'), {'username': user.username, 'password': user.username},
            follow=True)
        self.assertTemplateUsed(response, 'cirs/login.html')
        self.assertTemplateNotUsed(response, 'cirs/publishableincident_list.html')
        
    def test_user_without_role_sees_error_message(self):
        from cirs.views import MISSING_ROLE_MSG  # necessary only here so far
        user = create_user('cirs_user')
        response = self.client.post(
            reverse('login'), {'username': user.username, 'password': user.username},
            follow=True)
    
        self.assertEqual(response.context['message'], MISSING_ROLE_MSG)
        self.assertEqual(response.context['message_class'], 'danger')
        
    def test_user_without_role_is_logged_out(self):
        user = create_user('cirs_user')
        response = self.client.post(
            reverse('login'), {'username': user.username, 'password': user.username},
            follow=True)
        #from django.contrib import auth
        session_user = auth.get_user(self.client)

        self.assertNotEqual(session_user, user)
    
    @parameterized.expand(gen_test_role_classes)    
    def test_role_without_organization_is_redirected_to_login_page(self, name, role_cls):
        role = create_role(role_cls, name)
        response = self.client.post(
            reverse('login'), 
            {'username': role.user.username, 'password': role.user.username},
            follow=True)
        self.assertTemplateUsed(response, 'cirs/login.html')
        self.assertTemplateNotUsed(response, 'cirs/publishableincident_list.html')
    
    @parameterized.expand(gen_test_role_classes)     
    def test_role_without_organization_sees_error_message(self, name, role_cls):
        from cirs.views import MISSING_ORGANIZATION_MSG  # necessary only here so far
        role = create_role(role_cls, name)
        response = self.client.post(
            reverse('login'), 
            {'username': role.user.username, 'password': role.user.username},
            follow=True)
        self.assertEqual(response.context['message'], MISSING_ORGANIZATION_MSG)
        self.assertEqual(response.context['message_class'], 'danger')

    @parameterized.expand(gen_test_role_classes)
    def test_role_without_organization_is_logged_out(self, name, role_cls):
        role = create_role(role_cls, name)
        response = self.client.post(
            reverse('login'), 
            {'username': role.user.username, 'password': role.user.username},
            follow=True)
        
        session_user = auth.get_user(self.client)

        self.assertNotEqual(session_user, role.user)
        
    @parameterized.expand(gen_test_role_classes)
    def test_role_with_organization_is_logged_in(self, name, role_cls):
        role = create_role(role_cls, name)
        if name == 'reporter':
            org = mommy.make(Organization, reporter=role)
        elif name == 'reviewer':
            org = mommy.make(Organization)
            org.reviewers.add(role)
        
        response = self.client.post(
            reverse('login'), 
            {'username': role.user.username, 'password': role.user.username},
            follow=True)
        
        session_user = auth.get_user(self.client)

        self.assertEqual(session_user, role.user)
        
# next schema migration has to check if there are cis or organizations
# if there are cis and no org, raise
# if there are cis and multiple orgs raise 


class IncidentCreationViewSecurityTest(TestCase):
    # Role based access!
    def setUp(self):
        factory = RequestFactory()
        self.request = factory.get(reverse('create_incident'))
    
    def test_reporter_can_access_create_view(self):
        self.request.user = create_role(Reporter, 'reporter').user
        response =IncidentCreate.as_view()(self.request)
        self.assertIn('cirs/criticalincident_form.html', response.template_name)
        
    def test_reviewer_cannot_access_create_view(self):
        user = create_role(Reviewer, 'reviewer').user
        self.client.force_login(user)
        response = self.client.get(reverse('create_incident'), follow=True)
        self.assertTemplateNotUsed(response, 'cirs/criticalincident_form.html')
        self.assertTemplateUsed(response, 'cirs/publishableincident_list.html')
        
    def test_admin_cannot_access_create_view(self):
        user = create_user('admin', superuser=True)
        self.client.force_login(user)
        response = self.client.get(reverse('create_incident'), follow=True)
        self.assertTemplateNotUsed(response, 'cirs/criticalincident_form.html')
        self.assertTemplateUsed(response, 'admin/index.html')
    
    # Actually probably not necessary as user are checked at login?     
    def test_user_cannot_access_create_view(self):
        user = create_user('cirs_user')
        self.client.force_login(user)
        response = self.client.get(reverse('create_incident'), follow=True)
        self.assertTemplateNotUsed(response, 'cirs/criticalincident_form.html')
        self.assertTemplateUsed(response, 'cirs/login.html')
        session_user = auth.get_user(self.client)
        self.assertNotEqual(session_user, user)
        
    def test_anonymous_cannot_access_create_view(self):
        response = self.client.get(reverse('create_incident'), follow=True)
        self.assertTemplateNotUsed(response, 'cirs/criticalincident_form.html')
        self.assertTemplateUsed(response, 'cirs/login.html')

class CriticalIncidentWithOrganization(TestCase):
    
    def test_critical_incident_inherits_organization_from_creating_reporter(self):
        reporter = create_role(Reporter, 'reporter')
        # TODO: check if permission is still necessary or if reporter role is enough
        permission = Permission.objects.get(codename='add_criticalincident')
        reporter.user.user_permissions.add(permission)
        org = mommy.make(Organization, reporter=reporter)
        LabCIRSConfig.objects.create(send_notification=False)
        ci = mommy.prepare(CriticalIncident, public=True)
        self.client.login(username=reporter.user.username, password=reporter.user.username)

        response = self.client.post(reverse('create_incident'), data=ci.__dict__,
                                    follow=True)

        self.assertEqual(CriticalIncident.objects.first().organization, 
                         reporter.organization)
    
    @parameterized.expand([
        ('reporter',),
        ('reviewer',),
        ])
    def test_publishable_incident_list_view_returns_only_incidents_with_reporters_organization(self, role):
        self.reporter = create_role(Reporter, 'reporter')
        self.reviewer = create_role(Reviewer, 'reviewer')
        pi = mommy.make(PublishableIncident, publish=True,
                        critical_incident__public=True, 
                        critical_incident__organization__reporter=self.reporter)
        pi.critical_incident.organization.reviewers.add(self.reviewer)
        pi2 = mommy.make(PublishableIncident, critical_incident__public=True, publish=True)
        
        factory = RequestFactory()

        request = factory.get(reverse('incidents_list'))
        request.user = getattr(self, role).user
        response = PublishableIncidentList.as_view()(request)
        
        qs = response.context_data['object_list']
        self.assertIn(pi, qs)
        self.assertNotIn(pi2, qs)

