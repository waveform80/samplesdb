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
from samplesdb.models import DBSession, User, EmailAddress, Collection
from pyramid.security import Allow, Everyone


def user_finder(email_address):
    return User.by_email(email_address)

def group_finder(email_address, request):
    user = user_finder(email_address)
    if user is not None:
        for collection, role in user.collections.items():
            pass

def authenticate(email_address, password):
    # Need a transaction as User.authenticate can potentially write to the
    # database in the event of hash transitions
    with transaction.manager:
        user = user_finder(email_address)
        if user is not None:
            return user.authenticate(password)
        else:
            return False


class RootFactory(object):
    __acl__ = []

    def __init__(self, request):
        pass


class CollectionFactory(object):
    __acl__ = [
        (Allow, 'role:owner',   'destroy_collection'),
        (Allow, 'role:owner',   'rename_collection'),
        (Allow, 'role:owner',   'edit_members'),
        (Allow, 'role:owner',   'add_samples'),
        (Allow, 'role:owner',   'remove_samples'),
        (Allow, 'role:owner',   'audit_samples'),
        (Allow, 'role:owner',   'view_samples'),
        (Allow, 'role:editor',  'add_samples'),
        (Allow, 'role:editor',  'remove_samples'),
        (Allow, 'role:editor',  'audit_samples'),
        (Allow, 'role:editor',  'view_samples'),
        (Allow, 'role:auditor', 'audit_samples'),
        (Allow, 'role:auditor', 'view_samples'),
        (Allow, 'role:viewer',  'view_samples'),
        ]

    def __init__(self, request):
        pass


