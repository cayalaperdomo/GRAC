@app.route('/inventario_software/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def inventario_software_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Gestión de Activos de Información")
    ):
        flash("No tiene permiso para editar registros de activos de software.", "danger")
        return redirect(url_for('inventario_software'))

    item = InventarioSoftware.query.get_or_404(id)
    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()

    evidencias = InventarioSoftwareEvidencia.query.filter_by(
        registro_id=item.id
    ).order_by(InventarioSoftwareEvidencia.id.desc()).all()

    conf_opts = ValoracionConfidencialidad.query.order_by(ValoracionConfidencialidad.nivel_num.asc()).all()
    inte_opts = ValoracionIntegridad.query.order_by(ValoracionIntegridad.nivel_num.asc()).all()
    disp_opts = ValoracionDisponibilidad.query.order_by(ValoracionDisponibilidad.nivel_num.asc()).all()

    current_area = AreaEmpresa.query.filter_by(area=(item.area or '')).first()
    current_area_id = current_area.id if current_area else 0

    if request.method == 'POST':
        selected_area_id = request.form.get('area_id', type=int)
        selected_area = AreaEmpresa.query.get(selected_area_id) if selected_area_id else None

        item.area = selected_area.area if selected_area else ''
        item.division = (request.form.get('division') or '').strip()
        item.proceso = (request.form.get('proceso') or '').strip()
        item.nombre_activo = (request.form.get('nombre_activo') or '').strip()
        item.administrador = (request.form.get('administrador') or '').strip()
        item.dueno_tecnico = (request.form.get('dueno_tecnico') or '').strip()
        item.propietario = (request.form.get('propietario') or '').strip()
        item.medio = (request.form.get('medio') or '').strip()
        item.ubicacion_tipo = (request.form.get('ubicacion') or '').strip()
        item.ubicacion_nombre = (request.form.get('ubicacion_nombre') or '').strip()
        item.descripcion = (request.form.get('descripcion') or '').strip()
        item.accesos_autorizados = (request.form.get('accesos_autorizados') or '').strip()
        item.info_personal = request.form.get('info_personal') or 'No'
        item.info_regulada = request.form.get('info_regulada') or 'No'
        item.info_sensible_compania = request.form.get('info_sensible_compania') or 'No'
        item.info_sensible_clientes = request.form.get('info_sensible_clientes') or 'No'
        item.observaciones = (request.form.get('observaciones') or '').strip()

        try:
            item.c_nivel = int(request.form.get('conf_num') or 0)
            item.i_nivel = int(request.form.get('int_num') or 0)
            item.d_nivel = int(request.form.get('disp_num') or 0)
        except ValueError:
            item.c_nivel = item.i_nivel = item.d_nivel = 0

        if not (
            item.area and item.division and item.proceso and item.nombre_activo and
            item.administrador and item.dueno_tecnico and item.ubicacion_nombre and item.accesos_autorizados
        ):
            flash(
                "Campos obligatorios: Área, División, Proceso, Nombre, Administrador, Dueño Técnico, Nombre de la ubicación y Acceso Autorizado.",
                "danger"
            )
            return redirect(url_for('inventario_software_edit', id=item.id))

        for n in (item.c_nivel, item.i_nivel, item.d_nivel):
            if n < 1 or n > 5:
                flash("Los niveles C/I/D deben estar entre 1 y 5.", "danger")
                return redirect(url_for('inventario_software_edit', id=item.id))

        item.valor_activo = round((item.c_nivel + item.i_nivel + item.d_nivel) / 3)

        conf_row = ValoracionConfidencialidad.query.filter_by(nivel_num=item.c_nivel).first()
        item.etiqueta_conf_num = item.c_nivel
        item.etiqueta_conf_texto = conf_row.clasificacion if conf_row else f"Nivel {item.c_nivel}"

        crit_row = ValoracionCriticidadActivo.query.filter_by(nivel_num=item.valor_activo).first()
        item.criticidad_num = item.valor_activo
        item.criticidad_texto = crit_row.nivel_texto if crit_row else f"Nivel {item.valor_activo}"

        db.session.add(item)
        guardar_evidencias_inventario_software(item)
        db.session.commit()

        flash("Cambios guardados.", "success")
        return redirect(url_for('inventario_software_edit', id=item.id))

    html = """
    <div class="invsoftedit-shell">

      <div class="invsoftedit-header-card">
        <div class="invsoftedit-header-overlay">
          <div class="invsoftedit-header-text">
            <h3 class="invsoftedit-title m-0">Editar — Inventario de Software</h3>
            <div class="invsoftedit-subtitle">
              Actualización de activos de software del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="invsoftedit-header-actions">
        <a href="{{ url_for('inventario_software') }}"
           class="btn rounded-pill px-4 fw-bold invsoftedit-back-btn">
          ⬅ Volver a la Matriz
        </a>

        <a href="{{ url_for('inventario_software_detalle', id=item.id) }}"
           class="btn btn-info rounded-pill px-4 fw-bold text-white">
          Ver detalle
        </a>
      </div>

      <div class="invsoftedit-card">
        <div class="invsoftedit-card-body">

          <form id="formEditarInventarioSoftware" method="post" enctype="multipart/form-data">

            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Área</label>
                <select name="area_id" id="softArea" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}" {% if current_area_id == a.id %}selected{% endif %}>
                      {{ a.area }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">División</label>
                <select name="division" id="softDivision" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  {% if item.division %}
                    <option value="{{ item.division }}" selected>{{ item.division }}</option>
                  {% endif %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Proceso</label>
                <input type="text" name="proceso" class="form-control" required value="{{ item.proceso or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Nombre del Activo</label>
                <input type="text" name="nombre_activo" class="form-control" required value="{{ item.nombre_activo or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Administrador (Owner)</label>
                <input type="text" name="administrador" class="form-control" required value="{{ item.administrador or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Dueño Técnico</label>
                <input type="text" name="dueno_tecnico" class="form-control" required value="{{ item.dueno_tecnico or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Propietario</label>
                <input type="text" name="propietario" class="form-control" value="{{ item.propietario or '' }}">
              </div>

              <div class="col-md-9">
                <label class="form-label">Descripción</label>
                <textarea name="descripcion" class="form-control" rows="2">{{ item.descripcion or '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Medio</label>
                <select name="medio" class="form-select">
                  {% for opt in ['Aplicación Web','Aplicación de Escritorio','Aplicación de Servidor','Servicios con un Tercero'] %}
                    <option value="{{ opt }}" {% if item.medio == opt %}selected{% endif %}>{{ opt }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Ubicación</label>
                <select name="ubicacion" class="form-select">
                  {% for opt in ['Área','Servidor','Dominio/URL'] %}
                    <option value="{{ opt }}" {% if item.ubicacion_tipo == opt %}selected{% endif %}>{{ opt }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre de la ubicación</label>
                <input type="text" name="ubicacion_nombre" class="form-control" required value="{{ item.ubicacion_nombre or '' }}">
              </div>

              <div class="col-md-12">
                <label class="form-label">Acceso Autorizado (Áreas o Divisiones)</label>
                <input type="text"
                       name="accesos_autorizados"
                       class="form-control"
                       value="{{ item.accesos_autorizados or '' }}"
                       placeholder="p.ej.: Operaciones; Ventas; División Andina"
                       required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Confidencialidad (1..5)</label>
                <select name="conf_num" class="form-select" required>
                  {% for o in conf_opts %}
                    <option value="{{ o.nivel_num }}" {% if item.c_nivel == o.nivel_num %}selected{% endif %}>
                      {{ o.nivel_num }} — {{ o.clasificacion }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Integridad (1..5)</label>
                <select name="int_num" class="form-select" required>
                  {% for o in inte_opts %}
                    <option value="{{ o.nivel_num }}" {% if item.i_nivel == o.nivel_num %}selected{% endif %}>
                      {{ o.nivel_num }} — {{ o.nivel }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Disponibilidad (1..5)</label>
                <select name="disp_num" class="form-select" required>
                  {% for o in disp_opts %}
                    <option value="{{ o.nivel_num }}" {% if item.d_nivel == o.nivel_num %}selected{% endif %}>
                      {{ o.nivel_num }} — {{ o.nivel }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Info Personal?</label>
                <select name="info_personal" class="form-select">
                  <option value="Sí" {% if item.info_personal == 'Sí' %}selected{% endif %}>Sí</option>
                  <option value="No" {% if item.info_personal == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Regulada?</label>
                <select name="info_regulada" class="form-select">
                  <option value="Sí" {% if item.info_regulada == 'Sí' %}selected{% endif %}>Sí</option>
                  <option value="No" {% if item.info_regulada == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Sens. Compañía?</label>
                <select name="info_sensible_compania" class="form-select">
                  <option value="Sí" {% if item.info_sensible_compania == 'Sí' %}selected{% endif %}>Sí</option>
                  <option value="No" {% if item.info_sensible_compania == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Sens. Clientes?</label>
                <select name="info_sensible_clientes" class="form-select">
                  <option value="Sí" {% if item.info_sensible_clientes == 'Sí' %}selected{% endif %}>Sí</option>
                  <option value="No" {% if item.info_sensible_clientes == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-md-6">
                <label class="form-label">Observaciones</label>
                <input type="text" name="observaciones" class="form-control" value="{{ item.observaciones or '' }}">
              </div>

              <div class="col-md-12">
                <div class="invsoftedit-evidence-upload">
                  <label class="form-label mb-1">Agregar nuevas evidencias PDF</label>
                  <input type="file" name="evidencias" class="form-control" accept="application/pdf,.pdf" multiple>
                  <div class="invsoftedit-evidence-help">
                    Los nuevos PDF se sumarán a las evidencias existentes del activo.
                  </div>
                </div>
              </div>

            </div>

            <div class="invsoftedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold"
                      type="submit"
                      form="formEditarInventarioSoftware">
                Guardar cambios
              </button>

              <a href="{{ url_for('inventario_software') }}"
                 class="btn rounded-pill px-4 fw-bold invsoftedit-cancel-btn">
                Cancelar
              </a>
            </div>

          </form>

          <div class="invsoftedit-evidence-section">
            <div class="invsoftedit-section-title">📎 Evidencias actuales</div>

            {% if evidencias %}
              <div class="invsoftedit-evidence-grid">

                {% for ev in evidencias %}
                  <div class="invsoftedit-evidence-card">

                    <div class="invsoftedit-evidence-icon">📄</div>

                    <div class="invsoftedit-evidence-content">
                      <div class="invsoftedit-evidence-name">
                        {{ ev.original_name or ev.filename }}
                      </div>

                      <div class="invsoftedit-evidence-meta">
                        {{ ev.uploaded_at.strftime('%Y-%m-%d %H:%M') if ev.uploaded_at else '—' }}
                        ·
                        {{ ev.uploaded_by or 'Sistema' }}
                      </div>
                    </div>

                    <div class="invsoftedit-evidence-actions">

                      <a href="/inventario_software/evidencia/{{ ev.id }}/pdf"
                         class="btn btn-sm btn-primary rounded-pill fw-bold">
                        Ver evidencia
                      </a>

                      <form method="post"
                            action="/inventario_software/evidencia/{{ ev.id }}/delete"
                            class="d-inline"
                            onsubmit="return confirm('¿Eliminar esta evidencia?');">
                        <button type="submit"
                                class="btn btn-sm btn-danger rounded-pill fw-bold">
                          Eliminar
                        </button>
                      </form>

                    </div>

                  </div>
                {% endfor %}

              </div>
            {% else %}
              <div class="invsoftedit-no-evidence">
                No hay evidencias PDF cargadas para este activo.
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

      .invsoftedit-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      .invsoftedit-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .invsoftedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .invsoftedit-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent;
        padding:0;
        position:relative;
        z-index:1;
      }

      .invsoftedit-header-overlay::before{
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

      .invsoftedit-header-text{
        max-width:1100px;
        width:100%;
      }

      .invsoftedit-header-text::before{
        content:"SGSI · Edición Inventario de Software";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .invsoftedit-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .invsoftedit-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .invsoftedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .invsoftedit-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invsoftedit-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invsoftedit-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .invsoftedit-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .invsoftedit-card-body{
        padding:18px;
      }

      .invsoftedit-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .invsoftedit-card .form-control,
      .invsoftedit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .invsoftedit-card textarea.form-control{
        min-height:70px;
      }

      .invsoftedit-card .form-control:focus,
      .invsoftedit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 0.15rem rgba(63,134,214,.18);
      }

      .invsoftedit-evidence-upload{
        background:#f8fbff;
        border:1px dashed #9ec5fe;
        border-radius:14px;
        padding:12px;
      }

      .invsoftedit-evidence-help{
        color:#475569;
        font-size:.74rem;
        margin-top:5px;
      }

      .invsoftedit-evidence-section{
        margin-top:18px;
        background:#f8fbff;
        border:1px solid #dbeafe;
        border-radius:16px;
        padding:8px 7px;
      }

      .invsoftedit-section-title{
        color:#0f172a;
        font-size:.92rem;
        font-weight:950;
        margin-bottom:10px;
      }

      .invsoftedit-evidence-grid{
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
        gap:12px;
      }

      .invsoftedit-evidence-card{
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        display:flex;
        align-items:center;
        gap:12px;
        box-shadow:0 8px 16px rgba(15,23,42,.08);
      }

      .invsoftedit-evidence-icon{
        width:46px;
        height:46px;
        min-width:46px;
        border-radius:14px;
        background:linear-gradient(135deg,#e0f2fe,#dbeafe);
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.4rem;
      }

      .invsoftedit-evidence-content{
        flex:1;
        min-width:0;
      }

      .invsoftedit-evidence-name{
        color:#0f172a;
        font-size:.82rem;
        font-weight:950;
        word-break:break-word;
      }

      .invsoftedit-evidence-meta{
        color:#475569;
        font-size:.72rem;
        margin-top:3px;
      }

      .invsoftedit-evidence-actions{
        display:flex;
        gap:6px;
        flex-wrap:wrap;
        justify-content:flex-end;
      }

      .invsoftedit-evidence-actions .btn{
        font-size:.70rem;
        font-weight:900;
        padding:5px 11px;
      }

      .invsoftedit-no-evidence{
        background:#fff;
        border:1px dashed #9ec5fe;
        border-radius:14px;
        padding:8px 7px;
        color:#475569;
        font-size:.82rem;
        font-weight:700;
      }

      .invsoftedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .invsoftedit-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invsoftedit-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invsoftedit-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .invsoftedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .invsoftedit-header-card{
          min-height:88px;
        }

        .invsoftedit-title{
          font-size:1.20rem;
        }

        .invsoftedit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .invsoftedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .invsoftedit-header-overlay::before{
          margin:0;
        }

        .invsoftedit-header-actions .btn,
        .invsoftedit-bottom-actions .btn{
          width:100%;
        }

        .invsoftedit-evidence-card{
          flex-direction:column;
          align-items:flex-start;
        }

        .invsoftedit-evidence-actions{
          width:100%;
          justify-content:flex-start;
        }
      }
    </style>

    <script>
      function cargarDivisionesSoftwareEdit() {
        const areaSel = document.getElementById('softArea');
        const divSel  = document.getElementById('softDivision');
        const divisionActual = "{{ item.division|e }}";

        if (!areaSel || !divSel) return;

        const areaId = areaSel.value;
        divSel.innerHTML = '<option value="">-- Seleccione --</option>';

        if (!areaId) return;

        fetch(`/areas/${areaId}/divisiones_json`)
          .then(r => r.json())
          .then(data => {
            if (!data.divisiones || data.divisiones.length === 0) {
              divSel.innerHTML = '<option value="">(Sin divisiones para esta área)</option>';
              return;
            }

            divSel.innerHTML = '<option value="">-- Seleccione --</option>';

            data.divisiones.forEach(d => {
              const opt = document.createElement('option');
              opt.value = d.nombre;
              opt.textContent = d.nombre;

              if (d.nombre === divisionActual) {
                opt.selected = true;
              }

              divSel.appendChild(opt);
            });
          })
          .catch(err => {
            console.error('Error cargando divisiones (software):', err);
            divSel.innerHTML = '<option value="">Error cargando divisiones</option>';
          });
      }

      document.addEventListener('DOMContentLoaded', () => {
        const areaSel = document.getElementById('softArea');

        if (areaSel) {
          areaSel.addEventListener('change', cargarDivisionesSoftwareEdit);

          if (areaSel.value) {
            cargarDivisionesSoftwareEdit();
          }
        }
      });
    </script>
    """

    inner = render_template_string(
        html,
        item=item,
        areas=areas,
        evidencias=evidencias,
        current_area_id=current_area_id,
        conf_opts=conf_opts,
        inte_opts=inte_opts,
        disp_opts=disp_opts
    )

    return render_template_string(BASE, content=Markup(inner))

