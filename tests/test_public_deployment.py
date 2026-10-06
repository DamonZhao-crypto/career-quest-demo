"""Offline deployment checks; no real API calls or model downloads."""

import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class PublicDeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="career-quest-check-")
        cls.old_cwd = Path.cwd()
        cls.environment = patch.dict(os.environ, {
            "CAREER_QUEST_DATA_DIR": cls.temporary.name,
            "CAREER_QUEST_PUBLIC": "true",
        })
        cls.environment.start()
        # Ignore any administrator environment credentials during offline checks.
        cls.credential_environment = patch.dict(os.environ)
        cls.credential_environment.start()
        for name in ("PROVIDER", "API_KEY", "BASE_URL", "MODEL", "VOICE_API_KEY"):
            os.environ.pop(f"CAREER_QUEST_{name}", None)
        os.chdir(ROOT)
        import agents
        import hosting
        import storage
        cls.agents, cls.hosting, cls.storage = agents, hosting, storage
        cls.storage.init_db()

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.old_cwd)
        cls.credential_environment.stop()
        cls.environment.stop()
        cls.temporary.cleanup()

    def app(self, configured=True):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT / "cloud_app.py"), default_timeout=15)
        app.secrets = {"hosting": {"whisper_model": "base", "daily_api_limit": 200}}
        if configured:
            app.secrets["career_quest"] = {
                "provider": "bailian", "api_key": "offline-test-key",
                "model": "qwen-plus", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            }
        return app

    def test_missing_credentials_do_not_offer_visitor_key_input(self):
        app = self.app(configured=False).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertFalse(any("API" in widget.label for widget in app.text_input))
        self.assertFalse(any(button.label == "开始挑战" for button in app.button))

    def test_homepage_has_private_session_and_light_model(self):
        app = self.app().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertFalse(any("API" in widget.label or "存档编号" in widget.label for widget in app.text_input))
        self.assertEqual(len(app.session_state["public_visitor_id"]), 64)
        self.assertEqual(app.selectbox(key="speech_mode").value, "base · 速度优先")
        self.assertIn("small · 清晰优先（推荐）", app.selectbox(key="speech_mode").options)

    def test_two_visitors_cannot_see_each_others_history(self):
        alice, bob = self.app().run(), self.app().run()
        self.assertFalse(alice.exception)
        self.assertFalse(bob.exception)
        alice_id, bob_id = alice.session_state["public_visitor_id"], bob.session_state["public_visitor_id"]
        self.assertNotEqual(alice_id, bob_id)
        self.storage.save_result(alice_id, "平面设计师", "HR 面", 75, True,
                                 {"strength": "测试优势", "gap": "测试不足", "training_task": "测试训练"},
                                 result_key=alice_id)
        self.assertEqual(len(self.storage.get_history(alice_id)), 1)
        bob.radio(key="workspace_page").set_value("成长记录").run()
        self.assertFalse(bob.exception)
        self.assertFalse(self.storage.get_history(bob_id))
        self.assertFalse(any("存档编号" in widget.label for widget in bob.text_input))
        self.assertFalse(bob.dataframe)
        self.storage.delete_history(bob_id)
        self.assertEqual(len(self.storage.get_history(alice_id)), 1)

    def test_stage_flow_with_mocked_model(self):
        feedback = {"score": 80, "strength": "回答具体", "gap": "可以补充结果", "training_task": "再讲一个例子"}
        with patch.object(self.agents, "profile_agent", return_value={"summary": "测试画像", "skills": [], "gaps": []}), \
             patch.object(self.agents, "question_agent", return_value="请讲一次你做过的设计练习。"), \
             patch.object(self.agents, "evaluate_agent", return_value=feedback):
            app = self.app().run()
            app.text_input(key="setup_job").set_value("平面设计师")
            next(button for button in app.button if button.label == "开始挑战").click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            for _ in range(2):
                next(widget for widget in app.text_area if widget.label == "确认回答内容").set_value("我在课程中设计海报，负责版式，修改三版。")
                next(button for button in app.button if button.label == "提交回答并评分").click().run()
                self.assertFalse(app.exception)
                self.assertFalse(app.error)
            self.assertTrue(app.session_state["game"]["stage_result"]["passed"])
            player_id = app.session_state["public_visitor_id"]
            self.assertEqual(app.session_state["game"]["player_id"], player_id)
            self.assertEqual(len(self.storage.get_history(player_id)), 1)
            next(button for button in app.button if button.label == "进入下一关").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["game"]["stage_index"], 1)

    def test_daily_limit_is_atomic_across_parallel_attempts(self):
        with tempfile.TemporaryDirectory(prefix="quest-budget-") as directory:
            with patch.dict(os.environ, {"CAREER_QUEST_DATA_DIR": directory, "CAREER_QUEST_DAILY_API_LIMIT": "5"}):
                def reserve(_):
                    try:
                        self.hosting._reserve_daily_request()
                        return True
                    except self.hosting.HostingError:
                        return False
                with ThreadPoolExecutor(max_workers=4) as pool:
                    results = list(pool.map(reserve, range(20)))
                self.assertEqual(sum(results), 5)
                with closing(sqlite3.connect(Path(directory) / "usage.db")) as connection:
                    self.assertEqual(connection.execute("SELECT calls FROM usage").fetchone()[0], 5)

    def test_speech_busy_and_exception_release(self):
        with self.hosting.speech_slot():
            with self.assertRaises(self.hosting.HostingError):
                with self.hosting.speech_slot():
                    self.fail("a second transcription must not run simultaneously")
        with self.assertRaises(RuntimeError):
            with self.hosting.speech_slot():
                raise RuntimeError("simulated transcription failure")
        with self.hosting.speech_slot():
            pass

    def test_public_client_disables_unbudgeted_automatic_retries(self):
        client = self.agents.make_client("阿里云百炼（免费额度）", "offline-test-key")
        self.assertEqual(client.max_retries, 0)
        client.close()


if __name__ == "__main__":
    unittest.main()
