# tests/test_data_inlet.py

"""Test the functionality of the DataInlet class."""

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Tuple

import numpy as np
import pytest
from PyQt5.QtCore import QCoreApplication
from pytest_mock import MockerFixture

from MoBI_GUI.config import Config

if TYPE_CHECKING:
    from MoBI_GUI.data_inlet import DataInlet  # Type hint only import


# Fixtures
@pytest.fixture
def app() -> Generator[QCoreApplication, None, None]:
    """Pytest fixture to initialize the QCoreApplication."""
    app = QCoreApplication([])
    yield app
    app.quit()


@pytest.fixture
def mock_stream_inlet(mocker: MockerFixture) -> Tuple[Any, Any]:
    """Pytest fixture to mock the pylsl.StreamInlet class with channels metadata."""
    mock_inlet_class = mocker.patch("MoBI_GUI.data_inlet.StreamInlet")
    mock_inlet = mock_inlet_class.return_value

    mock_info = mocker.MagicMock()
    mock_info.name.return_value = "TestStream"
    mock_info.channel_count.return_value = 2

    # Create a real XML structure for desc()
    def create_desc_xml() -> ET.Element:
        root = ET.Element("desc")
        channels = ET.SubElement(root, "channels")
        channel_1 = ET.SubElement(channels, "channel")
        ET.SubElement(channel_1, "label").text = "Channel 1"
        channel_2 = ET.SubElement(channels, "channel")
        ET.SubElement(channel_2, "label").text = "Channel 2"
        return root

    mock_info.desc.return_value = create_desc_xml()
    mock_inlet.info.return_value = mock_info

    return mock_inlet_class, mock_inlet


@pytest.fixture
def mock_stream_inlet_no_channels(mocker: MockerFixture) -> Tuple[Any, Any]:
    """Pytest fixture to mock the pylsl.StreamInlet class without channels metadata."""
    mock_inlet_class = mocker.patch("MoBI_GUI.data_inlet.StreamInlet")
    mock_inlet = mock_inlet_class.return_value

    mock_info = mocker.MagicMock()
    mock_info.name.return_value = "TestStreamNoChannels"
    mock_info.channel_count.return_value = 2

    # Create a real XML structure with no channels
    def create_desc_xml_no_channels() -> ET.Element:
        root = ET.Element("desc")  # No 'channels' element
        return root

    mock_info.desc.return_value = create_desc_xml_no_channels()
    mock_inlet.info.return_value = mock_info

    return mock_inlet_class, mock_inlet


@pytest.fixture
def mock_logger(mocker: MockerFixture) -> MockerFixture:
    """Fixture to mock the logger variable in data_inlet.py."""
    mock_logger_instance = mocker.MagicMock()
    mocker.patch("MoBI_GUI.data_inlet.logger", mock_logger_instance)
    return mock_logger_instance


@pytest.fixture
def data_inlet(
    mock_stream_inlet: Tuple[Any, Any],
    mock_logger: MockerFixture,
    mocker: MockerFixture,
) -> "DataInlet":
    """Pytest fixture to create a DataInlet instance with StreamInlet and PlotItem."""
    from MoBI_GUI.data_inlet import DataInlet

    mock_inlet_class, mock_inlet = mock_stream_inlet
    plot_item = mocker.MagicMock()
    inlet = DataInlet(mock_inlet.info.return_value, plot_item)
    return inlet


# Tests
def test_initialization(
    data_inlet: "DataInlet", mock_stream_inlet: Tuple[Any, Any]
) -> None:
    """Test the initialization of DataInlet."""
    assert data_inlet.channel_count == 2
    assert data_inlet.buffers.shape == (data_inlet.buffers.shape[0], 2)
    assert data_inlet.ptr == 0
    mock_stream_inlet[1].pull_sample.assert_not_called()  # No sample pulled during init


def test_get_channel_names(
    app: QCoreApplication, data_inlet: "DataInlet", mock_stream_inlet: Tuple[Any, Any]
) -> None:
    """Test get_channel_names with valid channel metadata."""
    expected_channels = ["Channel 1", "Channel 2"]
    assert data_inlet.channel_names == expected_channels


