"""Module containing coverage tests."""

import importlib
from unittest.mock import patch


def test_core_pyupgrade_import_error():
    """Test function."""
    import py_gradeup.core

    with patch.dict("sys.modules", {"pyupgrade._main": None}):
        importlib.reload(py_gradeup.core)

        assert py_gradeup.core.Settings is None
        assert py_gradeup.core._fix_plugins("test", None) == "test"
        assert py_gradeup.core._fix_tokens("test") == "test"

        # also test _check_pyupgrade
        res = py_gradeup.core._check_pyupgrade("some content", (3, 10))
        assert res == "some content"

    # reload normally to restore for other tests
    importlib.reload(py_gradeup.core)
