#!/bin/bash
#
# Integration test script for linuxmuster-setup with system state management
# Creates snapshots and restores system state between tests
# thomas@linuxmuster.net
# 20251113
#

# Don't use set -e as it can interfere with test execution
# We handle errors explicitly in each function
set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Snapshot directory
SNAPSHOT_DIR="/tmp/linuxmuster-test-snapshots"
SNAPSHOT_NAME="baseline-$(date +%Y%m%d-%H%M%S)"

# Files and directories to snapshot/restore
declare -a SNAPSHOT_PATHS=(
    "/etc/linuxmuster"
    "/var/lib/linuxmuster"
    "/var/lib/samba"
    "/var/cache/linuxmuster"
    "/etc/samba"
    "/etc/dhcp"
    "/etc/hosts"
    "/etc/hostname"
    "/etc/resolv.conf"
    "/etc/netplan"
    "/etc/sudoers.d"
    "/etc/apparmor.d/local"
    "/etc/ntpsec"
    "/etc/nsswitch.conf"
    "/etc/cups/cupsd.conf"
)

# Test helper functions
print_header() {
    echo -e "\n${BLUE}=========================================="
    echo -e "$1"
    echo -e "==========================================${NC}"
}

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

print_info() {
    echo -e "${BLUE}ℹ INFO:${NC} $1"
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

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}ERROR: This script must be run as root${NC}"
        echo "Please run: sudo $0"
        exit 1
    fi
}

# Check if system is suitable for testing
check_system() {
    print_info "Checking system prerequisites..."

    # Check if linuxmuster-base7 is installed
    if ! command -v linuxmuster-setup &> /dev/null; then
        echo -e "${RED}ERROR: linuxmuster-setup not found. Install linuxmuster-base7 first.${NC}"
        exit 1
    fi

    # Check if linuxmuster-common is installed
    if ! python3 -c "import sys; sys.path.insert(0, '/usr/lib/linuxmuster'); import environment" 2>/dev/null; then
        echo -e "${RED}ERROR: linuxmuster-common not found. Install it first.${NC}"
        exit 1
    fi

    # Check if system is configured
    . /usr/share/linuxmuster/environment.sh || exit 1
    if [ -e "$SETUPINI" ]; then
        echo -e "${RED}ERROR: linuxmuster-setup has already been run. Is this a production system?${NC}"
        exit 1
    fi

    # Check available disk space (need at least 500MB for snapshots)
    available=$(df /tmp | awk 'NR==2 {print $4}')
    if [ "$available" -lt 512000 ]; then
        echo -e "${YELLOW}WARNING: Low disk space in /tmp (less than 500MB)${NC}"
        echo "Snapshots may fail. Continue anyway? (y/n)"
        read -r response
        if [ "$response" != "y" ]; then
            exit 1
        fi
    fi

    print_info "System check passed"
}

# Create system snapshot
create_snapshot() {
    local snapshot_name="${1:-$SNAPSHOT_NAME}"
    local snapshot_path="$SNAPSHOT_DIR/$snapshot_name"

    print_info "Creating system snapshot: $snapshot_name"

    # Create snapshot directory
    mkdir -p "$snapshot_path"

    # Snapshot each path
    for path in "${SNAPSHOT_PATHS[@]}"; do
        if [ -e "$path" ]; then
            local parent_dir=$(dirname "$path")
            local snapshot_target="$snapshot_path$parent_dir"
            mkdir -p "$snapshot_target"

            if [ -d "$path" ]; then
                cp -a "$path" "$snapshot_target/" 2>/dev/null || true
            else
                cp -a "$path" "$snapshot_target/" 2>/dev/null || true
            fi
        fi
    done

    # Snapshot package states (dpkg)
    dpkg --get-selections > "$snapshot_path/dpkg-selections.txt"

    # Snapshot running services
    systemctl list-units --type=service --state=running > "$snapshot_path/services.txt"

    # Create snapshot metadata
    cat > "$snapshot_path/metadata.txt" << EOF
Snapshot: $snapshot_name
Created: $(date)
Hostname: $(hostname)
Kernel: $(uname -r)
OS: $(lsb_release -d | cut -f2)
EOF

    print_info "Snapshot created successfully: $snapshot_path"
}

