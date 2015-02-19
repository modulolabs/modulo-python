#!/usr/bin/python

import modulo, datetime

port = modulo.Port()
clock = modulo.Clock(port)

clock.set_datetime(datetime.datetime.now())

print(clock.get_datetime())
