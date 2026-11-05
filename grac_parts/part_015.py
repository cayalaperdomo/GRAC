GDPR_INSTRUMENTO_TEMPLATE_XLSX = os.path.join(
    app.root_path,
    "static",
    "templates",
    "ISO27701_GDPR_Matriz.xlsx"
)

# Escala de evaluación: igual a NIST CSF 2.0
# SI=100, PARCIAL=50, NO=0, NA no participa del denominador.
GDPR_STATUS_SCORE = {
    "SI": 100,
    "PARCIAL": 50,
    "NO": 0,
    "NA": None,
}

# Se reutiliza exactamente el mismo criterio de niveles del módulo NIST.
GDPR_MADUREZ_LEVELS = [
    {
        "nivel": "Nivel 1: Ejecutado (Performed)",
        "descripcion": "La organización puede llevar a cabo prácticas de protección de datos de manera ad hoc.",
        "score": 1,
        "rango_pct": "0% – 20%",
        "logica": "Prácticas ad hoc"
    },
    {
        "nivel": "Nivel 2: Documentado (Documented)",
        "descripcion": "La organización ha establecido y documentado prácticas relacionadas con protección de datos personales.",
        "score": 2,
        "rango_pct": "21% – 40%",
        "logica": "Existe documentación"
    },
    {
        "nivel": "Nivel 3: Gestionado (Managed)",
        "descripcion": "La organización revisa el cumplimiento de los controles y asigna recursos adecuados para mantener el programa de protección de datos.",
        "score": 3,
        "rango_pct": "41% – 60%",
        "logica": "Se revisa cumplimiento"
    },
    {
        "nivel": "Nivel 4: Gestionado Cuantitativamente (Quantitatively Managed)",
        "descripcion": "La organización mide la efectividad del programa de protección de datos y ejecuta acciones correctivas cuando corresponde.",
        "score": 4,
        "rango_pct": "61% – 80%",
        "logica": "Se mide efectividad"
    },
    {
        "nivel": "Nivel 5: Optimizado (Optimizing)",
        "descripcion": "La organización ha institucionalizado la mejora continua y optimiza transversalmente sus prácticas de protección de datos personales.",
        "score": 5,
        "rango_pct": "81% – 100%",
        "logica": "Mejora continua institucionalizada"
    },
]

# =====================================================================
# HELPERS
# =====================================================================


GDPR_CODE_RE = re.compile(r"^\s*(\d+(?:\.\d+)+)\s*(.*)$")

# =====================================================================
# INFORME EJECUTIVO AI — PROTECCIÓN DE DATOS PERSONALES
# =====================================================================

def _gdpr_prompt_informe_ejecutivo(run: "DatosMadurezRun", resumen: dict) -> str:
    partes = []

    for dominio, data in (resumen or {}).items():
        try:
            pct = float(data.get("pct", 0) or 0)
        except Exception:
            pct = 0.0

        total = int(data.get("total", 0) or 0)
        brecha = max(0.0, 100.0 - pct)

        items = data.get("items", []) or []
        si = 0
        parcial = 0
        no = 0
        na = 0

        for it in items:
            st = (it.get("estado") or "").strip().upper()
            if st == "SI":
                si += 1
            elif st == "PARCIAL":
                parcial += 1
            elif st == "NO":
                no += 1
            elif st == "NA":
                na += 1

        nivel = gdpr_nivel_visual_por_pct(pct).get("nivel", "")

        partes.append(
            f"- Dominio: {dominio}\n"
            f"  * Cumplimiento: {pct:.2f}%\n"
            f"  * Brecha: {brecha:.2f}%\n"
            f"  * Nivel: {nivel}\n"
            f"  * Total ítems: {total}\n"
            f"  * SI: {si} | PARCIAL: {parcial} | NO: {no} | NA: {na}"
        )

    detalle = "\n".join(partes)

    return f"""
Eres un consultor senior en privacidad, gobierno de datos y cumplimiento GDPR / PIMS. Debes redactar un INFORME EJECUTIVO para alta dirección, claro, breve, profesional y accionable, basado en una evaluación de madurez de protección de datos personales.

DATOS GENERALES
- Consecutivo: {run.consecutivo}
- Cumplimiento general: {run.pct_general:.2f}%
- Nivel general: {gdpr_nivel_visual_por_pct(run.pct_general).get("nivel","")}

RESULTADOS POR DOMINIO
{detalle}

INSTRUCCIONES
1. Devuelve solamente JSON válido.
2. Debes devolver exactamente esta estructura:
{{
  "informe_ejecutivo": "texto"
}}

REGLAS DEL TEXTO:
- Escribe en español.
- Extensión aproximada: 4 a 7 párrafos cortos.
- Incluye:
  a) resumen general del nivel de madurez,
  b) fortalezas principales,
  c) brechas principales,
  d) dominios más débiles,
  e) riesgos ejecutivos si no se actúa,
  f) prioridades recomendadas para los próximos 90 días.
- No inventes herramientas específicas.
- Usa un tono ejecutivo, no técnico en exceso.
- No uses markdown ni viñetas; redacta como informe.
""".strip()

def _gdpr_prompt_plan_trabajo(run: "DatosMadurezRun", resumen: dict) -> str:
    partes = []

    for dominio, data in (resumen or {}).items():
        try:
            pct = float(data.get("pct", 0) or 0)
        except Exception:
            pct = 0.0

        total = int(data.get("total", 0) or 0)
        brecha = max(0.0, 100.0 - pct)

        items = data.get("items", []) or []
        si = 0
        parcial = 0
        no = 0
        na = 0

        for it in items:
            st = (it.get("estado") or "").strip().upper()
            if st == "SI":
                si += 1
            elif st == "PARCIAL":
                parcial += 1
            elif st == "NO":
                no += 1
            elif st == "NA":
                na += 1

        partes.append(
            f"- Dominio: {dominio}\n"
            f"  * Cumplimiento: {pct:.2f}%\n"
            f"  * Brecha: {brecha:.2f}%\n"
            f"  * Total ítems: {total}\n"
            f"  * SI: {si} | PARCIAL: {parcial} | NO: {no} | NA: {na}"
        )

    detalle = "\n".join(partes)

    return f"""
Eres un consultor senior en privacidad, protección de datos personales, GDPR y programas PIMS.
Debes construir un PLAN DE TRABAJO GENERAL para cerrar brechas de cumplimiento.

DATOS GENERALES
- Consecutivo: {run.consecutivo}
- Cumplimiento general: {run.pct_general:.2f}%
- Nivel general: {gdpr_nivel_visual_por_pct(run.pct_general).get("nivel","")}

RESULTADOS POR DOMINIO
{detalle}

INSTRUCCIONES
1. Devuelve solamente JSON válido.
2. Debes devolver exactamente esta estructura:
{{
  "plan_trabajo": [
    {{
      "frente": "string",
      "actividad": "string",
      "prioridad": "Alta|Media|Baja",
      "responsable_sugerido": "string",
      "plazo": "string",
      "entregable": "string"
    }}
  ]
}}

REGLAS
- Genera entre 8 y 15 actividades.
- Prioriza primero los dominios con menor cumplimiento.
- Usa lenguaje ejecutivo y accionable.
- No inventes herramientas específicas.
""".strip()

# =====================================================================
# HELPERS IA EXCLUSIVOS — PROTECCIÓN DE DATOS PERSONALES
# No tocan Ollama ni el helper global _ai_text
# =====================================================================

def _gdpr_extraer_json_objeto(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        return {}

    # Limpia fences tipo ```json ... ```
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except Exception:
        pass

    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end+1])
    except Exception:
        pass

    return {}


def _gdpr_ai_text_openrouter(prompt: str, max_tokens: int = 1200) -> str:
    """
    Helper exclusivo para el módulo de Protección de Datos Personales.
    Usa SOLO OpenRouter.
    No toca Ollama ni el helper global _ai_text.
    """
    api_key = get_openrouter_api_key()
    if not api_key:
        raise RuntimeError("No hay OpenRouter API Key configurada. Ve a Administración → OpenRouter API Key.")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    max_tokens_safe = max(400, min(int(max_tokens or 1200), 2200))

    resp = client.chat.completions.create(
        model="deepseek/deepseek-chat",
        temperature=0.2,
        max_tokens=max_tokens_safe,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un consultor senior en privacidad, protección de datos personales, GDPR y PIMS. "
                    "Debes responder únicamente con JSON válido, sin markdown, sin comentarios "
                    "y sin texto adicional antes o después del JSON."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
    )

    texto = (resp.choices[0].message.content or "").strip()

    print(f"DEBUG GDPR OPENROUTER - longitud respuesta: {len(texto)}")
    print(f"DEBUG GDPR OPENROUTER - preview: {texto[:500]}")

    if not texto:
        raise RuntimeError("OpenRouter respondió sin contenido.")

    return texto


def _gdpr_plan_trabajo_a_texto(plan_list) -> str:
    if not isinstance(plan_list, list):
        return ""

    lines = []
    for i, it in enumerate(plan_list, start=1):
        if not isinstance(it, dict):
            continue

        frente = (it.get("frente") or "").strip()
        actividad = (it.get("actividad") or "").strip()
        prioridad = (it.get("prioridad") or "").strip()
        responsable = (it.get("responsable_sugerido") or "").strip()
        plazo = (it.get("plazo") or "").strip()
        entregable = (it.get("entregable") or "").strip()

        lines.append(
            f"{i}. Frente: {frente or 'Sin definir'}\n"
            f"   Actividad: {actividad or 'Sin definir'}\n"
            f"   Prioridad: {prioridad or 'Sin definir'}\n"
            f"   Responsable sugerido: {responsable or 'Sin definir'}\n"
            f"   Plazo: {plazo or 'Sin definir'}\n"
            f"   Entregable: {entregable or 'Sin definir'}"
        )

    return "\n\n".join(lines).strip()

def _gdpr_normalizar_texto_plano_guardado(texto: str) -> str:
    """
    Limpia texto guardado para Datos Personales:
    - extrae JSON si viene {"informe_ejecutivo": "..."} o {"plan_trabajo": "..."}
    - quita ```json
    - convierte <br> a saltos reales
    - elimina HTML
    - elimina títulos generados por Ollama como **INFORME EJECUTIVO**
    """
    txt = (texto or "").strip()
    if not txt:
        return ""

    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = html.unescape(txt)
    txt = txt.replace("```json", "").replace("```", "").strip()

    # Si viene como JSON, extraer texto principal
    try:
        obj = json.loads(txt)
        if isinstance(obj, dict):
            val = (
                obj.get("informe_ejecutivo")
                or obj.get("plan_trabajo")
                or obj.get("texto")
                or ""
            )
            if isinstance(val, list):
                val = _gdpr_plan_trabajo_a_texto(val)
            if isinstance(val, str) and val.strip():
                txt = val.strip()
    except Exception:
        try:
            start = txt.find("{")
            end = txt.rfind("}")
            if start != -1 and end != -1 and end > start:
                obj = json.loads(txt[start:end+1])
                if isinstance(obj, dict):
                    val = (
                        obj.get("informe_ejecutivo")
                        or obj.get("plan_trabajo")
                        or obj.get("texto")
                        or ""
                    )
                    if isinstance(val, list):
                        val = _gdpr_plan_trabajo_a_texto(val)
                    if isinstance(val, str) and val.strip():
                        txt = val.strip()
        except Exception:
            pass

    txt = html.unescape(txt)

    # Convertir <br> a saltos reales y quitar tags HTML
    txt = re.sub(r"<\s*br\s*/?\s*>", "\n", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", "", txt)

    # Quitar restos de JSON mal guardado
    txt = re.sub(r'^\s*\{\s*"?informe_ejecutivo"?\s*:\s*"?', "", txt, flags=re.IGNORECASE)
    txt = re.sub(r'^\s*\{\s*"?plan_trabajo"?\s*:\s*"?', "", txt, flags=re.IGNORECASE)
    txt = re.sub(r'"?\s*\}\s*$', "", txt)

    # Quitar títulos que Ollama suele agregar
    patrones_titulos = [
        r"^\s*\*{1,3}\s*INFORME\s+EJECUTIVO\s*\*{1,3}\s*[:\-–—]?\s*",
        r"^\s*#{1,6}\s*INFORME\s+EJECUTIVO\s*[:\-–—]?\s*",
        r"^\s*INFORME\s+EJECUTIVO\s*[:\-–—]?\s*",
        r"^\s*\*{1,3}\s*RESUMEN\s+EJECUTIVO\s*\*{1,3}\s*[:\-–—]?\s*",
        r"^\s*#{1,6}\s*RESUMEN\s+EJECUTIVO\s*[:\-–—]?\s*",
        r"^\s*RESUMEN\s+EJECUTIVO\s*[:\-–—]?\s*",
        r"^\s*\*{1,3}\s*PLAN\s+DE\s+TRABAJO\s*\*{1,3}\s*[:\-–—]?\s*",
        r"^\s*#{1,6}\s*PLAN\s+DE\s+TRABAJO\s*[:\-–—]?\s*",
        r"^\s*PLAN\s+DE\s+TRABAJO\s*[:\-–—]?\s*",
    ]

    for patron in patrones_titulos:
        txt = re.sub(patron, "", txt, flags=re.IGNORECASE).strip()

    # Quitar markdown residual
    txt = txt.replace("**", "").replace("__", "")

    txt = re.sub(r"[ \t]+\n", "\n", txt)
    txt = re.sub(r"\n[ \t]+", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)

    return txt.strip()

def _gdpr_plan_accion_a_texto(plan_list) -> str:
    if not isinstance(plan_list, list):
        return ""

    lines = []
    for i, it in enumerate(plan_list, start=1):
        if not isinstance(it, dict):
            continue

        accion = (it.get("accion") or "").strip()
        prioridad = (it.get("prioridad") or "").strip()
        responsable = (it.get("responsable_sugerido") or "").strip()
        plazo = (it.get("plazo") or "").strip()
        evidencia = (it.get("evidencia_esperada") or "").strip()

        lines.append(
            f"{i}. Acción: {accion or 'Sin definir'}\n"
            f"   Prioridad: {prioridad or 'Sin definir'}\n"
            f"   Responsable sugerido: {responsable or 'Sin definir'}\n"
            f"   Plazo: {plazo or 'Sin definir'}\n"
            f"   Evidencia esperada: {evidencia or 'Sin definir'}"
        )

    return "\n\n".join(lines).strip()

def _extraer_json_objeto(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        return {}

    try:
        return json.loads(raw)
    except Exception:
        pass

    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end+1])
    except Exception:
        pass

    return {}

def _gdpr_parse_rango_pct(rango: str):
    if not rango:
        return None, None
    s = rango.replace("%", "").strip().replace("–", "-")
    parts = [p.strip() for p in s.split("-")]
    if len(parts) != 2:
        return None, None
    try:
        return float(parts[0]), float(parts[1])
    except Exception:
        return None, None


def gdpr_nivel_visual_por_pct(pct: float):
    try:
        p = float(pct)
    except Exception:
        p = 0.0

    p = max(0.0, min(100.0, p))

    for lvl in GDPR_MADUREZ_LEVELS:
        lo, hi = _gdpr_parse_rango_pct(lvl.get("rango_pct", ""))
        if lo is None or hi is None:
            continue
        if lo <= p <= hi:
            score = lvl.get("score", 0)
            color_map = {
                1: "#dc3545",
                2: "#fd7e14",
                3: "#ffc107",
                4: "#0d6efd",
                5: "#198754",
            }
            return {
                "nivel": lvl.get("nivel", "Sin nivel"),
                "score": score,
                "descripcion": lvl.get("descripcion", ""),
                "color": color_map.get(score, "#6c757d")
            }

    return {
        "nivel": "Sin nivel",
        "score": 0,
        "descripcion": "",
        "color": "#6c757d"
    }


def calcular_progreso_datos(preguntas, form_data=None, respuestas_db=None):
    total = len(preguntas)
    respondidas = 0

    for q in preguntas:
        estado = ""
        if form_data is not None:
            estado = (form_data.get(f"st_{q.id}") or "").strip().upper()
        elif respuestas_db is not None:
            estado = (respuestas_db.get(q.id, {}).get("estado") or "").strip().upper()

        if estado in ("SI", "PARCIAL", "NO", "NA"):
            respondidas += 1

    pct = int(round((respondidas / total) * 100)) if total > 0 else 0
    return respondidas, total, pct


def obtener_borrador_datos(user_id):
    if not user_id:
        return None

    return (
        DatosMadurezRun.query
        .filter(
            DatosMadurezRun.user_id == user_id,
            DatosMadurezRun.estado == "BORRADOR"
        )
        .order_by(DatosMadurezRun.updated_at.desc(), DatosMadurezRun.id.desc())
        .first()
    )


def cargar_respuestas_datos(run_id):
    out = {}
    if not run_id:
        return out

    rows = DatosMadurezRespuesta.query.filter_by(run_id=run_id).all()
    for r in rows:
        out[r.pregunta_id] = {
            "estado": (r.estado or "").strip().upper(),
            "comentario": (r.comentario or "").strip()
        }
    return out


def _es_fila_totalmente_vacia(ws, row_idx, max_cols=9):
    for c in range(1, max_cols + 1):
        v = ws.cell(row_idx, c).value
        if v is not None and str(v).strip() != "":
            return False
    return True


def _normalizar_titulo(t: str) -> str:
    t = (t or "").strip()
    t = re.sub(r"\s+", " ", t)
    return t

def _gdpr_construir_radar_fig(resumen: dict):
    """
    Construye la figura radar y la retorna como objeto matplotlib Figure.
    Sirve para HTML (base64) y para PDF (bytes PNG).
    """
    try:
        if not resumen or not isinstance(resumen, dict):
            return None

        items = []
        for dominio, data in resumen.items():
            try:
                pct = float(data.get("pct", 0) or 0)
            except Exception:
                pct = 0.0

            pct = max(0.0, min(100.0, pct))
            items.append((str(dominio), pct))

        if not items:
            return None

        items.sort(key=lambda x: x[1], reverse=True)

        def acortar_label(txt: str, max_len: int = 16) -> str:
            txt = (txt or "").strip()
            if len(txt) <= max_len:
                return txt
            return txt[:max_len - 3] + "..."

        labels = [f"{acortar_label(dom)}\n({int(round(pct))}%)" for dom, pct in items]
        values = [pct for _, pct in items]

        labels_plot = labels[:]
        values_plot = values[:]

        if len(labels_plot) == 1:
            labels_plot = [labels_plot[0], labels_plot[0], labels_plot[0]]
            values_plot = [values_plot[0], values_plot[0], values_plot[0]]
        elif len(labels_plot) == 2:
            labels_plot = [labels_plot[0], labels_plot[1], labels_plot[0]]
            values_plot = [values_plot[0], values_plot[1], values_plot[0]]

        n = len(labels_plot)
        angles = [i / float(n) * 2 * math.pi for i in range(n)]
        angles_closed = angles + angles[:1]
        values_closed = values_plot + values_plot[:1]

        fig = plt.figure(figsize=(10.5, 8.5), dpi=150)
        ax = plt.subplot(111, polar=True)

        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_position([0.18, 0.16, 0.64, 0.64])

        ax.set_xticks(angles)
        ax.set_xticklabels(labels_plot, fontsize=9, fontweight="bold")
        ax.tick_params(axis="x", pad=36)

        for label, angle in zip(ax.get_xticklabels(), angles):
            angle_deg = (angle * 180 / math.pi) % 360

            if angle_deg == 90 or angle_deg == 270:
                label.set_horizontalalignment("center")
            elif 90 < angle_deg < 270:
                label.set_horizontalalignment("right")
            else:
                label.set_horizontalalignment("left")

            label.set_verticalalignment("center")

        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=9)
        ax.set_rlabel_position(90)

        ax.grid(alpha=0.25, linewidth=0.8)
        ax.spines["polar"].set_alpha(0.18)

        ax.plot(angles_closed, values_closed, linewidth=3.0)
        ax.fill(angles_closed, values_closed, alpha=0.25)
        ax.scatter(angles, values_plot, s=35, zorder=3)

        return fig

    except Exception as e:
        print(f"[Radar Datos Personales] Error construyendo radar: {e}")
        return None

def generar_radar_datos_base64(resumen: dict) -> str | None:
    try:
        fig = _gdpr_construir_radar_fig(resumen)
        if fig is None:
            return None

        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            bbox_inches="tight",
            transparent=False,
            pad_inches=0.45
        )
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    except Exception as e:
        print(f"[Radar Datos Personales] Error generando radar base64: {e}")
        return None


def generar_radar_datos_png_bytes(resumen: dict) -> bytes | None:
    try:
        fig = _gdpr_construir_radar_fig(resumen)
        if fig is None:
            return None

        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            bbox_inches="tight",
            transparent=False,
            facecolor="white",
            pad_inches=0.45
        )
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    except Exception as e:
        print(f"[Radar Datos Personales] Error generando radar PNG bytes: {e}")
        return None

def gdpr_resumen_tarjetas_por_nivel(resumen: dict):
    """
    Cuenta cuántos dominios caen en cada nivel de madurez.
    """
    out = {
        1: {"cantidad": 0, "nivel": "Nivel 1", "color": "#dc3545"},
        2: {"cantidad": 0, "nivel": "Nivel 2", "color": "#fd7e14"},
        3: {"cantidad": 0, "nivel": "Nivel 3", "color": "#ffc107"},
        4: {"cantidad": 0, "nivel": "Nivel 4", "color": "#0d6efd"},
        5: {"cantidad": 0, "nivel": "Nivel 5", "color": "#198754"},
    }

    if not resumen or not isinstance(resumen, dict):
        return out

    for _, data in resumen.items():
        try:
            pct = float(data.get("pct", 0) or 0)
        except Exception:
            pct = 0.0

        niv = gdpr_nivel_visual_por_pct(pct)
        score = int(niv.get("score", 0) or 0)
        if score in out:
            out[score]["cantidad"] += 1

    return out

def _gdpr_construir_velocimetro_niveles_fig(resumen: dict):
    """
    Construye una figura con 5 mini-velocímetros, uno por nivel,
    mostrando la cantidad de dominios en cada nivel.
    """
    try:
        niveles = gdpr_resumen_tarjetas_por_nivel(resumen)

        items = []
        max_count = 0
        for score in [1, 2, 3, 4, 5]:
            item = niveles.get(score, {})
            cantidad = int(item.get("cantidad", 0) or 0)
            max_count = max(max_count, cantidad)
            items.append({
                "nivel": item.get("nivel", f"Nivel {score}"),
                "cantidad": cantidad,
                "color": item.get("color", "#6c757d")
            })

        max_value = max(max_count, 1)

        fig, axes = plt.subplots(1, 5, figsize=(14, 3.8), dpi=140, subplot_kw={'projection': 'polar'})
        if not isinstance(axes, (list, tuple, np.ndarray)):
            axes = [axes]

        for ax, item in zip(axes, items):
            ax.set_theta_offset(math.pi)
            ax.set_theta_direction(-1)
            ax.set_ylim(0, 10)

            # Fondo semicircular
            theta_bg = np.linspace(0, math.pi, 200)
            ax.plot(theta_bg, [8] * len(theta_bg), linewidth=18, alpha=0.12, solid_capstyle='round')

            # Valor actual
            frac = item["cantidad"] / max_value if max_value > 0 else 0
            theta_val = np.linspace(0, math.pi * frac, 200) if frac > 0 else [0]
            ax.plot(theta_val, [8] * len(theta_val), linewidth=18, color=item["color"], solid_capstyle='round')

            # Aguja
            needle_angle = math.pi * frac
            ax.plot([needle_angle, needle_angle], [0, 7.2], color="#0b1220", linewidth=2)

            # Centro
            ax.scatter([0], [0], s=30, color="#0b1220", zorder=5)

            # Limpiar ejes
            ax.set_xticks([])
            ax.set_yticks([])
            ax.grid(False)
            ax.spines["polar"].set_visible(False)

            # Textos
            ax.text(
                0.5, 1.12, item["nivel"],
                transform=ax.transAxes,
                ha="center", va="center",
                fontsize=9, fontweight="bold",
                color=item["color"]
            )

            ax.text(
                0.5, 0.42, f"{item['cantidad']}",
                transform=ax.transAxes,
                ha="center", va="center",
                fontsize=18, fontweight="bold",
                color="#0b1220"
            )

            ax.text(
                0.5, 0.26, "dominios",
                transform=ax.transAxes,
                ha="center", va="center",
                fontsize=8,
                color="#4b5563"
            )

        plt.tight_layout()
        return fig

    except Exception as e:
        print(f"[Velocimetro GDPR] Error construyendo figura: {e}")
        return None


def generar_velocimetro_niveles_base64(resumen: dict) -> str | None:
    try:
        fig = _gdpr_construir_velocimetro_niveles_fig(resumen)
        if fig is None:
            return None

        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            bbox_inches="tight",
            transparent=True,
            pad_inches=0.20
        )
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    except Exception as e:
        print(f"[Velocimetro GDPR] Error generando base64: {e}")
        return None


def generar_velocimetro_niveles_png_bytes(resumen: dict) -> bytes | None:
    try:
        fig = _gdpr_construir_velocimetro_niveles_fig(resumen)
        if fig is None:
            return None

        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            bbox_inches="tight",
            transparent=False,
            facecolor="white",
            pad_inches=0.20
        )
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    except Exception as e:
        print(f"[Velocimetro GDPR] Error generando PNG bytes: {e}")
        return None

# =====================================================================
# HELPERS DETALLE / PREGUNTAS / ANÁLISIS POR DOMINIO
# =====================================================================

def _gdpr_get_items_dominio(run_id: int, dominio: str):
    out = []

    q = (
        db.session.query(DatosMadurezRespuesta, DatosMadurezPregunta)
        .join(DatosMadurezPregunta, DatosMadurezPregunta.id == DatosMadurezRespuesta.pregunta_id)
        .filter(DatosMadurezRespuesta.run_id == run_id)
        .filter(DatosMadurezPregunta.dominio == dominio)
        .order_by(DatosMadurezPregunta.orden.asc(), DatosMadurezPregunta.id.asc())
    )

    for r, p in q.all():
        out.append({
            "pregunta_id": p.id,
            "codigo": (p.codigo or "").strip(),
            "titulo": (p.titulo or "").strip(),
            "pregunta": (p.pregunta or "").strip(),
            "estado": (r.estado or "").strip().upper(),
            "comentario": (r.comentario or "").strip()
        })

    return out


