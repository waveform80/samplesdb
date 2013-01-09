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

"""
Provides a routine to construct an authentication policy from settings
"""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

from pyramid.settings import asbool
from pyramid.authentication import AuthTktAuthenticationPolicy

def asint(v):
    try:
        return int(v)
    except ValueError:
        return 0

def authn_policy_from_settings(settings):
    """
    Return a Pyramid authentication policy using settings supplied from
    a Paste configuration file
    """
    prefixes = ('authn.',)
    options = {}

    for k, v in settings.items():
        for prefix in prefixes:
            if k.startswith(prefix):
                option_name = k[len(prefix):]
                if option_name == 'timeout':
                    v = int(v)
                options[option_name] = v
