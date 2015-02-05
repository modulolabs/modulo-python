#!/usr/bin/python
import os, math
import ctypes, ctypes.util, serial

class Port(object) :

    BroadcastAddress = 9

    BroadcastCommandGlobalReset = 0
    BroadcastCommandGetNextDeviceID = 1
    BroadcastCommandSetAddress = 2
    BroadcastCommandGetAddress = 3
    BroadcastCommandGetDeviceType = 4
    BroadcastCommandGetVersion = 5
    BroadcastCommandGetManufacturer = 6
    BroadcastCommandGetProduct = 7
    BroadcastCommandGetDocURL = 8
    BroadcastCommandGetDocURLContinued = 9
    BroadcastCommandGetInterrupt = 10
    BroadcastCommandSetStatusLED = 11

    StatusOff = 0
    StatusOn = 1
    StatusBlinking = 2
    StatusBreathing = 3

    def __init__(self) :
        self._busInitialized = False
        self._lastAssignedAddress = 9

    def _bytesToString(self, bytes) :
        s = ''
        for b in bytes :
            if b == 0 :
                break
            s = s + chr(b)
        return s
        
    
    # Reset all devices on the bus
    def global_reset(self) :
        self._transfer(self.BroadcastAddress, self.BroadcastCommandGlobalReset, [], 0)

    def assign_address(self, requestedDeviceType, deviceID) :
        # Ensure that a global reset has been performed
        if not self._busInitialized :
            self._busInitialized = True
            self.global_reset()

        # If no deviceID has been specified, find the first
        # device with the specified type
        if deviceID is None :
            deviceID = self.get_next_device_id(0)
            while deviceID is not None :
                deviceType = self.get_device_type(deviceID)
                if deviceType == requestedDeviceType :
                    break
                deviceID = self.get_next_device_id(deviceID+1)

        # No device found. We can't assign an address
        if deviceID is None :
            return None

        self._lastAssignedAddress += 1
        address = self._lastAssignedAddress

        self.set_address(deviceID, address)
        return address


    def set_address(self, deviceID, address) :
        sendData = [deviceID & 0xFF, deviceID >> 8, address]
        self._transfer(self.BroadcastAddress, self.BroadcastCommandSetAddress,
            sendData, 0)
    
    def get_address(self, deviceID) :
        sendData = [deviceID & 0xFF, deviceID >> 8]
        retval = self._transfer(self.BroadcastAddress, self.BroadcastCommandGetAddress,
            sendData, 1)
        if retval is None :
            return None
        return retval[0]

    def get_manufacturer(self, deviceID) :
        sendData = [deviceID & 0xFF, deviceID >> 8]
        resultData = self._transfer(
            self.BroadcastAddress, self.BroadcastCommandGetManufacturer, sendData, 31)
        return self._bytesToString(resultData)
        
    def get_product(self, deviceID) :
        sendData = [deviceID & 0xFF, deviceID >> 8]
        resultData = self._transfer(
            self.BroadcastAddress, self.BroadcastCommandGetProduct, sendData, 31)
        return self._bytesToString(resultData)

    def set_status(self, deviceID, status) :
        sendData = [deviceID & 0xFF, deviceID >> 8, status]
        resultData = self._transfer(
            self.BroadcastAddress, self.BroadcastCommandSetStatusLED, sendData, 0)

    # Returns the device ID of the device on the bus with the
    # next greater ID than the one provided.
    def get_next_device_id(self, lastDeviceID) :
        sendData = [lastDeviceID & 0xFF, lastDeviceID >> 8]
        resultData = self._transfer(
            self.BroadcastAddress, self.BroadcastCommandGetNextDeviceID, sendData, 2)
        if resultData is None :
            return None
        return resultData[1] | (resultData[0] << 8)
    
    def get_version(self, deviceID) :
        sendData = [deviceID & 0xFF, deviceID >> 8]
        retval = self._transfer(self.BroadcastAddress, self.BroadcastCommandGetVersion,
            sendData, 2)
        if retval is None :
            return None
        return retval[0] | (retval[1] << 8)

    def get_device_type(self, deviceID) :
        sendData = [deviceID & 0xFF, deviceID >> 8]
        resultData = self._transfer(
            self.BroadcastAddress, self.BroadcastCommandGetDeviceType, sendData, 31)
        return self._bytesToString(resultData)
        
    def get_motor(self, deviceID=None) :
        return MotorModule(self, deviceID)

    def get_dpad(self, deviceID=None) :
        return DPadModule(self, deviceID)

    def get_clock(self, deviceID=None) :
        return ClockModule(self, deviceID)

    def get_knob(self, deviceID=None) :
        return KnobModule(self, deviceID)

    def get_mini_display(self, deviceID=None) :
        return MiniDisplayModule(self, deviceID)

    def get_io(self, deviceID=None) :
        return IOModule(self, deviceID)

    def get_thermocouple(self, deviceID=None) :
        return ThermocoupleModule(self, deviceID)


class SerialPort(Port) :
    def __init__(self, path=None, controller=0) :
        super(SerialPort, self).__init__()

        if path is None :
            from serial.tools.list_ports import comports
            for port in comports() :
                if (port[1] == 'Modulo Controller') :
                    if (controller == 0) :
                        path = port[0]
                        break
                    controller -= 1

        self._serial = serial.Serial(path, 9600, timeout=5)

    def _transfer(self, address, command, sendData, receiveLen) :
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

