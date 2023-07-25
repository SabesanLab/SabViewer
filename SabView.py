#!/usr/bin/python3
# -*- coding: utf-8 -*-

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QPalette, QPainter
from PyQt5.QtWidgets import QLabel, QSizePolicy, QScrollArea, QMessageBox, QMainWindow, QMenu, QAction, \
    qApp, QFileDialog, QInputDialog

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import numpy as np
import h5py
import os
import skvideo # to read/write .avi
import skvideo.io  

import sys
import subprocess

from PIL import Image
import socket # remote control

import pyshmem # Our shared memory routines
from threading import Thread

diro="/mnt/f/Data/AO001R_RGC_imaging/Image_00001_AO001R_896_512_600_20_1.57_6000_-ve0.25_10deg/padded/"
dir_ssd="e:\drc"
DEFAULT_LAYER=0
ANIMATE_TIME_MS=250
MIP_PIXELS=5

class QImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()

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
        self.imageLabel2.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.imageLabel2.setScaledContents(True)
        self.imageLabel2.setVisible(True)

        self.b2 = QCheckBox("Valid")
        #self.b2.toggled.connect(lambda:self.btnstate(self.b2))
      
        self.scrollArea2 = QScrollArea()
        self.scrollArea2.setBackgroundRole(QPalette.Dark)
        
        self.top = QHBoxLayout()
        self.top.addWidget(self.scrollArea2)
        self.top.addWidget(self.b2)

        self.scrollArea2.setWidget(self.imageLabel2)
        self.scrollArea2.setVisible(False)
        self.scrollArea2.width = 512
        self.scrollArea2.height = 128
        
        
        self.doLog=False
        self.doMIP=False
        #h_layout.AddWidget(self.scrollArea)
        #hbox = QHBoxLayout(self.scrollArea)

        #self.setLayout(QVBoxLayout())
        #h_layout = QHBoxLayout()
       # self.layout().addLayout(h_layout)
       
