import logging
import socket

from rq import Queue
from rq.worker import BaseWorker, SimpleWorker

from ..services.rediz import g_rdb
from ..utils import g_config

log = logging.getLogger(__name__)


class RedisWorker:
    def __init__(self):
        # Connection
        self.rdb = g_rdb.conn

        # IP <=> Node Mapping
        self.host_to_node_map = g_config.redis.key.host_to_node_map
        # Node Name <=> Node Info Mapping (Node is a container)
        self.node_info_map = g_config.redis.key.node_info_map

        self.ttl = g_config.worker.ttl

        self.name: str = "Unknown"
        self.hostname: str = socket.gethostname()
        self.listened_queue: str = None

        self._worker: BaseWorker = None

    def listen(self, q_name: str):
        """
        By default we use SimpleWorker to avoid fork() in `rq`.
        We use `multiprocessing.Process` to fork() explicitly.

        NOTE:
        - NodeWorker owns and manages the state in Redis. So we use it
          in a serial manner (event driven) to avoid race conditions.
        - PinnedWorker also sticks to single process, as we want to execute
          commands serially on devices and persist the connection.
        """
        log.info(f"Worker {self.name} is listening on queue {q_name}")
        self.listened_queue = q_name

        queue = Queue(q_name, connection=self.rdb)
        self._worker = SimpleWorker(queue, name=self.name, connection=self.rdb, worker_ttl=self.ttl)
        self._worker.work()
