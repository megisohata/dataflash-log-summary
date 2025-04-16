from LogSummary import LogSummary
import os

def main():
    for file in os.listdir('logs'):
        if file.endswith('.BIN'):
            LogSummary(os.path.join('logs', file))

if __name__ == "__main__":
    main()
