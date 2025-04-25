from pymavlink import mavutil
import os
import csv
import re

# TODO: printing out joint summary, joint csv

class LogSummary:
    """
    A class for summarizing flight logs.
    Currently, it is designed to support the flight summary that DesOps requires, 
    but it can be extended to support other types of flight analysis.
    """

    MESSAGE_TYPES = {'CMD', 'MODE', 'MSG', 'STAT'} # Set of relevant message types
    AUTO_MODE = 10 # Auto mode number
    VERTICAL_MODES = {17, 18, 19, 20, 21, 22, 23, 25} # Set of vertical mode numbers

    def __init__(self, file):
        self.file = file
        self.messages = [] # List of relevant messages from the log file

        self.flights = 0
        self.auto_flights = 0
        self.auto_counted = False

        self.is_flying = False
        self.flight_start_time = None
        self.total_flight_time = 0

        self.is_auto = False
        self.auto_start_time = None
        self.total_auto_time = 0

        self.is_vertical = False
        self.vertical_start_time = None
        self.total_vertical_time = 0

        self.wp_data = {} # Format: {wp_num: [type, lat, lng, alt, deviance]}
        self.wp_count = 0
        self.wp_cmd = False
        self.avg_wp_deviance = None

        self.parse_log()
        self.process_messages()
        self.to_csv()
        self.print_summary()
        print(f"\033[1mLog Summary for {self.file} complete!\033[0m")

    def parse_log(self):
        message_count = 0
        mavlog = mavutil.mavlink_connection(self.file, dialect='ardupilotmega', robust_parsing=True)

        while True:
            message = mavlog.recv_match()

            if not message:
                break

            message = message.to_dict()

            if message['mavpackettype'] in self.MESSAGE_TYPES:
                self.messages.append(message)

            message_count += 1
        
        print(f'Processed {message_count} messages for {self.file}.')

    def process_messages(self):
        for message in self.messages:
            type = message['mavpackettype']

            if type == 'CMD':
                print(message)
                self.process_cmd_message(message)
            elif type == 'MODE':
                self.process_mode_message(message)
            elif type == 'MSG':
                print(message)
                self.process_msg_message(message)
            elif type == 'STAT':
                self.process_stat_message(message)

    def process_cmd_message(self, message):
        if self.wp_cmd:
            self.wp_data[self.wp_count][1] = message['Lat']
            self.wp_data[self.wp_count][2] = message['Lng']
            self.wp_data[self.wp_count][3] = message['Alt']
            self.wp_cmd = False

    def process_mode_message(self, message):
        mode = message['Mode']

        if not self.is_auto and mode == self.AUTO_MODE:
            # The plane is in auto mode.
            self.is_auto = True

            if self.is_flying:
                # If the plane is flying, calculate the auto flight time.
                if not self.auto_counted:
                    self.auto_flights += 1
                    self.auto_counted = True

                self.auto_start_time = message['TimeUS']
        elif self.is_auto and mode != self.AUTO_MODE:
            # The plane is not in auto mode.
            self.is_auto = False

            if self.is_flying:
                # If the plane is flying, calculate the auto flight time.
                self.total_auto_time += message['TimeUS'] - self.auto_start_time
                self.auto_start_time = None

        if not self.is_vertical and mode in self.VERTICAL_MODES:
            # The plane is in vertical mode
            self.is_vertical = True

            if self.is_flying:
                # If the plane is flying, calculate the vertical time.
                self.vertical_start_time = message['TimeUS']
        elif self.is_vertical and mode not in self.VERTICAL_MODES:
            # The plane is not in vertical mode.
            self.is_vertical = False

            if self.is_flying:
                # If the plane is flying, calculate the vertical time.
                self.total_vertical_time += message['TimeUS'] - self.vertical_start_time
                self.vertical_start_time = None

    def process_msg_message(self, message):
        msg = message['Message']

        if msg.startswith('Mission: '):
            self.wp_count += 1
            self.wp_cmd = True
            self.wp_data[self.wp_count] = [re.match(r'Mission: \d+ ([A-Za-z ]+)', msg).group(1), None, None, None, None]
        elif msg.startswith('Reached waypoint ') or msg.startswith('Passed waypoint '):
            deviance = int(re.search(r"dist (\d+)m", message['Message']).group(1))
            self.wp_data[self.wp_count][4] = deviance
        elif not self.is_vertical and re.match(r'VTOL position\d+ started v=\d+(?:\.\d+)? d=\d+(?:\.\d+)? h=\d+(?:\.\d+)?', msg):
            # The plane is in vertical flight while in auto mode.
            self.is_vertical = True
            self.vertical_start_time = message['TimeUS']
        elif self.is_vertical and msg == 'EXITED VTOL':
            # The plane has exited vertical flight while in auto mode.
            self.is_vertical = False
            self.total_vertical_time += message['TimeUS'] - self.vertical_start_time
            self.vertical_start_time = None
    
    def process_stat_message(self, message):
        if not self.is_flying and message['isFlyProb'] >= 0.8:
            # The plane has started flying!
            self.flights += 1
            self.is_flying = True
            self.auto_counted = False
            self.flight_start_time = message['TimeUS']

            if self.is_auto:
                # The plane started flying in auto mode.
                if not self.auto_counted:
                    self.auto_flights += 1
                    self.auto_counted = True

                self.auto_start_time = message['TimeUS']

            if self.is_vertical:
                # The plane started flying in vertical mode.
                self.vertical_start_time = message['TimeUS']
        elif self.is_flying and message['isFlyProb'] < 0.8:
            # The plane has stopped flying.
            self.is_flying = False
            self.total_flight_time += message['TimeUS'] - self.flight_start_time
            self.flight_start_time = None

            if self.is_auto:
                # The plane stopped flying in auto mode.
                self.total_auto_time += message['TimeUS'] - self.auto_start_time
                self.auto_start_time = None

            if self.is_vertical:
                # The plane stopped flying in vertical mode.
                self.total_vertical_time += message['TimeUS'] - self.vertical_start_time
                self.vertical_start_time = None

    def to_csv(self):
        file = os.path.basename(self.file)
        name, _ = os.path.splitext(file)
        csv_file = os.path.join('summaries', f"{name}.csv")

        total_flight_time = round(self.total_flight_time / 1e6, 2)
        total_auto_time = round(self.total_auto_time / 1e6, 2)
        total_manual_time = round((self.total_flight_time - self.total_auto_time) / 1e6, 2)
        total_vertical_time = round(self.total_vertical_time / 1e6, 2)
        total_horizontal_time = round((self.total_flight_time - self.total_vertical_time) / 1e6, 2)

        deviance_sum = 0
        deviance_count = 0

        for wp in self.wp_data.values():
            if wp[4] is not None:
                deviance_sum += wp[4]
                deviance_count += 1

        if deviance_count > 0:
            self.avg_wp_deviance = round(deviance_sum / deviance_count, 2)

        with open(csv_file, mode='w', newline='') as file:
            writer = csv.writer(file)

            writer.writerow([
                '# Flights', 
                '# Auto Flights', 
                'Flight Time (s)', 
                'Auto Flight Time (s)', 
                'Manual Flight Time (s)', 
                'Vertical Flight Time (s)', 
                'Horizontal Flight Time (s)', 
                'Waypoints Attempted', 
                'Waypoints Hit', 
                'Average Waypoint Deviance (m)'
            ])

            writer.writerow([
                self.flights,
                self.auto_flights,
                total_flight_time,
                total_auto_time,
                total_manual_time,
                total_vertical_time,
                total_horizontal_time,
                self.wp_count,
                self.wp_count,
                self.avg_wp_deviance if self.avg_wp_deviance is not None else 'N/A'
            ])

            if self.wp_count > 0:
                writer.writerow([])
                writer.writerow(['#', 'Type', 'Latitude', 'Longitude', 'Altitude', 'Deviance (m)'])

                for wp_num, wp_info in self.wp_data.items():
                    writer.writerow([
                        wp_num,
                        wp_info[0],
                        wp_info[1],
                        wp_info[2],
                        wp_info[3],
                        wp_info[4] if wp_info[4] is not None else 'N/A'
                    ])

        print(f"Summary saved to {csv_file}.")

    def print_summary(self):
        rows = [
            ('# Flights', self.flights),
            ('# Auto Flights', self.auto_flights),
            ('Flight Time (s)', f"{round(self.total_flight_time / 1e6, 2)}"),
            ('Auto Flight Time (s)', f"{round(self.total_auto_time / 1e6, 2)}"),
            ('Manual Flight Time (s)', f"{round((self.total_flight_time - self.total_auto_time) / 1e6, 2)}"),
            ('Vertical Flight Time (s)', f"{round(self.total_vertical_time / 1e6, 2)}"),
            ('Horizontal Flight Time (s)', f"{round((self.total_flight_time - self.total_vertical_time) / 1e6, 2)}"),
            ('Waypoints Attempted', self.wp_count),
            ('Waypoints Hit', self.wp_count),
            ('Average Waypoint Deviance (m)', f"{self.avg_wp_deviance if self.avg_wp_deviance else 'N/A'}")
        ]

        label_width = 40
        value_width = 40
        total_width = label_width + 3 + value_width

        border = '-' * (total_width + 4)

        print(border)
        print(f"| {'Flight Summary for ' + self.file:^{total_width}} |")
        print(border)

        for label, value in rows:
            print(f"| {label:<{label_width}} : {str(value):>{value_width}} |")

        print(border)
        print(f"| {'End of Flight Summary':^{total_width}} |")
        print(border)

        if self.wp_count > 0:
            try:
                headers = [
                    "#", 
                    "Type", 
                    "Latitude", 
                    "Longitude", 
                    "Altitude (m)", 
                    "Deviance (m)"
                ]

                rows = []
                for wp_num in self.wp_data:
                    row = [wp_num] + self.wp_data[wp_num][:4] + [self.wp_data[wp_num][4] if self.wp_data[wp_num][4] is not None else 'N/A']
                    rows.append(row)

                col_widths = [4, 16, 12, 12, 12, 12]
                total_width = sum(col_widths) + 3 * len(headers) + 1

                border = "-" * total_width
                print(border)
                print(f"| {'Waypoint Table for ' + self.file:^{total_width - 4}} |")
                print(border)

                header_line = "| " + " | ".join(
                    f"{headers[i]:^{col_widths[i]}}" for i in range(len(headers))
                ) + " |"
                print(header_line)
                print(border)

                for row in rows:
                    row_line = "| " + " | ".join(
                        f"{cell:<{col_widths[i]}}" if i == 1 else f"{cell:^{col_widths[i]}}"
                        for i, cell in enumerate(row)
                    ) + " |"
                    print(row_line)

                print(border)
                print(f'| {'End of Waypoint Table':^{total_width - 4}} |')
                print(border)
            except:
                print('Error with waypoint data. Something funky happened during test flight. Check the log file.')
        else:
            print('No waypoints found.')
