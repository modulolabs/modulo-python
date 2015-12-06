import modulo

def onButtonPressed(display, button) :
    display.clear()
    if button == 0:
        display.setTextColor(1,0,0)
        print >>display, "Button 0"
    elif button == 1 :
        display.setTextColor(0,1,0)
        print >>display, "Button 1"
    elif button == 2:
        display.setTextColor(0,0,1)
        print >>display, "Button 2"
    display.refresh()

def onButtonReleased(display, button):
    display.clear()
    display.setTextColor(1,1,1)
    print >>display, "Press Button"
    display.refresh()

port = modulo.Port()
display = modulo.Display(port)
display.buttonPressCallback = onButtonPressed
display.buttonReleaseCallback = onButtonReleased

onButtonReleased(display, 0)

port.runForever()



    




