"""
services/mcp_security/ast_validator.py
Validador sintáctico AST defensivo (Anti-SQL Injection) utilizando sqlglot.
Semestre 2/2026 - INF512 (Ingeniería de Software II)
Responsable: Nataly Martínez (ms5_ia_mcp_backend)
"""

from typing import Set, List, Optional
from pydantic import BaseModel
import sqlglot
from sqlglot import exp

TABLAS_PERMITIDAS_DEFAULT: Set[str] = {
    "hidrantes",
    "camiones",
    "insumos",
    "stock",
    "estaciones",
    "incidentes",
    "tb_incidentes_emergencia",
    "tb_despachos_tacticos",
    "tb_historial_incidente",
    "recursos_bomberos",
    "cuadrantes_operativos",
    # Tablas de Inventario y Recursos (MS-03 PostgreSQL)
    "suministros_quimicos",
    "kits_epp",
    "herramientas_equipos",
    "estaciones_inventario",
    "movimientos_inventario",
    "transacciones_saga_inventario",
}

TOKENS_MODIFICACION_PROHIBIDOS: Set[str] = {
    "DROP",
    "TRUNCATE",
    "UPDATE",
    "DELETE",
    "ALTER",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "INSERT",
    "CREATE",
    "REPLACE",
    "MERGE",
    "UPSERT",
}

TABLAS_SISTEMA_PROHIBIDAS: Set[str] = {
    "pg_catalog",
    "information_schema",
    "sqlite_master",
    "sys",
    "mysql",
    "usuarios",
    "tb_usuarios_sso",
    "passwords",
    "credenciales",
}


class ASTValidationResult(BaseModel):
    valido: bool
    motivo_rechazo: Optional[str] = None
    tipo_sentencia: Optional[str] = None
    tablas_detectadas: List[str] = []
    sql_sanitizado: Optional[str] = None
    es_solo_lectura: bool = False
    arbol_ast_simplificado: Optional[str] = None


class ASTValidator:
    """
    Capa de Seguridad Defensiva (Capa 2 de Defensa en Profundidad).
    Audita y valida consultas Text-to-SQL generadas por voz o herramientas MCP.
    """

    def __init__(self, tablas_permitidas: Optional[Set[str]] = None):
        self.tablas_permitidas = {t.lower() for t in (tablas_permitidas or TABLAS_PERMITIDAS_DEFAULT)}

    def validar(self, sql_query: str) -> ASTValidationResult:
        if not sql_query or not sql_query.strip():
            return ASTValidationResult(
                valido=False,
                motivo_rechazo="Consulta SQL vacía o nula.",
            )

        query_limpia = sql_query.strip()

        # 1. Chequeo Léxico Rápido: Detección de Tokens Destructivos
        tokens_en_query = {word.strip(";(),").upper() for word in query_limpia.split()}
        tokens_encontrados = tokens_en_query.intersection(TOKENS_MODIFICACION_PROHIBIDOS)
        if tokens_encontrados:
            return ASTValidationResult(
                valido=False,
                motivo_rechazo=(
                    f"Intento de modificación destructiva detectado. "
                    f"Tokens no permitidos: {list(tokens_encontrados)}"
                ),
                tipo_sentencia="DESTRUCTIVE_TOKEN",
            )

        # 2. Análisis del Árbol Sintáctico (AST) con sqlglot
        try:
            arboles = sqlglot.parse(query_limpia)
        except Exception as e:
            return ASTValidationResult(
                valido=False,
                motivo_rechazo=f"Error léxico/sintáctico en la consulta SQL: {str(e)}",
                tipo_sentencia="SYNTAX_ERROR",
            )

        if not arboles:
            return ASTValidationResult(
                valido=False,
                motivo_rechazo="No se pudo construir un árbol sintáctico válido.",
            )

        # 3. Bloqueo de Sentencias Múltiples (Inyección por punto y coma ';')
        if len(arboles) > 1:
            return ASTValidationResult(
                valido=False,
                motivo_rechazo="Múltiples sentencias SQL detectadas. Prohibido el uso de ';' para apilar comandos.",
                tipo_sentencia="MULTI_STATEMENT",
            )

        expresion = arboles[0]

        # 4. Lista blanca estricta: Solo se permiten sentencias SELECT
        if not isinstance(expresion, exp.Select):
            nombre_nodo = type(expresion).__name__
            return ASTValidationResult(
                valido=False,
                motivo_rechazo=f"Tipo de sentencia no autorizado: '{nombre_nodo}'. Solo se permiten sentencias SELECT.",
                tipo_sentencia=nombre_nodo,
            )

        # 5. Detección y Validación de Tablas Consultadas
        tablas_consultadas = {t.name.lower() for t in expresion.find_all(exp.Table) if t.name}

        # 5.1 Bloquear acceso a tablas del sistema o credenciales
        tablas_restringidas = tablas_consultadas.intersection(TABLAS_SISTEMA_PROHIBIDAS)
        if tablas_restringidas:
            return ASTValidationResult(
                valido=False,
                motivo_rechazo=f"Acceso denegado a tablas protegidas o de credenciales: {list(tablas_restringidas)}",
                tipo_sentencia="SELECT",
                tablas_detectadas=list(tablas_consultadas),
            )

        # 5.2 Validar contra lista blanca de tablas permitidas
        if not tablas_consultadas.issubset(self.tablas_permitidas):
            no_autorizadas = tablas_consultadas.difference(self.tablas_permitidas)
            return ASTValidationResult(
                valido=False,
                motivo_rechazo=f"Tablas fuera de la lista blanca permitida: {list(no_autorizadas)}",
                tipo_sentencia="SELECT",
                tablas_detectadas=list(tablas_consultadas),
            )

        # 6. Éxito: Consulta de solo lectura válida
        sql_normalizado = expresion.sql(dialect="postgres")
        return ASTValidationResult(
            valido=True,
            tipo_sentencia="SELECT",
            tablas_detectadas=sorted(list(tablas_consultadas)),
            sql_sanitizado=sql_normalizado,
            es_solo_lectura=True,
            arbol_ast_simplificado=f"{expresion.key.upper()}(from={list(tablas_consultadas)})"
        )

    @staticmethod
    def forzar_transaccion_solo_lectura() -> str:
        """
        Retorna la sentencia SQL que fuerza a nivel de sesión o transacción el modo READ ONLY.
        Capa 3 de Defensa en Profundidad.
        """
        return "SET TRANSACTION READ ONLY;"


# Instancia por defecto lista para uso global
ast_validator_default = ASTValidator()


def validar_consulta_ast(sql_query: str, tablas_permitidas: Optional[Set[str]] = None) -> ASTValidationResult:
    """Función de acceso directo para validar una consulta SQL."""
    if tablas_permitidas:
        return ASTValidator(tablas_permitidas).validar(sql_query)
    return ast_validator_default.validar(sql_query)
