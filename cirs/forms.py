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


from django import forms
from django.core import mail
from django.forms import Form, ModelForm, Textarea, TextInput, RadioSelect, CharField
from django.forms.utils import ErrorList

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

class IncidentCreateForm(ModelForm):
    error_css_class = "error alert alert-danger"

    class Meta:
        model = CriticalIncident
        fields = ['date', 'incident', 'reason', 'immediate_action',
                  'preventability', 'photo', 'public']
        widgets = {"incident": Textarea(attrs={'cols': 80, 'rows': 5,
                                               'class': "form-control"}),
                   "reason": Textarea(attrs={'cols': 80, 'rows': 5,
                                             'class': "form-control"}),
                   "immediate_action": Textarea(attrs={'cols': 80, 'rows': 5,
                                                       'class': "form-control"}),
                   "public": RadioSelect()
                   }

    def save(self):
        result = super(IncidentCreateForm, self).save()
        notify_on_creation(self, 'New critical incident')
        return result



class IncidentSearchForm(Form):
    incident_code = CharField()


class CommentForm(ModelForm):
    
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {"text": Textarea(attrs={'cols': 80, 'rows': 5, 
                                           'class': "form-control"})
        }

    def save(self):
        result = super(CommentForm, self).save()
        notify_on_creation(self, 'New LabCIRS comment', self.instance.author.id)
        return result

