from pymavlink import mavutil
import matplotlib.pyplot as plt
import numpy as np

file = 'logs/00000084.BIN'

data = {
    'flight_summary': [],
    'battery_voltage': [],
    'flights_timestamps': []
}

flight_summary_types = { 'STAT', 'MODE', 'MSG' } # message types used for flight summary data
vertical_modes = { 17, 18, 19, 20, 21, 22, 23 } # vertical flight modes

def parse_log(file):
    mavlog = mavutil.mavlink_connection(file, dialect='ardupilotmega', robust_parsing=True)

    total_messages = 0

    while True:
        message = mavlog.recv_match()

        if not message:
            break

        message = message.to_dict()

        if message['mavpackettype'] in flight_summary_types:
            data['flight_summary'].append(message)

        if message['mavpackettype'] == 'BAT':
            data['battery_voltage'].append(message)
        
        total_messages += 1
        print(f'Processing {total_messages} messages...', end='\r')

        print(f"{message['mavpackettype']}: {message}")
    
    print(f'Finished processing {total_messages} messages.')

def flight_summary(messages):
    is_flying = False
    is_auto_mode = False
    is_auto_flight = False
    is_vertical_mode = False

    flight_start = 0
    flight_end = 0
    auto_flight_start = 0
    auto_flight_end = 0
    vertical_flight_start = 0
    vertical_flight_end = 0

    total_flights = 0
    total_flight_time = 0
    total_auto_flights = 0
    total_auto_time = 0
    total_vertical_flight_time = 0

    for message in messages:
        if message['mavpackettype'] == 'STAT':
            if not is_flying and message['isFlyProb'] >= 0.8:
                is_flying = True
                total_flights += 1
                flight_start = message['TimeUS']
                data['flights_timestamps'].append(flight_start)

                if is_auto_mode: # start auto timer if in auto mode
                    auto_flight_start = message['TimeUS']

                    if not is_auto_flight: # classify as auto flight if not already so
                        is_auto_flight = True
                        total_auto_flights += 1
                
                if is_vertical_mode:
                    vertical_flight_start = message['TimeUS']
            elif is_flying and message['isFlyProb'] < 0.8:
                is_flying = False
                flight_end = message['TimeUS']
                total_flight_time += flight_end - flight_start

                flight_end = message['TimeUS']
                data['flights_timestamps'].append(flight_end)

                if is_auto_mode: # end auto timer if in auto mode
                    auto_flight_end = message['TimeUS']
                    total_auto_time += auto_flight_end - auto_flight_start

                    if is_auto_flight:
                        is_auto_flight = False
                
                if is_vertical_mode: # end vertical timer if in vertical mode
                    vertical_flight_end = message['TimeUS']
                    total_vertical_flight_time += vertical_flight_end - vertical_flight_start
        elif message['mavpackettype'] == 'MODE':
            if message['Mode'] == 10: # auto mode
                is_auto_mode = True
                
                if is_flying: # start auto timer if flying
                    auto_flight_start = message['TimeUS']

                    if not is_auto_flight: # classify as auto flight if not already so
                        is_auto_flight = True
                        total_auto_flights += 1

                if is_vertical_mode:
                    vertical_flight_end = message['TimeUS']
                    total_vertical_flight_time += vertical_flight_end - vertical_flight_start
            elif not is_vertical_mode and message['Mode'] in vertical_modes:
                is_vertical_mode = True

                if is_flying: # start vertical timer if flying
                    vertical_flight_start = message['TimeUS']
            elif message['Mode'] != 10 and message['Mode'] not in vertical_modes:
                if is_auto_mode:
                    is_auto_mode = False

                    if is_flying:
                        auto_flight_end = message['TimeUS']
                        total_auto_time += auto_flight_end - auto_flight_start

                        if is_auto_flight:
                            is_auto_flight = False

                if is_vertical_mode:
                    is_vertical_mode = False

                    if is_flying:
                        vertical_flight_end = message['TimeUS']
                        total_vertical_flight_time += vertical_flight_end - vertical_flight_start
        elif is_auto_mode and message['mavpackettype'] == 'MSG':
            if not is_vertical_mode and 'VTOL Position' in message['Message']:
                is_vertical_mode = True

                if is_flying: # start vertical timer if flying
                    vertical_flight_start = message['TimeUS']
            elif is_vertical_mode and 'Exited VTOL' in message['Message']:
                is_vertical_mode = False

                if is_flying:
                    vertical_flight_end = message['TimeUS']
                    total_vertical_flight_time += vertical_flight_end - vertical_flight_start

    print(
        f"Key flight data (for DesOps):\n"
        f"\tTotal Flights: {total_flights}\n"
        f"\tTotal Auto Flights: {total_auto_flights}\n"
        f"\tTotal Flight Time: {total_flight_time / 1e6:.2f}s\n"
        f"\tTotal Vertical Flight Time: {total_vertical_flight_time / 1e6:.2f}s\n"
        f"\tTotal Horizontal Time: {(total_flight_time - total_vertical_flight_time) / 1e6:.2f}s\n"
        f"\tAuto Flight Time: {total_auto_time / 1e6:.2f}s\n"
        f"\tManual Flight Time: {(total_flight_time - total_auto_time) / 1e6:.2f}s"
    )

def battery_voltage(messages):
    battery_voltage_times = []
    battery_voltages = []

    for message in messages:
        battery_voltage_times.append(message['TimeUS'] / 1e6)
        battery_voltages.append(message['Volt'])

    average_voltage = np.mean(battery_voltages)
    
    plt.plot(battery_voltage_times, battery_voltages)

    plt.title('Battery Voltage Over Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (V)')

    # add lines to indicate flight start and end times
    for i in range(len(data['flights_timestamps']) // 2):
        plt.axvline(data['flights_timestamps'][2 * i] / 1e6, color='red', linestyle = '--', label = 'Threshold')
        plt.text(data['flights_timestamps'][2 * i] / 1e6, average_voltage, f'Flight {i + 1} Start', rotation=90, color='red', ha='right')
        
        plt.axvline(data['flights_timestamps'][2 * i + 1] / 1e6, color='red', linestyle = '--', label = 'Threshold')
        plt.text(data['flights_timestamps'][2 * i + 1] / 1e6, average_voltage, f'Flight {i + 1} End', rotation=90, color='red', ha='right')

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
        elif user == 'battery voltage':
            battery_voltage(data['battery_voltage'])
        else:
            print('Please enter a valid command. For a list of all commands, enter [help].')
