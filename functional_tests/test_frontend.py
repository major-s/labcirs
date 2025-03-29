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

import time

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse
from django.test import override_settings
from model_mommy import mommy
from parameterized import parameterized
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from cirs.models import Department, Reporter, PublishableIncident, Reviewer, CriticalIncident
from cirs.tests.helpers import create_role

from .base import FunctionalTest



class FrontendBaseTest(FunctionalTest):
     
    def assertCurrentUrlIs(self, url):
        target_url = '{}{}'.format(self.live_server_url, url)
        self.assertEqual(self.browser.current_url, target_url)
        
    def assertBrandIs(self, label):
        brand = self.browser.find_element(By.CLASS_NAME, 'navbar-brand')
        self.assertEqual(brand.text, '{} / {}'.format(settings.ORGANIZATION, label))


class FrontendWithDepartments(FrontendBaseTest):
    """Test frontend after departments were aded to the models."""
    
   
    #@override_settings(DEBUG=True)
    def test_anon_user_sees_list_of_departments_on_home_page(self):
        
        mommy.make_recipe('cirs.department', _quantity=5)
        
        # Anonymous user visits the home page of LabCIRS server
        self.browser.get(self.live_server_url)
        
        # and sees a list of all departments
        labels = self.get_column_from_table_as_list('table_departments')
        for dept in Department.objects.all():
            self.assertIn(dept.label, labels)
            
        # At the top of the page he sees the name of the organization
        brand = self.browser.find_element(By.CLASS_NAME, 'navbar-brand')
        self.assertEqual(brand.text, settings.ORGANIZATION)
        
        # he clicks on one of the links and is redirected to the login page
        # for the department
        dept = Department.objects.last()
        self.click_link_with_text(dept.label)
        self.assertIn(reverse('login'), self.browser.current_url)
        
        # At the top of the page he sees the name of the organization and the department
        self.assertBrandIs(dept.label)
        
        
    def test_reporter_logs_in_after_he_clicked_on_his_department(self):
        rep1 = create_role(Reporter, 'rep1')
        rep2 = create_role(Reporter, 'rep2')
        # there are two departments with several published incidents
        dept1 = mommy.make_recipe('cirs.department', reporter=rep1)
        dept2 = mommy.make_recipe('cirs.department', reporter=rep2)
        for dept in (dept1, dept2):
            pis = mommy.make_recipe('cirs.published_incident', critical_incident__department=dept,
                              _quantity=5)
            for pi in pis:
                mommy.make_recipe('cirs.translated_pi', master=pi)

        # user goes to the incidents list for his department
        self.browser.get(self.live_server_url + dept1.get_absolute_url())

        # he logs in
        self.find_input_and_enter_text('username', rep1.user.username, By.NAME)
        self.find_input_and_enter_text('password', rep1.user.username, By.NAME)
        self.find_input_and_enter_text('password', Keys.RETURN, By.NAME)
        
        self.wait.until(EC.url_to_be(self.live_server_url + dept1.get_absolute_url()))
        incidents = self.get_column_from_table_as_list('tableIncidents')
    
        # and sees table with published incident from his department, but not from another
        for pi in PublishableIncident.objects.filter(critical_incident__department=dept1):
            self.assertIn(pi.incident, incidents)
        for pi in PublishableIncident.objects.exclude(critical_incident__department=dept1):
            self.assertNotIn(pi.incident, incidents)
        
        
        # if there is only one department he is redirected to the login page
        
        
        
        # if non existing department is entered in the url, user is redirected to home page
        
        
        
        # if user clicks on one dept and logs in with credentials from another dept, he is redirected
        # to his own dept and message is shown
        
    def test_reviewer_sees_only_incidents_from_one_department_at_once(self):
        # There is reviewer for two departments
        rev = create_role(Reviewer, 'rev')
        dept1, dept2 = mommy.make_recipe('cirs.department', _quantity=2)
        for dept in (dept1, dept2):
            pis = mommy.make_recipe('cirs.published_incident', critical_incident__department=dept,
                              _quantity=5)
            for pi in pis:
                mommy.make_recipe('cirs.translated_pi', master=pi)
            dept.reviewers.add(rev)
        # he logins and goes to the home page:
        self.quick_login(rev.user, reverse('labcirs_home'))
        # he clicks on first department
        self.click_link_with_text(dept1.label)

        # and sees table with incidents for dept1        
        incidents = self.get_column_from_table_as_list('tableIncidents')
        
        for pi in PublishableIncident.objects.filter(critical_incident__department=dept1):
            self.assertIn(pi.incident, incidents)
        for pi in PublishableIncident.objects.exclude(critical_incident__department=dept1):
            self.assertNotIn(pi.incident, incidents)

    def test_reviewer_is_redirected_to_his_dept_from_detail_view_of_ci_from_another_dept(self):
        rev = create_role(Reviewer, 'rev')
        dept1, dept2 = mommy.make_recipe('cirs.department', _quantity=2)
        dept1.reviewers.add(rev)
        for dept in (dept1, dept2):
            mommy.make_recipe('cirs.published_incident', critical_incident__department=dept,
                              _quantity=5)
        # he tries to access_detail view of one incident from dept2
        incident = CriticalIncident.objects.filter(department=dept2).first()
        self.quick_login(rev.user, incident.get_absolute_url())
        # but is redirected to his department page
        
        self.assertCurrentUrlIs(dept1.get_absolute_url())

        
