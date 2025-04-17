from LogSummary import LogSummary
import os
import glob
import pandas as pd
import numpy as np
import csv


def main():
    summaries_folder = 'summaries'
    logs_folder = 'logs'

    # Delete pre-existing CSV files
    csv_files = glob.glob(os.path.join(summaries_folder, '*.csv'))
    for file in csv_files:
        os.remove(file)

    # Run summary on each .BIN file
    for file in os.listdir(logs_folder):
        if file.endswith('.BIN'):
            LogSummary(os.path.join(logs_folder, file))

    # Define the headers we want in our final CSV
    summary_headers = ['log', 'flights', 'auto_flights', 'flight_time', 'manual_time', 
                      'auto_time', 'vertical_flight_time', 'horizontal_flight_time', 
                      'wp_attempted', 'wp_successful', 'average_wp_deviance']
    
    waypoint_headers = ['log', 'wp_number', 'type', 'lat', 'lng', 'alt', 'deviance']
    
    all_summary_data = []
    all_waypoint_data = []
    
    # Get all CSV files
    csv_files = glob.glob(os.path.join(summaries_folder, "*.csv"))
    
    # Process each CSV file
    for file_path in csv_files:
        # Extract file name without extension
        file_name = os.path.basename(file_path).split('.')[0]
        
        with open(file_path, 'r') as file:
            lines = file.readlines()
            
            # Skip the first line (header) and read the second line (summary data)
            if len(lines) >= 2:
                summary_data_line = lines[1].strip().split(',')
                
                # Add filename as log column with the actual data values
                summary_data = [file_name] + summary_data_line
                all_summary_data.append(summary_data)
                
                # Skip to line 4 (skip the waypoint header in line 3)
                # Process waypoint data starting from the fourth line
                if len(lines) >= 4:
                    for i in range(3, len(lines)):
                        line = lines[i].strip()
                        if line:  # Check if line is not empty
                            waypoint_data_line = line.split(',')
                            waypoint_data = [file_name] + waypoint_data_line
                            all_waypoint_data.append(waypoint_data)
    
    # Calculate totals for summary data
    if all_summary_data:
        # Convert to DataFrame for easier calculations
        df_summary = pd.DataFrame(all_summary_data, columns=summary_headers)
        
        # Convert numeric columns to appropriate types
        numeric_cols = summary_headers[1:]  # All except 'log'
        for col in numeric_cols:
            df_summary[col] = pd.to_numeric(df_summary[col], errors='coerce')
        
        # Create totals row
        totals = ['TOTAL']
        for col in summary_headers[1:]:
            if col == 'average_wp_deviance':
                # For average_wp_deviance, calculate the average
                totals.append(str(round(df_summary[col].mean(), 1)))
            else:
                # For other columns, calculate the sum
                totals.append(str(int(df_summary[col].sum())))
        
        # Add totals row to summary data
        all_summary_data.append(totals)
    
    # Write combined data to output file
    output_file = 'summary.csv'
    with open(output_file, 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        
        # Write summary data with headers
        writer.writerow(summary_headers)
        writer.writerows(all_summary_data)
        
        # Add a blank line
        writer.writerow([])
        
        # Write waypoint headers and data
        writer.writerow(waypoint_headers)
        writer.writerows(all_waypoint_data)
    
    print(f"Combined summary written to {output_file}.")
    print(f"\033[1mLog Summary for all files complete!\033[0m")

if __name__ == "__main__":
    main()
    