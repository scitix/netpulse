import logging
import sys

import filelock
from rq import Queue, Worker

from ..utils import g_config
from ..utils.logger import setup_logging
from .common import RedisWorker

log = logging.getLogger(__name__)


class FifoWorker(RedisWorker):
    def __init__(self, q_name: str):
        super().__init__()
        # For the FIFO Worker, the name is the hostname + fifo queue name
        self.name = f"{self.hostname}_{q_name}"

    def listen(self, q_name: str):
        """
        For FIFO worker, we use multiprocessing worker. This worker will fork.
        """
        # Currently only one FIFO worker allowed per node.
        flock = filelock.FileLock("./fifo.lock")
        acquired = False

        try:
            flock.acquire(timeout=3)
            acquired = True

            log.info(f"Worker {self.name} is listening on queue {q_name}")
            self.listened_queue = q_name

            queue = Queue(q_name, connection=self.rdb)
            self._worker = Worker(queue, name=self.name, connection=self.rdb, worker_ttl=self.ttl)

            self._worker.work()
        except filelock.Timeout:
            log.critical(f"Failed to acquire lock for FIFO worker {self.name}")
            sys.exit(1)
        except Exception as e:
            log.critical(f"FifoWorker {self.name} failed: {e}")
            sys.exit(1)
        finally:
            if acquired:
                self.cleanup()
                flock.release()
                log.info(f"FifoWorker {self.name} stopped.")
            else:
                log.info("FifoWorker exits without acquiring lock.")

    def cleanup(self):
        """
        No need to clean up for FifoWorker.
        """
        pass


g_fifo_worker: FifoWorker | None = None


def main():
    """
    This is the entry point for the FifoWorker.
    """
    global g_fifo_worker
    setup_logging(g_config.log.config, g_config.log.level)

    fifo_q = g_config.get_fifo_queue_name()
    g_fifo_worker = FifoWorker(fifo_q)
    g_fifo_worker.listen(fifo_q)


if __name__ == "__main__":
    main()
