from __future__ import annotations

from tradingbot.app.preflight import ReadinessStatus, check_log_paths
from tests.conftest import make_bot_config


def test_log_path_readiness_passes_for_creatable_paths(tmp_path):
    config = make_bot_config(
        decision_log_path=str(tmp_path / "logs" / "decisions.csv"),
        fill_log_path=str(tmp_path / "logs" / "fills.csv"),
        daily_snapshot_path=str(tmp_path / "logs" / "daily_snapshot.csv"),
    )

    result = check_log_paths(config)

    assert result.status == ReadinessStatus.PASS
    assert (tmp_path / "logs").exists()


def test_log_path_readiness_fails_when_parent_is_file(tmp_path):
    parent_file = tmp_path / "not_a_directory"
    parent_file.write_text("blocking parent", encoding="utf-8")
    config = make_bot_config(
        decision_log_path=str(parent_file / "decisions.csv"),
        fill_log_path=str(tmp_path / "logs" / "fills.csv"),
        daily_snapshot_path=str(tmp_path / "logs" / "daily_snapshot.csv"),
    )

    result = check_log_paths(config)

    assert result.status == ReadinessStatus.FAIL
    assert "not writable" in result.message
