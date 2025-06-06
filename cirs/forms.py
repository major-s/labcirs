# Copyright (C) 2018-2025 Sebastian Major
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


from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.forms import (CharField, ClearableFileInput, DateInput, Form,
                          ModelForm, RadioSelect, Select, Textarea,
                          ValidationError)
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from registration.forms import (RegistrationFormTermsOfService,
                                RegistrationFormUniqueEmail,
                                RegistrationFormUsernameLowercase)

from .models import Comment, CriticalIncident, Department


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


class DivErrorList(forms.utils.ErrorList):
    
    def __unicode__(self):
        return self.as_divs()
    
    def as_divs(self):
        if not self: return u''
        # CSS classes from bootstrap
        return u'<div class="errorlist">%s</div>' % ''.join([u'<small class="text-danger form-text">%s</small>' % e for e in self])


class LabCIRSRegistrationForm(RegistrationFormUsernameLowercase, RegistrationFormUniqueEmail):
    """
    Generates for to create department together with reviewer and reporter users
    """
    # reviewer is not anonymous, so first and last name should be provided
    first_name = forms.CharField(
        label=_('First name'), widget=forms.TextInput(attrs={'class': "form-control"}),
        help_text=_('Please enter your first name'))
    last_name = forms.CharField(
        label=_('Last name'), widget=forms.TextInput(attrs={'class': "form-control"}),
        help_text=_('Please enter your last name'))
    # additional fields for department and reporter
    department_label = forms.SlugField(
        label=_('Department label'),
        widget=forms.TextInput(attrs={'class': "form-control"}),
                               help_text=_('Only letters, digits, - and _. No whitespace!'))
    department_name = forms.CharField(
        label=_('Department name'),
        widget=forms.TextInput(attrs={'class': "form-control"}))
    reporter_name = forms.SlugField(
        label=_('User name for the reporter'),
        widget=forms.TextInput(attrs={'class': "form-control"}),
                               help_text=_('Only letters, digits, - and _. No whitespace! Lowercase only!'))
    
    field_order = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2', 
                   'department_label', 'department_name', 'reporter_name']
    
    error_css_class = "error"
    
    def __init__(self, *args, **kwargs):
        super(LabCIRSRegistrationForm, self).__init__(*args, **kwargs)
        for field in ('username', 'email', 'password1', 'password2'):
            self.fields[field].widget.attrs.update({'class': "form-control"})
        self.error_class = DivErrorList

    def clean_email(self):
        super(LabCIRSRegistrationForm, self).clean_email()
        if settings.REGISTRATION_RESTRICT_USER_EMAIL is True:
            allowed_domains = settings.REGISTRATION_EMAIL_DOMAINS
            allowed_list = ""
            if len(allowed_domains) == 1:
                allowed_list = gettext(f"Only @{allowed_domains[0]} is allowed!")
            elif len(allowed_domains) > 1:
                allowed_list = gettext(f"Allowed domains are @{', @'.join(allowed_domains)}")
            error_message = ' '.join((gettext('You cannot register with this email domain!'),
                                      allowed_list))
            
            email_domain = self.cleaned_data['email'].split('@')[-1]
            if email_domain not in allowed_domains:
                raise forms.ValidationError(error_message, code='invalid_email')

        return self.cleaned_data['email']

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

class LabCIRSRegistrationFormWithTOS(RegistrationFormTermsOfService, LabCIRSRegistrationForm):

    def __init__(self, *args, **kwargs):
        super(LabCIRSRegistrationFormWithTOS, self).__init__(*args, **kwargs)

        self.fields['tos'].widget.attrs.update({'class': "form-check-input", 
                                                'style': "margin-left:0.5rem"})