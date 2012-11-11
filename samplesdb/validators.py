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

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import pytz
from formencode import (
    FancyValidator,
    Schema,
    Invalid,
    validators,
    )

from samplesdb.models import EmailAddress, User, Collection, Role, Sample


class BaseSchema(Schema):
    filter_extra_fields = True
    allow_extra_fields = True


# The following classes define validators for each of the fields in the
# database that frequently appear on forms within the application. Centralizing
# the attributes of these validators simplifies maintenance and also makes the
# form schemas considerably less cluttered


class ValidSalutation(validators.OneOf):
    def __init__(self):
        super(ValidSalutation, self).__init__([
            'Mr.', 'Mrs.', 'Miss', 'Ms.', 'Dr.', 'Prof.'])


class ValidGivenName(validators.UnicodeString):
    def __init__(self):
        super(ValidGivenName, self).__init__(
            not_empty=True, max=User.__table__.c.given_name.type.length)


class ValidSurname(validators.UnicodeString):
    def __init__(self):
        super(ValidSurname, self).__init__(
            not_empty=True, max=User.__table__.c.surname.type.length)


class ValidOrganization(validators.UnicodeString):
    def __init__(self):
        super(ValidOrganization, self).__init__(
            max=User.__table__.c.organization.type.length)


class ValidPassword(validators.UnicodeString):
    def __init__(self, not_empty=True):
        super(ValidPassword, self).__init__(not_empty=not_empty, max=100)



class ValidAccountType(validators.OneOf):
    def __init__(self):
        super(ValidAccountType, self).__init__(['academic', 'commercial'])


class ValidEmail(validators.Email):
    def __init__(self, not_empty=True, resolve_domain=True):
        super(ValidEmail, self).__init__(
            not_empty=not_empty, resolve_domain=resolve_domain,
            max=EmailAddress.__table__.c.email.type.length)


class ValidCollectionName(validators.UnicodeString):
    def __init__(self):
        super(ValidCollectionName, self).__init__(
            not_empty=True, max=Collection.__table__.c.name.type.length)


class ValidSampleDescription(validators.UnicodeString):
    def __init__(self):
        super(ValidSampleDescription, self).__init__(
            not_empty=True, max=Sample.__table__.c.description.type.length)


class ValidSampleLocation(validators.UnicodeString):
    def __init__(self):
        super(ValidSampleLocation, self).__init__(
            not_empty=False, max=Sample.__table__.c.location.type.length)


class ValidSampleNotes(validators.UnicodeString):
    def __init__(self):
        super(ValidSampleNotes, self).__init__(not_empty=False)


class ValidTimezone(validators.OneOf):
    def __init__(self):
        super(ValidTimezone, self).__init__(pytz.all_timezones)


class ValidRole(FancyValidator):
    def __init__(self):
        super(ValidRole, self).__init__(not_empty=True, strip=True)

    def validate_python(self, value, state):
        if not isinstance(value, Role):
            raise Invalid('value is not a Role', value, state)

    def _from_python(self, value, state):
        return value.id

    def _to_python(self, value, state):
        result = Role.by_id(value)
        if result is None:
            raise Invalid('Invalid role', value, state)
        return result


class ValidUser(FancyValidator):
    def __init__(self, not_empty=True):
        super(ValidUser, self).__init__(not_empty=not_empty, strip=True)

    def validate_python(self, value, state):
        if not isinstance(value, User):
            raise Invalid('value is not a User', value, state)

    def _from_python(self, value, state):
        return value.verified_emails[0].email

    def _to_python(self, value, state):
        result = User.by_email(value)
        if result is None:
            raise Invalid('No users have address %s' % value, value, state)
        return result


class ValidCollection(FancyValidator):
    def __init__(self):
        super(ValidCollection, self).__init__(not_empty=True)

    def validate_python(self, value, state):
        if not isinstance(value, Collection):
            raise Invalid('value is not a Collection', value, state)

    def _from_python(self, value, state):
        return value.id

    def _to_python(self, value, state):
        result = Collection.by_id(value)
        if result is None:
            raise Invalid('Invalid collection', value, state)
        return result


class ValidSample(FancyValidator):
    def __init__(self):
        super(ValidSample, self).__init__(not_empty=True)

    def validate_python(self, value, state):
        if not isinstance(value, Sample):
            raise Invalid('value is not a Sample', value, state)

    def _from_python(self, value, state):
        return value.id

    def _to_python(self, value, state):
        result = Sample.by_id(value)
        if result is None:
            raise Invalid('Invalid collection', value, state)
        return result


