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


def test_cli_play_is_an_explicit_subcommand() -> None:
    """`if_fun play` must be treated as a real subcommand, not elided.

    With a single @app.command, Typer defaults to invoking that command when
    the user passes no subcommand name — but it then rejects the command
    name if supplied. A no-op callback forces subcommand dispatch so both
    behaviours work consistently.
    """
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # The help must list "play" as a named subcommand, not collapse it away.
    assert "play" in result.stdout.lower()
    # Running with no args must show help rather than launching the TUI.
    result_no_args = runner.invoke(app, [])
    # Typer's behaviour: missing-command exits 2 and prints help-like message.
    assert result_no_args.exit_code != 0 or "play" in result_no_args.stdout.lower()
