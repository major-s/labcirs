#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "labcirs.settings.dev")

    print """WARNING: manage.py uses development settings as default.
    If production settings are necessary run with:

    --settings=labcirs.settings.production
    """
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
