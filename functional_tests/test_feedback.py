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

import os
import time
from datetime import date

from django.conf import settings
from django.core import mail
from django.test import override_settings
from django.core.urlresolvers import reverse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC

from cirs.models import Comment, CriticalIncident, LabCIRSConfig
from .base import FunctionalTest

DEFAULT_WAIT = 5


incident_date = date(2015, 7, 24)
test_incident = {'date': incident_date,
                 'incident': 'A strang incident happened',
                 'reason': 'No one knows',
                 'immediate_action': 'No action possible',
                 'preventability': 'indistinct',
                 'public': True,
                 }


class CriticalIncidentFeedbackTest(FunctionalTest):

    @override_settings(DEBUG=True)
    def test_user_can_see_feedback_code(self):
        LabCIRSConfig.objects.create(send_notification=True)
        self.login_user()

        self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Add incident"))).click()

        # change to better test
        self.assertIn("incidents/create", self.browser.current_url)

        # the reporter enters incident data
        date_field = self.browser.find_element_by_id('id_date')
        # TODO: change to variable
        date_field.send_keys("07/24/2015")
        incident_field = self.browser.find_element_by_id('id_incident')
        incident_field.send_keys(test_incident['incident'])
        reason_field = self.browser.find_element_by_id('id_reason')
        reason_field.send_keys(test_incident['reason'])
        immediate_action_field = self.browser.find_element_by_id(
            'id_immediate_action')
        immediate_action_field.send_keys(test_incident['immediate_action'])
        preventability_select = Select(self.browser.find_element_by_id(
            'id_preventability'))
        preventability_select.select_by_value(test_incident['preventability'])
        self.browser.find_element_by_id('id_public_0').click()  # true


        for button in self.browser.find_elements_by_class_name("btn-danger"):
            if "Send" in button.text:
                button.click()
        # check for success
        time.sleep(2)
        # TODO: Add check for feedback message:
        # User sees the success page with code for feedback
        
        # feedback code seen by user is saved with the 
               
        code_info = self.browser.find_element_by_class_name("alert-info")
           
        #there should be only one object in the database
        ci = CriticalIncident.objects.first()
        comment_code = ci.comment_code
        
        self.assertIn(comment_code, code_info.text)


class CommentTest(FunctionalTest):

    def setUp(self):
        super(CommentTest, self).setUp()
        self.incident = CriticalIncident.objects.create(**test_incident)
        LabCIRSConfig.objects.create(send_notification=True)

    def view_incident_detail(self):
        '''Need this function because setting session from functional test
        did not work.'''
        incident = self.incident
        # TODO: let log in different users
        self.login_user()
        self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Comments"))).click()
        self.wait.until(
            EC.presence_of_element_located((By.ID, "id_incident_code"))
        ).send_keys(incident.comment_code)
        self.browser.find_element_by_class_name("btn-info").click()

    def create_comment(self, comment_text=None):
        # wait until text field present
        self.wait.until(
            EC.presence_of_element_located((By.ID, "id_text"))
            ).send_keys(comment_text)
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
        absolute_incident_url = self.live_server_url + self.incident.get_absolute_url()
        # reporter entered his comment already
        comment_text = "I have some remarks on this incident!"
        comment = Comment.objects.create(
            critical_incident=self.incident, author=self.reporter, text=comment_text)
        # reviewer logs in and goes to the incident page
        self.login_user(username=self.REVIEWER, password=self.REVIEWER_PASSWORD)
        time.sleep(1)
        self.browser.get(absolute_incident_url)

        # and sees the coment made by the reporter
        self.check_if_comment_in_the_last_row(comment_text)

        # now he can comment himself
        comment_text = "I still have some questions:"
        self.create_comment(comment_text)

        # check if the new comment is the last one
        self.check_if_comment_in_the_last_row(comment_text)
        
        # but now there is no email as reviewer made a comment himself
        self.assertEqual(len(mail.outbox), 0)
        
        # TODO: check what happens if therer are multiple recipients. It should send email then

    @override_settings(EMAIL_HOST='smtp.example.com')
    def test_send_email_after_reporter_creates_a_comment(self):
        config = LabCIRSConfig.objects.first()
        config.notification_recipients.add(self.reviewer)
        config.notification_sender_email = 'labcirs@labcirs.edu'
        config.save()
        self.view_incident_detail()
        comment_text = "I have some remarks on this incident!"
        self.create_comment(comment_text)
        # check if incident was sent by email
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'New LabCIRS comment')

class SecurityTest(FunctionalTest):

    def test_anon_user_cannot_access_incident(self):
        incident = CriticalIncident.objects.create(**test_incident)
        incident_url = incident.get_absolute_url()
        redirect_url = '%s%s?next=%s' % (self.live_server_url, reverse('login'),  incident_url)
        # should go to login page
        self.browser.get('%s%s' % (self.live_server_url, incident_url))

        self.assertEqual(self.browser.current_url, redirect_url)
    
    def test_reporter_cannot_access_incident_without_comment_code(self):
        # User logs in as reporter and tries to access directly detail view of an incident
        # this redirects him to the incident search page.
        incident = CriticalIncident.objects.create(**test_incident)
        incident_url = incident.get_absolute_url()
        self.login_user()
        time.sleep(2)
        redirect_url = '%s%s' % (self.live_server_url, reverse('incident_search'))
        self.browser.get('%s%s' % (self.live_server_url, incident_url))

        self.assertEqual(self.browser.current_url, redirect_url)
        
    @override_settings(DEBUG=True)
    def test_reporter_can_access_incident_with_correct_comment_code(self):
        incident = CriticalIncident.objects.create(**test_incident)
        self.login_user()
        self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Comments"))).click()
        self.wait.until(EC.presence_of_element_located((By.ID, "id_incident_code"))).send_keys(incident.comment_code)
        self.browser.find_element_by_class_name("btn-info").click()
        self.assertEqual(self.browser.current_url, self.live_server_url+incident.get_absolute_url())

    def test_reviewer_can_access_incident_without_code(self):
        incident = CriticalIncident.objects.create(**test_incident)
        absolute_incident_url = self.live_server_url + incident.get_absolute_url()
        self.login_user(username=self.REVIEWER, password=self.REVIEWER_PASSWORD)
        time.sleep(3)
        self.browser.get(absolute_incident_url)
        self.assertEqual(self.browser.current_url, absolute_incident_url)

    def test_wrong_code_redirects_to_search_page(self):
        # Reporter logs in and enters a code which does not exist
        self.login_user()
        self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Comments"))).click()
        self.wait.until(EC.presence_of_element_located((By.ID, "id_incident_code"))).send_keys('abc')
        self.browser.find_element_by_class_name("btn-info").click()

        # After submitting he lands again on the search page
        self.wait.until(EC.presence_of_element_located((By.ID, "id_incident_code")))

        # and sees informatinon that no incident was found
        self.assertIn("No matching critical incident found!", self.browser.page_source)

