"""Unit tests for the lightweight web entry point logic."""

from __future__ import annotations

import logging
from typing import Any, Callable, cast

import pytest

from MoBI_View.web import web_main


def test_main_invokes_schedule_and_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Main should stage the browser launch before running the server."""
    calls: list[str] = []
    monkeypatch.setattr(
        web_main, "schedule_browser_launch", lambda: calls.append("sched")
    )
    monkeypatch.setattr(web_main, "run_web", lambda: calls.append("run"))
    web_main.main()
    assert calls == ["sched", "run"]


def test_schedule_browser_launch_opens_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scheduling the browser launch should trigger a timer and open it."""
    created: dict[str, Any] = {}

    class FakeTimer:
        def __init__(self, delay: float, func: Callable[[], None]) -> None:
            created["delay"] = delay
            created["func"] = func
            self.daemon = False

        def start(self) -> None:
            created["daemon"] = self.daemon
            created["started"] = True
            func_to_run = cast(Callable[[], None], created["func"])
            func_to_run()

    monkeypatch.setattr(web_main.threading, "Timer", FakeTimer)
    opened: dict[str, Any] = {}

    def fake_open(url: str, new: int, autoraise: bool) -> None:
        opened["url"] = url
        opened["new"] = new
        opened["autoraise"] = autoraise

    monkeypatch.setattr(web_main.webbrowser, "open", fake_open)
    monkeypatch.setattr(web_main.Config, "HTTP_HOST", "0.0.0.0")
    monkeypatch.setattr(web_main.Config, "HTTP_PORT", 9000)
    web_main.schedule_browser_launch()
    assert created["delay"] == 0.5
    assert created["daemon"] is True
    assert created["started"] is True
    assert opened["url"] == "http://localhost:9000"
    assert opened["new"] == 2
    assert opened["autoraise"] is True


def test_schedule_browser_launch_logs_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Failures to open the browser should be logged and swallowed."""

    class FakeTimer:
        def __init__(self, delay: float, func: Callable[[], None]) -> None:
            self.func = func
            self.daemon = False

        def start(self) -> None:
            self.daemon = True
            self.func()

    monkeypatch.setattr(web_main.threading, "Timer", FakeTimer)

    def fake_open(url: str, new: int, autoraise: bool) -> None:
        raise web_main.webbrowser.Error("boom")

    monkeypatch.setattr(web_main.webbrowser, "open", fake_open)
    monkeypatch.setattr(web_main.Config, "HTTP_HOST", "example.com")
    monkeypatch.setattr(web_main.Config, "HTTP_PORT", 8001)
    caplog.set_level(logging.WARNING, logger=web_main.__name__)
    web_main.schedule_browser_launch()
    assert any("Browser launch failed" in message for message in caplog.messages)
