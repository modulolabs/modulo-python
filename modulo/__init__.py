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

            from serial.tools import list_ports

            if path is None :

                # Modulo Controller will contain in the hardware description:
                #    "16d0:a67" on OSX
                #    "16D0:0A67" on Windows 71
                for port in list_ports.grep("16d0:0?a67") :
                    if (controller == 0) :
                        path = port[0]
                        break
                    controller -= 1

            if path is None :
                print(list_ports.comports())
                raise IOError("Couldn't find a Modulo Controller connected via USB")

            self._serial = serial.Serial(path, 9600, timeout=5)
            self._eventData = []

        def transfer(self, address, command, sendData, receiveLen) :
            if address is None :
                return None

            sendBuffer = [ord('S'), address, command, len(sendData)] + sendData + [receiveLen]

            self._serial.write(bytearray(sendBuffer))

            code = self._serial.read(1)
            while (code == 'E') :
                self._eventData.append(self._serial.read(5))
                code = self._serial.read(1)


            retval = ord(self._serial.read(1))
            if retval and receiveLen > 0:
                data = self._serial.read(receiveLen)
                if isinstance(data, str) :
                    return [ord(x) for x in data]
                else :
                    return data
            return None

        def retrieveEventData(self) :
            if (self._serial.inWaiting()) :
                code = self._serial.read(1)
                while (code == 'E') :
                    self._eventData.append(self._serial.read(5))
                    code = self._serial.read(1)
            eventData = self._eventData
            self._eventData = []
            return eventData


        def close(self) :
            self._serial.write('Q')
            self._serial.flush();


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

        import atexit
        atexit.register(self._connection.close)

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
        sendData = [int(red*255), int(green*255), int(blue*255)]
        self.transfer(self._FunctionSetColor, sendData, 0)

    def set_hsv(self, h, s, v) :
        import colorsys
        r,g,b = colorsys.hsv_to_rgb(h,s,v)
        return self.set_color(r,g,b)


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


class Joystick(Module):
    """
    Connect to the module with the specified *deviceID* on the given *port*.
    If *deviceID* isn't specified, finds the first unused KnobModule.
    """ 

    FUNCTION_GET_BUTTON=0
    FUNCTION_GET_POSITION=1

    EVENT_BUTTON_CHANGED=0
    EVENT_POSITION_CHANGED=1

    def __init__(self, port, deviceID = None) :
        super(Joystick, self).__init__(port, "co.modulo.joystick", deviceID)

        self._buttonState = 0
        self._hPos = 128
        self._vPos = 128
        self._buttonPressCallback = None
        self._buttonReleaseCallback = None
        self._positionChangeCallback = None

    def _refreshState(self) :
        self._buttonState = self.transfer(self.FUNCTION_GET_BUTTON, [], 1)[0]

        self._hPos, self._vPos = self.transfer(self.FUNCTION_GET_POSITION, [], 2)
        
    def getButton(self) :
        self._refreshState()
        return self._buttonState

    def getHPos(self) :
        self._refreshState()

        return self._hPos*2.0/255.0 - 1;

    def getVPos(self) :
        self._refreshState()

        return self._vPos*2.0/255.0 - 1;




class DPad(Module) :
    """
    Connect to the module with the specified *deviceID* on the given *port*.
    If *deviceID* isn't specified, finds the first unused DPadModule.
    """

    _FunctionGetButtons = 0

    RIGHT = 0
    UP = 1
    LEFT = 2
    DOWN = 3
    CENTER = 4

    class Buttons(object) :
        def __init__(self, values = 0) :
            self.values = values
            self.right = values & 0b00001
            self.up = values & 0b00010
            self.left = values & 0b00100
            self.down = values & 0b01000
            self.center = values & 0b10000

    def __init__(self, port, deviceID = None) :
        super(DPad, self).__init__(port, "co.modulo.dpad", deviceID)    

    def _get_buttons(self) :
        receivedData = self.transfer(self._FunctionGetButtons, [], 1)
        if receivedData is None :
            return 0
        return receivedData[0]
    
    def get_button(self, button) :
        """Return whether the specified button is currently being pressed"""
        return bool(self._get_buttons() & (1 << button))

    def get_buttons(self) :
        """Return a byte with the state of each button in a different bit"""
        return self.Buttons(self._get_buttons())

