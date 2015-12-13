from __future__ import print_function

import modulo, sys, time

def _getNameForType(deviceType) :
    if deviceType == "co.modulo.knob":
        return "Knob"
    if deviceType == "co.modulo.blankslate":
        return "Blank Slate"
    if deviceType == "co.modulo.joystick":
        return "Joystick"
    if deviceType == "co.modulo.tempprobe":
        return "Temp Probe"
    if deviceType == "co.modulo.display":
        return "Display"
    if deviceType == "co.modulo.motor":
        return "Motor Driver"
    if deviceType == "co.modulo.ir":
        return "IR Remote"
    return "Unknown"


def list() :
    import modulo, sys, argparse

    parser = argparse.ArgumentParser(description='List connected modulo devices')
    parser.add_argument("-i", "--interactive",action='store_true',
        help="interactively list modulos one at a time, blinking their LEDS to identify them")
    args = parser.parse_args()

    port = modulo.Port()

    deviceID = port._getNextDeviceID(0)
    while deviceID is not None :
        deviceType = port._getDeviceType(deviceID)
        version = port._getVersion(deviceID)
        
        if args.interactive :
            port._setStatus(deviceID,port._StatusBlinking)

        print(_getNameForType(deviceType))
        print("         ID: ", deviceID)
        print("    Version: ", version)

        if args.interactive :
            print()
            print("Press return to continue")
            sys.stdin.readline()
            port._setStatus(deviceID, port._StatusOff)

        deviceID = port._getNextDeviceID(deviceID)


