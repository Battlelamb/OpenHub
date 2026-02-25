#!/bin/bash

# =============================================================================
# Agent Hub Automation Scripts
# =============================================================================
# Comprehensive bash automation for multi-agent coordination
# Designed for maximum simplicity and atomic operations
# =============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

# Hub Configuration
readonly AGENTHUB_URL="${AGENTHUB_URL:-http://localhost:7788}"
readonly AGENTHUB_WS_URL="${AGENTHUB_WS_URL:-ws://localhost:7788/v1/agent-connect}"
readonly API_KEY="${AGENTHUB_API_KEY:-}"

# Directories
readonly SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPTS_DIR")"
readonly LOGS_DIR="${PROJECT_ROOT}/logs"
readonly TEMP_DIR="${PROJECT_ROOT}/temp"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

# Logging function with timestamps
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO")  echo -e "${GREEN}[INFO]${NC}  [$timestamp] $message" ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC}  [$timestamp] $message" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} [$timestamp] $message" >&2 ;;
        "DEBUG") echo -e "${BLUE}[DEBUG]${NC} [$timestamp] $message" ;;
        *)       echo "[$timestamp] $message" ;;
    esac
    
    # Also write to log file
    mkdir -p "$LOGS_DIR"
    echo "[$level] [$timestamp] $message" >> "$LOGS_DIR/automation.log"
}

