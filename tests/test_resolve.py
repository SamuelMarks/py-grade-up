"""Tests for the resolve functionality."""

from unittest.mock import patch

from py_gradeup.models import GraphResult
from py_gradeup.sdk import PyGradeup


@patch("py_gradeup.sdk.PyGradeup.graph")
def test_resolve_no_conflict(mock_graph, tmp_path):
    """Test resolve when there is no conflict error."""
    mock_graph.return_value = GraphResult(tree="A==1.0", conflict_error=None)

    pg = PyGradeup(str(tmp_path))
    res = pg.resolve()

    assert res.success is True
    assert len(res.suggestions) == 0
    assert res.error is None


@patch("py_gradeup.sdk.PyGradeup.graph")
def test_resolve_with_conflict(mock_graph, tmp_path):
    """Test resolve when there is a parseable conflict error."""
    conflict_text = (
        "  × No solution found when resolving dependencies:\n"
        "  ╰─▶ Because fastapi==0.95.0 depends on starlette>=0.26.1,<0.27.0 and you require\n"  # noqa: E501
        "      fastapi==0.95.0, we can conclude that you require starlette>=0.26.1,<0.27.0.\n"  # noqa: E501
        "      And because you require starlette==0.20.0, we can conclude that your requirements are\n"  # noqa: E501
        "      unsatisfiable."
    )
    mock_graph.return_value = GraphResult(tree=None, conflict_error=conflict_text)

    pg = PyGradeup(str(tmp_path))
    res = pg.resolve()

    assert res.success is True
    assert res.suggestions == ["starlette>=0.26.1,<0.27.0"]
    assert res.error is None


@patch("py_gradeup.sdk.PyGradeup.graph")
def test_resolve_unparseable_conflict(mock_graph, tmp_path):
    """Test resolve when there is a conflict error but no suggestions can be parsed."""
    conflict_text = "Some random error happened during uv pip install."
    mock_graph.return_value = GraphResult(tree=None, conflict_error=conflict_text)

    pg = PyGradeup(str(tmp_path))
    res = pg.resolve()

    assert res.success is False
    assert res.error == "Could not parse conflict error for suggestions."
