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

"""The root of the samplesdb package

This module creates the SQLAlchemy engine, the Pyramid configurator object
(which handles routing), and the WSGI application itself.
"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid_beaker import session_factory_from_settings
from pyramid_mailer import mailer_factory_from_settings
from sqlalchemy import engine_from_config

from samplesdb.security import group_finder, RootContextFactory
from samplesdb.models import DBSession


__version__ = '0.1'

ROUTES = {
    # views.root
    'home':                       '/',
    'faq':                        '/faq',
    # views.account
    'account_login':              '/login',
    'account_logout':             '/logout',
    'account_index':              '/account',
    'account_create':             '/signup',
    'account_edit':               '/account/edit',
    'account_add_email':          '/account/add-email',
    'account_remove_email':       '/account/remove-email',
    'account_verify_email':       '/account/verify',
    'account_verify_complete':    '/verify/{code}',
    'account_verify_cancel':      '/cancel/{code}',
    'reset_password_request':     '/reset/send/{email}',
    'reset_password_complete':    '/reset/complete/{code}',
    'reset_password_cancel':      '/reset/cancel/{code}',
    # views.collections
    'collections_index':          '/collections',
    'collections_create':         '/collections/new',
    'collections_view':           '/collections/{collection_id}',
    'collections_edit':           '/collections/{collection_id}/edit',
    'collections_destroy':        '/collections/{collection_id}/destroy',
    'sample_view':                '/samples/{sample_id}',
    'sample_edit':                '/samples/{sample_id}/edit',
    'sample_split':               '/samples/{sample_id}/split',
    'sample_destroy':             '/samples/{sample_id}/destroy',
    'sample_remove':              '/samples/{sample_id}/remove',
    'sample_combine':             '/samples/combine',
    # views.admin
    'admin_home':              '/admin/',
    'admin_users':             '/admin/users/',
    'admin_user_create':       '/admin/users/new',
    'admin_user_view':         '/admin/users/{id}',
    'admin_user_edit':         '/admin/users/{id}/edit',
    'admin_user_remove':       '/admin/users/{id}/remove',
    'admin_groups':            '/admin/groups',
    'admin_group_create':      '/admin/groups/new',
    'admin_group_view':        '/admin/group/{id}',
    'admin_group_edit':        '/admin/group/{id}/edit',
    'admin_group_remove':      '/admin/group/{id}/remove',
    }


def main(global_config, **settings):
    """Returns the Pyramid WSGI application"""
    session_factory = session_factory_from_settings(settings)
    mailer_factory = mailer_factory_from_settings(settings)
    engine = engine_from_config(settings, 'sqlalchemy.')
    authn_policy = AuthTktAuthenticationPolicy('secret', callback=group_finder)
    authz_policy = ACLAuthorizationPolicy()
    DBSession.configure(bind=engine)

    config = Configurator(
        settings=settings, root_factory=RootContextFactory)
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)
    config.registry['mailer'] = mailer_factory
    config.set_session_factory(session_factory)
    config.add_static_view('static', 'static', cache_max_age=3600)
    for name, url in ROUTES.items():
        config.add_route(name, url)
    config.scan()
    app = config.make_wsgi_app()
    # XXX Dirty horrid hack for functional testing
    if settings.get('testing', '0') == '1':
        app.engine = engine
    return app

