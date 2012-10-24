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
from datetime import datetime, timedelta, date
from itertools import izip_longest

import pytz
from passlib.context import CryptContext
from sqlalchemy import (
    Table,
    Column,
    ForeignKey,
    CheckConstraint,
    func,
    )
from sqlalchemy.types import (
    Integer,
    Unicode,
    UnicodeText,
    Date,
    DateTime,
    String,
    )
from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    relationship,
    synonym,
    backref,
    )
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.associationproxy import association_proxy
from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

PASSWORD_CONTEXT = CryptContext(
    # Use PBKDF2 algorithm for password hashing with 10% variance in the rounds
    schemes = [b'pbkdf2_sha256'],
    default = b'pbkdf2_sha256',
    all__vary_rounds = 0.1,
    )

VALIDATION_TIMEOUT = 24 * 60 * 60 # 1 day in seconds
VALIDATION_INTERVAL = 10 * 60 # 10 minutes in seconds
VALIDATION_LIMIT = 3

RESET_TIMEOUT = 24 * 60 * 60 # 1 day in seconds
RESET_INTERNAL = 10 * 60 # 10 minutes in seconds
RESET_LIMIT = 3


class ValidationError(Exception):
    pass


class ResetError(Exception):
    pass


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

    def __init__(self, email):
        super(EmailValidation, self).__init__(**kwargs)
        if DBSession.query(EmailValidation).\
            filter(EmailValidation.email_ref==email).\
            filter(EmailValidation.created>datetime.utcnow() + timedelta(seconds=VALIDATION_INTERVAL)).first():
                raise ValidationError('A validation was requested for that '
                    'email address less than %d seconds ago' %
                    VALIDATION_INTERVAL)
        if DBSession.query(EmailValidation).\
            filter(EmailValidation.email_ref==email).\
            filter(EmailValidation.expiry<datetime.utcnow()).count() > VALIDATION_LIMIT:
                raise ValidationError('Too many active validations '
                    'currently exist for this account')
        self.email_ref = email
        self.expiry = datetime.utcnow() + timedelta(seconds=VALIDATION_TIMEOUT)
        self.id = os.urandom(self.__table__.c.id.type.length / 2).encode('hex')

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
            raise ValidationError('Validation code has expired')
        if user is not self.email.user:
            raise ValidationError('Invalid user for validation code %s' % self.id)
        self.email.validated = datetime.utcnow()
        DBSession.query(EmailValidation).\
            filter(EmailValidation.email_ref==self.email_ref).delete()


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
    validations = relationship(
        EmailValidation, backref='email',
        cascade='all, delete-orphan', passive_deletes=True)

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

    def __init__(self, user):
        super(PasswordReset, self).__init__(**kwargs)
        if DBSession.query(PasswordReset).\
            filter(PasswordReset.user_id==user.id).\
            filter(PasswordReset.created>datetime.utcnow() + timedelta(seconds=RESET_INTERVAL)).first():
                raise ResetError('A reset was requested for that '
                    'account less than %d seconds ago' % RESET_INTERVAL)
        if DBSession.query(PasswordReset).\
            filter(PasswordReset.expiry<datetime.utcnow()).\
            filter(PasswordReset.user_id==user.id).count() >= RESET_LIMIT:
                raise ResetError('Too many active resets currently '
                    'exist for this account')
        self.user_id = user.id
        self.expiry = datetime.utcnow() + timedelta(seconds=RESET_TIMEOUT)
        self.id = os.urandom(self.__table__.c.id.type.length / 2).encode('hex')

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
            raise ValueError('Reset code has expired')
        if user is not self.user:
            raise ValueError('Invalid user for reset code %s' % self.id)
        self.user.password = new_password
        DBSession.query(PasswordReset).\
            filter(PasswordReset.user_id==self.user_id).delete()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    salutation = Column(Unicode(10), nullable=False)
    given_name = Column(Unicode(200), nullable=False)
    surname = Column(Unicode(200), nullable=False)
    organization = Column(Unicode(200), default='', nullable=False)
    _password = Column('password', String(200))
    password_changed = Column(DateTime)
    resets = relationship(
        PasswordReset, backref='user',
        cascade='all, delete-orphan', passive_deletes=True)
    created = Column(DateTime, default=datetime.utcnow, nullable=False)
    _timezone = Column(
        'timezone', Unicode(max(len(t) for t in pytz.all_timezones)),
        default='UTC', nullable=False)
    emails = relationship(
        EmailAddress, backref='user',
        cascade='all, delete-orphan', passive_deletes=True)
    limits_id = Column(
        Unicode(20), ForeignKey(
            'user_limits.id', onupdate='RESTRICT', ondelete='RESTRICT'),
        nullable=False)
    collections = association_proxy(
        'user_collections', 'role',
        creator=lambda k, v: UserCollection(collection=k, role=v))
    # limits defined as backref on UserLimit
    # groups defined as backref on Group

    def __repr__(self):
        return ('<User: name="%s">' % ' '.join((
            self.salutation, self.given_name, self.surname))).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return ' '.join((
            self.salutation, self.given_name, self.surname))

    @classmethod
    def by_id(cls, id):
        """return the user with id ``id``"""
        return DBSession.query(cls).filter_by(id=id).first()

    @property
    def permissions(self):
        """Return a set with all permissions granted to the user"""
        result = set()
        for group in self.groups:
            result = result | set(group.permissions)
        return result

    def _get_timezone(self):
        """Return the timezone object corresponding to the name"""
        return pytz.timezone(self._timezone)

    def _set_timezone(self, value):
        """Set the timezone to the name of the timezone object"""
        if not hasattr(value, 'zone'):
            value = pytz.timezone(value)
        self._timezone = value.zone

    timezone = synonym('_timezone', descriptor=property(_get_timezone, _set_timezone))

    def _set_password(self, password):
        """Store a hashed version of password"""
        self._password = PASSWORD_CONTEXT.encrypt(password)
        self.password_changed = datetime.utcnow()

    def _get_password(self):
        """Return the hashed version of the password"""
        return self._password

    password = synonym('_password', descriptor=property(_get_password, _set_password))

    def test_password(self, password):
        """Check the password against existing credentials"""
        # We call verify_and_update here in case we've defined any new
        # (hopefully stronger) algorithms in the context above. If so, this'll
        # take care of migrating users as they login
        (result, new_password) = PASSWORD_CONTEXT.verify_and_update(password, self.password)
        if result and new_password:
            self._password = new_password
        return result


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
    description = Column(Unicode(200))
    users = relationship(
        User, secondary='user_groups', backref='groups')
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
    description = Column(Unicode(200))
    groups = relationship(
        Group, secondary='group_permissions', backref='permissions')

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
        return ('<SampleImage: sample_id=%d, filename="%s">' % (
            self.sample_id, self.filename)).encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.content

    # XXX Image read, write, and thumb read/write with pgmagick