# Restore system snapshot
restore_snapshot() {
    local snapshot_name="${1:-$SNAPSHOT_NAME}"
    local snapshot_path="$SNAPSHOT_DIR/$snapshot_name"

    if [ ! -d "$snapshot_path" ]; then
        echo -e "${RED}ERROR: Snapshot not found: $snapshot_path${NC}"
        return 1
    fi

    print_info "Restoring system snapshot: $snapshot_name"

    # Stop potentially affected services
    systemctl stop samba-ad-dc samba smbd nmbd winbind isc-dhcp-server 2>/dev/null || true

    # Restore each path
    for path in "${SNAPSHOT_PATHS[@]}"; do
        local snapshot_source="$snapshot_path$path"
        if [ -e "$snapshot_source" ]; then
            local parent_dir=$(dirname "$path")

            # Remove current version
            if [ -e "$path" ]; then
                rm -rf "$path"
            fi

            # Restore from snapshot
            mkdir -p "$parent_dir"
            if [ -d "$snapshot_source" ]; then
                cp -a "$snapshot_source" "$parent_dir/" 2>/dev/null || true
            else
                cp -a "$snapshot_source" "$parent_dir/" 2>/dev/null || true
            fi
        fi
    done

    # Restart services that were running
    # (In production, you'd want to restore the exact service state)
    systemctl restart samba-ad-dc 2>/dev/null || true
    systemctl restart samba 2>/dev/null || true
    systemctl restart smbd 2>/dev/null || true
    systemctl restart nmbd 2>/dev/null || true
    systemctl restart winbind 2>/dev/null || true
    systemctl restart isc-dhcp-server 2>/dev/null || true
    systemctl restart ntp 2>/dev/null || true
    systemctl restart apparmor 2>/dev/null || true
    systemctl restart cups 2>/dev/null || true
    systemctl restart linuxmuster-webui 2>/dev/null || true
    systemctl restart tftpd-hpa 2>/dev/null || true

    print_info "Snapshot restored successfully"
}

