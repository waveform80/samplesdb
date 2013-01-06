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

"""Implements an extended version of pyramid_simpleform.

This module extends the pyramid_simpleform package to support bi-directional
transcoding of values with formencode's validators (using from_python as well
as to_python), and the Foundation Grid being used for horizontal layout of form
controls.
"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import logging

from webhelpers.html import tags
from webhelpers.html.builder import HTML, literal
from pyramid.i18n import get_localizer
from pyramid.renderers import render
from formencode import (
    FancyValidator,
    Schema,
    Invalid,
    htmlfill,
    validators,
    variabledecode,
    )
from pyramid.events import NewRequest, subscriber
from pyramid.httpexceptions import HTTPForbidden


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


class State(object):
    """
    Default "empty" state object.

    Keyword arguments are automatically bound to properties, for
    example::

        obj = State(foo="bar")
        obj.foo == "bar"
    """

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __contains__(self, k):
        return hasattr(self, k)

    def __getitem__(self, k):
        try:
            return getattr(self, k)
        except AttributeError:
            raise KeyError

    def __setitem__(self, k, v):
        setattr(self, k, v)

    def get(self, k, default=None):
        return getattr(self, k, default)


class Form(object):
    """
    Represents an HTML form with formencode based schemas.

    `request` : Pyramid request instance

    `schema`  : FormEncode Schema class or instance

    `validators` : a dict of FormEncode validators i.e. { field : validator }

    `defaults`   : a dict of default values

    `obj`        : instance of an object (e.g. SQLAlchemy model)

    `state`      : state passed to FormEncode validators.

    `method`        : HTTP method

    `variable_decode` : will decode dict/lists

    `dict_char`       : variabledecode dict char

    `list_char`       : variabledecode list char

    Also note that values of ``obj`` supercede those of ``defaults``. Only
    fields specified in your schema or validators will be taken from the
    object.
    """

    default_state = State

    def __init__(
            self, request, schema=None, validators=None, defaults=None,
            obj=None, extra=None, include=None, exclude=None, state=None,
            method='POST', variable_decode=False, dict_char='.',
            list_char='-', multipart=False, came_from=None):

        self.request = request
        self.schema = schema
        self.validators = validators or {}
        self.method = method
        self.variable_decode = variable_decode
        self.dict_char = dict_char
        self.list_char = list_char
        self.multipart = multipart
        self.came_from = came_from
        self.state = state
        self.is_validated = False
        self.errors = {}
        self.data = {}
        if self.state is None:
            self.state = self.default_state()
        if not hasattr(self.state, '_'):
            self.state._ = get_localizer(self.request).translate
        if self.came_from is None:
            self.came_from = self.request.referer
        if defaults:
            self.data.update(defaults)
        if obj:
            if not self.schema:
                raise ValueError(
                    'You must specify a schema to read an obj for values')
            if self.schema:
                for f in self.schema.fields.keys():
                    if hasattr(obj, f):
                        self.data[f] = self.schema.fields[f].from_python(getattr(obj, f))
            if self.validators:
                fields = set(self.validators.keys())
                if self.schema:
                    fields -= set(self.schema.fields.keys())
                for f in fields:
                    if hasattr(obj, f):
                        self.data[f] = self.validators[f].from_python(getattr(obj, f))
        self.data_raw = self.data.copy()

    def is_error(self, field):
        """Checks if individual field has errors."""
        return field in self.errors

    def all_errors(self):
        """Returns all errors in a single list."""
        if isinstance(self.errors, basestring):
            return [self.errors]
        if isinstance(self.errors, list):
            return self.errors
        errors = []
        for field in self.errors.iterkeys():
            errors += self.errors_for(field)
        return errors

    def errors_for(self, field):
        """Returns any errors for a given field as a list."""
        errors = self.errors.get(field, [])
        if isinstance(errors, basestring):
            errors = [errors]
        return errors

    def validate(self):
        """
        Runs validation and returns True/False whether form is valid.

        This will check if the form should be validated (i.e. the request
        method matches) and the schema/validators validate.

        Validation will only be run once; subsequent calls to validate() will
        have no effect, i.e. will just return the original result.

        The errors and data values will be updated accordingly.
        """
        assert self.schema or self.validators
        if self.is_validated:
            return not(self.errors)
        if self.method and self.method != self.request.method:
            return False
        if self.method == 'POST':
            params = self.request.POST.mixed()
        else:
            params = self.request.params.mixed()
        if self.variable_decode:
            self.data_raw = variabledecode.variable_decode(
                params, self.dict_char, self.list_char)
        else:
            self.data_raw = params
        self.data.update(params)
        if self.schema:
            try:
                self.data = self.schema.to_python(
                    self.data_raw, self.state)
            except Invalid, e:
                self.errors = e.unpack_errors(
                    self.variable_decode, self.dict_char, self.list_char)
        if self.validators:
            for field, validator in self.validators.iteritems():
                try:
                    self.data[field] = validator.to_python(
                        self.data_raw.get(field), self.state)
                except Invalid, e:
                    self.errors[field] = unicode(e)
        # XXX This is a tad dirty - how do we know the field is called _came_from here?
        self.came_from = self.data.get('_came_from', self.came_from)
        self.is_validated = True
        return not(self.errors)

    def bind(self, obj, include=None, exclude=None):
        """
        Binds validated field values to an object instance, for example a
        SQLAlchemy model instance.

        `include` : list of included fields. If field not in this list it will
        not be bound to this object.

        `exclude` : list of excluded fields. If field is in this list it will
        not be bound to the object.

        Returns the `obj` passed in.

        Note that any properties starting with underscore "_" are ignored
        regardless of ``include`` and ``exclude``. If you need to set these
        do so manually from the ``data`` property of the form instance.

        Calling bind() before running validate() will result in a RuntimeError
        """
        if not self.is_validated:
            raise RuntimeError(
                'Form has not been validated. Call validate() first')
        if self.errors:
            raise RuntimeError('Cannot bind to object if form has errors')
        items = [(k, v) for k, v in self.data.items() if not k.startswith("_")]
        for k, v in items:
            if include and k not in include:
                continue
            if exclude and k in exclude:
                continue
            setattr(obj, k, v)
        return obj

    def htmlfill(self, content, **htmlfill_kwargs):
        """Runs FormEncode **htmlfill** on content."""
        charset = getattr(self.request, 'charset', 'utf-8')
        htmlfill_kwargs.setdefault('encoding', charset)
        return htmlfill.render(
            content, defaults=self.data, errors=self.errors, **htmlfill_kwargs)

    def render(self, template, extra_info=None, htmlfill=True,
              **htmlfill_kwargs):
        """
        Renders the form directly to a template, using Pyramid's **render**
        function.

        `template` : name of template

        `extra_info` : dict of extra data to pass to template

        `htmlfill` : run htmlfill on the result.

        By default the form itself will be passed in as `form`.

        htmlfill is automatically run on the result of render if `htmlfill` is
        **True**.

        This is useful if you want to use htmlfill on a form, but still return
        a dict from a view. For example::

            @view_config(name='submit', request_method='POST')
            def submit(request):

                form = Form(request, MySchema)
                if form.validate():
                    # do something
                return dict(form=form.render("my_form.html"))
        """
        extra_info = extra_info or {}
        extra_info.setdefault('form', self)
        result = render(template, extra_info, self.request)
        if htmlfill:
            result = self.htmlfill(result, **htmlfill_kwargs)
        return result


class FormRenderer(object):
    """
    A simple form helper. Uses WebHelpers to render individual form widgets:
    see the WebHelpers library for more information on individual widgets.
    """

    def __init__(self, form, csrf_field='_csrf', came_from_field='_came_from'):
        self.form = form
        self.data = self.form.data
        self.data_raw = self.form.data_raw
        self.csrf_field = csrf_field
        self.came_from_field = came_from_field
        self._csrf_done = False
        self._came_from_done = False

    def value(self, name, default=None):
        return self.data.get(name, default)

    def column(self, name, content, cols, inner_cols=None, errors=True):
        "Wraps content in a Foundation column"
        error_content = ''
        if errors:
            error_content = self.error_small(name, cols=inner_cols)
        return HTML.tag(
            'div', tags.literal(content), error_content,
            class_='%s columns %s' % (
                COL_NAMES[cols], 'error' if error_content else ''))

    def begin(self, url=None, **attrs):
        """
        Creates the opening <form> tags.

        By default URL will be current path.
        """
        self._csrf_done = False
        url = url or self.form.request.path
        multipart = attrs.pop('multipart', self.form.multipart)
        return tags.form(url, multipart=multipart, **attrs)

    def end(self):
        """
        Closes the form, i.e. outputs </form>.
        """
        return self.hidden_tag() + tags.end_form()

    def csrf(self, name=None):
        """
        Returns the CSRF hidden input. Creates new CSRF token if none has been
        assigned yet.

        The name of the hidden field is **_csrf** by default.
        """
        name = name or self.csrf_field
        token = self.form.request.session.get_csrf_token()
        if token is None:
            token = self.form.request.session.new_csrf_token()
        self._csrf_done = True
        return self.hidden(name, value=token)

    def came_from(self, name=None):
        """
        Returns the referral hidden input. Gets the referrer from the form data
        or the request if the form lacks it.

        The name of the hidden field is **_came_from** by default
        """
        name = name or self.came_from_field
        url = self.form.came_from
        self._came_from_done = True
        return self.hidden(name, value=url)

    def hidden_tag(self, *names):
        """
        Convenience for printing all hidden fields in a form inside a hidden
        DIV. Will also render the CSRF and referal hidden fields if they
        haven't been output explicitly already.

        :versionadded: 0.4
        """
        inputs = [self.hidden(name) for name in names]
        if not self._csrf_done:
            inputs.append(self.csrf())
        if not self._came_from_done:
            inputs.append(self.came_from())
        return HTML.tag(
            'div', tags.literal(''.join(inputs)), style='display:none;')

    def hidden(self, name, value=None, id=None, **attrs):
        """
        Outputs hidden input.
        """
        id = id or name
        return tags.hidden(name, self.value(name, value), id, **attrs)

    def label(self, name, label=None, cols=2, inner_cols=None, **attrs):
        """
        Outputs a <label> element.

        `name`  : field name. Automatically added to "for" attribute.

        `label` : if **None**, uses the capitalized field name.
        """
        if 'for_' not in attrs:
            attrs['for_'] = name
        label = label if label is not None else name.capitalize()
        if inner_cols:
            attrs = css_add_class(attrs, COL_NAMES[inner_cols])
        result = HTML.tag('label', label, **attrs)
        if cols:
            return self.column(name, result, cols, inner_cols, errors=False)
        else:
            return result

    def text(
            self, name, value=None, id=None,
            cols=10, inner_cols=None, errors=True, **attrs):
        """
        Outputs text input.
        """
        id = id or name
        if name in self.form.schema.fields:
            validator = self.form.schema.fields[name]
            if (
                    isinstance(validator, validators.FancyValidator) and
                    validator.not_empty and
                    not 'required' in attrs):
                attrs['required'] = 'required'
            if (
                    isinstance(validator, validators.String) and
                    validator.max is not None and
                    not 'maxlength' in attrs):
                attrs['maxlength'] = validator.max
        if inner_cols:
            attrs = css_add_class(attrs, COL_NAMES[inner_cols])
        result = tags.text(name, self.value(name, value), id, **attrs)
        if cols:
            return self.column(name, result, cols, inner_cols, errors)
        else:
            return result

    def email(
            self, name, value=None, id=None,
            cols=10, inner_cols=None, errors=True, **attrs):
        """
        Outputs email input.
        """
        if 'type' not in attrs:
            attrs['type'] = 'email'
        return self.text(name, value, id, cols, inner_cols, errors, **attrs)

    def number(
            self, name, value=None, id=None,
            cols=10, inner_cols=None, errors=True, **attrs):
        """
        Outputs a number-spinbox input.
        """
        if 'type' not in attrs:
            attrs['type'] = 'number'
        if name in self.form.schema.fields:
            validator = self.form.schema.fields[name]
            if isinstance(validator, validators.RangeValidator):
                if validator.min is not None and not 'min' in attrs:
                    attrs['min'] = validator.min
                if validator.max is not None and not 'max' in attrs:
                    attrs['max'] = validator.max
        return self.text(name, value, id, cols, inner_cols, errors, **attrs)

    def file(
            self, name, value=None, id=None,
            cols=10, inner_cols=None, errors=True, **attrs):
        """
        Outputs file input.
        """
        id = id or name
        if inner_cols:
            attrs = css_add_class(attrs, COL_NAMES[inner_cols])
        result = tags.file(name, self.value(name, value), id, **attrs)
        if cols:
            return self.column(name, result, cols, inner_cols, errors)
        else:
            return result

    def password(
            self, name, value=None, id=None,
            cols=10, inner_cols=None, errors=True, **attrs):
        """
        Outputs a password input.
        """
        id = id or name
        if inner_cols:
            attrs = css_add_class(attrs, COL_NAMES[inner_cols])
        result = tags.password(name, self.value(name, value), id, **attrs)
        if cols:
            return self.column(name, result, cols, inner_cols, errors)
        else:
            return result

    def textarea(
            self, name, content="", id=None,
            cols=10, inner_cols=None, errors=True, **attrs):
        """
        Outputs <textarea> element.
        """
        id = id or name
        if inner_cols:
            attrs = css_add_class(attrs, COL_NAMES[inner_cols])
        result = tags.textarea(name, self.value(name, content), id, **attrs)
        if cols:
            return self.column(name, result, cols, inner_cols, errors=False)
        else:
            return result

    def select(
            self, name, options=None, selected_value=None, id=None,
            cols=10, inner_cols=None, errors=True, **attrs):
        """
        Outputs <select> element.
        """
        id = id or name
        if options is None:
            validator = self.form.schema.fields[name]
            assert isinstance(validator, validators.OneOf)
            options = validator.list
        if inner_cols:
            attrs = css_add_class(attrs, COL_NAMES[inner_cols])
        result = tags.select(
            name, self.value(name, selected_value), options, id, **attrs)
        if cols:
            return self.column(name, result, cols, inner_cols, errors)
        else:
            return result

    def radio(self, name, value=None, checked=False, label=None, **attrs):
        """
        Outputs radio input.
        """
        checked = self.data.get(name) == value or checked
        return tags.radio(name, value, checked, label, **attrs)

    def checkbox(
            self, name, value='1', checked=False, label=None, id=None, **attrs):
        """
        Outputs checkbox input.
        """
        id = id or name
        return tags.checkbox(name, value, self.value(name), label, id, **attrs)

    def submit(
            self, name='submit', value='Submit', id=None,
            cols=10, inner_cols=None, cancel=True, **attrs):
        """
        Outputs submit button.
        """
        id = id or name
        attrs = css_add_class(attrs, 'button')
        if inner_cols:
            attrs = css_add_class(attrs, COL_NAMES[inner_cols])
        result = tags.submit(name, self.value(name, value), id, **attrs)
        if cancel and self.form.came_from:
            cancel_attrs = attrs.copy()
            cancel_attrs = css_add_class(cancel_attrs, 'secondary')
            result += literal(' ') + HTML.a(
                'Cancel', href=self.form.came_from, **cancel_attrs)
        if cols:
            return self.column(name, result, cols, inner_cols, errors=False)
        else:
            return result

    def is_error(self, name):
        """
        Shortcut for **self.form.is_error(name)**
        """
        return self.form.is_error(name)

    def errors_for(self, name):
        """
        Shortcut for **self.form.errors_for(name)**
        """
        return self.form.errors_for(name)

    def all_errors(self):
        """
        Shortcut for **self.form.all_errors()**
        """
        return self.form.all_errors()

    def errorlist(self, name=None, **attrs):
        """
        Shortcut for **self.error_flashes()**
        """
        return self.error_flashes(name, **attrs)

    def error_flashes(self, name=None, **attrs):
        """
        Renders errors as Foundation flash messages.

        If no errors present returns an empty string.

        `name` : errors for name. If **None** all errors will be rendered.
        """
        if name is None:
            errors = self.all_errors()
        else:
            errors = self.errors_for(name)
        content = [
            HTML.div(error, class_='alert-box alert', **attrs)
            for error in errors]
        return HTML(*content)

    def error_small(self, name, cols=None, **attrs):
        """
        Renders the specified error next to a Foundation form control

        `name` : errors for name.
        """
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

