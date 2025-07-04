from .device import router as device
from .manage import router as manage
from .pull import router as pull
from .push import router as push
from .template import router as template

__all__ = ["device", "manage", "pull", "push", "template"]
