import ctypes, ctypes.util
import numpy

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

                deviceID = self._port.getNextDeviceID(deviceID)
        
        if self._deviceID is None :
            return False

        self._address = self._port.getAddress(self._deviceID)
        if (self._address == 0) :
            self._port._lastAssignedAddress += 1
            self._address = self._port._lastAssignedAddress
            self._port.setAddress(self._deviceID, self._address)

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
        self.buttonReleaseCallback = None
        self.positionChangeCallback = None

    def setColor(self, red, green, blue) :
        """Set the color of the knob's LED. *red*, *green*, and *blue* should be
        between 0 and 1"""
        
        sendData = [int(red*255), int(green*255), int(blue*255)]
        self.transfer(self._FunctionSetColor, sendData, 0)

    def setHSV(self, h, s, v) :
        import colorsys
        r,g,b = colorsys.hsv_to_rgb(h,s,v)
        return self.setColor(r,g,b)

    def getButton(self) :
        """Return whether the knob is currently being pressed"""
        return self._buttonState

    def getAngle(self) :
        return (self.getPosition() % 24)*360/24.0

    def getPosition(self) :
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
                self._buttonPressCallback(self)

            if buttonReleased and self.buttonReleaseCallback :
                self.buttonReleaseCallback(self)
        
        if eventCode == self._EventPositionChanged :
            # Convert from 16 bit unsigned to 16 bit signed
            self._position = ctypes.c_short(eventData).value
            print self._position
            if self.positionChangeCallback :
                self.positionChangeCallback(self)


class Joystick(ModuloBase):
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
        self.buttonPressCallback = None
        self.buttonReleaseCallback = None
        self.positionChangeCallback = None

    def getButton(self) :
        self._init()
        return self._buttonState

    def getHPos(self) :
        self._init()

        return 1 - self._hPos*2.0/255.0

    def getVPos(self) :
        self._init()

        return 1 - self._vPos*2.0/255.0

    def _init(self) :
        if super(Joystick, self)._init() :
            self._refreshState()
            return True
        return False

    def _refreshState(self) :
        received = self.transfer(self.FUNCTION_GET_BUTTON, [], 1)
        if received is not None :
            self._buttonState = received[0]

        received = self.transfer(self.FUNCTION_GET_POSITION, [], 2)
        # XXX: This may not be working
        if received is not None and len(received) == 2 :
            self._hPos = received[0]
            self._vPos = received[1]

    def _processEvent(self, eventCode, eventData) :
        if eventCode == self.EVENT_BUTTON_CHANGED :
            buttonPressed = (eventData >> 8)
            buttonReleased = (eventData & 0xFF)

            self._buttonState = self._buttonState or buttonPressed
            self._buttonState = self._buttonState and not buttonReleased

            if self.buttonPressCallback :
                self.buttonPressCallback(self)

            if self.buttonReleaseCallback :
                self.buttonReleaseCallback(self)
        
        if eventCode == self.EVENT_POSITION_CHANGED :
            self._hPos = (eventData >> 8)
            self._vPos = (eventData & 0xFF)
            
            if self.positionChangeCallback :
                self.positionChangeCallback(self)

def TemperatureProbe(ModuloBase) :

    _FunctionGetTemperature = 0

    def __init__(self, port, deviceID = None) :
        super(TemperatureProbe, self).__init__(port, "co.modulo.tempprobe", deviceID)

    def getTemperatureC(self) :
        received = self.transfer(self._FunctionGetTemperature, [], 2)
        if received is None :
            return None

        t = ctypes.c_short(received[0] | (received[1] << 8)).value
        return t/10.0

    def getTemperatureF(self) :
        t = self.getTemperatureC()
        if t is None :
            return None

        return t*1.8 + 32

