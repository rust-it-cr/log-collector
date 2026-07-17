#!/usr/bin/env python3

import argparse
import datetime
import gzip
import logging
import pathlib
import re
import sys
import tarfile


class BothOperatorsError(Exception):
    pass

class InvalidTimeError(Exception):
    pass

class NoFilesError(Exception):
    pass

class NoOperatorError(Exception):
    pass

class UnknownCompressionTypeError(Exception):
    pass


RFC_5424 = r"(\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d)"
BSD_SYSLOG = r"(\w{3,9}  ?\d?\d \d\d:\d\d:\d\d)"


def main():
    try:

        args = parse_args()

        if args.time:
            args.time = convert_time(args.time)

        result_files = []

        for ending in [".tgz", ".tar"]:
            if str(args.source).endswith(ending):
                args.source = decompress_file(args.source, ending)
                break
            else:
                continue
                
        file_paths = compile_paths(args.source)
        filtered_file_paths = filter_paths(file_paths, args.file)

        for path in filtered_file_paths:
            file_lines = read_file(path)

            if args.time and args.key:
                filtered_lines = parse_by_time(file_lines, args.time)
                filtered_lines = parse_by_key(filtered_lines, args.key)
            elif args.time:
                filtered_lines = parse_by_time(file_lines, args.time)
            elif args.key:
                filtered_lines = parse_by_key(file_lines, args.key)
                
            result_files.append({"name": f"Log file: '{path}'", "content": filtered_lines})
            
        result = write_file(result_files, args.destination)
        print(result)
        sys.exit(0)

    except (BothOperatorsError, InvalidTimeError, UnboundLocalError, NoOperatorError, NoFilesError) as e:
        sys.exit(f"Failure: {e}. Please correct your input.")    

    except EOFError as e:
        sys.exit(f"Failure: {e}. Please check that the source file isn't corrupted.")

    except (FileNotFoundError, KeyError) as e:
        sys.exit(f"Failure: {e}. Please verify that the files you're matching actually exist.")

    except KeyboardInterrupt:
        sys.exit("Log collection cancelled.")

    except PermissionError as e:
        sys.exit(f"Failure: {e}. You don't have permission to parse this file or directory.")

    except TypeError as e:
        sys.exit(f"Failure: {e}. Please check that you're typing out all required arguments.")

    except UnknownCompressionTypeError as e:
        sys.exit(f"Failure: {e}. Please uncompress the directory and run the utility again on the uncompressed directory.")

    except Exception as e:
        exit_status = log_error(e, args)
        sys.exit(exit_status)


def parse_args(args=None):
    parser_message = "This tool takes a directory with log files therein and filters logs based on keyword/timestamp, generating a single file with matching results. You should wrap all arguments around quotation marks to avoid readability errors."
    parser_epilogue = "If you want more information about my work, please consider visiting my GitHub profile: https://github.com/rust-it-cr"

    source_help = "Source path for the file that contains all log files you want to parse. Ideally, this should be an absolute path."
    time_help = "Specify the timestamp or timerange to be used to collect logs from all specified log files. Time format: YYYY-MM-DDThh:mm:ss[ to YYYY-MM-DDThh:mm:ss]."
    destination_help = "Destination path for the output text file that will contain all matching logs. Ideally, this should be an absolute path."
    key_help = "Specific a keyword or collection thereof to match on the selected log files. You can select a single keyword or a chain thereof with either AND or OR operators."
    file_help = "Specify a filename or a regex to match on files you want to parse."

    parser = argparse.ArgumentParser(prog="logc", description=parser_message, epilog=parser_epilogue)

    parser.add_argument("-s", "--source", help=source_help)
    parser.add_argument("-d", "--destination", help=destination_help)
    parser.add_argument("-t", "--time", help=time_help, nargs="+")
    parser.add_argument("-k", "--key", help=key_help, nargs="+")
    parser.add_argument("-f", "--file", help=file_help, nargs="+")
    
    args = parser.parse_args(args)

    if not args.key and not args.time:
        raise TypeError("You didn't specify at least one filtering parameter")

    return args


