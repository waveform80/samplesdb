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

from webhelpers.html import tags
from webhelpers.html.builder import HTML
from formencode import validators
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

class FormRenderer(pyramid_simpleform.renderers.FormRenderer):
    def begin(self, url=None, **attrs):
        #attrs['class_'] = attrs.get('class_', '') + ' custom'
        return super(FormRenderer, self).begin(url, **attrs)

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

    def label(self, name, label=None, **attrs):
        if 'class_' not in attrs:
            attrs['class_'] = 'inline'
        return super(FormRenderer, self).label(name, label, **attrs)

    def errorlist(self, name=None, **attrs):
        if name is None:
            errors = self.all_errors()
        else:
            errors = self.errors_for(name)
        if not errors:
            return ''
        if 'class_' not in attrs:
            attrs['class_'] = "error"
        content = []
        for error in errors:
            content.append(tags.escape(error))
            content.append(tags.BR)
        return HTML.tag('small', *content[:-1], **attrs)

    def column(self, name, content, cols, errors=True):
        error_content = ''
        if errors:
            error_content = self.errorlist(name)
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
        if not 'class_' in attrs:
            attrs['class_'] = 'small button right'
        return self.column(name, self.submit(name, value, id, **attrs), cols, errors=False)
