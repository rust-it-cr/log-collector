# Log Collector

[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0) [![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

🛠️ **Python tool for log analysis:**
extracts logs and filters by timestamp/keyword, generating a single .txt file as output. It speeds up log analysis and groups logs accordingly.

## 💡 Who needs a log collector anyway?

Network troubleshooting often requires analyzing log bundles that contain dozens of compressed log files. Manually extracting these and running `grep` or searching through text editors is time-consuming and prone to human error.

I built **logc** to solve three specific problems:
- **Efficiency:** Automates the extraction and recursive searching of multiple logs in seconds.
- **Precision:** Uses specific timestamp and/or keyword logic to narrow down logs to the exact window of a network event, reducing "noise".
- **Portability:** Designed with zero external dependencies so it can be used immediately on any device with Python installed.

It works as follows: it checks for a directory, inspects all log files therein, and extracts all logs into a single file based on timestamp and/or keyword. The output is a structured file with the name of each log file at the beginning of each section and the relevant logs underneath the headers. As an aside note, this is my first project in Python. Building it was fun, and I'm here for any fixes that may be necessary.

## 📦 Installing, Updating, and/or Uninstalling **logc**

The recommended way to install **logc** is using `pipx`. This ensures the tool works on any OS by automatically managing your environment and system PATH.

### 1. Install Python and Git on your system.

### 2. Set up pipx
If you don't have [pipx](https://pypi.org/project/pipx/) installed, run:
```bash
python -m pip install --user pipx
python -m pipx ensurepath
```

**Note**: Restart your terminal after running ensurepath.

### 3. Install the tool:

To install **logc**, run the following command:

```bash
pipx install git+https://github.com/rust-it-cr/log-collector.git
```
**Note**: This installation method requires [Git](https://www.google.com/search?q=https://git-scm.com/downloads) to be installed on your local machine. However, you do not need a GitHub account to download the tool.

### 4. Update the tool:

To update the tool, simply run the following command:

```bash
pipx upgrade logc
```

If already up to date, your terminal will display the following message:

```bash
"logc is already at latest version x.y.z (location: <location on your PC>)"
```

### 5. Uninstall the tool:

If for some reason you don't want to use this tool any longer, uninstalling it is as simple as running this command:

```bash
pipx uninstall logc
```

## 🧩 Dependencies
This tool is built entirely using the **Python Standard Library**. 
- No third-party packages are required.
- Easy to deploy in environments where Junos-generated .tgz log files must be analyzed.

## 🛠 Usage

Once installed, use the `logc` command in your terminal.

### Help options:
View all available filters and options:
```bash
logc -h
```

## 🛠 Examples

### 1. Searching for specific errors
If you need to find every instance of a BGP flap across on a file (or several thereof) in the bundle:
```bash
logc -s "/home/user_name/Downloads/logs.tgz" -d "/home/user_name/Downloads/output.txt" -f "messages" "bgp_logs" -k "BGP_IO_ERROR"
```

### 2. Searching for logs within a specific time
If you need to find all the logs from a specific timestamp or time range across different files (or just one):
```bash
logc -s "/home/user_name/Downloads/logs.tgz" -d "/home/user_name/Downloads/output.txt" -f "chassisd" -t "2025-10-06 to 2025-10-07"
```

### 3. Combining filters:
You can also filter by both keywords and timestamps if that's what you need:
```bash
logc -s "/home/user_name/Downloads/logs.tgz" -d "/home/user_name/Downloads/output.txt" -f "default-log-messages" -t "2025-01-01T00:00:00" -k "crash" and "version" and "upgrade"
```

### 4. Match all files:
You can also perform a search on all parsable files by doing the following:
```bash
logc -s "/home/user_name/Downloads/logs.tgz" -d "/home/user_name/Downloads/output.txt" -f ".*" -t "2025-01-01T00:00:00" -k "crash" and "version" and "upgrade"
```

## 🧪 Testing & Error Handling

This project uses `pytest` and the standard src layout. To run tests, you must install the project in editable mode so the test suite can locate the package logic.

1. Install the package and dependencies:
```bash
pip install pytest
pip install -e .
```

2. Run the tests:

Always run the tests from the project root directory (where the pyproject.toml file is located). This ensures the logc_tool package is correctly discovered.

For Windows users:
```bash
python -m pytest
```

For MacOS/Linux users:

```bash
pytest
```

[**IMPORTANT**] Do not run the tests from inside the tests/ folder. Running from the root directory allows pytest to properly map the src/ layout and find all test files automatically.

3. Unknown error handling:

Also, this tool has a way of handling unknown errors gracefully. If that happens, you will see the following output (which you can send me later for debugging purposes)
```bash
logc -s "C:\Users\user_name\Downloads\corrupted-logs.tgz" -d "C:\Users\user_name\Downloads\no-file.txt" -f "messages" -k "ge-0/0/0"

'An error has occurred!'
'Error: <a technical description of the error>'
'Please share this entire error message with the developer of this tool for further debugging.'
```

## 📜 License

This project is licensed under the **GNU Lesser General Public License v3.0 or later**. 

- See the [COPYING](COPYING) file for the full GPLv3 text.

- See the [COPYING.LESSER](COPYING.LESSER) file for the LGPLv3 additional permissions.
