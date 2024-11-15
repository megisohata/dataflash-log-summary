from pymavlink import mavutil
import matplotlib.pyplot as plt

file = 'logs/00000075.BIN'

data = {
    'flight_summary': [],
    'battery_voltage': []
}

flight_summary_types = ['STAT', 'POS', 'MODE']

def parse_log(file):
    mavlog = mavutil.mavlink_connection(file, dialect='ardupilotmega', robust_parsing=True)

    total_messages = 0

    while True:
        message = mavlog.recv_match()

        if not message:
            break
        
        if message.get_type() in flight_summary_types:
            data['flight_summary'].append(message.to_dict())

        if message.get_type() == 'BAT':
            data['battery_voltage'].append(message.to_dict())
        
        total_messages += 1
        print(f'Processing {total_messages} messages...', end='\r')

        # print(f"{message.get_type()}: {message.to_dict()}")
    
    print(f'Finished processing {total_messages} messages.')

def flight_summary(data):
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

    for message in data:
        type = message['mavpackettype']

        if (type == 'STAT'):

            if (not isArmed and message['isFlying'] == 1):
                isArmed = True
            elif (isArmed and message['isFlying'] == 0):
                isArmed = False

        elif (type == 'POS'):
            if (isArmed and not isFlying and message['RelHomeAlt'] > flightAltBuffer):
                isFlying = True
                totalFlights += 1
                flightStart = message['TimeUS']

                if (isAuto):
                    autoFlightStart = message['TimeUS']

            elif (isArmed and isFlying and message['RelHomeAlt'] <= flightAltBuffer):
                isFlying = False
                flightEnd = message['TimeUS']
                totalFlightTime += flightEnd - flightStart

                if (isAuto):
                    autoFlightEnd = message['TimeUS']
                    totalAutoTime += autoFlightEnd - autoFlightStart
        
        elif (type == 'MODE'):
            if (message['Mode'] == 10):
                isAuto = True
                
                if (isFlying):
                    autoFlightStart = message['TimeUS']
            else:
                if (isAuto):
                    isAuto = False

                    if (isFlying):
                        autoFlightEnd = message['TimeUS']
                        totalAutoTime += autoFlightEnd - autoFlightStart

    print('Total Flights: ' + str(totalFlights))
    print('Total Flight Time: ' + str(totalFlightTime / 10e5) + 's')
    print('Auto Flight Time: ' + str(totalAutoTime / 10e5) + 's')
    print('Manual Flight Time: ' + str((totalFlightTime - totalAutoTime) / 10e5) + 's')

def battery_voltage(data):
    batteryVoltageTimes = []
    batteryVoltages = []

    for message in data:
        batteryVoltageTimes.append(message['TimeUS'] / 10e5)
        batteryVoltages.append(message['Volt'])
    
    plt.plot(batteryVoltageTimes, batteryVoltages)
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (V)')
    plt.show()

if __name__ == '__main__':
    print('Parsing log file...')
    parse_log(file)
    flight_summary(data['flight_summary'])

    while True:
        user = input('Enter: ')

        if user == 'exit':
            break
        elif user == 'bat':
            battery_voltage(data['battery_voltage'])
