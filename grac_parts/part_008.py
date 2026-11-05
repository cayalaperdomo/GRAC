@app.route('/rfc/aprobar_seguridad/<int:id>', methods=['GET', 'POST'])
@login_required
def rfc_aprobar_seguridad(id):
    user = User.query.get(session.get('user_id'))

    item = CambioRFCRegistro.query.get_or_404(id)
    aprobado = item.estado_seguridad == "Aprobado por seguridad"

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Gestión de Cambios (RFC)"):
        flash("No tiene permiso para acceder a la aprobación de seguridad.", "danger")
        return redirect(url_for('rfc_matriz'))

    if request.method == 'POST':
        if user.role == 'auditor':
            flash("El rol Auditor no puede aprobar registros.", "danger")
            return redirect(url_for('rfc_matriz'))

        if user.role != 'admin' and not verificar_permiso(user, "Gestión de Cambios (RFC)"):
            flash("No tiene permiso para aprobar cambios por seguridad.", "danger")
            return redirect(url_for('rfc_matriz'))

        fecha = parse_date_safe(request.form.get('aprueba_seguridad_fecha'))
        persona_id = request.form.get('aprueba_seguridad_persona_id', type=int)
        observacion = (request.form.get('aprueba_seguridad_observacion') or '').strip()

        if not fecha:
            flash("La fecha de aprobación de seguridad es obligatoria.", "danger")
            return redirect(url_for('rfc_aprobar_seguridad', id=id))

        if not persona_id:
            flash("Debe seleccionar el responsable que aprueba por seguridad.", "danger")
            return redirect(url_for('rfc_aprobar_seguridad', id=id))

        area = AreaEmpresa.query.get(persona_id)
        if not area:
            flash("No se encontró el responsable seleccionado.", "danger")
            return redirect(url_for('rfc_aprobar_seguridad', id=id))

        item.aprueba_seguridad_fecha = fecha
        item.aprueba_seguridad_nombre = getattr(area, 'responsable_nombre', '') or ''
        item.aprueba_seguridad_cargo = getattr(area, 'responsable_cargo', '') or ''
        item.aprueba_seguridad_observacion = observacion
        item.estado_seguridad = "Aprobado por seguridad"

        db.session.commit()

        flash("RFC aprobado por seguridad correctamente.", "success")
        return redirect(url_for('rfc_matriz'))

    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()

    html = """
    <div class="rfcsec-shell">

      <div class="rfcsec-header-card">
        <div class="rfcsec-header-overlay">
          <div class="rfcsec-header-text">
            <h3 class="rfcsec-title m-0">
              {% if aprobado %}Ver aprobación de seguridad{% else %}7.4 Aprueba Seguridad{% endif %}
            </h3>
            <div class="rfcsec-subtitle">
              Solicitud de cambio RFC {{ item.ticket or item.id }}
            </div>
          </div>
        </div>
      </div>

      <div class="rfcsec-header-actions">
        <a href="{{ url_for('rfc_matriz') }}"
           class="btn rounded-pill px-5 fw-bold rfcsec-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz RFC
        </a>
      </div>

      <div class="rfcsec-card">
        <div class="rfcsec-card-body">

          <div class="rfcsec-status-box">
            <div>
              <div class="rfcsec-status-title">Estado actual de seguridad</div>
              <div class="rfcsec-status-subtitle">
                {% if aprobado %}
                  Consulta de la aprobación registrada por seguridad.
                {% else %}
                  Complete los datos requeridos para aprobar formalmente el cambio desde seguridad.
                {% endif %}
              </div>
            </div>

            {% if aprobado %}
              <span class="badge rfcsec-badge rfcsec-badge-ok">Aprobado por seguridad</span>
            {% else %}
              <span class="badge rfcsec-badge rfcsec-badge-pending">Pendiente de aprobación por seguridad</span>
            {% endif %}
          </div>

          <form method="post">
            <div class="row g-3">

              <div class="col-12">
                <div class="rfcsec-section-title">
                  Información de aprobación de seguridad
                </div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha aprobación seguridad</label>
                <input type="date"
                       name="aprueba_seguridad_fecha"
                       class="form-control"
                       value="{{ item.aprueba_seguridad_fecha.strftime('%Y-%m-%d') if item.aprueba_seguridad_fecha else '' }}"
                       {% if aprobado %}readonly disabled{% else %}required{% endif %}>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre</label>

                {% if aprobado %}
                  <input type="text"
                         class="form-control"
                         value="{{ item.aprueba_seguridad_nombre or '—' }}"
                         readonly>
                {% else %}
                  <select name="aprueba_seguridad_persona_id"
                          id="aprueba_seguridad_persona_id"
                          class="form-select"
                          onchange="fillCargoDesdeArea('aprueba_seguridad_persona_id','aprueba_seguridad_cargo')"
                          required>
                    <option value="">-- Seleccione --</option>
                    {% for a in areas %}
                      <option value="{{ a.id }}"
                              data-cargo="{{ a.responsable_cargo or '' }}"
                              {% if item.aprueba_seguridad_nombre == a.responsable_nombre %}selected{% endif %}>
                        {{ a.responsable_nombre }}
                      </option>
                    {% endfor %}
                  </select>
                {% endif %}
              </div>

              <div class="col-md-4">
                <label class="form-label">Cargo</label>
                <input type="text"
                       id="aprueba_seguridad_cargo"
                       class="form-control"
                       value="{{ item.aprueba_seguridad_cargo or '' }}"
                       readonly>
              </div>

              <div class="col-12">
                <label class="form-label">Observación</label>
                <textarea name="aprueba_seguridad_observacion"
                          class="form-control"
                          rows="4"
                          {% if aprobado %}readonly disabled{% endif %}
                          placeholder="Registre la observación de aprobación de seguridad">{{ item.aprueba_seguridad_observacion or '' }}</textarea>
              </div>

            </div>

            <div class="rfcsec-bottom-actions">

              {% if not aprobado %}
                <button type="submit"
                        class="btn btn-success rounded-pill px-4 fw-bold">
                  Guardar aprobación
                </button>
              {% endif %}

              <a href="{{ url_for('rfc_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold rfcsec-cancel-btn"
                 onclick="showLoader()">
                {% if aprobado %}Volver{% else %}Cancelar{% endif %}
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

      .rfcsec-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      .rfcsec-header-card{
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

      .rfcsec-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .rfcsec-header-overlay{
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

      .rfcsec-header-overlay::before{
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

      .rfcsec-header-text{
        width:100%;
        max-width:1200px;
      }

      .rfcsec-header-text::before{
        content:"SGSI · Gestión de Cambios / RFC";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .rfcsec-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .rfcsec-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .rfcsec-header-actions,
      .rfcsec-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .rfcsec-header-actions .btn,
      .rfcsec-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .rfcsec-back-btn,
      .rfcsec-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .rfcsec-back-btn:hover,
      .rfcsec-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .rfcsec-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .rfcsec-card-body{
        padding:18px;
      }

      .rfcsec-status-box{
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:14px 16px;
        margin-bottom:16px;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
        box-shadow:0 6px 14px rgba(15,23,42,.08);
      }

      .rfcsec-status-title{
        font-weight:950;
        font-size:.90rem;
        color:#0f172a;
      }

      .rfcsec-status-subtitle{
        color:#475569;
        font-size:.78rem;
        margin-top:2px;
      }

      .rfcsec-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:4px 0 12px;
      }

      .rfcsec-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .rfcsec-card .form-control,
      .rfcsec-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .rfcsec-card textarea.form-control{
        min-height:95px;
        resize:vertical;
      }

      .rfcsec-card .form-control:focus,
      .rfcsec-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .rfcsec-badge{
        border-radius:999px;
        font-size:.72rem;
        padding:.45rem .75rem;
        font-weight:900;
        display:inline-flex;
        align-items:center;
        justify-content:center;
        text-align:center;
        line-height:1.15;
        white-space:normal;
      }

      .rfcsec-badge-ok{
        background:#dcfce7;
        color:#166534;
      }

      .rfcsec-badge-pending{
        background:#fef3c7;
        color:#92400e;
      }

      @media (max-width:992px){
        .rfcsec-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .rfcsec-header-card{
          min-height:88px;
        }

        .rfcsec-title{
          font-size:1.20rem;
        }

        .rfcsec-card-body{
          padding:8px 7px;
        }

        .rfcsec-status-box{
          flex-direction:column;
          align-items:flex-start;
        }
      }

      @media (max-width:768px){
        .rfcsec-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .rfcsec-header-overlay::before{
          margin:0;
        }

        .rfcsec-header-actions .btn,
        .rfcsec-bottom-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      function fillCargoDesdeArea(selectId, cargoInputId){
        const sel = document.getElementById(selectId);
        const opt = sel && sel.selectedOptions && sel.selectedOptions[0];
        const cargo = opt ? (opt.getAttribute('data-cargo') || '') : '';
        const inpCar = document.getElementById(cargoInputId);
        if (inpCar) inpCar.value = cargo;
      }

      window.addEventListener('DOMContentLoaded', function(){
        const sel = document.getElementById('aprueba_seguridad_persona_id');
        if(sel){
          fillCargoDesdeArea('aprueba_seguridad_persona_id','aprueba_seguridad_cargo');
        }
      });
    </script>
    """

    inner = render_template_string(
        html,
        item=item,
        areas=areas,
        aprobado=aprobado
    )
    return render_template_string(BASE, content=Markup(inner))

