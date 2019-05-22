# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-09-25 08:54
from __future__ import unicode_literals

from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.db import migrations, models
import django.db.models.deletion

DEPT_PK = 1

# define checks
def check(apps, schema_editor):  # @UnusedVariable
    global DEPT_PK # have to set it here
    Department = apps.get_model('cirs', 'Department')
    CriticalIncident = apps.get_model('cirs', 'CriticalIncident')
    LabCIRSConfig = apps.get_model('cirs', 'LabCIRSConfig')
    config_count = LabCIRSConfig.objects.count()
    ci_count = CriticalIncident.objects.count()
    dept_count =  Department.objects.count()
    # no multiple departments or configurations allowed
    if dept_count > 1 or config_count > 1:
        raise MultipleObjectsReturned('There are to many departments or configurations. '
                                      'Only one is allowed before you can migrate!')
    elif dept_count == 1:
        DEPT_PK = Department.objects.first().pk
    # there has to be exactly one department if incidents and/or configuration are present
    if (ci_count > 0 or config_count > 0) & (dept_count == 0):
        raise ValidationError('There are incidents and/or configuration, but no department. '
                              'In this case there has to be one before you can migrate!')
    
def backwards(apps, schema_editor):  # @UnusedVariable
    pass

def get_department_pk():
    # TODO:  Remove all migrations for version 5.?
    # check for multiple departments is provided before...
    return DEPT_PK
    

class Migration(migrations.Migration):

    dependencies = [
        ('cirs', '0006_data_migration_assign_roles_and_create_department'),
    ]

    operations = [
        migrations.RunPython(check, reverse_code=backwards),
        migrations.AddField(
            model_name='criticalincident',
            name='department',
            field=models.ForeignKey(default=get_department_pk, on_delete=django.db.models.deletion.PROTECT, to='cirs.Department', verbose_name='Department'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='labcirsconfig',
            name='department',
            field=models.OneToOneField(default=get_department_pk, on_delete=django.db.models.deletion.PROTECT, to='cirs.Department', verbose_name='Department'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='labcirsconfig',
            name='send_notification',
            field=models.BooleanField(default=False, help_text='Check if you wish to be informed about new incidents per email.<br>\n            IMPORTANT: Sender email has to exist and at least one recipient is necessary.<br>\n            BUG: If you had no recipients selected before changingn this setting,\n            please choose at least one and save.<br>\n            Not till then you can activate sending of notifications.', verbose_name='Send notification'),
        ),
    ]
