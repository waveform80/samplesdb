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

import transaction
from pyramid.response import Response
from pyramid.view import view_config
from pyramid_simpleform import Form
from pyramid_simpleform.renderers import FormRenderer
from formencode import Schema, validators

from samplesdb.models import (
    DBSession,
    User,
    EmailAddress,
    Sample,
    )


@view_config(route_name='index', renderer='templates/index.pt')
def index(request):
    return {'project': 'SamplesDB'}

class BaseSchema(Schema):
    filter_extra_fields = True
    allow_extra_fields = True

class SignUpSchema(BaseSchema):
    email = validators.Email(
        not_empty=True, resolve_domain=True,
        max=EmailAddress.__table__.c.email.type.length)
    password = validators.UnicodeString(not_empty=True)
    salutation = validators.UnicodeString(
        not_empty=True, max=User.__table__.c.salutation.type.length)
    given_name = validators.UnicodeString(
        not_empty=True, max=User.__table__.c.given_name.type.length)
    surname = validators.UnicodeString(
        not_empty=True, max=User.__table__.c.surname.type.length)
    organization = validators.UnicodeString(
        max=User.__table__.c.organization.type.length)
    chained_validators = [
        validators.FieldsMatch('email', 'email_confirm'),
        validators.FieldsMatch('password', 'password_confirm'),
        ]

@view_config(route_name='sign_up', renderer='templates/sign_up.pt')
def sign_up(request):
    form = Form(request, schema=SignUpSchema)
    if form.validate():
        with transaction.manager:
            new_user = form.bind(User())
            DBSession.add(new_user)
        return HTTPFound(location='/')
    return dict(form=FormRenderer(form), project='SamplesDB')
