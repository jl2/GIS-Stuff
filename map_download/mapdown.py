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

import sqlite3

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

# Parse an HTML document and get all of the links to .tif files
# This HTMLParser subclass creates a list of dictionaries
# containing information about all of the TIFF map files on the
# libremap.org map download page.
class MyHTMLParser(html.parser.HTMLParser):
    def __init__(self):
        super(MyHTMLParser, self).__init__()
        self.state = 0
        self.curTiff = dict()
        self.tiffs = []
        self.fields = []
        self.curField = None
        self.cfi = 0
        self.DEFAULT_STATE = 0
        self.HEADING_STATE = 1
        self.VALUE_STATE = 2

    def handle_starttag(self, tag, attrs):

        # html, table, and tr start tags
        # reset some state
        if tag == 'html':
            self.state = self.DEFAULT_STATE

        if tag=='table':
            self.state = self.DEFAULT_STATE
            self.fieldNames = []

        if tag=='tr':
            curTiff = dict()
            self.curField = None
            self.cfi = 0

        
        elif tag=='td':
            for at,val in attrs:
                # check if it's a heading
                if at=='class' and val=='headleftstyle':
                    # If so, flag that the next data element is a column heading
                    self.state = self.HEADING_STATE

                # Check if it's a table entry
                elif at=='class' and val=='leftstyle':
                    # If so, set the state accordingly
                    self.state = self.VALUE_STATE

        # Check 'a' tags for links to tiff image map files
        elif tag=='a':
            for at,val in attrs:
                if at=='href' and val[-3:]=='tif':
                    # Set curTiff's image url
                    self.curTiff['url'] = val

    # Only relevant endtag is tr, indicating the end of a row
    # Append curTiff to tiffs and reset for next row
    def handle_endtag(self, tag):
        if tag=='tr' and self.curTiff.get('url',None) is not None:
            self.tiffs.append(self.curTiff)
            # print('Appending',self.curTiff['Cell Name'], 'id',self.curTiff['ID'])
            self.curTiff = dict()

    # Handle data and reset state
    def handle_data(self, data):
        # Found a heading name, so add it to the field list
        if self.state == self.HEADING_STATE:
            self.fields.append(data)
            self.state = self.DEFAULT_STATE

        # Found a field value, so add it to curTiff
        elif self.state == self.VALUE_STATE:
            self.curField = self.fields[self.cfi]
            self.state = self.DEFAULT_STATE
            self.curTiff[self.curField] = data
            # Move to the next field
            self.cfi = self.cfi + 1
            if self.cfi >= len(self.fields):
                self.cfi = 0

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
    # print(parser.fields)
    
    print('Found {} tiffs'.format(len(parser.tiffs)))

    # Make the directory for the state's TIFFs
    if not os.path.exists(state):
        os.makedirs( state )

    dbFileName = state + '/' + state + '.db'
    # Delete the DB file if it exists
    if os.path.exists(dbFileName):
        os.remove(dbFileName)

    # Recreate it
    dbc = sqlite3.connect(dbFileName)
    dbc.execute('''\
create table maps (
    id integer primary key, 
    cell_name text, 
    state text, 
    category text, 
    se_latitude real, 
    se_longitude real, 
    min_val text, 
    dsn text, 
    tiff_url text)''')

    # Loop through the results and add them to the DB
    with dbc:
        for tifi in parser.tiffs:
            dbc.execute('''\
insert into maps(
    id,
    cell_name,
    state,
    category,
    se_latitude,
    se_longitude,
    min_val,
    dsn,
    tiff_url) 
    values (?,?,?,?,?,?,?,?,?)''',
                        (tifi['ID'],
                         tifi['Cell Name'],
                         tifi['State'],
                         tifi['Category'],
                         tifi['SE Latitude'],
                         tifi['SE Longitude'],
                         tifi['MIN'],
                         tifi['DSN'],
                         tifi['url']))
    dbc.close()

    # Concurrently download the TIFFs
    # Not sure if concurrency helps here, actually, but it may?
    # In any case, it was a chance to play with concurrent.futures...
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for tif in parser.tiffs:
            executor.submit(download_img, tif['url'], state )

if __name__=='__main__':
    main(sys.argv[1:])
