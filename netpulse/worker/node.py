import logging
import os
import signal
import sys
from multiprocessing import Process

import filelock
from rq import Queue, Worker
from rq.command import send_shutdown_command

from ..models import NodeInfo
from ..utils import g_config
from ..utils.exceptions import HostAlreadyPinnedError, NetPulseWorkerError, NodePreemptedError
from ..utils.logger import setup_logging
from .common import RedisWorker
from .pinned import PinnedWorker

log = logging.getLogger(__name__)


class NodeWorker(RedisWorker):
    """
    This is the daemon worker running on the node (should not be forked).
    All pinned worker is spawned by this worker. Spawning is serial and must be non-blocking.
    """

    def __init__(self):
        super().__init__()
        # For the node worker, the worker name is the hostname
        self.name = self.hostname
        # Save child worker's pids
        self._pid_to_host_map: dict = {}
        # If this worker is signal to exit, it could ignore all SIGCHLD
        self.signaled = False

    def _get_node(self):
        """
        Get the node info from the Redis.
        """
        node_info = self.rdb.hget(self.node_info_map, self.name)
        if not node_info:
            return None

        return NodeInfo.model_validate_json(node_info)

    def listen(self):
        """
        Start the node worker and register.
        """
        # We must ensure there is only one worker running on this node
        flock = filelock.FileLock("./node.lock")
        acquired = False

        try:
            flock.acquire(timeout=3)
            acquired = True

            # Got the lock, overwrite the node info (register)
            node_info = self._get_node()
            if node_info:
                log.warning(f"Node {self.name} already exists, overwriting...")

            node_info = NodeInfo(
                hostname=self.name,
                count=0,
                capacity=g_config.worker.pinned_per_node,
                queue=g_config.get_node_queue_name(self.name),
            )

            # Clean up stale pinned workers and register the node
            keys_to_delete = []
            for host, node_name in self.rdb.hscan_iter(self.host_to_node_map):
                if node_name.decode() == self.name:
                    keys_to_delete.append(host.decode())

            for host in keys_to_delete:
                q_name = g_config.get_host_queue_name(host)
                workers = Worker.all(queue=Queue(q_name, connection=self.rdb))
                for w in workers:
                    w.register_death()

            # Clean up stale data from Node Worker
            worker = Worker.all(queue=Queue(node_info.queue, connection=self.rdb))
            if worker and len(worker) > 0:
                for w in worker:
                    w.register_death()

            with self.rdb.pipeline() as pipe:
                if len(keys_to_delete):
                    pipe.hdel(self.host_to_node_map, *keys_to_delete)

                pipe.hset(self.node_info_map, self.name, node_info.model_dump_json())
                pipe.execute()

            # Start the loop
            super().listen(node_info.queue)
        except filelock.Timeout:
            log.critical(f"Failed to acquire lock for node {self.name}")
            sys.exit(1)
        except Exception as e:
            log.critical(f"NodeWorker {self.name} failed: {e}")
            sys.exit(1)
        finally:
            if acquired:
                self.cleanup()
                flock.release()
                log.info(f"NodeWorker {self.name} stopped.")
            else:
                log.info("NodeWorker exits without acquiring lock.")

    def cleanup(self):
        """
        Clean up all the state and workers.
        Clean up is called after rq.Worker is stopped. So no new Pinned Worker
        will be added after this, we can safely remove all state.
        """
        # When cleanup() is called, we don't need to listen to SIGCHLD anymore.
        self.signaled = True

        keys_to_delete = []
        for _, host in self._pid_to_host_map.items():
            keys_to_delete.append(host)

        with self.rdb.pipeline() as pipe:
            if len(keys_to_delete):
                pipe.hdel(self.host_to_node_map, *keys_to_delete)

            pipe.hdel(self.node_info_map, self.name)
            pipe.execute()

        # Remove all running workers
        for host in keys_to_delete:
            q_name = g_config.get_host_queue_name(host)
            workers = Worker.all(queue=Queue(q_name, connection=self.rdb))
            # assert len(workers) == 1
            for w in workers:
                send_shutdown_command(worker_name=w.name, connection=self.rdb)

    def signaled_to_exit(self):
        # NOTE: SIGINT will be sent to all child processes by TTY, as they have the same PGID
        # That means, SIGCHLD may come before we set signaled=True. It's fine.
        self.signaled = True
        if self._worker:
            self._worker.request_stop()

    def add(self, q_name: str, host: str):
        """
        Spawn a pinned worker on the node.
        This is not concurrent safe.
        """
        for pid, h in self._pid_to_host_map.items():
            if h == host:
                log.warning(f"Host {host} is already pinned (pid: {pid}), skipping...")
                return

        node_info = self.rdb.hget(self.node_info_map, self.name)
        if not node_info:
            # Should never happen
            log.error(f"Node {self.name} does not exist")
            sys.exit(1)

        node_info = NodeInfo.model_validate_json(node_info)

        # Check if the node has enough capacity
        if node_info.count >= node_info.capacity:
            log.error(f"Node {self.name} has reached its capacity")
            raise NodePreemptedError(f"Node {self.name} has reached its capacity")

        node_info.count += 1

        # Before starting, make sure the host is already not pinned.
        # NOTE: Lock acquired here. Unlock is in cleanup()/remove().
        # If NodeWorker is forced to exit, the lock will be released by controller.
        result = self.rdb.hsetnx(self.host_to_node_map, host, self.name)
        if not result:
            log.error(f"Host {host} is already pinned")
            raise HostAlreadyPinnedError(f"Host {host} is already pinned")

        def start():
            worker = PinnedWorker(q_name, host)
            worker.listen(q_name)

        try:
            p = Process(target=start)
            p.start()
        except Exception as e:
            log.error(f"Error in starting the pinned worker: {e}")
            self.rdb.hdel(self.host_to_node_map, host)
            raise e

        # Commit the change after the worker is started
        self._pid_to_host_map[p.pid] = host
        self.rdb.hset(self.node_info_map, self.name, node_info.model_dump_json())

    @staticmethod
    def _remove(pid: int, host: str):
        """
        The helper function to remove the pinned worker.
        NOTE: We can't call this directly from rq worker as it's not pickleable.
        So we have to set it @staticmethod.
        """
        if g_node_worker is None:
            raise NetPulseWorkerError("Node worker not initialized")

        self = g_node_worker
        try:
            self._pid_to_host_map.pop(pid)
        except KeyError:
            # Probably because the NodeWorker is restarted. It's ok to ignore.
            # See signaled_to_exit() for the reason.
            log.warning(f"Unknown pid ({pid}) of exiting child process")
            return

        log.info(f"Cleaning up Pinned Worker ({pid} for {host})")

        node_info = self.rdb.hget(self.node_info_map, self.name)
        if not node_info:
            return
        node_info = NodeInfo.model_validate_json(node_info)
        node_info.count -= 1

        with self.rdb.pipeline() as pipe:
            pipe.hdel(self.host_to_node_map, host)
            pipe.hset(self.node_info_map, self.name, node_info.model_dump_json())
            pipe.execute()

    def remove(self, pid: int):
        """
        Remove the pinned worker from the state.
        This is called after the pinned worker is exited.
        """
        if not (host := self._pid_to_host_map.get(pid)):
            # Should never happen
            log.warning(f"Unknown pid ({pid}) of exiting child process")
            return

        q = Queue(self.listened_queue, connection=self.rdb)

        # We use rq to queue the cleanup task,
        # so that cleanup won't interfere with the add operation.
        q.enqueue(NodeWorker._remove, kwargs={"pid": pid, "host": host})


