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

import pytz
import transaction
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.chameleon_text import render_template
from pyramid_simpleform import Form
from pyramid_mailer.message import Message
from formencode import Schema, validators

from samplesdb.forms import FormRenderer
from samplesdb.models import (
    VALIDATION_TIMEOUT,
    DBSession,
    User,
    Collection,
    EmailAddress,
    EmailValidation,
    Sample,
    )


@view_config(route_name='index', renderer='templates/index.pt')
def index(request):
    return {}

class BaseSchema(Schema):
    filter_extra_fields = True
    allow_extra_fields = True

class SignUpSchema(BaseSchema):
    email = validators.Email(
        not_empty=True, resolve_domain=True,
        max=EmailAddress.__table__.c.email.type.length)
    email_confirm = validators.UnicodeString()
    password = validators.UnicodeString(not_empty=True, max=100)
    password_confirm = validators.UnicodeString()
    salutation = validators.OneOf([
        '', 'Mr.', 'Mrs.', 'Miss', 'Ms.', 'Dr.', 'Prof.'])
    given_name = validators.UnicodeString(
        not_empty=True, max=User.__table__.c.given_name.type.length)
    surname = validators.UnicodeString(
        not_empty=True, max=User.__table__.c.surname.type.length)
    organization = validators.UnicodeString(
        max=User.__table__.c.organization.type.length)
    limits_id = validators.OneOf([
        'academic', 'commercial'])
    timezone = validators.OneOf(pytz.all_timezones)
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
            new_email = form.bind(EmailAddress())
            new_email.user = new_user
            DBSession.add(new_email)
            new_collection = Collection()
            new_collection.name = 'Default'
            owner_role = DBSession.query(Role).filter(Role.id=='owner').one()
            new_user.collections[new_collection] = owner_role
        return HTTPFound(location=request.route_url(
            'send_validation_email', email=form.data['email']))
    return dict(form=FormRenderer(form))

@view_config(route_name='user_validate_start', renderer='templates/send_validation_email.pt')
def user_validate_start(request):
    email = request.matchdict['email']
    with transaction.manager:
        new_validation = EmailValidation(email)
        DBSession.add(new_validation)
        user = new_validation.email.user
    mailer = request.registry['mailer']
    message = Message(
        recipients=[email],
        subject='%s user validation' % request.registry.settings['site_title'],
        body=render_template('samplesdb:templates/validation_email.txt',
            user=user,
            code=new_validation.id))
    return dict(email=email, timeout=VALIDATION_TIMEOUT)
