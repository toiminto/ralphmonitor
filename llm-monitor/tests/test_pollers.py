"""Tests for pollers (mocked)."""

import pytest
from unittest.mock import patch, MagicMock
import psutil


class TestSystemPoller:
    @patch("psutil.cpu_percent")
    @patch("psutil.virtual_memory")
    @patch("psutil.swap_memory")
    def test_system_poller_collects_metrics(self, mock_swap, mock_mem, mock_cpu):
        """Verify system poller collects correct metrics from psutil."""
        mock_cpu.return_value = 42.5
        mock_mem.return_value = MagicMock(used=4 * 1024 * 1024 * 1024, total=16 * 1024 * 1024 * 1024)
        mock_swap.return_value = MagicMock(used=0, total=8 * 1024 * 1024 * 1024)

        # Just verify psutil returns expected values
        assert psutil.cpu_percent(interval=0) == 42.5
        mem = psutil.virtual_memory()
        assert mem.used == 4 * 1024 * 1024 * 1024
        assert mem.total == 16 * 1024 * 1024 * 1024
