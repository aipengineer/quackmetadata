# tests/test_core.py
"""
Tests for QuackTool's core functionality.
"""

from pathlib import Path
from unittest import mock


from quacktool.core import (
    _detect_asset_type,
    _detect_by_extension,
    _detect_by_mime_type,
    _generate_output_path,
    _process_by_type_and_mode,
    process_asset,
)
from quacktool.models import AssetConfig, AssetType


class TestAssetTypeDetection:
    """Tests for asset type detection functions."""

    def test_detect_by_extension(self) -> None:
        """Test detection by file extension."""
        # Image
        assert _detect_by_extension(Path("test.jpg")) == AssetType.IMAGE
        assert _detect_by_extension(Path("test.png")) == AssetType.IMAGE
        assert _detect_by_extension(Path("test.webp")) == AssetType.IMAGE

        # Video
        assert _detect_by_extension(Path("test.mp4")) == AssetType.VIDEO
        assert _detect_by_extension(Path("test.mov")) == AssetType.VIDEO
        assert _detect_by_extension(Path("test.mkv")) == AssetType.VIDEO

        # Audio
        assert _detect_by_extension(Path("test.mp3")) == AssetType.AUDIO
        assert _detect_by_extension(Path("test.wav")) == AssetType.AUDIO
        assert _detect_by_extension(Path("test.flac")) == AssetType.AUDIO

        # Document
        assert _detect_by_extension(Path("test.pdf")) == AssetType.DOCUMENT
        assert _detect_by_extension(Path("test.docx")) == AssetType.DOCUMENT
        assert _detect_by_extension(Path("test.md")) == AssetType.DOCUMENT

        # Other
        assert _detect_by_extension(Path("test.xyz")) == AssetType.OTHER

    @mock.patch("quacktool.core.fs.get_mime_type")
    def test_detect_by_mime_type(self, mock_get_mime_type: mock.MagicMock) -> None:
        """Test detection by MIME type."""
        # Mock different MIME types
        mock_get_mime_type.side_effect = [
            "image/jpeg",
            "video/mp4",
            "audio/mpeg",
            "application/pdf",
            "unknown/type",
            None,
        ]

        # Test detection for each MIME type
        assert _detect_by_mime_type(Path("test.jpg")) == AssetType.IMAGE
        assert _detect_by_mime_type(Path("test.mp4")) == AssetType.VIDEO
        assert _detect_by_mime_type(Path("test.mp3")) == AssetType.AUDIO
        assert _detect_by_mime_type(Path("test.pdf")) == AssetType.DOCUMENT
        assert _detect_by_mime_type(Path("test.xyz")) == AssetType.OTHER
        assert _detect_by_mime_type(Path("test.none")) == AssetType.OTHER

    @mock.patch("quacktool.core._detect_by_mime_type")
    @mock.patch("quacktool.core._detect_by_extension")
    @mock.patch("quacktool.core.fs.get_file_info")
    def test_detect_asset_type(
            self,
            mock_get_file_info: mock.MagicMock,
            mock_detect_by_extension: mock.MagicMock,
            mock_detect_by_mime_type: mock.MagicMock,
    ) -> None:
        """Test the overall asset type detection."""
        # Set up mock return values
        mock_get_file_info.return_value = mock.MagicMock(success=True, exists=True)

        # Case 1: MIME type detection succeeds
        mock_detect_by_mime_type.return_value = AssetType.IMAGE
        assert _detect_asset_type(Path("test.jpg")) == AssetType.IMAGE

        # Case 2: MIME type detection fails, fall back to extension
        mock_detect_by_mime_type.return_value = AssetType.OTHER
        mock_detect_by_extension.return_value = AssetType.VIDEO
        assert _detect_asset_type(Path("test.mp4")) == AssetType.VIDEO

        # Case 3: File doesn't exist
        mock_get_file_info.return_value = mock.MagicMock(success=False, exists=False)
        assert _detect_asset_type(Path("nonexistent.file")) == AssetType.OTHER


class TestOutputPathGeneration:
    """Tests for output path generation."""

    @mock.patch("quacktool.core.resolver.resolve_project_path")
    @mock.patch("quacktool.core.fs.create_directory")
    @mock.patch("quacktool.core.get_tool_config")
    def test_generate_output_path(
            self,
            mock_get_tool_config: mock.MagicMock,
            mock_create_directory: mock.MagicMock,
            mock_resolve_project_path: mock.MagicMock,
            temp_dir: Path,
    ) -> None:
        """Test generating output paths."""
        # Set up mocks
        mock_get_tool_config.return_value = {"output_dir": str(temp_dir)}
        mock_resolve_project_path.return_value = temp_dir
        mock_create_directory.return_value = None

        # Test with default format (keep original extension)
        input_path = Path("test_file.jpg")
        output_path = _generate_output_path(input_path)
        assert output_path.name.startswith("test_file")
        assert output_path.suffix == ".jpg"
        assert output_path.parent == temp_dir

        # Test with specified format
        output_path = _generate_output_path(input_path, "webp")
        assert output_path.name.startswith("test_file")
        assert output_path.suffix == ".webp"

        # Verify directory creation was called
        mock_create_directory.assert_called_with(temp_dir, exist_ok=True)


