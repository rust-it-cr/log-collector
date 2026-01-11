from logc_tool.logc import parse_arguments, curate_and_standardize_cli_input
import pytest

# test the basic parameters for the parser work just fine
def test_basic_parsing():
    test_args = ["-s", "test-logs.tgz", "-d", "output.txt", "-f", "chassisd", "-t", "Oct  6 to Oct  8"]
    parsed = parse_arguments(test_args)

    assert parsed.source == "test-logs.tgz"
    assert parsed.destination == "output.txt"
    assert parsed.file == ["chassisd"]
    assert parsed.time == "Oct  6 to Oct  8"
    assert parsed.ignore_case == False

# test the tool needs at least -s, -d, -f, and either -t or any key flag
def test_missing_flag():
    test_args = ["-s", "test-logs.tgz", "-d", "output.txt", "-f", "chassisd"]

    # it exits with the "Please, specify at least -t or -k, or both." message
    with pytest.raises(SystemExit):
        parsed = parse_arguments(test_args)
        curate_and_standardize_cli_input(parsed)

# test the parser rejects mutually exclusive keys
def test_mutually_exclusive_keys():
    test_args = ["-s", "test-logs.tgz", "-d", "output.txt", "-f", "chassisd", "-k", "banana", "-ka", "banana", "apple"]

    with pytest.raises(SystemExit):
        parsed = parse_arguments(test_args)

