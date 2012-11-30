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
import io
import json
import time
from datetime import datetime, timedelta
from contextlib import closing
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen


__all__ = ['licenses_factory_from_settings', 'License', 'LicensesFactory']


# See <http://licenses.opendefinition.org> for the Licenses API. The URL below
# links to a JSON database of all licenses with various attributes
LICENSES_API_ALL = 'http://licenses.opendefinition.org/licenses/groups/all.json'


class License(object):
    def __init__(self, **attr):
        self.domain_content = bool(attr.get('domain_content', ''))
        self.domain_data = bool(attr.get('domain_data', ''))
        self.domain_software = bool(attr.get('domain_software', ''))
        self.family = attr.get('family', '')
        self.id = attr['id']
        self.is_generic = bool(attr.get('is_generic', ''))
        self.is_okd_compliant = bool(attr.get('is_okd_compliant', ''))
        self.is_osi_compliant = bool(attr.get('is_osi_compliant', ''))
        self.maintainer = attr.get('maintainer', '')
        self.status = attr['status']
        self.title = attr['title']
        self.url = attr.get('url', '')

    @property
    def is_open(self):
        return self.is_okd_compliant or self.is_osi_compliant


class DummyLicensesFactory(object):
    def __call__(self):
        return {'notspecified': License(
            domain_content=False,
            domain_data=False,
            domain_software=False,
            id='notspecified',
            is_generic=True,
            status='active',
            title='License Not Specified')}


class LicensesFactory(object):
    """Factory class which returns a dictionary of licenses when called"""

    def __init__(self, cache_dir):
        self._cache_dir = cache_dir
        if not os.path.exists(self._cache_dir):
            os.mkdir(self._cache_dir)

    @property
    def _cache_file(self):
        """Returns the full path and filename of the license JSON cache"""
        return os.path.join(self._cache_dir, 'all.json')

    @property
    def _lock_file(self):
        """Returns the full path and filename of the lock file/dir"""
        return os.path.join(self._cache_dir, 'lock')

    def _lock(self):
        """Obtains an inter-process lock in a cross-platform manner"""
        # Using mkdir() as it's atomic on both Unix and Windows
        os.mkdir(self._lock_file)

    def _unlock(self):
        """Releases the inter-process lock gained by lock()"""
        os.rmdir(self._lock_file)

    def _try_lock(self, timeout):
        """Attempts for timeout seconds to obtain the inter-process lock"""
        start = datetime.now()
        while datetime.now() - start < timedelta(seconds=timeout):
            try:
                self._lock()
                return True
            except OSError, exc:
                pass
            time.sleep(0.1)
        return False

    def _update_optional(self, timeout=1):
        """Attempts to update the cache, failing silently on lock timeout"""
        if self._try_lock(timeout):
            try:
                self._update_cache()
            finally:
                self._unlock()

    def _update_mandatory(self):
        """Attempts to update the cache, raises OSError on lock failure"""
        self._lock()
        try:
            self._update_cache()
        finally:
            self._unlock()

    def _update_cache(self):
        """Attempts to update the cache - should not be called directly"""
        # Download the new defs to a temoprary file
        with io.open(self._cache_file + '.new', 'wb') as target:
            with closing(urlopen(LICENSES_API_ALL, timeout=10)) as source:
                while True:
                    data = source.read(1024**2)
                    if not data:
                        break
                    target.write(data)
        # Renames within the same file-system are atomic, i.e. everything that
        # attempts to read the cache before this gets the old file and
        # everything afterwards gets the new cache - no process gets a
        # partially written cache file
        os.rename(self._cache_file + '.new', self._cache_file)

    def __call__(self):
        """Return a dictionary of License instances keyed by id"""
        if not os.path.exists(self._cache_file):
            # If the cache file doesn't exist we must create it in order to
            # return any results
            self._update_mandatory()
        elif (datetime.utcfromtimestamp(os.stat(self._cache_file).st_mtime) <
                (datetime.now() - timedelta(days=7))):
            # If the cache file is merely stale we'll attempt to get a lock and
            # update it, but if we timeout waiting for a lock just use the
            # stale file
            self._update_optional()
        return dict(
            (key, License(**value))
            for (key, value) in json.loads(
                io.open(self._cache_file, 'r').read()).items())


def licenses_factory_from_settings(settings):
    return LicensesFactory(settings['licenses_cache_dir'])

