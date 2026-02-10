#!/bin/bash
# =============================================================================
# docker-entrypoint.sh - CUPS 3.0 Container Entrypoint
# =============================================================================
set -e

echo "============================================"
echo " OpenPrinting CUPS 3.0 Container"
echo "============================================"

# Show installed component versions
echo ""
echo "Installed tools:"
for tool in ipptool ippfind ippeveprinter ipptransform; do
    if command -v "$tool" &>/dev/null; then
        echo "  $tool: $(command -v "$tool")"
    fi
done

echo ""
echo "Libraries:"
ldconfig -p 2>/dev/null | grep -E "libcups3|libpappl" || true
echo ""

# Start D-Bus if available (needed by cups-local for D-Bus notifications)
if [ -x /usr/bin/dbus-daemon ] && [ ! -e /run/dbus/pid ]; then
    mkdir -p /run/dbus
    dbus-daemon --system --fork 2>/dev/null || true
fi

# Start Avahi for mDNS/DNS-SD discovery
if [ -x /usr/sbin/avahi-daemon ]; then
    # Avahi requires D-Bus
    mkdir -p /run/avahi-daemon
    avahi-daemon --daemonize --no-chroot 2>/dev/null || true
fi

case "${1:-help}" in
    cups-local)
        echo "Starting cups-local (local printing server)..."
        echo "  cups-local runs as a per-user spooler with temporary queues."
        echo ""
        shift || true
        if command -v cupslocald &>/dev/null; then
            exec cupslocald "$@"
        else
            echo "ERROR: cupslocald not found. cups-local may not have built correctly."
            exit 1
        fi
        ;;
    cups-sharing)
        echo "Starting cups-sharing (sharing server on port 631)..."
        echo "  cups-sharing provides network printer sharing with"
        echo "  permanent queues, job accounting, and web interface."
        echo ""
        shift || true
        if command -v cupssharingd &>/dev/null; then
            exec cupssharingd "$@"
        else
            echo "ERROR: cupssharingd not found."
            echo "  cups-sharing is the least mature CUPS 3.0 component and"
            echo "  may not have a working daemon binary yet."
            echo "  Check: https://github.com/OpenPrinting/cups-sharing"
            exit 1
        fi
        ;;
    tools)
        echo "Available CUPS 3.0 tools:"
        echo "  ipptool       - IPP protocol testing"
        echo "  ippfind       - Discover IPP printers via DNS-SD/mDNS"
        echo "  ippeveprinter - Virtual IPP Everywhere printer"
        echo "  ipptransform  - File format conversion"
        echo ""
        echo "Example commands:"
        echo "  ippfind                          # Discover printers"
        echo "  ipptool -tv ipp://printer/ipp/print get-printer-attributes.test"
        echo "  ippeveprinter -v 'Test Printer'  # Start a virtual printer"
        echo ""
        echo "Dropping to shell..."
        exec /bin/bash
        ;;
    version)
        echo "Component versions:"
        local v
        v="$(pkg-config --modversion cups3 2>/dev/null)" && echo "  libcups3: $v" || echo "  libcups3: (version unavailable via pkg-config)"
        v="$(pkg-config --modversion pappl2 2>/dev/null)" && echo "  pappl2: $v" || echo "  pappl2: (version unavailable via pkg-config)"
        echo ""
        echo "Binaries:"
        command -v cupslocald &>/dev/null && echo "  cupslocald: $(command -v cupslocald)" || echo "  cupslocald: not found"
        command -v cupssharingd &>/dev/null && echo "  cupssharingd: $(command -v cupssharingd)" || echo "  cupssharingd: not found"
        ;;
    shell|bash)
        exec /bin/bash
        ;;
    help|--help|-h)
        echo "Usage: docker run [options] cups3 <command>"
        echo ""
        echo "Commands:"
        echo "  cups-local    Start the local printing server (default)"
        echo "  cups-sharing  Start the sharing/network server"
        echo "  tools         List available tools and drop to shell"
        echo "  version       Show installed component versions"
        echo "  shell         Open a bash shell"
        echo "  help          Show this help message"
        echo ""
        echo "Examples:"
        echo "  docker run -it cups3 cups-local"
        echo "  docker run -it -p 631:631 cups3 cups-sharing"
        echo "  docker run -it cups3 tools"
        echo "  docker run -it --network=host cups3 shell"
        ;;
    *)
        exec "$@"
        ;;
esac