def BlankSlate(ModuloBase) :
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
        super(BlankSlate, self).__init__(port, "co.modulo.io", deviceID)

    def getDigitalInput(self, pin) :
        result = self.transfer(self._FUNCTION_GET_DIGITAL_INPUT, [pin], 1)
        if result is not None :
            return result[0]
    
    def getDigitalInputs(self) :
        result = self.transfer(self._FUNCTION_GET_DIGITAL_INPUTS, [], 1)
        if result is not None :
            return result[0]
    
    def getAnalogInput(self, pin) :
        result = self.transfer(self._FUNCTION_GET_ANALOG_INPUT, [pin], 2)
        if result is not None :
            return (result[0] | (result[1] << 8))/1023.0
    
    def setDirection(self, pin, output) :
        self.transfer(self._FUNCTION_SET_DATA_DIRECTION, [pin, output], 0)
    
    def setDirections(self, outputs) :
        self.transfer(self._FUNCTION_SET_DATA_DIRECTIONS, [outputs], 0)

    def setDigitialOutput(self, pin, value) :
        self.transfer(self._FUNCTION_SET_DIGITAL_OUTPUTS, [pin, value], 0)

    def setDigitalOutputs(self, values) :
        self.transfer(self._FUNCTION_SET_DATA_DIRECTIONS, [values], 0)

    def setPWMValue(self, pin, value) :
        if value >= 1 :
            return self.setDigitalOutput(pin, 1.0)
        if value <= 0 :
            return self.setDigitalOutput(pin, 0.0)

        v = 65535*value
        sendData = [pin, v & 0xFF, v >> 8]
    
        self.transfer(self._FUNCTION_SET_PWM_OUTPUT, sendData, 0)

    def setPullup(self, pin, enable) :
        self.transfer(self._FUNCTION_SET_PULLUP, [pin, enable], 0)

    def setPullups(self, values) :
        self.transfer(self._FUNCTION_SET_PULLUPS, [values], 0)

    def setPWMFrequency(self, pin, value) :
        sendData = [pin, value & 0xFF, value >> 8]
    
        self.transfer(self._FUNCTION_SET_PWM_FREQUENCY, sendData, 0)


class Motor(ModuloBase) :

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
        super(BlankSlate, self).__init__(port, "co.modulo.motor", deviceID)
    
        self.positionReachedCallback = None
        self.faultChangedCallback = None
        
        self._fault = False
        self._stepperOffset = 0
        self._usPerStep = 5000
        self._microsteps = 256
        self._minMicrostepDuration = 1000
        
    
    def setChannel(self, channel, amount) :
        intValue = numpy.clip(amount, 0, 1)*0xFFFF
        data = [channel, intValue & 0xFF, intValue >> 8]
        self.transfer(self._FunctionSetValue, data, 0)

    def setMotorA(self, amount) :
        if amount > 0 :
            self.setChannel(0, 1)
            self.setChannel(1, 1-value)
        else :
            self.setChanenl(0, 1+value)
            self.setChannel(1, 1)

    def setMotorB(self, amount) :
        if amount > 0 :
            self.setChannel(2, 1)
            self.setChannel(3, 1-value)
        else :
            self.setChanenl(2, 1+value)
            self.setChannel(3, 1)


    def setMode(self, mode) :
        self.transfer(self._FunctionSetEnabled, [mode], 0)

    def setCurrentLimit(self, limit) :
        data = [numpy.clip(limit, 0, 1)*63]
        self.transfer(self.FunctionSetCurrrentLimit, data, 0)

    def setPWMFrequency(self, freq) :
        data = [frequency * 0xFF, frequency >> 8]
        self.transfer(self.FunctionSetPWMFrequency, data, 0)

    def setStepperSpeed(self, stepsPerSecond) :
        self._setStepperRate(1e6/stepsPerSecond)

    def setStepperRate(self, usPerStep) :
        self._usPerStep = usPerStep
        self._updateStepperSpeed()

    def setStepperResolution(self, microsteps, minMicrostepDuration=1000) :
        self._microsteps = microsteps
        self._minMicrostepDuration = minMicrostepDuration
        self._updateStepperSpeed()

    def setStepperTarget(self, targetPos) :
        data = [targetPos & 0xFF,
                (targetPos >> 8) & 0xFF,
                (targetPos >> 16) & 0xFF,
                (targetPos >> 24) & 0xFF]            

        self.transfer(self._FunctionSetStepperTarget, data, 0)

    def getStepperPosition(self) :
        receiveData = self.transfer(self._FunctionGetStepperPosition, [], 4)
        pos = 0
        if receiveData is not None :
            for i in [3,2,1,0] :
                pos = (pos << 8)
                pos = pos | receiveData[i]
        return pos

    def hasFault(self) :
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

        ticksPerMicrostep = numpy.clip(self._usPerStep, 0, 65535)

        sendData = [ticksPerMicrostep & 0xFF, ticksPerMicrostep >> 8, resolution]
        self._transfer(self._FunctionSetStepperSpeed, sendData)

    def _processEvent(self, eventCode, eventData) :
        if eventCode == self._EventPositionReached :
            if self.positionReachedCallback :
                self.positionReachedCallback(self)

        if eventCode == self._EventFaultChanged :
            if eventData & 1 :
                self._fault = True
            if eventData & 2 :
                self._fault = False
            if self.faultChangedCallback :
                self.faultChanedCallback(self)
    



class Controller(ModuloBase) :
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




class Display(ModuloBase) :
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

