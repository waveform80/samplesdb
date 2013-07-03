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

from datetime import datetime

import pytz
import bleach
import webhelpers
import webhelpers.date
import webhelpers.number
import webhelpers.html.builder
import webhelpers.html.converters
from pyramid.decorator import reify
from pyramid.renderers import get_renderer
from pyramid.security import has_permission


MARKUP_LANGUAGES = {
    'text'    : 'Plain Text',
    'html'    : 'HTML',
    'textile' : 'Textile Markup',
    'md'      : 'Markdown',
    }

try:
    import docutils
    import docutils.core
    MARKUP_LANGUAGES['rst'] = 'reStructuredText'
except ImportError:
    pass

try:
    import creole
    import creole.html_emitter
    MARKUP_LANGUAGES['creole'] = 'Creole Markup'
except ImportError:
    pass

ALLOWED_TAGS = set((
    'a', 'abbr', 'acronym', 'address', 'b', 'big', 'blockquote', 'br',
    'caption', 'center', 'cite', 'code', 'col', 'colgroup', 'dd', 'del', 'dfn',
    'div', 'dl', 'dt', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i',
    'img', 'ins', 'kbd', 'li', 'ol', 'p', 'pre', 'q', 's', 'samp', 'small',
    'span', 'strike', 'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'tfoot',
    'th', 'thead', 'tr', 'tt', 'u', 'ul', 'var'))

P_ATTRS     = ['align']
Q_ATTRS     = ['cite']
LIST_ATTRS  = ['compact', 'type']
CELLH_ATTRS = ['align', 'char', 'charoff']
CELLV_ATTRS = ['valign']
SIZE_ATTRS  = ['width', 'height']
COL_ATTRS   = CELLH_ATTRS + CELLV_ATTRS + ['span', 'width']
CELL_ATTRS  = CELLH_ATTRS + CELLV_ATTRS + SIZE_ATTRS + [
    'abbr',
    'axis',
    'headers',
    'scope',
    'rowspan',
    'colspan',
    'nowrap',
    'bgcolor',
    ]

ALLOWED_ATTRS = {
    '*'          : ['id', 'class', 'title', 'lang', 'dir'],
    'a'          : ['name', 'href'],
    'blockquote' : Q_ATTRS,
    'caption'    : P_ATTRS,
    'col'        : COL_ATTRS,
    'colgroup'   : COL_ATTRS,
    'del'        : Q_ATTRS + ['datetime'],
    'dl'         : ['compact'],
    'h1'         : P_ATTRS,
    'h2'         : P_ATTRS,
    'h3'         : P_ATTRS,
    'h4'         : P_ATTRS,
    'h5'         : P_ATTRS,
    'h6'         : P_ATTRS,
    'hr'         : ['align', 'noshade', 'size', 'width'],
    'img'        : SIZE_ATTRS + [
        'src',
        'alt',
        'align',
        'hspace',
        'vspace',
        'border',
        ],
    'ins'        : Q_ATTRS + ['datetime'],
    'li'         : ['type', 'value'],
    'ol'         : LIST_ATTRS + ['start'],
    'p'          : P_ATTRS,
    'pre'        : ['width'],
    'q'          : Q_ATTRS,
    'table'      : [
        'summary',
        'width',
        'border',
        'frame',
        'rules',
        'cellspacing',
        'cellpadding',
        'align',
        'bgcolor',
        ],
    'tbody'      : CELLH_ATTRS + CELLV_ATTRS,
    'td'         : CELL_ATTRS,
    'tfoot'      : CELLH_ATTRS + CELLV_ATTRS,
    'th'         : CELL_ATTRS,
    'thead'      : CELLH_ATTRS + CELLV_ATTRS,
    'tr'         : CELLH_ATTRS + CELLV_ATTRS + ['bgcolor'],
    'ul'         : LIST_ATTRS,
}


