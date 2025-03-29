# Copyright (C) 2018-2024 Sebastian Major
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

from django.contrib.auth.models import User, Permission

from cirs.models import Reporter, Reviewer


def create_user(name=None, superuser=False):
    if superuser is True:
        user = User.objects.create_superuser(name, '%s@localhost' % name, name)
    else:
        user = User.objects.create_user(name, '%s@localhost' % name, name)
    return user

def create_role(role_cls, name):
    if (role_cls != Reporter) and (role_cls != Reviewer):
        raise TypeError('This function can be used with Reporter or Reviewer '
                        'models only. Instead {} was used!'.format(role_cls))
    if type(name) == str:
        role = role_cls.objects.create(user=create_user(name))
    elif type(name) == User:
        role = role_cls.objects.create(user=name)
    else:
        raise TypeError('You have to proviede either a name for new user or an '
                        'existing user. But you provided {} which is '
                        '{}!'.format(name, type(name)))
    return role


def create_user_with_perm(name, codename):
    user = create_user(name)
    permission = Permission.objects.get(codename=codename)
    user.user_permissions.add(permission)
    return user