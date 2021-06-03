#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":

    # Check Python version as LabCIRS 6 can run with Python 3 only
 
    if sys.version_info.major < 3:
        print('This LabCIRS version requires Python 3 to run.\n'
                'If you are updating an existing production system, '
                'please update your virtual enviroment first.\n'
                'Then install LabCIRS version 6.0, e.g.:\n'
                'git clone --branch v6.0 https://github.com/major-s/labcirs.git\n'
                'migrate the whole project:\n'
                'python manage.py migrate\n'
                'and finally update to the current version if necessary!')
        raw_input('Press any key to exit!')
        exit()
    elif  sys.version_info.minor < 8:
        print('This LabCIRS version was developed with Python 3.8\n'
                +'You are using {}.{} which may work, '.format(sys.version_info.major, sys.version_info.minor)
                +'but the functionality was not tested.')
        text = input('Do you want to proceed?  (y/N):')
        if not text.lower().startswith('y'):
            exit()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "labcirs.settings.production")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
