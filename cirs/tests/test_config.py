# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Sebastian Major
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
from django.core.urlresolvers import reverse
from django.test import TestCase

from cirs.models import LabCIRSConfig

LOGIN_INFO = "You can find the login data for this demo installation at "
LINK_TEXT = "the demo login data page"
NOTIFICATION_TEXT = "A new incident was just reported. Plese check it."


class LabCIRSConfigModels(TestCase):
    """Tests LabCIRSConfig model"""

    def test_labcirs_config_save_and_retrieve(self):
        config = LabCIRSConfig()
        config.login_info_en = LOGIN_INFO
        config.login_info_url = reverse('demo_login_data_page')
        config.login_info_link_text_en = LINK_TEXT
        config.send_notification = False
        config.notification_sender_email = 'a@test.edu'
        config.notification_text = NOTIFICATION_TEXT
        config.clean()
        config.save()

        saved_config = LabCIRSConfig.objects.first()

        for field in ('login_info_en', 'login_info_url',
                      'login_info_link_text_en', 'send_notification',
                      'notification_sender_email', 'notification_text'):
            self.assertEqual(getattr(saved_config, field),
                             getattr(config, field)
                             )

    def test_login_info_in_response(self):
        LabCIRSConfig.objects.create(
            login_info_en=LOGIN_INFO,
            login_info_url=reverse('demo_login_data_page'),
            login_info_link_text_en=LINK_TEXT,
            send_notification=False
        )
        response = self.client.get(reverse('login'))
        for text in (LOGIN_INFO, LINK_TEXT):
            self.assertIn(text, str(response))

    def test_add_reviewer_as_notification_recipient(self):
        reviewer = User.objects.create_user("reviewer", "reviewer@test.edu",
                                            "reviewer")
        config = LabCIRSConfig.objects.create(send_notification=False)
        config.notification_recipients.add(reviewer)

        self.assertIn(
            reviewer,
            LabCIRSConfig.objects.first().notification_recipients.all()
        )
