#!/usr/bin/python

"""
Modulo Docstring
"""

import os, math
import ctypes, ctypes.util, serial


class Port(object) :
    """
    The Port class represents a physical connection to Modulo devices through a usb or i2c port.
    Once a port has been opened, create a Module object for each device that's connected to the port.

    """


    _BroadcastAddress = 9

    _BroadcastCommandGlobalReset = 0
    _BroadcastCommandGetNextDeviceID = 1
    _BroadcastCommandSetAddress = 2
    _BroadcastCommandGetAddress = 3
    _BroadcastCommandGetDeviceType = 4
    _BroadcastCommandGetVersion = 5
    _BroadcastCommandGetManufacturer = 6
    _BroadcastCommandGetProduct = 7
    _BroadcastCommandGetDocURL = 8
    _BroadcastCommandGetDocURLContinued = 9
    _BroadcastCommandGetInterrupt = 10
    _BroadcastCommandSetStatusLED = 11

    class _SerialConnection(object) :
        def __init__(self, path=None, controller=0) :
            super(Port._SerialConnection, self).__init__()

            if path is None :
                from serial.tools.list_ports import comports
                for port in comports() :
                    if (port[1] == 'Modulo Controller') :
                        if (controller == 0) :
                            path = port[0]
                            break
                        controller -= 1

            self._serial = serial.Serial(path, 9600, timeout=5)

        def transfer(self, address, command, sendData, receiveLen) :
            if address is None :
                return None

            self._serial.write('T')           # Transfer start token
            self._serial.write(chr(address))
            self._serial.write(chr(command))
            self._serial.write(chr(len(sendData)))
            for c in sendData :
                self._serial.write(chr(c))
            self._serial.write(chr(receiveLen))

            retval = ord(self._serial.read(1))
            if retval and receiveLen > 0:
                return [ord(x) for x in self._serial.read(receiveLen)]
            return None

    class _I2CConnection(object) :

        def __init__(self, i2cPath) :
            super(Port._I2CConnection, self).__init__()

            self._i2cfd = os.open(i2cPath, os.O_RDWR)
            if self._i2cfd < 0 :
                raise StandardError('Unable to open the i2c device ' + path)

            # This is the ctypes function for transferring data via i2c
            self._dll = ctypes.cdll.LoadLibrary('libmodulo.so')
            self.transferFunction = self._dll.modulotransfer

        # Wrapper around the modulotransfer function from the dll
        def transfer(self, address, command, sendData, receiveLen) :
            if address is None :
                return None

            sendBuffer = ctypes.create_string_buffer(len(sendData))
            for i in range(len(sendData)) :
                sendBuffer[i] = chr(sendData[i])
            receiveBuffer = ctypes.create_string_buffer(receiveLen)

            if (self.transferFunction(self._fd, address, command, sendBuffer, len(sendData),
                                   receiveBuffer, receiveLen) < 0) :
                return None

            return [ord(x) for x in receiveBuffer]


    def __init__(self, serialPortPath=None, i2cPortPath=None) :
        self._portInitialized = False
        self._lastAssignedAddress = 9

        if (i2cPortPath) :
            self._connection = self._I2CConnection(i2cPortPath)
        else :
            self._connection = self._SerialConnection(serialPortPath)


    def _bytesToString(self, bytes) :
        s = ''
        for b in bytes :
            if b == 0 :
                break
            s = s + chr(b)
        return s
        
    

    # Reset all devices on the port
    def _global_reset(self) :
        self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandGlobalReset, [], 0)

    def _assign_address(self, requestedDeviceType, deviceID) :
        # Ensure that a global reset has been performed
        if not self._portInitialized :
            self._portInitialized = True
            self._global_reset()

        # If no deviceID has been specified, find the first
        # device with the specified type
        if deviceID is None :
            deviceID = self._get_next_device_id(0)
            while deviceID is not None :
                deviceType = self._get_device_type(deviceID)
                if deviceType == requestedDeviceType :
                    break
                deviceID = self._get_next_device_id(deviceID+1)

        # No device found. We can't assign an address
        if deviceID is None :
            return None

        self._lastAssignedAddress += 1
        address = self._lastAssignedAddress

        self._set_address(deviceID, address)
        return address


    def _set_address(self, deviceID, address) :
        sendData = [deviceID & 0xFF, deviceID >> 8, address]
        self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandSetAddress,
            sendData, 0)
    
    def _get_address(self, deviceID) :
        sendData = [deviceID & 0xFF, deviceID >> 8]
        retval = self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandGetAddress,
            sendData, 1)
        if retval is None :
            return None
        return retval[0]

    def _get_manufacturer(self, deviceID) :
        sendData = [deviceID & 0xFF, deviceID >> 8]
        resultData = self._connection.transfer(
            self._BroadcastAddress, self._BroadcastCommandGetManufacturer, sendData, 31)
        return self._bytesToString(resultData)
        
    def _get_product(self, deviceID) :
        sendData = [deviceID & 0xFF, deviceID >> 8]
        resultData = self._connection.transfer(
            self._BroadcastAddress, self._BroadcastCommandGetProduct, sendData, 31)
        return self._bytesToString(resultData)

    def _set_status(self, deviceID, status) :
        sendData = [deviceID & 0xFF, deviceID >> 8, status]
        resultData = self._connection.transfer(
            self._BroadcastAddress, self._BroadcastCommandSetStatusLED, sendData, 0)

    # Returns the device ID of the device on the port with the
    # next greater ID than the one provided.
    def _get_next_device_id(self, lastDeviceID) :
        sendData = [lastDeviceID & 0xFF, lastDeviceID >> 8]
        resultData = self._connection.transfer(
            self._BroadcastAddress, self._BroadcastCommandGetNextDeviceID, sendData, 2)
        if resultData is None :
            return None
        return resultData[1] | (resultData[0] << 8)
    
    def _get_version(self, deviceID) :
        sendData = [deviceID & 0xFF, deviceID >> 8]
        retval = self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandGetVersion,
            sendData, 2)
        if retval is None :
            return None
        return retval[0] | (retval[1] << 8)

    def _get_device_type(self, deviceID) :
        sendData = [deviceID & 0xFF, deviceID >> 8]
        resultData = self._connection.transfer(
            self._BroadcastAddress, self._BroadcastCommandGetDeviceType, sendData, 31)
        return self._bytesToString(resultData)
        
