import csv
import os
import re
from pymavlink import mavutil

csv_data = []

data = {
    'flight_summary': [],
}

flight_summary_types = {'STAT', 'MODE', 'MSG'}
vertical_modes = {17, 18, 19, 20, 21, 22, 23}

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

        total_messages += 1
        print(f'Processing {total_messages} messages for {file}...', end='\r')

    print(f'Finished processing {total_messages} messages for {file}.')
    print(f'---------- Flight Summary for {file} ----------')

def flight_summary(messages, file):
    is_flying = False
    is_auto_mode = False
    is_auto_flight = False
    is_vertical_mode = False

    flight_start = flight_end = 0
    auto_flight_start = auto_flight_end = 0
    vertical_flight_start = vertical_flight_end = 0

    total_flights = total_flight_time = total_auto_flights = 0
    total_auto_time = total_vertical_flight_time = 0

    total_wp_attempted = 0
    total_wp_deviance = 0
    total_wp = 0

    for message in messages:
        if message['mavpackettype'] == 'STAT':
            if not is_flying and message['isFlyProb'] >= 0.8:
                is_flying = True
                total_flights += 1
                flight_start = message['TimeUS']

                if is_auto_mode:
                    auto_flight_start = message['TimeUS']

                    if not is_auto_flight:
                        is_auto_flight = True
                        total_auto_flights += 1

                if is_vertical_mode:
                    vertical_flight_start = message['TimeUS']
            elif is_flying and message['isFlyProb'] < 0.8:
                is_flying = False
                flight_end = message['TimeUS']
                total_flight_time += flight_end - flight_start

                if is_auto_mode:
                    auto_flight_end = message['TimeUS']
                    total_auto_time += auto_flight_end - auto_flight_start

                    if is_auto_flight:
                        is_auto_flight = False

                if is_vertical_mode:
                    vertical_flight_end = message['TimeUS']
                    total_vertical_flight_time += vertical_flight_end - vertical_flight_start
        elif message['mavpackettype'] == 'MODE':
            if message['Mode'] == 10:
                is_auto_mode = True
                if is_flying:
                    auto_flight_start = message['TimeUS']

                    if not is_auto_flight:
                        is_auto_flight = True
                        total_auto_flights += 1

                if is_vertical_mode:
                    vertical_flight_end = message['TimeUS']
                    total_vertical_flight_time += vertical_flight_end - vertical_flight_start
            elif not is_vertical_mode and message['Mode'] in vertical_modes:
                is_vertical_mode = True

                if is_flying:
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
        elif message['mavpackettype'] == 'MSG':
            if 'Mission: ' in message['Message']:
                total_wp_attempted += 1
            elif 'Reached waypoint' in message['Message'] or 'Passed waypoint' in message['Message']:
                distance = re.search(r"dist (\d+)m", message['Message'])
                total_wp_deviance += int(distance.group(1))
                total_wp += 1
            elif not is_vertical_mode and 'VTOL Position' in message['Message']:
                is_vertical_mode = True

                if is_flying:
                    vertical_flight_start = message['TimeUS']
            elif is_vertical_mode and 'Exited VTOL' in message['Message']:
                is_vertical_mode = False

                if is_flying:
                    vertical_flight_end = message['TimeUS']
                    total_vertical_flight_time += vertical_flight_end - vertical_flight_start

    total_flight_time = round(total_flight_time / 1e6, 2)
    total_vertical_flight_time = round(total_vertical_flight_time / 1e6, 2)
    total_horizontal_flight_time = round((total_flight_time - total_vertical_flight_time) / 1e6, 2)
    total_auto_time = round(total_auto_time / 1e6, 2)
    manual_flight_time = round((total_flight_time - total_auto_time) / 1e6, 2)
    average_wp_deviance = 0 if total_wp == 0 else round(total_wp_deviance / total_wp, 2)

    print(
        f'\tTotal Flights: {total_flights}\n'
        f'\tTotal Auto Flights: {total_auto_flights}\n'
        f'\tTotal Flight Time: {total_flight_time}s\n'
        f'\tTotal Vertical Flight Time: {total_vertical_flight_time}s\n'
        f'\tTotal Horizontal Time: {total_horizontal_flight_time}s\n'
        f'\tAuto Flight Time: {total_auto_time}s\n'
        f'\tManual Flight Time: {manual_flight_time}s\n'
        f'\tWaypoints Attempted: {total_wp_attempted}\n'
        f'\tAverage Waypoint Deviance: {average_wp_deviance}m across {total_wp} waypoints'
    )

    csv_data.append({'file': file, 
                     'flights': total_flights, 
                     'auto_flights': total_auto_flights, 
                     'flight_time': total_flight_time, 
                     'vertical_flight_time': total_vertical_flight_time, 
                     'horizontal_flight_time': total_horizontal_flight_time,
                     'auto_time': total_auto_time, 
                     'manual_time': manual_flight_time,
                     'wp_attempted': total_wp_attempted, 
                     'wp': total_wp,
                     'average_wp_deviance': average_wp_deviance})

    return total_flights, total_auto_flights, total_flight_time, total_vertical_flight_time, total_horizontal_flight_time, total_auto_time, manual_flight_time, total_wp_attempted, total_wp, total_wp_deviance

