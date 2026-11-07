def jira_is_enabled():
    return all([
        JIRA_ENABLED,
        (JIRA_BASE_URL or "").strip(),
        (JIRA_EMAIL or "").strip(),
        (JIRA_API_TOKEN or "").strip(),
        (JIRA_PROJECT_KEY or "").strip()
    ])


def jira_auth():
    return HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)


def jira_headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }


def jira_priority_name(prioridad_local: str) -> str:
    p = (prioridad_local or "").strip().lower()
    if p == "alta":
        return "High"
    if p == "media":
        return "Medium"
    if p == "baja":
        return "Low"
    return "Medium"


def limpiar_texto_jira(txt, max_len=None):
    valor = (txt or "").strip()
    if max_len:
        valor = valor[:max_len]
    return valor


def descripcion_plan_para_jira(plan, vuln):
    fecha_obj = plan.fecha_objetivo.strftime("%Y-%m-%d") if plan.fecha_objetivo else "No definida"

    return f"""
Plan de remediación generado desde el SGSI.

Vulnerabilidad asociada:
- Código: {vuln.codigo or 'N/A'}
- Activo: {vuln.activo or 'N/A'}
- Descripción: {vuln.descripcion_vulnerabilidad or 'N/A'}
- CVE: {vuln.cve or 'N/A'}
- CVSS: {vuln.cvss or 'N/A'}
- Clasificación: {vuln.clasificacion or 'N/A'}
- Estado vulnerabilidad: {vuln.estado or 'N/A'}

Plan de remediación:
- ID interno: {plan.id}
- Responsable SGSI: {plan.responsable or 'N/A'}
- Prioridad: {plan.prioridad or 'N/A'}
- Estado: {plan.estado or 'N/A'}
- Fecha objetivo: {fecha_obj}

Acción correctiva:
{plan.accion_correctiva or 'N/A'}

Recursos necesarios:
{plan.recursos_necesarios or 'N/A'}
""".strip()

def jira_adf_parrafo(texto: str, bold=False):
    if not texto:
        return {
            "type": "paragraph",
            "content": []
        }

    nodo = {
        "type": "text",
        "text": texto[:5000]
    }

    if bold:
        nodo["marks"] = [{"type": "strong"}]

    return {
        "type": "paragraph",
        "content": [nodo]
    }


def jira_adf_descripcion_plan(vuln, plan):
    contenido = []

    contenido.append(jira_adf_parrafo(f"Remediación de vulnerabilidad {vuln.codigo or '—'}", bold=True))
    contenido.append(jira_adf_parrafo(f"Activo: {vuln.activo or '—'}"))
    contenido.append(jira_adf_parrafo(f"Descripción vulnerabilidad: {vuln.descripcion_vulnerabilidad or '—'}"))
    contenido.append(jira_adf_parrafo(f"Acción correctiva: {plan.accion_correctiva or '—'}"))
    contenido.append(jira_adf_parrafo(f"Responsable SGSI: {plan.responsable or '—'}"))
    contenido.append(jira_adf_parrafo(f"Prioridad: {plan.prioridad or '—'}"))
    contenido.append(jira_adf_parrafo(f"Fecha objetivo: {plan.fecha_objetivo or '—'}"))
    contenido.append(jira_adf_parrafo(f"Recursos necesarios: {plan.recursos_necesarios or '—'}"))
    contenido.append(jira_adf_parrafo(f"Estado interno: {plan.estado or '—'}"))

    return {
        "type": "doc",
        "version": 1,
        "content": contenido
    }


def jira_consultar_issue(issue_key: str):
    if not jira_is_enabled():
        raise RuntimeError("Jira no está configurado correctamente.")

    url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue/{issue_key}"
    resp = requests.get(
        url,
        headers=jira_headers(),
        auth=jira_auth(),
        timeout=30
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Error consultando issue Jira: {resp.status_code} - {resp.text}")

    return resp.json()

def _month_range(anio: int, mes: int):
    last_day = calendar.monthrange(anio, mes)[1]
    start = f"{anio:04d}-{mes:02d}-01"
    end   = f"{anio:04d}-{mes:02d}-{last_day:02d}"
    return start, end


# ==========================
# HELPERS Nivel de Madurez
# ==========================
def to_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return "\n".join([to_text(x) for x in v if x is not None])
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False, indent=2)
    return str(v)

def load_instrument_structure(xlsx_path: str):
    xls = pd.ExcelFile(xlsx_path)
    sheets = []
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name, header=None)

        # Detectar si es "ANEXO A" por encabezado "Preguntas" en col 4
        is_anexo_a = False
        if df.shape[0] > 2:
            v = str(df.iloc[1, 4]) if df.shape[1] > 4 else ""
            if "preguntas" in v.lower():
                is_anexo_a = True

        items = []

        if is_anexo_a:
            # Header suele estar en fila 1, preguntas desde fila 3 aprox.
            # Columnas:
            # 0: idx, 1: control, 2: tema, 3: descripcion, 4: pregunta,
            # 5: no aplica, 6: si, 7: parcialmente, 8: no, 9: comentarios
            start_row = 3
            for r in range(start_row, len(df)):
                pregunta = df.iloc[r, 4] if df.shape[1] > 4 else None
                if pd.isna(pregunta) or not str(pregunta).strip():
                    continue

                control = df.iloc[r, 1] if df.shape[1] > 1 else ""
                tema = df.iloc[r, 2] if df.shape[1] > 2 else ""
                items.append({
                    "row": r,
                    "tipo": "q",
                    "control": "" if pd.isna(control) else str(control).strip(),
                    "tema": "" if pd.isna(tema) else str(tema).strip(),
                    "pregunta": str(pregunta).strip(),
                    "layout": "anexo_a"
                })

        else:
            # Capítulos (4-10): encabezado suele estar en fila 0
            # Columnas:
            # 1: pregunta/texto, 2..5 opciones, 6 comentarios
            start_row = 1
            for r in range(start_row, len(df)):
                texto = df.iloc[r, 1] if df.shape[1] > 1 else None
                if pd.isna(texto) or not str(texto).strip():
                    continue

                txt = str(texto).strip()

                # Si parece ser un título de cláusula (ej: "4.1 ...", "5.2 ...") lo marcamos como header
                is_header = bool(
                    (len(txt) < 120) and (
                        txt.startswith(("4.", "5.", "6.", "7.", "8.", "9.", "10.")) and
                        ("¿" not in txt)
                    )
                )

                items.append({
                    "row": r,
                    "tipo": "h" if is_header else "q",
                    "pregunta": txt,
                    "layout": "capitulo"
                })

        sheets.append({
            "name": sheet_name,
            "items": items
        })

    return sheets

def render_action_plan_table(plan: list) -> str:
    if not plan:
        return "<div class='text-muted small'>Aún no se ha generado el plan de acción general.</div>"

    tr = ""
    for row in plan[:250]:
        if not isinstance(row, dict):
            continue
        tr += f"""
        <tr class="cell-small">
          <td class="wrap" style="min-width:260px;">{xml_escape(to_text(row.get("accion")) )}</td>
          <td class="wrap" style="min-width:220px;">{xml_escape(to_text(row.get("proposito")) )}</td>
          <td class="wrap" style="min-width:240px;">{xml_escape(to_text(row.get("evidencia")) )}</td>
          <td class="text-muted" style="min-width:90px;">{xml_escape(to_text(row.get("prioridad")) )}</td>
          <td class="text-muted" style="min-width:90px;">{xml_escape(to_text(row.get("horizonte")) )}</td>
          <td class="wrap" style="min-width:220px;">{xml_escape(to_text(row.get("dependencia")) )}</td>
        </tr>
        """

    return f"""
    <div class="table-responsive mt-2" style="max-height: 460px; overflow:auto;">
      <table class="table table-sm table-striped align-middle table-tight">
        <thead>
          <tr>
            <th>Acción</th>
            <th>Propósito</th>
            <th>Evidencia</th>
            <th>Prioridad</th>
            <th>Horizonte</th>
            <th>Dependencia</th>
          </tr>
        </thead>
        <tbody>
          {tr if tr else "<tr><td colspan='6' class='text-muted'>Sin datos.</td></tr>"}
        </tbody>
      </table>
    </div>
    """

def normalize_action_plan_payload(parsed):
    """
    Acepta respuesta IA como:
      A) {"action_plan":[{...}]}
      B) {"plan":[{...}]}
      C) [{...}, {...}]   <-- lista directa (tu caso)
    Retorna SIEMPRE: {"action_plan":[{...}]}  (dict)
    Además normaliza llaves con acentos: acción->accion, propósito->proposito.
    """
    def _strip_accents_keys(d: dict) -> dict:
        if not isinstance(d, dict):
            return {}
        # mapa de llaves esperadas (acentos -> sin acentos)
        key_map = {
            "acción": "accion",
            "propósito": "proposito",
            "evidéncia": "evidencia",
            "responsáble": "responsable",
            "capítulo": "capitulo",
            "fase": "fase",
            "requisito": "requisito",
            "prioridad": "prioridad",
            "horizonte": "horizonte",
            "dependencia": "dependencia",
        }
        out = {}
        for k, v in d.items():
            kk = (k or "").strip()
            kk_low = kk.lower()
            kk_norm = key_map.get(kk_low, kk_low)

            # también soporta variantes comunes
            if kk_norm == "accion" or kk_norm == "acción":
                kk_norm = "accion"
            elif kk_norm == "proposito" or kk_norm == "propósito":
                kk_norm = "proposito"

            out[kk_norm] = v
        return out

    # 1) determinar lista de filas
    rows = None
    if isinstance(parsed, list):
        rows = parsed
    elif isinstance(parsed, dict):
        # varias llaves posibles
        rows = parsed.get("action_plan") or parsed.get("plan") or parsed.get("acciones")
        if rows is None:
            # a veces viene {"action_plan": {...}} malformado
            rows = []
    else:
        rows = []

    if not isinstance(rows, list):
        rows = []

    # 2) normalizar filas
    cleaned_rows = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        rr = _strip_accents_keys(r)

        cleaned_rows.append({
            # usa tus nombres esperados en UI
            "accion": harden_no_conditionals(to_text(rr.get("accion"))).strip(),
            "proposito": harden_no_conditionals(to_text(rr.get("proposito"))).strip(),
            "evidencia": harden_no_conditionals(to_text(rr.get("evidencia"))).strip(),
            "prioridad": (to_text(rr.get("prioridad")) or "").strip(),
            "horizonte": (to_text(rr.get("horizonte")) or "").strip(),
            "dependencia": harden_no_conditionals(to_text(rr.get("dependencia"))).strip(),
            "responsable": harden_no_conditionals(to_text(rr.get("responsable"))).strip(),
            "capitulo": (to_text(rr.get("capitulo")) or "").strip(),
            "fase": (to_text(rr.get("fase")) or "").strip(),
            "requisito": harden_no_conditionals(to_text(rr.get("requisito"))).strip(),
        })

    return {"action_plan": cleaned_rows}


 
# =========================
# Helper Evidencias SOA
# =========================

EVIDENCE_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx"}

def allowed_evidence_file(filename: str) -> bool:
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in EVIDENCE_EXTENSIONS
    )


# configuración del correo

def get_email_config():
    """
    Obtiene la configuración SMTP desde la base de datos (EmailConfig)
    o como fallback desde variables de entorno.
    """

    # 1️⃣ Intentar desde BD
    try:
        cfg = EmailConfig.query.first()
    except Exception:
        cfg = None

    if cfg:
        return {
            "SMTP_HOST": cfg.smtp_host,
            "SMTP_PORT": int(cfg.smtp_port or 587),
            "SMTP_USER": cfg.smtp_user,
            "SMTP_PASS": cfg.smtp_pass,
            "SMTP_FROM": cfg.smtp_from or cfg.smtp_user,
            "APP_NAME":  cfg.app_name or "SGSI",
        }

    # 2️⃣ Fallback a variables de entorno
    return {
        "SMTP_HOST": os.getenv("SMTP_HOST"),
        "SMTP_PORT": int(os.getenv("SMTP_PORT", "587")),
        "SMTP_USER": os.getenv("SMTP_USER"),
        "SMTP_PASS": os.getenv("SMTP_PASS"),
        "SMTP_FROM": os.getenv("SMTP_FROM"),
        "APP_NAME":  os.getenv("APP_NAME", "SGSI"),
    }

# Tipo de Riesgos

def gattr(obj, name):
    if name == "tipo_riesgo_nombre":
        tr = getattr(obj, "tipo_riesgo", None)
        return tr.nombre if tr else ""
    return getattr(obj, name, None)

# Metricas de Riesgos

RISK_ORDER = ["Bajo", "Moderado", "Alto", "Extremo"]  # orden oficial

def normalize_level(s: str) -> str:
    if s is None:
        return ""
    x = str(s).strip().lower()

    # quitar acentos simples
    x = (x.replace("á","a").replace("é","e").replace("í","i")
           .replace("ó","o").replace("ú","u"))

    # 1) si viene numérico (ej: "16", "20") interpreta como matriz prob*impacto
    if x.isdigit():
        v = int(x)
        if v <= 4:
            return "Bajo"
        elif v <= 9:
            return "Moderado"
        elif v <= 15:
            return "Alto"
        else:
            return "Extremo"

    # 2) sinónimos / variantes comunes
    if x in ["bajo", "low"]:
        return "Bajo"
    if x in ["medio", "moderado", "moderate", "medium"]:
        return "Moderado"
    if x in ["alto", "high"]:
        return "Alto"
    if x in ["Extremo", "extreme ", "severo", "several"]:
        return "Extremo"

    # 3) detección por contains
    if "crit" in x:
        return "Extremo"
    if "alt" in x:
        return "Alto"
    if "mod" in x or "med" in x:
        return "Moderado"
    if "baj" in x:
        return "Bajo"
    return ""

def safe_appetite_level(raw: str, default="Moderado") -> str:
    lvl = normalize_level(raw)
    return lvl if lvl in RISK_ORDER else default

def dominant_level(level_counts: dict) -> str:
    """
    Retorna el nivel dominante (el más frecuente).
    Si hay empate, gana el nivel MÁS alto (Extremo > Crítico > ...).
    """
    best_lvl = ""
    best_count = -1
    for lvl in RISK_ORDER:
        c = int(level_counts.get(lvl, 0) or 0)
        if c > best_count:
            best_count = c
            best_lvl = lvl
        elif c == best_count and c > 0:
            # empate: el más alto según RISK_ORDER
            if level_rank(lvl) > level_rank(best_lvl):
                best_lvl = lvl
    return best_lvl if best_count > 0 else ""

def build_trend_text_dominant(trend_rows):
    if not trend_rows:
        return {
            "inherente": "No hay datos con fecha para analizar tendencia.",
            "residual": "No hay datos con fecha para analizar tendencia.",
        }

    first = trend_rows[0]
    last = trend_rows[-1]

    inh_ini, inh_fin = first["inh_dominante"], last["inh_dominante"]
    res_ini, res_fin = first["res_dominante"], last["res_dominante"]

    def describe(start, end, label):
        if start == "Sin dato" or end == "Sin dato":
            return f"No hay suficiente información para determinar tendencia {label}."
        if start == end:
            return f"La criticidad dominante {label} se mantiene en **{start}**."
        # sube o baja según ranking
        if level_rank(end) > level_rank(start):
            return f"La criticidad dominante {label} **aumenta** de **{start}** a **{end}**."
        else:
            return f"La criticidad dominante {label} **disminuye** de **{start}** a **{end}**."

    return {
        "inherente": describe(inh_ini, inh_fin, "INHERENTE"),
        "residual": describe(res_ini, res_fin, "RESIDUAL"),
    }


def level_rank(level: str) -> int:
    lvl = normalize_level(level)
    if lvl in RISK_ORDER:
        return RISK_ORDER.index(lvl)
    return -1

def is_outside_appetite(residual_level: str, appetite_level: str) -> bool:
    """True si residual >= apetito (umbral)."""
    r = level_rank(residual_level)
    a = level_rank(appetite_level)
    if r < 0 or a < 0:
        return False
    return r >= a

def build_trend_text(trend_rows, order_levels):
    """
    Genera análisis en texto para Inherente y Residual por criticidad.
    Usa la primera y última fila disponible como comparación (inicio vs fin).
    """
    if not trend_rows:
        return {
            "inherente": "No hay datos con fecha para analizar tendencia.",
            "residual": "No hay datos con fecha para analizar tendencia.",
        }

    first = trend_rows[0]
    last = trend_rows[-1]

    def one_side(prefix: str) -> str:
        # prefix: "inh_" o "res_"
        lines = []
        total_first = 0
        total_last = 0

        deltas = []
        for lvl in order_levels:
            a = int(first.get(f"{prefix}{lvl}", 0) or 0)
            b = int(last.get(f"{prefix}{lvl}", 0) or 0)
            d = b - a
            total_first += a
            total_last += b
            deltas.append((lvl, a, b, d))

        # Resumen general
        if total_last > total_first:
            general = f"Aumenta el total ({total_first} → {total_last})."
        elif total_last < total_first:
            general = f"Disminuye el total ({total_first} → {total_last})."
        else:
            general = f"Se mantiene el total ({total_first} → {total_last})."

        # Cambios por criticidad
        changes = []
        for (lvl, a, b, d) in deltas:
            if d > 0:
                changes.append(f"{lvl}: +{d} ({a}→{b})")
            elif d < 0:
                changes.append(f"{lvl}: {d} ({a}→{b})")
            else:
                changes.append(f"{lvl}: 0 ({a}→{b})")

        # Encontrar mayor subida y mayor bajada
        max_up = max(deltas, key=lambda x: x[3])
        max_down = min(deltas, key=lambda x: x[3])

        extra = []
        if max_up[3] > 0:
            extra.append(f"Mayor aumento: {max_up[0]} (+{max_up[3]}).")
        if max_down[3] < 0:
            extra.append(f"Mayor reducción: {max_down[0]} ({max_down[3]}).")

        lines.append(general)
        lines.append("Cambios por criticidad: " + " · ".join(changes) + ".")
        if extra:
            lines.append(" ".join(extra))

        return " ".join(lines)

    return {
        "inherente": one_side("inh_"),
        "residual": one_side("res_"),
    }


def parse_any_date(s: str):
    """Parsea fechas típicas: YYYY-MM-DD, DD/MM/YYYY, etc. Retorna datetime o None."""
    if not s:
        return None
    s = str(s).strip()
    fmts = [
        "%Y-%m-%d", "%Y/%m/%d",
        "%d/%m/%Y", "%d-%m-%Y",
        "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S",
    ]
    # intento ISO
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except Exception:
            continue
    return None

def period_key(dt: datetime, tendencia: str) -> str:
    """Genera llave de periodo según tendencia."""
    y = dt.year
    m = dt.month
    tendencia = (tendencia or "mensual").lower()

    if tendencia == "mensual":
        return f"{y}-{m:02d}"
    if tendencia == "trimestral":
        q = (m - 1) // 3 + 1
        return f"{y}-T{q}"
    if tendencia == "cuatrimestral":
        c = (m - 1) // 4 + 1  # 1..3
        return f"{y}-C{c}"
    if tendencia == "semestral":
        s = 1 if m <= 6 else 2
        return f"{y}-S{s}"
    if tendencia == "anual":
        return f"{y}"

    # fallback
    return f"{y}-{m:02d}"

# mapa de divisiones por área

def divisiones_por_area():
    out = {}
    for a in AreaEmpresa.query.order_by(AreaEmpresa.area.asc(), AreaEmpresa.division.asc()).all():
        if not a.division:
            continue
        out.setdefault(a.id, [])
        if a.division not in out[a.id]:
            out[a.id].append(a.division)
    return out

def get_area_divisiones_map():
    """
    Devuelve un dict: { nombre_area: [división1, división2, ...] } (ordenadas)
    """
    filas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc(),
                                       AreaEmpresa.division.asc()).all()
    m = {}
    for f in filas:
        area = (f.area or "").strip()
        div  = (f.division or "").strip()
        if not area:
            continue
        m.setdefault(area, set())
        if div:
            m[area].add(div)
    # sets -> listas ordenadas
    return {k: sorted(v) for k, v in m.items()}


def get_areaid_divisiones_map():
    """
    Devuelve un dict: { area_id: [división1, división2, ...] } (ordenadas)
    Útil si tus selects usan area_id en lugar del nombre.
    """
    filas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc(),
                                       AreaEmpresa.division.asc()).all()
    m = {}
    for f in filas:
        div = (f.division or "").strip()
        m.setdefault(f.id, set())
        if div:
            m[f.id].add(div)
    return {k: sorted(v) for k, v in m.items()}

# para setear cálculos en servidor

    def calcular_criticidad(self):
        total = (self.valor_alcance or 0) + (self.valor_esencial or 0) + \
                (self.valor_plan_cont or 0) + (self.valor_alternativas or 0) + \
                (self.valor_plan_migracion or 0) + (self.valor_info_sensible or 0)
        self.criticidad_pct = total
        # Reglas pedidas:
        # >61 alta (rojo), >41 media (amarillo), >26 baja (verde oscuro), >1 muy baja (verde claro), si 0 -> muy baja
        if total > 61:
            self.criticidad_texto = "Criticidad alta"
            self.criticidad_color = "badge-rojo"
        elif total > 41:
            self.criticidad_texto = "Criticidad media"
            self.criticidad_color = "badge-amarillo"
        elif total > 26:
            self.criticidad_texto = "Criticidad baja"
            self.criticidad_color = "badge-verde-oscuro"
        elif total > 1:
            self.criticidad_texto = "Criticidad muy baja"
            self.criticidad_color = "badge-verde-claro"
        else:
            self.criticidad_texto = "Criticidad muy baja"
            self.criticidad_color = "badge-verde-claro"

    def calcular_certificados(self):
        # requiere_formulario: No si hay certificación, Sí si no hay
        self.requiere_formulario = "No" if (self.tiene_certificacion == "Sí") else "Sí"
        self.puntos_certificacion = 100 if (self.tiene_certificacion == "Sí") else 0
        if self.puntos_certificacion > 0:
            self.puntos_formulario = 0
        # total + resultado
        total = (self.puntos_certificacion or 0) + (self.puntos_formulario or 0)
        self.calificacion_total = total
        if total > 80:
            self.resultado_evaluacion = "Aprobado"
            self.resultado_color = "badge-aprobado"
        elif total > 60:
            self.resultado_evaluacion = "En revisión"
            self.resultado_color = "badge-revision"
        elif total > 0:
            self.resultado_evaluacion = "No Aprobado"
            self.resultado_color = "badge-noaprob"
        else:
            self.resultado_evaluacion = "No Aprobado"
            self.resultado_color = "badge-noaprob"
            
    def is_allowed_pdf(filename: str) -> bool:
        ext = os.path.splitext(filename.lower())[1]
    return ext in ALLOWED_PDF_EXT

    def unique_store_name(original: str) -> str:
        # evita colisiones y oculta nombres reales
        ext = os.path.splitext(original)[1].lower()
        return f"{uuid4().hex}{ext}"

    def obtener_cargos_desde_areas():
        cargos = set()
        for a in AreaEmpresa.query.all():
            # ajusta los nombres a tu modelo de Áreas
            if getattr(a, 'responsable_cargo', None):
                cargos.add(a.responsable_cargo)
            if getattr(a, 'division_cargo', None):
                cargos.add(a.division_cargo)
        lst = sorted(c for c in cargos if c)
        return lst or ['Analista','Coordinador','Jefe','Gerente']  # fallback

    def attribute(obj, name):
        return getattr(obj, name, None)


    
def extraer_respuestas_desde_excel(path_xlsx):
    """
    Lee el archivo Excel del cuestionario de proveedores y
    devuelve una lista de dicts con:
    - codigo
    - pregunta
    - cumplimiento
    - notas
    """
    xls = pd.ExcelFile(path_xlsx)

    # En tu plantilla el cuestionario está en la hoja "Requerimientos Aplicativos"
    df = xls.parse("Requerimientos Aplicativos", header=None)

    respuestas = []

    # A partir de la fila 36 empiezan las preguntas (según el archivo que subiste)
    # Columna B -> código (1.1, 1.2, etc.)
    # Columna C -> texto de la pregunta
    # Columna I -> Evidencias/Notas
    # Columna J -> Cumplimiento (lo que llenará el proveedor)
    for i in range(36, len(df)):
        cod = df.iloc[i, 1]
        txt = df.iloc[i, 2]

        # Si no hay código ni texto, saltamos
        if (pd.isna(cod) and pd.isna(txt)):
            continue

        # Saltar filas de títulos tipo "Sección 1", "Referencia", etc.
        cod_str = "" if pd.isna(cod) else str(cod).strip()
        txt_str = "" if pd.isna(txt) else str(txt).strip()

        if not txt_str:
            continue

        # Tomamos cumplimiento y notas
        notas = df.iloc[i, 8] if df.shape[1] > 8 else None
        cumpl = df.iloc[i, 9] if df.shape[1] > 9 else None

        notas_str = "" if pd.isna(notas) else str(notas).strip()
        cumpl_str = "" if pd.isna(cumpl) else str(cumpl).strip().upper()

        respuestas.append({
            "codigo": cod_str,
            "pregunta": txt_str,
            "cumplimiento": cumpl_str,
            "notas": notas_str
        })

    return respuestas

def chat_ai(prompt: str, model: str = None) -> str:
    """
    Mantiene la misma firma para no romper módulos existentes,
    pero usa el proveedor activo configurado en Administración.
    """
    ai_cfg = get_openrouter_client()
    provider = ai_cfg.get("provider")

    if provider == "ollama":
        base_url = ai_cfg.get("base_url", "").rstrip("/")
        ollama_model = ai_cfg.get("model") or get_ollama_model() or "llama3.1"

        if not base_url:
            raise RuntimeError("No existe OLLAMA_BASE_URL configurada en Administración.")
        if not ollama_model:
            raise RuntimeError("No existe OLLAMA_MODEL configurado en Administración.")

        resp = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": ollama_model,
                "prompt": f"Responde en español, claro y accionable.\n\n{prompt}",
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            },
            timeout=300
        )
        resp.raise_for_status()

        data = resp.json() or {}
        return (data.get("response") or "").strip()

    # OpenRouter
    client = ai_cfg["client"]
    model_name = model or ai_cfg.get("model") or OPENROUTER_MODEL or "deepseek/deepseek-chat"

    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "Responde en español, claro y accionable."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return (resp.choices[0].message.content or "").strip()


# =========================
# Inserta todos los controles si la tabla está vacía
# =========================