class I2CPort(Port) :

    def __init__(self, i2cPath) :
        super(I2CPort, self).__init__()

        self._i2cfd = os.open(i2cPath, os.O_RDWR)
        if self._i2cfd < 0 :
            raise StandardError('Unable to open the i2c device ' + path)

        # This is the ctypes function for transferring data via i2c
        self._dll = ctypes.cdll.LoadLibrary('libmodulo.so')
        self._transferFunction = self._dll.modulo_transfer

    # Wrapper around the modulo_transfer function from the dll
    def _transfer(self, address, command, sendData, receiveLen) :
        if address is None :
            return None

        sendBuffer = ctypes.create_string_buffer(len(sendData))
        for i in range(len(sendData)) :
            sendBuffer[i] = chr(sendData[i])
        receiveBuffer = ctypes.create_string_buffer(receiveLen)

        if (self._transferFunction(self._fd, address, command, sendBuffer, len(sendData),
                               receiveBuffer, receiveLen) < 0) :
            return None

        return [ord(x) for x in receiveBuffer]


class Module(object) :
    def __init__(self, bus, deviceType, deviceID) :
        self._bus = bus
        self._deviceType = deviceType
        self._deviceID = deviceID
        self._address = None

    def _transfer(self, command, sendData, receiveLen) :
        return self._bus._transfer(self.get_address(), command, sendData, receiveLen)

    def get_address(self) :
        if self._address is None :
            self._address = self._bus.assign_address(self._deviceType, self._deviceID)

        return self._address

class MotorModule(Module) :
    
    def __init__(self, bus, deviceID = None) :
        super(self, MotorModule).__init__(bus, "co.modulo.motor", deviceID)


class KnobModule(Module) :

    FunctionGetButton = 0
    FunctionGetPosition = 1
    FunctionAddOffsetPosition = 2
    FunctionSetColor = 3

    def __init__(self, bus, deviceID = None) :
        super(KnobModule, self).__init__(bus, "co.modulo.knob", deviceID)

    def set_color(self, r, g, b) :
        sendData = [r,g,b]
        self._transfer(self.FunctionSetColor, sendData, 0)

    def get_button(self) :
        receivedData = self._transfer(self.FunctionGetButton, [], 1)
        if receivedData is None :
            return False
        return bool(receivedData[0])

    def get_position(self) :
        receivedData = self._transfer(self.FunctionGetPosition, [], 2)
        if receivedData is None :
            return 0
        return ctypes.c_short(receivedData[0] | (receivedData[1] << 8)).value

class DPadModule(Module) :
    FunctionGetButtons = 0

    def __init__(self, bus, deviceID = None) :
        super(DPadModule, self).__init__(bus, "co.modulo.dpad", deviceID)    
    
    def get_button(self, button) :
        return bool(self.getButtons() & (1 << button))

    def get_buttons(self) :
        receivedData = self._transfer(self.FunctionGetButtons, [], 1)
        if receivedData is None :
            return 0
        return receivedData[0]

class ThermocoupleModule(Module) :
    FunctionGetTemperature = 0

    def __init__(self, bus, deviceID = None) :
        super(ThermocoupleModule, self).__init__(bus, "co.modulo.thermocouple", deviceID)

    def get_celsius(self) :
        receivedData = self._transfer(self.FunctionGetTemperature, [], 2)
        if (receivedData is None) :
            return None
        tenths = ctypes.c_short(receivedData[0] | (receivedData[1] << 8)).value
        return tenths/10.0

    def get_fahrenheit(self) :
        tempC = self.getTemperatureC()
        if (tempC is None) :
            return None
        return tempC*1.8 + 32

class ClockModule(Module) :

    FunctionGetTime = 0
    FunctionSetTime = 1
    FunctionGetTemperature = 2

    def __init__(self, bus, deviceID = None) :
        super(ClockModule, self).__init__(bus, "co.modulo.clock", deviceID)

    def get_datetime(self) :
        receivedData = self._transfer(self.FunctionGetTime, [], 9)
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
        self._transfer(self.FunctionSetTime, sendData, 0)


    def is_set(self) :
        receivedData = self._transfer(self.FunctionGetTime, [], 9)
        if (receivedData is None) :
            return False
        return bool(receivedData[7])

    def is_battery_low(self) :
        receivedData = self._transfer(self.FunctionGetTime, [], 9)
        if (receivedData is None) :
            return False
        return bool(receivedData[8])


class MiniDisplayModule(Module) :
    SetPixelsFunction = 0

    def __init__(self, bus, deviceID = None) :
        super(MiniDisplayModule, self).__init__(bus, "co.modulo.MiniDisplay", deviceID)

        self._width = 128
        self._height = 64
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
        return self._width

    def get_height(self) :
        return self._height

    def clear(self, color=0) :
        self.draw_rectangle(0, 0, self._width, self._height, fill=color, outline=None)

    def draw_pixel(self, x, y, color) :
        self._drawContext.point((x,y), color)
    
    def draw_line(self, points, color=1, width=1) :
        self._drawContext.line(points, fill=color, width=width)

    def draw_ellipse(self, x, y, w, h, fill=None, outline=1) :
        self._drawContext.ellipse([x,y,x+w,y+h], fill=fill, outline=outline)

    def draw_arc(self, x, y, w, h, start, end, outline) :
        self._drawContext.arc([x,y,x+w, y+h], start, end, fill=outline)

    def draw_pie_slice(self, x, y, w, h, start, end, fill=None, outline=1) :
        self._drawContext.arc([x,y,x+w, y+h], start, end, fill=fill, outline=outline)

    def draw_rectangle(self, x, y, w, h, fill=None, outline=1) :
        self._drawContext.rectangle([x,y,x+w,y+h],fill=fill, outline=outline)

    def draw_polygon(self, points, fill, outline) :
        self._drawContext.polygon(points, fill=fill, outline=outline)

    def update(self) :
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
                    self._transfer(self.SetPixelsFunction, dataToSend, 0)
