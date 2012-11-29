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

import re
from unicodedata import normalize
from datetime import datetime, timedelta

import pytz
import bleach
import webhelpers
import webhelpers.date
import webhelpers.number
import webhelpers.html.builder
import webhelpers.html.converters


literal = webhelpers.html.builder.literal
format_data_size = webhelpers.number.format_data_size


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


def render_markup(language, source):
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
    # converters above as they're not necessarily as good and sometimes disable
    # useful features like embedding HTML in MarkDown)
    return literal(bleach.clean(
        html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS))


def utcnow():
    "Returns the current UTC timestamp with the UTC timezone"
    return pytz.utc.localize(datetime.utcnow())


def distance_of_time_in_words(
        from_time, to_time=None, granularity='second', round=False):
    "Timezone aware version of webhelpers.date.distance_of_time_in_words"
    if isinstance(from_time, datetime) and from_time.tzinfo is None:
        if isinstance(to_time, datetime) and not to_time.tzinfo is None:
            from_time = pytz.utc.localize(from_time)
    if to_time is None:
        to_time = datetime.utcnow()
    if isinstance(to_time, datetime) and to_time.tzinfo is None:
        if isinstance(from_time, datetime) and not from_time.tzinfo is None:
            to_time = pytz.utc.localize(to_time)
    return webhelpers.date.distance_of_time_in_words(
        from_time, to_time, granularity, round)


def time_ago_in_words(from_time, granularity='second', round=False):
    "Timezone aware version of webhelpers.date.time_ago_in_words"
    return distance_of_time_in_words(
        from_time, datetime.now(), granularity, round)


_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

def slugify(text, default='', delim='-'):
    "Convert text to an ASCII URL/filename-safe slug"
    # Courtesy of Armin Ronacher <http://flask.pocoo.org/snippets/5/>
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return delim.join(result) or default

