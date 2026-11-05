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
                                class="btn btn-sm btn-outline-danger rounded-pill"
                                title="Eliminar proponente">
                          🗑️
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

class ProveedorEvalConfig(db.Model):
    __tablename__ = "proveedor_eval_config"

    id = db.Column(db.Integer, primary_key=True)

    min_certificaciones_aprobado = db.Column(db.Integer, default=1)
    pct_aprob_min = db.Column(db.Integer, default=81)
    pct_revision_min = db.Column(db.Integer, default=61)

    crit_muy_baja_max = db.Column(db.Integer, default=25)
    crit_baja_max = db.Column(db.Integer, default=50)
    crit_media_max = db.Column(db.Integer, default=75)

    # NUEVOS PESOS CONFIGURABLES
    peso_transversal = db.Column(db.Integer, default=10)
    peso_esencial = db.Column(db.Integer, default=15)
    peso_plan_continuidad = db.Column(db.Integer, default=10)
    peso_plan_recuperacion = db.Column(db.Integer, default=10)
    peso_alternativas = db.Column(db.Integer, default=10)
    peso_impacto_falla = db.Column(db.Integer, default=10)
    peso_plan_migracion = db.Column(db.Integer, default=10)
    peso_info_sensible = db.Column(db.Integer, default=10)
    peso_datos_personales = db.Column(db.Integer, default=5)
    peso_nube = db.Column(db.Integer, default=5)
    peso_sla = db.Column(db.Integer, default=5)

    @staticmethod
    def get():
        obj = ProveedorEvalConfig.query.first()
        if not obj:
            obj = ProveedorEvalConfig()
            db.session.add(obj)
            db.session.commit()
        return obj