def populate_if_needed():
    # Insertar controles iniciales si la tabla está vacía
    if Control.query.first() is None:
        for item in FULL_SOA:
            db.session.add(Control(**item))
        db.session.commit()

    # Crear la tabla de registro de incidentes directamente en SQLite
    conn = sqlite3.connect('sgsi.db')
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS registro_incidentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion_corta TEXT,
            causa TEXT,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            estado_actual TEXT,
            datos_personales_involucrados TEXT,
            violacion_datos_personales TEXT,
            medidas_tomadas TEXT,
            enlace_informe_interno TEXT,
            medidas_prevencion TEXT
        )
    """)
    conn.commit()
    conn.close()


def create_admin():
    if not User.query.filter_by(username='Administrador').first():
        admin = User(username='Administrador', role='admin')
        admin.set_password('Abcd12345%')
        db.session.add(admin)
        db.session.commit()


# =========================
# Inicialización de BD al arrancar (compatible con Flask 3.x)
# =========================

with app.app_context():
    db.create_all()
    populate_if_needed()
    create_admin()


# =========================
# Export CSV (descargar todo)
# =========================

@app.route('/export')
def export_csv():
    controls = Control.query.order_by(Control.nr).all()
    si = io.StringIO()
    fieldnames = ['nr','chapter','topic','control_text','applicable','justification','motivation','implemented']
    writer = csv.DictWriter(si, fieldnames=fieldnames)
    writer.writeheader()
    for c in controls:
        writer.writerow(c.to_dict())
    mem = io.BytesIO()
    mem.write(si.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name='soa_iso27001_export.csv', mimetype='text/csv')

# =========================
# Ruta para descargar via send_file necesita BytesIO importado
# =========================

from io import BytesIO as _BytesIO
def io_BytesIO(b): return _BytesIO(b)

# =========================
# Ajuste para send_file con BytesIO: re-definimos send_file wrapper
# =========================
from flask import Response
@app.route('/export_alt')
def export_csv_alt():
    controls = Control.query.order_by(Control.nr).all()
    si = io.StringIO()
    fieldnames = ['nr','chapter','topic','control_text','applicable','justification','motivation','implemented']
    writer = csv.DictWriter(si, fieldnames=fieldnames)
    writer.writeheader()
    for c in controls:
        writer.writerow(c.to_dict())
    data = si.getvalue().encode('utf-8')
    return Response(data, mimetype='text/csv', headers={'Content-Disposition':'attachment;filename=soa_iso27001_export.csv'})

# =========================
# Atajo: /export redirige a /export_alt si send_file falla
# =========================
@app.route('/export')
def export_csv_redirect():
    return export_csv_alt()

# =========================
# Manejador de errores simple
# =========================
@app.errorhandler(Exception)
def handle_all_errors(e):
    # si es un error HTTP normal (404, 403, etc.), respétalo
    if isinstance(e, HTTPException):
        return e

    tb = traceback.format_exc()
    html = f"""
    <div class="alert alert-danger">
      <h5 class="mb-2">Error interno real (traceback)</h5>
      <pre style="white-space:pre-wrap; font-size:12px; max-height:520px; overflow:auto;">{tb}</pre>
    </div>
    """
    return render_template_string(BASE, content=html), 500

# =========================
# Persona Empresas
# =========================
def get_personas_empresa():
    try:
        return EmpresaPersona.query.order_by(EmpresaPersona.nombre.asc()).all()
    except Exception:
        return []


# ============================================================================================================================================
#                                                               Autenticación de Usuarios
# ============================================================================================================================================

from functools import wraps
from flask import (
    render_template_string,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_file
)

import pyotp
import qrcode
import io
import base64

from io import BytesIO


# =========================
# DECORADOR DE LOGIN
# =========================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Por favor, inicia sesión.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = User.query.get(session.get('user_id'))

        if not user or user.role != 'admin':
            flash("Acceso solo permitido a administradores.", "danger")
            return redirect(url_for('menu'))

        return f(*args, **kwargs)

    return wrapper


def admin_or_access_manager_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = User.query.get(session.get('user_id'))

        if not user or user.role not in ('admin', 'gestor_accesos'):
            flash(
                "Acceso solo permitido a administradores o gestores de accesos.",
                "danger"
            )
            return redirect(url_for('menu'))

        return f(*args, **kwargs)

    return wrapper


def verify_otp(user, otp_code):
    if not user or not user.otp_secret:
        return False

    totp = pyotp.TOTP(user.otp_secret)
    return totp.verify(otp_code)


# ============================================================================================================================================
#                                                           RENDER QR OTP
# ============================================================================================================================================
def _render_qr_otp_setup(user, secret):

    otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.username,
        issuer_name="SGSI"
    )

    qr = qrcode.make(otp_uri)

    buffer = io.BytesIO()

    qr.save(buffer, format="PNG")

    qr_data = base64.b64encode(buffer.getvalue()).decode()

    content = f"""
    <div class="col-md-6 offset-md-3 text-center">

        <h3>Configuración de Autenticación en Dos Pasos</h3>

        <div class="alert alert-info">
            Escanea este código QR con Google Authenticator,
            Microsoft Authenticator o Authy.
            Luego ingresa el código de 6 dígitos para activar el token.
        </div>

        <img src="data:image/png;base64,{qr_data}"
             class="img-fluid mb-3"
             alt="QR Code"
             style="max-width:260px;">

        <form method="post"
              action="{url_for('verificar_otp')}"
              autocomplete="off"
              autocorrect="off"
              autocapitalize="none"
              spellcheck="false">

            <input type="hidden" name="username" value="{user.username}">
            <input type="hidden" name="modo" value="setup">

            <div class="mt-3 mb-3">
                <label class="form-label fw-bold">
                    Código de Verificación
                </label>

                <input class="form-control text-center"
                       name="otp"
                       type="password"
                       inputmode="numeric"
                       pattern="[0-9]{{6}}"
                       maxlength="6"
                       placeholder="••••••"
                       required
                       autocomplete="off"
                       autocorrect="off"
                       autocapitalize="none"
                       spellcheck="false">
            </div>

            <button class="btn btn-success rounded-pill px-4">
                Activar token
            </button>

            <a href="{url_for('login')}"
               class="btn btn-secondary rounded-pill px-4">
                Cancelar
            </a>

        </form>
    </div>
    """

    return render_template_string(BASE, content=content)


# ============================================================================================================================================
#                                                               LOGIN
# ============================================================================================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username_ingresado = (
            request.form.get('sgsi_user_secure') or
            ""
        ).strip()

        password_ingresado = (
            request.form.get('sgsi_password_secure') or
            ""
        )

        user = User.query.filter_by(
            username=username_ingresado
        ).first()

        # ============================================================
        # LOGIN CORRECTO
        # ============================================================
        if user and user.check_password(password_ingresado):

            # =====================================================
            # USUARIO SIN OTP CONFIGURADO
            # =====================================================
            if not user.otp_secret:

                secret_temporal = pyotp.random_base32()

                session['temp_user'] = user.username
                session['pending_otp_secret'] = secret_temporal

                return _render_qr_otp_setup(
                    user,
                    secret_temporal
                )

            # =====================================================
            # USUARIO YA TIENE OTP
            # =====================================================
            session['temp_user'] = user.username

            session.pop(
                'pending_otp_secret',
                None
            )

            return redirect(
                url_for('verificar_otp')
            )

        # ============================================================
        # LOGIN FALLIDO
        # ============================================================
        registrar_log(
            username_ingresado or "Desconocido",
            (
                "Acceso fallido al sistema. "
                f"Usuario o contraseña inválida: "
                f"{username_ingresado or 'Desconocido'}"
            )
        )

        flash(
            "Usuario o contraseña incorrectos.",
            "danger"
        )

    # ====================================================================
    # HTML LOGIN
    # ====================================================================
    content = """
    <style>

      input::-ms-reveal,
      input::-ms-clear{
        display:none;
      }

      input[type="password"]::-webkit-credentials-auto-fill-button,
      input[type="password"]::-webkit-textfield-decoration-container{
        display:none !important;
        visibility:hidden;
        pointer-events:none;
      }

      .login-card{
        background:#ffffff;
        border-radius:24px;
        padding:32px;
        box-shadow:0 10px 30px rgba(15,23,42,.08);
      }

      .login-title{
        font-size:2rem;
        font-weight:900;
        text-align:center;
        margin-bottom:24px;
        color:#1e293b;
      }

      .login-label{
        font-weight:800;
        margin-bottom:8px;
        color:#334155;
      }

      .login-input{
        height:52px;
        border-radius:14px;
        border:1px solid #dbe2ea;
        font-size:1rem;
        padding-left:14px;
        transition:.2s ease;
      }

      .login-input:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.15);
      }

      .login-btn{
        height:52px;
        border-radius:14px;
        font-weight:900;
        font-size:1rem;
        background:#3f86d6;
        border:none;
      }

      .login-btn:hover{
        background:#2f6fb6;
      }

    </style>

    <div class="col-md-4 offset-md-4">

      <div class="login-card">

        <div class="login-title">
          Iniciar sesión
        </div>

        <form method="post"
              id="sgsiLoginForm"
              autocomplete="off"
              autocorrect="off"
              autocapitalize="none"
              spellcheck="false">

            <!-- CAMPOS TRAMPA -->
            <input type="text"
                   style="display:none"
                   tabindex="-1"
                   autocomplete="off">

            <input type="password"
                   style="display:none"
                   tabindex="-1"
                   autocomplete="new-password">

            <!-- USUARIO -->
            <div class="mb-3">

              <label class="login-label">
                Usuario
              </label>

              <input class="form-control login-input"
                     id="sgsi_user_secure"
                     name="sgsi_user_secure"
                     type="text"
                     required

                     autocomplete="off"
                     autocorrect="off"
                     autocapitalize="none"
                     spellcheck="false"

                     data-form-type="other"

                     readonly
                     onfocus="this.removeAttribute('readonly');"

                     placeholder="Digite su usuario">

            </div>

            <!-- PASSWORD -->
            <div class="mb-4">

              <label class="login-label">
                Contraseña
              </label>

              <input class="form-control login-input"
                     id="sgsi_password_secure"
                     name="sgsi_password_secure"
                     type="password"
                     required

                     autocomplete="off"
                     autocorrect="off"
                     autocapitalize="none"
                     spellcheck="false"

                     data-form-type="other"
                     data-lpignore="true"

                     readonly
                     onfocus="this.removeAttribute('readonly');"

                     placeholder="••••••••">

            </div>

            <button class="btn btn-primary w-100 login-btn">
              Ingresar
            </button>

        </form>

      </div>

    </div>

    <script>

    document.addEventListener('DOMContentLoaded', function(){

        const form = document.getElementById('sgsiLoginForm');

        const user = document.getElementById('sgsi_user_secure');

        const pass = document.getElementById('sgsi_password_secure');

        // LIMPIAR AUTOFILL
        if(user){
            user.value = '';

            setTimeout(function(){
                user.value = '';
            }, 100);
        }

        if(pass){
            pass.value = '';

            setTimeout(function(){
                pass.value = '';
            }, 100);
        }

        // BLOQUEAR DETECCIÓN DE LOGIN
        if(form){

            form.setAttribute(
                'autocomplete',
                'off'
            );

            form.addEventListener(
                'submit',
                function(){

                    user.setAttribute(
                        'autocomplete',
                        'off'
                    );

                    pass.setAttribute(
                        'autocomplete',
                        'new-password'
                    );

                }
            );

        }

        // DESBLOQUEAR READONLY AL HACER FOCUS
        [user, pass].forEach(function(el){

            if(!el) return;

            el.addEventListener('focus', function(){

                this.removeAttribute(
                    'readonly'
                );

                this.setAttribute(
                    'autocomplete',
                    'off'
                );

            });

        });

    });

    </script>
    """

    return render_template_string(
        BASE,
        content=content
    )


# ============================================================================================================================================
#                                                               OTP
# ============================================================================================================================================
@app.route('/verificar_otp', methods=['GET', 'POST'])
def verificar_otp():

    username = session.get('temp_user')

    if not username:
        flash(
            "Primero inicia sesión.",
            "warning"
        )

        return redirect(
            url_for('login')
        )

    user = User.query.filter_by(
        username=username
    ).first()

    if not user:

        session.pop('temp_user', None)

        session.pop(
            'pending_otp_secret',
            None
        )

        registrar_log(
            username or "Desconocido",
            (
                "Acceso fallido al sistema. "
                "Usuario no encontrado "
                f"en verificación OTP: "
                f"{username or 'Desconocido'}"
            )
        )

        flash(
            "Usuario no encontrado.",
            "danger"
        )

        return redirect(
            url_for('login')
        )

    if request.method == 'POST':

        otp = (
            request.form.get('otp') or ""
        ).strip()

        modo = (
            request.form.get('modo') or ""
        ).strip()

        # =====================================================
        # CONFIGURACIÓN INICIAL OTP
        # =====================================================
        if modo == "setup":

            secret_temporal = session.get(
                'pending_otp_secret'
            )

            if not secret_temporal:

                flash(
                    "La configuración del token expiró. "
                    "Inicia sesión nuevamente.",
                    "warning"
                )

                return redirect(
                    url_for('login')
                )

            totp = pyotp.TOTP(
                secret_temporal
            )

            if totp.verify(otp):

                user.otp_secret = secret_temporal

                db.session.commit()

                session['user_id'] = user.id
                session['username'] = user.username
                session['role'] = user.role

                session.pop(
                    'temp_user',
                    None
                )

                session.pop(
                    'pending_otp_secret',
                    None
                )

                registrar_log(
                    user.username,
                    (
                        "Acceso exitoso al sistema. "
                        "Token OTP configurado "
                        f"y usuario autenticado "
                        f"con perfil: {user.role}"
                    )
                )

                flash(
                    f"Token configurado correctamente. "
                    f"Bienvenido {user.username}",
                    "success"
                )

                return redirect(
                    url_for('menu')
                )

            registrar_log(
                user.username,
                (
                    "Configuración OTP fallida. "
                    f"Código inválido para "
                    f"el usuario: {user.username}"
                )
            )

            flash(
                "Código OTP inválido. "
                "Escanea el QR e intenta nuevamente.",
                "danger"
            )

            return _render_qr_otp_setup(
                user,
                secret_temporal
            )

        # =====================================================
        # LOGIN NORMAL OTP
        # =====================================================
        if not user.otp_secret:

            flash(
                "Este usuario aún no tiene "
                "token configurado. "
                "Inicia sesión nuevamente.",
                "warning"
            )

            return redirect(
                url_for('login')
            )

        totp = pyotp.TOTP(
            user.otp_secret
        )

        if totp.verify(otp):

            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role

            session.pop(
                'temp_user',
                None
            )

            session.pop(
                'pending_otp_secret',
                None
            )

            registrar_log(
                user.username,
                (
                    "Acceso exitoso al sistema. "
                    "Usuario autenticado "
                    f"correctamente con perfil: "
                    f"{user.role}"
                )
            )

            flash(
                f"Bienvenido {user.username}",
                "success"
            )

            return redirect(
                url_for('menu')
            )

        registrar_log(
            user.username,
            (
                "Acceso fallido al sistema. "
                f"OTP inválido para el usuario: "
                f"{user.username}"
            )
        )

        flash(
            "Código OTP inválido, intente de nuevo.",
            "danger"
        )

    # ====================================================================
    # HTML OTP
    # ====================================================================
    content = f"""
    <div class="col-md-4 offset-md-4 text-center">

      <h3>Verificación de Código OTP</h3>

      <form method="post"
            autocomplete="off"
            autocorrect="off"
            autocapitalize="none"
            spellcheck="false">

        <input type="hidden"
               name="username"
               value="{user.username}">

        <div class="mb-3">

          <label>
            Código OTP
          </label>

          <input class="form-control text-center"
                 name="otp"
                 type="password"
                 inputmode="numeric"
                 pattern="[0-9]{{6}}"
                 maxlength="6"
                 placeholder="••••••"
                 required
                 autocomplete="off"
                 autocorrect="off"
                 autocapitalize="none"
                 spellcheck="false">

        </div>

        <button class="btn btn-success rounded-pill px-4">
          Verificar
        </button>

        <a href="{url_for('login')}"
           class="btn btn-secondary rounded-pill px-4">
          Cancelar
        </a>

      </form>

    </div>
    """

    return render_template_string(
        BASE,
        content=content
    )


# ============================================================================================================================================
#                                                           GENERAR OTP
# ============================================================================================================================================
@app.route('/generar_otp/<username>')
def generar_otp(username):

    user = User.query.filter_by(
        username=username
    ).first()

    if not user:
        return "Usuario no encontrado", 404

    secret = (
        user.otp_secret or
        session.get('pending_otp_secret') or
        pyotp.random_base32()
    )

    session['temp_user'] = user.username

    session['pending_otp_secret'] = secret

    otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name="Sistema ISO27001"
    )

    img = qrcode.make(otp_uri)

    buffer = BytesIO()

    img.save(buffer, format="PNG")

    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='image/png'
    )


# ============================================================================================================================================
#                                                               LOGOUT
# ============================================================================================================================================
@app.route('/logout')
def logout():

    try:
        _browser_session_revoke()
    except Exception as exc:
        print("No se pudo revocar la sesión al cerrar manualmente:", repr(exc))

    session.clear()

    flash(
        "Sesión finalizada",
        "info"
    )

    return redirect(
        url_for('login')
    )


# ============================================================================================================================================
#                                                   Fin módulo de Autenticación
# ============================================================================================================================================

# ============================================================================================================================================
#                                                                   Módulo de Perfil
# ============================================================================================================================================

@app.context_processor
def inject_user():
    u = None
    if 'user_id' in session:
        u = User.query.get(session.get('user_id'))
    return dict(current_user=u)

@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    user = User.query.get(session.get("user_id"))

    if request.method == "POST":
        accion = request.form.get("accion")

        # ============================
        # A) Subir foto
        # ============================
        if accion == "subir_foto":
            f = request.files.get("foto")
            if not f or f.filename == "":
                flash("Selecciona una imagen.", "warning")
                return redirect(url_for("perfil"))

            if not allowed_file(f.filename):
                flash("Formato no permitido. Usa PNG/JPG/JPEG/WEBP.", "danger")
                return redirect(url_for("perfil"))

            ext = f.filename.rsplit(".", 1)[1].lower()
            filename = secure_filename(f"{uuid4().hex}.{ext}")
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            f.save(path)

            # (Opcional) borrar foto anterior
            if user.photo_filename:
                old_path = os.path.join(app.config["UPLOAD_FOLDER"], user.photo_filename)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except:
                        pass

            user.photo_filename = filename
            db.session.commit()
            flash("Foto actualizada.", "success")
            return redirect(url_for("perfil"))

        # ============================
        # B) Cambiar contraseña
        # ============================
        if accion == "cambiar_password":
            actual = request.form.get("password_actual") or ""
            nueva = request.form.get("password_nueva") or ""
            confirma = request.form.get("password_confirma") or ""

            if not user.check_password(actual):
                flash("La contraseña actual no es correcta.", "danger")
                return redirect(url_for("perfil"))

            if len(nueva) < 10:
                flash("La nueva contraseña debe tener mínimo 10 caracteres.", "warning")
                return redirect(url_for("perfil"))

            # regla mínima: 1 mayúscula + 1 especial
            especiales = set("!@#$%^&*()-_=+[]{};:,.?/\\|`~")
            if not any(c.isupper() for c in nueva):
                flash("La nueva contraseña debe incluir al menos 1 mayúscula.", "warning")
                return redirect(url_for("perfil"))
            if not any(c in especiales for c in nueva):
                flash("La nueva contraseña debe incluir al menos 1 caracter especial.", "warning")
                return redirect(url_for("perfil"))

            if nueva != confirma:
                flash("La confirmación no coincide.", "warning")
                return redirect(url_for("perfil"))

            user.set_password(nueva)
            db.session.commit()
            flash("Contraseña cambiada correctamente.", "success")
            return redirect(url_for("perfil"))

    # URL de avatar
    avatar_url = (
        url_for("static", filename=f"uploads/profiles/{user.photo_filename}")
        if user.photo_filename
        else url_for("static", filename="img/default_user.png")  # crea esta imagen
    )

    inner = render_template_string("""
    <div class="perfil-shell">

      <!-- HEADER SGSI -->
      <div class="perfil-header-card">
        <div class="perfil-header-overlay">
          <div class="perfil-header-text">
            <h3 class="perfil-title m-0">Perfil de usuario</h3>
            <div class="perfil-subtitle">
              Administra tu foto de perfil y actualiza tu contraseña de acceso
            </div>
          </div>
        </div>
      </div>

      <div class="perfil-card">
        <div class="card-body">

          <!-- DATOS USUARIO -->
          <div class="perfil-section-title">Información del usuario</div>

          <div class="perfil-user-box mb-4">
            <img src="{{ avatar_url }}" alt="Foto" class="perfil-avatar">

            <div class="perfil-user-info">
              <div class="perfil-user-name">👤 {{ user.username }}</div>
              <div class="perfil-user-meta">Rol: <b>{{ user.role }}</b></div>
              {% if user.email %}
                <div class="perfil-user-meta">Correo: <b>{{ user.email }}</b></div>
              {% endif %}
            </div>
          </div>

          <!-- FOTO -->
          <div class="perfil-section-title">🖼️ Cambiar foto</div>

          <form method="POST" enctype="multipart/form-data" class="mb-4">
            <input type="hidden" name="accion" value="subir_foto">

            <div class="row g-3 align-items-end">
              <div class="col-md-8">
                <label class="form-label fw-semibold">Seleccionar imagen</label>
                <input type="file" name="foto" class="form-control" accept="image/*" required>
              </div>
              <div class="col-md-4 text-md-end">
                <button class="btn btn-primary rounded-pill px-4 fw-semibold">Subir foto</button>
              </div>
            </div>
          </form>

          <!-- CONTRASEÑA -->
          <div class="perfil-section-title">🔑 Cambiar contraseña</div>

          <form method="POST">
            <input type="hidden" name="accion" value="cambiar_password">

            <div class="row g-3">
              <div class="col-md-4">
                <label class="form-label fw-semibold">Contraseña actual</label>
                <input type="password" name="password_actual" class="form-control" required>
              </div>

              <div class="col-md-4">
                <label class="form-label fw-semibold">Nueva contraseña</label>
                <input type="password" name="password_nueva" class="form-control" required>
                <div class="text-muted small mt-1">Mínimo 10 caracteres, 1 mayúscula y 1 carácter especial</div>
              </div>

              <div class="col-md-4">
                <label class="form-label fw-semibold">Confirmar contraseña</label>
                <input type="password" name="password_confirma" class="form-control" required>
              </div>
            </div>

            <div class="text-center text-md-start">
              <button class="btn btn-success rounded-pill px-4 fw-semibold mt-4">Guardar contraseña</button>
            </div>
          </form>

        </div>
      </div>
    </div>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .perfil-shell{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
      }

      .perfil-header-card{
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
      }

      .perfil-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .perfil-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }

      .perfil-header-overlay::before{
        content:"👤";
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
      }

      .perfil-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .perfil-header-text::before{
        content:"SGSI · Perfil de Usuario";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .perfil-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .perfil-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        font-weight:800;
      }

      .perfil-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .perfil-header-actions .btn,
      .perfil-btn-main,
      .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .perfil-btn-main{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }

      .perfil-btn-main:hover{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }

      .perfil-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .perfil-card .card-body{
        padding:22px;
      }

      .perfil-section-title,
      .card h5,
      .card h6{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
        margin-bottom:16px;
      }

      .perfil-user-box{
        display:flex;
        align-items:center;
        gap:18px;
        background:#f8fbff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:16px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .perfil-avatar{
        width:78px;
        height:78px;
        border-radius:50%;
        object-fit:cover;
        border:3px solid #0b4a8f;
        box-shadow:0 6px 16px rgba(0,0,0,.12);
        flex:0 0 auto;
      }

      .perfil-user-info{
        min-width:0;
      }

      .perfil-user-name{
        font-size:1.05rem;
        font-weight:950;
        color:#101827;
        line-height:1.2;
        margin-bottom:4px;
      }

      .perfil-user-meta{
        color:#607086;
        font-size:.90rem;
        line-height:1.35;
        font-weight:700;
      }

      .form-label{
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
      }

      .form-control,
      .form-select{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }

      .form-control:focus,
      .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      @media (max-width:992px){
        .perfil-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .perfil-header-card{
          min-height:88px;
        }

        .perfil-title{
          font-size:1.20rem;
        }

        .perfil-subtitle{
          font-size:.68rem;
        }

        .perfil-card .card-body{
          padding:16px;
        }

        .perfil-user-box{
          flex-direction:column;
          align-items:flex-start;
          text-align:left;
        }
      }

      @media (max-width:768px){
        .perfil-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .perfil-header-overlay::before{
          margin:0;
        }

        .perfil-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .perfil-title,
        .perfil-subtitle{
          text-align:center;
        }

        .perfil-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, user=user, avatar_url=avatar_url)

    return render_template_string(BASE, content=Markup(inner))


# ============================================================================================================================================
#                                                                   Fin del módulo de Perfil
# ============================================================================================================================================

# ============================================================================================================================================
#                                                               Módulo de envio del password
# ============================================================================================================================================

def enviar_credenciales_email(destino, username, password, nombre_completo=None):
    cfg = get_email_config()

    SMTP_HOST = cfg.get("SMTP_HOST")
    SMTP_PORT = int(cfg.get("SMTP_PORT") or 465)
    SMTP_USER = cfg.get("SMTP_USER")
    SMTP_PASS = cfg.get("SMTP_PASS")
    SMTP_FROM = cfg.get("SMTP_FROM") or SMTP_USER
    APP_NAME  = cfg.get("APP_NAME") or "SGSI"

    if not SMTP_HOST:
        raise RuntimeError("Falta SMTP_HOST en la configuración.")
    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("Faltan credenciales SMTP (SMTP_USER/SMTP_PASS).")
    if not destino:
        raise RuntimeError("Correo destino vacío.")

    nombre_saludo = (nombre_completo or username or "").strip()

    msg = EmailMessage()
    msg["Subject"] = f"Credenciales de acceso - {APP_NAME}"
    msg["From"] = SMTP_FROM
    msg["To"] = destino
    msg.set_content(
        f"""Hola {nombre_saludo},

Se ha creado tu usuario en {APP_NAME}.

Usuario: {username}
Contraseña temporal: {password}

Por seguridad, cambia tu contraseña al ingresar.

Saludos,
{APP_NAME}
"""
    )

    context_ssl = ssl._create_unverified_context()

    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context_ssl, timeout=30) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context_ssl)
            smtp.ehlo()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)

# ============================================================================================================================================
#                                                               Fin módulo de envio del password
# ============================================================================================================================================


# ============================================================================================================================================
#                                                               Generar Password Seguro
# ============================================================================================================================================

def generar_password_seguro(longitud=10):
    if longitud < 10:
        raise ValueError("La contraseña debe tener mínimo 10 caracteres")

    mayuscula = secrets.choice(string.ascii_uppercase)
    minuscula = secrets.choice(string.ascii_lowercase)
    digito = secrets.choice(string.digits)
    especial = secrets.choice("!@#$%&*_-+=?")

    resto = ''.join(
        secrets.choice(
            string.ascii_letters + string.digits + "!@#$%&*_-+=?"
        )
        for _ in range(longitud - 4)
    )

    # Mezclar todo
    password_lista = list(mayuscula + minuscula + digito + especial + resto)
    secrets.SystemRandom().shuffle(password_lista)

    return ''.join(password_lista)


# ============================================================================================================================================
#                                                               Fin Generar Password Seguro
# ============================================================================================================================================


# ============================================================================================================================================
#                                                               Módulo de Gestión de Usuarios
# ============================================================================================================================================

MODULES = [
    "Análisis de Riesgos de Procesos con IA",
    "Declaración de Aplicabilidad",
    "Gestión de Riesgos",
    "Objetivos del Sistema de Gestión",
    "Planes de acción del SGSI",
    "Listado Maestro de Documentos",
    "Gestión de Activos de Información",
    "Inventario de Software",
    "Inventario de IA",
    "Inventario de Información",
    "Inventario de Datos Personales",
    "Inventario Físico",
    "Tablas de Valoración",
    "Dueños de Información",
    "Registro de Incidentes",
    "Planes de Respuesta a Incidentes",
    "Centro de Alertas",
    "Configuración Parámetros de la Empresa",
    "Gestión de Cambios (RFC)",
    "Registro de Proveedores",
    "Registro de Comunicaciones",
    "Plan de Concientización y Formación",
    "Seguimiento del Plan de Formación",
    "Campañas de Concientización",
    "Requisitos Legales",
    "Partes Interesadas",
    "Registro de Vulnerabilidades",
    "Pruebas SAST",
    "Modelamiento de Amenazas",
    "Superficie de Ataque y Escenarios",
    "Plan de Remediación",
    "Plan de Competencias",
    "Contexto Interno",
    "Contexto Externo",
    "DOFA",
    "PESI",
    "Informe Revisión por la Dirección",
    "Gestión de Accesos",
    "Continuidad del Negocio (BCP/DRP)",
    "Revisión de Accesos",
    "Cuestionarios de Proponentes",
    "Cuestionario de proveedores web",
    "Listas Restrictivas",
    "Security Scorecard de Terceros",
    "Nivel de madurez ISO 27001:2022",
    "Nivel de Madurez NIST CSF V.2.0",
    "Nivel de Madurez protección de datos personales",
    "Nivel de Madurez PCI-DSS",
    "Nivel de madurez SOC 2",
    "Nivel de Madurez ISO 22301",
    "Nivel de Madurez Gestión de Inteligencia Artificial",
    "Modelamiento de Amenazas",
    "Cumplimiento Continuo",
    "Métricas",
    "Reportes",
    "Logs de Auditoría",
    "Aplicación móvil",
]


# ============================================================
# DB ALTERNA PARA PERFIL DE USUARIOS
# NO MODIFICA LA TABLA user NI sgsi.db
# ============================================================

USUARIOS_PERFIL_DB_PATH = os.path.join(app.instance_path, "usuarios_perfil.db")


