# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2018-01-23 17:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cirs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='criticalincident',
            name='comment_code',
            field=models.CharField(blank=True, max_length=16),
        ),
    ]
