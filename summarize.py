from LogSummary import LogSummary
from LogSummary import print_banner
import os
import glob
import csv
from tabulate import tabulate


def main():
    # Delete old summaries.
    csv_files = glob.glob(os.path.join("summaries", "*.csv"))

    for file in csv_files:
        os.remove(file)

    # Summarize each log.
    logs = 0

    for file in os.listdir("logs"):
        if file.endswith(".BIN"):
            logs += 1
            LogSummary(os.path.join("logs", file))

    if logs > 1:
        flight_data = [
            [
                "Log",
                "Flights",
                "Auto Flights",
                "FT (s)",
                "Auto FT (s)",
                "Manual FT (s)",
                "Vertical FT (s)",
                "Horizontal FT (s)",
                "WP Attempted",
                "WP Hit",
                "Avg WP Deviance (m)",
            ]
        ]

        wp_data = [
            [
                "Log",
                "#",
                "Type",
                "Latitude",
                "Longitude",
                "Altitude (m)",
                "Deviance (m)",
            ]
        ]

        summaries = glob.glob(os.path.join("summaries", "*.csv"))

        for file in summaries:
            if file.endswith("flight_summary.csv"):
                entry = []

                with open(file, "r") as rfile:
                    reader = csv.reader(rfile)
                    next(reader)

                    for row in reader:
                        entry = [file.split("/")[1].split("_")[0]] + row

                flight_data.append(entry)
            elif file.endswith("waypoint_summary.csv"):
                with open(file, "r") as rfile:
                    reader = csv.reader(rfile)
                    next(reader)

                    for row in reader:
                        entry = [file.split("/")[1].split("_")[0]] + row
                        wp_data.append(entry)

        # Total row.
        total = ["TOTAL"]
        total.append(sum(float(row[1]) for row in flight_data[1:]))
        total.append(sum(float(row[2]) for row in flight_data[1:]))
        total.append(sum(float(row[3]) for row in flight_data[1:]))
        total.append(sum(float(row[4]) for row in flight_data[1:]))
        total.append(sum(float(row[5]) for row in flight_data[1:]))
        total.append(sum(float(row[6]) for row in flight_data[1:]))
        total.append(sum(float(row[7]) for row in flight_data[1:]))
        total.append(sum(float(row[8]) for row in flight_data[1:]))
        total.append(sum(float(row[9]) for row in flight_data[1:]))
        total.append(
            round(
                sum([float(row[10]) for row in flight_data[1:] if row[10] != "N/A"])
                / sum([1 for row in flight_data[1:] if row[10] != "N/A"]),
                2,
            )
        )
        flight_data.append(total)

        with open(
            os.path.join("summaries", f"flight_summary.csv"),
            "w",
            newline="",
        ) as file:
            writer = csv.writer(file)
            writer.writerows(flight_data)

        with open(
            os.path.join("summaries", f"waypoint_summary.csv"),
            "w",
            newline="",
        ) as file:
            writer = csv.writer(file)
            writer.writerows(wp_data)

        print_banner("ALL", label="Start")
        print(tabulate(flight_data[1:], headers=flight_data[0], tablefmt="outline"))
        print(tabulate(wp_data[1:], headers=wp_data[0], tablefmt="outline"))
        print("Combined flight summary saved to summaries/flight_summary.csv")
        print("Combined flight summary saved to summaries/waypoint_summary.csv")
        print_banner("ALL", label="End")


if __name__ == "__main__":
    main()