class Motor(Module) :

    _FunctionSetValue = 0
    _FunctionGetCurrent = 1
    _FunctionSetEnabled = 2
    _FunctionSetFrequency = 3

    def __init__(self, port, deviceID = None) :
         super(Motor, self).__init__(port, "co.modulo.motor", deviceID)    

    def enable_a(self, enabled=True) :
        "Enable the outputs for motor A (channels 0 and 1)"
        # Channels are enabled in pairs, so enabling 0 also enables 1
        self.transfer(self._FunctionSetEnabled, [0, enabled], 0)

    def enable_b(self, enabled=True) :
        "Enable the outputs for motor B (channels 2 and 3)"
        # Channels are enabled in pairs, so enabling 2 also enables 3
        self.transfer(self._FunctionSetEnabled, [2, enabled], 0)

    def set_channel(self, channel, value) :
        """
        Set the value (between 0 and 1) of the specified channel (0, 1, 2 or 3)."
        The outputs must also be enabled by calling enable_a() or enable_b()
        """
        intValue = int(min(1, max(0, value))*0xFFFF)
        dataToSend = [channel, intValue >> 8, intValue & 0xFF]
        self.transfer(self._FunctionSetValue, dataToSend, 0)

    def set_speed_a(self, value) :
        "Set the speed of Motor A (channels 0 and 1)"
        "The speed must be between -1 and 1"
        if (value > 0) :
            self.set_channel(0, value)
            self.set_channel(1, 0)
        else :
            self.set_channel(0, 0)
            self.set_channel(1, -value)

    def set_speed_b(self, value) :
        "Set the speed of Motor B (channels 2 and 3)"
        "The speed must be between -1 and 1"
        if (value > 0) :
            self.set_channel(2, value)
            self.set_channel(3, 0)
        else :
            self.set_channel(2, 0)
            self.set_channel(3, -value)

class Thermocouple(Module) :
    """
    Connect to the module with the specified *deviceID* on the given *port*.
    If *deviceID* isn't specified, finds the first unused ThermocoupleModule.
    """

    _FunctionGetTemperature = 0

    InvalidTemperature = -1000

    def __init__(self, port, deviceID = None) :
        super(Thermocouple, self).__init__(port, "co.modulo.thermocouple", deviceID)


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
        tempC = self.get_celsius()
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
    _FunctionSetPinDirection = 0
    _FunctionGetDigitalInput = 1
    _FunctionSetDigitalOutput = 2
    _FunctionSetPWMOutput = 3
    _FunctionGetAnalogInput = 4


    def __init__(self, port) :
        super(Controller, self).__init__(port, "co.modulo.controller", None)

    def setPinDirection(self, pin, output, pullup) :
        val = (pin << 2) | (pullup << 1) | output;
        self.transfer(self._FunctionSetPinDirection, [val], 0)

    def getDigitalInput(self, pin) :
        receivedData = self.transfer(self._FunctionGetDigitalInput, [pin], 1)
        return (receivedData[0] != 0)

    def setDigitalOutput(self, pin, value) :
        data = (pin << 1) | value
        self.transfer(self._FunctionSetDigitalOutput, [data], 0)

    def setPWMOutput(self, pin, value) :
        intValue = int(255*max(0, min(1, value)))
        self.transfer(self._FunctionSetPWMOutput, [pin, intValue], 0)

    def getAnalogInput(self, pin) :
        receivedData = self.transfer(self._FunctionGetAnalogInput, [pin], 2)
        return ctypes.c_short(receivedData[0] | (receivedData[1] << 8)).value

    # DEPRECATED
    def readTemperatureProbe(self, pin) :
        receivedData = self.transfer(self._FunctionReadTemperatureProbe, [pin], 2)
        return ctypes.c_short(receivedData[0] | (receivedData[1] << 8)).value




