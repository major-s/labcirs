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

from django.contrib.auth.models import User, Permission
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core import mail
from django.core.urlresolvers import resolve, reverse
from django.test import TestCase, RequestFactory, override_settings

from cirs.models import CriticalIncident, PublishableIncident, LabCIRSConfig
from cirs.views import IncidentCreateForm, PublishableIncidentList

from cirs.admin import CriticalIncidentAdmin
from django.contrib.admin.sites import AdminSite


class AddCriticalIncidentTest(TestCase):

    def setUp(self):
        self.username = 'reporter'
        self.email = 'reporter@test.edu'
        self.password = 'reporter'
        self.reporter = User.objects.create_user(self.username, self.email, self.password)

    def test_user_login(self):
        login = self.client.login(username=self.username, password=self.password)

        self.assertEqual(login, True)


class CriticalIncidentModelTest(TestCase):
    
    def setUp(self):
        # create first incident
        # TODO: change to objects.create()
        self.first_incident = CriticalIncident()
        self.first_incident.date = date(2012, 2, 26)
        self.first_incident.public = True
        self.first_incident.category = ['other']
        self.first_incident.save()
    
    def test_saving_and_retriving_incidents(self):
        self.first_incident.photo = File(open("cirs/tests/test.jpg"))
        self.first_incident.save()

        p = CriticalIncident.objects.get(id=1).photo.path

        # TODO: not really working. Compare files
        self.failUnless(open(p), 'file not found')
        # TODO: move category testing to another test
        my_incident = CriticalIncident.objects.get(pk=1)
        self.assertIn('other', my_incident.category)

    def test_cannot_save_future_incidents(self):
        self.first_incident.date = date.today() + timedelta(days=10)
        self.first_incident.status = 'in process'
        self.first_incident.save()
        self.assertRaises(ValidationError, self.first_incident.clean)
    
    def test_comment_code_is_generated_on_creation(self):
        #retreive incident and check for existing comment_code
        my_incident = CriticalIncident.objects.get(pk=1)
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
        self.username = 'reporter'
        self.email = 'reporter@test.edu'
        self.password = 'reporter'
        self.reporter = User.objects.create_user(self.username, self.email, self.password)
        user = User.objects.get(pk=1)
        permission = Permission.objects.get(codename='add_criticalincident')
        user.user_permissions.add(permission)
          
        incident_date = date(2015, 7, 31)
        test_incident = {'date': '07/24/2015',
                         'incident': 'A strang incident happened',
                         'reason': 'No one knows',
                         'immediate_action': 'No action possible',
                         'preventability': 'indistinct',
                         'public': True,
                         }
          
        login = self.client.login(username=self.username, password=self.password)
        LabCIRSConfig.objects.create(send_notification=False)

        response = self.client.post('/incidents/create/',  test_incident, follow=True)
        comment_code = CriticalIncident.objects.last().comment_code
        messages = list(response.context['messages'])
        self.assertEqual(comment_code, messages[0].message, "Comment code should be sent as message")


