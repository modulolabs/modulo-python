import ctypes, ctypes.util
import numpy, time

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
        if (self._address == 0 or self._address == 127) :
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
        self._temp = 0
        self.temperatureChangeCallback = None

    def getTemperatureC(self) :
        return self._temp/10.0

    def getTemperatureF(self) :
        return self._temp*1.8/10.0 + 32

    def _init(self) :
        if super(TemperatureProbe, self)._init() :

            received = self.transfer(self._FunctionGetTemperature, [], 2)
            if not received:
                self._isValid = False
                return None
        
            self._isValid = True
            self._temp = ctypes.c_short(received[0] | (received[1] << 8)).value
        
            if self.temperatureChangeCallback :
                self.temperatureChangeCallback(self)

    def _processEvent(self, eventCode, eventData) :
        if eventCode == self._EventTemperatuteChanged :
            self._temp = eventData
            self._isValid = True

            if self.temperatureChangeCallback :
                self.temperatureChangeCallback(self)



class IRRemote(ModuloBase) :

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
        self.transfer(self._FUNCTION_SET_BREAK_LENGTH, [len & 0xFF, len >> 8])
    
    
    def _processEvent(self, eventCode, eventData) :
        print 'Process Event'
        availBytes = eventData
    
        data = []
        i = 0
        while (i < availBytes) :
            data.append(self.transfer(self._FUNCTION_RECEIVE, [i, 16], 16))
            i += 16

        self.transfer(self._FUNCTION_CLEAR_READ, [], 0)
        
        print 'IR DATA:', data


    def send(self, data) :
        print 'Send'

        print 'Address is: ', self.getAddress(), self.getDeviceID()
        isIdle = False
        while not isIdle :
            val = self.transfer(self._FUNCTION_IS_IDLE, [], 1)
            print val
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
        result = self.transfer(self._FUNCTION_GET_DIGITAL_INPUT, [pin], 1)
        if result is not None :
            return result[0]
    
    def getDigitalInputs(self) :
        result = self.transfer(self._FUNCTION_GET_DIGITAL_INPUTS, [], 1)
        if result is not None :
            return result[0]
    
    def getAnalogInput(self, pin) :
        result = self.transfer(self._FUNCTION_GET_ANALOG_INPUT, [pin, 0], 2)
        if result is not None :
            return (result[0] | (result[1] << 8))/1023.0
    
    def setDirection(self, pin, output) :
        self.transfer(self._FUNCTION_SET_DATA_DIRECTION, [pin, output], 0)
    
    def setDirections(self, outputs) :
        self.transfer(self._FUNCTION_SET_DATA_DIRECTIONS, [outputs], 0)

    def setDigitalOutput(self, pin, value) :
        self.transfer(self._FUNCTION_SET_DIGITAL_OUTPUT, [pin, value], 0)

    def setDigitalOutputs(self, values) :
        self.transfer(self._FUNCTION_SET_DIGITAL_OUTPUTS, [values], 0)

    def setPWMValue(self, pin, value) :
        if value >= 1 :
            return self.setDigitalOutput(pin, 1.0)
        if value <= 0 :
            return self.setDigitalOutput(pin, 0.0)

        v = int(65535*value)
        sendData = [pin, v & 0xFF, v >> 8]
    
        self.transfer(self._FUNCTION_SET_PWM_OUTPUT, sendData, 0)

    def setPullup(self, pin, enable) :
        self.transfer(self._FUNCTION_SET_PULLUP, [pin, enable], 0)

    def setPullups(self, values) :
        self.transfer(self._FUNCTION_SET_PULLUPS, [values], 0)

    def setPWMFrequency(self, pin, value) :
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
        self.faultChangedCallback = None
        
        self._fault = False
        self._stepperOffset = 0
        self._usPerStep = 5000
        self._microsteps = 256
        self._minMicrostepDuration = 1000
        
    
    def setChannel(self, channel, amount) :
        intValue = int(numpy.clip(amount, 0, 1)*0xFFFF)
        data = [channel, intValue & 0xFF, intValue >> 8]
        self.transfer(self._FunctionSetValue, data, 0)

    def setMotorA(self, value) :
        if value > 0 :
            self.setChannel(0, 1)
            self.setChannel(1, 1-value)
        else :
            self.setChannel(0, 1+value)
            self.setChannel(1, 1)

    def setMotorB(self, value) :
        if value > 0 :
            self.setChannel(2, 1)
            self.setChannel(3, 1-value)
        else :
            self.setChannel(2, 1+value)
            self.setChannel(3, 1)

    def setMode(self, mode) :
        self.transfer(self._FunctionSetEnabled, [mode], 0)

    def setCurrentLimit(self, limit) :
        data = [int(numpy.clip(limit, 0, 1)*63)]
        self.transfer(self._FunctionSetCurrentLimit, data, 0)

    def setPWMFrequency(self, freq) :
        data = [freq & 0xFF, freq >> 8]
        self.transfer(self._FunctionSetFrequency, data, 0)

    def setStepperSpeed(self, stepsPerSecond) :
        self.setStepperRate(int(1e6/stepsPerSecond))

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

        self._width = 96
        self._height = 64
        self._currentOp = -1
        self._opBuffer = bytearray(self._OP_BUFFER_SIZE)
        self._opBufferLen = 0
        self._buttonState = 0
        self._isRefreshing = False
        self._availableSpace = 0
        self.buttonPressCallback = None
        self.buttonReleaseCallback = None

    def _sendOp(self, data) :
        while (self._availableSpace < len(data)) :
            receiveData = self.transfer(self._FUNCTION_GET_AVAILABLE_SPACE, [], 2)
            if receiveData :
                self._availableSpace = receiveData[0] | (receiveData[1] << 8)

            if self._availableSpace < len(data) :
                time.sleep(.005)

        self._availableSpace -= len(data)

        self.transfer(self._FUNCTION_APPEND_OP, data, 0)

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
        self._endOp()
        self._waitOnRefresh();

        self._sendOp([self._OpClear])

    def setLineColor(self, r, g, b, a=1) :
        self._endOp()
        self._waitOnRefresh()

        self._sendOp([self._OpSetLineColor, int(r*255), int(g*255), int(b*255), int(a*255)])

    def setFillColor(self, r, g, b, a=1) :
        self._endOp()
        self._waitOnRefresh()

        self._sendOp([self._OpSetFillColor, int(r*255), int(g*255), int(b*255), int(a*255)])

    def setTextColor(self, r, g, b, a=1) :
        self._endOp()
        self._waitOnRefresh()

        self._sendOp([self._OpSetTextColor, int(r*255), int(g*255), int(b*255), int(a*255)])
    
    def setCursor(self, x, y) :
        self._endOp()
        self._waitOnRefresh()
    
        self._sendOp([self._OpSetCursor, x, y])

    def refresh(self, flip=False) :
        self._endOp()
        self._waitOnRefresh()

        self._sendOp([self._OpRefresh, flip])
        self._isRefreshing = True
    
    def fillScreen(self, r, g, b) :
        self._endOp()
        self._waitOnRefresh()

        self._sendOp([self._OpFillScreen, int(255*r), int(255*g), int(255*b), 255])

    def drawLine(self, x0, y0, x1, y1) :
        self._endOp();
        self._waitOnRefresh();

        ## XXX: _clipLine(&x0, &y0, &x1, &y1);

        self._sendOp([self._OpDrawLine, x0, y0, x1, y1])

    def drawRect(self, x, y, w, h, r=0) :
        self._endOp()    
        self._waitOnRefresh();

        # XXX: clip

        self._sendOp([self._OpDrawRect, x, y, w, h, r])

    def drawTriangele(self, x0, y0, x1, y1, x2, y2) :
        self._endOp()
        self._waitOnRefresh();

        self._sendOp([self._OpDrawTriangle, x0, y0, x1, y1, x2, y2])

    def drawCircle(self, x, y, radius) :
        self._endOp()
        self._waitOnRefresh();

        self._sendOp([self._OpDrawCircle, x, y, radius])        

    def write(self, s) :
        self._waitOnRefresh();

        if self._currentOp != self._OpDrawString :
            self._endOp()
            self._beginOp(self._OpDrawString)

        for c in s :
            self._appendToOp(c)
        
    def setTextSize(self, size) :
        self._endOp()
        self._waitOnRefresh();

        self._sendOp([self._OpSetTextSize, size])

    def isComplete(self) :
        retVal = self.transfer(self._FUNCTION_IS_COMPLETE, [], 1)
        return retval is not None and retval[0]

    def isComplete(self) :
        retVal = self.transfer(self._FUNCTION_IS_EMPTY, [], 1)
        return retval is not None and retval[0]

    def _waitOnRefresh(self) :
        if self._isRefreshing :
            self._isRefreshing = False
            while self.isEmpty() :
                time.sleep(.005)

    def width(self) :
        "The width in pixels of the display"
        return self._width

    def height(self) :
        "The height in pixels of the display"
        return self._height


    def getButton(self, button) :
        return bool(self.getButtons() & (1 << button))

    def getButtons(self) :
        receivedData = self.transfer(self._FUNCTION_GET_BUTTONS, [], 1)
        if (receivedData is None) :
            return False

        return receivedData[0]

    def drawSplashScreen(self):
        self.setFillColor(.27, 0, .24)
        self.setLineColor(0,0,0,0)
        self.drawRect(0, 0, self._width, self._height)
        self.setCursor(0, 40)

        self.setTextColor(1,1,1)
        self.write("     MODULO")

        self.setFillColor(1, 1, 1)

        self.drawLogo(self.width()/2-18, 10, 35, 26)
    

    def drawLogo(self, x, y, width, height):
        lineWidth = width/7;

        self.drawRect(x, y, width, lineWidth);
        self.drawRect(x, y, lineWidth, height);
        self.drawRect(x+width-lineWidth, y, lineWidth, height);

        self.drawRect(x+lineWidth*2, y+lineWidth*2, lineWidth, height-lineWidth*2);
        self.drawRect(x+lineWidth*4, y+lineWidth*2, lineWidth, height-lineWidth*2);
        self.drawRect(x+lineWidth*2, y+height-lineWidth, lineWidth*3, lineWidth);

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

