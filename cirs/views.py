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

from django.contrib.auth import REDIRECT_FIELD_NAME, authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import resolve
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, FormView

from .forms import  IncidentCreateForm, IncidentSearchForm, CommentForm    
from .models import CriticalIncident, Comment, PublishableIncident, LabCIRSConfig, Department

import traceback

class DepartmentList(ListView):
    model = Department
    
    def dispatch(self, *args, **kwargs):
        if hasattr(self.request.user, 'reporter'):
            dept = self.request.user.reporter.department
            return redirect('incidents_for_department', dept=dept.label)
        elif hasattr(self.request.user, 'reviewer'):
            if self.request.user.reviewer.departments.count() == 1:
                dept = self.request.user.reviewer.departments.get()
                return redirect('incidents_for_department', dept=dept.label)
            else:
                return super(DepartmentList, self).dispatch(*args, **kwargs)
        else:
            return super(DepartmentList, self).dispatch(*args, **kwargs)
        
    def get_queryset(self):
        if hasattr(self.request.user, 'reviewer'):
            return self.request.user.reviewer.departments.all()
        else:
            return super(DepartmentList, self).get_queryset()


class IncidentCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = CriticalIncident
    form_class = IncidentCreateForm
    success_url = 'success'
    success_message = "%(comment_code)s"

    def dispatch(self, *args, **kwargs):
        if hasattr(self.request.user, 'reporter'):
            return super(IncidentCreate, self).dispatch(*args, **kwargs)
        elif hasattr(self.request.user, 'reviewer'):
            return HttpResponseRedirect(reverse_lazy('labcirs_home'))
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
        form.instance.department = self.request.user.reporter.department
        return super(IncidentCreate, self).form_valid(form)


class IncidentSearch(LoginRequiredMixin, FormView):
    form_class = IncidentSearchForm
    template_name = 'cirs/incident_search_form.html'

    def form_valid(self, form):
        comment_code = form.cleaned_data.get('incident_code')
        incident_id = CriticalIncident.objects.get(comment_code=comment_code).id
        self.request.session['accessible_incident'] = incident_id
        return redirect('incident_detail', pk=incident_id)

# TODO: Rename to Comment view?
class IncidentDetailView(LoginRequiredMixin, CreateView):
    """
    Delivers detail view of an incident for commenting. Simple form for comments
    is included and followed by a list of comments for this incident
    """
    model = Comment
    form_class = CommentForm
    template_name = 'cirs/criticalincident_detail.html'

    def dispatch(self, *args, **kwargs):
        if self.request.user.is_superuser:
            return redirect('admin:index')
        else:
            return super(IncidentDetailView, self).dispatch(*args, **kwargs)
    
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
        if hasattr(self.request.user, 'reviewer'):
            if context['incident'].department in self.request.user.reviewer.departments.all():
                return super(IncidentDetailView, self).render_to_response(context, **kwargs)
            else:
                return redirect('labcirs_home')
        accessible_incident_id = None
        try:
            accessible_incident_id = self.request.session['accessible_incident']
        except KeyError:
            return redirect('incident_search')
        if accessible_incident_id != context['incident'].pk:
            return redirect('incident_search')
        else:
            return super(IncidentDetailView, self).render_to_response(context, **kwargs)


class PublishableIncidentList(LoginRequiredMixin, ListView):
    """
    Returns a simple list of publishable incidents where "publish" is set to true
    and the department matches the reporters department
    """
    
    def dispatch(self, *args, **kwargs):
        if hasattr(self.request.user, 'reporter'):
            if self.request.user.reporter.department.label != self.kwargs['dept']:
                return redirect('labcirs_home')

        return super(PublishableIncidentList, self).dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super(PublishableIncidentList, self).get_context_data(**kwargs)
        try:
            context['department'] = self.kwargs['dept']
        except KeyError:
            pass
            # TODO: handle it
            #print e
            #traceback.print_exc()
        return context
    
    def get_queryset(self):
        if hasattr(self.request.user, 'reporter'):
            return PublishableIncident.objects.filter(publish=True,
                critical_incident__department=self.request.user.reporter.department)
        elif hasattr(self.request.user, 'reviewer'):

            qs =  PublishableIncident.objects.filter(publish=True,
                critical_incident__department__in=self.request.user.reviewer.departments.filter(
                    label=self.kwargs['dept']
                    ))
            return qs
        else:
            return PublishableIncident.objects.none()

MISSING_ROLE_MSG = _('This is a valid account, but you are neither reporter, '
                     'nor reviewer. Please contact the administrator!')

MISSING_DEPARTMENT_MSG =_('Your account has no associated department! '
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
                    if user.reviewer.departments.count() > 0:
                        return HttpResponseRedirect(reverse_lazy('admin:index'))
                    else:
                        message = MISSING_DEPARTMENT_MSG
                        logout(request)
                elif hasattr(user, 'reporter'):
                    if hasattr(user.reporter, 'department'):
                        #return dept = self.request.user.reporter.department
                        return redirect('incidents_for_department', 
                                        dept=user.reporter.department.label)
                        #return HttpResponseRedirect(redirect_url)
                        
                    else:
                        message = MISSING_DEPARTMENT_MSG
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
               }
    
    try:
        match = resolve(redirect_url)
        context['department'] = match.kwargs['dept']
        context['labcirs_config'] = LabCIRSConfig.objects.get(
            department__label=match.kwargs['dept'])
    except Exception as e:
        pass
        #print e
        #traceback.print_exc()
    return render(request, 'cirs/login.html', context)


def logout_user(request):
    logout(request)
    return HttpResponseRedirect(reverse_lazy('labcirs_home'))