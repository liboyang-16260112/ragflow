import pytest

from common import settings


def test_qkq_embedded_chat_is_optional_when_disabled():
    config = settings.load_qkq_embedded_chat_config({})

    assert config.enabled is False
    assert config.source == ""
    assert config.template_chat_id == ""
    assert config.identity_mode == ""


def test_qkq_embedded_chat_loads_trusted_header_configuration():
    config = settings.load_qkq_embedded_chat_config(
        {
            "QKQ_EMBEDDED_CHAT_ENABLED": "true",
            "QKQ_EMBEDDED_CHAT_SOURCE": " qkq ",
            "QKQ_EMBEDDED_CHAT_TEMPLATE_CHAT_ID": " template-001 ",
            "QKQ_EMBEDDED_CHAT_IDENTITY_MODE": " trusted-header ",
        }
    )

    assert config.enabled is True
    assert config.source == "qkq"
    assert config.template_chat_id == "template-001"
    assert config.identity_mode == "trusted-header"


@pytest.mark.parametrize(
    ("missing_name", "environment"),
    [
        (
            "QKQ_EMBEDDED_CHAT_SOURCE",
            {
                "QKQ_EMBEDDED_CHAT_ENABLED": "1",
                "QKQ_EMBEDDED_CHAT_TEMPLATE_CHAT_ID": "template-001",
                "QKQ_EMBEDDED_CHAT_IDENTITY_MODE": "trusted-header",
            },
        ),
        (
            "QKQ_EMBEDDED_CHAT_TEMPLATE_CHAT_ID",
            {
                "QKQ_EMBEDDED_CHAT_ENABLED": "1",
                "QKQ_EMBEDDED_CHAT_SOURCE": "qkq",
                "QKQ_EMBEDDED_CHAT_IDENTITY_MODE": "trusted-header",
            },
        ),
    ],
)
def test_enabled_qkq_embedded_chat_rejects_missing_mandatory_values(missing_name, environment):
    with pytest.raises(ValueError, match=missing_name):
        settings.load_qkq_embedded_chat_config(environment)


def test_enabled_qkq_embedded_chat_rejects_untrusted_identity_mode():
    with pytest.raises(ValueError, match="QKQ_EMBEDDED_CHAT_IDENTITY_MODE"):
        settings.load_qkq_embedded_chat_config(
            {
                "QKQ_EMBEDDED_CHAT_ENABLED": "yes",
                "QKQ_EMBEDDED_CHAT_SOURCE": "qkq",
                "QKQ_EMBEDDED_CHAT_TEMPLATE_CHAT_ID": "template-001",
                "QKQ_EMBEDDED_CHAT_IDENTITY_MODE": "browser-header",
            }
        )


def test_init_settings_fails_before_service_start_when_enabled_configuration_is_incomplete(monkeypatch):
    monkeypatch.setenv("QKQ_EMBEDDED_CHAT_ENABLED", "true")
    monkeypatch.delenv("QKQ_EMBEDDED_CHAT_SOURCE", raising=False)
    monkeypatch.delenv("QKQ_EMBEDDED_CHAT_TEMPLATE_CHAT_ID", raising=False)
    monkeypatch.setenv("QKQ_EMBEDDED_CHAT_IDENTITY_MODE", "trusted-header")

    with pytest.raises(ValueError, match="QKQ_EMBEDDED_CHAT_SOURCE"):
        settings.init_settings()
