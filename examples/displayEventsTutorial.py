# Import the modulo python library
import modulo

# This callback function will run any time a button is pressed
def onButtonPressed(display, button) :
    # First, clear the display
    display.clear()

    # Draw text to the display. The color and text depend on which
    # button was pressed.
    if button == 0:
        display.setTextColor(1,0,0)
        print >>display, "Button 0"
    elif button == 1 :
        display.setTextColor(0,1,0)
        print >>display, "Button 1"
    elif button == 2:
        display.setTextColor(0,0,1)
        print >>display, "Button 2"

    # Call refresh to update the display
    display.refresh()

# This callback function will run any time a button is pressed
def onButtonReleased(display, button):
    # First, clear the display
    display.clear()

    # Draw the text "Press Button" in white
    display.setTextColor(1,1,1)
    print >>display, "Press Button"

    # Call refresh to update the display
    display.refresh()

# Create a new Port object using the first Modulo Controller it finds.
port = modulo.Port()

# Create a Display object attached to the port
display = modulo.Display(port)

# Register our callback functions
display.buttonPressCallback = onButtonPressed
display.buttonReleaseCallback = onButtonReleased

# Execute the onButtonReleased function to update the display
onButtonReleased(display, 0)

# Process events until the program is terminated.
port.runForever()



    




