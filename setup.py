# -*- coding: utf-8 -*-
#
# Copyright (C) 2019-2021 Sebastian Major
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


import io
import json
import os
import sys
import shutil

from collections import OrderedDict
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    from labcirs.settings.base import local_config_file
except:
    print('Import not possible. Using hardcoded version')
    local_config_file = os.path.join(BASE_DIR, 'labcirs', 'settings', 'local_config.json')

MODIFIED = 'modified'
UNCHANGED = 'unchanged'



# It has to be hardcoded,

config_template_file = os.path.join(BASE_DIR, 'labcirs', 'settings', 'local_config.json.template')
wsgi_file = os.path.join(BASE_DIR, 'labcirs', 'wsgi.py')

def read_config(json_file):
    with io.open(json_file, mode='r', encoding='utf-8') as f:
            config = json.loads(f.read(), object_pairs_hook=OrderedDict)
    return config

def write_config(config):
    '''Writes config to json file, restarts the wsgi server and returns config from file'''
    # TODO: Backup old file before saving??
    output = json.dumps(config, indent=4, ensure_ascii=False)
    with io.open(local_config_file, mode='w', encoding='utf-8') as f:
            f.write(output)
    Path(wsgi_file).touch()
    return read_config(local_config_file)

def check_secret_key(local_config):
    if local_config['SECRET_KEY'] == config_template['SECRET_KEY']:
        text = input('Your config uses default secret_key. This is insecure!\n'
                         'It is recommended to generate a new one (Y/n):')
        if not text.lower().startswith('n'):
            makesecretkey.Command().handle(local_config_file=local_config_file)
            Path(wsgi_file).touch()

    return read_config(local_config_file)
    # returning flags also might be usefull for restarting wsgi

def check_missing_keys(local_config):
    if local_config.keys() != config_template.keys():
        print ('Some new keys are missing in your config.\n'
               'They will be added now? The order might change,\n'
               'comments will be updated.')

        new_config = OrderedDict()
        for key in config_template.keys():
            try:
                if key.startswith('_'):
                    if local_config[key] != config_template[key]:
                        print('Updating comment {} from:\n{}\nto:\n{}'.format(
                            key, local_config[key], config_template[key]))
                    new_config[key] = config_template[key]
                else:
                    new_config[key] = local_config[key]
            except KeyError:
                if key.startswith('_'):
                    new_config[key] = config_template[key]
                else:
                    new_config[key] = add_or_modify_conf_entry(key, config_template[key])
                print('Added {}: {}'.format(key, new_config[key]))

        return write_config(new_config)


def add_to_conf_list(key, conf_list):
    value = input('%s: Append items to %s:' % (key, conf_list))
    if value == '':
        return conf_list
    else:
        conf_list.append(value)
        return add_to_conf_list(key, conf_list)
    
def add_to_conf_dict(ord_dict):
    new_key = input('Enter the key. Single new line stops editing:')
    if new_key == '':
        return ord_dict
    else:
        value = input('Enter value for %s:' % new_key)
        ord_dict[new_key] = value
        text = input('Do you want to add more? (Y/n):')
        if text.lower().startswith('n'):
            return ord_dict
        else:
            return add_to_conf_dict(ord_dict)
  
def add_or_modify_conf_entry(k, v):
    '''Modify config entries based on their type.'''
    # Still needs improvement 
    try:
        # print comment/help if present
        print(local_config['_'+k])
    except:
        pass
    if type(v) in [str, int, bool]:
        # TODO: check if works in Python 3 and remove after update
        try:
            value = input('%s (%s): [%s]:' % (k, type(v), v))
        except UnicodeEncodeError:
            value = input('%s (%s) [%s] (non ASCII chars not displayed):' % (k, type(v), ''.join(i for i in v if ord(i)<128))).decode(sys.stdin.encoding)
        if value == '':
            return v
        else:
            if type(v) is int:
                return int(value)
            elif type(v) is bool:
                if value.lower() == 'false':
                    return False
                elif value.lower() == 'true':
                    return True
            else:
                # in Python 3 input strings don't need to be decoded
                # if type(value) is str:
                #     return value.decode('utf-8')
                # else:
                return value
    elif type(v) is list:
        return add_to_conf_list(k, v)
    elif type(v) is OrderedDict:
        if len(v.keys()) > 0:
            print('{} has following items:'.format(k))
            for key, value in v.items():
                print('%s: %s' % (key, value))
        text = input('Do you want to add? (Y/n):')
        if text.lower().startswith('n'):
            return v
        else:
            return add_to_conf_dict(v)
    else:
        print('Cannot recognize type {} for {}. Returning default ({})'.format(type(v), k, v))
        return v

def check_whole_conf(local_config):
    for k, v in local_config.items():
        # skip comments
        if k.startswith('_'):
            continue
        # don't print secret key or filename
        elif k in ('SECRET_KEY', 'FILENAME'):
            continue
        else:
            local_config[k] = add_or_modify_conf_entry(k, v)

    return write_config(local_config)

if __name__ == "__main__":
    
    config_template = read_config(config_template_file)
    
    print ('This is basic script for local LabCIRS configuration\n'
           'You can change string values and dictionary entries and add values to lists or '
           'dictionares\n'
           'Deleting from the last two is not possible and has to be done directly in the '
           'JSON config file')
    
    # check if local config file exists
    if not os.path.isfile(local_config_file):
        print('Local configuration file is missing. Generating from template...')
        shutil.copyfile(config_template_file, local_config_file)
        local_config = read_config(local_config_file)
        print('Now check and modify settings according to your needs:')
        local_config = check_whole_conf(local_config)
    else:
        local_config = read_config(local_config_file)
        # check keys
        check_missing_keys(local_config)
        # check whole file if wanted
        text = input('All keys are present. Do you want to check all? (Y/n):')
        if not text.lower().startswith('n'):
            check_whole_conf(local_config)
    # alway check secret key 
    from cirs.management.commands import makesecretkey
    local_config = check_secret_key(local_config)
    

# TODO: check if parler languages fit with languages