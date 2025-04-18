# Copyright (C) 2018-2025 Sebastian Major
#
# This file is part of LabCIRS.
#
# LabCIRS is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# LabCIRS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with LabCIRS.
# If not, see <https://www.gnu.org/licenses/>.

import itertools

from django.contrib import admin, auth
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import RequestFactory, TestCase
from django.urls import reverse
from model_mommy import mommy
from parameterized import parameterized

from cirs.admin import (ConfigurationAdmin, CriticalIncidentAdmin,
                        DepartmentAdmin, LabCIRSUserAdmin,
                        PublishableIncidentAdmin, RoleAdmin, admin_site)
from cirs.models import (CriticalIncident, Department, LabCIRSConfig,
                         PublishableIncident, Reporter, Reviewer)
from cirs.views import IncidentCreate, PublishableIncidentList

from .helpers import create_role, create_user


class AdminRegistration(TestCase):
    
    @parameterized.expand([(Department,), (Reporter,), (Reviewer,)])
    def test_registration(self, model):
        self.assertTrue(admin_site.is_registered(model), "{} not registered".format(model))


class DepartmentBase(TestCase):
    
    def setUp(self):

        self.user = create_user('cirs_user')
        self.reporter = create_role(Reporter, 'reporter')
        self.reviewer = create_role(Reviewer, 'reviewer')
        self.admin = create_user('admin', superuser=True)
    
        self.en_dict = {
            'label': 'EN',
            'name': 'Experimenting Nerds',
            'reporter': self.reporter,
            'active': True,
        }
        

class DepartmentTest(DepartmentBase):

    def test_department_admin_name_is_label(self):
        dept = Department.objects.create(**self.en_dict)
        self.assertEqual(str(dept), dept.label)


    @parameterized.expand([('label',), ('name',), ('reporter')])
    def test_unique_departmentt_field(self, field):
        fe_dict = {
            'label': 'FE',
            'name': 'Experimenting Noobs',
            'reporter': create_role(Reporter, 'reporter_fe'),
            'active': True,
        }
        # create first department
        Department.objects.create(**self.en_dict)
        # create second department object
        dept = Department(**fe_dict)
        # and set fields equal to first department
        setattr(dept, field, self.en_dict[field])
        with self.assertRaises(IntegrityError):
            dept.save()


    def test_assigned_reporter_does_not_appear_in_admin_form_for_new_dept(self):
        Department.objects.create(**self.en_dict)
        form = DepartmentAdmin(Department, admin.AdminSite()).get_form(None)
        self.assertNotIn(
            self.reporter, form().fields['reporter'].choices.queryset,
            '''Found {} in select for new department although he already is 
            the reporter for {}'''.format(
                str(self.reporter), self.reporter.department
            )
        )

    def test_assigned_reporter_appears_in_admin_form_for_his_dept(self):
        dept = Department.objects.create(**self.en_dict)
        form = DepartmentAdmin(Department, admin.AdminSite()).get_form(None, obj=dept)
        self.assertIn(
            dept.reporter, form().fields['reporter'].choices.queryset,
            'Did not found {} in select for {} although he is assigned'.format(
                str(dept.reporter), dept
            )
        )

    def test_reviewers_use_filter_horizontal(self):
        self.assertIn('reviewers', DepartmentAdmin.filter_horizontal)
        
    def test_department_label_cannot_contain_spaces(self):
        dept = Department({'label': 'x y', 'name': 'Name', 
                           'reporter': mommy.make_recipe('cirs.reporter')})
        with self.assertRaises(ValidationError):
            dept.full_clean()
            
    def test_department_has_get_abs_url(self):
        dept = mommy.make(Department)
        self.assertEqual(dept.get_absolute_url(), '/incidents/{}/'.format(dept.label))


class ReviewerReporterModel(DepartmentBase):
    """
    User can be assigned only to one role. Superuser cannot be assigned to any role.
    """

    def gen_test_cases():  # @NoSelf
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
        role_cls.objects.create(user=self.user)
        with self.assertRaises(IntegrityError):
            role_cls.objects.create(user=self.user)

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
        class1.objects.create(user=self.user)
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
    def test_assigned_user_does_not_apears_in_admin_in_new_role(self, _, role_cls):
        role = role_cls.objects.create(user=self.user)
        form = RoleAdmin(role_cls, admin.AdminSite()).get_form(None)
        self.assertNotIn(
            role.user, form().fields['user'].choices.queryset,
            'Found {} in select for {} although he is assigned as {}'.format(
                role.user, role_cls.__name__, role
            )
        )


