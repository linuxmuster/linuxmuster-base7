# linuxmuster-base7 Test Suite

## Overview

This directory contains two complementary test scripts for validating the refactored linuxmuster-base7 Python package structure and CLI tools. The scripts serve different purposes and should both be used in the development and release workflow.

## Comparison of Test Scripts

| Feature | test_setup_cli.sh | test_setup_integration.sh |
|---------|-------------------|---------------------------|
| **Purpose** | CLI parameter validation & unit tests | Full system integration tests |
| **Execution Time** | Fast (seconds) | Slow (minutes per test) |
| **System Impact** | Non-destructive | Modifies system configuration |
| **Test Count** | 20 tests | 6 tests |
| **When to Use** | During development, every commit | Before releases, major merges |
| **Environment** | Any system with package installed | Dedicated test VM only |
| **Snapshot/Restore** | No | Yes (automatic rollback) |
| **Interactive Mode** | No | Yes (menu-driven) |
| **CI/CD Integration** | Suitable for every build | Suitable for nightly/release builds |

## Test Scripts

### test_setup_cli.sh (Unit/CLI Tests)

**Fast, non-destructive test suite** for `linuxmuster-setup` command-line interface.
Tests parameter parsing and basic functionality without modifying the system significantly.

**Purpose:**
- Verify CLI parameter parsing works correctly
- Validate Python package structure and imports
- Test error handling for invalid inputs
- Ensure entry points are properly installed
- Quick feedback during development

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

**Execution time:** ~30 seconds

### test_setup_integration.sh (Integration Tests)

**Comprehensive integration test suite** with system snapshot/restore capability.
Tests full setup execution with automatic rollback between tests.

**Purpose:**
- Validate complete setup workflows end-to-end
- Test user management integration (Sophomorix)
- Verify system configuration changes
- Ensure rollback capability works correctly
- Comprehensive pre-release validation

**Tests included:**
1. Basic setup with minimal parameters
2. Create test users (after basic setup)
3. Full parameter setup (all CLI options)
4. Create test users (after full setup)
5. Config file based setup
6. Create test users (after config file setup)

**Total:** 6 integration tests (3 setup tests + 3 user creation tests)

**Execution time:** ~15-30 minutes (depending on system)

**Features:**
- **Automatic snapshot/restore**: Each test runs in isolation
- **Interactive mode**: Menu-driven testing interface
- **Manual snapshot management**: Create, restore, delete snapshots
- **Live output**: See setup progress in real-time
- **Graceful error handling**: Tests continue even if prerequisites are missing

## Usage

### test_setup_cli.sh (Non-destructive tests)

Run all CLI tests:
```bash
sudo ./tests/test_setup_cli.sh
```

**Requirements:**
- linuxmuster-base7 package installed
- linuxmuster-common package installed
- Root privileges (for writing to /var/cache/linuxmuster/)

### test_setup_integration.sh (Integration tests with snapshots)

#### Automatic mode
Run all 6 tests sequentially with automatic snapshot/restore:
```bash
sudo ./tests/test_setup_integration.sh
```

This will:
1. Create a baseline snapshot
2. Run all 6 tests (each test creates its own snapshot before execution)
3. Restore system state after each test
4. Clean up old snapshots (keep last 5)
5. Restore baseline state at the end

#### Run specific tests
Run single or multiple tests by number:
```bash
# Run single test (no restore after)
sudo ./tests/test_setup_integration.sh -t 1

# Run multiple tests (no restore after)
sudo ./tests/test_setup_integration.sh -t 1,2,4

# Run test(s) with restore after
sudo ./tests/test_setup_integration.sh -t 2,4 -r baseline
```

**Test numbers:**
- 1 = Basic Setup
- 2 = Full Setup
- 3 = Config File Setup
- 4 = Create Test Users

