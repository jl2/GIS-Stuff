#!/usr/bin/env python2.6

from __future__ import print_function

# mapdb.py

# Copyright (c) 2011, Jeremiah LaRocco jeremiah.larocco@gmail.com

# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.

# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


# This script connects to the Sqlite DB created by mapdown.py
# and uses PyGDAL to add some more information

# This should really be included in mapdown.py, but Debian doesn't have
# Python GDAL available for Python 3 yet.
# But when that day comes, this script and mapdown.py should be merged
# That said, care is being taken to make this script as Python3 compatible
# as possible

# Alternatively, this script may eventually contain some significant
# raster processing to do stuff like remove image borders.
# In that case it may be beneficial to port it to C or C++ and use
# the GDAL library directly.
# It's possible Python's performance will be "good enough", though.

import os
import sys
import os.path
import sqlite3

import gdal

from gdalconst import *

# Right now this is more or less a stub script to test GDAL
def main(args):
    for tifFile in args:
        # Open the specified TIFF file
        dataset = gdal.Open(tifFile , GA_ReadOnly )

        # Print some info
        print('Driver:',
              dataset.GetDriver().ShortName,'/',
              dataset.GetDriver().LongName)

        print('Size is',dataset.RasterXSize,'x',dataset.RasterYSize,
              'x',dataset.RasterCount)

        print('Projection is',dataset.GetProjection())

        # Get the transform data and print it
        # Eventually this data should be added to the DB, and used to strip
        # borders from the TIFF files.
        geotransform = dataset.GetGeoTransform()
        if geotransform is None:
            continue
        print('Origin = (',geotransform[0], ',',geotransform[3],')')
        print('Pixel Size = (',geotransform[1], ',',geotransform[5],')')

if __name__=='__main__':
    main(sys.argv[1:])
