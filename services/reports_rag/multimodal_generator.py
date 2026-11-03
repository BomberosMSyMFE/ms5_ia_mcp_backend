"""
services/reports_rag/multimodal_generator.py
Generador Multimodal de Reportes Tácticos:
1. PDF editorial de alta fidelidad con WeasyPrint y CSS Paged Media.
2. Excel estructurado con OpenPyXL, estilos corporativos y fórmulas automáticas.
3. Audio MP3 con síntesis de voz neural Edge-TTS (es-BO-MarceloNeural).
Semestre 2/2026 - INF512 (Ingeniería de Software II)
Responsable: Nataly Martínez (ms5_ia_mcp_backend)
"""

import io
import logging
from typing import Dict, Any, Optional
import weasyprint
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

logger = logging.getLogger("multimodal_generator")


class MultimodalGenerator:
    """
    Generador de artefactos ejecutivos en múltiples modalidades
    a partir de los datos consolidados y estructurados del RAGEngine.
    """

    def generar_pdf(self, datos_reporte: Dict[str, Any]) -> bytes:
        """
        Compila el reporte a un PDF formal de estándar editorial militar/táctico
        utilizando WeasyPrint y CSS Paged Media.
        """
        id_reporte = datos_reporte.get("id_reporte", "REP-SCZ-001")
        params = datos_reporte.get("parametros")
        cuadrante = getattr(params, "cuadrante", "TODOS")
        fecha = getattr(params, "fecha_solicitud", "2026-11-02 20:00:00")
        comando_voz = getattr(params, "comando_original", datos_reporte.get("instruccion_original", "Comando de voz general"))
        
        metricas = datos_reporte.get("metricas")
        total_agua = getattr(metricas, "total_litros_agua", 0)
        pct_agua = getattr(metricas, "porcentaje_disponibilidad_agua", 0.0)
        camiones_disp = getattr(metricas, "camiones_disponibles", 0)
        camiones_tot = getattr(metricas, "total_camiones", 0)
        hidrantes_op = getattr(metricas, "hidrantes_operativos", 0)
        hidrantes_tot = getattr(metricas, "hidrantes_totales", 0)
        litros_espuma = getattr(metricas, "litros_espuma_disponibles", 0)
        siniestros_act = getattr(metricas, "total_siniestros_activos", 0)
        resumen_radial = datos_reporte.get("resumen_radial", "")

        crudos = datos_reporte.get("datos_crudos", {})
        flota = crudos.get("flota_filtrada", [])
        hidrantes = crudos.get("hidrantes_filtrados", [])
        insumos = crudos.get("insumos", [])

        # Filas de tabla de flota en HTML
        filas_flota_html = ""
        for c in flota:
            badge_class = "badge-success" if c.get("estado") == "DISPONIBLE" else "badge-danger"
            filas_flota_html += f"""
            <tr>
                <td class="font-mono"><strong>{c.get('placa')}</strong></td>
                <td>{c.get('tipo')}</td>
                <td>Cuadrante {c.get('cuadrante')}</td>
                <td class="text-right font-mono">{c.get('agua_actual', 0):,} L</td>
                <td class="text-right font-mono">{c.get('capacidad_max', 0):,} L</td>
                <td class="text-center">{c.get('presion_bomba_bar', 0.0)} bar</td>
                <td class="text-center"><span class="{badge_class}">{c.get('estado')}</span></td>
            </tr>
            """.replace(",", ".")

        # Filas de tabla de hidrantes en HTML
        filas_hidrantes_html = ""
        for h in hidrantes:
            badge_h = "badge-success" if h.get("estado") == "OPERATIVO" else "badge-warning"
            filas_hidrantes_html += f"""
            <tr>
                <td class="font-mono"><strong>{h.get('id')}</strong></td>
                <td>{h.get('direccion')}</td>
                <td>Cuadrante {h.get('cuadrante')}</td>
                <td class="text-right font-mono">{h.get('caudal_lpm', 0):,} L/min</td>
                <td class="text-center">{h.get('presion_bar', 0.0)} bar</td>
                <td class="text-center"><span class="{badge_h}">{h.get('estado')}</span></td>
            </tr>
            """.replace(",", ".")

        # Filas de tabla de insumos en HTML
        filas_insumos_html = ""
        for i in insumos:
            filas_insumos_html += f"""
            <tr>
                <td class="font-mono"><strong>{i.get('id')}</strong></td>
                <td>{i.get('nombre')}</td>
                <td><span class="badge-neutral">{i.get('categoria')}</span></td>
                <td class="text-right font-mono"><strong>{i.get('cantidad', 0):,}</strong> {i.get('unidad')}</td>
                <td>Estación {i.get('estacion')}</td>
            </tr>
            """.replace(",", ".")

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Reporte Táctico - {id_reporte}</title>
    <style>
        @page {{
            size: A4;
            margin: 18mm 14mm 18mm 14mm;
            @top-right {{
                content: "USO OFICIAL TÁCTICO — COMANDO BOMBEROS";
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 7.5pt;
                font-weight: bold;
                color: #8B0000;
                letter-spacing: 0.5px;
            }}
            @bottom-left {{
                content: "SISTEMA INTEGRADO DE BOMBEROS (MS-05 IA CORE)";
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 7pt;
                color: #777777;
            }}
            @bottom-right {{
                content: "Página " counter(page) " de " counter(pages);
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 7.5pt;
                font-weight: bold;
                color: #444444;
            }}
        }}

        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #222222;
            margin: 0;
            padding: 0;
            font-size: 9.5pt;
            line-height: 1.35;
        }}

        .header-container {{
            border-bottom: 2.5px solid #8B0000;
            padding-bottom: 10px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}

        .header-title-box {{
            float: left;
            width: 65%;
        }}

        .header-meta-box {{
            float: right;
            width: 33%;
            text-align: right;
        }}

        .clearfix::after {{
            content: "";
            clear: both;
            display: table;
        }}

        .org-name {{
            font-size: 14pt;
            font-weight: 800;
            color: #8B0000;
            margin: 0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .report-title {{
            font-size: 11pt;
            font-weight: 700;
            color: #1A252C;
            margin: 3px 0 0 0;
        }}

        .badge-id {{
            background-color: #1A252C;
            color: #FFFFFF;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 8pt;
            font-family: monospace;
            font-weight: bold;
            display: inline-block;
        }}

        .badge-secure {{
            background-color: #8B0000;
            color: #FFFFFF;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 7pt;
            font-weight: bold;
            display: inline-block;
            margin-top: 4px;
            text-transform: uppercase;
        }}

        .meta-text {{
            font-size: 8pt;
            color: #555555;
            margin: 2px 0;
        }}

        .callout-box {{
            background-color: #FFF5F5;
            border-left: 4px solid #8B0000;
            padding: 8px 12px;
            margin-bottom: 14px;
            border-radius: 0 4px 4px 0;
        }}

        .callout-title {{
            font-weight: bold;
            color: #8B0000;
            font-size: 8.5pt;
            margin: 0 0 4px 0;
            text-transform: uppercase;
        }}

        .callout-text {{
            font-size: 8.5pt;
            color: #333333;
            margin: 0;
            font-style: italic;
        }}

        .kpi-grid {{
            margin-bottom: 14px;
        }}

        .kpi-col {{
            float: left;
            width: 23.5%;
            margin-right: 2%;
            background-color: #F8F9FA;
            border: 1px solid #E2E8F0;
            border-radius: 5px;
            padding: 8px 6px;
            text-align: center;
            box-sizing: border-box;
        }}

        .kpi-col:last-child {{
            margin-right: 0;
        }}

        .kpi-label {{
            font-size: 7pt;
            font-weight: bold;
            color: #64748B;
            text-transform: uppercase;
            margin-bottom: 3px;
        }}

        .kpi-value {{
            font-size: 13pt;
            font-weight: 800;
            color: #8B0000;
            font-family: monospace;
            margin: 0;
        }}

        .kpi-sub {{
            font-size: 7pt;
            color: #475569;
            margin-top: 2px;
        }}

        .section-header {{
            font-size: 9.5pt;
            font-weight: bold;
            color: #1E293B;
            border-bottom: 1.5px solid #CBD5E1;
            padding-bottom: 3px;
            margin-top: 14px;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8pt;
            margin-bottom: 12px;
        }}

        th {{
            background-color: #8B0000;
            color: #FFFFFF;
            font-weight: bold;
            text-align: left;
            padding: 5px 6px;
            font-size: 7.5pt;
            text-transform: uppercase;
        }}

        td {{
            padding: 4px 6px;
            border-bottom: 1px solid #E2E8F0;
            color: #334155;
        }}

        tr:nth-child(even) td {{
            background-color: #F8FAFC;
        }}

        .font-mono {{
            font-family: monospace;
        }}

        .text-right {{
            text-align: right;
        }}

        .text-center {{
            text-align: center;
        }}

        .badge-success {{
            background-color: #DEF7EC;
            color: #03543F;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 7pt;
            font-weight: bold;
        }}

        .badge-danger {{
            background-color: #FDE8E8;
            color: #9B1C1C;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 7pt;
            font-weight: bold;
        }}

        .badge-warning {{
            background-color: #FEF08A;
            color: #854D0E;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 7pt;
            font-weight: bold;
        }}

        .badge-neutral {{
            background-color: #E2E8F0;
            color: #334155;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 7pt;
        }}

        .signature-section {{
            margin-top: 25px;
            page-break-inside: avoid;
        }}

        .signature-box {{
            float: left;
            width: 45%;
            text-align: center;
            border-top: 1px solid #475569;
            padding-top: 6px;
        }}

        .signature-box:last-child {{
            float: right;
        }}

        .signer-name {{
            font-weight: bold;
            font-size: 8.5pt;
            color: #0F172A;
        }}

        .signer-title {{
            font-size: 7.5pt;
            color: #64748B;
        }}
    </style>
</head>
<body>

    <div class="header-container clearfix">
        <div class="header-title-box">
            <h1 class="org-name">Cuerpo de Bomberos Santa Cruz</h1>
            <h2 class="report-title">Informe Ejecutivo de Disponibilidad y Recursos Tácticos</h2>
            <div class="meta-text"><strong>Sector Operativo:</strong> Cuadrante {cuadrante} | <strong>Fecha Emisión:</strong> {fecha}</div>
        </div>
        <div class="header-meta-box">
            <div class="badge-id">{id_reporte}</div><br>
            <div class="badge-secure">Confidencial Táctico</div>
            <div class="meta-text" style="margin-top:4px;"><strong>Canal:</strong> Comando por Voz</div>
        </div>
    </div>

    <div class="callout-box">
        <div class="callout-title">🎙️ Resumen de Alerta Radial (Texto TTS Inyectado)</div>
        <p class="callout-text">"{resumen_radial}"</p>
    </div>

    <div class="kpi-grid clearfix">
        <div class="kpi-col">
            <div class="kpi-label">Volumen Hídrico</div>
            <div class="kpi-value">{total_agua:,} L</div>
            <div class="kpi-sub">{pct_agua}% Capacidad Total</div>
        </div>
        <div class="kpi-col">
            <div class="kpi-label">Flota Lista</div>
            <div class="kpi-value">{camiones_disp} / {camiones_tot}</div>
            <div class="kpi-sub">Unidades Disponibles</div>
        </div>
        <div class="kpi-col">
            <div class="kpi-label">Red Hidrantes</div>
            <div class="kpi-value">{hidrantes_op} / {hidrantes_tot}</div>
            <div class="kpi-sub">Presurizados Activos</div>
        </div>
        <div class="kpi-col">
            <div class="kpi-label">Espumógeno AFFF</div>
            <div class="kpi-value">{litros_espuma:,} L</div>
            <div class="kpi-sub">Stock Base Central</div>
        </div>
    </div>

    <div class="section-header">1. Estado y Telemetría de Camiones Cisterna y Ataque</div>
    <table>
        <thead>
            <tr>
                <th style="width: 14%;">Placa</th>
                <th style="width: 22%;">Tipo Vehículo</th>
                <th style="width: 16%;">Cuadrante</th>
                <th style="width: 15%; text-align: right;">Agua Actual</th>
                <th style="width: 15%; text-align: right;">Capacidad Máx</th>
                <th style="width: 10%; text-align: center;">Presión</th>
                <th style="width: 13%; text-align: center;">Estado</th>
            </tr>
        </thead>
        <tbody>
            {filas_flota_html}
        </tbody>
    </table>

    <div class="section-header">2. Red de Hidrantes y Presión de Línea</div>
    <table>
        <thead>
            <tr>
                <th style="width: 16%;">Código</th>
                <th style="width: 38%;">Ubicación / Calle</th>
                <th style="width: 14%;">Cuadrante</th>
                <th style="width: 12%; text-align: right;">Caudal</th>
                <th style="width: 10%; text-align: center;">Presión</th>
                <th style="width: 14%; text-align: center;">Operatividad</th>
            </tr>
        </thead>
        <tbody>
            {filas_hidrantes_html}
        </tbody>
    </table>

    <div class="section-header">3. Inventario Crítico de Material Químico y EPP</div>
    <table>
        <thead>
            <tr>
                <th style="width: 20%;">Código Insumo</th>
                <th style="width: 35%;">Descripción del Material</th>
                <th style="width: 15%;">Categoría</th>
                <th style="width: 15%; text-align: right;">Stock Actual</th>
                <th style="width: 15%;">Almacén Base</th>
            </tr>
        </thead>
        <tbody>
            {filas_insumos_html}
        </tbody>
    </table>

    <div class="signature-section clearfix">
        <div class="signature-box">
            <div class="signer-name">Cap. Nataly Martínez</div>
            <div class="signer-title">Comandancia de Operaciones y Crisis</div>
        </div>
        <div class="signature-box">
            <div class="signer-name">Maquinista en Turno</div>
            <div class="signer-title">Oficial de Guardia — Sala de Situación</div>
        </div>
    </div>

</body>
</html>
""".replace(",", ".")

        return weasyprint.HTML(string=html_content).write_pdf()

    def generar_excel(self, datos_reporte: Dict[str, Any]) -> bytes:
        """
        Genera una hoja de cálculo estructurada con OpenPyXL:
        - Hoja 1: Resumen Táctico y Metadatos.
        - Hoja 2: Flota y Camiones con fórmula de autosuma =SUM(...) y estilos rojo oscuro.
        - Hoja 3: Hidrantes e Insumos logísticos.
        """
        id_reporte = datos_reporte.get("id_reporte", "REP-SCZ-001")
        params = datos_reporte.get("parametros")
        cuadrante = getattr(params, "cuadrante", "TODOS")
        fecha = getattr(params, "fecha_solicitud", "2026-11-02 20:00:00")

        metricas = datos_reporte.get("metricas")
        crudos = datos_reporte.get("datos_crudos", {})
        flota = crudos.get("flota_filtrada", [])
        hidrantes = crudos.get("hidrantes_filtrados", [])
        insumos = crudos.get("insumos", [])

        wb = openpyxl.Workbook()
        
        # Paleta táctica Bomberos
        DARK_RED = "8B0000"
        LIGHT_RED = "FDE8E8"
        HEADER_FILL = PatternFill(start_color=DARK_RED, end_color=DARK_RED, fill_type="solid")
        ZEBRA_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        WHITE_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        BOLD_FONT = Font(name="Calibri", size=10, bold=True, color="000000")
        NORMAL_FONT = Font(name="Calibri", size=10, color="000000")
        TITLE_FONT = Font(name="Calibri", size=14, bold=True, color=DARK_RED)
        
        THIN_BORDER = Border(
            left=Side(style='thin', color='D1D5DB'),
            right=Side(style='thin', color='D1D5DB'),
            top=Side(style='thin', color='D1D5DB'),
            bottom=Side(style='thin', color='D1D5DB')
        )
        DOUBLE_BOTTOM = Border(
            left=Side(style='thin', color='D1D5DB'),
            right=Side(style='thin', color='D1D5DB'),
            top=Side(style='thin', color='D1D5DB'),
            bottom=Side(style='double', color='8B0000')
        )

        # ==============================================================
        # HOJA 1: RESUMEN TÁCTICO
        # ==============================================================
        ws1 = wb.active
        ws1.title = "Resumen Táctico"
        ws1.views.sheetView[0].showGridLines = True

        ws1["A1"] = "CUERPO DE BOMBEROS SANTA CRUZ — INFORME EJECUTIVO"
        ws1["A1"].font = TITLE_FONT
        ws1["A2"] = f"Identificador: {id_reporte} | Fecha: {fecha} | Sector: Cuadrante {cuadrante}"
        ws1["A2"].font = Font(name="Calibri", size=9, italic=True, color="4B5563")

        # Tabla de Metadatos
        meta_rows = [
            ("Métrica Clave", "Valor Verificado", "Unidad de Medida", "Evaluación Operativa"),
            ("Volumen Total Agua en Flota", getattr(metricas, "total_litros_agua", 0), "Litros", f"{getattr(metricas, 'porcentaje_disponibilidad_agua', 0)}% Capacidad"),
            ("Camiones Listos para Despacho", getattr(metricas, "camiones_disponibles", 0), "Unidades", f"{getattr(metricas, 'camiones_disponibles', 0)}/{getattr(metricas, 'total_camiones', 0)} Operativos"),
            ("Red de Hidrantes Cuadrante", getattr(metricas, "hidrantes_operativos", 0), "Puntos", f"{getattr(metricas, 'hidrantes_operativos', 0)}/{getattr(metricas, 'hidrantes_totales', 0)} Presurizados"),
            ("Reserva Espumógeno AFFF", getattr(metricas, "litros_espuma_disponibles", 0), "Litros", "Depósito Central Listo"),
            ("Siniestros Activos en Curso", getattr(metricas, "total_siniestros_activos", 0), "Emergencias", "Monitoreo en Sala de Crisis")
        ]

        start_r = 4
        for r_idx, row in enumerate(meta_rows, start=start_r):
            for c_idx, val in enumerate(row, start=1):
                cell = ws1.cell(row=r_idx, column=c_idx, value=val)
                cell.border = THIN_BORDER
                if r_idx == start_r:
                    cell.fill = HEADER_FILL
                    cell.font = WHITE_FONT
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.font = NORMAL_FONT
                    if c_idx == 2 and isinstance(val, (int, float)):
                        cell.number_format = '#,##0'
                        cell.alignment = Alignment(horizontal="right")
                    else:
                        cell.alignment = Alignment(horizontal="left")

        # Auto-width para Hoja 1
        for col in ws1.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws1.column_dimensions[col_letter].width = max(max_len + 3, 15)

        # ==============================================================
        # HOJA 2: FLOTA Y CAMIONES (CON FÓRMULA DE SUMA)
        # ==============================================================
        ws2 = wb.create_sheet(title="Flota y Camiones")
        ws2.views.sheetView[0].showGridLines = True

        ws2["A1"] = f"TELEMETRÍA Y ESTADO DE CAMIONES — CUADRANTE {cuadrante}"
        ws2["A1"].font = TITLE_FONT

        headers_flota = ["ID Camión", "Placa", "Tipo Unidad", "Cuadrante", "Agua Actual (L)", "Capacidad Máx (L)", "Presión (bar)", "Estado"]
        for c_idx, h in enumerate(headers_flota, start=1):
            cell = ws2.cell(row=3, column=c_idx, value=h)
            cell.fill = HEADER_FILL
            cell.font = WHITE_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = THIN_BORDER

        curr_r = 4
        for c in flota:
            row_vals = [
                c.get("id"),
                c.get("placa"),
                c.get("tipo"),
                c.get("cuadrante"),
                c.get("agua_actual", 0),
                c.get("capacidad_max", 0),
                c.get("presion_bomba_bar", 0.0),
                c.get("estado")
            ]
            for c_idx, val in enumerate(row_vals, start=1):
                cell = ws2.cell(row=curr_r, column=c_idx, value=val)
                cell.font = NORMAL_FONT
                cell.border = THIN_BORDER
                if curr_r % 2 == 0:
                    cell.fill = ZEBRA_FILL
                if c_idx in (5, 6):
                    cell.number_format = '#,##0'
                    cell.alignment = Alignment(horizontal="right")
                elif c_idx == 7:
                    cell.number_format = '0.0'
                    cell.alignment = Alignment(horizontal="right")
                elif c_idx == 8:
                    cell.alignment = Alignment(horizontal="center")
            curr_r += 1

        # Fila de Totales con fórmula OpenPyXL
        total_row = curr_r
        ws2.cell(row=total_row, column=1, value="TOTALES").font = BOLD_FONT
        ws2.cell(row=total_row, column=1).alignment = Alignment(horizontal="center")
        ws2.cell(row=total_row, column=1).border = DOUBLE_BOTTOM

        for col_idx in range(2, 5):
            ws2.cell(row=total_row, column=col_idx, value="").border = DOUBLE_BOTTOM

        # Fórmula =SUM(E4:E{curr_r-1})
        cell_sum_agua = ws2.cell(row=total_row, column=5, value=f"=SUM(E4:E{curr_r-1})")
        cell_sum_agua.font = BOLD_FONT
        cell_sum_agua.number_format = '#,##0'
        cell_sum_agua.alignment = Alignment(horizontal="right")
        cell_sum_agua.border = DOUBLE_BOTTOM

        # Fórmula =SUM(F4:F{curr_r-1})
        cell_sum_cap = ws2.cell(row=total_row, column=6, value=f"=SUM(F4:F{curr_r-1})")
        cell_sum_cap.font = BOLD_FONT
        cell_sum_cap.number_format = '#,##0'
        cell_sum_cap.alignment = Alignment(horizontal="right")
        cell_sum_cap.border = DOUBLE_BOTTOM

        ws2.cell(row=total_row, column=7, value="").border = DOUBLE_BOTTOM
        ws2.cell(row=total_row, column=8, value="").border = DOUBLE_BOTTOM

        # Auto-width para Hoja 2
        for col in ws2.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws2.column_dimensions[col_letter].width = max(max_len + 3, 14)

        # ==============================================================
        # HOJA 3: HIDRANTES E INSUMOS
        # ==============================================================
        ws3 = wb.create_sheet(title="Hidrantes e Insumos")
        ws3.views.sheetView[0].showGridLines = True

        ws3["A1"] = "RED DE HIDRANTES"
        ws3["A1"].font = TITLE_FONT

        headers_hidrantes = ["ID", "Dirección", "Cuadrante", "Caudal (L/min)", "Presión (bar)", "Estado"]
        for c_idx, h in enumerate(headers_hidrantes, start=1):
            cell = ws3.cell(row=3, column=c_idx, value=h)
            cell.fill = HEADER_FILL
            cell.font = WHITE_FONT
            cell.alignment = Alignment(horizontal="center")
            cell.border = THIN_BORDER

        r3 = 4
        for h in hidrantes:
            vals = [h.get("id"), h.get("direccion"), h.get("cuadrante"), h.get("caudal_lpm", 0), h.get("presion_bar", 0.0), h.get("estado")]
            for c_idx, val in enumerate(vals, start=1):
                cell = ws3.cell(row=r3, column=c_idx, value=val)
                cell.font = NORMAL_FONT
                cell.border = THIN_BORDER
                if c_idx == 4:
                    cell.number_format = '#,##0'
                    cell.alignment = Alignment(horizontal="right")
            r3 += 1

        r3 += 2
        ws3.cell(row=r3, column=1, value="INVENTARIO DE INSUMOS Y QUÍMICOS").font = TITLE_FONT
        r3 += 2

        headers_insumos = ["ID Insumo", "Descripción Material", "Categoría", "Stock Disponible", "Unidad", "Estación"]
        for c_idx, hi in enumerate(headers_insumos, start=1):
            cell = ws3.cell(row=r3, column=c_idx, value=hi)
            cell.fill = HEADER_FILL
            cell.font = WHITE_FONT
            cell.alignment = Alignment(horizontal="center")
            cell.border = THIN_BORDER
        r3 += 1

        for ins in insumos:
            vals = [ins.get("id"), ins.get("nombre"), ins.get("categoria"), ins.get("cantidad", 0), ins.get("unidad"), ins.get("estacion")]
            for c_idx, val in enumerate(vals, start=1):
                cell = ws3.cell(row=r3, column=c_idx, value=val)
                cell.font = NORMAL_FONT
                cell.border = THIN_BORDER
                if c_idx == 4:
                    cell.number_format = '#,##0'
                    cell.alignment = Alignment(horizontal="right")
            r3 += 1

        # Auto-width para Hoja 3
        for col in ws3.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws3.column_dimensions[col_letter].width = max(max_len + 3, 14)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    async def generar_audio_tts(self, texto_briefing: str, voice: str = "es-BO-MarceloNeural") -> bytes:
        """
        Genera el audio en formato MP3 con Edge-TTS para lectura por radio.
        Utiliza es-BO-MarceloNeural (español boliviano) para realismo local.
        """
        import edge_tts
        try:
            communicate = edge_tts.Communicate(texto_briefing, voice=voice)
            audio_buffer = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.extend(chunk["data"])
            
            logger.info(f"Audio TTS sintetizado con éxito ({len(audio_buffer)} bytes) con voz '{voice}'")
            return bytes(audio_buffer)
        except Exception as e:
            logger.error(f"Error generando audio TTS con Edge-TTS: {e}")
            # Retorno de bytes vacíos ante fallos de conexión externa
            return b""


multimodal_generator_default = MultimodalGenerator()
