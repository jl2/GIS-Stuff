#!/usr/bin/env python3

# neddown.py

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

# This script mass downloads NED elevation data from gisdata.usgs.gov

# Unfortunately it's not as straight forward as it sounds.
# Here's a description of the problem:
# The NED data is available in ArcGrid and "float" format, in 1 arc-second
# and 1/3 arc-second squares, here:

# http://gisdata.usgs.gov/XMLWebServices2/getTDDSDownloadURLs.aspx?XMin=
# -109.2&YMin=35.8&XMax=-101.9&YMax=42.1&EPSG=4326&STATE=Colorado&COUNTY=#

# The problem is that it's a shitload of data.  Zipped, a 1/3 arc-second
# square, in ArcGrid format is over 320 MB.  Float is even larger
# The USGS uses a tape library system to store the data.
# When the links on that page are clicked it opens a new window, which
# launches a process on the server to fetch the tapes, extract the data,
# create an archive and eventually send it to the client.  It communicates
# with the client using clientside Javascript.

# Long story short, that process isn't very amenable to mass downloading
# using wget or urllib.request.

# So, what this script does instead is to load that gisdata.usgs.gov page
# and parse out the links
# Then it opens a dialog box with a QWebKit control in it to handle all of
# the wierd Javascript communication.
# Then it grabs the final .zip file URL that the server returns and downloads
# the file.

import os
import os.path
import re
import sys
import subprocess
import http.client
import html.parser

import urllib.request
import urllib.parse

from PyQt4 import QtWebKit
from PyQt4 import QtGui
from PyQt4 import QtCore

import concurrent.futures

# Simple parser to grab the final URL of the data
class LinkParser(html.parser.HTMLParser):
    def __init__(self):
        super(LinkParser, self).__init__()
        self.url = None
    def handle_starttag(self, tag, attrs):
        if tag=='a':
            for at,val in attrs:
                if at=='href':
                    self.url = val

# Download a zip file containing NED data
# This function exists to be passed to an
# concurrent.futures.ThreadPoolExecutor
def download_ned(ned):
    fname = ned['out_dir'] + '/' + ned['name']+'.zip'
    if not os.path.exists(fname):
        print('Downloading',fname)
        urllib.request.urlretrieve(ned['good_url'], fname)

# Dialog box with a QtWebKit control to download and process
# downloads using Javascript
class FancyDownloader(QtGui.QDialog):
    def __init__(self, neds, executor, parent=None):
        super(FancyDownloader, self).__init__(parent)
            
        # store some info for later
        self.neds = neds
        print(self.neds)
        if len(self.neds)==0:
            self.close()
            self.destroy()
            return
        self.curNedIdx = 0
        self.executor = executor
        print('current idx',self.curNedIdx)
        print('num neds', len(self.neds))
        self.curNed = self.neds[self.curNedIdx]

        # Create the web control
        self.qwp = QtWebKit.QWebView(self)
        self.qwp.load(QtCore.QUrl(self.curNed['new_url']))
        self.connect(self.qwp, QtCore.SIGNAL('loadFinished(bool)'),
                     self.loadFinished)

        htl = QtGui.QHBoxLayout()
        htl.addWidget(self.qwp)
        self.setLayout(htl)

    # After each step in the Javascript process a loadFinished() event
    # is sent.
    # This event handler parses the current HTML of the WebKit control
    # and looks for the data URL.
    def loadFinished(self, ok):
        print('Got a load finished!')
        htmlText = self.qwp.page().currentFrame().toHtml().__str__()
        parser = LinkParser()
        parser.feed(htmlText)
        if parser.url is not None and parser.url.find('downloadID')>0:
            print('The download URL is:', parser.url)
            self.curNed['good_url'] = parser.url
            self.executor.submit(download_ned, self.curNed)
            self.curNedIdx += 1
            if self.curNedIdx<len(self.neds):
                self.curNed = self.neds[self.curNedIdx]
                self.qwp.setUrl(QtCore.QUrl(self.curNed['new_url']))
            else:
                print('Done with WebKit, closing and destroying window!')
                self.close()
                self.destroy()

            # A possible alternative that doesn't use an HTMLParser:
            # urlRx = re.compile('.*"(http://extract\.cr\.usgs\.gov/axis2/services/DownloadService/getData\?downloadID=.*)" style.*')
            # mt = urlRx.match(htmlText)
            # if mt is not None:
            #     self.ned['good_url'] = mt.group(1)
            #     self.executor.submit(download_ned, self.ned)
            # self.reject()

# This is a mess
# Parse the page at
# http://gisdata.usgs.gov/XMLWebServices2/getTDDSDownloadURLs.aspx?XMin=
# -109.2&YMin=35.8&XMax=-101.9&YMax=42.1&EPSG=4326&STATE=Colorado&COUNTY=#
# and look for links to NED data
# It's more or less a crude state machine based on emperical observations
# of the page's HTML and some experimentation.
# If the page layout is changed in any way, this will probably break.
# But until then...

