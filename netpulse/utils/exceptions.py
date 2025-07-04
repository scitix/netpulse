# Custom exceptions for NetPulse
class NetPulseError(Exception):
    """Base class for NetPulse-specific exceptions"""

    pass


class WorkerUnavailableError(NetPulseError):
    """
    Raised when no worker is available to handle the job, could be:
    - Scheduler is unable to find a suitable node to assign a pinned worker
    - No FIFO worker is available to handle the FIFO job
    """

    pass


class JobOperationError(NetPulseError):
    """Raised when a job operation fails"""

    pass


# These exceptions are used in the Worker class only,
# as they are raised in execution nodes instead of the controller.
class NetPulseWorkerError(NetPulseError):
    """Base class for exceptions raised by NetPulse workers"""

    pass


class HostAlreadyPinnedError(NetPulseWorkerError):
    """Raised when a host is already pinned to a worker."""

    pass


class NodePreemptedError(NetPulseWorkerError):
    """Raised when a node is preempted by another pinned worker."""

    pass