# https://www.qtcentre.org/threads/70176-QLayout-Attempting-to-add-QLayout-quot-quot-to-MainWindow-quot-quot-which-already-has-a-layout 
# https://zetcode.com/gui/pyqt5/layout/
      
        #self.setCentralWidget(self.scrollArea)
        self.widget = QWidget(self)
        
        self.checkboxValid = QCheckBox("Valid")
        self.checkboxValid.toggled.connect(lambda:self.btnstate(self.checkboxValid))         
        
        self.hbox = QVBoxLayout()
        self.hbox.setSpacing(10)
        self.widget.setLayout(self.hbox)
        
        self.label = QLabel(self)
        self.label.setFont(QFont('Arial', 18))
        self.label.setText('z-plane:')
       
        #self.loadDir( sys.argv[-1] )
        self.def_dir='.' # default directory. Command-line (or drag-drop) may override
        self.def_file='' # default directory. Command-line (or drag-drop) may override
        self.nvol=0
        self.nlayer=-1 # No image loaded year
        
        self.label_volume = QLabel(self)
        self.label_volume.setFont(QFont('Arial', 18))
        
       # QSizePolicy spLeft(QSizePolicy::Preferred, QSizePolicy::Preferred);
        self.scrollArea.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        self.hbox.addWidget(self.scrollArea)
        self.hbox.addWidget(self.scrollArea2)    
        #self.hbox.addLayout(hbox)
        self.hbox.addWidget(self.checkboxValid)
        self.hbox.addWidget(self.label)
        self.hbox.addWidget(self.label_volume)
        
        self.hbox.setStretchFactor(self.scrollArea,3)
        self.hbox.setStretchFactor(self.scrollArea2,1)

        self.setCentralWidget(self.widget)

        self.createActions()
        self.createMenus()

        self.av_which="av2"

        #self.init_image() # Maybe not ready
        
        self.setWindowTitle("Viewer")
        self.resize(1024, 925)
        
        self.setChildrenFocusPolicy(Qt.NoFocus)

        self.animating=False
        self.setAcceptDrops(True)
        
        self.socket=None # Remote control
        
        self.valids=np.ones(1, dtype='uint8' )

        self.toggler = -1

        
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()    
            
    def dropEvent(self, e):
        print (e.mimeData().text() )
        
    def loadDir(self, dir_and_wildcards):
        self.fils=glob.glob( dir_and_wildcards )
        #self.minvol=0 # %int( os.path.basename(self.fils[0]).split('_')[0] )
        #self.maxvol=int( os.path.basename(self.fils[-1]).split('_')[0] )
            
    def setChildrenFocusPolicy (self, policy):
        def recursiveSetChildFocusPolicy (parentQWidget):
            for childQWidget in parentQWidget.findChildren(QWidget):
                childQWidget.setFocusPolicy(policy)
                recursiveSetChildFocusPolicy(childQWidget)
        recursiveSetChildFocusPolicy(self)
        
    def keyPressEvent(self, event):
        if (event.modifiers() & Qt.ControlModifier):
            stride=10
        else:
            stride=1
            
        if event.key() == Qt.Key_Up:
            self.nlayer -= stride
            self.choose_layer(self.nlayer)
        elif event.key() == Qt.Key_Down:
            self.nlayer += stride
            self.choose_layer(self.nlayer)
        elif event.key() == Qt.Key_Left:
            self.nextVol(-stride)
        elif event.key() == Qt.Key_Right:
            self.nextVol(stride)
            
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
   
    def remote_start(self):
        if self.socket is None:
            self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM);
            self.socket.connect(('localhost',50000))
            self.remoteAct.checked=True
        else: # disconnect
            self.socket.sendall(b'reset')
            self.socket.close()
            self.socket=None
            self.remoteAct.checked=False
            
    def remote_send(self, command):
        if not (self.socket is None):
            self.socket.sendall(command)
            
    def toggle(self):
        if self.toggler==-1:
            self.toggler=self.nvol
        else:
            last=self.nvol #self.toggler
            self.nextVol(self.toggler-self.nvol)
            self.toggler=last
            
    def nextVol(self, direction):
        self.remote_send(b'next %d'%direction)
            
        if 'avi' in self.filname:
            self.nlayer += direction
            self.choose_layer(self.nlayer)
            return
            
        self.nvol += direction
        if self.nvol<0:
            self.nvol=len(self.fils)-1
        if self.nvol>len(self.fils)-1:
            self.nvol=0
        self.load1(self.nvol)
        
    # Moving mouse in axial profile window
    def axial_win_click(self , event):
        x = event.pos().x()
        y = event.pos().y()
        y=y/200.0 * np.shape(self.av)[0] # TODO: why 200?
        y=int(y)
        self.choose_layer(y)
        self.nlayer = y
        
    def main_move(self , event):
        x = event.pos().x()
        y = event.pos().y()
        self.display_coords( event.pos().x()/self.scaleFactor, event.pos().y()/self.scaleFactor, self.nlayer)      
    
    def display_coords(self,x,y,z):
        self.label.setText('x: %03d/%03d, y: %03d/%03d, z: %03d/%03d'%(x,self.width,y,self.height,z,self.n_depths))

    def choose_layer(self,n,first_time=False):
    
        n_depths=np.shape(self.dset)[2]
        if n>=n_depths: # Don't go past max depth
            n=n_depths-1
        elif n<0:
            n=0
            
        data=self.dset[:,:,int(n)]
        #shap=np.shape( data) ;
        #data = np.reshape( data, (shap[1], shap[0]) ) ;

        self.nlayer=n
        
        if self.doMIP and (n>=MIP_PIXELS) and (n<(n_depths+MIP_PIXELS+1)):
            # Max. intensity projection. Take max in layer-2 to layer+2
            data=self.dset[:,:,int(n)-MIP_PIXELS:int(n)+MIP_PIXELS+1]
            data=np.max(data,2)
        else:
            self.doMIP=False # Can't do MIP at edge of depths
            
        if self.doLog:
            data=np.array(data)
            #print ( np.shape(data), np.nanmean(data), np.max(data) )
            data=np.log10(data)
            data[np.isinf(data)]=np.nan
            data[data<1]=np.nan;
            mean1=np.nanmean(data);
            std1=np.nanstd(data);
            
            # Clamp to +/- 'X' stds
            data[(data-mean1)>(std1*6)] = mean1+6*std1;
            data[(data-mean1)<-(std1*3)] = mean1-3*std1;
            
            mean2=np.nanmean(data);
            std2=np.nanstd(data);
            data=(data-mean2)/(5*std2) + 0.5;
            #data -= np.min(data) # Make smallest == zero # && less than max layer # && less than max layer
            data[np.isnan(data)]=0
            data[np.isinf(data)]=0
            
            #print( np.histogram(data) )
            # Clamp
            data[data<0]=0;
            data[data>1]=1;

            #print (np.max(data), np.mean(data), np.min(data), mean1, std1, mean2, std2 )
            data_bits=np.array((10**data.T/np.max(10**data)*255.0),dtype='uint8')
        else: 
            data_bits=np.array((data.T/np.max(data)*255.0),dtype='uint8')
            
        data_bits=np.require(data_bits, np.uint8, 'C')

        # get the shape of the array
        height, width = np.shape(data_bits)

        # calculate the total number of bytes in the frame 
        totalBytes = data_bits.nbytes

        # divide by the number of rows
        bytesPerLine = int(totalBytes/height)

        # Needed to fix skew problem.
        #https://stackoverflow.com/questions/41596940/qimage-skews-some-images-but-not-others

        self.image_current = data_bits;
        
        image = QImage(data_bits.data, width, height, bytesPerLine, QImage.Format_Grayscale8)
        self.imageLabel.setPixmap(QPixmap.fromImage(image))
        self.scaleFactor = 1.0
        self.width=width
        self.height=height
        self.n_depths=n_depths
        self.display_coords(0,0,n+1);
    
        # Update the axial across-section image
        av=self.avg # reload from image
        data_bits=np.array((av.T/np.max(av)*255.0),dtype='uint8')

        if self.nlayer>0:  # && less than max layer. Make bright bar indicating location
            data_bits[self.nlayer-1:self.nlayer+1,:] = 255;

        data_bits=np.require(data_bits, np.uint8, 'C')
        
        #print( np.shape(self.dset) )
        if len(np.shape(self.avg))>1:
            # get the shape of the array
            width, height = np.shape(self.avg)
            #print( height, width)

            # calculate the total number of bytes in the frame 
            totalBytes = data_bits.nbytes

            # divide by the number of rows
            bytesPerLine = int(totalBytes/height)        
            self.image2 = QImage(data_bits.data, width, height, bytesPerLine, QImage.Format_Grayscale8)   
            
            #self.image2.fromData(data_bits.data);            
        else:
            pass
            
               
       # image2.scale(512,256)
        self.av=data_bits
        
        self.imageLabel2.setPixmap(QPixmap.fromImage(self.image2.scaled(600,200)) )
        self.imageLabel2.adjustSize()
    
    def update_display(self):
        self.label_volume.setText( '%s (%d of %d)'%(self.filname,self.nvol+1, len(self.fils)) )        
        self.choose_layer(self.nlayer)
        
    def btnstate(self,btn):
        self.valids[self.nvol]=self.checkboxValid.isChecked()
        
    def load1(self,nvol):
        self.nvol=nvol
        self.filname=self.fils[ nvol ]#os.path.join(dir_ssd, '%05d_vol.h5'%volnum)
        self.checkboxValid.setChecked( self.valids[nvol] )
        
        # TODO: get extension in better way
        parts=os.path.splitext(self.filname)
        #print(parts)
        if parts[1]=='.h5':
            self.loadh5(self.filname)
        elif parts[1]=='.mat':
            self.loadMat(self.filname)
        elif parts[1]=='.avi':
            print("Loading...")
            videodata = skvideo.io.vread(self.filname)

            if len(videodata.shape)>3:
                # Has color. Ignore by just taking mean across RGB
                videodata=np.mean( videodata,3)
                print("Transposing...")
                self.dset=np.transpose( videodata, [1, 2, 0] ) # Reorder dims so it matches MATLAB
                print( self.dset.shape )
                #self.dset=np.reshape( self.dset, (self.dset.shape[1], self.dset.shape[0], self.dset.shape[2]) )
            else:
                self.dset=np.transpose( videodata, [1, 2, 0] ) # Works for raw videos from MATLAB
            print("done...")
            self.avg = np.zeros( (5,5)) # TODO: Doesn't matter. Nothing to show.
            #self.dset=self.dset[..., np.newaxis] # Create a dummy last axial axis
            #print(self.videodata.shape, self.dset.shape)
            #print (np.max(self.dset[...,0]), np.mean(self.videodata[...,0]) )
        else:
            print('Unknown extension')
            
        self.update_display()
    
    def loadh5(self,filname):
        self.fil=h5py.File( filname ) #'test_av.h5') ) #'00188_vol.h5'))
        self.dset=self.fil['real']
        self.avg = self.fil[self.av_which][:]

    def loadMat(self,filname):
        fil=h5py.File( filname ) # Newer MATLAB (>=7.3) use hdf files !
        self.dset=fil[list(fil.keys())[0]]
        self.avg = np.mean( self.dset, 1)  # rebuild average

    def load_single(self,filname):
        self.fils = [filname]
        self.init_image() # First-time init of image widget (also loads)
    
    def init_image(self):
        #data_all=dset[:,:,:] # Dimensions are shuffled vs. MATLAB (MATLAB is "fortran order, vs. C order for the rest of the world")
        # https://swharden.com/blog/2013-06-03-realtime-image-pixelmap-from-numpy-array-data-in-qt/
        self.nlayer=DEFAULT_LAYER
        
        self.load1(0)

        #self.imageLabel2.setMouseTracking(True)
        self.imageLabel2.mousePressEvent = self.axial_win_click

        self.imageLabel.setMouseTracking(True)
        self.imageLabel.mouseMoveEvent = self.main_move

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
            #self.printAct.setEnabled(True)
            self.fitToWidthAct.setEnabled(True)
            self.fitToWindowAct.setEnabled(True)
            self.updateActions()

            if not self.fitToWindowAct.isChecked():
                self.imageLabel.adjustSize()
                
    def set_files(self,fils):
        self.fils=fils
        self.valids=np.ones(len(fils), dtype='uint8' )
        
    def open(self):
        #options = QFileDialog.Options()
        #fileName = QFileDialog.getOpenFileName(self, "Open File", QDir.currentPath())
        #fileName, _ = QFileDialog.getOpenFileName(self, 'QFileDialog.getOpenFileName()', '',
        #                                          'Images (*.png *.jpeg *.jpg *.bmp *.gif)', options=options)
                                                  
 
        ffilt='HDF5 files (*.h5);; All files (*.*)'
       #thedir = QFileDialog.getExistingDirectory(self, "Open Directory",
       #                                      "e:\drc" )
       #                                     # QFileDialog.ShowDirsOnly
       #                                      # QFileDialog.DontResolveSymlinks);
        thedir = QFileDialog.getOpenFileNames(self, "Choose file in directory",
                                             self.def_dir, ffilt );
                                            # QFileDialog.ShowDirsOnly
                                             # QFileDialog.DontResolveSymlinks);
                                                                        
        if len(thedir)==0:
            return

        if True:
            self.set_files(thedir[0]) # filenames, ignore filter
            self.def_dir=os.path.dirname( imageViewer.fils[0] ) # For next time, def dir good place
             
        else: # Old way to open files with wildards (glob)
            thedir=os.path.dirname(thedir[0]) # Now it's a file dialog, so get the dirname from the filname
            text, ok = QInputDialog.getText(self, 'Filename wildcards', 'Enter wildcards:')
            self.loadDir( os.path.join( thedir, text) )
        
        if len(self.fils) > 0:
            if self.nlayer==-1:
                self.init_image() # First-time init of image widget
            self.nextVol(0) # todo: "update screen"

        if False:
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
        self.logNormAct.checked=self.doLog
        self.update_display()
            
    def MIP(self):
        self.doMIP=not self.doMIP
        self.MIPAct.checked=self.doMIP
        self.update_display()

    def av2(self):
        self.av_which="av2"
        self.avg = self.fil[self.av_which][:]
        self.update_display()
    def av3(self):
        self.av_which="av3"
        self.avg = self.fil[self.av_which][:]
        self.update_display()
    
    def about(self):
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle....
            fil=open('version.txt','r')
            with fil:
                msg=fil.readlines();
            msg='</p><p>'.join(msg)
        else:
            msg = subprocess.check_output(['git', 'log', '-1','--pretty=format:%h,%ad']).decode()
            
        QMessageBox.about(self, "About Image Viewer",
                          "<p>Sabesan Lab volume/directory browser.</p>"+"Version: "+msg)

    def save(self):
        fileName = QFileDialog.getSaveFileName(self, ("Save F:xile"),
                                       "snapshot.png",
                                       ("Images (*.png *.xpm *.jpg)"))
        img = Image.fromarray(self.image_current, "L")
        #print(fileName)
        img.save(fileName[0])
        
    def video(self):
        for nframe in range(0,len(self.fils)):
            self.load1(nframe)
            # Max. intensity projection. Take max in layer-2 to layer+2
            data=self.dset[:,:,self.nlayer-MIP_PIXELS:self.nlayer+MIP_PIXELS+1]
            data=np.max(data,2)
            # Need to transpose x and y
            if nframe==0:
                videodata=np.zeros( (len(self.fils),data.shape[1],data.shape[0] ) )
            videodata[nframe] = data.T
        filename_movie=self.def_dir+'/video_MIP%02d.avi'%self.nlayer
        print(filename_movie)
        skvideo.io.vwrite(filename_movie, videodata );
            

    def export_valids(self):
        fileName = QFileDialog.getSaveFileName(self, ("Save F:xile"),
                                       self.def_dir+"/valids.csv",
                                       ("Images (*.png *.xpm *.jpg)"))
        np.savetxt(fileName[0], self.valids, delimiter=",",fmt='%d')

    def createActions(self):
        self.openAct = QAction("&Open...", self, shortcut="Ctrl+O", triggered=self.open)
        self.saveAct = QAction("&Save...", self, shortcut="Ctrl+S", triggered=self.save)
        self.videoAct = QAction("&Video...", self, shortcut="Ctrl+V", triggered=self.video)
        self.exportAct = QAction("&Export Valids...", self, shortcut="Ctrl+E", triggered=self.export_valids)
        #self.printAct = QAction("&Print...", self, shortcut="Ctrl+P", enabled=False, triggered=self.print_)
        self.remoteAct = QAction("&Remote...", self, shortcut="Ctrl+R", enabled=True, checkable=True, checked=False, triggered=self.remote_start)
        self.exitAct = QAction("E&xit", self, shortcut="Ctrl+Q", triggered=self.close)
        self.zoomInAct = QAction("Zoom &In (25%)", self, shortcut="Ctrl++", enabled=False, triggered=self.zoomIn)
        self.zoomOutAct = QAction("Zoom &Out (25%)", self, shortcut="Ctrl+-", enabled=False, triggered=self.zoomOut)
        self.normalSizeAct = QAction("&Normal Size", self, shortcut="Ctrl+N", enabled=False, triggered=self.normalSize)
        self.fitToWidthAct = QAction("&Fit to Width", self, shortcut="Ctrl+T", enabled=False, triggered=self.fitToWidth)
        self.fitToWindowAct = QAction("&Fit to Window", self, enabled=False, checkable=True, shortcut="Ctrl+F",
                                      triggered=self.fitToWindow)

        self.MIPAct = QAction("&MIP (-%d to +%d)"%(MIP_PIXELS,MIP_PIXELS), self, enabled=True, checkable=True, checked=False, shortcut="Ctrl+M",
                                      triggered=self.MIP)
        self.logNormAct = QAction("&Log Normalize", self, enabled=True, checkable=True, checked=False, shortcut="Ctrl+L",
                                      triggered=self.logNorm)
        self.av2Act = QAction("av&2", self, enabled=True, checkable=True, checked=False, shortcut="Ctrl+2",
                                      triggered=self.av2)
        self.av3Act = QAction("av&3", self, enabled=True, checkable=True, checked=False, shortcut="Ctrl+3",
                                      triggered=self.av3)
        self.toggleAct = QAction("to&ggle", self, enabled=True, shortcut="Ctrl+G",
                                      triggered=self.toggle)
                                      
        self.aboutAct = QAction("&About", self, triggered=self.about)
        self.aboutQtAct = QAction("About &Qt", self, triggered=qApp.aboutQt)

    def createMenus(self):
        self.fileMenu = QMenu("&File", self)
        self.fileMenu.addAction(self.openAct)
        self.fileMenu.addAction(self.saveAct)
        self.fileMenu.addAction(self.videoAct)
        self.fileMenu.addAction(self.exportAct)
        self.fileMenu.addAction(self.remoteAct)
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
        self.viewMenu.addAction(self.MIPAct)
        self.viewMenu.addAction(self.logNormAct)
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(self.av2Act)
        self.viewMenu.addAction(self.av3Act)
        
        self.viewMenu.addAction(self.toggleAct)

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