def convert_time(user_time):
    new_user_time = []

    for item in user_time:
        if " to " in item:
            items = item.split(" to ")
            dt = [datetime.datetime.fromisoformat(subitem) for subitem in items if re.match(RFC_5424, subitem)]
            new_user_time.append(dt)
        elif re.match(RFC_5424, item):
            dt = datetime.datetime.fromisoformat(item)
            new_user_time.append(dt)
        else:
            raise InvalidTimeError("The time you specified isn't valid")

    return(new_user_time)


def decompress_file(file, extension):
    match extension:

        case ".tgz" | ".tar":
            with tarfile.open(file) as new_file:
                new_path = f"{file}-decompressed"
                new_file.extractall(path=new_path, filter="fully_trusted")
                return new_path

        case _:
            raise UnknownCompressionTypeError("This compression type isn't supported")


def compile_paths(file, paths=[]):
    file = pathlib.Path(file)

    if file.is_dir():
        for item in file.iterdir():
            compile_paths(item)
    else:
        paths.append(file)

    return paths


def filter_paths(paths, filters):
    selected_paths = []

    for path in paths:
        for filter in filters:
            if re.search(filter, str(path)):
                selected_paths.append(path)

    if not selected_paths:
        raise NoFilesError("Your file selection didn't match any files")
    else:
        return selected_paths


def read_file(path):
    if str(path).endswith(".gz"):
         with gzip.open(path, "rt", encoding="latin1") as file:
            lines = file.readlines()
    else:
        with open(path, encoding="latin-1") as file:
            lines = file.readlines()

    return lines


def parse_by_time(lines, user_time):
    filtered_lines = []

    for line in lines:
        try:
            if match := re.search(RFC_5424, line):
                line_time = datetime.datetime.fromisoformat(str(match.group(0)))
            elif match := re.search(BSD_SYSLOG, line, re.IGNORECASE):
                match = f"{str(datetime.datetime.today().year)} {str(match.group(0))}" # This is the biggest limitation: assuming the current year will break the tool at some point: year transition and leap years break this
                line_time = datetime.datetime.strptime(match, "%Y %b %d %H:%M:%S")
        except ValueError:
            pass

        for filter in user_time:
            if isinstance(filter, list):
                start = filter[0]
                finish = filter[1]
                
                try:
                    if start <= line_time <= finish:
                        filtered_lines.append(line.strip())
                    else:
                        continue
                except UnboundLocalError:
                    pass
            else:
                if filter == line_time:
                    filtered_lines.append(line.strip())
                else:
                    continue

    return filtered_lines


def parse_by_key(lines, keys):
    filter_type, filtered_keys = None, []

    if "and" in keys and "or" in keys:
        raise BothOperatorsError("You can only use one time of filtering at a time: AND or OR")
    elif "and" not in keys and "or" not in keys and len(keys) > 1:
        raise NoOperatorError("You didn't specify either AND or OR operators")
    else:
        for key in keys:
            if key == "and" or key == "or":
                filter_type = key
            else:
                filtered_keys.append(key)

    filtered_lines = []

    for line in lines:
        if not filter_type:
            if re.search(key, line, re.IGNORECASE):
                filtered_lines.append(line.strip())
        elif filter_type == "and":
            if all([re.search(key, line, re.IGNORECASE) for key in filtered_keys]):
                filtered_lines.append(line.strip())
        elif filter_type == "or":
            for key in filtered_keys:
                if re.search(key, line, re.IGNORECASE):
                    filtered_lines.append(line.strip())

    return filtered_lines


def write_file(files, destination):
    with open(pathlib.Path(destination), "a", encoding="latin-1") as new_file:
        for file in files:
            new_file.write(f"{file["name"]}\n\n")
            if not file["content"]:
                new_file.write("Pattern not found\n")
            else:
                for line in file["content"]:
                    new_file.write(f"{line}\n")
            new_file.write("\n")

    return f"{destination} has been successfully generated!"


def log_error(error, args):
    logger = logging.getLogger("logc_logger")
    logger.setLevel(logging.ERROR)

    logger.error(f"An unknown error has occurred!\n\nUser input: {args}\n\nError: {error}\n\n", exc_info=True)

    print("\nPlease share this entire error message with the developer of this tool for further debugging.")
    
    return 1


if __name__ == "__main__":
    main()