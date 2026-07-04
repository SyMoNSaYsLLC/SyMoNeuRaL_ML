"""Intelligent logo caching and management."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class LogoManager:
    """Manage channel logo caching."""
    
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = Path(cache_dir) / "logos"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "metadata.json"
        self.metadata: dict = {}
        self.lock = threading.RLock()
        self.stats: dict[str, int] = {"hits": 0, "misses": 0, "downloads": 0, "errors": 0}
        
        self._load_metadata()
        logger.info(f"LogoManager initialized: {self.cache_dir}")
    
    def _load_metadata(self) -> None:
        """Load logo metadata."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logger.debug(f"Loaded {len(self.metadata)} logo entries")
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
    
    def _save_metadata(self) -> None:
        """Save logo metadata."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def _get_cache_path(self, url: str) -> Path:
        """Get cache file path from URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        ext = Path(url.split('?')[0]).suffix or '.png'
        return self.cache_dir / f"{url_hash}{ext}"
    
    def get_logo(self, url: str, force_download: bool = False) -> Path | None:
        """Get logo path, downloading if necessary."""
        if not url:
            return None
        
        try:
            with self.lock:
                cache_path = self._get_cache_path(url)
                
                if cache_path.exists() and not force_download:
                    self.stats["hits"] += 1
                    logger.debug(f"Logo cache hit: {url[:50]}")
                    return cache_path
                
                self.stats["misses"] += 1
                
                if self._download_logo(url, cache_path):
                    self.stats["downloads"] += 1
                    self.metadata[str(cache_path)] = {
                        "url": url,
                        "timestamp": time.time(),
                        "size": cache_path.stat().st_size if cache_path.exists() else 0
                    }
                    self._save_metadata()
                    return cache_path
                else:
                    self.stats["errors"] += 1
                    return None
        
        except Exception as e:
            logger.error(f"Logo get failed: {e}")
            self.stats["errors"] += 1
            return None
    
    def _download_logo(self, url: str, output_path: Path) -> bool:
        """Download logo from URL."""
        try:
            from urllib.request import Request, urlopen
            from PIL import Image  # type: ignore
            from io import BytesIO
            
            logger.debug(f"Downloading logo: {url[:50]}")
            
            req = Request(url, headers={"User-Agent": "symoneural-view/1.0"})
            with urlopen(req, timeout=10) as response:
                content = response.read()
            
            img = Image.open(BytesIO(content))
            
            max_size = 200
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            img.save(output_path, format='PNG', optimize=True)
            logger.debug(f"Downloaded logo: {output_path.name}")
            return True
        
        except Exception as e:
            logger.debug(f"Logo download failed: {e}")
            return False
    
    def cleanup(self, max_age_days: int = 30) -> None:
        """Remove old/unused logos."""
        try:
            cutoff_time = time.time() - (max_age_days * 86400)
            removed = 0
            
            for logo_path in self.cache_dir.glob("*.*"):
                if logo_path.is_file():
                    if logo_path.stat().st_mtime < cutoff_time:
                        logo_path.unlink()
                        if str(logo_path) in self.metadata:
                            del self.metadata[str(logo_path)]
                        removed += 1
            
            if removed > 0:
                self._save_metadata()
                logger.info(f"Cleaned up {removed} old logos")
        
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def get_cache_size(self) -> int:
        """Get total cache size in bytes."""
        try:
            return sum(f.stat().st_size for f in self.cache_dir.glob("*.*"))
        except (OSError, ValueError) as e:
            logger.debug(f"Failed to calculate cache size: {e}")
            return 0
    
    def clear_cache(self) -> bool:
        """Clear all cached logos."""
        try:
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.metadata.clear()
            logger.info("Logo cache cleared")
            return True
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self.lock:
            total = self.stats["hits"] + self.stats["misses"]
            hit_rate = self.stats["hits"] / total if total > 0 else 0.0
            
            return {
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "downloads": self.stats["downloads"],
                "errors": self.stats["errors"],
                "hit_rate": hit_rate,
                "cache_size_mb": self.get_cache_size() / (1024 * 1024),
                "cached_items": len(self.metadata)
            }
