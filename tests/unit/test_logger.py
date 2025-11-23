import logging

from netpulse.utils.logger import ScrubFilter


def test_scrub_filter_redacts_sensitive_fields():
    """ScrubFilter should mask sensitive keys in log message strings."""
    filt = ScrubFilter()

    record = logging.LogRecord(
        name="netpulse",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg='{"password": "secret", "token": "abc"}',
        args=(),
        exc_info=None,
        func=None,
    )
    filt.filter(record)

    assert "secret" not in record.msg
    assert '"password": "******"' in record.msg
    assert '"token": "******"' in record.msg


def test_scrub_filter_redacts_kwargs_dict():
    """ScrubFilter should redact sensitive values inside kwargs serialization."""
    filt = ScrubFilter()

    record = logging.LogRecord(
        name="netpulse",
        level=logging.INFO,
        pathname=__file__,
        lineno=20,
        msg="Credentials: %(data)s",
        args=(),
        exc_info=None,
        func=None,
    )
    record.args = {"data": '{"key": "abc", "community": "public"}'}
    filt.filter(record)

    assert "abc" not in record.args["data"]
    assert "public" not in record.args["data"]
