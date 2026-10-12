import sys
import types
from unittest.mock import MagicMock, mock_open, patch

import pytest

from app.tasks.worker import generate_voice_task


def test_generate_voice_task_success(monkeypatch):
    class FakeGTTS:
        def __init__(self, text, lang, slow):
            self.text = text

        def write_to_fp(self, fp):
            fp.write(b"audio-bytes")

    monkeypatch.setitem(sys.modules, "gtts", types.SimpleNamespace(gTTS=FakeGTTS))

    with patch("builtins.open", mock_open()) as mocked_open:
        result = generate_voice_task.run("hello world", "job-1")

    assert result["status"] == "done"
    assert result["job_id"] == "job-1"
    mocked_open.assert_called_once_with("/tmp/audio_job-1.mp3", "wb")


def test_generate_voice_task_failure_retries(monkeypatch):
    class BrokenGTTS:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("tts failed")

    monkeypatch.setitem(sys.modules, "gtts", types.SimpleNamespace(gTTS=BrokenGTTS))
    retry_exc = RuntimeError("retrying")
    retry_mock = MagicMock(side_effect=retry_exc)
    monkeypatch.setattr(generate_voice_task, "retry", retry_mock)

    with pytest.raises(RuntimeError, match="retrying"):
        generate_voice_task.run("hello world", "job-2")

    retry_mock.assert_called_once()
