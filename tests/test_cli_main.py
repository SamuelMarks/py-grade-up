"""Test module for CLI main."""

import runpy
import sys
from unittest.mock import patch


def test_cli_main():
    """Test CLI main block execution."""
    with patch.object(sys, "argv", ["py-gradeup", "--help"]):
        try:
            runpy.run_module("py_gradeup.cli", run_name="__main__")
        except SystemExit as e:
            assert e.code == 0
