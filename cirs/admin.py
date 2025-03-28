# -*- coding: utf-8 -*-
#
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

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db import models
from django.forms import TextInput, Textarea
from django.utils.translation import gettext_lazy as _

from parler.admin import TranslatableAdmin, TranslatableTabularInline
from registration.admin import RegistrationAdmin, RegistrationProfile

from cirs.models import (Comment, CriticalIncident, PublishableIncident, 
                         LabCIRSConfig, Department, Reporter, Reviewer)


class LabCIRSAdminSite(admin.AdminSite):
    site_header = _('LabCIRS for %s') % settings.ORGANIZATION
    # Translators: This message appears in the page title
    site_title = 'LabCIRS'
    index_title = _('LabCIRS administration')
    
    
admin_site = LabCIRSAdminSite()


class LabCIRSUserAdmin(UserAdmin):
    '''Local UserAdmin class to allow reviewers changing of reporter user data'''
    
    def get_queryset(self, request):
        qs = super(LabCIRSUserAdmin, self).get_queryset(request)
        try: 
            return qs.filter(
                reporter__in=Reporter.objects.filter(
                    department__in=request.user.reviewer.departments.all()))
        except Reviewer.DoesNotExist:
            if request.user.is_superuser is True:
                return qs

    def get_fieldsets(self, request, obj=None):
        # Reviewer can modify only names and change the password
        if hasattr(request.user, 'reviewer'):
            return ((None, {'fields': ('username', 'password')}),
                    (u'_(Personal info)', {'fields': ('first_name', 'last_name')}))
        else:
            return super(LabCIRSUserAdmin, self).get_fieldsets(request, obj=obj)

