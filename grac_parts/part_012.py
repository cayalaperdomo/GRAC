@app.route('/plan_diseno/edit/<int:id>', methods=['GET','POST'])
@login_required
def plan_diseno_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Plan de Concientización y Formación")
    ):
        flash("No tiene permiso para editar registros del plan.", "danger")
        return redirect(url_for('plan_diseno_matriz'))
    
    item = PlanDisenoRegistro.query.get_or_404(id)
    areas, divisiones_por_area = obtener_areas_y_divisiones_plan()

    if request.method == 'POST':
        item.tema_capacitacion = (request.form.get('tema_capacitacion') or '').strip()
        item.descripcion       = (request.form.get('descripcion') or '').strip()
        item.horas             = request.form.get('horas', type=int) or 0
        item.dirigida_area      = (request.form.get('dirigida_area') or '').strip()
        item.dirigida_division  = (request.form.get('dirigida_division') or '').strip()
        item.fecha_programada  = request.form.get('fecha_programada') or ''
        item.fecha_ejecucion   = request.form.get('fecha_ejecucion') or ''
        item.responsable       = (request.form.get('responsable') or '').strip()
        item.metodologia       = (request.form.get('metodologia') or '').strip()
        item.evidencia         = (request.form.get('evidencia') or '').strip()
        item.observaciones     = (request.form.get('observaciones') or '').strip()

        # 🔹 Nuevas evidencias PDF
        files = request.files.getlist('evidencias')
        for f in files:
            if not f or not f.filename:
                continue
            if not is_allowed_pdf(f.filename):
                flash(f"Archivo no permitido (solo PDF): {f.filename}", "danger")
                continue

            store_name = unique_store_name(f.filename)
            path = os.path.join(app.config['UPLOAD_PLAN_DISENO_DIR'], store_name)
            f.save(path)

            ev = PlanDisenoEvidencia(
                registro=item,
                filename=store_name,
                original_name=secure_filename(f.filename),
                mime='application/pdf',
                size=os.path.getsize(path)
            )
            db.session.add(ev)

        db.session.commit()
        flash("Registro del plan actualizado.", "success")
        return redirect(url_for('plan_diseno_matriz'))

    html = """
    <div class="plancapedit-shell">

      <!-- CABECERA -->
      <div class="plancapedit-header-card">
        <div class="plancapedit-header-overlay">
          <div class="plancapedit-header-text">
            <h3 class="plancapedit-title m-0">Editar registro del Plan de Concientización y Formación</h3>
            <div class="plancapedit-subtitle">
              Actualización de actividades de capacitación, concientización y formación del SGSI, incluyendo público objetivo, fechas, responsable, metodología y evidencias
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="plancapedit-header-actions">
        <a href="{{ url_for('plan_diseno_matriz') }}"
           class="btn rounded-pill px-5 fw-bold plancapedit-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <!-- TARJETA PRINCIPAL -->
      <div class="plancapedit-card">
        <div class="plancapedit-card-body">

          <form method="post" enctype="multipart/form-data">
            <div class="row g-3">

              <div class="col-12">
                <div class="plancapedit-section-title">Información de la actividad</div>
              </div>

              <div class="col-md-6">
                <label class="form-label">Tema de la capacitación</label>
                <input class="form-control"
                       name="tema_capacitacion"
                       value="{{ item.tema_capacitacion or '' }}"
                       required>
              </div>

              <div class="col-md-6">
                <label class="form-label"># Horas</label>
                <input type="number"
                       class="form-control"
                       name="horas"
                       min="0"
                       value="{{ item.horas or 0 }}">
              </div>

              <div class="col-md-12">
                <label class="form-label">Descripción</label>
                <textarea class="form-control"
                          name="descripcion"
                          rows="2">{{ item.descripcion or '' }}</textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Dirigida a (área)</label>
                <select class="form-select"
                        name="dirigida_area"
                        id="dirigida_area"
                        required
                        onchange="cargarDivisionesPlan()">
                  <option value="">-- Seleccione --</option>
                  <option value="Todas las áreas" {% if item.dirigida_area == 'Todas las áreas' %}selected{% endif %}>Todas las áreas</option>
                  {% for a in areas %}
                    <option value="{{ a }}" {% if item.dirigida_area == a %}selected{% endif %}>{{ a }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Dirigida a (división)</label>
                <select class="form-select"
                        name="dirigida_division"
                        id="dirigida_division"
                        required>
                  <option value="">-- Seleccione un área primero --</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha programada</label>
                <input type="date"
                       class="form-control"
                       name="fecha_programada"
                       value="{{ item.fecha_programada or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha ejecución</label>
                <input type="date"
                       class="form-control"
                       name="fecha_ejecucion"
                       value="{{ item.fecha_ejecucion or '' }}">
              </div>

              <div class="col-md-6">
                <label class="form-label">Responsable</label>
                <input class="form-control"
                       name="responsable"
                       value="{{ item.responsable or '' }}">
              </div>

              <div class="col-md-6">
                <label class="form-label">Metodología medición, evaluación y eficacia</label>
                <textarea class="form-control"
                          name="metodologia"
                          rows="2">{{ item.metodologia or '' }}</textarea>
              </div>

              <div class="col-12">
                <div class="plancapedit-section-title">Evidencias y observaciones</div>
              </div>

              <div class="col-md-6">
                <label class="form-label">Agregar nuevas evidencias PDF</label>
                <input type="file"
                       name="evidencias"
                       class="form-control"
                       accept="application/pdf"
                       multiple>
                <small class="text-muted">Solo PDF. Puedes adjuntar varios.</small>
              </div>

              <div class="col-md-6">
                <label class="form-label">Observaciones</label>
                <textarea class="form-control"
                          name="observaciones"
                          rows="2">{{ item.observaciones or '' }}</textarea>
              </div>

            </div>

            <div class="plancapedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>

              <a class="btn rounded-pill px-4 fw-bold plancapedit-cancel-btn"
                 href="{{ url_for('plan_diseno_matriz') }}">
                Cancelar
              </a>
            </div>
          </form>

          <hr class="my-4">

          <div class="plancapedit-section-title">Evidencias PDF existentes</div>

          <div class="table-responsive plancapedit-table-wrap">
            <table class="table table-sm align-middle mb-0">
              <thead class="plancapedit-table-head">
                <tr>
                  <th>Archivo</th>
                  <th>Tamaño</th>
                  <th style="width:22%">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {% for ev in item.evidencias %}
                  <tr>
                    <td class="text-break">{{ ev.original_name }}</td>
                    <td>{{ (ev.size or 0) // 1024 }} KB</td>
                    <td>
                      <a class="btn btn-outline-primary btn-sm rounded-pill px-3"
                           href="{{ url_for('plan_diseno_evidencia_view', evi_id=ev.id, next='plan_diseno_edit', reg_id=item.id) }}">
                          Ver en navegador
                      </a>

                      <form method="post"
                            action="{{ url_for('plan_diseno_evidencia_delete', evi_id=ev.id) }}"
                            class="d-inline"
                            onsubmit="return confirm('¿Eliminar esta evidencia?');">
                        <button class="btn btn-outline-danger btn-sm rounded-pill px-3" type="submit">
                          Eliminar
                        </button>
                      </form>
                    </td>
                  </tr>
                {% else %}
                  <tr>
                    <td colspan="3" class="text-muted text-center">Sin evidencias PDF</td>
                  </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>

        </div>
      </div>
    </div>

    <style>
    /* =========================
       FONDO SGSI
    ========================= */
    body{
      background-image:url('/static/img/ccsgsi.jpg');
      background-size:cover;
      background-position:center;
      background-attachment:fixed;
      background-repeat:no-repeat;
    }

    /* =========================
       CONTENEDOR
    ========================= */
    .plancapedit-shell{
      width:96%;
      max-width:1500px;
      margin:10px auto 24px auto;
    }

    /* =========================
       HEADER SGSI MODERNO (🔥 CLAVE)
    ========================= */
    .plancapedit-header-card{
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

    .plancapedit-header-card::before{
      content:"";
      position:absolute;
      inset:0;
      background:
        radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
        repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
    }

    .plancapedit-header-overlay{
      width:100%;
      display:flex;
      align-items:center;
      justify-content:flex-start;
      text-align:left;
      position:relative;
      z-index:1;
      background:transparent !important;
      padding:0 !important;
    }

    .plancapedit-header-overlay::before{
      content:"✏️";
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

    .plancapedit-header-text{
      max-width:1100px;
    }

    .plancapedit-header-text::before{
      content:"SGSI · Edición Plan Capacitación";
      display:inline-block;
      background:rgba(255,255,255,.18);
      border-radius:999px;
      padding:3px 10px;
      font-size:.65rem;
      font-weight:800;
      margin-bottom:4px;
      color:#fff;
    }

    .plancapedit-title{
      color:#ffffff !important;
      font-weight:950;
      font-size:1.32rem;
      line-height:1.1;
      text-shadow:0 3px 10px rgba(0,0,0,.35);
      margin:0 !important;
    }

    .plancapedit-subtitle{
      color:rgba(255,255,255,.95);
      font-size:.78rem;
      margin-top:4px;
    }

    /* =========================
       BOTONES
    ========================= */
    .plancapedit-header-actions{
      display:flex;
      justify-content:center;
      gap:10px;
      flex-wrap:wrap;
      margin:10px 0 14px;
    }

    .plancapedit-header-actions .btn{
      border-radius:10px !important;
      font-weight:900;
      box-shadow:0 8px 16px rgba(15,23,42,.15);
    }

    .plancapedit-back-btn{
      background:#ffffff;
      color:#0f172a;
      border:1px solid #cfd8e3;
    }

    .plancapedit-back-btn:hover{
      background:#edf5ff;
      color:#0b65d8;
    }

    /* =========================
       CARD
    ========================= */
    .plancapedit-card{
      background:rgba(255,255,255,.96)!important;
      border-radius:18px;
      backdrop-filter:blur(8px);
      box-shadow:0 12px 24px rgba(15,23,42,.18);
      border:1px solid rgba(219,230,244,.9);
      overflow:hidden;
    }

    .plancapedit-card-body{
      padding:18px;
    }

    /* =========================
       FORMULARIOS
    ========================= */
    .plancapedit-card .form-label{
      font-weight:800;
      font-size:.75rem;
      text-transform:uppercase;
      color:#0b4a8f;
    }

    .plancapedit-card .form-control,
    .plancapedit-card .form-select{
      border-radius:10px;
      border:1px solid #dbe6f4;
      min-height:40px;
      font-size:.85rem;
    }

    .plancapedit-card .form-control:focus,
    .plancapedit-card .form-select:focus{
      border-color:#1d5fae;
      box-shadow:0 0 0 0.2rem rgba(44,123,229,.15);
    }

    /* =========================
       SECCIONES
    ========================= */
    .plancapedit-section-title{
      font-weight:950;
      font-size:.78rem;
      color:#0b4a8f;
      padding:10px 12px;
      border-radius:12px;
      background:#eef5ff;
      border:1px solid #d9eaff;
      margin-bottom:12px;
    }

    /* =========================
       TABLA SGSI
    ========================= */
    .plancapedit-table-wrap{
      border:1px solid #dbe6f4;
      border-radius:14px;
      overflow:hidden;
    }

    .plancapedit-table-head th{
      background:#3f86d6 !important;
      color:#fff !important;
      font-weight:900;
      font-size:.78rem;
    }

    .table-hover tbody tr:hover{
      background:rgba(63,134,214,.08);
    }

    /* =========================
       BOTONES INFERIORES
    ========================= */
    .plancapedit-bottom-actions{
      display:flex;
      justify-content:center;
      gap:12px;
      margin-top:26px;
      flex-wrap:wrap;
    }

    .plancapedit-cancel-btn{
      background:#ffffff;
      color:#000;
      border:1px solid #cfd8e3;
    }

    .plancapedit-cancel-btn:hover{
      background:#edf5ff;
    }

    /* =========================
       RESPONSIVE
    ========================= */
    @media (max-width:992px){
      .plancapedit-shell{ width:98%; }

      .plancapedit-title{ font-size:1.15rem; }

      .plancapedit-card-body{ padding:8px 7px; }

      .plancapedit-header-overlay{
        flex-direction:column;
        text-align:center;
      }

      .plancapedit-header-overlay::before{
        margin:0 0 8px 0;
      }
    }
    </style>

    <script>
      const divisionesPlanPorArea = {{ divisiones_por_area|tojson }};

      function cargarDivisionesPlan(valorSeleccionado = null) {
        const areaSel = document.getElementById('dirigida_area');
        const divSel = document.getElementById('dirigida_division');
        const area = (areaSel.value || '').trim();

        divSel.innerHTML = '';

        if (!area) {
          divSel.innerHTML = '<option value="">-- Seleccione un área primero --</option>';
          return;
        }

        let opciones = '<option value="">-- Seleccione --</option>';
        opciones += '<option value="Todas las divisiones">Todas las divisiones</option>';

        if (area !== 'Todas las áreas') {
          const divisiones = divisionesPlanPorArea[area] || [];
          for (const d of divisiones) {
            opciones += `<option value="${d}">${d}</option>`;
          }
        }

        divSel.innerHTML = opciones;

        if (valorSeleccionado) {
          divSel.value = valorSeleccionado;
        }
      }

      window.addEventListener('DOMContentLoaded', function () {
        cargarDivisionesPlan({{ (item.dirigida_division or '')|tojson }});
      });
    </script>
    """
    inner = render_template_string(
        html,
        item=item,
        areas=areas,
        divisiones_por_area=divisiones_por_area
    )
    return render_template_string(BASE, content=Markup(inner))