def process_logs():
    total_flights = total_auto_flights = total_flight_time = total_vertical_flight_time = total_horizontal_flight_time = total_auto_time = manual_flight_time = total_wp_attempted = total_wp = total_wp_deviance = 0

    for file in os.listdir('logs'):
        if file.endswith('.BIN'):
            file_path = os.path.join('logs', file)
            
            data['flight_summary'].clear()
            
            parse_log(file_path)
            flights, auto_flights, flight_time, vertical_flight_time, horizontal_flight_time, auto_time, manual_time, wp_attempted, wp, wp_deviance = flight_summary(data['flight_summary'], file)
            total_flights += flights
            total_auto_flights += auto_flights
            total_flight_time += flight_time
            total_vertical_flight_time += vertical_flight_time
            total_horizontal_flight_time += horizontal_flight_time
            total_auto_time += auto_time
            manual_flight_time += manual_time
            total_wp_attempted += wp_attempted
            total_wp += wp
            total_wp_deviance += wp_deviance
            average_wp_deviance = 0 if total_wp == 0 else round(total_wp_deviance / total_wp, 2)

    print(
        f'========== TOTAL FLIGHT SUMMARY ==========\n'
        f'\tTotal Flights: {total_flights}\n'
        f'\tTotal Auto Flights: {total_auto_flights}\n'
        f'\tTotal Flight Time: {total_flight_time}s\n'
        f'\tTotal Vertical Flight Time: {total_vertical_flight_time}s\n'
        f'\tTotal Horizontal Time: {total_horizontal_flight_time}s\n'
        f'\tAuto Flight Time: {total_auto_time}s\n'
        f'\tManual Flight Time: {manual_flight_time}s\n'
        f'\tWaypoints Attempted: {total_wp_attempted}\n'
        f'\tAverage Waypoint Deviance: {average_wp_deviance}m across {total_wp} waypoints\n'
        f'========================================='
    )

    csv_data.append({'file': 'TOTAL', 
                     'flights': total_flights, 
                     'auto_flights': total_auto_flights, 
                     'flight_time': total_flight_time, 
                     'vertical_flight_time': total_vertical_flight_time, 
                     'horizontal_flight_time': total_horizontal_flight_time,
                     'auto_time': total_auto_time, 
                     'manual_time': manual_flight_time,
                     'wp_attempted': total_wp_attempted, 
                     'wp': total_wp,
                     'average_wp_deviance': average_wp_deviance})

    fieldnames = ['file', 
                  'flights', 
                  'auto_flights', 
                  'flight_time', 
                  'vertical_flight_time', 
                  'horizontal_flight_time', 
                  'auto_time', 
                  'manual_time', 
                  'wp_attempted', 
                  'wp', 
                  'average_wp_deviance']

    with open('flight_summary.csv', mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)

process_logs()
