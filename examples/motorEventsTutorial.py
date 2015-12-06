import modulo


def onPositionChanged(joystick) :
    hpos = joystick.getHPos()
    vpos = joystick.getVPos()

    motorDriver.setMotorA(vpos + hpos)
    motorDriver.setMotorB(vpos - hpos)


port = modulo.Port()
motorDriver = modulo.MotorDriver(port)
joystick = modulo.Joystick(port)

joystick.positionChangeCallback = onPositionChanged

port.runForever()