# =========================
# ELIMINAR — Plan de Concientización y Formación
# =========================
@app.route('/plan_diseno/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def plan_diseno_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros.", "danger")
        return redirect(url_for('plan_diseno_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Plan de Concientización y Formación"):
        flash("No tiene permiso para eliminar registros.", "danger")
        return redirect(url_for('plan_diseno_matriz'))

    if request.method == 'GET':
        flash("Para eliminar un registro debes usar el botón Eliminar desde la matriz.", "warning")
        return redirect(url_for('plan_diseno_matriz'))

    item = PlanDisenoRegistro.query.get(id)

    if not item:
        flash("El registro no existe o ya fue eliminado.", "warning")
        return redirect(url_for('plan_diseno_matriz'))

    try:
        db.session.delete(item)
        db.session.commit()
        flash("Plan de concientización eliminado correctamente.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"No fue posible eliminar el plan de concientización: {str(e)}", "danger")

    return redirect(url_for('plan_diseno_matriz'))

@app.route('/plan_diseno/evidencia/<int:evi_id>/file')
@login_required
def plan_diseno_evidencia_file(evi_id):
    evi = PlanDisenoEvidencia.query.get_or_404(evi_id)
    fullpath = os.path.join(app.config['UPLOAD_PLAN_DISENO_DIR'], evi.filename)

    if not os.path.isfile(fullpath):
        abort(404)

    return send_file(
        fullpath,
        mimetype=evi.mime or 'application/pdf',
        as_attachment=False,
        download_name=evi.original_name or evi.filename,
        conditional=True
    )

@app.route('/plan_diseno/evidencia/<int:evi_id>/view')
@login_required
def plan_diseno_evidencia_view(evi_id):
    evi = PlanDisenoEvidencia.query.get_or_404(evi_id)

    path = os.path.join(app.config['UPLOAD_PLAN_DISENO_DIR'], evi.filename)
    if not os.path.isfile(path):
        abort(404)

    ext = os.path.splitext(evi.filename or '')[1].lower()
    is_pdf = ext == '.pdf'
    is_office = ext in {'.doc', '.docx', '.xls', '.xlsx'}
    is_image = ext in {'.png', '.jpg', '.jpeg', '.webp', '.gif'}

    # =========================
    # Botón volver
    # =========================
    next_ep = request.args.get('next')
    reg_id = request.args.get('reg_id', type=int)

    if next_ep == 'plan_diseno_detalle' and reg_id:
        back_url = url_for('plan_diseno_detalle', id=reg_id)
        back_label = '⬅ Volver al Detalle'
    elif next_ep == 'plan_diseno_edit' and reg_id:
        back_url = url_for('plan_diseno_edit', id=reg_id)
        back_label = '⬅ Volver a Edición'
    elif next_ep == 'plan_diseno_matriz':
        back_url = url_for('plan_diseno_matriz')
        back_label = '⬅ Volver a la Matriz'
    elif next_ep == 'plan_diseno_menu':
        back_url = url_for('plan_diseno_menu')
        back_label = '⬅ Volver al Menú'
    else:
        back_url = request.referrer or url_for('plan_diseno_matriz')
        back_label = '⬅ Volver'

    # =========================
    # Conversión Office -> PDF
    # =========================
    pdf_converted_name = None
    if is_office:
        try:
            converted_dir = app.config.get(
                'UPLOAD_PLAN_DISENO_CONVERTED_DIR',
                os.path.join(app.root_path, 'static', 'converted_plan_diseno_evidencias')
            )
            os.makedirs(converted_dir, exist_ok=True)

            pdf_converted_path = ensure_pdf_from_office(path, output_dir=converted_dir)

            if pdf_converted_path and os.path.isfile(pdf_converted_path):
                pdf_converted_name = os.path.basename(pdf_converted_path)
        except Exception:
            pdf_converted_name = None

    inner_html = """
    <div class="plancevi-shell">

      <div class="plancevi-header-actions">
        <a href="{{ back_url }}"
           class="btn rounded-pill px-4 py-2 fw-bold plancevi-back-btn">
          {{ back_label }}
        </a>

        <div class="plancevi-file-pill" title="{{ original_name }}">
          📎 {{ original_name }}
        </div>
      </div>

      <div class="plancevi-card">
        <div class="plancevi-card-body">

          {% if is_pdf %}
            <div class="plancevi-pdf-container">
              <iframe id="pdfFrame"
                      src="{{ url_for('plan_diseno_evidencia_file', evi_id=evi_id) }}#zoom=page-width"
                      title="Visor PDF"></iframe>
            </div>

          {% elif pdf_converted_name %}
            <div class="plancevi-pdf-container">
              <iframe id="pdfFrame"
                      src="{{ url_for('plan_diseno_evidencia_convertido', filename=pdf_converted_name) }}#zoom=page-width"
                      title="Visor PDF convertido"></iframe>
            </div>

            <div class="plancevi-extra-actions">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('plan_diseno_evidencia_file', evi_id=evi_id) }}">
                Abrir archivo original
              </a>
            </div>

          {% elif is_image %}
            <div class="text-center p-3">
              <img src="{{ url_for('plan_diseno_evidencia_file', evi_id=evi_id) }}"
                   alt="{{ original_name }}"
                   class="img-fluid rounded-4 shadow-sm"
                   style="max-height: 78vh; object-fit: contain;">
            </div>

          {% elif is_office %}
            <div class="alert alert-warning m-2 rounded-4">
              No fue posible generar una vista previa interna del archivo Office.
              Verifica que LibreOffice esté instalado en el servidor.
            </div>

            <div class="plancevi-extra-actions">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('plan_diseno_evidencia_file', evi_id=evi_id) }}">
                Abrir / descargar archivo original
              </a>
            </div>

          {% else %}
            <div class="alert alert-info m-2 rounded-4">
              Este tipo de archivo (<b>{{ ext }}</b>) no se puede previsualizar.
              Puedes abrirlo o descargarlo.
            </div>

            <div class="plancevi-extra-actions">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('plan_diseno_evidencia_file', evi_id=evi_id) }}">
                Abrir archivo
              </a>
            </div>
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

      .plancevi-shell{
        width:96%;
        max-width:1500px;
        margin:22px auto 30px auto;
      }

      .plancevi-header-actions{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        flex-wrap:wrap;
        margin-bottom:16px;
      }

      .plancevi-back-btn{
        background:#ffffff;
        color:#000000;
        border:2px solid #ffffff;
        box-shadow:0 4px 10px rgba(0,0,0,.10);
      }

      .plancevi-back-btn:hover{
        background:#f3f4f6;
        color:#000000;
        border-color:#f3f4f6;
      }

      .plancevi-file-pill{
        max-width:70%;
        background:rgba(255,255,255,.92);
        color:#101827;
        border:1px solid rgba(0,0,0,.08);
        border-radius:999px;
        padding:10px 16px;
        font-size:.90rem;
        font-weight:700;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
        box-shadow:0 4px 10px rgba(0,0,0,.10);
      }

      .plancevi-card{
        background:rgba(255,255,255,.88)!important;
        border-radius:18px;
        backdrop-filter:blur(6px);
        box-shadow:0 10px 24px rgba(0,0,0,.18);
        overflow:hidden;
      }

      .plancevi-card-body{
        padding:8px 7px;
      }

      .plancevi-pdf-container{
        height:min(82vh,1000px);
        min-height:600px;
        width:100%;
      }

      .plancevi-pdf-container iframe{
        width:100%;
        height:100%;
        border:1px solid #dee2e6;
        border-radius:16px;
        background:#fff;
      }

      .plancevi-extra-actions{
        text-align:center;
        margin-top:14px;
      }

      @media (max-width:992px){
        .plancevi-shell{
          width:98%;
          margin:14px auto 24px auto;
        }

        .plancevi-header-actions{
          flex-direction:column;
          align-items:stretch;
        }

        .plancevi-file-pill{
          max-width:100%;
        }

        .plancevi-card-body{
          padding:10px;
        }

        .plancevi-pdf-container{
          min-height:520px;
        }
      }
    </style>

    <script>
      function setZoom(z) {
        var f = document.getElementById('pdfFrame');
        if (!f) return;
        var base = f.src.split('#')[0];
        f.src = base + '#zoom=' + encodeURIComponent(z);
      }
    </script>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            inner_html,
            evi_id=evi_id,
            original_name=evi.original_name or evi.filename,
            ext=ext,
            is_pdf=is_pdf,
            is_office=is_office,
            is_image=is_image,
            pdf_converted_name=pdf_converted_name,
            back_url=back_url,
            back_label=back_label
        ))
    )

@app.route('/plan_diseno/evidencia/convertido/<path:filename>')
@login_required
def plan_diseno_evidencia_convertido(filename):
    converted_dir = app.config.get(
        'UPLOAD_PLAN_DISENO_CONVERTED_DIR',
        os.path.join(app.root_path, 'static', 'converted_plan_diseno_evidencias')
    )

    full_path = safe_join(converted_dir, filename)
    if not full_path or not os.path.isfile(full_path):
        abort(404)

    return send_file(
        full_path,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=filename,
        conditional=True
    )

@app.route('/plan_diseno/evidencia/<int:evi_id>/delete', methods=['POST'])
@login_required
def plan_diseno_evidencia_delete(evi_id):
    evi = PlanDisenoEvidencia.query.get_or_404(evi_id)
    path = os.path.join(app.config['UPLOAD_PLAN_DISENO_DIR'], evi.filename)

    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

    plan_id = evi.registro.id if evi.registro else None

    db.session.delete(evi)
    db.session.commit()
    flash("Evidencia eliminada.", "success")

    if plan_id:
        return redirect(url_for('plan_diseno_edit', id=plan_id))
    return redirect(url_for('plan_diseno_matriz'))


# =================================================================================================================================================
#                                       Fin Módulo Plan de Concientización y Formación INGRESO DIRECTO A LA MATRIZ
# =================================================================================================================================================


# =================================================================================================================================================
#                                    Módulo Seguimiento Plan de Concientización y Formación INGRESO DIRECTO A LA MATRIZ
# =================================================================================================================================================

@app.route('/plan_cf/menu')
@login_required
def plan_cf_menu():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Seguimiento Plan de Concientización y Formación"):
        flash("No tiene permiso para acceder al Seguimiento Plan de Concientización y Formación.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('plan_cf_matriz'))

# =========================
# Obtener áreas y divisiones
# =========================
def obtener_areas_y_divisiones():
    """
    Devuelve:
      - areas: lista de áreas únicas
      - divisiones_por_area: dict { nombre_area: [div1, div2, ...] }
    """
    areas_db = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()

    areas = []
    divisiones_por_area = {}

    for a in areas_db:
        nombre_area = (a.area or '').strip()
        if not nombre_area:
            continue

        areas.append(nombre_area)
        divisiones_por_area[nombre_area] = []

        for d in (a.divisiones or []):
            nombre_div = (d.nombre_division or '').strip()
            if nombre_div and nombre_div not in divisiones_por_area[nombre_area]:
                divisiones_por_area[nombre_area].append(nombre_div)

        divisiones_por_area[nombre_area].sort(key=lambda s: s.lower())

    areas = sorted(set(areas), key=lambda s: s.lower())
    return areas, divisiones_por_area


# =========================
# Agregar Registros Seguimiento
# =========================
@app.route('/plan_cf/new', methods=['GET','POST'])
@login_required
def plan_cf_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros de seguimiento.", "danger")
        return redirect(url_for('plan_cf_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Seguimiento Plan de Concientización y Formación"):
        flash("No tiene permiso para agregar registros de seguimiento.", "danger")
        return redirect(url_for('plan_cf_matriz'))

    areas, divisiones_por_area = obtener_areas_y_divisiones()

    if request.method == 'POST':
        it = PlanCFRegistro(
            total_empleados_contratados=request.form.get('total_empleados_contratados', type=int) or 0,
            tipo_capacitacion=request.form.get('tipo_capacitacion') or '',
            nombre_capacitacion=(request.form.get('nombre_capacitacion') or '').strip(),
            objetivo_capacitacion=(request.form.get('objetivo_capacitacion') or '').strip(),
            temario=(request.form.get('temario') or '').strip(),
            fecha_programada=request.form.get('fecha_programada') or '',
            fecha_realizacion=request.form.get('fecha_realizacion') or '',
            cumplimiento_pct=request.form.get('cumplimiento_pct', type=int) or 0,
            area_participantes=request.form.get('area_participantes') or '',
            division_participantes=request.form.get('division_participantes') or '',
            competencia_entrenador=request.form.get('competencia_entrenador') or 'interno',
            quien_realizo=(request.form.get('quien_realizo') or '').strip(),
            horas_duracion=request.form.get('horas_duracion', type=int) or 0,
            indicador_realizacion=request.form.get('indicador_realizacion', type=int) or 0,
            num_asistentes=request.form.get('num_asistentes', type=int) or 0,
            num_programados=request.form.get('num_programados', type=int) or 0,
            num_evaluados=request.form.get('num_evaluados', type=int) or 0,
            num_eficaces=request.form.get('num_eficaces', type=int) or 0,
        )

        it.recalcular_indicadores()

        db.session.add(it)
        db.session.commit()
        flash("Registro agregado.", "success")
        return redirect(url_for('plan_cf_matriz'))

    html = """
    <div class="plancf-shell">

      <div class="plancf-header-card">
        <div class="plancf-header-overlay">
          <div class="plancf-header-text">
            <h3 class="plancf-title m-0">Agregar Seguimiento de Concientización</h3>
            <div class="plancf-subtitle">
              Registro de seguimiento de concientización y formación, incluyendo cobertura, eficacia, participantes, cumplimiento del programa y métricas automáticas
            </div>
          </div>
        </div>
      </div>

      <div class="plancf-header-actions">
        <a href="{{ url_for('plan_cf_matriz') }}"
           class="btn rounded-pill px-5 fw-bold plancf-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="plancf-card">
        <div class="plancf-card-body">
          <form method="post" oninput="autocalc()">
            <div class="row g-3">

              <div class="col-12">
                <div class="plancf-section-title">Información general</div>
              </div>

              <div class="col-md-2">
                <label class="form-label">Total de empleados contratados</label>
                <input type="number" class="form-control" name="total_empleados_contratados" min="0" value="0" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Tipo de capacitación</label>
                <select class="form-select" name="tipo_capacitacion" required>
                  <option value="">-- Seleccione --</option>
                  <option value="Inducción">Inducción</option>
                  <option value="Reinducción">Reinducción</option>
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre de la capacitación</label>
                <input class="form-control" name="nombre_capacitacion" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha Programada</label>
                <input type="date" class="form-control" name="fecha_programada" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha de realización</label>
                <input type="date" class="form-control" name="fecha_realizacion">
              </div>

              <div class="col-md-12">
                <label class="form-label">Objetivo de la capacitación</label>
                <textarea class="form-control" name="objetivo_capacitacion" rows="2"></textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Temario</label>
                <textarea class="form-control" name="temario" rows="2"></textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">% Cumplimiento Programa</label>
                <input type="number" class="form-control" name="cumplimiento_pct" min="0" max="100" value="0">
              </div>

              <div class="col-md-4">
                <label class="form-label">Área de colaboradores participantes</label>
                <select class="form-select"
                        name="area_participantes"
                        id="area_participantes"
                        required
                        onchange="cargarDivisiones()">
                  <option value="">-- Seleccione --</option>
                  <option value="Todas las áreas">Todas las áreas</option>
                  {% for a in areas %}
                    <option value="{{ a }}">{{ a }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">División de colaboradores participantes</label>
                <select class="form-select"
                        name="division_participantes"
                        id="division_participantes"
                        required>
                  <option value="">-- Seleccione un área primero --</option>
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Competencia del entrenador</label>
                <select class="form-select" name="competencia_entrenador">
                  <option value="interno">interno</option>
                  <option value="externo">externo</option>
                </select>
              </div>

              <div class="col-md-6">
                <label class="form-label">Quién realizó la Capacitación y/o Entrenamiento</label>
                <input class="form-control" name="quien_realizo">
              </div>

              <div class="col-md-2">
                <label class="form-label">Horas de duración</label>
                <input type="number" class="form-control" name="horas_duracion" min="0" value="0">
              </div>

              <div class="col-md-4">
                <label class="form-label">Indicador de realización (100/0)</label>
                <select class="form-select" name="indicador_realizacion">
                  <option value="100">100%</option>
                  <option value="0">0%</option>
                </select>
              </div>

              <div class="col-12">
                <div class="plancf-section-title">Métricas automáticas</div>
              </div>

              <div class="col-md-3">
                <label class="form-label">Número asistentes</label>
                <input type="number" class="form-control" name="num_asistentes" id="asist" min="0" value="0">
              </div>

              <div class="col-md-3">
                <label class="form-label">Número programados</label>
                <input type="number" class="form-control" name="num_programados" id="prog" min="0" value="0">
              </div>

              <div class="col-md-3">
                <label class="form-label">% Cobertura (auto)</label>
                <input class="form-control plancf-readonly" id="cov" value="0" readonly>
              </div>

              <div class="col-md-3">
                <label class="form-label">Número evaluados</label>
                <input type="number" class="form-control" name="num_evaluados" id="eval" min="0" value="0">
              </div>

              <div class="col-md-3">
                <label class="form-label">Número evaluaciones eficaces</label>
                <input type="number" class="form-control" name="num_eficaces" id="efi" min="0" value="0">
              </div>

              <div class="col-md-3">
                <label class="form-label">% de evaluaciones eficaces (auto)</label>
                <input class="form-control plancf-readonly" id="efi_pct" value="0" readonly>
              </div>

            </div>

            <div class="plancf-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>

              <a class="btn rounded-pill px-4 fw-bold plancf-cancel-btn"
                 href="{{ url_for('plan_cf_matriz') }}">
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

      .plancf-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      .plancf-header-card{
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

      .plancf-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .plancf-header-overlay{
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

      .plancf-header-overlay::before{
        content:"✅";
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

      .plancf-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .plancf-header-text::before{
        content:"SGSI · Cumplimiento Final";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .plancf-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .plancf-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .plancf-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .plancf-header-actions .btn,
      .plancf-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .plancf-back-btn,
      .plancf-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .plancf-back-btn:hover,
      .plancf-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .plancf-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .plancf-card-body{
        padding:18px;
      }

      .plancf-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .plancf-card .form-control,
      .plancf-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .plancf-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .plancf-card .form-control:focus,
      .plancf-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .plancf-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .plancf-readonly{
        background:#eef5ff !important;
        color:#0b4a8f !important;
        border:1px solid #d9eaff !important;
        font-weight:900;
      }

      .plancf-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
        width:100%;
      }

      .plancf-card .btn{
        font-weight:900;
      }

      @media (max-width:992px){
        .plancf-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .plancf-header-card{
          min-height:88px;
        }

        .plancf-title{
          font-size:1.20rem;
        }

        .plancf-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .plancf-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .plancf-header-overlay::before{
          margin:0;
        }

        .plancf-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .plancf-header-actions .btn,
        .plancf-bottom-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      const divisionesPorArea = {{ divisiones_por_area|tojson }};

      function cargarDivisiones(valorSeleccionado = null) {
        const areaSel = document.getElementById('area_participantes');
        const divSel = document.getElementById('division_participantes');
        const area = (areaSel.value || '').trim();

        divSel.innerHTML = '';

        if (!area) {
          divSel.innerHTML = '<option value="">-- Seleccione un área primero --</option>';
          return;
        }

        let opciones = '<option value="">-- Seleccione --</option>';
        opciones += '<option value="Todas las divisiones">Todas las divisiones</option>';

        if (area !== 'Todas las áreas') {
          const divisiones = divisionesPorArea[area] || [];
          for (const d of divisiones) {
            opciones += `<option value="${d}">${d}</option>`;
          }
        }

        divSel.innerHTML = opciones;

        if (valorSeleccionado) {
          divSel.value = valorSeleccionado;
        }
      }

      function autocalc() {
        const asist = parseInt(document.getElementById('asist').value || '0');
        const prog  = parseInt(document.getElementById('prog').value  || '0');
        const evals = parseInt(document.getElementById('eval').value  || '0');
        const efi   = parseInt(document.getElementById('efi').value   || '0');

        const cov = (prog > 0) ? Math.round(asist * 100 / prog) : 0;
        const efp = (evals > 0) ? Math.round(efi * 100 / evals) : 0;

        document.getElementById('cov').value = cov;
        document.getElementById('efi_pct').value = efp;
      }

      window.addEventListener('DOMContentLoaded', function () {
        autocalc();
        cargarDivisiones();
      });
    </script>
    """

    inner = render_template_string(
        html,
        areas=areas,
        divisiones_por_area=divisiones_por_area
    )
    return render_template_string(BASE, content=Markup(inner))

def attribute(obj, name):
    """Devuelve obj.<name> o None si no existe."""
    return getattr(obj, name, None)

# =========================
# Matriz Seguimiento
# =========================

@app.route('/plan_cf', methods=['GET'])
@login_required
def plan_cf_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Seguimiento Plan de Concientización y Formación"):
            flash("No tiene permiso para ver la Matriz de Seguimiento.", "danger")
            return redirect(url_for('capacitacion_menu'))
        read_only = False

    items = PlanCFRegistro.query.order_by(PlanCFRegistro.id.desc()).all()

    rows_html = []

    for it in items:
        tipo = escape(it.tipo_capacitacion or '—')
        nombre = escape(it.nombre_capacitacion or '—')
        fecha_programada = escape(it.fecha_programada or '—')
        quien = escape(it.quien_realizo or '—')
        asistentes = it.num_asistentes if it.num_asistentes is not None else 0
        cumplimiento = it.cumplimiento_pct if it.cumplimiento_pct is not None else 0
        cobertura = it.cobertura_pct if hasattr(it, 'cobertura_pct') and it.cobertura_pct is not None else 0
        eficaces = it.eficaces_pct if hasattr(it, 'eficaces_pct') and it.eficaces_pct is not None else 0

        acciones = [
            f'''
            <a href="{url_for('plan_cf_detalle', id=it.id)}"
               class="btn btn-info btn-sm rounded-pill plancfmat-btn-action text-white fw-bold">
              Ver detalle
            </a>
            '''
        ]

        if not read_only:
            try:
                acciones.append(
                    f'''
                    <a href="{url_for('plan_cf_edit', id=it.id)}"
                       class="btn btn-warning btn-sm rounded-pill plancfmat-btn-action fw-bold">
                      Editar
                    </a>
                    '''
                )
            except:
                pass

            try:
                acciones.append(
                    f'''
                    <a href="{url_for('plan_cf_delete', id=it.id)}"
                       class="btn btn-danger btn-sm rounded-pill plancfmat-btn-action fw-bold"
                       onclick="return confirm('¿Eliminar este registro?');">
                      Eliminar
                    </a>
                    '''
                )
            except:
                pass
        else:
            acciones.append('<span class="badge bg-secondary">Solo lectura</span>')

        rows_html.append(f"""
        <tr>
          <td>{tipo}</td>
          <td>{nombre}</td>
          <td>{fecha_programada}</td>
          <td>{quien}</td>
          <td class="text-center">{asistentes}</td>
          <td class="text-center">{cumplimiento}%</td>
          <td class="text-center">{cobertura}%</td>
          <td class="text-center">{eficaces}%</td>
          <td class="text-center plancfmat-col-acciones">
            <div class="plancfmat-actions-wrap">
              {''.join(acciones)}
            </div>
          </td>
        </tr>
        """)

    if not rows_html:
        rows_html.append("""
        <tr>
          <td colspan="9" class="text-center text-muted py-4">Sin registros</td>
        </tr>
        """)

    agregar_top = ""
    agregar_header = ""
    if not read_only:
        agregar_top = f'''
        <a href="{url_for('plan_cf_new')}"
           class="btn btn-primary rounded-pill px-5 fw-bold">
          ➕ Agregar registro
        </a>
        '''
        agregar_header = f'''
        <a href="{url_for('plan_cf_new')}"
           class="btn btn-primary rounded-pill fw-bold">
          ➕ Agregar registro
        </a>
        '''

    html = f"""
    <div class="plancfmat-shell">

      <div class="plancfmat-header-card">
        <div class="plancfmat-header-overlay">
          <div class="plancfmat-header-text">
            <h3 class="plancfmat-title m-0">Matriz Seguimiento Plan de Concientización y Formación</h3>
            <div class="plancfmat-subtitle">
              Seguimiento del programa de concientización y formación, incluyendo cobertura, eficacia, cumplimiento, participantes y métricas del proceso
            </div>
          </div>
        </div>
      </div>

      <div class="plancfmat-header-actions">
       

        {agregar_top}
      </div>

      <div class="plancfmat-card">

        <div class="plancfmat-topbar">
          <div>
            <h5 class="plancfmat-top-title mb-1">Resumen del seguimiento</h5>
            <div class="plancfmat-top-note">
              La matriz muestra los campos principales. Para consultar toda la información usa el botón <strong>Ver detalle</strong>.
            </div>
          </div>
          <div class="d-flex align-items-center gap-2 flex-wrap">
            <div class="plancfmat-counter-badge">
              Total registros: {len(items)}
            </div>

          </div>
        </div>

        <div class="plancfmat-card-body">
          <div class="table-responsive plancfmat-table-wrap">
            <table class="table table-bordered table-hover align-middle mb-0 plancfmat-table">

              <thead class="text-center">
                <tr class="plancfmat-group-row">
                  <th>Tipo</th>
                  <th>Nombre de la capacitación</th>
                  <th>Fecha programada</th>
                  <th>Quién realizó</th>
                  <th>Asistentes</th>
                  <th>% Cumplimiento</th>
                  <th>% Cobertura</th>
                  <th>% Eficaces</th>
                  <th class="plancfmat-col-acciones">Acciones</th>
                </tr>
              </thead>

              <tbody>
                {''.join(rows_html)}
              </tbody>
            </table>
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

      .plancfmat-shell{{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }}

      .plancfmat-header-card{{
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
      }}

      .plancfmat-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .plancfmat-header-overlay{{
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
      }}

      .plancfmat-header-overlay::before{{
        content:"✅";
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

      .plancfmat-header-text{{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .plancfmat-header-text::before{{
        content:"SGSI · Matriz de Cumplimiento Final";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .plancfmat-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }}

      .plancfmat-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .plancfmat-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .plancfmat-header-actions .btn{{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .plancfmat-back-btn{{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }}

      .plancfmat-back-btn:hover{{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }}

      .plancfmat-card{{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }}

      .plancfmat-topbar{{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:14px;
        padding:16px 16px 0 16px;
        flex-wrap:wrap;
      }}

      .plancfmat-top-title{{
        color:#0f172a;
        font-weight:950;
        font-size:.92rem;
      }}

      .plancfmat-top-note{{
        color:#475569;
        font-size:.78rem;
      }}

      .plancfmat-counter-badge{{
        background:linear-gradient(135deg,#0f172a,#1e3a8a);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:8px 14px;
        box-shadow:0 8px 18px rgba(0,0,0,.15);
        font-size:.78rem;
      }}

      .plancfmat-card-body{{
        padding:14px 16px 16px 16px;
      }}

      .plancfmat-table-wrap{{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }}

      .plancfmat-table{{
        min-width:1280px;
        table-layout:fixed;
        margin-bottom:0;
      }}

      .plancfmat-table thead th{{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border-color:rgba(0,0,0,.08) !important;
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal;
      }}

      .plancfmat-table th,
      .plancfmat-table td{{
        vertical-align:top;
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
      }}

      .plancfmat-table td{{
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }}

      .plancfmat-table tbody tr:nth-child(even){{
        background:#f8fbff;
      }}

      .plancfmat-table tbody tr:hover{{
        background:#eef6ff;
      }}

      .plancfmat-col-acciones{{
        width:190px !important;
        min-width:190px !important;
        text-align:center;
        vertical-align:middle !important;
      }}

      .plancfmat-actions-wrap{{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }}

      .plancfmat-btn-action,
      .plancfmat-actions-wrap .badge{{
        min-width:110px;
        max-width:125px;
        padding:4px 12px !important;
        font-size:.64rem !important;
        line-height:1.2;
        text-align:center;
        white-space:nowrap;
        border-radius:999px !important;
        font-weight:900;
      }}

      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      @media (max-width:992px){{
        .plancfmat-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .plancfmat-header-card{{
          min-height:88px;
        }}

        .plancfmat-title{{
          font-size:1.20rem;
        }}

        .plancfmat-card-body{{
          padding:12px;
        }}

        .plancfmat-topbar{{
          padding:12px 12px 0 12px;
        }}

        .plancfmat-col-acciones{{
          width:170px !important;
          min-width:170px !important;
        }}
      }}

      @media (max-width:768px){{
        .plancfmat-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .plancfmat-header-overlay::before{{
          margin:0;
        }}

        .plancfmat-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .plancfmat-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, content=Markup(html))

# =========================
# Detalle Seguimiento
# =========================
@app.route('/plan_cf/detalle/<int:id>')
@login_required
def plan_cf_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Seguimiento del Plan de Formación"):
            flash("No tiene permiso para ver el detalle del seguimiento.", "danger")
            return redirect(url_for('plan_cf_menu'))
        read_only = False

    it = PlanCFRegistro.query.get_or_404(id)
    label_by_key = dict(PLANCF_COLS)

    compact_candidates = [
        'tema',
        'actividad',
        'fecha',
        'responsable',
        'horas_duracion',
        'num_asistentes',
        'num_programados',
        'num_evaluados',
        'num_eficaces',
        'cumplimiento_pct',
        'cobertura_pct',
        'eficaces_pct',
        'indicador_realizacion'
    ]

    long_candidates = [
        'objetivo_capacitacion',
        'temario',
        'observaciones'
    ]

    compact_keys = [k for k in compact_candidates if hasattr(it, k)]
    long_keys = [k for k in long_candidates if hasattr(it, k)]

    used = set(compact_keys + long_keys)
    extra_keys = [k for k, _ in PLANCF_COLS if hasattr(it, k) and k not in used]

    percent_keys = {"cumplimiento_pct", "cobertura_pct", "eficaces_pct", "indicador_realizacion"}

    html = """
    <div class="plancfdet-shell">

      <div class="plancfdet-header-card">
        <div class="plancfdet-header-overlay">
          <div class="plancfdet-header-text">
            <h3 class="plancfdet-title m-0">Detalle del Seguimiento del Plan de Concientización y Formación</h3>
            <div class="plancfdet-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="plancfdet-header-actions">
        <a href="{{ url_for('plan_cf_matriz') }}"
           class="btn rounded-pill px-4 fw-bold plancfdet-back-btn">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('plan_cf_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="plancfdet-card">
        <div class="plancfdet-card-body">

          {% if compact_keys %}
          <div class="plancfdet-section">
            <div class="plancfdet-section-title">Información general</div>
            <div class="row g-3">
              {% for key in compact_keys %}
                <div class="col-md-3">
                  <div class="plancfdet-field plancfdet-field-compact">
                    <div class="plancfdet-label">{{ labels.get(key, key) }}</div>
                    <div class="plancfdet-value plancfdet-value-compact">
                      {% set val = it|attr(key) %}
                      {% if key in percent_keys %}
                        {{ val if val is not none else 0 }}%
                      {% else %}
                        {{ val if val is not none and val != '' else '—' }}
                      {% endif %}
                    </div>
                  </div>
                </div>
              {% endfor %}
            </div>
          </div>
          {% endif %}

          {% if extra_keys %}
          <div class="plancfdet-section">
            <div class="plancfdet-section-title">Datos complementarios</div>
            <div class="row g-3">
              {% for key in extra_keys %}
                <div class="col-md-6">
                  <div class="plancfdet-field">
                    <div class="plancfdet-label">{{ labels.get(key, key) }}</div>
                    <div class="plancfdet-value">
                      {% set val = it|attr(key) %}
                      {% if key in percent_keys %}
                        {{ val if val is not none else 0 }}%
                      {% else %}
                        {{ val if val is not none and val != '' else '—' }}
                      {% endif %}
                    </div>
                  </div>
                </div>
              {% endfor %}
            </div>
          </div>
          {% endif %}

          {% if long_keys %}
          <div class="plancfdet-section">
            <div class="plancfdet-section-title">Contenido y observaciones</div>
            <div class="row g-3">
              {% for key in long_keys %}
                <div class="col-md-12">
                  <div class="plancfdet-field">
                    <div class="plancfdet-label">{{ labels.get(key, key) }}</div>
                    <div class="plancfdet-value {% if loop.first %}plancfdet-value-lg{% endif %}">
                      {{ it|attr(key) if it|attr(key) not in [None, ''] else '—' }}
                    </div>
                  </div>
                </div>
              {% endfor %}
            </div>
          </div>
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

      .plancfdet-shell{
        width:96%;
        max-width:1250px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HEADER SGSI MODERNO (UNIFICADO)
      ========================= */
      .plancfdet-header-card{
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

      .plancfdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .plancfdet-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .plancfdet-header-overlay::before{
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
        font-size:1.4rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .plancfdet-header-text{
        max-width:1100px;
      }

      .plancfdet-header-text::before{
        content:"SGSI · Cumplimiento Final";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .plancfdet-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .plancfdet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES SUPERIORES
      ========================= */
      .plancfdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .plancfdet-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .plancfdet-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .plancfdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD PRINCIPAL (SGSI)
      ========================= */
      .plancfdet-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .plancfdet-card-body{
        padding:18px;
      }

      /* =========================
         SECCIONES
      ========================= */
      .plancfdet-section{
        margin-bottom:18px;
      }

      .plancfdet-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin-bottom:12px;
      }

      /* =========================
         CAMPOS
      ========================= */
      .plancfdet-field{
        background:#f8fafc;
        border:1px solid #dbe5f0;
        border-radius:14px;
        padding:8px 7px;
      }

      .plancfdet-label{
        font-size:.75rem;
        font-weight:900;
        color:#2563eb;
        text-transform:uppercase;
        margin-bottom:6px;
      }

      .plancfdet-value{
        color:#0b1220;
        font-size:.90rem;
        word-break:break-word;
      }

      /* =========================
         RESPONSIVE
      ========================= */
      @media (max-width:992px){
        .plancfdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .plancfdet-title{
          font-size:1.20rem;
        }

        .plancfdet-card-body{
          padding:8px 7px;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        it=it,
        read_only=read_only,
        compact_keys=compact_keys,
        extra_keys=extra_keys,
        long_keys=long_keys,
        labels=label_by_key,
        percent_keys=percent_keys
    )
    return render_template_string(BASE, content=Markup(inner))

# =========================
# Editar seguimiento
# =========================

@app.route('/plan_cf/edit/<int:id>', methods=['GET','POST'])
@login_required
def plan_cf_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Seguimiento del Plan de Formación")
    ):
        flash("No tiene permiso para editar registros de seguimiento.", "danger")
        return redirect(url_for('plan_cf_matriz'))
    
    item = PlanCFRegistro.query.get_or_404(id)
    areas, divisiones_por_area = obtener_areas_y_divisiones()

    if request.method == 'POST':
        item.nombre_capacitacion   = (request.form.get('nombre_capacitacion') or '').strip()
        item.objetivo_capacitacion = (request.form.get('objetivo_capacitacion') or '').strip()
        item.temario               = (request.form.get('temario') or '').strip()
        item.fecha_programada      = request.form.get('fecha_programada') or ''
        item.fecha_realizacion     = request.form.get('fecha_realizacion') or ''
        item.cumplimiento_pct      = request.form.get('cumplimiento_pct', type=int) or 0
        item.area_participantes     = request.form.get('area_participantes') or ''
        item.division_participantes = request.form.get('division_participantes') or ''
        item.competencia_entrenador= request.form.get('competencia_entrenador') or 'interno'
        item.quien_realizo         = (request.form.get('quien_realizo') or '').strip()
        item.horas_duracion        = request.form.get('horas_duracion', type=int) or 0
        item.indicador_realizacion = request.form.get('indicador_realizacion', type=int) or 0
        item.num_asistentes        = request.form.get('num_asistentes', type=int) or 0
        item.num_programados       = request.form.get('num_programados', type=int) or 0
        item.num_evaluados         = request.form.get('num_evaluados', type=int) or 0
        item.num_eficaces          = request.form.get('num_eficaces', type=int) or 0
        tipo_multi                 = request.form.getlist('tipo_capacitacion')
        item.total_empleados_contratados = request.form.get('total_empleados_contratados', type=int) or 0
        item.tipo_capacitacion     = request.form.get('tipo_capacitacion') or ''
        item.recalcular_indicadores()
        db.session.commit()
        flash("Cambios guardados.", "success")
        return redirect(url_for('plan_cf_matriz'))

    html = """
    <div class="plancfedit-shell">

      <!-- CABECERA -->
      <div class="plancfedit-header-card">
        <div class="plancfedit-header-overlay">
          <div class="plancfedit-header-text">
            <h3 class="plancfedit-title m-0">Editar registro — Plan de Concientización y Formación</h3>
            <div class="plancfedit-subtitle">
              Actualización del seguimiento de actividades de concientización y formación, incluyendo participantes, cobertura, eficacia y cumplimiento del programa
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="plancfedit-header-actions">
        <a href="{{ url_for('plan_cf_matriz') }}"
           class="btn rounded-pill px-5 fw-bold plancfedit-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <!-- TARJETA -->
      <div class="plancfedit-card">
        <div class="plancfedit-card-body">
          <form method="post" oninput="autocalc()">
            <div class="row g-3">

              <div class="col-12">
                <div class="plancfedit-section-title">Información general</div>
              </div>

              <div class="col-md-2">
                <label class="form-label">Total de empleados contratados</label>
                <input type="number"
                       class="form-control"
                       name="total_empleados_contratados"
                       min="0"
                       value="{{ item.total_empleados_contratados or 0 }}"
                       required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Tipo de capacitación</label>
                <select class="form-select" name="tipo_capacitacion" required>
                  <option value="">-- Seleccione --</option>
                  <option value="Inducción" {% if item.tipo_capacitacion=='Inducción' %}selected{% endif %}>Inducción</option>
                  <option value="Reinducción" {% if item.tipo_capacitacion=='Reinducción' %}selected{% endif %}>Reinducción</option>
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre de la capacitación</label>
                <input class="form-control"
                       name="nombre_capacitacion"
                       value="{{ item.nombre_capacitacion or '' }}"
                       required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha Programada</label>
                <input type="date"
                       class="form-control"
                       name="fecha_programada"
                       value="{{ item.fecha_programada or '' }}"
                       required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha de realización</label>
                <input type="date"
                       class="form-control"
                       name="fecha_realizacion"
                       value="{{ item.fecha_realizacion or '' }}">
              </div>

              <div class="col-md-12">
                <label class="form-label">Objetivo de la capacitación</label>
                <textarea class="form-control"
                          name="objetivo_capacitacion"
                          rows="2">{{ item.objetivo_capacitacion or '' }}</textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Temario</label>
                <textarea class="form-control"
                          name="temario"
                          rows="2">{{ item.temario or '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">% Cumplimiento Programa</label>
                <input type="number"
                       class="form-control"
                       name="cumplimiento_pct"
                       min="0"
                       max="100"
                       value="{{ item.cumplimiento_pct or 0 }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Área de colaboradores participantes</label>
                <select class="form-select"
                        name="area_participantes"
                        id="area_participantes"
                        required
                        onchange="cargarDivisiones()">
                  <option value="">-- Seleccione --</option>
                  <option value="Todas las áreas" {% if item.area_participantes == 'Todas las áreas' %}selected{% endif %}>Todas las áreas</option>
                  {% for a in areas %}
                    <option value="{{ a }}" {% if item.area_participantes == a %}selected{% endif %}>{{ a }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">División de colaboradores participantes</label>
                <select class="form-select"
                        name="division_participantes"
                        id="division_participantes"
                        required>
                  <option value="">-- Seleccione un área primero --</option>
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Competencia del entrenador</label>
                <select class="form-select" name="competencia_entrenador">
                  {% for opt in ['interno','externo'] %}
                    <option value="{{ opt }}" {% if item.competencia_entrenador==opt %}selected{% endif %}>{{ opt }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-6">
                <label class="form-label">Quién realizó la Capacitación y/o Entrenamiento</label>
                <input class="form-control"
                       name="quien_realizo"
                       value="{{ item.quien_realizo or '' }}">
              </div>

              <div class="col-md-2">
                <label class="form-label">Horas de duración</label>
                <input type="number"
                       class="form-control"
                       name="horas_duracion"
                       min="0"
                       value="{{ item.horas_duracion or 0 }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Indicador de realización (100/0)</label>
                <select class="form-select" name="indicador_realizacion">
                  <option value="100" {% if item.indicador_realizacion==100 %}selected{% endif %}>100%</option>
                  <option value="0" {% if item.indicador_realizacion==0 %}selected{% endif %}>0%</option>
                </select>
              </div>

              <div class="col-12">
                <div class="plancfedit-section-title">Métricas automáticas</div>
              </div>

              <div class="col-md-3">
                <label class="form-label">Número asistentes</label>
                <input type="number"
                       class="form-control"
                       name="num_asistentes"
                       id="asist"
                       min="0"
                       value="{{ item.num_asistentes or 0 }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Número programados</label>
                <input type="number"
                       class="form-control"
                       name="num_programados"
                       id="prog"
                       min="0"
                       value="{{ item.num_programados or 0 }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">% Cobertura (auto)</label>
                <input class="form-control plancfedit-readonly"
                       id="cov"
                       value="{{ item.cobertura_pct or 0 }}"
                       readonly>
              </div>

              <div class="col-md-3">
                <label class="form-label">Número evaluados</label>
                <input type="number"
                       class="form-control"
                       name="num_evaluados"
                       id="eval"
                       min="0"
                       value="{{ item.num_evaluados or 0 }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Número evaluaciones eficaces</label>
                <input type="number"
                       class="form-control"
                       name="num_eficaces"
                       id="efi"
                       min="0"
                       value="{{ item.num_eficaces or 0 }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">% de evaluaciones eficaces (auto)</label>
                <input class="form-control plancfedit-readonly"
                       id="efi_pct"
                       value="{{ item.eficaces_pct or 0 }}"
                       readonly>
              </div>

            </div>

            <div class="plancfedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>

              <a class="btn rounded-pill px-4 fw-bold plancfedit-cancel-btn"
                 href="{{ url_for('plan_cf_matriz') }}">
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

      .plancfedit-shell{
        width:96%;
        max-width:1200px;
        margin:10px auto 24px auto;
      }

      .plancfedit-header-card{
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

      .plancfedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .plancfedit-header-overlay{
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

      .plancfedit-header-overlay::before{
        content:"✏️";
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

      .plancfedit-header-text{
        max-width:1000px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .plancfedit-header-text::before{
        content:"SGSI · Edición de Cumplimiento Final";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .plancfedit-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .plancfedit-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .plancfedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .plancfedit-header-actions .btn,
      .plancfedit-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .plancfedit-back-btn,
      .plancfedit-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .plancfedit-back-btn:hover,
      .plancfedit-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .plancfedit-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .plancfedit-card-body{
        padding:18px;
      }

      .plancfedit-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .plancfedit-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .plancfedit-card .form-control,
      .plancfedit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .plancfedit-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .plancfedit-card .form-control:focus,
      .plancfedit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .plancfedit-card .input-group-text{
        border-radius:0 9px 9px 0;
        border:1px solid #d9e3f0;
        background:#eef5ff;
        color:#0b4a8f;
        font-weight:900;
      }

      .plancfedit-readonly{
        background:#eef5ff !important;
        color:#0b4a8f !important;
        border:1px solid #d9eaff !important;
        font-weight:900;
      }

      .plancfedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
        width:100%;
      }

      .plancfedit-soft-box{
        background:#eef5ff;
        border:1px solid #d9eaff;
        border-radius:14px;
        padding:12px 14px;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .plancfedit-card .btn{
        font-weight:900;
      }

      @media (max-width:992px){
        .plancfedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .plancfedit-header-card{
          min-height:88px;
        }

        .plancfedit-title{
          font-size:1.20rem;
        }

        .plancfedit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .plancfedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .plancfedit-header-overlay::before{
          margin:0;
        }

        .plancfedit-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .plancfedit-header-actions .btn,
        .plancfedit-bottom-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      const divisionesPorArea = {{ divisiones_por_area|tojson }};

      function cargarDivisiones(valorSeleccionado = null) {
        const areaSel = document.getElementById('area_participantes');
        const divSel = document.getElementById('division_participantes');
        const area = (areaSel.value || '').trim();

        divSel.innerHTML = '';

        if (!area) {
          divSel.innerHTML = '<option value="">-- Seleccione un área primero --</option>';
          return;
        }

        let opciones = '<option value="">-- Seleccione --</option>';
        opciones += '<option value="Todas las divisiones">Todas las divisiones</option>';

        if (area !== 'Todas las áreas') {
          const divisiones = divisionesPorArea[area] || [];
          for (const d of divisiones) {
            opciones += `<option value="${d}">${d}</option>`;
          }
        }

        divSel.innerHTML = opciones;

        if (valorSeleccionado) {
          divSel.value = valorSeleccionado;
        }
      }

      function autocalc() {
        const asist = parseInt(document.getElementById('asist').value || '0');
        const prog  = parseInt(document.getElementById('prog').value  || '0');
        const evals = parseInt(document.getElementById('eval').value  || '0');
        const efi   = parseInt(document.getElementById('efi').value   || '0');

        const cov = (prog > 0) ? Math.round(asist * 100 / prog) : 0;
        const efp = (evals > 0) ? Math.round(efi * 100 / evals) : 0;

        document.getElementById('cov').value = cov;
        document.getElementById('efi_pct').value = efp;
      }

      window.addEventListener('DOMContentLoaded', function () {
        autocalc();
        cargarDivisiones({{ (item.division_participantes or '')|tojson }});
      });
    </script>
    """
    inner = render_template_string(
        html,
        item=item,
        areas=areas,
        divisiones_por_area=divisiones_por_area
    )
    return render_template_string(BASE, content=Markup(inner))

# =========================
# Eliminar
# =========================

@app.route('/plan_cf/delete/<int:id>')
@login_required
def plan_cf_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Seguimiento del Plan de Formación")
    ):
        flash("No tiene permiso para eliminar registros de seguimiento.", "danger")
        return redirect(url_for('plan_cf_matriz'))
    
    it = PlanCFRegistro.query.get_or_404(id)
    db.session.delete(it)
    db.session.commit()
    flash("Registro eliminado.", "success")
    return redirect(url_for('plan_cf_matriz'))

# =================================================================================================================================================
#                                    Fin Módulo Seguimiento Plan de Concientización y Formación INGRESO DIRECTO A LA MATRIZ
# =================================================================================================================================================


# ==========================================================================================================================================
#                                                               Módulo Plan de Competencias
# ==========================================================================================================================================

# ==========================
# ENTRADA DIRECTA — PLAN DE COMPETENCIAS
# ==========================
@app.route("/plan_remediacion_competencias_menu")
@login_required
def plan_remediacion_competencias_menu():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Plan de Competencias"):
        flash("No tiene permiso para acceder al módulo de plan de competencias.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('plan_remediacion_competencias_matriz'))


# ==========================
# AGREGAR PLAN DE COMPETENCIAS
# ==========================
@app.route("/plan_remediacion_competencias/new", methods=["GET", "POST"])
@login_required
def plan_remediacion_competencias_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('plan_remediacion_competencias_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Plan de Competencias"):
        flash("No tiene permiso para agregar planes de competencias.", "danger")
        return redirect(url_for('plan_remediacion_competencias_matriz'))

    if request.method == "POST":
        rol_cargo = (request.form.get("rol_cargo") or "").strip()
        responsable = (request.form.get("responsable") or "").strip()
        competencias_requeridas = (request.form.get("competencias_requeridas") or "").strip()
        brechas_detectadas = (request.form.get("brechas_detectadas") or "").strip()
        plan_capacitacion = (request.form.get("plan_capacitacion") or "").strip()
        #observaciones = (request.form.get("observaciones") or "").strip()
        fecha_str = (request.form.get("fecha_cumplimiento") or "").strip()

        fecha_cumplimiento = None
        if fecha_str:
            try:
                fecha_cumplimiento = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Fecha de cumplimiento inválida.", "danger")
                return redirect(url_for("plan_remediacion_competencias_new"))

        if not all([rol_cargo, responsable, competencias_requeridas]):
            flash("Rol/Cargo, Responsable y Competencias Requeridas son obligatorios.", "danger")
            return redirect(url_for("plan_remediacion_competencias_new"))

        it = PlanRemediacionCompetenciaRegistro(
            rol_cargo=rol_cargo,
            responsable=responsable,
            competencias_requeridas=competencias_requeridas,
            brechas_detectadas=brechas_detectadas,
            plan_capacitacion=plan_capacitacion,
            fecha_cumplimiento=fecha_cumplimiento,
        )
        db.session.add(it)
        db.session.flush()

        files = request.files.getlist("evidencias")
        for f in files:
            if not f or not f.filename:
                continue
            if not is_allowed_pdf(f.filename):
                flash(f"Archivo no permitido (solo PDF): {f.filename}", "danger")
                continue

            store_name = unique_store_name(f.filename)
            path = os.path.join(app.config["UPLOAD_PLAN_REMEDIACION_COMP_DIR"], store_name)
            f.save(path)

            ev = PlanRemediacionCompetenciaEvidencia(
                plan=it,
                filename=store_name,
                original_name=secure_filename(f.filename),
                mime="application/pdf",
                size=os.path.getsize(path),
            )
            db.session.add(ev)

        db.session.commit()
        flash("Plan de remediación de competencias registrado.", "success")
        return redirect(url_for("plan_remediacion_competencias_matriz"))

    html = """
    <div class="plancomp-shell">

      <div class="plancomp-header-card">
        <div class="plancomp-header-overlay">
          <div class="plancomp-header-text">
            <h3 class="plancomp-title m-0">Agregar Plan de Competencias</h3>
            <div class="plancomp-subtitle">
              Registro de competencias requeridas, brechas detectadas, acciones de capacitación y evidencias asociadas al personal del SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="plancomp-header-actions">
        <a href="{{ url_for('plan_remediacion_competencias_matriz') }}"
           class="btn rounded-pill px-4 fw-bold plancomp-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="plancomp-card">
        <div class="plancomp-card-body">
          <form method="post" enctype="multipart/form-data">
            <div class="row g-3">

              <div class="col-12">
                <div class="plancomp-section-title">Información general</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Rol / Cargo</label>
                <input name="rol_cargo" class="form-control" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Responsable / Persona</label>
                <input name="responsable" class="form-control" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha de Cumplimiento</label>
                <input type="date" name="fecha_cumplimiento" class="form-control">
              </div>

              <div class="col-md-12">
                <label class="form-label">Competencias Requeridas</label>
                <textarea name="competencias_requeridas"
                          class="form-control"
                          rows="2"
                          required></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Brechas Detectadas</label>
                <textarea name="brechas_detectadas"
                          class="form-control"
                          rows="2"></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Plan de Capacitación / Acción</label>
                <textarea name="plan_capacitacion"
                          class="form-control"
                          rows="2"></textarea>
              </div>

              <div class="col-12">
                <div class="plancomp-section-title">Evidencias</div>
              </div>

              <div class="col-md-6">
                <label class="form-label">Evidencias de Competencia (PDF, varios)</label>
                <input type="file"
                       id="evidencias"
                       name="evidencias"
                       accept=".pdf"
                       multiple
                       class="form-control"
                       onchange="acumularEvidencias(this)">
                <small class="text-muted">
                  Puedes seleccionar varios a la vez o en varias rondas.
                </small>
                <div id="lista_evidencias_nuevas" class="mt-2"></div>
              </div>

            </div>

            <div class="plancomp-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>

              <a href="{{ url_for('plan_remediacion_competencias_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold plancomp-cancel-btn"
                 onclick="showLoader()">
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

      .plancomp-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .plancomp-header-card{
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

      .plancomp-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .plancomp-header-overlay{
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

      .plancomp-header-overlay::before{
        content:"✅";
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

      .plancomp-header-text{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .plancomp-header-text::before{
        content:"SGSI · Cumplimiento del Plan";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .plancomp-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .plancomp-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .plancomp-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .plancomp-header-actions .btn,
      .plancomp-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .plancomp-back-btn,
      .plancomp-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .plancomp-back-btn:hover,
      .plancomp-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .plancomp-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .plancomp-card-body{
        padding:18px;
      }

      .plancomp-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .plancomp-card .form-control,
      .plancomp-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .plancomp-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .plancomp-card .form-control:focus,
      .plancomp-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .plancomp-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .plancomp-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
        width:100%;
      }

      .plancomp-card .btn{
        font-weight:900;
      }

      @media (max-width:992px){
        .plancomp-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .plancomp-header-card{
          min-height:88px;
        }

        .plancomp-title{
          font-size:1.20rem;
        }

        .plancomp-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .plancomp-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .plancomp-header-overlay::before{
          margin:0;
        }

        .plancomp-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .plancomp-header-actions .btn,
        .plancomp-bottom-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      let evidenciasBufferDT = new DataTransfer();

      function renderListaEvidencias() {
        const cont = document.getElementById('lista_evidencias_nuevas');
        if (!cont) return;

        cont.innerHTML = '';
        if (evidenciasBufferDT.files.length === 0) {
          cont.innerHTML = '<div class="text-muted small">No hay archivos seleccionados</div>';
          return;
        }

        for (let i = 0; i < evidenciasBufferDT.files.length; i++) {
          const f = evidenciasBufferDT.files[i];
          const row = document.createElement('div');
          row.className = 'd-flex align-items-center justify-content-between mb-1';
          row.innerHTML = `
            <span class="text-truncate small" style="max-width:260px;">📎 ${f.name}</span>
            <button type="button"
                    class="btn btn-link text-danger p-0 small"
                    onclick="removeEvidenciaFromBuffer(${i})">
              🗑️
            </button>
          `;
          cont.appendChild(row);
        }
      }

      function acumularEvidencias(inputEl) {
        for (const f of inputEl.files) {
          evidenciasBufferDT.items.add(f);
        }
        inputEl.files = evidenciasBufferDT.files;
        renderListaEvidencias();
      }

      function removeEvidenciaFromBuffer(index) {
        const tmp = new DataTransfer();
        for (let i = 0; i < evidenciasBufferDT.files.length; i++) {
          if (i !== index) tmp.items.add(evidenciasBufferDT.files[i]);
        }
        evidenciasBufferDT = tmp;

        const inputEl = document.getElementById('evidencias');
        if (inputEl) inputEl.files = evidenciasBufferDT.files;
        renderListaEvidencias();
      }

      window.addEventListener('DOMContentLoaded', () => {
        renderListaEvidencias();
      });
    </script>
    """
    inner = render_template_string(html)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# MATRIZ PLAN DE COMPETENCIAS
# ==========================
@app.route("/plan_remediacion_competencias_matriz")
@login_required
def plan_remediacion_competencias_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Plan de Competencias"):
            flash("No tiene permiso para ver la matriz de plan de competencias.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    filtro_rol = (request.args.get('rol_cargo') or '').strip()
    filtro_responsable = (request.args.get('responsable') or '').strip()

    query = PlanRemediacionCompetenciaRegistro.query.options(
        selectinload(PlanRemediacionCompetenciaRegistro.evidencias)
    )

    if filtro_rol:
        query = query.filter(PlanRemediacionCompetenciaRegistro.rol_cargo == filtro_rol)

    if filtro_responsable:
        query = query.filter(PlanRemediacionCompetenciaRegistro.responsable == filtro_responsable)

    items = query.order_by(PlanRemediacionCompetenciaRegistro.id.desc()).all()

    opciones_rol = [
        x[0] for x in db.session.query(PlanRemediacionCompetenciaRegistro.rol_cargo)
        .filter(PlanRemediacionCompetenciaRegistro.rol_cargo.isnot(None))
        .filter(PlanRemediacionCompetenciaRegistro.rol_cargo != '')
        .distinct()
        .order_by(PlanRemediacionCompetenciaRegistro.rol_cargo.asc())
        .all()
    ]

    opciones_responsable = [
        x[0] for x in db.session.query(PlanRemediacionCompetenciaRegistro.responsable)
        .filter(PlanRemediacionCompetenciaRegistro.responsable.isnot(None))
        .filter(PlanRemediacionCompetenciaRegistro.responsable != '')
        .distinct()
        .order_by(PlanRemediacionCompetenciaRegistro.responsable.asc())
        .all()
    ]

    total_general = PlanRemediacionCompetenciaRegistro.query.count()
    total_filtrados = len(items)

    html = """
    <div class="plancompmat-shell">

      <div class="plancompmat-header-card">
        <div class="plancompmat-header-overlay">
          <div class="plancompmat-header-text">
            <h3 class="plancompmat-title m-0">Plan de Competencias</h3>
            <div class="plancompmat-subtitle">
              Visualización resumida de competencias requeridas, brechas detectadas, responsables y fechas de cumplimiento
            </div>
          </div>
        </div>
      </div>

      <div class="plancompmat-header-actions">

        {% if not read_only %}
        <a href="{{ url_for('plan_remediacion_competencias_new') }}"
           class="btn btn-primary rounded-pill px-4 fw-bold"
           onclick="showLoader()">
          ➕ Agregar Plan
        </a>
        {% endif %}
      </div>

      <div class="plancompmat-topbar-card">
        <div class="plancompmat-topbar-title">Resumen de competencias</div>
        <div class="plancompmat-topbar-subtitle">
          Total registros: <strong>{{ total_general }}</strong>
          &nbsp; | &nbsp;
          Mostrando: <strong>{{ total_filtrados }}</strong>
        </div>
      </div>

      <div class="plancompmat-filter-card">
        <div class="plancompmat-filter-head">Filtros de búsqueda</div>
        <div class="plancompmat-filter-body">
          <form method="get">
            <div class="row g-2 align-items-end">

              <div class="col-md-5">
                <label class="form-label plancompmat-label">Rol / Cargo</label>
                <select name="rol_cargo" class="form-select form-select-sm plancompmat-input-sm">
                  <option value="">-- Todos --</option>
                  {% for op in opciones_rol %}
                    <option value="{{ op }}" {% if filtro_rol == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-5">
                <label class="form-label plancompmat-label">Responsable</label>
                <select name="responsable" class="form-select form-select-sm plancompmat-input-sm">
                  <option value="">-- Todos --</option>
                  {% for op in opciones_responsable %}
                    <option value="{{ op }}" {% if filtro_responsable == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <div class="d-flex gap-2 plancompmat-filter-actions">
                  <button type="submit" class="btn btn-primary btn-sm rounded-pill px-3 w-100 fw-bold">
                    Filtrar
                  </button>

                  <a href="{{ url_for('plan_remediacion_competencias_matriz') }}"
                     class="btn btn-outline-secondary btn-sm rounded-pill px-3 w-100 fw-bold"
                     onclick="showLoader()">
                    Limpiar
                  </a>
                </div>
              </div>

            </div>
          </form>
        </div>
      </div>

      <div class="plancompmat-card">
        <div class="plancompmat-card-body">
          <div class="table-responsive">
            <table class="table table-hover align-middle plancompmat-table mb-0">
              <thead>
                <tr>
                  <th>Rol / Cargo</th>
                  <th>Competencias Requeridas</th>
                  <th>Brechas Detectadas</th>
                  <th>Responsable</th>
                  <th>Fecha Cumplimiento</th>
                  <th class="plancompmat-col-acciones">Acciones</th>
                </tr>
              </thead>

              <tbody>
                {% for it in items %}
                <tr>
                  <td>{{ it.rol_cargo or '—' }}</td>
                  <td>{{ it.competencias_requeridas or '—' }}</td>
                  <td>{{ it.brechas_detectadas or '—' }}</td>
                  <td>{{ it.responsable or '—' }}</td>
                  <td>{{ it.fecha_cumplimiento or '—' }}</td>

                  <td class="plancompmat-col-acciones">
                    <div class="plancompmat-actions-wrap">

                      <a href="{{ url_for('plan_remediacion_competencias_detalle', id=it.id) }}"
                         class="btn btn-info btn-sm rounded-pill plancompmat-btn-action text-white fw-bold"
                         onclick="showLoader()">
                        Ver detalle
                      </a>

                      {% if not read_only %}
                        <a href="{{ url_for('plan_remediacion_competencias_edit', id=it.id) }}"
                           class="btn btn-warning btn-sm rounded-pill plancompmat-btn-action fw-bold"
                           onclick="showLoader()">
                          Editar
                        </a>

                        <a href="{{ url_for('plan_remediacion_competencias_delete', id=it.id) }}"
                           class="btn btn-danger btn-sm rounded-pill plancompmat-btn-action fw-bold"
                           onclick="return confirm('¿Eliminar este registro del plan de competencias?');">
                          Eliminar
                        </a>
                      {% else %}
                        <span class="badge bg-secondary">Solo lectura</span>
                      {% endif %}

                    </div>
                  </td>
                </tr>
                {% endfor %}

                {% if items|length == 0 %}
                  <tr>
                    <td colspan="6" class="text-center text-muted py-4">
                      No se encontraron registros con los filtros aplicados.
                    </td>
                  </tr>
                {% endif %}
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

      .plancompmat-shell{
        width:96%;
        max-width:1600px;
        margin:10px auto 24px auto;
      }

      .plancompmat-header-card{
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

      .plancompmat-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .plancompmat-header-overlay{
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

      .plancompmat-header-overlay::before{
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
      }

      .plancompmat-header-text{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .plancompmat-header-text::before{
        content:"SGSI · Matriz de Cumplimiento del Plan";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .plancompmat-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .plancompmat-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .plancompmat-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .plancompmat-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .plancompmat-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .plancompmat-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .plancompmat-topbar-card,
      .plancompmat-filter-card,
      .plancompmat-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .plancompmat-topbar-card{
        padding:14px 16px;
        margin-bottom:12px;
      }

      .plancompmat-topbar-title{
        font-weight:950;
        font-size:.92rem;
        color:#0f172a;
      }

      .plancompmat-topbar-subtitle{
        font-size:.78rem;
        color:#475569;
      }

      .plancompmat-filter-card{
        margin-bottom:14px;
      }

      .plancompmat-filter-head{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#fff;
        font-weight:900;
        font-size:.82rem;
        padding:10px 14px;
      }

      .plancompmat-filter-body{
        padding:14px 16px;
      }

      .plancompmat-label{
        font-weight:800;
        font-size:.75rem;
        color:#25324a;
        margin-bottom:4px;
      }

      .plancompmat-input-sm{
        min-height:36px !important;
        height:36px !important;
        font-size:.78rem !important;
        border-radius:9px !important;
        padding:.25rem .6rem !important;
        border:1px solid #d9e3f0 !important;
        background:#f8fafc !important;
      }

      .plancompmat-input-sm:focus{
        border-color:#3f86d6 !important;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff !important;
      }

      .plancompmat-filter-actions .btn{
        border-radius:10px !important;
        min-height:36px;
        padding:7px 18px !important;
        font-size:.78rem;
        font-weight:900;
      }

      .plancompmat-card-body{
        padding:12px 16px 16px 16px;
      }

      .plancompmat-table-wrap,
      .table-responsive{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .plancompmat-table{
        min-width:1300px;
        table-layout:fixed;
        margin-bottom:0;
      }

      .plancompmat-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border-color:rgba(0,0,0,.08);
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal;
      }

      .plancompmat-table th,
      .plancompmat-table td{
        vertical-align:top;
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .plancompmat-table td{
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .plancompmat-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .plancompmat-table tbody tr:hover{
        background:#eef6ff;
      }

      .plancompmat-col-acciones{
        width:180px !important;
        min-width:180px !important;
        text-align:center;
        vertical-align:middle !important;
      }

      .plancompmat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .plancompmat-btn-action{
        min-width:110px;
        max-width:125px;
        padding:4px 12px !important;
        font-size:.64rem !important;
        line-height:1.2;
        text-align:center;
        white-space:nowrap;
        border-radius:999px !important;
        font-weight:900;
      }

      @media (max-width:992px){
        .plancompmat-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .plancompmat-header-card{
          min-height:88px;
        }

        .plancompmat-title{
          font-size:1.20rem;
        }

        .plancompmat-card-body,
        .plancompmat-filter-body{
          padding:12px;
        }

        .plancompmat-col-acciones{
          width:165px !important;
          min-width:165px !important;
        }
      }

      @media (max-width:768px){
        .plancompmat-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .plancompmat-header-overlay::before{
          margin:0;
        }

        .plancompmat-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .plancompmat-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        filtro_rol=filtro_rol,
        filtro_responsable=filtro_responsable,
        opciones_rol=opciones_rol,
        opciones_responsable=opciones_responsable,
        total_general=total_general,
        total_filtrados=total_filtrados
    )
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# DETALLE PLAN DE COMPETENCIAS
# ==========================
@app.route("/plan_remediacion_competencias/detalle/<int:id>")
@login_required
def plan_remediacion_competencias_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Plan de Competencias"):
            flash("No tiene permiso para ver el detalle del plan de competencias.", "danger")
            return redirect(url_for('plan_remediacion_competencias_matriz'))
        read_only = False

    it = (
        PlanRemediacionCompetenciaRegistro.query
        .options(selectinload(PlanRemediacionCompetenciaRegistro.evidencias))
        .get_or_404(id)
    )

    html = """
    <div class="plancompdet-shell">

      <div class="plancompdet-header-card">
        <div class="plancompdet-header-overlay">
          <div class="plancompdet-header-text">
            <h3 class="plancompdet-title m-0">Detalle del Plan de Competencias</h3>
            <div class="plancompdet-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="plancompdet-header-actions">
        <a href="{{ url_for('plan_remediacion_competencias_matriz') }}"
           class="btn rounded-pill px-4 fw-bold plancompdet-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('plan_remediacion_competencias_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold"
             onclick="showLoader()">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="plancompdet-card">
        <div class="plancompdet-card-body">

          <div class="row g-3">
            <div class="col-12">
              <div class="plancompdet-section-title">Información general</div>
            </div>

            <div class="col-md-4"><div class="plancompdet-block"><div class="plancompdet-label">Rol / Cargo</div><div class="plancompdet-value">{{ it.rol_cargo or '—' }}</div></div></div>
            <div class="col-md-4"><div class="plancompdet-block"><div class="plancompdet-label">Responsable</div><div class="plancompdet-value">{{ it.responsable or '—' }}</div></div></div>
            <div class="col-md-4"><div class="plancompdet-block"><div class="plancompdet-label">Fecha cumplimiento</div><div class="plancompdet-value">{{ it.fecha_cumplimiento or '—' }}</div></div></div>

            <div class="col-12">
              <div class="plancompdet-section-title">Competencias, brechas y plan de acción</div>
            </div>

            <div class="col-12"><div class="plancompdet-block"><div class="plancompdet-label">Competencias Requeridas</div><div class="plancompdet-value">{{ it.competencias_requeridas or '—' }}</div></div></div>
            <div class="col-12"><div class="plancompdet-block"><div class="plancompdet-label">Brechas Detectadas</div><div class="plancompdet-value">{{ it.brechas_detectadas or '—' }}</div></div></div>
            <div class="col-12"><div class="plancompdet-block"><div class="plancompdet-label">Plan de Capacitación / Acción</div><div class="plancompdet-value">{{ it.plan_capacitacion or '—' }}</div></div></div>
            
            <div class="col-12">
              <div class="plancompdet-section-title">Evidencias</div>
            </div>

            <div class="col-12">
              {% if it.evidencias %}
                <div class="row g-3">
                  {% for ev in it.evidencias %}
                  <div class="col-md-6">
                    <div class="plancompdet-file-card">
                      <div class="plancompdet-file-meta">
                        <div class="plancompdet-file-label">Archivo</div>
                        <a class="plancompdet-file-name"
                           href="{{ url_for('plan_remediacion_competencias_evidencia_view', evi_id=ev.id, next='plan_remediacion_competencias_detalle', reg_id=it.id) }}">
                          {{ ev.original_name or ev.filename }}
                        </a>
                        <div class="plancompdet-file-size">
                          {{ (ev.size / 1024)|round(1) if ev.size else 0 }} KB
                        </div>
                      </div>
                    </div>
                  </div>
                  {% endfor %}
                </div>
              {% else %}
                <div class="plancompdet-empty-box">
                  No hay evidencias cargadas.
                </div>
              {% endif %}
            </div>
          </div>

          <div class="plancompdet-bottom-actions">
            <a href="{{ url_for('plan_remediacion_competencias_matriz') }}"
               class="btn rounded-pill px-4 fw-bold plancompdet-cancel-btn"
               onclick="showLoader()">
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

      .plancompdet-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .plancompdet-header-card{
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

      .plancompdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .plancompdet-header-overlay{
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

      .plancompdet-header-overlay::before{
        content:"✅";
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

      .plancompdet-header-text{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .plancompdet-header-text::before{
        content:"SGSI · Detalle de Cumplimiento del Plan";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .plancompdet-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .plancompdet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .plancompdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .plancompdet-header-actions .btn,
      .plancompdet-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .plancompdet-back-btn,
      .plancompdet-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .plancompdet-back-btn:hover,
      .plancompdet-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .plancompdet-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .plancompdet-card-body{
        padding:18px;
      }

      .plancompdet-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .plancompdet-block{
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%) !important;
        border:1px solid #dbe6f4 !important;
        border-radius:14px !important;
        box-shadow:0 6px 14px rgba(15,23,42,.08);
        padding:14px 16px;
        margin-bottom:12px;
      }

      .plancompdet-label{
        font-weight:900;
        font-size:.72rem;
        color:#0b4a8f;
        margin-bottom:4px;
        text-transform:uppercase;
        letter-spacing:.35px;
      }

      .plancompdet-value{
        color:#101827;
        font-size:.84rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .plancompdet-file-card{
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px 14px;
        box-shadow:0 6px 14px rgba(15,23,42,.08);
      }

      .plancompdet-file-meta{
        min-width:0;
      }

      .plancompdet-file-label{
        font-size:.70rem;
        color:#475569;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
      }

      .plancompdet-file-name{
        display:block;
        font-size:.82rem;
        font-weight:900;
        color:#1d4ed8;
        text-decoration:none;
        word-break:break-word;
        margin-top:2px;
      }

      .plancompdet-file-name:hover{
        text-decoration:underline;
      }

      .plancompdet-file-size{
        font-size:.70rem;
        color:#475569;
        margin-top:2px;
        font-weight:700;
      }

      .plancompdet-empty-box{
        background:#f8fbff;
        border:1px dashed #b8cce8;
        border-radius:14px;
        padding:16px;
        text-align:center;
        color:#475569;
        font-size:.82rem;
        font-weight:800;
      }

      .plancompdet-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
      }

      @media (max-width:992px){
        .plancompdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .plancompdet-header-card{
          min-height:88px;
        }

        .plancompdet-title{
          font-size:1.20rem;
        }

        .plancompdet-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .plancompdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .plancompdet-header-overlay::before{
          margin:0;
        }

        .plancompdet-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .plancompdet-header-actions .btn,
        .plancompdet-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, it=it, read_only=read_only)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# EDITAR PLAN DE COMPETENCIAS
# ==========================
@app.route("/plan_remediacion_competencias/edit/<int:id>", methods=["GET", "POST"])
@login_required
def plan_remediacion_competencias_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede editar registros.", "danger")
        return redirect(url_for('plan_remediacion_competencias_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Plan de Competencias"):
        flash("No tiene permiso para editar planes de competencias.", "danger")
        return redirect(url_for('plan_remediacion_competencias_matriz'))

    item = (
        PlanRemediacionCompetenciaRegistro.query
        .options(selectinload(PlanRemediacionCompetenciaRegistro.evidencias))
        .get_or_404(id)
    )

    if request.method == "POST":
        rol_cargo = (request.form.get("rol_cargo") or "").strip()
        responsable = (request.form.get("responsable") or "").strip()
        competencias_requeridas = (request.form.get("competencias_requeridas") or "").strip()
        brechas_detectadas = (request.form.get("brechas_detectadas") or "").strip()
        plan_capacitacion = (request.form.get("plan_capacitacion") or "").strip()
        observaciones = (request.form.get("observaciones") or "").strip()
        fecha_str = (request.form.get("fecha_cumplimiento") or "").strip()

        fecha_cumplimiento = None
        if fecha_str:
            try:
                fecha_cumplimiento = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Fecha de cumplimiento inválida.", "danger")
                return redirect(url_for("plan_remediacion_competencias_edit", id=id))

        if not all([rol_cargo, responsable, competencias_requeridas]):
            flash("Rol/Cargo, Responsable y Competencias Requeridas son obligatorios.", "danger")
            return redirect(url_for("plan_remediacion_competencias_edit", id=id))

        item.rol_cargo = rol_cargo
        item.responsable = responsable
        item.competencias_requeridas = competencias_requeridas
        item.brechas_detectadas = brechas_detectadas
        item.plan_capacitacion = plan_capacitacion
        item.fecha_cumplimiento = fecha_cumplimiento

        files = request.files.getlist("evidencias")
        for f in files:
            if not f or not f.filename:
                continue
            if not is_allowed_pdf(f.filename):
                flash(f"Archivo no permitido (solo PDF): {f.filename}", "danger")
                continue

            store_name = unique_store_name(f.filename)
            path = os.path.join(app.config["UPLOAD_PLAN_REMEDIACION_COMP_DIR"], store_name)
            f.save(path)

            ev = PlanRemediacionCompetenciaEvidencia(
                plan=item,
                filename=store_name,
                original_name=secure_filename(f.filename),
                mime="application/pdf",
                size=os.path.getsize(path),
            )
            db.session.add(ev)

        db.session.commit()
        flash("Plan de competencias actualizado correctamente.", "success")
        return redirect(url_for("plan_remediacion_competencias_matriz"))

    html = """
    <div class="plancompedit-shell">

      <div class="plancompedit-header-card">
        <div class="plancompedit-header-overlay">
          <div class="plancompedit-header-text">
            <h3 class="plancompedit-title m-0">Editar Plan de Competencias</h3>
            <div class="plancompedit-subtitle">
              Actualización de competencias requeridas, brechas detectadas, acciones de capacitación y evidencias asociadas al personal del SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="plancompedit-header-actions">
        <a href="{{ url_for('plan_remediacion_competencias_matriz') }}"
           class="btn rounded-pill px-4 fw-bold plancompedit-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="plancompedit-card">
        <div class="plancompedit-card-body">

          <form id="formEditarPlanCompetencias" method="post" enctype="multipart/form-data">
            <div class="row g-3">

              <div class="col-12">
                <div class="plancompedit-section-title">Información general</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Rol / Cargo</label>
                <input name="rol_cargo" class="form-control" value="{{ item.rol_cargo or '' }}" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Responsable / Persona</label>
                <input name="responsable" class="form-control" value="{{ item.responsable or '' }}" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha de Cumplimiento</label>
                <input type="date" name="fecha_cumplimiento" class="form-control"
                       value="{{ item.fecha_cumplimiento.strftime('%Y-%m-%d') if item.fecha_cumplimiento else '' }}">
              </div>

              <div class="col-md-12">
                <label class="form-label">Competencias Requeridas</label>
                <textarea name="competencias_requeridas"
                          class="form-control"
                          rows="2"
                          required>{{ item.competencias_requeridas or '' }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Brechas Detectadas</label>
                <textarea name="brechas_detectadas"
                          class="form-control"
                          rows="2">{{ item.brechas_detectadas or '' }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Plan de Capacitación / Acción</label>
                <textarea name="plan_capacitacion"
                          class="form-control"
                          rows="2">{{ item.plan_capacitacion or '' }}</textarea>
              </div>

              <div class="col-12">
                <div class="plancompedit-section-title">Evidencias</div>
              </div>

              <div class="col-md-6">
                <label class="form-label">Agregar nuevas evidencias (PDF, varios)</label>
                <input type="file"
                       id="evidencias"
                       name="evidencias"
                       accept=".pdf"
                       multiple
                       class="form-control"
                       onchange="acumularEvidenciasEdit(this)">
                <small class="text-muted">Puedes agregar varios archivos nuevos.</small>
                <div id="lista_evidencias_nuevas" class="mt-2"></div>
              </div>

              <div class="col-12">
                <label class="form-label">Evidencias existentes</label>
                {% if item.evidencias %}
                  <div class="row g-3">
                    {% for ev in item.evidencias %}
                    <div class="col-md-6">
                      <div class="plancompedit-file-card">
                        <div class="plancompedit-file-meta">
                          <div class="plancompedit-file-label">Archivo</div>
                          <a class="plancompedit-file-name"
                             href="{{ url_for('plan_remediacion_competencias_evidencia_view', evi_id=ev.id, next='plan_remediacion_competencias_edit', reg_id=item.id) }}">
                            {{ ev.original_name or ev.filename }}
                          </a>
                          <div class="plancompedit-file-size">
                            {{ (ev.size / 1024)|round(1) if ev.size else 0 }} KB
                          </div>
                        </div>

                        <button type="submit"
                                class="btn btn-sm btn-danger rounded-pill"
                                formaction="{{ url_for('plan_remediacion_competencias_evidencia_delete', evi_id=ev.id) }}"
                                formmethod="post"
                                formenctype="application/x-www-form-urlencoded"
                                onclick="return confirm('¿Eliminar esta evidencia?');">
                          Eliminar
                        </button>
                      </div>
                    </div>
                    {% endfor %}
                  </div>
                {% else %}
                  <div class="plancompedit-empty-box">No hay evidencias cargadas.</div>
                {% endif %}
              </div>

            </div>

            <div class="plancompedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>

              <a href="{{ url_for('plan_remediacion_competencias_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold plancompedit-cancel-btn"
                 onclick="showLoader()">
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

      .plancompedit-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .plancompedit-header-card{
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

      .plancompedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .plancompedit-header-overlay{
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

      .plancompedit-header-overlay::before{
        content:"✏️";
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

      .plancompedit-header-text{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .plancompedit-header-text::before{
        content:"SGSI · Edición de Cumplimiento del Plan";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .plancompedit-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .plancompedit-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .plancompedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .plancompedit-header-actions .btn,
      .plancompedit-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .plancompedit-back-btn,
      .plancompedit-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .plancompedit-back-btn:hover,
      .plancompedit-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .plancompedit-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .plancompedit-card-body{
        padding:18px;
      }

      .plancompedit-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .plancompedit-card .form-control,
      .plancompedit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .plancompedit-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .plancompedit-card .form-control:focus,
      .plancompedit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .plancompedit-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .plancompedit-file-card{
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px 14px;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
        box-shadow:0 6px 14px rgba(15,23,42,.08);
      }

      .plancompedit-file-meta{
        min-width:0;
      }

      .plancompedit-file-label{
        font-size:.70rem;
        color:#475569;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
      }

      .plancompedit-file-name{
        display:block;
        font-size:.82rem;
        font-weight:900;
        color:#1d4ed8;
        text-decoration:none;
        word-break:break-word;
        margin-top:2px;
      }

      .plancompedit-file-name:hover{
        text-decoration:underline;
      }

      .plancompedit-file-size{
        font-size:.70rem;
        color:#475569;
        margin-top:2px;
        font-weight:700;
      }

      .plancompedit-empty-box{
        background:#f8fbff;
        border:1px dashed #b8cce8;
        border-radius:14px;
        padding:16px;
        text-align:center;
        color:#475569;
        font-size:.82rem;
        font-weight:800;
      }

      .plancompedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
        width:100%;
      }

      .plancompedit-card .btn{
        font-weight:900;
      }

      @media (max-width:992px){
        .plancompedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .plancompedit-header-card{
          min-height:88px;
        }

        .plancompedit-title{
          font-size:1.20rem;
        }

        .plancompedit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .plancompedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .plancompedit-header-overlay::before{
          margin:0;
        }

        .plancompedit-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .plancompedit-header-actions .btn,
        .plancompedit-bottom-actions .btn{
          width:100%;
        }

        .plancompedit-file-card{
          align-items:flex-start;
          flex-direction:column;
        }
      }
    </style>

    <script>
      let evidenciasBufferDTEdit = new DataTransfer();

      function renderListaEvidenciasEdit() {
        const cont = document.getElementById('lista_evidencias_nuevas');
        if (!cont) return;

        cont.innerHTML = '';
        if (evidenciasBufferDTEdit.files.length === 0) {
          cont.innerHTML = '<div class="text-muted small">No hay archivos nuevos seleccionados</div>';
          return;
        }

        for (let i = 0; i < evidenciasBufferDTEdit.files.length; i++) {
          const f = evidenciasBufferDTEdit.files[i];
          const row = document.createElement('div');
          row.className = 'd-flex align-items-center justify-content-between mb-1';
          row.innerHTML = `
            <span class="text-truncate small" style="max-width:260px;">📎 ${f.name}</span>
            <button type="button"
                    class="btn btn-link text-danger p-0 small"
                    onclick="removeEvidenciaFromBufferEdit(${i})">
              🗑️
            </button>
          `;
          cont.appendChild(row);
        }
      }

      function acumularEvidenciasEdit(inputEl) {
        const existentes = Array.from(evidenciasBufferDTEdit.files).map(f => f.name + "|" + f.size);

        for (const f of inputEl.files) {
          const key = f.name + "|" + f.size;
          if (!existentes.includes(key)) {
            evidenciasBufferDTEdit.items.add(f);
          }
        }

        inputEl.files = evidenciasBufferDTEdit.files;
        renderListaEvidenciasEdit();
      }

      function removeEvidenciaFromBufferEdit(index) {
        const tmp = new DataTransfer();
        for (let i = 0; i < evidenciasBufferDTEdit.files.length; i++) {
          if (i !== index) tmp.items.add(evidenciasBufferDTEdit.files[i]);
        }
        evidenciasBufferDTEdit = tmp;

        const inputEl = document.getElementById('evidencias');
        if (inputEl) inputEl.files = evidenciasBufferDTEdit.files;
        renderListaEvidenciasEdit();
      }

      window.addEventListener('DOMContentLoaded', () => {
        renderListaEvidenciasEdit();
      });
    </script>
    """
    inner = render_template_string(html, item=item)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# EVIDENCIA - ARCHIVO REAL
# ==========================
@app.route("/plan_remediacion_competencias/evidencia/<int:evi_id>/file")
@login_required
def plan_remediacion_competencias_evidencia_file(evi_id):
    ev = PlanRemediacionCompetenciaEvidencia.query.get_or_404(evi_id)
    path = os.path.join(app.config["UPLOAD_PLAN_REMEDIACION_COMP_DIR"], ev.filename)

    if not os.path.isfile(path):
        abort(404)

    return send_file(
        path,
        mimetype=ev.mime or "application/pdf",
        as_attachment=False,
        download_name=ev.original_name or ev.filename,
        conditional=True
    )


# ==========================
# EVIDENCIA - VISOR
# ==========================
@app.route("/plan_remediacion_competencias/evidencia/<int:evi_id>/view")
@login_required
def plan_remediacion_competencias_evidencia_view(evi_id):
    ev = PlanRemediacionCompetenciaEvidencia.query.get_or_404(evi_id)

    path = os.path.join(app.config["UPLOAD_PLAN_REMEDIACION_COMP_DIR"], ev.filename)
    if not os.path.isfile(path):
        abort(404)

    ext = os.path.splitext(ev.filename or "")[1].lower()
    is_pdf = ext == ".pdf"
    is_office = ext in {".doc", ".docx", ".xls", ".xlsx"}
    is_image = ext in {".png", ".jpg", ".jpeg", ".webp", ".gif"}

    next_ep = request.args.get("next")
    reg_id = request.args.get("reg_id", type=int)

    if next_ep == "plan_remediacion_competencias_detalle" and reg_id:
        back_url = url_for("plan_remediacion_competencias_detalle", id=reg_id)
        back_label = "⬅ Volver al Detalle"
    elif next_ep == "plan_remediacion_competencias_edit" and reg_id:
        back_url = url_for("plan_remediacion_competencias_edit", id=reg_id)
        back_label = "⬅ Volver a Edición"
    else:
        back_url = url_for("plan_remediacion_competencias_matriz")
        back_label = "⬅ Volver a la Matriz"

    pdf_converted_name = None
    if is_office:
        try:
            converted_dir = app.config.get(
                "UPLOAD_PLAN_REMEDIACION_COMP_CONVERTED_DIR",
                os.path.join(app.root_path, "static", "converted_plan_remediacion_comp_evidencias")
            )
            os.makedirs(converted_dir, exist_ok=True)

            pdf_converted_path = ensure_pdf_from_office(path, output_dir=converted_dir)

            if pdf_converted_path and os.path.isfile(pdf_converted_path):
                pdf_converted_name = os.path.basename(pdf_converted_path)
        except Exception:
            pdf_converted_name = None

    inner_html = """
    <div class="plancompevi-shell">

      <div class="plancompevi-header-actions">
        <a href="{{ back_url }}"
           class="btn rounded-pill px-4 py-2 fw-bold plancompevi-back-btn">
          {{ back_label }}
        </a>

        <div class="plancompevi-file-pill" title="{{ original_name }}">
          📎 {{ original_name }}
        </div>
      </div>

      <div class="plancompevi-card">
        <div class="plancompevi-card-body">

          {% if is_pdf %}
            <iframe
              src="{{ url_for('plan_remediacion_competencias_evidencia_file', evi_id=evi_id) }}"
              class="plancompevi-frame"
              title="Visor PDF">
            </iframe>

          {% elif pdf_converted_name %}
            <iframe
              src="{{ url_for('static', filename='converted_plan_remediacion_comp_evidencias/' ~ pdf_converted_name) }}"
              class="plancompevi-frame"
              title="Visor PDF convertido">
            </iframe>

          {% elif is_image %}
            <div class="text-center">
              <img
                src="{{ url_for('plan_remediacion_competencias_evidencia_file', evi_id=evi_id) }}"
                class="img-fluid rounded shadow-sm"
                alt="{{ original_name }}">
            </div>

          {% else %}
            <div class="alert alert-warning mb-0">
              No se pudo mostrar una vista previa del archivo. Puedes abrirlo directamente:
              <a href="{{ url_for('plan_remediacion_competencias_evidencia_file', evi_id=evi_id) }}" target="_blank">
                abrir archivo
              </a>
            </div>
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

      .plancompevi-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 30px auto;
      }

      .plancompevi-header-actions{
        display:flex;
        justify-content:center;
        align-items:center;
        gap:12px;
        flex-wrap:wrap;
        margin-bottom:16px;
      }

      .plancompevi-back-btn{
        background:#ffffff;
        color:#000000;
        border:2px solid #ffffff;
        box-shadow:0 4px 10px rgba(0,0,0,.10);
      }

      .plancompevi-back-btn:hover{
        background:#f3f4f6;
        color:#000000;
        border-color:#f3f4f6;
      }

      .plancompevi-file-pill{
        background:#3f86d6;
        color:#fff;
        border-radius:999px;
        padding:10px 16px;
        font-weight:700;
        max-width:520px;
        overflow:hidden;
        text-overflow:ellipsis;
        white-space:nowrap;
        box-shadow:0 4px 10px rgba(0,0,0,.10);
      }

      .plancompevi-card{
        background:rgba(248,252,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(6px);
        box-shadow:0 10px 24px rgba(0,0,0,.18);
        overflow:hidden;
      }

      .plancompevi-card-body{
        padding:16px;
      }

      .plancompevi-frame{
        width:100%;
        height:78vh;
        border:none;
        border-radius:12px;
        background:#fff;
      }
    </style>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            inner_html,
            back_url=back_url,
            back_label=back_label,
            evi_id=evi_id,
            original_name=ev.original_name or ev.filename,
            is_pdf=is_pdf,
            is_image=is_image,
            pdf_converted_name=pdf_converted_name
        ))
    )


# ==========================
# ELIMINAR PLAN DE COMPETENCIAS
# ==========================
@app.route("/plan_remediacion_competencias/delete/<int:id>")
@login_required
def plan_remediacion_competencias_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Plan de Competencias")
    ):
        flash("No tiene permiso para eliminar planes de competencias.", "danger")
        return redirect(url_for('plan_remediacion_competencias_matriz'))

    item = PlanRemediacionCompetenciaRegistro.query.get_or_404(id)

    for ev in item.evidencias:
        try:
            path = os.path.join(app.config["UPLOAD_PLAN_REMEDIACION_COMP_DIR"], ev.filename)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    db.session.delete(item)
    db.session.commit()
    flash("Registro eliminado correctamente.", "success")
    return redirect(url_for("plan_remediacion_competencias_matriz"))


# ==========================
# ELIMINAR EVIDENCIA INDIVIDUAL
# ==========================
@app.route("/plan_remediacion_competencias/evidencia/<int:evi_id>/delete", methods=["POST"])
@login_required
def plan_remediacion_competencias_evidencia_delete(evi_id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Plan de Competencias")
    ):
        flash("No tiene permiso para eliminar evidencias.", "danger")
        return redirect(url_for('plan_remediacion_competencias_matriz'))

    ev = PlanRemediacionCompetenciaEvidencia.query.get_or_404(evi_id)
    plan_id = ev.plan_id

    try:
        path = os.path.join(app.config["UPLOAD_PLAN_REMEDIACION_COMP_DIR"], ev.filename)
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

    db.session.delete(ev)
    db.session.commit()
    flash("Evidencia eliminada correctamente.", "success")
    return redirect(url_for("plan_remediacion_competencias_edit", id=plan_id))


# ==========================================================================================================================================
#                                                           Fin Módulo Plan de Competencias
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                       Módulo de Cuestionarios Proponentes
# ==========================================================================================================================================

# =================================================
# Utilidad (IA y Excel) cuestionario de proveedores
# =================================================

ALLOWED_EXTENSIONS_EXCEL = {"xls", "xlsx"}

def allowed_file_excel(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS_EXCEL


def leer_cuestionario_excel(file_storage) -> str:
    """
    Lee el Excel del cuestionario de proveedores y construye un texto:
    Referencia: X.X
    Pregunta: ...
    Respuesta: ...

    Se adapta al formato del archivo que me enviaste.
    """
    # Leemos el archivo en memoria
    in_memory_file = io.BytesIO(file_storage.read())
    # Muy importante: volvemos el puntero al inicio para poder reutilizar el archivo después
    file_storage.seek(0)

    # En tu archivo, el 'header' útil empieza en la fila 2 (índice 1)
    # Mantener las respuestas literales: por defecto pandas interpreta
    # "N/A" y "NA" como NaN y altera el resumen, el texto IA y el puntaje.
    df = pd.read_excel(in_memory_file, header=1, keep_default_na=False)

    # 1) Intento directo por nombre de columna (por si en el futuro cambias el formato)
    posibles_preg = ["Pregunta", "PREGUNTA", "pregunta"]
    posibles_resp = ["Respuesta", "RESPUESTA", "respuesta"]

    col_preg = next((c for c in df.columns if c in posibles_preg), None)
    col_resp = next((c for c in df.columns if c in posibles_resp), None)

    # 2) Si no encuentra, buscamos dentro de las primeras filas
    if col_preg is None or col_resp is None:
        for col in df.columns:
            valores = df[col].astype(str).str.lower()
            # miramos solo las primeras filas, donde viene "Pregunta" / "Respuesta"
            if col_preg is None and any("pregunta" in v for v in valores.head(3)):
                col_preg = col
            if col_resp is None and any("respuesta" in v for v in valores.head(3)):
                col_resp = col

    if col_preg is None or col_resp is None:
        raise ValueError("No se pudieron detectar las columnas de Pregunta / Respuesta en el Excel.")

    # Quitamos la fila que contiene los encabezados "Pregunta"/"Respuesta"
    df_limpio = df.copy()
    df_limpio = df_limpio[df_limpio[col_preg].astype(str).str.lower() != "pregunta"]
    df_limpio = df_limpio[df_limpio[col_resp].notna()]

    texto = ""
    for _, row in df_limpio.iterrows():
        pregunta = str(row[col_preg]).strip()
        respuesta = str(row[col_resp]).strip()

        if not pregunta or pregunta.lower() == "nan":
            continue
        if not respuesta or respuesta.lower() == "nan":
            continue

        # Intentamos tomar la referencia (columna 0)
        ref = ""
        primera_col = df_limpio.columns[0]
        ref_val = str(row[primera_col]).strip()
        if ref_val and ref_val.lower() not in ("referencia", "nan"):
            ref = ref_val

        if ref:
            texto += f"Referencia: {ref}\n"
        texto += f"Pregunta: {pregunta}\nRespuesta: {respuesta}\n\n"

    return texto

def _normalizar_respuesta(valor: str) -> str:
    """
    Normaliza textos tipo 'Sí', 'SI', 'N/A', 'Parcialmente', etc.
    """
    if valor is None:
        return ""
    if not isinstance(valor, str):
        valor = str(valor)

    valor = valor.strip()
    if not valor:
        return ""

    # quitar acentos
    valor = ''.join(c for c in unicodedata.normalize("NFD", valor) if unicodedata.category(c) != "Mn")
    return valor.lower()


def calcular_puntaje_desde_excel_bytes(contenido_excel: bytes) -> tuple[float, str]:
    """
    Lee el Excel (binario) del cuestionario y calcula el puntaje según la regla:
    - Sí = 100
    - N/A = 100
    - Parcialmente / En desarrollo = 50
    - No = 0

    Devuelve (puntaje_0_100, explicacion_texto).
    """
    in_memory_file = io.BytesIO(contenido_excel)
    # Mantener las respuestas literales: por defecto pandas interpreta
    # "N/A" y "NA" como NaN y altera el resumen, el texto IA y el puntaje.
    df = pd.read_excel(in_memory_file, header=1, keep_default_na=False)

    # Detectar columna de respuestas igual que en leer_cuestionario_excel
    posibles_resp = ["Respuesta", "RESPUESTA", "respuesta"]
    col_resp = next((c for c in df.columns if c in posibles_resp), None)

    if col_resp is None:
        # Buscar dentro de las primeras filas si aparece la palabra "respuesta"
        for col in df.columns:
            valores = df[col].astype(str).str.lower()
            if any("respuesta" in v for v in valores.head(3)):
                col_resp = col
                break

    if col_resp is None:
        raise ValueError("No se pudo detectar la columna de Respuesta en el Excel.")

    # Nos quedamos solo con filas que tengan algo en la respuesta
    df_limpio = df.copy()
    df_limpio = df_limpio[df_limpio[col_resp].notna()]

    valores_numericos = []
    conteo = {
        "si": 0,
        "na": 0,
        "parcial": 0,
        "no": 0,
        "otros": 0,
    }

    for _, row in df_limpio.iterrows():
        resp_raw = row[col_resp]
        resp_norm = _normalizar_respuesta(resp_raw)

        if not resp_norm or resp_norm == "nan":
            continue

        # Mapeo de respuestas
        if resp_norm in ("si", "s", "yes"):
            valores_numericos.append(1.0)
            conteo["si"] += 1
        elif "n/a" in resp_norm or resp_norm in ("na", "n.a", "n.a.", "no aplica"):
            valores_numericos.append(1.0)
            conteo["na"] += 1
        elif "parcial" in resp_norm or "desarrollo" in resp_norm:
            valores_numericos.append(0.5)
            conteo["parcial"] += 1
        elif resp_norm == "no":
            valores_numericos.append(0.0)
            conteo["no"] += 1
        else:
            # Si hay otros valores raros, los contamos pero no suman
            conteo["otros"] += 1

    if not valores_numericos:
        raise ValueError("No se encontraron respuestas válidas para calcular el puntaje.")

    promedio = sum(valores_numericos) / len(valores_numericos)
    puntaje_final = round(promedio * 100, 2)

    total = len(valores_numericos)
    explicacion = (
        f"Se evaluaron {total} preguntas. "
        f"Respuestas 'Sí' o 'N/A': {conteo['si'] + conteo['na']}, "
        f"'Parcialmente/En desarrollo': {conteo['parcial']}, "
        f"'No': {conteo['no']}. "
        f"El puntaje final es {puntaje_final:.2f}% según la fórmula: "
        "Sí/N.A.=100%, Parcialmente/En desarrollo=50%, No=0%."
    )

    return puntaje_final, explicacion



def evaluar_cuestionario_ia(texto_cuestionario: str) -> dict:
    prompt = f"""
Eres un experto en ciberseguridad y gestión de proveedores.
Analiza el siguiente cuestionario de seguridad diligenciado por un proponente.

Cuestionario:
{texto_cuestionario}

Tareas:
1. Evalúa el nivel de madurez en seguridad del proveedor (0 a 100, donde 100 es excelente).
2. Identifica las principales fortalezas y debilidades.
3. Señala riesgos relevantes para un Sistema de Gestión de Seguridad de la Información (SGSI).

Responde EXCLUSIVAMENTE en JSON válido con esta estructura:
{{
  "score": <numero entre 0 y 100>,
  "explanation": "<texto breve y claro explicando por qué pusiste ese puntaje, con fortalezas, debilidades y riesgos>"
}}
    """.strip()

    data = _ai_json_proponentes(
        prompt=prompt,
        system_prompt="Responde SOLO JSON válido. No incluyas texto adicional.",
        max_tokens=700,
        openrouter_model_env=os.getenv("AI_MODEL_CUESTIONARIO", "openai/gpt-4o-mini")
    )

    if "score" not in data or "explanation" not in data:
        raise ValueError(f"JSON incompleto IA cuestionario: {data}")

    return {
        "score": float(data["score"]),
        "explanation": (data["explanation"] or "").strip()
    }

def evaluar_reputacion_web_ia(nombre_proveedor: str, sitio_web: str | None = None) -> dict:
    prompt = f"""
Actúa como analista de riesgos de terceros.

Proveedor: {nombre_proveedor}
Sitio web (si se conoce): {sitio_web or "No informado"}

Tareas:
1. Describe las PRINCIPALES VENTAJAS del proveedor desde la perspectiva de ciberseguridad, cumplimiento y confiabilidad.
2. Describe los PRINCIPALES RIESGOS de ciberseguridad y cumplimiento que podrían existir con un proveedor de este tipo.
3. Indica qué CERTIFICACIONES DE SEGURIDAD relevantes (por ejemplo ISO 27001, SOC 2, etc.) tiene el proveedor
   según información disponible. Si no se encuentran certificaciones claras, indícalo explícitamente.
4. Indica qué CLIENTES o SECTORES relevantes atiende el proveedor (por ejemplo banca, gobierno, salud, etc.).
   Si no se identifican clientes públicos, dilo de forma explícita.
5. Resume INFORMACIÓN GENERAL DE LA COMPAÑÍA: tipo de servicios, tamaño aproximado (si se infiere), años en el mercado
   o cualquier otro dato relevante.
6. Asigna un PUNTAJE DE REPUTACIÓN de 0 a 100 (100 = reputación excelente).
   Si no hay información específica, utiliza un puntaje medio razonable (por ejemplo 60)
   dejando claro que la evidencia es limitada.

Responde SOLO en JSON válido con esta estructura:
{{
  "score": <numero entre 0 y 100>,
  "ventajas": "<texto breve>",
  "riesgos": "<texto breve>",
  "certificaciones_seguridad": "<texto breve>",
  "clientes": "<texto breve>",
  "informacion_compania": "<texto breve>"
}}
    """.strip()

    data = _ai_json_proponentes(
        prompt=prompt,
        system_prompt="Responde SOLO JSON válido. No incluyas texto adicional.",
        max_tokens=900,
        openrouter_model_env=os.getenv("AI_MODEL_REPUTACION", "openai/gpt-4o-mini")
    )

    if "score" not in data:
        raise ValueError(f"La IA devolvió un JSON sin la clave 'score': {data}")

    ventajas = data.get("ventajas", "No se identificaron ventajas específicas en la información disponible.")
    riesgos = data.get("riesgos", "No se identificaron riesgos específicos en la información disponible.")
    certificaciones = data.get(
        "certificaciones_seguridad",
        "No se identificaron certificaciones de seguridad específicas en la información disponible."
    )
    clientes = data.get(
        "clientes",
        "No se identificó información clara sobre clientes o sectores atendidos."
    )
    info_compania = data.get(
        "informacion_compania",
        "No se encontró información detallada sobre la compañía."
    )

    explicacion = (
        f"Ventajas:\n{ventajas}\n\n"
        f"Riesgos:\n{riesgos}\n\n"
        f"Certificaciones de seguridad:\n{certificaciones}\n\n"
        f"Clientes:\n{clientes}\n\n"
        f"Información de la compañía:\n{info_compania}"
    )

    return {
        "score": float(data["score"]),
        "explanation": explicacion
    }

def limitar_texto_ia(texto: str, max_chars_ollama: int = 3000, max_chars_openrouter: int = 12000) -> str:
    if not texto:
        return ""

    texto = texto.strip()

    provider = (get_ai_provider() or "openrouter").lower()

    if provider == "ollama":
        max_chars = max_chars_ollama
    else:
        max_chars = max_chars_openrouter

    if len(texto) <= max_chars:
        return texto

    return texto[:max_chars] + "\n\n[Texto truncado para optimizar consumo de IA]"

# =========================================
# Helpers IA - Cuestionarios de Proponentes
# =========================================

def _extraer_json_objeto_desde_texto(raw: str) -> dict:
    texto = (raw or "").strip()
    if not texto:
        raise ValueError("La IA devolvió una respuesta vacía.")

    # intento directo
    try:
        data = json.loads(texto)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # fallback: extraer primer bloque JSON
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        raise ValueError(f"No se encontró un objeto JSON válido en la respuesta IA: {texto[:500]}")

    data = json.loads(m.group(0))
    if not isinstance(data, dict):
        raise ValueError("La IA no devolvió un objeto JSON.")
    return data


def _ai_json_proponentes(prompt: str,
                         system_prompt: str = "Responde SOLO JSON válido. No incluyas texto adicional.",
                         max_tokens: int = 700,
                         openrouter_model_env: str = "openai/gpt-4o-mini") -> dict:
    """
    Helper IA para este módulo.
    Soporta OpenRouter y Ollama.
    Devuelve SIEMPRE dict.
    """
    provider = (get_ai_provider() or "openrouter").strip().lower()
    

    # =========================
    # OLLAMA
    # =========================
    if provider == "ollama":
        base_url = (get_ollama_base_url() or "http://localhost:11434").strip().rstrip("/")
        model = (get_ollama_model() or "llama3.1").strip()

        if not base_url:
            raise RuntimeError("No hay OLLAMA_BASE_URL configurada en Administración.")
        if not model:
            raise RuntimeError("No hay OLLAMA_MODEL configurado en Administración.")

        full_prompt = f"{system_prompt}\n\n{prompt}".strip()

        try:
            resp = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 350,
                        "num_ctx": 2048,
                        "keep_alive": 0
                    }
                },
                timeout=(10, 180)
            )
            resp.raise_for_status()

            data = resp.json() or {}
            raw = (data.get("response") or "").strip()

            if not raw:
                raise ValueError(f"Ollama respondió sin contenido. Respuesta: {str(data)[:500]}")

            return _extraer_json_objeto_desde_texto(raw)

        finally:
            try:
                liberar_memoria_ollama_seguro()
            except Exception:
                pass

    # =========================
    # OPENROUTER
    # =========================
    api_key = get_openrouter_api_key()
    if not api_key:
        raise RuntimeError("No hay OPENROUTER_API_KEY configurada en Administración.")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    model_name = os.getenv("AI_MODEL_CUESTIONARIO", openrouter_model_env)
    max_tokens_safe = min(int(max_tokens or 700), 900)

    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=max_tokens_safe,
        response_format={"type": "json_object"},
    )

    raw = (resp.choices[0].message.content or "").strip()
    if not raw:
        raise ValueError("OpenRouter devolvió una respuesta vacía.")


    return _extraer_json_objeto_desde_texto(raw)


def calcular_puntaje_total(puntaje_cuestionario: float,
                           puntaje_reputacion: float,
                           peso_cuestionario: float = 0.7,
                           peso_reputacion: float = 0.3) -> float:
    """
    Puntaje total basado únicamente en el cuestionario.
    La reputación se usa solo como información cualitativa, no influye en el porcentaje final.
    """
    return round(puntaje_cuestionario, 2)

def obtener_resumen_respuestas_desde_excel_bytes(contenido_excel: bytes) -> dict:
    """
    Lee el Excel (binario) y devuelve un resumen:
    {
      "SI": [...],
      "N/A": [...],
      "PARCIALMENTE / EN DESARROLLO": [...],
      "NO": [...],
      "SIN RESPUESTA / EN BLANCO": [...]
    }
    """
    in_memory_file = io.BytesIO(contenido_excel)
    # Mantener las respuestas literales: por defecto pandas interpreta
    # "N/A" y "NA" como NaN y altera el resumen, el texto IA y el puntaje.
    df = pd.read_excel(in_memory_file, header=1, keep_default_na=False)

    # Detectar columna de respuestas
    posibles_resp = ["Respuesta", "RESPUESTA", "respuesta"]
    col_resp = next((c for c in df.columns if c in posibles_resp), None)

    if col_resp is None:
        for col in df.columns:
            valores = df[col].astype(str).str.lower()
            if any("respuesta" in v for v in valores.head(3)):
                col_resp = col
                break

    if col_resp is None:
        raise ValueError("No se pudo detectar la columna de Respuesta en el Excel.")

    # Columna de referencia: usamos la primera columna
    col_ref = df.columns[0]

    # Listas por tipo de respuesta
    refs_si = []
    refs_na = []
    refs_parcial = []
    refs_no = []
    refs_sin_resp = []   # 🔹 NUEVA categoría

    # Recorremos TODAS las filas (sin filtrar por notna en respuesta)
    for _, row in df.iterrows():
        # referencia
        ref_raw = row[col_ref]
        ref = str(ref_raw).strip() if pd.notna(ref_raw) else ""
        # filtramos filas que no tienen referencia útil
        if not ref or ref.lower() in ("nan", "referencia"):
            continue

        resp_raw = row[col_resp] if col_resp in row else None

        # 🔹 Caso 1: respuesta vacía / NaN → SIN RESPUESTA
        if resp_raw is None or (isinstance(resp_raw, float) and pd.isna(resp_raw)):
            refs_sin_resp.append(ref)
            continue

        resp_str = str(resp_raw).strip()
        if not resp_str:
            refs_sin_resp.append(ref)
            continue

        # Normalizamos
        resp_norm = _normalizar_respuesta(resp_raw)

        # Si después de normalizar sigue vacío o "nan" → SIN RESPUESTA
        if not resp_norm or resp_norm == "nan":
            refs_sin_resp.append(ref)
            continue

        # Clasificamos por tipo de respuesta
        if resp_norm in ("si", "s", "yes"):
            refs_si.append(ref)
        elif "n/a" in resp_norm or resp_norm in ("na", "n.a", "n.a.", "no aplica"):
            refs_na.append(ref)
        elif "parcial" in resp_norm or "desarrollo" in resp_norm:
            refs_parcial.append(ref)
        elif resp_norm == "no":
            refs_no.append(ref)
        else:
            # Si quieres guardar otros valores, puedes agregarlos a otra lista
            # por ahora los ignoramos en el resumen
            pass

    resumen = {
        "SI": refs_si,
        "N/A": refs_na,
        "PARCIALMENTE / EN DESARROLLO": refs_parcial,
        "NO": refs_no,
        "SIN RESPUESTA / EN BLANCO": refs_sin_resp,
    }

    return resumen

#=======================
# Cuestionario
#=======================
@app.route('/ingreso_informacion_proponente_archivo', methods=['GET', 'POST'], endpoint='ingreso_informacion_proponente_archivo')
@app.route('/cuestionarios_proveedores', methods=['GET', 'POST'])
@login_required
def cuestionarios_proveedores():
    from flask import g as _cpw_g
    user = User.query.get(session.get('user_id'))
    _cpw_portal = getattr(_cpw_g, 'cpw_ids', None) is not None and verificar_permiso(user, 'Cuestionario de proveedores web')

    if user.role == 'auditor':
        flash("El rol Auditor no puede ingresar al módulo de cuestionario de proveedores.", "danger")
        return redirect(url_for('menu'))

    modo_archivo = request.path == '/ingreso_informacion_proponente_archivo'
    permiso_archivo = verificar_permiso(user, 'Cuestionarios de Proponentes')
    permiso_web = verificar_permiso(user, 'Cuestionario de proveedores web')
    if user.role != 'admin' and not _cpw_portal and not (permiso_archivo if modo_archivo else (permiso_archivo or permiso_web)):
        flash('No tiene permiso para ingresar al módulo solicitado.', 'danger')
        return redirect(url_for('menu'))
    
    # Cuando la API interna de ingreso web invoca esta función, mantiene su POST y resultados.
    destino = 'cuestionarios_proveedores' if _cpw_portal else 'ingreso_informacion_proponente_archivo'

    if request.method == 'POST' and not (modo_archivo or _cpw_portal):
        flash('La carga y evaluación desde archivo se realiza en Ingreso de información proponente archivo.', 'info')
        return redirect(url_for('ingreso_informacion_proponente_archivo'))

    if request.method == 'POST':
        accion = 'evaluar' if _cpw_portal else request.form.get('accion', 'subir')

        # =====================================
        # 1) ACCIÓN: SUBIR CUESTIONARIO
        # =====================================
        if accion == 'subir':
            nombre_proveedor = request.form.get('nombre_proveedor', '').strip()
            sitio_web = request.form.get('sitio_web', '').strip() or None
            file = request.files.get('archivo')

            if not nombre_proveedor:
                flash("Debes ingresar el nombre del proveedor.", "warning")
                return redirect(url_for(destino))

            if not file or file.filename == '':
                flash("Debes seleccionar un archivo de cuestionario en Excel.", "warning")
                return redirect(url_for(destino))

            if not allowed_file_excel(file.filename):
                flash("Solo se permiten archivos Excel (.xls, .xlsx).", "danger")
                return redirect(url_for(destino))

            try:
                # 1) Generamos texto normalizado (para referencia / auditoría)
                texto_normalizado = leer_cuestionario_excel(file)

                # 2) Guardamos binario del archivo
                contenido_bin = file.read()
                if not contenido_bin:
                    file.stream.seek(0)
                    contenido_bin = file.read()

                cuestionario = CuestionarioProveedor(
                    nombre_proveedor=nombre_proveedor,
                    sitio_web=sitio_web,
                    nombre_archivo=file.filename,
                    contenido_archivo=contenido_bin,
                    texto_normalizado=texto_normalizado,
                )
                db.session.add(cuestionario)
                db.session.commit()

                flash("Cuestionario cargado correctamente. Ahora puedes evaluar el grupo de proveedores.", "success")

            except Exception as e:
                db.session.rollback()
                print("Error al subir cuestionario:", e)
                flash(f"Ocurrió un error al cargar el cuestionario: {e}", "danger")

            return redirect(url_for(destino))

        # =====================================
        # 2) ACCIÓN: EVALUAR TODOS LOS PROVEEDORES (CREA UN GRUPO)
        # =====================================
        elif accion == 'evaluar':
            titulo_eval = _cpw_g.cpw_title if _cpw_portal else request.form.get('titulo_evaluacion', '').strip()
            descripcion_eval = (_cpw_g.cpw_description or None) if _cpw_portal else (request.form.get('descripcion_evaluacion', '').strip() or None)

            if not titulo_eval:
                flash("Debes ingresar un título para la evaluación.", "warning")
                return redirect(url_for(destino))

            # Un cuestionario se considera evaluado SOLO si existe su resultado
            # en el historial vigente del módulo «Evaluación de proponentes».
            # La tabla evaluacion_cuestionario conserva un cálculo auxiliar,
            # incluso después de eliminar el grupo histórico; no debe bloquear
            # una nueva evaluación cuando el resultado ya no existe.
            ids_con_resultado = db.session.query(EvaluacionGrupoDetalle.cuestionario_id)
            cuestionarios = CuestionarioProveedor.query.options(
                selectinload(CuestionarioProveedor.evaluacion)
            ).filter(
                ~CuestionarioProveedor.id.in_(ids_con_resultado),
                CuestionarioProveedor.id.in_(_cpw_g.cpw_ids) if _cpw_portal else True
            ).order_by(
                CuestionarioProveedor.fecha_carga.desc()
            ).all()

            if not cuestionarios:
                flash(
                    "No hay cuestionarios disponibles para esta evaluación. "
                    "Los cuestionarios seleccionados ya tienen resultados en "
                    "«Evaluación de proponentes», o aún no se han cargado. "
                    "Si se elimina el resultado histórico correspondiente, "
                    "su cuestionario podrá evaluarse nuevamente sin volver a cargarlo.",
                    "info"
                )
                return redirect(url_for(destino))

            # Si el usuario eligió cuestionarios ya registrados junto a otros
            # pendientes, procesar únicamente los pendientes y avisar cuáles
            # se omitieron para no generar resultados duplicados.
            omitidos = (len(set(_cpw_g.cpw_ids)) - len(cuestionarios)) if _cpw_portal else 0

            grupo = EvaluacionGrupo(
                titulo=titulo_eval,
                descripcion=descripcion_eval,
                fecha_evaluacion=datetime.utcnow()
            )
            db.session.add(grupo)
            db.session.flush()

            procesados = 0
            errores = 0

            for c in cuestionarios:
                try:
                    # =========================================================
                    # 1) PUNTAJE DEL CUESTIONARIO (ESTE SÍ DEBE SER OBLIGATORIO)
                    # =========================================================
                    if not c.contenido_archivo:
                        raise ValueError("El cuestionario no tiene contenido_archivo almacenado en la base de datos.")

                    score_c, exp_c = calcular_puntaje_desde_excel_bytes(c.contenido_archivo)

                    # =========================================================
                    # 2) IA SOBRE EL CUESTIONARIO (OPCIONAL, NO DEBE TUMBAR TODO)
                    # =========================================================
                    texto_q = limitar_texto_ia((c.texto_normalizado or "").strip())
                    if texto_q:
                        try:
                            ia_q = evaluar_cuestionario_ia(texto_q)
                            score_ia_q = float(ia_q.get("score", 0) or 0)
                            exp_ia_q = (ia_q.get("explanation") or "").strip()

                            exp_c = (
                                f"{exp_c}\n\n"
                                f"---\n"
                                f"ANÁLISIS IA DEL CUESTIONARIO (madurez proveedor): {score_ia_q:.1f}/100\n"
                                f"{exp_ia_q}"
                            )
                        except Exception as e_ia_q:
                            print(f"Error IA cuestionario proveedor {c.id} ({c.nombre_proveedor}): {e_ia_q}")
                            traceback.print_exc()
                            exp_c = (
                                f"{exp_c}\n\n"
                                f"---\n"
                                f"ANÁLISIS IA DEL CUESTIONARIO: No disponible por error técnico ({e_ia_q})."
                            )
                    else:
                        exp_c = (
                            f"{exp_c}\n\n"
                            f"---\n"
                            f"ANÁLISIS IA DEL CUESTIONARIO: No disponible (texto normalizado vacío)."
                        )

                    # =========================================================
                    # 3) REPUTACIÓN IA (OPCIONAL, NO DEBE TUMBAR TODO)
                    # =========================================================
                    try:
                        resultado_rep = evaluar_reputacion_web_ia(c.nombre_proveedor, c.sitio_web)
                        score_r = float(resultado_rep.get("score", 60) or 60)
                        exp_r = resultado_rep.get(
                            "explanation",
                            "No fue posible generar explicación de reputación."
                        )
                    except Exception as e_rep:
                        print(f"Error reputación IA proveedor {c.id} ({c.nombre_proveedor}): {e_rep}")
                        traceback.print_exc()

                        score_r = 60.0
                        exp_r = (
                            "No fue posible completar el análisis automático de reputación por un error técnico. "
                            "Se asignó un valor neutro informativo de 60/100 únicamente para referencia cualitativa. "
                            f"Detalle técnico: {e_rep}"
                        )

                    # =========================================================
                    # 4) PUNTAJE TOTAL
                    # =========================================================
                    score_total = calcular_puntaje_total(score_c, score_r)

                    # =========================================================
                    # 5) EVALUACIÓN ACTUAL DEL PROVEEDOR
                    # =========================================================
                    if c.evaluacion is None:
                        evaluacion = EvaluacionCuestionario(
                            cuestionario_id=c.id,
                            puntaje_cuestionario=score_c,
                            explicacion_cuestionario=exp_c,
                            puntaje_reputacion=score_r,
                            explicacion_reputacion=exp_r,
                            puntaje_total=score_total
                        )
                        db.session.add(evaluacion)
                    else:
                        c.evaluacion.puntaje_cuestionario = score_c
                        c.evaluacion.explicacion_cuestionario = exp_c
                        c.evaluacion.puntaje_reputacion = score_r
                        c.evaluacion.explicacion_reputacion = exp_r
                        c.evaluacion.puntaje_total = score_total

                    # =========================================================
                    # 6) DETALLE HISTÓRICO DEL GRUPO
                    # =========================================================
                    detalle = EvaluacionGrupoDetalle(
                        grupo_id=grupo.id,
                        cuestionario_id=c.id,
                        nombre_proveedor=c.nombre_proveedor,
                        sitio_web=c.sitio_web,
                        puntaje_cuestionario=score_c,
                        explicacion_cuestionario=exp_c,
                        puntaje_reputacion=score_r,
                        explicacion_reputacion=exp_r,
                        puntaje_total=score_total
                    )
                    db.session.add(detalle)

                    procesados += 1

                except Exception as e:
                    errores += 1
                    print(f"\n{'='*100}")
                    print(f"ERROR al evaluar cuestionario id {c.id} ({c.nombre_proveedor})")
                    print(f"Tipo de error: {type(e).__name__}")
                    print(f"Detalle: {e}")
                    traceback.print_exc()
                    print(f"{'='*100}\n")

            # Si ninguno se procesó, opcionalmente elimina el grupo vacío
            if procesados == 0:
                try:
                    db.session.rollback()
                except Exception:
                    pass

                flash(
                    f"No se pudo evaluar ningún proveedor para '{titulo_eval}'. "
                    f"Revisa la consola porque hubo errores en {errores} proveedor(es).",
                    "danger"
                )
                return redirect(url_for(destino))

            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print("Error al hacer commit de las evaluaciones:", e)
                traceback.print_exc()
                flash(f"Ocurrió un error al guardar las evaluaciones: {e}", "danger")
                return redirect(url_for(destino))

            if _cpw_portal:
                _cpw_g.cpw_group_id = grupo.id

            msg = f"Se creó la evaluación '{titulo_eval}' con {procesados} proponente(s) evaluado(s)."
            if omitidos > 0:
                msg += f" Se omitieron {omitidos} cuestionario(s) porque su resultado ya figura en Evaluación de proponentes."
            if errores > 0:
                msg += f" Hubo errores en {errores} proveedor(es). Revisa la consola para más detalles."
            flash(msg, "success")

            return redirect(url_for(destino))

        
    # GET de Consultas y resultados es liviano: no abre archivos Excel BLOB.
    cuestionarios_cargados = []
    if modo_archivo:
        # Mostrar de nuevo cuestionarios cuyos resultados fueron eliminados.
        # La existencia de evaluacion_cuestionario no equivale a un histórico vigente.
        ids_con_resultado = db.session.query(EvaluacionGrupoDetalle.cuestionario_id)
        cuestionarios_cargados = CuestionarioProveedor.query.options(
            load_only(CuestionarioProveedor.id, CuestionarioProveedor.fecha_carga,
                      CuestionarioProveedor.nombre_proveedor, CuestionarioProveedor.sitio_web,
                      CuestionarioProveedor.nombre_archivo)
        ).filter(
            ~CuestionarioProveedor.id.in_(ids_con_resultado)
        ).order_by(CuestionarioProveedor.fecha_carga.desc()).all()
    # El dato del grupo más reciente se preserva para compatibilidad con BASE.
    ultimo_grupo = EvaluacionGrupo.query.order_by(EvaluacionGrupo.fecha_evaluacion.desc()).first()

    # Construimos HTML
    content = render_template_string("""
    <div class="propia-shell">

      <!-- CABECERA -->
      <div class="propia-header-card">
        <div class="propia-header-overlay">
          <div class="propia-header-text">
            <h3 class="propia-title m-0">{{ 'Ingreso de información proponente archivo' if modo_archivo else 'Evaluación de proponentes' }}</h3>
            <div class="propia-subtitle">
              {% if modo_archivo %}
              Carga de cuestionarios Excel y evaluación grupal de proveedores.
              {% else %}
              Consultas y resultados de evaluaciones de proponentes ingresados por web o archivo.
              {% endif %}
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="propia-header-actions">
        
      </div>

      {% if modo_archivo %}
      <!-- CARGA -->
      <div class="propia-card mb-4">
        <div class="propia-card-body">
          <div class="propia-section-title">Cargar nuevo cuestionario</div>

          <form method="post" enctype="multipart/form-data" data-no-progress="true">
            <input type="hidden" name="accion" value="subir">

            <div class="row g-3">
              <div class="col-md-4">
                <label class="form-label">Nombre del proveedor</label>
                <input type="text" name="nombre_proveedor" class="form-control" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Sitio web (opcional)</label>
                <input type="url" name="sitio_web" class="form-control" placeholder="https://...">
              </div>

              <div class="col-md-4">
                <label class="form-label">Archivo Excel del cuestionario</label>
                <input type="file" name="archivo" class="form-control" accept=".xls,.xlsx" required>
              </div>
            </div>

            <div class="propia-bottom-actions justify-content-start">
              <button type="submit" class="btn btn-primary rounded-pill px-4 fw-bold">
                Subir cuestionario
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- TABLA CUESTIONARIOS -->
      {% if cuestionarios_cargados %}
      <div class="propia-card mb-4">
        <div class="propia-card-body">
          <div class="propia-section-title">Cuestionarios pendientes de evaluación</div>
          <p class="text-muted mb-2">
            Estos son los cuestionarios que has cargado y aún no han sido incluidos en una evaluación de grupo.
          </p>

          <div class="table-responsive propia-table-wrap">
            <table class="table table-sm table-striped align-middle mb-0">
              <thead class="propia-table-head">
                <tr>
                  <th>Fecha de carga</th>
                  <th>Proveedor</th>
                  <th>Sitio web</th>
                  <th>Archivo</th>
                  <th>Eliminar</th>
                </tr>
              </thead>
              <tbody>
                {% for c in cuestionarios_cargados %}
                  <tr>
                    <td>{{ c.fecha_carga.strftime('%Y-%m-%d %H:%M') }}</td>
                    <td>{{ c.nombre_proveedor }}</td>
                    <td>
                      {% if c.sitio_web %}
                        <a href="{{ c.sitio_web }}" target="_blank">{{ c.sitio_web }}</a>
                      {% else %}
                        -
                      {% endif %}
                    </td>
                    <td>{{ c.nombre_archivo }}</td>
                    <td>
                      <form method="post"
                            action="{{ url_for('cuestionarios_proveedores_eliminar', cuestionario_id=c.id) }}"
                            onsubmit="return confirm('¿Eliminar este proponente?');"
                            style="display:inline;">
                        <button type="submit"
                                class="btn btn-sm btn-outline-danger rounded-pill grac-trash-button"
                                title="Eliminar proponente" aria-label="Eliminar proponente">
                          <i class="bi bi-trash3-fill grac-action-icon-white" aria-hidden="true"></i><span class="visually-hidden">Eliminar</span>
                        </button>
                      </form>
                    </td>
                  </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      {% endif %}

      <!-- EVALUAR -->
      <div class="propia-card mb-4">
        <div class="propia-card-body">
          <div class="propia-section-title">Evaluar grupo de proveedores</div>
          <p class="mb-2">
            Primero sube todos los cuestionarios de los proponentes. Luego, con este botón,
            se calculará el puntaje de cada uno según sus respuestas y se estimará su reputación.
          </p>

          <form method="post" id="form-evaluar-proveedores" data-no-progress="true">
            <input type="hidden" name="accion" value="evaluar">

            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Título de la evaluación</label>
                <input type="text"
                       name="titulo_evaluacion"
                       class="form-control"
                       placeholder="Ej: Evaluación proveedores nube Q4 2025"
                       required>
              </div>

              <div class="col-md-6">
                <label class="form-label">Descripción (opcional)</label>
                <input type="text"
                       name="descripcion_evaluacion"
                       class="form-control"
                       placeholder="Ej: Evaluación para contrato de servicios cloud">
              </div>
            </div>

            <div class="propia-bottom-actions justify-content-start">
              <button type="submit" class="btn btn-success rounded-pill px-4 fw-bold">
                Evaluar todos los proveedores
              </button>
            </div>
          </form>

          <!-- PROGRESO -->
          <div id="evaluacion-progress" class="mt-3" style="display:none;">
            <p class="mb-1">Analizando proponentes, por favor espera...</p>
            <div class="progress propia-progress">
              <div id="evaluacion-progress-bar"
                   class="progress-bar progress-bar-striped progress-bar-animated"
                   role="progressbar"
                   style="width: 10%;"
                   aria-valuenow="10"
                   aria-valuemin="0"
                   aria-valuemax="100">
              </div>
            </div>
          </div>
        </div>
      </div>

      {% endif %}
      {% if not modo_archivo %}
      <!-- NAVEGACIÓN SECUNDARIA -->
      <div class="propia-card mb-4">
        <div class="propia-card-body">
          <div class="propia-section-title">Consultas y resultados</div>
          <p class="text-muted mb-3">Consulta en un solo lugar los resultados de evaluaciones realizadas desde el portal web y las cargadas mediante archivos Excel.</p>

          <div class="d-flex justify-content-center gap-2 flex-wrap">
            <a href="{{ url_for('cuestionarios_proveedores_historico') }}"
               class="btn rounded-pill px-4 fw-bold propia-menu-btn">
              📚 Ver histórico de evaluaciones
            </a>

            <a href="{{ url_for('cuestionarios_proveedores_recomendado') }}"
               class="btn rounded-pill px-4 fw-bold propia-menu-btn">
              🏆 Ver proponente recomendado
            </a>
          </div>
        </div>
      </div>

      {% endif %}
      <script>
        document.addEventListener('DOMContentLoaded', function() {
          const form = document.querySelector('#form-evaluar-proveedores');
          const cont = document.querySelector('#evaluacion-progress');
          const bar  = document.querySelector('#evaluacion-progress-bar');

          if (form && cont && bar) {
            form.addEventListener('submit', function() {
              if (window.hideSGSIProgress) {
                window.hideSGSIProgress();
              }

              cont.style.display = 'block';

              let progress = 10;
              bar.style.width = progress + '%';
              bar.setAttribute('aria-valuenow', progress);
              bar.innerText = progress + '%';

              const interval = setInterval(function() {
                progress += 5;

                if (progress >= 95) {
                  progress = 95;
                  clearInterval(interval);
                }

                bar.style.width = progress + '%';
                bar.setAttribute('aria-valuenow', progress);
                bar.innerText = progress + '%';
              }, 600);
            });
          }

          window.addEventListener('pageshow', function() {
            if (cont) cont.style.display = 'none';

            if (bar) {
              bar.style.width = '10%';
              bar.setAttribute('aria-valuenow', '10');
              bar.innerText = '';
            }

            if (window.hideSGSIProgress) {
              window.hideSGSIProgress();
            }
          });
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

      .propia-shell{
        width:96%;
        max-width:1600px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HEADER SGSI MODERNO
      ========================= */
      .propia-header-card{
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

      .propia-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .propia-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .propia-header-overlay::before{
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
        font-size:1.4rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .propia-header-text{
        max-width:1100px;
      }

      .propia-header-text::before{
        content:"SGSI · Gestión";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .propia-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .propia-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES SUPERIORES
      ========================= */
      .propia-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .propia-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .propia-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .propia-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD PRINCIPAL
      ========================= */
      .propia-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .propia-card-body{
        padding:18px;
      }

      /* =========================
         SECCIONES
      ========================= */
      .propia-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin-bottom:12px;
      }

      /* =========================
         FORMULARIOS
      ========================= */
      .propia-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .propia-card .form-control,
      .propia-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .propia-card textarea.form-control{
        min-height:70px;
      }

      .propia-card .form-control:focus,
      .propia-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      /* =========================
         TABLA SGSI
      ========================= */
      .propia-table-wrap{
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
        overflow:hidden;
      }

      .propia-table-head th{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        border:none !important;
        font-size:.80rem;
      }

      .table-hover tbody tr:hover{
        background:#eef6ff;
      }

      /* =========================
         PROGRESS
      ========================= */
      .propia-progress{
        height:18px;
        border-radius:999px;
        overflow:hidden;
      }

      .progress-bar{
        font-weight:800;
      }

      /* =========================
         BOTONES INFERIORES
      ========================= */
      .propia-bottom-actions{
        display:flex;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
        justify-content:center;
      }

      .propia-menu-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .propia-menu-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      .btn.rounded-pill{
        border-radius:10px !important;
        font-weight:900;
      }

      /* =========================
         RESPONSIVE
      ========================= */
      @media (max-width:992px){
        .propia-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .propia-title{
          font-size:1.20rem;
        }

        .propia-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .propia-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .propia-header-overlay::before{
          margin:0;
        }

        .propia-header-text::before{
          margin:auto;
        }

        .propia-header-actions .btn{
          width:100%;
        }
      }
    </style>
    </div>
    """, cuestionarios_cargados=cuestionarios_cargados, modo_archivo=modo_archivo)

    return render_template_string(BASE, content=content, ultimo_grupo=ultimo_grupo)

#===================================
# Cuestionario Proveedor Recomendado
#===================================

@app.route('/cuestionarios_proveedores/recomendado')
@login_required
def cuestionarios_proveedores_recomendado():
    # Traemos SOLO el último grupo de evaluación
    grupo = EvaluacionGrupo.query.options(
        selectinload(EvaluacionGrupo.detalles)
        .selectinload(EvaluacionGrupoDetalle.cuestionario)
    ).order_by(
        EvaluacionGrupo.fecha_evaluacion.desc()
    ).first()

    mejor = None
    detalles_ordenados = []

    if grupo and grupo.detalles:
        # Ordenamos los proponentes de la última evaluación por puntaje_total desc
        detalles_ordenados = sorted(grupo.detalles, key=lambda d: d.puntaje_total, reverse=True)
        mejor_detalle = detalles_ordenados[0]
        mejor = mejor_detalle.cuestionario

    content = render_template_string("""
    <div class="propreco-shell">

      <!-- CABECERA -->
      <div class="propreco-header-card">
        <div class="propreco-header-overlay">
          <div class="propreco-header-text">
            <h3 class="propreco-title m-0">Proponente recomendado por la evaluación</h3>
            <div class="propreco-subtitle">
              Visualización del proveedor recomendado según el análisis de cuestionario, reputación asistida por IA y comparación de la última evaluación grupal registrada
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="propreco-header-actions">
        <a href="{{ url_for('cuestionarios_proveedores') }}"
           class="btn rounded-pill px-5 fw-bold propreco-back-btn">
          ⬅️ Volver a Evaluación de proponentes
        </a>
      </div>

      {% if not grupo or not detalles %}

        <div class="propreco-card">
          <div class="propreco-card-body">
            <div class="alert alert-info mb-0">
              Todavía no hay ninguna evaluación de grupo registrada o no se encontraron proponentes evaluados.
              Primero realiza una evaluación de grupo desde el módulo de cuestionarios.
            </div>
          </div>
        </div>

      {% else %}

        <!-- RESUMEN DE ÚLTIMA EVALUACIÓN -->
        <div class="propreco-card mb-4">
          <div class="propreco-card-body">
            <div class="propreco-section-title">Última evaluación realizada</div>
            <div class="propreco-summary">
              <strong>{{ grupo.titulo }}</strong><br>
              {{ grupo.descripcion or '' }}
            </div>
          </div>
        </div>

        <!-- PROVEEDOR RECOMENDADO -->
        {% if mejor and mejor.evaluacion %}
        <div class="propreco-card propreco-highlight-card mb-4">
          <div class="propreco-card-body">
            <div class="propreco-section-title text-success">🏆 Proponente recomendado</div>

            <div class="row g-3">
              <div class="col-md-6">
                <div class="propreco-info-box">
                  <p class="mb-1"><strong>Proveedor:</strong> {{ mejor.nombre_proveedor }}</p>

                  {% if mejor.sitio_web %}
                    <p class="mb-1">
                      <strong>Sitio web:</strong>
                      <a href="{{ mejor.sitio_web }}" target="_blank">{{ mejor.sitio_web }}</a>
                    </p>
                  {% endif %}

                  <p class="mb-1">
                    <strong>Puntaje total (solo cuestionario):</strong>
                    {{ "%.2f"|format(mejor.evaluacion.puntaje_total) }}%
                  </p>
                </div>
              </div>

              <div class="col-md-6">
                <div class="propreco-badge-box">
                  <span class="badge propreco-win-badge px-4 py-2">
                    Recomendado
                  </span>
                </div>
              </div>

              <div class="col-12">
                <div class="propreco-reason-box">
                  <strong>Motivo (cuestionario / reglas):</strong><br>
                  {{ mejor.evaluacion.explicacion_cuestionario }}
                </div>
              </div>

              <div class="col-12">
                <div class="propreco-reason-box">
                  <strong>Motivo (reputación):</strong><br>
                  {{ mejor.evaluacion.explicacion_reputacion.replace('\\n', '<br>')|safe }}
                </div>
              </div>
            </div>
          </div>
        </div>
        {% endif %}

        <!-- RESULTADOS -->
        <div class="propreco-card">
          <div class="propreco-card-body">
            <div class="propreco-section-title">Resultados de la última evaluación de proponentes</div>

            <div class="table-responsive propreco-table-wrap">
              <table class="table table-sm table-striped align-middle mb-0">
                <thead class="propreco-table-head">
                  <tr>
                    <th>Proveedor</th>
                    <th>Sitio web</th>
                    <th>Puntaje cuestionario</th>
                    <th>Puntaje total</th>
                    <th>Ficha</th>
                  </tr>
                </thead>
                <tbody>
                  {% for d in detalles %}
                    <tr>
                      <td>{{ d.nombre_proveedor }}</td>
                      <td>
                        {% if d.sitio_web %}
                          <a href="{{ d.sitio_web }}" target="_blank">{{ d.sitio_web }}</a>
                        {% else %}
                          -
                        {% endif %}
                      </td>
                      <td>{{ "%.1f"|format(d.puntaje_cuestionario) }}</td>
                      <td>{{ "%.1f"|format(d.puntaje_total) }}</td>
                      <td>
                        <a href="{{ url_for('cuestionarios_proveedores_ficha_proponente', detalle_id=d.id) }}"
                           class="btn btn-sm btn-outline-secondary rounded-pill">
                          Ver ficha
                        </a>
                      </td>
                    </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>

          </div>
        </div>

      {% endif %}
    </div>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .propreco-shell{
        width:96%;
        max-width:1600px;
        margin:10px auto 24px auto;
      }

      .propreco-header-card{
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

      .propreco-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .propreco-header-overlay{
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

      .propreco-header-overlay::before{
        content:"🏆";
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

      .propreco-header-text{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .propreco-header-text::before{
        content:"SGSI · Recomendación de Proveedor";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .propreco-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .propreco-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .propreco-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .propreco-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .propreco-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .propreco-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .propreco-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        margin-bottom:18px;
      }

      .propreco-highlight-card{
        border:2px solid rgba(34,197,94,.35);
        box-shadow:0 14px 28px rgba(22,163,74,.14);
      }

      .propreco-card-body{
        padding:18px;
      }

      .propreco-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .propreco-summary{
        color:#0b1220;
        line-height:1.55;
        font-size:.90rem;
      }

      .propreco-info-box,
      .propreco-reason-box{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:8px 7px;
        height:100%;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .propreco-badge-box{
        display:flex;
        align-items:center;
        justify-content:center;
        min-height:100%;
      }

      .propreco-win-badge{
        background:linear-gradient(135deg,#087c3d,#0f8a42);
        color:#fff;
        font-size:.78rem;
        font-weight:950;
        border-radius:999px;
        box-shadow:0 8px 18px rgba(22,163,74,.25);
        padding:7px 14px;
      }

      .propreco-table-wrap{
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
        overflow:hidden;
      }

      .propreco-table-head th{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        vertical-align:middle;
        border:none !important;
        font-size:.78rem;
      }

      .table td,
      .table th{
        vertical-align:middle !important;
      }

      .table-hover tbody tr:hover{
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

      .propreco-card .btn{
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        font-weight:900;
      }

      @media (max-width:992px){
        .propreco-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .propreco-header-card{
          min-height:88px;
        }

        .propreco-title{
          font-size:1.20rem;
        }

        .propreco-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .propreco-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .propreco-header-overlay::before{
          margin:0;
        }

        .propreco-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .propreco-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, grupo=grupo, detalles=detalles_ordenados, mejor=mejor)

    return render_template_string(BASE, content=content)

#=======================
# Cuestionario Historial
#=======================

@app.route('/cuestionarios_proveedores/historico')
@login_required
def cuestionarios_proveedores_historico():
    grupos = EvaluacionGrupo.query.order_by(EvaluacionGrupo.fecha_evaluacion.desc()).all()

    content = render_template_string("""
    <div class="prophist-shell">

      <!-- CABECERA -->
      <div class="prophist-header-card">
        <div class="prophist-header-overlay">
          <div class="prophist-header-text">
            <h3 class="prophist-title m-0">Histórico de Evaluaciones de Proponentes</h3>
            <div class="prophist-subtitle">
              Consulta de evaluaciones grupales realizadas, cantidad de proponentes analizados y acceso al detalle histórico de cada proceso
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="prophist-header-actions">
        <a href="{{ url_for('cuestionarios_proveedores') }}"
           class="btn rounded-pill px-5 fw-bold prophist-back-btn">
          ⬅️ Volver a Evaluación de proponentes
        </a>
      </div>

      {% if grupos %}
        <div class="prophist-card">
          <div class="prophist-card-body">
            <div class="prophist-section-title">Evaluaciones registradas</div>

            <div class="table-responsive prophist-table-wrap">
              <table class="table table-sm table-striped align-middle mb-0">
                <thead class="prophist-table-head">
                  <tr>
                    <th>Fecha</th>
                    <th>Título</th>
                    <th>Descripción</th>
                    <th>Nº proponentes</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {% for g in grupos %}
                    <tr>
                      <td>{{ g.fecha_evaluacion.strftime('%Y-%m-%d %H:%M') }}</td>
                      <td>{{ g.titulo }}</td>
                      <td>{{ g.descripcion or '-' }}</td>
                      <td>{{ g.detalles|length }}</td>
                      <td>
                        <a href="{{ url_for('cuestionarios_proveedores_historico_detalle', grupo_id=g.id) }}"
                           class="btn btn-sm btn-outline-primary rounded-pill">
                          Ver evaluación
                        </a>

                        <form method="post"
                              action="{{ url_for('cuestionarios_proveedores_historico_eliminar', grupo_id=g.id) }}"
                              style="display:inline;"
                              onsubmit="return confirm('¿Seguro que deseas eliminar esta evaluación y su historial?');">
                          <button type="submit"
                                  class="btn btn-sm btn-outline-danger rounded-pill ms-1">
                            Eliminar
                          </button>
                        </form>
                      </td>
                    </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      {% else %}
        <div class="prophist-card">
          <div class="prophist-card-body">
            <div class="alert alert-info mb-0">
              Todavía no se ha registrado ninguna evaluación de grupo.
            </div>
          </div>
        </div>
      {% endif %}
    </div>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .prophist-shell{
        width:96%;
        max-width:1600px;
        margin:10px auto 24px auto;
      }

      .prophist-header-card{
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

      .prophist-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .prophist-header-overlay{
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

      .prophist-header-overlay::before{
        content:"📜";
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

      .prophist-header-text{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .prophist-header-text::before{
        content:"SGSI · Historial de Evaluación";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .prophist-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .prophist-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .prophist-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .prophist-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .prophist-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .prophist-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .prophist-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .prophist-card-body{
        padding:18px;
      }

      .prophist-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .prophist-table-wrap{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .prophist-table-head th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        vertical-align:middle;
        border:none !important;
        font-size:.78rem;
        text-align:center;
      }

      .table td,
      .table th{
        vertical-align:middle !important;
        font-size:.82rem;
      }

      .table-hover tbody tr:hover{
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

      .prophist-card .btn{
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        font-weight:900;
      }

      @media (max-width:992px){
        .prophist-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .prophist-header-card{
          min-height:88px;
        }

        .prophist-title{
          font-size:1.20rem;
        }

        .prophist-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .prophist-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .prophist-header-overlay::before{
          margin:0;
        }

        .prophist-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .prophist-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, grupos=grupos)

    return render_template_string(BASE, content=content)

#==================================
# Cuestionario Proponente Historial
#==================================

@app.route('/cuestionarios_proveedores/historico/<int:grupo_id>')
@login_required
def cuestionarios_proveedores_historico_detalle(grupo_id):
    grupo = EvaluacionGrupo.query.options(
        selectinload(EvaluacionGrupo.detalles).selectinload(EvaluacionGrupoDetalle.cuestionario)
    ).get_or_404(grupo_id)

    # ordenar por puntaje_total desc
    detalles_ordenados = sorted(grupo.detalles, key=lambda d: d.puntaje_total, reverse=True)

    content = render_template_string("""
    <div class="prophdet-shell">

      <!-- CABECERA -->
      <div class="prophdet-header-card">
        <div class="prophdet-header-overlay">
          <div class="prophdet-header-text">
            <h3 class="prophdet-title m-0">Historial de Evaluación – {{ grupo.titulo }}</h3>
            <div class="prophdet-subtitle">
              Fecha: {{ grupo.fecha_evaluacion.strftime('%Y-%m-%d %H:%M') }}{% if grupo.descripcion %} · {{ grupo.descripcion }}{% endif %}
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="prophdet-header-actions">
        <a href="{{ url_for('cuestionarios_proveedores_historico') }}"
           class="btn rounded-pill px-5 fw-bold prophdet-back-btn">
          ⬅️ Volver al Histórico de Evaluaciones
        </a>
      </div>

      <!-- TARJETA RESULTADOS -->
      <div class="prophdet-card">
        <div class="prophdet-card-body">
          <div class="prophdet-section-title">Proponentes evaluados en esta corrida</div>

          <div class="table-responsive prophdet-table-wrap">
            <table class="table table-sm table-striped align-middle mb-0">
              <thead class="prophdet-table-head">
                <tr>
                  <th>Proveedor</th>
                  <th>Sitio web</th>
                  <th>Puntaje cuestionario</th>
                  <th>Puntaje total</th>
                  <th>Ficha</th>
                  <th>Registrar</th>
                </tr>
              </thead>
              <tbody>
                {% for d in detalles %}
                  <tr>
                    <td>{{ d.nombre_proveedor }}</td>
                    <td>
                      {% if d.sitio_web %}
                        <a href="{{ d.sitio_web }}" target="_blank">{{ d.sitio_web }}</a>
                      {% else %}
                        -
                      {% endif %}
                    </td>
                    <td>{{ "%.1f"|format(d.puntaje_cuestionario) }}</td>
                    <td>{{ "%.1f"|format(d.puntaje_total) }}</td>
                    <td>
                      <a href="{{ url_for('cuestionarios_proveedores_ficha_proponente', detalle_id=d.id) }}"
                         class="btn btn-sm btn-outline-secondary rounded-pill">
                        Ver ficha
                      </a>
                    </td>
                    <td>
                      <a href="{{ url_for('proveedores_new') }}"
                         class="btn btn-sm btn-outline-success rounded-pill">
                        Registrar
                      </a>
                    </td>
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

      .prophdet-shell{
        width:96%;
        max-width:1600px;
        margin:10px auto 24px auto;
      }

      .prophdet-header-card{
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

      .prophdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .prophdet-header-overlay{
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

      .prophdet-header-overlay::before{
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
      }

      .prophdet-header-text{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .prophdet-header-text::before{
        content:"SGSI · Detalle Historial Proveedor";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .prophdet-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .prophdet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .prophdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .prophdet-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .prophdet-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .prophdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .prophdet-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .prophdet-card-body{
        padding:18px;
      }

      .prophdet-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .prophdet-table-wrap{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .prophdet-table-head th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        vertical-align:middle;
        border:none !important;
        font-size:.78rem;
        text-align:center;
      }

      .table td,
      .table th{
        vertical-align:middle !important;
        font-size:.82rem;
      }

      .table-hover tbody tr:hover{
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

      .prophdet-card .btn{
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        font-weight:900;
      }

      @media (max-width:992px){
        .prophdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .prophdet-header-card{
          min-height:88px;
        }

        .prophdet-title{
          font-size:1.20rem;
        }

        .prophdet-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .prophdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .prophdet-header-overlay::before{
          margin:0;
        }

        .prophdet-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .prophdet-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, grupo=grupo, detalles=detalles_ordenados)

    return render_template_string(BASE, content=content)

#========================================
# Eliminar Historicos
#========================================

@app.route('/cuestionarios_proveedores/historico/<int:grupo_id>/eliminar', methods=['POST'])
@login_required
def cuestionarios_proveedores_historico_eliminar(grupo_id):
    grupo = EvaluacionGrupo.query.get_or_404(grupo_id)
    try:
        db.session.delete(grupo)  # gracias al cascade en EvaluacionGrupo.detalles, se borran los detalles
        db.session.commit()
        flash(f"Se eliminó la evaluación '{grupo.titulo}' y su historial.", "success")
    except Exception as e:
        db.session.rollback()
        print("Error al eliminar evaluación de grupo:", e)
        flash("Ocurrió un error al eliminar la evaluación.", "danger")

    return redirect(url_for('cuestionarios_proveedores_historico'))

#========================================
# Cuestionario de un Proponente Historial
#========================================

@app.route('/cuestionarios_proveedores/historico/ficha/<int:detalle_id>')
@login_required
def cuestionarios_proveedores_ficha_proponente(detalle_id):
    detalle = EvaluacionGrupoDetalle.query.options(
        selectinload(EvaluacionGrupoDetalle.grupo),
        selectinload(EvaluacionGrupoDetalle.cuestionario)
    ).get_or_404(detalle_id)

    # 🔹 Resumen y verificación transparente del puntaje histórico.
    # Nunca modificamos puntajes archivados de forma implícita al abrir una ficha.
    resumen_respuestas = None
    puntaje_recalculado = None
    puntaje_desactualizado = False
    if detalle.cuestionario and detalle.cuestionario.contenido_archivo:
        try:
            resumen_respuestas = obtener_resumen_respuestas_desde_excel_bytes(
                detalle.cuestionario.contenido_archivo
            )
            puntaje_recalculado, _ = calcular_puntaje_desde_excel_bytes(
                detalle.cuestionario.contenido_archivo
            )
            puntaje_desactualizado = abs(float(detalle.puntaje_cuestionario or 0) - puntaje_recalculado) > 0.0049
        except Exception as e:
            print("Error al obtener resumen/puntaje del cuestionario:", e)
            resumen_respuestas = None
            puntaje_recalculado = None

    content = render_template_string("""
    <div class="proficha-shell">

      <!-- CABECERA -->
      <div class="proficha-header-card">
        <div class="proficha-header-overlay">
          <div class="proficha-header-text">
            <h3 class="proficha-title m-0">Ficha de Evaluación del Proponente</h3>
            <div class="proficha-subtitle">
              Detalle completo del proveedor evaluado, incluyendo puntaje de cuestionario, análisis de reputación con IA, resultado consolidado y referencias de respuesta
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="proficha-header-actions">
        <a href="{{ url_for('cuestionarios_proveedores_historico_detalle', grupo_id=detalle.grupo_id) }}"
           class="btn rounded-pill px-5 fw-bold proficha-back-btn">
          ⬅️ Volver a la Evaluación "{{ detalle.grupo.titulo }}"
        </a>
      </div>

      <!-- TARJETA PRINCIPAL -->
      <div class="proficha-card">
        <div class="proficha-card-body">

          <div class="proficha-section-title">Información general de la evaluación</div>

          <div class="row g-3">
            <div class="col-md-6">
              <div class="proficha-info-box">
                <p><strong>Evaluación:</strong> {{ detalle.grupo.titulo }}</p>
                <p><strong>Proveedor:</strong> {{ detalle.nombre_proveedor }}</p>
                {% if detalle.sitio_web %}
                  <p>
                    <strong>Sitio web:</strong>
                    <a href="{{ detalle.sitio_web }}" target="_blank">{{ detalle.sitio_web }}</a>
                  </p>
                {% endif %}
                <p><strong>Fecha de evaluación:</strong> {{ detalle.grupo.fecha_evaluacion.strftime('%Y-%m-%d %H:%M') }}</p>
              </div>
            </div>

            <div class="col-md-6">
              <div class="proficha-score-box">
                <div class="proficha-score-item">
                  <span class="proficha-score-label">Puntaje cuestionario</span>
                  <span class="badge bg-primary px-4 py-2">{{ "%.1f"|format(detalle.puntaje_cuestionario) }}%</span>
                </div>

                <div class="proficha-score-item mt-3">
                  <span class="proficha-score-label">Puntaje total</span>
                  <span class="badge bg-success px-4 py-2">{{ "%.1f"|format(detalle.puntaje_total) }}%</span>
                </div>
              </div>
            </div>

            {% if puntaje_desactualizado %}
            <div class="col-12">
              <div class="alert alert-warning mb-2" role="status">
                <strong>Revisión del puntaje:</strong> el archivo de respuestas arroja ahora
                <strong>{{ "%.2f"|format(puntaje_recalculado) }}%</strong> al reconocer correctamente "N/A".
                El puntaje histórico mostrado arriba se conserva sin modificar por trazabilidad.
                Para guardar un resultado nuevo con el cálculo corregido, elimina la evaluación histórica
                (si corresponde) y vuelve a evaluarla desde Ingreso información.
              </div>
            </div>
            {% endif %}

            <div class="col-12">
              <div class="proficha-section-title">Resultado del cuestionario</div>
              <div class="proficha-text-box">
                {{ detalle.explicacion_cuestionario.replace('\\n', '<br>')|safe }}
              </div>
            </div>

            <div class="col-12">
              <div class="proficha-section-title">Reputación</div>
              <div class="proficha-text-box">
                {{ detalle.explicacion_reputacion.replace('\\n', '<br>')|safe }}
              </div>
            </div>

            {% if detalle.cuestionario %}
            <div class="col-12">
              <div class="proficha-section-title">Archivo fuente</div>
              <div class="proficha-info-box">
                <p class="mb-0">
                  <strong>Archivo original:</strong> {{ detalle.cuestionario.nombre_archivo }}
                </p>
              </div>
            </div>
            {% endif %}

            {% if resumen_respuestas %}
            <div class="col-12">
              <div class="proficha-section-title">Resumen de referencias por tipo de respuesta</div>

              <div class="table-responsive proficha-table-wrap">
                <table class="table table-sm table-bordered align-middle mb-0">
                  <thead class="proficha-table-head">
                    <tr>
                      <th style="width:25%;">Respuesta</th>
                      <th>Referencias (puntos)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {% for tipo, refs in resumen_respuestas.items() %}
                      <tr>
                        <td><strong>{{ tipo }}</strong> <span class="badge bg-secondary ms-2" title="Número de referencias">{{ refs|length }}</span></td>
                        <td>
                          {% if refs and refs|length > 0 %}
                            {{ refs|join(', ') }}
                          {% else %}
                            <span class="text-muted">Sin referencias con esta respuesta</span>
                          {% endif %}
                        </td>
                      </tr>
                    {% endfor %}
                  </tbody>
                </table>
              </div>
            </div>
            {% endif %}

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

      .proficha-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HEADER SGSI MODERNO
      ========================= */
      .proficha-header-card{
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

      .proficha-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .proficha-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .proficha-header-overlay::before{
        content:"⭐";
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

      .proficha-header-text{
        max-width:1200px;
      }

      .proficha-header-text::before{
        content:"SGSI · Ficha de Proveedor";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .proficha-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .proficha-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES
      ========================= */
      .proficha-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .proficha-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .proficha-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .proficha-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      /* =========================
         CARDS
      ========================= */
      .proficha-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .proficha-card-body{
        padding:18px;
      }

      /* =========================
         SECCIONES
      ========================= */
      .proficha-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      /* =========================
         CONTENIDO
      ========================= */
      .proficha-info-box,
      .proficha-text-box,
      .proficha-score-box{
        background:#f8fafc;
        border:1px solid #e5e7eb;
        border-radius:14px;
        padding:8px 7px;
      }

      .proficha-score-item{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
      }

      .proficha-score-label{
        font-weight:800;
        color:#101827;
      }

      /* =========================
         TABLA SGSI
      ========================= */
      .proficha-table-wrap{
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
        overflow:hidden;
      }

      .proficha-table-head th{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        border:none !important;
        font-size:.78rem;
      }

      .table-hover tbody tr:hover{
        background:#eef6ff;
      }

      /* =========================
         BADGES
      ========================= */
      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .btn.rounded-pill{
        border-radius:10px !important;
      }

      /* =========================
         RESPONSIVE
      ========================= */
      @media (max-width:992px){
        .proficha-shell{
          width:98%;
        }

        .proficha-title{
          font-size:1.20rem;
        }

        .proficha-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .proficha-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .proficha-header-overlay::before{
          margin:0;
        }
      }
    </style>
    """, detalle=detalle, resumen_respuestas=resumen_respuestas,
       puntaje_recalculado=puntaje_recalculado, puntaje_desactualizado=puntaje_desactualizado)

    return render_template_string(BASE, content=content)

#========================================
# Eliminar Proponentes cargados
#========================================

@app.route('/cuestionarios_proveedores/eliminar/<int:cuestionario_id>', methods=['POST'])
@login_required
def cuestionarios_proveedores_eliminar(cuestionario_id):
    c = CuestionarioProveedor.query.get_or_404(cuestionario_id)

    try:
        db.session.delete(c)
        db.session.commit()
        flash(f"Se eliminó el cuestionario del proveedor '{c.nombre_proveedor}'.", "success")
    except Exception as e:
        db.session.rollback()
        print("Error al eliminar cuestionario:", e)
        flash("Ocurrió un error al eliminar el cuestionario.", "danger")

    return redirect(url_for('ingreso_informacion_proponente_archivo'))

# ============================================================================================================================================
#                                                       Fin Módulo Cuestionario de Proponentes
# ============================================================================================================================================


# ============================================================================================================================================
#                                                         Módulo Gestión de Proveedores
# ============================================================================================================================================

# =========================
# Modelos
# =========================

class ProveedorEvaluacion(db.Model):
    __tablename__ = 'proveedor_evaluaciones'
    id = db.Column(db.Integer, primary_key=True)
    area_id = db.Column(db.Integer, db.ForeignKey('areas_empresa.id'))
    
    # ---- Info Proveedor
    fecha_eval_seguridad = db.Column(db.String(10))
    nombre_proveedor = db.Column(db.String(255))
    estatus_proveedor = db.Column(db.String(100))
    area = db.relationship('AreaEmpresa', backref='proveedores')  # ✅ añade esto
    responsable_area_nombre = db.Column(db.String(255))
    responsable_area_cargo  = db.Column(db.String(150))
    nombre_cargo_evaluador = db.Column(db.String(255))
    pais_origen = db.Column(db.String(100))
    pais_servicio = db.Column(db.String(100))
    desc_producto_servicio = db.Column(db.Text)
    estado_avance = db.Column(db.String(50))        # Operando / Negociación / Instalaciones
    estado_evaluacion = db.Column(db.String(50))    # Finalizado / Proceso

    # ---- Calificación
    es_transversal = db.Column(db.String(2))        # "Sí"/"No"
    valor_alcance = db.Column(db.Integer)
    es_esencial = db.Column(db.String(2))
    valor_esencial = db.Column(db.Integer)
    tiene_plan_cont = db.Column(db.String(2))
    valor_plan_cont = db.Column(db.Integer)
    existen_alternativas = db.Column(db.String(2))
    valor_alternativas = db.Column(db.Integer)
    existe_plan_migracion = db.Column(db.String(2))
    valor_plan_migracion = db.Column(db.Integer)
    procesa_info_sensible = db.Column(db.String(2))
    valor_info_sensible = db.Column(db.Integer)

    criticidad_pct = db.Column(db.Integer)
    criticidad_texto = db.Column(db.String(50))
    criticidad_color = db.Column(db.String(50))

    # ---- Evaluación (certificaciones / formulario)
    tiene_certificacion = db.Column(db.String(2))
    requiere_formulario = db.Column(db.String(2))
    puntos_certificacion = db.Column(db.Integer)
    puntos_formulario = db.Column(db.Integer)
    calificacion_total = db.Column(db.Integer)
    resultado_evaluacion = db.Column(db.String(50))
    resultado_color = db.Column(db.String(50))
    num_certificaciones   = db.Column(db.Integer)     # cantidad de certs
    nombre_certificaciones = db.Column(db.Text)       # texto con los nombres
    tiene_plan_rec = db.Column(db.String(10))
    valor_plan_rec = db.Column(db.Integer, default=0)

    impacto_falla = db.Column(db.String(10))
    valor_impacto_falla = db.Column(db.Integer, default=0)

    procesa_datos_personales = db.Column(db.String(10))
    valor_datos_personales = db.Column(db.Integer, default=0)

    procesa_info_nube = db.Column(db.String(10))
    valor_nube = db.Column(db.Integer, default=0)

    incluye_sla = db.Column(db.String(10))
    valor_sla = db.Column(db.Integer, default=0)
    

    observaciones = db.Column(db.Text)

    # ---- Relación con evidencias
    evidencias = db.relationship(
        'ProveedorEvidencia',
        back_populates='proveedor',
        cascade='all, delete-orphan'
    )

    # ---- Métodos de cálculo (ajusta a tu lógica actual)
    def calcular_criticidad(self):
        total = (
            int(self.valor_alcance or 0) +
            int(self.valor_esencial or 0) +
            int(self.valor_plan_cont or 0) +
            int(self.valor_plan_rec or 0) +
            int(self.valor_alternativas or 0) +
            int(self.valor_impacto_falla or 0) +
            int(self.valor_plan_migracion or 0) +
            int(self.valor_info_sensible or 0) +
            int(self.valor_datos_personales or 0) +
            int(self.valor_nube or 0) +
            int(self.valor_sla or 0)
        )

        self.criticidad_pct = total

        cfg = ProveedorEvalConfig.get()

        if total <= (cfg.crit_muy_baja_max or 25):
            self.criticidad_texto = 'Criticidad muy baja'
            self.criticidad_color = 'badge-verde-claro'
        elif total <= (cfg.crit_baja_max or 50):
            self.criticidad_texto = 'Criticidad baja'
            self.criticidad_color = 'badge-verde-oscuro'
        elif total <= (cfg.crit_media_max or 75):
            self.criticidad_texto = 'Criticidad media'
            self.criticidad_color = 'badge-amarillo'
        else:
            self.criticidad_texto = 'Criticidad alta'
            self.criticidad_color = 'badge-rojo'

    def calcular_certificados(self):
        # Cargar parámetros configurables
        cfg = ProveedorEvalConfig.get()

        # 1) Puntos por certificación, según número de certificaciones
        #    Solo si tiene_certificacion == 'Sí' y cumple la cantidad mínima configurada
        num_certs = self.num_certificaciones or 0

        if self.tiene_certificacion == 'Sí' and num_certs >= (cfg.min_certificaciones_aprobado or 1):
            pt_cert = 100
        else:
            pt_cert = 0

        self.puntos_certificacion = pt_cert

        # 2) ¿requiere formulario?
        self.requiere_formulario = 'No' if pt_cert == 100 else 'Sí'

        # si se otorgan todos los puntos por certificación, el formulario puede quedar en 0 (o lo que tengas)
        if pt_cert == 100:
            self.puntos_formulario = self.puntos_formulario or 0

        total = pt_cert + (self.puntos_formulario or 0)
        self.calificacion_total = total

        # 3) Clasificación según rangos configurados
        if total >= (cfg.pct_aprob_min or 81):
            self.resultado_evaluacion = 'Aprobado'
            self.resultado_color = 'badge-aprobado'
        elif total >= (cfg.pct_revision_min or 61):
            self.resultado_evaluacion = 'En revisión'
            self.resultado_color = 'badge-revision'
        else:
            self.resultado_evaluacion = 'No Aprobado'
            self.resultado_color = 'badge-noaprob'

class ProveedorEvidencia(db.Model):
    __tablename__ = 'proveedor_evidencias'  # <- nombre de tabla para evidencias
    id = db.Column(db.Integer, primary_key=True)

    # FK debe apuntar al __tablename__ exacto definido arriba
    proveedor_id = db.Column(
        db.Integer,
        db.ForeignKey('proveedor_evaluaciones.id'),
        nullable=False
    )

    filename = db.Column(db.String(255), nullable=False)       # nombre guardado en disco
    original_name = db.Column(db.String(255), nullable=False)  # como lo subió el usuario
    mime = db.Column(db.String(100), default='application/pdf')
    size = db.Column(db.Integer)  # en bytes

    proveedor = db.relationship('ProveedorEvaluacion', back_populates='evidencias')

