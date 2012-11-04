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

import logging

from webhelpers.html import tags
from webhelpers.html.builder import HTML
from formencode import Schema, validators
from pyramid.events import NewRequest, subscriber
from pyramid.httpexceptions import HTTPForbidden
import pyramid_simpleform
import pyramid_simpleform.renderers


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


@subscriber(NewRequest)
def csrf_validation(event):
    if event.request.method == 'POST':
        logging.debug('Checking CSRF token')
        token = event.request.POST.get('_csrf')
        if token is None or token != event.request.session.get_csrf_token():
            raise HTTPForbidden('CSRF token is missing or invalid')
        logging.debug('CSRF token is valid')


class BaseSchema(Schema):
    filter_extra_fields = True
    allow_extra_fields = True


class Form(pyramid_simpleform.Form):
    pass


class FormRenderer(pyramid_simpleform.renderers.FormRenderer):
    def begin(self, url=None, **attrs):
        self._csrf_done = False
        return super(FormRenderer, self).begin(url, **attrs)

    def end(self):
        if not self._csrf_done:
            logging.debug('Forcing inclusion of CSRF token')
            return self.csrf_token() + super(FormRenderer, self).end()
        return super(FormRenderer, self).end()

    def csrf(self, name=None):
        result = super(FormRenderer, self).csrf(name)
        self._csrf_done = True
        return result

    def select(self, name, options=None, selected_value=None, id=None, **attrs):
        if options is None:
            validator = self.form.schema.fields[name]
            assert isinstance(validator, validators.OneOf)
            options = validator.list
        return super(FormRenderer, self).select(name, options, selected_value, id, **attrs)

    def text(self, name, value=None, id=None, **attrs):
        if name in self.form.schema.fields:
            validator = self.form.schema.fields[name]
            if isinstance(validator, validators.FancyValidator) and validator.not_empty:
                attrs['required'] = 'required'
            if isinstance(validator, validators.String) and validator.max is not None:
                attrs['maxlength'] = validator.max
        return super(FormRenderer, self).text(name, value, id, **attrs)

    def email(self, name, value=None, id=None, **attrs):
        if 'type' not in attrs:
            attrs['type'] = 'email'
        return self.text(name, value, id, **attrs)

    def submit(self, name='submit', value='Submit', id=None, **attrs):
        if not 'class_' in attrs:
            attrs['class_'] = 'small button right'
        return super(FormRenderer, self).submit(name, value, id, **attrs)

    def label(self, name, label=None, **attrs):
        if 'class_' not in attrs:
            attrs['class_'] = 'inline'
        return super(FormRenderer, self).label(name, label, **attrs)

    def errorlist(self, name=None, **attrs):
        return self.error_flashes(name, **attrs)

    def error_flashes(self, name=None, **attrs):
        if name is None:
            errors = self.all_errors()
        else:
            errors = self.errors_for(name)
        content = [
            HTML.div(error, class_='alert-box alert', **attrs)
            for error in errors]
        return HTML(*content)

    def error_small(self, name=None, **attrs):
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
        class_ = 'error'
        if 'cols' in attrs:
            class_ = 'error %s' % COL_NAMES[attrs['cols']]
            del attrs['cols']
        return HTML.tag('small', *content, class_=class_, **attrs)

    def column(self, name, content, cols, errors=True):
        error_content = ''
        if errors:
            error_content = self.error_small(name, cols=cols)
        return HTML.tag(
            'div', tags.literal(content), error_content,
            class_='%s columns %s' % (
                COL_NAMES[cols],
                'error' if error_content else ''))

    def col_label(self, name, label=None, errors=True, cols=2, **attrs):
        return self.column(name, self.label(name, label, **attrs), cols, errors=False)

    def col_select(self, name, options=None, selected_value=None, id=None, errors=True, cols=10, **attrs):
        return self.column(name, self.select(name, options, selected_value, id, **attrs), cols, errors)

    def col_text(self, name, value=None, id=None, errors=True, cols=10, **attrs):
        return self.column(name, self.text(name, value, id, **attrs), cols, errors)

    def col_email(self, name, value=None, id=None, errors=True, cols=10, **attrs):
        return self.column(name, self.email(name, value, id, **attrs), cols, errors)

    def col_password(self, name, value=None, id=None, errors=True, cols=10, **attrs):
        return self.column(name, self.password(name, value, id, **attrs), cols, errors)

    def col_submit(self, name='submit', value='Submit', id=None, cols=12, **attrs):
        return self.column(name, self.submit(name, value, id, **attrs), cols, errors=False)

