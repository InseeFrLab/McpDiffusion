"""Unit tests for mcpdiffusion.services.feedback."""

from __future__ import annotations

from mcpdiffusion.models.feedback import SendFeedbackInput
from mcpdiffusion.services.feedback import _ensure_feedback_file, send_feedback


class TestEnsureFeedbackFile:
    def test_creates_file_if_missing(self, tmp_path, monkeypatch):
        feedback_dir = tmp_path / "feedback"
        feedback_file = feedback_dir / "feedback.md"
        monkeypatch.setattr("mcpdiffusion.services.feedback._FEEDBACK_DIR", feedback_dir)
        monkeypatch.setattr("mcpdiffusion.services.feedback._FEEDBACK_FILE", feedback_file)

        result = _ensure_feedback_file()

        assert result == feedback_file
        assert feedback_file.exists()
        content = feedback_file.read_text(encoding="utf-8")
        assert "# Feedback Log" in content

    def test_does_not_overwrite_existing_file(self, tmp_path, monkeypatch):
        feedback_dir = tmp_path / "feedback"
        feedback_dir.mkdir()
        feedback_file = feedback_dir / "feedback.md"
        feedback_file.write_text("existing content", encoding="utf-8")
        monkeypatch.setattr("mcpdiffusion.services.feedback._FEEDBACK_DIR", feedback_dir)
        monkeypatch.setattr("mcpdiffusion.services.feedback._FEEDBACK_FILE", feedback_file)

        _ensure_feedback_file()

        assert feedback_file.read_text(encoding="utf-8") == "existing content"


class TestSendFeedback:
    async def test_returns_success(self, tmp_path, monkeypatch):
        feedback_dir = tmp_path / "feedback"
        feedback_file = feedback_dir / "feedback.md"
        monkeypatch.setattr("mcpdiffusion.services.feedback._FEEDBACK_DIR", feedback_dir)
        monkeypatch.setattr("mcpdiffusion.services.feedback._FEEDBACK_FILE", feedback_file)

        params = SendFeedbackInput(username="alice", feedback="Great tool!")
        result = await send_feedback(params)

        assert result.status == "success"
        assert result.message == "Feedback recorded successfully."
        assert result.timestamp

    async def test_appends_entry_to_file(self, tmp_path, monkeypatch):
        feedback_dir = tmp_path / "feedback"
        feedback_file = feedback_dir / "feedback.md"
        monkeypatch.setattr("mcpdiffusion.services.feedback._FEEDBACK_DIR", feedback_dir)
        monkeypatch.setattr("mcpdiffusion.services.feedback._FEEDBACK_FILE", feedback_file)

        await send_feedback(SendFeedbackInput(username="alice", feedback="First"))

        content = feedback_file.read_text(encoding="utf-8")
        assert "alice" in content
        assert "First" in content

    async def test_multiple_entries_appended(self, tmp_path, monkeypatch):
        feedback_dir = tmp_path / "feedback"
        feedback_file = feedback_dir / "feedback.md"
        monkeypatch.setattr("mcpdiffusion.services.feedback._FEEDBACK_DIR", feedback_dir)
        monkeypatch.setattr("mcpdiffusion.services.feedback._FEEDBACK_FILE", feedback_file)

        await send_feedback(SendFeedbackInput(username="alice", feedback="First"))
        await send_feedback(SendFeedbackInput(username="bob", feedback="Second"))

        content = feedback_file.read_text(encoding="utf-8")
        assert "alice" in content
        assert "bob" in content
        assert "First" in content
        assert "Second" in content
