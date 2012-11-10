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

from datetime import datetime, timedelta

import pytz
import webhelpers
import webhelpers.date
import webhelpers.number


format_data_size = webhelpers.number.format_data_size


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
