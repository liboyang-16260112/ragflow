import ast
from pathlib import Path

CHAT_API = Path(__file__).parents[5] / "api" / "apps" / "restful_apis" / "chat_api.py"


def _module():
    return ast.parse(CHAT_API.read_text())


def _function_source(name):
    tree = _module()
    node = next(item for item in tree.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name)
    return ast.unparse(node)


def test_managed_ownership_fields_are_not_mutable_through_chat_updates():
    tree = _module()
    assignment = next(
        item
        for item in tree.body
        if isinstance(item, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "_READONLY_FIELDS" for target in item.targets)
    )
    fields = ast.literal_eval(assignment.value)

    assert {"source", "external_user_id"} <= fields


def test_chat_detail_update_and_delete_use_managed_dialog_resolver():
    ensure_source = _function_source("_ensure_owned_chat")
    detail_source = _function_source("get_chat")

    assert "QKQManagedDialogResolver" in ensure_source
    assert "resolve_dialog" in ensure_source
    assert "is_embedded_request" in detail_source
    assert "resolve_dialog" in detail_source


def test_bulk_delete_scopes_delete_all_and_legacy_id_to_managed_owner():
    source = _function_source("bulk_delete_chats")

    assert "list_dialogs" in source
    assert "_ensure_owned_chat" in source


def test_all_conversation_routes_resolve_the_owned_chat_first():
    for function_name in ("create_session", "list_sessions", "get_session", "update_session", "delete_sessions"):
        assert "_ensure_owned_chat" in _function_source(function_name), function_name


def test_session_creation_allows_same_name_in_different_managed_chats():
    source = _function_source("create_session")

    assert "duplicated" not in source
    assert "ConversationService.query" not in source


def test_completion_feedback_and_reference_paths_resolve_chat_and_session_ownership():
    for function_name in ("session_completion", "delete_session_message", "update_message_feedback"):
        source = _function_source(function_name)
        assert "_ensure_owned_chat" in source, function_name
        assert "dialog_id" in source, function_name


def test_managed_file_routes_resolve_chat_ownership_and_use_chat_scoped_storage():
    for function_name in ("upload_chat_files", "download_chat_file", "delete_chat_file"):
        source = _function_source(function_name)
        assert "_ensure_owned_chat" in source, function_name
        assert "chat_id" in source, function_name


def test_completion_rejects_file_descriptors_from_another_managed_chat():
    source = _function_source("session_completion")

    assert "validate_file_descriptors" in source
