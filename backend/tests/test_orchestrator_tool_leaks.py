import importlib
import sys
import types
import unittest
from unittest.mock import patch

openai_module = types.ModuleType("openai")
openai_module.OpenAI = object
sys.modules.setdefault("openai", openai_module)

orchestrator = importlib.import_module("backend.app.services.orchestrator")


class _Registry:
    def get_contract(self, _name):
        return {}


class TestToolCallLeakHandling(unittest.TestCase):
    def _leaked_tool_plan(self):
        return (
            '{"tool": "get_user_comprehensive_profile", "args": {"user_id": 2, "scope": "basic"}} '
            '{"tool": "search_knowledge_repository", "args": {"source": "internal_kb", '
            '"query_type": "tech_evolution", "keywords": ["中国船舶发展史", "造船技术演进", "工业里程碑"]}} '
            '{"tool": "search_knowledge_repository", "args": {"source": "internal_kb", '
            '"query_type": "spirit_genealogy", "keywords": ["船舶工业精神", "自力更生"]}}'
        )

    def test_parses_adjacent_json_tool_calls_from_model_content(self):
        calls = orchestrator._parse_json_tool_calls(self._leaked_tool_plan())

        self.assertEqual(
            [call["name"] for call in calls],
            [
                "get_user_comprehensive_profile",
                "search_knowledge_repository",
                "search_knowledge_repository",
            ],
        )
        self.assertEqual(calls[0]["args"]["user_id"], 2)

    def test_plan_with_tools_consumes_adjacent_json_tool_calls_without_returning_them_as_content(self):
        with (
            patch.object(
                orchestrator,
                "call_ai_model_with_tools",
                return_value=(self._leaked_tool_plan(), [], []),
            ),
            patch.object(orchestrator, "write_agent_log"),
        ):
            assistant_content, tool_calls, _raw_tool_calls, used_json_fallback, _plan = orchestrator.plan_with_tools(
                [{"role": "user", "content": "介绍一下中国船舶的发展史"}],
                [{"type": "function", "function": {"name": "search_knowledge_repository"}}],
                "test-model",
                "test-key",
                "https://example.invalid/v1",
                _Registry(),
                "exploration",
                2,
                10,
            )

        self.assertEqual(assistant_content, "")
        self.assertTrue(used_json_fallback)
        self.assertEqual(
            [call["name"] for call in tool_calls],
            [
                "get_user_comprehensive_profile",
                "search_knowledge_repository",
                "search_knowledge_repository",
            ],
        )

    def test_synthesis_returns_fallback_when_retry_still_outputs_tool_call_format(self):
        leaked_response = self._leaked_tool_plan()

        with (
            patch.object(orchestrator, "call_ai_model", side_effect=[leaked_response, leaked_response]) as call_model,
            patch.object(orchestrator, "write_agent_log"),
        ):
            final_text = orchestrator.synthesize_with_tools(
                [{"role": "user", "content": "介绍一下中国船舶的发展史"}],
                "",
                [
                    {
                        "id": "call-1",
                        "name": "search_knowledge_repository",
                        "args": {"source": "internal_kb", "query_type": "tech_evolution", "keywords": ["中国船舶"]},
                    }
                ],
                [
                    {
                        "id": "call-1",
                        "name": "search_knowledge_repository",
                        "result": {"status": "ok", "results": []},
                    }
                ],
                "test-model",
                "test-key",
                "https://example.invalid/v1",
                "exploration",
            )

        self.assertEqual(final_text, orchestrator.FALLBACK_MESSAGE)
        self.assertEqual(call_model.call_count, 2)

    def test_stream_without_tools_retries_when_model_streams_tool_call_format(self):
        leaked_response = '{"tool": "get_user_comprehensive_profile", "args": {"user_id": 2, "scope": "basic"}}'

        with (
            patch.object(orchestrator, "call_ai_model_stream", return_value=[leaked_response]) as stream_model,
            patch.object(orchestrator, "call_ai_model", return_value="这是面向用户的最终回答。") as retry_model,
            patch.object(orchestrator, "write_agent_log"),
        ):
            chunks = list(
                orchestrator.stream_without_tools(
                    "test-model",
                    [{"role": "user", "content": "如何将新时代党建教育融入到船舶中"}],
                    api_key="test-key",
                    base_url="https://example.invalid/v1",
                )
            )

        self.assertEqual(chunks, ["这是面向用户的最终回答。"])
        stream_model.assert_called_once()
        retry_model.assert_called_once()

    def test_stream_synthesize_with_tools_yields_model_chunks(self):
        with (
            patch.object(orchestrator, "call_ai_model_stream", return_value=["第一段", "第二段"]) as stream_model,
            patch.object(orchestrator, "call_ai_model") as retry_model,
            patch.object(orchestrator, "write_agent_log"),
        ):
            chunks = list(
                orchestrator.stream_synthesize_with_tools(
                    [{"role": "user", "content": "帮我规划一下2027考研的复习规划"}],
                    "",
                    [
                        {
                            "id": "call-1",
                            "name": "execute_strategy_engine",
                            "args": {"action": "generate_plan", "context_data": {"request": "2027考研"}},
                        }
                    ],
                    [
                        {
                            "id": "call-1",
                            "name": "execute_strategy_engine",
                            "result": {"status": "ok", "plan": []},
                        }
                    ],
                    "test-model",
                    "test-key",
                    "https://example.invalid/v1",
                    "task",
                )
            )

        self.assertEqual(chunks, ["第一段", "第二段"])
        stream_model.assert_called_once()
        retry_model.assert_not_called()

    def test_stream_synthesize_with_tools_retries_before_emitting_leaked_tool_call(self):
        leaked_chunks = ['{"tool": "get_user_comprehensive_profile"', ', "args": {"user_id": 2}}']

        with (
            patch.object(orchestrator, "call_ai_model_stream", return_value=leaked_chunks) as stream_model,
            patch.object(orchestrator, "call_ai_model", return_value="这是重新生成的用户回答。") as retry_model,
            patch.object(orchestrator, "write_agent_log"),
        ):
            chunks = list(
                orchestrator.stream_synthesize_with_tools(
                    [{"role": "user", "content": "帮我规划一下2027考研的复习规划"}],
                    "",
                    [
                        {
                            "id": "call-1",
                            "name": "execute_strategy_engine",
                            "args": {"action": "generate_plan", "context_data": {"request": "2027考研"}},
                        }
                    ],
                    [
                        {
                            "id": "call-1",
                            "name": "execute_strategy_engine",
                            "result": {"status": "ok", "plan": []},
                        }
                    ],
                    "test-model",
                    "test-key",
                    "https://example.invalid/v1",
                    "task",
                )
            )

        self.assertEqual(chunks, ["这是重新生成的用户回答。"])
        stream_model.assert_called_once()
        retry_model.assert_called_once()


if __name__ == "__main__":
    unittest.main()
