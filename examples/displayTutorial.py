import modulo

port = modulo.Port()
display = modulo.Display(port)

while True :
    port.loop()

    display.clear()
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
    display.refresh()

