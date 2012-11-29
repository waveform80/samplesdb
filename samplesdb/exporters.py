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

from sqlalchemy.orm import aliased

from samplesdb.models import (
    DBSession,
    Collection,
    Sample,
    SampleCode,
    )


class CollectionCsvExporter(object):
    def __init__(self, collection):
        self.collection = collection
        self.dialect = csv.get_dialect('excel')
        self.all_columns = [
            ('id'          , 'Identifier')  , 
            ('description' , 'Description') , 
            ('created'     , 'Created')     , 
            ('destroyed'   , 'Destroyed')   , 
            ('location'    , 'Location')    , 
            ('parents'     , 'Parents')     , 
            ('children'    , 'Children')    , 
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
        columns = []
        aliases = []
        for column in self.columns:
            if column.startswith('code_'):
                alias = aliased(SampleCode)
                aliases.append((alias, column[len('code_'):]))
                columns.append(getattr(alias, 'value'))
            elif column in ('parents', 'children'):
                print('Skipping', column)
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
        writer = csv.writer(output_file, self.dialect)
        for i, row in enumerate(query.all()):
            writer.writerow(row)
