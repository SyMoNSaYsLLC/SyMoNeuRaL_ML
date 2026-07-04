"""Diagnostic and debugging tools."""

from __future__ import annotations

import json
import logging
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import core

logger = logging.getLogger(__name__)


def _core_path(attr_name: str, fallback: Path) -> Path:
    """Resolve optional path attributes from core safely."""
    value = getattr(core, attr_name, fallback)
    try:
        return Path(value)
    except (TypeError, ValueError):
        return fallback


CONFIG_DIR = _core_path("CONFIG_DIR", Path.home() / ".config" / "symoneural-view")
CACHE_DIR = _core_path("CACHE_DIR", Path.home() / ".cache" / "symoneural-view")
DATA_DIR = _core_path("DATA_DIR", Path.home() / ".local" / "share" / "symoneural-view")
LOG_FILE = _core_path("LOG_FILE", DATA_DIR / "symoneural-view.log")


class DiagnosticReport:
    """Generate comprehensive diagnostic reports."""
    
    @staticmethod
    def generate_system_report() -> dict:
        """Generate system diagnostic report."""
        logger.info("Generating system diagnostic report...")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "platform": sys.platform,
                "platform_info": platform.platform(),
                "python_version": platform.python_version(),
                "processor": platform.processor(),
                "machine": platform.machine(),
                "architecture": platform.architecture(),
            },
            "directories": {
                "config": str(CONFIG_DIR),
                "cache": str(CACHE_DIR),
                "data": str(DATA_DIR),
                "logs": str(LOG_FILE),
            }
        }
    
    @staticmethod
    def generate_performance_report() -> dict:
        """Generate performance diagnostic report."""
        logger.info("Generating performance diagnostic report...")
        
        perf_monitor = getattr(core, 'get_perf_monitor', lambda: None)()
        stats_collector = getattr(core, 'get_stats_collector', lambda: None)()
        
        return {
            "performance": perf_monitor.get_stats() if perf_monitor else {},
            "uptime_seconds": perf_monitor.uptime() if perf_monitor else 0,
            "session_stats": stats_collector.get_stats() if stats_collector else {},
        }
    
    @staticmethod
    def generate_config_report() -> dict:
        """Generate configuration report."""
        logger.info("Generating configuration report...")
        
        settings_obj = getattr(core, 'get_settings', lambda: None)()
        settings_data = settings_obj.data.copy() if settings_obj else {}
        
        return {
            "settings": settings_data,
            "storage_locations": {
                "config": str(CONFIG_DIR),
                "cache": str(CACHE_DIR),
                "data": str(DATA_DIR),
            }
        }
    
    @staticmethod
    def generate_full_report(output_file: Path | None = None) -> dict:
        """Generate complete diagnostic report."""
        logger.info("Generating complete diagnostic report...")
        
        report = {
            "report_time": datetime.now().isoformat(),
            "version": "2.0.0",
            "system": DiagnosticReport.generate_system_report(),
            "performance": DiagnosticReport.generate_performance_report(),
            "config": DiagnosticReport.generate_config_report(),
        }
        
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2)
                logger.info(f"Diagnostic report saved to {output_file}")
            except (OSError, IOError) as e:
                logger.error(f"Failed to save report: {e}")
        
        return report
    
    @staticmethod
    def print_report(report: dict) -> None:
        """Print diagnostic report to console."""
        print("\n" + "="*60)
        print("SyMoNeuRaL DIAGNOSTIC REPORT")
        print("="*60)
        
        print(f"\nReport Time: {report.get('report_time')}")
        print(f"Version: {report.get('version')}")
        
        # System info
        print("\n📊 System Information:")
        system_info = report.get('system', {})
        for key, value in system_info.get('system', {}).items():
            print(f"  {key}: {value}")
        
        # Performance
        print("\n⚡ Performance:")
        perf = report.get('performance', {})
        print(f"  Uptime: {perf.get('uptime_seconds', 0):.1f}s")
        
        # Session stats
        print("\n📈 Session Statistics:")
        stats = perf.get('session_stats', {})
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print("\n" + "="*60 + "\n")