# =========================
# MATRIZ — Inventario de Software
# =========================
@app.route('/inventario_software', methods=['GET'])
@login_required
def inventario_software():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Gestión de Activos de Información"):
            flash("No tiene permiso para ver los activos de información.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    items = InventarioSoftware.query.order_by(InventarioSoftware.id.desc()).all()

    matriz_items = []

    for item in items:
        conf_row = ValoracionConfidencialidad.query.filter_by(
            nivel_num=item.c_nivel
        ).first() if item.c_nivel is not None else None

        inte_row = ValoracionIntegridad.query.filter_by(
            nivel_num=item.i_nivel
        ).first() if item.i_nivel is not None else None

        disp_row = ValoracionDisponibilidad.query.filter_by(
            nivel_num=item.d_nivel
        ).first() if item.d_nivel is not None else None

        valor_row = ValoracionCriticidadActivo.query.filter_by(
            nivel_num=item.valor_activo
        ).first() if item.valor_activo is not None else None

        conf_texto = (
            conf_row.clasificacion
            if conf_row and getattr(conf_row, 'clasificacion', None)
            else (item.etiqueta_conf_texto or (f"Nivel {item.c_nivel}" if item.c_nivel is not None else "—"))
        )

        inte_texto = (
            inte_row.nivel
            if inte_row and getattr(inte_row, 'nivel', None)
            else (f"Nivel {item.i_nivel}" if item.i_nivel is not None else "—")
        )

        disp_texto = (
            disp_row.nivel
            if disp_row and getattr(disp_row, 'nivel', None)
            else (f"Nivel {item.d_nivel}" if item.d_nivel is not None else "—")
        )

        valor_texto = (
            valor_row.nivel_texto
            if valor_row and getattr(valor_row, 'nivel_texto', None)
            else (f"Nivel {item.valor_activo}" if item.valor_activo is not None else "—")
        )

        matriz_items.append({
            "item": item,
            "conf_texto": conf_texto,
            "inte_texto": inte_texto,
            "disp_texto": disp_texto,
            "valor_texto": valor_texto,
            "criticidad_texto": item.criticidad_texto or (f"Nivel {item.criticidad_num}" if item.criticidad_num is not None else "—"),
            "etiquetado_texto": item.etiqueta_conf_texto or (f"Nivel {item.etiqueta_conf_num}" if item.etiqueta_conf_num is not None else "—"),
        })

    html = """
    <div class="invsoftmat-shell">

      <div class="invsoftmat-header-card">
        <div class="invsoftmat-header-overlay">
          <div class="invsoftmat-header-text">
            <h3 class="invsoftmat-title m-0">Inventario de Software — Matriz</h3>
            <div class="invsoftmat-subtitle">
              Visualización resumida de activos de software del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="invsoftmat-header-actions">
        {% if not read_only %}
          <a href="{{ url_for('inventario_software_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            ➕ Agregar Activo
          </a>
        {% else %}
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            ➕ Agregar Activo
          </button>
        {% endif %}
      </div>

      <style>
        .badge-n1 { background:#2ecc71; color:#fff; }
        .badge-n2 { background:#f1c40f; color:#111; }
        .badge-n3 { background:#e67e22; color:#fff; }
        .badge-n4 { background:#e74c3c; color:#fff; }
        .badge-n5 { background:#8e44ad; color:#fff; }
      </style>

      <div class="invsoftmat-card">
        <div class="invsoftmat-topbar">
          <div>
            <h5 class="invsoftmat-top-title mb-1">Resumen de activos de software</h5>
            <div class="invsoftmat-top-note">
              La matriz muestra los niveles de valoración en texto. Para consultar toda la información utilice el botón <strong>Ver detalle</strong>.
            </div>
          </div>

          <div class="invsoftmat-counter-badge">
            Total registros: {{ matriz_items|length }}
          </div>
        </div>

        <div class="invsoftmat-card-body">
          <div class="invsoftmat-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-hover align-middle invsoftmat-table mb-0">

                <colgroup>
                  <col style="width: 11%;">
                  <col style="width: 11%;">
                  <col style="width: 11%;">
                  <col style="width: 15%;">
                  <col style="width: 12%;">
                  <col style="width: 12%;">
                  <col style="width: 12%;">
                  <col style="width: 12%;">
                  <col style="width: 12%;">
                  <col style="width: 12%;">
                  <col style="width: 14%;">
                </colgroup>

                <thead>
                  <tr>
                    <th>Área</th>
                    <th>División</th>
                    <th>Proceso</th>
                    <th>Nombre del Activo</th>
                    <th>Confidencialidad</th>
                    <th>Integridad</th>
                    <th>Disponibilidad</th>
                    <th>Valor</th>
                    <th>Criticidad</th>
                    <th>Etiquetado</th>
                    <th class="invsoftmat-col-acciones">Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  {% for row in matriz_items %}
                    {% set item = row.item %}
                    <tr>
                      <td>{{ item.area or '—' }}</td>
                      <td>{{ item.division or '—' }}</td>
                      <td>{{ item.proceso or '—' }}</td>

                      <td class="invsoftmat-cell-main">
                        <div class="invsoftmat-main-text">{{ item.nombre_activo or '—' }}</div>
                      </td>

                      <td class="text-center">
                        <span class="badge badge-n{{ item.c_nivel or 1 }} invsoftmat-badge-text">
                          {{ row.conf_texto }}
                        </span>
                      </td>

                      <td class="text-center">
                        <span class="badge badge-n{{ item.i_nivel or 1 }} invsoftmat-badge-text">
                          {{ row.inte_texto }}
                        </span>
                      </td>

                      <td class="text-center">
                        <span class="badge badge-n{{ item.d_nivel or 1 }} invsoftmat-badge-text">
                          {{ row.disp_texto }}
                        </span>
                      </td>

                      <td class="text-center">
                        <span class="badge badge-n{{ item.valor_activo or 1 }} invsoftmat-badge-text">
                          {{ row.valor_texto }}
                        </span>
                      </td>

                      <td class="text-center">
                        <span class="badge badge-n{{ item.criticidad_num or 1 }} invsoftmat-badge-text">
                          {{ row.criticidad_texto }}
                        </span>
                      </td>

                      <td class="text-center">
                        <span class="badge badge-n{{ item.etiqueta_conf_num or 1 }} invsoftmat-badge-text">
                          {{ row.etiquetado_texto }}
                        </span>
                      </td>

                      <td class="text-center invsoftmat-col-acciones">
                        <div class="invsoftmat-actions-wrap">

                          <a href="{{ url_for('inventario_software_detalle', id=item.id) }}"
                             class="btn btn-info btn-sm rounded-pill invsoftmat-btn-action text-white fw-bold">
                            Ver detalle
                          </a>

                          {% if not read_only %}
                            <a href="{{ url_for('inventario_software_edit', id=item.id) }}"
                               class="btn btn-warning btn-sm rounded-pill invsoftmat-btn-action fw-bold">
                              Editar
                            </a>

                            <a href="{{ url_for('inventario_software_delete', id=item.id) }}"
                               class="btn btn-danger btn-sm rounded-pill invsoftmat-btn-action fw-bold"
                               onclick="return confirm('¿Eliminar este activo de software?');">
                              Eliminar
                            </a>
                          {% else %}
                            <span class="badge bg-secondary">Solo lectura</span>
                          {% endif %}

                        </div>
                      </td>
                    </tr>
                  {% endfor %}

                  {% if matriz_items|length == 0 %}
                    <tr>
                      <td colspan="11" class="text-center text-muted py-5">
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

      .invsoftmat-shell{
        width:96%;
        max-width:1750px;
        margin:10px auto 24px auto;
      }

      .invsoftmat-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .invsoftmat-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .invsoftmat-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent;
        padding:0;
        position:relative;
        z-index:1;
      }

      .invsoftmat-header-overlay::before{
        content:"💻";
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

      .invsoftmat-header-text{
        max-width:1100px;
        width:100%;
      }

      .invsoftmat-header-text::before{
        content:"SGSI · Matriz Inventario de Software";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .invsoftmat-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .invsoftmat-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .invsoftmat-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .invsoftmat-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invsoftmat-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .invsoftmat-topbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:14px 16px 0 16px;
        flex-wrap:wrap;
      }

      .invsoftmat-top-title{
        color:#0f172a;
        font-weight:950;
        font-size:.92rem;
      }

      .invsoftmat-top-note{
        color:#475569;
        font-size:.78rem;
      }

      .invsoftmat-counter-badge{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:7px 14px;
        font-size:.78rem;
        box-shadow:0 8px 16px rgba(15,23,42,.16);
      }

      .invsoftmat-card-body{
        padding:12px 16px 16px 16px;
      }

      .invsoftmat-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#fff;
      }

      .invsoftmat-table{
        min-width:1650px;
        table-layout:fixed;
        margin-bottom:0;
      }

      .invsoftmat-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#fff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
      }

      .invsoftmat-table th,
      .invsoftmat-table td{
        vertical-align:top;
        font-size:.68rem;
        padding:9px 8px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .invsoftmat-table td{
        border-bottom:1px solid #e5edf7;
      }

      .invsoftmat-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .invsoftmat-table tbody tr:hover{
        background:#eef6ff;
      }

      .invsoftmat-cell-main .invsoftmat-main-text{
        font-weight:900;
        color:#0f172a;
      }

      .invsoftmat-badge-text{
        font-size:.68rem !important;
        line-height:1.15;
        padding:5px 8px;
        border-radius:999px;
        font-weight:900;
        white-space:normal;
        max-width:130px;
        display:inline-block;
      }

      .invsoftmat-col-acciones{
        width:160px !important;
        min-width:160px !important;
      }

      .invsoftmat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .invsoftmat-btn-action,
      .invsoftmat-actions-wrap .badge{
        font-size:.64rem !important;
        line-height:1.1;
        padding:4px 10px !important;
        min-width:108px;
        max-width:108px;
        text-align:center;
        white-space:nowrap;
        border-radius:999px !important;
        font-weight:900;
      }

      @media (max-width:992px){
        .invsoftmat-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .invsoftmat-header-card{
          min-height:88px;
        }

        .invsoftmat-title{
          font-size:1.20rem;
        }

        .invsoftmat-card-body{
          padding:12px;
        }

        .invsoftmat-topbar{
          padding:12px 14px 0 14px;
        }
      }

      @media (max-width:768px){
        .invsoftmat-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .invsoftmat-header-overlay::before{
          margin:0;
        }

        .invsoftmat-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        matriz_items=matriz_items,
        read_only=read_only
    )

    return render_template_string(BASE, content=Markup(inner))

# =========================
# DETALLE — Inventario de Software
# =========================
@app.route('/inventario_software/detalle/<int:id>', methods=['GET'])
@login_required
def inventario_software_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role != 'auditor':
        if user.role != 'admin' and not verificar_permiso(user, "Gestión de Activos de Información"):
            flash("No tiene permiso para ver el detalle de activos de software.", "danger")
            return redirect(url_for('inventario_software'))

    item = InventarioSoftware.query.get_or_404(id)

    evidencias = InventarioSoftwareEvidencia.query.filter_by(
        registro_id=item.id
    ).order_by(InventarioSoftwareEvidencia.id.desc()).all()

    conf_row = ValoracionConfidencialidad.query.filter_by(nivel_num=item.c_nivel).first() if item.c_nivel is not None else None
    inte_row = ValoracionIntegridad.query.filter_by(nivel_num=item.i_nivel).first() if item.i_nivel is not None else None
    disp_row = ValoracionDisponibilidad.query.filter_by(nivel_num=item.d_nivel).first() if item.d_nivel is not None else None
    valor_row = ValoracionCriticidadActivo.query.filter_by(nivel_num=item.valor_activo).first() if item.valor_activo is not None else None

    conf_texto = conf_row.clasificacion if conf_row and getattr(conf_row, 'clasificacion', None) else (item.etiqueta_conf_texto or (f"Nivel {item.c_nivel}" if item.c_nivel is not None else "—"))
    inte_texto = inte_row.nivel if inte_row and getattr(inte_row, 'nivel', None) else (f"Nivel {item.i_nivel}" if item.i_nivel is not None else "—")
    disp_texto = disp_row.nivel if disp_row and getattr(disp_row, 'nivel', None) else (f"Nivel {item.d_nivel}" if item.d_nivel is not None else "—")
    valor_texto = valor_row.nivel_texto if valor_row and getattr(valor_row, 'nivel_texto', None) else (f"Nivel {item.valor_activo}" if item.valor_activo is not None else "—")

    criticidad_texto = item.criticidad_texto or (f"Nivel {item.criticidad_num}" if item.criticidad_num is not None else "—")
    etiquetado_texto = item.etiqueta_conf_texto or (
        conf_row.clasificacion if conf_row and getattr(conf_row, 'clasificacion', None)
        else (f"Nivel {item.etiqueta_conf_num}" if item.etiqueta_conf_num is not None else "—")
    )

    def badge_class(n):
        if n == 1:
            return "badge-n1"
        if n == 2:
            return "badge-n2"
        if n == 3:
            return "badge-n3"
        if n == 4:
            return "badge-n4"
        return "badge-n5"

    conf_badge = badge_class(item.c_nivel or 1)
    inte_badge = badge_class(item.i_nivel or 1)
    disp_badge = badge_class(item.d_nivel or 1)
    valor_badge = badge_class(item.valor_activo or 1)
    criticidad_badge = badge_class(item.criticidad_num or 1)
    etiquetado_badge = badge_class(item.etiqueta_conf_num or 1)

    html = """
    <div class="invsoftdet-shell">

      <div class="invsoftdet-header-card">
        <div class="invsoftdet-header-overlay">
          <div class="invsoftdet-header-text">
            <h3 class="invsoftdet-title m-0">Detalle — Inventario de Software</h3>
            <div class="invsoftdet-subtitle">
              Consulta completa del activo de software registrado en el Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="invsoftdet-header-actions">
        <a href="{{ url_for('inventario_software') }}"
           class="btn rounded-pill px-4 fw-bold invsoftdet-back-btn">
          ⬅ Volver a la Matriz
        </a>

        {% if user.role != 'auditor' %}
          <a href="{{ url_for('inventario_software_edit', id=item.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar
          </a>
        {% endif %}
      </div>

      <style>
        .badge-n1 { background:#2ecc71; color:#fff; }
        .badge-n2 { background:#f1c40f; color:#111; }
        .badge-n3 { background:#e67e22; color:#fff; }
        .badge-n4 { background:#e74c3c; color:#fff; }
        .badge-n5 { background:#8e44ad; color:#fff; }
      </style>

      <div class="invsoftdet-card">
        <div class="invsoftdet-card-body">

          <div class="row g-3">

            <div class="col-md-4"><div class="invsoftdet-field"><div class="invsoftdet-label">Área</div><div class="invsoftdet-value">{{ item.area or '—' }}</div></div></div>
            <div class="col-md-4"><div class="invsoftdet-field"><div class="invsoftdet-label">División</div><div class="invsoftdet-value">{{ item.division or '—' }}</div></div></div>
            <div class="col-md-4"><div class="invsoftdet-field"><div class="invsoftdet-label">Proceso</div><div class="invsoftdet-value">{{ item.proceso or '—' }}</div></div></div>

            <div class="col-md-6"><div class="invsoftdet-field"><div class="invsoftdet-label">Nombre del Activo</div><div class="invsoftdet-value">{{ item.nombre_activo or '—' }}</div></div></div>
            <div class="col-md-3"><div class="invsoftdet-field"><div class="invsoftdet-label">Owner/Admin</div><div class="invsoftdet-value">{{ item.administrador or '—' }}</div></div></div>
            <div class="col-md-3"><div class="invsoftdet-field"><div class="invsoftdet-label">Dueño Técnico</div><div class="invsoftdet-value">{{ item.dueno_tecnico or '—' }}</div></div></div>

            <div class="col-md-4"><div class="invsoftdet-field"><div class="invsoftdet-label">Propietario</div><div class="invsoftdet-value">{{ item.propietario or '—' }}</div></div></div>
            <div class="col-md-4"><div class="invsoftdet-field"><div class="invsoftdet-label">Medio</div><div class="invsoftdet-value">{{ item.medio or '—' }}</div></div></div>
            <div class="col-md-4"><div class="invsoftdet-field"><div class="invsoftdet-label">Ubicación</div><div class="invsoftdet-value">{{ item.ubicacion_tipo or '—' }} — {{ item.ubicacion_nombre or '—' }}</div></div></div>

            <div class="col-md-12"><div class="invsoftdet-field"><div class="invsoftdet-label">Descripción</div><div class="invsoftdet-value">{{ item.descripcion or '—' }}</div></div></div>
            <div class="col-md-12"><div class="invsoftdet-field"><div class="invsoftdet-label">Accesos Autorizados</div><div class="invsoftdet-value">{{ item.accesos_autorizados or '—' }}</div></div></div>

            <div class="col-md-2"><div class="invsoftdet-field text-center"><div class="invsoftdet-label">Confidencialidad</div><span class="badge {{ conf_badge }} invsoftdet-badge">{{ conf_texto }}</span></div></div>
            <div class="col-md-2"><div class="invsoftdet-field text-center"><div class="invsoftdet-label">Integridad</div><span class="badge {{ inte_badge }} invsoftdet-badge">{{ inte_texto }}</span></div></div>
            <div class="col-md-2"><div class="invsoftdet-field text-center"><div class="invsoftdet-label">Disponibilidad</div><span class="badge {{ disp_badge }} invsoftdet-badge">{{ disp_texto }}</span></div></div>
            <div class="col-md-2"><div class="invsoftdet-field text-center"><div class="invsoftdet-label">Valor del Activo</div><span class="badge {{ valor_badge }} invsoftdet-badge">{{ valor_texto }}</span></div></div>
            <div class="col-md-2"><div class="invsoftdet-field text-center"><div class="invsoftdet-label">Criticidad</div><span class="badge {{ criticidad_badge }} invsoftdet-badge">{{ criticidad_texto }}</span></div></div>
            <div class="col-md-2"><div class="invsoftdet-field text-center"><div class="invsoftdet-label">Etiquetado</div><span class="badge {{ etiquetado_badge }} invsoftdet-badge">{{ etiquetado_texto }}</span></div></div>

            <div class="col-md-3"><div class="invsoftdet-field"><div class="invsoftdet-label">¿Info Personal?</div><div class="invsoftdet-value">{{ item.info_personal or '—' }}</div></div></div>
            <div class="col-md-3"><div class="invsoftdet-field"><div class="invsoftdet-label">¿Regulada?</div><div class="invsoftdet-value">{{ item.info_regulada or '—' }}</div></div></div>
            <div class="col-md-3"><div class="invsoftdet-field"><div class="invsoftdet-label">¿Sens. Compañía?</div><div class="invsoftdet-value">{{ item.info_sensible_compania or '—' }}</div></div></div>
            <div class="col-md-3"><div class="invsoftdet-field"><div class="invsoftdet-label">¿Sens. Clientes?</div><div class="invsoftdet-value">{{ item.info_sensible_clientes or '—' }}</div></div></div>

            <div class="col-md-12"><div class="invsoftdet-field"><div class="invsoftdet-label">Observaciones</div><div class="invsoftdet-value">{{ item.observaciones or '—' }}</div></div></div>

          </div>

          <div class="invsoftdet-evidence-section">
            <div class="invsoftdet-section-title">📎 Evidencias PDF</div>

            {% if evidencias %}
              <div class="invsoftdet-evidence-grid">

                {% for ev in evidencias %}
                  <div class="invsoftdet-evidence-card">

                    <div class="invsoftdet-evidence-icon">📄</div>

                    <div class="invsoftdet-evidence-content">
                      <div class="invsoftdet-evidence-name">
                        {{ ev.original_name or ev.filename }}
                      </div>

                      <div class="invsoftdet-evidence-meta">
                        {{ ev.uploaded_at.strftime('%Y-%m-%d %H:%M') if ev.uploaded_at else '—' }}
                        ·
                        {{ ev.uploaded_by or 'Sistema' }}
                      </div>
                    </div>

                    <div class="invsoftdet-evidence-actions">

                      <a href="/inventario_software/evidencia/{{ ev.id }}/pdf"
                         class="btn btn-sm btn-primary rounded-pill fw-bold">
                        Ver evidencia
                      </a>

                      {% if user.role != 'auditor' %}
                        <form method="post"
                              action="/inventario_software/evidencia/{{ ev.id }}/delete"
                              class="d-inline"
                              onsubmit="return confirm('¿Eliminar esta evidencia?');">
                          <button type="submit"
                                  class="btn btn-sm btn-danger rounded-pill fw-bold">
                            Eliminar
                          </button>
                        </form>
                      {% endif %}

                    </div>

                  </div>
                {% endfor %}

              </div>
            {% else %}
              <div class="invsoftdet-no-evidence">
                No hay evidencias PDF cargadas para este activo.
              </div>
            {% endif %}
          </div>

          <div class="invsoftdet-bottom-actions">
            <a href="{{ url_for('inventario_software') }}"
               class="btn rounded-pill px-4 fw-bold invsoftdet-cancel-btn">
              Cerrar
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

      .invsoftdet-shell{
        width:96%;
        max-width:1400px;
        margin:10px auto 24px auto;
      }

      .invsoftdet-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .invsoftdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 90% 10%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .invsoftdet-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .invsoftdet-header-overlay::before{
        content:"💻";
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

      .invsoftdet-header-text{
        max-width:1100px;
        width:100%;
      }

      .invsoftdet-header-text::before{
        content:"SGSI · Inventario de Software";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .invsoftdet-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .invsoftdet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .invsoftdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .invsoftdet-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invsoftdet-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invsoftdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .invsoftdet-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .invsoftdet-card-body{
        padding:20px;
      }

      .invsoftdet-field{
        background:linear-gradient(180deg,#f8fafc,#ffffff);
        border:1px solid #e2e8f0;
        border-radius:14px;
        padding:8px 7px;
        height:100%;
        box-shadow:0 4px 10px rgba(0,0,0,.05);
      }

      .invsoftdet-label{
        font-size:.72rem;
        font-weight:900;
        color:#2563eb;
        text-transform:uppercase;
        letter-spacing:.4px;
        margin-bottom:6px;
      }

      .invsoftdet-value{
        color:#0f172a;
        font-size:.90rem;
        white-space:pre-wrap;
        word-break:break-word;
        line-height:1.35;
      }

      .invsoftdet-badge{
        font-size:.72rem;
        padding:6px 10px;
        border-radius:999px;
        display:inline-block;
        font-weight:800;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .invsoftdet-evidence-section{
        margin-top:18px;
        background:#f8fbff;
        border:1px solid #dbeafe;
        border-radius:16px;
        padding:8px 7px;
      }

      .invsoftdet-section-title{
        color:#0f172a;
        font-size:.92rem;
        font-weight:950;
        margin-bottom:10px;
      }

      .invsoftdet-evidence-grid{
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
        gap:12px;
      }

      .invsoftdet-evidence-card{
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        display:flex;
        align-items:center;
        gap:12px;
        box-shadow:0 8px 16px rgba(15,23,42,.08);
      }

      .invsoftdet-evidence-icon{
        width:46px;
        height:46px;
        min-width:46px;
        border-radius:14px;
        background:linear-gradient(135deg,#e0f2fe,#dbeafe);
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.4rem;
      }

      .invsoftdet-evidence-content{
        flex:1;
        min-width:0;
      }

      .invsoftdet-evidence-name{
        color:#0f172a;
        font-size:.82rem;
        font-weight:950;
        word-break:break-word;
      }

      .invsoftdet-evidence-meta{
        color:#475569;
        font-size:.72rem;
        margin-top:3px;
      }

      .invsoftdet-evidence-actions{
        display:flex;
        gap:6px;
        flex-wrap:wrap;
        justify-content:flex-end;
      }

      .invsoftdet-evidence-actions .btn{
        font-size:.70rem;
        font-weight:900;
        padding:5px 11px;
      }

      .invsoftdet-no-evidence{
        background:#fff;
        border:1px dashed #9ec5fe;
        border-radius:14px;
        padding:8px 7px;
        color:#475569;
        font-size:.82rem;
        font-weight:700;
      }

      .invsoftdet-bottom-actions{
        display:flex;
        justify-content:center;
        gap:12px;
        margin-top:24px;
        flex-wrap:wrap;
      }

      .invsoftdet-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
      }

      .invsoftdet-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 12px rgba(0,0,0,.10);
      }

      .invsoftdet-cancel-btn:hover{
        background:#f1f5f9;
      }

      @media (max-width:992px){
        .invsoftdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .invsoftdet-title{
          font-size:1.20rem;
        }

        .invsoftdet-card-body{
          padding:8px 7px;
        }

        .invsoftdet-badge{
          width:100%;
          text-align:center;
        }
      }

      @media (max-width:768px){
        .invsoftdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .invsoftdet-header-overlay::before{
          margin:0;
        }

        .invsoftdet-header-actions .btn{
          width:100%;
        }

        .invsoftdet-evidence-card{
          flex-direction:column;
          align-items:flex-start;
        }

        .invsoftdet-evidence-actions{
          width:100%;
          justify-content:flex-start;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        item=item,
        user=user,
        evidencias=evidencias,
        conf_texto=conf_texto,
        inte_texto=inte_texto,
        disp_texto=disp_texto,
        valor_texto=valor_texto,
        criticidad_texto=criticidad_texto,
        etiquetado_texto=etiquetado_texto,
        conf_badge=conf_badge,
        inte_badge=inte_badge,
        disp_badge=disp_badge,
        valor_badge=valor_badge,
        criticidad_badge=criticidad_badge,
        etiquetado_badge=etiquetado_badge
    )

    return render_template_string(BASE, content=Markup(inner))

# =========================
# VISTA — Evidencia Inventario de Software
# =========================
@app.route('/inventario_software/evidencia/<int:evidencia_id>/pdf')
@login_required
def inventario_software_evidencia_pdf(evidencia_id):

    user = User.query.get(session.get('user_id'))

    if user.role != 'auditor':

        if user.role != 'admin' and not verificar_permiso(
            user,
            "Gestión de Activos de Información"
        ):

            flash(
                "No tiene permiso para ver evidencias de activos de software.",
                "danger"
            )

            return redirect(url_for('inventario_software'))

    ev = InventarioSoftwareEvidencia.query.get_or_404(evidencia_id)

    item = InventarioSoftware.query.get_or_404(
        ev.registro_id
    )

    upload_dir = app.config.get(
        'UPLOAD_INVENTARIO_SOFTWARE_DIR'
    )

    if not upload_dir:
        abort(404)

    file_path = os.path.join(
        upload_dir,
        ev.filename
    )

    if not os.path.exists(file_path):

        flash(
            "No se encontró el archivo de evidencia.",
            "danger"
        )

        return redirect(
            url_for(
                'inventario_software_detalle',
                id=ev.registro_id
            )
        )

    inner_html = """

    <div class="container my-3">

      <!-- =========================
           BOTONES SUPERIORES
      ========================== -->
      <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">

        <a href="{{ url_for('inventario_software_detalle', id=item.id) }}"
           class="btn btn-secondary rounded-pill px-4 py-2 fw-bold">

          ⬅ Volver al Detalle

        </a>

        <div class="small text-muted text-truncate">
          Archivo: {{ ev.original_name or ev.filename }}
        </div>

      </div>

      <!-- =========================
           CARD VISOR PDF
      ========================== -->
      <div class="card shadow-sm evidencia-card">

        <div class="card-header evidencia-header">

          <div>

            <small>
              Activo:
              {{ item.nombre_activo or '—' }}
            </small>

          </div>

        </div>

        <div class="card-body p-2">

          <div class="pdf-container">

            <iframe
              id="pdfFrame"
              src="{{ url_for('inventario_software_evidencia_pdf_raw', evidencia_id=ev.id) }}#zoom=page-width"
              title="Visor PDF">
            </iframe>

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

      .evidencia-card{
        background:rgba(255,255,255,.90)!important;
        backdrop-filter:blur(4px);
        border-radius:14px;
        overflow:hidden;
        border:none;
      }

      .evidencia-header{
        background:linear-gradient(
          135deg,
          #062b55,
          #0b4a8f,
          #1d5fae
        );

        color:#fff !important;
        border:none;
      }

      .pdf-container{
        height:min(82vh,1000px);
        min-height:600px;
        width:100%;
      }

      .pdf-container iframe{
        width:100%;
        height:100%;
        border:1px solid #dee2e6;
        border-radius:8px;
        background:#fff;
      }

      @media (max-width:768px){

        .pdf-container{
          min-height:500px;
        }

      }

    </style>

    """

    return render_template_string(
        BASE,
        content=Markup(
            render_template_string(
                inner_html,
                ev=ev,
                item=item
            )
        )
    )


# =========================
# PDF RAW — Evidencia Inventario de Software
# =========================
@app.route('/inventario_software/evidencia/<int:evidencia_id>/pdf/raw')
@login_required
def inventario_software_evidencia_pdf_raw(evidencia_id):

    user = User.query.get(session.get('user_id'))

    if user.role != 'auditor':

        if user.role != 'admin' and not verificar_permiso(
            user,
            "Gestión de Activos de Información"
        ):

            flash(
                "No tiene permiso para ver evidencias de activos de software.",
                "danger"
            )

            return redirect(url_for('inventario_software'))

    ev = InventarioSoftwareEvidencia.query.get_or_404(
        evidencia_id
    )

    upload_dir = app.config.get(
        'UPLOAD_INVENTARIO_SOFTWARE_DIR'
    )

    if not upload_dir:
        abort(404)

    file_path = os.path.join(
        upload_dir,
        ev.filename
    )

    if not os.path.exists(file_path):

        flash(
            "No se encontró el archivo de evidencia.",
            "danger"
        )

        return redirect(
            url_for(
                'inventario_software_detalle',
                id=ev.registro_id
            )
        )

    return send_from_directory(
        upload_dir,
        ev.filename,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=ev.original_name or ev.filename
    )

@app.route('/inventario_software/evidencia/<int:evidencia_id>/delete', methods=['POST'])
@login_required
def inventario_software_evidencia_delete(evidencia_id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar evidencias.", "danger")
        return redirect(url_for('inventario_software'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Activos de Información"):
        flash("No tiene permiso para eliminar evidencias.", "danger")
        return redirect(url_for('inventario_software'))

    ev = InventarioSoftwareEvidencia.query.get_or_404(evidencia_id)
    registro_id = ev.registro_id

    upload_dir = app.config.get('UPLOAD_INVENTARIO_SOFTWARE_DIR')
    file_path = os.path.join(upload_dir, ev.filename) if upload_dir else None

    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

    db.session.delete(ev)
    db.session.commit()

    flash("Evidencia eliminada correctamente.", "success")
    return redirect(url_for('inventario_software_detalle', id=registro_id))

# =========================
# ELIMINAR — Inventario de Software
# =========================
@app.route('/inventario_software/delete/<int:id>')
@login_required
def inventario_software_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin'
        and not verificar_permiso(user, "Gestión de Activos de Información")
    ):
        flash("No tiene permiso para eliminar activos.", "danger")
        return redirect(url_for('inventario_software_menu'))

    it = InventarioSoftware.query.get_or_404(id)

    upload_dir = app.config.get('UPLOAD_INVENTARIO_SOFTWARE_DIR')
    if upload_dir:
        try:
            for ev in list(it.evidencias or []):
                if ev.filename:
                    file_path = os.path.join(upload_dir, ev.filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
        except Exception as e:
            print("Error eliminando evidencias del activo de software:", repr(e))

    db.session.delete(it)
    db.session.commit()
    flash("Eliminado correctamente.", "success")
    return redirect(url_for('inventario_software'))

# ===================================
# ENTRADA DIRECTA — Inventario Físico
# ===================================

# ============================================================
#                 INTEGRACIÓN GLPI → INVENTARIO FÍSICO GRAC
# ============================================================

# =========================
# MODELO — Configuración GLPI Inventario Físico
# =========================
class GLPIInventarioFisicoConfig(db.Model):
    __tablename__ = "glpi_inventario_fisico_config"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False, default="GLPI Principal")
    base_url = db.Column(db.String(500), nullable=False)  # Ej: http://192.168.0.10:8080/apirest.php
    app_token = db.Column(db.Text, nullable=True)
    user_token = db.Column(db.Text, nullable=True)

    # Valores por defecto para completar campos SGSI que GLPI normalmente no trae
    # IMPORTANTE: sin ForeignKey porque en tu app la tabla real de AreaEmpresa no se llama necesariamente "area_empresa".
    # Se guarda el ID del área y se consulta contra AreaEmpresa manualmente.
    area_id_default = db.Column(db.Integer, nullable=True)
    division_default = db.Column(db.String(250), nullable=True)
    ciudad_default = db.Column(db.String(120), nullable=True)
    pais_default = db.Column(db.String(120), nullable=True, default="Colombia")

    c_nivel_default = db.Column(db.Integer, nullable=False, default=3)
    i_nivel_default = db.Column(db.Integer, nullable=False, default=3)
    d_nivel_default = db.Column(db.Integer, nullable=False, default=3)

    activo = db.Column(db.Boolean, nullable=False, default=True)
    verificar_ssl = db.Column(db.Boolean, nullable=False, default=False)
    timeout = db.Column(db.Integer, nullable=False, default=30)

    ultima_prueba = db.Column(db.DateTime, nullable=True)
    ultimo_sync = db.Column(db.DateTime, nullable=True)
    ultimo_estado = db.Column(db.String(40), nullable=True)
    ultimo_mensaje = db.Column(db.Text, nullable=True)



def ensure_glpi_inventario_fisico_tables():
    """
    Crea solo la tabla independiente de configuración GLPI si no existe.
    No modifica la tabla actual InventarioFisico.
    Evita ejecutar db.create_all() global para no disparar errores de otros modelos.
    """
    try:
        with app.app_context():
            GLPIInventarioFisicoConfig.__table__.create(bind=db.engine, checkfirst=True)
    except Exception as e:
        print("Error creando tabla GLPI Inventario Físico:", repr(e))


try:
    ensure_glpi_inventario_fisico_tables()
except Exception:
    pass


# =========================
# HELPERS — Seguridad token
# =========================
def _glpi_invfis_encrypt(value):
    if not value:
        return ""
    try:
        if "_fernet_from_app" in globals():
            f = _fernet_from_app()
            return f.encrypt(value.encode("utf-8")).decode("utf-8")
    except Exception:
        pass
    return value


def _glpi_invfis_decrypt(value):
    if not value:
        return ""
    try:
        if "_fernet_from_app" in globals():
            f = _fernet_from_app()
            return f.decrypt(value.encode("utf-8")).decode("utf-8")
    except Exception:
        pass
    return value


def _glpi_normalize_base_url(base_url):
    base_url = (base_url or "").strip().rstrip("/")
    if not base_url:
        return ""
    if not base_url.endswith("/apirest.php"):
        base_url = base_url + "/apirest.php"
    return base_url


def _glpi_invfis_config_activa():
    return (
        GLPIInventarioFisicoConfig.query
        .filter_by(activo=True)
        .order_by(GLPIInventarioFisicoConfig.id.desc())
        .first()
    )


def _glpi_invfis_headers(cfg, session_token=None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    app_token = _glpi_invfis_decrypt(cfg.app_token)
    if app_token:
        headers["App-Token"] = app_token

    if session_token:
        headers["Session-Token"] = session_token

    return headers


def _glpi_invfis_init_session(cfg):
    """
    Inicia sesión en GLPI usando user_token + app_token.
    """
    base_url = _glpi_normalize_base_url(cfg.base_url)
    user_token = _glpi_invfis_decrypt(cfg.user_token)

    if not base_url or not user_token:
        raise Exception("Debe configurar la URL base de GLPI y el User Token.")

    headers = _glpi_invfis_headers(cfg)
    headers["Authorization"] = "user_token " + user_token

    url = base_url + "/initSession"
    res = requests.get(
        url,
        headers=headers,
        timeout=cfg.timeout or 30,
        verify=bool(cfg.verificar_ssl),
    )

    if res.status_code not in (200, 201):
        raise Exception(f"GLPI initSession falló: HTTP {res.status_code} - {res.text[:500]}")

    data = res.json()
    token = data.get("session_token")
    if not token:
        raise Exception("GLPI no devolvió session_token.")

    return token


def _glpi_invfis_kill_session(cfg, session_token):
    try:
        base_url = _glpi_normalize_base_url(cfg.base_url)
        if not base_url or not session_token:
            return

        requests.get(
            base_url + "/killSession",
            headers=_glpi_invfis_headers(cfg, session_token),
            timeout=10,
            verify=bool(cfg.verificar_ssl),
        )
    except Exception:
        pass


def _glpi_get_value(obj, *keys, default=""):
    """
    Lee campos de GLPI soportando nombres comunes y valores nulos.
    """
    for k in keys:
        if isinstance(obj, dict) and k in obj and obj.get(k) not in (None, ""):
            return str(obj.get(k)).strip()
    return default


def _glpi_pick_dropdown_name(obj, key):
    """
    GLPI con expand_dropdowns puede devolver texto o dict.
    """
    val = obj.get(key) if isinstance(obj, dict) else None
    if isinstance(val, dict):
        return str(val.get("name") or val.get("completename") or "").strip()
    if val not in (None, ""):
        return str(val).strip()
    return ""


def _glpi_invfis_fetch_computers(cfg, session_token, range_start=0, range_end=999):
    """
    Consulta computadores de GLPI.
    """
    base_url = _glpi_normalize_base_url(cfg.base_url)

    params = {
        "expand_dropdowns": "true",
        "range": f"{range_start}-{range_end}",
    }

    res = requests.get(
        base_url + "/Computer",
        headers=_glpi_invfis_headers(cfg, session_token),
        params=params,
        timeout=cfg.timeout or 30,
        verify=bool(cfg.verificar_ssl),
    )

    if res.status_code not in (200, 206):
        raise Exception(f"Consulta de computadores GLPI falló: HTTP {res.status_code} - {res.text[:500]}")

    data = res.json()
    if isinstance(data, dict) and "data" in data:
        return data.get("data") or []
    if isinstance(data, list):
        return data
    return []


def _glpi_invfis_fetch_computer_detail(cfg, session_token, computer_id):
    """
    Consulta el detalle de un computador GLPI para traer campos que muchas veces
    no vienen completos en la consulta masiva /Computer.
    """
    computer_id = _glpi_clean_text(computer_id)
    if not computer_id:
        return {}

    base_url = _glpi_normalize_base_url(cfg.base_url)
    params = {
        "expand_dropdowns": "true",
        "with_devices": "true",
        "get_hateoas": "false",
    }

    res = requests.get(
        base_url + f"/Computer/{computer_id}",
        headers=_glpi_invfis_headers(cfg, session_token),
        params=params,
        timeout=cfg.timeout or 30,
        verify=bool(cfg.verificar_ssl),
    )

    if res.status_code not in (200, 206):
        return {}

    data = res.json()
    return data if isinstance(data, dict) else {}


_GLPI_INVFIS_ITEM_CACHE = {}


def _glpi_invfis_api_get(cfg, session_token, path, params=None):
    """
    GET genérico contra API REST GLPI.
    Devuelve dict/list o {} si no responde correctamente.
    """
    try:
        base_url = _glpi_normalize_base_url(cfg.base_url)
        res = requests.get(
            base_url + path,
            headers=_glpi_invfis_headers(cfg, session_token),
            params=params or {"expand_dropdowns": "true", "get_hateoas": "false"},
            timeout=cfg.timeout or 30,
            verify=bool(cfg.verificar_ssl),
        )
        if res.status_code not in (200, 206):
            return {}
        data = res.json()
        return data
    except Exception:
        return {}


def _glpi_invfis_first_dict(data):
    """
    Devuelve el primer diccionario útil desde una respuesta GLPI que puede venir
    como dict, list o {"data": [...]}.
    """
    if isinstance(data, dict):
        if isinstance(data.get("data"), list) and data.get("data"):
            for row in data.get("data"):
                if isinstance(row, dict):
                    return row
        return data

    if isinstance(data, list):
        for row in data:
            if isinstance(row, dict):
                return row

    return {}


def _glpi_invfis_fetch_operating_system_relation(cfg, session_token, computer_id):
    """
    GLPI 10 suele guardar la pestaña 'Operating systems' como relación
    Item_OperatingSystem, no siempre dentro del objeto Computer.

    Esta función consulta varias rutas compatibles y devuelve el primer registro
    de sistema operativo asociado al computador.

    Campos esperados en Item_OperatingSystem:
      - operatingsystems_id
      - operatingsystemversions_id
      - operatingsystemarchitectures_id
      - operatingsystemkernels_id
      - operatingsystemkernelversions_id
      - operatingsystemeditions_id
      - operatingsystemservicepacks_id
    """
    computer_id = _glpi_clean_text(computer_id)
    if not computer_id:
        return {}

    candidates = [
        f"/Computer/{computer_id}/Item_OperatingSystem",
        f"/Computer/{computer_id}/OperatingSystem",
        f"/Computer/{computer_id}/OperatingSystemVersion",
    ]

    for path in candidates:
        data = _glpi_invfis_api_get(
            cfg,
            session_token,
            path,
            params={"expand_dropdowns": "true", "get_hateoas": "false"}
        )
        row = _glpi_invfis_first_dict(data)
        if row:
            return row

    # Último intento: búsqueda directa sobre Item_OperatingSystem.
    # Algunas instalaciones no habilitan el endpoint padre/hijo, pero sí el itemtype directo.
    try:
        data = _glpi_invfis_api_get(
            cfg,
            session_token,
            "/Item_OperatingSystem",
            params={
                "expand_dropdowns": "true",
                "get_hateoas": "false",
                "criteria[0][field]": "items_id",
                "criteria[0][searchtype]": "equals",
                "criteria[0][value]": computer_id,
                "criteria[1][link]": "AND",
                "criteria[1][field]": "itemtype",
                "criteria[1][searchtype]": "equals",
                "criteria[1][value]": "Computer",
            }
        )
        row = _glpi_invfis_first_dict(data)
        if row:
            return row
    except Exception:
        pass

    return {}


def _glpi_invfis_merge_os_relation_into_computer(computer, os_relation):
    """
    Mezcla el registro Item_OperatingSystem en el dict Computer sin perder campos
    del equipo. Además crea llaves alias para que el mapeo GRAC lea exactamente:
      procesador      <- arquitectura
      tipo_sistema    <- nombre del SO
      version_so      <- kernel
      edicion_so      <- edición
    """
    merged = dict(computer or {})

    if not isinstance(os_relation, dict) or not os_relation:
        return merged

    for k, v in os_relation.items():
        if v not in (None, "", "None", "null"):
            merged[k] = v

    return merged


def _glpi_invfis_extract_id(value):
    """
    Extrae el ID real de un campo GLPI, aun cuando venga expandido como dict.
    """
    if value in (None, "", "None", "null"):
        return ""

    if isinstance(value, dict):
        for k in ("id", "items_id", "value"):
            if value.get(k) not in (None, "", "None", "null"):
                return str(value.get(k)).strip()
        return ""

    # Si ya viene como número/string numérico
    value = str(value).strip()
    return value if value.isdigit() else ""


def _glpi_invfis_extract_name(value):
    """
    Extrae nombre/completename si el campo GLPI ya vino expandido.
    """
    if value in (None, "", "None", "null"):
        return ""

    if isinstance(value, dict):
        for k in ("name", "completename", "value"):
            if value.get(k) not in (None, "", "None", "null"):
                txt = str(value.get(k)).strip()
                # Evita devolver un ID numérico como nombre
                if txt and not txt.isdigit():
                    return txt
        return ""

    txt = str(value).strip()
    return "" if txt.isdigit() else txt


def _glpi_invfis_resolve_item_name(cfg, session_token, itemtype, item_id):
    """
    Resuelve un ID de dropdown GLPI consultando su endpoint.
    Ejemplos:
      /OperatingSystem/1
      /OperatingSystemArchitecture/1
      /OperatingSystemKernel/1
      /OperatingSystemKernelVersion/1
      /OperatingSystemEdition/1
    """
    item_id = _glpi_clean_text(item_id)
    if not itemtype or not item_id:
        return ""

    cache_key = (itemtype, item_id)
    if cache_key in _GLPI_INVFIS_ITEM_CACHE:
        return _GLPI_INVFIS_ITEM_CACHE[cache_key]

    data = _glpi_invfis_api_get(cfg, session_token, f"/{itemtype}/{item_id}")
    if isinstance(data, dict):
        for k in ("name", "completename", "value"):
            val = _glpi_clean_text(data.get(k))
            if val:
                _GLPI_INVFIS_ITEM_CACHE[cache_key] = val
                return val

    _GLPI_INVFIS_ITEM_CACHE[cache_key] = ""
    return ""


def _glpi_invfis_resolve_dropdown(cfg, session_token, computer, field_name, itemtypes):
    """
    Resuelve un campo dropdown de GLPI:
      1) Si ya vino expandido con name/completename, usa ese texto.
      2) Si vino como ID, consulta el endpoint del itemtype correspondiente.
      3) Si no existe, devuelve vacío.
    """
    if not isinstance(computer, dict):
        return ""

    raw = computer.get(field_name)
    expanded_name = _glpi_invfis_extract_name(raw)
    if expanded_name:
        return expanded_name

    item_id = _glpi_invfis_extract_id(raw)
    if not item_id:
        item_id = _glpi_any_value(computer, field_name)

    item_id = _glpi_clean_text(item_id)
    if not item_id or not item_id.isdigit():
        return ""

    for itemtype in itemtypes:
        name = _glpi_invfis_resolve_item_name(cfg, session_token, itemtype, item_id)
        if name:
            return name

    return ""


def _glpi_invfis_resolve_operating_system_data(cfg, session_token, computer):
    """
    Relaciones definitivas solicitadas GLPI → GRAC:

      - Procesador en GRAC      = Arquitecturas en GLPI
      - Tipo de sistema en GRAC = Nombre en Operating system GLPI
      - Versión SO en GRAC      = Kernel en Operating system GLPI
      - Edición del SO en GRAC  = Edición en Operating system GLPI

    Se consulta primero el campo expandido. Si GLPI solo entrega IDs,
    se resuelven contra los endpoints nativos de GLPI.
    """

    # Tipo de sistema GRAC = Nombre en Operating system GLPI
    tipo_sistema = (
        _glpi_invfis_resolve_dropdown(
            cfg,
            session_token,
            computer,
            "operatingsystems_id",
            ("OperatingSystem",)
        )
        or _glpi_any_value(
            computer,
            "operating_system",
            "operatingsystem",
            "operating_system_name",
            "os_name",
            "os",
            "sistema_operativo",
            "tipo_sistema",
            "name_operatingsystem"
        )
    )

    # Edición del SO GRAC = Edición en Operating system GLPI
    edicion_so = (
        _glpi_invfis_resolve_dropdown(
            cfg,
            session_token,
            computer,
            "operatingsystemeditions_id",
            ("OperatingSystemEdition", "OperatingSystemServicePack")
        )
        or _glpi_any_value(
            computer,
            "operating_system_edition",
            "operatingsystemedition",
            "os_edition",
            "edition",
            "edicion",
            "edicion_so"
        )
    )

    # Versión SO GRAC = Kernel en Operating system GLPI
    # En GLPI puede existir como kernel o kernel version, según versión/agente.
    version_so_kernel = (
        _glpi_invfis_resolve_dropdown(
            cfg,
            session_token,
            computer,
            "operatingsystemkernels_id",
            ("OperatingSystemKernel",)
        )
        or _glpi_invfis_resolve_dropdown(
            cfg,
            session_token,
            computer,
            "operatingsystemkernelversions_id",
            ("OperatingSystemKernelVersion", "OperatingSystemKernel")
        )
        or _glpi_any_value(
            computer,
            "operating_system_kernel",
            "operatingsystemkernel",
            "operating_system_kernel_version",
            "kernel",
            "kernel_version",
            "os_kernel",
            "version_kernel",
            "version_so"
        )
    )

    # Procesador GRAC = Arquitecturas en GLPI
    arquitectura = (
        _glpi_invfis_resolve_dropdown(
            cfg,
            session_token,
            computer,
            "operatingsystemarchitectures_id",
            ("OperatingSystemArchitecture", "Architecture")
        )
        or _glpi_invfis_resolve_dropdown(
            cfg,
            session_token,
            computer,
            "architectures_id",
            ("Architecture", "OperatingSystemArchitecture")
        )
        or _glpi_any_value(
            computer,
            "operating_system_architecture",
            "operatingsystemarchitecture",
            "architecture",
            "architectures",
            "arquitectura",
            "arquitecturas",
            "os_architecture"
        )
    )

    return tipo_sistema, edicion_so, version_so_kernel, arquitectura



def _glpi_clean_text(value):
    """
    Normaliza valores traídos desde GLPI.
    Si GLPI no trae valor, devuelve cadena vacía.
    """
    if value in (None, "", "None", "null"):
        return ""
    return str(value).strip()


def _glpi_any_value(obj, *keys):
    """
    Busca el primer valor real en el diccionario GLPI.
    No inventa valores por defecto.
    """
    if not isinstance(obj, dict):
        return ""

    for key in keys:
        val = obj.get(key)
        if isinstance(val, dict):
            val = val.get("name") or val.get("completename") or val.get("value")
        elif isinstance(val, list):
            val = ", ".join([_glpi_clean_text(x.get("name") if isinstance(x, dict) else x) for x in val if x])
        val = _glpi_clean_text(val)
        if val:
            return val

    return ""


def _glpi_invfis_os_data(cfg, session_token, computer):
    """
    Wrapper compatible para las relaciones GLPI → GRAC.
    Usa resolución robusta por endpoint cuando GLPI trae IDs.
    """
    return _glpi_invfis_resolve_operating_system_data(cfg, session_token, computer)



def _glpi_invfis_hw_data(computer):
    """
    RAM se toma solo si viene desde GLPI.

    Procesador NO se toma de CPU física porque el requerimiento indica:
      procesador en GRAC = Arquitecturas en GLPI.
    Ese valor se asigna desde _glpi_invfis_os_data().
    """
    ram = _glpi_any_value(
        computer,
        "memory",
        "ram",
        "ram_instalada",
        "memories",
        "computermemories"
    )

    return ram



def _glpi_invfis_fetch_group_relation(cfg, session_token, computer_id):
    """
    Busca el Grupo a cargo del computador en GLPI.

    En GLPI, el campo visual 'Grupo a cargo' puede venir:
      - directamente en Computer como groups_id_tech / groups_id
      - o como relación Group_Item asociada al Computer.

    Devuelve el primer registro útil.
    """
    computer_id = _glpi_clean_text(computer_id)
    if not computer_id:
        return {}

    candidates = [
        f"/Computer/{computer_id}/Group_Item",
        f"/Computer/{computer_id}/Group",
    ]

    for path in candidates:
        data = _glpi_invfis_api_get(
            cfg,
            session_token,
            path,
            params={"expand_dropdowns": "true", "get_hateoas": "false"}
        )
        row = _glpi_invfis_first_dict(data)
        if row:
            return row

    # Intento directo sobre Group_Item.
    try:
        data = _glpi_invfis_api_get(
            cfg,
            session_token,
            "/Group_Item",
            params={
                "expand_dropdowns": "true",
                "get_hateoas": "false",
                "criteria[0][field]": "items_id",
                "criteria[0][searchtype]": "equals",
                "criteria[0][value]": computer_id,
                "criteria[1][link]": "AND",
                "criteria[1][field]": "itemtype",
                "criteria[1][searchtype]": "equals",
                "criteria[1][value]": "Computer",
            }
        )
        row = _glpi_invfis_first_dict(data)
        if row:
            return row
    except Exception:
        pass

    return {}


def _glpi_invfis_merge_group_relation_into_computer(computer, group_relation):
    """
    Mezcla la relación Group_Item al dict Computer y crea aliases.
    """
    merged = dict(computer or {})

    if not isinstance(group_relation, dict) or not group_relation:
        return merged

    for k, v in group_relation.items():
        if v not in (None, "", "None", "null"):
            merged[k] = v

    # Normaliza aliases comunes hacia groups_id_tech.
    for key in ("groups_id", "groups_id_tech", "group_id", "group", "name", "completename"):
        val = group_relation.get(key)
        if val not in (None, "", "None", "null") and not merged.get("groups_id_tech"):
            merged["groups_id_tech"] = val
            break

    return merged



def _glpi_invfis_resolver_nombre_grupo_glpi(cfg=None, session_token=None, computer=None):
    raw_group = ""

    if isinstance(computer, dict):
        raw_group = (
            computer.get("groups_id_tech")
            or computer.get("groups_id")
            or computer.get("group_id")
            or ""
        )

    group_id = str(raw_group).strip()

    mapa_grupos = {
        "1": "Seguridad",
        "3": "Ventas",
    }

    return mapa_grupos.get(group_id, ""), group_id


def _glpi_invfis_crear_area_segura(nombre_area):
    nombre_area = _glpi_clean_text(nombre_area)
    if not nombre_area:
        return None

    try:
        with db.session.no_autoflush:
            area = AreaEmpresa.query.filter(AreaEmpresa.area.ilike(nombre_area)).first()
            if area:
                return area.id
    except Exception:
        db.session.rollback()

    try:
        from sqlalchemy import text

        tabla = AreaEmpresa.__table__.name

        columnas_db = db.session.execute(
            text(f"PRAGMA table_info({tabla})")
        ).fetchall()

        valores = {}

        for col in columnas_db:
            col_name = col[1]
            not_null = col[3]
            pk = col[5]

            if pk:
                continue

            if col_name == "area":
                valores[col_name] = nombre_area
            elif not_null:
                if "responsable" in col_name.lower():
                    valores[col_name] = "Importado desde GLPI"
                elif "cargo" in col_name.lower():
                    valores[col_name] = "Automático GLPI"
                else:
                    valores[col_name] = ""
            else:
                valores[col_name] = None

        columnas = ", ".join(valores.keys())
        placeholders = ", ".join([f":{k}" for k in valores.keys()])

        db.session.execute(
            text(f"INSERT INTO {tabla} ({columnas}) VALUES ({placeholders})"),
            valores
        )
        db.session.flush()

        area = AreaEmpresa.query.filter(AreaEmpresa.area.ilike(nombre_area)).first()
        return area.id if area else None

    except Exception as e:
        print("ERROR REAL CREANDO AREA GLPI:", repr(e))
        db.session.rollback()
        return None


def _glpi_invfis_resolver_area_obligatoria(cfg=None, session_token=None, computer=None):
    grupo_texto, group_id = _glpi_invfis_resolver_nombre_grupo_glpi(
        cfg,
        session_token,
        computer
    )

    if not grupo_texto:
        return None

    return _glpi_invfis_crear_area_segura(grupo_texto)


def _glpi_invfis_numero_neutro(value=None):
    """
    Devuelve 0 cuando GLPI no trae clasificación.
    Se usa para cumplir columnas numéricas NOT NULL sin inventar niveles 1-5.
    """
    try:
        if value in (None, "", "None", "null"):
            return 0
        return int(value)
    except Exception:
        return 0


def _glpi_invfis_map_computer_to_data(cfg, computer, session_token=None):
    """
    Mapeo GLPI Computer → InventarioFisico.

    Reglas aplicadas:
    - No se inventan datos funcionales cuando GLPI no los trae.
    - Asignado a = campo name de GLPI.
    - Todo campo SO se interpreta como Sistema Operativo.
    - Sistema Operativo de GLPI se guarda en GRAC como tipo_sistema.
    - area_id se resuelve técnicamente porque la tabla inventario_fisico lo exige NOT NULL.
    """

    glpi_id = _glpi_any_value(computer, "id")
    nombre_glpi = _glpi_any_value(computer, "name", "nombre")
    serial = _glpi_any_value(computer, "serial", "serial_number", "otherserial")
    uuid = _glpi_any_value(computer, "uuid", "id_producto")

    marca = (
        _glpi_pick_dropdown_name(computer, "manufacturers_id")
        or _glpi_any_value(computer, "manufacturer", "marca")
    )

    modelo = (
        _glpi_pick_dropdown_name(computer, "computermodels_id")
        or _glpi_any_value(computer, "model", "modelo")
    )

    tipo_equipo = (
        _glpi_pick_dropdown_name(computer, "computertypes_id")
        or _glpi_any_value(computer, "type", "tipo", "clase_activo")
    )

    ubicacion = (
        _glpi_pick_dropdown_name(computer, "locations_id")
        or _glpi_any_value(computer, "location", "ubicacion", "ciudad")
    )

    sistema_operativo, edicion_so, version_so, arquitectura_glpi = _glpi_invfis_os_data(cfg, session_token, computer)
    ram = _glpi_invfis_hw_data(computer)

    comentario = _glpi_any_value(computer, "comment", "comments")

    # Clase del activo solo con datos que vienen de GLPI.
    clase_activo = ""
    if tipo_equipo and modelo:
        clase_activo = f"{tipo_equipo} / {modelo}"
    elif tipo_equipo:
        clase_activo = tipo_equipo
    elif modelo:
        clase_activo = modelo

    # IMPORTANTE:
    # area_id es obligatorio por estructura de la tabla inventario_fisico.
    # Si GLPI no trae un área que coincida con AreaEmpresa, se toma la primera área existente
    # únicamente para permitir el guardado. No se completan otros valores por defecto.
    area_id_obligatoria = _glpi_invfis_resolver_area_obligatoria(
        cfg,
        session_token,
        computer
    )

    data = {
        "area_id": area_id_obligatoria,
        "division": _glpi_any_value(computer, "division", "business_unit", "departamento"),

        # Regla solicitada: Asignado a = campo name de GLPI
        "asignado_a": nombre_glpi,

        "cargo": _glpi_any_value(computer, "cargo", "position", "title"),
        "ciudad": ubicacion,
        "clase_activo": clase_activo,
        "marca": marca,

        # Solo si GLPI lo trae.
        "mouse": _glpi_any_value(computer, "mouse"),
        "teclado": _glpi_any_value(computer, "keyboard", "teclado"),
        "base_portatil": _glpi_any_value(computer, "base_portatil", "dock", "docking_station"),
        "monitor": _glpi_any_value(computer, "monitor", "monitors"),

        "numero_serial": serial,
        "nombre_dispositivo": nombre_glpi,
        # Relación solicitada: Procesador GRAC = Arquitecturas en GLPI
        "procesador": arquitectura_glpi,
        "ram_instalada": ram,

        # Identificadores GLPI
        "id_dispositivo": glpi_id,
        "id_producto": uuid,

        # SO = Sistema Operativo
        "tipo_sistema": sistema_operativo,
        "edicion_so": edicion_so,
        "version_so": version_so,

        "pais": _glpi_any_value(computer, "country", "pais"),
        "fecha_compra": None,
        "fecha_asignacion": None,

        # Clasificación SGSI: GLPI no la trae.
        # Se guarda 0 para cumplir columnas numéricas NOT NULL si existen, sin mostrar niveles inventados.
        "c_nivel": _glpi_invfis_numero_neutro(_glpi_any_value(computer, "c_nivel", "confidencialidad")),
        "i_nivel": _glpi_invfis_numero_neutro(_glpi_any_value(computer, "i_nivel", "integridad")),
        "d_nivel": _glpi_invfis_numero_neutro(_glpi_any_value(computer, "d_nivel", "disponibilidad")),
        "valor_activo": _glpi_invfis_numero_neutro(_glpi_any_value(computer, "valor_activo")),
        "criticidad_num": _glpi_invfis_numero_neutro(_glpi_any_value(computer, "criticidad_num")),
        "criticidad_texto": _glpi_any_value(computer, "criticidad_texto"),
        "etiqueta_conf_num": _glpi_invfis_numero_neutro(_glpi_any_value(computer, "etiqueta_conf_num")),
        "etiqueta_conf_texto": _glpi_any_value(computer, "etiqueta_conf_texto"),

        # Información regulatoria: solo se diligencia si GLPI lo trae.
        "info_personal": _glpi_any_value(computer, "info_personal"),
        "info_regulada": _glpi_any_value(computer, "info_regulada"),
        "info_sensible": _glpi_any_value(computer, "info_sensible"),
        "info_sensible_clientes": _glpi_any_value(computer, "info_sensible_clientes"),

        "observaciones": comentario,
    }

    return data


def _glpi_invfis_find_existing(data):
    """
    Evita duplicados.
    Prioridad:
    1) número serial
    2) id_dispositivo GLPI
    3) nombre de dispositivo

    Usa no_autoflush para que una búsqueda no dispare flush prematuro.
    """
    serial = (data.get("numero_serial") or "").strip()
    glpi_id = (data.get("id_dispositivo") or "").strip()
    nombre = (data.get("nombre_dispositivo") or "").strip()

    with db.session.no_autoflush:
        if serial:
            item = InventarioFisico.query.filter_by(numero_serial=serial).first()
            if item:
                return item

        if glpi_id:
            item = InventarioFisico.query.filter_by(id_dispositivo=glpi_id).first()
            if item:
                return item

        if nombre:
            item = InventarioFisico.query.filter_by(nombre_dispositivo=nombre).first()
            if item:
                return item

    return None


def _glpi_invfis_upsert(data):
    """
    Crea o actualiza un activo físico desde datos GLPI.
    Ejecuta flush controlado para detectar errores por registro y no dejar
    la sesión en estado inválido para el siguiente equipo.
    """
    item = _glpi_invfis_find_existing(data)
    created = False

    if not item:
        item = InventarioFisico()
        db.session.add(item)
        created = True

    for k, v in data.items():
        if hasattr(item, k):
            setattr(item, k, v)

    db.session.flush()
    return item, created


def glpi_invfis_sincronizar():
    """
    Ejecuta sincronización GLPI → InventarioFisico.
    No importa registros sin identificador mínimo de GLPI.
    Hace commit por registro para evitar que un error dañe toda la transacción.
    """
    cfg = _glpi_invfis_config_activa()
    if not cfg:
        raise Exception("No existe una configuración GLPI activa.")

    session_token = None
    creados = 0
    actualizados = 0
    omitidos = 0
    errores = []

    try:
        session_token = _glpi_invfis_init_session(cfg)
        computers = _glpi_invfis_fetch_computers(cfg, session_token)

        for comp in computers:
            try:
                comp_detalle = comp

                # Consulta detalle por equipo y, muy importante, la relación
                # Item_OperatingSystem que alimenta la pestaña "Operating systems" de GLPI.
                # Sin esta relación, muchos GLPI devuelven en blanco:
                # Arquitecturas, Nombre del SO, Kernel y Edición.
                glpi_comp_id = _glpi_any_value(comp, "id")
                if glpi_comp_id:
                    detalle = _glpi_invfis_fetch_computer_detail(cfg, session_token, glpi_comp_id)
                    if detalle:
                        comp_detalle = {**comp, **detalle}

                    os_relation = _glpi_invfis_fetch_operating_system_relation(cfg, session_token, glpi_comp_id)
                    if os_relation:
                        comp_detalle = _glpi_invfis_merge_os_relation_into_computer(comp_detalle, os_relation)

                    group_relation = _glpi_invfis_fetch_group_relation(cfg, session_token, glpi_comp_id)
                    if group_relation:
                        comp_detalle = _glpi_invfis_merge_group_relation_into_computer(comp_detalle, group_relation)

                data = _glpi_invfis_map_computer_to_data(cfg, comp_detalle, session_token)

                # FORZAR ÁREA DESDE GRUPO GLPI ANTES DE OMITIR
                if not data.get("area_id"):
                    grupo_glpi = (
                        _glpi_any_value(comp_detalle, "groups_id_tech", "groups_id", "group_id")
                        or ""
                    ).strip()

                    mapa_grupos = {
                        "1": "Seguridad",
                        "3": "Ventas",
                    }

                    nombre_area = mapa_grupos.get(grupo_glpi)

                    if nombre_area:
                        area = AreaEmpresa.query.filter(AreaEmpresa.area.ilike(nombre_area)).first()

                        if not area:
                            area = AreaEmpresa(
                                area=nombre_area,
                                responsable_nombre="GLPI",
                                responsable_cargo="GLPI"
                            )
                            db.session.add(area)
                            db.session.flush()

                        data["area_id"] = area.id

                if not data.get("area_id"):
                    grupo_debug = (
                        _glpi_any_value(comp_detalle, "groups_id_tech", "groups_id", "group_id", "name", "completename")
                        or _glpi_any_value(comp_detalle, "grupo_a_cargo", "technical_group", "group_tech")
                        or "NO DETECTADO"
                    )

                    omitidos += 1
                    errores.append(
                        f"Equipo GLPI {comp.get('id', 'N/D')} omitido: FALLÓ crear Área desde Grupo GLPI. "
                        f"Valor detectado GLPI: {grupo_debug}"
                    )
                    db.session.rollback()
                    continue

                _, created = _glpi_invfis_upsert(data)
                db.session.commit()

                if created:
                    creados += 1
                else:
                    actualizados += 1

            except Exception as e:
                db.session.rollback()
                omitidos += 1
                errores.append(f"Equipo GLPI {comp.get('id', 'N/D')}: {str(e)}")

        try:
            cfg = _glpi_invfis_config_activa()
            cfg.ultimo_sync = datetime.utcnow()
            cfg.ultimo_estado = "OK" if not errores else "OK_CON_OMITIDOS"
            cfg.ultimo_mensaje = f"Creados: {creados}, Actualizados: {actualizados}, Omitidos: {omitidos}"
            if errores:
                cfg.ultimo_mensaje += " | " + " || ".join(errores[:5])
            db.session.add(cfg)
            db.session.commit()
        except Exception:
            db.session.rollback()

        return {
            "creados": creados,
            "actualizados": actualizados,
            "omitidos": omitidos,
            "errores": errores[:20],
        }

    except Exception as e:
        db.session.rollback()
        try:
            cfg = _glpi_invfis_config_activa()
            if cfg:
                cfg.ultimo_sync = datetime.utcnow()
                cfg.ultimo_estado = "ERROR"
                cfg.ultimo_mensaje = str(e)
                db.session.add(cfg)
                db.session.commit()
        except Exception:
            db.session.rollback()
        raise

    finally:
        if session_token:
            _glpi_invfis_kill_session(cfg, session_token)

# =========================
# RUTA — Configurar conexión GLPI
# =========================
@app.route('/inventario_fisico/glpi/config', methods=['GET', 'POST'])
@login_required
def inventario_fisico_glpi_config():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin'
        and not verificar_permiso(user, "Gestión de Activos de Información")
    ):
        flash("No tiene permiso para configurar GLPI.", "danger")
        return redirect(url_for('inventario_fisico'))

    cfg = _glpi_invfis_config_activa()
    if not cfg:
        cfg = GLPIInventarioFisicoConfig(
            nombre="GLPI Principal",
            base_url="",
            activo=True,
            verificar_ssl=False,
            timeout=30,

            # Estos campos se conservan por compatibilidad con la tabla,
            # pero la sincronización ya no los usa para inventar datos.
            area_id_default=None,
            division_default="",
            ciudad_default="",
            pais_default="",
            c_nivel_default=0,
            i_nivel_default=0,
            d_nivel_default=0,
        )
        db.session.add(cfg)
        db.session.commit()

    if request.method == 'POST':
        accion = request.form.get("accion") or "guardar"

        cfg.nombre = (request.form.get("nombre") or "GLPI Principal").strip()
        cfg.base_url = _glpi_normalize_base_url(request.form.get("base_url"))

        app_token = (request.form.get("app_token") or "").strip()
        user_token = (request.form.get("user_token") or "").strip()

        if app_token:
            cfg.app_token = _glpi_invfis_encrypt(app_token)
        if user_token:
            cfg.user_token = _glpi_invfis_encrypt(user_token)

        # No se diligencian valores por defecto que no vengan de GLPI.
        cfg.area_id_default = None
        cfg.division_default = ""
        cfg.ciudad_default = ""
        cfg.pais_default = ""
        cfg.c_nivel_default = 0
        cfg.i_nivel_default = 0
        cfg.d_nivel_default = 0

        cfg.verificar_ssl = True if request.form.get("verificar_ssl") == "1" else False
        cfg.timeout = request.form.get("timeout", type=int) or 30
        cfg.activo = True

        db.session.add(cfg)
        db.session.commit()

        if accion == "probar":
            session_token = None
            try:
                session_token = _glpi_invfis_init_session(cfg)
                cfg.ultima_prueba = datetime.utcnow()
                cfg.ultimo_estado = "OK"
                cfg.ultimo_mensaje = "Conexión exitosa con GLPI."
                db.session.add(cfg)
                db.session.commit()
                flash("Conexión exitosa con GLPI.", "success")
            except Exception as e:
                cfg.ultima_prueba = datetime.utcnow()
                cfg.ultimo_estado = "ERROR"
                cfg.ultimo_mensaje = str(e)
                db.session.add(cfg)
                db.session.commit()
                flash(f"Error probando conexión GLPI: {str(e)}", "danger")
            finally:
                if session_token:
                    _glpi_invfis_kill_session(cfg, session_token)
        else:
            flash("Configuración GLPI guardada correctamente.", "success")

        return redirect(url_for('inventario_fisico_glpi_config'))

    html = """
    <div class="glpiinv-shell">

      <div class="glpiinv-header-card">
        <div class="glpiinv-header-overlay">
          <div class="glpiinv-header-text">
            <h3 class="glpiinv-title m-0">Configurar conexión GLPI</h3>
            <div class="glpiinv-subtitle">
              Parámetros de integración para importar exclusivamente datos existentes en GLPI al Inventario Físico GRAC
            </div>
          </div>
        </div>
      </div>

      <div class="glpiinv-header-actions">
        <a href="{{ url_for('inventario_fisico') }}"
           class="btn rounded-pill px-4 fw-bold glpiinv-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="glpiinv-card">
        <div class="glpiinv-card-body">

          {% with msgs = get_flashed_messages(with_categories=true) %}
            {% if msgs %}
              {% for cat, msg in msgs %}
                <div class="alert alert-{{ 'warning' if cat=='message' else cat }} alert-dismissible fade show" role="alert">
                  {{ msg }}
                  <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
              {% endfor %}
            {% endif %}
          {% endwith %}

          <form method="post">
            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Nombre de la conexión</label>
                <input type="text" name="nombre" class="form-control" value="{{ cfg.nombre or '' }}">
              </div>

              <div class="col-md-8">
                <label class="form-label">URL API REST GLPI</label>
                <input type="text"
                       name="base_url"
                       class="form-control"
                       required
                       placeholder="http://192.168.0.10:8080/apirest.php"
                       value="{{ cfg.base_url or '' }}">
                <small class="text-muted">Puede ser con o sin /apirest.php. El sistema lo normaliza.</small>
              </div>

              <div class="col-md-6">
                <label class="form-label">App Token</label>
                <input type="password" name="app_token" class="form-control" placeholder="Dejar vacío para conservar el actual">
              </div>

              <div class="col-md-6">
                <label class="form-label">User Token</label>
                <input type="password" name="user_token" class="form-control" placeholder="Dejar vacío para conservar el actual">
              </div>

              <div class="col-md-2">
                <label class="form-label">Timeout</label>
                <input type="number" name="timeout" class="form-control" min="5" max="300" value="{{ cfg.timeout or 30 }}">
              </div>

              <div class="col-md-12">
                <div class="form-check mt-2">
                  <input class="form-check-input" type="checkbox" name="verificar_ssl" value="1" id="verificar_ssl"
                         {% if cfg.verificar_ssl %}checked{% endif %}>
                  <label class="form-check-label fw-bold" for="verificar_ssl">
                    Verificar certificado SSL
                  </label>
                </div>
              </div>

            </div>

            <div class="glpiinv-status-box mt-4">
              <div><b>Última prueba:</b> {{ cfg.ultima_prueba or '—' }}</div>
              <div><b>Última sincronización:</b> {{ cfg.ultimo_sync or '—' }}</div>
              <div><b>Estado:</b> {{ cfg.ultimo_estado or '—' }}</div>
              <div><b>Mensaje:</b> {{ cfg.ultimo_mensaje or '—' }}</div>
            </div>

            <div class="glpiinv-note mt-3">
              <b>Nota:</b> la importación no diligencia valores por defecto de GRAC. Solo se guardan datos que existan en GLPI.
              El campo <b>Asignado a</b> se toma del campo <b>name</b> de GLPI. <b>Procesador</b> se toma de <b>Arquitecturas</b>. <b>Tipo de sistema</b> se toma del <b>Nombre del Operating system</b>, <b>Versión SO</b> del <b>Kernel</b> y <b>Edición del SO</b> de <b>Edición</b>.
            </div>

            <div class="glpiinv-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" name="accion" value="guardar" type="submit">
                💾 Guardar configuración
              </button>
              <button class="btn btn-primary rounded-pill px-4 fw-bold" name="accion" value="probar" type="submit">
                🔌 Probar conexión
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

      .glpiinv-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      .glpiinv-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        color:#fff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .glpiinv-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .glpiinv-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        position:relative;
        z-index:1;
      }

      .glpiinv-header-overlay::before{
        content:"🔌";
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
        margin-right:14px;
      }

      .glpiinv-header-text::before{
        content:"SGSI · GLPI Inventario Físico";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .glpiinv-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .glpiinv-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .glpiinv-header-actions,
      .glpiinv-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .glpiinv-header-actions .btn,
      .glpiinv-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .glpiinv-back-btn{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .glpiinv-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .glpiinv-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .glpiinv-card-body{
        padding:16px 18px;
      }

      .glpiinv-card .form-label{
        font-weight:800;
        color:#25324a;
        font-size:.78rem;
      }

      .glpiinv-card .form-control,
      .glpiinv-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .glpiinv-status-box,
      .glpiinv-note{
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px 14px;
        background:#f8fbff;
        font-size:.82rem;
        color:#24324a;
      }
    </style>
    """

    inner = render_template_string(html, cfg=cfg)
    return render_template_string(BASE, content=Markup(inner))


# =========================
# RUTA — Sincronizar GLPI → Inventario Físico
# =========================
@app.route('/inventario_fisico/glpi/sync', methods=['POST'])
@login_required
def inventario_fisico_glpi_sync():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin'
        and not verificar_permiso(user, "Gestión de Activos de Información")
    ):
        flash("No tiene permiso para sincronizar GLPI.", "danger")
        return redirect(url_for('inventario_fisico'))

    try:
        resumen = glpi_invfis_sincronizar()

        msg = (
            f"Sincronización GLPI finalizada. "
            f"Creados: {resumen['creados']}, "
            f"Actualizados: {resumen['actualizados']}, "
            f"Omitidos: {resumen['omitidos']}."
        )

        errores = resumen.get("errores") or []
        if errores:
            msg += " Detalle: " + " | ".join(errores[:10])

        flash(msg, "success" if resumen["omitidos"] == 0 else "warning")

    except Exception as e:
        print("ERROR GLPI Inventario Físico:", traceback.format_exc())
        flash(f"Error sincronizando con GLPI: {str(e)}", "danger")

    return redirect(url_for('inventario_fisico'))


@app.route('/inventario_fisico_menu', methods=['GET'])
@login_required
def inventario_fisico_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(
        user, "Gestión de Activos de Información"
    ):
        flash("No tiene permiso para acceder al módulo de inventarios físico.", "danger")
        return redirect(url_for('activos_menu'))

    return redirect(url_for('inventario_fisico'))

# =========================
# AGREGAR — Inventario Físico
# =========================
@app.route('/inventario_fisico/new', methods=['GET', 'POST'])
@login_required
def inventario_fisico_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('inventario_fisico'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Activos de Información"):
        flash("No tiene permiso para agregar registros de activos.", "danger")
        return redirect(url_for('inventario_fisico'))
    
    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()
    paises = sorted([c.name for c in pycountry.countries])

    conf_opts = ValoracionConfidencialidad.query.order_by(ValoracionConfidencialidad.nivel_num.asc()).all()
    inte_opts = ValoracionIntegridad.query.order_by(ValoracionIntegridad.nivel_num.asc()).all()
    disp_opts = ValoracionDisponibilidad.query.order_by(ValoracionDisponibilidad.nivel_num.asc()).all()

    if request.method == 'POST':
        area_id = request.form.get('area_id', type=int)
        division = (request.form.get('division') or '').strip()

        asignado_a = (request.form.get('asignado_a') or '').strip()
        cargo      = (request.form.get('cargo') or '').strip()
        ciudad     = (request.form.get('ciudad') or '').strip()

        clase_activo = (request.form.get('clase_activo') or '').strip()
        marca        = (request.form.get('marca') or '').strip()

        mouse         = request.form.get('mouse') or 'No'
        teclado       = request.form.get('teclado') or 'No'
        base_portatil = request.form.get('base_portatil') or 'No'
        monitor       = request.form.get('monitor') or 'No'

        numero_serial      = (request.form.get('numero_serial') or '').strip()
        nombre_dispositivo = (request.form.get('nombre_dispositivo') or '').strip()
        procesador         = (request.form.get('procesador') or '').strip()
        ram_instalada      = (request.form.get('ram_instalada') or '').strip()
        id_dispositivo     = (request.form.get('id_dispositivo') or '').strip()
        id_producto        = (request.form.get('id_producto') or '').strip()
        tipo_sistema       = (request.form.get('tipo_sistema') or '').strip()
        edicion_so         = (request.form.get('edicion_so') or '').strip()
        version_so         = (request.form.get('version_so') or '').strip()
        pais               = (request.form.get('pais') or '').strip()

        from datetime import datetime
        fecha_compra_str     = (request.form.get('fecha_compra') or '').strip()
        fecha_asignacion_str = (request.form.get('fecha_asignacion') or '').strip()

        fecha_compra = None
        fecha_asignacion = None
        try:
            fecha_compra = datetime.strptime(fecha_compra_str, '%Y-%m-%d').date() if fecha_compra_str else None
            fecha_asignacion = datetime.strptime(fecha_asignacion_str, '%Y-%m-%d').date() if fecha_asignacion_str else None
        except ValueError:
            flash("Formato de fecha inválido.", "danger")
            return redirect(url_for('inventario_fisico_new'))

        try:
            c_nivel = int(request.form.get('c_nivel') or 0)
            i_nivel = int(request.form.get('i_nivel') or 0)
            d_nivel = int(request.form.get('d_nivel') or 0)
        except ValueError:
            c_nivel = i_nivel = d_nivel = 0

        info_personal          = request.form.get('info_personal') or 'No'
        info_regulada          = request.form.get('info_regulada') or 'No'
        info_sensible          = request.form.get('info_sensible') or 'No'
        info_sensible_clientes = request.form.get('info_sensible_clientes') or 'No'

        observaciones = (request.form.get('observaciones') or '').strip()

        if not (area_id and division and clase_activo and nombre_dispositivo):
            flash("Campos obligatorios: Área, División, Clase de activo y Nombre del dispositivo.", "danger")
            return redirect(url_for('inventario_fisico_new'))

        for n in (c_nivel, i_nivel, d_nivel):
            if n < 1 or n > 5:
                flash("Los niveles C/I/D deben estar entre 1 y 5.", "danger")
                return redirect(url_for('inventario_fisico_new'))

        valor_activo = round((c_nivel + i_nivel + d_nivel) / 3)

        conf_row = ValoracionConfidencialidad.query.filter_by(nivel_num=c_nivel).first()
        etiqueta_conf_num = c_nivel
        etiqueta_conf_texto = conf_row.clasificacion if conf_row else f"Nivel {c_nivel}"

        crit_row = ValoracionCriticidadActivo.query.filter_by(nivel_num=valor_activo).first()
        criticidad_num = valor_activo
        criticidad_texto = crit_row.nivel_texto if crit_row else f"Nivel {valor_activo}"

        it = InventarioFisico(
            area_id=area_id,
            division=division,
            asignado_a=asignado_a,
            cargo=cargo,
            ciudad=ciudad,
            clase_activo=clase_activo,
            marca=marca,
            mouse=mouse,
            teclado=teclado,
            base_portatil=base_portatil,
            monitor=monitor,
            numero_serial=numero_serial,
            nombre_dispositivo=nombre_dispositivo,
            procesador=procesador,
            ram_instalada=ram_instalada,
            id_dispositivo=id_dispositivo,
            id_producto=id_producto,
            tipo_sistema=tipo_sistema,
            edicion_so=edicion_so,
            version_so=version_so,
            pais=pais,
            fecha_compra=fecha_compra,
            fecha_asignacion=fecha_asignacion,
            c_nivel=c_nivel,
            i_nivel=i_nivel,
            d_nivel=d_nivel,
            valor_activo=valor_activo,
            criticidad_num=criticidad_num,
            criticidad_texto=criticidad_texto,
            etiqueta_conf_num=etiqueta_conf_num,
            etiqueta_conf_texto=etiqueta_conf_texto,
            info_personal=info_personal,
            info_regulada=info_regulada,
            info_sensible=info_sensible,
            info_sensible_clientes=info_sensible_clientes,
            observaciones=observaciones
        )
        db.session.add(it)
        db.session.commit()
        flash("Activo físico creado.", "success")
        return redirect(url_for('inventario_fisico'))

    html = """
    <div class="invfis-shell">

      <div class="invfis-header-card">
        <div class="invfis-header-overlay">
          <div class="invfis-header-text">
            <h3 class="invfis-title m-0">Agregar — Inventario Físico</h3>
            <div class="invfis-subtitle">
              Registro y clasificación de activos físicos del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="invfis-header-actions">
        <a href="{{ url_for('inventario_fisico') }}"
           class="btn rounded-pill px-4 fw-bold invfis-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="invfis-card">
        <div class="invfis-card-body">
          <form method="post">
            <div class="row g-3">

              <div class="col-md-3">
                <label class="form-label">Área</label>
                <select name="area_id" id="fisArea" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}">{{ a.area }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">División</label>
                <select name="division" id="fisDivision" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Asignado a</label>
                <input type="text" name="asignado_a" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Cargo</label>
                <input type="text" name="cargo" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">País</label>
                <select name="pais" class="form-select">
                  <option value="">-- Seleccione --</option>
                  {% for p in paises %}
                    <option value="{{ p }}">{{ p }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Ciudad</label>
                <input type="text" name="ciudad" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Clase de activo</label>
                <select name="clase_activo" class="form-select" required>
                  {% for opt in ['Laptop','Servidor','Equipo de comunicación','Desktop'] %}
                    <option value="{{ opt }}">{{ opt }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Marca</label>
                <input type="text" name="marca" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Mouse</label>
                <select name="mouse" class="form-select">
                  <option>Sí</option>
                  <option>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Teclado</label>
                <select name="teclado" class="form-select">
                  <option>Sí</option>
                  <option>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Base Portátil</label>
                <select name="base_portatil" class="form-select">
                  <option>Sí</option>
                  <option>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Monitor</label>
                <select name="monitor" class="form-select">
                  <option>Sí</option>
                  <option>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Número de serial</label>
                <input type="text" name="numero_serial" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Nombre del dispositivo</label>
                <input type="text" name="nombre_dispositivo" class="form-control" required>
              </div>

              <div class="col-md-3">
                <label class="form-label">Procesador</label>
                <input type="text" name="procesador" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">RAM instalada</label>
                <input type="text" name="ram_instalada" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Id. del dispositivo</label>
                <input type="text" name="id_dispositivo" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Id. del producto</label>
                <input type="text" name="id_producto" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Tipo de sistema operativo</label>
                <input type="text" name="tipo_sistema" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Edición del SO</label>
                <input type="text" name="edicion_so" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Versión</label>
                <input type="text" name="version_so" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de compra</label>
                <input type="date" name="fecha_compra" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de asignación del equipo</label>
                <input type="date" name="fecha_asignacion" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Clasificación Confidencialidad</label>
                <select name="c_nivel" class="form-select">
                  {% for o in conf_opts %}
                    <option value="{{ o.nivel_num }}">{{ o.nivel_num }} — {{ o.clasificacion }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Clasificación Integridad</label>
                <select name="i_nivel" class="form-select">
                  {% for o in inte_opts %}
                    <option value="{{ o.nivel_num }}">{{ o.nivel_num }} — {{ o.nivel }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Clasificación Disponibilidad</label>
                <select name="d_nivel" class="form-select">
                  {% for o in disp_opts %}
                    <option value="{{ o.nivel_num }}">{{ o.nivel_num }} — {{ o.nivel }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Es Información Personal?</label>
                <select name="info_personal" class="form-select">
                  <option>Sí</option>
                  <option>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Es información regulada por una legislación?</label>
                <select name="info_regulada" class="form-select">
                  <option>Sí</option>
                  <option>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Es información sensible de la Compañía?</label>
                <select name="info_sensible" class="form-select">
                  <option>Sí</option>
                  <option>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Es información sensible de Clientes?</label>
                <select name="info_sensible_clientes" class="form-select">
                  <option>Sí</option>
                  <option>No</option>
                </select>
              </div>

              <div class="col-12">
                <label class="form-label">Observaciones</label>
                <textarea name="observaciones" class="form-control" rows="2"></textarea>
              </div>

            </div>

            <div class="invfis-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>
              <a href="{{ url_for('inventario_fisico') }}"
                 class="btn rounded-pill px-4 fw-bold invfis-cancel-btn">
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

      .invfis-shell{
        width:96%;
        max-width:1550px;
        margin:10px auto 24px auto;
      }

      .invfis-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .invfis-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .invfis-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent;
        padding:0;
        position:relative;
        z-index:1;
      }

      .invfis-header-overlay::before{
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
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .invfis-header-text{
        max-width:1100px;
        width:100%;
      }

      .invfis-header-text::before{
        content:"SGSI · Inventario Físico";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .invfis-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .invfis-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .invfis-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .invfis-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invfis-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invfis-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .invfis-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .invfis-card-body{
        padding:18px;
      }

      .invfis-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .invfis-card .form-control,
      .invfis-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .invfis-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .invfis-card .form-control:focus,
      .invfis-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }

      .invfis-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .invfis-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invfis-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invfis-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .invfis-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .invfis-header-card{
          min-height:88px;
        }

        .invfis-title{
          font-size:1.20rem;
        }

        .invfis-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .invfis-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .invfis-header-overlay::before{
          margin:0;
        }

        .invfis-header-actions .btn,
        .invfis-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        areas=areas,
        paises=paises,
        conf_opts=conf_opts,
        inte_opts=inte_opts,
        disp_opts=disp_opts
    )
    return render_template_string(BASE, content=Markup(inner))

# =========================
# EDICIÓN — Inventario Físico
# =========================
@app.route('/inventario_fisico/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def inventario_fisico_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Gestión de Activos de Información")
    ):
        flash("No tiene permiso para editar registros de activos físicos.", "danger")
        return redirect(url_for('inventario_fisico'))
    
    item = InventarioFisico.query.get_or_404(id)

    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()
    paises = sorted([c.name for c in pycountry.countries])
    divisiones = DivisionEmpresa.query.order_by(
        DivisionEmpresa.area_id.asc(),
        DivisionEmpresa.nombre_division.asc()
    ).all()

    div_map = {}
    for d in divisiones:
        div_map.setdefault(d.area_id, []).append(d.nombre_division)

    conf_opts = ValoracionConfidencialidad.query.order_by(ValoracionConfidencialidad.nivel_num.asc()).all()
    inte_opts = ValoracionIntegridad.query.order_by(ValoracionIntegridad.nivel_num.asc()).all()
    disp_opts = ValoracionDisponibilidad.query.order_by(ValoracionDisponibilidad.nivel_num.asc()).all()

    if request.method == 'POST':
        item.area_id = request.form.get('area_id', type=int)
        item.division = (request.form.get('division') or '').strip()

        item.asignado_a = (request.form.get('asignado_a') or '').strip()
        item.cargo      = (request.form.get('cargo') or '').strip()
        item.ciudad     = (request.form.get('ciudad') or '').strip()

        item.clase_activo = (request.form.get('clase_activo') or '').strip()
        item.marca        = (request.form.get('marca') or '').strip()

        item.mouse         = request.form.get('mouse') or 'No'
        item.teclado       = request.form.get('teclado') or 'No'
        item.base_portatil = request.form.get('base_portatil') or 'No'
        item.monitor       = request.form.get('monitor') or 'No'

        item.numero_serial      = (request.form.get('numero_serial') or '').strip()
        item.nombre_dispositivo = (request.form.get('nombre_dispositivo') or '').strip()
        item.procesador         = (request.form.get('procesador') or '').strip()
        item.ram_instalada      = (request.form.get('ram_instalada') or '').strip()
        item.id_dispositivo     = (request.form.get('id_dispositivo') or '').strip()
        item.id_producto        = (request.form.get('id_producto') or '').strip()
        item.tipo_sistema       = (request.form.get('tipo_sistema') or '').strip()
        item.edicion_so         = (request.form.get('edicion_so') or '').strip()
        item.version_so         = (request.form.get('version_so') or '').strip()
        item.pais               = (request.form.get('pais') or '').strip()

        from datetime import datetime
        fecha_compra_str     = (request.form.get('fecha_compra') or '').strip()
        fecha_asignacion_str = (request.form.get('fecha_asignacion') or '').strip()

        try:
            item.fecha_compra = datetime.strptime(fecha_compra_str, '%Y-%m-%d').date() if fecha_compra_str else None
            item.fecha_asignacion = datetime.strptime(fecha_asignacion_str, '%Y-%m-%d').date() if fecha_asignacion_str else None
        except ValueError:
            flash("Formato de fecha inválido.", "danger")
            return redirect(url_for('inventario_fisico_edit', id=item.id))

        try:
            item.c_nivel = int(request.form.get('c_nivel') or 0)
            item.i_nivel = int(request.form.get('i_nivel') or 0)
            item.d_nivel = int(request.form.get('d_nivel') or 0)
        except ValueError:
            item.c_nivel = item.i_nivel = item.d_nivel = 0

        item.info_personal          = request.form.get('info_personal') or 'No'
        item.info_regulada          = request.form.get('info_regulada') or 'No'
        item.info_sensible          = request.form.get('info_sensible') or 'No'
        item.info_sensible_clientes = request.form.get('info_sensible_clientes') or 'No'
        item.observaciones          = (request.form.get('observaciones') or '').strip()

        if not (item.area_id and item.division and item.clase_activo and item.nombre_dispositivo):
            flash("Campos obligatorios: Área, División, Clase de activo y Nombre del dispositivo.", "danger")
            return redirect(url_for('inventario_fisico_edit', id=item.id))

        for n in (item.c_nivel, item.i_nivel, item.d_nivel):
            if n < 1 or n > 5:
                flash("Los niveles C/I/D deben estar entre 1 y 5.", "danger")
                return redirect(url_for('inventario_fisico_edit', id=item.id))

        item.valor_activo = round((item.c_nivel + item.i_nivel + item.d_nivel) / 3)

        conf_row = ValoracionConfidencialidad.query.filter_by(nivel_num=item.c_nivel).first()
        item.etiqueta_conf_num = item.c_nivel
        item.etiqueta_conf_texto = conf_row.clasificacion if conf_row else f"Nivel {item.c_nivel}"

        crit_row = ValoracionCriticidadActivo.query.filter_by(nivel_num=item.valor_activo).first()
        item.criticidad_num = item.valor_activo
        item.criticidad_texto = crit_row.nivel_texto if crit_row else f"Nivel {item.valor_activo}"

        db.session.add(item)
        db.session.commit()
        flash("Cambios guardados.", "success")
        return redirect(url_for('inventario_fisico'))

    html = """
    <div class="invfisedit-shell">

      <div class="invfisedit-header-card">
        <div class="invfisedit-header-overlay">
          <div class="invfisedit-header-text">
            <h3 class="invfisedit-title m-0">Editar — Inventario Físico</h3>
            <div class="invfisedit-subtitle">
              Actualización de activos físicos del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="invfisedit-header-actions">
        <a href="{{ url_for('inventario_fisico') }}"
           class="btn rounded-pill px-4 fw-bold invfisedit-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="invfisedit-card">
        <div class="invfisedit-card-body">
          <form method="post">
            <div class="row g-3">

              <div class="col-md-3">
                <label class="form-label">Área</label>
                <select name="area_id" id="fisAreaEdit" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}" {% if item.area_id == a.id %}selected{% endif %}>
                      {{ a.area }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">División</label>
                <select name="division" id="fisDivisionEdit" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  {% if item.division %}
                    <option value="{{ item.division }}" selected>{{ item.division }}</option>
                  {% endif %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Asignado a</label>
                <input type="text" name="asignado_a" class="form-control" value="{{ item.asignado_a or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Cargo</label>
                <input type="text" name="cargo" class="form-control" value="{{ item.cargo or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">País</label>
                <select name="pais" class="form-select">
                  <option value="">-- Seleccione --</option>
                  {% for p in paises %}
                    <option value="{{ p }}" {% if item.pais == p %}selected{% endif %}>{{ p }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Ciudad</label>
                <input type="text" name="ciudad" class="form-control" value="{{ item.ciudad or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Clase de activo</label>
                <select name="clase_activo" class="form-select" required>
                  {% for opt in ['Laptop','Servidor','Equipo de comunicación','Desktop'] %}
                    <option value="{{ opt }}" {% if item.clase_activo == opt %}selected{% endif %}>{{ opt }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Marca</label>
                <input type="text" name="marca" class="form-control" value="{{ item.marca or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Mouse</label>
                <select name="mouse" class="form-select">
                  <option value="Sí" {% if item.mouse == 'Sí' %}selected{% endif %}>Sí</option>
                  <option value="No" {% if item.mouse == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Teclado</label>
                <select name="teclado" class="form-select">
                  <option value="Sí" {% if item.teclado == 'Sí' %}selected{% endif %}>Sí</option>
                  <option value="No" {% if item.teclado == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Base Portátil</label>
                <select name="base_portatil" class="form-select">
                  <option value="Sí" {% if item.base_portatil == 'Sí' %}selected{% endif %}>Sí</option>
                  <option value="No" {% if item.base_portatil == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Monitor</label>
                <select name="monitor" class="form-select">
                  <option value="Sí" {% if item.monitor == 'Sí' %}selected{% endif %}>Sí</option>
                  <option value="No" {% if item.monitor == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Número de serial</label>
                <input type="text" name="numero_serial" class="form-control" value="{{ item.numero_serial or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Nombre del dispositivo</label>
                <input type="text" name="nombre_dispositivo" class="form-control" value="{{ item.nombre_dispositivo or '' }}" required>
              </div>

              <div class="col-md-3">
                <label class="form-label">Procesador</label>
                <input type="text" name="procesador" class="form-control" value="{{ item.procesador or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">RAM instalada</label>
                <input type="text" name="ram_instalada" class="form-control" value="{{ item.ram_instalada or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Id. del dispositivo</label>
                <input type="text" name="id_dispositivo" class="form-control" value="{{ item.id_dispositivo or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Id. del producto</label>
                <input type="text" name="id_producto" class="form-control" value="{{ item.id_producto or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Tipo de sistema operativo</label>
                <input type="text" name="tipo_sistema" class="form-control" value="{{ item.tipo_sistema or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Edición del SO</label>
                <input type="text" name="edicion_so" class="form-control" value="{{ item.edicion_so or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Versión</label>
                <input type="text" name="version_so" class="form-control" value="{{ item.version_so or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de compra</label>
                <input type="date" name="fecha_compra" class="form-control"
                       value="{{ item.fecha_compra.strftime('%Y-%m-%d') if item.fecha_compra else '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de asignación del equipo</label>
                <input type="date" name="fecha_asignacion" class="form-control"
                       value="{{ item.fecha_asignacion.strftime('%Y-%m-%d') if item.fecha_asignacion else '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Clasificación Confidencialidad</label>
                <select name="c_nivel" class="form-select">
                  {% for o in conf_opts %}
                    <option value="{{ o.nivel_num }}" {% if item.c_nivel == o.nivel_num %}selected{% endif %}>{{ o.nivel_num }} — {{ o.clasificacion }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Clasificación Integridad</label>
                <select name="i_nivel" class="form-select">
                  {% for o in inte_opts %}
                    <option value="{{ o.nivel_num }}" {% if item.i_nivel == o.nivel_num %}selected{% endif %}>{{ o.nivel_num }} — {{ o.nivel }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Clasificación Disponibilidad</label>
                <select name="d_nivel" class="form-select">
                  {% for o in disp_opts %}
                    <option value="{{ o.nivel_num }}" {% if item.d_nivel == o.nivel_num %}selected{% endif %}>{{ o.nivel_num }} — {{ o.nivel }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Es Información Personal?</label>
                <select name="info_personal" class="form-select">
                  <option value="Sí" {% if item.info_personal == 'Sí' %}selected{% endif %}>Sí</option>
                  <option value="No" {% if item.info_personal == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Es información regulada por una legislación?</label>
                <select name="info_regulada" class="form-select">
                  <option value="Sí" {% if item.info_regulada == 'Sí' %}selected{% endif %}>Sí</option>
                  <option value="No" {% if item.info_regulada == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Es información sensible de la Compañía?</label>
                <select name="info_sensible" class="form-select">
                  <option value="Sí" {% if item.info_sensible == 'Sí' %}selected{% endif %}>Sí</option>
                  <option value="No" {% if item.info_sensible == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Es información sensible de Clientes?</label>
                <select name="info_sensible_clientes" class="form-select">
                  <option value="Sí" {% if item.info_sensible_clientes == 'Sí' %}selected{% endif %}>Sí</option>
                  <option value="No" {% if item.info_sensible_clientes == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-12">
                <label class="form-label">Observaciones</label>
                <textarea name="observaciones" class="form-control" rows="2">{{ item.observaciones or '' }}</textarea>
              </div>

            </div>

            <div class="invfisedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>
              <a href="{{ url_for('inventario_fisico') }}"
                 class="btn rounded-pill px-4 fw-bold invfisedit-cancel-btn">
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

      /* =========================
         CONTENEDOR
         ========================= */
      .invfisedit-shell{
        width:96%;
        max-width:1450px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HEADER SGSI PRO
         ========================= */
      .invfisedit-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .invfisedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .invfisedit-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .invfisedit-header-overlay::before{
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
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .invfisedit-header-text{
        max-width:1100px;
        width:100%;
      }

      .invfisedit-header-text::before{
        content:"SGSI · Inventario Físico";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .invfisedit-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .invfisedit-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES SUPERIORES
         ========================= */
      .invfisedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .invfisedit-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invfisedit-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invfisedit-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD
         ========================= */
      .invfisedit-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .invfisedit-card-body{
        padding:18px;
      }

      /* =========================
         FORMULARIOS (COMPACTOS PRO)
         ========================= */
      .invfisedit-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .invfisedit-card .form-control,
      .invfisedit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .invfisedit-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .invfisedit-card .form-control:focus,
      .invfisedit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }

      /* =========================
         BOTONES INFERIORES
         ========================= */
      .invfisedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .invfisedit-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invfisedit-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invfisedit-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         RESPONSIVE
         ========================= */
      @media (max-width:992px){
        .invfisedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .invfisedit-title{
          font-size:1.20rem;
        }

        .invfisedit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .invfisedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .invfisedit-header-overlay::before{
          margin:0;
        }

        .invfisedit-header-actions .btn,
        .invfisedit-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        item=item,
        areas=areas,
        div_map=div_map,
        paises=paises,
        conf_opts=conf_opts,
        inte_opts=inte_opts,
        disp_opts=disp_opts
    )
    return render_template_string(BASE, content=Markup(inner))

# =========================
# MATRIZ — Inventario Físico
# =========================
@app.route('/inventario_fisico', methods=['GET'])
@login_required
def inventario_fisico():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso_activos(user, "Inventario Físico"):
            flash("No tiene permiso para ver los activos físicos.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    items = (
        InventarioFisico.query
        .options(selectinload(InventarioFisico.area))
        .order_by(InventarioFisico.id.desc())
        .all()
    )

    cfg_glpi = _glpi_invfis_config_activa()

    matriz_items = []

    for item in items:
        conf_row = ValoracionConfidencialidad.query.filter_by(nivel_num=item.c_nivel).first() if item.c_nivel is not None else None
        inte_row = ValoracionIntegridad.query.filter_by(nivel_num=item.i_nivel).first() if item.i_nivel is not None else None
        disp_row = ValoracionDisponibilidad.query.filter_by(nivel_num=item.d_nivel).first() if item.d_nivel is not None else None
        valor_row = ValoracionCriticidadActivo.query.filter_by(nivel_num=item.valor_activo).first() if item.valor_activo is not None else None

        conf_texto = conf_row.clasificacion if conf_row and getattr(conf_row, 'clasificacion', None) else (item.etiqueta_conf_texto or (f"Nivel {item.c_nivel}" if item.c_nivel is not None else "—"))
        inte_texto = inte_row.nivel if inte_row and getattr(inte_row, 'nivel', None) else (f"Nivel {item.i_nivel}" if item.i_nivel is not None else "—")
        disp_texto = disp_row.nivel if disp_row and getattr(disp_row, 'nivel', None) else (f"Nivel {item.d_nivel}" if item.d_nivel is not None else "—")
        valor_texto = valor_row.nivel_texto if valor_row and getattr(valor_row, 'nivel_texto', None) else (f"Nivel {item.valor_activo}" if item.valor_activo is not None else "—")
        criticidad_texto = item.criticidad_texto or (f"Nivel {item.criticidad_num}" if item.criticidad_num is not None else "—")
        etiquetado_texto = item.etiqueta_conf_texto or (
            conf_row.clasificacion if conf_row and getattr(conf_row, 'clasificacion', None)
            else (f"Nivel {item.etiqueta_conf_num}" if item.etiqueta_conf_num is not None else "—")
        )

        matriz_items.append({
            "item": item,
            "conf_texto": conf_texto,
            "inte_texto": inte_texto,
            "disp_texto": disp_texto,
            "valor_texto": valor_texto,
            "criticidad_texto": criticidad_texto,
            "etiquetado_texto": etiquetado_texto,
        })

    html = """
    <div class="invfismat-shell">

      <div class="invfismat-header-card">
        <div class="invfismat-header-overlay">
          <div class="invfismat-header-text">
            <h3 class="invfismat-title m-0">Inventario Físico — Matriz</h3>
            <div class="invfismat-subtitle">
              Visualización resumida de activos físicos del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="invfismat-header-actions">
        {% if not read_only %}
          <a href="{{ url_for('inventario_fisico_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            ➕ Agregar Activo
          </a>

          <a href="{{ url_for('inventario_fisico_glpi_config') }}"
             class="btn rounded-pill px-4 fw-bold invfismat-btn-config-glpi">
            ⚙️ Configurar GLPI
          </a>

          <form method="post"
                action="{{ url_for('inventario_fisico_glpi_sync') }}"
                class="d-inline"
                onsubmit="return confirm('¿Desea sincronizar los equipos de GLPI con la matriz de inventario físico?');">
            <button type="submit"
                    class="btn rounded-pill px-4 fw-bold invfismat-btn-glpi">
              🔌 Sincronizar GLPI
            </button>
          </form>
        {% else %}
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            ➕ Agregar Activo
          </button>
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            🔌 Sincronizar GLPI
          </button>
        {% endif %}
      </div>

      {% if cfg_glpi %}
        <div class="invfismat-glpi-status">
          <b>GLPI:</b> {{ cfg_glpi.base_url or 'Sin URL' }}
          <span class="mx-2">|</span>
          <b>Último sync:</b> {{ cfg_glpi.ultimo_sync or '—' }}
          <span class="mx-2">|</span>
          <b>Estado:</b> {{ cfg_glpi.ultimo_estado or '—' }}
          {% if cfg_glpi.ultimo_mensaje %}
            <span class="mx-2">|</span>
            {{ cfg_glpi.ultimo_mensaje }}
          {% endif %}
        </div>
      {% else %}
        <div class="invfismat-glpi-status">
          <b>GLPI:</b> no configurado. Use el botón <b>Configurar GLPI</b>.
        </div>
      {% endif %}

      <style>
        .badge-n1 { background:#2ecc71; color:#fff; }
        .badge-n2 { background:#f1c40f; color:#111; }
        .badge-n3 { background:#e67e22; color:#fff; }
        .badge-n4 { background:#e74c3c; color:#fff; }
        .badge-n5 { background:#8e44ad; color:#fff; }
      </style>

      <div class="invfismat-card">
        <div class="invfismat-topbar">
          <div>
            <h5 class="invfismat-top-title mb-1">Resumen de activos físicos</h5>
            <div class="invfismat-top-note">
              La matriz muestra los niveles de valoración en texto. Para consultar toda la información utilice el botón <strong>Ver detalle</strong>.
            </div>
          </div>

          <div class="invfismat-counter-badge">
            Total registros: {{ matriz_items|length }}
          </div>
        </div>

        <div class="invfismat-card-body">
          <div class="invfismat-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-hover align-middle invfismat-table mb-0">

                <colgroup>
                  <col style="width: 10%;">
                  <col style="width: 10%;">
                  <col style="width: 13%;">
                  <col style="width: 9%;">
                  <col style="width: 9%;">
                  <col style="width: 11%;">
                  <col style="width: 11%;">
                  <col style="width: 11%;">
                  <col style="width: 11%;">
                  <col style="width: 11%;">
                  <col style="width: 12%;">
                  <col style="width: 14%;">
                </colgroup>

                <thead>
                  <tr>
                    <th>Área</th>
                    <th>División</th>
                    <th>Nombre del dispositivo</th>
                    <th>Clase</th>
                    <th>Marca</th>
                    <th>Confidencialidad</th>
                    <th>Integridad</th>
                    <th>Disponibilidad</th>
                    <th>Valor</th>
                    <th>Criticidad</th>
                    <th>Etiquetado</th>
                    <th class="invfismat-col-acciones">Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  {% for row in matriz_items %}
                    {% set item = row.item %}
                    <tr>
                      <td>{{ item.area.area if item.area else '—' }}</td>
                      <td>{{ item.division or '—' }}</td>

                      <td class="invfismat-cell-main">
                        <div class="invfismat-main-text">{{ item.nombre_dispositivo or '—' }}</div>
                      </td>

                      <td>{{ item.clase_activo or '—' }}</td>
                      <td>{{ item.marca or '—' }}</td>

                      <td class="text-center">
                        <span class="badge badge-n{{ item.c_nivel or 1 }} invfismat-badge-text">
                          {{ row.conf_texto }}
                        </span>
                      </td>

                      <td class="text-center">
                        <span class="badge badge-n{{ item.i_nivel or 1 }} invfismat-badge-text">
                          {{ row.inte_texto }}
                        </span>
                      </td>

                      <td class="text-center">
                        <span class="badge badge-n{{ item.d_nivel or 1 }} invfismat-badge-text">
                          {{ row.disp_texto }}
                        </span>
                      </td>

                      <td class="text-center">
                        <span class="badge badge-n{{ item.valor_activo or 1 }} invfismat-badge-text">
                          {{ row.valor_texto }}
                        </span>
                      </td>

                      <td class="text-center">
                        <span class="badge badge-n{{ item.criticidad_num or 1 }} invfismat-badge-text">
                          {{ row.criticidad_texto }}
                        </span>
                      </td>

                      <td class="text-center">
                        <span class="badge badge-n{{ item.etiqueta_conf_num or 1 }} invfismat-badge-text">
                          {{ row.etiquetado_texto }}
                        </span>
                      </td>

                      <td class="text-center invfismat-col-acciones">
                        <div class="invfismat-actions-wrap">

                          <a href="{{ url_for('inventario_fisico_detalle', id=item.id) }}"
                             class="btn btn-info btn-sm rounded-pill invfismat-btn-action text-white fw-bold">
                            Ver detalle
                          </a>

                          {% if not read_only %}
                            <a href="{{ url_for('inventario_fisico_edit', id=item.id) }}"
                               class="btn btn-warning btn-sm rounded-pill invfismat-btn-action fw-bold">
                              Editar
                            </a>

                            <a href="{{ url_for('inventario_fisico_delete', id=item.id) }}"
                               class="btn btn-danger btn-sm rounded-pill invfismat-btn-action fw-bold"
                               onclick="return confirm('¿Eliminar este activo físico?');">
                              Eliminar
                            </a>
                          {% else %}
                            <span class="badge bg-secondary">Solo lectura</span>
                          {% endif %}

                        </div>
                      </td>
                    </tr>
                  {% endfor %}

                  {% if matriz_items|length == 0 %}
                    <tr>
                      <td colspan="12" class="text-center text-muted py-5">
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

      .invfismat-shell{
        width:96%;
        max-width:1850px;
        margin:10px auto 24px auto;
      }

      .invfismat-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .invfismat-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .invfismat-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent;
        padding:0;
        position:relative;
        z-index:1;
      }

      .invfismat-header-overlay::before{
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
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .invfismat-header-text{
        max-width:1100px;
        width:100%;
      }

      .invfismat-header-text::before{
        content:"SGSI · Matriz Inventario Físico";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .invfismat-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .invfismat-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .invfismat-header-actions{
        display:flex;
        justify-content:center;
        align-items:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .invfismat-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .invfismat-btn-config-glpi{
        background:#475569;
        color:#fff;
        border:1px solid #475569;
      }

      .invfismat-btn-config-glpi:hover{
        background:#475569;
        color:#fff;
        border-color:#475569;
      }

      .invfismat-btn-glpi{
        background:#0b65d8;
        color:#fff;
        border:1px solid #0b65d8;
      }

      .invfismat-btn-glpi:hover{
        background:#084fa8;
        color:#fff;
        border-color:#084fa8;
      }

      .invfismat-glpi-status{
        width:100%;
        max-width:1850px;
        margin:0 auto 12px auto;
        background:rgba(255,255,255,.92);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:10px 14px;
        box-shadow:0 8px 18px rgba(15,23,42,.12);
        font-size:.80rem;
        color:#25324a;
        text-align:center;
      }

      .invfismat-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .invfismat-topbar{
        padding:14px 18px;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:14px;
        background:linear-gradient(180deg,#ffffff 0%,#f5f9ff 100%);
        border-bottom:1px solid #e2e8f0;
      }

      .invfismat-top-title{
        font-weight:950;
        color:#1e293b;
        font-size:1rem;
      }

      .invfismat-top-note{
        font-size:.78rem;
        color:#475569;
      }

      .invfismat-counter-badge{
        background:#0b4a8f;
        color:#fff;
        border-radius:999px;
        padding:8px 14px;
        font-weight:900;
        font-size:.78rem;
        white-space:nowrap;
        box-shadow:0 8px 16px rgba(20,89,166,.22);
      }

      .invfismat-card-body{
        padding:16px 18px;
      }

      .invfismat-table-wrap{
        max-height:72vh;
        overflow:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#fff;
      }

      .invfismat-table{
        min-width:1450px;
        table-layout:fixed;
      }

      .invfismat-table th,
      .invfismat-table td{
        font-size:.68rem;
        padding:8px 7px;
        vertical-align:middle;
        word-break:break-word;
      }

      .invfismat-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#fff !important;
        font-weight:900;
        text-align:center;
      }

      .invfismat-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .invfismat-table tbody tr:hover{
        background:#eef6ff;
      }

      .invfismat-main-text{
        font-weight:900;
        color:#1e293b;
      }

      .invfismat-badge-text{
        border-radius:999px;
        padding:.42rem .58rem;
        font-size:.68rem;
        font-weight:900;
        white-space:normal;
        line-height:1.15;
        display:inline-block;
        min-width:80px;
      }

      .invfismat-col-acciones{
        min-width:170px;
      }

      .invfismat-actions-wrap{
        display:flex;
        justify-content:center;
        align-items:center;
        gap:6px;
        flex-wrap:wrap;
      }

      .invfismat-btn-action{
        font-size:.64rem !important;
        padding:5px 10px !important;
        box-shadow:0 4px 10px rgba(0,0,0,.10);
      }

      @media (max-width:992px){
        .invfismat-shell{
          width:98%;
        }

        .invfismat-topbar{
          flex-direction:column;
          align-items:flex-start;
        }
      }

      @media (max-width:768px){
        .invfismat-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .invfismat-header-overlay::before{
          margin:0;
        }

        .invfismat-header-actions .btn,
        .invfismat-header-actions form{
          width:100%;
        }

        .invfismat-header-actions form button{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        matriz_items=matriz_items,
        read_only=read_only,
        cfg_glpi=cfg_glpi,
    )
    return render_template_string(BASE, content=Markup(inner))

# =========================
# DETALLE — Inventario Físico
# =========================
@app.route('/inventario_fisico/detalle/<int:id>', methods=['GET'])
@login_required
def inventario_fisico_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role != 'auditor':
        if user.role != 'admin' and not verificar_permiso(user, "Gestión de Activos de Información"):
            flash("No tiene permiso para ver el detalle de activos físicos.", "danger")
            return redirect(url_for('inventario_fisico'))

    item = (
        InventarioFisico.query
        .options(selectinload(InventarioFisico.area))
        .get_or_404(id)
    )

    conf_row = ValoracionConfidencialidad.query.filter_by(
        nivel_num=item.c_nivel
    ).first() if item.c_nivel is not None else None

    inte_row = ValoracionIntegridad.query.filter_by(
        nivel_num=item.i_nivel
    ).first() if item.i_nivel is not None else None

    disp_row = ValoracionDisponibilidad.query.filter_by(
        nivel_num=item.d_nivel
    ).first() if item.d_nivel is not None else None

    valor_row = ValoracionCriticidadActivo.query.filter_by(
        nivel_num=item.valor_activo
    ).first() if item.valor_activo is not None else None

    conf_texto = (
        conf_row.clasificacion
        if conf_row and getattr(conf_row, 'clasificacion', None)
        else (item.etiqueta_conf_texto or (f"Nivel {item.c_nivel}" if item.c_nivel is not None else "—"))
    )

    inte_texto = (
        inte_row.nivel
        if inte_row and getattr(inte_row, 'nivel', None)
        else (f"Nivel {item.i_nivel}" if item.i_nivel is not None else "—")
    )

    disp_texto = (
        disp_row.nivel
        if disp_row and getattr(disp_row, 'nivel', None)
        else (f"Nivel {item.d_nivel}" if item.d_nivel is not None else "—")
    )

    valor_texto = (
        valor_row.nivel_texto
        if valor_row and getattr(valor_row, 'nivel_texto', None)
        else (f"Nivel {item.valor_activo}" if item.valor_activo is not None else "—")
    )

    criticidad_texto = item.criticidad_texto or (
        f"Nivel {item.criticidad_num}" if item.criticidad_num is not None else "—"
    )

    etiquetado_texto = item.etiqueta_conf_texto or (
        conf_row.clasificacion if conf_row and getattr(conf_row, 'clasificacion', None)
        else (f"Nivel {item.etiqueta_conf_num}" if item.etiqueta_conf_num is not None else "—")
    )

    def badge_class(n):
        if n == 1:
            return "badge-n1"
        if n == 2:
            return "badge-n2"
        if n == 3:
            return "badge-n3"
        if n == 4:
            return "badge-n4"
        return "badge-n5"

    conf_badge = badge_class(item.c_nivel or 1)
    inte_badge = badge_class(item.i_nivel or 1)
    disp_badge = badge_class(item.d_nivel or 1)
    valor_badge = badge_class(item.valor_activo or 1)
    criticidad_badge = badge_class(item.criticidad_num or 1)
    etiquetado_badge = badge_class(item.etiqueta_conf_num or 1)

    html = """
    <div class="invfisdet-shell">

      <div class="invfisdet-header-card">
        <div class="invfisdet-header-overlay">
          <div class="invfisdet-header-text">
            <h3 class="invfisdet-title m-0">Detalle — Inventario Físico</h3>
            <div class="invfisdet-subtitle">
              Consulta completa del activo físico registrado en el Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="invfisdet-header-actions">
        <a href="{{ url_for('inventario_fisico') }}"
           class="btn rounded-pill px-4 fw-bold invfisdet-back-btn">
          ⬅ Volver a la Matriz
        </a>

        {% if user.role != 'auditor' %}
          <a href="{{ url_for('inventario_fisico_edit', id=item.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar
          </a>
        {% endif %}
      </div>

      <style>
        .badge-n1 { background:#2ecc71; color:#fff; }
        .badge-n2 { background:#f1c40f; color:#111; }
        .badge-n3 { background:#e67e22; color:#fff; }
        .badge-n4 { background:#e74c3c; color:#fff; }
        .badge-n5 { background:#8e44ad; color:#fff; }
      </style>

      <div class="invfisdet-card">
        <div class="invfisdet-card-body">

          <div class="row g-3">
            <div class="col-md-4">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Área</div>
                <div class="invfisdet-value">{{ item.area.area if item.area else '—' }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="invfisdet-field">
                <div class="invfisdet-label">División</div>
                <div class="invfisdet-value">{{ item.division or '—' }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Clase de activo</div>
                <div class="invfisdet-value">{{ item.clase_activo or '—' }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Asignado a</div>
                <div class="invfisdet-value">{{ item.asignado_a or '—' }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Cargo</div>
                <div class="invfisdet-value">{{ item.cargo or '—' }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Ciudad</div>
                <div class="invfisdet-value">{{ item.ciudad or '—' }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Marca</div>
                <div class="invfisdet-value">{{ item.marca or '—' }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Número de serial</div>
                <div class="invfisdet-value">{{ item.numero_serial or '—' }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Nombre del dispositivo</div>
                <div class="invfisdet-value">{{ item.nombre_dispositivo or '—' }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Procesador</div>
                <div class="invfisdet-value">{{ item.procesador or '—' }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">RAM instalada</div>
                <div class="invfisdet-value">{{ item.ram_instalada or '—' }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">ID del dispositivo</div>
                <div class="invfisdet-value">{{ item.id_dispositivo or '—' }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">ID del producto</div>
                <div class="invfisdet-value">{{ item.id_producto or '—' }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Tipo de sistema</div>
                <div class="invfisdet-value">{{ item.tipo_sistema or '—' }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Edición SO</div>
                <div class="invfisdet-value">{{ item.edicion_so or '—' }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Versión SO</div>
                <div class="invfisdet-value">{{ item.version_so or '—' }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">País</div>
                <div class="invfisdet-value">{{ item.pais or '—' }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Fecha de compra</div>
                <div class="invfisdet-value">{{ item.fecha_compra or '—' }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Fecha de asignación</div>
                <div class="invfisdet-value">{{ item.fecha_asignacion or '—' }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Monitor</div>
                <div class="invfisdet-value">{{ item.monitor or '—' }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Mouse</div>
                <div class="invfisdet-value">{{ item.mouse or '—' }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Teclado</div>
                <div class="invfisdet-value">{{ item.teclado or '—' }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Base portátil</div>
                <div class="invfisdet-value">{{ item.base_portatil or '—' }}</div>
              </div>
            </div>

            <div class="col-md-2">
              <div class="invfisdet-field text-center">
                <div class="invfisdet-label">Confidencialidad</div>
                <span class="badge {{ conf_badge }} invfisdet-badge">{{ conf_texto }}</span>
              </div>
            </div>

            <div class="col-md-2">
              <div class="invfisdet-field text-center">
                <div class="invfisdet-label">Integridad</div>
                <span class="badge {{ inte_badge }} invfisdet-badge">{{ inte_texto }}</span>
              </div>
            </div>

            <div class="col-md-2">
              <div class="invfisdet-field text-center">
                <div class="invfisdet-label">Disponibilidad</div>
                <span class="badge {{ disp_badge }} invfisdet-badge">{{ disp_texto }}</span>
              </div>
            </div>

            <div class="col-md-2">
              <div class="invfisdet-field text-center">
                <div class="invfisdet-label">Valor del Activo</div>
                <span class="badge {{ valor_badge }} invfisdet-badge">{{ valor_texto }}</span>
              </div>
            </div>

            <div class="col-md-2">
              <div class="invfisdet-field text-center">
                <div class="invfisdet-label">Criticidad</div>
                <span class="badge {{ criticidad_badge }} invfisdet-badge">{{ criticidad_texto }}</span>
              </div>
            </div>

            <div class="col-md-2">
              <div class="invfisdet-field text-center">
                <div class="invfisdet-label">Etiquetado</div>
                <span class="badge {{ etiquetado_badge }} invfisdet-badge">{{ etiquetado_texto }}</span>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">¿Es información personal?</div>
                <div class="invfisdet-value">{{ item.info_personal or '—' }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">¿Es información regulada?</div>
                <div class="invfisdet-value">{{ item.info_regulada or '—' }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">¿Info sensible compañía?</div>
                <div class="invfisdet-value">{{ item.info_sensible or '—' }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="invfisdet-field">
                <div class="invfisdet-label">¿Info sensible clientes?</div>
                <div class="invfisdet-value">{{ item.info_sensible_clientes or '—' }}</div>
              </div>
            </div>

            <div class="col-md-12">
              <div class="invfisdet-field">
                <div class="invfisdet-label">Observaciones</div>
                <div class="invfisdet-value">{{ item.observaciones or '—' }}</div>
              </div>
            </div>

          </div>

          <div class="invfisdet-bottom-actions">
            <a href="{{ url_for('inventario_fisico') }}"
               class="btn rounded-pill px-4 fw-bold invfisdet-cancel-btn">
              Cerrar
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

      .invfisdet-shell{
        width:96%;
        max-width:1400px;
        margin:10px auto 24px auto;
      }

      .invfisdet-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .invfisdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 90% 10%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .invfisdet-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .invfisdet-header-overlay::before{
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
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .invfisdet-header-text{
        max-width:1100px;
        width:100%;
      }

      .invfisdet-header-text::before{
        content:"SGSI · Inventario Físico";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .invfisdet-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .invfisdet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .invfisdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .invfisdet-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invfisdet-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invfisdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .invfisdet-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .invfisdet-card-body{
        padding:20px;
      }

      .invfisdet-field{
        background:linear-gradient(180deg,#f8fafc,#ffffff);
        border:1px solid #e2e8f0;
        border-radius:14px;
        padding:8px 7px;
        height:100%;
        box-shadow:0 4px 10px rgba(0,0,0,.05);
      }

      .invfisdet-label{
        font-size:.72rem;
        font-weight:900;
        color:#2563eb;
        text-transform:uppercase;
        letter-spacing:.4px;
        margin-bottom:6px;
      }

      .invfisdet-value{
        color:#0f172a;
        font-size:.90rem;
        white-space:pre-wrap;
        word-break:break-word;
        line-height:1.35;
      }

      .invfisdet-badge{
        font-size:.72rem;
        padding:6px 10px;
        border-radius:999px;
        display:inline-block;
        font-weight:800;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .invfisdet-bottom-actions{
        display:flex;
        justify-content:center;
        gap:12px;
        margin-top:24px;
        flex-wrap:wrap;
      }

      .invfisdet-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
      }

      .invfisdet-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 12px rgba(0,0,0,.10);
      }

      .invfisdet-cancel-btn:hover{
        background:#f1f5f9;
      }

      @media (max-width:992px){
        .invfisdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .invfisdet-title{
          font-size:1.20rem;
        }

        .invfisdet-card-body{
          padding:8px 7px;
        }

        .invfisdet-badge{
          width:100%;
          text-align:center;
        }
      }

      @media (max-width:768px){
        .invfisdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .invfisdet-header-overlay::before{
          margin:0;
        }

        .invfisdet-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        item=item,
        user=user,
        conf_texto=conf_texto,
        inte_texto=inte_texto,
        disp_texto=disp_texto,
        valor_texto=valor_texto,
        criticidad_texto=criticidad_texto,
        etiquetado_texto=etiquetado_texto,
        conf_badge=conf_badge,
        inte_badge=inte_badge,
        disp_badge=disp_badge,
        valor_badge=valor_badge,
        criticidad_badge=criticidad_badge,
        etiquetado_badge=etiquetado_badge
    )
    return render_template_string(BASE, content=Markup(inner))

# =========================
# ELIMINAR — Inventario Físico
# =========================
@app.route('/inventario_fisico/delete/<int:id>')
@login_required
def inventario_fisico_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin'
        and not verificar_permiso(user, "Gestión de Activos de Información")
    ):
        flash("No tiene permiso para eliminar activos.", "danger")
        return redirect(url_for('inventario_fisico_menu'))

    it = InventarioFisico.query.get_or_404(id)
    db.session.delete(it)
    db.session.commit()
    flash("Eliminado.", "success")
    return redirect(url_for('inventario_fisico'))

# ====================================
# Inventario de Datos Personales
# ====================================

class InventarioDatosPersonales(db.Model):
    __tablename__ = "inventario_datos_personales"

    id = db.Column(db.Integer, primary_key=True)

    responsable_datos = db.Column(db.String(255), nullable=False)

    area_id = db.Column(db.Integer, nullable=True)
    division_id = db.Column(db.Integer, nullable=True)

    naturaleza_datos = db.Column(db.Text, nullable=False)
    ubicacion_sistema_datos = db.Column(db.String(255), nullable=False)
    titular_datos = db.Column(db.String(200), nullable=False)
    sitio_web_asociado = db.Column(db.Text)

    fuente_datos = db.Column(db.String(255), nullable=False)
    administrador_sistema = db.Column(db.String(255), nullable=False)
    alcance_datos = db.Column(db.Text)
    formato_informacion = db.Column(db.String(150))
    proposito_uso_datos = db.Column(db.Text, nullable=False)

    pais_almacenamiento = db.Column(db.String(120), nullable=False)
    pais_acceso = db.Column(db.String(120), nullable=False)

    transferencia_fuera_compania = db.Column(db.String(2), default="No")
    politica_retencion = db.Column(db.String(255))
    politica_privacidad = db.Column(db.Text)
    solicita_consentimiento = db.Column(db.String(2), default="No")

    notas = db.Column(db.Text)
    recomendacion = db.Column(db.Text)
    seguridad_quien_tiene_acceso = db.Column(db.String(255), nullable=False)
    consentimiento_titular_disponible = db.Column(db.String(2), default="No")

    dato_nombre = db.Column(db.String(2), default="No")
    dato_telefono = db.Column(db.String(2), default="No")
    dato_direccion = db.Column(db.String(2), default="No")
    dato_numero_identificacion = db.Column(db.String(2), default="No")
    dato_fecha_nacimiento = db.Column(db.String(2), default="No")
    dato_licencia_conduccion = db.Column(db.String(2), default="No")
    dato_pasaporte_visa = db.Column(db.String(2), default="No")
    dato_sensible = db.Column(db.String(2), default="No")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<InventarioDatosPersonales {self.id} - {self.responsable_datos}>"

# =========================
# ENTRADA DIRECTA — Inventario de Datos Personales
# =========================
@app.route('/inventario_datos_personales_menu')
@login_required
def inventario_datos_personales_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Gestión de Activos de Información"):
        flash("No tiene permiso para acceder al módulo de inventario de datos personales.", "danger")
        return redirect(url_for('activos_menu'))

    return redirect(url_for('inventario_datos_personales'))


# =========================
# Agregar — Inventario de Datos Personales
# =========================
@app.route('/inventario_datos_personales/new', methods=['GET', 'POST'])
@login_required
def inventario_datos_personales_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('inventario_datos_personales'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Activos de Información"):
        flash("No tiene permiso para agregar registros de datos personales.", "danger")
        return redirect(url_for('inventario_datos_personales'))

    paises = sorted([c.name for c in pycountry.countries])
    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()

    if request.method == 'POST':
        area_id = request.form.get('area_id', type=int)
        division_id = request.form.get('division_id', type=int)

        naturaleza_datos = (request.form.get('naturaleza_datos') or "").strip()
        ubicacion_sistema_datos = (request.form.get('ubicacion_sistema_datos') or "").strip()
        titular_datos = (request.form.get('titular_datos') or "").strip()
        sitio_web_asociado = (request.form.get('sitio_web_asociado') or "").strip()

        fuente_datos = (request.form.get('fuente_datos') or "").strip()
        administrador_sistema = (request.form.get('administrador_sistema') or "").strip()
        alcance_datos = (request.form.get('alcance_datos') or "").strip()
        formato_informacion = (request.form.get('formato_informacion') or "").strip()
        proposito_uso_datos = (request.form.get('proposito_uso_datos') or "").strip()

        pais_almacenamiento = (request.form.get('pais_almacenamiento') or "").strip()
        pais_acceso = (request.form.get('pais_acceso') or "").strip()
        transferencia_fuera_compania = request.form.get('transferencia_fuera_compania') or "No"
        politica_retencion = (request.form.get('politica_retencion') or "").strip()
        politica_privacidad = (request.form.get('politica_privacidad') or "").strip()
        solicita_consentimiento = request.form.get('solicita_consentimiento') or "No"

        notas = (request.form.get('notas') or "").strip()
        recomendacion = (request.form.get('recomendacion') or "").strip()
        seguridad_quien_tiene_acceso = (request.form.get('seguridad_quien_tiene_acceso') or "").strip()
        consentimiento_titular_disponible = request.form.get('consentimiento_titular_disponible') or "No"

        dato_nombre = request.form.get('dato_nombre') or "No"
        dato_telefono = request.form.get('dato_telefono') or "No"
        dato_direccion = request.form.get('dato_direccion') or "No"
        dato_numero_identificacion = request.form.get('dato_numero_identificacion') or "No"
        dato_fecha_nacimiento = request.form.get('dato_fecha_nacimiento') or "No"
        dato_licencia_conduccion = request.form.get('dato_licencia_conduccion') or "No"
        dato_pasaporte_visa = request.form.get('dato_pasaporte_visa') or "No"
        dato_sensible = request.form.get('dato_sensible') or "No"

        area = AreaEmpresa.query.get(area_id) if area_id else None
        division = DivisionEmpresa.query.get(division_id) if division_id else None

        responsable_datos = ""
        if area:
            responsable_datos = area.area
        if division:
            responsable_datos = f"{responsable_datos} / {division.nombre_division}"

        if not (
            area_id and naturaleza_datos and ubicacion_sistema_datos and
            titular_datos and fuente_datos and administrador_sistema and
            proposito_uso_datos and pais_almacenamiento and pais_acceso and
            seguridad_quien_tiene_acceso
        ):
            flash("Complete los campos obligatorios del inventario de datos personales.", "danger")
            return redirect(url_for('inventario_datos_personales_new'))

        item = InventarioDatosPersonales(
            responsable_datos=responsable_datos,
            area_id=area_id,
            division_id=division_id,
            naturaleza_datos=naturaleza_datos,
            ubicacion_sistema_datos=ubicacion_sistema_datos,
            titular_datos=titular_datos,
            sitio_web_asociado=sitio_web_asociado,
            fuente_datos=fuente_datos,
            administrador_sistema=administrador_sistema,
            alcance_datos=alcance_datos,
            formato_informacion=formato_informacion,
            proposito_uso_datos=proposito_uso_datos,
            pais_almacenamiento=pais_almacenamiento,
            pais_acceso=pais_acceso,
            transferencia_fuera_compania=transferencia_fuera_compania,
            politica_retencion=politica_retencion,
            politica_privacidad=politica_privacidad,
            solicita_consentimiento=solicita_consentimiento,
            notas=notas,
            recomendacion=recomendacion,
            seguridad_quien_tiene_acceso=seguridad_quien_tiene_acceso,
            consentimiento_titular_disponible=consentimiento_titular_disponible,
            dato_nombre=dato_nombre,
            dato_telefono=dato_telefono,
            dato_direccion=dato_direccion,
            dato_numero_identificacion=dato_numero_identificacion,
            dato_fecha_nacimiento=dato_fecha_nacimiento,
            dato_licencia_conduccion=dato_licencia_conduccion,
            dato_pasaporte_visa=dato_pasaporte_visa,
            dato_sensible=dato_sensible
        )
        db.session.add(item)
        db.session.commit()

        flash("Registro de inventario de datos personales creado.", "success")
        return redirect(url_for('inventario_datos_personales'))

    html = """
    <div class="invdp-shell">

      <div class="invdp-header-card">
        <div class="invdp-header-overlay">
          <div class="invdp-header-text">
            <h3 class="invdp-title m-0">Registro — Inventario de Datos Personales</h3>
            <div class="invdp-subtitle">
              Registro de sistemas, tratamientos, acceso, transferencia y elementos de datos personales
            </div>
          </div>
        </div>
      </div>

      <div class="invdp-header-actions">
        <a href="{{ url_for('inventario_datos_personales') }}"
           class="btn rounded-pill px-4 fw-bold invdp-back-btn">
          ⬅ Volver a la Matriz
        </a>

        
      </div>

      <div class="invdp-card">
        <div class="invdp-card-body">
          <form method="post">
            <div class="row g-3">

              <div class="col-md-8">
                <label class="form-label">Responsable de los datos</label>

                <div class="row g-2">
                  <div class="col-md-6">
                    <select name="area_id" id="area_id" class="form-select" required>
                      <option value="">-- Seleccione Área --</option>
                      {% for a in areas %}
                        <option value="{{ a.id }}">{{ a.area }}</option>
                      {% endfor %}
                    </select>
                  </div>

                  <div class="col-md-6">
                    <select name="division_id" id="division_id" class="form-select">
                      <option value="">Todas las divisiones</option>
                    </select>
                  </div>
                </div>

                <small class="text-muted">Seleccione el área y, si aplica, la división responsable de los datos.</small>
              </div>

              <div class="col-md-4">
                <label class="form-label">Titular de los datos</label>
                <input type="text" name="titular_datos" class="form-control" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Ubicación del sistema de datos</label>
                <input type="text" name="ubicacion_sistema_datos" class="form-control" placeholder="Ej. SAP, CRM, ERP" required>
              </div>

              <div class="col-md-6">
                <label class="form-label">Naturaleza de los datos</label>
                <textarea name="naturaleza_datos" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Sitio web asociado</label>
                <textarea name="sitio_web_asociado" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Fuente de los datos</label>
                <input type="text" name="fuente_datos" class="form-control" required>
              </div>

              <div class="col-md-6">
                <label class="form-label">Administrador del sistema</label>
                <input type="text" name="administrador_sistema" class="form-control" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Formato de la información</label>
                <select name="formato_informacion" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Digital">Digital</option>
                  <option value="Físico">Físico</option>
                  <option value="Mixto">Mixto</option>
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Alcance de los datos</label>
                <textarea name="alcance_datos" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Propósito y uso de los datos</label>
                <textarea name="proposito_uso_datos" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">¿Dónde se almacenan los datos?</label>
                <select name="pais_almacenamiento" class="form-select" required>
                  <option value="">-- Seleccione país --</option>
                  {% for p in paises %}
                    <option value="{{ p }}">{{ p }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">¿Dónde se accede a los datos?</label>
                <select name="pais_acceso" class="form-select" required>
                  <option value="">-- Seleccione país --</option>
                  {% for p in paises %}
                    <option value="{{ p }}">{{ p }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Transferencia de datos fuera de la compañía</label>
                <select name="transferencia_fuera_compania" class="form-select">
                  <option value="No">No</option>
                  <option value="Sí">Sí</option>
                </select>
              </div>

              <div class="col-md-6">
                <label class="form-label">Política de retención</label>
                <input type="text" name="politica_retencion" class="form-control" placeholder="Ubicación de la política y años de retención">
              </div>

              <div class="col-md-6">
                <label class="form-label">¿Política de privacidad?</label>
                <textarea name="politica_privacidad" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">¿Se solicita consentimiento?</label>
                <select name="solicita_consentimiento" class="form-select">
                  <option value="No">No</option>
                  <option value="Sí">Sí</option>
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Seguridad — ¿Quién tiene acceso?</label>
                <input type="text" name="seguridad_quien_tiene_acceso" class="form-control" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">¿Existe consentimiento disponible del titular?</label>
                <select name="consentimiento_titular_disponible" class="form-select">
                  <option value="No">No</option>
                  <option value="Sí">Sí</option>
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Notas</label>
                <textarea name="notas" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Recomendación</label>
                <textarea name="recomendacion" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-12 mt-4">
                <div class="invdp-section-title">Elementos de datos</div>
              </div>

              {% set yn_fields = [
                ('dato_nombre', 'Nombre'),
                ('dato_telefono', 'Teléfono'),
                ('dato_direccion', 'Dirección'),
                ('dato_numero_identificacion', 'Número del Documento de Identificación'),
                ('dato_fecha_nacimiento', 'Fecha de nacimiento'),
                ('dato_licencia_conduccion', 'Número de licencia de conducción'),
                ('dato_pasaporte_visa', 'Información de pasaporte / visa'),
                ('dato_sensible', 'Datos sensibles')
              ] %}

              {% for field, label in yn_fields %}
              <div class="col-md-3">
                <label class="form-label">{{ label }}</label>
                <select name="{{ field }}" class="form-select">
                  <option value="No">No</option>
                  <option value="Sí">Sí</option>
                </select>
              </div>
              {% endfor %}

            </div>

            <div class="invdp-bottom-actions">
              <button type="submit" class="btn btn-success rounded-pill px-4 fw-bold">
                Guardar registro
              </button>

              <a href="{{ url_for('inventario_datos_personales') }}"
                 class="btn rounded-pill px-4 fw-bold invdp-cancel-btn">
                Cancelar
              </a>
            </div>
          </form>
        </div>
      </div>
    </div>

    <script>
    document.addEventListener('DOMContentLoaded', function () {
      const areaSel = document.getElementById('area_id');
      const divSel = document.getElementById('division_id');

      if (!areaSel || !divSel) return;

      areaSel.addEventListener('change', async function () {
        const areaId = this.value;
        divSel.innerHTML = '<option value="">Todas las divisiones</option>';

        if (!areaId) return;

        try {
          const resp = await fetch(`/areas/${areaId}/divisiones_json`);
          const data = await resp.json();

          (data.divisiones || []).forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.id;
            opt.textContent = d.nombre;
            divSel.appendChild(opt);
          });
        } catch (e) {
          console.error('Error cargando divisiones:', e);
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

      .invdp-shell{
        width:96%;
        max-width:1400px;
        margin:10px auto 24px auto;
      }

      .invdp-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .invdp-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .invdp-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent;
        padding:0;
        position:relative;
        z-index:1;
      }

      .invdp-header-overlay::before{
        content:"🗂️";
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

      .invdp-header-text{
        max-width:1100px;
        width:100%;
      }

      .invdp-header-text::before{
        content:"SGSI · Inventario de Datos Personales";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .invdp-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .invdp-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .invdp-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .invdp-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invdp-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invdp-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .invdp-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .invdp-card-body{
        padding:18px;
      }

      .invdp-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .invdp-card .form-control,
      .invdp-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .invdp-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .invdp-card .form-control:focus,
      .invdp-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }

      .invdp-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 10px;
      }

      .invdp-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .invdp-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invdp-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invdp-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .invdp-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .invdp-header-card{
          min-height:88px;
        }

        .invdp-title{
          font-size:1.20rem;
        }

        .invdp-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .invdp-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .invdp-header-overlay::before{
          margin:0;
        }

        .invdp-header-actions .btn,
        .invdp-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(html, paises=paises, areas=areas))
    )


# =========================
# Matriz — Inventario de Datos Personales
# =========================
@app.route('/inventario_datos_personales', methods=['GET'])
@login_required
def inventario_datos_personales():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso_activos(user, "Inventario de Datos Personales"):
        flash("No tiene permiso para ver la matriz de datos personales.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == 'auditor')

    items = InventarioDatosPersonales.query.order_by(InventarioDatosPersonales.id.desc()).all()

    html = render_template_string("""
    <div class="invdpm-shell">

      <div class="invdpm-header-card">
        <div class="invdpm-header-overlay">
          <div class="invdpm-header-text">
            <h3 class="invdpm-title m-0">Matriz — Inventario de Datos Personales</h3>
            <div class="invdpm-subtitle">
              Visualización resumida de registros del inventario de datos personales
            </div>
          </div>
        </div>
      </div>

      <div class="invdpm-header-actions">

        {% if not read_only %}
          <a href="{{ url_for('inventario_datos_personales_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            ➕ Agregar Registro
          </a>
        {% else %}
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            ➕ Agregar Registro
          </button>
        {% endif %}
      </div>

      <div class="invdpm-card">
        <div class="invdpm-topbar">
          <div>
            <h5 class="invdpm-top-title mb-1">Resumen de activos de información</h5>
            <div class="invdpm-top-note">
              La matriz muestra únicamente los campos esenciales. Para consultar toda la información utilice el botón <strong>Ver detalle</strong>.
            </div>
          </div>

          <div class="invdpm-counter-badge">
            Total registros: {{ items|length }}
          </div>
        </div>

        <div class="invdpm-card-body">
          <div class="invdpm-table-wrap">
            <div class="table-responsive">
              <table class="table align-middle mb-0 invdpm-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Responsable</th>
                    <th>Naturaleza de los datos</th>
                    <th>Titular</th>
                    <th>Sistema</th>
                    <th>Almacenamiento</th>
                    <th>Acceso</th>
                    <th class="text-center invdpm-col-acciones">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {% for it in items %}
                  <tr>
                    <td>{{ it.id }}</td>
                    <td>{{ it.responsable_datos }}</td>
                    <td>{{ it.naturaleza_datos }}</td>
                    <td>{{ it.titular_datos }}</td>
                    <td>{{ it.ubicacion_sistema_datos }}</td>
                    <td>{{ it.pais_almacenamiento }}</td>
                    <td>{{ it.pais_acceso }}</td>
                    <td class="text-center invdpm-col-acciones">
                      <div class="invdpm-actions-wrap">
                        <a href="{{ url_for('inventario_datos_personales_detalle', id=it.id) }}"
                           class="btn btn-info btn-sm text-white rounded-pill invdpm-btn-action">
                          Ver detalle
                        </a>

                        {% if not read_only %}
                          <a href="{{ url_for('inventario_datos_personales_edit', id=it.id) }}"
                             class="btn btn-primary btn-sm rounded-pill invdpm-btn-action">
                            Editar
                          </a>

                          <a href="{{ url_for('inventario_datos_personales_delete', id=it.id) }}"
                             class="btn btn-danger btn-sm rounded-pill invdpm-btn-action"
                             onclick="return confirm('¿Eliminar este registro de inventario de datos personales?');">
                            Eliminar
                          </a>
                        {% else %}
                          <span class="badge bg-secondary">Solo lectura</span>
                        {% endif %}
                      </div>
                    </td>
                  </tr>
                  {% else %}
                  <tr>
                    <td colspan="8" class="text-center py-4 text-muted">
                      No hay registros creados.
                    </td>
                  </tr>
                  {% endfor %}
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

      .invdpm-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      .invdpm-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .invdpm-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .invdpm-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent;
        padding:0;
        position:relative;
        z-index:1;
      }

      .invdpm-header-overlay::before{
        content:"🗂️";
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

      .invdpm-header-text{
        max-width:1100px;
        width:100%;
      }

      .invdpm-header-text::before{
        content:"SGSI · Matriz de Datos Personales";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .invdpm-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .invdpm-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .invdpm-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .invdpm-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invdpm-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invdpm-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .invdpm-card{
        background:rgba(255,255,255,.96);
        border:none;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .invdpm-topbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:14px 16px 0 16px;
        flex-wrap:wrap;
      }

      .invdpm-top-title{
        color:#0f172a;
        font-weight:950;
        font-size:.92rem;
      }

      .invdpm-top-note{
        color:#475569;
        font-size:.78rem;
      }

      .invdpm-counter-badge{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:7px 14px;
        font-size:.78rem;
        box-shadow:0 8px 16px rgba(15,23,42,.16);
      }

      .invdpm-card-body{
        padding:12px 16px 16px 16px;
      }

      .invdpm-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#fff;
      }

      .invdpm-table{
        min-width:1300px;
        table-layout:fixed;
        margin-bottom:0;
      }

      .invdpm-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        white-space:nowrap;
      }

      .invdpm-table td,
      .invdpm-table th{
        vertical-align:middle;
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .invdpm-table td{
        border-bottom:1px solid #e5edf7;
      }

      .invdpm-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .invdpm-table tbody tr:hover{
        background:#eef6ff;
      }

      .invdpm-col-acciones{
        min-width:180px;
        width:180px;
      }

      .invdpm-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .invdpm-btn-action{
        min-width:105px;
        max-width:120px;
        font-size:.64rem !important;
        padding:4px 12px !important;
        line-height:1.2;
        text-align:center;
        white-space:nowrap;
        border-radius:999px !important;
        font-weight:900;
      }

      @media (max-width:992px){
        .invdpm-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .invdpm-header-card{
          min-height:88px;
        }

        .invdpm-title{
          font-size:1.20rem;
        }

        .invdpm-card-body{
          padding:12px;
        }

        .invdpm-topbar{
          padding:12px 14px 0 14px;
        }
      }

      @media (max-width:768px){
        .invdpm-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .invdpm-header-overlay::before{
          margin:0;
        }

        .invdpm-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, items=items, read_only=read_only)

    return render_template_string(BASE, content=Markup(html))

# =========================
# Detalle — Inventario de Datos Personales
# =========================
@app.route('/inventario_datos_personales/detalle/<int:id>', methods=['GET'])
@login_required
def inventario_datos_personales_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Gestión de Activos de Información"):
        flash("No tiene permiso para ver el detalle de datos personales.", "danger")
        return redirect(url_for('inventario_datos_personales'))

    read_only = (user.role == 'auditor')
    item = InventarioDatosPersonales.query.get_or_404(id)

    html = render_template_string("""
    <div class="invdpd-shell">

      <div class="invdpd-header-card">
        <div class="invdpd-header-overlay">
          <div class="invdpd-header-text">
            <h3 class="invdpd-title m-0">Detalle — Inventario de Datos Personales</h3>
            <div class="invdpd-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="invdpd-header-actions">
        <a href="{{ url_for('inventario_datos_personales') }}"
           class="btn rounded-pill px-4 fw-bold invdpd-back-btn">
          ⬅ Volver a la Matriz
        </a>


        {% if not read_only %}
          <a href="{{ url_for('inventario_datos_personales_edit', id=item.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar
          </a>
        {% endif %}
      </div>

      <div class="row g-3">
        <div class="col-lg-6">
          <div class="invdpd-card h-100">
            <div class="invdpd-card-title">Información general</div>
            <div class="invdpd-body">
              <div><strong>Responsable de los datos:</strong> {{ item.responsable_datos or '-' }}</div>
              <div><strong>Naturaleza de los datos:</strong> {{ item.naturaleza_datos }}</div>
              <div><strong>Ubicación del sistema de datos:</strong> {{ item.ubicacion_sistema_datos }}</div>
              <div><strong>Titular de los datos:</strong> {{ item.titular_datos }}</div>
              <div><strong>Sitio web asociado:</strong> {{ item.sitio_web_asociado or '-' }}</div>
              <div><strong>Fuente de los datos:</strong> {{ item.fuente_datos }}</div>
              <div><strong>Administrador del sistema:</strong> {{ item.administrador_sistema }}</div>
              <div><strong>Alcance de los datos:</strong> {{ item.alcance_datos or '-' }}</div>
              <div><strong>Formato de la información:</strong> {{ item.formato_informacion or '-' }}</div>
              <div><strong>Propósito y uso de los datos:</strong> {{ item.proposito_uso_datos }}</div>
            </div>
          </div>
        </div>

        <div class="col-lg-6">
          <div class="invdpd-card h-100">
            <div class="invdpd-card-title">Privacidad y tratamiento</div>
            <div class="invdpd-body">
              <div><strong>País de almacenamiento:</strong> {{ item.pais_almacenamiento }}</div>
              <div><strong>País de acceso:</strong> {{ item.pais_acceso }}</div>
              <div><strong>Transferencia fuera de la compañía:</strong> {{ item.transferencia_fuera_compania }}</div>
              <div><strong>Política de retención:</strong> {{ item.politica_retencion or '-' }}</div>
              <div><strong>Política de privacidad:</strong> {{ item.politica_privacidad or '-' }}</div>
              <div><strong>¿Se solicita consentimiento?:</strong> {{ item.solicita_consentimiento }}</div>
              <div><strong>Seguridad — ¿Quién tiene acceso?:</strong> {{ item.seguridad_quien_tiene_acceso }}</div>
              <div><strong>Consentimiento disponible del titular:</strong> {{ item.consentimiento_titular_disponible }}</div>
              <div><strong>Notas:</strong> {{ item.notas or '-' }}</div>
              <div><strong>Recomendación:</strong> {{ item.recomendacion or '-' }}</div>
            </div>
          </div>
        </div>

        <div class="col-12">
          <div class="invdpd-card">
            <div class="invdpd-card-title">Elementos de datos</div>
            <div class="invdpd-body">
              <div class="row g-3">
                <div class="col-md-3"><strong>Nombre:</strong> {{ item.dato_nombre }}</div>
                <div class="col-md-3"><strong>Teléfono:</strong> {{ item.dato_telefono }}</div>
                <div class="col-md-3"><strong>Dirección:</strong> {{ item.dato_direccion }}</div>
                <div class="col-md-3"><strong>Número identificación:</strong> {{ item.dato_numero_identificacion }}</div>
                <div class="col-md-3"><strong>Fecha de nacimiento:</strong> {{ item.dato_fecha_nacimiento }}</div>
                <div class="col-md-3"><strong>Licencia de conducción:</strong> {{ item.dato_licencia_conduccion }}</div>
                <div class="col-md-3"><strong>Pasaporte / visa:</strong> {{ item.dato_pasaporte_visa }}</div>
                <div class="col-md-3"><strong>Dato sensible:</strong> {{ item.dato_sensible }}</div>
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

      .invdpd-shell{
        width:96%;
        max-width:1400px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HEADER SGSI MODERNO
      ========================= */
      .invdpd-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .invdpd-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .invdpd-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .invdpd-header-overlay::before{
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
        font-size:1.4rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .invdpd-header-text{
        max-width:1100px;
        width:100%;
      }

      .invdpd-header-text::before{
        content:"SGSI · Detalle de Datos Personales";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .invdpd-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .invdpd-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES
      ========================= */
      .invdpd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .invdpd-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invdpd-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invdpd-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD DETALLE
      ========================= */
      .invdpd-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .invdpd-card-title{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1);
        color:#ffffff;
        font-weight:900;
        font-size:.90rem;
        padding:12px 16px;
        letter-spacing:.3px;
      }

      .invdpd-body{
        padding:18px;
        color:#334155;
        font-size:.85rem;
        line-height:1.5;
      }

      .invdpd-body > div{
        margin-bottom:10px;
        padding:10px 12px;
        background:#f8fbff;
        border-radius:10px;
        border:1px solid #e3edf7;
      }

      /* =========================
         RESPONSIVE
      ========================= */
      @media (max-width:992px){
        .invdpd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .invdpd-header-card{
          min-height:88px;
        }

        .invdpd-title{
          font-size:1.20rem;
        }

        .invdpd-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .invdpd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .invdpd-header-overlay::before{
          margin:0;
        }

        .invdpd-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, item=item, read_only=read_only)

    return render_template_string(BASE, content=Markup(html))


# =========================
# Editar — Inventario de Datos Personales
# =========================
@app.route('/inventario_datos_personales/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def inventario_datos_personales_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede editar registros.", "danger")
        return redirect(url_for('inventario_datos_personales'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Activos de Información"):
        flash("No tiene permiso para editar registros de datos personales.", "danger")
        return redirect(url_for('inventario_datos_personales'))

    item = InventarioDatosPersonales.query.get_or_404(id)
    paises = sorted([c.name for c in pycountry.countries])

    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()

    divisiones = []
    if item.area_id:
        divisiones = (
            DivisionEmpresa.query
            .filter_by(area_id=item.area_id)
            .order_by(DivisionEmpresa.nombre_division.asc())
            .all()
        )

    if request.method == 'POST':
        item.area_id = request.form.get('area_id', type=int)
        item.division_id = request.form.get('division_id', type=int)

        item.naturaleza_datos = (request.form.get('naturaleza_datos') or "").strip()
        item.ubicacion_sistema_datos = (request.form.get('ubicacion_sistema_datos') or "").strip()
        item.titular_datos = (request.form.get('titular_datos') or "").strip()
        item.sitio_web_asociado = (request.form.get('sitio_web_asociado') or "").strip()

        item.fuente_datos = (request.form.get('fuente_datos') or "").strip()
        item.administrador_sistema = (request.form.get('administrador_sistema') or "").strip()
        item.alcance_datos = (request.form.get('alcance_datos') or "").strip()
        item.formato_informacion = (request.form.get('formato_informacion') or "").strip()
        item.proposito_uso_datos = (request.form.get('proposito_uso_datos') or "").strip()

        item.pais_almacenamiento = (request.form.get('pais_almacenamiento') or "").strip()
        item.pais_acceso = (request.form.get('pais_acceso') or "").strip()
        item.transferencia_fuera_compania = request.form.get('transferencia_fuera_compania') or "No"
        item.politica_retencion = (request.form.get('politica_retencion') or "").strip()
        item.politica_privacidad = (request.form.get('politica_privacidad') or "").strip()
        item.solicita_consentimiento = request.form.get('solicita_consentimiento') or "No"

        item.notas = (request.form.get('notas') or "").strip()
        item.recomendacion = (request.form.get('recomendacion') or "").strip()
        item.seguridad_quien_tiene_acceso = (request.form.get('seguridad_quien_tiene_acceso') or "").strip()
        item.consentimiento_titular_disponible = request.form.get('consentimiento_titular_disponible') or "No"

        item.dato_nombre = request.form.get('dato_nombre') or "No"
        item.dato_telefono = request.form.get('dato_telefono') or "No"
        item.dato_direccion = request.form.get('dato_direccion') or "No"
        item.dato_numero_identificacion = request.form.get('dato_numero_identificacion') or "No"
        item.dato_fecha_nacimiento = request.form.get('dato_fecha_nacimiento') or "No"
        item.dato_licencia_conduccion = request.form.get('dato_licencia_conduccion') or "No"
        item.dato_pasaporte_visa = request.form.get('dato_pasaporte_visa') or "No"
        item.dato_sensible = request.form.get('dato_sensible') or "No"

        area = AreaEmpresa.query.get(item.area_id) if item.area_id else None
        division = DivisionEmpresa.query.get(item.division_id) if item.division_id else None

        item.responsable_datos = ""
        if area:
            item.responsable_datos = area.area
        if division:
            item.responsable_datos = f"{item.responsable_datos} / {division.nombre_division}"

        if not (
            item.area_id and item.naturaleza_datos and item.ubicacion_sistema_datos and
            item.titular_datos and item.fuente_datos and item.administrador_sistema and
            item.proposito_uso_datos and item.pais_almacenamiento and item.pais_acceso and
            item.seguridad_quien_tiene_acceso
        ):
            flash("Complete los campos obligatorios del inventario de datos personales.", "danger")
            return redirect(url_for('inventario_datos_personales_edit', id=item.id))

        db.session.commit()
        flash("Registro de inventario de datos personales actualizado.", "success")
        return redirect(url_for('inventario_datos_personales_detalle', id=item.id))

    html = """
    <div class="invdpe-shell">

      <div class="invdpe-header-card">
        <div class="invdpe-header-overlay">
          <div class="invdpe-header-text">
            <h3 class="invdpe-title m-0">Editar — Inventario de Datos Personales</h3>
            <div class="invdpe-subtitle">
              Modificación del registro #{{ item.id }}
            </div>
          </div>
        </div>
      </div>

      <div class="invdpe-header-actions">
        <a href="{{ url_for('inventario_datos_personales') }}"
           class="btn rounded-pill px-4 fw-bold invdpe-back-btn">
          ⬅ Volver a la Matriz
        </a>

        <a href="{{ url_for('inventario_datos_personales_detalle', id=item.id) }}"
           class="btn rounded-pill px-4 fw-bold invdpe-back-btn">
          🔎 Volver al Detalle
        </a>

      </div>

      <div class="invdpe-card">
        <div class="invdpe-card-body">
          <form method="post">
            <div class="row g-3">

              <div class="col-md-8">
                <label class="form-label">Responsable de los datos</label>

                <div class="row g-2">
                  <div class="col-md-6">
                    <select name="area_id" id="area_id" class="form-select" required>
                      <option value="">-- Seleccione Área --</option>
                      {% for a in areas %}
                        <option value="{{ a.id }}" {% if item.area_id == a.id %}selected{% endif %}>
                          {{ a.area }}
                        </option>
                      {% endfor %}
                    </select>
                  </div>

                  <div class="col-md-6">
                    <select name="division_id" id="division_id" class="form-select">
                      <option value="" {% if not item.division_id %}selected{% endif %}>Todas las divisiones</option>
                      {% for d in divisiones %}
                        <option value="{{ d.id }}" {% if item.division_id == d.id %}selected{% endif %}>
                          {{ d.nombre_division }}
                        </option>
                      {% endfor %}
                    </select>
                  </div>
                </div>

                <small class="text-muted">Seleccione el área y, si aplica, la división responsable de los datos.</small>
              </div>

              <div class="col-md-4">
                <label class="form-label">Titular de los datos</label>
                <input type="text" name="titular_datos" class="form-control" value="{{ item.titular_datos or '' }}" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Ubicación del sistema de datos</label>
                <input type="text" name="ubicacion_sistema_datos" class="form-control" value="{{ item.ubicacion_sistema_datos or '' }}" placeholder="Ej. SAP, CRM, ERP" required>
              </div>

              <div class="col-md-6">
                <label class="form-label">Naturaleza de los datos</label>
                <textarea name="naturaleza_datos" class="form-control" rows="2" required>{{ item.naturaleza_datos or '' }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Sitio web asociado</label>
                <textarea name="sitio_web_asociado" class="form-control" rows="2">{{ item.sitio_web_asociado or '' }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Fuente de los datos</label>
                <input type="text" name="fuente_datos" class="form-control" value="{{ item.fuente_datos or '' }}" required>
              </div>

              <div class="col-md-6">
                <label class="form-label">Administrador del sistema</label>
                <input type="text" name="administrador_sistema" class="form-control" value="{{ item.administrador_sistema or '' }}" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Formato de la información</label>
                <select name="formato_informacion" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Digital" {% if item.formato_informacion == 'Digital' %}selected{% endif %}>Digital</option>
                  <option value="Físico" {% if item.formato_informacion == 'Físico' %}selected{% endif %}>Físico</option>
                  <option value="Mixto" {% if item.formato_informacion == 'Mixto' %}selected{% endif %}>Mixto</option>
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Alcance de los datos</label>
                <textarea name="alcance_datos" class="form-control" rows="2">{{ item.alcance_datos or '' }}</textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Propósito y uso de los datos</label>
                <textarea name="proposito_uso_datos" class="form-control" rows="2" required>{{ item.proposito_uso_datos or '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">¿Dónde se almacenan los datos?</label>
                <select name="pais_almacenamiento" class="form-select" required>
                  <option value="">-- Seleccione país --</option>
                  {% for p in paises %}
                    <option value="{{ p }}" {% if item.pais_almacenamiento == p %}selected{% endif %}>{{ p }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">¿Dónde se accede a los datos?</label>
                <select name="pais_acceso" class="form-select" required>
                  <option value="">-- Seleccione país --</option>
                  {% for p in paises %}
                    <option value="{{ p }}" {% if item.pais_acceso == p %}selected{% endif %}>{{ p }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Transferencia de datos fuera de la compañía</label>
                <select name="transferencia_fuera_compania" class="form-select">
                  <option value="No" {% if item.transferencia_fuera_compania == 'No' %}selected{% endif %}>No</option>
                  <option value="Sí" {% if item.transferencia_fuera_compania == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
              </div>

              <div class="col-md-6">
                <label class="form-label">Política de retención</label>
                <input type="text" name="politica_retencion" class="form-control" value="{{ item.politica_retencion or '' }}" placeholder="Ubicación de la política y años de retención">
              </div>

              <div class="col-md-6">
                <label class="form-label">¿Política de privacidad?</label>
                <textarea name="politica_privacidad" class="form-control" rows="2">{{ item.politica_privacidad or '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">¿Se solicita consentimiento?</label>
                <select name="solicita_consentimiento" class="form-select">
                  <option value="No" {% if item.solicita_consentimiento == 'No' %}selected{% endif %}>No</option>
                  <option value="Sí" {% if item.solicita_consentimiento == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Seguridad — ¿Quién tiene acceso?</label>
                <input type="text" name="seguridad_quien_tiene_acceso" class="form-control" value="{{ item.seguridad_quien_tiene_acceso or '' }}" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">¿Existe consentimiento disponible del titular?</label>
                <select name="consentimiento_titular_disponible" class="form-select">
                  <option value="No" {% if item.consentimiento_titular_disponible == 'No' %}selected{% endif %}>No</option>
                  <option value="Sí" {% if item.consentimiento_titular_disponible == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Notas</label>
                <textarea name="notas" class="form-control" rows="2">{{ item.notas or '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Recomendación</label>
                <textarea name="recomendacion" class="form-control" rows="2">{{ item.recomendacion or '' }}</textarea>
              </div>

              <div class="col-12 mt-4">
                <div class="invdpe-section-title">Elementos de datos</div>
              </div>

              {% set yn_fields = [
                ('dato_nombre', 'Nombre'),
                ('dato_telefono', 'Teléfono'),
                ('dato_direccion', 'Dirección'),
                ('dato_numero_identificacion', 'Número del Documento de Identificación'),
                ('dato_fecha_nacimiento', 'Fecha de nacimiento'),
                ('dato_licencia_conduccion', 'Número de licencia de conducción'),
                ('dato_pasaporte_visa', 'Información de pasaporte / visa'),
                ('dato_sensible', 'Datos sensibles')
              ] %}

              {% for field, label in yn_fields %}
              <div class="col-md-3">
                <label class="form-label">{{ label }}</label>
                <select name="{{ field }}" class="form-select">
                  <option value="No" {% if item[field] == 'No' %}selected{% endif %}>No</option>
                  <option value="Sí" {% if item[field] == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
              </div>
              {% endfor %}

            </div>

            <div class="invdpe-bottom-actions">
              <button type="submit" class="btn btn-success rounded-pill px-4 fw-bold">
                Guardar cambios
              </button>

              <a href="{{ url_for('inventario_datos_personales_detalle', id=item.id) }}"
                 class="btn rounded-pill px-4 fw-bold invdpe-cancel-btn">
                Cancelar
              </a>
            </div>
          </form>
        </div>
      </div>
    </div>

    <script>
    document.addEventListener('DOMContentLoaded', function () {
      const areaSel = document.getElementById('area_id');
      const divSel = document.getElementById('division_id');
      const divisionActual = "{{ item.division_id or '' }}";

      if (!areaSel || !divSel) return;

      areaSel.addEventListener('change', async function () {
        const areaId = this.value;
        divSel.innerHTML = '<option value="">Todas las divisiones</option>';

        if (!areaId) return;

        try {
          const resp = await fetch(`/areas/${areaId}/divisiones_json`);
          const data = await resp.json();

          (data.divisiones || []).forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.id;
            opt.textContent = d.nombre;
            if (String(d.id) === String(divisionActual)) {
              opt.selected = true;
            }
            divSel.appendChild(opt);
          });
        } catch (e) {
          console.error('Error cargando divisiones:', e);
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

      .invdpe-shell{
        width:96%;
        max-width:1400px;
        margin:10px auto 24px auto;
      }

      .invdpe-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .invdpe-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .invdpe-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent;
        padding:0;
        position:relative;
        z-index:1;
      }

      .invdpe-header-overlay::before{
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

      .invdpe-header-text{
        max-width:1100px;
        width:100%;
      }

      .invdpe-header-text::before{
        content:"SGSI · Edición Datos Personales";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .invdpe-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .invdpe-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .invdpe-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .invdpe-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invdpe-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invdpe-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .invdpe-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .invdpe-card-body{
        padding:18px;
      }

      .invdpe-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .invdpe-card .form-control,
      .invdpe-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .invdpe-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .invdpe-card .form-control:focus,
      .invdpe-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }

      .invdpe-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 10px;
      }

      .invdpe-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .invdpe-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .invdpe-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invdpe-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .invdpe-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .invdpe-header-card{
          min-height:88px;
        }

        .invdpe-title{
          font-size:1.20rem;
        }

        .invdpe-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .invdpe-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .invdpe-header-overlay::before{
          margin:0;
        }

        .invdpe-header-actions .btn,
        .invdpe-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            html,
            item=item,
            paises=paises,
            areas=areas,
            divisiones=divisiones
        ))
    )


# =========================
# Eliminar — Inventario de Datos Personales
# =========================
@app.route('/inventario_datos_personales/delete/<int:id>', methods=['GET'])
@login_required
def inventario_datos_personales_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros.", "danger")
        return redirect(url_for('inventario_datos_personales'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Activos de Información"):
        flash("No tiene permiso para eliminar registros de datos personales.", "danger")
        return redirect(url_for('inventario_datos_personales'))

    item = InventarioDatosPersonales.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()

    flash("Registro de inventario de datos personales eliminado.", "success")
    return redirect(url_for('inventario_datos_personales'))

# =========================
# Menú Activos Valoración (ESTILO UNIFICADO)
# =========================
@app.route('/activos_valoracion')
@login_required
def activos_valoracion():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and not verificar_permiso_activos(user, "Tablas de Valoración"):
        flash("No tiene permiso para acceder a Tablas de Valoración.", "danger")
        return redirect(url_for('menu'))
    
    html = render_template_string("""
    <div class="menu-wrap">

      <!-- ===== HEADER (BANNER) ===== -->
      <div class="plan-hero">
        <h2 class="plan-title">📊 Tablas de Valoración de Activos</h2>
      </div>

      <!-- ===== BOTÓN VOLVER (CENTRADO, FUERA DEL BANNER) ===== -->
      <div class="volver-center">
        <a href="{{ url_for('activos_menu') }}"
           class="btn btn-light rounded-pill px-4 fw-semibold"
           onclick="showLoader()">
          ⬅ Volver al Menú Gestión de Activos
        </a>
      </div>

      <!-- ===== TARJETAS COMPACTAS ===== -->
      <div class="row justify-content-center g-3 mt-2">

        <!-- Confidencialidad -->
        <div class="col-xl-3 col-lg-4 col-md-6 col-sm-12">
          <div class="card plan-tile h-100">
            <div class="card-body text-center d-flex flex-column justify-content-between">
              <div>
                <div class="plan-card-title">🔐 Confidencialidad</div>
                <p class="plan-card-sub mb-0">Valoración del nivel de confidencialidad.</p>
              </div>
              <a href="{{ url_for('valor_confidencialidad') }}"
                 class="btn btn-primary rounded-pill px-4 mt-2"
                 onclick="showLoader()">
                Entrar
              </a>
            </div>
          </div>
        </div>

        <!-- Integridad -->
        <div class="col-xl-3 col-lg-4 col-md-6 col-sm-12">
          <div class="card plan-tile h-100">
            <div class="card-body text-center d-flex flex-column justify-content-between">
              <div>
                <div class="plan-card-title">🧩 Integridad</div>
                <p class="plan-card-sub mb-0">Valoración del nivel de integridad.</p>
              </div>
              <a href="{{ url_for('valor_integridad') }}"
                 class="btn btn-primary rounded-pill px-4 mt-2"
                 onclick="showLoader()">
                Entrar
              </a>
            </div>
          </div>
        </div>

        <!-- Disponibilidad -->
        <div class="col-xl-3 col-lg-4 col-md-6 col-sm-12">
          <div class="card plan-tile h-100">
            <div class="card-body text-center d-flex flex-column justify-content-between">
              <div>
                <div class="plan-card-title">🕒 Disponibilidad</div>
                <p class="plan-card-sub mb-0">Valoración del nivel de disponibilidad.</p>
              </div>
              <a href="{{ url_for('valor_disponibilidad') }}"
                 class="btn btn-primary rounded-pill px-4 mt-2"
                 onclick="showLoader()">
                Entrar
              </a>
            </div>
          </div>
        </div>

        <!-- Criticidad -->
        <div class="col-xl-3 col-lg-4 col-md-6 col-sm-12">
          <div class="card plan-tile h-100">
            <div class="card-body text-center d-flex flex-column justify-content-between">
              <div>
                <div class="plan-card-title">🔥 Criticidad del Activo</div>
                <p class="plan-card-sub mb-0">Evaluación del nivel de criticidad.</p>
              </div>
              <a href="{{ url_for('valor_criticidad_activo') }}"
                 class="btn btn-primary rounded-pill px-4 mt-2"
                 onclick="showLoader()">
                Entrar
              </a>
            </div>
          </div>
        </div>

      </div>
    </div>

    <style>
      /* =========================
         FONDO UNIFICADO
      ========================= */
      body{
        background:#b0b6bf !important;
        background-image:none !important;
      }

      .menu-wrap{
        max-width:1100px;
        margin:22px auto 30px;
      }

      /* =========================
         HEADER (BANNER)
      ========================= */
      .plan-hero{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        height:130px;
        display:flex;
        align-items:center;
        justify-content:center;
        border-radius:18px;
        box-shadow:0 12px 30px rgba(0,0,0,.30);
      }

      .plan-title{
        color:white;
        font-weight:900;
        font-size:1.8rem; /* MISMA LETRA */
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        margin:0;
        text-align:center;
        padding:0 14px;
      }

      /* =========================
         BOTÓN VOLVER (centrado arriba)
      ========================= */
      .volver-center{
        display:flex;
        justify-content:center;
        margin-top:14px;
        margin-bottom:6px;
      }

      /* =========================
         TARJETAS COMPACTAS
      ========================= */
      .plan-tile{
        border:none;
        border-radius:18px;
        background:rgba(255,255,255,.90) !important;
        backdrop-filter:blur(6px);
        box-shadow:0 8px 18px rgba(0,0,0,.18);
        transition:all .22s ease;
        min-height:145px;
        padding:6px;
      }

      .plan-tile:hover{
        transform:translateY(-5px) scale(1.01);
        box-shadow:0 16px 30px rgba(0,0,0,.26);
      }

      .plan-card-title{
        font-size:1.15rem; /* MISMA LETRA */
        font-weight:900;
        color:#101827;
        margin-top:10px;
        line-height:1.25;
      }

      .plan-card-sub{
        font-size:.9rem;
        color:rgba(31,41,55,.70);
        margin-top:6px;
      }

      .plan-tile .btn{
        font-size:.85rem;
        padding:6px 22px;
      }

      @media (max-width:576px){
        .plan-title{ font-size:1.45rem; }
        .plan-hero{ height:120px; }
        .plan-tile{ min-height:135px; }
      }
    </style>
    """)

    return render_template_string(BASE, content=Markup(html))

