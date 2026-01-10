#!/usr/bin/env python3

import argparse
import datetime
import getpass
import gzip
import io
import logging
import pathlib
import re
import sys
import tarfile

# create a custom argparse class to have all three flags pointing to the same dest while being able to differentiate them by their "type" (i.e., name)
class KFlagAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)

        flag_type = option_string.lstrip("-")
        setattr(namespace, f"{self.dest}_type", flag_type)

# call the principal functions to curate and standardize input from the command line, and then to filter and store logs based off of the specified time and/or key
def main():
    try:
        args = parse_arguments()
        curate_and_standardize_cli_input(args)
        parse_logs_and_create_file(args)

    except AttributeError:
        sys.exit("You must specify at least the following flags and its values for the script to work: -s, -d, -f, and either -t, -k, or both.")
    except EOFError:
        sys.exit("An output file couldn't be generated. Check if the .tgz file is corrupted or any file therein.")
    except FileNotFoundError or KeyError:
        sys.exit("Please, specify existent and valid files. No output file will be produced unless the files you specify really exist.")
    except TypeError:
        sys.exit("Please, check the correctness of your arguments.")
    except ValueError:
        sys.exit("Either of the specified timestamps (or both) don't exist within the file.")
    except Exception as error:
        log_error(error)
        sys.exit(f'An unknown error has ocurred. Open the "error.log" file in your Desktop directory to better understand what went wrong.')

    else:
        print(f"{args.destination} has been successfully created!")
        sys.exit(0)

# initialize a parser object with its arguments to fetch user input from the command-line
def parse_arguments(args=None):
    # create PARSER object with its flags: --source, --time, --file, --destination, and --key
    PARSER = argparse.ArgumentParser(description="This tool takes a Junos-like .tgz file with logs and generates a .txt file from the specified log files therein from a specific timestamp/time range or keyword/keylist. All arguments should be wrapped around quotation marks.")

    PARSER.add_argument("-s", "--source", help="source path for the compressed file that contains the log files to be parsed. Must end in .tgz and be an absolute path.")
    PARSER.add_argument("-t", "--time", help='specify the timestamp the parser should use to collect logs from all specified files. Time format: "<month> <day>[ <HH>[:<MM>[:<SS>]]][ to <month> <day> [<HH>[:<MM>[:<SS>]]]]" or "<YYYY>-<MM>-<DD>[T<HH>[:<MM>[:<SS>]]][ to <YYYY>-<MM>-<DD>[T<HH>[:<MM>[:<SS>]]]]". Only one format supported at a time (i.e., BSD or sd-syslog).')
    PARSER.add_argument("-f", "--file", help="specify one or more files inside the .tgz file for their logs to be parsed and extracted into the output file. You can only specify a timestamp and not a time range if parsing more than one file.", nargs="+")
    PARSER.add_argument("-i", "--ignore_case", help="run a case-insensitive match on the selected files. It can only be used when using any key parameter. It does not take any arguments.", action="store_true")
    PARSER.add_argument("-d", "--destination", help="destination path for the output text file that will contain all specified logs. Must end in .txt and be an absolute path.")

    # create a mutually exclusive group for a single key, an AND key group, or an OR key group
    KEY_GROUP = PARSER.add_mutually_exclusive_group()

    KEY_GROUP.add_argument("-k", "--key", action=KFlagAction, dest="key", help="specify a keyword/keyphrase to match on the selected log files")
    KEY_GROUP.add_argument("-ka", "--keyAND", action=KFlagAction, dest="key", help="a logical AND extension of -k. It takes two or more arguments.", nargs="+")
    KEY_GROUP.add_argument("-ko", "--keyOR", action=KFlagAction, dest="key", help="a logical OR extension of -k. It takes two or more arguments.", nargs="+")

    # parse the arguments in the PARSER object to be usable by the script
    return PARSER.parse_args(args)

# check that user input at the command line is coherent
def curate_and_standardize_cli_input(args):
    if not args.time and not args.key:
        sys.exit("Please, specify at least -t or -k, or both.")
    elif not args.source.endswith(".tgz"):
        sys.exit("Source file must be a .tgz file.")
    elif not args.destination.endswith(".txt"):
        sys.exit("Destination file must be a .txt file.")
    elif args.time and not re.search(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)  ?\d?\d( \d\d(:\d\d(:\d\d)?)?)?( to (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)  ?\d?\d( \d\d(:\d\d(:\d\d)?)?)?)?$", args.time) and not re.search(r"\d\d\d\d-\d\d-\d\d(T\d\d(:\d\d(:\d\d)?)?)?( to \d\d\d\d-\d\d-\d\d(T\d\d(:\d\d(:\d\d)?)?)?)?", args.time):
        sys.exit("Incorrect time format.")
    elif len(args.file) > 1 and args.time and " to " in args.time:
        sys.exit("Using a time range is only supported with one file at a time.")
    elif args.key and args.key_type == "ka" and len(args.key) < 2:
        sys.exit("-ka requires two or more arguments.")
    elif args.key and args.key_type == "ko" and len(args.key) < 2:
        sys.exit("-ko requires two or more arguments.")
    elif args.ignore_case and not args.key:
        sys.exit("You can only perform a case-insensitive search when any key parameter is present.")
    else:
        return

