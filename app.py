# This fork is derived from acbetter 
# Have added fit to width function as requested on his forum
# please visit https://gist.github.com/acbetter/e7d0c600fdc0865f4b0ee05a17b858f2 


#!/usr/bin/python3
# -*- coding: utf-8 -*-

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QPalette, QPainter
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import QLabel, QSizePolicy, QScrollArea, QMessageBox, QMainWindow, QMenu, QAction, \
    qApp, QFileDialog

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import numpy as np
import h5py
import os

diro="/mnt/f/Data/AO001R_RGC_imaging/Image_00001_AO001R_896_512_600_20_1.57_6000_-ve0.25_10deg/padded/"
dir_ssd="e:\drc"
DEFAULT_LAYER=134
ANIMATE_TIME_MS=250


class QImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.printer = QPrinter()
        self.scaleFactor = 0.0

        
        self.imageLabel = QLabel()
        self.imageLabel.setBackgroundRole(QPalette.Base)
        self.imageLabel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.imageLabel.setScaledContents(True)

        self.scrollArea = QScrollArea()
        self.scrollArea.setBackgroundRole(QPalette.Dark)
        self.scrollArea.setWidget(self.imageLabel)
        self.scrollArea.setVisible(False)
        
        self.imageLabel2 = QLabel()
        self.imageLabel2.setBackgroundRole(QPalette.Base)
        #self.imageLabel2.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.imageLabel2.setScaledContents(True)
        #self.imageLabel2.setVisible(False)

        self.scrollArea2 = QScrollArea()
        self.scrollArea2.setBackgroundRole(QPalette.Dark)
        self.scrollArea2.setWidget(self.imageLabel2)
        self.scrollArea2.setVisible(False)
        self.scrollArea2.width = 512
        self.scrollArea2.height = 128
        
        
        self.doLog=False
        #h_layout.AddWidget(self.scrollArea)
        #hbox = QHBoxLayout(self.scrollArea)

        #self.setLayout(QVBoxLayout())
        #h_layout = QHBoxLayout()
       # self.layout().addLayout(h_layout)
       
