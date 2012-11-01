# -*- coding: utf-8 -*-
# vim: set et sw=4 sts=4:

# Copyright 2012 Dave Hughes.
#
# This file is part of samplesdb.
#
# samplesdb is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# samplesdb is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# samplesdb.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import transaction
from pyramid.view import view_config
from formencode import validators

from samplesdb.views import BaseView
from samplesdb.forms import BaseSchema, Form, FormRenderer
from samplesdb.models import Collection, Sample

class CollectionsView(BaseView):
    """Handler for collection related views"""

    @view_config(route_name='collections_index', renderer='../templates/collections/index.pt')
    def index(self):
        return {}
