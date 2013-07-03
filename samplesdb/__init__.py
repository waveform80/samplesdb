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
The main module of the samplesdb application.

This module creates the Pyramid configurator object which in turn is used to
create the WSGI application itself. The main() routine is referenced by the
INI file passed to pserve.
"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import warnings
warnings.resetwarnings()
import mimetypes

from pyramid.config import Configurator
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid_beaker import session_factory_from_settings
from pyramid_mailer import mailer_factory_from_settings
from sqlalchemy import engine_from_config

from samplesdb.models import DBSession
from samplesdb.licenses import licenses_factory_from_settings
from samplesdb.authentication import authentication_policy_from_settings
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
    'home':                        r'/',
    'faq':                         r'/faq',
    # views.account
    'account_login':               r'/login',
    'account_logout':              r'/logout',
    'account_index':               r'/account',
    'account_create':              r'/signup',
    'account_edit':                r'/account/edit',
    'account_add_email':           r'/account/add-email',
    'account_remove_email':        r'/account/remove-email',
    'account_verify_email':        r'/account/verify',
    'account_verify_complete':     r'/verify/{code:[a-fA-f0-9]+}',
    'account_reset_password':      r'/account/reset',
    'account_reset_complete':      r'/reset/{code:[a-fA-F0-9]+}',
    # views.collections
    'collections_index':           r'/collections',
    'collections_open':            r'/collections/open',
    'collections_create':          r'/collections/new',
    'collections_view':            r'/collections/{collection_id:\d+}',
    'collections_edit':            r'/collections/{collection_id:\d+}/edit',
    'collections_export':          r'/collections/{collection_id:\d+}/export',
    'collections_destroy':         r'/collections/{collection_id:\d+}/destroy',
    'samples_create':              r'/collections/{collection_id:\d+}/new',
    'samples_combine':             r'/collections/{collection_id:\d+}/combine',
    'samples_view':                r'/samples/{sample_id:\d+}',
    'samples_edit':                r'/samples/{sample_id:\d+}/edit',
    'samples_split':               r'/samples/{sample_id:\d+}/split',
    'samples_destroy':             r'/samples/{sample_id:\d+}/destroy',
    'samples_remove':              r'/samples/{sample_id:\d+}/remove',
    'samples_add_log':             r'/samples/{sample_id:\d+}/add-log',
    'samples_add_attachment':      r'/samples/{sample_id:\d+}/add-attachment',
    'samples_remove_attachment':   r'/samples/{sample_id:\d+}/remove-attachment',
    'samples_default_attachment':  r'/samples/{sample_id:\d+}/default-attachment',
    'samples_download_attachment': r'/samples/{sample_id:\d+}/download-attachment',
    'samples_attachment_thumb':    r'/samples/{sample_id:\d+}/thumb/{attachment}',
    # views.admin
    'admin_home':                  r'/admin/',
    'admin_users':                 r'/admin/users/',
    'admin_user_create':           r'/admin/users/new',
    'admin_user_view':             r'/admin/users/{id:\d+}',
    'admin_user_edit':             r'/admin/users/{id:\d+}/edit',
    'admin_user_remove':           r'/admin/users/{id:\d+}/remove',
    'admin_groups':                r'/admin/groups',
    'admin_group_create':          r'/admin/groups/new',
    'admin_group_view':            r'/admin/groups/{id}',
    'admin_group_edit':            r'/admin/groups/{id}/edit',
    'admin_group_remove':          r'/admin/groups/{id}/remove',
    }


def main(global_config, **settings):
    """Returns the Pyramid WSGI application"""
    # Ensure that the production configuration has been updated with "real"
    # values (at least where required for security)
    for key in ('authn.secret', 'session.secret'):
        if settings.get(key) == 'CHANGEME':
            raise ValueError('You must specify a new value for %s' % key)
    mimetypes.init()
    session_factory = session_factory_from_settings(settings)
    mailer_factory = mailer_factory_from_settings(settings)
    licenses_factory = licenses_factory_from_settings(settings)
    authn_policy = authentication_policy_from_settings(settings)
    authz_policy = ACLAuthorizationPolicy()
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)

    config = Configurator(
        settings=settings,
        root_factory=RootContextFactory,
        authentication_policy=authn_policy,
        authorization_policy=authz_policy,
        session_factory=session_factory)
    config.registry['mailer'] = mailer_factory
    config.registry['licenses'] = licenses_factory
    # XXX Deprecated in 1.4
    config.set_request_property(get_user, b'user', reify=True)
    # XXX For 1.4:
    #config.add_request_method(get_user, b'user', reify=True)
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