**Behavior:**
- Before test(s): Automatic snapshot is created (`auto-test-N-TIMESTAMP` or `auto-tests-TIMESTAMP`)
- During tests: Tests run consecutively without restore between them
- After test(s): No restore by default (changes remain), unless `-r <snapshot>` is specified

This allows you to:
- Examine system state after tests complete
- Run specific test combinations
- Control when/if cleanup happens

#### Interactive mode
Menu-driven interface for selective testing and snapshot management:
```bash
sudo ./tests/test_setup_integration.sh --interactive
```

**Interactive menu options:**
1. **Create baseline snapshot** - Create a named snapshot of current system state
2. **Run single test with snapshot** - Choose from:
   - Basic setup
   - Full setup
   - Config file setup
   - Create test users
   - *Option 0: Back to main menu*
3. **Run all tests** - Execute all 6 tests sequentially
4. **List snapshots** - Show all available snapshots with creation dates
5. **Restore specific snapshot** - Select and restore a snapshot by name
   - *Shows snapshot list before prompting*
   - *Enter 0 to go back*
6. **Delete specific snapshot** - Remove a snapshot by name
   - *Shows snapshot list before prompting*
   - *Enter 0 to go back*
7. **Delete all snapshots** - Remove all snapshots (requires confirmation)
8. **Cleanup old snapshots** - Keep only N most recent snapshots
9. **Exit** - Quit interactive mode

**Features:**
- Submenus include "Back" options (press 0)
- "Press Enter to continue" prompts after operations
- Colored section headers for better navigation
- Snapshot list shown before restore/delete operations

#### Command-line snapshot management
For scripting and automation:

```bash
# Create snapshot
sudo ./tests/test_setup_integration.sh --create-snapshot baseline
sudo ./tests/test_setup_integration.sh -c baseline

# List snapshots
sudo ./tests/test_setup_integration.sh --list
sudo ./tests/test_setup_integration.sh -l

# Restore snapshot (standalone, no tests)
sudo ./tests/test_setup_integration.sh --restore baseline
sudo ./tests/test_setup_integration.sh -r baseline

# Delete specific snapshot
sudo ./tests/test_setup_integration.sh --delete baseline
sudo ./tests/test_setup_integration.sh -d baseline

# Delete all snapshots (with confirmation)
sudo ./tests/test_setup_integration.sh --delete-all

# Cleanup old snapshots (keep last 5)
sudo ./tests/test_setup_integration.sh --cleanup 5
```

**Note:** The `-r` option can be used:
- **Standalone**: `-r baseline` - Only restores the snapshot, runs no tests
- **With tests**: `-t 1,2 -r baseline` - Runs tests 1 and 2, then restores the snapshot

#### Common usage scenarios

**Testing without cleanup (examine results):**
```bash
# Run tests and keep changes for inspection
sudo ./tests/test_setup_integration.sh -t 2,4
# Inspect system state...
# Later restore to clean state
sudo ./tests/test_setup_integration.sh -r baseline
```

**Quick test with automatic cleanup:**
```bash
# Create baseline first
sudo ./tests/test_setup_integration.sh -c baseline
# Run tests, then auto-restore
sudo ./tests/test_setup_integration.sh -t 1,2 -r baseline
```

**Iterative testing workflow:**
```bash
# 1. Create initial clean state
sudo ./tests/test_setup_integration.sh -c clean-start

# 2. Run tests, examine results
sudo ./tests/test_setup_integration.sh -t 1,2

# 3. If tests look good, run more tests
sudo ./tests/test_setup_integration.sh -t 3,4

# 4. When done, restore clean state
sudo ./tests/test_setup_integration.sh -r clean-start
```

**Testing changes to specific setup module:**
```bash
# Test only config file setup after code changes
sudo ./tests/test_setup_integration.sh -t 3
# Check results, fix code if needed, restore and repeat
sudo ./tests/test_setup_integration.sh -r baseline
sudo ./tests/test_setup_integration.sh -t 3
```