class SendNotificationEmailTest(TestCase):

    def setUp(self):
        incident_date = date(2015, 7, 31)
        self.test_incident = {
            'date': incident_date,
            'incident': 'A strang incident happened',
            'reason': 'No one knows',
            'immediate_action': 'No action possible',
            'preventability': 'indistinct',
            'public': True,
            }
        self.test_config = {
            'login_info_en': 'Login information',
            'login_info_de': 'Anmeldeinformationen',
            'send_notification': False,
            'notification_text': 'Notification text.',
            }
        self.reviewer = User.objects.create_user("reviewer", "reviewer@test.edu", "reviewer")

    def test_send_email_after_form_is_saved(self):
        config = LabCIRSConfig.objects.create(send_notification=True)
        config.notification_recipients.add(self.reviewer)
        form = IncidentCreateForm(self.test_incident)
        form.save()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'New critical incident')

    def test_set_email_body_in_config(self):
        config = LabCIRSConfig.objects.create(**self.test_config)
        config.notification_recipients.add(self.reviewer)
        config.send_notification = True
        config.save()
        form = IncidentCreateForm(self.test_incident)
        form.save()
        email_body = LabCIRSConfig.objects.first().notification_text
        self.assertEqual(mail.outbox[0].body, email_body)

    @override_settings(EMAIL_HOST='localhost')
    def test_no_notifications_without_proper_smtp_host(self):
        """Raises error as EMAIL_HOST is set to localhost"""
        config = LabCIRSConfig.objects.create(**self.test_config)
        config.send_notification = True
        with self.assertRaises(ValidationError):
            config.full_clean()

    def test_do_not_send_email_if_send_notification_is_false(self):
        config = LabCIRSConfig.objects.create(**self.test_config)
        form = IncidentCreateForm(self.test_incident)
        form.save()
        self.assertEqual(len(mail.outbox), 0)

    def test_no_notifications_without_recipients(self):
        config = LabCIRSConfig.objects.create(**self.test_config)
        config.send_notification = True
        config.save()
        with self.assertRaises(ValidationError):
            config.full_clean()

    def test_email_adress_of_all_recipients_in_mail(self):
        config = LabCIRSConfig.objects.create(**self.test_config)
        config.send_notification = True
        config.notification_recipients.add(self.reviewer)
        config.save()
        form = IncidentCreateForm(self.test_incident)
        form.save()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.reviewer.email, mail.outbox[0].to)

    def test_no_notifications_without_sender(self):
        config = LabCIRSConfig.objects.create(**self.test_config)
        config.send_notification = True
        config.notification_recipients.add(self.reviewer)
        config.save()
        with self.assertRaises(ValidationError):
            config.full_clean()

    def test_sender_email_in_email_header(self):
        config = LabCIRSConfig.objects.create(**self.test_config)
        config.send_notification = True
        config.notification_recipients.add(self.reviewer)
        config.notification_sender_email = 'labcirs@labcirs.edu'
        config.save()
        form = IncidentCreateForm(self.test_incident)
        form.save()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual('labcirs@labcirs.edu', mail.outbox[0].from_email)


class CriticalIncidentAdminTest(TestCase):

    def test_admin_can_choose_category_in_QMB_block(self,):
        ci_admin = CriticalIncidentAdmin(CriticalIncident, AdminSite())
        qmb_fields = ci_admin.fieldsets[1][1]['fields']
        self.assertIn('category', qmb_fields)


def generate_critical_incident(incident_dict, processed=None):
    incident = CriticalIncident.objects.create(**incident_dict)
    if processed is True:
        incident.status = 'in process'
        incident.clean()
        incident.save()
    return incident


def generate_three_incidents():
    """generate three incidents with different dates in order 2,3,1"""
    incident_date = date(2015, 7, 31)
    test_incident = {'date': incident_date,
                     'incident': 'A strang incident happened',
                     'reason': 'No one knows',
                     'immediate_action': 'No action possible',
                     'preventability': 'indistinct',
                     'public': True,
                     }

    first_ci = generate_critical_incident(test_incident, processed=True)
    test_incident['date'] = date(2015, 8, 31)
    second_ci = generate_critical_incident(test_incident, processed=True)
    test_incident['date'] = date(2015, 5, 31)
    third_ci = generate_critical_incident(test_incident, processed=True)
    # publish incidents
    incidents = OrderedDict((('c', third_ci), ('a', first_ci), ('b', second_ci)))
    for char, incident in incidents.iteritems():
        published_incident = PublishableIncident(critical_incident=incident)
        for field in ('incident', 'description', 'measures_and_consequences'):
            for lang in ('de', 'en'):  # TODO: import languages from settings
                setattr(published_incident, (field + '_' + lang), char)
        published_incident.publish = True
        published_incident.clean()
        published_incident.save()


class PublishedIncidentTest(TestCase):

    def setUp(self):
        self.username = 'reporter'
        self.email = 'reporter@test.edu'
        self.password = 'reporter'
        self.reporter = User.objects.create_user(self.username, self.email,
                                                 self.password)

    def test_new_published_incidents_are_displayed_first(self):
        """Tests if newest published incidents appear first in the table.
        Neglects jQuery.DataTables!!!"""
        generate_three_incidents()

        self.factory = RequestFactory()

        request = self.factory.get(reverse('incidents_list'))
        request.user = self.reporter
        response = PublishableIncidentList.as_view()(request)

        # newest should come first
        wanted_order = ['b', 'a', 'c']
        real_order = []
        for inc in response.context_data['object_list']:
            real_order.append(inc.incident_en)
        self.assertEqual(real_order, wanted_order)
