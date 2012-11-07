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

import logging

import pytz
from webhelpers.html import tags
from webhelpers.html.builder import HTML
from formencode import (
    FancyValidator,
    Schema,
    Invalid,
    validators,
    variabledecode,
    )
from pyramid.events import NewRequest, subscriber
from pyramid.httpexceptions import HTTPForbidden
import pyramid_simpleform
import pyramid_simpleform.renderers

from samplesdb.models import EmailAddress, User, Collection, Role
from samplesdb.security import (
    OWNER_ROLE,
    EDITOR_ROLE,
    AUDITOR_ROLE,
    VIEWER_ROLE,
    )


COL_NAMES = {
    1:  'one',
    2:  'two',
    3:  'three',
    4:  'four',
    5:  'five',
    6:  'six',
    7:  'seven',
    8:  'eight',
    9:  'nine',
    10: 'ten',
    11: 'eleven',
    12: 'twelve',
}


def css_add_class(attrs, cls):
    "Add CSS class ``cls'' to element attributes ``attrs''"
    css_classes = set(attrs.get('class_', '').split())
    css_classes.add(cls)
    result = attrs.copy()
    result['class_'] = ' '.join(css_classes)
    return result


def css_del_class(attrs, cls):
    "Remove CSS class ``cls'' from element attributes ``attrs''"
    css_classes = set(attrs.get('class_', ).split())
    if cls in css_classes:
        css_classes.remove(cls)
    result = attrs.copy()
    if 'class_' in result:
        del result['class_']
    if css_classes:
        result['class_'] = ' '.join(css_classes)
    return result


@subscriber(NewRequest)
def csrf_validation(event):
    if event.request.method == 'POST':
        logging.debug('Checking CSRF token')
        token = event.request.POST.get('_csrf')
        if token is None or token != event.request.session.get_csrf_token():
            logging.debug('CSRF TOKEN IS INVALID!')
            raise HTTPForbidden('CSRF token is missing or invalid')
        logging.debug('CSRF token is valid')


class BaseSchema(Schema):
    filter_extra_fields = True
    allow_extra_fields = True


class Form(pyramid_simpleform.Form):
    "A refinement of Form to make decoded form variables accessible"

    def validate(self):
        super(Form, self).validate()
        if self.method == 'POST':
            params = self.request.POST
        else:
            params = self.request.params

        if self.variable_decode:
            self.data_decoded = variabledecode.variable_decode(
                    params, self.dict_char, self.list_char)
        else:
            self.data_decoded = params


