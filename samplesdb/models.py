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
from datetime import datetime, timedelta, date
from itertools import izip_longest

from sqlalchemy import Table, Column, ForeignKey, CheckConstraint, func
from sqlalchemy.types import Integer, Unicode, UnicodeText, Date, DateTime, String
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, synonym
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


class EmailValidation(Base):
    __tablename__ = 'email_validations'

    id = Column(String(32), primary_key=True)
    created = Column(DateTime, default=datetime.utcnow, nullable=False)
    expiry = Column(DateTime, nullable=False)
    email_ref = Column(
        Unicode(200), ForeignKey(
            'email_addresses.email', onupdate='RESTRICT', ondelete='CASCADE'),
        nullable=False)
    # email defined as backref on EmailAddress

    def __init__(self, **kwargs):
        super(EmailValidation, self).__init__(**kwargs)
        # XXX Ensure a validation hasn't been requested in the last 10 minutes
        self.expiry = datetime.utcnow() + timedelta(days=1)
        # XXX Calculate os.urandom length from self.id.len? / 2
        self.id = os.urandom(16).encode('hex')

    def __repr__(self):
        return ('<EmailValidation: id="%s">' % self.id).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.id

    @classmethod
    def by_id(cls, id):
        """return the email validation record with id ``id``"""
        return DBSession.query(cls).filter_by(id=id).first()

    def validate(self, user):
        if datetime.utcnow() > self.expiry:
            raise ValueError('Validation code has expired')
        if user is not self.email.user:
            raise ValueError('Invalid user for validation code %s' % self.id)
        self.email.validated = datetime.utcnow()
        DBSession.delete(self)


class EmailAddress(Base):
    __tablename__ = 'email_addresses'

    email = Column(Unicode(200), primary_key=True)
    user_id = Column(
        Integer, ForeignKey(
            'users.id', onupdate='RESTRICT', ondelete='CASCADE'),
        nullable=False)
    # user defined as backref on Users
    created = Column(DateTime, default=datetime.utcnow, nullable=False)
    validated = Column(DateTime)
    validations = relationship(EmailValidation, backref='email')

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


class PasswordReset(Base):
    __tablename__ = 'password_resets'

    id = Column(String(32), primary_key=True)
    created = Column(DateTime, default=datetime.utcnow, nullable=False)
    expiry = Column(DateTime, nullable=False)
    user_id = Column(
        Integer, ForeignKey(
            'users.id', onupdate='RESTRICT', ondelete='CASCADE'),
        nullable=False)
    # user defined as backref on User

    def __init__(self, **kwargs):
        super(PasswordReset, self).__init__(**kwargs)
        # XXX Ensure a reset hasn't been requested in the last 10 minutes
        self.expiry = datetime.utcnow() + timedelta(days=1)
        # XXX Calculate os.urandom length from self.id.len? / 2
        self.id = os.urandom(16).encode('hex')

    def __repr__(self):
        return ('<PasswordReset: id="%s">' % self.id).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.id

    @classmethod
    def by_id(cls, id):
        """return the password reset record with id ``id``"""
        return DBSession.query(cls).filter_by(id=id).first()

    def reset_password(self, user, new_password):
        if datetime.utcnow() > self.expiry:
            raise ValueError('Validation code has expired')
        if user is not self.user:
            raise ValueError('Invalid user for validation code %s' % self.id)
        self.user.password = new_password
        DBSession.delete(self)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(200), nullable=False)
    organization = Column(Unicode(200), default='', nullable=False)
    _password = Column('password', String(200))
    password_changed = Column(DateTime)
    resets = relationship(PasswordReset, backref='user')
    created = Column(DateTime, default=datetime.utcnow, nullable=False)
    emails = relationship(EmailAddress, backref='user')
    limits_id = Column(
        Unicode(20), ForeignKey(
            'user_limits.id', onupdate='RESTRICT', ondelete='RESTRICT'),
        nullable=False)
    # limits defined as backref on UserLimit
    # groups defined as backref on Group
    # collections defined as backref on Collection

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
        self.password_changed = datetime.utcnow()

    def _get_password(self):
        """Return the hashed version of the password."""
        return self._password

    password = synonym('_password', descriptor=property(_get_password, _set_password))

    def test_password(self, password):
        """Check the password against existing credentials."""
        utcnow = datetime.utcnow()
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
            # XXX Pause for up to a second to ensure all logins take a "long"
            # time (at least in computational terms)
            pass


class UserLimit(Base):
    __tablename__ = 'user_limits'

    id = Column(Unicode(20), primary_key=True)
    collections_limit = Column(Integer, default=10, nullable=False)
    samples_limit = Column(Integer, default=1000, nullable=False)
    users = relationship(User, backref='limits')

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


class Group(Base):
    __tablename__ = 'groups'

    id = Column(Unicode(20), primary_key=True)
    description = Column(Unicode(100))
    users = relationship(
        User, secondary=lambda: user_group_table, backref='groups')
    # permissions defined as backref on Permissions

    def __repr__(self):
        return ('<Group: id="%s">' % self.id).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.id

    @classmethod
    def by_id(cls, id):
        """return the group object with id ``id``"""
        return DBSession.query(cls).filter_by(id=id).first()


class Permission(Base):
    __tablename__ = 'permissions'

    id = Column(Unicode(20), primary_key=True)
    description = Column(Unicode(100))
    groups = relationship(
        Group, secondary=lambda: group_permission_table, backref='permissions')

    def __repr__(self):
        return ('<Permission: id="%s">' % self.id).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.id

    @classmethod
    def by_id(cls, id):
        """return the permission object with id ``id``"""
        return DBSession.query(cls).filter_by(id=id).first()


