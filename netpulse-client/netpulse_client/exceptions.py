"""
NetPulse Client 异常类定义
"""

from typing import Optional


class NetPulseError(Exception):
    """NetPulse 基础异常类"""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthenticationError(NetPulseError):
    """认证错误"""
    pass


class ConnectionError(NetPulseError):
    """连接错误"""
    pass


class JobError(NetPulseError):
    """任务错误"""
    
    def __init__(self, message: str, job_id: Optional[str] = None, status_code: Optional[int] = None):
        super().__init__(message, status_code)
        self.job_id = job_id


class TimeoutError(NetPulseError):
    """超时错误"""
    pass


class ValidationError(NetPulseError):
    """验证错误"""
    pass


class SDKValidationError(NetPulseError):
    """SDK验证错误"""
    pass


class ConfigurationError(NetPulseError):
    """Raised when configuration is invalid."""
    pass


class TemplateError(NetPulseError):
    """Raised when template processing fails."""
    pass


class DeviceError(NetPulseError):
    """Raised when device operation fails."""
    
    def __init__(self, message: str, device_host: Optional[str] = None):
        super().__init__(message)
        self.device_host = device_host 