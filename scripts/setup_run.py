"""Compatibility entrypoint for future run setup automation.

The canonical CLI is `scripts/workflow.py --setup`. This module exists so
automation jobs can later import setup behavior without shelling out.
"""

from workflow import setup_run

__all__ = ["setup_run"]
