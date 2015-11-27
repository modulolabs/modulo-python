import serial

class Port(object) :
    """
    The Port class represents a physical connection to Modulo devices through a usb or i2c port.
    Once a port has been opened, create a Module object for each device that's connected to the port.

    """

    _BroadcastAddress = 9

    _BroadcastCommandGlobalReset = 0
    _BroadcastCommandGetNextDeviceID = 1
    _BroadcastCommandGetNextUnassignedDeviceID = 2
    _BroadcastCommandSetAddress = 3
    _BroadcastCommandGetAddress = 4
    _BroadcastCommandGetDeviceType = 5
    _BroadcastCommandGetVersion = 6
    _BroadcastCommandGetEvent = 7
    _BroadcastCommandClearEvent = 8
    _BroadcastCommandSetStatusLED = 9

    _BroadcastCommandExitBootloader = 100

    def __init__(self, serialPortPath=None) :
        self._portInitialized = False
        self._lastAssignedAddress = 9
        self._connection = SerialConnection(serialPortPath)
        self._modulos = []

        import atexit
        atexit.register(self._connection.close)

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

    def runForever(self) :
        while True :
            self.loop()

    def loop(self, noWait=False) :
        if noWait :
            if self._connection.inWaiting() == 0:
                return

        receiveData = self._connection.receivePacket()
        if (receiveData == None) :
            return False
        if (receiveData[0] != 'V') :
            self.processOutOfBandPacket(receiveData)
            return False

        print receiveData

        event = [ord(x) for x in receiveData[1:]]
        #event = self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandGetEvent, [], 5)
        #if event is None or len(event) == 0:
    #        break
        #self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandClearEvent, event, 0)

    
        eventCode = event[0]
        deviceID = event[1] | (event[2] << 8)
        eventData = event[3] | (event[4] << 8)

        print event
        
        m = self.findModuloByID(deviceID)
        if m :
            print event
            gotEvent = True
            m._processEvent(eventCode, eventData)

        return True

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


class SerialConnection(object) :
    Delimeter = 0x7E
    Escape = 0x7D

    def __init__(self, path=None, controller=0) :
        super(SerialConnection, self).__init__()

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
        print 'Sending', data
        self._serial.write(chr(self.Delimeter))
        for x in data :
            if x == self.Delimeter or x == self.Escape :
                self._serial.write(chr(self.Escape))
                self._serial.write(chr(x ^ (1 << 5)))
            else :
                self._serial.write(chr(x))
        self._serial.write(chr(self.Delimeter))
        

    def receivePacket(self) :
        c = self._serial.read()
        if (c == '') :
            return None
        while (c != chr(self.Delimeter) and c != '') :
            print 'Skipping before delimeter: ', c
            c = self._serial.read()

        while (c == chr(self.Delimeter)) :
            c = self._serial.read()

        data = []
        while (c != chr(self.Delimeter) and c != '') :
            if (c == chr(self.Escape)) :
                c = chr(ord(self._serial.read()) ^ (1 << 5))
            data.append(c)
            c = self._serial.read()

        print 'Received', data
        return data

    def inWaiting(self) :
        return self._serial.inWaiting()

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