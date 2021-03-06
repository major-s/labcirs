# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-09-14 09:31
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cirs', '0004_auto_20180628_1403'),
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.SlugField(help_text='Label can only consist of letters, numbers, underscores and hyphens.', max_length=32, unique=True, verbose_name='Label')),
                ('name', models.CharField(max_length=255, unique=True, verbose_name='Name')),
            ],
            options={
                'verbose_name': 'Department',
                'verbose_name_plural': 'Departments',
            },
        ),
        migrations.CreateModel(
            name='Reporter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.OneToOneField(help_text='User assigned to other roles and superusers are not listed here!', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Reporter',
                'verbose_name_plural': 'Reporters',
            },
        ),
        migrations.CreateModel(
            name='Reviewer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.OneToOneField(help_text='User assigned to other roles and superusers are not listed here!', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Reviewer',
                'verbose_name_plural': 'Reviewers',
            },
        ),
        migrations.AddField(
            model_name='department',
            name='reporter',
            field=models.OneToOneField(help_text='Reporters assigned to other departments are not listed here!', on_delete=django.db.models.deletion.PROTECT, to='cirs.Reporter', verbose_name='Reporter'),
        ),
        migrations.AddField(
            model_name='department',
            name='reviewers',
            field=models.ManyToManyField(related_name='departments', to='cirs.Reviewer', verbose_name='Reviewers'),
        ),
    ]