class Module(object) :
    """
    The base class for all Modules. Generally you should not create instances
    of this class directly.
    """

    def __init__(self, port, deviceType, deviceID) :
        if port is None :
            raise ValueError("Cannot create a Module with an invalid port")

        self._port = port
        self._deviceType = deviceType
        self._deviceID = deviceID
        self._address = None

    def transfer(self, command, sendData, receiveLen) :
        return self._port._connection.transfer(self.get_address(), command, sendData, receiveLen)

    def get_address(self) :
        """
        Returns the module's i2c address.
        
        A module's address is an 8 bit number used to identify the device on the i2c bus.
        The address will be assigned automatically when the device is first accessed
        after power up or after a global reset.
        
        Normally you do not need to know a Module's address or do anything with it directly
        """
        
        if self._address is None :
            self._address = self._port._assign_address(self._deviceType, self._deviceID)

        return self._address

    def get_device_id(self) :
        """
        Returns the module's device ID.

        A module's device ID is a 16 bit number that is programmed into the device by
        the manufacturer. It never changes and therefore can be reliably used to distingush
        one module from another, even if they are the same type of module
        """

        return self._deviceID

class Knob(Module) :
    """
    Connect to the module with the specified *deviceID* on the given *port*.
    If *deviceID* isn't specified, finds the first unused KnobModule.
    """

    _FunctionGetButton = 0
    _FunctionGetPosition = 1
    _FunctionAddOffsetPosition = 2
    _FunctionSetColor = 3

    def __init__(self, port, deviceID = None) :
        super(Knob, self).__init__(port, "co.modulo.knob", deviceID)

    def set_color(self, red, green, blue) :
        """Set the color of the knob's LED. *red*, *green*, and *blue* should be
        between 0 and 1"""
        sendData = [r*255,g*255,b*255]
        self.transfer(self._FunctionSetColor, sendData, 0)

    def get_button(self) :
        """Return whether the knob is currently being pressed"""
        receivedData = self.transfer(self._FunctionGetButton, [], 1)
        if receivedData is None :
            return False
        return bool(receivedData[0])

    def get_position(self) :
        """Return the position of the knob in steps. There are 24 steps per revolution"""
        receivedData = self.transfer(self._FunctionGetPosition, [], 2)
        if receivedData is None :
            return 0
        return ctypes.c_short(receivedData[0] | (receivedData[1] << 8)).value

    def get_angle(self) :
        """Return the knob's angle in degrees"""
        return self.get_position()*360/24

