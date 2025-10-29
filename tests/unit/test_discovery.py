"""Unit tests for the discovery module."""

from typing import Callable
from unittest.mock import MagicMock

import pytest
from pylsl import StreamInfo
from pytest_mock import MockFixture

from MoBI_View.core import discovery
from MoBI_View.core.data_inlet import DataInlet


@pytest.fixture
def mock_stream_info_factory() -> Callable[..., MagicMock]:
    """Factory for creating mock StreamInfo objects."""

    def _factory(
        name: str = "TestStream",
        stream_type: str = "EEG",
        source_id: str = "test_source_123",
        channel_count: int = 3,
    ) -> MagicMock:
        info = MagicMock(spec=StreamInfo)
        info.name.return_value = name
        info.type.return_value = stream_type
        info.source_id.return_value = source_id
        info.channel_count.return_value = channel_count
        info.channel_format.return_value = 1  # float32
        info.get_channel_labels.return_value = [f"Ch{i}" for i in range(channel_count)]
        info.get_channel_types.return_value = ["EEG"] * channel_count
        info.get_channel_units.return_value = ["uV"] * channel_count
        return info

    return _factory


@pytest.fixture
def mock_data_inlet_factory() -> Callable[..., MagicMock]:
    """Factory for creating mock DataInlet objects."""

    def _factory(
        stream_name: str = "TestStream",
        stream_type: str = "EEG",
        source_id: str = "test_source_123",
    ) -> MagicMock:
        inlet = MagicMock(spec=DataInlet)
        inlet.stream_name = stream_name
        inlet.stream_type = stream_type
        inlet.source_id = source_id
        return inlet

    return _factory


def test_discover_and_create_inlets_finds_new_streams(
    mocker: MockFixture,
    mock_stream_info_factory: Callable[..., MagicMock],
) -> None:
    """discover_and_create_inlets should create DataInlets for discovered streams."""
    stream1 = mock_stream_info_factory(name="Stream1", source_id="source1")
    stream2 = mock_stream_info_factory(name="Stream2", source_id="source2")

    mocker.patch(
        "MoBI_View.core.discovery.resolve_streams",
        return_value=[stream1, stream2],
    )

    mock_inlet_class = mocker.patch("MoBI_View.core.discovery.DataInlet")
    mock_inlet1 = MagicMock()
    mock_inlet1.stream_name = "Stream1"
    mock_inlet1.stream_type = "EEG"
    mock_inlet1.source_id = "source1"
    mock_inlet1.channel_count = 3

    mock_inlet2 = MagicMock()
    mock_inlet2.stream_name = "Stream2"
    mock_inlet2.stream_type = "EEG"
    mock_inlet2.source_id = "source2"
    mock_inlet2.channel_count = 3

    mock_inlet_class.side_effect = [mock_inlet1, mock_inlet2]

    inlets, count = discovery.discover_and_create_inlets(wait_time=0.5)

    assert count == 2
    assert len(inlets) == 2
    assert mock_inlet_class.call_count == 2


def test_discover_and_create_inlets_with_no_streams(
    mocker: MockFixture,
) -> None:
    """discover_and_create_inlets should return empty list when no streams found."""
    mocker.patch(
        "MoBI_View.core.discovery.resolve_streams",
        return_value=[],
    )

    inlets, count = discovery.discover_and_create_inlets(wait_time=0.5)

    assert count == 0
    assert len(inlets) == 0


def test_discover_and_create_inlets_deduplicates_existing_streams(
    mocker: MockFixture,
    mock_stream_info_factory: Callable[..., MagicMock],
    mock_data_inlet_factory: Callable[..., MagicMock],
) -> None:
    """discover_and_create_inlets should skip streams that already exist."""
    existing_inlet = mock_data_inlet_factory(
        stream_name="ExistingStream",
        source_id="existing_source",
        stream_type="EEG",
    )

    existing_stream_info = mock_stream_info_factory(
        name="ExistingStream",
        source_id="existing_source",
        stream_type="EEG",
    )
    new_stream_info = mock_stream_info_factory(
        name="NewStream",
        source_id="new_source",
        stream_type="EMG",
    )

    mocker.patch(
        "MoBI_View.core.discovery.resolve_streams",
        return_value=[existing_stream_info, new_stream_info],
    )

    mock_inlet_class = mocker.patch("MoBI_View.core.discovery.DataInlet")
    mock_new_inlet = MagicMock()
    mock_new_inlet.stream_name = "NewStream"
    mock_new_inlet.stream_type = "EMG"
    mock_new_inlet.source_id = "new_source"
    mock_new_inlet.channel_count = 2
    mock_inlet_class.return_value = mock_new_inlet

    inlets, count = discovery.discover_and_create_inlets(
        wait_time=0.5,
        existing_inlets=[existing_inlet],
    )

    assert count == 1
    assert len(inlets) == 1
    assert mock_inlet_class.call_count == 1


