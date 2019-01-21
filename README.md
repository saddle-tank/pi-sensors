# pi-sensors
Sensors on my raspberry pi
These programs are for creating RRD databases for my sensors that are being read by a number of raspberry-pi computers.

Some sensors are on a 1-Wire micro LAN and some are wired directly to the pi's GPIO.

The sensor connected pies are polled from a central pi to collect the sensor data which is added to RRD databases (one db per sensor)
RRD is used to graph the sensor data and display it on a web page


