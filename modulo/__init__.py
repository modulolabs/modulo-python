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
    _BroadcastCommandGetEvent = 6
    _BroadcastCommandSetStatusLED = 7
    _BroadcastCommandSetStatusLED = 8
    _BroadcastCommandExitBootloader = 100

    class _SerialConnection(object) :
        Delimeter = 0x7E
        Escape = 0x7D


        def __init__(self, path=None, controller=0) :
            super(Port._SerialConnection, self).__init__()

            from serial.tools import list_ports

            if path is None :

                # Modulo Controller will contain in the hardware description:
                #    "16d0:a67" on OSX
                #    "16D0:0A67" on Windows 71
                for port in list_ports.grep("16d0:0?b58") :
                    if (controller == 0) :
                        path = port[0]
                        break
                    controller -= 1

            if path is None :
                print(list_ports.comports())
                raise IOError("Couldn't find a Modulo Controller connected via USB")

            self._serial = serial.Serial(path, timeout=.1)
            self._eventData = []

            while not self.receivePacket() :
                self.sendPacket([ord('X')])
                pass

        def sendPacket(self, data) :
            self._serial.write(chr(self.Delimeter))
            for x in data :
                self._serial.write(chr(x))
            self._serial.write(chr(self.Delimeter))
            

        def receivePacket(self) :
            c = self._serial.read()
            if (c == '') :
                print 'Read error'
                return None
            while (c != chr(self.Delimeter) and c != '') :
                print 'Skipping before delimeter: ', c
                c = self._serial.read()

            while (c == chr(self.Delimeter)) :
                c = self._serial.read()

            data = []
            while (c != chr(self.Delimeter) and c != '') :
                if (c == chr(self.Escape)) :
                    c = self._serial.read() ^ (1 << 5)
                data.append(c)
                c = self._serial.read()

            return data

        def transfer(self, address, command, sendData, receiveLen) :
            if address is None :
                return None

            sendBuffer = [ord('T'), address, command, len(sendData), receiveLen] + sendData

            self.sendPacket(sendBuffer)

            receiveData = self.receivePacket()
            while (receiveData != None and receiveData[0] != 'R') :
                self.processOutOfBandPacket(receiveData)
                receiveData = self.receivePacket()

            if receiveData is None :
                return None

            receiveData = [ord(x) for x in receiveData]
            return receiveData[2:]


        def processOutOfBandPacket(self, data) :
            if (data[0] == 'D') :
                print('Debug: ' + "".join(data[1:]))
            else :
                print('Out of band: ', data)

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
            self.sendPacket([ord('Q')])
            self._serial.flush();

    def __init__(self, serialPortPath=None) :
        self._portInitialized = False
        self._lastAssignedAddress = 9
        self._connection = self._SerialConnection(serialPortPath)
        self._modulos = []

        #import atexit
        #atexit.register(self._connection.close)

    def _bytesToString(self, bytes) :
        s = ''
        for b in bytes :
            if b == 0 :
                break
            s = s + chr(b)
        return s


    def findModuloByID(self, id) :
        for m in self._modulos :
            if (m._deviceID == id) :
                return m
        return None

    def loop() :
        while True :
            event = self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandGetEvent, [], 5)
            if event is None :
                break
            self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandClearEvent, event, 0)

            eventCode = event[0]
            deviceID = event[1] | (event[2] << 8)
            eventData = event[3] | (event[4] << 8)
            
            m = self.findModuloByID(deviceID)
            if m :
                m._processEvent(eventCode, eventData)


    # Reset all devices on the port
    def globalReset(self) :
        self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandGlobalReset, [], 0)

        for m in modulos :
            m._reset()

    def exitBootloader(self) :
        self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandExitBootloader, [], 0)

    # Returns the device ID of the device on the port with the
    # next greater ID than the one provided.
    def getNextDeviceID(self, lastDeviceID) :
        if lastDeviceID == 0xFFFF :
            return 0xFFFF
        
        nextDeviceID = lastDeviceID+1

        sendData = [nextDeviceID & 0xFF, nextDeviceID >> 8]
        resultData = self._connection.transfer(
            self._BroadcastAddress, self._BroadcastCommandGetNextDeviceID, sendData, 2)
        if resultData is None or len(resultData) < 2:
            return None
        return resultData[1] | (resultData[0] << 8)


    def setAddress(self, deviceID, address) :
        sendData = [deviceID & 0xFF, deviceID >> 8, address]
        self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandSetAddress,
            sendData, 0)
    
    def getAddress(self, deviceID) :
        sendData = [deviceID & 0xFF, deviceID >> 8]
        retval = self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandGetAddress,
            sendData, 1)
        if retval is None :
            return None
        return retval[0]

    def setStatus(self, deviceID, status) :
        sendData = [deviceID & 0xFF, deviceID >> 8, status]
        resultData = self._connection.transfer(
            self._BroadcastAddress, self._BroadcastCommandSetStatusLED, sendData, 0)

    def getVersion(self, deviceID) :
        sendData = [deviceID & 0xFF, deviceID >> 8]
        retval = self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandGetVersion,
            sendData, 2)
        if retval is None :
            return None
        return retval[0] | (retval[1] << 8)

    def getDeviceType(self, deviceID) :
        sendData = [deviceID & 0xFF, deviceID >> 8]
        resultData = self._connection.transfer(
            self._BroadcastAddress, self._BroadcastCommandGetDeviceType, sendData, 31)
        return self._bytesToString(resultData)

    # def _assign_address(self, requestedDeviceType, deviceID) :
    #     # Ensure that a global reset has been performed
    #     if not self._portInitialized :
    #         self._portInitialized = True
    #         self._global_reset()

    #     # If no deviceID has been specified, find the first
    #     # device with the specified type
    #     if deviceID is None :
    #         deviceID = self._get_next_device_id(0)
    #         while deviceID is not None :
    #             deviceType = self._get_device_type(deviceID)
    #             if deviceType == requestedDeviceType :
    #                 break
    #             deviceID = self._get_next_device_id(deviceID+1)

    #     # No device found. We can't assign an address
    #     if deviceID is None :
    #         return None

    #     self._lastAssignedAddress += 1
    #     address = self._lastAssignedAddress

    #     self._set_address(deviceID, address)
    #     return address



        
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
        
        self._port._modulos.append(self)

    def __del__(self) :
        self.close()

    def close(self) :
        if (self._port) :
            self._port._modulos.remove(self)
            

    def transfer(self, command, sendData, receiveLen) :
        return self._port._connection.transfer(self.getAddress(), command, sendData, receiveLen)

    def _reset(self) :
        self._address = None

    def _processEvent(self, eventCode, eventData) :
        pass

    def getDeviceID(self) :
        self._init()
        return self._deviceID
    
    def setDeviceID(self, deviceID) :
        if (deviceID != self._deviceID) :
            self._deviceID = deviceID
            self._address = None

    def getAddress(self) :
        self._init()
        return self._address

    def _loop(self) :
        if self._disconnected :
            if self.getAddress() != None :
                self._disconnected = False
    
    def _init(self) :
        if self._address is not None :
            return False

        if self._deviceID is None:
            deviceID = self._port.getNextDeviceID(0)
            while (deviceID is not None) :
                m = self._port.findModuloByID(deviceID)
                
                if m is None :
                    if (self._port.getDeviceType(deviceID) == self._deviceType) :
                        self._deviceID = deviceID
                        break
        
        if self._deviceID is None :
            return False

        self._address = self._port.getAddress(self._deviceID)
        if (self._address == 0) :
            self._port._lastAssignedAddress += 1
            self._address = self._port._lastAssignedAddress
            self._port.setAddress(self._deviceID, self._address)

        return True


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