# https://www.qtcentre.org/threads/70176-QLayout-Attempting-to-add-QLayout-quot-quot-to-MainWindow-quot-quot-which-already-has-a-layout 
# https://zetcode.com/gui/pyqt5/layout/
      
        #self.setCentralWidget(self.scrollArea)
        self.widget = QWidget(self)
         
        self.hbox = QVBoxLayout()
        self.hbox.setSpacing(10)
        self.widget.setLayout(self.hbox)
        
        self.label = QLabel(self)
        self.label.setFont(QFont('Arial', 18))
        self.label.setText('z-plane:')

        self.fils=glob.glob(sys.argv[-1] )
        self.minvol=int( os.path.basename(self.fils[0]).split('_')[0] )
        self.maxvol=int( os.path.basename(self.fils[-1]).split('_')[0] )
        self.nvol=0
        
        self.label_volume = QLabel(self)
        self.label_volume.setFont(QFont('Arial', 18))
        
       # QSizePolicy spLeft(QSizePolicy::Preferred, QSizePolicy::Preferred);
        self.scrollArea.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        self.hbox.addWidget(self.scrollArea)
        self.hbox.addWidget(self.scrollArea2)    
        self.hbox.addWidget(self.label)
        self.hbox.addWidget(self.label_volume)
        
        self.hbox.setStretchFactor(self.scrollArea,3)
        self.hbox.setStretchFactor(self.scrollArea2,1)

        self.setCentralWidget(self.widget)

        self.createActions()
        self.createMenus()

        self.init_image()
        
        self.setWindowTitle("Viewer")
        self.resize(1024, 925)
        
        self.setChildrenFocusPolicy(Qt.NoFocus)

        self.animating=False

    def setChildrenFocusPolicy (self, policy):
        def recursiveSetChildFocusPolicy (parentQWidget):
            for childQWidget in parentQWidget.findChildren(QWidget):
                childQWidget.setFocusPolicy(policy)
                recursiveSetChildFocusPolicy(childQWidget)
        recursiveSetChildFocusPolicy(self)
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            self.nlayer -= 1
            self.choose_layer(self.nlayer)
        elif event.key() == Qt.Key_Down:
            self.nlayer += 1
            self.choose_layer(self.nlayer)
        elif event.key() == Qt.Key_Left:
            self.nextVol(-1)
        elif event.key() == Qt.Key_Right:
            self.nextVol(1)
            
        elif event.key() == Qt.Key_A:
            self.animating = not self.animating
            if self.animating: # Start  
                self.timer=QTimer(self)
                self.timer.timeout.connect(self.animate)
                self.timer.start(ANIMATE_TIME_MS)
            else:
                self.timer.stop()
    
    def animate(self):
        self.nextVol(1)
    
    def nextVol(self, direction):
        self.nvol += direction
        if self.nvol<0:
            self.nvol=len(self.fils)-1
        if self.nvol>len(self.fils)-1:
            self.nvol=0
        self.loadh5(self.nvol)
        
    def getPos(self , event):
            x = event.pos().x()
            y = event.pos().y()
            y=y/200.0 * np.shape(self.av)[0]
            #x=x/200 * np.shape(self.av)[1]
            #print(y)
            y=int(y)
            self.choose_layer(y)
            self.nlayer = y
        
    def choose_layer(self,n,first_time=False):
        data=self.dset[:,:,int(n)]
        
        self.nlayer=n
        
        if self.doLog:
            data=np.log10(data)
            data_bits=np.array((data.T/np.max(data)*255.0),dtype='uint8')
        else: 
            data_bits=np.array((data.T/np.max(data)*255.0),dtype='uint8')
            
        data_bits=np.require(data_bits, np.uint8, 'C')
        image = QImage(data_bits.data, np.shape(data)[0], np.shape(data)[1], QImage.Format_Grayscale8)
        self.imageLabel.setPixmap(QPixmap.fromImage(image))
        self.scaleFactor = 1.0
        self.label.setText('%03d'%n)
    
        # Update the axial across-section image
        av=self.avg # reload from image
        data_bits=np.array((av.T/np.max(av)*255.0),dtype='uint8')
        data_bits[self.nlayer-1:self.nlayer+1,:] = 255;
        data_bits=np.require(data_bits, np.uint8, 'C')
        
        if True:
            self.image2 = QImage(data_bits.data, np.shape(self.avg)[0], np.shape(self.avg)[1], QImage.Format_Grayscale8)   
        else:
            self.image2.fromData(data_bits.data);
               
       # image2.scale(512,256)
        self.av=data_bits
        
        self.imageLabel2.setPixmap(QPixmap.fromImage(self.image2.scaled(600,200)) )
        self.imageLabel2.adjustSize()
    
    def loadh5(self,nvol):
        self.nvol=nvol
        filname=self.fils[ nvol ]#os.path.join(dir_ssd, '%05d_vol.h5'%volnum)
        fil=h5py.File( filname ) #'test_av.h5') ) #'00188_vol.h5'))
        self.dset=fil['real']
        self.avg = fil['av3'][:]
        self.label_volume.setText( '%03d %s %03d (%d of %d)'%(self.minvol,filname,self.maxvol,self.nvol+1, len(self.fils)) )
        
        self.choose_layer(self.nlayer)
    
    def init_image(self):
        #data_all=dset[:,:,:] # Dimensions are shuffled vs. MATLAB (MATLAB is "fortran order, vs. C order for the rest of the world")
        # https://swharden.com/blog/2013-06-03-realtime-image-pixelmap-from-numpy-array-data-in-qt/
        self.nlayer=DEFAULT_LAYER
        self.loadh5(0)
        #self.imageLabel2.setMouseTracking(True)
        self.imageLabel2.mousePressEvent = self.getPos

