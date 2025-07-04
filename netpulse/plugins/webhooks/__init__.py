from typing import Any

import rq

from ...models import WebHook


class BaseWebHookCaller:
    """Abstract base class for all webhooks."""

    webhook_name: str = "base"

    def __init__(self, hook: WebHook):
        raise NotImplementedError

    def call(self, req: Any, job: rq.job.Job, result: Any, **kwargs):
        """
        (noexcept) This method must throw no exceptions.
        """
        raise NotImplementedError