def test_get_channel_names_no_channels(
    app: QCoreApplication,
    mock_stream_inlet_no_channels: Tuple[Any, Any],
    mock_logger: MockerFixture,
    mocker: MockerFixture,
) -> None:
    """Test get_channel_names when 'channels' metadata is missing."""
    from MoBI_GUI.data_inlet import DataInlet  # Import after patching logger

    _, mock_inlet = mock_stream_inlet_no_channels
    plot_item = mocker.MagicMock()
    inlet = DataInlet(mock_inlet.info.return_value, plot_item)

    expected_channels = ["Channel 1", "Channel 2"]
    assert inlet.channel_names == expected_channels

    mock_logger.warning.assert_called_once_with(
        "No 'channels' element found in StreamInfo. Using default channel names."
    )


def test_get_channel_names_exception(
    mock_stream_inlet: Tuple[Any, Any],
    mock_logger: MockerFixture,
    mocker: MockerFixture,
) -> None:
    """Test get_channel_names when an exception occurs."""
    from MoBI_GUI.data_inlet import DataInlet  # Import after patching logger

    _, mock_inlet = mock_stream_inlet
    mock_info = mock_inlet.info.return_value
    mock_info.desc.side_effect = Exception("Test exception")
    plot_item = mocker.MagicMock()

    inlet = DataInlet(mock_info, plot_item)

    expected_channels = ["Channel 1", "Channel 2"]
    assert inlet.channel_names == expected_channels

    mock_logger.error.assert_called_once_with(
        "Error extracting channel names: Test exception"
    )


def test_pull_sample_success(
    app: QCoreApplication, data_inlet: "DataInlet", mock_stream_inlet: Tuple[Any, Any]
) -> None:
    """Test successful data pulling from the LSL stream."""
    _, mock_inlet = mock_stream_inlet
    mock_inlet.pull_sample.return_value = ([0.1, 0.2], 123456789.0)

    emitted = []

    def on_data_updated(name: str, data: Dict[str, List[float]]) -> None:
        emitted.append((name, data))

    data_inlet.data_updated.connect(on_data_updated)
    data_inlet.pull_sample()

    assert data_inlet.ptr == 1
    assert len(emitted) == 1
    emitted_name, emitted_data = emitted[0]
    assert emitted_name == "TestStream"
    assert emitted_data["Channel 1"][0] == 0.1
    assert emitted_data["Channel 2"][0] == 0.2


def test_pull_sample_no_data(
    app: QCoreApplication, data_inlet: "DataInlet", mock_stream_inlet: Tuple[Any, Any]
) -> None:
    """Test the scenario where no data is available from the LSL stream."""
    _, mock_inlet = mock_stream_inlet
    mock_inlet.pull_sample.return_value = (None, None)

    emitted = []

    def on_data_updated(name: str, data: Dict[str, List[float]]) -> None:
        emitted.append((name, data))

    data_inlet.data_updated.connect(on_data_updated)
    data_inlet.pull_sample()

    assert data_inlet.ptr == 0
    assert len(emitted) == 0


def test_toggle_channel_visibility(
    data_inlet: "DataInlet", mocker: MockerFixture
) -> None:
    """Test toggling the visibility of a channel."""
    logger_info_mock = mocker.patch("MoBI_GUI.data_inlet.logger.info")

    data_inlet.toggle_channel_visibility("Channel 1", False)

    data_inlet.plot_item.showCurve.assert_called_once_with(0, False)
    logger_info_mock.assert_called_once_with(
        "Toggled visibility for Channel 1 to False"
    )


def test_toggle_channel_visibility_invalid(
    data_inlet: "DataInlet",
    mock_logger: MockerFixture,
) -> None:
    """Test toggling the visibility of a non-existent channel."""
    data_inlet.toggle_channel_visibility("NonExistentChannel", True)

    mock_logger.warning.assert_called_once_with("Channel NonExistentChannel not found.")


def test_update_plot(
    data_inlet: "DataInlet", mocker: MockerFixture, mock_logger: MockerFixture
) -> None:
    """Test the update_plot method of DataInlet."""
    data_inlet.buffers = np.random.rand(Config.BUFFER_SIZE, data_inlet.channel_count)
    mock_plot_item = data_inlet.plot_item
    mock_plot_item.isVisible.return_value = True
    mock_plot_item.plot.return_value = mocker.MagicMock()

    data_inlet.update_plot()

    mock_plot_item.clear.assert_called_once()
    assert mock_plot_item.isVisible.call_count == data_inlet.channel_count
    assert mock_plot_item.plot.call_count == data_inlet.channel_count
    assert len(data_inlet.curves) == data_inlet.channel_count
    mock_logger.debug.assert_called_with("Plot updated with new data.")


