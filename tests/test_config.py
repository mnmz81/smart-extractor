import pytest

from smart_extractor.config import Settings


def test_keys_default_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    settings = Settings(_env_file=None)
    assert settings.anthropic_api_key is None
    assert settings.google_api_key is None


def test_key_is_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-value-for-test")
    settings = Settings(_env_file=None)
    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "fake-value-for-test"


def test_key_is_masked_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-value-for-test")
    settings = Settings(_env_file=None)
    assert "fake-value-for-test" not in repr(settings)
    assert "fake-value-for-test" not in str(settings)
