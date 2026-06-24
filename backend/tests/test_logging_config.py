import logging

from app.logging_config import ColorFormatter


def _record(level: int, msg: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="app.test",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )


def test_color_formatter_wraps_levelname_in_ansi():
    formatter = ColorFormatter("%(levelname)s %(name)s: %(message)s")
    output = formatter.format(_record(logging.INFO, "hello"))
    assert "\x1b[32m" in output
    assert "\x1b[0m" in output
    assert "INFO" in output
    assert "hello" in output


def test_color_formatter_restores_original_levelname():
    formatter = ColorFormatter("%(levelname)s: %(message)s")
    record = _record(logging.WARNING, "watch out")
    formatter.format(record)
    assert record.levelname == "WARNING"


def test_color_formatter_uses_distinct_colors_per_level():
    formatter = ColorFormatter("%(levelname)s")
    info = formatter.format(_record(logging.INFO, "x"))
    warn = formatter.format(_record(logging.WARNING, "x"))
    error = formatter.format(_record(logging.ERROR, "x"))
    assert info.startswith("\x1b[32m")
    assert warn.startswith("\x1b[33m")
    assert error.startswith("\x1b[31m")
