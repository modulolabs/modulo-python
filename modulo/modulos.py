from __future__ import print_function, division, absolute_import, unicode_literals
import ctypes, ctypes.util
import time

def _clip(x, min, max) :
    if x < min :
        return min
    if x > max :
        return max
    return x

class ModuloBase(object) :
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
        """Disconnect this object from its associated Port"""
        if (self._port) :
            self._port._modulos.remove(self)

    def transfer(self, command, sendData, receiveLen) :
        return self._port._connection.transfer(self.getAddress(), command, sendData, receiveLen)

    def _reset(self) :
        self._address = None

    def _processEvent(self, eventCode, eventData) :
        pass

    def getDeviceID(self) :
        """Return the device ID or None if no modulo was found"""
        self._init()
        return self._deviceID
    
    def setDeviceID(self, deviceID) :
        """Set the ID of the modulo that this object should connect to"""
        if (deviceID != self._deviceID) :
            self._deviceID = deviceID
            self._address = None

    def getAddress(self) :
        """Return the I2C address or None if no modulo was found"""
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
            deviceID = self._port._getNextDeviceID(0)
            while (deviceID is not None) :
                m = self._port._findModuloByID(deviceID)
                
                if m is None :
                    if (self._port._getDeviceType(deviceID) == self._deviceType) :
                        self._deviceID = deviceID
                        break

                deviceID = self._port._getNextDeviceID(deviceID)
        
        if self._deviceID is None :
            return False

        self._address = self._port._getAddress(self._deviceID)
        if (self._address == 0 or self._address == 127) :
            self._port._lastAssignedAddress += 1
            self._address = self._port._lastAssignedAddress
            self._port._setAddress(self._deviceID, self._address)

        return True


class Knob(ModuloBase) :
    """
    Connect to the module with the specified *deviceID* on the given *port*.
    If *deviceID* isn't specified, finds the first unused KnobModule.
    """

    _FunctionGetButton = 0
    _FunctionGetPosition = 1
    _FunctionAddOffsetPosition = 2
    _FunctionSetColor = 3

    _EventButtonChanged = 0
    _EventPositionChanged = 1

    def __init__(self, port, deviceID = None) :
        super(Knob, self).__init__(port, "co.modulo.knob", deviceID)

        self._buttonState = False
        self._position = 0

        self.buttonPressCallback = None
        """ A function that will be called when the knob is pressed.

            The first argument to the function is the knob object that's
            receiving the event. ie::

                def onKnobPressed(knob) :
                   ...
        """

        self.buttonReleaseCallback = None
        """ A function that will be called when the knob is released.

            The first argument to the function is the knob object that's
            receiving the event. ie::

                def onKnobReleased(knob) :
                   ...
        """

        self.positionChangeCallback = None
        """ A function that will be called when the knob's position changes.

            The first argument to the function is the knob object that's
            receiving the event. ie::

                def onKnobTurned(knob) :
                   ...
        """

    def setColor(self, red, green, blue) :
        """Set the color of the knob's LED. *red*, *green*, and *blue* should be
        between 0 and 1"""
        
        sendData = [int(red*255), int(green*255), int(blue*255)]
        self.transfer(self._FunctionSetColor, sendData, 0)

    def setHSV(self, hue, saturation, value) :
        """Set the color of the knob's LED. *hue*, *saturation*, and *value* should be
        between 0 and 1"""
        import colorsys
        r,g,b = colorsys.hsv_to_rgb(hue,saturation,value)
        return self.setColor(r,g,b)

    def getButton(self) :
        """Return whether the knob is currently being pressed"""
        return self._buttonState

    def getAngle(self) :
        """Return the angle of the knob in degrees between 0 and 360."""
        return (self.getPosition() % 24)*360/24.0

    def getPosition(self) :
        """Return the position of the knob in clicks (24 per revolution)."""
        return self._position

    def _init(self) :
        if super(Knob, self)._init() :
            self._refreshState()
            return True
        return False

    def _refreshState(self) :
        receivedData = self.transfer(self._FunctionGetPosition, [], 2)
        if receivedData is not None :
            self._position = ctypes.c_short(receivedData[0] | (receivedData[1] << 8)).value
        
        receivedData = self.transfer(self._FunctionGetButton, [], 1)
        if receivedData is not None :
            self._button = bool(receivedData[0])

    def _processEvent(self, eventCode, eventData) :
        if eventCode == self._EventButtonChanged :
            buttonPressed = bool(eventData & 0x0100)
            buttonReleased = bool(eventData & 0x0001);

            self._buttonState = self._buttonState or buttonPressed
            self._buttonState = self._buttonState and not buttonReleased

            if buttonPressed and self.buttonPressCallback :
                self.buttonPressCallback(self)

            if buttonReleased and self.buttonReleaseCallback :
                self.buttonReleaseCallback(self)
        
        if eventCode == self._EventPositionChanged :
            # Convert from 16 bit unsigned to 16 bit signed
            self._position = ctypes.c_short(eventData).value
            if self.positionChangeCallback :
                self.positionChangeCallback(self)


