"""
api/routers/__init__.py
"""

from .reports_router import reports_router
from .mcp_router import mcp_router
from .maintenance_router import maintenance_router
from .agente_router import agente_router
from .ml_router import ml_router

__all__ = [
    "reports_router",
    "mcp_router",
    "maintenance_router",
    "agente_router",
    "ml_router"
]
