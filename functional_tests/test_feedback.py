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

from django.core import mail
from django.core.urlresolvers import reverse
from django.test import override_settings
from model_mommy import mommy
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from cirs.models import Comment, CriticalIncident, LabCIRSConfig, Department, Reporter
from cirs.tests.helpers import create_role

from .base import FunctionalTest


DEFAULT_WAIT = 5


class CriticalIncidentFeedbackTest(FunctionalTest):

    @override_settings(DEBUG=True)
    def test_user_can_see_feedback_code(self):
        LabCIRSConfig.objects.create(send_notification=True)
        reporter = create_role(Reporter, self.reporter)
        # create department. In theory I could test if reporter has 
        # an department in the view, but acutally users who are not superuser 
        # and don't have assoziated department cannot efectivly log in
        mommy.make(Department, reporter=reporter)
        self.quick_login_reporter(reverse('create_incident'))

        # the reporter enters incident data
        self.enter_test_incident()

        # User sees the success page with code for feedback        
        code_info = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, 'alert-info')))
           
        #there should be only one object in the database
        ci = CriticalIncident.objects.first()
        comment_code = ci.comment_code
        
        self.assertIn(comment_code, code_info.text)


class CommentTest(FunctionalTest):

    def setUp(self):
        super(CommentTest, self).setUp()
        self.incident = mommy.make(CriticalIncident, public=True,
            department__reporter=create_role(Reporter, self.reporter))
        self.config = LabCIRSConfig.objects.create(send_notification=True)

    def view_incident_detail(self):
        '''Need this function because setting session from functional test
        did not work.'''
        # TODO: let log in different users?
        self.quick_login_reporter()
        self.click_link_with_text('Comments')
        self.find_input_and_enter_text('id_incident_code', self.incident.comment_code)
        self.browser.find_element_by_class_name("btn-info").click()

    def create_comment(self, comment_text=None):
        # wait until text field present, enter text
        self.find_input_and_enter_text('id_text', comment_text)
        # and clicks the "Save" button.
        self.browser.find_element_by_class_name("btn-danger").click()

    def check_if_comment_in_the_last_row(self, comment_text=None):
        table = self.wait.until(
            EC.presence_of_element_located((By.ID, "id_comment_table")))
        rows = table.find_elements_by_tag_name('tr')
        self.assertIn(comment_text, rows[-1].text)

    @override_settings(DEBUG=True)        
    def test_reporter_can_add_comment(self):
        absolute_incident_url = self.live_server_url + self.incident.get_absolute_url()
        self.view_incident_detail()

        # reporter enters a comment into the comment text field
        comment_text = "I have some remarks on this incident!"
        self.create_comment(comment_text)
        
        # and lands afterwards on the same page
        self.assertEqual(self.browser.current_url, absolute_incident_url)
        # the new comment is below
        self.check_if_comment_in_the_last_row(comment_text)

    @override_settings(DEBUG=True) 
    def test_reviewer_can_comment_on_incident(self):
        # reporter entered his comment already
        comment_text = "I have some remarks on this incident!"
        Comment.objects.create(critical_incident=self.incident,
                               author=self.reporter, text=comment_text)
        # reviewer logs in and goes to the incident page
        self.quick_backend_login(self.reviewer, self.incident.get_absolute_url())

        # and sees the coment made by the reporter
        self.check_if_comment_in_the_last_row(comment_text)

        # now he can comment himself
        comment_text = "I still have some questions:"
        self.create_comment(comment_text)

        # check if the new comment is the last one
        self.check_if_comment_in_the_last_row(comment_text)
        
        # but now there is no email as reviewer made a comment himself
        self.assertEqual(len(mail.outbox), 0)  # @UndefinedVariable
        
        # TODO: check what happens if therer are multiple recipients. It should send email then

    @override_settings(EMAIL_HOST='smtp.example.com')
    def test_send_email_after_reporter_creates_a_comment(self):
        self.config.notification_recipients.add(self.reviewer)
        self.config.notification_sender_email = 'labcirs@labcirs.edu'
        self.config.save()
        self.view_incident_detail()
        comment_text = "I have some remarks on this incident!"
        self.create_comment(comment_text)
        # check if incident was sent by email
        self.assertEqual(len(mail.outbox), 1)  # @UndefinedVariable
        self.assertEqual(mail.outbox[0].subject, 'New LabCIRS comment')

class SecurityTest(FunctionalTest):
    
    def setUp(self):
        super(SecurityTest, self).setUp()
        self.incident = mommy.make(CriticalIncident, public=True)
        self.absolute_incident_url = self.live_server_url + self.incident.get_absolute_url()

    def test_anon_user_cannot_access_incident(self):
        incident_url = self.incident.get_absolute_url()
        redirect_url = '{}{}?next={}'.format(self.live_server_url,
                                             reverse('login'),  incident_url)
        # should go to login page
        self.browser.get(self.absolute_incident_url)#'%s%s' % (self.live_server_url, incident_url))
        self.assertEqual(self.browser.current_url, redirect_url)
    
    def test_reporter_cannot_access_incident_without_comment_code(self):
        # User logs in as reporter and tries to access directly detail view of an incident
        # this redirects him to the incident search page.
        self.quick_login_reporter()
        redirect_url = '{}{}'.format(self.live_server_url,
                                     reverse('incident_search'))
        self.browser.get(self.absolute_incident_url)
        self.assertEqual(self.browser.current_url, redirect_url)
        
    @override_settings(DEBUG=True)
    def test_reporter_can_access_incident_with_correct_comment_code(self):
        self.quick_login_reporter(reverse('incident_search'))
        self.find_input_and_enter_text('id_incident_code', self.incident.comment_code)
        self.browser.find_element_by_class_name("btn-info").click()
        self.assertEqual(self.browser.current_url, self.absolute_incident_url)

    def test_reviewer_can_access_incident_without_code(self):
        self.quick_backend_login(self.reviewer)
        self.browser.get(self.absolute_incident_url)
        self.assertEqual(self.browser.current_url, self.absolute_incident_url)

    def test_wrong_code_redirects_to_search_page(self):
        # Reporter logs in and enters a code which does not exist
        self.quick_login_reporter(reverse('incident_search'))
        self.find_input_and_enter_text('id_incident_code', 'abc')
        self.browser.find_element_by_class_name("btn-info").click()

        # After submitting he lands again on the search page
        self.wait.until(EC.presence_of_element_located((By.ID, "id_incident_code")))

        # and sees informatinon that no incident was found
        self.assertIn("No matching critical incident found!", self.browser.page_source)

