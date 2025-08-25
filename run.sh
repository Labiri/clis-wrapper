#!/bin/bash

# OpenAI-Compatible Claude/Gemini Wrapper - Run Script
# Supports debug mode with comprehensive logging to debug.log

# Default values
DEBUG_MODE=true
VERBOSE=true
PORT=8005
LOG_FILE="debug.log"
SHOW_HELP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --debug|-d)
            DEBUG_MODE=true
            VERBOSE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --port|-p)
            PORT="$2"
            shift 2
            ;;
        --log-file)
            LOG_FILE="$2"
            shift 2
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            SHOW_HELP=true
            shift
            ;;
    esac
done

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
    cat << EOF
Usage: ./run.sh [OPTIONS]

Run the OpenAI-compatible Claude/Gemini wrapper with optional debug logging.

OPTIONS:
    -d, --debug          Enable debug mode (logs everything to debug.log)
    -v, --verbose        Enable verbose output (without full debug logging)
    -p, --port PORT      Set the server port (default: 8000)
    --log-file FILE      Set the debug log file path (default: debug.log)
    -h, --help           Show this help message

EXAMPLES:
    ./run.sh                    # Run normally on port 8000
    ./run.sh --debug            # Run with debug logging to debug.log
    ./run.sh -d -p 8080         # Debug mode on port 8080
    ./run.sh --verbose          # Verbose output without file logging

ENVIRONMENT:
    The script respects all environment variables from .env file
    Debug mode sets: DEBUG_MODE=true, VERBOSE=true
    Logs are written to: $LOG_FILE (when in debug mode)

EOF
    exit 0
fi

# Function to log messages
log_message() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if [ "$DEBUG_MODE" = true ]; then
        echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    fi
    
    if [ "$VERBOSE" = true ] || [ "$level" = "ERROR" ]; then
        echo "[$level] $message"
    fi
}

# Clear or create debug log file if in debug mode
if [ "$DEBUG_MODE" = true ]; then
    > "$LOG_FILE"
    log_message "INFO" "Debug logging initialized - writing to $LOG_FILE"
    log_message "INFO" "Starting server with debug mode enabled"
fi

# Check for Poetry
if ! command -v poetry &> /dev/null; then
    log_message "ERROR" "Poetry is not installed. Please install Poetry first."
    echo "Visit: https://python-poetry.org/docs/#installation"
    exit 1
fi

# Check if .env file exists
if [ -f .env ]; then
    log_message "INFO" ".env file found - Poetry will load it automatically"
else
    log_message "WARN" ".env file not found - using system environment variables"
fi

# Override with command line arguments (these take precedence over .env)
export DEBUG_MODE=$DEBUG_MODE
export VERBOSE=$VERBOSE
# Don't override PORT from command line if using .env
if [ "$PORT" != "8000" ]; then
    export PORT=$PORT
fi

log_message "INFO" "Configuration:"
log_message "INFO" "  - Port: $PORT"
log_message "INFO" "  - Debug Mode: $DEBUG_MODE"
log_message "INFO" "  - Verbose: $VERBOSE"
log_message "INFO" "  - Log File: $LOG_FILE"

# Check Python version
PYTHON_VERSION=$(poetry run python --version 2>&1)
log_message "INFO" "Python version: $PYTHON_VERSION"

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    log_message "INFO" "Virtual environment not found, installing dependencies..."
    poetry install
    if [ $? -ne 0 ]; then
        log_message "ERROR" "Failed to install dependencies"
        exit 1
    fi
fi

# Function to cleanup on exit
cleanup() {
    log_message "INFO" "Shutting down server..."
    if [ "$DEBUG_MODE" = true ]; then
        log_message "INFO" "Debug log saved to: $LOG_FILE"
        echo "Debug log saved to: $LOG_FILE"
    fi
}

# Set up cleanup trap
trap cleanup EXIT INT TERM

# Start the server
log_message "INFO" "Starting FastAPI server on port $PORT..."

if [ "$DEBUG_MODE" = true ]; then
    # In debug mode, capture all output to both console and log file
    echo "Starting server in DEBUG mode - logging to $LOG_FILE"
    echo "Press Ctrl+C to stop the server"
    echo "----------------------------------------"
    
    # Use tee to duplicate output to both console and log file
    poetry run uvicorn main:app \
        --host 0.0.0.0 \
        --port "$PORT" \
        --log-level debug \
        --reload \
        2>&1 | while IFS= read -r line; do
            echo "$line"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] [UVICORN] $line" >> "$LOG_FILE"
        done
else
    # Normal mode - just run the server
    if [ "$VERBOSE" = true ]; then
        LOG_LEVEL="info"
    else
        LOG_LEVEL="warning"
    fi
    
    poetry run uvicorn main:app \
        --host 0.0.0.0 \
        --port "$PORT" \
        --log-level "$LOG_LEVEL" \
        --reload
fi