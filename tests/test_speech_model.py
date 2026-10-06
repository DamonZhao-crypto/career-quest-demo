"""Check genuine failure boundaries and protect data in diagnostic logs."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import speech_model


class SpeechModelTests(unittest.TestCase):
    def test_model_download_error_is_distinct_from_startup_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("faster_whisper.utils.download_model", side_effect=TimeoutError("private download URL")):
                with self.assertLogs("career_quest.speech", "ERROR") as output:
                    with self.assertRaises(speech_model.SpeechServiceError) as context:
                        speech_model.load_cpu_model("base", directory)
                self.assertEqual(context.exception.code, "S03")
                self.assertNotIn("private download URL", " ".join(output.output))

    def test_existing_cache_loads_offline_and_reports_model_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "models--Systran--faster-whisper-base/snapshots/test"
            snapshot.mkdir(parents=True)
            (snapshot / "model.bin").write_bytes(b"placeholder")
            for name in ("config.json", "tokenizer.json"):
                (snapshot / name).write_text(json.dumps({}), encoding="utf-8")
            with patch("faster_whisper.WhisperModel", side_effect=RuntimeError("private internal path")), \
                 patch("faster_whisper.utils.download_model") as download:
                with self.assertLogs("career_quest.speech", "ERROR"):
                    with self.assertRaises(speech_model.SpeechServiceError) as context:
                        speech_model.load_cpu_model("base", directory)
                self.assertEqual(context.exception.code, "S04")
                download.assert_not_called()

    def test_log_never_records_raw_error_message(self):
        with self.assertLogs("career_quest.speech", "ERROR") as output:
            speech_model.report_speech_failure("audio-transcription", ValueError("secret_key recording transcript signed_url"))
        text = " ".join(output.output)
        self.assertIn("ValueError", text)
        for private in ("secret_key", "recording transcript", "signed_url"):
            self.assertNotIn(private, text)


if __name__ == "__main__":
    unittest.main()