def socket_callback(which_command,data):
    global imageViewer
    if which_command=='data':
        #print( np.shape(data), data )
        imageViewer.dset=data
        imageViewer.avg = np.mean( data, 1)
        imageViewer.update_display()
        imageViewer.label_volume.setText( '<remote data> 1/1')
    elif which_command=='next':
        imageViewer.nextVol(data)
         
    
if __name__ == '__main__':
    import sys
    import glob
    import os
    global imageViewer
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    imageViewer = QImageViewer()

    listener_thread = Thread(target=pyshmem.do_listen, args=[socket_callback] )
    listener_thread.daemon=True # So application will terminate even if this thread is alive
    listener_thread.start()    

    #if len(sys.argv)>2:
    #    param=sys.argv[1]+sys.arv[2] #concat strings. extension separated
        
    if len(sys.argv)>2:
        imageViewer.set_files(sys.argv[1:]) #.split(' ')
        #if self.nlayer==-1:
        imageViewer.init_image() # First-time init of image widget
        imageViewer.nextVol(0)
        imageViewer.def_dir=os.path.dirname( imageViewer.fils[0] )
    elif len(sys.argv)>1:
        param=sys.argv[1]
        if os.path.isfile(param):
            imageViewer.load_single(param)
            imageViewer.def_dir=os.path.dirname( param )
        elif os.path.exists(param):
            imageViewer.def_dir=param # loadDir
    else: # Load dummy. TODO: blank?
        imageViewer.set_files(['F:/3D_registration/dummy.h5'])
        imageViewer.init_image()
        imageViewer.nextVol(0)
        imageViewer.def_dir="F:/3D_registration/Results";
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
