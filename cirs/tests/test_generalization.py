# -*- coding: utf-8 -*-
#
# Copyright (C) 2016-2019 Sebastian Major
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
import json

from django.core.urlresolvers import reverse
from django.test import TestCase

from labcirs.settings.base import get_local_setting


class Labcirs4All(TestCase):
    """Tests for generalized LabCIRS

    It tests also the get_local_config function from settings
    """

    def setUp(self):
        self.default = 'LabCIRS'
        self.name = 'MyLab'
        self.config_file = 'test_config.json'

    def tearDown(self):
        if os.path.isfile(self.config_file):
            os.remove(self.config_file)

    def write_test_config(self, config_file, value):
        f = open(self.config_file, 'w')
        json.dump({'ORGANIZATION': value}, f, indent=2)
        f.close()

    def test_custom_organization_name(self):
        """Use the stored name."""
        self.write_test_config(self.config_file, self.name)
        organization = get_local_setting('ORGANIZATION',
                                         config_file=self.config_file)
        self.assertEqual(organization, self.name)

    def test_get_local_conf_accepts_default(self):
        """Althoug default is specifed the stored name should be used."""
        self.write_test_config(self.config_file, self.name)
        organization = get_local_setting('ORGANIZATION', self.default,
                                         config_file=self.config_file)
        self.assertEqual(organization, self.name)

    def test_get_local_conf_returns_default_only_if_value_empty(self):
        """The name should be the default LabCIRS."""
        self.write_test_config(self.config_file, '')
        organization = get_local_setting('ORGANIZATION', self.default,
                                         config_file=self.config_file)
        self.assertEqual(organization, 'LabCIRS')

    def test_organization_in_context_data(self):
        response = self.client.get(reverse('login'))
        organization = get_local_setting('ORGANIZATION', 'LabCIRS')
        self.assertIn(organization, response.content.decode('utf-8'))