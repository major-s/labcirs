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

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME, authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.core import mail
from django.core.urlresolvers import reverse_lazy
from django.forms import ModelForm, Textarea, TextInput, RadioSelect
from django.forms.utils import ErrorList
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView

from .models import CriticalIncident, PublishableIncident, LabCIRSConfig


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
        config = LabCIRSConfig.objects.first()
        if config.send_notification:
            # send only if incident was saved
            if self.instance.pk is not None:
                try:
                    mail_body = config.notification_text
                except:
                    mail_body = ""
                to_list = []
                for user in config.notification_recipients.all():
                    to_list.append(user.email)
                mail.send_mail('New critical incident', mail_body,
                               config.notification_sender_email,
                               to_list, fail_silently=False)
        return result


class IncidentCreate(CreateView):
    model = CriticalIncident
    form_class = IncidentCreateForm
    success_url = 'success'

    @method_decorator(permission_required('cirs.add_criticalincident'))
    def dispatch(self, *args, **kwargs):
        return super(IncidentCreate, self).dispatch(*args, **kwargs)


class PublishableIncidentList(ListView):
    """
    Returns a simple list of publishable incidents where "publish" is set to true.
    """
    queryset = PublishableIncident.objects.filter(publish=True)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(PublishableIncidentList, self).dispatch(*args, **kwargs)


def login_user(request, redirect_field_name=REDIRECT_FIELD_NAME):
    username = password = message = message_class = ''
    redirect_url = request.GET.get(redirect_field_name, '')
    if len(redirect_url) == 0:
        redirect_url = reverse_lazy('labcirs_home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                # TODO: prevent superuser accessing frontend view
                if user.has_perm('cirs.add_criticalincident'):
                    return HttpResponseRedirect(redirect_url)
                else:
                    return HttpResponseRedirect(reverse_lazy('admin:index'))
            else:
                message = _('Your account is not active, please contact the admin.')
                message_class = 'warning'
        else:
            message = _("""Your username and/or password were incorrect.
                        Please check the information below!""")
            message_class = 'danger'

    context = {'message': message,
               'message_class': message_class,
               'username': username,
               redirect_field_name: redirect_url,
               'EXPNEURO_FORUM_URL': settings.EXPNEURO_FORUM_URL,
               'labcirs_config': LabCIRSConfig.objects.first()
               }
    return render(request, 'cirs/login.html', context)


def logout_user(request):
    logout(request)
    return HttpResponseRedirect(reverse_lazy('labcirs_home'))