g_node_worker: NodeWorker = None


def start_pinned_worker(q_name: str, host: str):
    """
    This is requested from controller and called from rq.Worker.
    """
    if g_node_worker is None:
        raise NetPulseWorkerError("Node worker not initialized")
    g_node_worker.add(q_name, host)


def sigchld_handler(signum, frame):
    """
    Handle PinnedWorker's exit and cleanup.
    """
    global g_node_worker
    try:
        while True:
            pid, status = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break

            log.info(f"Child process {pid} exited with status {status}.")

            if g_node_worker is None:
                log.critical("Node worker not initialized")
                continue  # Should never happen

            if g_node_worker.signaled:
                # If Node Worker is quitting, we already cleaned up everything in cleanup()
                log.debug("Node worker is signaled to exit, ignore all SIGCHLD")
                continue

            g_node_worker.remove(pid)
    except ChildProcessError:
        pass


def sigterm_sigint_handler(signum, frame):
    """
    Handle SIGTERM/SIGINT signal.
    """
    global g_node_worker
    if g_node_worker is None:
        log.error("Node worker not initialized")
        sys.exit(1)

    g_node_worker.signaled_to_exit()


def main():
    """
    This is the entry point for the node worker.
    """
    global g_node_worker
    setup_logging(g_config.log.config, g_config.log.level)

    # Install the signal handlers
    signal.signal(signal.SIGCHLD, sigchld_handler)
    signal.signal(signal.SIGTERM, sigterm_sigint_handler)
    signal.signal(signal.SIGINT, sigterm_sigint_handler)

    g_node_worker = NodeWorker()
    g_node_worker.listen()


if __name__ == "__main__":
    main()
