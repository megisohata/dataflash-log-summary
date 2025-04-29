from pymavlink import mavutil
import csv
import os
import re

class LogSummary:
    """
    A class for summarizing flight logs.
    Currently, it is designed to support the flight summary that DesOps requires, 
    but it can be extended to support other types of flight analysis.
    """

    MESSAGE_TYPES = {'STAT', 'MODE', 'MSG', 'CMD'} # Set of relevant message types
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

        self.set_wp = []
        self.wp_count = 0
        self.wp_data = {} # Format: {wp_num: [type, lat, lng, alt, deviance]}

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

            if message_count % 1000 == 0:
                print(f'Processed {message_count} messages for {self.file}.', end='\r')
        
        print(f'Finished processing {message_count} messages for {self.file}.')

    def process_messages(self):
        for message in self.messages:
            type = message['mavpackettype']

            if type == 'STAT':
                self.process_stat_message(message)
            elif type == 'MODE':
                self.process_mode_message(message)
            elif type == 'MSG':
                self.process_msg_message(message)
            elif type == 'CMD':
                self.process_cmd_message(message)
        
        print(f'---------- Flight Summary for {self.file} ----------')
        print(f'Total flights: {self.flights}')
        print(f'Total auto flights: {self.auto_flights}')
        print(f'Total flight time: {round(self.total_flight_time / 1e6, 2)} seconds')
        print(f'Total auto flight time: {round(self.total_auto_time / 1e6, 2)} seconds')
        print(f'Total vertical flight time: {round(self.total_vertical_time / 1e6, 2)} seconds')
        print(f'Total horizontal flight time: {round((self.total_flight_time - self.total_vertical_time) / 1e6, 2)} seconds')
        print(f'Waypoints: {self.wp_data}')

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
            self.set_wp = []

            if self.is_auto:
                # The plane stopped flying in auto mode.
                self.total_auto_time += message['TimeUS'] - self.auto_start_time
                self.auto_start_time = None

            if self.is_vertical:
                # The plane stopped flying in vertical mode.
                self.total_vertical_time += message['TimeUS'] - self.vertical_start_time
                self.vertical_start_time = None

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

        if self.is_auto:
            if not self.is_vertical and re.match(r"VTOL position\d+ started v=\d+(?:\.\d+)? d=\d+(?:\.\d+)? h=\d+(?:\.\d+)?", msg):
                # The plane is in vertical flight while in auto mode.
                self.is_vertical = True
                self.vertical_start_time = message['TimeUS']
            elif self.is_vertical and msg == "EXITED VTOL":
                # The plane has exited vertical flight while in auto mode.
                self.is_vertical = False
                self.total_vertical_time += message['TimeUS'] - self.vertical_start_time
                self.vertical_start_time = None
        
        if msg.startswith('Mission: '):
            self.wp_count += 1
            wp_info = self.set_wp.pop(0)
            self.wp_data[self.wp_count] = [re.match(r'Mission: \d+ ([A-Za-z ]+)', msg).group(1), wp_info[0], wp_info[1], wp_info[2], None]
        elif msg.startswith('Reached waypoint ') or msg.startswith('Passed waypoint '):
             deviance = int(re.search(r"dist (\d+)m", message['Message']).group(1))
             self.wp_data[self.wp_count][4] = deviance

    def process_cmd_message(self, message):
        if not self.is_flying and message['CNum'] != 0:
            self.set_wp.append([message['Lat'], message['Lng'], message['Alt']])
