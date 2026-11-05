@iso22301_madurez_bp.route("/ingreso", methods=["GET"])
@login_required
def ingreso():
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("No tiene permiso para ingresar información ISO 22301.")

    if Iso22301MadurezPregunta.query.filter_by(tipo="q").count() == 0:
        flash("⚠️ Primero debes importar el instrumento ISO 22301.", "warning")
        return redirect(url_for("madurez_iso22301.parametros"))

    preguntas = (
        Iso22301MadurezPregunta.query
        .filter_by(activo=True, tipo="q")
        .order_by(
            Iso22301MadurezPregunta.bloque_codigo.asc(),
            Iso22301MadurezPregunta.seccion_codigo.asc(),
            Iso22301MadurezPregunta.orden.asc(),
            Iso22301MadurezPregunta.id.asc()
        )
        .all()
    )

    draft = obtener_borrador_iso22301(user.id if user else None)
    respuestas_guardadas = cargar_respuestas_iso22301(draft.id) if draft else {}
    consecutivo_val = (draft.consecutivo if draft else "") or ""

    _, _, progreso_inicial = calcular_progreso_iso22301(
        preguntas,
        respuestas_db=respuestas_guardadas
    )

    grouped = _iso22301_group_questions()
    acc_html = []
    acc_id = 0

    def esc(x):
        return escape(str(x or ""))

    for bloque_codigo, payload in grouped.items():
        acc_id += 1
        func_key = f"iso22301func{acc_id}"
        titulo_bloque = payload.get("titulo") or iso22301_block_title(bloque_codigo) or bloque_codigo
        rows = []

        for q in payload.get("items", []):
            saved = respuestas_guardadas.get(q.id, {})
            saved_estado = (saved.get("estado") or "").strip().upper()
            saved_com = esc(saved.get("comentario") or "")
            qtext = q.pregunta or ""
            evidence_hint = q.evidencia_sugerida or ""
            clause_code = q.seccion_codigo or ""
            domain_name = q.seccion_nombre or ""
            cat_code = q.pregunta_codigo or clause_code or bloque_codigo

            rows.append(f"""
            <div class="col-12 col-xl-6">
              <div class="nistform-qcard h-100">
                <div class="nistform-qhead">
                  <div class="d-flex align-items-center gap-2 flex-wrap">
                    <span class="badge rounded-pill text-bg-light border fw-semibold">{esc(cat_code)}</span>
                    <span class="badge rounded-pill text-bg-primary">Orden {q.orden or 0}</span>
                  </div>
                </div>

                <div class="small text-primary fw-bold mb-2">Cláusula {esc(clause_code)} · {esc(domain_name)}</div>
                <div class="nistform-qtext">{esc(qtext)}</div>
                {f'<div class="alert alert-light border small mt-3 mb-0"><b>Evidencia sugerida:</b> {esc(evidence_hint)}</div>' if evidence_hint else ''}

                <div class="nistform-radio-row">
                  <label class="nistform-radio-card">
                    <input class="form-check-input" type="radio" name="st_{q.id}" value="NA" {"checked" if saved_estado == "NA" else ""}>
                    <span>N/A</span>
                  </label>

                  <label class="nistform-radio-card">
                    <input class="form-check-input" type="radio" name="st_{q.id}" value="SI" {"checked" if saved_estado == "SI" else ""}>
                    <span>Sí</span>
                  </label>

                  <label class="nistform-radio-card">
                    <input class="form-check-input" type="radio" name="st_{q.id}" value="PARCIAL" {"checked" if saved_estado == "PARCIAL" else ""}>
                    <span>Parcial</span>
                  </label>

                  <label class="nistform-radio-card">
                    <input class="form-check-input" type="radio" name="st_{q.id}" value="NO" {"checked" if saved_estado == "NO" else ""}>
                    <span>No</span>
                  </label>
                </div>

                <div class="mt-3">
                  <label class="form-label small fw-bold text-black mb-1">Comentarios / evidencia</label>
                  <textarea class="form-control form-control-sm"
                            name="cm_{q.id}"
                            rows="3"
                            placeholder="Comentarios / evidencia">{saved_com}</textarea>
                </div>
              </div>
            </div>
            """)

        acc_html.append(f"""
        <div class="accordion-item nistform-acc-item">
          <h2 class="accordion-header" id="h{func_key}">
            <button class="accordion-button {'collapsed' if acc_id != 1 else ''}"
                    type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#c{func_key}">
              <div class="nistform-acc-inner">
                <div>
                  <div class="nistform-func-title">{esc(titulo_bloque)}</div>
                  <div class="nistform-func-subtitle">Capítulo ISO 22301 · {esc(bloque_codigo)}</div>
                </div>
                <span class="badge rounded-pill text-bg-primary">{len(payload.get('items', []))} preguntas</span>
              </div>
            </button>
          </h2>

          <div id="c{func_key}" class="accordion-collapse collapse {'show' if acc_id == 1 else ''}">
            <div class="accordion-body nistform-acc-body">
              <div class="nistform-cat-block">
                <div class="nistform-cat-title">
                  <span>{esc(bloque_codigo)}</span>
                  <small>{esc(titulo_bloque)}</small>
                </div>
                <div class="row g-3">{''.join(rows)}</div>
              </div>
            </div>
          </div>
        </div>
        """)

    alerta_borrador = ""
    if draft:
        alerta_borrador = f"""
        <div class="alert alert-info rounded-4 border-0 shadow-sm">
          <i class="bi bi-info-circle-fill me-2"></i>
          Tienes un borrador ISO 22301 cargado automáticamente.
          <strong>Progreso actual:</strong> {progreso_inicial}%.
        </div>
        """

    disabled_analizar = "" if progreso_inicial == 100 else "disabled"

    content = f"""
    <div class="nistform-shell iso22301-no-global-loader">

      <style>
        #SGSI_PROGRESS_GLOBAL,
        #globalLoader,
        #loader,
        #progressOverlay,
        .modal-backdrop,
        .progress-overlay,
        .loader-overlay,
        .sgsi-loader,
        .sgsi-progress {{
          display: none !important;
          visibility: hidden !important;
          opacity: 0 !important;
          pointer-events: none !important;
        }}
      </style>

      <div class="nistform-header-card">
        <div class="nistform-header-overlay">
          <div class="nistform-header-text">
            <h3 class="nistform-title m-0">Nivel de Madurez — ISO 22301</h3>
            <div class="nistform-subtitle">Ingreso de información del instrumento ISO 22301</div>
          </div>
        </div>
      </div>

      <div class="nistform-header-actions">
        <a href="{url_for('madurez_iso22301.inicio_iso22301')}" class="btn btn-light rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver
        </a>

        <a href="{url_for('madurez_iso22301.historial')}" class="btn btn-outline-primary rounded-pill px-4 fw-bold">
          <i class="bi bi-clock-history me-2"></i>Historial
        </a>
      </div>

      <div class="nistform-card p-4">
        {alerta_borrador}

        <form id="iso22301IngresoForm"
              method="POST"
              action="{url_for('madurez_iso22301.ingreso_guardar')}"
              novalidate>

          <input type="hidden" name="draft_id" value="{draft.id if draft else ''}">
          <input type="hidden" name="accion" id="iso22301Accion" value="guardar">

          <div class="nistform-section-title">Información de la revisión</div>

          <div class="mb-4">
            <label class="text-black form-label fw-semibold">
              Consecutivo de la Revisión <span class="text-danger">*</span>
            </label>

            <input type="text"
                   class="form-control form-control-lg rounded-pill"
                   name="consecutivo"
                   id="iso22301Consecutivo"
                   value="{esc(consecutivo_val)}"
                   autocomplete="off">

            <div id="iso22301ConsecutivoError"
                 class="invalid-feedback d-none fw-bold mt-2">
              Debes ingresar el consecutivo de la Revisión.
            </div>
          </div>

          <div class="nistform-section-title">
            📊 Progreso del instrumento
          </div>

          <div class="mb-4">
            <div class="progress nistform-progress">
              <div id="iso22301ProgressBar"
                   class="progress-bar progress-bar-striped progress-bar-animated"
                   role="progressbar"
                   style="width:{progreso_inicial}%"
                   aria-valuemin="0"
                   aria-valuemax="100"
                   aria-valuenow="{progreso_inicial}">
                {progreso_inicial}%
              </div>
            </div>

            <div class="text-center small text-muted mt-2">
              <span id="iso22301ProgressText">{progreso_inicial}%</span> del instrumento completado
            </div>
          </div>

          <div class="nistform-section-title">Instrumento de evaluación</div>

          <div class="accordion nistform-accordion" id="accIso22301">
            {''.join(acc_html)}
          </div>

          <div class="d-flex justify-content-center gap-3 flex-wrap mt-4">
            <button class="btn btn-outline-primary btn-lg rounded-pill px-5 shadow fw-semibold"
                    type="button"
                    id="btnGuardarIso22301">
              <i class="bi bi-save2 me-2"></i>Guardar
            </button>

            <button id="btnAnalizarIso22301"
                    class="btn btn-primary btn-lg rounded-pill px-5 shadow fw-semibold"
                    type="button"
                    {disabled_analizar}>
              <i class="bi bi-bar-chart-line-fill me-2"></i>Analizar
            </button>
          </div>
        </form>
      </div>
    </div>

    <script>
    (function () {{

      const total = {len(preguntas)};

      function hideLoader() {{
        const ids = ["SGSI_PROGRESS_GLOBAL", "globalLoader", "loader", "progressOverlay"];
        ids.forEach(function(id) {{
          const el = document.getElementById(id);
          if (el) {{
            el.style.display = "none";
            el.style.visibility = "hidden";
            el.style.opacity = "0";
            el.style.pointerEvents = "none";
            el.classList.add("d-none");
          }}
        }});

        document.querySelectorAll(".modal-backdrop, .progress-overlay, .loader-overlay, .sgsi-loader, .sgsi-progress").forEach(function(el) {{
          el.style.display = "none";
          el.style.visibility = "hidden";
          el.style.opacity = "0";
          el.style.pointerEvents = "none";
          el.classList.add("d-none");
        }});
      }}

      function marcadas() {{
        const names = new Set();
        document.querySelectorAll('input[type="radio"][name^="st_"]:checked').forEach(function(r) {{
          names.add(r.name);
        }});
        return names.size;
      }}

      function actualizarProgresoIso22301() {{
        const respondidas = marcadas();
        const porcentaje = total > 0 ? Math.round((respondidas / total) * 100) : 0;
        const bar = document.getElementById("iso22301ProgressBar");
        const text = document.getElementById("iso22301ProgressText");
        const btnAnalizar = document.getElementById("btnAnalizarIso22301");

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

      function validarConsecutivo() {{
        const consecutivo = document.getElementById("iso22301Consecutivo");
        const msg = document.getElementById("iso22301ConsecutivoError");

        if (!consecutivo || !consecutivo.value.trim()) {{
          hideLoader();

          if (consecutivo) {{
            consecutivo.classList.add("is-invalid");
            consecutivo.focus();
          }}

          if (msg) {{
            msg.classList.remove("d-none");
            msg.style.display = "block";
          }}

          return false;
        }}

        consecutivo.classList.remove("is-invalid");

        if (msg) {{
          msg.classList.add("d-none");
          msg.style.display = "none";
        }}

        return true;
      }}

      function enviarIso22301(accion) {{
        hideLoader();

        if (!validarConsecutivo()) {{
          hideLoader();
          return false;
        }}

        if (accion === "analizar" && marcadas() < total) {{
          hideLoader();
          alert("Para analizar debes completar el 100% del instrumento.");
          return false;
        }}

        const form = document.getElementById("iso22301IngresoForm");
        const accionInput = document.getElementById("iso22301Accion");

        if (!form) {{
          return false;
        }}

        if (accionInput) {{
          accionInput.value = accion;
        }}

        hideLoader();

        HTMLFormElement.prototype.submit.call(form);
        return false;
      }}

      window.iso22301GuardarSinLoader = function(e) {{
        if (e) {{
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
        }}
        return enviarIso22301("guardar");
      }};

      window.iso22301AnalizarSinLoader = function(e) {{
        if (e) {{
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
        }}
        return enviarIso22301("analizar");
      }};

      document.addEventListener("DOMContentLoaded", function () {{
        hideLoader();

        const btnGuardar = document.getElementById("btnGuardarIso22301");
        const btnAnalizar = document.getElementById("btnAnalizarIso22301");
        const consecutivo = document.getElementById("iso22301Consecutivo");
        const form = document.getElementById("iso22301IngresoForm");

        if (btnGuardar) {{
          btnGuardar.onclick = iso22301GuardarSinLoader;
        }}

        if (btnAnalizar) {{
          btnAnalizar.onclick = iso22301AnalizarSinLoader;
        }}

        if (consecutivo) {{
          consecutivo.addEventListener("input", function() {{
            validarConsecutivo();
            hideLoader();
          }});
        }}

        if (form) {{
          form.addEventListener("submit", function(e) {{
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            hideLoader();
            return false;
          }}, true);
        }}

        document.querySelectorAll('input[type="radio"][name^="st_"]').forEach(function(radio) {{
          radio.addEventListener("change", actualizarProgresoIso22301);
        }});

        actualizarProgresoIso22301();
        hideLoader();
        setInterval(hideLoader, 250);
      }});
    }})();
    </script>

    {iso22301_nistform_css()}
    """

    return render_template_string(BASE, title="Ingreso ISO 22301", content=content)


# ============================================================
# GUARDAR / ANALIZAR — ISO 22301
# ============================================================

