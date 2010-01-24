#!/usr/bin/env python2.5
#
# barriosq.py - main barrioSquare program file
# 
# barrioSquare v0.1.5
# Copyright(c) 2010 Chili Technologies LLC
# http://www.chilitechno.com/fster
#
# This file is part of barrioSquare.
#
# barrioSquare is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# barrioSquare is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with barrioSquare. If not, see <http://www.gnu.org/licenses/>.
# or write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# By using this software you agree to be bound by the terms of the foursquare.com service
# which are available at http://foursquare.com/legal/terms
# 
# This software makes extensive use of the foursquare.com api, but is not affiliated by, 
# or endorsed by foursquare and is a 3rd party application which makes use of the foursquare.com api.
#
# ============================================================================
# Name        : barriosq.py
# Author      : Chris J. Burris - chris@chilitechno.com
# Version     : 0.1.5
# Description : barrioSquare
# ============================================================================

import sys
import math

from PyQt4 import QtGui, QtCore, QtWebKit
from barrioConfig import *
from barrioStyles import *
import oauthclient
import oauth
import time
import os
import cgi
import xml
import osso
import socket

from xml.dom.minidom import parseString
# location libs
# import location
# import gobject

# thread and process libs
import thread
import subprocess

# web libraries
import webbrowser
import urllib2

# global script vars
locationSubprocessRestartCount = 0
locationSubprocessIsRestarting = False
friendRefreshCount = 0
getLocationChildPID = 0
acquisitionCount = 0
badgeCount = 0
currentLatitude = 0
currentLongitude = 0
horizontalAccuracy = 1000
verticalAccuracy = 1000
locationMethodType = 0
fsRequestToken = None
fsRequestTokenString = ''
fsSecret = ''
fsKey = ''
userPreferencesDir = os.path.expanduser('~') + os.sep + '.barriosquare' + os.sep
hasToken = 0
locationFixAcquired = 0
qb = None
searchKeywords = ''
shoutString = ''
infoNoticeString = ''
checkinVenueID = 0
pingFriends = False
pingTwitter = False
allowIncomingPings = True
pingFacebook = False
# set FakeCheckin to True to simulate a check-in (must have really checked into a venue at least once before)
FakeCheckin = True
loggedInUserID = 0
showSplashScreen = False
doingSignout = False
locationManagerObj = None

print userPreferencesDir
if (not os.path.exists(userPreferencesDir)):
	print 'Creating Pref Dir'
	os.mkdir(userPreferencesDir)
	os.mkdir(userPreferencesDir + 'venueCache' + os.sep)
	os.mkdir(userPreferencesDir + 'imageCache' + os.sep)
	os.mkdir(userPreferencesDir + 'imageCache' + os.sep + 'users' + os.sep)
	os.mkdir(userPreferencesDir + 'imageCache' + os.sep + 'icon' + os.sep)
	os.mkdir(userPreferencesDir + 'imageCache' + os.sep + 'badges' + os.sep)
	showSplashScreen = True
	# save initial locationMethodType
	locationMethodFile = open(userPreferencesDir + 'locationMethodType.txt','w')
	print 'initial locationMethodType: %d' % locationMethodType
	locationMethodFile.write(str(locationMethodType) + '\n')
	locationMethodFile.close()
	time.sleep(1)
else:
	locationMethodFile = open(userPreferencesDir + 'locationMethodType.txt','r')
	i = 0
	for line in locationMethodFile:
		# print 'line: ' + line
		i = i + 1
		if (i == 1):
			locationMethodType = int(line)
	locationMethodFile.close()
	print 'loaded locationMethodType: %d' % locationMethodType

# redirect error and std out to files for crash reporting
fsock = open(os.path.expanduser('~') + os.sep + '.barriosquare' + os.sep + 'stderr.log', 'w')
sys.stderr = fsock

class SplashScreenDialog(QtGui.QDialog):
	def __init__(self, parent=None):
		QtGui.QDialog.__init__(self, parent)
		self.setWindowTitle(VERSION_STRING)
		self.resize(800,300)

		self.lblDesc = QtGui.QLabel(VERSION_STRING + ': Welcome! By using this application which makes extensive use of the foursquare.com API you agree to be bound by terms at http://foursquare.com/legal/terms. This application is a 3rd party application not affiliated with or endorsed by foursquare.com. This application is distributed on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or implied.',self)
		self.lblDesc.setGeometry(5,5,700,300)
		self.lblDesc.setWordWrap(True)
		self.lblDesc.setAlignment(QtCore.Qt.AlignTop)

		self.bttnOk = QtGui.QPushButton('OK',self)
		self.bttnOk.setGeometry(620,205,175,80)
		self.bttnOk.setStyleSheet(QPUSHBUTTON_DEFAULT)

		self.connect(self.bttnOk, QtCore.SIGNAL('clicked()'),
			self.doOkClicked)
	
	def doOkClicked(self):
		self.close()

class ProcessingDialog(QtGui.QDialog):
	def __init__(self, title, txt, parent=None):
		QtGui.QDialog.__init__(self, parent)
		self.setWindowTitle(title)
		p = self.palette()
		p.setColor(QtGui.QPalette.Window, QtGui.QColor(0, 0, 0))
		self.setPalette(p)
		self.resize(800,200)

		global qb
		if qb.simpleNetworkTest():	
			self.lblLoadingIcon = QtGui.QLabel('',self)
			self.loadingGif = QtGui.QMovie(APP_DIRECTORY + 'loading2.gif', QtCore.QByteArray(), self)
			self.loadingGif.setCacheMode(QtGui.QMovie.CacheAll)
			self.loadingGif.setSpeed(100)
			self.loadingGif.setBackgroundColor(QtGui.QColor(0, 0, 0))
			self.lblLoadingIcon.setGeometry(10,10,50,50)
			self.lblLoadingIcon.setMovie(self.loadingGif)
			self.loadingGif.start()

			# add descriptive text
			self.lblText = QtGui.QLabel(txt, self)
			self.lblText.setGeometry(65,5,600,100)
			self.lblText.setWordWrap(True)
			self.lblText.setAlignment(QtCore.Qt.AlignTop)
		else:
			self.lblError = QtGui.QLabel('Error: Unable to contact api.foursquare.com. Please check your Internet connection and try again.',self)
			self.lblError.setGeometry(5,5,600,190)
			self.lblError.setWordWrap(True)
			self.lblError.setAlignment(QtCore.Qt.AlignTop)

			self.bttnOk = QtGui.QPushButton('OK',self)
			self.bttnOk.setGeometry(620,5,175,80)
			self.bttnOk.setStyleSheet(QPUSHBUTTON_DEFAULT)

		self.lblPoweredby = QtGui.QLabel('',self)
		self.lblPoweredby.setGeometry(5,164,225,36)
		poweredbyPixmap = QtGui.QPixmap(APP_DIRECTORY + 'powerbyfoursquare2.png')
		poweredbyPixmap2 = poweredbyPixmap.scaled(QtCore.QSize(225,36), QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)		
		self.lblPoweredby.setPixmap(poweredbyPixmap2)

		
class NearbyWorkerThread(QtCore.QThread):
	def __init__(self, parent = None):
    		QtCore.QThread.__init__(self, parent)
		self.exiting = False

	def run(self):
		print 'NearbyWorkerThread.run() Executing thread logic'
		client3 = oauthclient.SimpleOAuthClient('api.foursquare.com', 80, API_PREFIX_URL+'venues', ACCESS_TOKEN_URL, AUTHORIZATION_URL)
		consumer = oauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
		signature_method_plaintext = oauth.OAuthSignatureMethod_PLAINTEXT()
		signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
	
		global currentLatitude
		global currentLongitude

		nearbyParams = {
			'l'	:	30,
			'geolat':	currentLatitude,
			'geolong':	currentLongitude,
		}
		oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, callback=CALLBACK_URL, http_url=API_PREFIX_URL+'venues', parameters=nearbyParams)
		oauth_request.sign_request(signature_method_plaintext, consumer, fsRequestToken)
		print oauth_request.to_postdata()
		nearbyResultXml = client3.access_resource(oauth_request, http_url=API_PREFIX_URL+'venues', requestType='GET')
		# print nearbyResultXml		
		# save venue data to cache file
		nearbyCacheFile = open(userPreferencesDir + 'nearbyCache.xml','w')
		nearbyCacheFile.write(nearbyResultXml)
		nearbyCacheFile.close()	

	def __del__(self):
		self.exiting = True
		self.wait()

class RefreshFriendsWorkerThread(QtCore.QThread):
	def __init__(self, parent = None):
    		QtCore.QThread.__init__(self, parent)
		self.exiting = False

	def run(self):
		global infoNoticeString
		print 'RefreshFriendsWorkerThread.run() Executing thread logic'
		client3 = oauthclient.SimpleOAuthClient('api.foursquare.com', 80, API_PREFIX_URL+'checkins', ACCESS_TOKEN_URL, AUTHORIZATION_URL)
		consumer = oauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
		signature_method_plaintext = oauth.OAuthSignatureMethod_PLAINTEXT()
		signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
	
		global currentLatitude
		global currentLongitude

		nearbyParams = {
			'geolat':	currentLatitude,
			'geolong':	currentLongitude,
			'oauth_token':	fsKey,
			'oauth_token_secret':	fsSecret
		}
		oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, callback=CALLBACK_URL, http_url=API_PREFIX_URL+'checkins', parameters=nearbyParams)
		oauth_request.sign_request(signature_method_plaintext, consumer, fsRequestToken)
		# print oauth_request.to_postdata()
		checkinsResultXml = client3.access_resource(oauth_request, http_url=API_PREFIX_URL+'checkins', requestType='GET')
		# print checkinsResultXml		
		parseSuccess = False
		try:
			checkinsXml = parseString(checkinsResultXml)
			parseSuccess = True
			# save venue data to cache file
			checkinsCacheFile = open(userPreferencesDir + 'checkinsResultsCache.xml','w')
			checkinsCacheFile.write(checkinsResultXml)
			checkinsCacheFile.close()	
		except xml.parsers.expat.ExpatError:
			print 'error parsing checkinsResultXml'
			parseSuccess = False
			infoNoticeString = 'Error: api.foursquare.com problem refreshing friends'
			self.emit(QtCore.SIGNAL('displayInfoNotice()'))
			# if file doesn't exist save an empty xml doc to prevent endless retry
			if (not os.path.exists(userPreferencesDir + 'checkinsResultsCache.xml')):
				checkinsCacheFile = open(userPreferencesDir + 'checkinsResultsCache.xml','w')
				checkinsCacheFile.write('<?xml version="1.0" encoding="UTF-8"?><checkins/>')
				checkinsCacheFile.close()	
				
	
		if parseSuccess == True:
			checkinNodes = checkinsXml.getElementsByTagName('checkin')
			for node in checkinNodes:
				# get photo
				photoURL = node.getElementsByTagName('photo')[0].firstChild.data

				photoURLchunks = photoURL.split('/')
				photoFile = userPreferencesDir + 'imageCache' + os.sep + 'users' + os.sep + photoURLchunks[3] + '_' + photoURLchunks[4]
				# print 'photoFile: ' + photoFile			
				# if cached file doesn't exist for user, download it now
				if not os.path.exists(photoFile):
					global qb
					qb.getUserPhoto(photoURL)	

	def __del__(self):
		self.exiting = True
		self.wait()

class CheckinWorkerThread(QtCore.QThread):
	def __init__(self, parent = None):
    		QtCore.QThread.__init__(self, parent)
		self.exiting = False

	def setup(self, pFriends, pTwitter, pFacebook, vID, shoutStr):
		# print '(setup) shout: '+shoutStr
		# print '(setup) venueID %d' % vID
		self.shout = shoutStr
		self.pingFriends = pFriends
		self.pingTwitter = pTwitter
		self.pingFacebook = pFacebook
		self.venueID = vID

	def run(self):
		print 'Executing thread logic'
		global FakeCheckin
		global infoNoticeString

		print '*** check in data ***'
		print currentLatitude
		print currentLongitude
		print self.pingFriends
		print self.pingTwitter
		print self.pingFacebook
		print self.venueID
		print self.shout
		print fsKey
		print fsSecret
		print '*** end check in data ***'


		if (FakeCheckin == False):
			client3 = oauthclient.SimpleOAuthClient('api.foursquare.com', 80, API_PREFIX_URL+'checkin', ACCESS_TOKEN_URL, AUTHORIZATION_URL)
			consumer = oauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
			signature_method_plaintext = oauth.OAuthSignatureMethod_PLAINTEXT()
			signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()


			isPrivate = 1
			if self.pingFriends == True:
				isPrivate = 0
			isTwitter = 0
			if self.pingTwitter == True:
				isTwitter = 1
			isFacebook = 0
			if self.pingFacebook == True:
				isFacebook = 1
	
			nearbyParams = {
				'vid'	:	self.venueID,
				'geolat' : 	currentLatitude,
				'geolong':	currentLongitude,
				'private':	isPrivate,
				'twitter':	isTwitter,
				'facebook':	isFacebook,
				'shout'	 :	self.shout,
				'oauth_token':	fsKey,
				'oauth_token_secret':	fsSecret
			}
			oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, callback=CALLBACK_URL, http_url=API_PREFIX_URL+'checkin', parameters=nearbyParams)
			oauth_request.sign_request(signature_method_plaintext, consumer, fsRequestToken)
			# print oauth_request.to_postdata()
			checkinResultXmlString = client3.access_resource(oauth_request, http_url=API_PREFIX_URL+'checkin', requestType='POST')
			print checkinResultXmlString		
			parseSuccess = False
			try:
				checkinResultXml = parseString(checkinResultXmlString)
				parseSuccess = True
				checkinCacheFile = open(userPreferencesDir + 'checkInCache.xml','w')
				checkinCacheFile.write(checkinResultXmlString)
				checkinCacheFile.close()

				# also store a copy tagged with the venueID 
				checkinCacheFile2 = open(userPreferencesDir + 'checkInCache_vid' + str(self.venueID) + '.xml','w')
				checkinCacheFile2.write(checkinResultXmlString)
				checkinCacheFile2.close()		

			except xml.parsers.expat.ExpatError:
				print 'error parsing checkinResult'
				parseSuccess = False
				infoNoticeString = 'Error: api.foursquare.com problem. Check history before trying again'
				self.emit(QtCore.SIGNAL('displayInfoNotice()'))	
		else:
			# sleep fake checkin for 5 seconds to simulate real checkin
			time.sleep(5)		


	def __del__(self):
		self.exiting = True
		self.wait()

class VenueListItem(QtGui.QWidget):
	def __init__(self, parent=None):
        	QtGui.QWidget.__init__(self, parent)

	def setText(self, text1, text2):
		self.mainText = text1
		self.subtitleText = text2

	def paintEvent(self, event):
		paint = QtGui.QPainter()
		paint.begin(self)

		paint.setPen(QtGui.QColor(255, 255, 255))
		paint.setBrush(QtGui.QColor(255, 255, 255))
		paint.drawRect(0, 0, 800, 75)

		paint.setPen(QtGui.QColor(168, 34, 3))
		font = QtGui.QFont('Helvetica', 25, QtGui.QFont.Light)
		paint.setFont(font)
		paint.drawText(3, 34, self.mainText)

		font = QtGui.QFont('Helvetica', 15, QtGui.QFont.Light)
		paint.setFont(font)
		paint.drawText(6, 62, self.subtitleText)

		# draw line
		pen = QtGui.QPen(QtGui.QColor(20, 20, 20), 1, QtCore.Qt.DotLine)
		paint.setPen(pen)
		paint.setBrush(QtCore.Qt.NoBrush)
	        paint.drawLine(1, 74, 800, 74)

		paint.end()

