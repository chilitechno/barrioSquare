# This file is part of barrioSquare.
# 
# v0.1.20
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
# this file should not be called directly.
# called from barriosq.py
#

import location
import gobject
import os
import time
import sys
import socket

print sys.argv

getLocationChildPID = 0
currentLatitude = 0
currentLongitude = 0
lockCount = 0
partialLockCount = 0
locationMethodType = int(sys.argv[1])
serverPort = int(sys.argv[2])

maxPartialLockCount = 0
maxLockCount = 0

userPreferencesDir = os.path.expanduser('~') + os.sep + '.barriosquare' + os.sep

# print 'loaded locationMethodType: %d' % locationMethodType

# create the socket to back to the server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', serverPort))
sock.send('INITIALIZING\n\r')

if (not os.path.exists(userPreferencesDir)):
	print 'Creating Pref Dir'
	os.mkdir(userPreferencesDir)		

def on_error(control, error, data):
    print "location error: %d... quitting" % error
    data.quit()

def on_changed(device, data):
	if not device:
		return
	if device.status == location.GPS_DEVICE_STATUS_NO_FIX:
		return
	if device.fix:
		if device.fix[1] & location.GPS_DEVICE_LATLONG_SET:
			global sock
			global currentLatitude
			global currentLongitude
			global lockCount
			currentLatitude = device.fix[4]
			currentLongitude = device.fix[5]
			horizAcc = str(device.fix[6])
			vertAcc = str(device.fix[7])
			# print device.fix[6]
			# print "lat = %f" % currentLatitude
			# print "long = %f" % currentLongitude
			# print "horizAcc = " + horizAcc
			if horizAcc == 'nan':
				realHorizAcc = -1
			else:
				realHorizAcc = float(horizAcc) / 100
			if vertAcc == 'nan':
				realVertAcc = -1
			else:
				realVertAcc = float(vertAcc) / 100

			# print 'Full lock acquired'
			lockCount += 1
			print 'Fl|' + str(lockCount) + '|' + str(currentLatitude) + '|' + str(currentLongitude) + '|' + str(realHorizAcc) + '|' + str(realVertAcc)
			# print 'lock count: %d' % lockCount

			strCurrentLatitude = "%f" % currentLatitude
			strCurrentLongitude = "%f" % currentLongitude
			
			sockCommand = 'UPDATING_LOCATION|' + str(currentLatitude) + '|' + str(currentLongitude) + '|' + str(realHorizAcc) + '|' + str(realVertAcc)
			sock.send(sockCommand + '\n\r')
			
			#
			# locationFile = open(userPreferencesDir + 'CurrentLocation.txt','w')
			# locationFile.write(strCurrentLatitude + '\n')
			# locationFile.write(strCurrentLongitude + '\n')
			# locationFile.write(str(realHorizAcc) + '\n')
			# locationFile.write(str(realVertAcc) + '\n')
			# locationFile.close()	
			# time.sleep(2)
			# data.stop()			

def on_stop(control, data):
    print "quitting"
    global sock
    sock.close()
    data.quit()

def start_location(data):
    data.start()
    return False

loop = gobject.MainLoop()

control = location.GPSDControl.get_default()
device = location.GPSDevice()

interval = location.INTERVAL_120S
print '(get-location.py) LocationMethodType: %d' % locationMethodType
if locationMethodType == 0:
	maxPartialLockCount = 4
	maxLockCount = 1
	control.set_properties(preferred_method=location.METHOD_USER_SELECTED,
                      preferred_interval=interval)
elif locationMethodType == 1:
	maxPartialLockCount = 4
	maxLockCount = 1
	control.set_properties(preferred_method=location.METHOD_CWP,
                       preferred_interval=interval)
elif locationMethodType == 2:
	maxPartialLockCount = 4
	maxLockCount = 1
	control.set_properties(preferred_method=location.METHOD_ACWP,
                       preferred_interval=interval)
elif locationMethodType == 3:
	maxPartialLockCount = 6
	maxLockCount = 1
	control.set_properties(preferred_method=location.METHOD_GNSS,
                       preferred_interval=interval)
elif locationMethodType == 4:
	maxPartialLockCount = 6
	maxLockCount = 1
	control.set_properties(preferred_method=location.METHOD_AGNSS,
                       preferred_interval=interval)

# control.set_properties(preferred_method=location.METHOD_USER_SELECTED,
#                       preferred_interval=location.INTERVAL_DEFAULT)

control.connect("error-verbose", on_error, loop)
device.connect("changed", on_changed, control)
control.connect("gpsd-stopped", on_stop, loop)

gobject.idle_add(start_location, control)

loop.run()
