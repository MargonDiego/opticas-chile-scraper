"""Unit tests for the canonical embedding-text builder (no database, no I/O)."""

from src.services.embedding_text import (
    MAX_EMBEDDING_TEXT_CHARS,
    build_embedding_text,
    store_display_name,
    truncate_at_word_boundary,
)


def test_parts_follow_the_documented_order():
    text = build_embedding_text(
        brand="Ray-Ban",
        model_name="Aviator Large Metal",
        category="opticos",
        store="gmo",
        description="Clásico de aviador con lentes verdes.",
    )

    assert text == (
        "Ray-Ban Aviator Large Metal opticos GMO Chile "
        "Clásico de aviador con lentes verdes."
    )


def test_missing_fields_are_skipped_without_leaving_gaps():
    text = build_embedding_text(brand="Polaroid", model_name="Kids 0100")

    assert text == "Polaroid Kids 0100"
    assert "  " not in text


def test_all_empty_fields_produce_an_empty_string():
    assert build_embedding_text() == ""
    assert build_embedding_text(brand="", model_name="   ", description=None) == ""


def test_whitespace_is_normalized():
    text = build_embedding_text(
        brand="  Ray\n\tBan  ",
        model_name="Aviator   Large",
        category=" opticos ",
        store="gmo",
        description="  Lentes \n\n de   sol  ",
    )

    assert text == "Ray Ban Aviator Large opticos GMO Chile Lentes de sol"
    assert "\n" not in text
    assert "\t" not in text


def test_html_markup_is_stripped_from_descriptions():
    text = build_embedding_text(
        brand="Vogue",
        model_name="VO1234",
        description="<p>Armazón <strong>infantil</strong></p>",
    )

    assert "<" not in text
    assert ">" not in text
    assert "Armazón infantil" in text


def test_store_id_maps_to_its_display_name():
    assert store_display_name("ryk") == "Rotter & Krauss"
    # Unknown ids stay usable instead of silently disappearing.
    assert store_display_name("new_store") == "new_store"
    assert store_display_name(None) == ""


def test_truncation_happens_at_a_word_boundary():
    description = " ".join(["palabra"] * 400)
    text = build_embedding_text(
        brand="Polaroid",
        model_name="Kids",
        description=description,
    )

    assert len(text) <= MAX_EMBEDDING_TEXT_CHARS
    assert text.startswith("Polaroid Kids ")
    # The description was cut, but never in the middle of a word.
    assert text.endswith("palabra")
    assert text == text.strip()


def test_truncate_at_word_boundary_moves_back_to_the_last_space():
    assert truncate_at_word_boundary("alpha beta gamma", max_chars=12) == "alpha beta"


def test_truncate_at_word_boundary_falls_back_to_a_hard_cut_for_one_long_word():
    assert truncate_at_word_boundary("x" * 20, max_chars=5) == "xxxxx"


def test_truncate_keeps_short_text_intact():
    assert truncate_at_word_boundary("short text", max_chars=100) == "short text"


def test_output_is_deterministic():
    kwargs = {
        "brand": "Ray-Ban",
        "model_name": "Aviator",
        "category": "sol",
        "store": "ryk",
        "description": "Lentes polarizados.",
    }

    first = build_embedding_text(**kwargs)
    second = build_embedding_text(**kwargs)

    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")
