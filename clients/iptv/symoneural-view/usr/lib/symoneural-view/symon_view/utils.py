"""Utility functions and helpers."""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class URLValidator:
    """Validate URLs."""

    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    @staticmethod
    def is_valid(url: str) -> bool:
        """Check if URL is valid."""
        return bool(URLValidator.URL_PATTERN.match(url))

    @staticmethod
    def is_stream(url: str) -> bool:
        """Check if URL is media stream."""
        stream_extensions = {'.m3u', '.m3u8', '.ts', '.mp4', '.mkv', '.avi', '.flv', '.webm'}
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Check extension
        for ext in stream_extensions:
            if path.endswith(ext):
                return True

        # Check known streaming protocols
        return any(proto in url.lower() for proto in ['rtmp://', 'http-ts://', 'hls://', 'dash://'])


class StringUtils:
    """String manipulation utilities."""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Remove invalid filename characters."""
        invalid_chars = r'[/<>:"|?*\x00-\x1f]'
        sanitized = re.sub(invalid_chars, '_', filename)
        return sanitized.strip('._')

    @staticmethod
    def truncate(text: str, max_length: int, suffix: str = "...") -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix

    @staticmethod
    def extract_domain(url: str) -> str | None:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.split(':')[0]
            return domain
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize channel/item name."""
        # Remove extra spaces
        name = ' '.join(name.split())
        # Remove special prefixes
        name = re.sub(r'^[*#]+\s*', '', name)
        # Capitalize words
        return name.title()


class FileUtils:
    """File utilities."""

    @staticmethod
    def get_file_size(filepath: Path) -> str:
        """Get human-readable file size."""
        try:
            size_bytes = filepath.stat().st_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024:
                    return f"{size_bytes:.1f}{unit}"
                size_bytes /= 1024
            return f"{size_bytes:.1f}TB"
        except OSError:
            return "Unknown"

    @staticmethod
    def get_mimetype(filepath: Path) -> str:
        """Get MIME type for file."""
        mime, _ = mimetypes.guess_type(str(filepath))
        return mime or "application/octet-stream"

    @staticmethod
    def get_free_space(path: Path) -> int:
        """Get free disk space in bytes."""
        try:
            import shutil
            return shutil.disk_usage(str(path)).free
        except OSError:
            return 0

    @staticmethod
    def find_files(directory: Path, pattern: str = "*") -> list[Path]:
        """Find files matching pattern."""
        try:
            return list(directory.glob(pattern))
        except OSError:
            return []


class ProcessUtils:
    """Process utilities."""

    @staticmethod
    def find_process(name: str) -> int | None:
        """Find process by name."""
        try:
            result = subprocess.run(
                ['pgrep', '-f', name],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return int(result.stdout.decode().strip().split('\n')[0])
        except (subprocess.SubprocessError, OSError, ValueError):
            pass
        return None

    @staticmethod
    def is_process_running(pid: int) -> bool:
        """Check if process is running."""
        try:
            import os
            os.kill(pid, 0)  # Signal 0 doesn't kill, just checks
            return True
        except (ProcessLookupError, OSError):
            return False

    @staticmethod
    def get_process_info(pid: int) -> dict | None:
        """Get process information."""
        try:
            result = subprocess.run(
                ['ps', '-p', str(pid), '-o', 'pid,ppid,cmd'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.decode().strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    return {
                        "pid": int(parts[0]),
                        "ppid": int(parts[1]),
                        "cmd": ' '.join(parts[2:])
                    }
        except (subprocess.SubprocessError, OSError, ValueError):
            pass
        return None


class CryptoUtils:
    """Cryptographic utilities."""

    @staticmethod
    def hash_string(text: str, algorithm: str = 'md5') -> str:
        """Hash string."""
        if algorithm == 'md5':
            return hashlib.md5(text.encode()).hexdigest()
        elif algorithm == 'sha256':
            return hashlib.sha256(text.encode()).hexdigest()
        return ""

    @staticmethod
    def hash_file(filepath: Path, algorithm: str = 'sha256') -> str:
        """Hash file."""
        try:
            hash_obj = hashlib.sha256() if algorithm == 'sha256' else hashlib.md5()

            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_obj.update(chunk)

            return hash_obj.hexdigest()
        except Exception as e:
            logger.error(f"File hash failed: {e}")
            return ""


class SystemUtils:
    """System utilities."""

    @staticmethod
    def get_platform() -> str:
        """Get platform info."""
        if sys.platform.startswith('linux'):
            return 'linux'
        elif sys.platform == 'darwin':
            return 'macos'
        elif sys.platform == 'win32':
            return 'windows'
        return 'unknown'

    @staticmethod
    def get_desktop_environment() -> str:
        """Detect desktop environment."""
        import os

        desktop_env = os.getenv('XDG_CURRENT_DESKTOP', '').lower()
        if desktop_env:
            return desktop_env.split(':')[0]

        # Fallback checks
        if os.getenv('GNOME_DESKTOP_SESSION_ID'):
            return 'gnome'
        elif os.getenv('KDE_FULL_SESSION'):
            return 'kde'
        elif os.getenv('TDE_FULL_SESSION'):
            return 'tde'

        return 'unknown'

    @staticmethod
    def get_system_info() -> dict:
        """Get system information."""
        import platform

        return {
            "platform": SystemUtils.get_platform(),
            "desktop": SystemUtils.get_desktop_environment(),
            "python": platform.python_version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }


class ValidationUtils:
    """Input validation utilities."""

    @staticmethod
    def is_valid_port(port: int) -> bool:
        """Check if port is valid."""
        return 0 < port < 65536

    @staticmethod
    def is_valid_ip(address: str) -> bool:
        """Check if IP address is valid."""
        parts = address.split('.')
        if len(parts) != 4:
            return False

        try:
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Check if email is valid."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
