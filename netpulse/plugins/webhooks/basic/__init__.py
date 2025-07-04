import logging
from typing import Any

import requests
import rq

from .. import BaseWebHookCaller, WebHook

log = logging.getLogger(__name__)


class BasicWebHookCaller(BaseWebHookCaller):
    webhook_name = "basic"

    def __init__(self, hook: WebHook):
        self.config = hook

    def call(self, req: Any, job: rq.job.Job, result: Any, **kwargs):
        if isinstance(result, str):
            data = result
        else:
            data = str(result)

        data = {
            "id": job.id,
            "result": data,
        }

        try:
            resp = requests.request(
                method=self.config.method.value,
                url=self.config.url.unicode_string(),
                headers=self.config.headers,
                cookies=self.config.cookies,
                timeout=self.config.timeout,
                auth=self.config.auth,
                json=data,
            )
            resp.raise_for_status()
        except Exception as e:
            log.warning(f"Failed to call webhook {self.config.url}: {e}")
        else:
            log.debug(f"Webhook {self.config.url} called successfully")


__all__ = ["BasicWebHookCaller"]
