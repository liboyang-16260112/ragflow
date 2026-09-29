from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from threading import Barrier, Lock
from types import SimpleNamespace
from typing import ClassVar

import pytest
from peewee import IntegrityError

from api.db.services.qkq_managed_dialog_service import (
    QKQManagedDialogAccessError,
    QKQManagedDialogResolver,
)
from common.constants import StatusEnum
from common.settings import QKQEmbeddedChatConfig


class FakeDialogService:
    dialogs: ClassVar[dict] = {}

    @classmethod
    def get_by_id(cls, dialog_id):
        dialog = cls.dialogs.get(dialog_id)
        return dialog is not None, dialog

    @classmethod
    def query(cls, **filters):
        return [
            dialog
            for dialog in cls.dialogs.values()
            if all(getattr(dialog, key, None) == value for key, value in filters.items())
        ]

    @classmethod
    def save(cls, **payload):
        dialog = SimpleNamespace(**payload)
        cls.dialogs[dialog.id] = dialog
        return 1

    @classmethod
    def update_by_id(cls, dialog_id, payload):
        dialog = cls.dialogs.get(dialog_id)
        if dialog is None:
            return 0
        for key, value in payload.items():
            setattr(dialog, key, value)
        return 1


@pytest.fixture
def resolver():
    FakeDialogService.dialogs = {
        "template-001": SimpleNamespace(
            id="template-001",
            tenant_id="shared-tenant",
            status=StatusEnum.VALID.value,
            source=None,
            external_user_id=None,
        ),
        "managed-a": SimpleNamespace(
            id="managed-a",
            tenant_id="shared-tenant",
            status=StatusEnum.VALID.value,
            source="qkq",
            external_user_id="user-a",
        ),
        "managed-b": SimpleNamespace(
            id="managed-b",
            tenant_id="shared-tenant",
            status=StatusEnum.VALID.value,
            source="qkq",
            external_user_id="user-b",
        ),
    }
    return QKQManagedDialogResolver(
        config=QKQEmbeddedChatConfig(
            enabled=True,
            source="qkq",
            template_chat_id="template-001",
            identity_mode="trusted-header",
        ),
        dialog_service=FakeDialogService,
        atomic_factory=nullcontext,
        id_factory=lambda: "managed-c",
    )


def test_rejects_missing_trusted_user_identity(resolver):
    with pytest.raises(QKQManagedDialogAccessError, match="Missing trusted QKQ identity"):
        resolver.resolve_identity({}, authenticated_tenant_id="shared-tenant")


def test_rejects_forged_header_from_non_shared_tenant(resolver):
    with pytest.raises(QKQManagedDialogAccessError, match="Trusted QKQ ingress authentication required"):
        resolver.resolve_identity(
            {"X-QKQ-User-Id": "user-a"},
            authenticated_tenant_id="browser-user-tenant",
        )


def test_rejects_dialog_owned_by_another_qkq_user(resolver):
    with pytest.raises(QKQManagedDialogAccessError, match="Managed chat not found"):
        resolver.resolve_dialog(
            "managed-b",
            {"X-QKQ-User-Id": "user-a"},
            authenticated_tenant_id="shared-tenant",
        )


def test_returns_dialog_for_valid_trusted_identity(resolver):
    dialog = resolver.resolve_dialog(
        "managed-a",
        {"X-QKQ-User-Id": " user-a "},
        authenticated_tenant_id="shared-tenant",
    )

    assert dialog.id == "managed-a"
    assert dialog.external_user_id == "user-a"


def test_ensure_dialog_clones_only_template_configuration(resolver):
    template = FakeDialogService.dialogs["template-001"]
    template.name = "template"
    template.description = "approved"
    template.icon = "template-icon"
    template.language = "Chinese"
    template.llm_id = "model-1"
    template.tenant_llm_id = "tenant-model-1"
    template.llm_setting = {"temperature": 0.2}
    template.prompt_type = "simple"
    template.prompt_config = {"system": "approved prompt"}
    template.meta_data_filter = {"department": "legal"}
    template.similarity_threshold = 0.3
    template.vector_similarity_weight = 0.7
    template.top_n = 8
    template.rerank_candidates_count = 80
    template.top_k = 256
    template.do_refer = "1"
    template.rerank_id = "reranker-1"
    template.tenant_rerank_id = "tenant-reranker-1"
    template.kb_ids = ["shared-kb"]
    template.sessions = ["must-not-copy"]
    template.messages = ["must-not-copy"]

    dialog = resolver.ensure_dialog(
        {"X-QKQ-User-Id": "user-c"},
        authenticated_tenant_id="shared-tenant",
    )

    assert dialog.name == "知识问答-qkq-user-c"
    assert dialog.source == "qkq"
    assert dialog.external_user_id == "user-c"
    assert dialog.kb_ids == ["shared-kb"]
    assert dialog.prompt_config == {"system": "approved prompt"}
    assert not hasattr(dialog, "sessions")
    assert not hasattr(dialog, "messages")
    assert dialog.kb_ids is not template.kb_ids
    assert dialog.prompt_config is not template.prompt_config


def test_repeated_ensure_returns_the_same_dialog(resolver):
    first = resolver.ensure_dialog(
        {"X-QKQ-User-Id": "user-c"},
        authenticated_tenant_id="shared-tenant",
    )
    second = resolver.ensure_dialog(
        {"X-QKQ-User-Id": "user-c"},
        authenticated_tenant_id="shared-tenant",
    )

    assert second.id == first.id
    assert len([dialog for dialog in FakeDialogService.dialogs.values() if getattr(dialog, "external_user_id", None) == "user-c"]) == 1


