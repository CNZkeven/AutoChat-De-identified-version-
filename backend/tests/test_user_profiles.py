import importlib
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

openai_module = types.ModuleType("openai")
openai_module.OpenAI = object
sys.modules.setdefault("openai", openai_module)

user_profiles = importlib.import_module("backend.app.services.user_profiles")


class _Query:
    def filter(self, *_args):
        return self

    def first(self):
        return None


class _Session:
    def __init__(self):
        self.added = []
        self.committed = False

    def query(self, _model):
        return _Query()

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.committed = True

    def refresh(self, _item):
        return None


class TestGeneratePublicProfileFallback(unittest.TestCase):
    def _user(self):
        return SimpleNamespace(
            id=1,
            username="20260001",
            full_name=None,
            major=None,
            grade=None,
            gender=None,
        )

    def _snapshot(self, memory_summaries, conversation_history=None):
        snapshot = user_profiles.ProfileInputSnapshot(
            academic_updated_at=None,
            memory_updated_at=None,
            course_count=0,
            courses=[],
            memory_summaries=memory_summaries,
        )
        snapshot.conversation_history = conversation_history or []
        return snapshot

    def test_generates_from_dialogue_history_when_student_database_has_no_courses(self):
        session = _Session()
        snapshot = self._snapshot(
            [
                {
                    "agent": "task",
                    "summary": "学生经常询问项目拆解和时间安排，偏好清晰步骤。",
                    "updated_at": None,
                }
            ]
        )

        with (
            patch.object(user_profiles, "_build_profile_snapshot", return_value=snapshot),
            patch.object(user_profiles, "_generate_profile_content", return_value="画像正文") as generate_content,
        ):
            profile = user_profiles.generate_public_profile(session, self._user())

        self.assertEqual(profile.content, "未连接学生数据库，仅根据对话记录生成\n\n画像正文")
        self.assertTrue(session.committed)
        generate_content.assert_called_once()

    def test_generates_from_raw_dialogue_history_when_memory_summary_is_empty(self):
        session = _Session()
        snapshot = self._snapshot(
            [],
            [
                {
                    "agent": "task",
                    "role": "user",
                    "content": "我总是拖到最后才开始写作业，想要一个更清晰的计划。",
                    "created_at": None,
                }
            ],
        )

        with (
            patch.object(user_profiles, "_build_profile_snapshot", return_value=snapshot),
            patch.object(user_profiles, "_generate_profile_content", return_value="画像正文") as generate_content,
        ):
            profile = user_profiles.generate_public_profile(session, self._user())

        self.assertEqual(profile.content, "未连接学生数据库，仅根据对话记录生成\n\n画像正文")
        self.assertTrue(session.committed)
        generate_content.assert_called_once()

    def test_returns_no_data_message_when_student_database_and_dialogue_history_are_empty(self):
        session = _Session()

        with (
            patch.object(user_profiles, "_build_profile_snapshot", return_value=self._snapshot([])),
            patch.object(user_profiles, "_generate_profile_content") as generate_content,
        ):
            profile = user_profiles.generate_public_profile(session, self._user())

        self.assertEqual(profile.content, "无对话记录和学生数据库，无法生成")
        self.assertTrue(session.committed)
        generate_content.assert_not_called()


if __name__ == "__main__":
    unittest.main()
