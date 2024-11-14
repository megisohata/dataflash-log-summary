from pymavlink import mavutil

file = 'logs/00000075.BIN'

mavlog = mavutil.mavlink_connection(file, dialect='ardupilotmega', robust_parsing=True)

while True:
    message = mavlog.recv_match()

    if not message:
        break

    print(f"{message.get_type()}: {message.to_dict()}")