import pytest

from pdfgen.utils import resolve_path


def test_none_input_returns_none(tmp_path):
    assert resolve_path(None, str(tmp_path)) is None


def test_empty_string_returns_none(tmp_path):
    assert resolve_path("", str(tmp_path)) is None


def test_absolute_existing_path(tmp_path):
    f = tmp_path / "doc.pdf"
    f.touch()
    assert resolve_path(str(f), None) == str(f)


def test_absolute_missing_path_returns_none(tmp_path):
    assert resolve_path(str(tmp_path / "missing.pdf"), None) is None


def test_relative_path_resolved_against_base(tmp_path):
    f = tmp_path / "img.png"
    f.touch()
    result = resolve_path("img.png", str(tmp_path))
    assert result == str(f)


def test_relative_path_missing_returns_none(tmp_path):
    assert resolve_path("ghost.png", str(tmp_path)) is None


def test_relative_path_no_base_uses_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "local.txt"
    f.touch()
    assert resolve_path("local.txt", None) == str(f)
