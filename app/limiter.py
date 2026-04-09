"""
Global rate limiter instance for OpenHub (PROD-01).

Defined in a dedicated module to avoid circular imports between
main.py and route modules that apply per-endpoint limits.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
