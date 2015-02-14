import modulo, time

port = modulo.Port()
knob = modulo.Knob(port)
display = modulo.Display(port)

while True :
    display.clear()
    display.set_cursor(0,0)
    display.writeln(knob.get_angle())
    display.update()
    time.sleep(.05)