class SampleAudit(Base):
    __tablename__ = 'sample_audits'

    sample_id = Column(
        Integer, ForeignKey(
            'samples.id', onupdate='RESTRICT', ondelete='CASCADE'),
        primary_key=True)
    # sample defined as backref on Sample
    audited = Column(DateTime, default=datetime.utcnow, primary_key=True)
    auditor_id = Column(
        Integer, ForeignKey(
            'users.id', onupdate='RESTRICT', ondelete='RESTRICT'),
        nullable=False)
    auditor = relationship(User)

    def __repr__(self):
        return ('<SampleAudit: sample_id=%d, audited="%s">' % (
            self.sample_id, self.audited.isoformat())).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return '%d at %s' % (self.sample_id, self.audited.isoformat())


class SampleImage(Base):
    __tablename__ = 'sample_images'

    sample_id = Column(
        Integer, ForeignKey(
            'samples.id', onupdate='RESTRICT', ondelete='CASCADE'),
        primary_key=True)
    # sample defined as backref on Sample
    filename = Column(Unicode(200), primary_key=True)
    creator_id = Column(
        Integer, ForeignKey(
            'users.id', onupdate='RESTRICT', ondelete='SET NULL'))
    creator = relationship(User)
    created = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return ('<SampleImage: sample_id=%d, created_by=%d, created="%s">' % (
            self.sample_id, self.created_by, self.audited.isoformat())).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.content


class Sample(Base):
    __tablename__ = 'samples'

    id = Column(Integer, primary_key=True)
    description = Column(Unicode(200), nullable=False)
    created = Column(DateTime)
    creator_id = Column(Integer, ForeignKey(/usr/local/turbogears/ratbot/dbfiles/synchro_2_2.png
        'users.id', onupdate='RESTRICT', ondelete='SET NULL'))
    creator = relationship(User)
    destroyed = Column(DateTime)
    code = Column(Unicode(50), default='', nullable=False)
    notes = Column(UnicodeText, default='', nullable=False)
    collection_id = Column(Integer, ForeignKey(
        'collections.id', onupdate='RESTRICT', ondelete='CASCADE'),
        nullable=False)
    # collection defined as backref on Collection
    parents = relationship(
        'Sample', secondary=lambda: sample_origins_table,
        primaryjoin='samples.id = sample_origins.sample_id',
        secondaryjoin='sample_origins.parent_id = samples.id')
    children = relationship(
        'Sample', secondary=lambda: sample_origins_table,
        primaryjoin='samples.id = sample_origins.parent_id',
        secondaryjoin='sample_origins.sample_id = samples.id')
    images = relationship(SampleImage, backref='sample')
    audits = relationship(SampleAudit, backref='sample')

    def __repr__(self):
        return ('<Sample: id=%d>' % self.id).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.description

    @classmethod
    def by_id(cls, id):
        """return the permission object with id ``id``"""
        return DBSession.query(cls).filter_by(id=id).first()


class Collection(Base):
    __tablename__ = 'collections'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(200), nullable=False)
    created = Column(DateTime, default=datetime.utcnow(), nullable=False)
    samples = relationship(Sample, backref='collection')
    users = relationship(
        User, secondary=lambda: user_collections_table, backref='collections')

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


class Role(Base):
    __tablename__ = 'roles'

    id = Column(Unicode(20), primary_key=True)
    description = Column(Unicode(100), nullable=False)
    created = Column(DateTime, default=datetime.utcnow(), nullable=False)

    def __repr__(self):
        return ('<Role: id="%s">' % self.id).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.id

    @classmethod
    def by_id(cls, id):
        """return the role object with id ``id``"""
        return DBSession.query(cls).filter_by(id=id).first()


group_permission_table = Table(
    'group_permissions',
    Base.metadata,
    Column(
        'group_id', Unicode(20),
        ForeignKey('groups.id', onupdate='RESTRICT', ondelete='CASCADE'),
        primary_key=True),
    Column(
        'permission_id', Unicode(20),
        ForeignKey('permissions.id', onupdate='RESTRICT', ondelete='RESTRICT'),
        primary_key=True)
    )


user_group_table = Table(
    'user_groups',
    Base.metadata,
    Column(
        'user_id', Integer,
        ForeignKey('users.id', onupdate='RESTRICT', ondelete='CASCADE'),
        primary_key=True),
    Column(
        'group_id', Unicode(20),
        ForeignKey('groups.id', onupdate='RESTRICT', ondelete='RESTRICT'),
        primary_key=True)
    )


user_collections_table = Table(
    'user_collections',
    Base.metadata,
    Column(
        'user_id', Integer,
        ForeignKey('users.id', onupdate='RESTRICT', ondelete='CASCADE'),
        primary_key=True),
    Column(
        'collection_id', Integer,
        ForeignKey('collections.id', onupdate='RESTRICT', ondelete='CASCADE'),
        primary_key=True),
    Column(
        'role_id', Unicode(20),
        ForeignKey('roles.id', onupdate='RESTRICT', ondelete='RESTRICT'),
        nullable=False)
    )


sample_origins_table = Table(
    'sample_origins',
    Base.metadata,
    Column(
        'sample_id', Integer,
        ForeignKey('samples.id', onupdate='RESTRICT', ondelete='CASCADE'),
        primary_key=True),
    Column(
        'parent_id', Integer,
        ForeignKey('samples.id', onupdate='RESTRICT', ondelete='CASCADE'),
        primary_key=True)
    )