# decompress the .tgz file and parse according to files specified in --file; if a .gz file, decompress it an parse it appropriately
def parse_logs_and_create_file(args):
    with tarfile.open(pathlib.Path(args.source)) as tgz:
        
        for file in args.file:
            
            collector = tgz.extractfile(f"var/log/{file}")
            
            if str(file).endswith(".gz"):
                with gzip.open(collector, "rt") as gz_collector:
                    parsed_logs = filter_logs(gz_collector.readlines())
            else:
                collector = io.TextIOWrapper(collector, encoding="latin1")
                parsed_logs = filter_logs(collector.readlines(), args)
            
            with open(pathlib.Path(args.destination), "a", encoding="utf-8") as new_file:
                new_file.write(f'Log file: "{file}"\n\n')
                for log in parsed_logs:
                    new_file.write(str(f"{log}\n"))
                new_file.write("\n")

    return

# filter and store logs based off of the specified parameters
def filter_logs(logs, args):
    if args.time and args.key:
        tmp = filter_by_parameter(logs, args.time)

        if args.key_type == "ka":
            tmp = filter_by_multiple_keys_AND(tmp, args.key)
        elif args.key_type == "ko":
            tmp = filter_by_multiple_keys_OR(tmp, args.key)
        else:
            if args.ignore_case:
                tmp = [item for item in tmp if str(args.key).lower() in str(item).lower()]
            else:
                tmp = [item for item in tmp if args.key in item]
        
        if len(tmp) == 0:
            tmp = ["Pattern not found"]

    elif args.time and not args.key:
        tmp = filter_by_parameter(logs, args.time, args)
        if len(tmp) == 0:
            tmp = ["Pattern not found"]

    elif args.key and not args.time:
        if args.key_type == "ka":
            tmp = filter_by_multiple_keys_AND(logs, args.key, args)
        elif args.key_type == "ko":
            tmp = filter_by_multiple_keys_OR(logs, args.key, args)
        else:
            tmp = filter_by_parameter(logs, args.key)
        
        if len(tmp) == 0:
            tmp = ["Pattern not found"]
        
    return tmp

# filter based off of time or key
def filter_by_parameter(logs, arg_parameter, args):
    tmp = []

    if " to " in arg_parameter and arg_parameter == args.time:
        inside_range = False
        ranges = arg_parameter.split(" to ")

        check_bounds(logs, ranges)

        for log in logs:
            if str(ranges[0]) in str(log):
                inside_range = True
                tmp.append(log.strip())
            if inside_range:
                tmp.append(log.strip())
            if str(ranges[1]) in str(log):
                inside_range = False
                tmp.append(log.strip())
        
    else:
        pattern_count = False

        if args.ignore_case and arg_parameter == args.key:
            for log in logs:
                if str(arg_parameter).lower() in str(log).lower():
                    pattern_count = True
                    tmp.append(log.strip())
        else:
            for log in logs:
                if str(arg_parameter) in str(log):
                    pattern_count = True
                    tmp.append(log.strip())
        
        if pattern_count == False:
            tmp = ["Pattern not found"]

    return tmp

# check if lower and upper bounds really exist in the specified file
def check_bounds(logs, ranges):
    range_counter = 0

    for log in logs:
        if str(ranges[0]) in str(log):
            range_counter += 1
            break

    for log in logs:
        if str(ranges[1]) in str(log):
            range_counter += 1
            break

    if range_counter != 2:
        raise ValueError("Time range doesn't exist in the present file.")
    else:
        return

# match the log if it contains ALL keys within ARGS.key (AND matching)
def filter_by_multiple_keys_AND(logs, keys, args):
    tmp = []

    if args.ignore_case:
        for log in logs:
            if all([str(key).lower() in str(log).lower() for key in keys]):
                tmp.append(log.strip())
    else:
        for log in logs:
            if all([key in log for key in keys]):
                tmp.append(log.strip())

    return tmp

# match the log if it contains at least one of the keys within ARGS.key (OR matching)
def filter_by_multiple_keys_OR(logs, keys, args):
    tmp = []

    if args.ignore_case:
        for log in logs:
            for key in keys:
                if str(key).lower() in str(log).lower():
                    tmp.append(log.strip())
    else:
        for log in logs:
            for key in keys:
                if key in log:
                    tmp.append(log.strip())

    return tmp

# use a logging object to log unkwown errors for debugging and troubleshooting into a file called "error.log", always found in the user's desktop
def log_error(error):
    username = getpass.getuser()
    date = datetime.datetime.now().strftime("%Y-%m-%d")

    log_path = pathlib.Path.home() / "Desktop" / f"{username}_{date}_error.log"

    logging.basicConfig(
            filename=log_path,
            level=logging.ERROR,
            format="%(asctime)s | %(levelname)s: %(message)s"
        )
    
    logging.error(f"{error}", exc_info=True)


if __name__ == "__main__":
    main()