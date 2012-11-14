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
    Form,
    FormRenderer,
    )
from samplesdb.validators import (
    FormSchema,
    SubFormSchema,
    ValidCollection,
    ValidMarkupLanguage,
    ValidSampleDescription,
    ValidSampleLocation,
    ValidSampleNotes,
    ValidLogMessage,
    ValidCodeName,
    ValidCodeValue,
    )
from samplesdb.security import (
    VIEW_COLLECTION,
    EDIT_COLLECTION,
    )
from samplesdb.models import (
    DBSession,
    Sample,
    SampleLogEntry,
    )


class SampleLogEntrySchema(SubFormSchema):
    message = ValidLogMessage()


class SampleLogEntryCreateSchema(SampleLogEntrySchema):
    pass


class SampleCodeSchema(SubFormSchema):
    name = ValidCodeName()
    value = ValidCodeValue()


class SampleSchema(FormSchema):
    collection = ValidCollection()
    description = ValidSampleDescription()
    location = ValidSampleLocation()
    notes_markup = ValidMarkupLanguage()
    notes = ValidSampleNotes()
    sample_codes = foreach.ForEach(SampleCodeSchema())


class SampleCreateSchema(SampleSchema):
    pass


class SampleEditSchema(SampleSchema):
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
        form = Form(
            self.request,
            schema=SampleCreateSchema,
            variable_decode=True,
            multipart=True)
        if form.validate():
            print(form.data)
            new_sample = form.bind(
                Sample.create(self.request.user, self.context.collection))
            DBSession.add(new_sample)
            DBSession.flush()
            for storage in self.request.POST.getall('attachments'):
                if storage:
                    new_sample.attachments.create(storage.filename, storage.file)
            return HTTPFound(
                location=self.request.route_url(
                    'samples_view', sample_id=new_sample.id))
        return dict(form=FormRenderer(form))

    @view_config(
        route_name='samples_edit',
        renderer='../templates/samples/edit.pt',
        permission=EDIT_COLLECTION)
    def edit(self):
        sample = self.context.sample
        form = Form(
            self.request,
            schema=SampleEditSchema,
            obj=sample,
            variable_decode=True)
        if form.validate():
            form.bind(sample)
            return HTTPFound(
                location=self.request.route_url(
                    'samples_view', sample_id=sample.id))
        return dict(form=FormRenderer(form))

    @view_config(
        route_name='samples_view',
        renderer='../templates/samples/view.pt',
        permission=VIEW_COLLECTION)
    def view(self):
        return dict(
            log_form=FormRenderer(Form(self.request, schema=SampleLogEntryCreateSchema)),
            attachment_form=FormRenderer(Form(self.request, multipart=True)),
            )

    @view_config(
        route_name='samples_add_attachment',
        permission=EDIT_COLLECTION)
    def add_attachment(self):
        for storage in self.request.POST.getall('attachments'):
            self.context.sample.attachments.create(storage.filename, storage.file)
        return HTTPFound(
            location=self.request.route_url(
                'samples_view',
                sample_id=self.context.sample.id,
                _anchor='attachments'))

    @view_config(
        route_name='samples_remove_attachment',
        permission=EDIT_COLLECTION)
    def remove_attachment(self):
        for filename in self.request.params.getall('attachments'):
            self.context.sample.attachments.remove(filename)
        return HTTPFound(
            location=self.request.route_url(
                'samples_view',
                sample_id=self.context.sample.id,
                _anchor='attachments'))

    @view_config(
        route_name='samples_default_attachment',
        permission=EDIT_COLLECTION)
    def default_attachment(self):
        self.context.sample.default_attachment = self.request.params.get('attachment')
        return HTTPFound(
            location=self.request.route_url(
                'samples_view',
                sample_id=self.context.sample.id,
                _anchor='attachments'))

    @view_config(
        route_name='samples_attachment_thumb',
        permission=VIEW_COLLECTION)
    def attachment_thumb(self):
        response = self.request.response
        response.content_type = self.context.sample.attachments.thumb_mime_type(
                self.request.matchdict['attachment'])
        response.app_iter = self.context.sample.attachments.thumb_open(
                self.request.matchdict['attachment'])
        return response

    @view_config(
        route_name='samples_add_log',
        permission=EDIT_COLLECTION)
    def add_log(self):
        form = Form(self.request, schema=SampleLogEntryCreateSchema)
        if form.validate():
            new_log_entry = form.bind(SampleLogEntry(creator=self.request.user))
            self.context.sample.log.append(new_log_entry)
        return HTTPFound(
            location=self.request.route_url(
                'samples_view',
                sample_id=self.context.sample.id,
                _anchor='log'))

