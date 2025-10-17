"""Unit tests for the web stream registry."""

from __future__ import annotations

from typing import cast

import numpy as np
import pytest

from MoBI_View.core.data_inlet import DataInlet
from MoBI_View.web.stream_buffers import Registry


class FakeInlet:
    """Lightweight substitute mimicking ``DataInlet`` for unit tests."""

    def __init__(self, name: str = "Test", channel_count: int = 2) -> None:
        """Prepare a stub inlet with a fixed-size circular buffer."""
        self.stream_name = name
        self.stream_type = "EEG"
        self.channel_count = channel_count
        self.sample_rate = 10.0
        self.channel_info = {"labels": [f"Ch{i}" for i in range(channel_count)]}
        self.buffers = np.zeros((8, channel_count), dtype=float)
        self.ptr = 0

    def inject(self, sample: np.ndarray) -> None:
        """Append a sample to the stub buffer, advancing the pointer."""
        self.buffers[self.ptr % self.buffers.shape[0]] = sample
        self.ptr += 1


def test_registry_add_get_remove() -> None:
    """Registry should support add/get/remove operations for inlets."""
    registry = Registry()
    inlet = FakeInlet(name="Alpha")
    typed_inlet = cast(DataInlet, inlet)
    registry.add(typed_inlet)
    assert registry.get("Alpha") is typed_inlet
    assert registry.all() == [typed_inlet]
    registry.remove("Alpha")
    assert registry.all() == []


def test_registry_get_missing_raises_key_error() -> None:
    """Requesting an unknown stream should raise KeyError with context."""
    registry = Registry()
    with pytest.raises(KeyError, match="missing"):
        registry.get("missing")


def test_registry_remove_missing_raises_key_error() -> None:
    """Removing an unregistered stream should raise KeyError with context."""
    registry = Registry()
    with pytest.raises(KeyError, match="missing"):
        registry.remove("missing")
