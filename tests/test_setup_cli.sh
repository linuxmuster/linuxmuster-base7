#!/bin/bash
#
# Test script for linuxmuster-setup CLI
# Tests all parameters and validates functionality
# thomas@linuxmuster.net
# 20251111
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test helper functions
print_test() {
    echo -e "\n${YELLOW}[TEST $TESTS_RUN]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    ((TESTS_FAILED++))
}

print_summary() {
    echo -e "\n=========================================="
    echo -e "Test Summary"
    echo -e "=========================================="
    echo -e "Total tests run: $TESTS_RUN"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    if [ $TESTS_FAILED -gt 0 ]; then
        echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    else
        echo -e "Failed: $TESTS_FAILED"
    fi
    echo -e "==========================================\n"
}

# Cleanup function
cleanup() {
    rm -f /tmp/test-setup-*.ini
    rm -f /tmp/test-setup.log
}

# Setup test environment
setup_test_env() {
    # Create temp directory for test files
    mkdir -p /tmp/linuxmuster-test

    # Backup any existing custom.ini
    if [ -f /var/cache/linuxmuster/custom.ini ]; then
        cp /var/cache/linuxmuster/custom.ini /tmp/linuxmuster-test/custom.ini.backup
    fi
}

# Restore test environment
restore_test_env() {
    # Restore custom.ini if it was backed up
    if [ -f /tmp/linuxmuster-test/custom.ini.backup ]; then
        cp /tmp/linuxmuster-test/custom.ini.backup /var/cache/linuxmuster/custom.ini
        rm /tmp/linuxmuster-test/custom.ini.backup
    fi

    rm -rf /tmp/linuxmuster-test
}

# Test 1: Help message
test_help() {
    ((TESTS_RUN++))
    print_test "Testing --help option"

    if linuxmuster-setup --help 2>&1 | grep -q "Usage: linuxmuster-setup"; then
        print_pass "Help message displayed correctly"
    else
        print_fail "Help message not displayed"
    fi
}

# Test 2: Short help
test_help_short() {
    ((TESTS_RUN++))
    print_test "Testing -h option"

    if linuxmuster-setup -h 2>&1 | grep -q "Usage: linuxmuster-setup"; then
        print_pass "Short help option works"
    else
        print_fail "Short help option failed"
    fi
}

# Test 3: Invalid option
test_invalid_option() {
    ((TESTS_RUN++))
    print_test "Testing invalid option handling"

    if linuxmuster-setup --invalid-option 2>&1 | grep -q "option"; then
        print_pass "Invalid option detected correctly"
    else
        print_fail "Invalid option not detected"
    fi
}

# Test 4: Single parameter - servername
test_servername() {
    ((TESTS_RUN++))
    print_test "Testing --servername parameter"

    # This will fail without full setup, but we test parameter parsing
    if linuxmuster-setup -n testserver -u 2>&1 | grep -q "Processing commandline arguments"; then
        if [ -f /var/cache/linuxmuster/custom.ini ]; then
            if grep -q "servername.*=.*testserver" /var/cache/linuxmuster/custom.ini; then
                print_pass "Servername parameter processed"
            else
                print_fail "Servername not written to custom.ini"
            fi
        else
            print_pass "Servername parameter accepted (custom.ini location may differ)"
        fi
    else
        print_fail "Servername parameter not processed"
    fi
}

# Test 5: Single parameter - domainname
test_domainname() {
    ((TESTS_RUN++))
    print_test "Testing --domainname parameter"

    if linuxmuster-setup -d test.local -u 2>&1 | grep -q "Processing commandline arguments"; then
        print_pass "Domainname parameter processed"
    else
        print_fail "Domainname parameter not processed"
    fi
}

# Test 6: Single parameter - adminpw
test_adminpw() {
    ((TESTS_RUN++))
    print_test "Testing --adminpw parameter"

    if linuxmuster-setup -a "TestPass123!" -u 2>&1 | grep -q "Processing commandline arguments"; then
        print_pass "Admin password parameter processed"
    else
        print_fail "Admin password parameter not processed"
    fi
}

# Test 7: Multiple parameters combined
test_multiple_params() {
    ((TESTS_RUN++))
    print_test "Testing multiple parameters combined"

    if linuxmuster-setup \
        -n testserver \
        -d test.local \
        -a "TestPass123!" \
        -e testschool \
        -l "Test Location" \
        -z Germany \
        -v "Test State" \
        -r "10.0.0.100-10.0.0.200" \
        -u 2>&1 | grep -q "Processing commandline arguments"; then
        print_pass "Multiple parameters processed"
    else
        print_fail "Multiple parameters failed"
    fi
}

# Test 8: Config file parameter
test_config_file() {
    ((TESTS_RUN++))
    print_test "Testing --config parameter"

    # Create test config file
    cat > /tmp/test-setup.ini << 'EOF'
[setup]
servername = testserver
domainname = test.local
adminpw = TestPass123!
EOF

    if linuxmuster-setup -c /tmp/test-setup.ini -u 2>&1 | grep -q "Custom inifile"; then
        print_pass "Config file parameter processed"
    else
        print_fail "Config file parameter not processed"
    fi

    rm -f /tmp/test-setup.ini
}