class DPad(Module) :
    """
    Connect to the module with the specified *deviceID* on the given *port*.
    If *deviceID* isn't specified, finds the first unused DPadModule.
    """

    _FunctionGetButtons = 0

    def __init__(self, port, deviceID = None) :
        super(DPad, self).__init__(port, "co.modulo.dpad", deviceID)    
    
    def get_button(self, button) :
        """Return whether the specified button is currently being pressed"""
        return bool(self.getButtons() & (1 << button))

    def get_buttons(self) :
        """Return a byte with the state of each button in a different bit"""
        receivedData = self.transfer(self._FunctionGetButtons, [], 1)
        if receivedData is None :
            return 0
        return receivedData[0]

class Thermocouple(Module) :
    """
    Connect to the module with the specified *deviceID* on the given *port*.
    If *deviceID* isn't specified, finds the first unused ThermocoupleModule.
    """

    _FunctionGetTemperature = 0

    InvalidTemperature = -1000

    def __init__(self, port, deviceID = None) :
        super(ThermocoupleModule, self).__init__(port, "co.modulo.thermocouple", deviceID)


    def get_celsius(self) :
        """
        Return the thermocouple temperature in celsius.
        Returns None if no probe is connected
        """

        receivedData = self.transfer(self._FunctionGetTemperature, [], 2)
        if (receivedData is None) :
            return None
        tenths = ctypes.c_short(receivedData[0] | (receivedData[1] << 8)).value
        if (tenths == -10000) : # Check for the invalid temperature sentinal
            return None
        return tenths/10.0

    def get_fahrenheit(self) :
        """
        Return the thermocouple temperature in celsius.
        Returns None if no probe is connected
        """
        tempC = self.getTemperatureC()
        if (tempC is None) :
            return None
        return tempC*1.8 + 32

class Clock(Module) :
    """
    Connect to the module with the specified *deviceID* on the given *port*.
    If *deviceID* isn't specified, finds the first unused ClockModule.
    """

    _FunctionGetTime = 0
    _FunctionSetTime = 1
    _FunctionGetTemperature = 2

    def __init__(self, port, deviceID = None) :
        super(Clock, self).__init__(port, "co.modulo.clock", deviceID)

    def get_datetime(self) :
        """
        Return a datetime object representing the date and time stored
        in the clock module
        """
        receivedData = self.transfer(self._FunctionGetTime, [], 9)
        if (receivedData is None) :
            return None

        if not receivedData[7] : # Check the isSet bit
            return None

        import datetime
        return datetime.datetime(
            receivedData[6] + 2000, # year
            receivedData[5], # month
            receivedData[3], # day
            receivedData[2], # hour
            receivedData[1], # minute
            receivedData[0]) # second

    def set_datetime(self, t = None) :
        """
        Set the module's date and time using the provided datetime, or the current
        date and time if *t* is None
        """

        if t is None :
            import datetime
            t = datetime.datetime.now()

        sendData = [
            t.second,
            t.minute,
            t.hour,
            t.day,
            t.weekday(),
            t.month,
            t.year-2000]
        self.transfer(self._FunctionSetTime, sendData, 0)


    def is_set(self) :
        """
        Return whether the date and time have been set since the last battery failure
        """
        receivedData = self.transfer(self._FunctionGetTime, [], 9)
        if (receivedData is None) :
            return False
        return bool(receivedData[7])

    def is_battery_low(self) :
        """
        Return whether the battery is low
        """
        receivedData = self.transfer(self._FunctionGetTime, [], 9)
        if (receivedData is None) :
            return False
        return bool(receivedData[8])


class Controller(Module) :
    """
    Connect to the Controller module on the given port.

    TODO: Needs additional API for accessing I/O pins.
    """

    def __init__(self, port) :
        super(Controller, self).__init__(port, "co.modulo.controller", deviceID)

    def readTemperatureProbe(self, pin) :
        receivedData = self.transfer(self._FunctionReadTemperatureProbe, [pin], 2)
        return ctypes.c_short(receivedData[0] | (receivedData[1] << 8)).value

