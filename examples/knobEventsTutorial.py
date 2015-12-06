import modulo

def onPositionChanged(knob) :
    
    angle = knob.getAngle()
    hue = angle/360.0
    saturation = 1-knob.getButton()

    knob.setHSV(hue, saturation, 1.0)

port = modulo.Port()
knob = modulo.Knob(port)
knob.positionChangeCallback = onPositionChanged

port.runForever()

