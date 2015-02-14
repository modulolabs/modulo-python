Modulo Python Documentation
===========================


Introduction
------------

   The Modulo python library is easy to use. Simply create a Port object
   to open a connection to the hardware, then create a specific type of
   Module object for each device that you wish to use.

   The example below gets the angle from a knob and prints it on a display.::

      import modulo, time

      port = modulo.Port()
      knob = modulo.Knob(port)
      display = modulo.Display(port)

      while True :
          display.clear()
          display.set_cursor(0,0)
          display.writeln(knob.get_angle())
          display.update()
          time.sleep(.05)

Port
----

.. autoclass:: modulo.Port
   :members:
   :undoc-members:


Modules
-------

.. autosummary::
   modulo.Module
   modulo.Display
   modulo.DPad
   modulo.Knob
   modulo.Thermocouple
   modulo.Clock
   modulo.Controller

.. autoclass:: modulo.Module
   :members:
   :undoc-members:

.. autoclass:: modulo.Display
   :members:
   :undoc-members:

.. autoclass:: modulo.DPad
   :members:
   :undoc-members:

.. autoclass:: modulo.Knob
   :members:
   :undoc-members:

.. autoclass:: modulo.Thermocouple
   :members:
   :undoc-members:

.. autoclass:: modulo.Clock
   :members:
   :undoc-members:

.. autoclass:: modulo.Controller
   :members:
   :undoc-members:



