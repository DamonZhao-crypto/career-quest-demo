"""Protect answers from prompt contamination and repeated decoding loops."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from speech import repetition_detected, transcribe_recording, vocabulary_hints


def segment(text):
    return SimpleNamespace(text=text, start=0, end=12, avg_logprob=-0.3, no_speech_prob=0.1)


class SpeechQualityTests(unittest.TestCase):
    def test_realistic_repetition_and_natural_repeated_terms(self):
        bad = "针对项目编程。" + "\ufffdFigma：开发工程师" * 12 + "然后做一个项目。"
        self.assertTrue(repetition_detected(bad))
        self.assertFalse(repetition_detected("我用 Python 写接口，用 Python 处理数据，最后部署 Python 服务。"))
        self.assertFalse(repetition_detected("我，我先分析需求，然后修改了两次，两次的反馈都不同。"))

    def test_clean_answer_is_not_rewritten_and_audio_exists_during_iteration(self):
        expected = "我没有负责后端，负责的是交互设计。"
        observed = []
        def decode(path, **options):
            observed.append(options)
            def segments():
                self.assertTrue(Path(path).is_file())
                yield segment(expected)
            return segments(), SimpleNamespace()
        model = Mock()
        model.transcribe.side_effect = decode
        result = transcribe_recording(b"fake recording for mocked decoder", model)
        self.assertEqual(result["text"], expected)
        self.assertFalse(result["retried"])
        self.assertEqual(result["warnings"], [])
        self.assertEqual(model.transcribe.call_count, 1)
        self.assertIsNone(observed[0]["initial_prompt"])
        self.assertIsNone(observed[0]["hotwords"])
        self.assertEqual(observed[0]["no_repeat_ngram_size"], 0)

    def test_suspicious_answer_retries_without_hints_and_keeps_original(self):
        original = "这是我的项目。" + "\ufffdFigma：开发工程师" * 12
        correct = "我负责需求分析和页面设计，项目还没有上线。"
        model = Mock()
        model.transcribe.side_effect = [(iter([segment(original)]), None), (iter([segment(correct)]), None)]
        result = transcribe_recording(b"mock recording", model, "Figma")
        self.assertEqual(result["text"], correct)
        self.assertEqual(result["original_text"], original)
        self.assertTrue(result["retried"])
        self.assertTrue(result["warnings"])
        self.assertIsNone(model.transcribe.call_args.kwargs["hotwords"])
        self.assertIsNone(model.transcribe.call_args.kwargs["initial_prompt"])
        self.assertEqual(model.transcribe.call_count, 2)

    def test_retry_empty_or_still_bad_is_not_silently_deleted(self):
        original = "我没有上线这个项目。" + "Figma：开发工程师" * 12
        for retry_text in ("", original):
            model = Mock()
            model.transcribe.side_effect = [(iter([segment(original)]), None), (iter([segment(retry_text)]), None)]
            result = transcribe_recording(b"mock recording", model)
            self.assertEqual(result["text"], original)
            self.assertEqual(len(result["warnings"]), 2)
            self.assertEqual(model.transcribe.call_count, 2)

    def test_vocabulary_is_short_deduplicated_and_explicit(self):
        self.assertEqual(vocabulary_hints(), "")
        self.assertEqual(vocabulary_hints("Python，Python、FastAPI"), "Python，FastAPI")
        self.assertLessEqual(len(vocabulary_hints("x" * 500)), 120)
        self.assertEqual(len(vocabulary_hints("、".join(str(i) for i in range(30))).split("，")), 8)


if __name__ == "__main__":
    unittest.main()
