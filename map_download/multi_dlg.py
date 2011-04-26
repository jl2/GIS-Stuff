#!/usr/bin/env python3

# multi_dlg.py

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

# I used this to test the basic idea of the "FancyDownloader" class
# No idea why I'm adding it to Git, but maybe it will be useful later

# It just loads a list of URLs, one after the other and then exits

import sys

from PyQt4 import QtWebKit
from PyQt4 import QtGui
from PyQt4 import QtCore

import concurrent.futures

class FancyDownloader(QtGui.QDialog):
    def __init__(self, urls, parent=None):
        super(FancyDownloader, self).__init__(parent)
        self.idx = 0
        self.urls = urls

        # Create the web control
        self.qwp = QtWebKit.QWebView(self)
        self.qwp.load(QtCore.QUrl(self.urls[self.idx]))
        self.connect(self.qwp, QtCore.SIGNAL('loadFinished(bool)'),
                     self.loadFinished)

        htl = QtGui.QHBoxLayout()
        htl.addWidget(self.qwp)
        self.setLayout(htl)

    def loadFinished(self, ok):
        self.disconnect(self.qwp, QtCore.SIGNAL('loadFinished(bool)'),
                        self.loadFinished)

        print('Got a load finished!', ok)
        self.idx += 1
        if self.idx<len(self.urls):
            print('Going to ',self.urls[self.idx])
            self.qwp.setUrl(QtCore.QUrl(self.urls[self.idx]))
            self.connect(self.qwp, QtCore.SIGNAL('loadFinished(bool)'),
                          self.loadFinished)
        else:
            print('Destroying')
            self.close()
            self.destroy()

def main(args):
    app = QtGui.QApplication([])
    urls = ['http://google.com',
            'http://yahoo.com',
            'http://jlarocco.com',
            'http://bing.com',
            ]
    fd = FancyDownloader(urls)
    fd.show()
    print('Done showing!')
    sys.exit(app.exec_())

if __name__=='__main__':
    main(sys.argv[1:])
