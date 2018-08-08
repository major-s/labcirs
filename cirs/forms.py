# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Sebastian Major
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


#from django import forms
from django.core import mail
from django.forms import (Form, ModelForm, Textarea, TextInput, RadioSelect, 
                          CharField, Select, ClearableFileInput, DateInput, ValidationError)
from django.forms.utils import ErrorList
from django.utils.translation import ugettext_lazy as _

from .models import CriticalIncident, Comment, LabCIRSConfig


def notify_on_creation(form, subject='', excluded_user_id=None):
    config = LabCIRSConfig.objects.first()
    if config.send_notification:
        # send only if incident was saved
        if form.instance.pk is not None:
            try:
                # TODO: add comment notification
                mail_body = config.notification_text
            except:
                mail_body = ""
            to_list = []
            for user in config.notification_recipients.all().exclude(id=excluded_user_id):
                to_list.append(user.email)
            mail.send_mail(subject, mail_body,
                           config.notification_sender_email,
                           to_list, fail_silently=False)


class BootstrapRadioSelect(RadioSelect):
    # Used only in Django >= 1.11 as before no templates were used for widgets.
    # The built-in templates have problems when used with Bootstrap 4 class="form-check-input"
    # Older versions simply ignore this attribute.
    template_name="cirs/radio_option_bootstrap_4.html"


class IncidentCreateForm(ModelForm):
    error_css_class = "error alert alert-danger"

    class Meta:
        model = CriticalIncident
        fields = ['date', 'incident', 'reason', 'immediate_action',
                  'preventability', 'photo', 'public']
        widgets = {"date": DateInput(attrs={'class': "form-control col-sm-5"}),
                   "incident": Textarea(attrs={'rows': 5, 'class': "form-control"}),
                   "reason": Textarea(attrs={'rows': 5, 'class': "form-control"}),
                   "immediate_action": Textarea(attrs={'rows': 5, 'class': "form-control"}),
                   "preventability": Select(attrs={'class': "form-control col-sm-5"}),
                   "photo": ClearableFileInput(attrs={'class': "form-control-file"}),
                   "public": BootstrapRadioSelect(attrs={'class': "form-check-input"})
                   }

    def save(self):
        result = super(IncidentCreateForm, self).save()
        notify_on_creation(self, 'New critical incident')
        return result


class IncidentSearchForm(Form):
    incident_code = CharField()
    incident_code.widget.attrs.update({'class': "form-control col-sm-3"})
    error_css_class = "error alert alert-danger"
    
    def clean_incident_code(self):
        comment_code = self.cleaned_data.get('incident_code')
        try:
            CriticalIncident.objects.get(comment_code=comment_code)
            return comment_code
        except CriticalIncident.DoesNotExist:
            raise ValidationError(_('No matching critical incident found!'), code='invalid_id')


class CommentForm(ModelForm):
    
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {"text": Textarea(attrs={'rows': 5, 'class': "form-control"})}

    def save(self):
        result = super(CommentForm, self).save()
        notify_on_creation(self, 'New LabCIRS comment', self.instance.author.id)
        return result

