from types import SimpleNamespace

from pydantic import HttpUrl

from netpulse.models.common import WebHook
from netpulse.plugins.webhooks import basic as webhook_basic
from netpulse.plugins.webhooks.basic import BasicWebHookCaller


def test_basic_webhook_calls_requests(monkeypatch):
    """BasicWebHookCaller should send JSON payload with job id and result."""
    hook = WebHook(name="basic", url=HttpUrl("http://example.com/hook"))
    captured: dict[str, object] = {}

    class DummyResponse:
        def raise_for_status(self):
            captured["raised"] = True

    def fake_request(**kwargs):
        captured.update(kwargs)
        return DummyResponse()

    monkeypatch.setattr(webhook_basic.requests, "request", fake_request)

    caller = BasicWebHookCaller(hook)
    caller.call(req=None, job=SimpleNamespace(id="job-1"), result={"ok": True})  # type: ignore

    assert captured["method"] == hook.method.value
    assert captured["url"] == hook.url.unicode_string()
    assert captured["json"] == {"id": "job-1", "result": "{'ok': True}"}
    assert captured["raised"] is True


def test_basic_webhook_swallows_request_errors(monkeypatch):
    """HTTP errors from webhook should be logged, not raised."""
    hook = WebHook(name="basic", url=HttpUrl("http://example.com/hook"))
    calls: list[int] = []

    def failing_request(**_kwargs):
        calls.append(1)
        raise RuntimeError("boom")

    monkeypatch.setattr(webhook_basic.requests, "request", failing_request)

    caller = BasicWebHookCaller(hook)
    # Should not raise even if the HTTP call fails
    caller.call(req=None, job=SimpleNamespace(id="job-2"), result="done")  # type: ignore

    assert calls == [1]