def get_usuarios_perfil_db_connection():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(USUARIOS_PERFIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_usuarios_perfil_db():
    conn = get_usuarios_perfil_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios_perfil (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            nombre_completo TEXT,
            fecha_creacion TEXT,
            fecha_actualizacion TEXT
        )
    """)

    conn.commit()
    conn.close()


def obtener_nombre_usuario_alterno(user_id):
    init_usuarios_perfil_db()

    conn = get_usuarios_perfil_db_connection()
    row = conn.execute("""
        SELECT nombre_completo
        FROM usuarios_perfil
        WHERE user_id = ?
    """, (user_id,)).fetchone()
    conn.close()

    return (row["nombre_completo"] if row else "") or ""


def guardar_nombre_usuario_alterno(user_id, nombre_completo):
    init_usuarios_perfil_db()

    nombre_completo = (nombre_completo or "").strip()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_usuarios_perfil_db_connection()
    cur = conn.cursor()

    existe = cur.execute("""
        SELECT id
        FROM usuarios_perfil
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    if existe:
        cur.execute("""
            UPDATE usuarios_perfil
            SET nombre_completo = ?,
                fecha_actualizacion = ?
            WHERE user_id = ?
        """, (nombre_completo, ahora, user_id))
    else:
        cur.execute("""
            INSERT INTO usuarios_perfil (
                user_id,
                nombre_completo,
                fecha_creacion,
                fecha_actualizacion
            )
            VALUES (?, ?, ?, ?)
        """, (user_id, nombre_completo, ahora, ahora))

    conn.commit()
    conn.close()


def eliminar_nombre_usuario_alterno(user_id):
    init_usuarios_perfil_db()

    conn = get_usuarios_perfil_db_connection()
    conn.execute("""
        DELETE FROM usuarios_perfil
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()


def cargar_perfiles_usuarios_alternos():
    init_usuarios_perfil_db()

    conn = get_usuarios_perfil_db_connection()
    rows = conn.execute("""
        SELECT user_id, nombre_completo
        FROM usuarios_perfil
    """).fetchall()
    conn.close()

    return {
        int(r["user_id"]): (r["nombre_completo"] or "")
        for r in rows
    }


init_usuarios_perfil_db()


@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
def usuarios():
    user = User.query.get(session.get('user_id'))

    if (
        user.role != 'admin'
        and user.role != 'gestor_accesos'
        and not verificar_permiso(user, "Gestión de Usuarios")
    ):
        registrar_log(
            user.username if user else "Desconocido",
            "Intento de acceso no autorizado al módulo Gestión de Usuarios."
        )
        flash("No tiene acceso para este módulo.", "danger")
        return redirect(url_for('menu'))

    usuario_actual = User.query.get(session.get('user_id'))
    es_admin = usuario_actual.role == 'admin'
    es_gestor = usuario_actual.role == 'gestor_accesos'

    accion = None

    if request.method == 'POST':
        accion = request.form.get('accion')

        # ======================
        # CREAR
        # ======================
        if accion == 'crear':
            nombre_completo = (request.form.get('nombre_completo') or "").strip()
            role_nuevo = request.form.get('role') or 'user'
            username = (request.form.get('username') or "").strip()
            email = (request.form.get('email') or "").strip().lower()

            if not username or not email:
                flash("Usuario y correo son obligatorios.", "warning")
                return redirect(url_for('usuarios'))

            if User.query.filter_by(username=username).first():
                flash("Ya existe un usuario con ese nombre.", "danger")
                return redirect(url_for('usuarios'))

            if User.query.filter_by(email=email).first():
                flash("Ya existe un usuario con ese correo.", "danger")
                return redirect(url_for('usuarios'))

            password_auto = generar_password_seguro(10)

            u = User(username=username, email=email, role=role_nuevo)
            u.set_password(password_auto)
            db.session.add(u)
            db.session.commit()

            guardar_nombre_usuario_alterno(u.id, nombre_completo)

            registrar_log(
                usuario_actual.username,
                f"Creación de usuario. Usuario creado: {username}. Perfil asignado: {role_nuevo}."
            )

            try:
                nombre_para_correo = obtener_nombre_usuario_alterno(u.id) or username
                enviar_credenciales_email(email, username, password_auto, nombre_para_correo)
                flash("Usuario creado y contraseña enviada al correo.", "success")
            except Exception as e:
                print("Error enviando correo:", repr(e))
                flash(f"Usuario creado, pero falló el envío de correo: {e}", "warning")

        # ======================
        # EDITAR
        # ======================
        elif accion == 'editar' and (es_admin or es_gestor):
            u = User.query.get(int(request.form['id']))

            if not u:
                flash("Usuario no encontrado.", "danger")
                return redirect(url_for('usuarios'))

            username_anterior = u.username or ""
            email_anterior = u.email or ""
            rol_anterior = u.role or ""
            nombre_anterior = obtener_nombre_usuario_alterno(u.id)

            nuevo_nombre_completo = (request.form.get('nombre_completo') or "").strip()
            nuevo_username = (request.form.get('username') or "").strip()
            nuevo_email = (request.form.get('email') or "").strip().lower()
            nuevo_role = request.form.get('role') or u.role

            nueva_password = (
                request.form.get('password_secure') or
                request.form.get('password') or
                ""
            )

            if not nuevo_username:
                flash("El usuario no puede quedar vacío.", "warning")
                return redirect(url_for('usuarios'))

            if not nuevo_email:
                flash("El correo no puede quedar vacío.", "warning")
                return redirect(url_for('usuarios'))

            existe_username = User.query.filter(
                User.username == nuevo_username,
                User.id != u.id
            ).first()

            if existe_username:
                flash("Ya existe otro usuario con ese nombre.", "danger")
                return redirect(url_for('usuarios'))

            existe_email = User.query.filter(
                User.email == nuevo_email,
                User.id != u.id
            ).first()

            if existe_email:
                flash("El correo ya está en uso por otro usuario.", "danger")
                return redirect(url_for('usuarios'))

            u.username = nuevo_username
            u.email = nuevo_email
            u.role = nuevo_role

            if nueva_password:
                u.set_password(nueva_password)

            db.session.commit()

            guardar_nombre_usuario_alterno(u.id, nuevo_nombre_completo)

            cambios = []

            if nombre_anterior != nuevo_nombre_completo:
                cambios.append(f"nombre: '{nombre_anterior}' → '{nuevo_nombre_completo}'")

            if username_anterior != u.username:
                cambios.append(f"usuario: '{username_anterior}' → '{u.username}'")

            if email_anterior != (u.email or ""):
                cambios.append(f"correo: '{email_anterior}' → '{u.email or ''}'")

            if rol_anterior != u.role:
                cambios.append(f"rol: '{rol_anterior}' → '{u.role}'")

            if nueva_password:
                cambios.append("contraseña actualizada")

            detalle_cambios = "; ".join(cambios) if cambios else "sin cambios visibles"

            registrar_log(
                usuario_actual.username,
                f"Modificación de usuario. Usuario afectado: {u.username}. Cambios realizados: {detalle_cambios}."
            )

            flash("Usuario modificado correctamente.", "success")

        # ======================
        # ELIMINAR
        # ======================
        elif accion == 'eliminar' and (es_admin or es_gestor):
            u = User.query.get_or_404(int(request.form['id']))
            username_eliminado = u.username
            rol_eliminado = u.role

            if u.username == 'Administrador':
                registrar_log(
                    usuario_actual.username,
                    "Intento bloqueado de eliminar el usuario Administrador."
                )
                flash("No se puede eliminar el usuario Administrador.", "danger")
                return redirect(url_for('usuarios'))

            UserPermission.query.filter_by(user_id=u.id).delete()
            eliminar_nombre_usuario_alterno(u.id)

            db.session.delete(u)
            db.session.commit()

            registrar_log(
                usuario_actual.username,
                f"Eliminación de usuario. Usuario eliminado: {username_eliminado}. Perfil que tenía: {rol_eliminado}."
            )

            flash("Usuario eliminado.", "info")

        else:
            registrar_log(
                usuario_actual.username,
                f"Acción no permitida en Gestión de Usuarios. Acción intentada: {accion or 'Sin acción'}."
            )
            flash("Acción no permitida.", "warning")

    usuarios = User.query.order_by(User.id.asc()).all()
    perfiles_usuarios = cargar_perfiles_usuarios_alternos()

    content = render_template_string("""
    <div class="users-shell">

      <div class="users-header-card">
        <div class="users-header-overlay">
          <div class="users-header-text">
            <h3 class="users-title m-0">Gestión de Usuarios</h3>
            <div class="users-subtitle">
              Administra usuarios, nombres, correos, roles, contraseñas y permisos
              de acceso dentro del sistema SGSI.
            </div>
          </div>
        </div>
      </div>

      <div class="users-card p-4 mb-4">
        <div class="users-section-title">
          Usuarios registrados
        </div>

        <div class="table-responsive users-table-wrap">
          <table class="table table-bordered align-middle mb-0">
            <thead class="users-table-head">
              <tr class="text-center">
                <th style="width:70px;">N°</th>
                <th>Nombre completo</th>
                <th>Usuario</th>
                <th>Correo</th>
                <th>Rol</th>
                <th style="min-width:300px;">Acciones</th>
              </tr>
            </thead>

            <tbody>
              {% for u in usuarios %}
                <tr>
                  <td class="text-center fw-bold">
                    {{ loop.index }}
                  </td>

                  <td>
                    <input form="f{{u.id}}"
                           name="nombre_completo"
                           value="{{ perfiles_usuarios.get(u.id, '') }}"
                           class="form-control"
                           autocomplete="off"
                           autocorrect="off"
                           autocapitalize="none"
                           spellcheck="false"
                           placeholder="Nombre completo">
                  </td>

                  <td>
                    <input form="f{{u.id}}"
                           name="username"
                           value="{{u.username}}"
                           class="form-control"
                           autocomplete="off"
                           autocorrect="off"
                           autocapitalize="none"
                           spellcheck="false">
                  </td>

                  <td>
                    <input form="f{{u.id}}"
                           name="email"
                           type="email"
                           value="{{u.email or ''}}"
                           class="form-control"
                           autocomplete="off"
                           autocorrect="off"
                           autocapitalize="none"
                           spellcheck="false">
                  </td>

                  <td>
                    <select form="f{{u.id}}" name="role" class="form-select">
                      <option value="user" {% if u.role=='user' %}selected{% endif %}>Usuario</option>
                      <option value="admin" {% if u.role=='admin' %}selected{% endif %}>Administrador</option>
                      <option value="auditor" {% if u.role=='auditor' %}selected{% endif %}>Auditor</option>
                      <option value="gestor_accesos" {% if u.role=='gestor_accesos' %}selected{% endif %}>Gestor de Accesos</option>
                    </select>
                  </td>

                  <td>
                    <input form="f{{u.id}}"
                           name="password_secure"
                           id="password_secure_{{u.id}}"
                           type="password"
                           placeholder="Nueva contraseña"
                           class="form-control mb-2 user-password-secure"
                           autocomplete="new-password"
                           autocorrect="off"
                           autocapitalize="none"
                           spellcheck="false"
                           data-lpignore="true"
                           data-form-type="other"
                           readonly
                           onfocus="this.removeAttribute('readonly');"
                           onblur="this.setAttribute('readonly','readonly');">

                    <div class="d-flex flex-wrap gap-1">
                      {% if current_role in ['admin', 'gestor_accesos'] %}
                        <button form="f{{u.id}}"
                                type="submit"
                                name="accion"
                                value="editar"
                                class="btn btn-sm btn-primary rounded-pill px-3">
                          Guardar
                        </button>

                        <button form="f{{u.id}}"
                                type="submit"
                                name="accion"
                                value="eliminar"
                                class="btn btn-sm btn-danger rounded-pill px-3"
                                onclick="return confirm('¿Seguro que deseas eliminar este usuario?');">
                          Eliminar
                        </button>
                      {% endif %}

                      {% if u.role == 'user' %}
                        <a href="{{ url_for('editar_permisos', user_id=u.id) }}"
                           class="btn btn-sm btn-warning rounded-pill px-3">
                          Permisos
                        </a>
                      {% endif %}
                    </div>

                    <form id="f{{u.id}}"
                          method="post"
                          autocomplete="off"
                          autocorrect="off"
                          autocapitalize="none"
                          spellcheck="false"
                          style="display:none;">
                      <input type="hidden" name="id" value="{{u.id}}">
                    </form>
                  </td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>

        <div class="users-id-note">
          Nota: el campo N° es consecutivo visual. El ID real del usuario se conserva internamente para permisos y relaciones.
        </div>
      </div>

      <div class="users-card p-4">
        <div class="users-section-title">
          Crear nuevo usuario
        </div>

        <form method="post"
              autocomplete="off"
              autocorrect="off"
              autocapitalize="none"
              spellcheck="false">
          <input type="hidden" name="accion" value="crear">

          <div class="users-create-grid">

            <div class="users-field">
              <label class="form-label">Nombre completo</label>
              <input name="nombre_completo"
                     placeholder="Nombre completo"
                     class="form-control"
                     autocomplete="off"
                     autocorrect="off"
                     autocapitalize="none"
                     spellcheck="false">
            </div>

            <div class="users-field">
              <label class="form-label">Usuario</label>
              <input name="username"
                     placeholder="Usuario"
                     class="form-control"
                     autocomplete="off"
                     autocorrect="off"
                     autocapitalize="none"
                     spellcheck="false"
                     required>
            </div>

            <div class="users-field">
              <label class="form-label">Correo del usuario</label>
              <input name="email"
                     type="email"
                     placeholder="Correo del usuario"
                     class="form-control"
                     autocomplete="off"
                     autocorrect="off"
                     autocapitalize="none"
                     spellcheck="false"
                     required>
            </div>

            {% if current_role in ['admin', 'gestor_accesos'] %}
              <div class="users-field users-role-field">
                <label class="form-label">Rol</label>
                <select name="role" class="form-select">
                  <option value="user">Usuario</option>
                  <option value="admin">Administrador</option>
                  <option value="auditor">Auditor</option>
                  <option value="gestor_accesos">Gestor de Accesos</option>
                </select>
              </div>
            {% endif %}

            <div class="users-create-actions">
              <button type="submit" class="btn btn-success users-create-btn">
                Crear Usuario
              </button>
            </div>

          </div>
        </form>
      </div>

    </div>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      input::-ms-reveal,
      input::-ms-clear{
        display:none;
      }

      input[type="password"]::-webkit-credentials-auto-fill-button,
      input[type="password"]::-webkit-textfield-decoration-container{
        display:none !important;
        visibility:hidden;
        pointer-events:none;
      }

      .users-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .users-header-card{
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
      }

      .users-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .users-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }

      .users-header-overlay::before{
        content:"👥";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.4rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .users-header-text{
        max-width:1000px;
        min-width:0;
      }

      .users-header-text::before{
        content:"SGSI · Administración de Usuarios";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .users-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }

      .users-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        max-width:100%;
      }

      .users-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .users-card.p-4{
        padding:1.5rem !important;
      }

      .users-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
        overflow-wrap:break-word;
      }

      .users-table-wrap{
        border:1px solid #e2ebf5;
        border-radius:14px;
        background:#ffffff;
        overflow-x:auto;
        overflow-y:hidden;
        width:100%;
        max-width:100%;
      }

      .users-table-wrap .table{
        margin-bottom:0;
        min-width:1250px;
      }

      .users-table-head th{
        background:#eef5ff !important;
        color:#0b4a8f !important;
        font-weight:950;
        vertical-align:middle !important;
        border-bottom:1px solid #d7dee7 !important;
        white-space:nowrap;
        font-size:.82rem;
      }

      table td,
      table th{
        vertical-align:middle !important;
      }

      table td{
        font-size:.85rem;
        color:#334155;
      }

      .form-control,
      .form-select{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        max-width:100%;
      }

      .form-control:focus,
      .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .users-id-note{
        margin-top:10px;
        font-size:.74rem;
        color:#475569;
        font-weight:700;
        text-align:right;
      }

      h3{
        color:#ffffff;
        margin:0;
      }

      .users-create-grid{
        display:grid;
        grid-template-columns:minmax(180px,1fr) minmax(180px,1fr) minmax(230px,1fr) minmax(150px,.65fr);
        gap:16px;
        align-items:end;
        width:100%;
        max-width:100%;
      }

      .users-field{
        min-width:0;
        width:100%;
      }

      .users-role-field{
        min-width:0;
      }

      .users-create-actions{
        grid-column:1 / -1;
        width:100%;
        display:flex;
        justify-content:flex-end;
        align-items:center;
        padding-top:4px;
      }

      .users-create-btn{
        width:190px;
        max-width:100%;
        min-height:44px;
        padding:0 22px !important;
        border-radius:12px !important;
        font-weight:950 !important;
        font-size:.92rem;
        display:flex;
        align-items:center;
        justify-content:center;
        white-space:nowrap;
        box-shadow:0 10px 18px rgba(25,135,84,.22) !important;
      }

      @media (max-width:1200px){
        .users-create-grid{
          grid-template-columns:repeat(2,minmax(220px,1fr));
        }
      }

      @media (max-width:992px){
        .users-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .users-title{
          font-size:1.20rem;
          line-height:1.08;
        }

        .users-subtitle{
          font-size:.68rem;
          line-height:1.12;
        }

        .users-card.p-4{
          padding:1rem !important;
        }

        .users-create-actions{
          justify-content:center;
        }

        .users-create-btn{
          width:100%;
        }

        .users-id-note{
          text-align:center;
        }
      }

      @media (max-width:768px){
        .users-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .users-header-overlay::before{
          margin:0;
        }

        .users-title,
        .users-subtitle{
          text-align:center;
        }

        .users-create-grid{
          grid-template-columns:1fr;
        }
      }
    </style>

    <script>
      document.addEventListener('DOMContentLoaded', function(){

        const passwordFields = document.querySelectorAll('.user-password-secure');

        passwordFields.forEach(function(field){

          field.value = '';

          field.setAttribute('type', 'password');
          field.setAttribute('autocomplete', 'new-password');
          field.setAttribute('autocorrect', 'off');
          field.setAttribute('autocapitalize', 'none');
          field.setAttribute('spellcheck', 'false');
          field.setAttribute('data-lpignore', 'true');
          field.setAttribute('data-form-type', 'other');

          setTimeout(function(){
            field.value = '';
          }, 150);

          field.addEventListener('focus', function(){
            this.removeAttribute('readonly');
            this.setAttribute('type', 'password');
            this.setAttribute('autocomplete', 'new-password');
          });

          field.addEventListener('blur', function(){
            this.setAttribute('readonly', 'readonly');
          });

        });

      });
    </script>
    """,
    usuarios=usuarios,
    current_role=usuario_actual.role,
    perfiles_usuarios=perfiles_usuarios)

    return render_template_string(BASE, content=content)


# =========================
# Crear nueva ruta para editar permisos
# =========================

@app.route('/editar_permisos/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_or_access_manager_required
def editar_permisos(user_id):
    user = User.query.get_or_404(user_id)
    usuario_actual = User.query.get(session.get('user_id'))

    if usuario_actual.role == 'gestor_accesos' and user.role != 'user':
        flash("El Gestor de Accesos solo puede gestionar permisos de usuarios con rol 'Usuario'.", "danger")
        return redirect(url_for('usuarios'))

    modules = MODULES

    if request.method == 'POST':
        permisos_seleccionados = request.form.getlist('permisos')

        try:
            UserPermission.query.filter_by(user_id=user.id).delete()

            for module in modules:
                acceso = module in permisos_seleccionados
                nuevo = UserPermission(
                    user_id=user.id,
                    module_name=module,
                    has_access=acceso
                )
                db.session.add(nuevo)

            db.session.commit()
            flash("Permisos actualizados correctamente", "success")
            return redirect(url_for('usuarios'))

        except Exception as e:
            db.session.rollback()
            flash(f"No se pudieron actualizar los permisos: {e}", "danger")

    user_perms = UserPermission.query.filter_by(user_id=user.id, has_access=True).all()
    user_modules = [p.module_name for p in user_perms]

    content = render_template_string("""
    <div class="perm-shell">

      <div class="perm-header-card">
        <div class="perm-header-overlay">
          <div class="perm-header-text">
            <h3 class="perm-title m-0">Editar Permisos</h3>
            <div class="perm-subtitle">
              Administración de módulos habilitados para el usuario {{ user.username }}
            </div>
          </div>
        </div>
      </div>

      <div class="perm-header-actions">
        <a href="{{ url_for('usuarios') }}"
           class="btn rounded-pill px-4 fw-bold perm-back-btn">
          ⬅ Volver a Usuarios
        </a>
      </div>

      <div class="perm-card">
        <div class="perm-card-body">
          <form method="post">
            <div class="row g-3">
              {% for module in modules %}
                <div class="col-md-6 col-lg-4">
                  <div class="form-check perm-check">
                    <input class="form-check-input"
                           type="checkbox"
                           name="permisos"
                           value="{{ module }}"
                           id="mod_{{ loop.index }}"
                           {% if module in user_modules %}checked{% endif %}>
                    <label class="form-check-label fw-semibold" for="mod_{{ loop.index }}">
                      {{ module }}
                    </label>
                  </div>
                </div>
              {% endfor %}
            </div>

            <div class="perm-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar Permisos
              </button>

              <a href="{{ url_for('usuarios') }}"
                 class="btn rounded-pill px-4 fw-bold perm-cancel-btn">
                Cancelar
              </a>
            </div>
          </form>
        </div>
      </div>

    </div>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .perm-shell{
        width:96%;
        max-width:1400px;
        margin:26px auto 24px auto;
      }

      .perm-header-card{
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
      }

      .perm-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .perm-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }

      .perm-header-overlay::before{
        content:"🔐";
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
      }

      .perm-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
      }

      .perm-header-text::before{
        content:"SGSI · Gestión de Permisos";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .perm-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .perm-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .perm-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .perm-header-actions .btn,
      .perm-back-btn,
      .perm-cancel-btn,
      .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .perm-back-btn,
      .perm-cancel-btn{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }

      .perm-back-btn:hover,
      .perm-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }

      .perm-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .perm-card-body,
      .perm-card .card-body{
        padding:20px;
      }

      .perm-check{
        background:#f8fafc;
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:14px 16px 14px 40px;
        min-height:58px;
        box-shadow:0 4px 10px rgba(15,23,42,.05);
      }

      .form-check-input{
        border-color:#9db7d7;
      }

      .form-check-input:checked{
        background-color:#0b4a8f;
        border-color:#0b4a8f;
      }

      .form-check-label{
        font-weight:800;
        color:#101827;
      }

      .perm-bottom-actions{
        display:flex;
        justify-content:center;
        gap:12px;
        margin-top:24px;
        flex-wrap:wrap;
      }

      @media (max-width:992px){
        .perm-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .perm-header-card{
          min-height:88px;
        }

        .perm-title{
          font-size:1.20rem;
        }

        .perm-subtitle{
          font-size:.68rem;
        }

        .perm-card-body,
        .perm-card .card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .perm-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .perm-header-overlay::before{
          margin:0;
        }

        .perm-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .perm-title,
        .perm-subtitle{
          text-align:center;
        }

        .perm-header-actions .btn,
        .perm-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """, user=user, modules=modules, user_modules=user_modules)

    return render_template_string(BASE, content=content)


# =========================
# Función genérica para verificar permisos
# =========================
def verificar_permiso(user, module_name):
    if not user:
        return False

    if user.role == 'admin':
        return True

    if user.role == 'auditor':
        return not auditor_module_blocked(module_name)

    perm = UserPermission.query.filter_by(
        user_id=user.id,
        module_name=module_name
    ).first()

    return bool(perm and perm.has_access)

def verificar_permiso_activos(user, permiso_matriz):
    if not user:
        return False

    if user.role == "admin":
        return True

    if user.role == "auditor":
        return True

    return (
        verificar_permiso(user, "Gestión de Activos de Información")
        or verificar_permiso(user, permiso_matriz)
    )


# ============================================================
# REGLAS GLOBALES DEL ROL AUDITOR
# ============================================================

AUDITOR_MODULES_DENY = {
    "Centro de Alertas",
    "Configuración Parámetros de la Empresa",
    "OpenRouter API Key",
    "Gestión de Usuarios",
    "Aplicación móvil",
}

AUDITOR_ACTIONS_DENY_LABELS = (
    "Agregar",
    "Nuevo",
    "Crear",
    "Configurar",
    "Configuración",
    "Parámetros",
    "Editar",
    "Eliminar",
)


def is_auditor(user):
    return bool(user and getattr(user, "role", None) == "auditor")


def auditor_module_blocked(module_name: str) -> bool:
    return (module_name or "").strip() in AUDITOR_MODULES_DENY


def auditor_can_enter_module(module_name: str) -> bool:
    return not auditor_module_blocked(module_name)


def auditor_is_read_only(user) -> bool:
    return is_auditor(user)


# ============================================================================================================================================
#                                                               Fin Modulo de Gestión de Usuarios
# ============================================================================================================================================

# ============================================================================================================================================
#                                                               MÓDULO LOGS DE AUDITORÍA
# ============================================================================================================================================

@app.route('/admin/logs_auditoria')
@login_required
@admin_required
def logs_auditoria():
    busqueda = (request.args.get("busqueda") or "").strip()
    fecha_desde = (request.args.get("fecha_desde") or "").strip()
    fecha_hasta = (request.args.get("fecha_hasta") or "").strip()

    conn = get_log_db_connection()
    cur = conn.cursor()

    sql = """
        SELECT id, fecha_hora, usuario_transaccion, novedad
        FROM auditoria_logs
        WHERE 1=1
    """
    params = []

    if busqueda:
        sql += """
            AND (
                usuario_transaccion LIKE ?
                OR novedad LIKE ?
            )
        """
        like_value = f"%{busqueda}%"
        params.extend([like_value, like_value])

    if fecha_desde:
        sql += " AND substr(fecha_hora, 1, 10) >= ? "
        params.append(fecha_desde)

    if fecha_hasta:
        sql += " AND substr(fecha_hora, 1, 10) <= ? "
        params.append(fecha_hasta)

    sql += " ORDER BY datetime(fecha_hora) ASC "

    cur.execute(sql, params)
    logs = cur.fetchall()
    conn.close()

    content = render_template_string("""
    <div class="logs-shell">

      <div class="logs-header-card">
        <div class="logs-header-overlay">
          <div class="logs-header-text">
            <h3 class="logs-title m-0">Logs de Auditoría</h3>
            <div class="logs-subtitle">
              Registro de accesos exitosos, accesos fallidos y creación de usuarios del SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="logs-header-actions">
        
      </div>

      <div class="logs-card p-4 mb-4">
        <div class="logs-section-title">Filtros de búsqueda</div>

        <form method="get">
          <div class="row g-3">
            <div class="col-md-4">
              <label class="form-label">Buscar por usuario o novedad</label>
              <input type="text" name="busqueda" value="{{ busqueda }}" class="form-control" placeholder="Ej: acceso fallido, admin, carlos">
            </div>

            <div class="col-md-3">
              <label class="form-label">Fecha desde</label>
              <input type="date" name="fecha_desde" value="{{ fecha_desde }}" class="form-control">
            </div>

            <div class="col-md-3">
              <label class="form-label">Fecha hasta</label>
              <input type="date" name="fecha_hasta" value="{{ fecha_hasta }}" class="form-control">
            </div>

            <div class="col-md-2 d-flex align-items-end">
              <button class="btn btn-primary rounded-pill w-100 fw-bold">Filtrar</button>
            </div>
          </div>
        </form>
      </div>

      <div class="logs-card p-4">
        <div class="logs-section-title d-flex justify-content-between align-items-center flex-wrap gap-2">
          <span>Histórico de logs</span>
          <span class="badge bg-primary">Total: {{ logs|length }}</span>
        </div>

        <div class="table-responsive logs-table-wrap">
          <table class="table table-bordered align-middle mb-0">
            <thead class="logs-table-head">
              <tr class="text-center">
                <th style="width:90px;">ID</th>
                <th style="width:190px;">Fecha y hora</th>
                <th style="width:220px;">Usuario que hizo la transacción</th>
                <th>Novedad</th>
              </tr>
            </thead>
            <tbody>
              {% for log in logs %}
                <tr>
                  <td class="text-center">{{ log["id"] }}</td>
                  <td class="text-center">{{ log["fecha_hora"] }}</td>
                  <td>{{ log["usuario_transaccion"] }}</td>
                  <td>{{ log["novedad"] }}</td>
                </tr>
              {% else %}
                <tr>
                  <td colspan="4" class="text-center text-muted py-4">
                    No hay registros de auditoría para mostrar.
                  </td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .logs-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .logs-header-card{
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
      }

      .logs-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .logs-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }

      .logs-header-overlay::before{
        content:"🧾";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.4rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .logs-header-text{
        max-width:1000px;
        min-width:0;
      }

      .logs-header-text::before{
        content:"SGSI · Auditoría y Trazabilidad";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .logs-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }

      .logs-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }

      .logs-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        max-width:100%;
      }

      .logs-btn-main{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .logs-btn-main:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      .logs-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .logs-card.p-4{
        padding:1.5rem !important;
      }

      .logs-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
        overflow-wrap:break-word;
      }

      .logs-table-wrap{
        border:1px solid #e2ebf5;
        border-radius:14px;
        background:#ffffff;
        overflow-x:auto;
        overflow-y:hidden;
        width:100%;
        max-width:100%;
      }

      .logs-table-wrap .table{
        margin-bottom:0;
        min-width:980px;
      }

      .logs-table-head th{
        background:#eef5ff !important;
        color:#0b4a8f !important;
        font-weight:950;
        vertical-align:middle !important;
        border-bottom:1px solid #d7dee7 !important;
        white-space:nowrap;
        font-size:.82rem;
      }

      .logs-table-wrap td,
      .logs-table-wrap th{
        vertical-align:middle !important;
      }

      .logs-table-wrap td{
        font-size:.85rem;
        color:#334155;
      }

      .logs-table-wrap tbody tr:hover{
        background:#f8fbff;
      }

      .form-control,
      .form-select{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        max-width:100%;
      }

      .form-control:focus,
      .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      h3{
        color:#ffffff;
        margin:0;
      }

      @media (max-width:992px){
        .logs-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .logs-title{
          font-size:1.20rem;
          line-height:1.08;
        }

        .logs-subtitle{
          font-size:.68rem;
          line-height:1.12;
        }

        .logs-card.p-4{
          padding:1rem !important;
        }
      }

      @media (max-width:768px){
        .logs-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .logs-header-overlay::before{
          margin:0;
        }

        .logs-title,
        .logs-subtitle{
          text-align:center;
        }

        .logs-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, logs=logs, busqueda=busqueda, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)

    return render_template_string(BASE, content=content)

# ============================================================================================================================================
#                                                               FIN MÓDULO LOGS DE AUDITORÍA
# ============================================================================================================================================

# ============================================================================================================================================
#                                                               Menu Principal
# ============================================================================================================================================
# AJUSTE: menú activo corregido, Pruebas SAST integrado y botón duplicado removido.

# =====================================================================
# HELPERS TABLERO PRINCIPAL SGSI (VERSIÓN GRANDE + VELOCÍMETRO MEJORADO)
# =====================================================================
from collections import Counter
import base64
import io
import math
import re
import json
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from flask import jsonify


def _dashboard_fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        bbox_inches="tight",
        dpi=220,
        facecolor=fig.get_facecolor()
    )
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _dashboard_empty_chart(title="Sin datos", subtitle="No hay información disponible"):
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    ax.axis("off")

    ax.text(
        0.5, 0.62, title,
        ha="center", va="center",
        fontsize=18, fontweight="bold", color="#101827"
    )
    ax.text(
        0.5, 0.42, subtitle,
        ha="center", va="center",
        fontsize=11, color="#4b5563"
    )
    return _dashboard_fig_to_b64(fig)


def _dashboard_gauge_b64(value, title="Cumplimiento", subtitle="Protección de datos personales"):
    try:
        value = float(value or 0)
    except Exception:
        value = 0.0

    value = max(0.0, min(100.0, value))

    fig, ax = plt.subplots(figsize=(8.6, 5.6), subplot_kw={"aspect": "equal"})
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    ax.axis("off")

    # =========================================================
    # GEOMETRÍA
    # Velocímetro superior: 180° (izquierda) a 0° (derecha)
    # =========================================================
    r_outer = 1.22
    band_width = 0.24

    # arco base
    ax.add_patch(
        patches.Wedge(
            (0, 0), r_outer, 0, 180,
            width=band_width,
            facecolor="#e5e7eb",
            edgecolor="none"
        )
    )

    # segmentos de color: izquierda rojo -> derecha azul
    segmentos = [
        (144, 180, "#b91c1c"),  # 0-20
        (108, 144, "#c76b00"),  # 20-40
        (72, 108, "#d39b00"),   # 40-60
        (36, 72, "#0f8a42"),    # 60-80
        (0, 36, "#087ab8"),     # 80-100
    ]

    for a0, a1, color in segmentos:
        ax.add_patch(
            patches.Wedge(
                (0, 0), r_outer, a0, a1,
                width=band_width,
                facecolor=color,
                edgecolor="white",
                linewidth=2.0
            )
        )

    # =========================================================
    # MARCAS Y NÚMEROS ARRIBA
    # 0 izquierda -> 100 derecha
    # =========================================================
    for pct in range(0, 101, 20):
        angle_deg = 180 - (pct / 100.0) * 180.0
        ang = math.radians(angle_deg)

        # marca
        x0, y0 = 0.92 * math.cos(ang), 0.92 * math.sin(ang)
        x1, y1 = 1.08 * math.cos(ang), 1.08 * math.sin(ang)
        ax.plot([x0, x1], [y0, y1], color="#64748b", linewidth=1.5)

        # texto
        tx, ty = 1.36 * math.cos(ang), 1.36 * math.sin(ang)
        ax.text(
            tx, ty, f"{pct}",
            ha="center", va="center",
            fontsize=10.5,
            color="#475569",
            fontweight="bold"
        )

    # =========================================================
    # FLECHA / AGUJA CORRECTA
    # 0 izquierda -> 100 derecha, siempre hacia arriba
    # =========================================================
    angle_deg = 180 - (value / 100.0) * 180.0
    ang = math.radians(angle_deg)

    # aguja principal
    x = 0.83 * math.cos(ang)
    y = 0.83 * math.sin(ang)
    ax.plot([0, x], [0, y], linewidth=4.6, color="#0b1220", solid_capstyle="round", zorder=6)

    # punta triangular para que se vea más bonita
    tip_x = 0.98 * math.cos(ang)
    tip_y = 0.98 * math.sin(ang)

    left_ang = math.radians(angle_deg + 90)
    right_ang = math.radians(angle_deg - 90)

    base_left_x = 0.05 * math.cos(left_ang)
    base_left_y = 0.05 * math.sin(left_ang)
    base_right_x = 0.05 * math.cos(right_ang)
    base_right_y = 0.05 * math.sin(right_ang)

    needle = patches.Polygon(
        [
            (base_left_x, base_left_y),
            (tip_x, tip_y),
            (base_right_x, base_right_y),
        ],
        closed=True,
        facecolor="#0b1220",
        edgecolor="none",
        zorder=7
    )
    ax.add_patch(needle)

    # centro
    ax.add_patch(patches.Circle((0, 0), 0.085, color="#0b1220", zorder=8))
    ax.add_patch(patches.Circle((0, 0), 0.035, color="#ffffff", zorder=9))

    # =========================================================
    # TEXTO CENTRAL
    # =========================================================
    ax.text(
        0, 0.38, f"{value:.1f}%",
        ha="center", va="center",
        fontsize=30,
        fontweight="bold",
        color="#0b1220"
    )

    ax.text(
        0, 0.16, title,
        ha="center", va="center",
        fontsize=14,
        fontweight="bold",
        color="#101827"
    )

    ax.text(
        0, -0.02, subtitle,
        ha="center", va="center",
        fontsize=10.5,
        color="#4b5563"
    )

    ax.set_xlim(-1.50, 1.50)
    ax.set_ylim(-0.18, 1.50)

    return _dashboard_fig_to_b64(fig)

def _dashboard_donut_b64(labels, values, title="", subtitle=""):
    labels = labels or []
    values = values or []

    total = sum(v for v in values if isinstance(v, (int, float)))
    if not labels or not values or total == 0:
        return _dashboard_empty_chart(title or "Sin datos", "No hay información para graficar")

    palette = [
        "#087c3d",
        "#84cc16",
        "#d39b00",
        "#c95508",
        "#b91c1c",
        "#5521a8",
        "#087ab8",
    ]
    colors = [palette[i % len(palette)] for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(8.0, 5.6))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    def _autopct(pct):
        if pct < 4:
            return ""
        return f"{pct:.0f}%"

    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        autopct=_autopct,
        startangle=90,
        counterclock=False,
        colors=colors,
        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
        pctdistance=0.78
    )

    for t in autotexts:
        t.set_fontsize(10)
        t.set_color("#0b1220")
        t.set_fontweight("bold")

    ax.text(
        0, 0.08, str(int(total)),
        ha="center", va="center",
        fontsize=28, fontweight="bold", color="#0b1220"
    )
    ax.text(
        0, -0.14, "Total",
        ha="center", va="center",
        fontsize=10, color="#4b5563"
    )

    legend_labels = [f"{lab}: {val}" for lab, val in zip(labels, values)]
    ax.legend(
        wedges,
        legend_labels,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        fontsize=10,
        frameon=False,
        handlelength=1.2,
        labelspacing=0.8
    )

    if title:
        ax.set_title(title, fontsize=15, fontweight="bold", color="#0b1220", pad=12)
    if subtitle:
        fig.text(0.5, 0.03, subtitle, ha="center", fontsize=10, color="#4b5563")

    ax.set_aspect("equal")
    return _dashboard_fig_to_b64(fig)


def _dashboard_latest_iso_radar():
    try:
        run = AnalysisRun.query.order_by(AnalysisRun.id.desc()).first()
        if not run:
            return _dashboard_empty_chart("Madurez ISO 27001", "Sin datos")

        chapter_results = json.loads(run.chapter_results_json or "{}")

        labels = []
        values = []

        for cap, data in chapter_results.items():
            labels.append(cap[:20])  # evita texto largo
            try:
                values.append(float(data.get("pct", 0)))
            except:
                values.append(0)

        if not labels:
            return _dashboard_empty_chart("Madurez ISO 27001", "Sin datos")

        return generar_radar_grande(labels, values, "Madurez ISO 27001")

    except Exception as e:
        return _dashboard_empty_chart("ISO Error", str(e))

def generar_radar_grande(labels, values, title):
    angles = [n / float(len(labels)) * 2 * math.pi for n in range(len(labels))]
    angles += angles[:1]

    values += values[:1]

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#ffffff")

    ax.plot(angles, values, linewidth=3)
    ax.fill(angles, values, alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11)

    ax.set_yticks([20,40,60,80,100])
    ax.set_yticklabels(["20%","40%","60%","80%","100%"], fontsize=10)

    # 🔥 porcentaje en el centro
    promedio = sum(values[:-1]) / len(values[:-1]) if values else 0
    ax.text(0, 0, f"{promedio:.1f}%", ha='center', va='center',
            fontsize=28, fontweight='bold', color="#0b1220")

    ax.set_title(title, size=16, pad=30, fontweight="bold")

    return _dashboard_fig_to_b64(fig)



def _dashboard_latest_nist_radar():
    try:
        run = (
            NistMadurezRun.query
            .filter(NistMadurezRun.estado == "FINALIZADO")
            .order_by(NistMadurezRun.id.desc())
            .first()
        )

        if not run:
            return _dashboard_empty_chart(
                "Madurez NIST CSF 2.0",
                "No se encontró una revisión NIST finalizada"
            )

        radar = (getattr(run, "radar_overall_b64", None) or "").strip()
        if radar:
            return radar

        resumen = {}
        try:
            resumen = json.loads(run.resumen_json or "{}")
        except Exception:
            resumen = {}

        radar_labels, radar_values = nist_pct_por_funcion(resumen, NIST_FUNC_ORDER)
        if radar_labels and radar_values:
            radar = nist_radar_b64(
                radar_labels,
                radar_values,
                title="Madurez NIST CSF 2.0"
            )
            if radar:
                return radar

    except Exception:
        pass

    return _dashboard_empty_chart(
        "Madurez NIST CSF 2.0",
        "No se encontró una araña NIST disponible"
    )

def _dashboard_latest_iso_data():
    try:
        run = AnalysisRun.query.order_by(AnalysisRun.id.desc()).first()
        if not run:
            return {
                "radar_b64": _dashboard_empty_chart(
                    "Madurez ISO 27001",
                    "No se encontró una araña ISO disponible"
                ),
                "pct": 0.0
            }

        radar = (getattr(run, "radar_overall_b64", None) or "").strip()

        pct_general = 0.0
        try:
            chapter_results = json.loads(run.chapter_results_json or "{}")
            vals = []
            if isinstance(chapter_results, dict):
                for _, data in chapter_results.items():
                    try:
                        vals.append(float((data or {}).get("pct", 0) or 0))
                    except Exception:
                        pass
            if vals:
                pct_general = round(sum(vals) / len(vals), 2)
        except Exception:
            pct_general = 0.0

        if not radar:
            radar = _dashboard_empty_chart(
                "Madurez ISO 27001",
                "No se encontró una araña ISO disponible"
            )

        return {
            "radar_b64": radar,
            "pct": pct_general
        }

    except Exception:
        return {
            "radar_b64": _dashboard_empty_chart(
                "Madurez ISO 27001",
                "No se encontró una araña ISO disponible"
            ),
            "pct": 0.0
        }

