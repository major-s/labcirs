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

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME, authenticate, login, logout
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, FormView

from .forms import  IncidentCreateForm, IncidentSearchForm, CommentForm    
from .models import CriticalIncident, Comment, PublishableIncident, LabCIRSConfig


class IncidentCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = CriticalIncident
    form_class = IncidentCreateForm
    success_url = 'success'
    success_message = "%(comment_code)s"

    #@method_decorator(permission_required('cirs.add_criticalincident'))
    def dispatch(self, *args, **kwargs):
        if hasattr(self.request.user, 'reporter'):
            return super(IncidentCreate, self).dispatch(*args, **kwargs)
        elif hasattr(self.request.user, 'reviewer'):
            return HttpResponseRedirect(reverse_lazy('incidents_list'))
        elif self.request.user.is_superuser:
            return HttpResponseRedirect(reverse_lazy('admin:index'))
        else:
            logout(self.request)
            return HttpResponseRedirect(reverse_lazy('login'))
    
    def get_success_message(self, cleaned_data):
        return self.success_message % dict(
            cleaned_data,
            comment_code=self.object.comment_code,
        )

    def form_valid(self, form):
        form.instance.organization = self.request.user.reporter.organization
        return super(IncidentCreate, self).form_valid(form)


class IncidentSearch(LoginRequiredMixin, FormView):
    form_class = IncidentSearchForm
    template_name = 'cirs/incident_search_form.html'

    def form_valid(self, form):
        comment_code = form.cleaned_data.get('incident_code')
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


class PublishableIncidentList(LoginRequiredMixin, ListView):
    """
    Returns a simple list of publishable incidents where "publish" is set to true
    and the organization matches the reporters organization
    """
    def get_queryset(self):
        if hasattr(self.request.user, 'reporter'):
            return PublishableIncident.objects.filter(publish=True,
                critical_incident__organization=self.request.user.reporter.organization)
        elif hasattr(self.request.user, 'reviewer'):
            return PublishableIncident.objects.filter(publish=True,
                critical_incident__organization__in=self.request.user.reviewer.organizations.all())
        else:
            return PublishableIncident.objects.none()

MISSING_ROLE_MSG = _('This is a valid account, but you are neither reporter, '
                     'nor reviewer. Please contact the administrator!')

MISSING_ORGANIZATION_MSG =_('Your account has no associated organization! '
                            'Please contact the administrator!')

def login_user(request, redirect_field_name=REDIRECT_FIELD_NAME):
    username = password = message = ''
    message_class = 'danger'
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
                # Done here but other views are also important!
                if user.is_superuser:
                    return HttpResponseRedirect(reverse_lazy('admin:index'))
                elif hasattr(user, 'reviewer'):
                    if user.reviewer.organizations.count() > 0:
                        return HttpResponseRedirect(reverse_lazy('admin:index'))
                    else:
                        message = MISSING_ORGANIZATION_MSG
                        logout(request)
                elif hasattr(user, 'reporter'):
                    if hasattr(user.reporter, 'organization'):
                        return HttpResponseRedirect(redirect_url)
                    else:
                        message = MISSING_ORGANIZATION_MSG
                        logout(request)
                else:
                    message = MISSING_ROLE_MSG
                    logout(request)
            else:
                message = _('Your account is not active, please contact the admin.')
                message_class = 'warning'
        else:
            message = _("""Your username and/or password were incorrect.
                        Please check the information below!""")

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