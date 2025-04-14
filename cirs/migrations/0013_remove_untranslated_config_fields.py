# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-29 22:12
from __future__ import unicode_literals

from django.db import migrations
from django.db import models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ('cirs', '0012_migrate_translatable_config_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='labcirsconfig',
            name='login_info_de',
            field=models.TextField(_('Login info (in German)'), default=' '),
            preserve_default=True,
        ),
        migrations.RemoveField(
            model_name='labcirsconfig',
            name='login_info_de',
        ),
        migrations.AlterField(
            model_name='labcirsconfig',
            name='login_info_en',
            field=models.TextField(_('Login info (in English)'), default=' '),
            preserve_default=True,
        ),
        migrations.RemoveField(
            model_name='labcirsconfig',
            name='login_info_en',
        ),
        migrations.RemoveField(
            model_name='labcirsconfig',
            name='login_info_link_text_de',
        ),
        migrations.RemoveField(
            model_name='labcirsconfig',
            name='login_info_link_text_en',
        ),
    ]
