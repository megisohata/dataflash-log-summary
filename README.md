# DataFlash Log Summary

This project focuses on streamlining the process of analyzing log files after each test flight, which currently requires up to 10 minutes per file when done manually—and often involves multiple files per test flight. The program significantly improves efficiency by summarizing large files containing up to 2 million messages in approximately 30 seconds.

## Usage

```
git clone git@github.com:[USERNAME]/dataflash-log-summary.git
```

Create a `logs` folder in the root directory.

Move all log files (.BIN) you want to summarize into the `logs` folder.

From your terminal, run `python script.py`.

The script will process each file one-by-one, output the summary of each file, then output the sum of all the files.

Example Output:

<img width="650" alt="Terminal Output" src="https://github.com/user-attachments/assets/15ef0c97-4f28-4462-b5c9-6d01534274d0">