def test_concurrent_ensure_returns_one_dialog():
    class ConcurrentDialogService(FakeDialogService):
        dialogs: ClassVar[dict] = {
            "template-001": SimpleNamespace(
                id="template-001",
                tenant_id="shared-tenant",
                status=StatusEnum.VALID.value,
                kb_ids=["shared-kb"],
                prompt_config={"system": "approved"},
            )
        }
        barrier = Barrier(2)
        lock = Lock()

        @classmethod
        def query(cls, **filters):
            with cls.lock:
                matches = [
                    dialog
                    for dialog in cls.dialogs.values()
                    if all(getattr(dialog, key, None) == value for key, value in filters.items())
                ]
            if not matches:
                cls.barrier.wait(timeout=5)
            return matches

        @classmethod
        def save(cls, **payload):
            binding = (payload["tenant_id"], payload["source"], payload["external_user_id"])
            with cls.lock:
                if any(
                    (dialog.tenant_id, getattr(dialog, "source", None), getattr(dialog, "external_user_id", None)) == binding
                    for dialog in cls.dialogs.values()
                ):
                    raise IntegrityError("duplicate managed dialog binding")
                cls.dialogs[payload["id"]] = SimpleNamespace(**payload)
            return 1

    ids = iter(("managed-race-a", "managed-race-b"))
    ids_lock = Lock()

    def next_id():
        with ids_lock:
            return next(ids)

    resolver = QKQManagedDialogResolver(
        config=QKQEmbeddedChatConfig(
            enabled=True,
            source="qkq",
            template_chat_id="template-001",
            identity_mode="trusted-header",
        ),
        dialog_service=ConcurrentDialogService,
        atomic_factory=nullcontext,
        id_factory=next_id,
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: resolver.ensure_dialog(
                    {"X-QKQ-User-Id": "user-race"},
                    authenticated_tenant_id="shared-tenant",
                ),
                range(2),
            )
        )

    assert {dialog.id for dialog in results} in ({"managed-race-a"}, {"managed-race-b"})
    assert len(
        [
            dialog
            for dialog in ConcurrentDialogService.dialogs.values()
            if getattr(dialog, "external_user_id", None) == "user-race"
        ]
    ) == 1


def test_embedded_list_returns_only_current_qkq_users_managed_chat(resolver):
    assert resolver.is_embedded_request({"X-QKQ-User-Id": "user-a"}) is True

    dialogs = resolver.list_dialogs(
        {"X-QKQ-User-Id": "user-a"},
        authenticated_tenant_id="shared-tenant",
    )

    assert [dialog.id for dialog in dialogs] == ["managed-a"]


def test_request_without_qkq_header_remains_non_embedded(resolver):
    assert resolver.is_embedded_request({}) is False


def test_rejects_file_descriptor_from_another_managed_chat(resolver):
    with pytest.raises(QKQManagedDialogAccessError, match="Managed attachment not found"):
        resolver.validate_file_descriptors(
            "managed-a",
            [{"role": "user", "files": [{"id": "file-b", "created_by": "managed-b"}]}],
        )


def test_accepts_file_descriptor_scoped_to_current_managed_chat(resolver):
    resolver.validate_file_descriptors(
        "managed-a",
        [{"role": "user", "files": [{"id": "file-a", "created_by": "managed-a"}]}],
    )


def test_managed_dialogs_share_template_kb_ids_but_keep_independent_configuration():
    FakeDialogService.dialogs = {
        "template-001": SimpleNamespace(
            id="template-001",
            tenant_id="shared-tenant",
            status=StatusEnum.VALID.value,
            kb_ids=["shared-kb"],
            prompt_config={"system": "approved"},
            llm_setting={"temperature": 0.2},
        )
    }
    ids = iter(("managed-a", "managed-b"))
    resolver = QKQManagedDialogResolver(
        config=QKQEmbeddedChatConfig(
            enabled=True,
            source="qkq",
            template_chat_id="template-001",
            identity_mode="trusted-header",
        ),
        dialog_service=FakeDialogService,
        atomic_factory=nullcontext,
        id_factory=lambda: next(ids),
    )

    dialog_a = resolver.ensure_dialog({"X-QKQ-User-Id": "user-a"}, "shared-tenant")
    dialog_b = resolver.ensure_dialog({"X-QKQ-User-Id": "user-b"}, "shared-tenant")
    dialog_a.prompt_config["system"] = "user-a prompt"
    dialog_a.llm_setting["temperature"] = 0.9

    assert dialog_a.kb_ids == dialog_b.kb_ids == ["shared-kb"]
    assert dialog_b.prompt_config == {"system": "approved"}
    assert dialog_b.llm_setting == {"temperature": 0.2}
    assert dialog_a.prompt_config is not dialog_b.prompt_config
    assert dialog_a.llm_setting is not dialog_b.llm_setting


def test_default_ensure_uses_no_outer_database_transaction():
    FakeDialogService.dialogs = {
        "template-001": SimpleNamespace(
            id="template-001",
            tenant_id="shared-tenant",
            status=StatusEnum.VALID.value,
            kb_ids=["shared-kb"],
            prompt_config={"system": "approved"},
            llm_setting={"temperature": 0.2},
        )
    }
    resolver = QKQManagedDialogResolver(
        config=QKQEmbeddedChatConfig(
            enabled=True,
            source="qkq",
            template_chat_id="template-001",
            identity_mode="trusted-header",
        ),
        dialog_service=FakeDialogService,
        id_factory=lambda: "managed-default-no-atomic",
    )

    dialog = resolver.ensure_dialog(
        {"X-QKQ-User-Id": "user-default-no-atomic"},
        authenticated_tenant_id="shared-tenant",
    )

    assert dialog.id == "managed-default-no-atomic"
    assert dialog.external_user_id == "user-default-no-atomic"