class Joystick(ModuloBase):
    """
    Connect to the module with the specified *deviceID* on the given *port*.
    If *deviceID* isn't specified, finds the first unused KnobModule.
    """ 

    _FUNCTION_GET_BUTTON=0
    _FUNCTION_GET_POSITION=1

    _EVENT_BUTTON_CHANGED=0
    _EVENT_POSITION_CHANGED=1

    def __init__(self, port, deviceID = None) :
        super(Joystick, self).__init__(port, "co.modulo.joystick", deviceID)

        self._buttonState = 0
        self._hPos = 128
        self._vPos = 128

        self.buttonPressCallback = None
        """ A function that will be called when the joystick is pressed.

            The first argument to the function is the joystick object that's
            receiving the event. ie::

                def onJoystickPressed(joystick) :
                   ...
        """

        self.buttonReleaseCallback = None
        """ A function that will be called when the joystick is released.

            The first argument to the function is the joystick object that's
            receiving the event. ie::

                def onJoystickReleased(joystick) :
                   ...
        """

        self.positionChangeCallback = None
        """ A function that will be called when the joystick position changes.

            The first argument to the function is the joystick object that's
            receiving the event. ie::

                def onJoystickMoved(joystick) :
                   ...
        """

    def getButton(self) :
        """Return wehther the joystick is currently pressed"""
        self._init()
        return self._buttonState

    def getHPos(self) :
        """Return the horizontal position of the joystick. (between -1 and 1)"""
        self._init()
        return 1 - self._hPos*2.0/255.0

    def getVPos(self) :
        """Return the vertical position of the joystick. (between -1 and 1)"""
        self._init()
        return 1 - self._vPos*2.0/255.0

    def _init(self) :
        if super(Joystick, self)._init() :
            self._refreshState()
            return True
        return False

    def _refreshState(self) :
        received = self.transfer(self._FUNCTION_GET_BUTTON, [], 1)
        if received is not None :
            self._buttonState = received[0]

        received = self.transfer(self._FUNCTION_GET_POSITION, [], 2)
        if received :
            self._hPos = received[0]
            self._vPos = received[1]


    def _processEvent(self, eventCode, eventData) :
        if eventCode == self._EVENT_BUTTON_CHANGED :
            buttonPressed = (eventData >> 8)
            buttonReleased = (eventData & 0xFF)

            self._buttonState = self._buttonState or buttonPressed
            self._buttonState = self._buttonState and not buttonReleased

            if self.buttonPressCallback :
                self.buttonPressCallback(self)

            if self.buttonReleaseCallback :
                self.buttonReleaseCallback(self)
        
        if eventCode == self._EVENT_POSITION_CHANGED :
            self._hPos = (eventData >> 8)
            self._vPos = (eventData & 0xFF)
            
            if self.positionChangeCallback :
                self.positionChangeCallback(self)

