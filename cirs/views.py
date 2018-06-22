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
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core import mail
from django.core.urlresolvers import reverse_lazy
from django import forms
from django.forms import ModelForm, Textarea, TextInput, RadioSelect
from django.forms.utils import ErrorList
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, FormView

from .models import CriticalIncident, Comment, PublishableIncident, LabCIRSConfig


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


class CommentForm(ModelForm):
    
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {"text": Textarea(attrs={'cols': 80, 'rows': 5, 
                                           'class': "form-control"})
        }

    def save(self):
        result = super(CommentForm, self).save()
        config = LabCIRSConfig.objects.first()
        if config.send_notification:
            # send only if incident was saved
            if self.instance.pk is not None:
                try:
                    # TODO: add comment notification
                    mail_body = config.notification_text
                except:
                    mail_body = ""
                to_list = []
                for user in config.notification_recipients.all().exclude(id=self.instance.author.id):
                    to_list.append(user.email)
                mail.send_mail('New LabCIRS comment', mail_body,
                               config.notification_sender_email,
                               to_list, fail_silently=False)
        return result


class IncidentCreate(SuccessMessageMixin, CreateView):
    model = CriticalIncident
    form_class = IncidentCreateForm
    success_url = 'success'
    success_message = "%(comment_code)s"

    @method_decorator(permission_required('cirs.add_criticalincident'))
    def dispatch(self, *args, **kwargs):
        return super(IncidentCreate, self).dispatch(*args, **kwargs)
    
    def get_success_message(self, cleaned_data):
        return self.success_message % dict(
            cleaned_data,
            comment_code=self.object.comment_code,
        )


class IncidentSearchForm(forms.Form):
    incident_code = forms.CharField()


class IncidentSearch(LoginRequiredMixin, FormView):
    form_class = IncidentSearchForm
    template_name = 'cirs/incident_search_form.html'

    def form_valid(self, form):
        comment_code = form.cleaned_data.get('incident_code')
        # TODO: handle nonexistend codes
        incident_id = CriticalIncident.objects.get(comment_code=comment_code).id
        self.request.session['accessible_incident'] = incident_id
        return redirect('incident_detail', pk=incident_id)


class IncidentDetailView(LoginRequiredMixin, CreateView):
    """
    Delivers detail view of an incident for commenting. Simple form for comments
    is included and followed by a list of comments for this incident
    """
    model = Comment
    form_class = CommentForm
    template_name = 'cirs/criticalincident_detail.html'

    def get_success_url(self):
        # returns the absolute URL of the parent (and current incident)
        return CriticalIncident.objects.get(pk=self.kwargs['pk']).get_absolute_url()
  
    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.critical_incident = CriticalIncident.objects.get(pk=self.kwargs['pk'])
        return super(IncidentDetailView, self).form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super(IncidentDetailView, self).get_context_data(**kwargs)
        context['incident'] = CriticalIncident.objects.get(pk=self.kwargs['pk'])
        return context

    def render_to_response(self, context, **kwargs):
        if self.request.user.has_perm('cirs.change_criticalincident'):
            return super(IncidentDetailView, self).render_to_response(context, **kwargs)
        accessible_incident_id = None
        try:
            accessible_incident_id = self.request.session['accessible_incident']
        except KeyError as e:
            return redirect('incident_search')
        if accessible_incident_id != context['incident'].pk:
            return redirect('incident_search')
        else:
            return super(IncidentDetailView, self).render_to_response(context, **kwargs)


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
               'labcirs_config': LabCIRSConfig.objects.first()
               }
    return render(request, 'cirs/login.html', context)


def logout_user(request):
    logout(request)
    return HttpResponseRedirect(reverse_lazy('labcirs_home'))