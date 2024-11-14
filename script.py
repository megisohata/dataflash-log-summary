from pymavlink import mavutil

file = 'logs/00000085.BIN'

mavlog = mavutil.mavlink_connection(file, dialect='ardupilotmega', robust_parsing=True)

flying = False
start = 0
end = 0
flights = 0
flightTime = 0

buffer = 1

while True:
    message = mavlog.recv_match()

    if not message:
        break

    messageType = message.get_type()

    if (messageType == 'POS'):
        if (not flying and message.to_dict()['RelHomeAlt'] > buffer):
            flying = True
            flights += 1
            start = message.to_dict()['TimeUS']
        elif (flying and message.to_dict()['RelHomeAlt'] <= buffer):
            flying = False
            end = message.to_dict()['TimeUS']
            flightTime += end - start
            
    print(f"{messageType}: {message.to_dict()}")
    
print('Flights: ' + str(flights))
print('Flight Time: ' + str(flightTime / 10e5) + 's')