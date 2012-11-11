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
import tempfile
from contextlib import closing

# Try and import some 3rd party library for image handling
try:
    from PIL import Image
    IMAGE_API = 'PIL'
    CAN_RESIZE = [
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
    ]
except ImportError:
    try:
        from pgmagick import Image
        IMAGE_API = 'pgmagick'
        CAN_RESIZE = [
            'image/gif',
            'image/jpeg',
            'image/pcx',
            'image/pict',
            'image/png',
            'image/tiff',
            'image/vnd.wap.wbmp',
            'image/x-jng',
            'image/x-photoshop',
            'image/x-portable-anymap',
            'image/x-portable-bitmap',
            'image/x-portable-graymap',
            'image/x-portable-pixmap',
            'image/x-xbitmap',
            'image/x-xwindowdump',
        ]
    except ImportError:
        IMAGE_API = None
        CAN_RESIZE = []

__all__ = ['can_resize', 'resize_image', 'IMAGE_API']


def can_resize(mime_type):
    "Returns True if the specified MIME type can be resized by this library"
    return mime_type in CAN_RESIZE


def resize_image(source_filename, target_filename, maxw, maxh=None):
    "Resizes source image to target with specified maximum width and/or height"
    if maxh is None:
        maxh = maxw
    im = Image.open(source_filename)
    (w, h) = im.size
    if w > maxw or h > maxh:
        scale = min(float(maxw) / w, float(maxh) / h)
        w = int(round(w * scale))
        h = int(round(h * scale))
        im = im.convert('RGB').resize((w, h), Image.ANTIALIAS)
    else:
        im = im.convert('RGB')
    tempfd, temppath = tempfile.mkstemp(
        dir=os.path.dirname(target_filename))
    try:
        with closing(os.fdopen(tempfd, 'wb')) as f:
            im.save(f, 'JPEG')
    except:
        os.unlink(temppath)
        raise
    os.rename(temppath, target_filename)
