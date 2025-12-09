"""Constants for the CUPS integration."""

DOMAIN = "cups"

# Configuration constants not in homeassistant.const
CONF_BASE_PATH = "base_path"

# Default values
DEFAULT_PORT = 631
DEFAULT_SSL = False
DEFAULT_VERIFY_SSL = True
DEFAULT_BASE_PATH = "/ipp/print"

# Update interval
UPDATE_INTERVAL = 30  # seconds

# Platforms
PLATFORMS = ["sensor", "binary_sensor"]

# Printer states (IPP)
PRINTER_STATE_IDLE = 3
PRINTER_STATE_PROCESSING = 4
PRINTER_STATE_STOPPED = 5

# Printer state reasons
PRINTER_STATE_REASONS = {
    "none": "No issues",
    "other": "Unknown issue",
    "media-needed": "Media needed",
    "media-jam": "Media jam",
    "media-low": "Media low",
    "media-empty": "Media empty",
    "toner-low": "Toner low",
    "toner-empty": "Toner empty",
    "marker-supply-low": "Ink/toner low",
    "marker-supply-empty": "Ink/toner empty",
    "paused": "Paused",
    "shutdown": "Shutdown",
    "connecting-to-device": "Connecting",
    "offline": "Offline",
    "door-open": "Door open",
    "cover-open": "Cover open",
}

# Marker types
MARKER_TYPE_TONER = "toner"
MARKER_TYPE_INK = "ink"
MARKER_TYPE_RIBBON = "ribbon"
MARKER_TYPE_DEVELOPER = "developer"
MARKER_TYPE_FUSER_OIL = "fuser-oil"
MARKER_TYPE_SOLID_WAX = "solid-wax"
MARKER_TYPE_STAPLES = "staples"
MARKER_TYPE_WASTE_TONER = "waste-toner"
MARKER_TYPE_WASTE_INK = "waste-ink"
MARKER_TYPE_WASTE_WAX = "waste-wax"
MARKER_TYPE_WASTE_WATER = "waste-water"

# Marker colors
MARKER_COLOR_BLACK = "black"
MARKER_COLOR_CYAN = "cyan"
MARKER_COLOR_MAGENTA = "magenta"
MARKER_COLOR_YELLOW = "yellow"
MARKER_COLOR_LIGHT_CYAN = "lightCyan"
MARKER_COLOR_LIGHT_MAGENTA = "lightMagenta"
MARKER_COLOR_GRAY = "gray"
MARKER_COLOR_LIGHT_GRAY = "lightGray"

# Attributes
ATTR_PRINTER_NAME = "printer_name"
ATTR_PRINTER_URI = "printer_uri"
ATTR_PRINTER_STATE = "printer_state"
ATTR_PRINTER_STATE_MESSAGE = "state_message"
ATTR_PRINTER_STATE_REASONS = "state_reasons"
ATTR_PRINTER_MAKE_MODEL = "make_and_model"
ATTR_PRINTER_LOCATION = "location"
ATTR_PRINTER_INFO = "printer_info"
ATTR_PRINTER_URI_SUPPORTED = "uri_supported"
ATTR_SERIAL_NUMBER = "serial_number"
ATTR_FIRMWARE_VERSION = "firmware_version"
ATTR_UPTIME = "uptime"
ATTR_COMMAND_SET = "command_set"

# Job attributes
ATTR_JOB_ID = "job_id"
ATTR_JOB_NAME = "job_name"
ATTR_JOB_STATE = "job_state"
ATTR_JOB_USER = "job_user"
ATTR_JOB_PAGES = "pages"
ATTR_JOB_PAGES_COMPLETED = "pages_completed"

# Marker attributes
ATTR_MARKER_INDEX = "index"
ATTR_MARKER_NAME = "name"
ATTR_MARKER_TYPE = "type"
ATTR_MARKER_COLOR = "color"
ATTR_MARKER_LEVEL = "level"
ATTR_MARKER_LOW_LEVEL = "low_level"
ATTR_MARKER_HIGH_LEVEL = "high_level"

# Error messages
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_INVALID_HOST = "invalid_host"
ERROR_UNKNOWN = "unknown"

# Services
SERVICE_PAUSE_PRINTER = "pause_printer"
SERVICE_RESUME_PRINTER = "resume_printer"
SERVICE_CANCEL_ALL_JOBS = "cancel_all_jobs"
SERVICE_PAUSE_JOB = "pause_job"
SERVICE_RESUME_JOB = "resume_job"
SERVICE_CANCEL_JOB = "cancel_job"