class FormRenderer(pyramid_simpleform.renderers.FormRenderer):
    "A refinement of FormRenderer with additions for Foundation columns"

    def __init__(self, form, csrf_field='_csrf'):
        super(FormRenderer, self).__init__(form, csrf_field)
        self.data_decoded = form.data_decoded

    def begin(self, url=None, **attrs):
        "Returns the opening tag for an HTML form"
        self._csrf_done = False
        return super(FormRenderer, self).begin(url, **attrs)

    def end(self):
        "Returns the closing tag for an HTML form"
        if not self._csrf_done:
            logging.debug('Forcing inclusion of CSRF token')
            return self.csrf_token() + super(FormRenderer, self).end()
        return super(FormRenderer, self).end()

    def csrf(self, name=None):
        "Returns the hidden Cross-Site Request Forgery input element"
        result = super(FormRenderer, self).csrf(name)
        self._csrf_done = True
        return result

    def select(self, name, options=None, selected_value=None, id=None, **attrs):
        "Returns a select element"
        if options is None:
            validator = self.form.schema.fields[name]
            assert isinstance(validator, validators.OneOf)
            options = validator.list
        return super(FormRenderer, self).select(name, options, selected_value, id, **attrs)

    def text(self, name, value=None, id=None, **attrs):
        "Returns an text input element"
        if name in self.form.schema.fields:
            validator = self.form.schema.fields[name]
            if isinstance(validator, validators.FancyValidator) and validator.not_empty:
                attrs['required'] = 'required'
            if isinstance(validator, validators.String) and validator.max is not None:
                attrs['maxlength'] = validator.max
        return super(FormRenderer, self).text(name, value, id, **attrs)

    def email(self, name, value=None, id=None, **attrs):
        "Returns an email input element"
        if 'type' not in attrs:
            attrs['type'] = 'email'
        return self.text(name, value, id, **attrs)

    def submit(self, name='submit', value='Submit', id=None, **attrs):
        "Returns a form submit button"
        if not 'class_' in attrs:
            attrs['class_'] = 'small button right'
        return super(FormRenderer, self).submit(name, value, id, **attrs)

    def label(self, name, label=None, **attrs):
        "Returns a form label element"
        if 'class_' not in attrs:
            attrs['class_'] = 'inline'
        return super(FormRenderer, self).label(name, label, **attrs)

    def errorlist(self, name=None, **attrs):
        "Returns the list of current form errors"
        return self.error_flashes(name, **attrs)

    def error_flashes(self, name=None, **attrs):
        "Returns the list of specified errors as Foundation flashes"
        if name is None:
            errors = self.all_errors()
        else:
            errors = self.errors_for(name)
        content = [
            HTML.div(error, class_='alert-box alert', **attrs)
            for error in errors]
        return HTML(*content)

    def error_small(self, name=None, cols=None, **attrs):
        "Returns the list of specified errors as Foundation form attachments"
        if name is None:
            errors = self.all_errors()
        else:
            errors = self.errors_for(name)
        if not errors:
            return ''
        content = []
        for error in errors:
            content.append(HTML(error))
            content.append(tags.BR)
        content = content[:-1]
        attrs = css_add_class(attrs, 'error')
        if cols:
            attrs = css_add_class(attrs, COL_NAMES[cols])
        return HTML.tag('small', *content, **attrs)

    def column(self, name, content, cols, inner_cols=None, errors=True):
        "Wraps content in a Foundation column"
        error_content = ''
        if errors:
            error_content = self.error_small(name, cols=inner_cols)
        return HTML.tag(
            'div', tags.literal(content), error_content,
            class_='%s columns %s' % (
                COL_NAMES[cols], 'error' if error_content else ''))

    def col_label(
            self, name, label=None, errors=True, cols=2, inner_cols=None,
            **attrs):
        "Return a form label within a column"
        if inner_cols:
            attrs = css_add_class(attrs, COL_NAMES[inner_cols])
        return self.column(
            name, self.label(name, label, **attrs),
            cols, inner_cols, errors=False)

    def col_select(
            self, name, options=None, selected_value=None, id=None,
            errors=True, cols=10, inner_cols=None, **attrs):
        "Return a select element within a column"
        if inner_cols:
            attrs = css_add_class(attrs, COL_NAMES[inner_cols])
        return self.column(
            name, self.select(name, options, selected_value, id, **attrs),
            cols, inner_cols, errors)

    def col_text(
            self, name, value=None, id=None,
            errors=True, cols=10, inner_cols=None, **attrs):
        "Return a text input within a column"
        if inner_cols:
            attrs = css_add_class(attrs, COL_NAMES[inner_cols])
        return self.column(
            name, self.text(name, value, id, **attrs),
            cols, inner_cols, errors)

    def col_email(
            self, name, value=None, id=None,
            errors=True, cols=10, inner_cols=None, **attrs):
        "Return an email input within a column"
        if inner_cols:
            attrs = css_add_class(attrs, COL_NAMES[inner_cols])
        return self.column(
            name, self.email(name, value, id, **attrs),
            cols, inner_cols, errors)

    def col_password(
            self, name, value=None, id=None,
            errors=True, cols=10, inner_cols=None, **attrs):
        "Return a password input within a column"
        if inner_cols:
            attrs = css_add_class(attrs, COL_NAMES[inner_cols])
        return self.column(
            name, self.password(name, value, id, **attrs),
            cols, inner_cols, errors)

    def col_submit(
            self, name='submit', value='Submit', id=None,
            cols=12, inner_cols=None, **attrs):
        "Return a submit button within a column"
        if inner_cols:
            attrs = css_add_class(attrs, COL_NAMES[inner_cols])
        return self.column(
            name, self.submit(name, value, id, **attrs),
            cols, inner_cols, errors=False)


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


class ValidTimezone(validators.OneOf):
    def __init__(self):
        super(ValidTimezone, self).__init__(pytz.all_timezones)


class ValidRole(FancyValidator):
    def _from_python(self, value, state):
        assert isinstance(value, Role)
        return value.id

    def _to_python(self, value, state):
        result = Role.by_id(value.strip())
        if result is None:
            raise Invalid('Invalid role', value, state)
        return result


class ValidUser(FancyValidator):
    def _from_python(self, value, state):
        assert isinstance(value, User)
        return value.verified_emails[0].email

    def _to_python(self, value, state):
        result = User.by_email(value.strip())
        if result is None:
            raise Invalid('No users have address %s' % value, value, state)
        return result


