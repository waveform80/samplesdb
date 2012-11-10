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

from pyramid.decorator import reify
from pyramid.renderers import get_renderer
from pyramid.security import authenticated_userid

from samplesdb import helpers


class BaseView(object):
    """Abstract base class for view handlers"""

    @reify
    def site_title(self):
        return self.request.registry.settings['site_title']

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
    def helpers(self):
        return helpers

