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

from django.contrib import admin
from django.contrib.auth.models import User
from django.db import models
from django.forms import TextInput, Textarea
from django.utils.translation import ugettext_lazy as _

from cirs.models import (Comment, CriticalIncident, PublishableIncident, 
                         LabCIRSConfig, Organization, Reporter, Reviewer)


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
    ('incident_de', 'incident_en'), ('description_de', 'description_en'),
    ('measures_and_consequences_de', 'measures_and_consequences_en')
    )

pi_form_overrides = {
    models.CharField: {'widget': TextInput(attrs={'size': '62'})},
    models.TextField: {'widget': Textarea(attrs={'rows': 6, 'cols': 60})},
    }


class PublishableIncidentInline(admin.StackedInline):
    model = PublishableIncident
    fields = common_pi_fields + ('publish', )
    formfield_overrides = pi_form_overrides


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('author', 'text',)
    
    def has_add_permission(self, request):
        return False

class CriticalIncidentAdmin(admin.ModelAdmin):
    readonly_fields = ('date', 'incident', 'reason', 'immediate_action',
                       'public', 'reported', 'preventability', 'photo',
                       'photo_tag')
    list_filter = ('status', 'date', 'reported', 'public', 'risk',
                   HasPublishableIncidentListFilter)
    list_display = ('incident', 'date', 'reported', 'status', 'risk')
    list_display_links = ('incident', 'status', 'risk')
    fieldsets = (
        ('Reported incident', {
            'fields': (('date', 'reported'), 'public', 'incident', 'reason',
                       'immediate_action', 'preventability', 'photo',
                       'photo_tag')
        }),
        ('Review', {
            'fields': (('review_date', 'status'),
                       ('risk', 'frequency', 'hazard'),
                       'responsibilty', 'action', 'category')
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
            return qs.filter(organization__in=request.user.reviewer.organizations.all())
        except Reviewer.DoesNotExist:
            return qs.none()

class PublishableIncidentAdmin(admin.ModelAdmin):

    fields = (('critical_incident', 'publish'),) + common_pi_fields
    list_filter = ('publish',)
    list_display = ('incident_de', 'incident_en', 'critical_incident')
    list_display_links = ('incident_de', 'incident_en')

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
                critical_incident__organization__in=request.user.reviewer.organizations.all())
        except Reviewer.DoesNotExist:
            return qs.none()


class ConfigurationAdmin(admin.ModelAdmin):
    filter_horizontal = ('notification_recipients',)
    fieldsets = (
        (_('Login infos'), {
            'fields': ('login_info_en', 'login_info_de', 'login_info_url',
                       'login_info_link_text_en', 'login_info_link_text_de'
                       )
        }),
        (_('Notification settings'), {
            'fields': (('send_notification', 'notification_sender_email'),
                       'notification_text', 'notification_recipients')
        })
    )


class AdminWithObject(admin.ModelAdmin):
    
    def get_form(self, request, obj=None, **kwargs):
        self.model_instance = None
        if obj:
            self.model_instance = obj
           
        return super(AdminWithObject, self).get_form(request, obj, **kwargs)


class OrganizationAdmin(AdminWithObject):
    filter_horizontal = ('reviewers',)
       
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "reporter":
            kwargs["queryset"] = (Reporter.objects.filter(organization=None) 
                                  | Reporter.objects.filter(organization=self.model_instance))
        return super(OrganizationAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class RoleAdmin(AdminWithObject):

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            queryset = User.objects.filter(is_superuser=False, reporter=None, reviewer=None)
            assigned_user = User.objects.none()
            # add assigned user if existing object is provided
            if self.model_instance:
                assigned_user =  User.objects.filter(**{self.model._meta.model_name: self.model_instance})
            kwargs["queryset"] = queryset | assigned_user
            
        return super(RoleAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(CriticalIncident, CriticalIncidentAdmin)
admin.site.register(PublishableIncident, PublishableIncidentAdmin)
admin.site.register(LabCIRSConfig, ConfigurationAdmin)
admin.site.register(Comment)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Reporter, RoleAdmin)
admin.site.register(Reviewer, RoleAdmin)
