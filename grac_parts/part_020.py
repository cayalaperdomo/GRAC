@ai_madurez_bp.route("/guardar", methods=["POST"])
@login_required
def guardar():
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user) or user.role == "auditor":
        flash("No tiene permiso para guardar información del módulo de Gestión de IA.", "danger")
        return redirect(url_for("madurez_ai.home"))

    preguntas = ai_cargar_preguntas()
    if not preguntas:
        flash("⚠️ Primero debes importar el instrumento ISO 42001.", "warning")
        return redirect(url_for("madurez_ai.parametros"))

    consecutivo = (request.form.get("consecutivo") or "").strip()
    if not consecutivo:
        flash("⚠️ Debes ingresar el consecutivo de revisión.", "warning")
        return redirect(url_for("madurez_ai.ingreso"))

    accion = (request.form.get("accion") or "borrador").strip().lower()
    estado_run = "FINALIZADO" if accion in ("finalizar", "analizar") else "BORRADOR"

    respondidas, total, progreso_pct = ai_calcular_progreso(
        preguntas,
        form_data=request.form
    )

    if estado_run == "FINALIZADO" and progreso_pct < 100:
        flash("⚠️ Para finalizar debes responder todas las preguntas del instrumento.", "warning")
        return redirect(url_for("madurez_ai.ingreso"))

    draft = ai_obtener_borrador(user.id)
    conn = get_ai_madurez_conn()
    cur = conn.cursor()
    now = _ai_now()

    if draft:
        run_id = int(draft["id"])
        cur.execute("""
            UPDATE ai_madurez_runs
            SET consecutivo = ?,
                updated_at = ?,
                estado = ?,
                progreso_pct = ?
            WHERE id = ?
        """, (
            consecutivo,
            now,
            estado_run,
            progreso_pct,
            run_id
        ))
    else:
        cur.execute("""
            INSERT INTO ai_madurez_runs
            (
                created_at,
                updated_at,
                consecutivo,
                user_id,
                estado,
                progreso_pct,
                resumen_json,
                pct_general,
                radar_overall_b64
            )
            VALUES (?, ?, ?, ?, ?, ?, '{}', 0, NULL)
        """, (
            now,
            now,
            consecutivo,
            user.id,
            estado_run,
            progreso_pct
        ))
        run_id = cur.lastrowid

    for q in preguntas:
        qid = int(q["id"])
        estado = _ai_estado_normalizado(request.form.get(f"st_{qid}"))
        comentario = (
            request.form.get(f"cm_{qid}")
            or request.form.get(f"com_{qid}")
            or ""
        ).strip()

        if estado not in ("SI", "PARCIAL", "NO", "NA"):
            cur.execute("""
                DELETE FROM ai_madurez_respuestas
                WHERE run_id = ? AND pregunta_id = ?
            """, (run_id, qid))
            continue

        cur.execute("""
            INSERT INTO ai_madurez_respuestas
            (
                run_id,
                pregunta_id,
                estado,
                comentario
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id, pregunta_id)
            DO UPDATE SET
                estado = excluded.estado,
                comentario = excluded.comentario
        """, (
            run_id,
            qid,
            estado,
            comentario
        ))

    conn.commit()
    conn.close()

    # Recalcula desde respuestas reales.
    # N/A queda excluido del denominador.
    resumen, pct_general = ai_recalcular_y_actualizar_run(run_id)

    if estado_run == "FINALIZADO":
        flash("✅ Evaluación finalizada y analizada correctamente.", "success")
        return redirect(url_for("madurez_ai.detalle", run_id=run_id))

    flash("✅ Borrador guardado correctamente.", "success")
    return redirect(url_for("madurez_ai.ingreso"))


# ============================================================================================================================================
# HISTORIAL — GESTIÓN DE INTELIGENCIA ARTIFICIAL ISO 42001
# ============================================================================================================================================

@ai_madurez_bp.route("/historial", methods=["GET"])
@login_required
def historial():
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para consultar el historial de Gestión de IA.", "danger")
        return redirect(url_for("menu"))

    conn = get_ai_madurez_conn()

    if user.role == "admin":
        rows = conn.execute("""
            SELECT *
            FROM ai_madurez_runs
            ORDER BY created_at DESC, id DESC
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT *
            FROM ai_madurez_runs
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
        """, (user.id,)).fetchall()

    conn.close()

    trs = ""

    for r in rows:
        nivel = ai_nivel_visual_por_pct(r["pct_general"])
        estado = (r["estado"] or "").upper().strip()
        estado_badge = "success" if estado == "FINALIZADO" else "warning text-dark"

        pdf_btn = ""
        delete_btn = ""

        if user.role != "auditor":
            pdf_btn = f"""
            <a href="{url_for('madurez_ai.exportar_pdf', run_id=r['id'])}"
               class="btn btn-sm aihis-btn-pdf"
               title="Exportar PDF">
              <i class="bi bi-file-earmark-pdf-fill me-1"></i>PDF
            </a>
            """

            delete_btn = f"""
            <form method="POST"
                  action="{url_for('madurez_ai.eliminar_revision', run_id=r['id'])}"
                  class="d-inline"
                  onsubmit="return confirm('¿Está seguro de eliminar esta revisión? Esta acción no se puede deshacer.');">
              <button type="submit"
                      class="btn btn-sm aihis-btn-delete"
                      title="Eliminar revisión">
                <i class="bi bi-trash-fill me-1"></i>Eliminar
              </button>
            </form>
            """

        trs += f"""
        <tr>
          <td class="fw-bold text-center">{r["id"]}</td>

          <td class="fw-bold">
            {escape(r["consecutivo"] or "")}
          </td>

          <td>
            {escape(r["created_at"] or "")}
          </td>

          <td class="text-center">
            <span class="badge bg-{estado_badge} rounded-pill px-3">
              {escape(r["estado"] or "")}
            </span>
          </td>

          <td class="text-center fw-bold">
            {float(r["pct_general"] or 0):.2f}%
          </td>

          <td class="text-center">
            <span class="badge rounded-pill px-3 py-2"
                  style="background:{nivel.get("color", "#6c757d")}; color:#fff;">
              {escape(nivel.get("nivel", ""))}
            </span>
          </td>

          <td class="text-center">
            <div class="aihis-actions">
              <a href="{url_for('madurez_ai.detalle', run_id=r['id'])}"
                 class="btn btn-sm aihis-btn-view"
                 title="Ver detalle">
                <i class="bi bi-eye-fill me-1"></i>Ver
              </a>

              {pdf_btn}
              {delete_btn}
            </div>
          </td>
        </tr>
        """

    if not trs:
        trs = """
        <tr>
          <td colspan="7" class="text-center text-muted py-4">
            No hay revisiones registradas.
          </td>
        </tr>
        """

    content = f"""
<div class="aihis-shell">

  {ai_header(
      "aihis",
      "Historial de Revisiones — Gestión de IA",
      "Consulta las evaluaciones de madurez registradas del Sistema de Gestión de Inteligencia Artificial.",
      "🕘",
      "SGSI · Historial ISO 42001"
  )}

  <div class="aihis-header-actions">
    <a href="{url_for('madurez_ai.home')}"
       class="btn aihis-btn-main rounded-pill px-4 fw-bold">
      <i class="bi bi-arrow-left me-2"></i>Volver
    </a>
  </div>

  <div class="aihis-card p-4">
    <div class="table-responsive aihis-table-wrap">
      <table class="table table-sm align-middle mb-0 aihis-table">
        <thead>
          <tr>
            <th style="width:70px;">ID</th>
            <th>Consecutivo</th>
            <th style="width:180px;">Fecha</th>
            <th style="width:130px;">Estado</th>
            <th style="width:120px;">% General</th>
            <th style="width:220px;">Nivel</th>
            <th style="width:260px;">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {trs}
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

  .aihis-shell{{
    width:96%;
    max-width:1500px;
    margin:26px auto 24px auto;
  }}

  .aihis-header-actions{{
    display:flex;
    justify-content:center;
    gap:10px;
    flex-wrap:wrap;
    margin:10px 0 14px;
  }}

  .aihis-card{{
    background:rgba(255,255,255,.96) !important;
    border-radius:18px !important;
    backdrop-filter:blur(8px);
    box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
    border:1px solid rgba(219,230,244,.9) !important;
  }}

  .aihis-btn-main{{
    background:#ffffff;
    color:#0f172a !important;
    border:1px solid #cfd8e3 !important;
    border-radius:10px !important;
    font-weight:900;
    box-shadow:0 4px 10px rgba(0,0,0,.08);
  }}

  .aihis-btn-main:hover{{
    background:#edf5ff;
    color:#0b65d8 !important;
  }}

  .aihis-table-wrap{{
    max-height:72vh;
    overflow:auto;
    border-radius:14px;
  }}

  .aihis-table thead th{{
    position:sticky;
    top:0;
    z-index:3;
    background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
    color:#ffffff !important;
    font-size:.78rem;
    font-weight:950;
    text-align:center;
    vertical-align:middle;
    padding:12px 10px;
  }}

  .aihis-table tbody td{{
    font-size:.84rem;
    vertical-align:middle;
    padding:11px 10px;
  }}

  .aihis-actions{{
    display:flex;
    justify-content:center;
    align-items:center;
    gap:6px;
    flex-wrap:wrap;
  }}

  .aihis-actions .btn{{
    min-height:36px;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    border-radius:10px !important;
    font-weight:900;
    box-shadow:0 4px 10px rgba(0,0,0,.10);
    padding:6px 12px !important;
    font-size:.68rem !important;
    gap:4px;
    white-space:nowrap;
  }}

  .aihis-btn-view{{
    background:#0d6efd !important;
    color:#ffffff !important;
    border:1px solid #0d6efd !important;
  }}

  .aihis-btn-view:hover{{
    background:#0b5ed7 !important;
    color:#ffffff !important;
  }}

  .aihis-btn-pdf{{
    background:#dc3545 !important;
    color:#ffffff !important;
    border:1px solid #dc3545 !important;
  }}

  .aihis-btn-pdf:hover{{
    background:#bb2d3b !important;
    color:#ffffff !important;
  }}

  .aihis-btn-delete{{
    background:#212529 !important;
    color:#ffffff !important;
    border:1px solid #212529 !important;
  }}

  .aihis-btn-delete:hover{{
    background:#000000 !important;
    color:#ffffff !important;
  }}

  @media (max-width:768px){{
    .aihis-shell{{
      width:98%;
      margin:12px auto 22px auto;
    }}

    .aihis-header-actions .btn{{
      width:100%;
    }}

    .aihis-actions{{
      gap:6px;
    }}

    .aihis-actions .btn{{
      width:100%;
    }}
  }}
</style>
"""

    return render_template_string(BASE, title="Historial Madurez IA", content=content)


# ============================================================================================================================================
# ELIMINAR REVISIÓN — GESTIÓN DE INTELIGENCIA ARTIFICIAL ISO 42001
# ============================================================================================================================================