class ReporterUserChangeRights(DepartmentBase):
    
    def setUp(self):
        super(ReporterUserChangeRights, self).setUp()
        factory = RequestFactory()
        self.request = factory.get(
            reverse('admin:auth_user_change', args=(self.reporter.user.pk,)))
        
    WANTED_FIELDS = ['username', 'password', 'first_name', 'last_name']
    PROHIBITED_FIELDS = ['email', 'is_active', 'is_staff', 'is_superuser', 'groups',
                         'user_permissions', 'last_login', 'date_joined']
    
    @parameterized.expand(WANTED_FIELDS)
    def test_reviewer_can_change_only_some_reporter_user_fields(self, field):
        self.request.user = self.reviewer.user
        user_admin = LabCIRSUserAdmin(User, admin.AdminSite()).get_form(
            self.request, obj=self.reporter.user)
        self.assertIn(field, user_admin._meta.fields)
        
    @parameterized.expand(PROHIBITED_FIELDS)
    def test_reviewer_cannot_see_prohibited_reporter_user_fields(self, field):
        self.request.user = self.reviewer.user
        user_admin = LabCIRSUserAdmin(User, admin.AdminSite()).get_form(
            self.request, obj=self.reporter.user)
        self.assertNotIn(field, user_admin._meta.fields)
        
    @parameterized.expand(WANTED_FIELDS+PROHIBITED_FIELDS)
    def test_admin_can_change_all_reporter_user_fields(self, field):
        '''Admin can access all fields of any user'''
        self.request.user = self.admin
        user_admin = LabCIRSUserAdmin(User, admin.AdminSite()).get_form(
            self.request, obj=self.reporter.user)
        self.assertIn(field, user_admin._meta.fields)


class SecurityTest(TestCase):
    
    def gen_test_role_classes():  # @NoSelf
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
        self.client.post(
            reverse('login'), {'username': user.username, 'password': user.username},
            follow=True)
        session_user = auth.get_user(self.client)

        self.assertNotEqual(session_user, user)
    
    @parameterized.expand(gen_test_role_classes)    
    def test_role_without_department_is_redirected_to_login_page(self, name, role_cls):
        role = create_role(role_cls, name)
        response = self.client.post(
            reverse('login'), 
            {'username': role.user.username, 'password': role.user.username},
            follow=True)
        self.assertTemplateUsed(response, 'cirs/login.html')
        self.assertTemplateNotUsed(response, 'cirs/publishableincident_list.html')
    
    @parameterized.expand(gen_test_role_classes)     
    def test_role_without_department_sees_error_message(self, name, role_cls):
        from cirs.views import \
            MISSING_DEPARTMENT_MSG  # necessary only here so far
        role = create_role(role_cls, name)
        response = self.client.post(
            reverse('login'), 
            {'username': role.user.username, 'password': role.user.username},
            follow=True)
        self.assertEqual(response.context['message'], MISSING_DEPARTMENT_MSG)
        self.assertEqual(response.context['message_class'], 'danger')

    @parameterized.expand(gen_test_role_classes)
    def test_role_without_department_is_logged_out(self, name, role_cls):
        role = create_role(role_cls, name)
        self.client.post(
            reverse('login'), 
            {'username': role.user.username, 'password': role.user.username},
            follow=True)
        
        session_user = auth.get_user(self.client)

        self.assertNotEqual(session_user, role.user)
        
    @parameterized.expand(gen_test_role_classes)
    def test_role_with_department_is_logged_in(self, name, role_cls):
        role = create_role(role_cls, name)
        if name == 'reporter':
            dept = mommy.make(Department, reporter=role)
        elif name == 'reviewer':
            dept = mommy.make(Department)
            dept.reviewers.add(role)
        
        self.client.post(
            reverse('login'), 
            {'username': role.user.username, 'password': role.user.username},
            follow=True)
        
        session_user = auth.get_user(self.client)

        self.assertEqual(session_user, role.user)

    # Reviewer needs rights to work in the admin backend, so they have to be granted
    # to the user upon assignig a role, but revoked upon removal
    
    @parameterized.expand([
        ('cirs.change_criticalincident',),
        ('cirs.add_publishableincident',),
        ('cirs.change_publishableincident',),
        ('cirs.change_labcirsconfig', ),
        ('auth.change_user', ),
    ])
    def test_users_has_permission_after_assignement_of_reviewer_role(self, perm_code):
        user = create_user('cirs_user')
        Reviewer.objects.create(user=user)
        self.assertTrue(user.has_perm(perm_code))

    def test_users_is_staff_after_assignement_of_reviewer_role(self):
        user = create_user('cirs_user')
        Reviewer.objects.create(user=user)
        self.assertTrue(user.is_staff)