class TemperatureProbe(ModuloBase) :

    _FunctionGetTemperature = 0
    _EventTemperatuteChanged = 0

    def __init__(self, port, deviceID = None) :
        super(TemperatureProbe, self).__init__(port, "co.modulo.tempprobe", deviceID)
        self.isValid = False
        """ A function that will be called when the probe's temperature changes.

            The first argument to the function is the temperature probe
            that's receiving the event. ie::

                def onTemperatureChanged(temperatureProbe) :
                   ...
        """

        self.temperatureChangeCallback = None
        """Function to be called when the temperature changes"""

        self._temp = 0


    def getTemperatureC(self) :
        """Return the temperature of the probe in celsius"""
        return self._temp/10.0

    def getTemperatureF(self) :
        """Return the temperature of the probe in fahrenheit"""
        return self._temp*1.8/10.0 + 32

    def _init(self) :
        if super(TemperatureProbe, self)._init() :

            received = self.transfer(self._FunctionGetTemperature, [], 2)
            if not received:
                self.isValid = False
                return None
        
            self.isValid = True
            self._temp = ctypes.c_short(received[0] | (received[1] << 8)).value
        
            if self.temperatureChangeCallback :
                self.temperatureChangeCallback(self)

    def _processEvent(self, eventCode, eventData) :
        if eventCode == self._EventTemperatuteChanged :
            self._temp = eventData
            self.isValid = True

            if self.temperatureChangeCallback :
                self.temperatureChangeCallback(self)



class IRRemote(ModuloBase) :
    """
    Infrared remote control transmitter and receiver

    Note: this class can send and receive raw IR data as a sequence of pulse
    lengths, but support for encoding and decoding those pulse lengths into
    useful codes is not quite complete. Full encoding/decoding will be implemented
    soon. Please check community.modulo.co for more information on the status
    of this feature."""

    _FUNCTION_RECEIVE = 0
    _FUNCTION_GET_READ_SIZE = 1
    _FUNCTION_CLEAR_READ = 2
    _FUNCTION_SET_SEND_DATA = 3
    _FUNCTION_SEND = 4
    _FUNCTION_IS_IDLE = 5
    _FUNCTION_SET_BREAK_LENGTH = 6

    _EVENT_RECEIVE = 0

    def __init__(self, port, deviceID = None) :
        super(IRRemote, self).__init__(port, "co.modulo.ir", deviceID)
        
    def setBreakLength(self, l) :
        """Set the no signal time that's required before the receiver considers
            a transmission complete."""
        self.transfer(self._FUNCTION_SET_BREAK_LENGTH, [len & 0xFF, len >> 8])
    
    def _processEvent(self, eventCode, eventData) :
        print('Process Event')
        availBytes = eventData
    
        data = []
        i = 0
        while (i < availBytes) :
            data.append(self.transfer(self._FUNCTION_RECEIVE, [i, 16], 16))
            i += 16

        self.transfer(self._FUNCTION_CLEAR_READ, [], 0)
        
        print('IR DATA:', data)


    def send(self, data) :
        """Send raw data. Each byte is the number of 50us ticks that the output
            should be on or off. The first byte is an off period."""

        print('Send')

        print ('Address is: ', self.getAddress(), self.getDeviceID())
        isIdle = False
        while not isIdle :
            val = self.transfer(self._FUNCTION_IS_IDLE, [], 1)
            print(val)
            if val is None:
                return
            isIdle = val[0]
            if isIdle :
                time.sleep(.005)

        for i in range(len(data), 16) :
            packet = [i] + data[i:i+16]
            if not self.transfer(self._FUNCTION_SET_SEND_DATA, packet, 0) :
                return

        self.transfer(self._FUNCTION_SEND, [len(data)], 0)


