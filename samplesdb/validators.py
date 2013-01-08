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

import csv
from datetime import datetime

import pytz
from formencode import (
    FancyValidator,
    Schema,
    Invalid,
    validators,
    )
from formencode.compound import CompoundValidator
from formencode.foreach import ForEach
from pyramid.threadlocal import get_current_registry

from samplesdb.views import MARKUP_LANGUAGES
from samplesdb.models import (
    EmailAddress,
    UserLimit,
    User,
    Collection,
    Role,
    Sample,
    SampleLogEntry,
    SampleCode,
    )


class BaseSchema(Schema):
    filter_extra_fields = True
    allow_extra_fields = True


class FormSchema(BaseSchema):
    _came_from = validators.UnicodeString()


class SubFormSchema(BaseSchema):
    pass


class ForEachDict(ForEach):
    def __init__(self, *args, **kw):
        super(ForEachDict, self).__init__(*args, **kw)
        self.key_name = kw['key_name']
        self.value_name = kw['value_name']

    def validate_python(self, value, state):
        if not hasattr(value, 'items'):
            if not hasattr(value, 'iteritems'):
                raise Invalid('value is not dict-like', value, state)

    def _to_python(self, value, state):
        value = super(ForEachDict, self)._to_python(value, state)
        result = {}
        try:
            for i, item in enumerate(value):
                try:
                    key = item[self.key_name]
                except KeyError:
                    raise Invalid(
                        'key %s not present in item %d of value' % (
                            self.key_name, i), value, state)
                try:
                    value = item[self.value_name]
                except KeyError:
                    raise Invalid(
                        'key %s not present in item %d of value' % (
                            self.value_name, i), value, state)
                if key in result:
                    raise Invalid(
                        'duplicate key %s found at position %d in value' % (
                            key, i), value, state)
                result[key] = value
        except TypeError:
            raise Invalid('value is not iterable', value, state)
        return result

    def _from_python(self, value, state):
        result = []
        if hasattr(value, 'iteritems'):
            iterator = value.iteritems()
        elif hasattr(value, 'items'):
            iterator = value.items()
        for key, value in iterator:
            result.append({self.key_name: key, self.value_name: value})
        return super(ForEachDict, self)._from_python(result, state)


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



class ValidEmail(validators.Email):
    def __init__(self, not_exist=False, not_empty=True, resolve_domain=True):
        super(ValidEmail, self).__init__(
            not_empty=not_empty, resolve_domain=resolve_domain,
            max=EmailAddress.__table__.c.email.type.length)
        self.not_exist = not_exist

    def _to_python(self, value, state):
        result = super(ValidEmail, self)._to_python(value, state)
        if self.not_exist:
            address = EmailAddress.by_email(result)
            if address:
                raise Invalid(
                    'A user exists with that e-mail address', value, state)
        return result


class ValidCollectionOwner(validators.UnicodeString):
    def __init__(self):
        super(ValidCollectionOwner, self).__init__(
            not_empty=True, max=Collection.__table__.c.owner.type.length)


class ValidCollectionName(validators.UnicodeString):
    def __init__(self):
        super(ValidCollectionName, self).__init__(
            not_empty=True, max=Collection.__table__.c.name.type.length)


class ValidCollectionLicense(validators.OneOf):
    def __init__(self):
        super(ValidCollectionLicense, self).__init__(list=[], hideList=True)

    def validate_python(self, value, state):
        self.list = get_current_registry()['licenses']().keys()
        super(ValidCollectionLicense, self).validate_python(value.id, state)

    def _to_python(self, value, state):
        return get_current_registry()['licenses']()[value]

    def _from_python(self, value, state):
        return value.id


class ValidSampleDescription(validators.UnicodeString):
    def __init__(self):
        super(ValidSampleDescription, self).__init__(
            not_empty=True, max=Sample.__table__.c.description.type.length)


