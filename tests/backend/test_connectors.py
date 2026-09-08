"""Unit tests for discourse-connector detection."""

from app.services.connectors import DISCOURSE_CONNECTORS, find_connectors


def test_connector_list_is_non_empty() -> None:
    assert DISCOURSE_CONNECTORS


def test_finds_connectors_case_insensitively() -> None:
    text = "Furthermore, we should act. On the other hand, it costs money."
    connectors = [m.connector for m in find_connectors(text)]
    assert "furthermore" in connectors
    assert "on the other hand" in connectors


def test_returns_offsets_in_document_order() -> None:
    text = "However, X. Therefore, Y."
    matches = find_connectors(text)
    assert [m.connector for m in matches] == ["however", "therefore"]
    assert matches[0].index < matches[1].index


def test_does_not_match_inside_longer_words() -> None:
    assert find_connectors("the howevering issue") == []


def test_empty_text_returns_no_matches() -> None:
    assert find_connectors("") == []


def test_reports_original_character_index() -> None:
    text = "Hello. Furthermore, bye."
    matches = find_connectors(text)
    assert matches[0].connector == "furthermore"
    assert text[matches[0].index : matches[0].index + len("furthermore")] == "Furthermore"
