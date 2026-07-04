"""Playlist and EPG parsing with caching, retry logic, and memory efficiency."""

from __future__ import annotations

import logging
import re
import threading
import time
import xml.etree.ElementTree as ET
from typing import Callable

from . import core

logger = logging.getLogger(__name__)


class M3UParser:
    """Parse M3U/M3U8 playlist files with incremental processing."""
    
    @staticmethod
    def parse(filepath: str, progress_callback: Callable | None = None) -> list[dict]:
        """Parse M3U file into channels list."""
        channels = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            current_channel = None
            
            for idx, line in enumerate(lines):
                if progress_callback and idx % 100 == 0:
                    progress_callback(idx / total_lines)
                
                line = line.strip()
                
                if line.startswith('#EXTINF:'):
                    current_channel = M3UParser._parse_extinf(line)
                elif line and not line.startswith('#') and current_channel:
                    current_channel['url'] = line
                    channels.append(current_channel)
                    current_channel = None
            
            logger.info(f"Parsed {len(channels)} channels from {filepath}")
            return channels
        except Exception as e:
            logger.error(f"M3U parse failed: {e}")
            return []
    
    @staticmethod
    def _parse_extinf(line: str) -> dict:
        """Parse EXTINF line into channel metadata."""
        channel = {
            "name": "Unknown",
            "logo": None,
            "group": "Uncategorized",
            "tvg_id": None,
            "tvg_name": None,
            "url": None,
            "_source": "m3u"
        }
        
        props_match = re.search(r'#EXTINF:(.*?),(.*)', line)
        if props_match:
            props_str = props_match.group(1)
            channel['name'] = props_match.group(2).strip()
            
            for prop in re.findall(r'(\w+)="([^"]*)"', props_str):
                key, value = prop
                if key == 'tvg-name':
                    channel['tvg_name'] = value
                elif key == 'tvg-id':
                    channel['tvg_id'] = value
                elif key == 'group-title':
                    channel['group'] = value
                elif key == 'tvg-logo':
                    channel['logo'] = value
        
        return channel


class XMLTVParser:
    """Parse XMLTV EPG format with streamed parsing for large files."""
    
    @staticmethod
    def parse(xml_content: str) -> dict[str, list[dict]]:
        """Parse XMLTV into EPG dictionary."""
        epg = {}
        try:
            root = ET.fromstring(xml_content)
            
            for programme in root.findall('programme'):
                channel_id = programme.get('channel')
                if not channel_id:
                    continue
                
                if channel_id not in epg:
                    epg[channel_id] = []
                
                program_data = {
                    "start": programme.get('start'),
                    "stop": programme.get('stop'),
                    "title": None,
                    "description": None,
                    "category": None,
                    "icon": None
                }
                
                for elem_name, field_name in [
                    ('title', 'title'),
                    ('desc', 'description'),
                    ('category', 'category')
                ]:
                    elem = programme.find(elem_name)
                    if elem is not None and elem.text:
                        program_data[field_name] = elem.text
                
                icon_elem = programme.find('icon')
                if icon_elem is not None:
                    program_data['icon'] = icon_elem.get('src')
                
                epg[channel_id].append(program_data)
            
            logger.info(f"Parsed EPG for {len(epg)} channels")
            return epg
        except Exception as e:
            logger.error(f"XMLTV parse failed: {e}")
            return {}


