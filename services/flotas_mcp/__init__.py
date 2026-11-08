"""
services/flotas_mcp/__init__.py
Servidor MCP de Operaciones de Flotas y Recursos Hídricos.
Autor: Maikol (MS-02 Flotas & MS-05 IA Core)
"""

from .bomberos_flotas_mcp import (
    consultar_unidades_cercanas,
    verificar_hidrantes_cercanos,
    calcular_tiempo_llegada,
    proponer_orden_despacho,
    mcp_flotas
)

__all__ = [
    "consultar_unidades_cercanas",
    "verificar_hidrantes_cercanos",
    "calcular_tiempo_llegada",
    "proponer_orden_despacho",
    "mcp_flotas"
]
