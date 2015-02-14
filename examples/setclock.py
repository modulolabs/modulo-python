#!/usr/bin/python

import modulo, datetime

port = modulo.SerialPort()

clock = port.get_clock()

clock.set_datetime(datetime.datetime.now())

print clock.get_datetime()
