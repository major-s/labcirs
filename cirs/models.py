# -*- coding: utf-8 -*-
#
# Copyright (C) 2016-2018 Sebastian Major
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

from __future__ import unicode_literals
from datetime import date
from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from multiselectfield import MultiSelectField


class Role(models.Model):
    user = models.OneToOneField(User, verbose_name=_('User'), on_delete=models.PROTECT,
        help_text='User assigned to other roles and superusers are not listed here!')

    def clean(self):
        if self.user.is_superuser:
            raise ValidationError(
                _('Superuser cannot become {}'.format(type(self).__name__.lower())))

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.user.username


class Reporter(Role):
    
    def clean(self):
        super(Reporter, self).clean()
        if hasattr(self.user, 'reviewer'):
            raise ValidationError(
                _('This user is already a reviewer and thus cannot become a reporter'))
    
    class Meta:
        verbose_name = _('Reporter')
        verbose_name_plural = _('Reporters')


class Reviewer(Role):
    REVIEWER_PERM_CODES = ('change_criticalincident', 'add_publishableincident', 
                           'change_publishableincident', 'change_labcirsconfig')
    REVIEWER_PERMS = Permission.objects.filter(codename__in=REVIEWER_PERM_CODES)
    
    def clean(self):
        super(Reviewer, self).clean()
        if hasattr(self.user, 'reporter'):
            raise ValidationError(
                _('This user is already a reporter and thus cannot become a reviewer'))
            
    def save(self, *args, **kwargs):
        super(Reviewer, self).save(*args, **kwargs)
        self.user.user_permissions.set(self.REVIEWER_PERMS)
        self.user.is_staff = True
        self.user.save()

    class Meta:
        verbose_name = _('Reviewer')
        verbose_name_plural = _('Reviewers')      


class Department(models.Model):
    label = models.CharField(_('Label'), max_length=32, unique=True)
    name = models.CharField(_('Name'), max_length=255, unique=True)
    reporter = models.OneToOneField(Reporter, verbose_name=_("Reporter"), on_delete=models.PROTECT,
            help_text='Reporters assigned to other departments are not listed here!')
    reviewers = models.ManyToManyField(Reviewer, verbose_name=_("Reviewers"), related_name='departments')

    class Meta:
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')

    def __unicode__(self):
        return self.label


FREQUENCY_CHOICES = (('singular case', _('singular case (for the first time)')),
                     ('seldom', _('seldom (once per year)')),
                     ('occasional', _('occasional (once per month)')),
                     ('frequent', _('frequent (once per Week)')),
                     ('regular', _('regular (daily)')))
HAZARD_CHOICES = (('very low', _('very low')), ('low', _('low')),
                  ('moderate', _('moderate')), ('high', _('high')),
                  ('very high', _('very high')))
PREVENTABILITY_CHOICES = (('indistinct', _('appraisal not possible')),
                          ('avoidable', _('The incident was avoidable')),
                          ('not avoidable', _('The incident was not avoidable')))
PUBLIC_CHOICES = ((True, _('I agree that this report will be made public to people outside the quality management team after copyedit.')),
    (False, _('I DO NOT agree that this report will be made public to people outside the quality management team even after copyedit.')))
RISK_CHOICES = (('low', _('low')), ('middle', _('middle')), ('high', _('high')))
STATUS_CHOICES = (('new', _('new')), ('in process', _('in process')),
                  ('under supervision', _('under supervision')),
                  ('completed', _('completed')))
CATEGORY_CHOICES = (('organisation/communication', _('organisation/communication')),
                    ('technique/methods', _('technique/methods')),
                    ('knowledge/training', _('knowledge/training')),
                    ('concentration/attention (mistake/slip)',
                     _('concentration/attention (mistake/slip)')),
                    ('infrastructure', _('infrastructure')),
                    ('other', _('other'))
                    )