def _dashboard_latest_nist_data():
    try:
        run = (
            NistMadurezRun.query
            .filter(NistMadurezRun.estado == "FINALIZADO")
            .order_by(NistMadurezRun.id.desc())
            .first()
        )

        if not run:
            return {
                "radar_b64": _dashboard_empty_chart(
                    "Madurez NIST CSF 2.0",
                    "No se encontró una revisión NIST finalizada"
                ),
                "pct": 0.0
            }

        radar = (getattr(run, "radar_overall_b64", None) or "").strip()
        pct_general = float(run.pct_general or 0)

        if not radar:
            resumen = {}
            try:
                resumen = json.loads(run.resumen_json or "{}")
            except Exception:
                resumen = {}

            radar_labels, radar_values = nist_pct_por_funcion(resumen, NIST_FUNC_ORDER)
            if radar_labels and radar_values:
                radar = nist_radar_b64(
                    radar_labels,
                    radar_values,
                    title="Madurez NIST CSF 2.0"
                )

        if not radar:
            radar = _dashboard_empty_chart(
                "Madurez NIST CSF 2.0",
                "No se encontró una araña NIST disponible"
            )

        return {
            "radar_b64": radar,
            "pct": round(pct_general, 2)
        }

    except Exception:
        return {
            "radar_b64": _dashboard_empty_chart(
                "Madurez NIST CSF 2.0",
                "No se encontró una araña NIST disponible"
            ),
            "pct": 0.0
        }




# ============================================================
# CONSTRUCTOR PERSONAL DEL CENTRO DE CONTROL
# ============================================================
# El catálogo fijo conserva las visualizaciones originales y agrega fuentes
# de madurez y métricas que ya existen en GRAC. Los elementos adicionales
# creados por cada usuario se almacenan en dashboard_custom_widgets.
DASHBOARD_WIDGET_CATALOG = [
    {
        "key": "kpi_iso",
        "kind": "kpi",
        "group": "Indicadores superiores",
        "label": "Indicador ISO 27001",
        "description": "Porcentaje general de madurez ISO 27001.",
        "title": "ISO 27001",
        "subtitle": "Madurez general",
        "icon": "bi-shield-check",
        "color": "blue",
        "value_key": "iso_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_iso_stat",
        "default_enabled": True,
    },
    {
        "key": "kpi_nist",
        "kind": "kpi",
        "group": "Indicadores superiores",
        "label": "Indicador NIST CSF 2.0",
        "description": "Porcentaje general de cumplimiento NIST CSF 2.0.",
        "title": "NIST CSF 2.0",
        "subtitle": "Cumplimiento general",
        "icon": "bi-compass",
        "color": "orange",
        "value_key": "nist_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_nist_stat",
        "default_enabled": True,
    },
    {
        "key": "kpi_datos",
        "kind": "kpi",
        "group": "Indicadores superiores",
        "label": "Indicador de Datos Personales",
        "description": "Nivel general de cumplimiento en protección de datos personales.",
        "title": "Datos Personales",
        "subtitle": "Nivel de cumplimiento",
        "icon": "bi-lock-fill",
        "color": "green",
        "value_key": "datos_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_datos_stat",
        "default_enabled": True,
    },
    {
        "key": "kpi_scorecard",
        "kind": "kpi",
        "group": "Indicadores superiores",
        "label": "Indicador Security Scorecard",
        "description": "Promedio de Security Scorecard de terceros.",
        "title": "Security Scorecard",
        "subtitle": "Score promedio",
        "icon": "bi-shield-fill-check",
        "color": "purple",
        "value_key": "scorecard_terceros_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_scorecard_terceros_stat",
        "default_enabled": True,
    },
    {
        "key": "kpi_pci",
        "kind": "kpi",
        "group": "Madurez y cumplimiento",
        "label": "Madurez PCI-DSS",
        "description": "Nivel promedio general de la última evaluación PCI-DSS.",
        "title": "PCI-DSS",
        "subtitle": "Nivel de madurez",
        "icon": "bi-credit-card-2-front",
        "color": "orange",
        "value_key": "pci_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_pci_stat",
        "default_enabled": False,
    },
    {
        "key": "kpi_soc2",
        "kind": "kpi",
        "group": "Madurez y cumplimiento",
        "label": "Madurez SOC 2",
        "description": "Porcentaje general de la última evaluación de madurez SOC 2.",
        "title": "SOC 2",
        "subtitle": "Nivel de madurez",
        "icon": "bi-patch-check-fill",
        "color": "purple",
        "value_key": "soc2_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_soc2_stat",
        "default_enabled": False,
    },
    {
        "key": "kpi_ai",
        "kind": "kpi",
        "group": "Madurez y cumplimiento",
        "label": "Madurez del Sistema de Gestión de IA",
        "description": "Porcentaje general de la última revisión ISO/IEC 42001 del sistema de gestión de IA.",
        "title": "Gestión de IA",
        "subtitle": "Madurez ISO/IEC 42001",
        "icon": "bi-robot",
        "color": "blue",
        "value_key": "ai_maturity_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_ai_stat",
        "default_enabled": False,
    },
    {
        "key": "kpi_riesgos_activos",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Total de riesgos activos",
        "description": "Cantidad de riesgos no archivados registrados en la matriz.",
        "title": "Riesgos activos",
        "subtitle": "Matriz de riesgos",
        "icon": "bi-exclamation-diamond-fill",
        "color": "orange",
        "value_key": "risks_active_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_risks_active",
        "default_enabled": False,
    },
    {
        "key": "kpi_riesgos_fuera_apetito",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Riesgos fuera del apetito",
        "description": "Riesgos activos cuyo nivel residual supera el apetito configurado.",
        "title": "Fuera del apetito",
        "subtitle": "Riesgo residual",
        "icon": "bi-exclamation-triangle-fill",
        "color": "purple",
        "value_key": "risks_outside_appetite_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_risks_outside",
        "default_enabled": False,
    },
    {
        "key": "kpi_incidentes_abiertos",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Incidentes abiertos",
        "description": "Cantidad de incidentes que todavía no están cerrados o resueltos.",
        "title": "Incidentes abiertos",
        "subtitle": "Gestión de incidentes",
        "icon": "bi-broadcast-pin",
        "color": "orange",
        "value_key": "incidents_open_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_incidents_open",
        "default_enabled": False,
    },
    {
        "key": "kpi_incidentes_cumplimiento",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Cumplimiento promedio de incidentes",
        "description": "Promedio del cumplimiento global MTCD/MTIR calculado en métricas de incidentes.",
        "title": "Cumplimiento incidentes",
        "subtitle": "Promedio MTCD / MTIR",
        "icon": "bi-stopwatch-fill",
        "color": "green",
        "value_key": "incidents_compliance_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_incidents_compliance",
        "default_enabled": False,
    },
    {
        "key": "kpi_vulnerabilidades_abiertas",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Vulnerabilidades abiertas",
        "description": "Cantidad de vulnerabilidades cuyo estado continúa abierto.",
        "title": "Vulnerabilidades abiertas",
        "subtitle": "Gestión de vulnerabilidades",
        "icon": "bi-bug-fill",
        "color": "orange",
        "value_key": "vulnerabilities_open_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_vulns_open",
        "default_enabled": False,
    },
    {
        "key": "kpi_vulnerabilidades_criticas",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Vulnerabilidades críticas abiertas",
        "description": "Cantidad de vulnerabilidades críticas que permanecen abiertas.",
        "title": "Críticas abiertas",
        "subtitle": "Vulnerabilidades",
        "icon": "bi-radioactive",
        "color": "purple",
        "value_key": "vulnerabilities_critical_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_vulns_critical",
        "default_enabled": False,
    },
    {
        "key": "kpi_planes_abiertos",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Planes de acción abiertos",
        "description": "Cantidad de actividades de mejora o acciones correctivas abiertas.",
        "title": "Planes abiertos",
        "subtitle": "Planes de acción",
        "icon": "bi-list-check",
        "color": "blue",
        "value_key": "plans_open_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_plans_open",
        "default_enabled": False,
    },
    {
        "key": "kpi_planes_vencidos",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Planes de acción vencidos",
        "description": "Planes abiertos cuya fecha propuesta de ejecución ya venció.",
        "title": "Planes vencidos",
        "subtitle": "Seguimiento de acciones",
        "icon": "bi-calendar-x-fill",
        "color": "purple",
        "value_key": "plans_overdue_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_plans_overdue",
        "default_enabled": False,
    },
    {
        "key": "kpi_requisitos_no_cumple",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Requisitos legales no cumplidos",
        "description": "Cantidad de requisitos legales con estado No cumple o Incumple.",
        "title": "Requisitos no cumplidos",
        "subtitle": "Cumplimiento legal",
        "icon": "bi-bank2",
        "color": "orange",
        "value_key": "legal_noncompliant_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_legal_noncompliant",
        "default_enabled": False,
    },
    {
        "key": "kpi_proveedores_alta",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Proveedores de criticidad alta",
        "description": "Cantidad de evaluaciones de proveedores clasificadas con criticidad alta.",
        "title": "Proveedores críticos",
        "subtitle": "Criticidad alta",
        "icon": "bi-buildings-fill",
        "color": "purple",
        "value_key": "providers_high_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_providers_high",
        "default_enabled": False,
    },
    {
        "key": "kpi_cultura_seguridad",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Última métrica de cultura de seguridad",
        "description": "Resultado general de la medición más reciente de cultura y formación.",
        "title": "Cultura de seguridad",
        "subtitle": "Último resultado",
        "icon": "bi-people-fill",
        "color": "green",
        "value_key": "security_culture_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_security_culture",
        "default_enabled": False,
    },
    {
        "key": "chart_iso",
        "kind": "chart",
        "group": "Gráficas de madurez y cumplimiento",
        "label": "Gráfica de madurez ISO 27001",
        "description": "Araña o gráfica consolidada de madurez ISO 27001.",
        "title": "Madurez ISO 27001",
        "value_key": "iso_pct",
        "suffix": "%",
        "decimals": 2,
        "image_key": "iso_radar_b64",
        "image_id": "dash_iso_radar",
        "default_enabled": True,
    },
    {
        "key": "chart_nist",
        "kind": "chart",
        "group": "Gráficas de madurez y cumplimiento",
        "label": "Gráfica de madurez NIST CSF 2.0",
        "description": "Araña o gráfica consolidada de madurez NIST CSF 2.0.",
        "title": "Madurez NIST CSF 2.0",
        "value_key": "nist_pct",
        "suffix": "%",
        "decimals": 2,
        "image_key": "nist_radar_b64",
        "image_id": "dash_nist_radar",
        "default_enabled": True,
    },
    {
        "key": "chart_datos",
        "kind": "chart",
        "group": "Gráficas de madurez y cumplimiento",
        "label": "Gráfica de Protección de Datos Personales",
        "description": "Medidor del nivel de cumplimiento en protección de datos personales.",
        "title": "Protección de Datos Personales",
        "value_key": "datos_pct",
        "suffix": "%",
        "decimals": 2,
        "image_key": "datos_gauge_b64",
        "image_id": "dash_datos_gauge",
        "default_enabled": True,
    },
    {
        "key": "chart_pci",
        "kind": "chart",
        "group": "Gráficas de madurez y cumplimiento",
        "label": "Gráfica de madurez PCI-DSS",
        "description": "Medidor de la última evaluación de madurez PCI-DSS.",
        "title": "Madurez PCI-DSS",
        "value_key": "pci_pct",
        "suffix": "%",
        "decimals": 2,
        "image_key": "pci_gauge_b64",
        "image_id": "dash_pci_gauge",
        "default_enabled": False,
    },
    {
        "key": "chart_soc2",
        "kind": "chart",
        "group": "Gráficas de madurez y cumplimiento",
        "label": "Gráfica de madurez SOC 2",
        "description": "Araña o medidor de la última evaluación SOC 2.",
        "title": "Madurez SOC 2",
        "value_key": "soc2_pct",
        "suffix": "%",
        "decimals": 2,
        "image_key": "soc2_radar_b64",
        "image_id": "dash_soc2_radar",
        "default_enabled": False,
    },
    {
        "key": "chart_ai",
        "kind": "chart",
        "group": "Gráficas de madurez y cumplimiento",
        "label": "Gráfica del Sistema de Gestión de IA",
        "description": "Araña o medidor de la última revisión ISO/IEC 42001.",
        "title": "Sistema de Gestión de IA",
        "value_key": "ai_maturity_pct",
        "suffix": "%",
        "decimals": 2,
        "image_key": "ai_radar_b64",
        "image_id": "dash_ai_radar",
        "default_enabled": False,
    },
    {
        "key": "chart_riesgos",
        "kind": "chart",
        "group": "Gráficas operativas",
        "label": "Gráfica de Riesgos Residuales",
        "description": "Distribución de los riesgos residuales por nivel.",
        "title": "Riesgos residuales",
        "display_value": "Distribución",
        "image_key": "riesgos_b64",
        "image_id": "dash_riesgos",
        "default_enabled": True,
    },
    {
        "key": "chart_incidentes",
        "kind": "chart",
        "group": "Gráficas operativas",
        "label": "Gráfica de Incidentes",
        "description": "Clasificación consolidada de incidentes de seguridad.",
        "title": "Incidentes",
        "display_value": "Clasificación",
        "image_key": "incidentes_b64",
        "image_id": "dash_incidentes",
        "default_enabled": True,
    },
    {
        "key": "chart_vulnerabilidades",
        "kind": "chart",
        "group": "Gráficas operativas",
        "label": "Gráfica de Vulnerabilidades",
        "description": "Distribución de vulnerabilidades por criticidad.",
        "title": "Vulnerabilidades",
        "display_value": "Criticidad",
        "image_key": "vulnerabilidades_b64",
        "image_id": "dash_vulnerabilidades",
        "default_enabled": True,
    },
    {
        "key": "chart_proveedores",
        "kind": "chart",
        "group": "Gráficas operativas",
        "label": "Gráfica de Proveedores",
        "description": "Distribución de proveedores de acuerdo con su criticidad.",
        "title": "Proveedores",
        "display_value": "Criticidad",
        "image_key": "proveedores_criticidad_b64",
        "image_id": "dash_proveedores_criticidad",
        "default_enabled": True,
    },
    {
        "key": "chart_planes_accion",
        "kind": "chart",
        "group": "Gráficas operativas",
        "label": "Gráfica de Planes de Acción",
        "description": "Estado consolidado de los planes de acción del SGSI.",
        "title": "Planes de acción",
        "display_value": "Estado",
        "image_key": "planes_accion_estado_b64",
        "image_id": "dash_planes_accion_estado",
        "default_enabled": True,
    },
    {
        "key": "chart_requisitos_legales",
        "kind": "chart",
        "group": "Gráficas operativas",
        "label": "Gráfica de Requisitos Legales",
        "description": "Estado de cumplimiento de los requisitos legales registrados.",
        "title": "Requisitos legales",
        "display_value": "Cumplimiento",
        "image_key": "requisitos_legales_estado_b64",
        "image_id": "dash_requisitos_legales_estado",
        "default_enabled": True,
    },
]

DASHBOARD_WIDGET_MAP = {
    item["key"]: dict(item, default_order=index + 1)
    for index, item in enumerate(DASHBOARD_WIDGET_CATALOG)
}

# Fuentes seguras para que cada usuario construya visualizaciones sencillas.
# El usuario únicamente selecciona: 1) fuente de datos y 2) presentación.
# No se permite ingresar SQL, nombres de tablas, código ni expresiones libres.
DASHBOARD_VISUALIZATION_LABELS = {
    "radar": "Araña / radar",
    "gauge": "Velocímetro",
    "donut": "Aro",
    "line": "Línea en el tiempo",
    "pie": "Circular (pie)",
    "bar_vertical": "Barras verticales",
    "bar_horizontal": "Barras horizontales",
    "kpi": "Indicador numérico (anterior)",
}

