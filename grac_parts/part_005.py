@app.route('/partes_interesadas/detalle/<int:id>')
@login_required
def parte_interesada_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Partes Interesadas"):
            flash("No tiene permiso para ver el detalle del registro.", "danger")
            return redirect(url_for('partes_interesadas_matriz'))
        read_only = False

    it = ParteInteresada.query.get_or_404(id)

    html = """
    <div class="pid-shell">

      <div class="pid-header-card">
        <div class="pid-header-overlay">
          <div class="pid-header-text">
            <h3 class="pid-title m-0">Detalle de Parte Interesada</h3>
            <div class="pid-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="pid-header-actions">
        <a href="{{ url_for('partes_interesadas_matriz') }}"
           class="btn rounded-pill px-4 fw-bold pid-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('parte_interesada_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold"
             onclick="showLoader()">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="pid-card">
        <div class="pid-card-body">

          <div class="pid-section">
            <div class="pid-section-title">Información principal</div>
            <div class="row g-3">
              <div class="col-md-8">
                <div class="pid-field">
                  <div class="pid-label">Parte Interesada</div>
                  <div class="pid-value pid-value-lg">{{ it.parte_interesada or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="pid-field">
                  <div class="pid-label">Fecha de Revisión</div>
                  <div class="pid-value">{{ format_fecha_partes(it.fecha_revision) }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="pid-section">
            <div class="pid-section-title">Análisis del registro</div>
            <div class="row g-3">
              <div class="col-md-12">
                <div class="pid-field">
                  <div class="pid-label">Necesidades / Expectativas</div>
                  <div class="pid-value">{{ it.necesidades_expectativas or '—' }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="pid-field">
                  <div class="pid-label">Requisitos Aplicables</div>
                  <div class="pid-value">{{ it.requisitos_aplicables or '—' }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="pid-section">
            <div class="pid-section-title">Evidencias</div>
            {% if it.evidencias %}
              <div class="pid-ev-grid">
                {% for ev in it.evidencias %}
                  <div class="pid-ev-card">
                    <div class="pid-ev-left">
                      <div class="pid-ev-icon">PDF</div>
                      <div class="pid-ev-meta">
                        <a href="{{ url_for('partes_evidencia_view', evi_id=ev.id, next='partes_interesadas_matriz') }}"
                           class="pid-ev-name">
                          {{ ev.original_name }}
                        </a>
                        <div class="pid-ev-size">
                          {{ ((ev.size or 0) / 1024)|round(1) }} KB
                        </div>
                      </div>
                    </div>
                    <div class="pid-ev-actions">
                      <a href="{{ url_for('partes_evidencia_view', evi_id=ev.id, next='partes_interesadas_matriz') }}"
                         class="btn btn-outline-primary btn-sm rounded-pill px-3">
                        Ver PDF
                      </a>
                    </div>
                  </div>
                {% endfor %}
              </div>
            {% else %}
              <div class="pid-empty-box">
                No hay evidencias cargadas para este registro.
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

      .pid-shell{
        width:96%;
        max-width:1250px;
        margin:10px auto 24px auto;
      }

      .pid-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .pid-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
        pointer-events:none;
      }

      .pid-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .pid-header-overlay::before{
        content:"👥";
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
      }

      .pid-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .pid-header-text::before{
        content:"SGSI · Detalle de Parte Interesada";
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

      .pid-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .pid-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      .pid-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .pid-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .pid-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .pid-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .pid-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .pid-card-body{
        padding:16px 18px;
      }

      .pid-section{
        margin-bottom:14px;
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .pid-section:last-child{
        margin-bottom:0;
      }

      .pid-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      .pid-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        min-height:100%;
      }

      .pid-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .pid-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .pid-value-lg{
        font-size:.90rem;
        font-weight:900;
        color:#0f172a;
        line-height:1.35;
      }

      .pid-ev-grid{
        display:grid;
        gap:10px;
      }

      .pid-ev-card{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:10px 12px;
        box-shadow:0 6px 14px rgba(15,23,42,.08);
        flex-wrap:wrap;
      }

      .pid-ev-left{
        display:flex;
        align-items:center;
        gap:7px;
        min-width:0;
      }

      .pid-ev-icon{
        width:32px;
        height:32px;
        min-width:32px;
        border-radius:11px;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:.74rem;
        font-weight:900;
        box-shadow:0 6px 14px rgba(211,47,47,.20);
      }

      .pid-ev-meta{
        min-width:0;
      }

      .pid-ev-name{
        display:block;
        font-size:.78rem;
        font-weight:900;
        color:#1d4ed8;
        text-decoration:none;
        word-break:break-word;
      }

      .pid-ev-name:hover{
        text-decoration:underline;
      }

      .pid-ev-size{
        font-size:.70rem;
        color:#475569;
        margin-top:2px;
      }

      .pid-empty-box{
        background:rgba(255,255,255,.75);
        border:1px dashed #cfd8e3;
        border-radius:14px;
        padding:8px 7px;
        text-align:center;
        color:#475569;
        font-size:.80rem;
      }

      @media (max-width:992px){
        .pid-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .pid-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .pid-title{
          font-size:1.22rem;
        }

        .pid-subtitle{
          font-size:.74rem;
        }

        .pid-card-body{
          padding:8px 7px;
        }

        .pid-section{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .pid-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .pid-header-overlay::before{
          margin-right:0;
        }

        .pid-title{
          font-size:1.12rem;
        }

        .pid-subtitle{
          font-size:.72rem;
        }

        .pid-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        it=it,
        read_only=read_only,
        format_fecha_partes=format_fecha_partes
    )
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Editar
# ==========================
@app.route('/partes_interesadas/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def parte_interesada_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede editar registros.", "danger")
        return redirect(url_for('partes_interesadas_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Partes Interesadas"):
        flash("No tiene permiso para editar registros.", "danger")
        return redirect(url_for('partes_interesadas_matriz'))

    it = ParteInteresada.query.get_or_404(id)

    if request.method == 'POST':
        parte_interesada = (request.form.get('parte_interesada') or '').strip()
        necesidades = (request.form.get('necesidades_expectativas') or '').strip()
        requisitos = (request.form.get('requisitos_aplicables') or '').strip()
        fecha_str = (request.form.get('fecha_revision') or '').strip()

        if not all([parte_interesada, necesidades, requisitos]):
            flash("Campos obligatorios: Parte interesada, Necesidades/Expectativas y Requisitos aplicables.", "danger")
            return redirect(url_for('parte_interesada_edit', id=id))

        fecha_revision = None
        if fecha_str:
            try:
                fecha_revision = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de revisión inválida.", "danger")
                return redirect(url_for('parte_interesada_edit', id=id))

        it.parte_interesada = parte_interesada
        it.necesidades_expectativas = necesidades
        it.requisitos_aplicables = requisitos
        it.fecha_revision = fecha_revision

        files = request.files.getlist('evidencias')
        for f in files:
            if not f or not f.filename:
                continue
            if not is_allowed_pdf(f.filename):
                flash(f"Archivo no permitido (solo PDF): {f.filename}", "danger")
                continue

            store_name = unique_store_name(f.filename)
            path = os.path.join(app.config['UPLOAD_PARTES_INTERESADAS_DIR'], store_name)
            f.save(path)

            ev = ParteInteresadaEvidencia(
                registro=it,
                filename=store_name,
                original_name=secure_filename(f.filename),
                mime='application/pdf',
                size=os.path.getsize(path)
            )
            db.session.add(ev)

        db.session.commit()
        flash("Registro actualizado.", "success")
        return redirect(url_for('partes_interesadas_matriz'))

    fecha_value = ""
    if getattr(it, "fecha_revision", None):
        try:
            fecha_value = it.fecha_revision.strftime("%Y-%m-%d")
        except Exception:
            fecha_value = ""

    html = """
    <div class="partesedit-shell">

      <div class="partesedit-header-card">
        <div class="partesedit-header-overlay">
          <div class="partesedit-header-text">
            <h3 class="partesedit-title m-0">Editar Parte Interesada</h3>
            <div class="partesedit-subtitle">
              Actualización de la información, necesidades, requisitos aplicables y evidencias de la parte interesada
            </div>
          </div>
        </div>
      </div>

      <div class="partesedit-header-actions">
        <a href="{{ url_for('partes_interesadas_matriz') }}"
           class="btn rounded-pill px-4 fw-bold partesedit-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="partesedit-card">
        <div class="partesedit-card-body">
          <form method="post" enctype="multipart/form-data">
            <div class="row g-3">

              <div class="col-md-6">
                <label class="form-label">Parte Interesada</label>
                <input name="parte_interesada" class="form-control" required value="{{ it.parte_interesada }}">
              </div>

              <div class="col-md-6">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date" name="fecha_revision" class="form-control" value="{{ fecha_value }}">
              </div>

              <div class="col-md-12">
                <label class="form-label">Necesidades / Expectativas</label>
                <textarea name="necesidades_expectativas" class="form-control" rows="2" required>{{ it.necesidades_expectativas }}</textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Requisitos Aplicables</label>
                <textarea name="requisitos_aplicables" class="form-control" rows="2" required>{{ it.requisitos_aplicables }}</textarea>
              </div>

              <div class="col-lg-6">
                <label class="form-label">Agregar nuevas evidencias PDF</label>

                <div class="partesedit-upload-box">
                  <div class="partesedit-upload-icon">📎</div>
                  <div class="partesedit-upload-title">Adjuntar nuevos archivos</div>
                  <div class="partesedit-upload-subtitle2">
                    Los PDFs actuales se conservan. Aquí solo agregarás evidencias nuevas.
                  </div>

                  <div class="mt-3">
                    <input
                      type="file"
                      id="evidencias"
                      name="evidencias"
                      accept=".pdf"
                      multiple
                      class="form-control partesedit-file-input"
                      onchange="acumularEvidencias(this)">
                  </div>

                  <div class="mt-3">
                    <div id="lista_evidencias_nuevas" class="partesedit-files-grid"></div>
                  </div>
                </div>
              </div>

              <div class="col-lg-6">
                <label class="form-label">Evidencias actuales</label>

                <div class="partesedit-current-box">
                  {% if it.evidencias %}
                    <div class="partesedit-files-grid">
                      {% for ev in it.evidencias %}
                        <div id="ev-row-{{ ev.id }}" class="partesedit-file-card-current">
                          <div class="partesedit-file-left">
                            <div class="partesedit-file-pdf">PDF</div>
                            <div class="partesedit-file-meta">
                              <div class="partesedit-file-name" title="{{ ev.original_name }}">
                                {{ ev.original_name }}
                              </div>
                              <div class="partesedit-file-status">
                                Archivo cargado · {{ ((ev.size or 0)/1024)|round(1) }} KB
                              </div>
                            </div>
                          </div>

                          <div class="partesedit-file-actions">
                            <a href="{{ url_for('partes_evidencia_view', evi_id=ev.id, next='partes_interesadas_matriz') }}"
                               class="btn btn-sm btn-outline-primary rounded-pill px-3">
                              Ver
                            </a>

                            <button type="button"
                                    class="btn btn-sm btn-outline-danger rounded-pill px-3"
                                    onclick="eliminarEvidenciaParte({{ ev.id }})">
                              Eliminar
                            </button>
                          </div>
                        </div>
                      {% endfor %}
                    </div>
                  {% else %}
                    <div class="text-muted small partesedit-empty-box">
                      No hay evidencias cargadas para este registro.
                    </div>
                  {% endif %}
                </div>
              </div>

            </div>

            <div class="partesedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>
              <a href="{{ url_for('partes_interesadas_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold partesedit-cancel-btn">
                Cancelar
              </a>
            </div>
          </form>
        </div>
      </div>
    </div>

    <script>
      async function eliminarEvidenciaParte(eviId) {
        if (!confirm('¿Desea eliminar esta evidencia?')) return;

        try {
          const resp = await fetch(`/partes_evidencia/${eviId}/delete`, {
            method: 'POST',
            headers: {
              'X-Requested-With': 'XMLHttpRequest'
            }
          });

          if (resp.ok) {
            const row = document.getElementById(`ev-row-${eviId}`);
            if (row) row.remove();
          } else {
            alert('No se pudo eliminar la evidencia.');
          }
        } catch (err) {
          console.error(err);
          alert('Error de conexión al eliminar la evidencia.');
        }
      }

      let evidenciasBufferDT = new DataTransfer();

      function formatFileSize(bytes) {
        if (!bytes || bytes <= 0) return '0 KB';
        const kb = bytes / 1024;
        if (kb < 1024) return `${kb.toFixed(1)} KB`;
        return `${(kb / 1024).toFixed(2)} MB`;
      }

      function renderListaEvidencias() {
        const cont = document.getElementById('lista_evidencias_nuevas');
        if (!cont) return;
        cont.innerHTML = '';

        if (evidenciasBufferDT.files.length === 0) {
          cont.innerHTML = `
            <div class="text-muted small partesedit-empty-box">
              No hay archivos nuevos seleccionados
            </div>
          `;
          return;
        }

        for (let i = 0; i < evidenciasBufferDT.files.length; i++) {
          const f = evidenciasBufferDT.files[i];
          const card = document.createElement('div');
          card.className = 'partesedit-file-card-new';
          card.innerHTML = `
            <div class="partesedit-file-left">
              <div class="partesedit-file-pdf">PDF</div>
              <div class="partesedit-file-meta">
                <div class="partesedit-file-name" title="${f.name}">${f.name}</div>
                <div class="partesedit-file-status">Listo para cargar · ${formatFileSize(f.size)}</div>
              </div>
            </div>

            <button type="button"
                    class="btn btn-sm btn-outline-danger rounded-pill px-3"
                    onclick="removeEvidenciaFromBuffer(${i})">
              Quitar
            </button>
          `;
          cont.appendChild(card);
        }
      }

      function acumularEvidencias(inputEl) {
        for (const f of inputEl.files) {
          const yaExiste = Array.from(evidenciasBufferDT.files).some(
            x => x.name === f.name && x.size === f.size && x.lastModified === f.lastModified
          );
          if (!yaExiste) evidenciasBufferDT.items.add(f);
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

      window.addEventListener('DOMContentLoaded', renderListaEvidencias);
    </script>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .partesedit-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI UNIFICADO
      ========================== */
      .partesedit-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .partesedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .partesedit-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .partesedit-header-overlay::before{
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
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .partesedit-header-text::before{
        content:"SGSI · Edición Parte Interesada";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .partesedit-title{
        color:#fff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
      }

      .partesedit-subtitle{
        font-size:.78rem;
        opacity:.9;
      }

      /* =========================
         ACCIONES
      ========================== */
      .partesedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .partesedit-back-btn{
        background:#fff;
        border:1px solid #cfd8e3;
        border-radius:10px;
        padding:8px 18px;
        font-weight:800;
      }

      /* =========================
         CARD
      ========================== */
      .partesedit-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .partesedit-card-body{
        padding:16px 18px;
      }

      /* =========================
         FORMULARIO
      ========================== */
      .partesedit-card .form-label{
        font-weight:800;
        font-size:.78rem;
        margin-bottom:4px;
      }

      .partesedit-card .form-control,
      .partesedit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:36px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .partesedit-card textarea{
        min-height:70px;
      }

      /* =========================
         UPLOAD
      ========================== */
      .partesedit-upload-box,
      .partesedit-current-box{
        border-radius:16px;
        padding:8px 7px;
        border:1px solid #dbe6f4;
        background:#fff;
      }

      .partesedit-upload-box{
        border:2px dashed #7fb0e6;
        text-align:center;
      }

      .partesedit-upload-icon{
        width:52px;
        height:52px;
        margin:auto;
        border-radius:14px;
        background:linear-gradient(135deg,#062b55,#1d5fae);
        color:#fff;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.4rem;
      }

      .partesedit-files-grid{
        display:grid;
        gap:10px;
      }

      .partesedit-file-card-current,
      .partesedit-file-card-new{
        display:flex;
        justify-content:space-between;
        align-items:center;
        padding:10px;
        border-radius:12px;
        border:1px solid #dbe6f4;
        background:#fff;
      }

      .partesedit-file-pdf{
        width:36px;
        height:36px;
        border-radius:10px;
        background:#b91c1c;
        color:#fff;
        display:flex;
        align-items:center;
        justify-content:center;
        font-weight:900;
      }

      /* =========================
         BOTONES
      ========================== */
      .partesedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .partesedit-bottom-actions .btn{
        border-radius:10px;
        padding:8px 20px;
        font-size:.8rem;
        font-weight:900;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media(max-width:992px){
        .partesedit-shell{ width:98%; }

        .partesedit-header-card{
          min-height:88px;
        }

        .partesedit-title{
          font-size:1.2rem;
        }

        .partesedit-card-body{
          padding:8px 7px;
        }
      }

      @media(max-width:768px){
        .partesedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .partesedit-header-overlay::before{
          margin:0;
        }

        .partesedit-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(html, it=it, fecha_value=fecha_value)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Eliminar registro
# ==========================
@app.route('/partes_interesadas/<int:id>/delete', methods=['POST'])
@login_required
def parte_interesada_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros.", "danger")
        return redirect(url_for('partes_interesadas_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Partes Interesadas"):
        flash("No tiene permiso para eliminar registros.", "danger")
        return redirect(url_for('menu'))

    it = ParteInteresada.query.get_or_404(id)

    evs = list(getattr(it, 'evidencias', []) or [])
    for ev in evs:
        try:
            path = os.path.join(app.config['UPLOAD_PARTES_INTERESADAS_DIR'], ev.filename)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        db.session.delete(ev)

    db.session.delete(it)
    db.session.commit()
    flash("Registro eliminado.", "success")
    return redirect(url_for('partes_interesadas_matriz'))


# ==========================
# Eliminar evidencia individual
# ==========================
@app.route('/partes_evidencia/<int:evi_id>/delete', methods=['POST'])
@login_required
def partes_evidencia_delete(evi_id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar evidencias.", "danger")
        return redirect(url_for('partes_interesadas_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Partes Interesadas"):
        flash("No tiene permiso para eliminar evidencias.", "danger")
        return redirect(url_for('menu'))

    ev = ParteInteresadaEvidencia.query.get_or_404(evi_id)
    registro_id = ev.registro_id

    try:
        path = os.path.join(app.config['UPLOAD_PARTES_INTERESADAS_DIR'], ev.filename)
        if os.path.exists(path):
            os.remove(path)
    except Exception as ex:
        print("Error eliminando archivo físico de partes interesadas:", ex)

    db.session.delete(ev)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return ('', 204)

    flash("Evidencia eliminada correctamente.", "success")
    return redirect(url_for('parte_interesada_edit', id=registro_id))

# ==========================================================================================================================================
#                                                               Fin Módulo Partes Interesadas
# ==========================================================================================================================================


# =========================================================================================================================================
#                                                               Módulo de Contexto Interno
# =========================================================================================================================================

class ContextoInterno(db.Model):
    __tablename__ = 'contexto_interno'

    id = db.Column(db.Integer, primary_key=True)

    factor_interno   = db.Column(db.String(200), nullable=False)   # Factor Interno
    descripcion      = db.Column(db.Text, nullable=False)          # Descripción
    impacto_sgsi     = db.Column(db.Text, nullable=False)          # Impacto en el SGSI
    fortalezas       = db.Column(db.Text, nullable=True)           # Fortalezas
    debilidades      = db.Column(db.Text, nullable=True)           # Debilidades
    fecha_revision   = db.Column(db.Date, nullable=True)           # Fecha de Revisión

def format_fecha_contexto(valor):
    if not valor:
        return '—'
    try:
        return valor.strftime('%Y-%m-%d')
    except Exception:
        return str(valor)

def resumir_contexto_texto(valor, limite=140):
    if not valor:
        return '—'
    txt = str(valor).strip()
    if len(txt) <= limite:
        return txt
    return txt[:limite].rstrip() + '...'


# ==========================
# ENTRADA DIRECTA AL MÓDULO
# ==========================
@app.route('/contexto_interno_menu')
@login_required
def contexto_interno_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Contexto Interno"):
        flash("No tiene permiso para acceder al módulo de contexto interno.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('contexto_interno_matriz'))


# ==========================
# Agregar Contexto Interno
# ==========================
@app.route('/contexto_interno/new', methods=['GET', 'POST'])
@login_required
def contexto_interno_new():

    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('contexto_interno_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Contexto Interno"):
        flash("No tiene permiso para agregar resgitro de contexto interno.", "danger")
        return redirect(url_for('contexto_interno_matriz'))

    if request.method == 'POST':
        factor_interno = (request.form.get('factor_interno') or '').strip()
        descripcion    = (request.form.get('descripcion') or '').strip()
        impacto_sgsi   = (request.form.get('impacto_sgsi') or '').strip()
        fortalezas     = (request.form.get('fortalezas') or '').strip()
        debilidades    = (request.form.get('debilidades') or '').strip()
        fecha_str      = (request.form.get('fecha_revision') or '').strip()

        fecha_revision = None
        if fecha_str:
            try:
                fecha_revision = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de revisión inválida.", "danger")
                return redirect(url_for('contexto_interno_new'))

        if not (factor_interno and descripcion and impacto_sgsi):
            flash("Campos obligatorios: Factor Interno, Descripción e Impacto en el SGSI.", "danger")
            return redirect(url_for('contexto_interno_new'))

        it = ContextoInterno(
            factor_interno=factor_interno,
            descripcion=descripcion,
            impacto_sgsi=impacto_sgsi,
            fortalezas=fortalezas,
            debilidades=debilidades,
            fecha_revision=fecha_revision
        )
        db.session.add(it)
        db.session.commit()
        flash("Contexto interno registrado.", "success")
        return redirect(url_for('contexto_interno_matriz'))

    html = """
    <div class="ctxint-shell">

      <div class="ctxint-header-card">
        <div class="ctxint-header-overlay">
          <div class="ctxint-header-text">
            <h3 class="ctxint-title m-0">Agregar Contexto Interno</h3>
            <div class="ctxint-subtitle">
              Registro de factores internos que influyen en el Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="ctxint-header-actions">
        <a href="{{ url_for('contexto_interno_matriz') }}"
           class="btn rounded-pill px-4 fw-bold ctxint-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="ctxint-card">
        <div class="ctxint-card-body">
          <form method="post">
            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Factor Interno</label>
                <input name="factor_interno" class="form-control" required>
              </div>

              <div class="col-md-8">
                <label class="form-label">Descripción</label>
                <textarea name="descripcion" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Impacto en el SGSI</label>
                <textarea name="impacto_sgsi" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Fortalezas</label>
                <textarea name="fortalezas" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Debilidades</label>
                <textarea name="debilidades" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date" name="fecha_revision" class="form-control">
              </div>

            </div>

            <div class="ctxint-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>

              <a href="{{ url_for('contexto_interno_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold ctxint-cancel-btn">
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

      .ctxint-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      .ctxint-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .ctxint-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
        pointer-events:none;
      }

      .ctxint-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .ctxint-header-overlay::before{
        content:"🏢";
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
      }

      .ctxint-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .ctxint-header-text::before{
        content:"SGSI · Contexto Interno";
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

      .ctxint-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .ctxint-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      .ctxint-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .ctxint-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxint-header-actions .btn-primary,
      .ctxint-header-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxint-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxint-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .ctxint-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxint-card-body{
        padding:16px 18px;
      }

      .ctxint-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .ctxint-card .form-control,
      .ctxint-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
        padding-top:5px;
        padding-bottom:5px;
      }

      .ctxint-card textarea{
        min-height:70px;
        resize:vertical;
      }

      .ctxint-card .form-control:focus,
      .ctxint-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .ctxint-card .row{
        row-gap:10px;
      }

      .ctxint-card .mb-3{
        margin-bottom:.70rem !important;
      }

      .ctxint-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .ctxint-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxint-bottom-actions .btn-primary,
      .ctxint-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxint-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .ctxint-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxint-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .ctxint-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxint-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .ctxint-title{
          font-size:1.22rem;
        }

        .ctxint-subtitle{
          font-size:.74rem;
        }

        .ctxint-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .ctxint-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .ctxint-header-overlay::before{
          margin-right:0;
        }

        .ctxint-title{
          font-size:1.12rem;
        }

        .ctxint-subtitle{
          font-size:.72rem;
        }

        .ctxint-bottom-actions .btn,
        .ctxint-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Matriz Contexto Interno
# ==========================
CONTEXTO_INTERNO_MATRIZ_MIN_COLS = [
    "factor_interno",
    "descripcion",
    "impacto_sgsi",
    "fecha_revision",
]

@app.route('/contexto_interno_matriz', methods=['GET'])
@login_required
def contexto_interno_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Contexto Interno"):
            flash("No tiene permiso para ver los contextos internos.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    items = ContextoInterno.query.order_by(ContextoInterno.id.desc()).all()

    html = """
    <div class="ctxintmat-shell">

      <div class="ctxintmat-header-card">
        <div class="ctxintmat-header-overlay">
          <div class="ctxintmat-header-text">
            <h3 class="ctxintmat-title m-0">Contexto Interno</h3>
            <div class="ctxintmat-subtitle">
              Visualización resumida de los factores internos que afectan el Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="ctxintmat-header-actions">
        {% if not read_only %}
          <a href="{{ url_for('contexto_interno_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            ⨁ Agregar Contexto Interno
          </a>
        {% endif %}

      </div>

      <div class="ctxintmat-card">
        <div class="ctxintmat-topbar">
          <div>
            <h5 class="ctxintmat-top-title mb-1">Resumen de registros</h5>
            <div class="ctxintmat-top-note">
              La matriz presenta únicamente los campos más importantes. Para revisar el registro completo usa el botón <strong>Ver detalle</strong>.
            </div>
          </div>
          <div class="ctxintmat-counter-badge">
            Total registros: {{ items|length }}
          </div>
        </div>

        <div class="ctxintmat-card-body">
          <div class="ctxintmat-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-hover align-middle ctxintmat-table mb-0">
                <colgroup>
                  <col style="width: 22%;">
                  <col style="width: 28%;">
                  <col style="width: 28%;">
                  <col style="width: 10%;">
                  <col style="width: 12%;">
                </colgroup>

                <thead>
                  <tr>
                    <th>Factor Interno</th>
                    <th>Descripción</th>
                    <th>Impacto en el SGSI</th>
                    <th>Fecha de Revisión</th>
                    <th>Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  {% for it in items %}
                    <tr>
                      <td class="ctxintmat-cell-main">
                        <div class="ctxintmat-main-text">{{ it.factor_interno or '—' }}</div>
                      </td>

                      <td>{{ resumir_contexto_texto(it.descripcion, 150) }}</td>

                      <td>{{ resumir_contexto_texto(it.impacto_sgsi, 150) }}</td>

                      <td class="text-center">
                        {{ format_fecha_contexto(it.fecha_revision) }}
                      </td>

                      <td class="text-center">
                        <div class="ctxintmat-actions-wrap">
                          <a href="{{ url_for('contexto_interno_detalle', id=it.id) }}"
                             class="btn btn-info btn-sm rounded-pill px-3 fw-bold text-white">
                            Ver detalle
                          </a>

                          {% if not read_only %}
                            <a href="{{ url_for('contexto_interno_edit', id=it.id) }}"
                               class="btn btn-warning btn-sm rounded-pill px-3 fw-bold">
                              Editar
                            </a>

                            <a href="{{ url_for('contexto_interno_delete', id=it.id) }}"
                               class="btn btn-danger btn-sm rounded-pill px-3 fw-bold"
                               onclick="return confirm('¿Eliminar este registro?');">
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
                      <td colspan="5" class="text-center text-muted py-5">
                        Sin registros
                      </td>
                    </tr>
                  {% endif %}
                </tbody>
              </table>
            </div>
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

      .ctxintmat-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .ctxintmat-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .ctxintmat-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
        pointer-events:none;
      }

      .ctxintmat-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .ctxintmat-header-overlay::before{
        content:"🏢";
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
      }

      .ctxintmat-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .ctxintmat-header-text::before{
        content:"SGSI · Contexto Interno";
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

      .ctxintmat-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .ctxintmat-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      .ctxintmat-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .ctxintmat-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxintmat-header-actions .btn-primary,
      .ctxintmat-header-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxintmat-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxintmat-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .ctxintmat-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxintmat-topbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:14px 16px 0 16px;
        flex-wrap:wrap;
      }

      .ctxintmat-top-title{
        color:#0f172a;
        font-weight:950;
        font-size:.94rem;
      }

      .ctxintmat-top-note{
        color:#475569;
        font-size:.78rem;
        margin-top:3px;
      }

      .ctxintmat-counter-badge{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:7px 14px;
        font-size:.78rem;
        box-shadow:0 8px 16px rgba(15,23,42,.16);
      }

      .ctxintmat-card-body{
        padding:12px 16px 16px 16px;
      }

      .ctxintmat-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:rgba(255,255,255,.99);
      }

      .ctxintmat-table{
        min-width:1200px;
        margin-bottom:0;
        table-layout:fixed;
        border-collapse:separate;
        border-spacing:0;
      }

      .ctxintmat-table th,
      .ctxintmat-table td{
        white-space:normal;
        word-break:break-word;
        vertical-align:top;
        font-size:.68rem;
        padding:9px 8px;
      }

      .ctxintmat-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border-right:1px solid rgba(255,255,255,.28);
      }

      .ctxintmat-table td{
        color:#101827;
        border-right:1px solid #dce6f3;
        border-bottom:1px solid #dce6f3;
        background:#ffffff;
      }

      .ctxintmat-table tbody tr:nth-child(even) td{
        background:#f8fbff;
      }

      .ctxintmat-table tbody tr:hover td{
        background:#eef6ff;
      }

      .ctxintmat-cell-main .ctxintmat-main-text{
        font-weight:900;
        color:#0f172a;
        line-height:1.35;
      }

      .ctxintmat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .ctxintmat-actions-wrap .btn,
      .ctxintmat-table .btn{
        min-width:86px;
        min-height:28px;
        border-radius:999px !important;
        padding:4px 12px !important;
        font-size:.70rem;
        font-weight:900;
        display:inline-flex;
        align-items:center;
        justify-content:center;
      }

      .ctxintmat-table .btn-info{
        background:#087ab8;
        border:none;
        color:#fff;
      }

      .ctxintmat-table .btn-warning{
        background:#c76b00;
        border:none;
        color:#0b1220;
      }

      .ctxintmat-table .btn-danger{
        background:#b91c1c;
        border:none;
        color:#fff;
      }

      .ctxintmat-table .btn-success{
        background:#087c3d;
        border:none;
        color:#fff;
      }

      .ctxintmat-table-wrap::-webkit-scrollbar{
        height:11px;
        width:11px;
      }

      .ctxintmat-table-wrap::-webkit-scrollbar-track{
        background:#dbe4f0;
        border-radius:12px;
      }

      .ctxintmat-table-wrap::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,#5aa3ea,#3f86d6);
        border-radius:12px;
        border:2px solid #dbe4f0;
      }

      .ctxintmat-table-wrap{
        scrollbar-width:thin;
        scrollbar-color:#3f86d6 #dbe4f0;
      }

      @media (max-width:992px){
        .ctxintmat-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxintmat-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .ctxintmat-card-body{
          padding:12px 14px 14px 14px;
        }

        .ctxintmat-topbar{
          padding:12px 14px 0 14px;
        }

        .ctxintmat-title{
          font-size:1.22rem;
        }

        .ctxintmat-subtitle{
          font-size:.74rem;
        }
      }

      @media (max-width:768px){
        .ctxintmat-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .ctxintmat-header-overlay::before{
          margin-right:0;
        }

        .ctxintmat-title{
          font-size:1.12rem;
        }

        .ctxintmat-subtitle{
          font-size:.72rem;
        }

        .ctxintmat-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        resumir_contexto_texto=resumir_contexto_texto,
        format_fecha_contexto=format_fecha_contexto
    )
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Detalle Contexto Interno
# ==========================
@app.route('/contexto_interno/detalle/<int:id>')
@login_required
def contexto_interno_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Contexto Interno"):
            flash("No tiene permiso para ver el detalle del contexto interno.", "danger")
            return redirect(url_for('contexto_interno_matriz'))
        read_only = False

    it = ContextoInterno.query.get_or_404(id)

    html = """
    <div class="ctxintd-shell">

      <div class="ctxintd-header-card">
        <div class="ctxintd-header-overlay">
          <div class="ctxintd-header-text">
            <h3 class="ctxintd-title m-0">Detalle — Contexto Interno</h3>
            <div class="ctxintd-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="ctxintd-header-actions">
        <a href="{{ url_for('contexto_interno_matriz') }}"
           class="btn rounded-pill px-4 fw-bold ctxintd-back-btn">
          ⬅ Volver a la Matriz
        </a>


        {% if not read_only %}
          <a href="{{ url_for('contexto_interno_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="ctxintd-card">
        <div class="ctxintd-card-body">

          <div class="ctxintd-section">
            <div class="ctxintd-section-title">Información principal</div>
            <div class="row g-3">
              <div class="col-md-8">
                <div class="ctxintd-field">
                  <div class="ctxintd-label">Factor Interno</div>
                  <div class="ctxintd-value ctxintd-value-lg">{{ it.factor_interno or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="ctxintd-field">
                  <div class="ctxintd-label">Fecha de Revisión</div>
                  <div class="ctxintd-value">{{ format_fecha_contexto(it.fecha_revision) }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="ctxintd-field">
                  <div class="ctxintd-label">Descripción</div>
                  <div class="ctxintd-value">{{ it.descripcion or '—' }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="ctxintd-field">
                  <div class="ctxintd-label">Impacto en el SGSI</div>
                  <div class="ctxintd-value">{{ it.impacto_sgsi or '—' }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="ctxintd-section">
            <div class="ctxintd-section-title">Análisis interno</div>
            <div class="row g-3">
              <div class="col-md-6">
                <div class="ctxintd-field">
                  <div class="ctxintd-label">Fortalezas</div>
                  <div class="ctxintd-value">{{ it.fortalezas or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="ctxintd-field">
                  <div class="ctxintd-label">Debilidades</div>
                  <div class="ctxintd-value">{{ it.debilidades or '—' }}</div>
                </div>
              </div>
            </div>
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

      .ctxintd-shell{
        width:96%;
        max-width:1250px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI UNIFICADO
      ========================== */
      .ctxintd-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .ctxintd-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .ctxintd-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .ctxintd-header-overlay::before{
        content:"🏢";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .ctxintd-header-text::before{
        content:"SGSI · Contexto Interno (Detalle)";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .ctxintd-title{
        color:#fff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
      }

      .ctxintd-subtitle{
        font-size:.78rem;
        opacity:.9;
      }

      /* =========================
         ACCIONES
      ========================== */
      .ctxintd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .ctxintd-back-btn{
        background:#fff;
        border:1px solid #cfd8e3;
        border-radius:10px;
        padding:8px 18px;
        font-weight:800;
      }

      /* =========================
         CARD
      ========================== */
      .ctxintd-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxintd-card-body{
        padding:16px 18px;
      }

      /* =========================
         SECCIONES
      ========================== */
      .ctxintd-section{
        margin-bottom:14px;
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .ctxintd-section:last-child{
        margin-bottom:0;
      }

      .ctxintd-section-title{
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
      ========================== */
      .ctxintd-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        min-height:100%;
      }

      .ctxintd-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .ctxintd-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .ctxintd-value-lg{
        font-size:.90rem;
        font-weight:900;
        color:#0f172a;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media(max-width:992px){
        .ctxintd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxintd-header-card{
          min-height:88px;
        }

        .ctxintd-title{
          font-size:1.2rem;
        }

        .ctxintd-card-body{
          padding:8px 7px;
        }

        .ctxintd-section{
          padding:12px;
        }
      }

      @media(max-width:768px){
        .ctxintd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .ctxintd-header-overlay::before{
          margin:0;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        it=it,
        read_only=read_only,
        format_fecha_contexto=format_fecha_contexto
    )
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Edición
# ==========================
@app.route('/contexto_interno/edit/<int:id>', methods=['GET','POST'])
@login_required
def contexto_interno_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Contexto Interno")
    ):
        flash("No tiene permiso para editar registros del contexto interno.", "danger")
        return redirect(url_for('contexto_interno_matriz'))
    
    item = ContextoInterno.query.get_or_404(id)

    if request.method == 'POST':
        item.factor_interno = (request.form.get('factor_interno') or '').strip()
        item.descripcion    = (request.form.get('descripcion') or '').strip()
        item.impacto_sgsi   = (request.form.get('impacto_sgsi') or '').strip()
        item.fortalezas     = (request.form.get('fortalezas') or '').strip()
        item.debilidades    = (request.form.get('debilidades') or '').strip()
        fecha_str           = (request.form.get('fecha_revision') or '').strip()

        if fecha_str:
            try:
                item.fecha_revision = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de revisión inválida.", "danger")
                return redirect(url_for('contexto_interno_edit', id=id))
        else:
            item.fecha_revision = None

        db.session.commit()
        flash("Registro actualizado.", "success")
        return redirect(url_for('contexto_interno_matriz'))

    html = """
    <div class="ctxinted-shell">

      <div class="ctxinted-header-card">
        <div class="ctxinted-header-overlay">
          <div class="ctxinted-header-text">
            <h3 class="ctxinted-title m-0">Editar Contexto Interno</h3>
            <div class="ctxinted-subtitle">
              Actualización de factores internos que afectan el Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="ctxinted-header-actions">
        <a href="{{ url_for('contexto_interno_matriz') }}"
           class="btn rounded-pill px-4 fw-bold ctxinted-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="ctxinted-card">
        <div class="ctxinted-card-body">

          <form method="post">
            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Factor Interno</label>
                <input name="factor_interno"
                       class="form-control"
                       value="{{ item.factor_interno }}"
                       required>
              </div>

              <div class="col-md-8">
                <label class="form-label">Descripción</label>
                <textarea name="descripcion"
                          class="form-control"
                          rows="2"
                          required>{{ item.descripcion }}</textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Impacto en el SGSI</label>
                <textarea name="impacto_sgsi"
                          class="form-control"
                          rows="2"
                          required>{{ item.impacto_sgsi }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Fortalezas</label>
                <textarea name="fortalezas"
                          class="form-control"
                          rows="2">{{ item.fortalezas }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Debilidades</label>
                <textarea name="debilidades"
                          class="form-control"
                          rows="2">{{ item.debilidades }}</textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date"
                       name="fecha_revision"
                       class="form-control"
                       value="{{ item.fecha_revision.strftime('%Y-%m-%d') if item.fecha_revision else '' }}">
              </div>

            </div>

            <div class="ctxinted-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold"
                      type="submit">
                Guardar cambios
              </button>

              <a href="{{ url_for('contexto_interno_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold ctxinted-cancel-btn">
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

      .ctxinted-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      .ctxinted-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .ctxinted-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
        pointer-events:none;
      }

      .ctxinted-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .ctxinted-header-overlay::before{
        content:"✏️";
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
      }

      .ctxinted-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .ctxinted-header-text::before{
        content:"SGSI · Edición Contexto Interno";
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

      .ctxinted-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .ctxinted-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      .ctxinted-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .ctxinted-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxinted-header-actions .btn-primary,
      .ctxinted-header-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxinted-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxinted-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .ctxinted-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxinted-card-body{
        padding:16px 18px;
      }

      .ctxinted-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .ctxinted-card .form-control,
      .ctxinted-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
        padding-top:5px;
        padding-bottom:5px;
      }

      .ctxinted-card textarea{
        min-height:70px;
        resize:vertical;
      }

      .ctxinted-card .form-control:focus,
      .ctxinted-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .ctxinted-card .row{
        row-gap:10px;
      }

      .ctxinted-card .mb-3{
        margin-bottom:.70rem !important;
      }

      .ctxinted-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .ctxinted-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxinted-bottom-actions .btn-primary,
      .ctxinted-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxinted-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .ctxinted-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxinted-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .ctxinted-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxinted-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .ctxinted-title{
          font-size:1.22rem;
        }

        .ctxinted-subtitle{
          font-size:.74rem;
        }

        .ctxinted-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .ctxinted-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .ctxinted-header-overlay::before{
          margin-right:0;
        }

        .ctxinted-title{
          font-size:1.12rem;
        }

        .ctxinted-subtitle{
          font-size:.72rem;
        }

        .ctxinted-bottom-actions .btn,
        .ctxinted-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, item=item)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Borrado
# ==========================
@app.route('/contexto_interno/delete/<int:id>')
@login_required
def contexto_interno_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Contexto Interno")
    ):
        flash("No tiene permiso para eliminar registros del contexto interno.", "danger")
        return redirect(url_for('contexto_interno_matriz'))

    item = ContextoInterno.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash("Registro eliminado.", "success")
    return redirect(url_for('contexto_interno_matriz'))

# ==========================================================================================================================================
#                                                               Fin Módulo de Contexto Interno
# ==========================================================================================================================================


# ==========================================================================================================================================
#                                                               Módulo de Contexto Externo
# ==========================================================================================================================================

class ContextoExterno(db.Model):
    __tablename__ = 'contexto_externo'

    id = db.Column(db.Integer, primary_key=True)

    categoria            = db.Column(db.String(200), nullable=False)  # Categoría
    descripcion_factor   = db.Column(db.Text, nullable=False)         # Descripción del factor externo
    impacto_sgsi         = db.Column(db.Text, nullable=False)         # Impacto en el SGSI
    oportunidades = db.Column(db.Text, nullable=True)
    amenazas      = db.Column(db.Text, nullable=True)
    fecha_revision       = db.Column(db.Date, nullable=True)          # Fecha de Revisión

def format_fecha_contexto_externo(valor):
    if not valor:
        return '—'
    try:
        return valor.strftime('%Y-%m-%d')
    except Exception:
        return str(valor)

def resumir_contexto_externo_texto(valor, limite=140):
    if not valor:
        return '—'
    txt = str(valor).strip()
    if len(txt) <= limite:
        return txt
    return txt[:limite].rstrip() + '...'


# ==========================
# ENTRADA DIRECTA AL MÓDULO
# ==========================
@app.route('/contexto_externo_menu')
@login_required
def contexto_externo_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Contexto Externo"):
        flash("No tiene permiso para acceder al módulo de contexto externo.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('contexto_externo_matriz'))


# ==========================
# Agregar Contexto Externo
# ==========================
@app.route('/contexto_externo/new', methods=['GET', 'POST'])
@login_required
def contexto_externo_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('contexto_externo_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Contexto Externo"):
        flash("No tiene permiso para agregar registro de contexto externo.", "danger")
        return redirect(url_for('contexto_externo_matriz'))

    if request.method == 'POST':
        categoria          = (request.form.get('categoria') or '').strip()
        descripcion_factor = (request.form.get('descripcion_factor') or '').strip()
        impacto_sgsi       = (request.form.get('impacto_sgsi') or '').strip()
        oportunidades      = (request.form.get('oportunidades') or '').strip()
        amenazas           = (request.form.get('amenazas') or '').strip()
        fecha_str          = (request.form.get('fecha_revision') or '').strip()

        fecha_revision = None
        if fecha_str:
            try:
                fecha_revision = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de revisión inválida.", "danger")
                return redirect(url_for('contexto_externo_new'))

        if not (categoria and descripcion_factor and impacto_sgsi):
            flash("Campos obligatorios: Categoría, Descripción del factor externo e Impacto en el SGSI.", "danger")
            return redirect(url_for('contexto_externo_new'))

        it = ContextoExterno(
            categoria=categoria,
            descripcion_factor=descripcion_factor,
            impacto_sgsi=impacto_sgsi,
            oportunidades=oportunidades,
            amenazas=amenazas,
            fecha_revision=fecha_revision
        )
        db.session.add(it)
        db.session.commit()
        flash("Contexto externo registrado.", "success")
        return redirect(url_for('contexto_externo_matriz'))

    html = """
    <div class="ctxext-shell">

      <div class="ctxext-header-card">
        <div class="ctxext-header-overlay">
          <div class="ctxext-header-text">
            <h3 class="ctxext-title m-0">⨁ Agregar Contexto Externo</h3>
            <div class="ctxext-subtitle">
              Registro de factores externos que influyen en el Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="ctxext-header-actions">
        <a href="{{ url_for('contexto_externo_matriz') }}"
           class="btn rounded-pill px-4 fw-bold ctxext-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="ctxext-card">
        <div class="ctxext-card-body">
          <form method="post">
            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Categoría</label>
                <input name="categoria" class="form-control" required>
              </div>

              <div class="col-md-8">
                <label class="form-label">Descripción del factor externo</label>
                <textarea name="descripcion_factor" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Impacto en el SGSI</label>
                <textarea name="impacto_sgsi" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Oportunidades</label>
                <textarea name="oportunidades" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Amenazas</label>
                <textarea name="amenazas" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date" name="fecha_revision" class="form-control">
              </div>

            </div>

            <div class="ctxext-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>

              <a href="{{ url_for('contexto_externo_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold ctxext-cancel-btn">
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

      .ctxext-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI UNIFICADO
      ========================== */
      .ctxext-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .ctxext-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .ctxext-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .ctxext-header-overlay::before{
        content:"🌍";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .ctxext-header-text::before{
        content:"SGSI · Contexto Externo";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .ctxext-title{
        color:#fff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
      }

      .ctxext-subtitle{
        font-size:.78rem;
        opacity:.9;
      }

      /* =========================
         ACCIONES
      ========================== */
      .ctxext-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .ctxext-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxext-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxext-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD FORMULARIO
      ========================== */
      .ctxext-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxext-card-body{
        padding:16px 18px;
      }

      /* =========================
         FORMULARIOS COMPACTOS
      ========================== */
      .ctxext-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .ctxext-card .form-control,
      .ctxext-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
      }

      .ctxext-card textarea{
        min-height:70px;
        resize:vertical;
      }

      .ctxext-card .form-control:focus,
      .ctxext-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .ctxext-card .row{
        row-gap:10px;
      }

      .ctxext-card .mb-3{
        margin-bottom:.70rem !important;
      }

      /* =========================
         BOTONES
      ========================== */
      .ctxext-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .ctxext-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxext-bottom-actions .btn-primary,
      .ctxext-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxext-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .ctxext-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxext-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .ctxext-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxext-header-card{
          min-height:88px;
        }

        .ctxext-title{
          font-size:1.2rem;
        }

        .ctxext-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .ctxext-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .ctxext-header-overlay::before{
          margin:0;
        }

        .ctxext-bottom-actions .btn,
        .ctxext-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Matriz Contexto Externo
# ==========================
CONTEXTO_EXTERNO_MATRIZ_MIN_COLS = [
    "categoria",
    "descripcion_factor",
    "impacto_sgsi",
    "fecha_revision",
]

@app.route('/contexto_externo_matriz', methods=['GET'])
@login_required
def contexto_externo_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Contexto Externo"):
            flash("No tiene permiso para ver los contextos externos.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    items = ContextoExterno.query.order_by(ContextoExterno.id.desc()).all()

    html = """
    <div class="ctxextmat-shell">

      <div class="ctxextmat-header-card">
        <div class="ctxextmat-header-overlay">
          <div class="ctxextmat-header-text">
            <h3 class="ctxextmat-title m-0">Contexto Externo</h3>
            <div class="ctxextmat-subtitle">
              Visualización resumida de los factores externos que afectan el Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="ctxextmat-header-actions">
        {% if not read_only %}
          <a href="{{ url_for('contexto_externo_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            Agregar Contexto Externo
          </a>
        {% endif %}

      </div>

      <div class="ctxextmat-card">
        <div class="ctxextmat-topbar">
          <div>
            <h5 class="ctxextmat-top-title mb-1">Resumen de registros</h5>
            <div class="ctxextmat-top-note">
              La matriz presenta únicamente los campos más importantes. Para revisar el registro completo usa el botón <strong>Ver detalle</strong>.
            </div>
          </div>
          <div class="ctxextmat-counter-badge">
            Total registros: {{ items|length }}
          </div>
        </div>

        <div class="ctxextmat-card-body">
          <div class="ctxextmat-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-hover align-middle ctxextmat-table mb-0">
                <colgroup>
                  <col style="width: 20%;">
                  <col style="width: 30%;">
                  <col style="width: 28%;">
                  <col style="width: 10%;">
                  <col style="width: 12%;">
                </colgroup>

                <thead>
                  <tr>
                    <th>Categoría</th>
                    <th>Descripción del factor externo</th>
                    <th>Impacto en el SGSI</th>
                    <th>Fecha de Revisión</th>
                    <th>Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  {% for it in items %}
                    <tr>
                      <td class="ctxextmat-cell-main">
                        <div class="ctxextmat-main-text">{{ it.categoria or '—' }}</div>
                      </td>

                      <td>{{ resumir_contexto_externo_texto(it.descripcion_factor, 150) }}</td>

                      <td>{{ resumir_contexto_externo_texto(it.impacto_sgsi, 150) }}</td>

                      <td class="text-center">
                        {{ format_fecha_contexto_externo(it.fecha_revision) }}
                      </td>

                      <td class="text-center">
                        <div class="ctxextmat-actions-wrap">
                          <a href="{{ url_for('contexto_externo_detalle', id=it.id) }}"
                             class="btn btn-info btn-sm rounded-pill px-3 fw-bold text-white">
                            Ver detalle
                          </a>

                          {% if not read_only %}
                            <a href="{{ url_for('contexto_externo_edit', id=it.id) }}"
                               class="btn btn-warning btn-sm rounded-pill px-3 fw-bold">
                              Editar
                            </a>

                            <a href="{{ url_for('contexto_externo_delete', id=it.id) }}"
                               class="btn btn-danger btn-sm rounded-pill px-3 fw-bold"
                               onclick="return confirm('¿Eliminar este registro?');">
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
                      <td colspan="5" class="text-center text-muted py-5">
                        Sin registros
                      </td>
                    </tr>
                  {% endif %}
                </tbody>
              </table>
            </div>
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

      .ctxextmat-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .ctxextmat-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .ctxextmat-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
        pointer-events:none;
      }

      .ctxextmat-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .ctxextmat-header-overlay::before{
        content:"🌍";
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
      }

      .ctxextmat-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .ctxextmat-header-text::before{
        content:"SGSI · Contexto Externo";
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

      .ctxextmat-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .ctxextmat-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      .ctxextmat-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .ctxextmat-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxextmat-header-actions .btn-primary,
      .ctxextmat-header-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxextmat-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxextmat-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .ctxextmat-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxextmat-topbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:14px 16px 0 16px;
        flex-wrap:wrap;
      }

      .ctxextmat-top-title{
        color:#0f172a;
        font-weight:950;
        font-size:.94rem;
      }

      .ctxextmat-top-note{
        color:#475569;
        font-size:.78rem;
        margin-top:3px;
      }

      .ctxextmat-counter-badge{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:7px 14px;
        font-size:.78rem;
        box-shadow:0 8px 16px rgba(15,23,42,.16);
      }

      .ctxextmat-card-body{
        padding:12px 16px 16px 16px;
      }

      .ctxextmat-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:rgba(255,255,255,.99);
      }

      .ctxextmat-table{
        min-width:1200px;
        margin-bottom:0;
        table-layout:fixed;
        border-collapse:separate;
        border-spacing:0;
      }

      .ctxextmat-table th,
      .ctxextmat-table td{
        white-space:normal;
        word-break:break-word;
        vertical-align:top;
        font-size:.68rem;
        padding:9px 8px;
      }

      .ctxextmat-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border-right:1px solid rgba(255,255,255,.28);
      }

      .ctxextmat-table td{
        color:#101827;
        border-right:1px solid #dce6f3;
        border-bottom:1px solid #dce6f3;
        background:#ffffff;
      }

      .ctxextmat-table tbody tr:nth-child(even) td{
        background:#f8fbff;
      }

      .ctxextmat-table tbody tr:hover td{
        background:#eef6ff;
      }

      .ctxextmat-cell-main .ctxextmat-main-text{
        font-weight:900;
        color:#0f172a;
        line-height:1.35;
      }

      .ctxextmat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .ctxextmat-actions-wrap .btn,
      .ctxextmat-table .btn{
        min-width:86px;
        min-height:28px;
        border-radius:999px !important;
        padding:4px 12px !important;
        font-size:.70rem;
        font-weight:900;
        display:inline-flex;
        align-items:center;
        justify-content:center;
      }

      .ctxextmat-table .btn-info{
        background:#087ab8;
        border:none;
        color:#fff;
      }

      .ctxextmat-table .btn-warning{
        background:#c76b00;
        border:none;
        color:#0b1220;
      }

      .ctxextmat-table .btn-danger{
        background:#b91c1c;
        border:none;
        color:#fff;
      }

      .ctxextmat-table .btn-success{
        background:#087c3d;
        border:none;
        color:#fff;
      }

      .ctxextmat-table-wrap::-webkit-scrollbar{
        height:11px;
        width:11px;
      }

      .ctxextmat-table-wrap::-webkit-scrollbar-track{
        background:#dbe4f0;
        border-radius:12px;
      }

      .ctxextmat-table-wrap::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,#5aa3ea,#3f86d6);
        border-radius:12px;
        border:2px solid #dbe4f0;
      }

      .ctxextmat-table-wrap{
        scrollbar-width:thin;
        scrollbar-color:#3f86d6 #dbe4f0;
      }

      @media (max-width:992px){
        .ctxextmat-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxextmat-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .ctxextmat-card-body{
          padding:12px 14px 14px 14px;
        }

        .ctxextmat-topbar{
          padding:12px 14px 0 14px;
        }

        .ctxextmat-title{
          font-size:1.22rem;
        }

        .ctxextmat-subtitle{
          font-size:.74rem;
        }
      }

      @media (max-width:768px){
        .ctxextmat-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .ctxextmat-header-overlay::before{
          margin-right:0;
        }

        .ctxextmat-title{
          font-size:1.12rem;
        }

        .ctxextmat-subtitle{
          font-size:.72rem;
        }

        .ctxextmat-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        resumir_contexto_externo_texto=resumir_contexto_externo_texto,
        format_fecha_contexto_externo=format_fecha_contexto_externo
    )
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Detalle Contexto Externo
# ==========================
@app.route('/contexto_externo/detalle/<int:id>')
@login_required
def contexto_externo_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Contexto Externo"):
            flash("No tiene permiso para ver el detalle del contexto externo.", "danger")
            return redirect(url_for('contexto_externo_matriz'))
        read_only = False

    it = ContextoExterno.query.get_or_404(id)

    html = """
    <div class="ctxextd-shell">

      <div class="ctxextd-header-card">
        <div class="ctxextd-header-overlay">
          <div class="ctxextd-header-text">
            <h3 class="ctxextd-title m-0">Detalle — Contexto Externo</h3>
            <div class="ctxextd-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="ctxextd-header-actions">
        <a href="{{ url_for('contexto_externo_matriz') }}"
           class="btn rounded-pill px-4 fw-bold ctxextd-back-btn">
          ⬅ Volver a la Matriz
        </a>


        {% if not read_only %}
          <a href="{{ url_for('contexto_externo_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="ctxextd-card">
        <div class="ctxextd-card-body">

          <div class="ctxextd-section">
            <div class="ctxextd-section-title">Información principal</div>
            <div class="row g-3">
              <div class="col-md-8">
                <div class="ctxextd-field">
                  <div class="ctxextd-label">Categoría</div>
                  <div class="ctxextd-value ctxextd-value-lg">{{ it.categoria or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="ctxextd-field">
                  <div class="ctxextd-label">Fecha de Revisión</div>
                  <div class="ctxextd-value">{{ format_fecha_contexto_externo(it.fecha_revision) }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="ctxextd-field">
                  <div class="ctxextd-label">Descripción del factor externo</div>
                  <div class="ctxextd-value">{{ it.descripcion_factor or '—' }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="ctxextd-field">
                  <div class="ctxextd-label">Impacto en el SGSI</div>
                  <div class="ctxextd-value">{{ it.impacto_sgsi or '—' }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="ctxextd-section">
            <div class="ctxextd-section-title">Análisis externo</div>
            <div class="row g-3">
              <div class="col-md-6">
                <div class="ctxextd-field">
                  <div class="ctxextd-label">Oportunidades</div>
                  <div class="ctxextd-value">{{ it.oportunidades or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="ctxextd-field">
                  <div class="ctxextd-label">Amenazas</div>
                  <div class="ctxextd-value">{{ it.amenazas or '—' }}</div>
                </div>
              </div>
            </div>
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

      .ctxextd-shell{
        width:96%;
        max-width:1250px;
        margin:10px auto 24px auto;
      }

      .ctxextd-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .ctxextd-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .ctxextd-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .ctxextd-header-overlay::before{
        content:"🌍";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .ctxextd-header-text::before{
        content:"SGSI · Contexto Externo (Detalle)";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .ctxextd-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .ctxextd-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .ctxextd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .ctxextd-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxextd-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxextd-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .ctxextd-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxextd-card-body{
        padding:16px 18px;
      }

      .ctxextd-section{
        margin-bottom:14px;
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .ctxextd-section:last-child{
        margin-bottom:0;
      }

      .ctxextd-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      .ctxextd-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        min-height:100%;
      }

      .ctxextd-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .ctxextd-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .ctxextd-value-lg{
        font-size:.90rem;
        font-weight:900;
        color:#0f172a;
      }

      @media (max-width:992px){
        .ctxextd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxextd-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .ctxextd-title{
          font-size:1.2rem;
        }

        .ctxextd-card-body{
          padding:8px 7px;
        }

        .ctxextd-section{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .ctxextd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .ctxextd-header-overlay::before{
          margin:0;
        }

        .ctxextd-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        it=it,
        read_only=read_only,
        format_fecha_contexto_externo=format_fecha_contexto_externo
    )
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Editar
# ==========================
@app.route('/contexto_externo/edit/<int:id>', methods=['GET','POST'])
@login_required
def contexto_externo_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Contexto Externo")
    ):
        flash("No tiene permiso para editar registros del contexto externo.", "danger")
        return redirect(url_for('contexto_externo_matriz'))

    item = ContextoExterno.query.get_or_404(id)

    if request.method == 'POST':
        item.categoria          = (request.form.get('categoria') or '').strip()
        item.descripcion_factor = (request.form.get('descripcion_factor') or '').strip()
        item.impacto_sgsi       = (request.form.get('impacto_sgsi') or '').strip()
        item.oportunidades      = (request.form.get('oportunidades') or '').strip()
        item.amenazas           = (request.form.get('amenazas') or '').strip()
        fecha_str               = (request.form.get('fecha_revision') or '').strip()

        if fecha_str:
            try:
                item.fecha_revision = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de revisión inválida.", "danger")
                return redirect(url_for('contexto_externo_edit', id=id))
        else:
            item.fecha_revision = None

        db.session.commit()
        flash("Registro actualizado.", "success")
        return redirect(url_for('contexto_externo_matriz'))

    html = """
    <div class="ctxexed-shell">

      <div class="ctxexed-header-card">
        <div class="ctxexed-header-overlay">
          <div class="ctxexed-header-text">
            <h3 class="ctxexed-title m-0">Editar Contexto Externo</h3>
            <div class="ctxexed-subtitle">
              Actualización de factores externos que afectan el Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="ctxexed-header-actions">
        <a href="{{ url_for('contexto_externo_matriz') }}"
           class="btn rounded-pill px-4 fw-bold ctxexed-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="ctxexed-card">
        <div class="ctxexed-card-body">

          <form method="post">
            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Categoría</label>
                <input name="categoria"
                       class="form-control"
                       value="{{ item.categoria }}"
                       required>
              </div>

              <div class="col-md-8">
                <label class="form-label">Descripción del factor externo</label>
                <textarea name="descripcion_factor"
                          class="form-control"
                          rows="2"
                          required>{{ item.descripcion_factor }}</textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Impacto en el SGSI</label>
                <textarea name="impacto_sgsi"
                          class="form-control"
                          rows="2"
                          required>{{ item.impacto_sgsi }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Oportunidades</label>
                <textarea name="oportunidades"
                          class="form-control"
                          rows="2">{{ item.oportunidades or "" }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Amenazas</label>
                <textarea name="amenazas"
                          class="form-control"
                          rows="2">{{ item.amenazas or "" }}</textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date"
                       name="fecha_revision"
                       class="form-control"
                       value="{{ item.fecha_revision.strftime('%Y-%m-%d') if item.fecha_revision else '' }}">
              </div>

            </div>

            <div class="ctxexed-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>

              <a href="{{ url_for('contexto_externo_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold ctxexed-cancel-btn">
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

      .ctxexed-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI UNIFICADO
      ========================== */
      .ctxexed-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .ctxexed-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .ctxexed-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .ctxexed-header-overlay::before{
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
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .ctxexed-header-text::before{
        content:"SGSI · Edición Contexto Externo";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .ctxexed-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .ctxexed-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         ACCIONES
      ========================== */
      .ctxexed-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .ctxexed-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxexed-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxexed-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD FORMULARIO
      ========================== */
      .ctxexed-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxexed-card-body{
        padding:16px 18px;
      }

      /* =========================
         FORMULARIO COMPACTO
      ========================== */
      .ctxexed-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .ctxexed-card .form-control,
      .ctxexed-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .ctxexed-card textarea{
        min-height:70px;
        resize:vertical;
      }

      .ctxexed-card .form-control:focus,
      .ctxexed-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .ctxexed-card .row{
        row-gap:10px;
      }

      .ctxexed-card .mb-3{
        margin-bottom:.70rem !important;
      }

      /* =========================
         BOTONES
      ========================== */
      .ctxexed-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .ctxexed-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxexed-bottom-actions .btn-primary,
      .ctxexed-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxexed-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .ctxexed-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxexed-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .ctxexed-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxexed-header-card{
          min-height:88px;
        }

        .ctxexed-title{
          font-size:1.2rem;
        }

        .ctxexed-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .ctxexed-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .ctxexed-header-overlay::before{
          margin:0;
        }

        .ctxexed-bottom-actions .btn,
        .ctxexed-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, item=item)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Eliminar
# ==========================
@app.route('/contexto_externo/delete/<int:id>')
@login_required
def contexto_externo_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Contexto Externo")
    ):
        flash("No tiene permiso para eliminar registros del contexto externo.", "danger")
        return redirect(url_for('contexto_externo_matriz'))

    item = ContextoExterno.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash("Registro eliminado.", "success")
    return redirect(url_for('contexto_externo_matriz'))

# ==========================================================================================================================================
#                                                       Fin Módulo de Contexto Externo
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                               Módulo DOFA
# ==========================================================================================================================================

# ==========================
# DOFA
# ==========================

class DofaAnalisis(db.Model):
    __tablename__ = 'dofa_analisis'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False, default="DOFA")
    fecha = db.Column(db.Date, nullable=False, default=date.today)

    fortalezas = db.Column(db.Text, nullable=True)
    debilidades = db.Column(db.Text, nullable=True)
    oportunidades = db.Column(db.Text, nullable=True)
    amenazas = db.Column(db.Text, nullable=True)

    estrategias_fo = db.Column(db.Text, nullable=True)
    estrategias_fa = db.Column(db.Text, nullable=True)
    estrategias_do = db.Column(db.Text, nullable=True)
    estrategias_da = db.Column(db.Text, nullable=True)

    creado_por = db.Column(db.String(80), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


# =================================
#   Entrada directa a listado DOFA
# =================================

@app.route('/dofa_menu')
@login_required
def dofa_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "DOFA"):
        flash("No tiene permiso para acceder al módulo DOFA.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('dofa_list'))


def _autollenar_dofa_desde_contexto():
    internos = ContextoInterno.query.all()
    externos = ContextoExterno.query.all()

    fortalezas = []
    debilidades = []
    for r in internos:
        if r.fortalezas and r.fortalezas.strip():
            fortalezas.append(f"- {r.fortalezas.strip()}")
        if r.debilidades and r.debilidades.strip():
            debilidades.append(f"- {r.debilidades.strip()}")

    oportunidades = []
    amenazas = []
    for e in externos:
        op = (e.oportunidades or "").strip()
        am = (e.amenazas or "").strip()

        if op:
            oportunidades.append(f"- {op}")
        if am:
            amenazas.append(f"- {am}")

    return (
        "\n".join(fortalezas).strip(),
        "\n".join(debilidades).strip(),
        "\n".join(oportunidades).strip(),
        "\n".join(amenazas).strip(),
    )


# ==========================================
# Generación de estrategias DOFA con IA
# ==========================================

def _dofa_ai_clean(value, limit=9000):
    text_value = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return text_value[:limit]


def _dofa_ai_normalize_strategy(value):
    if isinstance(value, list):
        items = []
        for item in value:
            item_text = _dofa_ai_clean(item, 1800)
            if item_text:
                items.append(item_text if item_text.startswith(("-", "•")) else f"- {item_text}")
        return "\n".join(items).strip()

    if isinstance(value, dict):
        items = []
        for item in value.values():
            item_text = _dofa_ai_clean(item, 1800)
            if item_text:
                items.append(item_text if item_text.startswith(("-", "•")) else f"- {item_text}")
        return "\n".join(items).strip()

    text_value = _dofa_ai_clean(value, 5000)
    text_value = re.sub(r"^\s*(?:ESTRATEGIAS?\s*)?(?:FO|FA|DO|DA)\s*[:\-]\s*", "", text_value, flags=re.I)
    return text_value.strip()


def _dofa_ai_extract_result(raw_text):
    raw_text = _dofa_ai_clean(raw_text, 20000)
    if not raw_text:
        raise ValueError("La IA no devolvió contenido.")

    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    data = None
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(cleaned[start:end + 1])
        except Exception:
            data = None

    if not isinstance(data, dict):
        # Respaldo para modelos que respondan con secciones FO / FA / DO / DA.
        section_pattern = re.compile(
            r"(?ims)^\s*(?:#{1,6}\s*)?(FO|FA|DO|DA)\s*(?:\([^)]*\))?\s*[:\-]\s*(.*?)(?=^\s*(?:#{1,6}\s*)?(?:FO|FA|DO|DA)\s*(?:\([^)]*\))?\s*[:\-]|\Z)"
        )
        sections = {}
        for match in section_pattern.finditer(cleaned):
            sections[match.group(1).lower()] = match.group(2).strip()
        if len(sections) == 4:
            data = sections

    if not isinstance(data, dict):
        raise ValueError("La IA no devolvió las cuatro estrategias en un formato válido.")

    aliases = {
        "estrategias_fo": ("estrategias_fo", "estrategia_fo", "fo", "FO"),
        "estrategias_fa": ("estrategias_fa", "estrategia_fa", "fa", "FA"),
        "estrategias_do": ("estrategias_do", "estrategia_do", "do", "DO"),
        "estrategias_da": ("estrategias_da", "estrategia_da", "da", "DA"),
    }

    result = {}
    for target, possible_keys in aliases.items():
        value = None
        for key in possible_keys:
            if key in data:
                value = data.get(key)
                break
        normalized = _dofa_ai_normalize_strategy(value)
        if not normalized:
            raise ValueError(f"La IA no generó contenido para {target.replace('estrategias_', '').upper()}.")
        result[target] = normalized

    return result


def _dofa_generate_strategies_with_ai(fortalezas, oportunidades, debilidades, amenazas):
    quadrants = {
        "fortalezas": _dofa_ai_clean(fortalezas),
        "oportunidades": _dofa_ai_clean(oportunidades),
        "debilidades": _dofa_ai_clean(debilidades),
        "amenazas": _dofa_ai_clean(amenazas),
    }

    missing_labels = {
        "fortalezas": "Fortalezas",
        "oportunidades": "Oportunidades",
        "debilidades": "Debilidades",
        "amenazas": "Amenazas",
    }
    missing = [missing_labels[key] for key, value in quadrants.items() if not value]
    if missing:
        raise ValueError(
            "Complete los cuatro cuadrantes antes de generar estrategias con IA. "
            "Falta información en: " + ", ".join(missing) + "."
        )

    expected_format = {
        "estrategias_fo": "- Estrategia 1\n- Estrategia 2",
        "estrategias_fa": "- Estrategia 1\n- Estrategia 2",
        "estrategias_do": "- Estrategia 1\n- Estrategia 2",
        "estrategias_da": "- Estrategia 1\n- Estrategia 2",
    }

    prompt = f"""
Genere estrategias cruzadas para una matriz DOFA de una organización, utilizando únicamente
la información proporcionada. No invente capacidades, tecnologías, contratos, certificaciones,
presupuestos, incidentes ni condiciones que no estén presentes en los cuadrantes.

Criterios:
- FO: utilizar fortalezas para aprovechar oportunidades.
- FA: utilizar fortalezas para reducir o afrontar amenazas.
- DO: superar debilidades aprovechando oportunidades.
- DA: reducir debilidades y evitar o mitigar amenazas.
- Genere exactamente dos estrategias concretas y accionables por cada cuadrante.
- Cada estrategia debe indicar una acción organizacional clara.
- Responda en español.
- No agregue explicaciones, encabezados ni texto fuera del JSON.
- Devuelva exclusivamente un objeto JSON válido con estas cuatro claves:
{json.dumps(expected_format, ensure_ascii=False, indent=2)}

MATRIZ DOFA:
{json.dumps(quadrants, ensure_ascii=False, indent=2)}
""".strip()

    raw_result = ai_text_general(
        prompt=prompt,
        system_prompt=(
            "Eres un consultor senior en planeación estratégica, gestión de riesgos y seguridad "
            "de la información. Genera estrategias DOFA realistas y responde solo JSON válido."
        ),
        temperature=0.2,
        max_tokens=350,
    )
    return _dofa_ai_extract_result(raw_result)


@app.route('/dofa/generar_estrategias_ia', methods=['POST'])
@login_required
def dofa_generar_estrategias_ia():
    user = User.query.get(session.get('user_id'))

    if not user:
        return jsonify(ok=False, message="La sesión de usuario no es válida."), 401

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "DOFA"):
        return jsonify(ok=False, message="No tiene permiso para utilizar la IA del módulo DOFA."), 403

    if user.role == 'auditor':
        return jsonify(ok=False, message="Perfil auditor: solo lectura."), 403

    data = request.get_json(silent=True) or request.form.to_dict()

    try:
        strategies = _dofa_generate_strategies_with_ai(
            fortalezas=data.get("fortalezas"),
            oportunidades=data.get("oportunidades"),
            debilidades=data.get("debilidades"),
            amenazas=data.get("amenazas"),
        )

        try:
            registrar_log(
                user.username,
                "Generó estrategias FO, FA, DO y DA con IA en el módulo DOFA."
            )
        except Exception:
            pass

        return jsonify(
            ok=True,
            message=(
                "Estrategias generadas. Revise y edite el contenido antes de guardar la matriz DOFA."
            ),
            estrategias=strategies,
        )
    except ValueError as exc:
        return jsonify(ok=False, message=str(exc)), 400
    except Exception as exc:
        print("Error generando estrategias DOFA con IA:", repr(exc))
        return jsonify(
            ok=False,
            message=(
                "No fue posible generar las estrategias con IA. Verifique la configuración "
                "de OpenRouter u Ollama e inténtelo nuevamente."
            ),
        ), 500


# =================================
# Agregar DOFA
# =================================

@app.route('/dofa/new', methods=['GET', 'POST'])
@login_required
def dofa_new():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "DOFA"):
        flash("No tiene permiso para acceder al módulo DOFA.", "danger")
        return redirect(url_for('menu'))

    if user.role == 'auditor':
        flash("Perfil auditor: solo lectura.", "warning")
        return redirect(url_for('dofa_list'))

    if request.method == 'POST':
        titulo = (request.form.get('titulo') or "DOFA").strip()
        fecha_str = (request.form.get('fecha') or "").strip()

        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else date.today()
        except Exception:
            fecha = date.today()

        dofa = DofaAnalisis(
            titulo=titulo,
            fecha=fecha,
            fortalezas=request.form.get('fortalezas') or "",
            debilidades=request.form.get('debilidades') or "",
            oportunidades=request.form.get('oportunidades') or "",
            amenazas=request.form.get('amenazas') or "",
            estrategias_fo=request.form.get('estrategias_fo') or "",
            estrategias_fa=request.form.get('estrategias_fa') or "",
            estrategias_do=request.form.get('estrategias_do') or "",
            estrategias_da=request.form.get('estrategias_da') or "",
            creado_por=user.username
        )
        db.session.add(dofa)
        db.session.commit()
        flash("DOFA guardado correctamente.", "success")
        return redirect(url_for('dofa_list'))

    f, d, o, a = _autollenar_dofa_desde_contexto()

    content = render_template_string("""
    <div class="dofa-shell">

      <div class="dofa-header-card">
        <div class="dofa-header-overlay">
          <div class="dofa-header-text">
            <h3 class="dofa-title m-0">Nuevo DOFA</h3>
            <div class="dofa-subtitle">
              Matriz 2x2 con fortalezas, oportunidades, debilidades, amenazas y estrategias FO / FA / DO / DA
            </div>
          </div>
        </div>
      </div>

      <div class="dofa-header-actions">
        <a href="{{ url_for('dofa_list') }}"
           class="btn rounded-pill px-5 fw-bold dofa-back-btn">
          ⬅ Volver al Listado DOFA
        </a>

      </div>

      <form method="POST" class="dofa-card">
        <div class="dofa-card-body">

          <div class="row g-3">
            <div class="col-md-8">
              <label class="form-label fw-semibold">Título</label>
              <input type="text" name="titulo" class="form-control" value="DOFA">
            </div>
            <div class="col-md-4">
              <label class="form-label fw-semibold">Fecha</label>
              <input type="date" name="fecha" class="form-control" value="{{ today }}">
            </div>
          </div>

          <hr class="my-4">

          <div class="row g-3">
            <div class="col-md-6">
              <div class="quad quad-f">
                <div class="quad-h">✅ Fortalezas</div>
                <textarea name="fortalezas" class="form-control quad-ta" rows="7" placeholder="- ...">{{ f }}</textarea>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-o">
                <div class="quad-h">🌟 Oportunidades</div>
                <textarea name="oportunidades" class="form-control quad-ta" rows="7" placeholder="- ...">{{ o }}</textarea>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-d">
                <div class="quad-h">⚠️ Debilidades</div>
                <textarea name="debilidades" class="form-control quad-ta" rows="7" placeholder="- ...">{{ d }}</textarea>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-a">
                <div class="quad-h">🛡️ Amenazas</div>
                <textarea name="amenazas" class="form-control quad-ta" rows="7" placeholder="- ...">{{ a }}</textarea>
              </div>
            </div>
          </div>

          <hr class="my-4">


          <div class="dofa-ai-panel">
            <div class="dofa-ai-copy">
              <div class="dofa-ai-title">✨ Generación de estrategias con IA</div>
              <div class="dofa-ai-help">
                La IA utiliza el contenido actual de Fortalezas, Oportunidades, Debilidades y Amenazas.
                El resultado se coloca en campos editables: puede ajustarlo, reemplazarlo o ingresar
                las estrategias manualmente.
              </div>
            </div>
            <button type="button"
                    class="btn dofa-ai-btn"
                    data-no-progress="true"
                    onclick="generarEstrategiasDofaIA(this, 'cE')">
              <span class="dofa-ai-btn-label">🧠 Generar FO / FA / DO / DA con IA</span>
            </button>
          </div>
          <div class="dofa-ai-status" role="status" aria-live="polite"></div>

          <div class="accordion dofa-accordion" id="accEstrategias">
            <div class="accordion-item">
              <h2 class="accordion-header" id="hE">
                <button class="accordion-button collapsed fw-semibold" type="button"
                        data-bs-toggle="collapse" data-bs-target="#cE" aria-expanded="false" aria-controls="cE">
                  🧠 Estrategias FO / FA / DO / DA (opcional)
                </button>
              </h2>
              <div id="cE" class="accordion-collapse collapse" aria-labelledby="hE" data-bs-parent="#accEstrategias">
                <div class="accordion-body">

                  <div class="row g-3">
                    <div class="col-md-6">
                      <label class="form-label fw-semibold">FO (Fortalezas + Oportunidades)</label>
                      <textarea name="estrategias_fo" class="form-control" rows="4"></textarea>
                    </div>
                    <div class="col-md-6">
                      <label class="form-label fw-semibold">FA (Fortalezas + Amenazas)</label>
                      <textarea name="estrategias_fa" class="form-control" rows="4"></textarea>
                    </div>
                    <div class="col-md-6">
                      <label class="form-label fw-semibold">DO (Debilidades + Oportunidades)</label>
                      <textarea name="estrategias_do" class="form-control" rows="4"></textarea>
                    </div>
                    <div class="col-md-6">
                      <label class="form-label fw-semibold">DA (Debilidades + Amenazas)</label>
                      <textarea name="estrategias_da" class="form-control" rows="4"></textarea>
                    </div>
                  </div>

                </div>
              </div>
            </div>
          </div>

          <div class="dofa-bottom-actions">
            <button class="btn btn-success rounded-pill px-4 fw-bold">
              💾 Guardar DOFA
            </button>
            <a href="{{ url_for('dofa_list') }}"
               class="btn rounded-pill px-4 fw-bold dofa-cancel-btn">
              Cancelar
            </a>
          </div>

        </div>
      </form>

    </div>


    <script>
    (function () {
      if (window.__GRAC_DOFA_AI_READY__) return;
      window.__GRAC_DOFA_AI_READY__ = true;

      function showStrategySection(collapseId) {
        const collapseElement = document.getElementById(collapseId);
        if (!collapseElement) return;

        try {
          if (window.bootstrap && window.bootstrap.Collapse) {
            window.bootstrap.Collapse
              .getOrCreateInstance(collapseElement, {toggle: false})
              .show();
          } else {
            collapseElement.classList.add('show');
          }
        } catch (_error) {
          collapseElement.classList.add('show');
        }

        const toggle = document.querySelector('[data-bs-target="#' + collapseId + '"]');
        if (toggle) {
          toggle.classList.remove('collapsed');
          toggle.setAttribute('aria-expanded', 'true');
        }
      }

      function setDofaAiStatus(statusElement, message, kind) {
        if (!statusElement) return;
        statusElement.textContent = message || '';
        statusElement.className = 'dofa-ai-status is-visible ' + (kind || 'is-info');
      }

      window.generarEstrategiasDofaIA = async function (button, collapseId) {
        const form = button ? button.closest('form') : null;
        const panel = button ? button.closest('.dofa-ai-panel') : null;
        const statusElement = panel && panel.nextElementSibling &&
          panel.nextElementSibling.classList.contains('dofa-ai-status')
            ? panel.nextElementSibling
            : null;

        if (!form) {
          setDofaAiStatus(statusElement, 'No se encontró el formulario de la matriz DOFA.', 'is-error');
          return;
        }

        const names = [
          'fortalezas',
          'oportunidades',
          'debilidades',
          'amenazas',
          'estrategias_fo',
          'estrategias_fa',
          'estrategias_do',
          'estrategias_da'
        ];

        const fields = {};
        names.forEach(function (name) {
          fields[name] = form.querySelector('[name="' + name + '"]');
        });

        const sourceLabels = {
          fortalezas: 'Fortalezas',
          oportunidades: 'Oportunidades',
          debilidades: 'Debilidades',
          amenazas: 'Amenazas'
        };

        const missing = Object.keys(sourceLabels).filter(function (name) {
          return !fields[name] || !String(fields[name].value || '').trim();
        });

        if (missing.length) {
          setDofaAiStatus(
            statusElement,
            'Complete los cuatro cuadrantes. Falta información en: ' +
              missing.map(function (name) { return sourceLabels[name]; }).join(', ') + '.',
            'is-error'
          );
          return;
        }

        const strategyNames = [
          'estrategias_fo',
          'estrategias_fa',
          'estrategias_do',
          'estrategias_da'
        ];
        const hasExistingStrategies = strategyNames.some(function (name) {
          return fields[name] && String(fields[name].value || '').trim();
        });

        if (
          hasExistingStrategies &&
          !window.confirm(
            'Ya existen estrategias registradas. La generación con IA reemplazará temporalmente ' +
            'el contenido actual de FO, FA, DO y DA. Podrá editarlo antes de guardar. ¿Desea continuar?'
          )
        ) {
          return;
        }

        const originalHtml = button.innerHTML;
        button.disabled = true;
        button.innerHTML =
          '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Generando...';
        setDofaAiStatus(
          statusElement,
          'Analizando la matriz y construyendo estrategias FO, FA, DO y DA...',
          'is-info'
        );

        const payload = {
          fortalezas: fields.fortalezas.value,
          oportunidades: fields.oportunidades.value,
          debilidades: fields.debilidades.value,
          amenazas: fields.amenazas.value
        };

        try {
          const response = await fetch("{{ url_for('dofa_generar_estrategias_ia') }}", {
            method: 'POST',
            credentials: 'same-origin',
            cache: 'no-store',
            headers: {
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(payload)
          });

          let data = {};
          try {
            data = await response.json();
          } catch (_jsonError) {
            data = {};
          }

          if (!response.ok || !data.ok) {
            throw new Error(
              data.message || 'No fue posible generar las estrategias con IA.'
            );
          }

          const strategies = data.estrategias || {};
          const labels = {
            estrategias_fo: 'FO',
            estrategias_fa: 'FA',
            estrategias_do: 'DO',
            estrategias_da: 'DA'
          };

          strategyNames.forEach(function (name) {
            if (!fields[name] || !String(strategies[name] || '').trim()) {
              throw new Error('La IA no devolvió una estrategia válida para ' + labels[name] + '.');
            }
          });

          strategyNames.forEach(function (name) {
            fields[name].value = strategies[name];
            fields[name].dispatchEvent(new Event('input', {bubbles: true}));
          });

          showStrategySection(collapseId);
          setDofaAiStatus(
            statusElement,
            data.message ||
              'Estrategias generadas. Puede editarlas antes de guardar la matriz DOFA.',
            'is-success'
          );

          if (fields.estrategias_fo) {
            setTimeout(function () {
              fields.estrategias_fo.focus();
              fields.estrategias_fo.scrollIntoView({behavior: 'smooth', block: 'center'});
            }, 250);
          }
        } catch (error) {
          setDofaAiStatus(
            statusElement,
            error && error.message
              ? error.message
              : 'No fue posible generar las estrategias con IA.',
            'is-error'
          );
        } finally {
          button.disabled = false;
          button.innerHTML = originalHtml;
        }
      };
    })();
    </script>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .dofa-shell{
        width:96%;
        max-width:1450px;
        margin:10px auto 24px auto;
      }

      .dofa-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .dofa-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .dofa-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .dofa-header-overlay::before{
        content:"🧩";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .dofa-header-text::before{
        content:"SGSI · Análisis DOFA";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .dofa-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .dofa-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .dofa-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .dofa-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .dofa-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .dofa-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .dofa-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .dofa-card-body{
        padding:16px 18px;
      }

      .dofa-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .dofa-card .form-control,
      .dofa-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
      }

      .dofa-card textarea{
        min-height:70px;
        resize:vertical;
      }

      .dofa-card .form-control:focus,
      .dofa-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .quad{
        border-radius:16px;
        padding:12px;
        border:1px solid #dbe6f4;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .quad-h{
        font-weight:950;
        font-size:.86rem;
        margin-bottom:8px;
        color:#0f172a;
      }

      .quad-ta{
        background:rgba(255,255,255,.92) !important;
        border-radius:12px;
      }

      .quad-f{ background:rgba(25,135,84,.10); }
      .quad-o{ background:rgba(13,110,253,.10); }
      .quad-d{ background:rgba(255,193,7,.14); }
      .quad-a{ background:rgba(220,53,69,.10); }

      .dofa-accordion .accordion-item{
        border-radius:14px !important;
        overflow:hidden;
        border:1px solid #dbe6f4;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .dofa-accordion .accordion-button{
        font-size:.84rem;
        font-weight:900;
        color:#0b4a8f;
        background:#eef5ff;
      }

      .dofa-accordion .accordion-button:not(.collapsed){
        color:#062b55;
        background:#dbeafe;
        box-shadow:none;
      }


      .dofa-ai-panel{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:18px;
        padding:13px 15px;
        margin-bottom:10px;
        border:1px solid #b9d5f4;
        border-radius:14px;
        background:linear-gradient(135deg,#eef6ff,#f8fbff);
        box-shadow:0 6px 14px rgba(15,72,133,.08);
      }

      .dofa-ai-copy{
        min-width:0;
      }

      .dofa-ai-title{
        color:#0b4a8f;
        font-size:.86rem;
        font-weight:950;
        margin-bottom:3px;
      }

      .dofa-ai-help{
        color:#516174;
        font-size:.76rem;
        line-height:1.35;
      }

      .dofa-ai-btn{
        flex:0 0 auto;
        border:none;
        border-radius:10px !important;
        padding:9px 16px !important;
        color:#ffffff !important;
        background:linear-gradient(135deg,#6f42c1,#3b82f6);
        font-size:.78rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(76,81,191,.20);
      }

      .dofa-ai-btn:hover,
      .dofa-ai-btn:focus{
        color:#ffffff !important;
        transform:translateY(-1px);
        box-shadow:0 10px 19px rgba(76,81,191,.26);
      }

      .dofa-ai-btn:disabled{
        opacity:.75;
        transform:none;
      }

      .dofa-ai-status{
        display:none;
        margin:0 0 12px 0;
        padding:9px 12px;
        border-radius:10px;
        font-size:.76rem;
        font-weight:700;
      }

      .dofa-ai-status.is-visible{
        display:block;
      }

      .dofa-ai-status.is-info{
        color:#0b4a8f;
        background:#eaf4ff;
        border:1px solid #b9d5f4;
      }

      .dofa-ai-status.is-success{
        color:#166534;
        background:#ecfdf3;
        border:1px solid #a7e2bd;
      }

      .dofa-ai-status.is-error{
        color:#991b1b;
        background:#fff1f2;
        border:1px solid #fecdd3;
      }

      .dofa-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .dofa-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .dofa-bottom-actions .btn-primary,
      .dofa-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .dofa-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .dofa-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .dofa-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .dofa-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .dofa-header-card{
          min-height:88px;
        }

        .dofa-title{
          font-size:1.2rem;
        }

        .dofa-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){

        .dofa-ai-panel{
          align-items:stretch;
          flex-direction:column;
          gap:10px;
        }

        .dofa-ai-btn{
          width:100%;
        }

        .dofa-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .dofa-header-overlay::before{
          margin:0;
        }

        .dofa-bottom-actions .btn,
        .dofa-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, today=date.today().strftime("%Y-%m-%d"), f=f, d=d, o=o, a=a)

    return render_template_string(BASE, content=content)


# =================================
# Listado DOFA
# =================================

@app.route('/dofa/list')
@login_required
def dofa_list():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "DOFA"):
        flash("No tiene permiso para acceder al módulo DOFA.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == 'auditor')
    rows = DofaAnalisis.query.order_by(DofaAnalisis.fecha.desc(), DofaAnalisis.id.desc()).all()

    content = render_template_string("""
    <div class="dofalist-shell">

      <div class="dofalist-header-card">
        <div class="dofalist-header-overlay">
          <div class="dofalist-header-text">
            <h3 class="dofalist-title m-0">Listado DOFA</h3>
            <div class="dofalist-subtitle">
              Consulta, visualización y gestión de matrices DOFA según el perfil del usuario
            </div>
          </div>
        </div>
      </div>

      <div class="dofalist-header-actions">
        <div class="d-flex gap-2 flex-wrap justify-content-center">

          {% if not read_only %}
            <a href="{{ url_for('dofa_new') }}"
               class="btn btn-info text-white rounded-pill px-4 fw-semibold"
               onclick="showLoader()">
              ➕ Nuevo
            </a>
          {% endif %}
        </div>
      </div>

      <div class="dofalist-search-card">
        <div class="dofalist-search-body">
          <div class="row g-2 align-items-center">
            <div class="col-md-8">
              <div class="input-group">
                <span class="input-group-text bg-white">🔎</span>
                <input id="qDofa"
                       class="form-control"
                       placeholder="Buscar por título, creado por, fecha..."
                       autocomplete="off">
              </div>
            </div>
            <div class="col-md-4 text-md-end">
              <span class="badge rounded-pill bg-dark-subtle text-dark px-3 py-2">
                Total: <span id="cntDofa">{{ rows|length }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="dofalist-table-card">
        <div class="dofalist-table-card-body">
          <div class="dofalist-table-wrap">
            <div class="table-responsive">
              <table class="table table-hover align-middle mb-0 dofalist-table" id="tblDofa">
                <thead class="table-light">
                  <tr>
                    <th style="width:80px;">ID</th>
                    <th>Título</th>
                    <th style="width:140px;">Fecha</th>
                    <th style="width:180px;">Creado por</th>
                    <th class="text-end" style="width:320px;">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {% for r in rows %}
                    <tr class="dofa-row"
                        data-search="{{ (r.id|string) ~ ' ' ~ (r.titulo or '') ~ ' ' ~ (r.creado_por or '') ~ ' ' ~ (r.fecha|string) | lower }}">
                      <td class="text-muted">#{{ r.id }}</td>
                      <td class="fw-semibold">{{ r.titulo }}</td>
                      <td>{{ r.fecha }}</td>
                      <td>{{ r.creado_por or "" }}</td>
                      <td class="text-end">

                        <a class="btn btn-sm btn-outline-info rounded-pill"
                           href="{{ url_for('dofa_view', dofa_id=r.id) }}"
                           onclick="showLoader()">
                          👁 Ver
                        </a>

                        {% if not read_only %}
                          <a class="btn btn-sm btn-outline-primary rounded-pill"
                             href="{{ url_for('dofa_edit', dofa_id=r.id) }}"
                             onclick="showLoader()">
                            ✏️ Editar
                          </a>

                          <form method="POST"
                                action="{{ url_for('dofa_delete', dofa_id=r.id) }}"
                                style="display:inline"
                                onsubmit="return confirm('¿Eliminar este DOFA?');">
                            <button class="btn btn-sm btn-outline-danger rounded-pill">
                              🗑 Eliminar
                            </button>
                          </form>
                        {% endif %}
                      </td>
                    </tr>
                  {% endfor %}

                  {% if not rows %}
                    <tr>
                      <td colspan="5" class="text-center text-muted py-5">
                        No hay DOFAs registrados.
                        {% if not read_only %}
                          <div class="mt-3">
                            <a href="{{ url_for('dofa_new') }}"
                               class="btn btn-info text-white rounded-pill px-4 fw-semibold"
                               onclick="showLoader()">
                              ➕ Crear el primero
                            </a>
                          </div>
                        {% endif %}
                      </td>
                    </tr>
                  {% endif %}
                </tbody>
              </table>
            </div>
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

      .dofalist-shell{
        width:96%;
        max-width:1450px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI UNIFICADO
      ========================== */
      .dofalist-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .dofalist-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .dofalist-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .dofalist-header-overlay::before{
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
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .dofalist-header-text::before{
        content:"SGSI · Listado DOFA";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .dofalist-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .dofalist-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         ACCIONES
      ========================== */
      .dofalist-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .dofalist-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .dofalist-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .dofalist-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARDS
      ========================== */
      .dofalist-search-card,
      .dofalist-table-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .dofalist-search-card{
        margin-bottom:14px;
      }

      .dofalist-search-body,
      .dofalist-table-card-body{
        padding:14px 16px;
      }

      /* =========================
         FORMULARIO BÚSQUEDA
      ========================== */
      .dofalist-search-body .form-control{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:36px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .dofalist-search-body .btn{
        border-radius:10px;
        font-size:.80rem;
        font-weight:900;
      }

      /* =========================
         TABLA SGSI
      ========================== */
      .dofalist-table-wrap{
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
        overflow:auto;
      }

      .dofalist-table{
        margin-bottom:0;
        font-size:.80rem;
      }

      .dofalist-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        padding:10px;
      }

      .dofalist-table td{
        vertical-align:middle;
        padding:9px;
        border-bottom:1px solid #e5edf7;
      }

      .dofalist-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .dofalist-table tbody tr:hover{
        background:#eef6ff;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .dofalist-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .dofalist-header-card{
          min-height:88px;
        }

        .dofalist-title{
          font-size:1.2rem;
        }

        .dofalist-search-body,
        .dofalist-table-card-body{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .dofalist-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .dofalist-header-overlay::before{
          margin:0;
        }

        .dofalist-header-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      (function(){
        const q = document.getElementById("qDofa");
        const rows = Array.from(document.querySelectorAll("#tblDofa .dofa-row"));
        const cnt = document.getElementById("cntDofa");
        if(!q || !rows.length || !cnt) return;

        function apply(){
          const s = (q.value || "").toLowerCase().trim();
          let vis = 0;
          rows.forEach(tr => {
            const hay = (tr.getAttribute("data-search") || "");
            const show = (!s || hay.includes(s));
            tr.style.display = show ? "" : "none";
            if(show) vis++;
          });
          cnt.textContent = vis;
        }
        q.addEventListener("input", apply);
        apply();
      })();
    </script>
    """, rows=rows, read_only=read_only)

    return render_template_string(BASE, content=content)


# =================================
# Ver DOFA
# =================================

@app.route('/dofa/<int:dofa_id>')
@login_required
def dofa_view(dofa_id):
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "DOFA"):
        flash("No tiene permiso para acceder al módulo DOFA.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == 'auditor')
    r = DofaAnalisis.query.get_or_404(dofa_id)

    content = render_template_string("""
    <div class="dofaview-shell">

      <div class="dofaview-header-card">
        <div class="dofaview-header-overlay">
          <div class="dofaview-header-text">
            <h3 class="dofaview-title m-0">Ver DOFA</h3>
            <div class="dofaview-subtitle">
              {{ r.titulo }} • {{ r.fecha }}
              {% if r.creado_por %} • Creado por: {{ r.creado_por }}{% endif %}
            </div>
          </div>
        </div>
      </div>

      <div class="dofaview-header-actions">
        <div class="d-flex gap-2 flex-wrap justify-content-center">
          <a href="{{ url_for('dofa_list') }}"
             class="btn rounded-pill px-4 fw-semibold dofaview-back-btn"
             onclick="showLoader()">
            ⬅ Volver al Listado DOFA
          </a>

          {% if not read_only %}
            <a href="{{ url_for('dofa_edit', dofa_id=r.id) }}"
               class="btn btn-info text-white rounded-pill px-4 fw-semibold"
               onclick="showLoader()">
              ✏️ Editar
            </a>
          {% endif %}
        </div>
      </div>

      <div class="dofaview-card">
        <div class="dofaview-card-body">

          <div class="row g-3">

            <div class="col-md-6">
              <div class="quad quad-f">
                <div class="quad-h">✅ Fortalezas</div>
                <div class="quad-box">{{ (r.fortalezas or '') }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-o">
                <div class="quad-h">🌟 Oportunidades</div>
                <div class="quad-box">{{ (r.oportunidades or '') }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-d">
                <div class="quad-h">⚠️ Debilidades</div>
                <div class="quad-box">{{ (r.debilidades or '') }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-a">
                <div class="quad-h">🛡️ Amenazas</div>
                <div class="quad-box">{{ (r.amenazas or '') }}</div>
              </div>
            </div>

          </div>

          <hr class="my-4">

          <div class="accordion dofaview-accordion" id="accEstrategiasVer">
            <div class="accordion-item">
              <h2 class="accordion-header" id="hEV">
                <button class="accordion-button collapsed fw-semibold"
                        type="button"
                        data-bs-toggle="collapse"
                        data-bs-target="#cEV"
                        aria-expanded="false"
                        aria-controls="cEV">
                  🧠 Estrategias FO / FA / DO / DA
                </button>
              </h2>
              <div id="cEV"
                   class="accordion-collapse collapse"
                   aria-labelledby="hEV"
                   data-bs-parent="#accEstrategiasVer">
                <div class="accordion-body">

                  <div class="row g-3">
                    <div class="col-md-6">
                      <div class="strat">
                        <div class="strat-h">FO (Fortalezas + Oportunidades)</div>
                        <div class="strat-box">{{ r.estrategias_fo or '' }}</div>
                      </div>
                    </div>

                    <div class="col-md-6">
                      <div class="strat">
                        <div class="strat-h">FA (Fortalezas + Amenazas)</div>
                        <div class="strat-box">{{ r.estrategias_fa or '' }}</div>
                      </div>
                    </div>

                    <div class="col-md-6">
                      <div class="strat">
                        <div class="strat-h">DO (Debilidades + Oportunidades)</div>
                        <div class="strat-box">{{ r.estrategias_do or '' }}</div>
                      </div>
                    </div>

                    <div class="col-md-6">
                      <div class="strat">
                        <div class="strat-h">DA (Debilidades + Amenazas)</div>
                        <div class="strat-box">{{ r.estrategias_da or '' }}</div>
                      </div>
                    </div>
                  </div>

                </div>
              </div>
            </div>
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

      .dofaview-shell{
        width:96%;
        max-width:1450px;
        margin:10px auto 24px auto;
      }

      .dofaview-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .dofaview-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .dofaview-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .dofaview-header-overlay::before{
        content:"🧩";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .dofaview-header-text::before{
        content:"SGSI · Detalle DOFA";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .dofaview-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .dofaview-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .dofaview-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .dofaview-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .dofaview-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .dofaview-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .dofaview-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .dofaview-card-body{
        padding:16px 18px;
      }

      .quad{
        border-radius:16px;
        padding:12px;
        border:1px solid #dbe6f4;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .quad-h{
        font-weight:950;
        font-size:.86rem;
        margin-bottom:8px;
        color:#0f172a;
      }

      .quad-box{
        background:rgba(255,255,255,.92);
        border-radius:12px;
        padding:10px 12px;
        min-height:130px;
        white-space:pre-wrap;
        font-size:.80rem;
        line-height:1.38;
        color:#101827;
      }

      .quad-f{ background:rgba(25,135,84,.10); }
      .quad-o{ background:rgba(13,110,253,.10); }
      .quad-d{ background:rgba(255,193,7,.14); }
      .quad-a{ background:rgba(220,53,69,.10); }

      .strat{
        border-radius:14px;
        border:1px solid #dbe6f4;
        background:#f8fbff;
        padding:12px;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .strat-h{
        font-weight:950;
        font-size:.86rem;
        margin-bottom:8px;
        color:#0b4a8f;
      }

      .strat-box{
        background:rgba(255,255,255,.92);
        border-radius:12px;
        padding:10px 12px;
        white-space:pre-wrap;
        min-height:95px;
        font-size:.80rem;
        line-height:1.38;
        color:#101827;
      }

      .dofaview-accordion .accordion-item{
        border-radius:14px !important;
        overflow:hidden;
        border:1px solid #dbe6f4;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .dofaview-accordion .accordion-button{
        font-size:.84rem;
        font-weight:900;
        color:#0b4a8f;
        background:#eef5ff;
      }

      .dofaview-accordion .accordion-button:not(.collapsed){
        color:#062b55;
        background:#dbeafe;
        box-shadow:none;
      }

      @media (max-width:992px){
        .dofaview-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .dofaview-header-card{
          min-height:88px;
        }

        .dofaview-title{
          font-size:1.2rem;
        }

        .dofaview-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .dofaview-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .dofaview-header-overlay::before{
          margin:0;
        }

        .dofaview-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, r=r, read_only=read_only)

    return render_template_string(BASE, content=content)


# =================================
# Editar DOFA
# =================================

@app.route('/dofa/<int:dofa_id>/edit', methods=['GET', 'POST'])
@login_required
def dofa_edit(dofa_id):
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "DOFA"):
        flash("No tiene permiso para acceder al módulo DOFA.", "danger")
        return redirect(url_for('menu'))

    if user.role == 'auditor':
        flash("Perfil auditor: solo lectura.", "warning")
        return redirect(url_for('dofa_view', dofa_id=dofa_id))

    r = DofaAnalisis.query.get_or_404(dofa_id)

    if request.method == 'POST':
        r.titulo = (request.form.get('titulo') or r.titulo).strip()

        fecha_str = (request.form.get('fecha') or "").strip()
        try:
            r.fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else r.fecha
        except Exception:
            pass

        r.fortalezas = request.form.get('fortalezas') or ""
        r.oportunidades = request.form.get('oportunidades') or ""
        r.debilidades = request.form.get('debilidades') or ""
        r.amenazas = request.form.get('amenazas') or ""

        r.estrategias_fo = request.form.get('estrategias_fo') or ""
        r.estrategias_fa = request.form.get('estrategias_fa') or ""
        r.estrategias_do = request.form.get('estrategias_do') or ""
        r.estrategias_da = request.form.get('estrategias_da') or ""

        db.session.commit()
        flash("DOFA actualizado correctamente.", "success")
        return redirect(url_for('dofa_view', dofa_id=r.id))

    content = render_template_string("""
    <div class="dofaedit-shell">

      <div class="dofaedit-header-card">
        <div class="dofaedit-header-overlay">
          <div class="dofaedit-header-text">
            <h3 class="dofaedit-title m-0">Editar DOFA</h3>
            <div class="dofaedit-subtitle">
              {{ r.titulo }} • {{ r.fecha }}
            </div>
          </div>
        </div>
      </div>

      <div class="dofaedit-header-actions">
        <div class="d-flex gap-2 flex-wrap justify-content-center">
          <a href="{{ url_for('dofa_list') }}"
             class="btn rounded-pill px-4 fw-semibold dofaedit-back-btn"
             onclick="showLoader()">
            ⬅ Volver al Listado DOFA
          </a>
        </div>
      </div>

      <form method="POST" class="dofaedit-card">
        <div class="dofaedit-card-body">

          <div class="row g-3">
            <div class="col-md-8">
              <label class="form-label fw-semibold">Título</label>
              <input type="text" name="titulo" class="form-control" value="{{ r.titulo }}">
            </div>
            <div class="col-md-4">
              <label class="form-label fw-semibold">Fecha</label>
              <input type="date" name="fecha" class="form-control" value="{{ r.fecha }}">
            </div>
          </div>

          <hr class="my-4">

          <div class="row g-3">
            <div class="col-md-6">
              <div class="quad quad-f">
                <div class="quad-h">✅ Fortalezas</div>
                <textarea name="fortalezas" class="form-control quad-ta" rows="7" placeholder="- ...">{{ r.fortalezas or "" }}</textarea>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-o">
                <div class="quad-h">🌟 Oportunidades</div>
                <textarea name="oportunidades" class="form-control quad-ta" rows="7" placeholder="- ...">{{ r.oportunidades or "" }}</textarea>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-d">
                <div class="quad-h">⚠️ Debilidades</div>
                <textarea name="debilidades" class="form-control quad-ta" rows="7" placeholder="- ...">{{ r.debilidades or "" }}</textarea>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-a">
                <div class="quad-h">🛡️ Amenazas</div>
                <textarea name="amenazas" class="form-control quad-ta" rows="7" placeholder="- ...">{{ r.amenazas or "" }}</textarea>
              </div>
            </div>
          </div>

          <hr class="my-4">


          <div class="dofa-ai-panel">
            <div class="dofa-ai-copy">
              <div class="dofa-ai-title">✨ Generación y actualización con IA</div>
              <div class="dofa-ai-help">
                La IA toma los cuatro cuadrantes tal como aparecen en esta edición. Las estrategias
                generadas quedan completamente editables y también pueden escribirse manualmente.
              </div>
            </div>
            <button type="button"
                    class="btn dofa-ai-btn"
                    data-no-progress="true"
                    onclick="generarEstrategiasDofaIA(this, 'cEE')">
              <span class="dofa-ai-btn-label">🧠 Generar o regenerar con IA</span>
            </button>
          </div>
          <div class="dofa-ai-status" role="status" aria-live="polite"></div>

          <div class="accordion dofaedit-accordion" id="accEstrategiasEdit">
            <div class="accordion-item">
              <h2 class="accordion-header" id="hEE">
                <button class="accordion-button collapsed fw-semibold"
                        type="button"
                        data-bs-toggle="collapse"
                        data-bs-target="#cEE"
                        aria-expanded="false"
                        aria-controls="cEE">
                  🧠 Estrategias FO / FA / DO / DA
                </button>
              </h2>
              <div id="cEE"
                   class="accordion-collapse collapse"
                   aria-labelledby="hEE"
                   data-bs-parent="#accEstrategiasEdit">
                <div class="accordion-body">

                  <div class="row g-3">
                    <div class="col-md-6">
                      <label class="form-label fw-semibold">FO (Fortalezas + Oportunidades)</label>
                      <textarea name="estrategias_fo" class="form-control" rows="4">{{ r.estrategias_fo or "" }}</textarea>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label fw-semibold">FA (Fortalezas + Amenazas)</label>
                      <textarea name="estrategias_fa" class="form-control" rows="4">{{ r.estrategias_fa or "" }}</textarea>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label fw-semibold">DO (Debilidades + Oportunidades)</label>
                      <textarea name="estrategias_do" class="form-control" rows="4">{{ r.estrategias_do or "" }}</textarea>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label fw-semibold">DA (Debilidades + Amenazas)</label>
                      <textarea name="estrategias_da" class="form-control" rows="4">{{ r.estrategias_da or "" }}</textarea>
                    </div>
                  </div>

                </div>
              </div>
            </div>
          </div>

          <div class="dofaedit-bottom-actions">
            <button class="btn btn-success rounded-pill px-4 fw-semibold">
              💾 Guardar cambios
            </button>

            <a href="{{ url_for('dofa_view', dofa_id=r.id) }}"
               class="btn rounded-pill px-4 fw-semibold dofaedit-cancel-btn"
               onclick="showLoader()">
              Cancelar
            </a>
          </div>

        </div>
      </form>

    </div>


    <script>
    (function () {
      if (window.__GRAC_DOFA_AI_READY__) return;
      window.__GRAC_DOFA_AI_READY__ = true;

      function showStrategySection(collapseId) {
        const collapseElement = document.getElementById(collapseId);
        if (!collapseElement) return;

        try {
          if (window.bootstrap && window.bootstrap.Collapse) {
            window.bootstrap.Collapse
              .getOrCreateInstance(collapseElement, {toggle: false})
              .show();
          } else {
            collapseElement.classList.add('show');
          }
        } catch (_error) {
          collapseElement.classList.add('show');
        }

        const toggle = document.querySelector('[data-bs-target="#' + collapseId + '"]');
        if (toggle) {
          toggle.classList.remove('collapsed');
          toggle.setAttribute('aria-expanded', 'true');
        }
      }

      function setDofaAiStatus(statusElement, message, kind) {
        if (!statusElement) return;
        statusElement.textContent = message || '';
        statusElement.className = 'dofa-ai-status is-visible ' + (kind || 'is-info');
      }

      window.generarEstrategiasDofaIA = async function (button, collapseId) {
        const form = button ? button.closest('form') : null;
        const panel = button ? button.closest('.dofa-ai-panel') : null;
        const statusElement = panel && panel.nextElementSibling &&
          panel.nextElementSibling.classList.contains('dofa-ai-status')
            ? panel.nextElementSibling
            : null;

        if (!form) {
          setDofaAiStatus(statusElement, 'No se encontró el formulario de la matriz DOFA.', 'is-error');
          return;
        }

        const names = [
          'fortalezas',
          'oportunidades',
          'debilidades',
          'amenazas',
          'estrategias_fo',
          'estrategias_fa',
          'estrategias_do',
          'estrategias_da'
        ];

        const fields = {};
        names.forEach(function (name) {
          fields[name] = form.querySelector('[name="' + name + '"]');
        });

        const sourceLabels = {
          fortalezas: 'Fortalezas',
          oportunidades: 'Oportunidades',
          debilidades: 'Debilidades',
          amenazas: 'Amenazas'
        };

        const missing = Object.keys(sourceLabels).filter(function (name) {
          return !fields[name] || !String(fields[name].value || '').trim();
        });

        if (missing.length) {
          setDofaAiStatus(
            statusElement,
            'Complete los cuatro cuadrantes. Falta información en: ' +
              missing.map(function (name) { return sourceLabels[name]; }).join(', ') + '.',
            'is-error'
          );
          return;
        }

        const strategyNames = [
          'estrategias_fo',
          'estrategias_fa',
          'estrategias_do',
          'estrategias_da'
        ];
        const hasExistingStrategies = strategyNames.some(function (name) {
          return fields[name] && String(fields[name].value || '').trim();
        });

        if (
          hasExistingStrategies &&
          !window.confirm(
            'Ya existen estrategias registradas. La generación con IA reemplazará temporalmente ' +
            'el contenido actual de FO, FA, DO y DA. Podrá editarlo antes de guardar. ¿Desea continuar?'
          )
        ) {
          return;
        }

        const originalHtml = button.innerHTML;
        button.disabled = true;
        button.innerHTML =
          '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Generando...';
        setDofaAiStatus(
          statusElement,
          'Analizando la matriz y construyendo estrategias FO, FA, DO y DA...',
          'is-info'
        );

        const payload = {
          fortalezas: fields.fortalezas.value,
          oportunidades: fields.oportunidades.value,
          debilidades: fields.debilidades.value,
          amenazas: fields.amenazas.value
        };

        try {
          const response = await fetch("{{ url_for('dofa_generar_estrategias_ia') }}", {
            method: 'POST',
            credentials: 'same-origin',
            cache: 'no-store',
            headers: {
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(payload)
          });

          let data = {};
          try {
            data = await response.json();
          } catch (_jsonError) {
            data = {};
          }

          if (!response.ok || !data.ok) {
            throw new Error(
              data.message || 'No fue posible generar las estrategias con IA.'
            );
          }

          const strategies = data.estrategias || {};
          const labels = {
            estrategias_fo: 'FO',
            estrategias_fa: 'FA',
            estrategias_do: 'DO',
            estrategias_da: 'DA'
          };

          strategyNames.forEach(function (name) {
            if (!fields[name] || !String(strategies[name] || '').trim()) {
              throw new Error('La IA no devolvió una estrategia válida para ' + labels[name] + '.');
            }
          });

          strategyNames.forEach(function (name) {
            fields[name].value = strategies[name];
            fields[name].dispatchEvent(new Event('input', {bubbles: true}));
          });

          showStrategySection(collapseId);
          setDofaAiStatus(
            statusElement,
            data.message ||
              'Estrategias generadas. Puede editarlas antes de guardar la matriz DOFA.',
            'is-success'
          );

          if (fields.estrategias_fo) {
            setTimeout(function () {
              fields.estrategias_fo.focus();
              fields.estrategias_fo.scrollIntoView({behavior: 'smooth', block: 'center'});
            }, 250);
          }
        } catch (error) {
          setDofaAiStatus(
            statusElement,
            error && error.message
              ? error.message
              : 'No fue posible generar las estrategias con IA.',
            'is-error'
          );
        } finally {
          button.disabled = false;
          button.innerHTML = originalHtml;
        }
      };
    })();
    </script>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .dofaedit-shell{
        width:96%;
        max-width:1450px;
        margin:10px auto 24px auto;
      }

      .dofaedit-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .dofaedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .dofaedit-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .dofaedit-header-overlay::before{
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
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .dofaedit-header-text::before{
        content:"SGSI · Edición DOFA";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .dofaedit-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .dofaedit-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .dofaedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .dofaedit-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .dofaedit-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .dofaedit-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .dofaedit-light-btn{
        background:rgba(255,255,255,.14);
        color:#ffffff;
        border:1px solid rgba(255,255,255,.65);
      }

      .dofaedit-light-btn:hover{
        background:rgba(255,255,255,.22);
        color:#ffffff;
      }

      .dofaedit-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .dofaedit-card-body{
        padding:16px 18px;
      }

      .dofaedit-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .dofaedit-card .form-control,
      .dofaedit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
      }

      .dofaedit-card textarea{
        min-height:70px;
        resize:vertical;
      }

      .dofaedit-card .form-control:focus,
      .dofaedit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .quad{
        border-radius:16px;
        padding:12px;
        border:1px solid #dbe6f4;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .quad-h{
        font-weight:950;
        font-size:.86rem;
        margin-bottom:8px;
        color:#0f172a;
      }

      .quad-ta{
        background:rgba(255,255,255,.92) !important;
        border-radius:12px;
      }

      .quad-f{ background:rgba(25,135,84,.10); }
      .quad-o{ background:rgba(13,110,253,.10); }
      .quad-d{ background:rgba(255,193,7,.14); }
      .quad-a{ background:rgba(220,53,69,.10); }

      .dofaedit-accordion .accordion-item{
        border-radius:14px !important;
        overflow:hidden;
        border:1px solid #dbe6f4;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .dofaedit-accordion .accordion-button{
        font-size:.84rem;
        font-weight:900;
        color:#0b4a8f;
        background:#eef5ff;
      }

      .dofaedit-accordion .accordion-button:not(.collapsed){
        color:#062b55;
        background:#dbeafe;
        box-shadow:none;
      }


      .dofa-ai-panel{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:18px;
        padding:13px 15px;
        margin-bottom:10px;
        border:1px solid #b9d5f4;
        border-radius:14px;
        background:linear-gradient(135deg,#eef6ff,#f8fbff);
        box-shadow:0 6px 14px rgba(15,72,133,.08);
      }

      .dofa-ai-copy{
        min-width:0;
      }

      .dofa-ai-title{
        color:#0b4a8f;
        font-size:.86rem;
        font-weight:950;
        margin-bottom:3px;
      }

      .dofa-ai-help{
        color:#516174;
        font-size:.76rem;
        line-height:1.35;
      }

      .dofa-ai-btn{
        flex:0 0 auto;
        border:none;
        border-radius:10px !important;
        padding:9px 16px !important;
        color:#ffffff !important;
        background:linear-gradient(135deg,#6f42c1,#3b82f6);
        font-size:.78rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(76,81,191,.20);
      }

      .dofa-ai-btn:hover,
      .dofa-ai-btn:focus{
        color:#ffffff !important;
        transform:translateY(-1px);
        box-shadow:0 10px 19px rgba(76,81,191,.26);
      }

      .dofa-ai-btn:disabled{
        opacity:.75;
        transform:none;
      }

      .dofa-ai-status{
        display:none;
        margin:0 0 12px 0;
        padding:9px 12px;
        border-radius:10px;
        font-size:.76rem;
        font-weight:700;
      }

      .dofa-ai-status.is-visible{
        display:block;
      }

      .dofa-ai-status.is-info{
        color:#0b4a8f;
        background:#eaf4ff;
        border:1px solid #b9d5f4;
      }

      .dofa-ai-status.is-success{
        color:#166534;
        background:#ecfdf3;
        border:1px solid #a7e2bd;
      }

      .dofa-ai-status.is-error{
        color:#991b1b;
        background:#fff1f2;
        border:1px solid #fecdd3;
      }

      .dofaedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .dofaedit-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .dofaedit-bottom-actions .btn-primary,
      .dofaedit-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .dofaedit-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .dofaedit-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .dofaedit-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .dofaedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .dofaedit-header-card{
          min-height:88px;
        }

        .dofaedit-title{
          font-size:1.2rem;
        }

        .dofaedit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){

        .dofa-ai-panel{
          align-items:stretch;
          flex-direction:column;
          gap:10px;
        }

        .dofa-ai-btn{
          width:100%;
        }

        .dofaedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .dofaedit-header-overlay::before{
          margin:0;
        }

        .dofaedit-bottom-actions .btn,
        .dofaedit-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, r=r)

    return render_template_string(BASE, content=content)


# =================================
# Eliminar DOFA
# =================================

@app.route('/dofa/<int:dofa_id>/delete', methods=['POST'])
@login_required
def dofa_delete(dofa_id):
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "DOFA"):
        flash("No tiene permiso para acceder al módulo DOFA.", "danger")
        return redirect(url_for('menu'))

    if user.role == 'auditor':
        flash("Perfil auditor: solo lectura.", "warning")
        return redirect(url_for('dofa_list'))

    r = DofaAnalisis.query.get_or_404(dofa_id)
    db.session.delete(r)
    db.session.commit()
    flash("DOFA eliminado correctamente.", "success")
    return redirect(url_for('dofa_list'))


# ==========================================================================================================================================
#                                                               Fin Módulo DOFA
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                               Módulo de Listado de Documentos Maestros
# ==========================================================================================================================================

DOCS_ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx"}

def docs_allowed_file(filename: str) -> bool:
    if not filename:
        return False
    ext = os.path.splitext(filename)[1].lower().strip()
    if not ext:
        return False
    return ext[1:] in DOCS_ALLOWED_EXTENSIONS

def docs_unique_store_name(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower().strip()
    return f"{uuid.uuid4().hex}{ext}"

def fmt_kb(size):
    if not size:
        return "0 KB"
    return f"{round(size / 1024, 1)} KB"


# ========================================
# ENTRADA DIRECTA — Listado Maestro de Documentos
# ========================================
@app.route('/docs_menu')
@login_required
def docs_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Listado Maestro de Documentos"):
        flash("No tiene permiso para acceder al listado maestro de documentos.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('docs_matriz'))



# ========================================
# Configuración de tipos documentales
# ========================================
@app.route('/docs_tipos_config', methods=['GET', 'POST'])
@login_required
def docs_tipos_config():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede configurar los tipos de documentos.", "danger")
        return redirect(url_for('docs_menu'))

    if user.role != 'admin' and not verificar_permiso(user, "Listado Maestro de Documentos"):
        flash("No tiene permiso para agregar configuraciones al listado maestro de documentos.", "danger")
        return redirect(url_for('docs_menu'))

    if request.method == 'POST':
        rid = request.form.get('id', type=int)

        nombre = (request.form.get('nombre') or '').strip()
        descripcion = (request.form.get('descripcion') or '').strip()
        min_meses_revision = request.form.get('min_meses_revision', type=int) or 0

        if not nombre:
            flash("El nombre del tipo de documento es obligatorio.", "danger")
            return redirect(url_for('docs_tipos_config'))

        if rid:
            item = DocTipoDocumento.query.get(rid)
            if not item:
                flash("Registro no encontrado.", "danger")
                return redirect(url_for('docs_tipos_config'))
        else:
            item = DocTipoDocumento()
            db.session.add(item)

        item.nombre = nombre
        item.descripcion = descripcion
        item.min_meses_revision = min_meses_revision

        db.session.commit()
        flash("Tipo de documento guardado correctamente.", "success")
        return redirect(url_for('docs_tipos_config'))

    edit_id   = request.args.get('edit', type=int)
    edit_item = DocTipoDocumento.query.get(edit_id) if edit_id else None
    items     = DocTipoDocumento.query.order_by(DocTipoDocumento.id.desc()).all()

    html = """
    <div class="doccfg-shell">

      <div class="doccfg-header-card">
        <div class="doccfg-header-overlay">
          <div class="doccfg-header-text">
            <h3 class="doccfg-title m-0">Configuración Nombre de Documentos</h3>
            <div class="doccfg-subtitle">
              Administración de tipos documentales, descripción y periodicidad mínima de revisión
            </div>
          </div>
        </div>
      </div>

      <div class="doccfg-header-actions">
        <a href="{{ url_for('docs_menu') }}"
           class="btn rounded-pill px-5 fw-bold doccfg-back-btn">
          ⬅ Volver al Menú Listado Maestro
        </a>
      </div>

      <div class="doccfg-form-card">
        <div class="doccfg-form-card-body">
          <form method="post">
            {% if edit_item %}
              <input type="hidden" name="id" value="{{ edit_item.id }}">
            {% endif %}

            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Tipo de documento</label>
                <input type="text"
                       name="nombre"
                       class="form-control"
                       value="{{ edit_item.nombre if edit_item else '' }}"
                       required>
              </div>

              <div class="col-md-6">
                <label class="form-label">Descripción</label>
                <input type="text"
                       name="descripcion"
                       class="form-control"
                       value="{{ edit_item.descripcion if edit_item else '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Mínimo tiempo de revisión (meses)</label>
                <input type="number"
                       name="min_meses_revision"
                       class="form-control"
                       min="0"
                       value="{{ edit_item.min_meses_revision if edit_item and edit_item.min_meses_revision is not none else 0 }}">
                <small class="text-muted">Ejemplo: 12 = revisar al menos una vez al año.</small>
              </div>
            </div>

            <div class="doccfg-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                {{ 'Guardar cambios' if edit_item else 'Agregar' }}
              </button>

              {% if edit_item %}
                <a href="{{ url_for('docs_tipos_config') }}"
                   class="btn rounded-pill px-4 fw-bold doccfg-cancel-btn">
                  Cancelar
                </a>
              {% endif %}
            </div>
          </form>
        </div>
      </div>

      <div class="doccfg-table-card">
        <div class="doccfg-table-card-body">
          <div class="doccfg-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-sm align-middle doccfg-table mb-0">
                <thead class="table-secondary">
                  <tr class="text-center">
                    <th>Tipo de documento</th>
                    <th>Descripción</th>
                    <th>Mín. revisión (meses)</th>
                    <th style="width:18%">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {% for it in items %}
                    <tr>
                      <td>{{ it.nombre }}</td>
                      <td>{{ it.descripcion or '—' }}</td>
                      <td class="text-center">
                        {{ it.min_meses_revision if it.min_meses_revision is not none else '0' }}
                      </td>
                      <td class="text-center">
                        <a href="{{ url_for('docs_tipos_config', edit=it.id) }}"
                           class="btn btn-warning btn-sm rounded-pill px-3">
                          Editar
                        </a>
                        <a href="{{ url_for('docs_tipos_delete', id=it.id) }}"
                           class="btn btn-danger btn-sm rounded-pill px-3"
                           onclick="return confirm('¿Eliminar este tipo de documento?');">
                          Eliminar
                        </a>
                      </td>
                    </tr>
                  {% endfor %}

                  {% if items|length == 0 %}
                    <tr>
                      <td colspan="4" class="text-center text-muted py-4">
                        Sin tipos configurados
                      </td>
                    </tr>
                  {% endif %}
                </tbody>
              </table>
            </div>
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

      .doccfg-shell{
        width:96%;
        max-width:1400px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI
      ========================== */
      .doccfg-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .doccfg-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .doccfg-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .doccfg-header-overlay::before{
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
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .doccfg-header-text::before{
        content:"SGSI · Configuración Documental";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .doccfg-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .doccfg-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         ACCIONES
      ========================== */
      .doccfg-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .doccfg-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .doccfg-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .doccfg-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARDS
      ========================== */
      .doccfg-form-card,
      .doccfg-table-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .doccfg-form-card{
        margin-bottom:14px;
      }

      .doccfg-form-card-body,
      .doccfg-table-card-body{
        padding:14px 16px;
      }

      /* =========================
         FORMULARIO
      ========================== */
      .doccfg-form-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .doccfg-form-card .form-control,
      .doccfg-form-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:36px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .doccfg-form-card .form-control:focus,
      .doccfg-form-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      /* =========================
         BOTONES
      ========================== */
      .doccfg-bottom-actions{
        display:flex;
        justify-content:flex-start;
        gap:10px;
        flex-wrap:wrap;
        margin-top:16px;
      }

      .doccfg-bottom-actions .btn{
        border-radius:10px !important;
        min-height:36px;
        padding:7px 20px !important;
        font-size:.80rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .doccfg-bottom-actions .btn-primary,
      .doccfg-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .doccfg-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .doccfg-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .doccfg-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         TABLA SGSI
      ========================== */
      .doccfg-table-wrap{
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
        overflow:auto;
      }

      .doccfg-table{
        margin-bottom:0;
        font-size:.80rem;
      }

      .doccfg-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        padding:10px;
      }

      .doccfg-table td{
        padding:9px;
        border-bottom:1px solid #e5edf7;
      }

      .doccfg-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .doccfg-table tbody tr:hover{
        background:#eef6ff;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .doccfg-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .doccfg-header-card{
          min-height:88px;
        }

        .doccfg-title{
          font-size:1.2rem;
        }

        .doccfg-form-card-body,
        .doccfg-table-card-body{
          padding:12px;
        }

        .doccfg-bottom-actions{
          justify-content:center;
        }
      }

      @media (max-width:768px){
        .doccfg-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .doccfg-header-overlay::before{
          margin:0;
        }

        .doccfg-header-actions .btn,
        .doccfg-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(html, edit_item=edit_item, items=items)
    return render_template_string(BASE, content=Markup(inner))


# =========================
# Borrado tipos de documentos
# =========================
@app.route('/docs_tipos/delete/<int:id>')
@login_required
def docs_tipos_delete(id):
    item = DocTipoDocumento.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash("Tipo de documento eliminado.", "success")
    return redirect(url_for('docs_tipos_config'))


# =========================
# Agregar documentos
# =========================
@app.route('/docs/new', methods=['GET', 'POST'])
@login_required
def docs_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('docs_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Listado Maestro de Documentos"):
        flash("No tiene permiso para agregar configuraciones al listado maestro de documentos.", "danger")
        return redirect(url_for('docs_matriz'))

    tipos = DocTipoDocumento.query.order_by(DocTipoDocumento.nombre.asc()).all()

    if request.method == 'POST':
        tipo_id = request.form.get('tipo_id', type=int)
        codigo  = (request.form.get('codigo') or '').strip()
        inicial = (request.form.get('inicial') or '').strip()
        tipo_texto = (request.form.get('tipo_texto') or '').strip()
        num1   = request.form.get('num1', type=int)
        num2   = request.form.get('num2', type=int)
        num3   = request.form.get('num3', type=int)
        nombre_documento = (request.form.get('nombre_documento') or '').strip()
        version = request.form.get('version', type=int) or 1
        fecha_creacion_raw = (request.form.get('fecha_creacion') or '').strip()
        fecha_ultima_revision_raw = (request.form.get('fecha_ultima_revision') or '').strip()

        fecha_creacion = parse_fecha_flexible(fecha_creacion_raw)
        fecha_ultima_revision = parse_fecha_flexible(fecha_ultima_revision_raw)

        if not fecha_creacion:
            fecha_creacion = date.today()

        if not fecha_ultima_revision:
            fecha_ultima_revision = fecha_creacion

        estado  = (request.form.get('estado') or '').strip()
        control_cambios = (request.form.get('control_cambios') or '').strip()
        observaciones   = (request.form.get('observaciones') or '').strip()

        if not tipo_id or not nombre_documento:
            flash("Tipo de documento y nombre del documento son obligatorios.", "danger")
            return redirect(url_for('docs_new'))

        ultimo = DocMaestroDocumento.query.order_by(DocMaestroDocumento.item.desc()).first()
        next_item = (ultimo.item + 1) if ultimo and ultimo.item else 1

        doc = DocMaestroDocumento(
            item=next_item,
            tipo_id=tipo_id,
            codigo=codigo,
            inicial=inicial,
            tipo_texto=tipo_texto,
            num1=num1,
            num2=num2,
            num3=num3,
            nombre_documento=nombre_documento,
            version=version,
            fecha_creacion=fecha_creacion,
            fecha_ultima_revision=fecha_ultima_revision,
            estado=estado,
            control_cambios=control_cambios,
            observaciones=observaciones
        )

        db.session.add(doc)
        db.session.flush()

        os.makedirs(app.config['UPLOAD_DOCS_DIR'], exist_ok=True)

        fmain = request.files.get('archivo')
        if fmain and fmain.filename:
            orig = secure_filename(fmain.filename).strip()

            if not docs_allowed_file(orig):
                db.session.rollback()
                flash(f"Tipo de archivo no permitido: {orig}. Solo PDF, Word, Excel.", "danger")
                return redirect(url_for('docs_new'))

            store_name = docs_unique_store_name(orig)
            path = os.path.join(app.config['UPLOAD_DOCS_DIR'], store_name)
            fmain.save(path)

            doc.filename = store_name
            doc.original_name = orig
            doc.mime = fmain.mimetype or 'application/octet-stream'
            doc.size = os.path.getsize(path)

        db.session.commit()
        flash("Documento guardado correctamente.", "success")
        return redirect(url_for('docs_matriz'))

    html = """
    <div class="docsadd-shell">

      <div class="docsadd-header-card">
        <div class="docsadd-header-overlay">
          <div class="docsadd-header-text">
            <h3 class="docsadd-title m-0">Agregar Documento al Listado Maestro</h3>
            <div class="docsadd-subtitle">
              Registro y control de documentos del SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="docsadd-header-actions">
        <a href="{{ url_for('docs_matriz') }}"
           class="btn rounded-pill px-5 fw-bold docsadd-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="docsadd-form-card">
        <div class="docsadd-form-card-body">
          <form method="post" enctype="multipart/form-data">

            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Tipo de documento</label>
                <select name="tipo_id" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  {% for t in tipos %}
                    <option value="{{ t.id }}">{{ t.nombre }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Código</label>
                <input type="text" name="codigo" class="form-control">
              </div>

              <div class="col-md-4">
                <label class="form-label">Inicial</label>
                <input type="text" name="inicial" class="form-control">
              </div>

              <div class="col-md-4">
                <label class="form-label">Tipo</label>
                <input type="text" name="tipo_texto" class="form-control">
              </div>

              <div class="col-md-2">
                <label class="form-label">#1</label>
                <input type="number" name="num1" class="form-control">
              </div>

              <div class="col-md-2">
                <label class="form-label">#2</label>
                <input type="number" name="num2" class="form-control">
              </div>

              <div class="col-md-2">
                <label class="form-label">#3</label>
                <input type="number" name="num3" class="form-control">
              </div>

              <div class="col-md-6">
                <label class="form-label">Nombre del documento</label>
                <input type="text" name="nombre_documento" class="form-control" required>
              </div>

              <div class="col-md-6">
                <label class="form-label">Documento principal (PDF, Word, Excel)</label>
                <input type="file" name="archivo" class="form-control"
                       accept=".pdf,.doc,.docx,.xls,.xlsx">
              </div>

              <div class="col-md-2">
                <label class="form-label">Versión</label>
                <input type="number" name="version" class="form-control" min="1" value="1">
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha creación documento</label>
                <input type="date" name="fecha_creacion" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha última revisión</label>
                <input type="date" name="fecha_ultima_revision" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Estado</label>
                <select name="estado" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Vigente">Vigente</option>
                  <option value="Versión obsoleta">Versión obsoleta</option>
                </select>
              </div>

              <div class="col-md-12">
                <label class="form-label">Control de cambios</label>
                <textarea name="control_cambios" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Observaciones</label>
                <textarea name="observaciones" class="form-control" rows="2"></textarea>
              </div>

            </div>

            <div class="docsadd-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>
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

      .docsadd-shell{
        width:96%;
        max-width:1450px;
        margin:10px auto 24px auto;
      }

      .docsadd-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .docsadd-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .docsadd-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .docsadd-header-overlay::before{
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
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .docsadd-header-text::before{
        content:"SGSI · Agregar Documento";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .docsadd-title{
        color:#ffffff!important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .docsadd-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .docsadd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .docsadd-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .docsadd-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .docsadd-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .docsadd-form-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .docsadd-form-card-body{
        padding:16px 18px;
      }

      .docsadd-form-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .docsadd-form-card .form-control,
      .docsadd-form-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
      }

      .docsadd-form-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .docsadd-form-card .form-control:focus,
      .docsadd-form-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .docsadd-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin-top:18px;
      }

      .docsadd-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .docsadd-bottom-actions .btn-primary,
      .docsadd-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .docsadd-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      @media (max-width:992px){
        .docsadd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .docsadd-header-card{
          min-height:88px;
        }

        .docsadd-title{
          font-size:1.2rem;
        }

        .docsadd-form-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .docsadd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .docsadd-header-overlay::before{
          margin:0;
        }

        .docsadd-header-actions .btn,
        .docsadd-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(html, tipos=tipos)
    return render_template_string(BASE, content=Markup(inner))


def meses_entre(d_inicio: date, d_fin: date) -> int:
    anios = d_fin.year - d_inicio.year
    meses = d_fin.month - d_inicio.month
    total = anios * 12 + meses
    if d_fin.day < d_inicio.day:
        total -= 1
    return total

def parse_fecha_flexible(value) -> date | None:
    if value is None:
        return None

    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value

    s = str(value).strip()
    if not s or s in ("—", "-", "N/A", "NA", "None", "null"):
        return None

    s = s.replace("T", " ")
    if " " in s:
        s = s.split(" ")[0].strip()

    formatos = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y")
    for fmt in formatos:
        try:
            return dt.datetime.strptime(s, fmt).date()
        except Exception:
            pass

    return None

