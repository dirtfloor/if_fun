from typer.testing import CliRunner

from if_fun.cli import app

runner = CliRunner()


def test_cli_shows_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "play" in result.stdout.lower()


def test_cli_play_command_exists() -> None:
    result = runner.invoke(app, ["play", "--help"])
    assert result.exit_code == 0
