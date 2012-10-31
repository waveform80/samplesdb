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

from pyramid.view import view_config

from samplesdb.views import BaseView
from samplesdb.views.account import LoginSchema
from samplesdb.forms import BaseSchema, Form, FormRenderer

class RootView(BaseView):
    """Handler for root (mostly static) views"""

    @view_config(route_name='home', renderer='../templates/root/home.pt')
    def home(self):
        form = Form(
            self.request,
            schema=LoginSchema,
            defaults=dict(came_from=self.request.url))
        return dict(form=FormRenderer(form))

    @view_config(route_name='faq', renderer='../templates/root/faq.pt')
    def faq(self):
        return {}