class CriticalIncident(models.Model):
    """
    Generate incident objects. The first part is generated by the reporter,
    the second, separated by #review in the source code
    may be generated by the reviewer.
    """
    # general part, visible to all
    date = models.DateField(_("Date of incident"))
    incident = models.TextField(_("Mistake / problem / critical incident"))
    reason = models.TextField(_("Cause of failure"))
    immediate_action = models.TextField(
        _("Immediate action / suggestion"), help_text=_(
            "Immediate action or suggestion regarding prevention / troubleshooting"
            )
        )
    preventability = models.CharField(
        _("Preventability"), max_length=255, choices=PREVENTABILITY_CHOICES,
        help_text=_("In your opinion, was the incident avoidable or not?"))
    photo = models.ImageField(
        _("Photo"), upload_to="photos/%Y/%m/%d", null=True, blank=True)
    public = models.BooleanField(
        _("Publication"), choices=PUBLIC_CHOICES, default=None)
    comment_code = models.CharField(max_length=16, blank=True)
    # auto filled part, invisible for reporter
    reported = models.DateField(_("Date of report"), auto_now_add=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    # review part, invisible for reporter
    action = models.TextField(_("Action"), blank=True)
    responsibilty = models.CharField(
        _("Responsibility"), max_length=255, blank=True)
    review_date = models.DateField(_("Review date"), null=True, blank=True)
    status = models.CharField(
        _("Status"), max_length=255, choices=STATUS_CHOICES, default="new")
    risk = models.CharField(
        _("Risk classification"), max_length=255, choices=RISK_CHOICES, blank=True)
    frequency = models.CharField(
        _("Frequency"), max_length=255, choices=FREQUENCY_CHOICES, blank=True)
    hazard = models.CharField(
        _("Hazard"), help_text=_("For emploees or science"), max_length=255,
        choices=HAZARD_CHOICES, blank=True)
    category = MultiSelectField(
        _("Category"), max_length=255, choices=CATEGORY_CHOICES, blank=True)

    class Meta:
        verbose_name = _("Critical incident")
        verbose_name_plural = _("Critical incidents")

    def photo_tag(self):
        photo_html_tag = ''
        if self.photo:
            image_url = str(settings.MEDIA_URL) + str(self.photo)
            photo_html_tag = format_html(
                '<a href="%s" target="_blank"><img style="max-width:300px;max-height:200px" src="%s" /></a><br>%s' %
                (image_url, image_url, _("Click to see full size in new window/tab")))
        return photo_html_tag
    photo_tag.short_description = _("Photo")
    photo_tag.help_text = _("Click to see full size in new window/tab")
    photo_tag.allow_tags = True

    def clean(self):
        today = date.today()
        if self.date and self.date > today:
            raise ValidationError(_("Please report only incidents which already happened."))
        # TODO: This is very ugly. Should find better option to force one choice from the users.  
        if self.public == "Empty" or self.public == "Leer":
            raise ValidationError(_("Please decide if this report may be published in the lab."))
        if self.id is not None:
            if self.status == 'new':
                for field in ('action', 'responsibilty', 'review_date', 'risk', 'frequency'):
                    if field != '':
                        raise ValidationError(_('If anything was changed in the QMB block, please set status at least to "in process".'))
    
    def get_absolute_url(self):
        return reverse('incident_detail', args=[str(self.id)])
    
    def __unicode__(self):
        info = (self.incident[:25] + '..') if len(self.incident) > 25 else self.incident
        return info
    
    def save(self, *agrs, **kwargs):
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789@#$%&*-_=+'
        while not self.comment_code:
            random_string = get_random_string(8, chars)
            if CriticalIncident.objects.filter(comment_code=random_string).count() == 0:
                self.comment_code = random_string
        super(CriticalIncident, self).save(*agrs, **kwargs)

class PublishableIncident(models.Model):
    critical_incident = models.OneToOneField(CriticalIncident,
                                             verbose_name=_("Critical incident"))
    incident_de = models.CharField(_("Incident (in German)"), max_length=255)
    incident_en = models.CharField(_("Incident (in English)"), max_length=255)
    description_de = models.TextField(_("Description (in German)"), blank=True)
    description_en = models.TextField(_("Description (in English)"), blank=True)
    measures_and_consequences_de = models.TextField(
        _("Measures and consequences (in German)"), blank=True)
    measures_and_consequences_en = models.TextField(
        _("Measures and consequences (in English)"), blank=True)
    publish = models.BooleanField(_("Publish"), default=False)

    class Meta:
        verbose_name = _("Publishable incident")
        verbose_name_plural = _("Publishable incidents")
        ordering = ['-id']

    def clean(self):
        forced_fields = (self.incident_de, self.incident_en,
                         self.description_de, self.description_en,
                         self.measures_and_consequences_de,
                         self.measures_and_consequences_en)
        if self.critical_incident.public is False:
            raise ValidationError(_("The reporter did not agreed to publish this incident!"))
        if self.publish is True:
            for field in forced_fields:
                if field == "":
                    raise ValidationError(_("All fields (in all languages) are mandatory for publication!"))

    def __unicode__(self):
        return self.incident_de


class LabCIRSConfig(models.Model):
    EMAIL_HOST_ERROR = _(
        'If you want to send notifications, an existing email server distinct '
        'from localhost has to be set by the server administrator in the local '
        'server configuration.')

    # Login data
    login_info_en = models.TextField(_('Login info (in English)'))
    login_info_de = models.TextField(_('Login info (in German)'))
    login_info_url = models.URLField(_('URL for login info'), blank=True)
    login_info_link_text_en = models.CharField(_('Link text (in English)'),
                                               max_length=255, blank=True)
    login_info_link_text_de = models.CharField(_('Link text (in German)'),
                                               max_length=255, blank=True)
    # Notification settings
    send_notification = models.BooleanField(
        _('Send notification'),
        help_text=_(
            """Check if you wish to be informed about new incidents per email.<br>
            IMPORTANT: Sender email has to exist and at least one recipient is necessary.<br>
            BUG: If you had no recipients selected before changingn this setting,
            please choose at least one and save.<br>
            Not till then you can activate sending of notifications.""")
        )
    notification_sender_email = models.EmailField(
        _('Notification sender email address'), blank=True,
        help_text=_('Enter a valid email address you want to use as a sender'))
    # TODO: limit_choices_to should actually use permissions. Check if user has email!
    notification_recipients = models.ManyToManyField(
        User, verbose_name=_('Notification recipients'), null=True, blank=True,
        help_text=_('Choose recipients of the notification email'),
        limit_choices_to={'is_superuser': False, 'is_staff': True})
    notification_text = models.TextField(
        _('Notification text'), blank=True,
        help_text=('Enter the message which will be send to the reviewer(s) '
                   'when a new incident is reported')
        )

    class Meta:
        verbose_name = _('LabCIRS configuration')
        verbose_name_plural = _('LabCIRS configuration')

    def clean(self):
        # TODO: show all error messages if multiple validation errors occur at the same time
        if self.send_notification is True:
            if (settings.EMAIL_HOST == '' or settings.EMAIL_HOST == 'localhost'):
                raise ValidationError(self.EMAIL_HOST_ERROR)
            if self.notification_recipients.all().count() == 0:
                raise ValidationError(_('You have to choose at least one notification recipient.'))
            if self.notification_sender_email == '':
                raise ValidationError(_('You have to enter valid sender email.'))

COMMENT_STATUS_CHOICES = (('open', _('open')), ('in process', _('in process')),
                  ('closed', _('closed')))
            
class Comment(models.Model):
    critical_incident = models.ForeignKey(CriticalIncident, 
                                          verbose_name=_("Critical incident"),
                                          related_name='comments',
                                          on_delete=models.PROTECT)
    author = models.ForeignKey(User, verbose_name=_("Author"), 
                               on_delete=models.PROTECT)
    created = models.DateField(_("Created at"), auto_now_add=True)
    text =  models.TextField(_("Text"))
    status = models.CharField(
        _("Status"), help_text=_("Status of the comment"), max_length=255,
        choices=COMMENT_STATUS_CHOICES, default=COMMENT_STATUS_CHOICES[0][0])
    
    def __unicode__(self):
        return self.text[:64]
