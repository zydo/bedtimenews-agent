from datetime import datetime

import pytest
from src import scheduler


class _ImmediateSchedule:
    def get_next(self, _return_type):
        return datetime.now().astimezone()


def _disable_scheduler_side_effects(monkeypatch):
    monkeypatch.setattr(scheduler.signal, "signal", lambda *_args: None)
    monkeypatch.setattr(scheduler, "_configure_file_logging", lambda: None)


def test_scheduler_runs_pipeline_when_schedule_is_due(monkeypatch):
    _disable_scheduler_side_effects(monkeypatch)
    monkeypatch.setattr(
        scheduler,
        "croniter",
        lambda _expression, _start_time: _ImmediateSchedule(),
    )
    calls = []

    def run_pipeline():
        calls.append("run")
        scheduler.shutdown_requested = True

    scheduler.run_scheduler(run_pipeline)

    assert calls == ["run"]


def test_scheduler_rejects_invalid_cron_expression(monkeypatch):
    _disable_scheduler_side_effects(monkeypatch)

    def invalid_schedule(_expression, _start_time):
        raise ValueError("invalid schedule")

    monkeypatch.setattr(scheduler, "croniter", invalid_schedule)

    with pytest.raises(SystemExit) as exc_info:
        scheduler.run_scheduler(lambda: None)

    assert exc_info.value.code == 1
