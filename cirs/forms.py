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


from django import forms
from django.contrib.auth.models import User
from django.core import mail
from django.forms import (Form, ModelForm, Textarea, RadioSelect, CharField, Select, 
                          ClearableFileInput, DateInput, ValidationError)
#from django.forms.utils import ErrorList
from django.utils.translation import ugettext_lazy as _

from registration.forms import (RegistrationFormTermsOfService, RegistrationFormUsernameLowercase,
                                RegistrationFormUniqueEmail)

from .models import CriticalIncident, Comment, Department




def notify_on_creation(form, department, subject='', excluded_user_id=None):
    config = department.labcirsconfig
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
        department = self.instance.department
        notify_on_creation(self, department, 'New critical incident')
        return result


class IncidentSearchForm(Form):
    incident_code = CharField(label=_('Incident code'))
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
        department = self.instance.critical_incident.department
        notify_on_creation(self, department, 'New LabCIRS comment', self.instance.author.id)
        return result




class LabCIRSRegistrationForm(RegistrationFormTermsOfService, RegistrationFormUsernameLowercase):#,
                 #RegistrationFormUniqueEmail):
    """
    Generates for to create department together with reviewer and reporter users
    """
    department_label = forms.SlugField(
        widget=forms.TextInput(attrs={'class': "form-control col-sm-6"}),
                               help_text=_('Only letters, numbers and -/_'))
    department_name = forms.CharField(widget=forms.TextInput(attrs={'class': "form-control col-sm-6"}))
    reporter_name = forms.SlugField(widget=forms.TextInput(attrs={'class': "form-control col-sm-6"}),
                                    help_text=_('Only letters, numbers and -/_'))
    
    field_order = ['username', 'email', 'password1', 'password2', 'department_label',
                   'department_name', 'reporter_name', 'tos']
    
    def __init__(self, *args, **kwargs):
        super(LabCIRSRegistrationForm, self).__init__(*args, **kwargs)
        for field in ('username', 'email', 'password1', 'password2'):
            self.fields[field].widget.attrs.update({'class': "form-control col-sm-6"})
        self.fields['tos'].widget.attrs.update({'class': "form-check-input col-sm-1"})


    def clean_department_label(self):
        department_label = self.cleaned_data['department_label']
        if Department.objects.filter(label=department_label).exists():
            raise forms.ValidationError(_('Department with this label already exists!'))
        return department_label
    
    def clean_department_name(self):
        department_name = self.cleaned_data['department_name']
        if Department.objects.filter(name=department_name).exists():
            raise forms.ValidationError(_('Department with this name already exists!'))
        return department_name
    
    def clean_reporter_name(self):
        reporter_name = self.cleaned_data['reporter_name']
        if User.objects.filter(username=reporter_name).exists():
            raise forms.ValidationError(_('This user already exists!'))
        return reporter_name