class HealthCheck:
    """System health check utilities."""
    
    @staticmethod
    def check_directories() -> dict[str, bool]:
        """Check if all required directories exist."""
        results: dict[str, bool] = {}

        for name, path in [
            ("config", CONFIG_DIR),
            ("cache", CACHE_DIR),
            ("data", DATA_DIR),
        ]:
            try:
                path.mkdir(parents=True, exist_ok=True)
                results[name] = True
            except (OSError, PermissionError) as e:
                logger.error(f"Failed to create {name} directory: {e}")
                results[name] = False
        
        return results
    
    @staticmethod
    def check_disk_space() -> dict[str, int]:
        """Check available disk space."""
        import shutil
        
        results: dict[str, int] = {}
        for name, path in [
            ("cache", CACHE_DIR),
            ("data", DATA_DIR),
        ]:
            try:
                free = shutil.disk_usage(str(path)).free
                results[name] = free // (1024 * 1024)
            except (OSError, ValueError) as e:
                logger.error(f"Failed to check disk space for {name}: {e}")
                results[name] = -1
        
        return results
    
    @staticmethod
    def check_permissions() -> dict[str, bool]:
        """Check file permissions."""
        results: dict[str, bool] = {}
        
        for name, path in [
            ("config", CONFIG_DIR),
            ("cache", CACHE_DIR),
            ("data", DATA_DIR),
        ]:
            try:
                test_file = path / ".permission_test"
                test_file.touch()
                test_file.unlink()
                results[name] = True
            except (OSError, PermissionError) as e:
                logger.warning(f"Permission denied for {name}: {e}")
                results[name] = False
        
        return results
    
    @staticmethod
    def run_full_health_check() -> dict:
        """Run complete health check."""
        logger.info("Running health check...")
        
        return {
            "directories": HealthCheck.check_directories(),
            "disk_space_mb": HealthCheck.check_disk_space(),
            "permissions": HealthCheck.check_permissions(),
            "timestamp": datetime.now().isoformat(),
        }


class DebugConsole:
    """Interactive debug console."""
    
    def __init__(self) -> None:
        self.commands: dict[str, Callable] = {
            "help": self._cmd_help,
            "status": self._cmd_status,
            "perf": self._cmd_performance,
            "stats": self._cmd_stats,
            "cache": self._cmd_cache,
            "health": self._cmd_health,
            "settings": self._cmd_settings,
            "clear_cache": self._cmd_clear_cache,
            "report": self._cmd_report,
            "exit": self._cmd_exit,
        }
    
    def run(self) -> None:
        """Run interactive console."""
        print("\n🔧 SyMoNeuRaL Debug Console")
        print("Type 'help' for commands\n")
        
        while True:
            try:
                cmd_input = input("debug> ").strip()
                
                if not cmd_input:
                    continue
                
                parts = cmd_input.split(maxsplit=1)
                cmd = parts[0]
                args = parts[1] if len(parts) > 1 else ""
                
                if cmd in self.commands:
                    self.commands[cmd](args)
                else:
                    print(f"Unknown command: {cmd}")
            
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def _cmd_help(self, args: str) -> None:
        """Show help."""
        print("\nAvailable commands:")
        for cmd in self.commands.keys():
            print(f"  {cmd}")
        print()
    
    def _cmd_status(self, args: str) -> None:
        """Show status."""
        perf = getattr(core, 'get_perf_monitor', lambda: None)()
        if perf:
            print(f"\n✓ Uptime: {perf.uptime():.1f}s\n")
        else:
            print("\n✗ Performance monitor not available\n")
    
    def _cmd_performance(self, args: str) -> None:
        """Show performance stats."""
        perf = getattr(core, 'get_perf_monitor', lambda: None)()
        stats = perf.get_stats() if perf else {}
        print(f"\n{json.dumps(stats, indent=2)}\n")
    
    def _cmd_stats(self, args: str) -> None:
        """Show statistics."""
        stats_collector = getattr(core, 'get_stats_collector', lambda: None)()
        stats = stats_collector.get_stats() if stats_collector else {}
        print(f"\n{json.dumps(stats, indent=2)}\n")
    
    def _cmd_cache(self, args: str) -> None:
        """Show cache info."""
        print("\nCache information available through other commands\n")
    
    def _cmd_health(self, args: str) -> None:
        """Run health check."""
        health = HealthCheck.run_full_health_check()
        print(f"\n{json.dumps(health, indent=2)}\n")
    
    def _cmd_settings(self, args: str) -> None:
        """Show settings."""
        settings_obj = getattr(core, 'get_settings', lambda: None)()
        settings = settings_obj.data if settings_obj else {}
        print(f"\n{json.dumps(settings, indent=2)}\n")
    
    def _cmd_clear_cache(self, args: str) -> None:
        """Clear cache."""
        import shutil
        try:
            shutil.rmtree(CACHE_DIR, ignore_errors=True)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            print("\n✓ Cache cleared\n")
        except Exception as e:
            print(f"\n✗ Failed to clear cache: {e}\n")
    
    def _cmd_report(self, args: str) -> None:
        """Generate report."""
        report = DiagnosticReport.generate_full_report()
        DiagnosticReport.print_report(report)
    
    def _cmd_exit(self, args: str) -> None:
        """Exit console."""
        raise KeyboardInterrupt()