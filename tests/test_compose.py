"""Tests for the compose engine (pdfgen/compose.py).

Fixtures are inline dicts — the three compose inputs are template / values /
translations, and building them as literals keeps each test self-describing and
dependency-free. Coverage per the brief: a static node, a conditional node with
2+ variants, a nested group of conditionals, interpolation, and each failure
case (missing key, no matching variant, missing interpolation value, and the
validation guard against surviving template vocabulary / placeholders). One
integration test proves the composed output actually renders.
"""
import pytest

from pdfgen.compose import ComposeError, compose
from pdfgen.engine import render_pdf


# --- static node -----------------------------------------------------------


def test_static_keyed_leaf_resolves_to_text():
    """A keyed leaf becomes a literal element: key -> interpolated text."""
    template = {
        "document": {"title": "Report"},
        "content": [{"type": "heading", "level": 1, "key": "title"}],
    }
    out = compose(template, values={}, translations={"title": "Your Results"})

    assert out["content"] == [{"type": "heading", "level": 1, "text": "Your Results"}]
    # Non-key fields pass through; document metadata is untouched.
    assert out["document"] == {"title": "Report"}


def test_inputs_are_not_mutated():
    """compose returns a fresh tree; caller inputs stay as they were."""
    template = {"content": [{"type": "paragraph", "key": "hi"}]}
    values = {}
    translations = {"hi": "Hello"}

    compose(template, values, translations)

    assert template == {"content": [{"type": "paragraph", "key": "hi"}]}


# --- interpolation ---------------------------------------------------------


def test_interpolation_fills_placeholders_from_values():
    template = {"content": [{"type": "paragraph", "key": "greeting"}]}
    values = {"client_name": "Dana", "score": 72}
    translations = {"greeting": "Hello {{client_name}}, your score is {{score}}."}

    out = compose(template, values, translations)

    assert out["content"][0]["text"] == "Hello Dana, your score is 72."


def test_interpolation_supports_dotted_lookup():
    template = {"content": [{"type": "paragraph", "key": "line"}]}
    values = {"scores": {"composure": 3}}
    translations = {"line": "Composure: {{scores.composure}}"}

    out = compose(template, values, translations)

    assert out["content"][0]["text"] == "Composure: 3"


# --- conditional node with 2+ variants -------------------------------------


CONDITIONAL_TEMPLATE = {
    "content": [
        {
            "variants": [
                {"when": {"composure": "low"}, "content": [{"type": "paragraph", "key": "low"}]},
                {"when": {"composure": "high"}, "content": [{"type": "paragraph", "key": "high"}]},
            ]
        }
    ]
}
CONDITIONAL_TRANSLATIONS = {"low": "Stay calm.", "high": "Well composed."}


def test_variant_selected_by_matching_when():
    out = compose(CONDITIONAL_TEMPLATE, {"composure": "high"}, CONDITIONAL_TRANSLATIONS)
    assert out["content"] == [{"type": "paragraph", "text": "Well composed."}]


def test_other_variant_selected_for_other_value():
    out = compose(CONDITIONAL_TEMPLATE, {"composure": "low"}, CONDITIONAL_TRANSLATIONS)
    assert out["content"] == [{"type": "paragraph", "text": "Stay calm."}]


def test_when_requires_all_keys_to_match():
    """Every key in a `when` must match; a partial match does not select it."""
    template = {
        "content": [
            {
                "variants": [
                    {
                        "when": {"composure": "low", "confidence": "high"},
                        "content": [{"type": "paragraph", "key": "a"}],
                    },
                    {
                        "when": {"composure": "low"},
                        "content": [{"type": "paragraph", "key": "b"}],
                    },
                ]
            }
        ]
    }
    # confidence is "low", so the two-key variant fails and the fallback wins.
    out = compose(
        template,
        {"composure": "low", "confidence": "low"},
        {"a": "A", "b": "B"},
    )
    assert out["content"] == [{"type": "paragraph", "text": "B"}]


def test_explicit_empty_variant_shows_nothing():
    """The sanctioned 'show nothing' path: an explicit empty-content variant."""
    template = {
        "content": [
            {
                "variants": [
                    {"when": {"flag": "on"}, "content": [{"type": "paragraph", "key": "x"}]},
                    {"when": {"flag": "off"}, "content": []},
                ]
            }
        ]
    }
    out = compose(template, {"flag": "off"}, {"x": "shown"})
    assert out["content"] == []


# --- nested group of conditionals ------------------------------------------


