"""Coverage-focused tests for the MoBI_View.main entry module."""

from __future__ import annotations

import runpy
import sys
from types import SimpleNamespace
from typing import cast

import pytest


class DummyQApp:
    """Minimal QApplication stand-in that avoids launching a real UI."""

    def __init__(self, *args: object) -> None:
        """Ignore constructor arguments."""

    def exec(self) -> int:
        """Return immediately instead of running a GUI event loop."""
        return 0


class DummyView:
    """View stub that records whether ``show`` was invoked."""

    def __init__(self, **kwargs: object) -> None:
        """Store initialization kwargs for inspection."""
        self.kwargs = kwargs
        self.show_called = False

    def show(self) -> None:  # pragma: no cover - invoked by test
        """Record that the view was shown."""
        self.show_called = True


def test_main_module_runs_under___main__(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running the module via runpy should execute the script guard."""
    monkeypatch.setattr("PyQt6.QtWidgets.QApplication", DummyQApp)
    monkeypatch.setattr(
        "MoBI_View.presenters.main_app_presenter.MainAppPresenter",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    captured_view: dict[str, DummyView] = {}

    def make_view(**kwargs: object) -> DummyView:
        view = DummyView(**kwargs)
        captured_view["view"] = view
        return view

    monkeypatch.setattr("MoBI_View.views.main_app_view.MainAppView", make_view)
    monkeypatch.setattr("pylsl.resolve_streams", lambda: [])
    monkeypatch.setattr("sys.exit", lambda code: None)
    monkeypatch.delitem(sys.modules, "MoBI_View.main", raising=False)

    runpy.run_module("MoBI_View.main", run_name="__main__")
    assert "view" in captured_view
    assert captured_view["view"].show_called


def test_main_function_invokes_components(monkeypatch: pytest.MonkeyPatch) -> None:
    """Direct invocation of main() should wire presenters and exit cleanly."""
    from MoBI_View import main as main_module

    created: dict[str, object] = {}

    class RecordingApp(DummyQApp):
        def exec(self) -> int:
            created["exec"] = True
            return 0

    class RecordingInlet:
        def __init__(self, info: SimpleNamespace) -> None:
            name = info.name()
            if name == "Broken":
                raise RuntimeError("stream issue")
            self.stream_name = name
            self.stream_type = info.type()

    def fake_resolve() -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                name=lambda: "Alpha",
                type=lambda: "EEG",
            ),
            SimpleNamespace(
                name=lambda: "Broken",
                type=lambda: "Aux",
            ),
        ]

    class RecordingView:
        def __init__(self, stream_info: dict[str, str]) -> None:
            created["stream_info"] = stream_info
            self.show_called = False

        def show(self) -> None:
            self.show_called = True
            created["show"] = True

    def fake_presenter(view: RecordingView, data_inlets: list[RecordingInlet]) -> None:
        created["presenter"] = (view, data_inlets)

    monkeypatch.setattr(main_module, "QApplication", RecordingApp)
    monkeypatch.setattr(main_module, "resolve_streams", fake_resolve)
    monkeypatch.setattr(main_module, "DataInlet", RecordingInlet)
    monkeypatch.setattr(main_module, "MainAppView", RecordingView)
    monkeypatch.setattr(main_module, "MainAppPresenter", fake_presenter)
    monkeypatch.setattr(
        main_module.sys,
        "exit",
        lambda code: created.setdefault("exit", code),
    )
    main_module.main()
    assert created["exec"] is True
    assert created["show"] is True
    view, inlets = cast(
        tuple[RecordingView, list[RecordingInlet]],
        created["presenter"],
    )
    assert isinstance(view, RecordingView)
    assert len(inlets) == 1
    assert created["stream_info"] == {"Alpha": "EEG"}
    assert created["exit"] == 0
