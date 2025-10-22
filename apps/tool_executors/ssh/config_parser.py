"""SSH config parser for reading ~/.ssh/config."""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SSHConfigParser:
    """Parser for SSH config files."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.expanduser("~/.ssh/config")
        self.config_path = Path(config_path)
        self.hosts: Dict[str, Dict[str, str]] = {}

    def parse(self) -> Dict[str, Dict[str, str]]:
        """Parse SSH config file."""
        if not self.config_path.exists():
            logger.warning(f"SSH config not found at {self.config_path}")
            return {}

        current_host = None
        host_config = {}

        try:
            with open(self.config_path, "r") as f:
                for line in f:
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Parse Host directive
                    if line.lower().startswith("host "):
                        # Save previous host config
                        if current_host:
                            self.hosts[current_host] = host_config

                        # Start new host
                        current_host = line.split(None, 1)[1]
                        host_config = {}

                    # Parse other directives
                    elif current_host:
                        parts = line.split(None, 1)
                        if len(parts) == 2:
                            key, value = parts
                            host_config[key.lower()] = value

                # Save last host
                if current_host:
                    self.hosts[current_host] = host_config

            logger.info(f"Parsed {len(self.hosts)} hosts from SSH config")
            return self.hosts

        except Exception as e:
            logger.error(f"Failed to parse SSH config: {e}")
            return {}

    def get_host_config(self, hostname: str) -> Optional[Dict[str, str]]:
        """Get configuration for a specific host."""
        if not self.hosts:
            self.parse()

        # Direct match
        if hostname in self.hosts:
            return self.hosts[hostname]

        # Try pattern matching
        for pattern, config in self.hosts.items():
            if self._match_pattern(pattern, hostname):
                return config

        return None

    def _match_pattern(self, pattern: str, hostname: str) -> bool:
        """Match hostname against pattern (supports * and ?)."""
        import fnmatch

        return fnmatch.fnmatch(hostname, pattern)

    def get_connection_params(self, hostname: str) -> Dict[str, any]:
        """Get connection parameters for a host."""
        config = self.get_host_config(hostname)

        if not config:
            return {"host": hostname}

        params = {
            "host": config.get("hostname", hostname),
            "port": int(config.get("port", 22)),
            "username": config.get("user"),
            "key_file": config.get("identityfile"),
        }

        # ProxyJump support (jump host)
        if "proxyjump" in config:
            jump_host = config["proxyjump"]
            params["jump_host"] = self.get_connection_params(jump_host)

        # ProxyCommand support
        if "proxycommand" in config:
            params["proxy_command"] = config["proxycommand"]

        # Remove None values
        return {k: v for k, v in params.items() if v is not None}
