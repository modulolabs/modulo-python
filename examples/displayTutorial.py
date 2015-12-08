# Import the modulo python library
import modulo

# Create a new Port object using the first Modulo Controller it finds.
port = modulo.Port()

# Create a Display object attached to the port
display = modulo.Display(port)

# Run this loop until the program is terminated
while True :
    # Call port.loop() on each iteration to process events
    port.loop()

    # Clear the display
    display.clear()

    # Draw text to the display. The color and text depend on which
    # button is pressed.
    if display.getButton(0) :
        display.setTextColor(1,0,0)
        print >>display, "Button 0"
    elif display.getButton(1) :
        display.setTextColor(0,1,0)
        print >>display, "Button 1"
    elif display.getButton(2) :
        display.setTextColor(0,0,1)
        print >>display, "Button 2"
    else :
        display.setTextColor(1,1,1)
        print >>display, "Press Button"

    # Call refresh to update the display
    display.refresh()

