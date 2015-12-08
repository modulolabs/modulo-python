# Import the modulo python library
import modulo

# Create a new Port object using the first Modulo Controller it finds.
port = modulo.Port()

# Create a Knob object attached to the port
knob = modulo.Knob(port)

# Run this loop until the program is terminated
while True :
    # Call port.loop() on each iteration to process events
    port.loop()
    
    # Get the angle of the knob (between 0 and 360)
    angle = knob.getAngle()

    # Divide the angle by 360 to get the hue, which is between 0 and 1
    hue = angle/360.0

    # When the knob is pressed, set the saturation to 0.
    saturation = 1-knob.getButton()

    # Set the color. The value is always 1.0 (full brightness)
    knob.setHSV(hue, saturation, 1.0)
