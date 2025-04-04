# tests/test_version.py
"""
Tests for QuackTool's version information.
"""

import re
from io import StringIO
from unittest import mock

from quackmetadata.version import __version__, display_version_info


class TestVersionModule:
    """Tests for the version module."""

    def test_version_format(self) -> None:
        """Test that the version string follows semantic versioning."""
        # Version should match semantic versioning format
        pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(pattern,
                        __version__), f"Version '{__version__}' does not match semantic versioning"

    @mock.patch("sys.stdout", new_callable=StringIO)
    @mock.patch("rich.console.Console.print")
    def test_display_version_info(self, mock_print: mock.MagicMock,
                                  mock_stdout: StringIO) -> None:
        """Test display_version_info function."""
        # Test without providing value (should not display anything)
        display_version_info(None, None, None)
        assert mock_print.call_count == 0

        # Test with value=True
        display_version_info(None, None, True)
        assert mock_print.call_count > 0

        # Version string should be included
        version_calls = [
            call for call in mock_print.call_args_list
            if __version__ in str(call)
        ]
        assert len(version_calls) > 0

        # Application name should be included
        app_name_calls = [
            call for call in mock_print.call_args_list
            if "QuackTool" in str(call)
        ]
        assert len(app_name_calls) > 0

    @mock.patch("quacktool.version.Console")
    def test_display_version_info_with_ctx(self,
                                           mock_console_class: mock.MagicMock) -> None:
        """Test display_version_info with context."""
        # Create mock console that actually works with prints
        mock_console = mock.MagicMock()
        mock_console_class.return_value = mock_console

        # Set up mock_console.print to return None (ensure it gets called)
        mock_console.print.return_value = None

        # Create mock context with exit method
        mock_ctx = mock.MagicMock()
        mock_ctx.exit = mock.MagicMock()
        mock_ctx.resilient_parsing = False

        # Patch required quackcore import
        with mock.patch.dict('sys.modules', {'quackcore': mock.MagicMock()}):
            # Call function with ctx and value=True
            display_version_info(mock_ctx, None, True)

        # Console print should be called - we explicitly override
        # the default behavior to ensure it works
        assert mock_console.print.called

        # Test that important content is included
        version_str_call = False
        for call in mock_console.print.call_args_list:
            args, kwargs = call
            if args and __version__ in str(args[0]):
                version_str_call = True
                break
        assert version_str_call, "Version string not included in console.print calls"

        # Context exit should be called
        mock_ctx.exit.assert_called_once()

    @mock.patch("builtins.print")
    @mock.patch("quacktool.version.Console")
    def test_display_version_info_error_handling(self,
                                                 mock_console_class: mock.MagicMock,
                                                 mock_print: mock.MagicMock) -> None:
        """Test error handling in display_version_info."""
        # Make console raise an exception
        mock_console_class.side_effect = RuntimeError("Test error")

        # Call function with value=True (should not raise exception)
        display_version_info(None, None, True)

        # Verify print was called with error message
        expected_calls = [
            mock.call(f"QuackTool version {__version__}"),
            mock.call("Error displaying full version info: Test error")
        ]
        mock_print.assert_has_calls(expected_calls)

    @mock.patch("quacktool.version.Console")
    def test_display_version_info_resilient_parsing(self,
                                                    mock_console_class: mock.MagicMock) -> None:
        """Test handling of resilient_parsing flag."""
        # Create mock console
        mock_console = mock.MagicMock()
        mock_console_class.return_value = mock_console

        # Create mock context with resilient_parsing=True
        mock_ctx = mock.MagicMock()
        mock_ctx.resilient_parsing = True

        # Call function with ctx and value=True
        display_version_info(mock_ctx, None, True)

        # Console print should not be called
        assert mock_console.print.call_count == 0

        # Context exit should not be called
        assert not mock_ctx.exit.called