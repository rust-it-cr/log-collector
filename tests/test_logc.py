from logc_tool import logc
import pytest
import re

# Test proper functionality and argument assignment
def test_basic_parsing():
    test_args = ["-s", "test-logs.tgz", "-d", "output.txt", "-f", "chassisd", "-t", "Oct  6 to Oct  8"]

    parsed = logc.parse_args(test_args)

    assert parsed.source == "test-logs.tgz"
    assert parsed.destination == "output.txt"
    assert parsed.file == ["chassisd"]
    assert parsed.time == "Oct  6 to Oct  8"
    assert parsed.ignore_case == False

# Test when the user hasn't specified all required flags
def test_missing_flag():
    test_args = ["-s", "test-logs.tgz", "-d", "output.txt", "-f", "chassisd"]

    with pytest.raises(TypeError):
        logc.parse_args(test_args)

# Test when using both AND and OR operators at the same time
def test_mutually_exclusive_keys():
    test_args = ["-s", "test-logs.tgz", "-d", "output.txt", "-f", "chassisd", "-k", "fpc", "and", "pic", "or", "port"]

    parsed = logc.parse_args(test_args)

    with pytest.raises(logc.BothOperatorsError):
        logc.parse_by_key([], parsed.key)

# Test when the wildcard is malformed or invalid
def test_invalid_wildcard():
    test_args = ["-s", "test-logs.tgz", "-d", "output.txt", "-w", "*", "-k", "fpc"]

    parsed = logc.parse_args(test_args)

    with pytest.raises(re.PatternError):
        logc.get_wildcard_files(parsed.source, parsed.wildcard)

# Test for no operators within args.key
def test_no_operator_for_key():
    test_args = ["-s", "test-logs.tgz", "-d", "output.txt", "-w", "messages", "-k", "fpc", "pic", "port"]

    parsed = logc.parse_args(test_args)

    with pytest.raises(logc.NoOperatorError):
        logc.parse_by_key([], parsed.key)

