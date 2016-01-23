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

# Variables to store previously displayed
# values, to avoid unnecessary redraws
last_screen_x = 0
last_screen_y = 0
last_button_pressed = False

# Screen coords go from 0..width/height-1
max_x = display.width - 1
max_y = display.height - 1

while True:
    # Wait for any previous drawing to complete
    while not display.isComplete():
        time.sleep(0.05)

    # Let the port do its processing
    port.loop()

    # Read the joystick position
    jx = joystick.getHPos()
    jy = joystick.getVPos()
    button_pressed = joystick.getButton()

    # Scale the joystick position to screen coordinates
    screen_x = int((max_x / 2.0) - ((max_x / 2.0) * jx))
    screen_y = int((max_y / 2.0) + ((max_y / 2.0) * jy))

    # Only redraw the crosshairs if something has changed
    # since last time
    if ((screen_x != last_screen_x) or
        (screen_y != last_screen_y) or
            (button_pressed != last_button_pressed)):
        draw_crosshairs(screen_x, screen_y, button_pressed)

        last_screen_x = screen_x
        last_screen_y = screen_y
        last_button_pressed = button_pressed
