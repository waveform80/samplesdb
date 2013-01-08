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

from samplesdb.views import BaseView
from samplesdb.forms import (
    Form,
    FormRenderer,
    )
from samplesdb.validators import (
    FormSchema,
    SubFormSchema,
    ForEachDict,
    ValidCollection,
    ValidMarkupLanguage,
    ValidSampleDescription,
    ValidSampleLocation,
    ValidSampleNotes,
    ValidSampleAliquots,
    ValidSampleAliquant,
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
    codes = ForEachDict(SampleCodeSchema(),
                key_name='name', value_name='value')


class SampleCreateSchema(SampleSchema):
    pass


class SampleEditSchema(SampleSchema):
    pass


class SampleDestroySchema(FormSchema):
    reason = ValidLogMessage()

class SampleSplitSchema(FormSchema):
    collection = ValidCollection()
    location = ValidSampleLocation()
    aliquots = ValidSampleAliquots()
    aliquant = ValidSampleAliquant()


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
            # XXX Check for EDIT_COLLECTION on selected collection
            # XXX Should be using form collection below
            new_sample = form.bind(
                Sample.create(self.request.user, self.context.collection))
            for storage in self.request.POST.getall('attachments'):
                if storage:
                    new_sample.attachments.create(storage.filename, storage.file)
            return HTTPFound(
                location=self.request.route_url(
                    'samples_view', sample_id=new_sample.id))
        return dict(form=FormRenderer(form))

    @view_config(
        route_name='samples_destroy',
        renderer='../templates/samples/destroy.pt',
        permission=EDIT_COLLECTION)
    def destroy(self):
        form = Form(
            self.request,
            defaults=dict(reason='Sample destroyed'),
            schema=SampleDestroySchema)
        if form.validate():
            self.context.sample.destroy(self.request.user, form.data['reason'])
            return HTTPFound(
                location=self.request.route_url(
                    'samples_view', sample_id=self.context.sample.id))
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
            # XXX Check for EDIT_COLLECTION on new collection
            form.bind(sample)
            return HTTPFound(
                location=self.request.route_url(
                    'samples_view', sample_id=sample.id))
        return dict(form=FormRenderer(form))

    @view_config(
        route_name='samples_split',
        renderer='../templates/samples/split.pt',
        permission=EDIT_COLLECTION)
    def split(self):
        sample = self.context.sample
        form = Form(
            self.request,
            schema=SampleSplitSchema,
            obj=sample,
            defaults=dict(aliquots=2),
            variable_decode=True)
        if form.validate():
            # XXX Check for EDIT_COLLECTION on new collection
            aliquots = sample.split(
                self.request.user, form.data['collection'],
                form.data['aliquots'], form.data['aliquant'],
                location=form.data['location'])
            for aliquot in aliquots:
                DBSession.add(aliquot)
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
            attachment_form=FormRenderer(Form(self.request, multipart=True)))

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
        attachments = self.context.sample.attachments
        attachment = self.request.matchdict['attachment']
        response.content_type = attachments.thumb_mime_type(attachment)
        response.content_length = attachments.thumb_filesize(attachment)
        response.app_iter = attachments.thumb_open(attachment)
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

