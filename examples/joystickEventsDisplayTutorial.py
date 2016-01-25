# Import the modulo python library
import modulo
import time

CROSSHAIR_COLOR = (0.4, 0.4, 0.4)       # Gray
DOT_COLOR_DESELECTED = (0.4, 0.4, 0.4)  # Gray
DOT_COLOR_SELECTED = (1, 0, 0)          # Red
TEXT_COLOR = (0, 0.7, 0)                # Green

DOT_SIZE_SELECTED = 8
DOT_SIZE_DESELECTED = 4


def draw_crosshairs(x, y, selected):
    # Draw crosshairs
    display.clear()

    display.setLineColor(*CROSSHAIR_COLOR)

    # Horizontal crosshair
    display.drawRect(0, y, display.width, 1)

    # Vertical crosshair
    display.drawRect(x, 0, 1, display.height)

    # Dot
    if selected:
        dot_color = DOT_COLOR_SELECTED
        dot_size = DOT_SIZE_SELECTED
    else:
        dot_color = DOT_COLOR_DESELECTED
        dot_size = DOT_SIZE_DESELECTED
    display.setFillColor(*dot_color)
    display.drawCircle(x, y, dot_size)

    # Coordinate value display
    display.setTextColor(*TEXT_COLOR)
    display.setCursor(0, 0)
    display.write("x=%02d\ny=%02d" % (x, y))

    # Update the display!
    display.refresh()


# Create a new Port object using the first Modulo Controller it finds.
port = modulo.Port()

# Create a Joystick object attached to the port
joystick = modulo.Joystick(port)

# Create a Display object attached to the port
display = modulo.Display(port)

joystick_changed = True

# Screen coords go from 0..width/height-1
max_x = display.width - 1
max_y = display.height - 1

# When we get a notification that the joystick state has changed,
# simply set a variable to let the main loop know.
# We don't update the display within the callback because the
# joystick state notifications can come in at a high rate, and
# if we update the display here then they back up resulting in
# a backlog and laggy display.
def onJoystickChanged(joystick):
    global joystick_changed
    joystick_changed = True

# Register our callback function for both position and button changes
joystick.positionChangeCallback = onJoystickChanged
joystick.buttonPressCallback = onJoystickChanged

while True:
    port.loop()

    # Only update the display when the joystick state has changed
    if joystick_changed:
        joystick_changed = False

        # Scale the joystick position to screen coordinates
        screen_x = int((max_x / 2.0) - ((max_x / 2.0) * joystick.getHPos()))
        screen_y = int((max_y / 2.0) + ((max_y / 2.0) * joystick.getVPos()))

        draw_crosshairs(screen_x, screen_y, joystick.getButton())