class HasPublishableIncidentListFilter(admin.SimpleListFilter):
    title = _('has publishable incident')
    parameter_name = 'has_publishable_incident'

    def lookups(self, request, model_admin):
        return (
            ('1', _('Yes')),
            ('0', _('No')),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.exclude(publishableincident=None)
        if self.value() == '0':
            return queryset.filter(publishableincident=None)

common_pi_fields = (
    ('incident', 'description', 'measures_and_consequences')
    )

pi_form_overrides = {
    models.CharField: {'widget': TextInput(attrs={'size': '62'})},
    models.TextField: {'widget': Textarea(attrs={'rows': 6, 'cols': 60})},
    }


class PublishableIncidentInline(TranslatableTabularInline):
    model = PublishableIncident
    fields = common_pi_fields + ('publish', 'translation_info')
    formfield_overrides = pi_form_overrides
    readonly_fields = ('translation_info', )


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('author', 'text',)
    
    def has_add_permission(self, request, *args, **kwargs):
        # TODO: write tests. Reviewer should not add comments in the admin inline view
        return False

class CriticalIncidentAdmin(admin.ModelAdmin):
    readonly_fields = ('date', 'incident', 'reason', 'immediate_action',
                       'public', 'reported', 'preventability', 'photo',
                       'photo_tag')
    list_filter = ('department', 'status', 'date', 'reported', 'public', 'risk',
                   HasPublishableIncidentListFilter)
    list_display = ('incident', 'date', 'reported', 'status', 'risk')
    list_display_links = ('incident', 'status', 'risk')
    fieldsets = (
        (_('Reported incident'), {
            'fields': (('date', 'reported'), 'public', 'incident', 'reason',
                       'immediate_action', 'preventability', 'photo',
                       'photo_tag')
            
        }),
        (_('Review'), {
            'fields': (('review_date', 'status'),
                       ('risk', 'frequency', 'hazard'),
                       'responsibilty', 'action', 'category'),
            'classes': ['collapse',]
        })
    )
    inlines = [PublishableIncidentInline, CommentInline]

    def get_formsets(self, request, obj=None):
        for inline in self.get_inline_instances(request, obj):
            # hide PublishableIncidentInline in the add view
            if isinstance(inline, PublishableIncidentInline) and obj.public is False:
                continue
            yield inline.get_formset(request, obj)
            
    def get_queryset(self, request):
        qs = super(CriticalIncidentAdmin, self).get_queryset(request)
        try:
            return qs.filter(department__in=request.user.reviewer.departments.all())
        except Reviewer.DoesNotExist:
            return qs.none()

class PublishableIncidentAdmin(TranslatableAdmin):

    fields = (('critical_incident', 'publish', 'translation_info'),) + common_pi_fields
    list_filter = ('publish', )
    list_display = ('incident', 'critical_incident', 'translation_status')
    list_display_links = ('incident', )
    readonly_fields = ('translation_info', )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "critical_incident":
            kwargs["queryset"] = CriticalIncident.objects.filter(public=True).filter(publishableincident=None).exclude(status='new')
        return super(PublishableIncidentAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj:
            readonly_fields.extend(['critical_incident'])
        return readonly_fields

    formfield_overrides = pi_form_overrides
    
    def get_queryset(self, request):
        qs = super(PublishableIncidentAdmin, self).get_queryset(request)
        try:
            return qs.filter(
                critical_incident__department__in=request.user.reviewer.departments.all())
        except Reviewer.DoesNotExist:
            return qs.none()


class AdminObjectMixin(object):
    
    def get_form(self, request, obj=None, **kwargs):
        self.model_instance = None
        if obj:
            self.model_instance = obj
           
        return super(AdminObjectMixin, self).get_form(request, obj, **kwargs)


class ConfigurationAdmin(AdminObjectMixin, TranslatableAdmin):
    
    list_display = ('__str__', 'translation_status')
    filter_horizontal = ('notification_recipients',)
    fieldsets = (
        (_('Languages'), {
            'fields': ('mandatory_languages', 'translation_info')
        }),
        (_('Login infos - translate "login info" and "link text" if using multiple languages!'), {
            'fields': ('login_info', 'login_info_url', 'login_info_link_text')
        }),
        (_('Notification settings'), {
            'fields': (('send_notification', 'notification_sender_email'),
                       'notification_text', 'notification_recipients')
        })
    )
    readonly_fields = ('translation_info', )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # If by chance someone creates config in admin manually, the list will be empty!
        if db_field.name == "notification_recipients":
            kwargs["queryset"] = User.objects.filter(reviewer__in=self.model_instance.department.reviewers.all())
        return super(ConfigurationAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super(ConfigurationAdmin, self).get_queryset(request)
        try:
            return qs.filter(
                department__in=request.user.reviewer.departments.all())
        except Reviewer.DoesNotExist:
            if request.user.is_superuser is True:
                return qs


class DepartmentAdmin(AdminObjectMixin, admin.ModelAdmin):
    filter_horizontal = ('reviewers',)
       
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "reporter":
            kwargs["queryset"] = (Reporter.objects.filter(department=None) 
                                  | Reporter.objects.filter(department=self.model_instance))
        return super(DepartmentAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class RoleAdmin(AdminObjectMixin, admin.ModelAdmin):

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            queryset = User.objects.filter(is_superuser=False, reporter=None, reviewer=None)
            assigned_user = User.objects.none()
            # add assigned user if existing object is provided
            if self.model_instance:
                assigned_user =  User.objects.filter(**{self.model._meta.model_name: self.model_instance})
            kwargs["queryset"] = queryset | assigned_user
            
        return super(RoleAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


admin_site.register(User, LabCIRSUserAdmin)
admin_site.register(CriticalIncident, CriticalIncidentAdmin)
admin_site.register(PublishableIncident, PublishableIncidentAdmin)
admin_site.register(LabCIRSConfig, ConfigurationAdmin)
admin_site.register(Department, DepartmentAdmin)
admin_site.register(Reporter, RoleAdmin)
admin_site.register(Reviewer, RoleAdmin)
admin_site.register(RegistrationProfile, RegistrationAdmin)
