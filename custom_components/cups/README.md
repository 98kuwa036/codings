# CUPS (OpenPrinting) Integration for Home Assistant

A comprehensive Home Assistant custom integration for monitoring and managing CUPS (Common Unix Printing System) and IPP (Internet Printing Protocol) printers.

## Features

### Sensors

- **Printer Status**: Monitor printer state (idle, printing, stopped)
- **Ink/Toner Levels**: Individual sensors for each ink or toner cartridge
- **Print Queue Length**: Track the number of pending print jobs
- **Connectivity**: Binary sensor showing printer online/offline status

### Device Information

- Printer name and model
- Manufacturer information
- Firmware version
- Serial number
- Uptime
- Location and description

### Services (Planned)

The following services are defined but require additional IPP operations not currently exposed by the pyipp library:

- `cups.pause_printer`: Pause the printer
- `cups.resume_printer`: Resume a paused printer
- `cups.cancel_all_jobs`: Cancel all pending jobs
- `cups.pause_job`: Pause a specific job
- `cups.resume_job`: Resume a paused job
- `cups.cancel_job`: Cancel a specific job

## Installation

### HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Search for "CUPS" in HACS
3. Click "Install"
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/cups` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

### Automatic Discovery (Recommended)

The integration supports automatic discovery of network printers via Zeroconf/mDNS:

1. Go to **Settings** → **Devices & Services**
2. Wait for discovered printers to appear
3. Click **Configure** on the discovered printer
4. Confirm the settings

### Manual Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "CUPS"
4. Enter your printer details:
   - **Host**: Hostname or IP address of the printer (e.g., `192.168.1.100` or `printer.local`)
   - **Port**: IPP port (default: `631`)
   - **SSL**: Enable if the printer uses HTTPS
   - **Verify SSL**: Enable SSL certificate verification
   - **Base Path**: Base path for IPP requests (default: `/ipp/print`)

## Examples

### Display Printer Status in Lovelace

```yaml
type: entities
entities:
  - entity: sensor.printer_status
  - entity: binary_sensor.printer_connectivity
  - entity: sensor.printer_print_queue
```

### Monitor Ink Levels

```yaml
type: glance
entities:
  - entity: sensor.printer_black_toner
  - entity: sensor.printer_cyan_toner
  - entity: sensor.printer_magenta_toner
  - entity: sensor.printer_yellow_toner
```

### Automation: Low Ink Alert

```yaml
automation:
  - alias: "Printer Low Ink Alert"
    trigger:
      - platform: numeric_state
        entity_id:
          - sensor.printer_black_toner
          - sensor.printer_cyan_toner
          - sensor.printer_magenta_toner
          - sensor.printer_yellow_toner
        below: 20
    action:
      - service: notify.mobile_app
        data:
          message: "Printer {{ trigger.to_state.name }} is low ({{ trigger.to_state.state }}%)"
```

### Automation: Printer Offline Alert

```yaml
automation:
  - alias: "Printer Offline Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.printer_connectivity
        to: "off"
        for:
          minutes: 5
    action:
      - service: notify.mobile_app
        data:
          message: "Printer is offline"
```

## Technical Details

### Supported Protocols

- **IPP (Internet Printing Protocol)**: RFC 8011
- **IPPS (IPP over SSL/TLS)**: Secure printing
- **Zeroconf/mDNS**: Automatic printer discovery

### Dependencies

- **pyipp**: Python IPP client library (v0.14.6)
- Supports IPP 1.1, 2.0, and 2.1

### Data Update Interval

The integration polls printer data every 30 seconds by default.

### Attributes

Each sensor provides comprehensive attributes including:

**Printer Status Sensor:**
- Printer name
- Printer URI
- State (numeric)
- State message
- State reasons
- Make and model
- Location
- Info
- Serial number
- Uptime

**Marker Level Sensors:**
- Marker index
- Marker name
- Marker type (toner, ink, ribbon, etc.)
- Marker color
- Level percentage

## Compatibility

### Tested Printers

- HP LaserJet series
- HP OfficeJet series
- Canon PIXMA series
- Epson EcoTank series
- Brother HL series
- Generic CUPS/IPP-compatible printers

### Requirements

- Printer must support IPP protocol
- Printer must be accessible on the network
- Home Assistant 2023.1 or later

## Troubleshooting

### Printer Not Discovered

1. Ensure the printer is on the same network as Home Assistant
2. Check that mDNS is enabled on your network
3. Try manual configuration instead

### Connection Errors

1. Verify the hostname/IP address is correct
2. Check that the port is accessible (default: 631)
3. For SSL printers, ensure SSL settings are correct
4. Check firewall rules on both printer and Home Assistant

### Missing Ink Level Sensors

Some printers do not report ink/toner levels via IPP. This is a limitation of the printer, not the integration.

### Service Not Working

Job management services require IPP operations not currently exposed by the pyipp library. These are placeholders for future implementation.

## Development

### Project Structure

```
custom_components/cups/
├── __init__.py           # Integration setup and services
├── binary_sensor.py      # Connectivity sensor
├── config_flow.py        # Configuration UI
├── const.py             # Constants
├── manifest.json        # Integration metadata
├── sensor.py            # Status and marker sensors
├── services.yaml        # Service definitions
├── strings.json         # UI strings
└── translations/        # Localization
    ├── en.json
    └── ja.json
```

### Contributing

Contributions are welcome! Please submit issues and pull requests to the GitHub repository.

## License

This integration is provided as-is without warranty. Use at your own risk.

## Credits

- **pyipp**: Python IPP client library by [@ctalkington](https://github.com/ctalkington)
- **OpenPrinting**: CUPS printing system by the Linux Foundation

## References

- [CUPS Documentation](https://openprinting.github.io/cups/)
- [IPP Specification (RFC 8011)](https://tools.ietf.org/html/rfc8011)
- [pyipp Library](https://github.com/ctalkington/python-ipp)
- [Home Assistant Developer Docs](https://developers.home-assistant.io/)

## Version History

### 1.0.0 (Initial Release)

- Printer status monitoring
- Ink/toner level sensors
- Print queue tracking
- Connectivity monitoring
- Zeroconf auto-discovery
- Manual configuration
- Service definitions (planned)
- English and Japanese translations
