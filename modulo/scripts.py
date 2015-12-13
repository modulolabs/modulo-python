import modulo, sys, time


def identify() :
    if len(sys.argv) != 2 or not sys.argv[1].isdigit() :
        print('Specify the ID of a device to identify. For instance, ')
        print('   ',sys.argv[0],"123")
        sys.exit(-1)

    port = modulo.SerialPort()

    requestedDeviceID = int(sys.argv[1])
    found = False

    deviceID = port.get_next_device_id(0)
    while  deviceID is not None :
        if (deviceID == requestedDeviceID) :
            port.set_status(deviceID, port.StatusBlinking)
            found = True
        else :
            port.set_status(deviceID, port.StatusOff)


        deviceID = port.get_next_device_id(deviceID+1)

    if not found :
        print('Could not find device with id', requestedDeviceID)
        sys.exit(-1)

    time.sleep(2)
    port.set_status(requestedDeviceID, port.StatusOff)

def list() :
    import modulo

    port = modulo.SerialPort()

    deviceID = port.get_next_device_id(0)
    while  deviceID is not None :
        print("DeviceID: ", deviceID)
        print("    device type: ", port.get_device_type(deviceID))
        print("    manufactuer: ", port.get_manufacturer(deviceID))
        print("    product:     ", port.get_product(deviceID))
        print("    version:     ", port.get_version(deviceID))
        print("    i2c address: ", port.get_address(deviceID))

        deviceID = port.get_next_device_id(deviceID+1)

