#!/usr/bin/env python3

import argparse
import datetime
import gzip
import io
import logging
import pathlib
import re
import sys
import tarfile

# Custom classes for specific errors
class BothOperatorsError(Exception): # If trying to use both AND and OR operators for -k filtering
    pass

class InvalidTimeError(Exception): # If the specified -t parameter doesn't match either regex
    pass

class MoreThanOneFileError(Exception): # If trying to parse more than one file at a time when using a time range
    pass

class NoOperatorError(Exception): # If using -k with multiple parameters but neither operator is present
    pass

class NonExistentRangeError(Exception): # If the specified time range doesn't exist within a given file
    pass


def main():
    try:
        args = parse_args() # Parse all arguments from the command-line

        if args.wildcard:
            files = get_wildcard_files(args.source, args.wildcard)
            titles = files
        elif args.file:
            files = args.file
            titles = args.file

        files = open_tgz(args.source, files) # Assign the already-opened files to be filtered to the files variable

        filtered_files = []

        for file in files: 
            if args.ignore_case: # If -i is present, store the real file in a variable and lowercase all other variables: the files and logs therein and the time and keys to filter
                real_file = file
                file, args.key, args.time = lower_input(file, args.key, args.time)
                    
            if args.time and args.key: # For filtering with both -t and -k
                file = parse_by_time(file, args.time, titles)
                file = parse_by_key(file, args.key)
            elif args.time: # For filtering with only -t
                file = parse_by_time(file, args.time, titles)
            elif args.key: # For filtering with only -k
                file = parse_by_key(file, args.key)
            
            if args.ignore_case and "Pattern not found" not in file: # If -i is set and the the filtered file is populated with logs, restore them to their original casing
                file = restore_logs(file, real_file)

            filtered_files.append(file)

        success = write_new_file(filtered_files, args.destination, titles) # If successful, write an output file with the filtered logs and exit the program
        sys.exit(success)

    except EOFError as e: # Error out if the source file is corrupted
        sys.exit(f"Failure: {e}. Please, check that the source file isn't corrupted.")

    except (FileNotFoundError, KeyError) as e: # Error out if any specified file in either -s or -f doesn't exist
        sys.exit(f"Failure: {e}. Please, verify that the files you're matching actually exist.")

    except re.PatternError as e: # Error out if the wildcard expression can't match any files
        sys.exit(f"Failure: {e}. Please, check that your wildcard expression is correctly formed.")

    except TypeError as e: # Error out whenever the user isn't using all required flags
        sys.exit(f"Failure: {e}. Please, check that you're typing out all required arguments.")

    except (BothOperatorsError, InvalidTimeError, MoreThanOneFileError, NoOperatorError, NonExistentRangeError) as e: # Error out for all custom errors
        sys.exit(f"Failure: {e}. Please, correct your input.")

    except Exception as e: # Catch all unknown errors and generate a debugging file in the user's Desktop
        failure = log_error(e, args) # Send the error message and args.Namespace to the logging function for proper error file generation
        sys.exit(failure)

# When using the -w flag, create a list of all matching files
def get_wildcard_files(source, wildcard):
    tmp = []

    with tarfile.open(pathlib.Path(source)) as tgz: # Open the .tgz file to iterate over it for pattern matching

        for item in tgz:
            _, file, _ = str(item).split("'") # Split the matching item to get a string like "var/log/{name}"
            
            file = file.replace("var/log/", "") # Delete "var/log" to obtain the raw file name

            if wildcard == "all": # Perform a query on all files
                tmp.append(file)
            else:
                for w in wildcard: # Check for more than one wildcard argument
                    if re.match(w, file, re.IGNORECASE): # Use the user wildcard as a regex for matching
                        tmp.append(file)

    if len(tmp) == 0: # If tmp is empty, that means there was no match
        raise FileNotFoundError("Wildcard didn't match any file")

    return tmp
    
