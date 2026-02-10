#!/bin/bash
# =============================================================================
# build-cups3.sh - Build and run OpenPrinting CUPS 3.0 in Docker
# =============================================================================
#
# This script builds the complete CUPS 3.0 stack from source inside a Docker
# container. CUPS 3.0 consists of three independent components:
#
#   1. libcups (v3.0.0)   - New CUPS library (breaks compat with 2.x)
#   2. PAPPL  (v2.x dev)  - Printer Application Framework
#   3. cups-local          - Per-user local printing server
#   4. cups-sharing        - Network sharing server
#
# Both cups-local and cups-sharing are PAPPL-based and require libcups3.
#
# IMPORTANT NOTES:
#   - libcups v3.0.0 is a stable release.
#   - PAPPL v2.0 has NOT been formally released; master branch is used.
#   - cups-local and cups-sharing are alpha quality (built from master).
#   - The OpenPrinting/cups GitHub repo is CUPS 2.x, NOT 3.x.
#
# Usage:
#   ./build-cups3.sh [build|run|run-sharing|tools|shell|clean|help]
#
# References:
#   https://openprinting.github.io/cups/cups3.html
#   https://github.com/OpenPrinting/libcups
#   https://github.com/OpenPrinting/cups-local
#   https://github.com/OpenPrinting/cups-sharing
#   https://github.com/michaelrsweet/pappl
# =============================================================================

set -euo pipefail

IMAGE_NAME="cups3"
IMAGE_TAG="latest"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
check_docker() {
    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed or not in PATH."
        echo "  Install Docker: https://docs.docker.com/engine/install/"
        exit 1
    fi
    if ! docker info &>/dev/null 2>&1; then
        log_error "Docker daemon is not running or current user lacks permissions."
        echo "  Try: sudo systemctl start docker"
        echo "  Or:  sudo usermod -aG docker \$USER"
        exit 1
    fi
}

check_platform() {
    local arch
    arch="$(uname -m)"
    if [ "$arch" != "x86_64" ]; then
        log_warn "This script targets x86_64 (amd64). Detected: ${arch}"
        log_warn "The build may still work but is untested on this architecture."
    fi
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
cmd_build() {
    log_info "Building CUPS 3.0 Docker image: ${FULL_IMAGE}"
    echo ""
    echo "  Components to build:"
    echo "    1. libcups    v3.0.0  (stable)   - CUPS 3.x library"
    echo "    2. PAPPL      v2.x    (master)   - Printer Application Framework"
    echo "    3. cups-local          (master)   - Local printing server (alpha)"
    echo "    4. cups-sharing        (master)   - Sharing server (alpha)"
    echo ""
    log_warn "cups-local and cups-sharing are alpha-quality software."
    log_warn "PAPPL v2.0 is built from master (no stable release yet)."
    echo ""

    docker build \
        --platform linux/amd64 \
        -t "${FULL_IMAGE}" \
        -f "${SCRIPT_DIR}/Dockerfile" \
        "${SCRIPT_DIR}"

    echo ""
    log_ok "Docker image built successfully: ${FULL_IMAGE}"
    echo ""
    echo "  Next steps:"
    echo "    ./build-cups3.sh run           # Start cups-local"
    echo "    ./build-cups3.sh run-sharing   # Start cups-sharing (port 631)"
    echo "    ./build-cups3.sh tools         # Explore available tools"
    echo "    ./build-cups3.sh shell         # Open a shell in the container"
}

cmd_run_local() {
    log_info "Starting cups-local (local printing server)..."
    docker run -it --rm \
        --name cups3-local \
        --network host \
        "${FULL_IMAGE}" cups-local "$@"
}

cmd_run_sharing() {
    log_info "Starting cups-sharing (network sharing server on port 631)..."
    docker run -it --rm \
        --name cups3-sharing \
        -p 631:631 \
        --privileged \
        "${FULL_IMAGE}" cups-sharing "$@"
}

cmd_tools() {
    log_info "Opening CUPS 3.0 tools environment..."
    docker run -it --rm \
        --name cups3-tools \
        --network host \
        "${FULL_IMAGE}" tools
}

cmd_shell() {
    log_info "Opening shell in CUPS 3.0 container..."
    docker run -it --rm \
        --name cups3-shell \
        --network host \
        "${FULL_IMAGE}" shell
}

cmd_version() {
    docker run --rm "${FULL_IMAGE}" version
}

cmd_clean() {
    log_info "Removing CUPS 3.0 Docker image..."
    docker rmi "${FULL_IMAGE}" 2>/dev/null && log_ok "Image removed." || log_warn "Image not found."
    # Also remove builder cache
    docker builder prune -f --filter "label=cups3" 2>/dev/null || true
}

cmd_help() {
    cat <<'HELP'
build-cups3.sh - Build and run OpenPrinting CUPS 3.0 in Docker

CUPS 3.0 Architecture:
  CUPS 3 is a complete redesign that eliminates printer drivers and splits
  the system into three independent components:

  libcups (v3.0.0)   New C library for HTTP/HTTPS/IPP (not binary-compatible
                      with libcups 1.x/2.x)
  cups-local          Per-user local spooler with temporary queues, basic
                      filtering, runs as a normal user
  cups-sharing        Network sharing server with permanent queues, job
                      accounting, web UI, runs as root

  Both servers are built on the PAPPL framework.

  NOTE: The GitHub repo "OpenPrinting/cups" is CUPS 2.x.
        CUPS 3.x lives in "libcups", "cups-local", and "cups-sharing".

Usage:
  ./build-cups3.sh <command>

Commands:
  build          Build the Docker image (compiles all components from source)
  run            Start cups-local (local printing server)
  run-sharing    Start cups-sharing (network server, port 631)
  tools          Open interactive shell with CUPS 3.0 tools
  shell          Open a plain bash shell in the container
  version        Show installed component versions
  clean          Remove the Docker image
  help           Show this help message

Examples:
  # Build the image
  ./build-cups3.sh build

  # Discover printers on the network
  ./build-cups3.sh shell
  > ippfind

  # Run a virtual IPP Everywhere printer for testing
  ./build-cups3.sh shell
  > ippeveprinter -v "Test Printer"

  # Start the local server
  ./build-cups3.sh run

  # Start the sharing server with web UI on port 631
  ./build-cups3.sh run-sharing
HELP
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    check_docker
    check_platform

    local cmd="${1:-help}"
    shift || true

    case "$cmd" in
        build)        cmd_build "$@" ;;
        run)          cmd_run_local "$@" ;;
        run-sharing)  cmd_run_sharing "$@" ;;
        tools)        cmd_tools "$@" ;;
        shell)        cmd_shell "$@" ;;
        version)      cmd_version "$@" ;;
        clean)        cmd_clean "$@" ;;
        help|--help|-h) cmd_help ;;
        *)
            log_error "Unknown command: $cmd"
            echo ""
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"
