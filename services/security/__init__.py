"""
services/security
Módulo de seguridad defensiva, autenticación SSO y autorización RBAC para MS-05 IA Backend.
"""

from .jwt_auth import (
    UsuarioAutenticado,
    get_current_user,
    exigir_roles,
    validar_operador_guard,
    crear_token_prueba,
    JWT_SECRET,
    JWT_ALGORITHM,
    COOKIE_NAME,
    ROLES_TACTICOS_PERMITIDOS
)

__all__ = [
    "UsuarioAutenticado",
    "get_current_user",
    "exigir_roles",
    "validar_operador_guard",
    "crear_token_prueba",
    "JWT_SECRET",
    "JWT_ALGORITHM",
    "COOKIE_NAME",
    "ROLES_TACTICOS_PERMITIDOS"
]
