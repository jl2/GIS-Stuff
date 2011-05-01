#!/usr/bin/env python3

# viewtile.py

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


# This is a quick hack to view tiled images and scroll around
# Really poor quality right now, more like a proof of concept to demonstrate
# that the tile splitting code is working.

import re
import os
import sys
import glob
import os.path

from PyQt4 import QtGui
from PyQt4 import QtCore

class TileViewer(QtGui.QDialog):
    def __init__(self, directory, parent=None):
        super(TileViewer, self).__init__(parent)
        self.directory = directory
        self.get_image_counts()

        # Start at the top left corner
        self.curX = self.minx
        self.curY = self.miny

        # Create 4 labels
        self.lblUL = QtGui.QLabel('')
        self.lblLL = QtGui.QLabel('')
        self.lblUR = QtGui.QLabel('')
        self.lblLR = QtGui.QLabel('')
        self.lblUL.setAlignment(QtCore.Qt.AlignTop and QtCore.Qt.AlignLeft)
        self.lblLL.setAlignment(QtCore.Qt.AlignTop and QtCore.Qt.AlignLeft)
        self.lblUR.setAlignment(QtCore.Qt.AlignTop and QtCore.Qt.AlignLeft)
        self.lblLR.setAlignment(QtCore.Qt.AlignTop and QtCore.Qt.AlignLeft)

        self.refreshImages()

        # Add the labels to the layout
        vtl = QtGui.QVBoxLayout()
        htl = QtGui.QHBoxLayout()
        htl.addWidget(self.lblUL)
        htl.addWidget(self.lblUR)
        vtl.addLayout(htl)
        
        htl = QtGui.QHBoxLayout()
        htl.addWidget(self.lblLL)
        htl.addWidget(self.lblLR)
        vtl.addLayout(htl)
        self.setLayout(vtl)

    # Figure out the number of images in each dimension
    def get_image_counts(self):
        fns = glob.glob(self.directory + '/*.png')
        locPat = re.compile('.*(\d{4})x(\d{4}).png')
        self.minx = 999
        self.miny = 999
        self.maxx = 0
        self.maxy = 0
        for fn in fns:
            mp = locPat.match(fn)
            xd = int(mp.group(1))
            yd = int(mp.group(2))
            if xd<self.minx:
                self.minx = xd
            if yd<self.miny:
                self.miny = yd
            if xd>self.maxx:
                self.maxx = xd
            if yd>self.maxy:
                self.maxy = yd

    # Handle movement keypresses
    def keyPressEvent(self, event):
        tkey = event.key()
        if tkey  == QtCore.Qt.Key_Up:
            self.moveUp()
        elif tkey==QtCore.Qt.Key_Down:
            self.moveDown()
        elif tkey==QtCore.Qt.Key_Left:
            self.moveLeft()
        elif tkey==QtCore.Qt.Key_Right:
            self.moveRight()

    def refreshImages(self):
        # Update title to say which image is at the top left
        self.setWindowTitle('At ({}, {})'.format(self.curX, self.curY))


        # Load the images
        # Note that this could be coordinated with the movement functions
        # so that only 2 images are loaded in most cases
        tileFileName = '{}/tile{:04d}x{:04d}.png'.format(self.directory,
                                                         self.curX,
                                                         self.curY)
        self.pmapUL = QtGui.QPixmap(tileFileName)

        tileFileName = '{}/tile{:04d}x{:04d}.png'.format(self.directory,
                                                         self.curX+1,
                                                         self.curY)
        self.pmapUR = QtGui.QPixmap(tileFileName)

        tileFileName = '{}/tile{:04d}x{:04d}.png'.format(self.directory,
                                                         self.curX,
                                                         self.curY+1)
        self.pmapLL = QtGui.QPixmap(tileFileName)

        tileFileName = '{}/tile{:04d}x{:04d}.png'.format(self.directory,
                                                         self.curX+1,
                                                         self.curY+1)
        self.pmapLR = QtGui.QPixmap(tileFileName)

        # Update the labels
        self.lblUL.setPixmap(self.pmapUL)
        self.lblUR.setPixmap(self.pmapUR)
        self.lblLL.setPixmap(self.pmapLL)
        self.lblLR.setPixmap(self.pmapLR)

    # Move
    def moveUp(self):
        if self.curY>self.miny:
            self.curY-=1
            self.refreshImages()
    def moveDown(self):
        if self.curY<(self.maxy-1):
            self.curY+=1
            self.refreshImages()

    def moveLeft(self):
        if self.curX>self.minx:
            self.curX-=1
            self.refreshImages()
    def moveRight(self):
        if self.curX<(self.maxx-1):
            self.curX+=1
            self.refreshImages()

        
def main(args):
    if len(args)!=1:
        print('Command takes 1 argument!')
        print("\t./viewtile.py <image_directory>")
        sys.exit(1)
    app = QtGui.QApplication([])
    tv = TileViewer(args[0])
    tv.show()
    sys.exit(app.exec_())

if __name__=='__main__':
    main(sys.argv[1:])
