import modulo

port = modulo.Port()
motorDriver = modulo.MotorDriver(port)
joystick = modulo.Joystick(port)

while True :
    port.loop()

    hpos = joystick.getHPos()
    vpos = joystick.getVPos()

    motorDriver.setMotorA(vpos + hpos)
    motorDriver.setMotorB(vpos - hpos)

