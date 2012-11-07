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
from samplesdb.models import (
    DBSession,
    User,
    Collection,
    Sample,
    )
from pyramid.security import (
    Allow,
    Everyone,
    Authenticated,
    )


# Permissions
CREATE_USER        = 'create_user'
DESTROY_USER       = 'destroy_user'
EDIT_USER          = 'edit_user'
CREATE_GROUP       = 'create_group'
DESTROY_GROUP      = 'destroy_group'
EDIT_GROUP         = 'edit_group'
CREATE_LIMIT       = 'create_limit'
DESTROY_LIMIT      = 'destroy_limit'
EDIT_LIMIT         = 'edit_limit'
CREATE_COLLECTION  = 'create_collection'
DESTROY_COLLECTION = 'destroy_collection'
RENAME_COLLECTION  = 'rename_collection'
EDIT_MEMBERS       = 'edit_members'
EDIT_COLLECTION    = 'edit_collection'
AUDIT_COLLECTION   = 'audit_collection'
VIEW_COLLECTION    = 'view_collection'
MANAGE_COLLECTIONS = 'manage_collections'
MANAGE_ACCOUNT     = 'manage_account'

# Permission groups
AUTHENTICATED_PERMISSIONS = (MANAGE_COLLECTIONS, MANAGE_ACCOUNT, CREATE_COLLECTION)
VIEWER_PERMISSIONS        = AUTHENTICATED_PERMISSIONS + (VIEW_COLLECTION,)
AUDITOR_PERMISSIONS       = VIEWER_PERMISSIONS + (AUDIT_COLLECTION,)
EDITOR_PERMISSIONS        = AUDITOR_PERMISSIONS + (EDIT_COLLECTION,)
OWNER_PERMISSIONS         = EDITOR_PERMISSIONS + (
    DESTROY_COLLECTION,
    RENAME_COLLECTION,
    EDIT_MEMBERS,
    )
ADMIN_PERMISSIONS = OWNER_PERMISSIONS + (
    CREATE_USER,
    DESTROY_USER,
    EDIT_USER,
    CREATE_GROUP,
    DESTROY_GROUP,
    EDIT_GROUP,
    CREATE_LIMIT,
    DESTROY_LIMIT,
    EDIT_LIMIT,
    )

# Principal prefixes
ROLE_PREFIX  = 'role:'
GROUP_PREFIX = 'group:'

# Role and group names
VIEWER_ROLE  = 'viewer'
AUDITOR_ROLE = 'auditor'
EDITOR_ROLE  = 'editor'
OWNER_ROLE   = 'owner'
ADMINS_GROUP = 'admins'

# Collection principals
VIEWER_PRINCIPAL  = ROLE_PREFIX + 'viewer'
AUDITOR_PRINCIPAL = ROLE_PREFIX + 'auditor'
EDITOR_PRINCIPAL  = ROLE_PREFIX + 'editor'
OWNER_PRINCIPAL   = ROLE_PREFIX + 'owner'

# Administration principals
ADMINS_PRINCIPAL  = GROUP_PREFIX + 'admins'


def user_finder(email_address):
    "Returns the User object with the specified email address or None"
    return User.by_email(email_address)

def group_finder(email_address, request):
    "Returns the set of principals for a user in the current context"
    user = user_finder(email_address)
    principals = []
    if user is not None:
        # Each group the user belongs to is added as a principal
        principals.extend(GROUP_PREFIX + group for group in user.groups)
        if (
                isinstance(request.context, CollectionContextFactory) or
                isinstance(request.context, SampleContextFactory)):
            # Each role the user holds in the current context's collection
            # is added as a principal
            principals.extend(
                ROLE_PREFIX + role
                for role in user.collections[request.context.collection])
    return principals

def authenticate(email_address, password):
    "Authenticates the user with the specified email address and password"
    # Need a transaction as User.authenticate can potentially write to the
    # database in the event of hash transitions
    with transaction.manager:
        user = user_finder(email_address)
        if user is not None:
            return user.authenticate(password)
        else:
            return False


class RootContextFactory(object):
    __acl__ = [
        (Allow , Authenticated     , AUTHENTICATED_PERMISSIONS) ,
        (Allow , VIEWER_PRINCIPAL  , VIEWER_PERMISSIONS)        ,
        (Allow , AUDITOR_PRINCIPAL , AUDITOR_PERMISSIONS)       ,
        (Allow , EDITOR_PRINCIPAL  , EDITOR_PERMISSIONS)        ,
        (Allow , OWNER_PRINCIPAL   , OWNER_PERMISSIONS)         ,
        (Allow , ADMINS_PRINCIPAL  , ADMIN_PERMISSIONS)         ,
        ]

    def __init__(self, request):
        pass


class CollectionContextFactory(RootContextFactory):
    def __init__(self, request):
        super(CollectionContextFactory, self).__init__(request)
        self.collection = DBSession.query(Collection).\
            filter_by(id=request.matchdict['collection_id']).one()


class SampleContextFactory(RootContextFactory):
    def __init__(self, request):
        super(SampleContextFactory, self).__init__(request)
        self.sample = DBSession.query(Sample).\
            filter_by(id=request.matchdict['sample_id']).one()
        self.collection = self.sample.collection
