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

"""
Defines the view handlers for collection-related views in samplesdb.
"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

from pyramid.view import view_config
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPFound

from samplesdb.helpers import slugify
from samplesdb.views import BaseView
from samplesdb.exporters import CollectionCsvExporter
from samplesdb.forms import (
    Form,
    FormRenderer,
    )
from samplesdb.validators import (
    FormSchema,
    SubFormSchema,
    ForEachDict,
    ValidRole,
    ValidUser,
    ValidCollectionName,
    ValidCollectionOwner,
    ValidCollectionLicense,
    ValidExportColumns,
    ValidCsvDelimiter,
    ValidCsvDoubleQuotes,
    ValidCsvLineTerminator,
    ValidCsvQuoteChar,
    ValidCsvQuoting,
    ValidDateTimeFormat,
    )
from samplesdb.security import (
    OWNER_ROLE,
    CREATE_COLLECTION,
    VIEW_COLLECTION,
    EDIT_COLLECTION,
    VIEW_COLLECTIONS,
    )
from samplesdb.models import (
    DBSession,
    EmailAddress,
    Collection,
    SampleCode,
    Sample,
    Role,
    )


class CollectionUserSchema(SubFormSchema):
    user = ValidUser()
    role = ValidRole()


class CollectionSchema(FormSchema):
    name = ValidCollectionName()
    owner = ValidCollectionOwner()
    license = ValidCollectionLicense()
    users = ForEachDict(CollectionUserSchema(),
                key_name='user', value_name='role')


class CollectionCsvExportSchema(FormSchema):
    columns = ValidExportColumns()
    delimiter = ValidCsvDelimiter()
    doublequote = ValidCsvDoubleQuotes()
    lineterminator = ValidCsvLineTerminator()
    quotechar = ValidCsvQuoteChar()
    quoting = ValidCsvQuoting()
    dateformat = ValidDateTimeFormat()


class CollectionCreateSchema(CollectionSchema):
    pass


class CollectionEditSchema(CollectionSchema):
    pass


class CollectionsView(BaseView):
    """Handlers for collection related views"""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @reify
    def roles(self):
        return [
            (role.id, role.id.title())
            for role in DBSession.query(Role)
            ]

    @reify
    def licenses(self):
        licenses = self.request.registry['licenses']().values()
        licenses = (
            (list(sorted((
                (license.id, license.title)
                for license in licenses
                if license.is_open
                ), key=lambda i: i[1])), 'Open Licenses'),
            (list(sorted((
                (license.id, license.title)
                for license in licenses
                if not license.is_open
                ), key=lambda i: i[1])), 'Proprietary Licenses'),
            )
        return licenses

    @view_config(
        route_name='collections_index',
        renderer='../templates/collections/index.pt',
        permission=VIEW_COLLECTIONS)
    def index(self):
        return dict(
            title='My Collections',
            collections=self.request.user.collections,
            )

    @view_config(
        route_name='collections_open',
        renderer='../templates/collections/index.pt',
        permission=VIEW_COLLECTIONS)
    def open(self):
        return dict(
            title='Open Collections',
            # XXX Perform the open filter with a query
            collections=[
                collection for collection in DBSession.query(Collection)
                if collection.license.is_open
                ]
            )

    @view_config(
        route_name='collections_create',
        renderer='../templates/collections/create.pt',
        permission=CREATE_COLLECTION)
    def create(self):
        form = Form(
            self.request,
            schema=CollectionCreateSchema,
            variable_decode=True,
            defaults=dict(owner=self.request.user.full_name))
        if form.validate():
            new_collection = form.bind(Collection())
            # Hard-code ownership to currently authenticated user
            new_collection.users[self.request.user] = DBSession.query(Role).\
                filter(Role.id==OWNER_ROLE).one()
            DBSession.add(new_collection)
            DBSession.flush()
            return HTTPFound(
                location=self.request.route_url(
                    'collections_view', collection_id=new_collection.id))
        return dict(form=FormRenderer(form))

    @view_config(
        route_name='collections_edit',
        renderer='../templates/collections/edit.pt',
        permission=EDIT_COLLECTION)
    def edit(self):
        collection = self.context.collection
        form = Form(
            self.request,
            schema=CollectionEditSchema,
            obj=collection,
            variable_decode=True)
        if form.validate():
            form.bind(collection)
            # Ensure the edit cannot change ownership by current user
            collection.users[self.request.user] = DBSession.query(Role).\
                filter(Role.id==OWNER_ROLE).one()
            return HTTPFound(location=form.came_from)
        return dict(form=FormRenderer(form))

    @view_config(
        route_name='collections_export',
        renderer='../templates/collections/export.pt',
        permission=VIEW_COLLECTION)
    def export(self):
        exporter = CollectionCsvExporter(self.context.collection)
        form = Form(
            self.request,
            obj=exporter,
            schema=CollectionCsvExportSchema)
        if form.validate():
            form.bind(exporter)
            response = self.request.response
            response.content_type = b'text/csv'
            response.headers.add(
                str('Content-Disposition'),
                str('attachment; filename=%s.csv' % slugify(
                    self.context.collection.name,
                    default='collection-%d' % self.context.collection.id)))
            exporter.export(response.body_file)
            return response
        return dict(
            exporter=exporter,
            form=FormRenderer(form))

    @view_config(
        route_name='collections_view',
        renderer='../templates/collections/view.pt',
        permission=VIEW_COLLECTION)
    def view(self):
        filter = self.request.params.get('filter', 'existing')
        display = self.request.params.get('display', 'grid')
        # XXX Construct a query instead (better performance than retrieving
        # everything and doing filtering in Python)
        samples = [
            sample
            for sample in self.context.collection.all_samples
            if filter == 'all'
            or (filter == 'existing' and not sample.destroyed)
            or (filter == 'destroyed' and sample.destroyed)]
        return dict(
            filter=filter,
            display=display,
            samples=samples)

