import pytest

from pdfgen.merger import deep_merge, load_defaults


# ── deep_merge ────────────────────────────────────────────────────────────────

def test_primitive_override_wins():
    assert deep_merge({"a": 1}, {"a": 2}) == {"a": 2}


def test_missing_override_key_kept_from_base():
    result = deep_merge({"a": 1, "b": 2}, {"a": 99})
    assert result["b"] == 2


def test_new_key_in_override_added():
    result = deep_merge({"a": 1}, {"b": 2})
    assert result["b"] == 2


def test_nested_dicts_merged_recursively():
    base = {"doc": {"title": "Old", "size": 11}}
    override = {"doc": {"title": "New"}}
    result = deep_merge(base, override)
    assert result["doc"]["title"] == "New"
    assert result["doc"]["size"] == 11


def test_array_override_wins_not_merged():
    base = {"tags": ["a", "b"]}
    override = {"tags": ["c"]}
    assert deep_merge(base, override)["tags"] == ["c"]


def test_base_not_mutated():
    base = {"a": {"x": 1}}
    deep_merge(base, {"a": {"x": 2}})
    assert base["a"]["x"] == 1


def test_override_not_mutated():
    override = {"a": {"x": 2}}
    deep_merge({"a": {"x": 1}}, override)
    assert override["a"]["x"] == 2


def test_empty_override_returns_base_copy():
    base = {"a": 1}
    result = deep_merge(base, {})
    assert result == base


# ── load_defaults ─────────────────────────────────────────────────────────────

def test_load_defaults_returns_dict():
    d = load_defaults()
    assert isinstance(d, dict)


def test_load_defaults_has_required_keys():
    d = load_defaults()
    for key in ("document", "styles", "content", "pagination"):
        assert key in d, f"Missing key: {key}"


def test_load_defaults_mutation_does_not_poison_cache():
    d1 = load_defaults()
    d1["document"]["title"] = "MUTATED"
    d2 = load_defaults()
    assert d2["document"]["title"] != "MUTATED"


def test_load_defaults_returns_fresh_copy_each_call():
    d1 = load_defaults()
    d2 = load_defaults()
    assert d1 is not d2
