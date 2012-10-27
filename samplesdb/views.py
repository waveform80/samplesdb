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
from pyramid.view import view_config, forbidden_view_config
from pyramid.security import remember, forget, authenticated_userid
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import get_renderer
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


@view_config(route_name='login', renderer='templates/login.pt')
@forbidden_view_config(renderer='templates/login.pt')
def login(request):
    master = get_renderer('templates/master.pt').implementation()
    login_url = request.route_url('login')
    referer = request.url
    if referer == login_url:
        referer = request.route_url('user_profile')
    came_from = request.params.get('came_from', referer)
    username = None
    password = None
    # XXX Do we need to add this to the form?
    if 'form.submitted' in request.params:
        username = request.params.get('username')
        password = request.params.get('password')
        # XXX Replace with real login code
        if password == password:
            headers = remember(request, login)
            return HTTPFound(location=came_from, headers=headers)
        flash = 'Invalid login'
    return dict(
        page_title='Home',
        master=master,
        url=request.route_url('login'),
        came_from=came_from,
        username=username,
        password=password)

@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(location=request.route_url('login'), headers=headers)

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
    master = get_renderer('templates/master.pt').implementation()
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
            'user_validate_request', email=form.data['email']))
    return dict(page_title='New User', master=master, form=FormRenderer(form))

@view_config(route_name='user_validate_request', renderer='templates/user_validate_request.pt')
def user_validate_start(request):
    master = get_renderer('templates/master.pt').implementation()
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
            request=request,
            user=new_validation.email.user,
            validation=new_validation))
    return dict(page_title='Validation Sent', master=master, email=email, timeout=VALIDATION_TIMEOUT)

@view_config(route_name='user_validate_complete', renderer='templates/user_validate_complete.pt')
def user_validate_complete(request):
    master = get_renderer('templates/master.pt').implementation()
    return dict(page_title='Validation Complete', master=master)

@view_config(route_name='user_validate_cancel', renderer='templates/user_validate_cancel.pt')
def user_validate_cancel(request):
    master = get_renderer('templates/master.pt').implementation()
    return dict(page_title='Validation Cancelled', master=master)
