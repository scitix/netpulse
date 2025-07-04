import logging
import sys

from .common import RedisWorker

log = logging.getLogger(__name__)


class PinnedWorker(RedisWorker):
    def __init__(self, q_name: str, host: str):
        super().__init__()
        # For the Pinned Worker, the name is the hostname + queue name
        self.name = f"{self.hostname}_{q_name}"
        self.host = host

    def listen(self, q_name: str):
        try:
            super().listen(q_name)
        except Exception as e:
            log.critical(f"Pinned worker {self.name} failed: {e}")
            sys.exit(1)
        finally:
            self.cleanup()
            log.info(f"Pinned worker {self.name} stopped.")

    def cleanup(self):
        """
        Pinned worker don't need to implement this.
        Cleanup is done by the NodeWorker's sigchld_handler.
        """
        pass