def test_discover_and_create_inlets_handles_inlet_creation_error(
    mocker: MockFixture,
    mock_stream_info_factory: Callable[..., MagicMock],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """discover_and_create_inlets should skip streams that fail to create inlets."""
    stream1 = mock_stream_info_factory(name="BadStream", source_id="bad_source")
    stream2 = mock_stream_info_factory(name="GoodStream", source_id="good_source")

    mocker.patch(
        "MoBI_View.core.discovery.resolve_streams",
        return_value=[stream1, stream2],
    )

    mock_inlet_class = mocker.patch("MoBI_View.core.discovery.DataInlet")
    mock_good_inlet = MagicMock()
    mock_good_inlet.stream_name = "GoodStream"
    mock_good_inlet.stream_type = "EEG"
    mock_good_inlet.source_id = "good_source"
    mock_good_inlet.channel_count = 3

    mock_inlet_class.side_effect = [
        RuntimeError("Failed to create inlet"),
        mock_good_inlet,
    ]

    inlets, count = discovery.discover_and_create_inlets(wait_time=0.5)
    captured = capsys.readouterr()

    assert count == 1
    assert len(inlets) == 1
    assert "Skipping stream BadStream" in captured.out


def test_discover_and_create_inlets_handles_resolve_error(
    mocker: MockFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """discover_and_create_inlets should handle errors from resolve_streams."""
    mocker.patch(
        "MoBI_View.core.discovery.resolve_streams",
        side_effect=RuntimeError("Network error"),
    )

    inlets, count = discovery.discover_and_create_inlets(wait_time=0.5)
    captured = capsys.readouterr()

    assert count == 0
    assert len(inlets) == 0
    assert "Error during stream discovery" in captured.out


def test_discover_and_create_inlets_prints_discovered_streams(
    mocker: MockFixture,
    mock_stream_info_factory: Callable[..., MagicMock],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """discover_and_create_inlets should print info about discovered streams."""
    stream = mock_stream_info_factory(name="TestStream", channel_count=8)

    mocker.patch(
        "MoBI_View.core.discovery.resolve_streams",
        return_value=[stream],
    )

    mock_inlet = MagicMock()
    mock_inlet.stream_name = "TestStream"
    mock_inlet.stream_type = "EEG"
    mock_inlet.source_id = "test_source"
    mock_inlet.channel_count = 8

    mocker.patch("MoBI_View.core.discovery.DataInlet", return_value=mock_inlet)

    discovery.discover_and_create_inlets(wait_time=0.5)
    captured = capsys.readouterr()

    assert "Discovered new stream: TestStream" in captured.out
    assert "8 channels" in captured.out


def test_discover_and_create_inlets_with_empty_existing_list(
    mocker: MockFixture,
    mock_stream_info_factory: Callable[..., MagicMock],
) -> None:
    """discover_and_create_inlets should handle empty existing_inlets list."""
    stream = mock_stream_info_factory(name="Stream1")

    mocker.patch(
        "MoBI_View.core.discovery.resolve_streams",
        return_value=[stream],
    )

    mock_inlet = MagicMock()
    mock_inlet.stream_name = "Stream1"
    mock_inlet.stream_type = "EEG"
    mock_inlet.source_id = "source1"
    mock_inlet.channel_count = 3

    mocker.patch("MoBI_View.core.discovery.DataInlet", return_value=mock_inlet)

    inlets, count = discovery.discover_and_create_inlets(
        wait_time=0.5,
        existing_inlets=[],
    )

    assert count == 1
    assert len(inlets) == 1


def test_discover_and_create_inlets_deduplicates_by_source_name_type(
    mocker: MockFixture,
    mock_stream_info_factory: Callable[..., MagicMock],
    mock_data_inlet_factory: Callable[..., MagicMock],
) -> None:
    """discover_and_create_inlets should deduplicate using (name, type)."""
    existing = mock_data_inlet_factory(
        stream_name="MyStream",
        stream_type="EEG",
    )

    same_stream = mock_stream_info_factory(
        name="MyStream",
        stream_type="EEG",
    )

    different_stream = mock_stream_info_factory(
        name="DifferentStream",
        stream_type="EEG",
    )

    mocker.patch(
        "MoBI_View.core.discovery.resolve_streams",
        return_value=[same_stream, different_stream],
    )

    mock_new_inlet = MagicMock()
    mock_new_inlet.stream_name = "DifferentStream"
    mock_new_inlet.stream_type = "EEG"
    mock_new_inlet.channel_count = 3

    mocker.patch("MoBI_View.core.discovery.DataInlet", return_value=mock_new_inlet)

    inlets, count = discovery.discover_and_create_inlets(
        wait_time=0.5,
        existing_inlets=[existing],
    )

    assert count == 1
    assert len(inlets) == 1
