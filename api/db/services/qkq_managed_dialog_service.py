from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager, nullcontext
from copy import deepcopy
from dataclasses import dataclass

from peewee import IntegrityError

from common import settings
from common.constants import StatusEnum
from common.misc_utils import get_uuid

QKQ_USER_ID_HEADER = "X-QKQ-User-Id"
_MANAGED_DIALOG_CONFIG_FIELDS = (
    "description",
    "icon",
    "language",
    "llm_id",
    "tenant_llm_id",
    "llm_setting",
    "prompt_type",
    "prompt_config",
    "meta_data_filter",
    "similarity_threshold",
    "vector_similarity_weight",
    "top_n",
    "rerank_candidates_count",
    "top_k",
    "do_refer",
    "rerank_id",
    "tenant_rerank_id",
    "kb_ids",
)


class QKQManagedDialogAccessError(PermissionError):
    """Controlled denial for embedded QKQ identity or Dialog ownership checks."""


@dataclass(frozen=True)
class QKQManagedIdentity:
    tenant_id: str
    external_user_id: str
    source: str


class QKQManagedDialogResolver:
    def __init__(
        self,
        config=None,
        dialog_service=None,
        atomic_factory: Callable[[], AbstractContextManager] | None = None,
        id_factory: Callable[[], str] | None = None,
    ):
        self._config = settings.QKQ_EMBEDDED_CHAT if config is None else config
        if dialog_service is None:
            from api.db.services.dialog_service import DialogService

            dialog_service = DialogService
        self._dialog_service = dialog_service
        # CommonService methods manage their own connection_context. Wrapping
        # them in DB.atomic() makes the inner context attempt to close a
        # connection while the outer transaction is still open. The unique
        # managed-binding index provides the required first-entry concurrency
        # guarantee, with IntegrityError handled below.
        self._atomic_factory = nullcontext if atomic_factory is None else atomic_factory
        self._id_factory = get_uuid if id_factory is None else id_factory

    def is_embedded_request(self, headers: Mapping[str, str]) -> bool:
        return self._config.enabled and QKQ_USER_ID_HEADER in headers

    def resolve_identity(self, headers: Mapping[str, str], authenticated_tenant_id: str) -> QKQManagedIdentity:
        if not self._config.enabled or self._config.identity_mode != "trusted-header":
            raise QKQManagedDialogAccessError("QKQ embedded chat is not enabled for trusted ingress")

        external_user_id = (headers.get(QKQ_USER_ID_HEADER) or "").strip()
        if not external_user_id:
            raise QKQManagedDialogAccessError("Missing trusted QKQ identity")

        template = self._get_template()
        if str(getattr(template, "tenant_id", "")) != str(authenticated_tenant_id or ""):
            raise QKQManagedDialogAccessError("Trusted QKQ ingress authentication required")

        return QKQManagedIdentity(
            tenant_id=str(template.tenant_id),
            external_user_id=external_user_id,
            source=self._config.source,
        )

    def list_dialogs(self, headers: Mapping[str, str], authenticated_tenant_id: str) -> list:
        identity = self.resolve_identity(headers, authenticated_tenant_id)
        return list(
            self._dialog_service.query(
                tenant_id=identity.tenant_id,
                source=identity.source,
                external_user_id=identity.external_user_id,
                status=StatusEnum.VALID.value,
            )
        )

    @staticmethod
    def validate_file_descriptors(dialog_id: str, messages: list[dict]) -> None:
        for message in messages or []:
            for file_info in message.get("files") or []:
                if (
                    not isinstance(file_info, dict)
                    or not file_info.get("id")
                    or str(file_info.get("created_by", "")) != str(dialog_id)
                ):
                    raise QKQManagedDialogAccessError("Managed attachment not found")

    def resolve_dialog(self, dialog_id: str, headers: Mapping[str, str], authenticated_tenant_id: str):
        identity = self.resolve_identity(headers, authenticated_tenant_id)
        exists, dialog = self._dialog_service.get_by_id(dialog_id)
        if not exists or not self._is_owned_by(dialog, identity):
            raise QKQManagedDialogAccessError("Managed chat not found")
        return dialog

    def ensure_dialog(self, headers: Mapping[str, str], authenticated_tenant_id: str):
        identity = self.resolve_identity(headers, authenticated_tenant_id)
        template = self._get_template()
        payload = self._build_managed_dialog_payload(template, identity)

        try:
            with self._atomic_factory():
                existing = self._find_managed_dialog(identity)
                if existing is not None:
                    if str(getattr(existing, "status", "")) == StatusEnum.VALID.value:
                        return existing
                    self._dialog_service.update_by_id(existing.id, payload)
                    exists, reactivated = self._dialog_service.get_by_id(existing.id)
                    if not exists:
                        raise LookupError("Managed chat could not be reactivated")
                    return reactivated

                dialog_id = self._id_factory()
                self._dialog_service.save(id=dialog_id, **payload)
                exists, created = self._dialog_service.get_by_id(dialog_id)
                if not exists:
                    raise LookupError("Managed chat could not be created")
                return created
        except IntegrityError:
            # A concurrent first-entry request won the unique key race. Its
            # transaction is complete before the unique violation is surfaced,
            # so resolving the binding now returns the single winning Dialog.
            existing = self._find_managed_dialog(identity)
            if existing is not None and str(getattr(existing, "status", "")) == StatusEnum.VALID.value:
                return existing
            raise

    def _get_template(self):
        exists, template = self._dialog_service.get_by_id(self._config.template_chat_id)
        if not exists or str(getattr(template, "status", "")) != StatusEnum.VALID.value:
            raise QKQManagedDialogAccessError("QKQ template chat is unavailable")
        return template

    def _find_managed_dialog(self, identity: QKQManagedIdentity):
        dialogs = self._dialog_service.query(
            tenant_id=identity.tenant_id,
            source=identity.source,
            external_user_id=identity.external_user_id,
        )
        return next(iter(dialogs), None)

    @staticmethod
    def _build_managed_dialog_payload(template, identity: QKQManagedIdentity) -> dict:
        payload = {
            "tenant_id": identity.tenant_id,
            "source": identity.source,
            "external_user_id": identity.external_user_id,
            "name": f"知识问答-qkq-{identity.external_user_id}",
            "status": StatusEnum.VALID.value,
        }
        for field in _MANAGED_DIALOG_CONFIG_FIELDS:
            if hasattr(template, field):
                payload[field] = deepcopy(getattr(template, field))
        return payload

    @staticmethod
    def _is_owned_by(dialog, identity: QKQManagedIdentity) -> bool:
        return (
            str(getattr(dialog, "status", "")) == StatusEnum.VALID.value
            and str(getattr(dialog, "tenant_id", "")) == identity.tenant_id
            and getattr(dialog, "source", None) == identity.source
            and str(getattr(dialog, "external_user_id", "")) == identity.external_user_id
        )
