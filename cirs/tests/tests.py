# -*- coding: utf-8 -*-
#
# Copyright (C) 2016-2018 Sebastian Major
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

from collections import OrderedDict
from datetime import date, timedelta

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User, Permission
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core import mail
from django.core.urlresolvers import resolve, reverse
from django.test import TestCase, RequestFactory, override_settings

from model_mommy import mommy

from cirs.admin import CriticalIncidentAdmin
from cirs.models import CriticalIncident, PublishableIncident, LabCIRSConfig, Organization, Reporter
from cirs.views import IncidentCreateForm, PublishableIncidentList

from .helpers import create_role, create_user, create_user_with_perm


class CriticalIncidentModelTest(TestCase):
    
    def setUp(self):
        # create first incident
        self.first_incident = mommy.make(CriticalIncident, public=True, category = ['other'])
    
    def test_saving_and_retriving_incidents(self):
        self.first_incident.photo = File(open("cirs/tests/test.jpg"))
        self.first_incident.save()

        p = CriticalIncident.objects.get(id=1).photo.path

        # TODO: not really working. Compare files
        self.failUnless(open(p), 'file not found')
        # TODO: move category testing to another test
        my_incident = CriticalIncident.objects.first()
        self.assertIn('other', my_incident.category)

    def test_cannot_save_future_incidents(self):
        self.first_incident.date = date.today() + timedelta(days=10)
        self.first_incident.status = 'in process'
        self.first_incident.save()
        self.assertRaises(ValidationError, self.first_incident.clean)
    
    def test_comment_code_is_generated_on_creation(self):
        #retreive incident and check for existing comment_code
        my_incident = CriticalIncident.objects.first()
        self.assertNotEqual('', my_incident.comment_code, "Comment code should not be empty")
        
        # TODO: test for unique code
        
    def test_get_absolute_url_returns_valid_url(self):
        my_incident = CriticalIncident.objects.get(pk=1)
        self.assertEqual(my_incident.get_absolute_url(), '/incidents/1/')

class CriticalIncidentFormTest(TestCase):

    incident_form_fields = ['date', 'incident', 'reason', 'immediate_action',
                            'preventability', 'photo', 'public']

    def test_photo_field_in_form(self):
        form = IncidentCreateForm()
        self.assertIn('id_photo', form.as_p())

    # TODO: def test_all_necessary_fields_in


class CriticalIncidentCreateViewTest(TestCase):
  
    def test_create_view_returns_message(self):
        user = create_user_with_perm('reporter', 'add_criticalincident')
        create_role(Reporter, user)
        mommy.make(Organization, reporter=user.reporter)
          
        test_incident = {'date': '07/24/2015',
                         'incident': 'A strang incident happened',
                         'reason': 'No one knows',
                         'immediate_action': 'No action possible',
                         'preventability': 'indistinct',
                         'public': True,
                         }
          
        login = self.client.login(username=user.username, password=user.username)
        LabCIRSConfig.objects.create(send_notification=False)

        response = self.client.post(reverse('create_incident'),  test_incident, follow=True)
        comment_code = CriticalIncident.objects.last().comment_code
        messages = list(response.context['messages'])
        self.assertEqual(comment_code, messages[0].message, "Comment code should be sent as message")


class SendNotificationEmailTest(TestCase):

    def setUp(self):
        self.organization = mommy.make(Organization)
        incident_date = date(2015, 7, 31)
        self.test_incident = {
            'date': incident_date,
            'incident': 'A strang incident happened',
            'reason': 'No one knows',
            'immediate_action': 'No action possible',
            'preventability': 'indistinct',
            'public': True,
            }
        self.reviewer = User.objects.create_user("reviewer", "reviewer@test.edu", "reviewer")

    def save_form(self):
        form = IncidentCreateForm(self.test_incident)
        form.instance.organization = self.organization
        form.save()
        
    def prepare_config(self, send=True, recipient=None):
        # TODO: should only prepare? 
        config = LabCIRSConfig.objects.create(
            login_info_en='Login information',
            login_info_de='Anmeldeinformationen',
            send_notification=send,
            notification_text='Notification text.',
        )
        if recipient is not None:
            config.notification_recipients.add(recipient)
        return config
       

    def test_send_email_after_form_is_saved(self):
        config = LabCIRSConfig.objects.create(send_notification=True)
        config.notification_recipients.add(self.reviewer)
        self.save_form()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'New critical incident')

    def test_set_email_body_in_config(self):
        self.prepare_config(recipient=self.reviewer)
        self.save_form()
        email_body = LabCIRSConfig.objects.first().notification_text
        self.assertEqual(mail.outbox[0].body, email_body)

    @override_settings(EMAIL_HOST='localhost')
    def test_no_notifications_without_proper_smtp_host(self):
        """Raises error as EMAIL_HOST is set to localhost"""
        config = self.prepare_config()
        with self.assertRaises(ValidationError):
            config.full_clean()

    def test_do_not_send_email_if_send_notification_is_false(self):
        self.prepare_config(send=False)
        self.save_form()
        self.assertEqual(len(mail.outbox), 0)

    def test_no_notifications_without_recipients(self):
        config = self.prepare_config()
        with self.assertRaises(ValidationError):
            config.full_clean()

    def test_email_adress_of_all_recipients_in_mail(self):
        self.prepare_config(recipient=self.reviewer)
        self.save_form()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.reviewer.email, mail.outbox[0].to)

    def test_no_notifications_without_sender(self):
        config = self.prepare_config(recipient=self.reviewer)
        with self.assertRaises(ValidationError):
            config.full_clean()

    def test_sender_email_in_email_header(self):
        config = self.prepare_config(recipient=self.reviewer)
        config.notification_sender_email = 'labcirs@labcirs.edu'
        config.save()
        self.save_form()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual('labcirs@labcirs.edu', mail.outbox[0].from_email)


class CriticalIncidentAdminTest(TestCase):

    def test_admin_can_choose_category_in_QMB_block(self,):
        ci_admin = CriticalIncidentAdmin(CriticalIncident, AdminSite())
        qmb_fields = ci_admin.fieldsets[1][1]['fields']
        self.assertIn('category', qmb_fields)


def generate_three_incidents(organization):
    """generate three incidents with different dates in order 2,3,1 and names c, a, b"""
    
    def new_incident(month):
        return mommy.make(CriticalIncident, public=True, 
                          date=date(2015, month, 31), organization=organization)

    incidents = [new_incident(month) for month in (7,8,5)]

    for char, incident in zip('cab', incidents):    
        published_incident = PublishableIncident(critical_incident=incident, publish=True)
        for field in ('incident', 'description', 'measures_and_consequences'):
            for lang in ('de', 'en'):  # TODO: import languages from settings
                setattr(published_incident, (field + '_' + lang), char)
        published_incident.clean()
        published_incident.save()


class PublishedIncidentTest(TestCase):

    def test_new_published_incidents_are_displayed_first(self):
        """Tests if newest published incidents appear first in the table.
        Neglects jQuery.DataTables!!!"""
        reporter = create_role(Reporter, 'reporter')
        organization = mommy.make(Organization, reporter=reporter)
        generate_three_incidents(organization)

        factory = RequestFactory()

        request = factory.get(reverse('incidents_list'))
        request.user = reporter.user
        response = PublishableIncidentList.as_view()(request)

        # newest should come first
        wanted_order = ['b', 'a', 'c']
        real_order = []
        for inc in response.context_data['object_list']:
            real_order.append(inc.incident_en)
        self.assertEqual(real_order, wanted_order)