class BlankSlate(ModuloBase) :
    _FUNCTION_GET_DIGITAL_INPUT = 0
    _FUNCTION_GET_DIGITAL_INPUTS = 1
    _FUNCTION_GET_ANALOG_INPUT = 2
    _FUNCTION_SET_DATA_DIRECTION = 3
    _FUNCTION_SET_DATA_DIRECTIONS = 4
    _FUNCTION_SET_DIGITAL_OUTPUT = 5
    _FUNCTION_SET_DIGITAL_OUTPUTS = 6
    _FUNCTION_SET_PWM_OUTPUT = 7
    _FUNCTION_SET_PULLUP = 8
    _FUNCTION_SET_PULLUPS = 9
    _FUNCTION_SET_PWM_FREQUENCY = 10

    def __init__(self, port, deviceID = None) :
        super(BlankSlate, self).__init__(port, "co.modulo.blankslate", deviceID)

    def getDigitalInput(self, pin) :
        """Disables the output on the specified pin and returns the pin's value"""
        result = self.transfer(self._FUNCTION_GET_DIGITAL_INPUT, [pin], 1)
        if result is not None :
            return result[0]
    
    def getDigitalInputs(self) :
        """Reads the digital inputs from all 8 pins. Does not enable/disable outputs on any pins."""
        result = self.transfer(self._FUNCTION_GET_DIGITAL_INPUTS, [], 1)
        if result is not None :
            return result[0]
    
    def getAnalogInput(self, pin) :
        """Disables the output on the specified pin and performs an analog read."""
        result = self.transfer(self._FUNCTION_GET_ANALOG_INPUT, [pin, 0], 2)
        if result is not None :
            return (result[0] | (result[1] << 8))/1023.0
    
    def setDirection(self, pin, output) :
        """Sets the pin direction to either output or input"""
        self.transfer(self._FUNCTION_SET_DATA_DIRECTION, [pin, output], 0)
    
    def setDirections(self, outputs) :
        """Sets the pin directions for all 8 pins simultaneously"""
        self.transfer(self._FUNCTION_SET_DATA_DIRECTIONS, [outputs], 0)

    def setDigitalOutput(self, pin, value) :
        """Enables the output and sets the output value on the specified pin."""
        self.transfer(self._FUNCTION_SET_DIGITAL_OUTPUT, [pin, value], 0)

    def setDigitalOutputs(self, values) :
        """Set the digital outputs on all 8 pins. Does not enable or disable outputs on any pins."""
        self.transfer(self._FUNCTION_SET_DIGITAL_OUTPUTS, [values], 0)

    def setPWMValue(self, pin, value) :
        """Enable the output and set the PWM duty cycle on the specified pin.
            Pins 0-4 have hardware PWM support. Pins 5-7 only have software PWM
            which has more jitter, especially at high frequencies."""

        if value >= 1 :
            return self.setDigitalOutput(pin, 1.0)
        if value <= 0 :
            return self.setDigitalOutput(pin, 0.0)

        v = int(65535*value)
        sendData = [pin, v & 0xFF, v >> 8]
    
        self.transfer(self._FUNCTION_SET_PWM_OUTPUT, sendData, 0)

    def setPullup(self, pin, enable) :
        """Sets whether a pullup is enabled on the specified pin."""
        self.transfer(self._FUNCTION_SET_PULLUP, [pin, enable], 0)

    def setPullups(self, values) :
        """Set whether the pullup is enabled on all 8 pins."""
        self.transfer(self._FUNCTION_SET_PULLUPS, [values], 0)

    def setPWMFrequency(self, pin, value) :
        """Set the frequency for PWM signals on the specified pin."""
        sendData = [pin, value & 0xFF, value >> 8]
    
        self.transfer(self._FUNCTION_SET_PWM_FREQUENCY, sendData, 0)