class BadgeListItem(QtGui.QWidget):
	def __init__(self, parent=None):
        	QtGui.QWidget.__init__(self, parent)

	def setText(self, text1, text2, iconPath):
		self.mainText = text1
		self.subtitleText = text2
		self.lblIcon = QtGui.QLabel('',self)
		self.lblIcon.setGeometry(5, 5, 57, 57)
		if iconPath != None:
			self.lblIcon.setPixmap(QtGui.QPixmap(iconPath))

	def paintEvent(self, event):
		paint = QtGui.QPainter()
		paint.begin(self)

		paint.setPen(QtGui.QColor(255, 255, 255))
		paint.setBrush(QtGui.QColor(255, 255, 255))
		paint.drawRect(0, 0, 800, 75)

		paint.setPen(QtGui.QColor(168, 34, 3))
		font = QtGui.QFont('Helvetica', 30, QtGui.QFont.Light)
		paint.setFont(font)
		paint.drawText(73, 34, self.mainText)

		font = QtGui.QFont('Helvetica', 15, QtGui.QFont.Light)
		paint.setFont(font)
		paint.drawText(76, 62, self.subtitleText)

		# draw line
		pen = QtGui.QPen(QtGui.QColor(20, 20, 20), 1, QtCore.Qt.DotLine)
		paint.setPen(pen)
		paint.setBrush(QtCore.Qt.NoBrush)
	        paint.drawLine(1, 74, 800, 74)

		paint.end()

class FriendListItem(QtGui.QWidget):
	def __init__(self, parent=None):
        	QtGui.QWidget.__init__(self, parent)

	def setText(self, text1, text2, text3, iconPath):
		self.mainText = text1
		self.subtitleText = text2
		self.dateText = text3
		self.lblIcon = QtGui.QLabel('',self)
		self.lblIcon.setGeometry(5, 5, 65, 65)
		if iconPath != None:
			self.lblIcon.setPixmap(QtGui.QPixmap(iconPath))

	def paintEvent(self, event):
		paint = QtGui.QPainter()
		paint.begin(self)

		paint.setPen(QtGui.QColor(255, 255, 255))
		paint.setBrush(QtGui.QColor(255, 255, 255))
		paint.drawRect(0, 0, 800, 75)

		paint.setPen(QtGui.QColor(168, 34, 3))
		font = QtGui.QFont('Helvetica', 23, QtGui.QFont.Light)
		paint.setFont(font)
		paint.drawText(73, 34, self.mainText)

		font = QtGui.QFont('Helvetica', 15, QtGui.QFont.Light)
		paint.setFont(font)
		paint.drawText(76, 62, self.subtitleText)

		# draw line
		pen = QtGui.QPen(QtGui.QColor(20, 20, 20), 1, QtCore.Qt.DotLine)
		paint.setPen(pen)
		paint.setBrush(QtCore.Qt.NoBrush)
	        paint.drawLine(1, 74, 800, 74)

		paint.end()

class TipListItem(QtGui.QWidget):
	def __init__(self, height, parent=None):
        	QtGui.QWidget.__init__(self, parent)
		self.widgetHeight = height

	def setText(self, text1, iconPath):
		self.mainText = text1
		self.lblIcon = QtGui.QLabel('',self)
		self.lblIcon.setGeometry(700, 5, 65, 65)
		if iconPath != None:
			self.lblIcon.setPixmap(QtGui.QPixmap(iconPath))

	def paintEvent(self, event):
		paint = QtGui.QPainter()
		paint.begin(self)

		paint.setPen(QtGui.QColor(255, 255, 255))
		paint.setBrush(QtGui.QColor(255, 255, 255))
		paint.drawRect(0, 0, 800, self.widgetHeight)

		doc = QtGui.QTextDocument()
		doc.setHtml(self.mainText)
		doc.setTextWidth(700)

		paint.setPen(QtGui.QColor(168, 34, 3))
		font = QtGui.QFont('Helvetica', 15, QtGui.QFont.Light)
		paint.setFont(font)
		rect = QtCore.QRectF(0,5,800,self.widgetHeight-5)
		options = QtGui.QTextOption()
		options.setWrapMode(QtGui.QTextOption.WordWrap)
		options.setAlignment(QtCore.Qt.AlignLeft)
		# rect = paint.boundingRect(rect, self.mainText, options)	
		# print rect

		doc.drawContents(paint, rect)

		# draw line
		pen = QtGui.QPen(QtGui.QColor(20, 20, 20), 1, QtCore.Qt.DotLine)
		paint.setPen(pen)
		paint.setBrush(QtCore.Qt.NoBrush)
	        paint.drawLine(1, self.widgetHeight - 1, 800, self.widgetHeight - 1)

		paint.end()

class CheckInDialog(QtGui.QDialog):
	def __init__(self, id, venueName, parent=None):
		QtGui.QDialog.__init__(self, parent)

		p = self.palette()
		p.setColor(QtGui.QPalette.Window, QtGui.QColor(0, 0, 0))
		self.setPalette(p)
		
		print 'Place ID:' + id
		self.venueID = id

		self.setWindowTitle('Check-In')
		self.lblTitle = QtGui.QLabel('Checking in @ ' + venueName,self)
		self.lblTitle.setFont(QtGui.QFont('Helvetica', 30))
		self.lblTitle.setGeometry(5,5,800,50)

		self.chkPingFriends = QtGui.QCheckBox('Ping my Friends',self)
		self.chkPingFriends.setGeometry(5,50,500,40)
		self.chkPingFriends.setChecked(True)

		global pingTwitter

		self.chkTwitter = QtGui.QCheckBox('Tweet this check-in',self)
		self.chkTwitter.setGeometry(5,90,500,40)
		self.chkTwitter.setChecked(pingTwitter)

		global pingFacebook

		self.chkFacebook = QtGui.QCheckBox('Post this check-in to facebook',self)
		self.chkFacebook.setGeometry(5,130,500,40)
		self.chkFacebook.setChecked(pingFacebook)

		self.txtShout = QtGui.QLineEdit(self)
		self.txtShout.setGeometry(5, 180, 500, 50)

		self.bttnCheckIn = QtGui.QPushButton('Check In!',self)
		self.bttnCheckIn.setGeometry(5,250,300,120)
		self.bttnCheckIn.setStyleSheet(QPUSHBUTTON_DEFAULT)

		self.connect(self.bttnCheckIn, QtCore.SIGNAL('clicked()'),
			self.doCheckInButtonClicked)

		self.resize(800,480)

		self.checkinWorker = CheckinWorkerThread()
		self.connect(self.checkinWorker, QtCore.SIGNAL('finished()'), self.checkinFinished)
		self.connect(self.checkinWorker, QtCore.SIGNAL('displayInfoNotice()'), self.displayInfoNoticeGlobal)

		self.lblLoadingIcon = QtGui.QLabel('',self)
		self.loadingGif = QtGui.QMovie(APP_DIRECTORY + 'loading2.gif', QtCore.QByteArray(), self)
		self.loadingGif.setCacheMode(QtGui.QMovie.CacheAll)
		self.loadingGif.setSpeed(100)
		self.loadingGif.setBackgroundColor(QtGui.QColor(0, 0, 0))
		self.lblLoadingIcon.setGeometry(330,290,50,50)
		self.lblLoadingIcon.setMovie(self.loadingGif)
		self.lblLoadingIcon.hide()

	def displayInfoNoticeGlobal(self):
		global infoNoticeString
		global qb
		qb.displayInfoNotice(infoNoticeString)

	def checkinFinished(self):
		print 'checkinFinished'
		self.close()
		print 'launch Dialog from MainWindow with checkin details'
		global qb
		qb.displayCheckinDetails()

	def doCheckInButtonClicked(self):
		print 'doCheckInButtonClicked'
		print 'VenueID: ' + self.venueID
		venID = int(self.venueID)
		shout = ''
		if len(str(self.txtShout.text()).strip()) > 0:
			shout = str(self.txtShout.text()).strip()

		global shoutString
		shoutString = shout
		global checkinVenueID
		checkinVenueID = venID

		self.loadingGif.start()
		self.lblLoadingIcon.show()
		self.bttnCheckIn.setEnabled(False)
		self.bttnCheckIn.setText('Checking In...')
		self.bttnCheckIn.setEnabled(False)

		self.checkinWorker.setup(self.chkPingFriends.isChecked(),self.chkTwitter.isChecked(),self.chkFacebook.isChecked(),venID,shout)
		self.checkinWorker.start()

class CheckinResultsDialog(QtGui.QDialog):
	def __init__(self, parent=None):
		QtGui.QDialog.__init__(self, parent)

		self.setWindowTitle('You have checked in!')

		self.lblMessage1 = QtGui.QLabel('',self)
		self.lblMessage1.setGeometry(10,10,780,40)
	
		self.lblPoints = QtGui.QLabel('',self)
		self.lblPoints.setGeometry(10,50,500,40)

		self.lblMayor = QtGui.QLabel('',self)
		self.lblMayor.setGeometry(10,80,520,100)
		self.lblMayor.setWordWrap(True)

		self.resize(800,240)


		# parse the checkin
		checkinXmlFile = open(userPreferencesDir + 'checkInCache.xml','r')
		checkinXmlString = ''
		for line in checkinXmlFile:
			checkinXmlString += line
		checkinXmlFile.close()
		print checkinXmlString
		checkinXml = parseString(checkinXmlString)
		# get the message
		message = ''
		if checkinXml.getElementsByTagName('message').length > 0:
			message = checkinXml.getElementsByTagName('message')[0].firstChild.data
		self.lblMessage1.setText(message)

		scoringNode = checkinXml.getElementsByTagName('scoring')
		points = ''
		hasIcon = False
		if scoringNode.length > 0:
			pointsNode = scoringNode[0].getElementsByTagName('points')
			if (pointsNode.length > 0):
				points = pointsNode[0].firstChild.data
				if int(points) == 1:
					points += ' point'
				else:
					points += ' points'
			messageNode = scoringNode[0].getElementsByTagName('message')
			if messageNode.length > 0 and pointsNode.length > 0:
				points += ', '
			if messageNode.length > 0:
				points += messageNode[0].firstChild.data
	
			iconNode = scoringNode[0].getElementsByTagName('icon')

			if iconNode.length > 0:
				# get icon
				iconUrl = iconNode[0].firstChild.data
				photoURLchunks = iconUrl.split('/')
				iconFile = userPreferencesDir + 'imageCache' + os.sep + 'icon' + os.sep + photoURLchunks[4] + '_' + photoURLchunks[5]
				if not os.path.exists(iconFile):
					self.downloadIcon(iconUrl)
				self.lblPoints.setGeometry(10, 60, 25, 25)
				self.lblPoints.setPixmap(QtGui.QPixmap(iconFile))
				hasIcon = True
		
		if hasIcon:
			self.lblPointsText = QtGui.QLabel('',self)
			self.lblPointsText.setGeometry(40,50,760,40)
			self.lblPointsText.setText(points)
		else:
			self.lblPoints.setText(points)

		# add mayor info
		mayorNode = checkinXml.getElementsByTagName('mayor')
		if mayorNode.length > 0:
			mayorType = mayorNode[0].getElementsByTagName('type')[0].firstChild.data
			mayorMessageNodes = mayorNode[0].getElementsByTagName('message')
			if mayorMessageNodes.length > 0:
				mayorMessage = mayorMessageNodes[0].firstChild.data
				self.lblMayor.setText(mayorMessage)		
					
		# add dismiss button
		self.bttnDismiss = QtGui.QPushButton('Dismiss', self)
		self.bttnDismiss.setGeometry(595,135,200,100)	
		self.bttnDismiss.setStyleSheet(QPUSHBUTTON_DEFAULT)	

		self.connect(self.bttnDismiss, QtCore.SIGNAL('clicked()'),
			QtCore.SLOT('close()'))

	def downloadIcon(self, iconUrl):
		print 'downloadIcon'
		photoResponse = urllib2.urlopen(iconUrl)
		photoData = photoResponse.read()

		photoURLchunks = iconUrl.split('/')
		saveFile = photoURLchunks[4] + '_' + photoURLchunks[5]

		photoFile = open(userPreferencesDir + 'imageCache' + os.sep + 'icon' + os.sep + saveFile,'w')
		photoFile.write(photoData)
		photoFile.close()