# Progress indicator for long operations
progress() {
    local step="$1"
    local total="$2"
    local message="$3"
    
    local percent
    percent=$(( (step * 100) / total ))
    local bar_length=20
    local filled_length
    filled_length=$(( (percent * bar_length) / 100 ))
    
    local bar=""
    for ((i=0; i<filled_length; i++)); do bar+="█"; done
    for ((i=filled_length; i<bar_length; i++)); do bar+="░"; done
    
    printf "\r${BLUE}[%3d%%]${NC} |%s| %s" "$percent" "$bar" "$message"
    
    if [ "$step" -eq "$total" ]; then
        echo  # New line when complete
    fi
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Wait for service to be ready
wait_for_service() {
    local url="$1"
    local timeout="${2:-30}"
    local interval="${3:-2}"
    
    log "INFO" "Waiting for service at $url (timeout: ${timeout}s)"
    
    for ((i=1; i<=timeout; i+=interval)); do
        if curl -s -f "$url/v1/health" >/dev/null 2>&1; then
            log "INFO" "Service is ready!"
            return 0
        fi
        
        progress "$i" "$timeout" "Checking service health..."
        sleep "$interval"
    done
    
    log "ERROR" "Service failed to start within ${timeout}s"
    return 1
}

# Validate API key
validate_api_key() {
    if [ -z "$API_KEY" ]; then
        log "ERROR" "API_KEY not set. Export AGENTHUB_API_KEY=your-key"
        return 1
    fi
}

# Make API call with error handling
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    local expected_status="${4:-200}"
    
    local url="${AGENTHUB_URL}${endpoint}"
    local response_file
    response_file=$(mktemp)
    local status_code
    
    log "DEBUG" "API Call: $method $url"
    
    if [ -n "$data" ]; then
        status_code=$(curl -s -w "%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -H "X-AgentHub-Key: $API_KEY" \
            -d "$data" \
            "$url" -o "$response_file")
    else
        status_code=$(curl -s -w "%{http_code}" -X "$method" \
            -H "X-AgentHub-Key: $API_KEY" \
            "$url" -o "$response_file")
    fi
    
    if [ "$status_code" != "$expected_status" ]; then
        log "ERROR" "API call failed. Status: $status_code, Response: $(cat "$response_file")"
        rm -f "$response_file"
        return 1
    fi
    
    cat "$response_file"
    rm -f "$response_file"
    return 0
}

# =============================================================================
# SYSTEM MANAGEMENT FUNCTIONS
# =============================================================================

# Start Agent Hub system
hub_start() {
    log "INFO" "Starting Agent Hub system..."
    
    # Step 1: Check prerequisites
    log "INFO" "Step 1/6: Checking prerequisites"
    if ! command_exists docker; then
        log "ERROR" "Docker not found. Please install Docker first."
        return 1
    fi
    
    if ! command_exists docker-compose; then
        log "ERROR" "Docker Compose not found. Please install Docker Compose first."
        return 1
    fi
    
    # Step 2: Create necessary directories
    log "INFO" "Step 2/6: Creating directories"
    mkdir -p "$LOGS_DIR" "$TEMP_DIR"
    mkdir -p "${PROJECT_ROOT}/data/sqlite"
    mkdir -p "${PROJECT_ROOT}/data/zvec"
    mkdir -p "${PROJECT_ROOT}/data/redis"
    mkdir -p "${PROJECT_ROOT}/data/artifacts"
    
    # Step 3: Start services
    log "INFO" "Step 3/6: Starting Docker services"
    cd "$PROJECT_ROOT"
    
    if ! docker-compose up -d; then
        log "ERROR" "Failed to start Docker services"
        return 1
    fi
    
    # Step 4: Wait for services to be ready
    log "INFO" "Step 4/6: Waiting for services to be ready"
    wait_for_service "$AGENTHUB_URL" 60 3
    
    # Step 5: Initialize database if needed
    log "INFO" "Step 5/6: Initializing database"
    if ! api_call "GET" "/v1/health" "" "200" >/dev/null; then
        log "WARN" "Health check failed, attempting to initialize database"
        docker-compose exec agenthub python scripts/init_db.py || true
    fi
    
    # Step 6: Verify system status
    log "INFO" "Step 6/6: Verifying system status"
    local health_response
    health_response=$(api_call "GET" "/v1/health")
    
    if echo "$health_response" | jq -e '.status == "healthy"' >/dev/null 2>&1; then
        log "INFO" "✅ Agent Hub started successfully!"
        log "INFO" "🌐 API URL: $AGENTHUB_URL"
        log "INFO" "🔌 WebSocket URL: $AGENTHUB_WS_URL"
        return 0
    else
        log "ERROR" "System health check failed"
        return 1
    fi
}

# Stop Agent Hub system
hub_stop() {
    log "INFO" "Stopping Agent Hub system..."
    
    cd "$PROJECT_ROOT"
    
    # Step 1: Gracefully disconnect all agents
    log "INFO" "Step 1/3: Gracefully disconnecting agents"
    if api_call "GET" "/v1/health" "" "200" >/dev/null 2>&1; then
        api_call "POST" "/v1/admin/shutdown-prepare" || true
        sleep 5
    fi
    
    # Step 2: Stop services
    log "INFO" "Step 2/3: Stopping Docker services"
    docker-compose down
    
    # Step 3: Cleanup
    log "INFO" "Step 3/3: Cleaning up temporary files"
    rm -rf "$TEMP_DIR"/*.tmp 2>/dev/null || true
    
    log "INFO" "✅ Agent Hub stopped successfully"
}

# Restart Agent Hub system
hub_restart() {
    log "INFO" "Restarting Agent Hub system..."
    hub_stop
    sleep 3
    hub_start
}

# Get system status
hub_status() {
    log "INFO" "Checking Agent Hub status..."
    
    # Check if services are running
    cd "$PROJECT_ROOT"
    local running_services
    running_services=$(docker-compose ps --services --filter "status=running" 2>/dev/null | wc -l)
    
    if [ "$running_services" -eq 0 ]; then
        log "INFO" "❌ Agent Hub is not running"
        return 1
    fi
    
    # Check API health
    if ! api_call "GET" "/v1/health" "" "200" >/dev/null 2>&1; then
        log "WARN" "⚠️  Services running but API unhealthy"
        return 1
    fi
    
    # Get detailed status
    local health_data
    health_data=$(api_call "GET" "/v1/health")
    
    local agent_count
    agent_count=$(echo "$health_data" | jq -r '.agents.connected // 0')
    
    local task_count
    task_count=$(echo "$health_data" | jq -r '.tasks.active // 0')
    
    log "INFO" "✅ Agent Hub is running"
    log "INFO" "👥 Connected agents: $agent_count"
    log "INFO" "📋 Active tasks: $task_count"
    log "INFO" "🌐 API URL: $AGENTHUB_URL"
    
    return 0
}

# =============================================================================
# AGENT MANAGEMENT FUNCTIONS
# =============================================================================

# Register agent with the hub
agent_register() {
    local agent_name="$1"
    local capabilities="$2"  # Comma-separated list
    local labels="${3:-}"    # Optional key=value pairs
    
    validate_api_key
    
    log "INFO" "Registering agent: $agent_name"
    
    # Step 1: Validate inputs
    log "INFO" "Step 1/4: Validating inputs"
    if [ -z "$agent_name" ] || [ -z "$capabilities" ]; then
        log "ERROR" "Usage: agent_register <name> <capabilities> [labels]"
        log "ERROR" "Example: agent_register 'claude-fe' 'react,typescript,testing'"
        return 1
    fi
    
    # Step 2: Convert capabilities to JSON array
    log "INFO" "Step 2/4: Processing capabilities"
    local caps_array
    caps_array=$(echo "$capabilities" | sed 's/,/","/g' | sed 's/^/"/' | sed 's/$/"/')
    caps_array="[$caps_array]"
    
    # Step 3: Build registration payload
    log "INFO" "Step 3/4: Building registration payload"
    local payload
    payload=$(cat <<EOF
{
    "agent_name": "$agent_name",
    "capabilities": $caps_array
}
EOF
)
    
    # Add labels if provided
    if [ -n "$labels" ]; then
        local labels_json="{}"
        # TODO: Parse key=value pairs into JSON
        payload=$(echo "$payload" | jq --argjson labels "$labels_json" '. + {labels: $labels}')
    fi
    
    # Step 4: Register agent
    log "INFO" "Step 4/4: Sending registration request"
    local response
    if response=$(api_call "POST" "/v1/agents/register" "$payload" "201"); then
        local agent_id
        agent_id=$(echo "$response" | jq -r '.data.agent_id')
        log "INFO" "✅ Agent registered successfully"
        log "INFO" "🆔 Agent ID: $agent_id"
        log "INFO" "🎯 Capabilities: $capabilities"
        
        # Save agent info for future reference
        echo "$response" > "$TEMP_DIR/agent_${agent_id}.json"
        return 0
    else
        log "ERROR" "Failed to register agent"
        return 1
    fi
}

# Send heartbeat for agent
agent_heartbeat() {
    local agent_id="$1"
    local current_task="${2:-}"
    local status="${3:-online}"
    
    validate_api_key
    
    log "DEBUG" "Sending heartbeat for agent: $agent_id"
    
    local payload
    payload=$(cat <<EOF
{
    "status": "$status",
    "current_task": "$current_task"
}
EOF
)
    
    if api_call "POST" "/v1/agents/$agent_id/heartbeat" "$payload" "200" >/dev/null; then
        log "DEBUG" "Heartbeat sent successfully"
        return 0
    else
        log "ERROR" "Failed to send heartbeat"
        return 1
    fi
}

# Disconnect agent gracefully
agent_disconnect() {
    local agent_id="$1"
    
    validate_api_key
    
    log "INFO" "Disconnecting agent: $agent_id"
    
    # Step 1: Complete any active tasks
    log "INFO" "Step 1/3: Checking for active tasks"
    local active_tasks
    active_tasks=$(api_call "GET" "/v1/agents/$agent_id/tasks?status=claimed,running")
    
    if echo "$active_tasks" | jq -e '.data | length > 0' >/dev/null 2>&1; then
        log "WARN" "Agent has active tasks. Attempting graceful completion..."
        # Give agent time to complete tasks
        sleep 10
    fi
    
    # Step 2: Release any held locks
    log "INFO" "Step 2/3: Releasing resource locks"
    api_call "POST" "/v1/locks/release-all" "{\"owner_agent_id\": \"$agent_id\"}" "200" >/dev/null || true
    
    # Step 3: Send disconnect signal
    log "INFO" "Step 3/3: Sending disconnect signal"
    if api_call "POST" "/v1/agents/$agent_id/disconnect" "{}" "200" >/dev/null; then
        log "INFO" "✅ Agent disconnected successfully"
        
        # Clean up temp files
        rm -f "$TEMP_DIR/agent_${agent_id}.json"
        return 0
    else
        log "ERROR" "Failed to disconnect agent"
        return 1
    fi
}

# List all agents
agent_list() {
    validate_api_key
    
    log "INFO" "Fetching agent list..."
    
    local response
    if response=$(api_call "GET" "/v1/agents" "" "200"); then
        echo "$response" | jq -r '.data[] | "\(.id)\t\(.name)\t\(.status)\t\(.capabilities | join(","))"' | \
        while IFS=$'\t' read -r id name status capabilities; do
            printf "%-20s %-15s %-10s %s\n" "$id" "$name" "$status" "$capabilities"
        done
        return 0
    else
        log "ERROR" "Failed to fetch agent list"
        return 1
    fi
}

# =============================================================================
# TASK MANAGEMENT FUNCTIONS
# =============================================================================

# Create a new task
task_create() {
    local title="$1"
    local description="$2"
    local capabilities="$3"  # Comma-separated
    local priority="${4:-50}"
    
    validate_api_key
    
    log "INFO" "Creating task: $title"
    
    # Step 1: Validate inputs
    log "INFO" "Step 1/3: Validating inputs"
    if [ -z "$title" ] || [ -z "$description" ] || [ -z "$capabilities" ]; then
        log "ERROR" "Usage: task_create <title> <description> <capabilities> [priority]"
        return 1
    fi
    
    # Step 2: Build task payload
    log "INFO" "Step 2/3: Building task payload"
    local caps_array
    caps_array=$(echo "$capabilities" | sed 's/,/","/g' | sed 's/^/"/' | sed 's/$/"/')
    caps_array="[$caps_array]"
    
    local payload
    payload=$(cat <<EOF
{
    "title": "$title",
    "description": "$description",
    "required_capabilities": $caps_array,
    "priority": $priority
}
EOF
)
    
    # Step 3: Create task
    log "INFO" "Step 3/3: Creating task"
    local response
    if response=$(api_call "POST" "/v1/tasks" "$payload" "201"); then
        local task_id
        task_id=$(echo "$response" | jq -r '.data.task_id')
        log "INFO" "✅ Task created successfully"
        log "INFO" "🆔 Task ID: $task_id"
        log "INFO" "🎯 Required capabilities: $capabilities"
        echo "$task_id"  # Return task ID for scripting
        return 0
    else
        log "ERROR" "Failed to create task"
        return 1
    fi
}

# Claim next available task for agent
task_claim() {
    local agent_id="$1"
    
    validate_api_key
    
    log "INFO" "Claiming task for agent: $agent_id"
    
    # Step 1: Get next available task
    log "INFO" "Step 1/3: Finding available task"
    local response
    if ! response=$(api_call "GET" "/v1/tasks/next?agent_id=$agent_id" "" "200"); then
        log "WARN" "No tasks available for agent capabilities"
        return 1
    fi
    
    local task_id
    task_id=$(echo "$response" | jq -r '.data.task_id // empty')
    
    if [ -z "$task_id" ]; then
        log "INFO" "No matching tasks available"
        return 1
    fi
    
    # Step 2: Claim the task
    log "INFO" "Step 2/3: Claiming task $task_id"
    if ! api_call "POST" "/v1/tasks/$task_id/claim" "{\"agent_id\": \"$agent_id\"}" "200" >/dev/null; then
        log "ERROR" "Failed to claim task (may have been claimed by another agent)"
        return 1
    fi
    
    # Step 3: Start the task
    log "INFO" "Step 3/3: Starting task execution"
    if api_call "POST" "/v1/tasks/$task_id/start" "{}" "200" >/dev/null; then
        log "INFO" "✅ Task claimed and started"
        log "INFO" "🆔 Task ID: $task_id"
        echo "$task_id"  # Return task ID for scripting
        return 0
    else
        log "ERROR" "Failed to start task"
        return 1
    fi
}

# Complete a task
task_complete() {
    local task_id="$1"
    local result_summary="$2"
    local artifact_ids="${3:-}"  # Comma-separated artifact IDs
    
    validate_api_key
    
    log "INFO" "Completing task: $task_id"
    
    # Step 1: Validate task exists and is running
    log "INFO" "Step 1/3: Validating task status"
    local task_info
    if ! task_info=$(api_call "GET" "/v1/tasks/$task_id" "" "200"); then
        log "ERROR" "Task not found"
        return 1
    fi
    
    local current_status
    current_status=$(echo "$task_info" | jq -r '.data.status')
    if [ "$current_status" != "running" ]; then
        log "ERROR" "Task is not in running state (current: $current_status)"
        return 1
    fi
    
    # Step 2: Build completion payload
    log "INFO" "Step 2/3: Building completion payload"
    local artifacts_array="[]"
    if [ -n "$artifact_ids" ]; then
        artifacts_array=$(echo "$artifact_ids" | sed 's/,/","/g' | sed 's/^/"/' | sed 's/$/"/')
        artifacts_array="[$artifacts_array]"
    fi
    
    local payload
    payload=$(cat <<EOF
{
    "result_summary": "$result_summary",
    "artifact_ids": $artifacts_array
}
EOF
)
    
    # Step 3: Complete the task
    log "INFO" "Step 3/3: Submitting completion"
    if api_call "POST" "/v1/tasks/$task_id/complete" "$payload" "200" >/dev/null; then
        log "INFO" "✅ Task completed successfully"
        return 0
    else
        log "ERROR" "Failed to complete task"
        return 1
    fi
}

# Fail a task
task_fail() {
    local task_id="$1"
    local error_message="$2"
    local retryable="${3:-true}"
    
    validate_api_key
    
    log "INFO" "Failing task: $task_id"
    
    local payload
    payload=$(cat <<EOF
{
    "error_message": "$error_message",
    "retryable": $retryable
}
EOF
)
    
    if api_call "POST" "/v1/tasks/$task_id/fail" "$payload" "200" >/dev/null; then
        log "INFO" "✅ Task marked as failed"
        if [ "$retryable" = "true" ]; then
            log "INFO" "🔄 Task will be retried automatically"
        fi
        return 0
    else
        log "ERROR" "Failed to mark task as failed"
        return 1
    fi
}

# List tasks
task_list() {
    local status_filter="${1:-}"  # Optional status filter
    local agent_filter="${2:-}"   # Optional agent filter
    
    validate_api_key
    
    log "INFO" "Fetching task list..."
    
    local query_params=""
    [ -n "$status_filter" ] && query_params+="status=$status_filter&"
    [ -n "$agent_filter" ] && query_params+="agent_id=$agent_filter&"
    
    local endpoint="/v1/tasks"
    [ -n "$query_params" ] && endpoint+="?${query_params%&}"
    
    local response
    if response=$(api_call "GET" "$endpoint" "" "200"); then
        printf "%-20s %-15s %-10s %-20s %s\n" "TASK_ID" "STATUS" "PRIORITY" "AGENT" "TITLE"
        printf "%s\n" "$(printf '=%.0s' {1..80})"
        
        echo "$response" | jq -r '.data[] | "\(.id)\t\(.status)\t\(.priority)\t\(.claimed_by // "none")\t\(.title)"' | \
        while IFS=$'\t' read -r id status priority agent title; do
            printf "%-20s %-15s %-10s %-20s %s\n" "$id" "$status" "$priority" "$agent" "$title"
        done
        return 0
    else
        log "ERROR" "Failed to fetch task list"
        return 1
    fi
}

# =============================================================================
# ARTIFACT MANAGEMENT FUNCTIONS
# =============================================================================

# Upload artifact file
artifact_upload() {
    local file_path="$1"
    local artifact_type="${2:-file}"
    local task_id="${3:-}"
    local visibility="${4:-public}"
    
    validate_api_key
    
    log "INFO" "Uploading artifact: $(basename "$file_path")"
    
    # Step 1: Validate file exists
    log "INFO" "Step 1/4: Validating file"
    if [ ! -f "$file_path" ]; then
        log "ERROR" "File not found: $file_path"
        return 1
    fi
    
    local file_size
    file_size=$(stat -c%s "$file_path" 2>/dev/null || stat -f%z "$file_path" 2>/dev/null)
    log "INFO" "File size: $file_size bytes"
    
    # Step 2: Calculate checksum
    log "INFO" "Step 2/4: Calculating checksum"
    local checksum
    if command_exists sha256sum; then
        checksum=$(sha256sum "$file_path" | cut -d' ' -f1)
    elif command_exists shasum; then
        checksum=$(shasum -a 256 "$file_path" | cut -d' ' -f1)
    else
        log "WARN" "No SHA256 utility found, skipping checksum"
        checksum=""
    fi
    
    # Step 3: Build metadata
    log "INFO" "Step 3/4: Building metadata"
    local filename
    filename=$(basename "$file_path")
    
    # Step 4: Upload file
    log "INFO" "Step 4/4: Uploading file"
    local response
    if response=$(curl -s -f -X POST \
        -H "X-AgentHub-Key: $API_KEY" \
        -F "file=@$file_path" \
        -F "artifact_type=$artifact_type" \
        -F "visibility=$visibility" \
        $([ -n "$task_id" ] && echo "-F task_id=$task_id") \
        $([ -n "$checksum" ] && echo "-F checksum=$checksum") \
        "$AGENTHUB_URL/v1/artifacts/upload"); then
        
        local artifact_id
        artifact_id=$(echo "$response" | jq -r '.data.artifact_id')
        log "INFO" "✅ Artifact uploaded successfully"
        log "INFO" "🆔 Artifact ID: $artifact_id"
        log "INFO" "📁 Filename: $filename"
        echo "$artifact_id"  # Return artifact ID for scripting
        return 0
    else
        log "ERROR" "Failed to upload artifact"
        return 1
    fi
}

# Download artifact
artifact_download() {
    local artifact_id="$1"
    local output_path="${2:-./}"
    
    validate_api_key
    
    log "INFO" "Downloading artifact: $artifact_id"
    
    # Step 1: Get artifact metadata
    log "INFO" "Step 1/3: Getting artifact metadata"
    local metadata
    if ! metadata=$(api_call "GET" "/v1/artifacts/$artifact_id" "" "200"); then
        log "ERROR" "Artifact not found"
        return 1
    fi
    
    local filename
    filename=$(echo "$metadata" | jq -r '.data.filename')
    
    # Step 2: Determine output path
    log "INFO" "Step 2/3: Determining output path"
    if [ -d "$output_path" ]; then
        output_path="$output_path/$filename"
    fi
    
    # Step 3: Download file
    log "INFO" "Step 3/3: Downloading file to $output_path"
    if curl -s -f \
        -H "X-AgentHub-Key: $API_KEY" \
        -o "$output_path" \
        "$AGENTHUB_URL/v1/artifacts/$artifact_id/download"; then
        
        log "INFO" "✅ Artifact downloaded successfully"
        log "INFO" "📁 Saved to: $output_path"
        return 0
    else
        log "ERROR" "Failed to download artifact"
        return 1
    fi
}

# List artifacts
artifact_list() {
    local task_id="${1:-}"
    local artifact_type="${2:-}"
    
    validate_api_key
    
    log "INFO" "Fetching artifact list..."
    
    local query_params=""
    [ -n "$task_id" ] && query_params+="task_id=$task_id&"
    [ -n "$artifact_type" ] && query_params+="type=$artifact_type&"
    
    local endpoint="/v1/artifacts"
    [ -n "$query_params" ] && endpoint+="?${query_params%&}"
    
    local response
    if response=$(api_call "GET" "$endpoint" "" "200"); then
        printf "%-20s %-15s %-10s %-20s %s\n" "ARTIFACT_ID" "TYPE" "SIZE" "TASK_ID" "FILENAME"
        printf "%s\n" "$(printf '=%.0s' {1..80})"
        
        echo "$response" | jq -r '.data[] | "\(.id)\t\(.artifact_type)\t\(.size_bytes)\t\(.task_id // "none")\t\(.filename)"' | \
        while IFS=$'\t' read -r id type size task filename; do
            printf "%-20s %-15s %-10s %-20s %s\n" "$id" "$type" "$size" "$task" "$filename"
        done
        return 0
    else
        log "ERROR" "Failed to fetch artifact list"
        return 1
    fi
}

# =============================================================================
# KNOWLEDGE SHARING FUNCTIONS
# =============================================================================

# Share knowledge/finding
knowledge_share() {
    local category="$1"        # solution, bug, pattern, etc.
    local content="$2"         # The finding content
    local severity="${3:-info}" # info, warning, critical
    local tags="${4:-}"        # Comma-separated tags
    
    validate_api_key
    
    log "INFO" "Sharing knowledge: $category"
    
    # Step 1: Validate inputs
    log "INFO" "Step 1/3: Validating inputs"
    if [ -z "$category" ] || [ -z "$content" ]; then
        log "ERROR" "Usage: knowledge_share <category> <content> [severity] [tags]"
        return 1
    fi
    
    # Step 2: Build knowledge payload
    log "INFO" "Step 2/3: Building knowledge payload"
    local tags_array="[]"
    if [ -n "$tags" ]; then
        tags_array=$(echo "$tags" | sed 's/,/","/g' | sed 's/^/"/' | sed 's/$/"/')
        tags_array="[$tags_array]"
    fi
    
    local payload
    payload=$(cat <<EOF
{
    "category": "$category",
    "content": "$content",
    "severity": "$severity",
    "tags": $tags_array
}
EOF
)
    
    # Step 3: Share knowledge
    log "INFO" "Step 3/3: Sharing with other agents"
    local response
    if response=$(api_call "POST" "/v1/knowledge/share" "$payload" "201"); then
        local knowledge_id
        knowledge_id=$(echo "$response" | jq -r '.data.knowledge_id')
        log "INFO" "✅ Knowledge shared successfully"
        log "INFO" "🆔 Knowledge ID: $knowledge_id"
        echo "$knowledge_id"  # Return knowledge ID for scripting
        return 0
    else
        log "ERROR" "Failed to share knowledge"
        return 1
    fi
}

# Search knowledge base
knowledge_search() {
    local query="$1"
    local category="${2:-}"
    local limit="${3:-10}"
    
    validate_api_key
    
    log "INFO" "Searching knowledge: $query"
    
    local query_params="q=$(printf '%s' "$query" | jq -sRr @uri)&limit=$limit"
    [ -n "$category" ] && query_params+="&category=$category"
    
    local response
    if response=$(api_call "GET" "/v1/knowledge/search?$query_params" "" "200"); then
        echo "$response" | jq -r '.data[] | "\(.id)\t\(.category)\t\(.severity)\t\(.content)"' | \
        while IFS=$'\t' read -r id category severity content; do
            printf "%-20s %-15s %-10s %s\n" "$id" "$category" "$severity" "${content:0:50}..."
        done
        return 0
    else
        log "ERROR" "Failed to search knowledge"
        return 1
    fi
}

# =============================================================================
# RESOURCE LOCK FUNCTIONS
# =============================================================================

# Acquire resource lock
lock_acquire() {
    local resource_key="$1"
    local agent_id="$2"
    local ttl="${3:-300}"  # 5 minutes default
    
    validate_api_key
    
    log "INFO" "Acquiring lock for: $resource_key"
    
    local payload
    payload=$(cat <<EOF
{
    "resource_key": "$resource_key",
    "owner_agent_id": "$agent_id",
    "ttl_seconds": $ttl
}
EOF
)
    
    if api_call "POST" "/v1/locks/acquire" "$payload" "201" >/dev/null; then
        log "INFO" "✅ Lock acquired successfully"
        log "INFO" "🔒 Resource: $resource_key"
        log "INFO" "⏰ TTL: ${ttl}s"
        return 0
    else
        log "ERROR" "Failed to acquire lock (may be held by another agent)"
        return 1
    fi
}

# Release resource lock
lock_release() {
    local resource_key="$1"
    local agent_id="$2"
    
    validate_api_key
    
    log "INFO" "Releasing lock for: $resource_key"
    
    local payload
    payload=$(cat <<EOF
{
    "resource_key": "$resource_key",
    "owner_agent_id": "$agent_id"
}
EOF
)
    
    if api_call "POST" "/v1/locks/release" "$payload" "200" >/dev/null; then
        log "INFO" "✅ Lock released successfully"
        return 0
    else
        log "ERROR" "Failed to release lock"
        return 1
    fi
}

# List active locks
lock_list() {
    local agent_id="${1:-}"
    
    validate_api_key
    
    log "INFO" "Fetching lock list..."
    
    local query_params=""
    [ -n "$agent_id" ] && query_params="owner_agent_id=$agent_id"
    
    local endpoint="/v1/locks"
    [ -n "$query_params" ] && endpoint+="?$query_params"
    
    local response
    if response=$(api_call "GET" "$endpoint" "" "200"); then
        printf "%-40s %-20s %s\n" "RESOURCE_KEY" "OWNER_AGENT" "EXPIRES_AT"
        printf "%s\n" "$(printf '=%.0s' {1..80})"
        
        echo "$response" | jq -r '.data[] | "\(.resource_key)\t\(.owner_agent_id)\t\(.lease_until)"' | \
        while IFS=$'\t' read -r resource owner expires; do
            printf "%-40s %-20s %s\n" "$resource" "$owner" "$expires"
        done
        return 0
    else
        log "ERROR" "Failed to fetch lock list"
        return 1
    fi
}

# =============================================================================
# PROJECT AUTOMATION FUNCTIONS
# =============================================================================

# Initialize new project for agent coordination
project_init() {
    local project_name="$1"
    local project_path="${2:-./}"
    
    log "INFO" "Initializing project: $project_name"
    
    # Step 1: Create project structure
    log "INFO" "Step 1/5: Creating project structure"
    local full_path="$project_path/$project_name"
    mkdir -p "$full_path"/{scripts,config,logs,temp,artifacts}
    
    # Step 2: Copy automation scripts
    log "INFO" "Step 2/5: Setting up automation scripts"
    cp "$0" "$full_path/scripts/agent_automation.sh"
    chmod +x "$full_path/scripts/agent_automation.sh"
    
    # Step 3: Create configuration files
    log "INFO" "Step 3/5: Creating configuration files"
    cat > "$full_path/config/agent.env" <<EOF
# Agent Hub Configuration
AGENTHUB_URL=http://localhost:7788
AGENTHUB_WS_URL=ws://localhost:7788/v1/agent-connect
AGENTHUB_API_KEY=your-api-key-here

# Agent Configuration
AGENT_NAME=${project_name}-agent
AGENT_CAPABILITIES=code_edit,testing,documentation
AGENT_LABELS=project=$project_name

# Project Configuration
PROJECT_NAME=$project_name
PROJECT_ROOT=$full_path
EOF
    
    # Step 4: Create helper scripts
    log "INFO" "Step 4/5: Creating helper scripts"
    cat > "$full_path/scripts/start.sh" <<'EOF'
#!/bin/bash
source "$(dirname "$0")/../config/agent.env"
"$(dirname "$0")/agent_automation.sh" agent_register "$AGENT_NAME" "$AGENT_CAPABILITIES"
EOF
    chmod +x "$full_path/scripts/start.sh"
    
    cat > "$full_path/scripts/monitor.sh" <<'EOF'
#!/bin/bash
source "$(dirname "$0")/../config/agent.env"
watch -n 5 "$(dirname "$0")/agent_automation.sh" hub_status
EOF
    chmod +x "$full_path/scripts/monitor.sh"
    
    # Step 5: Create README
    log "INFO" "Step 5/5: Creating documentation"
    cat > "$full_path/README.md" <<EOF
# $project_name Agent Project

This project is configured for Agent Hub coordination.

## Quick Start

1. Configure your agent in \`config/agent.env\`
2. Start the Agent Hub: \`scripts/agent_automation.sh hub_start\`
3. Register your agent: \`scripts/start.sh\`
4. Monitor status: \`scripts/monitor.sh\`

## Available Commands

- \`scripts/agent_automation.sh hub_start\` - Start Agent Hub
- \`scripts/agent_automation.sh agent_register <name> <capabilities>\`
- \`scripts/agent_automation.sh task_claim <agent_id>\`
- \`scripts/agent_automation.sh task_complete <task_id> <summary>\`

See agent_automation.sh for full command reference.
EOF
    
    log "INFO" "✅ Project initialized successfully"
    log "INFO" "📁 Location: $full_path"
    log "INFO" "📖 Next steps:"
    log "INFO" "   1. cd $full_path"
    log "INFO" "   2. Edit config/agent.env"
    log "INFO" "   3. scripts/agent_automation.sh hub_start"
}

# Run automated task workflow
project_run_workflow() {
    local workflow_file="$1"
    local agent_id="$2"
    
    log "INFO" "Running workflow: $workflow_file"
    
    if [ ! -f "$workflow_file" ]; then
        log "ERROR" "Workflow file not found: $workflow_file"
        return 1
    fi
    
    # Read workflow steps
    local step_count
    step_count=$(grep -c "^STEP:" "$workflow_file" || echo 0)
    
    if [ "$step_count" -eq 0 ]; then
        log "ERROR" "No workflow steps found in file"
        return 1
    fi
    
    log "INFO" "Found $step_count workflow steps"
    
    local current_step=1
    while IFS= read -r line; do
        if [[ "$line" =~ ^STEP: ]]; then
            local step_description="${line#STEP: }"
            log "INFO" "Executing step $current_step/$step_count: $step_description"
            
            # Create task for this step
            local task_id
            task_id=$(task_create "Workflow Step $current_step" "$step_description" "automation" 10)
            
            if [ -n "$task_id" ]; then
                # Wait for task completion or timeout
                local timeout=300  # 5 minutes
                local elapsed=0
                
                while [ $elapsed -lt $timeout ]; do
                    local task_status
                    task_status=$(api_call "GET" "/v1/tasks/$task_id" | jq -r '.data.status')
                    
                    case "$task_status" in
                        "completed")
                            log "INFO" "✅ Step $current_step completed"
                            break
                            ;;
                        "failed")
                            log "ERROR" "❌ Step $current_step failed"
                            return 1
                            ;;
                        *)
                            sleep 5
                            elapsed=$((elapsed + 5))
                            ;;
                    esac
                done
                
                if [ $elapsed -ge $timeout ]; then
                    log "ERROR" "⏰ Step $current_step timed out"
                    return 1
                fi
            else
                log "ERROR" "Failed to create task for step $current_step"
                return 1
            fi
            
            current_step=$((current_step + 1))
        fi
    done < "$workflow_file"
    
    log "INFO" "✅ Workflow completed successfully"
}

# =============================================================================
# MONITORING AND MAINTENANCE FUNCTIONS
# =============================================================================

# Monitor system health continuously
monitor_health() {
    local interval="${1:-30}"  # seconds
    
    log "INFO" "Starting health monitor (interval: ${interval}s)"
    log "INFO" "Press Ctrl+C to stop monitoring"
    
    while true; do
        clear
        echo "=== Agent Hub Health Monitor ==="
        echo "$(date)"
        echo
        
        # System status
        if hub_status >/dev/null 2>&1; then
            echo "🟢 System Status: HEALTHY"
        else
            echo "🔴 System Status: UNHEALTHY"
        fi
        
        # Agent status
        local agent_response
        if agent_response=$(api_call "GET" "/v1/agents" "" "200" 2>/dev/null); then
            local agent_count
            agent_count=$(echo "$agent_response" | jq -r '.data | length')
            echo "👥 Connected Agents: $agent_count"
        else
            echo "👥 Connected Agents: ERROR"
        fi
        
        # Task status
        local task_response
        if task_response=$(api_call "GET" "/v1/tasks" "" "200" 2>/dev/null); then
            local queued_tasks
            queued_tasks=$(echo "$task_response" | jq -r '[.data[] | select(.status == "queued")] | length')
            local running_tasks  
            running_tasks=$(echo "$task_response" | jq -r '[.data[] | select(.status == "running")] | length')
            echo "📋 Queued Tasks: $queued_tasks"
            echo "🏃 Running Tasks: $running_tasks"
        else
            echo "📋 Task Status: ERROR"
        fi
        
        # Resource usage
        if command_exists docker; then
            local container_stats
            container_stats=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | grep -v CONTAINER || echo "No containers")
            echo
            echo "📊 Container Stats:"
            echo "$container_stats"
        fi
        
        sleep "$interval"
    done
}

# Clean up old data
cleanup() {
    local days="${1:-7}"  # Keep data for 7 days by default
    
    log "INFO" "Starting cleanup (keeping data newer than $days days)"
    
    # Step 1: Clean log files
    log "INFO" "Step 1/4: Cleaning old log files"
    find "$LOGS_DIR" -name "*.log" -type f -mtime +$days -delete 2>/dev/null || true
    
    # Step 2: Clean temporary files
    log "INFO" "Step 2/4: Cleaning temporary files"
    find "$TEMP_DIR" -type f -mtime +1 -delete 2>/dev/null || true
    
    # Step 3: Clean up old artifacts (if configured)
    log "INFO" "Step 3/4: Cleaning old artifacts"
    # This would typically call the API to clean up old artifacts
    # api_call "POST" "/v1/admin/cleanup" "{\"days\": $days}" "200" >/dev/null || true
    
    # Step 4: Docker cleanup
    log "INFO" "Step 4/4: Docker cleanup"
    if command_exists docker; then
        docker system prune -f >/dev/null 2>&1 || true
    fi
    
    log "INFO" "✅ Cleanup completed"
}

# Backup system data
backup() {
    local backup_path="${1:-./backups}"
    local timestamp
    timestamp=$(date '+%Y%m%d_%H%M%S')
    
    log "INFO" "Creating backup: $timestamp"
    
    # Step 1: Create backup directory
    log "INFO" "Step 1/4: Creating backup directory"
    mkdir -p "$backup_path/$timestamp"
    
    # Step 2: Backup database
    log "INFO" "Step 2/4: Backing up database"
    if docker-compose ps agenthub >/dev/null 2>&1; then
        docker-compose exec agenthub sqlite3 /app/data/sqlite/agenthub.db ".backup /tmp/backup.db"
        docker cp "$(docker-compose ps -q agenthub):/tmp/backup.db" "$backup_path/$timestamp/agenthub.db"
    fi
    
    # Step 3: Backup vector data
    log "INFO" "Step 3/4: Backing up vector data"
    if [ -d "${PROJECT_ROOT}/data/zvec" ]; then
        tar -czf "$backup_path/$timestamp/zvec.tar.gz" -C "${PROJECT_ROOT}/data" zvec/
    fi
    
    # Step 4: Backup artifacts
    log "INFO" "Step 4/4: Backing up artifacts"
    if [ -d "${PROJECT_ROOT}/data/artifacts" ]; then
        tar -czf "$backup_path/$timestamp/artifacts.tar.gz" -C "${PROJECT_ROOT}/data" artifacts/
    fi
    
    log "INFO" "✅ Backup completed: $backup_path/$timestamp"
}

# =============================================================================
# MAIN COMMAND DISPATCHER
# =============================================================================

# Show help
show_help() {
    cat <<EOF
Agent Hub Automation Scripts
============================

SYSTEM MANAGEMENT:
  hub_start                                 Start Agent Hub system
  hub_stop                                  Stop Agent Hub system
  hub_restart                               Restart Agent Hub system
  hub_status                                Check system status
  
AGENT MANAGEMENT:
  agent_register <name> <capabilities>      Register new agent
  agent_heartbeat <agent_id> [task] [status] Send heartbeat
  agent_disconnect <agent_id>               Disconnect agent
  agent_list                                List all agents
  
TASK MANAGEMENT:
  task_create <title> <desc> <caps> [priority] Create new task
  task_claim <agent_id>                     Claim next available task
  task_complete <task_id> <summary> [artifacts] Complete task
  task_fail <task_id> <error> [retryable]   Mark task as failed
  task_list [status] [agent]               List tasks
  
ARTIFACT MANAGEMENT:
  artifact_upload <file> [type] [task] [visibility] Upload artifact
  artifact_download <id> [output_path]     Download artifact
  artifact_list [task_id] [type]           List artifacts
  
KNOWLEDGE SHARING:
  knowledge_share <category> <content> [severity] [tags] Share knowledge
  knowledge_search <query> [category] [limit] Search knowledge base
  
RESOURCE LOCKS:
  lock_acquire <resource> <agent> [ttl]    Acquire resource lock
  lock_release <resource> <agent>          Release resource lock
  lock_list [agent_id]                     List active locks
  
PROJECT AUTOMATION:
  project_init <name> [path]               Initialize new project
  project_run_workflow <workflow> <agent>  Run workflow file
  
MONITORING & MAINTENANCE:
  monitor_health [interval]                Monitor system health
  cleanup [days]                           Clean up old data
  backup [path]                            Backup system data

EXAMPLES:
  $0 hub_start
  $0 agent_register "claude-fe" "react,typescript,testing"
  $0 task_create "Fix CORS issue" "Add CORS middleware" "fastapi,backend"
  $0 artifact_upload "./report.pdf" "report" "task_123"
  $0 knowledge_share "solution" "Fixed CORS by adding origins=['*']"

ENVIRONMENT VARIABLES:
  AGENTHUB_URL       Hub API URL (default: http://localhost:7788)
  AGENTHUB_API_KEY   API key for authentication (required for most operations)
  
For more information, see the documentation at:
- CLAUDE.md
- DEVELOPMENT_RULES.md  
- ARCHITECTURE_EVALUATION.md
EOF
}

# Main function
main() {
    local command="${1:-help}"
    shift || true
    
    case "$command" in
        # System Management
        "hub_start")        hub_start "$@" ;;
        "hub_stop")         hub_stop "$@" ;;
        "hub_restart")      hub_restart "$@" ;;
        "hub_status")       hub_status "$@" ;;
        
        # Agent Management
        "agent_register")   agent_register "$@" ;;
        "agent_heartbeat")  agent_heartbeat "$@" ;;
        "agent_disconnect") agent_disconnect "$@" ;;
        "agent_list")       agent_list "$@" ;;
        
        # Task Management
        "task_create")      task_create "$@" ;;
        "task_claim")       task_claim "$@" ;;
        "task_complete")    task_complete "$@" ;;
        "task_fail")        task_fail "$@" ;;
        "task_list")        task_list "$@" ;;
        
        # Artifact Management
        "artifact_upload")  artifact_upload "$@" ;;
        "artifact_download") artifact_download "$@" ;;
        "artifact_list")    artifact_list "$@" ;;
        
        # Knowledge Sharing
        "knowledge_share")  knowledge_share "$@" ;;
        "knowledge_search") knowledge_search "$@" ;;
        
        # Resource Locks
        "lock_acquire")     lock_acquire "$@" ;;
        "lock_release")     lock_release "$@" ;;
        "lock_list")        lock_list "$@" ;;
        
        # Project Automation
        "project_init")     project_init "$@" ;;
        "project_run_workflow") project_run_workflow "$@" ;;
        
        # Monitoring & Maintenance
        "monitor_health")   monitor_health "$@" ;;
        "cleanup")          cleanup "$@" ;;
        "backup")           backup "$@" ;;
        
        # Help
        "help"|"-h"|"--help") show_help ;;
        
        *)
            log "ERROR" "Unknown command: $command"
            echo
            show_help
            exit 1
            ;;
    esac
}

# Only run main if script is executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi