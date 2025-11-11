# linuxmuster-base7 Test Suite

## Overview

This directory contains test scripts for validating the refactored linuxmuster-base7 Python package structure and CLI tools.

## Test Scripts

### test_setup_cli.sh

Comprehensive test suite for `linuxmuster-setup` command-line interface.

**Tests included:**
1. Help message display (`--help`, `-h`)
2. Invalid option handling
3. Individual parameters:
   - `--servername` / `-n`
   - `--domainname` / `-d`
   - `--adminpw` / `-a`
   - `--schoolname` / `-e`
   - `--location` / `-l`
   - `--country` / `-z`
   - `--state` / `-v`
   - `--dhcprange` / `-r`
4. Combined parameters
5. Config file parameter (`--config` / `-c`)
6. Unattended mode (`--unattended` / `-u`)
7. Skip firewall option (`--skip-fw` / `-s`)
8. Long option names
9. Special characters in passwords
10. Module loading from Python package
11. Entry point installation verification
12. Python package structure validation
13. Functions module accessibility
14. Error handling (invalid config files)

**Total:** 20 automated tests

## Usage

### Run all tests:
```bash
sudo ./tests/test_setup_cli.sh
```

### Requirements:
- linuxmuster-base7 package installed
- linuxmuster-common package installed
- Root privileges (for writing to /var/cache/linuxmuster/)

## Test Output

The script provides colored output:
- 🟢 **Green**: Passed tests
- 🔴 **Red**: Failed tests
- 🟡 **Yellow**: Test descriptions

Example output:
```
==========================================
linuxmuster-setup CLI Test Suite
==========================================
Testing refactored Python package structure
Date: Mon Nov 11 12:00:00 CET 2025
==========================================

[TEST 1] Testing --help option
✓ PASS: Help message displayed correctly

[TEST 2] Testing -h option
✓ PASS: Short help option works

...

==========================================
Test Summary
==========================================
Total tests run: 20
Passed: 20
Failed: 0
==========================================

All tests passed!
```

## Exit Codes

- `0`: All tests passed
- `1`: One or more tests failed

## Adding New Tests

To add a new test:

1. Create a test function following the pattern:
```bash
test_new_feature() {
    ((TESTS_RUN++))
    print_test "Testing new feature"

    if condition; then
        print_pass "New feature works"
    else
        print_fail "New feature failed"
    fi
}
```

2. Add the function call to the `main()` function

3. Update this README with test description

## Integration with CI/CD

The test script can be integrated into CI/CD pipelines:

```bash
# In your CI/CD script
cd /path/to/linuxmuster-base7
sudo ./tests/test_setup_cli.sh || exit 1
```

## Notes

- Tests that modify `/var/cache/linuxmuster/custom.ini` will backup and restore the file
- Some tests may require network access or specific system configuration
- Tests are designed to be non-destructive and safe to run on development systems
- For production testing, use a dedicated test environment

## Troubleshooting

### Test fails with "command not found"
Ensure linuxmuster-base7 package is properly installed:
```bash
which linuxmuster-setup
python3 -c "import linuxmuster_base7"
```

### Permission denied errors
Run with sudo:
```bash
sudo ./tests/test_setup_cli.sh
```

### Module import errors
Verify Python package installation:
```bash
python3 -c "import linuxmuster_base7; print(linuxmuster_base7.__version__)"
```

## Future Enhancements

Planned additions:
- Tests for other CLI tools (import-devices, import-subnets, etc.)
- Integration tests with mock Samba/LDAP environment
- Performance benchmarks
- Code coverage reporting
- Automated regression testing

## Contributing

When adding new features to linuxmuster-base7, please:
1. Add corresponding tests to this suite
2. Ensure all existing tests still pass
3. Update this README with new test descriptions
