from peewee import CharField

from api.db import db_models
from common import settings


def test_dialog_model_declares_nullable_qkq_ownership_and_unique_binding():
    assert isinstance(db_models.Dialog.source, CharField)
    assert db_models.Dialog.source.null is True
    assert isinstance(db_models.Dialog.external_user_id, CharField)
    assert db_models.Dialog.external_user_id.null is True
    assert (("tenant_id", "source", "external_user_id"), True) in db_models.Dialog._meta.indexes


def test_migrate_db_adds_qkq_dialog_ownership_columns(monkeypatch):
    added_columns = {}

    def record_add_column(_migrator, table_name, column_name, column_type):
        if table_name == "dialog" and column_name in {"source", "external_user_id"}:
            added_columns[column_name] = column_type

    monkeypatch.setattr(settings, "DATABASE_TYPE", "mysql")
    monkeypatch.setattr(db_models, "alter_db_add_column", record_add_column)
    monkeypatch.setattr(db_models, "alter_db_column_type", lambda *_args: None)
    monkeypatch.setattr(db_models, "alter_db_rename_column", lambda *_args: None)
    monkeypatch.setattr(db_models, "alter_db_drop_index", lambda *_args: None)
    monkeypatch.setattr(db_models, "relax_gaussdb_empty_string_compatible_columns", lambda: None)
    monkeypatch.setattr(db_models, "migrate", lambda *_operations: None)
    monkeypatch.setattr(db_models, "migrate_add_unique_email", lambda _migrator: None)
    monkeypatch.setattr(db_models, "migrate_model_type_names", lambda: None)
    monkeypatch.setattr(db_models, "ensure_model_indexes", lambda _migrator: None)

    db_models.migrate_db()

    assert set(added_columns) == {"source", "external_user_id"}
    assert all(isinstance(field, CharField) for field in added_columns.values())
    assert all(field.null is True for field in added_columns.values())


def test_unique_qkq_binding_index_creation_is_idempotent(monkeypatch):
    created = []

    class Index:
        columns = ("tenant_id", "source", "external_user_id")
        unique = True

    class FakeDB:
        @staticmethod
        def get_indexes(table_name):
            assert table_name == "dialog"
            return [Index()] if created else []

    class Migrator:
        @staticmethod
        def add_index(table_name, columns, unique=False):
            created.append((table_name, tuple(columns), unique))
            return object()

    monkeypatch.setattr(db_models, "DB", FakeDB)
    monkeypatch.setattr(
        db_models.inspect,
        "getmembers",
        lambda *_args, **_kwargs: [("Dialog", db_models.Dialog)],
    )
    monkeypatch.setattr(db_models, "migrate", lambda *_operations: None)

    db_models.ensure_model_indexes(Migrator())
    db_models.ensure_model_indexes(Migrator())

    qkq_binding_indexes = [
        item
        for item in created
        if item == ("dialog", ("tenant_id", "source", "external_user_id"), True)
    ]
    assert qkq_binding_indexes == [("dialog", ("tenant_id", "source", "external_user_id"), True)]
