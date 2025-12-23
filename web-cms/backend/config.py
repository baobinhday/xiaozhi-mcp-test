"""
Configuration and settings for the MCP Endpoints CMS.
"""

import logging
import os
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=False)

# Directory paths
CMS_DIR = Path(__file__).parent.parent.absolute()
PROJECT_ROOT = CMS_DIR.parent

# Server configuration
HTTP_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8890

# Authentication settings
CMS_USERNAME = os.environ.get("CMS_USERNAME", "admin")
CMS_PASSWORD = os.environ.get("CMS_PASSWORD", "asfadfdagdfhfghjgjghkj23546%354")
CMS_SECRET_KEY = os.environ.get("CMS_SECRET_KEY", secrets.token_hex(32))
SESSION_DURATION_HOURS = 24

# Rate limiting settings
MAX_LOGIN_ATTEMPTS = 3
RATE_LIMIT_WINDOW = 60  # seconds

# File paths
MCP_CONFIG_PATH = PROJECT_ROOT / "data" / "mcp_config.json"
TOOLS_CACHE_PATH = PROJECT_ROOT / "data" / "tools_cache.json"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('CMS')
