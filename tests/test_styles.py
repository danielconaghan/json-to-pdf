import pytest

from pdfgen.styles import resolve_styles


def test_simple_style_returned_as_is():
    styles = {"body": {"font": "Helvetica", "size": 11}}
    result = resolve_styles(styles)
    assert result["body"]["font"] == "Helvetica"
    assert result["body"]["size"] == 11


def test_extends_key_not_in_resolved_output():
    styles = {
        "base": {"font": "Helvetica"},
        "child": {"extends": "base", "size": 9},
    }
    result = resolve_styles(styles)
    assert "extends" not in result["child"]


def test_child_inherits_parent_fields():
    styles = {
        "base": {"font": "Helvetica", "size": 11},
        "child": {"extends": "base", "size": 9},
    }
    result = resolve_styles(styles)
    assert result["child"]["font"] == "Helvetica"
    assert result["child"]["size"] == 9


def test_child_overrides_parent_field():
    styles = {
        "base": {"font": "Helvetica", "color": "#000000"},
        "child": {"extends": "base", "color": "#ff0000"},
    }
    result = resolve_styles(styles)
    assert result["child"]["color"] == "#ff0000"


def test_grandchild_inherits_through_chain():
    styles = {
        "root": {"font": "Helvetica", "size": 11},
        "mid": {"extends": "root", "size": 9},
        "leaf": {"extends": "mid", "color": "#888888"},
    }
    result = resolve_styles(styles)
    assert result["leaf"]["font"] == "Helvetica"
    assert result["leaf"]["size"] == 9
    assert result["leaf"]["color"] == "#888888"


def test_circular_extends_raises():
    styles = {
        "a": {"extends": "b"},
        "b": {"extends": "a"},
    }
    with pytest.raises(ValueError, match="Circular"):
        resolve_styles(styles)


def test_missing_extends_target_raises():
    styles = {"child": {"extends": "nonexistent"}}
    with pytest.raises(ValueError, match="nonexistent"):
        resolve_styles(styles)


def test_sibling_styles_resolved_independently():
    styles = {
        "base": {"size": 11},
        "a": {"extends": "base", "color": "red"},
        "b": {"extends": "base", "color": "blue"},
    }
    result = resolve_styles(styles)
    assert result["a"]["color"] == "red"
    assert result["b"]["color"] == "blue"


def test_result_is_independent_of_input_mutation():
    styles = {"body": {"font": "Helvetica"}}
    result = resolve_styles(styles)
    styles["body"]["font"] = "Times"
    assert result["body"]["font"] == "Helvetica"