class MotorDriver(ModuloBase) :

    ModeDisabled = 0
    ModeDC = 1
    ModeStepper = 2

    _FunctionSetValue = 0;
    _FunctionSetEnabled = 1;
    _FunctionSetFrequency = 2;
    _FunctionSetCurrentLimit = 3;
    _FunctionSetStepperSpeed = 4;
    _FunctionGetStepperPosition = 5;
    _FunctionSetStepperTarget = 6;
    _FunctionAddStepperOffset = 7;

    _EventPositionReached = 0;
    _EventFaultChanged = 1;

    def __init__(self, port, deviceID = None) :
        super(MotorDriver, self).__init__(port, "co.modulo.motor", deviceID)
    
        self.positionReachedCallback = None
        """ A function that will be called when the stepper target position is
            reached.

            The first argument to the function is the MotorDriver object that's
            receiving the event. ie::

                def onPositionReached(motorDriver) :
                   ...
        """

        self.faultChangedCallback = None
        """ A function that will be called when the fault status changes.

            The first argument to the function is the MotorDriver object that's
            receiving the event. ie::

                def onFaultChanged(motorDriver) :
                   ...
        """
        
        self._fault = False
        self._stepperOffset = 0
        self._usPerStep = 5000
        self._microsteps = 256
        self._minMicrostepDuration = 1000
        
    
    def setChannel(self, channel, amount) :
        """Set a single channel (0-3) to the specified amount, between 0 and 1.
           Changes the mode to ModeDC if it's not already."""
        intValue = int(_clip(amount, 0, 1)*0xFFFF)
        data = [channel, intValue & 0xFF, intValue >> 8]
        self.transfer(self._FunctionSetValue, data, 0)
    
    def _setMotor(self, side, value) :
        """Sets the motor output for a side (A=0,B=2) to a specified value.
           Includes a -1<=x<=1 check on value to prevent silent failure."""
        value = _clip(value, -1, 1)
        if value > 0 :
            self.setChannel(side, 1)
            self.setChannel(side+1, 1-value)
        else :
            self.setChannel(side, 1+value)
            self.setChannel(side+1, 1)
    
    def setMotorA(self, value) :
        """Set the motor output A to the specified amount, between -1 and 1.
           Changes the mode to ModeDC if it's not already."""
        self._setMotor(0, value)

    def setMotorB(self, value) :
        """Set the motor output B to the specified amount, between -1 and 1.
           Changes the mode to ModeDC if it's not already."""
        self._setMotor(2, value)

    def setMode(self, mode) :
        """Set the driver mode to Disabled, DC, or Stepper"""
        self.transfer(self._FunctionSetEnabled, [mode], 0)

    def setCurrentLimit(self, limit) :
        """Set the driver current limit (between 0 and 1)."""
        data = [int(_clip(limit, 0, 1)*63)]
        self.transfer(self._FunctionSetCurrentLimit, data, 0)

    def setPWMFrequency(self, freq) :
        """Set the motor driver PWM frequency"""
        data = [freq & 0xFF, freq >> 8]
        self.transfer(self._FunctionSetFrequency, data, 0)

    def setStepperSpeed(self, stepsPerSecond) :
        """Set the stepper speed in whole steps per second."""
        self.setStepperRate(int(1e6/stepsPerSecond))

    def setStepperRate(self, usPerStep) :
        """Set the number of microseconds to take between each whole step."""
        self._usPerStep = usPerStep
        self._updateStepperSpeed()

    def setStepperResolution(self, microsteps, minMicrostepDuration=1000) :
        """Set the number of microsteps to take between each whole step.
            It can be 1, 2, 4, 8, 16, 32, 64, 128, or 256.
 
            If the duration of a microstep (in microseconds) would be less than
            minMicrostepDuration, then the number of microsteps is decreased
            automatically. This helps to avoid skipping steps when the rate is
            higher than the motor or driver can handle."""

        self._microsteps = microsteps
        self._minMicrostepDuration = minMicrostepDuration
        self._updateStepperSpeed()

    def setStepperTarget(self, targetPos) :
        """Set the stepper target position. The target position is in 1/256 of
            a whole step. (So setting the target to 256 will take as many steps/
            microsteps as are necessary to move to the position that is 1 whole
            step from the starting position."""
        data = [targetPos & 0xFF,
                (targetPos >> 8) & 0xFF,
                (targetPos >> 16) & 0xFF,
                (targetPos >> 24) & 0xFF]            

        self.transfer(self._FunctionSetStepperTarget, data, 0)

    def getStepperPosition(self) :
        """Return the current position of the stepper motor in 1/256 increments
           of wholes steps."""
        receiveData = self.transfer(self._FunctionGetStepperPosition, [], 4)
        pos = 0
        if receiveData is not None :
            for i in [3,2,1,0] :
                pos = (pos << 8)
                pos = pos | receiveData[i]
        return pos

    def hasFault(self) :
        """Return whether a fault condition (such as a short between motor terminals,
           over current shutdown, or over temperature shutdown) is currently present."""
        return self._fault

    def _updateStepperSpeed(self) :
        microsteps = self._microsteps

        if microsteps > 256 :
            microsteps = 256

        while (microsteps > 1 and self._usPerStep/microsteps < self._minMicrostepDuration) :
            microsteps /= 2

        resolution = 0
        i = microsteps/2
        while i > 0 and resolution <= 8 :
            resolution += 1
            i /= 2

        ticksPerMicrostep = _clip(self._usPerStep, 0, 65535)

        sendData = [ticksPerMicrostep & 0xFF, ticksPerMicrostep >> 8, resolution]
        self.transfer(self._FunctionSetStepperSpeed, sendData, 0)

    def _processEvent(self, eventCode, eventData) :
        if eventCode == self._EventPositionReached :
            if self.positionReachedCallback :
                self.positionReachedCallback(self)

        if eventCode == self._EventFaultChanged :
            if eventData & 1 :
                self._fault = True
                if self.faultChangedCallback :
                    self.faultChangedCallback(self)
            if eventData & 2 :
                self._fault = False
                if self.faultChangedCallback :
                    self.faultChangedCallback(self)
    