def _gdpr_ai_prompt_dominio(dominio: str, pct: float, items: list[dict]):
    bullets = []

    for it in items[:100]:
        pregunta = (it.get("pregunta") or "")[:280].replace("\n", " ")
        comentario = (it.get("comentario") or "")[:220].replace("\n", " ")
        codigo = (it.get("codigo") or "").strip()
        estado = (it.get("estado") or "").strip().upper()

        linea = f"- [{estado}] "
        if codigo:
            linea += f"{codigo}: "
        linea += pregunta
        if comentario:
            linea += f" | Evidencia: {comentario}"

        bullets.append(linea)

    joined = "\n".join(bullets) if bullets else "- Sin evidencias registradas."

    return f"""
Eres un consultor experto en privacidad, protección de datos personales, GDPR y programas PIMS.
Debes producir un análisis accionable y concreto por dominio.

CONTEXTO
- Dominio: {dominio}
- Cumplimiento actual: {pct:.2f}%

EVIDENCIAS (preguntas, estado y comentarios)
{joined}

INSTRUCCIONES OBLIGATORIAS
1) Devuelve SOLAMENTE JSON válido.
2) No devuelvas markdown.
3) No devuelvas texto antes ni después del JSON.
4) Debes devolver SIEMPRE estas tres llaves:
   - "estado_actual"
   - "estado_requerido"
   - "plan_accion"
5) "estado_actual" y "estado_requerido" deben ser textos obligatorios, no vacíos.
6) "plan_accion" debe ser un arreglo, aunque sea con 1 elemento.
7) Si falta evidencia, igual debes llenar "estado_actual" y "estado_requerido" explicándolo claramente.

FORMATO EXACTO DE SALIDA
{{
  "estado_actual": "texto obligatorio",
  "estado_requerido": "texto obligatorio",
  "plan_accion": [
    {{
      "accion": "texto",
      "prioridad": "Alta",
      "responsable_sugerido": "texto",
      "plazo": "texto",
      "evidencia_esperada": "texto"
    }}
  ]
}}

REGLAS
- Usa lenguaje ejecutivo, claro y accionable.
- Prioriza brechas reales derivadas de SI / PARCIAL / NO.
- No inventes herramientas específicas si no aparecen en la evidencia.
- Si la evidencia es insuficiente, debes decirlo claramente en "estado_actual" y aun así proponer un "estado_requerido".
""".strip()

# =====================================================================
# VELOCÍMETROS POR DOMINIO — PROTECCIÓN DE DATOS PERSONALES
# =====================================================================

def _gdpr_construir_velocimetro_fig(label: str, pct: float, nivel: str, color: str):
    try:
        pct = max(0.0, min(100.0, float(pct or 0)))

        def _nivel_corto(txt: str) -> str:
            txt = (txt or "").strip()
            if txt.startswith("Nivel 1"):
                return "Nivel 1"
            if txt.startswith("Nivel 2"):
                return "Nivel 2"
            if txt.startswith("Nivel 3"):
                return "Nivel 3"
            if txt.startswith("Nivel 4"):
                return "Nivel 4"
            if txt.startswith("Nivel 5"):
                return "Nivel 5"
            return txt or "Sin nivel"

        def _label_corto(txt: str, max_len: int = 34) -> str:
            txt = (txt or "").strip()
            txt = re.sub(r"\s+", " ", txt)
            if len(txt) <= max_len:
                return txt
            return txt[:max_len - 3] + "..."

        fig = plt.figure(figsize=(4.8, 3.2), dpi=150)
        ax = fig.add_subplot(111, polar=True)

        ax.set_theta_direction(-1)
        ax.set_theta_offset(np.pi)
        ax.set_ylim(0, 10)
        ax.set_facecolor("white")

        # =========================
        # Fondo base del dial
        # =========================
        theta_full = np.linspace(0, np.pi, 500)
        ax.plot(
            theta_full,
            [8.0] * len(theta_full),
            linewidth=20,
            color="#edf2f7",
            solid_capstyle="round",
            zorder=1
        )

        # =========================
        # Tramos visuales del dial
        # =========================
        rangos = [
            (0, 20,  "#dc3545"),
            (20, 40, "#fd7e14"),
            (40, 60, "#ffc107"),
            (60, 80, "#0d6efd"),
            (80, 100, "#198754"),
        ]

        for ini, fin, col in rangos:
            th = np.linspace(np.pi * (ini / 100.0), np.pi * (fin / 100.0), 80)
            ax.plot(
                th,
                [8.0] * len(th),
                linewidth=8,
                color=col,
                alpha=0.28,
                solid_capstyle="butt",
                zorder=2
            )

        # =========================
        # Arco de avance real
        # =========================
        frac = pct / 100.0
        if frac > 0:
            theta_val = np.linspace(0, np.pi * frac, 300)
            ax.plot(
                theta_val,
                [8.0] * len(theta_val),
                linewidth=20,
                color=color,
                solid_capstyle="round",
                zorder=4
            )

        # =========================
        # Marcas del dial
        # =========================
        for tick in [0, 20, 40, 60, 80, 100]:
            ang = np.pi * (tick / 100.0)
            ax.plot([ang, ang], [6.9, 8.9], color="#64748b", linewidth=1.2, zorder=3)

        # Etiquetas de escala
        escala = [
            (0, "0"),
            (25, "25"),
            (50, "50"),
            (75, "75"),
            (100, "100"),
        ]
        for val, txt in escala:
            ang = np.pi * (val / 100.0)
            ax.text(
                ang, 9.65, txt,
                ha="center", va="center",
                fontsize=7.5,
                color="#475569",
                fontweight="bold"
            )

        # =========================
        # Aguja
        # =========================
        needle_angle = np.pi * frac
        ax.plot(
            [needle_angle, needle_angle],
            [0, 6.6],
            color="#0f172a",
            linewidth=2.2,
            zorder=6
        )

        # Centro
        ax.scatter([0], [0], s=95, color="#0f172a", zorder=7)
        ax.scatter([0], [0], s=28, color="white", zorder=8)

        # Limpieza
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
        ax.spines["polar"].set_visible(False)

        # =========================
        # Textos
        # =========================
        ax.text(
            0.5, 1.16, _label_corto(label),
            transform=ax.transAxes,
            ha="center", va="center",
            fontsize=10,
            fontweight="bold",
            color="#101827"
        )

        ax.text(
            0.5, 0.48, f"{pct:.1f}%",
            transform=ax.transAxes,
            ha="center", va="center",
            fontsize=20,
            fontweight="bold",
            color="#0b1220"
        )

        ax.text(
            0.5, 0.31, _nivel_corto(nivel),
            transform=ax.transAxes,
            ha="center", va="center",
            fontsize=9,
            fontweight="bold",
            color=color
        )

        ax.text(
            0.5, 0.18, "cumplimiento",
            transform=ax.transAxes,
            ha="center", va="center",
            fontsize=8,
            color="#4b5563"
        )

        fig.subplots_adjust(top=0.88, bottom=0.06, left=0.06, right=0.94)
        return fig

    except Exception as e:
        print(f"[GDPR Velocímetro] Error: {e}")
        return None

def generar_gdpr_velocimetro_png_bytes(label: str, pct: float, nivel: str, color: str):
    fig = _gdpr_construir_velocimetro_fig(label, pct, nivel, color)
    if fig is None:
        return None

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", pad_inches=0.20)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generar_gdpr_velocimetro_base64(label: str, pct: float, nivel: str, color: str):
    b = generar_gdpr_velocimetro_png_bytes(label, pct, nivel, color)
    if not b:
        return None
    return base64.b64encode(b).decode("utf-8")

def _gdpr_build_pdf_run(run: "DatosMadurezRun") -> io.BytesIO:
    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    radar_png = generar_radar_datos_png_bytes(resumen)

    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
        title="Protección de Datos Personales - Informe Ejecutivo"
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="GDPR_Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="GDPR_Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#1d4f8f"),
        spaceBefore=10,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="GDPR_Normal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#101827"),
        spaceAfter=5
    ))

    styles.add(ParagraphStyle(
        name="GDPR_Small",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#374151"),
        spaceAfter=4
    ))

    def pdf_escape(v):
        return html.escape(str(v or ""))

    def nivel_color(pct):
        try:
            pct = float(pct or 0)
        except Exception:
            pct = 0

        if pct >= 81:
            return colors.HexColor("#198754")
        if pct >= 61:
            return colors.HexColor("#0d6efd")
        if pct >= 41:
            return colors.HexColor("#ffc107")
        if pct >= 21:
            return colors.HexColor("#fd7e14")
        return colors.HexColor("#dc3545")

    def nivel_nombre_corto(nivel_txt):
        txt = str(nivel_txt or "")
        if ":" in txt:
            txt = txt.split(":", 1)[1].strip()
        if "(" in txt:
            txt = txt.split("(", 1)[0].strip()
        return txt or "No definido"

    def nivel_badge_pdf(pct, nivel_data):
        c = nivel_color(pct)
        score = nivel_data.get("score", 0)
        nombre = nivel_nombre_corto(nivel_data.get("nivel", ""))

        badge = Table(
            [[
                "",
                Paragraph(
                    f"<b>Nivel {score}</b> - {pdf_escape(nombre)}",
                    styles["GDPR_Small"]
                )
            ]],
            colWidths=[0.28 * cm, 4.25 * cm]
        )

        badge.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), c),
            ("BOX", (0, 0), (0, 0), 0.25, c),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))

        return badge

    def add_section(title):
        table = Table(
            [[Paragraph(pdf_escape(title), styles["GDPR_Title"])]],
            colWidths=[26.8 * cm]
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#3f86d6")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#1d4f8f")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(table)
        story.append(Spacer(1, 8))

    def add_text_block(texto):
        texto = _gdpr_normalizar_texto_plano_guardado(texto or "")
        if not texto:
            story.append(Paragraph("No hay información registrada.", styles["GDPR_Normal"]))
            return

        for parrafo in re.split(r"\n\s*\n", texto):
            parrafo = parrafo.strip()
            if parrafo:
                story.append(Paragraph(pdf_escape(parrafo), styles["GDPR_Normal"]))

    def normalizar_plan_dominio(texto_raw):
        txt = (texto_raw or "").strip()
        if not txt:
            return ""

        txt = txt.replace("```json", "").replace("```", "").strip()

        try:
            obj = json.loads(txt)
        except Exception:
            obj = _extraer_json_objeto(txt)

        if isinstance(obj, dict):
            plan = obj.get("plan_accion") or obj.get("plan") or obj.get("acciones")
            if isinstance(plan, list):
                return _gdpr_plan_accion_a_texto(plan)

        return _gdpr_normalizar_texto_plano_guardado(txt)

    story = []

    # =========================
    # ENCABEZADO
    # =========================
    add_section("Protección de Datos Personales - Informe de Madurez")

    nivel_general = gdpr_nivel_visual_por_pct(run.pct_general)
    nivel_nombre = nivel_nombre_corto(nivel_general.get("nivel", ""))

    resumen_tbl = Table([
        ["Consecutivo", pdf_escape(run.consecutivo)],
        ["Fecha", run.created_at.strftime("%Y-%m-%d %H:%M")],
        [
            "Cumplimiento general",
            f"{run.pct_general:.2f}% - Nivel {nivel_general.get('score', 0)} ({pdf_escape(nivel_nombre)})"
        ],
        ["Nivel de madurez", pdf_escape(nivel_general.get("nivel", ""))]
    ], colWidths=[5.2 * cm, 21.6 * cm])

    resumen_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f1fb")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1d4f8f")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8e3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(resumen_tbl)
    story.append(Spacer(1, 12))

    # =========================
    # INFORME EJECUTIVO
    # =========================
    story.append(Paragraph("Informe Ejecutivo", styles["GDPR_Section"]))

    informe_exec = (
        run.informe_ejecutivo_editado
        or run.informe_ejecutivo_ai
        or ""
    ).strip()

    add_text_block(informe_exec)
    story.append(Spacer(1, 10))

    # =========================
    # RADAR / ARAÑA
    # =========================
    story.append(Paragraph("Radar por Dominio", styles["GDPR_Section"]))

    if radar_png:
        try:
            img_buf = io.BytesIO(radar_png)
            img = RLImage(img_buf, width=12.5 * cm, height=10.5 * cm)
            story.append(img)
            story.append(Spacer(1, 10))
        except Exception as e:
            story.append(
                Paragraph(
                    f"No se pudo renderizar el radar: {pdf_escape(e)}",
                    styles["GDPR_Normal"]
                )
            )

    # =========================
    # TABLA GENERAL CON COLORIMETRÍA TIPO ISO
    # =========================
    story.append(Paragraph("Detalle por Dominio", styles["GDPR_Section"]))

    data = [[
        "Dominio",
        "% Cumplimiento",
        "Nivel de madurez",
        "Items",
        "Brecha"
    ]]

    for dominio, d in (resumen or {}).items():
        try:
            pct = float(d.get("pct", 0) or 0)
        except Exception:
            pct = 0.0

        total = int(d.get("total", 0) or 0)
        brecha = max(0.0, 100.0 - pct)
        nivel_data = gdpr_nivel_visual_por_pct(pct)

        data.append([
            Paragraph(pdf_escape(dominio), styles["GDPR_Small"]),
            Paragraph(f"{pct:.2f}%", styles["GDPR_Small"]),
            nivel_badge_pdf(pct, nivel_data),
            Paragraph(str(total), styles["GDPR_Small"]),
            Paragraph(f"{brecha:.2f}%", styles["GDPR_Small"])
        ])

    tbl = Table(
        data,
        colWidths=[12.0 * cm, 3.2 * cm, 5.4 * cm, 2.2 * cm, 3.0 * cm],
        repeatRows=1
    )

    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3f86d6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7.2),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8e3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 1), (1, -1), "CENTER"),
        ("ALIGN", (3, 1), (4, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.append(tbl)

    # =========================
    # ANÁLISIS POR DOMINIO
    # =========================
    analisis_rows = DatosMadurezDominioAnalisis.query.filter_by(
        run_id=run.id
    ).order_by(
        DatosMadurezDominioAnalisis.dominio.asc()
    ).all()

    if analisis_rows:
        story.append(PageBreak())
        add_section("Análisis Ejecutivo por Dominio")

        for a in analisis_rows:
            story.append(Paragraph(pdf_escape(a.dominio), styles["GDPR_Section"]))

            estado_actual = _gdpr_normalizar_texto_plano_guardado(a.estado_actual or "")
            estado_requerido = _gdpr_normalizar_texto_plano_guardado(a.estado_requerido or "")
            plan_accion = normalizar_plan_dominio(
                a.plan_accion_editado or a.plan_accion_ai or ""
            )

            bloque = Table([
                [
                    Paragraph("<b>Estado actual</b>", styles["GDPR_Small"]),
                    Paragraph(pdf_escape(estado_actual or "No registrado."), styles["GDPR_Small"])
                ],
                [
                    Paragraph("<b>Estado requerido</b>", styles["GDPR_Small"]),
                    Paragraph(pdf_escape(estado_requerido or "No registrado."), styles["GDPR_Small"])
                ],
                [
                    Paragraph("<b>Plan de acción</b>", styles["GDPR_Small"]),
                    Paragraph(pdf_escape(plan_accion or "No registrado."), styles["GDPR_Small"])
                ],
            ], colWidths=[4.2 * cm, 22.6 * cm])

            bloque.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f1fb")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1d4f8f")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8e3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))

            story.append(bloque)
            story.append(Spacer(1, 10))

    doc.build(story)
    buf.seek(0)
    return buf


@madurez_datos_bp.route("/detalle/<int:run_id>/pdf", methods=["GET"])
@login_required
def detalle_pdf(run_id: int):
    run = DatosMadurezRun.query.get_or_404(run_id)

    filename = f"Proteccion_Datos_{(run.consecutivo or 'revision').replace(' ', '_')}.pdf"

    return send_file(
        _gdpr_build_pdf_run(run),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )

# =====================================================================
# IMPORTACIÓN DEL INSTRUMENTO DESDE EXCEL
# =====================================================================

@madurez_datos_bp.route("/admin/importar_instrumento", methods=["POST"])
@login_required
def importar_instrumento_admin():
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El rol Auditor no puede importar instrumentos.", "danger")
        return redirect(url_for("madurez_datos.inicio"))

    force = (request.args.get("force") == "1") or (request.form.get("force") == "1")

    if (DatosMadurezPregunta.query.count() > 0) and not force:
        flash("⚠️ El instrumento de protección de datos ya fue importado. Usa force=1 si deseas reiniciarlo.", "warning")
        return redirect(url_for("madurez_datos.inicio"))

    if force:
        try:
            DatosMadurezRespuesta.query.delete()
            DatosMadurezRun.query.delete()
            DatosMadurezPregunta.query.delete()
            db.session.commit()
        except Exception:
            db.session.rollback()

    if not os.path.exists(GDPR_INSTRUMENTO_TEMPLATE_XLSX):
        flash(f"❌ No se encontró el Excel GDPR en: {GDPR_INSTRUMENTO_TEMPLATE_XLSX}", "danger")
        return redirect(url_for("madurez_datos.inicio"))

    try:
        wb = load_workbook(GDPR_INSTRUMENTO_TEMPLATE_XLSX, data_only=True)
    except Exception as e:
        flash(f"❌ No se pudo abrir el Excel GDPR: {e}", "danger")
        return redirect(url_for("madurez_datos.inicio"))

    if not wb.sheetnames:
        flash("❌ El archivo Excel GDPR no tiene hojas.", "danger")
        return redirect(url_for("madurez_datos.inicio"))

    ws = wb[wb.sheetnames[0]]

    created = 0
    orden = 0
    dominio_actual = None
    codigo_actual = 0

    # Formato real del Excel:
    # Columna B = pregunta / dominio
    # Columnas C..G = N/A, Si, Parcialmente, No, Comentarios
    for r in range(1, ws.max_row + 1):
        val = ws.cell(r, 2).value   # <-- COLUMNA B
        txt = "" if val is None else str(val).strip()

        if not txt:
            continue

        # Saltar encabezado
        if txt.lower() == "pregunta":
            continue

        # Detectar si la fila es dominio:
        # si tiene texto en B y las columnas C..G están vacías
        cols_c_g_vacias = True
        for c in range(3, 8):   # C..G
            vv = ws.cell(r, c).value
            if vv is not None and str(vv).strip() != "":
                cols_c_g_vacias = False
                break

        es_posible_dominio = (
            cols_c_g_vacias
            and len(txt) <= 80
            and not txt.endswith("?")
            and not txt.startswith("¿")
        )

        if es_posible_dominio:
            dominio_actual = txt
            continue

        # Lo demás se toma como pregunta
        orden += 1
        codigo_actual += 1

        db.session.add(DatosMadurezPregunta(
            dominio=dominio_actual or "General",
            codigo=str(codigo_actual),
            titulo=dominio_actual or f"Control {codigo_actual}",
            orden=orden,
            pregunta=txt,
            activo=True
        ))
        created += 1

    db.session.commit()
    flash(f"✅ Instrumento de protección de datos importado correctamente. Preguntas creadas: {created}", "success")
    return redirect(url_for("madurez_datos.inicio"))

# =====================================================================
# PANTALLA PRINCIPAL
# =====================================================================