class Display(Module) :
    """
    Connect to the module with the specified *deviceID* on the given *port*.
    If *deviceID* isn't specified, finds the first unused MiniDisplayModule.
    """

    _FUNCTION_APPEND_OP = 0
    _FUNCTION_IS_COMPLETE = 1
    _FUNCTION_GET_BUTTONS = 2

    _OpRefresh = 0
    _OpFillScreen = 1
    _OpDrawLine = 2
    _OpSetLineColor = 3
    _OpSetFillColor = 4
    _OpSetTextColor = 5
    _OpDrawRect = 6
    _OpDrawCircle = 7
    _OpDrawTriangle = 8
    _OpDrawString = 9
    _OpSetCursor = 10
    _OpSetTextSize = 11

    Black = (0,0,0,255)
    White = (255, 255, 255, 255)
    Clear = (0,0,0,0)

    def __init__(self, port, deviceID = None) :

        super(Display, self).__init__(port, "co.modulo.colordisplay", deviceID)

        self._width = 96
        self._height = 64
        self._isRefreshing = False
        self._textSize = 1

    def get_width(self) :
        "The width in pixels of the display"
        return self._width

    def get_height(self) :
        "The height in pixels of the display"
        return self._height

    def write(self, obj, color=1) :
        first = True
        dataToSend = [self._OpDrawString] + list(str(obj)) + [0]
        self.transfer(self._FUNCTION_APPEND_OP, dataToSend, 0)

    def writeln(self, obj, color=1) :
        self.write(str(obj) + "\n", color)

    def clear(self) :
        self.fillScreen(self.Black)
        self.setCursor(0,0)

    def setLineColor(self, color) :
        self._waitOnRefresh()

        sendData = [self._OpSetLineColor, color[0], color[1], color[2], color[3]]
        self.transfer(self._FUNCTION_APPEND_OP, sendData, 0)

    def setFillColor(self, color) :
        self._waitOnRefresh()

        sendData = [self._OpSetFillColor, color[0], color[1], color[2], color[3]]
        self.transfer(self._FUNCTION_APPEND_OP, sendData, 0)

    def setTextColor(self, color) :
        self._waitOnRefresh()

        sendData = [self._OpSetTextColor, color[0], color[1], color[2], color[3]]
        self.transfer(self._FUNCTION_APPEND_OP, sendData, 0)

    def setTextSize(self, size):
        self._waitOnRefresh()

        sendData = [self._OpSetTextSize, size]
        self.transfer(self._FUNCTION_APPEND_OP, sendData, 0)
        self._textSize = size

    def setCursor(self, x, y) :
        self._waitOnRefresh()

        sendData = [self._OpSetCursor, x, y]
        self.transfer(self._FUNCTION_APPEND_OP, sendData, 0)

    def refresh(self):
        self._waitOnRefresh()

        sendData = [self._OpRefresh]
        self.transfer(self._FUNCTION_APPEND_OP, sendData, 0)

        self._isRefreshing = True

    def fillScreen(self, color):
        self._waitOnRefresh()

        sendData = [self._OpFillScreen, color[0], color[1], color[2], color[3]]
        self.transfer(self._FUNCTION_APPEND_OP, sendData, 0)

    def drawLine(self, x0, y0, x1, y1):
        self._waitOnRefresh()

        # XXX: Need to properly clip the line to the display bounding rect
        if (x0 < 0 or x0 >= self.get_width() or
            y0 < 0 or y0 >= self.get_height() or
            x1 < 0 or x1 >= self.get_width() or
            y1 < 0 or y1 >= self.get_height()) :
            return

        sendData = [self._OpDrawLine, x0, y0, x1, y1]
        self.transfer(self._FUNCTION_APPEND_OP, sendData, 0)

    def drawRect(self, x, y, w, h, radius):
        self._waitOnRefresh()

        sendData = [self._OpDrawRect, x, y, w, h, radius]
        self.transfer(self._FUNCTION_APPEND_OP, sendData, 0)

    def _isComplete(self) :
        data = self.transfer(self._FUNCTION_IS_COMPLETE, [], 1)
        if data is None :
            return True
        return data[0]

    def _waitOnRefresh(self) :
        if (self._isRefreshing) :
            self._isRefreshing = False;
            import time
            while not self._isComplete() :
                time.sleep(.01)

    def getButton(self, button) :
        return self.getButtons() & (1 << button);

    def getButtons(self) :
        receivedData = transfer(self._FUNCTION_GET_BUTTONS, [], 1)
        if (receiveData is None) :
            return False

        return receivedData[0]

    def drawSplashScreen(self):
        self.setFillColor((90,0,50));
        self.setLineColor((0,0,0,0));
        self.drawRect(0, 0, WIDTH, HEIGHT);
        self.setCursor(0, 40);

        self.write("     MODULO");

        self.setFillColor((255,255,255));

        self.drawLogo(WIDTH/2-18, 10, 35, 26);
    

    def drawLogo(self, x, y, width, height):
        self.lineWidth = width/7;

        self.drawRect(x, y, width, lineWidth, 1);
        self.drawRect(x, y, lineWidth, height, 1);
        self.drawRect(x+width-lineWidth, y, lineWidth, height, 1);

        self.drawRect(x+lineWidth*2, y+lineWidth*2, lineWidth, height-lineWidth*2, 1);
        self.drawRect(x+lineWidth*4, y+lineWidth*2, lineWidth, height-lineWidth*2, 1);
        self.drawRect(x+lineWidth*2, y+height-lineWidth, lineWidth*3, lineWidth, 1);

