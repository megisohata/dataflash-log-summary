from LogSummary import LogSummary
import os
import glob
import pandas as pd
import csv

def main():
    summaries_folder = 'summaries'
    logs_folder = 'logs'

    # Delete pre-existing CSV files.
    csv_files = glob.glob(os.path.join(summaries_folder, '*.csv'))
    for file in csv_files:
        os.remove(file)

    # Run summary on each .BIN file.
    for file in os.listdir(logs_folder):
        if file.endswith('.BIN'):
            LogSummary(os.path.join(logs_folder, file))

    # Define CSV headers.
    summary_headers = [
        'Log',
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
    ]

    waypoint_headers = [
        'Log',
        "#", 
        "Type", 
        "Latitude", 
        "Longitude", 
        "Altitude (m)", 
        "Deviance (m)"
    ]

    all_summary_data = []
    all_waypoint_data = []

    csv_files = glob.glob(os.path.join(summaries_folder, "*.csv"))

    for file_path in csv_files:
        file_name = os.path.basename(file_path).split('.')[0]

        with open(file_path, 'r') as file:
            lines = file.readlines()

            # Process summary data from second line
            if len(lines) >= 2:
                summary_data_line = lines[1].strip().split(',')
                summary_data = [file_name] + summary_data_line
                all_summary_data.append(summary_data)

            # Process waypoint data starting from line 4
            for line in lines[3:]:
                line = line.strip()
                if line:  # Skip empty lines
                    wp = line.split(',')
                    if wp[0] == "#" or wp[1] == "Type":
                        continue  # Skip headers or malformed lines
                    waypoint_data = [file_name] + wp
                    all_waypoint_data.append(waypoint_data)

    # Calculate totals for summary data
    if all_summary_data:
        df_summary = pd.DataFrame(all_summary_data, columns=summary_headers)

        # Convert numeric columns
        numeric_cols = summary_headers[1:]
        for col in numeric_cols:
            df_summary[col] = pd.to_numeric(df_summary[col], errors='coerce')

        # Totals row
        totals = ['TOTAL']
        for col in numeric_cols:
            if col == 'average_wp_deviance':
                totals.append(str(round(df_summary[col].mean(), 1)))
            else:
                totals.append(str(int(df_summary[col].sum())))

        all_summary_data.append(totals)

    # Write to combined CSV
    output_file = os.path.join(summaries_folder, 'summary.csv')
    with open(output_file, 'w', newline='') as outfile:
        writer = csv.writer(outfile)

        # Write summary section
        writer.writerow(summary_headers)
        writer.writerows(all_summary_data)

        # Blank line
        writer.writerow([])

        # Write waypoint section
        writer.writerow(waypoint_headers)
        writer.writerows(all_waypoint_data)

    print(f"Combined summary written to {output_file}.")
    print(f"\033[1mLog Summary for all files complete!\033[0m")


if __name__ == "__main__":
    main()