class Sample(Base):
    __tablename__ = 'samples'

    id = Column(Integer, primary_key=True)
    description = Column(Unicode(200), nullable=False)
    created = Column(DateTime)
    creator_id = Column(Integer, ForeignKey(
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
        'Sample', secondary='sample_origins',
        primaryjoin='sample_origins.c.sample_id==samples.c.id',
        secondaryjoin='sample_origins.c.parent_id==samples.c.id')
    children = relationship(
        'Sample', secondary='sample_origins',
        primaryjoin='sample_origins.c.parent_id==samples.c.id',
        secondaryjoin='sample_origins.c.sample_id==samples.c.id')
    images = relationship(
        SampleImage, backref='sample',
        cascade='all, delete-orphan', passive_deletes=True)
    audits = relationship(
        SampleAudit, backref='sample',
        cascade='all, delete-orphan', passive_deletes=True)

    def __repr__(self):
        return ('<Sample: description="%s">' % self.description).encode('utf-8')

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
    users = association_proxy(
        'collection_users', 'role',
        creator=lambda k, v: UserCollection(user=k, role=v))

    def __repr__(self):
        return ('<Collection: name="%s">' % self.name).encode('utf-8')

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
    description = Column(Unicode(200), nullable=False)
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


class UserCollection(Base):
    __tablename__ = 'user_collections'

    user_id = Column(Integer, ForeignKey(
        'users.id', onupdate='RESTRICT', ondelete='CASCADE'),
        primary_key=True)
    collection_id = Column(Integer, ForeignKey(
        'collections.id', onupdate='RESTRICT', ondelete='CASCADE'),
        primary_key=True)
    role_id = Column(Unicode(20), ForeignKey(
        'roles.id', onupdate='RESTRICT', ondelete='RESTRICT'),
        nullable=False)
    user = relationship(
        User, backref=backref(
            'user_collections',
            collection_class=attribute_mapped_collection('collection')))
    collection = relationship(
        Collection, backref=backref(
            'collection_users',
            collection_class=attribute_mapped_collection('user')))
    role = relationship(Role)


class GroupPermission(Base):
    __tablename__ = 'group_permissions'

    group_id = Column(
        Unicode(20), ForeignKey(
            'groups.id', onupdate='RESTRICT', ondelete='CASCADE'),
        primary_key=True)
    permission_id = Column(
        Unicode(20), ForeignKey(
            'permissions.id', onupdate='RESTRICT', ondelete='RESTRICT'),
        primary_key=True)


class UserGroup(Base):
    __tablename__ = 'user_groups'

    user_id = Column(
        Integer, ForeignKey(
            'users.id', onupdate='RESTRICT', ondelete='CASCADE'),
        primary_key=True)
    group_id = Column(
        Unicode(20), ForeignKey(
            'groups.id', onupdate='RESTRICT', ondelete='RESTRICT'),
        primary_key=True)


class SampleOrigin(Base):
    __tablename__ = 'sample_origins'

    sample_id = Column(
        Integer, ForeignKey(
            'samples.id', onupdate='RESTRICT', ondelete='CASCADE'),
        primary_key=True)
    parent_id = Column(
        Integer, ForeignKey(
            'samples.id', onupdate='RESTRICT', ondelete='CASCADE'),
        primary_key=True)
