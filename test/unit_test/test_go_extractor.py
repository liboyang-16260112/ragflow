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
"""Focused unit tests for the Go router extractor.

Covers:
* Nested Gin groups
* Path parameter normalization
* Direct engine routes
* Handler symbol extraction
* Dynamic / unresolvable diagnostic emission
"""

import textwrap

import sys
sys.path.insert(0, ".")

from scripts.living_map.go_extractor import _extract_one_go_file  # noqa: E402


# ---------------------------------------------------------------------------
# Nested groups + path parameters
# ---------------------------------------------------------------------------

def test_nested_group_and_path_params():
    source = textwrap.dedent("""\
    v1 := authorized.Group("/api/v1")
    datasets := v1.Group("/datasets")
    datasets.GET("/:dataset_id/documents/:document_id/chunks", r.chunkHandler.ListChunks)
    datasets.POST("/:dataset_id/search", r.datasetsHandler.SearchDataset)
    """)
    facts = _extract_one_go_file(source, "router.go")
    assert len(facts) == 2

    chunks = [f for f in facts if "chunks" in f.original_path]
    assert len(chunks) == 1
    c = chunks[0]
    assert c.method == "GET"
    assert c.normalized_path == "/api/v1/datasets/{dataset_id}/documents/{document_id}/chunks"
    assert c.handler_symbol == "r.chunkHandler.ListChunks"
    assert c.runtime == "go"
    assert not c.dynamic

    search = [f for f in facts if "search" in f.original_path]
    assert len(search) == 1
    s = search[0]
    assert s.method == "POST"
    assert s.normalized_path == "/api/v1/datasets/{dataset_id}/search"
    assert s.handler_symbol == "r.datasetsHandler.SearchDataset"


# ---------------------------------------------------------------------------
# Direct engine routes
# ---------------------------------------------------------------------------

def test_direct_engine_route():
    source = textwrap.dedent("""\
    engine.GET("/health", r.systemHandler.Health)
    engine.GET("/v1/system/configs", r.systemHandler.GetConfigs)
    """)
    facts = _extract_one_go_file(source, "router.go")
    assert len(facts) == 2
    paths = {f.normalized_path for f in facts}
    assert "/health" in paths
    assert "/v1/system/configs" in paths


# ---------------------------------------------------------------------------
# Gin wildcard path params
# ---------------------------------------------------------------------------

def test_gin_wildcard_params():
    source = textwrap.dedent("""\
    v1 := authorized.Group("/api/v1")
    v1.GET("/documents/artifact/:filename", r.documentHandler.GetDocumentArtifact)
    """)
    facts = _extract_one_go_file(source, "router.go")
    assert len(facts) == 1
    assert facts[0].normalized_path == "/api/v1/documents/artifact/{filename}"
    assert facts[0].original_path == "/api/v1/documents/artifact/:filename"


# ---------------------------------------------------------------------------
# Multiple nested groups + multiple methods
# ---------------------------------------------------------------------------

def test_multiple_groups_and_methods():
    source = textwrap.dedent("""\
    authorized := engine.Group("")
    v1 := authorized.Group("/api/v1")
    chats := v1.Group("/chats")
    chats.GET("", r.chatHandler.ListChats)
    chats.POST("", r.chatHandler.Create)
    chats.DELETE("/:chat_id", r.chatHandler.DeleteChat)
    chats.GET("/:chat_id/sessions", r.chatSessionHandler.ListChatSessions)
    chats.POST("/:chat_id/sessions", r.chatSessionHandler.CreateSession)
    """)
    facts = _extract_one_go_file(source, "router.go")
    assert len(facts) == 5
    methods_paths = {(f.method, f.normalized_path) for f in facts}
    assert ("GET", "/api/v1/chats") in methods_paths
    assert ("POST", "/api/v1/chats") in methods_paths
    assert ("DELETE", "/api/v1/chats/{chat_id}") in methods_paths
    assert ("GET", "/api/v1/chats/{chat_id}/sessions") in methods_paths
    assert ("POST", "/api/v1/chats/{chat_id}/sessions") in methods_paths


# ---------------------------------------------------------------------------
# Debug direct routes
# ---------------------------------------------------------------------------

def test_x_api_source_middleware_not_extracted():
    """engine.Use() calls are not route registrations."""
    source = textwrap.dedent("""\
    engine.Use(func(c *gin.Context) {
        c.Header("X-API-Source", "go")
        c.Next()
    })
    engine.GET("/health", r.systemHandler.Health)
    """)
    facts = _extract_one_go_file(source, "router.go")
    assert len(facts) == 1
    assert facts[0].handler_symbol == "r.systemHandler.Health"


# ---------------------------------------------------------------------------
# Diagnostic: unresolvable method
# ---------------------------------------------------------------------------

def test_dynamic_unresolvable_method():
    """If a registration uses an unrecognized token as method, report diagnostic."""
    source = textwrap.dedent("""\
    v1 := authorized.Group("/api/v1")
    v1.UNKNOWN("/mystery", handler.Foo)
    """)
    facts = _extract_one_go_file(source, "router.go")
    # The regex matches `.UNKNOWN("path", handler)`, but UNKNOWN is not in HTTP_METHODS
    dynamic_facts = [f for f in facts if f.dynamic]
    assert len(dynamic_facts) >= 1
    for f in dynamic_facts:
        assert f.diagnostic is not None
        assert "UNKNOWN" in f.diagnostic


# ---------------------------------------------------------------------------
# Agent webhook dynamic methods (EE router pattern)
# ---------------------------------------------------------------------------

def test_agent_webhook_pattern():
    """Agent webhook methods may be registered dynamically; exercise handler detection."""
    source = textwrap.dedent("""\
    v1 := authorized.Group("/api/v1")
    v1.POST("/agents/:agent_id/webhook", r.agentHandler.Webhook)
    """)
    facts = _extract_one_go_file(source, "router.go")
    assert len(facts) == 1
    assert facts[0].method == "POST"
    assert facts[0].normalized_path == "/api/v1/agents/{agent_id}/webhook"
    assert facts[0].handler_symbol == "r.agentHandler.Webhook"
    assert not facts[0].dynamic


# ---------------------------------------------------------------------------
# Empty / no routes
# ---------------------------------------------------------------------------

def test_empty_file():
    source = "package router\n"
    facts = _extract_one_go_file(source, "empty.go")
    assert facts == []


def test_no_routes():
    source = textwrap.dedent("""\
    package router
    import "github.com/gin-gonic/gin"
    type Router struct {}
    """)
    facts = _extract_one_go_file(source, "struct_only.go")
    assert facts == []


# ---------------------------------------------------------------------------
# JSON response payloads (for completeness — not extracted as routes)
# ---------------------------------------------------------------------------

def test_json_endpoint():
    """Ensure we capture a typical JSON endpoint."""
    source = textwrap.dedent("""\
    v1 := authorized.Group("/api/v1")
    v1.POST("/chat/completions", r.chatSessionHandler.ChatCompletions)
    """)
    facts = _extract_one_go_file(source, "chat.go")
    assert len(facts) == 1
    f = facts[0]
    assert f.method == "POST"
    assert f.normalized_path == "/api/v1/chat/completions"
