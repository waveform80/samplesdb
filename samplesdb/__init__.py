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
from sqlalchemy import engine_from_config

from samplesdb.models import DBSession


__version__ = '0.1'

ROUTES = {
    'home':                    '/',
    'login':                   '/login',
    'logout':                  '/logout',
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
    'user_sign_up':            '/sign_up',
    'user_validate':           '/validate/{key}',
    'user_profile':            '/profile',
    }

def main(global_config, **settings):
    """Returns the Pyramid WSGI application"""
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    config = Configurator(settings=settings)
    config.add_static_view('static', 'static', cache_max_age=3600)
    for name, pattern in ROUTES:
        config.add_route(name, pattern)
    config.scan()
    return config.make_wsgi_app()

