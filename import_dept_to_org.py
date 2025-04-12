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

from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured

from cirs.models import (Reporter, Reviewer, Department, CriticalIncident, PublishableIncident,
    PublishableIncidentTranslation, LabCIRSConfigTranslation)

# you have to add 'old' database to your settings

def import_single_labcirs(source='old', target='default'):
    """Imports LabCIRS site with only one department to multidepartment site.
    
    Joins a whole LabCIRS site with one department with the curent one. Intendend to join old 
    sites which were used before version 5 into one multidepartment site.
    The databases have to be specified in project settings (production.py).
    Has to be used from the Python shell:
    > python manage.py shell
    >>> from import_dept_to_org import import_single_labcirs
    >>> import_single_labcirs()
    
    Args:
        source: the database of the single department site as defined in the configuration (default 'old')
        target: the database of the current multidepartment site (default 'default')
    
    
    """

    for model in (Reporter, Department):
        no_old_items = model.objects.using(source).count()
        if no_old_items > 1:
            raise ImproperlyConfigured('For import you can have only one {} in your {} database, '
                'but you have {}! Please correct in your original system! Aborting!'.format(
                    model._meta.model_name, source, no_old_items))
        
    
    rep = Reporter.objects.using(source).get()
    user = rep.user
    print user
    user.pk = None
    user.save(using=target)

    rep.pk = None
    rep.user_id = user.pk
    rep.save(using=target)
    
    # rep is defined
    
    reviewers = Reviewer.objects.using(source).all()
    new_reviewers = []
    for rev in reviewers:
        user = rev.user
        user.pk = None
        print user
        user.save(using=target)
        rev.pk = None
        rev.user_id = user.pk
        rev.save(using=target)
        new_reviewers.append(rev)
    # revs are defined
    
    dept = Department.objects.using(source).get()
    config = dept.labcirsconfig
    recipients = [user.username for user in config.notification_recipients.all()]
    translations = LabCIRSConfigTranslation.objects.using(source).filter(master_id=config.pk)

    dept.pk = None
    dept.reporter_id = rep.pk
    dept.save(using=target)

    for rev in new_reviewers:
        dept.reviewers.add(rev)

    dept.labcirsconfig.delete()

    config.pk = None
    config.department_id = dept.pk
    config.save(using=target)
    
    new_recipients = User.objects.filter(username__in=recipients)
    
    for recipient in new_recipients:
        config.notification_recipients.add(recipient)
    
    for translation in translations:
        translation.pk = None
        translation.master_id = config.pk
        translation.save(using=target)
    
    #config done
    
    cis = CriticalIncident.objects.using(source).filter(department__label=dept.label) # just in case
    for ci in cis:
        comments = list(ci.comments.all())
        print comments
        # only if pi exists...
        try:
            pi = ci.publishableincident
            translations = PublishableIncidentTranslation.objects.using(source).filter(master_id=pi.pk)
        except PublishableIncident.DoesNotExist:
            pi = None
            print '{} has no publishable incident'.format(ci)
        
        ci.pk = None
        ci.department_id = dept.pk
        ci.save(using=target)
        if pi is not None:
            pi.pk = None
            pi.critical_incident_id = ci.pk
            pi.save(using=target)
            for translation in translations:
                translation.pk = None
                translation.master_id = pi.pk
                translation.save(using=target)
            
        print comments
        for comment in comments:
            print comment
            username = comment.author.username
            print username
            comment.pk = None
            comment.critical_incident_id = ci.pk
            comment.author_id = User.objects.get(username=username).pk
            comment.save(using=target)