# Also, it's slightly complicated by the fact that the first request
# always (almost always) sends a "retry" with <a> link to a new URL
# So this catches that.
class MyHTMLParser(html.parser.HTMLParser):
    def __init__(self):
        super(MyHTMLParser, self).__init__()
        self.curNed = dict()
        self.neds = list()
        self.state = 0
        self.retryUrl = None
        self.DEFAULT_STATE = 0
        self.NAME_STATE = 1
        self.TITLE_STATE = 2
        self.TR_STATE=3
        self.RETRY_STATE = 999
        self.curDesc = ''

    def handle_starttag(self, tag, attrs):
        # Have to look at title tags to see if the title is
        # "Object moved", which is the cue that the page
        # needs to be fetched again at a new URL
        if tag=='title':
            self.state = self.TITLE_STATE

        # First handle_data after a <tr> returns the
        # type of data being linked to a couple rows over
        # We need to save this description for later so that
        # the appropriate links are followed
        elif tag=='tr':
            self.state = self.TR_STATE

        # <a> tags that contain the actual links
        elif tag=='a':
            for at,val in attrs:
                # Of course using href would be too easy
                if at=='onclick':
                    # Set curTiff's image url
                    self.curNed['url'] = val
                    self.curNed['desc'] = self.curDesc
                    # Switch to the 'name' state, indicating that the
                    # next handle_data will be the name of the NED link
                    self.state = self.NAME_STATE
                # But if a retry is necessary, it uses href,
                # so check for that
                elif at=='href' and self.state ==self.RETRY_STATE:
                    # print('Retry at:',val)
                    self.retryUrl = val

    # </a> is as good a place as any to add the current NED to the list
    def handle_endtag(self, tag):
        if tag=='a' and self.curNed.get('url',None) is not None :
            self.neds.append(self.curNed)
            # and reset
            self.curNed = dict()

    # Handle data and reset state
    def handle_data(self, data):
        # Name of the current NED
        # something like n<lat>w<long>
        if self.state == self.NAME_STATE:
            self.curNed['name'] = data.strip()
            self.state = self.DEFAULT_STATE

        # Grab the description of the next set of links
        elif self.state==self.TR_STATE:
            self.curDesc = data
            self.state = self.DEFAULT_STATE

        # An 'Object moved' title indicates a retry is necessary,
        # so check for it and setup the RETRY_STATE if found
        elif self.state == self.TITLE_STATE:
            if data=='Object moved':
                # try again
                self.state = self.RETRY_STATE
            else:
                # Don't try again
                self.state = self.DEFAULT_STATE


def main(args):
    # Default to CO, but check for args that override that
    # Note that the whole state of Colorado is f'in huge
    # Probably a poor choice of default, but it makes my testing easier
    xmin = -109.2
    ymin = 35.8
    xmax = -101.9
    ymax = 42.1
    outDir = 'colorado_neds'
    
    if len(args)==5:
        xmin = float(args[0])
        ymin = float(args[1])
        xmax = float(args[2])
        ymax = float(args[3])
        outDir = args[4]
    elif len(args)>0:
        print('This script takes 0 or 5 arguments.')
        print('If arguments are given, the syntax should be:')
        print("\tneddown.py min_long min_lat max_long max_lat output_directory")
        sys.exit(1)

    # Download and parse the initial page
    conn =  http.client.HTTPConnection('gisdata.usgs.gov')
    url = '/XMLWebServices2/getTDDSDownloadURLs.aspx?XMin={}&YMin={}&XMax={}&YMax={}&EPSG=4326&STATE=&COUNTY=#'.format(xmin,ymin,xmax,ymax)
    conn.request("GET", url)
    r1 = conn.getresponse()
    body = r1.read().decode()

    # Fix some screwed up HTML before parsing it
    body = body.replace('false;=', 'false=')
    parser = MyHTMLParser()
    # print(body)
    parser.feed(body)
    # print('Retry at:', parser.retryUrl)
    neds = list()
    sessionID = ''
    sessionRx = re.compile('.*(\(S\(.+\)\)).*')
    # Check for a retry
    if parser.retryUrl is not None:
        # Got a retry, so try again
        newUrl = urllib.parse.unquote(parser.retryUrl)
        conn.request("GET", newUrl)
        # Should really error check this, but there's not much to do
        # except fail anyway
        mtch = sessionRx.match(newUrl)
        sessionID = mtch.group(1)
        r2 = conn.getresponse()

        body = r2.read().decode()
        # print(body)
        # Again, fix bad HTML before parsing
        body = body.replace('false;=', 'false=')
        body = body.replace('onclick=','onclick="')
        body = body.replace('false;>', 'false;">')
        parser2 = MyHTMLParser()
        parser2.feed(body)
        # Theoretically possible there was another retry, but I've never
        # seen it.
        neds = parser2.neds
    else:
        # No retry
        neds = parser.neds

    if len(neds)==0:
        print("An error occured fetching the NED URLs!")
        exit(2)
    # Create the output directory if it doesn't exist
    if not os.path.exists(outDir):
        os.makedirs( outDir )

    
    nedTypes = set()
    toDownload = list()
    # Create a new list containing the NED urls we're interested in
    # Choices are:
    # 'National Elevation Dataset (1 arc second) Pre-packaged ArcGrid format'
    # 'National Elevation Dataset (1/3 arc second) Pre-packaged ArcGrid format'
    # 'National Elevation Dataset (1 arc second) Pre-packaged Float format'
    # 'National Elevation Dataset (1/3 arc second) Pre-packaged Float format'
    wantedFormat = 'National Elevation Dataset (1/3 arc second) Pre-packaged ArcGrid format'
    for ned in neds:
        if ned['desc']==wantedFormat:
            nt = ned
            rawUrl = nt['url']
            # Remove the Javascript cruft and create the actual URLs
            newUrl = rawUrl.replace('window.open(\'', '/XMLWebServices2/'+sessionID+'/')
            newUrl = newUrl.replace("','downloadWin','left=100,top=100,width=600,height=500'); return false;", '')
            newUrl = 'http://gisdata.usgs.gov' + newUrl
            nt['new_url'] = newUrl
            nt['out_dir'] = outDir
            toDownload.append(nt)

    # Create a "FancyDownloader" and start downloading the NEDs concurrently
    app = QtGui.QApplication([])
    rv = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        fd = FancyDownloader(toDownload, executor)
        fd.show()
        rv = app.exec_()

    # Bye
    sys.exit(rv)

if __name__=='__main__':
    main(sys.argv[1:])
