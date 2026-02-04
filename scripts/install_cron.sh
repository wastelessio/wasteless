#!/bin/bash
###############################################################################
# Wasteless - Cron Job Installation Script
#
# This script helps install and manage the automated cleanup cron job.
#
# Usage:
#   ./scripts/install_cron.sh install   # Install cron job
#   ./scripts/install_cron.sh remove    # Remove cron job
#   ./scripts/install_cron.sh status    # Check if cron job is installed
#
# Author: Wasteless
###############################################################################

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CLEANUP_SCRIPT="$SCRIPT_DIR/run_cleanup.sh"

# Cron job identifier (unique comment to find our job)
CRON_IDENTIFIER="# Wasteless: Automated cleanup of orphaned recommendations"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC}  $*"
}

print_success() {
    echo -e "${GREEN}✅${NC} $*"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $*"
}

print_error() {
    echo -e "${RED}❌${NC} $*"
}

print_header() {
    echo ""
    echo "======================================================================="
    echo "$*"
    echo "======================================================================="
    echo ""
}

# Function to check if cron job is installed
is_installed() {
    crontab -l 2>/dev/null | grep -F "$CRON_IDENTIFIER" >/dev/null 2>&1
    return $?
}

# Function to install cron job
install_cron() {
    print_header "🔧 Installing Wasteless Cleanup Cron Job"

    # Check if already installed
    if is_installed; then
        print_warning "Cron job is already installed!"
        print_info "Run '$0 remove' to remove it first, then reinstall."
        exit 1
    fi

    # Verify cleanup script exists
    if [ ! -f "$CLEANUP_SCRIPT" ]; then
        print_error "Cleanup script not found at: $CLEANUP_SCRIPT"
        exit 1
    fi

    # Make script executable
    chmod +x "$CLEANUP_SCRIPT"

    # Ask user for schedule preference
    echo "Choose cleanup schedule:"
    echo "  1) Daily at 3:00 AM (Recommended)"
    echo "  2) Every 12 hours (3:00 AM and 3:00 PM)"
    echo "  3) Every 6 hours (3:00 AM, 9:00 AM, 3:00 PM, 9:00 PM)"
    echo "  4) Custom schedule"
    echo ""
    read -p "Enter your choice [1-4]: " schedule_choice

    case $schedule_choice in
        1)
            CRON_SCHEDULE="0 3 * * *"
            SCHEDULE_DESC="Daily at 3:00 AM"
            ;;
        2)
            CRON_SCHEDULE="0 3,15 * * *"
            SCHEDULE_DESC="Every 12 hours (3:00 AM and 3:00 PM)"
            ;;
        3)
            CRON_SCHEDULE="0 3,9,15,21 * * *"
            SCHEDULE_DESC="Every 6 hours (3:00 AM, 9:00 AM, 3:00 PM, 9:00 PM)"
            ;;
        4)
            echo ""
            print_info "Enter cron schedule (e.g., '0 3 * * *' for daily at 3 AM)"
            print_info "Format: minute hour day month weekday"
            read -p "Cron schedule: " CRON_SCHEDULE
            SCHEDULE_DESC="Custom: $CRON_SCHEDULE"
            ;;
        *)
            print_error "Invalid choice. Exiting."
            exit 1
            ;;
    esac

    # Create cron job entry
    CRON_JOB="$CRON_SCHEDULE $CLEANUP_SCRIPT"

    # Add to crontab
    (crontab -l 2>/dev/null || true; echo "$CRON_IDENTIFIER"; echo "$CRON_JOB") | crontab -

    # Verify installation
    if is_installed; then
        print_success "Cron job installed successfully!"
        echo ""
        print_info "Schedule: $SCHEDULE_DESC"
        print_info "Script: $CLEANUP_SCRIPT"
        print_info "Logs: $PROJECT_ROOT/logs/cleanup_*.log"
        echo ""
        print_info "To verify installation: $0 status"
        print_info "To remove: $0 remove"
    else
        print_error "Failed to install cron job"
        exit 1
    fi
}

# Function to remove cron job
remove_cron() {
    print_header "🗑️  Removing Wasteless Cleanup Cron Job"

    # Check if installed
    if ! is_installed; then
        print_warning "Cron job is not installed"
        exit 0
    fi

    # Remove from crontab
    crontab -l 2>/dev/null | grep -v -F "$CRON_IDENTIFIER" | grep -v -F "$SCRIPT_DIR/run_cleanup.sh" | crontab -

    # Verify removal
    if ! is_installed; then
        print_success "Cron job removed successfully"
    else
        print_error "Failed to remove cron job"
        exit 1
    fi
}

# Function to check status
check_status() {
    print_header "📊 Wasteless Cleanup Cron Job Status"

    if is_installed; then
        print_success "Cron job is INSTALLED"
        echo ""
        print_info "Current crontab entry:"
        echo "---"
        crontab -l 2>/dev/null | grep -A 1 -F "$CRON_IDENTIFIER"
        echo "---"
        echo ""
        print_info "Recent logs:"
        if [ -d "$PROJECT_ROOT/logs" ]; then
            ls -lt "$PROJECT_ROOT/logs/cleanup_"*.log 2>/dev/null | head -5 || print_info "No logs found yet"
        else
            print_info "Logs directory not created yet (will be created on first run)"
        fi
    else
        print_warning "Cron job is NOT installed"
        echo ""
        print_info "To install: $0 install"
    fi
}

# Main execution
case "${1:-}" in
    install)
        install_cron
        ;;
    remove)
        remove_cron
        ;;
    status)
        check_status
        ;;
    *)
        echo "Wasteless - Cron Job Management"
        echo ""
        echo "Usage: $0 {install|remove|status}"
        echo ""
        echo "Commands:"
        echo "  install  - Install automated cleanup cron job"
        echo "  remove   - Remove cron job"
        echo "  status   - Check installation status"
        echo ""
        exit 1
        ;;
esac

exit 0