class Display(ModuloBase) :
    """
    Connect to the module with the specified *deviceID* on the given *port*.
    If *deviceID* isn't specified, finds the first unused MiniDisplayModule.
    """

    _FUNCTION_APPEND_OP = 0
    _FUNCTION_IS_COMPLETE = 1
    _FUNCTION_GET_BUTTONS = 2
    _FUNCTION_RAW_WRITE = 3
    _FUNCTION_IS_EMPTY = 4
    _FUNCTION_GET_AVAILABLE_SPACE = 5
    _FUNCTION_SET_CURRENT = 6
    _FUNCTION_SET_CONTRAST = 7

    _EVENT_BUTTON_CHANGED = 0

    _OpRefresh = 0;
    _OpFillScreen = 1;
    _OpDrawLine = 2;
    _OpSetLineColor = 3;
    _OpSetFillColor = 4;
    _OpSetTextColor = 5;
    _OpDrawRect = 6;
    _OpDrawCircle = 7;
    _OpDrawTriangle = 8;
    _OpDrawString = 9;
    _OpSetCursor = 10;
    _OpSetTextSize = 11;
    _OpClear = 12;

    _OP_BUFFER_SIZE = 28

    def __init__(self, port, deviceID = None) :
        super(Display, self).__init__(port, "co.modulo.display", deviceID)

        self.width = 96
        """The width of the display in pixels"""

        self.height = 64
        """The height of the display in pixels"""

        self.buttonPressCallback = None
        """ A function that will be called when a button is pressed.

            The first argument to the function is the display object that's
            receiving the event. The second argument is the button number (0, 1, or 2) ie::

                def onButtonPressed(display, button) :
                   ...
        """

        self.buttonReleaseCallback = None
        """ A function that will be called when a button is released.

            The first argument to the function is the display object that's
            receiving the event. The second argument is the button number (0, 1, or 2) ie::

                def onButtonReleased(display, button) :
                   ...
        """

        self._currentOp = -1
        self._opBuffer = bytearray(self._OP_BUFFER_SIZE)
        self._opBufferLen = 0
        self._buttonState = 0
        self._isRefreshing = False
        self._availableSpace = 0


    def _sendOp(self, data) :
        while (self._availableSpace < len(data)) :
            receiveData = self.transfer(self._FUNCTION_GET_AVAILABLE_SPACE, [], 2)
            if receiveData :
                self._availableSpace = receiveData[0] | (receiveData[1] << 8)

            if self._availableSpace < len(data) :
                time.sleep(.005)

        self._availableSpace -= len(data)

        self.transfer(self._FUNCTION_APPEND_OP, [int(x) for x in data], 0)

    def _beginOp(self, opCode) :
        if opCode == self._currentOp :
            return

        self._currentOp = opCode
        self._opBufferLen  = 1
        self._opBuffer[0] = opCode

    def _appendToOp(self, data) :
        self._opBuffer[self._opBufferLen] = data
        self._opBufferLen += 1

        if (self._currentOp == self._OpDrawString and
            self._opBufferLen == self._OP_BUFFER_SIZE-1) :
            self._endOp()

    def _endOp(self) :
        if self._currentOp == self._OpDrawString :
    
            self._opBuffer[self._opBufferLen] = 0
            self._opBufferLen += 1
            dataToSend = [x for x in self._opBuffer[:self._opBufferLen]]
            self._sendOp(dataToSend)
            self._opBufferLen = 0
            self._currentOp = -1

    def clear(self) :
        """Fill the screen with black, set the line, fill, and text colors to white,
            and return the cursor to (0,0)"""
        self._endOp()
        self._waitOnRefresh();

        self._sendOp([self._OpClear])

    def setLineColor(self, r, g, b, a=1) :
        """Set the current line color."""
        self._endOp()
        self._waitOnRefresh()

        r,g,b,a = [int(255*_clip(x,0,1)) for x in (r,g,b,a)]

        self._sendOp([self._OpSetLineColor, r, g, b, a])

    def setFillColor(self, r, g, b, a=1) :
        """Set the current fill color"""
        self._endOp()
        self._waitOnRefresh()

        r,g,b,a = [int(255*_clip(x,0,1)) for x in (r,g,b,a)]

        self._sendOp([self._OpSetFillColor, r, g, b, a])

    def setTextColor(self, r, g, b, a=1) :
        """Set the current text color"""
        self._endOp()
        self._waitOnRefresh()

        r,g,b,a = [int(255*_clip(x,0,1)) for x in (r,g,b,a)]

        self._sendOp([self._OpSetTextColor, r, g, b, a])
    
    def setCursor(self, x, y) :
        """Set the cursor position, which is where the next text will be drawn."""
        self._endOp()
        self._waitOnRefresh()
    
        # Convert to 8 bit two's complement representation
        x = ctypes.c_ubyte(int(x)).value
        y = ctypes.c_ubyte(int(y)).value

        self._sendOp([self._OpSetCursor, x, y])

    def refresh(self, flip=False) :
        """Display the results of all previous drawing commands.
           Note that after calling refresh, the next drawing operation will
           block until the frame has been drawn."""
        self._endOp()
        self._waitOnRefresh()

        self._sendOp([self._OpRefresh, flip])
        self._isRefreshing = True
    
    def fillScreen(self, r, g, b) :
        """Fill the screen"""
        self._endOp()
        self._waitOnRefresh()

        r,g,b = [int(255*_clip(x,0,1)) for x in (r,g,b)]

        self._sendOp([self._OpFillScreen, r, g, b, 255])

    def drawLine(self, x0, y0, x1, y1) :
        """Draw a line segment from (x0,y0) to (x1,y1)

           All values must be between -127 and 128.
        """
        self._endOp();
        self._waitOnRefresh();

        # XXX: Need to add proper line clipping implementation

        # Convert to 8 bit two's complement representation
        x0 = ctypes.c_ubyte(int(x0)).value
        y0 = ctypes.c_ubyte(int(y0)).value
        x1 = ctypes.c_ubyte(int(x1)).value
        y1 = ctypes.c_ubyte(int(y1)).value

        self._sendOp([self._OpDrawLine, x0, y0, x1, y1])

    def drawRect(self, x, y, w, h, r=0) :
        """Draw a rectangle with the upper left corner at (x,y) and the
           specified width, height, and corner radius.
        """
        self._endOp()    
        self._waitOnRefresh();

        # Helper function which clips a dimension (pos and length) of a rect
        def _clipRange(x, w, maxWidth) :
            # Clip the left side to -127.
            # To support rounded rects we don't clip to 0
            left = -128
            if (x < left) :
                w += x-left
                x = left
            
            # Return (0, 0) if the rect is offscreen 
            if (w <= 0) or (x >= maxWidth):
                return 0,0

            if w > 255:
                w = 255

            # Convert x to 8 bit two's complement representation
            x = ctypes.c_ubyte(int(x)).value

            return x, int(w)

        x, w = _clipRange(x, w, self.width)
        y, h = _clipRange(y, h, self.height)
        r = int(r)

        self._sendOp([self._OpDrawRect, x, y, w, h, r])

    def drawTriangle(self, x0, y0, x1, y1, x2, y2) :
        """Draw a triangle.

           Values must be between -128 and 127."""
        self._endOp()
        self._waitOnRefresh();
    
        # Convert to 8 bit two's complement representation
        x0 = ctypes.c_ubyte(int(x0)).value
        y0 = ctypes.c_ubyte(int(y0)).value
        x1 = ctypes.c_ubyte(int(x1)).value
        y1 = ctypes.c_ubyte(int(y1)).value
        x2 = ctypes.c_ubyte(int(x2)).value
        y2 = ctypes.c_ubyte(int(y2)).value

        self._sendOp([self._OpDrawTriangle, x0, y0, x1, y1, x2, y2])

    def drawCircle(self, x, y, radius) :
        """ Draw a circle centered at (x,y) with the specified radius.

            x and y must be between -128 and 127.
            radius must be between 0 and 255
        """
        self._endOp()
        self._waitOnRefresh();

        # Convert to 8 bit two's complement representation
        x = ctypes.c_ubyte(int(x)).value
        y = ctypes.c_ubyte(int(y)).value
        radius = int(radius)

        self._sendOp([self._OpDrawCircle, x, y, radius])        

    def write(self, s) :
        """ Write a single charachter c. You can also print to the display with
            print >>display,"Hello Modulo" (Python 2) or
            print("Hello Modulo", file=display) (Python 3)"""
        self._waitOnRefresh();

        if self._currentOp != self._OpDrawString :
            self._endOp()
            self._beginOp(self._OpDrawString)

        for c in s :
            self._appendToOp(ord(c))
        
    def setTextSize(self, size) :
        """Set the text size. This is a multiplier of the base text size,
           which is 8px high."""
        self._endOp()
        self._waitOnRefresh();

        self._sendOp([self._OpSetTextSize, size])

    def isComplete(self) :
        """ Return whether all previous drawing operations have been completed."""
        retval = self.transfer(self._FUNCTION_IS_COMPLETE, [], 1)
        return retval and retval[0]

    def isEmpty(self) :
        """Return whether the queue of drawing operations is empty. If the display
           is still refreshing, it may be empty but not complete."""
        retval = self.transfer(self._FUNCTION_IS_EMPTY, [], 1)
        return retval and bool(retval[0])

    def _waitOnRefresh(self) :
        if self._isRefreshing :
            self._isRefreshing = False
            while not self.isEmpty() :
                time.sleep(.005)


    def getButton(self, button) :
        """Return whether the specified button is currently pressed"""
        return bool(self.getButtons() & (1 << button))

    def getButtons(self) :
        """Return the state of all three buttons, one in each bit."""
        receivedData = self.transfer(self._FUNCTION_GET_BUTTONS, [], 1)
        if (receivedData is None) :
            return False

        return receivedData[0]

    def drawSplashScreen(self):
        """Draw the Modulo logo and the word 'MODULO' on a purple background"""
        self.setFillColor(.27, 0, .24)
        self.setLineColor(0,0,0,0)
        self.drawRect(0, 0, self.width, self.height)
        self.setCursor(0, 40)

        self.setTextColor(1,1,1)
        self.write("     MODULO")

        self.setFillColor(1, 1, 1)

        self.drawLogo(self.width/2-18, 10, 35, 26)
    

    def drawLogo(self, x, y, width, height):
        """Draw the Modulo logo"""
        lineWidth = width/7;

        self.drawRect(x, y, width, lineWidth);
        self.drawRect(x, y, lineWidth, height);
        self.drawRect(x+width-lineWidth, y, lineWidth, height);

        self.drawRect(x+lineWidth*2, y+lineWidth*2, lineWidth, height-lineWidth*2);
        self.drawRect(x+lineWidth*4, y+lineWidth*2, lineWidth, height-lineWidth*2);
        self.drawRect(x+lineWidth*2, y+height-lineWidth, lineWidth*3, lineWidth);

    def setCurrent(self, current) :
        """Set the display's master current. Higher current values produce a
            brighter, more vivid image but may increase image burn-in and audible
            noise from the OLED driver. The default is .75."""
        
        current = int(15*_clip(current,0,1))

        # we must wait until no drawing operations are still in progress.
        while not self.isComplete() :
            import time
            time.sleep(.005)
    
        self.transfer(self._FUNCTION_SET_CURRENT, [current], 0)


    def setContrast(self, r, g, b) :
        """Set the per channel contrast values, which affect image brightness and
           color balance. The default is (.93, 0.555, 1.0)."""

        contrast = [int(255*_clip(r,0,1)),
                    int(255*_clip(g,0,1)),
                    int(255*_clip(b,0,1))]


        # we must wait until no drawing operations are still in progress.
        while not self.isComplete() :
            import time
            time.sleep(.005)
    
        self.transfer(self._FUNCTION_SET_CONTRAST,  contrast, 0)


    def _processEvent(self, eventCode, eventData) :
        if eventCode == self._EVENT_BUTTON_CHANGED :
            buttonPressed = eventData >> 8
            buttonReleased = eventData & 0xFF
    
            self._buttonState |= buttonPressed
            self._buttonState &= buttonReleased

            for i in range(3) :
                if buttonPressed & (1 << i) and self.buttonPressCallback :
                    self.buttonPressCallback(self, i)

                if buttonReleased & (1 << i) and self.buttonReleaseCallback :
                    self.buttonReleaseCallback(self, i)

