from pymavlink import mavutil

file = 'logs/00000075.BIN'

mavlog = mavutil.mavlink_connection(file, dialect='ardupilotmega', robust_parsing=True)

isArmed = False
isFlying = False
isAuto = False

flightStart = 0
flightEnd = 0
autoFlightStart = 0
autoFlightEnd = 0

totalFlights = 0
totalFlightTime = 0
totalAutoTime = 0

flightAltBuffer = 0.1

while True:
    message = mavlog.recv_match()

    if not message:
        break

    messageType = message.get_type()

    if (messageType == 'STAT'):

        if (not isArmed and message.to_dict()['isFlying'] == 1):
            isArmed = True
        elif (isArmed and message.to_dict()['isFlying'] == 0):
            isArmed = False

    elif (messageType == 'POS'):
        if (isArmed and not isFlying and message.to_dict()['RelHomeAlt'] > flightAltBuffer):
            isFlying = True
            totalFlights += 1
            flightStart = message.to_dict()['TimeUS']

            if (isAuto):
                autoFlightStart = message.to_dict()['TimeUS']

        elif (isArmed and isFlying and message.to_dict()['RelHomeAlt'] <= flightAltBuffer):
            isFlying = False
            flightEnd = message.to_dict()['TimeUS']
            totalFlightTime += flightEnd - flightStart

            if (isAuto):
                autoFlightEnd = message.to_dict()['TimeUS']
                totalAutoTime += autoFlightEnd - autoFlightStart
    
    elif (messageType == "MODE"):
        if (message.to_dict()['Mode'] == 10):
            isAuto = True
            
            if (isFlying):
                autoFlightStart = message.to_dict()['TimeUS']
        else:
            if (isAuto):
                isAuto = False

                if (isFlying):
                    autoFlightEnd = message.to_dict()['TimeUS']
                    totalAutoTime += autoFlightEnd - autoFlightStart
            
    # print(f"{messageType}: {message.to_dict()}")
    
print('Total Flights: ' + str(totalFlights))
print('Total Flight Time: ' + str(totalFlightTime / 10e5) + 's')
print('Auto Flight Time: ' + str(totalAutoTime / 10e5) + 's')
print('Manual Flight Time: ' + str((totalFlightTime - totalAutoTime) / 10e5) + 's')