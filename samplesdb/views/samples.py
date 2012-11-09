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

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from formencode import validators, foreach

from samplesdb.views import BaseView
from samplesdb.forms import (
    BaseSchema,
    Form,
    FormRenderer,
    ValidCollection,
    ValidSampleDescription,
    ValidSampleLocation,
    ValidSampleNotes,
    )
from samplesdb.security import (
    VIEW_COLLECTION,
    EDIT_COLLECTION,
    )
from samplesdb.models import (
    DBSession,
    Sample,
    )


class SampleSchema(BaseSchema):
    collection = ValidCollection()
    description = ValidSampleDescription()
    location = ValidSampleLocation()
    notes = ValidSampleNotes()


class SampleCreateSchema(SampleSchema):
    pass


class SamplesView(BaseView):
    """Handlers for sample related views"""

    def __init__(self, request):
        self.request = request

    @view_config(
        route_name='samples_view',
        renderer='../templates/samples/view.pt',
        permission=VIEW_COLLECTION)
    def view(self):
        filter = self.request.params.get('filter', 'existing')
        # XXX Construct a query instead (better performance than retrieving
        # everything and doing filtering in Python)
        samples = (
            sample
            for sample in self.request.context.collection.all_samples
            if filter == 'all'
            or (filter == 'existing' and not sample.destroyed)
            or (filter == 'destroyed' and sample.destroyed))
        return dict(filter=filter, samples=samples)

