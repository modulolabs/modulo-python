# Import the modulo python library
import modulo

# Create a new Port object using the first Modulo Controller it finds.
port = modulo.Port()

# Create a MotorDriver object attached to the port
motorDriver = modulo.MotorDriver(port)

# Create a Joystick object attached to the port
joystick = modulo.Joystick(port)

# Run this loop until the program is terminated
while True :
    # Call port.loop() on each iteration to process events
    port.loop()

    # Get the horizontal and vertical position of the joystick
    # These values will be between -1 and 1
    hpos = joystick.getHPos()
    vpos = joystick.getVPos()

    # Set the speed of the left and right motors
    motorDriver.setMotorA(vpos + hpos)
    motorDriver.setMotorB(vpos - hpos)