class Display(Module) :
    """
    Connect to the module with the specified *deviceID* on the given *port*.
    If *deviceID* isn't specified, finds the first unused MiniDisplayModule.
    """

    SetPixelsFunction = 0

    def __init__(self, port, deviceID = None) :

        super(Display, self).__init__(port, "co.modulo.MiniDisplay", deviceID)

        self._width = 128
        self._height = 64
        self._cursor = (0,0)
        self._currentBuffer = bytearray(self._width*self._height/8)
        self._previousBuffer = bytearray(self._width*self._height/8)

        for i in range(self._width*self._height/8) :
            self._previousBuffer[i] = 0xFF

        from PIL import Image, ImageDraw, ImageFont
        self._font = ImageFont.load_default()
        self._image = Image.new("1", (self._width, self._height))
        self._drawContext = ImageDraw.Draw(self._image)
        self._drawContext.text((0,0), "Hello", fill=1)

    def get_width(self) :
        "The width in pixels of the display"
        return self._width

    def get_height(self) :
        "The height in pixels of the display"
        return self._height

    def set_cursor(self, x, y) :
        self._cursor = (x,y)

    def write(self, obj, color=1) :
        first = True
        for line in str(obj).split("\n") :
            w,h = self._drawContext.textsize(line)
            x,y = self._cursor

            if not first :
                x = 0
                y += h

            self._drawContext.text((x,y), line, fill=color)

            first = False
            self._cursor = (x+w, y)

    def writeln(self, obj, color=1) :
        self.write(str(obj) + "\n", color)

    def clear(self, color=0) :
        "Clear the display, setting all pixels to the specified *color*."
        self.draw_rectangle(0, 0, self._width, self._height, fill=color, outline=None)

    def draw_pixel(self, x, y, color) :
        "Set a single pixel to the specified *color*"
        self._drawContext.point((x,y), color)
    
    def draw_line(self, points, color=1, width=1) :
        """
        Draw lines connecting the specified points (a sequence of (x,y) tuples)
        with the specified *color* and *width*
        """
        self._drawContext.line(points, fill=color, width=width)

    def draw_ellipse(self, x, y, width, height, fill=None, outline=1) :
        """
        Draw an elipse centered at *x*,*y* with given *width* and *height*
        Optionally *fill* and *outline* the elipse with the specified
        """
        self._drawContext.ellipse([x,y,x+width,y+height], fill=fill, outline=outline)

    def draw_arc(self, x, y, w, h, start, end, outline) :
        self._drawContext.arc([x,y,x+w, y+h], start, end, fill=outline)

    def draw_pie_slice(self, x, y, w, h, start, end, fill=None, outline=1) :
        self._drawContext.arc([x,y,x+w, y+h], start, end, fill=fill, outline=outline)

    def draw_rectangle(self, x, y, w, h, fill=None, outline=1) :
        self._drawContext.rectangle([x,y,x+w,y+h],fill=fill, outline=outline)

    def draw_polygon(self, points, fill, outline) :
        self._drawContext.polygon(points, fill=fill, outline=outline)

    def update(self) :
        """Update the display with the current image"""

        # Copy the pixels from the PIL image into the _currentBuffer bytearray
        for x in range(self._width) :
            for y in range(self._height) :
                if self._image.getpixel( (x,y) ) :
                    self._currentBuffer[x+ (y/8)*self._width] |=  (1 << (y&7));
                else :
                    self._currentBuffer[x+ (y/8)*self._width] &=  ~(1 << (y&7));

        for page in range(self._height/8) :
            for x in range(0, self._width, 16) :
                dataToSend = [page, x]

                needsTransfer = False
                for i in range(16) :
                    index = page*self._width + x + i
                    if self._currentBuffer[index] != self._previousBuffer[index] :
                        needsTransfer = True
                    self._previousBuffer[index] = self._currentBuffer[index]
                    dataToSend.append(self._currentBuffer[index])

                if (needsTransfer) :
                    self.transfer(self.SetPixelsFunction, dataToSend, 0)
