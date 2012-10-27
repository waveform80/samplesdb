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

from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
#from pyramid_beaker import session_factory_from_settings
#from pyramid_mailer import mailer_factory_from_settings
from sqlalchemy import engine_from_config

from samplesdb.security import group_finder, RootFactory
from samplesdb.models import DBSession


__version__ = '0.1'

ROUTES = {
    'login':                   '/',
    'logout':                  '/logout',
    'sign_up':                 '/signup',
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
    'admin_permissions':       '/admin/permissions/',
    'admin_permission_create': '/admin/permissions/new',
    'admin_permission_view':   '/admin/permissions/{id}',
    'admin_permission_edit':   '/admin/permissions/{id}/edit',
    'admin_permission_remove': '/admin/permissions/{id}/remove',
    'user_validate_request':   '/validate/send/{email}',
    'user_validate_complete':  '/validate/complete/{code}',
    'user_validate_cancel':    '/validate/cancel/{code}',
    'reset_password_request':  '/reset/send/{email}',
    'reset_password_complete': '/reset/complete/{code}',
    'reset_password_cancel':   '/reset/cancel/{code}',
    'user_profile':            '/profile',
    'user_collections':        '/collections',
    'user_collection_create':  '/collections/new',
    'user_collection_view':    '/collections/{id}',
    'user_collection_edit':    '/collections/{id}/edit',
    'user_collection_remove':  '/collections/{id}/remove',
    'user_sample_view':        '/samples/{id}',
    'user_sample_edit':        '/samples/{id}/edit',
    'user_sample_split':       '/samples/{id}/split',
    'user_sample_destroy':     '/samples/{id}/destroy',
    'user_sample_remove':      '/samples/{id}/remove',
    'user_sample_combine':     '/samples/combine',
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
        settings=settings, root_factory=RootFactory)
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)
    config.registry['mailer'] = mailer_factory
    config.set_session_factory(session_factory)
    config.add_static_view('static', 'static', cache_max_age=3600)
    for name, pattern in ROUTES.items():
        config.add_route(name, pattern)
    config.scan()

    return config.make_wsgi_app()