@ai_madurez_bp.route("/historial/eliminar/<int:run_id>", methods=["POST"])
@login_required
def eliminar_revision(run_id):
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para eliminar revisiones de Gestión de IA.", "danger")
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede eliminar revisiones.", "warning")
        return redirect(url_for("madurez_ai.historial"))

    conn = get_ai_madurez_conn()
    run = conn.execute(
        "SELECT * FROM ai_madurez_runs WHERE id = ?",
        (run_id,)
    ).fetchone()

    if not run:
        conn.close()
        flash("No se encontró la revisión solicitada.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    if user.role != "admin" and run["user_id"] != user.id:
        conn.close()
        flash("No tiene permiso para eliminar esta revisión.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    try:
        conn.execute("DELETE FROM ai_madurez_respuestas WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM ai_madurez_runs WHERE id = ?", (run_id,))
        conn.commit()
        flash("Revisión eliminada correctamente.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"No se pudo eliminar la revisión: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("madurez_ai.historial"))


# ================
# Detalle — Gestión de Inteligencia Artificial ISO 42001
# ================

@ai_madurez_bp.route("/detalle/<int:run_id>", methods=["GET"])
@login_required
def detalle(run_id):
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para consultar el detalle de Gestión de IA.", "danger")
        return redirect(url_for("menu"))

    conn = get_ai_madurez_conn()
    run = conn.execute(
        "SELECT * FROM ai_madurez_runs WHERE id = ?",
        (run_id,)
    ).fetchone()
    conn.close()

    if not run:
        flash("No se encontró la revisión solicitada.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    if user.role != "admin" and run["user_id"] != user.id:
        flash("No tiene permiso para consultar esta revisión.", "danger")
        return redirect(url_for("madurez_ai.historial"))
    # Recalcular siempre desde respuestas reales.
    # N/A cuenta como respondida para progreso, pero NO cuenta en porcentaje.
    resumen, pct_general_recalculado = ai_recalcular_y_actualizar_run(run_id)

    conn = get_ai_madurez_conn()
    run = conn.execute(
        "SELECT * FROM ai_madurez_runs WHERE id = ?",
        (run_id,)
    ).fetchone()
    conn.close()

    resumen_raw = resumen

    resumen = {}
    for cap, cats in (resumen_raw or {}).items():
        cap_limpio = _ai_codigo_limpio(cap)
        resumen.setdefault(cap_limpio, {})

        for cat_code, d in (cats or {}).items():
            cat_limpio = _ai_codigo_limpio(cat_code)
            data = dict(d or {})

            if not data.get("categoria"):
                data["categoria"] = _ai_codigo_visible(cat_limpio)

            resumen[cap_limpio][cat_limpio] = data

    def _nl2br_ai(s: str) -> str:
        txt = _ai_limpiar_texto_rico_guardado(s or "")
        return txt.replace("\n", "<br>")

    def _clip(v, max_len=92):
        txt = (v or "").strip()
        if len(txt) <= max_len:
            return txt
        return txt[:max_len].rstrip() + "..."

    informe_ai = _ai_limpiar_texto_rico_guardado(run["informe_ejecutivo_ai"] or "")
    informe_editado = _ai_limpiar_texto_rico_guardado(run["informe_ejecutivo_editado"] or "")
    informe_mostrar = informe_editado if informe_editado else informe_ai

    nivel_general = ai_nivel_visual_por_pct(run["pct_general"])
    nivel_general_texto = (nivel_general.get("nivel") or "").strip()
    nivel_general_nombre = (
        nivel_general_texto.split(":", 1)[1].strip()
        if ":" in nivel_general_texto
        else nivel_general_texto
    )

    read_only = user.role == "auditor"

    pdf_btn = ""
    if not read_only:
        pdf_btn = f"""
        <a href="{url_for('madurez_ai.exportar_pdf', run_id=run_id)}"
           class="btn aidet-btn-danger grac-nav-blue-btn rounded-pill px-4 fw-bold">
          <i class="bi bi-file-earmark-pdf me-2"></i>Exportar PDF
        </a>
        """

    if read_only:
        informe_btns = """
        <button type="button"
                class="btn btn-secondary rounded-pill px-4 fw-bold"
                disabled
                title="El perfil Auditor no puede generar IA">
          <i class="bi bi-magic me-2"></i>Generar con IA
        </button>

        <button type="button"
                class="btn btn-secondary rounded-pill px-4 fw-bold"
                disabled
                title="El perfil Auditor no puede editar">
          <i class="bi bi-pencil-square me-2"></i>Editar
        </button>
        """
    else:
        informe_btns = f"""
        <form method="POST"
              action="{url_for('madurez_ai.informe_ejecutivo_generar', run_id=run_id)}"
              class="m-0"
              data-progress-text="Generando informe ejecutivo con IA..."
              onsubmit="return ai42001Progress('Generando informe ejecutivo con IA...');">
          <button type="submit"
                  class="btn aidet-btn-success rounded-pill px-4 fw-bold">
            <i class="bi bi-magic me-2"></i>Generar con IA
          </button>
        </form>

        <a href="{url_for('madurez_ai.informe_ejecutivo_editar', run_id=run_id)}"
           class="btn btn-primary rounded-pill px-4 fw-bold"
           data-no-progress="true">
          <i class="bi bi-pencil-square me-2"></i>Editar
        </a>
        """

    top_html = f"""
    <div class="row g-3 mb-4">
      <div class="col-12 col-xl-5">
        <div class="aidet-card p-4 h-100">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
            <div class="aidet-title-block">
              <div class="aidet-card-title">📌 Resultado General de Madurez</div>
              <div class="text-muted small">
                Resultado consolidado del Sistema de Gestión de Inteligencia Artificial.
              </div>
            </div>

            <div class="text-end">
              <div class="badge rounded-pill px-3 py-2"
                   style="background:{nivel_general.get('color','#6c757d')}; color:#fff; font-size:.82rem;">
                Nivel {nivel_general.get('score', 0)}
              </div>
              <div class="small text-muted mt-1 aidet-soft-text">{escape(nivel_general_nombre)}</div>
            </div>
          </div>

          <div class="aidet-general-score-box mt-4">
            <div class="aidet-general-score-label">Cumplimiento general</div>
            <div class="aidet-general-score-value">{float(run["pct_general"] or 0):.2f}%</div>
            <div class="aidet-general-score-subtitle">
              Consecutivo: <b>{escape(run["consecutivo"] or "")}</b>
            </div>
          </div>

          <div class="row g-3 mt-2">
            <div class="col-12 col-md-6">
              <div class="aidet-mini-kpi">
                <div class="aidet-mini-kpi-label">Estado</div>
                <div class="aidet-mini-kpi-value">{escape(run["estado"] or "")}</div>
              </div>
            </div>

            <div class="col-12 col-md-6">
              <div class="aidet-mini-kpi">
                <div class="aidet-mini-kpi-label">Fecha</div>
                <div class="aidet-mini-kpi-value">{escape((run["created_at"] or "")[:16])}</div>
              </div>
            </div>
          </div>

          <div class="alert alert-info mt-3 mb-0 small rounded-4 border-0">
            <b>Lectura ejecutiva:</b> este resultado refleja el nivel de implementación,
            documentación, gestión y mejora continua del sistema de gestión de IA evaluado.
          </div>
        </div>
      </div>

      <div class="col-12 col-xl-7">
        <div class="aidet-card p-4 h-100">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div class="aidet-title-block">
              <div class="aidet-card-title">🧾 Informe ejecutivo</div>
              <div class="text-muted small">
                Síntesis ejecutiva generada con IA a partir de los resultados por capítulo y categoría.
              </div>
            </div>

            <div class="d-flex gap-2 flex-wrap">
              {informe_btns}
            </div>
          </div>

          <div class="aidet-exec-box mt-3">
              {
                  (
                      f'<div class="aidet-exec-text">{_nl2br_ai(escape(informe_mostrar))}</div>'
                  )
                  if informe_mostrar
                  else
                  (
                      '<div class="text-center py-4">'
                      '<div class="mb-2" style="font-size:2rem;">&#129302;</div>'
                      '<div class="fw-bold text-black">Aún no hay informe ejecutivo</div>'
                      '<div class="text-muted small mt-1">'
                      'Presiona <b>Generar con IA</b> para construir el informe con base '
                      'en el resultado del Sistema de Gestión de Inteligencia Artificial.'
                      '</div>'
                      '</div>'
                  )
              }
            </div>
        </div>
      </div>
    </div>
    """

    def gauge_svg_categoria(pct, color="#2f6fb6"):
        try:
            pct = max(0, min(100, float(pct or 0)))
        except Exception:
            pct = 0.0

        radius = 43
        circumference = math.pi * radius
        progress = circumference * (pct / 100.0)

        return f"""
        <svg class="aidet-gauge-svg" viewBox="0 0 128 84" aria-hidden="true">
          <path d="M21 66 A43 43 0 0 1 107 66"
                fill="none"
                stroke="#e6edf6"
                stroke-width="11"
                stroke-linecap="round"/>

          <path d="M21 66 A43 43 0 0 1 107 66"
                fill="none"
                stroke="{color}"
                stroke-width="11"
                stroke-linecap="round"
                stroke-dasharray="{progress:.2f} {circumference:.2f}"/>

          <circle cx="64" cy="66" r="4.5" fill="{color}"/>

          <text x="64" y="49"
                text-anchor="middle"
                style="font-size:16px;font-weight:950;fill:#0b1220;">
            {pct:.0f}%
          </text>

          <text x="22" y="80"
                text-anchor="middle"
                style="font-size:9px;font-weight:800;fill:#475569;">
            0
          </text>

          <text x="106" y="80"
                text-anchor="middle"
                style="font-size:9px;font-weight:800;fill:#475569;">
            100
          </text>
        </svg>
        """

    cap_order = []
    for cap in AI_CAP_ORDER_DEFAULT:
        cap_key = _ai_codigo_limpio(cap)
        if cap_key in (resumen or {}):
            cap_order.append(cap_key)

    for cap in (resumen or {}).keys():
        if cap not in cap_order:
            cap_order.append(cap)

    detalle_cards = []

    for cap in cap_order:
        cats = (resumen or {}).get(cap, {}) or {}
        if not cats:
            continue

        for cat_code, d in cats.items():
            cat_code_limpio = _ai_codigo_limpio(cat_code)
            cat_visible = _ai_codigo_visible(cat_code_limpio)

            pct = float(d.get("pct", 0) or 0)
            total = int(d.get("total", 0) or 0)
            nombre_categoria = (d.get("categoria") or cat_visible).strip()
            nivel_data = ai_nivel_visual_por_pct(pct)

            nivel_score = nivel_data.get("score", "")
            nivel_texto = (nivel_data.get("nivel") or "").strip()
            nivel_nombre = (
                nivel_texto.split(":", 1)[1].strip()
                if ":" in nivel_texto
                else nivel_texto
            )

            gauge_html = gauge_svg_categoria(pct, nivel_data.get("color", "#2f6fb6"))

            detalle_cards.append(f"""
            <div class="aidet-gauge-card">
              <div class="aidet-gauge-head">
                <span class="aidet-cat-code" title="{escape(_ai_codigo_visible(cap))}">
                  {escape(_clip(_ai_codigo_visible(cap), 42))}
                </span>
                <span class="aidet-items-pill">{total} ítems</span>
              </div>

              <div class="aidet-cat-subcode" title="{escape(cat_visible)}">
                {escape(_clip(cat_visible, 42))}
              </div>

              <div class="aidet-gauge-area">
                {gauge_html}
              </div>

              <div class="aidet-cat-name" title="{escape(nombre_categoria)}">
                {escape(_clip(nombre_categoria or cat_visible, 95))}
              </div>

              <div class="aidet-level-row">
                <span class="nivel-dot" style="background-color:{nivel_data.get('color','#6c757d')} !important;"></span>
                <span class="aidet-level-main">Nivel {nivel_score}</span>
              </div>

              <div class="aidet-level-name" title="{escape(nivel_nombre)}">
                {escape(_clip(nivel_nombre, 65))}
              </div>

              <div class="aidet-card-actions">
                <a class="btn btn-sm btn-outline-primary rounded-pill aidet-action-btn"
                   href="{url_for('madurez_ai.detalle_categoria', run_id=run_id, cap=_ai_codigo_limpio(cap).upper(), cat_code=cat_code_limpio.upper())}"
                   data-no-progress="true">
                  <i class="bi bi-list-check me-1"></i>Ver preguntas
                </a>

                <a class="btn btn-sm btn-outline-dark rounded-pill aidet-action-btn"
                   href="{url_for('madurez_ai.analisis_categoria', run_id=run_id, cap=_ai_codigo_limpio(cap).upper(), cat_code=cat_code_limpio.upper())}">
                  <i class="bi bi-cpu me-1"></i>Análisis
                </a>
              </div>
            </div>
            """)

    if detalle_cards:
        detalle_html = f"""
        <div class="aidet-card p-4 mb-4">
          <div class="d-flex justify-content-between align-items-start flex-wrap gap-3 mb-3">
            <div class="aidet-title-block">
              <div class="aidet-section-title">
                Detalle de Madurez — Sistema de Gestión de Inteligencia Artificial
              </div>
              <div class="text-muted small">
                Resultado detallado por capítulos y categorías evaluadas bajo ISO 42001.
              </div>
            </div>

            <div class="aidet-capitulo-resumen">
              <div class="d-flex align-items-center gap-2 flex-wrap justify-content-end">
                <span class="badge rounded-pill px-3 py-2"
                      style="background:{nivel_general.get('color','#6c757d')}; color:#fff;">
                  Nivel {nivel_general.get('score', 0)}
                </span>
                <span class="fw-bold text-dark">{float(run["pct_general"] or 0):.2f}%</span>
              </div>
              <div class="small text-muted text-end mt-1 aidet-soft-text">
                {escape(nivel_general_nombre)}
              </div>
            </div>
          </div>

          <div class="aidet-gauge-grid">
            {''.join(detalle_cards)}
          </div>
        </div>
        """
    else:
        detalle_html = """
        <div class="aidet-card p-4 mb-4">
          <div class="alert alert-warning mb-0">
            No hay resultados consolidados para mostrar.
          </div>
        </div>
        """

    content = f"""
    <div class="aidet-shell">

      <div class="aidet-header-card">
        <div class="aidet-header-overlay">
          <div class="aidet-header-text">
            <h3 class="aidet-title m-0">Resultado de Madurez — Sistema de Gestión de Inteligencia Artificial</h3>
            <div class="aidet-subtitle">
              Consecutivo: <b>{escape(run["consecutivo"] or "")}</b>
              · Cumplimiento general: <b>{float(run["pct_general"] or 0):.2f}%</b>
              · Nivel general: <b>{escape(nivel_general_nombre)}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="aidet-header-actions">
        <a href="{url_for('madurez_ai.historial')}"
           class="btn aidet-btn-main rounded-pill px-4 fw-bold"
           data-no-progress="true">
          <i class="bi bi-arrow-left me-2"></i>Volver al historial
        </a>

        <a href="{url_for('madurez_ai.home')}"
           class="btn aidet-btn-soft rounded-pill px-4 fw-bold"
           data-no-progress="true">
          <i class="bi bi-house-door-fill me-2"></i>Volver al módulo
        </a>

        {pdf_btn}
      </div>

      {top_html}

      {detalle_html}

    </div>

    {AI_MADUREZ_PROGRESS_JS}

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .aidet-shell{{
        width:96%;
        max-width:1720px;
        margin:26px auto 24px auto;
      }}

      .aidet-header-card{{
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

      .aidet-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .aidet-header-overlay{{
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

      .aidet-header-overlay::before{{
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
      }}

      .aidet-header-text::before{{
        content:"SGSI · Resultado ISO 42001";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .aidet-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .aidet-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        overflow-wrap:anywhere;
      }}

      .aidet-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .aidet-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .aidet-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .aidet-btn-soft{{
        background:rgba(255,255,255,.88);
        color:#111 !important;
        border:1px solid rgba(108,117,125,.35);
      }}

      .aidet-btn-success{{
        background:#198754;
        color:#ffffff !important;
        border:1px solid #198754;
      }}

      .aidet-btn-danger{{
        background:#dc3545;
        color:#ffffff !important;
        border:1px solid #dc3545;
      }}

      .aidet-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
      }}

      .aidet-card-title,
      .aidet-section-title{{
        font-weight:950;
        color:#0b4a8f;
      }}

      .aidet-section-title{{
        font-size:1rem;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }}

      .aidet-general-score-box{{
        background:linear-gradient(135deg,#eef5ff,#ffffff);
        border:1px solid rgba(63,134,214,.20);
        border-radius:18px;
        padding:22px 18px;
        text-align:center;
      }}

      .aidet-general-score-label{{
        font-size:.78rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
      }}

      .aidet-general-score-value{{
        font-size:3.1rem;
        line-height:1;
        font-weight:950;
        color:#0f172a;
        margin:8px 0;
      }}

      .aidet-mini-kpi{{
        background:#f8fafc;
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        height:100%;
      }}

      .aidet-mini-kpi-label{{
        font-size:.72rem;
        color:#475569;
        font-weight:900;
        text-transform:uppercase;
      }}

      .aidet-mini-kpi-value{{
        margin-top:4px;
        font-size:.92rem;
        color:#0f172a;
        font-weight:950;
      }}

      .aidet-exec-box{{
        min-height:310px;
        background:linear-gradient(180deg,rgba(248,250,252,.94),rgba(255,255,255,.98));
        border:1px solid rgba(63,134,214,.16);
        border-radius:16px;
        padding:18px;
      }}

      .aidet-exec-text{{
        font-size:.96rem;
        line-height:1.65;
        color:#101827;
        overflow-wrap:anywhere;
      }}

      .aidet-gauge-grid{{
        display:grid !important;
        grid-template-columns:repeat(3, minmax(0, 1fr)) !important;
        gap:18px !important;
        width:100%;
      }}

      .aidet-gauge-card{{
        min-width:0;
        width:100%;
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
        border:1px solid #dbe6f4;
        border-radius:18px;
        padding:15px 14px 14px 14px;
        box-shadow:0 10px 22px rgba(15,23,42,.10);
        min-height:358px;
        display:flex;
        flex-direction:column;
        overflow:hidden;
        position:relative;
      }}

      .aidet-gauge-card::before{{
        content:"";
        position:absolute;
        top:0;
        left:0;
        right:0;
        height:5px;
        background:linear-gradient(90deg,#0b4a8f,#1d5fae,#6fb7ff);
      }}

      .aidet-gauge-head{{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:6px;
        border-bottom:1px solid rgba(0,0,0,.06);
        padding-bottom:8px;
        margin-bottom:5px;
      }}

      .aidet-cat-code{{
        font-size:.83rem;
        font-weight:950;
        color:#0b4a8f;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
      }}

      .aidet-cat-subcode{{
        width:100%;
        text-align:center;
        color:#475569;
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.25px;
        min-height:18px;
        max-height:18px;
        overflow:hidden;
        white-space:nowrap;
        text-overflow:ellipsis;
        margin-top:4px;
      }}

      .aidet-items-pill{{
        background:#eef5ff;
        color:#0b4a8f;
        border:1px solid #d9eaff;
        border-radius:999px;
        padding:4px 10px;
        font-size:.66rem;
        font-weight:950;
        white-space:nowrap;
      }}

      .aidet-gauge-area{{
        height:118px;
        display:flex;
        align-items:center;
        justify-content:center;
        margin-top:6px;
      }}

      .aidet-gauge-svg{{
        width:176px;
        max-width:100%;
        height:auto;
        display:block;
      }}

      .aidet-cat-name{{
        min-height:32px;
        max-height:32px;
        overflow:hidden;
        margin-top:6px;
        padding:0 4px;
        text-align:center;
        font-size:.86rem;
        line-height:1.24;
        font-weight:850;
        color:#0f172a;
        word-break:break-word;
        overflow-wrap:anywhere;
        display:-webkit-box;
        -webkit-line-clamp:3;
        -webkit-box-orient:vertical;
      }}

      .aidet-level-row{{
        margin-top:auto;
        display:flex;
        align-items:center;
        justify-content:center;
        gap:7px;
        padding-top:10px;
      }}

      .nivel-dot{{
        width:11px;
        height:11px;
        min-width:11px;
        border-radius:50%;
        display:inline-block;
      }}

      .aidet-level-main{{
        font-size:.84rem;
        font-weight:950;
        color:#0f172a;
      }}

      .aidet-level-name{{
        min-height:36px;
        max-height:36px;
        overflow:hidden;
        text-align:center;
        font-size:.68rem;
        line-height:1.18;
        color:#475569;
        margin-top:4px;
      }}

      .aidet-card-actions{{
        display:flex;
        justify-content:center;
        align-items:center;
        gap:6px;
        flex-wrap:wrap;
        margin-top:10px;
      }}

      .aidet-action-btn{{
        font-size:.72rem !important;
        padding:6px 11px !important;
        font-weight:900 !important;
      }}

      @media (max-width:1199.98px){{
        .aidet-gauge-grid{{
          grid-template-columns:repeat(2, minmax(0, 1fr)) !important;
        }}
      }}

      @media (max-width:575.98px){{
        .aidet-gauge-grid{{
          grid-template-columns:1fr !important;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Detalle Madurez IA", content=content)


# ============================================================================================================================================
# VER PREGUNTAS POR CATEGORÍA — GESTIÓN DE IA ISO 42001
# Corrige categorías con espacios, tildes, guiones bajos y capítulos con una sola categoría
# ============================================================================================================================================

@ai_madurez_bp.route("/detalle/<int:run_id>/categoria/<path:cap>/<path:cat_code>", methods=["GET"])
@login_required
def detalle_categoria(run_id, cap, cat_code):
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para consultar las preguntas de Gestión de IA.", "danger")
        return redirect(url_for("menu"))

    import unicodedata

    def _norm_ai_txt(v):
        txt = str(v or "").strip().upper()
        txt = txt.replace("_", " ")
        txt = txt.replace("-", " ")
        txt = " ".join(txt.split())
        txt = unicodedata.normalize("NFKD", txt)
        txt = "".join(c for c in txt if not unicodedata.combining(c))
        return txt

    cap_original = cap or ""
    cat_original = cat_code or ""

    cap_norm = _norm_ai_txt(cap_original)
    cat_norm = _norm_ai_txt(cat_original)

    conn = get_ai_madurez_conn()
    run = conn.execute(
        "SELECT * FROM ai_madurez_runs WHERE id = ?",
        (run_id,)
    ).fetchone()

    if not run:
        conn.close()
        flash("No se encontró la revisión solicitada.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    if user.role != "admin" and run["user_id"] != user.id:
        conn.close()
        flash("No tiene permiso para consultar esta revisión.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    rows_all = conn.execute("""
        SELECT
            p.id AS pregunta_id,
            p.orden AS orden,
            p.capitulo AS capitulo,
            COALESCE(p.categoria_codigo, p.capitulo) AS categoria_codigo,
            COALESCE(p.categoria, p.capitulo) AS categoria,
            p.pregunta AS pregunta,
            r.estado AS estado,
            r.comentario AS comentario
        FROM ai_madurez_respuestas r
        INNER JOIN ai_madurez_preguntas p ON p.id = r.pregunta_id
        WHERE r.run_id = ?
        ORDER BY p.capitulo ASC, p.orden ASC, p.id ASC
    """, (run_id,)).fetchall()

    conn.close()

    # 1. Filtra por capítulo y categoría de forma flexible
    rows_db = []
    for row in rows_all:
        row_cap_norm = _norm_ai_txt(row["capitulo"])
        row_cat_code_norm = _norm_ai_txt(row["categoria_codigo"])
        row_cat_name_norm = _norm_ai_txt(row["categoria"])

        if row_cap_norm == cap_norm and (
            row_cat_code_norm == cat_norm or
            row_cat_name_norm == cat_norm or
            cat_norm in row_cat_code_norm or
            cat_norm in row_cat_name_norm or
            row_cat_code_norm in cat_norm or
            row_cat_name_norm in cat_norm
        ):
            rows_db.append(row)

    # 2. Si no encontró por categoría, muestra TODAS las preguntas del capítulo
    # Esto corrige capítulos que solo tienen una categoría o códigos con tildes/guiones alterados.
    if not rows_db:
        for row in rows_all:
            row_cap_norm = _norm_ai_txt(row["capitulo"])
            if row_cap_norm == cap_norm:
                rows_db.append(row)

    # 3. Si aun así no encuentra, intenta por categoría en todo el run
    if not rows_db:
        for row in rows_all:
            row_cat_code_norm = _norm_ai_txt(row["categoria_codigo"])
            row_cat_name_norm = _norm_ai_txt(row["categoria"])

            if (
                row_cat_code_norm == cat_norm or
                row_cat_name_norm == cat_norm or
                cat_norm in row_cat_code_norm or
                cat_norm in row_cat_name_norm or
                row_cat_code_norm in cat_norm or
                row_cat_name_norm in cat_norm
            ):
                rows_db.append(row)

    capitulo_real = rows_db[0]["capitulo"] if rows_db else cap_original
    categoria_real = rows_db[0]["categoria"] if rows_db else ""
    categoria_codigo_real = rows_db[0]["categoria_codigo"] if rows_db else cat_original

    cap_url = capitulo_real or cap_original
    cat_url = categoria_codigo_real or cat_original

    def badge_estado(estado):
        e = (estado or "").upper().strip()
        if e == "SI":
            return '<span class="badge rounded-pill bg-success px-3">Sí</span>'
        if e == "PARCIAL":
            return '<span class="badge rounded-pill bg-warning text-dark px-3">Parcial</span>'
        if e == "NO":
            return '<span class="badge rounded-pill bg-danger px-3">No</span>'
        if e == "NA":
            return '<span class="badge rounded-pill bg-secondary px-3">N/A</span>'
        return '<span class="badge rounded-pill bg-light text-dark border px-3">Sin respuesta</span>'

    trs = ""
    for item in rows_db:
        trs += f"""
        <tr>
          <td class="text-center fw-bold text-muted">
            {escape(str(item["orden"] or item["pregunta_id"] or ""))}
          </td>
          <td>
            <div class="aidetcat-question">{escape(item["pregunta"] or "")}</div>
            <div class="aidetcat-meta">
              Capítulo: {escape(item["capitulo"] or "")}
              · Categoría: {escape(item["categoria"] or item["categoria_codigo"] or "")}
            </div>
          </td>
          <td class="text-center">{badge_estado(item["estado"])}</td>
          <td>
            <div class="aidetcat-comment">
              {escape(item["comentario"] or "Sin comentarios / evidencia.")}
            </div>
          </td>
        </tr>
        """

    if not trs:
        trs = """
        <tr>
          <td colspan="4" class="text-center text-muted py-4">
            No hay preguntas registradas para esta categoría o capítulo.
          </td>
        </tr>
        """

    content = f"""
    <div class="aidetcat-shell">

      <div class="aidetcat-header-card">
        <div class="aidetcat-header-overlay">
          <div class="aidetcat-header-text">
            <h3 class="aidetcat-title m-0">Preguntas Evaluadas — Sistema de Gestión de IA</h3>
            <div class="aidetcat-subtitle">
              Consecutivo: <b>{escape(run["consecutivo"] or "")}</b>
              · Capítulo: <b>{escape(capitulo_real or "")}</b>
              · Categoría: <b>{escape(categoria_codigo_real or "")}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="aidetcat-header-actions">
        <a href="{url_for('madurez_ai.detalle', run_id=run_id)}"
           class="btn aidetcat-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al detalle
        </a>

        <a href="{url_for('madurez_ai.analisis_categoria', run_id=run_id, cap=cap_url, cat_code=cat_url)}"
           class="btn aidetcat-btn-soft rounded-pill px-4 fw-bold">
          <i class="bi bi-cpu me-2"></i>Ir al análisis
        </a>
      </div>

      <div class="aidetcat-card p-4 mb-4">
        <div class="aidetcat-section-title">
          {escape(categoria_codigo_real or "")} — {escape(categoria_real or "")}
        </div>
        <div class="text-muted small">
          Relación de preguntas, respuesta seleccionada y comentarios/evidencia registrados.
        </div>
      </div>

      <div class="aidetcat-card p-4">
        <div class="table-responsive aidetcat-table-wrap">
          <table class="table table-sm align-middle mb-0">
            <thead>
              <tr>
                <th style="width:80px;">Orden</th>
                <th>Pregunta</th>
                <th style="width:130px;">Respuesta</th>
                <th style="width:34%;">Comentarios / Evidencia</th>
              </tr>
            </thead>
            <tbody>
              {trs}
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

      .aidetcat-shell{{
        width:96%;
        max-width:1580px;
        margin:26px auto 24px auto;
      }}

      .aidetcat-header-card{{
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

      .aidetcat-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .aidetcat-header-overlay{{
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

      .aidetcat-header-overlay::before{{
        content:"📋";
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

      .aidetcat-header-text{{
        width:100%;
        min-width:0;
        display:block !important;
      }}

      .aidetcat-header-text::before{{
        content:"SGSI · Preguntas ISO 42001";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .aidetcat-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .aidetcat-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        overflow-wrap:anywhere;
      }}

      .aidetcat-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .aidetcat-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .aidetcat-btn-main{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .aidetcat-btn-main:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .aidetcat-btn-soft{{
        background:rgba(255,255,255,.88);
        color:#111 !important;
        border:1px solid rgba(108,117,125,.35);
      }}

      .aidetcat-card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
      }}

      .aidetcat-section-title{{
        font-weight:950;
        color:#0b4a8f;
        font-size:1rem;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
        overflow-wrap:anywhere;
      }}

      .aidetcat-table-wrap{{
        max-height:72vh;
        overflow:auto;
        border-radius:14px;
      }}

      .aidetcat-table-wrap thead th{{
        position:sticky;
        top:0;
        z-index:3;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-size:.78rem;
        font-weight:950;
        text-align:center;
        vertical-align:middle;
      }}

      .aidetcat-table-wrap tbody td{{
        font-size:.84rem;
        vertical-align:top;
      }}

      .aidetcat-question{{
        font-weight:800;
        color:#0f172a;
        line-height:1.35;
        overflow-wrap:anywhere;
      }}

      .aidetcat-meta{{
        margin-top:6px;
        color:#475569;
        font-size:.72rem;
        font-weight:700;
        overflow-wrap:anywhere;
      }}

      .aidetcat-comment{{
        color:#475569;
        line-height:1.35;
        overflow-wrap:anywhere;
      }}

      @media (max-width:768px){{
        .aidetcat-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .aidetcat-header-overlay::before{{
          margin:0;
        }}

        .aidetcat-title,
        .aidetcat-subtitle{{
          text-align:center;
        }}

        .aidetcat-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Preguntas Madurez IA", content=content)

@ai_madurez_bp.route("/detalle/<int:run_id>/informe-ejecutivo/generar", methods=["POST"])
@login_required
def informe_ejecutivo_generar(run_id):
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user) or user.role == "auditor":
        flash("El perfil Auditor no puede generar el informe ejecutivo con IA.", "danger")
        return redirect(url_for("madurez_ai.detalle", run_id=run_id))

    conn = get_ai_madurez_conn()
    run = conn.execute("SELECT * FROM ai_madurez_runs WHERE id = ?", (run_id,)).fetchone()
    conn.close()

    if not run:
        flash("No se encontró la revisión.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    if user.role != "admin" and run["user_id"] != user.id:
        flash("No tiene permiso para generar IA sobre esta revisión.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    try:
        resumen = json.loads(run["resumen_json"] or "{}")
    except Exception:
        resumen = {}

    if not resumen:
        flash("⚠️ No hay resultados consolidados para generar el informe ejecutivo.", "warning")
        return redirect(url_for("madurez_ai.detalle", run_id=run_id))

    try:
        raw = _ai_call_text(
            _ai_prompt_informe_ejecutivo(run, resumen),
            max_tokens=900
        )

        obj = _ai_extraer_json_objeto(raw)
        informe = ""

        if isinstance(obj, dict):
            informe = (obj.get("informe_ejecutivo") or "").strip()

        if not informe:
            informe = raw or ""

        informe = _ai_limpiar_texto_rico_guardado(informe)

    except Exception as e:
        flash(f"❌ Error llamando IA para el informe ejecutivo: {e}", "danger")
        return redirect(url_for("madurez_ai.detalle", run_id=run_id))

    if not informe:
        flash("⚠️ La IA no devolvió un informe ejecutivo válido.", "warning")
        return redirect(url_for("madurez_ai.detalle", run_id=run_id))

    conn = get_ai_madurez_conn()
    try:
        conn.execute("""
            UPDATE ai_madurez_runs
            SET informe_ejecutivo_ai = ?,
                informe_ejecutivo_editado = ?,
                updated_at = ?
            WHERE id = ?
        """, (informe, informe, _ai_now(), run_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f"❌ Error guardando informe IA: {e}", "danger")
        return redirect(url_for("madurez_ai.detalle", run_id=run_id))
    finally:
        conn.close()

    flash("✅ Informe ejecutivo generado con IA.", "success")
    return redirect(url_for("madurez_ai.detalle", run_id=run_id))


@ai_madurez_bp.route("/detalle/<int:run_id>/plan-trabajo/generar", methods=["POST"])
@login_required
def plan_trabajo_generar(run_id):
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user) or user.role == "auditor":
        flash("El perfil Auditor no puede generar el plan de trabajo con IA.", "danger")
        return redirect(url_for("madurez_ai.detalle", run_id=run_id))

    conn = get_ai_madurez_conn()
    run = conn.execute("SELECT * FROM ai_madurez_runs WHERE id = ?", (run_id,)).fetchone()
    conn.close()

    if not run:
        flash("No se encontró la revisión.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    if user.role != "admin" and run["user_id"] != user.id:
        flash("No tiene permiso para generar IA sobre esta revisión.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    try:
        resumen = json.loads(run["resumen_json"] or "{}")
    except Exception:
        resumen = {}

    try:
        raw = _ai_call_text(_ai_prompt_plan_trabajo(run, resumen), max_tokens=1800)
        obj = _ai_extraer_json_objeto(raw)
        plan_list = obj.get("plan_trabajo", []) if isinstance(obj, dict) else []
        lines = []

        if isinstance(plan_list, list):
            for i, it in enumerate(plan_list, start=1):
                lines.append(
                    f"{i}. Frente: {(it.get('frente') or 'Sin definir').strip()}\n"
                    f"   Actividad: {(it.get('actividad') or 'Sin definir').strip()}\n"
                    f"   Prioridad: {(it.get('prioridad') or 'Sin definir').strip()}\n"
                    f"   Responsable sugerido: {(it.get('responsable_sugerido') or 'Sin definir').strip()}\n"
                    f"   Plazo: {(it.get('plazo') or 'Sin definir').strip()}\n"
                    f"   Entregable: {(it.get('entregable') or 'Sin definir').strip()}"
                )

        plan = "\n\n".join(lines).strip() or raw or ""
        plan = _ai_limpiar_texto_rico_guardado(plan)
    except Exception as e:
        flash(f"❌ Error llamando IA para el plan de trabajo: {e}", "danger")
        return redirect(url_for("madurez_ai.detalle", run_id=run_id))

    conn = get_ai_madurez_conn()
    conn.execute("""
        UPDATE ai_madurez_runs
        SET plan_trabajo_ai = ?, plan_trabajo_editado = ?, updated_at = ?
        WHERE id = ?
    """, (plan, plan, _ai_now(), run_id))
    conn.commit()
    conn.close()

    flash("✅ Plan de trabajo generado con IA.", "success")
    return redirect(url_for("madurez_ai.detalle", run_id=run_id))


@ai_madurez_bp.route("/detalle/<int:run_id>/informe-ejecutivo/editar", methods=["GET", "POST"])
@login_required
def informe_ejecutivo_editar(run_id):
    return _ai_editar_texto_run(
        run_id=run_id,
        campo_editado="informe_ejecutivo_editado",
        campo_ai="informe_ejecutivo_ai",
        form_name="informe_ejecutivo",
        titulo="Editar Informe Ejecutivo — Gestión de IA",
        label="Informe ejecutivo editable",
        back_endpoint="madurez_ai.detalle",
    )


@ai_madurez_bp.route("/detalle/<int:run_id>/plan-trabajo/editar", methods=["GET", "POST"])
@login_required
def plan_trabajo_editar(run_id):
    return _ai_editar_texto_run(
        run_id=run_id,
        campo_editado="plan_trabajo_editado",
        campo_ai="plan_trabajo_ai",
        form_name="plan_trabajo",
        titulo="Editar Plan de Trabajo — Gestión de IA",
        label="Plan de trabajo editable",
        back_endpoint="madurez_ai.detalle",
    )


def _ai_editar_texto_run(run_id, campo_editado, campo_ai, form_name, titulo, label, back_endpoint):
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user) or user.role == "auditor":
        flash("El perfil Auditor no puede editar este contenido.", "danger")
        return redirect(url_for(back_endpoint, run_id=run_id))

    conn = get_ai_madurez_conn()
    run = conn.execute("SELECT * FROM ai_madurez_runs WHERE id = ?", (run_id,)).fetchone()

    if not run:
        conn.close()
        flash("No se encontró la revisión.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    if user.role != "admin" and run["user_id"] != user.id:
        conn.close()
        flash("No tiene permiso para editar esta revisión.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    if request.method == "POST":
        texto = (request.form.get(form_name) or "").strip()
        conn.execute(f"UPDATE ai_madurez_runs SET {campo_editado} = ?, updated_at = ? WHERE id = ?", (texto, _ai_now(), run_id))
        conn.commit()
        conn.close()
        flash("✅ Información actualizada.", "success")
        return redirect(url_for(back_endpoint, run_id=run_id))

    texto_actual = (run[campo_editado] or run[campo_ai] or "").strip()
    conn.close()

    content = f"""
<div class="aiedit-shell">
  {ai_header(
      "aiedit",
      escape(titulo),
      f"Consecutivo: <b>{escape(run['consecutivo'] or '')}</b>",
      "📝",
      "SGSI · Edición ISO 42001"
  )}

  <div class="aiedit-header-actions">
    <a href="{url_for(back_endpoint, run_id=run_id)}" class="btn aiedit-btn-main rounded-pill px-4 fw-bold">
      <i class="bi bi-arrow-left me-2"></i>Volver al detalle
    </a>
  </div>

  <div class="aiedit-card p-4">
    <form method="POST">
      <div class="aiedit-section-title">{escape(label)}</div>
      <textarea name="{form_name}" class="form-control" rows="20">{escape(texto_actual)}</textarea>
      <div class="d-flex justify-content-center mt-4">
        <button type="submit" class="btn btn-primary rounded-pill px-5 fw-bold">
          <i class="bi bi-save2 me-2"></i>Guardar cambios
        </button>
      </div>
    </form>
  </div>
</div>
"""
    return render_template_string(BASE, title=titulo, content=content)


@ai_madurez_bp.route("/detalle/<int:run_id>/analisis/<path:cap>/<path:cat_code>", methods=["GET"])
@login_required
def analisis_categoria(run_id, cap, cat_code):
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para consultar el análisis de Gestión de IA.", "danger")
        return redirect(url_for("menu"))

    cap_u = (cap or "").upper().strip()
    cat_u = (cat_code or "").upper().strip()

    conn = get_ai_madurez_conn()
    run = conn.execute("SELECT * FROM ai_madurez_runs WHERE id = ?", (run_id,)).fetchone()

    if not run:
        conn.close()
        flash("No se encontró la revisión.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    try:
        resumen = json.loads(run["resumen_json"] or "{}")
    except Exception:
        resumen = {}

    cap_real = cap
    cat_real = cat_code
    cat_nombre = ""
    pct = 0.0

    for cap_name, cats in (resumen or {}).items():
        if (cap_name or "").upper().strip() == cap_u:
            cap_real = cap_name
            for cc, d in (cats or {}).items():
                if (cc or "").upper().strip() == cat_u:
                    cat_real = cc
                    cat_nombre = d.get("categoria", "") or ""
                    pct = float(d.get("pct", 0) or 0)
                    break

    ana = conn.execute("""
        SELECT *
        FROM ai_madurez_categoria_analisis
        WHERE run_id = ?
          AND (
                UPPER(TRIM(capitulo)) = ?
             OR UPPER(TRIM(capitulo)) = ?
          )
          AND (
                UPPER(TRIM(categoria_codigo)) = ?
             OR UPPER(TRIM(categoria_codigo)) = ?
          )
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
    """, (
        run_id,
        cap_u,
        str(cap_real).upper().strip(),
        cat_u,
        str(cat_real).upper().strip()
    )).fetchone()

    conn.close()

    gen_btn = ""
    edit_btn = ""

    if user.role != "auditor":
        gen_btn = f"""
        <form method="POST"
              action="{url_for('madurez_ai.analisis_categoria_generar', run_id=run_id, cap=cap_u, cat_code=cat_u)}"
              data-progress-text="Generando análisis ejecutivo con IA..."
              onsubmit="return ai42001Progress('Generando análisis ejecutivo con IA...');">
          <button type="submit" class="btn btn-primary rounded-pill px-4">
            <i class="bi bi-stars me-2"></i>Generar / Regenerar análisis IA
          </button>
        </form>
        """

        edit_btn = f"""
        <a href="{url_for('madurez_ai.analisis_categoria_editar', run_id=run_id, cap=cap_u, cat_code=cat_u)}"
           class="btn btn-outline-primary rounded-pill px-4"
           data-no-progress="true">
          <i class="bi bi-pencil-square me-2"></i>Editar análisis
        </a>
        """

    estado_actual = (ana["estado_actual"] or "").strip() if ana else ""
    estado_requerido = (ana["estado_requerido"] or "").strip() if ana else ""
    plan_accion = ""

    if ana:
        plan_accion = ((ana["plan_accion_editado"] or "").strip() or (ana["plan_accion_ai"] or "").strip())
        plan_accion = _ai_normalizar_plan_accion_texto(plan_accion)

    content = f"""
<div class="aiana-shell">
  {ai_header(
      "aiana",
      "Análisis Ejecutivo por Categoría — Gestión de IA",
      f"{escape(cap_real or cap)} · {escape(cat_real or cat_code)} · Cumplimiento: <b>{pct:.2f}%</b>",
      "✨",
      "SGSI · Análisis ISO 42001"
  )}

  <div class="aiana-header-actions">
    <a href="{url_for('madurez_ai.detalle', run_id=run_id)}"
       class="btn aiana-btn-main rounded-pill px-4 fw-bold"
       data-no-progress="true">
      <i class="bi bi-arrow-left me-2"></i>Volver al detalle
    </a>

    {gen_btn}
    {edit_btn}
  </div>

  <div class="aiana-card p-4">
    <div class="aiana-section-title">Categoría evaluada</div>

    <div class="alert alert-info">
      <b>{escape(cat_real or cat_code)}</b> — {escape(cat_nombre or "")}
    </div>

    <div class="row g-3">
      <div class="col-12 col-lg-4">
        <div class="card h-100">
          <div class="card-body">
            <h6 class="fw-bold text-primary">Estado actual</h6>
            <pre class="small mb-0" style="white-space:pre-wrap;">{escape(estado_actual or "No generado.")}</pre>
          </div>
        </div>
      </div>

      <div class="col-12 col-lg-4">
        <div class="card h-100">
          <div class="card-body">
            <h6 class="fw-bold text-primary">Estado requerido</h6>
            <pre class="small mb-0" style="white-space:pre-wrap;">{escape(estado_requerido or "No generado.")}</pre>
          </div>
        </div>
      </div>

      <div class="col-12 col-lg-4">
        <div class="card h-100">
          <div class="card-body">
            <h6 class="fw-bold text-primary">Plan de acción</h6>
            <pre class="small mb-0" style="white-space:pre-wrap;">{escape(plan_accion or "No generado.")}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

{AI_MADUREZ_PROGRESS_JS}
"""
    return render_template_string(BASE, title="Análisis Categoría IA", content=content)


@ai_madurez_bp.route("/detalle/<int:run_id>/analisis/<path:cap>/<path:cat_code>/generar", methods=["POST"])
@login_required
def analisis_categoria_generar(run_id, cap, cat_code):
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para generar análisis de Gestión de IA.", "danger")
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede generar análisis con IA.", "danger")
        return redirect(url_for("madurez_ai.analisis_categoria", run_id=run_id, cap=cap, cat_code=cat_code))

    cap_u = (cap or "").upper().strip()
    cat_u = (cat_code or "").upper().strip()

    conn = get_ai_madurez_conn()
    run = conn.execute(
        "SELECT * FROM ai_madurez_runs WHERE id = ?",
        (run_id,)
    ).fetchone()
    conn.close()

    if not run:
        flash("No se encontró la revisión.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    if user.role != "admin" and run["user_id"] != user.id:
        flash("No tiene permiso para generar análisis sobre esta revisión.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    try:
        resumen = json.loads(run["resumen_json"] or "{}")
    except Exception:
        resumen = {}

    cap_real = cap
    cat_real = cat_code
    cat_nombre = ""
    pct = 0.0

    for cap_name, cats in (resumen or {}).items():
        if (cap_name or "").upper().strip() == cap_u:
            cap_real = cap_name

            for cc, d in (cats or {}).items():
                if (cc or "").upper().strip() == cat_u:
                    cat_real = cc
                    cat_nombre = d.get("categoria", "") or ""
                    pct = float(d.get("pct", 0) or 0)
                    break

    items = _ai_items_categoria(run_id, cap_u, cat_u)

    if not items:
        items = _ai_items_categoria(run_id, str(cap_real).upper().strip(), str(cat_real).upper().strip())

    if not items:
        flash("⚠️ No se encontraron respuestas asociadas a esta categoría. Verifica que la revisión tenga respuestas guardadas.", "warning")
        return redirect(url_for("madurez_ai.analisis_categoria", run_id=run_id, cap=cap_u, cat_code=cat_u))

    prompt = _ai_prompt_categoria(
        capitulo=cap_real,
        categoria_codigo=cat_real,
        categoria_nombre=cat_nombre,
        pct=pct,
        items=items
    )

    try:
        raw = _ai_call_text(prompt, max_tokens=1800)
    except Exception as e:
        flash(f"❌ Error llamando IA para el análisis de categoría: {e}", "danger")
        return redirect(url_for("madurez_ai.analisis_categoria", run_id=run_id, cap=cap_u, cat_code=cat_u))

    obj = _ai_extraer_json_objeto(raw)

    estado_actual = ""
    estado_requerido = ""
    plan_accion = ""

    if isinstance(obj, dict):
        estado_actual = _ai_texto_plano_desde_valor(obj.get("estado_actual") or "")
        estado_requerido = _ai_texto_plano_desde_valor(obj.get("estado_requerido") or "")

        plan_raw = obj.get("plan_accion") or obj.get("plan") or obj.get("acciones") or ""

        if isinstance(plan_raw, list):
            plan_accion = _ai_build_plan_accion_texto(plan_raw)
        else:
            plan_accion = _ai_texto_plano_desde_valor(plan_raw)

    if not estado_actual:
        estado_actual = "No se pudo interpretar correctamente el estado actual generado por la IA. Se recomienda regenerar el análisis."

    if not estado_requerido:
        estado_requerido = "No se pudo interpretar correctamente el estado requerido generado por la IA. Se recomienda regenerar el análisis."

    if not plan_accion:
        plan_accion = _ai_normalizar_plan_accion_texto(raw)

    if not plan_accion or plan_accion.strip().startswith("{"):
        plan_accion = "No se pudo generar correctamente el plan de acción. Se recomienda regenerar el análisis."

    now = _ai_now()

    cap_guardar = _ai_key(cap_real or cap_u or cap)
    cat_guardar = _ai_key(cat_real or cat_u or cat_code)

    if not estado_actual.strip():
        estado_actual = "La IA generó una respuesta vacía para el estado actual. Se recomienda regenerar el análisis."

    if not estado_requerido.strip():
        estado_requerido = "La IA generó una respuesta vacía para el estado requerido. Se recomienda regenerar el análisis."

    if not plan_accion.strip():
        plan_accion = "La IA generó una respuesta vacía para el plan de acción. Se recomienda regenerar el análisis."

    conn = get_ai_madurez_conn()

    conn.execute("""
        DELETE FROM ai_madurez_categoria_analisis
        WHERE run_id = ?
          AND (
                categoria_codigo = ?
             OR UPPER(TRIM(categoria_codigo)) = ?
          )
    """, (
        run_id,
        cat_guardar,
        cat_guardar
    ))

    conn.execute("""
        INSERT INTO ai_madurez_categoria_analisis
        (
            run_id,
            capitulo,
            categoria_codigo,
            estado_actual,
            estado_requerido,
            plan_accion_ai,
            plan_accion_editado,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        cap_guardar,
        cat_guardar,
        estado_actual.strip(),
        estado_requerido.strip(),
        plan_accion.strip(),
        plan_accion.strip(),
        now,
        now
    ))

    conn.commit()
    conn.close()

    flash("✅ Análisis generado correctamente con IA.", "success")
    return redirect(url_for(
        "madurez_ai.analisis_categoria",
        run_id=run_id,
        cap=cap_guardar,
        cat_code=cat_guardar
    ))


@ai_madurez_bp.route("/detalle/<int:run_id>/analisis/<path:cap>/<path:cat_code>/editar", methods=["GET", "POST"])
@login_required
def analisis_categoria_editar(run_id, cap, cat_code):
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user) or user.role == "auditor":
        flash("El perfil Auditor no puede editar análisis.", "danger")
        return redirect(url_for("madurez_ai.analisis_categoria", run_id=run_id, cap=cap, cat_code=cat_code))

    cap_u = (cap or "").upper().strip()
    cat_u = (cat_code or "").upper().strip()

    conn = get_ai_madurez_conn()
    ana = conn.execute("""
        SELECT * FROM ai_madurez_categoria_analisis
        WHERE run_id = ? AND UPPER(capitulo) = ? AND UPPER(categoria_codigo) = ?
    """, (run_id, cap_u, cat_u)).fetchone()

    if request.method == "POST":
        estado_actual = (request.form.get("estado_actual") or "").strip()
        estado_requerido = (request.form.get("estado_requerido") or "").strip()
        plan_accion = (request.form.get("plan_accion") or "").strip()

        if ana:
            conn.execute("""
                UPDATE ai_madurez_categoria_analisis
                SET estado_actual = ?, estado_requerido = ?, plan_accion_editado = ?, updated_at = ?
                WHERE id = ?
            """, (estado_actual, estado_requerido, plan_accion, _ai_now(), ana["id"]))
        else:
            conn.execute("""
                INSERT INTO ai_madurez_categoria_analisis
                (run_id, capitulo, categoria_codigo, estado_actual, estado_requerido, plan_accion_ai, plan_accion_editado, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (run_id, cap, cat_code, estado_actual, estado_requerido, plan_accion, plan_accion, _ai_now(), _ai_now()))

        conn.commit()
        conn.close()
        flash("✅ Análisis actualizado.", "success")
        return redirect(url_for("madurez_ai.analisis_categoria", run_id=run_id, cap=cap_u, cat_code=cat_u))

    estado_actual = ana["estado_actual"] if ana else ""
    estado_requerido = ana["estado_requerido"] if ana else ""
    plan_accion = (ana["plan_accion_editado"] or ana["plan_accion_ai"]) if ana else ""
    conn.close()

    content = f"""
<div class="aiedana-shell">
  {ai_header(
      "aiedana",
      "Editar Análisis por Categoría — Gestión de IA",
      f"{escape(cap)} · {escape(cat_code)}",
      "📝",
      "SGSI · Edición Análisis ISO 42001"
  )}

  <div class="aiedana-header-actions">
    <a href="{url_for('madurez_ai.analisis_categoria', run_id=run_id, cap=cap_u, cat_code=cat_u)}"
       class="btn aiedana-btn-main rounded-pill px-4 fw-bold">
      <i class="bi bi-arrow-left me-2"></i>Volver
    </a>
  </div>

  <div class="aiedana-card p-4">
    <form method="POST">
      <label class="form-label fw-bold text-primary">Estado actual</label>
      <textarea name="estado_actual" class="form-control mb-3" rows="7">{escape(estado_actual or "")}</textarea>

      <label class="form-label fw-bold text-primary">Estado requerido</label>
      <textarea name="estado_requerido" class="form-control mb-3" rows="7">{escape(estado_requerido or "")}</textarea>

      <label class="form-label fw-bold text-primary">Plan de acción</label>
      <textarea name="plan_accion" class="form-control mb-3" rows="10">{escape(plan_accion or "")}</textarea>

      <div class="text-center">
        <button class="btn btn-primary rounded-pill px-5 fw-bold">
          <i class="bi bi-save2 me-2"></i>Guardar cambios
        </button>
      </div>
    </form>
  </div>
</div>
"""
    return render_template_string(BASE, title="Editar Análisis IA", content=content)


# ============================================================
# PDF
# ============================================================

def _ai_build_pdf_run(run_id):
    conn = get_ai_madurez_conn()
    run = conn.execute("SELECT * FROM ai_madurez_runs WHERE id = ?", (run_id,)).fetchone()
    analisis_rows = conn.execute("""
        SELECT * FROM ai_madurez_categoria_analisis
        WHERE run_id = ?
        ORDER BY capitulo ASC, categoria_codigo ASC
    """, (run_id,)).fetchall()
    conn.close()

    if not run:
        raise RuntimeError("No se encontró la revisión.") 

    resumen, pct_general_recalculado = ai_recalcular_y_actualizar_run(run_id)

    conn = get_ai_madurez_conn()
    run = conn.execute("SELECT * FROM ai_madurez_runs WHERE id = ?", (run_id,)).fetchone()
    conn.close()

    radar_b64 = ""

    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
        title="ISO 42001 - Informe de Madurez Gestión IA",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="AI_Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, textColor=colors.white, alignment=TA_CENTER, spaceAfter=8))
    styles.add(ParagraphStyle(name="AI_Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, textColor=colors.HexColor("#1d4f8f"), spaceBefore=10, spaceAfter=8))
    styles.add(ParagraphStyle(name="AI_Normal", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#101827"), spaceAfter=5))
    styles.add(ParagraphStyle(name="AI_Small", parent=styles["Normal"], fontName="Helvetica", fontSize=7.5, leading=9, textColor=colors.HexColor("#374151"), spaceAfter=4))

    def pdf_escape(v):
        return html.escape(str(v or ""))

    def add_section(story, title):
        table = Table([[Paragraph(pdf_escape(title), styles["AI_Title"])]], colWidths=[26.8 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#3f86d6")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#1d4f8f")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(table)
        story.append(Spacer(1, 8))

    def add_text_block(story, texto):
        texto = _ai_limpiar_texto_rico_guardado(texto or "")
        if not texto:
            story.append(Paragraph("No hay información registrada.", styles["AI_Normal"]))
            return
        for parrafo in re.split(r"\n\s*\n", texto):
            parrafo = parrafo.strip()
            if parrafo:
                story.append(Paragraph(pdf_escape(parrafo), styles["AI_Normal"]))

    story = []
    add_section(story, "ISO 42001 - Informe de Madurez Gestión de Inteligencia Artificial")

    nivel = ai_nivel_visual_por_pct(run["pct_general"])
    resumen_tbl = Table([
        ["Consecutivo", pdf_escape(run["consecutivo"])],
        ["Fecha", pdf_escape(run["created_at"])],
        ["Cumplimiento general", f"{float(run['pct_general'] or 0):.2f}% - Nivel {nivel.get('score', 0)}"],
        ["Nivel de madurez", pdf_escape(nivel.get("nivel", ""))],
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

    story.append(Paragraph("Informe Ejecutivo", styles["AI_Section"]))
    add_text_block(story, run["informe_ejecutivo_editado"] or run["informe_ejecutivo_ai"] or "")
    story.append(Spacer(1, 10))

    #story.append(Paragraph("Radar por Capítulo ISO 42001", styles["AI_Section"]))
    if radar_b64:
        try:
            img_buf = io.BytesIO(base64.b64decode(radar_b64))
            story.append(RLImage(img_buf, width=11.5 * cm, height=11.0 * cm))
            story.append(Spacer(1, 10))
        except Exception:
            story.append(Paragraph("No se pudo renderizar el radar.", styles["AI_Normal"]))

    story.append(Paragraph("Detalle por Capítulo y Categoría", styles["AI_Section"]))
    data = [["Capítulo", "Categoría", "Nombre", "% Cumplimiento", "Nivel", "Items"]]

    for cap, cats in (resumen or {}).items():
        for cat_code, d in cats.items():
            pct = float(d.get("pct", 0) or 0)
            nv = ai_nivel_visual_por_pct(pct)
            data.append([
                Paragraph(pdf_escape(cap), styles["AI_Small"]),
                Paragraph(pdf_escape(cat_code), styles["AI_Small"]),
                Paragraph(pdf_escape(d.get("categoria", "")), styles["AI_Small"]),
                Paragraph(f"{pct:.2f}%", styles["AI_Small"]),
                Paragraph(pdf_escape(nv.get("nivel", "")), styles["AI_Small"]),
                Paragraph(str(int(d.get("total", 0) or 0)), styles["AI_Small"]),
            ])

    tbl = Table(data, colWidths=[5.0 * cm, 4.0 * cm, 8.5 * cm, 3.0 * cm, 4.3 * cm, 2.0 * cm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3f86d6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7.2),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8e3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (3, 1), (3, -1), "CENTER"),
        ("ALIGN", (5, 1), (5, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(tbl)

    plan_general = run["plan_trabajo_editado"] or run["plan_trabajo_ai"] or ""
    if plan_general:
        story.append(PageBreak())
        add_section(story, "Plan de Trabajo General")
        add_text_block(story, plan_general)

    if analisis_rows:
        story.append(PageBreak())
        add_section(story, "Análisis Ejecutivo por Categoría")

        for a in analisis_rows:
            story.append(Paragraph(pdf_escape(f"{a['capitulo']} - {a['categoria_codigo']}"), styles["AI_Section"]))
            bloque = Table([
                [Paragraph("<b>Estado actual</b>", styles["AI_Small"]), Paragraph(pdf_escape(a["estado_actual"] or "No registrado."), styles["AI_Small"])],
                [Paragraph("<b>Estado requerido</b>", styles["AI_Small"]), Paragraph(pdf_escape(a["estado_requerido"] or "No registrado."), styles["AI_Small"])],
                [Paragraph("<b>Plan de acción</b>", styles["AI_Small"]), Paragraph(pdf_escape(_ai_normalizar_plan_accion_texto(a["plan_accion_editado"] or a["plan_accion_ai"] or "") or "No registrado."), styles["AI_Small"])],
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


@ai_madurez_bp.route("/detalle/<int:run_id>/pdf", methods=["GET"])
@login_required
def exportar_pdf(run_id):
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para exportar PDF del módulo de Gestión de IA.", "danger")
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede exportar PDF en este módulo.", "danger")
        return redirect(url_for("madurez_ai.detalle", run_id=run_id))

    conn = get_ai_madurez_conn()
    run = conn.execute("SELECT * FROM ai_madurez_runs WHERE id = ?", (run_id,)).fetchone()
    conn.close()

    if not run:
        flash("No se encontró la revisión.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    if user.role != "admin" and run["user_id"] != user.id:
        flash("No tiene permiso para exportar esta revisión.", "danger")
        return redirect(url_for("madurez_ai.historial"))

    try:
        pdf = _ai_build_pdf_run(run_id)
    except Exception as e:
        flash(f"❌ Error generando PDF: {e}", "danger")
        return redirect(url_for("madurez_ai.detalle", run_id=run_id))

    filename = f"madurez_gestion_ia_{run_id}.pdf"
    return send_file(pdf, as_attachment=True, download_name=filename, mimetype="application/pdf")

# ============================================================================================================================================
# SUBMÓDULO EVALUACIÓN DE RIESGOS DE IA — NIST AI RMF
# ============================================================================================================================================

def ai_risk_load_questions():
    init_ai_madurez_db()
    conn = get_ai_madurez_conn()
    rows = conn.execute("""
        SELECT *
        FROM ai_risk_preguntas
        WHERE activo = 1
        ORDER BY orden ASC, id ASC
    """).fetchall()
    conn.close()
    return rows


def ai_risk_load_responses(evaluacion_id):
    if not evaluacion_id:
        return {}

    conn = get_ai_madurez_conn()
    rows = conn.execute("""
        SELECT *
        FROM ai_risk_respuestas
        WHERE evaluacion_id = ?
    """, (evaluacion_id,)).fetchall()
    conn.close()

    return {
        int(row["pregunta_id"]): {
            "estado": _ai_estado_normalizado(row["estado"]),
            "comentario": (row["comentario"] or "").strip(),
            "evidencia": (row["evidencia"] or "").strip(),
        }
        for row in rows
    }


def ai_risk_get_draft(user_id):
    if not user_id:
        return None

    conn = get_ai_madurez_conn()
    row = conn.execute("""
        SELECT *
        FROM ai_risk_evaluaciones
        WHERE user_id = ? AND estado = 'BORRADOR'
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
    """, (user_id,)).fetchone()
    conn.close()
    return row


def ai_risk_can_view(evaluacion, user):
    if not evaluacion or not user:
        return False
    if user.role == "admin":
        return True
    if user.role == "auditor":
        return (evaluacion["estado"] or "").upper() == "FINALIZADO"
    return int(evaluacion["user_id"] or 0) == int(user.id)


def ai_risk_get_evaluation(evaluacion_id, user):
    conn = get_ai_madurez_conn()
    row = conn.execute("""
        SELECT *
        FROM ai_risk_evaluaciones
        WHERE id = ?
    """, (evaluacion_id,)).fetchone()
    conn.close()

    if not row or not ai_risk_can_view(row, user):
        return None
    return row


def ai_risk_maturity_level(cumplimiento_pct):
    """Aplica a riesgos los mismos niveles configurados para madurez de IA."""
    maturity = ai_nivel_visual_por_pct(cumplimiento_pct)
    try:
        value = max(0.0, min(100.0, float(cumplimiento_pct or 0)))
    except Exception:
        value = 0.0

    return {
        "nivel": maturity.get("nivel", "Nivel no definido"),
        "score": int(maturity.get("score", 0) or 0),
        "color": maturity.get("color", "#6c757d"),
        "cumplimiento": value,
    }


def ai_risk_calculate_progress(preguntas, form_data=None, respuestas=None):
    total = len(preguntas)
    respondidas = 0

    for q in preguntas:
        qid = int(q["id"])
        if form_data is not None:
            estado = _ai_estado_normalizado(form_data.get(f"risk_st_{qid}"))
        else:
            estado = _ai_estado_normalizado((respuestas or {}).get(qid, {}).get("estado"))

        if estado in ("SI", "PARCIAL", "NO", "NA"):
            respondidas += 1

    pct = int(round((respondidas / total) * 100)) if total else 0
    return respondidas, total, pct


def ai_risk_build_summary(evaluacion_id):
    conn = get_ai_madurez_conn()
    rows = conn.execute("""
        SELECT
            p.id AS pregunta_id,
            p.codigo,
            p.fase_codigo,
            p.fase,
            p.nist_funcion,
            p.nist_categoria,
            p.titulo,
            p.pregunta,
            p.evidencia_sugerida,
            p.orden,
            r.estado,
            r.comentario,
            r.evidencia
        FROM ai_risk_preguntas p
        LEFT JOIN ai_risk_respuestas r
          ON r.pregunta_id = p.id
         AND r.evaluacion_id = ?
        WHERE p.activo = 1
        ORDER BY p.orden ASC, p.id ASC
    """, (evaluacion_id,)).fetchall()
    conn.close()

    summary = {
        "total": len(rows),
        "respondidas": 0,
        "conteos": {"SI": 0, "PARCIAL": 0, "NO": 0, "NA": 0, "PENDIENTE": 0},
        "fases": {},
        "funciones": {},
        "items": [],
    }

    def new_group(nombre):
        return {
            "nombre": nombre,
            "total": 0,
            "respondidas": 0,
            "aplicables": 0,
            "puntaje": 0.0,
            "SI": 0,
            "PARCIAL": 0,
            "NO": 0,
            "NA": 0,
        }

    for row in rows:
        estado = _ai_estado_normalizado(row["estado"])
        estado_key = estado if estado else "PENDIENTE"
        summary["conteos"][estado_key] += 1

        if estado:
            summary["respondidas"] += 1

        fase_code = row["fase_codigo"] or "SIN_FASE"
        funcion = row["nist_funcion"] or "SIN_FUNCION"

        phase_group = summary["fases"].setdefault(
            fase_code,
            new_group(row["fase"] or fase_code)
        )
        function_name = AI_RISK_FUNCTIONS.get(funcion, {}).get("nombre", funcion)
        function_group = summary["funciones"].setdefault(
            funcion,
            new_group(function_name)
        )

        for group in (phase_group, function_group):
            group["total"] += 1
            if estado:
                group["respondidas"] += 1
                group[estado] += 1

            score_value = AI_STATUS_SCORE.get(estado)
            if score_value is not None:
                group["aplicables"] += 1
                group["puntaje"] += float(score_value)

        summary["items"].append({
            "pregunta_id": int(row["pregunta_id"]),
            "codigo": row["codigo"] or "",
            "fase_codigo": fase_code,
            "fase": row["fase"] or "",
            "nist_funcion": funcion,
            "nist_categoria": row["nist_categoria"] or "",
            "titulo": row["titulo"] or "",
            "pregunta": row["pregunta"] or "",
            "evidencia_sugerida": row["evidencia_sugerida"] or "",
            "estado": estado,
            "comentario": row["comentario"] or "",
            "evidencia": row["evidencia"] or "",
            "orden": int(row["orden"] or 0),
        })

    for groups in (summary["fases"], summary["funciones"]):
        for group in groups.values():
            applicable = int(group["aplicables"] or 0)
            pct = (float(group["puntaje"] or 0) / applicable * 100.0) if applicable else 0.0
            exposure = 100.0 - pct if applicable else 0.0
            maturity = ai_risk_maturity_level(pct)
            group["cumplimiento_pct"] = round(pct, 2)
            group["exposicion_pct"] = round(exposure, 2)
            group["nivel_madurez"] = maturity["nivel"]
            group["madurez_score"] = maturity["score"]
            group["color"] = maturity["color"]
            # Alias conservado para compatibilidad con resúmenes históricos.
            group["nivel_riesgo"] = maturity["nivel"]
            group.pop("puntaje", None)

    applicable_items = [
        item for item in summary["items"]
        if AI_STATUS_SCORE.get(item["estado"]) is not None
    ]
    applicable_total = len(applicable_items)
    score_total = sum(
        float(AI_STATUS_SCORE.get(item["estado"], 0.0))
        for item in applicable_items
    )

    cumplimiento = (score_total / applicable_total * 100.0) if applicable_total else 0.0
    exposicion = 100.0 - cumplimiento if applicable_total else 0.0
    progreso = int(round((summary["respondidas"] / summary["total"]) * 100)) if summary["total"] else 0
    maturity = ai_risk_maturity_level(cumplimiento)

    summary["aplicables"] = applicable_total
    summary["progreso_pct"] = progreso
    summary["cumplimiento_pct"] = round(cumplimiento, 2)
    summary["exposicion_pct"] = round(exposicion, 2)
    summary["nivel_madurez"] = maturity["nivel"]
    summary["madurez_score"] = maturity["score"]
    summary["color_madurez"] = maturity["color"]
    # Alias conservados para no romper evaluaciones almacenadas previamente.
    summary["nivel_riesgo"] = maturity["nivel"]
    summary["color_riesgo"] = maturity["color"]

    return summary


def ai_risk_recalculate(evaluacion_id):
    summary = ai_risk_build_summary(evaluacion_id)
    conn = get_ai_madurez_conn()
    conn.execute("""
        UPDATE ai_risk_evaluaciones
        SET updated_at = ?,
            progreso_pct = ?,
            cumplimiento_pct = ?,
            exposicion_pct = ?,
            nivel_riesgo = ?,
            resumen_json = ?
        WHERE id = ?
    """, (
        _ai_now(),
        int(summary["progreso_pct"]),
        float(summary["cumplimiento_pct"]),
        float(summary["exposicion_pct"]),
        summary["nivel_madurez"],
        json.dumps(summary, ensure_ascii=False),
        evaluacion_id,
    ))
    conn.commit()
    conn.close()
    return summary


def ai_risk_css():
    return """
<style>
  .airisk-shell{width:96%;max-width:1600px;margin:26px auto 24px auto;}
  .airisk-card{
    background:rgba(255,255,255,.97);
    border:1px solid #dbe6f4;
    border-radius:18px;
    padding:20px;
    box-shadow:0 12px 24px rgba(15,23,42,.16);
  }
  .airisk-actions{display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin:10px 0 16px;}
  .airisk-actions .btn{border-radius:999px!important;padding:9px 22px!important;font-weight:900;}
  .airisk-kpi{height:100%;border:1px solid #dbe6f4;border-radius:16px;padding:16px;background:#fff;}
  .airisk-kpi-value{font-size:1.55rem;font-weight:950;color:#0b4a8f;}
  .airisk-kpi-label{font-size:.76rem;color:#64748b;font-weight:800;}
  .airisk-section{font-weight:950;color:#0b4a8f;font-size:1rem;border-bottom:2px solid #dcecff;padding-bottom:8px;margin-bottom:14px;}
  .airisk-progress{height:24px;border-radius:999px;background:#dbe6f4;overflow:hidden;}
  .airisk-progress > div{height:100%;background:linear-gradient(135deg,#0b4a8f,#2f7fd1);color:#fff;font-weight:900;text-align:center;line-height:24px;transition:width .2s ease;}
  .airisk-phase{border:1px solid #dbe6f4!important;border-radius:16px!important;overflow:hidden;margin-bottom:12px;}
  .airisk-phase .accordion-button{background:linear-gradient(135deg,#eef6ff,#fff);font-weight:900;color:#0f3d68;box-shadow:none;}
  .airisk-q{border:1px solid #e2e8f0;border-radius:15px;padding:16px;background:#fff;height:100%;}
  .airisk-q-title{font-weight:900;color:#0f172a;margin:8px 0 5px;}
  .airisk-q-text{font-size:.88rem;line-height:1.45;color:#1e293b;}
  .airisk-radio{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:13px;}
  .airisk-radio label{border:1px solid #dbe6f4;border-radius:10px;padding:8px;text-align:center;font-size:.76rem;font-weight:900;background:#f8fafc;cursor:pointer;}
  .airisk-radio input{margin-right:4px;}
  .airisk-badge{display:inline-block;border-radius:999px;padding:4px 9px;color:#fff;font-size:.68rem;font-weight:900;}
  .airisk-note{font-size:.76rem;background:#f8fafc;border-left:4px solid #0d6efd;padding:9px 11px;border-radius:8px;margin-top:10px;color:#475569;}
  .airisk-table thead th{background:#0b4a8f!important;color:#fff!important;position:sticky;top:0;z-index:2;font-size:.72rem;}
  .airisk-table td{font-size:.76rem;vertical-align:top;}
  .airisk-analysis{white-space:pre-wrap;line-height:1.55;color:#1e293b;}
  @media(max-width:768px){
    .airisk-shell{width:98%;margin-top:12px;}
    .airisk-actions .btn{width:100%;}
    .airisk-radio{grid-template-columns:1fr 1fr;}
  }
</style>
"""


@ai_madurez_bp.route("/riesgos", methods=["GET"])
@login_required
def ai_risk_home():
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para acceder a la Evaluación de Riesgos de IA.", "danger")
        return redirect(url_for("menu"))

    conn = get_ai_madurez_conn()
    total_questions = conn.execute(
        "SELECT COUNT(*) AS c FROM ai_risk_preguntas WHERE activo = 1"
    ).fetchone()["c"]

    if user.role == "admin":
        stats = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN estado = 'FINALIZADO' THEN 1 ELSE 0 END) AS finalizadas,
                SUM(CASE WHEN estado = 'BORRADOR' THEN 1 ELSE 0 END) AS borradores
            FROM ai_risk_evaluaciones
        """).fetchone()
    elif user.role == "auditor":
        stats = conn.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) AS finalizadas,
                0 AS borradores
            FROM ai_risk_evaluaciones
            WHERE estado = 'FINALIZADO'
        """).fetchone()
    else:
        stats = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN estado = 'FINALIZADO' THEN 1 ELSE 0 END) AS finalizadas,
                SUM(CASE WHEN estado = 'BORRADOR' THEN 1 ELSE 0 END) AS borradores
            FROM ai_risk_evaluaciones
            WHERE user_id = ?
        """, (user.id,)).fetchone()
    conn.close()

    if user.role == "auditor":
        new_button = """
        <button class="btn btn-secondary" disabled title="El rol Auditor no puede crear evaluaciones">
          <i class="bi bi-lock-fill me-2"></i>Nueva evaluación
        </button>
        """
    else:
        new_button = f"""
        <a href="{url_for('madurez_ai.ai_risk_form')}" class="btn btn-primary">
          <i class="bi bi-clipboard2-check-fill me-2"></i>Nueva evaluación
        </a>
        """

    function_cards = ""
    for key in ("GOVERN", "MAP", "MEASURE", "MANAGE"):
        info = AI_RISK_FUNCTIONS[key]
        function_cards += f"""
        <div class="col-12 col-md-6 col-xl-3">
          <div class="airisk-kpi">
            <span class="airisk-badge" style="background:{info['color']};">{key}</span>
            <div class="fw-bold mt-2">{escape(info['nombre'])}</div>
            <div class="small text-muted mt-1">{escape(info['descripcion'])}</div>
          </div>
        </div>
        """

    content = f"""
<div class="airisk-shell">
  {ai_header(
      "airisk",
      "Nivel de Madurez de Riesgos de Inteligencia Artificial",
      "Checklist por ciclo de vida alineado con las funciones GOVERN, MAP, MEASURE y MANAGE de NIST AI RMF.",
      "⚠️",
      "SGSI · NIST AI RMF"
  )}

  <div class="airisk-actions">
    <a href="{url_for('madurez_ai.home')}" class="btn btn-light border">
      <i class="bi bi-arrow-left me-2"></i>Volver a Madurez IA
    </a>
    {new_button}
    <a href="{url_for('madurez_ai.ai_risk_history')}" class="btn btn-outline-primary">
      <i class="bi bi-clock-history me-2"></i>Historial de evaluaciones
    </a>
  </div>

  <div class="row g-3 mb-3">
    <div class="col-6 col-lg-3"><div class="airisk-kpi"><div class="airisk-kpi-value">{int(total_questions or 0)}</div><div class="airisk-kpi-label">Preguntas activas</div></div></div>
    <div class="col-6 col-lg-3"><div class="airisk-kpi"><div class="airisk-kpi-value">{int(stats['total'] or 0)}</div><div class="airisk-kpi-label">Evaluaciones</div></div></div>
    <div class="col-6 col-lg-3"><div class="airisk-kpi"><div class="airisk-kpi-value">{int(stats['finalizadas'] or 0)}</div><div class="airisk-kpi-label">Finalizadas</div></div></div>
    <div class="col-6 col-lg-3"><div class="airisk-kpi"><div class="airisk-kpi-value">{int(stats['borradores'] or 0)}</div><div class="airisk-kpi-label">Borradores</div></div></div>
  </div>

  <div class="airisk-card mb-3">
    <div class="airisk-section">Estructura NIST AI RMF</div>
    <div class="row g-3">{function_cards}</div>
    <div class="alert alert-info small mt-3 mb-0">
      <b>Parámetros de madurez IA reutilizados:</b>
      Sí = {int(float(AI_STATUS_SCORE.get('SI', 0)) * 100)}%,
      Parcial = {int(float(AI_STATUS_SCORE.get('PARCIAL', 0)) * 100)}%,
      No = {int(float(AI_STATUS_SCORE.get('NO', 0)) * 100)}% y N/A se excluye.
      El nivel de madurez de riesgos se obtiene de los cinco rangos definidos en
      <b>Parámetros — Madurez Gestión de Inteligencia Artificial</b>.
      La exposición se conserva como indicador complementario: 100% menos el porcentaje de controles implementados.
    </div>
  </div>

  <div class="airisk-card">
    <div class="airisk-section">Ciclo de vida evaluado</div>
    <div class="row g-3">
      {''.join(f'<div class="col-12 col-md-6"><div class="airisk-note"><b>{escape(p["nombre"])}</b><br>{escape(p["descripcion"])}<br><span class="text-primary fw-bold">{escape(p["foco_nist"])}</span></div></div>' for p in AI_RISK_PHASES)}
    </div>
  </div>
</div>
{ai_risk_css()}
"""
    return render_template_string(BASE, title="Madurez de Riesgos de IA — NIST AI RMF", content=content)


@ai_madurez_bp.route("/riesgos/evaluacion", methods=["GET"])
@login_required
def ai_risk_form():
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para acceder a la Evaluación de Riesgos de IA.", "danger")
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El rol Auditor no puede crear ni modificar evaluaciones de riesgos.", "warning")
        return redirect(url_for("madurez_ai.ai_risk_home"))

    preguntas = ai_risk_load_questions()
    draft = ai_risk_get_draft(user.id)
    respuestas = ai_risk_load_responses(draft["id"]) if draft else {}
    _, _, initial_progress = ai_risk_calculate_progress(preguntas, respuestas=respuestas)

    def esc(value):
        return escape(str(value or ""))

    def checked(question_id, value):
        current = _ai_estado_normalizado(respuestas.get(question_id, {}).get("estado"))
        return "checked" if current == value else ""

    phase_html = ""
    for index, phase in enumerate(AI_RISK_PHASES, start=1):
        phase_questions = [q for q in preguntas if q["fase_codigo"] == phase["codigo"]]
        cards = ""

        for q in phase_questions:
            qid = int(q["id"])
            saved = respuestas.get(qid, {})
            function_color = AI_RISK_FUNCTIONS.get(q["nist_funcion"], {}).get("color", "#6c757d")

            cards += f"""
            <div class="col-12 col-xl-6">
              <div class="airisk-q">
                <div class="d-flex gap-2 flex-wrap">
                  <span class="badge bg-light text-primary border">{esc(q['codigo'])}</span>
                  <span class="airisk-badge" style="background:{function_color};">{esc(q['nist_funcion'])}</span>
                  <span class="badge bg-secondary">{esc(q['nist_categoria'])}</span>
                </div>
                <div class="airisk-q-title">{esc(q['titulo'])}</div>
                <div class="airisk-q-text">{esc(q['pregunta'])}</div>
                <div class="airisk-note"><b>Evidencia sugerida:</b> {esc(q['evidencia_sugerida'])}</div>

                <div class="airisk-radio">
                  <label><input type="radio" name="risk_st_{qid}" value="SI" {checked(qid, 'SI')}>Sí</label>
                  <label><input type="radio" name="risk_st_{qid}" value="PARCIAL" {checked(qid, 'PARCIAL')}>Parcial</label>
                  <label><input type="radio" name="risk_st_{qid}" value="NO" {checked(qid, 'NO')}>No</label>
                  <label><input type="radio" name="risk_st_{qid}" value="NA" {checked(qid, 'NA')}>N/A</label>
                </div>

                <div class="row g-2 mt-2">
                  <div class="col-12">
                    <label class="form-label small fw-bold">Comentario / justificación</label>
                    <textarea class="form-control" name="risk_cm_{qid}" rows="2">{esc(saved.get('comentario'))}</textarea>
                  </div>
                  <div class="col-12">
                    <label class="form-label small fw-bold">Referencia de evidencia</label>
                    <textarea class="form-control" name="risk_ev_{qid}" rows="2" placeholder="Documento, enlace, repositorio, acta o registro">{esc(saved.get('evidencia'))}</textarea>
                  </div>
                </div>
              </div>
            </div>
            """

        phase_html += f"""
        <div class="accordion-item airisk-phase">
          <h2 class="accordion-header" id="airisk-h-{phase['codigo']}">
            <button class="accordion-button {'collapsed' if index != 1 else ''}" type="button"
                    data-bs-toggle="collapse" data-bs-target="#airisk-c-{phase['codigo']}">
              <div>
                <div>{esc(phase['nombre'])}</div>
                <div class="small text-muted">{esc(phase['descripcion'])} · {len(phase_questions)} preguntas</div>
              </div>
            </button>
          </h2>
          <div id="airisk-c-{phase['codigo']}" class="accordion-collapse collapse {'show' if index == 1 else ''}">
            <div class="accordion-body"><div class="row g-3">{cards}</div></div>
          </div>
        </div>
        """

    classification = (draft["clasificacion_riesgo"] if draft else "") or ""
    options = ["Por determinar", "Prohibido", "Alto", "Limitado", "Mínimo"]
    option_html = "".join(
        f'<option value="{esc(opt)}" {"selected" if classification == opt else ""}>{esc(opt)}</option>'
        for opt in options
    )
    disabled_finish = "" if initial_progress == 100 else "disabled"

    content = f"""
<div class="airisk-shell">
  {ai_header(
      "airisk",
      "Ingreso — Nivel de Madurez de Riesgos de IA",
      "Responde las 25 preguntas del ciclo de vida. Sí significa que el control o práctica está implementado.",
      "🧭",
      "SGSI · NIST AI RMF"
  )}

  <div class="airisk-actions">
    <a href="{url_for('madurez_ai.ai_risk_home')}" class="btn btn-light border"><i class="bi bi-arrow-left me-2"></i>Volver</a>
    <a href="{url_for('madurez_ai.ai_risk_history')}" class="btn btn-outline-primary"><i class="bi bi-clock-history me-2"></i>Historial</a>
  </div>

  <form id="aiRiskForm" method="POST" action="{url_for('madurez_ai.ai_risk_save')}">
    <input type="hidden" name="evaluacion_id" value="{draft['id'] if draft else ''}">

    <div class="airisk-card mb-3">
      <div class="airisk-section">Información del proyecto o sistema de IA</div>
      {'<div class="alert alert-info small">Se cargó automáticamente el borrador pendiente.</div>' if draft else ''}
      <div class="row g-3">
        <div class="col-12 col-md-4">
          <label class="form-label fw-bold">Consecutivo *</label>
          <input class="form-control" name="consecutivo" required value="{esc(draft['consecutivo'] if draft else '')}">
        </div>
        <div class="col-12 col-md-8">
          <label class="form-label fw-bold">Nombre del proyecto o sistema de IA *</label>
          <input class="form-control" name="nombre_proyecto" required value="{esc(draft['nombre_proyecto'] if draft else '')}">
        </div>
        <div class="col-12 col-md-6">
          <label class="form-label fw-bold">Responsable / Product Owner</label>
          <input class="form-control" name="responsable" value="{esc(draft['responsable'] if draft else '')}">
        </div>
        <div class="col-12 col-md-6">
          <label class="form-label fw-bold">Clasificación regulatoria del riesgo</label>
          <select class="form-select" name="clasificacion_riesgo">{option_html}</select>
        </div>
        <div class="col-12 col-md-6">
          <label class="form-label fw-bold">Caso de uso</label>
          <textarea class="form-control" name="caso_uso" rows="3">{esc(draft['caso_uso'] if draft else '')}</textarea>
        </div>
        <div class="col-12 col-md-6">
          <label class="form-label fw-bold">Descripción y alcance</label>
          <textarea class="form-control" name="descripcion" rows="3">{esc(draft['descripcion'] if draft else '')}</textarea>
        </div>
      </div>
    </div>

    <div class="airisk-card mb-3">
      <div class="airisk-section">📊 Progreso de diligenciamiento</div>
      <div class="airisk-progress">
        <div id="aiRiskProgressBar" style="width:{initial_progress}%">{initial_progress}%</div>
      </div>
      <div class="text-center small text-muted mt-2">
        <span id="aiRiskProgressText">{initial_progress}%</span> del cuestionario completado
      </div>
    </div>

    <div class="airisk-card">
      <div class="airisk-section">Checklist de evaluación por fases</div>
      <div class="alert alert-light border small">
        Escala tomada de los parámetros de Madurez IA:
        <b>Sí</b> = {int(float(AI_STATUS_SCORE.get('SI', 0)) * 100)}%;
        <b>Parcial</b> = {int(float(AI_STATUS_SCORE.get('PARCIAL', 0)) * 100)}%;
        <b>No</b> = {int(float(AI_STATUS_SCORE.get('NO', 0)) * 100)}%;
        <b>N/A</b> = excluido del cálculo con justificación.
      </div>
      <div class="accordion" id="aiRiskAccordion">{phase_html}</div>

      <div class="d-flex justify-content-center gap-3 flex-wrap mt-4">
        <button class="btn btn-outline-primary btn-lg rounded-pill px-5 fw-bold" type="submit" name="accion" value="borrador">
          <i class="bi bi-save2 me-2"></i>Guardar borrador
        </button>
        <button id="aiRiskFinishButton" class="btn btn-primary btn-lg rounded-pill px-5 fw-bold" type="submit"
                name="accion" value="finalizar" {disabled_finish}>
          <i class="bi bi-check2-circle me-2"></i>Finalizar y analizar
        </button>
      </div>
    </div>
  </form>
</div>
{ai_risk_css()}

<script>
(function(){{
  function updateAiRiskProgress(){{
    const radios = Array.from(document.querySelectorAll('input[type="radio"][name^="risk_st_"]'));
    const names = Array.from(new Set(radios.map(function(r){{return r.name;}})));
    let answered = 0;
    names.forEach(function(name){{
      if(document.querySelector('input[name="' + name + '"]:checked')) answered++;
    }});
    const pct = names.length ? Math.round(answered / names.length * 100) : 0;
    const bar = document.getElementById("aiRiskProgressBar");
    const text = document.getElementById("aiRiskProgressText");
    const finish = document.getElementById("aiRiskFinishButton");
    if(bar){{bar.style.width = pct + "%"; bar.textContent = pct + "%";}}
    if(text) text.textContent = pct + "%";
    if(finish){{finish.disabled = pct < 100; finish.classList.toggle("disabled", pct < 100);}}
  }}
  document.addEventListener("change", function(event){{
    if(event.target.matches('input[type="radio"][name^="risk_st_"]')) updateAiRiskProgress();
  }});
  document.addEventListener("DOMContentLoaded", updateAiRiskProgress);
}})();
</script>
"""
    return render_template_string(BASE, title="Madurez de Riesgos de IA", content=content)


@ai_madurez_bp.route("/riesgos/guardar", methods=["POST"])
@login_required
def ai_risk_save():
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user) or user.role == "auditor":
        flash("No tiene permiso para guardar evaluaciones de riesgos de IA.", "danger")
        return redirect(url_for("madurez_ai.ai_risk_home"))

    preguntas = ai_risk_load_questions()
    consecutivo = (request.form.get("consecutivo") or "").strip()
    project_name = (request.form.get("nombre_proyecto") or "").strip()

    if not consecutivo or not project_name:
        flash("Debes ingresar el consecutivo y el nombre del proyecto o sistema de IA.", "warning")
        return redirect(url_for("madurez_ai.ai_risk_form"))

    action = (request.form.get("accion") or "borrador").strip().lower()
    answered, total, progress = ai_risk_calculate_progress(preguntas, form_data=request.form)

    if answered == 0:
        flash("Debes responder al menos una pregunta antes de guardar la evaluación de riesgos.", "warning")
        return redirect(url_for("madurez_ai.ai_risk_form"))

    requested_finish = action == "finalizar"
    status = "FINALIZADO" if requested_finish and progress == 100 else "BORRADOR"

    raw_id = (request.form.get("evaluacion_id") or "").strip()
    evaluation = None
    if raw_id.isdigit():
        evaluation = ai_risk_get_evaluation(int(raw_id), user)
        if evaluation and evaluation["estado"] != "BORRADOR":
            evaluation = None

    if not evaluation:
        evaluation = ai_risk_get_draft(user.id)

    now = _ai_now()
    conn = get_ai_madurez_conn()
    cur = conn.cursor()

    if evaluation:
        evaluation_id = int(evaluation["id"])
        cur.execute("""
            UPDATE ai_risk_evaluaciones
            SET updated_at = ?,
                consecutivo = ?,
                nombre_proyecto = ?,
                responsable = ?,
                caso_uso = ?,
                descripcion = ?,
                clasificacion_riesgo = ?,
                estado = ?,
                progreso_pct = ?
            WHERE id = ?
        """, (
            now,
            consecutivo,
            project_name,
            (request.form.get("responsable") or "").strip(),
            (request.form.get("caso_uso") or "").strip(),
            (request.form.get("descripcion") or "").strip(),
            (request.form.get("clasificacion_riesgo") or "Por determinar").strip(),
            status,
            progress,
            evaluation_id,
        ))
    else:
        cur.execute("""
            INSERT INTO ai_risk_evaluaciones (
                created_at, updated_at, consecutivo, nombre_proyecto,
                responsable, caso_uso, descripcion, clasificacion_riesgo,
                user_id, estado, progreso_pct, cumplimiento_pct,
                exposicion_pct, nivel_riesgo, resumen_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 100, 'Nivel 1: Ejecutado (Performed)', '{}')
        """, (
            now,
            now,
            consecutivo,
            project_name,
            (request.form.get("responsable") or "").strip(),
            (request.form.get("caso_uso") or "").strip(),
            (request.form.get("descripcion") or "").strip(),
            (request.form.get("clasificacion_riesgo") or "Por determinar").strip(),
            user.id,
            status,
            progress,
        ))
        evaluation_id = cur.lastrowid

    for question in preguntas:
        qid = int(question["id"])
        answer = _ai_estado_normalizado(request.form.get(f"risk_st_{qid}"))
        comment = (request.form.get(f"risk_cm_{qid}") or "").strip()
        evidence = (request.form.get(f"risk_ev_{qid}") or "").strip()

        if answer not in ("SI", "PARCIAL", "NO", "NA"):
            cur.execute("""
                DELETE FROM ai_risk_respuestas
                WHERE evaluacion_id = ? AND pregunta_id = ?
            """, (evaluation_id, qid))
            continue

        cur.execute("""
            INSERT INTO ai_risk_respuestas (
                evaluacion_id, pregunta_id, estado, comentario, evidencia
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(evaluacion_id, pregunta_id)
            DO UPDATE SET
                estado = excluded.estado,
                comentario = excluded.comentario,
                evidencia = excluded.evidencia
        """, (evaluation_id, qid, answer, comment, evidence))

    conn.commit()
    conn.close()
    ai_risk_recalculate(evaluation_id)

    if requested_finish and progress < 100:
        flash(f"El avance es {progress}%. Se guardó como borrador; debes responder las {total} preguntas para finalizar.", "warning")
        return redirect(url_for("madurez_ai.ai_risk_form"))

    if status == "FINALIZADO":
        flash("✅ Evaluación de riesgos de IA finalizada correctamente.", "success")
        return redirect(url_for("madurez_ai.ai_risk_detail", evaluacion_id=evaluation_id))

    flash(f"✅ Borrador guardado. Progreso: {answered}/{total} preguntas ({progress}%).", "success")
    return redirect(url_for("madurez_ai.ai_risk_form"))


@ai_madurez_bp.route("/riesgos/historial", methods=["GET"])
@login_required
def ai_risk_history():
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para consultar evaluaciones de riesgos de IA.", "danger")
        return redirect(url_for("menu"))

    conn = get_ai_madurez_conn()
    if user.role == "admin":
        evaluations = conn.execute("""
            SELECT * FROM ai_risk_evaluaciones
            ORDER BY updated_at DESC, id DESC
        """).fetchall()
    elif user.role == "auditor":
        evaluations = conn.execute("""
            SELECT * FROM ai_risk_evaluaciones
            WHERE estado = 'FINALIZADO'
            ORDER BY updated_at DESC, id DESC
        """).fetchall()
    else:
        evaluations = conn.execute("""
            SELECT * FROM ai_risk_evaluaciones
            WHERE user_id = ?
            ORDER BY updated_at DESC, id DESC
        """, (user.id,)).fetchall()
    conn.close()

    rows = ""
    for evaluation in evaluations:
        maturity = ai_risk_maturity_level(evaluation["cumplimiento_pct"])
        status = (evaluation["estado"] or "").upper()
        status_class = "success" if status == "FINALIZADO" else "warning text-dark"

        actions = f"""
        <a href="{url_for('madurez_ai.ai_risk_detail', evaluacion_id=evaluation['id'])}" class="btn btn-sm btn-primary">
          <i class="bi bi-eye-fill"></i> Ver
        </a>
        """

        if user.role != "auditor":
            if status == "FINALIZADO":
                actions += f"""
                <a href="{url_for('madurez_ai.ai_risk_pdf', evaluacion_id=evaluation['id'])}" class="btn btn-sm btn-danger">
                  <i class="bi bi-file-earmark-pdf-fill"></i> PDF
                </a>
                """
            actions += f"""
            <form method="POST" action="{url_for('madurez_ai.ai_risk_delete', evaluacion_id=evaluation['id'])}"
                  class="d-inline" onsubmit="return confirm('¿Eliminar esta evaluación de riesgos de IA?');">
              <button class="btn btn-sm btn-dark"><i class="bi bi-trash-fill"></i> Eliminar</button>
            </form>
            """

        rows += f"""
        <tr>
          <td class="fw-bold">{escape(evaluation['consecutivo'] or '')}</td>
          <td>{escape(evaluation['nombre_proyecto'] or '')}</td>
          <td>{escape(evaluation['clasificacion_riesgo'] or 'Por determinar')}</td>
          <td class="text-center"><span class="badge bg-{status_class}">{escape(status)}</span></td>
          <td class="text-center">{int(evaluation['progreso_pct'] or 0)}%</td>
          <td class="text-center">{float(evaluation['cumplimiento_pct'] or 0):.2f}%</td>
          <td class="text-center"><span class="airisk-badge" style="background:{maturity['color']};">{escape(maturity['nivel'])}</span></td>
          <td class="text-center">{float(evaluation['exposicion_pct'] or 0):.2f}%</td>
          <td><div class="d-flex gap-1 flex-wrap justify-content-center">{actions}</div></td>
        </tr>
        """

    if not rows:
        rows = '<tr><td colspan="9" class="text-center text-muted py-4">No hay evaluaciones registradas.</td></tr>'

    new_button = "" if user.role == "auditor" else f"""
      <a href="{url_for('madurez_ai.ai_risk_form')}" class="btn btn-primary">
        <i class="bi bi-plus-circle me-2"></i>Nueva evaluación
      </a>
    """

    content = f"""
<div class="airisk-shell">
  {ai_header(
      "airisk",
      "Historial — Nivel de Madurez de Riesgos de IA",
      "Seguimiento de borradores y evaluaciones finalizadas con la escala de madurez IA y NIST AI RMF.",
      "🕘",
      "SGSI · NIST AI RMF"
  )}
  <div class="airisk-actions">
    <a href="{url_for('madurez_ai.ai_risk_home')}" class="btn btn-light border"><i class="bi bi-arrow-left me-2"></i>Volver</a>
    {new_button}
  </div>
  <div class="airisk-card">
    <div class="table-responsive">
      <table class="table table-hover align-middle airisk-table">
        <thead><tr>
          <th>Consecutivo</th><th>Proyecto / sistema</th><th>Clasificación</th><th>Estado</th>
          <th>Progreso</th><th>Controles</th><th>Nivel de madurez</th><th>Exposición</th><th>Acciones</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </div>
</div>
{ai_risk_css()}
"""
    return render_template_string(BASE, title="Historial de Madurez de Riesgos de IA", content=content)


@ai_madurez_bp.route("/riesgos/detalle/<int:evaluacion_id>", methods=["GET"])
@login_required
def ai_risk_detail(evaluacion_id):
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para consultar evaluaciones de riesgos de IA.", "danger")
        return redirect(url_for("menu"))

    evaluation = ai_risk_get_evaluation(evaluacion_id, user)
    if not evaluation:
        flash("No se encontró la evaluación o no tiene acceso.", "danger")
        return redirect(url_for("madurez_ai.ai_risk_history"))

    summary = ai_risk_recalculate(evaluacion_id)
    evaluation = ai_risk_get_evaluation(evaluacion_id, user)
    maturity = ai_risk_maturity_level(evaluation["cumplimiento_pct"])

    phase_rows = ""
    for phase in AI_RISK_PHASES:
        data = summary["fases"].get(phase["codigo"], {})
        phase_rows += f"""
        <tr>
          <td class="fw-bold">{escape(phase['nombre'])}</td>
          <td>{escape(phase['foco_nist'])}</td>
          <td class="text-center">{int(data.get('SI', 0))}</td>
          <td class="text-center">{int(data.get('PARCIAL', 0))}</td>
          <td class="text-center">{int(data.get('NO', 0))}</td>
          <td class="text-center">{int(data.get('NA', 0))}</td>
          <td class="text-center fw-bold">{float(data.get('cumplimiento_pct', 0)):.2f}%</td>
          <td class="text-center">{float(data.get('exposicion_pct', 0)):.2f}%</td>
          <td class="text-center"><span class="airisk-badge" style="background:{data.get('color', '#6c757d')};">{escape(data.get('nivel_madurez', ''))}</span></td>
        </tr>
        """

    function_rows = ""
    for key in ("GOVERN", "MAP", "MEASURE", "MANAGE"):
        data = summary["funciones"].get(key, {})
        color = AI_RISK_FUNCTIONS[key]["color"]
        function_rows += f"""
        <tr>
          <td><span class="airisk-badge" style="background:{color};">{key}</span></td>
          <td>{escape(AI_RISK_FUNCTIONS[key]['descripcion'])}</td>
          <td class="text-center">{int(data.get('total', 0))}</td>
          <td class="text-center fw-bold">{float(data.get('cumplimiento_pct', 0)):.2f}%</td>
          <td class="text-center">{float(data.get('exposicion_pct', 0)):.2f}%</td>
          <td class="text-center"><span class="airisk-badge" style="background:{data.get('color', '#6c757d')};">{escape(data.get('nivel_madurez', ''))}</span></td>
        </tr>
        """

    item_rows = ""
    status_colors = {
        "SI": "success",
        "PARCIAL": "warning text-dark",
        "NO": "danger",
        "NA": "secondary",
        "": "light text-dark",
    }

    for item in summary["items"]:
        state = item["estado"] or ""
        item_rows += f"""
        <tr>
          <td><span class="badge bg-light text-primary border">{escape(item['codigo'])}</span></td>
          <td><b>{escape(item['titulo'])}</b><br>{escape(item['pregunta'])}<br><span class="text-muted">Evidencia esperada: {escape(item['evidencia_sugerida'])}</span></td>
          <td><span class="airisk-badge" style="background:{AI_RISK_FUNCTIONS.get(item['nist_funcion'], {}).get('color', '#6c757d')};">{escape(item['nist_funcion'])}</span><br>{escape(item['nist_categoria'])}</td>
          <td class="text-center"><span class="badge bg-{status_colors.get(state, 'secondary')}">{escape(state or 'Pendiente')}</span></td>
          <td>{escape(item['comentario'] or '')}</td>
          <td>{escape(item['evidencia'] or '')}</td>
        </tr>
        """

    analysis_text = str(escape(evaluation["analisis_ai"] or "")).replace("\n", "<br>")
    plan_text = str(escape(evaluation["plan_tratamiento_ai"] or "")).replace("\n", "<br>")

    ai_button = ""
    pdf_button = ""
    if user.role != "auditor":
        if evaluation["estado"] == "FINALIZADO":
            ai_button = f"""
            <form method="POST" action="{url_for('madurez_ai.ai_risk_analyze', evaluacion_id=evaluacion_id)}" class="d-inline"
                  onsubmit="return confirm('¿Generar o actualizar el análisis ejecutivo con IA?');">
              <button class="btn btn-warning"><i class="bi bi-stars me-2"></i>Generar análisis con IA</button>
            </form>
            """
            pdf_button = f"""
            <a href="{url_for('madurez_ai.ai_risk_pdf', evaluacion_id=evaluacion_id)}" class="btn btn-danger">
              <i class="bi bi-file-earmark-pdf-fill me-2"></i>Exportar PDF
            </a>
            """

    content = f"""
<div class="airisk-shell">
  {ai_header(
      "airisk",
      "Resultado — Nivel de Madurez de Riesgos de IA",
      f"{escape(evaluation['consecutivo'])} · {escape(evaluation['nombre_proyecto'])}",
      "📊",
      "SGSI · NIST AI RMF"
  )}

  <div class="airisk-actions">
    <a href="{url_for('madurez_ai.ai_risk_history')}" class="btn btn-light border"><i class="bi bi-arrow-left me-2"></i>Historial</a>
    <a href="{url_for('madurez_ai.ai_risk_home')}" class="btn btn-outline-primary"><i class="bi bi-house-door me-2"></i>Inicio del submódulo</a>
    {ai_button}
    {pdf_button}
  </div>

  <div class="row g-3 mb-3">
    <div class="col-6 col-lg-3"><div class="airisk-kpi"><div class="airisk-kpi-value">{int(evaluation['progreso_pct'] or 0)}%</div><div class="airisk-kpi-label">Progreso</div></div></div>
    <div class="col-6 col-lg-3"><div class="airisk-kpi"><div class="airisk-kpi-value">{float(evaluation['cumplimiento_pct'] or 0):.2f}%</div><div class="airisk-kpi-label">Controles implementados</div></div></div>
    <div class="col-6 col-lg-3"><div class="airisk-kpi"><div class="airisk-kpi-value">{float(evaluation['exposicion_pct'] or 0):.2f}%</div><div class="airisk-kpi-label">Exposición de riesgo</div></div></div>
    <div class="col-6 col-lg-3"><div class="airisk-kpi"><div class="airisk-kpi-value" style="color:{maturity['color']};">{maturity['score']}/5</div><div class="airisk-kpi-label">{escape(maturity['nivel'])}</div></div></div>
  </div>

  <div class="airisk-card mb-3">
    <div class="airisk-section">Información de la evaluación</div>
    <div class="row g-2 small">
      <div class="col-md-3"><b>Estado:</b> {escape(evaluation['estado'])}</div>
      <div class="col-md-3"><b>Clasificación:</b> {escape(evaluation['clasificacion_riesgo'] or 'Por determinar')}</div>
      <div class="col-md-3"><b>Responsable:</b> {escape(evaluation['responsable'] or '')}</div>
      <div class="col-md-3"><b>Fecha:</b> {escape(evaluation['created_at'] or '')}</div>
      <div class="col-md-6"><b>Caso de uso:</b> {escape(evaluation['caso_uso'] or '')}</div>
      <div class="col-md-6"><b>Descripción:</b> {escape(evaluation['descripcion'] or '')}</div>
    </div>
  </div>

  <div class="airisk-card mb-3">
    <div class="airisk-section">Resultado por fase del ciclo de vida</div>
    <div class="table-responsive"><table class="table table-hover airisk-table">
      <thead><tr><th>Fase</th><th>Foco NIST</th><th>Sí</th><th>Parcial</th><th>No</th><th>N/A</th><th>Controles</th><th>Exposición</th><th>Nivel de madurez</th></tr></thead>
      <tbody>{phase_rows}</tbody>
    </table></div>
  </div>

  <div class="airisk-card mb-3">
    <div class="airisk-section">Resultado por función NIST AI RMF</div>
    <div class="table-responsive"><table class="table table-hover airisk-table">
      <thead><tr><th>Función</th><th>Propósito</th><th>Preguntas</th><th>Controles</th><th>Exposición</th><th>Nivel de madurez</th></tr></thead>
      <tbody>{function_rows}</tbody>
    </table></div>
  </div>

  <div class="row g-3 mb-3">
    <div class="col-12 col-lg-6">
      <div class="airisk-card h-100">
        <div class="airisk-section">Análisis ejecutivo con IA</div>
        <div class="airisk-analysis">{analysis_text or 'No se ha generado el análisis ejecutivo.'}</div>
      </div>
    </div>
    <div class="col-12 col-lg-6">
      <div class="airisk-card h-100">
        <div class="airisk-section">Plan de tratamiento</div>
        <div class="airisk-analysis">{plan_text or 'No se ha generado el plan de tratamiento.'}</div>
      </div>
    </div>
  </div>

  <div class="airisk-card">
    <div class="airisk-section">Detalle de respuestas y evidencias</div>
    <div class="table-responsive"><table class="table table-hover airisk-table">
      <thead><tr><th>Código</th><th>Pregunta</th><th>NIST</th><th>Respuesta</th><th>Comentario</th><th>Evidencia</th></tr></thead>
      <tbody>{item_rows}</tbody>
    </table></div>
  </div>
</div>
{ai_risk_css()}
"""
    return render_template_string(BASE, title="Resultado de Madurez de Riesgos de IA", content=content)


def ai_risk_prompt(evaluation, summary):
    gaps = []
    for item in summary.get("items", []):
        if item.get("estado") in ("NO", "PARCIAL"):
            gaps.append(
                f"- {item.get('codigo')} | {item.get('nist_funcion')} {item.get('nist_categoria')} | "
                f"{item.get('titulo')} | Respuesta: {item.get('estado')} | "
                f"Comentario: {item.get('comentario') or 'Sin comentario'} | "
                f"Evidencia: {item.get('evidencia') or 'Sin evidencia'}"
            )

    gap_text = "\n".join(gaps) if gaps else "No se identificaron respuestas NO o PARCIAL."

    return f"""
Actúa como consultor senior en gestión de riesgos de Inteligencia Artificial y NIST AI RMF.
Analiza una evaluación interna basada en las funciones GOVERN, MAP, MEASURE y MANAGE.

DATOS
Proyecto: {evaluation['nombre_proyecto']}
Consecutivo: {evaluation['consecutivo']}
Caso de uso: {evaluation['caso_uso'] or 'No informado'}
Clasificación regulatoria: {evaluation['clasificacion_riesgo'] or 'Por determinar'}
Controles implementados: {float(summary.get('cumplimiento_pct', 0)):.2f}%
Exposición: {float(summary.get('exposicion_pct', 0)):.2f}%
Nivel de madurez de riesgos: {summary.get('nivel_madurez', '')}
Puntuación de madurez: {int(summary.get('madurez_score', 0) or 0)}/5

BRECHAS
{gap_text}

Devuelve solamente JSON válido con esta estructura:
{{
  "analisis_ejecutivo": "4 a 7 párrafos breves con alcance, fortalezas, brechas, riesgos e implicaciones",
  "plan_tratamiento": [
    {{
      "prioridad": "Alta|Media|Baja",
      "funcion_nist": "GOVERN|MAP|MEASURE|MANAGE",
      "accion": "acción concreta",
      "responsable_sugerido": "rol",
      "plazo": "plazo",
      "evidencia_esperada": "evidencia verificable"
    }}
  ]
}}

Genera entre 6 y 12 acciones, prioriza respuestas NO y PARCIAL, no inventes hechos ni herramientas.
""".strip()


@ai_madurez_bp.route("/riesgos/detalle/<int:evaluacion_id>/analizar-ai", methods=["POST"])
@login_required
def ai_risk_analyze(evaluacion_id):
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user) or user.role == "auditor":
        flash("No tiene permiso para generar análisis de riesgos con IA.", "danger")
        return redirect(url_for("madurez_ai.ai_risk_home"))

    evaluation = ai_risk_get_evaluation(evaluacion_id, user)
    if not evaluation:
        flash("No se encontró la evaluación.", "danger")
        return redirect(url_for("madurez_ai.ai_risk_history"))

    if evaluation["estado"] != "FINALIZADO":
        flash("Debes finalizar la evaluación antes de generar el análisis con IA.", "warning")
        return redirect(url_for("madurez_ai.ai_risk_detail", evaluacion_id=evaluacion_id))

    summary = ai_risk_recalculate(evaluacion_id)

    try:
        raw = _ai_call_text(ai_risk_prompt(evaluation, summary), max_tokens=1800)
        obj = _ai_extraer_json_objeto(raw)
        analysis = _ai_normalizar_texto(
            obj.get("analisis_ejecutivo") if isinstance(obj, dict) else raw
        )

        plan_items = obj.get("plan_tratamiento", []) if isinstance(obj, dict) else []
        lines = []
        for index, item in enumerate(plan_items, start=1):
            lines.append(
                f"{index}. Prioridad: {_ai_normalizar_texto(item.get('prioridad')) or 'Sin definir'}\n"
                f"   Función NIST: {_ai_normalizar_texto(item.get('funcion_nist')) or 'Sin definir'}\n"
                f"   Acción: {_ai_normalizar_texto(item.get('accion')) or 'Sin definir'}\n"
                f"   Responsable: {_ai_normalizar_texto(item.get('responsable_sugerido')) or 'Sin definir'}\n"
                f"   Plazo: {_ai_normalizar_texto(item.get('plazo')) or 'Sin definir'}\n"
                f"   Evidencia esperada: {_ai_normalizar_texto(item.get('evidencia_esperada')) or 'Sin definir'}"
            )

        plan = "\n\n".join(lines).strip()
        conn = get_ai_madurez_conn()
        conn.execute("""
            UPDATE ai_risk_evaluaciones
            SET analisis_ai = ?,
                plan_tratamiento_ai = ?,
                updated_at = ?
            WHERE id = ?
        """, (analysis, plan, _ai_now(), evaluacion_id))
        conn.commit()
        conn.close()
        flash("✅ Análisis ejecutivo y plan de tratamiento generados.", "success")

    except Exception as error:
        flash(f"❌ No fue posible generar el análisis con IA: {error}", "danger")

    return redirect(url_for("madurez_ai.ai_risk_detail", evaluacion_id=evaluacion_id))


@ai_madurez_bp.route("/riesgos/eliminar/<int:evaluacion_id>", methods=["POST"])
@login_required
def ai_risk_delete(evaluacion_id):
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user) or user.role == "auditor":
        flash("No tiene permiso para eliminar evaluaciones de riesgos de IA.", "danger")
        return redirect(url_for("madurez_ai.ai_risk_home"))

    evaluation = ai_risk_get_evaluation(evaluacion_id, user)
    if not evaluation:
        flash("No se encontró la evaluación o no tiene acceso.", "danger")
        return redirect(url_for("madurez_ai.ai_risk_history"))

    conn = get_ai_madurez_conn()
    conn.execute("DELETE FROM ai_risk_respuestas WHERE evaluacion_id = ?", (evaluacion_id,))
    conn.execute("DELETE FROM ai_risk_evaluaciones WHERE id = ?", (evaluacion_id,))
    conn.commit()
    conn.close()

    flash("✅ Evaluación de riesgos de IA eliminada.", "success")
    return redirect(url_for("madurez_ai.ai_risk_history"))


def ai_risk_build_pdf(evaluacion_id):
    conn = get_ai_madurez_conn()
    evaluation = conn.execute(
        "SELECT * FROM ai_risk_evaluaciones WHERE id = ?",
        (evaluacion_id,)
    ).fetchone()
    conn.close()

    if not evaluation:
        raise ValueError("Evaluación no encontrada.")

    summary = ai_risk_build_summary(evaluacion_id)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1.1 * cm,
        leftMargin=1.1 * cm,
        topMargin=1.1 * cm,
        bottomMargin=1.1 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AIRiskTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=18, textColor=colors.HexColor("#0b4a8f"), spaceAfter=10
    )
    section_style = ParagraphStyle(
        "AIRiskSection", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=11, textColor=colors.HexColor("#0b4a8f"), spaceBefore=8, spaceAfter=6
    )
    normal_style = ParagraphStyle(
        "AIRiskNormal", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8, leading=10, textColor=colors.HexColor("#1e293b")
    )
    small_style = ParagraphStyle(
        "AIRiskSmall", parent=normal_style, fontSize=6.7, leading=8
    )

    def p(value, style=normal_style):
        return Paragraph(html.escape(str(value or "")).replace("\n", "<br/>"), style)

    story = [
        Paragraph("Nivel de Madurez de Riesgos de Inteligencia Artificial — NIST AI RMF", title_style),
        p(f"Consecutivo: {evaluation['consecutivo']} | Proyecto: {evaluation['nombre_proyecto']} | Estado: {evaluation['estado']}"),
        p(f"Responsable: {evaluation['responsable'] or ''} | Clasificación: {evaluation['clasificacion_riesgo'] or 'Por determinar'} | Fecha: {evaluation['created_at']}"),
        Spacer(1, 8),
    ]

    maturity = ai_risk_maturity_level(summary["cumplimiento_pct"])
    kpi_data = [
        ["Progreso", "Controles implementados", "Exposición", "Nivel de madurez"],
        [
            f"{summary['progreso_pct']}%",
            f"{summary['cumplimiento_pct']:.2f}%",
            f"{summary['exposicion_pct']:.2f}%",
            maturity["nivel"],
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[6.7 * cm] * 4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b4a8f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([kpi_table, Spacer(1, 8), Paragraph("Resultado por fase", section_style)])

    phase_data = [["Fase", "Foco NIST", "Sí", "Parcial", "No", "N/A", "Controles", "Exposición", "Nivel de madurez"]]
    for phase in AI_RISK_PHASES:
        data = summary["fases"].get(phase["codigo"], {})
        phase_data.append([
            p(phase["nombre"], small_style),
            p(phase["foco_nist"], small_style),
            str(data.get("SI", 0)),
            str(data.get("PARCIAL", 0)),
            str(data.get("NO", 0)),
            str(data.get("NA", 0)),
            f"{float(data.get('cumplimiento_pct', 0)):.2f}%",
            f"{float(data.get('exposicion_pct', 0)):.2f}%",
            p(data.get("nivel_madurez", ""), small_style),
        ])

    phase_table = Table(
        phase_data,
        colWidths=[5.2 * cm, 3.2 * cm, 1.1 * cm, 1.4 * cm, 1.1 * cm, 1.1 * cm, 2.2 * cm, 2.0 * cm, 2.0 * cm],
        repeatRows=1
    )
    phase_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5fa9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (2, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([phase_table, Spacer(1, 8), Paragraph("Detalle de respuestas", section_style)])

    detail_data = [["Código", "Fase", "NIST", "Pregunta", "Respuesta", "Comentario / evidencia"]]
    for item in summary["items"]:
        detail_data.append([
            p(item["codigo"], small_style),
            p(item["fase_codigo"], small_style),
            p(f"{item['nist_funcion']} {item['nist_categoria']}", small_style),
            p(f"{item['titulo']}: {item['pregunta']}", small_style),
            p(item["estado"] or "Pendiente", small_style),
            p((item["comentario"] or "") + ("\nEvidencia: " + item["evidencia"] if item["evidencia"] else ""), small_style),
        ])

    detail_table = Table(
        detail_data,
        colWidths=[1.6 * cm, 1.2 * cm, 2.5 * cm, 12.2 * cm, 1.8 * cm, 7.5 * cm],
        repeatRows=1
    )
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5fa9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(detail_table)

    if evaluation["analisis_ai"] or evaluation["plan_tratamiento_ai"]:
        story.append(PageBreak())
        if evaluation["analisis_ai"]:
            story.extend([
                Paragraph("Análisis ejecutivo", section_style),
                p(evaluation["analisis_ai"]),
                Spacer(1, 8),
            ])
        if evaluation["plan_tratamiento_ai"]:
            story.extend([
                Paragraph("Plan de tratamiento", section_style),
                p(evaluation["plan_tratamiento_ai"]),
            ])

    doc.build(story)
    buffer.seek(0)
    return buffer


@ai_madurez_bp.route("/riesgos/detalle/<int:evaluacion_id>/pdf", methods=["GET"])
@login_required
def ai_risk_pdf(evaluacion_id):
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para exportar evaluaciones de riesgos de IA.", "danger")
        return redirect(url_for("menu"))

    evaluation = ai_risk_get_evaluation(evaluacion_id, user)
    if not evaluation:
        flash("No se encontró la evaluación o no tiene acceso.", "danger")
        return redirect(url_for("madurez_ai.ai_risk_history"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede exportar PDF en este módulo.", "warning")
        return redirect(url_for("madurez_ai.ai_risk_detail", evaluacion_id=evaluacion_id))

    try:
        pdf = ai_risk_build_pdf(evaluacion_id)
    except Exception as error:
        flash(f"❌ No fue posible generar el PDF: {error}", "danger")
        return redirect(url_for("madurez_ai.ai_risk_detail", evaluacion_id=evaluacion_id))

    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", evaluation["consecutivo"] or str(evaluacion_id))
    return send_file(
        pdf,
        as_attachment=True,
        download_name=f"Madurez_Riesgos_IA_{safe_name}.pdf",
        mimetype="application/pdf"
    )


# ============================================================================================================================================
#                       FIN MÓDULO NIVEL DE MADUREZ — GESTIÓN DE IA ISO 42001
# ============================================================================================================================================


# ==========================================================================================================================================
#                                                   Módulo de Listas Restrictivas
# ==========================================================================================================================================

ALLOWED_LISTAS_EXT = {'txt', 'csv'}

def allowed_listas_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_LISTAS_EXT

def asegurar_permiso_listas_restrictivas():
    try:
        usuarios = User.query.all()
        for u in usuarios:
            existe = UserPermission.query.filter_by(
                user_id=u.id,
                module_name="Listas Restrictivas"
            ).first()

            if not existe:
                db.session.add(UserPermission(
                    user_id=u.id,
                    module_name="Listas Restrictivas",
                    has_access=(u.role == 'admin')
                ))
        db.session.commit()
    except Exception as e:
        print("Error creando permiso de Listas Restrictivas:", repr(e))

def _normalizar_texto_lista(txt):
    txt = (txt or '').strip().lower()
    txt = ''.join(
        c for c in unicodedata.normalize('NFKD', txt)
        if not unicodedata.combining(c)
    )
    txt = re.sub(r'[^a-z0-9\s]', ' ', txt)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt

def _score_nombre_lista(a, b):
    a_n = _normalizar_texto_lista(a)
    b_n = _normalizar_texto_lista(b)

    if not a_n or not b_n:
        return 0.0

    if a_n == b_n:
        return 100.0

    ta = set(a_n.split())
    tb = set(b_n.split())

    if not ta or not tb:
        return 0.0

    inter = len(ta & tb)
    union = len(ta | tb)
    score = (inter / union) * 100 if union else 0.0

    if a_n in b_n or b_n in a_n:
        score = max(score, 92.0)

    return round(score, 2)

def _clasificar_resultado_lista(score, documento_match=False):
    if documento_match:
        return "Coincidencia exacta", "Alto"

    if score >= 95:
        return "Coincidencia exacta", "Alto"
    elif score >= 80:
        return "Coincidencia probable", "Medio"
    return "Sin coincidencias", "Bajo"

def _http_json_or_none(url, timeout=25, headers=None):
    try:
        r = requests.get(url, timeout=timeout, headers=headers or {})
        if r.status_code == 200:
            try:
                return r.json()
            except Exception:
                return None
        return None
    except Exception:
        return None

def _limpiar_nombre_persona(txt):
    txt = _normalizar_texto_lista(txt)

    stopwords = {
        "mr", "mrs", "ms", "dr", "dra", "doctor", "sr", "sra", "sir",
        "sheikh", "haji", "prof", "profesor", "and", "of", "the"
    }

    partes = [p for p in txt.split() if p and p not in stopwords and len(p) > 1]
    return " ".join(partes).strip()


def _score_nombre_persona_consulta(nombre_consulta, nombre_lista):
    a = _limpiar_nombre_persona(nombre_consulta)
    b = _limpiar_nombre_persona(nombre_lista)

    if not a or not b:
        return 0.0

    ta = a.split()
    tb = b.split()

    if len(ta) < 2 or len(tb) < 2:
        return 0.0

    set_a = set(ta)
    set_b = set(tb)

    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    score = (inter / union) * 100 if union else 0.0

    if inter >= 3:
        score += 10
    elif inter == 2:
        score += 4

    if len(tb) <= 2:
        score -= 15

    return round(max(0.0, min(score, 100.0)), 2)


def _extraer_candidatos_xml_texto(root):
    candidatos = set()

    for elem in root.iter():
        texto = " ".join(t.strip() for t in elem.itertext() if t and t.strip())
        texto = re.sub(r"\s+", " ", texto).strip()

        if not texto:
            continue

        if len(texto) < 8:
            continue

        if re.fullmatch(r"[\d\W_]+", texto):
            continue

        partes = texto.split()
        if len(partes) < 2:
            continue

        candidatos.add(texto)

    return list(candidatos)

def consultar_listas_externas(nombre, tipo_documento=None, numero_documento=None, pais=None):
    resultados = []
    numero_documento = (numero_documento or "").strip()
    pais = (pais or "").strip()

    fuentes_externas = [
        {
            "fuente": "ONU",
            "url": "https://scsanctions.un.org/resources/xml/en/consolidated.xml",
            "tipo": "xml"
        },
        {
            "fuente": "OFAC",
            "url": "https://www.treasury.gov/ofac/downloads/sdn.xml",
            "tipo": "xml"
        }
    ]

    vistos = set()

    for fuente_cfg in fuentes_externas:
        fuente = fuente_cfg["fuente"]
        url = fuente_cfg["url"]
        tipo = fuente_cfg["tipo"]

        try:
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                continue

            if tipo == "xml":
                root = ET.fromstring(r.content)
                candidatos = _extraer_candidatos_xml_texto(root)

                for candidato in candidatos:
                    score_final = _score_nombre_persona_consulta(nombre, candidato)

                    documento_match = False
                    if numero_documento and numero_documento in candidato:
                        documento_match = True
                        score_final = 100.0

                    resultado, nivel = _clasificar_resultado_lista(
                        score_final,
                        documento_match=documento_match
                    )

                    if not documento_match and score_final < 85:
                        continue

                    clave = (fuente, _normalizar_texto_lista(candidato))
                    if clave in vistos:
                        continue
                    vistos.add(clave)

                    resultados.append({
                        "fuente": fuente,
                        "nombre": candidato,
                        "alias": "",
                        "tipo_documento": tipo_documento or "",
                        "numero_documento": numero_documento or "",
                        "pais": pais or "",
                        "categoria": "Lista externa",
                        "observaciones": f"Coincidencia detectada desde {fuente}",
                        "score": score_final,
                        "resultado": resultado,
                        "nivel_riesgo": nivel
                    })

        except Exception as e:
            print(f"Error consultando fuente externa {fuente}: {repr(e)}")
            continue

    resultados = sorted(resultados, key=lambda x: x["score"], reverse=True)
    return resultados[:20]

def consultar_listas_restrictivas_global(nombre, tipo_documento=None, numero_documento=None, pais=None):
    """
    Consolida consulta local + externas.
    """
    local_result = consultar_listas_restrictivas_local(
        nombre=nombre,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        pais=pais
    )

    externas = consultar_listas_externas(
        nombre=nombre,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        pais=pais
    )

    detalle_total = []
    if local_result.get("detalle"):
        detalle_total.extend(local_result["detalle"])
    if externas:
        detalle_total.extend(externas)

    detalle_total = sorted(detalle_total, key=lambda x: x.get("score", 0), reverse=True)

    if not detalle_total:
        return {
            "fuente": "Local + Externas",
            "resultado": "Sin coincidencias",
            "nivel_riesgo": "Bajo",
            "score": 0.0,
            "detalle": []
        }

    mejor = detalle_total[0]
    return {
        "fuente": "Local + Externas",
        "resultado": mejor.get("resultado", "Sin coincidencias"),
        "nivel_riesgo": mejor.get("nivel_riesgo", "Bajo"),
        "score": mejor.get("score", 0.0),
        "detalle": detalle_total[:20]
    }

def _resolver_fuente_detectada(resultado):
    """
    Devuelve una cadena con las fuentes reales detectadas, por ejemplo:
    'ONU', 'OFAC', 'Lista Local' o 'OFAC, ONU'
    """
    detalle = resultado.get("detalle") or []

    if not detalle:
        return resultado.get("fuente", "No especificado")

    fuentes = []
    for item in detalle:
        fuente = (item.get("fuente") or "").strip()
        if fuente and fuente not in fuentes:
            fuentes.append(fuente)

    if not fuentes:
        return resultado.get("fuente", "No especificado")

    return ", ".join(fuentes)

def cargar_fuente_lista_desde_archivo(file_storage, fuente_default="Carga Archivo"):
    if not file_storage or not file_storage.filename:
        return 0, 0

    if not allowed_listas_file(file_storage.filename):
        raise ValueError("Archivo no permitido. Use .txt o .csv")

    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit('.', 1)[1].lower()

    contenido = file_storage.read()
    if isinstance(contenido, bytes):
        contenido = contenido.decode('utf-8', errors='ignore')

    insertados = 0
    omitidos = 0

    conn = get_listas_db_connection()
    cur = conn.cursor()

    if ext == 'txt':
        lineas = [ln.strip() for ln in contenido.splitlines() if ln.strip()]
        for linea in lineas:
            partes = [p.strip() for p in linea.split('|')]
            nombre = partes[0] if len(partes) > 0 else ''
            numero_documento = partes[1] if len(partes) > 1 else ''
            pais = partes[2] if len(partes) > 2 else ''
            categoria = partes[3] if len(partes) > 3 else ''

            if not nombre:
                omitidos += 1
                continue

            cur.execute("""
                INSERT INTO listas_restrictivas_fuente (
                    fuente, nombre, alias, tipo_documento, numero_documento, pais,
                    categoria, observaciones, activo, fecha_actualizacion
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Sí', ?)
            """, (
                fuente_default,
                nombre,
                '',
                '',
                numero_documento,
                pais,
                categoria,
                f'Cargado desde archivo plano: {filename}',
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            insertados += 1

    elif ext == 'csv':
        reader = csv.DictReader(io.StringIO(contenido))
        for row in reader:
            nombre = (row.get('nombre') or '').strip()
            alias = (row.get('alias') or '').strip()
            tipo_documento = (row.get('tipo_documento') or '').strip()
            numero_documento = (row.get('numero_documento') or '').strip()
            pais = (row.get('pais') or '').strip()
            categoria = (row.get('categoria') or '').strip()
            observaciones = (row.get('observaciones') or '').strip()

            if not nombre:
                omitidos += 1
                continue

            cur.execute("""
                INSERT INTO listas_restrictivas_fuente (
                    fuente, nombre, alias, tipo_documento, numero_documento, pais,
                    categoria, observaciones, activo, fecha_actualizacion
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Sí', ?)
            """, (
                fuente_default,
                nombre,
                alias,
                tipo_documento,
                numero_documento,
                pais,
                categoria,
                observaciones,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            insertados += 1

    conn.commit()
    conn.close()

    return insertados, omitidos

def get_consulta_lista_by_id(consulta_id):
    conn = get_listas_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM listas_restrictivas_consultas
        WHERE id = ?
    """, (consulta_id,))
    row = cur.fetchone()
    conn.close()
    return row


def delete_consulta_lista_by_id(consulta_id):
    conn = get_listas_db_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM listas_restrictivas_consultas
        WHERE id = ?
    """, (consulta_id,))
    conn.commit()
    cambios = cur.rowcount
    conn.close()
    return cambios > 0


def consultar_listas_restrictivas_local(nombre, tipo_documento=None, numero_documento=None, pais=None):
    conn = get_listas_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM listas_restrictivas_fuente
        WHERE activo = 'Sí'
    """)
    rows = cur.fetchall()
    conn.close()

    mejor = None
    coincidencias = []

    for r in rows:
        score_nombre = _score_nombre_lista(nombre, r["nombre"])
        documento_match = False

        if numero_documento and r["numero_documento"]:
            documento_match = (str(numero_documento).strip() == str(r["numero_documento"]).strip())

        score_final = 100.0 if documento_match else score_nombre
        resultado, nivel = _clasificar_resultado_lista(score_final, documento_match=documento_match)

        item = {
            "id": r["id"],
            "fuente": r["fuente"],
            "nombre": r["nombre"],
            "alias": r["alias"],
            "tipo_documento": r["tipo_documento"],
            "numero_documento": r["numero_documento"],
            "pais": r["pais"],
            "categoria": r["categoria"],
            "observaciones": r["observaciones"],
            "score": score_final,
            "resultado": resultado,
            "nivel_riesgo": nivel
        }

        if documento_match or score_final >= 80:
            coincidencias.append(item)

        if mejor is None or score_final > mejor["score"]:
            mejor = item

    if not mejor or mejor["score"] < 80:
        return {
            "fuente": "Lista Local",
            "resultado": "Sin coincidencias",
            "nivel_riesgo": "Bajo",
            "score": 0.0,
            "detalle": []
        }

    coincidencias = sorted(coincidencias, key=lambda x: x["score"], reverse=True)

    return {
        "fuente": "Lista Local",
        "resultado": mejor["resultado"],
        "nivel_riesgo": mejor["nivel_riesgo"],
        "score": mejor["score"],
        "detalle": coincidencias[:10]
    }

def registrar_consulta_lista_db(origen, proveedor_id, nombre_consultado, tipo_documento, numero_documento,
                                pais, fuente, resultado, nivel_riesgo, score, detalle,
                                observaciones, usuario):
    fecha_consulta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_listas_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO listas_restrictivas_consultas (
            origen, proveedor_id, nombre_consultado, tipo_documento, numero_documento, pais,
            fuente, resultado, nivel_riesgo, score_coincidencia,
            detalle_json, observaciones, usuario, fecha_consulta
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        origen,
        proveedor_id,
        nombre_consultado,
        tipo_documento,
        numero_documento,
        pais,
        fuente,
        resultado,
        nivel_riesgo,
        score,
        json.dumps(detalle, ensure_ascii=False),
        observaciones,
        usuario,
        fecha_consulta
    ))
    conn.commit()
    conn.close()

    if proveedor_id:
        upsert_estado_lista_proveedor(
            proveedor_id=proveedor_id,
            resultado=resultado,
            riesgo=nivel_riesgo,
            score=score,
            fecha_consulta=fecha_consulta,
            fuente=fuente
        )

    return fecha_consulta

@app.route('/listas_restrictivas', methods=['GET'])
@login_required
def listas_restrictivas_home():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Listas Restrictivas"):
            flash("No tiene permiso para acceder al módulo de Listas Restrictivas.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    conn = get_listas_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) AS total_base
        FROM listas_restrictivas_fuente
        WHERE activo = 'Sí'
    """)
    total_base = cur.fetchone()["total_base"]

    cur.execute("""
        SELECT COUNT(*) AS total_consultas
        FROM listas_restrictivas_consultas
    """)
    total_consultas = cur.fetchone()["total_consultas"]

    cur.execute("""
        SELECT id, fecha_consulta, nombre_consultado, resultado
        FROM listas_restrictivas_consultas
        ORDER BY fecha_consulta DESC, id DESC
        LIMIT 20
    """)
    ultimas_consultas = cur.fetchall()
    conn.close()

    html = """
    <div class="lr-shell">

      <!-- HEADER -->
      <div class="lr-header-card">
        <div class="lr-header-overlay">
          <div class="lr-header-text">
            <h3 class="lr-title m-0">Módulo de Listas Restrictivas</h3>
            <div class="lr-subtitle">
              Consulta consolidada contra listas externas y base local, administración de fuentes y trazabilidad histórica
            </div>
          </div>
        </div>
      </div>

      <!-- KPIs -->
      <div class="row g-3 mb-3">
        <div class="col-md-4">
          <div class="lr-kpi-card">
            <div class="lr-kpi-label">Registros activos base local</div>
            <div class="lr-kpi-value text-danger">{{ total_base }}</div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="lr-kpi-card">
            <div class="lr-kpi-label">Consultas realizadas</div>
            <div class="lr-kpi-value text-primary">{{ total_consultas }}</div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="lr-kpi-card">
            <div class="lr-kpi-label">Fuentes consultadas</div>
            <div class="lr-kpi-value text-dark">Local + Externas</div>
          </div>
        </div>
      </div>

      <!-- ACCIONES -->
      <div class="row g-3 mb-3">
        <div class="col-md-6">
          <div class="lr-action-card">
            <div class="lr-action-icon"><i class="bi bi-search"></i></div>
            <div class="lr-action-title">Consultar listas restrictivas</div>
            <div class="lr-action-desc">
              Realice búsqueda contra base local y listas externas como OFAC y ONU.
            </div>

            <div class="mt-3">
              <a href="{{ url_for('listas_restrictivas_consulta_manual') }}"
                 class="btn btn-primary rounded-pill px-4 fw-bold">
                Ir a consultar
              </a>
            </div>
          </div>
        </div>

        <div class="col-md-6">
          <div class="lr-action-card">
            <div class="lr-action-icon"><i class="bi bi-database"></i></div>
            <div class="lr-action-title">Administrar base local</div>
            <div class="lr-action-desc">
              Cree registros manuales o cargue archivos TXT / CSV.
            </div>

            <div class="mt-3">
              {% if current_user.role == 'admin' %}
              <a href="{{ url_for('listas_restrictivas_base') }}"
                 class="btn btn-primary rounded-pill px-4 fw-bold">
                Ir a la base
              </a>
              {% else %}
              <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
                Solo administrador
              </button>
              {% endif %}
            </div>
          </div>
        </div>
      </div>

      <!-- TABLA -->
      <div class="lr-table-card">
        <div class="lr-table-card-body">

          <h5 class="fw-bold mb-3">Últimas consultas</h5>

          {% if ultimas_consultas %}
          <div class="table-responsive">
            <table class="table table-bordered align-middle lr-table">
              <thead>
                <tr class="text-center">
                  <th>Fecha</th>
                  <th>Nombre</th>
                  <th>Resultado</th>
                  <th>Acciones</th>
                </tr>
              </thead>

              <tbody>
                {% for r in ultimas_consultas %}
                <tr>
                  <td>{{ r['fecha_consulta'] }}</td>
                  <td>{{ r['nombre_consultado'] }}</td>

                  <td class="text-center">
                    {% if r['resultado'] == 'Sin coincidencias' %}
                      <span class="badge bg-success">{{ r['resultado'] }}</span>
                    {% elif r['resultado'] == 'Coincidencia probable' %}
                      <span class="badge bg-warning text-dark">{{ r['resultado'] }}</span>
                    {% else %}
                      <span class="badge bg-danger">{{ r['resultado'] }}</span>
                    {% endif %}
                  </td>

                  <td class="text-center">
                    <a href="{{ url_for('listas_restrictivas_detalle', consulta_id=r['id']) }}"
                       class="btn btn-sm btn-primary rounded-pill px-3 fw-bold">
                      Ver
                    </a>
                  </td>
                </tr>
                {% endfor %}
              </tbody>

            </table>
          </div>
          {% else %}
          <div class="alert alert-info">No hay consultas registradas.</div>
          {% endif %}

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

      .lr-shell{
        width:96%;
        max-width:1700px;
        margin:10px auto 24px auto;
      }

      .lr-header-card{
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
        margin-bottom:10px;
      }

      .lr-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .lr-header-overlay{
        width:100%;
        height:auto;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }

      .lr-header-overlay::before{
        content:"🚨";
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

      .lr-header-text,
      .lr-header-overlay > div{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .lr-header-text::before,
      .lr-header-overlay > div::before{
        content:"SGSI · Listas Restrictivas";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .lr-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .lr-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .lr-kpi-card,
      .lr-action-card,
      .lr-table-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        height:100%;
      }

      .lr-kpi-card{
        padding:18px;
        text-align:center;
      }

      .lr-kpi-label{
        color:#475569;
        font-weight:900;
        font-size:.78rem;
        text-transform:uppercase;
        letter-spacing:.35px;
        margin-bottom:8px;
      }

      .lr-kpi-value{
        font-size:1.85rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1.1;
      }

      .lr-action-card{
        padding:18px;
        text-align:center;
        transition:all .2s ease;
      }

      .lr-action-card:hover{
        transform:translateY(-3px);
        box-shadow:0 16px 28px rgba(15,23,42,.22);
      }

      .lr-action-icon{
        width:52px;
        height:52px;
        border-radius:14px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.55rem;
        margin:0 auto 10px auto;
      }

      .lr-action-title{
        font-weight:950;
        font-size:.92rem;
        color:#0f172a;
      }

      .lr-action-desc{
        color:#475569;
        font-size:.78rem;
        margin-top:6px;
        line-height:1.35;
      }

      .lr-table-card-body{
        padding:14px 16px 16px 16px;
      }

      .lr-table-wrap,
      .table-responsive{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .lr-table{
        margin-bottom:0;
      }

      .lr-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border:none !important;
        font-size:.78rem;
        padding:9px 8px;
      }

      .lr-table th,
      .lr-table td{
        vertical-align:middle;
        font-size:.82rem;
        padding:9px 8px;
        word-break:break-word;
      }

      .lr-table td{
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .lr-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .lr-table tbody tr:hover td{
        background:#eef6ff;
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .btn.rounded-pill{
        border-radius:10px !important;
      }

      .lr-shell .btn{
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      @media (max-width:992px){
        .lr-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .lr-header-card{
          min-height:88px;
        }

        .lr-title{
          font-size:1.20rem;
        }

        .lr-table-card-body{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .lr-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .lr-header-overlay::before{
          margin:0;
        }

        .lr-header-text::before,
        .lr-header-overlay > div::before{
          margin-left:auto;
          margin-right:auto;
        }
      }
    </style>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            html,
            total_base=total_base,
            total_consultas=total_consultas,
            ultimas_consultas=ultimas_consultas,
            read_only=read_only
        ))
    )

@app.route('/listas_restrictivas/detalle/<int:consulta_id>', methods=['GET'])
@login_required
def listas_restrictivas_detalle(consulta_id):
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Listas Restrictivas"):
        flash("No tiene permiso para ver el detalle de listas restrictivas.", "danger")
        return redirect(url_for('menu'))

    consulta = get_consulta_lista_by_id(consulta_id)
    if not consulta:
        flash("La consulta seleccionada no existe.", "danger")
        return redirect(url_for('listas_restrictivas_home'))

    html = """
    <div class="lr-shell">

      <div class="lr-header-card">
        <div class="lr-header-overlay">
          <div class="lr-header-text">
            <h3 class="lr-title m-0">Detalle de Consulta de Listas Restrictivas</h3>
            <div class="lr-subtitle">
              Información completa de la consulta seleccionada
            </div>
          </div>
        </div>
      </div>

      <div class="lr-detail-card">
        <div class="lr-detail-card-body">

          <div class="row g-3">
            <div class="col-md-6">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Fecha</div>
                <div class="lr-detail-value">{{ consulta['fecha_consulta'] }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Origen</div>
                <div class="lr-detail-value">{{ consulta['origen'] }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Nombre consultado</div>
                <div class="lr-detail-value">{{ consulta['nombre_consultado'] }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Detectado o Consultado en</div>
                <div class="lr-detail-value">{{ consulta['fuente'] or 'No especificado' }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Resultado</div>
                <div class="lr-detail-value">
                  {% if consulta['resultado'] == 'Sin coincidencias' %}
                    <span class="badge bg-success fs-6">{{ consulta['resultado'] }}</span>
                  {% elif consulta['resultado'] == 'Coincidencia probable' %}
                    <span class="badge bg-warning text-dark fs-6">{{ consulta['resultado'] }}</span>
                  {% else %}
                    <span class="badge bg-danger fs-6">{{ consulta['resultado'] }}</span>
                  {% endif %}
                </div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Riesgo</div>
                <div class="lr-detail-value">{{ consulta['nivel_riesgo'] }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Score</div>
                <div class="lr-detail-value">{{ '%.2f'|format(consulta['score_coincidencia'] or 0) }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Tipo documento</div>
                <div class="lr-detail-value">{{ consulta['tipo_documento'] or '' }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Número documento</div>
                <div class="lr-detail-value">{{ consulta['numero_documento'] or '' }}</div>
              </div>
            </div>

            <div class="col-md-12">
              <div class="lr-detail-box">
                <div class="lr-detail-label">País</div>
                <div class="lr-detail-value">{{ consulta['pais'] or '' }}</div>
              </div>
            </div>
          </div>

          <div class="lr-actions mt-4">
            <a href="{{ url_for('listas_restrictivas_home') }}"
               class="btn lr-back-btn rounded-pill px-4 fw-bold">
              Volver
            </a>
          </div>

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

      .lr-shell{
        width:96%;
        max-width:1250px;
        margin:26px auto 24px auto;
      }

      .lr-header-card{
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

      .lr-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .lr-header-overlay{
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

      .lr-header-overlay::before{
        content:"🔎";
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

      .lr-header-text{
        max-width:1100px;
        width:100%;
      }

      .lr-header-text::before{
        content:"SGSI · Detalle Listas Restrictivas";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .lr-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .lr-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .lr-detail-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .lr-detail-card-body{
        padding:22px;
      }

      .lr-detail-box{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:14px 16px;
        height:100%;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .lr-detail-label{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
        margin-bottom:6px;
      }

      .lr-detail-value{
        color:#101827;
        font-size:.90rem;
        line-height:1.38;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .lr-actions{
        display:flex;
        gap:10px;
        justify-content:center;
        flex-wrap:wrap;
        margin-top:18px;
      }

      .lr-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .lr-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .lr-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .badge{
        border-radius:999px;
        font-size:.82rem;
        padding:.42rem .75rem;
        font-weight:900;
      }

      .btn.rounded-pill{
        border-radius:10px !important;
      }

      @media (max-width:992px){
        .lr-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .lr-header-card{
          min-height:88px;
        }

        .lr-title{
          font-size:1.20rem;
        }

        .lr-detail-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .lr-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .lr-header-overlay::before{
          margin:0;
        }

        .lr-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .lr-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(html, consulta=consulta))
    )

@app.route('/listas_restrictivas/eliminar/<int:consulta_id>', methods=['POST'])
@login_required
def listas_restrictivas_eliminar(consulta_id):
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and not verificar_permiso(user, "Listas Restrictivas"):
        flash("No tiene permiso para eliminar consultas de listas restrictivas.", "danger")
        return redirect(url_for('menu'))

    consulta = get_consulta_lista_by_id(consulta_id)
    if not consulta:
        flash("La consulta seleccionada no existe.", "danger")
        return redirect(url_for('listas_restrictivas_home'))

    nombre_consultado = consulta["nombre_consultado"]
    eliminado = delete_consulta_lista_by_id(consulta_id)

    if eliminado:
        registrar_log(
            session.get('username', 'Sistema'),
            f"Consulta de listas restrictivas eliminada. ID {consulta_id} - {nombre_consultado}"
        )
        flash("Consulta eliminada correctamente.", "success")
    else:
        flash("No fue posible eliminar la consulta.", "danger")

    return redirect(url_for('listas_restrictivas_home'))

DOCUMENTOS_POR_PAIS = {
    "Colombia": [
        "Cédula de ciudadanía",
        "Cédula de extranjería",
        "NIT",
        "NUIP",
        "Pasaporte",
        "PEP",
        "PPT",
        "Registro civil",
        "Tarjeta de identidad"
    ],
    "Canadá": [
        "Driver License",
        "Health Card",
        "Passport",
        "Permanent Resident Card",
        "SIN",
        "Tax Number"
    ],
    "Estados Unidos": [
        "Driver License",
        "Passport",
        "SSN",
        "State ID",
        "Tax ID"
    ],
    "México": [
        "CURP",
        "INE",
        "Pasaporte",
        "RFC"
    ],
    "Perú": [
        "Carné de extranjería",
        "DNI",
        "Pasaporte",
        "RUC"
    ],
    "Ecuador": [
        "Cédula",
        "Pasaporte",
        "RUC"
    ],
    "Chile": [
        "Cédula de identidad",
        "Pasaporte",
        "RUT"
    ],
    "Argentina": [
        "CUIL",
        "CUIT",
        "DNI",
        "Pasaporte"
    ],
    "Brasil": [
        "CPF",
        "CNPJ",
        "Passaporte",
        "RG"
    ],
    "España": [
        "DNI",
        "NIE",
        "Pasaporte"
    ],
    "Panamá": [
        "Cédula",
        "Pasaporte",
        "RUC"
    ],
    "Venezuela": [
        "Cédula de identidad",
        "Pasaporte",
        "RIF"
    ],
    "Otro": [
        "Documento nacional",
        "ID fiscal",
        "Pasaporte",
        "Otro"
    ]
}


@app.route('/listas_restrictivas/consulta', methods=['GET', 'POST'])
@login_required
def listas_restrictivas_consulta_manual():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede ejecutar consultas manuales de listas restrictivas.", "danger")
        return redirect(url_for('listas_restrictivas_home'))

    if user.role != 'admin' and not verificar_permiso(user, "Listas Restrictivas"):
        flash("No tiene permiso para consultar listas restrictivas.", "danger")
        return redirect(url_for('menu'))

    resultado = None
    nombre = ''
    tipo_documento = ''
    numero_documento = ''
    pais = 'Colombia'
    observaciones = ''

    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        tipo_documento = (request.form.get('tipo_documento') or '').strip()
        numero_documento = (request.form.get('numero_documento') or '').strip()
        pais = (request.form.get('pais') or 'Colombia').strip()
        observaciones = (request.form.get('observaciones') or '').strip()

        if not nombre:
            flash("Debe ingresar el nombre a consultar.", "danger")
            return redirect(url_for('listas_restrictivas_consulta_manual'))

        resultado = consultar_listas_restrictivas_global(
            nombre=nombre,
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            pais=pais
        )

        fuente_detectada = _resolver_fuente_detectada(resultado)

        registrar_consulta_lista_db(
            origen='manual',
            proveedor_id=None,
            nombre_consultado=nombre,
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            pais=pais,
            fuente=fuente_detectada,
            resultado=resultado["resultado"],
            nivel_riesgo=resultado["nivel_riesgo"],
            score=resultado["score"],
            detalle=resultado["detalle"],
            observaciones=observaciones,
            usuario=(user.username if user else "Sistema")
        )

        registrar_log(
            session.get('username', 'Sistema'),
            f"Consulta manual listas restrictivas: {nombre}. Detectado en: {fuente_detectada}. Resultado: {resultado['resultado']} ({resultado['nivel_riesgo']})"
        )

    html = """
    <div class="lr-shell">

      <div class="lr-header-card">
        <div class="lr-header-overlay">
          <div class="lr-header-text">
            <h3 class="lr-title m-0">Consulta Manual de Listas Restrictivas</h3>
            <div class="lr-subtitle">
              Validación consolidada contra listas externas y base local de listas restrictivas
            </div>
          </div>
        </div>
      </div>

      <div class="lr-form-card">
        <div class="lr-form-card-body">
          <form method="post" class="row g-3" id="formConsultaListas">

            <div class="col-md-6">
              <label class="lr-label">Nombre / Razón social</label>
              <input type="text"
                     name="nombre"
                     class="form-control lr-input"
                     value="{{ nombre }}"
                     required>
            </div>

            <div class="col-md-3">
              <label class="lr-label">País</label>
              <select name="pais" id="pais" class="form-select lr-input" onchange="actualizarTiposDocumento()">
                {% for p in documentos_por_pais.keys() %}
                  <option value="{{ p }}" {% if pais == p %}selected{% endif %}>{{ p }}</option>
                {% endfor %}
              </select>
            </div>

            <div class="col-md-3">
              <label class="lr-label">Tipo documento</label>
              <select name="tipo_documento" id="tipo_documento" class="form-select lr-input">
                <option value="">Seleccione...</option>
              </select>
            </div>

            <div class="col-md-4">
              <label class="lr-label">Número documento</label>
              <input type="text"
                     name="numero_documento"
                     class="form-control lr-input"
                     value="{{ numero_documento }}">
            </div>

            <div class="col-12">
              <div class="lr-actions">
                <button type="submit" class="btn btn-primary rounded-pill px-4 fw-bold" id="btnConsultarListas">
                  Consultar
                </button>

                <a href="{{ url_for('listas_restrictivas_home') }}"
                   class="btn lr-back-btn rounded-pill px-4 fw-bold">
                  Volver
                </a>
              </div>
            </div>

          </form>
        </div>
      </div>

      {% if resultado %}
      <div class="lr-result-card">
        <div class="lr-result-card-body">

          <div class="row g-3 mb-3">
            <div class="col-md-3">
              <div class="lr-kpi-card">
                <div class="lr-kpi-label">Detectado o Consultado en</div>
                <div class="lr-kpi-value-sm">{{ _resolver_fuente_detectada(resultado) }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="lr-kpi-card">
                <div class="lr-kpi-label">Resultado</div>
                <div class="mt-2">
                  {% if resultado['resultado'] == 'Sin coincidencias' %}
                    <span class="badge bg-success fs-6">{{ resultado['resultado'] }}</span>
                  {% elif resultado['resultado'] == 'Coincidencia probable' %}
                    <span class="badge bg-warning text-dark fs-6">{{ resultado['resultado'] }}</span>
                  {% else %}
                    <span class="badge bg-danger fs-6">{{ resultado['resultado'] }}</span>
                  {% endif %}
                </div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="lr-kpi-card">
                <div class="lr-kpi-label">Nivel de riesgo</div>
                <div class="lr-kpi-value-sm">{{ resultado['nivel_riesgo'] }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="lr-kpi-card">
                <div class="lr-kpi-label">Score</div>
                <div class="lr-kpi-value">{{ '%.2f'|format(resultado['score'] or 0) }}</div>
              </div>
            </div>
          </div>

          {% if resultado['detalle'] %}
          <div class="lr-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered align-middle lr-table mb-0">
                <thead>
                  <tr class="text-center">
                    <th>Fuente</th>
                    <th>Nombre</th>
                    <th>Documento</th>
                    <th>País</th>
                    <th>Categoría</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {% for d in resultado['detalle'] %}
                  <tr>
                    <td>{{ d['fuente'] }}</td>
                    <td>{{ d['nombre'] }}</td>
                    <td>{{ d['numero_documento'] or '' }}</td>
                    <td>{{ d['pais'] or '' }}</td>
                    <td>{{ d['categoria'] or '' }}</td>
                    <td class="text-center fw-bold">{{ '%.2f'|format(d['score'] or 0) }}</td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>
          {% else %}
          <div class="alert alert-info mb-0">
            No se encontraron coincidencias detalladas para mostrar.
          </div>
          {% endif %}

        </div>
      </div>
      {% endif %}

    </div>

    <!-- POPUP DE PROGRESO -->
    <div class="lr-loading-overlay" id="lrLoadingOverlay" aria-hidden="true">
      <div class="lr-loading-modal">
        <div class="lr-loading-icon-wrap">
          <div class="lr-loading-spinner"></div>
        </div>

        <div class="lr-loading-title">Consultando listas restrictivas</div>
        <div class="lr-loading-subtitle">
          Estamos validando coincidencias en listas externas y base local. No cierre esta ventana.
        </div>

        <div class="lr-progress">
          <div class="lr-progress-bar" id="lrProgressBar"></div>
        </div>

        <div class="lr-progress-text" id="lrProgressText">Iniciando consulta...</div>
      </div>
    </div>

    <script>
      const DOCUMENTOS_POR_PAIS = {{ documentos_por_pais | tojson }};
      const tipoDocumentoActual = {{ tipo_documento | tojson }};

      function actualizarTiposDocumento() {
        const paisSelect = document.getElementById("pais");
        const tipoDocumentoSelect = document.getElementById("tipo_documento");

        if (!paisSelect || !tipoDocumentoSelect) return;

        const pais = paisSelect.value;
        const opciones = DOCUMENTOS_POR_PAIS[pais] || DOCUMENTOS_POR_PAIS["Otro"] || [];

        tipoDocumentoSelect.innerHTML = '<option value="">Seleccione...</option>';

        opciones.forEach(function(opcion) {
          const opt = document.createElement("option");
          opt.value = opcion;
          opt.textContent = opcion;

          if (tipoDocumentoActual && tipoDocumentoActual === opcion) {
            opt.selected = true;
          }

          tipoDocumentoSelect.appendChild(opt);
        });
      }

      function mostrarPopupConsulta() {
        const overlay = document.getElementById("lrLoadingOverlay");
        const bar = document.getElementById("lrProgressBar");
        const text = document.getElementById("lrProgressText");

        if (!overlay || !bar || !text) return;

        overlay.classList.add("show");
        overlay.setAttribute("aria-hidden", "false");

        let progreso = 8;
        bar.style.width = progreso + "%";
        text.textContent = "Preparando parámetros de consulta...";

        const etapas = [
          { p: 20, t: "Validando información ingresada..." },
          { p: 38, t: "Consultando listas locales..." },
          { p: 56, t: "Consultando listas externas..." },
          { p: 74, t: "Analizando coincidencias encontradas..." },
          { p: 88, t: "Consolidando resultado final..." },
          { p: 96, t: "Finalizando consulta..." }
        ];

        let idx = 0;

        window.lrConsultaInterval = setInterval(() => {
          if (idx < etapas.length) {
            progreso = etapas[idx].p;
            bar.style.width = progreso + "%";
            text.textContent = etapas[idx].t;
            idx++;
          } else {
            clearInterval(window.lrConsultaInterval);
          }
        }, 700);
      }

      document.addEventListener("DOMContentLoaded", function() {
        actualizarTiposDocumento();

        const form = document.getElementById("formConsultaListas");
        const btn = document.getElementById("btnConsultarListas");

        if (form && btn) {
          form.addEventListener("submit", function(e) {
            const nombreInput = form.querySelector('input[name="nombre"]');
            if (!nombreInput || !nombreInput.value.trim()) {
              return;
            }

            btn.disabled = true;
            btn.innerHTML = 'Consultando...';
            mostrarPopupConsulta();
          });
        }
      });
    </script>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .lr-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }

      .lr-header-card{
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

      .lr-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .lr-header-overlay{
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

      .lr-header-overlay::before{
        content:"🔎";
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

      .lr-header-text{
        max-width:1200px;
        width:100%;
      }

      .lr-header-text::before{
        content:"SGSI · Consulta Listas Restrictivas";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .lr-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .lr-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .lr-form-card,
      .lr-result-card,
      .lr-kpi-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        margin-bottom:16px;
      }

      .lr-form-card-body,
      .lr-result-card-body{
        padding:22px;
      }

      .lr-label{
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

      .lr-input{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }

      .lr-input:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }

      .lr-actions{
        display:flex;
        gap:10px;
        justify-content:center;
        flex-wrap:wrap;
        margin-top:14px;
      }

      .lr-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .lr-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .lr-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .lr-kpi-card{
        padding:16px;
        text-align:center;
        height:100%;
      }

      .lr-kpi-label{
        color:#475569;
        font-weight:900;
        font-size:.72rem;
        text-transform:uppercase;
        letter-spacing:.35px;
        margin-bottom:8px;
      }

      .lr-kpi-value{
        font-size:1.85rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1.1;
      }

      .lr-kpi-value-sm{
        font-size:.92rem;
        font-weight:900;
        color:#0b1220;
        word-break:break-word;
      }

      .lr-table-wrap,
      .table-responsive{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .lr-table{
        margin-bottom:0;
      }

      .lr-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border:none !important;
        font-size:.78rem;
        padding:9px 8px;
      }

      .lr-table th,
      .lr-table td{
        vertical-align:middle;
        font-size:.82rem;
        padding:9px 8px;
        word-break:break-word;
      }

      .lr-table td{
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .lr-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .lr-table tbody tr:hover td{
        background:#eef6ff;
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .btn.rounded-pill{
        border-radius:10px !important;
      }

      .lr-loading-overlay{
        position:fixed;
        inset:0;
        background:rgba(15,23,42,.48);
        backdrop-filter:blur(6px);
        display:flex;
        align-items:center;
        justify-content:center;
        z-index:9999;
        opacity:0;
        visibility:hidden;
        transition:all .25s ease;
      }

      .lr-loading-overlay.show{
        opacity:1;
        visibility:visible;
      }

      .lr-loading-modal{
        width:min(92vw,520px);
        background:rgba(255,255,255,.96);
        border-radius:24px;
        box-shadow:0 24px 60px rgba(0,0,0,.28);
        padding:28px 24px 24px 24px;
        text-align:center;
        border:1px solid rgba(255,255,255,.7);
      }

      .lr-loading-icon-wrap{
        display:flex;
        justify-content:center;
        margin-bottom:14px;
      }

      .lr-loading-spinner{
        width:54px;
        height:54px;
        border-radius:50%;
        border:4px solid rgba(63,134,214,.18);
        border-top-color:#3f86d6;
        animation:lrSpin .9s linear infinite;
      }

      @keyframes lrSpin{
        to{ transform:rotate(360deg); }
      }

      .lr-loading-title{
        font-size:1.15rem;
        font-weight:950;
        color:#0f172a;
        margin-bottom:6px;
      }

      .lr-loading-subtitle{
        color:#475569;
        font-size:.94rem;
        margin-bottom:18px;
      }

      .lr-progress{
        width:100%;
        height:14px;
        background:#e5eefb;
        border-radius:999px;
        overflow:hidden;
        box-shadow:inset 0 1px 3px rgba(0,0,0,.08);
      }

      .lr-progress-bar{
        width:0%;
        height:100%;
        background:linear-gradient(90deg,#2f6fb6 0%,#3f86d6 55%,#5aa3ea 100%);
        border-radius:999px;
        transition:width .45s ease;
      }

      .lr-progress-text{
        margin-top:12px;
        color:#334155;
        font-size:.92rem;
        font-weight:700;
      }

      @media (max-width:992px){
        .lr-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .lr-header-card{
          min-height:88px;
        }

        .lr-title{
          font-size:1.20rem;
        }

        .lr-form-card-body,
        .lr-result-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .lr-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .lr-header-overlay::before{
          margin:0;
        }

        .lr-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .lr-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            html,
            resultado=resultado,
            nombre=nombre,
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            pais=pais,
            observaciones=observaciones,
            documentos_por_pais=DOCUMENTOS_POR_PAIS,
            _resolver_fuente_detectada=_resolver_fuente_detectada
        ))
    )

@app.route('/listas_restrictivas/base', methods=['GET', 'POST'])
@login_required
def listas_restrictivas_base():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin':
        flash("Solo el administrador puede gestionar la base de listas restrictivas.", "danger")
        return redirect(url_for('menu'))

    if request.method == 'POST':
        archivo_fuente = request.files.get('archivo_fuente')
        if archivo_fuente and archivo_fuente.filename:
            try:
                insertados, omitidos = cargar_fuente_lista_desde_archivo(
                    archivo_fuente,
                    fuente_default="Carga Archivo"
                )
                flash(f"Archivo procesado correctamente. Insertados: {insertados}. Omitidos: {omitidos}.", "success")
                return redirect(url_for('listas_restrictivas_base'))
            except Exception as e:
                flash(f"Error cargando archivo plano: {str(e)}", "danger")
                return redirect(url_for('listas_restrictivas_base'))
        fuente = (request.form.get('fuente') or '').strip() or 'Lista Local'
        nombre = (request.form.get('nombre') or '').strip()
        alias = (request.form.get('alias') or '').strip()
        tipo_documento = (request.form.get('tipo_documento') or '').strip()
        numero_documento = (request.form.get('numero_documento') or '').strip()
        pais = (request.form.get('pais') or '').strip()
        categoria = (request.form.get('categoria') or '').strip()
        observaciones = (request.form.get('observaciones') or '').strip()

        if not nombre:
            flash("El nombre del registro es obligatorio.", "danger")
            return redirect(url_for('listas_restrictivas_base'))

        conn = get_listas_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO listas_restrictivas_fuente (
                fuente, nombre, alias, tipo_documento, numero_documento, pais,
                categoria, observaciones, activo, fecha_actualizacion
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Sí', ?)
        """, (
            fuente, nombre, alias, tipo_documento, numero_documento, pais,
            categoria, observaciones, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()

        flash("Registro agregado a la base independiente de listas restrictivas.", "success")
        return redirect(url_for('listas_restrictivas_base'))

    conn = get_listas_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM listas_restrictivas_fuente
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()

    html = """
    <div class="lr-shell">

      <!-- HEADER -->
      <div class="lr-header-card">
        <div class="lr-header-overlay">
          <div class="lr-header-text">
            <h3 class="lr-title m-0">Base de Listas Restrictivas</h3>
            <div class="lr-subtitle">
              Administración de listas locales + carga masiva por archivo plano
            </div>
          </div>
        </div>
      </div>

      <!-- FORMULARIO GENERAL -->
      <form method="post" enctype="multipart/form-data" class="row g-3">

        <!-- CARGA ARCHIVO -->
        <div class="col-12">
          <div class="card shadow-sm border-0 rounded-4">
            <div class="card-body">
              <h5 class="fw-bold mb-2">📂 Carga por archivo plano</h5>

              <p class="text-muted mb-2">
                Puede cargar archivos <strong>.txt</strong> o <strong>.csv</strong>
              </p>

              <p class="text-muted small mb-2">
                TXT: <code>nombre|documento|pais|categoria</code>
              </p>

              <p class="text-muted small mb-3">
                CSV: columnas → nombre, alias, tipo_documento, numero_documento, pais, categoria, observaciones
              </p>

              <input type="file" name="archivo_fuente" class="form-control" accept=".txt,.csv">
            </div>
          </div>
        </div>

        <!-- FORMULARIO MANUAL -->
        <div class="col-12">
          <div class="card shadow-sm border-0 rounded-4">
            <div class="card-body">

              <h5 class="fw-bold mb-3">➕ Registro manual</h5>

              <div class="row g-3">
                <div class="col-md-3">
                  <label class="form-label fw-bold">Fuente</label>
                  <input name="fuente" class="form-control">
                </div>

                <div class="col-md-5">
                  <label class="form-label fw-bold">Nombre</label>
                  <input name="nombre" class="form-control" required>
                </div>

                <div class="col-md-4">
                  <label class="form-label fw-bold">Alias</label>
                  <input name="alias" class="form-control">
                </div>

                <div class="col-md-3">
                  <label class="form-label fw-bold">Tipo documento</label>
                  <input name="tipo_documento" class="form-control">
                </div>

                <div class="col-md-3">
                  <label class="form-label fw-bold">Número documento</label>
                  <input name="numero_documento" class="form-control">
                </div>

                <div class="col-md-3">
                  <label class="form-label fw-bold">País</label>
                  <input name="pais" class="form-control">
                </div>

                <div class="col-md-3">
                  <label class="form-label fw-bold">Categoría</label>
                  <input name="categoria" class="form-control">
                </div>

                <div class="col-12">
                  <label class="form-label fw-bold">Observaciones</label>
                  <textarea name="observaciones" class="form-control" rows="2"></textarea>
                </div>

                <div class="col-12 text-center">
                  <button type="submit" class="btn btn-danger rounded-pill px-4 fw-bold">
                    Guardar
                  </button>

                  <a href="{{ url_for('listas_restrictivas_home') }}"
                     class="btn btn-light rounded-pill px-4 fw-bold">
                    Volver
                  </a>
                </div>
              </div>

            </div>
          </div>
        </div>

      </form>

      <!-- TABLA -->
      <div class="card shadow-sm border-0 rounded-4 mt-3">
        <div class="card-body">

          <h5 class="fw-bold mb-3">📊 Base actual</h5>

          <div class="table-responsive lr-table-container">
            <table class="table table-bordered align-middle lr-table">
              <thead>
                <tr class="text-center">
                  <th>ID</th>
                  <th>Fuente</th>
                  <th>Nombre</th>
                  <th>Documento</th>
                  <th>País</th>
                  <th>Categoría</th>
                  <th>Estado</th>
                  <th>Actualización</th>
                </tr>
              </thead>

              <tbody>
                {% for r in rows %}
                <tr>
                  <td>{{ r['id'] }}</td>
                  <td>{{ r['fuente'] }}</td>
                  <td>{{ r['nombre'] }}</td>
                  <td>{{ r['numero_documento'] or '' }}</td>
                  <td>{{ r['pais'] or '' }}</td>
                  <td>{{ r['categoria'] or '' }}</td>
                  <td>
                    {% if r['activo'] == 'Sí' %}
                      <span class="badge bg-success">Activo</span>
                    {% else %}
                      <span class="badge bg-secondary">Inactivo</span>
                    {% endif %}
                  </td>
                  <td>{{ r['fecha_actualizacion'] or '' }}</td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>

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

      .lr-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }

      .lr-header-card{
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

      .lr-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .lr-header-overlay{
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

      .lr-header-overlay::before{
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
      }

      .lr-header-text,
      .lr-header-overlay > div{
        max-width:1200px;
        width:100%;
      }

      .lr-header-text::before,
      .lr-header-overlay > div::before{
        content:"SGSI · Base Local Listas Restrictivas";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .lr-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .lr-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .card-body{
        padding:18px;
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

      .lr-table-container{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .lr-table-container::-webkit-scrollbar{
        width:10px;
        height:10px;
      }

      .lr-table-container::-webkit-scrollbar-thumb{
        background:#2f7fd1;
        border-radius:10px;
      }

      .lr-table-container::-webkit-scrollbar-track{
        background:#edf4ff;
      }

      .lr-table{
        margin-bottom:0;
      }

      .lr-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border:none !important;
        font-size:.78rem;
        padding:9px 8px;
      }

      .lr-table th,
      .lr-table td{
        vertical-align:middle;
        font-size:.82rem;
        padding:9px 8px;
        word-break:break-word;
      }

      .lr-table td{
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .lr-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .lr-table tbody tr:hover{
        background:#eef6ff;
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .btn,
      .btn.rounded-pill{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      @media (max-width:992px){
        .lr-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .lr-header-card{
          min-height:88px;
        }

        .lr-title{
          font-size:1.20rem;
        }

        .card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .lr-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .lr-header-overlay::before{
          margin:0;
        }

        .lr-header-text::before,
        .lr-header-overlay > div::before{
          margin-left:auto;
          margin-right:auto;
        }

        .btn{
          width:100%;
        }
      }
    </style>
    """

    return render_template_string(BASE, content=Markup(render_template_string(html, rows=rows)))

@app.route('/listas_restrictivas/proveedor/<int:proveedor_id>/consultar', methods=['POST'])
@login_required
def listas_restrictivas_consultar_proveedor(proveedor_id):
    user = User.query.get(session.get('user_id'))
    proveedor = ProveedorEvaluacion.query.get_or_404(proveedor_id)

    if user.role == 'auditor':
        flash("El rol Auditor no puede ejecutar consultas de listas restrictivas.", "danger")
        return redirect(url_for('proveedores_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Listas Restrictivas"):
        flash("No tiene permiso para consultar listas restrictivas.", "danger")
        return redirect(url_for('menu'))

    nombre = (proveedor.nombre_proveedor or '').strip()
    pais = (proveedor.pais_origen or proveedor.pais_servicio or '').strip()
    tipo_documento = ''
    numero_documento = ''

    if not nombre:
        flash("El proveedor no tiene nombre para realizar la consulta.", "danger")
        return redirect(url_for('proveedores_edit', id=proveedor.id))

    resultado = consultar_listas_restrictivas_global(
        nombre=nombre,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        pais=pais
    )

    fuente_detectada = _resolver_fuente_detectada(resultado)

    registrar_consulta_lista_db(
        origen='proveedor',
        proveedor_id=proveedor.id,
        nombre_consultado=nombre,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        pais=pais,
        fuente=fuente_detectada,
        resultado=resultado["resultado"],
        nivel_riesgo=resultado["nivel_riesgo"],
        score=resultado["score"],
        detalle=resultado["detalle"],
        observaciones="Consulta ejecutada desde proveedor hacia módulo independiente de listas restrictivas",
        usuario=(user.username if user else "Sistema")
    )

    registrar_log(
        session.get('username', 'Sistema'),
        f"Consulta proveedor a listas restrictivas. Proveedor {proveedor.id} - {nombre}. Detectado en: {fuente_detectada}. Resultado: {resultado['resultado']} ({resultado['nivel_riesgo']})"
    )

    return redirect(url_for('listas_restrictivas_historial_proveedor', proveedor_id=proveedor.id))


@app.route('/listas_restrictivas/proveedor/<int:proveedor_id>/historial', methods=['GET'])
@login_required
def listas_restrictivas_historial_proveedor(proveedor_id):
    user = User.query.get(session.get('user_id'))
    proveedor = ProveedorEvaluacion.query.get_or_404(proveedor_id)

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Listas Restrictivas"):
        flash("No tiene permiso para ver el historial de listas restrictivas del proveedor.", "danger")
        return redirect(url_for('menu'))

    historial = get_historial_lista_proveedor(proveedor.id)
    estado = get_estado_lista_proveedor(proveedor.id)

    html = """
    <div class="provlist-shell">
      <div class="provlist-header-card">
        <div class="provlist-header-overlay">
          <div class="provlist-header-text">
            <h3 class="provlist-title m-0">🚨 Historial de Listas Restrictivas del Proveedor</h3>
            <div class="provlist-subtitle">
              Proveedor: <strong>{{ proveedor.nombre_proveedor }}</strong>
            </div>
          </div>
        </div>
      </div>

      <div class="provlist-actions">
        <a href="{{ url_for('proveedores_matriz') }}" class="btn rounded-pill px-4 fw-bold provlist-back-btn">
          ⬅ Volver a la Matriz
        </a>
        <a href="{{ url_for('proveedores_detalle', id=proveedor.id) }}" class="btn btn-primary rounded-pill px-4 fw-bold">
          Ver detalle del proveedor
        </a>
        <a href="{{ url_for('listas_restrictivas_home') }}" class="btn btn-danger rounded-pill px-4 fw-bold">
          Ir al módulo de listas restrictivas
        </a>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-md-4">
          <div class="card shadow-sm border-0 rounded-4 h-100">
            <div class="card-body text-center">
              <div class="text-muted">Último resultado</div>
              <div class="mt-2">
                {% if estado and estado['resultado'] == 'Sin coincidencias' %}
                  <span class="badge bg-success fs-6">{{ estado['resultado'] }}</span>
                {% elif estado and estado['resultado'] == 'Coincidencia probable' %}
                  <span class="badge bg-warning text-dark fs-6">{{ estado['resultado'] }}</span>
                {% elif estado and estado['resultado'] == 'Coincidencia exacta' %}
                  <span class="badge bg-danger fs-6">{{ estado['resultado'] }}</span>
                {% else %}
                  <span class="badge bg-secondary fs-6">Sin consultar</span>
                {% endif %}
              </div>
            </div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="card shadow-sm border-0 rounded-4 h-100">
            <div class="card-body text-center">
              <div class="text-muted">Nivel de riesgo</div>
              <div class="display-6 fw-bold text-danger">{{ estado['riesgo'] if estado else '—' }}</div>
            </div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="card shadow-sm border-0 rounded-4 h-100">
            <div class="card-body text-center">
              <div class="text-muted">Último score</div>
              <div class="display-6 fw-bold text-primary">
                {{ '%.2f'|format(estado['score'] or 0) if estado else '0.00' }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="provlist-card">
        <div class="provlist-card-body">
          {% if historial %}
          <div class="table-responsive">
            <table class="table table-bordered align-middle provlist-table">
              <thead>
                <tr class="text-center">
                  <th>Fecha</th>
                  <th>Nombre consultado</th>
                  <th>Fuente</th>
                  <th>Resultado</th>
                  <th>Riesgo</th>
                  <th>Score</th>
                  <th>Usuario</th>
                  <th>Detalle</th>
                </tr>
              </thead>
              <tbody>
                {% for h in historial %}
                <tr>
                  <td>{{ h['fecha_consulta'] }}</td>
                  <td>{{ h['nombre_consultado'] }}</td>
                  <td>{{ h['fuente'] }}</td>
                  <td>
                    {% if h['resultado'] == 'Sin coincidencias' %}
                      <span class="badge bg-success">{{ h['resultado'] }}</span>
                    {% elif h['resultado'] == 'Coincidencia probable' %}
                      <span class="badge bg-warning text-dark">{{ h['resultado'] }}</span>
                    {% else %}
                      <span class="badge bg-danger">{{ h['resultado'] }}</span>
                    {% endif %}
                  </td>
                  <td>{{ h['nivel_riesgo'] }}</td>
                  <td>{{ '%.2f'|format(h['score_coincidencia'] or 0) }}</td>
                  <td>{{ h['usuario'] or 'Sistema' }}</td>
                  <td style="min-width:320px;">
                    <pre style="white-space:pre-wrap;margin:0;">{{ h['detalle_json'] }}</pre>
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
          {% else %}
            <div class="alert alert-info mb-0">
              No hay consultas registradas para este proveedor.
            </div>
          {% endif %}
        </div>
      </div>
    </div>

    <style>
      .provlist-shell{width:96%;max-width:1700px;margin:10px auto 30px auto;}
      .provlist-header-card{
        background: linear-gradient(135deg, #b91c1c 0%, #b91c1c 55%, #ef4444 100%);
        min-height: 88px; border-radius: 18px; overflow: hidden;
        box-shadow: 0 12px 28px rgba(0,0,0,.22); margin-bottom: 14px;
      }
      .provlist-header-overlay{
        width:100%;height:100%;display:flex;align-items:center;justify-content:center;
        text-align:center;padding:10px 22px;background:rgba(0,0,0,.08);
      }
      .provlist-title{color:#fff;font-weight:900;font-size:1.35rem;}
      .provlist-subtitle{color:rgba(255,255,255,.96);font-size:.86rem;margin-top:4px;}
      .provlist-card{
        background: rgba(248,252,255,.96);
        border-radius: 18px; backdrop-filter: blur(6px);
        box-shadow: 0 10px 24px rgba(0,0,0,.16);
      }
      .provlist-card-body{padding:16px;}
      .provlist-actions{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-bottom:14px;}
      .provlist-back-btn{background:#fff;color:#000;border:2px solid #fff;}
      .provlist-table thead th{
        background:#fee2e2 !important;
        color:#7f1d1d;
        font-weight:800;
        text-align:center;
        vertical-align:middle;
      }
    </style>
    """

    inner = render_template_string(
        html,
        proveedor=proveedor,
        historial=historial,
        estado=estado
    )
    return render_template_string(BASE, content=Markup(inner))

# ==========================================================================================================================================
#                                                   Fin Módulo de Listas Restrictivas
# ==========================================================================================================================================

# ==========================================================================================================================================
#                  MODULO SCORECARD PROVEEDORES INDEPENDIENTE - DNS HEALTH / IP REPUTATION / ESCANEO KALI PROPIO
# ==========================================================================================================================================


try:
    import dns.resolver
except Exception:
    dns = None

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception:
    Fernet = None
    InvalidToken = Exception

try:
    from leakcheck_api import LeakCheckAPI_v2
except Exception:
    LeakCheckAPI_v2 = None


SCORECARD_DB_PATH = os.path.join(app.instance_path, "scorecard_proveedores.db")
SCORECARD_UPLOAD_DIR = os.path.join(app.instance_path, "scorecard_outputs")
os.makedirs(SCORECARD_UPLOAD_DIR, exist_ok=True)


# ============================================================
# DB INDEPENDIENTE SCORECARD
# ============================================================

def get_scorecard_db_connection():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(SCORECARD_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_scorecard_db():
    os.makedirs(app.instance_path, exist_ok=True)

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proveedor_id INTEGER,
            proveedor_nombre TEXT,
            dominio TEXT NOT NULL,
            ip_resuelta TEXT,
            score_dns REAL DEFAULT 0,
            score_ip REAL DEFAULT 0,
            score_kali REAL DEFAULT 0,
            score_incidentes REAL DEFAULT 100,
            score_darkweb REAL DEFAULT 100,
            score_total REAL DEFAULT 0,
            nivel_riesgo TEXT,
            estado TEXT DEFAULT 'pendiente',
            progress_pct INTEGER DEFAULT 0,
            current_stage TEXT,
            current_tool TEXT,
            modo_kali TEXT,
            herramientas_json TEXT,
            resumen_json TEXT,
            salida_consola TEXT,
            error_detalle TEXT,
            usuario TEXT,
            fecha_ejecucion TEXT NOT NULL,
            fecha_inicio TEXT,
            fecha_fin TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            categoria TEXT NOT NULL,
            herramienta TEXT,
            control TEXT,
            estado TEXT,
            riesgo TEXT,
            severidad TEXT,
            score REAL DEFAULT 0,
            evidencia TEXT,
            recomendacion TEXT,
            archivo_salida TEXT,
            detalle_json TEXT,
            fecha TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_outputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            herramienta TEXT NOT NULL,
            comando TEXT,
            archivo_salida TEXT,
            exit_code INTEGER,
            duracion_segundos REAL DEFAULT 0,
            fecha TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            proveedor_id INTEGER,
            proveedor_nombre TEXT,
            dominio TEXT,
            fuente TEXT,
            titulo TEXT,
            url TEXT,
            fecha_incidente TEXT,
            severidad TEXT,
            descripcion TEXT,
            detalle_json TEXT,
            fecha_registro TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_darkweb_exposures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            proveedor_id INTEGER,
            proveedor_nombre TEXT,
            dominio TEXT,
            fuente TEXT,
            tipo_exposicion TEXT,
            indicador TEXT,
            severidad TEXT,
            fecha TEXT,
            evidencia TEXT,
            recomendacion TEXT,
            url TEXT,
            credencial_confirmada INTEGER DEFAULT 0,
            detalle_json TEXT,
            fecha_registro TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_parametros (
            clave TEXT PRIMARY KEY,
            valor REAL NOT NULL,
            descripcion TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_risk_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            score_min REAL NOT NULL DEFAULT 0,
            color_bootstrap TEXT DEFAULT 'secondary',
            orden INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1,
            fecha_creacion TEXT NOT NULL
        )
    """)

    parametros_default = [
        ("peso_dns", 20, "Peso DNS Health"),
        ("peso_ip", 15, "Peso IP Reputation"),
        ("peso_kali", 35, "Peso Kali Linux"),
        ("peso_incidentes", 15, "Peso Incidentes/Brechas"),
        ("peso_darkweb", 15, "Peso Dark Web / Exposure Intelligence"),
        ("darkweb_score_sin_hallazgos", 100, "Sin hallazgos"),
        ("darkweb_score_1_2", 80, "1 a 2 hallazgos"),
        ("darkweb_score_3_5", 60, "3 a 5 hallazgos"),
        ("darkweb_score_mas_5", 40, "Más de 5 hallazgos"),
        ("darkweb_score_credenciales_confirmadas", 20, "Credenciales confirmadas"),
    ]

    for clave, valor, descripcion in parametros_default:
        cur.execute("""
            INSERT OR IGNORE INTO scorecard_parametros (clave, valor, descripcion)
            VALUES (?, ?, ?)
        """, (clave, valor, descripcion))

    cur.execute("SELECT COUNT(*) AS total FROM scorecard_risk_levels")
    total_risk_levels = cur.fetchone()["total"]

    if total_risk_levels == 0:
        niveles_default = [
            ("Bajo", 85, "success", 1),
            ("Medio", 70, "warning text-dark", 2),
            ("Alto", 50, "danger", 3),
            ("Crítico", 0, "dark", 4),
        ]

        for nombre, score_min, color_bootstrap, orden in niveles_default:
            cur.execute("""
                INSERT INTO scorecard_risk_levels
                (nombre, score_min, color_bootstrap, orden, activo, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                nombre,
                score_min,
                color_bootstrap,
                orden,
                1,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

    conn.commit()

    # Migración ligera si la base ya existía
    cur.execute("PRAGMA table_info(scorecard_runs)")
    cols = [r["name"] for r in cur.fetchall()]

    if "score_incidentes" not in cols:
        cur.execute("ALTER TABLE scorecard_runs ADD COLUMN score_incidentes REAL DEFAULT 100")
        conn.commit()

    if "score_darkweb" not in cols:
        cur.execute("ALTER TABLE scorecard_runs ADD COLUMN score_darkweb REAL DEFAULT 100")
        conn.commit()

    conn.close()


init_scorecard_db()

def init_scorecard_enterprise_api_db():
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proveedor TEXT NOT NULL UNIQUE,
            api_key_encrypted TEXT,
            activo INTEGER DEFAULT 0,
            notas TEXT,
            actualizado_por TEXT,
            fecha_actualizacion TEXT NOT NULL
        )
    """)

    proveedores_default = [
        ("leakcheck", "LeakCheck API"),
        ("hibp", "Have I Been Pwned API"),
        ("shodan", "Shodan API"),
    ]

    for proveedor, notas in proveedores_default:
        cur.execute("""
            INSERT OR IGNORE INTO scorecard_api_keys
            (proveedor, api_key_encrypted, activo, notas, actualizado_por, fecha_actualizacion)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            proveedor,
            "",
            0,
            notas,
            "Sistema",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    conn.commit()
    conn.close()


# Ejecutar una vez al cargar el módulo.
init_scorecard_enterprise_api_db()


# ============================================================
# PERMISOS
# ============================================================

def scorecard_user_permiso():
    user = User.query.get(session.get("user_id"))

    if not user:
        return None, False, False

    read_only = user.role == "auditor"

    if user.role != "admin" and user.role != "auditor" and not verificar_permiso(user, "Registro de Proveedores"):
        return user, False, read_only

    return user, True, read_only


# ============================================================
# UTILIDADES BASE
# ============================================================

def limpiar_dominio_scorecard(valor):
    valor = (valor or "").strip().lower()
    valor = re.sub(r"^https?://", "", valor)
    valor = valor.split("/")[0]
    valor = valor.split(":")[0]
    valor = valor.strip()
    return valor


def scorecard_get_crypto_master_key():
    """
    Genera una llave Fernet derivada del SECRET_KEY de Flask.
    No usa variables de entorno.

    Recomendación:
    - Asegúrate de tener app.secret_key estable en producción.
    - Si cambias app.secret_key, las API keys cifradas antes no se podrán descifrar.
    """
    if Fernet is None:
        return None

    import base64
    import hashlib

    raw_secret = str(getattr(app, "secret_key", "") or "GRAC_SCORECARD_LOCAL_SECRET").encode("utf-8")
    salt = b"GRAC_SCORECARD_API_KEYS_V1"
    digest = hashlib.sha256(raw_secret + salt).digest()
    return base64.urlsafe_b64encode(digest)


def scorecard_encrypt_api_key(api_key):
    api_key = (api_key or "").strip()

    if not api_key:
        return ""

    key = scorecard_get_crypto_master_key()

    if not key:
        # Fallback controlado si cryptography no está instalada.
        # No recomendado, pero evita romper el sistema.
        return "plain:" + api_key

    f = Fernet(key)
    return f.encrypt(api_key.encode("utf-8")).decode("utf-8")


def scorecard_decrypt_api_key(api_key_encrypted):
    api_key_encrypted = (api_key_encrypted or "").strip()

    if not api_key_encrypted:
        return ""

    if api_key_encrypted.startswith("plain:"):
        return api_key_encrypted.replace("plain:", "", 1)

    key = scorecard_get_crypto_master_key()

    if not key:
        return ""

    try:
        f = Fernet(key)
        return f.decrypt(api_key_encrypted.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""
    except Exception:
        return ""


def scorecard_mask_api_key(api_key):
    api_key = (api_key or "").strip()

    if not api_key:
        return "No configurada"

    if len(api_key) <= 8:
        return api_key[:2] + "***"

    return api_key[:4] + "****" + api_key[-4:]


def scorecard_get_enterprise_api_key(proveedor):
    proveedor = (proveedor or "").strip().lower()

    try:
        conn = get_scorecard_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT api_key_encrypted, activo
            FROM scorecard_api_keys
            WHERE proveedor = ?
            LIMIT 1
        """, (proveedor,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return ""

        if int(row["activo"] or 0) != 1:
            return ""

        return scorecard_decrypt_api_key(row["api_key_encrypted"])

    except Exception:
        return ""


def scorecard_api_status():
    proveedores = ["leakcheck", "hibp", "shodan"]
    estado = {}

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    for proveedor in proveedores:
        cur.execute("""
            SELECT *
            FROM scorecard_api_keys
            WHERE proveedor = ?
            LIMIT 1
        """, (proveedor,))
        row = cur.fetchone()

        if row:
            api_key = scorecard_decrypt_api_key(row["api_key_encrypted"])
            estado[proveedor] = {
                "activo": int(row["activo"] or 0) == 1,
                "configurada": bool(api_key),
                "mask": scorecard_mask_api_key(api_key),
                "fecha": row["fecha_actualizacion"],
                "notas": row["notas"] or ""
            }
        else:
            estado[proveedor] = {
                "activo": False,
                "configurada": False,
                "mask": "No configurada",
                "fecha": "",
                "notas": ""
            }

    conn.close()
    return estado


def scorecard_guardar_api_key(proveedor, api_key, activo, usuario):
    proveedor = (proveedor or "").strip().lower()
    api_key = (api_key or "").strip()

    encrypted = scorecard_encrypt_api_key(api_key) if api_key else ""

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_api_keys
        (proveedor, api_key_encrypted, activo, notas, actualizado_por, fecha_actualizacion)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(proveedor) DO UPDATE SET
            api_key_encrypted = excluded.api_key_encrypted,
            activo = excluded.activo,
            actualizado_por = excluded.actualizado_por,
            fecha_actualizacion = excluded.fecha_actualizacion
    """, (
        proveedor,
        encrypted,
        1 if activo and api_key else 0,
        proveedor,
        usuario,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def scorecard_mask_email(email):
    email = (email or "").strip()

    if not email:
        return ""

    if "@" not in email:
        return email[:2] + "***" if len(email) > 2 else "***"

    user, domain = email.split("@", 1)
    if len(user) <= 2:
        user_mask = user[:1] + "***"
    else:
        user_mask = user[:2] + "***"

    return f"{user_mask}@{domain}"


def scorecard_mask_indicator(value):
    value = str(value or "").strip()

    if not value:
        return ""

    if "@" in value:
        return scorecard_mask_email(value)

    if len(value) <= 8:
        return value[:2] + "***"

    return value[:4] + "***" + value[-3:]


def scorecard_api_error_item(fuente, detalle):
    """
    Retorna item informativo.
    Este tipo NO debe bajar score.
    """
    return {
        "fuente": fuente,
        "tipo_exposicion": "API no disponible / error controlado",
        "indicador": fuente,
        "severidad": "Bajo",
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "evidencia": str(detalle)[:700],
        "recomendacion": "Validar API key, cuota, plan activo, conectividad y permisos del servicio.",
        "url": "",
        "credencial_confirmada": False,
        "detalle": {"error": str(detalle), "no_penaliza_score": True}
    }



def target_url_scorecard(dominio):
    dominio = limpiar_dominio_scorecard(dominio)
    return "https://" + dominio


def resolver_ip_scorecard(dominio):
    try:
        return socket.gethostbyname(dominio)
    except Exception:
        return ""


def scorecard_risk_levels_activos():
    try:
        conn = get_scorecard_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT *
            FROM scorecard_risk_levels
            WHERE activo = 1
            ORDER BY score_min DESC, orden ASC, id ASC
        """)
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def nivel_riesgo_scorecard(score):
    score = float(score or 0)
    niveles = scorecard_risk_levels_activos()

    if not niveles:
        if score >= 85:
            return "Bajo"
        if score >= 70:
            return "Medio"
        if score >= 50:
            return "Alto"
        return "Crítico"

    for nivel in niveles:
        if score >= float(nivel["score_min"] or 0):
            return nivel["nombre"]

    return niveles[-1]["nombre"]


def scorecard_badge_color(nivel_nombre):
    try:
        conn = get_scorecard_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT color_bootstrap
            FROM scorecard_risk_levels
            WHERE nombre = ?
            LIMIT 1
        """, (nivel_nombre,))
        row = cur.fetchone()
        conn.close()
        return row["color_bootstrap"] if row else "secondary"
    except Exception:
        return "secondary"


def scorecard_run_dir(run_id, dominio):
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", dominio or "target")
    path = os.path.join(SCORECARD_UPLOAD_DIR, f"scorecard_{run_id}_{safe}")
    os.makedirs(path, exist_ok=True)
    return path


def scorecard_output_file(run_dir, herramienta, ext="txt"):
    herramienta = re.sub(r"[^a-zA-Z0-9_.-]+", "_", herramienta or "output")
    return os.path.join(run_dir, f"{herramienta}.{ext}")


def scorecard_set_progress(run_id, pct=None, stage=None, tool=None, estado=None, error=None):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    updates = []
    params = []

    if pct is not None:
        updates.append("progress_pct = ?")
        params.append(max(0, min(100, int(pct))))

    if stage is not None:
        updates.append("current_stage = ?")
        params.append(stage)

    if tool is not None:
        updates.append("current_tool = ?")
        params.append(tool)

    if estado is not None:
        updates.append("estado = ?")
        params.append(estado)

    if error is not None:
        updates.append("error_detalle = ?")
        params.append(error)

    if updates:
        params.append(run_id)
        cur.execute(f"UPDATE scorecard_runs SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    conn.close()


def guardar_scorecard_finding(run_id, item):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_findings
        (run_id, categoria, herramienta, control, estado, riesgo, severidad, score,
         evidencia, recomendacion, archivo_salida, detalle_json, fecha)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        item.get("categoria"),
        item.get("herramienta"),
        item.get("control"),
        item.get("estado"),
        item.get("riesgo"),
        item.get("severidad"),
        float(item.get("score") or 0),
        item.get("evidencia"),
        item.get("recomendacion"),
        item.get("archivo_salida"),
        json.dumps(item, ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def guardar_scorecard_output(run_id, herramienta, comando, archivo_salida, exit_code, duracion):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_outputs
        (run_id, herramienta, comando, archivo_salida, exit_code, duracion_segundos, fecha)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        herramienta,
        comando,
        archivo_salida,
        int(exit_code or 0),
        float(duracion or 0),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


# ============================================================
# DNS HEALTH
# ============================================================

def dns_txt_scorecard(nombre):
    if dns is None:
        return []

    try:
        answers = dns.resolver.resolve(nombre, "TXT", lifetime=5)
        return [str(x.to_text()).strip('"') for x in answers]
    except Exception:
        return []


def dns_any_scorecard(nombre, tipo):
    if dns is None:
        return []

    try:
        answers = dns.resolver.resolve(nombre, tipo, lifetime=5)
        return [str(x.to_text()) for x in answers]
    except Exception:
        return []


def evaluar_dns_health_scorecard(dominio):
    """
    Evalúa DNS Health corrigiendo falsos positivos por subdominios.

    - A/CNAME se evalúa sobre el dominio ingresado.
    - MX, NS, SPF y DMARC se evalúan sobre dominio base.
    """

    score = 100
    findings = []

    dominio_original = limpiar_dominio_scorecard(dominio)
    dominio_base = obtener_dominio_base(dominio_original)

    registros_a = dns_any_scorecard(dominio_original, "A")

    registros_cname = []
    if not registros_a:
        registros_cname = dns_any_scorecard(dominio_original, "CNAME")

    registros_mx = dns_any_scorecard(dominio_base, "MX")
    registros_ns = dns_any_scorecard(dominio_base, "NS")

    txt_root = dns_txt_scorecard(dominio_base)
    txt_dmarc = dns_txt_scorecard(f"_dmarc.{dominio_base}")

    spf_ok = any("v=spf1" in x.lower() for x in txt_root)
    dmarc_ok = any("v=dmarc1" in x.lower() for x in txt_dmarc)

    dmarc_policy = ""
    for item in txt_dmarc:
        low = item.lower()
        if "p=reject" in low:
            dmarc_policy = "reject"
        elif "p=quarantine" in low:
            dmarc_policy = "quarantine"
        elif "p=none" in low:
            dmarc_policy = "none"

    def add(control, estado, riesgo, puntaje, evidencia, recomendacion):
        findings.append({
            "categoria": "DNS Health",
            "herramienta": "DNS Resolver",
            "control": control,
            "estado": estado,
            "riesgo": riesgo,
            "severidad": riesgo,
            "score": puntaje,
            "evidencia": evidencia,
            "recomendacion": recomendacion
        })

    if registros_a:
        add(
            "Registro A",
            "OK",
            "Bajo",
            100,
            f"{dominio_original}: " + ", ".join(registros_a[:8]),
            "Mantener monitoreo de resolución pública."
        )
    elif registros_cname:
        add(
            "Registro A/CNAME",
            "OK por CNAME",
            "Bajo",
            100,
            f"{dominio_original} apunta por CNAME a: " + ", ".join(registros_cname[:8]),
            "Mantener monitoreo de resolución pública y destino CNAME autorizado."
        )
    else:
        score -= 20
        add(
            "Registro A",
            "No detectado",
            "Alto",
            0,
            f"No se encontraron registros A ni CNAME para {dominio_original}.",
            "Validar publicación DNS del dominio o subdominio evaluado."
        )

    if registros_mx:
        add(
            "MX",
            "OK",
            "Bajo",
            100,
            f"{dominio_base}: " + ", ".join(registros_mx[:8]),
            "Mantener proveedores MX autorizados."
        )
    else:
        # No todos los dominios web reciben correo. Por eso queda bajo y solo descuenta 5.
        score -= 5
        add(
            "MX",
            "No detectado en dominio base",
            "Bajo",
            70,
            f"No se encontraron registros MX para {dominio_base}. Esto puede ser aceptable si el dominio no recibe correo.",
            "Confirmar si el proveedor usa este dominio para correo. Si lo usa, configurar MX."
        )

    if registros_ns:
        add(
            "NS",
            "OK",
            "Bajo",
            100,
            f"{dominio_base}: " + ", ".join(registros_ns[:8]),
            "Mantener gobierno sobre la administración DNS."
        )
    else:
        score -= 10
        add(
            "NS",
            "No detectado en dominio base",
            "Medio",
            0,
            f"No se encontraron registros NS para {dominio_base}.",
            "Validar delegación DNS del dominio base."
        )

    if spf_ok:
        add(
            "SPF",
            "OK",
            "Bajo",
            100,
            f"Se detectó registro SPF en {dominio_base}.",
            "Evitar configuraciones demasiado permisivas como +all."
        )
    else:
        score -= 20
        add(
            "SPF",
            "No configurado en dominio base",
            "Alto",
            0,
            f"No se encontró TXT con v=spf1 en {dominio_base}.",
            "Configurar SPF para mitigar spoofing si el dominio envía correo."
        )

    if not dmarc_ok:
        score -= 30
        add(
            "DMARC",
            "No configurado en dominio base",
            "Alto",
            0,
            f"No se encontró _dmarc.{dominio_base}.",
            "Configurar DMARC con política gradual."
        )
    elif dmarc_policy == "none":
        score -= 10
        add(
            "DMARC",
            "Configurado p=none",
            "Medio",
            70,
            f"DMARC existe en _dmarc.{dominio_base}, pero está en modo monitoreo.",
            "Avanzar gradualmente a quarantine o reject."
        )
    else:
        add(
            "DMARC",
            "OK",
            "Bajo",
            100,
            f"Política DMARC en _dmarc.{dominio_base}: {dmarc_policy or 'definida'}.",
            "Mantener monitoreo DMARC."
        )

    return max(0, min(100, score)), findings


# ============================================================
# IP REPUTATION
# ============================================================

def reverse_ip_scorecard(ip):
    try:
        parts = ip.split(".")
        if len(parts) != 4:
            return ""
        return ".".join(reversed(parts))
    except Exception:
        return ""


def evaluar_ip_reputation_scorecard(ip):
    score = 100
    findings = []

    if not ip:
        return 0, [{
            "categoria": "IP Reputation",
            "herramienta": "DNSBL",
            "control": "Resolución IP",
            "estado": "No resuelta",
            "riesgo": "Alto",
            "severidad": "Alto",
            "score": 0,
            "evidencia": "No se pudo resolver IP.",
            "recomendacion": "Validar dominio objetivo."
        }]

    zonas = [
        "zen.spamhaus.org",
        "bl.spamcop.net",
        "dnsbl.sorbs.net",
        "b.barracudacentral.org"
    ]

    reversed_ip = reverse_ip_scorecard(ip)
    listada = []

    if dns is not None and reversed_ip:
        for zona in zonas:
            consulta = f"{reversed_ip}.{zona}"
            try:
                dns.resolver.resolve(consulta, "A", lifetime=4)
                listada.append(zona)
            except Exception:
                pass

    if listada:
        score -= min(90, len(listada) * 25)
        findings.append({
            "categoria": "IP Reputation",
            "herramienta": "DNSBL",
            "control": "Blacklist",
            "estado": "Listada",
            "riesgo": "Alto",
            "severidad": "Alto",
            "score": max(0, score),
            "evidencia": "IP listada en: " + ", ".join(listada),
            "recomendacion": "Solicitar remediación al proveedor y revisar reputación del servicio."
        })
    else:
        findings.append({
            "categoria": "IP Reputation",
            "herramienta": "DNSBL",
            "control": "Blacklist",
            "estado": "OK",
            "riesgo": "Bajo",
            "severidad": "Bajo",
            "score": 100,
            "evidencia": "No se detectó la IP en las listas consultadas.",
            "recomendacion": "Mantener monitoreo de reputación."
        })

    return max(0, min(100, score)), findings


# ============================================================
# KALI SCAN INDEPENDIENTE
# ============================================================

def scorecard_cfg_get(cfg, *names, default=None):
    for name in names:
        try:
            value = getattr(cfg, name)
            if value not in [None, ""]:
                return value
        except Exception:
            pass
    return default


def scorecard_kali_modo(cfg):
    modo = str(scorecard_cfg_get(cfg, "modo", "scanner_mode", default="local") or "local").lower()
    if "rem" in modo or "ssh" in modo or "kali" in modo:
        return "remoto"
    return "local"


def scorecard_tool_path(cfg, tool):
    mapping = {
        "nmap": ["nmap_path", "path_nmap", "ruta_nmap"],
        "whatweb": ["whatweb_path", "path_whatweb", "ruta_whatweb"],
        "nikto": ["nikto_path", "path_nikto", "ruta_nikto"],
        "nuclei": ["nuclei_path", "path_nuclei", "ruta_nuclei"],
        "testssl": ["testssl_path", "path_testssl", "ruta_testssl", "testssl_sh_path"],
    }

    for attr in mapping.get(tool, []):
        value = scorecard_cfg_get(cfg, attr)
        if value:
            return value

    return tool if tool != "testssl" else "testssl"


def scorecard_run_command(cfg, cmd_list, timeout=180):
    """
    Ejecuta comando local o remoto usando la configuración de Kali existente.
    No usa tablas ni pantallas de vulnerabilidades.
    """
    modo = scorecard_kali_modo(cfg)

    if modo == "remoto":
        ssh_host = scorecard_cfg_get(cfg, "ssh_host", "host", "kali_host", "remote_host")
        ssh_user = scorecard_cfg_get(cfg, "ssh_user", "usuario", "kali_user", "remote_user")
        ssh_port = scorecard_cfg_get(cfg, "ssh_port", "port", "kali_port", default="22")
        ssh_key = scorecard_cfg_get(cfg, "ssh_key", "ssh_key_path", "kali_key")

        if not ssh_host:
            raise RuntimeError("La configuración Kali remota no tiene host SSH definido.")

        destino = f"{ssh_user}@{ssh_host}" if ssh_user else ssh_host
        remote_cmd = " ".join(shlex.quote(str(x)) for x in cmd_list)

        ssh_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-p", str(ssh_port)]

        if ssh_key:
            ssh_cmd += ["-i", str(ssh_key)]

        ssh_cmd += [destino, remote_cmd]

        start = time.time()
        proc = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        duracion = round(time.time() - start, 2)
        salida = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")

        return {
            "cmd": " ".join(ssh_cmd),
            "exit_code": proc.returncode,
            "output": salida,
            "duracion": duracion
        }

    start = time.time()
    proc = subprocess.run(
        [str(x) for x in cmd_list],
        capture_output=True,
        text=True,
        timeout=timeout
    )

    duracion = round(time.time() - start, 2)
    salida = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")

    return {
        "cmd": " ".join(str(x) for x in cmd_list),
        "exit_code": proc.returncode,
        "output": salida,
        "duracion": duracion
    }


def scorecard_detectar_severidades(texto):
    texto_low = (texto or "").lower()

    crit = len(re.findall(r"\bcritical\b|\bcrítico\b|\bcritico\b", texto_low))
    high = len(re.findall(r"\bhigh\b|\balto\b", texto_low))
    med = len(re.findall(r"\bmedium\b|\bmedio\b|\bmoderado\b", texto_low))
    low = len(re.findall(r"\blow\b|\bbajo\b", texto_low))

    return {
        "criticas": crit,
        "altas": high,
        "medias": med,
        "bajas": low
    }


def scorecard_score_kali_desde_resumen(resumen):
    criticas = int(resumen.get("criticas") or 0)
    altas = int(resumen.get("altas") or 0)
    medias = int(resumen.get("medias") or 0)
    bajas = int(resumen.get("bajas") or 0)
    errores = int(resumen.get("errores") or 0)

    descuento = (criticas * 25) + (altas * 15) + (medias * 7) + (bajas * 3) + (errores * 2)
    return max(0, 100 - min(100, descuento))


# ============================================================
# OWASP ZAP NORMAL (BASELINE)
# ============================================================

def scorecard_severity_from_text(texto):
    texto = (texto or "").lower()

    if any(x in texto for x in ["critical", "crítico", "critico"]):
        return "Crítico"

    if any(x in texto for x in ["high", "alto"]):
        return "Alto"

    if any(x in texto for x in ["medium", "medio"]):
        return "Medio"

    return "Bajo"


def ejecutar_scorecard_zap_baseline(run_id, dominio):
    run_dir = scorecard_run_dir(run_id, dominio)

    out_html = os.path.join(run_dir, "zap_scan.html")
    out_txt = os.path.join(run_dir, "zap_scan.txt")

    url = target_url_scorecard(dominio)

    docker_image = "ghcr.io/zaproxy/zaproxy:stable"

    cmd = [
        "bash",
        "-lc",
        (
            f"rm -f {shlex.quote(out_html)} {shlex.quote(out_txt)}; "

            f"echo '[OWASP_ZAP] BASELINE iniciado' > {shlex.quote(out_txt)}; "

            f"docker run --rm "
            f"-v {shlex.quote(run_dir)}:/zap/wrk/:rw "
            f"{docker_image} "
            f"zap-baseline.py "
            f"-t {shlex.quote(url)} "
            f"-r zap_scan.html "
            f"-I "
            f">> {shlex.quote(out_txt)} 2>&1; "

            f"ls -lh {shlex.quote(out_html)} {shlex.quote(out_txt)} 2>&1"
        )
    ]

    start = time.time()

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=900
    )

    duracion = round(time.time() - start, 2)

    salida = (proc.stdout or "") + "\n" + (proc.stderr or "")

    guardar_scorecard_output(
        run_id,
        "OWASP ZAP",
        " ".join(cmd),
        out_html,
        proc.returncode,
        duracion
    )

    return {
        "exit_code": proc.returncode,
        "output": salida,
        "html": out_html,
        "txt": out_txt
    }


def parse_scorecard_zap_findings(run_id, dominio):
    findings = []

    run_dir = scorecard_run_dir(run_id, dominio)

    html_file = os.path.join(run_dir, "zap_scan.html")
    txt_file = os.path.join(run_dir, "zap_scan.txt")

    if os.path.exists(html_file):

        try:
            with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            patrones = re.findall(
                r'<h3[^>]*>(.*?)</h3>(.*?)(?=<h3|</body>|</html>)',
                content,
                re.I | re.S
            )

            for titulo_raw, bloque in patrones:

                titulo = html.unescape(
                    re.sub(r'<.*?>', '', titulo_raw)
                ).strip()

                if not titulo:
                    continue

                risk = "Medium"

                risk_match = re.search(
                    r'Risk.*?<td[^>]*>(.*?)</td>',
                    bloque,
                    re.I | re.S
                )

                if risk_match:
                    risk = html.unescape(
                        re.sub(r'<.*?>', '', risk_match.group(1))
                    ).strip()

                desc = ""

                desc_match = re.search(
                    r'Description.*?<td[^>]*>(.*?)</td>',
                    bloque,
                    re.I | re.S
                )

                if desc_match:
                    desc = html.unescape(
                        re.sub(r'<.*?>', ' ', desc_match.group(1))
                    ).strip()

                severidad = scorecard_severity_from_text(
                    risk + " " + titulo + " " + desc
                )

                findings.append({
                    "categoria": "OWASP ZAP",
                    "herramienta": "OWASP ZAP",
                    "control": titulo[:250],
                    "estado": "Hallazgo detectado",
                    "riesgo": severidad,
                    "severidad": severidad,
                    "score": (
                        20 if severidad == "Crítico"
                        else 45 if severidad == "Alto"
                        else 70 if severidad == "Medio"
                        else 90
                    ),
                    "evidencia": (
                        f"OWASP ZAP identificó: {titulo}\n\n"
                        f"{desc[:2500]}"
                    ),
                    "recomendacion": (
                        "Validar el hallazgo reportado por OWASP ZAP y aplicar remediación."
                    ),
                    "archivo_salida": html_file,
                    "detalle": {
                        "titulo": titulo,
                        "risk": risk
                    }
                })

        except Exception as e:

            findings.append({
                "categoria": "OWASP ZAP",
                "herramienta": "OWASP ZAP",
                "control": "Error parseando ZAP",
                "estado": "Error",
                "riesgo": "Medio",
                "severidad": "Medio",
                "score": 50,
                "evidencia": str(e),
                "recomendacion": "Validar parser OWASP ZAP.",
                "archivo_salida": html_file,
                "detalle": {}
            })

    if not findings and os.path.exists(txt_file):

        try:
            with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = [x.strip() for x in f.readlines() if x.strip()]

            for ln in lines:

                low = ln.lower()

                if any(x in low for x in [
                    "fail-new:",
                    "warn-new:",
                    "x-frame-options",
                    "content-security-policy",
                    "cookie",
                    "missing",
                    "server leaks",
                    "strict-transport-security"
                ]):

                    severidad = scorecard_severity_from_text(ln)

                    findings.append({
                        "categoria": "OWASP ZAP",
                        "herramienta": "OWASP ZAP",
                        "control": ln[:250],
                        "estado": "Hallazgo detectado",
                        "riesgo": severidad,
                        "severidad": severidad,
                        "score": (
                            20 if severidad == "Crítico"
                            else 45 if severidad == "Alto"
                            else 70 if severidad == "Medio"
                            else 90
                        ),
                        "evidencia": ln[:2500],
                        "recomendacion": "Validar hallazgo reportado por OWASP ZAP.",
                        "archivo_salida": txt_file,
                        "detalle": {}
                    })

        except Exception:
            pass

    return findings


def ejecutar_scorecard_kali_independiente(run_id, dominio):
    cfg = _scan_cfg()
    run_dir = scorecard_run_dir(run_id, dominio)
    url = target_url_scorecard(dominio)
    ip = resolver_ip_scorecard(dominio)

    modo = scorecard_kali_modo(cfg)

    herramientas = {
        "nmap": scorecard_tool_path(cfg, "nmap"),
        "whatweb": scorecard_tool_path(cfg, "whatweb"),
        "nikto": scorecard_tool_path(cfg, "nikto"),
        "nuclei": scorecard_tool_path(cfg, "nuclei"),
        "testssl": scorecard_tool_path(cfg, "testssl"),
        "zap": "Docker OWASP ZAP Baseline"
    }

    conn = get_scorecard_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE scorecard_runs
        SET modo_kali = ?,
            herramientas_json = ?,
            estado = ?,
            fecha_inicio = ?,
            progress_pct = ?,
            current_stage = ?,
            current_tool = ?
        WHERE id = ?
    """, (
        modo,
        json.dumps(herramientas, ensure_ascii=False),
        "ejecutando",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        45,
        "Inicializando escaneo Kali independiente",
        "dispatcher",
        run_id
    ))
    conn.commit()
    conn.close()

    logs = []
    resumen_global = {
        "criticas": 0,
        "altas": 0,
        "medias": 0,
        "bajas": 0,
        "errores": 0,
        "herramientas": {}
    }

    comandos = []

    # ============================================================
    # OWASP ZAP NORMAL / BASELINE
    # ============================================================
    try:
        scorecard_set_progress(
            run_id,
            pct=50,
            stage="Ejecutando OWASP ZAP normal",
            tool="OWASP ZAP"
        )

        zap_result = ejecutar_scorecard_zap_baseline(run_id, dominio)
        zap_findings = parse_scorecard_zap_findings(run_id, dominio)

        resumen_zap = {
            "exit_code": zap_result.get("exit_code"),
            "archivo_html": zap_result.get("html"),
            "archivo_txt": zap_result.get("txt"),
            "hallazgos": len(zap_findings),
            "severidades": {
                "criticas": 0,
                "altas": 0,
                "medias": 0,
                "bajas": 0
            }
        }

        for item in zap_findings:
            guardar_scorecard_finding(run_id, item)

            sev = item.get("severidad")

            if sev == "Crítico":
                resumen_global["criticas"] += 1
                resumen_zap["severidades"]["criticas"] += 1
            elif sev == "Alto":
                resumen_global["altas"] += 1
                resumen_zap["severidades"]["altas"] += 1
            elif sev == "Medio":
                resumen_global["medias"] += 1
                resumen_zap["severidades"]["medias"] += 1
            else:
                resumen_global["bajas"] += 1
                resumen_zap["severidades"]["bajas"] += 1

        resumen_global["herramientas"]["OWASP ZAP"] = resumen_zap

        logs.append(
            "\n\n===== OWASP ZAP NORMAL =====\n" +
            (zap_result.get("output") or "")[:5000]
        )

    except Exception as e:
        resumen_global["errores"] += 1
        error_text = traceback.format_exc()

        resumen_global["herramientas"]["OWASP ZAP"] = {
            "exit_code": 99,
            "archivo": "",
            "duracion": 0,
            "severidades": {
                "criticas": 0,
                "altas": 0,
                "medias": 1,
                "bajas": 0
            },
            "error": str(e)
        }

        guardar_scorecard_finding(run_id, {
            "categoria": "OWASP ZAP",
            "herramienta": "OWASP ZAP",
            "control": "Ejecución OWASP ZAP",
            "estado": "Error",
            "riesgo": "Medio",
            "severidad": "Medio",
            "score": 50,
            "evidencia": str(e),
            "recomendacion": "Validar Docker, permisos del usuario y disponibilidad de la imagen OWASP ZAP.",
            "archivo_salida": "",
            "detalle": {"error": str(e)}
        })

        logs.append(f"\n\n===== OWASP ZAP ERROR =====\n{error_text[:5000]}")

    # ============================================================
    # NMAP
    # ============================================================
    if ip:
        comandos.append(("Nmap", [
            herramientas["nmap"],
            "-Pn",
            "-sV",
            "--top-ports",
            "100",
            ip
        ], 240))

    # ============================================================
    # WHATWEB
    # ============================================================
    comandos.append(("WhatWeb", [
        herramientas["whatweb"],
        "--no-errors",
        url
    ], 180))

    # ============================================================
    # NIKTO
    # ============================================================
    comandos.append(("Nikto", [
        herramientas["nikto"],
        "-host",
        url,
        "-nointeractive"
    ], 300))

    # ============================================================
    # NUCLEI
    # ============================================================
    comandos.append(("Nuclei", [
        herramientas["nuclei"],
        "-u",
        url,
        "-severity",
        "critical,high,medium,low",
        "-silent"
    ], 420))

    # ============================================================
    # TESTSSL
    # ============================================================
    comandos.append(("testssl", [
        herramientas["testssl"],
        "--fast",
        "--warnings",
        "batch",
        url
    ], 420))

    total_tools = len(comandos)

    for idx, (nombre, cmd, timeout) in enumerate(comandos, start=1):
        pct = 55 + int((idx / max(total_tools, 1)) * 35)

        scorecard_set_progress(
            run_id,
            pct=pct,
            stage=f"Ejecutando {nombre}",
            tool=nombre
        )

        archivo = scorecard_output_file(run_dir, nombre.lower(), "txt")

        try:
            resultado = scorecard_run_command(cfg, cmd, timeout=timeout)

            with open(archivo, "w", encoding="utf-8", errors="ignore") as f:
                f.write(resultado.get("output") or "")

            guardar_scorecard_output(
                run_id,
                nombre,
                resultado.get("cmd"),
                archivo,
                resultado.get("exit_code"),
                resultado.get("duracion")
            )

            salida = resultado.get("output") or ""
            severidades = scorecard_detectar_severidades(salida)

            for k in ["criticas", "altas", "medias", "bajas"]:
                resumen_global[k] += severidades.get(k, 0)

            resumen_global["herramientas"][nombre] = {
                "exit_code": resultado.get("exit_code"),
                "archivo": archivo,
                "duracion": resultado.get("duracion"),
                "severidades": severidades
            }

            riesgo = "Bajo"

            if severidades["criticas"] > 0:
                riesgo = "Crítico"
            elif severidades["altas"] > 0:
                riesgo = "Alto"
            elif severidades["medias"] > 0:
                riesgo = "Medio"

            evidencia = salida[:1200] if salida else "La herramienta no retornó hallazgos relevantes."

            guardar_scorecard_finding(run_id, {
                "categoria": "Kali Linux Scan",
                "herramienta": nombre,
                "control": f"Ejecución {nombre}",
                "estado": (
                    "Ejecutado"
                    if resultado.get("exit_code") in [0, None]
                    else f"Finalizó con código {resultado.get('exit_code')}"
                ),
                "riesgo": riesgo,
                "severidad": riesgo,
                "score": (
                    100 if riesgo == "Bajo"
                    else 70 if riesgo == "Medio"
                    else 45 if riesgo == "Alto"
                    else 20
                ),
                "evidencia": evidencia,
                "recomendacion": "Revisar la salida técnica y validar remediación con el proveedor.",
                "archivo_salida": archivo,
                "detalle": resumen_global["herramientas"][nombre]
            })

            logs.append(f"\n\n===== {nombre} =====\n{salida[:5000]}")

        except Exception as e:
            resumen_global["errores"] += 1
            error_text = traceback.format_exc()

            with open(archivo, "w", encoding="utf-8", errors="ignore") as f:
                f.write(error_text)

            guardar_scorecard_output(
                run_id,
                nombre,
                " ".join(str(x) for x in cmd),
                archivo,
                99,
                0
            )

            guardar_scorecard_finding(run_id, {
                "categoria": "Kali Linux Scan",
                "herramienta": nombre,
                "control": f"Ejecución {nombre}",
                "estado": "Error",
                "riesgo": "Medio",
                "severidad": "Medio",
                "score": 50,
                "evidencia": str(e),
                "recomendacion": "Validar instalación, rutas y conectividad con Kali.",
                "archivo_salida": archivo,
                "detalle": {"error": str(e)}
            })

            logs.append(f"\n\n===== {nombre} ERROR =====\n{error_text[:5000]}")

    score_kali = scorecard_score_kali_desde_resumen(resumen_global)

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT score_dns, score_ip, score_incidentes, score_darkweb, resumen_json
        FROM scorecard_runs
        WHERE id = ?
    """, (run_id,))

    row = cur.fetchone()

    score_dns = float(row["score_dns"] or 0) if row else 0
    score_ip = float(row["score_ip"] or 0) if row else 0
    score_incidentes = float(row["score_incidentes"] or 100) if row else 100
    score_darkweb = float(row["score_darkweb"] or 100) if row else 100

    score_total = scorecard_calcular_total(
        score_dns,
        score_ip,
        score_kali,
        score_incidentes,
        score_darkweb,
        incluir_kali=True
    )

    nivel = nivel_riesgo_scorecard(score_total)

    resumen_base = {}

    try:
        resumen_base = json.loads(row["resumen_json"] or "{}") if row else {}
    except Exception:
        resumen_base = {}

    resumen_final = {
        **resumen_base,
        "dns_score": score_dns,
        "ip_score": score_ip,
        "kali_score": score_kali,
        "incident_score": score_incidentes,
        "darkweb_score": score_darkweb,
        "score_total": score_total,
        "nivel_riesgo": nivel,
        "kali": resumen_global
    }

    cur.execute("""
        UPDATE scorecard_runs
        SET score_kali = ?,
            score_total = ?,
            nivel_riesgo = ?,
            estado = ?,
            progress_pct = ?,
            current_stage = ?,
            current_tool = ?,
            resumen_json = ?,
            salida_consola = ?,
            fecha_fin = ?
        WHERE id = ?
    """, (
        score_kali,
        score_total,
        nivel,
        "finalizado",
        100,
        "Escaneo Scorecard finalizado",
        None,
        json.dumps(resumen_final, ensure_ascii=False),
        ("\n".join(logs))[:25000],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        run_id
    ))

    conn.commit()
    conn.close()



