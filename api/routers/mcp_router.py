"""
api/routers/mcp_router.py
Router FastAPI para el Servidor MCP (Model Context Protocol) y Capa Defensiva AST:
- Auditoría sintáctica de SQL generado por IA / Agentes (sqlglot)
- Bloqueo de inyecciones destructivas (DROP, TRUNCATE, UPDATE, DELETE, etc.)
- Ejecución segura con transacción forzada READ ONLY
- Catálogo e invocación de herramientas MCP tipadas
Semestre 2/2026 - INF512 (Ingeniería de Software II)
Responsable: Nataly Martínez (ms5_ia_mcp_backend)
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from services.mcp_security.ast_validator import validar_consulta_ast, ASTValidator
from services.mcp_security.mcp_server import (
    CATALOGO_HERRAMIENTAS_MCP,
    verificar_hidrantes_cercanos,
    consultar_stock_estacion,
    consultar_camiones_disponibles,
    ejecutar_consulta_analitica_segura,
    ConsultaAnaliticaInput,
    HidrantesInput,
    StockInput,
    CamionesInput
)

mcp_router = APIRouter(prefix="/api/v1/mcp", tags=["Seguridad AST y Servidor FastMCP"])


class ValidarSQLInputDTO(BaseModel):
    sql: str = Field(..., description="Sentencia SQL a auditar mediante el parser sintáctico AST")


class EjecutarHerramientaGenericaDTO(BaseModel):
    parametros: Dict[str, Any] = Field(default_factory=dict, description="Argumentos tipados de la herramienta")


@mcp_router.post(
    "/validar-sql",
    summary="Auditar sentencia SQL con el Parser Sintáctico AST (sqlglot)",
    description="Valida que la consulta sea exclusivamente un SELECT de solo lectura, bloqueando tokens destructivos y schemas restringidos."
)
async def auditar_sql_ast(payload: ValidarSQLInputDTO):
    if not payload.sql or not payload.sql.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La sentencia SQL a auditar no puede estar vacía."
        )

    resultado = validar_consulta_ast(payload.sql.strip())
    return {
        "valido": resultado.valido,
        "tipo_sentencia": resultado.tipo_sentencia,
        "motivo_rechazo": resultado.motivo_rechazo,
        "tablas_detectadas": resultado.tablas_detectadas,
        "arbol_ast_simplificado": resultado.arbol_ast_simplificado,
        "sql_sanitizado": resultado.sql_sanitizado,
        "transaccion_recomendada": ASTValidator.forzar_transaccion_solo_lectura()
    }


@mcp_router.post(
    "/ejecutar-sql-seguro",
    summary="Ejecutar consulta analítica protegida por AST",
    description="Inspecciona el AST con sqlglot. Si es 100% segura, se ejecuta dentro del contexto READ ONLY de la base de datos."
)
async def ejecutar_sql_seguro(payload: ConsultaAnaliticaInput):
    resultado = ejecutar_consulta_analitica_segura(payload.consulta_sql.strip())
    if not resultado.get("exito"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "INYECCION_O_SENTENCIA_NO_PERMITIDA",
                "motivo": resultado.get("error_seguridad"),
                "tipo_sentencia": resultado.get("tipo_sentencia"),
                "sql_rechazado": resultado.get("sql_rechazado")
            }
        )
    return resultado


@mcp_router.get(
    "/herramientas",
    summary="Catálogo de herramientas MCP disponibles",
    description="Lista el catálogo de funciones MCP registradas con sus esquemas JSON Schema para agentes cognitivos."
)
async def listar_herramientas_mcp():
    return {
        "protocolo": "Model Context Protocol (MCP) - Bomberos Santa Cruz",
        "total_herramientas": len(CATALOGO_HERRAMIENTAS_MCP),
        "herramientas": CATALOGO_HERRAMIENTAS_MCP
    }


@mcp_router.post(
    "/herramientas/{tool_name}/ejecutar",
    summary="Invocar una herramienta MCP de forma tipada y segura",
    description="Ejecuta la función MCP solicitada pasando los parámetros auditados."
)
async def invocar_herramienta_mcp(tool_name: str, payload: EjecutarHerramientaGenericaDTO):
    params = payload.parametros

    if tool_name == "verificar_hidrantes_cercanos":
        try:
            validado = HidrantesInput(**params)
            datos = verificar_hidrantes_cercanos(
                latitud=validado.latitud,
                longitud=validado.longitud,
                radio_metros=validado.radio_metros
            )
            return {"herramienta": tool_name, "exito": True, "resultados": datos}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Parámetros inválidos para {tool_name}: {str(e)}")

    elif tool_name == "consultar_stock_estacion":
        try:
            validado = StockInput(**params)
            datos = consultar_stock_estacion(
                nombre_estacion=validado.nombre_estacion,
                categoria=validado.categoria
            )
            return {"herramienta": tool_name, "exito": True, "resultados": datos}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Parámetros inválidos para {tool_name}: {str(e)}")

    elif tool_name == "consultar_camiones_disponibles":
        try:
            validado = CamionesInput(**params)
            datos = consultar_camiones_disponibles(cuadrante=validado.cuadrante or "TODOS")
            return {"herramienta": tool_name, "exito": True, "resultados": datos}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Parámetros inválidos para {tool_name}: {str(e)}")

    elif tool_name == "ejecutar_consulta_analitica_segura":
        try:
            validado = ConsultaAnaliticaInput(**params)
            res = ejecutar_consulta_analitica_segura(validado.consulta_sql)
            if not res.get("exito"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "INYECCION_O_SENTENCIA_NO_PERMITIDA",
                        "motivo": res.get("error_seguridad")
                    }
                )
            return {"herramienta": tool_name, "exito": True, "resultados": res}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Error en consulta analítica: {str(e)}")

    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Herramienta MCP '{tool_name}' no encontrada en el catálogo."
        )
