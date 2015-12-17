from __future__ import print_function, division, absolute_import, unicode_literals
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

    _CodeEvent = ord('V')
    _CodeEcho = ord('X')

    _StatusOff = 0
    _StatusOn = 1
    _StatusBlinking = 2

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

    def _findModuloByID(self, id) :
        """Find the modulo object with the specified deviceID"""
        for m in self._modulos :
            if (m._deviceID == id) :
                return m
        return None

    def runForever(self) :
        """Continue to process events forever"""
        while True :
            self.loop()

    def loop(self, noWait=False) :
        """Call loop as often as possible to handle events and execute callbacks"""
        for m in self._modulos :
            m.getAddress()

        gotPacket = False
        packet = self._connection.getNextPacket(noWait)
        while packet :
            gotPacket = True
            if (packet[0] == self._CodeEvent) :
                event = packet[1:]

                eventCode = event[0]
                deviceID = event[1] | (event[2] << 8)
                eventData = event[3] | (event[4] << 8)

                
                m = self._findModuloByID(deviceID)
                if m :
                    m._processEvent(eventCode, eventData)
            elif (packet[0] != self._CodeEcho) :
                # Discard echo packet if it's received out of band
                # No other type of packet should be received.
                print('Invalid out of band packet: ', packet)

            # Never wait when checking to see if there are additional packets
            packet = self._connection.getNextPacket(noWait=True)

        return gotPacket

    def _globalReset(self) :
        """Reset all modulos to their initial state"""
        self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandGlobalReset, [], 0)

        for m in modulos :
            m._reset()

    def _exitBootloader(self) :
        """Tell all modulos to exit their bootloader and begin normal operation"""
        self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandExitBootloader, [], 0)


    def _getNextDeviceID(self, lastDeviceID) :
        """Find the smallest deviceID that's greater than the one provided.
           This can be used to iterate over all connected modulos."""
        if lastDeviceID == 0xFFFF :
            return 0xFFFF
        
        nextDeviceID = lastDeviceID+1

        sendData = [nextDeviceID & 0xFF, nextDeviceID >> 8]
        resultData = self._connection.transfer(
            self._BroadcastAddress, self._BroadcastCommandGetNextDeviceID, sendData, 2)
        if resultData:
            return resultData[1] | (resultData[0] << 8)

    def _getNextUnassignedDeviceID(self, lastDeviceID) :
        """Like getNextDeviceID, but only returns IDs of modulos that don't have
            an assigned address."""
        if lastDeviceID == 0xFFFF :
            return 0xFFFF
        
        nextDeviceID = lastDeviceID+1

        sendData = [nextDeviceID & 0xFF, nextDeviceID >> 8]
        resultData = self._connection.transfer(
            self._BroadcastAddress, self._BroadcastCommandGetNextUnassignedDeviceID, sendData, 2)
        if resultData :
            resultData[1] | (resultData[0] << 8)

    def _setAddress(self, deviceID, address) :
        """Set the I2C address of the modulo with the specified ID"""
        sendData = [deviceID & 0xFF, deviceID >> 8, address]
        self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandSetAddress,
            sendData, 0)
    
    def _getAddress(self, deviceID) :
        """Get the I2C address of the modulo with the specified ID"""
        sendData = [deviceID & 0xFF, deviceID >> 8]
        retval = self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandGetAddress,
            sendData, 1)
        if retval :
            return retval[0]

    def _setStatus(self, deviceID, status) :
        """Set the status LED of the modulo with the specified ID to either On,
           Off, or Blinking"""
        sendData = [deviceID & 0xFF, deviceID >> 8, status]
        self._connection.transfer(
            self._BroadcastAddress, self._BroadcastCommandSetStatusLED, sendData, 0)

    def _getVersion(self, deviceID) :
        """Get the firmware version of the modulo with the specified ID"""
        sendData = [deviceID & 0xFF, deviceID >> 8]
        retval = self._connection.transfer(self._BroadcastAddress, self._BroadcastCommandGetVersion,
            sendData, 2)
        if not retval :
            return None
        return retval[0] | (retval[1] << 8)

    def _getDeviceType(self, deviceID) :
        """Get the device type string of the modulo with the specified ID"""
        sendData = [deviceID & 0xFF, deviceID >> 8]
        resultData = self._connection.transfer(
            self._BroadcastAddress, self._BroadcastCommandGetDeviceType, sendData, 31)
        return self._bytesToString(resultData)