class FrontendWithDepartmentsConfig(FunctionalTest):
    
    #def setUp(self):
    #    super(FrontendWithDepartmentsConfig, self).setUp()
        
    
    def test_each_department_has_own_login_info(self):
        # anonymous call of dept leads to login with own login info
        dept1, dept2 = mommy.make_recipe('cirs.department', _quantity=2)
        dept1.labcirsconfig.login_info = 'Department 1'
        dept1.labcirsconfig.save()
        dept2.labcirsconfig.login_info = 'Department 2'
        dept2.labcirsconfig.save()
        self.browser.get(self.live_server_url + dept1.get_absolute_url())
        info = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'alert-success')))
        time.sleep(3)
        self.assertEqual(info.text, 'Department 1')
        
        # now go to second department and look for the same
        self.browser.get(self.live_server_url + dept2.get_absolute_url())
        info = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'alert-success')))
        time.sleep(3)
        self.assertEqual(info.text, 'Department 2')
    
    # TODO: This is not frontend test?
    @override_settings(EMAIL_HOST='smtp.example.com')
    def test_each_department_has_own_email_config(self):
        rev1, rev2 = mommy.make_recipe('cirs.reviewer', _quantity=2)
        dept1, dept2 = mommy.make_recipe('cirs.department', _quantity=2)
        dept1.labcirsconfig.notification_recipients.add(rev1.user)
        dept2.labcirsconfig.notification_recipients.add(rev2.user)
               
        for dept in (dept1, dept2):
            dept.labcirsconfig.send_notification = True
            dept.labcirsconfig.notification_sender_email = 'labcirs@labcirs.edu'
            dept.labcirsconfig.save()
            self.quick_login(dept.reporter.user, 
                             reverse('create_incident', kwargs={'dept':dept.label}))
            # reporter enters incident data
            self.enter_test_incident(wait_for_success=True)

            # check if incident was sent by email to correct reviewer

            self.assertEqual(mail.outbox[-1].to[0], 
                             dept.labcirsconfig.notification_recipients.first().email)

class RedirectKnownUsers(FrontendBaseTest):
    """
    If logged in user access pages directly they have to be sometimes redirected
    """
    def setUp(self):
        super(RedirectKnownUsers, self).setUp()
        self.dept = mommy.make_recipe('cirs.department')
        self.rev = mommy.make_recipe('cirs.reviewer')
        self.dept.reviewers.add(self.rev)

    # if reporter is already logged in he is redirected to his dept and message is shown
    @parameterized.expand([
        ('rep1',),
        ('rev1',), # has only one department
    ])        
    def test_redirect_after_home_access(self, name):
        ## Reporter and reviewer with only one department should be redirected
        ## to the list of department incidents
        user = User.objects.get(username=name)
        # user goes to home page
        self.quick_login(user)
        self.assertCurrentUrlIs(self.dept.get_absolute_url())

    def test_redirect_reviewer_with_multiple_departments_after_home_access(self):
        dept2, dept3 = mommy.make_recipe('cirs.department', _quantity=2)
        dept2.reviewers.add(self.rev)
        self.quick_login(self.rev.user)
        labels = self.get_column_from_table_as_list('table_departments')

        for dept in (self.dept, dept2):
            self.assertIn(dept.label, labels)
        self.assertNotIn(dept3.label, labels)
    
    def test_redirect_admin_from_detail_view(self):
        ci = mommy.make_recipe('cirs.public_ci')
        self.quick_login(self.admin, ci.get_absolute_url())
        self.assertCurrentUrlIs(reverse('admin:index'))
    # TODO:    
    def test_redirect_reporter_with_correct_code_but_wrong_dept_from_details_view(self):
        pass

    def test_redirect_superuser_from_department_list(self):
        self.quick_login(self.admin, reverse('departments_list'))
        self.assertCurrentUrlIs(reverse('admin:index'))

    @parameterized.expand([
        ('create_incident',),
        #('success',), # not necessary
        ('incident_search',),
        ('incidents_for_department',)
    ])
    def test_superuser_is_always_redirected(self, view):
        self.quick_login(self.admin, reverse(view, kwargs={'dept':self.dept.label}))
        self.assertCurrentUrlIs(reverse('admin:index'))

class CorrectDepartmentInURL(FrontendBaseTest):
    
    def test_rep1_logs_in_via_dept2_and_sees_his_dept_and_message(self):
        dept1, dept2 = mommy.make_recipe('cirs.department', _quantity=2)
        mommy.make_recipe('cirs.published_incident', _quantity=5, 
                          critical_incident__department=dept1)
        self.quick_login(dept1.reporter.user, dept2.get_absolute_url())
        #time.sleep(1)
        self.assertCurrentUrlIs(dept1.get_absolute_url())
        self.assertBrandIs(dept1.label)
        heading1 = self.browser.find_element(By.TAG_NAME, 'h2')
        self.assertIn(dept1.label, heading1.text)
        # check also for message
        #self.assertIn
        error_message = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, 'alert-warning'))
        ).text
        self.assertIn(dept1.label, error_message)
        
    def test_nav_link_leads_to_list_with_department(self):
        # BUGFIX: After adding the departments, the links points to nowhere as there is no dept
        dept = mommy.make_recipe('cirs.department')
        self.quick_login(dept.reporter.user)
        self.click_link_with_text("View incidents")
        self.assertCurrentUrlIs(dept.get_absolute_url())