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

import os
from setuptools import setup, find_packages
from utils import description, get_version, require_python

# Workaround <http://bugs.python.org/issue10945>
import codecs
try:
    codecs.lookup('mbcs')
except LookupError:
    ascii = codecs.lookup('ascii')
    func = lambda name, enc=ascii: {True: enc}.get(name=='mbcs')
    codecs.register(func)

require_python(0x020600f0)

HERE = os.path.abspath(os.path.dirname(__file__))

CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Environment :: Web Environment',
    'Framework :: Pyramid',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Topic :: Internet :: WWW/HTTP',
    'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    'Topic :: Scientific/Engineering',
    ]

REQUIRES = [
    'pyramid<1.4dev',
    'SQLAlchemy<0.8dev',
    'transaction',
    'pyramid_tm',
    'pyramid_debugtoolbar',
    # XXX Overridden with samplesdb.forms (submit changes as a patch to pyramid_simpleform?)
    #'pyramid_simpleform',
    # XXX Deps from pyramid_simpleform
    'webhelpers<2.0dev',
    'formencode<2.0dev',
    'pyramid_beaker',
    'pyramid_mailer',
    'pydns',
    'zope.sqlalchemy',
    'repoze.who<3.0dev',
    'waitress',
    'pytz',
    'passlib<2.0dev',
    'Pillow<2.0dev',
    'docutils<1.0dev',
    'creole<2.0dev',
    'pygments<2.0dev',
    'markdown<3.0dev',
    'bleach<2.0dev',
    'xlwt<0.8dev',
    # XXX elaphe trunk is borked (apparently). Remove this limit when it's fixed
    'elaphe==0.5.3',
    'nose',
    'mock',
    'WebTest',
    ]

ENTRY_POINTS = """\
    [paste.app_factory]
    main = samplesdb:main

    [console_scripts]
    initialize_samplesdb_db = samplesdb.scripts.initializedb:main
    """

def main():
    setup(
        name                 = 'samplesdb',
        version              = get_version(os.path.join(HERE, 'samplesdb/__init__.py')),
        description          = 'samplesdb',
        long_description     = description(os.path.join(HERE, 'README.rst')),
        classifiers          = CLASSIFIERS,
        author               = 'Dave Hughes',
        author_email         = 'dave@waveform.org.uk',
        url                  = 'https://github.com/waveform80/samplesdb',
        keywords             = 'science samples database',
        packages             = find_packages(exclude=['distribute_setup', 'utils']),
        include_package_data = True,
        platforms            = 'ALL',
        install_requires     = REQUIRES,
        extras_require       = {},
        zip_safe             = False,
        test_suite           = 'nose.collector',
        entry_points         = ENTRY_POINTS,
        )

if __name__ == '__main__':
    main()
