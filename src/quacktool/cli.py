# src/quacktool/cli.py
"""
CLI compatibility module.

This module provides backward compatibility for imports from quacktool.cli
which now points to demo_cli.py
"""

# Re-export everything from demo_cli.py
from quacktool.demo_cli import *

# Export the main entry point
__all__ = ["main", "cli"]