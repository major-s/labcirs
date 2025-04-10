# Copyright (C) 2016-2025 Sebastian Major
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

import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (REDIRECT_FIELD_NAME, authenticate, login,
                                 logout)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, render
from django.urls import get_script_prefix, resolve, reverse_lazy
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, FormView
from registration.backends.admin_approval.views import RegistrationView

from .forms import CommentForm, IncidentCreateForm, IncidentSearchForm
from .models import (Comment, CriticalIncident, Department, LabCIRSConfig,
                     PublishableIncident, Reporter, Reviewer)


class RedirectMixin(object):
       
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_superuser:
            return redirect('admin:index')
        elif not (hasattr(user, 'reporter') or hasattr(user, 'reviewer')):
            logout(self.request)
            redirect('login')
        return super(RedirectMixin, self).dispatch(request, *args, **kwargs)


class ContextAndRedirectMixin(RedirectMixin):
    
    def get_context_data(self, **kwargs):
        context = super(ContextAndRedirectMixin, self).get_context_data(**kwargs)
        if hasattr(self.request.user, 'reporter'):
            context['department'] = self.request.user.reporter.department.label
        else:
            context['department'] = self.kwargs['dept']
        return context

class DepartmentList(RedirectMixin, ListView):
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
            return self.request.user.reviewer.departments.filter(active=True)#all()
        else:
            return Department.objects.filter(active=True)
            #return super(DepartmentList, self).get_queryset()


