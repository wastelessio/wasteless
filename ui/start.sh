#!/bin/bash
#
# WasteLess UI - Start Script (FastAPI)
#
# Usage: ./start.sh
#
# To create a 'wasteless' alias, run:
#   source start.sh --install-alias
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Handle --install-alias flag
if [ "$1" = "--install-alias" ]; then
    SHELL_RC=""
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_RC="$HOME/.bashrc"
    fi

    if [ -n "$SHELL_RC" ]; then
        ALIAS_LINE="alias wasteless='$SCRIPT_DIR/start.sh'"

        # Check if alias already exists
        if grep -q "alias wasteless=" "$SHELL_RC" 2>/dev/null; then
            echo "Alias 'wasteless' already exists in $SHELL_RC"
        else
            echo "" >> "$SHELL_RC"
            echo "# WasteLess CLI" >> "$SHELL_RC"
            echo "$ALIAS_LINE" >> "$SHELL_RC"
            echo "Alias 'wasteless' added to $SHELL_RC"
            echo "Run 'source $SHELL_RC' or open a new terminal to use it."
        fi
    else
        echo "Could not detect shell. Add this manually to your shell config:"
        echo "  alias wasteless='$SCRIPT_DIR/start.sh'"
    fi
    exit 0
fi

cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  __        __        _       _                "
echo "  \ \      / /_ _ ___| |_ ___| | ___  ___ ___ "
echo "   \ \ /\ / / _\` / __| __/ _ \ |/ _ \/ __/ __|"
echo "    \ V  V / (_| \__ \ ||  __/ |  __/\__ \__ \\"
echo "     \_/\_/ \__,_|___/\__\___|_|\___||___/___/"
echo ""
echo "       Cloud Cost Optimization Platform"
echo -e "${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found!${NC}"
    echo "Please create a .env file with database credentials"
    echo "You can copy from: cp .env.template .env"
    exit 1
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
fi

# Load environment
source .env

# Get port (WASTELESS_PORT env var overrides .env setting)
PORT="${WASTELESS_PORT:-${STREAMLIT_SERVER_PORT:-8888}}"

# Check if port is in use
if lsof -ti:$PORT > /dev/null 2>&1; then
    PID=$(lsof -ti:$PORT | head -1)
    PROC=$(ps -p "$PID" -o comm= 2>/dev/null || echo "unknown")
    if echo "$PROC" | grep -qE "uvicorn|python"; then
        echo -e "${GREEN}WasteLess is already running on http://localhost:$PORT${NC}"
        echo "Open your browser at: http://localhost:$PORT"
        exit 0
    else
        echo -e "${YELLOW}Port $PORT is already in use by '$PROC' (PID $PID).${NC}"
        echo "To use a different port:"
        echo "  WASTELESS_PORT=8889 wasteless"
        exit 1
    fi
fi

echo ""
echo -e "  ${YELLOW}Starting server...${NC}"
echo ""

LOG_FILE="/tmp/wasteless_${PORT}.log"

# Force Python unbuffered output so logs appear in file immediately (not TTY)
export PYTHONUNBUFFERED=1

# Start uvicorn in background
uvicorn main:app --host 0.0.0.0 --port $PORT --reload \
    --reload-exclude 'venv/**' \
    --reload-exclude '*.pyc' \
    --reload-exclude '__pycache__/**' > "$LOG_FILE" 2>&1 &
UVICORN_PID=$!

# Cleanup on exit (Ctrl+C or normal exit)
cleanup() {
    printf "\r                                          \r"
    kill $UVICORN_PID 2>/dev/null
    kill $TAIL_PID 2>/dev/null
    rm -f "$LOG_FILE"
}
trap cleanup EXIT INT TERM

# Spinner (ASCII — safe on macOS bash 3.2)
SPINNER=('|' '/' '-' '\')
MAX_WAIT=30
i=0
READY=0
while [ $i -lt $MAX_WAIT ]; do
    if ! kill -0 $UVICORN_PID 2>/dev/null; then
        printf "\r                                          \r"
        echo -e "  \033[0;31m✗ Server failed to start. Logs:\033[0m"
        cat "$LOG_FILE"
        exit 1
    fi
    if curl -s -o /dev/null "http://localhost:$PORT/" 2>/dev/null; then
        READY=1
        break
    fi
    SPIN_CHAR="${SPINNER[$((i % 4))]}"
    printf "\r  %s  Starting... (%ds)" "$SPIN_CHAR" "$i"
    sleep 1
    i=$((i + 1))
done

printf "\r                                          \r"

if [ $READY -eq 0 ]; then
    echo -e "  \033[0;31m✗ Server did not respond after ${MAX_WAIT}s. Logs:\033[0m"
    cat "$LOG_FILE"
    exit 1
fi

echo -e "  ${GREEN}✅ Ready → http://localhost:$PORT${NC}"
echo ""

# Auto-open browser
if command -v open &>/dev/null; then
    open "http://localhost:$PORT"
elif command -v xdg-open &>/dev/null; then
    xdg-open "http://localhost:$PORT" &>/dev/null &
fi

echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop."
echo ""

# Stream uvicorn logs to terminal
tail -f "$LOG_FILE" &
TAIL_PID=$!

# Wait for uvicorn (returns when killed or crashes)
wait $UVICORN_PID || true