class PlaceInfoLoaderWorkerThread(QtCore.QThread):
	def __init__(self, parent = None):
    		QtCore.QThread.__init__(self, parent)
		self.exiting = False

	def setup(self, id, placeDlg, forceRefresh):
		self.id = id
		self.placeDlg = placeDlg
		self.forceRefresh = forceRefresh

	def run(self):
		print 'PlaceInfoLoaderWorkerThread.run() Executing thread logic'
		print 'Venue ID: ' + self.id
		venueCacheFileName = userPreferencesDir + 'venueCache' + os.sep + self.id.toAscii() + '.xml'

		if (self.forceRefresh == False):
			# look to see if cache file is old or not existing
			if (not os.path.exists(venueCacheFileName)):
				self.forceRefresh = True
			else:
				cacheFileTime = os.path.getmtime(venueCacheFileName)
				currentTime = time.time()
				timediff = currentTime - cacheFileTime
				# for refresh
				if (timediff > 3600):
					self.forceRefresh = True

		mayorPhotoUrl = None
		mayorName = None
		mayorUserID = 0
		mayorCheckinCount = 0
		global qb

		parseSuccess = False

		if (self.forceRefresh == True):
			client4 = oauthclient.SimpleOAuthClient('api.foursquare.com', 80, API_PREFIX_URL+'venue', ACCESS_TOKEN_URL, AUTHORIZATION_URL)
			consumer = oauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
			signature_method_plaintext = oauth.OAuthSignatureMethod_PLAINTEXT()
			signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
	
			nearbyParams = {
				'vid':	str(self.id),
			}
			oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, callback=CALLBACK_URL, http_url=API_PREFIX_URL+'venue', parameters=nearbyParams)
			oauth_request.sign_request(signature_method_plaintext, consumer, fsRequestToken)
			print oauth_request.to_postdata()
			nearbyResult = client4.access_resource(oauth_request, http_url=API_PREFIX_URL+'venue', requestType='GET')
			print nearbyResult
			# save result to cache 
			nearbyLocationCacheFile = open(venueCacheFileName,'w')
			nearbyLocationCacheFile.write(nearbyResult)
			nearbyLocationCacheFile.close()
			# parse mayor information and download pic if not cached
			try:
				nearbyXml = parseString(nearbyResult)
				parseSuccess = True
			except xml.parsers.expat.ExpatError:
				print 'error parsing nearbyResult'
				parseSuccess = False
			if parseSuccess == True:
				mayorNodes = nearbyXml.getElementsByTagName('mayor')
				if mayorNodes.length > 0:
					mayorUserID = int(mayorNodes[0].getElementsByTagName('user')[0].getElementsByTagName('id')[0].firstChild.data)
					mayorCheckinCount = int(mayorNodes[0].getElementsByTagName('count')[0].firstChild.data)
					mayorPhotoUrl = mayorNodes[0].getElementsByTagName('photo')[0].firstChild.data
					print 'mayor photo url: ' + mayorPhotoUrl
					mayorName = mayorNodes[0].getElementsByTagName('firstname')[0].firstChild.data
					if mayorNodes[0].getElementsByTagName('lastname').length > 0:
						mayorName += ' ' + mayorNodes[0].getElementsByTagName('lastname')[0].firstChild.data
					# urllib request to download file
					qb.getUserPhoto(mayorPhotoUrl)
			else:
				print 'parseSuccess is False'
		else:
			# load it from the file
			nearbyLocationCacheFile = open(venueCacheFileName,'r')
			nearbyXmlString = ''
			for line in nearbyLocationCacheFile:
				nearbyXmlString += line
			nearbyLocationCacheFile.close()
			print nearbyXmlString
			try:
				nearbyXml = parseString(nearbyXmlString)
				parseSuccess = True
			except xml.parsers.expat.ExpatError:
				print 'error parsing nearbyResult'
				parseSuccess = False

			if parseSuccess == True:
				mayorNodes = nearbyXml.getElementsByTagName('mayor')
				if mayorNodes.length > 0:
					mayorUserID = int(mayorNodes[0].getElementsByTagName('user')[0].getElementsByTagName('id')[0].firstChild.data)
					mayorCheckinCount = int(mayorNodes[0].getElementsByTagName('count')[0].firstChild.data)
					mayorPhotoUrl = mayorNodes[0].getElementsByTagName('photo')[0].firstChild.data
					mayorName = mayorNodes[0].getElementsByTagName('firstname')[0].firstChild.data
					if mayorNodes[0].getElementsByTagName('lastname').length > 0:
						mayorName += ' ' + mayorNodes[0].getElementsByTagName('lastname')[0].firstChild.data
			else:
				print 'parseSuccess is false'

		if parseSuccess == True:
			nearbyNodes = nearbyXml.getElementsByTagName('venue')
			venueName = ''
			addressString = ''
			cityString = ''
			phoneString = ''
			strLatLon = ''
			node = nearbyNodes[0]
			venueName = node.getElementsByTagName('name')[0].firstChild.data
			print 'address nodes length: %d' % node.getElementsByTagName('address').length
			addressNode = node.getElementsByTagName('address')
			if addressNode.length > 0:
				if addressNode[0].firstChild != None:
					addressString = addressNode[0].firstChild.data

			crossstreetNode = node.getElementsByTagName('crossstreet')
			if crossstreetNode.length > 0:
				if crossstreetNode[0].firstChild != None:
					addressString += ' (' + crossstreetNode[0].firstChild.data + ')'

			cityString = node.getElementsByTagName('city')[0].firstChild.data
			if (node.getElementsByTagName('state').length > 0):
				cityString += ', ' + node.getElementsByTagName('state')[0].firstChild.data
			if (node.getElementsByTagName('zip').length > 0):
				cityString += ' ' + node.getElementsByTagName('zip')[0].firstChild.data
			if node.getElementsByTagName('phone').length > 0:
				phoneString = '' +  node.getElementsByTagName('phone')[0].firstChild.data

			strLatLon = node.getElementsByTagName('geolat')[0].firstChild.data + ',' + node.getElementsByTagName('geolong')[0].firstChild.data

			self.placeDlg.venueName = venueName
			self.placeDlg.addressString = addressString
			self.placeDlg.cityString = cityString
			self.placeDlg.phoneString = phoneString
			self.placeDlg.strLatLon = strLatLon
		
			# see if there are specials
			specialsNodes = nearbyXml.getElementsByTagName('special')
			# add button for specials
			hasSpecials = False
			specialsText = ''
			if specialsNodes.length > 0:
				hasSpecials = True
				if specialsNodes.length == 1:
					specialsText = '1 special'
				else:
					specialsText = '%d specials' % specialsNodes.length
	
			self.placeDlg.hasSpecials = hasSpecials
			self.placeDlg.specialsText = specialsText
	
			# see if there are any checkins here (last 3 hours, if so add "Recent Checkins" button to UI)
			checkinNodes = nearbyXml.getElementsByTagName('checkin')
			if checkinNodes.length > 0:
				for node in checkinNodes:
					checkinPhotoUrl = node.getElementsByTagName('photo')[0].firstChild.data
					# download photo if file cache not existent
					checkinURLchunks = checkinPhotoUrl.split('/')
					checkinPhotoFile = userPreferencesDir + 'imageCache' + os.sep + 'users' + os.sep + checkinURLchunks[3] + '_' + checkinURLchunks[4]
					# print 'checkinPhotoFile: ' + checkinPhotoFile
					if not os.path.exists(checkinPhotoFile):
						qb.getUserPhoto(checkinPhotoUrl)

			venueCheckinCount = checkinNodes.length
			venueCheckinCount = 1
			venueCheckinText = ''
			if venueCheckinCount > 0:
				if venueCheckinCount == 1:
					venueCheckinText = '1 checkin'
				else:
					venueCheckinText = '%d checkins' % venueCheckinCount

			self.placeDlg.venueCheckinText = venueCheckinText
			self.placeDlg.venueCheckinCount = venueCheckinCount
			self.placeDlg.tipsText = '0 tips'
			tipNodes = nearbyXml.getElementsByTagName('tip')
			if (tipNodes.length > 0):
				print 'Has Tips'
				self.placeDlg.tipsText = '%d Tips' % tipNodes.length	
				for node in tipNodes:
					tipPhotoUrl = node.getElementsByTagName('photo')[0].firstChild.data			
					tipURLchunks = tipPhotoUrl.split('/')
					tipPhotoFile = userPreferencesDir + 'imageCache' + os.sep + 'users' + os.sep + tipURLchunks[3] + '_' + tipURLchunks[4]
					# print 'tipPhotoFile: ' + tipPhotoFile
					if not os.path.exists(tipPhotoFile):
						qb.getUserPhoto(tipPhotoUrl)

			self.placeDlg.mayorPhotoFile = ''
			self.placeDlg.mayorName = ''
			if mayorPhotoUrl != None:
				print 'display mayorPhoto: ' + mayorPhotoUrl
				print 'mayor: ' + mayorName
				print 'mayorUserID: %d' % mayorUserID

				global loggedInUserID
				if loggedInUserID == mayorUserID:
					mayorName = 'You are still the mayor! ('
				else:
					mayorName += ' is the mayor ('
				mayorName += '%d' % mayorCheckinCount
				mayorName += 'x)'

				self.placeDlg.mayorName = mayorName
				# set mayor


				# set photo
				photoURLchunks = mayorPhotoUrl.split('/')
				photoFile = userPreferencesDir + 'imageCache' + os.sep + 'users' + os.sep + photoURLchunks[3] + '_' + photoURLchunks[4]
				# print 'photoFile: ' + photoFile			
				# if cached file doesn't exist for mayor, download it now
				if not os.path.exists(photoFile):
					qb.getUserPhoto(mayorPhotoUrl)
				self.placeDlg.mayorPhotoFile = photoFile
			time.sleep(1)
		else:
			print 'parseSuccess is False'


	def __del__(self):
		self.exiting = True
		self.wait()

class BadgesDialog(QtGui.QDialog):
	def __init__(self, uid, parent=None):
		QtGui.QDialog.__init__(self, parent)	
		self.setWindowTitle('My Badges')
		self.resize(800,480)
		self.badgesListWidget = QtGui.QListWidget(self)
		self.badgesListWidget.setGeometry(5, 5, 820, 370)

		# load info
		if int(uid) == 0:
			cacheFileName = 'userDetailCache.xml'
		else:
			cacheFileName = 'userDetailCache_' + str(uid) + '.xml'
		userXmlFile = open(userPreferencesDir + cacheFileName,'r')
		userXmlString = ''
		for line in userXmlFile:
			userXmlString += line
		userXmlFile.close()
		print userXmlString
		userXml = parseString(userXmlString)
		badgesNodes = userXml.getElementsByTagName('badge')
		if badgesNodes.length > 0:
			for node in badgesNodes:
				badgeIconURL = node.getElementsByTagName('icon')[0].firstChild.data
				badgeURLchunks = badgeIconURL.split('/')
				badgeFile = userPreferencesDir + 'imageCache' + os.sep + 'badges' + os.sep + badgeURLchunks[4] + '_' + badgeURLchunks[5]
				badgeDescr = node.getElementsByTagName('description')[0].firstChild.data
				badgeName = node.getElementsByTagName('name')[0].firstChild.data
				badgeItem = QtGui.QListWidgetItem('',self.badgesListWidget)
				badgeItem.setSizeHint(QtCore.QSize(770, 75))
				wItem = BadgeListItem()
				wItem.setText(badgeName,badgeDescr,badgeFile)
				self.badgesListWidget.setItemWidget(badgeItem,wItem)
				badgeItem.setStatusTip(node.getElementsByTagName('id')[0].firstChild.data)

class MyFriendsDialog(QtGui.QDialog):
	def __init__(self, parent=None):
		QtGui.QDialog.__init__(self, parent)	


class MyLocationDialog(QtGui.QDialog):
	def __init__(self, strLatLon, parent=None):
		QtGui.QDialog.__init__(self, parent)	
		self.strLatLon = strLatLon
		self.setWindowTitle('My Information')
		self.resize(800,480)
		self.web = QtWebKit.QWebView(self)
		
		self.web.load(QtCore.QUrl('http://maps.google.com/maps/api/staticmap?center=' + self.strLatLon + '&size=600x245&maptype=roadmap&markers=color:red|' + self.strLatLon + '&zoom=14&sensor=false&key=' + GOOGLE_MAPS_API_KEY))
		self.web.setGeometry(5,5,600,245)

		self.lblInfo = QtGui.QLabel('NOTE: Your actual location may be different than that which is indicated on the map due to differences in how the location of your device is obtained (GPS, Cell Tower, etc)',self);
		self.lblInfo.setGeometry(5,250,600,120)
		self.lblInfo.setWordWrap(True)

		self.web.show()

		# add buttons for badges, map, etc
		self.bttnMap = QtGui.QPushButton('Google Map',self)
		self.bttnMap.setGeometry(610,5,185,80)
		self.bttnMap.setStyleSheet(QPUSHBUTTON_DEFAULT)
		if badgeCount == 1:
			badgeStr = '%d Badge' % badgeCount
		else:
			badgeStr = '%d Badges' % badgeCount
		# add buttons for badges, map, etc
		self.bttnBadges = QtGui.QPushButton(badgeStr,self)
		self.bttnBadges.setGeometry(610,95,185,80)
		self.bttnBadges.setStyleSheet(QPUSHBUTTON_DEFAULT)

		self.bttnRefresh = QtGui.QPushButton('Refresh Location',self)
		self.bttnRefresh.setGeometry(610,185,185,80)
		self.bttnRefresh.setStyleSheet(QPUSHBUTTON_DEFAULT)

		self.bttnFriends = QtGui.QPushButton('My Friends',self)
		self.bttnFriends.setGeometry(610,275,185,80)
		self.bttnFriends.setStyleSheet(QPUSHBUTTON_DEFAULT)

		self.connect(self.bttnBadges, QtCore.SIGNAL('clicked()'),
			self.doBadgesButtonClicked)

		self.connect(self.bttnRefresh, QtCore.SIGNAL('clicked()'),
			self.doRefreshLocationClicked)

	def doRefreshLocationClicked(self):
		print 'doRefreshLocationClicked'
		global locationManagerObj
		locationManagerObj.acquireLocationFix()

	def doBadgesButtonClicked(self):
		print 'doBagdesButtonClicked'
		global loggedInUserID
		self.badgesDlg = BadgesDialog(0)
		self.badgesDlg.show()

class WhosHereDialog(QtGui.QDialog):
	def __init__(self, venueID, parent=None):
		QtGui.QDialog.__init__(self, parent)	
		self.setWindowTitle('Who\'s Here')
		self.resize(800,480)
		self.whosHereListWidget = QtGui.QListWidget(self)
		self.whosHereListWidget.setGeometry(5, 5, 750, 370)

		venueCacheFileName = userPreferencesDir + 'venueCache' + os.sep + venueID + '.xml'
		nearbyLocationCacheFile = open(venueCacheFileName,'r')
		nearbyXmlString = ''
		for line in nearbyLocationCacheFile:
			nearbyXmlString += line
		nearbyLocationCacheFile.close()
		print nearbyXmlString
		nearbyXml = parseString(nearbyXmlString)
		checkinNodes = nearbyXml.getElementsByTagName('checkin')
		if checkinNodes.length > 0:
			for node in checkinNodes:
				checkinItem = QtGui.QListWidgetItem('',self.whosHereListWidget)
				checkinItem.setSizeHint(QtCore.QSize(770, 75))
				wItem = FriendListItem()
				checkinString = node.getElementsByTagName('firstname')[0].firstChild.data
				checkinString += ' ' + node.getElementsByTagName('lastname')[0].firstChild.data
				
				shoutNodes = node.getElementsByTagName('shout')
				# print 'shouts: %d' % shoutNodes.length
				if shoutNodes.length > 0:
					checkinString += ' ("' + shoutNodes[0].firstChild.data + '")'
				
				checkinPhotoUrl = node.getElementsByTagName('photo')[0].firstChild.data
				checkinURLchunks = checkinPhotoUrl.split('/')
				checkinPhotoFile = userPreferencesDir + 'imageCache' + os.sep + 'users' + os.sep + checkinURLchunks[3] + '_' + checkinURLchunks[4]

				wItem.setText(checkinString,'5 mins ago','',checkinPhotoFile)
				self.whosHereListWidget.setItemWidget(checkinItem,wItem)
				checkinItem.setStatusTip(node.getElementsByTagName('id')[0].firstChild.data)

class AddTipDialog(QtGui.QMainWindow):
	def __init__(self, venueID, venueName, parent=None):
		QtGui.QMainWindow.__init__(self, parent)	
		self.setWindowTitle('Add tip for ' + venueName)
		self.lblName = QtGui.QLabel('Add Tip',self)
		self.lblName.setGeometry(5,5,100,10)
		self.txtTip = QtGui.QTextEdit(self)
		self.txtTip.setAcceptRichText(False)
		self.txtTip.setGeometry(5,15,800,200)

		
class TipsDialog(QtGui.QMainWindow):
	def __init__(self, venueID, parent=None):
		QtGui.QMainWindow.__init__(self, parent)	
		self.setWindowTitle('Tips')
		self.resize(800,480)
		self.tipsListWidget = QtGui.QListWidget(self)
		self.tipsListWidget.setGeometry(5, 5, 790, 350)
		p = self.tipsListWidget.palette()
		p.setColor(QtGui.QPalette.Highlight, QtGui.QColor(255, 255, 184))
		p.setColor(QtGui.QPalette.Base, QtGui.QColor(255, 0, 0))
		p = self.tipsListWidget.setPalette(p)
		self.tipsListWidget.setStyleSheet(QLISTWIDGET_DEFAULT)

		venueCacheFileName = userPreferencesDir + 'venueCache' + os.sep + venueID + '.xml'
		nearbyLocationCacheFile = open(venueCacheFileName,'r')
		nearbyXmlString = ''
		for line in nearbyLocationCacheFile:
			nearbyXmlString += line
		nearbyLocationCacheFile.close()
		print nearbyXmlString
		nearbyXml = parseString(nearbyXmlString)
		
		venueName = nearbyXml.getElementsByTagName('name')[0].firstChild.data
		tipNodes = nearbyXml.getElementsByTagName('tip')
		if tipNodes.length > 0:
			tipStr = '%d' % tipNodes.length
			if tipNodes.length == 1:
				tipStr += ' tip for ' + venueName
			else:
				tipStr += ' tips for ' + venueName
			for node in tipNodes:
				tipItem = QtGui.QListWidgetItem('',self.tipsListWidget)

				tipString = '<b>' + node.getElementsByTagName('firstname')[0].firstChild.data
				if node.getElementsByTagName('lastname').length > 0:
					tipString += ' ' + node.getElementsByTagName('lastname')[0].firstChild.data
				tipString += '</b> says: <i>"'
				tipString += node.getElementsByTagName('text')[0].firstChild.data + '"</i>'
				
				# calculate the height of the row based on the length of the tip

				print 'line len: %d' % len(tipString)
				lines = math.ceil(len(tipString) / 40)
				print 'lines: %d' % lines
				height = lines * 30
				print 'height: %d' % height
				if height < 75:
					height = 75

	
				tipItem.setSizeHint(QtCore.QSize(730, height))
				wItem = TipListItem(height)

				photoUrl = node.getElementsByTagName('photo')[0].firstChild.data
				URLchunks = photoUrl.split('/')
				photoFile = userPreferencesDir + 'imageCache' + os.sep + 'users' + os.sep + URLchunks[3] + '_' + URLchunks[4]

				wItem.setText(tipString,photoFile)
				self.tipsListWidget.setItemWidget(tipItem,wItem)
				tipItem.setStatusTip(node.getElementsByTagName('id')[0].firstChild.data)
		else:
			tipStr = 'No tips for ' + venueName
		self.setWindowTitle(tipStr)
		# parse output

		
