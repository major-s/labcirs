# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Sebastian Major
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

from __future__ import unicode_literals

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.db import migrations

# TODO: make kind of setup function to create permissions

def get_permission(codename, models):
    try:
        permission = models.Permission.objects.get(codename=codename)
        return permission
    except models.Permission.DoesNotExist:
        if models.CriticalIncident.objects.count() > 0:
            raise ValidationError('Permission does not exist although there '
                                  'are critcal incidents in the database!')

def create_reporter(models):
    # only reporter should have the permission to add incidents, therefore
    # we search for this user
    # in new installations there are no permissions during initial migration
    # therefore try is necessary
    # only one reporter should exist before this migration.
        
    permission = get_permission('add_criticalincident', models)
    try:
        reporter = models.User.objects.get(user_permissions=permission)
        print('Assigning {} as reporter'.format(reporter.username))
        models.Reporter.objects.create(user=reporter)
    except models.User.DoesNotExist:
        if models.CriticalIncident.objects.count() > 0:
            raise ValidationError('There are critical incidents in the database, '
                                  'therefore there should be one user with permission '
                                  '"add_criticalincident". '
                                  'Correct and rerun the migration!')
    except MultipleObjectsReturned as e:
        raise e

def create_reviewers(models):
    # all users with reviewer permissions are turned to reviewers
    permission = get_permission('change_criticalincident', models) 
    reviewers = models.User.objects.filter(user_permissions=permission)
    if (reviewers.count() == 0) & (models.CriticalIncident.objects.count() > 0):
        raise ValidationError('There are critical incidents in the database, '
                              'therefore there should be at least one user with permission '
                              '"change_criticalincident". '
                              'Correct and rerun the migration!')
    for review_user in reviewers:
        try:
            # model.full_clean() does not work in migrations!!!
            if review_user.reporter.user == review_user:
                raise ValidationError('{} cannot be reporter and reviewer. Please correct permissions and migrate again'.format(review_user.username))
        except models.Reporter.DoesNotExist:
            print('Assigning {} as reviewer'.format(review_user.username))
            models.Reviewer.objects.create(user = review_user)


def create_department(models):
    # in installations for single organizations/departments there should be only one reporter.
    # if multiple exist, exception is thrown while creating reporter role
    # there has to be also at least one reviewer and one valid configuration
    reviewers = models.Reviewer.objects.all()
    if (models.Reporter.objects.count() == 1) & (reviewers.count() > 0) & (models.LabCIRSConfig.objects.count() == 1):
        dept = models.Department.objects.create(
            label=settings.ORGANIZATION,
            name=settings.ORGANIZATION,
            reporter=models.Reporter.objects.first()
            )
        for reviewer in reviewers:
            dept.reviewers.add(reviewer)


def backwards(apps, schema_editor):  # @UnusedVariable
    for cls_name in ('Reporter', 'Reviewer', 'Department'):
        model_cls = apps.get_model('cirs', cls_name)
        model_cls.objects.all().delete()


def forward(apps, schema_editor):  # @UnusedVariable
    
    class ArchivedModels():
        def __init__(self):
            self.User = apps.get_model('auth', 'User')
            self.Permission = apps.get_model('auth', 'Permission')
            self.CriticalIncident = apps.get_model('cirs', 'CriticalIncident')
            self.Reporter = apps.get_model('cirs', 'Reporter')
            self.Reviewer = apps.get_model('cirs', 'Reviewer')
            self.Department = apps.get_model('cirs', 'Department')
            self.LabCIRSConfig = apps.get_model('cirs',  'LabCIRSConfig')
        
    models = ArchivedModels()
    
    create_reporter(models)
    create_reviewers(models)
    create_department(models)
    

class Migration(migrations.Migration):

    dependencies = [
        ('cirs', '0005_department_and_roles'),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=backwards)
    ]