class BackendViewAccess(TestCase):

    @parameterized.expand([
        (CriticalIncident, CriticalIncidentAdmin, 'public_ci'),
        (PublishableIncident, PublishableIncidentAdmin, 'published_incident'),
    ])
    def test_admin_list_view(self, cls_name, admin_cls, recipe):
        incidents = mommy.make_recipe('cirs.'+recipe,  _quantity=2)
        reviewers = mommy.make_recipe('cirs.reviewer',  _quantity=2)
        for incident, reviewer in zip(incidents, reviewers):
            if cls_name == CriticalIncident:
                incident.department.reviewers.add(reviewer)
            elif cls_name == PublishableIncident:
                incident.critical_incident.department.reviewers.add(reviewer)
        
        model_admin = admin_cls(cls_name, admin.AdminSite())
        
        factory = RequestFactory()
        request = factory.get(
            reverse('admin:cirs_{}_changelist'.format(cls_name._meta.model_name)))
        request.user = reviewers[0].user

        qs = model_admin.get_queryset(request)

        self.assertIn(incidents[0], qs)
        self.assertNotIn(incidents[1], qs)
        
        # now with another reviewer
        request.user = reviewers[1].user

        qs = model_admin.get_queryset(request)

        self.assertIn(incidents[1], qs)
        self.assertNotIn(incidents[0], qs)

    @parameterized.expand([
        (CriticalIncident, CriticalIncidentAdmin, 'public_ci'),
        (PublishableIncident, PublishableIncidentAdmin, 'published_incident'),
    ])
    def test_list_view_returns_empty_qs_for_superuser(self, cls_name, admin_cls, recipe):
        mommy.make_recipe('cirs.'+recipe,  _quantity=2)
        model_admin = admin_cls(cls_name, admin.AdminSite())
        
        factory = RequestFactory()
        request = factory.get(
            reverse('admin:cirs_{}_changelist'.format(cls_name._meta.model_name)))
        request.user = create_user('superman', superuser=True)
        qs = model_admin.get_queryset(request)
        self.assertEqual(qs.count(), 0)
        
    def test_only_own_reporters_in_qs_for_reviewer(self):
        rev, rev2 = mommy.make_recipe('cirs.reviewer', _quantity=2)
        depts = mommy.make_recipe('cirs.department', _quantity=3)
        depts[0].reviewers.add(rev)
        depts[1].reviewers.add(rev)
        
        factory = RequestFactory()
        request = factory.get(reverse('admin:auth_user_changelist'))
        request.user = rev.user
        model_admin = LabCIRSUserAdmin(User, admin.AdminSite())
        qs = model_admin.get_queryset(request)
        self.assertIn(depts[0].reporter.user, qs)
        self.assertIn(depts[1].reporter.user, qs)
        self.assertNotIn(depts[2].reporter.user, qs)
        self.assertNotIn(rev.user, qs)
        self.assertNotIn(rev2.user, qs)
        
        
# next schema migration has to check if there are cis or departments
# if there are cis and no dept, raise
# if there are cis and multiple depts raise 


class IncidentCreationViewSecurityTest(TestCase):
    # Role based access!
    def setUp(self):
        factory = RequestFactory()
        self.dept = mommy.make_recipe('cirs.department')
        self.create_url = reverse('create_incident', kwargs={'dept': self.dept.label})
        self.request = factory.get(self.create_url)
    
    def test_reporter_can_access_create_view(self):
        # TODO: check also for rep with other department? 
        # Not necessary. Report always uses department form reporter
        # TODO: Change to normal client to remove RequestFactory
        self.request.user = self.dept.reporter.user
        response =IncidentCreate.as_view()(self.request)
        self.assertIn('cirs/criticalincident_form.html', response.template_name)
        
    def test_reviewer_cannot_access_create_view(self):
        user = create_role(Reviewer, 'reviewer').user
        self.client.force_login(user)
        response = self.client.get(self.create_url, follow=True)
        self.assertTemplateNotUsed(response, 'cirs/criticalincident_form.html')
        self.assertTemplateUsed(response, 'cirs/department_list.html')
        
    def test_admin_cannot_access_create_view(self):
        user = create_user('admin', superuser=True)
        self.client.force_login(user)
        response = self.client.get(self.create_url, follow=True)
        self.assertTemplateNotUsed(response, 'cirs/criticalincident_form.html')
        self.assertTemplateUsed(response, 'admin/index.html')
    
    # Actually probably not necessary as user are checked at login?     
    def test_user_cannot_access_create_view(self):
        user = create_user('cirs_user')
        self.client.force_login(user)
        response = self.client.get(self.create_url, follow=True)
        self.assertTemplateNotUsed(response, 'cirs/criticalincident_form.html')
        self.assertTemplateUsed(response, 'cirs/login.html')
        session_user = auth.get_user(self.client)
        self.assertNotEqual(session_user, user)
        
    def test_anonymous_cannot_access_create_view(self):
        response = self.client.get(self.create_url, follow=True)
        self.assertTemplateNotUsed(response, 'cirs/criticalincident_form.html')
        self.assertTemplateUsed(response, 'cirs/login.html')