# ==========================
# MATRIZ — RFC
# ==========================
@app.route('/rfc_matriz')
@login_required
def rfc_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Gestión de Cambios (RFC)"):
            flash("No tiene permiso para ver la matriz de gestión de cambios.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    filtro_ticket = (request.args.get('ticket') or '').strip()
    filtro_tipo = (request.args.get('tipo_cambio') or '').strip()
    filtro_prioridad = (request.args.get('prioridad') or '').strip()
    filtro_eficaz = (request.args.get('cambio_eficaz') or '').strip()

    query = CambioRFCRegistro.query

    if filtro_ticket:
        query = query.filter(CambioRFCRegistro.ticket.ilike(f"%{filtro_ticket}%"))

    if filtro_tipo:
        query = query.filter(CambioRFCRegistro.tipo_cambio == filtro_tipo)

    if filtro_prioridad:
        query = query.filter(CambioRFCRegistro.prioridad == filtro_prioridad)

    if filtro_eficaz:
        query = query.filter(CambioRFCRegistro.cambio_eficaz == filtro_eficaz)

    items = query.order_by(CambioRFCRegistro.id.desc()).all()

    opciones_tipo = [
        x[0] for x in db.session.query(CambioRFCRegistro.tipo_cambio)
        .filter(CambioRFCRegistro.tipo_cambio.isnot(None))
        .filter(CambioRFCRegistro.tipo_cambio != '')
        .distinct()
        .order_by(CambioRFCRegistro.tipo_cambio.asc())
        .all()
    ]

    opciones_prioridad = [
        x[0] for x in db.session.query(CambioRFCRegistro.prioridad)
        .filter(CambioRFCRegistro.prioridad.isnot(None))
        .filter(CambioRFCRegistro.prioridad != '')
        .distinct()
        .order_by(CambioRFCRegistro.prioridad.asc())
        .all()
    ]

    opciones_eficaz = [
        x[0] for x in db.session.query(CambioRFCRegistro.cambio_eficaz)
        .filter(CambioRFCRegistro.cambio_eficaz.isnot(None))
        .filter(CambioRFCRegistro.cambio_eficaz != '')
        .distinct()
        .order_by(CambioRFCRegistro.cambio_eficaz.asc())
        .all()
    ]

    total_filtrados = len(items)
    total_general = CambioRFCRegistro.query.count()

    html = """
    <div class="rfcmat-shell">

      <div class="rfcmat-header-card">
        <div class="rfcmat-header-overlay">
          <div class="rfcmat-header-text">
            <h3 class="rfcmat-title m-0">Gestión de Cambios (RFC)</h3>
            <div class="rfcmat-subtitle">
              Visualización resumida de solicitudes de cambio, seguimiento, aprobación e implementación dentro del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="rfcmat-header-actions">
        {% if not read_only %}
        <a href="{{ url_for('rfc_new') }}"
           class="btn btn-primary rounded-pill px-4 fw-bold"
           onclick="showLoader()">
          ➕ Agregar RFC
        </a>
        {% endif %}
      </div>

      <div class="rfcmat-topbar">
        <div class="rfcmat-topbar-card">
          <div class="rfcmat-topbar-title">Resumen de solicitudes RFC</div>
          <div class="rfcmat-topbar-subtitle">
            Total registros: <strong>{{ total_general }}</strong>
            &nbsp; | &nbsp;
            Mostrando: <strong>{{ total_filtrados }}</strong>
          </div>
        </div>
      </div>

      <div class="rfcmat-filter-card">
        <div class="rfcmat-filter-head">
          <span>Filtros de búsqueda</span>
        </div>

        <div class="rfcmat-filter-body">
          <form method="get" class="row g-2 align-items-end">

            <div class="col-xl-3 col-lg-3 col-md-6">
              <label class="form-label rfcmat-label">Ticket</label>
              <input type="text"
                     name="ticket"
                     class="form-control form-control-sm rfcmat-input-sm"
                     value="{{ filtro_ticket }}"
                     placeholder="Buscar ticket">
            </div>

            <div class="col-xl-3 col-lg-3 col-md-6">
              <label class="form-label rfcmat-label">Tipo de cambio</label>
              <select name="tipo_cambio" class="form-select form-select-sm rfcmat-input-sm">
                <option value="">Todos</option>
                {% for op in opciones_tipo %}
                  <option value="{{ op }}" {% if filtro_tipo == op %}selected{% endif %}>{{ op }}</option>
                {% endfor %}
              </select>
            </div>

            <div class="col-xl-2 col-lg-2 col-md-4">
              <label class="form-label rfcmat-label">Prioridad</label>
              <select name="prioridad" class="form-select form-select-sm rfcmat-input-sm">
                <option value="">Todas</option>
                {% for op in opciones_prioridad %}
                  <option value="{{ op }}" {% if filtro_prioridad == op %}selected{% endif %}>{{ op }}</option>
                {% endfor %}
              </select>
            </div>

            <div class="col-xl-2 col-lg-2 col-md-4">
              <label class="form-label rfcmat-label">Eficaz</label>
              <select name="cambio_eficaz" class="form-select form-select-sm rfcmat-input-sm">
                <option value="">Todos</option>
                {% for op in opciones_eficaz %}
                  <option value="{{ op }}" {% if filtro_eficaz == op %}selected{% endif %}>{{ op }}</option>
                {% endfor %}
              </select>
            </div>

            <div class="col-xl-2 col-lg-2 col-md-4">
              <div class="d-flex gap-2 rfcmat-filter-actions">
                <button type="submit" class="btn btn-primary btn-sm rounded-pill px-3 w-100">
                  Filtrar
                </button>
                <a href="{{ url_for('rfc_matriz') }}"
                   class="btn btn-outline-secondary btn-sm rounded-pill px-3 w-100"
                   onclick="showLoader()">
                  Limpiar
                </a>
              </div>
            </div>

          </form>
        </div>
      </div>

      <div class="rfcmat-card">
        <div class="rfcmat-card-body">
          <div class="table-responsive">
            <table class="table table-hover align-middle rfcmat-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Ticket</th>
                  <th>Fecha</th>
                  <th>Responsable</th>
                  <th>Tipo de cambio</th>
                  <th>Prioridad</th>
                  <th>Ambiente</th>
                  <th>¿Eficaz?</th>
                  <th>Estado Seguridad</th>
                  <th class="rfcmat-col-acciones">Acciones</th>
                </tr>
              </thead>

              <tbody>
                {% for it in items %}
                <tr>
                  <td>{{ it.id }}</td>
                  <td>{{ it.ticket or '—' }}</td>
                  <td>{{ it.fecha_solicitud.strftime('%Y-%m-%d') if it.fecha_solicitud else '—' }}</td>
                  <td>{{ it.responsable_solicitud_nombre or '—' }}</td>
                  <td>{{ it.tipo_cambio or '—' }}</td>

                  <td>
                    {% set p = (it.prioridad or '')|lower %}
                    {% if p == 'alta' %}
                      <span class="badge rfcmat-badge rfcmat-badge-alta">Alta</span>
                    {% elif p == 'media' %}
                      <span class="badge rfcmat-badge rfcmat-badge-media">Media</span>
                    {% elif p == 'baja' %}
                      <span class="badge rfcmat-badge rfcmat-badge-baja">Baja</span>
                    {% else %}
                      <span class="badge rfcmat-badge rfcmat-badge-neutro">—</span>
                    {% endif %}
                  </td>

                  <td>{{ it.ambiente or '—' }}</td>

                  <td>
                    {% set e = (it.cambio_eficaz or '')|lower %}
                    {% if e == 'si' %}
                      <span class="badge rfcmat-badge rfcmat-badge-ok">Sí</span>
                    {% elif e == 'no' %}
                      <span class="badge rfcmat-badge rfcmat-badge-no">No</span>
                    {% else %}
                      <span class="badge rfcmat-badge rfcmat-badge-neutro">—</span>
                    {% endif %}
                  </td>

                  <td>
                    {% if it.estado_seguridad == 'Aprobado por seguridad' %}
                      <span class="badge rfcmat-badge rfcmat-badge-ok">
                        Aprobado
                      </span>
                    {% else %}
                      <span class="badge rfcmat-badge rfcmat-badge-pendiente">
                        Pendiente de aprobación
                      </span>
                    {% endif %}
                  </td>

                  <td class="rfcmat-col-acciones">
                    <div class="rfcmat-actions-wrap">

                      <a href="{{ url_for('rfc_view', id=it.id) }}"
                         class="btn btn-info btn-sm rounded-pill rfcmat-btn-action"
                         onclick="showLoader()">
                        Ver detalle
                      </a>

                      {% if it.estado_seguridad == 'Aprobado por seguridad' %}
                        <a href="{{ url_for('rfc_aprobar_seguridad', id=it.id) }}"
                           class="btn btn-secondary btn-sm rounded-pill rfcmat-btn-action"
                           onclick="showLoader()">
                          Ver aprobación
                        </a>
                      {% elif not read_only %}
                        <a href="{{ url_for('rfc_aprobar_seguridad', id=it.id) }}"
                           class="btn btn-success btn-sm rounded-pill rfcmat-btn-action"
                           onclick="showLoader()">
                          Aprobar
                        </a>
                      {% endif %}

                      {% if not read_only %}
                        <a href="{{ url_for('rfc_edit', id=it.id) }}"
                           class="btn btn-warning btn-sm rounded-pill rfcmat-btn-action"
                           onclick="showLoader()">
                          Editar
                        </a>

                        <a href="{{ url_for('rfc_delete', id=it.id) }}"
                           class="btn btn-danger btn-sm rounded-pill rfcmat-btn-action"
                           onclick="return confirm('¿Está seguro de eliminar esta solicitud RFC?');">
                          Eliminar
                        </a>
                      {% else %}
                        <span class="badge bg-secondary">Solo lectura</span>
                      {% endif %}

                    </div>
                  </td>
                </tr>
                {% endfor %}

                {% if not items %}
                <tr>
                  <td colspan="10" class="text-center text-muted py-4">
                    No hay registros RFC para los filtros seleccionados.
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

      .rfcmat-shell{
        width:96%;
        max-width:1700px;
        margin:10px auto 24px auto;
      }

      .rfcmat-header-card{
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

      .rfcmat-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .rfcmat-header-overlay{
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

      .rfcmat-header-overlay::before{
        content:"🔄";
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

      .rfcmat-header-overlay > div::before,
      .rfcmat-header-text::before{
        content:"SGSI · Matriz de Cambios / RFC";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .rfcmat-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .rfcmat-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .rfcmat-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .rfcmat-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .rfcmat-topbar-card,
      .rfcmat-filter-card,
      .rfcmat-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .rfcmat-topbar-card{
        padding:14px 16px;
        margin-bottom:12px;
      }

      .rfcmat-topbar-title{
        font-weight:950;
        font-size:.92rem;
        color:#0f172a;
      }

      .rfcmat-topbar-subtitle{
        font-size:.78rem;
        color:#475569;
      }

      .rfcmat-filter-card{
        margin-bottom:14px;
      }

      .rfcmat-filter-head{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#fff;
        font-weight:900;
        font-size:.82rem;
        padding:10px 14px;
      }

      .rfcmat-filter-body{
        padding:14px 16px;
      }

      .rfcmat-label{
        font-weight:800;
        font-size:.75rem;
        color:#25324a;
        margin-bottom:4px;
      }

      .rfcmat-input-sm{
        min-height:36px !important;
        height:36px !important;
        font-size:.78rem !important;
        border-radius:9px !important;
        padding:.25rem .6rem !important;
        border:1px solid #d9e3f0 !important;
        background:#f8fafc !important;
      }

      .rfcmat-input-sm:focus{
        border-color:#3f86d6 !important;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff !important;
      }

      .rfcmat-filter-actions .btn{
        border-radius:10px !important;
        min-height:36px;
        padding:7px 18px !important;
        font-size:.78rem;
        font-weight:900;
      }

      .rfcmat-card-body{
        padding:12px 16px 16px 16px;
      }

      .table-responsive{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .rfcmat-table{
        min-width:1650px;
        table-layout:fixed;
        margin-bottom:0;
      }

      .rfcmat-table thead th{
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

      .rfcmat-table th,
      .rfcmat-table td{
        vertical-align:middle;
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal !important;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .rfcmat-table td{
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .rfcmat-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .rfcmat-table tbody tr:hover{
        background:#eef6ff;
      }

      .rfcmat-table th:nth-child(9),
      .rfcmat-table td:nth-child(9){
        width:230px !important;
        min-width:230px !important;
        max-width:230px !important;
        text-align:center !important;
        vertical-align:middle !important;
      }

      .rfcmat-table td:nth-child(9) .badge,
      .rfcmat-badge-pendiente{
        width:185px !important;
        max-width:185px !important;
        white-space:normal !important;
        word-break:normal !important;
        overflow-wrap:break-word !important;
        line-height:1.15 !important;
        padding:.45rem .55rem !important;
        display:inline-flex !important;
        align-items:center !important;
        justify-content:center !important;
        text-align:center !important;
        border-radius:999px !important;
      }

      .rfcmat-col-acciones{
        width:190px !important;
        min-width:190px !important;
        text-align:center;
        vertical-align:middle !important;
      }

      .rfcmat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .rfcmat-btn-action{
        min-width:115px;
        max-width:135px;
        padding:4px 12px !important;
        font-size:.64rem !important;
        line-height:1.2;
        text-align:center;
        white-space:nowrap;
        border-radius:999px !important;
        font-weight:900;
      }

      .rfcmat-badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
        display:inline-block;
        text-align:center;
      }

      .rfcmat-badge-alta{ background:#fee2e2; color:#991b1b; }
      .rfcmat-badge-media{ background:#fef3c7; color:#92400e; }
      .rfcmat-badge-baja{ background:#dcfce7; color:#166534; }
      .rfcmat-badge-ok{ background:#dcfce7; color:#166534; }
      .rfcmat-badge-no{ background:#fee2e2; color:#991b1b; }
      .rfcmat-badge-neutro{ background:#e5e7eb; color:#374151; }
      .rfcmat-badge-pendiente{ background:#fef3c7; color:#92400e; }

      @media (max-width:992px){
        .rfcmat-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .rfcmat-header-card{
          min-height:88px;
        }

        .rfcmat-title{
          font-size:1.20rem;
        }

        .rfcmat-card-body,
        .rfcmat-filter-body{
          padding:12px;
        }

        .rfcmat-col-acciones{
          width:170px !important;
          min-width:170px !important;
        }

        .rfcmat-table th:nth-child(9),
        .rfcmat-table td:nth-child(9){
          width:210px !important;
          min-width:210px !important;
        }
      }

      @media (max-width:768px){
        .rfcmat-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .rfcmat-header-overlay::before{
          margin:0;
        }

        .rfcmat-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        opciones_tipo=opciones_tipo,
        opciones_prioridad=opciones_prioridad,
        opciones_eficaz=opciones_eficaz,
        filtro_ticket=filtro_ticket,
        filtro_tipo=filtro_tipo,
        filtro_prioridad=filtro_prioridad,
        filtro_eficaz=filtro_eficaz,
        total_filtrados=total_filtrados,
        total_general=total_general
    )

    return render_template_string(BASE, content=Markup(inner))

# =========================
# Editar RFC
# =========================

@app.route('/rfc/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def rfc_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede editar registros.", "danger")
        return redirect(url_for('rfc_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Cambios (RFC)"):
        flash("No tiene permiso para editar cambios.", "danger")
        return redirect(url_for('rfc_matriz'))

    item = CambioRFCRegistro.query.get_or_404(id)
    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()

    if request.method == 'POST':
        try:
            item.ticket = (request.form.get('ticket') or '').strip()
            evidencias_files = request.files.getlist('evidencias')

            fecha_solicitud = parse_date_safe(request.form.get('fecha_solicitud'))
            if not fecha_solicitud:
                flash("La fecha de solicitud es obligatoria y debe tener formato válido.", "danger")
                return redirect(url_for('rfc_edit', id=id))
            item.fecha_solicitud = fecha_solicitud

            responsable_id = request.form.get('responsable_solicitud_id', type=int)
            item.responsable_solicitud_id = responsable_id

            if responsable_id:
                a = AreaEmpresa.query.get(responsable_id)
                if a:
                    item.responsable_solicitud_nombre = getattr(a, 'responsable_nombre', '') or ''
                    item.responsable_solicitud_cargo = getattr(a, 'responsable_cargo', '') or ''
                else:
                    item.responsable_solicitud_nombre = ''
                    item.responsable_solicitud_cargo = ''
            else:
                item.responsable_solicitud_nombre = ''
                item.responsable_solicitud_cargo = ''

            item.descripcion = (request.form.get('descripcion') or '').strip()
            item.antecedentes = (request.form.get('antecedentes') or '').strip()
            item.objetivo = (request.form.get('objetivo') or '').strip()
            item.alcance = (request.form.get('alcance') or '').strip()
            item.ambiente = (request.form.get('ambiente') or '').strip()
            item.partes_interesadas = (request.form.get('partes_interesadas') or '').strip()
            item.recursos_necesarios = (request.form.get('recursos_necesarios') or '').strip()
            item.tipo_cambio = (request.form.get('tipo_cambio') or '').strip()
            item.prioridad = (request.form.get('prioridad') or '').strip()
            # --- Evaluación de riesgos (múltiples) ---
            riesgos_sistema      = request.form.getlist('sistema_procedente[]')
            riesgos_riesgo       = request.form.getlist('riesgo[]')
            riesgos_impacto      = request.form.getlist('impacto[]')
            riesgos_controles    = request.form.getlist('controles_aplicar[]')
            riesgos_responsable  = request.form.getlist('responsable_riesgo[]')

            # --- Plan de pruebas (múltiples) ---
            planes_act       = request.form.getlist('plan_pruebas_actividad[]')
            planes_inicio    = request.form.getlist('plan_pruebas_fecha_inicio[]')
            planes_fin       = request.form.getlist('plan_pruebas_fecha_fin[]')
            planes_resp      = request.form.getlist('plan_pruebas_responsable[]')
            planes_entreg    = request.form.getlist('plan_pruebas_entregables[]')
            planes_acciones  = request.form.getlist('plan_pruebas_acciones[]')

            # --- Rollback (múltiples) ---
            rb_acts   = request.form.getlist('rollback_actividad[]')
            rb_resps  = request.form.getlist('rollback_responsable[]')
            rb_ejecs  = request.form.getlist('rollback_ejecucion[]')

            # --- Actividades implementadas (múltiples) ---
            impl_acts    = request.form.getlist('impl_actividad[]')
            impl_resps   = request.form.getlist('impl_responsable[]')
            impl_fechas  = request.form.getlist('impl_fecha[]')
            impl_ejecs   = request.form.getlist('impl_ejecucion[]')

            # ===== CAMPOS ÚNICOS DEL CAPÍTULO =====
            impl_tmon_unico  = (request.form.get('impl_tiempo_monitoreo_unico') or '').strip()
            impl_fap_unica   = (request.form.get('impl_fecha_aprobacion_unica') or '').strip()
            impl_ftc_unica   = (request.form.get('impl_fecha_tentativa_cierre_unica') or '').strip()
            impl_frc_unica   = (request.form.get('impl_fecha_real_cierre_unica') or '').strip()
            impl_obs_unica   = (request.form.get('impl_observaciones_unicas') or '').strip()

            item.ajustes_requeridos = (request.form.get('ajustes_requeridos') or '').strip()
            item.cambios_requeridos = (request.form.get('cambios_requeridos') or '').strip()

            revisa_id = request.form.get('revisa_persona_id', type=int)
            item.revisa_persona_id = revisa_id
            item.revisa_observaciones = (request.form.get('revisa_observaciones') or '').strip()
            item.revisa_fecha = parse_date_safe(request.form.get('revisa_fecha'))

            if revisa_id:
                ar = AreaEmpresa.query.get(revisa_id)
                if ar:
                    item.revisa_nombre = getattr(ar, 'responsable_nombre', '') or ''
                    item.revisa_cargo = getattr(ar, 'responsable_cargo', '') or ''
                else:
                    item.revisa_nombre = ''
                    item.revisa_cargo = ''
            else:
                item.revisa_nombre = ''
                item.revisa_cargo = ''

            aprueba_id = request.form.get('aprueba_persona_id', type=int)
            item.aprueba_persona_id = aprueba_id
            item.aprueba_observaciones = (request.form.get('aprueba_observaciones') or '').strip()
            item.aprueba_fecha = parse_date_safe(request.form.get('aprueba_fecha'))

            if aprueba_id:
                aa = AreaEmpresa.query.get(aprueba_id)
                if aa:
                    item.aprueba_nombre = getattr(aa, 'responsable_nombre', '') or ''
                    item.aprueba_cargo = getattr(aa, 'responsable_cargo', '') or ''
                else:
                    item.aprueba_nombre = ''
                    item.aprueba_cargo = ''
            else:
                item.aprueba_nombre = ''
                item.aprueba_cargo = ''

            implementa_id = request.form.get('implementa_persona_id', type=int)
            item.implementa_persona_id = implementa_id
            item.implementa_observaciones = (request.form.get('implementa_observaciones') or '').strip()
            item.implementa_fecha = parse_date_safe(request.form.get('implementa_fecha'))

            if implementa_id:
                ai = AreaEmpresa.query.get(implementa_id)
                if ai:
                    item.implementa_nombre = getattr(ai, 'responsable_nombre', '') or ''
                    item.implementa_cargo = getattr(ai, 'responsable_cargo', '') or ''
                else:
                    item.implementa_nombre = ''
                    item.implementa_cargo = ''
            else:
                item.implementa_nombre = ''
                item.implementa_cargo = ''

            item.cambio_eficaz = (request.form.get('cambio_eficaz') or '').strip()
            item.descripcion_seguimiento = (request.form.get('descripcion_seguimiento') or '').strip()

            # =========================
            # Reemplazar detalles hijos
            # =========================
            CambioRFCRiesgo.query.filter_by(rfc_id=item.id).delete()
            CambioRFCPlanPruebas.query.filter_by(rfc_id=item.id).delete()
            CambioRFCRollback.query.filter_by(rfc_id=item.id).delete()
            CambioRFCImplementacion.query.filter_by(rfc_id=item.id).delete()
            db.session.flush()

            # =========================
            # Guardar Evaluación de riesgos
            # =========================
            total_riesgos = max(
                len(riesgos_sistema),
                len(riesgos_riesgo),
                len(riesgos_impacto),
                len(riesgos_controles),
                len(riesgos_responsable)
            )

            for i in range(total_riesgos):
                sistema      = (riesgos_sistema[i] if i < len(riesgos_sistema) else '').strip()
                riesgo_txt   = (riesgos_riesgo[i] if i < len(riesgos_riesgo) else '').strip()
                impacto_txt  = (riesgos_impacto[i] if i < len(riesgos_impacto) else '').strip()
                controles    = (riesgos_controles[i] if i < len(riesgos_controles) else '').strip()
                responsable  = (riesgos_responsable[i] if i < len(riesgos_responsable) else '').strip()

                if any([sistema, riesgo_txt, impacto_txt, controles, responsable]):
                    db.session.add(CambioRFCRiesgo(
                        rfc_id=item.id,
                        sistema_procedente=sistema,
                        riesgo=riesgo_txt,
                        impacto=impacto_txt,
                        controles_aplicar=controles,
                        responsable_riesgo=responsable
                    ))

            # =========================
            # Guardar Planes de pruebas
            # =========================
            total_planes = max(
                len(planes_act), len(planes_inicio), len(planes_fin),
                len(planes_resp), len(planes_entreg), len(planes_acciones)
            )

            for i in range(total_planes):
                actividad   = (planes_act[i] if i < len(planes_act) else '').strip()
                fecha_ini   = (planes_inicio[i] if i < len(planes_inicio) else '').strip()
                fecha_fin   = (planes_fin[i] if i < len(planes_fin) else '').strip()
                responsable = (planes_resp[i] if i < len(planes_resp) else '').strip()
                entregables = (planes_entreg[i] if i < len(planes_entreg) else '').strip()
                acciones    = (planes_acciones[i] if i < len(planes_acciones) else '').strip()

                if any([actividad, fecha_ini, fecha_fin, responsable, entregables, acciones]):
                    db.session.add(CambioRFCPlanPruebas(
                        rfc_id=item.id,
                        actividad=actividad,
                        fecha_inicio=fecha_ini,
                        fecha_fin=fecha_fin,
                        responsable=responsable,
                        entregables=entregables,
                        acciones=acciones
                    ))

            # =========================
            # Guardar Rollbacks
            # =========================
            total_rb = max(len(rb_acts), len(rb_resps), len(rb_ejecs))

            for i in range(total_rb):
                actividad   = (rb_acts[i] if i < len(rb_acts) else '').strip()
                responsable = (rb_resps[i] if i < len(rb_resps) else '').strip()
                ejecucion   = (rb_ejecs[i] if i < len(rb_ejecs) else '').strip()

                if any([actividad, responsable, ejecucion]):
                    db.session.add(CambioRFCRollback(
                        rfc_id=item.id,
                        actividad=actividad,
                        responsable=responsable,
                        ejecucion=ejecucion
                    ))

            # =========================
            # Guardar Implementaciones
            # =========================
            total_impl = max(
                len(impl_acts), len(impl_resps), len(impl_fechas), len(impl_ejecs)
            )

            for i in range(total_impl):
                actividad   = (impl_acts[i] if i < len(impl_acts) else '').strip()
                responsable = (impl_resps[i] if i < len(impl_resps) else '').strip()
                fecha       = (impl_fechas[i] if i < len(impl_fechas) else '').strip()
                ejecucion   = (impl_ejecs[i] if i < len(impl_ejecs) else '').strip()

                # Solo el primer registro guarda los campos globales del capítulo
                tmon          = impl_tmon_unico if i == 0 else ''
                fecha_apr     = impl_fap_unica if i == 0 else ''
                fecha_tent    = impl_ftc_unica if i == 0 else ''
                fecha_real    = impl_frc_unica if i == 0 else ''
                observaciones = impl_obs_unica if i == 0 else ''

                if any([actividad, responsable, fecha, ejecucion, tmon, fecha_apr, fecha_tent, fecha_real, observaciones]):
                    db.session.add(CambioRFCImplementacion(
                        rfc_id=item.id,
                        actividad=actividad,
                        responsable=responsable,
                        fecha=fecha,
                        ejecucion=ejecucion,
                        tiempo_monitoreo=tmon,
                        fecha_aprobacion=fecha_apr,
                        fecha_tentativa_cierre=fecha_tent,
                        fecha_real_cierre=fecha_real,
                        observaciones=observaciones
                    ))

            # =========================
            # Guardar nuevas evidencias RFC
            # =========================
            upload_dir = app.config['UPLOAD_RFC_DIR']
            os.makedirs(upload_dir, exist_ok=True)

            for file in evidencias_files:
                if not file or not file.filename:
                    continue

                original_name = secure_filename(file.filename)
                if not original_name:
                    continue

                ext = os.path.splitext(original_name)[1].lower()
                unique_name = f"rfc_{item.id}_{uuid.uuid4().hex}{ext}"
                save_path = os.path.join(upload_dir, unique_name)

                file.save(save_path)

                try:
                    file_size = os.path.getsize(save_path)
                except Exception:
                    file_size = 0

                nueva_evidencia = CambioRFCEvidencia(
                    rfc_id=item.id,
                    filename=unique_name,
                    original_name=original_name,
                    mime=file.mimetype or 'application/octet-stream',
                    size=file_size
                )
                db.session.add(nueva_evidencia)


            db.session.commit()
            flash("Solicitud RFC actualizada.", "success")
            return redirect(url_for('rfc_matriz'))

        except Exception:
            db.session.rollback()
            raise

    riesgos_data = [
        {
            'sistema_procedente': x.sistema_procedente or '',
            'riesgo': x.riesgo or '',
            'impacto': x.impacto or '',
            'controles_aplicar': x.controles_aplicar or '',
            'responsable_riesgo': x.responsable_riesgo or '',
        }
        for x in (item.riesgos or [])
    ]

    planes_data = [
        {
            'actividad': x.actividad or '',
            'fecha_inicio': x.fecha_inicio or '',
            'fecha_fin': x.fecha_fin or '',
            'responsable': x.responsable or '',
            'entregables': x.entregables or '',
            'acciones': x.acciones or '',
        }
        for x in (item.planes_pruebas or [])
    ]

    rollbacks_data = [
        {
            'actividad': x.actividad or '',
            'responsable': x.responsable or '',
            'ejecucion': x.ejecucion or '',
        }
        for x in (item.rollbacks or [])
    ]

    implementaciones_data = [
        {
            'actividad': x.actividad or '',
            'responsable': x.responsable or '',
            'fecha': x.fecha or '',
            'ejecucion': x.ejecucion or '',
            'tiempo_monitoreo': x.tiempo_monitoreo or '',
            'fecha_aprobacion': x.fecha_aprobacion or '',
            'fecha_tentativa_cierre': x.fecha_tentativa_cierre or '',
            'fecha_real_cierre': x.fecha_real_cierre or '',
            'observaciones': x.observaciones or '',
        }
        for x in (item.implementaciones or [])
    ]

    impl_general = {
        'tiempo_monitoreo': '',
        'fecha_aprobacion': '',
        'fecha_tentativa_cierre': '',
        'fecha_real_cierre': '',
        'observaciones': ''
    }

    if item.implementaciones and len(item.implementaciones) > 0:
        primera_impl = item.implementaciones[0]
        impl_general = {
            'tiempo_monitoreo': primera_impl.tiempo_monitoreo or '',
            'fecha_aprobacion': primera_impl.fecha_aprobacion or '',
            'fecha_tentativa_cierre': primera_impl.fecha_tentativa_cierre or '',
            'fecha_real_cierre': primera_impl.fecha_real_cierre or '',
            'observaciones': primera_impl.observaciones or ''
        }

    html = """
    <div class="rfcedit-shell">

      <!-- CABECERA -->
      <div class="rfcedit-header-card">
        <div class="rfcedit-header-overlay">
          <div class="rfcedit-header-text">
            <h3 class="rfcedit-title m-0">Editar Solicitud de Cambios (RFC)</h3>
            <div class="rfcedit-subtitle">
              Actualización de la solicitud de cambio, evaluación de riesgos, aprobación, implementación y seguimiento del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="rfcedit-header-actions">
        <a href="{{ url_for('rfc_matriz') }}"
           class="btn rounded-pill px-5 fw-bold rfcedit-back-btn">
          ⬅ Volver a la Matriz RFC
        </a>
      </div>

      <!-- TARJETA PRINCIPAL -->
      <div class="rfcedit-card">
        <div class="rfcedit-card-body">

          <form method="post" enctype="multipart/form-data">
            <div class="row g-3">

              <!-- Información general -->
              <div class="col-12">
                <div class="rfcedit-section-title">Información general</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Ticket o No. de solicitud</label>
                <input type="text" name="ticket" class="form-control" value="{{ item.ticket or '' }}" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha Solicitud</label>
                <input type="date" name="fecha_solicitud" class="form-control"
                       value="{{ item.fecha_solicitud.strftime('%Y-%m-%d') if item.fecha_solicitud else '' }}" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Responsable de la solicitud</label>
                <select name="responsable_solicitud_id"
                        id="responsable_solicitud_id"
                        class="form-select"
                        onchange="fillCargoDesdeArea('responsable_solicitud_id','responsable_solicitud_cargo')">
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}"
                            data-cargo="{{ a.responsable_cargo or '' }}"
                            {% if item.responsable_solicitud_id == a.id %}selected{% endif %}>
                      {{ a.responsable_nombre }}
                    </option>
                  {% endfor %}
                </select>
                <input type="text"
                       id="responsable_solicitud_cargo"
                       class="form-control mt-1"
                       value="{{ item.responsable_solicitud_cargo or '' }}"
                       readonly>
              </div>

              <!-- Información del cambio -->
              <div class="col-12 mt-3">
                <div class="rfcedit-section-title">Información del cambio</div>
              </div>

              <div class="col-12">
                <label class="form-label">Descripción</label>
                <textarea name="descripcion" class="form-control" rows="2">{{ item.descripcion or '' }}</textarea>
              </div>

              <div class="col-12">
                <label class="form-label">Antecedentes</label>
                <textarea name="antecedentes" class="form-control" rows="2">{{ item.antecedentes or '' }}</textarea>
              </div>

              <div class="col-12">
                <label class="form-label">Objetivo</label>
                <textarea name="objetivo" class="form-control" rows="2">{{ item.objetivo or '' }}</textarea>
              </div>

              <div class="col-12">
                <label class="form-label">Alcance</label>
                <textarea name="alcance" class="form-control" rows="2">{{ item.alcance or '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Ambiente</label>
                <select name="ambiente" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Producción" {% if item.ambiente == 'Producción' %}selected{% endif %}>Producción</option>
                  <option value="Contingencia" {% if item.ambiente == 'Contingencia' %}selected{% endif %}>Contingencia</option>
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Tipo de cambio</label>
                <select name="tipo_cambio" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Planificado (normal)" {% if item.tipo_cambio == 'Planificado (normal)' %}selected{% endif %}>Planificado (normal)</option>
                  <option value="No planificado (emergencia)" {% if item.tipo_cambio == 'No planificado (emergencia)' %}selected{% endif %}>No planificado (emergencia)</option>
                  <option value="Tipificado (recurrente)" {% if item.tipo_cambio == 'Tipificado (recurrente)' %}selected{% endif %}>Tipificado (recurrente)</option>
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Prioridad</label>
                <select name="prioridad" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Alta" {% if item.prioridad == 'Alta' %}selected{% endif %}>Alta</option>
                  <option value="Media" {% if item.prioridad == 'Media' %}selected{% endif %}>Media</option>
                  <option value="Baja" {% if item.prioridad == 'Baja' %}selected{% endif %}>Baja</option>
                </select>
              </div>

              <div class="col-12">
                <label class="form-label">Partes interesadas impactadas</label>
                <textarea name="partes_interesadas" class="form-control" rows="2">{{ item.partes_interesadas or '' }}</textarea>
              </div>

              <div class="col-12">
                <label class="form-label">Recursos necesarios</label>
                <textarea name="recursos_necesarios" class="form-control" rows="2">{{ item.recursos_necesarios or '' }}</textarea>
              </div>

              <!-- Evaluación de riesgos -->
              <div class="col-12 mt-3">
                <div class="d-flex justify-content-between align-items-center">
                  <div class="rfcedit-section-title mb-0">Evaluación de riesgos</div>
                  <button type="button" class="btn btn-outline-primary btn-sm rounded-pill" onclick="addRiesgoRow()">
                    + Agregar registro
                  </button>
                </div>
              </div>

              <div class="col-12">
                <div id="riesgos-container"></div>
              </div>

              <!-- Plan de pruebas -->
              <div class="col-12 mt-3">
                <div class="d-flex justify-content-between align-items-center">
                  <div class="rfcedit-section-title mb-0">Plan de pruebas (si aplica)</div>
                  <button type="button" class="btn btn-outline-primary btn-sm rounded-pill" onclick="addPlanPruebasRow()">
                    + Agregar registro
                  </button>
                </div>
              </div>

              <div class="col-12">
                <div id="plan-pruebas-container"></div>
              </div>

              <!-- Rollback -->
              <div class="col-12 mt-3">
                <div class="d-flex justify-content-between align-items-center">
                  <div class="rfcedit-section-title mb-0">Plan de Marcha Atrás (Rollback)</div>
                  <button type="button" class="btn btn-outline-primary btn-sm rounded-pill" onclick="addRollbackRow()">
                    + Agregar registro
                  </button>
                </div>
              </div>

              <div class="col-12">
                <div id="rollback-container"></div>
              </div>

               <!-- Implementación -->
              <div class="col-12 mt-3">
                <div class="d-flex justify-content-between align-items-center">
                  <div class="rfcedit-section-title mb-0">Actividades implementadas del cambio</div>
                  <button type="button" class="btn btn-outline-primary btn-sm rounded-pill" onclick="addImplementacionRow()">
                    + Agregar registro
                  </button>
                </div>
              </div>

              <!-- PRIMERO: registros implementación -->
              <div class="col-12">
                <div id="implementacion-container"></div>
              </div>

              <!-- DESPUÉS: datos generales del capítulo -->
              <div class="col-12">
                <div class="dynamic-block border rounded p-3 mb-3 bg-light">
                  <div class="mb-2">
                    <strong>Datos generales de implementación del cambio</strong>
                  </div>

                  <div class="row g-3">
                    <div class="col-md-3">
                      <label class="form-label">Tiempo estimado monitoreo</label>
                      <input type="text"
                             name="impl_tiempo_monitoreo_unico"
                             class="form-control"
                             value="{{ impl_general.tiempo_monitoreo }}">
                    </div>

                    <div class="col-md-3">
                      <label class="form-label">Fecha aprobación</label>
                      <input type="date"
                             name="impl_fecha_aprobacion_unica"
                             class="form-control"
                             value="{{ impl_general.fecha_aprobacion }}">
                    </div>

                    <div class="col-md-3">
                      <label class="form-label">Fecha tentativa cierre</label>
                      <input type="date"
                             name="impl_fecha_tentativa_cierre_unica"
                             class="form-control"
                             value="{{ impl_general.fecha_tentativa_cierre }}">
                    </div>

                    <div class="col-md-3">
                      <label class="form-label">Fecha real cierre</label>
                      <input type="date"
                             name="impl_fecha_real_cierre_unica"
                             class="form-control"
                             value="{{ impl_general.fecha_real_cierre }}">
                    </div>

                    <div class="col-md-12">
                      <label class="form-label">Observaciones</label>
                      <textarea name="impl_observaciones_unicas"
                                class="form-control"
                                rows="2">{{ impl_general.observaciones }}</textarea>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Aprobación -->
              <div class="col-12 mt-3">
                <div class="rfcedit-section-title">Aprobación del cambio</div>
              </div>

              <div class="col-md-3">
                <label class="form-label">Se requiere realizar ajustes?</label>
                <select name="ajustes_requeridos" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Si" {% if item.ajustes_requeridos == 'Si' %}selected{% endif %}>Si</option>
                  <option value="No" {% if item.ajustes_requeridos == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-md-9">
                <label class="form-label">Cambios requeridos (si se requieren)</label>
                <textarea name="cambios_requeridos" class="form-control" rows="2">{{ item.cambios_requeridos or '' }}</textarea>
              </div>

              <!-- Revisa -->
              <div class="col-12 mt-2">
                <div class="rfcedit-subsection-title">Revisa</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre responsable del área</label>
                <select name="revisa_persona_id"
                        id="revisa_persona_id"
                        class="form-select"
                        onchange="fillCargoDesdeArea('revisa_persona_id','revisa_cargo')">
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}"
                            data-cargo="{{ a.responsable_cargo or '' }}"
                            {% if item.revisa_persona_id == a.id %}selected{% endif %}>
                      {{ a.responsable_nombre }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Cargo (Responsable de área)</label>
                <input type="text"
                       id="revisa_cargo"
                       class="form-control"
                       value="{{ item.revisa_cargo or '' }}"
                       readonly>
              </div>

              <div class="col-md-4">
                <label class="form-label">Observaciones</label>
                <textarea name="revisa_observaciones" class="form-control" rows="2">{{ item.revisa_observaciones or '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha revisión</label>
                <input type="date"
                       name="revisa_fecha"
                       class="form-control"
                       value="{{ item.revisa_fecha.strftime('%Y-%m-%d') if item.revisa_fecha else '' }}">
              </div>

              <!-- Aprueba -->
              <div class="col-12 mt-2">
                <div class="rfcedit-subsection-title">Aprueba (Comité de cambios)</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre responsable del área</label>
                <select name="aprueba_persona_id"
                        id="aprueba_persona_id"
                        class="form-select"
                        onchange="fillCargoDesdeArea('aprueba_persona_id','aprueba_cargo')">
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}"
                            data-cargo="{{ a.responsable_cargo or '' }}"
                            {% if item.aprueba_persona_id == a.id %}selected{% endif %}>
                      {{ a.responsable_nombre }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Cargo (Responsable de área)</label>
                <input type="text"
                       id="aprueba_cargo"
                       class="form-control"
                       value="{{ item.aprueba_cargo or '' }}"
                       readonly>
              </div>

              <div class="col-md-4">
                <label class="form-label">Observaciones</label>
                <textarea name="aprueba_observaciones" class="form-control" rows="2">{{ item.aprueba_observaciones or '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha revisión</label>
                <input type="date"
                       name="aprueba_fecha"
                       class="form-control"
                       value="{{ item.aprueba_fecha.strftime('%Y-%m-%d') if item.aprueba_fecha else '' }}">
              </div>

              <!-- Implementa -->
              <div class="col-12 mt-2">
                <div class="rfcedit-subsection-title">Implementa</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre responsable del área</label>
                <select name="implementa_persona_id"
                        id="implementa_persona_id"
                        class="form-select"
                        onchange="fillCargoDesdeArea('implementa_persona_id','implementa_cargo')">
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}"
                            data-cargo="{{ a.responsable_cargo or '' }}"
                            {% if item.implementa_persona_id == a.id %}selected{% endif %}>
                      {{ a.responsable_nombre }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Cargo (Responsable de área)</label>
                <input type="text"
                       id="implementa_cargo"
                       class="form-control"
                       value="{{ item.implementa_cargo or '' }}"
                       readonly>
              </div>

              <div class="col-md-4">
                <label class="form-label">Observaciones</label>
                <textarea name="implementa_observaciones" class="form-control" rows="2">{{ item.implementa_observaciones or '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha revisión</label>
                <input type="date"
                       name="implementa_fecha"
                       class="form-control"
                       value="{{ item.implementa_fecha.strftime('%Y-%m-%d') if item.implementa_fecha else '' }}">
              </div>

              <!-- Seguimiento -->
              <div class="col-12 mt-3">
                <div class="rfcedit-section-title">Seguimiento del cambio</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">¿El cambio fue eficaz?</label>
                <select name="cambio_eficaz" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Si" {% if item.cambio_eficaz == 'Si' %}selected{% endif %}>Si</option>
                  <option value="No" {% if item.cambio_eficaz == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Descripción del seguimiento</label>
                <textarea name="descripcion_seguimiento" class="form-control" rows="2">{{ item.descripcion_seguimiento or '' }}</textarea>
              </div>

              <!-- Evidencias -->
              <div class="col-12 mt-3">
                <div class="d-flex justify-content-between align-items-center">
                  <div class="rfcedit-section-title mb-0">Evidencias</div>
                  <div class="text-muted small">Puedes adjuntar uno o varios archivos</div>
                </div>
              </div>

              <div class="col-12">
                <label class="form-label">Cargar nuevas evidencias</label>
                <input type="file"
                       name="evidencias"
                       class="form-control"
                       multiple
                       accept=".pdf,.png,.jpg,.jpeg,.webp,.gif,.doc,.docx,.xls,.xlsx">
              </div>

              <div class="col-12">
                {% if item.evidencias %}
                  <div class="rfcedit-files-grid">
                    {% for ev in item.evidencias %}
                      <div class="rfcedit-file-card">
                        <div class="rfcedit-file-left">
                          <div class="rfcedit-file-icon">
                            {{ (ev.original_name or 'FILE').split('.')[-1][:4]|upper }}
                          </div>
                          <div class="rfcedit-file-meta">
                            <div class="rfcedit-file-label">Evidencia cargada</div>
                            <a href="{{ url_for('rfc_evidencia_view', evi_id=ev.id, next='rfc_edit', rfc_id=item.id) }}"
                               class="rfcedit-file-name">
                              {{ ev.original_name }}
                            </a>
                            <div class="rfcedit-file-size">
                              {{ ((ev.size or 0) / 1024)|round(1) }} KB
                            </div>
                          </div>
                        </div>

                        <div class="d-flex gap-2 flex-wrap">
                          <a href="{{ url_for('rfc_evidencia_view', evi_id=ev.id, next='rfc_edit', rfc_id=item.id) }}"
                             class="btn btn-info btn-sm rounded-pill text-white fw-bold">
                            Ver
                          </a>

                          <form method="post"
                                action="{{ url_for('rfc_evidencia_delete', evi_id=ev.id) }}"
                                style="display:inline;"
                                onsubmit="return confirm('¿Eliminar esta evidencia?');">
                            <button type="submit"
                                    class="btn btn-danger btn-sm rounded-pill fw-bold">
                              Eliminar
                            </button>
                          </form>
                        </div>
                      </div>
                    {% endfor %}
                  </div>
                {% else %}
                  <div class="rfcedit-empty-box">
                    No hay evidencias registradas para esta solicitud RFC.
                  </div>
                {% endif %}
              </div>

            <div class="rfcedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>

              <a href="{{ url_for('rfc_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold rfcedit-cancel-btn">
                Cancelar
              </a>
            </div>

          </form>

        </div>
      </div>
    </div>

    <script>
      function removeDynamicBlock(btn){
        const block = btn.closest('.dynamic-block');
        if (block) block.remove();
      }

      function addRiesgoRow(data = {}) {
        const container = document.getElementById('riesgos-container');
        const div = document.createElement('div');
        div.className = 'dynamic-block border rounded p-3 mb-3 bg-light';
        div.innerHTML = `
          <div class="d-flex justify-content-between align-items-center mb-2">
            <strong>Registro evaluación de riesgo</strong>
            <button type="button" class="btn btn-outline-danger btn-sm rounded-pill" onclick="removeDynamicBlock(this)">Eliminar</button>
          </div>
          <div class="row g-3">
            <div class="col-md-4">
              <label class="form-label">Sistema procedente</label>
              <textarea name="sistema_procedente[]" class="form-control" rows="2">${data.sistema_procedente || ''}</textarea>
            </div>
            <div class="col-md-4">
              <label class="form-label">Riesgo</label>
              <textarea name="riesgo[]" class="form-control" rows="2">${data.riesgo || ''}</textarea>
            </div>
            <div class="col-md-4">
              <label class="form-label">Impacto</label>
              <textarea name="impacto[]" class="form-control" rows="2">${data.impacto || ''}</textarea>
            </div>
            <div class="col-md-6">
              <label class="form-label">Controles a aplicar</label>
              <textarea name="controles_aplicar[]" class="form-control" rows="2">${data.controles_aplicar || ''}</textarea>
            </div>
            <div class="col-md-6">
              <label class="form-label">Responsable</label>
              <textarea name="responsable_riesgo[]" class="form-control" rows="2">${data.responsable_riesgo || ''}</textarea>
            </div>
          </div>
        `;
        container.appendChild(div);
      }

      function addPlanPruebasRow(data = {}) {
        const container = document.getElementById('plan-pruebas-container');
        const div = document.createElement('div');
        div.className = 'dynamic-block border rounded p-3 mb-3 bg-light';
        div.innerHTML = `
          <div class="d-flex justify-content-between align-items-center mb-2">
            <strong>Registro plan de pruebas</strong>
            <button type="button" class="btn btn-outline-danger btn-sm rounded-pill" onclick="removeDynamicBlock(this)">Eliminar</button>
          </div>
          <div class="row g-3">
            <div class="col-md-4">
              <label class="form-label">Actividad</label>
              <textarea name="plan_pruebas_actividad[]" class="form-control" rows="2">${data.actividad || ''}</textarea>
            </div>
            <div class="col-md-4">
              <label class="form-label">Fecha/hora inicio</label>
              <input type="datetime-local" name="plan_pruebas_fecha_inicio[]" class="form-control" value="${data.fecha_inicio || ''}">
            </div>
            <div class="col-md-4">
              <label class="form-label">Fecha/hora fin</label>
              <input type="datetime-local" name="plan_pruebas_fecha_fin[]" class="form-control" value="${data.fecha_fin || ''}">
            </div>
            <div class="col-md-4">
              <label class="form-label">Responsable</label>
              <textarea name="plan_pruebas_responsable[]" class="form-control" rows="2">${data.responsable || ''}</textarea>
            </div>
            <div class="col-md-4">
              <label class="form-label">Entregables</label>
              <textarea name="plan_pruebas_entregables[]" class="form-control" rows="2">${data.entregables || ''}</textarea>
            </div>
            <div class="col-md-4">
              <label class="form-label">Acciones a seguir</label>
              <textarea name="plan_pruebas_acciones[]" class="form-control" rows="2">${data.acciones || ''}</textarea>
            </div>
          </div>
        `;
        container.appendChild(div);
      }

      function addRollbackRow(data = {}) {
        const container = document.getElementById('rollback-container');
        const div = document.createElement('div');
        div.className = 'dynamic-block border rounded p-3 mb-3 bg-light';
        div.innerHTML = `
          <div class="d-flex justify-content-between align-items-center mb-2">
            <strong>Registro rollback</strong>
            <button type="button" class="btn btn-outline-danger btn-sm rounded-pill" onclick="removeDynamicBlock(this)">Eliminar</button>
          </div>
          <div class="row g-3">
            <div class="col-md-4">
              <label class="form-label">Actividad</label>
              <textarea name="rollback_actividad[]" class="form-control" rows="2">${data.actividad || ''}</textarea>
            </div>
            <div class="col-md-4">
              <label class="form-label">Responsable</label>
              <textarea name="rollback_responsable[]" class="form-control" rows="2">${data.responsable || ''}</textarea>
            </div>
            <div class="col-md-4">
              <label class="form-label">Ejecución y seguimiento</label>
              <textarea name="rollback_ejecucion[]" class="form-control" rows="2">${data.ejecucion || ''}</textarea>
            </div>
          </div>
        `;
        container.appendChild(div);
      }

      function addImplementacionRow(data = {}) {
        const container = document.getElementById('implementacion-container');
        const div = document.createElement('div');
        div.className = 'dynamic-block border rounded p-3 mb-3 bg-light';
        div.innerHTML = `
          <div class="d-flex justify-content-between align-items-center mb-2">
            <strong>Registro implementación</strong>
            <button type="button" class="btn btn-outline-danger btn-sm rounded-pill" onclick="removeDynamicBlock(this)">Eliminar</button>
          </div>
          <div class="row g-3">
            <div class="col-md-4">
              <label class="form-label">Actividad</label>
              <textarea name="impl_actividad[]" class="form-control" rows="2">${data.actividad || ''}</textarea>
            </div>
            <div class="col-md-4">
              <label class="form-label">Responsable</label>
              <textarea name="impl_responsable[]" class="form-control" rows="2">${data.responsable || ''}</textarea>
            </div>
            <div class="col-md-4">
              <label class="form-label">Fecha</label>
              <input type="date" name="impl_fecha[]" class="form-control" value="${data.fecha || ''}">
            </div>
            <div class="col-md-12">
              <label class="form-label">Ejecución y seguimiento</label>
              <textarea name="impl_ejecucion[]" class="form-control" rows="2">${data.ejecucion || ''}</textarea>
            </div>
          </div>
        `;
        container.appendChild(div);
      }

      const riesgosData = {{ riesgos_data|tojson }};
      const planesData = {{ planes_data|tojson }};
      const rollbacksData = {{ rollbacks_data|tojson }};
      const implementacionesData = {{ implementaciones_data|tojson }};

      window.addEventListener('DOMContentLoaded', () => {
        if (riesgosData.length) { riesgosData.forEach(r => addRiesgoRow(r)); } else { addRiesgoRow(); }
        if (planesData.length) { planesData.forEach(p => addPlanPruebasRow(p)); } else { addPlanPruebasRow(); }
        if (rollbacksData.length) { rollbacksData.forEach(r => addRollbackRow(r)); } else { addRollbackRow(); }
        if (implementacionesData.length) { implementacionesData.forEach(i => addImplementacionRow(i)); } else { addImplementacionRow(); }

        fillCargoDesdeArea('responsable_solicitud_id','responsable_solicitud_cargo');
        fillCargoDesdeArea('revisa_persona_id','revisa_cargo');
        fillCargoDesdeArea('aprueba_persona_id','aprueba_cargo');
        fillCargoDesdeArea('implementa_persona_id','implementa_cargo');
      });

      function fillCargoDesdeArea(selectId, cargoInputId){
        const sel = document.getElementById(selectId);
        const opt = sel && sel.selectedOptions && sel.selectedOptions[0];
        const cargo = opt ? (opt.getAttribute('data-cargo') || '') : '';
        const inpCar = document.getElementById(cargoInputId);
        if (inpCar) inpCar.value = cargo;
      }
    </script>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .rfcedit-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .rfcedit-header-card{
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

      .rfcedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .rfcedit-header-overlay{
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

      .rfcedit-header-overlay::before{
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

      .rfcedit-header-text{
        max-width:1200px;
        width:100%;
        display:block;
        transform:none;
      }

      .rfcedit-header-text::before{
        content:"SGSI · Edición de Cambio / RFC";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .rfcedit-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .rfcedit-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .rfcedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .rfcedit-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .rfcedit-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .rfcedit-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .rfcedit-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .rfcedit-card-body{
        padding:18px;
      }

      .rfcedit-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .rfcedit-card .form-control,
      .rfcedit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .rfcedit-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .rfcedit-card .form-control:focus,
      .rfcedit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .rfcedit-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .rfcedit-subsection-title{
        font-weight:900;
        font-size:.82rem;
        color:#25324a;
        padding:9px 12px;
        background:#f8fbff;
        border-radius:12px;
        border:1px solid #dbe6f4;
        margin-bottom:10px;
      }

      .rfcedit-dynamic-block{
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%) !important;
        border:1px solid #dbe6f4 !important;
        border-radius:14px !important;
        box-shadow:0 6px 14px rgba(15,23,42,.08);
        padding:12px !important;
      }

      .rfcedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
      }

      .rfcedit-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .rfcedit-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .rfcedit-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .badge-prio-alta,
      .badge-prio-media,
      .badge-prio-baja{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .badge-prio-alta{ background:#e74c3c; color:#fff; }
      .badge-prio-media{ background:#f1c40f; color:#111; }
      .badge-prio-baja{ background:#2ecc71; color:#fff; }

      @media (max-width:992px){
        .rfcedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .rfcedit-header-card{
          min-height:88px;
        }

        .rfcedit-title{
          font-size:1.20rem;
        }

        .rfcedit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .rfcedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .rfcedit-header-overlay::before{
          margin:0;
        }

        .rfcedit-header-actions .btn,
        .rfcedit-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        item=item,
        areas=areas,
        riesgos_data=riesgos_data,
        planes_data=planes_data,
        rollbacks_data=rollbacks_data,
        implementaciones_data=implementaciones_data,
        impl_general=impl_general
    )
    
    return render_template_string(BASE, content=Markup(inner))


# =========================
# Evidencias RFC - archivo real
# =========================
@app.route('/rfc/evidencia/<int:evi_id>/file')
@login_required
def rfc_evidencia_file(evi_id):
    evi = CambioRFCEvidencia.query.get_or_404(evi_id)
    fullpath = os.path.join(app.config['UPLOAD_RFC_DIR'], evi.filename)

    if not os.path.isfile(fullpath):
        abort(404)

    return send_file(
        fullpath,
        mimetype=evi.mime or 'application/pdf',
        as_attachment=False,
        download_name=evi.original_name or evi.filename,
        conditional=True
    )


# =========================
# Evidencias RFC - visor elegante
# =========================
@app.route('/rfc/evidencia/<int:evi_id>/view')
@login_required
def rfc_evidencia_view(evi_id):
    evi = CambioRFCEvidencia.query.get_or_404(evi_id)

    path = os.path.join(app.config['UPLOAD_RFC_DIR'], evi.filename)
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
    rfc_id = request.args.get('rfc_id', type=int) or evi.rfc_id

    if next_ep == 'rfc_edit' and rfc_id:
        back_url = url_for('rfc_edit', id=rfc_id)
        back_label = '⬅ Volver a Editar RFC'
    elif next_ep == 'rfc_view' and rfc_id:
        back_url = url_for('rfc_view', id=rfc_id)
        back_label = '⬅ Volver al RFC'
    elif next_ep == 'rfc_matriz':
        back_url = url_for('rfc_matriz')
        back_label = '⬅ Volver a la Matriz RFC'
    elif next_ep == 'rfc_menu':
        back_url = url_for('rfc_menu')
        back_label = '⬅ Volver al Menú RFC'
    else:
        if rfc_id:
            back_url = url_for('rfc_view', id=rfc_id)
            back_label = '⬅ Volver al RFC'
        else:
            back_url = request.referrer or url_for('rfc_menu')
            back_label = '⬅ Volver'

    # =========================
    # Conversión Office -> PDF
    # =========================
    pdf_converted_name = None
    if is_office:
        try:
            converted_dir = app.config.get(
                'UPLOAD_RFC_CONVERTED_DIR',
                os.path.join(app.root_path, 'static', 'converted_rfc_evidencias')
            )
            os.makedirs(converted_dir, exist_ok=True)

            pdf_converted_path = ensure_pdf_from_office(path, output_dir=converted_dir)

            if pdf_converted_path and os.path.isfile(pdf_converted_path):
                pdf_converted_name = os.path.basename(pdf_converted_path)
        except Exception:
            pdf_converted_name = None

    inner_html = """
    <div class="rfcevi-shell">

      <div class="rfcevi-header-actions">
        <a href="{{ back_url }}"
           class="btn rounded-pill px-4 py-2 fw-bold rfcevi-back-btn">
          {{ back_label }}
        </a>

        <div class="rfcevi-file-pill" title="{{ original_name }}">
          📎 {{ original_name }}
        </div>
      </div>

      <div class="rfcevi-card">
        <div class="rfcevi-card-body">

          {% if is_pdf %}
            <div class="rfcevi-pdf-container">
              <iframe id="pdfFrame"
                      src="{{ url_for('rfc_evidencia_file', evi_id=evi_id) }}#zoom=page-width"
                      title="Visor PDF"></iframe>
            </div>

          {% elif pdf_converted_name %}
            <div class="rfcevi-pdf-container">
              <iframe id="pdfFrame"
                      src="{{ url_for('rfc_evidencia_convertido', filename=pdf_converted_name) }}#zoom=page-width"
                      title="Visor PDF convertido"></iframe>
            </div>

            <div class="rfcevi-extra-actions">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('rfc_evidencia_file', evi_id=evi_id) }}">
                Abrir archivo original
              </a>
            </div>

          {% elif is_image %}
            <div class="text-center p-3">
              <img src="{{ url_for('rfc_evidencia_file', evi_id=evi_id) }}"
                   alt="{{ original_name }}"
                   class="img-fluid rounded-4 shadow-sm"
                   style="max-height: 78vh; object-fit: contain;">
            </div>

          {% elif is_office %}
            <div class="alert alert-warning m-2 rounded-4">
              No fue posible generar una vista previa interna del archivo Office.
              Verifica que LibreOffice esté instalado en el servidor.
            </div>

            <div class="rfcevi-extra-actions">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('rfc_evidencia_file', evi_id=evi_id) }}">
                Abrir / descargar archivo original
              </a>
            </div>

          {% else %}
            <div class="alert alert-info m-2 rounded-4">
              Este tipo de archivo (<b>{{ ext }}</b>) no se puede previsualizar.
              Puedes abrirlo o descargarlo.
            </div>

            <div class="rfcevi-extra-actions">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('rfc_evidencia_file', evi_id=evi_id) }}">
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

      .rfcevi-shell{
        width:96%;
        max-width:1500px;
        margin:22px auto 30px auto;
      }

      .rfcevi-header-actions{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        flex-wrap:wrap;
        margin-bottom:16px;
      }

      .rfcevi-back-btn{
        background:#ffffff;
        color:#000000;
        border:2px solid #ffffff;
        box-shadow:0 4px 10px rgba(0,0,0,.10);
      }

      .rfcevi-back-btn:hover{
        background:#f3f4f6;
        color:#000000;
        border-color:#f3f4f6;
      }

      .rfcevi-file-pill{
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

      .rfcevi-card{
        background:rgba(255,255,255,.88)!important;
        border-radius:18px;
        backdrop-filter:blur(6px);
        box-shadow:0 10px 24px rgba(0,0,0,.18);
        overflow:hidden;
      }

      .rfcevi-card-body{
        padding:8px 7px;
      }

      .rfcevi-pdf-container{
        height:min(82vh,1000px);
        min-height:600px;
        width:100%;
      }

      .rfcevi-pdf-container iframe{
        width:100%;
        height:100%;
        border:1px solid #dee2e6;
        border-radius:16px;
        background:#fff;
      }

      .rfcevi-extra-actions{
        text-align:center;
        margin-top:14px;
      }

      @media (max-width:992px){
        .rfcevi-shell{
          width:98%;
          margin:14px auto 24px auto;
        }

        .rfcevi-header-actions{
          flex-direction:column;
          align-items:stretch;
        }

        .rfcevi-file-pill{
          max-width:100%;
        }

        .rfcevi-card-body{
          padding:10px;
        }

        .rfcevi-pdf-container{
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


@app.route('/rfc/evidencia/convertido/<path:filename>')
@login_required
def rfc_evidencia_convertido(filename):
    converted_dir = app.config.get(
        'UPLOAD_RFC_CONVERTED_DIR',
        os.path.join(app.root_path, 'static', 'converted_rfc_evidencias')
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

# =========================
# Borrado RFC
# =========================
@app.route('/rfc/evidencia/<int:evi_id>/delete', methods=['POST'])
@login_required
def rfc_evidencia_delete(evi_id):
    evi = CambioRFCEvidencia.query.get_or_404(evi_id)
    rfc_id = evi.rfc_id
    path = os.path.join(app.config['UPLOAD_RFC_DIR'], evi.filename)
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
    db.session.delete(evi)
    db.session.commit()
    flash("Evidencia eliminada.", "success")
    return redirect(url_for('rfc_edit', id=rfc_id))

@app.route('/rfc/delete/<int:id>')
@login_required
def rfc_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Gestión de Cambios (RFC)")
    ):
        flash("No tiene permiso para eliminar cmabios.", "danger")
        return redirect(url_for('rfc_matriz'))
    
    item = CambioRFCRegistro.query.get_or_404(id)
    # borrar archivos físicos
    for ev in list(item.evidencias or []):
        p = os.path.join(app.config['UPLOAD_RFC_DIR'], ev.filename)
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass
        db.session.delete(ev)

    db.session.delete(item)
    db.session.commit()
    flash("Solicitud de cambio RFC eliminada.", "success")
    return redirect(url_for('rfc_matriz'))


# =========================
# Ver RFC
# =========================
@app.route('/rfc/view/<int:id>')
@login_required
def rfc_view(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Gestión de Cambios (RFC)"):
            flash("No tiene permiso para visualizar RFC.", "danger")
            return redirect(url_for('rfc_menu'))
        read_only = False

    item = CambioRFCRegistro.query.get_or_404(id)

    riesgos = item.riesgos or []
    planes = item.planes_pruebas or []
    rollbacks = item.rollbacks or []
    implementaciones = item.implementaciones or []
    evidencias = item.evidencias or []

    impl_general = {
        'tiempo_monitoreo': '',
        'fecha_aprobacion': '',
        'fecha_tentativa_cierre': '',
        'fecha_real_cierre': '',
        'observaciones': ''
    }

    if implementaciones:
        primera_impl = implementaciones[0]
        impl_general = {
            'tiempo_monitoreo': primera_impl.tiempo_monitoreo or '',
            'fecha_aprobacion': primera_impl.fecha_aprobacion or '',
            'fecha_tentativa_cierre': primera_impl.fecha_tentativa_cierre or '',
            'fecha_real_cierre': primera_impl.fecha_real_cierre or '',
            'observaciones': primera_impl.observaciones or ''
        }
        
    evidencias = item.evidencias or []

    def fvalor(v):
        return v if v not in (None, '') else '—'

    html = """
    <div class="rfcdet-shell">

      <!-- CABECERA -->
      <div class="rfcdet-header-card">
        <div class="rfcdet-header-overlay">
          <div class="rfcdet-header-text">
            <h3 class="rfcdet-title m-0">Detalle de la Solicitud de Cambio (RFC)</h3>
            <div class="rfcdet-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <!-- BOTONES -->
      <div class="rfcdet-header-actions">
        <a href="{{ url_for('rfc_matriz') }}"
           class="btn rounded-pill px-4 fw-bold rfcdet-back-btn">
          ⬅ Volver a la Matriz RFC
        </a>


        {% if not read_only %}
          <a href="{{ url_for('rfc_edit', id=item.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <!-- TARJETA -->
      <div class="rfcdet-card">
        <div class="rfcdet-card-body">

          <!-- 1. Información general -->
          <div class="rfcdet-section">
            <div class="rfcdet-section-title">Información general</div>
            <div class="row g-3">

              <div class="col-md-3">
                <div class="rfcdet-field rfcdet-field-compact">
                  <div class="rfcdet-label">Ticket o No. de solicitud</div>
                  <div class="rfcdet-value rfcdet-value-compact">{{ fvalor(item.ticket) }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="rfcdet-field rfcdet-field-compact">
                  <div class="rfcdet-label">Fecha solicitud</div>
                  <div class="rfcdet-value rfcdet-value-compact">{{ fvalor(item.fecha_solicitud) }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="rfcdet-field">
                  <div class="rfcdet-label">Responsable de la solicitud</div>
                  <div class="rfcdet-value">{{ fvalor(item.responsable_solicitud_nombre) }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="rfcdet-field">
                  <div class="rfcdet-label">Cargo responsable</div>
                  <div class="rfcdet-value">{{ fvalor(item.responsable_solicitud_cargo) }}</div>
                </div>
              </div>

            </div>
          </div>

          <!-- 2. Información del cambio -->
          <div class="rfcdet-section">
            <div class="rfcdet-section-title">Información del cambio</div>
            <div class="row g-3">

              <div class="col-md-4">
                <div class="rfcdet-field rfcdet-field-compact">
                  <div class="rfcdet-label">Ambiente</div>
                  <div class="rfcdet-value rfcdet-value-compact">{{ fvalor(item.ambiente) }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="rfcdet-field rfcdet-field-compact">
                  <div class="rfcdet-label">Tipo de cambio</div>
                  <div class="rfcdet-value rfcdet-value-compact">{{ fvalor(item.tipo_cambio) }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="rfcdet-field rfcdet-field-compact">
                  <div class="rfcdet-label">Prioridad</div>
                  <div class="rfcdet-value rfcdet-value-compact">
                    {% if item.prioridad == 'Alta' %}
                      <span class="badge badge-prio-alta">Alta</span>
                    {% elif item.prioridad == 'Media' %}
                      <span class="badge badge-prio-media">Media</span>
                    {% elif item.prioridad == 'Baja' %}
                      <span class="badge badge-prio-baja">Baja</span>
                    {% else %}
                      <span class="badge bg-secondary">—</span>
                    {% endif %}
                  </div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="rfcdet-field">
                  <div class="rfcdet-label">Descripción</div>
                  <div class="rfcdet-value rfcdet-value-lg">{{ fvalor(item.descripcion) }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="rfcdet-field">
                  <div class="rfcdet-label">Antecedentes</div>
                  <div class="rfcdet-value">{{ fvalor(item.antecedentes) }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="rfcdet-field">
                  <div class="rfcdet-label">Objetivo</div>
                  <div class="rfcdet-value">{{ fvalor(item.objetivo) }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="rfcdet-field">
                  <div class="rfcdet-label">Alcance</div>
                  <div class="rfcdet-value">{{ fvalor(item.alcance) }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="rfcdet-field">
                  <div class="rfcdet-label">Partes interesadas impactadas</div>
                  <div class="rfcdet-value">{{ fvalor(item.partes_interesadas) }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="rfcdet-field">
                  <div class="rfcdet-label">Recursos necesarios</div>
                  <div class="rfcdet-value">{{ fvalor(item.recursos_necesarios) }}</div>
                </div>
              </div>

            </div>
          </div>

          <!-- 3. Evaluación de riesgos -->
          <div class="rfcdet-section">
            <div class="rfcdet-section-title">Evaluación de riesgos</div>

            {% if riesgos %}
              <div class="rfcdet-table-wrap">
                <div class="table-responsive">
                  <table class="table table-bordered table-sm align-middle rfcdet-table mb-0">
                    <thead>
                      <tr>
                        <th>Sistema procedente</th>
                        <th>Riesgo</th>
                        <th>Impacto</th>
                        <th>Controles a aplicar</th>
                        <th>Responsable</th>
                      </tr>
                    </thead>
                    <tbody>
                      {% for r in riesgos %}
                        <tr>
                          <td>{{ fvalor(r.sistema_procedente) }}</td>
                          <td>{{ fvalor(r.riesgo) }}</td>
                          <td>{{ fvalor(r.impacto) }}</td>
                          <td>{{ fvalor(r.controles_aplicar) }}</td>
                          <td>{{ fvalor(r.responsable_riesgo) }}</td>
                        </tr>
                      {% endfor %}
                    </tbody>
                  </table>
                </div>
              </div>
            {% else %}
              <div class="rfcdet-empty-box">No hay riesgos registrados.</div>
            {% endif %}
          </div>

          <!-- 4. Plan de pruebas -->
          <div class="rfcdet-section">
            <div class="rfcdet-section-title">Plan de pruebas (si aplica)</div>

            {% if planes %}
              <div class="rfcdet-table-wrap">
                <div class="table-responsive">
                  <table class="table table-bordered table-sm align-middle rfcdet-table mb-0">
                    <thead>
                      <tr>
                        <th>Actividad</th>
                        <th>Fecha/hora inicio</th>
                        <th>Fecha/hora fin</th>
                        <th>Responsable</th>
                        <th>Entregables</th>
                        <th>Acciones a seguir</th>
                      </tr>
                    </thead>
                    <tbody>
                      {% for p in planes %}
                        <tr>
                          <td>{{ fvalor(p.actividad) }}</td>
                          <td>{{ fvalor(p.fecha_inicio) }}</td>
                          <td>{{ fvalor(p.fecha_fin) }}</td>
                          <td>{{ fvalor(p.responsable) }}</td>
                          <td>{{ fvalor(p.entregables) }}</td>
                          <td>{{ fvalor(p.acciones) }}</td>
                        </tr>
                      {% endfor %}
                    </tbody>
                  </table>
                </div>
              </div>
            {% else %}
              <div class="rfcdet-empty-box">No hay plan de pruebas registrado.</div>
            {% endif %}
          </div>

          <!-- 5. Plan de marcha atrás -->
          <div class="rfcdet-section">
            <div class="rfcdet-section-title">Plan de Marcha Atrás (Rollback)</div>

            {% if rollbacks %}
              <div class="rfcdet-table-wrap">
                <div class="table-responsive">
                  <table class="table table-bordered table-sm align-middle rfcdet-table mb-0">
                    <thead>
                      <tr>
                        <th>Actividad</th>
                        <th>Responsable</th>
                        <th>Ejecución y seguimiento</th>
                      </tr>
                    </thead>
                    <tbody>
                      {% for r in rollbacks %}
                        <tr>
                          <td>{{ fvalor(r.actividad) }}</td>
                          <td>{{ fvalor(r.responsable) }}</td>
                          <td>{{ fvalor(r.ejecucion) }}</td>
                        </tr>
                      {% endfor %}
                    </tbody>
                  </table>
                </div>
              </div>
            {% else %}
              <div class="rfcdet-empty-box">No hay rollback registrado.</div>
            {% endif %}
          </div>

          <!-- 6. Actividades implementadas -->
          <div class="rfcdet-section">
            <div class="rfcdet-section-title">Actividades implementadas del cambio</div>

            {% if implementaciones %}
              <div class="rfcdet-table-wrap mb-3">
                <div class="table-responsive">
                  <table class="table table-bordered table-sm align-middle rfcdet-table mb-0">
                    <thead>
                      <tr>
                        <th>Actividad</th>
                        <th>Responsable</th>
                        <th>Fecha</th>
                        <th>Ejecución y seguimiento</th>
                      </tr>
                    </thead>
                    <tbody>
                      {% for i in implementaciones %}
                        <tr>
                          <td>{{ fvalor(i.actividad) }}</td>
                          <td>{{ fvalor(i.responsable) }}</td>
                          <td>{{ fvalor(i.fecha) }}</td>
                          <td>{{ fvalor(i.ejecucion) }}</td>
                        </tr>
                      {% endfor %}
                    </tbody>
                  </table>
                </div>
              </div>

              <div class="row g-3">
                <div class="col-md-3">
                  <div class="rfcdet-field rfcdet-field-compact">
                    <div class="rfcdet-label">Tiempo estimado monitoreo</div>
                    <div class="rfcdet-value rfcdet-value-compact">{{ fvalor(impl_general.tiempo_monitoreo) }}</div>
                  </div>
                </div>

                <div class="col-md-3">
                  <div class="rfcdet-field rfcdet-field-compact">
                    <div class="rfcdet-label">Fecha aprobación</div>
                    <div class="rfcdet-value rfcdet-value-compact">{{ fvalor(impl_general.fecha_aprobacion) }}</div>
                  </div>
                </div>

                <div class="col-md-3">
                  <div class="rfcdet-field rfcdet-field-compact">
                    <div class="rfcdet-label">Fecha tentativa cierre</div>
                    <div class="rfcdet-value rfcdet-value-compact">{{ fvalor(impl_general.fecha_tentativa_cierre) }}</div>
                  </div>
                </div>

                <div class="col-md-3">
                  <div class="rfcdet-field rfcdet-field-compact">
                    <div class="rfcdet-label">Fecha real cierre</div>
                    <div class="rfcdet-value rfcdet-value-compact">{{ fvalor(impl_general.fecha_real_cierre) }}</div>
                  </div>
                </div>

                <div class="col-md-12">
                  <div class="rfcdet-field">
                    <div class="rfcdet-label">Observaciones</div>
                    <div class="rfcdet-value">{{ fvalor(impl_general.observaciones) }}</div>
                  </div>
                </div>
              </div>

            {% else %}
              <div class="rfcdet-empty-box">No hay actividades implementadas registradas.</div>
            {% endif %}
          </div>

          <!-- 7. Aprobación del cambio -->
          <div class="rfcdet-section">
            <div class="rfcdet-section-title">Aprobación del cambio</div>

            <div class="row g-3 mb-2">
              <div class="col-md-4">
                <div class="rfcdet-field rfcdet-field-compact">
                  <div class="rfcdet-label">¿Se requiere realizar ajustes?</div>
                  <div class="rfcdet-value rfcdet-value-compact">{{ fvalor(item.ajustes_requeridos) }}</div>
                </div>
              </div>

              <div class="col-md-8">
                <div class="rfcdet-field">
                  <div class="rfcdet-label">Cambios requeridos</div>
                  <div class="rfcdet-value">{{ fvalor(item.cambios_requeridos) }}</div>
                </div>
              </div>
            </div>

            <div class="rfcdet-subsection-title">7.1 Revisa</div>
            <div class="row g-3 mb-3">
              <div class="col-md-3">
                <div class="rfcdet-field"><div class="rfcdet-label">Nombre</div><div class="rfcdet-value">{{ fvalor(item.revisa_nombre) }}</div></div>
              </div>
              <div class="col-md-3">
                <div class="rfcdet-field"><div class="rfcdet-label">Cargo</div><div class="rfcdet-value">{{ fvalor(item.revisa_cargo) }}</div></div>
              </div>
              <div class="col-md-3">
                <div class="rfcdet-field"><div class="rfcdet-label">Fecha</div><div class="rfcdet-value">{{ fvalor(item.revisa_fecha) }}</div></div>
              </div>
              <div class="col-md-12">
                <div class="rfcdet-field"><div class="rfcdet-label">Observaciones</div><div class="rfcdet-value">{{ fvalor(item.revisa_observaciones) }}</div></div>
              </div>
            </div>

            <div class="rfcdet-subsection-title">7.2 Aprueba (Comité de cambios)</div>
            <div class="row g-3 mb-3">
              <div class="col-md-3">
                <div class="rfcdet-field"><div class="rfcdet-label">Nombre</div><div class="rfcdet-value">{{ fvalor(item.aprueba_nombre) }}</div></div>
              </div>
              <div class="col-md-3">
                <div class="rfcdet-field"><div class="rfcdet-label">Cargo</div><div class="rfcdet-value">{{ fvalor(item.aprueba_cargo) }}</div></div>
              </div>
              <div class="col-md-3">
                <div class="rfcdet-field"><div class="rfcdet-label">Fecha</div><div class="rfcdet-value">{{ fvalor(item.aprueba_fecha) }}</div></div>
              </div>
              <div class="col-md-12">
                <div class="rfcdet-field"><div class="rfcdet-label">Observaciones</div><div class="rfcdet-value">{{ fvalor(item.aprueba_observaciones) }}</div></div>
              </div>
            </div>

            <div class="rfcdet-subsection-title">7.3 Implementa</div>
            <div class="row g-3">
              <div class="col-md-3">
                <div class="rfcdet-field"><div class="rfcdet-label">Nombre</div><div class="rfcdet-value">{{ fvalor(item.implementa_nombre) }}</div></div>
              </div>
              <div class="col-md-3">
                <div class="rfcdet-field"><div class="rfcdet-label">Cargo</div><div class="rfcdet-value">{{ fvalor(item.implementa_cargo) }}</div></div>
              </div>
              <div class="col-md-3">
                <div class="rfcdet-field"><div class="rfcdet-label">Fecha</div><div class="rfcdet-value">{{ fvalor(item.implementa_fecha) }}</div></div>
              </div>
              <div class="col-md-12">
                <div class="rfcdet-field"><div class="rfcdet-label">Observaciones</div><div class="rfcdet-value">{{ fvalor(item.implementa_observaciones) }}</div></div>
              </div>
            </div>
          </div>

          <!-- 8. Seguimiento -->
          <div class="rfcdet-section">
            <div class="rfcdet-section-title">Seguimiento del cambio</div>
            <div class="row g-3">
              <div class="col-md-4">
                <div class="rfcdet-field rfcdet-field-compact">
                  <div class="rfcdet-label">¿El cambio fue eficaz?</div>
                  <div class="rfcdet-value rfcdet-value-compact">{{ fvalor(item.cambio_eficaz) }}</div>
                </div>
              </div>

              <div class="col-md-8">
                <div class="rfcdet-field">
                  <div class="rfcdet-label">Descripción del seguimiento</div>
                  <div class="rfcdet-value">{{ fvalor(item.descripcion_seguimiento) }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 9. Evidencias -->
          <div class="rfcdet-section">
            <div class="rfcdet-section-title">Evidencias</div>

            {% if evidencias %}
              <div class="rfcdet-files-grid">
                {% for ev in evidencias %}
                  <div class="rfcdet-file-card">
                    <div class="rfcdet-file-left">
                      <div class="rfcdet-file-icon">PDF</div>
                      <div class="rfcdet-file-meta">
                        <div class="rfcdet-file-label">Evidencia</div>
                        <a href="{{ url_for('rfc_evidencia_view', evi_id=ev.id, next='rfc_view', rfc_id=item.id) }}">
                           class="rfcdet-file-name">
                          {{ ev.original_name }}
                        </a>
                        <div class="rfcdet-file-size">{{ (ev.size or 0)//1024 }} KB</div>
                      </div>
                    </div>
                    <div>
                      <a href="{{ url_for('rfc_evidencia_view', evi_id=ev.id, next='rfc_view', rfc_id=item.id) }}">
                        Ver archivo
                      </a>
                    </div>
                  </div>
                {% endfor %}
              </div>
            {% else %}
              <div class="rfcdet-empty-box">No hay evidencias registradas.</div>
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

      .rfcdet-shell{
        width:96%;
        max-width:1200px;
        margin:10px auto 24px auto;
      }

      .rfcdet-header-card{
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

      .rfcdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .rfcdet-header-overlay{
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

      .rfcdet-header-overlay::before{
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

      .rfcdet-header-text{
        max-width:1000px;
        width:100%;
        transform:none;
      }

      .rfcdet-header-text::before{
        content:"SGSI · Detalle de Cambio / RFC";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .rfcdet-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .rfcdet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .rfcdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .rfcdet-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .rfcdet-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .rfcdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .rfcdet-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .rfcdet-card-body{
        padding:18px;
      }

      .rfcdet-section{
        margin-bottom:14px;
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .rfcdet-section:last-child{
        margin-bottom:0;
      }

      .rfcdet-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      .rfcdet-subsection-title{
        font-weight:900;
        font-size:.82rem;
        color:#25324a;
        padding:9px 12px;
        background:#f8fbff;
        border-radius:12px;
        border:1px solid #dbe6f4;
        margin:12px 0 10px 0;
      }

      .rfcdet-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        min-height:78px;
        height:100%;
        display:flex;
        flex-direction:column;
        justify-content:flex-start;
      }

      .rfcdet-field-compact{
        min-height:78px;
        justify-content:center;
        align-items:center;
        text-align:center;
      }

      .rfcdet-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .rfcdet-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .rfcdet-value-lg{
        font-size:.90rem;
        font-weight:900;
        color:#0f172a;
      }

      .rfcdet-value-compact{
        font-weight:900;
        font-size:.80rem;
        line-height:1.2;
      }

      .rfcdet-value .badge,
      .rfcdet-value-compact .badge{
        font-size:.70rem;
        padding:5px 10px;
        border-radius:999px;
        white-space:nowrap;
        display:inline-block;
        font-weight:900;
      }

      .badge-prio-alta,
      .badge-prio-media,
      .badge-prio-baja{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .badge-prio-alta{background:#e74c3c;color:#fff;}
      .badge-prio-media{background:#f1c40f;color:#111;}
      .badge-prio-baja{background:#2ecc71;color:#fff;}

      .rfcdet-section .row.g-3{
        --bs-gutter-x:.8rem;
        --bs-gutter-y:.8rem;
      }

      .rfcdet-table-wrap{
        border:1px solid #dbe6f4;
        border-radius:14px;
        overflow:hidden;
        background:#fff;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .rfcdet-table{
        margin-bottom:0;
      }

      .rfcdet-table thead th{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        font-size:.78rem;
        border-bottom:1px solid #d7dee7 !important;
        padding:9px 8px;
      }

      .rfcdet-table td,
      .rfcdet-table th{
        white-space:normal;
        word-break:break-word;
        vertical-align:top;
        font-size:.78rem;
        padding:9px 8px;
      }

      .rfcdet-table td{
        border-bottom:1px solid #e5edf7;
      }

      .rfcdet-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .rfcdet-table tbody tr:hover{
        background:#eef6ff;
      }

      .rfcdet-files-grid{
        display:grid;
        gap:10px;
      }

      .rfcdet-file-card{
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

      .rfcdet-file-left{
        display:flex;
        align-items:center;
        gap:7px;
        min-width:0;
      }

      .rfcdet-file-icon{
        width:32px;
        height:32px;
        min-width:32px;
        border-radius:11px;
        background:linear-gradient(135deg,#1d4ed8,#60a5fa);
        color:#fff;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:.72rem;
        font-weight:900;
        box-shadow:0 6px 14px rgba(29,78,216,.20);
      }

      .rfcdet-file-meta{
        min-width:0;
      }

      .rfcdet-file-label{
        font-size:.70rem;
        color:#475569;
        font-weight:900;
      }

      .rfcdet-file-name{
        display:block;
        font-size:.78rem;
        font-weight:900;
        color:#1d4ed8;
        text-decoration:none;
        word-break:break-word;
      }

      .rfcdet-file-name:hover{
        text-decoration:underline;
      }

      .rfcdet-file-size{
        font-size:.70rem;
        color:#475569;
        margin-top:2px;
      }

      .rfcdet-empty-box{
        background:#f8fbff;
        border:1px dashed #b8cce8;
        border-radius:14px;
        padding:16px;
        text-align:center;
        color:#475569;
        font-size:.82rem;
        font-weight:800;
      }

      .form-control,
      .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .form-control:focus,
      .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }

      @media (max-width:992px){
        .rfcdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .rfcdet-header-card{
          min-height:88px;
        }

        .rfcdet-title{
          font-size:1.20rem;
        }

        .rfcdet-card-body{
          padding:8px 7px;
        }

        .rfcdet-section{
          padding:12px;
        }

        .rfcdet-field,
        .rfcdet-field-compact{
          min-height:72px;
        }
      }

      @media (max-width:768px){
        .rfcdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .rfcdet-header-overlay::before{
          margin:0;
        }

        .rfcdet-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        item=item,
        riesgos=riesgos,
        planes=planes,
        rollbacks=rollbacks,
        implementaciones=implementaciones,
        evidencias=evidencias,
        impl_general=impl_general,
        read_only=read_only,
        fvalor=fvalor
    )
    return render_template_string(BASE, content=Markup(inner))


# ==========================================================================================================================================
#                                                               Fin Módulo Control de Cambios
# ==========================================================================================================================================

# ============================================================================================================================================
#                                                               Módulo Gestión de Incidentes
# ============================================================================================================================================

import os
import sqlite3
from datetime import datetime
from flask import request, redirect, url_for, flash, render_template_string
from markupsafe import Markup

# ==========================
# DB INCIDENTES SQLITE (instance/incidentes.db)
# ==========================
os.makedirs(app.instance_path, exist_ok=True)
INCIDENTES_DB_PATH = os.path.join(app.instance_path, "incidentes.db")

def get_incidentes_db_connection():
    conn = sqlite3.connect(INCIDENTES_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_incidentes_db():
    os.makedirs(app.instance_path, exist_ok=True)

    conn = sqlite3.connect(INCIDENTES_DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS registro_incidentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_alerta TEXT,
            nombre_alerta TEXT,
            descripcion_alerta TEXT,
            id_incidente TEXT,
            clasificacion_incidente TEXT,
            cargo_responsable TEXT,
            atacante TEXT,
            ubicacion_atacante TEXT,
            tipo_recurso_afectado TEXT,
            nombre_recurso_id TEXT,
            estado TEXT,
            fecha_cierre TEXT,
            descripcion_cierre TEXT,
            principio TEXT,
            prioridad TEXT,
            se_requiere_contencion TEXT,
            fecha_hora_contencion TEXT,
            descripcion_contencion TEXT,
            se_requiere_recuperacion TEXT,
            fecha_hora_recuperacion TEXT,
            descripcion_recuperacion TEXT
        )
    """)

    conn.commit()
    conn.close()

# Crear la base y tabla si no existen
init_incidentes_db()

# ==========================
# ENTRADA DIRECTA — INCIDENTES
# ==========================
@app.route('/incidentes')
@login_required
def incidentes():
    user = User.query.get(session.get('user_id'))

    # Si tienes permiso propio, cambia este nombre
    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Gestión de Cambios (RFC)"):
        flash("No tiene permiso para acceder a Gestión de Incidentes.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('incidentes_matriz'))


# ============================================================================
# AGREGAR INCIDENTE
# ============================================================================

@app.route('/incidentes/nuevo', methods=['GET', 'POST'])
@login_required
def incidentes_nuevo():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Gestión de Cambios (RFC)"):
        flash("No tiene permiso para acceder a Gestión de Incidentes.", "danger")
        return redirect(url_for('menu'))

    solo_lectura = (user.role == 'auditor')
    if solo_lectura:
        flash("Perfil auditor: solo lectura, no puede registrar incidentes.", "warning")
        return redirect(url_for('incidentes_matriz'))

    if request.method == 'POST':
        conn = get_incidentes_db_connection()
        c = conn.cursor()

        raw_fecha_alerta = request.form.get('fecha_alerta') or None
        fecha_alerta = None
        if raw_fecha_alerta:
            try:
                dt = datetime.strptime(raw_fecha_alerta, "%Y-%m-%dT%H:%M")
                fecha_alerta = dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                fecha_alerta = raw_fecha_alerta

        id_incidente = (request.form.get('id_incidente') or '').strip()
        clasificacion_incidente = (request.form.get('clasificacion_incidente') or '').strip()
        cargo_responsable = (request.form.get('cargo_responsable') or '').strip()

        nombre_alerta = (request.form.get('nombre_alerta') or '').strip()
        descripcion_alerta = (request.form.get('descripcion_alerta') or '').strip()
        atacante = (request.form.get('atacante') or '').strip()
        ubicacion_atacante = (request.form.get('ubicacion_atacante') or '').strip()
        tipo_recurso = (request.form.get('tipo_recurso_afectado') or '').strip()
        nombre_recurso_id = (request.form.get('nombre_recurso_id') or '').strip()
        estado = (request.form.get('estado') or '').strip()

        fecha_cierre = request.form.get('fecha_cierre') or None
        descripcion_cierre = (request.form.get('descripcion_cierre') or '').strip()
        principio = (request.form.get('principio') or '').strip()
        prioridad = (request.form.get('prioridad') or '').strip()

        se_requiere_contencion = request.form.get('se_requiere_contencion') or "No"
        raw_fecha_hora_contencion = request.form.get('fecha_hora_contencion') or None
        descripcion_contencion = (request.form.get('descripcion_contencion') or '').strip()

        fecha_hora_contencion = None
        if se_requiere_contencion == "Si" and raw_fecha_hora_contencion:
            try:
                dtc = datetime.strptime(raw_fecha_hora_contencion, "%Y-%m-%dT%H:%M")
                fecha_hora_contencion = dtc.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                fecha_hora_contencion = raw_fecha_hora_contencion
        else:
            fecha_hora_contencion = None
            descripcion_contencion = ""

        se_requiere_recuperacion = request.form.get('se_requiere_recuperacion') or "No"
        raw_fecha_hora_recuperacion = request.form.get('fecha_hora_recuperacion') or None
        descripcion_recuperacion = (request.form.get('descripcion_recuperacion') or '').strip()

        fecha_hora_recuperacion = None
        if se_requiere_recuperacion == "Si" and raw_fecha_hora_recuperacion:
            try:
                dtr = datetime.strptime(raw_fecha_hora_recuperacion, "%Y-%m-%dT%H:%M")
                fecha_hora_recuperacion = dtr.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                fecha_hora_recuperacion = raw_fecha_hora_recuperacion
        else:
            fecha_hora_recuperacion = None
            descripcion_recuperacion = ""

        c.execute("""
            INSERT INTO registro_incidentes (
                fecha_alerta,
                nombre_alerta,
                descripcion_alerta,
                id_incidente,
                clasificacion_incidente,
                cargo_responsable,
                atacante,
                ubicacion_atacante,
                tipo_recurso_afectado,
                nombre_recurso_id,
                estado,
                fecha_cierre,
                descripcion_cierre,
                principio,
                prioridad,
                se_requiere_contencion,
                fecha_hora_contencion,
                descripcion_contencion,
                se_requiere_recuperacion,
                fecha_hora_recuperacion,
                descripcion_recuperacion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fecha_alerta,
            nombre_alerta,
            descripcion_alerta,
            id_incidente,
            clasificacion_incidente,
            cargo_responsable,
            atacante,
            ubicacion_atacante,
            tipo_recurso,
            nombre_recurso_id,
            estado,
            fecha_cierre,
            descripcion_cierre,
            principio,
            prioridad,
            se_requiere_contencion,
            fecha_hora_contencion,
            descripcion_contencion,
            se_requiere_recuperacion,
            fecha_hora_recuperacion,
            descripcion_recuperacion
        ))

        conn.commit()
        conn.close()

        flash("Incidente agregado correctamente.", "success")
        return redirect(url_for('incidentes_matriz'))

    config = MetricConfigIncidentes.query.first()
    clasificaciones_config = []
    if config:
        clasificaciones_config = [fila.clasificacion for fila in config.clasificaciones]

    content = render_template_string("""
    <div class="incadd-shell">

      <div class="incadd-header-card">
        <div class="incadd-header-overlay">
          <div class="incadd-header-text">
            <h3 class="incadd-title m-0">Agregar Incidente de Seguridad</h3>
            <div class="incadd-subtitle">
              Registro y gestión inicial de incidentes de seguridad de la información, incluyendo clasificación, contención, recuperación y cierre
            </div>
          </div>
        </div>
      </div>

      <div class="incadd-header-actions">
        <a href="{{ url_for('incidentes_matriz') }}"
           class="btn rounded-pill px-4 fw-bold incadd-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz de Incidentes
        </a>
      </div>

      <div class="incadd-card">
        <div class="incadd-card-body">
          <form method="POST" class="row g-3">

            <div class="col-12">
              <div class="incadd-section-title">Información general del incidente</div>
            </div>

            <div class="col-md-4">
              <label class="form-label">ID del Incidente</label>
              <input class="form-control" name="id_incidente" placeholder="Ej: INC-2025-001">
            </div>

            <div class="col-md-3">
              <label class="form-label">Fecha de la alerta</label>
              <input type="datetime-local" class="form-control" name="fecha_alerta" required>
            </div>

            <div class="col-md-5">
              <label class="form-label">Nombre de la Alerta</label>
              <input class="form-control" name="nombre_alerta" required>
            </div>

            <div class="col-md-4">
              <label class="form-label">Clasificación del Incidente</label>
              <select name="clasificacion_incidente" class="form-select" required>
                <option value="">Seleccione...</option>
                {% for c in clasificaciones %}
                  <option value="{{ c }}">{{ c }}</option>
                {% endfor %}
              </select>
            </div>

            <div class="col-md-4">
              <label class="form-label">Cargo responsable de la gestión</label>
              <input class="form-control" name="cargo_responsable" placeholder="Ej: Analista SOC N2">
            </div>

            <div class="col-md-4">
              <label class="form-label">Atacante</label>
              <input class="form-control" name="atacante">
            </div>

            <div class="col-md-4">
              <label class="form-label">Ubicación atacante</label>
              <input class="form-control" name="ubicacion_atacante">
            </div>

            <div class="col-md-4">
              <label class="form-label">Tipo Recurso Afectado</label>
              <input class="form-control" name="tipo_recurso_afectado">
            </div>

            <div class="col-md-4">
              <label class="form-label">Nombre Recurso y ID</label>
              <input class="form-control" name="nombre_recurso_id">
            </div>

            <div class="col-md-4">
              <label class="form-label">Estado</label>
              <select name="estado" class="form-select">
                <option value="Abierto">Abierto</option>
                <option value="Cerrado">Cerrado</option>
              </select>
            </div>

            <div class="col-md-4">
              <label class="form-label">Fecha Cierre</label>
              <input type="date" class="form-control" name="fecha_cierre">
            </div>

            <div class="col-md-4">
              <label class="form-label">Principio afectado</label>
              <select name="principio" class="form-select">
                <option value="Confidencialidad">Confidencialidad</option>
                <option value="Integridad">Integridad</option>
                <option value="Disponibilidad">Disponibilidad</option>
              </select>
            </div>

            <div class="col-md-4">
              <label class="form-label">Prioridad (Criticidad del activo)</label>
              <select name="prioridad" class="form-select">
                <option value="Alta">Alta</option>
                <option value="Media">Media</option>
                <option value="Baja">Baja</option>
              </select>
            </div>

            <div class="col-12 mt-3">
              <div class="incadd-section-title">Contención del incidente</div>
            </div>

            <div class="col-md-3">
              <label class="form-label">Se requiere Contención</label>
              <select name="se_requiere_contencion"
                      id="se_requiere_contencion"
                      class="form-select"
                      onchange="toggleContencion()">
                <option value="No" selected>No</option>
                <option value="Si">Sí</option>
              </select>
            </div>

            <div class="col-md-4">
              <label class="form-label">Fecha y hora de Contención</label>
              <input type="datetime-local"
                     class="form-control"
                     name="fecha_hora_contencion"
                     id="fecha_hora_contencion"
                     disabled>
            </div>

            <div class="col-12">
              <label class="form-label">Descripción de la Contención</label>
              <textarea class="form-control"
                        name="descripcion_contencion"
                        id="descripcion_contencion"
                        rows="2"
                        disabled></textarea>
            </div>

            <div class="col-12 mt-3">
              <div class="incadd-section-title">Recuperación del incidente</div>
            </div>

            <div class="col-md-3">
              <label class="form-label">Se requiere Recuperación</label>
              <select name="se_requiere_recuperacion"
                      id="se_requiere_recuperacion"
                      class="form-select"
                      onchange="toggleRecuperacion()">
                <option value="No" selected>No</option>
                <option value="Si">Sí</option>
              </select>
            </div>

            <div class="col-md-4">
              <label class="form-label">Fecha y hora de Recuperación</label>
              <input type="datetime-local"
                     class="form-control"
                     name="fecha_hora_recuperacion"
                     id="fecha_hora_recuperacion"
                     disabled>
            </div>

            <div class="col-12">
              <label class="form-label">Descripción de la Recuperación</label>
              <textarea class="form-control"
                        name="descripcion_recuperacion"
                        id="descripcion_recuperacion"
                        rows="2"
                        disabled></textarea>
            </div>

            <div class="col-12 mt-3">
              <div class="incadd-section-title">Detalle y cierre</div>
            </div>

            <div class="col-12">
              <label class="form-label">Descripción Alerta</label>
              <textarea class="form-control" name="descripcion_alerta" rows="2"></textarea>
            </div>

            <div class="col-12">
              <label class="form-label">Descripción del Cierre</label>
              <textarea class="form-control" name="descripcion_cierre" rows="2"></textarea>
            </div>

            <div class="incadd-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold">Guardar incidente</button>
              <a href="{{ url_for('incidentes_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold incadd-cancel-btn"
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

      .incadd-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .incadd-header-card{
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

      .incadd-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .incadd-header-overlay{
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

      .incadd-header-overlay::before{
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

      .incadd-header-text{
        max-width:1200px;
        width:100%;
        display:block;
        transform:none;
      }

      .incadd-header-text::before{
        content:"SGSI · Gestión de Incidentes";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .incadd-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .incadd-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .incadd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .incadd-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .incadd-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .incadd-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .incadd-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .incadd-card-body{
        padding:18px;
      }

      .incadd-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .incadd-card .form-control,
      .incadd-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .incadd-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .incadd-card .form-control:focus,
      .incadd-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .incadd-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .incadd-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
        width:100%;
      }

      .incadd-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .incadd-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .incadd-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .incadd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .incadd-header-card{
          min-height:88px;
        }

        .incadd-title{
          font-size:1.20rem;
        }

        .incadd-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .incadd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .incadd-header-overlay::before{
          margin:0;
        }

        .incadd-header-actions .btn,
        .incadd-bottom-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      function toggleContencion() {
        const sel = document.getElementById('se_requiere_contencion');
        const enable = sel && sel.value === 'Si';

        const fh = document.getElementById('fecha_hora_contencion');
        const desc = document.getElementById('descripcion_contencion');

        if (fh) {
          fh.disabled = !enable;
          if (!enable) fh.value = '';
        }
        if (desc) {
          desc.disabled = !enable;
          if (!enable) desc.value = '';
        }
      }

      function toggleRecuperacion() {
        const sel = document.getElementById('se_requiere_recuperacion');
        const enable = sel && sel.value === 'Si';

        const fh = document.getElementById('fecha_hora_recuperacion');
        const desc = document.getElementById('descripcion_recuperacion');

        if (fh) {
          fh.disabled = !enable;
          if (!enable) fh.value = '';
        }
        if (desc) {
          desc.disabled = !enable;
          if (!enable) desc.value = '';
        }
      }

      document.addEventListener('DOMContentLoaded', function() {
        toggleContencion();
        toggleRecuperacion();
      });
    </script>
    """, clasificaciones=clasificaciones_config)

    return render_template_string(BASE, content=content)


# ============================================================================
# MATRIZ GESTIÓN DE INCIDENTES
# ============================================================================

@app.route('/incidentes/matriz')
@login_required
def incidentes_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Gestión de Cambios (RFC)"):
        flash("No tiene permiso para acceder a Gestión de Incidentes.", "danger")
        return redirect(url_for('menu'))

    solo_lectura = (user.role == 'auditor')

    conn = get_incidentes_db_connection()
    c = conn.cursor()

    eliminar_id = request.args.get('eliminar')
    if eliminar_id and not solo_lectura:
        c.execute("DELETE FROM registro_incidentes WHERE id=?", (eliminar_id,))
        conn.commit()
        flash("Incidente eliminado correctamente.", "success")

    filtro_nombre = (request.args.get('nombre_alerta') or '').strip()
    filtro_clasificacion = (request.args.get('clasificacion_incidente') or '').strip()
    filtro_prioridad = (request.args.get('prioridad') or '').strip()
    filtro_estado = (request.args.get('estado') or '').strip()

    base_query = """
        SELECT
            id,
            fecha_alerta,
            id_incidente,
            nombre_alerta,
            descripcion_alerta,
            clasificacion_incidente,
            cargo_responsable,
            estado,
            prioridad
        FROM registro_incidentes
        WHERE 1=1
    """
    params = []

    if filtro_nombre:
        base_query += " AND nombre_alerta LIKE ?"
        params.append(f"%{filtro_nombre}%")

    if filtro_clasificacion:
        base_query += " AND clasificacion_incidente = ?"
        params.append(filtro_clasificacion)

    if filtro_prioridad:
        base_query += " AND prioridad = ?"
        params.append(filtro_prioridad)

    if filtro_estado:
        base_query += " AND estado = ?"
        params.append(filtro_estado)

    base_query += " ORDER BY id DESC"

    c.execute(base_query, tuple(params))
    incidentes = c.fetchall()

    c.execute("""
        SELECT DISTINCT clasificacion_incidente
        FROM registro_incidentes
        WHERE clasificacion_incidente IS NOT NULL
          AND TRIM(clasificacion_incidente) <> ''
        ORDER BY clasificacion_incidente ASC
    """)
    opciones_clasificacion = [x[0] for x in c.fetchall()]

    c.execute("""
        SELECT DISTINCT prioridad
        FROM registro_incidentes
        WHERE prioridad IS NOT NULL
          AND TRIM(prioridad) <> ''
        ORDER BY prioridad ASC
    """)
    opciones_prioridad = [x[0] for x in c.fetchall()]

    c.execute("""
        SELECT DISTINCT estado
        FROM registro_incidentes
        WHERE estado IS NOT NULL
          AND TRIM(estado) <> ''
        ORDER BY estado ASC
    """)
    opciones_estado = [x[0] for x in c.fetchall()]

    c.execute("SELECT COUNT(*) FROM registro_incidentes")
    total_general = c.fetchone()[0]
    total_filtrados = len(incidentes)

    conn.close()

    html = """
    <div class="incmat-shell">

      <div class="incmat-header-card">
        <div class="incmat-header-overlay">
          <div class="incmat-header-text">
            <h3 class="incmat-title m-0">Registro de Incidentes</h3>
            <div class="incmat-subtitle">
              Visualización resumida de incidentes de seguridad de la información registrados en el sistema
            </div>
          </div>
        </div>
      </div>

      <div class="incmat-header-actions">

        {% if not solo_lectura %}
        <a href="{{ url_for('incidentes_nuevo') }}"
           class="btn btn-primary rounded-pill px-4 fw-bold"
           onclick="showLoader()">
          ➕ Agregar Incidente
        </a>
        {% endif %}
      </div>

      <div class="incmat-topbar">
        <div class="incmat-topbar-card">
          <div class="incmat-topbar-title">Resumen de incidentes</div>
          <div class="incmat-topbar-subtitle">
            Total registros: <strong>{{ total_general }}</strong>
            &nbsp; | &nbsp;
            Mostrando: <strong>{{ total_filtrados }}</strong>
          </div>
        </div>
      </div>

      <div class="incmat-filter-card">
        <div class="incmat-filter-head">
          <span>Filtros de búsqueda</span>
        </div>

        <div class="incmat-filter-body">
          <form method="GET" class="row g-2 align-items-end">

            <div class="col-xl-3 col-lg-3 col-md-6">
              <label class="form-label incmat-label">Nombre alerta</label>
              <input type="text"
                     name="nombre_alerta"
                     class="form-control form-control-sm incmat-input-sm"
                     value="{{ filtro_nombre }}"
                     placeholder="Buscar alerta">
            </div>

            <div class="col-xl-3 col-lg-3 col-md-6">
              <label class="form-label incmat-label">Clasificación</label>
              <select name="clasificacion_incidente" class="form-select form-select-sm incmat-input-sm">
                <option value="">Todas</option>
                {% for op in opciones_clasificacion %}
                  <option value="{{ op }}" {% if filtro_clasificacion == op %}selected{% endif %}>{{ op }}</option>
                {% endfor %}
              </select>
            </div>

            <div class="col-xl-2 col-lg-2 col-md-4">
              <label class="form-label incmat-label">Prioridad</label>
              <select name="prioridad" class="form-select form-select-sm incmat-input-sm">
                <option value="">Todas</option>
                {% for op in opciones_prioridad %}
                  <option value="{{ op }}" {% if filtro_prioridad == op %}selected{% endif %}>{{ op }}</option>
                {% endfor %}
              </select>
            </div>

            <div class="col-xl-2 col-lg-2 col-md-4">
              <label class="form-label incmat-label">Estado</label>
              <select name="estado" class="form-select form-select-sm incmat-input-sm">
                <option value="">Todos</option>
                {% for op in opciones_estado %}
                  <option value="{{ op }}" {% if filtro_estado == op %}selected{% endif %}>{{ op }}</option>
                {% endfor %}
              </select>
            </div>

            <div class="col-xl-2 col-lg-2 col-md-4">
              <div class="d-flex gap-2 incmat-filter-actions">
                <button class="btn btn-primary btn-sm rounded-pill px-3 w-100" type="submit">
                  Filtrar
                </button>
                <a href="{{ url_for('incidentes_matriz') }}"
                   class="btn btn-outline-secondary btn-sm rounded-pill px-3 w-100"
                   onclick="showLoader()">
                  Limpiar
                </a>
              </div>
            </div>

          </form>
        </div>
      </div>

      <div class="incmat-card">
        <div class="incmat-card-body">
          <div class="table-responsive">
            <table class="table table-hover align-middle incmat-table">
              <thead>
                <tr>
                  <th>ID Incidente</th>
                  <th>Fecha Alerta</th>
                  <th>Nombre Alerta</th>
                  <th>Descripción</th>
                  <th>Clasificación</th>
                  <th>Estado</th>
                  <th>Prioridad</th>
                  <th class="incmat-col-acciones">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {% for fila in incidentes %}
                {% set id_reg = fila[0] %}
                {% set fecha_alerta = fila[1] %}
                {% set id_incidente = fila[2] %}
                {% set nombre_alerta = fila[3] %}
                {% set descripcion_alerta = fila[4] %}
                {% set clasificacion_incidente = fila[5] %}
                {% set cargo_responsable = fila[6] %}
                {% set estado = fila[7] %}
                {% set prioridad = fila[8] %}
                <tr>
                  <td>{{ id_incidente or '—' }}</td>
                  <td>{{ fecha_alerta or '—' }}</td>
                  <td>{{ nombre_alerta or '—' }}</td>
                  <td>{{ descripcion_alerta or '—' }}</td>
                  <td>{{ clasificacion_incidente or '—' }}</td>
                  <td>{{ estado or '—' }}</td>
                  <td>
                    {% set p = (prioridad or '')|lower %}
                    {% if p == 'alta' %}
                      <span class="badge incmat-badge incmat-badge-alta">Alta</span>
                    {% elif p == 'media' %}
                      <span class="badge incmat-badge incmat-badge-media">Media</span>
                    {% elif p == 'baja' %}
                      <span class="badge incmat-badge incmat-badge-baja">Baja</span>
                    {% else %}
                      <span class="badge incmat-badge incmat-badge-neutro">—</span>
                    {% endif %}
                  </td>
                  <td class="incmat-col-acciones">
                    <div class="incmat-actions-wrap">
                      <a href="{{ url_for('incidentes_detalle', id=id_reg) }}"
                         class="btn btn-info btn-sm rounded-pill incmat-btn-action text-white fw-bold"
                         onclick="showLoader()">
                        Ver detalle
                      </a>

                      {% if not solo_lectura %}
                      <a href="{{ url_for('incidentes_editar', id=id_reg) }}"
                         class="btn btn-warning btn-sm rounded-pill incmat-btn-action fw-bold"
                         onclick="showLoader()">
                        Editar
                      </a>
                      <a href="{{ url_for('incidentes_matriz', eliminar=id_reg, nombre_alerta=filtro_nombre, clasificacion_incidente=filtro_clasificacion, prioridad=filtro_prioridad, estado=filtro_estado) }}"
                         class="btn btn-danger btn-sm rounded-pill incmat-btn-action fw-bold"
                         onclick="return confirm('¿Seguro que deseas eliminar este incidente?');">
                        Eliminar
                      </a>
                      {% else %}
                      <span class="badge bg-secondary">Solo lectura</span>
                      {% endif %}
                    </div>
                  </td>
                </tr>
                {% endfor %}

                {% if not incidentes %}
                <tr>
                  <td colspan="8" class="text-center text-muted py-4">
                    No hay incidentes para los filtros seleccionados.
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

      .incmat-shell{
        width:96%;
        max-width:1600px;
        margin:10px auto 24px auto;
      }

      .incmat-header-card{
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

      .incmat-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .incmat-header-overlay{
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

      .incmat-header-overlay::before{
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

      .incmat-header-text{
        max-width:1200px;
        width:100%;
        display:block;
        transform:none;
      }

      .incmat-header-text::before{
        content:"SGSI · Matriz de Incidentes";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .incmat-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .incmat-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .incmat-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .incmat-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .incmat-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .incmat-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .incmat-topbar-card,
      .incmat-filter-card,
      .incmat-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .incmat-topbar-card{
        padding:14px 16px;
        margin-bottom:12px;
      }

      .incmat-topbar-title{
        font-weight:950;
        font-size:.92rem;
        color:#0f172a;
      }

      .incmat-topbar-subtitle{
        font-size:.78rem;
        color:#475569;
      }

      .incmat-filter-card{
        margin-bottom:14px;
      }

      .incmat-filter-head{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#fff;
        font-weight:900;
        font-size:.82rem;
        padding:10px 14px;
      }

      .incmat-filter-body{
        padding:14px 16px;
      }

      .incmat-label{
        font-weight:800;
        font-size:.75rem;
        color:#25324a;
        margin-bottom:4px;
      }

      .incmat-input-sm{
        min-height:36px !important;
        height:36px !important;
        font-size:.78rem !important;
        border-radius:9px !important;
        padding:.25rem .6rem !important;
        border:1px solid #d9e3f0 !important;
        background:#f8fafc !important;
      }

      .incmat-input-sm:focus{
        border-color:#3f86d6 !important;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff !important;
      }

      .incmat-filter-actions .btn{
        border-radius:10px !important;
        min-height:36px;
        padding:7px 18px !important;
        font-size:.78rem;
        font-weight:900;
      }

      .incmat-card-body{
        padding:12px 16px 16px 16px;
      }

      .incmat-table-wrap,
      .table-responsive{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .incmat-table{
        min-width:1300px;
        table-layout:fixed;
        margin-bottom:0;
      }

      .incmat-table thead th{
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

      .incmat-table th,
      .incmat-table td{
        vertical-align:top;
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .incmat-table td{
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .incmat-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .incmat-table tbody tr:hover{
        background:#eef6ff;
      }

      .incmat-col-acciones{
        width:180px !important;
        min-width:180px !important;
        text-align:center;
        vertical-align:middle !important;
      }

      .incmat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .incmat-btn-action{
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

      .incmat-badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
        display:inline-block;
        text-align:center;
      }

      .incmat-badge-alta{
        background:#fee2e2;
        color:#991b1b;
      }

      .incmat-badge-media{
        background:#fef3c7;
        color:#92400e;
      }

      .incmat-badge-baja{
        background:#dcfce7;
        color:#166534;
      }

      .incmat-badge-neutro{
        background:#e5e7eb;
        color:#374151;
      }

      @media (max-width:992px){
        .incmat-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .incmat-header-card{
          min-height:88px;
        }

        .incmat-title{
          font-size:1.20rem;
        }

        .incmat-card-body,
        .incmat-filter-body{
          padding:12px;
        }

        .incmat-col-acciones{
          width:165px !important;
          min-width:165px !important;
        }
      }

      @media (max-width:768px){
        .incmat-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .incmat-header-overlay::before{
          margin:0;
        }

        .incmat-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    content = render_template_string(
        html,
        incidentes=incidentes,
        solo_lectura=solo_lectura,
        total_general=total_general,
        total_filtrados=total_filtrados,
        opciones_clasificacion=opciones_clasificacion,
        opciones_prioridad=opciones_prioridad,
        opciones_estado=opciones_estado,
        filtro_nombre=filtro_nombre,
        filtro_clasificacion=filtro_clasificacion,
        filtro_prioridad=filtro_prioridad,
        filtro_estado=filtro_estado
    )
    return render_template_string(BASE, content=Markup(content))


# ============================================================================
# DETALLE INCIDENTE
# ============================================================================

@app.route('/incidentes/detalle/<int:id>')
@login_required
def incidentes_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Gestión de Cambios (RFC)"):
        flash("No tiene permiso para ver el detalle del incidente.", "danger")
        return redirect(url_for('incidentes_matriz'))

    solo_lectura = (user.role == 'auditor')

    conn = get_incidentes_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT
            id,
            fecha_alerta,
            id_incidente,
            nombre_alerta,
            descripcion_alerta,
            clasificacion_incidente,
            cargo_responsable,
            atacante,
            ubicacion_atacante,
            tipo_recurso_afectado,
            nombre_recurso_id,
            estado,
            fecha_cierre,
            descripcion_cierre,
            principio,
            prioridad,
            se_requiere_contencion,
            fecha_hora_contencion,
            descripcion_contencion,
            se_requiere_recuperacion,
            fecha_hora_recuperacion,
            descripcion_recuperacion
        FROM registro_incidentes
        WHERE id = ?
    """, (id,))
    row = c.fetchone()
    conn.close()

    if not row:
        flash("Incidente no encontrado.", "danger")
        return redirect(url_for('incidentes_matriz'))

    content = render_template_string("""
    <div class="incview-shell">

      <div class="incview-header-card">
        <div class="incview-header-overlay">
          <div class="incview-header-text">
            <h3 class="incview-title m-0">Ver Incidente de Seguridad</h3>
            <div class="incview-subtitle">
              Consulta detallada del incidente de seguridad, incluyendo clasificación, contención, recuperación, seguimiento y cierre
            </div>
          </div>
        </div>
      </div>

      <div class="incview-header-actions">
        <a href="{{ url_for('incidentes_matriz') }}"
           class="btn rounded-pill px-4 fw-bold incview-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz de Incidentes
        </a>

        {% if can_planes %}
        <a href="{{ url_for('ir_incident_plans', iid=row['id']) }}" class="btn btn-primary rounded-pill px-4 fw-bold"><i class="bi bi-shield-check"></i> Activar plan de respuesta</a>
        {% endif %}
        {% if not solo_lectura %}
        <a href="{{ url_for('incidentes_editar', id=row['id']) }}"
           class="btn btn-warning rounded-pill px-4 fw-bold"
           onclick="showLoader()">
          ✏️ Editar
        </a>
        {% endif %}
      </div>

      <div class="incview-card">
        <div class="incview-card-body">

          <div class="row g-3">
            <div class="col-12">
              <div class="incview-section-title">Información general del incidente</div>
            </div>

            <div class="col-md-4"><div class="incview-block"><div class="incview-label">ID del incidente</div><div class="incview-value">{{ row['id_incidente'] or '—' }}</div></div></div>
            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Fecha de la alerta</div><div class="incview-value">{{ row['fecha_alerta'] or '—' }}</div></div></div>
            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Nombre de la alerta</div><div class="incview-value">{{ row['nombre_alerta'] or '—' }}</div></div></div>

            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Clasificación</div><div class="incview-value">{{ row['clasificacion_incidente'] or '—' }}</div></div></div>
            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Cargo responsable</div><div class="incview-value">{{ row['cargo_responsable'] or '—' }}</div></div></div>
            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Atacante</div><div class="incview-value">{{ row['atacante'] or '—' }}</div></div></div>

            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Ubicación atacante</div><div class="incview-value">{{ row['ubicacion_atacante'] or '—' }}</div></div></div>
            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Tipo de recurso afectado</div><div class="incview-value">{{ row['tipo_recurso_afectado'] or '—' }}</div></div></div>
            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Nombre recurso y ID</div><div class="incview-value">{{ row['nombre_recurso_id'] or '—' }}</div></div></div>

            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Estado</div><div class="incview-value">{{ row['estado'] or '—' }}</div></div></div>
            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Fecha cierre</div><div class="incview-value">{{ row['fecha_cierre'] or '—' }}</div></div></div>
            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Principio afectado</div><div class="incview-value">{{ row['principio'] or '—' }}</div></div></div>

            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Prioridad</div><div class="incview-value">{{ row['prioridad'] or '—' }}</div></div></div>

            <div class="col-12 mt-2">
              <div class="incview-section-title">Contención del incidente</div>
            </div>

            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Se requiere contención</div><div class="incview-value">{{ row['se_requiere_contencion'] or '—' }}</div></div></div>
            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Fecha y hora de contención</div><div class="incview-value">{{ row['fecha_hora_contencion'] or '—' }}</div></div></div>
            <div class="col-12"><div class="incview-block"><div class="incview-label">Descripción de la contención</div><div class="incview-value">{{ row['descripcion_contencion'] or '—' }}</div></div></div>

            <div class="col-12 mt-2">
              <div class="incview-section-title">Recuperación del incidente</div>
            </div>

            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Se requiere recuperación</div><div class="incview-value">{{ row['se_requiere_recuperacion'] or '—' }}</div></div></div>
            <div class="col-md-4"><div class="incview-block"><div class="incview-label">Fecha y hora de recuperación</div><div class="incview-value">{{ row['fecha_hora_recuperacion'] or '—' }}</div></div></div>
            <div class="col-12"><div class="incview-block"><div class="incview-label">Descripción de la recuperación</div><div class="incview-value">{{ row['descripcion_recuperacion'] or '—' }}</div></div></div>

            <div class="col-12 mt-2">
              <div class="incview-section-title">Detalle y cierre</div>
            </div>

            <div class="col-12"><div class="incview-block"><div class="incview-label">Descripción de la alerta</div><div class="incview-value">{{ row['descripcion_alerta'] or '—' }}</div></div></div>
            <div class="col-12"><div class="incview-block"><div class="incview-label">Descripción del cierre</div><div class="incview-value">{{ row['descripcion_cierre'] or '—' }}</div></div></div>
          </div>

          <div class="incview-bottom-actions">
            <a href="{{ url_for('incidentes_matriz') }}"
               class="btn rounded-pill px-4 fw-bold incview-cancel-btn"
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

      .incview-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HEADER SGSI UNIFICADO
      ========================= */
      .incview-header-card{
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

      .incview-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .incview-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .incview-header-overlay::before{
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
      }

      .incview-header-text{
        max-width:1200px;
        width:100%;
      }

      .incview-header-text::before{
        content:"SGSI · Detalle de Incidente";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .incview-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .incview-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES SUPERIORES
      ========================= */
      .incview-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .incview-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .incview-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .incview-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD PRINCIPAL
      ========================= */
      .incview-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .incview-card-body{
        padding:18px;
      }

      /* =========================
         SECCIONES
      ========================= */
      .incview-section-title{
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
         BLOQUES DE INFORMACIÓN
      ========================= */
      .incview-block{
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%) !important;
        border:1px solid #dbe6f4 !important;
        border-radius:14px !important;
        box-shadow:0 6px 14px rgba(15,23,42,.08);
        padding:14px 16px;
        margin-bottom:12px;
      }

      .incview-label{
        font-weight:900;
        font-size:.72rem;
        color:#1d4ed8;
        margin-bottom:4px;
        text-transform:uppercase;
      }

      .incview-value{
        color:#101827;
        font-size:.85rem;
        white-space:pre-wrap;
        word-break:break-word;
      }

      /* =========================
         ACCIONES INFERIORES
      ========================= */
      .incview-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
      }

      .incview-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .incview-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .incview-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         RESPONSIVE
      ========================= */
      @media (max-width:992px){
        .incview-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .incview-header-card{
          min-height:88px;
        }

        .incview-title{
          font-size:1.20rem;
        }

        .incview-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .incview-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .incview-header-overlay::before{
          margin:0;
        }

        .incview-header-actions .btn,
        .incview-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """, row=row, solo_lectura=solo_lectura,
       can_planes=verificar_permiso(user, 'Planes de Respuesta a Incidentes'))

    return render_template_string(BASE, content=content)


# ============================================================================
# EDITAR INCIDENTE
# ============================================================================

@app.route('/incidentes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def incidentes_editar(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede editar registros.", "danger")
        return redirect(url_for('incidentes_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Cambios (RFC)"):
        flash("No tiene permiso para editar incidentes.", "danger")
        return redirect(url_for('incidentes_matriz'))

    conn = get_incidentes_db_connection()
    c = conn.cursor()

    c.execute("""
        SELECT
            id,
            fecha_alerta,
            id_incidente,
            nombre_alerta,
            descripcion_alerta,
            clasificacion_incidente,
            cargo_responsable,
            atacante,
            ubicacion_atacante,
            tipo_recurso_afectado,
            nombre_recurso_id,
            estado,
            fecha_cierre,
            descripcion_cierre,
            principio,
            prioridad,
            se_requiere_contencion,
            fecha_hora_contencion,
            descripcion_contencion,
            se_requiere_recuperacion,
            fecha_hora_recuperacion,
            descripcion_recuperacion
        FROM registro_incidentes
        WHERE id = ?
    """, (id,))
    row = c.fetchone()

    if not row:
        conn.close()
        flash("Incidente no encontrado.", "danger")
        return redirect(url_for('incidentes_matriz'))

    if request.method == 'POST':
        raw_fecha_alerta = request.form.get('fecha_alerta') or None
        fecha_alerta = None
        if raw_fecha_alerta:
            try:
                dt = datetime.strptime(raw_fecha_alerta, "%Y-%m-%dT%H:%M")
                fecha_alerta = dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                fecha_alerta = raw_fecha_alerta

        id_incidente = (request.form.get('id_incidente') or '').strip()
        clasificacion_incidente = (request.form.get('clasificacion_incidente') or '').strip()
        cargo_responsable = (request.form.get('cargo_responsable') or '').strip()

        nombre_alerta = (request.form.get('nombre_alerta') or '').strip()
        descripcion_alerta = (request.form.get('descripcion_alerta') or '').strip()
        atacante = (request.form.get('atacante') or '').strip()
        ubicacion_atacante = (request.form.get('ubicacion_atacante') or '').strip()
        tipo_recurso = (request.form.get('tipo_recurso_afectado') or '').strip()
        nombre_recurso_id = (request.form.get('nombre_recurso_id') or '').strip()
        estado = (request.form.get('estado') or '').strip()

        fecha_cierre = request.form.get('fecha_cierre') or None
        descripcion_cierre = (request.form.get('descripcion_cierre') or '').strip()
        principio = (request.form.get('principio') or '').strip()
        prioridad = (request.form.get('prioridad') or '').strip()

        se_requiere_contencion = request.form.get('se_requiere_contencion') or "No"
        raw_fecha_hora_contencion = request.form.get('fecha_hora_contencion') or None
        descripcion_contencion = (request.form.get('descripcion_contencion') or '').strip()

        fecha_hora_contencion = None
        if se_requiere_contencion == "Si" and raw_fecha_hora_contencion:
            try:
                dtc = datetime.strptime(raw_fecha_hora_contencion, "%Y-%m-%dT%H:%M")
                fecha_hora_contencion = dtc.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                fecha_hora_contencion = raw_fecha_hora_contencion
        else:
            fecha_hora_contencion = None
            descripcion_contencion = ""

        se_requiere_recuperacion = request.form.get('se_requiere_recuperacion') or "No"
        raw_fecha_hora_recuperacion = request.form.get('fecha_hora_recuperacion') or None
        descripcion_recuperacion = (request.form.get('descripcion_recuperacion') or '').strip()

        fecha_hora_recuperacion = None
        if se_requiere_recuperacion == "Si" and raw_fecha_hora_recuperacion:
            try:
                dtr = datetime.strptime(raw_fecha_hora_recuperacion, "%Y-%m-%dT%H:%M")
                fecha_hora_recuperacion = dtr.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                fecha_hora_recuperacion = raw_fecha_hora_recuperacion
        else:
            fecha_hora_recuperacion = None
            descripcion_recuperacion = ""

        c.execute("""
            UPDATE registro_incidentes
            SET
                fecha_alerta = ?,
                nombre_alerta = ?,
                descripcion_alerta = ?,
                id_incidente = ?,
                clasificacion_incidente = ?,
                cargo_responsable = ?,
                atacante = ?,
                ubicacion_atacante = ?,
                tipo_recurso_afectado = ?,
                nombre_recurso_id = ?,
                estado = ?,
                fecha_cierre = ?,
                descripcion_cierre = ?,
                principio = ?,
                prioridad = ?,
                se_requiere_contencion = ?,
                fecha_hora_contencion = ?,
                descripcion_contencion = ?,
                se_requiere_recuperacion = ?,
                fecha_hora_recuperacion = ?,
                descripcion_recuperacion = ?
            WHERE id = ?
        """, (
            fecha_alerta,
            nombre_alerta,
            descripcion_alerta,
            id_incidente,
            clasificacion_incidente,
            cargo_responsable,
            atacante,
            ubicacion_atacante,
            tipo_recurso,
            nombre_recurso_id,
            estado,
            fecha_cierre,
            descripcion_cierre,
            principio,
            prioridad,
            se_requiere_contencion,
            fecha_hora_contencion,
            descripcion_contencion,
            se_requiere_recuperacion,
            fecha_hora_recuperacion,
            descripcion_recuperacion,
            id
        ))

        conn.commit()
        conn.close()

        flash("Incidente actualizado correctamente.", "success")
        return redirect(url_for('incidentes_matriz'))

    def to_datetime_local(value):
        if not value:
            return ""
        try:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M")
            return dt.strftime("%Y-%m-%dT%H:%M")
        except ValueError:
            return value

    config = MetricConfigIncidentes.query.first()
    clasificaciones_config = []
    if config:
        clasificaciones_config = [fila.clasificacion for fila in config.clasificaciones]

    content = render_template_string("""
    <div class="incedit-shell">

      <div class="incedit-header-card">
        <div class="incedit-header-overlay">
          <div class="incedit-header-text">
            <h3 class="incedit-title m-0">Editar Incidente de Seguridad</h3>
            <div class="incedit-subtitle">
              Actualización del incidente de seguridad, incluyendo clasificación, contención, recuperación, seguimiento y cierre
            </div>
          </div>
        </div>
      </div>

      <div class="incedit-header-actions">
        <a href="{{ url_for('incidentes_matriz') }}"
           class="btn rounded-pill px-4 fw-bold incedit-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz de Incidentes
        </a>
      </div>

      <div class="incedit-card">
        <div class="incedit-card-body">
          <form method="POST" class="row g-3">

            <div class="col-12">
              <div class="incedit-section-title">Información general del incidente</div>
            </div>

            <div class="col-md-4">
              <label class="form-label">ID del Incidente</label>
              <input class="form-control" name="id_incidente" value="{{ row['id_incidente'] or '' }}">
            </div>

            <div class="col-md-3">
              <label class="form-label">Fecha de la alerta</label>
              <input type="datetime-local" class="form-control" name="fecha_alerta" value="{{ to_datetime_local(row['fecha_alerta']) }}" required>
            </div>

            <div class="col-md-5">
              <label class="form-label">Nombre de la Alerta</label>
              <input class="form-control" name="nombre_alerta" value="{{ row['nombre_alerta'] or '' }}" required>
            </div>

            <div class="col-md-4">
              <label class="form-label">Clasificación del Incidente</label>
              <select name="clasificacion_incidente" class="form-select" required>
                <option value="">Seleccione...</option>
                {% for c in clasificaciones %}
                  <option value="{{ c }}" {% if row['clasificacion_incidente'] == c %}selected{% endif %}>{{ c }}</option>
                {% endfor %}
              </select>
            </div>

            <div class="col-md-4">
              <label class="form-label">Cargo responsable de la gestión</label>
              <input class="form-control" name="cargo_responsable" value="{{ row['cargo_responsable'] or '' }}">
            </div>

            <div class="col-md-4">
              <label class="form-label">Atacante</label>
              <input class="form-control" name="atacante" value="{{ row['atacante'] or '' }}">
            </div>

            <div class="col-md-4">
              <label class="form-label">Ubicación atacante</label>
              <input class="form-control" name="ubicacion_atacante" value="{{ row['ubicacion_atacante'] or '' }}">
            </div>

            <div class="col-md-4">
              <label class="form-label">Tipo Recurso Afectado</label>
              <input class="form-control" name="tipo_recurso_afectado" value="{{ row['tipo_recurso_afectado'] or '' }}">
            </div>

            <div class="col-md-4">
              <label class="form-label">Nombre Recurso y ID</label>
              <input class="form-control" name="nombre_recurso_id" value="{{ row['nombre_recurso_id'] or '' }}">
            </div>

            <div class="col-md-4">
              <label class="form-label">Estado</label>
              <select name="estado" class="form-select">
                <option value="Abierto" {% if row['estado'] == 'Abierto' %}selected{% endif %}>Abierto</option>
                <option value="Cerrado" {% if row['estado'] == 'Cerrado' %}selected{% endif %}>Cerrado</option>
              </select>
            </div>

            <div class="col-md-4">
              <label class="form-label">Fecha Cierre</label>
              <input type="date" class="form-control" name="fecha_cierre" value="{{ row['fecha_cierre'] or '' }}">
            </div>

            <div class="col-md-4">
              <label class="form-label">Principio afectado</label>
              <select name="principio" class="form-select">
                <option value="Confidencialidad" {% if row['principio'] == 'Confidencialidad' %}selected{% endif %}>Confidencialidad</option>
                <option value="Integridad" {% if row['principio'] == 'Integridad' %}selected{% endif %}>Integridad</option>
                <option value="Disponibilidad" {% if row['principio'] == 'Disponibilidad' %}selected{% endif %}>Disponibilidad</option>
              </select>
            </div>

            <div class="col-md-4">
              <label class="form-label">Prioridad (Criticidad del activo)</label>
              <select name="prioridad" class="form-select">
                <option value="Alta" {% if row['prioridad'] == 'Alta' %}selected{% endif %}>Alta</option>
                <option value="Media" {% if row['prioridad'] == 'Media' %}selected{% endif %}>Media</option>
                <option value="Baja" {% if row['prioridad'] == 'Baja' %}selected{% endif %}>Baja</option>
              </select>
            </div>

            <div class="col-12 mt-3">
              <div class="incedit-section-title">Contención del incidente</div>
            </div>

            <div class="col-md-3">
              <label class="form-label">Se requiere Contención</label>
              <select name="se_requiere_contencion"
                      id="se_requiere_contencion"
                      class="form-select"
                      onchange="toggleContencion()">
                <option value="No" {% if row['se_requiere_contencion'] != 'Si' %}selected{% endif %}>No</option>
                <option value="Si" {% if row['se_requiere_contencion'] == 'Si' %}selected{% endif %}>Sí</option>
              </select>
            </div>

            <div class="col-md-4">
              <label class="form-label">Fecha y hora de Contención</label>
              <input type="datetime-local"
                     class="form-control"
                     name="fecha_hora_contencion"
                     id="fecha_hora_contencion"
                     value="{{ to_datetime_local(row['fecha_hora_contencion']) }}">
            </div>

            <div class="col-12">
              <label class="form-label">Descripción de la Contención</label>
              <textarea class="form-control"
                        name="descripcion_contencion"
                        id="descripcion_contencion"
                        rows="2">{{ row['descripcion_contencion'] or '' }}</textarea>
            </div>

            <div class="col-12 mt-3">
              <div class="incedit-section-title">Recuperación del incidente</div>
            </div>

            <div class="col-md-3">
              <label class="form-label">Se requiere Recuperación</label>
              <select name="se_requiere_recuperacion"
                      id="se_requiere_recuperacion"
                      class="form-select"
                      onchange="toggleRecuperacion()">
                <option value="No" {% if row['se_requiere_recuperacion'] != 'Si' %}selected{% endif %}>No</option>
                <option value="Si" {% if row['se_requiere_recuperacion'] == 'Si' %}selected{% endif %}>Sí</option>
              </select>
            </div>

            <div class="col-md-4">
              <label class="form-label">Fecha y hora de Recuperación</label>
              <input type="datetime-local"
                     class="form-control"
                     name="fecha_hora_recuperacion"
                     id="fecha_hora_recuperacion"
                     value="{{ to_datetime_local(row['fecha_hora_recuperacion']) }}">
            </div>

            <div class="col-12">
              <label class="form-label">Descripción de la Recuperación</label>
              <textarea class="form-control"
                        name="descripcion_recuperacion"
                        id="descripcion_recuperacion"
                        rows="2">{{ row['descripcion_recuperacion'] or '' }}</textarea>
            </div>

            <div class="col-12 mt-3">
              <div class="incedit-section-title">Detalle y cierre</div>
            </div>

            <div class="col-12">
              <label class="form-label">Descripción Alerta</label>
              <textarea class="form-control" name="descripcion_alerta" rows="2">{{ row['descripcion_alerta'] or '' }}</textarea>
            </div>

            <div class="col-12">
              <label class="form-label">Descripción del Cierre</label>
              <textarea class="form-control" name="descripcion_cierre" rows="2">{{ row['descripcion_cierre'] or '' }}</textarea>
            </div>

            <div class="incedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold">Guardar cambios</button>
              <a href="{{ url_for('incidentes_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold incedit-cancel-btn"
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

      .incedit-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .incedit-header-card{
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

      .incedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .incedit-header-overlay{
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

      .incedit-header-overlay::before{
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

      .incedit-header-text{
        max-width:1200px;
        width:100%;
        display:block;
        transform:none;
      }

      .incedit-header-text::before{
        content:"SGSI · Edición de Incidente";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .incedit-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .incedit-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .incedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .incedit-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .incedit-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .incedit-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .incedit-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .incedit-card-body{
        padding:18px;
      }

      .incedit-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .incedit-card .form-control,
      .incedit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .incedit-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .incedit-card .form-control:focus,
      .incedit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .incedit-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .incedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
      }

      .incedit-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .incedit-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .incedit-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .incedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .incedit-header-card{
          min-height:88px;
        }

        .incedit-title{
          font-size:1.20rem;
        }

        .incedit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .incedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .incedit-header-overlay::before{
          margin:0;
        }

        .incedit-header-actions .btn,
        .incedit-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    <script>
      function toggleContencion() {
        const sel = document.getElementById('se_requiere_contencion');
        const enable = sel && sel.value === 'Si';

        const fh = document.getElementById('fecha_hora_contencion');
        const desc = document.getElementById('descripcion_contencion');

        if (fh) {
          fh.disabled = !enable;
          if (!enable) fh.value = '';
        }
        if (desc) {
          desc.disabled = !enable;
          if (!enable) desc.value = '';
        }
      }

      function toggleRecuperacion() {
        const sel = document.getElementById('se_requiere_recuperacion');
        const enable = sel && sel.value === 'Si';

        const fh = document.getElementById('fecha_hora_recuperacion');
        const desc = document.getElementById('descripcion_recuperacion');

        if (fh) {
          fh.disabled = !enable;
          if (!enable) fh.value = '';
        }
        if (desc) {
          desc.disabled = !enable;
          if (!enable) desc.value = '';
        }
      }

      document.addEventListener('DOMContentLoaded', function() {
        toggleContencion();
        toggleRecuperacion();
      });
    </script>
    """, row=row, clasificaciones=clasificaciones_config, to_datetime_local=to_datetime_local)

    conn.close()
    return render_template_string(BASE, content=content)

# ============================================================================================================================================
#                                                               Fin del Módulo Gestión de Incidentes
# ============================================================================================================================================

# ==========================================================================================================================================
#                                                               Módulo Registro de Vulnerabilidades
# ==========================================================================================================================================

# =============================
# Constantes globales
# =============================

VULN_CLASIFICACIONES = ['Crítica', 'Alta', 'Media', 'Baja']

# ==========================================================================================================================================
#                                           SUBMÓDULO ANÁLISIS AUTOMÁTICO DE VULNERABILIDADES
# ==========================================================================================================================================

#=======================================
# Escaneo de Vulnerabilidades Kali Linux
#=======================================

class KaliScannerConfig(db.Model):
    __tablename__ = "kali_scanner_config"

    id = db.Column(db.Integer, primary_key=True)

    # local o remoto
    modo = db.Column(db.String(20), nullable=False, default="local")  # local / remoto

    # Si es remoto
    host = db.Column(db.String(255), nullable=True)
    puerto_ssh = db.Column(db.Integer, nullable=False, default=22)
    usuario_ssh = db.Column(db.String(120), nullable=True)
    password_ssh = db.Column(db.String(255), nullable=True)   # si quieres, luego lo ciframos
    ruta_base_remota = db.Column(db.String(500), nullable=True)

    # Si es local
    ruta_nmap = db.Column(db.String(500), nullable=True, default="/usr/bin/nmap")
    ruta_nikto = db.Column(db.String(500), nullable=True, default="/usr/bin/nikto")
    ruta_nuclei = db.Column(db.String(255), nullable=True)
    ruta_whatweb = db.Column(db.String(500), nullable=True, default="/usr/bin/whatweb")
    ruta_testssl = db.Column(db.String(500), nullable=True, default="/usr/bin/testssl")
    ruta_zap = db.Column(db.String(500))

    activo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VulnerabilityScanRun(db.Model):
    __tablename__ = "vulnerability_scan_runs"

    id = db.Column(db.Integer, primary_key=True)

    target = db.Column(db.String(500), nullable=False)   # URL o IP
    target_type = db.Column(db.String(20), nullable=False)  # url / ip
    scan_mode = db.Column(db.String(30), nullable=False, default="full")  # full
    scanner_mode = db.Column(db.String(20), nullable=False)  # local / remoto

    estado = db.Column(db.String(30), nullable=False, default="pendiente")  # pendiente/ejecutando/finalizado/error
    fecha_inicio = db.Column(db.DateTime, nullable=True)
    fecha_fin = db.Column(db.DateTime, nullable=True)

    ejecutado_por = db.Column(db.String(120), nullable=True)
    responsable_asignado = db.Column(db.String(200), nullable=True)

    archivo_resumen_json = db.Column(db.String(500), nullable=True)
    archivo_reporte_pdf = db.Column(db.String(500), nullable=True)
    archivo_log = db.Column(db.String(500), nullable=True)

    salida_consola = db.Column(db.Text, nullable=True)
    error_detalle = db.Column(db.Text, nullable=True)

    total_hallazgos = db.Column(db.Integer, nullable=False, default=0)
    criticas = db.Column(db.Integer, nullable=False, default=0)
    altas = db.Column(db.Integer, nullable=False, default=0)
    medias = db.Column(db.Integer, nullable=False, default=0)
    bajas = db.Column(db.Integer, nullable=False, default=0)
    progress_pct = db.Column(db.Integer, nullable=False, default=0)
    current_stage = db.Column(db.String(100), nullable=True)
    current_tool = db.Column(db.String(50), nullable=True)

    cancel_requested = db.Column(db.Boolean, nullable=False, default=False)
    stopped_by_user = db.Column(db.Boolean, nullable=False, default=False)

    findings_streamed = db.Column(db.Integer, nullable=False, default=0)

    created_vulns = db.Column(db.Integer, nullable=False, default=0)
    created_plans = db.Column(db.Integer, nullable=False, default=0)

    worker_pid = db.Column(db.Integer, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    active_pid = db.Column(db.Integer, nullable=True)
    active_command = db.Column(db.Text, nullable=True)
    monitor_enabled = db.Column(db.Boolean, nullable=False, default=True)
    herramientas = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class VulnerabilityScanFinding(db.Model):
    __tablename__ = "vulnerability_scan_findings"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("vulnerability_scan_runs.id", ondelete="CASCADE"), nullable=False)

    fuente = db.Column(db.String(50), nullable=False)   # nmap / nikto / whatweb / testssl
    titulo = db.Column(db.String(500), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)

    severidad = db.Column(db.String(20), nullable=False)  # Crítica/Alta/Media/Baja
    cvss = db.Column(db.String(20), nullable=True)
    cve = db.Column(db.String(100), nullable=True)

    puerto = db.Column(db.String(50), nullable=True)
    protocolo = db.Column(db.String(50), nullable=True)
    servicio = db.Column(db.String(200), nullable=True)
    evidencia = db.Column(db.Text, nullable=True)
    recomendacion_base = db.Column(db.Text, nullable=True)

    vulnerabilidad_registro_id = db.Column(
        db.Integer,
        db.ForeignKey("vulnerabilidades_registro.id"),
        nullable=True
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    run = db.relationship("VulnerabilityScanRun", backref=db.backref("hallazgos", lazy=True, cascade="all, delete-orphan"))



SCAN_PRIORIDADES = ["Alta", "Media", "Baja"]
SCAN_ESTADOS = ["pendiente", "ejecutando", "finalizado", "error"]
SCAN_TARGET_TYPES = ["url", "ip"]
SCAN_SCANNER_MODES = ["local", "remoto"]


def _scan_cfg():
    cfg = KaliScannerConfig.query.first()
    if not cfg:
        cfg = KaliScannerConfig(
            modo="remoto",
            host="10.211.55.10",
            puerto_ssh=22,
            usuario_ssh="parallels",
            ruta_nmap="/usr/bin/nmap",
            ruta_nikto="/usr/bin/nikto",
            ruta_nuclei="/usr/bin/nuclei",
            ruta_whatweb="/usr/bin/whatweb",
            ruta_testssl="/usr/bin/testssl",
            ruta_zap="/usr/share/zaproxy/zap.sh",
            ruta_base_remota="/tmp"
        )
        db.session.add(cfg)
        db.session.commit()

    # compatibilidad si ya existe el registro viejo sin valor
    if not getattr(cfg, "ruta_nuclei", None):
        cfg.ruta_nuclei = "/usr/bin/nuclei"
        db.session.commit()

    return cfg


def detectar_tipo_objetivo(target: str) -> str:
    t = (target or "").strip()
    if not t:
        return "ip"

    # IP directa
    try:
        ipaddress.ip_address(t)
        return "ip"
    except Exception:
        pass

    # URL explícita
    if re.match(r"^https?://", t, re.I):
        return "url"

    # Dominio simple -> tratar como URL
    if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", t):
        return "url"

    return "ip"


def normalizar_target_para_scan(target: str) -> str:
    t = (target or "").strip()
    if not t:
        return ""

    if detectar_tipo_objetivo(t) == "url":
        if not re.match(r"^https?://", t, re.I):
            t = "http://" + t
    return t


def extraer_host_de_target(target: str) -> str:
    t = normalizar_target_para_scan(target)
    if detectar_tipo_objetivo(t) == "ip":
        return t.strip()

    parsed = urlparse(t)
    return (parsed.hostname or "").strip()


def target_valido(target: str) -> bool:
    t = (target or "").strip()
    if not t:
        return False

    # IP válida
    try:
        ipaddress.ip_address(t)
        return True
    except Exception:
        pass

    # URL o dominio válido
    if re.match(r"^https?://[a-zA-Z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$", t, re.I):
        return True

    if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", t):
        return True

    return False


def safe_scan_slug(texto: str) -> str:
    val = re.sub(r"[^a-zA-Z0-9._-]+", "_", (texto or "").strip())
    return val[:120] if val else "scan"


def scan_run_dir(run_id: int, target: str) -> str:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    folder = f"scan_{run_id}_{safe_scan_slug(target)}_{ts}"
    path = os.path.join(app.config["UPLOAD_VULNERABILIDADES_DIR"], folder)
    os.makedirs(path, exist_ok=True)
    return path


def scan_output_file(run_dir: str, name: str, ext: str) -> str:
    os.makedirs(run_dir, exist_ok=True)
    return os.path.join(run_dir, f"{name}.{ext.lstrip('.')}")

def _cmd_to_string(cmd):
    try:
        return " ".join(shlex.quote(str(x)) for x in cmd)
    except Exception:
        return str(cmd)


def run_local_command_stream(run_id, cmd):
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        start_new_session=True
    )

    output_lines = []

    run = VulnerabilityScanRun.query.get(run_id)
    if run:
        run.active_pid = proc.pid
        run.active_command = _cmd_to_string(cmd)
        db.session.commit()

    try:
        for line in iter(proc.stdout.readline, ''):
            if not line:
                break

            output_lines.append(line.rstrip())

            # guardar pequeño log incremental para monitoreo
            run = VulnerabilityScanRun.query.get(run_id)
            if run:
                prev = run.salida_consola or ""
                chunk = (prev + line)[-20000:]
                run.salida_consola = chunk
                db.session.commit()

            # revisar cancelación mientras corre
            if scan_check_cancel(run_id):
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except Exception:
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                break

        proc.wait(timeout=10)

    except Exception:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass
        raise
    finally:
        run = VulnerabilityScanRun.query.get(run_id)
        if run:
            run.active_pid = None
            run.active_command = None
            db.session.commit()

    return {
        "returncode": proc.returncode,
        "stdout": "\n".join(output_lines),
        "stderr": ""
    }


def run_remote_command_stream(run_id, cfg, remote_cmd: str):
    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "UserKnownHostsFile=/Users/carlosayalaperdomo/.ssh/known_hosts",
        "-p", str(cfg.puerto_ssh or 22),
        f"{cfg.usuario_ssh}@{cfg.host}",
        remote_cmd
    ]

    proc = subprocess.Popen(
        ssh_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        start_new_session=True
    )

    output_lines = []

    run = VulnerabilityScanRun.query.get(run_id)
    if run:
        run.active_pid = proc.pid
        run.active_command = remote_cmd
        db.session.commit()

    try:
        for line in iter(proc.stdout.readline, ''):
            if not line:
                break

            output_lines.append(line.rstrip())

            run = VulnerabilityScanRun.query.get(run_id)
            if run:
                prev = run.salida_consola or ""
                chunk = (prev + line)[-20000:]
                run.salida_consola = chunk
                db.session.commit()

            if scan_check_cancel(run_id):
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except Exception:
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                break

        proc.wait(timeout=10)

    except Exception:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass
        raise
    finally:
        run = VulnerabilityScanRun.query.get(run_id)
        if run:
            run.active_pid = None
            run.active_command = None
            db.session.commit()

    return {
        "returncode": proc.returncode,
        "stdout": "\n".join(output_lines),
        "stderr": ""
    }

def obtener_puertos_abiertos_desde_xml(xml_file: str):
    puertos = []

    if not os.path.exists(xml_file):
        return puertos

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for host in root.findall("host"):
            ports = host.find("ports")
            if ports is None:
                continue

            for port in ports.findall("port"):
                state_el = port.find("state")
                if state_el is not None and state_el.attrib.get("state") == "open":
                    portid = port.attrib.get("portid")
                    if portid:
                        puertos.append(portid)
    except Exception:
        pass

    return sorted(list(set(puertos)), key=lambda x: int(x))


def run_local_command(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or ""
    }


def run_remote_command(cfg, remote_cmd: str):
    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "UserKnownHostsFile=/Users/carlosayalaperdomo/.ssh/known_hosts",
        "-p", str(cfg.puerto_ssh or 22),
        f"{cfg.usuario_ssh}@{cfg.host}",
        remote_cmd
    ]
    proc = subprocess.run(ssh_cmd, capture_output=True, text=True)
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or ""
    }


def scp_from_remote(cfg, remote_path: str, local_path: str):
    scp_cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "UserKnownHostsFile=/Users/carlosayalaperdomo/.ssh/known_hosts",
        "-P", str(cfg.puerto_ssh or 22),
        f"{cfg.usuario_ssh}@{cfg.host}:{remote_path}",
        local_path
    ]
    proc = subprocess.run(scp_cmd, capture_output=True, text=True)
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or ""
    }


def command_exists_local(bin_path: str) -> bool:
    return bool(bin_path and os.path.exists(bin_path))

def severity_from_nuclei(sev: str):
    s = (sev or "").strip().lower()
    if s == "critical":
        return "Crítica"
    if s == "high":
        return "Alta"
    if s == "medium":
        return "Media"
    if s in ("low", "info", "informational"):
        return "Baja"
    return "Media"

def severity_from_cvss(cvss):
    try:
        score = float(cvss)
        if score >= 9.0:
            return "Crítica"
        elif score >= 7.0:
            return "Alta"
        elif score >= 4.0:
            return "Media"
        return "Baja"
    except Exception:
        return "Media"


def severity_from_text(txt: str):
    s = (txt or "").lower()
    if any(x in s for x in ["critical", "crítica", "critica"]):
        return "Crítica"
    if any(x in s for x in ["high", "alta"]):
        return "Alta"
    if any(x in s for x in ["medium", "media", "moderate"]):
        return "Media"
    return "Baja"


def prioridad_desde_clasificacion(clasificacion: str) -> str:
    c = (clasificacion or "").strip()
    if c in ("Crítica", "Alta"):
        return "Alta"
    if c == "Media":
        return "Media"
    return "Baja"


def calcular_fecha_objetivo_por_clasificacion(clasificacion: str):
    hoy = date.today()
    c = (clasificacion or "").strip()
    if c == "Crítica":
        return hoy + timedelta(days=7)
    if c == "Alta":
        return hoy + timedelta(days=15)
    if c == "Media":
        return hoy + timedelta(days=30)
    return hoy + timedelta(days=45)


def generar_codigo_vulnerabilidad_auto():
    total = db.session.query(func.count(VulnerabilidadRegistro.id)).scalar() or 0
    return f"VULN-AUTO-{total + 1:05d}"


def resumir_hallazgos_run(run):
    qs = VulnerabilityScanFinding.query.filter_by(run_id=run.id).all()
    run.total_hallazgos = len(qs)
    run.criticas = sum(1 for x in qs if x.severidad == "Crítica")
    run.altas = sum(1 for x in qs if x.severidad == "Alta")
    run.medias = sum(1 for x in qs if x.severidad == "Media")
    run.bajas = sum(1 for x in qs if x.severidad == "Baja")

def ejecutar_nuclei(run_id, cfg, target: str, run_dir: str):
    out_jsonl = scan_output_file(run_dir, "nuclei_scan", "jsonl")
    out_txt = scan_output_file(run_dir, "nuclei_scan", "txt")

    cmd = [
        cfg.ruta_nuclei or "/usr/bin/nuclei",
        "-u", target,
        "-silent",
        "-nc",
        "-jsonl-export", out_jsonl,
        "-severity", "critical,high,medium,low",
        "-rate-limit", "150",
        "-bulk-size", "25",
        "-concurrency", "25",
        "-timeout", "10",
        "-retries", "2",
        "-stats"
    ]

    if cfg.modo == "local":
        res = ejecutar_comando_scan(run_id, cfg, cmd)
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write((res["stdout"] or "") + "\n" + (res["stderr"] or ""))
        return res

    remote_base = (cfg.ruta_base_remota or "/tmp").rstrip("/")
    remote_jsonl = f"{remote_base}/nuclei_scan.jsonl"
    remote_txt = f"{remote_base}/nuclei_scan.txt"

    remote_cmd_list = [
        cfg.ruta_nuclei or "/usr/bin/nuclei",
        "-u", target,
        "-silent",
        "-nc",
        "-jsonl-export", remote_jsonl,
        "-severity", "critical,high,medium,low",
        "-rate-limit", "150",
        "-bulk-size", "25",
        "-concurrency", "25",
        "-timeout", "10",
        "-retries", "2",
        "-stats"
    ]

    remote_cmd = " ".join(shlex.quote(str(x)) for x in remote_cmd_list) + f" > {shlex.quote(remote_txt)} 2>&1"

    res = ejecutar_comando_scan(run_id, cfg, cmd, remote_cmd=remote_cmd)

    pull_jsonl = scp_from_remote(cfg, remote_jsonl, out_jsonl)
    if pull_jsonl["returncode"] != 0:
        if "No such file" not in (pull_jsonl["stderr"] or "") and "not found" not in (pull_jsonl["stderr"] or "").lower():
            return {
                "returncode": 1,
                "stdout": "",
                "stderr": f"No se pudo traer salida JSONL de Nuclei: {pull_jsonl['stderr']}"
            }

    pull_txt = scp_from_remote(cfg, remote_txt, out_txt)
    if pull_txt["returncode"] != 0:
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": f"No se pudo traer salida TXT de Nuclei: {pull_txt['stderr']}"
        }

    return res

def extraer_cves_desde_texto(texto: str):
    if not texto:
        return None

    encontrados = re.findall(r"\bCVE-\d{4}-\d{4,7}\b", texto, flags=re.I)
    if not encontrados:
        return None

    # quitar duplicados preservando orden
    vistos = set()
    limpios = []
    for c in encontrados:
        c_norm = c.upper()
        if c_norm not in vistos:
            vistos.add(c_norm)
            limpios.append(c_norm)

    return ", ".join(limpios[:5]) if limpios else None


def parse_nuclei_jsonl(run_dir: str):
    findings = []
    jsonl_file = scan_output_file(run_dir, "nuclei_scan", "jsonl")
    txt_file = scan_output_file(run_dir, "nuclei_scan", "txt")

    if os.path.exists(jsonl_file):
        try:
            with open(jsonl_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = (line or "").strip()
                    if not line:
                        continue

                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue

                    info = obj.get("info") or {}
                    classification = info.get("classification") or {}
                    meta = info.get("metadata") or {}

                    template_id = obj.get("template-id") or obj.get("template") or "nuclei-template"
                    name = info.get("name") or template_id
                    severity_raw = info.get("severity") or obj.get("severity") or "medium"
                    matched_at = obj.get("matched-at") or obj.get("host") or obj.get("url") or ""
                    host = obj.get("host") or ""
                    port = obj.get("port")
                    ip = obj.get("ip") or ""
                    scheme = obj.get("scheme") or ""
                    curl_cmd = obj.get("curl-command") or ""
                    matcher_name = obj.get("matcher-name") or ""
                    extracted = obj.get("extracted-results") or []

                    cve = None
                    cves = classification.get("cve-id") or classification.get("cves") or []

                    if isinstance(cves, list) and cves:
                        cve = ", ".join(str(x).upper() for x in cves[:5] if str(x).strip())
                    elif isinstance(cves, str) and cves.strip():
                        cve = cves.strip().upper()

                    # fallback adicional: buscar CVE en otros campos
                    if not cve:
                        texto_cve = " ".join([
                            str(template_id or ""),
                            str(name or ""),
                            str(obj.get("matched-at") or ""),
                            str(info.get("description") or ""),
                            str(info.get("reference") or ""),
                            str(info.get("tags") or ""),
                            str(classification or {}),
                            str(meta or {}),
                            str(extracted or {})
                        ])
                        cve = extraer_cves_desde_texto(texto_cve)

                    cvss = classification.get("cvss-score") or meta.get("cvss-score")

                    descripcion = []
                    descripcion.append(f"Template: {template_id}")
                    if name and name != template_id:
                        descripcion.append(f"Nombre: {name}")
                    if host:
                        descripcion.append(f"Host: {host}")
                    if scheme:
                        descripcion.append(f"Esquema: {scheme}")
                    if matcher_name:
                        descripcion.append(f"Matcher: {matcher_name}")
                    if extracted:
                        descripcion.append("Extracted: " + ", ".join(str(x) for x in extracted[:5]))

                    evidencia = f"Matched-at: {matched_at}"
                    if ip:
                        evidencia += f" | IP: {ip}"
                    if port:
                        evidencia += f" | Puerto: {port}"
                    if curl_cmd:
                        evidencia += f" | curl: {curl_cmd[:1200]}"

                    findings.append({
                        "fuente": "nuclei",
                        "titulo": f"Nuclei: {name}",
                        "descripcion": " | ".join(descripcion)[:5000],
                        "severidad": severity_from_nuclei(severity_raw),
                        "cvss": cvss,
                        "cve": cve,
                        "puerto": str(port) if port else None,
                        "protocolo": scheme or None,
                        "servicio": template_id,
                        "evidencia": evidencia[:5000],
                        "recomendacion_base": "Validar el hallazgo detectado por Nuclei, confirmar exposición real, aplicar corrección técnica y repetir escaneo."
                    })

        except Exception as e:
            findings.append({
                "fuente": "nuclei",
                "titulo": "Error interpretando salida de Nuclei",
                "descripcion": str(e),
                "severidad": "Media",
                "cvss": None,
                "cve": None,
                "puerto": None,
                "protocolo": None,
                "servicio": None,
                "evidencia": "No fue posible parsear el JSONL de Nuclei.",
                "recomendacion_base": "Validar integridad del archivo JSONL y repetir el escaneo."
            })

    # fallback: si no hubo JSONL pero sí hubo salida txt, registrar al menos líneas útiles
    if not findings and os.path.exists(txt_file):
        try:
            with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = [x.strip() for x in f.readlines() if x.strip()]

            for ln in lines[:200]:
                low = ln.lower()
                if any(k in low for k in ["critical", "high", "medium", "low", "[", "matched", "template"]):
                    findings.append({
                        "fuente": "nuclei",
                        "titulo": "Hallazgo detectado por nuclei",
                        "descripcion": ln[:1000],
                        "severidad": severity_from_text(ln),
                        "cvss": None,
                        "cve": None,
                        "puerto": None,
                        "protocolo": None,
                        "servicio": "nuclei",
                        "evidencia": ln[:1500],
                        "recomendacion_base": "Validar el hallazgo detectado por Nuclei, confirmar exposición real y aplicar corrección técnica."
                    })
        except Exception:
            pass

    return findings


def html_escape(v):
    return escape(v or "")


# ==========================
# Helpers IA - Remediación
# ==========================

def _texto_limpio_para_ai(x):
    return (str(x or "").strip()
            .replace("\r\n", "\n")
            .replace("\r", "\n"))

def _es_ruido_hallazgo_scan(hallazgo: dict) -> bool:
    txt = " ".join([
        _texto_limpio_para_ai(hallazgo.get("titulo")),
        _texto_limpio_para_ai(hallazgo.get("descripcion")),
        _texto_limpio_para_ai(hallazgo.get("evidencia")),
    ]).lower()

    patrones_ruido = [
        "initialising plugin",
        "initializing plugin",
        "loading plugin",
        "nikto_ssl",
        "starting scan",
        "plugin",
        "debug:",
        "trace:",
        "scan started",
        "scan completed"
    ]

    return any(p in txt for p in patrones_ruido)

def _fallback_remediacion_segura(hallazgo: dict) -> dict:
    severidad = (hallazgo.get("severidad") or "").strip().lower()
    prioridad = "Media"

    if severidad in ("crítica", "critica", "critical"):
        prioridad = "Crítica"
    elif severidad in ("alta", "high"):
        prioridad = "Alta"
    elif severidad in ("baja", "low"):
        prioridad = "Baja"

    titulo = (hallazgo.get("titulo") or "hallazgo detectado").strip()

    return {
        "accion_correctiva": (
            f"Validar técnicamente el hallazgo '{titulo}', confirmar su impacto real, "
            f"aplicar la corrección correspondiente en el activo afectado, "
            f"ejecutar una nueva verificación y documentar la evidencia de cierre."
        ),
        "prioridad": prioridad,
        "recursos_necesarios": (
            "Equipo técnico responsable del activo, apoyo de seguridad de la información "
            "y evidencia técnica de validación/cierre."
        )
    }

def sugerir_remediacion_ai(hallazgo: dict) -> dict:
    fallback = _fallback_remediacion_segura(hallazgo)

    try:
        # Si el “hallazgo” realmente es ruido del escáner, no mandar a IA
        if _es_ruido_hallazgo_scan(hallazgo):

            return fallback

        provider = (get_ai_provider() or "openrouter").strip().lower()

        titulo = _texto_limpio_para_ai(hallazgo.get("titulo"))
        descripcion = _texto_limpio_para_ai(hallazgo.get("descripcion"))
        fuente = _texto_limpio_para_ai(hallazgo.get("fuente"))
        severidad = _texto_limpio_para_ai(hallazgo.get("severidad"))
        cve = _texto_limpio_para_ai(hallazgo.get("cve"))
        cvss = _texto_limpio_para_ai(hallazgo.get("cvss"))
        puerto = _texto_limpio_para_ai(hallazgo.get("puerto"))
        servicio = _texto_limpio_para_ai(hallazgo.get("servicio"))
        evidencia = _texto_limpio_para_ai(hallazgo.get("evidencia"))

        prompt = f"""
CONTEXTO DEFENSIVO:
Estoy gestionando un programa de remediación de vulnerabilidades en una organización.
Necesito una recomendación DEFENSIVA para corregir un hallazgo detectado por herramientas de seguridad.
No estoy pidiendo explotación, ataque ni instrucciones ofensivas.

Hallazgo:
- Título: {titulo}
- Descripción: {descripcion}
- Fuente: {fuente}
- Severidad: {severidad}
- CVE: {cve}
- CVSS: {cvss}
- Puerto: {puerto}
- Servicio: {servicio}
- Evidencia: {evidencia}

Devuelve SOLO JSON válido con esta estructura exacta:
{{
  "accion_correctiva": "texto",
  "prioridad": "Crítica|Alta|Media|Baja",
  "recursos_necesarios": "texto"
}}

Reglas:
- Responder en español.
- Enfoque 100% defensivo.
- No incluir explicación adicional fuera del JSON.
- Si la evidencia es limitada, dar una remediación conservadora y segura.
""".strip()

        raw = ai_text_general(
            prompt=prompt,
            system_prompt="Eres un consultor senior de ciberseguridad defensiva. Responde solo JSON válido.",
            temperature=0.2,
            max_tokens=300
        )


        if not raw:
            return fallback

        # Si Ollama rechaza por política o responde texto libre, usar fallback
        rechazo = [
            "no puedo proporcionar asistencia",
            "no puedo ayudar",
            "i can't help",
            "i cannot help",
            "malicios",
            "dañinas",
            "harmful"
        ]
        raw_l = raw.lower()
        if any(p in raw_l for p in rechazo):

            return fallback

        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            print("DEBUG REMEDIACION AI - no vino JSON válido, usando fallback.")
            return fallback

        data = json.loads(m.group(0))

        accion = (data.get("accion_correctiva") or "").strip()
        prioridad = (data.get("prioridad") or "").strip()
        recursos = (data.get("recursos_necesarios") or "").strip()

        return {
            "accion_correctiva": accion or fallback["accion_correctiva"],
            "prioridad": prioridad or fallback["prioridad"],
            "recursos_necesarios": recursos or fallback["recursos_necesarios"]
        }

    except Exception as e:

        return fallback

def ejecutar_comando_scan(run_id, cfg, cmd_local, remote_cmd=None):
    if cfg.modo == "local":
        return run_local_command_stream(run_id, cmd_local)

    if not cfg.host or not cfg.usuario_ssh:
        return {"returncode": 1, "stdout": "", "stderr": "Configuración remota incompleta (host/usuario_ssh)."}

    if not remote_cmd:
        remote_cmd = " ".join(shlex.quote(str(x)) for x in cmd_local)

    return run_remote_command_stream(run_id, cfg, remote_cmd)


def ejecutar_nmap(run_id, cfg, host_objetivo: str, run_dir: str):
    xml_file = scan_output_file(run_dir, "nmap_scan", "xml")
    xml_fast = scan_output_file(run_dir, "nmap_fast", "xml")

    # =========================
    # FASE 1: descubrimiento rápido
    # =========================
    scan_set_progress(run_id, pct=10, stage="Nmap: descubriendo puertos", tool="nmap")


    cmd_fast = [
        cfg.ruta_nmap or "/usr/bin/nmap",
        "-n",                 # sin DNS
        "-Pn",                # tratar host como activo
        "--top-ports", "1000",
        "-T4",
        "--max-retries", "2",
        "--host-timeout", "5m",
        "-oX", xml_fast,
        host_objetivo
    ]

    if cfg.modo == "local":
        res_fast = ejecutar_comando_scan(run_id, cfg, cmd_fast)
    else:
        remote_base = (cfg.ruta_base_remota or "/tmp").rstrip("/")
        remote_xml_fast = f"{remote_base}/nmap_fast.xml"
        remote_cmd_fast = " ".join(shlex.quote(str(x)) for x in [
            cfg.ruta_nmap or "/usr/bin/nmap",
            "-n",
            "-Pn",
            "--top-ports", "1000",
            "-T4",
            "--max-retries", "2",
            "--host-timeout", "5m",
            "-oX", remote_xml_fast,
            host_objetivo
        ])
        res_fast = ejecutar_comando_scan(run_id, cfg, cmd_fast, remote_cmd=remote_cmd_fast)

        if res_fast["returncode"] == 0:
            pull = scp_from_remote(cfg, remote_xml_fast, xml_fast)
            if pull["returncode"] != 0:
                return {
                    "returncode": 1,
                    "stdout": res_fast["stdout"],
                    "stderr": f"No se pudo traer XML rápido remoto: {pull['stderr']}"
                }

    if res_fast["returncode"] != 0:
        return res_fast

    puertos_abiertos = obtener_puertos_abiertos_desde_xml(xml_fast)

    if not puertos_abiertos:
        # copiar xml rápido como xml final si no hay puertos
        shutil.copyfile(xml_fast, xml_file)
        return res_fast
    scan_set_progress(run_id, pct=20, stage="Nmap: puertos descubiertos", tool="nmap")

    

    # =========================
    # FASE 2: análisis detallado solo de puertos abiertos
    # =========================
    scan_set_progress(run_id, pct=25, stage="Nmap: analizando servicios abiertos", tool="nmap")

    puertos_str = ",".join(puertos_abiertos)

    cmd_detail = [
        cfg.ruta_nmap or "/usr/bin/nmap",
        "-n",
        "-Pn",
        "-sV",
        "-sC",
        "-p", puertos_str,
        "-T4",
        "--max-retries", "2",
        "--host-timeout", "10m",
        "-oX", xml_file,
        host_objetivo
    ]

    # OJO: quitamos -O para hacer el escaneo más eficiente
    # Si luego quieres OS detection, que sea opcional con checkbox

    if cfg.modo == "local":
        return ejecutar_comando_scan(run_id, cfg, cmd_detail)

    remote_base = (cfg.ruta_base_remota or "/tmp").rstrip("/")
    remote_xml = f"{remote_base}/nmap_scan.xml"
    remote_cmd_detail = " ".join(shlex.quote(str(x)) for x in [
        cfg.ruta_nmap or "/usr/bin/nmap",
        "-n",
        "-Pn",
        "-sV",
        "-sC",
        "-p", puertos_str,
        "-T4",
        "--max-retries", "2",
        "--host-timeout", "10m",
        "-oX", remote_xml,
        host_objetivo
    ])

    res_detail = ejecutar_comando_scan(run_id, cfg, cmd_detail, remote_cmd=remote_cmd_detail)

    if res_detail["returncode"] == 0:
        pull = scp_from_remote(cfg, remote_xml, xml_file)
        if pull["returncode"] != 0:
            return {
                "returncode": 1,
                "stdout": res_detail["stdout"],
                "stderr": f"No se pudo traer XML remoto: {pull['stderr']}"
            }

    scan_set_progress(run_id, pct=30, stage="Nmap finalizado", tool="nmap")

    return res_detail


def ejecutar_whatweb(run_id, cfg, target: str, run_dir: str):
    out_file = scan_output_file(run_dir, "whatweb_scan", "txt")
    cmd = [cfg.ruta_whatweb or "/usr/bin/whatweb", target]

    if cfg.modo == "local":
        res = ejecutar_comando_scan(run_id, cfg, cmd)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(res["stdout"] or "")
        return res

    remote_base = (cfg.ruta_base_remota or "/tmp").rstrip("/")
    remote_file = f"{remote_base}/whatweb_scan.txt"
    remote_cmd = f"{shlex.quote(cfg.ruta_whatweb or '/usr/bin/whatweb')} {shlex.quote(target)} > {shlex.quote(remote_file)} 2>&1"
    res = ejecutar_comando_scan(run_id, cfg, cmd, remote_cmd=remote_cmd)
    pull = scp_from_remote(cfg, remote_file, out_file)
    if pull["returncode"] != 0:
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": f"No se pudo traer salida de Nikto: {pull['stderr']}"
        }

    return res


def ejecutar_nikto(run_id, cfg, target: str, run_dir: str):
    out_file = scan_output_file(run_dir, "nikto_scan", "txt")

    cmd = [
        cfg.ruta_nikto or "/usr/bin/nikto",
        "-h", target,
        "-Tuning", "1234567890abcx",
        "-timeout", "8",
        "-maxtime", "8m",
        "-nointeractive",
        "-ask", "no",
        "-C", "all",
        "-Display", "V"
    ]

    if cfg.modo == "local":
        res = ejecutar_comando_scan(run_id, cfg, cmd)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write((res["stdout"] or "") + "\n" + (res["stderr"] or ""))
        return res

    remote_base = (cfg.ruta_base_remota or "/tmp").rstrip("/")
    remote_file = f"{remote_base}/nikto_scan.txt"

    remote_cmd = " ".join(shlex.quote(str(x)) for x in cmd) + f" > {shlex.quote(remote_file)} 2>&1"

    res = ejecutar_comando_scan(run_id, cfg, cmd, remote_cmd=remote_cmd)

    pull = scp_from_remote(cfg, remote_file, out_file)
    if pull["returncode"] != 0:
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": f"No se pudo traer salida de Nikto: {pull['stderr']}"
        }

    return res

def validar_herramientas_scan(cfg):
    faltantes = []

    herramientas = [
        ("Nmap", cfg.ruta_nmap),
        ("Nikto", cfg.ruta_nikto),
        ("Nuclei", cfg.ruta_nuclei),
        ("testssl", cfg.ruta_testssl),
        ("OWASP ZAP", cfg.ruta_zap),
    ]

    if cfg.modo == "local":
        for nombre, ruta in herramientas:
            ruta = (ruta or "").strip()
            if not ruta:
                faltantes.append(f"{nombre}: ruta vacía")
                continue
            if not os.path.exists(ruta):
                faltantes.append(f"{nombre}: {ruta}")
        return faltantes

    if cfg.modo == "remoto":
        if not (cfg.host and cfg.usuario_ssh):
            faltantes.append("Configuración remota incompleta: host/usuario_ssh")
            return faltantes

        for nombre, ruta in herramientas:
            ruta = (ruta or "").strip()
            if not ruta:
                faltantes.append(f"{nombre}: ruta vacía")
        return faltantes

    faltantes.append(f"Modo inválido: {cfg.modo}")
    return faltantes

def ejecutar_testssl(run_id, cfg, target: str, run_dir: str):
    out_file = scan_output_file(run_dir, "testssl_scan", "txt")

    cmd = [
        cfg.ruta_testssl or "/usr/bin/testssl",
        "--warnings", "batch",
        "--openssl-timeout", "8",
        "--connect-timeout", "8",
        "--color", "0",
        target
    ]

    if cfg.modo == "local":
        res = ejecutar_comando_scan(run_id, cfg, cmd)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write((res["stdout"] or "") + "\n" + (res["stderr"] or ""))
        return res

    remote_base = (cfg.ruta_base_remota or "/tmp").rstrip("/")
    remote_file = f"{remote_base}/testssl_scan.txt"
    remote_cmd = " ".join(shlex.quote(str(x)) for x in cmd) + f" > {shlex.quote(remote_file)} 2>&1"

    res = ejecutar_comando_scan(run_id, cfg, cmd, remote_cmd=remote_cmd)

    pull = scp_from_remote(cfg, remote_file, out_file)
    if pull["returncode"] != 0:
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": f"No se pudo traer salida de testssl: {pull['stderr']}"
        }

    return res


def parse_nmap_xml(run_dir: str):
    findings = []
    xml_file = scan_output_file(run_dir, "nmap_scan", "xml")
    if not os.path.exists(xml_file):
        return findings

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for host in root.findall("host"):
            addr = host.find("address")
            ip_val = addr.attrib.get("addr") if addr is not None else ""

            ports = host.find("ports")
            if ports is None:
                continue

            for port in ports.findall("port"):
                portid = port.attrib.get("portid", "")
                protocol = port.attrib.get("protocol", "")
                state_el = port.find("state")
                service_el = port.find("service")

                state = state_el.attrib.get("state", "") if state_el is not None else ""
                service_name = service_el.attrib.get("name", "") if service_el is not None else ""
                product = service_el.attrib.get("product", "") if service_el is not None else ""
                version = service_el.attrib.get("version", "") if service_el is not None else ""

                if state == "open":
                    titulo = f"Puerto {portid}/{protocol} abierto"
                    extrainfo = service_el.attrib.get("extrainfo", "") if service_el is not None else ""
                    tunnel = service_el.attrib.get("tunnel", "") if service_el is not None else ""

                    desc = " ".join(
                        x for x in [
                            "Servicio detectado:",
                            service_name,
                            product,
                            version,
                            f"({extrainfo})" if extrainfo else "",
                            f"[{tunnel}]" if tunnel else ""
                        ] if x
                    ).strip()

                    sev = "Media"
                    if portid in ("21", "23", "3389", "445"):
                        sev = "Alta"
                    elif portid in ("80", "443", "8080", "8443", "22"):
                        sev = "Media"

                    findings.append({
                        "fuente": "nmap",
                        "titulo": titulo,
                        "descripcion": desc,
                        "severidad": sev,
                        "cvss": None,
                        "cve": None,
                        "puerto": portid,
                        "protocolo": protocol,
                        "servicio": " ".join(
                            x for x in [service_name, product, version, extrainfo, tunnel] if x
                        ).strip(),
                        "evidencia": f"Host: {ip_val} | Puerto: {portid}/{protocol} | Estado: {state}",
                        "recomendacion_base": "Revisar necesidad del servicio expuesto, restringir acceso y aplicar hardening."
                    })
    except Exception as e:
        findings.append({
            "fuente": "nmap",
            "titulo": "Error interpretando salida de Nmap",
            "descripcion": str(e),
            "severidad": "Media",
            "cvss": None,
            "cve": None,
            "puerto": None,
            "protocolo": None,
            "servicio": None,
            "evidencia": "No fue posible parsear el XML de Nmap.",
            "recomendacion_base": "Validar integridad del archivo XML y repetir el escaneo."
        })

    return findings


def parse_txt_findings_generic(file_path: str, fuente: str):
    findings = []
    if not os.path.exists(file_path):
        return findings

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [x.strip() for x in f.readlines() if x.strip()]

        for ln in lines[:500]:
            low = ln.lower()
            sev = severity_from_text(ln)

            if fuente == "nikto":
                trigger = any(k in low for k in [
                    "osvdb",
                    "vulnerable",
                    "warning",
                    "error",
                    "cookie",
                    "header",
                    "ssl",
                    "tls",
                    "cgi",
                    "x-frame-options",
                    "x-content-type-options",
                    "missing",
                    "allowed",
                    "exposed",
                    "retrieved",
                    "entry",
                    "outdated",
                    "apache",
                    "nginx",
                    "php",
                    "directory indexing",
                    "server leaks"
                ])
                if not trigger:
                    continue

                if any(k in low for k in ["vulnerable", "remote code", "sql injection", "xss", "rce", "traversal"]):
                    sev = "Alta"
                elif any(k in low for k in ["missing", "header", "cookie", "ssl", "tls", "warning"]):
                    sev = "Media"

            elif fuente == "whatweb":
                trigger = any(k in low for k in [
                    "apache", "nginx", "php", "wordpress", "jquery",
                    "drupal", "joomla", "server", "x-powered-by",
                    "bootstrap", "iis", "tomcat"
                ])
                if not trigger:
                    continue

            elif fuente == "testssl":
                trigger = any(k in low for k in [
                    "weak", "vulnerable", "critical", "high", "medium",
                    "ssl", "tls", "rc4", "3des", "heartbleed", "robot",
                    "renegotiation", "deprecated", "cbc", "beast", "lucky13",
                    "sweet32", "crime", "poodle", "certificate", "expired",
                    "self-signed", "tls1", "tls 1.0", "tls 1.1"
                ])
                if not trigger:
                    continue

                if any(k in low for k in ["critical", "heartbleed", "robot", "poodle", "sweet32"]):
                    sev = "Alta"

            cve_detectado = extraer_cves_desde_texto(ln)

            findings.append({
                "fuente": fuente,
                "titulo": ln[:220],
                "descripcion": ln[:1000],
                "severidad": sev,
                "cvss": None,
                "cve": cve_detectado,
                "puerto": None,
                "protocolo": None,
                "servicio": None,
                "evidencia": ln[:1500],
                "recomendacion_base": f"Revisar y corregir la condición reportada por {fuente}, aplicar hardening y volver a validar."
            })

    except Exception as e:
        findings.append({
            "fuente": fuente,
            "titulo": f"Error interpretando salida de {fuente}",
            "descripcion": str(e),
            "severidad": "Media",
            "cvss": None,
            "cve": None,
            "puerto": None,
            "protocolo": None,
            "servicio": None,
            "evidencia": "No fue posible parsear la salida textual.",
            "recomendacion_base": "Validar salida de la herramienta y repetir el escaneo."
        })

    return findings

def ejecutar_zap(run_id, cfg, target: str, run_dir: str):
    out_html = scan_output_file(run_dir, "zap_scan", "html")
    out_txt = scan_output_file(run_dir, "zap_scan", "txt")

    os.makedirs(run_dir, exist_ok=True)

    docker_image = "ghcr.io/zaproxy/zaproxy:stable"

    if cfg.modo == "local":
        cmd = [
            "bash",
            "-lc",
            (
                f"rm -f {shlex.quote(out_html)} {shlex.quote(out_txt)}; "
                f"echo '[OWASP_ZAP] Ejecutando escaneo NORMAL con Docker ZAP' > {shlex.quote(out_txt)}; "

                f"docker run --rm "
                f"-v {shlex.quote(run_dir)}:/zap/wrk/:rw "
                f"{docker_image} "
                f"zap-baseline.py "
                f"-t {shlex.quote(target)} "
                f"-r zap_scan.html "
                f"-I "
                f">> {shlex.quote(out_txt)} 2>&1; "

                f"if [ ! -f {shlex.quote(out_html)} ]; then "
                f"echo '<html><body><h2>OWASP ZAP no generó reporte HTML</h2><pre>' > {shlex.quote(out_html)}; "
                f"cat {shlex.quote(out_txt)} >> {shlex.quote(out_html)} 2>/dev/null; "
                f"echo '</pre></body></html>' >> {shlex.quote(out_html)}; "
                f"fi; "

                f"ls -lh {shlex.quote(out_html)} {shlex.quote(out_txt)} 2>&1"
            )
        ]

        res = ejecutar_comando_scan(run_id, cfg, cmd)

        return {
            "returncode": res.get("returncode", 0),
            "stdout": res.get("stdout") or "",
            "stderr": res.get("stderr") or ""
        }

    remote_base = (cfg.ruta_base_remota or "/tmp").rstrip("/")
    remote_dir = f"{remote_base}/zap_normal_scan_{run_id}"
    remote_html = f"{remote_dir}/zap_scan.html"
    remote_txt = f"{remote_dir}/zap_scan.txt"

    remote_cmd = (
        f"mkdir -p {shlex.quote(remote_dir)}; "
        f"rm -f {shlex.quote(remote_html)} {shlex.quote(remote_txt)}; "

        f"echo '[OWASP_ZAP] Ejecutando escaneo NORMAL con Docker ZAP remoto' > {shlex.quote(remote_txt)}; "
        f"echo '[OWASP_ZAP] Target: {shlex.quote(target)}' >> {shlex.quote(remote_txt)}; "
        f"docker images | grep zaproxy >> {shlex.quote(remote_txt)} 2>&1 || true; "

        f"docker run --rm "
        f"-v {shlex.quote(remote_dir)}:/zap/wrk/:rw "
        f"{docker_image} "
        f"zap-baseline.py "
        f"-t {shlex.quote(target)} "
        f"-r zap_scan.html "
        f"-I "
        f">> {shlex.quote(remote_txt)} 2>&1; "

        f"if [ ! -f {shlex.quote(remote_html)} ]; then "
        f"echo '<html><body><h2>OWASP ZAP no generó reporte HTML</h2><pre>' > {shlex.quote(remote_html)}; "
        f"cat {shlex.quote(remote_txt)} >> {shlex.quote(remote_html)} 2>/dev/null; "
        f"echo '</pre></body></html>' >> {shlex.quote(remote_html)}; "
        f"fi; "

        f"ls -lh {shlex.quote(remote_html)} {shlex.quote(remote_txt)} 2>&1"
    )

    res = ejecutar_comando_scan(
        run_id,
        cfg,
        ["bash", "-lc", "echo OWASP ZAP normal remoto"],
        remote_cmd=remote_cmd
    )

    scp_from_remote(cfg, remote_txt, out_txt)
    pull_html = scp_from_remote(cfg, remote_html, out_html)

    if pull_html["returncode"] != 0:
        return {
            "returncode": 1,
            "stdout": res.get("stdout") or "",
            "stderr": (
                "No se pudo traer reporte HTML de OWASP ZAP normal. "
                f"Detalle SCP: {pull_html.get('stderr') or ''}\n\n"
                f"Salida remota:\n{res.get('stdout') or ''}\n{res.get('stderr') or ''}"
            )
        }

    return {
        "returncode": res.get("returncode", 0),
        "stdout": res.get("stdout") or "",
        "stderr": res.get("stderr") or ""
    }


def parse_zap_findings(run_dir: str):
    findings = []
    html_file = scan_output_file(run_dir, "zap_scan", "html")
    txt_file = scan_output_file(run_dir, "zap_scan", "txt")

    if os.path.exists(html_file):
        try:
            with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            patrones = re.findall(
                r'<h3[^>]*>(.*?)</h3>.*?Risk.*?<td.*?>(.*?)</td>.*?Description</td>\s*<td.*?>(.*?)</td>',
                content,
                re.I | re.S
            )

            for titulo, risk, descripcion in patrones:
                titulo = html.unescape(re.sub(r'<.*?>', '', titulo)).strip()
                risk = html.unescape(re.sub(r'<.*?>', '', risk)).strip()
                descripcion = html.unescape(re.sub(r'<.*?>', ' ', descripcion)).strip()

                titulo = re.sub(r'Generated on.*', '', titulo, flags=re.I | re.S).strip()

                if not titulo:
                    titulo = "OWASP ZAP Finding"

                findings.append({
                    "fuente": "owasp_zap",
                    "titulo": f"OWASP ZAP: {titulo}"[:500],
                    "descripcion": descripcion[:5000],
                    "severidad": severity_from_text(risk),
                    "cvss": None,
                    "cve": extraer_cves_desde_texto(descripcion),
                    "puerto": None,
                    "protocolo": "http/https",
                    "servicio": "web",
                    "evidencia": f"Hallazgo identificado por OWASP ZAP ({risk})",
                    "recomendacion_base": "Validar el hallazgo reportado por OWASP ZAP y aplicar remediación."
                })

        except Exception as e:
            findings.append({
                "fuente": "owasp_zap",
                "titulo": "Error interpretando OWASP ZAP",
                "descripcion": str(e),
                "severidad": "Media",
                "cvss": None,
                "cve": None,
                "puerto": None,
                "protocolo": "http/https",
                "servicio": "web",
                "evidencia": "No fue posible interpretar el reporte HTML.",
                "recomendacion_base": "Validar el parser de OWASP ZAP."
            })

    if not findings and os.path.exists(txt_file):
        try:
            with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = [x.strip() for x in f.readlines() if x.strip()]

            for ln in lines:
                low = ln.lower()

                if any(x in low for x in [
                    "warn-new:",
                    "fail-new:",
                    "x-frame-options",
                    "content-security-policy",
                    "cookie",
                    "missing",
                    "server leaks",
                    "strict-transport-security"
                ]):
                    findings.append({
                        "fuente": "owasp_zap",
                        "titulo": f"OWASP ZAP: {ln[:180]}",
                        "descripcion": ln[:1000],
                        "severidad": severity_from_text(ln),
                        "cvss": None,
                        "cve": extraer_cves_desde_texto(ln),
                        "puerto": None,
                        "protocolo": "http/https",
                        "servicio": "web",
                        "evidencia": ln[:1500],
                        "recomendacion_base": "Validar el hallazgo reportado por OWASP ZAP y aplicar remediación."
                    })
        except Exception:
            pass

    unicos = []
    vistos = set()

    for h in findings:
        key = (
            h.get("titulo"),
            h.get("evidencia")
        )

        if key in vistos:
            continue

        vistos.add(key)
        unicos.append(h)

    return unicos

def crear_vulnerabilidad_desde_hallazgo(run, hallazgo):
    item = VulnerabilidadRegistro(
        clasificacion=hallazgo.get("severidad"),
        codigo=generar_codigo_vulnerabilidad_auto(),
        activo=run.target,
        descripcion_vulnerabilidad=(
            (hallazgo.get("titulo") or "Hallazgo técnico")
            + (" | " + hallazgo.get("descripcion") if hallazgo.get("descripcion") else "")
        )[:4000],
        cve=(hallazgo.get("cve") or "").strip().upper() or None,
        cvss=str(hallazgo.get("cvss")) if hallazgo.get("cvss") is not None else None,
        fecha_identificacion=date.today(),
        fecha_cierre=None,
        estado="Abierto",
        responsable=run.responsable_asignado or run.ejecutado_por or "Pendiente",
        riesgo_residual=(hallazgo.get("evidencia") or "")[:4000]
    )
    db.session.add(item)
    db.session.flush()
    return item


def crear_plan_remediacion_auto(vuln, hallazgo):
    rem = sugerir_remediacion_ai(hallazgo)

    plan = PlanRemediacion(
        vulnerabilidad_id=vuln.id,
        accion_correctiva=rem.get("accion_correctiva") or "Pendiente de definir",
        responsable=vuln.responsable or "Pendiente",
        prioridad=rem.get("prioridad") or prioridad_desde_clasificacion(vuln.clasificacion),
        fecha_objetivo=calcular_fecha_objetivo_por_clasificacion(vuln.clasificacion),
        recursos_necesarios=rem.get("recursos_necesarios"),
        estado="Abierto"
    )
    db.session.add(plan)
    db.session.flush()
    return plan

def ejecutar_scan_web(run, cfg, run_dir: str, crear_vulns=True, crear_planes=True):
    target = normalizar_target_para_scan(run.target)
    host = extraer_host_de_target(target)
    logs = []

    try:
        herramientas = json.loads(run.herramientas or "[]")
    except Exception:
        herramientas = []

    if not herramientas:
        herramientas = ["nmap", "nikto", "nuclei", "whatweb", "testssl", "zap"]

    # =========================
    # NMAP
    # =========================
    if "nmap" in herramientas:

        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=5, stage="Preparando Nmap", tool="nmap")

        if host:
            res_nmap = ejecutar_nmap(run.id, cfg, host, run_dir)
            logs.append(f"[NMAP]\nSTDOUT:\n{res_nmap['stdout']}\nSTDERR:\n{res_nmap['stderr']}\n")

            findings = parse_nmap_xml(run_dir)

            guardar_findings_y_sincronizar(
                run,
                findings,
                run_dir,
                crear_vulns,
                crear_planes
            )

    # =========================
    # WHATWEB
    # =========================
    if "whatweb" in herramientas:

        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=35, stage="Ejecutando WhatWeb", tool="whatweb")

        res_whatweb = ejecutar_whatweb(run.id, cfg, target, run_dir)
        logs.append(f"[WHATWEB]\nSTDOUT:\n{res_whatweb['stdout']}\nSTDERR:\n{res_whatweb['stderr']}\n")

        findings = parse_txt_findings_generic(
            scan_output_file(run_dir, "whatweb_scan", "txt"),
            "whatweb"
        )

        guardar_findings_y_sincronizar(
            run,
            findings,
            run_dir,
            crear_vulns,
            crear_planes
        )

    # =========================
    # NIKTO
    # =========================
    if "nikto" in herramientas:

        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=45, stage="Ejecutando Nikto", tool="nikto")

        res_nikto = ejecutar_nikto(run.id, cfg, target, run_dir)
        logs.append(f"[NIKTO]\nSTDOUT:\n{res_nikto['stdout']}\nSTDERR:\n{res_nikto['stderr']}\n")

        findings = parse_txt_findings_generic(
            scan_output_file(run_dir, "nikto_scan", "txt"),
            "nikto"
        )

        guardar_findings_y_sincronizar(
            run,
            findings,
            run_dir,
            crear_vulns,
            crear_planes
        )

    # =========================
    # TESTSSL
    # =========================
    if "testssl" in herramientas:

        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        ssl_target = target

        if ssl_target.startswith("http://"):
            ssl_target = "https://" + ssl_target.replace("http://", "", 1)

        scan_set_progress(run.id, pct=60, stage="Ejecutando testssl", tool="testssl")

        res_testssl = ejecutar_testssl(run.id, cfg, ssl_target, run_dir)
        logs.append(f"[TESTSSL]\nSTDOUT:\n{res_testssl['stdout']}\nSTDERR:\n{res_testssl['stderr']}\n")

        findings = parse_txt_findings_generic(
            scan_output_file(run_dir, "testssl_scan", "txt"),
            "testssl"
        )

        guardar_findings_y_sincronizar(
            run,
            findings,
            run_dir,
            crear_vulns,
            crear_planes
        )

    # =========================
    # NUCLEI
    # =========================
    if "nuclei" in herramientas:

        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=75, stage="Ejecutando Nuclei", tool="nuclei")

        res_nuclei = ejecutar_nuclei(run.id, cfg, target, run_dir)
        logs.append(f"[NUCLEI]\nSTDOUT:\n{res_nuclei['stdout']}\nSTDERR:\n{res_nuclei['stderr']}\n")

        findings = parse_nuclei_jsonl(run_dir)

        guardar_findings_y_sincronizar(
            run,
            findings,
            run_dir,
            crear_vulns,
            crear_planes
        )

    # =========================
    # OWASP ZAP
    # =========================
    if "zap" in herramientas:

        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=90, stage="Ejecutando OWASP ZAP", tool="zap")

        res_zap = ejecutar_zap(run.id, cfg, target, run_dir)
        logs.append(f"[OWASP_ZAP]\nSTDOUT:\n{res_zap['stdout']}\nSTDERR:\n{res_zap['stderr']}\n")

        findings = parse_zap_findings(run_dir)

        guardar_findings_y_sincronizar(
            run,
            findings,
            run_dir,
            crear_vulns,
            crear_planes
        )

    return logs


def ejecutar_scan_ip(run, cfg, run_dir: str, crear_vulns=True, crear_planes=True):
    target = (run.target or "").strip()
    logs = []

    # =========================
    # NMAP
    # =========================
    if scan_check_cancel(run.id):
        scan_mark_stopped(run.id)
        return logs

    scan_set_progress(run.id, pct=5, stage="Preparando Nmap", tool="nmap")

    res_nmap = ejecutar_nmap(run.id, cfg, target, run_dir)
    logs.append(f"[NMAP]\nSTDOUT:\n{res_nmap['stdout']}\nSTDERR:\n{res_nmap['stderr']}\n")

    findings = parse_nmap_xml(run_dir)
    guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

    findings_bd = VulnerabilityScanFinding.query.filter_by(run_id=run.id).all()
    puertos_web = [f for f in findings_bd if (f.puerto or "") in ("80", "443", "8080", "8443")]

    if puertos_web:
        http_target = f"http://{target}"
        https_target = f"https://{target}"

        # =========================
        # NIKTO
        # =========================
        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=35, stage="Ejecutando Nikto", tool="nikto")

        res_nikto = ejecutar_nikto(run.id, cfg, http_target, run_dir)
        logs.append(f"[NIKTO]\nSTDOUT:\n{res_nikto['stdout']}\nSTDERR:\n{res_nikto['stderr']}\n")

        findings = parse_txt_findings_generic(
            scan_output_file(run_dir, "nikto_scan", "txt"),
            "nikto"
        )
        guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

        # =========================
        # TESTSSL
        # =========================
        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        tiene_ssl = any((f.puerto or "") in ("443", "8443") for f in puertos_web)
        if tiene_ssl:
            scan_set_progress(run.id, pct=60, stage="Ejecutando testssl", tool="testssl")

            res_testssl = ejecutar_testssl(run.id, cfg, https_target, run_dir)
            logs.append(f"[TESTSSL]\nSTDOUT:\n{res_testssl['stdout']}\nSTDERR:\n{res_testssl['stderr']}\n")

            findings = parse_txt_findings_generic(
                scan_output_file(run_dir, "testssl_scan", "txt"),
                "testssl"
            )
            guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

        # =========================
        # NUCLEI
        # =========================
        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        nuclei_target = https_target if any((f.puerto or "") == "443" for f in puertos_web) else http_target

        scan_set_progress(run.id, pct=82, stage="Ejecutando Nuclei", tool="nuclei")

        res_nuclei = ejecutar_nuclei(run.id, cfg, nuclei_target, run_dir)
        logs.append(f"[NUCLEI]\nSTDOUT:\n{res_nuclei['stdout']}\nSTDERR:\n{res_nuclei['stderr']}\n")

        findings = parse_nuclei_jsonl(run_dir)
        guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

    return logs

def guardar_findings_y_sincronizar(run, findings, run_dir: str, crear_vulns=True, crear_planes=True):
    created_vulns = 0
    created_planes = 0
    streamed_now = 0

    for h in findings:
        # evitar duplicado simple
        existe = VulnerabilityScanFinding.query.filter_by(
            run_id=run.id,
            fuente=h.get("fuente") or "scanner",
            titulo=(h.get("titulo") or "Hallazgo técnico")[:500],
            evidencia=(h.get("evidencia") or "")[:5000]
        ).first()
        if existe:
            continue

        rec = VulnerabilityScanFinding(
            run_id=run.id,
            fuente=h.get("fuente") or "scanner",
            titulo=(h.get("titulo") or "Hallazgo técnico")[:500],
            descripcion=(h.get("descripcion") or "")[:5000],
            severidad=h.get("severidad") or "Media",
            cvss=str(h.get("cvss")) if h.get("cvss") is not None else None,
            cve=((h.get("cve") or "").strip().upper() or None),
            puerto=(h.get("puerto") or None),
            protocolo=(h.get("protocolo") or None),
            servicio=(h.get("servicio") or None),
            evidencia=(h.get("evidencia") or "")[:5000],
            recomendacion_base=(h.get("recomendacion_base") or "")[:5000]
        )
        db.session.add(rec)
        db.session.flush()

        vuln = None

        if crear_vulns:
            vuln = crear_vulnerabilidad_desde_hallazgo(run, h)
            rec.vulnerabilidad_registro_id = vuln.id
            created_vulns += 1

            if crear_planes:
                crear_plan_remediacion_auto(vuln, h)
                created_planes += 1

        # =========================
        # MODELAMIENTO DE AMENAZAS AUTOMÁTICO
        # =========================
        crear_threat_model_desde_hallazgo(
            run=run,
            hallazgo=h,
            vuln=vuln,
            finding_rec=rec
        )

        streamed_now += 1

        run.findings_streamed = (run.findings_streamed or 0) + 1
        run.created_vulns = (run.created_vulns or 0) + (1 if crear_vulns else 0)
        run.created_plans = (run.created_plans or 0) + (1 if (crear_vulns and crear_planes) else 0)

        db.session.commit()

    resumen = {
        "run_id": run.id,
        "target": run.target,
        "target_type": run.target_type,
        "estado": run.estado,
        "total_findings": VulnerabilityScanFinding.query.filter_by(run_id=run.id).count(),
        "created_vulns": run.created_vulns or 0,
        "created_planes": run.created_plans or 0,
        "generated_at": datetime.utcnow().isoformat()
    }

    resumen_path = scan_output_file(run_dir, "summary", "json")
    with open(resumen_path, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    run.archivo_resumen_json = resumen_path
    db.session.commit()
    return created_vulns, created_planes, streamed_now

def scan_set_progress(run_id, pct=None, stage=None, tool=None):
    run = VulnerabilityScanRun.query.get(run_id)
    if not run:
        return

    if pct is not None:
        run.progress_pct = max(0, min(100, int(pct)))
    if stage is not None:
        run.current_stage = stage
    if tool is not None:
        run.current_tool = tool

    db.session.commit()


def scan_check_cancel(run_id):
    run = VulnerabilityScanRun.query.get(run_id)
    if not run:
        return False
    return bool(run.cancel_requested)


def scan_mark_stopped(run_id, msg="Escaneo detenido por el usuario."):
    run = VulnerabilityScanRun.query.get(run_id)
    if not run:
        return

    run.estado = "detenido"
    run.stopped_by_user = True
    run.error_detalle = msg
    run.fecha_fin = datetime.utcnow()
    run.progress_pct = min(run.progress_pct or 0, 99)
    run.current_stage = "Escaneo detenido"
    run.current_tool = None
    run.active_pid = None
    run.active_command = None
    db.session.commit()

def ejecutar_full_scan(run_id: int, crear_vulns=True, crear_planes=True):
    run = VulnerabilityScanRun.query.get_or_404(run_id)

    run.estado = "ejecutando"
    run.fecha_inicio = datetime.utcnow()
    run.progress_pct = 1
    run.current_stage = "Inicializando escaneo con herramientas seleccionadas"
    run.current_tool = "dispatcher"
    run.cancel_requested = False
    run.stopped_by_user = False
    run.active_pid = None
    run.active_command = None
    db.session.commit()

    run_dir = scan_run_dir(run.id, run.target)
    log_path = scan_output_file(run_dir, "scan_log", "txt")

    try:
        cfg = _scan_cfg()

        faltantes = validar_herramientas_scan(cfg)
        if faltantes:
            raise RuntimeError("Herramientas no encontradas: " + " | ".join(faltantes))

        if run.target_type == "url":
            logs = ejecutar_scan_web(run, cfg, run_dir, crear_vulns, crear_planes)
        else:
            logs = ejecutar_scan_ip(run, cfg, run_dir, crear_vulns, crear_planes)

        run = VulnerabilityScanRun.query.get(run.id)

        if run.estado == "detenido" or run.cancel_requested:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(logs or []))
            run.archivo_log = log_path
            run.salida_consola = ("\n\n".join(logs or []))[:20000]
            run.current_stage = "Escaneo detenido"
            run.current_tool = None
            run.active_pid = None
            run.active_command = None
            db.session.commit()
            return {"ok": False, "stopped": True}

        scan_set_progress(run.id, pct=95, stage="Consolidando resultados", tool="sync")

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(logs or []))

        run = VulnerabilityScanRun.query.get(run.id)
        run.archivo_log = log_path
        run.salida_consola = ("\n\n".join(logs or []))[:20000]

        resumir_hallazgos_run(run)
        run.estado = "finalizado"
        run.progress_pct = 100
        run.current_stage = "Escaneo finalizado"
        run.current_tool = None
        run.active_pid = None
        run.active_command = None
        run.fecha_fin = datetime.utcnow()
        db.session.commit()

        pdf_path = build_vulnerability_scan_pdf(run.id)
        run.archivo_reporte_pdf = pdf_path
        db.session.commit()

        return {
            "ok": True,
            "findings": run.total_hallazgos or 0,
            "vulns": run.created_vulns or 0,
            "planes": run.created_plans or 0
        }

    except Exception as e:
        tb = traceback.format_exc()

        run = VulnerabilityScanRun.query.get(run_id)
        if run and run.estado == "detenido":
            return {"ok": False, "stopped": True}

        if run:
            run.estado = "error"
            run.error_detalle = f"{str(e)}\n\n{tb}"
            run.fecha_fin = datetime.utcnow()
            run.current_stage = "Error en la ejecución"
            run.current_tool = None
            run.active_pid = None
            run.active_command = None
            run.salida_consola = ((run.salida_consola or "") + "\n\n[TRACEBACK]\n" + tb)[-20000:]
            run.archivo_log = log_path if os.path.exists(os.path.dirname(log_path)) else None
            db.session.commit()
        return {"ok": False, "error": str(e)}

def _background_scan_worker(app_obj, run_id, crear_vulns, crear_planes):
    with app_obj.app_context():
        try:
            run = VulnerabilityScanRun.query.get(run_id)
            if run:
                run.current_stage = "Worker iniciado"
                run.current_tool = "worker"
                db.session.commit()

            ejecutar_full_scan(run_id, crear_vulns=crear_vulns, crear_planes=crear_planes)

        except Exception as e:
            tb = traceback.format_exc()
            run = VulnerabilityScanRun.query.get(run_id)
            if run:
                run.estado = "error"
                run.error_detalle = f"{str(e)}\n\n{tb}"
                run.current_stage = "Error arrancando worker"
                run.current_tool = None
                run.fecha_fin = datetime.utcnow()
                db.session.commit()

def lanzar_scan_background(run_id, crear_vulns=True, crear_planes=True):
    t = threading.Thread(
        target=_background_scan_worker,
        args=(app, run_id, crear_vulns, crear_planes),
        daemon=True
    )
    t.start()
    return t

def vuln_scan_shell(title, body_html):
    threat_model_titles = {
        "Modelamiento de Amenazas",
        "Matriz MITRE ATT&CK",
        "No mapeados MITRE",
        "Clasificación complementaria No Mapeados",
    }
    is_threat_model = title in threat_model_titles

    shell_html = """
    <div class="menu-wrap{% if is_threat_model %} threat-shell{% endif %}">
      <div class="plan-hero">
        <h2 class="plan-title">{{ title }}</h2>
      </div>

      {% if not is_threat_model %}
        <div class="volver-center">
          <a href="{{ url_for('vulnerabilidades_matriz') }}"
             class="btn btn-light rounded-pill px-4 fw-semibold"
             onclick="showLoader()">
            ⬅ Volver a la Matriz
          </a>
        </div>
      {% endif %}

      {{ body_html|safe }}
    </div>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .menu-wrap{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
        overflow:hidden;
        min-width:0;
      }

      /* Modelamiento de Amenazas ocupa todo el ancho útil del contenido.
         El scroll horizontal queda limitado a cada tabla o matriz y no a la página completa. */
      .menu-wrap.threat-shell{
        width:calc(100% - 24px);
        max-width:none;
        margin:14px 12px 24px 12px;
        overflow:visible;
        min-width:0;
      }

      .menu-wrap.threat-shell,
      .menu-wrap.threat-shell *,
      .menu-wrap.threat-shell *::before,
      .menu-wrap.threat-shell *::after{
        box-sizing:border-box;
      }

      .menu-wrap.threat-shell > *,
      .menu-wrap.threat-shell .glass-card,
      .menu-wrap.threat-shell .soft-table-wrap,
      .menu-wrap.threat-shell .table-responsive,
      .menu-wrap.threat-shell .mitre-shell,
      .menu-wrap.threat-shell .mitre-board-wrap{
        width:100%;
        max-width:100%;
        min-width:0;
      }

      .menu-wrap.threat-shell .row{
        margin-left:0;
        margin-right:0;
        width:100%;
      }

      .menu-wrap.threat-shell .row > [class*="col-"]{
        min-width:0;
      }

      .menu-wrap.threat-shell .table-responsive,
      .menu-wrap.threat-shell .soft-table-wrap,
      .menu-wrap.threat-shell .mitre-board-wrap{
        overflow-x:auto;
        overflow-y:auto;
        -webkit-overflow-scrolling:touch;
      }

      .menu-wrap.threat-shell img,
      .menu-wrap.threat-shell svg,
      .menu-wrap.threat-shell canvas{
        max-width:100%;
        height:auto;
      }

      .plan-hero{
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

      .plan-hero::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .plan-hero::after{
        content:"🛰️";
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
        position:relative;
        z-index:1;
        order:-1;
      }

      .plan-title{
        position:relative;
        z-index:1;
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        margin:0 !important;
        text-align:left;
        padding:0;
        transform:none;
        overflow-wrap:break-word;
      }

      .plan-title::before{
        content:"SGSI · Gestión de Vulnerabilidades";
        display:block;
        width:fit-content;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .volver-center{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .toolbar-actions{
        display:flex;
        gap:10px;
        flex-wrap:wrap;
        justify-content:center;
        align-items:center;
      }

      .volver-center .btn,
      .toolbar-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
        max-width:100%;
      }

      .volver-center .btn-secondary,
      .volver-center .btn-outline-secondary{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .volver-center .btn-secondary:hover,
      .volver-center .btn-outline-secondary:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .glass-card,
      .soft-table-wrap,
      .metric-box{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .glass-card{
        padding:0;
      }

      .section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
        overflow-wrap:break-word;
      }

      .soft-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        background:#ffffff !important;
      }

      .soft-table{
        min-width:1100px;
        table-layout:fixed;
        margin-bottom:0;
      }

      .soft-table thead th{
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

      .soft-table th,
      .soft-table td{
        vertical-align:top;
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .soft-table td{
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .soft-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .soft-table tbody tr:hover{
        background:#eef6ff;
      }

      .badge-soft{
        display:inline-flex;
        align-items:center;
        justify-content:center;
        padding:.35rem .65rem;
        border-radius:999px;
        font-size:.70rem;
        font-weight:900;
        text-align:center;
        max-width:100%;
        white-space:normal;
      }

      .sev-critica{ background:#7f1d1d; color:#ffffff; }
      .sev-alta{ background:#b91c1c; color:#ffffff; }
      .sev-media{ background:#d97706; color:#ffffff; }
      .sev-baja{ background:#15803d; color:#ffffff; }

      .estado-pendiente{ background:#4b5563; color:#ffffff; }
      .estado-ejecutando{ background:#1d4ed8; color:#ffffff; }
      .estado-finalizado{ background:#15803d; color:#ffffff; }
      .estado-error{ background:#b91c1c; color:#ffffff; }
      .estado-detenido{ background:#5521a8; color:#ffffff; }

      .metric-box{
        padding:14px 16px;
        min-height:90px;
      }

      .metric-label{
        font-size:.78rem;
        color:#475569;
        font-weight:900;
        overflow-wrap:break-word;
      }

      .metric-value{
        font-size:1.28rem;
        color:#0b4a8f;
        font-weight:950;
        margin-top:4px;
        overflow-wrap:break-word;
      }

      .form-label{
        font-weight:900;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .form-control,
      .form-select{
        border-radius:10px !important;
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

      .progress{
        height:20px;
        border-radius:999px;
        background:#dbe6f4;
        overflow:hidden;
      }

      .progress-bar{
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:.68rem;
        font-weight:900;
      }

      .soft-table-wrap::-webkit-scrollbar{
        height:11px;
        width:11px;
      }

      .soft-table-wrap::-webkit-scrollbar-track{
        background:#dbe4f0;
        border-radius:12px;
      }

      .soft-table-wrap::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,#5aa3ea 0%,#3f86d6 100%);
        border-radius:12px;
        border:2px solid #dbe4f0;
      }

      .soft-table-wrap{
        scrollbar-width:thin;
        scrollbar-color:#3f86d6 #dbe4f0;
      }

      h3{
        color:#ffffff;
        margin:0;
      }

      @media (max-width:992px){
        .menu-wrap{
          width:98%;
          margin:8px auto 22px auto;
        }

        .menu-wrap.threat-shell{
          width:calc(100% - 16px);
          margin:8px 8px 22px 8px;
        }

        .plan-hero{
          min-height:88px;
        }

        .plan-title{
          font-size:1.20rem;
        }
      }

      @media (max-width:768px){
        .menu-wrap.threat-shell{
          width:100%;
          margin:6px 0 18px 0;
        }

        .menu-wrap.threat-shell .glass-card{
          border-radius:14px;
        }

        .menu-wrap.threat-shell .table-responsive,
        .menu-wrap.threat-shell .soft-table-wrap{
          border-radius:12px;
        }

        .plan-hero{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .plan-hero::after{
          margin:0;
        }

        .plan-title{
          text-align:center;
        }

        .plan-title::before{
          margin-left:auto;
          margin-right:auto;
        }

        .volver-center .btn,
        .toolbar-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        shell_html,
        title=title,
        body_html=Markup(body_html),
        is_threat_model=is_threat_model,
    )
    return render_template_string(BASE, content=Markup(inner))

def badge_severidad_html(valor):
    v = (valor or "").strip().lower()
    mapa = {
        "crítica": "sev-critica",
        "critica": "sev-critica",
        "alta": "sev-alta",
        "media": "sev-media",
        "baja": "sev-baja",
    }
    cls = mapa.get(v, "sev-media")
    return Markup(f'<span class="badge-soft {cls}">{escape(valor or "—")}</span>')


def badge_estado_scan_html(valor):
    v = (valor or "").strip().lower()
    mapa = {
        "pendiente": "estado-pendiente",
        "ejecutando": "estado-ejecutando",
        "finalizado": "estado-finalizado",
        "error": "estado-error",
        "detenido": "estado-detenido",
    }
    cls = mapa.get(v, "estado-pendiente")
    return Markup(f'<span class="badge-soft {cls}">{escape(valor or "—")}</span>')

# ==========================
# Reporte del escaneo
# ==========================

def build_vulnerability_scan_pdf(run_id: int):
    run = VulnerabilityScanRun.query.get_or_404(run_id)
    findings = VulnerabilityScanFinding.query.filter_by(run_id=run.id).order_by(VulnerabilityScanFinding.id.asc()).all()

    pdf_path = os.path.join(
        app.config["UPLOAD_VULNERABILIDADES_DIR"],
        f"reporte_scan_{run.id}.pdf"
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    h2 = styles["Heading2"]
    normal = styles["Normal"]

    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=32, leftMargin=32, topMargin=32, bottomMargin=28)
    story = []

    story.append(Paragraph("Reporte de Análisis de Vulnerabilidades", title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>ID Corrida:</b> {run.id}", normal))
    story.append(Paragraph(f"<b>Objetivo:</b> {html_escape(run.target)}", normal))
    story.append(Paragraph(f"<b>Tipo Objetivo:</b> {html_escape(run.target_type)}", normal))
    story.append(Paragraph(f"<b>Modo Escáner:</b> {html_escape(run.scanner_mode)}", normal))
    story.append(Paragraph(f"<b>Estado:</b> {html_escape(run.estado)}", normal))
    story.append(Paragraph(f"<b>Fecha Inicio:</b> {run.fecha_inicio or '—'}", normal))
    story.append(Paragraph(f"<b>Fecha Fin:</b> {run.fecha_fin or '—'}", normal))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Resumen Ejecutivo", h2))
    resumen_data = [
        ["Severidad", "Cantidad"],
        ["Crítica", str(run.criticas or 0)],
        ["Alta", str(run.altas or 0)],
        ["Media", str(run.medias or 0)],
        ["Baja", str(run.bajas or 0)],
        ["Total", str(run.total_hallazgos or 0)],
    ]
    t = Table(resumen_data, colWidths=[9 * cm, 5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Metodología", h2))
    story.append(Paragraph(
        "Se ejecutó un análisis técnico automatizado utilizando herramientas del entorno Kali Linux. "
        "Según el tipo de objetivo se utilizaron Nmap, Nikto, testssl y Nuclei para identificar "
        "servicios expuestos, puertos abiertos, debilidades de configuración web, hallazgos basados "
        "en templates y vulnerabilidades o debilidades asociadas a TLS/SSL.",
        normal
    ))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Hallazgos Detallados", h2))

    if not findings:
        story.append(Paragraph("No se encontraron hallazgos parseados en esta corrida.", normal))
    else:
        for idx, f in enumerate(findings, start=1):
            story.append(Paragraph(f"{idx}. {html_escape(f.titulo)}", styles["Heading3"]))
            story.append(Paragraph(f"<b>Fuente:</b> {html_escape(f.fuente)}", normal))
            story.append(Paragraph(f"<b>Severidad:</b> {html_escape(f.severidad)}", normal))
            story.append(Paragraph(f"<b>CVE:</b> {html_escape(f.cve or '—')}", normal))
            story.append(Paragraph(f"<b>CVSS:</b> {html_escape(f.cvss or '—')}", normal))
            story.append(Paragraph(f"<b>Puerto:</b> {html_escape(f.puerto or '—')}", normal))
            story.append(Paragraph(f"<b>Servicio:</b> {html_escape(f.servicio or '—')}", normal))
            story.append(Paragraph(f"<b>Descripción:</b> {html_escape(f.descripcion or '—')}", normal))
            story.append(Paragraph(f"<b>Evidencia:</b> {html_escape(f.evidencia or '—')}", normal))
            story.append(Paragraph(f"<b>Recomendación Base:</b> {html_escape(f.recomendacion_base or '—')}", normal))
            story.append(Spacer(1, 10))

    story.append(PageBreak())
    story.append(Paragraph("Descargo", h2))
    story.append(Paragraph(
        "Este reporte corresponde a un análisis automatizado sobre objetivos autorizados. "
        "Los resultados deben ser validados por el equipo técnico y complementados con revisión contextual, "
        "tratamiento de riesgos y seguimiento de remediación dentro del SGSI.",
        normal
    ))

    doc.build(story)
    return pdf_path


# ==========================
# Entrada directa al módulo — Registro de Vulnerabilidades
# ==========================
@app.route('/vulnerabilidades_menu')
@login_required
def vulnerabilidades_menu():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        flash("No tiene permiso para acceder al módulo de registro de vulnerabilidades.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('vulnerabilidades_matriz'))

# ==========================
# Agregar Vulnerabilidades
# ==========================

@app.route('/vulnerabilidad/new', methods=['GET', 'POST'])
@login_required
def vulnerabilidad_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('vulnerabilidades_menu'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        flash("No tiene permiso para agregar requisitos legales.", "danger")
        return redirect(url_for('vulnerabilidades_menu'))

    if request.method == 'POST':
        codigo = (request.form.get('codigo') or '').strip()
        activo = (request.form.get('activo') or '').strip()
        descripcion_vulnerabilidad = (request.form.get('descripcion_vulnerabilidad') or '').strip()
        cve = (request.form.get('cve') or '').strip()
        cvss = (request.form.get('cvss') or '').strip()
        clasificacion = (request.form.get('clasificacion') or '').strip()
        responsable = (request.form.get('responsable') or '').strip()
        riesgo_residual = (request.form.get('riesgo_residual') or '').strip()
        estado = request.form.get('estado') or ''

        fecha_str = (request.form.get('fecha_identificacion') or '').strip()
        fecha_identificacion = None
        if fecha_str:
            try:
                fecha_identificacion = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de identificación inválida.", "danger")
                return redirect(url_for('vulnerabilidad_new'))
        
        fecha_cierre_str = (request.form.get('fecha_cierre') or '').strip()
        fecha_cierre = None
        if fecha_cierre_str:
            try:
                fecha_cierre = datetime.strptime(fecha_cierre_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de cierre inválida.", "danger")
                return redirect(url_for('vulnerabilidad_new'))
            

        # Validaciones mínimas
        if not all([codigo, activo, descripcion_vulnerabilidad, estado, responsable]):
            flash("Campos obligatorios: ID, Activo, Descripción, Estado y Responsable.", "danger")
            return redirect(url_for('vulnerabilidad_new'))

        it = VulnerabilidadRegistro(
            codigo=codigo,
            activo=activo,
            descripcion_vulnerabilidad=descripcion_vulnerabilidad,
            cve=cve,
            cvss=cvss,
            clasificacion=clasificacion,          # ⬅⬅ importante
            fecha_identificacion=fecha_identificacion,
            fecha_cierre=fecha_cierre, 
            estado=estado,
            responsable=responsable,
            riesgo_residual=riesgo_residual
        )
        db.session.add(it)

        # Evidencias (varios archivos, como en otros módulos)
        files = request.files.getlist('evidencias')
        for f in files:
            if not f or not f.filename:
                continue
            if not is_allowed_pdf(f.filename):   # o tu validador de tipos (puedes permitir .pdf,.jpg,etc.)
                flash(f"Archivo no permitido: {f.filename}", "danger")
                continue

            store_name = unique_store_name(f.filename)
            path = os.path.join(app.config['UPLOAD_VULNERABILIDADES_DIR'], store_name)
            f.save(path)

            ev = VulnerabilidadEvidencia(
                vulnerabilidad=it,
                filename=store_name,
                original_name=secure_filename(f.filename),
                mime='application/pdf',
                size=os.path.getsize(path)
            )
            db.session.add(ev)

        # Sincronización automática con Modelamiento de Amenazas / MITRE ATT&CK
        db.session.flush()
        sincronizar_vulnerabilidad_con_modelamiento(it)

        db.session.commit()
        flash("Vulnerabilidad registrada y sincronizada con Modelamiento de Amenazas.", "success")
        return redirect(url_for('vulnerabilidades_matriz'))

    # GET
    html = """
    <div class="vulnadd-shell">

      <!-- CABECERA -->
      <div class="vulnadd-header-card">
        <div class="vulnadd-header-overlay">
          <div class="vulnadd-header-text">
            <h3 class="vulnadd-title m-0">Agregar Vulnerabilidad</h3>
            <div class="vulnadd-subtitle">
              Registro y gestión de vulnerabilidades identificadas, incluyendo activo afectado, clasificación, responsable, riesgo residual y evidencias de cierre
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="vulnadd-header-actions">
        <a href="{{ url_for('vulnerabilidades_matriz') }}"
           class="btn rounded-pill px-5 fw-bold vulnadd-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <!-- TARJETA -->
      <div class="vulnadd-card">
        <div class="vulnadd-card-body">
          <form method="post" enctype="multipart/form-data">
            <div class="row g-3">

              <div class="col-12">
                <div class="vulnadd-section-title">Información de la vulnerabilidad</div>
              </div>

              <div class="col-md-3">
                <label class="form-label">ID (alfanumérico)</label>
                <input name="codigo" class="form-control" required>
              </div>

              <div class="col-md-9">
                <label class="form-label">Activo</label>
                <input name="activo" class="form-control" required>
              </div>

              <div class="col-md-12">
                <label class="form-label">Descripción de la Vulnerabilidad</label>
                <textarea name="descripcion_vulnerabilidad" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">CVE</label>
                <input name="cve" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">CVSS</label>
                <input name="cvss" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Clasificación</label>
                <select name="clasificacion" class="form-select">
                  <option value="">-- Seleccione --</option>
                  {% for op in clasif_choices %}
                    <option value="{{ op }}">{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de Identificación</label>
                <input type="date" name="fecha_identificacion" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de Cierre</label>
                <input type="date" name="fecha_cierre" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Estado</label>
                <select name="estado" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  <option value="Abierto">Abierto</option>
                  <option value="Cerrado">Cerrado</option>
                </select>
              </div>

              <div class="col-md-6">
                <label class="form-label">Responsable</label>
                <input name="responsable" class="form-control" required>
              </div>

              <div class="col-md-6">
                <label class="form-label">Riesgo Residual</label>
                <textarea name="riesgo_residual" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Evidencia de Cierre (múltiples archivos)</label>
                <input
                  type="file"
                  id="evidencias"
                  name="evidencias"
                  multiple
                  class="form-control"
                  onchange="acumularEvidencias(this)"
                >
                <small class="text-muted">
                  Puedes seleccionar varios a la vez o ir agregando en varias rondas.
                </small>
                <div id="lista_evidencias_nuevas" class="mt-2"></div>
              </div>

            </div>

            <div class="vulnadd-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>
              <a href="{{ url_for('vulnerabilidades_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold vulnadd-cancel-btn">
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

      .vulnadd-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HEADER SGSI UNIFICADO (IGUAL A TODOS)
      ========================= */
      .vulnadd-header-card{
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

      .vulnadd-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .vulnadd-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .vulnadd-header-overlay::before{
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

      .vulnadd-header-text{
        max-width:1100px;
        width:100%;
      }

      .vulnadd-header-text::before{
        content:"SGSI · Gestión de Vulnerabilidades";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .vulnadd-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .vulnadd-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES SUPERIORES
      ========================= */
      .vulnadd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .vulnadd-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .vulnadd-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .vulnadd-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD PRINCIPAL
      ========================= */
      .vulnadd-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .vulnadd-card-body{
        padding:18px;
      }

      /* =========================
         FORMULARIOS
      ========================= */
      .vulnadd-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .vulnadd-card .form-control,
      .vulnadd-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .vulnadd-card textarea.form-control{
        min-height:70px;
      }

      .vulnadd-card .form-control:focus,
      .vulnadd-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      /* =========================
         TITULOS
      ========================= */
      .vulnadd-section-title{
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
         BOTONES INFERIORES
      ========================= */
      .vulnadd-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
      }

      .vulnadd-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .vulnadd-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .vulnadd-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         RESPONSIVE
      ========================= */
      @media (max-width:992px){
        .vulnadd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .vulnadd-header-card{
          min-height:88px;
        }

        .vulnadd-title{
          font-size:1.20rem;
        }

        .vulnadd-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .vulnadd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .vulnadd-header-overlay::before{
          margin:0;
        }

        .vulnadd-header-actions .btn,
        .vulnadd-bottom-actions .btn{
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
    inner = render_template_string(html, clasif_choices=VULN_CLASIFICACIONES)
    return render_template_string(BASE, content=Markup(inner))

# ==========================
# Matriz Vulnerabilidades
# ==========================

