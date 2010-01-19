# 
# this file should not be called directly.
# called from barriosq.py
#

import location
import gobject
import os

currentLatitude = 0
currentLongitude = 0
lockCount = 0
partialLockCount = 0
locationMethodType = 0

userPreferencesDir = os.path.expanduser('~') + os.sep + '.barriosquare' + os.sep

locationMethodFile = open(userPreferencesDir + 'locationMethodType.txt','r')
i = 0
for line in locationMethodFile:
	print 'line: ' + line
	i = i + 1
	if (i == 1):
		locationMethodType = int(line)

locationMethodFile.close()
print 'loaded locationMethodType: %d' % locationMethodType

if (not os.path.exists(userPreferencesDir)):
	print 'Creating Pref Dir'
	os.mkdir(userPreferencesDir)		

def on_error(control, error, data):
    print "location error: %d... quitting" % error
    data.quit()

def on_changed(device, data):
    if not device:
        return
    if device.fix:
        if device.fix[1] & location.GPS_DEVICE_LATLONG_SET:
	    global currentLatitude
	    global currentLongitude
	    global lockCount
	    currentLatitude = device.fix[4]
	    currentLongitude = device.fix[5]
            print "lat = %f, long = %f" % device.fix[4:6]
	    if (currentLatitude == 0) or (currentLongitude == 0):
		print 'Partial lock acquired'
		global partialLockCount
		partialLockCount += 1
	    else:
		print 'Full lock acquired'
		lockCount += 1
		print 'lock count: %d' % lockCount
		
		locationFile = open(userPreferencesDir + 'CurrentLocation.txt','w')
		strCurrentLatitude = "%f" % currentLatitude
		strCurrentLongitude = "%f" % currentLongitude

		if ((lockCount == 3) and (partialLockCount > 0)) or ((lockCount == 2) and (partialLockCount == 0)):
			locationFile.write(strCurrentLatitude + '\n')
			locationFile.write(strCurrentLongitude + '\n')
			locationFile.close()	

		    	data.stop()

def on_stop(control, data):
    print "quitting"
    data.quit()

def start_location(data):
    data.start()
    return False

loop = gobject.MainLoop()

control = location.GPSDControl.get_default()
device = location.GPSDevice()

if locationMethodType == 0:
	control.set_properties(preferred_method=location.METHOD_USER_SELECTED,
                      preferred_interval=location.INTERVAL_DEFAULT)
elif locationMethodType == 1:
	control.set_properties(preferred_method=location.METHOD_CWP,
                       preferred_interval=location.INTERVAL_DEFAULT)
elif locationMethodType == 2:
	control.set_properties(preferred_method=location.METHOD_ACWP,
                       preferred_interval=location.INTERVAL_DEFAULT)
elif locationMethodType == 3:
	control.set_properties(preferred_method=location.METHOD_GNSS,
                       preferred_interval=location.INTERVAL_DEFAULT)
elif locationMethodType == 4:
	control.set_properties(preferred_method=location.METHOD_AGNSS,
                       preferred_interval=location.INTERVAL_DEFAULT)

# control.set_properties(preferred_method=location.METHOD_USER_SELECTED,
#                       preferred_interval=location.INTERVAL_DEFAULT)

control.connect("error-verbose", on_error, loop)
device.connect("changed", on_changed, control)
control.connect("gpsd-stopped", on_stop, loop)

gobject.idle_add(start_location, control)

loop.run()
