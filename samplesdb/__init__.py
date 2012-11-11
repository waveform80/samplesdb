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

import mimetypes

from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid_beaker import session_factory_from_settings
from pyramid_mailer import mailer_factory_from_settings
from sqlalchemy import engine_from_config

from samplesdb.models import DBSession
from samplesdb.security import (
    get_user,
    group_finder,
    RootContextFactory,
    CollectionContextFactory,
    SampleContextFactory,
    )


__version__ = '0.1'

ROUTES = {
    # views.root
    'home':                       r'/',
    'faq':                        r'/faq',
    # views.account
    'account_login':              r'/login',
    'account_logout':             r'/logout',
    'account_index':              r'/account',
    'account_create':             r'/signup',
    'account_edit':               r'/account/edit',
    'account_add_email':          r'/account/add-email',
    'account_remove_email':       r'/account/remove-email',
    'account_verify_email':       r'/account/verify',
    'account_verify_complete':    r'/verify/{code:[a-fA-f0-9]+}',
    'account_reset_password':     r'/account/reset',
    'account_reset_complete':     r'/reset/{code:[a-fA-F0-9]+}',
    # views.collections
    'collections_index':          r'/collections',
    'collections_create':         r'/collections/new',
    'collections_view':           r'/collections/{collection_id:\d+}',
    'collections_edit':           r'/collections/{collection_id:\d+}/edit',
    'collections_destroy':        r'/collections/{collection_id:\d+}/destroy',
    'samples_create':             r'/collections/{collection_id:\d+}/new',
    'samples_view':               r'/samples/{sample_id:\d+}',
    'samples_edit':               r'/samples/{sample_id:\d+}/edit',
    'samples_split':              r'/samples/{sample_id:\d+}/split',
    'samples_destroy':            r'/samples/{sample_id:\d+}/destroy',
    'samples_remove':             r'/samples/{sample_id:\d+}/remove',
    'samples_combine':            r'/samples/combine',
    # views.admin
    'admin_home':                 r'/admin/',
    'admin_users':                r'/admin/users/',
    'admin_user_create':          r'/admin/users/new',
    'admin_user_view':            r'/admin/users/{id:\d+}',
    'admin_user_edit':            r'/admin/users/{id:\d+}/edit',
    'admin_user_remove':          r'/admin/users/{id:\d+}/remove',
    'admin_groups':               r'/admin/groups',
    'admin_group_create':         r'/admin/groups/new',
    'admin_group_view':           r'/admin/groups/{id}',
    'admin_group_edit':           r'/admin/groups/{id}/edit',
    'admin_group_remove':         r'/admin/groups/{id}/remove',
    }


def main(global_config, **settings):
    """Returns the Pyramid WSGI application"""
    mimetypes.init()
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
    config.set_request_property(get_user, b'user', reify=True)
    config.add_static_view('static', 'static', cache_max_age=3600)
    for name, url in ROUTES.items():
        if '{collection_id:' in url:
            factory = CollectionContextFactory
        elif '{sample_id:' in url:
            factory = SampleContextFactory
        else:
            factory = RootContextFactory
        config.add_route(name, url, factory=factory)
    config.scan()
    app = config.make_wsgi_app()
    # XXX Dirty horrid hack for functional testing
    if settings.get('testing', '0') == '1':
        app.engine = engine
    return app

