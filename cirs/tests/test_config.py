# Copyright (C) 2016-2025 Sebastian Major
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

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from model_mommy import mommy
from parameterized import parameterized

from cirs.models import LabCIRSConfig

LOGIN_INFO = "You can find the login data for this demo installation at "
LINK_TEXT = "the demo login data page"
NOTIFICATION_TEXT = "A new incident was just reported. Plese check it."


class LabCIRSConfigModels(TestCase):
    """Tests LabCIRSConfig model"""
    
    def setUp(self):
        self.dept = mommy.make_recipe('cirs.department')
        self.config = self.dept.labcirsconfig

    def test_labcirs_config_save_and_retrieve(self):
        self.config.login_info = LOGIN_INFO
        self.config.login_info_url = reverse('demo_login_data_page') # TODO: remove to clean urls.py
        self.config.login_info_link_text = LINK_TEXT
        self.config.send_notification = False
        self.config.notification_sender_email = 'a@test.edu'
        self.config.notification_text = NOTIFICATION_TEXT
        self.config.clean()
        self.config.save()

        saved_config = LabCIRSConfig.objects.first()

        for field in ('login_info', 'login_info_url',
                      'login_info_link_text', 'send_notification',
                      'notification_sender_email', 'notification_text'):
            self.assertEqual(getattr(saved_config, field),
                             getattr(self.config, field)
                             )

    @parameterized.expand([
        (LOGIN_INFO,),
        (LINK_TEXT,),
    ])
    def test_login_info_in_response(self, text):
        self.config.login_info_en = LOGIN_INFO
        self.config.login_info_url = reverse('demo_login_data_page') # TODO: remove to clean urls.py
        self.config.login_info_link_text_en = LINK_TEXT
        self.config.clean()
        self.config.save()

        response = self.client.get(self.dept.get_absolute_url(), follow=True)
        self.assertIn(text, str(response.content))

    def test_add_reviewer_as_notification_recipient(self):
        reviewer = User.objects.create_user("reviewer", "reviewer@test.edu",
                                            "reviewer")
        self.config.notification_recipients.add(reviewer)

        self.assertIn(
            reviewer,
            LabCIRSConfig.objects.first().notification_recipients.all()
        )