#        self.choose_layer(self.nlayer,True) # loadh5 will do one
        
        self.scrollArea2.setVisible(True)
        self.imageLabel2.adjustSize()
    
    
        if True:
            #image = QImage(fileName)
           # if image.isNull():
           #     QMessageBox.information(self, "Image Viewer", "Cannot load %s." % fileName)
           #     return
            #self.setWindowTitle("Image Viewer : " + fileName)
            

            self.scrollArea.setVisible(True)
            self.printAct.setEnabled(True)
            self.fitToWidthAct.setEnabled(True)
            self.fitToWindowAct.setEnabled(True)
            self.updateActions()

            if not self.fitToWindowAct.isChecked():
                self.imageLabel.adjustSize()
    
    def open(self):
        #options = QFileDialog.Options()
        #fileName = QFileDialog.getOpenFileName(self, "Open File", QDir.currentPath())
        #fileName, _ = QFileDialog.getOpenFileName(self, 'QFileDialog.getOpenFileName()', '',
        #                                          'Images (*.png *.jpeg *.jpg *.bmp *.gif)', options=options)
                                                  
 

        if True:
            #image = QImage(fileName)
            if image.isNull():
                QMessageBox.information(self, "Image Viewer", "Cannot load %s." % fileName)
                return
            #self.setWindowTitle("Image Viewer : " + fileName)
            self.imageLabel.setPixmap(QPixmap.fromImage(image))
            self.scaleFactor = 1.0

            self.scrollArea.setVisible(True)
            self.printAct.setEnabled(True)
            self.fitToWidthAct.setEnabled(True)
            self.fitToWindowAct.setEnabled(True)
            self.updateActions()

            if not self.fitToWindowAct.isChecked():
                self.imageLabel.adjustSize()

    def print_(self):
        dialog = QPrintDialog(self.printer, self)
        if dialog.exec_():
            painter = QPainter(self.printer)
            rect = painter.viewport()
            size = self.imageLabel.pixmap().size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(self.imageLabel.pixmap().rect())
            painter.drawPixmap(0, 0, self.imageLabel.pixmap())

    def zoomIn(self):
        self.scaleImage(1.25)

    def zoomOut(self):
        self.scaleImage(0.8)

    def normalSize(self):
        self.imageLabel.adjustSize()
        self.scaleFactor = 1.0
        self.scaleImage(1.0)

    def fitToWidth(self):
        if self.scrollArea.width()   > 0 and self.imageLabel.pixmap().width() > 0:
            zoomfactor =  self.scrollArea.width() / self.imageLabel.pixmap().width()
        else:
            zoomfactor = 1

        self.imageLabel.adjustSize()
        self.scaleFactor = zoomfactor
        self.scaleImage(1.0)


        self.updateActions()

    def fitToWindow(self):
        fitToWindow = self.fitToWindowAct.isChecked()
        self.scrollArea.setWidgetResizable(fitToWindow)
        if not fitToWindow:
            self.normalSize()

        self.updateActions()
        
    def logNorm(self):
        self.doLog=not self.doLog
        if self.doLog:
            self.logNormAct.checked=True
    
    def about(self):
        QMessageBox.about(self, "About Image Viewer",
                          "<p>The <b>Image Viewer</b> example shows how to combine "
                          "QLabel and QScrollArea to display an image. QLabel is "
                          "typically used for displaying text, but it can also display "
                          "an image. QScrollArea provides a scrolling view around "
                          "another widget. If the child widget exceeds the size of the "
                          "frame, QScrollArea automatically provides scroll bars.</p>"
                          "<p>The example demonstrates how QLabel's ability to scale "
                          "its contents (QLabel.scaledContents), and QScrollArea's "
                          "ability to automatically resize its contents "
                          "(QScrollArea.widgetResizable), can be used to implement "
                          "zooming and scaling features.</p>"
                          "<p>In addition the example shows how to use QPainter to "
                          "print an image.</p>")

    def createActions(self):
        self.openAct = QAction("&Open...", self, shortcut="Ctrl+O", triggered=self.open)
        self.printAct = QAction("&Print...", self, shortcut="Ctrl+P", enabled=False, triggered=self.print_)
        self.exitAct = QAction("E&xit", self, shortcut="Ctrl+Q", triggered=self.close)
        self.zoomInAct = QAction("Zoom &In (25%)", self, shortcut="Ctrl++", enabled=False, triggered=self.zoomIn)
        self.zoomOutAct = QAction("Zoom &Out (25%)", self, shortcut="Ctrl+-", enabled=False, triggered=self.zoomOut)
        self.normalSizeAct = QAction("&Normal Size", self, shortcut="Ctrl+S", enabled=False, triggered=self.normalSize)
        self.fitToWidthAct = QAction("&Fit to Width", self, shortcut="Ctrl+S", enabled=False, triggered=self.fitToWidth)
        self.fitToWindowAct = QAction("&Fit to Window", self, enabled=False, checkable=True, shortcut="Ctrl+F",
                                      triggered=self.fitToWindow)

        self.logNormAct = QAction("&Log Normalize", self, enabled=True, checkable=True, checked=False, shortcut="Ctrl+L",
                                      triggered=self.logNorm)
                                      
        self.aboutAct = QAction("&About", self, triggered=self.about)
        self.aboutQtAct = QAction("About &Qt", self, triggered=qApp.aboutQt)

    def createMenus(self):
        self.fileMenu = QMenu("&File", self)
        self.fileMenu.addAction(self.openAct)
        self.fileMenu.addAction(self.printAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAct)

        self.viewMenu = QMenu("&View", self)
        self.viewMenu.addAction(self.zoomInAct)
        self.viewMenu.addAction(self.zoomOutAct)
        self.viewMenu.addAction(self.normalSizeAct)
        self.viewMenu.addAction(self.fitToWidthAct)
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(self.fitToWindowAct)
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(self.logNormAct)

        self.helpMenu = QMenu("&Help", self)
        self.helpMenu.addAction(self.aboutAct)
        self.helpMenu.addAction(self.aboutQtAct)

        self.menuBar().addMenu(self.fileMenu)
        self.menuBar().addMenu(self.viewMenu)
        self.menuBar().addMenu(self.helpMenu)

    def updateActions(self):
        self.zoomInAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.zoomOutAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.fitToWidthAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.normalSizeAct.setEnabled(not self.fitToWindowAct.isChecked())

    def scaleImage(self, factor):
        self.scaleFactor *= factor
        self.imageLabel.resize(self.scaleFactor * self.imageLabel.pixmap().size())

        self.adjustScrollBar(self.scrollArea.horizontalScrollBar(), factor)
        self.adjustScrollBar(self.scrollArea.verticalScrollBar(), factor)

        self.zoomInAct.setEnabled(self.scaleFactor < 3.0)
        self.zoomOutAct.setEnabled(self.scaleFactor > 0.333)

    def adjustScrollBar(self, scrollBar, factor):
        scrollBar.setValue(int(factor * scrollBar.value()
                               + ((factor - 1) * scrollBar.pageStep() / 2)))


if __name__ == '__main__':
    import sys
    import glob
    import os
    from PyQt5.QtWidgets import QApplication


    
    app = QApplication(sys.argv)
    imageViewer = QImageViewer()
    imageViewer.show()
    sys.exit(app.exec_())
    
    
    # TODO QScrollArea support mouse
    # base on https://github.com/baoboa/pyqt5/blob/master/examples/widgets/imageviewer.py
    #
    # if you need Two Image Synchronous Scrolling in the window by PyQt5 and Python 3
    # please visit https://gist.github.com/acbetter/e7d0c600fdc0865f4b0ee05a17b858f2
    
    
    
    #To animate:
            # timer = QtCore.QTimer(self)
        # timer.timeout.connect(self.update_image)
        # timer.start(60*1000)
        # self.update_image()