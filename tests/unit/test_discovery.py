"""Unit tests for the discovery module."""

from typing import Callable
from unittest.mock import MagicMock

import pytest
from pylsl import info as pylsl_info
from pytest_mock import MockFixture

from MoBI_View.core import data_inlet, discovery


@pytest.fixture
def mock_stream_info_factory() -> Callable[..., MagicMock]:
    """Factory for creating mock StreamInfo objects."""

    def _factory(
        name: str = "TestStream",
        stream_type: str = "EEG",
        channel_count: int = 3,
        source_id: str = "MockSourceID",
    ) -> MagicMock:
        info = MagicMock(spec=pylsl_info.StreamInfo)
        info.name.return_value = name
        info.type.return_value = stream_type
        info.channel_count.return_value = channel_count
        info.channel_format.return_value = 1
        info.source_id.return_value = source_id
        info.get_channel_labels.return_value = [f"Ch{i}" for i in range(channel_count)]
        info.get_channel_types.return_value = ["EEG"] * channel_count
        info.get_channel_units.return_value = ["uV"] * channel_count
        return info

    return _factory


def test_happy_path_discovers_and_creates_inlets(
    mocker: MockFixture,
    mock_stream_info_factory: Callable[..., MagicMock],
) -> None:
    """Test the complete happy path: discover streams and create inlets."""
    stream1 = mock_stream_info_factory(name="Stream1")
    stream2 = mock_stream_info_factory(name="Stream2")
    mocker.patch(
        "MoBI_View.core.discovery.pylsl_resolve.resolve_streams",
        return_value=[stream1, stream2],
    )

    mock_inlet1 = MagicMock(stream_name="Stream1", stream_type="EEG", channel_count=3)
    mock_inlet2 = MagicMock(stream_name="Stream2", stream_type="EEG", channel_count=3)
    mocker.patch(
        "MoBI_View.core.discovery.data_inlet.DataInlet",
        side_effect=[mock_inlet1, mock_inlet2],
    )

    inlets = discovery.discover_and_create_inlets()

    assert len(inlets) == 2
    assert inlets[0].stream_name == "Stream1"
    assert inlets[1].stream_name == "Stream2"


def test_deduplicates_against_existing_inlets(
    mocker: MockFixture,
    mock_stream_info_factory: Callable[..., MagicMock],
) -> None:
    """Test deduplication: skips streams that match existing inlets."""
    existing_inlet = MagicMock(spec=data_inlet.DataInlet)
    existing_inlet.source_id = "ExistingSourceID"
    existing_inlet.stream_name = "ExistingStream"
    existing_inlet.stream_type = "EEG"

    existing_stream = mock_stream_info_factory(
        name="ExistingStream", stream_type="EEG", source_id="ExistingSourceID"
    )
    new_stream = mock_stream_info_factory(name="NewStream", stream_type="EMG")
    mocker.patch(
        "MoBI_View.core.discovery.pylsl_resolve.resolve_streams",
        return_value=[existing_stream, new_stream],
    )

    mock_new_inlet = MagicMock(
        stream_name="NewStream", stream_type="EMG", channel_count=3
    )
    mocker.patch(
        "MoBI_View.core.discovery.data_inlet.DataInlet", return_value=mock_new_inlet
    )

    inlets = discovery.discover_and_create_inlets(existing_inlets=[existing_inlet])

    assert len(inlets) == 1
    assert inlets[0].stream_name == "NewStream"


def test_handles_resolve_streams_failure(
    mocker: MockFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test error handling when resolve_streams() fails."""
    mocker.patch(
        "MoBI_View.core.discovery.pylsl_resolve.resolve_streams",
        side_effect=RuntimeError("Network error"),
    )

    inlets = discovery.discover_and_create_inlets()

    assert len(inlets) == 0
    assert "Error during stream discovery" in caplog.text
    assert "Network error" in caplog.text


def test_handles_data_inlet_creation_failure(
    mocker: MockFixture,
    mock_stream_info_factory: Callable[..., MagicMock],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test error handling when DataInlet creation fails for one stream."""
    bad_stream = mock_stream_info_factory(name="BadStream")
    good_stream = mock_stream_info_factory(name="GoodStream")
    mocker.patch(
        "MoBI_View.core.discovery.pylsl_resolve.resolve_streams",
        return_value=[bad_stream, good_stream],
    )

    mock_good_inlet = MagicMock(
        stream_name="GoodStream", stream_type="EEG", channel_count=3
    )
    mocker.patch(
        "MoBI_View.core.discovery.data_inlet.DataInlet",
        side_effect=[RuntimeError("Invalid channel format"), mock_good_inlet],
    )

    inlets = discovery.discover_and_create_inlets()

    assert len(inlets) == 1
    assert inlets[0].stream_name == "GoodStream"
    assert "Skipping stream BadStream" in caplog.text


def test_handles_no_streams_discovered(
    mocker: MockFixture,
) -> None:
    """Test when resolve_streams() returns an empty list."""
    mocker.patch(
        "MoBI_View.core.discovery.pylsl_resolve.resolve_streams", return_value=[]
    )

    inlets = discovery.discover_and_create_inlets()

    assert len(inlets) == 0


@pytest.mark.parametrize(
    ("wait_time_input", "expected_value", "expected_log_fragment"),
    [
        (None, 1.0, None),  # Uses config default
        (2.5, 2.5, None),  # Valid explicit value
        (0.5, 0.5, None),  # Valid edge case (minimum)
        (-1.5, 1.0, "wait_time cannot be negative or zero"),  # Negative
        (0, 1.0, "wait_time cannot be negative or zero"),  # Zero
        (0.3, 0.5, "below minimum of 0.5s"),  # Below minimum
        (float("inf"), 1.0, "Invalid wait_time value"),  # Infinity
        ("invalid", 1.0, "Invalid wait_time value"),  # Invalid type
    ],
)
def test_wait_time_validation(
    mocker: MockFixture,
    mock_stream_info_factory: Callable[..., MagicMock],
    caplog: pytest.LogCaptureFixture,
    wait_time_input: float | None,
    expected_value: float,
    expected_log_fragment: str | None,
) -> None:
    """Test wait_time validation and defaults."""
    stream = mock_stream_info_factory(name="Stream")
    mock_resolve = mocker.patch(
        "MoBI_View.core.discovery.pylsl_resolve.resolve_streams",
        return_value=[stream],
    )
    mock_inlet = MagicMock(stream_name="Stream")
    mocker.patch(
        "MoBI_View.core.discovery.data_inlet.DataInlet", return_value=mock_inlet
    )

    if wait_time_input is None:
        discovery.discover_and_create_inlets()
    else:
        discovery.discover_and_create_inlets(wait_time=wait_time_input)  # type: ignore[arg-type]

    mock_resolve.assert_called_once_with(expected_value)
    if expected_log_fragment:
        assert expected_log_fragment in caplog.text