class SerialConnection(object) :
    _Delimeter = 0x7E
    _Escape = 0x7D

    _CodeEcho = ord('X')
    _CodeTransfer = ord('T')
    _CodeReceive = ord('R')
    _CodeQuit = ord('Q')

    def __init__(self, path=None, controller=0) :
        super(SerialConnection, self).__init__()

        if path is None :
            from serial.tools import list_ports

            # Modulo Controller will contain in the hardware description:
            #    "16d0:a67" on OSX
            #    "16D0:0A67" on Windows 71
            for port in self._grepPorts("16d0:0?b58") :
                if (controller == 0) :
                    path = port[0]
                    break
                controller -= 1

        if path is None :
            print(list_ports.comports())
            raise IOError("Couldn't find a Modulo Controller connected via USB")

        self._serial = serial.Serial(path, timeout=.1)
        self._outOfBandPackets = []

        # The arduino samd usb serial implementation seems to swallow some
        # initial data when the connection is being set up. To work around this,
        # send pings until we get a response. After that the connection will be
        # reliable.
        while not self.getNextPacket() :
            self.sendPacket([self._CodeEcho])

    def _grepPorts(self, regexp) :
        """This is a copy of serial.list_ports.grep that has been modified to
           work around an error that occurs on OSX 10.10.5, where the desc
           field is None which causes the grep to fail"""
        import re
        from serial.tools import list_ports
        r = re.compile(regexp, re.I)
        for port, desc, hwid in list_ports.comports() :
            if r.search(hwid) :
                yield port, desc, hwid

    def sendPacket(self, data) :
    
        packet = []
        for x in data :
            if x == self._Delimeter or x == self._Escape :
                packet.append(self._Escape)
                packet.append(x ^ (1 << 5))
            else :
                packet.append(x)

        self._serial.write([self._Delimeter] + packet + [self._Delimeter])
        
    def transfer(self, address, command, sendData, receiveLen) :
        if address is None :
            return None

        sendBuffer = [self._CodeTransfer, address, command, len(sendData),
            receiveLen] + sendData

        self.sendPacket(sendBuffer)

        # Receive packets and queue them in the out of band packet list until
        # we receive a response packet.
        receiveData = self._receivePacket()
        while (receiveData != None and receiveData[0] != self._CodeReceive) :
            self._outOfBandPackets.append(receiveData)
            receiveData = self._receivePacket()

        if receiveData is None :
            return None

        return receiveData[2:]

    def getNextPacket(self, noWait=False) :
        if noWait and (not self._outOfBandPackets) and (self._serial.inWaiting() == 0):
            return None

        if self._outOfBandPackets :
            p = self._outOfBandPackets[0]
            self._outOfBandPackets = self._outOfBandPackets[1:]
            return p
        else :
            return self._receivePacket()

    def close(self) :
        self.sendPacket([self._CodeQuit])
        self._serial.flush();

    def _readByte(self) :
        c = self._serial.read()
        if c:
            return ord(c)

    def _receivePacket(self) :
        c = self._readByte()
        if (c is None) :
            return None

        while (c != self._Delimeter and c is not None) :
            c = self._readByte()

        while (c == self._Delimeter) :
            c = self._readByte()

        data = []
        while (c != self._Delimeter and c is not None) :
            if (c == self._Escape) :
                c = self._readByte() ^ (1 << 5)
            data.append(c)
            c = self._readByte()

        return data
