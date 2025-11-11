#!/bin/bash
#
# Integration test script for linuxmuster-setup with system state management
# Creates snapshots and restores system state between tests
# thomas@linuxmuster.net
# 20251111
#

set -e

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
    "/var/cache/linuxmuster"
    "/etc/samba/smb.conf"
    "/etc/dhcp"
    "/etc/hosts"
    "/etc/hostname"
    "/etc/resolv.conf"
    "/etc/netplan"
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
    systemctl stop samba smbd nmbd winbind isc-dhcp-server 2>/dev/null || true

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
    systemctl restart samba 2>/dev/null || true
    systemctl restart isc-dhcp-server 2>/dev/null || true

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

    ((TESTS_RUN++))
    print_test "$test_name"

    # Create pre-test snapshot
    local pre_snapshot="pretest-$TESTS_RUN-$(date +%s)"
    print_info "Creating pre-test snapshot..."
    create_snapshot "$pre_snapshot" > /dev/null 2>&1

    # Run test - invoke the test function
    print_info "Executing test function: $test_function"
    if eval "$test_function"; then
        print_pass "$test_name completed successfully"
    else
        print_fail "$test_name failed"
    fi

    # Restore snapshot
    print_info "Restoring system state..."
    restore_snapshot "$pre_snapshot" > /dev/null 2>&1

    # Cleanup test snapshot
    print_info "Cleaning up test snapshot..."
    rm -rf "$SNAPSHOT_DIR/$pre_snapshot"
}

# Example test: Basic setup with minimal parameters
test_basic_setup() {
    print_info "Running basic setup test..."

    local output=$(linuxmuster-setup \
        -n testserver \
        -d test.local \
        -a "TestPass123!" \
        -u \
        -s 2>&1)

    if echo "$output" | grep -q "Processing commandline arguments"; then
        print_info "Basic setup test executed"
        return 0
    else
        print_fail "Basic setup test failed"
        return 1
    fi
}

# Example test: Full parameter setup
test_full_setup() {
    print_info "Running full parameter setup test..."

    local output=$(linuxmuster-setup \
        -n testserver \
        -d test.local \
        -a "TestPass123!" \
        -e "Test School" \
        -l "Test City" \
        -z "Germany" \
        -v "Test State" \
        -r "10.0.0.100-10.0.0.200" \
        -u \
        -s 2>&1)

    if echo "$output" | grep -q "Processing commandline arguments"; then
        print_info "Full setup test executed"
        return 0
    else
        print_fail "Full setup test failed"
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
dhcprange = 10.0.0.100-10.0.0.200
EOF

    local output=$(linuxmuster-setup -c /tmp/test-setup-full.ini -u -s 2>&1)
    local result=0

    if echo "$output" | grep -q "Custom inifile"; then
        print_info "Config file setup test executed"
        result=0
    else
        print_fail "Config file setup test failed"
        result=1
    fi

    rm -f /tmp/test-setup-full.ini
    return $result
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
                echo -n "Snapshot name (or press Enter for auto-name): "
                read -r name
                name=${name:-"manual-$(date +%Y%m%d-%H%M%S)"}
                create_snapshot "$name"
                ;;
            2)
                echo "Available tests:"
                echo "  1. Basic setup"
                echo "  2. Full setup"
                echo "  3. Config file setup"
                echo -n "Select test: "
                read -r test_choice
                case $test_choice in
                    1) run_test_with_snapshot "Basic Setup" test_basic_setup ;;
                    2) run_test_with_snapshot "Full Setup" test_full_setup ;;
                    3) run_test_with_snapshot "Config File Setup" test_config_file_setup ;;
                    *) echo "Invalid choice" ;;
                esac
                ;;
            3)
                run_all_tests
                ;;
            4)
                list_snapshots
                ;;
            5)
                echo -n "Snapshot name to restore: "
                read -r name
                restore_snapshot "$name"
                ;;
            6)
                echo -n "Snapshot name to delete: "
                read -r name
                delete_snapshot "$name"
                ;;
            7)
                delete_all_snapshots
                ;;
            8)
                echo -n "Keep how many recent snapshots? [5]: "
                read -r keep
                keep=${keep:-5}
                cleanup_snapshots "$keep"
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

    # Run tests - these should actually execute now
    print_info "Test 1/3: Basic Setup Test"
    run_test_with_snapshot "Basic Setup Test" test_basic_setup

    print_info "Test 2/3: Full Setup Test"
    run_test_with_snapshot "Full Setup Test" test_full_setup

    print_info "Test 3/3: Config File Setup Test"
    run_test_with_snapshot "Config File Setup Test" test_config_file_setup

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

# Main function
main() {
    print_header "linuxmuster-setup Integration Test Suite"
    echo "Date: $(date)"
    echo ""

    # Check prerequisites
    check_root
    check_system

    # Parse arguments
    case "${1:-}" in
        --interactive|-i)
            interactive_mode
            ;;
        --create-snapshot|-c)
            create_snapshot "${2:-manual-$(date +%Y%m%d-%H%M%S)}"
            ;;
        --restore|-r)
            if [ -z "$2" ]; then
                echo "Usage: $0 --restore <snapshot-name>"
                exit 1
            fi
            restore_snapshot "$2"
            ;;
        --list|-l)
            list_snapshots
            ;;
        --delete|-d)
            if [ -z "$2" ]; then
                echo "Usage: $0 --delete <snapshot-name>"
                exit 1
            fi
            delete_snapshot "$2"
            ;;
        --delete-all)
            delete_all_snapshots
            ;;
        --cleanup)
            cleanup_snapshots "${2:-5}"
            ;;
        --help|-h)
            cat << EOF
Usage: $0 [OPTIONS]

Integration test suite for linuxmuster-setup with snapshot management.

Options:
  (no options)          Run all tests automatically
  -i, --interactive     Interactive mode
  -c, --create-snapshot [name]  Create system snapshot
  -r, --restore <name>  Restore snapshot
  -l, --list            List available snapshots
  -d, --delete <name>   Delete specific snapshot
  --delete-all          Delete all snapshots (with confirmation)
  --cleanup [count]     Cleanup old snapshots (keep last N, default: 5)
  -h, --help            Show this help

Examples:
  $0                    # Run all tests
  $0 -i                 # Interactive mode
  $0 -c baseline        # Create snapshot named 'baseline'
  $0 -r baseline        # Restore snapshot 'baseline'
  $0 -l                 # List all snapshots
  $0 -d baseline        # Delete snapshot 'baseline'
  $0 --delete-all       # Delete all snapshots

EOF
            exit 0
            ;;
        "")
            run_all_tests
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac

    # Exit with appropriate code
    if [ $TESTS_FAILED -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Run main
main "$@"