class TestProcessAsset:
    """Tests for the process_asset function."""

    @mock.patch("quacktool.core._process_by_type_and_mode")
    @mock.patch("quacktool.core._detect_asset_type")
    @mock.patch("quacktool.core._generate_output_path")
    def test_process_asset_success(
            self,
            mock_generate_output_path: mock.MagicMock,
            mock_detect_asset_type: mock.MagicMock,
            mock_process_by_type_and_mode: mock.MagicMock,
            test_file: Path,
    ) -> None:
        """Test successful asset processing."""
        # Set up mocks
        output_path = Path("output/test_processed.webp")
        mock_generate_output_path.return_value = output_path
        mock_detect_asset_type.return_value = AssetType.IMAGE
        mock_process_by_type_and_mode.return_value = mock.MagicMock(
            success=True,
            output_path=output_path,
            error=None,
            metrics={"size_ratio": 0.8},
            duration_ms=100,
        )

        # Create config and call process_asset
        config = AssetConfig(input_path=test_file)
        result = process_asset(config)

        # Verify the result
        assert result.success is True
        assert result.output_path == output_path
        assert result.error is None
        assert "size_ratio" in result.metrics
        assert result.duration_ms >= 1  # Duration should be set

        # Verify correct types were detected and methods were called
        mock_detect_asset_type.assert_called_once()
        mock_generate_output_path.assert_called_once()
        mock_process_by_type_and_mode.assert_called_once_with(
            config, AssetType.IMAGE, output_path
        )

    def test_process_asset_nonexistent_file(self) -> None:
        """Test processing with a nonexistent file."""
        # Create config with nonexistent file
        config = AssetConfig(
            input_path=Path("/path/to/nonexistent/file"),
            # Skip validation by pretending we're in a test environment
            # This prevents the validation error in AssetConfig
        )

        # Mock the file check in process_asset to force a "not exists" scenario
        with mock.patch("pathlib.Path.exists", return_value=False):
            result = process_asset(config)

        # Verify the result
        assert result.success is False
        assert "not found" in result.error if result.error else ""
        assert result.duration_ms >= 1


    @mock.patch("quacktool.core._process_by_type_and_mode")
    def test_process_asset_error_handling(
            self,
            mock_process_by_type_and_mode: mock.MagicMock,
            test_file: Path,
    ) -> None:
        """Test error handling during processing."""
        # Set up mock for _generate_output_path to avoid config issues
        with mock.patch("quacktool.core._generate_output_path") as mock_output_path:
            mock_output_path.return_value = Path("output/test.txt")

            # Set up mock for _detect_asset_type to avoid potential issues
            with mock.patch("quacktool.core._detect_asset_type") as mock_detect_type:
                mock_detect_type.return_value = AssetType.IMAGE

                # Set up mock to raise an exception
                mock_process_by_type_and_mode.side_effect = RuntimeError(
                    "Test processing error")

                # Create config and call process_asset
                config = AssetConfig(input_path=test_file)
                result = process_asset(config)

                # Verify the result has captured the error
                assert result.success is False
                assert "Test processing error" in result.error if result.error else ""
                assert result.duration_ms >= 1

class TestProcessByTypeAndMode:
    """Tests for the process by type and mode functions."""

    @mock.patch("quacktool.core.fs.create_directory")
    @mock.patch("quacktool.core._process_image")
    def test_process_image(
            self,
            mock_process_image: mock.MagicMock,
            mock_create_directory: mock.MagicMock,
            test_file: Path,
    ) -> None:
        """Test processing for image assets."""
        # Set up mock
        output_path = Path("output/test.webp")
        mock_process_image.return_value = mock.MagicMock(
            success=True, output_path=output_path
        )

        # Create config and call processing function
        config = AssetConfig(input_path=test_file)
        result = _process_by_type_and_mode(config, AssetType.IMAGE, output_path)

        # Verify results
        assert result.success is True
        assert result.output_path == output_path

        # Verify mocks were called
        mock_create_directory.assert_called_once_with(output_path.parent, exist_ok=True)
        mock_process_image.assert_called_once_with(config, output_path)

    @mock.patch("quacktool.core.fs.create_directory")
    @mock.patch("quacktool.core._process_video")
    def test_process_video(
            self,
            mock_process_video: mock.MagicMock,
            mock_create_directory: mock.MagicMock,
            test_file: Path,
    ) -> None:
        """Test processing for video assets."""
        # Set up mock
        output_path = Path("output/test.mp4")
        mock_process_video.return_value = mock.MagicMock(
            success=True, output_path=output_path
        )

        # Create config and call processing function
        config = AssetConfig(input_path=test_file)
        result = _process_by_type_and_mode(config, AssetType.VIDEO, output_path)

        # Verify results
        assert result.success is True
        assert result.output_path == output_path

        # Verify mocks were called
        mock_create_directory.assert_called_once_with(output_path.parent, exist_ok=True)
        mock_process_video.assert_called_once_with(config, output_path)

    @mock.patch("quacktool.core.fs.create_directory")
    @mock.patch("quacktool.core._copy_file")
    def test_process_other(
            self,
            mock_copy_file: mock.MagicMock,
            mock_create_directory: mock.MagicMock,
            test_file: Path,
    ) -> None:
        """Test processing for other asset types."""
        # Set up mock
        output_path = Path("output/test.txt")
        mock_copy_file.return_value = mock.MagicMock(
            success=True, output_path=output_path
        )

        # Create config and call processing function
        config = AssetConfig(input_path=test_file)
        result = _process_by_type_and_mode(config, AssetType.OTHER, output_path)

        # Verify results
        assert result.success is True
        assert result.output_path == output_path

        # Verify mocks were called
        mock_create_directory.assert_called_once_with(output_path.parent, exist_ok=True)
        mock_copy_file.assert_called_once_with(test_file, output_path)