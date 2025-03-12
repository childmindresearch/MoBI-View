"""Common fixtures for PyQt/PyQtGraph testing."""

from typing import Generator

import pyqtgraph as pg
import pytest
from PyQt6 import QtWidgets


@pytest.fixture(scope="session", autouse=True)
def qt_app() -> Generator[QtWidgets.QApplication, None, None]:
    """Creates a QtWidgets.QApplication instance for tests.

    Yields:
        A QApplication instance.
    """
    app = QtWidgets.QApplication([])
    pg.setConfigOption("useOpenGL", False)
    yield app
    app.quit()
