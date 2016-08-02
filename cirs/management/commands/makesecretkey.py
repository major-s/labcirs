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
from django.core.management.base import BaseCommand, CommandError
from django.utils.crypto import get_random_string

from labcirs.settings.base import get_local_setting, local_config_file


class Command(BaseCommand):
    help = "Generates new secret key and writes it to the local config file."

    def handle(self, *args, **options):
        # copied from djangos startproject command
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        secret_key = get_random_string(50, chars)
        # use OrderedDict to preserve the order of the keys in the json file
        with open(local_config_file, 'r') as f:
            local_config = json.loads(f.read(), object_pairs_hook=OrderedDict)
        local_config['SECRET_KEY'] = secret_key
        with open(local_config_file, 'w') as f:
            json.dump(local_config, f, indent=4)
