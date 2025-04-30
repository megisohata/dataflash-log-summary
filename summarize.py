from LogSummary import LogSummary
import os
import glob


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
        flight_data = []
        wp_data = []

        summaries = glob.glob(os.path.join("summaries", "*.csv"))

        for file in summaries:
            if file.endswith("flight_summary.csv"):
                pass
            elif file.endswith("waypoint_summary.csv"):
                pass


if __name__ == "__main__":
    main()