@madurez_datos_bp.route("/", methods=["GET"], endpoint="inicio")
@login_required
def madurez_datos_inicio():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez protección de datos personales"):
        flash("No tiene permiso para acceder al módulo de nivel de madurez de protección de datos personales.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == 'auditor')

    if read_only:
        ingreso_btn = """
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled
                  title="El rol Auditor no puede ingresar información">
            <i class="bi bi-pencil-square me-2"></i>Ingresar la información
          </button>
        """
    else:
        ingreso_btn = f"""
          <a href="{url_for('madurez_datos.ingreso')}" class="btn btn-primary rounded-pill px-4 fw-bold">
            <i class="bi bi-pencil-square me-2"></i>Ingresar la información
          </a>
        """

    if read_only:
        parametros_btn = """
          <button class="btn btn-outline-secondary rounded-pill px-3" disabled
                  title="El rol Auditor no tiene acceso a Parámetros">
            <i class="bi bi-gear me-2"></i>Parámetros
          </button>
        """
    else:
        parametros_btn = f"""
          <a href="{url_for('madurez_datos.parametros')}" class="btn btn-outline-secondary rounded-pill px-3">
            <i class="bi bi-gear me-2"></i>Parámetros
          </a>
        """

    total = DatosMadurezPregunta.query.count()

    if total == 0:
        badge = '<span class="badge bg-danger ms-2">Instrumento NO cargado</span>'
        hint = "Primero entra a Parámetros y realiza la importación del instrumento (1 vez)."
    else:
        badge = '<span class="badge bg-success ms-2">Instrumento cargado</span>'
        hint = "Puedes ingresar la información o consultar el historial de revisiones."

    content = f"""
    <div class="datamad-shell">
      <div class="datamad-header-card">
        <div class="datamad-header-overlay">
          <div class="datamad-header-text">
            <h3 class="datamad-title m-0">Nivel de Madurez — Protección de Datos Personales</h3>
            <div class="datamad-subtitle">
              Evaluación del programa de protección de datos personales con enfoque GDPR / PIMS.
            </div>
          </div>
        </div>
      </div>

      <div class="datamad-header-actions">
        {ingreso_btn}
        <a href="{url_for('madurez_datos.historial')}" class="btn datamad-btn-soft rounded-pill px-4">
          <i class="bi bi-clock-history me-2"></i>Historial de Revisiones
        </a>
      </div>

      <div class="row g-3 mt-2">
        <div class="col-12 col-lg-8">
          <div class="datamad-card p-4 h-100">
            <div class="datamad-section-title">Estado del instrumento</div>
            <div class="fw-bold">Estado del instrumento {badge}</div>
            <div class="text-muted small mt-1">Preguntas cargadas: <b>{total}</b></div>
            <div class="mt-2 small">{hint}</div>
            <div class="mt-3">{parametros_btn}</div>
            <div class="alert alert-info mt-3 mb-0 small">
              <b>Sugerencia:</b> En <b>Parámetros</b> se visualiza la misma escala 1–5 del módulo NIST CSF 2.0.
            </div>
          </div>
        </div>

        <div class="col-12 col-lg-4">
          <div class="datamad-card p-4 h-100">
            <div class="datamad-section-title">¿Qué puedes hacer aquí?</div>
            <ul class="small mb-0 text-black ps-3">
              <li><b>Ingresar la información:</b> diligenciar respuestas (Sí/Parcial/No/N/A) con evidencia.</li>
              <li><b>Historial:</b> revisar evaluaciones previas y porcentaje general.</li>
              <li><b>Parámetros:</b> ver niveles de madurez e importar el instrumento.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .datamad-shell{{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }}

      .datamad-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .datamad-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .datamad-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .datamad-header-overlay::before{{
        content:"🛡️";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .datamad-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .datamad-header-text::before{{
        content:"SGSI · Protección de Datos Personales";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .datamad-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .datamad-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .datamad-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .datamad-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .datamad-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .datamad-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .datamad-btn-soft{{
        background:rgba(255,255,255,.88);
        color:#111 !important;
        border:1px solid rgba(108,117,125,.35);
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .datamad-btn-soft:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .datamad-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .datamad-card.p-4{{
        padding:1.5rem !important;
      }}

      .datamad-section-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:0;
      }}

      .datamad-section-title{{
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
        margin-bottom:14px;
      }}

      .datamad-card .small{{
        line-height:1.45;
      }}

      .datamad-card ul li{{
        margin-bottom:6px;
      }}

      .datamad-card ul li:last-child{{
        margin-bottom:0;
      }}

      .datamad-card .alert-info{{
        border-radius:14px;
        border:1px solid rgba(13,110,253,.16);
        box-shadow:0 6px 16px rgba(0,0,0,.06);
      }}

      .badge,
      .datamad-card .badge{{
        font-size:.70rem;
        padding:.35rem .65rem;
        border-radius:999px;
        font-weight:900;
      }}

      .form-label{{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:6px 10px;
        border-radius:10px;
        display:inline-block;
        margin-bottom:6px;
      }}

      .form-control,
      .form-select{{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      textarea.form-control{{
        min-height:90px;
      }}

      .form-control:focus,
      .form-select:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .btn.rounded-pill,
      .btn.pill,
      .pill{{
        border-radius:999px !important;
      }}

      .datamad-card .btn-primary,
      .datamad-card .btn-outline-secondary,
      .datamad-card .btn-outline-primary{{
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        font-weight:900;
      }}

      @media (max-width:991.98px){{
        .datamad-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .datamad-header-card{{
          min-height:88px;
        }}

        .datamad-title{{
          font-size:1.20rem;
        }}

        .datamad-subtitle{{
          font-size:.68rem;
        }}

        .datamad-header-actions{{
          gap:6px;
        }}
      }}

      @media (max-width:768px){{
        .datamad-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .datamad-header-overlay::before{{
          margin:0;
        }}

        .datamad-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .datamad-title,
        .datamad-subtitle{{
          text-align:center;
        }}

        .datamad-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Madurez Datos Personales", content=content)


# =====================================================================
# PARÁMETROS
# =====================================================================

@madurez_datos_bp.route("/parametros", methods=["GET"])
@login_required
def parametros():
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El rol Auditor no tiene acceso a Parámetros.", "danger")
        return redirect(url_for("madurez_datos.inicio"))

    total = DatosMadurezPregunta.query.count()
    badge = '<span class="badge bg-success ms-2">Instrumento cargado</span>' if total > 0 else '<span class="badge bg-danger ms-2">Instrumento NO cargado</span>'

    rows = []
    for lvl in GDPR_MADUREZ_LEVELS:
        rows.append(f"""
        <tr>
          <td class="fw-semibold">{escape(lvl['nivel'])}</td>
          <td class="text-muted">{escape(lvl['descripcion'])}</td>
          <td class="text-center fw-bold">{lvl['score']}</td>
          <td class="text-center">{escape(lvl.get('rango_pct',''))}</td>
          <td class="text-muted">{escape(lvl.get('logica',''))}</td>
        </tr>
        """)

    content = f"""
    <div class="datapar-shell">
      <div class="datapar-header-card">
        <div class="datapar-header-overlay">
          <div class="datapar-header-text">
            <h3 class="datapar-title m-0">Parámetros — Protección de Datos Personales</h3>
            <div class="datapar-subtitle">
              El nivel de evaluación de madurez es exactamente el mismo del módulo NIST CSF 2.0.
            </div>
          </div>
        </div>
      </div>

      <div class="datapar-header-actions">
        <a href="{url_for('madurez_datos.inicio')}" class="btn datapar-btn-main rounded-pill px-4 fw-bold">⬅ Inicio</a>
      </div>

      <div class="datapar-card p-4 mb-3">
        <div class="datapar-section-title">Estado del instrumento {badge}</div>
        <div class="text-muted small">Preguntas cargadas: <b>{total}</b></div>
      </div>

      <div class="datapar-card p-4 mb-3">
        <div class="datapar-section-title">Modelo de niveles de madurez (igual a NIST)</div>
        <div class="table-responsive">
          <table class="table table-sm table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Nivel</th>
                <th>Descripción</th>
                <th class="text-center">Score</th>
                <th class="text-center">Rango %</th>
                <th>Lógica</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
        </div>
      </div>

      <div class="datapar-card p-4 text-center">
        <div class="datapar-section-title">Importar instrumento de evaluación</div>
        <div class="text-muted small mb-3">
          Este proceso importa el instrumento oficial de protección de datos personales desde el Excel.
        </div>
        <form method="POST" action="{url_for('madurez_datos.importar_instrumento_admin', force=1)}">
          <button class="btn btn-danger rounded-pill px-4 fw-semibold">
            <i class="bi bi-database-add me-2"></i>Importar instrumento
          </button>
        </form>
      </div>
    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .datapar-shell{{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }}

      .datapar-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .datapar-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .datapar-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .datapar-header-overlay::before{{
        content:"⚙️";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .datapar-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .datapar-header-text::before{{
        content:"SGSI · Parámetros de Datos Personales";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .datapar-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .datapar-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .datapar-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .datapar-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .datapar-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .datapar-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .datapar-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .datapar-card.p-4{{
        padding:1.5rem !important;
      }}

      .datapar-section-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:0;
      }}

      .datapar-section-title{{
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
        margin-bottom:16px;
      }}

      .form-label{{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:6px 10px;
        border-radius:10px;
        display:inline-block;
        margin-bottom:6px;
      }}

      .form-control,
      .form-select{{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      .form-control:focus,
      .form-select:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .btn.rounded-pill,
      .btn.pill,
      .pill{{
        border-radius:999px !important;
      }}

      .datapar-card .btn-primary,
      .datapar-card .btn-outline-primary,
      .datapar-card .btn-outline-danger{{
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      @media (max-width:991.98px){{
        .datapar-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .datapar-header-card{{
          min-height:88px;
        }}

        .datapar-title{{
          font-size:1.20rem;
        }}

        .datapar-subtitle{{
          font-size:.68rem;
        }}
      }}

      @media (max-width:768px){{
        .datapar-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .datapar-header-overlay::before{{
          margin:0;
        }}

        .datapar-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .datapar-title,
        .datapar-subtitle{{
          text-align:center;
        }}

        .datapar-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Parámetros Datos Personales", content=content)


# =====================================================================
# INGRESO DE INFORMACIÓN
# =====================================================================

@madurez_datos_bp.route("/ingreso", methods=["GET"])
@login_required
def ingreso():
    user = User.query.get(session.get("user_id"))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez protección de datos personales"):
        flash("No tiene permiso para acceder al módulo de nivel de madurez de protección de datos personales.", "danger")
        return redirect(url_for('menu'))

    if user.role == "auditor":
        flash("El rol Auditor no puede ingresar la información en este módulo.", "warning")
        return redirect(url_for("madurez_datos.inicio"))

    if DatosMadurezPregunta.query.count() == 0:
        flash("⚠️ Primero debes importar el instrumento de protección de datos personales (1 vez).", "warning")
        return redirect(url_for("madurez_datos.inicio"))

    preguntas = (
        DatosMadurezPregunta.query
        .filter_by(activo=True)
        .order_by(
            DatosMadurezPregunta.dominio.asc(),
            DatosMadurezPregunta.orden.asc(),
            DatosMadurezPregunta.id.asc()
        )
        .all()
    )

    draft = obtener_borrador_datos(user.id if user else None)
    respuestas_db = cargar_respuestas_datos(draft.id if draft else None)
    _, _, progreso_inicial = calcular_progreso_datos(preguntas, respuestas_db=respuestas_db)

    consecutivo = draft.consecutivo if draft else ""
    draft_id = draft.id if draft else ""

    dominios = {}
    for q in preguntas:
        dom = (q.dominio or "Sin dominio").strip()
        dominios.setdefault(dom, [])
        dominios[dom].append(q)

    bloques_dominios = []

    for idx, (dominio, items) in enumerate(dominios.items()):
        collapse_id = f"datosDominioCollapse_{idx}"
        show_cls = "show" if idx == 0 else ""

        preguntas_html = []

        for q in items:
            resp = respuestas_db.get(q.id, {})
            est = (resp.get("estado") or "").strip().upper()
            cm = (resp.get("comentario") or "").strip()

            def checked(val):
                return "checked" if est == val else ""

            preguntas_html.append(f"""
            <div class="col-12 col-xl-6">
              <div class="dataform-qcard h-100">

                <div class="dataform-qhead">
                  <div class="d-flex align-items-center gap-2 flex-wrap">
                    <span class="badge rounded-pill text-bg-light border fw-semibold">
                      {escape(q.codigo or '')}
                    </span>
                    <span class="badge rounded-pill text-bg-primary">
                      Orden {q.orden or 0}
                    </span>
                  </div>
                </div>

                <div class="dataform-qtitle">
                  {escape(q.titulo or '')}
                </div>

                <div class="dataform-qtext">
                  {escape(q.pregunta or '')}
                </div>

                <div class="dataform-radio-row">
                  <label class="dataform-radio-card">
                    <input type="radio" name="st_{q.id}" value="NA" {checked('NA')}>
                    <span>N/A</span>
                  </label>

                  <label class="dataform-radio-card">
                    <input type="radio" name="st_{q.id}" value="SI" {checked('SI')}>
                    <span>Sí</span>
                  </label>

                  <label class="dataform-radio-card">
                    <input type="radio" name="st_{q.id}" value="PARCIAL" {checked('PARCIAL')}>
                    <span>Parcial</span>
                  </label>

                  <label class="dataform-radio-card">
                    <input type="radio" name="st_{q.id}" value="NO" {checked('NO')}>
                    <span>No</span>
                  </label>
                </div>

                <div class="mt-3">
                  <label class="form-label small fw-bold text-black mb-1">Comentario / evidencia</label>
                  <textarea class="form-control"
                            name="cm_{q.id}"
                            rows="3"
                            placeholder="Describe la evidencia, observaciones o hallazgos...">{escape(cm)}</textarea>
                </div>

              </div>
            </div>
            """)

        bloques_dominios.append(f"""
        <div class="accordion-item dataform-acc-item">
          <h2 class="accordion-header" id="headingDom_{idx}">
            <button class="accordion-button {'collapsed' if idx != 0 else ''} dataform-acc-btn"
                    type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#{collapse_id}"
                    aria-expanded="{str(idx == 0).lower()}"
                    aria-controls="{collapse_id}">
              <div class="dataform-acc-inner">
                <div class="dataform-acc-title-wrap">
                  <i class="bi bi-folder2-open me-2"></i>
                  <span class="dataform-acc-title">{escape(dominio)}</span>
                </div>
                <span class="badge rounded-pill text-bg-light border">
                  {len(items)} preguntas
                </span>
              </div>
            </button>
          </h2>

          <div id="{collapse_id}"
               class="accordion-collapse collapse {show_cls}"
               aria-labelledby="headingDom_{idx}">
            <div class="accordion-body dataform-acc-body">
              <div class="row g-3">
                {''.join(preguntas_html)}
              </div>
            </div>
          </div>
        </div>
        """)

    disabled_analizar = "disabled" if progreso_inicial < 100 else ""

    content = f"""
    <div class="dataform-shell">
      <div class="dataform-header-card">
        <div class="dataform-header-overlay">
          <div class="dataform-header-text">
            <h3 class="dataform-title m-0">Ingreso de información — Protección de Datos Personales</h3>
            <div class="dataform-subtitle">
              Diligencia el instrumento por capítulo, guarda el borrador y analiza cuando el progreso sea 100%.
            </div>
          </div>
        </div>
      </div>

      <div class="dataform-header-actions">
        <a href="{url_for('madurez_datos.inicio')}" class="btn dataform-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al Inicio
        </a>
      </div>

      <div class="dataform-card p-4">
        <form id="datosIngresoForm"
              method="POST"
              action="{url_for('madurez_datos.ingreso_guardar')}"
              novalidate
              autocomplete="off">

          <input type="hidden" name="draft_id" value="{draft_id}">

          <div class="row g-3 align-items-end mb-4">
            <div class="col-md-5">
              <label class="text-black form-label fw-bold" for="datosConsecutivoRevision">
                Consecutivo <span class="text-danger">*</span>
              </label>

              <input type="text"
                     class="form-control"
                     name="consecutivo"
                     id="datosConsecutivoRevision"
                     value="{escape(consecutivo)}"
                     autocomplete="off"
                     required>

              <div id="datosConsecutivoRevisionError"
                   class="invalid-feedback d-none fw-bold mt-2">
                Debes ingresar el consecutivo de la Revisión.
              </div>
            </div>

            <div class="col-md-7">
              <label class="form-label fw-bold">Progreso del diligenciamiento</label>
              <div class="progress dataform-progress">
                <div id="dataProgressBar"
                     class="progress-bar bg-success"
                     role="progressbar"
                     style="width:{progreso_inicial}%"
                     aria-valuenow="{progreso_inicial}"
                     aria-valuemin="0"
                     aria-valuemax="100">
                  {progreso_inicial}%
                </div>
              </div>
              <div class="small text-muted mt-1">
                Progreso actual: <span id="dataProgressText">{progreso_inicial}%</span>
              </div>
            </div>
          </div>

          <div class="accordion dataform-accordion" id="accordionIngresoDatos">
            {''.join(bloques_dominios)}
          </div>

          <div class="d-flex justify-content-center gap-3 flex-wrap mt-4">
            <button class="btn btn-outline-primary btn-lg rounded-pill px-5 shadow fw-semibold datos-submit-btn"
                    type="submit"
                    name="accion"
                    value="guardar"
                    data-accion="guardar">
              <i class="bi bi-save2 me-2"></i>Guardar
            </button>

            <button id="btnAnalizarDatos"
                    class="btn btn-primary btn-lg rounded-pill px-5 shadow fw-semibold datos-submit-btn"
                    type="submit"
                    name="accion"
                    value="analizar"
                    data-accion="analizar"
                    {disabled_analizar}>
              <i class="bi bi-bar-chart-line-fill me-2"></i>Analizar
            </button>
          </div>
        </form>
      </div>
    </div>

    <script>
    (function() {{

        let DATOS_BLOQUEAR_LOADER = false;

        function datosOcultarLoaderGlobal() {{
            const ids = [
                "SGSI_PROGRESS_GLOBAL",
                "globalLoader",
                "loader",
                "progressOverlay",
                "sgsiProgressGlobal",
                "globalProgress",
                "overlayProgress",
                "loadingOverlay"
            ];

            ids.forEach(function(id) {{
                const el = document.getElementById(id);
                if (el) {{
                    el.style.display = "none";
                    el.style.visibility = "hidden";
                    el.style.opacity = "0";
                    el.style.pointerEvents = "none";
                    el.classList.add("d-none");
                    el.classList.remove("show");
                }}
            }});

            document.querySelectorAll(
                ".modal-backdrop, " +
                ".progress-overlay, " +
                ".loader-overlay, " +
                ".sgsi-loader, " +
                ".sgsi-progress, " +
                ".loading-overlay, " +
                ".global-loader, " +
                ".global-progress, " +
                ".progress-global"
            ).forEach(function(el) {{
                el.style.display = "none";
                el.style.visibility = "hidden";
                el.style.opacity = "0";
                el.style.pointerEvents = "none";
                el.classList.add("d-none");
                el.classList.remove("show");
            }});

            document.body.classList.remove("modal-open");
            document.body.style.overflow = "";
            document.body.style.paddingRight = "";
        }}

        function datosValidarConsecutivoRevision() {{
            const input = document.getElementById("datosConsecutivoRevision");
            const error = document.getElementById("datosConsecutivoRevisionError");

            const valor = input ? input.value.trim() : "";

            if (!valor) {{
                DATOS_BLOQUEAR_LOADER = true;
                datosOcultarLoaderGlobal();

                if (input) {{
                    input.classList.add("is-invalid");
                    input.setAttribute("aria-invalid", "true");
                    input.focus();
                }}

                if (error) {{
                    error.classList.remove("d-none");
                    error.style.display = "block";
                }}

                return false;
            }}

            DATOS_BLOQUEAR_LOADER = false;

            if (input) {{
                input.classList.remove("is-invalid");
                input.setAttribute("aria-invalid", "false");
            }}

            if (error) {{
                error.classList.add("d-none");
                error.style.display = "none";
            }}

            return true;
        }}

        function actualizarProgresoDatos() {{
            const radios = document.querySelectorAll('input[type="radio"][name^="st_"]');
            const nombres = [...new Set(Array.from(radios).map(r => r.name))];
            const total = nombres.length;
            let respondidas = 0;

            nombres.forEach(function(nombre) {{
                const marcado = document.querySelector('input[name="' + nombre + '"]:checked');
                if (marcado) respondidas++;
            }});

            const porcentaje = total > 0 ? Math.round((respondidas / total) * 100) : 0;
            const bar = document.getElementById("dataProgressBar");
            const text = document.getElementById("dataProgressText");
            const btnAnalizar = document.getElementById("btnAnalizarDatos");

            if (bar) {{
                bar.style.width = porcentaje + "%";
                bar.innerText = porcentaje + "%";
                bar.setAttribute("aria-valuenow", porcentaje);
            }}

            if (text) {{
                text.innerText = porcentaje + "%";
            }}

            if (btnAnalizar) {{
                btnAnalizar.disabled = porcentaje < 100;
                btnAnalizar.classList.toggle("disabled", porcentaje < 100);
            }}
        }}

        const posiblesLoaders = [
            "showLoader",
            "mostrarLoader",
            "showGlobalLoader",
            "mostrarProgresoGlobal",
            "showProgress",
            "openLoader",
            "activarLoader",
            "SGSI_showLoader"
        ];

        posiblesLoaders.forEach(function(nombreFuncion) {{
            const original = window[nombreFuncion];

            if (typeof original === "function" && !original.__datosInterceptado) {{
                const wrapper = function() {{
                    if (DATOS_BLOQUEAR_LOADER || !datosValidarConsecutivoRevision()) {{
                        datosOcultarLoaderGlobal();
                        return false;
                    }}

                    return original.apply(this, arguments);
                }};

                wrapper.__datosInterceptado = true;
                window[nombreFuncion] = wrapper;
            }}
        }});

        document.addEventListener("change", function(e) {{
            if (e.target.matches('input[type="radio"][name^="st_"]')) {{
                actualizarProgresoDatos();
            }}
        }});

        document.addEventListener("click", function(e) {{
            const btn = e.target.closest(".datos-submit-btn");

            if (!btn) {{
                return;
            }}

            if (!datosValidarConsecutivoRevision()) {{
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();

                DATOS_BLOQUEAR_LOADER = true;
                datosOcultarLoaderGlobal();

                return false;
            }}
        }}, true);

        window.addEventListener("DOMContentLoaded", function() {{
            const form = document.getElementById("datosIngresoForm");
            const input = document.getElementById("datosConsecutivoRevision");

            if (input) {{
                input.addEventListener("input", function() {{
                    datosValidarConsecutivoRevision();
                }});

                input.addEventListener("blur", function() {{
                    datosValidarConsecutivoRevision();
                }});
            }}

            if (form) {{
                form.addEventListener("submit", function(e) {{
                    if (!datosValidarConsecutivoRevision()) {{
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();

                        DATOS_BLOQUEAR_LOADER = true;
                        datosOcultarLoaderGlobal();

                        return false;
                    }}
                }}, true);
            }}

            actualizarProgresoDatos();
            datosOcultarLoaderGlobal();
        }});

        window.addEventListener("pageshow", function() {{
            datosOcultarLoaderGlobal();
        }});

    }})();
    </script>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .dataform-shell{{
        width:96%;
        max-width:1700px;
        margin:26px auto 24px auto;
      }}

      .dataform-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .dataform-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .dataform-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .dataform-header-overlay::before{{
        content:"📝";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .dataform-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .dataform-header-text::before{{
        content:"SGSI · Evaluación Protección de Datos Personales";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .dataform-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .dataform-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .dataform-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .dataform-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .dataform-header-actions .btn{{
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .dataform-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .dataform-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .dataform-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .dataform-card{{
        padding:1.5rem !important;
      }}

      .dataform-progress{{
        height:22px;
        border-radius:999px;
        overflow:hidden;
        background:#e5edf7;
        box-shadow:inset 0 1px 3px rgba(15,23,42,.12);
      }}

      .progress-bar{{
        font-weight:900;
      }}

      .form-label{{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:6px 10px;
        border-radius:10px;
        display:inline-block;
        margin-bottom:6px;
      }}

      .form-control,
      .form-select{{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      textarea.form-control{{
        min-height:92px;
      }}

      .form-control:focus,
      .form-select:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .form-control.is-invalid{{
        border-color:#dc3545 !important;
        background:#fff5f5 !important;
        box-shadow:0 0 0 .15rem rgba(220,53,69,.15) !important;
      }}

      .invalid-feedback{{
        color:#b42318;
        background:#fff1f1;
        border:1px solid #ffd4d4;
        border-radius:10px;
        padding:8px 12px;
      }}

      .dataform-accordion{{
        --bs-accordion-border-color:transparent;
        --bs-accordion-btn-focus-box-shadow:0 0 0 .2rem rgba(63,134,214,.12);
      }}

      .dataform-acc-item,
      .accordion-item{{
        border:1px solid #dbe6f4 !important;
        background:#ffffff !important;
        margin-bottom:14px;
        border-radius:18px !important;
        overflow:hidden;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }}

      .dataform-acc-btn,
      .accordion-button{{
        background:#eef5ff !important;
        color:#0f172a !important;
        font-weight:900;
        padding:18px 22px !important;
        border-bottom:1px solid #dbe6f4;
        box-shadow:none !important;
      }}

      .dataform-acc-btn:not(.collapsed),
      .accordion-button:not(.collapsed){{
        background:#dbeafe !important;
        color:#0b4a8f !important;
        box-shadow:none !important;
      }}

      .dataform-acc-btn::after{{
        filter:none;
      }}

      .dataform-acc-inner{{
        width:100%;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
      }}

      .dataform-acc-title{{
        font-size:1rem;
        font-weight:950;
        color:#1e293b;
      }}

      .dataform-acc-body,
      .accordion-body{{
        background:rgba(255,255,255,.96) !important;
        padding:18px !important;
      }}

      .dataform-qcard{{
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 4px 10px rgba(15,23,42,.05);
        transition:.2s;
        height:100%;
      }}

      .dataform-qcard:hover{{
        transform:translateY(-2px);
        box-shadow:0 8px 20px rgba(15,23,42,.10);
      }}

      .dataform-qtitle{{
        font-size:.92rem;
        font-weight:950;
        color:#0b4a8f;
        margin-bottom:5px;
      }}

      .dataform-qtext{{
        font-size:.92rem;
        color:#0f172a;
        font-weight:700;
        line-height:1.45;
      }}

      .dataform-radio-row{{
        display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:10px;
        margin-top:14px;
      }}

      .dataform-radio-card{{
        display:flex;
        align-items:center;
        justify-content:center;
        gap:6px;
        background:#f8fafc;
        border:1px solid #dbe4ee;
        border-radius:12px;
        min-height:46px;
        font-weight:900;
        color:#101827;
        cursor:pointer;
        transition:.2s;
        padding:8px 10px;
      }}

      .dataform-radio-card:hover{{
        background:#eef6ff;
        border-color:#93c5fd;
      }}

      .dataform-radio-card input[type="radio"]{{
        transform:scale(1.08);
      }}

      .btn.rounded-pill,
      .btn.pill,
      .pill{{
        border-radius:999px !important;
      }}

      .dataform-card .btn-primary,
      .dataform-card .btn-outline-primary,
      .dataform-card .btn-outline-secondary{{
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        font-weight:900;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:1200px){{
        .dataform-radio-row{{
          grid-template-columns:repeat(2,1fr);
        }}
      }}

      @media (max-width:991.98px){{
        .dataform-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .dataform-header-card{{
          min-height:88px;
        }}

        .dataform-title{{
          font-size:1.20rem;
        }}

        .dataform-subtitle{{
          font-size:.68rem;
        }}
      }}

      @media (max-width:768px){{
        .dataform-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .dataform-header-overlay::before{{
          margin:0;
        }}

        .dataform-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .dataform-title,
        .dataform-subtitle{{
          text-align:center;
        }}

        .dataform-header-actions .btn{{
          width:100%;
        }}

        .dataform-radio-row{{
          grid-template-columns:1fr;
        }}

        .dataform-acc-inner{{
          flex-direction:column;
          align-items:flex-start;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Ingreso Protección de Datos", content=content)

# =====================================================================
# GUARDAR / ANALIZAR
# =====================================================================

@madurez_datos_bp.route("/ingreso/guardar", methods=["POST"])
@login_required
def ingreso_guardar():
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El rol Auditor no puede ingresar la información en este módulo.", "danger")
        return redirect(url_for("madurez_datos.inicio"))

    consecutivo = (request.form.get("consecutivo") or "").strip()
    accion = (request.form.get("accion") or "guardar").strip().lower()
    draft_id = (request.form.get("draft_id") or "").strip()

    if not consecutivo:
        flash("Debes ingresar el consecutivo de la revisión.", "warning")
        return redirect(url_for("madurez_datos.inicio"))

    preguntas = (
        DatosMadurezPregunta.query
        .filter_by(activo=True)
        .order_by(DatosMadurezPregunta.orden.asc())
        .all()
    )

    respondidas, total, progreso_pct = calcular_progreso_datos(preguntas, form_data=request.form)

    try:
        run = None

        if draft_id:
            run = DatosMadurezRun.query.filter_by(id=int(draft_id)).first()
            if run and user and run.user_id != user.id:
                flash("No tienes permiso para modificar este borrador.", "danger")
                return redirect(url_for("madurez_datos.ingreso"))

        if not run:
            run = obtener_borrador_datos(user.id if user else None)

        if not run:
            run = DatosMadurezRun(
                consecutivo=consecutivo,
                user_id=user.id if user else None,
                estado="BORRADOR",
                progreso_pct=0,
                resumen_json="{}",
                pct_general=0.0
            )
            db.session.add(run)
            db.session.flush()

        run.consecutivo = consecutivo
        run.progreso_pct = progreso_pct
        run.updated_at = datetime.now(timezone.utc)

        DatosMadurezRespuesta.query.filter_by(run_id=run.id).delete()

        for q in preguntas:
            st = (request.form.get(f"st_{q.id}") or "").strip().upper()
            cm = (request.form.get(f"cm_{q.id}") or "").strip()

            if st in ("SI", "PARCIAL", "NO", "NA"):
                db.session.add(DatosMadurezRespuesta(
                    run_id=run.id,
                    pregunta_id=q.id,
                    estado=st,
                    comentario=cm
                ))

        db.session.flush()

        if accion == "guardar":
            run.estado = "BORRADOR"
            db.session.commit()
            flash(f"✅ Borrador de protección de datos guardado correctamente. Progreso actual: {progreso_pct}%.", "success")
            return redirect(url_for("madurez_datos.ingreso"))

        if accion == "analizar":
            if progreso_pct < 100 or respondidas < total:
                db.session.commit()
                flash(
                    f"⚠️ El análisis solo se habilita cuando el instrumento esté al 100%. Actualmente llevas {progreso_pct}%.",
                    "warning"
                )
                return redirect(url_for("madurez_datos.ingreso"))

            acc = {}
            sum_all = 0.0
            cnt_all = 0

            respuestas = (
                db.session.query(DatosMadurezRespuesta, DatosMadurezPregunta)
                .join(DatosMadurezPregunta, DatosMadurezPregunta.id == DatosMadurezRespuesta.pregunta_id)
                .filter(DatosMadurezRespuesta.run_id == run.id)
                .order_by(DatosMadurezPregunta.orden.asc())
                .all()
            )

            for r, q in respuestas:
                st = (r.estado or "").strip().upper()
                score = GDPR_STATUS_SCORE.get(st)
                if score is None:
                    continue

                dom = (q.dominio or "SIN_DOMINIO").strip()
                acc.setdefault(dom, {
                    "sum": 0.0,
                    "count": 0,
                    "items": []
                })

                acc[dom]["sum"] += float(score)
                acc[dom]["count"] += 1
                acc[dom]["items"].append({
                    "codigo": q.codigo,
                    "titulo": q.titulo,
                    "pregunta": q.pregunta,
                    "estado": st,
                    "comentario": r.comentario or "",
                    "score": float(score)
                })

                sum_all += float(score)
                cnt_all += 1

            out = {}
            for dom, d in acc.items():
                pct = round((d["sum"] / d["count"]) if d["count"] else 0.0, 2)
                out[dom] = {
                    "pct": pct,
                    "total": d["count"],
                    "items": d["items"]
                }

            pct_general = round((sum_all / cnt_all) if cnt_all else 0.0, 2)
            run.resumen_json = json.dumps(out, ensure_ascii=False)
            run.pct_general = pct_general
            run.estado = "FINALIZADO"
            run.progreso_pct = 100

            db.session.commit()

            niv = gdpr_nivel_visual_por_pct(pct_general)
            flash(
                f"✅ Revisión de protección de datos guardada y analizada. Nivel general: {pct_general:.2f}% · Madurez: {niv['nivel']}",
                "success"
            )
            return redirect(url_for("madurez_datos.detalle", run_id=run.id))

        db.session.commit()
        flash("✅ Información procesada correctamente.", "success")
        return redirect(url_for("madurez_datos.ingreso"))

    except Exception as e:
        db.session.rollback()
        flash(f"⚠️ Error en el proceso: {e}", "danger")
        return redirect(url_for("madurez_datos.ingreso"))


# =====================================================================
# HISTORIAL
# =====================================================================

@madurez_datos_bp.route("/historial", methods=["GET"])
@login_required
def historial():
    user = User.query.get(session.get("user_id"))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez protección de datos personales"):
        flash("No tiene permiso para acceder al módulo de nivel de madurez de protección de datos personales.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == "auditor")

    runs = DatosMadurezRun.query.order_by(
        DatosMadurezRun.created_at.desc(),
        DatosMadurezRun.id.desc()
    ).limit(200).all()

    rows = []
    for r in runs:
        nivel = gdpr_nivel_visual_por_pct(r.pct_general)

        if read_only:
            delete_btn = """
            <button type="button"
                    class="btn btn-sm btn-outline-secondary rounded-pill"
                    disabled
                    title="El perfil Auditor no puede eliminar registros">
              Eliminar
            </button>
            """
        else:
            delete_btn = f"""
            <form method="post"
                  action="{url_for('madurez_datos.eliminar_run', run_id=r.id)}"
                  onsubmit="return confirm('¿Desea eliminar este registro?');"
                  style="margin:0; display:inline;">
              <button type="submit"
                      class="btn btn-sm btn-outline-danger rounded-pill">
                Eliminar
              </button>
            </form>
            """

        rows.append(f"""
        <tr>
          <td>{r.id}</td>
          <td>{escape(r.consecutivo or '')}</td>
          <td>{escape(r.estado or '')}</td>
          <td>{r.pct_general:.2f}%</td>
          <td>
            <span class="badge rounded-pill px-3 py-2"
                  style="background:{nivel['color']}; color:#fff;">
              {escape(nivel['nivel'])}
            </span>
          </td>
          <td>{r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else ''}</td>
          <td class="text-end">
            <div class="d-flex justify-content-end gap-2 flex-wrap">
              <a class="btn btn-sm btn-outline-primary rounded-pill"
                   href="{url_for('madurez_datos.detalle', run_id=r.id)}">
                  Ver detalle
              </a>

              <a class="btn btn-sm btn-outline-danger rounded-pill"
                   href="{url_for('madurez_datos.detalle_pdf_datos', run_id=r.id)}"
                   data-no-progress="true">
                  📄 PDF
              </a>

                {delete_btn}
            </div>
          </td>
        </tr>
        """)

    content = f"""
    <div class="datstd-shell">

      <div class="datstd-header-card">
        <div class="datstd-header-overlay">
          <div class="datstd-header-text">
            <h3 class="datstd-title m-0">Historial — Protección de Datos Personales</h3>
            <div class="datstd-subtitle">
              Consulta revisiones guardadas, porcentaje general, nivel de madurez y acceso al detalle.
            </div>
          </div>
        </div>
      </div>

      <div class="datstd-header-actions">
        <a href="{url_for('madurez_datos.inicio')}"
           class="btn datstd-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al Inicio
        </a>
      </div>

      {"<div class='alert alert-info'>🔒 El perfil Auditor puede consultar el historial, pero no puede eliminar ni generar/editar contenido con IA.</div>" if read_only else ""}

      <div class="datstd-card p-4">
        <div class="datstd-section-title">Revisiones guardadas</div>

        <div class="table-responsive datstd-table-wrap">
          <table class="table table-sm align-middle table-hover mb-0">
            <thead class="datstd-table-head">
              <tr>
                <th>ID</th>
                <th>Consecutivo</th>
                <th>Estado</th>
                <th>% General</th>
                <th>Nivel</th>
                <th>Fecha</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows) if rows else "<tr><td colspan='7' class='text-muted text-center py-4'>Sin registros.</td></tr>"}
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .datstd-shell{{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }}

      .datstd-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .datstd-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .datstd-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .datstd-header-overlay::before{{
        content:"📚";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .datstd-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .datstd-header-text::before{{
        content:"SGSI · Estándares de Datos Personales";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .datstd-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .datstd-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .datstd-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .datstd-header-actions .btn,
      .btn{{
        border-radius:999px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .datstd-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .datstd-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .datstd-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .datstd-card.p-4{{
        padding:1.5rem !important;
      }}

      .datstd-section-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:12px;
      }}

      .datstd-section-title{{
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }}

      .datstd-table-wrap,
      .table-responsive{{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }}

      .table{{
        margin-bottom:0;
      }}

      .datstd-table-head th,
      .table thead th{{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-size:.78rem;
        font-weight:900 !important;
        border:none !important;
        white-space:nowrap;
        vertical-align:middle !important;
        text-align:center;
        padding:9px 8px;
      }}

      .table tbody td{{
        vertical-align:middle;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }}

      .table tbody tr:nth-child(even){{
        background:#f8fbff;
      }}

      .table-hover tbody tr:hover,
      .table tbody tr:hover{{
        background:#eef6ff;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:991.98px){{
        .datstd-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .datstd-header-card{{
          min-height:88px;
        }}

        .datstd-title{{
          font-size:1.20rem;
        }}

        .datstd-subtitle{{
          font-size:.68rem;
        }}
      }}

      @media (max-width:768px){{
        .datstd-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .datstd-header-overlay::before{{
          margin:0;
        }}

        .datstd-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .datstd-title,
        .datstd-subtitle{{
          text-align:center;
        }}

        .datstd-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Historial Protección de Datos", content=content)

@madurez_datos_bp.route("/detalle/<int:run_id>/pdf", methods=["GET"], endpoint="detalle_pdf_datos")
@login_required
def detalle_pdf_datos(run_id: int):
    run = DatosMadurezRun.query.get_or_404(run_id)

    filename = f"Proteccion_Datos_{(run.consecutivo or 'revision').replace(' ', '_')}.pdf"

    return send_file(
        _gdpr_build_pdf_run(run),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )


# =========================
# ELIMINAR RUN
# =========================
@madurez_datos_bp.route("/eliminar/<int:run_id>", methods=["POST"])
@login_required
def eliminar_run(run_id):
    user = User.query.get(session.get("user_id"))

    # 🔒 Solo admin
    if user.role != 'admin':
        flash("No tiene permiso para eliminar registros.", "danger")
        return redirect(url_for('madurez_datos.historial'))

    run = DatosMadurezRun.query.get_or_404(run_id)

    try:
        db.session.delete(run)
        db.session.commit()
        flash("Registro eliminado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar: {str(e)}", "danger")

    return redirect(url_for('madurez_datos.historial'))

@madurez_datos_bp.route("/detalle/<int:run_id>/dominio/<path:dominio>/preguntas", methods=["GET"])
@login_required
def detalle_dominio_preguntas(run_id: int, dominio: str):
    user = User.query.get(session.get("user_id"))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez protección de datos personales"):
        flash("No tiene permiso para acceder al detalle del dominio.", "danger")
        return redirect(url_for('menu'))

    run = DatosMadurezRun.query.get_or_404(run_id)
    dominio_txt = (dominio or "").strip()

    items = _gdpr_get_items_dominio(run.id, dominio_txt)

    rows = []
    for it in items:
        estado = it.get("estado", "")
        badge_map = {
            "SI": "success",
            "PARCIAL": "warning text-dark",
            "NO": "danger",
            "NA": "secondary"
        }
        badge_cls = badge_map.get(estado, "secondary")

        rows.append(f"""
        <tr>
          <td class="datadom-pregunta">
            <div class="fw-bold">{escape(it.get('codigo') or '')}</div>
            <div>{escape(it.get('pregunta') or '')}</div>
          </td>
          <td class="col-estado text-center">
            <span class="badge bg-{badge_cls}">{escape(estado)}</span>
          </td>
          <td class="datadom-comentario">
            {escape(it.get('comentario') or '')}
          </td>
        </tr>
        """)

    content = f"""
    <div class="datadom-shell">
      <div class="datadom-header-card">
        <div class="datadom-header-overlay">
          <div class="datadom-header-text">
            <h3 class="datadom-title m-0">Preguntas por Dominio</h3>
            <div class="datadom-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b> · Dominio: <b>{escape(dominio_txt)}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="datadom-header-actions">
        <a href="{url_for('madurez_datos.detalle', run_id=run.id)}"
           class="btn datadom-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al detalle
        </a>
      </div>

      <div class="datadom-card p-4">
        <div class="datadom-section-title">Detalle de preguntas y evidencias</div>

        <div class="datadom-table-wrap">
          <table class="table table-hover align-middle datadom-table">
            <thead class="datadom-table-head">
              <tr>
                <th>Pregunta</th>
                <th class="col-estado text-center">Estado</th>
                <th>Comentario / Evidencia</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows) if rows else '<tr><td colspan="3" class="text-center text-muted py-4">No hay preguntas para este dominio.</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .datadom-shell{{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }}

      .datadom-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .datadom-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .datadom-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .datadom-header-overlay::before{{
        content:"📂";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .datadom-header-text{{
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .datadom-header-text::before{{
        content:"SGSI · Detalle de Dominio Datos Personales";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .datadom-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .datadom-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .datadom-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .datadom-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .datadom-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .datadom-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .datadom-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .datadom-section-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }}

      .datadom-table-wrap,
      .table-responsive{{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }}

      .datadom-table,
      .table{{
        width:100%;
        margin-bottom:0 !important;
        table-layout:fixed;
      }}

      .datadom-table-head th,
      .table thead th{{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-size:.78rem;
        font-weight:900 !important;
        border:none !important;
        white-space:nowrap;
        vertical-align:middle !important;
        text-align:center;
        padding:9px 8px;
      }}

      .datadom-table th,
      .datadom-table td,
      .table tbody td{{
        vertical-align:middle !important;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }}

      .datadom-table .col-estado{{
        width:140px;
      }}

      .datadom-pregunta,
      .datadom-comentario,
      .wrap{{
        white-space:normal !important;
        word-break:break-word;
        overflow-wrap:anywhere;
      }}

      .table tbody tr:nth-child(even){{
        background:#f8fbff;
      }}

      .table-hover tbody tr:hover,
      .table tbody tr:hover{{
        background:#eef6ff;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:991.98px){{
        .datadom-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .datadom-header-card{{
          min-height:88px;
        }}

        .datadom-title{{
          font-size:1.20rem;
        }}

        .datadom-subtitle{{
          font-size:.68rem;
        }}

        .datadom-table{{
          table-layout:auto;
        }}
      }}

      @media (max-width:768px){{
        .datadom-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .datadom-header-overlay::before{{
          margin:0;
        }}

        .datadom-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .datadom-title,
        .datadom-subtitle{{
          text-align:center;
        }}

        .datadom-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Preguntas por Dominio", content=content)

@madurez_datos_bp.route("/detalle/<int:run_id>/plan-trabajo/editar", methods=["GET", "POST"])
@login_required
def plan_trabajo_editar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede editar el plan de trabajo.", "danger")
        return redirect(url_for("madurez_datos.detalle", run_id=run_id))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez protección de datos personales"):
        flash("No tiene permiso para editar el plan de trabajo.", "danger")
        return redirect(url_for('menu'))

    run = DatosMadurezRun.query.get_or_404(run_id)
    texto_actual = _gdpr_normalizar_texto_plano_guardado(
        run.plan_trabajo_editado or run.plan_trabajo_ai or ""
    )

    if request.method == "POST":
        texto = _gdpr_normalizar_texto_plano_guardado(
            (request.form.get("plan_trabajo") or "").strip()
        )
        run.plan_trabajo_editado = texto
        db.session.commit()
        flash("✅ Plan de trabajo actualizado.", "success")
        return redirect(url_for("madurez_datos.detalle", run_id=run.id))

    content = f"""
    <div class="datstd-shell">

      <div class="datstd-header-card">
        <div class="datstd-header-overlay">
          <div class="datstd-header-text">
            <h3 class="datstd-title m-0">Editar Plan de Trabajo — Protección de Datos Personales</h3>
            <div class="datstd-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="datstd-header-actions">
        <a href="{url_for('madurez_datos.detalle', run_id=run.id)}"
           class="btn datstd-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al detalle
        </a>
      </div>

      <div class="datstd-card p-4">
        <form method="POST">
          <div class="datstd-section-title">Plan de trabajo editable</div>

          <div class="text-muted small mb-3">
            Ajusta el contenido del plan de trabajo y guarda los cambios.
          </div>

          <textarea name="plan_trabajo"
                    class="form-control datstd-textarea"
                    rows="20"
                    placeholder="Escribe o ajusta aquí el plan de trabajo...">{escape(texto_actual)}</textarea>

          <div class="d-flex justify-content-center mt-4">
            <button type="submit" class="btn btn-primary rounded-pill px-5 fw-bold">
              <i class="bi bi-save2 me-2"></i>Guardar cambios
            </button>
          </div>
        </form>
      </div>
    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .datstd-shell{{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }}

      .datstd-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .datstd-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .datstd-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .datstd-header-overlay::before{{
        content:"📄";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .datstd-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .datstd-header-text::before{{
        content:"SGSI · Estándar Datos Personales";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .datstd-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }}

      .datstd-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .datstd-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .datstd-header-actions .btn,
      .datstd-btn-main,
      .btn{{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .datstd-btn-main{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .datstd-btn-main:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }}

      .datstd-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .datstd-card.p-4{{
        padding:1.5rem !important;
      }}

      .datstd-section-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
      }}

      .datstd-section-title{{
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }}

      .datstd-textarea{{
        min-height:420px;
        border-radius:14px;
        border:1px solid #d9e3f0;
        resize:vertical;
        background:#f8fafc;
        font-size:.86rem;
        padding:14px 16px;
        box-shadow:none !important;
      }}

      .datstd-textarea:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .form-label{{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:6px 10px;
        border-radius:10px;
        display:inline-block;
        margin-bottom:6px;
      }}

      .form-control,
      .form-select{{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      .form-control:focus,
      .form-select:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:992px){{
        .datstd-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .datstd-header-card{{
          min-height:88px;
        }}

        .datstd-title{{
          font-size:1.20rem;
        }}

        .datstd-subtitle{{
          font-size:.68rem;
        }}

        .datstd-card.p-4{{
          padding:1rem !important;
        }}

        .datstd-textarea{{
          min-height:320px;
        }}
      }}

      @media (max-width:768px){{
        .datstd-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .datstd-header-overlay::before{{
          margin:0;
        }}

        .datstd-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .datstd-title,
        .datstd-subtitle{{
          text-align:center;
        }}

        .datstd-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Editar Plan de Trabajo Datos Personales", content=content)

@madurez_datos_bp.route("/detalle/<int:run_id>/plan-trabajo/generar", methods=["POST"])
@login_required
def plan_trabajo_generar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede generar el plan de trabajo con IA.", "danger")
        return redirect(url_for("madurez_datos.detalle", run_id=run_id))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez protección de datos personales"):
        flash("No tiene permiso para generar el plan de trabajo.", "danger")
        return redirect(url_for('menu'))

    run = DatosMadurezRun.query.get_or_404(run_id)

    if user.role not in ("admin", "auditor"):
        if run.user_id and run.user_id != user.id:
            flash("No tiene permiso para generar IA sobre esta revisión.", "danger")
            return redirect(url_for("madurez_datos.historial"))

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    if not resumen:
        flash("⚠️ No hay resultados consolidados para generar el plan de trabajo.", "warning")
        return redirect(url_for("madurez_datos.detalle", run_id=run.id))

    prompt = _gdpr_prompt_plan_trabajo(run, resumen)

    try:
        raw = _ai_text(prompt, max_tokens=1800)
    except Exception as e:
        flash(f"❌ Error llamando IA para el plan de trabajo: {e}", "danger")
        return redirect(url_for("madurez_datos.detalle", run_id=run.id))

    plan_texto = ""

    try:
        obj = _gdpr_extraer_json_objeto(raw)
        if isinstance(obj, dict):
            plan_texto = _gdpr_plan_trabajo_a_texto(obj.get("plan_trabajo", []))
    except Exception:
        plan_texto = ""

    if not plan_texto:
        plan_texto = (raw or "").strip()

    # LIMPIAR HTML/TAGS ANTES DE GUARDAR
    plan_texto = _gdpr_normalizar_texto_plano_guardado(plan_texto)

    if not plan_texto:
        flash("⚠️ La IA no devolvió contenido para el plan de trabajo.", "warning")
        return redirect(url_for("madurez_datos.detalle", run_id=run.id))

    # sincronizar ambos campos para que se vea limpio de inmediato
    run.plan_trabajo_ai = plan_texto
    run.plan_trabajo_editado = plan_texto

    db.session.commit()
    flash("✅ Plan de trabajo generado con IA.", "success")
    return redirect(url_for("madurez_datos.detalle", run_id=run.id))

@madurez_datos_bp.route("/detalle/<int:run_id>/dominio/<path:dominio>/analisis", methods=["GET", "POST"])
@login_required
def analisis_dominio(run_id: int, dominio: str):
    user = User.query.get(session.get("user_id"))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez protección de datos personales"):
        flash("No tiene permiso para acceder al análisis del dominio.", "danger")
        return redirect(url_for('menu'))

    run = DatosMadurezRun.query.get_or_404(run_id)
    dominio_txt = (dominio or "").strip()
    read_only = (user.role == "auditor")
    modo_edicion = request.args.get("editar", "0") == "1"

    if read_only and modo_edicion:
        return redirect(url_for("madurez_datos.analisis_dominio", run_id=run.id, dominio=dominio_txt))

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    d = (resumen or {}).get(dominio_txt, {}) or {}
    pct = float(d.get("pct", 0) or 0)

    ana = (
        DatosMadurezDominioAnalisis.query
        .filter_by(run_id=run.id, dominio=dominio_txt)
        .first()
    )

    if request.method == "POST":
        if read_only:
            flash("El perfil Auditor no puede guardar cambios en el análisis del dominio.", "danger")
            return redirect(url_for("madurez_datos.analisis_dominio", run_id=run.id, dominio=dominio_txt))

        estado_actual = (request.form.get("estado_actual") or "").strip()
        estado_requerido = (request.form.get("estado_requerido") or "").strip()
        plan_editado = (request.form.get("plan_accion_editado") or "").strip()

        if not ana:
            ana = DatosMadurezDominioAnalisis(run_id=run.id, dominio=dominio_txt)
            db.session.add(ana)

        ana.estado_actual = estado_actual
        ana.estado_requerido = estado_requerido
        ana.plan_accion_editado = plan_editado

        db.session.commit()
        flash("✅ Análisis guardado.", "success")
        return redirect(url_for("madurez_datos.analisis_dominio", run_id=run.id, dominio=dominio_txt))

    estado_actual = (ana.estado_actual if ana else "") or ""
    estado_requerido = (ana.estado_requerido if ana else "") or ""
    plan_ai = (ana.plan_accion_ai if ana else "") or ""
    plan_editado = (ana.plan_accion_editado if ana else "") or ""
    plan_mostrar = plan_editado or plan_ai

    if read_only:
        toggle_btn = """
        <button class="btn btn-outline-secondary rounded-pill px-4 fw-bold"
                type="button"
                disabled
                title="El perfil Auditor no puede editar el análisis del dominio">
          <i class="bi bi-pencil-square me-2"></i>Editar
        </button>
        """
    else:
        toggle_btn = (
            f"""
            <a href="{url_for('madurez_datos.analisis_dominio', run_id=run.id, dominio=dominio_txt)}"
               class="btn datstd-btn-main rounded-pill px-4 fw-bold">
              <i class="bi bi-eye me-2"></i>Ver modo lectura
            </a>
            """
            if modo_edicion else
            f"""
            <a href="{url_for('madurez_datos.analisis_dominio', run_id=run.id, dominio=dominio_txt, editar=1)}"
               class="btn btn-primary rounded-pill px-4 fw-bold">
              <i class="bi bi-pencil-square me-2"></i>Editar
            </a>
            """
        )

    if modo_edicion and not read_only:
        panel_izq = f"""
        <div class="col-12 col-lg-6">
          <div class="datstd-card p-4 h-100">
            <div class="datstd-section-title">✏️ Edición manual del análisis</div>
            <div class="text-muted small mb-3">
              Ajusta los textos generados y guarda los cambios.
            </div>

            <form method="POST">
              <div class="datstd-section-title">📌 Estado actual</div>
              <textarea class="form-control datstd-textarea"
                        name="estado_actual"
                        rows="8">{escape(estado_actual)}</textarea>

              <div class="datstd-section-title mt-3">🎯 Estado requerido</div>
              <textarea class="form-control datstd-textarea"
                        name="estado_requerido"
                        rows="7">{escape(estado_requerido)}</textarea>

              <div class="datstd-section-title mt-3">🛠 Plan de acción (editable)</div>
              <textarea class="form-control datstd-textarea"
                        name="plan_accion_editado"
                        rows="12">{escape(plan_editado)}</textarea>

              <div class="d-flex justify-content-center mt-3">
                <button class="btn btn-primary rounded-pill px-5 fw-bold" type="submit">
                  <i class="bi bi-save2 me-2"></i>Guardar cambios
                </button>
              </div>
            </form>
          </div>
        </div>
        """

        panel_der = f"""
        <div class="col-12 col-lg-6">
          <div class="datstd-card p-4 h-100">
            <div class="datstd-section-title">🤖 Generación con IA</div>
            <div class="text-muted small mt-1">
              Genera o regenera automáticamente el análisis del dominio.
            </div>

            <div class="text-center mt-4">
              <form method="POST"
                    action="{url_for('madurez_datos.analisis_dominio_generar', run_id=run.id, dominio=dominio_txt)}"
                    class="m-0 mt-4">
                <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                  <i class="bi bi-magic me-2"></i>Generar análisis (IA)
                </button>
              </form>
            </div>
          </div>
        </div>
        """
    else:
        panel_izq = f"""
        <div class="col-12 col-lg-6">
          <div class="datstd-card p-4 h-100">
            <div class="datstd-section-title">📄 Análisis del dominio</div>

            <div class="datstd-read-box mt-2">
              <b>📌 Estado actual</b><br>
              {escape(estado_actual) if estado_actual else "<span class='text-muted'>Pendiente por generar con IA.</span>"}
            </div>

            <div class="datstd-read-box mt-3">
              <b>🎯 Estado requerido</b><br>
              {escape(estado_requerido) if estado_requerido else "<span class='text-muted'>Pendiente por generar con IA.</span>"}
            </div>

            <div class="datstd-read-box mt-3">
              <b>🛠 Plan de acción</b><br>
              {escape(plan_mostrar) if plan_mostrar else "<span class='text-muted'>Pendiente por generar con IA.</span>"}
            </div>
          </div>
        </div>
        """

        if read_only:
            panel_der = """
            <div class="col-12 col-lg-6">
              <div class="datstd-card p-4 h-100">
                <div class="datstd-section-title">🤖 Generación con IA</div>
                <div class="text-muted small mt-1">
                  El perfil Auditor puede consultar el análisis, pero no puede editarlo ni generarlo con IA.
                </div>

                <div class="text-center mt-4">
                  <button class="btn btn-outline-secondary rounded-pill px-4 fw-bold" type="button" disabled
                          title="El perfil Auditor no puede generar análisis con IA">
                    <i class="bi bi-magic me-2"></i>Generar análisis (IA)
                  </button>
                </div>
              </div>
            </div>
            """
        else:
            panel_der = f"""
            <div class="col-12 col-lg-6">
              <div class="datstd-card p-4 h-100">
                <div class="datstd-section-title">🤖 Generación con IA</div>
                <div class="text-muted small mt-1">
                  Usa este botón para generar o regenerar el análisis del dominio.
                </div>

                <div class="text-center mt-4">
                  <form method="POST"
                        action="{url_for('madurez_datos.analisis_dominio_generar', run_id=run.id, dominio=dominio_txt)}"
                        class="m-0">
                    <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                      <i class="bi bi-magic me-2"></i>Generar análisis (IA)
                    </button>
                  </form>
                </div>
              </div>
            </div>
            """

    content = f"""
    <div class="datstd-shell">

      <div class="datstd-header-card">
        <div class="datstd-header-overlay">
          <div class="datstd-header-text">
            <h3 class="datstd-title m-0">Análisis por Dominio</h3>
            <div class="datstd-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b> · Dominio: <b>{escape(dominio_txt)}</b> · Cumplimiento: <b>{pct:.2f}%</b>
            </div>
          </div>
        </div>
      </div>

      <div class="datstd-header-actions">
        <a href="{url_for('madurez_datos.detalle', run_id=run.id)}"
           class="btn datstd-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al detalle
        </a>
        {toggle_btn}
      </div>

      {"<div class='alert alert-info'>🔒 El perfil Auditor puede ver el análisis del dominio, pero no puede usar Editar ni Generar análisis (IA).</div>" if read_only else ""}

      <div class="row g-3">
        {panel_izq}
        {panel_der}
      </div>

    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .datstd-shell{{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }}

      .datstd-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .datstd-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .datstd-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .datstd-header-overlay::before{{
        content:"🤖";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .datstd-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .datstd-header-text::before{{
        content:"SGSI · Análisis Datos Personales";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .datstd-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .datstd-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .datstd-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .datstd-header-actions .btn,
      .btn{{
        border-radius:999px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .datstd-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .datstd-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .datstd-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .datstd-card.p-4{{
        padding:1.5rem !important;
      }}

      .datstd-section-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:10px;
      }}

      .datstd-textarea{{
        border-radius:14px !important;
        border:1px solid #d9e3f0 !important;
        box-shadow:none !important;
        resize:vertical;
        background:#f8fafc;
      }}

      .datstd-textarea:focus{{
        border-color:#3f86d6 !important;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .datstd-read-box{{
        min-height:110px;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
        padding:14px 16px;
        color:#243443;
        white-space:pre-wrap;
        word-break:break-word;
        overflow-wrap:anywhere;
      }}

      .form-label{{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:6px 10px;
        border-radius:10px;
        display:inline-block;
        margin-bottom:6px;
      }}

      .form-control,
      .form-select{{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      .form-control:focus,
      .form-select:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:991.98px){{
        .datstd-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .datstd-header-card{{
          min-height:88px;
        }}

        .datstd-title{{
          font-size:1.20rem;
        }}

        .datstd-subtitle{{
          font-size:.68rem;
        }}

        .datstd-read-box{{
          min-height:90px;
        }}
      }}

      @media (max-width:768px){{
        .datstd-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .datstd-header-overlay::before{{
          margin:0;
        }}

        .datstd-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .datstd-title,
        .datstd-subtitle{{
          text-align:center;
        }}

        .datstd-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Análisis de Dominio Datos Personales", content=content)

@madurez_datos_bp.route("/detalle/<int:run_id>/dominio/<path:dominio>/analisis/generar", methods=["POST"])
@login_required
def analisis_dominio_generar(run_id: int, dominio: str):
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede generar análisis del dominio con IA.", "danger")
        return redirect(url_for("madurez_datos.analisis_dominio", run_id=run_id, dominio=(dominio or "").strip()))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez protección de datos personales"):
        flash("No tiene permiso para generar análisis del dominio.", "danger")
        return redirect(url_for('menu'))

    run = DatosMadurezRun.query.get_or_404(run_id)
    dominio_txt = (dominio or "").strip()

    if user.role not in ("admin", "auditor"):
        if run.user_id and run.user_id != user.id:
            flash("No tiene permiso para generar IA sobre esta revisión.", "danger")
            return redirect(url_for("madurez_datos.historial"))

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    d = (resumen or {}).get(dominio_txt, {}) or {}
    pct = float(d.get("pct", 0) or 0)

    items = _gdpr_get_items_dominio(run.id, dominio_txt)
    if not items:
        flash("⚠️ No hay preguntas/respuestas para este dominio en esta revisión.", "warning")
        return redirect(url_for("madurez_datos.analisis_dominio", run_id=run.id, dominio=dominio_txt))

    prompt = _gdpr_ai_prompt_dominio(dominio_txt, pct, items)

    try:
        raw = _ai_text(prompt, max_tokens=1800)
    except Exception as e:
        flash(f"❌ Error llamando IA: {e}", "danger")
        return redirect(url_for("madurez_datos.analisis_dominio", run_id=run.id, dominio=dominio_txt))

    obj = _gdpr_extraer_json_objeto(raw)

    estado_actual = (obj.get("estado_actual") or "").strip() if isinstance(obj, dict) else ""
    estado_requerido = (obj.get("estado_requerido") or "").strip() if isinstance(obj, dict) else ""
    plan_ai = _gdpr_plan_accion_a_texto(obj.get("plan_accion", [])) if isinstance(obj, dict) else ""

    if not estado_actual:
        estado_actual = "No se pudo interpretar correctamente el estado actual generado por la IA. Se recomienda regenerar el análisis."

    if not estado_requerido:
        estado_requerido = "No se pudo interpretar correctamente el estado requerido generado por la IA. Se recomienda regenerar el análisis."

    if not plan_ai or plan_ai.strip().startswith("{"):
        plan_ai = "No se pudo generar correctamente el plan de acción. Regenera el análisis."

    ana = (
        DatosMadurezDominioAnalisis.query
        .filter_by(run_id=run.id, dominio=dominio_txt)
        .first()
    )

    if not ana:
        ana = DatosMadurezDominioAnalisis(run_id=run.id, dominio=dominio_txt)
        db.session.add(ana)

    ana.estado_actual = estado_actual
    ana.estado_requerido = estado_requerido
    ana.plan_accion_ai = plan_ai
    ana.plan_accion_editado = plan_ai

    db.session.commit()

    flash("✅ Análisis generado por IA y guardado.", "success")
    return redirect(url_for("madurez_datos.analisis_dominio", run_id=run.id, dominio=dominio_txt))

# ==========
# DETALLE / RESULTADO
# ==========

@madurez_datos_bp.route("/detalle/<int:run_id>", methods=["GET"])
@login_required
def detalle(run_id):
    user = User.query.get(session.get("user_id"))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez protección de datos personales"):
        flash("No tiene permiso para acceder al módulo de nivel de madurez de protección de datos personales.", "danger")
        return redirect(url_for('menu'))

    run = DatosMadurezRun.query.get_or_404(run_id)

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    def esc(x):
        return escape(x or "")

    def _nl2br(s: str) -> str:
        txt = _gdpr_normalizar_texto_plano_guardado(s or "")
        return txt.replace("\n", "<br>")

    nivel_general = gdpr_nivel_visual_por_pct(run.pct_general)
    nivel_general_texto = (nivel_general.get("nivel") or "").strip()
    nivel_general_nombre = nivel_general_texto.split(":", 1)[1].strip() if ":" in nivel_general_texto else nivel_general_texto

    radar_b64 = generar_radar_datos_base64(resumen)

    informe_ai = _gdpr_normalizar_texto_plano_guardado(run.informe_ejecutivo_ai or "")
    informe_editado = _gdpr_normalizar_texto_plano_guardado(run.informe_ejecutivo_editado or "")
    informe_mostrar = informe_editado if informe_editado else informe_ai

    plan_ai = _gdpr_normalizar_texto_plano_guardado(run.plan_trabajo_ai or "")
    plan_editado = _gdpr_normalizar_texto_plano_guardado(run.plan_trabajo_editado or "")
    plan_mostrar = plan_editado if plan_editado else plan_ai

    pdf_btn = ""
    try:
        pdf_btn = f"""
        <a href="{url_for('madurez_datos.exportar_pdf', run_id=run.id)}"
           class="btn btn-danger rounded-pill px-4 fw-bold"
           target="_blank">
          <i class="bi bi-file-earmark-pdf me-2"></i>Exportar PDF
        </a>
        """
    except Exception:
        pdf_btn = ""

    top_html = f"""
    <div class="row g-3 mb-4">

      <div class="col-12 col-xl-5">
        <div class="datares-card p-4 h-100">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
            <div>
              <div class="datares-card-title">📊 Radar por dominios</div>
              <div class="text-muted small">
                Resultado consolidado del programa de protección de datos personales.
              </div>
            </div>

            <div class="text-end">
              <div class="badge rounded-pill px-3 py-2"
                   style="background:{nivel_general.get('color','#6c757d')}; color:#fff; font-size:.82rem;">
                Nivel {nivel_general.get('score', 0)}
              </div>
              <div class="small text-muted mt-1">{esc(nivel_general_nombre)}</div>
            </div>
          </div>

          <div class="text-center mt-3 datares-radar-wrap">
            <div class="datares-radar-pct-box">
              <div class="datares-radar-pct-label">Cumplimiento general</div>
              <div class="datares-radar-pct-value">{float(run.pct_general or 0):.2f}%</div>
              <div class="datares-radar-pct-subtitle">
                Nivel {nivel_general.get('score', 0)} · {esc(nivel_general_nombre)}
              </div>
            </div>

            {f'<img class="img-fluid datares-radar-small" src="data:image/png;base64,{radar_b64}">' if radar_b64 else '<div class="alert alert-warning mb-0">No fue posible generar el radar.</div>'}
          </div>
        </div>
      </div>

      <div class="col-12 col-xl-7">
        <div class="datares-card p-4 h-100">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div>
              <div class="datares-card-title">🧾 Informe ejecutivo</div>
              <div class="text-muted small">
                Síntesis ejecutiva generada con IA a partir de los resultados por dominio.
              </div>
            </div>

            <div class="d-flex gap-2 flex-wrap">
              <form method="POST"
                    action="{url_for('madurez_datos.informe_ejecutivo_generar', run_id=run.id)}"
                    class="m-0">
                <button type="submit" class="btn datares-btn-success rounded-pill px-4 fw-bold">
                  <i class="bi bi-magic me-2"></i>Generar con IA
                </button>
              </form>

              <a href="{url_for('madurez_datos.informe_ejecutivo_editar', run_id=run.id)}"
                 class="btn btn-primary rounded-pill px-4 fw-bold">
                <i class="bi bi-pencil-square me-2"></i>Editar
              </a>
            </div>
          </div>

          <div class="datares-exec-box mt-3">
            {f'<div class="datares-exec-text">{_nl2br(esc(informe_mostrar))}</div>' if informe_mostrar else '''
              <div class="text-center py-4">
                <div class="mb-2" style="font-size:2rem;">&#129302;</div>
                <div class="fw-bold text-black">Aún no hay informe ejecutivo</div>
                <div class="text-muted small mt-1">
                  Presiona <b>Generar con IA</b> para construir el informe con base en el resultado de los dominios.
                </div>
              </div>
            '''}
          </div>
        </div>
      </div>

    </div>

    <div class="row g-3 mb-4">

      <div class="col-12">
        <div class="datares-card p-4">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div>
              <div class="datares-card-title">🗂️ Plan de trabajo</div>
              <div class="text-muted small">
                Plan general de cierre de brechas derivado del resultado.
              </div>
            </div>

            <div class="d-flex gap-2 flex-wrap">
              <form method="POST"
                    action="{url_for('madurez_datos.plan_trabajo_generar', run_id=run.id)}"
                    class="m-0">
                <button type="submit" class="btn datares-btn-success rounded-pill px-4 fw-bold">
                  <i class="bi bi-magic me-2"></i>Generar con IA
                </button>
              </form>

              <a href="{url_for('madurez_datos.plan_trabajo_editar', run_id=run.id)}"
                 class="btn btn-primary rounded-pill px-4 fw-bold">
                <i class="bi bi-pencil-square me-2"></i>Editar
              </a>
            </div>
          </div>

          <div class="datares-exec-box datares-plan-box mt-3">
            {f'<div class="datares-exec-text">{_nl2br(plan_mostrar)}</div>' if plan_mostrar else '''
              <div class="text-center py-4">
                <div class="mb-2" style="font-size:2rem;">&#128450;</div>
                <div class="fw-bold text-black">Aún no hay plan de trabajo</div>
                <div class="text-muted small mt-1">
                  Presiona <b>Generar con IA</b> para construir el plan general.
                </div>
              </div>
            '''}
          </div>
        </div>
      </div>

    </div>
    """

    tarjetas = []
    for dominio, data in resumen.items():
        try:
            pct = float(data.get("pct", 0) or 0)
        except Exception:
            pct = 0.0

        total = int(data.get("total", 0) or 0)
        items = data.get("items", []) or []
        niv = gdpr_nivel_visual_por_pct(pct)

        counts = {"SI": 0, "PARCIAL": 0, "NO": 0, "NA": 0}
        for it in items:
            st = (it.get("estado") or "").strip().upper()
            if st in counts:
                counts[st] += 1

        gauge_b64 = generar_gdpr_velocimetro_base64(
            dominio,
            pct,
            niv.get("nivel", ""),
            niv.get("color", "#6c757d")
        )

        nivel_texto = (niv.get("nivel") or "").strip()
        nivel_nombre = nivel_texto.split(":", 1)[1].strip() if ":" in nivel_texto else nivel_texto

        tarjetas.append(f"""
        <div class="col-12 col-lg-6">
          <div class="datares-card p-4 h-100">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-3">
              <div>
                <div class="datares-domain-title">{esc(dominio)}</div>
                <div class="small text-muted">Ítems evaluados: <b>{total}</b></div>
              </div>

              <div class="text-end">
                <span class="badge rounded-pill px-3 py-2"
                      style="background:{niv.get('color','#6c757d')}; color:#fff;">
                  Nivel {niv.get('score', 0)}
                </span>
                <div class="small text-muted mt-1">{esc(nivel_nombre)}</div>
              </div>
            </div>

            <div class="text-center datares-gauge-wrap">
              {f'<img class="img-fluid datares-gauge" src="data:image/png;base64,{gauge_b64}">' if gauge_b64 else ''}
            </div>

            <div class="row g-2 mt-1">
              <div class="col-6 col-md-3">
                <div class="mini-stat bg-success-subtle text-success-emphasis">Sí<br><b>{counts['SI']}</b></div>
              </div>
              <div class="col-6 col-md-3">
                <div class="mini-stat bg-warning-subtle text-dark">Parcial<br><b>{counts['PARCIAL']}</b></div>
              </div>
              <div class="col-6 col-md-3">
                <div class="mini-stat bg-danger-subtle text-danger-emphasis">No<br><b>{counts['NO']}</b></div>
              </div>
              <div class="col-6 col-md-3">
                <div class="mini-stat bg-secondary-subtle text-secondary-emphasis">N/A<br><b>{counts['NA']}</b></div>
              </div>
            </div>

            <div class="d-flex flex-wrap gap-2 justify-content-center mt-3">
              <a href="{url_for('madurez_datos.detalle_dominio_preguntas', run_id=run.id, dominio=dominio)}"
                 class="btn btn-outline-primary rounded-pill px-3">
                <i class="bi bi-list-check me-2"></i>Ver preguntas
              </a>

              <a href="{url_for('madurez_datos.analisis_dominio', run_id=run.id, dominio=dominio)}"
                 class="btn btn-outline-dark rounded-pill px-3">
                <i class="bi bi-cpu me-2"></i>Análisis
              </a>
            </div>
          </div>
        </div>
        """)

    content = f"""
    <div class="datares-shell">

      <div class="datares-header-card">
        <div class="datares-header-overlay">
          <div class="datares-header-text">
            <h3 class="datares-title m-0">️Resultado — Protección de Datos Personales</h3>
            <div class="datares-subtitle">
              Consecutivo: <b>{esc(run.consecutivo or '')}</b>
              · Cumplimiento general: <b>{float(run.pct_general or 0):.2f}%</b>
              · Nivel general: <b>{esc(nivel_general_nombre)}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="datares-header-actions">
        <a href="{url_for('madurez_datos.historial')}"
           class="btn datares-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al historial
        </a>

        <a href="{url_for('madurez_datos.inicio')}"
           class="btn datares-btn-soft rounded-pill px-4 fw-bold">
          <i class="bi bi-house-door-fill me-2"></i>Volver al módulo
        </a>
      </div>

      {top_html}

      <div class="row g-3">
        {''.join(tarjetas)}
      </div>

    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .datares-shell{{
        width:96%;
        max-width:1650px;
        margin:26px auto 30px auto;
      }}

      .datares-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:20px;
        padding:16px 24px;
        min-height:96px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 14px 28px rgba(15,23,42,.28);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .datares-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.18),transparent 24%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 14px
          );
        pointer-events:none;
      }}

      .datares-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        position:relative;
        z-index:1;
      }}

      .datares-header-overlay::before{{
        content:"🛡";
        width:56px;
        height:42px;
        min-width:56px;
        border-radius:16px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
        box-shadow:0 10px 20px rgba(0,0,0,.22);
        margin-right:14px;
      }}

      .datares-header-text{{
        width:100%;
      }}

      .datares-header-text::before{{
        content:"SGSI · Resultado Protección de Datos Personales";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:4px 10px;
        font-size:.66rem;
        font-weight:900;
        margin-bottom:5px;
        color:#ffffff;
      }}

      .datares-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.34rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .datares-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.79rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .datares-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 16px;
      }}

      .datares-header-actions .btn,
      .btn{{
        border-radius:12px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .datares-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #d7e0ea !important;
      }}

      .datares-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .datares-btn-soft{{
        background:rgba(255,255,255,.88);
        color:#111 !important;
        border:1px solid rgba(108,117,125,.30);
      }}

      .datares-btn-soft:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .datares-btn-success{{
        background:#198754;
        color:#ffffff !important;
        border:1px solid #198754;
      }}

      .datares-btn-success:hover{{
        background:#157347;
        color:#ffffff !important;
      }}

      .datares-card,
      .card{{
        background:rgba(255,255,255,.97) !important;
        border-radius:20px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 14px 28px rgba(15,23,42,.16) !important;
        border:1px solid rgba(219,230,244,.95) !important;
        overflow:hidden;
      }}

      .datares-card-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:1rem;
        color:#0b4a8f;
      }}

      .datares-radar-wrap{{
        min-height:420px;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:flex-start;
      }}

      .datares-radar-pct-box{{
        width:100%;
        max-width:320px;
        margin:4px auto 14px auto;
        padding:14px 15px;
        border-radius:18px;
        background:linear-gradient(135deg,#eef5ff,#ffffff);
        border:1px solid rgba(63,134,214,.22);
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }}

      .datares-radar-pct-label{{
        font-size:.72rem;
        font-weight:950;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.45px;
      }}

      .datares-radar-pct-value{{
        font-size:2.45rem;
        line-height:1;
        font-weight:950;
        color:#0f172a;
        margin:5px 0;
      }}

      .datares-radar-pct-subtitle{{
        font-size:.80rem;
        color:#475569;
        font-weight:800;
      }}

      .datares-radar-small{{
        max-width:370px;
        width:100%;
        height:auto;
      }}

      .datares-exec-box{{
        min-height:350px;
        background:linear-gradient(
          180deg,
          rgba(248,250,252,.94),
          rgba(255,255,255,.98)
        );
        border:1px solid rgba(63,134,214,.16);
        border-radius:16px;
        padding:20px;
        box-shadow:inset 0 1px 0 rgba(255,255,255,.60);
      }}

      .datares-plan-box{{
        min-height:260px;
        max-height:580px;
        overflow:auto;
      }}

      .datares-exec-text{{
        font-size:.96rem;
        line-height:1.72;
        color:#101827;
        white-space:normal;
      }}

      .datares-domain-title{{
        font-size:1rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1.2;
      }}

      .datares-gauge-wrap{{
        min-height:200px;
        padding:8px;
        display:flex;
        align-items:center;
        justify-content:center;
      }}

      .datares-gauge{{
        max-width:220px;
        max-height:160px;
      }}

      .mini-stat{{
        border-radius:14px;
        padding:11px 8px;
        text-align:center;
        font-size:.84rem;
        line-height:1.2;
        font-weight:900;
        box-shadow:0 4px 10px rgba(15,23,42,.08);
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.38rem .68rem;
        font-weight:900;
      }}

      @media (max-width:991.98px){{
        .datares-shell{{
          width:98%;
          margin:10px auto 24px auto;
        }}

        .datares-header-card{{
          min-height:88px;
        }}

        .datares-title{{
          font-size:1.18rem;
        }}

        .datares-subtitle{{
          font-size:.68rem;
        }}

        .datares-radar-wrap{{
          min-height:350px;
        }}

        .datares-radar-small{{
          max-width:280px;
        }}

        .datares-exec-box{{
          min-height:260px;
        }}

        .datares-radar-pct-value{{
          font-size:2rem;
        }}
      }}

      @media (max-width:768px){{
        .datares-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .datares-header-overlay::before{{
          margin:0;
        }}

        .datares-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .datares-title,
        .datares-subtitle{{
          text-align:center;
        }}

        .datares-header-actions .btn{{
          width:100%;
        }}

        .datares-radar-pct-box{{
          max-width:100%;
        }}

        .datares-radar-small{{
          max-width:100%;
        }}

        .datares-exec-box{{
          min-height:220px;
          padding:16px;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Resultado Protección de Datos", content=content)

# ==================================
# Generar y editar informe ejecutivo
# ==================================

@madurez_datos_bp.route("/detalle/<int:run_id>/informe-ejecutivo/generar", methods=["POST"])
@login_required
def informe_ejecutivo_generar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede generar el informe ejecutivo con IA.", "danger")
        return redirect(url_for("madurez_datos.detalle", run_id=run_id))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez protección de datos personales"):
        flash("No tiene permiso para generar el informe ejecutivo.", "danger")
        return redirect(url_for('menu'))

    run = DatosMadurezRun.query.get_or_404(run_id)

    if user.role not in ("admin", "auditor"):
        if run.user_id and run.user_id != user.id:
            flash("No tiene permiso para generar IA sobre esta revisión.", "danger")
            return redirect(url_for("madurez_datos.historial"))

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    if not resumen:
        flash("⚠️ No hay resultados consolidados para generar el informe ejecutivo.", "warning")
        return redirect(url_for("madurez_datos.detalle", run_id=run.id))

    prompt = _gdpr_prompt_informe_ejecutivo(run, resumen)

    try:
        raw = _ai_text(prompt, max_tokens=1400)
    except Exception as e:
        flash(f"❌ Error llamando IA para el informe ejecutivo: {e}", "danger")
        return redirect(url_for("madurez_datos.detalle", run_id=run.id))

    informe_ai = ""
    try:
        obj = _gdpr_extraer_json_objeto(raw)
        if isinstance(obj, dict):
            informe_ai = (obj.get("informe_ejecutivo") or "").strip()
    except Exception:
        informe_ai = ""

    if not informe_ai:
        informe_ai = (raw or "").strip()

    if not informe_ai:
        flash("⚠️ La IA no devolvió contenido para el informe ejecutivo.", "warning")
        return redirect(url_for("madurez_datos.detalle", run_id=run.id))

    # IMPORTANTE: sincronizar SIEMPRE ambos campos
    run.informe_ejecutivo_ai = informe_ai
    run.informe_ejecutivo_editado = informe_ai

    db.session.commit()

    flash("✅ Informe ejecutivo generado con IA.", "success")
    return redirect(url_for("madurez_datos.detalle", run_id=run.id))

@madurez_datos_bp.route("/detalle/<int:run_id>/informe-ejecutivo/editar", methods=["GET", "POST"])
@login_required
def informe_ejecutivo_editar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede editar el informe ejecutivo.", "danger")
        return redirect(url_for("madurez_datos.detalle", run_id=run_id))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez protección de datos personales"):
        flash("No tiene permiso para editar el informe ejecutivo.", "danger")
        return redirect(url_for('menu'))

    run = DatosMadurezRun.query.get_or_404(run_id)

    texto_actual = (run.informe_ejecutivo_editado or run.informe_ejecutivo_ai or "").strip()

    if request.method == "POST":
        texto = (request.form.get("informe_ejecutivo") or "").strip()
        run.informe_ejecutivo_editado = texto
        db.session.commit()
        flash("✅ Informe ejecutivo actualizado.", "success")
        return redirect(url_for("madurez_datos.detalle", run_id=run.id))

    content = f"""
    <div class="datstd-shell">

      <div class="datstd-header-card">
        <div class="datstd-header-overlay">
          <div class="datstd-header-text">
            <h3 class="datstd-title m-0">Editar Informe Ejecutivo — Protección de Datos Personales</h3>
            <div class="datstd-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="datstd-header-actions">
        <a href="{url_for('madurez_datos.detalle', run_id=run.id)}"
           class="btn datstd-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al detalle
        </a>
      </div>

      <div class="datstd-card p-4">
        <form method="POST">
          <div class="datstd-section-title">Informe ejecutivo editable</div>

          <div class="text-muted small mb-3">
            Ajusta el contenido del informe ejecutivo y guarda los cambios.
          </div>

          <textarea name="informe_ejecutivo"
                    class="form-control datstd-textarea"
                    rows="20"
                    placeholder="Escribe o ajusta aquí el informe ejecutivo...">{escape(texto_actual)}</textarea>

          <div class="d-flex justify-content-center mt-4">
            <button type="submit" class="btn btn-primary rounded-pill px-5 fw-bold">
              <i class="bi bi-save2 me-2"></i>Guardar cambios
            </button>
          </div>
        </form>
      </div>
    </div>

        <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .datstd-shell{{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }}

      .datstd-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .datstd-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .datstd-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .datstd-header-overlay::before{{
        content:"📄";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .datstd-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .datstd-header-text::before{{
        content:"SGSI · Estándar Datos Personales";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .datstd-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }}

      .datstd-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .datstd-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .datstd-header-actions .btn,
      .datstd-btn-main,
      .btn{{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .datstd-btn-main{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .datstd-btn-main:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }}

      .datstd-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .datstd-card.p-4{{
        padding:1.5rem !important;
      }}

      .datstd-section-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
      }}

      .datstd-section-title{{
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }}

      .datstd-textarea{{
        min-height:420px;
        border-radius:14px;
        border:1px solid #d9e3f0;
        resize:vertical;
        background:#f8fafc;
        font-size:.86rem;
        padding:14px 16px;
        box-shadow:none !important;
      }}

      .datstd-textarea:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .form-label{{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:6px 10px;
        border-radius:10px;
        display:inline-block;
        margin-bottom:6px;
      }}

      .form-control,
      .form-select{{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      .form-control:focus,
      .form-select:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:992px){{
        .datstd-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .datstd-header-card{{
          min-height:88px;
        }}

        .datstd-title{{
          font-size:1.20rem;
        }}

        .datstd-subtitle{{
          font-size:.68rem;
        }}

        .datstd-card.p-4{{
          padding:1rem !important;
        }}

        .datstd-textarea{{
          min-height:320px;
        }}
      }}

      @media (max-width:768px){{
        .datstd-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .datstd-header-overlay::before{{
          margin:0;
        }}

        .datstd-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .datstd-title,
        .datstd-subtitle{{
          text-align:center;
        }}

        .datstd-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Editar Informe Ejecutivo Datos Personales", content=content)


# =========================
# Exportación PDF — Protección de Datos Personales
# =========================

@madurez_datos_bp.route("/exportar_pdf/<int:run_id>")
@login_required
def exportar_pdf(run_id):
    user = User.query.get(session.get("user_id"))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez protección de datos personales"):
        flash("No tiene permiso para exportar el reporte PDF de protección de datos personales.", "danger")
        return redirect(url_for('menu'))

    run = DatosMadurezRun.query.get_or_404(run_id)

    informe_exec = (run.informe_ejecutivo_editado or run.informe_ejecutivo_ai or "").strip()
    if informe_exec:
        story.append(Paragraph("Informe Ejecutivo", styles["Heading2"]))
        story.append(Spacer(1, 4))
        for par in informe_exec.split("\n"):
            par = par.strip()
            if par:
                story.append(Paragraph(xml_escape(par), styles["Normal"]))
                story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    logo_path = get_company_logo_path(run.consecutivo if hasattr(run, "consecutivo") else "")
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        "DatosTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=colors.HexColor("#0b1b2b"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )

    small_style = ParagraphStyle(
        "DatosSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        spaceAfter=4
    )

    if logo_path and os.path.exists(logo_path):
        try:
            story.append(RLImage(logo_path, width=4*cm, height=2*cm))
            story.append(Spacer(1, 8))
        except Exception:
            pass

    story.append(Paragraph("Reporte de Nivel de Madurez — Protección de Datos Personales", title_style))
    story.append(Paragraph(f"Consecutivo: {xml_escape(run.consecutivo or '')}", styles["Normal"]))
    story.append(Paragraph(
        f"Fecha: {xml_escape(run.created_at.strftime('%Y-%m-%d %H:%M') if run.created_at else '')}",
        styles["Normal"]
    ))
    story.append(Paragraph(f"Promedio general: {float(run.pct_general or 0):.2f}%", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Resumen por dominio
    table_data = [["Dominio", "Nivel", "% Cumplimiento", "Brecha"]]

    for dominio, data in resumen.items():
        try:
            pct = float(data.get("pct", 0) or 0)
        except Exception:
            pct = 0.0

        niv = gdpr_nivel_visual_por_pct(pct)
        brecha = max(0.0, 100.0 - pct)

        table_data.append([
            dominio,
            niv.get("nivel", ""),
            f"{pct:.2f}%",
            f"{brecha:.2f}%"
        ])

    tbl = Table(table_data, colWidths=[6.0*cm, 5.0*cm, 3.0*cm, 3.0*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b1b2b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 12))

    # Radar
    radar_png = generar_radar_datos_png_bytes(resumen)
    if radar_png:
        story.append(Paragraph("Radar de dominios", styles["Heading2"]))
        story.append(Spacer(1, 6))
        story.append(RLImage(BytesIO(radar_png), width=15*cm, height=10*cm))
        story.append(Spacer(1, 12))

    # Velocímetros por dominio
    story.append(Paragraph("Tablero por dominio", styles["Heading2"]))
    story.append(Spacer(1, 8))

    for dominio, data in resumen.items():
        try:
            pct = float(data.get("pct", 0) or 0)
        except Exception:
            pct = 0.0

        niv = gdpr_nivel_visual_por_pct(pct)
        png = generar_gdpr_velocimetro_png_bytes(
            dominio,
            pct,
            niv["nivel"],
            niv["color"]
        )

        story.append(Paragraph(xml_escape(dominio), styles["Heading3"]))

        if png:
            story.append(RLImage(BytesIO(png), width=8.5*cm, height=5.0*cm))

        story.append(Paragraph(
            f"Cumplimiento: {pct:.2f}% | Nivel: {xml_escape(niv['nivel'])} | Brecha: {max(0.0, 100.0 - pct):.2f}%",
            styles["Normal"]
        ))
        story.append(Spacer(1, 10))

    # Detalle de preguntas por dominio
    for dominio, data in resumen.items():
        items = data.get("items", []) or []
        if not items:
            continue

        story.append(PageBreak())
        story.append(Paragraph(f"Detalle — {xml_escape(dominio)}", styles["Heading2"]))
        story.append(Spacer(1, 8))

        detalle_table = [["Pregunta", "Estado", "Comentario / evidencia"]]

        for it in items:
            codigo = (it.get("codigo") or "").strip()
            titulo = (it.get("titulo") or "").strip()
            pregunta = (it.get("pregunta") or "").strip()
            estado = (it.get("estado") or "").strip().upper()
            comentario = (it.get("comentario") or "").strip() or "—"

            encabezado = " ".join([x for x in [codigo, titulo] if x]).strip()
            pregunta_full = f"{encabezado}\n{pregunta}" if encabezado else pregunta

            detalle_table.append([
                Paragraph(xml_escape(pregunta_full).replace("\n", "<br/>"), small_style),
                Paragraph(xml_escape(estado or "—"), small_style),
                Paragraph(xml_escape(comentario), small_style),
            ])

        detalle_tbl = Table(detalle_table, colWidths=[9.5*cm, 2.5*cm, 6.0*cm])
        detalle_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(detalle_tbl)
        story.append(Spacer(1, 10))

    doc.build(story)
    buf.seek(0)

    return send_file(
        buf,
        as_attachment=True,
        download_name=f"Reporte_Madurez_Proteccion_Datos_{run.id}.pdf",
        mimetype="application/pdf"
    )


# ==========================================================================================================================================
#                                           Fin Módulo de Madurez Protección de Datos Personales
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                   Módulo de Madurez PCI-DSS
# ==========================================================================================================================================


pci_madurez_bp = Blueprint("madurez_pci", __name__, url_prefix="/madurez_pci")

PCI_INSTRUMENTO_TEMPLATE_XLSX = os.path.join(
    BASE_DIR, "static", "templates", "PCI requerimientos.xlsx"
)

PCI_TRADUCIR_EN_IMPORTACION = False  # ✅ NO traducir, usar texto tal cual venga en el Excel

PCI_STATUS_SCORE = {
    "SI": 100,
    "PARCIAL": 50,
    "NO": 0,
    "NA": None,
}

PCI_BLOCK_ORDER = [
    "REQ-1", "REQ-2", "REQ-3", "REQ-4", "REQ-5", "REQ-6",
    "REQ-7", "REQ-8", "REQ-9", "REQ-10", "REQ-11", "REQ-12",
    "A1", "A2"
]

PCI_BLOCK_TITLES = {
    "REQ-1": "Requerimiento 1 — Instalar y mantener controles de seguridad de red",
    "REQ-2": "Requerimiento 2 — Aplicar configuraciones seguras a todos los componentes del sistema",
    "REQ-3": "Requerimiento 3 — Proteger los datos de cuenta almacenados",
    "REQ-4": "Requerimiento 4 — Proteger los datos de titulares de tarjeta mediante criptografía robusta durante la transmisión",
    "REQ-5": "Requerimiento 5 — Proteger todos los sistemas y redes contra software malicioso",
    "REQ-6": "Requerimiento 6 — Desarrollar y mantener sistemas y software seguros",
    "REQ-7": "Requerimiento 7 — Restringir el acceso a datos de cuenta según la necesidad de conocer",
    "REQ-8": "Requerimiento 8 — Identificar usuarios y autenticar el acceso a componentes del sistema",
    "REQ-9": "Requerimiento 9 — Restringir el acceso físico a los datos de titulares de tarjeta",
    "REQ-10": "Requerimiento 10 — Registrar y monitorear todo acceso a componentes del sistema y datos de titulares de tarjeta",
    "REQ-11": "Requerimiento 11 — Probar regularmente la seguridad de sistemas y redes",
    "REQ-12": "Requerimiento 12 — Mantener una política de seguridad de la información",
    "A1": "Apéndice A1 — Requisitos adicionales para proveedores de servicios multi-tenant",
    "A2": "Apéndice A2 — Requisitos adicionales para entidades que usan SSL/TLS temprano"
}

def pci_block_title(code: str) -> str:
    return PCI_BLOCK_TITLES.get((code or "").strip().upper(), code or "")

class PciMadurezParametro(db.Model):
    __tablename__ = "pci_madurez_parametros"

    id = db.Column(db.Integer, primary_key=True)
    nivel = db.Column(db.String(80), nullable=False)
    rango_desde = db.Column(db.Float, nullable=False)
    rango_hasta = db.Column(db.Float, nullable=False)
    color = db.Column(db.String(20), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    orden = db.Column(db.Integer, default=0)

class PciMadurezPregunta(db.Model):
    __tablename__ = "pci_madurez_preguntas"

    id = db.Column(db.Integer, primary_key=True)
    bloque_codigo = db.Column(db.String(20), index=True, nullable=True)   # REQ-1 ... REQ-12, A1, A2
    bloque_nombre = db.Column(db.String(255), nullable=True)              # título del bloque
    seccion_codigo = db.Column(db.String(30), index=True, nullable=True)  # 1.1 / 1.2 / A1.1 / A2.1 ...
    seccion_nombre = db.Column(db.Text, nullable=True)                    # línea descriptiva de la sección
    pregunta_codigo = db.Column(db.String(30), index=True, nullable=True) # 1.1.1 / A1.1.1 / etc
    pregunta = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(5), nullable=False, default="q")           # h / q
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)

class PciMadurezRun(db.Model):
    __tablename__ = "pci_madurez_runs"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    estado = db.Column(db.String(20), default="BORRADOR")  # BORRADOR / FINALIZADO
    progreso_pct = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PciMadurezRespuesta(db.Model):
    __tablename__ = "pci_madurez_respuestas"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("pci_madurez_runs.id", ondelete="CASCADE"), nullable=False)
    pregunta_id = db.Column(db.Integer, db.ForeignKey("pci_madurez_preguntas.id", ondelete="CASCADE"), nullable=False)
    estado = db.Column(db.String(20), nullable=False)  # SI / PARCIAL / NO / NA
    comentario = db.Column(db.Text, nullable=True)

class PciAnalysisRun(db.Model):
    __tablename__ = "pci_analysis_runs"

    id = db.Column(db.Integer, primary_key=True)
    pci_run_id = db.Column(db.Integer, db.ForeignKey("pci_madurez_runs.id", ondelete="CASCADE"), nullable=False)
    fecha_calculo = db.Column(db.DateTime, default=datetime.utcnow)
    company_name = db.Column(db.String(255), nullable=False)

    nivel_promedio_general = db.Column(db.Float, default=0)
    resultados_json = db.Column(db.Text)
    preguntas_json = db.Column(db.Text)
    velocimetros_json = db.Column(db.Text)

    # NUEVOS
    informe_ejecutivo_ai = db.Column(db.Text, nullable=True)
    informe_ejecutivo_editado = db.Column(db.Text, nullable=True)
    plan_trabajo_ai = db.Column(db.Text, nullable=True)
    plan_trabajo_editado = db.Column(db.Text, nullable=True)

# =========================
# Parametros
# =========================

def seed_pci_parametros():
    if PciMadurezParametro.query.first():
        return

    params = [
        {
            "nivel": "Inicial",
            "rango_desde": 0,
            "rango_hasta": 20.99,
            "color": "#dc3545",
            "descripcion": "No existe implementación formal o es mínima.",
            "orden": 1
        },
        {
            "nivel": "Repetible",
            "rango_desde": 21,
            "rango_hasta": 40.99,
            "color": "#fd7e14",
            "descripcion": "Existen prácticas parciales y repetibles.",
            "orden": 2
        },
        {
            "nivel": "Definido",
            "rango_desde": 41,
            "rango_hasta": 60.99,
            "color": "#ffc107",
            "descripcion": "El proceso está definido y documentado.",
            "orden": 3
        },
        {
            "nivel": "Gestionado",
            "rango_desde": 61,
            "rango_hasta": 80.99,
            "color": "#0d6efd",
            "descripcion": "El proceso se mide, gestiona y controla.",
            "orden": 4
        },
        {
            "nivel": "Óptimo",
            "rango_desde": 81,
            "rango_hasta": 100,
            "color": "#198754",
            "descripcion": "El proceso es eficaz, sostenido y mejorado continuamente.",
            "orden": 5
        },
    ]

    for p in params:
        db.session.add(PciMadurezParametro(**p))
    db.session.commit()

def pci_resolver_nivel(pct: float):
    pct = max(0.0, min(100.0, float(pct or 0)))
    rows = PciMadurezParametro.query.order_by(PciMadurezParametro.orden.asc()).all()
    for r in rows:
        if float(r.rango_desde) <= pct <= float(r.rango_hasta):
            return {
                "nivel": r.nivel,
                "color": r.color or "#6c757d",
                "descripcion": r.descripcion or ""
            }
    return {
        "nivel": "Sin nivel",
        "color": "#6c757d",
        "descripcion": ""
    }

# =========================
# Helpers de importación PCI
# =========================

def pci_safe_str(x):
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()

def pci_estado_normalizado(v):
    estado = pci_safe_str(v).upper()
    estado = estado.replace(" ", "")
    estado = estado.replace(".", "")
    estado = estado.replace("-", "")
    estado = estado.replace("/", "")

    if estado in ("SI", "SÍ", "YES"):
        return "SI"

    if estado in ("PARCIAL", "PARCIALMENTE", "PARTIAL"):
        return "PARCIAL"

    if estado in ("NO", "N"):
        return "NO"

    if estado in ("NA", "N/A", "NOAPLICA", "NOAPLICABLE", "NOTAPPLICABLE"):
        return "NA"

    return ""

def _pci_norm(s: str) -> str:
    s = pci_safe_str(s)
    s = "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )
    s = s.upper()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def pci_normalizar_texto_excel(texto: str) -> str:
    t = pci_safe_str(texto)
    if not t:
        return ""

    t = t.replace("\ufeff", " ").replace("\xa0", " ")
    t = t.replace("•\t", "• ").replace("•", "• ")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t).strip()

    # Arregla espacios malos en prefijos tipo A1. 1 / A2. 1
    t = re.sub(r"^(A[12])\s*\.\s*(\d+)", r"\1.\2", t, flags=re.IGNORECASE)

    # Arregla 8. 1 / 3.3. 1 / 12.4.2. 1
    t = re.sub(r"^(\d+)\s*\.\s*(\d+)", r"\1.\2", t)
    t = re.sub(r"^(\d+\.\d+)\s*\.\s*(\d+)", r"\1.\2", t)
    t = re.sub(r"^(\d+\.\d+\.\d+)\s*\.\s*(\d+)", r"\1.\2", t)
    t = re.sub(r"^(A[12]\.\d+)\s*\.\s*(\d+)", r"\1.\2", t, flags=re.IGNORECASE)

    # Si el código quedó pegado al texto
    t = re.sub(
        r"^((?:A[12]\.\d+(?:\.\d+)*)|\d+(?:\.\d+){1,3})(?=[A-Za-zÁÉÍÓÚáéíóú])",
        r"\1 ",
        t,
        flags=re.IGNORECASE
    )

    return t.strip()


def pci_detectar_bloque(texto: str):
    """
    Detecta bloques usando texto normalizado, para no fallar con acentos raros.
    """
    t = pci_normalizar_texto_excel(texto)
    n = _pci_norm(t)

    m = re.match(r"^(REQUERIMIENTO|REQUISITO)\s+(\d+)\b", n)
    if m:
        num = int(m.group(2))
        return f"REQ-{num}", t

    if n.startswith("APENDICE A1"):
        return "A1", t

    if n.startswith("APENDICE A2"):
        return "A2", t

    return None, None


def pci_extraer_codigo_inicial(texto: str):
    t = pci_normalizar_texto_excel(texto)

    m = re.match(r"^(A[12]\.\d+(?:\.\d+)*)\b", t, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper()

    m = re.match(r"^(\d+(?:\.\d+){1,3})\b", t)
    if m:
        return m.group(1)

    return None


def pci_detectar_seccion(texto: str):
    t = pci_normalizar_texto_excel(texto)
    codigo = pci_extraer_codigo_inicial(t)
    if not codigo:
        return None, None

    if re.match(r"^\d+\.\d+$", codigo):
        return codigo, t

    if re.match(r"^A[12]\.\d+$", codigo, flags=re.IGNORECASE):
        return codigo.upper(), t

    return None, None


def pci_detectar_pregunta_codigo(texto: str):
    t = pci_normalizar_texto_excel(texto)
    codigo = pci_extraer_codigo_inicial(t)
    if not codigo:
        return None

    if re.match(r"^\d+\.\d+\.\d+(?:\.\d+)?$", codigo):
        return codigo

    if re.match(r"^A[12]\.\d+\.\d+$", codigo, flags=re.IGNORECASE):
        return codigo.upper()

    return None


def pci_resumen_instrumento():
    total_q = PciMadurezPregunta.query.filter_by(tipo="q").count()
    total_h = PciMadurezPregunta.query.filter_by(tipo="h").count()

    por_bloque = (
        db.session.query(
            PciMadurezPregunta.bloque_codigo,
            func.count(PciMadurezPregunta.id)
        )
        .filter(PciMadurezPregunta.tipo == "q")
        .group_by(PciMadurezPregunta.bloque_codigo)
        .all()
    )

    return {
        "total_preguntas": total_q,
        "total_headers": total_h,
        "por_bloque": {k: v for k, v in por_bloque}
    }


def cargar_respuestas_pci(run_id):
    out = {}

    if not run_id:
        return out

    rows = PciMadurezRespuesta.query.filter_by(run_id=run_id).all()

    for r in rows:
        out[r.pregunta_id] = {
            "estado": pci_estado_normalizado(r.estado),
            "comentario": (r.comentario or "").strip()
        }

    return out


def calcular_progreso_pci(preguntas, form_data=None, respuestas_db=None):
    total = len(preguntas)
    respondidas = 0

    for q in preguntas:
        estado = ""

        if form_data is not None:
            estado = pci_estado_normalizado(form_data.get(f"st_{q.id}"))
        elif respuestas_db is not None:
            estado = pci_estado_normalizado(respuestas_db.get(q.id, {}).get("estado"))

        if estado in ("SI", "PARCIAL", "NO", "NA"):
            respondidas += 1

    pct = int(round((respondidas / total) * 100)) if total > 0 else 0
    return respondidas, total, pct

def _pci_prompt_plan_trabajo(run: "PciAnalysisRun", resultados: dict) -> str:
    partes = []

    for bloque in PCI_BLOCK_ORDER:
        item = (resultados or {}).get(bloque)
        if not item:
            continue

        pct = float(item.get("pct", 0) or 0)
        nombre = item.get("nombre") or pci_block_title(bloque)
        counts = item.get("counts", {}) or {}

        partes.append(
            f"- {bloque} - {nombre}: {pct:.2f}% | "
            f"SI={counts.get('SI',0)} PARCIAL={counts.get('PARCIAL',0)} NO={counts.get('NO',0)} NA={counts.get('NA',0)}"
        )

    detalle = "\n".join(partes)

    return f"""
Eres un consultor senior en cumplimiento PCI-DSS. Debes construir un PLAN DE TRABAJO GENERAL para cerrar brechas de cumplimiento.

CONTEXTO
- Revisión: {run.company_name}
- Cumplimiento general: {float(run.nivel_promedio_general or 0):.2f}%

RESULTADOS RESUMIDOS
{detalle}

INSTRUCCIONES
1. Devuelve solamente JSON válido.
2. Debes devolver exactamente esta estructura:
{{
  "plan_trabajo": [
    {{
      "frente": "string",
      "actividad": "string",
      "prioridad": "Alta|Media|Baja",
      "responsable_sugerido": "string",
      "plazo": "string",
      "entregable": "string"
    }}
  ]
}}

REGLAS
- Genera entre 8 y 15 actividades.
- Prioriza primero requerimientos con menor cumplimiento.
- Usa lenguaje ejecutivo y accionable.
- No inventes herramientas específicas.
""".strip()

# ==========================================
# INFORME EJECUTIVO AI — PCI-DSS
# ==========================================

def _pci_prompt_informe_ejecutivo(ar: "PciAnalysisRun", resultados: dict) -> str:
    partes = []

    for code in PCI_BLOCK_ORDER:
        item = (resultados or {}).get(code)
        if not item:
            partes.append(f"- {pci_block_title(code)}: sin información.")
            continue

        pct = float(item.get("pct", 0) or 0)
        total = int(item.get("total", 0) or 0)
        madurez = (item.get("madurez") or "").strip()
        brecha = float(item.get("brecha_pct", 0) or 0)
        counts = item.get("counts", {}) or {}

        partes.append(
            f"- {pci_block_title(code)}:\n"
            f"  * Cumplimiento: {pct:.2f}%\n"
            f"  * Madurez: {madurez}\n"
            f"  * Brecha: {brecha:.2f}%\n"
            f"  * Total ítems: {total}\n"
            f"  * SI: {counts.get('SI',0)} | PARCIAL: {counts.get('PARCIAL',0)} | NO: {counts.get('NO',0)} | NA: {counts.get('NA',0)}"
        )

    detalle = "\n".join(partes)

    return f"""
Eres un consultor senior en PCI-DSS, gobierno de seguridad y cumplimiento. Debes redactar un INFORME EJECUTIVO para alta dirección, claro, breve, profesional y accionable, basado en una evaluación de madurez PCI-DSS.

DATOS GENERALES
- Compañía / consecutivo: {ar.company_name}
- Cumplimiento general: {float(ar.nivel_promedio_general or 0):.2f}%

RESULTADOS POR REQUERIMIENTO / APÉNDICE
{detalle}

INSTRUCCIONES
1. Devuelve solamente JSON válido.
2. Debes devolver exactamente esta estructura:
{{
  "informe_ejecutivo": "texto"
}}

REGLAS DEL TEXTO:
- Escribe en español.
- Extensión aproximada: 4 a 7 párrafos cortos.
- Incluye:
  a) resumen general del nivel de madurez,
  b) fortalezas principales,
  c) brechas principales,
  d) requerimientos/apéndices más débiles,
  e) riesgos ejecutivos si no se actúa,
  f) prioridades recomendadas para los próximos 90 días.
- No inventes herramientas específicas.
- Usa un tono ejecutivo, no técnico en exceso.
- No uses markdown ni viñetas; redacta como informe.
""".strip()


def _extraer_json_objeto(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        return {}

    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except Exception:
        pass

    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end+1])
    except Exception:
        pass

    return {}

# =========================
# AI helper PCI (OpenRouter / Ollama)
# =========================

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

def _ai_text(prompt: str, max_tokens: int = 900) -> str:
    """
    Helper central de IA para PCI-DSS.
    Soporta OpenRouter y Ollama.
    """
    provider = (get_ai_provider() or "openrouter").strip().lower()


    # =====================================================
    # OLLAMA
    # =====================================================
    if provider == "ollama":
        base_url = (get_ollama_base_url() or "http://localhost:11434").strip().rstrip("/")
        model = (get_ollama_model() or "llama3.1").strip()

        if not base_url:
            raise RuntimeError("No hay OLLAMA_BASE_URL configurada en Administración.")
        if not model:
            raise RuntimeError("No hay OLLAMA_MODEL configurado en Administración.")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        }


        resp = requests.post(
            f"{base_url}/api/generate",
            json=payload,
            timeout=300
        )
        resp.raise_for_status()

        data = resp.json() or {}

        texto = (data.get("response") or "").strip()

        # Fallback adicional
        if not texto:
            texto = (data.get("message") or "").strip()

        if not texto:
            raise RuntimeError(
                "Ollama respondió sin contenido. "
                f"Respuesta recibida: {str(data)[:500]}"
            )

        return texto

    # =====================================================
    # OPENROUTER
    # =====================================================
    api_key = get_openrouter_api_key()
    if not api_key:
        raise RuntimeError("No hay OpenRouter API Key configurada. Ve a Administración → OpenRouter API Key.")

    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key
    )

    max_tokens_safe = max(700, min(int(max_tokens or 1200), 2200))

    resp = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        temperature=0.2,
        max_tokens=max_tokens_safe,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un consultor experto en PCI-DSS. "
                    "Debes responder únicamente con JSON válido, sin markdown, "
                    "sin ```json, sin HTML, sin <br>, sin <b>, y sin texto adicional."
                )
            },
            {"role": "user", "content": prompt},
        ],
    )

    texto = (resp.choices[0].message.content or "").strip()
    if not texto:
        raise RuntimeError("OpenRouter respondió sin contenido.")
    return texto

# =========================
# Importación instrumento PCI-DSS
# =========================

@pci_madurez_bp.route("/admin/importar_instrumento", methods=["POST"])
@login_required
def importar_instrumento_pci():
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El rol Auditor no puede importar instrumentos.", "danger")
        return redirect(url_for("madurez_pci.parametros"))

    force = (request.args.get("force") == "1") or (request.form.get("force") == "1")

    try:
        if force:
            PciAnalysisRun.query.delete()
            PciMadurezRespuesta.query.delete()
            PciMadurezRun.query.delete()
            PciMadurezPregunta.query.delete()
            db.session.commit()
            flash("🧹 Instrumento PCI-DSS anterior borrado. Reimportando…", "info")

        if PciMadurezPregunta.query.first() and not force:
            flash("El instrumento PCI-DSS ya está cargado en la base de datos.", "warning")
            return redirect(url_for("madurez_pci.parametros"))

        xlsx_path = PCI_INSTRUMENTO_TEMPLATE_XLSX
        if not os.path.exists(xlsx_path):
            alt = os.path.join(BASE_DIR, "static", "templates", "PCI requerimientos .xlsx")
            if os.path.exists(alt):
                xlsx_path = alt

        if not os.path.exists(xlsx_path):
            flash(f"No se encontró el archivo PCI para importar: {xlsx_path}", "danger")
            return redirect(url_for("madurez_pci.parametros"))

        df = pd.read_excel(xlsx_path, sheet_name=0, header=0)

        col_pregunta = None
        for c in df.columns:
            if _pci_norm(c) == "PREGUNTA":
                col_pregunta = c
                break

        if not col_pregunta:
            flash("El Excel PCI no contiene la columna 'Pregunta'.", "danger")
            return redirect(url_for("madurez_pci.parametros"))

        orden = 1
        bloque_codigo = None
        bloque_nombre = None
        seccion_codigo = None
        seccion_nombre = None

        creadas_q = 0
        creadas_h = 0
        ignoradas = 0

        for _, row in df.iterrows():
            txt = pci_normalizar_texto_excel(row.get(col_pregunta))

            if not txt:
                continue

            if _pci_norm(txt) == "PREGUNTA":
                continue

            # Detectar bloque
            bc, bn = pci_detectar_bloque(txt)
            if bc:
                bloque_codigo = bc
                bloque_nombre = bn
                seccion_codigo = None
                seccion_nombre = None

                db.session.add(PciMadurezPregunta(
                    bloque_codigo=bloque_codigo,
                    bloque_nombre=bloque_nombre,
                    seccion_codigo=None,
                    seccion_nombre=None,
                    pregunta_codigo=None,
                    pregunta=bn,
                    tipo="h",
                    orden=orden,
                    activo=True
                ))
                orden += 1
                creadas_h += 1
                continue

            if not bloque_codigo:
                ignoradas += 1
                continue

            # Detectar sección / pregunta
            sc, sn = pci_detectar_seccion(txt)
            pq = pci_detectar_pregunta_codigo(txt)

            if sc and not pq:
                seccion_codigo = sc
                seccion_nombre = sn

                db.session.add(PciMadurezPregunta(
                    bloque_codigo=bloque_codigo,
                    bloque_nombre=bloque_nombre,
                    seccion_codigo=seccion_codigo,
                    seccion_nombre=seccion_nombre,
                    pregunta_codigo=None,
                    pregunta=sn,
                    tipo="h",
                    orden=orden,
                    activo=True
                ))
                orden += 1
                creadas_h += 1
                continue

            if pq:
                db.session.add(PciMadurezPregunta(
                    bloque_codigo=bloque_codigo,
                    bloque_nombre=bloque_nombre,
                    seccion_codigo=seccion_codigo,
                    seccion_nombre=seccion_nombre,
                    pregunta_codigo=pq,
                    pregunta=txt,
                    tipo="q",
                    orden=orden,
                    activo=True
                ))
                orden += 1
                creadas_q += 1
                continue

            ignoradas += 1

        db.session.commit()
        seed_pci_parametros()

        resumen = pci_resumen_instrumento()

        flash(
            f"✅ Instrumento PCI-DSS importado correctamente. "
            f"Cabeceras: {creadas_h} | Preguntas: {creadas_q} | Ignoradas: {ignoradas}",
            "success"
        )
        flash(
            f"📌 Resumen por bloque: {resumen['por_bloque']}",
            "info"
        )

        return redirect(url_for("madurez_pci.parametros"))

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        flash(f"❌ Error importando instrumento PCI-DSS: {e}", "danger")
        return redirect(url_for("madurez_pci.parametros"))

def obtener_borrador_pci(user_id):
    if not user_id:
        return None

    return (
        PciMadurezRun.query
        .filter(
            PciMadurezRun.user_id == user_id,
            PciMadurezRun.estado == "BORRADOR"
        )
        .order_by(PciMadurezRun.updated_at.desc(), PciMadurezRun.id.desc())
        .first()
    )

# =========================
# Informe ejecutivo
# =========================

@pci_madurez_bp.route("/resultado/<int:run_id>/informe-ejecutivo/generar", methods=["POST"])
@login_required
def informe_ejecutivo_generar_pci(run_id: int):
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede generar el informe ejecutivo con IA.", "danger")
        return redirect(url_for("madurez_pci.resultado", run_id=run_id))

    if user.role != "admin" and not verificar_permiso(user, "Nivel de madurez PCI-DSS"):
        flash("No tiene permiso para generar el informe ejecutivo PCI-DSS.", "danger")
        return redirect(url_for("menu"))

    run = PciAnalysisRun.query.get_or_404(run_id)

    try:
        resultados = json.loads(run.resultados_json or "{}")
    except Exception:
        resultados = {}

    if not resultados:
        flash("⚠️ No hay resultados consolidados para generar el informe ejecutivo.", "warning")
        return redirect(url_for("madurez_pci.resultado", run_id=run.id))

    prompt = _pci_prompt_informe_ejecutivo(run, resultados)

    try:
        raw = _ai_text(prompt, max_tokens=500)
    except Exception as e:
        flash(f"❌ Error llamando IA para el informe ejecutivo: {e}", "danger")
        return redirect(url_for("madurez_pci.resultado", run_id=run.id))

    if not (raw or "").strip():
        flash("⚠️ Ollama no devolvió contenido para el informe ejecutivo.", "warning")
        return redirect(url_for("madurez_pci.resultado", run_id=run.id))

    informe_ai = raw.strip()


    obj = _extraer_json_objeto(raw)
    if isinstance(obj, dict):
        informe_extraido = (obj.get("informe_ejecutivo") or "").strip()
        if informe_extraido:
            informe_ai = informe_extraido



    if not informe_ai.strip():
        flash("⚠️ La respuesta de IA no trajo un informe ejecutivo válido.", "warning")
        return redirect(url_for("madurez_pci.resultado", run_id=run.id))

    # Normalizar antes de guardar
    informe_ai = pci_normalizar_texto_rico_guardado(informe_ai)

    run.informe_ejecutivo_ai = informe_ai

    # IMPORTANTE:
    # para que se vea inmediatamente en pantalla, sincronizamos también el editado
    run.informe_ejecutivo_editado = informe_ai

    db.session.add(run)
    db.session.flush()
    db.session.commit()
    db.session.refresh(run)


    flash("✅ Informe ejecutivo PCI-DSS generado con IA.", "success")
    return redirect(url_for("madurez_pci.resultado", run_id=run.id))

# =========================
# Analisis y Calculos
# =========================

def build_pci_df_from_db(run_id: int) -> "pd.DataFrame":
    q = (
        db.session.query(PciMadurezRespuesta, PciMadurezPregunta)
        .join(PciMadurezPregunta, PciMadurezPregunta.id == PciMadurezRespuesta.pregunta_id)
        .filter(PciMadurezRespuesta.run_id == run_id)
        .filter(PciMadurezPregunta.tipo == "q")
        .order_by(PciMadurezPregunta.orden.asc())
    )

    rows = []

    for r, p in q.all():
        estado = pci_estado_normalizado(r.estado)

        if estado not in ("SI", "PARCIAL", "NO", "NA"):
            continue

        rows.append({
            "pregunta_id": p.id,
            "bloque_codigo": p.bloque_codigo,
            "bloque_nombre": p.bloque_nombre,
            "seccion_codigo": p.seccion_codigo,
            "seccion_nombre": p.seccion_nombre,
            "pregunta_codigo": p.pregunta_codigo,
            "pregunta": p.pregunta,
            "estado": estado,
            "comentario": (r.comentario or "").strip(),
        })

    return pd.DataFrame(rows)

def pci_pct_from_estados(estados: list[str]) -> float:
    vals = []

    for e in estados:
        estado = pci_estado_normalizado(e)

        if estado == "NA":
            continue

        v = PCI_STATUS_SCORE.get(estado)

        if v is not None:
            vals.append(float(v))

    if not vals:
        return 0.0

    return round(sum(vals) / len(vals), 2)

def run_analysis_from_pci_run(pci_run_id: int):
    run = PciMadurezRun.query.get_or_404(pci_run_id)
    df = build_pci_df_from_db(run.id)

    resultados = {}
    preguntas_detalle = []

    if df.empty:
        ar = (
            PciAnalysisRun.query
            .filter_by(pci_run_id=run.id)
            .order_by(PciAnalysisRun.id.desc())
            .first()
        )

        if not ar:
            ar = PciAnalysisRun(
                pci_run_id=run.id,
                company_name=run.company_name,
                nivel_promedio_general=0,
                resultados_json=json.dumps({}, ensure_ascii=False),
                preguntas_json=json.dumps([], ensure_ascii=False),
                velocimetros_json=json.dumps({}, ensure_ascii=False)
            )
            db.session.add(ar)
        else:
            ar.company_name = run.company_name
            ar.nivel_promedio_general = 0
            ar.resultados_json = json.dumps({}, ensure_ascii=False)
            ar.preguntas_json = json.dumps([], ensure_ascii=False)
            ar.velocimetros_json = json.dumps({}, ensure_ascii=False)

        db.session.commit()
        return ar.id

    for _, row in df.iterrows():
        estado = pci_estado_normalizado(row["estado"])

        preguntas_detalle.append({
            "bloque_codigo": row["bloque_codigo"],
            "seccion_codigo": row["seccion_codigo"],
            "pregunta_codigo": row["pregunta_codigo"],
            "pregunta": row["pregunta"],
            "estado": estado,
            "comentario": row["comentario"],
        })

    for bloque in PCI_BLOCK_ORDER:
        sub = df[df["bloque_codigo"] == bloque].copy()

        if sub.empty:
            continue

        sub["estado"] = sub["estado"].apply(pci_estado_normalizado)

        counts = {
            "SI": int((sub["estado"] == "SI").sum()),
            "PARCIAL": int((sub["estado"] == "PARCIAL").sum()),
            "NO": int((sub["estado"] == "NO").sum()),
            "NA": int((sub["estado"] == "NA").sum()),
        }

        validos = sub[sub["estado"].isin(["SI", "PARCIAL", "NO"])].copy()
        total_validos = int(len(validos))
        total_respondidas = int(len(sub))

        pct = pci_pct_from_estados(sub["estado"].tolist())
        nivel_info = pci_resolver_nivel(pct)

        resultados[bloque] = {
            "bloque": bloque,
            "nombre": pci_block_title(bloque),
            "pct": pct,
            "madurez": nivel_info["nivel"],
            "color": nivel_info["color"],
            "descripcion": nivel_info["descripcion"],
            "total": total_respondidas,
            "total_validos": total_validos,
            "counts": counts,
            "brecha_pct": round(100 - pct, 2)
        }

    bloques_validos = [
        float(v["pct"])
        for v in resultados.values()
        if int(v.get("total_validos", 0) or 0) > 0
    ]

    promedio_general = (
        round(sum(bloques_validos) / len(bloques_validos), 2)
        if bloques_validos
        else 0
    )

    ar = (
        PciAnalysisRun.query
        .filter_by(pci_run_id=run.id)
        .order_by(PciAnalysisRun.id.desc())
        .first()
    )

    if not ar:
        ar = PciAnalysisRun(
            pci_run_id=run.id,
            company_name=run.company_name
        )
        db.session.add(ar)

    ar.company_name = run.company_name
    ar.nivel_promedio_general = promedio_general
    ar.resultados_json = json.dumps(resultados, ensure_ascii=False)
    ar.preguntas_json = json.dumps(preguntas_detalle, ensure_ascii=False)
    ar.velocimetros_json = json.dumps(resultados, ensure_ascii=False)

    db.session.commit()
    return ar.id


# =========================
# Analisis y Guardar
# =========================

@pci_madurez_bp.route("/ingreso/guardar", methods=["POST"])
@login_required
def ingreso_guardar_pci():
    user = User.query.get(session.get("user_id"))

    company_name = (request.form.get("company_name") or "").strip()
    accion = (request.form.get("accion") or "guardar").strip().lower()
    draft_id = (request.form.get("draft_id") or "").strip()

    if not company_name:
        flash("Debes ingresar el consecutivo de la Revisión.", "warning")
        return redirect(url_for("madurez_pci.ingreso"))

    preguntas = PciMadurezPregunta.query.order_by(PciMadurezPregunta.orden.asc()).all()
    preguntas_q = [p for p in preguntas if p.tipo == "q"]

    respondidas, total, progreso_pct = calcular_progreso_pci(
        preguntas_q,
        form_data=request.form
    )

    try:
        run_form = None

        if draft_id:
            run_form = PciMadurezRun.query.filter_by(id=int(draft_id)).first()
            if run_form and user and run_form.user_id != user.id:
                flash("No tienes permiso para modificar este borrador.", "danger")
                return redirect(url_for("madurez_pci.ingreso"))

        if not run_form:
            run_form = obtener_borrador_pci(user.id if user else None)

        if not run_form:
            run_form = PciMadurezRun(
                company_name=company_name,
                user_id=user.id if user else None,
                estado="BORRADOR",
                progreso_pct=0
            )
            db.session.add(run_form)
            db.session.flush()

        run_form.company_name = company_name
        run_form.progreso_pct = progreso_pct
        run_form.updated_at = datetime.now(timezone.utc)

        PciMadurezRespuesta.query.filter_by(run_id=run_form.id).delete()

        for p in preguntas_q:
            estado = pci_estado_normalizado(request.form.get(f"st_{p.id}"))
            comentario = (request.form.get(f"c_{p.id}") or "").strip()

            if estado in ("SI", "PARCIAL", "NO", "NA"):
                db.session.add(PciMadurezRespuesta(
                    run_id=run_form.id,
                    pregunta_id=p.id,
                    estado=estado,
                    comentario=comentario
                ))

        db.session.flush()

        if accion == "guardar":
            run_form.estado = "BORRADOR"
            db.session.commit()
            flash(f"✅ Borrador PCI-DSS guardado correctamente. Progreso actual: {progreso_pct}%.", "success")
            return redirect(url_for("madurez_pci.ingreso"))

        if accion == "analizar":
            respondidas, total, progreso_pct = calcular_progreso_pci(
                preguntas_q,
                form_data=request.form
            )

            print("=== PCI DEBUG ANALIZAR ===")
            print("accion:", accion)
            print("respondidas:", respondidas)
            print("total:", total)
            print("progreso_pct:", progreso_pct)
            print("=========================")

            if progreso_pct < 100:
                db.session.commit()
                flash(
                    f"⚠️ El análisis solo se habilita cuando el instrumento esté al 100%. Actualmente llevas {progreso_pct}%.",
                    "warning"
                )
                return redirect(url_for("madurez_pci.ingreso"))

            run_form.estado = "FINALIZADO"
            run_form.progreso_pct = 100
            db.session.commit()

            analysis_run_id = run_analysis_from_pci_run(run_form.id)

            flash("✅ Análisis PCI-DSS ejecutado correctamente.", "success")
            return redirect(url_for("madurez_pci.resultado", run_id=analysis_run_id))

        db.session.commit()
        return redirect(url_for("madurez_pci.ingreso"))

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        flash(f"Error guardando/analisando PCI-DSS: {e}", "danger")
        return redirect(url_for("madurez_pci.ingreso"))

# =========================
# Velocimetros
# =========================

def _pci_construir_velocimetro_fig(label: str, pct: float, nivel: str, color: str):
    try:
        pct = max(0.0, min(100.0, float(pct or 0)))

        fig = plt.figure(figsize=(3.8, 2.4))
        ax = fig.add_subplot(111, polar=True)
        ax.set_theta_direction(-1)
        ax.set_theta_offset(np.pi)
        ax.set_ylim(0, 10)

        # fondo semicircular
        theta_bg = np.linspace(0, np.pi, 300)
        ax.plot(theta_bg, [8] * len(theta_bg), linewidth=18, color="#e9ecef", solid_capstyle='round')

        # avance
        frac = pct / 100.0
        theta_val = np.linspace(0, np.pi * frac, 300) if frac > 0 else [0]
        ax.plot(theta_val, [8] * len(theta_val), linewidth=18, color=color, solid_capstyle='round')

        # aguja
        needle_angle = np.pi * frac
        ax.plot([needle_angle, needle_angle], [0, 7.1], color="#0b1220", linewidth=2)

        # centro
        ax.scatter([0], [0], s=30, color="#0b1220", zorder=5)

        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
        ax.spines["polar"].set_visible(False)

        ax.text(0.5, 1.10, label, transform=ax.transAxes, ha="center", va="center",
                fontsize=9, fontweight="bold", color="#101827")
        ax.text(0.5, 0.44, f"{pct:.0f}%", transform=ax.transAxes, ha="center", va="center",
                fontsize=18, fontweight="bold", color="#0b1220")
        ax.text(0.5, 0.26, nivel, transform=ax.transAxes, ha="center", va="center",
                fontsize=8.5, color=color)

        plt.tight_layout()
        return fig
    except Exception as e:
        print(f"[PCI Velocímetro] Error: {e}")
        return None

def generar_pci_velocimetro_png_bytes(titulo, valor, nivel="", color="#6c757d"):
    """
    Genera un velocímetro limpio y legible para incrustar en PDF.
    Retorna bytes PNG.
    """
    try:
        valor = max(0, min(100, float(valor or 0)))

        # Figura más grande y limpia para PDF
        fig = plt.figure(figsize=(7.2, 4.2), dpi=220)
        ax = plt.axes([0.04, 0.08, 0.92, 0.84])
        ax.set_aspect("equal")
        ax.axis("off")

        # Límites controlados para dejar buen espacio al texto
        ax.set_xlim(-1.18, 1.18)
        ax.set_ylim(-0.28, 1.18)

        # Fondo transparente/blanco limpio
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        # =========================
        # Arco base
        # =========================
        outer_r = 1.00
        width = 0.18

        # Tramos del arco
        rangos = [
            (180, 144, "#d9534f"),  # rojo
            (144, 108, "#f0ad4e"),  # naranja
            (108, 72,  "#f7d154"),  # amarillo
            (72,  36,  "#5bc0de"),  # azul
            (36,   0,  "#5cb85c"),  # verde
        ]

        for theta1, theta2, c in rangos:
            ax.add_patch(Wedge(
                (0, 0), outer_r, theta2, theta1,
                width=width,
                facecolor=c,
                edgecolor="white",
                linewidth=2
            ))

        # Aro exterior suave
        ax.add_patch(Circle((0, 0), radius=outer_r, fill=False, linewidth=1.0, edgecolor="#d1d5db"))

        # =========================
        # Marcas del velocímetro
        # =========================
        for pct in range(0, 101, 10):
            ang = math.radians(180 - (pct / 100.0) * 180.0)
            x1 = math.cos(ang) * 0.78
            y1 = math.sin(ang) * 0.78
            x2 = math.cos(ang) * 0.88
            y2 = math.sin(ang) * 0.88
            ax.plot([x1, x2], [y1, y2], linewidth=1.2, color="#4b5563")

        # Etiquetas principales
        for pct in [0, 25, 50, 75, 100]:
            ang = math.radians(180 - (pct / 100.0) * 180.0)
            xt = math.cos(ang) * 0.63
            yt = math.sin(ang) * 0.63
            ax.text(
                xt, yt, f"{pct}",
                ha="center", va="center",
                fontsize=10, fontweight="bold", color="#374151"
            )

        # =========================
        # Aguja
        # =========================
        ang = math.radians(180 - (valor / 100.0) * 180.0)
        xn = math.cos(ang) * 0.72
        yn = math.sin(ang) * 0.72

        aguja = FancyArrowPatch(
            (0, 0), (xn, yn),
            arrowstyle="-|>",
            mutation_scale=18,
            linewidth=2.4,
            color="#0b1220",
            zorder=5
        )
        ax.add_patch(aguja)

        # Centro
        ax.add_patch(Circle((0, 0), radius=0.065, facecolor="#0b1220", edgecolor="white", linewidth=1.0, zorder=6))

        # =========================
        # Textos
        # =========================
        titulo_corto = (titulo or "").strip()
        if len(titulo_corto) > 42:
            titulo_corto = titulo_corto[:39] + "..."

        ax.text(
            0, 1.06, titulo_corto,
            ha="center", va="center",
            fontsize=13, fontweight="bold", color="#0f3d68"
        )

        ax.text(
            0, 0.30, f"{valor:.1f}%",
            ha="center", va="center",
            fontsize=24, fontweight="bold", color=color
        )

        if nivel:
            nivel_txt = str(nivel).strip()
            if len(nivel_txt) > 30:
                nivel_txt = nivel_txt[:27] + "..."
            ax.text(
                0, 0.12, nivel_txt,
                ha="center", va="center",
                fontsize=11, fontweight="bold", color="#374151"
            )

        ax.text(
            -0.96, -0.05, "Bajo",
            ha="left", va="center",
            fontsize=9, color="#4b5563"
        )
        ax.text(
            0.96, -0.05, "Alto",
            ha="right", va="center",
            fontsize=9, color="#4b5563"
        )

        # =========================
        # Exportar a PNG en alta calidad
        # =========================
        buf = io.BytesIO()
        canvas = FigureCanvas(fig)
        canvas.print_png(buf)
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

    except Exception:
        plt.close("all")
        return None

def generar_pci_velocimetro_base64(label: str, pct: float, nivel: str, color: str):
    b = generar_pci_velocimetro_png_bytes(label, pct, nivel, color)
    if not b:
        return None
    return base64.b64encode(b).decode("utf-8")

def cargar_ai_pci_por_run(analysis_run_id: int) -> dict:
    """
    Carga análisis IA por requerimiento PCI si existe el modelo.
    Si el modelo no existe, retorna vacío para que el PDF no falle.
    """
    try:
        if "PciControlAiAnalysis" not in globals():
            return {}

        rows = PciControlAiAnalysis.query.filter_by(
            analysis_run_id=analysis_run_id
        ).all()

        out = {}

        for r in rows:
            out[(r.bloque_codigo or "").strip().upper()] = {
                "id": r.id,
                "bloque_nombre": r.bloque_nombre or "",
                "estado_actual": r.estado_actual or "",
                "estado_requerido": r.estado_requerido or "",
                "plan_accion": r.plan_accion or "",
            }

        return out

    except Exception as e:
        print("No se pudo cargar análisis IA PCI por bloque:", repr(e))
        return {}

def pci_normalizar_texto_rico_guardado(texto: str) -> str:
    txt = (texto or "").strip()
    if not txt:
        return ""

    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = html.unescape(txt)
    txt = txt.replace("```json", "").replace("```", "").strip()

    # Si viene como JSON, extraer campos principales
    try:
        obj = json.loads(txt)
        if isinstance(obj, dict):
            val = (
                obj.get("informe_ejecutivo")
                or obj.get("plan_trabajo")
                or obj.get("texto")
                or ""
            )
            if isinstance(val, list):
                val = json.dumps(val, ensure_ascii=False)
            if isinstance(val, str) and val.strip():
                txt = val.strip()
    except Exception:
        pass

    txt = html.unescape(txt)

    # Convertir <br> a saltos y eliminar HTML
    txt = re.sub(r"<\s*br\s*/?\s*>", "\n", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", "", txt)

    # Quitar títulos que Ollama agrega
    patrones_titulos = [
        r"^\s*\*{1,3}\s*INFORME\s+EJECUTIVO\s+DE\s+MADUREZ\s+PCI[-\s]?DSS\s*\*{1,3}\s*[:\-–—]?\s*",
        r"^\s*#{1,6}\s*INFORME\s+EJECUTIVO\s+DE\s+MADUREZ\s+PCI[-\s]?DSS\s*[:\-–—]?\s*",
        r"^\s*INFORME\s+EJECUTIVO\s+DE\s+MADUREZ\s+PCI[-\s]?DSS\s*[:\-–—]?\s*",
        r"^\s*\*{1,3}\s*DE\s+MADUREZ\s+PCI[-\s]?DSS\s*\*{1,3}\s*[:\-–—]?\s*",
        r"^\s*DE\s+MADUREZ\s+PCI[-\s]?DSS\s*[:\-–—]?\s*",
        r"^\s*\*{1,3}\s*INFORME\s+EJECUTIVO\s*\*{1,3}\s*[:\-–—]?\s*",
        r"^\s*#{1,6}\s*INFORME\s+EJECUTIVO\s*[:\-–—]?\s*",
        r"^\s*INFORME\s+EJECUTIVO\s*[:\-–—]?\s*",
        r"^\s*\*{1,3}\s*RESUMEN\s+EJECUTIVO\s*\*{1,3}\s*[:\-–—]?\s*",
        r"^\s*#{1,6}\s*RESUMEN\s+EJECUTIVO\s*[:\-–—]?\s*",
        r"^\s*RESUMEN\s+EJECUTIVO\s*[:\-–—]?\s*",
        r"^\s*\*{1,3}\s*PLAN\s+DE\s+TRABAJO\s*\*{1,3}\s*[:\-–—]?\s*",
        r"^\s*#{1,6}\s*PLAN\s+DE\s+TRABAJO\s*[:\-–—]?\s*",
        r"^\s*PLAN\s+DE\s+TRABAJO\s*[:\-–—]?\s*",
    ]

    for patron in patrones_titulos:
        txt = re.sub(patron, "", txt, flags=re.IGNORECASE).strip()

    # Quitar markdown residual
    txt = txt.replace("**", "").replace("__", "")

    txt = re.sub(r"[ \t]+\n", "\n", txt)
    txt = re.sub(r"\n[ \t]+", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)

    return txt.strip()

def generar_pci_radar_base64(resultados: dict):
    try:
        labels = []
        values = []

        for code in PCI_BLOCK_ORDER:
            item = (resultados or {}).get(code)
            if not item:
                continue

            total_validos = int(item.get("total_validos", 0) or 0)

            # Si todo el bloque es N/A, NO entra al radar
            if total_validos <= 0:
                continue

            labels.append(code)
            values.append(float(item.get("pct", 0) or 0))

        if not labels:
            return None

        N = len(labels)
        vals = values + values[:1]
        angles = [n / float(N) * 2 * math.pi for n in range(N)]
        angles += angles[:1]

        fig = plt.figure(figsize=(5.2, 4.2), dpi=180)
        ax = plt.subplot(111, polar=True)

        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=8, fontweight="bold")

        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7)

        ax.plot(angles, vals, linewidth=2.2)
        ax.fill(angles, vals, alpha=0.18)

        ax.set_title("Radar de Cumplimiento PCI-DSS", fontsize=11, fontweight="bold", pad=16)

        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0.25)
        plt.close(fig)
        buf.seek(0)

        return base64.b64encode(buf.getvalue()).decode("utf-8")

    except Exception as e:
        print("Error generando radar PCI:", repr(e))
        plt.close("all")
        return None

# =========================
# Resultado y Tablero
# =========================

@pci_madurez_bp.route("/resultado/<int:run_id>", methods=["GET"])
@login_required
def resultado(run_id):
    user = User.query.get(session.get("user_id"))

    if user.role not in ("admin", "auditor") and not verificar_permiso(user, "Nivel de madurez PCI-DSS"):
        flash("No tiene permiso para ver resultados de PCI-DSS.", "danger")
        return redirect(url_for("menu"))

    run = PciAnalysisRun.query.get_or_404(run_id)

    # Recalcular automáticamente sin volver a ingresar información.
    # Usa las respuestas ya guardadas en PciMadurezRespuesta.
    try:
        nuevo_analysis_id = run_analysis_from_pci_run(run.pci_run_id)
        run = PciAnalysisRun.query.get_or_404(nuevo_analysis_id)
    except Exception as e:
        print("Error recalculando PCI-DSS:", repr(e))

    read_only = (user.role == "auditor")

    if read_only:
        boton_informe_ai = """
        <button class="btn btn-outline-secondary rounded-pill px-4 fw-bold" type="button" disabled>
          <i class="bi bi-magic me-2"></i>Generar
        </button>
        """

        boton_editar_informe = """
        <button class="btn btn-outline-secondary rounded-pill px-4 fw-bold" type="button" disabled>
          <i class="bi bi-pencil-square me-2"></i>Editar
        </button>
        """

        boton_plan_ai = """
        <button class="btn btn-outline-secondary rounded-pill px-4 fw-bold" type="button" disabled>
          <i class="bi bi-magic me-2"></i>Generar
        </button>
        """

        boton_editar_plan = """
        <button class="btn btn-outline-secondary rounded-pill px-4 fw-bold" type="button" disabled>
          <i class="bi bi-pencil-square me-2"></i>Editar
        </button>
        """
    else:
        boton_informe_ai = f"""
        <form method="POST" action="{url_for('madurez_pci.informe_ejecutivo_generar_pci', run_id=run.id)}" class="m-0">
          <button type="submit" class="btn btn-success rounded-pill px-4 fw-bold">
            <i class="bi bi-magic me-2"></i>Generar
          </button>
        </form>
        """

        boton_editar_informe = f"""
        <a href="{url_for('madurez_pci.informe_ejecutivo_editar_pci', run_id=run.id)}"
           class="btn btn-primary rounded-pill px-4 fw-bold">
          <i class="bi bi-pencil-square me-2"></i>Editar
        </a>
        """

        boton_plan_ai = f"""
        <form method="POST" action="{url_for('madurez_pci.plan_trabajo_generar_pci', run_id=run.id)}" class="m-0">
          <button type="submit" class="btn btn-success rounded-pill px-4 fw-bold">
            <i class="bi bi-magic me-2"></i>Generar
          </button>
        </form>
        """

        boton_editar_plan = f"""
        <a href="{url_for('madurez_pci.plan_trabajo_editar_pci', run_id=run.id)}"
           class="btn btn-primary rounded-pill px-4 fw-bold">
          <i class="bi bi-pencil-square me-2"></i>Editar
        </a>
        """

    try:
        resultados = json.loads(run.resultados_json or "{}")
    except Exception:
        resultados = {}

    radar_b64 = generar_pci_radar_base64(resultados)

    informe_ai = pci_normalizar_texto_rico_guardado(run.informe_ejecutivo_ai or "")
    informe_editado = pci_normalizar_texto_rico_guardado(run.informe_ejecutivo_editado or "")
    informe_mostrar = informe_editado if informe_editado != "" else informe_ai

    plan_ai = pci_normalizar_texto_rico_guardado(run.plan_trabajo_ai or "")
    plan_editado = pci_normalizar_texto_rico_guardado(run.plan_trabajo_editado or "")
    plan_mostrar = plan_editado if plan_editado != "" else plan_ai

    def esc(x):
        return escape(x or "")

    def nl2br(x):
        txt = pci_normalizar_texto_rico_guardado(x or "")
        return txt.replace("\n", "<br>")

    tarjetas = []

    for code in PCI_BLOCK_ORDER:
        item = resultados.get(code)
        if not item:
            continue

        total_validos = int(item.get("total_validos", 0) or 0)

        # Si todo el bloque es N/A, NO se muestra en el detalle
        # Ejemplo: A2 con SI=0, PARCIAL=0, NO=0, NA=3
        if total_validos <= 0:
            continue

        img_b64 = generar_pci_velocimetro_base64(
            pci_block_title(code),
            item.get("pct", 0),
            item.get("madurez", ""),
            item.get("color", "#6c757d")
        )

        tarjetas.append({
            "code": code,
            "title": pci_block_title(code),
            "pct": float(item.get("pct", 0) or 0),
            "madurez": item.get("madurez", ""),
            "color": item.get("color", "#6c757d"),
            "descripcion": item.get("descripcion", ""),
            "brecha_pct": float(item.get("brecha_pct", 0) or 0),
            "total": int(item.get("total", 0) or 0),
            "total_validos": total_validos,
            "counts": item.get("counts", {}),
            "img_b64": img_b64,
        })

    cards_html = []

    for t in tarjetas:
        counts = t["counts"] or {}

        img_html = ""
        if t.get("img_b64"):
            img_html = f"""
            <img src="data:image/png;base64,{t['img_b64']}"
                 class="img-fluid pcires-gauge mb-2"
                 alt="{esc(t['title'])}">
            """

        cards_html.append(f"""
        <div class="col-12 col-lg-6">
          <div class="pcires-card p-4 h-100">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
              <div>
                <div class="pcires-card-title">{esc(t["title"])}</div>
                <div class="small text-muted">
                  Total respondidas: <b>{t["total"]}</b> ·
                  Válidas: <b>{t["total_validos"]}</b> ·
                  Brecha: <b>{t["brecha_pct"]:.2f}%</b>
                </div>
              </div>
              <span class="badge rounded-pill px-3 py-2"
                    style="background:{t['color']}; color:#fff;">
                {esc(t["madurez"])}
              </span>
            </div>

            <div class="text-center">
              {img_html}
            </div>

            <div class="row g-2 mt-1">
              <div class="col-6 col-md-3">
                <div class="mini-stat bg-success-subtle text-success-emphasis">Sí<br><b>{counts.get("SI",0)}</b></div>
              </div>
              <div class="col-6 col-md-3">
                <div class="mini-stat bg-warning-subtle text-dark">Parcial<br><b>{counts.get("PARCIAL",0)}</b></div>
              </div>
              <div class="col-6 col-md-3">
                <div class="mini-stat bg-danger-subtle text-danger-emphasis">No<br><b>{counts.get("NO",0)}</b></div>
              </div>
              <div class="col-6 col-md-3">
                <div class="mini-stat bg-secondary-subtle text-secondary-emphasis">N/A<br><b>{counts.get("NA",0)}</b></div>
              </div>
            </div>

            <div class="d-flex justify-content-center mt-3">
              <a href="{url_for('madurez_pci.resultado_bloque_preguntas', run_id=run.id, bloque_codigo=t['code'])}"
                 class="btn btn-outline-primary rounded-pill px-4 fw-bold">
                <i class="bi bi-list-check me-2"></i>Ver preguntas respondidas
              </a>
            </div>
          </div>
        </div>
        """)

    radar_html = ""
    if radar_b64:
        radar_html = f"""
        <div class="pcires-card p-4 h-100">
          <div class="pcires-card-title">🕸️ Radar de cumplimiento PCI-DSS</div>
          <div class="text-muted small mb-2">
            Vista comparativa por requerimiento. N/A no afecta el cálculo.
          </div>
          <div class="text-center">
            <img src="data:image/png;base64,{radar_b64}"
                 class="img-fluid pcires-radar"
                 alt="Radar PCI-DSS">
          </div>
        </div>
        """

    top_html = f"""
    <div class="row g-3 mb-4">

      <div class="col-12 col-xl-4">
        <div class="pcires-card p-4 h-100">
          <div class="pcires-card-title">📌 Resultado General PCI-DSS</div>
          <div class="text-muted small mb-3">
            Cálculo recalculado desde las respuestas guardadas.
          </div>

          <div class="pcires-general-score-box">
            <div class="pcires-general-score-label">Cumplimiento general</div>
            <div class="pcires-general-score-value">{float(run.nivel_promedio_general or 0):.2f}%</div>
            <div class="pcires-general-score-subtitle">
              Revisión: <b>{esc(run.company_name or '')}</b>
            </div>
          </div>

          <div class="alert alert-info mt-3 mb-0 small rounded-4 border-0">
            <b>Nota:</b> las respuestas N/A cuentan como respondidas, pero se excluyen del denominador de madurez.
          </div>
        </div>
      </div>

      <div class="col-12 col-xl-4">
        {radar_html}
      </div>

      <div class="col-12 col-xl-4">
        <div class="pcires-card p-4 h-100">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div>
              <div class="fw-bold text-black">🧾 Informe ejecutivo</div>
              <div class="text-muted small">Síntesis ejecutiva general.</div>
            </div>
            <div class="d-flex gap-2 flex-wrap">
              {boton_informe_ai}
              {boton_editar_informe}
            </div>
          </div>

          <div class="pcires-exec-box mt-3">
            {f'<div class="pcires-exec-text">{nl2br(informe_mostrar)}</div>' if informe_mostrar else '<div class="text-muted">Aún no hay informe ejecutivo.</div>'}
          </div>
        </div>
      </div>

    </div>

    <div class="row g-3 mb-4">
      <div class="col-12">
        <div class="pcires-card p-4 h-100">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div>
              <div class="fw-bold text-black">🗂️ Plan de trabajo</div>
              <div class="text-muted small">Plan general de cierre de brechas.</div>
            </div>
            <div class="d-flex gap-2 flex-wrap">
              {boton_plan_ai}
              {boton_editar_plan}
            </div>
          </div>

          <div class="pcires-exec-box mt-3">
            {f'<div class="pcires-exec-text">{nl2br(plan_mostrar)}</div>' if plan_mostrar else '<div class="text-muted">Aún no hay plan de trabajo.</div>'}
          </div>
        </div>
      </div>
    </div>
    """

    content = f"""
    <div class="pcires-shell">

      <div class="pcires-header-card">
        <div class="pcires-header-overlay">
          <div class="pcires-header-text">
            <h3 class="pcires-title m-0">Resultado — PCI-DSS</h3>
            <div class="pcires-subtitle">
              Revisión: <b>{esc(run.company_name or '')}</b>
              · Cumplimiento general: <b>{float(run.nivel_promedio_general or 0):.2f}%</b>
            </div>
          </div>
        </div>
      </div>

      <div class="pcires-header-actions">
        <a href="{url_for('madurez_pci.historial')}"
           class="btn pcires-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al historial
        </a>

        <a href="{url_for('madurez_pci.inicio_pci')}"
           class="btn pcires-btn-soft rounded-pill px-4 fw-bold">
          <i class="bi bi-house-door-fill me-2"></i>Volver al módulo
        </a>
      </div>

      {"<div class='alert alert-info'>🔒 El perfil Auditor puede consultar el resultado PCI-DSS, pero no puede generar ni editar el informe ejecutivo ni el plan de trabajo.</div>" if read_only else ""}

      {top_html}

      <div class="row g-3">
        {''.join(cards_html)}
      </div>

    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .pcires-shell{{
        width:96%;
        max-width:1650px;
        margin:26px auto 24px auto;
      }}

      .pcires-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .pcires-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .pcires-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .pcires-header-overlay::before{{
        content:"💳";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .pcires-header-text::before{{
        content:"SGSI · Resultado PCI-DSS";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .pcires-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .pcires-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .pcires-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .pcires-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .pcires-btn-main{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .pcires-btn-soft{{
        background:rgba(255,255,255,.88);
        color:#111;
        border:1px solid rgba(108,117,125,.35);
      }}

      .pcires-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .pcires-card-title{{
        font-weight:950;
        font-size:1rem;
        color:#0b4a8f;
        margin-bottom:8px;
      }}

      .pcires-general-score-box{{
        background:linear-gradient(135deg,#eef5ff,#ffffff);
        border:1px solid rgba(63,134,214,.20);
        border-radius:18px;
        padding:22px 18px;
        text-align:center;
      }}

      .pcires-general-score-label{{
        font-size:.78rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
      }}

      .pcires-general-score-value{{
        font-size:3rem;
        line-height:1;
        font-weight:950;
        color:#0f172a;
        margin:8px 0;
      }}

      .pcires-general-score-subtitle{{
        font-size:.82rem;
        color:#475569;
      }}

      .pcires-radar{{
        max-width:420px;
        width:100%;
        height:auto;
      }}

      .pcires-gauge{{
        max-width:230px;
        width:100%;
        height:auto;
      }}

      .pcires-exec-box{{
        min-height:220px;
        max-height:420px;
        overflow:auto;
        background:linear-gradient(180deg,rgba(248,250,252,.94),rgba(255,255,255,.98));
        border:1px solid rgba(63,134,214,.16);
        border-radius:16px;
        padding:18px;
      }}

      .pcires-exec-text{{
        font-size:.95rem;
        line-height:1.6;
        color:#101827;
      }}

      .mini-stat{{
        border-radius:12px;
        padding:8px 7px;
        text-align:center;
        font-size:.84rem;
        font-weight:900;
        box-shadow:0 4px 10px rgba(15,23,42,.08);
      }}

      @media (max-width:768px){{
        .pcires-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .pcires-header-overlay::before{{
          margin:0;
        }}

        .pcires-title,
        .pcires-subtitle{{
          text-align:center;
        }}

        .pcires-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Resultado PCI-DSS", content=content)


@pci_madurez_bp.route("/resultado/<int:run_id>/bloque/<string:bloque_codigo>/preguntas", methods=["GET"])
@login_required
def resultado_bloque_preguntas(run_id, bloque_codigo):
    user = User.query.get(session.get("user_id"))

    if user.role not in ("admin", "auditor") and not verificar_permiso(user, "Nivel de madurez PCI-DSS"):
        flash("No tiene permiso para ver el detalle de preguntas PCI-DSS.", "danger")
        return redirect(url_for("menu"))

    run = PciAnalysisRun.query.get_or_404(run_id)

    try:
        preguntas_detalle = json.loads(run.preguntas_json or "[]")
    except Exception:
        preguntas_detalle = []

    bloque_codigo = (bloque_codigo or "").strip().upper()
    bloque_titulo = pci_block_title(bloque_codigo)

    preguntas = [
        p for p in preguntas_detalle
        if (p.get("bloque_codigo") or "").strip().upper() == bloque_codigo
    ]

    def esc(x):
        return escape(x or "")

    rows = []
    for p in preguntas:
        estado = (p.get("estado") or "").strip().upper()
        badge_cls = {
            "SI": "bg-success",
            "PARCIAL": "bg-warning text-dark",
            "NO": "bg-danger",
            "NA": "bg-secondary"
        }.get(estado, "bg-secondary")

        rows.append(f"""
        <tr>
          <td style="width:15%;">
            <div class="fw-bold">{esc(p.get("pregunta_codigo") or "")}</div>
            <div class="small text-muted">{esc(p.get("seccion_codigo") or "")}</div>
          </td>
          <td style="width:47%;">{esc(p.get("pregunta") or "")}</td>
          <td style="width:13%;" class="text-center">
            <span class="badge {badge_cls}">{esc(estado)}</span>
          </td>
          <td style="width:25%;">{esc(p.get("comentario") or "")}</td>
        </tr>
        """)

    content = f"""
    <div class="pcidet-shell">

      <div class="pcidet-header-card">
        <div class="pcidet-header-overlay">
          <div class="pcidet-header-text">
            <h3 class="pcidet-title m-0">Detalle de Preguntas — {esc(bloque_titulo)}</h3>
            <div class="pcidet-subtitle">
              Revisión: <b>{esc(run.company_name or '')}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="pcidet-header-actions">
        <a href="{url_for('madurez_pci.resultado', run_id=run.id)}"
           class="btn pcidet-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al resultado
        </a>

        <a href="{url_for('madurez_pci.inicio_pci')}"
           class="btn pcidet-btn-soft rounded-pill px-4 fw-bold">
          <i class="bi bi-house-door-fill me-2"></i>Volver al módulo
        </a>
      </div>

      <div class="pcidet-card p-4">
        <div class="pcidet-section-title">Preguntas respondidas del bloque</div>

        <div class="table-responsive">
          <table class="table table-hover align-middle pcidet-table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Pregunta</th>
                <th class="text-center">Estado</th>
                <th>Comentario</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows) if rows else '<tr><td colspan="4" class="text-center text-muted py-4">No hay preguntas registradas para este bloque.</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .pcidet-shell{{
        width:96%;
        max-width:1650px;
        margin:26px auto 24px auto;
      }}

      .pcidet-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .pcidet-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .pcidet-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .pcidet-header-overlay::before{{
        content:"📄";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .pcidet-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .pcidet-header-text::before{{
        content:"SGSI · Detalle PCI-DSS";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .pcidet-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .pcidet-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .pcidet-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .pcidet-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .pcidet-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .pcidet-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .pcidet-btn-soft{{
        background:rgba(255,255,255,.88);
        color:#111 !important;
        border:1px solid rgba(108,117,125,.35);
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .pcidet-btn-soft:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .pcidet-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .pcidet-section-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }}

      .table-responsive{{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }}

      .pcidet-table,
      .table{{
        width:100%;
        margin-bottom:0 !important;
      }}

      .pcidet-table thead th,
      .table thead th{{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-size:.78rem;
        font-weight:900 !important;
        border:none !important;
        white-space:nowrap;
        vertical-align:middle !important;
        text-align:center;
        padding:9px 8px;
      }}

      .pcidet-table td,
      .pcidet-table th,
      .table tbody td{{
        vertical-align:middle !important;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }}

      .table tbody tr:nth-child(even){{
        background:#f8fbff;
      }}

      .table tbody tr:hover,
      .pcidet-table tbody tr:hover{{
        background:#eef6ff;
      }}

      .wrap{{
        white-space:normal !important;
        word-break:break-word;
        overflow-wrap:anywhere;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:991.98px){{
        .pcidet-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .pcidet-header-card{{
          min-height:88px;
        }}

        .pcidet-title{{
          font-size:1.20rem;
        }}

        .pcidet-subtitle{{
          font-size:.68rem;
        }}
      }}

      @media (max-width:768px){{
        .pcidet-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .pcidet-header-overlay::before{{
          margin:0;
        }}

        .pcidet-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .pcidet-title,
        .pcidet-subtitle{{
          text-align:center;
        }}

        .pcidet-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title=f"Detalle {bloque_titulo}", content=content)

# =========================
# Exportación PDF
# =========================

@pci_madurez_bp.route("/exportar_pdf/<int:run_id>")
@login_required
def exportar_pdf(run_id):
    run = PciAnalysisRun.query.get_or_404(run_id)

    try:
        resultados = json.loads(run.resultados_json or "{}")
    except Exception:
        resultados = {}

    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
        title="PCI-DSS - Informe Ejecutivo"
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="PCI_Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="PCI_Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#1d4f8f"),
        spaceBefore=10,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="PCI_Normal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#101827"),
        spaceAfter=5
    ))

    styles.add(ParagraphStyle(
        name="PCI_Small",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#374151"),
        spaceAfter=4
    ))

    story = []

    def pdf_escape(v):
        return html.escape(str(v or ""))

    def nivel_color(pct):
        try:
            pct = float(pct or 0)
        except Exception:
            pct = 0

        if pct >= 81:
            return colors.HexColor("#198754")
        if pct >= 61:
            return colors.HexColor("#0d6efd")
        if pct >= 41:
            return colors.HexColor("#ffc107")
        if pct >= 21:
            return colors.HexColor("#fd7e14")
        return colors.HexColor("#dc3545")

    def nivel_badge_pdf(pct, nivel_txt):
        c = nivel_color(pct)
        nivel_txt = str(nivel_txt or "Sin nivel").strip()

        badge = Table(
            [[
                "",
                Paragraph(pdf_escape(nivel_txt), styles["PCI_Small"])
            ]],
            colWidths=[0.28 * cm, 4.25 * cm]
        )

        badge.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), c),
            ("BOX", (0, 0), (0, 0), 0.25, c),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))

        return badge

    def add_section(title):
        table = Table(
            [[Paragraph(pdf_escape(title), styles["PCI_Title"])]],
            colWidths=[26.8 * cm]
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#3f86d6")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#1d4f8f")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(table)
        story.append(Spacer(1, 8))

    def add_text_block(texto):
        texto = pci_normalizar_texto_rico_guardado(texto or "")
        if not texto:
            story.append(Paragraph("No hay información registrada.", styles["PCI_Normal"]))
            return

        for parrafo in re.split(r"\n\s*\n", texto):
            parrafo = parrafo.strip()
            if parrafo:
                story.append(Paragraph(pdf_escape(parrafo), styles["PCI_Normal"]))

    # =========================
    # ENCABEZADO
    # =========================
    add_section("PCI-DSS - Informe de Madurez")

    pct_general = float(run.nivel_promedio_general or 0)
    nivel_general = pci_resolver_nivel(pct_general)

    resumen_tbl = Table([
        ["Revisión", pdf_escape(run.company_name)],
        ["Fecha", run.fecha_calculo.strftime("%Y-%m-%d %H:%M") if run.fecha_calculo else ""],
        [
            "Cumplimiento general",
            f"{pct_general:.2f}% - {pdf_escape(nivel_general.get('nivel', 'Sin nivel'))}"
        ],
        ["Nivel de madurez", pdf_escape(nivel_general.get("nivel", "Sin nivel"))]
    ], colWidths=[5.2 * cm, 21.6 * cm])

    resumen_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f1fb")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1d4f8f")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8e3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(resumen_tbl)
    story.append(Spacer(1, 12))

    # =========================
    # INFORME EJECUTIVO
    # =========================
    story.append(Paragraph("Informe Ejecutivo", styles["PCI_Section"]))

    informe_exec = (
        run.informe_ejecutivo_editado
        or run.informe_ejecutivo_ai
        or ""
    ).strip()

    add_text_block(informe_exec)
    story.append(Spacer(1, 10))

    # =========================
    # TABLA GENERAL
    # =========================
    story.append(Paragraph("Detalle por Requerimiento / Apéndice", styles["PCI_Section"]))

    data = [[
        "Bloque",
        "Nombre",
        "% Cumplimiento",
        "Nivel de madurez",
        "Items",
        "Brecha"
    ]]

    for code in PCI_BLOCK_ORDER:
        item = (resultados or {}).get(code)
        if not item:
            continue

        pct = float(item.get("pct", 0) or 0)
        total = int(item.get("total", 0) or 0)
        brecha = float(item.get("brecha_pct", max(0.0, 100.0 - pct)) or 0)
        nivel_txt = item.get("madurez") or pci_resolver_nivel(pct).get("nivel", "Sin nivel")

        data.append([
            Paragraph(pdf_escape(code), styles["PCI_Small"]),
            Paragraph(pdf_escape(pci_block_title(code)), styles["PCI_Small"]),
            Paragraph(f"{pct:.2f}%", styles["PCI_Small"]),
            nivel_badge_pdf(pct, nivel_txt),
            Paragraph(str(total), styles["PCI_Small"]),
            Paragraph(f"{brecha:.2f}%", styles["PCI_Small"])
        ])

    tbl = Table(
        data,
        colWidths=[2.6 * cm, 8.8 * cm, 3.0 * cm, 5.4 * cm, 2.2 * cm, 3.0 * cm],
        repeatRows=1
    )

    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3f86d6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7.2),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8e3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
        ("ALIGN", (4, 1), (5, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.append(tbl)

    # =========================
    # ANÁLISIS POR REQUERIMIENTO
    # =========================
    ai_por_bloque = cargar_ai_pci_por_run(run.id)

    if ai_por_bloque:
        story.append(PageBreak())
        add_section("Análisis Ejecutivo por Requerimiento")

        for code in PCI_BLOCK_ORDER:
            a = ai_por_bloque.get(code)
            if not a:
                continue

            titulo = f"{code} - {pci_block_title(code)}"
            story.append(Paragraph(pdf_escape(titulo), styles["PCI_Section"]))

            estado_actual = pci_normalizar_texto_rico_guardado(a.get("estado_actual") or "")
            estado_requerido = pci_normalizar_texto_rico_guardado(a.get("estado_requerido") or "")
            plan_accion = pci_normalizar_texto_rico_guardado(a.get("plan_accion") or "")

            bloque = Table([
                [
                    Paragraph("<b>Estado actual</b>", styles["PCI_Small"]),
                    Paragraph(pdf_escape(estado_actual or "No registrado."), styles["PCI_Small"])
                ],
                [
                    Paragraph("<b>Estado requerido</b>", styles["PCI_Small"]),
                    Paragraph(pdf_escape(estado_requerido or "No registrado."), styles["PCI_Small"])
                ],
                [
                    Paragraph("<b>Plan de acción</b>", styles["PCI_Small"]),
                    Paragraph(pdf_escape(plan_accion or "No registrado."), styles["PCI_Small"])
                ],
            ], colWidths=[4.2 * cm, 22.6 * cm])

            bloque.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f1fb")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1d4f8f")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8e3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))

            story.append(bloque)
            story.append(Spacer(1, 10))

    doc.build(story)
    buf.seek(0)

    filename = f"PCI_DSS_{(run.company_name or 'revision').replace(' ', '_')}.pdf"

    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )

# =====================================================================
# PANTALLA PRINCIPAL PCI-DSS
# =====================================================================

@pci_madurez_bp.route("/", methods=["GET"], endpoint="inicio_pci")
@login_required
def inicio_pci():
    user = User.query.get(session.get("user_id"))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez PCI-DSS"):
        flash("No tiene permiso para acceder al módulo de nivel de madurez PCI-DSS.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == 'auditor')

    if read_only:
        ingreso_btn = """
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled
                  title="El rol Auditor no puede ingresar información">
            <i class="bi bi-pencil-square me-2"></i>Ingresar la información
          </button>
        """
    else:
        ingreso_btn = f"""
          <a href="{url_for('madurez_pci.ingreso')}" class="btn btn-primary rounded-pill px-4 fw-bold">
            <i class="bi bi-pencil-square me-2"></i>Ingresar la información
          </a>
        """

    if read_only:
        parametros_btn = """
          <button class="btn btn-outline-secondary rounded-pill px-3" disabled
                  title="El rol Auditor no tiene acceso a Parámetros">
            <i class="bi bi-gear me-2"></i>Parámetros
          </button>
        """
    else:
        parametros_btn = f"""
          <a href="{url_for('madurez_pci.parametros')}" class="btn btn-outline-secondary rounded-pill px-3">
            <i class="bi bi-gear me-2"></i>Parámetros
          </a>
        """

    total = PciMadurezPregunta.query.filter_by(tipo="q").count()

    if total == 0:
        badge = '<span class="badge bg-danger ms-2">Instrumento NO cargado</span>'
        hint = "Primero entra a Parámetros y realiza la importación del instrumento PCI-DSS (solo una vez)."
    else:
        badge = '<span class="badge bg-success ms-2">Instrumento cargado</span>'
        hint = "Puedes ingresar la información, analizar la evaluación o consultar el historial de revisiones."

    content = f"""
    <div class="pcimad-shell">
      <div class="pcimad-header-card">
        <div class="pcimad-header-overlay">
          <div class="pcimad-header-text">
            <h3 class="pcimad-title m-0">Nivel de Madurez — PCI-DSS</h3>
            <div class="pcimad-subtitle">
              Evaluación del nivel de cumplimiento y madurez de los 12 requerimientos y los apéndices A1 y A2 de PCI-DSS.
            </div>
          </div>
        </div>
      </div>

      <div class="pcimad-header-actions">
        {ingreso_btn}
        <a href="{url_for('madurez_pci.historial')}" class="btn pcimad-btn-soft rounded-pill px-4">
          <i class="bi bi-clock-history me-2"></i>Historial de Revisiones
        </a>
      </div>

      <div class="row g-3 mt-2">
        <div class="col-12 col-lg-8">
          <div class="pcimad-card p-4 h-100">
            <div class="pcimad-section-title">Estado del instrumento</div>
            <div class="fw-bold">Estado del instrumento {badge}</div>
            <div class="text-muted small mt-1">Preguntas cargadas: <b>{total}</b></div>
            <div class="mt-2 small">{hint}</div>

            <div class="mt-3">{parametros_btn}</div>

            <div class="alert alert-info mt-3 mb-0 small">
              <b>Sugerencia:</b> importa el Excel original de PCI-DSS sin traducción, manteniendo los textos tal cual vienen en el instrumento.
            </div>
          </div>
        </div>

        <div class="col-12 col-lg-4">
          <div class="pcimad-card p-4 h-100">
            <div class="pcimad-section-title">¿Qué puedes hacer aquí?</div>
            <ul class="small mb-0 text-black ps-3">
              <li><b>Ingresar la información:</b> diligenciar respuestas por requisito con opciones Sí / Parcial / No / N/A.</li>
              <li><b>Historial:</b> revisar evaluaciones previas, porcentajes y análisis ejecutados.</li>
              <li><b>Parámetros:</b> importar el instrumento y consultar la escala de madurez.</li>
              <li><b>Tablero:</b> visualizar velocímetros por requerimiento y apéndices en los resultados.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .pcimad-shell{{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }}

      .pcimad-header-card{{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:14px;
      }}

      .pcimad-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .pcimad-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .pcimad-header-overlay::before{{
        content:"💳";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .pcimad-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .pcimad-header-text::before{{
        content:"SGSI · PCI-DSS";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .pcimad-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .pcimad-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .pcimad-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .pcimad-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .pcimad-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .pcimad-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .pcimad-btn-soft{{
        background:rgba(255,255,255,.88);
        color:#111 !important;
        border:1px solid rgba(108,117,125,.35);
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .pcimad-btn-soft:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .pcimad-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .pcimad-card.p-4{{
        padding:1.5rem !important;
      }}

      .pcimad-section-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
      }}

      .pcimad-section-title{{
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }}

      .pcimad-card ul li{{
        margin-bottom:8px;
      }}

      .pcimad-card ul li:last-child{{
        margin-bottom:0;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      .text-muted.small{{
        font-size:.84rem;
        line-height:1.45;
      }}

      .form-label{{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:6px 10px;
        border-radius:10px;
        display:inline-block;
        margin-bottom:6px;
      }}

      .form-control,
      .form-select{{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      .form-control:focus,
      .form-select:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      @media (max-width:991.98px){{
        .pcimad-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .pcimad-header-card{{
          min-height:88px;
        }}

        .pcimad-title{{
          font-size:1.20rem;
        }}

        .pcimad-subtitle{{
          font-size:.68rem;
        }}
      }}

      @media (max-width:768px){{
        .pcimad-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .pcimad-header-overlay::before{{
          margin:0;
        }}

        .pcimad-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .pcimad-title,
        .pcimad-subtitle{{
          text-align:center;
        }}

        .pcimad-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Madurez PCI-DSS", content=content)

# =========================
# Ingreso
# =========================

