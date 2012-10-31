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

import logging

import pytz
import transaction
from pyramid.view import view_config, forbidden_view_config
from pyramid.security import remember, forget
from pyramid.httpexceptions import HTTPFound
from formencode import validators

from samplesdb.views import BaseView
from samplesdb.forms import BaseSchema, Form, FormRenderer
from samplesdb.security import authenticate
from samplesdb.models import EmailAddress, User


class LoginSchema(BaseSchema):
    username = validators.Email(
        not_empty=True, resolve_domain=False,
        max=EmailAddress.__table__.c.email.type.length)
    password = validators.UnicodeString(not_empty=True, max=100)
    came_from = validators.UnicodeString()


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


class LoginView(BaseView):
    """Handler for login and logout"""

    @view_config(route_name='login', renderer='../templates/login.pt')
    @forbidden_view_config(renderer='../templates/login.pt')
    def login(self):
        referer = self.request.url
        if referer == self.request.route_url('login'):
            referer = self.request.route_url('home')
        form = Form(
            self.request,
            schema=LoginSchema,
            defaults=dict(came_from=referer))
        if form.validate():
            username = form.data['username']
            password = form.data['password']
            if authenticate(username, password):
                headers = remember(self.request, username)
                return HTTPFound(
                    location=form.data['came_from'],
                    headers=headers)
            else:
                self.request.session.flash('Invalid login')
        return dict(
            page_title='Login',
            form=FormRenderer(form),
            )

    @view_config(route_name='logout')
    def logout(self):
        headers = forget(self.request)
        return HTTPFound(
            location=self.request.route_url('home'),
            headers=headers)

    @view_config(
        route_name='sign_up',
        renderer='../templates/sign_up.pt')
    def sign_up(self):
        form = Form(self.request, schema=SignUpSchema)
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
            return HTTPFound(location=self.request.route_url(
                'user_validate_request', email=form.data['email']))
        return dict(
            page_title='New User',
            form=FormRenderer(form),
            )

    @view_config(
        route_name='user_validate_request',
        renderer='../templates/user_validate_request.pt')
    def user_validate_request(self):
        email = self.request.matchdict['email']
        with transaction.manager:
            new_validation = EmailValidation(email)
            DBSession.add(new_validation)
            user = new_validation.email.user
        mailer = self.request.registry['mailer']
        message = Message(
            recipients=[email],
            subject='%s user validation' % self.request.registry.settings['site_title'],
            body=render_template('../templates/validation_email.txt',
                request=self.request,
                user=new_validation.email.user,
                validation=new_validation))
        return dict(
            page_title='Validation Sent',
            email=email,
            timeout=VALIDATION_TIMEOUT,
            )

    @view_config(
        route_name='user_validate_complete',
        renderer='../templates/user_validate_complete.pt')
    def user_validate_complete(self):
        return dict(
            page_title='Validation Complete',
            )

    @view_config(
        route_name='user_validate_cancel',
        renderer='../templates/user_validate_cancel.pt')
    def user_validate_cancel(self):
        return dict(
            page_title='Validation Cancelled',
            )

    @view_config(
        route_name='user_profile',
        renderer='../templates/user_profile.pt')
    def user_profile(self):
        return dict(
            page_title='User Profile',
            )

