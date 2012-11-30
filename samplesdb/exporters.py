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

from sqlalchemy.orm import aliased

from samplesdb.models import (
    DBSession,
    Collection,
    Sample,
    SampleCode,
    )


def invert_map(m):
    """
    Quick hack to invert a mapping with unique values
    """
    return dict(zip(m.values(), m.keys()))


class CollectionCsvExporter(object):
    """
    CSV Exporter class for collections.

    `collection` : the collection to be exported

    After construction, the ``all_columns`` property will be a map of column
    identifier to column description. The ``columns`` property will be an
    ordered sequence of column identifiers selected for export which should be
    modified according to user preference.

    HTML-form friendly variants of the properties of the csv ``Dialect`` class
    are provided in ``delimiter``, ``lineterminator``, ``quotechar`` and so on.
    They default to the values of the Excel dialect.
    """

    _delimiter_map = {
        b',':  'comma',
        b';':  'semi-colon',
        b' ':  'space',
        b'\t': 'tab',
        }

    _lineterminator_map = {
        b'\r\n': 'dos',
        b'\n':   'unix',
        b'\r':   'mac',
        }

    _quotechar_map = {
        b'"': 'double',
        b"'": 'single',
        }

    _quoting_map = {
        csv.QUOTE_NONE:       'none',
        csv.QUOTE_MINIMAL:    'minimal',
        csv.QUOTE_NONNUMERIC: 'non-numeric',
        csv.QUOTE_ALL:        'all',
        }

    _delimiter_inv = invert_map(_delimiter_map)
    _lineterminator_inv = invert_map(_lineterminator_map)
    _quotechar_inv = invert_map(_quotechar_map)
    _quoting_inv = invert_map(_quoting_map)

    def __init__(self, collection):
        self.collection = collection
        self.delimiter = self._delimiter_map[csv.excel.delimiter]
        self.lineterminator = self._lineterminator_map[csv.excel.lineterminator]
        self.quotechar = self._quotechar_map[csv.excel.quotechar]
        self.quoting = self._quoting_map[csv.excel.quoting]
        self.doublequote = csv.excel.doublequote
        self.dateformat = '%Y-%m-%d'
        self.all_columns = [
            ('id'          , 'Identifier')  , 
            ('description' , 'Description') , 
            ('created'     , 'Created')     , 
            ('destroyed'   , 'Destroyed')   , 
            ('location'    , 'Location')    , 
            # XXX Figure out a reasonable cross-database way of including this
            # (SQLite supports GROUP_CONCAT, PostgreSQL has a string_agg but
            # only in 9+, or we could use Python expressions if we don't care
            # about efficieny...)
            #('parents'     , 'Parents')     , 
            #('children'    , 'Children')    , 
            ]
        self.all_columns.extend(
            DBSession.query('code_' + SampleCode.name, SampleCode.name).\
                join(Sample).\
                join(Collection).\
                filter(Collection.id==collection.id).\
                distinct().all())
        self.columns = [name for (name, title) in self.all_columns]
        self.all_columns = dict(self.all_columns)

    def export(self, output_file):
        """
        Export the collection to the specified file.

        `output_file` : a file-like object which the CSV will be written to
        """
        columns = []
        aliases = []
        for column in self.columns:
            if column.startswith('code_'):
                alias = aliased(SampleCode)
                aliases.append((alias, column[len('code_'):]))
                columns.append(getattr(alias, 'value'))
            elif column in ('parents', 'children'):
                raise NotImplementedError
            else:
                columns.append(Sample.__table__.columns[column])
        query = DBSession.query(*columns).select_from(Sample).\
                filter(Sample.collection_id==self.collection.id)
        for alias, name in aliases:
            query = query.\
                outerjoin(alias,
                    (Sample.id==getattr(alias, 'sample_id')) &
                    (getattr(alias, 'name')==name)
                    )
        writer = csv.writer(output_file,
            delimiter=self._delimiter_inv[self.delimiter],
            lineterminator=self._lineterminator_inv[self.lineterminator],
            quotechar=self._quotechar_inv[self.quotechar],
            quoting=self._quoting_inv[self.quoting],
            doublequote=self.doublequote)
        for row in query:
            # Rewrite the format of datetime values to exclude microseconds
            # (which confuse several spreadsheet parsers and which it's
            # unlikely anyone cares about)
            row = [
                value.strftime(self.dateformat)
                if isinstance(value, datetime) else value
                for value in row
                ]
            writer.writerow(row)