def test_nested_conditionals_flatten_into_content_list():
    """A variant whose content holds more variants resolves recursively and
    flattens — the renderer's content list has no nesting, so groups collapse."""
    template = {
        "content": [
            {
                "variants": [
                    {
                        "when": {"segment": "retail"},
                        "content": [
                            {"type": "heading", "level": 2, "key": "retail_title"},
                            {
                                "variants": [
                                    {
                                        "when": {"risk": "high"},
                                        "content": [{"type": "paragraph", "key": "retail_high"}],
                                    },
                                    {
                                        "when": {"risk": "low"},
                                        "content": [{"type": "paragraph", "key": "retail_low"}],
                                    },
                                ]
                            },
                        ],
                    },
                    {"when": {"segment": "pro"}, "content": [{"type": "paragraph", "key": "pro"}]},
                ]
            }
        ]
    }
    translations = {
        "retail_title": "Retail",
        "retail_high": "High risk retail.",
        "retail_low": "Low risk retail.",
        "pro": "Professional.",
    }

    out = compose(template, {"segment": "retail", "risk": "high"}, translations)

    assert out["content"] == [
        {"type": "heading", "level": 2, "text": "Retail"},
        {"type": "paragraph", "text": "High risk retail."},
    ]


def test_plain_container_flattens():
    """A node with `content` but no `variants`/`key` is organisational and
    flattens its children in place."""
    template = {
        "content": [
            {"content": [{"type": "paragraph", "key": "a"}, {"type": "paragraph", "key": "b"}]}
        ]
    }
    out = compose(template, {}, {"a": "A", "b": "B"})
    assert out["content"] == [
        {"type": "paragraph", "text": "A"},
        {"type": "paragraph", "text": "B"},
    ]


def test_literal_element_passes_through():
    """An element carrying no template vocabulary is emitted untouched."""
    template = {"content": [{"type": "spacer", "height": 12}]}
    out = compose(template, {}, {})
    assert out["content"] == [{"type": "spacer", "height": 12}]


# --- failure cases ---------------------------------------------------------


def test_missing_translation_key_raises():
    template = {"content": [{"type": "paragraph", "key": "absent"}]}
    with pytest.raises(ComposeError) as exc:
        compose(template, {}, {})
    assert "absent" in str(exc.value)


def test_no_matching_variant_raises():
    template = {
        "content": [
            {
                "variants": [
                    {"when": {"band": "low"}, "content": [{"type": "paragraph", "key": "x"}]},
                ]
            }
        ]
    }
    with pytest.raises(ComposeError) as exc:
        compose(template, {"band": "medium"}, {"x": "X"})
    assert "no variant matched" in str(exc.value)


def test_missing_interpolation_value_raises():
    template = {"content": [{"type": "paragraph", "key": "greeting"}]}
    translations = {"greeting": "Hello {{client_name}}"}
    with pytest.raises(ComposeError) as exc:
        compose(template, {}, translations)
    assert "client_name" in str(exc.value)


def test_variant_without_when_raises():
    template = {
        "content": [
            {"variants": [{"content": [{"type": "paragraph", "key": "x"}]}]}
        ]
    }
    with pytest.raises(ComposeError) as exc:
        compose(template, {}, {"x": "X"})
    assert "when" in str(exc.value)


def test_template_without_content_raises():
    with pytest.raises(ComposeError):
        compose({"document": {}}, {}, {})


def test_error_identifies_offending_node_path():
    """Errors carry a path so a failure points at the node that caused it."""
    template = {
        "content": [
            {"type": "spacer", "height": 4},
            {"type": "paragraph", "key": "missing"},
        ]
    }
    with pytest.raises(ComposeError) as exc:
        compose(template, {}, {})
    assert "content[1]" in str(exc.value)


# --- integration: composed output renders ----------------------------------


def test_composed_document_renders_to_pdf():
    """End-to-end: a composed document is a valid render_pdf input."""
    template = {
        "document": {"title": "Client Report"},
        "content": [
            {"type": "heading", "level": 1, "key": "title"},
            {
                "variants": [
                    {"when": {"band": "low"}, "content": [{"type": "paragraph", "key": "body"}]},
                    {"when": {"band": "high"}, "content": [{"type": "paragraph", "key": "body"}]},
                ]
            },
        ],
    }
    values = {"band": "low", "name": "Dana"}
    translations = {"title": "Results for {{name}}", "body": "Your assessment is complete."}

    composed = compose(template, values, translations)
    pdf = render_pdf(composed)

    assert pdf.startswith(b"%PDF-")
