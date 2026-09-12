import pytest

from agent_runtime.postgres import _RetryingConnection


class TransientDatabaseError(Exception):
    pass


class FakeConnection:
    def __init__(self, *, fail=False, value=None):
        self.fail = fail
        self.value = value
        self.closed = False
        self.calls = 0

    def execute(self, statement, params=None):
        self.calls += 1
        if self.fail:
            raise TransientDatabaseError("SSL connection closed")
        return self.value

    def close(self):
        self.closed = True


def test_interrupted_read_reconnects_once():
    first = FakeConnection(fail=True)
    second = FakeConnection(value="row")
    connection = _RetryingConnection(first, lambda: second, (TransientDatabaseError,))

    assert connection.execute("SELECT document FROM runs WHERE id=%s", ("run-1",)) == "row"
    assert first.closed is True
    assert second.calls == 1


def test_interrupted_write_is_not_repeated():
    first = FakeConnection(fail=True)
    replacement = FakeConnection(value="unexpected")
    connection = _RetryingConnection(first, lambda: replacement, (TransientDatabaseError,))

    with pytest.raises(TransientDatabaseError):
        connection.execute("INSERT INTO runs VALUES (%s)", ("run-1",))

    assert first.closed is False
    assert replacement.calls == 0