class PlaceInfoDialog(QtGui.QMainWindow):
	def __init__(self, id, mainWindow, parent=None):
		QtGui.QMainWindow.__init__(self, parent)	

		self.resize(800,480)

		# thread out reading results into separate thread

		print 'Place ID:' + id
		self.venueID = id.toAscii()

		# self.setModal(1)
		self.setWindowTitle('Place Info')
		self.venueName = ''

		self.addressString = ''
		self.cityString = ''
		self.phoneString = ''

		# hildonized probably doesn't need cancel button
		# self.bttnCancel = QtGui.QPushButton('Cancel', self)
		# self.bttnCancel.setGeometry(675, 25, 150, 80)

		self.lblName = QtGui.QLabel('',self)
		self.lblName.setFont(QtGui.QFont('Helvetica', 30))
		self.lblName.setGeometry(5,175,600,50)

		self.lblAddress = QtGui.QLabel('',self)
		self.lblAddress.setFont(QtGui.QFont('Helvetica', 15))
		self.lblAddress.setGeometry(5,210,600,50)

		self.lblCity = QtGui.QLabel('',self)
		self.lblCity.setFont(QtGui.QFont('Helvetica', 15))
		self.lblCity.setGeometry(5,230,600,50)

		self.lblPhone = QtGui.QLabel('',self)
		self.lblPhone.setFont(QtGui.QFont('Helvetica', 15))
		self.lblPhone.setGeometry(5,250,300,50)

		# add a button for tips
		self.bttnCheckIn = QtGui.QPushButton('Check-In Here',self)
		self.bttnCheckIn.setGeometry(620,10,175,80)
		self.bttnCheckIn.setStyleSheet(QPUSHBUTTON_DEFAULT)

		# add a button for tips
		self.bttnTips = QtGui.QPushButton('0 Tips',self)
		self.bttnTips.setGeometry(620,100,175,80)
		self.bttnTips.setStyleSheet(QPUSHBUTTON_DEFAULT)

		# add a button for venue
		self.bttnMap = QtGui.QPushButton('Links',self)
		self.bttnMap.setGeometry(620,190,175,80)
		self.bttnMap.setStyleSheet(QPUSHBUTTON_DEFAULT)

		# add label
		self.lblDisplay1 = QtGui.QLabel('',self)
		self.lblDisplay1.setGeometry(0,0,1,1)

		# add label
		self.lblDisplay2 = QtGui.QLabel('',self)
		self.lblDisplay2.setGeometry(0,0,1,1)

		self.web = QtWebKit.QWebView(self)
		
		self.web.load(QtCore.QUrl.fromLocalFile(APP_DIRECTORY + 'loading.html'))
		self.web.setGeometry(5,2,600,175)

		self.web.show()

		self.connect(self.bttnMap, QtCore.SIGNAL('clicked()'),
			self.doMapButtonClicked)

		self.connect(self.bttnCheckIn, QtCore.SIGNAL('clicked()'),
			self.doCheckInButtonClicked)

		self.connect(self.bttnTips, QtCore.SIGNAL('clicked()'),
			self.doShowTips)

		self.bttnCheckinsList = QtGui.QPushButton('',self)
		self.bttnCheckinsList.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnCheckinsList.hide()

		self.connect(self.bttnCheckinsList, QtCore.SIGNAL('clicked()'),
			self.doShowRecentCheckins)

		# self.connect(self.bttnCancel, QtCore.SIGNAL('clicked()'), 
		#	self, QtCore.SLOT('close()'))

	def doShowTips(self):
		print 'doShowTips'
		self.tipsDlg = TipsDialog(self.venueID,self)
		self.tipsDlg.show()

	def doShowRecentCheckins(self):
		print 'doShowRecentCheckins'
		self.whosHereDlg = WhosHereDialog(self.venueID)
		self.whosHereDlg.show()

	def loadingFinished(self):
		print 'loadingFinished'
		self.lblName.setText(self.venueName)
		self.lblAddress.setText(self.addressString)
		self.lblCity.setText(self.cityString)
		self.lblPhone.setText(self.phoneString)
		self.setWindowTitle(self.venueName)
		self.web.load(QtCore.QUrl('http://maps.google.com/maps/api/staticmap?center=' + self.strLatLon + '&size=600x175&maptype=roadmap&markers=color:red|' + self.strLatLon + '&zoom=16&sensor=false&key=' + GOOGLE_MAPS_API_KEY))
		if self.hasSpecials:
			self.bttnSpecials = QtGui.QPushButton(self.specialsText,self)
			self.bttnSpecials.setGeometry(620,280,175,80)
			self.bttnSpecials.setStyleSheet(QPUSHBUTTON_DEFAULT)
			# connect the slot
			self.connect(self.bttnSpecials, QtCore.SIGNAL('clicked()'),
				self.doSpecialsButtonClicked)

		if self.venueCheckinCount > 0:
			self.bttnCheckinsList.setText('Who\'s Here')
			if self.hasSpecials:
				self.bttnCheckinsList.setGeometry(435,280,175,80)
			else:
				self.bttnCheckinsList.setGeometry(620,280,175,80)
			self.bttnCheckinsList.show()

		self.bttnTips.setText(self.tipsText)

		if self.mayorName != '':
			self.lblDisplay2.setGeometry(85, 290, 300, 30)
			self.lblDisplay2.setText(self.mayorName)

		if self.mayorPhotoFile != '':
			self.lblDisplay1.setGeometry(5, 290, 75, 75)
			userPhotoPixmap = QtGui.QPixmap(self.mayorPhotoFile)
			if userPhotoPixmap != None:
				self.lblDisplay1.setPixmap(userPhotoPixmap)
			else:
				print 'userPhotoPixmap is None'

	def doSpecialsButtonClicked(self):
		print 'doSpecialsClicked'

	def doMapButtonClicked(self):
		url = VENUE_URL + self.venueID
		print 'Opening URL: ' + url
		webbrowser.open_new(url)
	
	def doCheckInButtonClicked(self):
		self.checkInDlg = CheckInDialog(self.venueID,self.venueName)
		self.checkInDlg.show()

class HistoryWorkerThread(QtCore.QThread):
	def __init__(self, parent = None):
    		QtCore.QThread.__init__(self, parent)
		self.exiting = False

	def run(self):
		client3 = oauthclient.SimpleOAuthClient('api.foursquare.com', 80, API_PREFIX_URL+'history', ACCESS_TOKEN_URL, AUTHORIZATION_URL)
		consumer = oauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
		signature_method_plaintext = oauth.OAuthSignatureMethod_PLAINTEXT()
		signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
	
		nearbyParams = {
			'l':	20,
			'oauth_token':	fsKey,
			'oauth_token_secret':	fsSecret
		}
		oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, callback=CALLBACK_URL, http_url=API_PREFIX_URL+'history', parameters=nearbyParams)
		oauth_request.sign_request(signature_method_plaintext, consumer, fsRequestToken)
		# print oauth_request.to_postdata()
		historyResultXml = client3.access_resource(oauth_request, http_url=API_PREFIX_URL+'history', requestType='GET')
		# print historyResultXml		
		# save venue data to cache file
		# catch invalid xml
		historyCacheFile = open(userPreferencesDir + 'historyCache.xml','w')
		historyCacheFile.write(historyResultXml)
		historyCacheFile.close()	
		# emit to main thread
		self.emit(QtCore.SIGNAL('reloadMainWindowWithResultsOfHistory()'))

	def __del__(self):
		self.exiting = True
		self.wait()


class SearchWorkerThread(QtCore.QThread):
	def __init__(self, parent = None):
    		QtCore.QThread.__init__(self, parent)
		self.exiting = False

	def run(self):
		client3 = oauthclient.SimpleOAuthClient('api.foursquare.com', 80, API_PREFIX_URL+'venues', ACCESS_TOKEN_URL, AUTHORIZATION_URL)
		consumer = oauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
		signature_method_plaintext = oauth.OAuthSignatureMethod_PLAINTEXT()
		signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
	
		global searchKeywords
		global currentLatitude
		global currentLongitude

		nearbyParams = {
			'geolat':	currentLatitude,
			'geolong':	currentLongitude,
			'q':	searchKeywords
		}
		oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, callback=CALLBACK_URL, http_url=API_PREFIX_URL+'venues', parameters=nearbyParams)
		oauth_request.sign_request(signature_method_plaintext, consumer, fsRequestToken)
		print oauth_request.to_postdata()
		searchResultXml = client3.access_resource(oauth_request, http_url=API_PREFIX_URL+'venues', requestType='GET')
		print searchResultXml		
		# save venue data to cache file
		searchCacheFile = open(userPreferencesDir + 'searchResultsCache.xml','w')
		searchCacheFile.write(searchResultXml)
		searchCacheFile.close()	
		# emit to main thread
		self.emit(QtCore.SIGNAL('reloadMainWindowWithResultsOfSearch()'))

	def __del__(self):
		self.exiting = True
		self.wait()

class SearchDialog(QtGui.QDialog):
	def __init__(self, parent=None):
		QtGui.QDialog.__init__(self, parent)

		self.setModal(1)
		self.setWindowTitle('Search for Venue')

		self.resize(800,200)

		# lbl for email
		lblSearch = QtGui.QLabel('Keywords:', self)
		lblSearch.setGeometry(10, 15, 150, 75)
		lblSearch.setFont(QtGui.QFont('Helvetica', 25))

		# txt field for email
		self.txtKeywords = QtGui.QLineEdit(self)
		# non-hildon: txtEmail.setGeometry(190, 10, 220, 50)
		self.txtKeywords.setGeometry(170, 20, 460, 60)
		self.txtKeywords.setFont(QtGui.QFont('Helvetica', 27))

		self.bttnDoSearch = QtGui.QPushButton('Search', self)
		self.bttnDoSearch.setGeometry(640, 10, 150, 80)
		self.bttnDoSearch.setStyleSheet(QPUSHBUTTON_DEFAULT)

		# bttnCancel = QtGui.QPushButton('Cancel', self)
		# bttnCancel.setGeometry(400, 150, 150, 80)

		self.connect(self.bttnDoSearch, QtCore.SIGNAL('clicked()'),
			self.doSearchButtonClicked)
		self.searchWorker = SearchWorkerThread()
		self.connect(self.searchWorker, QtCore.SIGNAL('finished()'),
			self.searchFinished)
		self.connect(self.searchWorker, QtCore.SIGNAL('reloadMainWindowWithResultsOfSearch()'), self.reloadMainWindowWithSearchResults)

	def doSearchButtonClicked(self):
		print 'doSearchButtonClicked'
		global qb
		keywords = '' + str(self.txtKeywords.text()).strip()
		print 'Keywords: ' + keywords
		global searchKeywords
		searchKeywords = keywords
		self.bttnDoSearch.setText('Searching...')
		self.searchWorker.start()

	def reloadMainWindowWithSearchResults(self):
		global qb
		qb.loadSearchResults()

	def searchFinished(self):
		print 'searchFinished'
		self.close()

class ConfirmDialog(QtGui.QDialog):
	def __init__(self, titleString, confirmString, parent=None):
		QtGui.QDialog.__init__(self, parent)

class AboutDialog(QtGui.QDialog):
	def __init__(self, parent=None):
		QtGui.QDialog.__init__(self, parent)
		self.setWindowTitle('About barrioSquare')
		self.resize(800,480)

class SignInWorkerThread(QtCore.QThread):
	def __init__(self, parent = None):
    		QtCore.QThread.__init__(self, parent)
		self.exiting = False

	def setup(self,email,password):
		self.email = email
		self.password = password

	def run(self):
		print 'SignInWorkerThread.run() Executing thread logic'
		global qb
		global infoNoticeString
		print 'emailOrPhone: 	' + self.email
		print 'password:	' + self.password

		print '** OAuth **'
		client = oauthclient.SimpleOAuthClient(SERVER, PORT, REQUEST_TOKEN_URL, ACCESS_TOKEN_URL, AUTHORIZATION_URL)
		client2 = oauthclient.SimpleOAuthClient('api.foursquare.com', 80, AUTHORIZATION_EXCHANGE_URL, ACCESS_TOKEN_URL, AUTHORIZATION_URL)
		consumer = oauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
		signature_method_plaintext = oauth.OAuthSignatureMethod_PLAINTEXT()
		signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
	
		fourSquareCredentials = {
			'fs_username':	self.email,
			'fs_password':	self.password
		}	

		print '* Do Authentication Exchange *'
		oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, callback=CALLBACK_URL, http_url=AUTHORIZATION_EXCHANGE_URL, parameters=fourSquareCredentials)
		oauth_request.sign_request(signature_method_plaintext, consumer, None)
		authResult = None
		clientConnectErrorString = ''
		clientConnectResult = 0
		try:
			authResult = client2.fetch_request_token(oauth_request)
			clientConnectResult = 0
		except socket.error, e:
			print 'socket error connecting to api endpoint'
			print e
			clientConnectResult = e[0]
			clientConnectErrorString = e[1]

		if clientConnectResult > 0:
			infoNoticeString = 'Error: ' + clientConnectErrorString
			self.emit(QtCore.SIGNAL('displayInfoNotice()'))	

		elif authResult != None:
			print authResult
			global fsRequestToken
			fsRequestToken = authResult
			# save token to file
			global hasToken
			hasToken = 1
			tokenFile = open(userPreferencesDir + 'tokenFile','w')
			tokenFile.write(fsRequestToken.to_string())		
			tokenFile.close()
			global fsRequestTokenString
			fsRequestTokenString = fsRequestToken.to_string()
			print fsRequestTokenString
			params = cgi.parse_qs(fsRequestTokenString, keep_blank_values=False)
			key = params['oauth_token'][0]
			global fsKey
			fsKey = key
			secret = params['oauth_token_secret'][0]
			global fsSecret
			fsSecret = secret
	
			fsRequestToken = oauth.OAuthToken(key, secret)
			print fsRequestToken
			print fsKey
			print fsSecret

			time.sleep(1)
			# authorize the token
			oauth_request = oauth.OAuthRequest.from_token_and_callback(token=fsRequestToken, http_url=client.authorization_url)
			response = client.authorize_token(oauth_request)
			print response
			self.emit(QtCore.SIGNAL('setSignInSuccess'),True)	
		else:
			# login incorrect, display error
			# self.lblError.setText('Username or password incorrect')
			# use OSSO
			infoNoticeString = 'Username or password incorrect'
			self.emit(QtCore.SIGNAL('displayInfoNotice()'))	

		time.sleep(1)

	def __del__(self):
		self.exiting = True
		self.wait()