@iso22301_madurez_bp.route("/ingreso/guardar", methods=["POST"])
@login_required
def ingreso_guardar():
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("No tiene permiso para guardar ni analizar información ISO 22301.")

    consecutivo = (request.form.get("consecutivo") or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    accion = (request.form.get("accion") or "guardar").strip().lower()
    draft_id = (request.form.get("draft_id") or "").strip()

    if not consecutivo:
        flash("Debes ingresar el consecutivo de la Revisión.", "warning")
        return redirect(url_for("madurez_iso22301.ingreso"))

    preguntas = (
        Iso22301MadurezPregunta.query
        .filter_by(activo=True, tipo="q")
        .order_by(
            Iso22301MadurezPregunta.bloque_codigo.asc(),
            Iso22301MadurezPregunta.orden.asc(),
            Iso22301MadurezPregunta.id.asc()
        )
        .all()
    )

    if not preguntas:
        flash("⚠️ No hay preguntas activas cargadas en el instrumento ISO 22301.", "warning")
        return redirect(url_for("madurez_iso22301.inicio_iso22301"))

    respondidas, total, progreso_pct = calcular_progreso_iso22301(preguntas, form_data=request.form)

    try:
        run = None

        if draft_id and draft_id.isdigit():
            run = Iso22301MadurezRun.query.filter_by(id=int(draft_id)).first()

        if not run:
            run = obtener_borrador_iso22301(user.id if user else None)

        if respondidas == 0:
            if run and _contar_respuestas_run_iso22301(run.id) == 0:
                Iso22301MadurezRespuesta.query.filter_by(run_id=run.id).delete(synchronize_session=False)
                Iso22301MadurezCriterioAnalisis.query.filter_by(run_id=run.id).delete(synchronize_session=False)
                db.session.delete(run)
                db.session.commit()

            flash("⚠️ Debes responder al menos una pregunta antes de guardar o analizar.", "warning")
            return redirect(url_for("madurez_iso22301.ingreso"))

        if not run:
            run = Iso22301MadurezRun(
                consecutivo=consecutivo,
                company_name=consecutivo,
                user_id=user.id if user else None,
                estado="BORRADOR",
                progreso_pct=0,
                resumen_json="{}",
                pct_general=0.0,
                radar_overall_b64=None
            )
            db.session.add(run)
            db.session.flush()

        run.consecutivo = consecutivo
        run.company_name = consecutivo
        run.user_id = user.id if user else run.user_id
        run.progreso_pct = progreso_pct
        run.updated_at = datetime.utcnow()

        Iso22301MadurezRespuesta.query.filter_by(run_id=run.id).delete(synchronize_session=False)

        respuestas_insertadas = 0

        for q in preguntas:
            st = (request.form.get(f"st_{q.id}") or "").strip().upper()
            cm = (request.form.get(f"cm_{q.id}") or "").replace("\r\n", "\n").replace("\r", "\n").strip()

            if st in ("SI", "PARCIAL", "NO", "NA"):
                db.session.add(Iso22301MadurezRespuesta(
                    run_id=run.id,
                    pregunta_id=q.id,
                    estado=st,
                    comentario=cm
                ))
                respuestas_insertadas += 1

        if accion == "analizar":
            if progreso_pct < 100:
                db.session.commit()
                flash("⚠️ Para analizar debes completar el 100% del instrumento.", "warning")
                return redirect(url_for("madurez_iso22301.ingreso"))

            run.estado = "FINALIZADO"
            run.progreso_pct = 100
            db.session.commit()

            run_id = run_analysis_from_iso22301_run(run.id)

            flash(f"✅ Revisión ISO 22301 analizada correctamente. Se consolidaron {respuestas_insertadas} respuestas.", "success")
            return redirect(url_for("madurez_iso22301.detalle", run_id=run_id))

        db.session.commit()
        flash("✅ Información ISO 22301 guardada correctamente.", "success")
        return redirect(url_for("madurez_iso22301.ingreso"))

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        flash(f"❌ Error guardando la revisión ISO 22301: {e}", "danger")
        return redirect(url_for("madurez_iso22301.ingreso"))

# ============================================================
# HISTORIAL ISO 22301 — COMPACTO SIN LOADER
# ============================================================

@iso22301_madurez_bp.route("/historial", methods=["GET"])
@login_required
def historial():

    user = User.query.get(session.get("user_id"))

    denied = iso22301_check_access_or_redirect(
        user,
        "No tiene permiso para ver historial ISO 22301."
    )

    if denied:
        return denied

    runs = (
        Iso22301MadurezRun.query
        .filter(Iso22301MadurezRun.estado == "FINALIZADO")
        .order_by(
            Iso22301MadurezRun.created_at.desc(),
            Iso22301MadurezRun.id.desc()
        )
        .all()
    )

    # Actualiza evaluaciones históricas creadas con la fórmula anterior,
    # sin incluir N/A en el denominador. Se reconstruye el resumen para
    # corregir también capítulos que tienen únicamente respuestas N/A.
    historial_actualizado = False
    for run in runs:
        resumen_corregido = _iso22301_build_resumen(run.id)
        resumen_json_corregido = json.dumps(resumen_corregido, ensure_ascii=False)
        pct_corregido = iso22301_pct_general_from_resumen(resumen_corregido)

        if (run.resumen_json or "{}") != resumen_json_corregido:
            run.resumen_json = resumen_json_corregido
            historial_actualizado = True

        if abs(float(run.pct_general or 0) - pct_corregido) > 0.005:
            run.pct_general = pct_corregido
            historial_actualizado = True
    if historial_actualizado:
        db.session.commit()

    # =========================================================
    # BOTÓN NUEVA REVISIÓN
    # =========================================================
    nueva_revision_btn = ""

    if iso22301_user_can_execute(user):

        nueva_revision_btn = f"""
        <a href="{url_for('madurez_iso22301.ingreso')}"
           class="btn btn-primary btn-sm rounded-pill px-3 fw-bold shadow-sm iso22301-no-loader">

          <i class="bi bi-plus-circle me-1"></i>
          Nueva revisión

        </a>
        """

    # =========================================================
    # FILAS
    # =========================================================
    rows = []

    for run in runs:

        nivel = iso22301_resolver_nivel(run.pct_general or 0)

        badge = f"""
        <span class="iso22301hist-badge"
              style="background:{nivel.get('color','#6c757d')};">

          {escape(nivel.get('nivel','Sin nivel'))}

        </span>
        """

        eliminar_btn = ""

        if iso22301_user_can_execute(user):

            eliminar_btn = f"""
            <form method="POST"
                  action="{url_for('madurez_iso22301.eliminar_run', run_id=run.id)}"
                  class="d-inline iso22301-no-loader"
                  onsubmit="return confirm('¿Seguro que deseas eliminar esta revisión ISO 22301?');">

              <button type="submit"
                      class="btn btn-danger btn-xs iso22301hist-btn">

                <i class="bi bi-trash"></i>
                Eliminar

              </button>

            </form>
            """

        rows.append(f"""
        <tr>

          <td class="fw-semibold iso22301hist-text-main">
            {escape(run.consecutivo or '')}
          </td>

          <td class="text-center iso22301hist-text">
            {run.created_at.strftime('%Y-%m-%d %H:%M') if run.created_at else ''}
          </td>

          <td class="text-center">
            <span class="iso22301hist-pct">
              {float(run.pct_general or 0):.2f}%
            </span>
          </td>

          <td class="text-center">
            {badge}
          </td>

          <td class="text-center">

            <div class="d-flex justify-content-center gap-1 flex-wrap">

              <a href="{url_for('madurez_iso22301.detalle', run_id=run.id)}"
                 class="btn btn-primary btn-xs iso22301hist-btn iso22301-no-loader">

                <i class="bi bi-eye"></i>
                Ver

              </a>

              {eliminar_btn}

            </div>

          </td>

        </tr>
        """)

    # =========================================================
    # VACÍO
    # =========================================================
    if not rows:

        rows.append("""
        <tr>
          <td colspan="5"
              class="text-center text-muted py-4">

            No existen revisiones ISO 22301 finalizadas.

          </td>
        </tr>
        """)

    # =========================================================
    # HTML
    # =========================================================
    content = f"""

    <div class="iso22301hist-shell">

      <!-- HEADER -->
      <div class="iso22301hist-header-card">

        <div class="iso22301hist-header-overlay">

          <div class="iso22301hist-header-text">

            <h3 class="iso22301hist-title m-0">
              Historial de Revisiones — ISO 22301
            </h3>

            <div class="iso22301hist-subtitle">
              Consulta de evaluaciones históricas y resultados consolidados.
            </div>

          </div>

        </div>

      </div>

      <!-- BOTONES -->
      <div class="iso22301hist-header-actions">

        <a href="{url_for('madurez_iso22301.inicio_iso22301')}"
           class="btn btn-light btn-sm rounded-pill px-3 fw-bold shadow-sm iso22301-no-loader">

          <i class="bi bi-arrow-left me-1"></i>
          Volver

        </a>

        {nueva_revision_btn}

      </div>

      <!-- TABLA -->
      <div class="iso22301hist-card">

        <div class="iso22301hist-section-title">
          Revisiones finalizadas
        </div>

        <div class="table-responsive">

          <table class="table table-hover align-middle iso22301hist-table">

            <thead>
              <tr>
                <th>Consecutivo</th>
                <th class="text-center">Fecha</th>
                <th class="text-center">% Cumplimiento</th>
                <th class="text-center">Nivel</th>
                <th class="text-center">Acciones</th>
              </tr>
            </thead>

            <tbody>
              {''.join(rows)}
            </tbody>

          </table>

        </div>

      </div>

    </div>

    <!-- =================================================== -->
    <!-- CSS -->
    <!-- =================================================== -->

    <style>

      body {{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .iso22301hist-shell {{
        width:94%;
        max-width:1180px;
        margin:8px auto 24px auto;
      }}

      .iso22301hist-header-card {{
        background:linear-gradient(
          135deg,
          #2f6fb6 0%,
          #3f86d6 55%,
          #5aa3ea 100%
        );

        height:72px;

        display:flex;
        align-items:center;
        justify-content:center;

        border-radius:16px;

        box-shadow:0 10px 24px rgba(0,0,0,.24);

        margin-bottom:10px;
        overflow:hidden;
      }}

      .iso22301hist-header-overlay {{
        width:100%;
        height:100%;

        display:flex;
        align-items:center;
        justify-content:center;

        text-align:center;

        background:rgba(0,0,0,.08);

        padding:6px 18px;
      }}

      .iso22301hist-title {{
        color:#fff;
        font-size:1.28rem;
        font-weight:800;
        line-height:1.1;
        text-shadow:0 2px 8px rgba(0,0,0,.28);
      }}

      .iso22301hist-subtitle {{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:3px;
        font-weight:500;
      }}

      .iso22301hist-header-actions {{
        display:flex;
        justify-content:center;
        align-items:center;
        gap:6px;
        flex-wrap:wrap;
        margin:8px 0 10px 0;
      }}

      .iso22301hist-card {{
        background:rgba(255,255,255,.95);
        border:1px solid rgba(255,255,255,.60);
        border-radius:16px;
        box-shadow:0 10px 24px rgba(0,0,0,.20);
        padding:12px;
        overflow:hidden;
      }}

      .iso22301hist-section-title {{
        color:#0f3d68;
        font-size:.92rem;
        font-weight:800;
        margin-bottom:8px;
        padding-bottom:6px;
        border-bottom:1px solid rgba(15,61,104,.12);
      }}

      .iso22301hist-table {{
        margin-bottom:0;
        font-size:.80rem;
      }}

      .iso22301hist-table thead th {{
        background:#0f3d68;
        color:#fff;
        font-size:.74rem;
        font-weight:800;
        padding:7px 8px;
        vertical-align:middle;
        white-space:nowrap;
      }}

      .iso22301hist-table tbody td {{
        padding:6px 8px;
        vertical-align:middle;
        background:rgba(255,255,255,.96);
        border-bottom:1px solid rgba(15,61,104,.08);
      }}

      .iso22301hist-table tbody tr:hover td {{
        background:#eef6ff;
      }}

      .iso22301hist-text-main {{
        color:#0b1220;
        font-size:.80rem;
      }}

      .iso22301hist-text {{
        color:#374151;
        font-size:.68rem;
      }}

      .iso22301hist-pct {{
        color:#0d6efd;
        font-weight:800;
        font-size:.80rem;
      }}

      .iso22301hist-badge {{
        display:inline-block;
        color:#fff;
        font-size:.68rem;
        font-weight:800;
        padding:4px 8px;
        border-radius:999px;
        line-height:1;
        white-space:nowrap;
      }}

      .iso22301hist-btn {{
        border-radius:999px !important;
        padding:3px 8px !important;
        font-size:.64rem !important;
        font-weight:700 !important;
        line-height:1.2 !important;
      }}

      .btn-xs {{
        --bs-btn-padding-y:.16rem;
        --bs-btn-padding-x:.40rem;
        --bs-btn-font-size:.70rem;
      }}

    </style>

    <!-- =================================================== -->
    <!-- DESACTIVAR LOADER -->
    <!-- =================================================== -->

    <script>

      document.addEventListener("DOMContentLoaded", function() {{

        // ==========================================
        // QUITAR OVERLAY GLOBAL
        // ==========================================
        const overlays = [
          "SGSI_PROGRESS_GLOBAL",
          "globalLoader",
          "loader",
          "progressOverlay"
        ];

        overlays.forEach(function(id) {{

          const el = document.getElementById(id);

          if (el) {{
            el.style.display = "none";
            el.style.visibility = "hidden";
            el.classList.add("d-none");
          }}

        }});

        // ==========================================
        // DESACTIVAR SHOWLOADER
        // ==========================================
        document.querySelectorAll(".iso22301-no-loader").forEach(function(el) {{

          el.removeAttribute("onclick");
          el.onclick = null;

        }});

      }});

    </script>
    """

    return render_template_string(
        BASE,
        title="Historial ISO 22301",
        content=content
    )


# ============================================================
# ISO 22301 — DETALLE POR CRITERIO
# ============================================================

@iso22301_madurez_bp.route("/detalle/<int:run_id>/criterio/<bloque_codigo>", methods=["GET"])
@login_required
def detalle_criterio(run_id: int, bloque_codigo: str):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_access(user):
        return iso22301_deny_access("No tiene permiso para ver el detalle del capítulo ISO 22301.")

    run = Iso22301MadurezRun.query.get_or_404(run_id)
    bloque_codigo = (bloque_codigo or "").strip().upper()

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    d = resumen.get(bloque_codigo)
    if not d:
        flash("No se encontró información para este capítulo ISO 22301.", "warning")
        return redirect(url_for("madurez_iso22301.detalle", run_id=run.id))

    items = d.get("items", []) or []
    nombre = d.get("nombre") or iso22301_block_title(bloque_codigo) or bloque_codigo
    pct = float(d.get("pct", 0) or 0)
    aplicables = int(d.get("validas", 0) or 0)
    nivel = (
        iso22301_nivel_visual_por_pct(pct)
        if aplicables > 0
        else {"nivel": "No aplica", "score": 0, "color": "#6c757d"}
    )

    rows = []
    for it in items:
        estado = (it.get("estado") or "").upper()
        color = {
            "SI": "success",
            "PARCIAL": "warning text-dark",
            "NO": "danger",
            "NA": "secondary"
        }.get(estado, "secondary")

        rows.append(f"""
        <tr>
          <td style="width:120px;">
            <span class="badge bg-light text-primary border">
              {escape(it.get("pregunta_codigo") or "")}
            </span>
          </td>
          <td>
            <div class="fw-bold text-dark">{escape(it.get("pregunta") or "")}</div>
            <div class="small text-muted mt-1">{escape(it.get("comentario") or "")}</div>
          </td>
          <td class="text-center" style="width:110px;">
            <span class="badge bg-{color}">{escape(estado)}</span>
          </td>
        </tr>
        """)

    content = f"""
    <div class="nistdet-shell">

      <div class="nistdet-header-card">
        <div class="nistdet-header-overlay">
          <div class="nistdet-header-text">
            <h3 class="nistdet-title m-0">Preguntas ISO 22301 — {escape(nombre)}</h3>
            <div class="nistdet-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
              · Cumplimiento: <b>{pct:.2f}%</b>
              · Nivel: <b>{escape(nivel.get("nivel",""))}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="nistdet-header-actions">
        <a href="{url_for('madurez_iso22301.detalle', run_id=run.id)}"
           class="btn nistdet-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al detalle
        </a>
      </div>

      <div class="nistdet-card p-4">
        <div class="nistdet-section-title mb-3">{escape(nombre)}</div>

        <div class="table-responsive">
          <table class="table table-sm table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Código</th>
                <th>Pregunta / Evidencia</th>
                <th class="text-center">Estado</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    {iso22301_nist_css('nistdet', '📊')}
    """

    return render_template_string(BASE, title="Detalle capítulo ISO 22301", content=content)


# ============================================================
# ISO 22301 — ANÁLISIS POR CRITERIO
# ============================================================

@iso22301_madurez_bp.route("/detalle/<int:run_id>/criterio/<bloque_codigo>/analisis", methods=["GET", "POST"])
@login_required
def analisis_criterio(run_id: int, bloque_codigo: str):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_access(user):
        return iso22301_deny_access("No tiene permiso para ver el análisis ISO 22301.")

    run = Iso22301MadurezRun.query.get_or_404(run_id)
    bloque_codigo = (bloque_codigo or "").strip().upper()

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    d = resumen.get(bloque_codigo)
    if not d:
        flash("No se encontró información para este capítulo ISO 22301.", "warning")
        return redirect(url_for("madurez_iso22301.detalle", run_id=run.id))

    nombre = d.get("nombre") or iso22301_block_title(bloque_codigo) or bloque_codigo
    pct = float(d.get("pct", 0) or 0)
    items = d.get("items", []) or []
    aplicables = int(d.get("validas", 0) or 0)

    analisis = Iso22301MadurezCriterioAnalisis.query.filter_by(
        run_id=run.id,
        bloque_codigo=bloque_codigo
    ).first()

    if request.method == "POST":
        if not iso22301_user_can_execute(user):
            return iso22301_deny_execute("El rol Auditor no puede generar análisis con IA.")

        if aplicables <= 0:
            flash("Este capítulo no tiene preguntas aplicables; todas fueron marcadas N/A.", "warning")
            return redirect(url_for("madurez_iso22301.analisis_criterio", run_id=run.id, bloque_codigo=bloque_codigo))

        prompt = _iso22301_ai_prompt_criterio(run, bloque_codigo, nombre, pct, items)

        try:
            raw = _iso22301_ai_text(prompt, max_tokens=1200)
            obj = _extraer_json_objeto_iso22301(raw)

            estado_actual = (obj.get("estado_actual") or "").strip() if isinstance(obj, dict) else ""
            estado_requerido = (obj.get("estado_requerido") or "").strip() if isinstance(obj, dict) else ""
            plan_raw = json.dumps(obj.get("plan_accion", []), ensure_ascii=False) if isinstance(obj, dict) else raw
            plan_txt = _build_plan_accion_iso22301_texto(obj.get("plan_accion", [])) if isinstance(obj, dict) else raw

            if not analisis:
                analisis = Iso22301MadurezCriterioAnalisis(
                    run_id=run.id,
                    bloque_codigo=bloque_codigo,
                    bloque_nombre=nombre
                )
                db.session.add(analisis)

            analisis.estado_actual = estado_actual
            analisis.estado_requerido = estado_requerido
            analisis.plan_accion_ai = plan_txt or plan_raw
            analisis.plan_accion_editado = plan_txt or plan_raw
            db.session.commit()

            flash("✅ Análisis ISO 22301 generado con IA.", "success")

        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            flash(f"❌ Error generando análisis ISO 22301: {e}", "danger")

        return redirect(url_for("madurez_iso22301.analisis_criterio", run_id=run.id, bloque_codigo=bloque_codigo))

    estado_actual = analisis.estado_actual if analisis else ""
    estado_requerido = analisis.estado_requerido if analisis else ""
    plan_accion = _normalizar_plan_accion_iso22301_texto(
        (analisis.plan_accion_editado or analisis.plan_accion_ai) if analisis else ""
    )

    boton_generar = ""
    if iso22301_user_can_execute(user):
        boton_generar = """
        <form method="POST" class="m-0">
          <button type="submit" class="btn nistdet-btn-success rounded-pill px-4 fw-bold">
            <i class="bi bi-magic me-2"></i>Generar análisis IA
          </button>
        </form>
        """
    else:
        boton_generar = """
        <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
          <i class="bi bi-lock me-2"></i>Solo lectura
        </button>
        """

    content = f"""
    <div class="nistdet-shell">

      <div class="nistdet-header-card">
        <div class="nistdet-header-overlay">
          <div class="nistdet-header-text">
            <h3 class="nistdet-title m-0">Análisis ISO 22301 — {escape(nombre)}</h3>
            <div class="nistdet-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
              · Cumplimiento: <b>{pct:.2f}%</b>
            </div>
          </div>
        </div>
      </div>

      <div class="nistdet-header-actions">
        <a href="{url_for('madurez_iso22301.detalle', run_id=run.id)}"
           class="btn nistdet-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al detalle
        </a>
        {boton_generar}
      </div>

      <div class="row g-3">
        <div class="col-12 col-xl-6">
          <div class="nistdet-card p-4 h-100">
            <div class="nistdet-section-title">Estado actual</div>
            <div class="nistdet-exec-box mt-3">
              {escape(estado_actual) if estado_actual else "No se ha generado análisis."}
            </div>
          </div>
        </div>

        <div class="col-12 col-xl-6">
          <div class="nistdet-card p-4 h-100">
            <div class="nistdet-section-title">Estado requerido</div>
            <div class="nistdet-exec-box mt-3">
              {escape(estado_requerido) if estado_requerido else "No se ha generado análisis."}
            </div>
          </div>
        </div>

        <div class="col-12">
          <div class="nistdet-card p-4">
            <div class="nistdet-section-title">Plan de acción</div>
            <div class="nistdet-exec-box mt-3">
              <pre class="mb-0" style="white-space:pre-wrap;font-family:inherit;">{escape(plan_accion) if plan_accion else "No se ha generado plan de acción."}</pre>
            </div>
          </div>
        </div>
      </div>

    </div>

    {iso22301_nist_css('nistdet', '📊')}
    """

    return render_template_string(BASE, title="Análisis capítulo ISO 22301", content=content)

# ============================================================
# DETALLE ISO 22301 — MISMO DISEÑO NIST
# ============================================================

@iso22301_madurez_bp.route("/detalle/<int:run_id>", methods=["GET"])
@login_required
def detalle(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_access(user):
        return iso22301_deny_access("No tiene permiso para ver el detalle ISO 22301.")

    # Recalcula también las evaluaciones anteriores con la fórmula vigente.
    run_analysis_from_iso22301_run(run_id)
    run = Iso22301MadurezRun.query.get_or_404(run_id)
    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    def _nl2br_iso22301(s: str) -> str:
        txt = iso22301_normalizar_texto_rico_guardado(s or "")
        return txt.replace("\n", "<br>")

    radar_labels, radar_values = iso22301_pct_por_criterio(resumen, ISO22301_BLOCK_ORDER)
    radar_b64 = run.radar_overall_b64 or iso22301_radar_b64(
        radar_labels,
        radar_values,
        title="Radar por Capítulo"
    )

    informe_ai = iso22301_normalizar_texto_rico_guardado(run.informe_ejecutivo_ai or "")
    informe_editado = iso22301_normalizar_texto_rico_guardado(run.informe_ejecutivo_editado or "")
    informe_mostrar = informe_editado if informe_editado else informe_ai

    nivel_general = iso22301_nivel_visual_por_pct(run.pct_general)
    nivel_general_texto = (nivel_general.get("nivel") or "").strip()
    nivel_general_nombre = nivel_general_texto.split(":", 1)[1].strip() if ":" in nivel_general_texto else nivel_general_texto

    botones_ia = ""
    if iso22301_user_can_execute(user):
        botones_ia = f"""
          <form method="POST"
                  action="{url_for('madurez_iso22301.informe_ejecutivo_generar', run_id=run.id)}"
                  class="m-0">
              <button type="submit" class="btn nistdet-btn-success rounded-pill px-4 fw-bold">
                <i class="bi bi-magic me-2"></i>Generar con IA
              </button>
            </form>

            <a href="{url_for('madurez_iso22301.informe_ejecutivo_editar', run_id=run.id)}"
               class="btn btn-primary rounded-pill px-4 fw-bold">
              <i class="bi bi-pencil-square me-2"></i>Editar
            </a>
        """
    else:
        botones_ia = """
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            <i class="bi bi-lock me-2"></i>Solo lectura
          </button>
        """

    pdf_btn = ""
    if iso22301_user_can_access(user):
        pdf_btn = f"""
        <a href="{url_for('madurez_iso22301.exportar_pdf', run_id=run.id)}"
           class="btn btn-danger rounded-pill px-4 fw-bold">
          <i class="bi bi-file-earmark-pdf me-2"></i>Exportar PDF
        </a>
        """

    top_html = f"""
    <div class="row g-3 mb-4">

      <div class="col-12 col-xl-5">
        <div class="nistdet-card p-4 h-100">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
            <div>
              <div class="nistdet-card-title">📊 Radar por Capítulo General</div>
              <div class="text-muted small">
                Resultado consolidado por criterios ISO 22301.
              </div>
            </div>

            <div class="text-end">
              <div class="badge rounded-pill px-3 py-2"
                   style="background:{nivel_general.get('color','#6c757d')}; color:#fff; font-size:.82rem;">
                Nivel {nivel_general.get('score', 0)}
              </div>
              <div class="small text-muted mt-1">{escape(nivel_general_nombre)}</div>
            </div>
          </div>

          <div class="text-center mt-3">
            {f'<img class="img-fluid nistdet-radar-img-small" src="data:image/png;base64,{radar_b64}">' if radar_b64 else '<div class="alert alert-warning mb-0">No fue posible generar el radar.</div>'}
          </div>
        </div>
      </div>

      <div class="col-12 col-xl-7">
        <div class="nistdet-card p-4 h-100">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div>
              <div class="nistdet-card-title">🧾 Informe ejecutivo</div>
              <div class="text-muted small">
                Síntesis ejecutiva generada con IA a partir de los resultados por capítulo ISO 22301.
              </div>
            </div>

            <div class="d-flex gap-2 flex-wrap">
              {botones_ia}
            </div>
          </div>

          <div class="nistdet-exec-box mt-3">
            {f'<div class="nistdet-exec-text">{_nl2br_iso22301(escape(informe_mostrar))}</div>' if informe_mostrar else '''
              <div class="text-center py-4">
                <div class="mb-2" style="font-size:2rem;">&#129302;</div>
                <div class="fw-bold text-black">Aún no hay informe ejecutivo</div>
                <div class="text-muted small mt-1">
                  No se ha generado informe ejecutivo para esta revisión.
                </div>
              </div>
            '''}
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

        radius = 44
        circumference = math.pi * radius
        progress = circumference * (pct / 100.0)

        return f"""
        <svg width="150" height="96" viewBox="0 0 120 78" aria-hidden="true">
          <path d="M16 62 A44 44 0 0 1 104 62"
                fill="none" stroke="#e9ecef" stroke-width="10" stroke-linecap="round"/>
          <path d="M16 62 A44 44 0 0 1 104 62"
                fill="none" stroke="{color}" stroke-width="10" stroke-linecap="round"
                stroke-dasharray="{progress:.2f} {circumference:.2f}"/>
          <text x="60" y="46" text-anchor="middle"
                style="font-size:15px;font-weight:800;fill:#111;">{pct:.0f}%</text>
          <text x="17" y="74" text-anchor="middle"
                style="font-size:10px;fill:#6c757d;">0</text>
          <text x="103" y="74" text-anchor="middle"
                style="font-size:10px;fill:#6c757d;">100</text>
        </svg>
        """

    criterio_cards = []

    for code in ISO22301_BLOCK_ORDER:
        if code not in resumen:
            continue

        d = resumen.get(code, {}) or {}

        pct = float(d.get("pct", 0) or 0)
        total = int(d.get("total", 0) or 0)
        aplicables = int(d.get("validas", 0) or 0)
        no_aplica = int(d.get("NA", 0) or 0)
        nombre_criterio = (d.get("nombre") or iso22301_block_title(code) or code).strip()

        nivel_data = (
            iso22301_nivel_visual_por_pct(pct)
            if aplicables > 0
            else {"nivel": "No aplica", "score": 0, "color": "#6c757d"}
        )
        nivel_score = nivel_data.get("score", "")
        nivel_texto = (nivel_data.get("nivel") or "").strip()
        nivel_nombre = nivel_texto.split(":", 1)[1].strip() if ":" in nivel_texto else nivel_texto

        gauge_html = gauge_svg_categoria(pct, nivel_data.get("color", "#2f6fb6"))

        criterio_cards.append(f"""
        <div class="col-12 col-md-6 col-xl-4">
          <div class="nistdet-subcard h-100">

            <div class="nistdet-subcard-top">
              <div class="text-center">
                {gauge_html}
              </div>
            </div>

            <div class="nistdet-subcard-body">
              <div class="nistdet-row">
                <div class="nistdet-label">Criterio</div>
                <div class="nistdet-value fw-bold">{escape(code)}</div>
              </div>

              <div class="nistdet-row">
                <div class="nistdet-label">Nombre</div>
                <div class="nistdet-value nistdet-value-wrap">{escape(nombre_criterio)}</div>
              </div>

              <div class="nistdet-row">
                <div class="nistdet-label">% Cumplimiento</div>
                <div class="nistdet-value fw-bold">{pct:.2f}%</div>
              </div>

              <div class="nistdet-row">
                <div class="nistdet-label">Nivel de Madurez</div>
                <div class="nistdet-value">
                  <div class="d-flex align-items-center gap-2 flex-wrap mb-1">
                    <span class="nivel-dot"
                          style="background-color:{nivel_data.get('color','#6c757d')} !important;"></span>
                    <span class="fw-bold">Nivel {nivel_score}</span>
                  </div>
                  <div class="text-muted small nistdet-value-wrap">
                    {escape(nivel_nombre)}
                  </div>
                </div>
              </div>

              <div class="nistdet-row">
                <div class="nistdet-label">Ítems aplicables</div>
                <div class="nistdet-value fw-bold">{aplicables}</div>
              </div>

              <div class="nistdet-row">
                <div class="nistdet-label">N/A excluidos</div>
                <div class="nistdet-value fw-bold">{no_aplica} de {total}</div>
              </div>

              <div class="nistdet-row nistdet-row-actions">
                <div class="nistdet-label">Acciones</div>
                <div class="nistdet-value">
                  <div class="d-flex flex-wrap gap-2">
                    <a class="btn btn-sm btn-outline-primary rounded-pill"
                       href="{url_for('madurez_iso22301.detalle_criterio', run_id=run.id, bloque_codigo=code)}">
                      <i class="bi bi-list-check me-1"></i>Ver preguntas
                    </a>

                    <a class="btn btn-sm btn-outline-dark rounded-pill"
                       href="{url_for('madurez_iso22301.analisis_criterio', run_id=run.id, bloque_codigo=code)}">
                      <i class="bi bi-cpu me-1"></i>Análisis
                    </a>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
        """)

    capitulo_cards = f"""
    <div class="nistdet-card p-4 mb-4">
      <div class="d-flex justify-content-between align-items-start flex-wrap gap-3 mb-3">
        <div>
          <div class="nistdet-section-title">ISO 22301 — Trust Services Criteria</div>
          <div class="text-muted small">
            Resultado detallado por criterios ISO 22301.
          </div>
        </div>

        <div class="nistdet-capitulo-resumen">
          <div class="d-flex align-items-center gap-2 flex-wrap justify-content-end">
            <span class="badge rounded-pill px-3 py-2"
                  style="background:{nivel_general.get('color','#6c757d')}; color:#fff;">
              Nivel {nivel_general.get('score', 0)}
            </span>
            <span class="fw-bold text-dark">{run.pct_general:.2f}%</span>
          </div>
          <div class="small text-muted text-end mt-1">
            {escape(nivel_general_nombre)}
          </div>
        </div>
      </div>

      <div class="row g-3">
        {''.join(criterio_cards)}
      </div>
    </div>
    """

    content = f"""
    <div class="nistdet-shell">

      <div class="nistdet-header-card">
        <div class="nistdet-header-overlay">
          <div class="nistdet-header-text">
            <h3 class="nistdet-title m-0">Resultado de Madurez — ISO 22301</h3>
            <div class="nistdet-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
              · Cumplimiento general: <b>{run.pct_general:.2f}%</b>
              · Nivel general: <b>{escape(nivel_general_nombre)}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="nistdet-header-actions">
        <a href="{url_for('madurez_iso22301.historial')}"
           class="btn nistdet-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al historial
        </a>

        <a href="{url_for('madurez_iso22301.inicio_iso22301')}"
           class="btn nistdet-btn-soft rounded-pill px-4 fw-bold">
          <i class="bi bi-house-door-fill me-2"></i>Volver al módulo
        </a>

        {pdf_btn}
      </div>

      {top_html}

      {capitulo_cards}

    </div>

    {iso22301_nist_css('nistdet', '📊')}
    """
    return render_template_string(BASE, title="Detalle ISO 22301", content=content)


# Alias por compatibilidad si tu menú anterior apuntaba a resultado
@iso22301_madurez_bp.route("/resultado/<int:run_id>", methods=["GET"])
@login_required
def resultado(run_id: int):
    return detalle(run_id)

# ============================================================
# ISO 22301 — PROMPT INFORME EJECUTIVO IA
# ============================================================

def _iso22301_prompt_informe_ejecutivo(run: "Iso22301MadurezRun", resumen: dict) -> str:
    """
    Prompt para generar informe ejecutivo ISO 22301.
    Lo usa informe_ejecutivo_generar().
    """

    lineas = []

    for code in ISO22301_BLOCK_ORDER:
        d = (resumen or {}).get(code)
        if not d:
            continue

        lineas.append(
            f"- {d.get('nombre') or iso22301_block_title(code) or code}: "
            f"{float(d.get('pct', 0) or 0):.2f}% | "
            f"Nivel: {d.get('madurez') or ''} | "
            f"SI: {d.get('SI', 0)} | "
            f"Parcial: {d.get('PARCIAL', 0)} | "
            f"NO: {d.get('NO', 0)} | "
            f"N/A: {d.get('NA', 0)} | "
            f"Total: {d.get('total', 0)}"
        )

    criterios_txt = "\n".join(lineas) if lineas else "Sin resultados consolidados."

    return f"""
Eres un consultor senior experto en ISO 22301, auditoría de controles, gobierno de seguridad de la información y Trust Services Criteria.

Genera un informe ejecutivo profesional para alta dirección.

DATOS DE LA EVALUACIÓN
Consecutivo: {run.consecutivo}
Cumplimiento general: {float(run.pct_general or 0):.2f}%

RESULTADOS POR CRITERIO
{criterios_txt}

RESPONDE ÚNICAMENTE JSON VÁLIDO.
No uses markdown.
No agregues texto antes ni después del JSON.

Formato exacto:
{{
  "informe_ejecutivo": "texto"
}}

REGLAS:
- El informe debe tener entre 5 y 8 párrafos.
- No repitas el título "Informe Ejecutivo".
- Explica el estado general de madurez ISO 22301.
- Menciona fortalezas principales.
- Menciona brechas o criterios con menor cumplimiento.
- Explica riesgos ejecutivos asociados.
- Incluye recomendaciones estratégicas.
- No inventes datos que no estén en los resultados.
- Redacción clara, ejecutiva y consultiva.
""".strip()

# ============================================================
# IA — INFORME / PLAN
# ============================================================

@iso22301_madurez_bp.route("/detalle/<int:run_id>/informe-ejecutivo/generar", methods=["POST"])
@login_required
def informe_ejecutivo_generar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("El perfil Auditor no puede generar el informe ejecutivo con IA.")

    run_analysis_from_iso22301_run(run_id)
    run = Iso22301MadurezRun.query.get_or_404(run_id)

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    if not resumen:
        flash("⚠️ No hay resultados consolidados para generar el informe ejecutivo.", "warning")
        return redirect(url_for("madurez_iso22301.detalle", run_id=run.id))

    try:
        prompt_informe = _iso22301_prompt_informe_ejecutivo(run, resumen)
        raw = _iso22301_ai_text(prompt_informe, max_tokens=1800)
        informe_ai = _iso22301_extraer_informe_ai(raw)

        # Un segundo intento solo se realiza cuando la respuesta existe pero
        # no contiene texto utilizable. Evita que una variación de formato
        # obligue al usuario a iniciar nuevamente la generación.
        if not informe_ai:
            prompt_reintento = f"""
{prompt_informe}

CORRECCIÓN DE FORMATO OBLIGATORIA:
La respuesta anterior no contenía texto utilizable. Devuelve un único objeto
JSON con la clave exacta \"informe_ejecutivo\" y un valor de texto no vacío.
""".strip()
            raw = _iso22301_ai_text(prompt_reintento, max_tokens=1800)
            informe_ai = _iso22301_extraer_informe_ai(raw)

        if not informe_ai:
            raise RuntimeError(
                "La IA respondió sin contenido utilizable después de dos intentos. "
                "Verifique el modelo configurado e intente nuevamente."
            )

        run.informe_ejecutivo_ai = informe_ai
        run.informe_ejecutivo_editado = informe_ai
        run.updated_at = datetime.utcnow()

        db.session.add(run)
        db.session.commit()

        flash("✅ Informe ejecutivo ISO 22301 generado con IA.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error llamando IA para el informe ejecutivo: {e}", "danger")

    return redirect(url_for("madurez_iso22301.detalle", run_id=run.id))


@iso22301_madurez_bp.route("/detalle/<int:run_id>/informe-ejecutivo/editar", methods=["GET", "POST"])
@login_required
def informe_ejecutivo_editar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("El perfil Auditor no puede editar el informe ejecutivo.")

    run = Iso22301MadurezRun.query.get_or_404(run_id)

    if request.method == "POST":
        texto_form = request.form.get("informe") or ""
        texto_limpio = iso22301_normalizar_texto_rico_guardado(texto_form)

        run.informe_ejecutivo_editado = texto_limpio
        run.updated_at = datetime.utcnow()

        db.session.add(run)
        db.session.commit()

        flash("✅ Informe ejecutivo ISO 22301 actualizado.", "success")
        return redirect(url_for("madurez_iso22301.detalle", run_id=run.id))

    texto = run.informe_ejecutivo_editado or run.informe_ejecutivo_ai or ""
    texto = iso22301_normalizar_texto_rico_guardado(texto)

    # Limpia en base de datos si venía guardado como JSON literal
    if texto and texto != (run.informe_ejecutivo_editado or run.informe_ejecutivo_ai or ""):
        run.informe_ejecutivo_editado = texto
        db.session.add(run)
        db.session.commit()

    content = f"""
<div class="nistdet-shell">
  <div class="nistdet-header-card">
    <div class="nistdet-header-overlay">
      <div class="nistdet-header-text">
        <h3 class="nistdet-title m-0">Editar Informe Ejecutivo — ISO 22301</h3>
      </div>
    </div>
  </div>

  <form method="POST" class="nistdet-card p-4">
    <textarea name="informe" rows="18" class="form-control">{escape(texto)}</textarea>

    <div class="text-end mt-3">
      <a href="{url_for('madurez_iso22301.detalle', run_id=run.id)}"
         class="btn btn-secondary rounded-pill px-4">
        Cancelar
      </a>

      <button class="btn btn-primary rounded-pill px-4 fw-bold">
        Guardar
      </button>
    </div>
  </form>
</div>
{iso22301_nist_css('nistdet', '✍️')}
"""
    return render_template_string(BASE, title="Editar Informe Ejecutivo ISO 22301", content=content)


@iso22301_madurez_bp.route("/detalle/<int:run_id>/plan-trabajo/generar", methods=["POST"])
@login_required
def plan_trabajo_generar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("El perfil Auditor no puede generar el plan de trabajo con IA.")

    run = Iso22301MadurezRun.query.get_or_404(run_id)
    resumen = json.loads(run.resumen_json or "{}")

    try:
        raw = _iso22301_ai_text(_iso22301_prompt_plan_trabajo(run, resumen), max_tokens=1600)
        obj = _extraer_json_objeto_iso22301(raw)
        plan = obj.get("plan_trabajo") if isinstance(obj, dict) else None
        plan_txt = _build_plan_accion_iso22301_texto(plan) if isinstance(plan, list) else raw
        plan_txt = iso22301_normalizar_texto_rico_guardado(plan_txt)

        if not plan_txt:
            raise RuntimeError("La IA no devolvió un plan válido.")

        run.plan_trabajo_ai = plan_txt
        run.plan_trabajo_editado = plan_txt
        db.session.commit()

        flash("✅ Plan de trabajo ISO 22301 generado con IA.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error generando plan de trabajo: {e}", "danger")

    return redirect(url_for("madurez_iso22301.detalle", run_id=run.id))


@iso22301_madurez_bp.route("/detalle/<int:run_id>/plan-trabajo/editar", methods=["GET", "POST"])
@login_required
def plan_trabajo_editar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("El perfil Auditor no puede editar el plan de trabajo.")

    run = Iso22301MadurezRun.query.get_or_404(run_id)

    if request.method == "POST":
        run.plan_trabajo_editado = (request.form.get("plan") or "").strip()
        db.session.commit()
        flash("✅ Plan de trabajo ISO 22301 actualizado.", "success")
        return redirect(url_for("madurez_iso22301.detalle", run_id=run.id))

    texto = run.plan_trabajo_editado or run.plan_trabajo_ai or ""

    content = f"""
<div class="nistdet-shell">
  <div class="nistdet-header-card">
    <div class="nistdet-header-overlay">
      <div class="nistdet-header-text">
        <h3 class="nistdet-title m-0">Editar Plan de Trabajo — ISO 22301</h3>
      </div>
    </div>
  </div>

  <form method="POST" class="nistdet-card p-4">
    <textarea name="plan" rows="18" class="form-control">{escape(texto)}</textarea>
    <div class="text-end mt-3">
      <a href="{url_for('madurez_iso22301.detalle', run_id=run.id)}" class="btn btn-secondary rounded-pill px-4">Cancelar</a>
      <button class="btn btn-success rounded-pill px-4 fw-bold">Guardar</button>
    </div>
  </form>
</div>
{iso22301_nist_css('nistdet', '✍️')}
"""
    return render_template_string(BASE, title="Editar Plan ISO 22301", content=content)

# ============================================================
# PDF EJECUTIVO ISO 22301
# ============================================================

def _iso22301_build_pdf_run(run: "Iso22301MadurezRun") -> io.BytesIO:
    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    labels, values = iso22301_pct_por_criterio(resumen, ISO22301_BLOCK_ORDER)
    radar_b64 = run.radar_overall_b64 or iso22301_radar_b64(
        labels,
        values,
        title="Radar por Capítulo - ISO 22301"
    )

    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
        title="ISO 22301 - Informe Ejecutivo"
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ISO22301_Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="ISO22301_Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#1d4f8f"),
        spaceBefore=10,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="ISO22301_Normal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#101827"),
        spaceAfter=5
    ))

    styles.add(ParagraphStyle(
        name="ISO22301_Small",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#374151"),
        spaceAfter=4
    ))

    def pdf_escape(v):
        return html.escape(str(v or ""))

    story = []

    title_tbl = Table(
        [[Paragraph("ISO 22301 - Informe de Madurez", styles["ISO22301_Title"])]],
        colWidths=[26.8 * cm]
    )
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#3f86d6")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#1d4f8f")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 8))

    nivel_general = iso22301_resolver_nivel(run.pct_general)

    resumen_tbl = Table([
        ["Consecutivo", pdf_escape(run.consecutivo)],
        ["Fecha", run.created_at.strftime("%Y-%m-%d %H:%M") if run.created_at else ""],
        ["Cumplimiento general", f"{float(run.pct_general or 0):.2f}% - {pdf_escape(nivel_general.get('nivel',''))}"],
    ], colWidths=[5.2 * cm, 21.6 * cm])

    resumen_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f1fb")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1d4f8f")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8e3")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(resumen_tbl)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Informe Ejecutivo", styles["ISO22301_Section"]))

    informe = iso22301_normalizar_texto_rico_guardado(
        run.informe_ejecutivo_editado or run.informe_ejecutivo_ai or ""
    )

    if informe:
        for parrafo in re.split(r"\n\s*\n", informe):
            if parrafo.strip():
                story.append(Paragraph(pdf_escape(parrafo.strip()), styles["ISO22301_Normal"]))
    else:
        story.append(Paragraph("No hay informe ejecutivo registrado.", styles["ISO22301_Normal"]))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Radar por Capítulo ISO 22301", styles["ISO22301_Section"]))

    if radar_b64:
        try:
            img = RLImage(
                io.BytesIO(base64.b64decode(radar_b64)),
                width=11.5 * cm,
                height=11.0 * cm
            )
            story.append(img)
        except Exception:
            story.append(Paragraph("No fue posible insertar el radar.", styles["ISO22301_Normal"]))

    story.append(Paragraph("Detalle por Criterio", styles["ISO22301_Section"]))

    data = [[
        "Criterio",
        "% Cumplimiento",
        "Nivel",
        "SI",
        "Parcial",
        "NO",
        "N/A",
        "Ítems aplicables"
    ]]

    for code in ISO22301_BLOCK_ORDER:
        d = resumen.get(code)
        if not d:
            continue

        data.append([
            Paragraph(pdf_escape(d.get("nombre") or code), styles["ISO22301_Small"]),
            Paragraph(f"{float(d.get('pct', 0) or 0):.2f}%", styles["ISO22301_Small"]),
            Paragraph(pdf_escape(d.get("madurez") or ""), styles["ISO22301_Small"]),
            str(d.get("SI", 0)),
            str(d.get("PARCIAL", 0)),
            str(d.get("NO", 0)),
            str(d.get("NA", 0)),
            str(d.get("validas", 0)),
        ])

    tbl = Table(
        data,
        colWidths=[
            7.2 * cm,
            3.0 * cm,
            5.0 * cm,
            1.5 * cm,
            2.0 * cm,
            1.5 * cm,
            1.5 * cm,
            2.0 * cm
        ],
        repeatRows=1
    )

    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3f86d6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8e3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.append(tbl)

    plan = _normalizar_plan_accion_iso22301_texto(
        run.plan_trabajo_editado or run.plan_trabajo_ai or ""
    )

    if plan:
        story.append(PageBreak())
        story.append(Paragraph("Plan de Trabajo", styles["ISO22301_Section"]))

        for parrafo in re.split(r"\n\s*\n", plan):
            if parrafo.strip():
                story.append(Paragraph(pdf_escape(parrafo.strip()), styles["ISO22301_Normal"]))

    doc.build(story)
    buf.seek(0)
    return buf

# ============================================================
# EXPORTAR PDF — ADMIN / USUARIO CON PERMISO / AUDITOR
# ============================================================

@iso22301_madurez_bp.route("/detalle/<int:run_id>/pdf", methods=["GET"])
@login_required
def exportar_pdf(run_id: int):
    user = User.query.get(session.get("user_id"))

    # ✅ Auditor también puede exportar/imprimir PDF
    denied = iso22301_check_access_or_redirect(
        user,
        "No tiene permiso para exportar PDF ISO 22301."
    )
    if denied:
        return denied

    # Garantiza que el PDF use la fórmula vigente incluso si la revisión
    # fue creada antes de excluir N/A del denominador.
    run_analysis_from_iso22301_run(run_id)
    run = Iso22301MadurezRun.query.get_or_404(run_id)

    pdf = _iso22301_build_pdf_run(run)

    filename = f"ISO22301_Madurez_{re.sub(r'[^A-Za-z0-9_-]+', '_', run.consecutivo or str(run.id))}.pdf"

    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )


# ============================================================
# ELIMINAR — AUDITOR NO PUEDE
# ============================================================

@iso22301_madurez_bp.route("/detalle/<int:run_id>/eliminar", methods=["POST"])
@login_required
def eliminar_run(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("El perfil Auditor no puede eliminar revisiones ISO 22301.")

    run = Iso22301MadurezRun.query.get_or_404(run_id)

    try:
        Iso22301MadurezCriterioAnalisis.query.filter_by(run_id=run.id).delete(synchronize_session=False)
        Iso22301MadurezRespuesta.query.filter_by(run_id=run.id).delete(synchronize_session=False)
        db.session.delete(run)
        db.session.commit()
        flash("✅ Revisión ISO 22301 eliminada correctamente.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error eliminando revisión ISO 22301: {e}", "danger")

    return redirect(url_for("madurez_iso22301.historial"))


# ============================================================
# CSS — COPIA DE PATRÓN NIST
# ============================================================
def iso22301_nist_css(prefix, icon, subtitle_label="ISO 22301"):
    return f"""
<style>
  body{{
    background-image:url('/static/img/ccsgsi.jpg');
    background-size:cover;
    background-position:center;
    background-attachment:fixed;
    background-repeat:no-repeat;
  }}

  .{prefix}-shell{{
    width:96%;
    max-width:1600px;
    margin:26px auto 24px auto;
  }}

  .{prefix}-header-card{{
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

  .{prefix}-header-card::before{{
    content:"";
    position:absolute;
    inset:0;
    background:
      radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
      repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
    pointer-events:none;
  }}

  .{prefix}-header-overlay{{
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

  .{prefix}-header-overlay::before{{
    content:"{icon}";
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

  .{prefix}-header-text{{
    max-width:1100px;
    width:100%;
    display:block !important;
    transform:none !important;
  }}

  .{prefix}-header-text::before{{
    content:"SGSI · {subtitle_label}";
    display:inline-block;
    background:rgba(255,255,255,.18);
    border-radius:999px;
    padding:3px 10px;
    font-size:.65rem;
    font-weight:800;
    margin-bottom:4px;
    color:#ffffff;
  }}

  .{prefix}-title{{
    color:#ffffff !important;
    font-weight:950;
    font-size:1.32rem;
    line-height:1.1;
    text-shadow:0 3px 10px rgba(0,0,0,.35);
    margin:0 !important;
  }}

  .{prefix}-subtitle{{
    color:rgba(255,255,255,.95);
    font-size:.78rem;
    margin-top:4px;
    line-height:1.25;
    font-weight:800;
  }}

  .{prefix}-header-actions{{
    display:flex;
    justify-content:center;
    align-items:center;
    flex-wrap:wrap;
    gap:10px;
    margin:10px 0 14px;
  }}

  .{prefix}-header-actions .btn,
  .{prefix}-btn-main,
  .{prefix}-btn-primary,
  .{prefix}-btn-soft,
  .btn{{
    border-radius:10px !important;
    min-height:32px;
    padding:8px 22px !important;
    font-size:.82rem;
    font-weight:900;
    box-shadow:0 8px 16px rgba(15,23,42,.15);
  }}

  .{prefix}-btn-main,
  .{prefix}-btn-primary{{
    background:#0b4a8f !important;
    border:1px solid #0b4a8f !important;
    color:#ffffff !important;
  }}

  .{prefix}-btn-main:hover,
  .{prefix}-btn-primary:hover{{
    background:#0f4f94 !important;
    color:#ffffff !important;
  }}

  .{prefix}-btn-soft{{
    background:#ffffff !important;
    border:1px solid #cfd8e3 !important;
    color:#0f172a !important;
  }}

  .{prefix}-btn-soft:hover{{
    background:#edf5ff !important;
    color:#0b65d8 !important;
  }}

  .{prefix}-card,
  .card{{
    background:rgba(255,255,255,.96) !important;
    border-radius:18px !important;
    backdrop-filter:blur(8px);
    box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
    border:1px solid rgba(219,230,244,.9) !important;
    overflow:hidden;
  }}

  .{prefix}-section-title,
  .card h5,
  .card h6{{
    font-weight:950;
    font-size:.95rem;
    color:#0b4a8f;
    margin:8px 0 14px 0;
    padding-bottom:8px;
    border-bottom:2px solid rgba(59,130,246,.18);
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

  @media(max-width:991.98px){{
    .{prefix}-shell{{
      width:98%;
      margin:8px auto 22px auto;
    }}

    .{prefix}-header-card{{
      min-height:88px;
    }}

    .{prefix}-title{{
      font-size:1.20rem;
    }}

    .{prefix}-subtitle{{
      font-size:.68rem;
    }}
  }}

  @media(max-width:768px){{
    .{prefix}-header-overlay{{
      flex-direction:column;
      text-align:center;
      gap:10px;
    }}

    .{prefix}-header-overlay::before{{
      margin:0;
    }}

    .{prefix}-header-text::before{{
      margin-left:auto;
      margin-right:auto;
    }}

    .{prefix}-title,
    .{prefix}-subtitle{{
      text-align:center;
    }}

    .{prefix}-header-actions .btn{{
      width:100%;
    }}
  }}
</style>
"""


def iso22301_nistform_css():
    return """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .nistform-shell{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }

      .nistform-header-card{
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

      .nistform-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .nistform-header-overlay{
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

      .nistform-header-overlay::before{
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
      }

      .nistform-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .nistform-header-text::before{
        content:"SGSI · Evaluación ISO 22301";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .nistform-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .nistform-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        font-weight:800;
      }

      .nistform-header-actions{
        display:flex;
        justify-content:center;
        align-items:center;
        flex-wrap:wrap;
        gap:10px;
        margin:10px 0 14px;
      }

      .nistform-header-actions .btn,
      .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .nistform-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .nistform-section-title,
      .card h5,
      .card h6{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin:8px 0 14px 0;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }

      .nistform-progress{
        height:24px;
        border-radius:999px;
        background:#dbe6f4;
        overflow:hidden;
        box-shadow:inset 0 2px 6px rgba(0,0,0,.12);
      }

      .nistform-progress .progress-bar{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1);
        font-weight:900;
      }

      .nistform-accordion{
        display:flex;
        flex-direction:column;
        gap:12px;
      }

      .nistform-acc-item{
        border:1px solid #dbe6f4;
        border-radius:18px!important;
        overflow:hidden;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .nistform-acc-item .accordion-button{
        background:linear-gradient(135deg,#eef6ff,#ffffff);
        color:#101827;
        font-weight:900;
        box-shadow:none;
        padding:16px 18px;
      }

      .nistform-acc-item .accordion-button:not(.collapsed){
        background:linear-gradient(135deg,#dceeff,#ffffff);
        color:#0b4a8f;
      }

      .nistform-acc-inner{
        width:100%;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:14px;
      }

      .nistform-func-title{
        font-size:1.02rem;
        font-weight:950;
        color:#0b4a8f;
      }

      .nistform-func-subtitle{
        font-size:.78rem;
        color:#607086;
        font-weight:700;
        margin-top:2px;
      }

      .nistform-acc-body{
        background:#f8fbff;
        padding:16px;
      }

      .nistform-cat-block{
        background:rgba(255,255,255,.88);
        border:1px solid rgba(15,23,42,.08);
        border-radius:18px;
        padding:8px 7px;
        margin-bottom:14px;
      }

      .nistform-cat-title{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
        margin-bottom:14px;
        color:#0b4a8f;
        font-weight:950;
      }

      .nistform-cat-title small{
        color:#607086;
        font-weight:700;
      }

      .nistform-qcard{
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:16px;
        box-shadow:0 8px 18px rgba(15,23,42,.06);
      }

      .nistform-qhead{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        margin-bottom:10px;
      }

      .nistform-qtext{
        color:#0b1220;
        font-weight:800;
        line-height:1.35;
        min-height:76px;
      }

      .nistform-radio-row{
        display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:6px;
        margin-top:14px;
      }

      .nistform-radio-card{
        display:flex;
        align-items:center;
        justify-content:center;
        gap:7px;
        border:1px solid #d7e0ec;
        background:#ffffff;
        color:#101827;
        border-radius:999px;
        padding:8px 10px;
        font-weight:900;
        font-size:.78rem;
        cursor:pointer;
        transition:all .18s ease;
        min-height:40px;
        user-select:none;
      }

      .nistform-radio-card input{
        accent-color:#0b4a8f;
      }

      .nistform-radio-card:hover{
        transform:translateY(-1px);
        box-shadow:0 8px 16px rgba(15,23,42,.10);
      }

      .nistform-radio-card:has(input[value="NA"]:checked){
        background:#e2e3e5;
        border-color:#6c757d;
        color:#41464b;
      }

      .nistform-radio-card:has(input[value="SI"]:checked){
        background:#d1e7dd;
        border-color:#198754;
        color:#0f5132;
      }

      .nistform-radio-card:has(input[value="PARCIAL"]:checked){
        background:#fff3cd;
        border-color:#ffc107;
        color:#664d03;
      }

      .nistform-radio-card:has(input[value="NO"]:checked){
        background:#f8d7da;
        border-color:#dc3545;
        color:#842029;
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

      @media(max-width:991.98px){
        .nistform-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .nistform-header-card{
          min-height:88px;
        }

        .nistform-title{
          font-size:1.20rem;
        }

        .nistform-subtitle{
          font-size:.68rem;
        }

        .nistform-card{
          padding:14px!important;
        }
      }

      @media(max-width:768px){
        .nistform-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .nistform-header-overlay::before{
          margin:0;
        }

        .nistform-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .nistform-title,
        .nistform-subtitle{
          text-align:center;
        }

        .nistform-header-actions .btn{
          width:100%;
        }

        .nistform-acc-inner,
        .nistform-cat-title{
          flex-direction:column;
          align-items:flex-start;
        }

        .nistform-radio-row{
          grid-template-columns:1fr;
        }
      }
    </style>
    """

# ==========================================================================================================================================
#                                                   Fin Módulo de Madurez ISO 22301 — Diseño NIST
# ============================================================================================================================================

# ============================================================================================================================================
#                       MÓDULO NIVEL DE MADUREZ — GESTIÓN DE INTELIGENCIA ARTIFICIAL ISO 42001
# ============================================================================================================================================

ai_madurez_bp = Blueprint("madurez_ai", __name__, url_prefix="/madurez-ai")

AI_MADUREZ_PERMISO = "Nivel de Madurez Gestión de Inteligencia Artificial"
AI_MADUREZ_DB_PATH = os.path.join(app.instance_path, "ai_madurez_42001.db")
AI_INSTRUMENTO_DEFAULT = os.path.join(app.root_path, "static", "templates", "Instrumento ISO 42001 ES.xlsx")

AI_STATUS_SCORE = {
    "SI": 1.0,
    "PARCIAL": 0.5,
    "NO": 0.0,
    "NA": None,
}

AI_MADUREZ_LEVELS = [
    {
        "nivel": "Nivel 1: Ejecutado (Performed)",
        "descripcion": "La organización ejecuta prácticas de gestión de IA de forma básica, reactiva o ad hoc.",
        "score": 1,
        "rango_pct": "0% – 20%",
        "logica": "Prácticas ad hoc",
    },
    {
        "nivel": "Nivel 2: Documentado (Documented)",
        "descripcion": "La organización cuenta con prácticas documentadas para gestionar riesgos, responsabilidades y controles de IA.",
        "score": 2,
        "rango_pct": "21% – 40%",
        "logica": "Existe documentación",
    },
    {
        "nivel": "Nivel 3: Gestionado (Managed)",
        "descripcion": "La organización gestiona formalmente el sistema de gestión de IA, asigna responsables y revisa cumplimiento.",
        "score": 3,
        "rango_pct": "41% – 60%",
        "logica": "Se gestiona cumplimiento",
    },
    {
        "nivel": "Nivel 4: Gestionado Cuantitativamente (Quantitatively Managed)",
        "descripcion": "La organización mide la efectividad, monitorea resultados y reporta periódicamente el desempeño del sistema de IA.",
        "score": 4,
        "rango_pct": "61% – 80%",
        "logica": "Se mide efectividad",
    },
    {
        "nivel": "Nivel 5: Optimizado (Optimizing)",
        "descripcion": "La organización mejora continuamente el sistema de gestión de IA y optimiza sus procesos de gobierno, riesgo y control.",
        "score": 5,
        "rango_pct": "81% – 100%",
        "logica": "Mejora continua institucionalizada",
    },
]

AI_CAP_ORDER_DEFAULT = [
    "Contexto de la Organización",
    "Liderazgo",
    "Planificación",
    "Soporte",
    "Operación",
    "Evaluación del Desempeño",
    "Mejora",
    "Anexo A",
    "Gobierno",
    "Riesgo",
    "Datos",
    "Transparencia",
    "Seguridad",
]

# ============================================================
# CATÁLOGO DE EVALUACIÓN DE RIESGOS DE IA — NIST AI RMF
# Fuente operativa: checklist suministrado por el usuario.
# La clasificación NIST usa las funciones GOVERN, MAP,
# MEASURE y MANAGE del AI RMF.
# ============================================================

AI_RISK_PHASES = [
    {
        "codigo": "F1",
        "nombre": "Fase 1: Concepción y Definición",
        "descripcion": "Definición del propósito, contexto, clasificación e impactos potenciales del sistema de IA.",
        "foco_nist": "MAP / GOVERN",
    },
    {
        "codigo": "F2",
        "nombre": "Fase 2: Gobernanza de Datos",
        "descripcion": "Licitud, calidad, representatividad, minimización y trazabilidad de los datos.",
        "foco_nist": "GOVERN / MAP / MEASURE",
    },
    {
        "codigo": "F3",
        "nombre": "Fase 3: Desarrollo y Entrenamiento",
        "descripcion": "Diseño seguro, documentación, explicabilidad, robustez y dependencias técnicas.",
        "foco_nist": "MAP / MEASURE",
    },
    {
        "codigo": "F4",
        "nombre": "Fase 4: Validación y Pruebas",
        "descripcion": "Medición independiente del rendimiento, la robustez, la equidad y la supervisión humana.",
        "foco_nist": "MEASURE / GOVERN",
    },
    {
        "codigo": "F5",
        "nombre": "Fase 5: Despliegue y Operación",
        "descripcion": "Monitoreo continuo, deriva, incidentes, contingencia y tratamiento del riesgo.",
        "foco_nist": "MEASURE / MANAGE",
    },
]

AI_RISK_FUNCTIONS = {
    "GOVERN": {
        "nombre": "GOVERN — Gobernar",
        "descripcion": "Políticas, responsabilidades, cultura y supervisión para gestionar los riesgos de IA.",
        "color": "#6f42c1",
    },
    "MAP": {
        "nombre": "MAP — Mapear",
        "descripcion": "Contexto, propósito, partes interesadas, impactos y riesgos del sistema de IA.",
        "color": "#0d6efd",
    },
    "MEASURE": {
        "nombre": "MEASURE — Medir",
        "descripcion": "Métodos, métricas, pruebas y seguimiento de riesgos y características de confianza.",
        "color": "#fd7e14",
    },
    "MANAGE": {
        "nombre": "MANAGE — Gestionar",
        "descripcion": "Priorización, respuesta, tratamiento, seguimiento y comunicación del riesgo.",
        "color": "#198754",
    },
}

# codigo, fase_codigo, fase, funcion NIST, categoría NIST,
# título, pregunta, evidencia sugerida, orden
AI_RISK_QUESTION_CATALOG = [
    (
        "AIR-001", "F1", "Fase 1: Concepción y Definición", "MAP", "MAP-1",
        "Definición del propósito previsto",
        "¿Se ha documentado el uso específico y el propósito previsto del sistema de IA conforme a los requisitos aplicables, incluido el AI Act cuando corresponda?",
        "Ficha del caso de uso, declaración de propósito, alcance, usuarios previstos y usos excluidos.", 1
    ),
    (
        "AIR-002", "F1", "Fase 1: Concepción y Definición", "MAP", "MAP-1",
        "Clasificación de riesgo",
        "¿Se ha determinado y documentado si el sistema se clasifica como riesgo prohibido, alto, limitado o mínimo?",
        "Matriz de clasificación regulatoria, concepto jurídico y aprobación del comité de IA.", 2
    ),
    (
        "AIR-003", "F1", "Fase 1: Concepción y Definición", "GOVERN", "GOVERN-1",
        "Evaluación de impacto",
        "¿Se ha realizado una evaluación de impacto sobre protección de datos (DPIA) conforme al RGPD o a la regulación de privacidad aplicable?",
        "DPIA, evaluación de impacto algorítmico, concepto de privacidad y plan de tratamiento.", 3
    ),
    (
        "AIR-004", "F1", "Fase 1: Concepción y Definición", "MAP", "MAP-3",
        "Análisis de partes interesadas",
        "¿Se han identificado los grupos y partes interesadas potencialmente afectados por las decisiones del sistema?",
        "Mapa de partes interesadas, perfiles afectados y registro de consultas.", 4
    ),
    (
        "AIR-005", "F1", "Fase 1: Concepción y Definición", "MAP", "MAP-5",
        "Viabilidad ética",
        "¿Se han evaluado los posibles impactos negativos en la equidad, los derechos fundamentales y la no discriminación?",
        "Evaluación ética, análisis de impacto en derechos fundamentales y criterios de aceptación.", 5
    ),
    (
        "AIR-006", "F2", "Fase 2: Gobernanza de Datos", "GOVERN", "GOVERN-1",
        "Licitud y procedencia",
        "¿Se ha verificado la base legal y la procedencia autorizada de los datos utilizados para entrenamiento, validación y operación?",
        "Inventario de fuentes, bases legales, licencias, consentimientos y contratos de datos.", 6
    ),
    (
        "AIR-007", "F2", "Fase 2: Gobernanza de Datos", "MEASURE", "MEASURE-2",
        "Representatividad",
        "¿Se han realizado pruebas para asegurar que los datos no introducen sesgos estadísticos significativos?",
        "Informe de representatividad, métricas de sesgo y resultados por subgrupos.", 7
    ),
    (
        "AIR-008", "F2", "Fase 2: Gobernanza de Datos", "MAP", "MAP-2",
        "Minimización",
        "¿Se han aplicado técnicas de anonimización, seudonimización o minimización para limitar los datos personales al mínimo necesario?",
        "Diseño de minimización, evidencia de anonimización y diccionario de datos.", 8
    ),
    (
        "AIR-009", "F2", "Fase 2: Gobernanza de Datos", "GOVERN", "GOVERN-1",
        "Linaje de datos",
        "¿Existe un registro completo del origen y de las transformaciones aplicadas a los conjuntos de datos?",
        "Registro de linaje, versionado de datasets, procesos ETL y responsables de custodia.", 9
    ),
    (
        "AIR-010", "F2", "Fase 2: Gobernanza de Datos", "MEASURE", "MEASURE-2",
        "Calidad técnica",
        "¿Se han auditado los datos para detectar valores atípicos (outliers), datos incompletos, inconsistentes o corruptos?",
        "Informe de calidad, reglas de validación, métricas y registros de corrección.", 10
    ),
    (
        "AIR-011", "F3", "Fase 3: Desarrollo y Entrenamiento", "MAP", "MAP-2",
        "Selección de algoritmos",
        "¿Se ha justificado la elección del modelo considerando su interpretabilidad, robustez y adecuación al propósito previsto?",
        "Decisión de arquitectura, comparación de modelos y criterios técnicos de selección.", 11
    ),
    (
        "AIR-012", "F3", "Fase 3: Desarrollo y Entrenamiento", "GOVERN", "GOVERN-1",
        "Documentación técnica",
        "¿Se ha generado una ficha técnica (Model Card) que detalle las limitaciones, los datos, las métricas y el uso previsto del modelo?",
        "Model Card, Data Card, documentación de arquitectura y registro de limitaciones.", 12
    ),
    (
        "AIR-013", "F3", "Fase 3: Desarrollo y Entrenamiento", "MEASURE", "MEASURE-2",
        "Seguridad del entorno",
        "¿Se han implementado y probado controles para prevenir el envenenamiento de datos, la extracción del modelo y otros ataques contra la IA?",
        "Modelo de amenazas, pruebas de seguridad, controles de acceso y resultados de red teaming.", 13
    ),
    (
        "AIR-014", "F3", "Fase 3: Desarrollo y Entrenamiento", "MEASURE", "MEASURE-2",
        "Explicabilidad",
        "¿Se han integrado mecanismos y herramientas para interpretar y auditar las decisiones o resultados del modelo?",
        "Pruebas de explicabilidad, documentación de métodos XAI y ejemplos de explicaciones.", 14
    ),
    (
        "AIR-015", "F3", "Fase 3: Desarrollo y Entrenamiento", "MAP", "MAP-4",
        "Gestión de dependencias",
        "¿Se han auditado las librerías, modelos y componentes de terceros para reducir vulnerabilidades de cadena de suministro?",
        "SBOM/ML-BOM, inventario de dependencias, análisis de vulnerabilidades y licencias.", 15
    ),
    (
        "AIR-016", "F4", "Fase 4: Validación y Pruebas", "MEASURE", "MEASURE-1",
        "Métricas de rendimiento",
        "¿Se ha validado el modelo con conjuntos de datos independientes y métricas apropiadas para el contexto de uso?",
        "Plan de validación, test set independiente, métricas y umbrales de aceptación.", 16
    ),
    (
        "AIR-017", "F4", "Fase 4: Validación y Pruebas", "MEASURE", "MEASURE-2",
        "Pruebas de robustez",
        "¿Se ha sometido el modelo a ataques adversarios simulados y pruebas de robustez?",
        "Informe de pruebas adversariales, escenarios, resultados y remediaciones.", 17
    ),
    (
        "AIR-018", "F4", "Fase 4: Validación y Pruebas", "GOVERN", "GOVERN-3",
        "Supervisión humana",
        "¿Se han definido y probado mecanismos de intervención humana (human-in-the-loop) para casos críticos?",
        "Matriz de decisiones, procedimiento de escalamiento, roles y pruebas de intervención.", 18
    ),
    (
        "AIR-019", "F4", "Fase 4: Validación y Pruebas", "MEASURE", "MEASURE-2",
        "Validación de equidad",
        "¿Se ha analizado el impacto del modelo en diferentes subgrupos demográficos o poblaciones afectadas?",
        "Métricas de equidad, análisis por subgrupos y plan de mitigación de sesgos.", 19
    ),
    (
        "AIR-020", "F4", "Fase 4: Validación y Pruebas", "MEASURE", "MEASURE-2",
        "Pruebas de estrés",
        "¿Se ha evaluado y documentado el comportamiento del sistema ante entradas inesperadas, datos fuera de distribución o ruido?",
        "Casos de prueba, resultados de estrés, límites operativos y criterios de degradación segura.", 20
    ),
    (
        "AIR-021", "F5", "Fase 5: Despliegue y Operación", "GOVERN", "GOVERN-1",
        "Control de versiones",
        "¿Se garantiza la trazabilidad y reproducibilidad de los modelos, datos, parámetros y configuraciones desplegados?",
        "Registro de versiones, repositorios, artefactos de despliegue y procedimiento de reproducción.", 21
    ),
    (
        "AIR-022", "F5", "Fase 5: Despliegue y Operación", "MEASURE", "MEASURE-3",
        "Monitorización de deriva",
        "¿Existen métricas y alertas ante cambios en la distribución de los datos o el desempeño del modelo (data/model drift)?",
        "Tablero de monitoreo, umbrales, alertas y registros de deriva.", 22
    ),
    (
        "AIR-023", "F5", "Fase 5: Despliegue y Operación", "MEASURE", "MEASURE-4",
        "Vigilancia post-comercialización",
        "¿Se ha establecido un proceso para recopilar y analizar el rendimiento y los impactos del sistema en el entorno real?",
        "Plan de monitoreo, reportes periódicos, retroalimentación y métricas posproducción.", 23
    ),
    (
        "AIR-024", "F5", "Fase 5: Despliegue y Operación", "MANAGE", "MANAGE-2",
        "Plan de contingencia",
        "¿Existe un procedimiento documentado y probado para la desactivación, reversión o sustitución segura del sistema?",
        "Plan de contingencia, rollback, criterios de suspensión y resultados de pruebas.", 24
    ),
    (
        "AIR-025", "F5", "Fase 5: Despliegue y Operación", "MANAGE", "MANAGE-4",
        "Gestión de incidentes",
        "¿Existe un canal y un proceso para reportar, investigar y tratar comportamientos anómalos o impactos adversos del sistema?",
        "Procedimiento de incidentes de IA, canal de reporte, registros y lecciones aprendidas.", 25
    ),
]

# La evaluación de riesgos no mantiene una escala de madurez separada.
# Reutiliza directamente AI_STATUS_SCORE y AI_MADUREZ_LEVELS, que son
# los parámetros definidos para el módulo de madurez de IA.


# ============================================================
# DB INDEPENDIENTE
# ============================================================

def get_ai_madurez_conn():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(AI_MADUREZ_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_ai_madurez_db():
    conn = get_ai_madurez_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_madurez_preguntas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            capitulo TEXT NOT NULL,
            capitulo_codigo TEXT,
            categoria TEXT,
            categoria_codigo TEXT,
            orden INTEGER NOT NULL DEFAULT 0,
            pregunta TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_madurez_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            consecutivo TEXT NOT NULL,
            user_id INTEGER,
            estado TEXT NOT NULL DEFAULT 'BORRADOR',
            progreso_pct INTEGER NOT NULL DEFAULT 0,
            resumen_json TEXT NOT NULL DEFAULT '{}',
            pct_general REAL NOT NULL DEFAULT 0,
            radar_overall_b64 TEXT,
            informe_ejecutivo_ai TEXT,
            informe_ejecutivo_editado TEXT,
            plan_trabajo_ai TEXT,
            plan_trabajo_editado TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_madurez_respuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            pregunta_id INTEGER NOT NULL,
            estado TEXT NOT NULL,
            comentario TEXT,
            UNIQUE(run_id, pregunta_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_madurez_categoria_analisis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            capitulo TEXT NOT NULL,
            categoria_codigo TEXT NOT NULL,
            estado_actual TEXT,
            estado_requerido TEXT,
            plan_accion_ai TEXT,
            plan_accion_editado TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(run_id, capitulo, categoria_codigo)
        )
    """)

    # Tablas independientes del submódulo Evaluación de Riesgos — NIST AI RMF.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_risk_preguntas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            fase_codigo TEXT NOT NULL,
            fase TEXT NOT NULL,
            nist_funcion TEXT NOT NULL,
            nist_categoria TEXT NOT NULL,
            titulo TEXT NOT NULL,
            pregunta TEXT NOT NULL,
            evidencia_sugerida TEXT,
            orden INTEGER NOT NULL DEFAULT 0,
            activo INTEGER NOT NULL DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_risk_evaluaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            consecutivo TEXT NOT NULL,
            nombre_proyecto TEXT NOT NULL,
            responsable TEXT,
            caso_uso TEXT,
            descripcion TEXT,
            clasificacion_riesgo TEXT,
            user_id INTEGER,
            estado TEXT NOT NULL DEFAULT 'BORRADOR',
            progreso_pct INTEGER NOT NULL DEFAULT 0,
            cumplimiento_pct REAL NOT NULL DEFAULT 0,
            exposicion_pct REAL NOT NULL DEFAULT 100,
            nivel_riesgo TEXT NOT NULL DEFAULT 'Nivel 1: Ejecutado (Performed)',
            resumen_json TEXT NOT NULL DEFAULT '{}',
            analisis_ai TEXT,
            plan_tratamiento_ai TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_risk_respuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluacion_id INTEGER NOT NULL,
            pregunta_id INTEGER NOT NULL,
            estado TEXT NOT NULL,
            comentario TEXT,
            evidencia TEXT,
            UNIQUE(evaluacion_id, pregunta_id)
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_risk_eval_usuario
        ON ai_risk_evaluaciones(user_id, estado, updated_at)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_risk_resp_evaluacion
        ON ai_risk_respuestas(evaluacion_id, pregunta_id)
    """)

    # Carga y mantiene sincronizadas las 25 preguntas del documento Word.
    for item in AI_RISK_QUESTION_CATALOG:
        (
            codigo, fase_codigo, fase, nist_funcion, nist_categoria,
            titulo, pregunta, evidencia_sugerida, orden
        ) = item

        cur.execute("""
            INSERT OR IGNORE INTO ai_risk_preguntas (
                codigo, fase_codigo, fase, nist_funcion, nist_categoria,
                titulo, pregunta, evidencia_sugerida, orden, activo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, item)

        cur.execute("""
            UPDATE ai_risk_preguntas
            SET fase_codigo = ?,
                fase = ?,
                nist_funcion = ?,
                nist_categoria = ?,
                titulo = ?,
                pregunta = ?,
                evidencia_sugerida = ?,
                orden = ?,
                activo = 1
            WHERE codigo = ?
        """, (
            fase_codigo,
            fase,
            nist_funcion,
            nist_categoria,
            titulo,
            pregunta,
            evidencia_sugerida,
            orden,
            codigo
        ))


    conn.commit()
    conn.close()


init_ai_madurez_db()

def ai_madurez_corregir_codigos_tildes():
    """
    Corrige códigos dañados tipo CONTEXTO_DE_LA_ORGANIZACI_N
    en preguntas, análisis y resumen_json de revisiones existentes.
    No borra respuestas.
    """
    conn = get_ai_madurez_conn()
    cur = conn.cursor()

    reemplazos = {
        "CONTEXTO_DE_LA_ORGANIZACI_N": "CONTEXTO_DE_LA_ORGANIZACION",
        "PLANIFICACI_N": "PLANIFICACION",
        "OPERACI_N": "OPERACION",
        "EVALUACI_N_DEL_DESEMPE_O": "EVALUACION_DEL_DESEMPENO",
        "EVALUACI_N": "EVALUACION",
        "DESEMPE_O": "DESEMPENO",
        "GESTI_N": "GESTION",
        "INFORMACI_N": "INFORMACION",
    }

    for viejo, nuevo in reemplazos.items():
        cur.execute("""
            UPDATE ai_madurez_preguntas
            SET categoria_codigo = REPLACE(categoria_codigo, ?, ?),
                capitulo_codigo = REPLACE(capitulo_codigo, ?, ?)
            WHERE categoria_codigo LIKE '%' || ? || '%'
               OR capitulo_codigo LIKE '%' || ? || '%'
        """, (viejo, nuevo, viejo, nuevo, viejo, viejo))

        cur.execute("""
            UPDATE ai_madurez_categoria_analisis
            SET categoria_codigo = REPLACE(categoria_codigo, ?, ?),
                capitulo = REPLACE(capitulo, ?, ?)
            WHERE categoria_codigo LIKE '%' || ? || '%'
               OR capitulo LIKE '%' || ? || '%'
        """, (viejo, nuevo, viejo, nuevo, viejo, viejo))

    runs = cur.execute("SELECT id, resumen_json FROM ai_madurez_runs").fetchall()

    for run in runs:
        raw = run["resumen_json"] or "{}"

        for viejo, nuevo in reemplazos.items():
            raw = raw.replace(viejo, nuevo)

        try:
            obj = json.loads(raw)
            nuevo_resumen = {}

            for cap, cats in (obj or {}).items():
                cap_limpio = cap
                for viejo, nuevo in reemplazos.items():
                    cap_limpio = cap_limpio.replace(viejo, nuevo)

                nuevo_resumen.setdefault(cap_limpio, {})

                for cat_code, data in (cats or {}).items():
                    cat_limpio = cat_code
                    for viejo, nuevo in reemplazos.items():
                        cat_limpio = cat_limpio.replace(viejo, nuevo)

                    nuevo_resumen[cap_limpio][cat_limpio] = data

            raw = json.dumps(nuevo_resumen, ensure_ascii=False)

        except Exception:
            pass

        cur.execute("""
            UPDATE ai_madurez_runs
            SET resumen_json = ?,
                radar_overall_b64 = NULL,
                updated_at = ?
            WHERE id = ?
        """, (raw, _ai_now(), run["id"]))

    conn.commit()
    conn.close()


# ============================================================
# HELPERS
# ============================================================

def _ai_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Ejecutar corrección automática de códigos con tildes
try:
    ai_madurez_corregir_codigos_tildes()
except Exception as e:
    print("Corrección automática ISO 42001:", e)


def _ai_normalizar_texto(v):
    if v is None:
        return ""

    if isinstance(v, (dict, list)):
        try:
            return json.dumps(v, ensure_ascii=False, indent=2).strip()
        except Exception:
            return str(v).strip()

    return str(v or "").replace("\r\n", "\n").replace("\r", "\n").strip()

def _ai_estado_normalizado(v):
    estado = str(v or "").strip().upper()
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

def _ai_key(v):
    txt = str(v or "").strip()

    txt = txt.replace("ORGANIZACI_N", "ORGANIZACION")
    txt = txt.replace("PLANIFICACI_N", "PLANIFICACION")
    txt = txt.replace("OPERACI_N", "OPERACION")
    txt = txt.replace("EVALUACI_N", "EVALUACION")
    txt = txt.replace("DESEMPE_O", "DESEMPENO")
    txt = txt.replace("GESTI_N", "GESTION")
    txt = txt.replace("INFORMACI_N", "INFORMACION")

    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = txt.upper()
    txt = re.sub(r"[^A-Z0-9]+", "_", txt)
    txt = re.sub(r"_+", "_", txt).strip("_")
    return txt

def _ai_codigo_limpio(v):
    txt = str(v or "").strip()

    reemplazos = {
        "CONTEXTO_DE_LA_ORGANIZACI_N": "CONTEXTO_DE_LA_ORGANIZACION",
        "PLANIFICACI_N": "PLANIFICACION",
        "OPERACI_N": "OPERACION",
        "EVALUACI_N_DEL_DESEMPE_O": "EVALUACION_DEL_DESEMPENO",
        "EVALUACI_N": "EVALUACION",
        "DESEMPE_O": "DESEMPENO",
        "GESTI_N": "GESTION",
        "INFORMACI_N": "INFORMACION",
    }

    for viejo, nuevo in reemplazos.items():
        txt = txt.replace(viejo, nuevo)

    return txt


def _ai_codigo_visible(v):
    txt = _ai_codigo_limpio(v)

    nombres = {
        "CONTEXTO_DE_LA_ORGANIZACION": "Contexto de la Organización",
        "PLANIFICACION": "Planificación",
        "OPERACION": "Operación",
        "EVALUACION_DEL_DESEMPENO": "Evaluación del Desempeño",
        "GESTION": "Gestión",
        "INFORMACION": "Información",
    }

    return nombres.get(txt, txt.replace("_", " ").title())

def _ai_texto_plano_desde_valor(v):
    """
    Convierte respuestas IA tipo string, dict o list en texto legible.
    Evita que se muestre JSON crudo en Estado actual / Estado requerido.
    """
    if v is None:
        return ""

    if isinstance(v, str):
        return _ai_normalizar_texto(v)

    if isinstance(v, list):
        partes = []
        for i, item in enumerate(v, start=1):
            txt = _ai_texto_plano_desde_valor(item)
            if txt:
                partes.append(f"{i}. {txt}")
        return "\n".join(partes).strip()

    if isinstance(v, dict):
        partes = []

        for k, val in v.items():
            if isinstance(val, dict):
                subpartes = []
                for sk, sv in val.items():
                    txt = _ai_texto_plano_desde_valor(sv)
                    if txt:
                        subpartes.append(f"{sk}: {txt}")

                if subpartes:
                    partes.append(f"{k}:\n" + "\n".join(subpartes))

            elif isinstance(val, list):
                txt = _ai_texto_plano_desde_valor(val)
                if txt:
                    partes.append(f"{k}:\n{txt}")

            else:
                txt = _ai_texto_plano_desde_valor(val)
                if txt:
                    partes.append(f"{k}: {txt}")

        return "\n\n".join(partes).strip()

    return str(v).strip()


def _ai_permiso(user):
    if not user:
        return False
    if user.role in ("admin", "auditor"):
        return True
    return verificar_permiso(user, AI_MADUREZ_PERMISO)


def _ai_read_only(user):
    return bool(user and user.role == "auditor")


def _ai_escape(v):
    return escape(v or "")


AI_MADUREZ_PROGRESS_JS = """
<script>
(function () {
    window.ai42001Progress = function (mensaje) {
        try {
            if (typeof window.showSGSIProgress === "function") {
                window.showSGSIProgress(
                    mensaje || "Generando y procesando información..."
                );
            }
        } catch (e) {
            console.log("Progreso IA ISO 42001:", e);
        }

        return true;
    };
})();
</script>
"""


def _ai_parse_rango_pct(rango):
    if not rango:
        return None, None
    s = str(rango).replace("%", "").replace("–", "-").strip()
    parts = [p.strip() for p in s.split("-")]
    if len(parts) != 2:
        return None, None
    try:
        return float(parts[0]), float(parts[1])
    except Exception:
        return None, None


def ai_nivel_visual_por_pct(pct):
    try:
        p = float(pct or 0)
    except Exception:
        p = 0.0
    p = max(0.0, min(100.0, p))

    color_map = {
        1: "#dc3545",
        2: "#fd7e14",
        3: "#ffc107",
        4: "#0d6efd",
        5: "#198754",
    }

    for lvl in AI_MADUREZ_LEVELS:
        lo, hi = _ai_parse_rango_pct(lvl.get("rango_pct", ""))
        if lo is None:
            continue
        if lo <= p <= hi:
            score = int(lvl.get("score", 0) or 0)
            return {
                "nivel": lvl.get("nivel", ""),
                "score": score,
                "color": color_map.get(score, "#6c757d"),
            }

    return {"nivel": "Nivel no definido", "score": 0, "color": "#6c757d"}


def _ai_limpiar_texto_rico_guardado(texto):
    txt = (texto or "").strip()
    if not txt:
        return ""

    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = html.unescape(txt)
    txt = txt.replace("```json", "").replace("```", "").strip()

    try:
        obj = json.loads(txt)
        if isinstance(obj, dict):
            for k in ("informe_ejecutivo", "plan_trabajo", "texto"):
                val = obj.get(k)
                if isinstance(val, str) and val.strip():
                    txt = val.strip()
                    break
    except Exception:
        pass

    txt = html.unescape(txt)
    txt = re.sub(r"<\s*br\s*/?\s*>", "\n", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = txt.replace("**", "").replace("__", "")
    txt = re.sub(r"^\s*(INFORME EJECUTIVO|RESUMEN EJECUTIVO)\s*[:\-–—]?\s*", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"[ \t]+\n", "\n", txt)
    txt = re.sub(r"\n[ \t]+", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)

    return txt.strip()


def _ai_extraer_json_objeto(raw):
    txt = (raw or "").strip()
    if not txt:
        return {}

    txt = txt.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(txt)
    except Exception:
        pass

    try:
        start = txt.find("{")
        end = txt.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(txt[start:end + 1])
    except Exception:
        pass

    return {}


def _ai_build_plan_accion_texto(plan_list):
    if not isinstance(plan_list, list):
        return ""

    lines = []
    for i, it in enumerate(plan_list, start=1):
        accion = _ai_normalizar_texto(it.get("accion"))
        prioridad = _ai_normalizar_texto(it.get("prioridad"))
        responsable = _ai_normalizar_texto(it.get("responsable_sugerido"))
        plazo = _ai_normalizar_texto(it.get("plazo"))
        evidencia = _ai_normalizar_texto(it.get("evidencia_esperada"))

        lines.append(
            f"{i}. Acción: {accion or 'Sin definir'}\n"
            f"   Prioridad: {prioridad or 'Sin definir'}\n"
            f"   Responsable sugerido: {responsable or 'Sin definir'}\n"
            f"   Plazo: {plazo or 'Sin definir'}\n"
            f"   Evidencia esperada: {evidencia or 'Sin definir'}"
        )

    return "\n\n".join(lines).strip()


def _ai_normalizar_plan_accion_texto(texto_raw):
    txt = (texto_raw or "").strip()
    if not txt:
        return ""

    txt = txt.replace("```json", "").replace("```", "").strip()
    obj = _ai_extraer_json_objeto(txt)

    if isinstance(obj, dict):
        plan_list = obj.get("plan_accion") or obj.get("plan") or obj.get("acciones")
        plan_txt = _ai_build_plan_accion_texto(plan_list or [])
        if plan_txt:
            return plan_txt

        bloques = []
        if obj.get("estado_actual"):
            bloques.append("Estado actual:\n" + _ai_normalizar_texto(obj.get("estado_actual")))
        if obj.get("estado_requerido"):
            bloques.append("Estado requerido:\n" + _ai_normalizar_texto(obj.get("estado_requerido")))
        if bloques:
            return "\n\n".join(bloques).strip()

    return txt


def ai_cargar_preguntas():
    init_ai_madurez_db()
    conn = get_ai_madurez_conn()
    rows = conn.execute("""
        SELECT * FROM ai_madurez_preguntas
        WHERE activo = 1
        ORDER BY capitulo ASC, categoria_codigo ASC, orden ASC, id ASC
    """).fetchall()
    conn.close()
    return rows


def ai_cargar_respuestas(run_id):
    out = {}
    if not run_id:
        return out

    conn = get_ai_madurez_conn()
    rows = conn.execute(
        "SELECT * FROM ai_madurez_respuestas WHERE run_id = ?",
        (run_id,)
    ).fetchall()
    conn.close()

    for r in rows:
        out[int(r["pregunta_id"])] = {
            "estado": _ai_estado_normalizado(r["estado"]),
            "comentario": (r["comentario"] or "").strip(),
        }

    return out


def ai_obtener_borrador(user_id):
    if not user_id:
        return None

    conn = get_ai_madurez_conn()
    row = conn.execute("""
        SELECT * FROM ai_madurez_runs
        WHERE user_id = ? AND estado = 'BORRADOR'
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
    """, (user_id,)).fetchone()
    conn.close()
    return row


def ai_calcular_progreso(preguntas, form_data=None, respuestas_db=None):
    total = len(preguntas)
    respondidas = 0

    for q in preguntas:
        qid = int(q["id"])
        estado = ""

        if form_data is not None:
            estado = _ai_estado_normalizado(form_data.get(f"st_{qid}"))
        elif respuestas_db is not None:
            estado = _ai_estado_normalizado(respuestas_db.get(qid, {}).get("estado"))

        if estado in ("SI", "PARCIAL", "NO", "NA"):
            respondidas += 1

    pct = int(round((respondidas / total) * 100)) if total else 0
    return respondidas, total, pct


def ai_group_questions():
    preguntas = ai_cargar_preguntas()
    grouped = {}

    for q in preguntas:
        cap = q["capitulo"] or "Sin capítulo"
        cat_code = q["categoria_codigo"] or cap
        categoria = q["categoria"] or cap

        grouped.setdefault(cap, {})
        grouped[cap].setdefault(cat_code, {"categoria": categoria, "items": []})
        grouped[cap][cat_code]["items"].append(q)

    return grouped


def ai_resumen_desde_run(run_id):
    conn = get_ai_madurez_conn()

    rows = conn.execute("""
        SELECT
            p.capitulo,
            COALESCE(p.categoria_codigo, p.capitulo) AS categoria_codigo,
            COALESCE(p.categoria, p.capitulo) AS categoria,
            r.estado
        FROM ai_madurez_respuestas r
        INNER JOIN ai_madurez_preguntas p ON p.id = r.pregunta_id
        WHERE r.run_id = ?
        ORDER BY p.capitulo ASC, p.categoria_codigo ASC, p.orden ASC
    """, (run_id,)).fetchall()

    conn.close()

    resumen = {}

    for row in rows:
        estado = _ai_estado_normalizado(row["estado"])

        if estado not in ("SI", "PARCIAL", "NO", "NA"):
            continue

        cap = row["capitulo"] or "Sin capítulo"
        cat = _ai_codigo_limpio(row["categoria_codigo"] or cap)
        cat_name = row["categoria"] or _ai_codigo_visible(cat)

        resumen.setdefault(cap, {})
        resumen[cap].setdefault(cat, {
            "categoria": cat_name,
            "total": 0,
            "total_respondidas": 0,
            "validos": 0,
            "si": 0,
            "parcial": 0,
            "no": 0,
            "na": 0,
            "score": 0.0,
            "pct": 0.0,
        })

        d = resumen[cap][cat]
        d["total"] += 1
        d["total_respondidas"] += 1

        # N/A cuenta como respondida, pero NO entra al porcentaje
        if estado == "NA":
            d["na"] += 1
            continue

        score = AI_STATUS_SCORE.get(estado)

        if score is None:
            continue

        d["validos"] += 1
        d["score"] += float(score)

        if estado == "SI":
            d["si"] += 1
        elif estado == "PARCIAL":
            d["parcial"] += 1
        elif estado == "NO":
            d["no"] += 1

    # Calcula porcentaje por categoría
    categorias_validas_pct = []

    for cap, cats in resumen.items():
        for cat, d in cats.items():
            validos = int(d.get("validos") or 0)
            score = float(d.get("score") or 0)

            if validos > 0:
                d["pct"] = round((score / validos) * 100, 2)
                categorias_validas_pct.append(float(d["pct"]))
            else:
                d["pct"] = 0.0

    # Cálculo general correcto:
    # promedio simple de categorías válidas,
    # NO promedio por cantidad de preguntas.
    pct_general = (
        round(sum(categorias_validas_pct) / len(categorias_validas_pct), 2)
        if categorias_validas_pct
        else 0.0
    )

    return resumen, pct_general

def ai_pct_por_capitulo(resumen):
    labels = []
    values = []

    ordered = []

    for cap in AI_CAP_ORDER_DEFAULT:
        if cap in (resumen or {}):
            ordered.append(cap)

    for cap in (resumen or {}).keys():
        if cap not in ordered:
            ordered.append(cap)

    for cap in ordered:
        cats = (resumen or {}).get(cap, {}) or {}
        pcts_validos = []

        for _cat_code, d in cats.items():
            validos = int(d.get("validos", 0) or 0)

            if validos <= 0:
                continue

            pcts_validos.append(float(d.get("pct", 0) or 0))

        labels.append(cap)
        values.append(
            round(sum(pcts_validos) / len(pcts_validos), 2)
            if pcts_validos
            else 0.0
        )

    return labels, values

def ai_recalcular_y_actualizar_run(run_id):
    conn = get_ai_madurez_conn()

    rows = conn.execute("""
        SELECT id, estado
        FROM ai_madurez_respuestas
        WHERE run_id = ?
    """, (run_id,)).fetchall()

    for r in rows:
        estado_norm = _ai_estado_normalizado(r["estado"])

        if estado_norm:
            conn.execute("""
                UPDATE ai_madurez_respuestas
                SET estado = ?
                WHERE id = ?
            """, (estado_norm, r["id"]))

    conn.commit()
    conn.close()

    resumen, pct_general = ai_resumen_desde_run(run_id)

    conn = get_ai_madurez_conn()
    conn.execute("""
        UPDATE ai_madurez_runs
        SET resumen_json = ?,
            pct_general = ?,
            radar_overall_b64 = NULL,
            updated_at = ?
        WHERE id = ?
    """, (
        json.dumps(resumen, ensure_ascii=False),
        pct_general,
        _ai_now(),
        run_id
    ))

    conn.commit()
    conn.close()

    return resumen, pct_general


def ai_radar_b64(labels, values, title="Radar ISO 42001"):
    if not labels:
        return ""

    vals = [max(0.0, min(100.0, float(v or 0))) for v in values]
    N = len(labels)

    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]
    plot_vals = vals + vals[:1]

    fig = plt.figure(figsize=(3.55, 3.55), dpi=170)
    ax = plt.subplot(111, polar=True)
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=6.6)
    ax.tick_params(axis="x", pad=9)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7)
    ax.plot(angles, plot_vals, linewidth=2.0)
    ax.fill(angles, plot_vals, alpha=0.16)
    ax.set_title(title, fontsize=9.5, pad=14)
    fig.subplots_adjust(top=0.83, bottom=0.10, left=0.10, right=0.90)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0.22)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def ai_importar_instrumento_desde_excel(path_excel, force=False):
    if not os.path.exists(path_excel):
        raise FileNotFoundError(f"No existe el archivo del instrumento: {path_excel}")

    init_ai_madurez_db()

    conn = get_ai_madurez_conn()
    cur = conn.cursor()

    total_actual = cur.execute("SELECT COUNT(*) AS c FROM ai_madurez_preguntas").fetchone()["c"]
    if total_actual and not force:
        conn.close()
        return 0

    if force:
        cur.execute("DELETE FROM ai_madurez_categoria_analisis")
        cur.execute("DELETE FROM ai_madurez_respuestas")
        cur.execute("DELETE FROM ai_madurez_runs")
        cur.execute("DELETE FROM ai_madurez_preguntas")
        conn.commit()

    wb = load_workbook(path_excel, data_only=True)
    ws = wb[wb.sheetnames[0]]

    capitulo_actual = "General"
    categoria_actual = "General"
    categoria_codigo = "GENERAL"
    orden = 0
    insertados = 0

    for row in ws.iter_rows(min_row=1, values_only=True):
        pregunta = row[0] if row and len(row) else None
        texto = str(pregunta or "").strip()

        if not texto:
            continue

        lower = texto.lower()

        if lower in ("pregunta", "preguntas"):
            continue

        # Encabezados tipo: "Cláusula – Contexto de la Organización"
        if lower.startswith("cláusula") or lower.startswith("clausula") or lower.startswith("anexo") or lower.startswith("annex"):
            limpio = texto
            limpio = re.sub(r"^cl[áa]usula\s*[–—-]\s*", "", limpio, flags=re.IGNORECASE).strip()
            limpio = re.sub(r"^anexo\s*[–—-]?\s*", "Anexo ", limpio, flags=re.IGNORECASE).strip()
            capitulo_actual = limpio or texto
            categoria_actual = capitulo_actual
            categoria_codigo = _ai_key(capitulo_actual) or "GENERAL"
            continue

        # Filas normales de pregunta
        orden += 1
        cur.execute("""
            INSERT INTO ai_madurez_preguntas
            (capitulo, capitulo_codigo, categoria, categoria_codigo, orden, pregunta, activo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (
            capitulo_actual,
            categoria_codigo,
            categoria_actual,
            categoria_codigo,
            orden,
            texto,
        ))
        insertados += 1

    conn.commit()
    conn.close()
    return insertados


def _ai_items_categoria(run_id, cap_u, cat_u):
    cap_u = (cap_u or "").upper().strip()
    cat_u = (cat_u or "").upper().strip()

    conn = get_ai_madurez_conn()

    rows = conn.execute("""
        SELECT p.capitulo, p.categoria_codigo, p.categoria, p.pregunta, r.estado, r.comentario
        FROM ai_madurez_respuestas r
        INNER JOIN ai_madurez_preguntas p ON p.id = r.pregunta_id
        WHERE r.run_id = ?
          AND (
                UPPER(TRIM(p.capitulo)) = ?
             OR UPPER(TRIM(COALESCE(p.categoria_codigo, ''))) = ?
             OR UPPER(TRIM(COALESCE(p.categoria, ''))) = ?
          )
        ORDER BY p.orden ASC, p.id ASC
    """, (run_id, cap_u, cat_u, cat_u)).fetchall()

    conn.close()

    items = []
    for r in rows:
        estado = (r["estado"] or "").strip().upper()

        if estado not in ("SI", "PARCIAL", "NO", "NA"):
            continue

        items.append({
            "pregunta": _ai_normalizar_texto(r["pregunta"] or ""),
            "estado": estado,
            "comentario": _ai_normalizar_texto(r["comentario"] or ""),
        })

    return items


# ============================================================
# PROMPTS IA
# ============================================================

def _ai_prompt_categoria(capitulo, categoria_codigo, categoria_nombre, pct, items):
    bullets = []
    for it in items[:80]:
        pregunta = (it.get("pregunta") or "")[:320].replace("\n", " ")
        comentario = (it.get("comentario") or "")[:420].replace("\n", " ")
        estado = (it.get("estado") or "").strip().upper()

        linea = f"- Estado: {estado}. Pregunta: {pregunta}"
        if comentario:
            linea += f" Evidencia/comentario: {comentario}"

        bullets.append(linea)

    joined = "\n".join(bullets) if bullets else "- Sin evidencias registradas."

    return f"""
Eres un consultor experto en ISO/IEC 42001, gobierno de IA, gestión de riesgos de IA, seguridad de la información y sistemas de gestión.

CONTEXTO:
Capítulo: {capitulo}
Categoría: {categoria_codigo}
Nombre categoría: {categoria_nombre}
Cumplimiento actual: {pct:.2f}%

EVIDENCIAS:
{joined}

INSTRUCCIONES:
Devuelve únicamente JSON válido.
No uses markdown.
No devuelvas objetos anidados.
No agrupes por capítulo.
No uses llaves internas como SI, PARCIAL, NO o TODOS.
Cada campo debe ser texto plano.

ESTRUCTURA EXACTA:
{{
  "estado_actual": "Texto ejecutivo en párrafo, claro y profesional.",
  "estado_requerido": "Texto ejecutivo en párrafo, claro y profesional.",
  "plan_accion": [
    {{
      "accion": "Texto de la acción.",
      "prioridad": "Alta",
      "responsable_sugerido": "Texto del responsable sugerido.",
      "plazo": "Texto del plazo.",
      "evidencia_esperada": "Texto de la evidencia esperada."
    }}
  ]
}}

REGLAS:
Escribe en español.
El estado actual debe explicar qué muestran las respuestas SI, PARCIAL, NO y NA.
El estado requerido debe describir la condición objetivo para cumplir ISO/IEC 42001.
El plan de acción debe tener entre 3 y 6 acciones.
Si falta evidencia, indícalo dentro del texto ejecutivo, no como JSON.
""".strip()


def _ai_prompt_informe_ejecutivo(run, resumen):
    partes = []
    labels, vals = ai_pct_por_capitulo(resumen)
    pct_por_cap = dict(zip(labels, vals))

    for cap, cats in (resumen or {}).items():
        lineas = []
        for cat_code, d in cats.items():
            lineas.append(
                f"  * {cat_code} - {d.get('categoria','')}: {float(d.get('pct',0) or 0):.2f}% "
                f"({int(d.get('total',0) or 0)} ítems)"
            )
        partes.append(f"- {cap}: {pct_por_cap.get(cap, 0):.2f}%\n" + "\n".join(lineas[:25]))

    detalle = "\n".join(partes)

    return f"""
Eres un consultor senior en ISO/IEC 42001, gobierno de Inteligencia Artificial, seguridad de la información y gestión de riesgos.
Debes redactar un INFORME EJECUTIVO para alta dirección, claro, breve, profesional y accionable.

DATOS GENERALES
Consecutivo: {run["consecutivo"]}
Cumplimiento general: {float(run["pct_general"] or 0):.2f}%
Nivel general: {ai_nivel_visual_por_pct(run["pct_general"]).get("nivel","")}

RESULTADOS POR CAPÍTULO Y CATEGORÍA
{detalle}

INSTRUCCIONES
Devuelve solamente JSON válido.
Estructura exacta:
{{"informe_ejecutivo":"texto"}}

REGLAS DEL TEXTO
Escribe en español.
Extensión aproximada: 4 a 7 párrafos cortos.
Incluye: resumen general, fortalezas, brechas, capítulos más débiles, riesgos ejecutivos y prioridades de 90 días.
No uses markdown ni viñetas.
No inventes herramientas específicas.
""".strip()


def _ai_prompt_plan_trabajo(run, resumen):
    partes = []
    for cap, cats in (resumen or {}).items():
        for cat_code, d in cats.items():
            pct = float(d.get("pct", 0) or 0)
            partes.append(
                f"- {cap} | {cat_code} - {d.get('categoria','')}: "
                f"{pct:.2f}% | brecha {100-pct:.2f}% | {int(d.get('total',0) or 0)} ítems"
            )

    detalle = "\n".join(partes)

    return f"""
Eres un consultor senior en ISO/IEC 42001 y gobierno de Inteligencia Artificial.
Construye un PLAN DE TRABAJO GENERAL para cerrar brechas de madurez del sistema de gestión de IA.

DATOS GENERALES
Consecutivo: {run["consecutivo"]}
Cumplimiento general: {float(run["pct_general"] or 0):.2f}%
Nivel general: {ai_nivel_visual_por_pct(run["pct_general"]).get("nivel","")}

RESULTADOS
{detalle}

INSTRUCCIONES
Devuelve solamente JSON válido.
Estructura exacta:
{{"plan_trabajo":[{{"frente":"string","actividad":"string","prioridad":"Alta|Media|Baja","responsable_sugerido":"string","plazo":"string","entregable":"string"}}]}}

REGLAS
Genera entre 8 y 15 actividades.
Prioriza categorías con menor cumplimiento.
Usa lenguaje ejecutivo y accionable.
No inventes herramientas específicas.
""".strip()


def _ai_call_text(prompt, max_tokens=1200):
    try:
        prompt = (prompt or "").strip()
        if not prompt:
            raise RuntimeError("Prompt vacío para IA.")

        try:
            return _ai_text(prompt, max_tokens=max_tokens)
        except TypeError:
            return _ai_text(prompt)

    except NameError:
        raise RuntimeError("No existe el helper global _ai_text(). Integra este módulo después del helper IA usado por NIST.")
    except Exception as e:
        raise RuntimeError(f"Error real llamando IA: {e}")


# ============================================================
# CSS BASE — MISMO PATRÓN NIST CSF 2.0
# ============================================================

def ai_css(prefix="aimad", icon="🤖", tag="SGSI · ISO 42001"):
    return f"""
<style>
  .bg-purple{{ background-color:#6f42c1 !important; }}
  .badge.bg-purple{{ color:#ffffff !important; }}

  body{{
    background-image:url('/static/img/ccsgsi.jpg');
    background-size:cover;
    background-position:center;
    background-attachment:fixed;
    background-repeat:no-repeat;
  }}

  .{prefix}-shell{{
    width:96%;
    max-width:1600px;
    margin:26px auto 24px auto;
  }}

  .{prefix}-header-card{{
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

  .{prefix}-header-card::before{{
    content:"";
    position:absolute;
    inset:0;
    background:
      radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
      repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
    pointer-events:none;
  }}

  .{prefix}-header-overlay{{
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

  .{prefix}-header-overlay::before{{
    content:"{icon}";
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

  .{prefix}-header-text{{
    max-width:1100px;
    width:100%;
    display:block !important;
  }}

  .{prefix}-header-text::before{{
    content:"{tag}";
    display:inline-block;
    background:rgba(255,255,255,.18);
    border-radius:999px;
    padding:3px 10px;
    font-size:.65rem;
    font-weight:800;
    margin-bottom:4px;
    color:#ffffff;
  }}

  .{prefix}-title{{
    color:#ffffff !important;
    font-weight:950;
    font-size:1.32rem;
    line-height:1.1;
    margin:0 !important;
    text-shadow:0 3px 10px rgba(0,0,0,.35);
  }}

  .{prefix}-subtitle{{
    color:rgba(255,255,255,.95);
    font-size:.78rem;
    margin-top:4px;
  }}

  .{prefix}-header-actions{{
    display:flex;
    justify-content:center;
    gap:10px;
    flex-wrap:wrap;
    margin:10px 0 14px;
  }}

  .{prefix}-header-actions .btn,
  .btn{{
    border-radius:10px !important;
    font-weight:900;
  }}

  .{prefix}-btn-main{{
    background:#ffffff;
    color:#0f172a !important;
    border:1px solid #cfd8e3 !important;
  }}

  .{prefix}-btn-main:hover{{
    background:#edf5ff;
    color:#0b65d8 !important;
  }}

  .{prefix}-btn-soft{{
    background:rgba(255,255,255,.88);
    color:#111 !important;
    border:1px solid rgba(108,117,125,.35);
  }}

  .{prefix}-card,
  .card{{
    background:rgba(255,255,255,.96) !important;
    border-radius:18px !important;
    backdrop-filter:blur(8px);
    box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
  }}

  .card-body{{ padding:18px; }}

  .{prefix}-section-title{{
    color:#1d4f8f;
    font-weight:950;
    font-size:1rem;
    margin-bottom:10px;
  }}

  .table-responsive{{
    max-height:72vh;
    overflow:auto;
    border-radius:14px;
    background:#ffffff;
  }}

  .table thead th{{
    position:sticky;
    top:0;
    background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
    color:#ffffff !important;
    font-size:.78rem;
    font-weight:900;
    text-align:center;
    z-index:2;
  }}

  .table tbody td{{
    font-size:.82rem;
    padding:9px;
    vertical-align:top;
  }}

  .table tbody tr:nth-child(even){{ background:#f8fbff; }}
  .table tbody tr:hover{{ background:#eef6ff; }}

  .form-control,
  .form-select{{
    border-radius:10px;
    border:1px solid #d9e3f0;
    min-height:40px;
  }}

  .form-control:focus,
  .form-select:focus{{
    border-color:#3f86d6;
    box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
  }}

  .ai-progress-wrap{{
    background:rgba(255,255,255,.92);
    border-radius:16px;
    padding:12px 16px;
    box-shadow:0 8px 20px rgba(15,23,42,.14);
  }}

  .ai-progress-bar{{
    height:18px;
    border-radius:999px;
    overflow:hidden;
    background:#e9eef6;
  }}

  .ai-progress-fill{{
    height:100%;
    background:linear-gradient(135deg,#0b4a8f,#1d5fae);
    color:#fff;
    font-size:.72rem;
    font-weight:900;
    text-align:center;
    line-height:18px;
  }}

  .ai-kpi{{
    border-radius:16px;
    background:#ffffff;
    border:1px solid #e2e8f0;
    padding:8px 7px;
    height:100%;
  }}

  .ai-kpi-value{{
    font-size:1.45rem;
    font-weight:950;
    color:#0b4a8f;
  }}

  .ai-kpi-label{{
    color:#475569;
    font-size:.78rem;
    font-weight:800;
  }}

  @media (max-width:768px){{
    .{prefix}-header-overlay{{
      flex-direction:column;
      text-align:center;
      gap:10px;
    }}

    .{prefix}-header-overlay::before{{ margin:0; }}

    .{prefix}-header-text::before{{
      margin-left:auto;
      margin-right:auto;
    }}

    .{prefix}-title,
    .{prefix}-subtitle{{ text-align:center; }}

    .{prefix}-header-actions .btn{{ width:100%; }}
  }}
</style>
"""


def ai_header(prefix, title, subtitle, icon="🤖", tag="SGSI · ISO 42001"):
    return f"""
<div class="{prefix}-header-card">
  <div class="{prefix}-header-overlay">
    <div class="{prefix}-header-text">
      <h3 class="{prefix}-title m-0">{title}</h3>
      <div class="{prefix}-subtitle">{subtitle}</div>
    </div>
  </div>
</div>
{ai_css(prefix, icon, tag)}
"""


# ============================================================
# RUTAS
# ============================================================

@ai_madurez_bp.route("/", methods=["GET"])
@login_required
def home():
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para acceder al módulo de Nivel de Madurez de Gestión de Inteligencia Artificial.", "danger")
        return redirect(url_for("menu"))

    read_only = _ai_read_only(user)
    conn = get_ai_madurez_conn()
    total = conn.execute("SELECT COUNT(*) AS c FROM ai_madurez_preguntas").fetchone()["c"]
    conn.close()

    if read_only:
        ingreso_btn = """
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled
                  title="El rol Auditor no puede ingresar información">
            <i class="bi bi-pencil-square me-2"></i>Ingresar la información
          </button>
        """
        parametros_btn = """
          <button class="btn btn-outline-secondary rounded-pill px-3" disabled
                  title="El rol Auditor no tiene acceso a Parámetros">
            <i class="bi bi-gear me-2"></i>Parámetros
          </button>
        """
    else:
        ingreso_btn = f"""
          <a href="{url_for('madurez_ai.ingreso')}" class="btn btn-primary rounded-pill px-4 fw-bold">
            <i class="bi bi-pencil-square me-2"></i>Ingresar la información
          </a>
        """
        parametros_btn = f"""
          <a href="{url_for('madurez_ai.parametros')}" class="btn btn-outline-secondary rounded-pill px-3">
            <i class="bi bi-gear me-2"></i>Parámetros
          </a>
        """

    if total == 0:
        badge = '<span class="badge bg-danger ms-2">Instrumento NO cargado</span>'
        hint = "Primero entra a Parámetros y realiza la importación del instrumento ISO 42001."
    else:
        badge = '<span class="badge bg-success ms-2">Instrumento cargado</span>'
        hint = "Puedes ingresar la información o consultar el historial de revisiones."

    content = f"""
<div class="aimad-shell">

  {ai_header(
      "aimad",
      "Nivel de Madurez — Sistema de Gestión de Inteligencia Artificial",
      "Evaluación de madurez del Sistema de Gestión de IA basada en ISO/IEC 42001 y controles asociados.",
      "🤖",
      "SGSI · ISO 42001"
  )}

  <div class="aimad-header-actions">
    {ingreso_btn}
    <a href="{url_for('madurez_ai.historial')}" class="btn aimad-btn-soft rounded-pill px-4">
      <i class="bi bi-clock-history me-2"></i>Historial de Revisiones
    </a>
    <a href="{url_for('madurez_ai.ai_risk_home')}" class="btn btn-warning rounded-pill px-4 fw-bold">
      <i class="bi bi-exclamation-diamond-fill me-2"></i>Nivel de Madurez de Riesgos — NIST AI RMF
    </a>
  </div>

  <div class="row g-3 mt-2">
    <div class="col-12 col-lg-8">
      <div class="aimad-card p-4 h-100">
        <div class="aimad-section-title">Estado del instrumento</div>

        <div class="d-flex justify-content-between align-items-start flex-wrap gap-3">
          <div>
            <div class="fw-bold">Estado del instrumento {badge}</div>
            <div class="text-muted small mt-1">Preguntas cargadas: <b>{total}</b></div>
            <div class="mt-2 small">{hint}</div>
          </div>

          <div class="text-end">
            <div class="text-muted small">Acceso rápido</div>
            <div class="d-flex gap-2 flex-wrap justify-content-end mt-2">
              {parametros_btn}
            </div>
          </div>
        </div>

        <div class="alert alert-info mt-3 mb-0 small">
          <b>Sugerencia:</b> Usa <b>Parámetros</b> para cargar el instrumento y revisar la escala de madurez 1–5.
        </div>
      </div>
    </div>

    <div class="col-12 col-lg-4">
      <div class="aimad-card p-4 h-100">
        <div class="aimad-section-title">¿Qué puedes hacer aquí?</div>
        <ul class="small mb-0 text-black ps-3">
          <li><b>Ingresar información:</b> responder Sí/Parcial/No/N/A con comentarios.</li>
          <li><b>Historial:</b> consultar evaluaciones previas.</li>
          <li><b>Detalle:</b> ver cumplimiento, radar, informe IA, plan de trabajo y PDF.</li>
          <li><b>Riesgos de IA:</b> evaluar proyectos durante todo su ciclo de vida con NIST AI RMF.</li>
        </ul>
      </div>
    </div>
  </div>
</div>
"""
    return render_template_string(BASE, title="Madurez Gestión IA", content=content)


@ai_madurez_bp.route("/parametros", methods=["GET"])
@login_required
def parametros():
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para acceder a Parámetros del módulo de Gestión de IA.", "danger")
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El rol Auditor no tiene acceso a Parámetros.", "warning")
        return redirect(url_for("madurez_ai.home"))

    conn = get_ai_madurez_conn()
    total = conn.execute("SELECT COUNT(*) AS c FROM ai_madurez_preguntas").fetchone()["c"]
    conn.close()

    badge = '<span class="badge bg-danger ms-2">Instrumento NO cargado</span>' if total == 0 else '<span class="badge bg-success ms-2">Instrumento cargado</span>'

    rows = ""
    for lvl in AI_MADUREZ_LEVELS:
        rows += f"""
        <tr>
          <td class="fw-semibold">{escape(lvl["nivel"])}</td>
          <td class="text-muted">{escape(lvl["descripcion"])}</td>
          <td class="text-center fw-bold">{lvl["score"]}</td>
          <td class="text-center">{escape(lvl["rango_pct"])}</td>
          <td class="text-muted">{escape(lvl["logica"])}</td>
        </tr>
        """

    content = f"""
<div class="aipar-shell">
  {ai_header(
      "aipar",
      "Parámetros — Madurez Gestión de Inteligencia Artificial",
      "Configuración del instrumento ISO 42001 y definición de niveles de madurez.",
      "⚙️",
      "SGSI · Parámetros ISO 42001"
  )}

  <div class="aipar-header-actions">
    <a href="{url_for('madurez_ai.home')}" class="btn aipar-btn-main rounded-pill px-4 fw-bold">
      <i class="bi bi-arrow-left me-2"></i>Volver al Menú Principal de Madurez IA
    </a>
  </div>

  <div class="row g-3 mt-2">
    <div class="col-12 col-lg-5">
      <div class="aipar-card p-4 h-100">
        <div class="aipar-section-title">Instrumento</div>

        <div class="text-muted small">
          Preguntas cargadas: <b>{total}</b> {badge}
        </div>

        <div class="d-flex gap-2 flex-wrap mt-3">
          <form method="POST" action="{url_for('madurez_ai.importar_instrumento')}">
            <button class="btn btn-danger rounded-pill px-4">
              <i class="bi bi-database-add me-2"></i>Importar instrumento
            </button>
          </form>

          <form method="POST" action="{url_for('madurez_ai.importar_instrumento', force=1)}">
            <button class="btn btn-outline-danger rounded-pill px-4">
              <i class="bi bi-arrow-repeat me-2"></i>Re-importar force
            </button>
          </form>
        </div>

        <div class="alert alert-warning mt-3 mb-0 small">
          <b>Nota:</b> “Re-importar force” elimina preguntas, runs, respuestas y análisis del módulo IA.
        </div>

        <div class="mt-3">
          <a href="{url_for('madurez_ai.ingreso')}" class="btn btn-primary rounded-pill px-4 w-100 fw-semibold">
            <i class="bi bi-pencil-square me-2"></i>Ir a Ingresar la información
          </a>
        </div>
      </div>
    </div>

    <div class="col-12 col-lg-7">
      <div class="aipar-card p-4 h-100">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
          <div class="aipar-section-title mb-0">📌 Niveles de Madurez</div>
          <span class="badge bg-secondary">1 a 5</span>
        </div>

        <div class="table-responsive">
          <table class="table table-sm align-middle mb-0">
            <thead>
              <tr>
                <th style="width:28%;">Nivel de Madurez</th>
                <th>Descripción</th>
                <th style="width:70px;">Score</th>
                <th style="width:110px;">Rango %</th>
                <th style="width:22%;">Lógica</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </div>

        <div class="small text-muted mt-3">
          El puntaje se calcula por cumplimiento: Sí = 100%, Parcial = 50%, No = 0%, N/A se excluye.
        </div>
      </div>
    </div>
  </div>
</div>
"""
    return render_template_string(BASE, title="Parámetros Madurez IA", content=content)


@ai_madurez_bp.route("/parametros/importar", methods=["POST"])
@login_required
def importar_instrumento():
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user) or user.role == "auditor":
        flash("No tiene permiso para importar el instrumento de Gestión de IA.", "danger")
        return redirect(url_for("madurez_ai.home"))

    force = str(request.args.get("force", "")).strip() == "1"

    try:
        insertados = ai_importar_instrumento_desde_excel(AI_INSTRUMENTO_DEFAULT, force=force)
        if insertados == 0:
            flash("ℹ️ El instrumento ya estaba cargado. Usa Re-importar force si deseas recargarlo.", "info")
        else:
            flash(f"✅ Instrumento ISO 42001 importado correctamente. Preguntas cargadas: {insertados}.", "success")
    except Exception as e:
        flash(f"❌ Error importando instrumento: {e}", "danger")

    return redirect(url_for("madurez_ai.parametros"))


@ai_madurez_bp.route("/ingreso", methods=["GET"])
@login_required
def ingreso():
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para acceder al módulo de nivel de madurez de Gestión de Inteligencia Artificial.", "danger")
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El rol Auditor no puede ingresar la información en este módulo.", "warning")
        return redirect(url_for("madurez_ai.home"))

    preguntas = ai_cargar_preguntas()

    if not preguntas:
        flash("⚠️ Primero debes importar el instrumento ISO 42001.", "warning")
        return redirect(url_for("madurez_ai.parametros"))

    draft = ai_obtener_borrador(user.id if user else None)
    respuestas_guardadas = ai_cargar_respuestas(draft["id"]) if draft else {}
    consecutivo_val = (draft["consecutivo"] if draft else "") or ""

    _, _, progreso_inicial = ai_calcular_progreso(
        preguntas,
        respuestas_db=respuestas_guardadas
    )

    grouped = ai_group_questions()

    acc_html = []
    acc_id = 0

    def esc(x):
        return escape(x or "")

    for cap_name, cats in grouped.items():
        acc_id += 1
        func_key = f"func{acc_id}"
        inner = []

        for cat_code, payload in cats.items():
            rows = []

            for q in payload["items"]:
                qid = int(q["id"])
                saved = respuestas_guardadas.get(qid, {})
                saved_estado = (saved.get("estado") or "").strip().upper()
                saved_com = esc(saved.get("comentario") or "")
                qtext = q["pregunta"] or ""
                orden = q["orden"] or 0

                chk_na = "checked" if saved_estado == "NA" else ""
                chk_si = "checked" if saved_estado == "SI" else ""
                chk_pa = "checked" if saved_estado == "PARCIAL" else ""
                chk_no = "checked" if saved_estado == "NO" else ""

                rows.append(f"""
                <div class="col-12 col-xl-6">
                  <div class="nistform-qcard h-100">
                    <div class="nistform-qhead">
                      <div class="d-flex align-items-center gap-2 flex-wrap">
                        <span class="badge rounded-pill text-bg-light border fw-semibold">
                          {esc(cat_code)}
                        </span>
                        <span class="badge rounded-pill text-bg-primary">
                          Orden {orden}
                        </span>
                      </div>
                    </div>

                    <div class="nistform-qtext">
                      {esc(qtext)}
                    </div>

                    <div class="nistform-radio-row">
                      <label class="nistform-radio-card">
                        <input class="form-check-input" type="radio" name="st_{qid}" value="NA" {chk_na}>
                        <span>N/A</span>
                      </label>

                      <label class="nistform-radio-card">
                        <input class="form-check-input" type="radio" name="st_{qid}" value="SI" {chk_si}>
                        <span>Sí</span>
                      </label>

                      <label class="nistform-radio-card">
                        <input class="form-check-input" type="radio" name="st_{qid}" value="PARCIAL" {chk_pa}>
                        <span>Parcial</span>
                      </label>

                      <label class="nistform-radio-card">
                        <input class="form-check-input" type="radio" name="st_{qid}" value="NO" {chk_no}>
                        <span>No</span>
                      </label>
                    </div>

                    <div class="mt-3">
                      <label class="form-label small fw-bold text-black mb-1">Comentarios / evidencia</label>
                      <textarea class="form-control form-control-sm"
                                name="cm_{qid}"
                                rows="3"
                                placeholder="Comentarios / evidencia">{saved_com}</textarea>
                    </div>
                  </div>
                </div>
                """)

            inner.append(f"""
            <div class="nistform-cat-block">
              <div class="nistform-cat-title">
                <div>
                  <div class="nistform-cat-code">{esc(cat_code)}</div>
                  <div class="nistform-cat-name">{esc(payload.get('categoria', ''))}</div>
                </div>
                <div>
                  <span class="badge rounded-pill text-bg-secondary">{len(payload["items"])} preguntas</span>
                </div>
              </div>

              <div class="row g-3">
                {''.join(rows)}
              </div>
            </div>
            """)

        acc_html.append(f"""
        <div class="accordion-item nistform-acc-item">
          <h2 class="accordion-header" id="h{func_key}">
            <button class="accordion-button {'collapsed' if acc_id != 1 else ''} nistform-acc-btn"
                    type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#c{func_key}"
                    aria-expanded="{str(acc_id == 1).lower()}"
                    aria-controls="c{func_key}">
              <div class="nistform-acc-inner">
                <div class="nistform-acc-title-wrap">
                  <i class="bi bi-folder2-open me-2"></i>
                  <span class="nistform-acc-title">{esc(cap_name)}</span>
                </div>
                <span class="badge rounded-pill text-bg-light border">
                  {sum(len(v["items"]) for v in cats.values())} preguntas
                </span>
              </div>
            </button>
          </h2>

          <div id="c{func_key}"
               class="accordion-collapse collapse {'show' if acc_id == 1 else ''}">
            <div class="accordion-body nistform-acc-body">
              {''.join(inner)}
            </div>
          </div>
        </div>
        """)

    alerta_borrador = ""
    if draft:
        alerta_borrador = f"""
        <div class="alert alert-info rounded-4 border-0 shadow-sm">
          <i class="bi bi-info-circle-fill me-2"></i>
          Tienes un borrador cargado automáticamente.
          <strong>Progreso actual:</strong> {progreso_inicial}%.
        </div>
        """

    disabled_analizar = "" if progreso_inicial == 100 else "disabled"

    content = f"""
    <div class="nistform-shell">

      <div class="nistform-header-card">
        <div class="nistform-header-overlay">
          <div class="nistform-header-text">
            <h3 class="nistform-title m-0">Nivel de Madurez — Sistema de Gestión de Inteligencia Artificial</h3>
            <div class="nistform-subtitle">
              Registro de respuestas del instrumento de evaluación basado en
              ISO/IEC 42001 para el Sistema de Gestión de Inteligencia Artificial.
            </div>
          </div>
        </div>
      </div>

      <div class="nistform-header-actions">
        <a href="{url_for('madurez_ai.home')}"
           class="btn nistform-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver a Madurez IA
        </a>
      </div>

      <div class="nistform-card p-4">

        {alerta_borrador}

        <form id="nistIngresoForm"
              method="POST"
              action="{url_for('madurez_ai.guardar')}"
              novalidate
              autocomplete="off">

          <input type="hidden" name="draft_id" value="{draft['id'] if draft else ''}">

          <div class="nistform-section-title">
            Información de la revisión
          </div>

          <div class="mb-4">
            <label class="text-black form-label fw-semibold" for="nistConsecutivoRevision">
              Consecutivo de la Revisión <span class="text-danger">*</span>
            </label>

            <input type="text"
                   class="form-control"
                   name="consecutivo"
                   id="nistConsecutivoRevision"
                   value="{esc(consecutivo_val)}"
                   autocomplete="off"
                   required>

            <div id="nistConsecutivoRevisionError"
                 class="invalid-feedback d-none fw-bold mt-2">
              Debes ingresar el consecutivo de la Revisión.
            </div>
          </div>

          <div class="nistform-section-title">
            📊 Progreso del instrumento
          </div>

          <div class="mb-4">
            <div class="progress nistform-progress">
              <div id="nistProgressBar"
                   class="progress-bar progress-bar-striped progress-bar-animated"
                   role="progressbar"
                   style="width:{progreso_inicial}%"
                   aria-valuemin="0"
                   aria-valuemax="100"
                   aria-valuenow="{progreso_inicial}">
                {progreso_inicial}%
              </div>
            </div>

            <div class="text-center small text-muted mt-2">
              <span id="nistProgressText">{progreso_inicial}%</span> del instrumento completado
            </div>
          </div>

          <div class="nistform-section-title">
            Instrumento de evaluación
          </div>

          <div class="accordion nistform-accordion" id="accNist">
            {''.join(acc_html)}
          </div>

          <div class="d-flex justify-content-center gap-3 flex-wrap mt-4">
            <button id="btnGuardarNist"
                    class="btn btn-outline-primary btn-lg rounded-pill px-5 shadow fw-semibold nist-submit-btn"
                    type="submit"
                    name="accion"
                    value="guardar"
                    data-accion="guardar">
              <i class="bi bi-save2 me-2"></i>
              Guardar
            </button>

            <button id="btnAnalizarNist"
                    class="btn btn-primary btn-lg rounded-pill px-5 shadow fw-semibold nist-submit-btn"
                    type="submit"
                    name="accion"
                    value="analizar"
                    data-accion="analizar"
                    {disabled_analizar}>
              <i class="bi bi-bar-chart-line-fill me-2"></i>
              Analizar
            </button>
          </div>

        </form>

      </div>

    </div>

    <script>
    (function() {{

        let NIST_BLOQUEAR_LOADER = false;

        function nistOcultarLoaderGlobal() {{
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

        function nistValidarConsecutivoRevision() {{
            const input = document.getElementById("nistConsecutivoRevision");
            const error = document.getElementById("nistConsecutivoRevisionError");

            const valor = input ? input.value.trim() : "";

            if (!valor) {{
                NIST_BLOQUEAR_LOADER = true;
                nistOcultarLoaderGlobal();

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

            NIST_BLOQUEAR_LOADER = false;

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

        function actualizarProgresoNist() {{
            const radios = document.querySelectorAll('input[type="radio"][name^="st_"]');
            const nombres = [...new Set(Array.from(radios).map(r => r.name))];
            const total = nombres.length;

            let respondidas = 0;

            nombres.forEach(function(nombre) {{
                const marcado = document.querySelector('input[name="' + nombre + '"]:checked');
                if (marcado) {{
                    respondidas++;
                }}
            }});

            const porcentaje = total > 0 ? Math.round((respondidas / total) * 100) : 0;

            const bar = document.getElementById("nistProgressBar");
            const text = document.getElementById("nistProgressText");
            const btnAnalizar = document.getElementById("btnAnalizarNist");

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

            if (typeof original === "function" && !original.__nistInterceptado) {{
                const wrapper = function() {{
                    if (NIST_BLOQUEAR_LOADER || !nistValidarConsecutivoRevision()) {{
                        nistOcultarLoaderGlobal();
                        return false;
                    }}

                    return original.apply(this, arguments);
                }};

                wrapper.__nistInterceptado = true;
                window[nombreFuncion] = wrapper;
            }}
        }});

        document.addEventListener("change", function(e) {{
            if (e.target.matches('input[type="radio"][name^="st_"]')) {{
                actualizarProgresoNist();
            }}
        }});

        document.addEventListener("click", function(e) {{
            const btn = e.target.closest(".nist-submit-btn");

            if (!btn) {{
                return;
            }}

            if (!nistValidarConsecutivoRevision()) {{
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();

                NIST_BLOQUEAR_LOADER = true;
                nistOcultarLoaderGlobal();

                return false;
            }}
        }}, true);

        window.addEventListener("DOMContentLoaded", function() {{
            const form = document.getElementById("nistIngresoForm");
            const input = document.getElementById("nistConsecutivoRevision");

            if (input) {{
                input.addEventListener("input", function() {{
                    nistValidarConsecutivoRevision();
                }});

                input.addEventListener("blur", function() {{
                    nistValidarConsecutivoRevision();
                }});
            }}

            if (form) {{
                form.addEventListener("submit", function(e) {{
                    if (!nistValidarConsecutivoRevision()) {{
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();

                        NIST_BLOQUEAR_LOADER = true;
                        nistOcultarLoaderGlobal();

                        return false;
                    }}
                }}, true);
            }}

            actualizarProgresoNist();
            nistOcultarLoaderGlobal();
        }});

        window.addEventListener("pageshow", function() {{
            nistOcultarLoaderGlobal();
        }});

    }})();
    </script>

    <style>
      .bg-purple{{ background-color:#6f42c1 !important; }}
      .badge.bg-purple{{ color:#ffffff !important; }}

      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .nistform-shell{{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }}

      .nistform-header-card{{
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

      .nistform-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .nistform-header-overlay{{
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

      .nistform-header-overlay::before{{
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

      .nistform-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .nistform-header-text::before{{
        content:"SGSI · Evaluación ISO 42001";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .nistform-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .nistform-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .nistform-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .nistform-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .nistform-header-actions .btn{{
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .nistform-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .nistform-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }}

      .nistform-card,
      .card,
      .card-soft,
      .report-card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .nistform-card.p-4{{
        padding:1.5rem !important;
      }}

      .nistform-section-title{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
        margin-bottom:16px;
      }}

      .nistform-progress{{
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
      .form-select,
      .report-textarea{{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      textarea.form-control,
      .report-textarea{{
        min-height:90px;
      }}

      .form-control:focus,
      .form-select:focus,
      .report-textarea:focus{{
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

      .nistform-accordion{{
        --bs-accordion-border-color:transparent;
        --bs-accordion-btn-focus-box-shadow:0 0 0 .2rem rgba(63,134,214,.12);
      }}

      .nistform-acc-item,
      .accordion-item{{
        border:1px solid #dbe6f4 !important;
        border-radius:0 20px 20px 0 !important;
        overflow:hidden;
        margin-bottom:12px;
        background:#ffffff !important;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }}

      .nistform-acc-btn,
      .accordion-button{{
        background:#eef5ff !important;
        color:#0f172a !important;
        font-weight:900;
        padding:18px 22px !important;
        box-shadow:none !important;
        border-bottom:1px solid #dbe6f4;
      }}

      .nistform-acc-btn:not(.collapsed),
      .accordion-button:not(.collapsed){{
        background:#dbeafe !important;
        color:#0b4a8f !important;
        box-shadow:none !important;
      }}

      .nistform-acc-inner{{
        width:100%;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding-right:10px;
      }}

      .nistform-acc-title-wrap{{
        display:flex;
        align-items:center;
        gap:6px;
        min-width:0;
      }}

      .nistform-acc-title{{
        font-size:1rem;
        font-weight:950;
        color:#1e293b;
      }}

      .nistform-acc-body,
      .accordion-body{{
        background:rgba(255,255,255,.96) !important;
        padding:18px !important;
      }}

      .nistform-cat-block{{
        background:#f8fafc;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:16px;
        margin-bottom:16px;
      }}

      .nistform-cat-title{{
        display:flex;
        justify-content:space-between;
        align-items:flex-start;
        gap:12px;
        margin-bottom:14px;
        padding-bottom:10px;
        border-bottom:1px solid #dbe6f4;
      }}

      .nistform-cat-code{{
        font-size:.92rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1.15;
      }}

      .nistform-cat-name{{
        font-size:.78rem;
        color:#334155;
        margin-top:3px;
        line-height:1.25;
      }}

      .nistform-qcard{{
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 4px 10px rgba(15,23,42,.05);
        height:100%;
        transition:.2s ease;
      }}

      .nistform-qcard:hover{{
        transform:translateY(-2px);
        box-shadow:0 8px 20px rgba(15,23,42,.10);
      }}

      .nistform-qhead{{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:10px;
        margin-bottom:10px;
      }}

      .nistform-qtext{{
        font-size:.92rem;
        color:#0f172a;
        font-weight:700;
        line-height:1.45;
      }}

      .nistform-radio-row{{
        display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:10px;
        margin-top:14px;
      }}

      .nistform-radio-card{{
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

      .nistform-radio-card:hover{{
        background:#eef6ff;
        border-color:#93c5fd;
      }}

      .nistform-radio-card input[type="radio"]{{
        transform:scale(1.08);
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:1200px){{
        .nistform-radio-row{{
          grid-template-columns:repeat(2,1fr);
        }}
      }}

      @media (max-width:991.98px){{
        .nistform-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .nistform-header-card{{
          min-height:88px;
        }}

        .nistform-title{{
          font-size:1.20rem;
        }}

        .nistform-subtitle{{
          font-size:.68rem;
        }}
      }}

      @media (max-width:768px){{
        .nistform-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .nistform-header-overlay::before{{
          margin:0;
        }}

        .nistform-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .nistform-title,
        .nistform-subtitle{{
          text-align:center;
        }}

        .nistform-header-actions .btn{{
          width:100%;
        }}

        .nistform-acc-inner,
        .nistform-cat-title{{
          flex-direction:column;
          align-items:flex-start;
        }}

        .nistform-radio-row{{
          grid-template-columns:1fr;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Ingreso Madurez IA", content=content)


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
           class="btn aidet-btn-danger rounded-pill px-4 fw-bold">
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

