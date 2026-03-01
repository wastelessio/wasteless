#!/bin/bash
#
# wasteless — WasteLess CLI
#
# Usage:
#   wasteless           Start the web UI (default)
#   wasteless start     Start the web UI
#   wasteless collect   Collect CloudWatch metrics + detect idle instances
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

CMD="${1:-start}"

case "$CMD" in
    start | "")
        exec "$SCRIPT_DIR/ui/start.sh"
        ;;

    collect)
        cd "$SCRIPT_DIR"

        if [ ! -d "venv" ]; then
            echo -e "${RED}[ERROR]${NC} Virtual environment not found. Run ./install.sh first."
            exit 1
        fi

        source venv/bin/activate

        echo ""
        echo -e "${BOLD}WasteLess — Collect & Detect${NC}"
        echo ""

        echo -e "${CYAN}[1/2]${NC} Collecting CloudWatch metrics..."
        if python3 src/collectors/aws_cloudwatch.py; then
            echo -e "${GREEN}[OK]${NC} Metrics collected"
        else
            echo -e "${RED}[ERROR]${NC} Collector failed"
            exit 1
        fi

        echo ""
        echo -e "${CYAN}[2/2]${NC} Detecting idle instances..."
        if python3 src/detectors/ec2_idle.py; then
            echo -e "${GREEN}[OK]${NC} Detection complete"
        else
            echo -e "${RED}[ERROR]${NC} Detector failed"
            exit 1
        fi

        echo ""
        echo -e "${GREEN}Done!${NC} Open ${BOLD}http://localhost:8888/recommendations${NC} to review."
        echo ""
        ;;

    *)
        echo -e "${BOLD}Usage:${NC} wasteless [command]"
        echo ""
        echo "Commands:"
        echo "  start     Start the web UI (default)"
        echo "  collect   Collect AWS metrics and detect idle instances"
        echo ""
        exit 1
        ;;
esac
