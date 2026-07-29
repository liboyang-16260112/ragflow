#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""Focused schema tests for the API-surface manifest module.

These tests verify that the manifest schema:

* Accepts valid policy entries with all required fields.
* Rejects invalid enum values for visibility, stability, and runtime.
* Rejects duplicate canonical keys.
* Rejects compatibility entries missing ``canonical_replacement``.
* Rejects public entries missing ``http_reference`` or ``contract_test``.
"""

import pytest

from scripts.living_map.manifest_schema import (
    ManifestEntry,
    canonical_key,
    validate_manifest,
    VISIBILITY_VALUES,
    STABILITY_VALUES,
    RUNTIME_VALUES,
)


# ---------------------------------------------------------------------------
# canonical_key helper
# ---------------------------------------------------------------------------

def test_canonical_key_normalizes_method_and_path():
    assert canonical_key("get", "/api/v1/datasets") == "GET /api/v1/datasets"
    assert canonical_key("POST", "/api/v1/datasets/{dataset_id}/") == "POST /api/v1/datasets/{dataset_id}"


def test_canonical_key_trailing_slash_root():
    assert canonical_key("GET", "/") == "GET /"


# ---------------------------------------------------------------------------
# Valid entries
# ---------------------------------------------------------------------------

def test_valid_public_entry():
    e = ManifestEntry(
        method="GET",
        path="/api/v1/datasets",
        capability="数据集管理",
        visibility="public",
        stability="stable",
        runtime="both",
        http_reference="references/http_api_reference.md#get-apiv1datasets",
        sdk_reference="sdk/python/ragflow_sdk/modules/dataset.py",
        contract_test="api/apps/restful_apis/dataset_api.py",
    )
    assert e.key == "GET /api/v1/datasets"
    assert validate_manifest([e]) == []


def test_valid_internal_entry():
    e = ManifestEntry(
        method="POST",
        path="/api/v1/system/status",
        capability="系统管理",
        visibility="internal",
        stability="stable",
        runtime="python",
    )
    assert validate_manifest([e]) == []


def test_valid_compatibility_entry_with_replacement():
    e = ManifestEntry(
        method="POST",
        path="/api/v1/chats/{chat_id}/completions",
        capability="会话管理",
        visibility="compatibility",
        stability="deprecated",
        runtime="python",
        canonical_replacement="POST /api/v1/chat/completions",
    )
    assert validate_manifest([e]) == []


def test_valid_beta_entry():
    e = ManifestEntry(
        method="GET",
        path="/api/v1/experimental/feature",
        capability="实验功能",
        visibility="beta",
        stability="experimental",
        runtime="go-only",
    )
    assert validate_manifest([e]) == []


def test_multiple_valid_entries():
    entries = [
        ManifestEntry(
            method="GET",
            path="/api/v1/datasets",
            capability="数据集管理",
            visibility="public",
            stability="stable",
            runtime="both",
            http_reference="references/http_api_reference.md#get-apiv1datasets",
            contract_test="api/apps/restful_apis/dataset_api.py",
        ),
        ManifestEntry(
            method="POST",
            path="/api/v1/datasets",
            capability="数据集管理",
            visibility="public",
            stability="stable",
            runtime="both",
            http_reference="references/http_api_reference.md#post-apiv1datasets",
            contract_test="api/apps/restful_apis/dataset_api.py",
        ),
    ]
    assert validate_manifest(entries) == []


# ---------------------------------------------------------------------------
# Invalid enum values
# ---------------------------------------------------------------------------

def test_rejects_invalid_visibility():
    e = ManifestEntry(
        method="GET",
        path="/api/v1/bad",
        capability="测试",
        visibility="INVALID_VISIBILITY",
        stability="stable",
        runtime="python",
    )
    errors = validate_manifest([e])
    assert any("invalid visibility" in err for err in errors)


def test_rejects_invalid_stability():
    e = ManifestEntry(
        method="GET",
        path="/api/v1/bad",
        capability="测试",
        visibility="public",
        stability="INVALID_STABILITY",
        runtime="python",
        http_reference="ref",
        contract_test="test",
    )
    errors = validate_manifest([e])
    assert any("invalid stability" in err for err in errors)


def test_rejects_invalid_runtime():
    e = ManifestEntry(
        method="GET",
        path="/api/v1/bad",
        capability="测试",
        visibility="public",
        stability="stable",
        runtime="INVALID_RUNTIME",
        http_reference="ref",
        contract_test="test",
    )
    errors = validate_manifest([e])
    assert any("invalid runtime" in err for err in errors)


# ---------------------------------------------------------------------------
# Duplicate canonical keys
# ---------------------------------------------------------------------------

def test_rejects_duplicate_keys():
    entries = [
        ManifestEntry(
            method="GET",
            path="/api/v1/datasets",
            capability="数据集管理",
            visibility="public",
            stability="stable",
            runtime="both",
            http_reference="ref1",
            contract_test="test1",
        ),
        ManifestEntry(
            method="GET",
            path="/api/v1/datasets",
            capability="重复条目",
            visibility="internal",
            stability="stable",
            runtime="python",
        ),
    ]
    errors = validate_manifest(entries)
    assert any("Duplicate canonical key" in err for err in errors)


# ---------------------------------------------------------------------------
# Missing required fields for public entries
# ---------------------------------------------------------------------------

def test_rejects_public_without_http_reference():
    e = ManifestEntry(
        method="GET",
        path="/api/v1/datasets/{dataset_id}",
        capability="数据集管理",
        visibility="public",
        stability="stable",
        runtime="both",
        http_reference=None,
        contract_test="test",
    )
    errors = validate_manifest([e])
    assert any("missing http_reference" in err for err in errors)


def test_rejects_public_without_contract_test():
    e = ManifestEntry(
        method="GET",
        path="/api/v1/datasets/{dataset_id}",
        capability="数据集管理",
        visibility="public",
        stability="stable",
        runtime="both",
        http_reference="ref",
        contract_test=None,
    )
    errors = validate_manifest([e])
    assert any("missing contract_test" in err for err in errors)


# ---------------------------------------------------------------------------
# Missing canonical_replacement for compatibility entries
# ---------------------------------------------------------------------------

def test_rejects_compatibility_without_replacement():
    e = ManifestEntry(
        method="POST",
        path="/api/v1/chats/{chat_id}/completions",
        capability="会话管理",
        visibility="compatibility",
        stability="deprecated",
        runtime="python",
        canonical_replacement=None,
    )
    errors = validate_manifest([e])
    assert any("missing canonical_replacement" in err for err in errors)


# ---------------------------------------------------------------------------
# Allowed values are well-formed
# ---------------------------------------------------------------------------

def test_visibility_values_are_nonempty_strings():
    for v in VISIBILITY_VALUES:
        assert isinstance(v, str) and v


def test_stability_values_are_nonempty_strings():
    for v in STABILITY_VALUES:
        assert isinstance(v, str) and v


def test_runtime_values_are_nonempty_strings():
    for v in RUNTIME_VALUES:
        assert isinstance(v, str) and v


# ---------------------------------------------------------------------------
# ManifestEntry serialization
# ---------------------------------------------------------------------------

def test_to_dict_omits_none_fields():
    e = ManifestEntry(
        method="GET",
        path="/api/v1/status",
        capability="系统管理",
        visibility="internal",
        stability="stable",
        runtime="python",
    )
    d = e.to_dict()
    assert "canonical_replacement" not in d
    assert "http_reference" not in d
    assert "sdk_reference" not in d
    assert "contract_test" not in d
    assert "notes" not in d


def test_to_dict_includes_optional_fields_when_set():
    e = ManifestEntry(
        method="GET",
        path="/api/v1/datasets",
        capability="数据集管理",
        visibility="public",
        stability="stable",
        runtime="both",
        http_reference="ref",
        sdk_reference="sdk_ref",
        contract_test="test",
        canonical_replacement="POST /api/v1/other",
        notes="some note",
    )
    d = e.to_dict()
    assert d["canonical_replacement"] == "POST /api/v1/other"
    assert d["http_reference"] == "ref"
    assert d["sdk_reference"] == "sdk_ref"
    assert d["contract_test"] == "test"
    assert d["notes"] == "some note"