# This function parses all command-line arguments and returns a Namespace objects with all parameters for input file(s) finding, log filtering, and output file generation. All help messages are stored in variables that are then passed to each object for more clarity.
def parse_args(args=None): 
    source_help = "source path for the compressed file that contains the log files to be parsed. Must be an absolute path."
    time_help = 'specify the timestamp the parser should use to collect logs from all specified files. Time format: "<month> <day>[ <HH>[:<MM>[:<SS>]]][ to <month> <day> [<HH>[:<MM>[:<SS>]]]]" or "<YYYY>-<MM>-<DD>[T<HH>[:<MM>[:<SS>]]][ to <YYYY>-<MM>-<DD>[T<HH>[:<MM>[:<SS>]]]]". Only one format supported at a time (i.e., BSD or sd-syslog).'
    ignore_case_help = "run a case-insensitive match on the selected files. It can only be used when using any key parameter. It does not take any arguments."
    destination_help = "destination path for the output text file that will contain all specified logs. Must be an absolute path."
    key_help = 'specify a keyword/keyphrase or group thereof to match on the selected log files. Specify AND matching with a series of words with the "and" keyword interleaved between them; the same logic applies to OR matching with the "or" keyword.'
    file_help = "specify one or more files for their logs to be parsed and extracted into the output file. You can only specify a timestamp and not a time range if parsing more than one file."
    wildcard_help = "specify a regular expression to collect all files matching it. This can't be used if you're using a time range."

    parser_description = "This tool takes a Junos-like .tgz file with logs and generates a .txt file from the specified log files therein based on a specific timestamp/time range or keyword/keylist. All arguments should be wrapped around quotation marks."

    PARSER = argparse.ArgumentParser(description=parser_description)

    PARSER.add_argument("-s", "--source", help=source_help)
    PARSER.add_argument("-t", "--time", help=time_help)
    PARSER.add_argument("-i", "--ignore_case", help=ignore_case_help, action="store_true")
    PARSER.add_argument("-d", "--destination", help=destination_help)
    PARSER.add_argument("-k", "--key", help=key_help, nargs="+")

    FILE_TAKING = PARSER.add_mutually_exclusive_group() # Either parameter here supports one or more files when using a timestamp, but not a time range
    FILE_TAKING.add_argument("-f", "--file", help=file_help, nargs="+")
    FILE_TAKING.add_argument("-w", "--wildcard", help=wildcard_help)

    args = PARSER.parse_args(args)

    if not args.key and not args.time:
        raise TypeError("You didn't specify at least one filtering parameter")

    return args

# Open a .tgz file, match on all files specified in -f, open them, read them, and return a list with each file as a list of logs
def open_tgz(source, items):
    tmp = []

    with tarfile.open(pathlib.Path(source)) as tgz:

        for item in items: # That is, for each file in items, either args.file or args.wildcard

            #TODO - for some reason, when using a wildcard, the whole file is unpacked before being extracted
            file = tgz.extractfile(f"var/log/{item}")

            if file == None:
                continue

            try: # Error handling if the file can't be decoded to continue with other files instead of erroring out
                if item.endswith(".gz"): # Handle .gz compressed files for proper reading
                    with gzip.open(file, "rt") as file:
                        tmp.append(file.readlines())
                else:
                    file = io.TextIOWrapper(file, encoding="cp1252") # Standardize all files to cp1252 encoding
                    tmp.append(file.readlines())

            except UnicodeDecodeError:
                pass

    return tmp

# If -i is set, lower all files with logs, all -k parameters, and any -t parameter, if present; return all parameters but lowered
def lower_input(file, keys, time):
    tmp_file = []
    tmp_keys = [] 

    for log in file:
        tmp_file.append(log.lower())

    for key in keys:
        tmp_keys.append(key.lower())

    if time == None: # In case no -t parameter was specified
        tmp_time = None
    else:
        tmp_time = time.lower()

    return tmp_file, tmp_keys, tmp_time # return new objects, not the original ones modified

# This function filters logs based on the time parameter specified within -t, either by range or by specific timestamp
def parse_by_time(file, time, files):
    BSD_FORMAT = r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)  ?\d?\d( \d\d(:\d\d(:\d\d)?)?)?( to (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)  ?\d?\d( \d\d(:\d\d(:\d\d)?)?)?)?$" # REGEX for BSD-formatted logs
    SD_SYSLOG_FORMAT = r"\d\d\d\d-\d\d-\d\d(T\d\d(:\d\d(:\d\d)?)?)?( to \d\d\d\d-\d\d-\d\d(T\d\d(:\d\d(:\d\d)?)?)?)?" # REGEX for sd-syslog-formatted logs

    if not re.search(BSD_FORMAT, time, re.IGNORECASE) and not re.search(SD_SYSLOG_FORMAT, time, re.IGNORECASE): # Avoid overly wrong time formats
        raise InvalidTimeError("Incorrect time format")

    if " to " in time and len(files) != 1: # Support only for one file in -f at a time when using a time range
        raise MoreThanOneFileError("When using a time range, you can only specify one file at a time")

    tmp = []

    if " to " in time: # to match based on a time range
        min, max = time.split(" to ") # first parameter goes to the left, and second one to the right

        range_counter = 0 # This is used to count if the specified time boundaries exist within the specified file

        for log in file: # Check if the lower bound exists
            if min in log:
                range_counter += 1
                break

        for log in file: # Check if the upper bound exists
            if max in log:
                range_counter += 1
                break

        if range_counter != 2: # If both limits exist within the file, the program will continue; otherwise, it will error out
            raise NonExistentRangeError("Time range doesn't exist in the present file")
        else:
            inside_range = False # To check whether we're inside the appropriate range

            for log in file:
                if min in log: # Whenever min is found, inside_range becomes True and all logs thereafter are stored in the tmp list
                    inside_range = True
                    tmp.append(log.strip())
                if inside_range: # While true, all logs after min but before max will be stored
                    tmp.append(log.strip())
                if max in log: # When found, inside_range becomes false and only the last logs containing max will be stored; after that, it will stop
                    inside_range = False
                    tmp.append(log.strip())
            
    else:
        pattern_count = False # To output a meaningful message to the customer

        for log in file:
            if time in log:
                pattern_count = True
                tmp.append(log.strip())

        if pattern_count == False: # That is, it there was no match at all, because the file is empty, write this to tmp
            tmp = "Pattern not found"

    return tmp

