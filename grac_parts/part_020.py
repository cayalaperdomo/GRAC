@app.route("/pesi/<int:plan_id>/pdf")
@login_required
def pesi_pdf(plan_id):
    user = _pesi_permiso()

    if not user:
        return redirect(url_for("menu"))

    plan = _pesi_get_plan(plan_id)

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.7 * cm,
        leftMargin=1.7 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "PESITitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=17,
        leading=22,
        textColor=colors.HexColor("#1d4f8f"),
        spaceAfter=16
    )

    h1 = ParagraphStyle(
        "PESIH1",
        parent=styles["Heading1"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1d4f8f"),
        spaceBefore=12,
        spaceAfter=8
    )

    normal = ParagraphStyle(
        "PESINormal",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        alignment=TA_LEFT,
        spaceAfter=6
    )

    small = ParagraphStyle(
        "PESISmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10
    )

    story = []

    def P(txt, style=normal):
        safe = xml_escape(str(txt or "")).replace("\n", "<br/>")
        return Paragraph(safe, style)

    def section(title, body):
        story.append(Paragraph(xml_escape(title), h1))
        story.append(P(body))

    def make_table(data, widths=None, font_size=8):
        clean = []

        for row in data:
            clean.append([P(c, small) for c in row])

        t = Table(clean, colWidths=widths, repeatRows=1)

        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1d4f8f")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9bb9d6")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))

        story.append(t)
        story.append(Spacer(1, 10))

    versiones_default, estrategias_default, portafolio_default, cronograma_default, presupuesto_default = _pesi_default_json()

    versiones = _pesi_json_load(plan.get("versiones_json"), versiones_default)
    estrategias = _pesi_json_load(plan.get("estrategias_json"), estrategias_default)
    portafolio = _pesi_json_load(plan.get("portafolio_json"), portafolio_default)
    cronograma = _pesi_json_load(plan.get("cronograma_json"), cronograma_default)
    presupuesto = _pesi_json_load(plan.get("presupuesto_json"), presupuesto_default)

    # Portada
    story.append(Spacer(1, 80))
    story.append(Paragraph("PLAN ESTRATÉGICO DE SEGURIDAD DE LA INFORMACIÓN", title_style))
    story.append(Spacer(1, 30))
    story.append(Paragraph(xml_escape(plan.get("entidad") or "(NOMBRE DE LA ENTIDAD)"), title_style))
    story.append(Spacer(1, 24))
    story.append(Paragraph(xml_escape(plan.get("anio") or "AÑO"), title_style))
    story.append(PageBreak())

    # Control de versiones
    story.append(Paragraph("Control de Versiones", h1))

    rows_versiones = [["Versión", "Fecha", "Modificación"]]

    for r in versiones:
        rows_versiones.append([
            r.get("version", ""),
            r.get("fecha", ""),
            r.get("modificacion", "")
        ])

    make_table(rows_versiones, [3 * cm, 4 * cm, 10 * cm])

    story.append(PageBreak())

    # Tabla de contenido
    story.append(Paragraph("Tabla de contenido", h1))

    toc = [
        "PLAN DE SEGURIDAD Y PRIVACIDAD DE LA INFORMACIÓN",
        "1. OBJETIVO",
        "1.1 OBJETIVOS ESPECÍFICOS",
        "2. ALCANCE",
        "3. DOCUMENTOS DE REFERENCIA",
        "4. ESTADO ACTUAL DE LA ENTIDAD RESPECTO AL SISTEMA DE GESTIÓN DE SEGURIDAD DE LA INFORMACIÓN",
        "5. ESTRATEGIA DE SEGURIDAD DIGITAL",
        "5.1 DESCRIPCIÓN DE LAS ESTRATEGIAS",
        "5.2 PORTAFOLIO DE PROYECTOS / ACTIVIDADES",
        "5.3 CRONOGRAMA DE ACTIVIDADES / PROYECTOS",
        "5.4 ANÁLISIS PRESUPUESTAL",
        "6. RESPONSABLES",
        "7. APROBACIÓN",
    ]

    for item in toc:
        story.append(P(item))

    story.append(PageBreak())

    story.append(Paragraph("PLAN DE SEGURIDAD Y PRIVACIDAD DE LA INFORMACIÓN", title_style))

    section("1. OBJETIVO", plan.get("objetivo"))
    section("1.1 OBJETIVOS ESPECÍFICOS", plan.get("objetivos_especificos"))
    section("2. ALCANCE", plan.get("alcance"))
    section("3. DOCUMENTOS DE REFERENCIA", plan.get("documentos_referencia"))
    section("4. ESTADO ACTUAL DE LA ENTIDAD RESPECTO AL SISTEMA DE GESTIÓN DE SEGURIDAD DE LA INFORMACIÓN", plan.get("estado_actual"))
    section("5. ESTRATEGIA DE SEGURIDAD DIGITAL", plan.get("estrategia_seguridad"))

    story.append(Paragraph("5.1 DESCRIPCIÓN DE LAS ESTRATEGIAS ESPECÍFICAS / EJES", h1))

    rows = [["ESTRATEGIA / EJE", "DESCRIPCIÓN / OBJETIVO"]]

    for r in estrategias:
        rows.append([
            r.get("estrategia", ""),
            r.get("descripcion", "")
        ])

    make_table(rows, [5.2 * cm, 11.8 * cm])

    story.append(Paragraph("5.2 PORTAFOLIO DE PROYECTOS / ACTIVIDADES", h1))

    rows = [["ESTRATEGIA / EJE", "PROYECTO", "PRODUCTOS ESPERADOS"]]

    for r in portafolio:
        rows.append([
            r.get("estrategia", ""),
            r.get("proyecto", ""),
            r.get("producto", "")
        ])

    make_table(rows, [4.5 * cm, 6.2 * cm, 6.3 * cm])

    story.append(Paragraph("5.3 CRONOGRAMA DE ACTIVIDADES / PROYECTOS", h1))

    rows = [["AÑO", "TRIMESTRE", "ACTIVIDAD / PROYECTO", "RESPONSABLE", "ESTADO"]]

    for r in cronograma:
        rows.append([
            r.get("anio", ""),
            r.get("trimestre", ""),
            r.get("actividad", ""),
            r.get("responsable", ""),
            r.get("estado", "")
        ])

    make_table(rows, [2 * cm, 3 * cm, 6 * cm, 3.8 * cm, 2.2 * cm], font_size=7)

    story.append(Paragraph("5.4 ANÁLISIS PRESUPUESTAL", h1))

    rows = [["AÑO", "PROYECTO", "INVERSIÓN"]]

    for r in presupuesto:
        rows.append([
            r.get("anio", ""),
            r.get("proyecto", ""),
            r.get("inversion", "")
        ])

    make_table(rows, [2.5 * cm, 10.5 * cm, 4 * cm])

    section("6. RESPONSABLES", plan.get("responsables"))

    story.append(Paragraph("7. APROBACIÓN", h1))
    story.append(P("El presente plan ha sido sometido a consideración y conocimiento de la alta dirección con el objetivo de ser aprobado y aplicado conforme a lo definido."))

    make_table([
        ["ELABORÓ", "REVISÓ", "APROBÓ"],
        [
            f"Nombre: {plan.get('elaboro_nombre') or ''}\nCargo: {plan.get('elaboro_cargo') or ''}",
            f"Nombre: {plan.get('reviso_nombre') or ''}\nCargo: {plan.get('reviso_cargo') or ''}",
            f"Nombre: {plan.get('aprobo_nombre') or ''}\nCargo: {plan.get('aprobo_cargo') or ''}\nFecha: {plan.get('fecha_aprobacion') or ''}",
        ]
    ], [5.6 * cm, 5.6 * cm, 5.6 * cm])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#5b6b7a"))
        canvas.drawString(1.7 * cm, 1.0 * cm, "SGSI — GRAC | PESI")
        canvas.drawRightString(19.3 * cm, 1.0 * cm, f"Página {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)

    buffer.seek(0)

    filename = f"PESI_{secure_filename(plan.get('entidad') or 'Entidad')}_{plan.get('anio') or datetime.now().year}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )

# ========================================================================================================================================
#                                   MÓDULO INFORME DE RESULTADOS PARA REVISIÓN POR LA DIRECCIÓN
# ========================================================================================================================================

REV_DIR_DB_PATH = os.path.join(app.instance_path, "revision_direccion.db")


def get_rev_dir_db_connection():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(REV_DIR_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_rev_dir_db():
    conn = get_rev_dir_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS revision_direccion_informes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entidad TEXT,
            anio TEXT,
            periodo TEXT,
            fecha_informe TEXT,

            objetivos_json TEXT,
            riesgos_intro TEXT,
            riesgos_json TEXT,
            riesgos_conclusion TEXT,

            auditorias_texto TEXT,
            cuestiones_texto TEXT,
            dofa_json TEXT,

            desempeno_texto TEXT,
            partes_json TEXT,

            mejora_texto TEXT,
            mejora_json TEXT,

            elaboro_nombre TEXT,
            elaboro_cargo TEXT,
            reviso_nombre TEXT,
            reviso_cargo TEXT,
            aprobo_nombre TEXT,
            aprobo_cargo TEXT,
            fecha_aprobacion TEXT,

            creado_por TEXT,
            fecha_creacion TEXT,
            fecha_actualizacion TEXT
        )
    """)

    conn.commit()
    conn.close()


init_rev_dir_db()


def _revdir_user_actual():
    try:
        return User.query.get(session.get("user_id"))
    except Exception:
        return None


def _revdir_permiso():
    user = _revdir_user_actual()

    if not user:
        flash("Debe iniciar sesión.", "danger")
        return None

    if user.role not in ("admin", "auditor") and not verificar_permiso(user, "Informe Revisión por la Dirección"):
        flash("No tiene permiso para acceder al Informe de Revisión por la Dirección.", "danger")
        return None

    return user


def _revdir_json_load(txt, default=None):
    try:
        data = json.loads(txt or "")
        return data if isinstance(data, list) else (default or [])
    except Exception:
        return default or []


def _revdir_json_dump_from_form(prefix, campos):
    filas = []
    total = int(request.form.get(prefix + "_count") or 0)

    for i in range(total):
        row = {}
        vacia = True

        for campo in campos:
            val = (request.form.get(f"{prefix}_{campo}_{i}") or "").strip()
            row[campo] = val
            if val:
                vacia = False

        if not vacia:
            filas.append(row)

    return json.dumps(filas, ensure_ascii=False)


def _revdir_get_plan(informe_id):
    conn = get_rev_dir_db_connection()
    row = conn.execute("""
        SELECT *
        FROM revision_direccion_informes
        WHERE id = ?
    """, (informe_id,)).fetchone()
    conn.close()

    if not row:
        abort(404)

    return dict(row)


# ============================================================
# AUTOCARGA DESDE MÓDULOS EXISTENTES
# ============================================================

def _revdir_autocargar_objetivos():
    rows = []

    try:
        items = ObjetivoSGSI.query.order_by(ObjetivoSGSI.id.asc()).all()

        for it in items:
            rows.append({
                "objetivo": getattr(it, "objetivo", "") or "",
                "meta": str(getattr(it, "meta_pct", "") or ""),
                "resultado": "",
                "analisis": ""
            })
    except Exception as e:
        print("Error cargando objetivos para Revisión Dirección:", repr(e))

    if not rows:
        rows = [{"objetivo": "", "meta": "", "resultado": "", "analisis": ""}]

    return rows


def _revdir_autocargar_riesgos(anio=None):
    rows = []

    try:
        items = Riesgo.query.order_by(Riesgo.id.desc()).all()

        for r in items:
            fecha_base = (
                getattr(r, "fecha_revision", None)
                or getattr(r, "fecha_identificacion", None)
                or getattr(r, "fecha_implementacion", None)
                or ""
            )

            fecha_txt = str(fecha_base or "")

            if anio and fecha_txt and str(anio) not in fecha_txt:
                continue

            rows.append({
                "codigo": str(getattr(r, "codigo_riesgo", "") or ""),
                "riesgo": str(getattr(r, "riesgo", "") or getattr(r, "nombre_activo", "") or ""),
                "prob_inh": str(getattr(r, "prob_inh", "") or ""),
                "impacto_inh": str(getattr(r, "imp_inh", "") or ""),
                "riesgo_inh": str(getattr(r, "riesgo_inherente", "") or ""),
                "riesgo_residual": str(getattr(r, "riesgo_residual", "") or "")
            })

    except Exception as e:
        print("Error cargando riesgos para Revisión Dirección:", repr(e))

    if not rows:
        rows = [{
            "codigo": "",
            "riesgo": "",
            "prob_inh": "",
            "impacto_inh": "",
            "riesgo_inh": "",
            "riesgo_residual": ""
        }]

    return rows


def _revdir_autocargar_dofa():
    data = {
        "fortalezas": "",
        "debilidades": "",
        "oportunidades": "",
        "amenazas": "",
        "estrategias_fo": "",
        "estrategias_fa": "",
        "estrategias_do": "",
        "estrategias_da": ""
    }

    try:
        dofa = DofaAnalisis.query.order_by(DofaAnalisis.id.desc()).first()

        if dofa:
            data = {
                "fortalezas": getattr(dofa, "fortalezas", "") or "",
                "debilidades": getattr(dofa, "debilidades", "") or "",
                "oportunidades": getattr(dofa, "oportunidades", "") or "",
                "amenazas": getattr(dofa, "amenazas", "") or "",
                "estrategias_fo": getattr(dofa, "estrategias_fo", "") or "",
                "estrategias_fa": getattr(dofa, "estrategias_fa", "") or "",
                "estrategias_do": getattr(dofa, "estrategias_do", "") or "",
                "estrategias_da": getattr(dofa, "estrategias_da", "") or ""
            }
    except Exception as e:
        print("Error cargando DOFA para Revisión Dirección:", repr(e))

    return [data]


def _revdir_autocargar_partes_interesadas():
    rows = []

    posibles_modelos = [
        "ParteInteresada",
        "PartesInteresadas",
        "ParteInteresadaSGSI",
        "PartesInteresadasSGSI",
        "Interesado",
        "Stakeholder"
    ]

    for nombre_modelo in posibles_modelos:
        cls = globals().get(nombre_modelo)

        if not cls:
            continue

        try:
            items = cls.query.all()

            for it in items:
                nombre = (
                    getattr(it, "nombre", None)
                    or getattr(it, "parte_interesada", None)
                    or getattr(it, "interesado", None)
                    or getattr(it, "descripcion", None)
                    or ""
                )

                rows.append({
                    "parte": str(nombre or ""),
                    "analisis": ""
                })

            if rows:
                break
        except Exception:
            continue

    if not rows:
        rows = [{"parte": "", "analisis": ""}]

    return rows


def _revdir_default_mejora():
    return [
        {
            "perspectiva": "",
            "objetivo_seg_inf": "",
            "proyecto": ""
        }
    ]


def _revdir_default_dict(user):
    anio = str(datetime.now().year)

    objetivos = _revdir_autocargar_objetivos()
    riesgos = _revdir_autocargar_riesgos(anio)
    dofa = _revdir_autocargar_dofa()
    partes = _revdir_autocargar_partes_interesadas()
    mejora = _revdir_default_mejora()

    return {
        "id": None,
        "entidad": "",
        "anio": anio,
        "periodo": f"Enero - Diciembre {anio}",
        "fecha_informe": datetime.now().strftime("%Y-%m-%d"),

        "objetivos_json": json.dumps(objetivos, ensure_ascii=False),

        "riesgos_intro": "Describa el resultado general de la valoración de riesgos y el estado del plan de tratamiento para el año evaluado.",
        "riesgos_json": json.dumps(riesgos, ensure_ascii=False),
        "riesgos_conclusion": "",

        "auditorias_texto": "Describa los resultados de auditorías internas realizadas al Sistema de Gestión de Seguridad de la Información.",
        "cuestiones_texto": "Describa los cambios o actualizaciones relevantes en las cuestiones externas e internas que afectan el SGSI.",
        "dofa_json": json.dumps(dofa, ensure_ascii=False),

        "desempeno_texto": "Describa la retroalimentación sobre el desempeño de la seguridad de la información.",
        "partes_json": json.dumps(partes, ensure_ascii=False),

        "mejora_texto": "Describa las oportunidades de mejora continua identificadas para el SGSI.",
        "mejora_json": json.dumps(mejora, ensure_ascii=False),

        "elaboro_nombre": "",
        "elaboro_cargo": "",
        "reviso_nombre": "",
        "reviso_cargo": "",
        "aprobo_nombre": "",
        "aprobo_cargo": "",
        "fecha_aprobacion": "",

        "creado_por": getattr(user, "username", "Sistema"),
        "fecha_creacion": "",
        "fecha_actualizacion": "",
    }


def _revdir_form_data():
    return {
        "entidad": (request.form.get("entidad") or "").strip(),
        "anio": (request.form.get("anio") or "").strip(),
        "periodo": (request.form.get("periodo") or "").strip(),
        "fecha_informe": (request.form.get("fecha_informe") or "").strip(),

        "objetivos_json": _revdir_json_dump_from_form(
            "objetivos",
            ["objetivo", "meta", "resultado", "analisis"]
        ),

        "riesgos_intro": (request.form.get("riesgos_intro") or "").strip(),
        "riesgos_json": _revdir_json_dump_from_form(
            "riesgos",
            ["codigo", "riesgo", "prob_inh", "impacto_inh", "riesgo_inh", "riesgo_residual"]
        ),
        "riesgos_conclusion": (request.form.get("riesgos_conclusion") or "").strip(),

        "auditorias_texto": (request.form.get("auditorias_texto") or "").strip(),
        "cuestiones_texto": (request.form.get("cuestiones_texto") or "").strip(),
        "dofa_json": _revdir_json_dump_from_form(
            "dofa",
            ["fortalezas", "debilidades", "oportunidades", "amenazas", "estrategias_fo", "estrategias_fa", "estrategias_do", "estrategias_da"]
        ),

        "desempeno_texto": (request.form.get("desempeno_texto") or "").strip(),
        "partes_json": _revdir_json_dump_from_form(
            "partes",
            ["parte", "analisis"]
        ),

        "mejora_texto": (request.form.get("mejora_texto") or "").strip(),
        "mejora_json": _revdir_json_dump_from_form(
            "mejora",
            ["perspectiva", "objetivo_seg_inf", "proyecto"]
        ),

        "elaboro_nombre": (request.form.get("elaboro_nombre") or "").strip(),
        "elaboro_cargo": (request.form.get("elaboro_cargo") or "").strip(),
        "reviso_nombre": (request.form.get("reviso_nombre") or "").strip(),
        "reviso_cargo": (request.form.get("reviso_cargo") or "").strip(),
        "aprobo_nombre": (request.form.get("aprobo_nombre") or "").strip(),
        "aprobo_cargo": (request.form.get("aprobo_cargo") or "").strip(),
        "fecha_aprobacion": (request.form.get("fecha_aprobacion") or "").strip(),
    }


def _revdir_insertar_desde_form(user):
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = _revdir_form_data()

    if not data["entidad"]:
        data["entidad"] = "Entidad sin nombre"

    data["creado_por"] = getattr(user, "username", "Sistema")
    data["fecha_creacion"] = ahora
    data["fecha_actualizacion"] = ahora

    conn = get_rev_dir_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO revision_direccion_informes (
            entidad, anio, periodo, fecha_informe,
            objetivos_json,
            riesgos_intro, riesgos_json, riesgos_conclusion,
            auditorias_texto, cuestiones_texto, dofa_json,
            desempeno_texto, partes_json,
            mejora_texto, mejora_json,
            elaboro_nombre, elaboro_cargo, reviso_nombre, reviso_cargo,
            aprobo_nombre, aprobo_cargo, fecha_aprobacion,
            creado_por, fecha_creacion, fecha_actualizacion
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["entidad"], data["anio"], data["periodo"], data["fecha_informe"],
        data["objetivos_json"],
        data["riesgos_intro"], data["riesgos_json"], data["riesgos_conclusion"],
        data["auditorias_texto"], data["cuestiones_texto"], data["dofa_json"],
        data["desempeno_texto"], data["partes_json"],
        data["mejora_texto"], data["mejora_json"],
        data["elaboro_nombre"], data["elaboro_cargo"], data["reviso_nombre"], data["reviso_cargo"],
        data["aprobo_nombre"], data["aprobo_cargo"], data["fecha_aprobacion"],
        data["creado_por"], data["fecha_creacion"], data["fecha_actualizacion"]
    ))

    nuevo_id = cur.lastrowid
    conn.commit()
    conn.close()

    try:
        registrar_log(data["creado_por"], f"Creó Informe Revisión por la Dirección: {data['entidad']} - {data['anio']}")
    except Exception:
        pass

    return nuevo_id


def _revdir_actualizar_desde_form(informe_id, user):
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = _revdir_form_data()

    if not data["entidad"]:
        data["entidad"] = "Entidad sin nombre"

    conn = get_rev_dir_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE revision_direccion_informes
        SET
            entidad = ?,
            anio = ?,
            periodo = ?,
            fecha_informe = ?,
            objetivos_json = ?,
            riesgos_intro = ?,
            riesgos_json = ?,
            riesgos_conclusion = ?,
            auditorias_texto = ?,
            cuestiones_texto = ?,
            dofa_json = ?,
            desempeno_texto = ?,
            partes_json = ?,
            mejora_texto = ?,
            mejora_json = ?,
            elaboro_nombre = ?,
            elaboro_cargo = ?,
            reviso_nombre = ?,
            reviso_cargo = ?,
            aprobo_nombre = ?,
            aprobo_cargo = ?,
            fecha_aprobacion = ?,
            fecha_actualizacion = ?
        WHERE id = ?
    """, (
        data["entidad"], data["anio"], data["periodo"], data["fecha_informe"],
        data["objetivos_json"],
        data["riesgos_intro"], data["riesgos_json"], data["riesgos_conclusion"],
        data["auditorias_texto"], data["cuestiones_texto"], data["dofa_json"],
        data["desempeno_texto"], data["partes_json"],
        data["mejora_texto"], data["mejora_json"],
        data["elaboro_nombre"], data["elaboro_cargo"], data["reviso_nombre"], data["reviso_cargo"],
        data["aprobo_nombre"], data["aprobo_cargo"], data["fecha_aprobacion"],
        ahora,
        informe_id
    ))

    conn.commit()
    conn.close()

    try:
        registrar_log(getattr(user, "username", "Sistema"), f"Actualizó Informe Revisión por la Dirección: {data['entidad']} - {data['anio']}")
    except Exception:
        pass


def _revdir_css():
    return """
    <style>
      body {
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .revdir-shell {
        width:96%;
        max-width:1550px;
        margin:26px auto 30px auto;
      }

      .revdir-header-card {
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

      .revdir-header-overlay {
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

      .revdir-header-overlay::before {
        content:"📊";
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

      .revdir-title {
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .revdir-subtitle {
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .revdir-card {
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .revdir-section {
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:18px;
        margin-bottom:16px;
        box-shadow:0 8px 18px rgba(15,23,42,.07);
      }

      .section-title {
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }

      .table-responsive {
        overflow-x:auto;
        background:#ffffff;
        border-radius:14px;
        border:1px solid #dbe6f4;
      }

      .table thead th {
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-size:.78rem;
        font-weight:900 !important;
        border:none !important;
        white-space:nowrap;
        text-align:center;
        vertical-align:middle !important;
      }

      .table td {
        vertical-align:middle !important;
        font-size:.82rem;
      }

      .revdir-edit-table textarea {
        min-width:220px;
        min-height:82px;
      }

      .form-label {
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

      .form-control {
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }

      textarea.form-control {
        min-height:110px;
        resize:vertical;
      }

      textarea[readonly],
      input[readonly] {
        background:#eef5ff !important;
        color:#334155 !important;
        cursor:not-allowed;
      }

      .btn {
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .btn-primary {
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        border:none !important;
      }

      .btn-success {
        background:linear-gradient(135deg,#16803c,#22a55a) !important;
        border:none !important;
      }

      .btn-danger {
        background:linear-gradient(135deg,#b91c1c,#ef4444) !important;
        border:none !important;
      }

      .revdir-help {
        font-size:.78rem;
        color:#475569;
        margin-top:-8px;
        margin-bottom:12px;
      }

      .dofa-grid {
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:14px;
      }

      .dofa-quad {
        border-radius:16px;
        padding:8px 7px;
        min-height:190px;
        border:1px solid #dbe6f4;
        background:#f8fbff;
        box-shadow:0 8px 18px rgba(15,23,42,.06);
      }

      .dofa-quad-title {
        font-weight:950;
        font-size:.9rem;
        margin-bottom:8px;
        color:#0b4a8f;
      }

      .dofa-quad textarea {
        min-height:140px;
      }

      @media (max-width:768px) {
        .dofa-grid {
          grid-template-columns:1fr;
        }
      }
    </style>
    """


def _revdir_render_rows(prefix, rows, campos, labels, readonly=False, locked_fields=None, allow_add=True, allow_delete=True):
    locked_fields = locked_fields or []

    if not rows:
        rows = [{}]

    html_rows = ""

    for i, row in enumerate(rows):
        html_rows += "<tr>"

        for campo in campos:
            val = escape(row.get(campo, "") or "")

            # IMPORTANTE:
            # readonly sí se envía en POST.
            # disabled NO se envía, por eso no se usa aquí.
            ro = "readonly" if (readonly or campo in locked_fields) else ""

            html_rows += f"""
            <td>
              <textarea class="form-control form-control-sm" rows="3" name="{prefix}_{campo}_{i}" {ro}>{val}</textarea>
            </td>
            """

        if not readonly and allow_delete:
            html_rows += """
            <td class="text-center">
              <button type="button" class="btn btn-sm btn-outline-danger rounded-pill" onclick="revdirRemoveRow(this)">
                🗑️
              </button>
            </td>
            """

        html_rows += "</tr>"

    ths = "".join(f"<th>{escape(label)}</th>" for label in labels)

    if not readonly and allow_delete:
        ths += "<th>Acción</th>"

    add_btn = ""

    if not readonly and allow_add:
        add_btn = f"""
        <button type="button" class="btn btn-sm btn-outline-primary rounded-pill mt-2"
                onclick="revdirAddRow('{prefix}')">
          ➕ Agregar fila
        </button>
        """

    return f"""
    <div class="table-responsive">
      <table class="table table-bordered align-middle revdir-edit-table">
        <thead>
          <tr>{ths}</tr>
        </thead>
        <tbody id="{prefix}_tbody">
          {html_rows}
        </tbody>
      </table>
    </div>

    <input type="hidden" id="{prefix}_count" name="{prefix}_count" value="{len(rows)}">

    {add_btn}
    """


def _revdir_render_dofa_grid(dofa_rows, readonly=False):
    if not dofa_rows:
        dofa_rows = _revdir_autocargar_dofa()

    d = dofa_rows[0] if isinstance(dofa_rows, list) and dofa_rows else {}
    ro = "readonly"

    campos = {
        "fortalezas": "✅ Fortalezas",
        "oportunidades": "🌟 Oportunidades",
        "debilidades": "⚠️ Debilidades",
        "amenazas": "🚨 Amenazas",
        "estrategias_fo": "Estrategias FO",
        "estrategias_fa": "Estrategias FA",
        "estrategias_do": "Estrategias DO",
        "estrategias_da": "Estrategias DA"
    }

    hidden = ""
    for campo in campos:
        hidden += f"""
        <input type="hidden" name="dofa_{campo}_0" value="{escape(d.get(campo, '') or '')}">
        """

    html = f"""
    <input type="hidden" id="dofa_count" name="dofa_count" value="1">
    {hidden}

    <div class="dofa-grid">
      <div class="dofa-quad">
        <div class="dofa-quad-title">✅ Fortalezas</div>
        <textarea class="form-control" rows="7" {ro}>{escape(d.get('fortalezas', '') or '')}</textarea>
      </div>

      <div class="dofa-quad">
        <div class="dofa-quad-title">🌟 Oportunidades</div>
        <textarea class="form-control" rows="7" {ro}>{escape(d.get('oportunidades', '') or '')}</textarea>
      </div>

      <div class="dofa-quad">
        <div class="dofa-quad-title">⚠️ Debilidades</div>
        <textarea class="form-control" rows="7" {ro}>{escape(d.get('debilidades', '') or '')}</textarea>
      </div>

      <div class="dofa-quad">
        <div class="dofa-quad-title">🚨 Amenazas</div>
        <textarea class="form-control" rows="7" {ro}>{escape(d.get('amenazas', '') or '')}</textarea>
      </div>

      <div class="dofa-quad">
        <div class="dofa-quad-title">Estrategias FO</div>
        <textarea class="form-control" rows="6" {ro}>{escape(d.get('estrategias_fo', '') or '')}</textarea>
      </div>

      <div class="dofa-quad">
        <div class="dofa-quad-title">Estrategias FA</div>
        <textarea class="form-control" rows="6" {ro}>{escape(d.get('estrategias_fa', '') or '')}</textarea>
      </div>

      <div class="dofa-quad">
        <div class="dofa-quad-title">Estrategias DO</div>
        <textarea class="form-control" rows="6" {ro}>{escape(d.get('estrategias_do', '') or '')}</textarea>
      </div>

      <div class="dofa-quad">
        <div class="dofa-quad-title">Estrategias DA</div>
        <textarea class="form-control" rows="6" {ro}>{escape(d.get('estrategias_da', '') or '')}</textarea>
      </div>
    </div>
    """

    return html


# ============================================================
# RUTAS
# ============================================================

@app.route("/revision_direccion")
@login_required
def revdir_index():
    user = _revdir_permiso()

    if not user:
        return redirect(url_for("menu"))

    conn = get_rev_dir_db_connection()
    informes = conn.execute("""
        SELECT *
        FROM revision_direccion_informes
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    informes = [dict(x) for x in informes]

    html = """
    <div class="revdir-shell">
      <div class="revdir-header-card">
        <div class="revdir-header-overlay">
          <div class="revdir-header-text">
            <h3 class="revdir-title">Informe de Resultados para Revisión por la Dirección</h3>
            <div class="revdir-subtitle">Gobierno / Dirección · SGSI</div>
          </div>
        </div>
      </div>

      <div class="revdir-card p-4">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
          <div>
            <div class="section-title">Informes registrados</div>
            <div class="text-muted small">Consulta, edición, PDF y eliminación según permisos.</div>
          </div>

          {% if user.role != 'auditor' %}
          <a href="{{ url_for('revdir_nuevo') }}" class="btn btn-primary rounded-pill px-4">
            ➕ Nuevo Informe
          </a>
          {% endif %}
        </div>

        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>ID</th>
                <th>Entidad</th>
                <th>Año</th>
                <th>Periodo</th>
                <th>Fecha</th>
                <th class="text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {% for r in informes %}
              <tr>
                <td>{{ r.id }}</td>
                <td>{{ r.entidad or '—' }}</td>
                <td>{{ r.anio or '—' }}</td>
                <td>{{ r.periodo or '—' }}</td>
                <td>{{ r.fecha_informe or '—' }}</td>
                <td class="text-center">
                  <div class="d-flex justify-content-center gap-2 flex-wrap">
                    <a class="btn btn-sm btn-outline-secondary rounded-pill" href="{{ url_for('revdir_ver', informe_id=r.id) }}">Ver</a>

                    {% if user.role != 'auditor' %}
                    <a class="btn btn-sm btn-outline-primary rounded-pill" href="{{ url_for('revdir_editar', informe_id=r.id) }}">Editar</a>
                    {% endif %}

                    <a class="btn btn-sm btn-danger rounded-pill" data-no-progress="true" href="{{ url_for('revdir_pdf', informe_id=r.id) }}">PDF</a>

                    {% if user.role != 'auditor' %}
                    <form method="POST"
                          action="{{ url_for('revdir_eliminar', informe_id=r.id) }}"
                          class="d-inline"
                          data-no-progress="true"
                          onsubmit="return confirm('¿Seguro que deseas eliminar este informe?');">
                      <button type="submit" class="btn btn-sm btn-outline-danger rounded-pill">Eliminar</button>
                    </form>
                    {% endif %}
                  </div>
                </td>
              </tr>
              {% else %}
              <tr>
                <td colspan="6" class="text-center text-muted py-4">No hay informes registrados.</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    """

    html += _revdir_css()

    return render_template_string(BASE, content=Markup(render_template_string(html, informes=informes, user=user)))


@app.route("/revision_direccion/nuevo", methods=["GET", "POST"])
@login_required
def revdir_nuevo():
    user = _revdir_permiso()

    if not user:
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El rol auditor solo puede consultar e imprimir informes.", "warning")
        return redirect(url_for("revdir_index"))

    if request.method == "POST":
        nuevo_id = _revdir_insertar_desde_form(user)
        flash("Informe creado correctamente.", "success")
        return redirect(url_for("revdir_editar", informe_id=nuevo_id))

    informe = _revdir_default_dict(user)
    return _revdir_render_form(informe, user, modo="nuevo")


@app.route("/revision_direccion/<int:informe_id>/ver")
@login_required
def revdir_ver(informe_id):
    user = _revdir_permiso()

    if not user:
        return redirect(url_for("menu"))

    informe = _revdir_get_plan(informe_id)
    return _revdir_render_form(informe, user, modo="ver")


@app.route("/revision_direccion/<int:informe_id>/editar", methods=["GET", "POST"])
@login_required
def revdir_editar(informe_id):
    user = _revdir_permiso()

    if not user:
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El rol auditor no puede editar informes.", "warning")
        return redirect(url_for("revdir_ver", informe_id=informe_id))

    informe = _revdir_get_plan(informe_id)

    if request.method == "POST":
        _revdir_actualizar_desde_form(informe_id, user)
        flash("Informe actualizado correctamente.", "success")
        return redirect(url_for("revdir_editar", informe_id=informe_id))

    return _revdir_render_form(informe, user, modo="editar")


@app.route("/revision_direccion/<int:informe_id>/eliminar", methods=["POST"])
@login_required
def revdir_eliminar(informe_id):
    user = _revdir_permiso()

    if not user:
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El rol auditor no puede eliminar informes.", "warning")
        return redirect(url_for("revdir_index"))

    informe = _revdir_get_plan(informe_id)

    conn = get_rev_dir_db_connection()
    conn.execute("DELETE FROM revision_direccion_informes WHERE id = ?", (informe_id,))
    conn.commit()
    conn.close()

    try:
        registrar_log(getattr(user, "username", "Sistema"), f"Eliminó Informe Revisión Dirección: {informe.get('entidad')} - {informe.get('anio')}")
    except Exception:
        pass

    flash("Informe eliminado correctamente.", "success")
    return redirect(url_for("revdir_index"))


def _revdir_render_form(informe, user, modo="editar"):
    readonly = (modo == "ver") or (user.role == "auditor")
    ro = "readonly" if readonly else ""
    disabled_submit = "d-none" if readonly else ""

    objetivos_rows = _revdir_json_load(informe.get("objetivos_json"), [])
    if not objetivos_rows:
        objetivos_rows = _revdir_autocargar_objetivos()

    riesgos_rows = _revdir_json_load(informe.get("riesgos_json"), [])
    if (
        not riesgos_rows
        or all(
            not str(r.get("prob_inh", "")).strip()
            and not str(r.get("impacto_inh", "")).strip()
            for r in riesgos_rows
        )
    ):
        riesgos_rows = _revdir_autocargar_riesgos(informe.get("anio"))

    dofa_rows = _revdir_json_load(informe.get("dofa_json"), [])
    if not dofa_rows:
        dofa_rows = _revdir_autocargar_dofa()

    partes_rows = _revdir_json_load(informe.get("partes_json"), [])
    if not partes_rows:
        partes_rows = _revdir_autocargar_partes_interesadas()

    mejora_rows = _revdir_json_load(informe.get("mejora_json"), [])
    if not mejora_rows:
        mejora_rows = _revdir_default_mejora()

    objetivos_html = _revdir_render_rows(
        "objetivos",
        objetivos_rows,
        ["objetivo", "meta", "resultado", "analisis"],
        ["Objetivo", "Meta", "Resultado", "Análisis"],
        readonly,
        locked_fields=["objetivo", "meta"],
        allow_add=False,
        allow_delete=False
    )

    riesgos_html = _revdir_render_rows(
        "riesgos",
        riesgos_rows,
        ["codigo", "riesgo", "prob_inh", "impacto_inh", "riesgo_inh", "riesgo_residual"],
        ["Código", "Riesgo", "Prob. Inh", "Impacto Inh", "Riesgo Inherente", "Riesgo Residual"],
        True,
        allow_add=False,
        allow_delete=False
    )

    dofa_html = _revdir_render_dofa_grid(dofa_rows, readonly=True)

    partes_html = _revdir_render_rows(
        "partes",
        partes_rows,
        ["parte", "analisis"],
        ["Parte Interesada", "Análisis"],
        readonly,
        locked_fields=["parte"],
        allow_add=False,
        allow_delete=False
    )

    mejora_html = _revdir_render_rows(
        "mejora",
        mejora_rows,
        ["perspectiva", "objetivo_seg_inf", "proyecto"],
        ["PERSPECTIVA", "OBJETIVO DE SEG. INF", "PROYECTO"],
        readonly,
        allow_add=True,
        allow_delete=True
    )

    titulo_modo = {
        "nuevo": "Nuevo Informe",
        "editar": "Editar Informe",
        "ver": "Ver Informe"
    }.get(modo, "Informe")

    pdf_button = ""
    if informe.get("id"):
        pdf_button = f"""
        <a href="{url_for('revdir_pdf', informe_id=informe.get('id'))}" data-no-progress="true" class="btn btn-danger rounded-pill px-4">
          📄 Generar PDF
        </a>
        """

    html = f"""
    <div class="revdir-shell">
      <div class="revdir-header-card">
        <div class="revdir-header-overlay">
          <div class="revdir-header-text">
            <h3 class="revdir-title">Informe de Resultados para Revisión por la Dirección</h3>
            <div class="revdir-subtitle">{titulo_modo} · Gobierno / Dirección · SGSI</div>
          </div>
        </div>
      </div>

      <form method="POST" class="revdir-card p-4">

        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-4">
          <div>
            <div class="section-title">{titulo_modo}</div>
            <div class="text-muted small">
              {"Consulta en solo lectura." if readonly else "Diligencia los campos editables del informe."}
            </div>
          </div>

          <div class="d-flex gap-2 flex-wrap">
            <a href="{url_for('revdir_index')}" class="btn btn-outline-secondary rounded-pill px-4">Volver</a>
            {pdf_button}
            <button type="submit" class="btn btn-success rounded-pill px-4 {disabled_submit}">
              💾 Guardar Informe
            </button>
          </div>
        </div>

        <div class="row g-3 mb-4">
          <div class="col-md-5">
            <label class="form-label">Entidad</label>
            <input class="form-control" name="entidad" value="{escape(informe.get('entidad') or '')}" {ro}>
          </div>
          <div class="col-md-2">
            <label class="form-label">Año</label>
            <input class="form-control" name="anio" value="{escape(informe.get('anio') or '')}" {ro}>
          </div>
          <div class="col-md-3">
            <label class="form-label">Periodo</label>
            <input class="form-control" name="periodo" value="{escape(informe.get('periodo') or '')}" {ro}>
          </div>
          <div class="col-md-2">
            <label class="form-label">Fecha informe</label>
            <input type="date" class="form-control" name="fecha_informe" value="{escape(informe.get('fecha_informe') or '')}" {ro}>
          </div>
        </div>

        <div class="revdir-section">
          <div class="section-title">A. RESULTADOS - MEDICIÓN OBJETIVOS DEL SGSI</div>
          <div class="revdir-help">Objetivo y meta se cargan automáticamente desde el módulo Objetivos del Sistema de Gestión. Resultado y análisis son editables.</div>
          {objetivos_html}
        </div>

        <div class="revdir-section">
          <div class="section-title">B. RESULTADOS DE LA VALORACIÓN DE RIESGOS Y ESTADO DEL PLAN DE TRATAMIENTO</div>
          <textarea class="form-control mb-3" rows="5" name="riesgos_intro" {ro}>{escape(informe.get('riesgos_intro') or '')}</textarea>
          <div class="revdir-help">La matriz se carga automáticamente desde Gestión de Riesgos para el año del informe y queda guardada al guardar el informe.</div>
          {riesgos_html}
          <label class="form-label mt-3">Conclusión</label>
          <textarea class="form-control" rows="4" name="riesgos_conclusion" {ro}>{escape(informe.get('riesgos_conclusion') or '')}</textarea>
        </div>

        <div class="revdir-section">
          <div class="section-title">C. AUDITORÍAS INTERNAS AL SGSI</div>
          <textarea class="form-control" rows="7" name="auditorias_texto" {ro}>{escape(informe.get('auditorias_texto') or '')}</textarea>
        </div>

        <div class="revdir-section">
          <div class="section-title">D. DEFINICIÓN EN LAS CUESTIONES EXTERNAS E INTERNAS</div>
          <textarea class="form-control mb-3" rows="6" name="cuestiones_texto" {ro}>{escape(informe.get('cuestiones_texto') or '')}</textarea>
          <div class="revdir-help">DOFA cargado automáticamente desde el módulo DOFA y queda guardado al guardar el informe.</div>
          {dofa_html}
        </div>

        <div class="revdir-section">
          <div class="section-title">E. RETROALIMENTACIÓN SOBRE EL DESEMPEÑO DE LA SEGURIDAD DE LA INFORMACIÓN</div>
          <textarea class="form-control" rows="7" name="desempeno_texto" {ro}>{escape(informe.get('desempeno_texto') or '')}</textarea>
        </div>

        <div class="revdir-section">
          <div class="section-title">F. RETROALIMENTACIÓN DE LAS PARTES INTERESADAS</div>
          <div class="revdir-help">Partes interesadas cargadas automáticamente; la columna Análisis es editable por el usuario.</div>
          {partes_html}
        </div>

        <div class="revdir-section">
          <div class="section-title">G. LAS OPORTUNIDADES DE MEJORA CONTINUA</div>
          <textarea class="form-control mb-3" rows="6" name="mejora_texto" {ro}>{escape(informe.get('mejora_texto') or '')}</textarea>
          {mejora_html}
        </div>

        <div class="revdir-section">
          <div class="section-title">Aprobación</div>
          <div class="row g-3">
            <div class="col-md-4">
              <label class="form-label">Elaboró - Nombre</label>
              <input class="form-control mb-2" name="elaboro_nombre" value="{escape(informe.get('elaboro_nombre') or '')}" {ro}>
              <label class="form-label">Elaboró - Cargo</label>
              <input class="form-control" name="elaboro_cargo" value="{escape(informe.get('elaboro_cargo') or '')}" {ro}>
            </div>
            <div class="col-md-4">
              <label class="form-label">Revisó - Nombre</label>
              <input class="form-control mb-2" name="reviso_nombre" value="{escape(informe.get('reviso_nombre') or '')}" {ro}>
              <label class="form-label">Revisó - Cargo</label>
              <input class="form-control" name="reviso_cargo" value="{escape(informe.get('reviso_cargo') or '')}" {ro}>
            </div>
            <div class="col-md-4">
              <label class="form-label">Aprobó - Nombre</label>
              <input class="form-control mb-2" name="aprobo_nombre" value="{escape(informe.get('aprobo_nombre') or '')}" {ro}>
              <label class="form-label">Aprobó - Cargo</label>
              <input class="form-control mb-2" name="aprobo_cargo" value="{escape(informe.get('aprobo_cargo') or '')}" {ro}>
              <label class="form-label">Fecha aprobación</label>
              <input type="date" class="form-control" name="fecha_aprobacion" value="{escape(informe.get('fecha_aprobacion') or '')}" {ro}>
            </div>
          </div>
        </div>

        <div class="text-center mt-4">
          <button type="submit" class="btn btn-success rounded-pill px-5 {disabled_submit}">
            💾 Guardar Informe
          </button>
        </div>
      </form>
    </div>

    <script>
      const REVDIR_TABLES = {{
        mejora: {{ fields: ["perspectiva", "objetivo_seg_inf", "proyecto"] }}
      }};

      function revdirAddRow(prefix) {{
        const cfg = REVDIR_TABLES[prefix];
        if (!cfg) return;

        const tbody = document.getElementById(prefix + "_tbody");
        const countInput = document.getElementById(prefix + "_count");

        if (!tbody || !countInput) return;

        let idx = parseInt(countInput.value || "0");
        let tr = document.createElement("tr");

        cfg.fields.forEach(function(field) {{
          let td = document.createElement("td");
          td.innerHTML = '<textarea class="form-control form-control-sm" rows="3" name="' + prefix + '_' + field + '_' + idx + '"></textarea>';
          tr.appendChild(td);
        }});

        let tdAction = document.createElement("td");
        tdAction.className = "text-center";
        tdAction.innerHTML = '<button type="button" class="btn btn-sm btn-outline-danger rounded-pill" onclick="revdirRemoveRow(this)">🗑️</button>';
        tr.appendChild(tdAction);

        tbody.appendChild(tr);
        countInput.value = idx + 1;
      }}

      function revdirRemoveRow(btn) {{
        const tr = btn.closest("tr");
        const tbody = tr ? tr.parentElement : null;

        if (!tr || !tbody) return;

        if (tbody.querySelectorAll("tr").length <= 1) {{
          tr.querySelectorAll("textarea").forEach(function(t) {{ t.value = ""; }});
          return;
        }}

        tr.remove();
      }}
    </script>
    """

    html += _revdir_css()

    return render_template_string(BASE, content=Markup(render_template_string(html, informe=informe, user=user)))


# ============================================================
# PDF CON PORTADA Y TABLA DE CONTENIDO EMPRESARIAL
# ============================================================

@app.route("/revision_direccion/<int:informe_id>/pdf")
@login_required
def revdir_pdf(informe_id):
    user = _revdir_permiso()

    if not user:
        return redirect(url_for("menu"))

    informe = _revdir_get_plan(informe_id)

    objetivos = _revdir_json_load(informe.get("objetivos_json"), [])
    riesgos = _revdir_json_load(informe.get("riesgos_json"), [])
    dofa = _revdir_json_load(informe.get("dofa_json"), [])
    partes = _revdir_json_load(informe.get("partes_json"), [])
    mejora = _revdir_json_load(informe.get("mejora_json"), [])

    dofa_data = dofa[0] if dofa else {}

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "RevDirTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=17,
        leading=22,
        textColor=colors.HexColor("#1d4f8f"),
        spaceAfter=14
    )

    cover_subtitle_style = ParagraphStyle(
        "RevDirCoverSubtitle",
        parent=styles["BodyText"],
        alignment=TA_CENTER,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6
    )

    h1 = ParagraphStyle(
        "RevDirH1",
        parent=styles["Heading1"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1d4f8f"),
        spaceBefore=10,
        spaceAfter=6
    )

    toc_title_style = ParagraphStyle(
        "RevDirTocTitle",
        parent=styles["Heading1"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1d4f8f"),
        spaceAfter=14
    )

    toc_item_style = ParagraphStyle(
        "RevDirTocItem",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        leftIndent=18,
        firstLineIndent=-14,
        spaceAfter=7,
        textColor=colors.HexColor("#101827")
    )

    normal = ParagraphStyle(
        "RevDirNormal",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
        spaceAfter=5
    )

    small = ParagraphStyle(
        "RevDirSmall",
        parent=styles["BodyText"],
        fontSize=7,
        leading=9
    )

    story = []

    def P(txt, style=normal):
        safe = xml_escape(str(txt or "")).replace("\n", "<br/>")
        return Paragraph(safe, style)

    def make_table(data, widths=None, font_size=7):
        clean = []
        for row in data:
            clean.append([P(c, small) for c in row])

        t = Table(clean, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1d4f8f")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9bb9d6")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

    def info_table():
        data = [
            ["Periodo", informe.get("periodo") or ""],
            ["Fecha del informe", informe.get("fecha_informe") or ""],
        ]

        clean = [[P(a, small), P(b, small)] for a, b in data]

        t = Table(clean, colWidths=[5 * cm, 9 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf3ff")),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1d4f8f")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9bb9d6")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))

        story.append(t)

    # ========================================================
    # PORTADA
    # ========================================================

    story.append(Spacer(1, 70))
    story.append(Paragraph("INFORME DE RESULTADOS", title_style))
    story.append(Paragraph("PARA REVISIÓN POR LA DIRECCIÓN", title_style))
    story.append(Spacer(1, 18))
    story.append(Paragraph("Sistema de Gestión de Seguridad de la Información — SGSI", cover_subtitle_style))
    story.append(Spacer(1, 30))
    story.append(Paragraph(xml_escape(informe.get("entidad") or "(NOMBRE DE LA ENTIDAD)"), title_style))
    story.append(Spacer(1, 24))
    info_table()
    story.append(PageBreak())

    # ========================================================
    # TABLA DE CONTENIDO INDENTADA
    # ========================================================

    story.append(Paragraph("Tabla de contenido", toc_title_style))

    toc = [
        ("A.", "RESULTADOS - MEDICIÓN OBJETIVOS DEL SISTEMA DE GESTIÓN DE SEGURIDAD DE LA INFORMACIÓN"),
        ("B.", "RESULTADOS DE LA VALORACIÓN DE RIESGOS Y ESTADO DEL PLAN DE TRATAMIENTO DE RIESGOS"),
        ("C.", "AUDITORÍAS INTERNAS AL SISTEMA DE GESTIÓN DE SEGURIDAD DE LA INFORMACIÓN"),
        ("D.", "DEFINICIÓN EN LAS CUESTIONES EXTERNAS E INTERNAS"),
        ("E.", "RETROALIMENTACIÓN SOBRE EL DESEMPEÑO DE LA SEGURIDAD DE LA INFORMACIÓN"),
        ("F.", "RETROALIMENTACIÓN DE LAS PARTES INTERESADAS"),
        ("G.", "LAS OPORTUNIDADES DE MEJORA CONTINUA"),
    ]

    for letra, texto in toc:
        story.append(Paragraph(f"<b>{letra}</b>&nbsp;&nbsp;{xml_escape(texto)}", toc_item_style))

    story.append(PageBreak())

    # ========================================================
    # CONTENIDO DEL INFORME
    # ========================================================

    story.append(Paragraph("A. RESULTADOS - MEDICIÓN OBJETIVOS DEL SGSI", h1))
    make_table(
        [["Objetivo", "Meta", "Resultado", "Análisis"]] +
        [[r.get("objetivo", ""), r.get("meta", ""), r.get("resultado", ""), r.get("analisis", "")] for r in objetivos],
        [5.2 * cm, 2.2 * cm, 4.2 * cm, 5.5 * cm]
    )

    story.append(Paragraph("B. RESULTADOS DE LA VALORACIÓN DE RIESGOS Y ESTADO DEL PLAN DE TRATAMIENTO", h1))
    story.append(P(informe.get("riesgos_intro")))

    make_table(
        [["Código", "Riesgo", "Prob. Inh", "Impacto Inh", "Riesgo Inherente", "Riesgo Residual"]] +
        [[
            r.get("codigo", ""),
            r.get("riesgo", ""),
            r.get("prob_inh", ""),
            r.get("impacto_inh", ""),
            r.get("riesgo_inh", ""),
            r.get("riesgo_residual", "")
        ] for r in riesgos],
        [2 * cm, 4.5 * cm, 2.4 * cm, 2.4 * cm, 3 * cm, 3 * cm],
        font_size=6
    )

    story.append(P("Conclusión: " + (informe.get("riesgos_conclusion") or "")))

    story.append(Paragraph("C. AUDITORÍAS INTERNAS AL SGSI", h1))
    story.append(P(informe.get("auditorias_texto")))

    story.append(Paragraph("D. DEFINICIÓN EN LAS CUESTIONES EXTERNAS E INTERNAS", h1))
    story.append(P(informe.get("cuestiones_texto")))

    make_table([
        ["Fortalezas", "Oportunidades"],
        [dofa_data.get("fortalezas", ""), dofa_data.get("oportunidades", "")],
        ["Debilidades", "Amenazas"],
        [dofa_data.get("debilidades", ""), dofa_data.get("amenazas", "")]
    ], [8.5 * cm, 8.5 * cm])

    make_table([
        ["Estrategias FO", "Estrategias FA"],
        [dofa_data.get("estrategias_fo", ""), dofa_data.get("estrategias_fa", "")],
        ["Estrategias DO", "Estrategias DA"],
        [dofa_data.get("estrategias_do", ""), dofa_data.get("estrategias_da", "")]
    ], [8.5 * cm, 8.5 * cm])

    story.append(Paragraph("E. RETROALIMENTACIÓN SOBRE EL DESEMPEÑO DE LA SEGURIDAD DE LA INFORMACIÓN", h1))
    story.append(P(informe.get("desempeno_texto")))

    story.append(Paragraph("F. RETROALIMENTACIÓN DE LAS PARTES INTERESADAS", h1))
    make_table(
        [["Parte Interesada", "Análisis"]] +
        [[r.get("parte", ""), r.get("analisis", "")] for r in partes],
        [6 * cm, 11 * cm]
    )

    story.append(Paragraph("G. LAS OPORTUNIDADES DE MEJORA CONTINUA", h1))
    story.append(P(informe.get("mejora_texto")))

    make_table(
        [["PERSPECTIVA", "OBJETIVO DE SEG. INF", "PROYECTO"]] +
        [[r.get("perspectiva", ""), r.get("objetivo_seg_inf", ""), r.get("proyecto", "")] for r in mejora],
        [4.5 * cm, 6.5 * cm, 6 * cm]
    )

    story.append(Paragraph("Aprobación", h1))

    make_table([
        ["Elaboró", "Revisó", "Aprobó"],
        [
            f"Nombre: {informe.get('elaboro_nombre') or ''}\nCargo: {informe.get('elaboro_cargo') or ''}",
            f"Nombre: {informe.get('reviso_nombre') or ''}\nCargo: {informe.get('reviso_cargo') or ''}",
            f"Nombre: {informe.get('aprobo_nombre') or ''}\nCargo: {informe.get('aprobo_cargo') or ''}\nFecha: {informe.get('fecha_aprobacion') or ''}",
        ]
    ], [5.6 * cm, 5.6 * cm, 5.6 * cm])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#5b6b7a"))
        canvas.drawString(1.5 * cm, 1.0 * cm, "SGSI — GRAC | Revisión por la Dirección")
        canvas.drawRightString(19.5 * cm, 1.0 * cm, f"Página {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)

    buffer.seek(0)

    filename = f"Informe_Revision_Direccion_{secure_filename(informe.get('entidad') or 'Entidad')}_{informe.get('anio') or datetime.now().year}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )

# ============================================================================================================================================
#                                      MÓDULO CONTINUIDAD DEL NEGOCIO (BCP/DRP) - GRAC
#                                      DB INDEPENDIENTE: instance/bcp_drp.db
# ============================================================================================================================================

BCP_MODULE_NAME = "Continuidad del Negocio (BCP/DRP)"
BCP_DB_PATH = os.path.join(app.instance_path, "bcp_drp.db")


def get_bcp_db_connection():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(BCP_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_bcp_db():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = get_bcp_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bcp_bia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proceso TEXT NOT NULL,
            responsable TEXT,
            area TEXT,
            criticidad TEXT,
            impacto_financiero TEXT,
            impacto_operacional TEXT,
            impacto_reputacional TEXT,
            impacto_legal TEXT,
            dependencias TEXT,
            tiempo_maximo_tolerable TEXT,
            rto_horas REAL DEFAULT 0,
            rpo_horas REAL DEFAULT 0,
            manual_alterno TEXT,
            sitio_alterno TEXT,
            proveedor_critico TEXT,
            estado TEXT DEFAULT 'Activo',
            informe_ai TEXT,
            plan_mejora_ai TEXT,
            creado_por TEXT,
            fecha_registro TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bcp_procesos_criticos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proceso TEXT NOT NULL,
            duenio TEXT,
            area TEXT,
            dependencias_tecnologicas TEXT,
            dependencias_humanas TEXT,
            proveedores_asociados TEXT,
            criticidad TEXT,
            sla_horas REAL DEFAULT 0,
            rto_horas REAL DEFAULT 0,
            rpo_horas REAL DEFAULT 0,
            descripcion TEXT,
            tiene_bcp TEXT DEFAULT 'No',
            creado_por TEXT,
            fecha_registro TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bcp_drp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            servidor TEXT NOT NULL,
            sistema TEXT,
            tipo_recuperacion TEXT,
            backup TEXT,
            ubicacion_backup TEXT,
            frecuencia_backup TEXT,
            backups_fallidos INTEGER DEFAULT 0,
            tiempo_recuperacion REAL DEFAULT 0,
            responsable TEXT,
            procedimiento TEXT,
            ultima_prueba TEXT,
            estado TEXT DEFAULT 'Pendiente',
            observaciones TEXT,
            creado_por TEXT,
            fecha_registro TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bcp_planes_continuidad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            escenario TEXT NOT NULL,
            descripcion TEXT,
            procedimiento_respuesta TEXT,
            responsable TEXT,
            tiempo_activacion TEXT,
            prioridad TEXT,
            recursos_necesarios TEXT,
            comunicaciones TEXT,
            estado TEXT DEFAULT 'Borrador',
            informe_ai TEXT,
            creado_por TEXT,
            fecha_registro TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bcp_crisis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_comite TEXT NOT NULL,
            roles TEXT,
            contactos_emergencia TEXT,
            escalamiento TEXT,
            arbol_llamadas TEXT,
            procedimientos TEXT,
            comunicaciones_oficiales TEXT,
            estado TEXT DEFAULT 'Activo',
            creado_por TEXT,
            fecha_registro TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bcp_pruebas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_prueba TEXT NOT NULL,
            fecha_prueba TEXT,
            resultado TEXT,
            hallazgos TEXT,
            evidencias TEXT,
            responsable TEXT,
            tiempo_recuperacion_real REAL DEFAULT 0,
            cumplimiento_rto TEXT DEFAULT 'No',
            cumplimiento_rpo TEXT DEFAULT 'No',
            lecciones_aprendidas TEXT,
            creado_por TEXT,
            fecha_registro TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bcp_dependencias_criticas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            tipo TEXT,
            proveedor TEXT,
            criticidad TEXT,
            impacto TEXT,
            plan_contingencia TEXT,
            responsable TEXT,
            estado TEXT DEFAULT 'Activo',
            creado_por TEXT,
            fecha_registro TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bcp_madurez (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dominio TEXT NOT NULL,
            descripcion TEXT,
            nivel INTEGER DEFAULT 0,
            observaciones TEXT,
            fecha_evaluacion TEXT,
            evaluador TEXT,
            fecha_registro TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bcp_metricas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            periodo TEXT NOT NULL,
            pruebas_exitosas_pct REAL DEFAULT 0,
            tiempo_promedio_recuperacion REAL DEFAULT 0,
            cumplimiento_rto_pct REAL DEFAULT 0,
            cumplimiento_rpo_pct REAL DEFAULT 0,
            procesos_con_bcp_pct REAL DEFAULT 0,
            sistemas_sin_drp INTEGER DEFAULT 0,
            backups_fallidos INTEGER DEFAULT 0,
            disponibilidad_servicios_pct REAL DEFAULT 0,
            observaciones TEXT,
            fecha_registro TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bcp_informes_ai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,
            contenido TEXT,
            contenido_editado TEXT,
            proveedor_ai TEXT,
            modelo_ai TEXT,
            generado_por TEXT,
            fecha_generacion TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# Inicializar DB independiente BCP al cargar la app
init_bcp_db()


# ============================================================
# HELPERS BCP
# ============================================================

def bcp_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def bcp_user():
    return User.query.get(session.get("user_id"))


def bcp_can_view(user):
    return user and (
        user.role in ("admin", "auditor")
        or verificar_permiso(user, BCP_MODULE_NAME)
    )


def bcp_can_write(user):
    return user and user.role != "auditor" and (
        user.role == "admin"
        or verificar_permiso(user, BCP_MODULE_NAME)
    )


def bcp_guard_view():
    user = bcp_user()
    if not bcp_can_view(user):
        flash("No tiene permiso para acceder al módulo BCP/DRP.", "danger")
        return None, redirect(url_for("menu"))
    return user, None


def bcp_guard_write():
    user = bcp_user()
    if not bcp_can_write(user):
        flash("No tiene permiso para modificar información del módulo BCP/DRP.", "danger")
        return None, redirect(url_for("bcp_dashboard"))
    return user, None


def bcp_float(value):
    try:
        return float(value or 0)
    except Exception:
        return 0


def bcp_int(value):
    try:
        return int(value or 0)
    except Exception:
        return 0


def bcp_pct(num, den):
    if not den:
        return 0
    return round((num / den) * 100, 2)


def bcp_norm_yes(value):
    return (value or "").strip().lower() in ("si", "sí", "s", "yes", "true", "1")


def bcp_badge(valor):
    v = (valor or "").lower()
    if "crítico" in v or "critico" in v or "alta" in v or "fallido" in v:
        return "danger"
    if "medio" in v or "pendiente" in v or "borrador" in v or "parcial" in v or "revisión" in v:
        return "warning text-dark"
    if "bajo" in v or "activo" in v or "exitoso" in v or "aprobado" in v or "probado" in v:
        return "success"
    return "secondary"


def bcp_query_all(table, order="id DESC"):
    conn = get_bcp_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table} ORDER BY {order}")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def bcp_query_one(table, item_id):
    conn = get_bcp_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def bcp_insert(table, data):
    keys = list(data.keys())
    placeholders = ",".join(["?"] * len(keys))
    sql = f"INSERT INTO {table} ({','.join(keys)}) VALUES ({placeholders})"
    conn = get_bcp_db_connection()
    cur = conn.cursor()
    cur.execute(sql, tuple(data[k] for k in keys))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def bcp_update(table, item_id, data):
    keys = list(data.keys())
    sql = f"UPDATE {table} SET {', '.join([k + ' = ?' for k in keys])} WHERE id = ?"
    conn = get_bcp_db_connection()
    cur = conn.cursor()
    cur.execute(sql, tuple(data[k] for k in keys) + (item_id,))
    conn.commit()
    conn.close()


def bcp_delete(table, item_id):
    conn = get_bcp_db_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def bcp_count(table):
    conn = get_bcp_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) AS total FROM {table}")
    total = cur.fetchone()["total"]
    conn.close()
    return total or 0


def bcp_metricas_actuales():
    bias = bcp_query_all("bcp_bia")
    procesos = bcp_query_all("bcp_procesos_criticos")
    drps = bcp_query_all("bcp_drp")
    pruebas = bcp_query_all("bcp_pruebas")
    deps = bcp_query_all("bcp_dependencias_criticas")
    madurez = bcp_query_all("bcp_madurez")

    rto_vals = []
    rpo_vals = []

    for x in bias:
        rto_vals.append(bcp_float(x.get("rto_horas")))
        rpo_vals.append(bcp_float(x.get("rpo_horas")))
    for x in procesos:
        rto_vals.append(bcp_float(x.get("rto_horas")))
        rpo_vals.append(bcp_float(x.get("rpo_horas")))

    pruebas_exitosas = len([x for x in pruebas if (x.get("resultado") or "").lower() == "exitoso"])
    rto_ok = len([x for x in pruebas if bcp_norm_yes(x.get("cumplimiento_rto"))])
    rpo_ok = len([x for x in pruebas if bcp_norm_yes(x.get("cumplimiento_rpo"))])
    procesos_con_bcp = len([x for x in procesos if bcp_norm_yes(x.get("tiene_bcp"))])

    nivel_madurez = round(sum([bcp_int(m.get("nivel")) for m in madurez]) / len(madurez), 2) if madurez else 0

    return {
        "nivel_madurez": nivel_madurez,
        "procesos_criticos": len(procesos),
        "servicios_criticos": len([d for d in deps if (d.get("tipo") or "").lower() in ("servicio", "cloud", "internet")]),
        "sistemas_criticos": len(drps),
        "rto_promedio": round(sum(rto_vals) / len(rto_vals), 2) if rto_vals else 0,
        "rpo_promedio": round(sum(rpo_vals) / len(rpo_vals), 2) if rpo_vals else 0,
        "pruebas_realizadas": len(pruebas),
        "estado_drp": bcp_pct(len([d for d in drps if (d.get("estado") or "").lower() in ("probado", "activo", "aprobado")]), len(drps)),
        "riesgo_operativo": len([b for b in bias if (b.get("criticidad") or "").lower() in ("alta", "crítica", "critica")]),
        "dependencias_criticas": len(deps),
        "proveedores_criticos": len([d for d in deps if d.get("proveedor")]),
        "estado_backups": bcp_pct(len([d for d in drps if (d.get("backup") or "").lower() not in ("", "no", "ninguno")]), len(drps)),
        "disponibilidad_servicios": 100,
        "pruebas_exitosas_pct": bcp_pct(pruebas_exitosas, len(pruebas)),
        "cumplimiento_rto_pct": bcp_pct(rto_ok, len(pruebas)),
        "cumplimiento_rpo_pct": bcp_pct(rpo_ok, len(pruebas)),
        "procesos_con_bcp_pct": bcp_pct(procesos_con_bcp, len(procesos)),
        "sistemas_sin_drp": max(0, len(procesos) - len(drps)),
        "backups_fallidos": sum([bcp_int(d.get("backups_fallidos")) for d in drps]),
        "tiempo_promedio_recuperacion": round(sum([bcp_float(p.get("tiempo_recuperacion_real")) for p in pruebas]) / len(pruebas), 2) if pruebas else 0,
    }


# ============================================================
# UI SHELL - MISMO ESTILO BASE DE GRAC
# BOTÓN PDF SOLO EN INFORME EJECUTIVO AI
# ============================================================

def bcp_render(title, body_html):
    user = User.query.get(session.get("user_id"))

    ruta_actual = (request.path or "").strip()
    mostrar_pdf = (
        ruta_actual.startswith("/bcp/ia")
        or ruta_actual.startswith("/bcp/ia/matriz")
        or "Informe Ejecutivo AI" in (title or "")
        or "Matriz Informes IA BCP" in (title or "")
    )

    shell_html = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .bcp-wrap{width:96%;max-width:1600px;margin:26px auto 24px auto;}

      .bcp-hero{
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

      .bcp-hero::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .bcp-hero-left{
        position:relative;
        z-index:1;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        gap:14px;
      }

      .bcp-hero-left::before{
        content:"🛟";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#fff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
      }

      .bcp-hero-text::before{
        content:"SGSI · Continuidad del Negocio";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .bcp-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .bcp-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        font-weight:800;
      }

      .bcp-header-actions{
        display:flex;
        justify-content:center;
        align-items:center;
        gap:10px;
        margin-bottom:16px;
        flex-wrap:wrap;
      }

      .bcp-toolbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        flex-wrap:wrap;
        margin-bottom:14px;
      }

      .bcp-actions{
        display:flex;
        justify-content:flex-end;
        align-items:center;
        gap:10px;
        flex-wrap:wrap;
        margin-left:auto;
      }

      .bcp-header-actions .btn,
      .bcp-actions .btn,
      .bcp-btn,
      .btn{
        border-radius:999px !important;
        min-height:40px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .bcp-btn-main{
        background:#fff;
        color:#000;
        border:2px solid #fff;
      }

      .bcp-btn-main:hover{
        background:#f3f4f6;
        color:#000;
        border-color:#f3f4f6;
      }

      .bcp-btn-info{
        background:#0dcaf0;
        color:#fff;
        border:2px solid #0dcaf0;
      }

      .bcp-btn-danger{
        background:#dc3545;
        color:#fff;
        border:2px solid #dc3545;
      }

      .bcp-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        margin-bottom:16px;
        overflow:hidden;
      }

      .bcp-card-body,
      .card-body{padding:18px;}

      .bcp-section-title,
      .card h5,
      .card h6{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:4px;
      }

      .bcp-section-muted{
        color:#607086;
        font-size:.82rem;
        font-weight:700;
        margin-top:3px;
      }

      .bcp-kpi{
        background:#fff;
        border-radius:16px;
        padding:14px 15px;
        box-shadow:0 8px 18px rgba(15,23,42,.10);
        height:100%;
        border:1px solid #dbe6f4;
        border-left:6px solid #0b4a8f;
      }

      .bcp-kpi-label{
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
        margin-bottom:8px;
        line-height:1.15;
      }

      .bcp-kpi-value{
        color:#0b4a8f;
        font-size:1.42rem;
        font-weight:950;
        line-height:1;
      }

      .bcp-table-wrap,
      .table-responsive{
        width:100%;
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        background:#fff;
        border-radius:14px;
        border:1px solid #dbe6f4;
        box-shadow:0 12px 24px rgba(15,23,42,.10);
      }

      .bcp-table,
      .table{
        width:100%;
        min-width:980px;
        border-collapse:separate;
        border-spacing:0;
        margin:0;
      }

      .bcp-table thead th,
      .table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#fff !important;
        font-size:.78rem;
        font-weight:900 !important;
        border:none !important;
        white-space:nowrap;
        vertical-align:middle !important;
        text-align:center;
        padding:9px 8px;
      }

      .bcp-table tbody td,
      .table tbody td,
      .table td{
        vertical-align:middle !important;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .bcp-table tbody tr:nth-child(even),
      .table tbody tr:nth-child(even){background:#f8fbff;}

      .bcp-table tbody tr:hover,
      .table tbody tr:hover{background:#eef6ff;}

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
        border-radius:10px !important;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }

      textarea.form-control{min-height:96px;}

      .form-control:focus,
      .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#fff;
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      @media(max-width:992px){
        .bcp-wrap{width:98%;margin:8px auto 22px auto;}
        .bcp-hero{min-height:88px;}
        .bcp-title{font-size:1.20rem;}
        .bcp-subtitle{font-size:.68rem;}
      }

      @media(max-width:768px){
        .bcp-hero{text-align:center;}
        .bcp-hero-left{flex-direction:column;text-align:center;gap:10px;width:100%;}
        .bcp-header-actions{flex-direction:column;}
        .bcp-header-actions .btn{width:100%;}
        .bcp-toolbar{flex-direction:column;align-items:stretch;}
        .bcp-actions{justify-content:center;width:100%;}
        .bcp-actions .btn{width:100%;}
      }
    </style>

    <div class="bcp-wrap">

      <div class="bcp-hero">
        <div class="bcp-hero-left">
          <div class="bcp-hero-text">
            <h1 class="bcp-title">Continuidad del Negocio (BCP/DRP)</h1>
            <div class="bcp-subtitle">{{ title }}</div>
          </div>
        </div>
      </div>

      <div class="bcp-header-actions">
        <a href="{{ url_for('bcp_dashboard') }}" class="btn bcp-btn-main">🏠 Dashboard</a>

        {% if mostrar_pdf %}
        <a href="{{ url_for('bcp_pdf') }}" class="btn bcp-btn-danger" data-no-progress="true">📄 PDF</a>
        {% endif %}
      </div>

      {{ body_html|safe }}

    </div>
    """

    inner = render_template_string(
        shell_html,
        title=title,
        body_html=Markup(body_html),
        user=user,
        mostrar_pdf=mostrar_pdf
    )

    return render_template_string(
        BASE,
        content=Markup(inner)
    )


# ============================================================
# CONFIGURACIÓN CRUD BCP
# ============================================================

BCP_CONFIG = {
    "bia": {
        "title": "Análisis de Impacto al Negocio - BIA",
        "table": "bcp_bia",
        "endpoint": "bcp_bia",
        "new_endpoint": "bcp_bia_new",
        "edit_endpoint": "bcp_bia_edit",
        "delete_endpoint": "bcp_bia_delete",
        "fields": [
            ("proceso", "Proceso", "text", True),
            ("responsable", "Responsable", "text", False),
            ("area", "Área", "text", False),
            ("criticidad", "Criticidad", "select", False, ["Baja", "Media", "Alta", "Crítica"]),
            ("impacto_financiero", "Impacto financiero", "select", False, ["Bajo", "Medio", "Alto", "Crítico"]),
            ("impacto_operacional", "Impacto operacional", "select", False, ["Bajo", "Medio", "Alto", "Crítico"]),
            ("impacto_reputacional", "Impacto reputacional", "select", False, ["Bajo", "Medio", "Alto", "Crítico"]),
            ("impacto_legal", "Impacto legal/regulatorio", "select", False, ["Bajo", "Medio", "Alto", "Crítico"]),
            ("dependencias", "Dependencias", "textarea", False),
            ("tiempo_maximo_tolerable", "Tiempo máximo tolerable", "text", False),
            ("rto_horas", "RTO horas", "number", False),
            ("rpo_horas", "RPO horas", "number", False),
            ("manual_alterno", "Manual alterno", "select", False, ["Sí", "No"]),
            ("sitio_alterno", "Sitio alterno", "text", False),
            ("proveedor_critico", "Proveedor crítico", "text", False),
            ("estado", "Estado", "select", False, ["Activo", "En revisión", "Inactivo"]),
        ],
        "columns": ["proceso", "responsable", "area", "criticidad", "rto_horas", "rpo_horas", "estado"]
    },
    "procesos": {
        "title": "Registro de Procesos Críticos",
        "table": "bcp_procesos_criticos",
        "endpoint": "bcp_procesos",
        "new_endpoint": "bcp_procesos_new",
        "edit_endpoint": "bcp_procesos_edit",
        "delete_endpoint": "bcp_procesos_delete",
        "fields": [
            ("proceso", "Proceso", "text", True),
            ("duenio", "Dueño", "text", False),
            ("area", "Área", "text", False),
            ("dependencias_tecnologicas", "Dependencias tecnológicas", "textarea", False),
            ("dependencias_humanas", "Dependencias humanas", "textarea", False),
            ("proveedores_asociados", "Proveedores asociados", "textarea", False),
            ("criticidad", "Nivel criticidad", "select", False, ["Baja", "Media", "Alta", "Crítica"]),
            ("sla_horas", "SLA horas", "number", False),
            ("rto_horas", "RTO horas", "number", False),
            ("rpo_horas", "RPO horas", "number", False),
            ("tiene_bcp", "Tiene BCP", "select", False, ["Sí", "No"]),
            ("descripcion", "Descripción", "textarea", False),
        ],
        "columns": ["proceso", "duenio", "area", "criticidad", "rto_horas", "rpo_horas", "tiene_bcp"]
    },
    "drp": {
        "title": "Plan de Recuperación Tecnológica - DRP",
        "table": "bcp_drp",
        "endpoint": "bcp_drp",
        "new_endpoint": "bcp_drp_new",
        "edit_endpoint": "bcp_drp_edit",
        "delete_endpoint": "bcp_drp_delete",
        "fields": [
            ("servidor", "Servidor / Activo", "text", True),
            ("sistema", "Sistema", "text", False),
            ("tipo_recuperacion", "Tipo recuperación", "text", False),
            ("backup", "Backup", "text", False),
            ("ubicacion_backup", "Ubicación backup", "text", False),
            ("frecuencia_backup", "Frecuencia backup", "text", False),
            ("backups_fallidos", "Backups fallidos", "int", False),
            ("tiempo_recuperacion", "Tiempo recuperación horas", "number", False),
            ("responsable", "Responsable", "text", False),
            ("procedimiento", "Procedimiento", "textarea", False),
            ("ultima_prueba", "Última prueba", "date", False),
            ("estado", "Estado", "select", False, ["Pendiente", "Activo", "Probado", "Fallido"]),
            ("observaciones", "Observaciones", "textarea", False),
        ],
        "columns": ["servidor", "sistema", "tipo_recuperacion", "backup", "backups_fallidos", "estado"]
    },
    "planes": {
        "title": "Planes de Continuidad",
        "table": "bcp_planes_continuidad",
        "endpoint": "bcp_planes",
        "new_endpoint": "bcp_planes_new",
        "edit_endpoint": "bcp_planes_edit",
        "delete_endpoint": "bcp_planes_delete",
        "fields": [
            ("escenario", "Escenario", "text", True),
            ("descripcion", "Descripción", "textarea", False),
            ("procedimiento_respuesta", "Procedimiento respuesta", "textarea", False),
            ("responsable", "Responsable", "text", False),
            ("tiempo_activacion", "Tiempo activación", "text", False),
            ("prioridad", "Prioridad", "select", False, ["Baja", "Media", "Alta", "Crítica"]),
            ("recursos_necesarios", "Recursos necesarios", "textarea", False),
            ("comunicaciones", "Comunicaciones", "textarea", False),
            ("estado", "Estado", "select", False, ["Borrador", "Aprobado", "En prueba", "Activo"]),
        ],
        "columns": ["escenario", "responsable", "prioridad", "estado"]
    },
    "crisis": {
        "title": "Gestión de Crisis",
        "table": "bcp_crisis",
        "endpoint": "bcp_crisis",
        "new_endpoint": "bcp_crisis_new",
        "edit_endpoint": "bcp_crisis_edit",
        "delete_endpoint": "bcp_crisis_delete",
        "fields": [
            ("nombre_comite", "Comité de crisis", "text", True),
            ("roles", "Roles", "textarea", False),
            ("contactos_emergencia", "Contactos emergencia", "textarea", False),
            ("escalamiento", "Escalamiento", "textarea", False),
            ("arbol_llamadas", "Árbol de llamadas", "textarea", False),
            ("procedimientos", "Procedimientos", "textarea", False),
            ("comunicaciones_oficiales", "Comunicaciones oficiales", "textarea", False),
            ("estado", "Estado", "select", False, ["Activo", "En revisión", "Inactivo"]),
        ],
        "columns": ["nombre_comite", "estado"]
    },
    "pruebas": {
        "title": "Simulacros y Pruebas",
        "table": "bcp_pruebas",
        "endpoint": "bcp_pruebas",
        "new_endpoint": "bcp_pruebas_new",
        "edit_endpoint": "bcp_pruebas_edit",
        "delete_endpoint": "bcp_pruebas_delete",
        "fields": [
            ("tipo_prueba", "Tipo prueba", "select", True, ["Tabletop", "Simulación ransomware", "DRP failover", "Recuperación backup", "Prueba comunicaciones", "Recuperación cloud"]),
            ("fecha_prueba", "Fecha prueba", "date", False),
            ("resultado", "Resultado", "select", False, ["Exitoso", "Parcial", "Fallido"]),
            ("hallazgos", "Hallazgos", "textarea", False),
            ("evidencias", "Evidencias", "textarea", False),
            ("responsable", "Responsable", "text", False),
            ("tiempo_recuperacion_real", "Tiempo recuperación real horas", "number", False),
            ("cumplimiento_rto", "Cumplimiento RTO", "select", False, ["Sí", "No"]),
            ("cumplimiento_rpo", "Cumplimiento RPO", "select", False, ["Sí", "No"]),
            ("lecciones_aprendidas", "Lecciones aprendidas", "textarea", False),
        ],
        "columns": ["tipo_prueba", "fecha_prueba", "resultado", "responsable", "cumplimiento_rto", "cumplimiento_rpo"]
    },
    "dependencias": {
        "title": "Dependencias Críticas",
        "table": "bcp_dependencias_criticas",
        "endpoint": "bcp_dependencias",
        "new_endpoint": "bcp_dependencias_new",
        "edit_endpoint": "bcp_dependencias_edit",
        "delete_endpoint": "bcp_dependencias_delete",
        "fields": [
            ("nombre", "Nombre", "text", True),
            ("tipo", "Tipo", "select", False, ["Internet", "Cloud", "SAP", "Microsoft 365", "AWS", "Oracle", "VPN", "Firewall", "WAF", "DNS", "Proveedor", "Otro"]),
            ("proveedor", "Proveedor", "text", False),
            ("criticidad", "Criticidad", "select", False, ["Baja", "Media", "Alta", "Crítica"]),
            ("impacto", "Impacto", "textarea", False),
            ("plan_contingencia", "Plan contingencia", "textarea", False),
            ("responsable", "Responsable", "text", False),
            ("estado", "Estado", "select", False, ["Activo", "En revisión", "Inactivo"]),
        ],
        "columns": ["nombre", "tipo", "proveedor", "criticidad", "estado"]
    },
    "madurez": {
        "title": "Evaluación de Madurez BCP",
        "table": "bcp_madurez",
        "endpoint": "bcp_madurez",
        "new_endpoint": "bcp_madurez_new",
        "edit_endpoint": "bcp_madurez_edit",
        "delete_endpoint": "bcp_madurez_delete",
        "fields": [
            ("dominio", "Dominio", "select", True, ["Gobierno BCP", "BIA", "DRP", "Gestión de Crisis", "Pruebas", "Mejora Continua"]),
            ("descripcion", "Descripción", "textarea", False),
            ("nivel", "Nivel 0 a 5", "int", False),
            ("observaciones", "Observaciones", "textarea", False),
            ("fecha_evaluacion", "Fecha evaluación", "date", False),
            ("evaluador", "Evaluador", "text", False),
        ],
        "columns": ["dominio", "nivel", "fecha_evaluacion", "evaluador"]
    },
}


def bcp_field_value(field, typ, raw):
    if typ == "number":
        return bcp_float(raw)
    if typ == "int":
        return bcp_int(raw)
    return (raw or "").strip()


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/bcp")
@app.route("/bcp/dashboard")
@login_required
def bcp_dashboard():
    user, resp = bcp_guard_view()
    if resp:
        return resp

    k = bcp_metricas_actuales()

    body = render_template_string("""
    <div class="row g-3 mb-3">
      {% for label, value, suffix in [
        ('Nivel de madurez BCP', k.nivel_madurez, '/5'),
        ('Procesos críticos', k.procesos_criticos, ''),
        ('Servicios críticos', k.servicios_criticos, ''),
        ('Sistemas críticos', k.sistemas_criticos, ''),
        ('RTO promedio', k.rto_promedio, ' h'),
        ('RPO promedio', k.rpo_promedio, ' h'),
        ('Pruebas realizadas', k.pruebas_realizadas, ''),
        ('Estado DRP', k.estado_drp, '%'),
        ('Riesgo operativo alto/crítico', k.riesgo_operativo, ''),
        ('Dependencias críticas', k.dependencias_criticas, ''),
        ('Proveedores críticos', k.proveedores_criticos, ''),
        ('Estado backups', k.estado_backups, '%')
      ] %}
      <div class="col-12 col-md-6 col-lg-3">
        <div class="bcp-kpi">
          <div class="bcp-kpi-label">{{ label }}</div>
          <div class="bcp-kpi-value">{{ value }}{{ suffix }}</div>
        </div>
      </div>
      {% endfor %}
    </div>

    <div class="row g-3 mb-3">
      <div class="col-lg-6">
        <div class="bcp-card"><div class="bcp-card-body">
          <h2 class="bcp-section-title">Cumplimiento RTO</h2>
          <div class="bcp-meter mt-3"><span style="width:{{ k.cumplimiento_rto_pct }}%"></span></div>
          <div class="mt-2 fw-bold">{{ k.cumplimiento_rto_pct }}%</div>
        </div></div>
      </div>
      <div class="col-lg-6">
        <div class="bcp-card"><div class="bcp-card-body">
          <h2 class="bcp-section-title">Cumplimiento RPO</h2>
          <div class="bcp-meter mt-3"><span style="width:{{ k.cumplimiento_rpo_pct }}%"></span></div>
          <div class="mt-2 fw-bold">{{ k.cumplimiento_rpo_pct }}%</div>
        </div></div>
      </div>
    </div>
    </div></div>
    """, k=k)

    return bcp_render("Dashboard Ejecutivo BCP", body)


# ============================================================
# CRUD GENÉRICO
# ============================================================

def bcp_list_page(key):
    user, resp = bcp_guard_view()
    if resp:
        return resp

    cfg = BCP_CONFIG[key]
    items = bcp_query_all(cfg["table"])
    read_only = not bcp_can_write(user)

    body = render_template_string("""
    <div class="bcp-card">
      <div class="bcp-card-body">
        <div class="bcp-toolbar">
          <div>
            <h2 class="bcp-section-title">{{ cfg.title }}</h2>
            <div class="bcp-section-muted">Gestión, seguimiento y trazabilidad del componente BCP/DRP.</div>
          </div>
          {% if not read_only %}
            <a class="btn btn-primary bcp-btn" href="{{ url_for(cfg.new_endpoint) }}">➕ Nuevo registro</a>
          {% endif %}
        </div>

        <div class="bcp-table-wrap">
          <table class="table table-hover bcp-table">
            <thead>
              <tr>
                <th style="width:80px;">ID</th>
                {% for c in cfg.columns %}
                  <th>{{ c|replace('_',' ')|title }}</th>
                {% endfor %}
                <th style="width:220px;">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {% for it in items %}
              <tr>
                <td class="fw-bold text-primary">#{{ it.id }}</td>
                {% for c in cfg.columns %}
                  {% set val = it.get(c) %}
                  <td>
                    {% if c in ['estado','criticidad','resultado','prioridad'] %}
                      <span class="badge bg-{{ bcp_badge(val) }}">{{ val or '—' }}</span>
                    {% elif c in ['tiene_bcp','cumplimiento_rto','cumplimiento_rpo'] %}
                      {% if val in ['Sí','Si','SI','sí','si'] %}
                        <span class="badge bg-success">Sí</span>
                      {% elif val %}
                        <span class="badge bg-danger">No</span>
                      {% else %}
                        <span class="text-muted">—</span>
                      {% endif %}
                    {% else %}
                      {{ val or '—' }}
                    {% endif %}
                  </td>
                {% endfor %}
                <td>
                  <div class="bcp-actions">
                    <a class="btn btn-sm btn-outline-primary" href="{{ url_for(cfg.edit_endpoint, id=it.id) }}">Ver/Editar</a>
                    {% if not read_only %}
                      <a class="btn btn-sm btn-outline-danger" onclick="return confirm('¿Eliminar este registro?')" href="{{ url_for(cfg.delete_endpoint, id=it.id) }}">Eliminar</a>
                    {% endif %}
                  </div>
                </td>
              </tr>
              {% else %}
              <tr><td colspan="20"><div class="bcp-empty">No existen registros para este componente.<br>{% if not read_only %}{% endif %}</div></td></tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    """, cfg=cfg, items=items, read_only=read_only, bcp_badge=bcp_badge)

    return bcp_render(cfg["title"], body)


def bcp_form_page(key, id=None):
    user, resp = bcp_guard_view()
    if resp:
        return resp

    cfg = BCP_CONFIG[key]
    item = bcp_query_one(cfg["table"], id) if id else {}
    read_only = not bcp_can_write(user)

    if request.method == "POST":
        user, resp = bcp_guard_write()
        if resp:
            return resp

        data = {}
        for f in cfg["fields"]:
            name, label, typ = f[0], f[1], f[2]
            data[name] = bcp_field_value(name, typ, request.form.get(name))

        if id:
            bcp_update(cfg["table"], id, data)
            saved_id = id
        else:
            data["creado_por"] = user.username
            data["fecha_registro"] = bcp_now()
            saved_id = bcp_insert(cfg["table"], data)

        try:
            registrar_log(user.username, f"Guardó registro BCP en {cfg['title']}: ID {saved_id}")
        except Exception:
            pass

        flash("Registro guardado correctamente.", "success")
        return redirect(url_for(cfg["endpoint"]))

    body = render_template_string("""
    <div class="bcp-card">
      <div class="bcp-card-body">
        <div class="bcp-toolbar">
          <div>
            <h2 class="bcp-section-title">{{ cfg.title }}</h2>
            <div class="bcp-section-muted">Complete la información requerida para este componente.</div>
          </div>
        </div>

        <form method="POST" data-progress-text="Guardando registro BCP/DRP...">
          <div class="row g-3">
            {% for f in cfg.fields %}
              {% set name = f[0] %}
              {% set label = f[1] %}
              {% set typ = f[2] %}
              {% set required = f[3] %}
              {% set options = f[4] if f|length > 4 else [] %}
              {% set value = item.get(name) %}
              <div class="col-md-6">
                <label class="form-label">{{ label }}</label>
                {% if typ == 'textarea' %}
                  <textarea class="form-control" name="{{ name }}" {% if read_only %}readonly{% endif %}>{{ value or '' }}</textarea>
                {% elif typ == 'select' %}
                  <select class="form-select" name="{{ name }}" {% if read_only %}disabled{% endif %} {% if required %}required{% endif %}>
                    <option value="">Seleccione...</option>
                    {% for op in options %}
                      <option value="{{ op }}" {% if value == op %}selected{% endif %}>{{ op }}</option>
                    {% endfor %}
                  </select>
                {% elif typ == 'date' %}
                  <input class="form-control" type="date" name="{{ name }}" value="{{ value or '' }}" {% if read_only %}readonly{% endif %}>
                {% else %}
                  <input class="form-control" type="{{ 'number' if typ in ['number','int'] else 'text' }}" step="0.01" name="{{ name }}" value="{{ value or '' }}" {% if required %}required{% endif %} {% if read_only %}readonly{% endif %}>
                {% endif %}
              </div>
            {% endfor %}
          </div>

          <div class="bcp-actions justify-content-center mt-4">
            <a class="btn btn-light" href="{{ url_for(cfg.endpoint) }}">Volver</a>
            {% if not read_only %}<button class="btn btn-primary" type="submit">Guardar</button>{% endif %}
          </div>
        </form>
      </div>
    </div>
    """, cfg=cfg, item=item, read_only=read_only)

    return bcp_render(cfg["title"], body)


def bcp_delete_item(key, id):
    user, resp = bcp_guard_write()
    if resp:
        return resp

    cfg = BCP_CONFIG[key]
    bcp_delete(cfg["table"], id)

    try:
        registrar_log(user.username, f"Eliminó registro BCP en {cfg['title']}: ID {id}")
    except Exception:
        pass

    flash("Registro eliminado correctamente.", "success")
    return redirect(url_for(cfg["endpoint"]))


# ============================================================
# RUTAS CRUD
# ============================================================

@app.route("/bcp/bia")
@login_required
def bcp_bia(): return bcp_list_page("bia")

@app.route("/bcp/bia/new", methods=["GET", "POST"])
@login_required
def bcp_bia_new(): return bcp_form_page("bia")

@app.route("/bcp/bia/edit/<int:id>", methods=["GET", "POST"])
@login_required
def bcp_bia_edit(id): return bcp_form_page("bia", id)

@app.route("/bcp/bia/delete/<int:id>")
@login_required
def bcp_bia_delete(id): return bcp_delete_item("bia", id)

@app.route("/bcp/procesos")
@login_required
def bcp_procesos(): return bcp_list_page("procesos")

@app.route("/bcp/procesos/new", methods=["GET", "POST"])
@login_required
def bcp_procesos_new(): return bcp_form_page("procesos")

@app.route("/bcp/procesos/edit/<int:id>", methods=["GET", "POST"])
@login_required
def bcp_procesos_edit(id): return bcp_form_page("procesos", id)

@app.route("/bcp/procesos/delete/<int:id>")
@login_required
def bcp_procesos_delete(id): return bcp_delete_item("procesos", id)

@app.route("/bcp/drp")
@login_required
def bcp_drp(): return bcp_list_page("drp")

@app.route("/bcp/drp/new", methods=["GET", "POST"])
@login_required
def bcp_drp_new(): return bcp_form_page("drp")

@app.route("/bcp/drp/edit/<int:id>", methods=["GET", "POST"])
@login_required
def bcp_drp_edit(id): return bcp_form_page("drp", id)

@app.route("/bcp/drp/delete/<int:id>")
@login_required
def bcp_drp_delete(id): return bcp_delete_item("drp", id)

@app.route("/bcp/planes")
@login_required
def bcp_planes(): return bcp_list_page("planes")

@app.route("/bcp/planes/new", methods=["GET", "POST"])
@login_required
def bcp_planes_new(): return bcp_form_page("planes")

@app.route("/bcp/planes/edit/<int:id>", methods=["GET", "POST"])
@login_required
def bcp_planes_edit(id): return bcp_form_page("planes", id)

@app.route("/bcp/planes/delete/<int:id>")
@login_required
def bcp_planes_delete(id): return bcp_delete_item("planes", id)

@app.route("/bcp/crisis")
@login_required
def bcp_crisis(): return bcp_list_page("crisis")

@app.route("/bcp/crisis/new", methods=["GET", "POST"])
@login_required
def bcp_crisis_new(): return bcp_form_page("crisis")

@app.route("/bcp/crisis/edit/<int:id>", methods=["GET", "POST"])
@login_required
def bcp_crisis_edit(id): return bcp_form_page("crisis", id)

@app.route("/bcp/crisis/delete/<int:id>")
@login_required
def bcp_crisis_delete(id): return bcp_delete_item("crisis", id)

@app.route("/bcp/pruebas")
@login_required
def bcp_pruebas(): return bcp_list_page("pruebas")

@app.route("/bcp/pruebas/new", methods=["GET", "POST"])
@login_required
def bcp_pruebas_new(): return bcp_form_page("pruebas")

@app.route("/bcp/pruebas/edit/<int:id>", methods=["GET", "POST"])
@login_required
def bcp_pruebas_edit(id): return bcp_form_page("pruebas", id)

@app.route("/bcp/pruebas/delete/<int:id>")
@login_required
def bcp_pruebas_delete(id): return bcp_delete_item("pruebas", id)

@app.route("/bcp/dependencias")
@login_required
def bcp_dependencias(): return bcp_list_page("dependencias")

@app.route("/bcp/dependencias/new", methods=["GET", "POST"])
@login_required
def bcp_dependencias_new(): return bcp_form_page("dependencias")

@app.route("/bcp/dependencias/edit/<int:id>", methods=["GET", "POST"])
@login_required
def bcp_dependencias_edit(id): return bcp_form_page("dependencias", id)

@app.route("/bcp/dependencias/delete/<int:id>")
@login_required
def bcp_dependencias_delete(id): return bcp_delete_item("dependencias", id)

@app.route("/bcp/madurez")
@login_required
def bcp_madurez(): return bcp_list_page("madurez")

@app.route("/bcp/madurez/new", methods=["GET", "POST"])
@login_required
def bcp_madurez_new(): return bcp_form_page("madurez")

@app.route("/bcp/madurez/edit/<int:id>", methods=["GET", "POST"])
@login_required
def bcp_madurez_edit(id): return bcp_form_page("madurez", id)

@app.route("/bcp/madurez/delete/<int:id>")
@login_required
def bcp_madurez_delete(id): return bcp_delete_item("madurez", id)


# ============================================================
# MÉTRICAS BCP - AUTOMÁTICAS POR MES / SIN BOTONES SUPERIORES
# ============================================================

def bcp_mes_actual():
    return datetime.now().strftime("%Y-%m")


def bcp_meses_disponibles():
    meses = set()

    conn = get_bcp_db_connection()
    cur = conn.cursor()

    for table, col in [
        ("bcp_pruebas", "fecha_prueba"),
        ("bcp_bia", "fecha_registro"),
        ("bcp_procesos_criticos", "fecha_registro"),
        ("bcp_drp", "fecha_registro"),
        ("bcp_dependencias_criticas", "fecha_registro"),
        ("bcp_madurez", "fecha_evaluacion"),
    ]:
        try:
            cur.execute(f"""
                SELECT DISTINCT substr({col}, 1, 7) AS periodo
                FROM {table}
                WHERE {col} IS NOT NULL
                  AND trim({col}) != ''
                  AND length({col}) >= 7
                ORDER BY periodo DESC
            """)
            for r in cur.fetchall():
                if r["periodo"]:
                    meses.add(r["periodo"])
        except Exception:
            pass

    conn.close()

    meses.add(bcp_mes_actual())
    return sorted(list(meses), reverse=True)


def bcp_filtrar_por_mes(rows, campo, periodo):
    if not periodo:
        return rows

    return [
        r for r in rows
        if str(r.get(campo) or "").startswith(periodo)
    ]


def bcp_metricas_por_mes(periodo=None):
    periodo = periodo or bcp_mes_actual()

    bias_all = bcp_query_all("bcp_bia")
    procesos_all = bcp_query_all("bcp_procesos_criticos")
    drps_all = bcp_query_all("bcp_drp")
    pruebas_all = bcp_query_all("bcp_pruebas")
    deps_all = bcp_query_all("bcp_dependencias_criticas")
    madurez_all = bcp_query_all("bcp_madurez")

    pruebas_mes = bcp_filtrar_por_mes(pruebas_all, "fecha_prueba", periodo)
    madurez_mes = bcp_filtrar_por_mes(madurez_all, "fecha_evaluacion", periodo)

    procesos_base = procesos_all
    drps_base = drps_all
    deps_base = deps_all
    bias_base = bias_all
    madurez_base = madurez_mes if madurez_mes else madurez_all

    rto_vals = []
    rpo_vals = []

    for x in bias_base:
        if bcp_float(x.get("rto_horas")) > 0:
            rto_vals.append(bcp_float(x.get("rto_horas")))
        if bcp_float(x.get("rpo_horas")) > 0:
            rpo_vals.append(bcp_float(x.get("rpo_horas")))

    for x in procesos_base:
        if bcp_float(x.get("rto_horas")) > 0:
            rto_vals.append(bcp_float(x.get("rto_horas")))
        if bcp_float(x.get("rpo_horas")) > 0:
            rpo_vals.append(bcp_float(x.get("rpo_horas")))

    pruebas_exitosas = len([
        x for x in pruebas_mes
        if (x.get("resultado") or "").strip().lower() == "exitoso"
    ])

    rto_ok = len([
        x for x in pruebas_mes
        if bcp_norm_yes(x.get("cumplimiento_rto"))
    ])

    rpo_ok = len([
        x for x in pruebas_mes
        if bcp_norm_yes(x.get("cumplimiento_rpo"))
    ])

    procesos_con_bcp = len([
        x for x in procesos_base
        if bcp_norm_yes(x.get("tiene_bcp"))
    ])

    nivel_madurez = round(
        sum([bcp_int(m.get("nivel")) for m in madurez_base]) / len(madurez_base),
        2
    ) if madurez_base else 0

    tiempo_promedio_recuperacion = round(
        sum([bcp_float(p.get("tiempo_recuperacion_real")) for p in pruebas_mes]) / len(pruebas_mes),
        2
    ) if pruebas_mes else 0

    return {
        "periodo": periodo,
        "nivel_madurez": nivel_madurez,
        "procesos_criticos": len(procesos_base),
        "servicios_criticos": len([
            d for d in deps_base
            if (d.get("tipo") or "").lower() in ("servicio", "cloud", "internet")
        ]),
        "sistemas_criticos": len(drps_base),
        "rto_promedio": round(sum(rto_vals) / len(rto_vals), 2) if rto_vals else 0,
        "rpo_promedio": round(sum(rpo_vals) / len(rpo_vals), 2) if rpo_vals else 0,
        "pruebas_realizadas": len(pruebas_mes),
        "estado_drp": bcp_pct(
            len([
                d for d in drps_base
                if (d.get("estado") or "").lower() in ("probado", "activo", "aprobado")
            ]),
            len(drps_base)
        ),
        "riesgo_operativo": len([
            b for b in bias_base
            if (b.get("criticidad") or "").lower() in ("alta", "crítica", "critica")
        ]),
        "dependencias_criticas": len(deps_base),
        "proveedores_criticos": len([d for d in deps_base if d.get("proveedor")]),
        "estado_backups": bcp_pct(
            len([
                d for d in drps_base
                if (d.get("backup") or "").lower() not in ("", "no", "ninguno")
            ]),
            len(drps_base)
        ),
        "disponibilidad_servicios": 100,
        "pruebas_exitosas_pct": bcp_pct(pruebas_exitosas, len(pruebas_mes)),
        "cumplimiento_rto_pct": bcp_pct(rto_ok, len(pruebas_mes)),
        "cumplimiento_rpo_pct": bcp_pct(rpo_ok, len(pruebas_mes)),
        "procesos_con_bcp_pct": bcp_pct(procesos_con_bcp, len(procesos_base)),
        "sistemas_sin_drp": max(0, len(procesos_base) - len(drps_base)),
        "backups_fallidos": sum([bcp_int(d.get("backups_fallidos")) for d in drps_base]),
        "tiempo_promedio_recuperacion": tiempo_promedio_recuperacion,
    }


def bcp_metricas_historico_mensual():
    meses = bcp_meses_disponibles()
    historico = []

    for mes in meses:
        historico.append(bcp_metricas_por_mes(mes))

    return historico


@app.route("/bcp/metricas")
@login_required
def bcp_metricas():
    user, resp = bcp_guard_view()
    if resp:
        return resp

    periodo = (request.args.get("periodo") or bcp_mes_actual()).strip()
    meses = bcp_meses_disponibles()

    if periodo not in meses:
        meses.append(periodo)
        meses = sorted(list(set(meses)), reverse=True)

    auto = bcp_metricas_por_mes(periodo)
    historico = bcp_metricas_historico_mensual()

    body = render_template_string("""
    <style>
      .bcp-header-actions {
        display: none !important;
      }
    </style>

    <div class="bcp-card">
      <div class="bcp-card-body">
        <div class="bcp-toolbar">
          <div>
            <h2 class="bcp-section-title">Métricas BCP automáticas por mes</h2>
            <div class="bcp-section-muted">
              Indicadores calculados automáticamente desde BIA, procesos críticos, DRP, pruebas, dependencias y madurez.
            </div>
          </div>

          <form method="GET" class="d-flex align-items-center gap-2 flex-wrap">
            <label class="form-label mb-0">Periodo</label>
            <select class="form-select" name="periodo" onchange="this.form.submit()" style="min-width:150px;">
              {% for m in meses %}
                <option value="{{ m }}" {% if m == periodo %}selected{% endif %}>{{ m }}</option>
              {% endfor %}
            </select>
          </form>
        </div>

        <div class="row g-3">
          {% for label, val, suf in [
            ('% pruebas exitosas', auto.pruebas_exitosas_pct, '%'),
            ('Tiempo promedio recuperación', auto.tiempo_promedio_recuperacion, ' h'),
            ('Cumplimiento RTO', auto.cumplimiento_rto_pct, '%'),
            ('Cumplimiento RPO', auto.cumplimiento_rpo_pct, '%'),
            ('Procesos con BCP', auto.procesos_con_bcp_pct, '%'),
            ('Sistemas sin DRP', auto.sistemas_sin_drp, ''),
            ('Backups fallidos', auto.backups_fallidos, ''),
            ('Disponibilidad servicios', auto.disponibilidad_servicios, '%')
          ] %}
          <div class="col-12 col-md-6 col-lg-3">
            <div class="bcp-kpi">
              <div class="bcp-kpi-label">{{ label }}</div>
              <div class="bcp-kpi-value">{{ val }}{{ suf }}</div>
            </div>
          </div>
          {% endfor %}
        </div>
      </div>
    </div>

    <div class="bcp-card">
      <div class="bcp-card-body">
        <div class="bcp-toolbar">
          <div>
            <h2 class="bcp-section-title">Detalle del periodo {{ periodo }}</h2>
            <div class="bcp-section-muted">Resumen automático del mes seleccionado.</div>
          </div>
        </div>

        <div class="bcp-table-wrap">
          <table class="table table-hover bcp-table">
            <thead>
              <tr>
                <th>Indicador</th>
                <th>Resultado</th>
                <th>Interpretación</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>Pruebas realizadas</td><td>{{ auto.pruebas_realizadas }}</td><td>Simulacros o pruebas BCP/DRP registradas en el mes.</td></tr>
              <tr><td>Pruebas exitosas</td><td>{{ auto.pruebas_exitosas_pct }}%</td><td>Porcentaje de pruebas con resultado exitoso.</td></tr>
              <tr><td>Cumplimiento RTO</td><td>{{ auto.cumplimiento_rto_pct }}%</td><td>Porcentaje de pruebas del mes que cumplieron el RTO.</td></tr>
              <tr><td>Cumplimiento RPO</td><td>{{ auto.cumplimiento_rpo_pct }}%</td><td>Porcentaje de pruebas del mes que cumplieron el RPO.</td></tr>
              <tr><td>Procesos con BCP</td><td>{{ auto.procesos_con_bcp_pct }}%</td><td>Cobertura total de procesos críticos con plan BCP.</td></tr>
              <tr><td>Estado DRP</td><td>{{ auto.estado_drp }}%</td><td>Porcentaje de DRP activos, aprobados o probados.</td></tr>
              <tr><td>Estado backups</td><td>{{ auto.estado_backups }}%</td><td>Porcentaje de activos/sistemas DRP con backup definido.</td></tr>
              <tr><td>Nivel de madurez BCP</td><td>{{ auto.nivel_madurez }}/5</td><td>Promedio de madurez BCP registrado para el periodo o histórico disponible.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="bcp-card">
      <div class="bcp-card-body">
        <div class="bcp-toolbar">
          <div>
            <h2 class="bcp-section-title">Histórico mensual automático</h2>
            <div class="bcp-section-muted">
              No requiere captura manual. Se calcula con los registros existentes por cada mes.
            </div>
          </div>
        </div>

        <div class="bcp-table-wrap">
          <table class="table table-hover bcp-table">
            <thead>
              <tr>
                <th>Periodo</th>
                <th>Pruebas</th>
                <th>Pruebas exitosas</th>
                <th>Tiempo prom. recuperación</th>
                <th>RTO</th>
                <th>RPO</th>
                <th>Procesos BCP</th>
                <th>Sistemas sin DRP</th>
                <th>Backups fallidos</th>
                <th>Disponibilidad</th>
              </tr>
            </thead>
            <tbody>
              {% for m in historico %}
                <tr>
                  <td class="fw-bold text-primary">{{ m.periodo }}</td>
                  <td>{{ m.pruebas_realizadas }}</td>
                  <td>{{ m.pruebas_exitosas_pct }}%</td>
                  <td>{{ m.tiempo_promedio_recuperacion }} h</td>
                  <td>{{ m.cumplimiento_rto_pct }}%</td>
                  <td>{{ m.cumplimiento_rpo_pct }}%</td>
                  <td>{{ m.procesos_con_bcp_pct }}%</td>
                  <td>{{ m.sistemas_sin_drp }}</td>
                  <td>{{ m.backups_fallidos }}</td>
                  <td>{{ m.disponibilidad_servicios }}%</td>
                </tr>
              {% else %}
                <tr>
                  <td colspan="10">
                    <div class="bcp-empty">No hay información mensual disponible.</div>
                  </td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>

      </div>
    </div>
    """, auto=auto, historico=historico, periodo=periodo, meses=meses)

    return bcp_render("Métricas BCP", body)


# ============================================================
# TABLA / MIGRACIÓN MATRIZ INFORMES IA BCP
# ============================================================

def bcp_init_informes_ai():
    conn = get_bcp_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bcp_informes_ai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,
            contenido TEXT,
            contenido_editado TEXT,
            proveedor_ai TEXT,
            modelo_ai TEXT,
            generado_por TEXT,
            fecha_generacion TEXT
        )
    """)

    columnas_requeridas = {
        "nivel_madurez": "REAL DEFAULT 0",
        "procesos_criticos": "INTEGER DEFAULT 0",
        "sistemas_criticos": "INTEGER DEFAULT 0",
        "rto_promedio": "REAL DEFAULT 0",
        "rpo_promedio": "REAL DEFAULT 0",
        "pruebas_realizadas": "INTEGER DEFAULT 0",
        "cumplimiento_rto_pct": "REAL DEFAULT 0",
        "cumplimiento_rpo_pct": "REAL DEFAULT 0",
        "procesos_con_bcp_pct": "REAL DEFAULT 0",
        "backups_fallidos": "INTEGER DEFAULT 0",
        "dependencias_criticas": "INTEGER DEFAULT 0"
    }

    columnas_actuales = [
        row["name"]
        for row in cur.execute("PRAGMA table_info(bcp_informes_ai)").fetchall()
    ]

    for columna, tipo in columnas_requeridas.items():
        if columna not in columnas_actuales:
            cur.execute(f"ALTER TABLE bcp_informes_ai ADD COLUMN {columna} {tipo}")

    conn.commit()
    conn.close()


with app.app_context():
    bcp_init_informes_ai()


# ============================================================
# MATRIZ HISTÓRICA INFORMES IA BCP - VERSIÓN EJECUTIVA
# ============================================================

@app.route("/bcp/ia/matriz")
@login_required
def bcp_matriz_informes():
    user, resp = bcp_guard_view()
    if resp:
        return resp

    bcp_init_informes_ai()

    conn = get_bcp_db_connection()
    informes = conn.execute("""
        SELECT
            id,
            fecha_generacion,
            generado_por,
            nivel_madurez,
            procesos_criticos,
            sistemas_criticos,
            rto_promedio,
            rpo_promedio,
            cumplimiento_rto_pct,
            cumplimiento_rpo_pct,
            backups_fallidos,
            proveedor_ai
        FROM bcp_informes_ai
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    body = render_template_string("""
    <style>
      .bcp-ia-summary-grid{
        display:grid;
        grid-template-columns:repeat(4,minmax(160px,1fr));
        gap:12px;
        margin-bottom:16px;
      }

      .bcp-ia-mini-card{
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-left:6px solid #0b4a8f;
        border-radius:16px;
        padding:14px 16px;
        box-shadow:0 8px 18px rgba(15,23,42,.10);
      }

      .bcp-ia-mini-label{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
      }

      .bcp-ia-mini-value{
        margin-top:5px;
        font-size:1.35rem;
        font-weight:950;
        color:#101827;
      }

      .bcp-ia-table{
        min-width:1050px !important;
      }

      .bcp-ia-table td,
      .bcp-ia-table th{
        white-space:nowrap;
      }

      .bcp-ia-actions{
        display:flex;
        justify-content:center;
        align-items:center;
        gap:6px;
        flex-wrap:wrap;
      }

      @media(max-width:992px){
        .bcp-ia-summary-grid{
          grid-template-columns:repeat(2,minmax(160px,1fr));
        }
      }

      @media(max-width:576px){
        .bcp-ia-summary-grid{
          grid-template-columns:1fr;
        }
      }
    </style>

    <div class="bcp-card">
      <div class="bcp-card-body">

        <div class="bcp-toolbar">
          <div>
            <h2 class="bcp-section-title mb-0">
              Matriz Histórica Informes IA BCP/DRP
            </h2>

            <div class="bcp-section-muted">
              Consulta ejecutiva de informes generados por IA para Continuidad del Negocio.
            </div>
          </div>

          {% if user.role != 'auditor' %}
          <a href="{{ url_for('bcp_ia_generar') }}"
             class="btn btn-primary rounded-pill px-4">
            <i class="bi bi-stars"></i>
            Generar nuevo informe IA
          </a>
          {% endif %}
        </div>

        <div class="bcp-ia-summary-grid">

          <div class="bcp-ia-mini-card">
            <div class="bcp-ia-mini-label">
              Total informes
            </div>

            <div class="bcp-ia-mini-value">
              {{ informes|length }}
            </div>
          </div>

          <div class="bcp-ia-mini-card">
            <div class="bcp-ia-mini-label">
              Última madurez
            </div>

            <div class="bcp-ia-mini-value">
              {% if informes|length > 0 %}
                {{ informes[0]['nivel_madurez'] or 0 }}/5
              {% else %}
                0/5
              {% endif %}
            </div>
          </div>

          <div class="bcp-ia-mini-card">
            <div class="bcp-ia-mini-label">
              Último RTO
            </div>

            <div class="bcp-ia-mini-value">
              {% if informes|length > 0 %}
                {{ informes[0]['rto_promedio'] or 0 }} h
              {% else %}
                0 h
              {% endif %}
            </div>
          </div>

          <div class="bcp-ia-mini-card">
            <div class="bcp-ia-mini-label">
              Último RPO
            </div>

            <div class="bcp-ia-mini-value">
              {% if informes|length > 0 %}
                {{ informes[0]['rpo_promedio'] or 0 }} h
              {% else %}
                0 h
              {% endif %}
            </div>
          </div>

        </div>

        <div class="alert alert-info border-0 shadow-sm">
          Esta matriz muestra únicamente los datos principales.
          Para consultar el contenido completo del informe,
          usa el botón <strong>Ver detalle</strong>.
        </div>

        <div class="bcp-table-wrap">
          <table class="table table-hover bcp-table bcp-ia-table align-middle">

            <thead>
              <tr>
                <th style="width:70px;">ID</th>
                <th>Fecha generación</th>
                <th>Usuario</th>
                <th>Madurez</th>
                <th>Procesos</th>
                <th>Sistemas</th>
                <th>RTO</th>
                <th>RPO</th>
                <th>Cumplimiento</th>
                <th>Backups fallidos</th>
                <th>Proveedor IA</th>
                <th style="width:260px;">Acciones</th>
              </tr>
            </thead>

            <tbody>

              {% for i in informes %}
              <tr>

                <td class="fw-bold text-primary text-center">
                  #{{ i['id'] }}
                </td>

                <td>
                  {{ i['fecha_generacion'] or '—' }}
                </td>

                <td>
                  {{ i['generado_por'] or '—' }}
                </td>

                <td class="text-center">
                  <span class="badge bg-primary">
                    {{ i['nivel_madurez'] or 0 }}/5
                  </span>
                </td>

                <td class="text-center">
                  {{ i['procesos_criticos'] or 0 }}
                </td>

                <td class="text-center">
                  {{ i['sistemas_criticos'] or 0 }}
                </td>

                <td class="text-center">
                  {{ i['rto_promedio'] or 0 }} h
                </td>

                <td class="text-center">
                  {{ i['rpo_promedio'] or 0 }} h
                </td>

                <td class="text-center">
                  <span class="badge bg-success">
                    RTO {{ i['cumplimiento_rto_pct'] or 0 }}%
                  </span>

                  <span class="badge bg-info text-dark">
                    RPO {{ i['cumplimiento_rpo_pct'] or 0 }}%
                  </span>
                </td>

                <td class="text-center">
                  {% if (i['backups_fallidos'] or 0) > 0 %}
                    <span class="badge bg-danger">
                      {{ i['backups_fallidos'] }}
                    </span>
                  {% else %}
                    <span class="badge bg-success">
                      0
                    </span>
                  {% endif %}
                </td>

                <td class="text-center">
                  {{ i['proveedor_ai'] or '—' }}
                </td>

                <td>
                  <div class="bcp-ia-actions">

                    <a href="{{ url_for('bcp_ver_informe_ia', informe_id=i['id']) }}"
                       class="btn btn-sm btn-outline-primary rounded-pill">
                      <i class="bi bi-eye"></i>
                      Ver detalle
                    </a>

                    {% if user.role != 'auditor' %}
                    <form method="POST"
                          action="{{ url_for('bcp_eliminar_informe_ia', informe_id=i['id']) }}"
                          style="display:inline;"
                          onsubmit="return confirm('¿Desea eliminar este informe IA BCP/DRP?')">

                      <button type="submit"
                              class="btn btn-sm btn-outline-danger rounded-pill">
                        <i class="bi bi-trash"></i>
                        Eliminar
                      </button>

                    </form>
                    {% endif %}

                  </div>
                </td>

              </tr>

              {% else %}
              <tr>
                <td colspan="12"
                    class="text-center text-muted py-4">

                  No existen informes IA generados.

                </td>
              </tr>
              {% endfor %}

            </tbody>
          </table>
        </div>

      </div>
    </div>
    """, informes=informes, user=user)

    return bcp_render("Matriz Informes IA BCP", body)


# ============================================================
# IA GENERATIVA BCP
# ============================================================

@app.route("/bcp/ia/generar")
@login_required
def bcp_ia_generar():
    user, resp = bcp_guard_write()
    if resp:
        return resp

    bcp_init_informes_ai()

    k = bcp_metricas_actuales()

    prompt = f"""
Actúa como experto senior en Continuidad del Negocio, ISO 22301, ISO 27001 y resiliencia operacional.

Genera un informe ejecutivo profesional, claro y concreto para el módulo Continuidad del Negocio (BCP/DRP) de GRAC.

Máximo 700 palabras.

Indicadores:
- Nivel madurez BCP: {k['nivel_madurez']}/5
- Procesos críticos: {k['procesos_criticos']}
- Sistemas críticos con DRP: {k['sistemas_criticos']}
- RTO promedio: {k['rto_promedio']} horas
- RPO promedio: {k['rpo_promedio']} horas
- Pruebas realizadas: {k['pruebas_realizadas']}
- Cumplimiento RTO: {k['cumplimiento_rto_pct']}%
- Cumplimiento RPO: {k['cumplimiento_rpo_pct']}%
- Procesos con BCP: {k['procesos_con_bcp_pct']}%
- Backups fallidos: {k['backups_fallidos']}
- Dependencias críticas: {k['dependencias_criticas']}

Incluye:
1. Resumen ejecutivo
2. Principales hallazgos
3. Riesgos de continuidad
4. Recomendaciones
5. Plan de mejora
6. Prioridades de corto plazo
7. Conclusión ejecutiva

No uses markdown con asteriscos.
No repitas títulos.
No generes texto excesivamente largo.
"""

    try:
        texto = ai_text_general(
            prompt,
            system_prompt="Eres consultor senior en continuidad de negocio, ISO 22301, ISO 27001 y ciberresiliencia.",
            temperature=0.2,
            max_tokens=650
        )

        flash("Informe IA generado correctamente y almacenado en la matriz histórica BCP.", "success")

    except Exception as e:
        texto = f"""
Informe Ejecutivo BCP/DRP

No fue posible generar el informe mediante IA en este momento.

Causa técnica:
{repr(e)}

Resumen técnico de la revisión:

Nivel de madurez BCP: {k.get('nivel_madurez', 0)}/5
Procesos críticos: {k.get('procesos_criticos', 0)}
Sistemas críticos con DRP: {k.get('sistemas_criticos', 0)}
RTO promedio: {k.get('rto_promedio', 0)} horas
RPO promedio: {k.get('rpo_promedio', 0)} horas
Pruebas realizadas: {k.get('pruebas_realizadas', 0)}
Cumplimiento RTO: {k.get('cumplimiento_rto_pct', 0)}%
Cumplimiento RPO: {k.get('cumplimiento_rpo_pct', 0)}%
Procesos con BCP: {k.get('procesos_con_bcp_pct', 0)}%
Backups fallidos: {k.get('backups_fallidos', 0)}
Dependencias críticas: {k.get('dependencias_criticas', 0)}

Recomendación:
Validar que el proveedor IA esté activo y respondiendo correctamente.
"""

        flash("El proveedor IA no respondió correctamente. Se guardó un resumen técnico en la matriz.", "warning")

    conn = get_bcp_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO bcp_informes_ai (
            tipo,
            contenido,
            contenido_editado,
            proveedor_ai,
            modelo_ai,
            generado_por,
            fecha_generacion,
            nivel_madurez,
            procesos_criticos,
            sistemas_criticos,
            rto_promedio,
            rpo_promedio,
            pruebas_realizadas,
            cumplimiento_rto_pct,
            cumplimiento_rpo_pct,
            procesos_con_bcp_pct,
            backups_fallidos,
            dependencias_criticas
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Informe Ejecutivo BCP/DRP",
        texto,
        "",
        (get_ai_provider() if 'get_ai_provider' in globals() else ""),
        "",
        user.username,
        bcp_now(),
        k.get("nivel_madurez", 0),
        k.get("procesos_criticos", 0),
        k.get("sistemas_criticos", 0),
        k.get("rto_promedio", 0),
        k.get("rpo_promedio", 0),
        k.get("pruebas_realizadas", 0),
        k.get("cumplimiento_rto_pct", 0),
        k.get("cumplimiento_rpo_pct", 0),
        k.get("procesos_con_bcp_pct", 0),
        k.get("backups_fallidos", 0),
        k.get("dependencias_criticas", 0)
    ))

    informe_id = cur.lastrowid
    conn.commit()
    conn.close()

    return redirect(url_for("bcp_ver_informe_ia", informe_id=informe_id))


# ============================================================
# VER DETALLE INFORME IA
# ============================================================

@app.route("/bcp/ia/ver/<int:informe_id>")
@login_required
def bcp_ver_informe_ia(informe_id):
    user, resp = bcp_guard_view()
    if resp:
        return resp

    bcp_init_informes_ai()

    conn = get_bcp_db_connection()
    informe = conn.execute("""
        SELECT *
        FROM bcp_informes_ai
        WHERE id = ?
    """, (informe_id,)).fetchone()
    conn.close()

    if not informe:
        flash("Informe no encontrado.", "warning")
        return redirect(url_for("bcp_matriz_informes"))

    contenido = informe["contenido_editado"] or informe["contenido"]

    body = render_template_string("""
    <div class="bcp-card">
      <div class="bcp-card-body">

        <h2 class="bcp-section-title mb-4">Detalle Informe Ejecutivo IA BCP/DRP</h2>

        <div class="row g-3 mb-4">
          <div class="col-md-3">
            <div class="alert alert-primary mb-0">
              <strong>Fecha</strong><br>{{ informe['fecha_generacion'] }}
            </div>
          </div>

          <div class="col-md-3">
            <div class="alert alert-info mb-0">
              <strong>Usuario</strong><br>{{ informe['generado_por'] }}
            </div>
          </div>

          <div class="col-md-3">
            <div class="alert alert-success mb-0">
              <strong>Madurez BCP</strong><br>{{ informe['nivel_madurez'] }}/5
            </div>
          </div>

          <div class="col-md-3">
            <div class="alert alert-warning mb-0">
              <strong>Proveedor IA</strong><br>{{ informe['proveedor_ai'] }}
            </div>
          </div>
        </div>

        <textarea class="form-control" rows="28" readonly>{{ contenido }}</textarea>

        <div class="bcp-actions justify-content-center mt-4">
          <a href="{{ url_for('bcp_matriz_informes') }}" class="btn btn-light rounded-pill px-4">
            Volver a matriz
          </a>

          {% if user.role != 'auditor' %}
          <a href="{{ url_for('bcp_ia_generar') }}" class="btn btn-primary rounded-pill px-4">
            Generar nuevo informe
          </a>
          {% endif %}
        </div>

      </div>
    </div>
    """, informe=informe, contenido=contenido, user=user)

    return bcp_render("Detalle Informe IA", body)


# ============================================================
# ELIMINAR INFORME IA BCP
# ============================================================

@app.route("/bcp/ia/eliminar/<int:informe_id>", methods=["POST"])
@login_required
def bcp_eliminar_informe_ia(informe_id):
    user, resp = bcp_guard_write()
    if resp:
        return resp

    if user.role == "auditor":
        flash("El rol auditor no puede eliminar informes IA.", "warning")
        return redirect(url_for("bcp_matriz_informes"))

    conn = get_bcp_db_connection()

    informe = conn.execute("""
        SELECT id
        FROM bcp_informes_ai
        WHERE id = ?
    """, (informe_id,)).fetchone()

    if not informe:
        conn.close()
        flash("El informe no existe.", "warning")
        return redirect(url_for("bcp_matriz_informes"))

    conn.execute("""
        DELETE FROM bcp_informes_ai
        WHERE id = ?
    """, (informe_id,))

    conn.commit()
    conn.close()

    flash("Informe IA BCP eliminado correctamente.", "success")
    return redirect(url_for("bcp_matriz_informes"))

# ============================================================
# PDF EJECUTIVO BCP
# ============================================================

@app.route("/bcp/pdf")
@login_required
def bcp_pdf():
    user, resp = bcp_guard_view()
    if resp:
        return resp

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    h1 = ParagraphStyle("BCPH1", parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#1d4f8f"), spaceAfter=12)
    h2 = ParagraphStyle("BCPH2", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#2f6fb6"), spaceAfter=8)
    normal = styles["BodyText"]

    k = bcp_metricas_actuales()

    story.append(Paragraph("Informe Ejecutivo Continuidad del Negocio (BCP/DRP)", h1))
    story.append(Paragraph(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal))
    story.append(Spacer(1, 12))

    data = [
        ["Indicador", "Valor"],
        ["Nivel de madurez BCP", f"{k['nivel_madurez']}/5"],
        ["Procesos críticos", str(k["procesos_criticos"])],
        ["Sistemas críticos", str(k["sistemas_criticos"])],
        ["RTO promedio", f"{k['rto_promedio']} horas"],
        ["RPO promedio", f"{k['rpo_promedio']} horas"],
        ["Pruebas realizadas", str(k["pruebas_realizadas"])],
        ["Cumplimiento RTO", f"{k['cumplimiento_rto_pct']}%"],
        ["Cumplimiento RPO", f"{k['cumplimiento_rpo_pct']}%"],
        ["Procesos con BCP", f"{k['procesos_con_bcp_pct']}%"],
        ["Sistemas sin DRP", str(k["sistemas_sin_drp"])],
        ["Backups fallidos", str(k["backups_fallidos"])],
    ]

    table = Table(data, colWidths=[8 * cm, 8 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1d4f8f")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Resumen de cobertura documental", h2))
    sections = [
        ("BIA", bcp_count("bcp_bia")),
        ("Procesos críticos", bcp_count("bcp_procesos_criticos")),
        ("DRP", bcp_count("bcp_drp")),
        ("Planes de continuidad", bcp_count("bcp_planes_continuidad")),
        ("Gestión de crisis", bcp_count("bcp_crisis")),
        ("Pruebas y simulacros", bcp_count("bcp_pruebas")),
        ("Dependencias críticas", bcp_count("bcp_dependencias_criticas")),
    ]
    table2 = Table([["Componente", "Registros"]] + [[a, str(b)] for a, b in sections], colWidths=[10 * cm, 6 * cm])
    table2.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2f6fb6")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ]))
    story.append(table2)

    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Informe_BCP_DRP_{datetime.now().strftime('%Y%m%d')}.pdf",
        mimetype="application/pdf"
    )

# ============================================================================================================================================
#                                      FIN MÓDULO CONTINUIDAD DEL NEGOCIO (BCP/DRP)
# ============================================================================================================================================


# ============================================================================================================================================
#                                           MÓDULO CUMPLIMIENTO CONTINUO - WAZUH + GRAC
# ============================================================================================================================================



CONT_COMP_MODULE_NAME = "Cumplimiento Continuo"


# ============================================================
# MODELOS
# ============================================================

class WazuhConfig(db.Model):
    __tablename__ = "wazuh_config"

    id = db.Column(db.Integer, primary_key=True)
    api_url = db.Column(db.String(500), nullable=False, default="https://localhost:55000")
    username = db.Column(db.String(120), nullable=False, default="wazuh-wui")
    password = db.Column(db.Text, nullable=True)
    token = db.Column(db.Text, nullable=True)
    verify_ssl = db.Column(db.Boolean, nullable=False, default=False)
    last_status = db.Column(db.String(50), nullable=True)
    last_message = db.Column(db.Text, nullable=True)
    last_test_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WazuhAgent(db.Model):
    __tablename__ = "wazuh_agents"

    id = db.Column(db.Integer, primary_key=True)
    wazuh_id = db.Column(db.String(80), unique=True, index=True)
    name = db.Column(db.String(255), nullable=True)
    ip = db.Column(db.String(100), nullable=True)
    os_name = db.Column(db.String(255), nullable=True)
    os_version = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(80), nullable=True)
    last_keep_alive = db.Column(db.String(80), nullable=True)
    raw_json = db.Column(db.Text, nullable=True)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)


class WazuhAlert(db.Model):
    __tablename__ = "wazuh_alerts"

    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.String(255), unique=True, index=True)
    timestamp = db.Column(db.String(80), nullable=True)
    agent_id = db.Column(db.String(80), nullable=True)
    agent_name = db.Column(db.String(255), nullable=True)
    rule_id = db.Column(db.String(80), nullable=True)
    rule_level = db.Column(db.Integer, default=0)
    rule_description = db.Column(db.Text, nullable=True)
    mitre_ids = db.Column(db.Text, nullable=True)
    groups = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(50), nullable=True)
    raw_json = db.Column(db.Text, nullable=True)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)


class WazuhVulnerability(db.Model):
    __tablename__ = "wazuh_vulnerabilities"

    id = db.Column(db.Integer, primary_key=True)
    unique_key = db.Column(db.String(500), unique=True, index=True)
    agent_id = db.Column(db.String(80), nullable=True)
    agent_name = db.Column(db.String(255), nullable=True)
    cve = db.Column(db.String(80), nullable=True)
    package_name = db.Column(db.String(255), nullable=True)
    package_version = db.Column(db.String(255), nullable=True)
    severity = db.Column(db.String(50), nullable=True)
    cvss = db.Column(db.Float, nullable=True)
    title = db.Column(db.Text, nullable=True)
    condition = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=True, default="Abierta")
    raw_json = db.Column(db.Text, nullable=True)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)


class WazuhSCAResult(db.Model):
    __tablename__ = "wazuh_sca_results"

    id = db.Column(db.Integer, primary_key=True)
    unique_key = db.Column(db.String(500), unique=True, index=True)
    agent_id = db.Column(db.String(80), nullable=True)
    agent_name = db.Column(db.String(255), nullable=True)
    policy_id = db.Column(db.String(120), nullable=True)
    policy_name = db.Column(db.String(255), nullable=True)
    check_id = db.Column(db.String(120), nullable=True)
    title = db.Column(db.Text, nullable=True)
    result = db.Column(db.String(50), nullable=True)
    compliance = db.Column(db.Text, nullable=True)
    raw_json = db.Column(db.Text, nullable=True)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)


class WazuhFimEvent(db.Model):
    __tablename__ = "wazuh_fim_events"

    id = db.Column(db.Integer, primary_key=True)
    unique_key = db.Column(db.String(500), unique=True, index=True)
    timestamp = db.Column(db.String(80), nullable=True)
    agent_id = db.Column(db.String(80), nullable=True)
    agent_name = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.Text, nullable=True)
    action = db.Column(db.String(100), nullable=True)
    severity = db.Column(db.String(50), nullable=True)
    raw_json = db.Column(db.Text, nullable=True)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)


class WazuhMitreEvent(db.Model):
    __tablename__ = "wazuh_mitre_events"

    id = db.Column(db.Integer, primary_key=True)
    unique_key = db.Column(db.String(500), unique=True, index=True)
    timestamp = db.Column(db.String(80), nullable=True)
    agent_id = db.Column(db.String(80), nullable=True)
    agent_name = db.Column(db.String(255), nullable=True)
    tactic = db.Column(db.String(255), nullable=True)
    technique = db.Column(db.String(255), nullable=True)
    technique_id = db.Column(db.String(80), nullable=True)
    rule_level = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, nullable=True)
    raw_json = db.Column(db.Text, nullable=True)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContinuousControl(db.Model):
    __tablename__ = "continuous_controls"

    id = db.Column(db.Integer, primary_key=True)
    standard = db.Column(db.String(50), nullable=False, index=True)
    control_code = db.Column(db.String(100), nullable=False, index=True)
    control_name = db.Column(db.Text, nullable=False)
    source_type = db.Column(db.String(50), nullable=False)  # vulnerability, alert, fim, sca, mitre, agent
    rule_key = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="No evaluado")
    score = db.Column(db.Float, nullable=False, default=0)
    evidence_count = db.Column(db.Integer, nullable=False, default=0)
    evidence_summary = db.Column(db.Text, nullable=True)
    last_evaluated_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("standard", "control_code", "source_type", name="uq_cont_control_map"),
    )


class ContinuousEvidence(db.Model):
    __tablename__ = "continuous_evidences"

    id = db.Column(db.Integer, primary_key=True)
    standard = db.Column(db.String(50), nullable=False, index=True)
    control_code = db.Column(db.String(100), nullable=False, index=True)
    control_name = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(100), nullable=False, default="Wazuh")
    source_type = db.Column(db.String(50), nullable=True)
    event_ref = db.Column(db.String(500), nullable=True)
    asset = db.Column(db.String(255), nullable=True)
    severity = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(50), nullable=True, default="No evaluado")
    description = db.Column(db.Text, nullable=True)
    evidence_date = db.Column(db.DateTime, default=datetime.utcnow)
    raw_json = db.Column(db.Text, nullable=True)


class ContinuousComplianceSyncLog(db.Model):
    __tablename__ = "continuous_compliance_sync_logs"

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=False, default="En proceso")
    message = db.Column(db.Text, nullable=True)
    agents_count = db.Column(db.Integer, default=0)
    vulnerabilities_count = db.Column(db.Integer, default=0)
    alerts_count = db.Column(db.Integer, default=0)
    fim_count = db.Column(db.Integer, default=0)
    sca_count = db.Column(db.Integer, default=0)
    mitre_count = db.Column(db.Integer, default=0)


class ContinuousActionPlan(db.Model):
    __bind_key__ = "planes_accion"
    __tablename__ = "continuous_action_plans"

    id = db.Column(db.Integer, primary_key=True)
    origin = db.Column(db.String(100), nullable=False, default="Wazuh")
    standard = db.Column(db.String(50), nullable=True)
    control_code = db.Column(db.String(100), nullable=True)
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)
    asset = db.Column(db.String(255), nullable=True)
    severity = db.Column(db.String(50), nullable=True)
    action_type = db.Column(db.String(100), nullable=True)  # Remediación / Incidente / Hallazgo
    responsible = db.Column(db.String(255), nullable=True)
    due_date = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="Abierto")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    source_ref = db.Column(db.String(500), nullable=True)
    raw_json = db.Column(db.Text, nullable=True)


class ContinuousActionPlanSuppression(db.Model):
    """Evita que una fuente automática vuelva a crear un plan eliminado."""
    __bind_key__ = "planes_accion"
    __tablename__ = "continuous_action_plan_suppressions"

    id = db.Column(db.Integer, primary_key=True)
    source_ref = db.Column(db.String(500), nullable=False, unique=True, index=True)
    deleted_plan_id = db.Column(db.Integer, nullable=True)
    deleted_title = db.Column(db.String(500), nullable=True)
    deleted_by = db.Column(db.String(255), nullable=True)
    deleted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


def migrar_planes_accion_a_db_independiente():
    """
    Copia de forma segura los planes existentes desde la tabla histórica
    continuous_action_plans de instance/sgsi.db hacia instance/planes_accion.db.

    - No elimina la tabla anterior: queda como respaldo.
    - INSERT OR IGNORE evita duplicar registros al reiniciar la aplicación.
    - Solo copia columnas presentes en ambas bases para tolerar futuras ampliaciones.
    """
    origen_path = os.path.join(app.instance_path, "sgsi.db")
    destino_path = PLANES_ACCION_DB_PATH

    if not os.path.exists(origen_path):
        return 0

    conn_origen = None
    conn_destino = None

    try:
        conn_origen = sqlite3.connect(origen_path)
        conn_origen.row_factory = sqlite3.Row
        cur_origen = conn_origen.cursor()

        existe_origen = cur_origen.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='continuous_action_plans'"
        ).fetchone()
        if not existe_origen:
            return 0

        conn_destino = sqlite3.connect(destino_path)
        cur_destino = conn_destino.cursor()

        existe_destino = cur_destino.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='continuous_action_plans'"
        ).fetchone()
        if not existe_destino:
            return 0

        columnas_origen = {
            fila[1] for fila in cur_origen.execute(
                "PRAGMA table_info(continuous_action_plans)"
            ).fetchall()
        }
        columnas_destino = {
            fila[1] for fila in cur_destino.execute(
                "PRAGMA table_info(continuous_action_plans)"
            ).fetchall()
        }

        orden_columnas = [
            "id", "origin", "standard", "control_code", "title",
            "description", "asset", "severity", "action_type",
            "responsible", "due_date", "status", "created_at",
            "source_ref", "raw_json"
        ]
        columnas = [
            nombre for nombre in orden_columnas
            if nombre in columnas_origen and nombre in columnas_destino
        ]

        if "id" not in columnas or "title" not in columnas:
            return 0

        columnas_sql = ", ".join(f'"{nombre}"' for nombre in columnas)
        placeholders = ", ".join("?" for _ in columnas)

        filas = cur_origen.execute(
            f"SELECT {columnas_sql} FROM continuous_action_plans ORDER BY id"
        ).fetchall()
        if not filas:
            return 0

        cambios_antes = conn_destino.total_changes
        cur_destino.executemany(
            f"INSERT OR IGNORE INTO continuous_action_plans ({columnas_sql}) "
            f"VALUES ({placeholders})",
            [tuple(fila[nombre] for nombre in columnas) for fila in filas]
        )
        conn_destino.commit()

        migrados = conn_destino.total_changes - cambios_antes
        if migrados:
            print(
                f"Planes de acción migrados a instance/planes_accion.db: {migrados}"
            )
        return migrados

    except Exception as e:
        if conn_destino is not None:
            try:
                conn_destino.rollback()
            except Exception:
                pass
        print("No se pudieron migrar los planes de acción:", repr(e))
        return 0

    finally:
        if conn_origen is not None:
            conn_origen.close()
        if conn_destino is not None:
            conn_destino.close()

class WazuhComplianceControl(db.Model):
    __tablename__ = "wazuh_compliance_controls"

    id = db.Column(db.Integer, primary_key=True)

    standard = db.Column(db.String(50), nullable=False, index=True)
    control_code = db.Column(db.String(100), nullable=False, index=True)
    control_name = db.Column(db.Text, nullable=True)

    alert_id = db.Column(db.String(255), nullable=True, index=True)
    agent_id = db.Column(db.String(80), nullable=True)
    agent_name = db.Column(db.String(255), nullable=True)

    rule_id = db.Column(db.String(80), nullable=True)
    rule_level = db.Column(db.Integer, default=0)
    rule_description = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(50), nullable=False, default="Needs review")
    severity = db.Column(db.String(50), nullable=True)

    raw_json = db.Column(db.Text, nullable=True)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("standard", "control_code", "alert_id", name="uq_wazuh_compliance_control_alert"),
    )

class ContinuousManualEvidence(db.Model):
    __tablename__ = "continuous_manual_evidences"

    id = db.Column(db.Integer, primary_key=True)

    standard = db.Column(db.String(50), nullable=False, index=True)
    control_code = db.Column(db.String(100), nullable=False, index=True)
    control_name = db.Column(db.Text, nullable=True)

    evaluation_type = db.Column(db.String(50), nullable=False, default="MANUAL")
    proposed_status = db.Column(db.String(50), nullable=False, default="No evaluado")
    approval_status = db.Column(db.String(50), nullable=False, default="Pendiente")

    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)

    file_name = db.Column(db.String(500), nullable=True)
    file_path = db.Column(db.String(1000), nullable=True)

    uploaded_by = db.Column(db.String(255), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviewed_by = db.Column(db.String(255), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_comment = db.Column(db.Text, nullable=True)

    valid_until = db.Column(db.String(20), nullable=True)


# ============================================================
# MAPEO BASE WAZUH -> ESTÁNDARES
# ============================================================

CONTINUOUS_CONTROL_LIBRARY = [
    # ISO 27001:2022
    ("ISO27001", "A.8.1", "Dispositivos endpoint de usuario", "agent", "agent_active"),
    ("ISO27001", "A.8.7", "Protección contra malware", "alert", "malware"),
    ("ISO27001", "A.8.8", "Gestión de vulnerabilidades técnicas", "vulnerability", "critical_high_vulns"),
    ("ISO27001", "A.8.9", "Gestión de configuración", "sca", "failed_sca"),
    ("ISO27001", "A.8.15", "Logging", "alert", "security_events"),
    ("ISO27001", "A.8.16", "Actividades de monitoreo", "alert", "security_events"),
    ("ISO27001", "A.8.19", "Instalación de software en sistemas operacionales", "fim", "fim_changes"),

    # SOC 2
    ("SOC2", "CC6", "Controles de acceso lógico", "alert", "auth_access"),
    ("SOC2", "CC7", "Monitoreo, detección y respuesta", "alert", "security_events"),
    ("SOC2", "CC8", "Gestión de cambios", "fim", "fim_changes"),
    ("SOC2", "CC9", "Gestión de riesgos", "vulnerability", "critical_high_vulns"),

    # PCI-DSS 4.0
    ("PCIDSS", "REQ-5", "Proteger sistemas contra malware", "alert", "malware"),
    ("PCIDSS", "REQ-6", "Desarrollar y mantener sistemas seguros", "vulnerability", "critical_high_vulns"),
    ("PCIDSS", "REQ-10", "Registrar y monitorear accesos", "alert", "security_events"),
    ("PCIDSS", "REQ-11", "Probar regularmente la seguridad", "sca", "failed_sca"),
    ("PCIDSS", "REQ-12", "Mantener programa de seguridad", "agent", "agent_active"),

    # NIST CSF 2.0
    ("NISTCSF", "GV.RM", "Estrategia de gestión de riesgos", "vulnerability", "critical_high_vulns"),
    ("NISTCSF", "ID.AM", "Gestión de activos", "agent", "agent_active"),
    ("NISTCSF", "PR.PS", "Seguridad de plataforma", "sca", "failed_sca"),
    ("NISTCSF", "DE.CM", "Monitoreo continuo", "alert", "security_events"),
    ("NISTCSF", "RS.AN", "Análisis de incidentes", "mitre", "mitre_events"),
]


def cont_comp_current_user():
    return User.query.get(session.get("user_id"))


def cont_comp_can_read(user):
    if not user:
        return False
    if user.role in ("admin", "auditor"):
        return True
    return verificar_permiso(user, CONT_COMP_MODULE_NAME)


def cont_comp_can_write(user):
    if not user:
        return False
    if user.role == "auditor":
        return False
    if user.role == "admin":
        return True
    return verificar_permiso(user, CONT_COMP_MODULE_NAME)


def cont_comp_require_read():
    user = cont_comp_current_user()
    if not cont_comp_can_read(user):
        flash("No tiene permiso para acceder a Cumplimiento Continuo.", "danger")
        return None, redirect(url_for("menu"))
    return user, None


def cont_comp_require_write():
    user = cont_comp_current_user()
    if user and user.role == "auditor":
        flash("El rol Auditor solo puede consultar este módulo.", "warning")
        return None, redirect(url_for("cont_comp_dashboard"))
    if not cont_comp_can_write(user):
        flash("No tiene permiso para modificar Cumplimiento Continuo.", "danger")
        return None, redirect(url_for("menu"))
    return user, None


def cont_comp_now():
    return datetime.utcnow()


def cont_comp_status_badge(status):
    s = (status or "No evaluado").strip()
    cls = {
        "Cumple": "success",
        "Parcial": "warning",
        "No cumple": "danger",
        "No evaluado": "secondary",
    }.get(s, "secondary")
    return f'<span class="badge bg-{cls}">{s}</span>'

# ============================================================
# BADGES ACTUALIZADOS
# ============================================================

def cont_comp_status_badge(status):
    s = (status or "No monitoreado").strip()

    cls = {
        "Cumple": "success",
        "Parcial": "warning",
        "No cumple": "danger",
        "No monitoreado": "secondary",
        "No evaluado": "secondary",
    }.get(s, "secondary")

    label = "No monitoreado" if s == "No evaluado" else s

    return f'<span class="badge bg-{cls}">{label}</span>'


def cont_comp_approval_badge(status):
    s = (status or "Pendiente").strip()

    cls = {
        "Pendiente": "warning",
        "Aprobado": "success",
        "Rechazado": "danger",
    }.get(s, "secondary")

    return f'<span class="badge bg-{cls}">{s}</span>'


def cont_comp_severity(value):
    v = (value or "").strip().lower()
    if v in ("critical", "critico", "crítico"):
        return "Crítica"
    if v in ("high", "alto", "alta"):
        return "Alta"
    if v in ("medium", "medio", "media"):
        return "Media"
    if v in ("low", "bajo", "baja"):
        return "Baja"
    return value or "N/A"


def cont_comp_get_config():
    cfg = WazuhConfig.query.first()
    if not cfg:
        cfg = WazuhConfig(api_url="https://localhost:55000", username="wazuh-wui", verify_ssl=False)
        db.session.add(cfg)
        db.session.commit()
    return cfg


def cont_comp_wazuh_headers(cfg):
    if cfg.token:
        return {"Authorization": f"Bearer {cfg.token}"}
    return {}


def cont_comp_wazuh_authenticate(cfg):
    api_url = (cfg.api_url or "").rstrip("/")
    if not api_url:
        raise RuntimeError("URL API Wazuh no configurada.")

    resp = requests.get(
        f"{api_url}/security/user/authenticate",
        auth=(cfg.username or "", cfg.password or ""),
        verify=bool(cfg.verify_ssl),
        timeout=20
    )
    resp.raise_for_status()
    data = resp.json() or {}
    token = data.get("data", {}).get("token") or data.get("token")
    if not token:
        raise RuntimeError(f"Wazuh no devolvió token. Respuesta: {str(data)[:500]}")
    cfg.token = token
    cfg.last_status = "Online"
    cfg.last_message = "Conexión exitosa."
    cfg.last_test_at = cont_comp_now()
    db.session.commit()
    return token


def cont_comp_wazuh_get(cfg, path, params=None):
    api_url = (cfg.api_url or "").rstrip("/")
    if not cfg.token:
        cont_comp_wazuh_authenticate(cfg)

    resp = requests.get(
        f"{api_url}{path}",
        headers=cont_comp_wazuh_headers(cfg),
        params=params or {},
        verify=bool(cfg.verify_ssl),
        timeout=40
    )

    if resp.status_code == 401:
        cont_comp_wazuh_authenticate(cfg)
        resp = requests.get(
            f"{api_url}{path}",
            headers=cont_comp_wazuh_headers(cfg),
            params=params or {},
            verify=bool(cfg.verify_ssl),
            timeout=40
        )

    resp.raise_for_status()
    return resp.json() or {}


def cont_comp_extract_items(data):
    if not isinstance(data, dict):
        return []
    d = data.get("data", data)
    if isinstance(d, dict):
        for key in ("affected_items", "items", "alerts", "results"):
            if isinstance(d.get(key), list):
                return d.get(key)
    if isinstance(d, list):
        return d
    return []


def cont_comp_seed_controls():
    for standard, code, name, source_type, rule_key in CONTINUOUS_CONTROL_LIBRARY:
        existing = ContinuousControl.query.filter_by(
            standard=standard,
            control_code=code,
            source_type=source_type
        ).first()
        if not existing:
            db.session.add(ContinuousControl(
                standard=standard,
                control_code=code,
                control_name=name,
                source_type=source_type,
                rule_key=rule_key,
                status="No evaluado",
                score=0
            ))
    db.session.commit()



def cont_comp_migrate_evidence_schema():
    """Agrega columnas nuevas sin perder evidencias existentes."""
    try:
        rows = db.session.execute(text("PRAGMA table_info(continuous_evidences)")).fetchall()
        columns = {row[1] for row in rows}
        if "status" not in columns:
            db.session.execute(text("ALTER TABLE continuous_evidences ADD COLUMN status VARCHAR(50)"))
            db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print("No se pudo actualizar el esquema de evidencias de Cumplimiento Continuo:", repr(exc))


def init_continuous_compliance_db():
    with app.app_context():
        # Crea las tablas de la base principal y de todos los binds,
        # incluida instance/planes_accion.db.
        db.create_all()
        cont_comp_migrate_evidence_schema()
        migrar_planes_accion_a_db_independiente()
        cont_comp_seed_controls()


# Llamado automático al iniciar
try:
    init_continuous_compliance_db()
except Exception as e:
    print("No se pudo inicializar Cumplimiento Continuo:", repr(e))


def cont_comp_apply_control_evaluation():
    controls = ContinuousControl.query.all()

    counts = {
        "agents_active": WazuhAgent.query.filter(WazuhAgent.status.ilike("%active%")).count(),
        "agents_total": WazuhAgent.query.count(),
        "vuln_critical_high": WazuhVulnerability.query.filter(
            WazuhVulnerability.severity.in_(["Critical", "High", "Crítica", "Alta", "critical", "high"])
        ).count(),
        "alerts_high": WazuhAlert.query.filter(WazuhAlert.rule_level >= 10).count(),
        "fim_events": WazuhFimEvent.query.count(),
        "sca_failed": WazuhSCAResult.query.filter(WazuhSCAResult.result.ilike("%fail%")).count(),
        "mitre_events": WazuhMitreEvent.query.count(),
    }

    for c in controls:
        score = 0
        status = "No evaluado"
        evidence_count = 0
        summary = ""

        if c.source_type == "agent":
            total = counts["agents_total"]
            active = counts["agents_active"]

            evidence_count = total
            summary = f"{active}/{total} agentes activos"

            if total == 0:
                status = "No evaluado"
                score = 0
            elif active == total:
                status = "Cumple"
                score = 100
            elif active > 0:
                status = "Parcial"
                score = round((active / total) * 100, 2)
            else:
                status = "No cumple"
                score = 0

        elif c.source_type == "vulnerability":
            evidence_count = counts["vuln_critical_high"]
            summary = f"{evidence_count} vulnerabilidades críticas/altas"

            if evidence_count == 0:
                status = "Cumple"
                score = 100
            elif evidence_count <= 5:
                status = "Parcial"
                score = 70
            else:
                status = "No cumple"
                score = 30

        elif c.source_type == "alert":
            evidence_count = counts["alerts_high"]
            summary = f"{evidence_count} alertas de severidad alta o crítica"

            if evidence_count == 0:
                status = "Cumple"
                score = 100
            elif evidence_count <= 10:
                status = "Parcial"
                score = 70
            else:
                status = "No cumple"
                score = 30

        elif c.source_type == "sca":
            failed = counts["sca_failed"]
            total_checks = WazuhSCAResult.query.count()
            passed = max(total_checks - failed, 0)

            evidence_count = failed
            summary = f"{passed}/{total_checks} verificaciones SCA cumplen"

            if total_checks == 0:
                status = "No evaluado"
                score = 0
            elif failed == 0:
                status = "Cumple"
                score = 100
            elif failed <= 10:
                status = "Parcial"
                score = 65
            else:
                status = "No cumple"
                score = 30

        elif c.source_type == "fim":
            evidence_count = counts["fim_events"]
            summary = f"{evidence_count} eventos de integridad detectados"

            if evidence_count == 0:
                status = "No evaluado"
                score = 0
            else:
                status = "Parcial"
                score = 75

        elif c.source_type == "mitre":
            evidence_count = counts["mitre_events"]
            summary = f"{evidence_count} técnicas MITRE detectadas"

            if evidence_count == 0:
                status = "No evaluado"
                score = 0
            elif evidence_count <= 10:
                status = "Parcial"
                score = 70
            else:
                status = "No cumple"
                score = 40

        c.status = status
        c.score = score
        c.evidence_count = evidence_count
        c.evidence_summary = summary
        c.last_evaluated_at = cont_comp_now()

    db.session.commit()


def cont_comp_create_evidence(standard, code, name, source_type, ref, asset, severity, description, raw):
    exists = ContinuousEvidence.query.filter_by(
        standard=standard,
        control_code=code,
        event_ref=str(ref)
    ).first()
    if exists:
        return

    db.session.add(ContinuousEvidence(
        standard=standard,
        control_code=code,
        control_name=name,
        source="Wazuh",
        source_type=source_type,
        event_ref=str(ref),
        asset=asset,
        severity=severity,
        description=description,
        raw_json=json.dumps(raw, ensure_ascii=False)[:100000] if raw is not None else None
    ))


def cont_comp_generate_evidences_and_actions():
    # Limpieza simple para evitar duplicados excesivos: no borra histórico.
    mappings = ContinuousControl.query.all()

    # Vulnerabilidades críticas/altas -> evidencias + planes de remediación
    vulns = WazuhVulnerability.query.filter(
        WazuhVulnerability.severity.in_(["Critical", "High", "Crítica", "Alta", "critical", "high"])
    ).limit(200).all()

    for v in vulns:
        related = [m for m in mappings if m.source_type == "vulnerability"]
        for m in related:
            cont_comp_create_evidence(
                m.standard, m.control_code, m.control_name, "Vulnerabilidad",
                v.unique_key, v.agent_name, cont_comp_severity(v.severity),
                f"{v.cve or 'CVE'} - {v.title or v.package_name or 'Vulnerabilidad detectada'}",
                {"cve": v.cve, "package": v.package_name, "cvss": v.cvss}
            )

        plan_exists = ContinuousActionPlan.query.filter_by(source_ref=v.unique_key, action_type="Remediación").first()
        if not plan_exists and not pa_source_is_suppressed(v.unique_key):
            db.session.add(ContinuousActionPlan(
                origin="Wazuh",
                standard="ISO27001",
                control_code="A.8.8",
                title=f"Remediar vulnerabilidad {v.cve or v.package_name or v.unique_key}",
                description=v.title or v.condition or "Vulnerabilidad detectada por Wazuh.",
                asset=v.agent_name,
                severity=cont_comp_severity(v.severity),
                action_type="Remediación",
                status="Abierto",
                source_ref=v.unique_key,
                raw_json=v.raw_json
            ))

    # Alertas críticas/altas -> incidentes
    alerts = WazuhAlert.query.filter(WazuhAlert.rule_level >= 12).limit(200).all()
    for a in alerts:
        related = [m for m in mappings if m.source_type == "alert"]
        for m in related:
            cont_comp_create_evidence(
                m.standard, m.control_code, m.control_name, "Alerta",
                a.alert_id, a.agent_name, cont_comp_severity(a.severity),
                a.rule_description or "Alerta de seguridad Wazuh",
                {"rule_id": a.rule_id, "level": a.rule_level, "mitre": a.mitre_ids}
            )

        plan_exists = ContinuousActionPlan.query.filter_by(source_ref=a.alert_id, action_type="Incidente").first()
        if not plan_exists and not pa_source_is_suppressed(a.alert_id):
            db.session.add(ContinuousActionPlan(
                origin="Wazuh",
                standard="ISO27001",
                control_code="A.5.24",
                title=f"Gestionar alerta crítica Wazuh nivel {a.rule_level}",
                description=a.rule_description or "Alerta crítica generada por Wazuh.",
                asset=a.agent_name,
                severity="Crítica" if (a.rule_level or 0) >= 12 else "Alta",
                action_type="Incidente",
                status="Abierto",
                source_ref=a.alert_id,
                raw_json=a.raw_json
            ))

    # SCA fallido -> hallazgos
    scas = WazuhSCAResult.query.filter(WazuhSCAResult.result.ilike("%fail%")).limit(200).all()
    for s in scas:
        related = [m for m in mappings if m.source_type == "sca"]
        for m in related:
            cont_comp_create_evidence(
                m.standard, m.control_code, m.control_name, "SCA",
                s.unique_key, s.agent_name, "Media",
                s.title or "Control de configuración fallido",
                {"policy": s.policy_name, "check_id": s.check_id, "result": s.result}
            )

        plan_exists = ContinuousActionPlan.query.filter_by(source_ref=s.unique_key, action_type="Hallazgo").first()
        if not plan_exists and not pa_source_is_suppressed(s.unique_key):
            db.session.add(ContinuousActionPlan(
                origin="Wazuh",
                standard="ISO27001",
                control_code="A.8.9",
                title=f"Corregir configuración insegura: {s.check_id or s.policy_name}",
                description=s.title or "Control SCA fallido detectado por Wazuh.",
                asset=s.agent_name,
                severity="Media",
                action_type="Hallazgo",
                status="Abierto",
                source_ref=s.unique_key,
                raw_json=s.raw_json
            ))

    db.session.commit()


def cont_comp_sync_agents(cfg):
    data = cont_comp_wazuh_get(cfg, "/agents", {"limit": 500})
    items = cont_comp_extract_items(data)
    count = 0
    for it in items:
        wid = str(it.get("id") or it.get("agent_id") or "")
        if not wid:
            continue
        row = WazuhAgent.query.filter_by(wazuh_id=wid).first() or WazuhAgent(wazuh_id=wid)
        row.name = it.get("name")
        row.ip = it.get("ip")
        osinfo = it.get("os") or {}
        row.os_name = osinfo.get("name")
        row.os_version = osinfo.get("version")
        row.status = it.get("status")
        row.last_keep_alive = it.get("lastKeepAlive") or it.get("last_keep_alive")
        row.raw_json = json.dumps(it, ensure_ascii=False)
        row.synced_at = cont_comp_now()
        db.session.add(row)
        count += 1
    db.session.commit()
    return count


def cont_comp_sync_vulnerabilities(cfg):
    # Wazuh puede variar endpoint por versión. Se intentan endpoints comunes.
    agents = WazuhAgent.query.all()
    count = 0
    for ag in agents:
        possible_paths = [
            f"/vulnerability/{ag.wazuh_id}",
            f"/vulnerability/{ag.wazuh_id}/inventory",
            f"/agents/{ag.wazuh_id}/vulnerability"
        ]
        items = []
        for path in possible_paths:
            try:
                data = cont_comp_wazuh_get(cfg, path, {"limit": 500})
                items = cont_comp_extract_items(data)
                if items:
                    break
            except Exception:
                continue

        for it in items:
            cve = it.get("cve") or it.get("cve_id") or it.get("name")
            pkg = it.get("package", {}).get("name") if isinstance(it.get("package"), dict) else it.get("package_name")
            unique = f"{ag.wazuh_id}:{cve}:{pkg}:{it.get('version') or it.get('package_version')}"
            row = WazuhVulnerability.query.filter_by(unique_key=unique).first() or WazuhVulnerability(unique_key=unique)
            row.agent_id = ag.wazuh_id
            row.agent_name = ag.name
            row.cve = cve
            row.package_name = pkg
            row.package_version = it.get("version") or it.get("package_version")
            row.severity = it.get("severity") or it.get("cvss", {}).get("severity") if isinstance(it.get("cvss"), dict) else it.get("severity")
            try:
                row.cvss = float(it.get("cvss3_score") or it.get("cvss2_score") or it.get("score") or 0)
            except Exception:
                row.cvss = None
            row.title = it.get("title") or it.get("description")
            row.condition = it.get("condition")
            row.raw_json = json.dumps(it, ensure_ascii=False)
            row.synced_at = cont_comp_now()
            db.session.add(row)
            count += 1
    db.session.commit()
    return count


def cont_comp_sync_alerts(cfg):
    possible_paths = ["/security/events", "/alerts", "/events"]

    items = []

    for path in possible_paths:
        try:
            data = cont_comp_wazuh_get(cfg, path, {"limit": 1000, "sort": "-timestamp"})
            items = cont_comp_extract_items(data)

            if items:
                break

        except Exception:
            continue

    count = 0
    compliance_count = 0

    for it in items:
        alert_id = str(it.get("id") or it.get("_id") or it.get("timestamp") or uuid.uuid4().hex)

        agent = it.get("agent") or {}
        rule = it.get("rule") or {}
        mitre = rule.get("mitre") or {}

        level = int(rule.get("level") or it.get("rule_level") or 0)

        row = WazuhAlert.query.filter_by(alert_id=alert_id).first() or WazuhAlert(alert_id=alert_id)

        row.timestamp = it.get("timestamp")
        row.agent_id = agent.get("id")
        row.agent_name = agent.get("name")
        row.rule_id = str(rule.get("id") or "")
        row.rule_level = level
        row.rule_description = rule.get("description") or it.get("description")
        row.mitre_ids = json.dumps(mitre.get("id") or mitre, ensure_ascii=False)
        row.groups = json.dumps(rule.get("groups") or [], ensure_ascii=False)
        row.severity = "Crítica" if level >= 12 else ("Alta" if level >= 7 else ("Media" if level >= 3 else "Baja"))
        row.raw_json = json.dumps(it, ensure_ascii=False)
        row.synced_at = cont_comp_now()

        db.session.add(row)

        compliance_count += cont_comp_save_compliance_controls_from_alert(
            alert_id=alert_id,
            agent=agent,
            rule=rule,
            raw=it
        )

        count += 1

    db.session.commit()

    return count



def cont_comp_classify_nist_reference(value):
    """
    Clasifica una etiqueta de cumplimiento Wazuh sin confundir NIST CSF 2.0
    con NIST SP 800-53.
    """
    normalized = re.sub(r"[^a-z0-9]+", "", str(value or "").lower())
    if "nist" not in normalized:
        return None

    if "80053" in normalized or "sp80053" in normalized:
        return "NIST80053"

    if "csf" in normalized or normalized in {"nist", "nist2", "nist20", "nistv20"}:
        return "NISTCSF"

    return None


def cont_comp_sync_sca(cfg):
    agents = WazuhAgent.query.all()
    count = 0

    for ag in agents:
        try:
            data = cont_comp_wazuh_get(cfg, f"/sca/{ag.wazuh_id}", {"limit": 500})
            policies = cont_comp_extract_items(data)
        except Exception:
            policies = []

        for p in policies:
            policy_id = p.get("policy_id") or p.get("id")
            policy_name = p.get("name") or p.get("policy_name")

            try:
                checks_data = cont_comp_wazuh_get(
                    cfg,
                    f"/sca/{ag.wazuh_id}/checks/{policy_id}",
                    {"limit": 1000}
                )
                checks = cont_comp_extract_items(checks_data)
            except Exception:
                checks = []

            for chk in checks:
                check_id = str(chk.get("id") or chk.get("check_id") or uuid.uuid4().hex)
                unique = f"{ag.wazuh_id}:{policy_id}:{check_id}"

                result = chk.get("result") or chk.get("status") or ""
                status, score, severity = cont_comp_source_status("sca", result=result)
                level = 8 if status == "No cumple" else (1 if status == "Cumple" else 0)

                row = WazuhSCAResult.query.filter_by(unique_key=unique).first() or WazuhSCAResult(unique_key=unique)
                row.agent_id = ag.wazuh_id
                row.agent_name = ag.name
                row.policy_id = str(policy_id or "")
                row.policy_name = policy_name
                row.check_id = check_id
                row.title = chk.get("title") or chk.get("description")
                row.result = result
                row.compliance = json.dumps(chk.get("compliance") or [], ensure_ascii=False)
                row.raw_json = json.dumps(chk, ensure_ascii=False)
                row.synced_at = cont_comp_now()

                db.session.add(row)
                count += 1

                compliance_items = chk.get("compliance") or []

                if isinstance(compliance_items, dict):
                    compliance_items = [compliance_items]

                if not isinstance(compliance_items, list):
                    compliance_items = []

                for comp in compliance_items:
                    standard = None
                    control_codes = []

                    if isinstance(comp, dict):
                        key = (comp.get("key") or comp.get("standard") or "").lower()
                        value = comp.get("value") or comp.get("control") or comp.get("id")

                        if "pci" in key:
                            standard = "PCIDSS"
                        elif "soc" in key or "tsc" in key:
                            standard = "SOC2"
                        elif "iso" in key:
                            standard = "ISO27001"
                        elif "nist" in key:
                            standard = cont_comp_classify_nist_reference(key)
                            if standard != "NISTCSF":
                                standard = None

                        control_codes = cont_comp_split_control_codes(value)

                    else:
                        text = str(comp).strip()
                        text_lower = text.lower()

                        if "pci" in text_lower:
                            standard = "PCIDSS"
                        elif "soc" in text_lower or "tsc" in text_lower:
                            standard = "SOC2"
                        elif "iso" in text_lower:
                            standard = "ISO27001"
                        elif "nist" in text_lower:
                            standard = cont_comp_classify_nist_reference(text)
                            if standard != "NISTCSF":
                                standard = None

                        if ":" in text:
                            values = text.split(":", 1)[1]
                        else:
                            values = text

                        control_codes = cont_comp_split_control_codes(values)

                    if not standard or not control_codes:
                        continue

                    resolved_control_codes = []
                    for control_code in control_codes:
                        if standard == "NISTCSF":
                            resolved_control_codes.extend(
                                cont_comp_nist_csf_expand_codes(control_code)
                            )
                        else:
                            resolved_control_codes.append(control_code)

                    resolved_control_codes = list(dict.fromkeys(resolved_control_codes))
                    if not resolved_control_codes:
                        continue

                    for control_code in resolved_control_codes:
                        alert_ref = f"SCA:{unique}:{standard}:{control_code}"

                        existing = WazuhComplianceControl.query.filter_by(
                            standard=standard,
                            control_code=control_code,
                            alert_id=alert_ref
                        ).first()

                        if existing:
                            existing.status = status
                            existing.severity = severity
                            existing.rule_level = level
                            existing.rule_description = row.title or None
                            existing.agent_id = ag.wazuh_id
                            existing.agent_name = ag.name
                            existing.raw_json = row.raw_json
                            existing.synced_at = cont_comp_now()
                            continue

                        db.session.add(WazuhComplianceControl(
                            standard=standard,
                            control_code=control_code,
                            control_name=row.title or control_code,
                            alert_id=alert_ref,
                            agent_id=ag.wazuh_id,
                            agent_name=ag.name,
                            rule_id=f"SCA-{check_id}",
                            rule_level=level,
                            rule_description=row.title or None,
                            status=status,
                            severity=severity,
                            raw_json=row.raw_json,
                            synced_at=cont_comp_now()
                        ))

    db.session.commit()
    return count

CONT_COMP_SUPPLEMENTAL_STANDARD_DESCRIPTIONS = {
    # Respaldo mínimo para puntos que pueden no venir en las listas estáticas
    # antiguas. El instrumento cargado en Mejora/Madurez siempre tiene prioridad.
    "SOC2": {
        "CC6.8": (
            "La entidad implementa controles para prevenir o detectar y actuar ante "
            "la introducción de software no autorizado o malicioso, con el fin de "
            "cumplir los objetivos de la entidad."
        ),
    },
}


def cont_comp_first_text_attr(obj, *attribute_names):
    """Obtiene el primer atributo textual existente sin asumir el esquema del modelo."""
    for attribute_name in attribute_names:
        try:
            value = getattr(obj, attribute_name, None)
        except Exception:
            value = None
        text_value = str(value or "").strip()
        if text_value:
            return text_value
    return ""


def cont_comp_extract_codes_from_instrument_text(standard, value):
    """Extrae códigos normativos escritos dentro del instrumento cargado."""
    standard = (standard or "").strip().upper()
    text_value = str(value or "").upper()
    if not text_value:
        return []

    if standard == "ISO27001":
        patterns = [
            r"\bA\.\d+(?:\.\d+)?\b",
            r"\b(?:4|5|6|7|8|9|10)\.\d+(?:\.\d+)*\b",
        ]
    elif standard == "NISTCSF":
        patterns = [r"\b[A-Z]{2}\.[A-Z]{2}(?:-\d{1,2})?\b"]
    elif standard == "SOC2":
        patterns = [r"\b(?:CC|A|C|PI|P)\d+(?:\.\d+)+\b"]
    elif standard == "PCIDSS":
        patterns = [r"\b(?:A[12]|\d{1,2})(?:\.\d+)+\b"]
    else:
        patterns = []

    found = []
    seen = set()
    for pattern in patterns:
        for raw_code in re.findall(pattern, text_value, flags=re.IGNORECASE):
            code = cont_comp_normalize_code(raw_code)
            if code and code not in seen:
                seen.add(code)
                found.append(code)
    return found


def cont_comp_code_is_valid_for_standard(standard, value):
    standard = (standard or "").strip().upper()
    code = cont_comp_normalize_code(value)
    if not code:
        return False

    if standard == "ISO27001":
        if code.startswith("A."):
            return cont_comp_iso27002_resolve_code(code) is not None
        return bool(re.fullmatch(r"(?:4|5|6|7|8|9|10)\.\d+(?:\.\d+)*", code))

    if standard == "NISTCSF":
        return cont_comp_nist_csf_resolve_code(code) is not None

    patterns = {
        "SOC2": r"^(?:CC|A|C|PI|P)\d+(?:\.\d+)+$",
        "PCIDSS": r"^(?:A[12]|\d{1,2})(?:\.\d+)+$",
    }
    return bool(re.fullmatch(patterns.get(standard, r"$^"), code, flags=re.IGNORECASE))


def cont_comp_strip_code_from_description(description, code):
    text_value = str(description or "").strip()
    code_value = str(code or "").strip()
    if not text_value or not code_value:
        return text_value

    cleaned = re.sub(
        rf"^\s*{re.escape(code_value)}\s*(?:[-–—:;.]\s*)?",
        "",
        text_value,
        count=1,
        flags=re.IGNORECASE,
    ).strip()
    return cleaned or text_value




# ============================================================
# CUMPLIMIENTO CONTINUO - ISO 27002 DESDE EXCEL + TEXTOS EN ESPAÑOL
# ============================================================
CONT_COMP_ISO27002_XLSX_CACHE = {
    "path": None,
    "mtime": None,
    "entries": [],
}


def cont_comp_normalizar_nombre_archivo(value):
    text_value = unicodedata.normalize("NFKD", str(value or ""))
    text_value = "".join(ch for ch in text_value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text_value.lower()).strip()



# ============================================================
# CUMPLIMIENTO CONTINUO - NIST CSF 2.0 DESDE DOCUMENTO OFICIAL
# ============================================================
CONT_COMP_NIST_CSF_DOCX_CACHE = {
    "path": None,
    "mtime": None,
    "entries": [],
    "functions": {},
    "categories": {},
}

CONT_COMP_NIST_CSF_EXPECTED_SUBCATEGORIES = 106
CONT_COMP_NIST_CSF_EXPECTED_FUNCTIONS = ("GV", "ID", "PR", "DE", "RS", "RC")


def cont_comp_nist_csf_docx_path():
    """
    Localiza el documento oficial utilizado por Cumplimiento Continuo:

        static/templates/NIST.CSF 2.0.docx

    Se toleran variaciones menores de espacios, puntos, guiones y mayúsculas.
    """
    folders = []
    for folder in (
        os.path.join(BASE_DIR, "static", "templates"),
        os.path.join(getattr(app, "root_path", BASE_DIR), "static", "templates"),
    ):
        folder = os.path.abspath(folder)
        if folder not in folders:
            folders.append(folder)

    preferred_names = (
        "NIST.CSF 2.0.docx",
        "NIST CSF 2.0.docx",
        "NIST_CSF_2.0.docx",
        "NIST-CSF-2.0.docx",
        "nist.csf 2.0.docx",
    )

    for folder in folders:
        for filename in preferred_names:
            path = os.path.join(folder, filename)
            if os.path.isfile(path):
                return path

    for folder in folders:
        if not os.path.isdir(folder):
            continue
        try:
            filenames = os.listdir(folder)
        except Exception:
            continue

        for filename in filenames:
            if not filename.lower().endswith(".docx"):
                continue
            normalized = cont_comp_normalizar_nombre_archivo(filename)
            words = set(normalized.split())
            if "nist" in words and "csf" in words and "2" in words and "0" in words:
                return os.path.join(folder, filename)

    return None


def cont_comp_nist_csf_entries_from_docx(force_reload=False):
    """
    Lee las funciones, categorías y 106 subcategorías del documento
    ``static/templates/NIST.CSF 2.0.docx``.

    La matriz utiliza únicamente las subcategorías XX.XX-00 presentes en ese
    documento. No se aceptan controles de NIST SP 800-53, como AC-11.
    """
    path = cont_comp_nist_csf_docx_path()
    if not path:
        return []

    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = None

    if (
        not force_reload
        and CONT_COMP_NIST_CSF_DOCX_CACHE.get("path") == path
        and CONT_COMP_NIST_CSF_DOCX_CACHE.get("mtime") == mtime
    ):
        return list(CONT_COMP_NIST_CSF_DOCX_CACHE.get("entries") or [])

    functions = {}
    categories = {}
    entries = []

    try:
        document = Document(path)

        for paragraph in document.paragraphs:
            text_value = re.sub(
                r"\s+",
                " ",
                str(paragraph.text or "").replace("\ufeff", " "),
            ).strip()
            if not text_value:
                continue

            function_match = re.match(
                r"^(.+?)\s+\(([A-Z]{2})\)\s*:\s*(.+)$",
                text_value,
                flags=re.IGNORECASE,
            )
            if function_match:
                function_code = function_match.group(2).upper()
                if function_code in CONT_COMP_NIST_CSF_EXPECTED_FUNCTIONS:
                    functions[function_code] = {
                        "code": function_code,
                        "name": function_match.group(1).strip(),
                        "description": function_match.group(3).strip(),
                    }
                continue

            category_match = re.match(
                r"^(.+?)\s+\(([A-Z]{2}\.[A-Z]{2})\)\s*:\s*(.+)$",
                text_value,
                flags=re.IGNORECASE,
            )
            if category_match:
                category_code = category_match.group(2).upper()
                categories[category_code] = {
                    "code": category_code,
                    "name": category_match.group(1).strip(),
                    "description": category_match.group(3).strip(),
                    "function_code": category_code.split(".", 1)[0],
                }
                continue

            detail_match = re.match(
                r"^([A-Z]{2}\.[A-Z]{2}-\d{2})\s*:\s*(.+)$",
                text_value,
                flags=re.IGNORECASE,
            )
            if not detail_match:
                continue

            code = detail_match.group(1).upper()
            description = detail_match.group(2).strip()
            parent = code.split("-", 1)[0]
            function_code = code.split(".", 1)[0]
            category_info = categories.get(parent, {})
            function_info = functions.get(function_code, {})

            entries.append({
                "code": code,
                "name": description,
                "description": description,
                "parent": parent,
                "category_code": parent,
                "category_name": category_info.get("name") or parent,
                "category_description": category_info.get("description") or "",
                "function_code": function_code,
                "function_name": function_info.get("name") or function_code,
                "function_description": function_info.get("description") or "",
                "source": "NIST_CSF_20_DOCX",
                "path": path,
            })

    except Exception as exc:
        print(
            "No se pudo leer static/templates/NIST.CSF 2.0.docx "
            f"para Cumplimiento Continuo: {repr(exc)}"
        )
        return []

    codes = [entry["code"] for entry in entries]
    expected_functions = set(CONT_COMP_NIST_CSF_EXPECTED_FUNCTIONS)

    if len(entries) != CONT_COMP_NIST_CSF_EXPECTED_SUBCATEGORIES:
        print(
            "El documento NIST CSF 2.0 no contiene las 106 subcategorías "
            f"esperadas. Se encontraron {len(entries)}."
        )
        return []

    if len(codes) != len(set(codes)):
        print("El documento NIST CSF 2.0 contiene códigos duplicados.")
        return []

    if set(functions) != expected_functions:
        print(
            "El documento NIST CSF 2.0 no contiene exactamente las funciones "
            "GV, ID, PR, DE, RS y RC."
        )
        return []

    if len(categories) != 22:
        print(
            "El documento NIST CSF 2.0 no contiene las 22 categorías "
            f"esperadas. Se encontraron {len(categories)}."
        )
        return []

    for entry in entries:
        if entry["parent"] not in categories:
            print(
                "El documento NIST CSF 2.0 contiene una subcategoría sin "
                f"categoría reconocida: {entry['code']}."
            )
            return []

    CONT_COMP_NIST_CSF_DOCX_CACHE.update({
        "path": path,
        "mtime": mtime,
        "entries": list(entries),
        "functions": dict(functions),
        "categories": dict(categories),
    })
    return entries


def cont_comp_nist_csf_official_catalog():
    """
    Devuelve las 106 subcategorías oficiales de NIST CSF 2.0.

    Cuando el DOCX está disponible, sus códigos y descripciones tienen
    prioridad absoluta. La lista incorporada solo se usa como respaldo si el
    archivo no está instalado.
    """
    document_entries = cont_comp_nist_csf_entries_from_docx()
    if document_entries:
        return {entry["code"]: entry for entry in document_entries}

    fallback = {}
    for raw_code, normative_description in NIST_CSF_20_CONTROLES:
        code = cont_comp_normalize_code(raw_code)
        if not re.fullmatch(r"[A-Z]{2}\.[A-Z]{2}-\d{2}", code or ""):
            continue
        fallback[code] = {
            "code": code,
            "name": str(normative_description or "").strip() or code,
            "description": str(normative_description or "").strip() or code,
            "parent": code.split("-", 1)[0],
            "category_code": code.split("-", 1)[0],
            "function_code": code.split(".", 1)[0],
            "source": "CATALOGO_NIST_CSF_20_INCORPORADO",
            "path": None,
        }
    return fallback


def cont_comp_nist_csf_canonical_subcategory(value):
    """Normaliza una subcategoría NIST CSF y confirma que exista en el DOCX."""
    raw = str(value or "").strip().upper()
    if not raw:
        return None

    raw = raw.replace("_", ".")
    raw = re.sub(r"\s+", "", raw)

    match = re.fullmatch(
        r"([A-Z]{2})[.\-]([A-Z]{2})[.\-](\d{1,2})",
        raw,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    code = f"{match.group(1).upper()}.{match.group(2).upper()}-{int(match.group(3)):02d}"
    return code if code in cont_comp_nist_csf_official_catalog() else None


def cont_comp_nist_csf_expand_codes(value):
    """
    Convierte una referencia NIST CSF en subcategorías válidas del documento.

    - PR.AA-01 -> PR.AA-01.
    - PR.AA    -> todas las subcategorías PR.AA-01 ... PR.AA-06.
    - PR       -> todas las subcategorías de PROTEGER.
    - AC-11    -> ninguna, porque corresponde a NIST SP 800-53 y no a CSF 2.0.
    """
    official = cont_comp_nist_csf_official_catalog()
    raw = str(value or "").strip().upper()
    if not raw:
        return []

    exact = cont_comp_nist_csf_canonical_subcategory(raw)
    if exact:
        return [exact]

    compact = re.sub(r"\s+", "", raw.replace("_", "."))

    category_match = re.fullmatch(
        r"([A-Z]{2})[.\-]([A-Z]{2})",
        compact,
        flags=re.IGNORECASE,
    )
    if category_match:
        prefix = f"{category_match.group(1).upper()}.{category_match.group(2).upper()}"
        return [
            code for code in official
            if code.startswith(prefix + "-")
        ]

    function_match = re.fullmatch(r"([A-Z]{2})", compact, flags=re.IGNORECASE)
    if function_match:
        prefix = function_match.group(1).upper() + "."
        return [code for code in official if code.startswith(prefix)]

    return []


def cont_comp_nist_csf_resolve_code(value):
    """Devuelve solo una subcategoría exacta válida de NIST CSF 2.0."""
    return cont_comp_nist_csf_canonical_subcategory(value)


def cont_comp_iso27002_xlsx_path():
    """Localiza static/templates/anexo A 27002.xlsx sin depender de mayúsculas o tildes."""
    folders = []
    for folder in (
        os.path.join(BASE_DIR, "static", "templates"),
        os.path.join(getattr(app, "root_path", BASE_DIR), "static", "templates"),
    ):
        folder = os.path.abspath(folder)
        if folder not in folders:
            folders.append(folder)

    preferred_names = (
        "anexo A 27002.xlsx",
        "Anexo A 27002.xlsx",
        "ANEXO A 27002.xlsx",
        "anexo_a_27002.xlsx",
        "anexo-a-27002.xlsx",
    )

    for folder in folders:
        for filename in preferred_names:
            path = os.path.join(folder, filename)
            if os.path.isfile(path):
                return path

    # Respaldo tolerante a variaciones menores del nombre.
    for folder in folders:
        if not os.path.isdir(folder):
            continue
        try:
            filenames = os.listdir(folder)
        except Exception:
            continue
        for filename in filenames:
            if not filename.lower().endswith(".xlsx"):
                continue
            normalized = cont_comp_normalizar_nombre_archivo(filename)
            words = set(normalized.split())
            if "anexo" in words and "27002" in words:
                return os.path.join(folder, filename)
    return None


def cont_comp_iso27002_control_code(value):
    text_value = str(value or "").replace("\ufeff", " ").strip().upper()
    if not text_value:
        return None

    match = re.search(
        r"(?<!\d)(?:A\s*[.\-]?\s*)?([5-8])\s*[.\-]\s*(\d{1,2})(?!\d)",
        text_value,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return f"A.{int(match.group(1))}.{int(match.group(2))}"


def cont_comp_limpiar_texto_excel_iso(value, code=None):
    text_value = str(value or "").replace("\ufeff", " ").replace("\r", "\n").strip()
    if not text_value or text_value.lower() in {"nan", "none", "null"}:
        return ""

    text_value = re.sub(r"[ \t]+", " ", text_value)
    text_value = re.sub(r"\n\s*\n+", "\n", text_value).strip()

    if code:
        raw = code.replace("A.", "")
        text_value = re.sub(
            rf"^\s*(?:A\s*[.\-]?\s*)?{re.escape(raw)}\s*(?:[-–—:;.]+\s*)?",
            "",
            text_value,
            count=1,
            flags=re.IGNORECASE,
        ).strip()

    normalized = cont_comp_normalizar_nombre_archivo(text_value)
    ignored_exact = {
        "codigo", "código", "control", "controles", "numero", "número", "no",
        "descripcion", "descripción", "descripcion del control", "descripción del control",
        "nombre", "nombre del control", "titulo", "título", "tema", "dominio",
        "si", "sí", "no aplica", "parcialmente", "parcial", "comentarios", "comentario",
        "estado", "resultado", "cumple", "no cumple", "evidencia", "observaciones",
    }
    if normalized in {cont_comp_normalizar_nombre_archivo(x) for x in ignored_exact}:
        return ""

    # No convertir preguntas del instrumento de madurez en texto normativo.
    if text_value.lstrip().startswith("¿"):
        return ""

    # Encabezados de familias: 5. Controles organizacionales, etc.
    if re.fullmatch(r"[5-8]\s*[.]?\s+.+", text_value, flags=re.IGNORECASE):
        return ""

    ignored_prefixes = (
        "tipo de control", "atributos", "propiedades", "conceptos de seguridad",
        "capacidades operativas", "dominios de seguridad", "propósito del control",
        "orientación", "guía de implementación", "otra información",
    )
    if any(normalized.startswith(cont_comp_normalizar_nombre_archivo(prefix)) for prefix in ignored_prefixes):
        return ""

    return text_value.strip()



CONT_COMP_ISO27002_FAMILY_COUNTS = {
    5: 37,  # Controles organizacionales
    6: 8,   # Controles de personas
    7: 14,  # Controles físicos
    8: 34,  # Controles tecnológicos
}

# Equivalencias únicamente para evidencias históricas que todavía conservan
# numeración del Anexo A de ISO/IEC 27001:2013. La matriz nunca presenta estos
# códigos antiguos: los traduce a un control válido de ISO/IEC 27002:2022.
CONT_COMP_ISO27002_LEGACY_TO_2022 = {
    "A.5.1.1": "A.5.1",
    "A.6.1.1": "A.5.2",
    "A.6.1.2": "A.5.3",
    "A.6.2.1": "A.6.7",
    "A.7.1.1": "A.6.1",
    "A.7.1.2": "A.6.2",
    "A.7.2.1": "A.6.3",
    "A.7.2.2": "A.6.4",
    "A.7.2.3": "A.6.5",
    "A.8.1.1": "A.5.9",
    "A.8.1.2": "A.5.9",
    "A.8.1.3": "A.5.10",
    "A.8.1.4": "A.5.11",
    "A.8.2.1": "A.5.12",
    "A.8.2.2": "A.5.13",
    "A.8.2.3": "A.5.14",
    "A.9.1.1": "A.5.15",
    "A.9.1.2": "A.5.15",
    "A.9.2.1": "A.5.16",
    "A.9.2.2": "A.5.18",
    "A.9.2.3": "A.5.18",
    "A.9.2.4": "A.5.18",
    "A.9.2.5": "A.5.18",
    "A.9.2.6": "A.5.18",
    "A.9.3.1": "A.5.17",
    "A.9.4.1": "A.8.3",
    "A.9.4.2": "A.8.5",
    "A.9.4.3": "A.8.5",
    "A.9.4.4": "A.8.5",
    "A.9.4.5": "A.8.4",
    "A.10.1.1": "A.8.24",
    "A.10.1.2": "A.8.24",
    "A.11.1.1": "A.7.1",
    "A.11.1.2": "A.7.2",
    "A.11.1.3": "A.7.3",
    "A.11.1.4": "A.7.4",
    "A.11.1.5": "A.7.5",
    "A.11.1.6": "A.7.6",
    "A.11.2.1": "A.7.8",
    "A.11.2.2": "A.7.9",
    "A.11.2.3": "A.7.9",
    "A.11.2.4": "A.7.13",
    "A.11.2.5": "A.7.9",
    "A.11.2.6": "A.7.10",
    "A.11.2.7": "A.7.7",
    "A.11.2.8": "A.7.11",
    "A.11.2.9": "A.7.14",
    "A.12.1.1": "A.5.37",
    "A.12.1.2": "A.8.32",
    "A.12.1.3": "A.8.6",
    "A.12.1.4": "A.8.31",
    "A.12.2.1": "A.8.7",
    "A.12.3.1": "A.8.13",
    "A.12.4.1": "A.8.15",
    "A.12.4.2": "A.8.15",
    "A.12.4.3": "A.8.15",
    "A.12.4.4": "A.8.17",
    "A.12.5.1": "A.8.19",
    "A.12.6.1": "A.8.8",
    "A.12.6.2": "A.8.19",
    "A.12.7.1": "A.8.34",
    "A.13.1.1": "A.8.20",
    "A.13.1.2": "A.8.22",
    "A.13.1.3": "A.8.21",
    "A.13.2.1": "A.5.14",
    "A.13.2.2": "A.5.14",
    "A.13.2.3": "A.5.14",
    "A.13.2.4": "A.5.14",
    "A.14.1.1": "A.8.26",
    "A.14.1.2": "A.8.26",
    "A.14.1.3": "A.8.24",
    "A.14.2.1": "A.8.25",
    "A.14.2.2": "A.8.32",
    "A.14.2.3": "A.8.32",
    "A.14.2.4": "A.8.28",
    "A.14.2.5": "A.8.27",
    "A.14.2.6": "A.8.29",
    "A.14.2.7": "A.8.29",
    "A.14.2.8": "A.8.29",
    "A.14.2.9": "A.8.30",
    "A.14.3.1": "A.8.33",
    "A.15.1.1": "A.5.19",
    "A.15.1.2": "A.5.20",
    "A.15.1.3": "A.5.21",
    "A.15.2.1": "A.5.22",
    "A.15.2.2": "A.5.22",
    "A.16.1.1": "A.5.24",
    "A.16.1.2": "A.6.8",
    "A.16.1.3": "A.6.8",
    "A.16.1.4": "A.5.25",
    "A.16.1.5": "A.5.26",
    "A.16.1.6": "A.5.27",
    "A.16.1.7": "A.5.28",
    "A.17.1.1": "A.5.29",
    "A.17.1.2": "A.5.30",
    "A.17.1.3": "A.5.29",
    "A.17.2.1": "A.8.14",
    "A.18.1.1": "A.5.31",
    "A.18.1.2": "A.5.32",
    "A.18.1.3": "A.5.33",
    "A.18.1.4": "A.5.34",
    "A.18.1.5": "A.5.31",
    "A.18.2.1": "A.5.35",
    "A.18.2.2": "A.5.36",
    "A.18.2.3": "A.5.36",
}


def cont_comp_iso27002_entries_from_xlsx(force_reload=False):
    """
    Lee exclusivamente los 93 controles oficiales del archivo:
        static/templates/anexo A 27002.xlsx

    El archivo suministrado guarda algunos códigos como números de Excel. Por
    eso 5.10 puede recibirse como 5.1, 5.20 como 5.2 y 8.30 como 8.3. Para no
    inventar controles, el código se reconstruye por la secuencia oficial de
    cada familia: A.5.1-A.5.37, A.6.1-A.6.8, A.7.1-A.7.14 y A.8.1-A.8.34.
    """
    path = cont_comp_iso27002_xlsx_path()
    if not path:
        return []

    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = None

    if (
        not force_reload
        and CONT_COMP_ISO27002_XLSX_CACHE.get("path") == path
        and CONT_COMP_ISO27002_XLSX_CACHE.get("mtime") == mtime
    ):
        return list(CONT_COMP_ISO27002_XLSX_CACHE.get("entries") or [])

    entries = []
    family_counts = {family: 0 for family in CONT_COMP_ISO27002_FAMILY_COUNTS}

    def clean(value):
        text_value = str(value or "").replace("\ufeff", " ").replace("\r", "\n").strip()
        if not text_value or text_value.lower() in {"nan", "none", "null"}:
            return ""
        text_value = re.sub(r"[ \t]+", " ", text_value)
        return re.sub(r"\n\s*\n+", "\n", text_value).strip()

    def family_from_value(value):
        if value is None:
            return None
        try:
            number = float(value)
            if number.is_integer() and int(number) in CONT_COMP_ISO27002_FAMILY_COUNTS:
                return int(number)
        except Exception:
            pass
        text_value = clean(value)
        match = re.fullmatch(r"([5-8])(?:\.0+)?", text_value)
        return int(match.group(1)) if match else None

    try:
        workbook = load_workbook(path, data_only=True, read_only=True)
        try:
            for worksheet in workbook.worksheets:
                rows = list(worksheet.iter_rows(values_only=True))
                current_family = None
                sequence = 0
                row_index = 0

                while row_index < len(rows):
                    row = list(rows[row_index] or ())
                    while len(row) < 4:
                        row.append(None)

                    code_cell = row[1]
                    title = clean(row[2])
                    marker = clean(row[3])
                    family = family_from_value(code_cell)

                    # Encabezados reales del archivo: 5/6/7/8 y nombre de familia.
                    if (
                        family
                        and title
                        and marker.lower() != "control"
                        and not re.search(r"\.\d+", clean(code_cell))
                    ):
                        current_family = family
                        sequence = 0
                        row_index += 1
                        continue

                    is_control = bool(
                        current_family
                        and title
                        and marker.lower() == "control"
                    )
                    if not is_control:
                        row_index += 1
                        continue

                    sequence += 1
                    expected = CONT_COMP_ISO27002_FAMILY_COUNTS[current_family]
                    if sequence > expected:
                        raise ValueError(
                            f"La familia {current_family} contiene más de {expected} controles."
                        )

                    code = f"A.{current_family}.{sequence}"
                    description_parts = []
                    next_index = row_index + 1

                    while next_index < len(rows):
                        next_row = list(rows[next_index] or ())
                        while len(next_row) < 4:
                            next_row.append(None)

                        next_family = family_from_value(next_row[1])
                        next_title = clean(next_row[2])
                        next_marker = clean(next_row[3])

                        if (
                            next_family
                            and next_title
                            and next_marker.lower() != "control"
                            and not re.search(r"\.\d+", clean(next_row[1]))
                        ):
                            break
                        if next_title and next_marker.lower() == "control":
                            break

                        normative_text = clean(next_row[3])
                        if normative_text and normative_text.lower() != "control":
                            if normative_text not in description_parts:
                                description_parts.append(normative_text)
                        next_index += 1

                    normative_body = "\n".join(description_parts).strip()
                    if not normative_body:
                        raise ValueError(f"El control {code} no tiene descripción en el archivo.")

                    entries.append({
                        "code": code,
                        "name": title,
                        "description": f"{title}\n{normative_body}",
                        "parent": code,
                        "source": "ANEXO_A_27002_XLSX",
                        "path": path,
                    })
                    family_counts[current_family] += 1
                    row_index = next_index
        finally:
            try:
                workbook.close()
            except Exception:
                pass

    except Exception as exc:
        print(f"No se pudo leer el archivo ISO 27002 {path}: {repr(exc)}")
        return []

    expected_total = sum(CONT_COMP_ISO27002_FAMILY_COUNTS.values())
    if len(entries) != expected_total or family_counts != CONT_COMP_ISO27002_FAMILY_COUNTS:
        print(
            "El archivo ISO 27002 no coincide con el Anexo A 2022 esperado. "
            f"Controles leídos: {len(entries)}; familias: {family_counts}."
        )
        return []

    codes = [entry["code"] for entry in entries]
    if len(codes) != len(set(codes)):
        print("El archivo ISO 27002 contiene códigos duplicados después de normalizar.")
        return []

    CONT_COMP_ISO27002_XLSX_CACHE.update({
        "path": path,
        "mtime": mtime,
        "entries": list(entries),
    })
    return entries


def cont_comp_iso27002_official_catalog():
    """Devuelve el catálogo oficial 2022, prefiriendo siempre el Excel suministrado."""
    excel_entries = cont_comp_iso27002_entries_from_xlsx()
    if excel_entries:
        return {entry["code"]: entry for entry in excel_entries}

    # Respaldo autocontenido: también corresponde a los 93 controles de 2022.
    fallback = {}
    for raw_code, normative_description in ISO_27002_CONTROLES:
        raw_code = str(raw_code or "").strip()
        code = raw_code if raw_code.upper().startswith("A.") else f"A.{raw_code}"
        code = cont_comp_normalize_code(code)
        if not re.fullmatch(r"A\.[5-8]\.\d{1,2}", code or ""):
            continue
        lines = [line.strip() for line in str(normative_description or "").splitlines() if line.strip()]
        name = lines[1] if len(lines) >= 2 else (lines[0] if lines else code)
        fallback[code] = {
            "code": code,
            "name": name,
            "description": str(normative_description or "").strip(),
            "parent": code,
            "source": "CATALOGO_ISO27002_2022_INCORPORADO",
            "path": None,
        }
    return fallback


def cont_comp_iso27002_resolve_code(value):
    """
    Devuelve únicamente un control válido del Anexo A 2022.

    - Mantiene códigos oficiales A.5.x, A.6.x, A.7.x y A.8.x.
    - Traduce códigos históricos 2013 cuando existe una equivalencia definida.
    - Devuelve None para puntos inexistentes, evitando que la matriz los cree.
    """
    code = cont_comp_normalize_code(value)
    if not code or not code.startswith("A."):
        return code or None

    official = cont_comp_iso27002_official_catalog()
    if code in official:
        return code

    mapped = CONT_COMP_ISO27002_LEGACY_TO_2022.get(code)
    if mapped and mapped in official:
        return mapped

    return None


def cont_comp_resolve_evidence_code(standard, value, catalog=None):
    """Normaliza el punto de una evidencia antes de incorporarlo a una matriz."""
    standard = (standard or "").strip().upper()
    code = cont_comp_normalize_code(value)
    if not code:
        return None

    if standard == "NISTCSF":
        return cont_comp_nist_csf_resolve_code(code)

    if standard != "ISO27001":
        return code

    if code.startswith("A."):
        return cont_comp_iso27002_resolve_code(code)

    # Los capítulos 4-10 solo se admiten cuando existen en el instrumento.
    catalog = catalog or {}
    return code if code in catalog else None



CONT_COMP_EVIDENCE_TRANSLATIONS = (
    (r"\bfile integrity monitoring\b", "monitoreo de integridad de archivos"),
    (r"\bintegrity monitoring\b", "monitoreo de integridad"),
    (r"\bsecurity configuration assessment\b", "evaluación de configuración de seguridad"),
    (r"\bconfiguration assessment\b", "evaluación de configuración"),
    (r"\bvulnerability detection\b", "detección de vulnerabilidades"),
    (r"\bvulnerability\b", "vulnerabilidad"),
    (r"\bvulnerabilities\b", "vulnerabilidades"),
    (r"\bmalicious software\b", "software malicioso"),
    (r"\bmalware\b", "software malicioso"),
    (r"\bunauthorized software\b", "software no autorizado"),
    (r"\bunauthorized access\b", "acceso no autorizado"),
    (r"\baccess control\b", "control de acceso"),
    (r"\buser account\b", "cuenta de usuario"),
    (r"\buser accounts\b", "cuentas de usuario"),
    (r"\bservice account\b", "cuenta de servicio"),
    (r"\bprivileged account\b", "cuenta privilegiada"),
    (r"\bpassword policy\b", "política de contraseñas"),
    (r"\bpassword complexity\b", "complejidad de contraseña"),
    (r"\bminimum password length\b", "longitud mínima de contraseña"),
    (r"\bpassword expiration\b", "vencimiento de contraseña"),
    (r"\bpassword age\b", "antigüedad de contraseña"),
    (r"\bauthentication failure\b", "fallo de autenticación"),
    (r"\bauthentication\b", "autenticación"),
    (r"\bauthorization\b", "autorización"),
    (r"\bmulti-factor authentication\b", "autenticación multifactor"),
    (r"\bmfa\b", "MFA"),
    (r"\baudit policy\b", "política de auditoría"),
    (r"\baudit log\b", "registro de auditoría"),
    (r"\baudit logs\b", "registros de auditoría"),
    (r"\blogging\b", "registro de eventos"),
    (r"\bsecurity event\b", "evento de seguridad"),
    (r"\bsecurity events\b", "eventos de seguridad"),
    (r"\bfailed login\b", "inicio de sesión fallido"),
    (r"\bfailed logins\b", "inicios de sesión fallidos"),
    (r"\blogin attempt\b", "intento de inicio de sesión"),
    (r"\blogin attempts\b", "intentos de inicio de sesión"),
    (r"\baccount lockout\b", "bloqueo de cuenta"),
    (r"\blocked account\b", "cuenta bloqueada"),
    (r"\bdisabled account\b", "cuenta deshabilitada"),
    (r"\binactive account\b", "cuenta inactiva"),
    (r"\bstale account\b", "cuenta sin uso reciente"),
    (r"\bgroup membership\b", "pertenencia a grupos"),
    (r"\badministrators group\b", "grupo de administradores"),
    (r"\bremote access\b", "acceso remoto"),
    (r"\bnetwork connection\b", "conexión de red"),
    (r"\bnetwork connections\b", "conexiones de red"),
    (r"\bfirewall rule\b", "regla de firewall"),
    (r"\bfirewall rules\b", "reglas de firewall"),
    (r"\binbound traffic\b", "tráfico entrante"),
    (r"\boutbound traffic\b", "tráfico saliente"),
    (r"\boperating system\b", "sistema operativo"),
    (r"\bsecurity update\b", "actualización de seguridad"),
    (r"\bsecurity updates\b", "actualizaciones de seguridad"),
    (r"\bsoftware update\b", "actualización de software"),
    (r"\bpatch management\b", "gestión de parches"),
    (r"\bconfiguration change\b", "cambio de configuración"),
    (r"\bconfiguration changes\b", "cambios de configuración"),
    (r"\bpolicy violation\b", "incumplimiento de política"),
    (r"\bpolicy violations\b", "incumplimientos de política"),
    (r"\bcompliance check\b", "verificación de cumplimiento"),
    (r"\bcompliance checks\b", "verificaciones de cumplimiento"),
    (r"\bshould be enabled\b", "debe estar habilitado"),
    (r"\bshould be disabled\b", "debe estar deshabilitado"),
    (r"\bis enabled\b", "está habilitado"),
    (r"\bis disabled\b", "está deshabilitado"),
    (r"\bnot configured\b", "no está configurado"),
    (r"\bmisconfigured\b", "configurado incorrectamente"),
    (r"\bconfiguration\b", "configuración"),
    (r"\bdetected\b", "detectado"),
    (r"\bnot detected\b", "no detectado"),
    (r"\bpassed\b", "cumple"),
    (r"\bpass\b", "cumple"),
    (r"\bfailed\b", "no cumple"),
    (r"\bfailure\b", "fallo"),
    (r"\bfail\b", "no cumple"),
    (r"\bwarning\b", "advertencia"),
    (r"\bcritical\b", "crítico"),
    (r"\bhigh\b", "alto"),
    (r"\bmedium\b", "medio"),
    (r"\blow\b", "bajo"),
    (r"\binformational\b", "informativo"),
    (r"\bensure\b", "verificar que"),
    (r"\bcheck\b", "verificación"),
    (r"\brule\b", "regla"),
    (r"\bsetting\b", "configuración"),
    (r"\bsettings\b", "configuraciones"),
)


def cont_comp_texto_probablemente_ingles(value):
    text_value = str(value or "").lower()
    words = re.findall(r"[a-záéíóúñ]+", text_value)
    if not words:
        return False

    english_words = {
        "the", "and", "or", "is", "are", "was", "were", "be", "been", "being",
        "to", "from", "for", "with", "without", "of", "on", "in", "into", "by",
        "this", "that", "these", "those", "should", "must", "ensure", "check",
        "enabled", "disabled", "failed", "passed", "detected", "account", "user",
        "password", "policy", "security", "system", "file", "rule", "access",
    }
    spanish_words = {
        "el", "la", "los", "las", "un", "una", "de", "del", "para", "por", "con",
        "sin", "que", "se", "debe", "deberá", "está", "son", "cuenta", "usuario",
        "contraseña", "política", "seguridad", "sistema", "archivo", "regla", "acceso",
    }
    en_score = sum(1 for word in words if word in english_words)
    es_score = sum(1 for word in words if word in spanish_words)
    return en_score >= 3 and en_score > es_score


def cont_comp_traducir_frases_tecnicas_es(value):
    text_value = str(value or "").strip()
    if not text_value:
        return ""
    for pattern, replacement in CONT_COMP_EVIDENCE_TRANSLATIONS:
        text_value = re.sub(pattern, replacement, text_value, flags=re.IGNORECASE)
    text_value = re.sub(r"[ \t]+", " ", text_value)
    text_value = re.sub(r"\n\s*\n+", "\n\n", text_value)
    return text_value.strip()


def cont_comp_estado_es(value):
    normalized = cont_comp_normalizar_nombre_archivo(value)
    mapping = {
        "cumple": "Cumple", "passed": "Cumple", "pass": "Cumple", "ok": "Cumple",
        "parcial": "Parcial", "partial": "Parcial", "partially": "Parcial",
        "no cumple": "No cumple", "failed": "No cumple", "fail": "No cumple",
        "no evaluado": "No evaluado", "not evaluated": "No evaluado",
        "no aplica": "No aplica", "not applicable": "No aplica", "na": "No aplica",
    }
    return mapping.get(normalized, str(value or "No evaluado").strip() or "No evaluado")


def cont_comp_severidad_es(value):
    normalized = cont_comp_normalizar_nombre_archivo(value)
    mapping = {
        "critical": "Crítica", "critica": "Crítica", "critico": "Crítica",
        "high": "Alta", "alta": "Alta", "alto": "Alta",
        "medium": "Media", "media": "Media", "medio": "Media", "moderate": "Media",
        "low": "Baja", "baja": "Baja", "bajo": "Baja",
        "informational": "Informativa", "info": "Informativa", "informativa": "Informativa",
    }
    return mapping.get(normalized, str(value or "—").strip() or "—")


CONT_COMP_GENERIC_EVIDENCE_TEXTS = {
    "resultado sca wazuh",
    "evidencia xdr",
    "evidencia automatica",
    "hallazgo automatico",
    "resultado tecnico",
    "technical evidence",
    "wazuh sca result",
    "wazuh result",
    "sin descripcion",
    "descripcion no disponible",
    "no description available",
}


def cont_comp_texto_evidencia_especifico(value, control_code="", reference=""):
    """
    Valida que un texto describa un hallazgo o una comprobación concreta.

    No se consideran evidencia los textos fabricados únicamente con el nombre
    de la fuente, el código normativo, el estado, la severidad o la referencia.
    """
    original = str(value or "").strip()
    if not original:
        return ""

    normalized = cont_comp_normalizar_nombre_archivo(original)
    code_normalized = cont_comp_normalizar_nombre_archivo(
        cont_comp_normalize_code(control_code) or control_code
    )
    reference_normalized = cont_comp_normalizar_nombre_archivo(reference)

    if normalized in CONT_COMP_GENERIC_EVIDENCE_TEXTS:
        return ""

    generic_prefixes = (
        "evidencia xdr ",
        "evidencia automatica ",
        "hallazgo automatico ",
        "resultado sca wazuh ",
        "resultado tecnico ",
        "technical evidence ",
        "wazuh sca result ",
    )
    if any(normalized.startswith(prefix) for prefix in generic_prefixes):
        return ""

    if code_normalized and normalized in {
        code_normalized,
        f"control {code_normalized}",
        f"punto {code_normalized}",
        f"hallazgo {code_normalized}",
        f"evidencia {code_normalized}",
    }:
        return ""

    if reference_normalized and normalized == reference_normalized:
        return ""

    # Debe contener una explicación legible, no solo un identificador.
    if len(original) < 8 or not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", original):
        return ""

    return original


def cont_comp_textos_desde_raw_json(raw_json):
    """Extrae textos técnicos originales útiles desde un JSON de Wazuh."""
    if not raw_json:
        return []

    try:
        payload = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
    except Exception:
        return []

    candidates = []
    preferred_keys = (
        "title", "description", "message", "reason", "rationale",
        "condition", "remediation", "recommendation", "solution",
    )

    def walk(value, depth=0):
        if depth > 4:
            return
        if isinstance(value, dict):
            # Primero los campos con mayor probabilidad de contener el hallazgo real.
            for key in preferred_keys:
                candidate = value.get(key)
                if isinstance(candidate, (str, int, float)):
                    text_candidate = str(candidate).strip()
                    if text_candidate:
                        candidates.append(text_candidate)
            for nested in value.values():
                if isinstance(nested, (dict, list)):
                    walk(nested, depth + 1)
        elif isinstance(value, list):
            for nested in value[:50]:
                walk(nested, depth + 1)

    walk(payload)

    unique = []
    seen = set()
    for candidate in candidates:
        key = candidate.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def cont_comp_seleccionar_evidencia_especifica(*values, raw_json=None,
                                                control_code="", reference=""):
    """
    Devuelve el primer texto técnico concreto disponible.

    Si no existe una descripción real del hallazgo, devuelve cadena vacía para
    que la evidencia no sea incluida ni altere el estado consolidado.
    """
    candidates = list(values)
    candidates.extend(cont_comp_textos_desde_raw_json(raw_json))

    for candidate in candidates:
        specific = cont_comp_texto_evidencia_especifico(
            candidate,
            control_code=control_code,
            reference=reference,
        )
        if specific:
            return specific
    return ""


def cont_comp_traduccion_evidencia_completa(original, translated):
    """Valida de forma conservadora que no queden fragmentos ingleses sin traducir."""
    original = str(original or "").strip()
    translated = str(translated or "").strip()
    if not translated:
        return False

    if translated == original:
        return not cont_comp_texto_probablemente_ingles(original)

    residual_english = {
        "the", "and", "or", "is", "are", "was", "were", "be", "been", "being",
        "to", "from", "for", "with", "without", "of", "on", "in", "into", "by",
        "this", "that", "these", "those", "should", "must", "ensure", "check",
        "enabled", "disabled", "failed", "passed", "detected", "account", "accounts",
        "user", "users", "password", "policy", "security", "system", "file", "files",
        "rule", "rules", "access", "root", "login", "logins", "audit", "installed",
        "configured", "permissions", "ownership", "service", "services", "package",
        "packages", "process", "processes", "network", "remote", "default", "group",
        "groups", "directory", "directories", "logs", "time", "synchronization",
        "authentication", "authorization", "monitoring", "configuration",
    }
    translated_words = set(re.findall(r"[a-z]+", translated.lower()))
    if translated_words.intersection(residual_english):
        return False

    return not cont_comp_texto_probablemente_ingles(translated)


def cont_comp_evidencia_texto_es(value, standard="", control_code="", source="",
                                  status="", severity="", reference=""):
    """
    Presenta el hallazgo sin inventar contenido.

    Si la traducción automática por glosario queda completamente en español,
    se utiliza. Cuando la traducción sería parcial o incierta, se conserva el
    texto original exactamente en su idioma de origen.
    """
    original = cont_comp_texto_evidencia_especifico(
        value,
        control_code=control_code,
        reference=reference,
    )
    if not original:
        return ""

    translated = cont_comp_traducir_frases_tecnicas_es(original)
    if cont_comp_traduccion_evidencia_completa(original, translated):
        return translated

    return original


def cont_comp_descripcion_normativa_es(value, standard="", code=""):
    """
    Presenta la descripción normativa sin fabricar traducciones.

    - Si el texto ya está en español, se conserva.
    - Si el glosario logra una traducción completa, se usa esa traducción.
    - Si la traducción es parcial o incierta, se muestra el texto original,
      incluso cuando esté en inglés.
    - Nunca se genera una frase de relleno como
      "Descripción en español del punto ...".
    """
    original = str(value or "").strip()
    code_text = cont_comp_normalize_code(code) or str(code or "").strip()

    if not original:
        return code_text

    # Limpia textos de relleno que hayan podido quedar almacenados por una
    # versión anterior. No se presentan como si fueran contenido normativo.
    if re.fullmatch(
        r"Descripción\s+en\s+español\s+del\s+punto\s+.+?\s+de\s+.+?\.?",
        original,
        flags=re.IGNORECASE,
    ):
        return code_text

    translated = cont_comp_traducir_frases_tecnicas_es(original)
    if translated and not cont_comp_texto_probablemente_ingles(translated):
        return translated

    # Regla solicitada: si no existe una traducción completa y confiable,
    # conservar exactamente la descripción original.
    return original


def cont_comp_instrument_catalog_entries(standard):
    """
    Lee directamente el instrumento cargado en los módulos de Mejora/Madurez.

    Devuelve puntos normativos exactos y sus descripciones sin depender de que
    las clases de cada instrumento tengan los mismos nombres de atributos.
    """
    standard = (standard or "").strip().upper()
    entries = []
    seen = set()

    def append_entry(code, description, name=None, parent=None):
        normalized_code = cont_comp_normalize_code(code)
        description_text = str(description or "").strip()
        name_text = str(name or "").strip()
        if (
            not normalized_code
            or not cont_comp_code_is_valid_for_standard(standard, normalized_code)
            or normalized_code in seen
        ):
            return

        description_text = cont_comp_strip_code_from_description(
            description_text or name_text or normalized_code,
            normalized_code,
        )
        seen.add(normalized_code)
        entries.append({
            "code": normalized_code,
            "name": name_text or description_text or normalized_code,
            "description": description_text or name_text or normalized_code,
            "parent": parent or cont_comp_parent_for_detail(standard, normalized_code),
            "source": "INSTRUMENTO_MEJORA",
        })

    try:
        if standard == "PCIDSS":
            preguntas = PciMadurezPregunta.query.filter_by(activo=True).order_by(
                PciMadurezPregunta.orden.asc(),
                PciMadurezPregunta.id.asc(),
            ).all()

            for p in preguntas:
                question = cont_comp_first_text_attr(p, "pregunta")
                section_name = cont_comp_first_text_attr(p, "seccion_nombre")
                block_name = cont_comp_first_text_attr(p, "bloque_nombre")

                direct_pairs = [
                    (cont_comp_first_text_attr(p, "pregunta_codigo"), question, section_name or block_name),
                    (cont_comp_first_text_attr(p, "seccion_codigo"), section_name or question, block_name),
                ]
                for code, description, name in direct_pairs:
                    append_entry(code, description, name)

                for source_text in (question, section_name, block_name):
                    for code in cont_comp_extract_codes_from_instrument_text(standard, source_text):
                        append_entry(code, question or section_name or block_name, section_name or block_name)

        elif standard == "SOC2":
            preguntas = Soc2MadurezPregunta.query.filter_by(activo=True).order_by(
                Soc2MadurezPregunta.orden.asc(),
                Soc2MadurezPregunta.id.asc(),
            ).all()

            for p in preguntas:
                question = cont_comp_first_text_attr(p, "pregunta")
                section_name = cont_comp_first_text_attr(p, "seccion_nombre")
                block_name = cont_comp_first_text_attr(p, "bloque_nombre")

                # Solo se admiten códigos SOC 2 reales. Se ignoran identificadores
                # internos como SEG-001 creados por algunas versiones del importador.
                for code_value, description, name in [
                    (cont_comp_first_text_attr(p, "pregunta_codigo"), question, section_name or block_name),
                    (cont_comp_first_text_attr(p, "seccion_codigo"), section_name or question, block_name),
                    (cont_comp_first_text_attr(p, "bloque_codigo"), block_name or question, block_name),
                ]:
                    append_entry(code_value, description, name)

                # Muchos instrumentos traen el código (por ejemplo CC6.8) dentro
                # de la propia pregunta, aunque no exista una columna separada.
                for source_text in (question, section_name, block_name):
                    for code in cont_comp_extract_codes_from_instrument_text(standard, source_text):
                        append_entry(code, question or section_name or block_name, section_name or block_name)

        elif standard == "NISTCSF":
            preguntas = NistMadurezPregunta.query.filter_by(activo=True).order_by(
                NistMadurezPregunta.orden.asc(),
                NistMadurezPregunta.id.asc(),
            ).all()

            for p in preguntas:
                # NistMadurezPregunta utiliza pregunta_es / pregunta_en.
                # No se accede a p.pregunta, porque ese atributo no existe.
                question = cont_comp_first_text_attr(p, "pregunta_es", "pregunta_en")
                category_name = cont_comp_first_text_attr(p, "categoria")
                function_name = cont_comp_first_text_attr(p, "funcion")
                category_code = cont_comp_first_text_attr(p, "categoria_codigo")
                function_code = cont_comp_first_text_attr(p, "funcion_codigo")

                append_entry(
                    category_code,
                    category_name or question,
                    category_name or function_name,
                    function_code or None,
                )

                for source_text in (question, category_name):
                    for code in cont_comp_extract_codes_from_instrument_text(standard, source_text):
                        append_entry(
                            code,
                            question or category_name or function_name,
                            category_name or function_name,
                            category_code or None,
                        )

        elif standard == "ISO27001":
            preguntas = MadurezPregunta.query.order_by(
                MadurezPregunta.sheet.asc(),
                MadurezPregunta.orden.asc(),
                MadurezPregunta.id.asc(),
            ).all()

            # Los encabezados del instrumento contienen el título del control.
            # Las preguntas (¿...?) son criterios de evaluación y no deben
            # mostrarse como descripción normativa.
            annex_headers = {}
            clause_headers = {}
            for p in preguntas:
                tipo = cont_comp_first_text_attr(p, "tipo")
                if tipo not in ("", "h"):
                    continue
                sheet = cont_comp_first_text_attr(p, "sheet").upper()
                header_text = cont_comp_first_text_attr(p, "control_desc", "tema", "pregunta", "seccion")
                control = cont_comp_first_text_attr(p, "control")
                section = cont_comp_first_text_attr(p, "seccion")

                if sheet == "ANEXO A" and control:
                    code = control if control.upper().startswith("A.") else f"A.{control}"
                    cleaned = cont_comp_strip_code_from_description(header_text, code.replace("A.", ""))
                    if cleaned:
                        annex_headers[cont_comp_normalize_code(code)] = cleaned
                else:
                    for code in cont_comp_extract_codes_from_instrument_text(
                        standard,
                        " ".join([section, header_text]),
                    ):
                        clause_headers[code] = cont_comp_strip_code_from_description(header_text, code)

            for p in preguntas:
                tipo = cont_comp_first_text_attr(p, "tipo")
                sheet = cont_comp_first_text_attr(p, "sheet").upper()
                control_description = cont_comp_first_text_attr(p, "control_desc")
                topic = cont_comp_first_text_attr(p, "tema")
                section = cont_comp_first_text_attr(p, "seccion")
                control = cont_comp_first_text_attr(p, "control")

                if sheet == "ANEXO A" and control:
                    code = control if control.upper().startswith("A.") else f"A.{control}"
                    normalized_code = cont_comp_normalize_code(code)
                    normative_text = control_description or topic or annex_headers.get(normalized_code)
                    if normative_text:
                        append_entry(code, normative_text, topic or annex_headers.get(normalized_code))
                    continue

                # Para capítulos 4–10 se utiliza el encabezado/sección del
                # requisito; nunca la pregunta de evaluación como descripción.
                if tipo not in ("", "q", "h"):
                    continue
                for code in cont_comp_extract_codes_from_instrument_text(standard, section):
                    normative_text = clause_headers.get(code) or section
                    if normative_text:
                        append_entry(code, normative_text, normative_text)

    except Exception as exc:
        # Una inconsistencia de un instrumento no debe volver a tumbar el
        # dashboard completo de Cumplimiento Continuo.
        print(
            f"No se pudo leer completamente el instrumento {standard} "
            f"para Cumplimiento Continuo: {repr(exc)}"
        )

    # Los suplementos solo se usan cuando el instrumento cargado y el catálogo
    # estático no entregan el punto. No reemplazan información del instrumento.
    for code, description in CONT_COMP_SUPPLEMENTAL_STANDARD_DESCRIPTIONS.get(standard, {}).items():
        append_entry(code, description, description)

    return entries


def cont_comp_lookup_instrument_point(standard, code):
    """Busca un punto específico cada vez que una evidencia lo requiera."""
    normalized_code = cont_comp_normalize_code(code)
    for entry in cont_comp_instrument_catalog_entries(standard):
        if entry.get("code") == normalized_code:
            return entry
    return None


def cont_comp_build_standard_catalog(standard):
    """
    Construye el catálogo normativo utilizado por las matrices de
    Cumplimiento Continuo.

    La columna ``description`` contiene exclusivamente el texto del punto
    del estándar. Los hallazgos y las evidencias se conservan separados y
    únicamente se muestran en la vista «Ver evidencia».
    """
    standard = (standard or "").strip().upper()
    rows = {}

    def clean_text(value):
        return str(value or "").strip()

    def short_title(description, fallback):
        text_lines = [
            line.strip()
            for line in clean_text(description).splitlines()
            if line.strip()
        ]
        if not text_lines:
            return fallback

        if standard == "ISO27001" and len(text_lines) >= 2:
            return text_lines[1][:500]

        first = text_lines[0]
        return (first[:497] + "...") if len(first) > 500 else (first or fallback)

    def add(code, name=None, parent=None, description=None, normative=False, source=None):
        code = cont_comp_normalize_code(code)
        if not code:
            return

        name_text = clean_text(name) or code
        description_text = clean_text(description) or name_text
        source_text = source or ("CATALOGO_NORMATIVO" if normative else "INSTRUMENTO_MEJORA")

        if code not in rows:
            rows[code] = {
                "detail_code": code,
                "parent_code": parent or cont_comp_parent_for_detail(standard, code),
                "name": name_text,
                "description": description_text,
                "description_source": source_text,
            }
            return

        current = rows[code]

        # Los catálogos oficiales incorporados mantienen prioridad. El
        # instrumento completa únicamente puntos ausentes.
        if normative and description_text:
            current["description"] = description_text
            current["description_source"] = source_text

        if (
            name_text
            and (
                not current.get("name")
                or current.get("name") == code
                or current.get("name") == current.get("description")
            )
        ):
            current["name"] = name_text

        if parent and not current.get("parent_code"):
            current["parent_code"] = parent

    # 1. Catálogos normativos.
    if standard == "ISO27001":
        # La matriz del Anexo A se construye EXCLUSIVAMENTE con los 93
        # controles ISO/IEC 27002:2022 del Excel oficial. No se agregan
        # controles heredados de 2013 ni códigos encontrados solo en evidencias.
        for entry in cont_comp_iso27002_official_catalog().values():
            add(
                entry.get("code"),
                entry.get("name"),
                parent=entry.get("parent"),
                description=entry.get("description"),
                normative=True,
                source=entry.get("source") or "ANEXO_A_27002_XLSX",
            )

    elif standard == "PCIDSS":
        for code, normative_description in PCI_DSS_CONTROLES:
            add(
                code,
                short_title(normative_description, code),
                description=normative_description,
                normative=True,
            )

    elif standard == "NISTCSF":
        # La matriz se construye EXCLUSIVAMENTE con las 106 subcategorías
        # presentes en static/templates/NIST.CSF 2.0.docx.
        for entry in cont_comp_nist_csf_official_catalog().values():
            add(
                entry.get("code"),
                entry.get("name"),
                parent=entry.get("parent"),
                description=entry.get("description"),
                normative=True,
                source=entry.get("source") or "NIST_CSF_20_DOCX",
            )

    elif standard == "SOC2":
        for code, normative_description in SOC2_CONTROLES:
            add(
                code,
                short_title(normative_description, code),
                description=normative_description,
                normative=True,
            )

    # 2. Complemento dinámico desde el instrumento realmente cargado en
    #    Mejora/Madurez. Esto agrega, por ejemplo, CC6.8 cuando no figura
    #    en una versión antigua de la lista estática.
    if standard != "NISTCSF":
        for entry in cont_comp_instrument_catalog_entries(standard):
            entry_code = cont_comp_normalize_code(entry.get("code"))
            if standard == "ISO27001" and entry_code.startswith("A."):
                entry_code = cont_comp_iso27002_resolve_code(entry_code)
                if not entry_code:
                    continue
            add(
                entry_code,
                entry.get("name"),
                parent=entry.get("parent"),
                description=entry.get("description"),
                normative=False,
                source=entry.get("source") or "INSTRUMENTO_MEJORA",
            )

    for code, item in rows.items():
        item["description"] = cont_comp_descripcion_normativa_es(
            item.get("description"), standard=standard, code=code
        )
        item["name"] = cont_comp_descripcion_normativa_es(
            item.get("name") or item.get("description"), standard=standard, code=code
        )

    return rows


def cont_comp_sync_fim_and_mitre_from_alerts():
    fim_count = 0
    mitre_count = 0
    alerts = WazuhAlert.query.order_by(WazuhAlert.id.desc()).limit(500).all()

    for a in alerts:
        raw = {}
        try:
            raw = json.loads(a.raw_json or "{}")
        except Exception:
            raw = {}

        syscheck = raw.get("syscheck") or raw.get("data", {}).get("syscheck")
        if syscheck:
            path = syscheck.get("path") or syscheck.get("file")
            action = syscheck.get("event") or syscheck.get("action")
            unique = f"{a.alert_id}:fim:{path}:{action}"
            row = WazuhFimEvent.query.filter_by(unique_key=unique).first() or WazuhFimEvent(unique_key=unique)
            row.timestamp = a.timestamp
            row.agent_id = a.agent_id
            row.agent_name = a.agent_name
            row.file_path = path
            row.action = action
            row.severity = a.severity
            row.raw_json = a.raw_json
            row.synced_at = cont_comp_now()
            db.session.add(row)
            fim_count += 1

        try:
            mitre_ids = json.loads(a.mitre_ids or "[]")
        except Exception:
            mitre_ids = []
        if mitre_ids:
            if isinstance(mitre_ids, dict):
                techniques = mitre_ids.get("id") or []
                tactics = mitre_ids.get("tactic") or []
            else:
                techniques = mitre_ids
                tactics = []

            if not isinstance(techniques, list):
                techniques = [techniques]

            for tid in techniques:
                unique = f"{a.alert_id}:mitre:{tid}"
                row = WazuhMitreEvent.query.filter_by(unique_key=unique).first() or WazuhMitreEvent(unique_key=unique)
                row.timestamp = a.timestamp
                row.agent_id = a.agent_id
                row.agent_name = a.agent_name
                row.tactic = ", ".join(tactics) if isinstance(tactics, list) else str(tactics or "")
                row.technique_id = str(tid)
                row.technique = str(tid)
                row.rule_level = a.rule_level
                row.description = a.rule_description
                row.raw_json = a.raw_json
                row.synced_at = cont_comp_now()
                db.session.add(row)
                mitre_count += 1

    db.session.commit()
    return fim_count, mitre_count


def cont_comp_full_sync():
    cfg = cont_comp_get_config()
    log = ContinuousComplianceSyncLog(status="En proceso", message="Sincronización iniciada.")
    db.session.add(log)
    db.session.commit()

    try:
        agents = cont_comp_sync_agents(cfg)
        vulns = cont_comp_sync_vulnerabilities(cfg)
        alerts = cont_comp_sync_alerts(cfg)
        sca = cont_comp_sync_sca(cfg)
        fim, mitre = cont_comp_sync_fim_and_mitre_from_alerts()

        cont_comp_apply_control_evaluation()
        cont_comp_generate_evidences_and_actions()

        log.status = "Exitoso"
        log.message = "Sincronización finalizada correctamente."
        log.finished_at = cont_comp_now()
        log.agents_count = agents
        log.vulnerabilities_count = vulns
        log.alerts_count = alerts
        log.sca_count = sca
        log.fim_count = fim
        log.mitre_count = mitre
        db.session.commit()

        try:
            registrar_log(session.get("username", "Sistema"), "Sincronización de Cumplimiento Continuo ejecutada.")
        except Exception:
            pass

        return log
    except Exception as e:
        traceback.print_exc()
        log.status = "Error"
        log.message = str(e)
        log.finished_at = cont_comp_now()
        db.session.commit()
        raise


# ============================================================
# HELPERS - EVIDENCIA MANUAL + AUTOMÁTICA
# ============================================================

def cont_comp_upload_folder():
    folder = os.path.join(app.root_path, "static", "uploads", "cumplimiento_continuo")
    os.makedirs(folder, exist_ok=True)
    return folder


def cont_comp_public_file_path(filename):
    if not filename:
        return None
    return f"uploads/cumplimiento_continuo/{filename}"


def cont_comp_manual_status_from_evidences(manual_evidences):
    approved = [
        e for e in manual_evidences
        if (e.approval_status or "").strip() == "Aprobado"
    ]

    pending = [
        e for e in manual_evidences
        if (e.approval_status or "").strip() == "Pendiente"
    ]

    rejected = [
        e for e in manual_evidences
        if (e.approval_status or "").strip() == "Rechazado"
    ]

    if approved:
        latest = sorted(
            approved,
            key=lambda x: x.reviewed_at or x.uploaded_at or datetime.min,
            reverse=True
        )[0]

        status = latest.proposed_status or "No evaluado"

        score_map = {
            "Cumple": 100,
            "Parcial": 60,
            "No cumple": 0,
            "No aplica": None,
            "No evaluado": 0,
        }

        score = score_map.get(status, 0)

        return {
            "has_manual": True,
            "status": status,
            "score": score,
            "summary": f"Evidencia manual aprobada por auditor. {latest.title}",
            "source": "Manual aprobada",
            "count": len(approved),
            "last_date": latest.reviewed_at or latest.uploaded_at,
        }

    if pending:
        latest = sorted(
            pending,
            key=lambda x: x.uploaded_at or datetime.min,
            reverse=True
        )[0]

        return {
            "has_manual": True,
            "status": "No evaluado",
            "score": 0,
            "summary": f"Evidencia manual cargada pendiente de aprobación. {latest.title}",
            "source": "Manual pendiente",
            "count": len(pending),
            "last_date": latest.uploaded_at,
        }

    if rejected:
        latest = sorted(
            rejected,
            key=lambda x: x.reviewed_at or x.uploaded_at or datetime.min,
            reverse=True
        )[0]

        return {
            "has_manual": True,
            "status": "No evaluado",
            "score": 0,
            "summary": f"Evidencia manual rechazada. {latest.review_comment or latest.title}",
            "source": "Manual rechazada",
            "count": len(rejected),
            "last_date": latest.reviewed_at or latest.uploaded_at,
        }

    return {
        "has_manual": False,
        "status": "No evaluado",
        "score": 0,
        "summary": "No hay evidencia manual cargada para este punto.",
        "source": "Sin evidencia manual",
        "count": 0,
        "last_date": None,
    }


def cont_comp_final_status_hybrid(wazuh_evidences, manual_evidences):
    wazuh_status, wazuh_score, wazuh_summary = cont_comp_final_status_from_evidences(wazuh_evidences)
    manual = cont_comp_manual_status_from_evidences(manual_evidences)

    dates = [e.synced_at for e in wazuh_evidences if e.synced_at]
    if manual.get("last_date"):
        dates.append(manual["last_date"])

    last_date = max(dates, default=None)

    if wazuh_status in ("No cumple", "Parcial", "Cumple"):
        return {
            "status": wazuh_status,
            "score": wazuh_score,
            "summary": wazuh_summary,
            "source_type": "Herramienta XDR (Wazuh)",
            "evidence_count": len(wazuh_evidences) + manual["count"],
            "last_evaluated_at": last_date,
            "evaluation_type": "AUTOMATIC" if wazuh_status in ("No cumple", "Cumple") else "HYBRID",
        }

    if wazuh_status == "No aplica":
        return {
            "status": "No aplica",
            "score": None,
            "summary": wazuh_summary,
            "source_type": "Excluido",
            "evidence_count": len(wazuh_evidences),
            "last_evaluated_at": last_date,
            "evaluation_type": "EXCLUDED",
        }

    if manual["has_manual"]:
        return {
            "status": manual["status"],
            "score": manual["score"],
            "summary": manual["summary"],
            "source_type": manual["source"],
            "evidence_count": manual["count"],
            "last_evaluated_at": manual["last_date"],
            "evaluation_type": "MANUAL",
        }

    return {
        "status": "No evaluado",
        "score": 0,
        "summary": "Pendiente de evidencia automática o documental.",
        "source_type": "Pendiente evidencia",
        "evidence_count": 0,
        "last_evaluated_at": None,
        "evaluation_type": "PENDING",
    }


# ============================================================
# UI BASE DEL MÓDULO
# ============================================================

CONT_COMP_CSS = """
<style>
  body{
    background-image:url('/static/img/ccsgsi.jpg');
    background-size:cover;
    background-position:center;
    background-attachment:fixed;
    background-repeat:no-repeat;
  }

  .cc-shell{
    width:96%;
    max-width:1650px;
    margin:10px auto 24px auto;
  }

  .cc-hero{
    background:linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
    border-radius:18px;
    padding:16px 24px;
    min-height:94px;
    display:flex;
    align-items:center;
    justify-content:flex-start;
    box-shadow:0 12px 24px rgba(15,23,42,.24);
    color:#ffffff;
    position:relative;
    overflow:hidden;
    margin-bottom:18px;
  }

  .cc-hero::before{
    content:"";
    position:absolute;
    inset:0;
    background:
      radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
      repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 15px);
    pointer-events:none;
  }

  .cc-hero::after{
    content:"🛡️";
    width:54px;
    height:54px;
    min-width:54px;
    border-radius:14px;
    background:rgba(255,255,255,.96);
    color:#0b4a8f;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:1.55rem;
    box-shadow:0 8px 18px rgba(0,0,0,.20);
    margin-right:14px;
    position:relative;
    z-index:1;
    order:-1;
  }

  .cc-hero h2{
    color:#ffffff !important;
    font-weight:950;
    font-size:1.36rem;
    line-height:1.08;
    margin:0;
    position:relative;
    z-index:1;
  }

  .cc-hero p{
    margin:5px 0 0 0;
    color:rgba(255,255,255,.90);
    font-size:.82rem;
    font-weight:600;
    position:relative;
    z-index:1;
  }

  .cc-hero .cc-hero-text::before{
    content:"SGSI · Cumplimiento Continuo";
    display:inline-block;
    background:rgba(255,255,255,.18);
    border:1px solid rgba(255,255,255,.30);
    border-radius:999px;
    padding:3px 10px;
    font-size:.66rem;
    font-weight:800;
    letter-spacing:.35px;
    margin-bottom:4px;
  }

  .cc-nav,
  div.cc-nav,
  .cc-shell > .cc-nav{
    display:none !important;
    visibility:hidden !important;
    height:0 !important;
    min-height:0 !important;
    max-height:0 !important;
    padding:0 !important;
    margin:0 !important;
    border:0 !important;
    overflow:hidden !important;
  }

  .cc-card{
    background:rgba(255,255,255,.97);
    border:1px solid rgba(219,230,244,.98);
    border-radius:18px;
    box-shadow:0 12px 26px rgba(15,23,42,.16);
    padding:16px;
    margin-bottom:14px;
    overflow:hidden;
  }

  .cc-section-title{
    color:#062b55;
    font-weight:950;
    font-size:1.02rem;
    margin:0 0 10px 0;
  }

  .cc-muted{
    color:#475569;
    font-size:.84rem;
    font-weight:600;
  }

  .cc-kpi{
    min-height:98px;
    padding:14px 12px;
    display:flex;
    align-items:center;
    gap:10px;
    background:rgba(255,255,255,.96);
    border:1px solid rgba(219,230,244,.95);
    border-radius:18px;
    box-shadow:0 10px 22px rgba(15,23,42,.14);
  }

  .cc-kpi .icon{
    width:46px;
    height:46px;
    min-width:46px;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
    background:linear-gradient(135deg,#0b4a8f,#1d5fae);
    color:#ffffff;
    font-size:1.22rem;
  }

  .cc-kpi .num{
    font-size:1.55rem;
    font-weight:950;
    color:#0b4a8f;
    line-height:1;
  }

  .cc-kpi .lbl{
    margin-top:4px;
    font-size:.68rem;
    color:#475569;
    font-weight:850;
    line-height:1.15;
  }

  .cc-table{
    background:#ffffff;
    border-collapse:separate !important;
    border-spacing:0;
    border:1px solid #d8e3f3;
    border-radius:14px;
    overflow:hidden;
    font-size:.82rem;
  }

  .cc-table thead th{
    background:linear-gradient(180deg,#eaf3ff 0%,#dcecff 100%) !important;
    color:#062b55 !important;
    font-weight:950 !important;
    text-align:center;
    vertical-align:middle;
    border-color:#c9daef !important;
    padding:8px 7px;
    white-space:nowrap;
  }

  .cc-table tbody td{
    vertical-align:middle;
    border-color:#e3edf8 !important;
    padding:6px 7px;
    color:#334155;
  }

  .cc-standard-matrix{
    width:100%;
    min-width:1480px;
    table-layout:fixed;
  }

  .cc-standard-matrix .cc-col-point{ width:9%; }
  .cc-standard-matrix .cc-col-description{ width:35%; }
  .cc-standard-matrix .cc-col-status{ width:8%; }
  .cc-standard-matrix .cc-col-analysis{ width:17%; }
  .cc-standard-matrix .cc-col-evidence{ width:5%; }
  .cc-standard-matrix .cc-col-source{ width:11%; }
  .cc-standard-matrix .cc-col-date{ width:8%; }
  .cc-standard-matrix .cc-col-action{ width:7%; }

  .cc-standard-matrix tbody td:nth-child(2),
  .cc-standard-matrix thead th:nth-child(2){
    min-width:430px;
    white-space:normal !important;
  }

  .cc-norm-description{
    white-space:pre-line;
    line-height:1.45;
    text-align:left;
    overflow-wrap:anywhere;
    word-break:normal;
    color:#26384d;
  }

  .cc-pill{
    display:inline-flex;
    align-items:center;
    justify-content:center;
    padding:5px 10px;
    border-radius:999px;
    font-size:.72rem;
    font-weight:900;
    background:#eaf3ff;
    color:#0b4a8f;
    border:1px solid #cbdff7;
  }

  .cc-form label{
    font-weight:900;
    color:#334155;
    font-size:.82rem;
    margin-bottom:4px;
  }

  .cc-form .form-control,
  .cc-card .form-control,
  .cc-card .form-select{
    border-radius:12px;
    border:1px solid #cbd8ea;
    font-size:.86rem;
    padding:9px 11px;
  }

  .cc-card .btn{
    border-radius:999px !important;
    font-weight:850 !important;
    padding-left:16px !important;
    padding-right:16px !important;
  }

  .badge{
    border-radius:999px;
    padding:6px 10px;
    font-weight:850;
  }

  .cc-empty{
    text-align:center;
    color:#475569;
    padding:34px 12px;
    font-weight:750;
  }
</style>
"""


def cont_comp_nav(active="dashboard"):
    return Markup("")


def cont_comp_render(
    content,
    active="dashboard",
    title="Cumplimiento Continuo",
    subtitle="Monitoreo continuo de controles con Wazuh."
):
    shell = f"""
    {CONT_COMP_CSS}

    <script>
      function removeCumplimientoTopNav() {{
        document.querySelectorAll(".cc-nav").forEach(function(el) {{
          el.remove();
        }});

        document.querySelectorAll(".cc-shell a[href*='/cumplimiento_continuo']").forEach(function(link) {{
          // Mantener visible la navegación interna de Gobierno de Firewall.
          // El limpiador global solo debe retirar la navegación superior antigua.
          if (link.closest("[data-keep-cumplimiento-nav='true']")) {{
            return;
          }}

          let box = link.closest("div");

          while (box && box.classList && !box.classList.contains("cc-shell")) {{
            let links = box.querySelectorAll("a[href*='/cumplimiento_continuo']").length;
            let tables = box.querySelectorAll("table").length;
            let forms = box.querySelectorAll("form").length;

            if (links >= 5 && tables === 0 && forms === 0) {{
              box.remove();
              return;
            }}

            box = box.parentElement;
          }}
        }});
      }}

      document.addEventListener("DOMContentLoaded", removeCumplimientoTopNav);
      setTimeout(removeCumplimientoTopNav, 300);
      setTimeout(removeCumplimientoTopNav, 1000);
    </script>

    <div class="cc-shell">
      <div class="cc-hero">
        <div class="cc-hero-text">
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>

      {content}
    </div>
    """

    return render_template_string(
        BASE,
        content=Markup(shell)
    )

# ============================================================
# ANÁLISIS WAZUH -> ESTÁNDARES
# ============================================================

def cont_comp_normalize_code(code):
    code = (code or "").strip().upper()
    code = code.replace("PCI_DSS", "")
    code = code.replace("PCI-DSS", "")
    code = code.replace("REQ.", "REQ-")
    code = code.replace("REQ ", "REQ-")
    code = code.replace("REQUERIMIENTO ", "REQ-")
    code = code.replace("REQUIREMENT ", "REQ-")
    code = code.strip(" :-")
    return code


def cont_comp_split_control_codes(value):
    if not value:
        return []

    if isinstance(value, list):
        raw = value
    elif isinstance(value, tuple):
        raw = list(value)
    else:
        raw = str(value).replace(";", ",").split(",")

    codes = []

    for item in raw:
        text = str(item).strip()

        if not text:
            continue

        text = text.replace("[", "").replace("]", "")
        text = text.replace("'", "").replace('"', "")

        if "," in text:
            for sub in text.split(","):
                sub = cont_comp_normalize_code(sub)
                if sub:
                    codes.append(sub)
        else:
            text = cont_comp_normalize_code(text)
            if text:
                codes.append(text)

    clean = []
    seen = set()

    for c in codes:
        if c and c not in seen:
            clean.append(c)
            seen.add(c)

    return clean

def cont_comp_parent_for_detail(standard, detail_code):
    standard = (standard or "").strip().upper()
    code = cont_comp_normalize_code(detail_code)

    if not code:
        return ""

    if standard == "PCIDSS":
        m = re.match(r"^(\d+)(?:\.|$)", code)
        if m:
            return f"REQ-{m.group(1)}"
        return code

    if standard == "SOC2":
        m = re.match(r"^(CC\d+)", code)
        if m:
            return m.group(1)
        return code

    if standard == "NISTCSF":
        m = re.match(r"^([A-Z]{2}\.[A-Z]{2})", code)
        if m:
            return m.group(1)
        return code

    if standard == "ISO27001":
        if code.startswith("A."):
            return code
        return code

    return code

def cont_comp_source_status(source_type, result=None, level=0, severity=None):
    source_type = (source_type or "").lower()
    result = (result or "").strip().lower()
    severity = (severity or "").strip().lower()
    level = int(level or 0)

    if source_type == "sca":
        if result in ("failed", "fail", "failure"):
            return "No cumple", 0, "Alta"

        if result in ("passed", "pass", "success", "ok"):
            return "Cumple", 100, "Baja"

        if result in ("not applicable", "not_applicable", "n/a", "na", "not applicable."):
            return "No aplica", None, "N/A"

        if result in ("not run", "not_run", "unknown", "none", "", "pending"):
            return "No evaluado", 0, "N/A"

        return "No evaluado", 0, "N/A"

    if source_type == "vulnerability":
        if severity in ("critical", "crítica", "critica", "high", "alta", "alto"):
            return "No cumple", 0, "Alta"

        if severity in ("medium", "media", "medio"):
            return "Parcial", 60, "Media"

        if severity in ("low", "baja", "bajo"):
            return "Parcial", 80, "Baja"

        return "No evaluado", 0, "N/A"

    if source_type == "alert":
        if level >= 12:
            return "No cumple", 0, "Crítica"

        if level >= 7:
            return "Parcial", 60, "Alta"

        if level >= 3:
            return "Parcial", 80, "Media"

        return "Cumple", 100, "Baja"

    if source_type == "fim":
        if level >= 12:
            return "No cumple", 0, "Crítica"

        if level >= 7:
            return "Parcial", 60, "Alta"

        return "Parcial", 75, "Media"

    if source_type == "mitre":
        if level >= 12:
            return "No cumple", 0, "Crítica"

        if level >= 7:
            return "Parcial", 60, "Alta"

        return "Parcial", 75, "Media"

    return "No evaluado", 0, "N/A"


def cont_comp_final_status_from_evidences(evidences):
    """
    Consolida las evidencias automáticas de un punto normativo.

    Reglas:
    - Todas Cumple       -> Cumple.
    - Todas No cumple    -> No cumple.
    - Todas Parcial      -> Parcial.
    - Cualquier mezcla entre Cumple, Parcial y No cumple -> Parcial.

    «No aplica» se excluye y «No evaluado» no altera el estado operativo.
    """
    def value(item, field, default=None):
        if isinstance(item, dict):
            return item.get(field, default)
        return getattr(item, field, default)

    if not evidences:
        return (
            "No monitoreado",
            0,
            "No existe evidencia automática desde la herramienta XDR, Gobierno de Firewall "
            "o Gobierno del Directorio Activo para este punto.",
        )

    visibles = [
        evidence
        for evidence in evidences
        if str(value(evidence, "status") or "").strip() != "No aplica"
    ]

    if not visibles:
        return (
            "No aplica",
            None,
            "Punto excluido por la evaluación técnica o por la gestión del hallazgo.",
        )

    valid_statuses = {"Cumple", "Parcial", "No cumple"}
    operational = [
        evidence
        for evidence in visibles
        if str(value(evidence, "status") or "").strip() in valid_statuses
    ]

    if not operational:
        return (
            "No monitoreado",
            0,
            "Las evidencias disponibles todavía no entregan un resultado operativo "
            "Cumple, Parcial o No cumple para este punto.",
        )

    counts = {
        status: sum(
            1
            for evidence in operational
            if str(value(evidence, "status") or "").strip() == status
        )
        for status in ("Cumple", "Parcial", "No cumple")
    }

    sources = sorted({
        str(value(evidence, "source") or "Fuente automática").strip()
        for evidence in operational
        if str(value(evidence, "source") or "").strip()
    })
    source_text = ", ".join(sources) if sources else "fuentes automáticas"
    present = {status for status, count in counts.items() if count > 0}
    total = len(operational)

    if present == {"Cumple"}:
        return (
            "Cumple",
            100,
            f"Todas las {total} evidencia(s) soportan el cumplimiento. "
            f"Origen: {source_text}.",
        )

    if present == {"No cumple"}:
        return (
            "No cumple",
            0,
            f"Todas las {total} evidencia(s) concluyen No cumple. "
            f"Origen: {source_text}.",
        )

    if present == {"Parcial"}:
        return (
            "Parcial",
            60,
            f"Todas las {total} evidencia(s) presentan cumplimiento parcial. "
            f"Origen: {source_text}.",
        )

    # Mezcla de resultados: no se permite que una sola evidencia No cumple
    # convierta todo el punto en No cumple. El resultado consolidado es Parcial.
    return (
        "Parcial",
        60,
        "Estado parcial por combinación de resultados: "
        f"{counts['Cumple']} Cumple, {counts['Parcial']} Parcial y "
        f"{counts['No cumple']} No cumple. Origen: {source_text}.",
    )


def cont_comp_get_control_eval_map(standard):
    """
    Devuelve mapas para buscar evaluación por control.
    """
    standard = (standard or "").strip().upper()

    controls = ContinuousControl.query.filter_by(standard=standard).all()

    exact = {}
    normalized = {}

    for c in controls:
        code = cont_comp_normalize_code(c.control_code)
        exact[c.control_code] = c
        normalized[code] = c

    return exact, normalized


def cont_comp_control_to_detail_status(control_obj):
    if not control_obj:
        return {
            "status": "No evaluado",
            "score": 0,
            "source_type": "-",
            "summary": "No existe mapeo automático desde la herramienta XDR, Gobierno de Firewall o Gobierno del Directorio Activo para este punto específico.",
            "evidence_count": 0,
            "last_evaluated_at": None,
        }

    return {
        "status": control_obj.status or "No evaluado",
        "score": float(control_obj.score or 0),
        "source_type": control_obj.source_type or "-",
        "summary": control_obj.evidence_summary or "Sin resumen de evidencia.",
        "evidence_count": int(control_obj.evidence_count or 0),
        "last_evaluated_at": control_obj.last_evaluated_at,
    }


def cont_comp_build_standard_detail_rows(standard):
    """Construye la matriz por estándar usando XDR, Firewall y Active Directory."""
    standard = (standard or "").strip().upper()
    catalog = cont_comp_build_standard_catalog(standard)

    evidence_by_code = {}

    xdr_evidences = WazuhComplianceControl.query.filter_by(
        standard=standard
    ).order_by(
        WazuhComplianceControl.synced_at.desc()
    ).all()

    for e in xdr_evidences:
        code = cont_comp_resolve_evidence_code(standard, e.control_code, catalog)
        if not code:
            continue

        reference = e.rule_id or e.alert_id
        evidence_original = cont_comp_seleccionar_evidencia_especifica(
            e.rule_description,
            raw_json=e.raw_json,
            control_code=code,
            reference=reference,
        )
        if not evidence_original:
            # Sin descripción técnica concreta no se publica ni se contabiliza.
            continue

        evidence_visible = cont_comp_evidencia_texto_es(
            evidence_original,
            standard=standard,
            control_code=code,
            source="Herramienta XDR (Wazuh)",
            status=e.status,
            severity=e.severity,
            reference=reference,
        )
        if not evidence_visible:
            continue

        record = {
            "status": cont_comp_estado_es(e.status),
            "source": "Herramienta XDR (Wazuh)",
            "source_type": "SCA" if (e.rule_id or "").startswith("SCA-") else "Alerta / telemetría",
            "title": evidence_visible,
            "reference": reference or "—",
            "severity": cont_comp_severidad_es(e.severity),
            "date": e.synced_at,
            "control_name": e.control_name,
        }
        evidence_by_code.setdefault(code, []).append(record)

        if code not in catalog:
            if standard in ("ISO27001", "NISTCSF"):
                continue
            instrument_point = cont_comp_lookup_instrument_point(standard, code)
            catalog[code] = {
                "detail_code": code,
                "parent_code": (
                    (instrument_point or {}).get("parent")
                    or cont_comp_parent_for_detail(standard, code)
                ),
                "name": cont_comp_descripcion_normativa_es(
                    (instrument_point or {}).get("name")
                    or (
                        e.control_name
                        if (e.control_name or "").strip()
                        and cont_comp_normalize_code(e.control_name) != code
                        else code
                    ),
                    standard=standard, code=code,
                ),
                "description": cont_comp_descripcion_normativa_es(
                    (instrument_point or {}).get("description")
                    or (
                        e.control_name
                        if (e.control_name or "").strip()
                        and cont_comp_normalize_code(e.control_name) != code
                        else evidence_original
                    )
                    or code,
                    standard=standard, code=code,
                ),
                "description_source": (
                    (instrument_point or {}).get("source")
                    or "REFERENCIA_CONTROL"
                ),
            }

    governance_evidences = ContinuousEvidence.query.filter_by(
        standard=standard
    ).filter(
        ContinuousEvidence.source.in_([
            "Gobierno de Firewall",
            "Gobierno del Directorio Activo",
        ])
    ).order_by(ContinuousEvidence.evidence_date.desc()).all()

    for e in governance_evidences:
        code = cont_comp_resolve_evidence_code(standard, e.control_code, catalog)
        if not code:
            continue

        raw = {}
        if e.raw_json:
            try:
                raw = json.loads(e.raw_json) or {}
            except Exception:
                raw = {}

        reference = raw.get("finding_code") or e.event_ref
        evidence_original = cont_comp_seleccionar_evidencia_especifica(
            raw.get("finding_title"),
            e.description,
            raw.get("description"),
            raw.get("recommendation"),
            control_code=code,
            reference=reference,
        )
        if not evidence_original:
            continue

        evidence_visible = cont_comp_evidencia_texto_es(
            evidence_original,
            standard=standard,
            control_code=code,
            source=e.source or "Fuente de gobierno",
            status=e.status,
            severity=e.severity,
            reference=reference,
        )
        if not evidence_visible:
            continue

        record = {
            "status": cont_comp_estado_es(e.status),
            "source": e.source or "Fuente de gobierno",
            "source_type": e.source_type or "Hallazgo de gobierno",
            "title": evidence_visible,
            "reference": reference or "—",
            "severity": cont_comp_severidad_es(e.severity),
            "date": e.evidence_date,
            "control_name": e.control_name,
        }
        evidence_by_code.setdefault(code, []).append(record)

        if code not in catalog:
            if standard in ("ISO27001", "NISTCSF"):
                continue
            instrument_point = cont_comp_lookup_instrument_point(standard, code)
            mapped_name = raw.get("mapped_control_name") or e.control_name or ""
            catalog[code] = {
                "detail_code": code,
                "parent_code": (
                    (instrument_point or {}).get("parent")
                    or cont_comp_parent_for_detail(standard, code)
                ),
                "name": cont_comp_descripcion_normativa_es(
                    (instrument_point or {}).get("name")
                    or (
                        mapped_name
                        if mapped_name.strip()
                        and cont_comp_normalize_code(mapped_name) != code
                        else code
                    ),
                    standard=standard, code=code,
                ),
                "description": cont_comp_descripcion_normativa_es(
                    (instrument_point or {}).get("description")
                    or (
                        mapped_name
                        if mapped_name.strip()
                        and cont_comp_normalize_code(mapped_name) != code
                        else evidence_original
                    )
                    or code,
                    standard=standard, code=code,
                ),
                "description_source": (
                    (instrument_point or {}).get("source")
                    or "REFERENCIA_CONTROL"
                ),
            }

    rows = []

    for code, item in catalog.items():
        records = evidence_by_code.get(code, [])
        status, score, summary = cont_comp_final_status_from_evidences(records)

        if status == "No aplica":
            continue

        sources = sorted({r.get("source") for r in records if r.get("source")})
        last_seen = max([r.get("date") for r in records if r.get("date")], default=None)

        status_priority = {"No cumple": 1, "Parcial": 2, "Cumple": 3, "No evaluado": 4}
        ordered_records = sorted(
            records,
            key=lambda r: (
                status_priority.get(r.get("status"), 9),
                -(r.get("date").timestamp() if hasattr(r.get("date"), "timestamp") else 0),
            )
        )

        origin_details = []
        seen_details = set()
        for rec in ordered_records:
            key = (
                rec.get("source"), rec.get("reference"), rec.get("title"), rec.get("status")
            )
            if key in seen_details:
                continue
            seen_details.add(key)
            title = str(rec.get("title") or "").strip()
            if not title:
                continue
            if len(title) > 260:
                title = title[:257] + "..."
            origin_details.append({
                "source": rec.get("source") or "Fuente automática",
                "status": rec.get("status") or "No evaluado",
                "title": title,
                "reference": rec.get("reference") or "—",
                "severity": rec.get("severity") or "—",
            })
            if len(origin_details) >= 6:
                break

        rows.append({
            "detail_code": code,
            "parent_code": item.get("parent_code"),
            "name": item.get("name"),
            "description": item.get("description") or item.get("name") or code,
            "description_source": item.get("description_source") or "INSTRUMENTO",
            "source_type": ", ".join(sources) if sources else "Sin fuente automática",
            "status": status,
            "score": score,
            "summary": summary,
            "evidence_count": len(records),
            "last_evaluated_at": last_seen,
            "evaluation_type": "AUTOMATIC_MULTI_SOURCE" if records else "NOT_MONITORED",
            "origin_details": origin_details,
        })

    priority = {
        "No cumple": 1,
        "Parcial": 2,
        "Cumple": 3,
        "No monitoreado": 4,
    }

    rows.sort(key=lambda r: (
        priority.get(r["status"], 9),
        r["detail_code"]
    ))

    return rows


def cont_comp_group_detail_rows(rows):
    grouped = {}

    for r in rows:
        key = r.get("detail_code") or r.get("parent_code") or "SIN-CODIGO"

        if key not in grouped:
            grouped[key] = {
                "detail_code": key,
                "parent_code": r.get("parent_code"),
                "name": r.get("name"),
                "source_type": r.get("source_type"),
                "status": r.get("status"),
                "score": r.get("score"),
                "summary": r.get("summary"),
                "evidence_count": r.get("evidence_count"),
                "last_evaluated_at": r.get("last_evaluated_at"),
                "questions": [],
            }

        question_text = r.get("question") or ""
        question_code = r.get("question_code") or ""

        if question_text:
            grouped[key]["questions"].append({
                "code": question_code,
                "text": question_text,
            })

    return list(grouped.values())

def cont_comp_extract_compliance_tags(rule):
    rule = rule or {}
    compliance = []

    mappings = {
        "pci_dss": "PCIDSS",
        "pci": "PCIDSS",
        "tsc": "SOC2",
        "soc2": "SOC2",
        "iso_27001": "ISO27001",
        "iso27001": "ISO27001",
        "nist": "NISTCSF",
        "nist_csf": "NISTCSF",
        "nist_800_53": "NIST80053",
    }

    for wazuh_key, standard in mappings.items():
        values = rule.get(wazuh_key)

        if not values:
            continue

        codes = cont_comp_split_control_codes(values)

        for code in codes:
            compliance.append({
                "standard": standard,
                "control_code": code,
                "control_name": code
            })

    return compliance


def cont_comp_status_from_wazuh_level(level):
    level = int(level or 0)

    if level >= 8:
        return "No cumple", "Alta"

    if level >= 3:
        return "Parcial", "Media"

    return "Cumple", "Baja"


def cont_comp_save_compliance_controls_from_alert(alert_id, agent, rule, raw):
    compliance_tags = cont_comp_extract_compliance_tags(rule)

    if not compliance_tags:
        return 0

    saved = 0
    level = int(rule.get("level") or 0)
    status, score, severity = cont_comp_source_status("alert", level=level)
    supported_standards = {"ISO27001", "SOC2", "PCIDSS", "NISTCSF"}

    for tag in compliance_tags:
        standard = tag["standard"]
        raw_control_code = tag["control_code"]

        # NIST SP 800-53 se conserva como un marco distinto y no se mezcla
        # con la matriz NIST CSF 2.0.
        if standard not in supported_standards:
            continue

        if standard == "NISTCSF":
            control_codes = cont_comp_nist_csf_expand_codes(raw_control_code)
        else:
            control_codes = [raw_control_code]

        for control_code in control_codes:
            existing = WazuhComplianceControl.query.filter_by(
                standard=standard,
                control_code=control_code,
                alert_id=str(alert_id)
            ).first()

            if existing:
                existing.status = status
                existing.severity = severity
                existing.rule_level = level
                existing.rule_description = rule.get("description")
                existing.raw_json = json.dumps(raw, ensure_ascii=False)
                existing.synced_at = cont_comp_now()
                continue

            db.session.add(WazuhComplianceControl(
                standard=standard,
                control_code=control_code,
                control_name=tag.get("control_name") or control_code,
                alert_id=str(alert_id),
                agent_id=(agent or {}).get("id"),
                agent_name=(agent or {}).get("name"),
                rule_id=str(rule.get("id") or ""),
                rule_level=level,
                rule_description=rule.get("description"),
                status=status,
                severity=severity,
                raw_json=json.dumps(raw, ensure_ascii=False),
                synced_at=cont_comp_now()
            ))

            saved += 1

    return saved


# ============================================================
# RUTAS
# ============================================================


@app.route("/cumplimiento_continuo/evidencia_manual/<standard>/<control_code>", methods=["GET", "POST"])
@login_required
def cont_comp_manual_evidence(standard, control_code):
    flash("Cumplimiento Continuo es un módulo 100% automático. Use los módulos normativos de GRAC para evidencia documental.", "warning")
    return redirect(url_for("cont_comp_standard", standard=standard))

@app.route("/cumplimiento_continuo/evidencia_manual/revisar/<int:evidence_id>/<decision>")
@login_required
def cont_comp_review_manual_evidence(evidence_id, decision):
    flash("La revisión manual de evidencias no aplica en Cumplimiento Continuo.", "warning")
    return redirect(url_for("cont_comp_dashboard"))



@app.route("/cumplimiento_continuo")
@login_required
def cont_comp_dashboard():
    user, resp = cont_comp_require_read()
    if resp:
        return resp

    cont_comp_sync_governance_findings()
    cfg = WazuhConfig.query.first()

    last_sync = ContinuousComplianceSyncLog.query.order_by(
        ContinuousComplianceSyncLog.id.desc()
    ).first()

    try:
        firewall_devices_count = FirewallGovDevice.query.count()
        firewall_findings_count = FirewallGovFinding.query.filter_by(active=True).count()
        firewall_critical_count = FirewallGovFinding.query.filter_by(active=True, severity="Crítica").count()
        firewall_last_sync = FirewallGovSyncLog.query.order_by(FirewallGovSyncLog.id.desc()).first()
    except Exception:
        firewall_devices_count = 0
        firewall_findings_count = 0
        firewall_critical_count = 0
        firewall_last_sync = None

    ad_metrics = cont_comp_get_ad_dashboard_metrics()

    standards_keys = ["ISO27001", "SOC2", "PCIDSS", "NISTCSF"]

    standards = []

    total_cumple = 0
    total_parcial = 0
    total_no_cumple = 0
    total_no_monitoreado = 0
    total_evaluados = 0
    total_controles = 0

    for std in standards_keys:
        rows = cont_comp_build_standard_detail_rows(std)

        controles = len(rows)
        cumple = len([r for r in rows if r["status"] == "Cumple"])
        parcial = len([r for r in rows if r["status"] == "Parcial"])
        no_cumple = len([r for r in rows if r["status"] == "No cumple"])
        no_monitoreado = len([r for r in rows if r["status"] == "No monitoreado"])

        evaluados = cumple + parcial + no_cumple

        cobertura = round((evaluados / controles) * 100, 1) if controles else 0
        score = round(((cumple + (parcial * 0.5)) / evaluados) * 100, 1) if evaluados else 0

        standards.append({
            "code": std,
            "name": {
                "ISO27001": "ISO 27001",
                "SOC2": "SOC 2",
                "PCIDSS": "PCI-DSS",
                "NISTCSF": "NIST CSF 2.0"
            }.get(std, std),
            "controles": controles,
            "evaluados": evaluados,
            "cumple": cumple,
            "parcial": parcial,
            "no_cumple": no_cumple,
            "no_monitoreado": no_monitoreado,
            "cobertura": cobertura,
            "score": score
        })

        total_cumple += cumple
        total_parcial += parcial
        total_no_cumple += no_cumple
        total_no_monitoreado += no_monitoreado
        total_evaluados += evaluados
        total_controles += controles

    cobertura_global = round((total_evaluados / total_controles) * 100, 1) if total_controles else 0

    content = render_template_string("""
    <div class="row g-3">
      <div class="col-md-3">
        <div class="cc-kpi">
          <div class="icon"><i class="bi bi-check2-circle"></i></div>
          <div><div class="num">{{ total_cumple }}</div><div class="lbl">Cumple</div></div>
        </div>
      </div>

      <div class="col-md-3">
        <div class="cc-kpi">
          <div class="icon"><i class="bi bi-x-octagon"></i></div>
          <div><div class="num">{{ total_no_cumple }}</div><div class="lbl">Hallazgos técnicos</div></div>
        </div>
      </div>

      <div class="col-md-3">
        <div class="cc-kpi">
          <div class="icon"><i class="bi bi-broadcast"></i></div>
          <div><div class="num">{{ cobertura_global }}%</div><div class="lbl">Cobertura automática</div></div>
        </div>
      </div>

      <div class="col-md-3">
        <div class="cc-kpi">
          <div class="icon"><i class="bi bi-slash-circle"></i></div>
          <div><div class="num">{{ total_no_monitoreado }}</div><div class="lbl">No monitoreado</div></div>
        </div>
      </div>
    </div>

    <div class="cc-card mt-3">
      <h5 class="cc-section-title">Estado automático por estándar</h5>

      <div class="table-responsive">
        <table class="table cc-table table-hover align-middle">
          <thead>
            <tr>
              <th>Estándar</th>
              <th>Total puntos</th>
              <th>Evaluados automáticamente</th>
              <th>Cumple</th>
              <th>Parcial</th>
              <th>No cumple</th>
              <th>No monitoreado</th>
              <th>Cobertura</th>
              <th>Score técnico</th>
              <th>Acción</th>
            </tr>
          </thead>

          <tbody>
          {% for s in standards %}
            <tr>
              <td><span class="cc-pill">{{ s.name }}</span></td>
              <td><strong>{{ s.controles }}</strong></td>
              <td><strong>{{ s.evaluados }}</strong></td>
              <td class="text-success fw-bold">{{ s.cumple }}</td>
              <td class="text-warning fw-bold">{{ s.parcial }}</td>
              <td class="text-danger fw-bold">{{ s.no_cumple }}</td>
              <td class="text-secondary fw-bold">{{ s.no_monitoreado }}</td>
              <td><strong>{{ "%.1f"|format(s.cobertura or 0) }}%</strong></td>
              <td><strong>{{ "%.1f"|format(s.score or 0) }}%</strong></td>
              <td>
                <a class="btn btn-sm btn-outline-primary"
                   href="{{ url_for('cont_comp_standard', standard=s.code) }}">
                  Ver detalle
                </a>
              </td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
    </div>

    <div class="cc-card">
      <h5 class="cc-section-title">Estado de conexión</h5>
      <div class="row g-3">
        <div class="col-md-4">
          <div class="p-3 border rounded-4 h-100 bg-white">
            <div class="fw-bold text-primary mb-2"><i class="bi bi-broadcast"></i> Herramienta XDR (Wazuh)</div>
            <p class="mb-1"><strong>Estado:</strong> {{ cfg.last_status if cfg else "No configurado" }}</p>
            <p class="mb-1"><strong>Último mensaje:</strong> {{ cfg.last_message if cfg else "—" }}</p>
            <p class="mb-0"><strong>Última sincronización:</strong> {{ last_sync.finished_at if last_sync else "Sin sincronización" }}</p>
          </div>
        </div>
        <div class="col-md-4">
          <div class="p-3 border rounded-4 h-100 bg-white">
            <div class="fw-bold text-primary mb-2"><i class="bi bi-bricks"></i> Gobierno de Firewall</div>
            <p class="mb-1"><strong>Dispositivos:</strong> {{ firewall_devices_count }}</p>
            <p class="mb-1"><strong>Hallazgos activos:</strong> {{ firewall_findings_count }} · <strong>Críticos:</strong> {{ firewall_critical_count }}</p>
            <p class="mb-2"><strong>Última sincronización:</strong> {{ firewall_last_sync.finished_at if firewall_last_sync else "Sin sincronización" }}</p>
            <a class="btn btn-sm btn-outline-primary" href="{{ url_for('cumplimiento_continuo_firewall') }}">Abrir Gobierno de Firewall</a>
          </div>
        </div>
        <div class="col-md-4">
          <div class="p-3 border rounded-4 h-100 bg-white">
            <div class="fw-bold text-primary mb-2"><i class="bi bi-person-lock"></i> Gobierno del Directorio Activo</div>
            <p class="mb-1"><strong>Conectores:</strong> {{ ad_metrics.connectors }}</p>
            <p class="mb-1"><strong>Hallazgos activos:</strong> {{ ad_metrics.findings }} · <strong>Críticos:</strong> {{ ad_metrics.critical }}</p>
            <p class="mb-2"><strong>Última sincronización:</strong> {{ ad_metrics.last_sync or 'Sin sincronización' }}</p>
            <a class="btn btn-sm btn-outline-primary" href="{{ url_for('adgov.dashboard') }}">Abrir Gobierno del Directorio Activo</a>
          </div>
        </div>
      </div>
    </div>
    """,
    cfg=cfg,
    standards=standards,
    total_cumple=total_cumple,
    total_parcial=total_parcial,
    total_no_cumple=total_no_cumple,
    total_no_monitoreado=total_no_monitoreado,
    cobertura_global=cobertura_global,
    last_sync=last_sync,
    firewall_devices_count=firewall_devices_count,
    firewall_findings_count=firewall_findings_count,
    firewall_critical_count=firewall_critical_count,
    firewall_last_sync=firewall_last_sync,
    ad_metrics=ad_metrics)

    return cont_comp_render(
        content,
        "dashboard",
        "Cumplimiento Continuo",
        "Monitoreo automático con herramienta XDR (Wazuh), Gobierno de Firewall y Gobierno del Directorio Activo."
    )


@app.route("/cumplimiento_continuo/wazuh", methods=["GET", "POST"])
@login_required
def cont_comp_wazuh_config():
    user, resp = cont_comp_require_write()
    if resp:
        return resp

    cfg = cont_comp_get_config()

    if request.method == "POST":
        cfg.api_url = (request.form.get("api_url") or "").strip().rstrip("/")
        cfg.username = (request.form.get("username") or "").strip()
        new_password = request.form.get("password") or ""
        if new_password.strip():
            cfg.password = new_password.strip()
            cfg.token = None
        cfg.verify_ssl = bool(request.form.get("verify_ssl"))
        db.session.commit()

        if request.form.get("action") == "test":
            try:
                cont_comp_wazuh_authenticate(cfg)
                flash("Conexión Wazuh validada correctamente.", "success")
            except Exception as e:
                cfg.last_status = "Offline"
                cfg.last_message = str(e)
                cfg.last_test_at = cont_comp_now()
                db.session.commit()
                flash(f"No fue posible conectar con Wazuh: {e}", "danger")
        else:
            flash("Configuración Wazuh guardada.", "success")

        return redirect(url_for("cont_comp_wazuh_config"))

    content = render_template_string("""
    <div class="cc-card">
      <h5 class="cc-section-title">Conexión Wazuh API</h5>
      <form method="POST" class="cc-form">
        <div class="row g-3">
          <div class="col-md-6">
            <label>URL API</label>
            <input class="form-control" name="api_url" value="{{ cfg.api_url }}" placeholder="https://localhost:55000">
          </div>
          <div class="col-md-3">
            <label>Usuario</label>
            <input class="form-control" name="username" value="{{ cfg.username }}" placeholder="wazuh-wui">
          </div>
          <div class="col-md-3">
            <label>Contraseña / Token</label>
            <input class="form-control" name="password" type="password" placeholder="Dejar vacío para conservar">
          </div>
          <div class="col-md-12">
            <div class="form-check mt-2">
              <input class="form-check-input" type="checkbox" name="verify_ssl" id="verify_ssl" {% if cfg.verify_ssl %}checked{% endif %}>
              <label class="form-check-label" for="verify_ssl">Verificar certificado SSL</label>
            </div>
            <small class="cc-muted">Para laboratorio Docker local normalmente se deja desactivado.</small>
          </div>
        </div>
        <div class="mt-4 d-flex gap-2 flex-wrap">
          <button class="btn btn-primary" name="action" value="save">Guardar</button>
          <button class="btn btn-success" name="action" value="test">Validar conexión</button>
          <a class="btn btn-outline-secondary" href="{{ url_for('cont_comp_dashboard') }}">Volver</a>
        </div>
      </form>
    </div>

    <div class="cc-card">
      <h5 class="cc-section-title">Estado</h5>
      <p><strong>Estado:</strong> {{ cfg.last_status or "Sin validar" }}</p>
      <p><strong>Mensaje:</strong> {{ cfg.last_message or "—" }}</p>
      <p><strong>Última prueba:</strong> {{ cfg.last_test_at or "—" }}</p>
    </div>
    """, cfg=cfg)

    return cont_comp_render(content, "wazuh", "Herramienta XDR (Wazuh)", "Configure la API REST de Wazuh para extraer agentes, alertas, vulnerabilidades, FIM, SCA y MITRE.")


@app.route("/cumplimiento_continuo/sincronizacion", methods=["GET", "POST"])
@login_required
def cont_comp_sync_view():
    user, resp = cont_comp_require_write()
    if resp:
        return resp

    if request.method == "POST":
        try:
            log = cont_comp_full_sync()
            flash("Sincronización ejecutada correctamente.", "success")
        except Exception as e:
            flash(f"Error ejecutando sincronización: {e}", "danger")
        return redirect(url_for("cont_comp_sync_view"))

    logs = ContinuousComplianceSyncLog.query.order_by(ContinuousComplianceSyncLog.id.desc()).limit(20).all()

    content = render_template_string("""
    <div class="cc-card">
      <h5 class="cc-section-title">Sincronizar datos desde Wazuh</h5>
      <p class="cc-muted">Extrae agentes, vulnerabilidades, alertas, SCA y eventos MITRE/FIM disponibles. Luego recalcula el cumplimiento y genera evidencias y planes de acción.</p>
      <form method="POST">
        <button class="btn btn-warning" data-progress-text="Sincronizando datos desde Wazuh...">
          <i class="bi bi-arrow-repeat"></i> Ejecutar sincronización
        </button>
      </form>
    </div>

    <div class="cc-card">
      <h5 class="cc-section-title">Historial de sincronización</h5>
      <div class="table-responsive">
        <table class="table cc-table">
          <thead><tr><th>Inicio</th><th>Fin</th><th>Estado</th><th>Agentes</th><th>Vulns</th><th>Alertas</th><th>SCA</th><th>FIM</th><th>MITRE</th><th>Mensaje</th></tr></thead>
          <tbody>
          {% for l in logs %}
            <tr>
              <td>{{ l.started_at }}</td><td>{{ l.finished_at or "—" }}</td><td>{{ l.status }}</td>
              <td>{{ l.agents_count }}</td><td>{{ l.vulnerabilities_count }}</td><td>{{ l.alerts_count }}</td>
              <td>{{ l.sca_count }}</td><td>{{ l.fim_count }}</td><td>{{ l.mitre_count }}</td><td>{{ l.message }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    """, logs=logs)

    return cont_comp_render(content, "sync", "Sincronización", "Actualice la información técnica recolectada desde Wazuh.")



@app.route("/cumplimiento_continuo/estandar/<standard>")
@login_required
def cont_comp_standard(standard):
    user, resp = cont_comp_require_read()
    if resp:
        return resp

    standard = (standard or "").strip().upper()
    cont_comp_sync_governance_findings()

    titles = {
        "ISO27001": "ISO 27001",
        "SOC2": "SOC 2",
        "PCIDSS": "PCI-DSS",
        "NISTCSF": "NIST CSF 2.0"
    }

    rows_all = cont_comp_build_standard_detail_rows(standard)

    no_cumple = [r for r in rows_all if r["status"] == "No cumple"]
    parcial = [r for r in rows_all if r["status"] == "Parcial"]
    cumple = [r for r in rows_all if r["status"] == "Cumple"]
    no_monitoreado = [r for r in rows_all if r["status"] == "No monitoreado"]

    rows = no_cumple + parcial + cumple

    evaluados = len(rows)
    total = len(rows_all)
    cobertura = round((evaluados / total) * 100, 1) if total else 0
    score = round(((len(cumple) + (len(parcial) * 0.5)) / evaluados) * 100, 1) if evaluados else 0

    content = render_template_string("""
    <div class="row g-3">
      <div class="col-md-3"><div class="cc-kpi"><div class="icon"><i class="bi bi-x-octagon"></i></div><div><div class="num">{{ no_cumple|length }}</div><div class="lbl">No cumple</div></div></div></div>
      <div class="col-md-3"><div class="cc-kpi"><div class="icon"><i class="bi bi-exclamation-triangle"></i></div><div><div class="num">{{ parcial|length }}</div><div class="lbl">Parcial</div></div></div></div>
      <div class="col-md-3"><div class="cc-kpi"><div class="icon"><i class="bi bi-check-circle"></i></div><div><div class="num">{{ cumple|length }}</div><div class="lbl">Cumple</div></div></div></div>
      <div class="col-md-3"><div class="cc-kpi"><div class="icon"><i class="bi bi-broadcast"></i></div><div><div class="num">{{ cobertura }}%</div><div class="lbl">Cobertura automática</div></div></div></div>
    </div>

    <div class="cc-card mt-3">
      <h5 class="cc-section-title">{{ title }} — Evaluación automática multifuente</h5>

      <p class="cc-muted mb-3">
        La evaluación consolida evidencias de la <strong>herramienta XDR (Wazuh)</strong>,
        <strong>Gobierno de Firewall</strong> y <strong>Gobierno del Directorio Activo</strong>.
        Puntos no monitoreados ocultos: <strong>{{ no_monitoreado|length }}</strong>.
        Score técnico sobre puntos evaluados: <strong>{{ score }}%</strong>.
      </p>

      <div class="table-responsive">
        <table class="table cc-table cc-standard-matrix table-hover align-middle">
          <colgroup>
            <col class="cc-col-point">
            <col class="cc-col-description">
            <col class="cc-col-status">
            <col class="cc-col-analysis">
            <col class="cc-col-evidence">
            <col class="cc-col-source">
            <col class="cc-col-date">
            <col class="cc-col-action">
          </colgroup>
          <thead>
            <tr>
              <th>Punto norma</th>
              <th>Descripción</th>
              <th>Estado</th>
              <th>Análisis consolidado</th>
              <th>Evidencias</th>
              <th>Fuente de evaluación</th>
              <th>Última evaluación</th>
              <th>Acción</th>
            </tr>
          </thead>

          <tbody>
          {% for r in rows %}
            <tr>
              <td><strong>{{ r.detail_code }}</strong><br><small>{{ r.parent_code or "—" }}</small></td>
              <td>
                <div class="cc-norm-description">{{ r.description or "—" }}</div>
              </td>
              <td>{{ status_badge(r.status)|safe }}</td>
              <td><small>{{ r.summary }}</small></td>
              <td><strong>{{ r.evidence_count }}</strong></td>
              <td><span class="cc-pill">{{ r.source_type }}</span></td>
              <td>{{ r.last_evaluated_at or "—" }}</td>
              <td>
                <a class="btn btn-sm btn-outline-primary" href="{{ url_for('cont_comp_evidences', standard=standard, control_code=r.detail_code) }}">Ver evidencia</a>
              </td>
            </tr>
          {% else %}
            <tr><td colspan="8" class="cc-empty">No hay evidencias automáticas de XDR, Firewall o Active Directory para este estándar.</td></tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    """,
    rows=rows,
    no_cumple=no_cumple,
    parcial=parcial,
    cumple=cumple,
    no_monitoreado=no_monitoreado,
    standard=standard,
    title=titles.get(standard, standard),
    cobertura=cobertura,
    score=score,
    status_badge=cont_comp_status_badge)

    return cont_comp_render(
        content,
        standard,
        titles.get(standard, standard),
        "Evaluación automática con herramienta XDR, Gobierno de Firewall y Gobierno del Directorio Activo."
    )


@app.route("/cumplimiento_continuo/evidencias")
@login_required
def cont_comp_evidences():
    user, resp = cont_comp_require_read()
    if resp:
        return resp

    standard = (request.args.get("standard") or "").strip().upper()
    control_code = cont_comp_normalize_code(request.args.get("control_code") or "")
    source_filter = (request.args.get("source") or "").strip()
    status_filter = (request.args.get("status") or "").strip()
    if status_filter not in ("Cumple", "Parcial", "No cumple"):
        status_filter = ""

    cont_comp_sync_governance_findings()
    evidences = cont_comp_collect_evidence_rows(
        standard=standard,
        control_code=control_code,
        source_filter=source_filter,
        status_filter=status_filter,
    )

    # En Evidencias se muestran los resultados con evaluación técnica:
    # Cumple, Parcial y No cumple. Se mantienen ocultos No aplica y No evaluado.
    evidences = [
        e for e in evidences
        if (e.get("status") or "").strip() in ("Cumple", "Parcial", "No cumple")
    ]

    counts = {
        "Cumple": sum(1 for e in evidences if e["status"] == "Cumple"),
        "Parcial": sum(1 for e in evidences if e["status"] == "Parcial"),
        "No cumple": sum(1 for e in evidences if e["status"] == "No cumple"),
    }

    content = render_template_string("""
    <div class="row g-3 mb-3">
      <div class="col-lg-3 col-md-6"><div class="cc-kpi"><div class="icon"><i class="bi bi-check-circle"></i></div><div><div class="num">{{ counts['Cumple'] }}</div><div class="lbl">Cumple</div></div></div></div>
      <div class="col-lg-3 col-md-6"><div class="cc-kpi"><div class="icon"><i class="bi bi-exclamation-circle"></i></div><div><div class="num">{{ counts['Parcial'] }}</div><div class="lbl">Parcial</div></div></div></div>
      <div class="col-lg-3 col-md-6"><div class="cc-kpi"><div class="icon"><i class="bi bi-x-octagon"></i></div><div><div class="num">{{ counts['No cumple'] }}</div><div class="lbl">No cumple</div></div></div></div>
      <div class="col-lg-3 col-md-6"><div class="cc-kpi"><div class="icon"><i class="bi bi-database-check"></i></div><div><div class="num">{{ evidences|length }}</div><div class="lbl">Total evidencias</div></div></div></div>
    </div>

    <div class="cc-card">
      <h5 class="cc-section-title">Evidencias automáticas multifuente</h5>

      <p class="cc-muted mb-3">
        Incluye puntos que <strong>cumplen</strong>, presentan cumplimiento <strong>parcial</strong>
        o <strong>no cumplen</strong>, obtenidos desde la <strong>herramienta XDR (Wazuh)</strong>,
        <strong>Gobierno de Firewall</strong> y <strong>Gobierno del Directorio Activo</strong>.
      </p>

      <form class="row g-2 mb-3">
        <div class="col-lg-2 col-md-4"><input class="form-control" name="standard" placeholder="PCIDSS / SOC2 / ISO27001 / NISTCSF" value="{{ standard }}"></div>
        <div class="col-lg-2 col-md-4"><input class="form-control" name="control_code" placeholder="1.2.5 / A.8.8 / PR.AA" value="{{ control_code }}"></div>
        <div class="col-lg-3 col-md-4">
          <select class="form-select" name="source">
            <option value="">Todas las fuentes</option>
            {% for value in ['Herramienta XDR (Wazuh)','Gobierno de Firewall','Gobierno del Directorio Activo'] %}
            <option value="{{ value }}" {% if source_filter == value %}selected{% endif %}>{{ value }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-lg-2 col-md-4">
          <select class="form-select" name="status">
            <option value="">Cumple, parcial y no cumple</option>
            {% for value in ['Cumple','Parcial','No cumple'] %}
            <option value="{{ value }}" {% if status_filter == value %}selected{% endif %}>{{ value }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-lg-1 col-md-4"><button class="btn btn-primary w-100">Filtrar</button></div>
        <div class="col-lg-2 col-md-4"><a class="btn btn-outline-secondary w-100" href="{{ url_for('cont_comp_evidences') }}">Limpiar</a></div>
      </form>

      <div class="table-responsive">
        <table class="table cc-table table-hover align-middle">
          <thead>
            <tr>
              <th>Fecha</th><th>Fuente</th><th>Estándar</th><th>Punto norma</th><th>Estado</th>
              <th>Activo / cuenta / regla</th><th>Referencia</th><th>Severidad</th><th>Hallazgo o evidencia obtenida</th>
            </tr>
          </thead>
          <tbody>
          {% for e in evidences %}
            <tr>
              <td>{{ e.date or '—' }}</td>
              <td><span class="cc-pill">{{ e.source }}</span></td>
              <td>{{ e.standard }}</td>
              <td><strong>{{ e.control_code }}</strong></td>
              <td>{{ status_badge(e.status)|safe }}</td>
              <td>{{ e.asset or '—' }}</td>
              <td>{{ e.reference or '—' }}</td>
              <td>{{ e.severity or '—' }}</td>
              <td style="min-width:320px">{{ e.description or '—' }}</td>
            </tr>
          {% else %}
            <tr><td colspan="9" class="cc-empty">No hay evidencias visibles para este filtro.</td></tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    """,
    evidences=evidences,
    counts=counts,
    standard=standard,
    control_code=control_code,
    source_filter=source_filter,
    status_filter=status_filter,
    status_badge=cont_comp_status_badge)

    return cont_comp_render(
        content,
        "evidences",
        "Evidencias de Cumplimiento Continuo",
        "Evidencias de la herramienta XDR, Gobierno de Firewall y Gobierno del Directorio Activo."
    )


@app.route("/cumplimiento_continuo/planes")
@login_required
def cont_comp_action_plans():
    return redirect(url_for("planes_accion_dashboard"))


@app.route("/cumplimiento_continuo/planes/<int:plan_id>", methods=["GET", "POST"])
@login_required
def cont_comp_action_plan_edit(plan_id):
    user, resp = cont_comp_require_write()
    if resp:
        return resp

    plan = ContinuousActionPlan.query.get_or_404(plan_id)

    if request.method == "POST":
        plan.responsible = (request.form.get("responsible") or "").strip()
        plan.due_date = (request.form.get("due_date") or "").strip()
        plan.status = (request.form.get("status") or "Abierto").strip()
        plan.description = (request.form.get("description") or "").strip()
        db.session.commit()
        flash("Plan de acción actualizado.", "success")
        return redirect(url_for("cont_comp_action_plans"))

    content = render_template_string("""
    <div class="cc-card">
      <h5 class="cc-section-title">Gestionar Plan de Acción</h5>
      <form method="POST" class="cc-form">
        <div class="mb-3">
          <label>Título</label>
          <input class="form-control" value="{{ plan.title }}" disabled>
        </div>
        <div class="mb-3">
          <label>Descripción</label>
          <textarea class="form-control" name="description" rows="5">{{ plan.description or "" }}</textarea>
        </div>
        <div class="row g-3">
          <div class="col-md-4"><label>Responsable</label><input class="form-control" name="responsible" value="{{ plan.responsible or '' }}"></div>
          <div class="col-md-4"><label>Fecha objetivo</label><input class="form-control" type="date" name="due_date" value="{{ plan.due_date or '' }}"></div>
          <div class="col-md-4"><label>Estado</label>
            <select class="form-select" name="status">
              {% for s in ["Abierto","En proceso","Cerrado","Cancelado"] %}
                <option value="{{ s }}" {% if plan.status == s %}selected{% endif %}>{{ s }}</option>
              {% endfor %}
            </select>
          </div>
        </div>
        <div class="mt-4 d-flex gap-2">
          <button class="btn btn-primary">Guardar</button>
          <a class="btn btn-outline-secondary" href="{{ url_for('cont_comp_action_plans') }}">Volver</a>
        </div>
      </form>
    </div>
    """, plan=plan)

    return cont_comp_render(content, "plans", "Gestionar Plan de Acción", "Actualice responsable, fecha objetivo, estado y descripción.")



# ============================================================================================================================================
#                         CAPÍTULO INDEPENDIENTE: PLAN DE ACCIÓN
#                         Consolidación ISO 27001, SOC 2, PCI-DSS, NIST CSF,
#                         Cumplimiento Continuo, Gobierno de Firewall y Riesgos
# ============================================================================================================================================

from sqlalchemy import or_ as pa_or_

PLANES_ACCION_MODULE_NAME = "Planes de acción del SGSI"
PA_STANDARD_LABELS = {
    "ISO27001": "ISO 27001",
    "SOC2": "SOC 2",
    "PCIDSS": "PCI-DSS",
    "NISTCSF": "NIST CSF 2.0",
    "RIESGOS": "Gestión de Riesgos",
    "MULTI": "Múltiples estándares",
    "SGSI": "Sistema de Gestión",
    "": "Sin clasificar",
}


def pa_current_user():
    return User.query.get(session.get("user_id"))


def pa_can_read(user):
    if not user:
        return False
    if user.role in ("admin", "auditor"):
        return True
    return verificar_permiso(user, PLANES_ACCION_MODULE_NAME)


def pa_can_write(user):
    if not user or user.role == "auditor":
        return False
    if user.role == "admin":
        return True
    return verificar_permiso(user, PLANES_ACCION_MODULE_NAME)


def pa_require_read():
    user = pa_current_user()
    if not pa_can_read(user):
        flash("No tiene permiso para acceder al capítulo Plan de Acción.", "danger")
        return None, redirect(url_for("menu"))
    return user, None


def pa_require_write():
    user = pa_current_user()
    if user and user.role == "auditor":
        flash("El rol Auditor solo puede consultar los planes de acción.", "warning")
        return None, redirect(url_for("planes_accion_dashboard"))
    if not pa_can_write(user):
        flash("No tiene permiso para registrar o modificar planes de acción.", "danger")
        return None, redirect(url_for("menu"))
    return user, None


def pa_username(user):
    if not user:
        return "Sistema"
    return (
        getattr(user, "nombre_completo", None)
        or getattr(user, "username", None)
        or getattr(user, "email", None)
        or "Usuario"
    )


def pa_standard_label(value):
    key = (value or "").strip().upper()
    return PA_STANDARD_LABELS.get(key, value or "Sin clasificar")


def pa_clean_text(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False, indent=2)
        except Exception:
            return str(value)
    text_value = str(value).strip()
    if not text_value or text_value in ("{}", "[]", "null", "None"):
        return ""
    return text_value


def pa_normalize_duplicate_value(value):
    """
    Normaliza texto para detectar duplicados aunque cambien mayúsculas,
    acentos o espacios.
    """
    value = pa_clean_text(value)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value).strip().casefold()


def pa_duplicate_signature(values):
    """
    Identidad funcional del plan. Responsable, fecha, estado y descripción
    pueden actualizarse sin convertir el mismo plan en uno diferente.
    """
    fields = (
        "origin", "standard", "control_code", "title", "asset", "action_type"
    )
    return tuple(pa_normalize_duplicate_value(values.get(field)) for field in fields)


def pa_source_is_automatic(source_ref):
    source_ref = pa_normalize_duplicate_value(source_ref)
    return bool(source_ref) and not (
        source_ref.startswith("manual:")
        or source_ref.startswith("riesgo-manual:")
    )


def pa_source_is_suppressed(source_ref):
    source_ref = (source_ref or "").strip()
    if not source_ref or not pa_source_is_automatic(source_ref):
        return False
    return ContinuousActionPlanSuppression.query.filter_by(
        source_ref=source_ref
    ).first() is not None


def pa_find_duplicate_plan(values, source_ref="", exclude_id=None):
    """
    Busca el plan existente por referencia de origen y, adicionalmente,
    por su identidad funcional normalizada.
    """
    source_ref = (source_ref or "").strip()

    if source_ref:
        source_query = ContinuousActionPlan.query.filter_by(source_ref=source_ref)
        if exclude_id is not None:
            source_query = source_query.filter(ContinuousActionPlan.id != exclude_id)
        existing = source_query.order_by(ContinuousActionPlan.id.asc()).first()
        if existing:
            return existing

    target_signature = pa_duplicate_signature(values)
    query = ContinuousActionPlan.query
    if exclude_id is not None:
        query = query.filter(ContinuousActionPlan.id != exclude_id)

    for existing in query.order_by(ContinuousActionPlan.id.asc()).all():
        existing_values = {
            "origin": existing.origin,
            "standard": existing.standard,
            "control_code": existing.control_code,
            "title": existing.title,
            "asset": existing.asset,
            "action_type": existing.action_type,
        }
        if pa_duplicate_signature(existing_values) == target_signature:
            return existing
    return None


def pa_due_date_obj(value):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def pa_status_closed(value):
    return (value or "").strip().lower() in {
        "cerrado", "cancelado", "completado", "resuelto", "finalizado"
    }


def pa_effective_status(plan, today=None):
    """
    Estado visible del plan.

    "Vencido" es un estado calculado: aplica cuando la fecha objetivo ya pasó
    y el plan todavía no está cerrado, cancelado, completado, resuelto o
    finalizado. No se guarda en la base de datos para evitar que quede
    desactualizado con el paso del tiempo.
    """
    today = today or date.today()
    stored_status = (getattr(plan, "status", "") or "Abierto").strip()
    due_date = pa_due_date_obj(getattr(plan, "due_date", ""))

    if due_date and due_date < today and not pa_status_closed(stored_status):
        return "Vencido"
    return stored_status or "Abierto"


def pa_badge_status(value):
    status = (value or "Abierto").strip()
    cls = {
        "Abierto": "danger",
        "En proceso": "warning text-dark",
        "Vencido": "danger",
        "Cerrado": "success",
        "Cancelado": "secondary",
    }.get(status, "info text-dark")
    return Markup(f'<span class="badge bg-{cls}">{escape(status)}</span>')


def pa_badge_severity(value):
    sev = (value or "Sin clasificar").strip()
    cls = {
        "Crítica": "danger",
        "Critica": "danger",
        "Alta": "warning text-dark",
        "Media": "info text-dark",
        "Baja": "success",
    }.get(sev, "secondary")
    return Markup(f'<span class="badge bg-{cls}">{escape(sev)}</span>')


def pa_risk_severity(risk):
    raw = " ".join([
        str(getattr(risk, "riesgo_residual", "") or ""),
        str(getattr(risk, "riesgo_inherente", "") or ""),
    ]).lower()
    if "extremo" in raw or "crít" in raw or "critic" in raw:
        return "Crítica"
    if "alto" in raw or "high" in raw:
        return "Alta"
    if "moder" in raw or "medio" in raw or "medium" in raw:
        return "Media"
    return "Baja"


def pa_upsert_source_plan(
    source_ref,
    origin,
    standard,
    title,
    description="",
    control_code="",
    asset="",
    severity="Media",
    action_type="Plan de cumplimiento",
    responsible="",
    due_date="",
    status="Abierto",
    raw_json=None,
):
    source_ref = (source_ref or "").strip()
    if not source_ref:
        return False

    plan = ContinuousActionPlan.query.filter_by(source_ref=source_ref).first()
    created = plan is None
    if created:
        if pa_source_is_suppressed(source_ref):
            return False

        values = {
            "origin": origin,
            "standard": standard,
            "control_code": control_code,
            "title": title,
            "asset": asset,
            "action_type": action_type,
        }
        if pa_find_duplicate_plan(values, source_ref=source_ref):
            return False

        plan = ContinuousActionPlan(source_ref=source_ref)
        db.session.add(plan)

    plan.origin = (origin or "Sistema").strip()
    plan.standard = (standard or "SGSI").strip().upper()
    plan.control_code = (control_code or "").strip()
    plan.title = (title or "Plan de acción").strip()[:500]
    plan.asset = (asset or "").strip()[:255]
    plan.severity = (severity or "Media").strip()
    plan.action_type = (action_type or "Plan de cumplimiento").strip()

    # Se conserva la gestión realizada por el usuario en registros ya existentes.
    if created or not (plan.description or "").strip():
        plan.description = pa_clean_text(description)
    if created or not (plan.responsible or "").strip():
        plan.responsible = (responsible or "").strip()
    if created or not (plan.due_date or "").strip():
        plan.due_date = (due_date or "").strip()
    if created:
        plan.status = (status or "Abierto").strip()

    if raw_json is not None:
        try:
            plan.raw_json = json.dumps(raw_json, ensure_ascii=False)
        except Exception:
            plan.raw_json = str(raw_json)

    return created


def pa_sync_legacy_mejora():
    created = 0
    for item in MejoraPlanRegistro.query.order_by(MejoraPlanRegistro.id.asc()).limit(2000).all():
        description = "\n\n".join([
            part for part in [
                f"Descripción o incumplimiento: {item.descripcion_incumplimiento}" if item.descripcion_incumplimiento else "",
                f"Causa: {item.causa}" if item.causa else "",
                f"Plan de acción: {item.plan_accion}" if item.plan_accion else "",
                f"Observación de eficacia: {item.observacion_eficacia}" if item.observacion_eficacia else "",
            ] if part
        ])
        title = item.descripcion_incumplimiento or item.plan_accion or f"Plan de mejora #{item.id}"
        if pa_upsert_source_plan(
            source_ref=f"mejora-legacy:{item.id}",
            origin="Mejora Continua",
            standard="ISO27001",
            title=title,
            description=description,
            control_code="Mejora SGSI",
            severity="Media",
            action_type=item.tipo_accion or "Mejora",
            responsible=item.responsable or "",
            due_date=item.fecha_ejecucion_propuesta or "",
            status="Cerrado" if (item.estado_actividad or "").strip().lower() == "cerrado" else "Abierto",
            raw_json={"legacy_mejora_id": item.id, "eficacia": item.eficacia},
        ):
            created += 1
    return created


def pa_sync_iso_maturity():
    created = 0
    for run in AnalysisRun.query.order_by(AnalysisRun.id.asc()).limit(1000).all():
        plan_text = pa_clean_text(run.action_plan_json)
        if not plan_text:
            continue
        if pa_upsert_source_plan(
            source_ref=f"madurez:ISO27001:{run.id}",
            origin="Madurez ISO 27001",
            standard="ISO27001",
            title=f"Plan de acción ISO 27001 - {run.company_name or 'Evaluación'}",
            description=plan_text,
            control_code="Evaluación de madurez",
            asset=run.company_name or "",
            severity="Media",
            action_type="Plan de cumplimiento",
            raw_json={"analysis_run_id": run.id, "filename": run.filename},
        ):
            created += 1
    return created


def pa_sync_nist_maturity():
    created = 0
    for run in NistMadurezRun.query.order_by(NistMadurezRun.id.asc()).limit(1000).all():
        plan_text = pa_clean_text(run.plan_trabajo_editado or run.plan_trabajo_ai)
        if not plan_text:
            continue
        if pa_upsert_source_plan(
            source_ref=f"madurez:NISTCSF:{run.id}",
            origin="Madurez NIST CSF 2.0",
            standard="NISTCSF",
            title=f"Plan de trabajo NIST CSF 2.0 - {run.consecutivo or run.id}",
            description=plan_text,
            control_code="Evaluación de madurez",
            asset=run.consecutivo or "",
            severity="Media",
            action_type="Plan de cumplimiento",
            raw_json={"nist_run_id": run.id, "cumplimiento": run.pct_general},
        ):
            created += 1
    return created


def pa_sync_pci_maturity():
    created = 0
    for run in PciAnalysisRun.query.order_by(PciAnalysisRun.id.asc()).limit(1000).all():
        plan_text = pa_clean_text(run.plan_trabajo_editado or run.plan_trabajo_ai)
        if not plan_text:
            continue
        if pa_upsert_source_plan(
            source_ref=f"madurez:PCIDSS:{run.id}",
            origin="Madurez PCI-DSS",
            standard="PCIDSS",
            title=f"Plan de trabajo PCI-DSS - {run.company_name or run.id}",
            description=plan_text,
            control_code="Evaluación de madurez",
            asset=run.company_name or "",
            severity="Alta",
            action_type="Plan de cumplimiento",
            raw_json={"pci_analysis_run_id": run.id, "pci_run_id": run.pci_run_id},
        ):
            created += 1
    return created


def pa_sync_soc2_maturity():
    created = 0
    for run in Soc2MadurezRun.query.order_by(Soc2MadurezRun.id.asc()).limit(1000).all():
        plan_text = pa_clean_text(run.plan_trabajo_editado or run.plan_trabajo_ai)
        if not plan_text:
            continue
        name = run.consecutivo or run.company_name or str(run.id)
        if pa_upsert_source_plan(
            source_ref=f"madurez:SOC2:{run.id}",
            origin="Madurez SOC 2",
            standard="SOC2",
            title=f"Plan de trabajo SOC 2 - {name}",
            description=plan_text,
            control_code="Evaluación de madurez",
            asset=run.company_name or run.consecutivo or "",
            severity="Media",
            action_type="Plan de cumplimiento",
            raw_json={"soc2_run_id": run.id, "cumplimiento": run.pct_general},
        ):
            created += 1
    return created


def pa_sync_risk_existing_plans():
    created = 0
    for risk in Riesgo.query.order_by(Riesgo.id.asc()).limit(3000).all():
        plan_a = pa_clean_text(getattr(risk, "plan_accion", ""))
        plan_b = pa_clean_text(getattr(risk, "planes_accion", ""))
        if not plan_a and not plan_b:
            continue
        description = "\n\n".join([
            part for part in [
                f"Riesgo: {risk.riesgo}" if risk.riesgo else "",
                f"Plan de acción del control: {plan_a}" if plan_a else "",
                f"Plan de tratamiento residual: {plan_b}" if plan_b else "",
                f"Observaciones: {risk.observaciones}" if risk.observaciones else "",
            ] if part
        ])
        if pa_upsert_source_plan(
            source_ref=f"riesgo-existente:{risk.id}",
            origin="Gestión de Riesgos",
            standard="RIESGOS",
            title=f"Tratamiento del riesgo {risk.codigo_riesgo or risk.id}",
            description=description,
            control_code=risk.codigo_riesgo or str(risk.id),
            asset=risk.nombre_activo or risk.activo or "",
            severity=pa_risk_severity(risk),
            action_type="Tratamiento de riesgo",
            responsible=risk.responsable or risk.propietario_riesgo or "",
            due_date=risk.fecha_implementacion or "",
            status="Abierto",
            raw_json={"riesgo_id": risk.id},
        ):
            created += 1
    return created


def pa_sync_continuous_controls():
    created = 0
    controls = ContinuousControl.query.filter(
        ContinuousControl.status.in_(["No cumple", "Parcial"])
    ).order_by(ContinuousControl.id.asc()).limit(3000).all()

    for control in controls:
        severity = "Alta" if control.status == "No cumple" else "Media"
        description = "\n\n".join([
            part for part in [
                f"Estado: {control.status}",
                f"Control: {control.control_name}" if control.control_name else "",
                f"Evidencia: {control.evidence_summary}" if control.evidence_summary else "",
                f"Notas: {control.notes}" if control.notes else "",
            ] if part
        ])
        source_ref = (
            f"cumplimiento-control:{control.standard}:{control.control_code}:"
            f"{control.source_type}:{control.id}"
        )
        if pa_upsert_source_plan(
            source_ref=source_ref,
            origin="Cumplimiento Continuo",
            standard=control.standard,
            title=f"Corregir {control.standard} {control.control_code} - {control.control_name}",
            description=description,
            control_code=control.control_code,
            severity=severity,
            action_type="Remediación de control",
            raw_json={"continuous_control_id": control.id},
        ):
            created += 1
    return created


def pa_sync_wazuh_compliance_controls():
    created = 0
    rows = WazuhComplianceControl.query.filter(
        WazuhComplianceControl.status.in_(["No cumple", "Parcial"])
    ).order_by(WazuhComplianceControl.id.asc()).limit(5000).all()

    for row in rows:
        event_ref = row.alert_id or str(row.id)
        source_ref = f"wazuh-control:{row.standard}:{row.control_code}:{event_ref}"
        description = "\n\n".join([
            part for part in [
                f"Estado: {row.status}",
                f"Descripción técnica: {row.rule_description}" if row.rule_description else "",
                f"Agente: {row.agent_name}" if row.agent_name else "",
                f"Regla Wazuh: {row.rule_id}" if row.rule_id else "",
            ] if part
        ])
        if pa_upsert_source_plan(
            source_ref=source_ref,
            origin="Cumplimiento Continuo - Wazuh",
            standard=row.standard,
            title=f"Remediar incumplimiento {row.standard} {row.control_code}",
            description=description,
            control_code=row.control_code,
            asset=row.agent_name or "",
            severity=row.severity or ("Alta" if row.status == "No cumple" else "Media"),
            action_type="Remediación de control",
            raw_json={"wazuh_compliance_control_id": row.id, "alert_id": row.alert_id},
        ):
            created += 1
    return created


def pa_sync_all_sources():
    created = 0
    errors = []
    sync_functions = [
        ("Mejora Continua", pa_sync_legacy_mejora),
        ("ISO 27001", pa_sync_iso_maturity),
        ("NIST CSF 2.0", pa_sync_nist_maturity),
        ("PCI-DSS", pa_sync_pci_maturity),
        ("SOC 2", pa_sync_soc2_maturity),
        ("Gestión de Riesgos", pa_sync_risk_existing_plans),
        ("Cumplimiento Continuo", pa_sync_continuous_controls),
        ("Wazuh", pa_sync_wazuh_compliance_controls),
    ]

    for label, function in sync_functions:
        try:
            new_records = int(function() or 0)
            db.session.commit()
            created += new_records
        except Exception as exc:
            db.session.rollback()
            errors.append(f"{label}: {exc}")

    return created, errors


def pa_render_page(content):
    return render_template_string(BASE, content=Markup(content))


@app.route("/planes_accion")
@login_required
def planes_accion_dashboard():
    user, response = pa_require_read()
    if response:
        return response

    sync_errors = []
    if pa_can_write(user):
        _, sync_errors = pa_sync_all_sources()

    standard = (request.args.get("standard") or "").strip().upper()
    origin = (request.args.get("origin") or "").strip()
    status = (request.args.get("status") or "").strip()
    search = (request.args.get("search") or "").strip()
    selected_plan_id = request.args.get("plan_id", type=int)

    query = ContinuousActionPlan.query
    if selected_plan_id:
        query = query.filter(ContinuousActionPlan.id == selected_plan_id)
    if standard:
        query = query.filter(ContinuousActionPlan.standard == standard)
    if origin:
        query = query.filter(ContinuousActionPlan.origin == origin)
    if search:
        like = f"%{search}%"
        query = query.filter(pa_or_(
            ContinuousActionPlan.title.ilike(like),
            ContinuousActionPlan.description.ilike(like),
            ContinuousActionPlan.control_code.ilike(like),
            ContinuousActionPlan.asset.ilike(like),
            ContinuousActionPlan.responsible.ilike(like),
        ))

    # El estado "Vencido" se calcula con la fecha objetivo; por eso todos los
    # filtros de estado se aplican sobre el estado efectivo y no únicamente
    # sobre el valor almacenado en la base de datos.
    today = date.today()
    plans = query.order_by(ContinuousActionPlan.id.desc()).limit(10000).all()
    if status:
        plans = [plan for plan in plans if pa_effective_status(plan, today) == status]
    plans = plans[:2000]
    all_plans = ContinuousActionPlan.query.order_by(ContinuousActionPlan.id.desc()).limit(10000).all()

    total = len(all_plans)
    effective_statuses = {
        plan.id: pa_effective_status(plan, today) for plan in all_plans
    }
    abiertos = sum(1 for p in all_plans if effective_statuses[p.id] == "Abierto")
    en_proceso = sum(1 for p in all_plans if effective_statuses[p.id] == "En proceso")
    cerrados = sum(1 for p in all_plans if effective_statuses[p.id] == "Cerrado")
    vencidos = sum(1 for p in all_plans if effective_statuses[p.id] == "Vencido")

    counts = {key: 0 for key in ["ISO27001", "SOC2", "PCIDSS", "NISTCSF", "RIESGOS", "MULTI"]}
    for plan in all_plans:
        key = (plan.standard or "").strip().upper()
        if key in counts:
            counts[key] += 1

    standards = [
        row[0] for row in db.session.query(ContinuousActionPlan.standard)
        .filter(ContinuousActionPlan.standard.isnot(None))
        .filter(ContinuousActionPlan.standard != "")
        .distinct().order_by(ContinuousActionPlan.standard.asc()).all()
    ]
    origins = [
        row[0] for row in db.session.query(ContinuousActionPlan.origin)
        .filter(ContinuousActionPlan.origin.isnot(None))
        .filter(ContinuousActionPlan.origin != "")
        .distinct().order_by(ContinuousActionPlan.origin.asc()).all()
    ]

    html = r'''
    <div class="pa-shell">
      <section class="pa-hero">
        <div class="pa-hero-icon"><i class="bi bi-clipboard2-check"></i></div>
        <div>
          <span class="pa-kicker">SGSI · Gestión transversal</span>
          <h1>Planes de Acción</h1>
          <p>Consolidación de acciones de ISO 27001, SOC 2, PCI-DSS, NIST CSF 2.0, Cumplimiento Continuo, Gobierno de Firewall y Gestión de Riesgos.</p>
        </div>
      </section>

      {% if sync_errors %}
      <div class="alert alert-warning small">
        Algunas fuentes no pudieron sincronizarse: {{ sync_errors|join(' · ') }}
      </div>
      {% endif %}

      <div class="pa-actions">
        {% if can_write %}
        <a href="{{ url_for('planes_accion_new') }}" class="pa-btn pa-btn-primary">
          <i class="bi bi-plus-circle"></i> Registrar plan de acción
        </a>
        <form method="post" action="{{ url_for('planes_accion_sync') }}" class="m-0">
          <button class="pa-btn pa-btn-light" type="submit">
            <i class="bi bi-arrow-repeat"></i> Actualizar fuentes
          </button>
        </form>
        {% endif %}
      </div>

      <div class="pa-kpi-grid">
        <div class="pa-kpi"><strong>{{ total }}</strong><span>Total de planes</span></div>
        <div class="pa-kpi"><strong>{{ abiertos }}</strong><span>Abiertos</span></div>
        <div class="pa-kpi"><strong>{{ en_proceso }}</strong><span>En proceso</span></div>
        <div class="pa-kpi"><strong>{{ cerrados }}</strong><span>Cerrados</span></div>
        <a class="pa-kpi pa-kpi-link danger" href="{{ url_for('planes_accion_dashboard', status='Vencido') }}" title="Ver cuáles planes están vencidos">
          <strong>{{ vencidos }}</strong><span>Vencidos · Ver planes</span>
        </a>
      </div>

      <div class="pa-standard-grid">
        <div><b>{{ counts.ISO27001 }}</b><span>ISO 27001</span></div>
        <div><b>{{ counts.SOC2 }}</b><span>SOC 2</span></div>
        <div><b>{{ counts.PCIDSS }}</b><span>PCI-DSS</span></div>
        <div><b>{{ counts.NISTCSF }}</b><span>NIST CSF 2.0</span></div>
        <div><b>{{ counts.RIESGOS }}</b><span>Gestión de Riesgos</span></div>
        <div><b>{{ counts.MULTI }}</b><span>Multiestándar</span></div>
      </div>

      <section class="pa-card">
        <form method="get" class="row g-2 align-items-end">
          <div class="col-lg-2 col-md-4">
            <label>Estándar / fuente</label>
            <select name="standard" class="form-select">
              <option value="">Todos</option>
              {% for value in standards %}
              <option value="{{ value }}" {% if standard == value %}selected{% endif %}>{{ standard_label(value) }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="col-lg-3 col-md-4">
            <label>Origen</label>
            <select name="origin" class="form-select">
              <option value="">Todos</option>
              {% for value in origins %}
              <option value="{{ value }}" {% if origin == value %}selected{% endif %}>{{ value }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="col-lg-2 col-md-4">
            <label>Estado</label>
            <select name="status" class="form-select">
              <option value="">Todos</option>
              {% for value in ['Abierto','En proceso','Vencido','Cerrado','Cancelado'] %}
              <option value="{{ value }}" {% if status == value %}selected{% endif %}>{{ value }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="col-lg-3 col-md-8">
            <label>Buscar</label>
            <input name="search" class="form-control" value="{{ search }}" placeholder="Título, control, activo o responsable">
          </div>
          <div class="col-lg-1 col-md-2"><button class="btn btn-primary w-100">Filtrar</button></div>
          <div class="col-lg-1 col-md-2"><a class="btn btn-outline-secondary w-100" href="{{ url_for('planes_accion_dashboard') }}">Limpiar</a></div>
        </form>
      </section>

      <section class="pa-card pa-table-card">
        <div class="table-responsive">
          <table class="table table-hover align-middle pa-table">
            <thead>
              <tr>
                <th>ID</th><th>Origen</th><th>Estándar</th><th>Control / riesgo</th>
                <th>Plan de acción</th><th>Tipo</th><th>Severidad</th>
                <th>Responsable</th><th>Fecha objetivo</th><th>Estado</th><th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {% for p in plans %}
              {% set effective = effective_status(p, today) %}
              <tr class="{% if effective == 'Vencido' %}pa-row-overdue{% endif %}">
                <td>{{ p.id }}</td>
                <td><span class="pa-origin">{{ p.origin or '—' }}</span></td>
                <td><span class="pa-standard">{{ standard_label(p.standard) }}</span></td>
                <td>{{ p.control_code or '—' }}</td>
                <td class="pa-plan-cell">
                  <strong>{{ p.title }}</strong>
                  {% if p.description %}<small>{{ p.description[:180] }}{% if p.description|length > 180 %}…{% endif %}</small>{% endif %}
                  {% if p.asset %}<em>Activo: {{ p.asset }}</em>{% endif %}
                </td>
                <td>{{ p.action_type or '—' }}</td>
                <td>{{ severity_badge(p.severity)|safe }}</td>
                <td>{{ p.responsible or '—' }}</td>
                <td>
                  {% set due = due_date_obj(p.due_date) %}
                  <span class="{% if due and due < today and not status_closed(p.status) %}text-danger fw-bold{% endif %}">
                    {{ p.due_date or '—' }}
                  </span>
                </td>
                <td>
                  {{ status_badge(effective)|safe }}
                  {% if effective == 'Vencido' %}
                    <small class="pa-overdue-note">Estado registrado: {{ p.status or 'Abierto' }}</small>
                  {% endif %}
                </td>
                <td>
                  <div class="d-flex flex-wrap gap-1 justify-content-center">
                    <a href="{{ url_for('planes_accion_edit', plan_id=p.id) }}" class="btn btn-sm btn-outline-primary">
                      {% if can_write %}Gestionar{% else %}Ver{% endif %}
                    </a>
                    {% if can_write %}
                    <form method="post" action="{{ url_for('planes_accion_delete', plan_id=p.id) }}" class="m-0"
                          onsubmit="return confirm('¿Confirma que desea eliminar este plan de acción? Esta operación no elimina el riesgo, hallazgo o registro de origen.');">
                      <button type="submit" class="btn btn-sm btn-outline-danger" title="Eliminar plan de acción">
                        <i class="bi bi-trash"></i> Eliminar
                      </button>
                    </form>
                    {% endif %}
                  </div>
                </td>
              </tr>
              {% else %}
              <tr><td colspan="11" class="text-center text-muted py-5">No hay planes de acción para los filtros seleccionados.</td></tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <style>
      body{background:#f3f7fb;}
      .pa-shell{width:96%;max-width:1750px;margin:22px auto 30px;}
      .pa-hero{display:flex;align-items:center;gap:14px;padding:17px 22px;border-radius:19px;color:#fff;background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);box-shadow:0 14px 30px rgba(15,23,42,.24);margin-bottom:14px;}
      .pa-hero-icon{width:56px;height:56px;min-width:56px;border-radius:15px;background:#fff;color:#0b4a8f;display:flex;align-items:center;justify-content:center;font-size:1.55rem;box-shadow:0 8px 18px rgba(0,0,0,.2);}
      .pa-kicker{display:inline-block;padding:3px 10px;border:1px solid rgba(255,255,255,.3);background:rgba(255,255,255,.14);border-radius:999px;font-size:.66rem;font-weight:900;}
      .pa-hero h1{font-size:1.45rem!important;margin:4px 0 2px!important;color:#fff!important;font-weight:950;}
      .pa-hero p{margin:0;color:rgba(255,255,255,.92);font-size:.82rem;}
      .pa-actions{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 14px;}
      .pa-btn{display:inline-flex;align-items:center;gap:8px;text-decoration:none;border:none;border-radius:11px;padding:9px 15px;font-size:.82rem;font-weight:900;box-shadow:0 7px 16px rgba(15,23,42,.12);}
      .pa-btn-primary{background:linear-gradient(135deg,#086df0,#2487ff);color:#fff;}
      .pa-btn-light{background:#fff;color:#0b4a8f;border:1px solid #cedbea;}
      .pa-kpi-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:11px;margin-bottom:11px;}
      .pa-kpi{background:#fff;border:1px solid #dde7f2;border-radius:16px;padding:13px 15px;box-shadow:0 9px 20px rgba(15,23,42,.10);display:flex;flex-direction:column;}
      .pa-kpi-link{text-decoration:none!important;transition:transform .18s ease,box-shadow .18s ease}.pa-kpi-link:hover{transform:translateY(-2px);box-shadow:0 13px 26px rgba(15,23,42,.16)}
      .pa-kpi strong{font-size:1.45rem;color:#0b4a8f;line-height:1;}.pa-kpi span{font-size:.72rem;color:#526173;font-weight:850;margin-top:5px}.pa-kpi.danger strong{color:#b42318;}
      .pa-standard-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px;margin-bottom:13px;}
      .pa-standard-grid div{background:#eaf3ff;border:1px solid #cfe0f5;border-radius:13px;padding:10px 12px;display:flex;justify-content:space-between;align-items:center;gap:8px;}
      .pa-standard-grid b{color:#0b4a8f;font-size:1.05rem}.pa-standard-grid span{font-size:.69rem;color:#334155;font-weight:850;text-align:right;}
      .pa-card{background:rgba(255,255,255,.98);border:1px solid #dce6f1;border-radius:18px;padding:14px 16px;box-shadow:0 11px 24px rgba(15,23,42,.12);margin-bottom:14px;}
      .pa-card label{font-size:.75rem;font-weight:900;color:#334155;margin-bottom:4px}.pa-card .form-control,.pa-card .form-select{min-height:36px;border-radius:10px;font-size:.78rem;border:1px solid #cfdbea;}
      .pa-table-card{padding:0;overflow:hidden}.pa-table{margin:0;min-width:1500px;font-size:.76rem}.pa-table thead th{background:#eaf3ff;color:#062b55;font-weight:950;text-align:center;white-space:nowrap;padding:9px 7px}.pa-table td{padding:7px;vertical-align:middle;border-color:#e5edf6}.pa-plan-cell{min-width:320px;max-width:470px}.pa-plan-cell strong,.pa-plan-cell small,.pa-plan-cell em{display:block}.pa-plan-cell small{color:#475569;margin-top:3px;white-space:pre-line}.pa-plan-cell em{font-size:.68rem;color:#64748b;margin-top:3px}.pa-origin,.pa-standard{display:inline-block;border-radius:999px;padding:4px 8px;background:#eef4fb;color:#0b4a8f;font-weight:850;white-space:nowrap;}
      .pa-row-overdue td{background:#fff5f4!important;border-top-color:#f5c2c0!important;border-bottom-color:#f5c2c0!important}.pa-row-overdue:hover td{background:#ffeceb!important}.pa-overdue-note{display:block;color:#9f1c14;font-size:.64rem;font-weight:800;margin-top:4px;white-space:nowrap}
      @media(max-width:1050px){.pa-kpi-grid{grid-template-columns:repeat(2,1fr)}.pa-standard-grid{grid-template-columns:repeat(2,1fr)}}
    </style>
    '''

    inner = render_template_string(
        html,
        plans=plans,
        total=total,
        abiertos=abiertos,
        en_proceso=en_proceso,
        cerrados=cerrados,
        vencidos=vencidos,
        counts=counts,
        standards=standards,
        origins=origins,
        standard=standard,
        origin=origin,
        status=status,
        search=search,
        sync_errors=sync_errors,
        can_write=pa_can_write(user),
        standard_label=pa_standard_label,
        status_badge=pa_badge_status,
        effective_status=pa_effective_status,
        severity_badge=pa_badge_severity,
        due_date_obj=pa_due_date_obj,
        status_closed=pa_status_closed,
        today=today,
    )
    return pa_render_page(inner)


@app.route("/planes_accion/sincronizar", methods=["POST"])
@login_required
def planes_accion_sync():
    user, response = pa_require_write()
    if response:
        return response
    created, errors = pa_sync_all_sources()
    if errors:
        flash(f"Sincronización terminada con observaciones. Nuevos planes: {created}. " + " | ".join(errors), "warning")
    else:
        flash(f"Fuentes actualizadas correctamente. Nuevos planes incorporados: {created}.", "success")
    registrar_log(pa_username(user), f"Sincronizó las fuentes del capítulo Plan de Acción. Nuevos registros: {created}.")
    return redirect(url_for("planes_accion_dashboard"))


@app.route("/planes_accion/nuevo", methods=["GET", "POST"])
@login_required
def planes_accion_new():
    user, response = pa_require_write()
    if response:
        return response

    risk_id = request.values.get("riesgo_id", type=int)
    risk = Riesgo.query.get(risk_id) if risk_id else None

    defaults = {
        "origin": "Gestión de Riesgos" if risk else "Registro manual",
        "standard": "RIESGOS" if risk else "SGSI",
        "control_code": (risk.codigo_riesgo or str(risk.id)) if risk else "",
        "title": f"Tratamiento del riesgo {risk.codigo_riesgo or risk.id}" if risk else "",
        "description": "",
        "asset": (risk.nombre_activo or risk.activo or "") if risk else "",
        "severity": pa_risk_severity(risk) if risk else "Media",
        "action_type": "Tratamiento de riesgo" if risk else "Correctiva",
        "responsible": (risk.responsable or risk.propietario_riesgo or "") if risk else "",
        "due_date": (risk.fecha_implementacion or "") if risk else "",
        "status": "Abierto",
    }

    if risk:
        defaults["description"] = "\n\n".join([
            part for part in [
                f"Riesgo: {risk.riesgo}" if risk.riesgo else "",
                f"Amenaza: {risk.amenaza}" if risk.amenaza else "",
                f"Vulnerabilidad: {risk.vulnerabilidad}" if risk.vulnerabilidad else "",
                f"Riesgo inherente: {risk.riesgo_inherente}" if risk.riesgo_inherente else "",
                f"Riesgo residual: {risk.riesgo_residual}" if risk.riesgo_residual else "",
                f"Tratamiento definido: {risk.tratamiento_riesgo}" if risk.tratamiento_riesgo else "",
                f"Plan existente: {risk.planes_accion or risk.plan_accion}" if (risk.planes_accion or risk.plan_accion) else "",
            ] if part
        ])

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        if not title:
            flash("El título del plan de acción es obligatorio.", "danger")
        else:
            source_ref = (
                f"riesgo-manual:{risk_id}:{uuid.uuid4().hex}"
                if risk_id else f"manual:{uuid.uuid4().hex}"
            )
            values = {
                "origin": (request.form.get("origin") or defaults["origin"]).strip(),
                "standard": (request.form.get("standard") or defaults["standard"]).strip().upper(),
                "control_code": (request.form.get("control_code") or "").strip(),
                "title": title[:500],
                "description": (request.form.get("description") or "").strip(),
                "asset": (request.form.get("asset") or "").strip(),
                "severity": (request.form.get("severity") or "Media").strip(),
                "action_type": (request.form.get("action_type") or "Correctiva").strip(),
                "responsible": (request.form.get("responsible") or "").strip(),
                "due_date": (request.form.get("due_date") or "").strip(),
                "status": (request.form.get("status") or "Abierto").strip(),
            }
            duplicate = pa_find_duplicate_plan(values, source_ref=source_ref)
            if duplicate:
                flash(
                    f"El plan de acción ya existe con el ID {duplicate.id}. "
                    "No se creó un registro repetido.",
                    "warning",
                )
                return redirect(url_for("planes_accion_edit", plan_id=duplicate.id))

            plan = ContinuousActionPlan(
                **values,
                source_ref=source_ref,
                raw_json=json.dumps({"riesgo_id": risk_id, "creado_por": pa_username(user)}, ensure_ascii=False),
            )
            db.session.add(plan)
            db.session.commit()
            registrar_log(pa_username(user), f"Registró el plan de acción {plan.id}: {plan.title}.")
            flash("Plan de acción registrado correctamente.", "success")
            return redirect(url_for("planes_accion_dashboard"))

    html = r'''
    <div class="pa-form-shell">
      <div class="pa-form-hero">
        <div><span>SGSI · Plan de Acción</span><h1>Registrar plan de acción</h1><p>Defina la actividad, su origen, responsable, fecha objetivo y estado de seguimiento.</p></div>
      </div>
      <div class="pa-form-actions"><a href="{{ url_for('planes_accion_dashboard') }}" class="btn btn-outline-secondary"><i class="bi bi-arrow-left"></i> Volver</a></div>
      {% if risk %}
      <div class="alert alert-info"><strong>Riesgo asociado:</strong> {{ risk.codigo_riesgo or risk.id }} · {{ risk.riesgo }}</div>
      {% endif %}
      <form method="post" class="pa-form-card">
        <input type="hidden" name="riesgo_id" value="{{ risk.id if risk else '' }}">
        <div class="row g-3">
          <div class="col-md-3"><label>Origen</label><input class="form-control" name="origin" value="{{ defaults.origin }}" required></div>
          <div class="col-md-3"><label>Estándar / ámbito</label><select class="form-select" name="standard">{% for value,label in standards %}<option value="{{ value }}" {% if defaults.standard == value %}selected{% endif %}>{{ label }}</option>{% endfor %}</select></div>
          <div class="col-md-3"><label>Control / código de riesgo</label><input class="form-control" name="control_code" value="{{ defaults.control_code }}"></div>
          <div class="col-md-3"><label>Activo relacionado</label><input class="form-control" name="asset" value="{{ defaults.asset }}"></div>
          <div class="col-12"><label>Título del plan</label><input class="form-control" name="title" value="{{ defaults.title }}" required></div>
          <div class="col-12"><label>Descripción y actividades</label><textarea class="form-control" name="description" rows="8">{{ defaults.description }}</textarea></div>
          <div class="col-md-3"><label>Tipo de acción</label><select class="form-select" name="action_type">{% for value in ['Correctiva','Mejora','Remediación','Tratamiento de riesgo','Plan de cumplimiento','Incidente','Hallazgo'] %}<option {% if defaults.action_type == value %}selected{% endif %}>{{ value }}</option>{% endfor %}</select></div>
          <div class="col-md-2"><label>Severidad</label><select class="form-select" name="severity">{% for value in ['Crítica','Alta','Media','Baja'] %}<option {% if defaults.severity == value %}selected{% endif %}>{{ value }}</option>{% endfor %}</select></div>
          <div class="col-md-3"><label>Responsable</label><input class="form-control" name="responsible" value="{{ defaults.responsible }}"></div>
          <div class="col-md-2"><label>Fecha objetivo</label><input type="date" class="form-control" name="due_date" value="{{ defaults.due_date }}"></div>
          <div class="col-md-2"><label>Estado</label><select class="form-select" name="status">{% for value in ['Abierto','En proceso','Cerrado','Cancelado'] %}<option {% if defaults.status == value %}selected{% endif %}>{{ value }}</option>{% endfor %}</select></div>
        </div>
        <div class="mt-4"><button class="btn btn-primary px-4"><i class="bi bi-save"></i> Guardar plan de acción</button></div>
      </form>
    </div>
    <style>
      body{background:#f3f7fb}.pa-form-shell{width:94%;max-width:1250px;margin:22px auto 30px}.pa-form-hero{background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);color:#fff;border-radius:18px;padding:17px 23px;box-shadow:0 14px 28px rgba(15,23,42,.22)}.pa-form-hero span{font-size:.67rem;font-weight:900;background:rgba(255,255,255,.16);border-radius:999px;padding:3px 9px}.pa-form-hero h1{color:#fff!important;font-size:1.4rem!important;margin:5px 0 2px!important}.pa-form-hero p{margin:0;font-size:.82rem;color:rgba(255,255,255,.92)}.pa-form-actions{margin:12px 0}.pa-form-card{background:#fff;border:1px solid #dce6f1;border-radius:18px;padding:20px;box-shadow:0 12px 25px rgba(15,23,42,.12)}.pa-form-card label{font-size:.77rem;font-weight:900;color:#334155;margin-bottom:4px}.pa-form-card .form-control,.pa-form-card .form-select{border-radius:10px;border:1px solid #cfdbea;font-size:.82rem}
    </style>
    '''
    inner = render_template_string(
        html,
        risk=risk,
        defaults=defaults,
        standards=[
            ("SGSI", "Sistema de Gestión"), ("ISO27001", "ISO 27001"),
            ("SOC2", "SOC 2"), ("PCIDSS", "PCI-DSS"),
            ("NISTCSF", "NIST CSF 2.0"), ("RIESGOS", "Gestión de Riesgos"),
            ("MULTI", "Múltiples estándares"),
        ],
    )
    return pa_render_page(inner)


