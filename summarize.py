from LogSummary import LogSummary
import os

def main():
    for file in os.listdir('logs'):
        if file.endswith('.BIN'):
            analyzer = LogSummary(os.path.join('logs', file))
            analyzer.parse_log()
            analyzer.process_messages()

if __name__ == "__main__":
    main()