# =========================
# ENTRADA DIRECTA — Registro de Proveedores
# =========================
@app.route('/proveedores_menu')
@login_required
def proveedores_menu():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Registro de Proveedores"):
        flash("No tiene permiso para acceder al módulo de registro de proveedores.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('proveedores_matriz'))


# =========================
# HELPERS
# =========================
def _proveedor_paises():
    try:
        paises = [c.name for c in pycountry.countries]
        paises.sort()
        return paises
    except Exception:
        return ["Colombia", "Argentina", "Brasil", "Chile", "México", "Perú", "España", "Estados Unidos"]

def _proveedor_fill_area_data(area_id):
    responsable_area_nombre = ''
    responsable_area_cargo = ''

    if area_id:
        a = AreaEmpresa.query.get(area_id)
        if a:
            responsable_area_nombre = (getattr(a, 'responsable_nombre', '') or '')
            responsable_area_cargo = (getattr(a, 'responsable_cargo', '') or '')

    return responsable_area_nombre, responsable_area_cargo

def _proveedor_apply_scores(obj, form, cfg):
    obj.es_transversal = form.get('es_transversal') or 'No'
    obj.es_esencial = form.get('es_esencial') or 'No'
    obj.tiene_plan_cont = form.get('tiene_plan_cont') or 'No'
    obj.tiene_plan_rec = form.get('tiene_plan_rec') or 'No'
    obj.existen_alternativas = form.get('existen_alternativas') or 'No'
    obj.impacto_falla = form.get('impacto_falla') or 'Bajo'
    obj.existe_plan_migracion = form.get('existe_plan_migracion') or 'No'
    obj.procesa_info_sensible = form.get('procesa_info_sensible') or 'No'
    obj.procesa_datos_personales = form.get('procesa_datos_personales') or 'No'
    obj.procesa_info_nube = form.get('procesa_info_nube') or 'No'
    obj.incluye_sla = form.get('incluye_sla') or 'No'

    obj.valor_alcance = int(cfg.peso_transversal or 0) if obj.es_transversal == 'Sí' else 0
    obj.valor_esencial = int(cfg.peso_esencial or 0) if obj.es_esencial == 'Sí' else 0
    obj.valor_plan_cont = 0 if obj.tiene_plan_cont == 'Sí' else int(cfg.peso_plan_continuidad or 0)
    obj.valor_plan_rec = 0 if obj.tiene_plan_rec == 'Sí' else int(cfg.peso_plan_recuperacion or 0)
    obj.valor_alternativas = 0 if obj.existen_alternativas == 'Sí' else int(cfg.peso_alternativas or 0)

    if obj.impacto_falla == 'Alto':
        obj.valor_impacto_falla = int(cfg.peso_impacto_falla or 0)
    elif obj.impacto_falla == 'Medio':
        obj.valor_impacto_falla = round(int(cfg.peso_impacto_falla or 0) * 0.5)
    else:
        obj.valor_impacto_falla = 0

    obj.valor_plan_migracion = 0 if obj.existe_plan_migracion == 'Sí' else int(cfg.peso_plan_migracion or 0)
    obj.valor_info_sensible = int(cfg.peso_info_sensible or 0) if obj.procesa_info_sensible == 'Sí' else 0
    obj.valor_datos_personales = int(cfg.peso_datos_personales or 0) if obj.procesa_datos_personales == 'Sí' else 0
    obj.valor_nube = int(cfg.peso_nube or 0) if obj.procesa_info_nube == 'Sí' else 0
    obj.valor_sla = 0 if obj.incluye_sla == 'Sí' else int(cfg.peso_sla or 0)

    obj.tiene_certificacion = form.get('tiene_certificacion') or 'No'
    obj.puntos_formulario = form.get('puntos_formulario', type=int) or 0
    obj.num_certificaciones = form.get('num_certificaciones', type=int) or 0
    obj.nombre_certificaciones = (form.get('nombre_certificaciones') or '').strip()

    obj.calcular_criticidad()
    obj.calcular_certificados()

    try:
        total_criticidad = int(getattr(obj, 'criticidad_pct', 0) or 0)
    except Exception:
        total_criticidad = 0

    if total_criticidad <= int(cfg.crit_baja_max or 50):
        obj.calificacion_total = 100
        obj.resultado_evaluacion = 'Aprobado Por Seguridad'
        obj.resultado_color = 'badge-aprobado'
        obj.requiere_formulario = 'No'
        obj.puntos_certificacion = 100
        obj.puntos_formulario = 0

def _proveedor_save_files(obj, files):
    for f in files:
        if not f or not f.filename:
            continue

        if not is_allowed_pdf(f.filename):
            flash(f"Archivo no permitido (solo PDF): {f.filename}", "danger")
            continue

        store_name = unique_store_name(f.filename)
        path = os.path.join(app.config['UPLOAD_PROVEEDORES_DIR'], store_name)
        f.save(path)

        ev = ProveedorEvidencia(
            proveedor=obj,
            filename=store_name,
            original_name=secure_filename(f.filename),
            mime='application/pdf',
            size=os.path.getsize(path)
        )
        db.session.add(ev)

def _render_proveedor_form(item=None, areas=None, paises=None, cfg=None, is_edit=False):
    if item is None:
        class Dummy:
            pass
        item = Dummy()
        item.id = None
        item.fecha_eval_seguridad = ''
        item.nombre_proveedor = ''
        item.estatus_proveedor = ''
        item.area_id = None
        item.responsable_area_nombre = ''
        item.responsable_area_cargo = ''
        item.nombre_cargo_evaluador = ''
        item.pais_origen = ''
        item.pais_servicio = ''
        item.desc_producto_servicio = ''
        item.estado_avance = 'Operando'
        item.estado_evaluacion = 'Proceso'
        item.es_transversal = 'No'
        item.es_esencial = 'No'
        item.tiene_plan_cont = 'No'
        item.tiene_plan_rec = 'No'
        item.existen_alternativas = 'No'
        item.impacto_falla = 'Bajo'
        item.existe_plan_migracion = 'No'
        item.procesa_info_sensible = 'No'
        item.procesa_datos_personales = 'No'
        item.procesa_info_nube = 'No'
        item.incluye_sla = 'No'
        item.criticidad_pct = 0
        item.criticidad_texto = 'Criticidad muy baja'
        item.tiene_certificacion = 'No'
        item.num_certificaciones = 0
        item.nombre_certificaciones = ''
        item.puntos_formulario = 0
        item.calificacion_total = 0
        item.resultado_evaluacion = 'No Aprobado por Seguridad'
        item.observaciones = ''
        item.evidencias = []

    html = """
    <div class="provform-shell">

      <div class="provform-header-card">
        <div class="provform-header-overlay">
          <div class="provform-header-text">
            <h3 class="provform-title m-0">
              {% if is_edit %}Editar Proveedor{% else %}Agregar — Proveedor{% endif %}
            </h3>
            <div class="provform-subtitle">
              Registro y evaluación de proveedores, incluyendo criticidad, certificaciones, continuidad, recuperación, SLA, nube, datos personales, evidencias y resultado de aprobación por seguridad
            </div>
          </div>
        </div>
      </div>

      <div class="provform-header-actions">
        <a href="{{ url_for('proveedores_matriz') }}"
           class="btn rounded-pill px-5 fw-bold provform-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz de Proveedores
        </a>
      </div>

      <div class="provform-card">
        <div class="provform-card-body">
          <form method="post" enctype="multipart/form-data" oninput="recalc()">
            <div class="row g-3">

              <div class="col-12">
                <div class="provform-section-box">
                  <div class="provform-section-title">Información general del proveedor</div>
                  <div class="provform-section-subtitle">
                    Datos básicos del proveedor, área responsable, evaluador, ubicación, descripción del servicio y estado del registro.
                  </div>
                </div>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de registro por el área de seguridad</label>
                <input type="date" name="fecha_eval_seguridad" class="form-control" value="{{ item.fecha_eval_seguridad or '' }}" required>
              </div>

              <div class="col-md-3">
                <label class="form-label">Nombre del Proveedor</label>
                <input type="text" name="nombre_proveedor" class="form-control" value="{{ item.nombre_proveedor or '' }}" required>
              </div>

              <div class="col-md-3">
                <label class="form-label">Estatus del Proveedor</label>
                <input type="text" name="estatus_proveedor" class="form-control" value="{{ item.estatus_proveedor or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Área responsable del proveedor</label>
                <select name="area_id" id="provArea" class="form-select" required onchange="fillResp()">
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}" {% if item.area_id == a.id %}selected{% endif %}>{{ a.area }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre del responsable del área</label>
                <input type="text" name="responsable_area_nombre" id="provResp" class="form-control" value="{{ item.responsable_area_nombre or '' }}" readonly>
              </div>

              <div class="col-md-4">
                <label class="form-label">Cargo del responsable del área</label>
                <input type="text" name="responsable_area_cargo" id="provCargo" class="form-control" value="{{ item.responsable_area_cargo or '' }}" readonly>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre y cargo del evaluador</label>
                <input type="text" name="nombre_cargo_evaluador" class="form-control" value="{{ item.nombre_cargo_evaluador or '' }}">
              </div>

              <div class="col-md-2">
                <label class="form-label">País de origen</label>
                <select name="pais_origen" class="form-select">
                  <option value="">-- Seleccione --</option>
                  {% for p in paises %}
                    <option value="{{ p }}" {% if item.pais_origen == p %}selected{% endif %}>{{ p }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label">País de servicio</label>
                <select name="pais_servicio" class="form-select">
                  <option value="">-- Seleccione --</option>
                  {% for p in paises %}
                    <option value="{{ p }}" {% if item.pais_servicio == p %}selected{% endif %}>{{ p }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-12">
                <label class="form-label">Descripción del producto/servicio</label>
                <textarea name="desc_producto_servicio" class="form-control" rows="2">{{ item.desc_producto_servicio or '' }}</textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Estado / avance</label>
                <select name="estado_avance" class="form-select">
                  {% for opt in ['Operando','Negociación','Instalaciones'] %}
                    <option {% if item.estado_avance == opt %}selected{% endif %}>{{ opt }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Estado del registro</label>
                <select name="estado_evaluacion" class="form-select">
                  {% for opt in ['Finalizado','Proceso'] %}
                    <option {% if item.estado_evaluacion == opt %}selected{% endif %}>{{ opt }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-12">
                <div class="provform-section-box">
                  <div class="provform-section-title">Calificación del proveedor</div>
                  <div class="provform-section-subtitle">
                    Criterios de criticidad y evaluación del proveedor: transversalidad, continuidad, recuperación, alternativas, impacto, migración, información sensible, datos personales, nube y SLA.
                  </div>
                </div>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Es transversal a toda la Organización?</label>
                <select name="es_transversal" id="es_transversal" class="form-select">
                  <option {% if item.es_transversal == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.es_transversal == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor alcance: <b id="val_alc">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Es esencial para la continuidad?</label>
                <select name="es_esencial" id="es_esencial" class="form-select">
                  <option {% if item.es_esencial == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.es_esencial == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor esencial: <b id="val_esen">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Tiene plan de continuidad?</label>
                <select name="tiene_plan_cont" id="tiene_plan_cont" class="form-select">
                  <option {% if item.tiene_plan_cont == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.tiene_plan_cont == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor plan cont.: <b id="val_plan">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Tiene plan de recuperación?</label>
                <select name="tiene_plan_rec" id="tiene_plan_rec" class="form-select">
                  <option {% if item.tiene_plan_rec == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.tiene_plan_rec == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor plan rec.: <b id="val_plan_rec">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Existen alternativas en el mercado?</label>
                <select name="existen_alternativas" id="existen_alternativas" class="form-select">
                  <option {% if item.existen_alternativas == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.existen_alternativas == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor alternativas: <b id="val_alt">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">Impacto en caso de falla</label>
                <select name="impacto_falla" id="impacto_falla" class="form-select">
                  <option {% if item.impacto_falla == 'Bajo' %}selected{% endif %}>Bajo</option>
                  <option {% if item.impacto_falla == 'Medio' %}selected{% endif %}>Medio</option>
                  <option {% if item.impacto_falla == 'Alto' %}selected{% endif %}>Alto</option>
                </select>
                <small>Valor impacto: <b id="val_impacto">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Existe plan de migración?</label>
                <select name="existe_plan_migracion" id="existe_plan_migracion" class="form-select">
                  <option {% if item.existe_plan_migracion == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.existe_plan_migracion == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor migración: <b id="val_mig">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Procesa/almacena info. sensible?</label>
                <select name="procesa_info_sensible" id="procesa_info_sensible" class="form-select">
                  <option {% if item.procesa_info_sensible == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.procesa_info_sensible == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor info sensible: <b id="val_inf">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Procesa/almacena datos personales?</label>
                <select name="procesa_datos_personales" id="procesa_datos_personales" class="form-select">
                  <option {% if item.procesa_datos_personales == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.procesa_datos_personales == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor datos personales: <b id="val_datos">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Procesa/almacena información en la nube?</label>
                <select name="procesa_info_nube" id="procesa_info_nube" class="form-select">
                  <option {% if item.procesa_info_nube == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.procesa_info_nube == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor nube: <b id="val_nube">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Incluye SLA definidos?</label>
                <select name="incluye_sla" id="incluye_sla" class="form-select">
                  <option {% if item.incluye_sla == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.incluye_sla == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor SLA: <b id="val_sla">0</b>%</small>
              </div>

              <div class="col-md-6">
                <label class="form-label">Criticidad % (auto)</label>
                <input type="text" class="form-control provform-readonly" id="criticidad_pct" value="{{ item.criticidad_pct or 0 }}" readonly>
                <small id="criticidad_texto" class="badge badge-verde-claro mt-1">{{ item.criticidad_texto or 'Criticidad muy baja' }}</small>
              </div>

              <div class="col-12">
                <div class="provform-section-box">
                  <div class="provform-section-title">Registro del proveedor</div>
                  <div class="provform-section-subtitle">
                    Registro de certificaciones, cantidad, nombres, puntos del formulario, cálculo automático de la calificación total y resultado de evaluación.
                  </div>
                </div>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Tiene certificación (ISO 27001, SOC2, etc.)?</label>
                <select name="tiene_certificacion" id="tiene_certificacion" class="form-select">
                  <option {% if item.tiene_certificacion == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.tiene_certificacion == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Requiere formulario: <b id="req_form">Sí</b></small><br>
                <small>Puntos por certificación: <b id="pt_cert">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">Número de certificaciones</label>
                <input type="number" min="0" name="num_certificaciones" id="num_certificaciones" class="form-control" value="{{ item.num_certificaciones or 0 }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Nombre de las certificaciones</label>
                <textarea name="nombre_certificaciones" id="nombre_certificaciones" class="form-control" rows="2">{{ item.nombre_certificaciones or '' }}</textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Puntos obtenidos en el formulario</label>
                <input type="number" max="100" min="0" name="puntos_formulario" id="puntos_formulario" class="form-control" value="{{ item.puntos_formulario or 0 }}">
                <small>Solo editable si no hay certificación.</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">Calificación total (auto)</label>
                <input type="text" class="form-control provform-readonly" id="cal_total" value="{{ item.calificacion_total or 0 }}" readonly>
              </div>

              <div class="col-md-3">
                <label class="form-label">Resultado (auto)</label><br>
                <span id="resultado_badge" class="badge badge-noaprob px-3 py-2">{{ item.resultado_evaluacion or 'No Aprobado por Seguridad' }}</span>
              </div>

              <div class="col-12">
                <div class="provform-section-box">
                  <div class="provform-section-title">Evidencias y observaciones</div>
                  <div class="provform-section-subtitle">
                    Adjunta soportes en PDF y registra observaciones complementarias sobre el proveedor, el análisis efectuado y los hallazgos identificados.
                  </div>
                </div>
              </div>

              {% if is_edit %}
              <div class="col-12">
                <label class="form-label">Evidencias existentes</label>
                {% if item.evidencias %}
                  <div class="row g-3">
                    {% for ev in item.evidencias %}
                    <div class="col-md-6">
                      <div class="provdet-file-card d-flex justify-content-between align-items-center">
                        <div class="provdet-file-meta">
                          <div class="provdet-file-label">Archivo</div>
                          <a class="provdet-file-name" href="{{ url_for('proveedores_evidencia_view', evi_id=ev.id, next='proveedores_edit', reg_id=item.id) }}">{{ ev.original_name or ev.filename }}</a>
                          <div class="provdet-file-size">{{ (ev.size / 1024)|round(1) if ev.size else 0 }} KB</div>
                        </div>

                        <button type="submit"
                                class="btn btn-sm btn-danger rounded-pill"
                                formaction="{{ url_for('proveedores_evidencia_delete', evi_id=ev.id) }}"
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
                  <div class="provdet-empty-box">No hay evidencias cargadas.</div>
                {% endif %}
              </div>
              {% endif %}

              <div class="col-12">
                <label class="form-label">{% if is_edit %}Agregar nuevas evidencias (PDF){% else %}Evidencias (PDF, puedes adjuntar varios){% endif %}</label>
                <input type="file" id="evidencias" name="evidencias" accept=".pdf" multiple class="form-control" onchange="acumularEvidenciasPDF(this)">
                <small class="text-muted">Puedes seleccionar varios a la vez o ir agregando en varias rondas.</small>
                <div id="lista_evidencias_nuevas" class="mt-2"></div>
              </div>

              <div class="col-12">
                <label class="form-label">Observaciones</label>
                <textarea name="observaciones" class="form-control" rows="2">{{ item.observaciones or '' }}</textarea>
              </div>

            </div>

            <div class="provform-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                {% if is_edit %}Guardar cambios{% else %}Guardar{% endif %}
              </button>

              <a href="{{ url_for('proveedores_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold provform-cancel-btn"
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

      .provform-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }

      .provform-header-card{
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

      .provform-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .provform-header-overlay{
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

      .provform-header-overlay::before{
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

      .provform-header-text{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .provform-header-text::before{
        content:"SGSI · Gestión de Proveedores";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .provform-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .provform-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .provform-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .provform-header-actions .btn,
      .provform-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .provform-back-btn,
      .provform-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .provform-back-btn:hover,
      .provform-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .provform-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .provform-card-body{
        padding:18px;
      }

      .provform-section-box{
        background:#eef5ff;
        border:1px solid #d9eaff;
        border-left:6px solid #0b4a8f;
        border-radius:14px;
        padding:12px 14px;
        margin:10px 0 12px;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .provform-section-title{
        font-size:.90rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1.1;
        margin-bottom:4px;
      }

      .provform-section-subtitle{
        font-size:.78rem;
        color:#475569;
        line-height:1.35;
      }

      .provform-card .form-label{
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

      textarea.form-control{
        min-height:72px;
        resize:vertical;
      }

      .form-control:focus,
      .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }

      .provform-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
        width:100%;
      }

      .badge,
      .badge-verde-claro,
      .badge-verde-oscuro,
      .badge-amarillo,
      .badge-rojo,
      .badge-aprobado,
      .badge-revision,
      .badge-noaprob{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .badge-verde-claro{ background:#d1fae5; color:#065f46; }
      .badge-verde-oscuro{ background:#10b981; color:#ffffff; }
      .badge-amarillo{ background:#fef3c7; color:#92400e; }
      .badge-rojo{ background:#fee2e2; color:#991b1b; }
      .badge-aprobado{ background:#dcfce7; color:#166534; }
      .badge-revision{ background:#fef3c7; color:#92400e; }
      .badge-noaprob{ background:#fee2e2; color:#991b1b; }

      .btn.rounded-pill{
        border-radius:10px !important;
      }

      @media (max-width:992px){
        .provform-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .provform-header-card{
          min-height:88px;
        }

        .provform-title{
          font-size:1.20rem;
        }

        .provform-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .provform-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .provform-header-overlay::before{
          margin:0;
        }

        .provform-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .provform-header-actions .btn,
        .provform-bottom-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      const AREAS_RESP = {
        {% for a in areas %}
        "{{ a.id }}": {nombre: {{ (a.responsable_nombre or '')|tojson }}, cargo: {{ (a.responsable_cargo or '')|tojson }}},
        {% endfor %}
      };

      const CRIT_MUY_BAJA_MAX = {{ cfg.crit_muy_baja_max or 25 }};
      const CRIT_BAJA_MAX     = {{ cfg.crit_baja_max or 50 }};
      const CRIT_MEDIA_MAX    = {{ cfg.crit_media_max or 75 }};
      const PCT_APROB_MIN     = {{ cfg.pct_aprob_min or 81 }};
      const PCT_REV_MIN       = {{ cfg.pct_revision_min or 61 }};
      const MIN_CERTS_100     = {{ cfg.min_certificaciones_aprobado or 1 }};

      const PESO_TRANSVERSAL       = {{ cfg.peso_transversal or 0 }};
      const PESO_ESENCIAL          = {{ cfg.peso_esencial or 0 }};
      const PESO_PLAN_CONTINUIDAD  = {{ cfg.peso_plan_continuidad or 0 }};
      const PESO_PLAN_RECUPERACION = {{ cfg.peso_plan_recuperacion or 0 }};
      const PESO_ALTERNATIVAS      = {{ cfg.peso_alternativas or 0 }};
      const PESO_IMPACTO_FALLA     = {{ cfg.peso_impacto_falla or 0 }};
      const PESO_PLAN_MIGRACION    = {{ cfg.peso_plan_migracion or 0 }};
      const PESO_INFO_SENSIBLE     = {{ cfg.peso_info_sensible or 0 }};
      const PESO_DATOS_PERSONALES  = {{ cfg.peso_datos_personales or 0 }};
      const PESO_NUBE              = {{ cfg.peso_nube or 0 }};
      const PESO_SLA               = {{ cfg.peso_sla or 0 }};

      function fillResp(){
        const areaId = document.getElementById('provArea').value;
        const data = AREAS_RESP[areaId] || {nombre:'', cargo:''};
        document.getElementById('provResp').value = data.nombre || '';
        document.getElementById('provCargo').value = data.cargo || '';
      }

      function setCertFieldsEnabled(enabled){
        document.getElementById('num_certificaciones').disabled = !enabled;
        document.getElementById('nombre_certificaciones').disabled = !enabled;
      }

      function recalc(){
        const yn = id => (document.getElementById(id)?.value || 'No');
        const impacto = document.getElementById('impacto_falla')?.value || 'Bajo';

        const val_alc = yn('es_transversal') === 'Sí' ? PESO_TRANSVERSAL : 0;
        const val_esen = yn('es_esencial') === 'Sí' ? PESO_ESENCIAL : 0;
        const val_plan = yn('tiene_plan_cont') === 'Sí' ? 0 : PESO_PLAN_CONTINUIDAD;
        const val_plan_rec = yn('tiene_plan_rec') === 'Sí' ? 0 : PESO_PLAN_RECUPERACION;
        const val_alt = yn('existen_alternativas') === 'Sí' ? 0 : PESO_ALTERNATIVAS;
        const val_mig = yn('existe_plan_migracion') === 'Sí' ? 0 : PESO_PLAN_MIGRACION;
        const val_inf = yn('procesa_info_sensible') === 'Sí' ? PESO_INFO_SENSIBLE : 0;
        const val_datos = yn('procesa_datos_personales') === 'Sí' ? PESO_DATOS_PERSONALES : 0;
        const val_nube = yn('procesa_info_nube') === 'Sí' ? PESO_NUBE : 0;
        const val_sla = yn('incluye_sla') === 'Sí' ? 0 : PESO_SLA;

        let val_impacto = 0;
        if (impacto === 'Alto') val_impacto = PESO_IMPACTO_FALLA;
        else if (impacto === 'Medio') val_impacto = Math.round(PESO_IMPACTO_FALLA * 0.5);

        document.getElementById('val_alc').innerText = val_alc;
        document.getElementById('val_esen').innerText = val_esen;
        document.getElementById('val_plan').innerText = val_plan;
        document.getElementById('val_plan_rec').innerText = val_plan_rec;
        document.getElementById('val_alt').innerText = val_alt;
        document.getElementById('val_impacto').innerText = val_impacto;
        document.getElementById('val_mig').innerText = val_mig;
        document.getElementById('val_inf').innerText = val_inf;
        document.getElementById('val_datos').innerText = val_datos;
        document.getElementById('val_nube').innerText = val_nube;
        document.getElementById('val_sla').innerText = val_sla;

        const total = val_alc + val_esen + val_plan + val_plan_rec + val_alt + val_impacto + val_mig + val_inf + val_datos + val_nube + val_sla;
        document.getElementById('criticidad_pct').value = total;

        const ct = document.getElementById('criticidad_texto');
        if (total <= CRIT_MUY_BAJA_MAX){
          ct.className='badge badge-verde-claro mt-1';
          ct.innerText='Criticidad muy baja';
        } else if (total <= CRIT_BAJA_MAX){
          ct.className='badge badge-verde-oscuro mt-1';
          ct.innerText='Criticidad baja';
        } else if (total <= CRIT_MEDIA_MAX){
          ct.className='badge badge-amarillo mt-1';
          ct.innerText='Criticidad media';
        } else {
          ct.className='badge badge-rojo mt-1';
          ct.innerText='Criticidad alta';
        }

        const cert = document.getElementById('tiene_certificacion').value;
        const pf = document.getElementById('puntos_formulario');

        setCertFieldsEnabled(cert === 'Sí');

        let numCerts = parseInt(document.getElementById('num_certificaciones').value || '0');

        let pt_cert = 0;
        if (cert === 'Sí' && numCerts >= MIN_CERTS_100){
          pt_cert = 100;
        }
        document.getElementById('pt_cert').innerText = pt_cert;

        const req_form = (pt_cert === 100 ? 'No' : 'Sí');
        document.getElementById('req_form').innerText = req_form;

        pf.disabled = (cert === 'Sí' && pt_cert === 100);

        let total_cal = pt_cert + (parseInt(pf.value || '0'));

        if (total <= CRIT_BAJA_MAX){
          total_cal = 100;
        }

        document.getElementById('cal_total').value = total_cal;

        const rb = document.getElementById('resultado_badge');
        rb.className = 'badge px-3 py-2';

        if (total <= CRIT_BAJA_MAX){
          rb.classList.add('badge-aprobado');
          rb.innerText='Aprobado Por Seguridad';
        }
        else if (total_cal >= PCT_APROB_MIN){
          rb.classList.add('badge-aprobado');
          rb.innerText='Aprobado por Seguridad';
        }
        else if (total_cal >= PCT_REV_MIN){
          rb.classList.add('badge-revision');
          rb.innerText='En revisión';
        }
        else{
          rb.classList.add('badge-noaprob');
          rb.innerText='No Aprobado por Seguridad';
        }
      }

      let evidenciasBufferDT = new DataTransfer();

      function renderListaEvidenciasPDF() {
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
          row.innerHTML = `<span class="text-truncate small" style="max-width:260px;">📎 ${f.name}</span><button type="button" class="btn btn-link text-danger p-0 small" onclick="removeEvidenciaPDF(${i})">🗑️</button>`;
          cont.appendChild(row);
        }
      }

      function acumularEvidenciasPDF(inputEl) {
        for (const f of inputEl.files) {
          evidenciasBufferDT.items.add(f);
        }
        inputEl.files = evidenciasBufferDT.files;
        renderListaEvidenciasPDF();
      }

      function removeEvidenciaPDF(index) {
        const tmp = new DataTransfer();
        for (let i = 0; i < evidenciasBufferDT.files.length; i++) {
          if (i !== index) tmp.items.add(evidenciasBufferDT.files[i]);
        }
        evidenciasBufferDT = tmp;
        const inputEl = document.getElementById('evidencias');
        if (inputEl) inputEl.files = evidenciasBufferDT.files;
        renderListaEvidenciasPDF();
      }

      window.addEventListener('DOMContentLoaded', ()=>{
        fillResp();
        recalc();
        renderListaEvidenciasPDF();
      });
    </script>
    """
    return render_template_string(
        html,
        item=item,
        areas=areas,
        paises=paises,
        cfg=cfg,
        is_edit=is_edit
    )


# =========================
# AGREGAR — Registro de Proveedores
# =========================
@app.route('/proveedores/new', methods=['GET', 'POST'])
@login_required
def proveedores_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('proveedores_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores"):
        flash("No tiene permiso para agregar registro de proveedores.", "danger")
        return redirect(url_for('proveedores_matriz'))

    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()
    cfg = ProveedorEvalConfig.get()
    paises = _proveedor_paises()

    if request.method == 'POST':
        it = ProveedorEvaluacion()

        it.fecha_eval_seguridad = request.form.get('fecha_eval_seguridad')
        it.nombre_proveedor = (request.form.get('nombre_proveedor') or '').strip()
        it.estatus_proveedor = (request.form.get('estatus_proveedor') or '').strip()

        it.area_id = request.form.get('area_id', type=int)
        it.responsable_area_nombre, it.responsable_area_cargo = _proveedor_fill_area_data(it.area_id)

        it.nombre_cargo_evaluador = (request.form.get('nombre_cargo_evaluador') or '').strip()
        it.pais_origen = (request.form.get('pais_origen') or '').strip()
        it.pais_servicio = (request.form.get('pais_servicio') or '').strip()
        it.desc_producto_servicio = (request.form.get('desc_producto_servicio') or '').strip()
        it.estado_avance = request.form.get('estado_avance') or 'Operando'
        it.estado_evaluacion = request.form.get('estado_evaluacion') or 'Proceso'
        it.observaciones = (request.form.get('observaciones') or '').strip()

        _proveedor_apply_scores(it, request.form, cfg)

        db.session.add(it)
        db.session.flush()

        _proveedor_save_files(it, request.files.getlist('evidencias'))

        db.session.commit()
        flash("Proveedor registrado.", "success")
        return redirect(url_for('proveedores_matriz'))

    html = _render_proveedor_form(
        item=None,
        areas=areas,
        paises=paises,
        cfg=cfg,
        is_edit=False
    )
    return render_template_string(BASE, content=Markup(html))


# =========================
# EVIDENCIA — Descargar
# =========================
@app.route('/proveedores/evidencia/<int:evi_id>')
@login_required
def proveedores_evidencia_download(evi_id):
    evi = ProveedorEvidencia.query.get_or_404(evi_id)
    directory = app.config['UPLOAD_PROVEEDORES_DIR']
    return send_from_directory(
        directory=directory,
        path=evi.filename,
        as_attachment=True,
        download_name=evi.original_name,
        mimetype=evi.mime
    )


# =========================
# EVIDENCIA — RAW / VISOR
# =========================
@app.route('/proveedores/evidencia/<int:evi_id>/raw')
@login_required
def proveedores_evidencia_raw(evi_id):
    evi = ProveedorEvidencia.query.get_or_404(evi_id)
    fullpath = os.path.join(app.config['UPLOAD_PROVEEDORES_DIR'], evi.filename)

    resp = send_file(
        fullpath,
        mimetype='application/pdf',
        download_name=evi.original_name,
        as_attachment=False
    )
    resp.headers['Content-Disposition'] = f'inline; filename="{evi.original_name}"'
    return resp


@app.route('/proveedores/evidencia/<int:evi_id>/ver')
@login_required
def proveedores_evidencia_view(evi_id):
    evi = ProveedorEvidencia.query.get_or_404(evi_id)

    path = os.path.join(app.config['UPLOAD_PROVEEDORES_DIR'], evi.filename)
    if not os.path.isfile(path):
        abort(404)

    ext = os.path.splitext(evi.filename or '')[1].lower()
    is_pdf = ext == '.pdf'
    is_office = ext in {'.doc', '.docx', '.xls', '.xlsx'}
    is_image = ext in {'.png', '.jpg', '.jpeg', '.webp', '.gif'}

    next_ep = request.args.get('next')
    reg_id = request.args.get('reg_id', type=int)

    if next_ep == 'proveedores_detalle' and reg_id:
        back_url = url_for('proveedores_detalle', id=reg_id)
        back_label = '⬅ Volver al Detalle'
    elif next_ep == 'proveedores_edit' and reg_id:
        back_url = url_for('proveedores_edit', id=reg_id)
        back_label = '⬅ Volver a Edición'
    else:
        back_url = url_for('proveedores_matriz')
        back_label = '⬅ Volver a la Matriz'

    pdf_converted_name = None
    if is_office:
        try:
            converted_dir = app.config.get(
                'UPLOAD_PROVEEDORES_CONVERTED_DIR',
                os.path.join(app.root_path, 'static', 'converted_proveedores_evidencias')
            )
            os.makedirs(converted_dir, exist_ok=True)

            pdf_converted_path = ensure_pdf_from_office(path, output_dir=converted_dir)
            if pdf_converted_path and os.path.isfile(pdf_converted_path):
                pdf_converted_name = os.path.basename(pdf_converted_path)
        except Exception:
            pdf_converted_name = None

    inner_html = """
    <div class="provevi-shell">
      <div class="provevi-header-actions">
        <a href="{{ back_url }}" class="btn rounded-pill px-4 py-2 fw-bold provevi-back-btn">
          {{ back_label }}
        </a>
        <div class="provevi-file-pill" title="{{ original_name }}">📎 {{ original_name }}</div>
      </div>

      <div class="provevi-card">
        <div class="provevi-card-body">
          {% if is_pdf %}
            <iframe src="{{ url_for('proveedores_evidencia_raw', evi_id=evi_id) }}" class="provevi-frame"></iframe>
          {% elif pdf_converted_name %}
            <iframe src="{{ url_for('static', filename='converted_proveedores_evidencias/' ~ pdf_converted_name) }}" class="provevi-frame"></iframe>
          {% elif is_image %}
            <div class="text-center">
              <img src="{{ url_for('proveedores_evidencia_raw', evi_id=evi_id) }}" class="img-fluid rounded shadow-sm">
            </div>
          {% else %}
            <div class="alert alert-warning mb-0">
              No se pudo mostrar vista previa.
              <a href="{{ url_for('proveedores_evidencia_download', evi_id=evi_id) }}" target="_blank">Abrir archivo</a>
            </div>
          {% endif %}
        </div>
      </div>
    </div>

    <style>
      body{background-image:url('/static/img/ccsgsi.jpg');background-size:cover;background-position:center;background-attachment:fixed;background-repeat:no-repeat;}
      .provevi-shell{width:96%;max-width:1650px;margin:10px auto 30px auto;}
      .provevi-header-actions{display:flex;justify-content:center;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px;}
      .provevi-back-btn{background:#ffffff;color:#000000;border:2px solid #ffffff;box-shadow:0 4px 10px rgba(0,0,0,.10);}
      .provevi-back-btn:hover{background:#f3f4f6;color:#000000;border-color:#f3f4f6;}
      .provevi-file-pill{background:#3f86d6;color:#fff;border-radius:999px;padding:10px 16px;font-weight:700;max-width:520px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;box-shadow:0 4px 10px rgba(0,0,0,.10);}
      .provevi-card{background:rgba(248,252,255,.96)!important;border-radius:18px;backdrop-filter:blur(6px);box-shadow:0 10px 24px rgba(0,0,0,.18);overflow:hidden;}
      .provevi-card-body{padding:16px;}
      .provevi-frame{width:100%;height:78vh;border:none;border-radius:12px;background:#fff;}
    </style>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            inner_html,
            back_url=back_url,
            back_label=back_label,
            evi_id=evi_id,
            original_name=evi.original_name or evi.filename,
            is_pdf=is_pdf,
            is_image=is_image,
            pdf_converted_name=pdf_converted_name
        ))
    )


# =========================
# EVIDENCIA — Eliminar
# =========================
@app.route('/proveedores/evidencia/<int:evi_id>/delete', methods=['POST'])
@login_required
def proveedores_evidencia_delete(evi_id):
    evi = ProveedorEvidencia.query.get_or_404(evi_id)
    p = os.path.join(app.config['UPLOAD_PROVEEDORES_DIR'], evi.filename)
    try:
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass

    proveedor_id = evi.proveedor_id
    db.session.delete(evi)
    db.session.commit()
    flash("Evidencia eliminada.", "success")
    return redirect(url_for('proveedores_edit', id=proveedor_id))


# =========================
# MATRIZ — Registro de Proveedores
# =========================
@app.route('/proveedores', methods=['GET'])
@login_required
def proveedores_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores"):
            flash("No tiene permiso para ver los registros de proveedores.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    filtro_proveedor = (request.args.get('proveedor') or '').strip()
    filtro_avance = (request.args.get('avance') or '').strip()
    filtro_area_responsable = (request.args.get('area_responsable') or '').strip()
    filtro_criticidad = (request.args.get('criticidad') or '').strip()
    filtro_resultado = (request.args.get('resultado') or '').strip()

    query = (
        ProveedorEvaluacion.query
        .options(
            selectinload(ProveedorEvaluacion.area),
            selectinload(ProveedorEvaluacion.evidencias)
        )
    )

    if filtro_proveedor:
        query = query.filter(ProveedorEvaluacion.nombre_proveedor == filtro_proveedor)

    if filtro_avance:
        query = query.filter(ProveedorEvaluacion.estado_avance == filtro_avance)

    if filtro_area_responsable:
        query = query.filter(ProveedorEvaluacion.area.has(area=filtro_area_responsable))

    if filtro_criticidad:
        query = query.filter(ProveedorEvaluacion.criticidad_texto == filtro_criticidad)

    if filtro_resultado:
        query = query.filter(ProveedorEvaluacion.resultado_evaluacion == filtro_resultado)

    items = query.order_by(ProveedorEvaluacion.id.desc()).all()

    opciones_proveedor = [
        x[0] for x in db.session.query(ProveedorEvaluacion.nombre_proveedor)
        .filter(ProveedorEvaluacion.nombre_proveedor.isnot(None))
        .filter(ProveedorEvaluacion.nombre_proveedor != '')
        .distinct()
        .order_by(ProveedorEvaluacion.nombre_proveedor.asc())
        .all()
    ]

    opciones_avance = [
        x[0] for x in db.session.query(ProveedorEvaluacion.estado_avance)
        .filter(ProveedorEvaluacion.estado_avance.isnot(None))
        .filter(ProveedorEvaluacion.estado_avance != '')
        .distinct()
        .order_by(ProveedorEvaluacion.estado_avance.asc())
        .all()
    ]

    opciones_area_responsable = [
        x[0] for x in db.session.query(AreaEmpresa.area)
        .join(ProveedorEvaluacion, ProveedorEvaluacion.area_id == AreaEmpresa.id)
        .filter(AreaEmpresa.area.isnot(None))
        .filter(AreaEmpresa.area != '')
        .distinct()
        .order_by(AreaEmpresa.area.asc())
        .all()
    ]

    opciones_criticidad = [
        x[0] for x in db.session.query(ProveedorEvaluacion.criticidad_texto)
        .filter(ProveedorEvaluacion.criticidad_texto.isnot(None))
        .filter(ProveedorEvaluacion.criticidad_texto != '')
        .distinct()
        .order_by(ProveedorEvaluacion.criticidad_texto.asc())
        .all()
    ]

    opciones_resultado = [
        x[0] for x in db.session.query(ProveedorEvaluacion.resultado_evaluacion)
        .filter(ProveedorEvaluacion.resultado_evaluacion.isnot(None))
        .filter(ProveedorEvaluacion.resultado_evaluacion != '')
        .distinct()
        .order_by(ProveedorEvaluacion.resultado_evaluacion.asc())
        .all()
    ]

    total_general = ProveedorEvaluacion.query.count()
    total_filtrados = len(items)

    html = """
    <div class="provmat-shell">

      <div class="provmat-header-card">
        <div class="provmat-header-overlay">
          <div class="provmat-header-text">
            <h3 class="provmat-title m-0">Registro de Proveedores</h3>
            <div class="provmat-subtitle">
              Visualización resumida del registro de proveedores, criticidad, resultado de evaluación y responsables del proceso
            </div>
          </div>
        </div>
      </div>

      <div class="provmat-header-actions">

        {% if not read_only %}
        <a href="{{ url_for('proveedores_param') }}"
           class="btn btn-secondary rounded-pill px-4 fw-bold"
           onclick="showLoader()">
          ⚙️ Parametrización
        </a>

        <a href="{{ url_for('proveedores_new') }}"
           class="btn btn-primary rounded-pill px-4 fw-bold"
           onclick="showLoader()">
          ➕ Agregar Registro
        </a>
        {% endif %}
      </div>

      <div class="provmat-topbar-card">
        <div class="provmat-topbar-title">Resumen de proveedores</div>
        <div class="provmat-topbar-subtitle">
          Total registros: <strong>{{ total_general }}</strong>
          &nbsp; | &nbsp;
          Mostrando: <strong>{{ total_filtrados }}</strong>
        </div>
      </div>

      <div class="provmat-filter-card">
        <div class="provmat-filter-head">Filtros de búsqueda</div>
        <div class="provmat-filter-body">
          <form method="get">
            <div class="row g-2 align-items-end">

              <div class="col-md-3">
                <label class="form-label provmat-label">Proveedor</label>
                <select name="proveedor" class="form-select form-select-sm provmat-input-sm">
                  <option value="">-- Todos --</option>
                  {% for op in opciones_proveedor %}
                    <option value="{{ op }}" {% if filtro_proveedor == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label provmat-label">Avance</label>
                <select name="avance" class="form-select form-select-sm provmat-input-sm">
                  <option value="">-- Todos --</option>
                  {% for op in opciones_avance %}
                    <option value="{{ op }}" {% if filtro_avance == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label provmat-label">Área responsable</label>
                <select name="area_responsable" class="form-select form-select-sm provmat-input-sm">
                  <option value="">-- Todas --</option>
                  {% for op in opciones_area_responsable %}
                    <option value="{{ op }}" {% if filtro_area_responsable == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label provmat-label">Criticidad</label>
                <select name="criticidad" class="form-select form-select-sm provmat-input-sm">
                  <option value="">-- Todas --</option>
                  {% for op in opciones_criticidad %}
                    <option value="{{ op }}" {% if filtro_criticidad == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label provmat-label">Resultado</label>
                <select name="resultado" class="form-select form-select-sm provmat-input-sm">
                  <option value="">-- Todos --</option>
                  {% for op in opciones_resultado %}
                    <option value="{{ op }}" {% if filtro_resultado == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-1">
                <div class="d-flex gap-2 provmat-filter-actions flex-column">
                  <button type="submit" class="btn btn-primary btn-sm rounded-pill px-3 w-100 fw-bold">
                    Filtrar
                  </button>

                  <a href="{{ url_for('proveedores_matriz') }}"
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

      <div class="provmat-card">
        <div class="provmat-card-body">
          <div class="table-responsive provmat-table-wrap">
            <table class="table table-hover align-middle provmat-table mb-0">
              <thead>
                <tr>
                  <th>Proveedor</th>
                  <th>Estatus</th>
                  <th>Avance</th>
                  <th>Área</th>
                  <th>Criticidad</th>
                  <th>Resultado</th>
                  <th>Responsable</th>
                  <th>Fecha</th>
                  <th class="provmat-col-acciones">Acciones</th>
                </tr>
              </thead>

              <tbody>
                {% for it in items %}
                <tr>
                  <td>{{ it.nombre_proveedor or '—' }}</td>
                  <td>{{ it.estatus_proveedor or '—' }}</td>
                  <td>{{ it.estado_avance or '—' }}</td>
                  <td>{{ it.area.area if it.area else '—' }}</td>

                  <td class="text-center">
                    <span class="badge {{ it.criticidad_color or 'bg-secondary' }}">
                      {{ it.criticidad_texto or '—' }}
                    </span>
                  </td>

                  <td class="text-center">
                    <span class="badge {{ it.resultado_color or 'bg-secondary' }}">
                      {{ it.resultado_evaluacion or '—' }}
                    </span>
                  </td>

                  <td>{{ it.responsable_area_nombre or '—' }}</td>
                  <td>{{ it.fecha_eval_seguridad or '—' }}</td>

                  <td class="provmat-col-acciones">
                    <div class="provmat-actions-wrap">
                      <a href="{{ url_for('proveedores_detalle', id=it.id) }}"
                         class="btn btn-info btn-sm rounded-pill provmat-btn-action text-white fw-bold"
                         onclick="showLoader()">
                        Ver detalle
                      </a>

                      {% if not read_only %}
                        <a href="{{ url_for('proveedores_edit', id=it.id) }}"
                           class="btn btn-warning btn-sm rounded-pill provmat-btn-action fw-bold"
                           onclick="showLoader()">
                          Editar
                        </a>

                        {% set resultado_norm = (it.resultado_evaluacion or '')|trim|lower %}
                        {% set es_aprobado = resultado_norm in ['aprobado', 'aprobado por seguridad'] %}
                        {% if not es_aprobado %}
                          <a href="{{ url_for('agregar_riesgo',
                                               origen='Proveedor',
                                               proveedor_id=it.id,
                                               proveedor=it.nombre_proveedor or '',
                                               activo=it.nombre_proveedor or '',
                                               descripcion=('Riesgo asociado al proveedor: ' ~ (it.nombre_proveedor or '')),
                                               observacion=('Proveedor con resultado de evaluación: ' ~ (it.resultado_evaluacion or 'No Aprobado'))) }}"
                             class="btn btn-danger btn-sm rounded-pill provmat-btn-action fw-bold"
                             onclick="showLoader()">
                            Registrar riesgo
                          </a>
                        {% endif %}

                        <a href="{{ url_for('proveedores_delete', id=it.id) }}"
                           class="btn btn-danger btn-sm rounded-pill provmat-btn-action fw-bold"
                           onclick="return confirm('¿Eliminar este proveedor?');">
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
                  <td colspan="9" class="text-center text-muted py-4">
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

      .provmat-shell{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }

      /* =========================
         HEADER SGSI UNIFICADO
      ========================= */
      .provmat-header-card{
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

      .provmat-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .provmat-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .provmat-header-overlay::before{
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

      .provmat-header-text{
        max-width:1200px;
      }

      .provmat-header-text::before{
        content:"SGSI · Gestión de Proveedores";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .provmat-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .provmat-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES
      ========================= */
      .provmat-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .provmat-header-actions .btn{
        border-radius:10px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 6px 14px rgba(0,0,0,.12);
      }

      .provmat-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .provmat-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      /* =========================
         TOPBAR
      ========================= */
      .provmat-topbar-card{
        background:rgba(255,255,255,.96);
        border-radius:16px;
        box-shadow:0 8px 18px rgba(15,23,42,.14);
        padding:12px 16px;
        margin-bottom:12px;
      }

      .provmat-topbar-title{
        font-weight:900;
        font-size:.95rem;
        color:#101827;
      }

      .provmat-topbar-subtitle{
        font-size:.82rem;
        color:#475569;
      }

      /* =========================
         FILTROS
      ========================= */
      .provmat-filter-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 10px 24px rgba(15,23,42,.16);
        margin-bottom:14px;
        overflow:hidden;
      }

      .provmat-filter-head{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1);
        color:#fff;
        font-weight:800;
        font-size:.82rem;
        padding:10px 14px;
      }

      .provmat-filter-body{
        padding:8px 7px;
      }

      .provmat-label{
        font-size:.70rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        margin-bottom:4px;
      }

      .provmat-input-sm{
        min-height:30px !important;
        font-size:.72rem !important;
        border-radius:10px !important;
        border:1px solid #d9e3f0 !important;
        background:#f8fafc !important;
      }

      .provmat-input-sm:focus{
        border-color:#3f86d6 !important;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#fff !important;
      }

      /* =========================
         CARD PRINCIPAL
      ========================= */
      .provmat-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .provmat-card-body{
        padding:16px;
      }

      /* =========================
         TABLA SGSI
      ========================= */
      .provmat-table thead th{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        font-size:.78rem;
        border:none;
        padding:9px 8px;
        text-align:center;
      }

      .provmat-table td{
        font-size:.82rem;
        padding:9px 8px;
        vertical-align:middle;
        border-bottom:1px solid #e5edf7;
      }

      .provmat-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .provmat-table tbody tr:hover{
        background:#eef6ff;
      }

      /* =========================
         ACCIONES
      ========================= */
      .provmat-col-acciones{
        width:160px;
        text-align:center;
      }

      .provmat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
      }

      .provmat-btn-action{
        font-size:.72rem;
        padding:4px 10px;
        min-width:110px;
        border-radius:999px;
        font-weight:800;
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

      .badge-verde-claro{ background:#d1fae5; color:#065f46; }
      .badge-verde-oscuro{ background:#10b981; color:#fff; }
      .badge-amarillo{ background:#fef3c7; color:#92400e; }
      .badge-rojo{ background:#fee2e2; color:#991b1b; }
      .badge-aprobado{ background:#dcfce7; color:#166534; }
      .badge-revision{ background:#fef3c7; color:#92400e; }
      .badge-noaprob{ background:#fee2e2; color:#991b1b; }

      /* =========================
         RESPONSIVE
      ========================= */
      @media (max-width:992px){
        .provmat-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .provmat-title{
          font-size:1.18rem;
        }

        .provmat-subtitle{
          font-size:.75rem;
        }

        .provmat-card-body{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .provmat-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .provmat-header-overlay::before{
          margin:0;
        }

        .provmat-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        opciones_proveedor=opciones_proveedor,
        opciones_avance=opciones_avance,
        opciones_area_responsable=opciones_area_responsable,
        opciones_criticidad=opciones_criticidad,
        opciones_resultado=opciones_resultado,
        filtro_proveedor=filtro_proveedor,
        filtro_avance=filtro_avance,
        filtro_area_responsable=filtro_area_responsable,
        filtro_criticidad=filtro_criticidad,
        filtro_resultado=filtro_resultado,
        total_filtrados=total_filtrados,
        total_general=total_general
    )
    return render_template_string(BASE, content=Markup(inner))


# =========================
# DETALLE — Proveedor
# =========================
@app.route('/proveedores/detalle/<int:id>')
@login_required
def proveedores_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores"):
            flash("No tiene permiso para ver el detalle del proveedor.", "danger")
            return redirect(url_for('proveedores_matriz'))
        read_only = False

    it = (
        ProveedorEvaluacion.query
        .options(
            selectinload(ProveedorEvaluacion.area),
            selectinload(ProveedorEvaluacion.evidencias)
        )
        .get_or_404(id)
    )

    def fmt_fecha(v):
        if not v:
            return '—'
        try:
            return v.strftime('%Y-%m-%d')
        except Exception:
            return str(v)

    def yn_badge(v):
        val = (v or '').strip().lower()
        if val in ('sí', 'si'):
            return Markup('<span class="badge badge-aprobado px-3 py-2">Sí</span>')
        if val == 'no':
            return Markup('<span class="badge badge-noaprob px-3 py-2">No</span>')
        return Markup('<span class="badge bg-secondary px-3 py-2">—</span>')

    html = """
    <div class="provdet-shell">

      <div class="provdet-header-card">
        <div class="provdet-header-overlay">
          <div class="provdet-header-text">
            <h3 class="provdet-title m-0">Detalle del Proveedor</h3>
            <div class="provdet-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="provdet-header-actions">
        <a href="{{ url_for('proveedores_matriz') }}"
           class="btn rounded-pill px-4 fw-bold provdet-back-btn">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('proveedores_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="provdet-card">
        <div class="provdet-card-body">

          <!-- =========================
               INFORMACIÓN GENERAL
          ========================== -->
          <div class="provdet-section">
            <div class="provdet-section-title">Información general del proveedor</div>
            <div class="row g-3">

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Fecha de registro por el área de seguridad</div>
                  <div class="provdet-value">{{ fmt_fecha(it.fecha_eval_seguridad) }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Nombre del proveedor</div>
                  <div class="provdet-value provdet-value-lg">{{ it.nombre_proveedor or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Estatus del proveedor</div>
                  <div class="provdet-value">{{ it.estatus_proveedor or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Área responsable</div>
                  <div class="provdet-value">{{ it.area.area if it.area else '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">Nombre del responsable del área</div>
                  <div class="provdet-value">{{ it.responsable_area_nombre or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">Cargo del responsable del área</div>
                  <div class="provdet-value">{{ it.responsable_area_cargo or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">Nombre y cargo del evaluador</div>
                  <div class="provdet-value">{{ it.nombre_cargo_evaluador or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">País de origen</div>
                  <div class="provdet-value">{{ it.pais_origen or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">País de servicio</div>
                  <div class="provdet-value">{{ it.pais_servicio or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Estado / avance</div>
                  <div class="provdet-value">{{ it.estado_avance or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Estado del registro</div>
                  <div class="provdet-value">{{ it.estado_evaluacion or '—' }}</div>
                </div>
              </div>

              <div class="col-12">
                <div class="provdet-field">
                  <div class="provdet-label">Descripción del producto / servicio</div>
                  <div class="provdet-value provdet-value-lg">{{ it.desc_producto_servicio or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <!-- =========================
               CALIFICACIÓN DEL PROVEEDOR
          ========================== -->
          <div class="provdet-section">
            <div class="provdet-section-title">Calificación del proveedor</div>
            <div class="row g-3">

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Es transversal a toda la organización?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.es_transversal) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_alcance or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Es esencial para la continuidad?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.es_esencial) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_esencial or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Tiene plan de continuidad?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.tiene_plan_cont) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_plan_cont or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Tiene plan de recuperación?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.tiene_plan_rec) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_plan_rec or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Existen alternativas en el mercado?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.existen_alternativas) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_alternativas or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">Impacto en caso de falla</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span class="badge bg-secondary px-3 py-2">{{ it.impacto_falla or '—' }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_impacto_falla or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Existe plan de migración?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.existe_plan_migracion) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_plan_migracion or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Procesa / almacena información sensible?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.procesa_info_sensible) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_info_sensible or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Procesa / almacena datos personales?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.procesa_datos_personales) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_datos_personales or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="provdet-field">
                  <div class="provdet-label">¿Procesa / almacena información en la nube?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.procesa_info_nube) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_nube or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="provdet-field">
                  <div class="provdet-label">¿Incluye SLA definidos?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.incluye_sla) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_sla or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field text-center">
                  <div class="provdet-label">Criticidad total</div>
                  <div class="provdet-big-number">{{ it.criticidad_pct or 0 }}%</div>
                  <div class="mt-2">
                    <span class="badge {{ it.criticidad_color or 'bg-secondary' }} px-3 py-2">
                      {{ it.criticidad_texto or '—' }}
                    </span>
                  </div>
                </div>
              </div>


              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Requiere formulario?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.requiere_formulario) }}</span>
                    <span class="provdet-score">Puntos cert.: {{ it.puntos_certificacion or 0 }}%</span>
                  </div>
                </div>
              </div>

            </div>
          </div>

          <!-- =========================
               REGISTRO DEL PROVEEDOR
          ========================== -->
          <div class="provdet-section">
            <div class="provdet-section-title">Registro del proveedor</div>
            <div class="row g-3">

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">¿Tiene certificación?</div>
                  <div class="provdet-value">{{ yn_badge(it.tiene_certificacion) }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Número de certificaciones</div>
                  <div class="provdet-value">{{ it.num_certificaciones or 0 }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Puntos obtenidos en el formulario</div>
                  <div class="provdet-value">{{ it.puntos_formulario or 0 }}%</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Puntos por certificación</div>
                  <div class="provdet-value">{{ it.puntos_certificacion or 0 }}%</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field text-center">
                  <div class="provdet-label">Calificación total</div>
                  <div class="provdet-big-number">{{ it.calificacion_total or 0 }}%</div>
                  <div class="mt-2">
                    <span class="badge {{ it.resultado_color or 'bg-secondary' }} px-3 py-2">
                      {{ it.resultado_evaluacion or '—' }}
                    </span>
                  </div>
                </div>
              </div>

              <div class="col-12">
                <div class="provdet-field">
                  <div class="provdet-label">Nombre de las certificaciones</div>
                  <div class="provdet-value provdet-value-lg">{{ it.nombre_certificaciones or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <!-- =========================
               EVIDENCIAS
          ========================== -->
          <div class="provdet-section">
            <div class="provdet-section-title">Evidencias</div>

            {% if it.evidencias %}
              <div class="provdet-ev-grid">
                {% for ev in it.evidencias %}
                  <div class="provdet-file-card">
                    <div class="provdet-file-left">
                      <div class="provdet-file-icon">PDF</div>
                      <div class="provdet-file-meta">
                        <div class="provdet-file-label">Archivo</div>
                        <a class="provdet-file-name"
                           href="{{ url_for('proveedores_evidencia_view', evi_id=ev.id, next='proveedores_detalle', reg_id=it.id) }}">
                          {{ ev.original_name or ev.filename }}
                        </a>
                        <div class="provdet-file-size">
                          {{ (ev.size / 1024)|round(1) if ev.size else 0 }} KB
                        </div>
                      </div>
                    </div>

                    <a href="{{ url_for('proveedores_evidencia_download', evi_id=ev.id) }}"
                       class="btn btn-outline-primary rounded-pill px-3 fw-bold">
                      Descargar
                    </a>
                  </div>
                {% endfor %}
              </div>
            {% else %}
              <div class="provdet-empty-box">No hay evidencias cargadas.</div>
            {% endif %}
          </div>

          <!-- =========================
               OBSERVACIONES
          ========================== -->
          <div class="provdet-section">
            <div class="provdet-section-title">Observaciones</div>
            <div class="provdet-field">
              <div class="provdet-value provdet-value-lg">{{ it.observaciones or '—' }}</div>
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

      .provdet-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }

      .provdet-header-card{
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

      .provdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .provdet-header-overlay{
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

      .provdet-header-overlay::before{
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

      .provdet-header-text{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .provdet-header-text::before{
        content:"SGSI · Detalle de Proveedor";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .provdet-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .provdet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .provdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .provdet-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .provdet-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .provdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .provdet-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .provdet-card-body{
        padding:18px;
      }

      .provdet-section{
        margin-bottom:14px;
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .provdet-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      .provdet-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        min-height:78px;
        height:100%;
      }

      .provdet-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .provdet-value{
        color:#101827;
        font-size:.86rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .provdet-value-lg{
        min-height:72px;
      }

      .provdet-big-number{
        font-size:1.75rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1.1;
      }

      .provdet-score{
        font-size:.68rem;
        font-weight:900;
        color:#475569;
        white-space:nowrap;
      }

      .provdet-ev-grid{
        display:grid;
        grid-template-columns:repeat(auto-fit, minmax(320px, 1fr));
        gap:14px;
      }

      .provdet-file-card{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:8px 7px;
        box-shadow:0 6px 14px rgba(15,23,42,.08);
        transition:all .2s ease;
      }

      .provdet-file-card:hover{
        transform:translateY(-3px);
        box-shadow:0 10px 20px rgba(15,23,42,.13);
      }

      .provdet-file-left{
        display:flex;
        align-items:center;
        gap:12px;
        min-width:0;
      }

      .provdet-file-icon{
        width:52px;
        height:52px;
        min-width:52px;
        border-radius:12px;
        background:linear-gradient(135deg,#b91c1c,#b91c1c);
        color:#ffffff;
        display:flex;
        align-items:center;
        justify-content:center;
        font-weight:950;
        font-size:.82rem;
        flex:0 0 auto;
      }

      .provdet-file-meta{
        min-width:0;
      }

      .provdet-file-label{
        font-size:.70rem;
        color:#475569;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
      }

      .provdet-file-name{
        display:block;
        font-weight:900;
        color:#1d4ed8;
        text-decoration:none;
        word-break:break-word;
        font-size:.82rem;
        margin-top:2px;
      }

      .provdet-file-name:hover{
        text-decoration:underline;
      }

      .provdet-file-size{
        font-size:.70rem;
        color:#475569;
        margin-top:3px;
        font-weight:700;
      }

      .provdet-empty-box{
        background:#f8fbff;
        border:1px dashed #b8cce8;
        border-radius:14px;
        padding:16px;
        text-align:center;
        color:#475569;
        font-size:.82rem;
        font-weight:800;
      }

      .badge,
      .badge-verde-claro,
      .badge-verde-oscuro,
      .badge-amarillo,
      .badge-rojo,
      .badge-aprobado,
      .badge-revision,
      .badge-noaprob{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .badge-verde-claro{ background:#d1fae5; color:#065f46; }
      .badge-verde-oscuro{ background:#10b981; color:#ffffff; }
      .badge-amarillo{ background:#fef3c7; color:#92400e; }
      .badge-rojo{ background:#fee2e2; color:#991b1b; }
      .badge-aprobado{ background:#dcfce7; color:#166534; }
      .badge-revision{ background:#fef3c7; color:#92400e; }
      .badge-noaprob{ background:#fee2e2; color:#991b1b; }

      .btn.rounded-pill{
        border-radius:10px !important;
      }

      @media (max-width:992px){
        .provdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .provdet-header-card{
          min-height:88px;
        }

        .provdet-title{
          font-size:1.20rem;
        }

        .provdet-card-body{
          padding:8px 7px;
        }

        .provdet-file-card{
          flex-direction:column;
          align-items:flex-start;
        }
      }

      @media (max-width:768px){
        .provdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .provdet-header-overlay::before{
          margin:0;
        }

        .provdet-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .provdet-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        it=it,
        read_only=read_only,
        fmt_fecha=fmt_fecha,
        yn_badge=yn_badge
    )
    return render_template_string(BASE, content=Markup(inner))


# =========================
# EDITAR — Proveedor
# =========================
@app.route('/proveedores/edit/<int:id>', methods=['GET','POST'])
@login_required
def proveedores_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores")
    ):
        flash("No tiene permiso para editar registros del módulo de proveedores.", "danger")
        return redirect(url_for('proveedores_matriz'))

    item = (
        ProveedorEvaluacion.query
        .options(
            selectinload(ProveedorEvaluacion.area),
            selectinload(ProveedorEvaluacion.evidencias)
        )
        .get_or_404(id)
    )

    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()
    cfg = ProveedorEvalConfig.get()
    paises = _proveedor_paises()

    if request.method == 'POST':
        item.fecha_eval_seguridad = request.form.get('fecha_eval_seguridad')
        item.nombre_proveedor = (request.form.get('nombre_proveedor') or '').strip()
        item.estatus_proveedor = (request.form.get('estatus_proveedor') or '').strip()

        item.area_id = request.form.get('area_id', type=int)
        item.responsable_area_nombre, item.responsable_area_cargo = _proveedor_fill_area_data(item.area_id)

        item.nombre_cargo_evaluador = (request.form.get('nombre_cargo_evaluador') or '').strip()
        item.pais_origen = (request.form.get('pais_origen') or '').strip()
        item.pais_servicio = (request.form.get('pais_servicio') or '').strip()
        item.desc_producto_servicio = (request.form.get('desc_producto_servicio') or '').strip()
        item.estado_avance = request.form.get('estado_avance') or item.estado_avance
        item.estado_evaluacion = request.form.get('estado_evaluacion') or item.estado_evaluacion
        item.observaciones = (request.form.get('observaciones') or '').strip()

        _proveedor_apply_scores(item, request.form, cfg)
        _proveedor_save_files(item, request.files.getlist('evidencias'))

        db.session.commit()
        flash("Proveedor actualizado.", "success")
        return redirect(url_for('proveedores_matriz'))

    html = _render_proveedor_form(
        item=item,
        areas=areas,
        paises=paises,
        cfg=cfg,
        is_edit=True
    )
    return render_template_string(BASE, content=Markup(html))


# =========================
# ELIMINAR — Proveedor
# =========================
@app.route('/proveedores/delete')
@login_required
def proveedores_delete():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores")
    ):
        flash("No tiene permiso para eliminar registros de proveedores.", "danger")
        return redirect(url_for('proveedores_matriz'))

    rid = request.args.get('id', type=int)
    it = ProveedorEvaluacion.query.get(rid)
    if it:
        db.session.delete(it)
        db.session.commit()
        flash("Eliminado correctamente.", "success")
    else:
        flash("Registro no encontrado.", "danger")

    return redirect(url_for('proveedores_matriz'))


# =========================
# PARAMETRIZACIÓN — Proveedores
# =========================
@app.route('/proveedores/param', methods=['GET','POST'])
@login_required
def proveedores_param():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar parametrizaciones de proveedores.", "danger")
        return redirect(url_for('proveedores_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores"):
        flash("No tiene permiso para agregar parametrizaciones de proveedores.", "danger")
        return redirect(url_for('proveedores_matriz'))

    cfg = ProveedorEvalConfig.get()

    if request.method == 'POST':
        cfg.min_certificaciones_aprobado = request.form.get('min_certificaciones_aprobado', type=int) or 1
        cfg.pct_aprob_min = request.form.get('pct_aprob_min', type=int) or 81
        cfg.pct_revision_min = request.form.get('pct_revision_min', type=int) or 61

        cfg.crit_muy_baja_max = request.form.get('crit_muy_baja_max', type=int) or 25
        cfg.crit_baja_max = request.form.get('crit_baja_max', type=int) or 50
        cfg.crit_media_max = request.form.get('crit_media_max', type=int) or 75

        cfg.peso_transversal = request.form.get('peso_transversal', type=int) or 0
        cfg.peso_esencial = request.form.get('peso_esencial', type=int) or 0
        cfg.peso_plan_continuidad = request.form.get('peso_plan_continuidad', type=int) or 0
        cfg.peso_plan_recuperacion = request.form.get('peso_plan_recuperacion', type=int) or 0
        cfg.peso_alternativas = request.form.get('peso_alternativas', type=int) or 0
        cfg.peso_impacto_falla = request.form.get('peso_impacto_falla', type=int) or 0
        cfg.peso_plan_migracion = request.form.get('peso_plan_migracion', type=int) or 0
        cfg.peso_info_sensible = request.form.get('peso_info_sensible', type=int) or 0
        cfg.peso_datos_personales = request.form.get('peso_datos_personales', type=int) or 0
        cfg.peso_nube = request.form.get('peso_nube', type=int) or 0
        cfg.peso_sla = request.form.get('peso_sla', type=int) or 0

        db.session.commit()
        flash("Parametrización guardada correctamente.", "success")
        return redirect(url_for('proveedores_matriz'))

    html = """
    <div class="provparam-shell">

      <div class="provparam-header-card">
        <div class="provparam-header-overlay">
          <div class="provparam-header-text">
            <h3 class="provparam-title m-0">Parametrización — Proveedores</h3>
            <div class="provparam-subtitle">
              Configuración de criterios de criticidad, puntuación y umbrales de aprobación
            </div>
          </div>
        </div>
      </div>

      <div class="provparam-header-actions">
        <a href="{{ url_for('proveedores_matriz') }}"
           class="btn rounded-pill px-4 fw-bold provparam-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="provparam-card">
        <div class="provparam-card-body">
          <form method="post">
            <div class="row g-3">

              <div class="col-12"><div class="provparam-section-title">Umbrales de resultado</div></div>

              <div class="col-md-4">
                <label class="form-label">Mínimo certificaciones para 100%</label>
                <input type="number" name="min_certificaciones_aprobado" class="form-control" value="{{ cfg.min_certificaciones_aprobado or 1 }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">% mínimo aprobado</label>
                <input type="number" name="pct_aprob_min" class="form-control" value="{{ cfg.pct_aprob_min or 81 }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">% mínimo en revisión</label>
                <input type="number" name="pct_revision_min" class="form-control" value="{{ cfg.pct_revision_min or 61 }}">
              </div>

              <div class="col-12"><div class="provparam-section-title">Umbrales de criticidad</div></div>

              <div class="col-md-4">
                <label class="form-label">Criticidad muy baja hasta</label>
                <input type="number" name="crit_muy_baja_max" class="form-control" value="{{ cfg.crit_muy_baja_max or 25 }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Criticidad baja hasta</label>
                <input type="number" name="crit_baja_max" class="form-control" value="{{ cfg.crit_baja_max or 50 }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Criticidad media hasta</label>
                <input type="number" name="crit_media_max" class="form-control" value="{{ cfg.crit_media_max or 75 }}">
              </div>

              <div class="col-12"><div class="provparam-section-title">Pesos de criticidad</div></div>

              <div class="col-md-3"><label class="form-label">Peso transversal</label><input type="number" name="peso_transversal" class="form-control" value="{{ cfg.peso_transversal or 0 }}"></div>
              <div class="col-md-3"><label class="form-label">Peso esencial</label><input type="number" name="peso_esencial" class="form-control" value="{{ cfg.peso_esencial or 0 }}"></div>
              <div class="col-md-3"><label class="form-label">Peso plan continuidad</label><input type="number" name="peso_plan_continuidad" class="form-control" value="{{ cfg.peso_plan_continuidad or 0 }}"></div>
              <div class="col-md-3"><label class="form-label">Peso plan recuperación</label><input type="number" name="peso_plan_recuperacion" class="form-control" value="{{ cfg.peso_plan_recuperacion or 0 }}"></div>

              <div class="col-md-3"><label class="form-label">Peso alternativas</label><input type="number" name="peso_alternativas" class="form-control" value="{{ cfg.peso_alternativas or 0 }}"></div>
              <div class="col-md-3"><label class="form-label">Peso impacto falla</label><input type="number" name="peso_impacto_falla" class="form-control" value="{{ cfg.peso_impacto_falla or 0 }}"></div>
              <div class="col-md-3"><label class="form-label">Peso plan migración</label><input type="number" name="peso_plan_migracion" class="form-control" value="{{ cfg.peso_plan_migracion or 0 }}"></div>
              <div class="col-md-3"><label class="form-label">Peso info sensible</label><input type="number" name="peso_info_sensible" class="form-control" value="{{ cfg.peso_info_sensible or 0 }}"></div>

              <div class="col-md-4"><label class="form-label">Peso datos personales</label><input type="number" name="peso_datos_personales" class="form-control" value="{{ cfg.peso_datos_personales or 0 }}"></div>
              <div class="col-md-4"><label class="form-label">Peso nube</label><input type="number" name="peso_nube" class="form-control" value="{{ cfg.peso_nube or 0 }}"></div>
              <div class="col-md-4"><label class="form-label">Peso SLA</label><input type="number" name="peso_sla" class="form-control" value="{{ cfg.peso_sla or 0 }}"></div>

            </div>

            <div class="provparam-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">Guardar parametrización</button>
              <a href="{{ url_for('proveedores_matriz') }}" class="btn rounded-pill px-4 fw-bold provparam-cancel-btn" onclick="showLoader()">Cancelar</a>
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

      .provparam-shell{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }

      .provparam-header-card{
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

      .provparam-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .provparam-header-overlay{
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

      .provparam-header-overlay::before{
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
      }

      .provparam-header-text{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .provparam-header-text::before{
        content:"SGSI · Parámetros de Proveedores";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .provparam-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .provparam-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .provparam-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .provparam-header-actions .btn,
      .provparam-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .provparam-back-btn,
      .provparam-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .provparam-back-btn:hover,
      .provparam-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .provparam-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .provparam-card-body{
        padding:18px;
      }

      .provparam-card .form-label{
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

      .provparam-card .form-control,
      .provparam-card .form-select{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }

      .provparam-card .form-control:focus,
      .provparam-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }

      .provparam-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .provparam-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
        width:100%;
      }

      .btn.rounded-pill{
        border-radius:10px !important;
      }

      @media (max-width:992px){
        .provparam-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .provparam-header-card{
          min-height:88px;
        }

        .provparam-title{
          font-size:1.20rem;
        }

        .provparam-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .provparam-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .provparam-header-overlay::before{
          margin:0;
        }

        .provparam-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .provparam-header-actions .btn,
        .provparam-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, cfg=cfg)
    return render_template_string(BASE, content=Markup(inner))

# ==========================================================================================================================================
#                                                            Fin Módulo Gestión de Proveedores
# ==========================================================================================================================================


# ==========================================================================================================================================
#                                                       Módulo de Métricas
# ==========================================================================================================================================

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



#========================
# Modelos
#========================


class MetricConfigIncidentes(db.Model):
    __tablename__ = "metric_config_incidentes"

    id = db.Column(db.Integer, primary_key=True)
    eta_objetivo = db.Column(db.Float, nullable=True)   # porcentaje (0-100)
    fecha_ultima_actualizacion = db.Column(db.DateTime, default=datetime.utcnow)

    clasificaciones = db.relationship(
        "MetricConfigIncidentesClasificacion",
        backref="config",
        cascade="all, delete-orphan"
    )


class MetricConfigIncidentesClasificacion(db.Model):
    __tablename__ = "metric_config_incidentes_clasificacion"

    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(
        db.Integer,
        db.ForeignKey("metric_config_incidentes.id"),
        nullable=False
    )

    clasificacion = db.Column(db.String(100), nullable=False)  # Ej: Crítico, Alto, Medio
    tmr = db.Column(db.Float, nullable=True)   # Tiempo máx. respuesta
    mtcd = db.Column(db.Float, nullable=True)  # Tiempo MTCD
    mtir = db.Column(db.Float, nullable=True)  # Tiempo MTIR

class MetricasVulnerabilidadesConfig(db.Model):
    # Si NO tienes __tablename__, el nombre de tabla será:
    # "metricas_vulnerabilidades_config"
    # __tablename__ = 'metricas_vulnerabilidades_config'  # opcional

    id = db.Column(db.Integer, primary_key=True)
    meta_anual_activas = db.Column(db.Float, nullable=True)
    creado_por_id = db.Column(db.Integer, nullable=True)

    clasificaciones = db.relationship(
        "MetricasVulnerabilidadesClasificacion",
        back_populates="config",
        cascade="all, delete-orphan"
    )

class MetricasVulnerabilidadesClasificacion(db.Model):
    __tablename__ = 'metricas_vuln_clasificacion'

    id = db.Column(db.Integer, primary_key=True)

    # 🔴 AQUÍ ESTÁ EL PROBLEMA: el string NO coincide con el nombre real de la tabla padre
    # config_id = db.Column(db.Integer, db.ForeignKey('metricas_vuln_config.id'))

    # ✅ AJUSTA EL NOMBRE DEL FOREIGN KEY
    config_id = db.Column(
        db.Integer,
        db.ForeignKey('metricas_vulnerabilidades_config.id'),  # <-- usa el nombre REAL de la tabla padre
        nullable=False
    )

    clasificacion = db.Column(db.String(50), nullable=False)
    cantidad_aceptada = db.Column(db.Integer, nullable=True)
    porcentaje_cumplimiento = db.Column(db.Float, nullable=True)
    tiempo_max_cierre_dias = db.Column(db.Integer, nullable=True)

    config = db.relationship("MetricasVulnerabilidadesConfig", back_populates="clasificaciones")
    

class MetricasVulnerabilidadesNivel(db.Model):
    __tablename__ = "metricas_vulnerabilidades_nivel"

    id = db.Column(db.Integer, primary_key=True)

    config_id = db.Column(
        db.Integer,
        db.ForeignKey("metricas_vulnerabilidades_config.id"),
        nullable=False
    )

    # Clasificación definida por el usuario (Crítico, Alto, Medio, Bajo, etc.)
    clasificacion = db.Column(db.String(100), nullable=False)

    # Cantidad aceptada de vulnerabilidades activas (mensual/anual) según su clasificación
    cantidad_aceptada = db.Column(db.Integer, nullable=True)

    # Distribución del % de cumplimiento de vulnerabilidades según su clasificación
    porcentaje_cumplimiento = db.Column(db.Float, nullable=True)


class MetricasCulturaConfig(db.Model):
    __tablename__ = "metricas_cultura_config"

    id = db.Column(db.Integer, primary_key=True)

    # META U OBJETIVO GENERAL (%)
    meta_general = db.Column(db.Float, nullable=True)

    # INDICADOR META INDIVIDUAL DE EFECTIVIDAD EN LA FORMACION INICIAL (FI) (%)
    meta_fi = db.Column(db.Float, nullable=True)

    # INDICADOR META INDIVIDUAL EJECUCION DE LA PLANEACION (EP) (%)
    meta_ep = db.Column(db.Float, nullable=True)

    fecha_actualizacion = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

class MetricasCultura(db.Model):
    __tablename__ = "metricas_cultura"

    id = db.Column(db.Integer, primary_key=True)

    anio = db.Column(db.Integer, nullable=False)
    mes  = db.Column(db.Integer, nullable=False)  # 1–12

    # Datos base
    personas_contratadas = db.Column(db.Integer, nullable=False)
    formacion_inicial_aprobada = db.Column(db.Integer, nullable=False)
    personas_reinduccion = db.Column(db.Integer, nullable=False)
    reinduccion_aprobada = db.Column(db.Integer, nullable=False)

    # Metas calculadas (porcentaje 0–100)
    meta_formacion = db.Column(db.Float)             # META ALCANZADA DE FORMACIÓN
    actividades_planeadas = db.Column(db.Integer, nullable=False)
    actividades_ejecutadas = db.Column(db.Integer, nullable=False)
    meta_actividades = db.Column(db.Float)           # META ALCANZADA DE ACTIVIDADES
    resultado_meta_general = db.Column(db.Float)     # RESULTADO DE LA META U OBJETIVO GENERAL

    # Análisis textual (AI + edición manual)
    analisis_mensual = db.Column(db.Text)

    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("anio", "mes", name="uq_metricas_cultura_anio_mes"),
    )

class MetricaIncidente(db.Model):
    __tablename__ = "metricas_incidentes"

    id = db.Column(db.Integer, primary_key=True)

    # Referencia al incidente original (tabla registro_incidentes)
    incidente_id = db.Column(db.Integer, nullable=False)

    # Datos básicos
    fecha_registro = db.Column(db.DateTime, nullable=False)  # Fecha y hora de la alerta
    descripcion_incidente = db.Column(db.Text, nullable=False)
    cargo_responsable = db.Column(db.String(255), nullable=True)
    clasificacion = db.Column(db.String(120), nullable=True)

    # Bloque CONTENCIÓN (MTDC)
    requiere_contencion = db.Column(db.Boolean, default=False)
    descripcion_mtcd = db.Column(db.Text, nullable=True)
    fecha_fin_mtcd = db.Column(db.DateTime, nullable=True)
    tiempo_mtcd_horas = db.Column(db.Float, nullable=True)
    cumplimiento_mtcd = db.Column(db.Float, nullable=True)  # %

    # Bloque RECUPERACIÓN (MTIR)
    requiere_recuperacion = db.Column(db.Boolean, default=False)
    descripcion_mtir = db.Column(db.Text, nullable=True)
    fecha_mtir = db.Column(db.DateTime, nullable=True)
    tiempo_mtir_horas = db.Column(db.Float, nullable=True)
    cumplimiento_mtir = db.Column(db.Float, nullable=True)  # %

    # Cumplimiento global
    cumplimiento_global = db.Column(db.Float, nullable=True)  # %

    # Análisis IA / manual por incidente
    analisis = db.Column(db.Text, nullable=True)

    creado_en = db.Column(db.DateTime, default=datetime.utcnow)


#========================
# Helper
#========================

# =============================
# Constantes globales INCIDENCIAS
# =============================

INCIDENTE_CLASIFICACIONES = ['Crítico', 'Alto', 'Medio', 'Bajo']

# ===========================
# Helpers de configuración de incidentes
# ===========================


def normalizar_texto(s):
    return s.strip().lower() if s else None

def get_config_incidentes_map():
    """
    Devuelve:
      clasif_nombres = ['Crítico', 'Alto', ...]
      tiempos_por_clas = {
        'crítico':  {'tmr': 4, 'mtcd': 1, 'mtir': 3},
        'alto':     {...},
        ...
      }
    """
    config = MetricConfigIncidentes.query.first()
    clasif_nombres = []
    tiempos_por_clas = {}

    # Si no hay configuración aún, devolvemos listas/diccionarios vacíos
    if not config:
        return clasif_nombres, tiempos_por_clas

    for fila in config.clasificaciones:
        nombre = (fila.clasificacion or "").strip()
        if not nombre:
            continue

        # Lista "bonita" para los combos/selects
        clasif_nombres.append(nombre)

        # Mapa normalizado para cálculos (keys en minúsculas)
        key = normalizar_texto(nombre)
        tiempos_por_clas[key] = {
            "tmr":  fila.tmr,
            "mtcd": fila.mtcd,
            "mtir": fila.mtir,
        }

    return clasif_nombres, tiempos_por_clas

# ===========================
# Vista métrica construida desde registro_incidentes
# ===========================

class IncidenteMetricaView:
    """
    Objeto ligero para que la plantilla de la matriz de métricas funcione
    igual que antes, pero tomando datos desde registro_incidentes.
    """
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def parse_dt_maybe(value: str):
    """
    Intenta parsear 'YYYY-MM-DD HH:MM' o 'YYYY-MM-DDTHH:MM'.
    Devuelve datetime o None si no se puede.
    """
    if not value:
        return None

    from datetime import datetime
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def construir_metrica_desde_incidente_row(row, tiempos_por_clas: dict) -> IncidenteMetricaView:
    """
    Recibe una fila de sqlite3.Row de la tabla registro_incidentes
    y la convierte en un IncidenteMetricaView con campos compatibles
    con la plantilla de la Matriz de Métricas.
    """

    # Campos básicos
    id_reg        = row["id"]
    fecha_alerta  = row["fecha_alerta"]
    desc_alerta   = row["descripcion_alerta"]
    clasif        = row["clasificacion_incidente"] or "Sin clasificación"

    se_req_cont   = (row["se_requiere_contencion"] or "No") == "Si"
    se_req_rec    = (row["se_requiere_recuperacion"] or "No") == "Si"

    fh_cont_raw   = row["fecha_hora_contencion"]
    fh_rec_raw    = row["fecha_hora_recuperacion"]

    dt_reg        = parse_dt_maybe(fecha_alerta)
    dt_cont       = parse_dt_maybe(fh_cont_raw)
    dt_rec        = parse_dt_maybe(fh_rec_raw)

    # ==========================
    # Cálculo de tiempos en horas
    # ==========================
    tiempo_mtcd_horas = None
    if se_req_cont and dt_reg and dt_cont:
        delta = dt_cont - dt_reg
        tiempo_mtcd_horas = max(0.0, delta.total_seconds() / 3600.0)

    # MTIR: depende de si hubo contención previa o no
    tiempo_mtir_horas = None
    if se_req_rec and dt_rec:
        if se_req_cont and dt_cont:
            base = dt_cont
        else:
            base = dt_reg
        if base:
            delta = dt_rec - base
            tiempo_mtir_horas = max(0.0, delta.total_seconds() / 3600.0)

    # ==========================
    # Buscar objetivos en la config (TMR, MTCD, MTIR)
    # ==========================
    key = normalizar_texto(clasif)
    cfg = tiempos_por_clas.get(key, {})
    tmr_obj  = cfg.get("tmr")   # Tiempo máximo total (TMR)
    mtcd_obj = cfg.get("mtcd")  # Tiempo respuesta MTCD
    mtir_obj = cfg.get("mtir")  # Tiempo máximo MTIR cuando hay MTCD

    # ==========================
    # Cumplimiento MTCD
    # ==========================
    cumplimiento_mtcd = None
    if se_req_cont and tiempo_mtcd_horas is not None and mtcd_obj is not None:
        if tiempo_mtcd_horas <= mtcd_obj:
            cumplimiento_mtcd = 100.0
        else:
            exceso = tiempo_mtcd_horas - mtcd_obj
            # % de cumplimiento aproximado (100% menos el porcentaje de exceso)
            cumplimiento_mtcd = max(0.0, 100.0 - (exceso / mtcd_obj) * 100.0)

    # ==========================
    # Cumplimiento MTIR
    # Lógica:
    #  - Si hubo MTCD: se compara contra MTIR
    #  - Si NO hubo MTCD: se compara contra TMR
    # ==========================
    cumplimiento_mtir = None
    if se_req_rec and tiempo_mtir_horas is not None:
        if se_req_cont and mtir_obj is not None:
            objetivo = mtir_obj
        else:
            objetivo = tmr_obj

        if objetivo is not None:
            if tiempo_mtir_horas <= objetivo:
                cumplimiento_mtir = 100.0
            else:
                exceso = tiempo_mtir_horas - objetivo
                cumplimiento_mtir = max(0.0, 100.0 - (exceso / objetivo) * 100.0)

    # ==========================
    # Cumplimiento global (promedio de los que existan)
    # ==========================
    valores = []
    if cumplimiento_mtcd is not None:
        valores.append(cumplimiento_mtcd)
    if cumplimiento_mtir is not None:
        valores.append(cumplimiento_mtir)

    cumplimiento_global = None
    if valores:
        cumplimiento_global = sum(valores) / len(valores)

    # De momento no generamos análisis automático (puedes luego
    # llamar a analizar_metrica_incidente_ia si quieres)
    analisis = None

    return IncidenteMetricaView(
        id=id_reg,                          # ✅ id BD (registro_incidentes.id) -> entero
        id_incidente=row["id_incidente"],   # ✅ id de negocio (INC-2025-001)
        fecha_registro=dt_reg,              # ✅ datetime desde fecha_alerta
        descripcion_incidente=desc_alerta or "",  # ✅ NUNCA None
        cargo_responsable=row["cargo_responsable"],

        clasificacion_incidente=clasif,     # si tu UI lo usa
        clasificacion=clasif,               # ✅ para guardar en MetricaIncidente

        requiere_contencion=se_req_cont,
        tiempo_mtcd_horas=tiempo_mtcd_horas,
        cumplimiento_mtcd=cumplimiento_mtcd,

        requiere_recuperacion=se_req_rec,
        tiempo_mtir_horas=tiempo_mtir_horas,
        cumplimiento_mtir=cumplimiento_mtir,

        cumplimiento_global=cumplimiento_global,
        analisis=None,
    )

    config = MetricConfigIncidentes.query.first()
    clasif_nombres = []
    tiempos_por_clas = {}

    if not config:
        return clasif_nombres, tiempos_por_clas

    for fila in config.clasificaciones:
        nombre = (fila.clasificacion or "").strip()
        if not nombre:
            continue
        clasif_nombres.append(nombre)

        key = normalizar_texto(nombre)
        tiempos_por_clas[key] = {
            "tmr": fila.tmr,
            "mtcd": fila.mtcd,
            "mtir": fila.mtir,
        }

    return clasif_nombres, tiempos_por_clas

def calcular_icv_vulnerabilidades(config, detalles, fecha_inicio, fecha_fin):
    """
    Calcula el Índice de Cumplimiento en Vulnerabilidades (ICV) para el periodo.
    Devuelve: (icv_global, filas_detalle)
    filas_detalle = [
      {
        "clasificacion": ...,
        "aceptada": ...,
        "real": ...,
        "cumplimiento": ...,
        "peso": ...,
        "aporte": ...
      },
      ...
    ]
    """
    if not config or not detalles:
        return None, []

    icv_global = 0.0
    filas = []

    for det in detalles:
        aceptada = det.cantidad_aceptada or 0
        peso = det.peso_pct or 0.0

        # Conteo de vulnerabilidades ACTIVAS en el periodo, por clasificación
        real = (
            Vulnerabilidad.query
            .filter(
                Vulnerabilidad.clasificacion == det.clasificacion,
                Vulnerabilidad.estado == "Activa",
                Vulnerabilidad.fecha_registro >= fecha_inicio,
                Vulnerabilidad.fecha_registro < fecha_fin,
            )
            .count()
        )

        # Cálculo de cumplimiento por clasificación
        if real == 0:
            cumplimiento = 100.0
        elif aceptada <= 0:
            # No se aceptan vulnerabilidades de esta clase
            cumplimiento = 0.0 if real > 0 else 100.0
        elif real <= aceptada:
            cumplimiento = 100.0
        else:
            cumplimiento = (aceptada / real) * 100.0

        cumplimiento = round(cumplimiento, 2)

        # Aporte ponderado al índice global
        aporte = round(cumplimiento * (peso / 100.0), 2)
        icv_global += aporte

        filas.append({
            "clasificacion": det.clasificacion,
            "aceptada": aceptada,
            "real": real,
            "cumplimiento": cumplimiento,
            "peso": peso,
            "aporte": aporte,
        })

    icv_global = round(icv_global, 2)
    return icv_global, filas

def normalizar_clasificacion(texto):
    if not texto:
        return None
    return texto.strip().lower()

def analizar_metricas_vuln_ia(datos_metricas: dict) -> str:
    prompt = f"""
Eres un analista experto en gestión de vulnerabilidades y SLAs.

Con base en estos datos (JSON), redacta un análisis ejecutivo en español.
- No inventes cifras.
- Incluye hallazgos, riesgos, y 5 acciones concretas priorizadas.
- Si no hay datos suficientes, dilo claramente.

DATOS (JSON):
{json.dumps(datos_metricas, ensure_ascii=False, indent=2)}
"""
    return chat_ai(prompt, model="openai/gpt-4o-mini").strip()


def analizar_vulnerabilidad_por_codigo_ia(vuln, sla_dias, dias_abierta):
    prompt = f"""
Eres un analista senior de ciberseguridad.
Debes redactar un análisis ejecutivo y accionable de una vulnerabilidad ABIERTA fuera de SLA.

Datos:
- Código: {vuln.codigo}
- Clasificación: {vuln.clasificacion or 'Sin clasificar'}
- Responsable: {vuln.responsable or 'Sin responsable'}
- Fecha identificación: {vuln.fecha_identificacion}
- Días abierta: {dias_abierta}
- SLA (días): {sla_dias}

Instrucciones:
- Escribe en español.
- Máximo 10-12 líneas.
- Incluye: impacto probable, riesgo de negocio, urgencia, y 3 acciones concretas verificables.
- NO inventes datos técnicos si no están.
- Si faltan datos, dilo y sugiere qué evidencia pedir.
"""

    return (chat_ai(prompt, model="openai/gpt-4o-mini") or "").strip()


def analizar_vulnerabilidad_cerrada_fuera_sla_ia(vuln, sla_dias, dias_cierre, cierre_eff):
    prompt = f"""
Eres un analista senior de ciberseguridad.
Debes redactar un análisis post-mortem de una vulnerabilidad CERRADA fuera de SLA.

Datos:
- Código: {vuln.codigo}
- Clasificación: {vuln.clasificacion or 'Sin clasificar'}
- Responsable: {vuln.responsable or 'Sin responsable'}
- Fecha identificación: {vuln.fecha_identificacion}
- Fecha cierre: {cierre_eff}
- Días cierre: {dias_cierre}
- SLA (días): {sla_dias}

Instrucciones:
- Escribe en español.
- Máximo 10-12 líneas.
- Explica el incumplimiento de SLA en términos de proceso (sin inventar causas).
- Propón 3 mejoras concretas del proceso (ej.: triage, dueños, ventanas, seguimiento).
- NO inventes datos.
"""

    return (chat_ai(prompt, model="openai/gpt-4o-mini") or "").strip()


def analizar_vulnerabilidad_cerrada_fuera_sla_ia(vuln, sla_dias, dias_cierre, cierre_eff) -> str:
    prompt = f"""
Eres un auditor de seguridad.

Analiza una vulnerabilidad CERRADA fuera de SLA y redacta:
1) Resumen del incumplimiento
2) Posibles causas (solo si se infieren razonablemente)
3) Lecciones aprendidas
4) Acciones preventivas para evitar repetición (mínimo 5)
5) Indicadores/controles recomendados

NO inventes fechas ni información.

Datos:
- Código: {vuln.codigo}
- Estado: {vuln.estado}
- Clasificación: {vuln.clasificacion}
- Responsable: {vuln.responsable}
- Fecha identificación: {vuln.fecha_identificacion}
- Fecha cierre efectiva: {cierre_eff}
- Días de cierre: {dias_cierre}
- SLA días: {sla_dias}
"""
    return chat_ai(prompt, model="openai/gpt-4o-mini").strip()


def cargar_incidente_por_id(incidente_id: int):
    init_incidentes_db()
    conn = get_incidentes_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM registro_incidentes WHERE id = ?", (incidente_id,))
    row = c.fetchone()
    conn.close()
    return row

def listar_incidentes_metricas():
    init_incidentes_db()
    conn = get_incidentes_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT *
        FROM registro_incidentes
        ORDER BY id DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def listar_incidentes_metricas_filtrados(
    nombre_alerta: str = "",
    clasificacion_incidente: str = "",
    prioridad: str = "",
    estado: str = ""
):
    init_incidentes_db()
    conn = get_incidentes_db_connection()
    c = conn.cursor()

    query = """
        SELECT *
        FROM registro_incidentes
        WHERE 1=1
    """
    params = []

    if (nombre_alerta or "").strip():
        query += " AND nombre_alerta LIKE ?"
        params.append(f"%{nombre_alerta.strip()}%")

    if (clasificacion_incidente or "").strip():
        query += " AND clasificacion_incidente = ?"
        params.append(clasificacion_incidente.strip())

    if (prioridad or "").strip():
        query += " AND prioridad = ?"
        params.append(prioridad.strip())

    if (estado or "").strip():
        query += " AND estado = ?"
        params.append(estado.strip())

    query += " ORDER BY id DESC"

    c.execute(query, tuple(params))
    rows = c.fetchall()
    conn.close()
    return rows




def analizar_metrica_incidente_ia(metrica: "MetricaIncidente", eta_objetivo: float | None = None) -> str:
    """
    Genera un análisis breve del resultado de la métrica de un incidente específico,
    comparando, cuando exista, contra el ETA u objetivo global configurado.
    """
    clasif = metrica.clasificacion or "Sin clasificación"
    req_cont = "Sí" if metrica.requiere_contencion else "No"
    req_rec = "Sí" if metrica.requiere_recuperacion else "No"

    objetivo_txt = f"{eta_objetivo:.2f} %" if eta_objetivo is not None else "no definido"

    prompt = f"""
Eres un analista de respuesta a incidentes de seguridad de la información.

Analiza la siguiente métrica de un incidente individual:

- ID del incidente: {metrica.incidente_id}
- Clasificación del incidente: {clasif}
- Fecha y hora de registro del incidente: {metrica.fecha_registro}
- Se requirió contención (MTDC): {req_cont}
- Tiempo ejecutado en la eficacia de la MTDC (horas): {metrica.tiempo_mtcd_horas}
- Cumplimiento meta final de la CONTENCIÓN (%): {metrica.cumplimiento_mtcd}
- Se requirió recuperación (MTIR): {req_rec}
- Tiempo ejecutado en la eficacia de la MTIR (horas): {metrica.tiempo_mtir_horas}
- Cumplimiento meta final de la RECUPERACIÓN (%): {metrica.cumplimiento_mtir}
- Cumplimiento global de la métrica (%): {metrica.cumplimiento_global}
- Objetivo global ETA u objetivo mensual de respuesta y solución de incidentes (%): {objetivo_txt}

Instrucciones:
1. Compara explícitamente el cumplimiento global de la métrica frente al objetivo ETA cuando esté definido.
2. Describe si el incidente se gestionó por encima, dentro o por debajo de lo esperado.
3. Comenta brevemente el rol de la contención y la recuperación en el resultado global.
4. Incluye 1–2 recomendaciones concretas para mejorar incidentes similares en el futuro.

Responde en ESPAÑOL, en un máximo de 8 líneas, en texto corrido, sin viñetas ni títulos.
    """.strip()

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        # 👇 AQUÍ ESTÁ EL PUNTO CLAVE:
        # NADA de ["content"], solo .message.content
        texto = resp.choices[0].message.content if resp.choices else ""
        if not texto:
            texto = "No se pudo generar automáticamente el análisis de la métrica. Por favor, complétalo manualmente."
        return texto.strip()

    except Exception as e:
        print("Error IA en analizar_metrica_incidente_ia:", e)
        return "No se pudo generar automáticamente el análisis de la métrica. Por favor, complétalo manualmente."

def analizar_vulnerabilidad_por_codigo_ia(vuln, sla_dias: int | None, dias_abierta: int) -> str:
    """
    Genera análisis por código de vulnerabilidad (vencida).
    vuln: objeto VulnerabilidadRegistro
    """
    cls = vuln.clasificacion or "Sin clasificar"
    resp = vuln.responsable or "No asignado"
    fecha_id = vuln.fecha_identificacion.strftime("%Y-%m-%d") if vuln.fecha_identificacion else "No definida"
    sla_txt = f"{sla_dias} días" if sla_dias is not None else "No definido"

    prompt = f"""
Eres un analista de gestión de vulnerabilidades.

Genera un análisis ejecutivo para una vulnerabilidad vencida (fuera de SLA):

Código: {vuln.codigo}
Clasificación: {cls}
Responsable: {resp}
Fecha identificación: {fecha_id}
Días abierta: {dias_abierta}
SLA configurado: {sla_txt}

Instrucciones:
1) Explica por qué está fuera de SLA y el riesgo operativo.
2) Indica 2–3 acciones concretas (plan de acción) para remediarla o mitigarla.
3) Tono profesional. Máximo 8–10 líneas. Sin viñetas ni títulos.
""".strip()

    resp_ai = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    texto = resp_ai.choices[0].message.content or ""
    return texto.strip()


#=================================
# Configuración de Riesgos
#=================================

@app.route('/metricas/configuracion/riesgos', methods=["GET", "POST"])
@login_required
def config_param_riesgos():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede configurar parámetros.", "danger")
        return redirect(url_for('menu'))

    if user.role != 'admin' and not verificar_permiso(user, "Métricas"):
        flash("No tiene permiso para configurar parámetros.", "danger")
        return redirect(url_for('menu'))

    # Cargar registro único (1 fila)
    cfg = MetricConfigRiesgos.query.first()
    if not cfg:
        cfg = MetricConfigRiesgos(
            apetito_residual_definido="",
            tendencia_tiempo="mensual"
        )
        db.session.add(cfg)
        db.session.commit()

    opciones = [
        ("mensual", "Mensual"),
        ("trimestral", "Trimestral"),
        ("cuatrimestral", "Cuatrimestral"),
        ("semestral", "Semestral"),
        ("anual", "Anual"),
    ]

    if request.method == "POST":
        apetito = (request.form.get("apetito_residual_definido") or "").strip()
        if not apetito or len(apetito) > 255:
            flash("El apetito de riesgo residual debe ser alfanumérico y máximo 255 caracteres.", "danger")
            return redirect(url_for("config_param_riesgos"))

        cfg.apetito_residual_definido = apetito
        tendencia = (request.form.get("tendencia_tiempo") or "mensual").strip().lower()

        permitidos = {k for k, _ in opciones}
        if tendencia not in permitidos:
            tendencia = "mensual"

        cfg.apetito_residual_definido = apetito
        cfg.tendencia_tiempo = tendencia
        db.session.commit()

        flash("Parámetros de riesgos guardados correctamente.", "success")
        return redirect(url_for("config_param_riesgos"))

    content = render_template_string("""
    <div class="riskcfg-shell">

      <!-- CABECERA -->
      <div class="riskcfg-header-card">
        <div class="riskcfg-header-overlay">
          <div class="riskcfg-header-text">
            <h3 class="riskcfg-title m-0">Parámetros de Riesgos</h3>
            <div class="riskcfg-subtitle">
              Configura el apetito de riesgo residual definido por la organización
              y la periodicidad de análisis de la tendencia en el tiempo.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="riskcfg-header-actions">

      </div>

      <!-- TARJETA -->
      <div class="riskcfg-card p-4">

        <div class="riskcfg-section-title">
          Configuración de parámetros
        </div>

        <form method="POST">

          <div class="mb-3">
            <label class="form-label fw-semibold">
              Apetito de riesgo residual (Definido)
            </label>

            <input
              type="text"
              name="apetito_residual_definido"
              class="form-control"
              maxlength="255"
              value="{{ cfg.apetito_residual_definido }}"
              placeholder="Ej: Bajo | Moderado | Alto | Nivel 3 | Residual <= 6"
              required
            >

            <div class="form-text">
              Valor alfanumérico definido por la organización para aceptación del riesgo residual.
            </div>
          </div>

          <div class="mb-3">
            <label class="form-label fw-semibold">
              Tendencia en el tiempo
            </label>

            <select name="tendencia_tiempo" class="form-select">
              {% for val, label in opciones %}
                <option value="{{ val }}" {% if (cfg.tendencia_tiempo or 'mensual') == val %}selected{% endif %}>
                  {{ label }}
                </option>
              {% endfor %}
            </select>

            <div class="form-text">
              Define la periodicidad con la que se mostrará y analizará la tendencia del riesgo.
            </div>
          </div>

          <div class="text-center mt-4">
            <button type="submit" class="btn btn-primary rounded-pill px-4 fw-semibold">
              💾 Guardar parámetros
            </button>
          </div>

        </form>

      </div>

    </div>

   <style>
      body {
        background-image: url('/static/img/ccsgsi.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
      }

      .riskcfg-shell {
        width: 96%;
        max-width: 1200px;
        margin: 26px auto 24px auto;
        overflow: hidden;
      }

      .riskcfg-header-card {
        background: linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius: 18px;
        padding: 16px 24px;
        min-height: 94px;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        box-shadow: 0 12px 24px rgba(15,23,42,.25);
        position: relative;
        overflow: hidden;
        margin-bottom: 14px;
      }

      .riskcfg-header-card::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .riskcfg-header-overlay {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        text-align: left;
        position: relative;
        z-index: 1;
        min-width: 0;
      }

      .riskcfg-header-overlay::before {
        content: "📉";
        width: 54px;
        height: 54px;
        min-width: 54px;
        border-radius: 14px;
        background: #ffffff;
        color: #0b4a8f;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.4rem;
        box-shadow: 0 8px 18px rgba(0,0,0,.25);
        margin-right: 14px;
      }

      .riskcfg-header-text {
        max-width: 1000px;
        min-width: 0;
      }

      .riskcfg-header-text::before {
        content: "SGSI · Configuración de Riesgos";
        display: inline-block;
        background: rgba(255,255,255,.18);
        border-radius: 999px;
        padding: 3px 10px;
        font-size: .65rem;
        font-weight: 800;
        margin-bottom: 4px;
        color: #ffffff;
      }

      .riskcfg-title {
        color: #ffffff !important;
        font-weight: 950;
        font-size: 1.32rem;
        line-height: 1.1;
        margin: 0 !important;
        text-shadow: 0 4px 14px rgba(0,0,0,.45);
        overflow-wrap: break-word;
      }

      .riskcfg-subtitle {
        color: rgba(255,255,255,.95);
        font-size: .78rem;
        line-height: 1.25;
        margin-top: 3px;
        overflow-wrap: break-word;
      }

      .riskcfg-header-actions {
        display: flex;
        justify-content: center;
        gap: 10px;
        flex-wrap: wrap;
        margin: 10px 0 14px;
      }

      .btn {
        border-radius: 10px !important;
        font-weight: 900;
        box-shadow: 0 4px 10px rgba(0,0,0,.08);
      }

      .riskcfg-btn-main {
        background: #ffffff;
        color: #0f172a;
        border: 1px solid #cfd8e3;
      }

      .riskcfg-btn-main:hover {
        background: #edf5ff;
        color: #0b65d8;
      }

      .riskcfg-card {
        background: rgba(255,255,255,.96) !important;
        border-radius: 18px;
        backdrop-filter: blur(8px);
        box-shadow: 0 12px 24px rgba(15,23,42,.18);
        border: 1px solid rgba(219,230,244,.9);
        overflow: hidden;
        width: 100%;
        max-width: 100%;
      }

      .riskcfg-card-body,
      .riskcfg-card .card-body {
        padding: 22px;
      }

      .riskcfg-section-title {
        font-weight: 950;
        font-size: .95rem;
        color: #0b4a8f;
        margin-bottom: 16px;
        border-bottom: 2px solid rgba(59,130,246,.18);
        padding-bottom: 8px;
        overflow-wrap: break-word;
      }

      .form-control,
      .form-select {
        border-radius: 10px;
        border: 1px solid #d9e3f0;
        min-height: 40px;
        font-size: .86rem;
        background: #f8fafc;
      }

      .form-control:focus,
      .form-select:focus {
        border-color: #3f86d6;
        box-shadow: 0 0 0 .15rem rgba(63,134,214,.18);
        background: #ffffff;
      }

      h3 {
        color: #ffffff;
        margin: 0;
      }

      @media (max-width: 992px) {
        .riskcfg-shell {
          width: 98%;
          margin: 8px auto 22px auto;
        }

        .riskcfg-title {
          font-size: 1.20rem;
        }

        .riskcfg-subtitle {
          font-size: .76rem;
        }

        .riskcfg-card-body,
        .riskcfg-card .card-body {
          padding: 16px;
        }
      }

      @media (max-width: 768px) {
        .riskcfg-header-overlay {
          flex-direction: column;
          text-align: center;
          gap: 10px;
        }

        .riskcfg-header-overlay::before {
          margin: 0;
        }

        .riskcfg-title,
        .riskcfg-subtitle {
          text-align: center;
        }

        .riskcfg-header-actions .btn {
          width: 100%;
        }
      }
    </style>
    """, cfg=cfg, opciones=opciones)

    return render_template_string(BASE, content=content)

#=================================
# Configuración de Incidentes
#=================================

@app.route('/metricas/configuracion/incidentes', methods=['GET', 'POST'])
@login_required
def config_param_incidentes():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('menu'))

    if user.role != 'admin' and not verificar_permiso(user, "Métricas"):
        flash("No tiene permiso para configurar incidentes.", "danger")
        return redirect(url_for('menu'))
    # 🔹 Siempre trabajaremos con UNA sola configuración global
    config = MetricConfigIncidentes.query.first()

    if request.method == 'POST':
        eta_objetivo = request.form.get('eta_objetivo')
        clasificaciones = request.form.getlist('clasificacion[]')
        tmr_list = request.form.getlist('tmr[]')
        mtcd_list = request.form.getlist('mtcd[]')
        mtir_list = request.form.getlist('mtir[]')

        # Si no existe config, la creamos
        if not config:
            config = MetricConfigIncidentes()
            db.session.add(config)

        # Guardar ETA objetivo
        try:
            config.eta_objetivo = float(eta_objetivo) if eta_objetivo else None
        except ValueError:
            config.eta_objetivo = None

        config.fecha_ultima_actualizacion = datetime.utcnow()

        # 🔹 Limpiamos clasificaciones anteriores y guardamos las nuevas
        config.clasificaciones.clear()

        for clasif, tmr, mtcd, mtir in zip(clasificaciones, tmr_list, mtcd_list, mtir_list):
            # Ignorar filas totalmente vacías
            if not (clasif or tmr or mtcd or mtir):
                continue

            fila = MetricConfigIncidentesClasificacion(
                config=config,
                clasificacion=(clasif or "").strip() or "Sin nombre",
            )

            # Convertimos a float si viene algo
            fila.tmr = float(tmr) if (tmr or "").strip() else None
            fila.mtcd = float(mtcd) if (mtcd or "").strip() else None
            fila.mtir = float(mtir) if (mtir or "").strip() else None

            db.session.add(fila)

        db.session.commit()
        flash("Parámetros de incidentes guardados correctamente.", "success")
        return redirect(url_for('config_param_incidentes'))

    # 🔹 GET → cargar valores guardados (si existen)
    eta_valor = config.eta_objetivo if config else None
    clasificaciones_guardadas = config.clasificaciones if config else []

    content = render_template_string("""
    <div class="incparam-shell">

      <!-- CABECERA -->
      <div class="incparam-header-card">
        <div class="incparam-header-overlay">
          <div class="incparam-header-text">
            <h3 class="incparam-title m-0">Parámetros de Incidentes</h3>
            <div class="incparam-subtitle">
              Configura el objetivo mensual (ETA) y los tiempos máximos de respuesta
              y recuperación de incidentes según su clasificación.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="incparam-header-actions">
        
      </div>

      <!-- TARJETA PRINCIPAL -->
      <div class="incparam-card p-4">

        <div class="incparam-section-title">
          Configuración de tiempos y objetivos
        </div>

        <form method="POST">

          <!-- ETA -->
          <div class="mb-3">
            <label for="eta_objetivo" class="form-label fw-semibold">
              ETA u objetivo mensual de respuesta y solución de incidentes (%)
            </label>

            <div class="input-group">
              <input type="number"
                     step="0.01"
                     min="0"
                     max="100"
                     class="form-control"
                     id="eta_objetivo"
                     name="eta_objetivo"
                     value="{{ eta_valor if eta_valor is not none else '' }}"
                     placeholder="Ej: 95">
              <span class="input-group-text">%</span>
            </div>

            <div class="form-text">
              Porcentaje de incidentes que se espera responder y solucionar dentro de los tiempos definidos.
            </div>
          </div>

          <hr>

          <!-- TABLA -->
          <h5 class="mb-3 fw-bold">
            Tiempo máximo de recuperación de incidentes en horas según clasificación
          </h5>

          <div class="table-responsive incparam-table-wrap">

            <table class="table table-sm align-middle mb-0" id="tabla-clasificaciones">

              <thead class="incparam-table-head">
                <tr>
                  <th style="min-width:140px;">Clasificación</th>
                  <th style="min-width:160px;">Tiempo máximo de respuesta (TMR)</th>
                  <th style="min-width:200px;">Tiempo MTCD dentro del TMR</th>
                  <th style="min-width:220px;">
                    Tiempo máximo de recuperación (MTIR)
                    <br>
                    <small class="text-muted">
                    Si no es requerido MTCD el tiempo será el definido en el TMR.
                    </small>
                  </th>
                  <th class="text-center" style="width:80px;">Acciones</th>
                </tr>
              </thead>

              <tbody id="body-clasificaciones">

              {% if clasificaciones_guardadas %}

                {% for fila in clasificaciones_guardadas %}
                <tr>

                  <td>
                    <select name="clasificacion[]" class="form-select">
                      <option value="">-- Seleccione --</option>
                      {% for op in clasif_choices %}
                        <option value="{{ op }}"
                          {% if fila.clasificacion == op %}selected{% endif %}>
                          {{ op }}
                        </option>
                      {% endfor %}
                    </select>
                  </td>

                  <td>
                    <input type="number"
                           step="0.01"
                           min="0"
                           name="tmr[]"
                           class="form-control"
                           value="{{ fila.tmr if fila.tmr is not none else '' }}">
                  </td>

                  <td>
                    <input type="number"
                           step="0.01"
                           min="0"
                           name="mtcd[]"
                           class="form-control"
                           value="{{ fila.mtcd if fila.mtcd is not none else '' }}">
                  </td>

                  <td>
                    <input type="number"
                           step="0.01"
                           min="0"
                           name="mtir[]"
                           class="form-control"
                           value="{{ fila.mtir if fila.mtir is not none else '' }}">
                  </td>

                  <td class="text-center">
                    <button type="button"
                            class="btn btn-outline-danger btn-sm"
                            onclick="eliminarFila(this)">
                      🗑️
                    </button>
                  </td>

                </tr>
                {% endfor %}

              {% else %}

                {% for op in clasif_choices %}
                <tr>

                  <td>
                    <select name="clasificacion[]" class="form-select">
                      <option value="">-- Seleccione --</option>
                      {% for opcion in clasif_choices %}
                        <option value="{{ opcion }}"
                          {% if opcion == op %}selected{% endif %}>
                          {{ opcion }}
                        </option>
                      {% endfor %}
                    </select>
                  </td>

                  <td>
                    <input type="number" step="0.01" min="0"
                           name="tmr[]" class="form-control"
                           placeholder="Horas">
                  </td>

                  <td>
                    <input type="number" step="0.01" min="0"
                           name="mtcd[]" class="form-control"
                           placeholder="Horas">
                  </td>

                  <td>
                    <input type="number" step="0.01" min="0"
                           name="mtir[]" class="form-control"
                           placeholder="Horas">
                  </td>

                  <td class="text-center">
                    <button type="button"
                            class="btn btn-outline-danger btn-sm"
                            onclick="eliminarFila(this)">
                      🗑️
                    </button>
                  </td>

                </tr>
                {% endfor %}

              {% endif %}

              </tbody>

            </table>
          </div>

          <button type="button"
                  class="btn btn-outline-primary btn-sm mt-3"
                  onclick="agregarFila()">
            ➕ Agregar clasificación
          </button>

          <div class="d-flex justify-content-end mt-4">
            <button type="submit"
                    class="btn btn-success rounded-pill px-4">
              💾 Guardar parámetros
            </button>
          </div>

        </form>

      </div>

    </div>

     <style>
      body {
        background-image: url('/static/img/ccsgsi.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
      }

      .incparam-shell {
        width: 96%;
        max-width: 1200px;
        margin: 26px auto 24px auto;
        overflow: hidden;
      }

      .incparam-header-card {
        background: linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius: 18px;
        padding: 16px 24px;
        min-height: 94px;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        box-shadow: 0 12px 24px rgba(15,23,42,.25);
        position: relative;
        overflow: hidden;
        margin-bottom: 14px;
      }

      .incparam-header-card::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .incparam-header-overlay {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        text-align: left;
        position: relative;
        z-index: 1;
        min-width: 0;
      }

      .incparam-header-overlay::before {
        content: "🚨";
        width: 54px;
        height: 54px;
        min-width: 54px;
        border-radius: 14px;
        background: #ffffff;
        color: #0b4a8f;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.4rem;
        box-shadow: 0 8px 18px rgba(0,0,0,.25);
        margin-right: 14px;
      }

      .incparam-header-text {
        max-width: 1000px;
        min-width: 0;
      }

      .incparam-header-text::before {
        content: "SGSI · Parámetros de Incidentes";
        display: inline-block;
        background: rgba(255,255,255,.18);
        border-radius: 999px;
        padding: 3px 10px;
        font-size: .65rem;
        font-weight: 800;
        margin-bottom: 4px;
        color: #ffffff;
      }

      .incparam-title {
        color: #ffffff !important;
        font-weight: 950;
        font-size: 1.32rem;
        line-height: 1.1;
        margin: 0 !important;
        text-shadow: 0 4px 14px rgba(0,0,0,.45);
        overflow-wrap: break-word;
      }

      .incparam-subtitle {
        color: rgba(255,255,255,.95);
        font-size: .78rem;
        line-height: 1.25;
        margin-top: 3px;
        overflow-wrap: break-word;
      }

      .incparam-header-actions {
        display: flex;
        justify-content: center;
        gap: 10px;
        flex-wrap: wrap;
        margin: 10px 0 14px;
      }

      .btn {
        border-radius: 10px !important;
        font-weight: 900;
        box-shadow: 0 4px 10px rgba(0,0,0,.08);
      }

      .incparam-btn-main {
        background: #ffffff;
        color: #0f172a;
        border: 1px solid #cfd8e3;
      }

      .incparam-btn-main:hover {
        background: #edf5ff;
        color: #0b65d8;
      }

      .incparam-card {
        background: rgba(255,255,255,.96) !important;
        border-radius: 18px;
        backdrop-filter: blur(8px);
        box-shadow: 0 12px 24px rgba(15,23,42,.18);
        border: 1px solid rgba(219,230,244,.9);
        overflow: hidden;
        width: 100%;
        max-width: 100%;
      }

      .incparam-card .card-body,
      .incparam-card-body {
        padding: 22px;
      }

      .incparam-section-title {
        font-weight: 950;
        font-size: .95rem;
        color: #0b4a8f;
        margin-bottom: 16px;
        border-bottom: 2px solid rgba(59,130,246,.18);
        padding-bottom: 8px;
        overflow-wrap: break-word;
      }

      .form-control,
      .form-select {
        border-radius: 10px;
        border: 1px solid #d9e3f0;
        min-height: 40px;
        font-size: .86rem;
        background: #f8fafc;
      }

      .form-control:focus,
      .form-select:focus {
        border-color: #3f86d6;
        box-shadow: 0 0 0 .15rem rgba(63,134,214,.18);
        background: #ffffff;
      }

      .incparam-table-wrap {
        border: 1px solid #e2ebf5;
        border-radius: 14px;
        background: #ffffff;
        overflow-x: auto;
        overflow-y: hidden;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.35);
        width: 100%;
        max-width: 100%;
      }

      .incparam-table-wrap .table {
        margin-bottom: 0;
        min-width: 780px;
      }

      .incparam-table-head th,
      .incparam-table-wrap thead th {
        background: #eef5ff !important;
        font-weight: 900;
        color: #0b4a8f;
        border-bottom: 1px solid #d7dee7 !important;
        vertical-align: middle;
        white-space: nowrap;
        font-size: .82rem;
      }

      .incparam-table-wrap tbody td {
        vertical-align: middle;
        font-size: .85rem;
        color: #334155;
      }

      .incparam-table-wrap tbody tr:last-child td {
        border-bottom: none;
      }

      .incparam-table-wrap tbody tr:hover {
        background: #f8fbff;
      }

      .incparam-btn-add {
        border-radius: 10px;
        font-weight: 900;
        box-shadow: 0 4px 10px rgba(0,0,0,.08);
      }

      .incparam-btn-del {
        border-radius: 10px;
        font-weight: 900;
      }

      h3 {
        color: #ffffff;
        margin: 0;
      }

      @media (max-width: 992px) {
        .incparam-shell {
          width: 98%;
          margin: 8px auto 22px auto;
        }

        .incparam-title {
          font-size: 1.20rem;
        }

        .incparam-subtitle {
          font-size: .76rem;
        }

        .incparam-card .card-body,
        .incparam-card-body {
          padding: 16px;
        }
      }

      @media (max-width: 768px) {
        .incparam-header-overlay {
          flex-direction: column;
          text-align: center;
          gap: 10px;
        }

        .incparam-header-overlay::before {
          margin: 0;
        }

        .incparam-title,
        .incparam-subtitle {
          text-align: center;
        }

        .incparam-header-actions .btn {
          width: 100%;
        }
      }
    </style>
    """,
    eta_valor=eta_valor,
    clasificaciones_guardadas=clasificaciones_guardadas,
    clasif_choices=INCIDENTE_CLASIFICACIONES)

    return render_template_string(BASE, content=content)

#==================================
# Configuración de Vulnerabilidades
#==================================

