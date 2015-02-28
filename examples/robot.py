import modulo, time

port = modulo.Port()
dpad = modulo.DPad(port)
display = modulo.Display(port)
motor = modulo.Motor(port)

motor.enable_a(True)
motor.enable_b(True)

while True :
    buttons = dpad.get_buttons()
    
    if buttons.up :
        if buttons.left : # Forward Left
            motor.set_speed_a(0)
            motor.set_speed_b(1)
        elif buttons.right : # Forward Right
            motor.set_speed_a(1)
            motor.set_speed_b(0)
        else : # Forward
            motor.set_speed_a(1)
            motor.set_speed_b(1)
    elif buttons.down :
        if buttons.left : # Back Left
            motor.set_speed_a(-1)
            motor.set_speed_b(0)
        elif buttons.right : # Back Right
            motor.set_speed_a(0)
            motor.set_speed_b(-1)
        else : # Back
            motor.set_speed_a(-1)
            motor.set_speed_b(-1)
    elif buttons.left : # Hard Left
        motor.set_speed_a(-1)
        motor.set_speed_b(1)
    elif buttons.right : # Hard Right
        motor.set_speed_a(1)
        motor.set_speed_b(-1)
    else : # Stop
        motor.set_speed_a(0)
        motor.set_speed_b(0)



