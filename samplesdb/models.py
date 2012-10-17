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

"""Declares the database model for the samplesdb application.

This module declares the ORM classes for the samplesdb application. The
SQLAlchemy declarative extension is used to simplify the definitions. Please
note that the production schema is NOT completely specified by these
declarations as we rely on triggers to maintain certain tables. Thus SQLALchemy
is not capable of generating the database structure solely from these
declarations. Instead, see the create_db.*.sql scripts under the samplesdb/sql
directory.
"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import hashlib
from datetime import datetime, timedelta
from itertools import izip_longest

from sqlalchemy import Table, ForeignKey, Column
from sqlalchemy.types import Integer, Unicode, DateTime, String
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.associationproxy import association_proxy
from zope.sqlalchemy import ZopeTransactionExtension


DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


def slow_equals(s, t):
    """
    Compares two strings for equality slowly.

    This function is used to deliberately compare every single byte/char in
    two strings (even when we don't need to) in order to ensure password
    hash checks all take the same time in an attempt to defeat timing attacks
    against the hash.
    """
    result = len(s) ^ len(t)
    for sc, st in izip_longest(s, t):
        result |= ord(sc) ^ ord(st)
    return result == 0


group_permission_table = Table(
    'group_permissions',
    metadata,
    Column(
        'group_id', Unicode(20),
        ForeignKey('groups.id', ondelete='CASCADE'),
        primary_key=True),
    Column(
        'permission_id', Unicode(20),
        ForeignKey('permissions.id', ondelete='RESTRICT'),
        primary_key=True)
    )


user_group_table = Table(
    'user_groups',
    metadata,
    Column(
        'user_id', Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        primary_key=True),
    Column(
        'group_id', Unicode(20),
        ForeignKey('groups.id', ondelete='RESTRICT'),
        primary_key=True)
    )


user_collections_table = Table(
    'user_collections',
    metadata,
    Column(
        'user_id', Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        primary_key=True),
    Column(
        'collection_id', Integer,
        ForeignKey('collections.id', ondelete='RESTRICT'),
        primary_key=True)
    )


class Permission(Base):
    __tablename__ = 'permissions'

    id = Column(Unicode(20), primary_key=True)
    name = Column(Unicode(100))
    groups = relationship(
        'Group', secondary=group_permission_table, backref='permissions')

    def __repr__(self):
        return ('<Permission: id="%s">' % self.name).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.id

    @classmethod
    def by_id(cls, id):
        """return the permission object with id ``id``"""
        return DBSession.query(cls).filter_by(id=id).first()


class Group(Base):
    __tablename__ = 'groups'

    id = Column(Unicode(20), primary_key=True)
    name = Column(Unicode(100))
    users = relationship(
        'User', secondary=user_group_table, backref='groups')

    def __repr__(self):
        return ('<Group: id="%s">' % self.name).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.id

    @classmethod
    def by_id(cls, id):
        """return the group object with id ``id``"""
        return DBSession.query(cls).filter_by(id=id).first()


class Collection(Base):
    __tablename__ = 'collections'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(200), nullable=False)
    created = Column(DateTime, default=datetime.now(), nullable=False)
    samples = relationship('Sample', backref='collection')
    users = relationship(
        'User', secondary=user_collections_table, backref='collections')

    def __repr__(self):
        return ('<Collection: id=%d>' % self.id).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.id

    @classmethod
    def by_id(cls, id):
        """return the collection with id ``id``"""
        return DBSession.query(cls).filter_by(id=id).first()


class UserLimit(Base):
    __tablename__ = 'user_limits'

    id = Column(Unicode(20), primary_key=True)
    collections_limit = Column(Integer, default=10, nullable=False)
    samples_limit = Column(Integer, default=1000, nullable=False)
    users = relationship('User', backref='limits')

    def __repr__(self):
        return ('<UserLimit: id="%s">' % self.id).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.id

    @classmethod
    def by_id(cls, id):
        """return the user limit with id ``id``"""
        return DBSession.query(cls).filter_by(id=id).first()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(200), nullable=False)
    organization = Column(Unicode(200), default='', nullable=False)
    _password = Column('password', String(200), nullable=False)
    created = Column(DateTime, default=datetime.now(), nullable=False)
    emails = relationship('EmailAddress', backref='user')
    limits_id = Column(Unicode(20), ForeignKey('UserLimit.id'))

    def __repr__(self):
        return ('<User: id=%d>' % self.id).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.name

    @classmethod
    def by_id(cls, id):
        """return the user with id ``id``"""
        return DBSession.query(cls).filter_by(id=id).first()

    @property
    def permissions(self):
        """Return a set with all permissions granted to the user."""
        result = set()
        for group in self.groups:
            result = result | set(group.permissions)
        return result

    @classmethod
    def _hash_password(cls, password):
        """Generate a salted hash of the specified password."""
        # Make sure password is a str because we cannot hash unicode objects
        if isinstance(password, unicode):
            password = password.encode('utf-8')
        salt = os.urandom(30)
        hash = hashlib.sha256()
        hash.update(salt)
        hash.update(password)
        return '1:%s:%s' % (
            salt.encode('base64').replace('\n', ''),
            hash.digest().encode('base64').replace('\n', ''))

    def _set_password(self, password):
        """Store a hashed version of password."""
        self._password = self._hash_password(password)

    def _get_password(self):
        """Return the hashed version of the password."""
        return self._password

    password = synonym('_password', descriptor=property(_get_password, _set_password))

    def test_password(self, password):
        """Check the password against existing credentials."""
        now = datetime.now()
        try:
            if self.password.startswith('1:'):
                ver, salt, our_hash = self.password.split(':')
                salt = salt.decode('base64')
                our_hash = our_hash.decode('base64')
                test_hash = hashlib.sha256()
                test_hash.update(salt)
                test_hash.update(password)
                test_hash = test_hash.digest()
                return slow_equals(our_hash, test_hash.digest())
            else:
                raise NotImplementedError
        finally:


class EmailAddress(Base):
    __tablename__ = 'email_addresses'

    email = Column(Unicode(200), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    created = Column(DateTime, default=datetime.now(), nullable=False)
    validation = Column(String(32))
    validation_expiry = Column(DateTime)
    validated = Column(DateTime)

    def __repr__(self):
        return ('<EmailAddress: email="%s">' % self.email).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.email

    @classmethod
    def by_email(cls, email):
        """return the address with email ``email``"""
        return DBSession.query(cls).filter_by(email=email).first()

    def generate_validation_code(self):
        assert self.validated is None
        self.validation = os.urandom(16).encode('hex')
        self.validation_expiry = datetime.now() + timedelta(days=1)

    def check_validation_code(self, code):
        if datetime.now() > self.validate_expiry:
            raise ValueError('Validation code has expired')
        if code != self.validation:
            raise ValueError('Invalid validation code for user %d' % self.user_id)
        self.validated = datetime.datetime.now()
