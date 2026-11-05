@pci_madurez_bp.route("/ingreso", methods=["GET"])
@login_required
def ingreso():
    user = User.query.get(session.get("user_id"))

    if user.role not in ("admin", "auditor") and not verificar_permiso(user, "Nivel de madurez PCI-DSS"):
        flash("No tiene permiso para acceder al módulo PCI-DSS.", "danger")
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El rol Auditor no puede ingresar la información en este módulo.", "warning")
        return redirect(url_for("madurez_pci.inicio_pci"))

    if PciMadurezPregunta.query.filter_by(tipo="q").count() == 0:
        flash("⚠️ Primero debes importar el instrumento PCI-DSS.", "warning")
        return redirect(url_for("madurez_pci.parametros"))

    draft = obtener_borrador_pci(user.id if user else None)
    respuestas_db = cargar_respuestas_pci(draft.id) if draft else {}

    preguntas = PciMadurezPregunta.query.order_by(PciMadurezPregunta.orden.asc()).all()
    preguntas_q = [p for p in preguntas if p.tipo == "q"]

    _, _, progreso_inicial = calcular_progreso_pci(
        preguntas_q,
        respuestas_db=respuestas_db
    )

    company_name = (draft.company_name if draft else "") or ""
    draft_id = draft.id if draft else ""
    tiene_consecutivo = bool(company_name.strip())

    bloques_map = {}
    bloque_actual = "SIN_BLOQUE"
    seccion_actual = "SIN_SECCION"

    for p in preguntas:
        bloque_codigo = (p.bloque_codigo or "SIN_BLOQUE").strip()
        bloque_nombre = (p.bloque_nombre or pci_block_title(bloque_codigo) or "Sin bloque").strip()

        if bloque_codigo not in bloques_map:
            bloques_map[bloque_codigo] = {
                "titulo": bloque_nombre,
                "secciones": {}
            }

        if p.tipo == "h":
            if p.seccion_codigo:
                seccion_actual = p.seccion_codigo.strip()
                bloques_map[bloque_codigo]["secciones"].setdefault(seccion_actual, {
                    "titulo": (p.seccion_nombre or p.pregunta or p.seccion_codigo).strip(),
                    "items": []
                })
            else:
                seccion_actual = "GENERAL"
                bloques_map[bloque_codigo]["secciones"].setdefault(seccion_actual, {
                    "titulo": "Preguntas del bloque",
                    "items": []
                })

            bloque_actual = bloque_codigo
            continue

        if p.tipo == "q":
            bloque_destino = bloque_codigo or bloque_actual or "SIN_BLOQUE"
            seccion_destino = (p.seccion_codigo or seccion_actual or "GENERAL").strip()

            if seccion_destino not in bloques_map[bloque_destino]["secciones"]:
                bloques_map[bloque_destino]["secciones"][seccion_destino] = {
                    "titulo": (p.seccion_nombre or p.seccion_codigo or "Preguntas").strip(),
                    "items": []
                }

            bloques_map[bloque_destino]["secciones"][seccion_destino]["items"].append(p)

    def esc(x):
        return escape(x or "")

    acc_html = []
    acc_id = 0

    for bloque_codigo in PCI_BLOCK_ORDER:
        data_bloque = bloques_map.get(bloque_codigo)

        if not data_bloque:
            continue

        acc_id += 1
        bloque_key = f"pci_bloque_{acc_id}"
        inner = []

        for _, sec in data_bloque["secciones"].items():
            items = sec.get("items", [])

            if not items:
                continue

            preguntas_html = []

            for q in items:
                saved = respuestas_db.get(q.id, {})
                saved_estado = (saved.get("estado") or "").strip().upper()
                saved_com = esc(saved.get("comentario") or "")
                pregunta_texto = (q.pregunta or "").strip()

                chk_na = "checked" if saved_estado == "NA" else ""
                chk_si = "checked" if saved_estado == "SI" else ""
                chk_pa = "checked" if saved_estado == "PARCIAL" else ""
                chk_no = "checked" if saved_estado == "NO" else ""

                preguntas_html.append(f"""
                <div class="col-12 col-xl-6">
                  <div class="pciform-qcard h-100">
                    <div class="pciform-qhead">
                      <div class="d-flex align-items-center gap-2 flex-wrap">
                        <span class="badge rounded-pill text-bg-light border fw-semibold">
                          {esc(q.seccion_codigo or bloque_codigo)}
                        </span>
                        <span class="badge rounded-pill text-bg-primary">
                          Orden {q.orden or 0}
                        </span>
                      </div>
                    </div>

                    <div class="pciform-qtext">
                      {esc(pregunta_texto)}
                    </div>

                    <div class="pciform-radio-row">
                      <label class="pciform-radio-card">
                        <input class="form-check-input pci-control-instrumento" type="radio" name="st_{q.id}" value="NA" {chk_na}>
                        <span>N/A</span>
                      </label>

                      <label class="pciform-radio-card">
                        <input class="form-check-input pci-control-instrumento" type="radio" name="st_{q.id}" value="SI" {chk_si}>
                        <span>Sí</span>
                      </label>

                      <label class="pciform-radio-card">
                        <input class="form-check-input pci-control-instrumento" type="radio" name="st_{q.id}" value="PARCIAL" {chk_pa}>
                        <span>Parcial</span>
                      </label>

                      <label class="pciform-radio-card">
                        <input class="form-check-input pci-control-instrumento" type="radio" name="st_{q.id}" value="NO" {chk_no}>
                        <span>No</span>
                      </label>
                    </div>

                    <div class="mt-3">
                      <label class="form-label small fw-bold text-black mb-1">Comentarios / evidencia</label>
                      <textarea class="form-control form-control-sm pci-control-instrumento"
                                name="c_{q.id}"
                                rows="3"
                                placeholder="Comentarios / evidencia">{saved_com}</textarea>
                    </div>
                  </div>
                </div>
                """)

            inner.append(f"""
            <div class="pciform-cat-block">
              <div class="pciform-cat-title">
                <div>
                  <div class="pciform-cat-code">{esc(sec.get("titulo") or "Sección")}</div>
                  <div class="pciform-cat-name">Preguntas de la sección</div>
                </div>
                <div>
                  <span class="badge rounded-pill text-bg-secondary">{len(items)} preguntas</span>
                </div>
              </div>

              <div class="row g-3">
                {''.join(preguntas_html)}
              </div>
            </div>
            """)

        acc_html.append(f"""
        <div class="accordion-item pciform-acc-item">
          <h2 class="accordion-header" id="h{bloque_key}">
            <button class="accordion-button {'collapsed' if acc_id != 1 else ''} pciform-acc-btn"
                    type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#c{bloque_key}"
                    aria-expanded="{str(acc_id == 1).lower()}"
                    aria-controls="c{bloque_key}">
              <div class="pciform-acc-inner">
                <div class="pciform-acc-title-wrap">
                  <i class="bi bi-folder2-open me-2"></i>
                  <span class="pciform-acc-title">{esc(data_bloque["titulo"])}</span>
                </div>
                <span class="badge rounded-pill text-bg-light border">
                  {sum(len(v["items"]) for v in data_bloque["secciones"].values())} preguntas
                </span>
              </div>
            </button>
          </h2>

          <div id="c{bloque_key}" class="accordion-collapse collapse {'show' if acc_id == 1 else ''}">
            <div class="accordion-body pciform-acc-body">
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

    disabled_analizar = "" if progreso_inicial == 100 and tiene_consecutivo else "disabled"

    content = f"""
    <div class="pciform-shell">

      <div class="pciform-header-card">
        <div class="pciform-header-overlay">
          <div class="pciform-header-text">
            <h3 class="pciform-title m-0">Diligenciamiento del Formulario</h3>
            <div class="pciform-subtitle">
              Registro de respuestas del instrumento de evaluación basado en
              los 12 requerimientos y los apéndices A1 y A2 de PCI-DSS.
            </div>
          </div>
        </div>
      </div>

      <div class="pciform-header-actions">
          <a href="{url_for('madurez_pci.inicio_pci')}"
             class="btn pciform-btn-main rounded-pill px-4 fw-bold">
            <i class="bi bi-arrow-left me-2"></i>Volver a Madurez PCI-DSS
          </a>
      </div>

      <div class="pciform-card p-4">

        {alerta_borrador}

        <form id="pciIngresoForm"
              method="POST"
              action="{url_for('madurez_pci.ingreso_guardar_pci')}"
              novalidate
              autocomplete="off"
              onsubmit="return pciValidarAntesDeEnviar(event);">

          <input type="hidden" name="draft_id" value="{draft_id}">

          <div class="pciform-section-title">
            Información de la revisión
          </div>

          <div class="mb-4">
            <label class="text-black form-label fw-semibold" for="pciConsecutivoRevision">
              Consecutivo de la revisión <span class="text-danger">*</span>
            </label>

            <input type="text"
                   class="form-control"
                   name="company_name"
                   id="pciConsecutivoRevision"
                   value="{esc(company_name)}"
                   autocomplete="off"
                   required
                   oninput="pciActualizarBloqueoPorConsecutivo();"
                   onblur="pciValidarConsecutivoRevision();">

            <div id="pciConsecutivoRevisionError"
                 class="invalid-feedback d-none fw-bold mt-2">
              Debes ingresar el consecutivo de la Revisión.
            </div>

            <div id="pciBloqueoAviso"
                 class="alert alert-warning rounded-4 mt-3 {'d-none' if tiene_consecutivo else ''}">
              <i class="bi bi-exclamation-triangle-fill me-2"></i>
              Primero debes ingresar el <strong>Consecutivo de la revisión</strong> para habilitar el instrumento.
            </div>
          </div>

          <div class="pciform-section-title">
            📊 Progreso del instrumento
          </div>

          <div class="mb-4">
            <div class="progress pciform-progress">
              <div id="pciProgressBar"
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
              <span id="pciProgressText">{progreso_inicial}%</span> del instrumento completado
            </div>
          </div>

          <div id="pciZonaInstrumento" class="{'pci-zona-bloqueada' if not tiene_consecutivo else ''}">
            <div class="pciform-section-title">
              Instrumento de evaluación
            </div>

            <div class="accordion pciform-accordion" id="accPCI">
              {''.join(acc_html)}
            </div>
          </div>

          <div class="d-flex justify-content-center gap-3 flex-wrap mt-4">
            <button id="btnGuardarPCI"
                    class="btn btn-outline-primary btn-lg rounded-pill px-5 shadow fw-semibold pci-submit-btn"
                    type="submit"
                    name="accion"
                    value="guardar"
                    data-accion="guardar"
                    onclick="return pciValidarAntesDeEnviar(event);">
              <i class="bi bi-save2 me-2"></i>
              Guardar
            </button>

            <button id="btnAnalizarPCI"
                    class="btn btn-primary btn-lg rounded-pill px-5 shadow fw-semibold pci-submit-btn"
                    type="submit"
                    name="accion"
                    value="analizar"
                    data-accion="analizar"
                    onclick="return pciValidarAntesDeEnviar(event);"
                    {disabled_analizar}>
              <i class="bi bi-bar-chart-line-fill me-2"></i>
              Analizar
            </button>
          </div>

        </form>

      </div>

    </div>

    <script>
    var PCI_BLOQUEAR_LOADER = true;

    function pciOcultarLoaderGlobal() {{
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

    function pciTieneConsecutivo() {{
        const input = document.getElementById("pciConsecutivoRevision");
        return !!(input && input.value && input.value.trim().length > 0);
    }}

    function pciValidarConsecutivoRevision() {{
        const input = document.getElementById("pciConsecutivoRevision");
        const error = document.getElementById("pciConsecutivoRevisionError");

        if (!pciTieneConsecutivo()) {{
            PCI_BLOQUEAR_LOADER = true;
            pciOcultarLoaderGlobal();

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

        PCI_BLOQUEAR_LOADER = false;

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

    function pciActualizarBloqueoPorConsecutivo() {{
        const habilitar = pciTieneConsecutivo();
        const zona = document.getElementById("pciZonaInstrumento");
        const aviso = document.getElementById("pciBloqueoAviso");
        const btnGuardar = document.getElementById("btnGuardarPCI");

        PCI_BLOQUEAR_LOADER = !habilitar;

        document.querySelectorAll(".pci-control-instrumento").forEach(function(el) {{
            el.disabled = !habilitar;
        }});

        if (zona) {{
            zona.classList.toggle("pci-zona-bloqueada", !habilitar);
        }}

        if (aviso) {{
            aviso.classList.toggle("d-none", habilitar);
        }}

        if (btnGuardar) {{
            btnGuardar.disabled = !habilitar;
            btnGuardar.classList.toggle("disabled", !habilitar);
        }}

        actualizarProgresoPCI();

        if (!habilitar) {{
            pciOcultarLoaderGlobal();
        }}
    }}

    function actualizarProgresoPCI() {{
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

        const bar = document.getElementById("pciProgressBar");
        const text = document.getElementById("pciProgressText");
        const btnAnalizar = document.getElementById("btnAnalizarPCI");

        if (bar) {{
            bar.style.width = porcentaje + "%";
            bar.innerText = porcentaje + "%";
            bar.setAttribute("aria-valuenow", porcentaje);
        }}

        if (text) {{
            text.innerText = porcentaje + "%";
        }}

        if (btnAnalizar) {{
            const bloquear = !pciTieneConsecutivo() || porcentaje < 100;
            btnAnalizar.disabled = bloquear;
            btnAnalizar.classList.toggle("disabled", bloquear);
        }}
    }}

    function pciValidarAntesDeEnviar(e) {{
        if (!pciValidarConsecutivoRevision()) {{
            if (e) {{
                e.preventDefault();
                e.stopPropagation();
                if (typeof e.stopImmediatePropagation === "function") {{
                    e.stopImmediatePropagation();
                }}
            }}

            PCI_BLOQUEAR_LOADER = true;
            pciOcultarLoaderGlobal();
            return false;
        }}

        PCI_BLOQUEAR_LOADER = false;
        return true;
    }}

    document.addEventListener("change", function(e) {{
        if (!pciTieneConsecutivo() && e.target.matches(".pci-control-instrumento")) {{
            e.preventDefault();
            e.stopPropagation();
            pciValidarConsecutivoRevision();
            return false;
        }}

        if (e.target.matches('input[type="radio"][name^="st_"]')) {{
            actualizarProgresoPCI();
        }}
    }}, true);

    document.addEventListener("click", function(e) {{
        const objetivo = e.target;

        if (!pciTieneConsecutivo()) {{
            if (
                objetivo.closest(".pci-submit-btn") ||
                objetivo.closest(".pciform-radio-card") ||
                objetivo.closest("#pciZonaInstrumento")
            ) {{
                e.preventDefault();
                e.stopPropagation();
                if (typeof e.stopImmediatePropagation === "function") {{
                    e.stopImmediatePropagation();
                }}

                pciValidarConsecutivoRevision();
                pciOcultarLoaderGlobal();
                return false;
            }}
        }}
    }}, true);

    window.addEventListener("DOMContentLoaded", function() {{
        pciActualizarBloqueoPorConsecutivo();
        actualizarProgresoPCI();
        pciOcultarLoaderGlobal();
    }});

    window.addEventListener("pageshow", function() {{
        pciActualizarBloqueoPorConsecutivo();
        pciOcultarLoaderGlobal();
    }});

    const pciLoadersExternos = [
        "showLoader",
        "mostrarLoader",
        "showGlobalLoader",
        "mostrarProgresoGlobal",
        "showProgress",
        "openLoader",
        "activarLoader",
        "SGSI_showLoader"
    ];

    pciLoadersExternos.forEach(function(nombreFuncion) {{
        const original = window[nombreFuncion];

        if (typeof original === "function" && !original.__pciInterceptado) {{
            const wrapper = function() {{
                if (PCI_BLOQUEAR_LOADER || !pciTieneConsecutivo()) {{
                    pciValidarConsecutivoRevision();
                    pciOcultarLoaderGlobal();
                    return false;
                }}

                return original.apply(this, arguments);
            }};

            wrapper.__pciInterceptado = true;
            window[nombreFuncion] = wrapper;
        }}
    }});
    </script>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .pciform-shell{{
        width:96%;
        max-width:1700px;
        margin:26px auto 24px auto;
      }}

      .pciform-header-card{{
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

      .pciform-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .pciform-header-overlay{{
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

      .pciform-header-overlay::before{{
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

      .pciform-header-text::before{{
        content:"SGSI · Evaluación PCI-DSS";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .pciform-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .pciform-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
      }}

      .pciform-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .pciform-btn-main{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
        font-weight:900;
      }}

      .pciform-card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
        padding:1.5rem !important;
      }}

      .pciform-section-title{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:14px;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }}

      .pciform-progress{{
        height:22px;
        border-radius:999px;
        overflow:hidden;
        background:#e5edf7;
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
      }}

      .form-control{{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        background:#f8fafc;
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

      .pci-zona-bloqueada{{
        opacity:.45;
        filter:grayscale(.25);
        pointer-events:none;
        user-select:none;
      }}

      .pciform-acc-item{{
        border:1px solid #dbe6f4 !important;
        background:#ffffff !important;
        margin-bottom:14px;
        border-radius:18px !important;
        overflow:hidden;
      }}

      .pciform-acc-btn{{
        background:#eef5ff !important;
        color:#0f172a !important;
        font-weight:900;
        padding:18px 22px !important;
      }}

      .pciform-acc-inner{{
        width:100%;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
      }}

      .pciform-cat-block{{
        background:#f8fafc;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:16px;
        margin-bottom:16px;
      }}

      .pciform-cat-title{{
        display:flex;
        justify-content:space-between;
        gap:12px;
        margin-bottom:14px;
        padding-bottom:10px;
        border-bottom:1px solid #dbe6f4;
      }}

      .pciform-cat-code{{
        font-size:.92rem;
        font-weight:950;
        color:#0b4a8f;
      }}

      .pciform-qcard{{
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
      }}

      .pciform-qtext{{
        font-size:.92rem;
        color:#0f172a;
        font-weight:700;
        line-height:1.45;
      }}

      .pciform-radio-row{{
        display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:10px;
        margin-top:14px;
      }}

      .pciform-radio-card{{
        display:flex;
        align-items:center;
        justify-content:center;
        gap:6px;
        background:#f8fafc;
        border:1px solid #dbe4ee;
        border-radius:12px;
        min-height:46px;
        font-weight:900;
        cursor:pointer;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:1200px){{
        .pciform-radio-row{{
          grid-template-columns:repeat(2,1fr);
        }}
      }}

      @media (max-width:768px){{
        .pciform-radio-row{{
          grid-template-columns:1fr;
        }}

        .pciform-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Ingreso PCI-DSS", content=content)

# =====================================================================
# PARÁMETROS PCI-DSS
# =====================================================================

@pci_madurez_bp.route("/parametros", methods=["GET"], endpoint="parametros")
@login_required
def parametros():
    user = User.query.get(session.get("user_id"))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez PCI-DSS"):
        flash("No tiene permiso para acceder a los parámetros de PCI-DSS.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == 'auditor')

    # Botón importar
    if read_only:
        importar_btn = """
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled
                  title="El rol Auditor no puede importar instrumentos">
            <i class="bi bi-upload me-2"></i>Importar instrumento
          </button>
        """
        reimportar_btn = ""
    else:
        importar_btn = f"""
          <form method="POST" action="{url_for('madurez_pci.importar_instrumento_pci')}" class="d-inline">
            <button type="submit" class="btn btn-primary rounded-pill px-4 fw-bold">
              <i class="bi bi-upload me-2"></i>Importar instrumento
            </button>
          </form>
        """
        reimportar_btn = f"""
          <form method="POST"
                action="{url_for('madurez_pci.importar_instrumento_pci')}?force=1"
                class="d-inline"
                onsubmit="return confirm('Esto borrará el instrumento PCI cargado y lo volverá a importar. ¿Desea continuar?');">
            <button type="submit" class="btn btn-outline-danger rounded-pill px-4 fw-bold">
              <i class="bi bi-arrow-repeat me-2"></i>Reimportar instrumento
            </button>
          </form>
        """

    params = PciMadurezParametro.query.order_by(PciMadurezParametro.orden.asc()).all()
    total_preguntas = PciMadurezPregunta.query.filter_by(tipo="q").count()

    rows = ""
    for p in params:
        rows += f"""
        <tr>
          <td class="text-center fw-bold">{p.orden}</td>
          <td class="fw-semibold">{xml_escape(p.nivel)}</td>
          <td class="text-center">{float(p.rango_desde):.2f}%</td>
          <td class="text-center">{float(p.rango_hasta):.2f}%</td>
          <td class="text-center">
              <span class="badge rounded-pill px-3 py-2"
                    style="background:{p.color or '#6c757d'};">
              </span>
           </td>
          <td>{xml_escape(p.descripcion or '')}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
          <td colspan="6" class="text-center text-muted py-4">
            No hay parámetros cargados aún.
          </td>
        </tr>
        """

    estado_badge = (
        '<span class="badge bg-success ms-2">Instrumento cargado</span>'
        if total_preguntas > 0 else
        '<span class="badge bg-danger ms-2">Instrumento NO cargado</span>'
    )

    content = f"""
    <div class="pcipar-shell">

      <div class="pcipar-header-card">
        <div class="pcipar-header-overlay">
          <div class="pcipar-header-text">
            <h3 class="pcipar-title m-0">Parámetros — Nivel de Madurez PCI-DSS</h3>
            <div class="pcipar-subtitle">
              Configuración base del instrumento, escala de medición y administración de la importación del cuestionario.
            </div>
          </div>
        </div>
      </div>

      <div class="pcipar-header-actions">
        <a href="{url_for('madurez_pci.inicio_pci')}" class="btn pcipar-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left-circle me-2"></i>Volver
        </a>
        {importar_btn}
        {reimportar_btn}
      </div>

      <div class="row g-3 mt-2">
        <div class="col-12 col-lg-4">
          <div class="pcipar-card p-4 h-100">
            <div class="pcipar-section-title">Estado del instrumento</div>
            <div class="fw-bold">Preguntas evaluables: <b>{total_preguntas}</b> {estado_badge}</div>
            <div class="mt-3 small text-muted">
              El instrumento se importa desde el archivo Excel de PCI-DSS sin traducción, respetando los textos originales.
            </div>

            <div class="alert alert-info mt-3 mb-0 small">
              <b>Nota:</b> la reimportación elimina las preguntas PCI actuales y vuelve a cargar el instrumento desde cero.
            </div>
          </div>
        </div>

        <div class="col-12 col-lg-8">
          <div class="pcipar-card p-4 h-100">
            <div class="pcipar-section-title">Escala de madurez</div>
            <div class="table-responsive">
              <table class="table table-sm align-middle mb-0">
                <thead>
                  <tr>
                    <th class="text-center">Orden</th>
                    <th>Nivel</th>
                    <th class="text-center">Desde</th>
                    <th class="text-center">Hasta</th>
                    <th class="text-center">Color</th>
                    <th>Descripción</th>
                  </tr>
                </thead>
                <tbody>
                  {rows}
                </tbody>
              </table>
            </div>
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

      .pcipar-shell{{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }}

      .pcipar-header-card{{
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

      .pcipar-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .pcipar-header-overlay{{
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

      .pcipar-header-overlay::before{{
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

      .pcipar-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .pcipar-header-text::before{{
        content:"SGSI · Parámetros PCI-DSS";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .pcipar-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .pcipar-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .pcipar-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .pcipar-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .pcipar-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .pcipar-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .pcipar-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .pcipar-card.p-4{{
        padding:1.5rem !important;
      }}

      .pcipar-section-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
      }}

      .pcipar-section-title{{
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

      .table{{
        margin-bottom:0;
      }}

      .pcipar-card table thead th,
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

      table td,
      table th,
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

      .pcipar-card table tbody tr:hover,
      .table tbody tr:hover{{
        background:#eef6ff;
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
        .pcipar-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .pcipar-header-card{{
          min-height:88px;
        }}

        .pcipar-title{{
          font-size:1.20rem;
        }}

        .pcipar-subtitle{{
          font-size:.68rem;
        }}
      }}

      @media (max-width:768px){{
        .pcipar-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .pcipar-header-overlay::before{{
          margin:0;
        }}

        .pcipar-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .pcipar-title,
        .pcipar-subtitle{{
          text-align:center;
        }}

        .pcipar-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Parámetros PCI-DSS", content=content)

# =====================================================================
# HISTORIAL PCI-DSS
# =====================================================================

@pci_madurez_bp.route("/historial", methods=["GET"], endpoint="historial")
@login_required
def historial():
    user = User.query.get(session.get("user_id"))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Nivel de madurez PCI-DSS"):
        flash("No tiene permiso para acceder al historial de PCI-DSS.", "danger")
        return redirect(url_for('menu'))

    runs = (
        PciAnalysisRun.query
        .order_by(PciAnalysisRun.fecha_calculo.desc(), PciAnalysisRun.id.desc())
        .limit(200)
        .all()
    )

    rows = ""
    for r in runs:
        nivel = pci_resolver_nivel(r.nivel_promedio_general or 0)

        if user.role == 'auditor':
            boton_eliminar = ""
        else:
            company_name_safe = escape(r.company_name or '')
            eliminar_url = url_for('madurez_pci.historial_eliminar', run_id=r.id)
            boton_eliminar = f"""
                <form method="POST"
                      action="{eliminar_url}"
                      class="m-0"
                      onsubmit="return confirm('¿Seguro que deseas eliminar esta revisión PCI-DSS?\\n\\nConsecutivo: {company_name_safe}');">
                  <button class="btn btn-sm btn-danger rounded-pill" type="submit">
                    <i class="bi bi-trash3 me-1"></i>Eliminar
                  </button>
                </form>
            """

        rows += f"""
        <tr>
          <td>{escape(r.fecha_calculo.strftime('%Y-%m-%d %H:%M')) if r.fecha_calculo else ''}</td>
          <td>{escape(r.company_name or '')}</td>
          <td class="text-center">
            <div class="d-flex flex-column align-items-center justify-content-center">
              <div class="fw-bold">{float(r.nivel_promedio_general or 0):.2f}%</div>
              <div class="d-flex align-items-center gap-2 mt-1 flex-wrap justify-content-center">
                <span class="badge rounded-pill" style="background:{nivel['color']}; font-size:11px;">
                  {escape(nivel['nivel'])}
                </span>
              </div>
            </div>
          </td>
          <td class="text-center">
            <div class="d-flex justify-content-center gap-2 flex-nowrap">
              <a class="btn btn-sm btn-primary rounded-pill"
                 href="{url_for('madurez_pci.resultado', run_id=r.id)}">
                <i class="bi bi-eye me-1"></i>Ver
              </a>

              <a class="btn btn-sm btn-outline-danger rounded-pill"
                 href="{url_for('madurez_pci.exportar_pdf', run_id=r.id)}" target="_blank">
                <i class="bi bi-file-earmark-pdf me-1"></i>PDF
              </a>

              {boton_eliminar}
            </div>
          </td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
          <td colspan="4" class="text-center text-muted py-4">
            No hay revisiones PCI-DSS registradas.
          </td>
        </tr>
        """

    content = f"""
    <div class="pcihist-shell">

      <div class="pcihist-header-card">
        <div class="pcihist-header-overlay">
          <div class="pcihist-header-text">
            <h3 class="pcihist-title m-0">Historial de Revisiones — PCI-DSS</h3>
            <div class="pcihist-subtitle">
              Consulta las evaluaciones ejecutadas, porcentajes de madurez y acciones disponibles.
            </div>
          </div>
        </div>
      </div>

      <div class="pcihist-header-actions">
        <a href="{url_for('madurez_pci.inicio_pci')}" class="btn pcihist-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left-circle me-2"></i>Volver al Inicio
        </a>
      </div>

      <div class="pcihist-card p-4">
        <div class="pcihist-section-title">Listado de revisiones</div>

        <div class="table-responsive">
          <table class="table align-middle mb-0">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Consecutivo</th>
                <th class="text-center">Madurez General</th>
                <th class="text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {rows}
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

      .pcihist-shell{{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }}

      .pcihist-header-card{{
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

      .pcihist-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .pcihist-header-overlay{{
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

      .pcihist-header-overlay::before{{
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

      .pcihist-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .pcihist-header-text::before{{
        content:"SGSI · Historial PCI-DSS";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .pcihist-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .pcihist-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .pcihist-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .pcihist-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .pcihist-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .pcihist-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .pcihist-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .pcihist-card.p-4{{
        padding:1.5rem !important;
      }}

      .pcihist-section-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
      }}

      .pcihist-section-title{{
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

      .table{{
        margin-bottom:0;
      }}

      .pcihist-card table thead th,
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

      table td,
      table th,
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

      .pcihist-card table tbody tr:hover,
      .table tbody tr:hover{{
        background:#eef6ff;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
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
        .pcihist-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .pcihist-header-card{{
          min-height:88px;
        }}

        .pcihist-title{{
          font-size:1.20rem;
        }}

        .pcihist-subtitle{{
          font-size:.68rem;
        }}
      }}

      @media (max-width:768px){{
        .pcihist-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .pcihist-header-overlay::before{{
          margin:0;
        }}

        .pcihist-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .pcihist-title,
        .pcihist-subtitle{{
          text-align:center;
        }}

        .pcihist-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Historial PCI-DSS", content=content)

# =====================================================================
# ELIMINAR REVISIÓN PCI-DSS
# =====================================================================

@pci_madurez_bp.route("/historial/<int:run_id>/eliminar", methods=["POST"], endpoint="historial_eliminar")
@login_required
def historial_eliminar(run_id):
    user = User.query.get(session.get("user_id"))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar revisiones.", "danger")
        return redirect(url_for('madurez_pci.historial'))

    if user.role != 'admin' and not verificar_permiso(user, "Nivel de madurez PCI-DSS"):
        flash("No tiene permiso para eliminar revisiones PCI-DSS.", "danger")
        return redirect(url_for('madurez_pci.historial'))

    ar = PciAnalysisRun.query.get_or_404(run_id)
    run_base = PciMadurezRun.query.filter_by(id=ar.pci_run_id).first()

    try:
        db.session.delete(ar)

        if run_base:
            PciMadurezRespuesta.query.filter_by(run_id=run_base.id).delete()
            db.session.delete(run_base)

        db.session.commit()
        flash("✅ Revisión PCI-DSS eliminada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"⚠️ Error eliminando la revisión PCI-DSS: {e}", "danger")

    return redirect(url_for('madurez_pci.historial'))


@pci_madurez_bp.route("/resultado/<int:run_id>/plan-trabajo/editar", methods=["GET", "POST"])
@login_required
def plan_trabajo_editar_pci(run_id: int):
    user = User.query.get(session.get("user_id"))

    if user.role not in ("admin", "auditor") and not verificar_permiso(user, "Nivel de madurez PCI-DSS"):
        flash("No tiene permiso para editar el plan de trabajo de PCI-DSS.", "danger")
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede editar el plan de trabajo.", "danger")
        return redirect(url_for("madurez_pci.resultado", run_id=run_id))

    run = PciAnalysisRun.query.get_or_404(run_id)
    texto_actual = (run.plan_trabajo_editado or run.plan_trabajo_ai or "").strip()

    if request.method == "POST":
        texto = (request.form.get("plan_trabajo") or "").strip()
        run.plan_trabajo_editado = texto
        db.session.commit()
        flash("✅ Plan de trabajo PCI-DSS actualizado.", "success")
        return redirect(url_for("madurez_pci.resultado", run_id=run.id))

    content = f"""
    <div class="datstd-shell">

      <!-- HEADER -->
      <div class="datstd-header-card">
        <div class="datstd-header-overlay">
          <div class="datstd-header-text">
            <h3 class="datstd-title m-0">Editar Plan de Trabajo — PCI-DSS</h3>
            <div class="datstd-subtitle">
              Revisión: <b>{escape(run.company_name or '')}</b>
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="datstd-header-actions">
        <a href="{url_for('madurez_pci.resultado', run_id=run.id)}"
           class="btn datstd-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al resultado
        </a>
      </div>

      <!-- CARD -->
      <div class="datstd-card p-4">
        <form method="POST">

          <div class="datstd-section-title">Plan de trabajo editable</div>

          <div class="text-muted small mb-3">
            Ajusta el contenido del plan de trabajo PCI-DSS y guarda los cambios.
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
      body {{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .datstd-shell {{
        width:96%;
        max-width:1600px;
        margin:26px auto 30px auto;
      }}

      .datstd-header-card {{
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

      .datstd-header-card::before {{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .datstd-header-overlay {{
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

      .datstd-header-overlay::before {{
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

      .datstd-header-text {{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .datstd-header-text::before {{
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

      .datstd-title {{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .datstd-subtitle {{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .datstd-header-actions {{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 16px;
      }}

      .datstd-header-actions .btn,
      .btn {{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .datstd-btn-main,
      .btn-outline-light {{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .datstd-btn-main:hover,
      .btn-outline-light:hover {{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .datstd-card,
      .card {{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .datstd-card.p-4 {{
        padding:1.5rem !important;
      }}

      .datstd-section-title,
      .card h5,
      .card h6 {{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
      }}

      .datstd-section-title {{
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }}

      .datstd-textarea,
      textarea.form-control {{
        min-height:420px;
        border-radius:14px;
        border:1px solid #d9e3f0;
        resize:vertical;
        background:#f8fafc;
        font-size:.90rem;
        line-height:1.45;
        box-shadow:none !important;
      }}

      .datstd-textarea:focus,
      textarea.form-control:focus {{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .form-label {{
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
      .form-select {{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      .form-control:focus,
      .form-select:focus {{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .badge {{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      .btn.rounded-pill {{
        border-radius:999px !important;
      }}

      @media (max-width:991.98px) {{
        .datstd-shell {{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .datstd-header-card {{
          min-height:88px;
        }}

        .datstd-title {{
          font-size:1.20rem;
        }}

        .datstd-subtitle {{
          font-size:.68rem;
        }}

        .datstd-textarea {{
          min-height:320px;
        }}
      }}

      @media (max-width:768px) {{
        .datstd-header-overlay {{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .datstd-header-overlay::before {{
          margin:0;
        }}

        .datstd-header-text::before {{
          margin-left:auto;
          margin-right:auto;
        }}

        .datstd-title,
        .datstd-subtitle {{
          text-align:center;
        }}

        .datstd-header-actions .btn {{
          width:100%;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Editar Plan de Trabajo PCI-DSS", content=content)

@pci_madurez_bp.route("/resultado/<int:run_id>/plan-trabajo/generar", methods=["POST"])
@login_required
def plan_trabajo_generar_pci(run_id: int):
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede generar el plan de trabajo con IA.", "danger")
        return redirect(url_for("madurez_pci.resultado", run_id=run_id))

    if user.role != "admin" and not verificar_permiso(user, "Nivel de madurez PCI-DSS"):
        flash("No tiene permiso para generar el plan de trabajo de PCI-DSS.", "danger")
        return redirect(url_for("menu"))

    run = PciAnalysisRun.query.get_or_404(run_id)

    try:
        resultados = json.loads(run.resultados_json or "{}")
    except Exception:
        resultados = {}

    if not resultados:
        flash("⚠️ No hay resultados consolidados para generar el plan de trabajo.", "warning")
        return redirect(url_for("madurez_pci.resultado", run_id=run.id))

    prompt = _pci_prompt_plan_trabajo(run, resultados)

    try:
        raw = _ai_text(prompt, max_tokens=1800)
    except Exception as e:
        flash(f"❌ Error llamando IA para el plan de trabajo: {e}", "danger")
        return redirect(url_for("madurez_pci.resultado", run_id=run.id))

    obj = _extraer_json_objeto(raw)

    plan_ai = ""
    if isinstance(obj, dict):
        plan_list = obj.get("plan_trabajo", [])
        if isinstance(plan_list, list):
            lines = []
            for i, it in enumerate(plan_list, start=1):
                if not isinstance(it, dict):
                    continue

                frente = pci_normalizar_texto_rico_guardado(it.get("frente") or "")
                actividad = pci_normalizar_texto_rico_guardado(it.get("actividad") or "")
                prioridad = pci_normalizar_texto_rico_guardado(it.get("prioridad") or "")
                responsable = pci_normalizar_texto_rico_guardado(it.get("responsable_sugerido") or "")
                plazo = pci_normalizar_texto_rico_guardado(it.get("plazo") or "")
                entregable = pci_normalizar_texto_rico_guardado(it.get("entregable") or "")

                lines.append(
                    f"{i}. Frente: {frente or 'Sin definir'}\n"
                    f"   Actividad: {actividad or 'Sin definir'}\n"
                    f"   Prioridad: {prioridad or 'Sin definir'}\n"
                    f"   Responsable sugerido: {responsable or 'Sin definir'}\n"
                    f"   Plazo: {plazo or 'Sin definir'}\n"
                    f"   Entregable: {entregable or 'Sin definir'}"
                )

            plan_ai = "\n\n".join(lines).strip()

    plan_ai = pci_normalizar_texto_rico_guardado(plan_ai)

    if not plan_ai:
        flash("⚠️ La IA respondió, pero no devolvió un plan_trabajo JSON válido. Regenera nuevamente.", "warning")
        return redirect(url_for("madurez_pci.resultado", run_id=run.id))

    run.plan_trabajo_ai = plan_ai
    run.plan_trabajo_editado = plan_ai

    db.session.commit()
    flash("✅ Plan de trabajo PCI-DSS generado con IA.", "success")
    return redirect(url_for("madurez_pci.resultado", run_id=run.id))

@pci_madurez_bp.route("/resultado/<int:run_id>/informe-ejecutivo/editar", methods=["GET", "POST"])
@login_required
def informe_ejecutivo_editar_pci(run_id: int):
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El perfil Auditor no puede editar el informe ejecutivo.", "danger")
        return redirect(url_for("madurez_pci.resultado", run_id=run_id))

    if user.role != "admin" and not verificar_permiso(user, "Nivel de madurez PCI-DSS"):
        flash("No tiene permiso para editar el informe ejecutivo PCI-DSS.", "danger")
        return redirect(url_for("menu"))

    run = PciAnalysisRun.query.get_or_404(run_id)
    texto_actual = (run.informe_ejecutivo_editado or run.informe_ejecutivo_ai or "").strip()

    if request.method == "POST":
        texto = (request.form.get("informe_ejecutivo") or "").strip()

        print("=== DEBUG EDITAR INFORME PCI ===")
        print("run_id:", run.id)
        print("texto recibido:", texto[:500])
        print("antes run.informe_ejecutivo_editado:", (run.informe_ejecutivo_editado or "")[:500])

        run.informe_ejecutivo_editado = texto
        db.session.add(run)
        db.session.flush()
        db.session.commit()

        # Recargar desde BD para validar que sí quedó guardado
        db.session.refresh(run)

        print("despues run.informe_ejecutivo_editado:", (run.informe_ejecutivo_editado or "")[:500])
        print("=== FIN DEBUG EDITAR INFORME PCI ===")

        flash("✅ Informe ejecutivo PCI-DSS actualizado.", "success")
        return redirect(url_for("madurez_pci.resultado", run_id=run.id))

    content = f"""
    <div class="pciexec-shell">

      <div class="pciexec-header-card">
        <div class="pciexec-header-overlay">
          <div class="pciexec-header-text">
            <h3 class="pciexec-title m-0">Editar Informe Ejecutivo — PCI-DSS</h3>
            <div class="pciexec-subtitle">
              Revisión: <b>{escape(run.company_name or '')}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="pciexec-header-actions">
        <a href="{url_for('madurez_pci.resultado', run_id=run.id)}"
           class="btn pciexec-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al resultado
        </a>
      </div>

      <div class="pciexec-card p-4">
        <form method="POST">
          <div class="pciexec-section-title">Informe ejecutivo editable</div>

          <div class="text-muted small mb-3">
            Ajusta el contenido del informe ejecutivo y guarda los cambios.
          </div>

          <textarea name="informe_ejecutivo"
                    class="form-control pciexec-textarea"
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
      body {{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .pciexec-shell {{
        width:96%;
        max-width:1600px;
        margin:26px auto 30px auto;
      }}

      .pciexec-header-card {{
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

      .pciexec-header-card::before {{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .pciexec-header-overlay {{
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

      .pciexec-header-overlay::before {{
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

      .pciexec-header-text {{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .pciexec-header-text::before {{
        content:"SGSI · Informe Ejecutivo PCI-DSS";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .pciexec-title {{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .pciexec-subtitle {{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .pciexec-header-actions {{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 16px;
      }}

      .pciexec-header-actions .btn,
      .btn {{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .pciexec-btn-main,
      .btn-outline-light {{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .pciexec-btn-main:hover,
      .btn-outline-light:hover {{
        background:#edf5ff;
        color:#0b65d8 !important;
      }}

      .pciexec-card,
      .card {{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .pciexec-card.p-4 {{
        padding:1.5rem !important;
      }}

      .pciexec-section-title,
      .card h5,
      .card h6 {{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
      }}

      .pciexec-section-title {{
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }}

      .pciexec-textarea,
      textarea.form-control {{
        min-height:420px;
        border-radius:14px;
        border:1px solid #d9e3f0;
        resize:vertical;
        background:#f8fafc;
        font-size:.90rem;
        line-height:1.45;
        box-shadow:none !important;
      }}

      .pciexec-textarea:focus,
      textarea.form-control:focus {{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .form-label {{
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
      .form-select {{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      .form-control:focus,
      .form-select:focus {{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .badge {{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      .btn.rounded-pill {{
        border-radius:999px !important;
      }}

      @media (max-width:991.98px) {{
        .pciexec-shell {{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .pciexec-header-card {{
          min-height:88px;
        }}

        .pciexec-title {{
          font-size:1.20rem;
        }}

        .pciexec-subtitle {{
          font-size:.68rem;
        }}
      }}

      @media (max-width:768px) {{
        .pciexec-header-overlay {{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .pciexec-header-overlay::before {{
          margin:0;
        }}

        .pciexec-header-text::before {{
          margin-left:auto;
          margin-right:auto;
        }}

        .pciexec-title,
        .pciexec-subtitle {{
          text-align:center;
        }}

        .pciexec-header-actions .btn {{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Editar Informe Ejecutivo PCI", content=content)




@pci_madurez_bp.route("/resultado/<int:analysis_id>", methods=["GET"])
@login_required
def detalle_resultado_pci(analysis_id: int):
    user = User.query.get(session.get("user_id"))

    if user.role not in ("admin", "auditor") and not verificar_permiso(user, "Nivel de madurez PCI-DSS"):
        flash("No tiene permiso para acceder al resultado PCI-DSS.", "danger")
        return redirect(url_for("menu"))

    ar = PciAnalysisRun.query.get_or_404(analysis_id)

    try:
        resultados = json.loads(ar.resultados_json or "{}")
    except Exception:
        resultados = {}

    def esc(x):
        return escape(x or "")

    def _nl2br(s: str) -> str:
        return (s or "").replace("\n", "<br>")

    # Radar simple desde resultados
    radar_b64 = None
    try:
        labels = []
        values = []
        for code in PCI_BLOCK_ORDER:
            item = resultados.get(code)
            if not item:
                continue
            labels.append(code)
            values.append(float(item.get("pct", 0) or 0))

        if labels and values:
            fig = plt.figure(figsize=(3.55, 3.55), dpi=170)
            ax = plt.subplot(111, polar=True)

            angles = [n / float(len(labels)) * 2 * math.pi for n in range(len(labels))]
            angles += angles[:1]
            vals = values + values[:1]

            ax.set_theta_offset(math.pi / 2)
            ax.set_theta_direction(-1)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(labels, fontsize=7.2)
            ax.tick_params(axis="x", pad=10)

            ax.set_ylim(0, 100)
            ax.set_yticks([20, 40, 60, 80, 100])
            ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7)
            ax.plot(angles, vals, linewidth=2.0)
            ax.fill(angles, vals, alpha=0.16)
            ax.set_title("Radar PCI-DSS", fontsize=9.5, pad=14)

            buf = io.BytesIO()
            fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0.22)
            plt.close(fig)
            radar_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        radar_b64 = None

    informe_ai = (ar.informe_ejecutivo_ai or "").strip()
    informe_editado = (ar.informe_ejecutivo_editado or "").strip()
    informe_mostrar = informe_editado or informe_ai

    top_html = f"""
    <div class="row g-3 mb-4">
      <div class="col-12 col-xl-5">
        <div class="pcidet-card p-4 h-100">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
            <div>
              <div class="pcidet-card-title">📊 Radar general PCI-DSS</div>
              <div class="text-muted small">
                Resultado consolidado por requerimiento y apéndice.
              </div>
            </div>

            <div class="text-end">
              <div class="badge rounded-pill px-3 py-2"
                   style="background:#0d6efd; color:#fff; font-size:.82rem;">
                {float(ar.nivel_promedio_general or 0):.2f}%
              </div>
              <div class="small text-muted mt-1">Promedio general</div>
            </div>
          </div>

          <div class="text-center mt-3 pcidet-radar-wrap">
            {f'<img class="img-fluid pcidet-radar-small" src="data:image/png;base64,{radar_b64}">' if radar_b64 else '<div class="alert alert-warning mb-0">No fue posible generar el radar.</div>'}
          </div>
        </div>
      </div>

      <div class="col-12 col-xl-7">
        <div class="pcidet-card p-4 h-100">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div>
              <div class="pcidet-card-title">🧾 Informe ejecutivo</div>
              <div class="text-muted small">
                Síntesis ejecutiva generada con IA a partir de los resultados PCI-DSS.
              </div>
            </div>

            <div class="d-flex gap-2 flex-wrap">
              <form method="POST"
                    action="{url_for('madurez_pci.informe_ejecutivo_generar_pci', analysis_id=ar.id)}"
                    class="m-0">
                <button type="submit" class="btn pcidet-btn-success rounded-pill px-4 fw-bold">
                  <i class="bi bi-magic me-2"></i>Generar con IA
                </button>
              </form>

              <a href="{url_for('madurez_pci.informe_ejecutivo_editar_pci', analysis_id=ar.id)}"
                 class="btn btn-primary rounded-pill px-4 fw-bold">
                <i class="bi bi-pencil-square me-2"></i>Editar
              </a>
            </div>
          </div>

          <div class="pcidet-exec-box mt-3">
            {f'<div class="pcidet-exec-text">{_nl2br(esc(informe_mostrar))}</div>' if informe_mostrar else '''
              <div class="text-center py-4">
                <div class="mb-2" style="font-size:2rem;">&#129302;</div>>
                <div class="fw-bold text-black">Aún no hay informe ejecutivo</div>
                <div class="text-muted small mt-1">
                  Presiona <b>Generar con IA</b> para construir el informe con base en el resultado de PCI-DSS.
                </div>
              </div>
            '''}
          </div>
        </div>
      </div>
    </div>
    """

    tarjetas = []
    for code in PCI_BLOCK_ORDER:
        item = resultados.get(code)
        if not item:
            continue

        pct = float(item.get("pct", 0) or 0)
        counts = item.get("counts", {}) or {}
        color = item.get("color", "#6c757d")
        madurez = item.get("madurez", "")
        brecha = float(item.get("brecha_pct", 0) or 0)

        tarjetas.append(f"""
        <div class="col-12 col-lg-6">
          <div class="pcidet-card p-4 h-100">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-3">
              <div>
                <div class="pcidet-domain-title">{esc(pci_block_title(code))}</div>
                <div class="small text-muted">Ítems evaluados: <b>{int(item.get('total', 0) or 0)}</b></div>
              </div>

              <div class="text-end">
                <span class="badge rounded-pill px-3 py-2"
                      style="background:{color}; color:#fff;">
                  {pct:.2f}%
                </span>
                <div class="small text-muted mt-1">{esc(madurez)}</div>
              </div>
            </div>

            <div class="row g-2 mt-1">
              <div class="col-6 col-md-3">
                <div class="mini-stat bg-success-subtle text-success-emphasis">Sí<br><b>{counts.get('SI',0)}</b></div>
              </div>
              <div class="col-6 col-md-3">
                <div class="mini-stat bg-warning-subtle text-dark">Parcial<br><b>{counts.get('PARCIAL',0)}</b></div>
              </div>
              <div class="col-6 col-md-3">
                <div class="mini-stat bg-danger-subtle text-danger-emphasis">No<br><b>{counts.get('NO',0)}</b></div>
              </div>
              <div class="col-6 col-md-3">
                <div class="mini-stat bg-secondary-subtle text-secondary-emphasis">N/A<br><b>{counts.get('NA',0)}</b></div>
              </div>
            </div>

            <div class="small text-muted mt-3">
              Brecha estimada: <b>{brecha:.2f}%</b>
            </div>
          </div>
        </div>
        """)

    content = f"""
    <div class="pcidet-shell">

      <div class="pcidet-header-card">
        <div class="pcidet-header-overlay">
          <div class="pcidet-header-text">
            <h3 class="pcidet-title m-0">Resultado — PCI-DSS</h3>
            <div class="pcidet-subtitle">
              Revisión: <b>{esc(ar.company_name or '')}</b>
              · Promedio general: <b>{float(ar.nivel_promedio_general or 0):.2f}%</b>
            </div>
          </div>
        </div>
      </div>

      <div class="pcidet-header-actions">
        <a href="{url_for('madurez_pci.historial_pci')}"
           class="btn pcidet-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al historial
        </a>

        <a href="{url_for('madurez_pci.inicio_pci')}"
           class="btn pcidet-btn-soft rounded-pill px-4 fw-bold">
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

      .pcidet-shell{{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }}

      /* =========================
         HEADER SGSI REAL (UNIFICADO)
      ========================= */
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
      }}

      .pcidet-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        position:relative;
        z-index:1;
      }}

      .pcidet-header-overlay::before{{
        content:"📊";
        width:54px;
        height:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.4rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .pcidet-header-text::before{{
        content:"SGSI · Resultado PCI-DSS";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }}

      .pcidet-title{{
        color:#ffffff;
        font-weight:950;
        font-size:1.32rem;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .pcidet-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
      }}

      /* =========================
         BOTONES SGSI
      ========================= */
      .pcidet-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .pcidet-header-actions .btn{{
        border-radius:10px;
        padding:8px 22px;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }}

      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8;
      }}

      .pcidet-btn-success{{
        background:#198754;
        color:#fff;
        border:1px solid #198754;
      }}

      .pcidet-btn-success:hover{{
        background:#157347;
      }}

      /* =========================
         CARDS SGSI
      ========================= */
      .pcidet-card,
      .card{{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }}

      .pcidet-card.p-4{{
        padding:18px !important;
      }}

      .pcidet-card-title,
      .card h5,
      .card h6{{
        font-weight:950;
        color:#0b4a8f;
      }}

      /* =========================
         RADAR
      ========================= */
      .pcidet-radar-wrap{{
        min-height:310px;
        display:flex;
        align-items:center;
        justify-content:center;
      }}

      .pcidet-radar-small{{
        max-width:300px;
        width:100%;
      }}

      /* =========================
         INFORME EJECUTIVO
      ========================= */
      .pcidet-exec-box{{
        background:#f8fbff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:18px;
      }}

      .pcidet-exec-text{{
        font-size:.92rem;
        line-height:1.6;
        color:#101827;
      }}

      /* =========================
         MINI KPI
      ========================= */
      .mini-stat{{
        border-radius:12px;
        padding:8px 7px;
        text-align:center;
        font-size:.84rem;
        font-weight:900;
        background:#eef5ff;
        color:#0b4a8f;
        box-shadow:0 4px 10px rgba(15,23,42,.08);
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      /* =========================
         RESPONSIVE
      ========================= */
      @media (max-width:768px){{
        .pcidet-header-overlay{{
          flex-direction:column;
          text-align:center;
        }}

        .pcidet-header-overlay::before{{
          margin:0;
        }}

        .pcidet-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Resultado PCI-DSS", content=content)

# ==========================================================================================================================================
#                                                   Fin Módulo de Madurez PCI-DSS
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                   Módulo de Madurez SOC 2 — Diseño NIST
# ==========================================================================================================================================

soc2_madurez_bp = Blueprint("madurez_soc2", __name__, url_prefix="/madurez_soc2")

# GRAC-RAM: colors se carga bajo demanda
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
# GRAC-RAM: importación diferida: from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
Image = _GRACDeferredSymbol("reportlab.platypus", "Image")

# ============================================================
# BASE DE DATOS INDEPENDIENTE — SOC 2
# ============================================================
SOC2_DB_PATH = os.path.join(app.instance_path, "soc2_madurez.db")
os.makedirs(app.instance_path, exist_ok=True)

app.config.setdefault("SQLALCHEMY_BINDS", {})
app.config["SQLALCHEMY_BINDS"]["soc2_madurez"] = "sqlite:///" + SOC2_DB_PATH

SOC2_PERMISSION_NAME = "Nivel de madurez SOC 2"
SOC2_INSTRUMENTO_TEMPLATE_XLSX = os.path.join(BASE_DIR, "static", "templates", "Matriz SOC 2.xlsx")

SOC2_STATUS_SCORE = {
    "SI": 100,
    "PARCIAL": 50,
    "NO": 0,
    "NA": None,  # N/A no suma ni resta; se excluye del cálculo
}

SOC2_BLOCK_ORDER = [
    "SEGURIDAD",
    "DISPONIBILIDAD",
    "CONFIDENCIALIDAD",
    "INTEGRIDAD",
    "PRIVACIDAD",
]

SOC2_BLOCK_TITLES = {
    "SEGURIDAD": "Seguridad",
    "DISPONIBILIDAD": "Disponibilidad",
    "CONFIDENCIALIDAD": "Confidencialidad",
    "INTEGRIDAD": "Integridad del procesamiento",
    "PRIVACIDAD": "Privacidad",
}

SOC2_MADUREZ_LEVELS = [
    {
        "nivel": "Nivel 1: Inicial",
        "descripcion": "No existe implementación formal o es mínima; las prácticas son ad hoc.",
        "score": 1,
        "rango_pct": "0% – 20%",
        "logica": "Prácticas no formalizadas"
    },
    {
        "nivel": "Nivel 2: Repetible",
        "descripcion": "Existen prácticas parciales y repetibles, pero con documentación o control limitado.",
        "score": 2,
        "rango_pct": "21% – 40%",
        "logica": "Prácticas parciales"
    },
    {
        "nivel": "Nivel 3: Definido",
        "descripcion": "El proceso está definido, documentado y comunicado para su ejecución consistente.",
        "score": 3,
        "rango_pct": "41% – 60%",
        "logica": "Proceso documentado"
    },
    {
        "nivel": "Nivel 4: Gestionado",
        "descripcion": "El proceso se mide, gestiona, controla y tiene seguimiento periódico.",
        "score": 4,
        "rango_pct": "61% – 80%",
        "logica": "Proceso medido y gestionado"
    },
    {
        "nivel": "Nivel 5: Optimizado",
        "descripcion": "El proceso es eficaz, sostenido y mejorado continuamente con evidencia trazable.",
        "score": 5,
        "rango_pct": "81% – 100%",
        "logica": "Mejora continua"
    },
]


# ============================================================
# MODELOS DB — SOC 2
# ============================================================
class Soc2MadurezParametro(db.Model):
    __bind_key__ = "soc2_madurez"
    __tablename__ = "soc2_madurez_parametros"

    id = db.Column(db.Integer, primary_key=True)
    nivel = db.Column(db.String(80), nullable=False)
    rango_desde = db.Column(db.Float, nullable=False)
    rango_hasta = db.Column(db.Float, nullable=False)
    color = db.Column(db.String(20), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    orden = db.Column(db.Integer, default=0)


class Soc2MadurezPregunta(db.Model):
    __bind_key__ = "soc2_madurez"
    __tablename__ = "soc2_madurez_preguntas"

    id = db.Column(db.Integer, primary_key=True)
    bloque_codigo = db.Column(db.String(50), index=True, nullable=True)
    bloque_nombre = db.Column(db.String(255), nullable=True)
    seccion_codigo = db.Column(db.String(50), index=True, nullable=True)
    seccion_nombre = db.Column(db.Text, nullable=True)
    pregunta_codigo = db.Column(db.String(50), index=True, nullable=True)
    pregunta = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(5), nullable=False, default="q")  # h / q
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)


class Soc2MadurezRun(db.Model):
    __bind_key__ = "soc2_madurez"
    __tablename__ = "soc2_madurez_runs"

    id = db.Column(db.Integer, primary_key=True)
    consecutivo = db.Column(db.String(255), nullable=False, index=True)
    company_name = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, nullable=True)  # DB independiente: no FK cruzada
    estado = db.Column(db.String(20), nullable=False, default="BORRADOR", index=True)
    progreso_pct = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    resumen_json = db.Column(db.Text, nullable=False, default="{}")
    pct_general = db.Column(db.Float, nullable=False, default=0.0)
    radar_overall_b64 = db.Column(db.Text, nullable=True)

    informe_ejecutivo_ai = db.Column(db.Text, nullable=True)
    informe_ejecutivo_editado = db.Column(db.Text, nullable=True)
    plan_trabajo_ai = db.Column(db.Text, nullable=True)
    plan_trabajo_editado = db.Column(db.Text, nullable=True)


class Soc2MadurezRespuesta(db.Model):
    __bind_key__ = "soc2_madurez"
    __tablename__ = "soc2_madurez_respuestas"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("soc2_madurez_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    pregunta_id = db.Column(db.Integer, db.ForeignKey("soc2_madurez_preguntas.id", ondelete="CASCADE"), nullable=False, index=True)
    estado = db.Column(db.String(20), nullable=False)  # SI / PARCIAL / NO / NA
    comentario = db.Column(db.Text, nullable=True)


class Soc2MadurezCriterioAnalisis(db.Model):
    __bind_key__ = "soc2_madurez"
    __tablename__ = "soc2_madurez_criterio_analisis"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("soc2_madurez_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    bloque_codigo = db.Column(db.String(50), nullable=False, index=True)
    bloque_nombre = db.Column(db.String(255), nullable=True)
    estado_actual = db.Column(db.Text, nullable=True)
    estado_requerido = db.Column(db.Text, nullable=True)
    plan_accion_ai = db.Column(db.Text, nullable=True)
    plan_accion_editado = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("run_id", "bloque_codigo", name="uq_soc2_run_bloque"),
    )


# ============================================================
# INICIALIZACIÓN DB INDEPENDIENTE
# ============================================================
def init_soc2_madurez_db():
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        app.config.setdefault("SQLALCHEMY_BINDS", {})
        app.config["SQLALCHEMY_BINDS"]["soc2_madurez"] = "sqlite:///" + SOC2_DB_PATH
        with app.app_context():
            db.create_all(bind_key="soc2_madurez")
            seed_soc2_parametros()
        print(f"✅ Base de datos SOC 2 inicializada correctamente: {SOC2_DB_PATH}")
    except Exception as e:
        print(f"❌ Error inicializando base de datos SOC 2: {repr(e)}")
        raise


# ============================================================
# HELPERS GENERALES
# ============================================================
def soc2_block_title(code: str) -> str:
    return SOC2_BLOCK_TITLES.get((code or "").strip().upper(), code or "")


def soc2_safe_str(x):
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()


def _soc2_norm(s: str) -> str:
    s = soc2_safe_str(s)
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.upper()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def soc2_normalizar_texto_excel(texto: str) -> str:
    t = soc2_safe_str(texto)
    if not t:
        return ""
    t = t.replace("\ufeff", " ").replace("\xa0", " ")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t).strip()
    return t


def soc2_detectar_bloque(texto: str):
    n = _soc2_norm(texto)
    mapa = {
        "SEGURIDAD": "SEGURIDAD",
        "DISPONIBILIDAD": "DISPONIBILIDAD",
        "CONFIDENCIALIDAD": "CONFIDENCIALIDAD",
        "INTEGRIDAD": "INTEGRIDAD",
        "INTEGRIDAD DEL PROCESAMIENTO": "INTEGRIDAD",
        "PRIVACIDAD": "PRIVACIDAD",
    }
    code = mapa.get(n)
    if code:
        return code, SOC2_BLOCK_TITLES[code]
    return None, None


def seed_soc2_parametros():
    if Soc2MadurezParametro.query.first():
        return
    params = [
        {"nivel": "Nivel 1: Inicial", "rango_desde": 0, "rango_hasta": 20.99, "color": "#dc3545", "descripcion": "No existe implementación formal o es mínima.", "orden": 1},
        {"nivel": "Nivel 2: Repetible", "rango_desde": 21, "rango_hasta": 40.99, "color": "#fd7e14", "descripcion": "Existen prácticas parciales y repetibles.", "orden": 2},
        {"nivel": "Nivel 3: Definido", "rango_desde": 41, "rango_hasta": 60.99, "color": "#ffc107", "descripcion": "El proceso está definido y documentado.", "orden": 3},
        {"nivel": "Nivel 4: Gestionado", "rango_desde": 61, "rango_hasta": 80.99, "color": "#0d6efd", "descripcion": "El proceso se mide, gestiona y controla.", "orden": 4},
        {"nivel": "Nivel 5: Optimizado", "rango_desde": 81, "rango_hasta": 100, "color": "#198754", "descripcion": "Proceso eficaz, sostenido y mejorado continuamente.", "orden": 5},
    ]
    for p in params:
        db.session.add(Soc2MadurezParametro(**p))
    db.session.commit()


def soc2_resolver_nivel(pct: float):
    try:
        pct = float(pct or 0)
    except Exception:
        pct = 0.0
    pct = max(0.0, min(100.0, pct))
    rows = Soc2MadurezParametro.query.order_by(Soc2MadurezParametro.orden.asc()).all()
    for r in rows:
        if float(r.rango_desde) <= pct <= float(r.rango_hasta):
            return {"nivel": r.nivel, "score": r.orden, "color": r.color or "#6c757d", "descripcion": r.descripcion or ""}
    return {"nivel": "Nivel no definido", "score": 0, "color": "#6c757d", "descripcion": ""}


def soc2_resumen_instrumento():
    total_q = Soc2MadurezPregunta.query.filter_by(tipo="q").count()
    total_h = Soc2MadurezPregunta.query.filter_by(tipo="h").count()
    por_bloque = (
        db.session.query(Soc2MadurezPregunta.bloque_codigo, func.count(Soc2MadurezPregunta.id))
        .filter(Soc2MadurezPregunta.tipo == "q")
        .group_by(Soc2MadurezPregunta.bloque_codigo)
        .all()
    )
    return {"total_preguntas": total_q, "total_headers": total_h, "por_bloque": {k: v for k, v in por_bloque}}


def cargar_respuestas_soc2(run_id):
    out = {}
    if not run_id:
        return out
    rows = Soc2MadurezRespuesta.query.filter_by(run_id=run_id).all()
    for r in rows:
        out[r.pregunta_id] = {"estado": (r.estado or "").strip().upper(), "comentario": (r.comentario or "").strip()}
    return out


def calcular_progreso_soc2(preguntas, form_data=None, respuestas_db=None):
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


def obtener_borrador_soc2(user_id):
    if not user_id:
        return None
    return (
        Soc2MadurezRun.query
        .filter(Soc2MadurezRun.user_id == user_id, Soc2MadurezRun.estado == "BORRADOR")
        .order_by(Soc2MadurezRun.updated_at.desc(), Soc2MadurezRun.id.desc())
        .first()
    )


def _contar_respuestas_run_soc2(run_id: int) -> int:
    if not run_id:
        return 0
    return Soc2MadurezRespuesta.query.filter_by(run_id=run_id).count()


def _eliminar_runs_vacios_soc2(user_id: int | None = None):
    q = Soc2MadurezRun.query
    if user_id:
        q = q.filter(Soc2MadurezRun.user_id == user_id)
    eliminados = 0
    for run in q.all():
        if Soc2MadurezRespuesta.query.filter_by(run_id=run.id).count() == 0:
            Soc2MadurezCriterioAnalisis.query.filter_by(run_id=run.id).delete(synchronize_session=False)
            db.session.delete(run)
            eliminados += 1
    if eliminados:
        db.session.commit()
    return eliminados


def soc2_pct_from_estados(estados: list[str]) -> float:
    vals = []
    for e in estados:
        estado = (e or "").strip().upper()

        # N/A no suma ni afecta el promedio
        if estado == "NA":
            continue

        v = SOC2_STATUS_SCORE.get(estado)
        if v is not None:
            vals.append(v)

    return round(sum(vals) / len(vals), 2) if vals else 0.0


def _parse_rango_pct_soc2(rango: str):
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


def soc2_nivel_visual_por_pct(pct: float):
    return soc2_resolver_nivel(pct)


def _soc2_group_questions():
    preguntas = (
        Soc2MadurezPregunta.query
        .filter_by(activo=True, tipo="q")
        .order_by(Soc2MadurezPregunta.bloque_codigo.asc(), Soc2MadurezPregunta.orden.asc(), Soc2MadurezPregunta.id.asc())
        .all()
    )
    grouped = {}
    for q in preguntas:
        bloque = (q.bloque_codigo or "SIN_BLOQUE").strip().upper()
        if bloque not in grouped:
            grouped[bloque] = {
                "titulo": q.bloque_nombre or soc2_block_title(bloque) or bloque,
                "items": []
            }
        grouped[bloque]["items"].append(q)
    ordered = {}
    for code in SOC2_BLOCK_ORDER:
        if code in grouped:
            ordered[code] = grouped[code]
    for code, val in grouped.items():
        if code not in ordered:
            ordered[code] = val
    return ordered


def _soc2_build_resumen(run_id: int) -> dict:
    q = (
        db.session.query(Soc2MadurezRespuesta, Soc2MadurezPregunta)
        .join(Soc2MadurezPregunta, Soc2MadurezPregunta.id == Soc2MadurezRespuesta.pregunta_id)
        .filter(Soc2MadurezRespuesta.run_id == run_id)
        .filter(Soc2MadurezPregunta.tipo == "q")
        .order_by(Soc2MadurezPregunta.bloque_codigo.asc(), Soc2MadurezPregunta.orden.asc())
    )
    por_bloque = {}
    for r, p in q.all():
        b = (p.bloque_codigo or "SIN_BLOQUE").strip().upper()
        por_bloque.setdefault(b, {
            "bloque": b,
            "nombre": p.bloque_nombre or soc2_block_title(b) or b,
            "total": 0,
            "validas": 0,
            "SI": 0,
            "PARCIAL": 0,
            "NO": 0,
            "NA": 0,
            "items": [],
        })
        estado = (r.estado or "").strip().upper()
        por_bloque[b]["total"] += 1
        if estado in ("SI", "PARCIAL", "NO", "NA"):
            por_bloque[b][estado] += 1
        score = SOC2_STATUS_SCORE.get(estado)
        if score is not None:
            por_bloque[b]["validas"] += 1
        por_bloque[b]["items"].append({
            "pregunta_id": p.id,
            "pregunta_codigo": p.pregunta_codigo,
            "pregunta": p.pregunta,
            "estado": estado,
            "comentario": r.comentario or "",
        })

    resumen = {}
    for b, d in por_bloque.items():
        estados = [it["estado"] for it in d["items"]]
        pct = soc2_pct_from_estados(estados)
        nivel = soc2_resolver_nivel(pct)
        d["pct"] = pct
        d["madurez"] = nivel["nivel"]
        d["score"] = nivel.get("score", 0)
        d["color"] = nivel["color"]
        d["descripcion"] = nivel.get("descripcion", "")
        d["brecha_pct"] = round(100.0 - pct, 2)
        resumen[b] = d
    return resumen


def soc2_pct_por_criterio(resumen: dict, order: list[str] = None):
    order = order or SOC2_BLOCK_ORDER
    labels, values = [], []
    for b in order:
        if b in (resumen or {}):
            labels.append(soc2_block_title(b) or b)
            values.append(float((resumen or {}).get(b, {}).get("pct", 0) or 0))
    for b, d in (resumen or {}).items():
        if b not in order:
            labels.append(d.get("nombre") or b)
            values.append(float(d.get("pct", 0) or 0))
    return labels, values


def soc2_radar_b64(labels: list[str], values: list[float], title: str = "Radar SOC 2"):
    if not labels:
        return ""
    vals = [max(0.0, min(100.0, float(v))) for v in values]
    N = len(labels)
    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]
    plot_vals = vals + vals[:1]

    fig = plt.figure(figsize=(3.55, 3.55), dpi=170)
    ax = plt.subplot(111, polar=True)
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=7.3)
    ax.tick_params(axis="x", pad=10)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7)
    ax.tick_params(axis="y", pad=4)
    ax.plot(angles, plot_vals, linewidth=2.0)
    ax.fill(angles, plot_vals, alpha=0.16)
    ax.set_title(title, fontsize=9.5, pad=14)
    fig.subplots_adjust(top=0.83, bottom=0.10, left=0.10, right=0.90)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0.22)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generar_soc2_velocimetro_png_bytes(titulo, valor, nivel="", color="#6c757d"):
    try:
        valor = max(0, min(100, float(valor or 0)))
        fig = plt.figure(figsize=(7.2, 4.2), dpi=220)
        ax = plt.axes([0.04, 0.08, 0.92, 0.84])
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_xlim(-1.18, 1.18)
        ax.set_ylim(-0.28, 1.18)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        rangos = [(180, 144, "#d9534f"), (144, 108, "#f0ad4e"), (108, 72, "#f7d154"), (72, 36, "#5bc0de"), (36, 0, "#5cb85c")]
        for theta1, theta2, c in rangos:
            ax.add_patch(Wedge((0, 0), 1.00, theta2, theta1, width=0.18, facecolor=c, edgecolor="white", linewidth=2))
        for pct in range(0, 101, 10):
            ang = math.radians(180 - (pct / 100.0) * 180.0)
            ax.plot([math.cos(ang) * 0.78, math.cos(ang) * 0.88], [math.sin(ang) * 0.78, math.sin(ang) * 0.88], linewidth=1.2, color="#4b5563")
        for pct in [0, 25, 50, 75, 100]:
            ang = math.radians(180 - (pct / 100.0) * 180.0)
            ax.text(math.cos(ang) * 0.63, math.sin(ang) * 0.63, f"{pct}", ha="center", va="center", fontsize=10, fontweight="bold", color="#374151")
        ang = math.radians(180 - (valor / 100.0) * 180.0)
        ax.add_patch(FancyArrowPatch((0, 0), (math.cos(ang) * 0.72, math.sin(ang) * 0.72), arrowstyle="-|>", mutation_scale=18, linewidth=2.4, color="#0b1220", zorder=5))
        ax.add_patch(Circle((0, 0), radius=0.065, facecolor="#0b1220", edgecolor="white", linewidth=1.0, zorder=6))
        titulo_corto = (titulo or "").strip()
        if len(titulo_corto) > 42:
            titulo_corto = titulo_corto[:39] + "..."
        ax.text(0, 1.06, titulo_corto, ha="center", va="center", fontsize=13, fontweight="bold", color="#0f3d68")
        ax.text(0, 0.30, f"{valor:.1f}%", ha="center", va="center", fontsize=24, fontweight="bold", color=color)
        if nivel:
            ax.text(0, 0.12, str(nivel)[:30], ha="center", va="center", fontsize=11, fontweight="bold", color="#374151")
        buf = io.BytesIO()
        canvas = FigureCanvas(fig)
        canvas.print_png(buf)
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        plt.close("all")
        return None


def generar_soc2_velocimetro_base64(label: str, pct: float, nivel: str, color: str):
    b = generar_soc2_velocimetro_png_bytes(label, pct, nivel, color)
    if not b:
        return None
    return base64.b64encode(b).decode("utf-8")


def soc2_normalizar_texto_rico_guardado(texto: str) -> str:
    txt = (texto or "").strip()

    if not txt:
        return ""

    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = html.unescape(txt)
    txt = txt.replace("```json", "").replace("```", "").strip()

    # Extrae JSON aunque venga como:
    # { "informe_ejecutivo": "texto..." }
    # { "plan_trabajo": "texto..." }
    # { "texto": "texto..." }
    obj = None

    try:
        obj = json.loads(txt)
    except Exception:
        try:
            start = txt.find("{")
            end = txt.rfind("}")
            if start != -1 and end != -1 and end > start:
                obj = json.loads(txt[start:end + 1])
        except Exception:
            obj = None

    if isinstance(obj, dict):
        val = (
            obj.get("informe_ejecutivo")
            or obj.get("informe")
            or obj.get("resumen_ejecutivo")
            or obj.get("plan_trabajo")
            or obj.get("plan_accion")
            or obj.get("texto")
            or ""
        )

        if isinstance(val, list):
            val = _build_plan_accion_soc2_texto(val)

        if isinstance(val, dict):
            val = json.dumps(val, ensure_ascii=False, indent=2)

        if isinstance(val, str) and val.strip():
            txt = val.strip()

    txt = html.unescape(txt)

    # Si aún quedaron llaves al inicio y contiene informe_ejecutivo,
    # intenta extraer por regex como último recurso.
    m = re.search(
        r'"informe_ejecutivo"\s*:\s*"(?P<txt>.*)"\s*\}?\s*$',
        txt,
        flags=re.IGNORECASE | re.DOTALL
    )

    if m:
        extraido = m.group("txt")

        try:
            # Solo interpreta secuencias JSON reales (\n, \u00f3, etc.)
            extraido = json.loads(f'"{extraido}"')
        except Exception:
            pass

        txt = extraido.strip()

    txt = re.sub(r"<\s*br\s*/?\s*>", "\n", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", "", txt)

    patrones = [
        r"^\s*\{\s*",
        r"^\s*\"informe_ejecutivo\"\s*:\s*\"?",
        r"^\s*\"resumen_ejecutivo\"\s*:\s*\"?",
        r"^\s*\*{0,3}\s*INFORME\s+EJECUTIVO\s*(DE\s+MADUREZ\s+SOC\s*2)?\s*\*{0,3}\s*[:\-–—]?\s*",
        r"^\s*#{1,6}\s*INFORME\s+EJECUTIVO\s*(DE\s+MADUREZ\s+SOC\s*2)?\s*[:\-–—]?\s*",
        r"^\s*RESUMEN\s+EJECUTIVO\s*[:\-–—]?\s*",
        r"^\s*PLAN\s+DE\s+TRABAJO\s*[:\-–—]?\s*",
    ]

    for p in patrones:
        txt = re.sub(p, "", txt, flags=re.IGNORECASE).strip()

    txt = re.sub(r'"\s*\}\s*$', "", txt).strip()
    txt = txt.replace("\\n", "\n")
    txt = txt.replace('\\"', '"')
    txt = txt.replace("**", "").replace("__", "")

    txt = re.sub(r"[ \t]+\n", "\n", txt)
    txt = re.sub(r"\n[ \t]+", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)

    return txt.strip()


def _extraer_json_objeto_soc2(raw: str) -> dict:
    raw = (raw or "").strip().replace("```json", "").replace("```", "").strip()
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
            return json.loads(raw[start:end + 1])
    except Exception:
        pass
    return {}


def _build_plan_accion_soc2_texto(plan_list) -> str:
    if not isinstance(plan_list, list):
        return ""
    lines = []
    for i, it in enumerate(plan_list, start=1):
        accion = (it.get("accion") or it.get("actividad") or "").strip()
        prioridad = (it.get("prioridad") or "").strip()
        responsable = (it.get("responsable_sugerido") or "").strip()
        plazo = (it.get("plazo") or "").strip()
        evidencia = (it.get("evidencia_esperada") or it.get("entregable") or "").strip()
        lines.append(
            f"{i}. Acción: {accion or 'Sin definir'}\n"
            f"   Prioridad: {prioridad or 'Sin definir'}\n"
            f"   Responsable sugerido: {responsable or 'Sin definir'}\n"
            f"   Plazo: {plazo or 'Sin definir'}\n"
            f"   Evidencia esperada: {evidencia or 'Sin definir'}"
        )
    return "\n\n".join(lines).strip()


def _normalizar_plan_accion_soc2_texto(texto_raw: str) -> str:
    txt = (texto_raw or "").strip().replace("```json", "").replace("```", "").strip()
    if not txt:
        return ""
    obj = _extraer_json_objeto_soc2(txt)
    if isinstance(obj, dict):
        for key in ("plan_accion", "plan_trabajo", "plan", "acciones"):
            if isinstance(obj.get(key), list):
                return _build_plan_accion_soc2_texto(obj.get(key))
    return soc2_normalizar_texto_rico_guardado(txt)

# ============================================================
# SOC 2 — PROMPT PLAN DE TRABAJO IA
# ============================================================

def _soc2_prompt_plan_trabajo(run: "Soc2MadurezRun", resumen: dict) -> str:
    """
    Prompt para generar plan de trabajo SOC 2.
    Lo usa plan_trabajo_generar().
    """

    lineas = []

    for code in SOC2_BLOCK_ORDER:
        d = (resumen or {}).get(code)
        if not d:
            continue

        lineas.append(
            f"- {d.get('nombre') or soc2_block_title(code) or code}: "
            f"{float(d.get('pct', 0) or 0):.2f}% | "
            f"Nivel: {d.get('madurez') or ''} | "
            f"Brecha: {float(d.get('brecha_pct', 0) or 0):.2f}% | "
            f"NO: {d.get('NO', 0)} | "
            f"Parcial: {d.get('PARCIAL', 0)}"
        )

    criterios_txt = "\n".join(lineas) if lineas else "Sin resultados consolidados."

    return f"""
Eres un consultor senior experto en SOC 2 y preparación para auditoría.

Genera un plan de trabajo priorizado para cerrar brechas SOC 2.

DATOS
Consecutivo: {run.consecutivo}
Cumplimiento general: {float(run.pct_general or 0):.2f}%

RESULTADOS POR CRITERIO
{criterios_txt}

RESPONDE ÚNICAMENTE JSON VÁLIDO.
No uses markdown.
No agregues texto antes ni después del JSON.

Formato exacto:
{{
  "plan_trabajo": [
    {{
      "accion": "texto",
      "prioridad": "Alta|Media|Baja",
      "responsable_sugerido": "texto",
      "plazo": "texto",
      "evidencia_esperada": "texto"
    }}
  ]
}}

REGLAS:
- Genera entre 8 y 12 acciones.
- Prioriza criterios con menor cumplimiento.
- Las acciones deben ser auditables y verificables.
- La evidencia esperada debe ser concreta.
- No inventes herramientas específicas.
""".strip()

# ============================================================
# IA — SOC 2
# ============================================================
def _soc2_ai_text(prompt: str, max_tokens: int = 900) -> str:
    """
    IA exclusiva para SOC 2.
    Corrige timeout de Ollama:
    - Reduce num_predict
    - Aumenta timeout
    - No usa stream
    - Mantiene OpenRouter si está configurado como proveedor
    """

    provider = (get_ai_provider() or "openrouter").strip().lower()

    # =========================
    # OLLAMA
    # =========================
    if provider == "ollama":
        base_url = (get_ollama_base_url() or "http://localhost:11434").strip().rstrip("/")
        model = (get_ollama_model() or "llama3.1").strip()

        if not base_url:
            raise RuntimeError("No hay OLLAMA_BASE_URL configurada.")
        if not model:
            raise RuntimeError("No hay OLLAMA_MODEL configurado.")

        try:
            resp = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.15,
                        "num_predict": int(max_tokens or 700),
                        "top_p": 0.9
                    }
                },
                timeout=600
            )

            resp.raise_for_status()
            data = resp.json() or {}
            texto = (data.get("response") or "").strip()

            if not texto:
                raise RuntimeError("Ollama respondió sin contenido.")

            return texto

        except requests.exceptions.ReadTimeout:
            raise RuntimeError(
                "Ollama tardó demasiado en responder. "
                "Se recomienda reducir el número de preguntas enviadas o usar OpenRouter para este análisis."
            )

        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "No fue posible conectar con Ollama. "
                "Verifica que Ollama esté activo en http://localhost:11434."
            )

    # =========================
    # OPENROUTER
    # =========================
    if "_ai_text" in globals():
        return _ai_text(prompt, max_tokens=max_tokens)

    raise RuntimeError("No se encontró helper global _ai_text para OpenRouter/Ollama.")


def _soc2_ai_prompt_criterio(
    run: "Soc2MadurezRun",
    bloque_codigo: str,
    bloque_nombre: str,
    pct: float,
    items: list[dict]
):
    """
    Prompt SOC 2 mejorado:
    - Evita respuestas demasiado cortas.
    - Mantiene límite para no generar timeout en Ollama.
    - Obliga estado actual y requerido con análisis real.
    """

    bullets = []

    for it in items[:30]:
        pregunta = (it.get("pregunta") or "")[:260].replace("\n", " ")
        comentario = (it.get("comentario") or "")[:260].replace("\n", " ")
        estado = (it.get("estado") or "").strip().upper()

        linea = f"- [{estado}] {pregunta}"
        if comentario:
            linea += f" | Evidencia/Comentario: {comentario}"

        bullets.append(linea)

    joined = "\n".join(bullets) if bullets else "- Sin evidencias registradas."

    return f"""
Eres un consultor senior experto en SOC 2, Trust Services Criteria, auditoría de controles, seguridad de la información y gobierno de riesgos.

Debes generar un análisis ejecutivo, claro y accionable para el criterio evaluado.

CONTEXTO DE LA EVALUACIÓN
Consecutivo: {run.consecutivo}
Criterio SOC 2: {bloque_codigo} - {bloque_nombre}
Cumplimiento actual: {pct:.2f}%

EVIDENCIAS Y RESPUESTAS DEL CRITERIO
{joined}

INSTRUCCIONES OBLIGATORIAS
Responde únicamente JSON válido.
No uses markdown.
No agregues texto antes ni después del JSON.

Debes devolver exactamente estas llaves:
{{
  "estado_actual": "texto",
  "estado_requerido": "texto",
  "plan_accion": [
    {{
      "accion": "texto",
      "prioridad": "Alta|Media|Baja",
      "responsable_sugerido": "texto",
      "plazo": "texto",
      "evidencia_esperada": "texto"
    }}
  ]
}}

REGLAS PARA estado_actual:
- No respondas solo con el porcentaje.
- Redacta entre 2 y 4 párrafos.
- Explica qué tan maduro está el criterio actualmente.
- Menciona fortalezas visibles según respuestas SI.
- Menciona brechas según respuestas NO y PARCIAL.
- Usa los comentarios/evidencias cuando existan.
- Si hay pocas evidencias, dilo claramente.
- No inventes herramientas ni controles que no estén soportados por las respuestas.

REGLAS PARA estado_requerido:
- No respondas solo con "100% de cumplimiento".
- Redacta entre 2 y 4 párrafos.
- Describe el estado objetivo esperado para SOC 2.
- Explica qué controles, evidencias, formalización, monitoreo y mejora deberían existir.
- Relaciona el estado requerido con auditoría, trazabilidad, evidencia y operación sostenida.
- No inventes marcas ni herramientas específicas.

REGLAS PARA plan_accion:
- Genera entre 5 y 8 acciones.
- Prioriza primero respuestas NO y PARCIAL.
- Cada acción debe ser concreta, auditable y verificable.
- La evidencia esperada debe ser un entregable real: política, procedimiento, matriz, registro, acta, reporte, evidencia de monitoreo, prueba de control, etc.
- Usa prioridades Alta, Media o Baja.

TONO
Profesional, ejecutivo y consultivo.
Enfocado en madurez SOC 2 y preparación para auditoría.
""".strip()


# ============================================================
# IMPORTAR INSTRUMENTO
# ============================================================
@soc2_madurez_bp.route("/admin/importar_instrumento", methods=["POST"])
@login_required
def importar_instrumento_soc2():
    user = User.query.get(session.get("user_id"))
    if user.role == "auditor":
        flash("El rol Auditor no puede importar instrumentos.", "danger")
        return redirect(url_for("madurez_soc2.parametros"))
    if user.role != "admin" and not verificar_permiso(user, SOC2_PERMISSION_NAME):
        flash("No tiene permiso para importar el instrumento SOC 2.", "danger")
        return redirect(url_for("menu"))

    force = (request.args.get("force") == "1") or (request.form.get("force") == "1")
    try:
        if force:
            Soc2MadurezCriterioAnalisis.query.delete()
            Soc2MadurezRespuesta.query.delete()
            Soc2MadurezRun.query.delete()
            Soc2MadurezPregunta.query.delete()
            db.session.commit()
            flash("🧹 Instrumento SOC 2 anterior borrado. Reimportando…", "info")

        if Soc2MadurezPregunta.query.first() and not force:
            flash("El instrumento SOC 2 ya está cargado en la base de datos.", "warning")
            return redirect(url_for("madurez_soc2.parametros"))

        alternativas = [
            SOC2_INSTRUMENTO_TEMPLATE_XLSX,
            os.path.join(BASE_DIR, "static", "templates", "Matriz SOC 2(2).xlsx"),
            os.path.join(BASE_DIR, "static", "templates", "SOC 2.xlsx"),
            os.path.join(BASE_DIR, "static", "templates", "SOC2.xlsx"),
        ]
        xlsx_path = next((p for p in alternativas if os.path.exists(p)), None)
        if not xlsx_path:
            flash("No se encontró el Excel SOC 2 en static/templates. Usa: Matriz SOC 2.xlsx", "danger")
            return redirect(url_for("madurez_soc2.parametros"))

        df = pd.read_excel(xlsx_path, sheet_name=0, header=0)
        col_pregunta = None
        for c in df.columns:
            if _soc2_norm(c) in ("PREGUNTAS", "PREGUNTA"):
                col_pregunta = c
                break
        if not col_pregunta:
            flash("El Excel SOC 2 no contiene la columna 'Preguntas'.", "danger")
            return redirect(url_for("madurez_soc2.parametros"))

        orden = 1
        bloque_codigo = None
        bloque_nombre = None
        creadas_q = 0
        creadas_h = 0
        ignoradas = 0

        for _, row in df.iterrows():
            txt = soc2_normalizar_texto_excel(row.get(col_pregunta))
            if not txt or _soc2_norm(txt) in ("PREGUNTAS", "PREGUNTA"):
                continue
            bc, bn = soc2_detectar_bloque(txt)
            if bc:
                bloque_codigo = bc
                bloque_nombre = bn
                db.session.add(Soc2MadurezPregunta(
                    bloque_codigo=bloque_codigo,
                    bloque_nombre=bloque_nombre,
                    seccion_codigo=bloque_codigo,
                    seccion_nombre=bloque_nombre,
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
            pregunta_codigo = f"{bloque_codigo[:3]}-{creadas_q + 1:03d}"
            db.session.add(Soc2MadurezPregunta(
                bloque_codigo=bloque_codigo,
                bloque_nombre=bloque_nombre,
                seccion_codigo=bloque_codigo,
                seccion_nombre=bloque_nombre,
                pregunta_codigo=pregunta_codigo,
                pregunta=txt,
                tipo="q",
                orden=orden,
                activo=True
            ))
            orden += 1
            creadas_q += 1

        db.session.commit()
        seed_soc2_parametros()
        flash(f"✅ Instrumento SOC 2 importado correctamente. Cabeceras: {creadas_h} | Preguntas: {creadas_q} | Ignoradas: {ignoradas}", "success")
        return redirect(url_for("madurez_soc2.parametros"))
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        flash(f"❌ Error importando instrumento SOC 2: {e}", "danger")
        return redirect(url_for("madurez_soc2.parametros"))


# ============================================================
# CONSOLIDAR ANÁLISIS
# ============================================================
def run_analysis_from_soc2_run(soc2_run_id: int):
    run = Soc2MadurezRun.query.get_or_404(soc2_run_id)
    resumen = _soc2_build_resumen(run.id)
    valores = [float(v.get("pct", 0) or 0) for v in resumen.values()]
    pct_general = round(sum(valores) / len(valores), 2) if valores else 0.0
    labels, values = soc2_pct_por_criterio(resumen, SOC2_BLOCK_ORDER)
    run.resumen_json = json.dumps(resumen, ensure_ascii=False)
    run.pct_general = pct_general
    run.radar_overall_b64 = soc2_radar_b64(labels, values, title="Radar por Criterio - SOC 2")
    run.company_name = run.consecutivo
    run.updated_at = datetime.utcnow()
    db.session.commit()
    return run.id

# ============================================================
# PERMISOS SOC 2 — ADMIN / USUARIO CON PERMISO / AUDITOR
# ============================================================

def soc2_user_can_access(user):
    """
    Puede VER el módulo:
    - admin
    - auditor
    - usuario con permiso Nivel de madurez SOC 2
    """
    return bool(
        user and (
            user.role in ("admin", "auditor")
            or verificar_permiso(user, SOC2_PERMISSION_NAME)
        )
    )


def soc2_user_can_execute(user):
    """
    Puede EJECUTAR / MODIFICAR:
    - admin
    - usuario con permiso Nivel de madurez SOC 2

    Auditor NO puede:
    - editar
    - eliminar
    - generar IA
    - exportar PDF
    - importar instrumento
    - guardar / analizar
    """
    return bool(
        user
        and user.role != "auditor"
        and (
            user.role == "admin"
            or verificar_permiso(user, SOC2_PERMISSION_NAME)
        )
    )


def soc2_check_access_or_redirect(user, msg="No tiene permiso para acceder al módulo SOC 2."):
    if not soc2_user_can_access(user):
        flash(msg, "danger")
        return redirect(url_for("menu"))
    return None


def soc2_check_execute_or_redirect(user, msg="No tiene permiso para ejecutar esta acción en SOC 2."):
    if not soc2_user_can_execute(user):
        flash(msg, "danger")
        return redirect(url_for("madurez_soc2.inicio_soc2"))
    return None


# Alias para compatibilidad con bloques anteriores
def soc2_deny_access(msg="No tiene permiso para acceder al módulo SOC 2."):
    flash(msg, "danger")
    return redirect(url_for("menu"))


def soc2_deny_execute(msg="No tiene permiso para ejecutar esta acción en SOC 2."):
    flash(msg, "danger")
    return redirect(url_for("madurez_soc2.inicio_soc2"))


# ============================================================
# PANTALLA PRINCIPAL — MISMO DISEÑO NIST
# ============================================================

@soc2_madurez_bp.route("/", methods=["GET"], endpoint="inicio_soc2")
@login_required
def inicio_soc2():
    user = User.query.get(session.get("user_id"))

    if not soc2_user_can_access(user):
        return soc2_deny_access("No tiene permiso para acceder al módulo de nivel de madurez SOC 2.")

    read_only = user.role == "auditor"

    ingreso_btn = """
      <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled title="El rol Auditor no puede ingresar información">
        <i class="bi bi-pencil-square me-2"></i>Ingresar la información
      </button>
    """ if read_only else f"""
      <a href="{url_for('madurez_soc2.ingreso')}" class="btn nistmad-btn-primary rounded-pill px-4 fw-bold">
        <i class="bi bi-pencil-square me-2"></i>Ingresar la información
      </a>
    """

    parametros_btn = """
      <button class="btn btn-outline-secondary rounded-pill px-3" disabled title="El rol Auditor no puede modificar parámetros">
        <i class="bi bi-gear me-2"></i>Parámetros
      </button>
    """ if read_only else f"""
      <a href="{url_for('madurez_soc2.parametros')}" class="btn btn-outline-secondary rounded-pill px-3">
        <i class="bi bi-gear me-2"></i>Parámetros
      </a>
    """

    total = Soc2MadurezPregunta.query.filter_by(tipo="q").count()
    badge = '<span class="badge bg-success ms-2">Instrumento cargado</span>' if total else '<span class="badge bg-danger ms-2">Instrumento NO cargado</span>'
    hint = "Puedes ingresar la información, analizar la evaluación o consultar el historial." if total else "Primero entra a Parámetros e importa el instrumento SOC 2."

    content = f"""
<div class="nistmad-shell">

  <div class="nistmad-header-card">
    <div class="nistmad-header-overlay">
      <div class="nistmad-header-text">
        <h3 class="nistmad-title m-0">Nivel de Madurez — SOC 2</h3>
        <div class="nistmad-subtitle">
          Evaluación por criterios SOC 2: Seguridad, Disponibilidad, Confidencialidad,
          Integridad del procesamiento y Privacidad.
        </div>
      </div>
    </div>
  </div>

  <div class="nistmad-header-actions">
    {ingreso_btn}
    <a href="{url_for('madurez_soc2.historial')}" class="btn nistmad-btn-soft rounded-pill px-4 historial-pill">
      <span class="d-inline-flex align-items-center gap-2">
        <span class="hist-dot"></span>
        <i class="bi bi-clock-history"></i>
        <span class="fw-semibold">Historial de Revisiones</span>
      </span>
    </a>
  </div>

  <div class="row g-3 mt-2">
    <div class="col-12 col-lg-8">
      <div class="nistmad-card p-4 h-100">
        <div class="nistmad-section-title">Estado del instrumento</div>
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
          <b>Sugerencia:</b> Usa <b>Parámetros</b> para ver la definición de niveles 1–5
          y gestionar la importación del instrumento SOC 2.
        </div>
      </div>
    </div>

    <div class="col-12 col-lg-4">
      <div class="nistmad-card p-4 h-100">
        <div class="nistmad-section-title">¿Qué puedes hacer aquí?</div>
        <ul class="small mb-0 text-black ps-3">
          <li><b>Ingresar la información:</b> diligenciar respuestas con evidencia.</li>
          <li><b>Historial:</b> revisar evaluaciones previas y resultados.</li>
          <li><b>Parámetros:</b> gestionar niveles e instrumento, excepto auditor.</li>
        </ul>
      </div>
    </div>
  </div>
</div>
{soc2_nist_css('nistmad', '🛡️')}
"""
    return render_template_string(BASE, title="Madurez SOC 2", content=content)

# ============================================================
# PARÁMETROS — USUARIO CON PERMISO PUEDE MODIFICAR / AUDITOR NO
# ============================================================

@soc2_madurez_bp.route("/parametros", methods=["GET", "POST"])
@login_required
def parametros():
    user = User.query.get(session.get("user_id"))

    if not soc2_user_can_execute(user):
        return soc2_deny_execute("No tiene permiso para administrar parámetros SOC 2.")

    seed_soc2_parametros()

    if request.method == "POST":
        try:
            for r in Soc2MadurezParametro.query.all():
                r.nivel = (request.form.get(f"nivel_{r.id}") or r.nivel).strip()
                r.rango_desde = float(request.form.get(f"desde_{r.id}") or r.rango_desde)
                r.rango_hasta = float(request.form.get(f"hasta_{r.id}") or r.rango_hasta)
                r.color = (request.form.get(f"color_{r.id}") or r.color).strip()
                r.descripcion = (request.form.get(f"descripcion_{r.id}") or "").strip()
            db.session.commit()
            flash("✅ Parámetros SOC 2 guardados correctamente.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error guardando parámetros SOC 2: {e}", "danger")
        return redirect(url_for("madurez_soc2.parametros"))

    rows = []
    for r in Soc2MadurezParametro.query.order_by(Soc2MadurezParametro.orden.asc()).all():
        rows.append(f"""
        <tr>
          <td><input class="form-control" name="nivel_{r.id}" value="{escape(r.nivel or '')}"></td>
          <td class="text-center"><input class="form-control text-center" name="desde_{r.id}" value="{r.rango_desde}"></td>
          <td class="text-center"><input class="form-control text-center" name="hasta_{r.id}" value="{r.rango_hasta}"></td>
          <td class="text-center"><input type="color" class="form-control form-control-color mx-auto" name="color_{r.id}" value="{escape(r.color or '#6c757d')}"></td>
          <td><textarea class="form-control" name="descripcion_{r.id}" rows="2">{escape(r.descripcion or '')}</textarea></td>
        </tr>
        """)

    resumen = soc2_resumen_instrumento()

    content = f"""
<div class="nistpar-shell">
  <div class="nistpar-header-card">
    <div class="nistpar-header-overlay">
      <div class="nistpar-header-text">
        <h3 class="nistpar-title m-0">Parámetros de Madurez — SOC 2</h3>
        <div class="nistpar-subtitle">Configuración de niveles, rangos de madurez e importación del instrumento.</div>
      </div>
    </div>
  </div>

  <div class="nistpar-header-actions">
    <a href="{url_for('madurez_soc2.inicio_soc2')}" class="btn nistpar-btn-main rounded-pill px-4 fw-bold">
      <i class="bi bi-arrow-left me-2"></i>Volver
    </a>
    <form method="POST" action="{url_for('madurez_soc2.importar_instrumento_soc2')}" class="m-0">
      <button class="btn btn-success rounded-pill px-4 fw-bold">
        <i class="bi bi-upload me-2"></i>Importar instrumento
      </button>
    </form>
    <form method="POST" action="{url_for('madurez_soc2.importar_instrumento_soc2')}?force=1" class="m-0" onsubmit="return confirm('¿Borrar e importar de nuevo el instrumento SOC 2?')">
      <button class="btn btn-danger rounded-pill px-4 fw-bold">
        <i class="bi bi-arrow-repeat me-2"></i>Reimportar
      </button>
    </form>
  </div>

  <div class="nistpar-card p-4 mb-3">
    <div class="nistpar-section-title">Resumen instrumento</div>
    <div class="small text-black">
      Preguntas: <b>{resumen['total_preguntas']}</b> · Cabeceras: <b>{resumen['total_headers']}</b> · Por criterio: <b>{escape(str(resumen['por_bloque']))}</b>
    </div>
  </div>

  <form method="POST" class="nistpar-card p-4">
    <div class="nistpar-section-title">Niveles de madurez</div>
    <div class="table-responsive">
      <table class="table table-hover align-middle nistpar-table">
        <thead class="nistpar-table-head">
          <tr>
            <th style="width:28%;">Nivel de Madurez</th>
            <th class="text-center" style="width:110px;">Desde %</th>
            <th class="text-center" style="width:110px;">Hasta %</th>
            <th class="text-center" style="width:90px;">Color</th>
            <th>Descripción del Nivel</th>
          </tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    <div class="text-end mt-3">
      <button class="btn btn-primary rounded-pill px-4 fw-bold">
        <i class="bi bi-save me-2"></i>Guardar parámetros
      </button>
    </div>
  </form>
</div>
{soc2_nist_css('nistpar', '⚙️')}
"""
    return render_template_string(BASE, title="Parámetros SOC 2", content=content)


# ============================================================
# INGRESO DE INFORMACIÓN SOC 2 — SIN LOADER GLOBAL EN VALIDACIÓN
# ============================================================

@soc2_madurez_bp.route("/ingreso", methods=["GET"])
@login_required
def ingreso():
    user = User.query.get(session.get("user_id"))

    if not soc2_user_can_execute(user):
        return soc2_deny_execute("No tiene permiso para ingresar información SOC 2.")

    if Soc2MadurezPregunta.query.filter_by(tipo="q").count() == 0:
        flash("⚠️ Primero debes importar el instrumento SOC 2.", "warning")
        return redirect(url_for("madurez_soc2.parametros"))

    preguntas = (
        Soc2MadurezPregunta.query
        .filter_by(activo=True, tipo="q")
        .order_by(
            Soc2MadurezPregunta.bloque_codigo.asc(),
            Soc2MadurezPregunta.seccion_codigo.asc(),
            Soc2MadurezPregunta.orden.asc(),
            Soc2MadurezPregunta.id.asc()
        )
        .all()
    )

    draft = obtener_borrador_soc2(user.id if user else None)
    respuestas_guardadas = cargar_respuestas_soc2(draft.id) if draft else {}
    consecutivo_val = (draft.consecutivo if draft else "") or ""

    grouped = _soc2_group_questions()
    acc_html = []
    acc_id = 0

    def esc(x):
        return escape(str(x or ""))

    for bloque_codigo, payload in grouped.items():
        acc_id += 1
        func_key = f"soc2func{acc_id}"
        titulo_bloque = payload.get("titulo") or soc2_block_title(bloque_codigo) or bloque_codigo
        rows = []

        for q in payload.get("items", []):
            saved = respuestas_guardadas.get(q.id, {})
            saved_estado = (saved.get("estado") or "").strip().upper()
            saved_com = esc(saved.get("comentario") or "")
            qtext = q.pregunta or ""
            cat_code = q.pregunta_codigo or q.seccion_codigo or bloque_codigo

            rows.append(f"""
            <div class="col-12 col-xl-6">
              <div class="nistform-qcard h-100">
                <div class="nistform-qhead">
                  <div class="d-flex align-items-center gap-2 flex-wrap">
                    <span class="badge rounded-pill text-bg-light border fw-semibold">{esc(cat_code)}</span>
                    <span class="badge rounded-pill text-bg-primary">Orden {q.orden or 0}</span>
                  </div>
                </div>

                <div class="nistform-qtext">{esc(qtext)}</div>

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
                  <div class="nistform-func-subtitle">Criterio SOC 2 · {esc(bloque_codigo)}</div>
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
        alerta_borrador = """
        <div class="alert alert-info rounded-4 border-0 shadow-sm">
          <i class="bi bi-info-circle-fill me-2"></i>
          Tienes un borrador SOC 2 cargado automáticamente.
        </div>
        """

    content = f"""
    <div class="nistform-shell soc2-no-global-loader">

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
            <h3 class="nistform-title m-0">Nivel de Madurez — SOC 2</h3>
            <div class="nistform-subtitle">Ingreso de información del instrumento SOC 2</div>
          </div>
        </div>
      </div>

      <div class="nistform-header-actions">
        <a href="{url_for('madurez_soc2.inicio_soc2')}" class="btn btn-light rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver
        </a>

        <a href="{url_for('madurez_soc2.historial')}" class="btn btn-outline-primary rounded-pill px-4 fw-bold">
          <i class="bi bi-clock-history me-2"></i>Historial
        </a>
      </div>

      <div class="nistform-card p-4">
        {alerta_borrador}

        <form id="soc2IngresoForm"
              method="POST"
              action="{url_for('madurez_soc2.ingreso_guardar')}"
              novalidate>

          <input type="hidden" name="draft_id" value="{draft.id if draft else ''}">
          <input type="hidden" name="accion" id="soc2Accion" value="guardar">

          <div class="nistform-section-title">Información de la revisión</div>

          <div class="mb-4">
            <label class="text-black form-label fw-semibold">
              Consecutivo de la Revisión <span class="text-danger">*</span>
            </label>

            <input type="text"
                   class="form-control form-control-lg rounded-pill"
                   name="consecutivo"
                   id="soc2Consecutivo"
                   value="{esc(consecutivo_val)}"
                   autocomplete="off">

            <div id="soc2ConsecutivoError"
                 class="invalid-feedback d-none fw-bold mt-2">
              Debes ingresar el consecutivo de la Revisión.
            </div>
          </div>

          <div class="nistform-section-title">Instrumento de evaluación</div>

          <div class="accordion nistform-accordion" id="accSoc2">
            {''.join(acc_html)}
          </div>

          <div class="d-flex justify-content-center gap-3 flex-wrap mt-4">
            <button class="btn btn-outline-primary btn-lg rounded-pill px-5 shadow fw-semibold"
                    type="button"
                    id="btnGuardarSoc2">
              <i class="bi bi-save2 me-2"></i>Guardar
            </button>

            <button id="btnAnalizarSoc2"
                    class="btn btn-primary btn-lg rounded-pill px-5 shadow fw-semibold"
                    type="button">
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

      function validarConsecutivo() {{
        const consecutivo = document.getElementById("soc2Consecutivo");
        const msg = document.getElementById("soc2ConsecutivoError");

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

      function enviarSoc2(accion) {{
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

        const form = document.getElementById("soc2IngresoForm");
        const accionInput = document.getElementById("soc2Accion");

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

      window.soc2GuardarSinLoader = function(e) {{
        if (e) {{
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
        }}
        return enviarSoc2("guardar");
      }};

      window.soc2AnalizarSinLoader = function(e) {{
        if (e) {{
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
        }}
        return enviarSoc2("analizar");
      }};

      document.addEventListener("DOMContentLoaded", function () {{
        hideLoader();

        const btnGuardar = document.getElementById("btnGuardarSoc2");
        const btnAnalizar = document.getElementById("btnAnalizarSoc2");
        const consecutivo = document.getElementById("soc2Consecutivo");
        const form = document.getElementById("soc2IngresoForm");

        if (btnGuardar) {{
          btnGuardar.onclick = soc2GuardarSinLoader;
        }}

        if (btnAnalizar) {{
          btnAnalizar.onclick = soc2AnalizarSinLoader;
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

        hideLoader();
        setInterval(hideLoader, 250);
      }});
    }})();
    </script>

    {soc2_nistform_css()}
    """

    return render_template_string(BASE, title="Ingreso SOC 2", content=content)


# ============================================================
# GUARDAR / ANALIZAR — SOC 2
# ============================================================

@soc2_madurez_bp.route("/ingreso/guardar", methods=["POST"])
@login_required
def ingreso_guardar():
    user = User.query.get(session.get("user_id"))

    if not soc2_user_can_execute(user):
        return soc2_deny_execute("No tiene permiso para guardar ni analizar información SOC 2.")

    consecutivo = (request.form.get("consecutivo") or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    accion = (request.form.get("accion") or "guardar").strip().lower()
    draft_id = (request.form.get("draft_id") or "").strip()

    if not consecutivo:
        flash("Debes ingresar el consecutivo de la Revisión.", "warning")
        return redirect(url_for("madurez_soc2.ingreso"))

    preguntas = (
        Soc2MadurezPregunta.query
        .filter_by(activo=True, tipo="q")
        .order_by(
            Soc2MadurezPregunta.bloque_codigo.asc(),
            Soc2MadurezPregunta.orden.asc(),
            Soc2MadurezPregunta.id.asc()
        )
        .all()
    )

    if not preguntas:
        flash("⚠️ No hay preguntas activas cargadas en el instrumento SOC 2.", "warning")
        return redirect(url_for("madurez_soc2.inicio_soc2"))

    respondidas, total, progreso_pct = calcular_progreso_soc2(preguntas, form_data=request.form)

    try:
        run = None

        if draft_id and draft_id.isdigit():
            run = Soc2MadurezRun.query.filter_by(id=int(draft_id)).first()

        if not run:
            run = obtener_borrador_soc2(user.id if user else None)

        if respondidas == 0:
            if run and _contar_respuestas_run_soc2(run.id) == 0:
                Soc2MadurezRespuesta.query.filter_by(run_id=run.id).delete(synchronize_session=False)
                Soc2MadurezCriterioAnalisis.query.filter_by(run_id=run.id).delete(synchronize_session=False)
                db.session.delete(run)
                db.session.commit()

            flash("⚠️ Debes responder al menos una pregunta antes de guardar o analizar.", "warning")
            return redirect(url_for("madurez_soc2.ingreso"))

        if not run:
            run = Soc2MadurezRun(
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

        Soc2MadurezRespuesta.query.filter_by(run_id=run.id).delete(synchronize_session=False)

        respuestas_insertadas = 0

        for q in preguntas:
            st = (request.form.get(f"st_{q.id}") or "").strip().upper()
            cm = (request.form.get(f"cm_{q.id}") or "").replace("\r\n", "\n").replace("\r", "\n").strip()

            if st in ("SI", "PARCIAL", "NO", "NA"):
                db.session.add(Soc2MadurezRespuesta(
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
                return redirect(url_for("madurez_soc2.ingreso"))

            run.estado = "FINALIZADO"
            run.progreso_pct = 100
            db.session.commit()

            run_id = run_analysis_from_soc2_run(run.id)

            flash(f"✅ Revisión SOC 2 analizada correctamente. Se consolidaron {respuestas_insertadas} respuestas.", "success")
            return redirect(url_for("madurez_soc2.detalle", run_id=run_id))

        db.session.commit()
        flash("✅ Información SOC 2 guardada correctamente.", "success")
        return redirect(url_for("madurez_soc2.ingreso"))

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        flash(f"❌ Error guardando la revisión SOC 2: {e}", "danger")
        return redirect(url_for("madurez_soc2.ingreso"))

# ============================================================
# HISTORIAL SOC 2 — COMPACTO SIN LOADER
# ============================================================

@soc2_madurez_bp.route("/historial", methods=["GET"])
@login_required
def historial():

    user = User.query.get(session.get("user_id"))

    denied = soc2_check_access_or_redirect(
        user,
        "No tiene permiso para ver historial SOC 2."
    )

    if denied:
        return denied

    runs = (
        Soc2MadurezRun.query
        .filter(Soc2MadurezRun.estado == "FINALIZADO")
        .order_by(
            Soc2MadurezRun.created_at.desc(),
            Soc2MadurezRun.id.desc()
        )
        .all()
    )

    # =========================================================
    # BOTÓN NUEVA REVISIÓN
    # =========================================================
    nueva_revision_btn = ""

    if soc2_user_can_execute(user):

        nueva_revision_btn = f"""
        <a href="{url_for('madurez_soc2.ingreso')}"
           class="btn btn-primary btn-sm rounded-pill px-3 fw-bold shadow-sm soc2-no-loader">

          <i class="bi bi-plus-circle me-1"></i>
          Nueva revisión

        </a>
        """

    # =========================================================
    # FILAS
    # =========================================================
    rows = []

    for run in runs:

        nivel = soc2_resolver_nivel(run.pct_general or 0)

        badge = f"""
        <span class="soc2hist-badge"
              style="background:{nivel.get('color','#6c757d')};">

          {escape(nivel.get('nivel','Sin nivel'))}

        </span>
        """

        eliminar_btn = ""

        if soc2_user_can_execute(user):

            eliminar_btn = f"""
            <form method="POST"
                  action="{url_for('madurez_soc2.eliminar_run', run_id=run.id)}"
                  class="d-inline soc2-no-loader"
                  onsubmit="return confirm('¿Seguro que deseas eliminar esta revisión SOC 2?');">

              <button type="submit"
                      class="btn btn-danger btn-xs soc2hist-btn">

                <i class="bi bi-trash"></i>
                Eliminar

              </button>

            </form>
            """

        rows.append(f"""
        <tr>

          <td class="fw-semibold soc2hist-text-main">
            {escape(run.consecutivo or '')}
          </td>

          <td class="text-center soc2hist-text">
            {run.created_at.strftime('%Y-%m-%d %H:%M') if run.created_at else ''}
          </td>

          <td class="text-center">
            <span class="soc2hist-pct">
              {float(run.pct_general or 0):.2f}%
            </span>
          </td>

          <td class="text-center">
            {badge}
          </td>

          <td class="text-center">

            <div class="d-flex justify-content-center gap-1 flex-wrap">

              <a href="{url_for('madurez_soc2.detalle', run_id=run.id)}"
                 class="btn btn-primary btn-xs soc2hist-btn soc2-no-loader">

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

            No existen revisiones SOC 2 finalizadas.

          </td>
        </tr>
        """)

    # =========================================================
    # HTML
    # =========================================================
    content = f"""

    <div class="soc2hist-shell">

      <!-- HEADER -->
      <div class="soc2hist-header-card">

        <div class="soc2hist-header-overlay">

          <div class="soc2hist-header-text">

            <h3 class="soc2hist-title m-0">
              Historial de Revisiones — SOC 2
            </h3>

            <div class="soc2hist-subtitle">
              Consulta de evaluaciones históricas y resultados consolidados.
            </div>

          </div>

        </div>

      </div>

      <!-- BOTONES -->
      <div class="soc2hist-header-actions">

        <a href="{url_for('madurez_soc2.inicio_soc2')}"
           class="btn btn-light btn-sm rounded-pill px-3 fw-bold shadow-sm soc2-no-loader">

          <i class="bi bi-arrow-left me-1"></i>
          Volver

        </a>

        {nueva_revision_btn}

      </div>

      <!-- TABLA -->
      <div class="soc2hist-card">

        <div class="soc2hist-section-title">
          Revisiones finalizadas
        </div>

        <div class="table-responsive">

          <table class="table table-hover align-middle soc2hist-table">

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

      .soc2hist-shell {{
        width:94%;
        max-width:1180px;
        margin:8px auto 24px auto;
      }}

      .soc2hist-header-card {{
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

      .soc2hist-header-overlay {{
        width:100%;
        height:100%;

        display:flex;
        align-items:center;
        justify-content:center;

        text-align:center;

        background:rgba(0,0,0,.08);

        padding:6px 18px;
      }}

      .soc2hist-title {{
        color:#fff;
        font-size:1.28rem;
        font-weight:800;
        line-height:1.1;
        text-shadow:0 2px 8px rgba(0,0,0,.28);
      }}

      .soc2hist-subtitle {{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:3px;
        font-weight:500;
      }}

      .soc2hist-header-actions {{
        display:flex;
        justify-content:center;
        align-items:center;
        gap:6px;
        flex-wrap:wrap;
        margin:8px 0 10px 0;
      }}

      .soc2hist-card {{
        background:rgba(255,255,255,.95);
        border:1px solid rgba(255,255,255,.60);
        border-radius:16px;
        box-shadow:0 10px 24px rgba(0,0,0,.20);
        padding:12px;
        overflow:hidden;
      }}

      .soc2hist-section-title {{
        color:#0f3d68;
        font-size:.92rem;
        font-weight:800;
        margin-bottom:8px;
        padding-bottom:6px;
        border-bottom:1px solid rgba(15,61,104,.12);
      }}

      .soc2hist-table {{
        margin-bottom:0;
        font-size:.80rem;
      }}

      .soc2hist-table thead th {{
        background:#0f3d68;
        color:#fff;
        font-size:.74rem;
        font-weight:800;
        padding:7px 8px;
        vertical-align:middle;
        white-space:nowrap;
      }}

      .soc2hist-table tbody td {{
        padding:6px 8px;
        vertical-align:middle;
        background:rgba(255,255,255,.96);
        border-bottom:1px solid rgba(15,61,104,.08);
      }}

      .soc2hist-table tbody tr:hover td {{
        background:#eef6ff;
      }}

      .soc2hist-text-main {{
        color:#0b1220;
        font-size:.80rem;
      }}

      .soc2hist-text {{
        color:#374151;
        font-size:.68rem;
      }}

      .soc2hist-pct {{
        color:#0d6efd;
        font-weight:800;
        font-size:.80rem;
      }}

      .soc2hist-badge {{
        display:inline-block;
        color:#fff;
        font-size:.68rem;
        font-weight:800;
        padding:4px 8px;
        border-radius:999px;
        line-height:1;
        white-space:nowrap;
      }}

      .soc2hist-btn {{
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
        document.querySelectorAll(".soc2-no-loader").forEach(function(el) {{

          el.removeAttribute("onclick");
          el.onclick = null;

        }});

      }});

    </script>
    """

    return render_template_string(
        BASE,
        title="Historial SOC 2",
        content=content
    )


# ============================================================
# SOC 2 — DETALLE POR CRITERIO
# ============================================================

@soc2_madurez_bp.route("/detalle/<int:run_id>/criterio/<bloque_codigo>", methods=["GET"])
@login_required
def detalle_criterio(run_id: int, bloque_codigo: str):
    user = User.query.get(session.get("user_id"))

    if not soc2_user_can_access(user):
        return soc2_deny_access("No tiene permiso para ver el detalle del criterio SOC 2.")

    run = Soc2MadurezRun.query.get_or_404(run_id)
    bloque_codigo = (bloque_codigo or "").strip().upper()

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    d = resumen.get(bloque_codigo)
    if not d:
        flash("No se encontró información para este criterio SOC 2.", "warning")
        return redirect(url_for("madurez_soc2.detalle", run_id=run.id))

    items = d.get("items", []) or []
    nombre = d.get("nombre") or soc2_block_title(bloque_codigo) or bloque_codigo
    pct = float(d.get("pct", 0) or 0)
    nivel = soc2_nivel_visual_por_pct(pct)

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
            <h3 class="nistdet-title m-0">Preguntas SOC 2 — {escape(nombre)}</h3>
            <div class="nistdet-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
              · Cumplimiento: <b>{pct:.2f}%</b>
              · Nivel: <b>{escape(nivel.get("nivel",""))}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="nistdet-header-actions">
        <a href="{url_for('madurez_soc2.detalle', run_id=run.id)}"
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

    {soc2_nist_css('nistdet', '📊')}
    """

    return render_template_string(BASE, title="Detalle criterio SOC 2", content=content)


# ============================================================
# SOC 2 — ANÁLISIS POR CRITERIO
# ============================================================

@soc2_madurez_bp.route("/detalle/<int:run_id>/criterio/<bloque_codigo>/analisis", methods=["GET", "POST"])
@login_required
def analisis_criterio(run_id: int, bloque_codigo: str):
    user = User.query.get(session.get("user_id"))

    if not soc2_user_can_access(user):
        return soc2_deny_access("No tiene permiso para ver el análisis SOC 2.")

    run = Soc2MadurezRun.query.get_or_404(run_id)
    bloque_codigo = (bloque_codigo or "").strip().upper()

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    d = resumen.get(bloque_codigo)
    if not d:
        flash("No se encontró información para este criterio SOC 2.", "warning")
        return redirect(url_for("madurez_soc2.detalle", run_id=run.id))

    nombre = d.get("nombre") or soc2_block_title(bloque_codigo) or bloque_codigo
    pct = float(d.get("pct", 0) or 0)
    items = d.get("items", []) or []

    analisis = Soc2MadurezCriterioAnalisis.query.filter_by(
        run_id=run.id,
        bloque_codigo=bloque_codigo
    ).first()

    if request.method == "POST":
        if not soc2_user_can_execute(user):
            return soc2_deny_execute("El rol Auditor no puede generar análisis con IA.")

        prompt = _soc2_ai_prompt_criterio(run, bloque_codigo, nombre, pct, items)

        try:
            raw = _soc2_ai_text(prompt, max_tokens=1200)
            obj = _extraer_json_objeto_soc2(raw)

            estado_actual = (obj.get("estado_actual") or "").strip() if isinstance(obj, dict) else ""
            estado_requerido = (obj.get("estado_requerido") or "").strip() if isinstance(obj, dict) else ""
            plan_raw = json.dumps(obj.get("plan_accion", []), ensure_ascii=False) if isinstance(obj, dict) else raw
            plan_txt = _build_plan_accion_soc2_texto(obj.get("plan_accion", [])) if isinstance(obj, dict) else raw

            if not analisis:
                analisis = Soc2MadurezCriterioAnalisis(
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

            flash("✅ Análisis SOC 2 generado con IA.", "success")

        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            flash(f"❌ Error generando análisis SOC 2: {e}", "danger")

        return redirect(url_for("madurez_soc2.analisis_criterio", run_id=run.id, bloque_codigo=bloque_codigo))

    estado_actual = analisis.estado_actual if analisis else ""
    estado_requerido = analisis.estado_requerido if analisis else ""
    plan_accion = _normalizar_plan_accion_soc2_texto(
        (analisis.plan_accion_editado or analisis.plan_accion_ai) if analisis else ""
    )

    boton_generar = ""
    if soc2_user_can_execute(user):
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
            <h3 class="nistdet-title m-0">Análisis SOC 2 — {escape(nombre)}</h3>
            <div class="nistdet-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
              · Cumplimiento: <b>{pct:.2f}%</b>
            </div>
          </div>
        </div>
      </div>

      <div class="nistdet-header-actions">
        <a href="{url_for('madurez_soc2.detalle', run_id=run.id)}"
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

    {soc2_nist_css('nistdet', '📊')}
    """

    return render_template_string(BASE, title="Análisis criterio SOC 2", content=content)

# ============================================================
# DETALLE SOC 2 — MISMO DISEÑO NIST
# ============================================================

@soc2_madurez_bp.route("/detalle/<int:run_id>", methods=["GET"])
@login_required
def detalle(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not soc2_user_can_access(user):
        return soc2_deny_access("No tiene permiso para ver el detalle SOC 2.")

    run = Soc2MadurezRun.query.get_or_404(run_id)

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    if not resumen:
        run_analysis_from_soc2_run(run.id)
        run = Soc2MadurezRun.query.get_or_404(run.id)
        try:
            resumen = json.loads(run.resumen_json or "{}")
        except Exception:
            resumen = {}

    def _nl2br_soc2(s: str) -> str:
        txt = soc2_normalizar_texto_rico_guardado(s or "")
        return txt.replace("\n", "<br>")

    radar_labels, radar_values = soc2_pct_por_criterio(resumen, SOC2_BLOCK_ORDER)
    radar_b64 = run.radar_overall_b64 or soc2_radar_b64(
        radar_labels,
        radar_values,
        title="Radar por Criterio"
    )

    informe_ai = soc2_normalizar_texto_rico_guardado(run.informe_ejecutivo_ai or "")
    informe_editado = soc2_normalizar_texto_rico_guardado(run.informe_ejecutivo_editado or "")
    informe_mostrar = informe_editado if informe_editado else informe_ai

    nivel_general = soc2_nivel_visual_por_pct(run.pct_general)
    nivel_general_texto = (nivel_general.get("nivel") or "").strip()
    nivel_general_nombre = nivel_general_texto.split(":", 1)[1].strip() if ":" in nivel_general_texto else nivel_general_texto

    botones_ia = ""
    if soc2_user_can_execute(user):
        botones_ia = f"""
          <form method="POST"
                  action="{url_for('madurez_soc2.informe_ejecutivo_generar', run_id=run.id)}"
                  class="m-0">
              <button type="submit" class="btn nistdet-btn-success rounded-pill px-4 fw-bold">
                <i class="bi bi-magic me-2"></i>Generar con IA
              </button>
            </form>

            <a href="{url_for('madurez_soc2.informe_ejecutivo_editar', run_id=run.id)}"
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
    if soc2_user_can_access(user):
        pdf_btn = f"""
        <a href="{url_for('madurez_soc2.exportar_pdf', run_id=run.id)}"
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
              <div class="nistdet-card-title">📊 Radar por Criterio General</div>
              <div class="text-muted small">
                Resultado consolidado por criterios SOC 2.
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
                Síntesis ejecutiva generada con IA a partir de los resultados por criterio SOC 2.
              </div>
            </div>

            <div class="d-flex gap-2 flex-wrap">
              {botones_ia}
            </div>
          </div>

          <div class="nistdet-exec-box mt-3">
            {f'<div class="nistdet-exec-text">{_nl2br_soc2(escape(informe_mostrar))}</div>' if informe_mostrar else '''
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

    for code in SOC2_BLOCK_ORDER:
        if code not in resumen:
            continue

        d = resumen.get(code, {}) or {}

        pct = float(d.get("pct", 0) or 0)
        total = int(d.get("total", 0) or 0)
        nombre_criterio = (d.get("nombre") or soc2_block_title(code) or code).strip()

        nivel_data = soc2_nivel_visual_por_pct(pct)
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
                <div class="nistdet-label">Ítems</div>
                <div class="nistdet-value fw-bold">{total}</div>
              </div>

              <div class="nistdet-row nistdet-row-actions">
                <div class="nistdet-label">Acciones</div>
                <div class="nistdet-value">
                  <div class="d-flex flex-wrap gap-2">
                    <a class="btn btn-sm btn-outline-primary rounded-pill"
                       href="{url_for('madurez_soc2.detalle_criterio', run_id=run.id, bloque_codigo=code)}">
                      <i class="bi bi-list-check me-1"></i>Ver preguntas
                    </a>

                    <a class="btn btn-sm btn-outline-dark rounded-pill"
                       href="{url_for('madurez_soc2.analisis_criterio', run_id=run.id, bloque_codigo=code)}">
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
          <div class="nistdet-section-title">SOC 2 — Trust Services Criteria</div>
          <div class="text-muted small">
            Resultado detallado por criterios SOC 2.
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
            <h3 class="nistdet-title m-0">Resultado de Madurez — SOC 2</h3>
            <div class="nistdet-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
              · Cumplimiento general: <b>{run.pct_general:.2f}%</b>
              · Nivel general: <b>{escape(nivel_general_nombre)}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="nistdet-header-actions">
        <a href="{url_for('madurez_soc2.historial')}"
           class="btn nistdet-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al historial
        </a>

        <a href="{url_for('madurez_soc2.inicio_soc2')}"
           class="btn nistdet-btn-soft rounded-pill px-4 fw-bold">
          <i class="bi bi-house-door-fill me-2"></i>Volver al módulo
        </a>

        {pdf_btn}
      </div>

      {top_html}

      {capitulo_cards}

    </div>

    {soc2_nist_css('nistdet', '📊')}
    """
    return render_template_string(BASE, title="Detalle SOC 2", content=content)


# Alias por compatibilidad si tu menú anterior apuntaba a resultado
@soc2_madurez_bp.route("/resultado/<int:run_id>", methods=["GET"])
@login_required
def resultado(run_id: int):
    return detalle(run_id)

# ============================================================
# SOC 2 — PROMPT INFORME EJECUTIVO IA
# ============================================================

def _soc2_prompt_informe_ejecutivo(run: "Soc2MadurezRun", resumen: dict) -> str:
    """
    Prompt para generar informe ejecutivo SOC 2.
    Lo usa informe_ejecutivo_generar().
    """

    lineas = []

    for code in SOC2_BLOCK_ORDER:
        d = (resumen or {}).get(code)
        if not d:
            continue

        lineas.append(
            f"- {d.get('nombre') or soc2_block_title(code) or code}: "
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
Eres un consultor senior experto en SOC 2, auditoría de controles, gobierno de seguridad de la información y Trust Services Criteria.

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
- Explica el estado general de madurez SOC 2.
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

@soc2_madurez_bp.route("/detalle/<int:run_id>/informe-ejecutivo/generar", methods=["POST"])
@login_required
def informe_ejecutivo_generar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not soc2_user_can_execute(user):
        return soc2_deny_execute("El perfil Auditor no puede generar el informe ejecutivo con IA.")

    run = Soc2MadurezRun.query.get_or_404(run_id)

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    if not resumen:
        flash("⚠️ No hay resultados consolidados para generar el informe ejecutivo.", "warning")
        return redirect(url_for("madurez_soc2.detalle", run_id=run.id))

    try:
        raw = _soc2_ai_text(
            _soc2_prompt_informe_ejecutivo(run, resumen),
            max_tokens=1200
        )

        obj = _extraer_json_objeto_soc2(raw)

        if isinstance(obj, dict):
            informe_ai = (
                obj.get("informe_ejecutivo")
                or obj.get("informe")
                or obj.get("resumen_ejecutivo")
                or obj.get("texto")
                or ""
            )
        else:
            informe_ai = raw or ""

        informe_ai = soc2_normalizar_texto_rico_guardado(informe_ai)

        if not informe_ai:
            raise RuntimeError("La IA no devolvió un informe válido.")

        run.informe_ejecutivo_ai = informe_ai
        run.informe_ejecutivo_editado = informe_ai
        run.updated_at = datetime.utcnow()

        db.session.add(run)
        db.session.commit()

        flash("✅ Informe ejecutivo SOC 2 generado con IA.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error llamando IA para el informe ejecutivo: {e}", "danger")

    return redirect(url_for("madurez_soc2.detalle", run_id=run.id))


@soc2_madurez_bp.route("/detalle/<int:run_id>/informe-ejecutivo/editar", methods=["GET", "POST"])
@login_required
def informe_ejecutivo_editar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not soc2_user_can_execute(user):
        return soc2_deny_execute("El perfil Auditor no puede editar el informe ejecutivo.")

    run = Soc2MadurezRun.query.get_or_404(run_id)

    if request.method == "POST":
        texto_form = request.form.get("informe") or ""
        texto_limpio = soc2_normalizar_texto_rico_guardado(texto_form)

        run.informe_ejecutivo_editado = texto_limpio
        run.updated_at = datetime.utcnow()

        db.session.add(run)
        db.session.commit()

        flash("✅ Informe ejecutivo SOC 2 actualizado.", "success")
        return redirect(url_for("madurez_soc2.detalle", run_id=run.id))

    texto = run.informe_ejecutivo_editado or run.informe_ejecutivo_ai or ""
    texto = soc2_normalizar_texto_rico_guardado(texto)

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
        <h3 class="nistdet-title m-0">Editar Informe Ejecutivo — SOC 2</h3>
      </div>
    </div>
  </div>

  <form method="POST" class="nistdet-card p-4">
    <textarea name="informe" rows="18" class="form-control">{escape(texto)}</textarea>

    <div class="text-end mt-3">
      <a href="{url_for('madurez_soc2.detalle', run_id=run.id)}"
         class="btn btn-secondary rounded-pill px-4">
        Cancelar
      </a>

      <button class="btn btn-primary rounded-pill px-4 fw-bold">
        Guardar
      </button>
    </div>
  </form>
</div>
{soc2_nist_css('nistdet', '✍️')}
"""
    return render_template_string(BASE, title="Editar Informe Ejecutivo SOC 2", content=content)


@soc2_madurez_bp.route("/detalle/<int:run_id>/plan-trabajo/generar", methods=["POST"])
@login_required
def plan_trabajo_generar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not soc2_user_can_execute(user):
        return soc2_deny_execute("El perfil Auditor no puede generar el plan de trabajo con IA.")

    run = Soc2MadurezRun.query.get_or_404(run_id)
    resumen = json.loads(run.resumen_json or "{}")

    try:
        raw = _soc2_ai_text(_soc2_prompt_plan_trabajo(run, resumen), max_tokens=1600)
        obj = _extraer_json_objeto_soc2(raw)
        plan = obj.get("plan_trabajo") if isinstance(obj, dict) else None
        plan_txt = _build_plan_accion_soc2_texto(plan) if isinstance(plan, list) else raw
        plan_txt = soc2_normalizar_texto_rico_guardado(plan_txt)

        if not plan_txt:
            raise RuntimeError("La IA no devolvió un plan válido.")

        run.plan_trabajo_ai = plan_txt
        run.plan_trabajo_editado = plan_txt
        db.session.commit()

        flash("✅ Plan de trabajo SOC 2 generado con IA.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error generando plan de trabajo: {e}", "danger")

    return redirect(url_for("madurez_soc2.detalle", run_id=run.id))


@soc2_madurez_bp.route("/detalle/<int:run_id>/plan-trabajo/editar", methods=["GET", "POST"])
@login_required
def plan_trabajo_editar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not soc2_user_can_execute(user):
        return soc2_deny_execute("El perfil Auditor no puede editar el plan de trabajo.")

    run = Soc2MadurezRun.query.get_or_404(run_id)

    if request.method == "POST":
        run.plan_trabajo_editado = (request.form.get("plan") or "").strip()
        db.session.commit()
        flash("✅ Plan de trabajo SOC 2 actualizado.", "success")
        return redirect(url_for("madurez_soc2.detalle", run_id=run.id))

    texto = run.plan_trabajo_editado or run.plan_trabajo_ai or ""

    content = f"""
<div class="nistdet-shell">
  <div class="nistdet-header-card">
    <div class="nistdet-header-overlay">
      <div class="nistdet-header-text">
        <h3 class="nistdet-title m-0">Editar Plan de Trabajo — SOC 2</h3>
      </div>
    </div>
  </div>

  <form method="POST" class="nistdet-card p-4">
    <textarea name="plan" rows="18" class="form-control">{escape(texto)}</textarea>
    <div class="text-end mt-3">
      <a href="{url_for('madurez_soc2.detalle', run_id=run.id)}" class="btn btn-secondary rounded-pill px-4">Cancelar</a>
      <button class="btn btn-success rounded-pill px-4 fw-bold">Guardar</button>
    </div>
  </form>
</div>
{soc2_nist_css('nistdet', '✍️')}
"""
    return render_template_string(BASE, title="Editar Plan SOC 2", content=content)

# ============================================================
# PDF EJECUTIVO SOC 2
# ============================================================

def _soc2_build_pdf_run(run: "Soc2MadurezRun") -> io.BytesIO:
    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    labels, values = soc2_pct_por_criterio(resumen, SOC2_BLOCK_ORDER)
    radar_b64 = run.radar_overall_b64 or soc2_radar_b64(
        labels,
        values,
        title="Radar por Criterio - SOC 2"
    )

    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
        title="SOC 2 - Informe Ejecutivo"
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="SOC2_Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="SOC2_Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#1d4f8f"),
        spaceBefore=10,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="SOC2_Normal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#101827"),
        spaceAfter=5
    ))

    styles.add(ParagraphStyle(
        name="SOC2_Small",
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
        [[Paragraph("SOC 2 - Informe de Madurez", styles["SOC2_Title"])]],
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

    nivel_general = soc2_resolver_nivel(run.pct_general)

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

    story.append(Paragraph("Informe Ejecutivo", styles["SOC2_Section"]))

    informe = soc2_normalizar_texto_rico_guardado(
        run.informe_ejecutivo_editado or run.informe_ejecutivo_ai or ""
    )

    if informe:
        for parrafo in re.split(r"\n\s*\n", informe):
            if parrafo.strip():
                story.append(Paragraph(pdf_escape(parrafo.strip()), styles["SOC2_Normal"]))
    else:
        story.append(Paragraph("No hay informe ejecutivo registrado.", styles["SOC2_Normal"]))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Radar por Criterio SOC 2", styles["SOC2_Section"]))

    if radar_b64:
        try:
            img = RLImage(
                io.BytesIO(base64.b64decode(radar_b64)),
                width=11.5 * cm,
                height=11.0 * cm
            )
            story.append(img)
        except Exception:
            story.append(Paragraph("No fue posible insertar el radar.", styles["SOC2_Normal"]))

    story.append(Paragraph("Detalle por Criterio", styles["SOC2_Section"]))

    data = [[
        "Criterio",
        "% Cumplimiento",
        "Nivel",
        "SI",
        "Parcial",
        "NO",
        "N/A",
        "Ítems"
    ]]

    for code in SOC2_BLOCK_ORDER:
        d = resumen.get(code)
        if not d:
            continue

        data.append([
            Paragraph(pdf_escape(d.get("nombre") or code), styles["SOC2_Small"]),
            Paragraph(f"{float(d.get('pct', 0) or 0):.2f}%", styles["SOC2_Small"]),
            Paragraph(pdf_escape(d.get("madurez") or ""), styles["SOC2_Small"]),
            str(d.get("SI", 0)),
            str(d.get("PARCIAL", 0)),
            str(d.get("NO", 0)),
            str(d.get("NA", 0)),
            str(d.get("total", 0)),
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

    plan = _normalizar_plan_accion_soc2_texto(
        run.plan_trabajo_editado or run.plan_trabajo_ai or ""
    )

    if plan:
        story.append(PageBreak())
        story.append(Paragraph("Plan de Trabajo", styles["SOC2_Section"]))

        for parrafo in re.split(r"\n\s*\n", plan):
            if parrafo.strip():
                story.append(Paragraph(pdf_escape(parrafo.strip()), styles["SOC2_Normal"]))

    doc.build(story)
    buf.seek(0)
    return buf

# ============================================================
# EXPORTAR PDF — ADMIN / USUARIO CON PERMISO / AUDITOR
# ============================================================

@soc2_madurez_bp.route("/detalle/<int:run_id>/pdf", methods=["GET"])
@login_required
def exportar_pdf(run_id: int):
    user = User.query.get(session.get("user_id"))

    # ✅ Auditor también puede exportar/imprimir PDF
    denied = soc2_check_access_or_redirect(
        user,
        "No tiene permiso para exportar PDF SOC 2."
    )
    if denied:
        return denied

    run = Soc2MadurezRun.query.get_or_404(run_id)

    pdf = _soc2_build_pdf_run(run)

    filename = f"SOC2_Madurez_{re.sub(r'[^A-Za-z0-9_-]+', '_', run.consecutivo or str(run.id))}.pdf"

    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )


# ============================================================
# ELIMINAR — AUDITOR NO PUEDE
# ============================================================

@soc2_madurez_bp.route("/detalle/<int:run_id>/eliminar", methods=["POST"])
@login_required
def eliminar_run(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not soc2_user_can_execute(user):
        return soc2_deny_execute("El perfil Auditor no puede eliminar revisiones SOC 2.")

    run = Soc2MadurezRun.query.get_or_404(run_id)

    try:
        Soc2MadurezCriterioAnalisis.query.filter_by(run_id=run.id).delete(synchronize_session=False)
        Soc2MadurezRespuesta.query.filter_by(run_id=run.id).delete(synchronize_session=False)
        db.session.delete(run)
        db.session.commit()
        flash("✅ Revisión SOC 2 eliminada correctamente.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error eliminando revisión SOC 2: {e}", "danger")

    return redirect(url_for("madurez_soc2.historial"))


# ============================================================
# CSS — COPIA DE PATRÓN NIST
# ============================================================
def soc2_nist_css(prefix, icon, subtitle_label="SOC 2"):
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


def soc2_nistform_css():
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
        content:"SGSI · Evaluación NIST CSF 2.0";
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
#                                                   Fin Módulo de Madurez SOC 2 — Diseño NIST
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                   Módulo de Madurez ISO 22301 — Diseño NIST
# ==========================================================================================================================================

iso22301_madurez_bp = Blueprint("madurez_iso22301", __name__, url_prefix="/madurez_iso22301")

# GRAC-RAM: colors se carga bajo demanda
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
# GRAC-RAM: importación diferida: from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
Image = _GRACDeferredSymbol("reportlab.platypus", "Image")

# ============================================================
# BASE DE DATOS INDEPENDIENTE — ISO 22301
# ============================================================
ISO22301_DB_PATH = os.path.join(app.instance_path, "iso22301_madurez.db")
os.makedirs(app.instance_path, exist_ok=True)

app.config.setdefault("SQLALCHEMY_BINDS", {})
app.config["SQLALCHEMY_BINDS"]["iso22301_madurez"] = "sqlite:///" + ISO22301_DB_PATH

ISO22301_PERMISSION_NAME = "Nivel de Madurez ISO 22301"
ISO22301_INSTRUMENTO_TEMPLATE_XLSX = os.path.join(BASE_DIR, "static", "templates", "Arkyntech_Matriz_Madurez_ISO_22301_ES.xlsx")

ISO22301_STATUS_SCORE = {
    "SI": 100,
    "PARCIAL": 50,
    "NO": 0,
    "NA": 0,  # Valor visible 0; se excluye explícitamente del denominador.
}

ISO22301_BLOCK_ORDER = ["4", "5", "6", "7", "8", "9", "10"]

ISO22301_BLOCK_TITLES = {
    "4": "Contexto de la organización",
    "5": "Liderazgo",
    "6": "Planificación",
    "7": "Apoyo",
    "8": "Operación",
    "9": "Evaluación del desempeño",
    "10": "Mejora",
}

# Catálogo original de Arkyntech. Permite inicializar la base independiente
# incluso cuando el Excel todavía no se ha copiado a static/templates.
ISO22301_EMBEDDED_CATALOG = [{'item_id': 'BCP-001',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.1',
  'domain_es': 'Contexto interno y externo',
  'assessment_question_es': 'La organización identifica las condiciones internas que pueden afectar su capacidad para mantener productos y '
                            'servicios prioritarios.',
  'suggested_evidence_es': 'Análisis de contexto, mapa de procesos, diagnóstico organizacional, actas de revisión.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-002',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.1',
  'domain_es': 'Contexto interno y externo',
  'assessment_question_es': 'La organización identifica factores externos que pueden originar interrupciones o modificar sus necesidades '
                            'de continuidad.',
  'suggested_evidence_es': 'Análisis PESTEL, escenarios de amenaza, informes sectoriales y regulatorios.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-003',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.1',
  'domain_es': 'Contexto interno y externo',
  'assessment_question_es': 'Los temas de continuidad se relacionan explícitamente con la estrategia, los objetivos y el apetito de riesgo '
                            'de la organización.',
  'suggested_evidence_es': 'Plan estratégico, declaración de apetito de riesgo, mapa de objetivos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-004',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.1',
  'domain_es': 'Contexto interno y externo',
  'assessment_question_es': 'Se revisan periódicamente los cambios del contexto y sus efectos sobre el sistema de continuidad.',
  'suggested_evidence_es': 'Calendario de revisión, actas, registro de cambios y decisiones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-005',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.1',
  'domain_es': 'Cambio climático — Enmienda 2024',
  'assessment_question_es': 'Se ha evaluado y documentado si el cambio climático es un asunto pertinente para la continuidad del negocio.',
  'suggested_evidence_es': 'Evaluación de pertinencia climática, escenarios físicos y de transición, conclusión aprobada.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-006',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.2',
  'domain_es': 'Partes interesadas',
  'assessment_question_es': 'Se mantienen identificadas las partes interesadas relevantes para la continuidad del negocio.',
  'suggested_evidence_es': 'Matriz de partes interesadas y responsables de relación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-007',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.2',
  'domain_es': 'Necesidades y expectativas',
  'assessment_question_es': 'Se conocen y actualizan las necesidades de continuidad de clientes, autoridades, empleados, proveedores y '
                            'socios críticos.',
  'suggested_evidence_es': 'Matriz de requisitos, contratos, SLA, comunicaciones y encuestas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-008',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.2.2',
  'domain_es': 'Requisitos legales y regulatorios',
  'assessment_question_es': 'Existe un inventario vigente de obligaciones legales, regulatorias y contractuales relacionadas con '
                            'continuidad.',
  'suggested_evidence_es': 'Matriz legal, circulares regulatorias, contratos, concepto jurídico.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-009',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.2.2',
  'domain_es': 'Cumplimiento',
  'assessment_question_es': 'Se asignan responsables y mecanismos para evaluar el cumplimiento de las obligaciones de continuidad.',
  'suggested_evidence_es': 'Evaluaciones de cumplimiento, responsables, hallazgos y planes de cierre.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-010',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.2',
  'domain_es': 'Cambio climático — Enmienda 2024',
  'assessment_question_es': 'Se consideran requisitos o expectativas de partes interesadas relacionados con cambio climático cuando '
                            'resultan pertinentes.',
  'suggested_evidence_es': 'Matriz de interesados, compromisos ESG, contratos, exigencias de autoridades o clientes.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-011',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.3',
  'domain_es': 'Alcance del SGCN',
  'assessment_question_es': 'El alcance define límites organizacionales, ubicaciones, procesos, productos, servicios y dependencias '
                            'incluidos.',
  'suggested_evidence_es': 'Declaración de alcance aprobada y mapa de cobertura.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-012',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.3',
  'domain_es': 'Alcance del SGCN',
  'assessment_question_es': 'La definición del alcance utiliza el contexto, las obligaciones y las necesidades de las partes interesadas.',
  'suggested_evidence_es': 'Trazabilidad del alcance con análisis de contexto y matriz de requisitos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-013',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.3',
  'domain_es': 'Alcance del SGCN',
  'assessment_question_es': 'Las interfaces con procesos, sedes, terceros y servicios fuera del alcance están identificadas y gestionadas.',
  'suggested_evidence_es': 'Mapa de interfaces, contratos, RACI y dependencias.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-014',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.3',
  'domain_es': 'Alcance del SGCN',
  'assessment_question_es': 'La declaración de alcance está documentada, aprobada, disponible y sujeta a control de cambios.',
  'suggested_evidence_es': 'Documento vigente, aprobación, historial de versiones y publicación interna.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-015',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.4',
  'domain_es': 'Sistema de gestión',
  'assessment_question_es': 'Los procesos necesarios del sistema de continuidad y sus interacciones están definidos.',
  'suggested_evidence_es': 'Mapa de procesos del SGCN, fichas de proceso y entradas/salidas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-016',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.4',
  'domain_es': 'Sistema de gestión',
  'assessment_question_es': 'Se asignan criterios, métodos, responsables y recursos para operar y controlar el sistema de continuidad.',
  'suggested_evidence_es': 'Procedimientos, indicadores, RACI, presupuesto y cronograma.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-017',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.4',
  'domain_es': 'Sistema de gestión',
  'assessment_question_es': 'El sistema se mantiene y mejora con base en resultados, cambios, incidentes y lecciones aprendidas.',
  'suggested_evidence_es': 'Plan de mejora, revisiones, informes de incidentes y seguimiento.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-018',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.1',
  'domain_es': 'Liderazgo y compromiso',
  'assessment_question_es': 'La alta dirección asume responsabilidad por la eficacia del sistema de continuidad.',
  'suggested_evidence_es': 'Actas de comité, decisiones, asignación de responsables y seguimiento ejecutivo.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-019',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.1',
  'domain_es': 'Integración',
  'assessment_question_es': 'Los requisitos de continuidad están integrados en procesos de negocio, proyectos, cambios y decisiones '
                            'relevantes.',
  'suggested_evidence_es': 'Metodologías corporativas, controles de proyecto y criterios de aprobación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-020',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.1',
  'domain_es': 'Recursos y apoyo',
  'assessment_question_es': 'La alta dirección asegura recursos suficientes para establecer, operar, probar y mejorar la continuidad.',
  'suggested_evidence_es': 'Presupuesto, capacidad de personal, herramientas, contratos y aprobaciones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-021',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.1',
  'domain_es': 'Comunicación directiva',
  'assessment_question_es': 'Los líderes comunican la importancia de una continuidad eficaz y del cumplimiento de los compromisos '
                            'definidos.',
  'suggested_evidence_es': 'Comunicaciones, sesiones ejecutivas, campañas y registros de asistencia.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-022',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.1',
  'domain_es': 'Resultados',
  'assessment_question_es': 'La dirección promueve el logro de resultados, la colaboración entre áreas y la mejora continua.',
  'suggested_evidence_es': 'Indicadores, compromisos de áreas, actas y reconocimientos o acciones correctivas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-023',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.2',
  'domain_es': 'Política de continuidad',
  'assessment_question_es': 'Existe una política adecuada al propósito, contexto y dirección estratégica de la organización.',
  'suggested_evidence_es': 'Política vigente, aprobación y relación con estrategia y alcance.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-024',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.2',
  'domain_es': 'Política de continuidad',
  'assessment_question_es': 'La política incluye compromisos de cumplimiento de requisitos y mejora continua.',
  'suggested_evidence_es': 'Texto de la política y evidencias de aprobación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-025',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.2',
  'domain_es': 'Política de continuidad',
  'assessment_question_es': 'La política proporciona un marco para definir y revisar objetivos de continuidad.',
  'suggested_evidence_es': 'Trazabilidad entre política, objetivos, indicadores y planes.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-026',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.2.2',
  'domain_es': 'Comunicación de la política',
  'assessment_question_es': 'La política está disponible, se comunica dentro de la organización y se comparte externamente cuando '
                            'corresponde.',
  'suggested_evidence_es': 'Intranet, inducción, comunicaciones a terceros y evidencia de acceso.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-027',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.3',
  'domain_es': 'Roles y autoridades',
  'assessment_question_es': 'Se asignan y comunican responsabilidades y autoridades para los roles del sistema de continuidad.',
  'suggested_evidence_es': 'RACI, perfiles de cargo, nombramientos y comunicaciones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-028',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.3',
  'domain_es': 'Gobierno del SGCN',
  'assessment_question_es': 'Existe una instancia de gobierno con autoridad para decidir, escalar y supervisar el desempeño del sistema.',
  'suggested_evidence_es': 'Términos de referencia del comité, calendario, actas y decisiones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-029',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.3',
  'domain_es': 'Reporte a la dirección',
  'assessment_question_es': 'Está definida la responsabilidad de informar a la alta dirección sobre desempeño, brechas y oportunidades de '
                            'mejora.',
  'suggested_evidence_es': 'Informes ejecutivos, tablero, frecuencia y destinatarios.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-030',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.1',
  'domain_es': 'Riesgos y oportunidades del SGCN',
  'assessment_question_es': 'Se determinan riesgos que podrían impedir que el sistema logre los resultados previstos.',
  'suggested_evidence_es': 'Registro de riesgos del SGCN, causas, consecuencias y controles.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-031',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.1',
  'domain_es': 'Riesgos y oportunidades del SGCN',
  'assessment_question_es': 'Se identifican oportunidades para fortalecer la resiliencia y mejorar el sistema.',
  'suggested_evidence_es': 'Registro de oportunidades, iniciativas, responsables y beneficios esperados.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-032',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.1',
  'domain_es': 'Tratamiento',
  'assessment_question_es': 'Las acciones para tratar riesgos y oportunidades están integradas en procesos y planes de trabajo.',
  'suggested_evidence_es': 'Planes de tratamiento, portafolio de iniciativas y seguimiento.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-033',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.1',
  'domain_es': 'Evaluación de eficacia',
  'assessment_question_es': 'Se evalúa si las acciones tomadas frente a riesgos y oportunidades fueron eficaces.',
  'suggested_evidence_es': 'Indicadores, revisiones, resultados de pruebas y cierre de acciones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-034',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.2',
  'domain_es': 'Objetivos de continuidad',
  'assessment_question_es': 'Se establecen objetivos coherentes con la política y pertinentes para las funciones y niveles aplicables.',
  'suggested_evidence_es': 'Matriz de objetivos, aprobación y despliegue por áreas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-035',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.2',
  'domain_es': 'Objetivos de continuidad',
  'assessment_question_es': 'Los objetivos son medibles cuando es posible, se monitorean y se actualizan según necesidad.',
  'suggested_evidence_es': 'Indicadores, metas, periodicidad, resultados y revisiones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-036',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.2',
  'domain_es': 'Planificación de objetivos',
  'assessment_question_es': 'Cada objetivo define actividades, recursos, responsable, plazo y método para evaluar resultados.',
  'suggested_evidence_es': 'Ficha de objetivo, plan de trabajo, presupuesto y criterio de éxito.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-037',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.2',
  'domain_es': 'Comunicación de objetivos',
  'assessment_question_es': 'Los objetivos se comunican a las personas y partes relevantes para su cumplimiento.',
  'suggested_evidence_es': 'Comunicaciones, tableros, reuniones y compromisos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-038',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.3',
  'domain_es': 'Cambios del SGCN',
  'assessment_question_es': 'Los cambios del sistema se planifican considerando propósito, consecuencias, integridad, recursos y '
                            'responsabilidades.',
  'suggested_evidence_es': 'Procedimiento de cambios, análisis de impacto y aprobaciones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-039',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.1',
  'domain_es': 'Recursos',
  'assessment_question_es': 'Se identifican y proveen recursos humanos, tecnológicos, físicos, financieros y de información para el SGCN.',
  'suggested_evidence_es': 'Plan de recursos, presupuesto, inventarios y contratos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-040',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.1',
  'domain_es': 'Disponibilidad de recursos',
  'assessment_question_es': 'Los recursos críticos de respuesta y recuperación están disponibles dentro de los tiempos requeridos.',
  'suggested_evidence_es': 'Pruebas de disponibilidad, inventarios, acuerdos y tiempos de activación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-041',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.2',
  'domain_es': 'Competencia',
  'assessment_question_es': 'Se han definido las competencias requeridas para roles que afectan el desempeño de continuidad.',
  'suggested_evidence_es': 'Perfiles, matriz de competencias y roles de crisis.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-042',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.2',
  'domain_es': 'Competencia',
  'assessment_question_es': 'Las personas asignadas demuestran competencia mediante formación, experiencia o evaluación.',
  'suggested_evidence_es': 'Certificados, experiencia, evaluaciones y observación en ejercicios.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-043',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.2',
  'domain_es': 'Desarrollo de capacidades',
  'assessment_question_es': 'Se ejecutan acciones para cerrar brechas de competencia y se evalúa su eficacia.',
  'suggested_evidence_es': 'Plan de formación, resultados, evaluaciones y mejoras.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-044',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.3',
  'domain_es': 'Conciencia',
  'assessment_question_es': 'El personal conoce la política, su contribución a la continuidad y las consecuencias de no cumplir los '
                            'procedimientos.',
  'suggested_evidence_es': 'Inducciones, campañas, encuestas y pruebas de conocimiento.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-045',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.3',
  'domain_es': 'Conciencia',
  'assessment_question_es': 'Las personas conocen su papel antes, durante y después de una interrupción.',
  'suggested_evidence_es': 'Tarjetas de rol, guías rápidas, simulacros y confirmaciones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-046',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.4',
  'domain_es': 'Comunicación',
  'assessment_question_es': 'Existe un plan que define qué, cuándo, con quién, cómo y quién comunica asuntos de continuidad.',
  'suggested_evidence_es': 'Plan de comunicación, matriz de contactos y vocerías.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-047',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.4',
  'domain_es': 'Comunicación',
  'assessment_question_es': 'Los canales de comunicación de crisis cuentan con alternativas y mecanismos de escalamiento.',
  'suggested_evidence_es': 'Árbol de llamadas, canales alternos, pruebas y protocolos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-048',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.4',
  'domain_es': 'Comunicación',
  'assessment_question_es': 'La comunicación con autoridades, medios, clientes, proveedores y otras partes relevantes está prevista.',
  'suggested_evidence_es': 'Plantillas, directorio, criterios de notificación y voceros.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-049',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.5',
  'domain_es': 'Información documentada',
  'assessment_question_es': 'Se determinan los documentos y registros necesarios para operar y demostrar la eficacia del sistema.',
  'suggested_evidence_es': 'Listado maestro, arquitectura documental y matriz de registros.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-050',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.5',
  'domain_es': 'Control documental',
  'assessment_question_es': 'Los documentos se identifican, revisan, aprueban, actualizan y distribuyen de forma controlada.',
  'suggested_evidence_es': 'Procedimiento documental, versiones, aprobaciones y permisos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-051',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.5',
  'domain_es': 'Protección documental',
  'assessment_question_es': 'La información de continuidad se protege, conserva, recupera y elimina de acuerdo con reglas definidas.',
  'suggested_evidence_es': 'Controles de acceso, respaldos, retención y eliminación segura.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-052',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.1',
  'domain_es': 'Planificación y control operacional',
  'assessment_question_es': 'Se planifican y controlan los procesos necesarios para cumplir requisitos y ejecutar las acciones del SGCN.',
  'suggested_evidence_es': 'Planes operativos, criterios de aceptación, controles y registros.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-053',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.1',
  'domain_es': 'Cambios operacionales',
  'assessment_question_es': 'Los cambios planificados se controlan y los cambios no previstos se revisan para reducir efectos adversos.',
  'suggested_evidence_es': 'Registros de cambio, evaluación de impacto y acciones de mitigación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-054',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.1',
  'domain_es': 'Procesos tercerizados',
  'assessment_question_es': 'Los procesos y servicios externos relevantes para continuidad están sujetos a controles definidos.',
  'suggested_evidence_es': 'Contratos, SLA, evaluaciones de proveedor, planes y pruebas conjuntas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-055',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.1',
  'domain_es': 'BIA y evaluación de riesgos',
  'assessment_question_es': 'Existe un proceso formal, vigente y consistente para el análisis de impacto y la evaluación de riesgos de '
                            'interrupción.',
  'suggested_evidence_es': 'Metodología aprobada, calendario, responsables y resultados.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-056',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.2',
  'domain_es': 'Análisis de impacto al negocio',
  'assessment_question_es': 'El BIA identifica actividades que soportan productos y servicios priorizados dentro del alcance.',
  'suggested_evidence_es': 'Inventario de productos, servicios, procesos y actividades priorizadas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-057',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.2',
  'domain_es': 'Impactos',
  'assessment_question_es': 'El BIA evalúa tipos de impacto y cómo aumentan con el tiempo después de una interrupción.',
  'suggested_evidence_es': 'Escalas de impacto, curvas temporales, criterios financieros, legales, operativos y reputacionales.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-058',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.2',
  'domain_es': 'Tiempos objetivo',
  'assessment_question_es': 'Se establecen y justifican los tiempos máximos tolerables, objetivos de recuperación y puntos objetivo de '
                            'recuperación cuando aplican.',
  'suggested_evidence_es': 'MTPD/MAO, RTO, RPO, criterios, aprobaciones y trazabilidad.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-059',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.2',
  'domain_es': 'Capacidad mínima',
  'assessment_question_es': 'Se define la capacidad mínima aceptable y el momento en que debe recuperarse cada actividad priorizada.',
  'suggested_evidence_es': 'Niveles mínimos de servicio, capacidad, volumen y cronograma de recuperación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-060',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.2',
  'domain_es': 'Recursos y dependencias',
  'assessment_question_es': 'El BIA identifica personas, tecnología, datos, instalaciones, proveedores y otras dependencias necesarias.',
  'suggested_evidence_es': 'Mapa de dependencias, recursos mínimos y puntos únicos de falla.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-061',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.2',
  'domain_es': 'Interdependencias',
  'assessment_question_es': 'Se analizan dependencias entre procesos y se define una secuencia viable de recuperación.',
  'suggested_evidence_es': 'Mapa de interdependencias, cadena de recuperación y validación de áreas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-062',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.2',
  'domain_es': 'Aprobación y actualización del BIA',
  'assessment_question_es': 'Los resultados del BIA son validados por dueños de negocio, aprobados y revisados ante cambios '
                            'significativos.',
  'suggested_evidence_es': 'Firmas, actas, versión vigente, disparadores y calendario de revisión.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-063',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.3',
  'domain_es': 'Riesgos de interrupción',
  'assessment_question_es': 'Se identifican amenazas, vulnerabilidades y escenarios que pueden interrumpir actividades priorizadas.',
  'suggested_evidence_es': 'Registro de escenarios, talleres, inteligencia de amenazas y análisis de vulnerabilidad.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-064',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.3',
  'domain_es': 'Análisis y evaluación',
  'assessment_question_es': 'Los riesgos de interrupción se analizan y evalúan con criterios consistentes y aprobados.',
  'suggested_evidence_es': 'Metodología, escalas, resultados, aceptación y priorización.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-065',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.3',
  'domain_es': 'Tratamiento y riesgo residual',
  'assessment_question_es': 'Se determinan controles, responsables, plazos y aceptación del riesgo residual.',
  'suggested_evidence_es': 'Plan de tratamiento, controles, aprobaciones y seguimiento.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-066',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.1',
  'domain_es': 'Estrategias y soluciones',
  'assessment_question_es': 'Las estrategias de continuidad se basan en los resultados del BIA y de la evaluación de riesgos.',
  'suggested_evidence_es': 'Trazabilidad BIA-riesgos-estrategias y criterios de decisión.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-067',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.2',
  'domain_es': 'Opciones de estrategia',
  'assessment_question_es': 'Se identifican opciones para antes, durante y después de una interrupción, incluyendo prevención, respuesta y '
                            'recuperación.',
  'suggested_evidence_es': 'Catálogo de opciones, escenarios, ventajas, limitaciones y costos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-068',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.3',
  'domain_es': 'Selección de soluciones',
  'assessment_question_es': 'Las soluciones se seleccionan considerando tiempos objetivo, capacidad, riesgos, costos, beneficios y '
                            'obligaciones.',
  'suggested_evidence_es': 'Análisis multicriterio, caso de negocio y aprobación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-069',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.3',
  'domain_es': 'Adecuación de soluciones',
  'assessment_question_es': 'Las soluciones seleccionadas son viables frente a escenarios severos pero plausibles.',
  'suggested_evidence_es': 'Pruebas de capacidad, análisis de estrés y supuestos documentados.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-070',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.4',
  'domain_es': 'Requisitos de recursos',
  'assessment_question_es': 'Se determinan los recursos necesarios para implementar las soluciones de continuidad.',
  'suggested_evidence_es': 'Requisitos de personal, instalaciones, TIC, datos, transporte, finanzas y proveedores.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-071',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.4',
  'domain_es': 'Proveedores y cadena de suministro',
  'assessment_question_es': 'Se establecen requisitos de continuidad para proveedores críticos y se verifica su capacidad.',
  'suggested_evidence_es': 'Cláusulas, cuestionarios, certificaciones, planes y resultados de pruebas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-072',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.5',
  'domain_es': 'Implementación de soluciones',
  'assessment_question_es': 'Las soluciones aprobadas se implementan, mantienen y controlan con responsables y recursos definidos.',
  'suggested_evidence_es': 'Plan de implementación, entregables, responsables y evidencia operativa.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-073',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.5',
  'domain_es': 'Capacidad técnica',
  'assessment_question_es': 'La infraestructura y los mecanismos de recuperación cumplen los objetivos establecidos.',
  'suggested_evidence_es': 'Pruebas técnicas, capacidad, replicación, respaldos y tiempos reales.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-074',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.1',
  'domain_es': 'Planes y procedimientos',
  'assessment_question_es': 'Los planes permiten gestionar una interrupción y continuar o recuperar actividades priorizadas.',
  'suggested_evidence_es': 'Planes vigentes, procedimientos, listas de verificación y anexos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-075',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.1',
  'domain_es': 'Características de los planes',
  'assessment_question_es': 'Los planes son específicos, flexibles, accesibles, comprensibles y utilizables bajo presión.',
  'suggested_evidence_es': 'Revisión de calidad, copias alternas, accesibilidad y pruebas de uso.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-076',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.2',
  'domain_es': 'Estructura de respuesta',
  'assessment_question_es': 'Existe una estructura de respuesta con niveles de autoridad, roles, suplencias y criterios de escalamiento.',
  'suggested_evidence_es': 'Organigrama de crisis, RACI, delegaciones y tarjetas de rol.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-077',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.2',
  'domain_es': 'Activación y desactivación',
  'assessment_question_es': 'Se definen criterios y responsables para activar, escalar, mantener y desactivar la respuesta.',
  'suggested_evidence_es': 'Matriz de activación, umbrales, autoridad y registro de decisiones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-078',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.2',
  'domain_es': 'Gestión estratégica, táctica y operativa',
  'assessment_question_es': 'La estructura coordina decisiones estratégicas, tácticas y operativas durante una interrupción.',
  'suggested_evidence_es': 'Protocolos de coordinación, salas de crisis y cadencia de reuniones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-079',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.3',
  'domain_es': 'Alerta y comunicación',
  'assessment_question_es': 'Se dispone de procedimientos para detectar, alertar, notificar y movilizar a los equipos relevantes.',
  'suggested_evidence_es': 'Monitoreo, alarmas, árbol de llamadas, pruebas y registros.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-080',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.3',
  'domain_es': 'Comunicación de crisis',
  'assessment_question_es': 'Los mensajes se preparan, autorizan, emiten y registran con control de consistencia y oportunidad.',
  'suggested_evidence_es': 'Plantillas, aprobaciones, registro de comunicaciones y monitoreo de medios.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-081',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.3',
  'domain_es': 'Interoperabilidad',
  'assessment_question_es': 'Los mecanismos de comunicación son compatibles con los de autoridades, respondedores y socios cuando aplica.',
  'suggested_evidence_es': 'Protocolos conjuntos, directorios, pruebas y acuerdos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-082',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.4',
  'domain_es': 'Contenido del plan',
  'assessment_question_es': 'Cada plan define propósito, alcance, objetivos, criterios de activación, roles, acciones y recursos.',
  'suggested_evidence_es': 'Plan aprobado y lista de contenidos mínimos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-083',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.4',
  'domain_es': 'Procedimientos de continuidad',
  'assessment_question_es': 'Los procedimientos detallan cómo operar a capacidad aceptable y cómo priorizar recursos durante la '
                            'interrupción.',
  'suggested_evidence_es': 'Procedimientos alternos, capacidad mínima y secuencia de actividades.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-084',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.4',
  'domain_es': 'Dependencias y terceros',
  'assessment_question_es': 'Los planes incorporan dependencias internas y externas, contactos y compromisos de terceros críticos.',
  'suggested_evidence_es': 'Anexos de dependencias, contactos, SLA y acuerdos de apoyo.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-085',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.4',
  'domain_es': 'Información vital',
  'assessment_question_es': 'La información esencial para ejecutar los planes está disponible, protegida y actualizada.',
  'suggested_evidence_es': 'Repositorios alternos, copias offline, control de acceso y versiones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-086',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.5',
  'domain_es': 'Recuperación y retorno',
  'assessment_question_es': 'Se planifica la transición desde la respuesta hasta la recuperación y el retorno controlado a la operación '
                            'normal.',
  'suggested_evidence_es': 'Plan de retorno, criterios de estabilidad, validaciones y aceptación del negocio.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-087',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.5',
  'domain_es': 'Restauración priorizada',
  'assessment_question_es': 'La recuperación respeta los tiempos, la secuencia y la capacidad definidos por el BIA.',
  'suggested_evidence_es': 'Cronograma de recuperación, resultados de pruebas y trazabilidad con RTO/RPO.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-088',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.5',
  'domain_es': 'Programa de ejercicios',
  'assessment_question_es': 'Existe un programa de ejercicios alineado con alcance, riesgos, capacidades y objetivos de continuidad.',
  'suggested_evidence_es': 'Programa anual/plurianual, cobertura y aprobación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-089',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.5',
  'domain_es': 'Tipos y escenarios',
  'assessment_question_es': 'Los ejercicios incluyen diferentes métodos y escenarios relevantes, progresivos y suficientemente exigentes.',
  'suggested_evidence_es': 'Ejercicios de escritorio, simulaciones, pruebas técnicas e integrales.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-090',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.5',
  'domain_es': 'Participación',
  'assessment_question_es': 'Participan las áreas, directivos, sedes y terceros necesarios para validar la capacidad de extremo a extremo.',
  'suggested_evidence_es': 'Listas de participantes, alcance, invitaciones y resultados.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-091',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.5',
  'domain_es': 'Criterios y seguridad',
  'assessment_question_es': 'Cada ejercicio define objetivos, criterios de éxito, controles de riesgo y reglas para evitar impactos no '
                            'deseados.',
  'suggested_evidence_es': 'Guion, plan de prueba, criterios, autorizaciones y plan de reversa.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-092',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.5',
  'domain_es': 'Resultados y mejoras',
  'assessment_question_es': 'Los ejercicios generan resultados documentados, lecciones, acciones, responsables y fechas de cierre.',
  'suggested_evidence_es': 'Informe de ejercicio, evidencias, plan de acción y seguimiento.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-093',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.5',
  'domain_es': 'Validación de capacidades',
  'assessment_question_es': 'Los resultados demuestran si las soluciones y planes alcanzan los tiempos y capacidades requeridos.',
  'suggested_evidence_es': 'Tiempos reales, volumen recuperado, desviaciones y aceptación del negocio.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-094',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.6',
  'domain_es': 'Evaluación documental y de capacidades',
  'assessment_question_es': 'Los planes, procedimientos y capacidades se revisan con una frecuencia definida y después de cambios o '
                            'incidentes.',
  'suggested_evidence_es': 'Calendario de revisión, disparadores, actas y versiones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-095',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.6',
  'domain_es': 'Conformidad y vigencia',
  'assessment_question_es': 'La evaluación confirma que los elementos de continuidad siguen siendo adecuados, suficientes y eficaces.',
  'suggested_evidence_es': 'Revisiones cruzadas, listas de verificación y aprobaciones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-096',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.6',
  'domain_es': 'Lecciones aprendidas',
  'assessment_question_es': 'Los resultados de incidentes, ejercicios y evaluaciones se incorporan a planes, estrategias y formación.',
  'suggested_evidence_es': 'Registro de lecciones, cambios implementados y validación posterior.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-097',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.1',
  'domain_es': 'Seguimiento y medición',
  'assessment_question_es': 'Se define qué medir, cómo medir, cuándo analizar y quién evalúa el desempeño del SGCN.',
  'suggested_evidence_es': 'Ficha de indicadores, fuentes, responsables y periodicidad.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-098',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.1',
  'domain_es': 'Indicadores',
  'assessment_question_es': 'Los indicadores cubren preparación, capacidad, ejercicios, incidentes, acciones y cumplimiento de objetivos.',
  'suggested_evidence_es': 'Tablero de indicadores, metas, tendencias y umbrales.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-099',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.1',
  'domain_es': 'Análisis y evaluación',
  'assessment_question_es': 'Los resultados se analizan para determinar eficacia, tendencias, desviaciones y necesidad de acciones.',
  'suggested_evidence_es': 'Informes de desempeño, análisis de causa y decisiones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-100',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.1',
  'domain_es': 'Evidencia de resultados',
  'assessment_question_es': 'Se conserva información documentada suficiente para demostrar los resultados del seguimiento y la evaluación.',
  'suggested_evidence_es': 'Registros, reportes, trazabilidad de datos y retención.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-101',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.2.1',
  'domain_es': 'Auditoría interna',
  'assessment_question_es': 'Se realizan auditorías internas planificadas para evaluar conformidad y eficacia del sistema.',
  'suggested_evidence_es': 'Programa, planes, listas de verificación, informes y evidencias.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-102',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.2.2',
  'domain_es': 'Programa de auditoría',
  'assessment_question_es': 'El programa considera importancia de procesos, cambios, riesgos y resultados de auditorías anteriores.',
  'suggested_evidence_es': 'Criterios de priorización, cobertura, frecuencia y cronograma.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-103',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.2.2',
  'domain_es': 'Independencia y competencia',
  'assessment_question_es': 'Los auditores son competentes y mantienen objetividad e imparcialidad frente al trabajo auditado.',
  'suggested_evidence_es': 'Competencias, asignaciones, declaración de independencia y revisión.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-104',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.2.2',
  'domain_es': 'Resultados de auditoría',
  'assessment_question_es': 'Los resultados se comunican a responsables pertinentes y se da seguimiento oportuno a las acciones.',
  'suggested_evidence_es': 'Informe, distribución, plan de acción y verificación de cierre.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-105',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.3',
  'domain_es': 'Revisión por la dirección',
  'assessment_question_es': 'La alta dirección revisa el SGCN a intervalos planificados.',
  'suggested_evidence_es': 'Calendario, convocatoria, actas y participantes.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-106',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.3.2',
  'domain_es': 'Entradas de revisión',
  'assessment_question_es': 'La revisión considera cambios, desempeño, auditorías, incidentes, ejercicios, riesgos, recursos y acciones '
                            'previas.',
  'suggested_evidence_es': 'Agenda, paquete de información y presentación ejecutiva.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-107',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.3.2',
  'domain_es': 'Necesidades y oportunidades',
  'assessment_question_es': 'La revisión analiza oportunidades de mejora y necesidades de cambio, recursos o actualización del sistema.',
  'suggested_evidence_es': 'Análisis de brechas, propuestas, decisiones y priorización.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-108',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.3.3',
  'domain_es': 'Salidas de revisión',
  'assessment_question_es': 'Las decisiones y acciones de la revisión quedan documentadas con responsables y plazos.',
  'suggested_evidence_es': 'Acta, decisiones, plan de acción y seguimiento.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-109',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '10',
  'clause': '10.1',
  'domain_es': 'No conformidad',
  'assessment_question_es': 'Las no conformidades e incidentes originan acciones para controlar, corregir y atender sus consecuencias.',
  'suggested_evidence_es': 'Registro de no conformidad, contención, corrección y evidencias.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-110',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '10',
  'clause': '10.1',
  'domain_es': 'Causa y recurrencia',
  'assessment_question_es': 'Se analizan causas y se determina si pueden existir problemas similares en otros procesos o ubicaciones.',
  'suggested_evidence_es': 'Análisis de causa raíz, revisión transversal y acciones sistémicas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-111',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '10',
  'clause': '10.1',
  'domain_es': 'Acción correctiva',
  'assessment_question_es': 'Las acciones correctivas son proporcionales al efecto de la no conformidad y se implementan oportunamente.',
  'suggested_evidence_es': 'Plan de acción, priorización, responsables y plazos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-112',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '10',
  'clause': '10.1',
  'domain_es': 'Eficacia y actualización',
  'assessment_question_es': 'Se revisa la eficacia de las acciones y se actualizan riesgos, controles o el sistema cuando corresponde.',
  'suggested_evidence_es': 'Verificación de eficacia, cambios, cierre y aprobación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-113',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '10',
  'clause': '10.2',
  'domain_es': 'Mejora continua',
  'assessment_question_es': 'La organización mejora continuamente la adecuación, suficiencia y eficacia del sistema de continuidad.',
  'suggested_evidence_es': 'Portafolio de mejoras, indicadores, lecciones y beneficios realizados.',
  'default_weight': 1,
  'active': True}]

ISO22301_MADUREZ_LEVELS = [
    {
        "nivel": "Nivel 1: Inicial",
        "descripcion": "No existe implementación formal o es mínima; las prácticas son ad hoc.",
        "score": 1,
        "rango_pct": "0% – 20%",
        "logica": "Prácticas no formalizadas"
    },
    {
        "nivel": "Nivel 2: Repetible",
        "descripcion": "Existen prácticas parciales y repetibles, pero con documentación o control limitado.",
        "score": 2,
        "rango_pct": "21% – 40%",
        "logica": "Prácticas parciales"
    },
    {
        "nivel": "Nivel 3: Definido",
        "descripcion": "El proceso está definido, documentado y comunicado para su ejecución consistente.",
        "score": 3,
        "rango_pct": "41% – 60%",
        "logica": "Proceso documentado"
    },
    {
        "nivel": "Nivel 4: Gestionado",
        "descripcion": "El proceso se mide, gestiona, controla y tiene seguimiento periódico.",
        "score": 4,
        "rango_pct": "61% – 80%",
        "logica": "Proceso medido y gestionado"
    },
    {
        "nivel": "Nivel 5: Optimizado",
        "descripcion": "El proceso es eficaz, sostenido y mejorado continuamente con evidencia trazable.",
        "score": 5,
        "rango_pct": "81% – 100%",
        "logica": "Mejora continua"
    },
]


# ============================================================
# MODELOS DB — ISO 22301
# ============================================================
class Iso22301MadurezParametro(db.Model):
    __bind_key__ = "iso22301_madurez"
    __tablename__ = "iso22301_madurez_parametros"

    id = db.Column(db.Integer, primary_key=True)
    nivel = db.Column(db.String(80), nullable=False)
    rango_desde = db.Column(db.Float, nullable=False)
    rango_hasta = db.Column(db.Float, nullable=False)
    color = db.Column(db.String(20), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    orden = db.Column(db.Integer, default=0)


class Iso22301MadurezPregunta(db.Model):
    __bind_key__ = "iso22301_madurez"
    __tablename__ = "iso22301_madurez_preguntas"

    id = db.Column(db.Integer, primary_key=True)
    bloque_codigo = db.Column(db.String(50), index=True, nullable=True)
    bloque_nombre = db.Column(db.String(255), nullable=True)
    seccion_codigo = db.Column(db.String(50), index=True, nullable=True)
    seccion_nombre = db.Column(db.Text, nullable=True)
    pregunta_codigo = db.Column(db.String(50), index=True, nullable=True)
    pregunta = db.Column(db.Text, nullable=False)
    evidencia_sugerida = db.Column(db.Text, nullable=True)
    tipo = db.Column(db.String(5), nullable=False, default="q")  # h / q
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)


class Iso22301MadurezRun(db.Model):
    __bind_key__ = "iso22301_madurez"
    __tablename__ = "iso22301_madurez_runs"

    id = db.Column(db.Integer, primary_key=True)
    consecutivo = db.Column(db.String(255), nullable=False, index=True)
    company_name = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, nullable=True)  # DB independiente: no FK cruzada
    estado = db.Column(db.String(20), nullable=False, default="BORRADOR", index=True)
    progreso_pct = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    resumen_json = db.Column(db.Text, nullable=False, default="{}")
    pct_general = db.Column(db.Float, nullable=False, default=0.0)
    radar_overall_b64 = db.Column(db.Text, nullable=True)

    informe_ejecutivo_ai = db.Column(db.Text, nullable=True)
    informe_ejecutivo_editado = db.Column(db.Text, nullable=True)
    plan_trabajo_ai = db.Column(db.Text, nullable=True)
    plan_trabajo_editado = db.Column(db.Text, nullable=True)


class Iso22301MadurezRespuesta(db.Model):
    __bind_key__ = "iso22301_madurez"
    __tablename__ = "iso22301_madurez_respuestas"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("iso22301_madurez_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    pregunta_id = db.Column(db.Integer, db.ForeignKey("iso22301_madurez_preguntas.id", ondelete="CASCADE"), nullable=False, index=True)
    estado = db.Column(db.String(20), nullable=False)  # SI / PARCIAL / NO / NA
    comentario = db.Column(db.Text, nullable=True)


class Iso22301MadurezCriterioAnalisis(db.Model):
    __bind_key__ = "iso22301_madurez"
    __tablename__ = "iso22301_madurez_criterio_analisis"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("iso22301_madurez_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    bloque_codigo = db.Column(db.String(50), nullable=False, index=True)
    bloque_nombre = db.Column(db.String(255), nullable=True)
    estado_actual = db.Column(db.Text, nullable=True)
    estado_requerido = db.Column(db.Text, nullable=True)
    plan_accion_ai = db.Column(db.Text, nullable=True)
    plan_accion_editado = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("run_id", "bloque_codigo", name="uq_iso22301_run_bloque"),
    )


# ============================================================
# INICIALIZACIÓN DB INDEPENDIENTE
# ============================================================
def _iso22301_ensure_schema():
    """Aplica migraciones idempotentes únicamente sobre la base ISO 22301."""
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(ISO22301_DB_PATH)
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(iso22301_madurez_preguntas)").fetchall()}
        if cols and "evidencia_sugerida" not in cols:
            conn.execute("ALTER TABLE iso22301_madurez_preguntas ADD COLUMN evidencia_sugerida TEXT")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()
    finally:
        conn.close()


def init_iso22301_madurez_db():
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        app.config.setdefault("SQLALCHEMY_BINDS", {})
        app.config["SQLALCHEMY_BINDS"]["iso22301_madurez"] = "sqlite:///" + ISO22301_DB_PATH
        with app.app_context():
            db.create_all(bind_key="iso22301_madurez")
            _iso22301_ensure_schema()
            seed_iso22301_parametros()
            if Iso22301MadurezPregunta.query.filter_by(tipo="q").count() == 0:
                iso22301_seed_catalog(ISO22301_EMBEDDED_CATALOG, replace=False)
        print(f"✅ Base de datos ISO 22301 inicializada correctamente: {ISO22301_DB_PATH}")
    except Exception as e:
        print(f"❌ Error inicializando base de datos ISO 22301: {repr(e)}")
        raise


# ============================================================
# HELPERS GENERALES
# ============================================================
def iso22301_block_title(code: str) -> str:
    return ISO22301_BLOCK_TITLES.get((code or "").strip().upper(), code or "")


def iso22301_safe_str(x):
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()


def _iso22301_norm(s: str) -> str:
    s = iso22301_safe_str(s)
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.upper()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def iso22301_normalizar_texto_excel(texto: str) -> str:
    t = iso22301_safe_str(texto)
    if not t:
        return ""
    t = t.replace("\ufeff", " ").replace("\xa0", " ")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t).strip()
    return t


def iso22301_detectar_bloque(texto: str):
    n = _iso22301_norm(texto)
    match = re.search(r"(?:CAPITULO|CAPÍTULO|CLAUSULA|CLÁUSULA)?\s*(10|[4-9])(?:\.0)?$", n)
    if match:
        code = match.group(1)
        return code, ISO22301_BLOCK_TITLES.get(code, code)
    return None, None


def seed_iso22301_parametros():
    if Iso22301MadurezParametro.query.first():
        return
    params = [
        {"nivel": "Nivel 1: Inicial", "rango_desde": 0, "rango_hasta": 20.99, "color": "#dc3545", "descripcion": "No existe implementación formal o es mínima.", "orden": 1},
        {"nivel": "Nivel 2: Repetible", "rango_desde": 21, "rango_hasta": 40.99, "color": "#fd7e14", "descripcion": "Existen prácticas parciales y repetibles.", "orden": 2},
        {"nivel": "Nivel 3: Definido", "rango_desde": 41, "rango_hasta": 60.99, "color": "#ffc107", "descripcion": "El proceso está definido y documentado.", "orden": 3},
        {"nivel": "Nivel 4: Gestionado", "rango_desde": 61, "rango_hasta": 80.99, "color": "#0d6efd", "descripcion": "El proceso se mide, gestiona y controla.", "orden": 4},
        {"nivel": "Nivel 5: Optimizado", "rango_desde": 81, "rango_hasta": 100, "color": "#198754", "descripcion": "Proceso eficaz, sostenido y mejorado continuamente.", "orden": 5},
    ]
    for p in params:
        db.session.add(Iso22301MadurezParametro(**p))
    db.session.commit()


def iso22301_resolver_nivel(pct: float):
    try:
        pct = float(pct or 0)
    except Exception:
        pct = 0.0
    pct = max(0.0, min(100.0, pct))
    rows = Iso22301MadurezParametro.query.order_by(Iso22301MadurezParametro.orden.asc()).all()
    for r in rows:
        if float(r.rango_desde) <= pct <= float(r.rango_hasta):
            return {"nivel": r.nivel, "score": r.orden, "color": r.color or "#6c757d", "descripcion": r.descripcion or ""}
    return {"nivel": "Nivel no definido", "score": 0, "color": "#6c757d", "descripcion": ""}


def iso22301_resumen_instrumento():
    total_q = Iso22301MadurezPregunta.query.filter_by(tipo="q").count()
    total_h = Iso22301MadurezPregunta.query.filter_by(tipo="h").count()
    por_bloque = (
        db.session.query(Iso22301MadurezPregunta.bloque_codigo, func.count(Iso22301MadurezPregunta.id))
        .filter(Iso22301MadurezPregunta.tipo == "q")
        .group_by(Iso22301MadurezPregunta.bloque_codigo)
        .all()
    )
    return {"total_preguntas": total_q, "total_headers": total_h, "por_bloque": {k: v for k, v in por_bloque}}


def cargar_respuestas_iso22301(run_id):
    out = {}
    if not run_id:
        return out
    rows = Iso22301MadurezRespuesta.query.filter_by(run_id=run_id).all()
    for r in rows:
        out[r.pregunta_id] = {"estado": (r.estado or "").strip().upper(), "comentario": (r.comentario or "").strip()}
    return out


def calcular_progreso_iso22301(preguntas, form_data=None, respuestas_db=None):
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


def obtener_borrador_iso22301(user_id):
    if not user_id:
        return None
    return (
        Iso22301MadurezRun.query
        .filter(Iso22301MadurezRun.user_id == user_id, Iso22301MadurezRun.estado == "BORRADOR")
        .order_by(Iso22301MadurezRun.updated_at.desc(), Iso22301MadurezRun.id.desc())
        .first()
    )


def _contar_respuestas_run_iso22301(run_id: int) -> int:
    if not run_id:
        return 0
    return Iso22301MadurezRespuesta.query.filter_by(run_id=run_id).count()


def _eliminar_runs_vacios_iso22301(user_id: int | None = None):
    q = Iso22301MadurezRun.query
    if user_id:
        q = q.filter(Iso22301MadurezRun.user_id == user_id)
    eliminados = 0
    for run in q.all():
        if Iso22301MadurezRespuesta.query.filter_by(run_id=run.id).count() == 0:
            Iso22301MadurezCriterioAnalisis.query.filter_by(run_id=run.id).delete(synchronize_session=False)
            db.session.delete(run)
            eliminados += 1
    if eliminados:
        db.session.commit()
    return eliminados


def iso22301_pct_from_estados(estados: list[str]) -> float:
    vals = []
    for e in estados:
        estado = (e or "").strip().upper()

        # N/A tiene valor 0, pero no es una pregunta aplicable y por eso
        # no suma ni aumenta el denominador del promedio.
        if estado == "NA":
            continue

        v = ISO22301_STATUS_SCORE.get(estado)
        if v is not None:
            vals.append(v)

    return round(sum(vals) / len(vals), 2) if vals else 0.0


def _parse_rango_pct_iso22301(rango: str):
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


def iso22301_nivel_visual_por_pct(pct: float):
    return iso22301_resolver_nivel(pct)


def _iso22301_group_questions():
    preguntas = (
        Iso22301MadurezPregunta.query
        .filter_by(activo=True, tipo="q")
        .order_by(Iso22301MadurezPregunta.bloque_codigo.asc(), Iso22301MadurezPregunta.orden.asc(), Iso22301MadurezPregunta.id.asc())
        .all()
    )
    grouped = {}
    for q in preguntas:
        bloque = (q.bloque_codigo or "SIN_BLOQUE").strip().upper()
        if bloque not in grouped:
            grouped[bloque] = {
                "titulo": q.bloque_nombre or iso22301_block_title(bloque) or bloque,
                "items": []
            }
        grouped[bloque]["items"].append(q)
    ordered = {}
    for code in ISO22301_BLOCK_ORDER:
        if code in grouped:
            ordered[code] = grouped[code]
    for code, val in grouped.items():
        if code not in ordered:
            ordered[code] = val
    return ordered


def _iso22301_build_resumen(run_id: int) -> dict:
    q = (
        db.session.query(Iso22301MadurezRespuesta, Iso22301MadurezPregunta)
        .join(Iso22301MadurezPregunta, Iso22301MadurezPregunta.id == Iso22301MadurezRespuesta.pregunta_id)
        .filter(Iso22301MadurezRespuesta.run_id == run_id)
        .filter(Iso22301MadurezPregunta.tipo == "q")
        .order_by(Iso22301MadurezPregunta.bloque_codigo.asc(), Iso22301MadurezPregunta.orden.asc())
    )
    por_bloque = {}
    for r, p in q.all():
        b = (p.bloque_codigo or "SIN_BLOQUE").strip().upper()
        por_bloque.setdefault(b, {
            "bloque": b,
            "nombre": p.bloque_nombre or iso22301_block_title(b) or b,
            "total": 0,
            "validas": 0,
            "SI": 0,
            "PARCIAL": 0,
            "NO": 0,
            "NA": 0,
            "items": [],
        })
        estado = (r.estado or "").strip().upper()
        por_bloque[b]["total"] += 1
        if estado in ("SI", "PARCIAL", "NO", "NA"):
            por_bloque[b][estado] += 1
        # Solo Sí, Parcial y No forman el denominador. N/A queda registrado
        # en el detalle, pero no participa en el nivel de madurez.
        if estado in ("SI", "PARCIAL", "NO"):
            por_bloque[b]["validas"] += 1
        por_bloque[b]["items"].append({
            "pregunta_id": p.id,
            "pregunta_codigo": p.pregunta_codigo,
            "pregunta": p.pregunta,
            "evidencia_sugerida": p.evidencia_sugerida or "",
            "estado": estado,
            "comentario": r.comentario or "",
        })

    resumen = {}
    for b, d in por_bloque.items():
        estados = [it["estado"] for it in d["items"]]
        pct = iso22301_pct_from_estados(estados)
        nivel = (
            iso22301_resolver_nivel(pct)
            if int(d.get("validas", 0) or 0) > 0
            else {
                "nivel": "No aplica",
                "score": 0,
                "color": "#6c757d",
                "descripcion": "Todas las preguntas del capítulo fueron marcadas N/A.",
            }
        )
        d["pct"] = pct
        d["madurez"] = nivel["nivel"]
        d["score"] = nivel.get("score", 0)
        d["color"] = nivel["color"]
        d["descripcion"] = nivel.get("descripcion", "")
        d["brecha_pct"] = round(100.0 - pct, 2) if d["validas"] > 0 else 0.0
        resumen[b] = d
    return resumen


def iso22301_pct_general_from_resumen(resumen: dict) -> float:
    """Calcula el resultado global solo con preguntas distintas de N/A."""
    estados = [
        item.get("estado", "")
        for bloque in (resumen or {}).values()
        for item in (bloque.get("items", []) or [])
    ]
    return iso22301_pct_from_estados(estados)


def iso22301_pct_por_criterio(resumen: dict, order: list[str] = None):
    order = order or ISO22301_BLOCK_ORDER
    labels, values = [], []
    for b in order:
        if b in (resumen or {}):
            d = (resumen or {}).get(b, {}) or {}
            if int(d.get("validas", 0) or 0) <= 0:
                continue
            labels.append(iso22301_block_title(b) or b)
            values.append(float(d.get("pct", 0) or 0))
    for b, d in (resumen or {}).items():
        if b not in order:
            if int(d.get("validas", 0) or 0) <= 0:
                continue
            labels.append(d.get("nombre") or b)
            values.append(float(d.get("pct", 0) or 0))
    return labels, values


def iso22301_radar_b64(labels: list[str], values: list[float], title: str = "Radar ISO 22301"):
    if not labels:
        return ""
    vals = [max(0.0, min(100.0, float(v))) for v in values]
    N = len(labels)
    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]
    plot_vals = vals + vals[:1]

    fig = plt.figure(figsize=(3.55, 3.55), dpi=170)
    ax = plt.subplot(111, polar=True)
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=7.3)
    ax.tick_params(axis="x", pad=10)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7)
    ax.tick_params(axis="y", pad=4)
    ax.plot(angles, plot_vals, linewidth=2.0)
    ax.fill(angles, plot_vals, alpha=0.16)
    ax.set_title(title, fontsize=9.5, pad=14)
    fig.subplots_adjust(top=0.83, bottom=0.10, left=0.10, right=0.90)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0.22)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generar_iso22301_velocimetro_png_bytes(titulo, valor, nivel="", color="#6c757d"):
    try:
        valor = max(0, min(100, float(valor or 0)))
        fig = plt.figure(figsize=(7.2, 4.2), dpi=220)
        ax = plt.axes([0.04, 0.08, 0.92, 0.84])
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_xlim(-1.18, 1.18)
        ax.set_ylim(-0.28, 1.18)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        rangos = [(180, 144, "#d9534f"), (144, 108, "#f0ad4e"), (108, 72, "#f7d154"), (72, 36, "#5bc0de"), (36, 0, "#5cb85c")]
        for theta1, theta2, c in rangos:
            ax.add_patch(Wedge((0, 0), 1.00, theta2, theta1, width=0.18, facecolor=c, edgecolor="white", linewidth=2))
        for pct in range(0, 101, 10):
            ang = math.radians(180 - (pct / 100.0) * 180.0)
            ax.plot([math.cos(ang) * 0.78, math.cos(ang) * 0.88], [math.sin(ang) * 0.78, math.sin(ang) * 0.88], linewidth=1.2, color="#4b5563")
        for pct in [0, 25, 50, 75, 100]:
            ang = math.radians(180 - (pct / 100.0) * 180.0)
            ax.text(math.cos(ang) * 0.63, math.sin(ang) * 0.63, f"{pct}", ha="center", va="center", fontsize=10, fontweight="bold", color="#374151")
        ang = math.radians(180 - (valor / 100.0) * 180.0)
        ax.add_patch(FancyArrowPatch((0, 0), (math.cos(ang) * 0.72, math.sin(ang) * 0.72), arrowstyle="-|>", mutation_scale=18, linewidth=2.4, color="#0b1220", zorder=5))
        ax.add_patch(Circle((0, 0), radius=0.065, facecolor="#0b1220", edgecolor="white", linewidth=1.0, zorder=6))
        titulo_corto = (titulo or "").strip()
        if len(titulo_corto) > 42:
            titulo_corto = titulo_corto[:39] + "..."
        ax.text(0, 1.06, titulo_corto, ha="center", va="center", fontsize=13, fontweight="bold", color="#0f3d68")
        ax.text(0, 0.30, f"{valor:.1f}%", ha="center", va="center", fontsize=24, fontweight="bold", color=color)
        if nivel:
            ax.text(0, 0.12, str(nivel)[:30], ha="center", va="center", fontsize=11, fontweight="bold", color="#374151")
        buf = io.BytesIO()
        canvas = FigureCanvas(fig)
        canvas.print_png(buf)
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        plt.close("all")
        return None


def generar_iso22301_velocimetro_base64(label: str, pct: float, nivel: str, color: str):
    b = generar_iso22301_velocimetro_png_bytes(label, pct, nivel, color)
    if not b:
        return None
    return base64.b64encode(b).decode("utf-8")


def iso22301_normalizar_texto_rico_guardado(texto: str) -> str:
    txt = (texto or "").strip()

    if not txt:
        return ""

    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = html.unescape(txt)
    txt = txt.replace("```json", "").replace("```", "").strip()

    # Extrae JSON aunque venga como:
    # { "informe_ejecutivo": "texto..." }
    # { "plan_trabajo": "texto..." }
    # { "texto": "texto..." }
    obj = None

    try:
        obj = json.loads(txt)
    except Exception:
        try:
            start = txt.find("{")
            end = txt.rfind("}")
            if start != -1 and end != -1 and end > start:
                obj = json.loads(txt[start:end + 1])
        except Exception:
            obj = None

    if isinstance(obj, dict):
        val = (
            obj.get("informe_ejecutivo")
            or obj.get("informe")
            or obj.get("resumen_ejecutivo")
            or obj.get("plan_trabajo")
            or obj.get("plan_accion")
            or obj.get("texto")
            or ""
        )

        if isinstance(val, list):
            val = _build_plan_accion_iso22301_texto(val)

        if isinstance(val, dict):
            val = json.dumps(val, ensure_ascii=False, indent=2)

        if isinstance(val, str) and val.strip():
            txt = val.strip()

    txt = html.unescape(txt)

    # Si aún quedaron llaves al inicio y contiene informe_ejecutivo,
    # intenta extraer por regex como último recurso.
    m = re.search(
        r'"informe_ejecutivo"\s*:\s*"(?P<txt>.*)"\s*\}?\s*$',
        txt,
        flags=re.IGNORECASE | re.DOTALL
    )

    if m:
        extraido = m.group("txt")

        try:
            # Solo interpreta secuencias JSON reales (\n, \u00f3, etc.)
            extraido = json.loads(f'"{extraido}"')
        except Exception:
            pass

        txt = extraido.strip()

    txt = re.sub(r"<\s*br\s*/?\s*>", "\n", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", "", txt)

    patrones = [
        r"^\s*\{\s*",
        r"^\s*\"informe_ejecutivo\"\s*:\s*\"?",
        r"^\s*\"resumen_ejecutivo\"\s*:\s*\"?",
        r"^\s*\*{0,3}\s*INFORME\s+EJECUTIVO\s*(DE\s+MADUREZ\s+ISO\s*22301)?\s*\*{0,3}\s*[:\-–—]?\s*",
        r"^\s*#{1,6}\s*INFORME\s+EJECUTIVO\s*(DE\s+MADUREZ\s+ISO\s*22301)?\s*[:\-–—]?\s*",
        r"^\s*RESUMEN\s+EJECUTIVO\s*[:\-–—]?\s*",
        r"^\s*PLAN\s+DE\s+TRABAJO\s*[:\-–—]?\s*",
    ]

    for p in patrones:
        txt = re.sub(p, "", txt, flags=re.IGNORECASE).strip()

    txt = re.sub(r'"\s*\}\s*$', "", txt).strip()
    txt = txt.replace("\\n", "\n")
    txt = txt.replace('\\"', '"')
    txt = txt.replace("**", "").replace("__", "")

    txt = re.sub(r"[ \t]+\n", "\n", txt)
    txt = re.sub(r"\n[ \t]+", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)

    return txt.strip()


def _extraer_json_objeto_iso22301(raw: str) -> dict:
    raw = (raw or "").strip().replace("```json", "").replace("```", "").strip()
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
            return json.loads(raw[start:end + 1])
    except Exception:
        pass
    return {}


def _iso22301_texto_informe_desde_valor(valor) -> str:
    """Obtiene texto útil desde respuestas de IA con estructuras variables."""
    if valor is None:
        return ""

    if isinstance(valor, str):
        return iso22301_normalizar_texto_rico_guardado(valor)

    if isinstance(valor, list):
        partes = []
        for item in valor:
            texto_item = _iso22301_texto_informe_desde_valor(item)
            if texto_item:
                partes.append(texto_item)
        return "\n\n".join(partes).strip()

    if not isinstance(valor, dict):
        return ""

    aliases = (
        "informe_ejecutivo",
        "informe_ejecutivo_iso_22301",
        "informe",
        "resumen_ejecutivo",
        "executive_summary",
        "executive_report",
        "report",
        "summary",
        "texto",
        "contenido",
        "content",
        "respuesta",
        "response",
        "resultado",
        "result",
        "output",
        "answer",
    )

    claves_normalizadas = {}
    for clave in valor.keys():
        clave_txt = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(clave))
        clave_norm = re.sub(r"[^a-z0-9]+", "_", clave_txt.lower()).strip("_")
        claves_normalizadas[clave_norm] = clave

    # Primero busca los nombres de campo conocidos, incluidos formatos
    # alternativos frecuentes de OpenRouter y Ollama.
    for alias in aliases:
        clave_real = claves_normalizadas.get(alias)
        if clave_real is None:
            continue
        texto = _iso22301_texto_informe_desde_valor(valor.get(clave_real))
        if texto:
            return texto

    # Si el proveedor anidó el contenido bajo otra clave, conserva el texto
    # más completo en lugar de descartar toda la respuesta.
    candidatos = []
    for contenido in valor.values():
        texto = _iso22301_texto_informe_desde_valor(contenido)
        if texto:
            candidatos.append(texto)

    return max(candidatos, key=len) if candidatos else ""


def _iso22301_extraer_informe_ai(raw) -> str:
    """Acepta JSON, JSON anidado, bloques Markdown o texto plano de la IA."""
    if raw is None:
        return ""

    if isinstance(raw, (dict, list)):
        return _iso22301_texto_informe_desde_valor(raw)

    raw_txt = str(raw).strip()
    if not raw_txt:
        return ""

    limpio = raw_txt.replace("```json", "").replace("```", "").strip()
    obj = None
    try:
        obj = json.loads(limpio)
    except Exception:
        try:
            inicio = limpio.find("{")
            fin = limpio.rfind("}")
            if inicio != -1 and fin != -1 and fin > inicio:
                obj = json.loads(limpio[inicio:fin + 1])
        except Exception:
            obj = None

    # Si el JSON sí fue válido, una estructura vacía o sin contenido debe
    # provocar el reintento; no debe guardarse como si fuera un informe.
    if obj is not None:
        return _iso22301_texto_informe_desde_valor(obj)

    # Fallback para texto plano o JSON incompleto por límite de tokens.
    texto = iso22301_normalizar_texto_rico_guardado(raw_txt)
    if texto.strip() in ("", "{}", "[]"):
        return ""
    return texto.strip()


def _build_plan_accion_iso22301_texto(plan_list) -> str:
    if not isinstance(plan_list, list):
        return ""
    lines = []
    for i, it in enumerate(plan_list, start=1):
        accion = (it.get("accion") or it.get("actividad") or "").strip()
        prioridad = (it.get("prioridad") or "").strip()
        responsable = (it.get("responsable_sugerido") or "").strip()
        plazo = (it.get("plazo") or "").strip()
        evidencia = (it.get("evidencia_esperada") or it.get("entregable") or "").strip()
        lines.append(
            f"{i}. Acción: {accion or 'Sin definir'}\n"
            f"   Prioridad: {prioridad or 'Sin definir'}\n"
            f"   Responsable sugerido: {responsable or 'Sin definir'}\n"
            f"   Plazo: {plazo or 'Sin definir'}\n"
            f"   Evidencia esperada: {evidencia or 'Sin definir'}"
        )
    return "\n\n".join(lines).strip()


def _normalizar_plan_accion_iso22301_texto(texto_raw: str) -> str:
    txt = (texto_raw or "").strip().replace("```json", "").replace("```", "").strip()
    if not txt:
        return ""
    obj = _extraer_json_objeto_iso22301(txt)
    if isinstance(obj, dict):
        for key in ("plan_accion", "plan_trabajo", "plan", "acciones"):
            if isinstance(obj.get(key), list):
                return _build_plan_accion_iso22301_texto(obj.get(key))
    return iso22301_normalizar_texto_rico_guardado(txt)

# ============================================================
# ISO 22301 — PROMPT PLAN DE TRABAJO IA
# ============================================================

def _iso22301_prompt_plan_trabajo(run: "Iso22301MadurezRun", resumen: dict) -> str:
    """
    Prompt para generar plan de trabajo ISO 22301.
    Lo usa plan_trabajo_generar().
    """

    lineas = []

    for code in ISO22301_BLOCK_ORDER:
        d = (resumen or {}).get(code)
        if not d or int(d.get("validas", 0) or 0) <= 0:
            continue

        lineas.append(
            f"- {d.get('nombre') or iso22301_block_title(code) or code}: "
            f"{float(d.get('pct', 0) or 0):.2f}% | "
            f"Nivel: {d.get('madurez') or ''} | "
            f"Brecha: {float(d.get('brecha_pct', 0) or 0):.2f}% | "
            f"NO: {d.get('NO', 0)} | "
            f"Parcial: {d.get('PARCIAL', 0)}"
        )

    criterios_txt = "\n".join(lineas) if lineas else "Sin resultados consolidados."

    return f"""
Eres un consultor senior experto en ISO 22301 y preparación para auditoría.

Genera un plan de trabajo priorizado para cerrar brechas ISO 22301.

DATOS
Consecutivo: {run.consecutivo}
Cumplimiento general: {float(run.pct_general or 0):.2f}%

RESULTADOS POR CRITERIO
{criterios_txt}

RESPONDE ÚNICAMENTE JSON VÁLIDO.
No uses markdown.
No agregues texto antes ni después del JSON.

Formato exacto:
{{
  "plan_trabajo": [
    {{
      "accion": "texto",
      "prioridad": "Alta|Media|Baja",
      "responsable_sugerido": "texto",
      "plazo": "texto",
      "evidencia_esperada": "texto"
    }}
  ]
}}

REGLAS:
- Genera entre 8 y 12 acciones.
- Prioriza criterios con menor cumplimiento.
- Las acciones deben ser auditables y verificables.
- La evidencia esperada debe ser concreta.
- No inventes herramientas específicas.
""".strip()

# ============================================================
# IA — ISO 22301
# ============================================================
def _iso22301_ai_text(prompt: str, max_tokens: int = 900) -> str:
    """
    IA exclusiva para ISO 22301.
    Corrige timeout de Ollama:
    - Reduce num_predict
    - Aumenta timeout
    - No usa stream
    - Mantiene OpenRouter si está configurado como proveedor
    """

    provider = (get_ai_provider() or "openrouter").strip().lower()

    # =========================
    # OLLAMA
    # =========================
    if provider == "ollama":
        base_url = (get_ollama_base_url() or "http://localhost:11434").strip().rstrip("/")
        model = (get_ollama_model() or "llama3.1").strip()

        if not base_url:
            raise RuntimeError("No hay OLLAMA_BASE_URL configurada.")
        if not model:
            raise RuntimeError("No hay OLLAMA_MODEL configurado.")

        try:
            resp = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.15,
                        "num_predict": int(max_tokens or 700),
                        "top_p": 0.9
                    }
                },
                timeout=600
            )

            resp.raise_for_status()
            data = resp.json() or {}
            texto = (data.get("response") or "").strip()

            if not texto:
                raise RuntimeError("Ollama respondió sin contenido.")

            return texto

        except requests.exceptions.ReadTimeout:
            raise RuntimeError(
                "Ollama tardó demasiado en responder. "
                "Se recomienda reducir el número de preguntas enviadas o usar OpenRouter para este análisis."
            )

        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "No fue posible conectar con Ollama. "
                "Verifica que Ollama esté activo en http://localhost:11434."
            )

    # =========================
    # OPENROUTER
    # =========================
    if "_ai_text" in globals():
        return _ai_text(prompt, max_tokens=max_tokens)

    raise RuntimeError("No se encontró helper global _ai_text para OpenRouter/Ollama.")


def _iso22301_ai_prompt_criterio(
    run: "Iso22301MadurezRun",
    bloque_codigo: str,
    bloque_nombre: str,
    pct: float,
    items: list[dict]
):
    """
    Prompt ISO 22301 mejorado:
    - Evita respuestas demasiado cortas.
    - Mantiene límite para no generar timeout en Ollama.
    - Obliga estado actual y requerido con análisis real.
    """

    bullets = []

    applicable_items = [
        it for it in (items or [])
        if (it.get("estado") or "").strip().upper() != "NA"
    ]

    for it in applicable_items[:30]:
        pregunta = (it.get("pregunta") or "")[:260].replace("\n", " ")
        comentario = (it.get("comentario") or "")[:260].replace("\n", " ")
        estado = (it.get("estado") or "").strip().upper()

        linea = f"- [{estado}] {pregunta}"
        if comentario:
            linea += f" | Evidencia/Comentario: {comentario}"

        bullets.append(linea)

    joined = "\n".join(bullets) if bullets else "- Sin evidencias registradas."

    return f"""
Eres un consultor senior experto en ISO 22301, Trust Services Criteria, auditoría de controles, seguridad de la información y gobierno de riesgos.

Debes generar un análisis ejecutivo, claro y accionable para el criterio evaluado.

CONTEXTO DE LA EVALUACIÓN
Consecutivo: {run.consecutivo}
Criterio ISO 22301: {bloque_codigo} - {bloque_nombre}
Cumplimiento actual: {pct:.2f}%

EVIDENCIAS Y RESPUESTAS DEL CRITERIO
{joined}

INSTRUCCIONES OBLIGATORIAS
Responde únicamente JSON válido.
No uses markdown.
No agregues texto antes ni después del JSON.

Debes devolver exactamente estas llaves:
{{
  "estado_actual": "texto",
  "estado_requerido": "texto",
  "plan_accion": [
    {{
      "accion": "texto",
      "prioridad": "Alta|Media|Baja",
      "responsable_sugerido": "texto",
      "plazo": "texto",
      "evidencia_esperada": "texto"
    }}
  ]
}}

REGLAS PARA estado_actual:
- No respondas solo con el porcentaje.
- Redacta entre 2 y 4 párrafos.
- Explica qué tan maduro está el criterio actualmente.
- Menciona fortalezas visibles según respuestas SI.
- Menciona brechas según respuestas NO y PARCIAL.
- Usa los comentarios/evidencias cuando existan.
- Si hay pocas evidencias, dilo claramente.
- No inventes herramientas ni controles que no estén soportados por las respuestas.

REGLAS PARA estado_requerido:
- No respondas solo con "100% de cumplimiento".
- Redacta entre 2 y 4 párrafos.
- Describe el estado objetivo esperado para ISO 22301.
- Explica qué controles, evidencias, formalización, monitoreo y mejora deberían existir.
- Relaciona el estado requerido con auditoría, trazabilidad, evidencia y operación sostenida.
- No inventes marcas ni herramientas específicas.

REGLAS PARA plan_accion:
- Genera entre 5 y 8 acciones.
- Prioriza primero respuestas NO y PARCIAL.
- Cada acción debe ser concreta, auditable y verificable.
- La evidencia esperada debe ser un entregable real: política, procedimiento, matriz, registro, acta, reporte, evidencia de monitoreo, prueba de control, etc.
- Usa prioridades Alta, Media o Baja.

TONO
Profesional, ejecutivo y consultivo.
Enfocado en madurez ISO 22301 y preparación para auditoría.
""".strip()


# ============================================================
# CARGA DEL CATÁLOGO E IMPORTACIÓN DEL INSTRUMENTO ISO 22301
# ============================================================
def _iso22301_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    txt = _iso22301_norm(value)
    return txt not in ("0", "FALSE", "FALSO", "NO", "INACTIVO")


def _iso22301_catalog_from_excel(xlsx_path):
    df = pd.read_excel(xlsx_path, sheet_name="Catálogo Arkyntech", header=0)
    normalized = {_iso22301_norm(c): c for c in df.columns}
    required = {
        "ITEM_ID", "CHAPTER", "CLAUSE", "DOMAIN_ES",
        "ASSESSMENT_QUESTION_ES", "SUGGESTED_EVIDENCE_ES"
    }
    missing = sorted(required - set(normalized))
    if missing:
        raise ValueError("Faltan columnas en 'Catálogo Arkyntech': " + ", ".join(missing))

    rows = []
    for _, row in df.iterrows():
        item_id = iso22301_safe_str(row.get(normalized["ITEM_ID"]))
        question = iso22301_normalizar_texto_excel(row.get(normalized["ASSESSMENT_QUESTION_ES"]))
        if not item_id or not question:
            continue
        rows.append({
            "item_id": item_id,
            "standard_code": iso22301_safe_str(row.get(normalized.get("STANDARD_CODE"))) or "ISO 22301",
            "standard_version": iso22301_safe_str(row.get(normalized.get("STANDARD_VERSION"))) or "2019+Amd1:2024",
            "chapter": iso22301_safe_str(row.get(normalized["CHAPTER"])).replace(".0", ""),
            "clause": iso22301_safe_str(row.get(normalized["CLAUSE"])),
            "domain_es": iso22301_safe_str(row.get(normalized["DOMAIN_ES"])),
            "assessment_question_es": question,
            "suggested_evidence_es": iso22301_normalizar_texto_excel(row.get(normalized["SUGGESTED_EVIDENCE_ES"])),
            "default_weight": 1,
            "active": _iso22301_bool(row.get(normalized.get("ACTIVE")), True),
        })
    return rows


def iso22301_seed_catalog(catalog_rows, replace=False):
    if replace:
        Iso22301MadurezCriterioAnalisis.query.delete(synchronize_session=False)
        Iso22301MadurezRespuesta.query.delete(synchronize_session=False)
        Iso22301MadurezRun.query.delete(synchronize_session=False)
        Iso22301MadurezPregunta.query.delete(synchronize_session=False)
        db.session.flush()
    elif Iso22301MadurezPregunta.query.filter_by(tipo="q").first():
        return {"headers": 0, "questions": 0, "ignored": 0}

    headers_created = set()
    creadas_q = 0
    creadas_h = 0
    ignoradas = 0
    orden = 1

    for item in catalog_rows or []:
        chapter = str(item.get("chapter") or "").strip().replace(".0", "")
        clause = str(item.get("clause") or "").strip()
        domain = str(item.get("domain_es") or "").strip()
        item_id = str(item.get("item_id") or "").strip()
        question = iso22301_normalizar_texto_excel(item.get("assessment_question_es"))
        evidence = iso22301_normalizar_texto_excel(item.get("suggested_evidence_es"))
        if chapter not in ISO22301_BLOCK_TITLES or not item_id or not question:
            ignoradas += 1
            continue

        if chapter not in headers_created:
            title = ISO22301_BLOCK_TITLES[chapter]
            db.session.add(Iso22301MadurezPregunta(
                bloque_codigo=chapter,
                bloque_nombre=title,
                seccion_codigo=chapter,
                seccion_nombre=title,
                pregunta_codigo=f"CAP-{chapter}",
                pregunta=title,
                evidencia_sugerida=None,
                tipo="h",
                orden=orden,
                activo=True,
            ))
            orden += 1
            creadas_h += 1
            headers_created.add(chapter)

        db.session.add(Iso22301MadurezPregunta(
            bloque_codigo=chapter,
            bloque_nombre=ISO22301_BLOCK_TITLES[chapter],
            seccion_codigo=clause,
            seccion_nombre=domain,
            pregunta_codigo=item_id,
            pregunta=question,
            evidencia_sugerida=evidence,
            tipo="q",
            orden=orden,
            activo=_iso22301_bool(item.get("active"), True),
        ))
        orden += 1
        creadas_q += 1

    db.session.commit()
    return {"headers": creadas_h, "questions": creadas_q, "ignored": ignoradas}


@iso22301_madurez_bp.route("/admin/importar_instrumento", methods=["POST"])
@login_required
def importar_instrumento_iso22301():
    user = User.query.get(session.get("user_id"))
    if user.role == "auditor":
        flash("El rol Auditor no puede importar instrumentos.", "danger")
        return redirect(url_for("madurez_iso22301.parametros"))
    if user.role != "admin" and not verificar_permiso(user, ISO22301_PERMISSION_NAME):
        flash("No tiene permiso para importar el instrumento ISO 22301.", "danger")
        return redirect(url_for("menu"))

    force = (request.args.get("force") == "1") or (request.form.get("force") == "1")
    try:
        if Iso22301MadurezPregunta.query.filter_by(tipo="q").first() and not force:
            flash("El instrumento ISO 22301 ya está cargado en la base de datos.", "warning")
            return redirect(url_for("madurez_iso22301.parametros"))

        alternativas = [
            ISO22301_INSTRUMENTO_TEMPLATE_XLSX,
            os.path.join(BASE_DIR, "static", "templates", "Arkyntech_Matriz_Madurez_ISO_22301_ES(1).xlsx"),
            os.path.join(BASE_DIR, "static", "templates", "ISO 22301.xlsx"),
        ]
        xlsx_path = next((p for p in alternativas if os.path.exists(p)), None)
        catalog_rows = _iso22301_catalog_from_excel(xlsx_path) if xlsx_path else ISO22301_EMBEDDED_CATALOG
        stats = iso22301_seed_catalog(catalog_rows, replace=force)
        source_name = os.path.basename(xlsx_path) if xlsx_path else "catálogo integrado en Arkyntech"
        flash(
            f"✅ Instrumento ISO 22301 importado desde {source_name}. "
            f"Capítulos: {stats['headers']} | Preguntas: {stats['questions']} | Ignoradas: {stats['ignored']}",
            "success",
        )
        return redirect(url_for("madurez_iso22301.parametros"))
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        flash(f"❌ Error importando instrumento ISO 22301: {e}", "danger")
        return redirect(url_for("madurez_iso22301.parametros"))


# ============================================================
# CONSOLIDAR ANÁLISIS
# ============================================================
def run_analysis_from_iso22301_run(iso22301_run_id: int):
    run = Iso22301MadurezRun.query.get_or_404(iso22301_run_id)
    resumen = _iso22301_build_resumen(run.id)
    # Cálculo general ponderado por pregunta aplicable. N/A se conserva
    # en el historial, pero no suma ni forma parte del denominador.
    pct_general = iso22301_pct_general_from_resumen(resumen)
    labels, values = iso22301_pct_por_criterio(resumen, ISO22301_BLOCK_ORDER)
    run.resumen_json = json.dumps(resumen, ensure_ascii=False)
    run.pct_general = pct_general
    run.radar_overall_b64 = iso22301_radar_b64(labels, values, title="Radar por Capítulo - ISO 22301")
    run.company_name = run.consecutivo
    run.updated_at = datetime.utcnow()
    db.session.commit()
    return run.id

# ============================================================
# PERMISOS ISO 22301 — ADMIN / USUARIO CON PERMISO / AUDITOR
# ============================================================

def iso22301_user_can_access(user):
    """
    Puede VER el módulo:
    - admin
    - auditor
    - usuario con permiso Nivel de madurez ISO 22301
    """
    return bool(
        user and (
            user.role in ("admin", "auditor")
            or verificar_permiso(user, ISO22301_PERMISSION_NAME)
        )
    )


def iso22301_user_can_execute(user):
    """
    Puede EJECUTAR / MODIFICAR:
    - admin
    - usuario con permiso Nivel de madurez ISO 22301

    Auditor NO puede:
    - editar
    - eliminar
    - generar IA
    - exportar PDF
    - importar instrumento
    - guardar / analizar
    """
    return bool(
        user
        and user.role != "auditor"
        and (
            user.role == "admin"
            or verificar_permiso(user, ISO22301_PERMISSION_NAME)
        )
    )


def iso22301_check_access_or_redirect(user, msg="No tiene permiso para acceder al módulo ISO 22301."):
    if not iso22301_user_can_access(user):
        flash(msg, "danger")
        return redirect(url_for("menu"))
    return None


def iso22301_check_execute_or_redirect(user, msg="No tiene permiso para ejecutar esta acción en ISO 22301."):
    if not iso22301_user_can_execute(user):
        flash(msg, "danger")
        return redirect(url_for("madurez_iso22301.inicio_iso22301"))
    return None


# Alias para compatibilidad con bloques anteriores
def iso22301_deny_access(msg="No tiene permiso para acceder al módulo ISO 22301."):
    flash(msg, "danger")
    return redirect(url_for("menu"))


def iso22301_deny_execute(msg="No tiene permiso para ejecutar esta acción en ISO 22301."):
    flash(msg, "danger")
    return redirect(url_for("madurez_iso22301.inicio_iso22301"))


# ============================================================
# PANTALLA PRINCIPAL — MISMO DISEÑO NIST
# ============================================================

@iso22301_madurez_bp.route("/", methods=["GET"], endpoint="inicio_iso22301")
@login_required
def inicio_iso22301():
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_access(user):
        return iso22301_deny_access("No tiene permiso para acceder al módulo de nivel de madurez ISO 22301.")

    read_only = user.role == "auditor"

    ingreso_btn = """
      <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled title="El rol Auditor no puede ingresar información">
        <i class="bi bi-pencil-square me-2"></i>Ingresar la información
      </button>
    """ if read_only else f"""
      <a href="{url_for('madurez_iso22301.ingreso')}" class="btn nistmad-btn-primary rounded-pill px-4 fw-bold">
        <i class="bi bi-pencil-square me-2"></i>Ingresar la información
      </a>
    """

    parametros_btn = """
      <button class="btn btn-outline-secondary rounded-pill px-3" disabled title="El rol Auditor no puede modificar parámetros">
        <i class="bi bi-gear me-2"></i>Parámetros
      </button>
    """ if read_only else f"""
      <a href="{url_for('madurez_iso22301.parametros')}" class="btn btn-outline-secondary rounded-pill px-3">
        <i class="bi bi-gear me-2"></i>Parámetros
      </a>
    """

    total = Iso22301MadurezPregunta.query.filter_by(tipo="q").count()
    badge = '<span class="badge bg-success ms-2">Instrumento cargado</span>' if total else '<span class="badge bg-danger ms-2">Instrumento NO cargado</span>'
    hint = "Puedes ingresar la información, analizar la evaluación o consultar el historial." if total else "Primero entra a Parámetros e importa el instrumento ISO 22301."

    content = f"""
<div class="nistmad-shell">

  <div class="nistmad-header-card">
    <div class="nistmad-header-overlay">
      <div class="nistmad-header-text">
        <h3 class="nistmad-title m-0">Nivel de Madurez — ISO 22301</h3>
        <div class="nistmad-subtitle">
          Evaluación por capítulos 4 a 10: Contexto, Liderazgo, Planificación, Apoyo,
          Operación, Evaluación del desempeño y Mejora.
        </div>
      </div>
    </div>
  </div>

  <div class="nistmad-header-actions">
    {ingreso_btn}
    <a href="{url_for('madurez_iso22301.historial')}" class="btn nistmad-btn-soft rounded-pill px-4 historial-pill">
      <span class="d-inline-flex align-items-center gap-2">
        <span class="hist-dot"></span>
        <i class="bi bi-clock-history"></i>
        <span class="fw-semibold">Historial de Revisiones</span>
      </span>
    </a>
  </div>

  <div class="row g-3 mt-2">
    <div class="col-12 col-lg-8">
      <div class="nistmad-card p-4 h-100">
        <div class="nistmad-section-title">Estado del instrumento</div>
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
          <b>Sugerencia:</b> Usa <b>Parámetros</b> para ver la definición de niveles 1–5
          y gestionar la importación del instrumento ISO 22301.
        </div>
      </div>
    </div>

    <div class="col-12 col-lg-4">
      <div class="nistmad-card p-4 h-100">
        <div class="nistmad-section-title">¿Qué puedes hacer aquí?</div>
        <ul class="small mb-0 text-black ps-3">
          <li><b>Ingresar la información:</b> diligenciar respuestas con evidencia.</li>
          <li><b>Historial:</b> revisar evaluaciones previas y resultados.</li>
          <li><b>Parámetros:</b> gestionar niveles e instrumento, excepto auditor.</li>
        </ul>
      </div>
    </div>
  </div>
</div>
{iso22301_nist_css('nistmad', '🛡️')}
"""
    return render_template_string(BASE, title="Madurez ISO 22301", content=content)

# ============================================================
# PARÁMETROS — USUARIO CON PERMISO PUEDE MODIFICAR / AUDITOR NO
# ============================================================

@iso22301_madurez_bp.route("/parametros", methods=["GET", "POST"])
@login_required
def parametros():
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("No tiene permiso para administrar parámetros ISO 22301.")

    seed_iso22301_parametros()

    if request.method == "POST":
        try:
            for r in Iso22301MadurezParametro.query.all():
                r.nivel = (request.form.get(f"nivel_{r.id}") or r.nivel).strip()
                r.rango_desde = float(request.form.get(f"desde_{r.id}") or r.rango_desde)
                r.rango_hasta = float(request.form.get(f"hasta_{r.id}") or r.rango_hasta)
                r.color = (request.form.get(f"color_{r.id}") or r.color).strip()
                r.descripcion = (request.form.get(f"descripcion_{r.id}") or "").strip()
            db.session.commit()
            flash("✅ Parámetros ISO 22301 guardados correctamente.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error guardando parámetros ISO 22301: {e}", "danger")
        return redirect(url_for("madurez_iso22301.parametros"))

    rows = []
    for r in Iso22301MadurezParametro.query.order_by(Iso22301MadurezParametro.orden.asc()).all():
        rows.append(f"""
        <tr>
          <td><input class="form-control" name="nivel_{r.id}" value="{escape(r.nivel or '')}"></td>
          <td class="text-center"><input class="form-control text-center" name="desde_{r.id}" value="{r.rango_desde}"></td>
          <td class="text-center"><input class="form-control text-center" name="hasta_{r.id}" value="{r.rango_hasta}"></td>
          <td class="text-center"><input type="color" class="form-control form-control-color mx-auto" name="color_{r.id}" value="{escape(r.color or '#6c757d')}"></td>
          <td><textarea class="form-control" name="descripcion_{r.id}" rows="2">{escape(r.descripcion or '')}</textarea></td>
        </tr>
        """)

    resumen = iso22301_resumen_instrumento()

    content = f"""
<div class="nistpar-shell">
  <div class="nistpar-header-card">
    <div class="nistpar-header-overlay">
      <div class="nistpar-header-text">
        <h3 class="nistpar-title m-0">Parámetros de Madurez — ISO 22301</h3>
        <div class="nistpar-subtitle">Configuración de niveles, rangos de madurez e importación del instrumento.</div>
      </div>
    </div>
  </div>

  <div class="nistpar-header-actions">
    <a href="{url_for('madurez_iso22301.inicio_iso22301')}" class="btn nistpar-btn-main rounded-pill px-4 fw-bold">
      <i class="bi bi-arrow-left me-2"></i>Volver
    </a>
    <form method="POST" action="{url_for('madurez_iso22301.importar_instrumento_iso22301')}" class="m-0">
      <button class="btn btn-success rounded-pill px-4 fw-bold">
        <i class="bi bi-upload me-2"></i>Importar instrumento
      </button>
    </form>
    <form method="POST" action="{url_for('madurez_iso22301.importar_instrumento_iso22301')}?force=1" class="m-0" onsubmit="return confirm('¿Borrar e importar de nuevo el instrumento ISO 22301?')">
      <button class="btn btn-danger rounded-pill px-4 fw-bold">
        <i class="bi bi-arrow-repeat me-2"></i>Reimportar
      </button>
    </form>
  </div>

  <div class="nistpar-card p-4 mb-3">
    <div class="nistpar-section-title">Resumen instrumento</div>
    <div class="small text-black">
      Preguntas: <b>{resumen['total_preguntas']}</b> · Cabeceras: <b>{resumen['total_headers']}</b> · Por capítulo: <b>{escape(str(resumen['por_bloque']))}</b>
    </div>
  </div>

  <form method="POST" class="nistpar-card p-4">
    <div class="nistpar-section-title">Niveles de madurez</div>
    <div class="table-responsive">
      <table class="table table-hover align-middle nistpar-table">
        <thead class="nistpar-table-head">
          <tr>
            <th style="width:28%;">Nivel de Madurez</th>
            <th class="text-center" style="width:110px;">Desde %</th>
            <th class="text-center" style="width:110px;">Hasta %</th>
            <th class="text-center" style="width:90px;">Color</th>
            <th>Descripción del Nivel</th>
          </tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    <div class="text-end mt-3">
      <button class="btn btn-primary rounded-pill px-4 fw-bold">
        <i class="bi bi-save me-2"></i>Guardar parámetros
      </button>
    </div>
  </form>
</div>
{iso22301_nist_css('nistpar', '⚙️')}
"""
    return render_template_string(BASE, title="Parámetros ISO 22301", content=content)


# ============================================================
# INGRESO DE INFORMACIÓN ISO 22301 — SIN LOADER GLOBAL EN VALIDACIÓN
# ============================================================

