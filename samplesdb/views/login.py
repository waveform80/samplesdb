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

from pyramid.view import view_config, forbidden_view_config
from pyramid.security import remember, forget
from pyramid.httpexceptions import HTTPFound
from formencode import validators

from samplesdb.views import BaseView
from samplesdb.forms import BaseSchema, Form, FormRenderer
from samplesdb.security import authenticate
from samplesdb.models import EmailAddress


class LoginSchema(BaseSchema):
    username = validators.Email(
        not_empty=True, resolve_domain=False,
        max=EmailAddress.__table__.c.email.type.length)
    password = validators.UnicodeString(not_empty=True, max=100)
    came_from = validators.UnicodeString()


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

