from pymavlink import mavutil

file = 'logs/00000085.BIN'

mavlog = mavutil.mavlink_connection(file, dialect='ardupilotmega', robust_parsing=True)

armed = False
flying = False

start = 0
end = 0

flights = 0
flightTime = 0

buffer = 0.1

while True:
    message = mavlog.recv_match()

    if not message:
        break

    messageType = message.get_type()

    if (messageType == 'STAT'):
        isFlying = message.to_dict()['isFlying']

        if (not armed and isFlying == 1):
            armed = True
        elif (armed and isFlying == 0):
            armed = False

    elif (messageType == 'POS'):
        if (armed and not flying and message.to_dict()['RelHomeAlt'] > buffer):
            flying = True
            flights += 1
            start = message.to_dict()['TimeUS']
        elif (armed and flying and message.to_dict()['RelHomeAlt'] <= buffer):
            flying = False
            end = message.to_dict()['TimeUS']
            flightTime += end - start
            
    print(f"{messageType}: {message.to_dict()}")
    
print('Flights: ' + str(flights))
print('Flight Time: ' + str(flightTime / 10e5) + 's')