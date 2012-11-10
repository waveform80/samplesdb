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
from formencode import foreach

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

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(
        route_name='samples_create',
        renderer='../templates/samples/create.pt',
        permission=EDIT_COLLECTION)
    def create(self):
        form = Form(self.request, schema=SampleCreateSchema)
        if form.validate():
            new_sample = form.bind(
                Sample.create(self.request.user, self.context.collection))
            DBSession.add(new_sample)
            DBSession.flush()
            return HTTPFound(
                location=self.request.route_url(
                    'samples_view', sample_id=new_sample.id))
        else:
            print(repr(form.data))
            print(repr(form.errors))
        return dict(form=FormRenderer(form))

    @view_config(
        route_name='samples_view',
        renderer='../templates/samples/view.pt',
        permission=VIEW_COLLECTION)
    def view(self):
        return {}