class SignInDialog(QtGui.QDialog):
	def __init__(self, parent=None):
		QtGui.QDialog.__init__(self, parent)
		self.SigningIn = False
		self.SignInSuccess = False

		p = self.palette()
		p.setColor(QtGui.QPalette.Window, QtGui.QColor(0, 0, 0))
		self.setPalette(p)

		self.setModal(1)
		self.setWindowTitle('Sign In')

		# lbl for email
		lblEmail = QtGui.QLabel('Phone Number / E-mail:', self)
		lblEmail.setGeometry(20, 30, 250, 20)

		# txt field for email
		self.txtEmail = QtGui.QLineEdit(self)
		# non-hildon: txtEmail.setGeometry(190, 10, 220, 50)
		self.txtEmail.setGeometry(270, 10, 220, 50)

		# lbl for password
		lblPasswd = QtGui.QLabel('Password:', self)
		lblPasswd.setGeometry(160, 80, 200, 20)

		self.lblError = QtGui.QLabel('',self)
		self.lblError.setGeometry(10,100,600,50)

		# txt field for email
		self.txtPasswd = QtGui.QLineEdit(self)
		# non-hildon: txtPasswd.setGeometry(190, 65, 220, 50)
		self.txtPasswd.setGeometry(270, 65, 220, 50)
		self.txtPasswd.setEchoMode(QtGui.QLineEdit.Password)

		self.lblLoadingIcon = QtGui.QLabel('',self)
		self.loadingGif = QtGui.QMovie(APP_DIRECTORY + 'loading2.gif', QtCore.QByteArray(), self)
		self.loadingGif.setCacheMode(QtGui.QMovie.CacheAll)
		self.loadingGif.setSpeed(100)
		self.loadingGif.setBackgroundColor(QtGui.QColor(0, 0, 0))
		self.lblLoadingIcon.setGeometry(525,130,50,50)
		self.lblLoadingIcon.setMovie(self.loadingGif)
		self.lblLoadingIcon.hide()

		self.bttnSignIn2 = QtGui.QPushButton('', self)
		self.bttnSignIn2.setGeometry(180, 135, 300, 40)

		signInPixmap = QtGui.QPixmap(APP_DIRECTORY + 'SignInFourSquare.png')
		signInPixmap2 = signInPixmap.scaled(QtCore.QSize(300,40), QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)		
	
		self.bttnSignIn2.setIcon(QtGui.QIcon(signInPixmap2))
		self.bttnSignIn2.setIconSize(QtCore.QSize(300,40))

		self.bttnSignIn2.setStyleSheet(QPUSHBUTTON_DEFAULT)

		lblInfo = QtGui.QLabel('Login will be via foursquare.com\'s OAuth mechanism to obtain a token. User credentials are not stored. When you sign out of the app, the token is destroyed. You can also remove app access to your account at anytime by visiting foursquare.com and clicking settings.',self)
		lblInfo.setGeometry(5,150,790,300)
		lblInfo.setWordWrap(True)
		# bttnCancel = QtGui.QPushButton('Cancel', self)
		# bttnCancel.setGeometry(400, 150, 150, 80)

		self.resize(800,480)

		self.signInWorker = SignInWorkerThread()
		self.connect(self.signInWorker, QtCore.SIGNAL('finished()'), self.signInCompleted)
		self.connect(self.signInWorker, QtCore.SIGNAL('setSignInSuccess'), self.setSignInSuccess)
		self.connect(self.signInWorker, QtCore.SIGNAL('displayInfoNotice()'), self.displayInfoNoticeGlobal)

		# self.connect(bttnCancel, QtCore.SIGNAL('clicked()'), 
		#	self, QtCore.SLOT('close()'))
		self.connect(self.bttnSignIn2, QtCore.SIGNAL('clicked()'),
			self.doSignInClicked)

	def displayInfoNoticeGlobal(self):
		global infoNoticeString
		global qb
		qb.displayInfoNotice(infoNoticeString)

	def setSignInSuccess(self,completed):
		self.SignInSuccess = completed

	def closeEvent(self, event):
		if self.SigningIn:
			reply = QtGui.QMessageBox.question(self, 'Cancel?',"Are you sure you want to cancel sign in?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
			if reply == QtGui.QMessageBox.Yes:
				self.SigningIn = False
				event.accept()
			else:
				event.ignore()
		else:
			event.accept()

	def signInCompleted(self):
		self.bttnSignIn2.setEnabled(True)
		self.lblLoadingIcon.hide()
		self.loadingGif.stop()
		self.SigningIn = False
		if self.SignInSuccess:
			# emit signOutFinished
			self.emit(QtCore.SIGNAL('signOutFinished()'))	
			self.close()
	
	def pause(self):
		print ''
		time.sleep(1)

	# @QtCore.pyqtSlot()
	def doSignInClicked(self):
		self.bttnSignIn2.setEnabled(False)
		self.lblLoadingIcon.show()
		self.loadingGif.start()
		self.SigningIn = True		
		self.signInWorker.setup(str(self.txtEmail.text()),str(self.txtPasswd.text()))
		self.signInWorker.start()
		




class ConfirmSignOutDialog(QtGui.QDialog):
	def __init__(self, parent=None):
		QtGui.QDialog.__init__(self, parent)
		self.setWindowTitle('Sign out?')
		self.resize(800,200)
		self.lblSignout = QtGui.QLabel('Are you sure you want to sign out of foursquare.com? Your OAuth token will be destroyed. You should also remove BarrioSquare from your account by visiting http://foursquare.com/settings',self)
		self.lblSignout.setGeometry(5,5,600,190)
		self.lblSignout.setWordWrap(True)
		self.lblSignout.setAlignment(QtCore.Qt.AlignTop)

		self.bttnOk = QtGui.QPushButton('OK',self)
		self.bttnOk.setGeometry(620,5,175,80)
		self.bttnOk.setStyleSheet(QPUSHBUTTON_DEFAULT)

		self.bttnCancel = QtGui.QPushButton('Cancel',self)
		self.bttnCancel.setGeometry(620,95,175,80)
		self.bttnCancel.setStyleSheet(QPUSHBUTTON_DEFAULT)

		self.connect(self.bttnOk, QtCore.SIGNAL('clicked()'),
			self.buttonOkClicked)	

		self.connect(self.bttnCancel, QtCore.SIGNAL('clicked()'),
			self.buttonCancelClicked)

	def buttonOkClicked(self):
		print 'buttonOkClicked'
		global doingSignout
		doingSignout = True
		self.close()

	def buttonCancelClicked(self):
		print 'buttonCancelClicked'
		global doingSignout
		doingSignout = False
		self.close()

class FriendCheckinDetailDialog(QtGui.QMainWindow):
	def __init__(self, id, parent=None):
		QtGui.QMainWindow.__init__(self, parent)	

		self.resize(800,480)

		self.lblName = QtGui.QLabel('',self)
		self.lblName.setFont(QtGui.QFont('Helvetica', 20))
		self.lblName.setGeometry(5,255,800,50)

		self.lblName2 = QtGui.QLabel('',self)
		self.lblName2.setFont(QtGui.QFont('Helvetica', 20))
		self.lblName2.setGeometry(5,305,800,50)


		self.web = QtWebKit.QWebView(self)
		
		self.web.load(QtCore.QUrl.fromLocalFile(APP_DIRECTORY + 'loading.html'))
		self.web.setGeometry(5,2,600,250)

		self.web.show()

		checkinsXmlFile = open(userPreferencesDir + 'checkinsResultsCache.xml','r')
		checkinXmlString = ''
		for line in checkinsXmlFile:
			checkinXmlString += line
		checkinsXmlFile.close()
		print checkinXmlString
		parseSuccess = False
		try:
			checkinsXml = parseString(checkinXmlString)
			parseSuccess = True
		except xml.parsers.expat.ExpatError:
			parseSuccess = False

		if parseSuccess == True:
			checkinNodes = checkinsXml.getElementsByTagName('checkin')
			for node in checkinNodes:
				vid = node.getElementsByTagName('id')[0].firstChild.data
				if vid == id:
					geolatNodes = node.getElementsByTagName('geolat')
					geolongNodes = node.getElementsByTagName('geolong')
					if geolatNodes.length > 0 and geolongNodes.length > 0:
						self.strLatLon = geolatNodes[0].firstChild.data + ',' + geolongNodes[0].firstChild.data
						self.web.load(QtCore.QUrl('http://maps.google.com/maps/api/staticmap?center=' + self.strLatLon + '&size=600x250&maptype=roadmap&markers=color:red|' + self.strLatLon + '&zoom=14&sensor=false&key=' + GOOGLE_MAPS_API_KEY))
					else:
						self.web.hide()
					self.setWindowTitle(node.getElementsByTagName('display')[0].firstChild.data)
					self.lblName.setText(node.getElementsByTagName('display')[0].firstChild.data)

class SettingsDialog(QtGui.QDialog):
	def __init__(self, parent=None):
		QtGui.QDialog.__init__(self, parent)	
		self.setWindowTitle('Settings')
		self.resize(800,480)
		self.scrollableArea = QtGui.QScrollArea(self)
	
		# add the child widget to the scroll area
		self.childWidget = QWidget()
		self.scrollableArea.setWidget(self.childWidget)
		
		# use box layout - add scrollable area for settings
		
		# 
		self.chkEnableAutoFriendsRefresh = QtGui.QCheckBox('Enable auto refresh of friends list',self)
		
		

class LocationSettingsDialog(QtGui.QDialog):
	def __init__(self, parent=None):
		QtGui.QDialog.__init__(self, parent)	
		self.setWindowTitle('Location Settings')
		self.resize(800,480)

		global locationMethodType
		
		self.radioLocationUSER = QtGui.QRadioButton('Use System Default',self)
		self.radioLocationUSER.setGeometry(5,5,700,27)
		if locationMethodType == 0:
			self.radioLocationUSER.setChecked(True)

		self.radioLocationCWP = QtGui.QRadioButton('Use Complementary Wireless Positioning',self)
		self.radioLocationCWP.setGeometry(5,70,700,27)
		if locationMethodType == 1:
			self.radioLocationCWP.setChecked(True)

		self.radioLocationACWP = QtGui.QRadioButton('Use Assisted Complementary Wireless Positioning',self)
		self.radioLocationACWP.setGeometry(5,135,700,27)
		if locationMethodType == 2:
			self.radioLocationACWP.setChecked(True)

		self.radioLocationGNSS = QtGui.QRadioButton('Use Global Navigation Satellite System',self)
		self.radioLocationGNSS.setGeometry(5,200,700,27)
		if locationMethodType == 3:
			self.radioLocationGNSS.setChecked(True)

		self.radioLocationAGNSS = QtGui.QRadioButton('Use Assisted Global Navigation Satellite System',self)
		self.radioLocationAGNSS.setGeometry(5,265,700,27)
		if locationMethodType == 4:
			self.radioLocationAGNSS.setChecked(True)	

		self.bttnOk = QtGui.QPushButton('OK',self)
		self.bttnOk.setGeometry(620,295,175,80)
		self.bttnOk.setStyleSheet(QPUSHBUTTON_DEFAULT)

		self.connect(self.bttnOk, QtCore.SIGNAL('clicked()'),
			self.doBttnOkClicked)	

	def doBttnOkClicked(self):
		global locationMethodType
		currentType = locationMethodType
		if self.radioLocationUSER.isChecked():
			locationMethodType = 0
		elif self.radioLocationCWP.isChecked():
			locationMethodType = 1
		elif self.radioLocationACWP.isChecked():
			locationMethodType = 2
		elif self.radioLocationGNSS.isChecked():
			locationMethodType = 3
		elif self.radioLocationAGNSS.isChecked():
			locationMethodType = 4 
		locationMethodFile = open(userPreferencesDir + 'locationMethodType.txt','w')
		print 'locationMethodType: %d' % locationMethodType
		locationMethodFile.write(str(locationMethodType) + '\n')
		locationMethodFile.close()
		if currentType != locationMethodType:
			reply = QtGui.QMessageBox.question(self, 'Location Method Changed',"Attempt to acquire your location based on your new settings?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
			if reply == QtGui.QMessageBox.Yes:
				print 'reinit location process'
				# reinit the location settings	
				global locationManagerObj
				locationManagerObj.restartSubprocess()	
		self.close()


class LoadNearbyVenuesFromFile(QtCore.QThread):
	def __init__(self, parent = None):
    		QtCore.QThread.__init__(self, parent)
		self.exiting = False

	def run(self):
		global qb
		nearbyXmlFile = open(userPreferencesDir + 'nearbyCache.xml','r')
		nearbyXmlString = ''
		for line in nearbyXmlFile:
			nearbyXmlString += line
		nearbyXmlFile.close()
		parseSuccess = False
		# print nearbyXmlString
		try:
			nearbyXml = parseString(nearbyXmlString)
			parseSuccess = True
		except xml.parsers.expat.ExpatError:
			parseSuccess = False

		if parseSuccess:
			# remove items from list
			self.emit(QtCore.SIGNAL('clearPlacesListWidget()'))

			# loop over xml venues and add to list widget
			nearbyNodes = nearbyXml.getElementsByTagName('venue')
			for node in nearbyNodes:
				# print node.getElementsByTagName('id')[0].firstChild.data
				addressString = ''
				addressNode = node.getElementsByTagName('address')
				if addressNode.length > 0:
					if addressNode[0].firstChild != None:
						addressString = addressNode[0].firstChild.data
				if node.getElementsByTagName('crossstreet').length > 0:
					addressString += ' (' + node.getElementsByTagName('crossstreet')[0].firstChild.data + ')'
				addressString += ' ~' + qb.calcMetersAsString(node.getElementsByTagName('distance')[0].firstChild.data)
				venueName = node.getElementsByTagName('name')[0].firstChild.data
				self.emit(QtCore.SIGNAL('addItemToPlacesListWidget'),venueName,addressString,node.getElementsByTagName('id')[0].firstChild.data)

				# nearbyPlaceString = node.getElementsByTagName('name')[0].firstChild.data
				# nearbyPlaceString += ' (' + self.calcMetersAsString(node.getElementsByTagName('distance')[0].firstChild.data) + ')'
				# nearbyItem = QtGui.QListWidgetItem(nearbyPlaceString,self.placesListWidget)
				# nearbyItem.setFont(QtGui.QFont('Helvetica', 30))
				# nearbyItem.setStatusTip(node.getElementsByTagName('id')[0].firstChild.data)
		else:
			print 'parseSuccess is False'		
		self.emit(QtCore.SIGNAL('dismissProcessingDialog()'))

	def __del__(self):
		self.exiting = True
		self.wait()


class LoadFriendsCheckinsFromFile(QtCore.QThread):
	def __init__(self, parent = None):
    		QtCore.QThread.__init__(self, parent)
		self.exiting = False

	def run(self):
		global qb
		global infoNoticeString
		checkinsXmlFile = open(userPreferencesDir + 'checkinsResultsCache.xml','r')
		checkinXmlString = ''
		for line in checkinsXmlFile:
			checkinXmlString += line
		checkinsXmlFile.close()
		parseSuccess = False
		try:
			checkinsXml = parseString(checkinXmlString)
			parseSuccess = True
		except xml.parsers.expat.ExpatError:
			parseSuccess = False
			print checkinXmlString
		if parseSuccess == True:

			# remove items from list
			self.emit(QtCore.SIGNAL('clearFriendsListWidget()'))

			unauthorized = 0
			# check unauthorized
			try:
				unauthorized = qb.checkUnauthorized(checkinsXml)
			except AttributeError:
				unauthorized = 0

			if unauthorized > 0:
				global doingSignout
				doingSignout = True
				self.emit(QtCore.SIGNAL('signOut()'))	
				self.emit(QtCore.SIGNAL('dismissProcessingDialog()'))
				if unauthorized == 1:
					infoNoticeString = 'Error: Your foursquare.com token has expired'
					self.emit(QtCore.SIGNAL('displayInfoNotice()'))		
			else:
				# switch the current tab to search tab
				# self.tabWidget.setCurrentWidget(self.searchResultsTab)

				# loop over xml venues and add to list widget
				checkinNodes = checkinsXml.getElementsByTagName('checkin')
				for node in checkinNodes:
					# get photo
					photoURL = node.getElementsByTagName('photo')[0].firstChild.data

					venueNode = node.getElementsByTagName('venue')
					OffGrid = False
					if venueNode.length == 0:
						print 'no venue info - off the grid'
						OffGrid = True
					photoURLchunks = photoURL.split('/')
					photoFile = userPreferencesDir + 'imageCache' + os.sep + 'users' + os.sep + photoURLchunks[3] + '_' + photoURLchunks[4]
					# print 'photoFile: ' + photoFile			
					# if cached file doesn't exist for user, download it now
					if not os.path.exists(photoFile):
						self.getUserPhoto(photoURL)

					# print node.getElementsByTagName('id')[0].firstChild.data
					checkinString = node.getElementsByTagName('display')[0].firstChild.data + '\n'
					if (node.getElementsByTagName('shout').length > 0):
						checkinString += node.getElementsByTagName('shout')[0].firstChild.data
					checkinString += node.getElementsByTagName('created')[0].firstChild.data

					addressString = ''
					addressNode = node.getElementsByTagName('address')
					if addressNode.length > 0:
						if addressNode[0].firstChild != None:
							addressString += addressNode[0].firstChild.data
					crosssStreetNode = node.getElementsByTagName('crossstreet')
					if crosssStreetNode.length > 0:
						if crosssStreetNode[0].firstChild != None:
							addressString += ' (' + crosssStreetNode[0].firstChild.data + ')'
					dateStr = qb.calcDateString(node.getElementsByTagName('created')[0].firstChild.data)
					addressString += ' ~' + dateStr
					displayStr = node.getElementsByTagName('display')[0].firstChild.data
					shoutNodes = node.getElementsByTagName('shout')
					# print 'shouts: %d' % shoutNodes.length
					if shoutNodes.length > 0:
						displayStr += ' ("' + shoutNodes[0].firstChild.data + '")'

					if OffGrid:
						self.emit(QtCore.SIGNAL('addItemToFriendsListWidget'),displayStr,addressString,photoFile,OffGrid,'-1')
					else:
						self.emit(QtCore.SIGNAL('addItemToFriendsListWidget'),displayStr,addressString,photoFile,OffGrid,node.getElementsByTagName('id')[0].firstChild.data)


					# checkinItem = QtGui.QListWidgetItem('',self.friendsListWidget)
					# checkinItem.setSizeHint(QtCore.QSize(770, 75))
					# wItem = FriendListItem()


					# wItem.setText(displayStr,addressString,'dateStr',photoFile)
					# self.friendsListWidget.setItemWidget(checkinItem,wItem)
					# if OffGrid:
					# 	checkinItem.setStatusTip('-1')
					# else:
					#	checkinItem.setStatusTip(node.getElementsByTagName('id')[0].firstChild.data)
			
				# checkinItem = QtGui.QListWidgetItem('',self.friendsListWidget)
				# checkinItem.setSizeHint(QtCore.QSize(770, 75))
				# wItem = FriendListItem()
				# wItem.setText('','','',None)
				# self.friendsListWidget.setItemWidget(checkinItem,wItem)
				# checkinItem.setStatusTip('0')

				self.emit(QtCore.SIGNAL('addItemToFriendsListWidget'),'','','',False,'0')
				self.emit(QtCore.SIGNAL('dismissProcessingDialog()'))

				if checkinNodes.length > 0:
					infoNoticeString = 'Loaded %d recent friend checkins' % checkinNodes.length
					self.emit(QtCore.SIGNAL('displayInfoNotice()'))				

		else:
			# parse error show error window
			print 'parseSuccess is false'
			self.emit(QtCore.SIGNAL('dismissProcessingDialog()'))

		# if self.processDlg != None:
		#	self.processDlg.close()

	def __del__(self):
		self.exiting = True
		self.wait()

class LoadUserInfoFromServerThread(QtCore.QThread):
	def __init__(self, parent = None):
    		QtCore.QThread.__init__(self, parent)
		self.exiting = False

	def setup(self,userid):
		self.userid = userid

	def run(self):
		# print 'doGetUserDetailInBackgroundThread'
		client3 = oauthclient.SimpleOAuthClient('api.foursquare.com', 80, API_PREFIX_URL+'user', ACCESS_TOKEN_URL, AUTHORIZATION_URL)
		consumer = oauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
		signature_method_plaintext = oauth.OAuthSignatureMethod_PLAINTEXT()
		signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
		print self.userid
		if self.userid > 0:
			cacheFileName = 'userDetailCache_' + str(uid) + '.xml'
			wsParams = {
				'uid':	uid,
				'oauth_token':	fsKey,
				'oauth_token_secret':	fsSecret
			}
		else:
			cacheFileName = 'userDetailCache.xml'
			wsParams = {
				'badges':	1,
				'oauth_token':	fsKey,
				'oauth_token_secret':	fsSecret
			}
		oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, callback=CALLBACK_URL, http_url=API_PREFIX_URL+'user', parameters=wsParams)
		oauth_request.sign_request(signature_method_plaintext, consumer, fsRequestToken)
		# print oauth_request.to_postdata()
		userResultXml = client3.access_resource(oauth_request, http_url=API_PREFIX_URL+'user', requestType='GET')
		# print userResultXml		
		# save user data to cache file
		parseSuccess = False
		# process result
		try:
			userXml = parseString(userResultXml)
			parseSuccess = True
			userDetailCacheFile = open(userPreferencesDir + cacheFileName,'w')
			userDetailCacheFile.write(userResultXml)
			userDetailCacheFile.close()
		except xml.parsers.expat.ExpatError:
			print 'error parsing userResultXml!'
			parseSuccess = False
			print userResultXml

		if parseSuccess == True:			
			if self.userid == 0:
				global loggedInUserID
				userNode = userXml.getElementsByTagName('user')
				loggedInUserID = int(userNode[0].getElementsByTagName('id')[0].firstChild.data)
				print 'logged in user: %d' % loggedInUserID

			settingsNode = userXml.getElementsByTagName('settings')
			if settingsNode.length > 0:
				twitterNode = settingsNode[0].getElementsByTagName('sendtotwitter')
				if twitterNode.length > 0:
					if twitterNode[0].firstChild.data == 'true':
						global pingTwitter
						pingTwitter = True

				facebookNode = settingsNode[0].getElementsByTagName('sendtofacebook')
				if facebookNode.length > 0:
					if facebookNode[0].firstChild.data == 'true':
						global pingFacebook
						pingFacebook = True

			badgesNodes = userXml.getElementsByTagName('badge')
			global badgeCount
			badgeCount = badgesNodes.length
			if badgesNodes.length > 0:
				for node in badgesNodes:
					badgeIconURL = node.getElementsByTagName('icon')[0].firstChild.data
					badgeURLchunks = badgeIconURL.split('/')
					badgeFile = userPreferencesDir + 'imageCache' + os.sep + 'badges' + os.sep + badgeURLchunks[4] + '_' + badgeURLchunks[5]
					print 'badgeFile: ' + badgeFile			
					# if cached file doesn't exist for user, download it now
					if not os.path.exists(badgeFile):
						photoResponse = urllib2.urlopen(badgeIconURL)
						photoData = photoResponse.read()

						badgeFile = open(badgeFile,'w')
						badgeFile.write(photoData)
						badgeFile.close()


	def __del__(self):
		self.exiting = True
		self.wait()

class UserHistoryLoaderThread(QtCore.QThread):
	def __init__(self, parent = None):
    		QtCore.QThread.__init__(self, parent)
		self.exiting = False

	def run(self):
		global qb
		historyXmlFile = open(userPreferencesDir + 'historyCache.xml','r')
		historyXmlString = ''
		for line in historyXmlFile:
			historyXmlString += line
		historyXmlFile.close()
		# print nearbyXmlString
		parseSuccess = False
		try:
			historyXml = parseString(historyXmlString)
			parseSuccess = True
		except xml.parsers.expat.ExpatError:
			parseSuccess = False

		if parseSuccess:
			# remove items from list
			self.emit(QtCore.SIGNAL('clearHistoryListWidget()'))

			# loop over xml venues and add to list widget
			historyNodes = historyXml.getElementsByTagName('checkin')
			for node in historyNodes:
				addressString = ''
				addressNode = node.getElementsByTagName('address')
				if addressNode.length > 0:
					if addressNode[0].firstChild != None:
						addressString = addressNode[0].firstChild.data

				crossstreetNode = node.getElementsByTagName('crossstreet')
				if crossstreetNode.length > 0:
					if crossstreetNode[0].firstChild != None:
						addressString += ' (' + crossstreetNode[0].firstChild.data + ')'

				dateStr = qb.calcDateString(node.getElementsByTagName('created')[0].firstChild.data)
				addressString += ' ~' + dateStr
				venueNodes = node.getElementsByTagName('venue')
				venueName = ''
				venueID = ''
				OffGrid = True
				shout = ''
				if venueNodes.length > 0:
					OffGrid = False
					venueID = venueNodes[0].getElementsByTagName('id')[0].firstChild.data
					venueName = venueNodes[0].getElementsByTagName('name')[0].firstChild.data
				shoutNodes = node.getElementsByTagName('shout')
				if shoutNodes.length > 0:
					shout = shoutNodes[0].firstChild.data
				if OffGrid:
					self.emit(QtCore.SIGNAL('addItemToHistoryListWidget'),venueName,shout,addressString,OffGrid,'-1')
				else:
					self.emit(QtCore.SIGNAL('addItemToHistoryListWidget'),venueName,shout,addressString,OffGrid,venueID)

	def __del__(self):
		self.exiting = True
		self.wait()
	
class MainWindow(QtGui.QMainWindow):
	def __init__(self, parent=None):
		QtGui.QMainWindow.__init__(self, parent)

		self.setWindowIcon(QtGui.QIcon(QtGui.QPixmap(APP_DIRECTORY + 'barrioSquare.png')))

		self.osso_c = osso.Context("barrioSquare", SHORT_VERSION_STRING, False)
		self.osso_rpc = osso.Rpc(self.osso_c)

		self.locationDialog = None
		self.setWindowTitle('BarrioSquare')
		self.processDlg = None
		# set menu
		# self.menubar = self.menuBar()
		# entry = self.menubar.addAction('&About')
		# entry = self.menubar.addAction('&Sign Out')


		#label = QtGui.QLabel('testing', self)
		#label.setGeometry(10, 60, 50, 20)

		self.resize(800,480)

		# add menu
		#
		# self.menuBar = QtGui.QMenuBar(self)
		# self.menuBarMainMenu = self.menuBar.addMenu('BQ')
		# if (fsRequestToken == None):
		#	self.menuBarMainMenuSignInOut = self.menuBarMainMenu.addAction('Sign In')
		# else:
		#	self.menuBarMainMenuSignInOut = self.menuBarMainMenu.addAction('Sign Out')

		if (fsRequestToken == None):
			self.bttnSignIn = QtGui.QPushButton('', self)
		else:
			self.bttnSignIn = QtGui.QPushButton('', self)			
		self.bttnSignIn.setGeometry(5, 338, 80, 80)
		self.bttnSignIn.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnSignIn.setIcon(QtGui.QIcon(QtGui.QPixmap(APP_DIRECTORY + 'signOutIcon.png')))
		self.bttnSignIn.setIconSize(QtCore.QSize(70,70))

		# button for search
		self.bttnSearch = QtGui.QPushButton('', self)			
		self.bttnSearch.setGeometry(620, 338, 80, 80)
		self.bttnSearch.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnSearch.setIcon(QtGui.QIcon(QtGui.QPixmap(APP_DIRECTORY + 'searchIcon.png')))
		self.bttnSearch.setIconSize(QtCore.QSize(70,70))

		# button for location
		self.bttnLocation = QtGui.QPushButton('', self)			
		self.bttnLocation.setGeometry(185, 338, 80, 80)
		self.bttnLocation.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnLocation.setIcon(QtGui.QIcon(QtGui.QPixmap(APP_DIRECTORY + 'myInfoIcon.png')))
		self.bttnLocation.setIconSize(QtCore.QSize(70,70))

		# button for settings
		self.bttnSettings = QtGui.QPushButton('', self)			
		self.bttnSettings.setGeometry(95, 338, 80, 80)
		self.bttnSettings.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnSettings.setIcon(QtGui.QIcon(QtGui.QPixmap(APP_DIRECTORY + 'settingsIcon.png')))
		self.bttnSettings.setIconSize(QtCore.QSize(70,70))

		self.bttnHistory = QtGui.QPushButton('', self)			
		self.bttnHistory.setGeometry(345, 338, 80, 80)
		self.bttnHistory.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnHistory.setIcon(QtGui.QIcon(QtGui.QPixmap(APP_DIRECTORY + 'historyIcon.png')))
		self.bttnHistory.setIconSize(QtCore.QSize(70,70))

		self.connect(self.bttnHistory, QtCore.SIGNAL('clicked()'),
			self.doShowHistoryTab)

		self.bttnFriends = QtGui.QPushButton('', self)			
		self.bttnFriends.setGeometry(435, 338, 86, 80)
		self.bttnFriends.setStyleSheet(QPUSHBUTTON_HIGHLIGHT)
		self.bttnFriends.setIcon(QtGui.QIcon(QtGui.QPixmap(APP_DIRECTORY + 'friendsIcon.png')))
		self.bttnFriends.setIconSize(QtCore.QSize(70,70))

		self.connect(self.bttnFriends, QtCore.SIGNAL('clicked()'),
			self.doShowFriendsTab)

		self.bttnPlaces = QtGui.QPushButton('', self)			
		self.bttnPlaces.setGeometry(530, 338, 80, 80)
		self.bttnPlaces.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnPlaces.setIcon(QtGui.QIcon(QtGui.QPixmap(APP_DIRECTORY + 'placesIcon.png')))
		self.bttnPlaces.setIconSize(QtCore.QSize(70,70))

		self.connect(self.bttnPlaces, QtCore.SIGNAL('clicked()'),
			self.doShowPlacesTab)

		# push menu
		self.settingsMenu = QtGui.QMenu(self)

		self.settingsMenuAboutAction = self.settingsMenu.addAction('About')
		self.connect(self.settingsMenuAboutAction, QtCore.SIGNAL("triggered()"), self.doAboutActionTriggered)

		self.settingsMenuClearCacheAction = self.settingsMenu.addAction('Clear Cache')
		self.connect(self.settingsMenuClearCacheAction, QtCore.SIGNAL("triggered()"), self.doClearCacheActionTriggered)

		self.settingLocationMenuAction = self.settingsMenu.addAction('Location Settings')

		self.connect(self.settingLocationMenuAction, QtCore.SIGNAL("triggered()"), self.doShowLocationSettingsDialog)

		self.bttnSettings.setMenu(self.settingsMenu)

		self.connect(self.bttnLocation, QtCore.SIGNAL('clicked()'),
			self.doShowLocationDialog)

		if (fsRequestToken == None):
			self.bttnSearch.hide()
			self.bttnLocation.hide()
			self.bttnPlaces.hide()
			self.bttnFriends.hide()

		# button for refresh
		self.bttnRefresh = QtGui.QPushButton('', self)			
		self.bttnRefresh.setGeometry(710, 338, 80, 80)
		self.bttnRefresh.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnRefresh.setIcon(QtGui.QIcon(QtGui.QPixmap(APP_DIRECTORY + 'refreshIcon.png')))
		self.bttnRefresh.setIconSize(QtCore.QSize(70,70))

		if (fsRequestToken == None):
			self.bttnRefresh.hide()

		# dialog for sign in
		self.signInDlg = SignInDialog()

		# dialog for search
		self.searchDlg = SearchDialog()

		# add a tab widget
		self.tabWidget = QtGui.QTabWidget(self)
		self.tabWidget.setGeometry(0, 0, 800, 330)

		self.friendsTab = QtGui.QWidget()
		self.tabWidget.addTab(self.friendsTab, QtCore.QString())

		self.placesTab = QtGui.QWidget()
		self.tabWidget.addTab(self.placesTab, QtCore.QString())

		self.historyTab = QtGui.QWidget()
		self.tabWidget.addTab(self.historyTab, QtCore.QString())

		self.searchResultsTab = QtGui.QWidget()
		self.tabWidget.addTab(self.searchResultsTab, QtCore.QString())

		self.tabWidget.setTabText(self.tabWidget.indexOf(self.friendsTab),QtGui.QApplication.translate('MainWindow','Friends','Friends',QtGui.QApplication.UnicodeUTF8))
		self.tabWidget.setTabText(self.tabWidget.indexOf(self.placesTab),QtGui.QApplication.translate('MainWindow','Places','Places',QtGui.QApplication.UnicodeUTF8))
		self.tabWidget.setTabText(self.tabWidget.indexOf(self.historyTab),QtGui.QApplication.translate('MainWindow','History','History',QtGui.QApplication.UnicodeUTF8))
		self.tabWidget.setTabText(self.tabWidget.indexOf(self.searchResultsTab),QtGui.QApplication.translate('MainWindow','Search Results','Search Results',QtGui.QApplication.UnicodeUTF8))
		
		self.tabWidget.setStyleSheet("QTabBar::tab { height: 0px; width: 180px; }");

		# add list widget for friends
		self.friendsListWidget = QtGui.QListWidget(self.friendsTab)
		self.friendsListWidget.setGeometry(0, 0, 820, 330) #310
		self.friendsListWidget.setStyleSheet(QLISTWIDGET_DEFAULT)

		p = self.friendsListWidget.palette()
		p.setColor(QtGui.QPalette.Highlight, QtGui.QColor(255, 255, 184))
		p = self.friendsListWidget.setPalette(p)

		# add list widget for places
		self.placesListWidget = QtGui.QListWidget(self.placesTab)
		self.placesListWidget.setGeometry(0, 0, 820, 330) #310
		
		p = self.placesListWidget.palette()
		p.setColor(QtGui.QPalette.Highlight, QtGui.QColor(255, 255, 184))
		p = self.placesListWidget.setPalette(p)

		# add list widget for history
		self.historyListWidget = QtGui.QListWidget(self.historyTab)
		self.historyListWidget.setGeometry(0, 0, 820, 330) #310
		self.historyListWidget.setStyleSheet(QLISTWIDGET_DEFAULT)

		p = self.historyListWidget.palette()
		p.setColor(QtGui.QPalette.Highlight, QtGui.QColor(255, 255, 184))
		p = self.historyListWidget.setPalette(p)

		# add list widget for search
		self.searchListWidget = QtGui.QListWidget(self.searchResultsTab)
		self.searchListWidget.setGeometry(0, 0, 820, 330) #310
		self.searchListWidget.setStyleSheet(QLISTWIDGET_DEFAULT)

		p = self.searchListWidget.palette()
		p.setColor(QtGui.QPalette.Highlight, QtGui.QColor(255, 255, 184))
		p = self.searchListWidget.setPalette(p)

		
		# thread to load venues from file
		self.loadNearbyVenuesWorker = LoadNearbyVenuesFromFile()
		self.connect(self.loadNearbyVenuesWorker, QtCore.SIGNAL('clearPlacesListWidget()'), self.clearPlacesListWidget)
		self.connect(self.loadNearbyVenuesWorker, QtCore.SIGNAL('addItemToPlacesListWidget'), self.addItemToPlacesListWidget)
		self.connect(self.loadNearbyVenuesWorker, QtCore.SIGNAL('displayInfoNotice()'), self.displayInfoNoticeGlobal)
		self.connect(self.loadNearbyVenuesWorker, QtCore.SIGNAL('dismissProcessingDialog()'), self.dismissProcessingDialog)

		# thread to load checkins from file and update UI
		self.loadFriendsCheckinsWorker = LoadFriendsCheckinsFromFile()
		self.connect(self.loadFriendsCheckinsWorker, QtCore.SIGNAL('signOut()'),self.onSignOutDialogClosed)
		self.connect(self.loadFriendsCheckinsWorker, QtCore.SIGNAL('clearFriendsListWidget()'), self.clearFriendsListWidget)
		self.connect(self.loadFriendsCheckinsWorker, QtCore.SIGNAL('addItemToFriendsListWidget'), self.addItemToFriendsListWidget)
		self.connect(self.loadFriendsCheckinsWorker, QtCore.SIGNAL('displayInfoNotice()'), self.displayInfoNoticeGlobal)
		self.connect(self.loadFriendsCheckinsWorker, QtCore.SIGNAL('dismissProcessingDialog()'), self.dismissProcessingDialog)
		self.connect(self.loadFriendsCheckinsWorker, QtCore.SIGNAL('finished()'), self.finishedLoadingFriendsCheckingsFromFile)

		# worker thread to retrieve checkins from server
		self.refreshFriendsWorker = RefreshFriendsWorkerThread()
		self.connect(self.refreshFriendsWorker, QtCore.SIGNAL('finished()'), self.loadFriendsCheckingsResultsFromFile)
		self.connect(self.refreshFriendsWorker, QtCore.SIGNAL('displayInfoNotice()'), self.displayInfoNoticeGlobal)

		# nearby worker
		self.nearbyPlacesWorker = NearbyWorkerThread()
		self.connect(self.nearbyPlacesWorker, QtCore.SIGNAL('finished()'), self.loadNearby)

		# user info fro server worker
		self.loadUserInfoFromServerWorker = LoadUserInfoFromServerThread()
		self.connect(self.loadUserInfoFromServerWorker ,QtCore.SIGNAL('finished()'),self.loadLoggedInUserInfoFromCache)

		# history loader worker
		self.historyLoaderWorker = UserHistoryLoaderThread()
		self.connect(self.historyLoaderWorker, QtCore.SIGNAL('clearHistoryListWidget()'), self.clearHistoryListWidget)
		self.connect(self.historyLoaderWorker, QtCore.SIGNAL('addItemToHistoryListWidget'), self.addItemToHistoryListWidget)

		self.connect(self.bttnSignIn, QtCore.SIGNAL('clicked()'),
				self.doSignInClicked)	

		self.signInDlg = SignInDialog()		
		self.connect(self.signInDlg, QtCore.SIGNAL('signOutFinished()'),
			self.onSignInDialogClosed)

		self.confirmSignOutDlg = ConfirmSignOutDialog()
		self.connect(self.confirmSignOutDlg, QtCore.SIGNAL('finished(int)'),
			self.onSignOutDialogClosed)

		self.connect(self.bttnRefresh, QtCore.SIGNAL('clicked()'),
			self.doRefreshListWidget)		
		self.connect(self.bttnSearch, QtCore.SIGNAL('clicked()'),
			self.showSearchDialog)
		# print 'Bind Places signal'
		self.connect(self.placesListWidget, QtCore.SIGNAL('itemClicked(QListWidgetItem*)'),
			self.doNearbyItemClicked)
		# print 'Bind Search signal'
		self.connect(self.searchListWidget, QtCore.SIGNAL('itemClicked(QListWidgetItem*)'),
			self.doNearbyItemClicked)
		# print 'Bind Friends signal'
		self.connect(self.friendsListWidget, QtCore.SIGNAL('itemClicked(QListWidgetItem*)'),
			self.doFriendItemClicked)
		self.connect(self.historyListWidget, QtCore.SIGNAL('itemClicked(QListWidgetItem*)'),
			self.doNearbyItemClicked)		

		if (fsRequestToken != None):
			self.loadLoggedInUserInfoFromCache()
			self.doGetUserDetailForLoggedInUser()
			if (not os.path.exists(userPreferencesDir + 'checkinsResultsCache.xml')):
			 	self.doLoadFriendsCheckings()
			else:
			 	self.loadFriendsCheckingsResultsFromFile()			
			if (not os.path.exists(userPreferencesDir + 'nearbyCache.xml')):
				self.getNearby()
			else:
			 	self.loadNearby()
			if os.path.exists(userPreferencesDir + 'historyCache.xml'):
			 	self.reloadMainWindowWithHistoryResults()
		# else:
		#	self.doSignInClicked()
		self.historyWorker = HistoryWorkerThread()
		self.connect(self.historyWorker, QtCore.SIGNAL('finished()'),
			self.historyFinished)
		self.connect(self.historyWorker, QtCore.SIGNAL('reloadMainWindowWithResultsOfHistory()'), self.reloadMainWindowWithHistoryResults)

	def doAboutActionTriggered(self):
		QtGui.QMessageBox.about(self, 'About ' + VERSION_STRING,"Copyright (c) 2010 Chili Technologies LLC\nVisit http://google.com/group/barriosquare or http://chilitechno.com/fster for more information.")

	def doClearCacheActionTriggered(self):
		reply = QtGui.QMessageBox.question(self, 'Clear Cache?',"Are you sure you want to clear the cache? Cached place data, recent history, friends checkins, and other resources will be removed from device.", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
		if reply == QtGui.QMessageBox.Yes:
			# TODO: do delete cache items
			print 'TODO'

	def finishedLoadingFriendsCheckingsFromFile(self):
		global friendRefreshCount
		friendRefreshCount = friendRefreshCount + 1
		print 'friendRefreshCount = %d' % friendRefreshCount
		# track friends reload count - if first reload count, i.e. first reload from startup, then do another refresh
		if friendRefreshCount == 1:
			self.doLoadFriendsCheckings()
		
	def closeEvent(self, event):
		reply = QtGui.QMessageBox.question(self, 'Quit?',"Are you sure you want to quit barrioSquare?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
		if reply == QtGui.QMessageBox.Yes:
			global getLocationChildPID
			if getLocationChildPID > 0:
				# kill subprocess before exit
				os.kill(getLocationChildPID, 9)
			event.accept()				
		else:
			event.ignore()

	def checkUnauthorized(self,xmlString):
		IsUnauthorized = 0
		unauthorizedNodes = xmlString.getElementsByTagName('unauthorized')
		if unauthorizedNodes.length > 0:
			IsUnauthorized = 1
			if unauthorizedNodes[0].firstChild.data == 'TOKEN_EXPIRED':
				IsUnauthorized = 1
		else:
			IsUnauthorized = 0
		return IsUnauthorized

	def addItemToFriendsListWidget(self,displayStr,addressString,photoFile,OffGrid,checkinId):
		# this method is called from our worker thread to update UI on main thread
		checkinItem = QtGui.QListWidgetItem('',self.friendsListWidget)
		checkinItem.setSizeHint(QtCore.QSize(770, 75))
		wItem = FriendListItem()

		wItem.setText(displayStr,addressString,'dateStr',photoFile)
		self.friendsListWidget.setItemWidget(checkinItem,wItem)
		if OffGrid:
			checkinItem.setStatusTip('-1')
		else:
			checkinItem.setStatusTip(checkinId)

	def addItemToHistoryListWidget(self,venueName,shout,addressString,OffGrid,venueID):
		nearbyItem = QtGui.QListWidgetItem('',self.historyListWidget)	
		nearbyItem.setSizeHint(QtCore.QSize(770, 75))
		wItem = VenueListItem()
		if venueName != '':
			wItem.setText(venueName,addressString)
		else:
			wItem.setText('You said: ' + shout,addressString)
		self.historyListWidget.setItemWidget(nearbyItem,wItem)
		nearbyItem.setStatusTip(venueID)

	def addItemToPlacesListWidget(self,venueName,addressString,venueID):
		nearbyItem = QtGui.QListWidgetItem('',self.placesListWidget)	
		nearbyItem.setSizeHint(QtCore.QSize(770, 75))
		wItem = VenueListItem()
		wItem.setText(venueName,addressString)
		self.placesListWidget.setItemWidget(nearbyItem,wItem)
		nearbyItem.setStatusTip(venueID)

	def clearHistoryListWidget(self):
		self.historyListWidget.clear()
			
	def clearPlacesListWidget(self):
		self.placesListWidget.clear()

	def clearFriendsListWidget(self):
		self.friendsListWidget.clear()
	
	def doShowHistoryTab(self):
		self.bttnFriends.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnPlaces.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnSearch.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnHistory.setStyleSheet(QPUSHBUTTON_HIGHLIGHT)
		self.tabWidget.setCurrentWidget(self.historyTab)

	def doShowFriendsTab(self):
		self.bttnFriends.setStyleSheet(QPUSHBUTTON_HIGHLIGHT)
		self.bttnPlaces.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnSearch.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnHistory.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.tabWidget.setCurrentWidget(self.friendsTab)

	def doShowPlacesTab(self):
		self.bttnFriends.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnPlaces.setStyleSheet(QPUSHBUTTON_HIGHLIGHT)
		self.bttnSearch.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnHistory.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.tabWidget.setCurrentWidget(self.placesTab)

	def doShowLocationSettingsDialog(self):
		# print 'doShowLocationSettingsDialog'
		self.locationSettingsDlg = LocationSettingsDialog()
		self.locationSettingsDlg.show()

	def historyFinished(self):
		if self.processDlg != None:
			self.processDlg.close()

	def simpleNetworkTest(self):
		networkResult = False
		try:
			response = urllib2.urlopen('http://foursquare.com/img/scoring/3.png')
			networkResult = True
		except:
			networkResult = False
		return networkResult

	def testNetworkConnection(self):
		client3 = oauthclient.SimpleOAuthClient('api.foursquare.com', 80, API_PREFIX_URL+'test', ACCESS_TOKEN_URL, AUTHORIZATION_URL)
		consumer = oauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
		signature_method_plaintext = oauth.OAuthSignatureMethod_PLAINTEXT()
		signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
	
		nearbyParams = {
			'test':	'ok'
		}
		oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, callback=CALLBACK_URL, http_url=API_PREFIX_URL+'test', parameters=nearbyParams)
		oauth_request.sign_request(signature_method_plaintext, consumer, fsRequestToken)
		print oauth_request.to_postdata()
		testResultXml = client3.access_resource(oauth_request, http_url=API_PREFIX_URL+'test', requestType='GET')

	def reloadMainWindowWithHistoryResults(self):
		# print 'reloadMainWindowWithHistoryResults'
		# start the history worker loader thread
		self.historyLoaderWorker.start()
	
	def dismissProcessingDialog(self):
		if self.processDlg != None:
			self.processDlg.close()		

	def displayInfoNotice(self,infoString):
		note = osso.SystemNote(self.osso_c)
		result = note.system_note_infoprint(infoString)

	def displayInfoNoticeGlobal(self):
		global infoNoticeString
		self.displayInfoNotice(infoNoticeString)

	def locationAcquired(self):
		print 'locationAcquired'
		self.displayInfoNotice('Location Updated')
		if self.locationDialog != None:		
			strLatLon = '%f' % currentLatitude
			strLatLon += ',%f' % currentLongitude
			print strLatLon
			self.locationDialog.strLatLon = strLatLon
			self.locationDialog.web.load(QtCore.QUrl('http://maps.google.com/maps/api/staticmap?center=' + self.locationDialog.strLatLon + '&size=600x245&maptype=roadmap&markers=color:red|' + self.locationDialog.strLatLon + '&zoom=14&sensor=false&key=' + GOOGLE_MAPS_API_KEY))
		
	def doShowLocationDialog(self):
		global currentLatitude
		global currentLongitude

		strLatLon = '%f' % currentLatitude
		strLatLon += ',%f' % currentLongitude

		self.locationDialog = MyLocationDialog(strLatLon)
		self.locationDialog.show()

	def doSignInClicked(self):
		# print 'doSignInClicked'
		global fsRequestToken
	
		if fsRequestToken == None:
			self.signInDlg.show()
		else:
			global doingSignout
			doingSignout = False		
			self.confirmSignOutDlg.show()

	def doRefreshListWidget(self):
		# see which tab is showing
		# self.getNearby()
		print 'current tab index: %d' % self.tabWidget.currentIndex()

		if self.tabWidget.currentIndex() < 3:
			refreshTxt = ''
			if self.tabWidget.currentIndex() == 0:
				refreshTxt = 'Please wait while we contact the server to refresh your friends\' recent checkin list. This action may take up to 30 seconds to complete depending on the server load.'
			elif self.tabWidget.currentIndex() == 1:
				refreshTxt = 'Please wait while we contact the server to refresh the nearby venue list. This action may take up to 30 seconds to complete depending on the server load.'
			elif self.tabWidget.currentIndex() == 2:
				refreshTxt = 'Please wait while we contact the server to refresh your checkin history. This action may take up to 30 seconds to complete depending on the server load.'

			self.processDlg = ProcessingDialog('Refreshing',refreshTxt)
			self.processDlg.show()
			if self.tabWidget.currentIndex() == 0:
				# refresh friends
				self.doLoadFriendsCheckings()
			elif self.tabWidget.currentIndex() == 1:
				# refresh nearby
				self.getNearby()
			elif self.tabWidget.currentIndex() == 2:
				self.historyWorker.start()

	def doGetUserDetailForLoggedInUser(self):
		# print 'doGetUserDetailForLoggedInUser'
		# call worker thread
		self.loadUserInfoFromServerWorker.setup(0)
		self.loadUserInfoFromServerWorker.start()

	def loadLoggedInUserInfoFromCache(self):
		# print 'loadLoggedInUserInfoFromCache'
		if os.path.exists(userPreferencesDir + 'userDetailCache.xml'):
			userXmlFile = open(userPreferencesDir + 'userDetailCache.xml','r')
			userXmlString = ''
			for line in userXmlFile:
				userXmlString += line
			userXmlFile.close()		
			parseSuccess = False
			try:
				userXml = parseString(userXmlString)
				parseSuccess = True
			except xml.parsers.expat.ExpatError:
				print 'error parsing userXmlString'
				parseSuccess = False
				print userXmlString
			if parseSuccess == True:
				global loggedInUserID
				userNode = userXml.getElementsByTagName('user')
			
				try:
					loggedInUserID = int(userNode[0].getElementsByTagName('id')[0].firstChild.data)
					print 'logged in user: %d' % loggedInUserID	
				except IndexError:
					print 'unable to read userID from response'
					loggedInUserID = 0	
	
	def showSearchDialog(self):
		self.tabWidget.setCurrentWidget(self.searchResultsTab)
		self.bttnFriends.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnPlaces.setStyleSheet(QPUSHBUTTON_DEFAULT)
		self.bttnSearch.setStyleSheet(QPUSHBUTTON_HIGHLIGHT)
		self.searchDlg = SearchDialog()
		self.searchDlg.show()
	
	# @QtCore.pyqtSlot()
	def onSignInDialogClosed(self):
		if  (hasToken == 1):
			self.bttnSignIn.setText('')
			self.bttnSearch.show()
			self.bttnRefresh.show()
			self.bttnLocation.show()
			self.bttnFriends.show()
			self.bttnPlaces.show()
			self.doShowFriendsTab()
			self.doGetUserDetailForLoggedInUser()

			# set a 'loading...' item
			checkinItem = QtGui.QListWidgetItem('',self.friendsListWidget)
			checkinItem.setSizeHint(QtCore.QSize(770, 75))
			wItem = FriendListItem()
			wItem.setText('Retrieving recent checkins...','','',APP_DIRECTORY + 'refreshing.gif')
			self.friendsListWidget.setItemWidget(checkinItem,wItem)
			checkinItem.setStatusTip('0')

			self.doLoadFriendsCheckings()
			self.getNearby()
		else:
			self.bttnSignIn.setText('')
			self.bttnSearch.hide()
			self.bttnRefresh.hide()
			self.bttnLocation.hide()
			self.bttnFriends.hide()
			self.bttnPlaces.hide()

	def onSignOutDialogClosed(self):
		print 'onSignOutDialogClosed'
		global doingSignout
		if doingSignout:
			doingSignout = False
			print 'doSignOut'	
			global fsRequestToken
			global fsRequestTokenString
			global fsSecret
			global fsKey
			global hasToken
			fsRequestToken = None
			fsRequestTokenString = ''
			fsSecret = ''
			fsKey = ''
			hasToken = 0
			# delete tokenFile
			os.remove(userPreferencesDir + 'tokenFile')
			self.bttnSignIn.setText('')
			self.bttnSearch.hide()
			self.bttnRefresh.hide()
			self.bttnLocation.hide()
			self.bttnFriends.hide()
			# reset the friends list widgets
			self.friendsListWidget.clear()

	def doSignOut(self):
		print 'Signing out'
		global doingSignout
		doingSignout = False		
		self.confirmSignOutDlg.show()

	def calcDateString(self, strDate):
		timeSinceEpoch = int(time.mktime(time.strptime(strDate,'%a, %d %b %y %H:%M:%S +0000')))
		currentTimeSinceEpoch = int(time.mktime(time.gmtime()))
		# print 'timeSinceEpoch: %d' % timeSinceEpoch
		# print 'currentTimeSinceEpoch %d' % currentTimeSinceEpoch
		timeDiffSecs = currentTimeSinceEpoch - timeSinceEpoch
		# print 'timeDiffSecs: %d' % timeDiffSecs
		if timeDiffSecs < 60:
			timeString = str(timeDiffSecs) + 's ago'
		elif timeDiffSecs < 3600:
			mins = int(math.ceil(timeDiffSecs / 60))
			timeString = str(mins) + 'm ago'
		elif timeDiffSecs < 18000:
			hours = int(math.floor(timeDiffSecs / 3600))
			mins = int(math.ceil((timeDiffSecs - (3600 * hours)) / 60))
			timeString = str(hours) + 'h ' + str(mins) + 'm ago'
		elif timeDiffSecs < 86400:
			hours = int(math.ceil(timeDiffSecs / 3600))
			timeString = str(hours) + 'h ago'
		else:
			days = int(math.ceil(timeDiffSecs / 86400))
			timeString = str(days) + 'd ago'
		return timeString
		
	def loadFriendsCheckingsResultsFromFile(self):
		print 'loadFriendsCheckingsResults'
		self.loadFriendsCheckinsWorker.start()

	def doLoadFriendsCheckings(self):
		self.refreshFriendsWorker.start()

	def displayCheckinDetails(self):
		print 'displayCheckinDetails'
		self.checkinResultsDlg = CheckinResultsDialog()
		self.checkinResultsDlg.show()


	def loadSearchResults(self):
		print 'loadSearchResults'
		searchXmlFile = open(userPreferencesDir + 'searchResultsCache.xml','r')
		searchXmlString = ''
		for line in searchXmlFile:
			searchXmlString += line
		searchXmlFile.close()
		# print nearbyXmlString
		searchXml = parseString(searchXmlString)

		# remove items from list
		self.searchListWidget.clear()

		# switch the current tab to search tab
		self.tabWidget.setCurrentWidget(self.searchResultsTab)

		# loop over xml venues and add to list widget
		searchNodes = searchXml.getElementsByTagName('venue')
		for node in searchNodes:
			nearbyItem = QtGui.QListWidgetItem('',self.searchListWidget)	
			nearbyItem.setSizeHint(QtCore.QSize(770, 75))
			wItem = VenueListItem()
			addressString = node.getElementsByTagName('address')[0].firstChild.data
			if node.getElementsByTagName('crossstreet').length > 0:
				addressString += ' (' + node.getElementsByTagName('crossstreet')[0].firstChild.data + ')'
			addressString += ' ~' + self.calcMetersAsString(node.getElementsByTagName('distance')[0].firstChild.data)
			wItem.setText(node.getElementsByTagName('name')[0].firstChild.data,addressString)
			self.searchListWidget.setItemWidget(nearbyItem,wItem)
			nearbyItem.setStatusTip(node.getElementsByTagName('id')[0].firstChild.data)


			# print node.getElementsByTagName('id')[0].firstChild.data
			# searchPlaceString = node.getElementsByTagName('name')[0].firstChild.data
			# searchPlaceString += ' (' + self.calcMetersAsString(node.getElementsByTagName('distance')[0].firstChild.data) + ')'
			# searchItem = QtGui.QListWidgetItem(searchPlaceString,self.searchListWidget)
			# searchItem.setFont(QtGui.QFont('Helvetica', 30))
			# searchItem.setStatusTip(node.getElementsByTagName('id')[0].firstChild.data)	

	def calcMetersAsString(self,mtr):
		meters = int(mtr)
		returnString = ''
		if (meters < 1000):
			returnString = str(meters) + 'm'
		else:
			km = float(meters) / 1000.0
			returnString = '%.1f' % km
			returnString += 'km'
		return returnString
	
	def loadNearby(self):
		self.loadNearbyVenuesWorker.start()
		
	def getNearby(self):
		print 'getNearby'
		self.nearbyPlacesWorker.start()
	
	def doFriendItemClicked(self,item):
		print 'doFriendItemClicked'
		if str(item.statusTip()) != '-1':
			self.friendCheckingDlg = FriendCheckinDetailDialog(str(item.statusTip()),self)
			self.friendCheckingDlg.show()
	
	def doNearbyItemClicked(self,item):
		print 'Item Clicked: ' + item.statusTip()
		if str(item.statusTip()) != '-1':
			self.loadingWorker = PlaceInfoLoaderWorkerThread()
			self.placeInfoDlg = PlaceInfoDialog(item.statusTip(),self,self)

			self.loadingWorker.setup(item.statusTip(), self.placeInfoDlg, False)
			self.connect(self.loadingWorker, QtCore.SIGNAL('finished()'), self.nearbyItemLoadingFinished)

			self.loadingWorker.start()

			# show processing dialog
			self.processDlg = ProcessingDialog('Loading...','Please wait while we load the selected item. We may contact the server to refresh with the latest information')
			self.processDlg.show()

	def nearbyItemLoadingFinished(self):
		print 'nearbyItemLoadingFinished - executing on main gui thread'
		self.placeInfoDlg.loadingFinished()
		self.processDlg.close()
		self.processDlg = None
		time.sleep(1)
		self.placeInfoDlg.show()


	def getUserPhoto(self,photoURL):
		print 'getUserPhoto'
		photoResponse = urllib2.urlopen(photoURL)
		photoData = photoResponse.read()

		# save filename as userpix_thumbs_61003_1256906281858.jpg
		photoURLchunks = photoURL.split('/')
		saveFile = photoURLchunks[3] + '_' + photoURLchunks[4]

		photoFile = open(userPreferencesDir + 'imageCache' + os.sep + 'users' + os.sep + saveFile,'w')
		photoFile.write(photoData)
		photoFile.close()

class LocationManagerThread(QtCore.QThread):
	def __init__(self, parent = None):
    		QtCore.QThread.__init__(self, parent)
		self.exiting = False

	def run(self):
		print 'LocationManagerThread.start()'
		global locationSubprocessIsRestarting
		global locationSubprocessRestartCount
		locationSubprocessRestartCount = locationSubprocessRestartCount + 1
		locationSubprocessIsRestarting = False		

		if locationSubprocessRestartCount > 1:
			time.sleep(15)

		child = subprocess.Popen(['python',GET_LOCATION_SCRIPT], shell=False, stdout=None)
		global getLocationChildPID
		getLocationChildPID = child.pid
		child.wait()
		print 'child process finished'

	def __del__(self):
		self.exiting = True
		self.wait()

class LocationBackgroundUpdateThread(QtCore.QThread):
	def __init__(self, parent = None):
    		QtCore.QThread.__init__(self, parent)
		self.exiting = False

	def run(self):		
		lastLocationReadTime = time.time()
		lastSuccessfulReadTime = time.time()
		global getLocationChildExecutionCount
		global locationMethodType
		global infoNoticeString
		global currentLatitude
		global currentLongitude
		global horizontalAccuracy
		global verticalAccuracy
		global acquisitionCount
		global locationSubprocessIsRestarting

		while not self.exiting:
			if (os.path.exists(userPreferencesDir + 'CurrentLocation.txt')):
				# this delta will keep increasing every loop iteration until it is reset by a successful read	
				# if the delta gets too big, switch the location type to coarse
				# kill and restart the child process
				currentReadSuccessDelta = time.time() - lastSuccessfulReadTime
				# print 'currentReadSuccessDelta: %d' % currentReadSuccessDelta
		
				locationModificationTime = os.path.getmtime(userPreferencesDir + 'CurrentLocation.txt')		
				# print 'locationModificationTime = %d' % locationModificationTime
				# print 'lastLocationReadTime = %d' % lastLocationReadTime
				# print 'lastSuccessfulReadTime = %d' % lastSuccessfulReadTime
				if lastLocationReadTime != locationModificationTime:
					lastLocationReadTime = locationModificationTime
					# time difference, so load file
					try:
						strCurrentLatitude = '0.0'
						strCurrentLongitude = '0.0'
						strCurrentHAccuracy = '1000000'
						strCurrentVAccuracy = '1000000'
						locationFile = open(userPreferencesDir + 'CurrentLocation.txt','r')
						i = 0
						for line in locationFile:
							# print 'line: ' + line
							i = i + 1
							if (i == 1):
								strCurrentLatitude = '%s' % line
							if (i == 2):
								strCurrentLongitude = '%s' % line
							if (i == 3):
								strCurrentHAccuracy = '%s' % line
							if (i == 4):
								strCurrentVAccuracy = '%s' % line
						locationFile.close()
						# print 'i was %d' % i
						if strCurrentLatitude != '0.0' and strCurrentLongitude != '0.0':
							acquisitionCount = acquisitionCount + 1
							currentLatitude = float(strCurrentLatitude)
							currentLongitude = float(strCurrentLongitude)
							print 'retrieved Latitude: %f' % currentLatitude
							print 'retrieved Longitude: %f' % currentLongitude
							if strCurrentHAccuracy == '-1':
								horizontalAccuracy = 1000000.0
							else:
								horizontalAccuracy = float(strCurrentHAccuracy)
							if strCurrentVAccuracy == '-1':
								verticalAccuracy = 1000000.0
							else:
								verticalAccuracy = float(strCurrentVAccuracy)
							# nfoNoticeString = 'Location updated'
							# self.emit(QtCore.SIGNAL('displayInfoNotice()'))
							lastSuccessfulReadTime = time.time()
					except:
						print 'error reading file'
				else:
					if not locationSubprocessIsRestarting:
						# if delta is more than a minute and no initial lock, downgrade location method to 0 = User selected to allow coarse accuracy and speedy lock
						if locationMethodType > 0:
							if acquisitionCount == 0:
								if currentReadSuccessDelta > 90:
									if locationMethodType == 4:
										infoNoticeString = 'Failed to update location via GPS, switching to coarse accuracy'
										self.emit(QtCore.SIGNAL('displayInfoNotice()'))
					
									locationMethodType = 0
									lastSuccessfulReadTime = time.time()
									self.emit(QtCore.SIGNAL('restartSubProcess()'))
							else:
								if currentReadSuccessDelta > 180:
									locationMethodType = 0
									lastSuccessfulReadTime = time.time()
									self.emit(QtCore.SIGNAL('restartSubProcess()'))
					else:
						lastSuccessfulReadTime = time.time()
			time.sleep(10)

	def __del__(self):
		self.exiting = True
		self.wait()

class LocationManager(QtCore.QObject):
	def __init__(self):
		QtCore.QObject.__init__(self)
		self.locationWorker = LocationManagerThread()
		self.locationBackgroundWorker = LocationBackgroundUpdateThread()
		# self.connect(self.locationWorker, QtCore.SIGNAL('finished()'), self.loadLocationFromFile)
		self.connect(self.locationBackgroundWorker, QtCore.SIGNAL('displayInfoNotice()'), self.displayInfoNoticeGlobal)		
		self.connect(self.locationBackgroundWorker, QtCore.SIGNAL('restartSubProcess()'), self.restartSubprocess)		

	def saveLocationMethodType(self):
		global locationMethodType
		locationMethodFile = open(userPreferencesDir + 'locationMethodType.txt','w')
		print 'locationMethodType: %d' % locationMethodType
		locationMethodFile.write(str(locationMethodType) + '\n')
		locationMethodFile.close()

	def restartSubprocess(self):
		global getLocationChildPID
		global locationSubprocessIsRestarting
		global acquisitionCount
		acquisitionCount = 0
		locationSubprocessIsRestarting = True
		print 'subprocess pid: %d' % getLocationChildPID
		if getLocationChildPID > 0:
			os.kill(getLocationChildPID, 9)
			time.sleep(1)
		self.saveLocationMethodType()
		self.locationWorker.start()

	def displayInfoNoticeGlobal(self):
		global infoNoticeString
		global qb
		if qb != None:
			qb.displayInfoNotice(infoNoticeString)

	def loadLocationFromFile(self):
		strCurrentLatitude = '0.0'
		strCurrentLongitude = '0.0'
		strCurrentHAccuracy = '1000000'
		strCurrentVAccuracy = '1000000'
		locationFile = open(userPreferencesDir + 'CurrentLocation.txt','r')
		i = 0
		for line in locationFile:
			# print 'line: ' + line
			i = i + 1
			if (i == 1):
				strCurrentLatitude = '%s' % line
			if (i == 2):
				strCurrentLongitude = '%s' % line
			if (i == 3):
				strCurrentHAccuracy = '%s' % line
			if (i == 4):
				strCurrentVAccuracy = '%s' % line
		locationFile.close()
		print 'i was %d' % i
		if strCurrentLatitude != '0.0' and strCurrentLongitude != '0.0':
			global currentLatitude
			global currentLongitude
			global horizontalAccuracy
			global verticalAccuracy
			currentLatitude = float(strCurrentLatitude)
			currentLongitude = float(strCurrentLongitude)
			print 'retrieved Latitude: %f' % currentLatitude
			print 'retrieved Longitude: %f' % currentLongitude
			if strCurrentHAccuracy == '-1':
				horizontalAccuracy = 1000000.0
			else:
				horizontalAccuracy = float(strCurrentHAccuracy)
			if strCurrentVAccuracy == '-1':
				verticalAccuracy = 1000000.0
			else:
				verticalAccuracy = float(strCurrentVAccuracy)
			global qb
			if qb == None:
				print 'qb is None'
			else:
				qb.locationAcquired()
							
		else:
			# reacquire fix
			self.acquireLocationFix()

	def acquireLocationFix(self):
		print 'LocationManager.acquireLocationFix'
		self.locationWorker.start()
		self.locationBackgroundWorker.start()
	
app = QtGui.QApplication(sys.argv)

locationManagerObj = LocationManager()

if (os.path.exists(userPreferencesDir + 'CurrentLocation.txt')):
	locationManagerObj.loadLocationFromFile()

print 'Checking to see if token exists'
if (os.path.exists(userPreferencesDir + 'tokenFile')):
	print 'Token file exists, loading token'
	readTokenFile = open(userPreferencesDir + 'tokenFile')
	fsToken = readTokenFile.readline()
	fsRequestTokenString = fsToken
	print fsToken
        params = cgi.parse_qs(fsToken, keep_blank_values=False)
        key = params['oauth_token'][0]
	fsKey = key
        secret = params['oauth_token_secret'][0]
	fsSecret = secret
	fsRequestToken = oauth.OAuthToken(key, secret)
	print fsRequestToken
	print fsKey
	print fsSecret

# set up a separate thread for location acquisition
locationFixAcquired = 0

locationManagerObj.acquireLocationFix()

if showSplashScreen:
	splashScreen = SplashScreenDialog()
	splashScreen.show()

qb = MainWindow()
qb.show()
sys.exit(app.exec_())

