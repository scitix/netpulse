from typing import List

from ...models import NodeInfo
from ...utils.exceptions import WorkerUnavailableError  # noqa: F401


class BaseScheduler:
    """
    Base class for all schedulers.
    Raise WorkerNotAvailableError when there is not enough capacity.
    """

    scheduler_name = "base"

    def __init__(self):
        raise NotImplementedError

    def node_select(self, nodes: List[NodeInfo], host: str) -> NodeInfo:
        raise NotImplementedError

    def batch_node_select(self, nodes: List[NodeInfo], hosts: List[str]) -> List[NodeInfo]:
        raise NotImplementedError