class XtreamAPI:
    """Xtream Codes API client with retry logic and caching."""
    
    CACHE_TTL: int = 3600
    
    def __init__(self, host: str, username: str, password: str, max_retries: int = 3) -> None:
        self.host = host.rstrip('/')
        self.username = username
        self.password = password
        self.base_url = f"{self.host}/player_api.php"
        self.max_retries = max_retries
        self.cache = {}
        self.cache_time = {}
        self.lock = threading.Lock()
    
    def fetch(self, method: str, params: dict | None = None) -> list | None:
        """Fetch data from Xtream API with caching."""
        try:
            import requests
        except ImportError:
            logger.error("requests library not installed")
            return None
        
        cache_key = f"{method}:{str(params)}"
        
        # Check cache
        with self.lock:
            if cache_key in self.cache:
                if time.time() - self.cache_time[cache_key] < self.CACHE_TTL:
                    logger.debug(f"Cache hit: {method}")
                    return self.cache[cache_key]
        
        # Try to fetch
        for attempt in range(self.max_retries):
            try:
                url_params = {"username": self.username, "password": self.password, "action": method}
                if params:
                    url_params.update(params)
                
                response = requests.get(self.base_url, params=url_params, timeout=15)
                response.raise_for_status()
                result = response.json()
                
                # Cache result
                with self.lock:
                    self.cache[cache_key] = result
                    self.cache_time[cache_key] = time.time()
                
                logger.debug(f"Fetched {method} ({len(result) if isinstance(result, list) else 1} items)")
                return result
            
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"{method} attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"{method} failed after {self.max_retries} attempts: {e}")
                    return None
    
    def fetch_live_streams(self) -> list:
        """Fetch live TV streams."""
        result = self.fetch("get_live_streams")
        return result if isinstance(result, list) else []
    
    def fetch_vod_streams(self) -> list:
        """Fetch VOD streams."""
        result = self.fetch("get_vod_streams")
        return result if isinstance(result, list) else []
    
    def fetch_series(self) -> list:
        """Fetch TV series."""
        result = self.fetch("get_series")
        return result if isinstance(result, list) else []
    
    def clear_cache(self) -> None:
        """Clear API cache."""
        with self.lock:
            self.cache.clear()
            self.cache_time.clear()
        event_bus = core.get_event_bus()
        if event_bus:
            cache_invalidated_event = getattr(core.EventType, "CACHE_INVALIDATED", "cache_invalidated")
            event_bus.emit(cache_invalidated_event, "xtream_api")


def organize_channels(channels: list[dict], style: str = "smart") -> dict:
    """Organize channels by category and group."""
    organized = {}
    
    for channel in channels:
        group = channel.get("group", "Uncategorized")
        
        if group not in organized:
            organized[group] = {
                "channels": [],
                "count": 0,
                "has_logo": sum(1 for ch in channels if ch.get("logo"))
            }
        
        organized[group]["channels"].append(channel)
        organized[group]["count"] += 1
    
    # Sort by count
    if style == "smart":
        organized = dict(sorted(organized.items(), 
                               key=lambda x: x[1]["count"], reverse=True))
    
    logger.info(f"Organized {len(channels)} channels into {len(organized)} groups")
    return organized


def merge_epg(channels: list[dict], epg_data: dict, source_info: dict | None = None) -> dict:
    """Merge EPG data with channels efficiently."""
    epg_index = {}
    matched = 0
    
    for channel in channels:
        tvg_id = channel.get("tvg_id")
        if not tvg_id:
            continue
        
        channel_epg = epg_data.get(tvg_id, [])
        if channel_epg:
            matched += 1
        
        epg_index[tvg_id] = {
            "channel": channel,
            "programs": channel_epg,
            "current": channel_epg[0] if channel_epg else None
        }
    
    logger.info(f"Merged EPG: {matched} channels matched out of {len(channels)}")
    return epg_index


# Legacy function exports
def parse_m3u(filepath: str) -> list[dict]:
    """Parse M3U file."""
    return M3UParser.parse(filepath)


def parse_xmltv(content: str) -> dict[str, list[dict]]:
    """Parse XMLTV content."""
    return XMLTVParser.parse(content)


def fetch_xtream_xmltv(host: str, user: str, pw: str) -> str | None:
    """Fetch XMLTV from Xtream server."""
    try:
        import requests
    except ImportError:
        logger.error("requests library not installed")
        return None
    
    try:
        url = f"{host.rstrip('/')}/player_api.php?username={user}&password={pw}&action=get_epg"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        logger.info(f"Fetched XMLTV from {host}")
        return response.text
    except Exception as e:
        logger.error(f"XMLTV fetch failed: {e}")
        return None
