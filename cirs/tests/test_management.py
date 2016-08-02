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

import json
from collections import OrderedDict
from django.core.management import call_command
from django.test import TestCase

from labcirs.settings.base import get_local_setting, local_config_file


class ManagementCommands(TestCase):

    def test_key_generator(self):
        """New key has to be differen from old one and be 50 chars long"""
        old_key = get_local_setting('SECRET_KEY')
        call_command('makesecretkey')
        new_key = get_local_setting('SECRET_KEY')
        self.assertEqual(len(new_key), 50)
        self.assertNotEqual(old_key, new_key)

    def test_order_of_setting_keys(self):
        """Key order has to be preserved"""
        with open(local_config_file, 'r') as f:
            old_config = json.loads(f.read(), object_pairs_hook=OrderedDict)
        call_command('makesecretkey')
        with open(local_config_file, 'r') as f:
            new_config = json.loads(f.read(), object_pairs_hook=OrderedDict)
        self.assertEqual(old_config.keys(), new_config.keys())