#### Requirements
- linuxmuster-base7 package installed
- linuxmuster-common package installed
- Root privileges (required for system modifications)
- At least 500MB free space in /tmp (for snapshots)
- For user creation tests: Sophomorix and Samba setup

#### Warning
**Integration tests will modify system configuration!**
Only run in dedicated test environments, **never on production systems**.

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

## Recommended Testing Workflow

### During Development
Run the fast CLI tests after code changes:
```bash
sudo ./tests/test_setup_cli.sh
```
This provides immediate feedback (30 seconds) without system modifications.

### Before Committing
Ensure all CLI tests pass:
```bash
sudo ./tests/test_setup_cli.sh || exit 1
```

### Before Release / Major Merge
Run full integration tests in a test VM:
```bash
# Option 1: Run all tests automatically
sudo ./tests/test_setup_integration.sh

# Option 2: Interactive testing for troubleshooting
sudo ./tests/test_setup_integration.sh --interactive
```

### Integration with CI/CD

**For every commit/PR** (fast feedback):
```bash
# In your CI/CD pipeline
cd /path/to/linuxmuster-base7
sudo ./tests/test_setup_cli.sh || exit 1
```

**For nightly builds / release candidates** (comprehensive validation):
```bash
# In your CI/CD pipeline (requires dedicated test VM)
cd /path/to/linuxmuster-base7
sudo ./tests/test_setup_integration.sh || exit 1
```

**Combined approach**:
```bash
#!/bin/bash
# Run fast tests first
echo "Running CLI tests..."
sudo ./tests/test_setup_cli.sh || exit 1

# Run integration tests only for release branches
if [[ "$BRANCH_NAME" == "master" || "$BRANCH_NAME" == "release/"* ]]; then
    echo "Running integration tests..."
    sudo ./tests/test_setup_integration.sh || exit 1
fi
```

## Notes

- Tests that modify `/var/cache/linuxmuster/custom.ini` will backup and restore the file
- Some tests may require network access or specific system configuration
- Tests are designed to be non-destructive and safe to run on development systems
- For production testing, use a dedicated test environment

## Troubleshooting

### CLI Tests (test_setup_cli.sh)

#### Test fails with "command not found"
Ensure linuxmuster-base7 package is properly installed:
```bash
which linuxmuster-setup
python3 -c "import linuxmuster_base7"
```

#### Permission denied errors
Run with sudo:
```bash
sudo ./tests/test_setup_cli.sh
```

#### Module import errors
Verify Python package installation:
```bash
python3 -c "import linuxmuster_base7; print(linuxmuster_base7.__version__)"
```

### Integration Tests (test_setup_integration.sh)

#### Test hangs or times out
- Tests have a 300-second (5-minute) timeout per operation
- Check system resources (CPU, memory, disk space)
- Review live output to see where it's hanging
- Run in interactive mode to test individual components

#### "Snapshot not found" errors
List available snapshots:
```bash
sudo ./tests/test_setup_integration.sh --list
```
Or clean up and start fresh:
```bash
sudo ./tests/test_setup_integration.sh --delete-all
```

#### "Not enough disk space" for snapshots
Check available space in /tmp:
```bash
df -h /tmp
```
Cleanup old snapshots:
```bash
sudo ./tests/test_setup_integration.sh --cleanup 1
```

#### User creation test fails
This is expected if:
- Samba/LDAP is not fully configured
- Sophomorix is not installed
- No domain controller is available

The test will gracefully skip with a note if prerequisites are missing.

#### Test fails but system state is corrupted
Restore from a previous snapshot:
```bash
sudo ./tests/test_setup_integration.sh --list
sudo ./tests/test_setup_integration.sh --restore <snapshot-name>
```

Or restore from backup if available:
```bash
# The test automatically backs up before each test
# Check /tmp/linuxmuster-snapshots/ for available snapshots
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