class BaseView(object):
    """Abstract base class for view handlers"""

    # This base class defines a whole load of properties and methods which are
    # intended as utility routines / properties for use within templates. First
    # are reified properties containing template macros...

    @reify
    def layout(self):
        renderer = get_renderer('../templates/layout.pt')
        return renderer.implementation().macros['layout']

    @reify
    def top_banner(self):
        renderer = get_renderer('../templates/top_banner.pt')
        return renderer.implementation().macros['top_banner']

    @reify
    def top_bar(self):
        renderer = get_renderer('../templates/top_bar.pt')
        return renderer.implementation().macros['top_bar']

    @reify
    def flashes(self):
        renderer = get_renderer('../templates/flashes.pt')
        return renderer.implementation().macros['flashes']

    @reify
    def open_licenses_panel(self):
        renderer = get_renderer('../templates/open_licenses.pt')
        return renderer.implementation().macros['open_licenses']

    @reify
    def collection_license(self):
        renderer = get_renderer('../templates/collection_license.pt')
        return renderer.implementation().macros['collection_license']

    @reify
    def markup_languages(self):
        return MARKUP_LANGUAGES

    # Next a bunch of methods mostly derived from the excellent webhelpers
    # library...

    @reify
    def site_title(self):
        return self.request.registry.settings['site_title']

    def has_permission(self, permission):
        return has_permission(permission, self.context, self.request)

    def literal(self, *args):
        "Indicates that the content is literal markup"
        return webhelpers.html.builder.literal(*args)

    def format_data_size(
            self, size, unit, precision=1, binary=False, full_name=False):
        "Formats a data-size with a Greek size-suffix"
        return webhelpers.number.format_data_size(
            size, unit, precision, binary, full_name)

    def as_local(self, dt):
        "Convert a datetime to the request user's timezone"
        if self.request.user:
            local_tz = self.request.user.timezone
        else:
            # XXX Attempt to calculate TZ from request info
            local_tz = pytz.utc
        if dt.tzinfo is None:
            return local_tz.localize(dt)
        else:
            return dt.astimezone(local_tz)

    def as_utc(self, dt):
        "Convert a datetime to the UTC timezone"
        if dt.tzinfo is None:
            return pytz.utc.localize(dt)
        else:
            return dt.astimezone(pytz.utc)

    def now(self):
        "Returns the current timestamp with the request user's timezone"
        return self.as_local(datetime.now())

    def utcnow(self):
        "Returns the current UTC timestamp with the UTC timezone"
        return self.as_utc(datetime.utcnow())

    def distance_of_time_in_words(
            self, from_time, to_time=None, granularity='second', round=False):
        "Timezone aware version of webhelpers.date.distance_of_time_in_words"
        from_time = self.as_utc(from_time)
        to_time = self.as_utc(to_time) if to_time else self.utcnow()
        return webhelpers.date.distance_of_time_in_words(
            from_time, to_time, granularity, round)

    def time_ago_in_words(
            self, from_time, granularity='second', round=False):
        "Timezone aware version of webhelpers.date.time_ago_in_words"
        return self.distance_of_time_in_words(
            from_time, None, granularity, round)

    def render_markup(self, language, source):
        if not language in MARKUP_LANGUAGES:
            raise ValueError('Unknown markup language %s' % language)
        if language == 'text':
            html = bleach.linkify(
                webhelpers.html.converters.format_paragraphs(source))
        elif language == 'html':
            html = source
        elif language == 'md':
            html = webhelpers.html.converters.markdown(source)
        elif language == 'textile':
            html = webhelpers.html.converters.textilize(source)
        elif language == 'rst':
            overrides = {
                'input_encoding'       : 'unicode',
                'doctitle_xform'       : False,
                'initial_header_level' : 2,
                }
            html = docutils.core.publish_parts(
                source=source, writer_name='html',
                settings_overrides=overrides)['fragment']
        elif language == 'creole':
            html = creole.html_emitter.HtmlEmitter(
                    creole.Parser(source).parse()).emit()
        # Sanitize all HTML output with bleach (don't rely on safe-mode of
        # converters above as they're not necessarily as good and sometimes
        # disable useful features like embedding HTML in MarkDown)
        return webhelpers.html.builder.literal(bleach.clean(
            html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS))