class CriticalIncidentWithDepartment(TestCase):
    
    def test_critical_incident_inherits_department_from_creating_reporter(self):
        reporter = create_role(Reporter, 'reporter')
        dept = mommy.make(Department, reporter=reporter)
        ci = mommy.prepare(CriticalIncident, public=True, id=1, photo='', department=dept, _fill_optional=True)
        self.client.login(username=reporter.user.username, password=reporter.user.username)
        self.client.post(reverse('create_incident', kwargs={'dept': dept.label}), data=ci.__dict__)

        self.assertEqual(CriticalIncident.objects.first().department, 
                         reporter.department)
    
    @parameterized.expand([
        ('rep1',),
        ('reviewer',),
        ])
    def test_publishable_incident_list_view_returns_only_incidents_with_ci_department(self, role):
        reviewer = create_role(Reviewer, 'reviewer')
        pi, pi2 = mommy.make_recipe('cirs.published_incident', _quantity=2)
        pi.critical_incident.department.reviewers.add(reviewer)
       
        factory = RequestFactory()
        kwargs={'dept': pi.critical_incident.department.label}
        request = factory.get(reverse('incidents_for_department', kwargs=kwargs))
        request.user = User.objects.get(username=role)

        response = PublishableIncidentList.as_view()(request, **kwargs)
        
        qs = response.context_data['object_list']
        self.assertIn(pi, qs)
        self.assertNotIn(pi2, qs)


class ConfigurationForDepartment(TestCase):
    
    def test_department_gets_config_upon_creation(self):
        dept = mommy.make_recipe('cirs.department')
        self.assertEqual(type(dept.labcirsconfig), LabCIRSConfig,
                         '{} misses configuration'.format(dept))

    def test_department_can_have_only_one_config(self):
        dept = mommy.make_recipe('cirs.department')
        with self.assertRaises(IntegrityError):
            mommy.make(LabCIRSConfig, department=dept)
            
    def test_notification_is_set_to_false_upon_config_creation(self):
        # Decided to set notification sendin to false by default
        config = LabCIRSConfig()
        self.assertFalse(config.send_notification)
        self.assertNotEqual(config.send_notification, None)
        
    def test_configurations_name_contains_dept_label(self):
        dept = mommy.make_recipe('cirs.department')
        self.assertEqual(str(dept.labcirsconfig),
                         'LabCIRS configuration for {}'.format(dept.label))
        
    def test_reviewer_sees_only_config_of_his_organization(self):
        dept1, dept2 = mommy.make_recipe('cirs.department', _quantity=2)
        reviewer = mommy.make_recipe('cirs.reviewer')
        dept1.reviewers.add(reviewer)
                
        model_admin = ConfigurationAdmin(LabCIRSConfig, admin.AdminSite())
        
        factory = RequestFactory()
        request = factory.get(reverse('admin:cirs_labcirsconfig_changelist'))
        request.user = reviewer.user

        qs = model_admin.get_queryset(request)

        self.assertIn(dept1.labcirsconfig, qs)
        self.assertNotIn(dept2.labcirsconfig, qs)
    
    def test_admin_sees_all_configurations(self):
        mommy.make_recipe('cirs.department', _quantity=5)
        model_admin = ConfigurationAdmin(LabCIRSConfig, admin.AdminSite())
        
        factory = RequestFactory()
        request = factory.get(reverse('admin:cirs_labcirsconfig_changelist'))
        request.user = create_user('admin', superuser=True)

        qs = model_admin.get_queryset(request)

        self.assertEqual(LabCIRSConfig.objects.count(), qs.count())

    def test_only_reviewer_for_dept_appears_in_the_recipient_list(self):
        dept = mommy.make_recipe('cirs.department')
        dept.labcirsconfig.login_info_de = 'Hallo!!!'
        dept.labcirsconfig.save()
        rev1, rev2 = mommy.make_recipe('cirs.reviewer', _quantity=2)
        dept.reviewers.add(rev1)
        form = ConfigurationAdmin(LabCIRSConfig, admin.AdminSite()).get_form(
            None, obj=dept.labcirsconfig)
        
        self.assertIn(
            rev1.user, form().fields['notification_recipients'].choices.queryset,
            'Did not found {} in select for recipients although he is assigned'.format(rev1.user)
        )
        self.assertNotIn(
            rev2.user, form().fields['notification_recipients'].choices.queryset,
            'Found {} in select for recipients although he is not assigned'.format(rev2.user)
        )
