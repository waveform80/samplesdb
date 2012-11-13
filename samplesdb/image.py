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
import tempfile
from contextlib import closing

from PIL import Image

__all__ = ['can_resize', 'make_thumbnail']

SVG_MIME_TYPE = 'image/svg+xml'
THUMB_MAXWIDTH = 150
THUMB_MAXHEIGHT = 150

def can_resize(mime_type):
    "Returns True if the specified MIME type can be resized by this library"
    return mime_type in set((
        'image/gif',
        'image/jpeg',
        'image/pcx',
        'image/png',
        'image/tiff',
        'image/x-ms-bmp',
        'image/x-portable-bitmap',
        'image/x-portable-graymap',
        'image/x-portable-pixmap',
        'image/x-xbitmap',
        ))

def make_thumbnail(source_filename, target_filename):
    "Resizes source image to target with specified maximum width and/or height"
    im = Image.open(source_filename)
    (w, h) = im.size
    if w > THUMB_MAXWIDTH or h > THUMB_MAXHEIGHT:
        scale = min(float(THUMB_MAXWIDTH) / w, float(THUMB_MAXHEIGHT) / h)
        w = int(round(w * scale))
        h = int(round(h * scale))
        im = im.convert('RGB').resize((w, h), Image.ANTIALIAS)
    else:
        im = im.convert('RGB')
    tempfd, temppath = tempfile.mkstemp(
        dir=os.path.dirname(target_filename))
    try:
        with io.open(tempfd, 'wb') as f:
            im.save(f, 'JPEG')
    except:
        os.unlink(temppath)
        raise
    os.rename(temppath, target_filename)

