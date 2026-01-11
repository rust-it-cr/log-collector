# Log Collector

[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0) [![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

🛠️ **Python tool for Junos log analysis:**
extracts .tgz bundles and filters by timestamp/keyword. It speeds up log analysis and groups accordingly.

## 💡 Who needs a log collector anyway?

Network troubleshooting often requires analyzing Junos `.tgz` bundles that contain dozens of compressed log files. Manually extracting these and running `grep` or searching through text editors is time-consuming and prone to human error.

I built **logc** to solve three specific problems:
- **Efficiency:** Automates the extraction and recursive searching of multiple logs in seconds.
- **Precision:** Uses specific timestamp logic to narrow down logs to the exact window of a network event, reducing "noise".
- **Portability:** Designed with zero external dependencies so it can be used immediately on any jump host or production server with Python installed.

## 📦 Installation

The recommended way to install **logc** is using `pipx`. This ensures the tool works on Windows, Mac, and Linux by automatically managing your environment and system PATH.

### 1. Set up pipx (first time only - just for Windows)
If you don't have `pipx` installed, run:
```bash
python -m pip install --user pipx
python -m pipx ensurepath
```

Note: Restart your terminal after running ensurepath.

### 2. Install the tool:

Install directly from the latest GitHub release:

```bash
pipx install https://github.com/rust-it-cr/log-collector/releases/download/v.0.1.2/logc-0.1.2-py3-none-any.whl
```

Or, download the .whl file from the GitHub page and run the following:

```bash
pipx install ./logc-0.1.2-py3-none-any.whl
```

## 🧩 Dependencies
This tool is built entirely using the **Python Standard Library**. 
- No third-party packages are required.
- Easy to deploy in air-gapped or restricted production environments where Junos-generated .tgz log files must be analyzed.

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
If you need to find all the logs from a specifit timestamp or time range across different files (or just one):
```bash
logc -s "/home/user_name/Downloads/logs.tgz" -d "/home/user_name/Downloads/output.txt" -f "chassisd" -t "Oct  6 to Oct  8"
```

### 3. Combining filters:
You can also filter by both keywords and timestamps if that's what you need:
```bash
logc -s "/home/user_name/Downloads/logs.tgz" -d "/home/user_name/Downloads/output.txt" -f "default-log-messages" -t "2025-01-01T00" -ka "crash" "version" "upgrade" 
```

### 4. Case-insensitive searching:
If needed, you can perform a case-insensitive search if you don't remember if the keyword is lower- or upper-case, of a combination thereof:
```bash
logc -s "/home/user_name/Downloads/logs.tgz" -d "/home/user_name/Downloads/output.txt" -f "kmd-logs" -t "Jan 1  12" -ko "vpn" "ipsec" "ike" -i
```

## 🧪 Testing & Error Handling

This project uses pytest and the standard src layout. To run tests, you must install the project in editable mode so the test suite can locate the package logic.

1. Install the package and dependencies:
```bash
pip install pytest
# Install the tool locally in editable mode
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

[!IMPORTANT] Do not run the tests from inside the tests/ folder. Running from the root directory allows pytest to properly map the src/ layout and find all test files automatically.

3. Unknown errors handling:

Also, this tool has a way of handling unknown errors gracefully. If that happens, you will see the following output and a file in your "Desktop" folder (which then you can send me for debugging purposes):
```bash
logc -s "C:\Users\user_name\Downloads\corrupted-logs.tgz" -d "C:\Users\user_name\Downloads\no-file.txt" -f "messages" -k "ge-0/0/0"

'An unknown error occurred. Please check the 'error.log' file on your Desktop for technical details.'
```

## 📜 License

This project is licensed under the **GNU Lesser General Public License v3.0 or later**. 

- See the [COPYING](COPYING) file for the full GPLv3 text.

- See the [COPYING.LESSER](COPYING.LESSER) file for the LGPLv3 additional permissions.
