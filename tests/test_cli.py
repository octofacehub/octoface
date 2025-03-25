"""Basic tests for OctoFace CLI."""

import pytest
from click.testing import CliRunner
try:
    import subprocess
except ImportError:
    subprocess = None

from octoface.cli import cli
from octoface import __version__


def test_cli_help():
    """Test the CLI help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "OctoFace CLI" in result.output


def test_cli_version():
    """Test the CLI version output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_command_presence():
    """Test that all expected commands are present."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    
    # Check for all commands
    commands = ["upload", "download", "generate-files", "test-github"]
    for command in commands:
        assert command in result.output, f"Command '{command}' not found in CLI help output"


@pytest.mark.skipif(subprocess is None, reason="subprocess not available")
def test_cli_can_be_executed():
    """Test that the CLI can be executed as a command."""
    try:
        result = subprocess.run(["octoface", "--version"], 
                               capture_output=True, 
                               text=True,
                               check=False)
        assert result.returncode == 0
        assert __version__ in result.stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        pytest.skip("octoface command not available in PATH")


def test_generate_files(mocker):
    """Test the generate-files command with mocked dependencies."""
    # Skip this test if pytest-mock is not installed
    if mocker is None:
        pytest.skip("pytest-mock not available")
    
    # Mock the dependencies
    mocker.patch("octoface.cli.generate_model_metadata", return_value={"name": "Test"})
    mocker.patch("octoface.cli.generate_readme", return_value="# Test")
    mocker.patch("octoface.cli.generate_model_tree", return_value={})
    mocker.patch("octoface.cli.get_github_username", return_value="testuser")
    mocker.patch("os.makedirs")
    
    # Mock file operations
    mocker.patch("builtins.open", mocker.mock_open())
    
    # Run the command
    runner = CliRunner()
    result = runner.invoke(
        cli, 
        [
            "generate-files", 
            "--name", "Test Model", 
            "--description", "A test model", 
            "--tags", "test",
            "--cid", "bafybeih2qqh6rfmgrrggvkwsve7yuru72tm66vmp2cc5q7nmhytnovq7dm"
        ]
    )
    
    # Check the result
    assert result.exit_code == 0 