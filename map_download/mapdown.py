#!/usr/bin/env python3

# mapdown.py

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

# This script mass downloads topo maps for an entire state from libremap.org

# Note that the maps are large and downloading an entire state
# takes a lot of disk space and bandwidth.  If you do it for more than a
# few states or repeatedly, you should donate to libremap.  Bandwidth
# isn't free, and they're providing a valuable service.
# For info on donating, see:

#      http://libremap.org/donate/


import os
import os.path

import sys
import subprocess
import http.client
import html.parser
import urllib.request
import concurrent.futures

# Download an image to the given directory if it doesn't
# already exist
def download_img(img_url, directory):
    fname = directory + '/' + img_url[img_url.rindex('/')+1:]
    if not os.path.exists(fname):
        urllib.request.urlretrieve(img_url, fname)
        print('Downloaded "{}"'.format(fname))
    else:
        print('"{}" already exists!'.format(fname))


tiffs = set()
# Parse an HTML document and get all of the links to .tif files
class MyHTMLParser(html.parser.HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag=='a':
            for at,val in attrs:
                if at=='href' and val[-3:]=='tif':
                    tiffs.add(val)

def main(args):
    # Default to CO, but check for an arg
    state = 'colorado'
    if len(args)>0:
        state = args[0]

    # Connect to libremap and get the index page
    conn =  http.client.HTTPConnection('libremap.org')
    conn.request("GET", '/data/state/{}/drg/'.format(state))
    r1 = conn.getresponse()

    # Parse the HTML to populate the set of TIFF files
    parser = MyHTMLParser()
    parser.feed(r1.read().decode())

    # Make the directory for the state's TIFFs
    if not os.path.exists(state):
        os.makedirs( state )

    # Concurrently download the TIFFs
    # Not sure if concurrency helps here, actually, but it may?
    # In any case, it was a chance to play with concurrent.futures...
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for url in tiffs:
            executor.submit(download_img, url, state )

if __name__=='__main__':
    main(sys.argv[1:])
