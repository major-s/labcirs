# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Sebastian Major
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

from __future__ import unicode_literals

from model_mommy.recipe import Recipe, seq
from .models import CriticalIncident, PublishableIncident, Reviewer, Reporter
from cirs.models import Department

REPORTER_NAME = 'rep'

public_ci = Recipe(CriticalIncident,
    incident = seq('Critical Incident '),
    public = True
)

published_incident = Recipe(PublishableIncident,
    incident_de = seq('Published Incident '),
    publish = True,
    critical_incident__public = True,
    critical_incident__department__label = seq('Dept_'),
    critical_incident__department__reporter__user__username = seq(REPORTER_NAME),
)

reviewer = Recipe(Reviewer,
    user__username = seq('rev'),
    user__email = seq('rev@localhost'),
)

reporter = Recipe(Reporter,
    user__username = seq(REPORTER_NAME))

department = Recipe(Department,
    label = seq('Dept_'),
    reporter__user__username = seq(REPORTER_NAME)
)