class IncidentCreate(ContextAndRedirectMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = CriticalIncident
    form_class = IncidentCreateForm
    success_url = 'success'
    success_message = "%(comment_code)s"
    
    def dispatch(self, request, *args, **kwargs):
        if hasattr(self.request.user, 'reviewer'):
            return redirect('labcirs_home')
        else:
            return super(IncidentCreate, self).dispatch(request, *args, **kwargs)
    
    def get_success_message(self, cleaned_data):
        return self.success_message % dict(
            cleaned_data,
            comment_code=self.object.comment_code,
        )

    def form_valid(self, form):
        form.instance.department = self.request.user.reporter.department
        return super(IncidentCreate, self).form_valid(form)


class IncidentSearch(ContextAndRedirectMixin, LoginRequiredMixin, FormView):
    form_class = IncidentSearchForm
    template_name = 'cirs/incident_search_form.html'
    
    REDIRECT_MESSAGE = _('If you want comment on any incident, please click on the number of '
                         'comments in the last column for published incidents or use the '
                         '"View on site" link in the admin interface!')

    def dispatch(self, *args, **kwargs):
        if hasattr(self.request.user, 'reviewer'):
            messages.warning(self.request, self.REDIRECT_MESSAGE)
            return redirect('incidents_for_department', dept=self.kwargs['dept'])
        else:
            return super(IncidentSearch, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        comment_code = form.cleaned_data.get('incident_code')
        incident = CriticalIncident.objects.get(comment_code=comment_code)
        self.request.session['accessible_incident'] = incident.id
        return redirect(incident.get_absolute_url())
    

# TODO: Rename to Comment view?
class IncidentDetailView(ContextAndRedirectMixin, LoginRequiredMixin, CreateView):
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
        if hasattr(self.request.user, 'reviewer'):
            # display only if reviewer belongs to incidents department
            if context['incident'].department in self.request.user.reviewer.departments.all():
                return super(IncidentDetailView, self).render_to_response(context, **kwargs)
            else:
                return redirect('labcirs_home')
        accessible_incident_id = None
        try:
            accessible_incident_id = self.request.session['accessible_incident']
        except KeyError:
            return redirect('incident_search', dept=context['department'])
        if accessible_incident_id != context['incident'].pk:
            return redirect('incident_search', dept=context['department'])
        else:
            return super(IncidentDetailView, self).render_to_response(context, **kwargs)


class PublishableIncidentList(ContextAndRedirectMixin, LoginRequiredMixin, ListView):
    """
    Returns a simple list of publishable incidents where "publish" is set to true
    and the department matches the reporters department
    """

    def dispatch(self, *args, **kwargs):
        if hasattr(self.request.user, 'reporter'):
            if self.request.user.reporter.department.label != self.kwargs['dept']:
                messages.warning(self.request, _('You were redirected from {} to {}!').format(
                    self.kwargs['dept'], self.request.user.reporter.department.label))
                return redirect('labcirs_home')

        return super(PublishableIncidentList, self).dispatch(*args, **kwargs)
    
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
        

class RegistrationViewWithDepartment(RegistrationView):
    """
    Registers new user and new department and adds the new user as Reviewer for this new department 
    """

    def register(self, form_class):
        department = Department()
        department.label = form_class.cleaned_data['department_label']
        department.name = form_class.cleaned_data['department_name']
        reporter_name = form_class.cleaned_data['reporter_name'].lower()
        reporter_user = User.objects.create_user(reporter_name, password=reporter_name, is_active=False)
        department.reporter = Reporter.objects.create(user=reporter_user)
        department.active = False
        department.save()
        if department.pk is not None:
            new_user = super(RegistrationViewWithDepartment, self).register(form_class)
            new_user.first_name = form_class.cleaned_data['first_name']
            new_user.last_name = form_class.cleaned_data['last_name']
            # in theory not necessary, because generation of reviewer saves the user, 
            # but in case of eventual changes...
            new_user.save()
            reviewer = Reviewer.objects.create(user=new_user)
            department.reviewers.add(reviewer)
            return new_user
        else:
            # TODO: redirect to error message if department could not be saved
            return False

    def get_context_data(self, **kwargs):
        context = super(RegistrationViewWithDepartment, self).get_context_data(**kwargs)
        context['REGISTRATION_USE_TOS'] = settings.REGISTRATION_USE_TOS
        # check if language tos file exist.
        # but maybe providing default tos file might be enough?
        if settings.REGISTRATION_USE_TOS is True:
            # TODO: move to settings?
            tos_dir = os.path.join(settings.BASE_DIR, 'labcirs', 'tos')
            tos_file = 'tos_%s.html' % get_language()
            if os.path.isfile(os.path.join(tos_dir, tos_file)):
                context['tos_file'] = tos_file
            else:
                context['message'] = _('You are supposed to accept TOS but there is none provided '
                                       'in the chosen language! Try another or contact the site '
                                       'administrator!')
                context['message_class'] = 'danger'
                context['disallow_registration'] = True
        return context
        
MISSING_ROLE_MSG = _('This is a valid account, but you are neither reporter, '
                     'nor reviewer. Please contact the administrator!')

MISSING_DEPARTMENT_MSG =_('Your account has no associated department! '
                          'Please contact the administrator!')

# I would prefere to use join on <br> after translation, but lazy translation is not working this way
# and translating in advance with ugettext does not show up in the browser.
# NOT_AUTHENTICATED_MSG = '<br>'.join(
#     (ugettext('Your username and/or password were incorrect.'), 
#      ugettext('If you want to report a new incident, please check the information below!'),
#      ugettext('If you are reviewer or administrator and forgot your password, please klick')))

def login_user(request, redirect_field_name=REDIRECT_FIELD_NAME):
    # Translators: Please preserve the <br> tags for proper HTML line breaks!
    NOT_AUTHENTICATED_MSG = _('Your username and/or password were incorrect.<br>' 
        'If you want to report a new incident, please check the information below!<br>'
        'If you are reviewer or administrator and forgot your password, please klick')
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
                if user.is_superuser:
                    return redirect(redirect_url)#'admin:index')
                elif hasattr(user, 'reviewer'):
                    if user.reviewer.departments.count() > 0:
                        return redirect('admin:index')
                    else:
                        message = MISSING_DEPARTMENT_MSG
                        logout(request)
                elif hasattr(user, 'reporter'):
                    if hasattr(user.reporter, 'department'):
                        return redirect('incidents_for_department', 
                                        dept=user.reporter.department.label)
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
            reset_link = '<a href="{}">{}.</a>'.format(reverse_lazy('auth_password_reset'), _('here'))
            message = NOT_AUTHENTICATED_MSG + " " + reset_link

    context = {'message': message,
               'message_class': message_class,
               'username': username,
               redirect_field_name: redirect_url,
               }
    
    try:
        # Resolve seems not to work if django project is not run from web root.
        prefix = get_script_prefix()
        match = resolve(redirect_url.replace(prefix, '/'))
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
    return redirect('labcirs_home')