# Filter logs based on keyword(s)
def parse_by_key(file, keys):
    tmp = []

    if len(keys) > 1: # For filtering logs based on more than one keyword
        if "and" in keys and "or" in keys: # To avoid mixing up operatiors
            raise BothOperatorsError("You can't use both AND and OR operators at the same time")
        elif "and" in keys: # For AND filtering
            tmp = and_filter(file, remove_operator(keys))
        elif "or" in keys: # For OR filtering
            tmp = or_filter(file, remove_operator(keys))
        else: # Error out if there's more than one keyword but no filtering operators
            raise NoOperatorError("You didn't specify either AND or OR operators")

    elif len(keys) == 1: # Filter based on a single keyword
        for log in file:
            if keys[0] in log: # As it is a list, but as we know it only has one element, access index zero to use it as the filter
                tmp.append(log.strip())
    
    if len(tmp) == 0: # Again, if tmp is empty, this message specifies that the pattern wasn't found
        tmp.append("Pattern not found")

    return tmp

# These removes all "and" and/or "or" keywords for proper filtering
def remove_operator(keys):
    tmp = []

    for key in keys:
        key = key.lower()

        if key == "and" or key == "or": # That is, if the element in the -k list is either, it will be popped out of the list
            continue
        else:
            tmp.append(key)

    return tmp

# Filter based on AND logic
def and_filter(file, keys):
    tmp = []

    for log in file:
        if all([key in log for key in keys]): # Only if ALL keys within the key list are in the log will the log be included in the tmp list
            tmp.append(log.strip())

    return tmp

# Filter based on OR logic
def or_filter(file, keys):
    tmp = []

    for log in file:
        for key in keys: # iterate over each key of the keys list
            if key in log: # if this current key is on the log, include the log in the tmp list
                tmp.append(log.strip())

    return tmp

# Restore all lowered filtered logs to their original casing
def restore_logs(file, real_file):
    tmp = []

    for lower_log in file: # iterate over each lowered log in the current file
        for log in real_file: # iterate over all logs in the original file for the current lowered log
            if lower_log in log.lower(): # if the lowered log is equal to the lowered version of the original log, include the original log in tmp
                tmp.append(log.strip())

    return tmp

# If an error occurs, generate an error file with the detail of the error and the stacktrace for debugging
def log_error(error, args):
    date = datetime.datetime.now().strftime("%Y-%m-%d") # Get the current date

    log_path = pathlib.Path.home() / "Desktop" / f"{date}_logc_error.log" # Generate the error file in the user's Desktop

    logger = logging.getLogger("logc_logger") # Set the logger
    logger.setLevel(logging.ERROR) # Set the severity to error

    if not logger.handlers: # Handle more than one error at the same time
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s | %(levelname)s: %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    logger.error(f"Execution failed\n\nUser input: {args}\n\nError: {error}\n\n", exc_info=True) # Generate an error file

    return f'An error has occurred!\nError: {error}\nCheck the {log_path} file for technical details and check the official guide ("logc -h") for a guide on how to use this program.' # Return a more user-friendly error message to know where to locate the error file

# Generate a new file with all the filtered files
def write_new_file(log_files, destination, file_names):
    with open(pathlib.Path(destination), "a") as new_file: # Open the destination as a new file and in append mode to support more than one file
        
        for i in range(len(log_files)): # Iterate over a range instead of the file itself to have an index for both the file itself and the file title
            
            new_file.write(f'Log file: "{file_names[i]}"\n\n') # Write the title of the current file
            
            if log_files[i] == "Pattern not found": # In case of just filtering with -t, to prevent this message from displaying in a weird way
                new_file.write(f"{log_files[i]}\n")

            else:
                for log in log_files[i]: # Iterate over each log in the current file and append it to the output file
                    new_file.write(f"{log}\n")

            new_file.write("\n") # Write a newline after each line for better readability

    return f"Successfully generated: {destination}"


if __name__ == "__main__":
    main()