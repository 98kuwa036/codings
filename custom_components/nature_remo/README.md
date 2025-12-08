# Nature Remo Custom Integration for Home Assistant

This custom integration allows you to control Nature Remo devices and all connected appliances through Home Assistant.

## Features

### Supported Platforms

- **Climate** - Full air conditioner control with temperature, mode, fan, and swing settings
- **Sensor** - Temperature, humidity, illuminance, motion, power consumption, and energy sensors
- **Remote** - Control IR-based appliances through custom commands
- **Switch** - Control devices with on/off IR signals
- **Light** - Control light appliances with brightness support

### Capabilities

- **Environment Monitoring**
  - Temperature sensor
  - Humidity sensor
  - Illuminance sensor
  - Motion detection

- **Air Conditioner Control**
  - Temperature adjustment
  - Mode selection (Cool, Heat, Dry, Fan, Auto)
  - Fan speed control
  - Swing mode control
  - Power on/off

- **Smart Meter Integration**
  - Real-time power consumption (Watts)
  - Cumulative energy usage (kWh)
  - ECHONET Lite property support

- **IR Remote Control**
  - Send custom IR signals
  - Support for TV, light, and other appliances
  - Pre-configured signal support

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/98kuwa036/codings`
6. Select category: "Integration"
7. Click "Add"
8. Search for "Nature Remo" and install

### Manual Installation

1. Copy the `custom_components/nature_remo` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

### Getting Your Access Token

1. Go to [Nature Remo Cloud API](https://home.nature.global/)
2. Sign in with your Nature Remo account
3. Navigate to "Generate Access Token"
4. Copy your access token

### Setup in Home Assistant

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Nature Remo"
4. Enter your access token
5. Click "Submit"

Your devices and appliances will be automatically discovered and added to Home Assistant.

## Usage

### Climate Entity (Air Conditioner)

Control your air conditioner:

```yaml
service: climate.set_temperature
target:
  entity_id: climate.living_room_ac
data:
  temperature: 24
  hvac_mode: cool
```

### Remote Entity (IR Appliances)

Send custom IR signals:

```yaml
service: remote.send_command
target:
  entity_id: remote.tv
data:
  command: power
```

### Sensor Entities

Access sensor data in automations:

```yaml
automation:
  trigger:
    - platform: numeric_state
      entity_id: sensor.living_room_temperature
      above: 28
  action:
    - service: climate.turn_on
      target:
        entity_id: climate.living_room_ac
```

### Switch/Light Entities

Control switches and lights:

```yaml
service: light.turn_on
target:
  entity_id: light.bedroom_light
data:
  brightness: 128
```

## API Endpoints Used

This integration uses the following Nature Remo Cloud API endpoints:

- `GET /1/users/me` - Get user information
- `GET /1/devices` - Get all Nature Remo devices
- `GET /1/appliances` - Get all registered appliances
- `POST /1/appliances/{id}/aircon_settings` - Control air conditioner
- `POST /1/appliances/{id}/tv` - Send TV signals
- `POST /1/appliances/{id}/light` - Send light signals
- `POST /1/signals/{id}/send` - Send IR signals

## Troubleshooting

### Cannot Connect Error

- Verify your access token is correct
- Check your internet connection
- Ensure Nature Remo Cloud API is accessible

### Devices Not Showing Up

- Restart Home Assistant
- Re-add the integration
- Check if devices are registered in the Nature Remo mobile app

### Climate/Light Controls Not Working

- Verify the appliance is properly configured in the Nature Remo app
- Check that the appliance type is correctly detected
- Review Home Assistant logs for error messages

## Support

For issues and feature requests, please visit:
- GitHub Issues: https://github.com/98kuwa036/codings/issues

## Credits

This integration is developed for the Home Assistant community.

### References

- [Nature Remo Cloud API Documentation](https://developer.nature.global/)
- [Home Assistant Developer Documentation](https://developers.home-assistant.io/)

## License

This project is provided as-is for personal and educational use.
