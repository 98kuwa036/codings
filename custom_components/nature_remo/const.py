"""Constants for the Nature Remo integration."""

DOMAIN = "nature_remo"

# Configuration
CONF_ACCESS_TOKEN = "access_token"

# API endpoints
API_BASE_URL = "https://api.nature.global"
API_VERSION = "1"

# Update interval
UPDATE_INTERVAL = 60  # seconds

# Platforms
PLATFORMS = ["sensor", "climate", "remote", "switch", "light"]

# Appliance types
APPLIANCE_TYPE_AC = "AC"
APPLIANCE_TYPE_TV = "TV"
APPLIANCE_TYPE_LIGHT = "LIGHT"
APPLIANCE_TYPE_IR = "IR"

# Device classes
DEVICE_CLASS_TEMPERATURE = "temperature"
DEVICE_CLASS_HUMIDITY = "humidity"
DEVICE_CLASS_ILLUMINANCE = "illuminance"
DEVICE_CLASS_MOTION = "motion"
DEVICE_CLASS_ENERGY = "energy"
DEVICE_CLASS_POWER = "power"

# AC modes
AC_MODE_COOL = "cool"
AC_MODE_WARM = "warm"
AC_MODE_DRY = "dry"
AC_MODE_BLOW = "blow"
AC_MODE_AUTO = "auto"

# AC fan modes
AC_FAN_AUTO = "auto"
AC_FAN_1 = "1"
AC_FAN_2 = "2"
AC_FAN_3 = "3"
AC_FAN_4 = "4"
AC_FAN_5 = "5"

# AC swing modes
AC_SWING_AUTO = "auto"
AC_SWING_1 = "1"
AC_SWING_2 = "2"
AC_SWING_3 = "3"

# Attributes
ATTR_DEVICE_ID = "device_id"
ATTR_DEVICE_NAME = "device_name"
ATTR_DEVICE_TYPE = "device_type"
ATTR_FIRMWARE_VERSION = "firmware_version"
ATTR_MAC_ADDRESS = "mac_address"
ATTR_SERIAL_NUMBER = "serial_number"
ATTR_LAST_COMMUNICATION = "last_communication"

# Smart meter attributes
ATTR_MEASURED_INSTANTANEOUS = "measured_instantaneous"
ATTR_NORMAL_DIRECTION_CUMULATIVE_ELECTRIC_ENERGY = "normal_direction_cumulative_electric_energy"
ATTR_COEFFICIENT = "coefficient"
ATTR_UNIT = "unit"

# Error messages
ERROR_AUTH_INVALID = "invalid_auth"
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_UNKNOWN = "unknown"

# Services
SERVICE_SEND_SIGNAL = "send_signal"
SERVICE_UPDATE_AIRCON = "update_aircon"
SERVICE_UPDATE_TV = "update_tv"
SERVICE_UPDATE_LIGHT = "update_light"