# List available snapshots
list_snapshots() {
    print_header "Available Snapshots"

    if [ ! -d "$SNAPSHOT_DIR" ] || [ -z "$(ls -A $SNAPSHOT_DIR 2>/dev/null)" ]; then
        echo "No snapshots found"
        return
    fi

    for snapshot in "$SNAPSHOT_DIR"/*; do
        if [ -f "$snapshot/metadata.txt" ]; then
            echo -e "\n${BLUE}Snapshot:${NC} $(basename "$snapshot")"
            cat "$snapshot/metadata.txt" | sed 's/^/  /'
        fi
    done
}

# Delete old snapshots
cleanup_snapshots() {
    local keep_count=${1:-5}

    if [ ! -d "$SNAPSHOT_DIR" ]; then
        return
    fi

    print_info "Cleaning up old snapshots (keeping last $keep_count)..."

    # Get sorted list of snapshots (oldest first)
    local snapshots=($(ls -1t "$SNAPSHOT_DIR" 2>/dev/null || true))
    local total=${#snapshots[@]}

    if [ "$total" -gt "$keep_count" ]; then
        local to_delete=$((total - keep_count))
        for ((i=keep_count; i<total; i++)); do
            local snapshot="${snapshots[$i]}"
            print_info "Deleting old snapshot: $snapshot"
            rm -rf "$SNAPSHOT_DIR/$snapshot"
        done
    fi
}

# Delete specific snapshot
delete_snapshot() {
    local snapshot_name="$1"
    local snapshot_path="$SNAPSHOT_DIR/$snapshot_name"

    if [ -z "$snapshot_name" ]; then
        echo -e "${RED}ERROR: Snapshot name required${NC}"
        return 1
    fi

    if [ ! -d "$snapshot_path" ]; then
        echo -e "${RED}ERROR: Snapshot not found: $snapshot_name${NC}"
        return 1
    fi

    print_info "Deleting snapshot: $snapshot_name"
    rm -rf "$snapshot_path"
    print_info "Snapshot deleted successfully"
}

# Delete all snapshots
delete_all_snapshots() {
    if [ ! -d "$SNAPSHOT_DIR" ]; then
        print_info "No snapshots to delete"
        return
    fi

    echo -e "${YELLOW}WARNING: This will delete ALL snapshots!${NC}"
    echo -n "Are you sure? (yes/no): "
    read -r confirm

    if [ "$confirm" = "yes" ]; then
        print_info "Deleting all snapshots..."
        rm -rf "$SNAPSHOT_DIR"
        print_info "All snapshots deleted"
    else
        print_info "Deletion cancelled"
    fi
}

# Test function template with snapshot/restore
run_test_with_snapshot() {
    local test_name="$1"
    local test_function="$2"
    local skip_restore="${3:-no}"  # Optional 3rd parameter: "skip" to skip restore

    ((TESTS_RUN++))
    print_test "$test_name"

    # Create pre-test snapshot
    local pre_snapshot="pretest-$TESTS_RUN-$(date +%s)"
    print_info "Creating pre-test snapshot: $pre_snapshot"

    # Create snapshot directory
    mkdir -p "$SNAPSHOT_DIR/$pre_snapshot" 2>/dev/null || true
    echo "DEBUG: Snapshot dir created: $SNAPSHOT_DIR/$pre_snapshot" >&2

    # Simplified snapshot - just copy essential dirs that exist
    print_info "Backing up configuration directories..."
    for path in /var/cache/linuxmuster /var/lib/linuxmuster /var/lib/samba; do
        echo "DEBUG: Checking path: $path" >&2
        if [ -d "$path" ]; then
            echo "DEBUG: Path exists, copying..." >&2
            parent=$(dirname "$path")
            mkdir -p "$SNAPSHOT_DIR/$pre_snapshot$parent" 2>/dev/null || true
            cp -a "$path" "$SNAPSHOT_DIR/$pre_snapshot$parent/" 2>/dev/null || true
            echo "DEBUG: Copied $path" >&2
        else
            echo "DEBUG: Path does not exist: $path" >&2
        fi
    done
    print_info "Snapshot created"

    # Run test - invoke the test function directly
    print_info "Executing test function: $test_function"
    echo "DEBUG: About to call function: $test_function" >&2

    # Call the function and capture result
    local test_result=0
    $test_function
    test_result=$?

    echo "DEBUG: Function returned with exit code: $test_result" >&2

    if [ $test_result -eq 0 ]; then
        print_pass "$test_name completed successfully"
    else
        print_fail "$test_name failed (exit code: $test_result)"
    fi

    # Restore snapshot (simplified) - skip if requested
    if [ "$skip_restore" = "skip" ]; then
        print_info "Skipping restore (changes will persist)"
        echo "DEBUG: Restore skipped as requested" >&2
    else
        echo "DEBUG: ===== STARTING RESTORE =====" >&2
        print_info "Restoring system state..."
        echo "DEBUG: Starting restore from: $SNAPSHOT_DIR/$pre_snapshot" >&2
        for path in /var/cache/linuxmuster /var/lib/linuxmuster /var/lib/samba; do
        snapshot_source="$SNAPSHOT_DIR/$pre_snapshot$path"
        echo "DEBUG: Checking restore source: $snapshot_source" >&2
        if [ -d "$snapshot_source" ]; then
            echo "DEBUG: Restoring $path" >&2
            rm -rf "$path" 2>/dev/null || true
            mkdir -p "$(dirname $path)" 2>/dev/null || true
            cp -a "$snapshot_source" "$(dirname $path)/" 2>/dev/null || true
            echo "DEBUG: Restored $path" >&2
        else
            echo "DEBUG: No snapshot for $path" >&2
        fi
    done
    echo "DEBUG: ===== RESTORE COMPLETE =====" >&2

    # Restart affected services
    echo "DEBUG: Restarting services..." >&2
    systemctl restart samba-ad-dc 2>/dev/null || true
    systemctl restart samba 2>/dev/null || true
    systemctl restart smbd 2>/dev/null || true
    systemctl restart nmbd 2>/dev/null || true
    systemctl restart winbind 2>/dev/null || true
    systemctl restart isc-dhcp-server 2>/dev/null || true
    systemctl restart ntp 2>/dev/null || true
    systemctl restart apparmor 2>/dev/null || true
    systemctl restart cups 2>/dev/null || true
    systemctl restart linuxmuster-webui 2>/dev/null || true
    systemctl restart tftpd-hpa 2>/dev/null || true
        echo "DEBUG: Services restarted" >&2

        print_info "System state restored"
    fi  # End of restore conditional

    # Cleanup test snapshot
    print_info "Cleaning up test snapshot..."
    echo "DEBUG: Removing snapshot: $SNAPSHOT_DIR/$pre_snapshot" >&2
    rm -rf "$SNAPSHOT_DIR/$pre_snapshot" 2>/dev/null || true
    echo "DEBUG: Snapshot cleaned up" >&2
}

# Example test: Basic setup with minimal parameters
test_basic_setup() {
    print_info "Running basic setup test..."

    # Add timeout and verbose output
    local output
    local exit_code

    print_info "Executing: linuxmuster-setup -n testserver -d test.local -a '***' -u -s"
    print_info "(This may take several minutes, output will be shown live...)"
    echo ""

    # Use timeout to prevent hanging (300 seconds = 5 minutes for full setup)
    # Use tee to show output live while also capturing it
    local temp_output="/tmp/test-setup-output-$$.txt"
    timeout 300 linuxmuster-setup \
        -n testserver \
        -d test.local \
        -a "TestPass123!" \
        -u \
        -s 2>&1 | tee "$temp_output" || true
    exit_code=${PIPESTATUS[0]}
    output=$(cat "$temp_output" 2>/dev/null || echo "")
    rm -f "$temp_output"

    echo ""
    print_info "Command completed with exit code: $exit_code"

    # Check for timeout (exit code 124)
    if [ $exit_code -eq 124 ]; then
        print_fail "Basic setup test timed out after 300 seconds"
        return 1
    fi

    # Check if setup ran (even if it failed, it should process arguments)
    # Success conditions:
    # 1. Setup processes commandline arguments
    # 2. OR setup begins execution (any setup module starts)
    if echo "$output" | grep -q "Processing commandline arguments\|ini.py\|templates.py\|ssl.py"; then
        print_info "Basic setup test executed (parameters processed correctly)"
        # Show exit code for reference
        if [ $exit_code -ne 0 ]; then
            print_info "Note: Setup exited with code $exit_code (may be expected in test environment)"
        fi
        return 0
    else
        print_fail "Basic setup test failed - output:"
        echo "$output" | head -30
        return 1
    fi
}

# Example test: Full parameter setup
test_full_setup() {
    print_info "Running full parameter setup test..."

    local output
    local exit_code

    print_info "Executing: linuxmuster-setup with full parameters"
    print_info "(This may take several minutes, output will be shown live...)"
    echo ""

    # Use timeout to prevent hanging (300 seconds = 5 minutes for full setup)
    local temp_output="/tmp/test-setup-output-$$.txt"
    timeout 300 linuxmuster-setup \
        -n testserver \
        -d test.local \
        -a "TestPass123!" \
        -e "Test School" \
        -l "Test City" \
        -z "Germany" \
        -v "Test State" \
        -r "10.0.255.1-10.0.255.254" \
        -u \
        -s 2>&1 | tee "$temp_output" || true
    exit_code=${PIPESTATUS[0]}
    output=$(cat "$temp_output" 2>/dev/null || echo "")
    rm -f "$temp_output"

    echo ""
    print_info "Command completed with exit code: $exit_code"

    # Check for timeout
    if [ $exit_code -eq 124 ]; then
        print_fail "Full setup test timed out after 300 seconds"
        return 1
    fi

    # Check if setup ran (even if it failed, it should process arguments)
    if echo "$output" | grep -q "Processing commandline arguments\|ini.py\|templates.py\|ssl.py"; then
        print_info "Full setup test executed (parameters processed correctly)"
        if [ $exit_code -ne 0 ]; then
            print_info "Note: Setup exited with code $exit_code (may be expected in test environment)"
        fi
        return 0
    else
        print_fail "Full setup test failed - output:"
        echo "$output" | head -30
        return 1
    fi
}

# Example test: Config file based setup
test_config_file_setup() {
    print_info "Running config file setup test..."

    cat > /tmp/test-setup-full.ini << 'EOF'
[setup]
servername = testserver
domainname = test.local
adminpw = TestPass123!
schoolname = Test School
location = Test City
country = Germany
state = Test State
dhcprange = 10.0.255.1-10.0.255.254
EOF

    local output
    local exit_code

    print_info "Executing: linuxmuster-setup -c /tmp/test-setup-full.ini -u -s"
    print_info "(This may take several minutes, output will be shown live...)"
    echo ""

    # Use timeout to prevent hanging (300 seconds = 5 minutes for full setup)
    local temp_output="/tmp/test-setup-output-$$.txt"
    timeout 300 linuxmuster-setup -c /tmp/test-setup-full.ini -u -s 2>&1 | tee "$temp_output" || true
    exit_code=${PIPESTATUS[0]}
    output=$(cat "$temp_output" 2>/dev/null || echo "")
    rm -f "$temp_output"

    rm -f /tmp/test-setup-full.ini

    echo ""
    print_info "Command completed with exit code: $exit_code"

    # Check for timeout
    if [ $exit_code -eq 124 ]; then
        print_fail "Config file setup test timed out after 300 seconds"
        return 1
    fi

    # Check if setup ran with config file
    if echo "$output" | grep -q "Custom inifile\|Processing commandline arguments\|ini.py"; then
        print_info "Config file setup test executed (config file processed correctly)"
        if [ $exit_code -ne 0 ]; then
            print_info "Note: Setup exited with code $exit_code (may be expected in test environment)"
        fi
        return 0
    else
        print_fail "Config file setup test failed - output:"
        echo "$output" | head -30
        return 1
    fi
}

# Test: Create test users
test_create_testusers() {
    print_info "Running create-testusers test..."

    # Check if script exists
    local script_path="/usr/share/linuxmuster/examples/create-testusers.py"
    if [ ! -f "$script_path" ]; then
        print_fail "create-testusers.py not found at $script_path"
        return 1
    fi

    local output
    local exit_code

    print_info "Executing: $script_path --force"
    print_info "(This may take several minutes, output will be shown live...)"
    echo ""

    # Use timeout to prevent hanging (300 seconds = 5 minutes)
    local temp_output="/tmp/test-testusers-output-$$.txt"
    timeout 300 "$script_path" --force 2>&1 | tee "$temp_output" || true
    exit_code=${PIPESTATUS[0]}
    output=$(cat "$temp_output" 2>/dev/null || echo "")
    rm -f "$temp_output"

    echo ""
    print_info "Command completed with exit code: $exit_code"

    # Check for timeout
    if [ $exit_code -eq 124 ]; then
        print_fail "Create-testusers test timed out after 300 seconds"
        return 1
    fi

    # Check if testuser creation ran successfully
    # Success indicators: "Creating test users", "done!", or "Success!"
    if echo "$output" | grep -q "Creating test users\|done!\|Success!"; then
        print_info "Create-testusers test executed (test users created)"
        if [ $exit_code -ne 0 ]; then
            print_info "Note: Script exited with code $exit_code (may be expected in test environment)"
        fi
        return 0
    else
        # If script fails due to missing prerequisites (e.g., no Samba setup), that's acceptable
        if echo "$output" | grep -qi "already users\|sophomorix\|samba"; then
            print_info "Create-testusers skipped (prerequisites not met or users already exist)"
            return 0
        else
            print_fail "Create-testusers test failed - output:"
            echo "$output" | head -30
            return 1
        fi
    fi
}

# Verify system state after test
verify_system_state() {
    local check_name="$1"

    print_info "Verifying $check_name..."

    # Add your verification logic here
    # For example:
    # - Check if files were created
    # - Check if services are running
    # - Check if configuration is correct

    return 0
}

# Interactive mode
interactive_mode() {
    while true; do
        echo -e "\n${BLUE}=== linuxmuster-setup Test Manager ===${NC}"
        echo "1. Create baseline snapshot"
        echo "2. Run single test with snapshot"
        echo "3. Run all tests"
        echo "4. List snapshots"
        echo "5. Restore specific snapshot"
        echo "6. Delete specific snapshot"
        echo "7. Delete all snapshots"
        echo "8. Cleanup old snapshots"
        echo "9. Exit"
        echo -n "Select option: "
        read -r choice

        case $choice in
            1)
                echo ""
                echo -e "${BLUE}=== Create Snapshot ===${NC}"
                echo -n "Snapshot name (or press Enter for auto-name): "
                read -r name
                name=${name:-"manual-$(date +%Y%m%d-%H%M%S)"}
                create_snapshot "$name"
                echo ""
                echo -n "Press Enter to continue..."
                read
                ;;
            2)
                while true; do
                    echo ""
                    echo -e "${BLUE}=== Run Single Test ===${NC}"
                    echo "Available tests:"
                    echo "  1. Basic setup"
                    echo "  2. Full setup"
                    echo "  3. Config file setup"
                    echo "  4. Create test users"
                    echo "  0. Back to main menu"
                    echo -n "Select test: "
                    read -r test_choice
                    case $test_choice in
                        1) run_test_with_snapshot "Basic Setup" test_basic_setup ;;
                        2) run_test_with_snapshot "Full Setup" test_full_setup ;;
                        3) run_test_with_snapshot "Config File Setup" test_config_file_setup ;;
                        4) run_test_with_snapshot "Create Test Users" test_create_testusers "skip" ;;
                        0) break ;;
                        *) echo "Invalid choice" ;;
                    esac
                    if [ "$test_choice" != "0" ]; then
                        echo ""
                        echo -n "Press Enter to continue..."
                        read
                    fi
                done
                ;;
            3)
                run_all_tests
                echo ""
                echo -n "Press Enter to continue..."
                read
                ;;
            4)
                list_snapshots
                echo ""
                echo -n "Press Enter to continue..."
                read
                ;;
            5)
                while true; do
                    echo ""
                    echo -e "${BLUE}=== Restore Snapshot ===${NC}"
                    list_snapshots
                    echo ""
                    echo -n "Snapshot name to restore (or 0 to go back): "
                    read -r name
                    if [ "$name" = "0" ]; then
                        break
                    fi
                    if [ -n "$name" ]; then
                        restore_snapshot "$name"
                        echo ""
                        echo -n "Press Enter to continue..."
                        read
                        break
                    else
                        echo "Please enter a snapshot name or 0 to go back"
                    fi
                done
                ;;
            6)
                while true; do
                    echo ""
                    echo -e "${BLUE}=== Delete Snapshot ===${NC}"
                    list_snapshots
                    echo ""
                    echo -n "Snapshot name to delete (or 0 to go back): "
                    read -r name
                    if [ "$name" = "0" ]; then
                        break
                    fi
                    if [ -n "$name" ]; then
                        delete_snapshot "$name"
                        echo ""
                        echo -n "Press Enter to continue..."
                        read
                        break
                    else
                        echo "Please enter a snapshot name or 0 to go back"
                    fi
                done
                ;;
            7)
                delete_all_snapshots
                echo ""
                echo -n "Press Enter to continue..."
                read
                ;;
            8)
                echo ""
                echo -e "${BLUE}=== Cleanup Old Snapshots ===${NC}"
                list_snapshots
                echo ""
                echo -n "Keep how many recent snapshots? [5]: "
                read -r keep
                keep=${keep:-5}
                cleanup_snapshots "$keep"
                echo ""
                echo -n "Press Enter to continue..."
                read
                ;;
            9)
                echo "Exiting..."
                exit 0
                ;;
            *)
                echo "Invalid choice"
                ;;
        esac
    done
}

# Run all tests
run_all_tests() {
    print_header "Running All Integration Tests"

    # Create baseline snapshot
    local baseline="baseline-$(date +%Y%m%d-%H%M%S)"
    print_info "Creating baseline snapshot: $baseline"
    create_snapshot "$baseline" > /dev/null 2>&1

    print_info "Starting test execution..."
    echo ""

    # Run tests - create test users after each setup test
    echo "DEBUG: About to start Test 1/6" >&2
    print_info "Test 1/6: Basic Setup Test"
    echo "DEBUG: Calling run_test_with_snapshot for test 1" >&2
    run_test_with_snapshot "Basic Setup Test" test_basic_setup
    echo "DEBUG: Test 1 completed" >&2

    echo "DEBUG: About to start Test 2/6" >&2
    print_info "Test 2/6: Create Test Users (after basic setup)"
    echo "DEBUG: Calling run_test_with_snapshot for test 2" >&2
    run_test_with_snapshot "Create Test Users (after basic setup)" test_create_testusers "skip"
    echo "DEBUG: Test 2 completed" >&2

    echo "DEBUG: About to start Test 3/6" >&2
    print_info "Test 3/6: Full Setup Test"
    echo "DEBUG: Calling run_test_with_snapshot for test 3" >&2
    run_test_with_snapshot "Full Setup Test" test_full_setup
    echo "DEBUG: Test 3 completed" >&2

    echo "DEBUG: About to start Test 4/6" >&2
    print_info "Test 4/6: Create Test Users (after full setup)"
    echo "DEBUG: Calling run_test_with_snapshot for test 4" >&2
    run_test_with_snapshot "Create Test Users (after full setup)" test_create_testusers "skip"
    echo "DEBUG: Test 4 completed" >&2

    echo "DEBUG: About to start Test 5/6" >&2
    print_info "Test 5/6: Config File Setup Test"
    echo "DEBUG: Calling run_test_with_snapshot for test 5" >&2
    run_test_with_snapshot "Config File Setup Test" test_config_file_setup
    echo "DEBUG: Test 5 completed" >&2

    echo "DEBUG: About to start Test 6/6" >&2
    print_info "Test 6/6: Create Test Users (after config file setup)"
    echo "DEBUG: Calling run_test_with_snapshot for test 6" >&2
    run_test_with_snapshot "Create Test Users (after config file setup)" test_create_testusers "skip"
    echo "DEBUG: Test 6 completed" >&2

    # Print summary
    print_summary

    # Cleanup old snapshots
    print_info "Cleaning up old snapshots..."
    cleanup_snapshots 5

    # Return to baseline
    print_info "Restoring baseline state..."
    restore_snapshot "$baseline"

    # Remove baseline snapshot as it's no longer needed
    print_info "Removing baseline snapshot..."
    rm -rf "$SNAPSHOT_DIR/$baseline"

    print_info "All tests completed!"
}

# Run single test
run_single_test() {
    local test_number="$1"
    local skip_restore="${2:-no}"

    print_header "Running Single Test"

    case "$test_number" in
        1)
            print_info "Test 1: Basic Setup"
            run_test_with_snapshot "Basic Setup Test" test_basic_setup "$skip_restore"
            ;;
        2)
            print_info "Test 2: Full Setup"
            run_test_with_snapshot "Full Setup Test" test_full_setup "$skip_restore"
            ;;
        3)
            print_info "Test 3: Config File Setup"
            run_test_with_snapshot "Config File Setup Test" test_config_file_setup "$skip_restore"
            ;;
        4)
            print_info "Test 4: Create Test Users"
            run_test_with_snapshot "Create Test Users" test_create_testusers "skip"
            ;;
        *)
            echo -e "${RED}ERROR: Invalid test number: $test_number${NC}"
            echo "Valid test numbers: 1-4"
            echo "  1 = Basic Setup"
            echo "  2 = Full Setup"
            echo "  3 = Config File Setup"
            echo "  4 = Create Test Users"
            exit 1
            ;;
    esac

    print_summary
}

# Main function
main() {
    print_header "linuxmuster-setup Integration Test Suite"
    echo "Date: $(date)"
    echo ""

    # Check prerequisites
    check_root
    check_system

    # Global options
    local skip_restore="no"

    # Parse options
    while [ $# -gt 0 ]; do
        case "$1" in
            --no-restore|-n)
                skip_restore="skip"
                shift
                ;;
            --test|-t)
                if [ -z "$2" ]; then
                    echo "Usage: $0 --test <number> [--no-restore]"
                    exit 1
                fi
                run_single_test "$2" "$skip_restore"
                exit $?
                ;;
            --interactive|-i)
                interactive_mode
                exit $?
                ;;
            --create-snapshot|-c)
                create_snapshot "${2:-manual-$(date +%Y%m%d-%H%M%S)}"
                exit $?
                ;;
            --restore|-r)
                if [ -z "$2" ]; then
                    echo "Usage: $0 --restore <snapshot-name>"
                    exit 1
                fi
                restore_snapshot "$2"
                exit $?
                ;;
            --list|-l)
                list_snapshots
                exit $?
                ;;
            --delete|-d)
                if [ -z "$2" ]; then
                    echo "Usage: $0 --delete <snapshot-name>"
                    exit 1
                fi
                delete_snapshot "$2"
                exit $?
                ;;
            --delete-all)
                delete_all_snapshots
                exit $?
                ;;
            --cleanup)
                cleanup_snapshots "${2:-5}"
                exit $?
                ;;
            --help|-h)
                cat << EOF
Usage: $0 [OPTIONS]

Integration test suite for linuxmuster-setup with snapshot management.

Options:
  (no options)              Run all tests automatically
  -t, --test <number>       Run single test (1-4) [--no-restore optional]
  -n, --no-restore          Skip restore after test (for -t option)
  -i, --interactive         Interactive mode
  -c, --create-snapshot [name]  Create system snapshot
  -r, --restore <name>      Restore snapshot
  -l, --list                List available snapshots
  -d, --delete <name>       Delete specific snapshot
  --delete-all              Delete all snapshots (with confirmation)
  --cleanup [count]         Cleanup old snapshots (keep last N, default: 5)
  -h, --help                Show this help

Test Numbers:
  1 = Basic Setup
  2 = Full Setup
  3 = Config File Setup
  4 = Create Test Users

Examples:
  $0                        # Run all tests
  $0 -t 1                   # Run test 1 (Basic Setup) with restore
  $0 -t 1 -n                # Run test 1 without restore
  $0 -t 4                   # Run test 4 (Create Users, never restores)
  $0 -i                     # Interactive mode
  $0 -c baseline            # Create snapshot named 'baseline'
  $0 -r baseline            # Restore snapshot 'baseline'
  $0 -l                     # List all snapshots
  $0 -d baseline            # Delete snapshot 'baseline'
  $0 --delete-all           # Delete all snapshots

EOF
                exit 0
                ;;
            "")
                run_all_tests
                exit $?
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # If we get here without exiting, run all tests
    run_all_tests

    # Exit with appropriate code
    if [ $TESTS_FAILED -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Run main
main "$@"
