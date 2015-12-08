import modulo

# This callback function will run whenever the joystick position changes
def onPositionChanged(joystick) :
    hpos = joystick.getHPos()
    vpos = joystick.getVPos()

    motorDriver.setMotorA(vpos + hpos)
    motorDriver.setMotorB(vpos - hpos)

# Create a new Port object using the first Modulo Controller it finds.
port = modulo.Port()

# Create a MotorDriver object attached to the port
motorDriver = modulo.MotorDriver(port)

# Create a Joystick object attached to the port
joystick = modulo.Joystick(port)

# Register our callback function
joystick.positionChangeCallback = onPositionChanged

# Process events until the program is terminated.
port.runForever()


