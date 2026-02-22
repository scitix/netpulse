from .detached_task import router as detached_task
from .device import router as device
from .manage import router as manage
from .storage import router as storage
from .template import router as template

__all__ = ["detached_task", "device", "manage", "storage", "template"]