class ValidSampleLocation(validators.UnicodeString):
    def __init__(self):
        super(ValidSampleLocation, self).__init__(
            not_empty=False, max=Sample.__table__.c.location.type.length)


class ValidSampleAliquots(validators.Int):
    def __init__(self):
        super(ValidSampleAliquots, self).__init__(
            not_empty=True, min=2, max=1000)


class ValidSampleAliquant(validators.Bool):
    pass


class ValidSampleNotes(validators.UnicodeString):
    def __init__(self):
        super(ValidSampleNotes, self).__init__(not_empty=False)


class ValidCodeName(validators.UnicodeString):
    def __init__(self):
        super(ValidCodeName, self).__init__(
            not_empty=True, max=SampleCode.__table__.c.name.type.length)


class ValidCodeValue(validators.UnicodeString):
    def __init__(self):
        super(ValidCodeValue, self).__init__(
            not_empty=True, max=SampleCode.__table__.c.value.type.length)


class ValidLogMessage(validators.UnicodeString):
    def __init__(self):
        super(ValidLogMessage, self).__init__(
            not_empty=False, max=SampleLogEntry.__table__.c.message.type.length)


class ValidTimezone(validators.OneOf):
    def __init__(self):
        super(ValidTimezone, self).__init__(pytz.all_timezones)


class ValidMarkupLanguage(validators.OneOf):
    def __init__(self):
        super(ValidMarkupLanguage, self).__init__(MARKUP_LANGUAGES.keys())


class ValidDateTimeFormat(FancyValidator):
    def __init__(self):
        super(ValidDateTimeFormat, self).__init__(not_empty=True, strip=True)

    def validate_python(self, value, state):
        try:
            datetime(2000, 1, 1).strftime(value)
        except ValueError, e:
            raise Invalid(str(e), value, state)


class ValidAccountType(FancyValidator):
    def __init__(self):
        super(ValidAccountType, self).__init__(not_empty=True, strip=True)

    def validate_python(self, value, state):
        if not isinstance(value, UserLimit):
            raise Invalid('value is not a UserLimit', value, state)

    def _from_python(self, value, state):
        return value.id

    def _to_python(self, value, state):
        result = UserLimit.by_id(value)
        if result is None:
            raise Invalid('Invalid account type', value, state)
        return result


class ValidEmailForAccountType(validators.FormValidator):
    error_msg = 'E-mail address is not valid for the selected account type'
    # Name of the field containing the account-type id
    account_type_field = None
    # Name of the field containing the e-mail address
    email_address_field = None

    __unpackargs__ = ('account_type_field', 'email_address_field')

    def validate_python(self, value_dict, state):
        account_type = value_dict.get(self.account_type_field)
        email_address = value_dict.get(self.email_address_field)
        if not account_type.email_pattern.match(email_address):
            raise Invalid(
                self.error_msg, value_dict, state, error_dict={
                    self.email_address_field: self.error_msg})


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


class ValidExportFormat(validators.OneOf):
    def __init__(self):
        super(ValidExportFormat, self).__init__(['csv', 'excel'])


class ValidExportColumns(validators.Set):
    def __init__(self):
        super(ValidExportColumns, self).__init__(not_empty=True)


class ValidCsvDelimiter(validators.OneOf):
    def __init__(self):
        super(ValidCsvDelimiter, self).__init__(['comma', 'semi-colon', 'space', 'tab'])


class ValidCsvQuoteChar(validators.OneOf):
    def __init__(self):
        super(ValidCsvQuoteChar, self).__init__(['single', 'double'])


class ValidCsvQuoting(validators.OneOf):
    def __init__(self):
        super(ValidCsvQuoting, self).__init__(['all', 'minimal', 'non-numeric', 'none'])


class ValidCsvDoubleQuotes(validators.Bool):
    pass


class ValidCsvLineTerminator(validators.OneOf):
    def __init__(self):
        super(ValidCsvLineTerminator, self).__init__(['dos', 'unix', 'max'])

