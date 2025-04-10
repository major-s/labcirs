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
from django.test import TestCase
from django.urls import reverse
from model_mommy import mommy
from parameterized import parameterized

from cirs.models import PublishableIncident, Reviewer
from cirs.tests.helpers import create_user

from .helpers import create_role


class HomeViewWithDepartment(TestCase):
         
    def test_all_departments_in_context_data(self):
        depts = mommy.make_recipe('cirs.department', 3)
        
        response = self.client.get(reverse('labcirs_home'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cirs/department_list.html')
        qs = response.context['object_list']

        for dept in depts:
            self.assertIn(dept, qs)
            
    def test_incident_for_department_list(self):
        depts = mommy.make_recipe('cirs.department', 3)
        # has to login at least reporter of first dept
        self.client.force_login(depts[0].reporter.user)
        response = self.client.get(depts[0].get_absolute_url(), follow=True)
        self.assertTemplateUsed(response, 'cirs/publishableincident_list.html')
        
    def test_dept_label_in_context(self):
        dept = mommy.make_recipe('cirs.department')
        self.client.force_login(dept.reporter.user)
        response = self.client.get(dept.get_absolute_url(), follow=True)

        self.assertEqual(response.context['department'], dept.label)

    def test_dept_label_in_context_even_without_login(self):
        dept = mommy.make_recipe('cirs.department')

        response = self.client.get(dept.get_absolute_url(), follow=True)

        self.assertEqual(response.context['department'], dept.label)
        
    def test_queryset_for_reviewer_contains_only_pis_for_dept_in_kwargs(self):
        rev = create_role(Reviewer, 'rev')
        dept1, dept2 = mommy.make_recipe('cirs.department', _quantity=2)
        for dept in (dept1, dept2):
            mommy.make_recipe('cirs.published_incident', critical_incident__department=dept,
                              _quantity=5)
            dept.reviewers.add(rev)
        self.client.force_login(rev.user)
        response = self.client.get(dept1.get_absolute_url(), follow=True)
        
        qs = response.context['object_list']
        for pi in PublishableIncident.objects.filter(critical_incident__department=dept1):
            self.assertIn(pi, qs)
        for pi in PublishableIncident.objects.exclude(critical_incident__department=dept1):
            self.assertNotIn(pi, qs)
    
    def test_incident_detail_redirects_foreign_reviewer_to_his_dept(self):
        rev = create_role(Reviewer, 'rev')
        dept1, dept2 = mommy.make_recipe('cirs.department', _quantity=2)
        dept1.reviewers.add(rev)
        ci = mommy.make_recipe('cirs.public_ci', department=dept2)
        self.client.force_login(rev.user)
        response = self.client.get(ci.get_absolute_url(), follow=True)
        
        self.assertRedirects(response, rev.departments.get().get_absolute_url())

        # TODO: display message
        
class LoginView(TestCase):
    
    def test_correct_config_in_context(self):
        depts = mommy.make_recipe('cirs.department', _quantity=3)
        for dept in depts:
            response = self.client.get(dept.get_absolute_url(), follow=True)
            self.assertEqual(response.context['labcirs_config'], dept.labcirsconfig)
            
class ViewRedirect(TestCase):
    
    def setUp(self):
        self.dept = mommy.make_recipe('cirs.department')
        self.rev = mommy.make_recipe('cirs.reviewer')
        self.dept.reviewers.add(self.rev)
        self.superman =  create_user('admin', superuser=True)
    
    @parameterized.expand([
        ('rep1',),
        ('rev1',), # has only one department here
    ])  
    def test_home_view_redirects_logged_in_user_to_incident_list_for_dept(self, name):
        user = User.objects.get(username=name)
        self.client.force_login(user)
        response = self.client.get(reverse('labcirs_home'), follow=True)
        self.assertTemplateUsed(response, 'cirs/publishableincident_list.html')
        
    def test_home_view_redirects_reviewer_with_many_depts_to_home_page(self):
        dept2 = mommy.make_recipe('cirs.department')
        dept2.reviewers.add(self.rev)
        self.client.force_login(self.rev.user)
        response = self.client.get(reverse('labcirs_home'), follow=True)
        self.assertTemplateUsed(response, 'cirs/department_list.html')
        
    def test_home_view_query_set_contains_only_reviewers_depts(self):
        dept2, dept3 = mommy.make_recipe('cirs.department', _quantity=2)
        dept2.reviewers.add(self.rev)
        self.client.force_login(self.rev.user)
        response = self.client.get(reverse('labcirs_home'), follow=True)
        qs = response.context['object_list']
        self.assertIn(dept2, qs)
        self.assertNotIn(dept3, qs)
        
    def test_detail_view_redirects_superuser_to_admin(self):
        ci = mommy.make_recipe('cirs.public_ci')
        self.client.force_login(self.superman)
        response = self.client.get(ci.get_absolute_url(), follow=True)
        self.assertRedirects(response, reverse('admin:index'))

    def test_department_list_redirects_superuser(self):
        self.client.force_login(self.superman)
        response = self.client.get(reverse('departments_list'), follow=True)
        self.assertRedirects(response, reverse('admin:index'))

    @parameterized.expand([
        #('departments_list',),
        ('create_incident',),
        ('incident_search',),
        ('incidents_for_department',)
    ])
    def test_superuser_is_always_redirected(self, view):
        self.client.force_login(self.superman)
        response = self.client.get(reverse(view, kwargs={'dept':self.dept.label}), follow=True)
        self.assertRedirects(response, reverse('admin:index'))
    
    def test_login_redirects_reporter_to_his_department(self):
        # Reporte might click wrong departmetn and still login, 
        # so he should be redirected to his dept or to the home page
        # (which then redirects to dept anyway!)
        dept2 = mommy.make_recipe('cirs.department')
        self.client.force_login(self.dept.reporter.user)
        response = self.client.get(dept2.get_absolute_url(), follow=True)
        self.assertRedirects(response, self.dept.get_absolute_url())
        expected_message = 'You were redirected from {} to {}!'.format(dept2.label, self.dept.label)
        self.assertIn(expected_message, [message.message for message in response.context['messages']])
    
    # TODO: move to another class    
    def test_dept_label_in_heading_over_table(self):
        self.client.force_login(self.dept.reporter.user)
        response = self.client.get(self.dept.get_absolute_url(), follow=True)
        title = 'Critical incidents for {}'.format(self.dept.label)
        self.assertIn(title, response.rendered_content)
        
    def test_nav_link_to_list_has_department(self):
        self.client.force_login(self.dept.reporter.user)
        response = self.client.get(self.dept.get_absolute_url(), follow=True)
        self.assertContains(response, self.dept.get_absolute_url())
        
    def test_user_without_role_sees_error_message(self):
        from cirs.views import MISSING_ROLE_MSG  # necessary only here so far
        user = create_user('cirs_user')
        response = self.client.post(
            reverse('login'), {'username': user.username, 'password': user.username},
            follow=True)
    
        self.assertEqual(response.context['message'], MISSING_ROLE_MSG)
        self.assertEqual(response.context['message_class'], 'danger')