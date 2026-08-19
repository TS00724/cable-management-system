import pytest

from app.exceptions import ValidationError
from app.services.identifiers import normalize_identifier_part, render_identifier


def test_identifier_rendering_normalizes_and_formats_sequence() -> None:
    identifier = render_identifier(
        "{campus}-{building}-{kind}-{sequence:05d}",
        {"campus": "Main Campus", "building": "Engineering", "kind": "hc", "sequence": 12},
    )
    assert identifier == "MAIN-CAMPUS-ENGINEERING-HC-00012"


def test_identifier_missing_value_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Missing identifier template value"):
        render_identifier("{campus}-{building}", {"campus": "MC"})


def test_identifier_empty_component_is_rejected() -> None:
    with pytest.raises(ValidationError):
        normalize_identifier_part("***")
