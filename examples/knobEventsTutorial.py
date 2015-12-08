# Import the modulo python library
import modulo

# This callback function will run whenever the knob position changes
def onPositionChanged(knob) :
    # Get the angle of the knob (between 0 and 360)
    angle = knob.getAngle()

    # Divide the angle by 360 to get the hue, which is between 0 and 1
    hue = angle/360.0

    # When the knob is pressed, set the saturation to 0.
    saturation = 1-knob.getButton()

    # Set the color. The value is always 1.0 (full brightness)
    knob.setHSV(hue, saturation, 1.0)

# Create a new Port object using the first Modulo Controller it finds.
port = modulo.Port()

# Create a Knob object attached to the port
knob = modulo.Knob(port)

# Register our callback function
knob.positionChangeCallback = onPositionChanged

# Process events until the program is terminated.
port.runForever()

