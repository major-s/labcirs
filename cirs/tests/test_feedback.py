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

import datetime as dt
import random
import string

from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from model_mommy import mommy

from cirs.forms import CommentForm
from cirs.models import CriticalIncident, Comment

from .helpers import create_user


class BaseFeedbackTest(TestCase):
    def setUp(self):
        self.reporter = create_user('reporter')
        self.ci = mommy.make(CriticalIncident, public=True)


class SecurityTest(BaseFeedbackTest):
    
    def setUp(self):
        super(SecurityTest,self).setUp()
        self.client.login(username=self.reporter.username, 
                          password=self.reporter.username)

    def test_reporter_cannot_acces_incident_directly(self):
        """Tests if reporter gets redirected to the search page
        if he tries to access the detail view of an incident."""

        response = self.client.get(self.ci.get_absolute_url(), follow=True)
        self.assertRedirects(response, reverse('incident_search'))
            
    def test_incident_search_sets_session_var_on_success(self):
        self.client.post(reverse('incident_search'), {'incident_code':self.ci.comment_code}, follow=True)
        self.assertEqual(self.client.session['accessible_incident'], self.ci.id)
        
    def test_reporter_can_acces_incident_if_session_var_is_set(self):
        """Tests if reporter gets redirected to the detail view of incident
        if 'accessible_incident' is set to the id of the incident.id."""
        session = self.client.session
        session['accessible_incident'] = self.ci.id
        session.save()
        response = self.client.get(self.ci.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_reporter_cannot_acces_incident_if_another_pk_is_set(self):
        """Tests if reporter gets redirected to the search view of incident
        if 'accessible_incident' is set to wrong id."""
        session = self.client.session
        session['accessible_incident'] = self.ci.id + 1
        session.save()
        response = self.client.get(self.ci.get_absolute_url(), follow=True)
        self.assertRedirects(response, reverse('incident_search'))

    def test_wrong_code_causes_form_error(self):
        response = self.client.post(reverse('incident_search'), {'incident_code':'ab'}, follow=True)
        self.assertFormError(response, 'form', 'incident_code', 'No matching critical incident found!')

class CommentModelTest(BaseFeedbackTest):
    def setUp(self):
        super(CommentModelTest,self).setUp()
        self.test_comment = {'critical_incident': self.ci,
                             'text': 'I have a comment on it',
                             'author': self.reporter,
                             'status': 'open'} 
    
    def test_comment_save_and_retrieve(self):
        Comment.objects.create(**self.test_comment)
        self.assertEqual(Comment.objects.first().critical_incident, self.ci)

    def test_comment_has_creation_date_of_today(self):
        Comment.objects.create(**self.test_comment)
        self.assertEqual(Comment.objects.first().created, dt.date.today())
        
    def test_comment_string_is_made_from_first_64_letters_of_text(self):
        comment_dict = self.test_comment.copy()
        comment_dict['text'] = ''.join(random.choice(string.printable) for _ in range(128))
        comment = Comment.objects.create(**comment_dict)
        self.assertEqual(str(comment), comment_dict['text'][:64])
        

class CommentViewTest(BaseFeedbackTest):
    def setUp(self):
        super(CommentViewTest,self).setUp()
        self.ci_url = reverse('incident_detail', kwargs={'pk': self.ci.pk})
        self.test_comment = {'critical_incident': self.ci,
                             'text': 'I have a comment on it',
                             'author': self.reporter,
                             'status': 'open'} 

        self.client.login(username=self.reporter.username, 
                          password=self.reporter.username)
        session = self.client.session
        session['accessible_incident'] = self.ci.id
        session.save()

    def test_comment_is_added_to_incident_after_post(self):
        Comment.objects.create(**self.test_comment)
        num_comments = Comment.objects.filter(critical_incident=self.ci).count()
        self.client.post(self.ci_url, data={'text': 'New comment!'}, follow=True)
        self.assertEqual(Comment.objects.filter(critical_incident=self.ci).count(),
                         num_comments + 1)

    def test_comment_text_in_comments_after_post(self):
        comment_text = 'I have another comment!'
        self.client.post(self.ci_url, data={'text': comment_text}, follow=True)
        self.assertEqual(Comment.objects.first().text, comment_text)
    
    def test_right_template_is_used(self):
        response = self.client.get(self.ci_url, follow=True)
        self.assertTemplateUsed(response, 'cirs/criticalincident_detail.html')
        
    def test_redirects_to_incident_view_after_post(self):
        response = self.client.post(self.ci_url, data={'text': 'New comment'},
                                    follow=True)
        self.assertRedirects(response, self.ci_url)

    def test_send_email_after_form_is_saved(self):
        reviewer = create_user('reviewer')
        config = self.ci.department.labcirsconfig
        config.send_notification=True
        config.notification_recipients.add(reviewer)
        config.save()
        
        form = CommentForm(self.test_comment)
        form.instance.author = self.reporter
        form.instance.critical_incident = self.ci
        form.save()

        self.assertEqual(len(mail.outbox), 1)  # @UndefinedVariable
        self.assertEqual(mail.outbox[0].subject, 'New LabCIRS comment')