def test_update_plot_exception(
    data_inlet: "DataInlet", mocker: MockerFixture, mock_logger: MockerFixture
) -> None:
    """Test update_plot when an exception occurs."""
    data_inlet.plot_item.clear.side_effect = Exception("Test exception")

    data_inlet.update_plot()

    mock_logger.error.assert_called_once_with("Error updating plot: Test exception")


def test_adjust_y_scale(
    data_inlet: "DataInlet", mocker: MockerFixture, mock_logger: MockerFixture
) -> None:
    """Test the adjust_y_scale method of DataInlet."""
    data_inlet.buffers = np.random.rand(Config.BUFFER_SIZE, data_inlet.channel_count)
    data_min = np.min(data_inlet.buffers)
    data_max = np.max(data_inlet.buffers)
    margin = Config.Y_MARGIN * (data_max - data_min)
    expected_range = (data_min - margin, data_max + margin)

    data_inlet.adjust_y_scale()

    data_inlet.plot_item.setYRange.assert_called_once_with(*expected_range)
    mock_logger.debug.assert_called_with("Y-axis scale adjusted.")


def test_adjust_y_scale_exception(
    data_inlet: "DataInlet", mocker: MockerFixture, mock_logger: MockerFixture
) -> None:
    """Test adjust_y_scale when an exception occurs."""
    data_inlet.buffers = np.array([])  # Empty array to cause np.min to fail

    data_inlet.adjust_y_scale()

    mock_logger.error.assert_called_once()
    called_args = mock_logger.error.call_args[0][0]
    assert "Error adjusting Y scale" in called_args


def test_pull_sample_exception(
    data_inlet: "DataInlet",
    mock_stream_inlet: Tuple[Any, Any],
    mock_logger: MockerFixture,
) -> None:
    """Test pull_sample when an exception occurs."""
    _, mock_inlet = mock_stream_inlet
    mock_inlet.pull_sample.side_effect = Exception("Test exception")

    data_inlet.pull_sample()

    mock_logger.error.assert_called_once_with("Error pulling sample: Test exception")


def test_get_channel_names_not_xml_element(
    mock_stream_inlet: Tuple[Any, Any],
    mock_logger: MockerFixture,
    mocker: MockerFixture,
) -> None:
    """Test get_channel_names when desc() does not return an XML element."""
    from MoBI_GUI.data_inlet import DataInlet

    _, mock_inlet = mock_stream_inlet
    mock_info = mock_inlet.info.return_value

    mock_info.desc.return_value = "Not an XML element"

    plot_item = mocker.MagicMock()
    inlet = DataInlet(mock_info, plot_item)

    expected_channels = ["Channel 1", "Channel 2"]
    assert inlet.channel_names == expected_channels

    mock_logger.error.assert_called_once_with(
        "Expected XML Element from StreamInfo.desc()"
    )


def test_toggle_channel_visibility_exception(
    data_inlet: "DataInlet", mock_logger: MockerFixture
) -> None:
    """Test toggle_channel_visibility for a non-existent channel."""
    data_inlet.toggle_channel_visibility("NonExistentChannel", True)

    mock_logger.warning.assert_called_once_with("Channel NonExistentChannel not found.")


def test_get_channel_names_missing_label(
    app: QCoreApplication,
    mock_stream_inlet: Tuple[Any, Any],
    mock_logger: MockerFixture,
    mocker: MockerFixture,
) -> None:
    """Test get_channel_names when some channels are missing labels."""
    from MoBI_GUI.data_inlet import DataInlet

    _, mock_inlet = mock_stream_inlet
    mock_info = mock_inlet.info.return_value

    channels = mock_info.desc.return_value.find("channels")
    channel = channels.findall("channel")[1]
    label = channel.find("label")
    if label is not None:
        channel.remove(label)

    # Reset mock_logger to ignore debug calls from __init__
    mock_logger.reset_mock()

    plot_item = mocker.MagicMock()
    inlet = DataInlet(mock_info, plot_item)

    expected_channels = ["Channel 1", "Channel 2"]
    assert inlet.channel_names == expected_channels
    mock_logger.debug.assert_any_call(
        "Extracted channel names: ['Channel 1', 'Channel 2']"
    )