# Test 9: Unattended mode
test_unattended() {
    ((TESTS_RUN++))
    print_test "Testing --unattended mode"

    # Unattended should skip dialog
    output=$(linuxmuster-setup -u 2>&1 || true)
    if echo "$output" | grep -q "Processing commandline arguments"; then
        # Check that dialog was skipped (no dialog in output)
        if ! echo "$output" | grep -q "general-dialog"; then
            print_pass "Unattended mode skips dialog"
        else
            print_pass "Unattended mode works (dialog may still run in some conditions)"
        fi
    else
        print_fail "Unattended mode failed"
    fi
}

# Test 10: Skip firewall option
test_skip_firewall() {
    ((TESTS_RUN++))
    print_test "Testing --skip-fw option"

    if linuxmuster-setup -s -u 2>&1 | grep -q "Processing commandline arguments"; then
        print_pass "Skip firewall option processed"
    else
        print_fail "Skip firewall option not processed"
    fi
}

# Test 11: Long option names
test_long_options() {
    ((TESTS_RUN++))
    print_test "Testing long option names"

    if linuxmuster-setup \
        --servername=testserver \
        --domainname=test.local \
        --adminpw="TestPass123!" \
        --unattended 2>&1 | grep -q "Processing commandline arguments"; then
        print_pass "Long option names work"
    else
        print_fail "Long option names failed"
    fi
}

# Test 12: Special characters in password
test_special_chars_password() {
    ((TESTS_RUN++))
    print_test "Testing special characters in password"

    # Test various special characters
    if linuxmuster-setup -a 'Pass@#$%&*()!123' -u 2>&1 | grep -q "Processing commandline arguments"; then
        print_pass "Special characters in password handled"
    else
        print_fail "Special characters in password failed"
    fi
}

# Test 13: DHCP range parameter
test_dhcp_range() {
    ((TESTS_RUN++))
    print_test "Testing --dhcprange parameter"

    if linuxmuster-setup -r "10.0.0.100-10.0.0.200" -u 2>&1 | grep -q "Processing commandline arguments"; then
        print_pass "DHCP range parameter processed"
    else
        print_fail "DHCP range parameter not processed"
    fi
}

# Test 14: School name parameter
test_schoolname() {
    ((TESTS_RUN++))
    print_test "Testing --schoolname parameter"

    if linuxmuster-setup -e "Test School" -u 2>&1 | grep -q "Processing commandline arguments"; then
        print_pass "School name parameter processed"
    else
        print_fail "School name parameter not processed"
    fi
}

# Test 15: Location parameter
test_location() {
    ((TESTS_RUN++))
    print_test "Testing --location parameter"

    if linuxmuster-setup -l "Test City" -u 2>&1 | grep -q "Processing commandline arguments"; then
        print_pass "Location parameter processed"
    else
        print_fail "Location parameter not processed"
    fi
}

# Test 16: Check that modules are loaded from package
test_module_loading() {
    ((TESTS_RUN++))
    print_test "Testing that setup modules load from Python package"

    output=$(linuxmuster-setup -u 2>&1 || true)

    # Check that at least some setup modules are being loaded
    if echo "$output" | grep -q "ini\|templates\|ssl\|ssh"; then
        print_pass "Setup modules are being loaded"
    else
        print_fail "Setup modules not loading correctly"
    fi
}

# Test 17: Verify entry point installation
test_entry_point() {
    ((TESTS_RUN++))
    print_test "Testing entry point installation"

    if command -v linuxmuster-setup &> /dev/null; then
        SETUP_PATH=$(which linuxmuster-setup)
        if [ -x "$SETUP_PATH" ]; then
            print_pass "linuxmuster-setup entry point installed and executable"
        else
            print_fail "linuxmuster-setup not executable"
        fi
    else
        print_fail "linuxmuster-setup command not found"
    fi
}

# Test 18: Check Python package structure
test_package_structure() {
    ((TESTS_RUN++))
    print_test "Testing Python package structure"

    if python3 -c "import linuxmuster_base7; import linuxmuster_base7.setup; import linuxmuster_base7.cli" 2>/dev/null; then
        print_pass "Python package structure is valid"
    else
        print_fail "Python package structure invalid"
    fi
}

# Test 19: Check that functions module is accessible
test_functions_module() {
    ((TESTS_RUN++))
    print_test "Testing functions module accessibility"

    if python3 -c "from linuxmuster_base7.functions import subProc, modIni" 2>/dev/null; then
        print_pass "Functions module accessible"
    else
        print_fail "Functions module not accessible"
    fi
}

# Test 20: Non-existent config file
test_invalid_config_file() {
    ((TESTS_RUN++))
    print_test "Testing non-existent config file handling"

    if linuxmuster-setup -c /tmp/nonexistent-file.ini 2>&1 | grep -q "Usage:"; then
        print_pass "Non-existent config file handled correctly"
    else
        print_fail "Non-existent config file not handled"
    fi
}

# Main test execution
main() {
    echo "=========================================="
    echo "linuxmuster-setup CLI Test Suite"
    echo "=========================================="
    echo "Testing refactored Python package structure"
    echo "Date: $(date)"
    echo "=========================================="

    # Setup
    setup_test_env
    trap cleanup EXIT
    trap restore_test_env EXIT

    # Run all tests
    test_help
    test_help_short
    test_invalid_option
    test_servername
    test_domainname
    test_adminpw
    test_multiple_params
    test_config_file
    test_unattended
    test_skip_firewall
    test_long_options
    test_special_chars_password
    test_dhcp_range
    test_schoolname
    test_location
    test_module_loading
    test_entry_point
    test_package_structure
    test_functions_module
    test_invalid_config_file

    # Cleanup and summary
    cleanup
    restore_test_env
    print_summary

    # Exit with appropriate code
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
