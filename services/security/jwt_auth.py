"""
services/security/jwt_auth.py
Módulo de Seguridad SSO y Validación Criptográfica de Tokens JWT para MS-05 IA Backend.
Garantiza el control de acceso táctico basado en roles (RBAC) para el pipeline
de Reportes Multimodales por Voz y consultas defensivas MCP.
Semestre 2/2026 - INF512 (Ingeniería de Software II)
Responsable: Nataly Martínez (ms5_ia_mcp_backend)
"""

import os
import time
from typing import Optional, List
import jwt
from pydantic import BaseModel
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWT_SECRET = os.getenv("JWT_SECRET", "super_secreto_bomberos_jwt_key_nataly_2026_uagrm")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
COOKIE_NAME = os.getenv("COOKIE_NAME", "token_sesion")

# Roles tácticos autorizados para operar la consola de Sala de Crisis y emitir reportes
ROLES_TACTICOS_PERMITIDOS = ["OPERADOR", "ADMINISTRADOR", "ADMIN"]

# Soporte OpenAPI Bearer para Swagger UI interactivo
bearer_scheme = HTTPBearer(auto_error=False)


class UsuarioAutenticado(BaseModel):
    id: str
    email: str
    rol: str


def extraer_token_de_request(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = None
) -> Optional[str]:
    """
    Extrae el token JWT con la siguiente jerarquía de prioridad:
    1. Cookie HttpOnly ('token_sesion' o alias 'jwt') emitida por el SSO de MS-01.
    2. Cabecera Authorization: Bearer <token> (para clientes REST / Swagger UI).
    """
    # 1. Cookies de sesión HttpOnly
    if COOKIE_NAME in request.cookies:
        return request.cookies[COOKIE_NAME]
    if "jwt" in request.cookies:
        return request.cookies["jwt"]
    if "token" in request.cookies:
        return request.cookies["token"]

    # 2. Cabecera Bearer Token
    if creds and creds.credentials:
        return creds.credentials

    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return None


def decodificar_token(token: str) -> dict:
    """
    Valida la firma criptográfica HS256 y la vigencia temporal del token JWT.
    Lanza HTTPException 401 si el token expiró o fue manipulado.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": True}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada: El token de autenticación ha vencido. Por favor inicie sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token de autenticación inválido o alterado: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> UsuarioAutenticado:
    """
    Dependencia FastAPI que autentica la identidad del usuario actual en MS-05.
    Lanza HTTP 401 si no se presenta un token válido en cookie o cabecera.
    """
    token = extraer_token_de_request(request, creds)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acceso no autorizado: No se encontró cookie de sesión HttpOnly ('token_sesion') ni Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decodificar_token(token)
    user_id = str(payload.get("sub") or payload.get("id") or "ANON")
    email = str(payload.get("email") or "")
    rol = str(payload.get("rol") or "").upper()

    if not rol:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token malformado: No contiene el atributo 'rol' del usuario.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return UsuarioAutenticado(id=user_id, email=email, rol=rol)


def exigir_roles(roles_permitidos: List[str]):
    """
    Generador de dependencias FastAPI para Control de Acceso Basado en Roles (RBAC).
    Verifica que el rol del usuario autenticado pertenezca a la lista de roles autorizados.
    Lanza HTTP 403 Forbidden si el rol es insuficiente.
    """
    roles_upper = [r.upper() for r in roles_permitidos]

    async def validador_rol(
        usuario: UsuarioAutenticado = Depends(get_current_user)
    ) -> UsuarioAutenticado:
        if usuario.rol not in roles_upper:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado: El rol '{usuario.rol}' no tiene permisos para ejecutar esta acción táctica. Roles requeridos: {roles_permitidos}."
            )
        return usuario

    return validador_rol


# Guard oficial para el pipeline de reportes y consola táctica (OPERADOR o ADMINISTRADOR)
validar_operador_guard = exigir_roles(ROLES_TACTICOS_PERMITIDOS)


def crear_token_prueba(
    sub: str = "USR-NAT-01",
    email: str = "nataly.comandos@bomberos.gob.bo",
    rol: str = "OPERADOR",
    exp_seconds: int = 3600
) -> str:
    """
    Genera un token JWT firmado para propósitos de pruebas automatizadas y desarrollo local.
    """
    payload = {
        "sub": sub,
        "email": email,
        "rol": rol,
        "exp": int(time.time()) + exp_seconds
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