DASHBOARD_DATA_SOURCE_CATALOG = [
    # Niveles de madurez: araña o velocímetro.
    {"key": "maturity_iso_pct", "group": "Niveles de madurez", "data_kind": "maturity", "label": "Nivel de Madurez — ISO 27001", "description": "Última evaluación de madurez ISO 27001.", "unit": "%", "decimals": 2, "allowed_views": ["radar", "gauge"], "default_title": "Nivel de Madurez — ISO 27001", "default_subtitle": "Última evaluación", "icon": "bi-shield-check", "color": "blue"},
    {"key": "maturity_nist_pct", "group": "Niveles de madurez", "data_kind": "maturity", "label": "Nivel de Madurez — NIST CSF 2.0", "description": "Última evaluación de madurez NIST CSF 2.0.", "unit": "%", "decimals": 2, "allowed_views": ["radar", "gauge"], "default_title": "Nivel de Madurez — NIST CSF 2.0", "default_subtitle": "Última evaluación", "icon": "bi-compass", "color": "orange"},
    {"key": "maturity_data_pct", "group": "Niveles de madurez", "data_kind": "maturity", "label": "Nivel de Madurez — Protección de Datos Personales", "description": "Última evaluación de protección de datos personales.", "unit": "%", "decimals": 2, "allowed_views": ["radar", "gauge"], "default_title": "Nivel de Madurez — Datos Personales", "default_subtitle": "Última evaluación", "icon": "bi-lock-fill", "color": "green"},
    {"key": "maturity_pci_pct", "group": "Niveles de madurez", "data_kind": "maturity", "label": "Nivel de Madurez — PCI-DSS", "description": "Última evaluación de madurez PCI-DSS.", "unit": "%", "decimals": 2, "allowed_views": ["radar", "gauge"], "default_title": "Nivel de Madurez — PCI-DSS", "default_subtitle": "Última evaluación", "icon": "bi-credit-card-2-front", "color": "orange"},
    {"key": "maturity_soc2_pct", "group": "Niveles de madurez", "data_kind": "maturity", "label": "Nivel de Madurez — SOC 2", "description": "Última evaluación de madurez SOC 2.", "unit": "%", "decimals": 2, "allowed_views": ["radar", "gauge"], "default_title": "Nivel de Madurez — SOC 2", "default_subtitle": "Última evaluación", "icon": "bi-patch-check-fill", "color": "purple"},
    {"key": "maturity_ai_pct", "group": "Niveles de madurez", "data_kind": "maturity", "label": "Nivel de Madurez — Sistema de Gestión de Inteligencia Artificial", "description": "Última revisión ISO/IEC 42001 del sistema de gestión de IA.", "unit": "%", "decimals": 2, "allowed_views": ["radar", "gauge"], "default_title": "Nivel de Madurez — Gestión de IA", "default_subtitle": "ISO/IEC 42001", "icon": "bi-robot", "color": "blue"},

    # Distribuciones: aro, pie o barras. También pueden resumirse en velocímetro.
    {"key": "risks_residual_distribution", "group": "Riesgos", "data_kind": "distribution", "label": "Riesgos por nivel residual", "description": "Distribución de los riesgos activos por nivel residual.", "unit": "", "decimals": 0, "allowed_views": ["donut", "pie", "bar_vertical", "bar_horizontal", "gauge"], "default_title": "Riesgos por nivel residual", "default_subtitle": "Distribución de riesgos activos", "icon": "bi-exclamation-diamond-fill", "color": "orange"},
    {"key": "incidents_classification_distribution", "group": "Incidentes", "data_kind": "distribution", "label": "Incidentes por clasificación", "description": "Distribución de incidentes por clasificación o criticidad.", "unit": "", "decimals": 0, "allowed_views": ["donut", "pie", "bar_vertical", "bar_horizontal", "gauge"], "default_title": "Incidentes por clasificación", "default_subtitle": "Gestión de incidentes", "icon": "bi-broadcast-pin", "color": "orange"},
    {"key": "vulnerabilities_severity_distribution", "group": "Vulnerabilidades", "data_kind": "distribution", "label": "Vulnerabilidades por criticidad", "description": "Distribución de vulnerabilidades por nivel de criticidad.", "unit": "", "decimals": 0, "allowed_views": ["donut", "pie", "bar_vertical", "bar_horizontal", "gauge"], "default_title": "Vulnerabilidades por criticidad", "default_subtitle": "Gestión de vulnerabilidades", "icon": "bi-bug-fill", "color": "purple"},
    {"key": "providers_criticality_distribution", "group": "Proveedores", "data_kind": "distribution", "label": "Proveedores por criticidad", "description": "Distribución de proveedores según su criticidad.", "unit": "", "decimals": 0, "allowed_views": ["donut", "pie", "bar_vertical", "bar_horizontal", "gauge"], "default_title": "Proveedores por criticidad", "default_subtitle": "Evaluación de terceros", "icon": "bi-buildings-fill", "color": "purple"},
    {"key": "plans_status_distribution", "group": "Planes y mejora", "data_kind": "distribution", "label": "Planes de acción por estado", "description": "Distribución de planes de acción abiertos, cerrados o sin estado.", "unit": "", "decimals": 0, "allowed_views": ["donut", "pie", "bar_vertical", "bar_horizontal", "gauge"], "default_title": "Planes de acción por estado", "default_subtitle": "Seguimiento de acciones", "icon": "bi-list-check", "color": "blue"},
    {"key": "legal_status_distribution", "group": "Cumplimiento", "data_kind": "distribution", "label": "Requisitos legales por estado", "description": "Distribución de requisitos legales por estado de cumplimiento.", "unit": "", "decimals": 0, "allowed_views": ["donut", "pie", "bar_vertical", "bar_horizontal", "gauge"], "default_title": "Requisitos legales por estado", "default_subtitle": "Cumplimiento legal", "icon": "bi-bank2", "color": "green"},

    # Tendencias: líneas en el tiempo o barras.
    {"key": "risks_timeline", "group": "Líneas en el tiempo", "data_kind": "timeline", "label": "Riesgos registrados en el tiempo", "description": "Cantidad mensual de riesgos identificados.", "unit": "", "decimals": 0, "allowed_views": ["line", "bar_vertical", "bar_horizontal"], "default_title": "Riesgos registrados en el tiempo", "default_subtitle": "Últimos períodos con información", "icon": "bi-graph-up-arrow", "color": "orange"},
    {"key": "incidents_timeline", "group": "Líneas en el tiempo", "data_kind": "timeline", "label": "Incidentes registrados en el tiempo", "description": "Cantidad mensual de incidentes registrados.", "unit": "", "decimals": 0, "allowed_views": ["line", "bar_vertical", "bar_horizontal"], "default_title": "Incidentes registrados en el tiempo", "default_subtitle": "Últimos períodos con información", "icon": "bi-graph-up-arrow", "color": "orange"},
    {"key": "vulnerabilities_timeline", "group": "Líneas en el tiempo", "data_kind": "timeline", "label": "Vulnerabilidades identificadas en el tiempo", "description": "Cantidad mensual de vulnerabilidades identificadas.", "unit": "", "decimals": 0, "allowed_views": ["line", "bar_vertical", "bar_horizontal"], "default_title": "Vulnerabilidades en el tiempo", "default_subtitle": "Últimos períodos con información", "icon": "bi-graph-up-arrow", "color": "purple"},
    {"key": "plans_timeline", "group": "Líneas en el tiempo", "data_kind": "timeline", "label": "Planes de acción registrados en el tiempo", "description": "Cantidad mensual de planes de acción creados.", "unit": "", "decimals": 0, "allowed_views": ["line", "bar_vertical", "bar_horizontal"], "default_title": "Planes de acción en el tiempo", "default_subtitle": "Últimos períodos con información", "icon": "bi-graph-up-arrow", "color": "blue"},
    {"key": "security_culture_timeline", "group": "Líneas en el tiempo", "data_kind": "timeline", "label": "Cultura de seguridad en el tiempo", "description": "Evolución mensual del resultado de cultura y formación.", "unit": "%", "decimals": 2, "allowed_views": ["line", "bar_vertical", "bar_horizontal"], "default_title": "Cultura de seguridad en el tiempo", "default_subtitle": "Resultado mensual", "icon": "bi-people-fill", "color": "green"},

    # Indicadores puntuales: velocímetro o aro.
    {"key": "scorecard_average_pct", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Security Scorecard promedio", "description": "Promedio del score de terceros evaluados.", "unit": "%", "decimals": 2, "allowed_views": ["gauge", "donut"], "default_title": "Security Scorecard promedio", "default_subtitle": "Terceros evaluados", "icon": "bi-shield-fill-check", "color": "purple"},
    {"key": "risks_active_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Riesgos activos", "description": "Cantidad de riesgos no archivados.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Riesgos activos", "default_subtitle": "Matriz de riesgos", "icon": "bi-exclamation-diamond-fill", "color": "orange"},
    {"key": "risks_outside_appetite_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Riesgos fuera del apetito", "description": "Cantidad de riesgos residuales que superan el apetito definido.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Riesgos fuera del apetito", "default_subtitle": "Riesgo residual", "icon": "bi-exclamation-triangle-fill", "color": "purple"},
    {"key": "incidents_open_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Incidentes abiertos", "description": "Cantidad de incidentes sin cierre o resolución.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Incidentes abiertos", "default_subtitle": "Gestión de incidentes", "icon": "bi-broadcast-pin", "color": "orange"},
    {"key": "incidents_compliance_pct", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Cumplimiento promedio MTCD/MTIR", "description": "Promedio de cumplimiento global de las métricas de incidentes.", "unit": "%", "decimals": 2, "allowed_views": ["gauge", "donut"], "default_title": "Cumplimiento MTCD / MTIR", "default_subtitle": "Métricas de incidentes", "icon": "bi-stopwatch-fill", "color": "green"},
    {"key": "vulnerabilities_open_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Vulnerabilidades abiertas", "description": "Cantidad de vulnerabilidades abiertas.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Vulnerabilidades abiertas", "default_subtitle": "Gestión de vulnerabilidades", "icon": "bi-bug-fill", "color": "orange"},
    {"key": "vulnerabilities_critical_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Vulnerabilidades críticas abiertas", "description": "Cantidad de vulnerabilidades críticas no cerradas.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Vulnerabilidades críticas", "default_subtitle": "Abiertas", "icon": "bi-radioactive", "color": "purple"},
    {"key": "plans_open_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Planes de acción abiertos", "description": "Cantidad de planes o actividades de mejora abiertas.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Planes de acción abiertos", "default_subtitle": "Seguimiento", "icon": "bi-list-check", "color": "blue"},
    {"key": "plans_overdue_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Planes de acción vencidos", "description": "Planes abiertos cuya fecha propuesta ya venció.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Planes de acción vencidos", "default_subtitle": "Seguimiento", "icon": "bi-calendar-x-fill", "color": "purple"},
    {"key": "legal_noncompliant_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Requisitos legales no cumplidos", "description": "Cantidad de requisitos en incumplimiento.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Requisitos no cumplidos", "default_subtitle": "Cumplimiento legal", "icon": "bi-bank2", "color": "orange"},
    {"key": "providers_high_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Proveedores de criticidad alta", "description": "Cantidad de proveedores clasificados con criticidad alta.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Proveedores de criticidad alta", "default_subtitle": "Evaluación de terceros", "icon": "bi-buildings-fill", "color": "purple"},
    {"key": "security_culture_pct", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Última métrica de cultura de seguridad", "description": "Resultado general más reciente de cultura y formación.", "unit": "%", "decimals": 2, "allowed_views": ["gauge", "donut"], "default_title": "Cultura de seguridad", "default_subtitle": "Último resultado", "icon": "bi-people-fill", "color": "green"},
]

DASHBOARD_DATA_SOURCE_MAP = {item["key"]: dict(item) for item in DASHBOARD_DATA_SOURCE_CATALOG}

DASHBOARD_ALLOWED_COLORS = {
    "blue": "Azul",
    "orange": "Naranja",
    "green": "Verde",
    "purple": "Morado",
}

DASHBOARD_ALLOWED_ICONS = {
    "bi-speedometer2": "Velocímetro",
    "bi-shield-check": "Escudo",
    "bi-robot": "Inteligencia artificial",
    "bi-credit-card-2-front": "PCI-DSS",
    "bi-patch-check-fill": "Cumplimiento",
    "bi-bar-chart-line-fill": "Métricas",
    "bi-graph-up-arrow": "Tendencia",
    "bi-exclamation-triangle-fill": "Alerta",
    "bi-exclamation-diamond-fill": "Riesgos",
    "bi-bug-fill": "Vulnerabilidades",
    "bi-radioactive": "Crítico",
    "bi-broadcast-pin": "Incidentes",
    "bi-stopwatch-fill": "Tiempos",
    "bi-list-check": "Planes de acción",
    "bi-calendar-x-fill": "Vencimiento",
    "bi-bank2": "Requisitos legales",
    "bi-buildings-fill": "Proveedores",
    "bi-people-fill": "Cultura",
    "bi-compass": "NIST",
    "bi-lock-fill": "Datos personales",
    "bi-shield-fill-check": "Scorecard",
}


def _dashboard_default_widget_keys():
    return [item["key"] for item in DASHBOARD_WIDGET_CATALOG if item.get("default_enabled", True)]


def _dashboard_custom_key(widget_id):
    return f"custom:{int(widget_id)}"


def _dashboard_custom_id_from_key(key):
    txt = str(key or "").strip()
    if not txt.startswith("custom:"):
        return None
    try:
        return int(txt.split(":", 1)[1])
    except Exception:
        return None


def _dashboard_dom_id(key):
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", str(key or ""))


def _dashboard_custom_widgets_for_user(user_id):
    if not user_id:
        return []
    try:
        return (
            DashboardCustomWidget.query
            .filter_by(user_id=int(user_id))
            .order_by(DashboardCustomWidget.id.asc())
            .all()
        )
    except Exception as exc:
        print("No se pudieron cargar las visualizaciones personalizadas:", repr(exc))
        return []


def _dashboard_custom_widget_meta(widget):
    source = DASHBOARD_DATA_SOURCE_MAP.get(widget.source_key, {})
    key = _dashboard_custom_key(widget.id)
    view = (widget.widget_type or "gauge").strip().lower()
    kind = "kpi" if view == "kpi" else "chart"
    suffix = widget.suffix if widget.suffix is not None else source.get("unit", "")
    try:
        decimals = max(0, min(int(widget.decimals if widget.decimals is not None else source.get("decimals", 2)), 2))
    except Exception:
        decimals = int(source.get("decimals", 2) or 0)

    return {
        "key": key,
        "dom_id": _dashboard_dom_id(key),
        "kind": kind,
        "group": "Visualizaciones creadas por el usuario",
        "label": source.get("label", widget.title),
        "description": source.get("description", widget.subtitle or "Visualización personalizada."),
        "title": widget.title or source.get("default_title", source.get("label", "Visualización")),
        "subtitle": widget.subtitle or source.get("default_subtitle", ""),
        "icon": widget.icon if widget.icon in DASHBOARD_ALLOWED_ICONS else source.get("icon", "bi-speedometer2"),
        "color": widget.color if widget.color in DASHBOARD_ALLOWED_COLORS else source.get("color", "blue"),
        "source_key": widget.source_key,
        "source_label": source.get("label", widget.source_key),
        "widget_type": view,
        "presentation_label": DASHBOARD_VISUALIZATION_LABELS.get(view, view),
        "target_value": widget.target_value,
        "suffix": suffix or "",
        "decimals": decimals,
        "element_id": f"dash_custom_{widget.id}",
        "image_id": f"dash_custom_chart_{widget.id}",
        "custom": True,
        "custom_id": widget.id,
    }


def _dashboard_available_widget_map(user_id):
    result = {key: dict(meta, dom_id=_dashboard_dom_id(key)) for key, meta in DASHBOARD_WIDGET_MAP.items()}
    for widget in _dashboard_custom_widgets_for_user(user_id):
        meta = _dashboard_custom_widget_meta(widget)
        result[meta["key"]] = meta
    return result


def _dashboard_resolve_widget_meta(user_id, key):
    key = str(key or "").strip()
    if key in DASHBOARD_WIDGET_MAP:
        return dict(DASHBOARD_WIDGET_MAP[key], dom_id=_dashboard_dom_id(key))

    widget_id = _dashboard_custom_id_from_key(key)
    if not widget_id or not user_id:
        return None

    try:
        widget = DashboardCustomWidget.query.filter_by(id=widget_id, user_id=int(user_id)).first()
        return _dashboard_custom_widget_meta(widget) if widget else None
    except Exception:
        return None


def _dashboard_get_selected_keys(user_id):
    defaults = _dashboard_default_widget_keys()
    if not user_id:
        return defaults

    try:
        available = _dashboard_available_widget_map(user_id)
        pref = DashboardPreference.query.filter_by(user_id=int(user_id)).first()
        if not pref:
            return defaults

        raw = json.loads(pref.widget_keys_json or "[]")
        if not isinstance(raw, list):
            return defaults

        selected = []
        seen = set()
        for key in raw:
            key = str(key or "").strip()
            if key in available and key not in seen:
                selected.append(key)
                seen.add(key)
        return selected
    except Exception as exc:
        print("No se pudo cargar la configuración del Centro de Control:", repr(exc))
        return defaults


def _dashboard_save_selected_keys(user_id, selected_keys):
    available = _dashboard_available_widget_map(user_id)
    clean = []
    seen = set()
    for key in selected_keys or []:
        key = str(key or "").strip()
        if key in available and key not in seen:
            clean.append(key)
            seen.add(key)

    pref = DashboardPreference.query.filter_by(user_id=int(user_id)).first()
    if not pref:
        pref = DashboardPreference(user_id=int(user_id))
        db.session.add(pref)
    pref.widget_keys_json = json.dumps(clean, ensure_ascii=False)
    pref.updated_at = datetime.utcnow()
    db.session.commit()
    return clean


def _dashboard_add_key_to_selection(user_id, key):
    selected = _dashboard_get_selected_keys(user_id)
    if key not in selected:
        selected.append(key)
    return _dashboard_save_selected_keys(user_id, selected)


def _dashboard_remove_key_from_selection(user_id, key):
    selected = [item for item in _dashboard_get_selected_keys(user_id) if item != key]
    return _dashboard_save_selected_keys(user_id, selected)


def _dashboard_reset_selected_keys(user_id):
    pref = DashboardPreference.query.filter_by(user_id=int(user_id)).first()
    if pref:
        db.session.delete(pref)
        db.session.commit()
    return _dashboard_default_widget_keys()


def _dashboard_format_value(value, suffix="", decimals=2):
    try:
        number = float(value or 0)
    except Exception:
        number = 0.0
    try:
        decimals = max(0, min(int(decimals), 2))
    except Exception:
        decimals = 2

    if decimals == 0:
        text = f"{int(round(number)):,}".replace(",", ".")
    else:
        text = f"{number:.{decimals}f}"
    suffix = str(suffix or "").strip()
    if suffix == "%":
        return text + "%"
    if suffix:
        return text + " " + suffix
    return text


def _dashboard_prepare_view(selected_keys, payload, user_id=None):
    kpis = []
    charts = []
    custom_payload = payload.get("custom_widgets", {}) or {}

    for key in selected_keys or []:
        meta = _dashboard_resolve_widget_meta(user_id, key)
        if not meta:
            continue

        if meta.get("custom"):
            data = custom_payload.get(key, {}) or {}
            item = dict(meta)
            item["value"] = data.get("value", 0)
            item["display_value"] = data.get("display_value", "")
            if meta.get("kind") == "kpi":
                if not item["display_value"]:
                    item["display_value"] = _dashboard_format_value(item["value"], meta.get("suffix", ""), meta.get("decimals", 2))
                kpis.append(item)
            else:
                item["image"] = data.get("image", "") or _dashboard_empty_chart(item.get("title", "Visualización"), "No hay información disponible")
                charts.append(item)
            continue

        if meta.get("kind") == "kpi":
            item = dict(meta)
            item["value"] = float(payload.get(meta.get("value_key"), 0) or 0)
            item["display_value"] = _dashboard_format_value(item["value"], meta.get("suffix", ""), meta.get("decimals", 2))
            kpis.append(item)
            continue

        item = dict(meta)
        value_key = meta.get("value_key")
        if value_key:
            item["value"] = float(payload.get(value_key, 0) or 0)
            item["display_value"] = _dashboard_format_value(item["value"], meta.get("suffix", "%"), meta.get("decimals", 2))
        else:
            item["value"] = meta.get("display_value", "")
            item["display_value"] = meta.get("display_value", "")
        item["image"] = payload.get(meta.get("image_key"), "") or ""
        charts.append(item)

    return kpis, charts


def _dashboard_latest_pci_data():
    try:
        model = globals().get("PciAnalysisRun")
        if model is not None:
            row = model.query.order_by(model.id.desc()).first()
            if row:
                pct = max(0.0, min(100.0, float(getattr(row, "nivel_promedio_general", 0) or 0)))
                radar = ""
                try:
                    resultados = json.loads(getattr(row, "resultados_json", "{}") or "{}")
                    radar_fn = globals().get("generar_pci_radar_base64")
                    if radar_fn and resultados:
                        radar = radar_fn(resultados) or ""
                except Exception:
                    radar = ""
                return {"pct": pct, "radar_b64": radar}
    except Exception as exc:
        print("No se pudo leer madurez PCI-DSS para el tablero:", repr(exc))
    return {"pct": 0.0, "radar_b64": ""}


def _dashboard_latest_soc2_data():
    try:
        model = globals().get("Soc2MadurezRun")
        if model is not None:
            row = (
                model.query
                .filter(func.upper(model.estado) == "FINALIZADO")
                .order_by(model.id.desc())
                .first()
            ) or model.query.order_by(model.id.desc()).first()
            if row:
                pct = max(0.0, min(100.0, float(getattr(row, "pct_general", 0) or 0)))
                return {"pct": pct, "radar_b64": getattr(row, "radar_overall_b64", None) or ""}
    except Exception as exc:
        print("No se pudo leer madurez SOC 2 para el tablero:", repr(exc))
    return {"pct": 0.0, "radar_b64": ""}


def _dashboard_latest_ai_data():
    db_path = globals().get("AI_MADUREZ_DB_PATH") or os.path.join(app.instance_path, "ai_madurez_42001.db")
    try:
        if not os.path.exists(db_path):
            return {"pct": 0.0, "radar_b64": ""}
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT pct_general, radar_overall_b64
            FROM ai_madurez_runs
            WHERE UPPER(COALESCE(estado, '')) = 'FINALIZADO'
            ORDER BY id DESC LIMIT 1
        """).fetchone()
        if row is None:
            row = conn.execute("""
                SELECT pct_general, radar_overall_b64
                FROM ai_madurez_runs
                ORDER BY id DESC LIMIT 1
            """).fetchone()
        conn.close()
        if row:
            pct = max(0.0, min(100.0, float(row["pct_general"] or 0)))
            return {"pct": pct, "radar_b64": row["radar_overall_b64"] or ""}
    except Exception as exc:
        print("No se pudo leer madurez de Gestión de IA para el tablero:", repr(exc))
    return {"pct": 0.0, "radar_b64": ""}


def _dashboard_latest_data_maturity_data():
    try:
        model = globals().get("DatosMadurezRun")
        if model is None:
            return {"pct": 0.0, "radar_b64": ""}
        row = (
            model.query
            .filter(func.upper(model.estado) == "FINALIZADO")
            .order_by(model.id.desc())
            .first()
        ) or model.query.order_by(model.id.desc()).first()
        if not row:
            return {"pct": 0.0, "radar_b64": ""}
        pct = max(0.0, min(100.0, float(getattr(row, "pct_general", 0) or 0)))
        radar = ""
        try:
            resumen = json.loads(getattr(row, "resumen_json", "{}") or "{}")
            radar_fn = globals().get("generar_radar_datos_base64")
            if radar_fn and resumen:
                radar = radar_fn(resumen) or ""
        except Exception:
            radar = ""
        return {"pct": pct, "radar_b64": radar}
    except Exception as exc:
        print("No se pudo leer madurez de Datos Personales para el tablero:", repr(exc))
        return {"pct": 0.0, "radar_b64": ""}


def _dashboard_maturity_data(source_key):
    if source_key == "maturity_iso_pct":
        data = _dashboard_latest_iso_data() or {}
        return {"pct": float(data.get("pct", 0) or 0), "radar_b64": data.get("radar_b64", "") or ""}
    if source_key == "maturity_nist_pct":
        data = _dashboard_latest_nist_data() or {}
        return {"pct": float(data.get("pct", 0) or 0), "radar_b64": data.get("radar_b64", "") or ""}
    if source_key == "maturity_data_pct":
        return _dashboard_latest_data_maturity_data()
    if source_key == "maturity_pci_pct":
        return _dashboard_latest_pci_data()
    if source_key == "maturity_soc2_pct":
        return _dashboard_latest_soc2_data()
    if source_key == "maturity_ai_pct":
        return _dashboard_latest_ai_data()
    return {"pct": 0.0, "radar_b64": ""}


def _dashboard_risk_rank(raw):
    txt = str(raw or "").strip().upper()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    if "EXTREMO" in txt or "CRITICO" in txt:
        return 5
    if "MUY ALTO" in txt:
        return 4
    if re.search(r"\bALTO\b", txt):
        return 3
    if "MODERADO" in txt or "MEDIO" in txt:
        return 2
    if "BAJO" in txt:
        return 1
    return 0


def _dashboard_active_risks():
    try:
        return [r for r in Riesgo.query.all() if not bool(getattr(r, "archivado", False))]
    except Exception:
        return []


def _dashboard_metric_value(source_key, user_id=None):
    source_key = str(source_key or "").strip()
    try:
        if source_key.startswith("maturity_"):
            return float((_dashboard_maturity_data(source_key) or {}).get("pct", 0) or 0)
        if source_key == "scorecard_average_pct":
            return float(_dashboard_latest_scorecard_terceros_pct() or 0)
        if source_key == "risks_active_count":
            return float(len(_dashboard_active_risks()))
        if source_key == "risks_outside_appetite_count":
            risks = _dashboard_active_risks()
            try:
                cfg = MetricConfigRiesgos.query.first()
                appetite_rank = _dashboard_risk_rank(getattr(cfg, "apetito_residual_definido", "") if cfg else "") or 2
            except Exception:
                appetite_rank = 2
            return float(sum(1 for r in risks if _dashboard_risk_rank(getattr(r, "riesgo_residual", "")) > appetite_rank))
        if source_key == "incidents_open_count":
            db_path = globals().get("INCIDENTES_DB_PATH") or os.path.join(app.instance_path, "incidentes.db")
            if not os.path.exists(db_path):
                return 0.0
            conn = sqlite3.connect(db_path)
            row = conn.execute("""
                SELECT COUNT(*) FROM registro_incidentes
                WHERE UPPER(TRIM(COALESCE(estado, ''))) NOT IN
                      ('CERRADO', 'CERRADA', 'CLOSED', 'RESUELTO', 'RESUELTA')
            """).fetchone()
            conn.close()
            return float(row[0] if row else 0)
        if source_key == "incidents_compliance_pct":
            model = globals().get("MetricaIncidente")
            if model is None:
                return 0.0
            value = db.session.query(func.avg(model.cumplimiento_global)).filter(model.cumplimiento_global.isnot(None)).scalar()
            return float(value or 0)
        if source_key in {"vulnerabilities_open_count", "vulnerabilities_critical_count"}:
            items = VulnerabilidadRegistro.query.all()
            open_items = []
            for item in items:
                estado = str(getattr(item, "estado", "") or "").strip().upper()
                if estado not in {"CERRADO", "CERRADA", "CLOSED", "RESUELTO", "RESUELTA"}:
                    open_items.append(item)
            if source_key == "vulnerabilities_open_count":
                return float(len(open_items))
            return float(sum(1 for item in open_items if "CRIT" in str(getattr(item, "clasificacion", "") or "").upper()))
        if source_key in {"plans_open_count", "plans_overdue_count"}:
            # IMPORTANTE: usar la MISMA fuente del módulo web /planes_accion.
            # Antes el dashboard/mobile consultaba MejoraPlanRegistro (mejora_planes),
            # mientras el módulo real de Planes de Acción usa ContinuousActionPlan
            # en instance/planes_accion.db. Esa diferencia generaba conteos incongruentes.
            items = ContinuousActionPlan.query.order_by(ContinuousActionPlan.id.desc()).limit(10000).all()
            today = date.today()
            effective = [pa_effective_status(item, today) for item in items]

            if source_key == "plans_open_count":
                # Todo plan que todavía requiere seguimiento, incluidos En proceso,
                # Pendiente y Vencido. Se excluyen únicamente estados cerrados/cancelados.
                return float(sum(
                    1 for status in effective
                    if not pa_status_closed(status)
                ))

            return float(sum(1 for status in effective if status == "Vencido"))
        if source_key == "legal_noncompliant_count":
            return float(sum(1 for item in RequisitoLegal.query.all() if "NO CUMPLE" in str(getattr(item, "estado", "") or "").upper() or "INCUMPLE" in str(getattr(item, "estado", "") or "").upper()))
        if source_key == "providers_high_count":
            return float(sum(1 for item in ProveedorEvaluacion.query.all() if "ALTA" in str(getattr(item, "criticidad_texto", "") or "").upper()))
        if source_key == "security_culture_pct":
            model = globals().get("MetricasCultura")
            if model is None:
                return 0.0
            row = model.query.order_by(model.anio.desc(), model.mes.desc(), model.id.desc()).first()
            return float(getattr(row, "resultado_meta_general", 0) or 0) if row else 0.0
    except Exception as exc:
        print(f"No se pudo calcular la fuente {source_key}:", repr(exc))
    return 0.0


def _dashboard_parse_date(raw):
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        if isinstance(raw, date):
            return datetime.combine(raw, datetime.min.time())
    except Exception:
        pass
    txt = str(raw).strip()
    if not txt:
        return None
    txt_iso = txt.replace("Z", "+00:00")
    try:
        value = datetime.fromisoformat(txt_iso)
        if getattr(value, "tzinfo", None):
            value = value.replace(tzinfo=None)
        return value
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(txt[:19], fmt)
        except Exception:
            continue
    return None


_DASHBOARD_MONTHS_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _dashboard_month_label(key):
    try:
        year, month = [int(x) for x in str(key).split("-")[:2]]
        return f"{_DASHBOARD_MONTHS_ES[month - 1]} {year}"
    except Exception:
        return str(key)


def _dashboard_monthly_count_series(values, limit=12):
    counts = Counter()
    for raw in values or []:
        dt_value = _dashboard_parse_date(raw)
        if dt_value:
            counts[dt_value.strftime("%Y-%m")] += 1
    keys = sorted(counts.keys())[-max(1, int(limit or 12)):]
    return [_dashboard_month_label(k) for k in keys], [float(counts[k]) for k in keys]


def _dashboard_distribution_risks():
    labels = ["Bajo", "Medio", "Alto", "Muy Alto", "Extremo"]
    values = {label: 0 for label in labels}
    for item in _dashboard_active_risks():
        rank = _dashboard_risk_rank(getattr(item, "riesgo_residual", ""))
        if rank == 1:
            values["Bajo"] += 1
        elif rank == 2:
            values["Medio"] += 1
        elif rank == 3:
            values["Alto"] += 1
        elif rank == 4:
            values["Muy Alto"] += 1
        elif rank == 5:
            values["Extremo"] += 1
    return labels, [float(values[label]) for label in labels]


def _dashboard_incident_db_rows(columns_candidates):
    db_path = globals().get("INCIDENTES_DB_PATH") or os.path.join(app.instance_path, "incidentes.db")
    if not os.path.exists(db_path):
        return [], None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(registro_incidentes)").fetchall()]
        column = next((candidate for candidate in columns_candidates if candidate in cols), None)
        if not column:
            return [], None
        rows = conn.execute(f"SELECT {column} AS value FROM registro_incidentes WHERE {column} IS NOT NULL AND TRIM(CAST({column} AS TEXT)) <> ''").fetchall()
        return rows, column
    finally:
        conn.close()


def _dashboard_distribution_incidents():
    labels = ["Bajo", "Medio", "Alto", "Crítico"]
    values = {label: 0 for label in labels}
    rows, _ = _dashboard_incident_db_rows(["clasificacion_incidente", "clasificacion", "criticidad", "nivel", "tipo_incidente", "categoria_incidente"])
    for row in rows:
        txt = unicodedata.normalize("NFKD", str(row["value"] or "").upper())
        txt = "".join(c for c in txt if not unicodedata.combining(c))
        if "CRIT" in txt:
            values["Crítico"] += 1
        elif "ALTO" in txt:
            values["Alto"] += 1
        elif "MEDIO" in txt or "MEDIA" in txt or "MODER" in txt:
            values["Medio"] += 1
        elif "BAJO" in txt or "BAJA" in txt:
            values["Bajo"] += 1
    return labels, [float(values[label]) for label in labels]


def _dashboard_distribution_vulnerabilities():
    labels = ["Baja", "Media", "Alta", "Crítica"]
    values = {label: 0 for label in labels}
    try:
        items = VulnerabilidadRegistro.query.all()
    except Exception:
        items = []
    for item in items:
        candidates = [
            getattr(item, "clasificacion", None), getattr(item, "severidad", None),
            getattr(item, "criticidad", None), getattr(item, "nivel_criticidad", None),
            getattr(item, "criticidad_vulnerabilidad", None), getattr(item, "impacto", None),
            getattr(item, "prioridad", None),
        ]
        txt = " ".join(str(v or "") for v in candidates).upper()
        txt = unicodedata.normalize("NFKD", txt)
        txt = "".join(c for c in txt if not unicodedata.combining(c))
        if "CRIT" in txt:
            values["Crítica"] += 1
        elif "ALTA" in txt or "HIGH" in txt:
            values["Alta"] += 1
        elif "MEDIA" in txt or "MEDIUM" in txt or "MODER" in txt:
            values["Media"] += 1
        elif "BAJA" in txt or "LOW" in txt or "INFO" in txt:
            values["Baja"] += 1
    return labels, [float(values[label]) for label in labels]


def _dashboard_distribution_providers():
    labels = ["Muy baja", "Baja", "Media", "Alta"]
    values = {label: 0 for label in labels}
    try:
        items = ProveedorEvaluacion.query.all()
    except Exception:
        items = []
    for item in items:
        txt = str(getattr(item, "criticidad_texto", "") or "").lower()
        if "muy baja" in txt:
            values["Muy baja"] += 1
        elif "baja" in txt:
            values["Baja"] += 1
        elif "media" in txt:
            values["Media"] += 1
        elif "alta" in txt:
            values["Alta"] += 1
    return labels, [float(values[label]) for label in labels]


def _dashboard_distribution_plans():
    # Misma fuente y mismo estado efectivo del módulo /planes_accion.
    labels = ["Abierto", "En proceso", "Vencido", "Cerrado", "Cancelado", "Otros"]
    values = {label: 0 for label in labels}
    try:
        items = ContinuousActionPlan.query.order_by(ContinuousActionPlan.id.desc()).limit(10000).all()
        today = date.today()
    except Exception:
        items = []
        today = date.today()

    for item in items:
        status = pa_effective_status(item, today)
        if status in values and status != "Otros":
            values[status] += 1
        else:
            values["Otros"] += 1
    return labels, [float(values[label]) for label in labels]


def _dashboard_distribution_legal():
    labels = ["Cumple", "Parcial", "No cumple", "Sin estado"]
    values = {label: 0 for label in labels}
    try:
        items = RequisitoLegal.query.all()
    except Exception:
        items = []
    for item in items:
        txt = str(getattr(item, "estado", "") or "").strip().upper()
        if txt == "CUMPLE":
            values["Cumple"] += 1
        elif "PARCIAL" in txt:
            values["Parcial"] += 1
        elif "NO CUMPLE" in txt or "INCUMPLE" in txt:
            values["No cumple"] += 1
        else:
            values["Sin estado"] += 1
    return labels, [float(values[label]) for label in labels]


def _dashboard_timeline_risks():
    return _dashboard_monthly_count_series([getattr(item, "fecha_identificacion", None) for item in _dashboard_active_risks()])


def _dashboard_timeline_incidents():
    rows, _ = _dashboard_incident_db_rows(["fecha_registro", "fecha_incidente", "fecha_reporte", "created_at", "fecha", "fecha_creacion"])
    return _dashboard_monthly_count_series([row["value"] for row in rows])


def _dashboard_timeline_vulnerabilities():
    try:
        items = VulnerabilidadRegistro.query.all()
    except Exception:
        items = []
    values = [getattr(item, "fecha_identificacion", None) or getattr(item, "created_at", None) for item in items]
    return _dashboard_monthly_count_series(values)


def _dashboard_timeline_plans():
    try:
        items = ContinuousActionPlan.query.order_by(ContinuousActionPlan.id.asc()).limit(10000).all()
    except Exception:
        items = []
    values = [getattr(item, "created_at", None) or getattr(item, "due_date", None) for item in items]
    return _dashboard_monthly_count_series(values)


def _dashboard_timeline_culture():
    model = globals().get("MetricasCultura")
    if model is None:
        return [], []
    try:
        rows = model.query.order_by(model.anio.asc(), model.mes.asc(), model.id.asc()).all()
    except Exception:
        return [], []
    values_by_key = {}
    for row in rows:
        try:
            year = int(getattr(row, "anio", 0) or 0)
            month = int(getattr(row, "mes", 0) or 0)
            if year > 0 and 1 <= month <= 12:
                values_by_key[f"{year:04d}-{month:02d}"] = float(getattr(row, "resultado_meta_general", 0) or 0)
        except Exception:
            continue
    keys = sorted(values_by_key.keys())[-12:]
    return [_dashboard_month_label(key) for key in keys], [values_by_key[key] for key in keys]


_DASHBOARD_DISTRIBUTION_SOURCES = {
    "risks_residual_distribution": _dashboard_distribution_risks,
    "incidents_classification_distribution": _dashboard_distribution_incidents,
    "vulnerabilities_severity_distribution": _dashboard_distribution_vulnerabilities,
    "providers_criticality_distribution": _dashboard_distribution_providers,
    "plans_status_distribution": _dashboard_distribution_plans,
    "legal_status_distribution": _dashboard_distribution_legal,
}

_DASHBOARD_TIMELINE_SOURCES = {
    "risks_timeline": _dashboard_timeline_risks,
    "incidents_timeline": _dashboard_timeline_incidents,
    "vulnerabilities_timeline": _dashboard_timeline_vulnerabilities,
    "plans_timeline": _dashboard_timeline_plans,
    "security_culture_timeline": _dashboard_timeline_culture,
}


def _dashboard_source_snapshot(source_key, user_id=None, cache=None):
    if cache is not None and source_key in cache:
        return cache[source_key]
    meta = DASHBOARD_DATA_SOURCE_MAP.get(source_key, {})
    kind = meta.get("data_kind", "scalar")
    result = {
        "source_key": source_key,
        "data_kind": kind,
        "value": 0.0,
        "unit": meta.get("unit", ""),
        "decimals": int(meta.get("decimals", 2) or 0),
        "labels": [],
        "values": [],
        "radar_b64": "",
        "meta": meta,
    }
    try:
        if kind == "maturity":
            data = _dashboard_maturity_data(source_key)
            result["value"] = float(data.get("pct", 0) or 0)
            result["radar_b64"] = data.get("radar_b64", "") or ""
        elif kind == "distribution":
            labels, values = _DASHBOARD_DISTRIBUTION_SOURCES.get(source_key, lambda: ([], []))()
            result["labels"] = list(labels or [])
            result["values"] = [float(v or 0) for v in (values or [])]
            result["value"] = float(sum(result["values"]))
        elif kind == "timeline":
            labels, values = _DASHBOARD_TIMELINE_SOURCES.get(source_key, lambda: ([], []))()
            result["labels"] = list(labels or [])
            result["values"] = [float(v or 0) for v in (values or [])]
            result["value"] = float(result["values"][-1]) if result["values"] else 0.0
        else:
            result["value"] = float(_dashboard_metric_value(source_key, user_id) or 0)
    except Exception as exc:
        print(f"No se pudo construir la fuente visual {source_key}:", repr(exc))
    if cache is not None:
        cache[source_key] = result
    return result


def _dashboard_metric_snapshot(source_key, user_id=None, cache=None):
    return _dashboard_source_snapshot(source_key, user_id, cache)


def _dashboard_nice_scale(value):
    try:
        value = max(0.0, float(value or 0))
    except Exception:
        value = 0.0
    if value <= 0:
        return 10.0
    magnitude = 10 ** math.floor(math.log10(value))
    for factor in (1, 2, 5, 10, 20):
        candidate = factor * magnitude
        if candidate >= value * 1.15:
            return float(candidate)
    return float(10 * magnitude)


def _dashboard_scalar_ring_b64(value, title="", subtitle="", unit="", decimals=2):
    try:
        value = max(0.0, float(value or 0))
    except Exception:
        value = 0.0
    scale = 100.0 if unit == "%" else _dashboard_nice_scale(value)
    current = min(value, scale)
    remaining = max(0.0, scale - current)
    fig, ax = plt.subplots(figsize=(8.0, 5.6))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    ax.pie(
        [current, remaining] if scale > 0 else [0, 1],
        startangle=90,
        counterclock=False,
        colors=["#0b5fa5", "#e7edf4"],
        wedgeprops=dict(width=0.34, edgecolor="white", linewidth=2),
    )
    display = _dashboard_format_value(value, unit, decimals)
    ax.text(0, 0.08, display, ha="center", va="center", fontsize=25, fontweight="bold", color="#0b1220")
    ax.text(0, -0.14, "Valor actual", ha="center", va="center", fontsize=10, color="#64748b")
    if title:
        ax.set_title(title, fontsize=15, fontweight="bold", color="#0b1220", pad=12)
    if subtitle:
        fig.text(0.5, 0.03, subtitle, ha="center", fontsize=10, color="#4b5563")
    ax.set_aspect("equal")
    return _dashboard_fig_to_b64(fig)


def _dashboard_pie_b64(labels, values, title="", subtitle=""):
    labels = list(labels or [])
    values = [float(v or 0) for v in (values or [])]
    if not labels or not values or sum(values) <= 0:
        return _dashboard_empty_chart(title or "Sin datos", "No hay información para graficar")
    palette = ["#087c3d", "#84cc16", "#d39b00", "#c95508", "#b91c1c", "#5521a8", "#087ab8"]
    fig, ax = plt.subplots(figsize=(8.0, 5.6))
    fig.patch.set_facecolor("#ffffff")
    wedges, _, autotexts = ax.pie(
        values,
        labels=None,
        autopct=lambda pct: f"{pct:.0f}%" if pct >= 4 else "",
        startangle=90,
        counterclock=False,
        colors=[palette[i % len(palette)] for i in range(len(labels))],
        wedgeprops=dict(edgecolor="white", linewidth=2),
    )
    for txt in autotexts:
        txt.set_fontsize(9)
        txt.set_fontweight("bold")
    ax.legend(wedges, [f"{label}: {_dashboard_format_value(value, '', 0)}" for label, value in zip(labels, values)], loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False, fontsize=9)
    if title:
        ax.set_title(title, fontsize=15, fontweight="bold", color="#0b1220", pad=12)
    if subtitle:
        fig.text(0.5, 0.03, subtitle, ha="center", fontsize=10, color="#4b5563")
    ax.set_aspect("equal")
    return _dashboard_fig_to_b64(fig)


def _dashboard_bar_b64(labels, values, title="", subtitle="", horizontal=False, unit=""):
    labels = [str(label) for label in (labels or [])]
    values = [float(v or 0) for v in (values or [])]
    if not labels or not values:
        return _dashboard_empty_chart(title or "Sin datos", "No hay información para graficar")
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    positions = list(range(len(labels)))
    palette = ["#0b5fa5", "#16855b", "#d48b0b", "#b44747", "#6c4bc2", "#2386b7"]
    colors = [palette[i % len(palette)] for i in positions]
    if horizontal:
        bars = ax.barh(positions, values, color=colors)
        ax.set_yticks(positions, labels)
        ax.invert_yaxis()
        for bar, value in zip(bars, values):
            ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, "  " + _dashboard_format_value(value, unit, 2 if unit == "%" else 0), va="center", fontsize=9, fontweight="bold")
        ax.grid(axis="x", alpha=.20)
    else:
        bars = ax.bar(positions, values, color=colors)
        ax.set_xticks(positions, labels, rotation=25, ha="right")
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), _dashboard_format_value(value, unit, 2 if unit == "%" else 0), ha="center", va="bottom", fontsize=9, fontweight="bold")
        ax.grid(axis="y", alpha=.20)
    ax.spines[["top", "right"]].set_visible(False)
    if title:
        ax.set_title(title, fontsize=15, fontweight="bold", color="#0b1220", pad=12)
    if subtitle:
        fig.text(0.5, 0.01, subtitle, ha="center", fontsize=9.5, color="#4b5563")
    fig.tight_layout(rect=[0, .05, 1, 1])
    return _dashboard_fig_to_b64(fig)


def _dashboard_line_b64(labels, values, title="", subtitle="", unit=""):
    labels = [str(label) for label in (labels or [])]
    values = [float(v or 0) for v in (values or [])]
    if not labels or not values:
        return _dashboard_empty_chart(title or "Sin datos", "No hay información histórica para graficar")
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    x = list(range(len(labels)))
    ax.plot(x, values, marker="o", linewidth=2.5, markersize=6, color="#0b5fa5")
    ax.fill_between(x, values, [0] * len(values), alpha=.10, color="#0b5fa5")
    ax.set_xticks(x, labels, rotation=28, ha="right")
    ax.grid(axis="y", alpha=.22)
    ax.spines[["top", "right"]].set_visible(False)
    for xi, value in zip(x, values):
        ax.annotate(_dashboard_format_value(value, unit, 2 if unit == "%" else 0), (xi, value), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8.5, fontweight="bold")
    if title:
        ax.set_title(title, fontsize=15, fontweight="bold", color="#0b1220", pad=12)
    if subtitle:
        fig.text(0.5, 0.01, subtitle, ha="center", fontsize=9.5, color="#4b5563")
    fig.tight_layout(rect=[0, .05, 1, 1])
    return _dashboard_fig_to_b64(fig)


def _dashboard_render_custom_visualization(snapshot, view, title, subtitle):
    view = str(view or "gauge").strip().lower()
    kind = snapshot.get("data_kind", "scalar")
    unit = snapshot.get("unit", "")
    decimals = snapshot.get("decimals", 2)
    value = float(snapshot.get("value", 0) or 0)
    labels = snapshot.get("labels", []) or []
    values = snapshot.get("values", []) or []

    if view == "radar":
        return snapshot.get("radar_b64", "") or _dashboard_empty_chart(title, "No se encontró información por dominio para generar la araña")
    if view == "gauge":
        if unit == "%":
            gauge_pct = max(0.0, min(100.0, value))
            gauge_subtitle = subtitle
        else:
            scale = _dashboard_nice_scale(value)
            gauge_pct = max(0.0, min(100.0, (value / scale * 100.0) if scale > 0 else 0.0))
            gauge_subtitle = f"{subtitle} · Valor actual: {_dashboard_format_value(value, unit, decimals)}".strip(" ·")
        return _dashboard_gauge_b64(gauge_pct, title, gauge_subtitle)
    if view == "donut":
        if kind == "distribution":
            return _dashboard_donut_b64(labels, values, title=title, subtitle=subtitle)
        return _dashboard_scalar_ring_b64(value, title, subtitle, unit, decimals)
    if view == "pie":
        return _dashboard_pie_b64(labels, values, title, subtitle)
    if view == "bar_vertical":
        if not labels:
            labels, values = [snapshot.get("meta", {}).get("label", "Valor")], [value]
        return _dashboard_bar_b64(labels, values, title, subtitle, horizontal=False, unit=unit if kind == "timeline" else "")
    if view == "bar_horizontal":
        if not labels:
            labels, values = [snapshot.get("meta", {}).get("label", "Valor")], [value]
        return _dashboard_bar_b64(labels, values, title, subtitle, horizontal=True, unit=unit if kind == "timeline" else "")
    if view == "line":
        return _dashboard_line_b64(labels, values, title, subtitle, unit=unit)
    return ""


def _dashboard_custom_widget_form_data(form):
    source_key = str(form.get("source_key") or "").strip()
    source = DASHBOARD_DATA_SOURCE_MAP.get(source_key)
    if not source:
        return None, "Seleccione una fuente de datos válida."

    widget_type = str(form.get("widget_type") or "").strip().lower()
    allowed = list(source.get("allowed_views", []))
    if widget_type not in allowed:
        return None, "Seleccione una presentación válida para la fuente de datos."

    return {
        "title": source.get("default_title") or source.get("label") or "Visualización",
        "subtitle": source.get("default_subtitle") or "",
        "source_key": source_key,
        "widget_type": widget_type,
        "icon": source.get("icon", "bi-speedometer2"),
        "color": source.get("color", "blue"),
        "target_value": None,
        "suffix": source.get("unit", ""),
        "decimals": int(source.get("decimals", 2) or 0),
    }, None


def _dashboard_build_payload(selected_keys=None, user_id=None):
    if selected_keys is None:
        selected_keys = _dashboard_default_widget_keys()

    selected = {key for key in selected_keys if key in DASHBOARD_WIDGET_MAP}
    selected_custom = [key for key in selected_keys if _dashboard_custom_id_from_key(key)]

    payload = {
        "iso_radar_b64": "", "iso_pct": 0.0,
        "nist_radar_b64": "", "nist_pct": 0.0,
        "datos_gauge_b64": "", "datos_pct": 0.0,
        "scorecard_terceros_pct": 0.0,
        "pci_pct": 0.0, "pci_gauge_b64": "",
        "soc2_pct": 0.0, "soc2_radar_b64": "",
        "ai_maturity_pct": 0.0, "ai_radar_b64": "",
        "risks_active_count": 0.0,
        "risks_outside_appetite_count": 0.0,
        "incidents_open_count": 0.0,
        "incidents_compliance_pct": 0.0,
        "vulnerabilities_open_count": 0.0,
        "vulnerabilities_critical_count": 0.0,
        "plans_open_count": 0.0,
        "plans_overdue_count": 0.0,
        "legal_noncompliant_count": 0.0,
        "providers_high_count": 0.0,
        "security_culture_pct": 0.0,
        "riesgos_b64": "", "incidentes_b64": "", "vulnerabilidades_b64": "",
        "proveedores_criticidad_b64": "", "planes_accion_estado_b64": "",
        "requisitos_legales_estado_b64": "", "custom_widgets": {},
    }

    if selected.intersection({"kpi_iso", "chart_iso"}):
        iso_data = _dashboard_latest_iso_data()
        payload["iso_radar_b64"] = iso_data["radar_b64"] if "chart_iso" in selected else ""
        payload["iso_pct"] = round(float(iso_data["pct"] or 0), 2)
    if selected.intersection({"kpi_nist", "chart_nist"}):
        nist_data = _dashboard_latest_nist_data()
        payload["nist_radar_b64"] = nist_data["radar_b64"] if "chart_nist" in selected else ""
        payload["nist_pct"] = round(float(nist_data["pct"] or 0), 2)
    if selected.intersection({"kpi_datos", "chart_datos"}):
        datos_pct = _dashboard_latest_datos_pct()
        payload["datos_pct"] = round(float(datos_pct or 0), 2)
        if "chart_datos" in selected:
            payload["datos_gauge_b64"] = _dashboard_gauge_b64(datos_pct, "Cumplimiento", "Protección de datos personales")
    if "kpi_scorecard" in selected:
        payload["scorecard_terceros_pct"] = round(float(_dashboard_latest_scorecard_terceros_pct() or 0), 2)
    if selected.intersection({"kpi_pci", "chart_pci"}):
        pci_data = _dashboard_latest_pci_data()
        payload["pci_pct"] = round(float(pci_data.get("pct", 0) or 0), 2)
        if "chart_pci" in selected:
            payload["pci_gauge_b64"] = _dashboard_gauge_b64(payload["pci_pct"], "Madurez", "PCI-DSS")
    if selected.intersection({"kpi_soc2", "chart_soc2"}):
        soc2_data = _dashboard_latest_soc2_data()
        payload["soc2_pct"] = round(float(soc2_data.get("pct", 0) or 0), 2)
        if "chart_soc2" in selected:
            payload["soc2_radar_b64"] = soc2_data.get("radar_b64") or _dashboard_gauge_b64(payload["soc2_pct"], "Madurez", "SOC 2")
    if selected.intersection({"kpi_ai", "chart_ai"}):
        ai_data = _dashboard_latest_ai_data()
        payload["ai_maturity_pct"] = round(float(ai_data.get("pct", 0) or 0), 2)
        if "chart_ai" in selected:
            payload["ai_radar_b64"] = ai_data.get("radar_b64") or _dashboard_gauge_b64(payload["ai_maturity_pct"], "Madurez", "ISO/IEC 42001")

    metric_to_payload = {
        "kpi_riesgos_activos": ("risks_active_count", "risks_active_count"),
        "kpi_riesgos_fuera_apetito": ("risks_outside_appetite_count", "risks_outside_appetite_count"),
        "kpi_incidentes_abiertos": ("incidents_open_count", "incidents_open_count"),
        "kpi_incidentes_cumplimiento": ("incidents_compliance_pct", "incidents_compliance_pct"),
        "kpi_vulnerabilidades_abiertas": ("vulnerabilities_open_count", "vulnerabilities_open_count"),
        "kpi_vulnerabilidades_criticas": ("vulnerabilities_critical_count", "vulnerabilities_critical_count"),
        "kpi_planes_abiertos": ("plans_open_count", "plans_open_count"),
        "kpi_planes_vencidos": ("plans_overdue_count", "plans_overdue_count"),
        "kpi_requisitos_no_cumple": ("legal_noncompliant_count", "legal_noncompliant_count"),
        "kpi_proveedores_alta": ("providers_high_count", "providers_high_count"),
        "kpi_cultura_seguridad": ("security_culture_pct", "security_culture_pct"),
    }
    source_cache = {}
    for widget_key, (payload_key, source_key) in metric_to_payload.items():
        if widget_key in selected:
            payload[payload_key] = _dashboard_metric_snapshot(source_key, user_id, source_cache)["value"]

    if "chart_riesgos" in selected:
        payload["riesgos_b64"] = _dashboard_riesgos_residuales_chart()
    if "chart_incidentes" in selected:
        payload["incidentes_b64"] = _dashboard_incidentes_chart()
    if "chart_vulnerabilidades" in selected:
        payload["vulnerabilidades_b64"] = _dashboard_vulnerabilidades_chart()
    if "chart_proveedores" in selected:
        payload["proveedores_criticidad_b64"] = _dashboard_proveedores_criticidad_chart()
    if "chart_planes_accion" in selected:
        payload["planes_accion_estado_b64"] = _dashboard_planes_accion_estado_chart()
    if "chart_requisitos_legales" in selected:
        payload["requisitos_legales_estado_b64"] = _dashboard_requisitos_legales_estado_chart()

    custom_map = {_dashboard_custom_key(widget.id): widget for widget in _dashboard_custom_widgets_for_user(user_id)}
    for key in selected_custom:
        widget = custom_map.get(key)
        if not widget:
            continue
        meta = _dashboard_custom_widget_meta(widget)
        snapshot = _dashboard_source_snapshot(widget.source_key, user_id, source_cache)
        value = float(snapshot.get("value", 0) or 0)
        data_kind = snapshot.get("data_kind", "scalar")
        if data_kind == "distribution":
            display_value = f"Total {_dashboard_format_value(value, '', 0)}"
        elif data_kind == "timeline":
            display_value = "Último: " + _dashboard_format_value(value, snapshot.get("unit", ""), snapshot.get("decimals", 0))
        else:
            display_value = _dashboard_format_value(value, snapshot.get("unit", ""), snapshot.get("decimals", 2))
        image = ""
        if meta.get("kind") == "chart":
            image = _dashboard_render_custom_visualization(snapshot, widget.widget_type, widget.title, widget.subtitle or "")
        payload["custom_widgets"][key] = {
            "value": value,
            "display_value": display_value,
            "image": image,
            "source_key": widget.source_key,
            "widget_type": widget.widget_type,
        }

    return payload


def _dashboard_latest_datos_pct():
    try:
        run = DatosMadurezRun.query.order_by(DatosMadurezRun.id.desc()).first()
        if run:
            return float(run.pct_general or 0)
    except Exception:
        pass
    return 0.0

def _dashboard_latest_scorecard_terceros_pct():
    """
    Score promedio de Security Scorecard de Terceros.
    Fuente: instance/scorecard_proponentes.db
    Tabla: scorecard_proponentes_runs
    """
    try:
        db_path = os.path.join(app.instance_path, "scorecard_proponentes.db")

        if not os.path.exists(db_path):
            return 0.0

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT AVG(score_total) AS promedio
            FROM scorecard_proponentes_runs
            WHERE estado = 'finalizado'
              AND score_total IS NOT NULL
        """)

        row = cur.fetchone()
        conn.close()

        return round(float(row["promedio"] or 0), 2)

    except Exception as e:
        print("ERROR DASHBOARD SCORECARD TERCEROS:", repr(e))
        return 0.0

def _dashboard_riesgos_residuales_chart():
    try:
        items = Riesgo.query.order_by(Riesgo.id.desc()).all()
    except Exception:
        try:
            items = RiesgoRegistro.query.order_by(RiesgoRegistro.id.desc()).all()
        except Exception:
            items = []

    niveles = ["Bajo", "Medio", "Alto", "Muy Alto", "Extremo"]
    conteos = {k: 0 for k in niveles}

    for it in items:
        raw = (
            getattr(it, "riesgo_residual", None)
            or getattr(it, "nivel_riesgo_residual", None)
            or getattr(it, "riesgo_residual_nivel", None)
            or ""
        )
        txt = str(raw).upper().strip()

        if "EXTREMO" in txt:
            conteos["Extremo"] += 1
        elif "MUY ALTO" in txt:
            conteos["Muy Alto"] += 1
        elif re.search(r"\bALTO\b", txt):
            conteos["Alto"] += 1
        elif "MEDIO" in txt or "MODERADO" in txt:
            conteos["Medio"] += 1
        elif "BAJO" in txt:
            conteos["Bajo"] += 1

    return _dashboard_donut_b64(
        niveles,
        [conteos[n] for n in niveles],
        title="Riesgos residuales",
        subtitle="Distribución por nivel"
    )

def _obtener_columnas_sqlite(db_path, tabla):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({tabla})")
        cols = [row[1] for row in cur.fetchall()]
        conn.close()
        return cols
    except Exception as e:
        print(f"ERROR obteniendo columnas de {tabla}: {e}")
        return []

def _dashboard_incidentes_chart():
    buckets = ["Bajo", "Medio", "Alto", "Crítico"]
    conteos = {k: 0 for k in buckets}

    def norm(txt):
        txt = str(txt or "").strip().upper()
        txt = (
            txt.replace("Á", "A")
               .replace("É", "E")
               .replace("Í", "I")
               .replace("Ó", "O")
               .replace("Ú", "U")
        )
        return txt

    def acumular_clasificacion(raw):
        txt = norm(raw)
        if not txt:
            return

        if "CRIT" in txt:
            conteos["Crítico"] += 1
        elif "ALTO" in txt:
            conteos["Alto"] += 1
        elif "MEDIO" in txt or "MEDIA" in txt or "MODER" in txt:
            conteos["Medio"] += 1
        elif "BAJO" in txt or "BAJA" in txt:
            conteos["Bajo"] += 1

    try:
        db_path = INCIDENTES_DB_PATH
        columnas = _obtener_columnas_sqlite(db_path, "registro_incidentes")

        posibles_columnas = [
            "clasificacion_incidente",
            "clasificacion",
            "criticidad",
            "nivel",
            "tipo_incidente",
            "categoria_incidente"
        ]

        columna_real = next((c for c in posibles_columnas if c in columnas), None)

        if not columna_real:
            print("ERROR DASHBOARD INCIDENTES: no existe una columna válida en registro_incidentes. Columnas encontradas:", columnas)
            return _dashboard_empty_chart(
                "Incidentes por clasificación",
                "No se encontró columna de clasificación en registro_incidentes"
            )

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute(f"""
            SELECT {columna_real}
            FROM registro_incidentes
            WHERE {columna_real} IS NOT NULL
              AND TRIM({columna_real}) <> ''
        """)
        rows = c.fetchall()
        conn.close()

        for row in rows:
            acumular_clasificacion(row[columna_real])

    except Exception as e:
        print("ERROR DASHBOARD INCIDENTES:", str(e))
        return _dashboard_empty_chart(
            "Incidentes por clasificación",
            f"Error consultando registro_incidentes: {str(e)}"
        )

    return _dashboard_donut_b64(
        buckets,
        [conteos[n] for n in buckets],
        title="Incidentes por clasificación",
        subtitle="Fuente: registro_incidentes"
    )


def _dashboard_vulnerabilidades_chart():
    buckets = ["Baja", "Media", "Alta", "Crítica"]
    conteos = {k: 0 for k in buckets}

    def norm_sev(raw):
        txt = str(raw or "").strip().upper()
        txt = (
            txt.replace("Á", "A")
               .replace("É", "E")
               .replace("Í", "I")
               .replace("Ó", "O")
               .replace("Ú", "U")
        )
        return txt

    def acumular(raw):
        txt = norm_sev(raw)
        if not txt:
            return False

        if "CRIT" in txt or "CRITICAL" in txt:
            conteos["Crítica"] += 1
            return True
        elif "ALTA" in txt or "HIGH" in txt:
            conteos["Alta"] += 1
            return True
        elif "MEDIA" in txt or "MEDIUM" in txt or "MODERATE" in txt:
            conteos["Media"] += 1
            return True
        elif "BAJA" in txt or "LOW" in txt or "INFO" in txt:
            conteos["Baja"] += 1
            return True

        return False

    # =========================================================
    # 1) FUENTE PRINCIPAL: MATRIZ DE VULNERABILIDADES
    # =========================================================
    try:
        items = VulnerabilidadRegistro.query.order_by(VulnerabilidadRegistro.id.desc()).all()
    except Exception:
        items = []

    for it in items:
        # probar varios campos posibles del modelo
        candidatos = [
            getattr(it, "clasificacion", None),
            getattr(it, "severidad", None),
            getattr(it, "criticidad", None),
            getattr(it, "nivel_criticidad", None),
            getattr(it, "criticidad_vulnerabilidad", None),
            getattr(it, "impacto", None),
            getattr(it, "prioridad", None),
        ]

        encontrado = False
        for raw in candidatos:
            if acumular(raw):
                encontrado = True
                break

        # fallback adicional: revisar texto libre por si la severidad quedó embebida
        if not encontrado:
            texto_fallback = " ".join([
                str(getattr(it, "titulo", "") or ""),
                str(getattr(it, "nombre", "") or ""),
                str(getattr(it, "descripcion", "") or ""),
                str(getattr(it, "detalle", "") or ""),
            ])
            acumular(texto_fallback)

    # =========================================================
    # 2) FALLBACK: SI LA MATRIZ NO TRAJO CRÍTICAS, USAR HALLAZGOS
    # =========================================================
    if sum(conteos.values()) == 0 or conteos["Crítica"] == 0:
        try:
            findings = VulnerabilityScanFinding.query.order_by(VulnerabilityScanFinding.id.desc()).all()

            conteos_scan = {k: 0 for k in buckets}
            for f in findings:
                txt = norm_sev(getattr(f, "severidad", None))
                if "CRIT" in txt or "CRITICAL" in txt:
                    conteos_scan["Crítica"] += 1
                elif "ALTA" in txt or "HIGH" in txt:
                    conteos_scan["Alta"] += 1
                elif "MEDIA" in txt or "MEDIUM" in txt or "MODERATE" in txt:
                    conteos_scan["Media"] += 1
                elif "BAJA" in txt or "LOW" in txt or "INFO" in txt:
                    conteos_scan["Baja"] += 1

            # solo usar findings si realmente aportan datos
            if sum(conteos_scan.values()) > sum(conteos.values()):
                conteos = conteos_scan

        except Exception:
            pass

    return _dashboard_donut_b64(
        buckets,
        [conteos[n] for n in buckets],
        title="Vulnerabilidades por criticidad",
        subtitle="Fuente: módulo de vulnerabilidades"
    )


def _dashboard_proveedores_criticidad_chart():
    buckets = [
        "Criticidad muy baja",
        "Criticidad baja",
        "Criticidad media",
        "Criticidad alta"
    ]

    conteos = {k: 0 for k in buckets}

    try:
        items = ProveedorEvaluacion.query.order_by(ProveedorEvaluacion.id.desc()).all()

        for it in items:
            raw = str(getattr(it, "criticidad_texto", "") or "").strip().lower()

            if "muy baja" in raw:
                conteos["Criticidad muy baja"] += 1
            elif "baja" in raw:
                conteos["Criticidad baja"] += 1
            elif "media" in raw:
                conteos["Criticidad media"] += 1
            elif "alta" in raw:
                conteos["Criticidad alta"] += 1

    except Exception as e:
        return _dashboard_empty_chart(
            "Proveedores por criticidad",
            f"Error consultando proveedores: {str(e)}"
        )

    return _dashboard_donut_b64(
        buckets,
        [conteos[n] for n in buckets],
        title="Proveedores por criticidad",
        subtitle="Distribución de proveedores según criticidad"
    )


def _dashboard_planes_accion_estado_chart():
    # Fuente única: ContinuousActionPlan / instance/planes_accion.db.
    buckets = ["Abierto", "En proceso", "Vencido", "Cerrado", "Cancelado", "Otros"]
    conteos = {k: 0 for k in buckets}

    try:
        items = ContinuousActionPlan.query.order_by(ContinuousActionPlan.id.desc()).limit(10000).all()
        today = date.today()

        for it in items:
            status = pa_effective_status(it, today)
            if status in conteos and status != "Otros":
                conteos[status] += 1
            else:
                conteos["Otros"] += 1

    except Exception as e:
        return _dashboard_empty_chart(
            "Planes de acción por estado",
            f"Error consultando planes de acción: {str(e)}"
        )

    return _dashboard_donut_b64(
        buckets,
        [conteos[n] for n in buckets],
        title="Planes de acción por estado",
        subtitle="Estado efectivo de los planes de acción del SGSI"
    )


def _dashboard_requisitos_legales_estado_chart():
    buckets = ["Cumple", "Parcial", "No cumple", "Sin estado"]
    conteos = {k: 0 for k in buckets}

    try:
        items = RequisitoLegal.query.order_by(RequisitoLegal.id.desc()).all()

        for it in items:
            raw = str(getattr(it, "estado", "") or "").strip().lower()

            if raw == "cumple":
                conteos["Cumple"] += 1
            elif raw == "parcial":
                conteos["Parcial"] += 1
            elif raw == "no cumple":
                conteos["No cumple"] += 1
            else:
                conteos["Sin estado"] += 1

    except Exception as e:
        return _dashboard_empty_chart(
            "Requisitos legales por estado",
            f"Error consultando requisitos legales: {str(e)}"
        )

    return _dashboard_donut_b64(
        buckets,
        [conteos[n] for n in buckets],
        title="Requisitos legales por estado",
        subtitle="Cumplimiento de requisitos legales aplicables"
    )

# =========================
# Plantilla HTML única (integrada)
# =========================

BASE = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Arkyntech GRAC</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">

  <style>
    :root{
      /* Paleta Arkyntech ajustada: tonos más oscuros y mejor contraste */
      --arky-blue:#062b55;
      --arky-blue-2:#0b4a8f;
      --arky-blue-3:#1d5fae;
      --arky-blue-4:#3f8fd6;
      --arky-soft:#dcecff;
      --arky-soft-2:#c9e3ff;
      --arky-border:#a9cdeb;
      --arky-text:#102a4b;
      --arky-muted:#425f7f;
      --arky-purple:#3f148a;
      --arky-topbar-h:58px;
    }

    html, body{ min-height:100%; }

    body{
      margin:0;
      color:var(--arky-text);
      padding-top:var(--arky-topbar-h);
      background:
        linear-gradient(135deg, rgba(214,232,248,.96) 0%, rgba(202,224,245,.93) 42%, rgba(216,208,242,.86) 100%),
        radial-gradient(circle at 86% 24%, rgba(47,18,102,.23) 0, rgba(47,18,102,.23) 17%, transparent 18%),
        radial-gradient(circle at 6% 88%, rgba(18,84,157,.23) 0, rgba(18,84,157,.23) 22%, transparent 23%),
        url('/static/img/ccsgsi.jpg');
      background-size:cover;
      background-position:center;
      background-attachment:fixed;
      background-repeat:no-repeat;
    }

    body::before{
      content:"";
      position:fixed;
      inset:var(--arky-topbar-h) 0 0 0;
      pointer-events:none;
      z-index:-1;
      background:
        radial-gradient(circle at 96% 22%, rgba(47,18,102,.18), transparent 24%),
        radial-gradient(circle at 2% 76%, rgba(18,84,157,.17), transparent 26%);
    }

    .sgsi-topbar{
      position:fixed;
      top:0;
      left:0;
      right:0;
      height:var(--arky-topbar-h);
      min-height:var(--arky-topbar-h);
      background:rgba(248,252,255,.96);
      backdrop-filter:blur(18px);
      -webkit-backdrop-filter:blur(18px);
      border-bottom:1px solid rgba(207,229,255,.95);
      box-shadow:0 10px 24px rgba(20,89,166,.10);
      z-index:999997;
      overflow:hidden;
    }

    .sgsi-topbar-inner{
      height:var(--arky-topbar-h);
      min-height:var(--arky-topbar-h);
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
      padding:0 18px 0 14px;
      overflow:hidden;
    }

    .sgsi-brand{
      height:var(--arky-topbar-h);
      width:230px;
      min-width:230px;
      display:flex;
      align-items:center;
      justify-content:flex-start;
      text-decoration:none;
      overflow:hidden;
      margin-left:0;
      padding:0;
    }

    .sgsi-logo{
      height:48px;
      width:auto;
      max-width:220px;
      object-fit:contain;
      object-position:left center;
      filter:drop-shadow(0 4px 9px rgba(11,58,110,.14));
      margin:0;
      display:block;
    }

    .sgsi-title{ display:none !important; }
    .sgsi-main-nav{ display:none !important; }

    .sgsi-user-area{
      display:flex;
      align-items:center;
      gap:10px;
      min-width:max-content;
      position:relative;
      z-index:10060;
    }

    .sgsi-topbar,
    .sgsi-topbar-inner{
      overflow:visible !important;
    }

    .sgsi-user-area .dropdown-menu{
      position:absolute !important;
      top:calc(100% + 8px) !important;
      right:0 !important;
      left:auto !important;
      z-index:10070 !important;
      min-width:210px !important;
      margin:0 !important;
      transform:none !important;
    }

    .sgsi-user-area .dropdown-menu.show{
      display:block !important;
      visibility:visible !important;
      opacity:1 !important;
    }

    .sgsi-pill-login{
      border:1px solid var(--arky-border);
      background:#ffffff;
      color:var(--arky-blue) !important;
      border-radius:999px;
      padding:10px 18px;
      font-weight:850;
      text-decoration:none;
      box-shadow:0 8px 18px rgba(20,89,166,.08);
    }

    .sgsi-user-link{
      display:flex;
      align-items:center;
      color:#fff !important;
      background:linear-gradient(135deg, var(--arky-blue) 0%, var(--arky-blue-2) 46%, var(--arky-purple) 100%);
      border-radius:999px;
      padding:5px 12px 5px 6px;
      text-decoration:none;
      box-shadow:0 12px 26px rgba(20,89,166,.24);
      border:1px solid rgba(255,255,255,.38);
    }

    button.sgsi-user-link{
      font-family:inherit;
      line-height:1;
      appearance:none;
      -webkit-appearance:none;
      outline:none;
    }

    button.sgsi-user-link:focus,
    button.sgsi-user-link:focus-visible{
      box-shadow:0 0 0 3px rgba(52,125,220,.30),0 12px 26px rgba(20,89,166,.24);
    }

    .sgsi-user-photo{
      width:32px;
      height:32px;
      object-fit:cover;
      border-radius:50%;
      border:2px solid rgba(255,255,255,.82);
      background:#fff;
    }

    .sgsi-user-name{
      margin-left:7px;
      font-size:.78rem;
      font-weight:850;
      max-width:150px;
      overflow:hidden;
      text-overflow:ellipsis;
      white-space:nowrap;
    }

    .container.py-4{
      max-width:100% !important;
      padding:0 !important;
    }

    .dropdown-menu{
      border:1px solid var(--arky-border);
      border-radius:16px;
      box-shadow:0 18px 36px rgba(20,89,166,.16);
      overflow:hidden;
    }

    @media(max-width:1100px){
      .sgsi-topbar-inner{
        padding:0 12px;
      }

      .sgsi-brand{
        width:200px !important;
        min-width:200px !important;
      }

      .sgsi-logo{
        height:44px !important;
        max-width:190px !important;
      }
    }

    @media(max-width:575px){
      :root{
        --arky-topbar-h:62px;
      }

      .sgsi-topbar,
      .sgsi-topbar-inner,
      .sgsi-brand{
        height:var(--arky-topbar-h);
        min-height:var(--arky-topbar-h);
      }

      .sgsi-brand{
        width:170px !important;
        min-width:170px !important;
      }

      .sgsi-logo{
        height:40px !important;
        max-width:160px !important;
      }

      .sgsi-user-name{
        display:none;
      }

      .sgsi-user-link{
        padding:6px;
      }
    }
  </style>
</head>

<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>

{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    <script>
      document.addEventListener("DOMContentLoaded", function () {
        {% for category, message in messages %}
          Swal.fire({
            title: {{ (
              'Error'
              if category == 'danger'
              else 'Proceso exitoso'
              if category == 'success'
              else 'Atención'
              if category == 'warning'
              else 'Información'
            ) | tojson }},
            text: {{ message | tojson }},
            icon: {{ (
              'error'
              if category == 'danger'
              else 'success'
              if category == 'success'
              else 'warning'
              if category == 'warning'
              else 'info'
            ) | tojson }},
            confirmButtonText: "Aceptar",
            confirmButtonColor: "#0b4a8f",
            backdrop: true,
            allowOutsideClick: false
          });
        {% endfor %}
      });
    </script>
  {% endif %}
{% endwith %}

<body>

<header class="sgsi-topbar">
  <div class="container-fluid sgsi-topbar-inner">

    <a class="sgsi-brand" href="{{ url_for('menu') }}" title="Arkyntech GRAC">
      <img src="{{ url_for('static', filename='img/Arkynthec.png') }}" class="sgsi-logo" alt="Arkyntech GRAC">
    </a>

    {% if current_user %}
    <div class="sgsi-user-area dropdown">
      <button class="sgsi-user-link dropdown-toggle" type="button" data-bs-toggle="dropdown" data-bs-auto-close="true" aria-expanded="false" style="cursor:pointer;">
        <img src="{{ url_for('static', filename='uploads/profiles/' ~ current_user.photo_filename)
                     if current_user.photo_filename
                     else url_for('static', filename='img/default_user.png') }}"
             class="sgsi-user-photo" alt="Perfil">
        <span class="sgsi-user-name">{{ current_user.username }}</span>
      </button>

      <ul class="dropdown-menu dropdown-menu-end">
        <li><a class="dropdown-item" href="{{ url_for('perfil') }}">👤 Ver perfil</a></li>
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item text-danger" href="{{ url_for('logout') }}">🚪 Cerrar sesión</a></li>
      </ul>
    </div>
    {% endif %}

  </div>
</header>

<div class="container py-4">
  {{ content|safe }}
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>

</body>
</html>
"""

# ========================================
# Agrupado por secciones (NO cambia rutas)
# ========================================

MENU_SECTIONS = [
    {
        "title": "Gobierno / Dirección",
        "icon": "bi-diagram-3",
        "items": [
            {"label": "Declaración de Aplicabilidad (SoA)", "href": "/soa", "icon": "bi-diagram-3", "btn": "btn-primary", "module": "Contexto Interno"},
            {"label": "Gestión de Riesgos", "href": "/riesgos_menu", "icon": "bi-diagram-3", "btn": "btn-primary", "module": "Gestión de Riesgos"},
            {"label": "Objetivos del Sistema de Gestión", "href": "/objetivos_menu", "icon": "bi-diagram-3", "btn": "btn-primary", "module": "Objetivos del Sistema de Gestión"},
            {"label": "Partes Interesadas", "href": "/partes_menu", "icon": "bi-people-fill", "btn": "btn-primary", "module": "Partes Interesadas"},
            {"label": "Contexto Interno", "href": "/contexto_interno_menu", "icon": "bi-building-fill-gear", "btn": "btn-info text-white", "module": "Contexto Interno"},
            {"label": "Contexto Externo", "href": "/contexto_externo_menu", "icon": "bi-globe2", "btn": "btn-info text-white", "module": "Contexto Externo"},
            {"label": "DOFA", "href": "/dofa_menu", "icon": "bi-grid-3x3-gap-fill", "btn": "btn-info text-white", "module": "DOFA"},
            {"label": "PESI", "href": "/pesi", "icon": "bi-shield-lock-fill", "btn": "btn-primary", "module": "PESI"},
            {"label": "Informe Revisión por la Dirección", "href": "/revision_direccion", "icon": "bi-clipboard-data-fill", "btn": "btn-primary", "module": "Informe Revisión por la Dirección"},
            {"label": "Análisis de Riesgos de Procesos", "href": "/procesos_ia", "icon": "bi-diagram-3", "btn": "btn-primary", "module": "Análisis de Riesgos de Procesos con IA"},
        ],
    },
    {
        "title": "Documentación",
        "icon": "bi-journal-text",
        "items": [
            {"label": "Listado Maestro de Documentos", "href": "/docs_menu", "icon": "bi-file-earmark-text", "btn": "btn-primary", "module": "Listado Maestro de Documentos"},
            {"label": "Registro de Comunicaciones", "href": "/comunicaciones_menu", "icon": "bi-envelope-paper", "btn": "btn-primary", "module": "Registro de Comunicaciones"},
            {"label": "Requisitos Legales", "href": "/requisitos_menu", "icon": "bi-balance-scale", "btn": "btn-primary", "module": "Requisitos Legales"},
        ],
    },
    {
        "title": "Operación y Control",
        "icon": "bi-shield-check",
        "items": [
            {
                "label": "Gestión de Activos de Información",
                "href": "#",
                "icon": "bi-archive",
                "btn": "btn-primary",
                "module": "Gestión de Activos de Información",
                "children": [
                    {
                        "label": "Matrices de Activos",
                        "href": "#",
                        "icon": "bi-box-seam",
                        "btn": "btn-outline-primary",
                        "children": [
                            {
                                "label": "Inventario de Software",
                                "href": "/inventario_software_menu",
                                "icon": "bi-cpu",
                                "btn": "btn-outline-primary",
                                "module": "Inventario de Software"
                            },
                            {
                                "label": "Inventario de IA",
                                "href": "/inventario_ia_menu",
                                "icon": "bi-cpu-fill",
                                "btn": "btn-outline-primary",
                                "module": "Inventario de IA"
                            },
                            {
                                "label": "Inventario de Información",
                                "href": "/inventario_informacion_menu",
                                "icon": "bi-file-earmark-text",
                                "btn": "btn-outline-primary",
                                "module": "Inventario de Información"
                            },
                            {
                                "label": "Inventario de Datos Personales",
                                "href": "/inventario_datos_personales_menu",
                                "icon": "bi-shield-lock",
                                "btn": "btn-outline-primary",
                                "module": "Inventario de Datos Personales"
                            },
                            {
                                "label": "Inventario Físico",
                                "href": "/inventario_fisico_menu",
                                "icon": "bi-pc-display",
                                "btn": "btn-outline-primary",
                                "module": "Inventario Físico"
                            },
                        ]
                    },
                    {
                        "label": "Tablas de Valoración",
                        "href": "#",
                        "icon": "bi-bar-chart-line",
                        "btn": "btn-outline-primary",
                        "module": "Tablas de Valoración",
                                            "children": [
                            {
                                "label": "Confidencialidad",
                                "href": "/valor_confidencialidad",
                                "icon": "bi-lock-fill",
                                "btn": "btn-outline-primary",
                                "module": "Tablas de Valoración"
                            },
                            {
                                "label": "Integridad",
                                "href": "/valor_integridad",
                                "icon": "bi-shield-check",
                                "btn": "btn-outline-primary",
                                "module": "Tablas de Valoración"
                            },
                            {
                                "label": "Disponibilidad",
                                "href": "/valor_disponibilidad",
                                "icon": "bi-clock-history",
                                "btn": "btn-outline-primary",
                                "module": "Tablas de Valoración"
                            },
                            {
                                "label": "Criticidad del Activo",
                                "href": "/valor_criticidad_activo",
                                "icon": "bi-exclamation-diamond-fill",
                                "btn": "btn-outline-primary",
                                "module": "Tablas de Valoración"
                            },
                        ]
                    },
                    {
                        "label": "Dueños de Información",
                        "href": "/duenos_info",
                        "icon": "bi-person-badge",
                        "btn": "btn-outline-primary",
                        "module": "Dueños de Información"
                    },
                ]
            },
            {
                "label": "Gestión de Accesos",
                "href": "/accesos_menu",
                "icon": "bi-shield-lock",
                "btn": "btn-info text-white",
                "module": "Gestión de Accesos"
            },
            {
                "label": "Revisión de Accesos",
                "href": "/revision_accesos_menu",
                "icon": "bi-clipboard-check",
                "btn": "btn-info text-white",
                "module": "Revisión de Accesos"
            },
            {
                "label": "Gestión de Cambios (RFC)",
                "href": "/rfc_menu",
                "icon": "bi-arrow-left-right",
                "btn": "btn-primary",
                "module": "Gestión de Cambios (RFC)"
            },
        ],
    },
    {
        "title": "Gestión de Eventos",
        "icon": "bi-exclamation-triangle",
        "items": [
            {"label": "Centro de Alertas", "href": "/alertas", "icon": "bi-bell-fill", "btn": "btn-warning text-dark", "module": "Centro de Alertas"},
            {"label": "Registro de Incidentes", "href": "/incidentes", "icon": "bi-exclamation-triangle", "btn": "btn-danger", "module": "Registro de Incidentes"},
            {"label": "Planes de Respuesta a Incidentes", "href": "/planes_respuesta_incidentes", "icon": "bi-shield-check", "btn": "btn-primary", "module": "Planes de Respuesta a Incidentes"},
            {"label": "Registro de Vulnerabilidades", "href": "/vulnerabilidades_menu", "icon": "bi-bug", "btn": "btn-danger", "module": "Registro de Vulnerabilidades"},
            {"label": "Modelamiento de Amenazas", "href": "/modelamiento_amenazas", "icon": "bi-diagram-3", "btn": "btn-dark", "module": "Modelamiento de Amenazas"},
            {"label": "Superficie de Ataque y Escenarios", "href": "/superficie_ataque", "icon": "bi-bullseye", "btn": "btn-primary", "module": "Superficie de Ataque y Escenarios"},
            {"label": "Plan de Remediación", "href": "/plan_remediacion_menu", "icon": "bi-tools", "btn": "btn-primary", "module": "Plan de Remediación"},
        ],
    },
    {
        "title": "Competencias y Cultura",
        "icon": "bi-mortarboard",
        "items": [
            {"label": "Campañas de Concientización", "href": "/campanias_concientizacion_menu", "icon": "bi-bullseye", "btn": "btn-primary", "module": "Campañas de Concientización"},
            {"label": "Plan de Concientización y Formación", "href": "/plan_diseno_menu", "icon": "bi-journal-text", "btn": "btn-primary", "module": "Plan de Concientización y Formación"},
            {"label": "Seguimiento Plan de Concientización y Formación", "href": "/plan_cf/menu", "icon": "bi-graph-up", "btn": "btn-info", "module": "Seguimiento del Plan de Formación"},
            {"label": "Plan de Competencia", "href": "/plan_remediacion_competencias_menu", "icon": "bi-person-badge", "btn": "btn-primary", "module": "Plan de Competencias"},

        ],
    },
    {
        "title": "Cadena de Suministro (TPRM)",
        "icon": "bi-truck",
        "items": [
            {
                "label": "Selección de Proponentes",
                "href": "#",
                "icon": "bi-people",
                "btn": "btn-info text-white",
                "children": [
                    {
                        "label": "Ingreso información",
                        "href": "#",
                        "icon": "bi-folder2-open",
                        "btn": "btn-info text-white",
                        "children": [
                            {"label": "Vía web", "href": "/cuestionario_proveedores_web", "icon": "bi-globe", "btn": "btn-info text-white", "module": "Cuestionario de proveedores web"},
                            {"label": "Vía archivo", "href": "/ingreso_informacion_proponente_archivo", "icon": "bi-file-earmark-spreadsheet", "btn": "btn-info text-white", "module": "Cuestionarios de Proponentes"},
                        ],
                    },
                    {"label": "Evaluación de proponentes", "href": "/cuestionarios_proveedores", "icon": "bi-bar-chart-line", "btn": "btn-info text-white", "module": "Cuestionarios de Proponentes"},
                ],
            },
            {"label": "Revisión en Listas Restrictivas", "href": "/listas_restrictivas", "icon": "bi-shield-exclamation", "btn": "btn-danger", "module": "Listas Restrictivas"},
            {"label": "Security Scorecard de Terceros", "href": "/proponentes/scorecard", "icon": "bi-shield-check", "btn": "btn-warning text-dark", "module": "Security Scorecard de Terceros"},
            {"label": "Registro de Proveedores", "href": "/proveedores_menu", "icon": "bi-building", "btn": "btn-primary", "module": "Registro de Proveedores"},
        ],
    },
    {
        "title": "Continuidad del Negocio",
        "icon": "bi-shield-check",
        "items": [
            {"label": "Continuidad del Negocio (BCP/DRP)", "href": "/bcp/dashboard", "icon": "bi-shield-check", "btn": "btn-primary", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "BIA", "href": "/bcp/bia", "icon": "bi-clipboard-data", "btn": "btn-info text-white", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "Procesos Críticos", "href": "/bcp/procesos", "icon": "bi-diagram-3", "btn": "btn-warning", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "Planes de Continuidad", "href": "/bcp/planes", "icon": "bi-journal-text", "btn": "btn-success", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "DRP", "href": "/bcp/drp", "icon": "bi-hdd-network", "btn": "btn-dark", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "Gestión de Crisis", "href": "/bcp/crisis", "icon": "bi-exclamation-triangle", "btn": "btn-danger", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "Simulacros y Pruebas", "href": "/bcp/pruebas", "icon": "bi-play-circle", "btn": "btn-secondary", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "Dependencias Críticas", "href": "/bcp/dependencias", "icon": "bi-link-45deg", "btn": "btn-primary", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "Madurez BCP", "href": "/bcp/madurez", "icon": "bi-graph-up-arrow", "btn": "btn-info", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "Informe Ejecutivo AI", "href": "/bcp/ia/matriz", "icon": "bi-robot", "btn": "btn-info text-white", "module": "Continuidad del Negocio (BCP/DRP)"},
        ]
    },
    {
        "title": "Medición y Mejora",
        "icon": "bi-graph-up-arrow",
        "items": [
            {"label": "Nivel de Madurez ISO-27001:2022", "href": "/madurez", "icon": "bi-speedometer2", "btn": "btn-primary", "module": "Nivel de madurez ISO 27001:2022"},
            {"label": "Nivel de Madurez NIST CSF V.2.0", "href": "/madurez_nist", "icon": "bi-compass", "btn": "btn-primary", "module": "Nivel de Madurez NIST CSF V.2.0"},
            {"label": "Nivel de Madurez Protección de Datos Personales", "href": "/madurez_datos", "icon": "bi-shield-lock", "btn": "btn-primary", "module": "Nivel de Madurez protección de datos personales"},
            {"label": "Nivel de Madurez PCI-DSS", "href": "/madurez_pci", "icon": "bi-credit-card-2-front", "btn": "btn-primary", "module": "Nivel de Madurez PCI-DSS"},
            {"label": "Nivel de Madurez SOC 2", "href": "/madurez_soc2/", "icon": "bi-shield-check", "btn": "btn-primary", "module": "Nivel de madurez SOC 2"},
            {"label": "Nivel de Madurez ISO 22301", "href": "/madurez_iso22301/", "icon": "bi-life-preserver", "btn": "btn-primary", "module": "Nivel de Madurez ISO 22301"},
            {"label": "Nivel de Madurez Gestión de Inteligencia Artificial", "href": "/madurez-ai", "icon": "bi-robot", "btn": "btn-primary", "module": "Nivel de Madurez Gestión de Inteligencia Artificial"},
            {
                "label": "Métricas",
                "href": "#",
                "icon": "bi-graph-up",
                "btn": "btn-info text-white",
                "module": "Métricas",
                "children": [
                    {
                        "label": "Métricas de Riesgos",
                        "href": "/metricas/riesgos",
                        "icon": "bi-exclamation-triangle",
                        "btn": "btn-info text-white",
                        "module": "Métricas"
                    },
                    {
                        "label": "Métricas de Incidentes",
                        "href": "/metricas/incidentes/matriz",
                        "icon": "bi-bell",
                        "btn": "btn-info text-white",
                        "module": "Métricas"
                    },
                    {
                        "label": "Métricas de Vulnerabilidades",
                        "href": "/metricas/vulnerabilidades",
                        "icon": "bi-shield-exclamation",
                        "btn": "btn-info text-white",
                        "module": "Métricas"
                    },
                    {
                        "label": "Métrica Cultura de Seguridad",
                        "href": "/metricas/cultura/matriz",
                        "icon": "bi-mortarboard",
                        "btn": "btn-info text-white",
                        "module": "Métricas"
                    },
                    {"label": "Métricas BCP", "href": "/bcp/metricas", "icon": "bi-bar-chart", "btn": "btn-success", "module": "Continuidad del Negocio (BCP/DRP)"},
                    {
                        "label": "Configuración de Parámetros",
                        "href": "#",
                        "icon": "bi-gear",
                        "btn": "btn-info text-white",
                        "module": "Métricas",
                        "children": [
                            {
                                "label": "Parámetros de Incidentes",
                                "href": "/metricas/configuracion/incidentes",
                                "icon": "bi-bell",
                                "btn": "btn-info text-white",
                                "module": "Métricas"
                            },
                            {
                                "label": "Parámetros de Vulnerabilidades",
                                "href": "/metricas/configuracion/vulnerabilidades",
                                "icon": "bi-shield-exclamation",
                                "btn": "btn-info text-white",
                                "module": "Métricas"
                            },
                            {
                                "label": "Parámetros de Cultura",
                                "href": "/metricas/configuracion/cultura",
                                "icon": "bi-mortarboard",
                                "btn": "btn-info text-white",
                                "module": "Métricas"
                            },
                            {
                                "label": "Parámetros de Riesgos",
                                "href": "/metricas/configuracion/riesgos",
                                "icon": "bi-exclamation-triangle",
                                "btn": "btn-info text-white",
                                "module": "Métricas"
                            }
                        ]
                    }
                ]
            },
        ],
    },
    {
    "title": "Cumplimiento Continuo",
            "icon": "bi-shield-lock",
            "items": [
                {
                    "label": "Dashboard",
                    "href": "/cumplimiento_continuo",
                    "icon": "bi-speedometer2",
                    "btn": "btn-primary",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "Herramienta XDR (Wazuh)",
                    "href": "/cumplimiento_continuo/wazuh",
                    "icon": "bi-plug",
                    "btn": "btn-primary",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "Sincronización",
                    "href": "/cumplimiento_continuo/sincronizacion",
                    "icon": "bi-arrow-repeat",
                    "btn": "btn-warning",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "ISO 27001",
                    "href": "/cumplimiento_continuo/estandar/ISO27001",
                    "icon": "bi-shield-check",
                    "btn": "btn-primary",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "SOC 2",
                    "href": "/cumplimiento_continuo/estandar/SOC2",
                    "icon": "bi-patch-check",
                    "btn": "btn-primary",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "PCI-DSS",
                    "href": "/cumplimiento_continuo/estandar/PCIDSS",
                    "icon": "bi-credit-card-2-front",
                    "btn": "btn-primary",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "NIST CSF 2.0",
                    "href": "/cumplimiento_continuo/estandar/NISTCSF",
                    "icon": "bi-diagram-3",
                    "btn": "btn-primary",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "Evidencias",
                    "href": "/cumplimiento_continuo/evidencias",
                    "icon": "bi-folder-check",
                    "btn": "btn-success",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "Gobierno de Firewall",
                    "href": "/cumplimiento_continuo/firewall",
                    "icon": "bi-bricks",
                    "btn": "btn-danger",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "Gobierno del Directorio Activo",
                    "href": "/cumplimiento_continuo/active_directory/",
                    "icon": "bi-person-lock",
                    "btn": "btn-primary",
                    "module": "Cumplimiento Continuo"
                },
            ],
    },

    {
        "title": "Planes de Acción",
        "icon": "bi-clipboard2-check",
        "items": [
            {
                "label": "Matriz de Planes de Acción",
                "href": "/planes_accion",
                "icon": "bi-list-check",
                "btn": "btn-primary",
                "module": "Planes de acción del SGSI"
            },
        ],
    },
    {
        "title": "Reportes",
        "icon": "bi-mortarboard",
        "items": [
             {"label": "Reportes", "href": "/reportes", "icon": "bi-printer-fill", "btn": "btn-outline-danger", "module": "Reportes"},
         ],
     },
    {
        "title": "Aplicación móvil",
        "icon": "bi-phone",
        "items": [
            {"label": "Descargar aplicación móvil", "desc": "Consulta y descarga GRAC Mobile para Android o iOS.", "href": "/aplicacion_movil", "icon": "bi-phone", "btn": "btn-primary", "module": "Aplicación móvil"},
        ],
    },
    {
        "title": "Administración",
        "icon": "bi-gear",
        "items": [
            {
                "label": "Configuración Parámetros de la Empresa",
                "href": "#",
                "icon": "bi-building-gear",
                "btn": "btn-primary",
                "module": "Configuración Parámetros de la Empresa",
                "children": [
                    {
                        "label": "Estructura Organizacional",
                        "href": "#",
                        "icon": "bi-diagram-3",
                        "btn": "btn-outline-primary",
                        "module": "Configuración Parámetros de la Empresa",
                        "children": [
                            {
                                "label": "Áreas",
                                "href": "/areas_area",
                                "icon": "bi-diagram-3",
                                "btn": "btn-outline-primary",
                                "module": "Configuración Parámetros de la Empresa"
                            },
                            {
                                "label": "Divisiones",
                                "href": "/areas_division",
                                "icon": "bi-diagram-2",
                                "btn": "btn-outline-primary",
                                "module": "Configuración Parámetros de la Empresa"
                            }
                        ]
                    },
                    {
                        "label": "Parámetros Generales",
                        "href": "#",
                        "icon": "bi-gear-wide-connected",
                        "btn": "btn-outline-primary",
                        "module": "Configuración Parámetros de la Empresa",
                        "children": [
                            {
                                "label": "Configuración del Correo",
                                "href": "/config/email",
                                "icon": "bi-envelope-at",
                                "btn": "btn-outline-primary",
                                "module": "Configuración Parámetros de la Empresa"
                            },
                        ]
                    }
                ]
            },
            {"label": "Portal de Proveedores — Conexión", "desc": "Generar código de vinculación de servidores para proveedores.", "href": "/admin/portal_proveedores_conexion", "icon": "bi-shield-lock", "btn": "btn-primary", "module": "Cuestionario de proveedores web", "admin_only": True},
            {"label": "Configuración AI", "desc": "Configurar llave cifrada para IA (solo admin).", "href": "/admin/openrouter_key", "icon": "bi-key-fill", "btn": "btn-warning text-dark", "admin_only": True},
            {"label": "Gestión de Usuarios", "href": "/usuarios", "icon": "bi-people", "btn": "btn-success", "module": "Gestión de Usuarios"},
            {"label": "Aplicación móvil", "desc": "Descarga GRAC Mobile para Android o accede a TestFlight en iOS.", "href": "/admin/mobile-app", "icon": "bi-phone", "btn": "btn-primary", "module": "Aplicación móvil"},
            {"label": "Administración de Alertas", "desc": "Configurar destinatarios, reglas, severidad y frecuencia.", "href": "/admin/alertas", "icon": "bi-bell-fill", "btn": "btn-warning text-dark", "admin_only": True},
            {"label": "Constructor del Centro de Control", "href": "/admin/dashboard_config", "icon": "bi-sliders", "btn": "btn-primary"},
            {"label": "Logs de Auditoría", "href": "/admin/logs_auditoria", "icon": "bi-journal-text", "btn": "btn-dark", "admin_only": True},
            {"label": "Chat con Asistente", "href": "/chatgpt_view", "icon": "bi-chat-dots", "btn": "btn-info text-white", "module": "Chat con Asistente"},
        ],
    },
]

def filtrar_items_menu(items, usuario_actual, seccion_admin=False):
    filtrados = []

    for it in items:
        item_copy = dict(it)
        # En Administración los perfiles Usuario y Auditor solo ven el chat.
        # Este filtro es exclusivo de la sección: no toca otros módulos SGSI.
        if (seccion_admin and usuario_actual.role in ("user", "auditor")
                and item_copy.get("href") != "/chatgpt_view"):
            continue
        children = item_copy.get("children", [])
        module_name = item_copy.get("module")

        permitido = True

        # Admin ve todo
        if usuario_actual.role == "admin":
            permitido = True

        # Solo admin
        elif item_copy.get("admin_only"):
            permitido = False

        # Declaración de Aplicabilidad (SoA)
        elif item_copy.get("href") == "/soa":
            permitido = (
                usuario_actual.role in ("admin", "auditor")
                or verificar_permiso(usuario_actual, "Contexto Interno")
            )

        # Resultados unificados: acceso tanto para quien gestiona la web
        # como para quien evalúa cuestionarios importados por archivo.
        elif item_copy.get("href") == "/cuestionarios_proveedores":
            permitido = (verificar_permiso(usuario_actual, "Cuestionarios de Proponentes")
                         or verificar_permiso(usuario_actual, "Cuestionario de proveedores web"))

        # Módulos normales por nombre
        elif module_name and module_name in MODULES:
            permitido = verificar_permiso(usuario_actual, module_name)

        # Si tiene hijos, se filtran recursivamente
        if children:
            children_filtrados = filtrar_items_menu(children, usuario_actual, seccion_admin=seccion_admin)

            if children_filtrados and permitido:
                item_copy["children"] = children_filtrados
                filtrados.append(item_copy)

            elif children_filtrados and not module_name:
                item_copy["children"] = children_filtrados
                filtrados.append(item_copy)

            else:
                continue
        else:
            if permitido:
                filtrados.append(item_copy)

    return filtrados


# ============================================================
# SEGURIDAD: SOLO CHAT PARA USUARIO Y AUDITOR EN ADMINISTRACIÓN
# ============================================================
@app.before_request
def _sgsi_restringir_administracion_a_chat():
    """Evita acceso por URL o POST a funciones administrativas ocultas del menú."""
    uid = session.get("user_id")
    if not uid:
        return None  # La autenticación conserva su validación original.

    path = (request.path or "/").rstrip("/") or "/"
    # Solo destinos administrativos del menú (sin interferir con otros módulos).
    administrativo = (
        path == "/admin" or path.startswith("/admin/")
        or path == "/usuarios" or path.startswith("/usuarios/")
        or path.startswith("/editar_permisos/")
        or path in {"/areas_area", "/areas_division", "/areas/delete", "/config/email"}
        or (path.startswith("/areas/") and
            (path.endswith("/info") or path.endswith("/divisiones_json")))
    )
    if not administrativo:
        return None

    usuario = db.session.get(User, uid)
    if usuario is None or usuario.role in ("user", "auditor"):
        # Un POST o una consulta directa tampoco puede sortear la restricción.
        abort(403, description="Acceso restringido a Administración. Solo Chat con Asistente.")
    return None


# ============================================================
# MENÚ GLOBAL SGSI SIEMPRE VISIBLE EN TODOS LOS MÓDULOS
# FIX: marca en azul SOLO la opción exacta / más específica
# ============================================================

def _sgsi_build_global_menu_html():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return ""

        usuario_actual = User.query.get(user_id)
        if not usuario_actual:
            return ""

        current_path = (request.path or "/").split("?")[0].rstrip("/")
        if not current_path:
            current_path = "/"

        current_endpoint = (request.endpoint or "").strip()

        # ============================================================
        # Normalizadores
        # ============================================================
        def _norm_path(path):
            path = str(path or "").split("?")[0].strip()
            if not path or path in ("#", "javascript:void(0);"):
                return path
            if not path.startswith("/"):
                path = "/" + path
            path = path.rstrip("/")
            return path or "/"

        def _path_matches(path):
            path = _norm_path(path)
            if not path or path in ("#", "javascript:void(0);"):
                return False

            # Dashboard Cumplimiento Continuo: SOLO exacto
            if path == "/cumplimiento_continuo":
                return current_path == "/cumplimiento_continuo"

            # Dashboard BCP: SOLO exacto
            if path == "/bcp/dashboard":
                return current_path == "/bcp/dashboard"

            # ISO maturity: no debe activar NIST, Datos, PCI, SOC2 ni AI
            if path == "/madurez":
                return current_path == "/madurez" or current_path.startswith("/madurez/")

            return current_path == path or current_path.startswith(path + "/")

        def _endpoint_matches(endpoint_prefix):
            endpoint_prefix = (endpoint_prefix or "").strip()
            if not endpoint_prefix:
                return False

            if current_endpoint == endpoint_prefix:
                return True

            if current_endpoint.startswith(endpoint_prefix + "_"):
                resto = current_endpoint[len(endpoint_prefix) + 1:]

                # Evita falsas coincidencias entre módulos de madurez
                if endpoint_prefix == "madurez" and resto.startswith((
                    "nist",
                    "datos",
                    "pci",
                    "soc2",
                    "iso22301",
                    "ai"
                )):
                    return False

                # Evita que Plan de Remediación se active con Plan de Competencias
                if endpoint_prefix == "plan_remediacion" and resto.startswith("competencias"):
                    return False

                # Evita que BCP dashboard se active con submódulos BCP
                if endpoint_prefix == "bcp" and resto.startswith((
                    "bia",
                    "procesos",
                    "planes",
                    "drp",
                    "crisis",
                    "pruebas",
                    "dependencias",
                    "madurez",
                    "ia",
                    "metricas"
                )):
                    return False

                # Evita que Dashboard de Cumplimiento Continuo se active con submódulos
                if endpoint_prefix == "cumplimiento_continuo" and resto.startswith((
                    "wazuh",
                    "sincronizacion",
                    "firewall",
                    "active_directory",
                    "estandar",
                    "evidencias",
                    "planes"
                )):
                    return False

                return True

            if current_endpoint.endswith("." + endpoint_prefix):
                return True

            return False

        # ============================================================
        # Reglas por label del menú
        # ============================================================
        MENU_ACTIVE_RULES = {
            "Análisis de Riesgos de Procesos con IA": {"paths": ["/procesos_ia"], "endpoints": ["pra_index", "pra_new", "pra_files_new", "pra_process", "pra_risk", "pra_edit"]},
            # Gobierno / Dirección
            "Declaración de Aplicabilidad (SoA)": {
                "paths": ["/soa"],
                "endpoints": ["soa"]
            },
            "Gestión de Riesgos": {
                "paths": ["/riesgos_menu", "/riesgos", "/riesgo"],
                "endpoints": [
                    "riesgos_menu",
                    "riesgos",
                    "riesgo",
                    "riesgo_matriz",
                    "riesgo_nuevo",
                    "riesgo_editar"
                ]
            },
            "Objetivos del Sistema de Gestión": {
                "paths": ["/objetivos_menu", "/objetivos", "/objetivo"],
                "endpoints": ["objetivos_menu", "objetivos", "objetivo"]
            },
            "Partes Interesadas": {
                "paths": [
                    "/partes_menu",
                    "/partes",
                    "/parte",
                    "/partes_interesadas",
                    "/parte_interesada"
                ],
                "endpoints": [
                    "partes_menu",
                    "partes",
                    "parte",
                    "partes_interesadas",
                    "parte_interesada"
                ]
            },
            "Contexto Interno": {
                "paths": ["/contexto_interno_menu", "/contexto_interno"],
                "endpoints": ["contexto_interno_menu", "contexto_interno"]
            },
            "Contexto Externo": {
                "paths": ["/contexto_externo_menu", "/contexto_externo"],
                "endpoints": ["contexto_externo_menu", "contexto_externo"]
            },
            "DOFA": {
                "paths": ["/dofa_menu", "/dofa"],
                "endpoints": ["dofa_menu", "dofa"]
            },
            "PESI": {
                "paths": ["/pesi"],
                "endpoints": ["pesi"]
            },
            "Informe Revisión por la Dirección": {
                "paths": ["/revision_direccion"],
                "endpoints": ["revision_direccion"]
            },

            # Documentación
            "Listado Maestro de Documentos": {
                "paths": ["/docs_menu", "/docs", "/documentos"],
                "endpoints": ["docs_menu", "docs", "documentos"]
            },
            "Registro de Comunicaciones": {
                "paths": ["/comunicaciones_menu", "/comunicaciones"],
                "endpoints": ["comunicaciones_menu", "comunicaciones"]
            },
            "Requisitos Legales": {
                "paths": [
                    "/requisitos_menu",
                    "/requisitos",
                    "/requisito_legal",
                    "/req_legal"
                ],
                "endpoints": [
                    "requisitos_menu",
                    "requisitos",
                    "requisito_legal",
                    "req_legal"
                ]
            },

            # Operación y Control
            "Gestión de Activos de Información": {
                "paths": [
                    "/inventario_software_menu",
                    "/inventario_software",
                    "/inventario_ia_menu",
                    "/inventario_ia",
                    "/inventario_informacion_menu",
                    "/inventario_informacion",
                    "/inventario_datos_personales_menu",
                    "/inventario_datos_personales",
                    "/inventario_fisico_menu",
                    "/inventario_fisico",
                    "/valor_confidencialidad",
                    "/valor_integridad",
                    "/valor_disponibilidad",
                    "/valor_criticidad_activo",
                    "/duenos_info"
                ],
                "endpoints": [
                    "inventario_software",
                    "inventario_ia",
                    "inventario_informacion",
                    "inventario_datos_personales",
                    "inventario_fisico",
                    "valor_confidencialidad",
                    "valor_integridad",
                    "valor_disponibilidad",
                    "valor_criticidad_activo",
                    "duenos_info"
                ]
            },
            "Matrices de Activos": {
                "paths": [
                    "/inventario_software_menu",
                    "/inventario_software",
                    "/inventario_ia_menu",
                    "/inventario_ia",
                    "/inventario_informacion_menu",
                    "/inventario_informacion",
                    "/inventario_datos_personales_menu",
                    "/inventario_datos_personales",
                    "/inventario_fisico_menu",
                    "/inventario_fisico"
                ],
                "endpoints": [
                    "inventario_software",
                    "inventario_ia",
                    "inventario_informacion",
                    "inventario_datos_personales",
                    "inventario_fisico"
                ]
            },
            "Inventario de Software": {
                "paths": ["/inventario_software_menu", "/inventario_software"],
                "endpoints": ["inventario_software"]
            },
            "Inventario de IA (ISO 42001)": {
                "paths": ["/inventario_ia_menu", "/inventario_ia"],
                "endpoints": ["inventario_ia"]
            },
            "Inventario de Información": {
                "paths": ["/inventario_informacion_menu", "/inventario_informacion"],
                "endpoints": ["inventario_informacion"]
            },
            "Inventario de Datos Personales": {
                "paths": ["/inventario_datos_personales_menu", "/inventario_datos_personales"],
                "endpoints": ["inventario_datos_personales"]
            },
            "Inventario Físico": {
                "paths": ["/inventario_fisico_menu", "/inventario_fisico"],
                "endpoints": ["inventario_fisico"]
            },
            "Tablas de Valoración": {
                "paths": [
                    "/valor_confidencialidad",
                    "/valor_integridad",
                    "/valor_disponibilidad",
                    "/valor_criticidad_activo"
                ],
                "endpoints": [
                    "valor_confidencialidad",
                    "valor_integridad",
                    "valor_disponibilidad",
                    "valor_criticidad_activo"
                ]
            },
            "Confidencialidad": {
                "paths": ["/valor_confidencialidad"],
                "endpoints": ["valor_confidencialidad"]
            },
            "Integridad": {
                "paths": ["/valor_integridad"],
                "endpoints": ["valor_integridad"]
            },
            "Disponibilidad": {
                "paths": ["/valor_disponibilidad"],
                "endpoints": ["valor_disponibilidad"]
            },
            "Criticidad del Activo": {
                "paths": ["/valor_criticidad_activo"],
                "endpoints": ["valor_criticidad_activo"]
            },
            "Dueños de Información": {
                "paths": ["/duenos_info"],
                "endpoints": ["duenos_info"]
            },
            "Gestión de Accesos": {
                "paths": ["/accesos_menu", "/accesos"],
                "endpoints": ["accesos"]
            },
            "Revisión de Accesos": {
                "paths": ["/revision_accesos_menu", "/revision_accesos"],
                "endpoints": ["revision_accesos"]
            },
            "Gestión de Cambios (RFC)": {
                "paths": ["/rfc_menu", "/rfc"],
                "endpoints": ["rfc"]
            },

            # Gestión de Eventos
            "Registro de Incidentes": {
                "paths": ["/incidentes"],
                "endpoints": ["incidentes", "incidente"]
            },
            "Planes de Respuesta a Incidentes": {
                "paths": ["/planes_respuesta_incidentes"],
                "endpoints": ["ir_catalog", "ir_plan_form", "ir_plan_detail", "ir_step_form", "ir_runs", "ir_run_new", "ir_run_detail", "ir_tracking"]
            },
            "Registro de Vulnerabilidades": {
                "paths": ["/vulnerabilidades_menu", "/vulnerabilidades"],
                "endpoints": ["vulnerabilidades", "vulnerabilidad", "vuln"]
            },
            "Pruebas SAST": {
                "paths": [
                    "/pruebas_sast",
                    "/pruebas_sast/informes",
                    "/pruebas_sast/config",
                    "/pruebas_sast/models",
                    "/pruebas_sast/start",
                    "/pruebas_sast/track",
                    "/pruebas_sast/progress",
                    "/pruebas_sast/result",
                    "/pruebas_sast/download"
                ],
                "endpoints": [
                    "sast_index",
                    "sast_reports",
                    "sast_report_detail",
                    "sast_config",
                    "sast_models",
                    "sast_start",
                    "sast_track",
                    "sast_progress",
                    "sast_result",
                    "sast_download_pdf",
                    "sast_download_json"
                ]
            },
            "Modelamiento de Amenazas": {
                "paths": ["/modelamiento_amenazas", "/vulnerabilidades/threat_model"],
                "endpoints": ["threat_model"]
            },
            "Superficie de Ataque y Escenarios": {
                "paths": ["/superficie_ataque"],
                "endpoints": ["attack_auto"]
            },
            "Plan de Remediación": {
                "paths": ["/plan_remediacion_menu", "/plan_remediacion"],
                "endpoints": [
                    "plan_remediacion_menu",
                    "plan_remediacion_matriz",
                    "plan_remediacion_nuevo",
                    "plan_remediacion_edit",
                    "plan_remediacion_detalle",
                    "plan_remediacion_delete",
                    "plan_remediacion_ai_sugerir"
                ]
            },

            # Competencias y Cultura
            "Campañas de Concientización": {
                "paths": [
                    "/campanias_concientizacion_menu",
                    "/campanias_concientizacion",
                    "/campanias_concientizacion_matriz"
                ],
                "endpoints": [
                    "campanias_concientizacion_menu",
                    "campanias_concientizacion",
                    "campanias_concientizacion_matriz"
                ]
            },
            "Plan de Concientización y Formación": {
                "paths": ["/plan_diseno_menu", "/plan_diseno"],
                "endpoints": ["plan_diseno"]
            },
            "Seguimiento Plan de Concientización y Formación": {
                "paths": ["/plan_cf/menu", "/plan_cf"],
                "endpoints": ["plan_cf"]
            },
            "Plan de Competencia": {
                "paths": [
                    "/plan_remediacion_competencias_menu",
                    "/plan_remediacion_competencias"
                ],
                "endpoints": ["plan_remediacion_competencias"]
            },

            # Cadena de Suministro
            "Vía web": {
                "paths": ["/cuestionario_proveedores_web"],
                "endpoints": ["cpw_admin", "cpw_evaluation", "cpw_detail"]
            },
            "Vía archivo": {
                "paths": ["/ingreso_informacion_proponente_archivo"],
                "endpoints": ["ingreso_informacion_proponente_archivo"]
            },
            "Evaluación de proponentes": {
                "paths": ["/cuestionarios_proveedores"],
                "endpoints": ["cuestionarios_proveedores"]
            },
            "Revisión en Listas Restrictivas": {
                "paths": ["/listas_restrictivas"],
                "endpoints": ["listas_restrictivas"]
            },
            "Security Scorecard de Terceros": {
                "paths": ["/proponentes/scorecard"],
                "endpoints": ["scorecard_proponentes", "proponentes"]
            },
            "Registro de Proveedores": {
                "paths": ["/proveedores_menu", "/proveedores"],
                "endpoints": ["proveedores"]
            },

            # Continuidad del Negocio
            "Continuidad del Negocio (BCP/DRP)": {
                "paths": ["/bcp/dashboard"],
                "endpoints": ["bcp_dashboard"],
                "exact": True
            },
            "BIA": {
                "paths": ["/bcp/bia"],
                "endpoints": ["bcp_bia"]
            },
            "Procesos Críticos": {
                "paths": ["/bcp/procesos"],
                "endpoints": ["bcp_procesos"]
            },
            "Planes de Continuidad": {
                "paths": ["/bcp/planes"],
                "endpoints": ["bcp_planes"]
            },
            "DRP": {
                "paths": ["/bcp/drp"],
                "endpoints": ["bcp_drp"]
            },
            "Gestión de Crisis": {
                "paths": ["/bcp/crisis"],
                "endpoints": ["bcp_crisis"]
            },
            "Simulacros y Pruebas": {
                "paths": ["/bcp/pruebas"],
                "endpoints": ["bcp_pruebas"]
            },
            "Dependencias Críticas": {
                "paths": ["/bcp/dependencias"],
                "endpoints": ["bcp_dependencias"]
            },
            "Madurez BCP": {
                "paths": ["/bcp/madurez"],
                "endpoints": ["bcp_madurez"]
            },
            "Informe Ejecutivo AI": {
                "paths": ["/bcp/ia"],
                "endpoints": ["bcp_ia"]
            },
            "Métricas BCP": {
                "paths": ["/bcp/metricas"],
                "endpoints": ["bcp_metricas"]
            },

            # Medición y Mejora
            "Nivel de Madurez ISO-27001:2022": {
                "paths": ["/madurez"],
                "endpoints": ["madurez"]
            },
            "Nivel de Madurez NIST CSF V.2.0": {
                "paths": ["/madurez_nist"],
                "endpoints": ["madurez_nist"]
            },
            "Nivel de Madurez Protección de Datos Personales": {
                "paths": ["/madurez_datos"],
                "endpoints": ["madurez_datos"]
            },
            "Nivel de Madurez PCI-DSS": {
                "paths": ["/madurez_pci"],
                "endpoints": ["madurez_pci"]
            },
            "Nivel de Madurez SOC 2": {
                "paths": ["/madurez_soc2"],
                "endpoints": ["madurez_soc2"]
            },
            "Nivel de Madurez ISO 22301": {
                "paths": ["/madurez_iso22301"],
                "endpoints": ["madurez_iso22301"]
            },
            "Nivel de Madurez Gestión de Inteligencia Artificial": {
                "paths": ["/madurez-ai"],
                "endpoints": ["madurez_ai"]
            },
            "Métricas": {
                "paths": ["/metricas"],
                "endpoints": ["metricas"]
            },
            "Métricas de Riesgos": {
                "paths": ["/metricas/riesgos"],
                "endpoints": ["metricas_riesgos"]
            },
            "Métricas de Incidentes": {
                "paths": ["/metricas/incidentes"],
                "endpoints": ["metricas_incidentes"]
            },
            "Métricas de Vulnerabilidades": {
                "paths": ["/metricas/vulnerabilidades"],
                "endpoints": ["metricas_vulnerabilidades"]
            },
            "Métrica Cultura de Seguridad": {
                "paths": ["/metricas/cultura"],
                "endpoints": ["metricas_cultura"]
            },
            "Métricas Planes de Mejora": {
                "paths": ["/metricas/mejora"],
                "endpoints": ["metricas_mejora"]
            },
            "Configuración de Parámetros": {
                "paths": ["/metricas/configuracion"],
                "endpoints": ["metricas_configuracion"]
            },
            "Parámetros de Incidentes": {
                "paths": ["/metricas/configuracion/incidentes"],
                "endpoints": ["metricas_configuracion_incidentes"]
            },
            "Parámetros de Vulnerabilidades": {
                "paths": ["/metricas/configuracion/vulnerabilidades"],
                "endpoints": ["metricas_configuracion_vulnerabilidades"]
            },
            "Parámetros de Cultura": {
                "paths": ["/metricas/configuracion/cultura"],
                "endpoints": ["metricas_configuracion_cultura"]
            },
            "Parámetros de Riesgos": {
                "paths": ["/metricas/configuracion/riesgos"],
                "endpoints": ["metricas_configuracion_riesgos"]
            },
            "Planes de Acción del Sistema de Gestión (Mejora)": {
                "paths": ["/mejora_menu", "/mejora"],
                "endpoints": ["mejora"]
            },
            "Matriz de Planes de Acción": {
                "paths": ["/planes_accion"],
                "endpoints": ["planes_accion_dashboard"],
                "exact": True
            },
            "Registrar Plan de Acción": {
                "paths": ["/planes_accion/nuevo"],
                "endpoints": ["planes_accion_new"]
            },

            # Reportes
            "Reportes": {
                "paths": ["/reportes"],
                "endpoints": ["reportes"]
            },

            # Cumplimiento Continuo
            "Dashboard": {
                "paths": ["/cumplimiento_continuo"],
                "endpoints": ["cumplimiento_continuo"],
                "exact": True
            },
            "Herramienta XDR (Wazuh)": {
                "paths": ["/cumplimiento_continuo/wazuh"],
                "endpoints": ["cumplimiento_continuo_wazuh"]
            },
            "Sincronización": {
                "paths": ["/cumplimiento_continuo/sincronizacion"],
                "endpoints": ["cumplimiento_continuo_sincronizacion"]
            },
            "Gobierno de Firewall": {
                "paths": ["/cumplimiento_continuo/firewall"],
                "endpoints": ["cumplimiento_continuo_firewall", "fwgov"]
            },
            "ISO 27001": {
                "paths": ["/cumplimiento_continuo/estandar/ISO27001"],
                "endpoints": ["cumplimiento_continuo_estandar"]
            },
            "SOC 2": {
                "paths": ["/cumplimiento_continuo/estandar/SOC2"],
                "endpoints": ["cumplimiento_continuo_estandar"]
            },
            "PCI-DSS": {
                "paths": ["/cumplimiento_continuo/estandar/PCIDSS"],
                "endpoints": ["cumplimiento_continuo_estandar"]
            },
            "NIST CSF 2.0": {
                "paths": ["/cumplimiento_continuo/estandar/NISTCSF"],
                "endpoints": ["cumplimiento_continuo_estandar"]
            },
            "Evidencias": {
                "paths": ["/cumplimiento_continuo/evidencias"],
                "endpoints": ["cumplimiento_continuo_evidencias"]
            },
            "Planes de Acción": {
                "paths": ["/cumplimiento_continuo/planes"],
                "endpoints": ["cumplimiento_continuo_planes"]
            },

            # Administración
            "Configuración Parámetros de la Empresa": {
                "paths": ["/areas_", "/config/email"],
                "endpoints": ["areas", "config_email"]
            },
            "Estructura Organizacional": {
                "paths": ["/areas_area", "/areas_division"],
                "endpoints": ["areas_area", "areas_division"]
            },
            "Áreas": {
                "paths": ["/areas_area"],
                "endpoints": ["areas_area"]
            },
            "Divisiones": {
                "paths": ["/areas_division"],
                "endpoints": ["areas_division"]
            },
            "Parámetros Generales": {
                "paths": ["/config/email"],
                "endpoints": ["config_email"]
            },
            "Configuración del Correo": {
                "paths": ["/config/email"],
                "endpoints": ["config_email"]
            },
            "Gestión de Usuarios": {
                "paths": ["/usuarios"],
                "endpoints": ["usuarios"]
            },
            "Descargar aplicación móvil": {
                "paths": ["/aplicacion_movil"],
                "endpoints": ["aplicacion_movil", "mobile_app_user_download"]
            },
            "Aplicación móvil": {
                "paths": ["/admin/mobile-app"],
                "endpoints": ["admin_mobile_app", "admin_mobile_app_download"]
            },
            "Centro de Alertas": {
                "paths": ["/alertas"],
                "endpoints": ["alert_center"],
                "exact": True
            },
            "Administración de Alertas": {
                "paths": ["/admin/alertas"],
                "endpoints": ["admin_alertas"],
                "exact": True
            },
            "Constructor del Centro de Control": {
                "paths": ["/admin/dashboard_config"],
                "endpoints": ["dashboard_config"],
                "exact": True
            },
            "Logs de Auditoría": {
                "paths": ["/admin/logs_auditoria"],
                "endpoints": ["logs_auditoria"]
            },
            "Chat con Asistente": {
                "paths": ["/chatgpt_view"],
                "endpoints": ["chatgpt_view"]
            },
        }

        # ============================================================
        # Determina la opción activa usando la coincidencia más específica
        # Esto evita que Dashboard (/cumplimiento_continuo) quede activo
        # cuando se entra a /cumplimiento_continuo/sincronizacion, etc.
        # ============================================================
        def _item_candidate_score(item):
            href = _norm_path(item.get("href", ""))
            label = item.get("label", "")
            # Matriz IA y sus formularios: mantener la opción activa.
            if current_path.startswith('/inventario_ia') and item.get('module') == 'Inventario de IA':
                return 10000
            # Centro de Reportes: mantener la opción activa incluso con filtros.
            if (current_path == '/reportes' or current_path.startswith('/reportes/')) and href == '/reportes':
                return 10000
            rules = MENU_ACTIVE_RULES.get(label, {})
            exact = bool(rules.get("exact", False))

            best = -1

            candidate_paths = []
            if href not in ("", "#", "javascript:void(0);"):
                candidate_paths.append(href)

            candidate_paths.extend(rules.get("paths", []) or [])

            for p in candidate_paths:
                p = _norm_path(p)
                if p in ("", "#", "javascript:void(0);"):
                    continue

                if exact:
                    if current_path == p:
                        best = max(best, len(p))
                else:
                    if _path_matches(p):
                        best = max(best, len(p))

            # Endpoint como respaldo. No se usa para distinguir estándares,
            # porque todos pueden compartir cumplimiento_continuo_estandar.
            for ep in rules.get("endpoints", []) or []:
                if _endpoint_matches(ep):
                    if label in ("ISO 27001", "SOC 2", "PCI-DSS", "NIST CSF 2.0"):
                        if best >= 0:
                            best = max(best, 500 + best)
                    else:
                        best = max(best, 100)

            return best

        def _flatten_items(items):
            out = []
            for it in items:
                out.append(it)
                for ch in it.get("children") or []:
                    out.extend(_flatten_items([ch]))
            return out

        # Primero filtra por permisos
        sections = []
        all_leaf_items = []

        for sec in MENU_SECTIONS:
            allowed_items = filtrar_items_menu(
                sec.get("items", []), usuario_actual,
                seccion_admin=(sec.get("title") == "Administración")
            )
            if allowed_items:
                sec2 = dict(sec)
                sec2["items"] = allowed_items
                sections.append(sec2)
                all_leaf_items.extend([
                    x for x in _flatten_items(allowed_items)
                    if not x.get("children")
                ])

        # Calcula el mejor candidato global
        best_item_key = None
        best_score = -1

        for item in all_leaf_items:
            score = _item_candidate_score(item)
            if score > best_score:
                best_score = score
                best_item_key = (
                    item.get("label", ""),
                    _norm_path(item.get("href", ""))
                )

        def _item_is_active(item):
            if item.get("children"):
                return False

            key = (
                item.get("label", ""),
                _norm_path(item.get("href", ""))
            )

            return best_score >= 0 and key == best_item_key

        def _mark_items(items):
            marked = []

            for it in items:
                item = dict(it)
                children = item.get("children") or []

                children_marked = _mark_items(children) if children else []
                item["_children"] = children_marked

                active_self = _item_is_active(item)
                active_child = any(ch.get("_active_tree") for ch in children_marked)

                item["_active"] = active_self
                item["_active_tree"] = active_self or active_child

                marked.append(item)

            return marked

        for sec in sections:
            sec["items"] = _mark_items(sec.get("items", []))
            sec["_active_tree"] = any(it.get("_active_tree") for it in sec["items"])

        return render_template_string("""
        <aside id="sgsiGlobalMenu" class="sgsi-global-menu-wrap">

<div class="sgsi-menu-fixed-shell">

            <div class="sgsi-menu-scroll-only" id="sgsiGlobalMenuScroll">

              <div class="sgsi-global-menu-list">

                <a class="sgsi-global-root-toggle sgsi-global-panel-control-btn {% if center_active %}sgsi-center-active{% endif %}" href="/">
                  <i class="bi bi-speedometer2"></i>
                  <span>Centro de Control</span>
                </a>

                {% macro render_items(items, prefix) %}
                  {% for it in items %}
                    {% set iid = prefix ~ "_item_" ~ loop.index %}

                    {% if it.get("_children") %}
                      <li class="sgsi-global-node">
                        <a class="sgsi-global-item sgsi-global-node-toggle {% if it.get('_active_tree') %}sgsi-active-tree{% endif %}"
                           href="javascript:void(0);"
                           data-target="{{ iid }}">
                          <i class="bi {{ it.get('icon','bi-box') }}"></i>
                          <span>{{ it["label"] }}</span>
                        </a>

                        <ul class="sgsi-global-panel sgsi-global-subpanel {% if it.get('_active_tree') %}sgsi-open{% endif %}" id="{{ iid }}">
                          {{ render_items(it["_children"], iid) }}
                        </ul>
                      </li>
                    {% else %}
                      <li>
                        <a class="sgsi-global-item {% if it.get('_active') %}sgsi-active{% endif %}"
                           href="{{ it.get('href', '#') }}">
                          <i class="bi {{ it.get('icon','bi-box') }}"></i>
                          <span>{{ it["label"] }}</span>
                        </a>
                      </li>
                    {% endif %}
                  {% endfor %}
                {% endmacro %}

                {% for sec in sections %}
                  {% set sid = "global_root_" ~ loop.index %}

                  <div class="sgsi-global-root-item">
                    <button class="btn sgsi-global-root-toggle {% if sec.get('_active_tree') %}sgsi-active-tree{% endif %}"
                            type="button"
                            data-target="{{ sid }}">
                      <i class="bi {{ sec.get('icon', 'bi-grid-1x2') }}"></i>
                      <span>{{ sec["title"] }}</span>
                    </button>

                    <ul class="sgsi-global-panel {% if sec.get('_active_tree') %}sgsi-open{% endif %}" id="{{ sid }}">
                      {{ render_items(sec["items"], sid) }}
                    </ul>
                  </div>
                {% endfor %}

              </div>
            </div>

          </div>
        </aside>

        <style>
          :root{
            /* Menú global unificado con Centro de Control */
            --sgsi-menu-w:245px;
            --sgsi-menu-left:0px;
            --sgsi-topbar-h:var(--arky-topbar-h, 58px);
            --sgsi-content-left:245px;
            --sgsi-card:#ffffff;
            --sgsi-purple:#074883;
            --sgsi-purple-2:#1d5fae;
            --sgsi-lav:#dcecff;
            --sgsi-lav-2:#c9e3ff;
            --sgsi-border:#a9cdeb;
            --sgsi-text:#0f3766;
            --sgsi-muted:#425f7f;
          }

          body{
            padding-left:var(--sgsi-content-left) !important;
          }

          #sgsiGlobalMenu,
          .sgsi-global-menu-wrap{
            position:fixed !important;
            top:var(--sgsi-topbar-h) !important;
            left:var(--sgsi-menu-left) !important;
            width:var(--sgsi-menu-w) !important;
            height:calc(100vh - var(--sgsi-topbar-h)) !important;
            z-index:999990 !important;
            pointer-events:none;
            transition:left .22s ease;
          }

          .sgsi-global-menu-arrow{
            position:absolute;
            right:-13px;
            top:16px;
            width:22px;
            height:50px;
            border-radius:999px;
            background:linear-gradient(135deg,var(--sgsi-purple),var(--sgsi-purple-2));
            color:#ffffff;
            display:flex;
            align-items:center;
            justify-content:center;
            cursor:pointer;
            box-shadow:0 10px 22px rgba(43,0,79,.22);
            border:2px solid #ffffff;
            z-index:20;
            pointer-events:auto;
          }

          .sgsi-global-menu-arrow .sgsi-arrow-icon{
            font-size:26px;
            font-weight:950;
            line-height:1;
            position:relative;
            top:-1px;
          }

          .sgsi-menu-fixed-shell{
            height:100%;
            width:100%;
            padding:8px 7px;
            border-radius:0 18px 18px 0;
            background:linear-gradient(180deg,rgba(238,247,255,.97) 0%,rgba(213,234,255,.95) 48%,rgba(198,222,245,.94) 100%);
            border:1px solid var(--sgsi-border);
            border-left:0;
            box-shadow:10px 0 30px rgba(28,91,160,.18), inset -1px 0 rgba(255,255,255,.65);
            backdrop-filter:blur(14px);
            -webkit-backdrop-filter:blur(14px);
            pointer-events:auto;
            transition:opacity .22s ease, transform .22s ease;
          }

          .sgsi-menu-scroll-only{
            height:100%;
            overflow-y:auto;
            overflow-x:hidden;
            padding-right:2px;
          }

          .sgsi-menu-scroll-only::-webkit-scrollbar{ width:7px; }
          .sgsi-menu-scroll-only::-webkit-scrollbar-thumb{ background:#b8a3d8; border-radius:999px; }
          .sgsi-menu-scroll-only::-webkit-scrollbar-track{ background:#eef4ff; border-radius:999px; }

          .sgsi-global-menu-list{
            display:flex;
            flex-direction:column;
            gap:7px;
          }

          .sgsi-global-root-item{
            display:block;
          }

          .sgsi-global-root-toggle,
          .sgsi-global-item,
          .sgsi-global-node-toggle{
            width:100%;
            display:flex !important;
            align-items:center;
            justify-content:flex-start;
            gap:7px;
            border:1px solid transparent !important;
            text-decoration:none !important;
            text-align:left;
            color:#26384f !important;
            background:transparent !important;
            font-weight:850;
            white-space:normal !important;
            line-height:1.15 !important;
            transition:all .18s ease;
          }

          .sgsi-global-root-toggle{
            font-size:.70rem !important;
            min-height:35px !important;
            padding:7px 8px !important;
            border-radius:11px !important;
          }

          .sgsi-global-item,
          .sgsi-global-node-toggle{
            font-size:.66rem !important;
            padding:6px 7px !important;
            border-radius:10px !important;
          }

          .sgsi-global-root-toggle:hover,
          .sgsi-global-node-toggle:hover{
            background:var(--sgsi-lav) !important;
            color:var(--sgsi-purple) !important;
            border-color:var(--sgsi-border) !important;
          }

          .sgsi-global-item:hover{
            background:#ffffff !important;
            color:var(--sgsi-purple) !important;
            box-shadow:0 8px 16px rgba(43,0,79,.08);
          }

          .sgsi-global-panel-control-btn.sgsi-center-active{
            background:linear-gradient(135deg,var(--sgsi-purple) 0%,var(--sgsi-purple-2) 58%,#3f8fd6 100%) !important;
            color:#ffffff !important;
            border:1px solid rgba(255,255,255,.40) !important;
            box-shadow:0 12px 26px rgba(75,11,130,.24) !important;
          }

          .sgsi-global-panel-control-btn.sgsi-center-active i,
          .sgsi-global-panel-control-btn.sgsi-center-active span{
            color:#ffffff !important;
          }

          .sgsi-global-node-toggle::after{
            content:"⌄";
            margin-left:auto;
            font-size:13px;
            font-weight:950;
            transition:transform .18s ease;
          }

          .sgsi-global-node-toggle.sgsi-active-tree::after{
            transform:rotate(180deg);
          }

          /* Capítulo principal activo */
          .sgsi-global-root-toggle.sgsi-active-tree{
            background:linear-gradient(135deg,var(--sgsi-purple),var(--sgsi-purple-2)) !important;
            color:#ffffff !important;
            border-color:rgba(255,255,255,.42) !important;
            box-shadow:0 8px 18px rgba(44,123,229,.28);
          }

          .sgsi-global-root-toggle.sgsi-active-tree i,
          .sgsi-global-root-toggle.sgsi-active-tree span{
            color:#ffffff !important;
          }

          /* Padres internos activos */
          .sgsi-global-node-toggle.sgsi-active-tree{
            background:linear-gradient(135deg,#c9e3ff,#ffffff) !important;
            color:var(--sgsi-purple) !important;
            border-color:var(--sgsi-border) !important;
          }

          .sgsi-global-node-toggle.sgsi-active-tree i,
          .sgsi-global-node-toggle.sgsi-active-tree span{
            color:var(--sgsi-purple) !important;
          }

          /* Opción final exacta activa */
          .sgsi-global-item.sgsi-active{
            background:linear-gradient(135deg,var(--sgsi-purple),var(--sgsi-purple-2)) !important;
            color:#ffffff !important;
            border-color:rgba(255,255,255,.42) !important;
            box-shadow:0 8px 18px rgba(44,123,229,.28);
          }

          .sgsi-global-item.sgsi-active i,
          .sgsi-global-item.sgsi-active span{
            color:#ffffff !important;
          }

          .sgsi-global-item i,
          .sgsi-global-root-toggle i,
          .sgsi-global-node-toggle i{
            color:inherit !important;
            width:16px;
            text-align:center;
            flex:0 0 auto;
          }

          .sgsi-global-panel{
            display:none;
            list-style:none;
            margin:4px 0 4px 0 !important;
            padding:4px 0 4px 6px !important;
            background:var(--sgsi-lav) !important;
            border:1px solid var(--sgsi-border) !important;
            border-radius:12px !important;
            overflow:visible !important;
          }

          .sgsi-global-subpanel{
            margin-left:5px !important;
            padding-left:8px !important;
            border-left:2px solid #a88fd3 !important;
          }

          .sgsi-global-panel.sgsi-open{
            display:block !important;
          }

          .sgsi-global-panel li{
            list-style:none;
            margin:0 0 3px 0;
            padding:0;
          }

          .sgsi-global-panel .sgsi-global-item,
          .sgsi-global-panel .sgsi-global-node-toggle{
            margin:3px 4px;
            background:rgba(241,247,255,.74) !important;
            border:1px solid rgba(181,205,230,.78) !important;
          }

          .sgsi-global-panel .sgsi-global-item.sgsi-active{
            background:linear-gradient(135deg,var(--sgsi-purple),var(--sgsi-purple-2)) !important;
            border-color:rgba(255,255,255,.42) !important;
          }

          body.sgsi-menu-collapsed{
            padding-left:0 !important;
          }

          body.sgsi-menu-collapsed #sgsiGlobalMenu{
            left:calc((var(--sgsi-menu-w) - 24px) * -1) !important;
          }

          body.sgsi-menu-collapsed #sgsiGlobalMenu .sgsi-menu-fixed-shell{
            opacity:0;
            pointer-events:none;
          }

          body.sgsi-menu-collapsed #sgsiGlobalMenuToggle .sgsi-arrow-icon{
            transform:rotate(180deg);
          }

          @media (max-width:992px){
            :root{
              --sgsi-content-left:0px;
            }

            body{
              padding-left:0 !important;
            }

            #sgsiGlobalMenu{
              left:calc((var(--sgsi-menu-w) - 24px) * -1) !important;
            }

            body:not(.sgsi-menu-collapsed) #sgsiGlobalMenu{
              left:0 !important;
            }
          }

          /* GRAC v10 — barra lateral compacta de iconos + expansión al pasar el mouse.
             Mantiene el contenido aprovechando el ancho libre, sin moverlo al pasar el cursor. */
          :root {
            --grac-rail-width:64px;
            --grac-menu-expanded-width:245px;
            --sgsi-content-left:var(--grac-rail-width);
          }
          body,
          body.sgsi-menu-collapsed {
            padding-left:var(--grac-rail-width) !important;
          }
          body.grac-menu-pinned {
            padding-left:var(--grac-menu-expanded-width) !important;
          }
          #sgsiGlobalMenu,
          body.sgsi-menu-collapsed #sgsiGlobalMenu {
            left:0 !important;
            width:var(--grac-menu-expanded-width) !important;
            pointer-events:none !important;
          }
          #sgsiGlobalMenu .sgsi-menu-fixed-shell,
          body.sgsi-menu-collapsed #sgsiGlobalMenu .sgsi-menu-fixed-shell {
            box-sizing:border-box !important;
            width:var(--grac-rail-width) !important;
            padding:8px 5px !important;
            opacity:1 !important;
            transform:none !important;
            pointer-events:auto !important;
            overflow:hidden !important;
            transition:width .22s ease,box-shadow .22s ease !important;
          }
          #sgsiGlobalMenu:is(:hover, :has(:focus-visible)) .sgsi-menu-fixed-shell,
          body.grac-menu-pinned #sgsiGlobalMenu .sgsi-menu-fixed-shell {
            width:var(--grac-menu-expanded-width) !important;
          }
          #sgsiGlobalMenu .sgsi-menu-scroll-only {
            overflow-y:auto !important;
            overflow-x:hidden !important;
            scrollbar-width:none;
          }
          #sgsiGlobalMenu:is(:hover, :has(:focus-visible)) .sgsi-menu-scroll-only,
          body.grac-menu-pinned #sgsiGlobalMenu .sgsi-menu-scroll-only {
            scrollbar-width:thin;
          }
          #sgsiGlobalMenu .sgsi-menu-scroll-only::-webkit-scrollbar {width:0 !important;}
          #sgsiGlobalMenu:is(:hover, :has(:focus-visible)) .sgsi-menu-scroll-only::-webkit-scrollbar,
          body.grac-menu-pinned #sgsiGlobalMenu .sgsi-menu-scroll-only::-webkit-scrollbar {
            width:6px !important;
          }
          #sgsiGlobalMenu .sgsi-global-root-toggle,
          #sgsiGlobalMenu .sgsi-global-panel-control-btn,
          #sgsiGlobalMenu button.sgsi-global-root-toggle {
            box-sizing:border-box !important;
            width:46px !important;
            max-width:46px !important;
            min-width:46px !important;
            min-height:38px !important;
            height:38px !important;
            margin:0 auto !important;
            padding:0 !important;
            display:flex !important;
            align-items:center !important;
            justify-content:center !important;
            gap:0 !important;
            overflow:hidden !important;
          }
          #sgsiGlobalMenu .sgsi-global-root-toggle > i,
          #sgsiGlobalMenu .sgsi-global-panel-control-btn > i {
            box-sizing:border-box !important;
            flex:0 0 20px !important;
            width:20px !important;
            text-align:center !important;
            font-size:1.05rem !important;
          }
          #sgsiGlobalMenu .sgsi-global-root-toggle > span,
          #sgsiGlobalMenu .sgsi-global-panel-control-btn > span,
          #sgsiGlobalMenu .sgsi-global-item > span,
          #sgsiGlobalMenu .sgsi-global-node-toggle > span {
            box-sizing:border-box !important;
            display:none !important;
          }
          #sgsiGlobalMenu .sgsi-global-root-toggle::after,
          #sgsiGlobalMenu .sgsi-global-node-toggle::after {
            display:none !important;
          }
          #sgsiGlobalMenu .sgsi-global-panel.sgsi-open {
            display:none !important;
          }
          #sgsiGlobalMenu:is(:hover, :has(:focus-visible)) .sgsi-global-panel.sgsi-open,
          body.grac-menu-pinned #sgsiGlobalMenu .sgsi-global-panel.sgsi-open {
            display:block !important;
          }
          #sgsiGlobalMenu:is(:hover, :has(:focus-visible)) .sgsi-global-root-toggle,
          #sgsiGlobalMenu:is(:hover, :has(:focus-visible)) .sgsi-global-panel-control-btn,
          body.grac-menu-pinned #sgsiGlobalMenu .sgsi-global-root-toggle,
          body.grac-menu-pinned #sgsiGlobalMenu .sgsi-global-panel-control-btn {
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
            margin:0 !important;
            padding:0 8px !important;
            justify-content:flex-start !important;
            gap:7px !important;
          }
          #sgsiGlobalMenu:is(:hover, :has(:focus-visible)) .sgsi-global-root-toggle > span,
          #sgsiGlobalMenu:is(:hover, :has(:focus-visible)) .sgsi-global-panel-control-btn > span,
          #sgsiGlobalMenu:is(:hover, :has(:focus-visible)) .sgsi-global-item > span,
          #sgsiGlobalMenu:is(:hover, :has(:focus-visible)) .sgsi-global-node-toggle > span,
          body.grac-menu-pinned #sgsiGlobalMenu .sgsi-global-root-toggle > span,
          body.grac-menu-pinned #sgsiGlobalMenu .sgsi-global-panel-control-btn > span,
          body.grac-menu-pinned #sgsiGlobalMenu .sgsi-global-item > span,
          body.grac-menu-pinned #sgsiGlobalMenu .sgsi-global-node-toggle > span {
            display:block !important;
            min-width:0 !important;
            flex:1 1 auto !important;
            white-space:normal !important;
          }
          #sgsiGlobalMenu:is(:hover, :has(:focus-visible)) .sgsi-global-root-toggle::after,
          #sgsiGlobalMenu:is(:hover, :has(:focus-visible)) .sgsi-global-node-toggle::after,
          body.grac-menu-pinned #sgsiGlobalMenu .sgsi-global-root-toggle::after,
          body.grac-menu-pinned #sgsiGlobalMenu .sgsi-global-node-toggle::after {
            display:block !important;
          }
          #sgsiGlobalMenu .sgsi-global-menu-arrow {
            right:calc(var(--grac-menu-expanded-width) - var(--grac-rail-width) - 12px) !important;
            transition:right .22s ease !important;
            pointer-events:auto !important;
          }
          #sgsiGlobalMenu:is(:hover, :has(:focus-visible)) .sgsi-global-menu-arrow,
          body.grac-menu-pinned #sgsiGlobalMenu .sgsi-global-menu-arrow {
            right:-12px !important;
          }
          #sgsiGlobalMenu .sgsi-global-menu-arrow .sgsi-arrow-icon {
            transform:none !important;
          }
          body.grac-menu-pinned #sgsiGlobalMenu .sgsi-global-menu-arrow .sgsi-arrow-icon {
            transform:rotate(180deg) !important;
          }
          @media(max-width:992px) {
            body,body.sgsi-menu-collapsed {padding-left:var(--grac-rail-width) !important;}
            body.grac-menu-pinned {padding-left:var(--grac-rail-width) !important;}
            #sgsiGlobalMenu {left:0 !important;}
          }

        </style>

        <script>
          (function(){
            const STORAGE_KEY = "sgsi_global_menu_scroll_top";

            function menuScroll(){
              return document.getElementById("sgsiGlobalMenuScroll");
            }

            function saveScroll(){
              const scroller = menuScroll();
              if(scroller){
                localStorage.setItem(STORAGE_KEY, String(scroller.scrollTop || 0));
              }
            }

            function restoreScroll(){
              const scroller = menuScroll();
              if(!scroller) return;

              const saved = parseInt(localStorage.getItem(STORAGE_KEY) || "0", 10);

              if(!isNaN(saved) && saved > 0){
                scroller.scrollTop = saved;
              }
            }

            function toggleMenu(trigger){
              const id = trigger.getAttribute("data-target");
              const panel = id ? document.getElementById(id) : null;

              if(!panel) return;

              const isOpen = panel.classList.contains("sgsi-open");

              if(isOpen){
                trigger.classList.remove("sgsi-active-tree");
                panel.classList.remove("sgsi-open");
              }else{
                trigger.classList.add("sgsi-active-tree");
                panel.classList.add("sgsi-open");
              }

              setTimeout(saveScroll, 80);
            }

            document.querySelectorAll("#sgsiGlobalMenu .sgsi-global-root-toggle, #sgsiGlobalMenu .sgsi-global-node-toggle").forEach(function(toggle){
              toggle.addEventListener("click", function(e){
                if(toggle.classList.contains("sgsi-global-panel-control-btn")) return;
                e.preventDefault();
                e.stopPropagation();
                toggleMenu(toggle);
              });
            });

            document.querySelectorAll("#sgsiGlobalMenu a[href]").forEach(function(link){
              link.addEventListener("click", saveScroll);
            });

            const scroller = menuScroll();

            if(scroller){
              scroller.addEventListener("scroll", saveScroll);
            }

            window.addEventListener("beforeunload", saveScroll);

            window.addEventListener("pageshow", function(){
              setTimeout(restoreScroll, 80);
            });

            setTimeout(restoreScroll, 80);
          })();
        </script>

    <script id="grac-hover-menu-v11">
      (function(){
        // El menú se controla únicamente con hover/foco: sin flecha de fijación.
        var menu = document.getElementById('sgsiGlobalMenu') || document.getElementById('sgsiLocalMenu');
        if (!menu) return;
        document.body.classList.remove('grac-menu-pinned', 'sgsi-menu-collapsed');
        // Elimina cualquier preferencia previa de fijación de la versión anterior.
        try {sessionStorage.removeItem('grac_menu_pinned_v10');} catch(e) {}
        // Conserva los nombres accesibles de los iconos cuando está contraído.
        menu.querySelectorAll('a,button').forEach(function(control){
          var labelNode = control.querySelector('span');
          var name = labelNode ? labelNode.textContent.trim() : '';
          if(name){
            control.setAttribute('aria-label',name);
            control.setAttribute('title',name);
          }
        });
      })();
    </script>
        """, sections=sections, center_active=(current_path == "/"))

    except Exception as e:
        print("Error construyendo menú global SGSI:", repr(e))
        return ""


