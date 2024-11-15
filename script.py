from pymavlink import mavutil
import matplotlib.pyplot as plt

file = 'logs/00000085.BIN'

data = {
    'all': [],
    'flight_summary': [],
    'battery_voltage': [],
    'flights': []
}

flight_summary_types = { 'STAT', 'POS', 'MODE' }

def parse_log(file):
    mavlog = mavutil.mavlink_connection(file, dialect='ardupilotmega', robust_parsing=True)

    total_messages = 0

    while True:
        message = mavlog.recv_match()

        if not message:
            break

        message = message.to_dict()
        
        data['all'].append(message)

        if message['mavpackettype'] in flight_summary_types:
            data['flight_summary'].append(message)

        if message['mavpackettype'] == 'BAT':
            data['battery_voltage'].append(message)
        
        total_messages += 1
        print(f'Processing {total_messages} messages...', end='\r')

        # print(f'{message['mavpackettype']}: {message}')
    
    print(f'Finished processing {total_messages} messages.')

def flight_summary(messages):
    is_armed = False
    is_flying = False
    is_auto_mode = False
    is_auto_flight = False

    flight_start = 0
    flight_end = 0
    auto_flight_start = 0
    auto_flight_end = 0

    total_flights = 0
    total_flight_time = 0
    total_auto_flights = 0
    total_auto_time = 0

    flight_alt_buffer = 0.1

    for message in messages:
        type = message['mavpackettype']

        if (type == 'STAT'):

            if (not is_armed and message['isFlying'] == 1):
                is_armed = True
            elif (is_armed and message['isFlying'] == 0):
                is_armed = False

        elif (type == 'POS'):
            if (is_armed and not is_flying and message['RelHomeAlt'] > flight_alt_buffer):
                is_flying = True
                total_flights += 1
                flight_start = message['TimeUS']
                data['flights'].append(flight_start)

                if is_auto_mode:
                    auto_flight_start = message['TimeUS']

                    if not is_auto_flight:
                        is_auto_flight = True
                        total_auto_flights += 1

            elif (is_armed and is_flying and message['RelHomeAlt'] <= flight_alt_buffer):
                is_flying = False
                flight_end = message['TimeUS']
                data['flights'].append(flight_end)
                total_flight_time += flight_end - flight_start

                if (is_auto_mode):
                    auto_flight_end = message['TimeUS']
                    total_auto_time += auto_flight_end - auto_flight_start

                    if is_auto_flight:
                        is_auto_flight = False
        
        elif (type == 'MODE'):
            if (message['Mode'] == 10):
                is_auto_mode = True
                
                if (is_flying):
                    auto_flight_start = message['TimeUS']

                    if not is_auto_flight:
                        is_auto_flight = True
                        total_auto_flights += 1
            else:
                if (is_auto_mode):
                    is_auto_mode = False

                    if (is_flying):
                        auto_flight_end = message['TimeUS']
                        total_auto_time += auto_flight_end - auto_flight_start

                        if is_auto_flight:
                            is_auto_flight = False

    print('Key flight data (for DesOps):\n' + 
          '\tTotal Flights: ' + str(total_flights) + '\n' + 
          '\tTotal Auto Flights: ' + str(total_auto_flights) + '\n' + 
          '\tTotal Flight Time: ' + str(total_flight_time / 10e5) + 's' + '\n' + 
          '\tAuto Flight Time: ' + str(total_auto_time / 10e5) + 's' + '\n' +
          '\tManual Flight Time: ' + str((total_flight_time - total_auto_time) / 10e5) + 's')

def print_all(messages):
    for message in messages:
        print(message)

def battery_voltage(messages):
    batter_voltage_times = []
    batter_voltages = []

    for message in messages:
        batter_voltage_times.append(message['TimeUS'] / 10e5)
        batter_voltages.append(message['Volt'])
    
    plt.plot(batter_voltage_times, batter_voltages)
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (V)')
    plt.show()

if __name__ == '__main__':
    print('Parsing log file...')
    parse_log(file)
    flight_summary(data['flight_summary'])

    while True:
        user = input('Enter a command: ')

        if user == 'exit':
            break
        elif user == 'help':
            print('Available commands:')
        elif user == 'all':
            print_all(data['all'])
        elif user == 'bat':
            battery_voltage(data['battery_voltage'])
        else:
            print('Please enter a valid command. For a list of all commands, enter [help].')
