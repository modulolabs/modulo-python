import modulo

port = modulo.Port()
knob = modulo.Knob(port)

while True :
    port.loop()
    
    angle = knob.getAngle()
    hue = angle/360.0
    saturation = 1-knob.getButton()

    knob.setHSV(hue, saturation, 1.0)
