def render_tabla_valoracion(titulo, items, post_url, edit_item=None, delete_url=None, volver_url=None):
    html = """
    <div class="container mt-4">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h3 class="m-0">{{ titulo }}</h3>
        <div class="d-flex gap-2">
          <a href="{{ volver_url }}" class="btn btn-secondary rounded-pill px-4 py-2">⬅ Volver</a>
          <a href="{{ url_for('activos_menu') }}" class="btn btn-outline-secondary rounded-pill px-4 py-2">🏠 Volver al Menú Activos</a>
        </div>
      </div>

      <!-- Formulario crear/editar -->
      <div class="card shadow-sm mb-3">
        <div class="card-body">
          <form method="post" action="{{ post_url }}">
            {% if edit_item %}
              <input type="hidden" name="id" value="{{ edit_item.id }}">
            {% endif %}

            <div class="row g-3">
              <div class="col-md-4">
                <label class="form-label">Nivel</label>
                <input type="text" name="nivel" class="form-control" required
                       value="{{ edit_item.nivel if edit_item else '' }}" placeholder="Alto / Medio / Bajo">
              </div>
              <div class="col-md-2">
                <label class="form-label">Impacto (1..5)</label>
                <input type="number" name="impacto" class="form-control" min="1" max="5" required
                       value="{{ edit_item.impacto if edit_item else '' }}">
              </div>
              <div class="col-md-3">
                <label class="form-label">Clasificación</label>
                <input type="text" name="clasificacion" class="form-control" required
                       value="{{ edit_item.clasificacion if edit_item else '' }}" placeholder="Restringido / Interno / Público">
              </div>
              <div class="col-md-3">
                <label class="form-label d-block">Estado</label>
                <select name="activo" class="form-select">
                  <option value="1" {% if edit_item and edit_item.activo %}selected{% endif %}>Activo</option>
                  <option value="0" {% if edit_item and not edit_item.activo %}selected{% endif %}>Inactivo</option>
                </select>
              </div>
              <div class="col-12">
                <label class="form-label">Descripción</label>
                <textarea name="descripcion" class="form-control" rows="2" required>{{ edit_item.descripcion if edit_item else '' }}</textarea>
              </div>
            </div>

            <div class="mt-3 d-flex justify-content-center gap-2">
              <button type="submit" class="btn btn-success rounded-pill px-4">
                {% if edit_item %}Guardar cambios{% else %}Agregar{% endif %}
              </button>
              {% if edit_item %}
                <a href="{{ request.path }}" class="btn btn-outline-secondary rounded-pill px-4">Cancelar</a>
              {% endif %}
            </div>
          </form>
        </div>
      </div>

      <!-- Tabla -->
      <div class="table-responsive">
        <table class="table table-bordered table-sm align-middle">
          <thead class="table-secondary">
            <tr class="text-center">
              <th style="width:12%">Nivel</th>
              <th style="width:10%">Impacto</th>
              <th style="width:18%">Clasificación</th>
              <th>Descripción</th>
              <th style="width:16%">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {% for it in items %}
            <tr>
              <td><b>{{ it.nivel }}</b> {% if not it.activo %}<span class="badge bg-secondary ms-1">Inactivo</span>{% endif %}</td>
              <td class="text-center">{{ it.impacto }}</td>
              <td>{{ it.clasificacion }}</td>
              <td class="small">{{ it.descripcion }}</td>
              <td class="text-center">
                <a href="{{ request.path }}?edit={{ it.id }}" class="btn btn-warning btn-sm rounded-pill px-3">Editar</a>
                <a href="{{ delete_url }}?id={{ it.id }}" class="btn btn-danger btn-sm rounded-pill px-3"
                   onclick="return confirm('¿Eliminar este registro?');">Eliminar</a>
              </td>
            </tr>
            {% endfor %}
            {% if items|length == 0 %}
              <tr><td colspan="5" class="text-center text-muted">Sin registros</td></tr>
            {% endif %}
          </tbody>
        </table>
      </div>
    </div>
    """
    return Markup(render_template_string(
        html,
        titulo=titulo,
        items=items,
        post_url=post_url,
        edit_item=edit_item,
        delete_url=delete_url,
        volver_url=volver_url,
        request=request
    ))
    


# =========================
# Valor Confidencialidad
# =========================

@app.route('/valor_confidencialidad', methods=['GET', 'POST'])
@login_required
def valor_confidencialidad():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores"):
            flash("No tiene permiso para ver los registros de proveedores.", "danger")
            return redirect(url_for('proveedores_menu'))
        read_only = False

    # 3) Definir si es solo lectura (auditor)
    solo_lectura = (user.role == 'auditor')

    # (Si no usas 'areas' aquí, incluso podrías eliminar esta línea)
    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()

    # 🚫 Si es auditor, ignoramos cualquier POST (no puede crear/editar)
    if request.method == 'POST' and solo_lectura:
        flash("El rol Auditor no puede modificar la tabla de valoración de confidencialidad.", "danger")
        return redirect(url_for('valor_confidencialidad'))

    # Crear / Editar: solo si NO es solo lectura
    if request.method == 'POST' and not solo_lectura:
        rid = request.form.get('id')
        nivel_txt = (request.form.get('nivel_confidencialidad') or "").strip()
        descripcion = (request.form.get('descripcion') or "").strip()
        impacto = (request.form.get('impacto') or "").strip()
        clasificacion = (request.form.get('clasificacion') or "").strip()
        try:
            nivel_num = int(request.form.get('nivel_num') or 0)
        except ValueError:
            nivel_num = 0

        # Validación
        if not (nivel_txt and descripcion and impacto and clasificacion):
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for('valor_confidencialidad'))
        if nivel_num < 1 or nivel_num > 5:
            flash("El nivel numérico debe estar entre 1 y 5.", "danger")
            return redirect(url_for('valor_confidencialidad'))

        # Crear / editar
        if rid:
            it = ValoracionConfidencialidad.query.get(int(rid))
            if not it:
                flash("Registro no encontrado.", "danger")
                return redirect(url_for('valor_confidencialidad'))
        else:
            it = ValoracionConfidencialidad()

        it.nivel_confidencialidad = nivel_txt
        it.descripcion = descripcion
        it.impacto = impacto
        it.clasificacion = clasificacion
        it.nivel_num = nivel_num

        db.session.add(it)
        db.session.commit()
        flash("Guardado correctamente.", "success")
        return redirect(url_for('valor_confidencialidad'))

    # GET
    edit_id = request.args.get('edit', type=int)
    edit_item = ValoracionConfidencialidad.query.get(edit_id) if edit_id else None
    items = ValoracionConfidencialidad.query.order_by(ValoracionConfidencialidad.nivel_num.asc(), ValoracionConfidencialidad.id.desc()).all()

    html = """
    <div class="valconf-shell">

      <!-- CABECERA -->
      <div class="valconf-header-card">
        <div class="valconf-header-overlay">
          <div class="valconf-header-text">
            <h3 class="valconf-title m-0">Tabla de Valoración — Confidencialidad</h3>
            <div class="valconf-subtitle">
              Configuración de niveles, clasificación e impacto para la valoración de confidencialidad de activos
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="valconf-header-actions">
      </div>

      <!-- FORMULARIO -->
      {% if not solo_lectura %}
      <div class="valconf-card mb-3">
        <div class="valconf-card-body">
          <form method="post" action="{{ url_for('valor_confidencialidad') }}">
            {% if edit_item %}
              <input type="hidden" name="id" value="{{ edit_item.id }}">
            {% endif %}

            <div class="row g-3">

              <div class="col-md-3">
                <label class="form-label">Nivel de Confidencialidad (texto)</label>
                <input type="text"
                       name="nivel_confidencialidad"
                       class="form-control"
                       required
                       placeholder="Alto / Medio / Bajo / etc."
                       value="{{ edit_item.nivel_confidencialidad if edit_item else '' }}">
              </div>

              <div class="col-md-2">
                <label class="form-label">Nivel (numérico 1–5)</label>
                <input type="number"
                       name="nivel_num"
                       class="form-control"
                       min="1"
                       max="5"
                       required
                       value="{{ edit_item.nivel_num if edit_item else '' }}"
                       placeholder="1 a 5">
              </div>

              <div class="col-md-4">
                <label class="form-label">Clasificación (texto)</label>
                <input type="text"
                       name="clasificacion"
                       class="form-control"
                       required
                       placeholder="Restringido / Interno / Público / etc."
                       value="{{ edit_item.clasificacion if edit_item else '' }}">
              </div>

              <div class="col-md-12">
                <label class="form-label">Impacto</label>
                <textarea name="impacto"
                          class="form-control"
                          rows="2"
                          required
                          placeholder="Descripción del impacto, ejemplos, alcance...">{{ edit_item.impacto if edit_item else '' }}</textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Descripción</label>
                <textarea name="descripcion"
                          class="form-control"
                          rows="2"
                          required
                          placeholder="Definición del nivel, ejemplos, alcance...">{{ edit_item.descripcion if edit_item else '' }}</textarea>
              </div>

            </div>

            <div class="valconf-bottom-actions">
              <button type="submit" class="btn btn-success rounded-pill px-4 fw-bold">
                {% if edit_item %}Guardar cambios{% else %}Agregar{% endif %}
              </button>

              {% if edit_item %}
                <a href="{{ url_for('valor_confidencialidad') }}"
                   class="btn rounded-pill px-4 fw-bold valconf-cancel-btn">
                  Cancelar
                </a>
              {% endif %}
            </div>
          </form>
        </div>
      </div>
      {% endif %}

      <!-- TABLA -->
      <style>
        .badge-n1 { background:#2ecc71; }
        .badge-n2 { background:#f1c40f; color:#111; }
        .badge-n3 { background:#ff6f61; }
        .badge-n4 { background:#8e2c2c; }
        .badge-n5 { background:#8e44ad; }
      </style>

      <div class="valconf-card">
        <div class="valconf-card-body">

          <div class="valconf-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-sm align-middle valconf-table mb-0">
                <thead class="table-secondary">
                  <tr class="text-center">
                    <th style="width:16%">Nivel (texto)</th>
                    <th style="width:8%">Nivel<br>numérico</th>
                    <th>Descripción</th>
                    <th style="width:18%">Impacto</th>
                    <th style="width:20%">Clasificación (color por nivel)</th>
                    <th style="width:16%">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {% for it in items %}
                    {% set cls = 'badge-n' ~ (it.nivel_num if it.nivel_num in [1,2,3,4,5] else 3) %}
                    <tr>
                      <td><b>{{ it.nivel_confidencialidad }}</b></td>
                      <td class="text-center">{{ it.nivel_num }}</td>
                      <td class="small">{{ it.descripcion }}</td>
                      <td>{{ it.impacto }}</td>
                      <td class="text-center">
                        <span class="badge {{ cls }} rounded-pill px-3 py-2">
                          {{ it.clasificacion }}
                        </span>
                      </td>
                      <td class="text-center">
                        {% if not solo_lectura %}
                          <a href="{{ url_for('valor_confidencialidad', edit=it.id) }}"
                             class="btn btn-warning btn-sm rounded-pill px-3">
                            Editar
                          </a>
                          <a href="{{ url_for('valor_confidencialidad_delete', id=it.id) }}"
                             class="btn btn-danger btn-sm rounded-pill px-3"
                             onclick="return confirm('¿Eliminar este registro?');">
                            Eliminar
                          </a>
                        {% else %}
                          <span class="text-muted small">Solo lectura</span>
                        {% endif %}
                      </td>
                    </tr>
                  {% endfor %}

                  {% if items|length == 0 %}
                    <tr>
                      <td colspan="6" class="text-center text-muted py-4">Sin registros</td>
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

      .valconf-shell{
        width:96%;
        max-width:1600px;
        margin:10px auto 24px auto;
      }

      .valconf-header-card{
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

      .valconf-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .valconf-header-overlay{
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

      .valconf-header-overlay::before{
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

      .valconf-header-text{
        max-width:1100px;
        width:100%;
        transform:none;
      }

      .valconf-header-text::before{
        content:"SGSI · Tablas de Valoración";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .valconf-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .valconf-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .valconf-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin:10px 0 14px;
        flex-wrap:wrap;
      }

      .valconf-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .valconf-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .valconf-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .valconf-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .valconf-card-body{
        padding:18px;
      }

      .valconf-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .valconf-card .form-control,
      .valconf-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .valconf-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .valconf-card .form-control:focus,
      .valconf-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }

      .valconf-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .valconf-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .valconf-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .valconf-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .valconf-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#fff;
      }

      .valconf-table{
        width:100%;
        min-width:1100px;
        table-layout:auto;
        margin-bottom:0;
      }

      .valconf-table th,
      .valconf-table td{
        white-space:normal;
        word-break:break-word;
        vertical-align:top;
        font-size:.78rem;
        padding:9px 8px;
      }

      .valconf-table td{
        border-bottom:1px solid #e5edf7;
      }

      .valconf-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
      }

      .valconf-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .valconf-table tbody tr:hover{
        background:#eef6ff;
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .btn.rounded-pill{
        border-radius:999px !important;
      }

      .valconf-card .btn{
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        font-weight:900;
        font-size:.78rem;
      }

      @media (max-width:992px){
        .valconf-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .valconf-header-card{
          min-height:88px;
        }

        .valconf-title{
          font-size:1.20rem;
        }

        .valconf-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .valconf-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .valconf-header-overlay::before{
          margin:0;
        }

        .valconf-header-actions .btn,
        .valconf-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        edit_item=edit_item,
        items=items,
        solo_lectura=solo_lectura
    )
    return render_template_string(BASE, content=Markup(inner))

@app.route('/valor_confidencialidad/delete')
@login_required
def valor_confidencialidad_delete():
    user = User.query.filter_by(username=session['username']).first()
    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros de la tabla de confidencialidad.", "danger")
        return redirect(url_for('valor_confidencialidad'))
    
    rid = request.args.get('id', type=int)
    it = ValoracionConfidencialidad.query.get(rid)
    if it:
        db.session.delete(it)
        db.session.commit()
        flash("Eliminado correctamente.", "success")
    else:
        flash("Registro no encontrado.", "danger")
    return redirect(url_for('valor_confidencialidad'))

# =========================
# Valor Integridad
# =========================

@app.route('/valor_integridad', methods=['GET', 'POST'])
@login_required
def valor_integridad():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores"):
            flash("No tiene permiso para ver los registros de proveedores.", "danger")
            return redirect(url_for('proveedores_menu'))
        read_only = False

    # 3) Definir si es solo lectura (auditor)
    solo_lectura = (user.role == 'auditor')

    # 4) Si es auditor e intenta hacer POST, se bloquea
    if request.method == 'POST' and solo_lectura:
        flash("El rol Auditor no puede modificar la tabla de valoración de integridad.", "danger")
        return redirect(url_for('valor_integridad'))

    # 5) Crear / Editar: solo si NO es solo lectura
    if request.method == 'POST' and not solo_lectura:
        rid = request.form.get('id')
        nivel_txt = (request.form.get('nivel') or "").strip()
        descripcion = (request.form.get('descripcion') or "").strip()
        impacto = (request.form.get('impacto') or "").strip()
        clasificacion = (request.form.get('clasificacion') or "").strip()
        try:
            nivel_num = int(request.form.get('nivel_num') or 0)
        except ValueError:
            nivel_num = 0

        if not (nivel_txt and descripcion and impacto and clasificacion):
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for('valor_integridad'))
        if nivel_num < 1 or nivel_num > 5:
            flash("El nivel numérico debe estar entre 1 y 5.", "danger")
            return redirect(url_for('valor_integridad'))

        if rid:
            it = ValoracionIntegridad.query.get(int(rid))
            if not it:
                flash("Registro no encontrado.", "danger")
                return redirect(url_for('valor_integridad'))
        else:
            it = ValoracionIntegridad()

        it.nivel = nivel_txt
        it.descripcion = descripcion
        it.impacto = impacto
        it.clasificacion = clasificacion
        it.nivel_num = nivel_num

        db.session.add(it)
        db.session.commit()
        flash("Guardado correctamente.", "success")
        return redirect(url_for('valor_integridad'))

    # GET
    edit_id = request.args.get('edit', type=int)
    edit_item = ValoracionIntegridad.query.get(edit_id) if edit_id else None
    items = ValoracionIntegridad.query.order_by(ValoracionIntegridad.nivel_num.asc(), ValoracionIntegridad.id.desc()).all()

    html = """
    <div class="valint-shell">

      <!-- CABECERA -->
      <div class="valint-header-card">
        <div class="valint-header-overlay">
          <div class="valint-header-text">
            <h3 class="valint-title m-0">Tabla de Valoración — Integridad</h3>
            <div class="valint-subtitle">
              Configuración de niveles, clasificación e impacto para la valoración de integridad de activos
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="valint-header-actions">
      </div>

      <!-- FORMULARIO -->
      {% if not solo_lectura %}
      <div class="valint-card mb-3">
        <div class="valint-card-body">

          <form method="post" action="{{ url_for('valor_integridad') }}">
            {% if edit_item %}
              <input type="hidden" name="id" value="{{ edit_item.id }}">
            {% endif %}

            <div class="row g-3">

              <div class="col-md-3">
                <label class="form-label">Nivel (texto)</label>
                <input type="text"
                       name="nivel"
                       class="form-control"
                       required
                       placeholder="Alto / Medio / Bajo / etc."
                       value="{{ edit_item.nivel if edit_item else '' }}">
              </div>

              <div class="col-md-2">
                <label class="form-label">Nivel (numérico 1–5)</label>
                <input type="number"
                       name="nivel_num"
                       class="form-control"
                       min="1"
                       max="5"
                       required
                       value="{{ edit_item.nivel_num if edit_item else '' }}"
                       placeholder="1 a 5">
              </div>

              <div class="col-md-4">
                <label class="form-label">Clasificación (texto)</label>
                <input type="text"
                       name="clasificacion"
                       class="form-control"
                       required
                       placeholder="Crítico / Importante / Normal / etc."
                       value="{{ edit_item.clasificacion if edit_item else '' }}">
              </div>

              <div class="col-md-12">
                <label class="form-label">Impacto</label>
                <textarea name="impacto"
                          class="form-control"
                          rows="2"
                          required
                          placeholder="Descripción del impacto, ejemplos, alcance...">{{ edit_item.impacto if edit_item else '' }}</textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Descripción</label>
                <textarea name="descripcion"
                          class="form-control"
                          rows="2"
                          required
                          placeholder="Definición del nivel, ejemplos, alcance...">{{ edit_item.descripcion if edit_item else '' }}</textarea>
              </div>

            </div>

            <div class="valint-bottom-actions">

              <button type="submit" class="btn btn-success rounded-pill px-4 fw-bold">
                {% if edit_item %}Guardar cambios{% else %}Agregar{% endif %}
              </button>

              {% if edit_item %}
                <a href="{{ url_for('valor_integridad') }}"
                   class="btn rounded-pill px-4 fw-bold valint-cancel-btn">
                  Cancelar
                </a>
              {% endif %}

            </div>

          </form>

        </div>
      </div>
      {% endif %}

      <!-- TABLA -->
      <style>
        .badge-n1 { background:#2ecc71; }
        .badge-n2 { background:#f1c40f; color:#111; }
        .badge-n3 { background:#e74c3c; }
        .badge-n4 { background:#8e2c2c; }
        .badge-n5 { background:#8e44ad; }
      </style>

      <div class="valint-card">
        <div class="valint-card-body">

          <div class="valint-table-wrap">
            <div class="table-responsive">

              <table class="table table-bordered table-sm align-middle valint-table mb-0">

                <thead class="table-secondary">
                  <tr class="text-center">
                    <th style="width:16%">Nivel (texto)</th>
                    <th style="width:8%">Nivel<br>numérico</th>
                    <th>Descripción</th>
                    <th style="width:18%">Impacto</th>
                    <th style="width:20%">Clasificación (color por nivel)</th>
                    <th style="width:16%">Acciones</th>
                  </tr>
                </thead>

                <tbody>

                {% for it in items %}
                  {% set cls = 'badge-n' ~ (it.nivel_num if it.nivel_num in [1,2,3,4,5] else 3) %}

                  <tr>

                    <td><b>{{ it.nivel }}</b></td>

                    <td class="text-center">
                      {{ it.nivel_num }}
                    </td>

                    <td class="small">
                      {{ it.descripcion }}
                    </td>

                    <td>
                      {{ it.impacto }}
                    </td>

                    <td class="text-center">
                      <span class="badge {{ cls }} rounded-pill px-3 py-2">
                        {{ it.clasificacion }}
                      </span>
                    </td>

                    <td class="text-center">

                      {% if not solo_lectura %}

                        <a href="{{ url_for('valor_integridad', edit=it.id) }}"
                           class="btn btn-warning btn-sm rounded-pill px-3">
                          Editar
                        </a>

                        <a href="{{ url_for('valor_integridad_delete', id=it.id) }}"
                           class="btn btn-danger btn-sm rounded-pill px-3"
                           onclick="return confirm('¿Eliminar este registro?');">
                          Eliminar
                        </a>

                      {% else %}

                        <span class="text-muted small">Solo lectura</span>

                      {% endif %}

                    </td>

                  </tr>

                {% endfor %}

                {% if items|length == 0 %}
                  <tr>
                    <td colspan="6" class="text-center text-muted py-4">
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
    .valint-shell{
      width:96%;
      max-width:1600px;
      margin:10px auto 24px auto;
    }

    /* =========================
       HEADER SGSI PRO
    ========================= */
    .valint-header-card{
      background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
      border-radius:18px;
      padding:16px 24px;
      min-height:95px;
      display:flex;
      align-items:center;
      justify-content:center;
      box-shadow:0 12px 24px rgba(15,23,42,.25);
      position:relative;
      overflow:hidden;
      margin-bottom:10px;
    }

    .valint-header-card::before{
      content:"";
      position:absolute;
      inset:0;
      background:
        radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
        repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
    }

    /* ICONO */
    .valint-header-overlay{
      width:100%;
      display:flex;
      align-items:center;
      justify-content:flex-start;
      text-align:left;
      position:relative;
      z-index:1;
    }

    .valint-header-overlay::before{
      content:"🧩";
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
    }

    /* TEXTO */
    .valint-header-text{
      max-width:1100px;
      width:100%;
    }

    .valint-header-text::before{
      content:"SGSI · Valoración Interna";
      display:inline-block;
      background:rgba(255,255,255,.18);
      border-radius:999px;
      padding:3px 10px;
      font-size:.65rem;
      font-weight:800;
      margin-bottom:4px;
      color:#fff;
    }

    .valint-title{
      color:#ffffff !important;
      font-weight:950;
      font-size:1.32rem;
      line-height:1.1;
      text-shadow:0 3px 10px rgba(0,0,0,.35);
      margin:0 !important;
    }

    .valint-subtitle{
      color:rgba(255,255,255,.95);
      font-size:.78rem;
      margin-top:4px;
    }

    /* =========================
       BOTONES SUPERIORES
    ========================= */
    .valint-header-actions{
      display:flex;
      justify-content:center;
      gap:10px;
      margin:10px 0 14px;
      flex-wrap:wrap;
    }

    .valint-header-actions .btn{
      border-radius:10px !important;
      min-height:32px;
      padding:8px 22px !important;
      font-size:.82rem;
      font-weight:900;
      box-shadow:0 8px 16px rgba(15,23,42,.15);
    }

    .valint-back-btn{
      background:#ffffff;
      color:#0f172a;
      border:1px solid #cfd8e3;
    }

    .valint-back-btn:hover{
      background:#edf5ff;
      color:#0b65d8;
      border-color:#9ec5fe;
    }

    /* =========================
       CARD PRINCIPAL
    ========================= */
    .valint-card{
      background:rgba(255,255,255,.96)!important;
      border-radius:18px;
      backdrop-filter:blur(8px);
      box-shadow:0 12px 24px rgba(15,23,42,.18);
      border:1px solid rgba(219,230,244,.9);
      overflow:hidden;
    }

    .valint-card-body{
      padding:18px;
    }

    /* =========================
       FORMULARIOS
    ========================= */
    .valint-card .form-label{
      font-weight:800;
      color:#25324a;
      font-size:.78rem;
    }

    .valint-card .form-control,
    .valint-card .form-select{
      border-radius:9px;
      border:1px solid #d9e3f0;
      min-height:32px;
      font-size:.80rem;
      background:#f8fafc;
    }

    .valint-card textarea{
      min-height:70px;
    }

    .valint-card .form-control:focus,
    .valint-card .form-select:focus{
      border-color:#3f86d6;
      box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
      background:#fff;
    }

    /* =========================
       BOTONES INFERIORES
    ========================= */
    .valint-bottom-actions{
      display:flex;
      justify-content:center;
      gap:10px;
      margin-top:18px;
      flex-wrap:wrap;
    }

    .valint-bottom-actions .btn{
      border-radius:10px !important;
      min-height:32px;
      padding:8px 22px !important;
      font-size:.82rem;
      font-weight:900;
      box-shadow:0 8px 16px rgba(15,23,42,.15);
    }

    .valint-cancel-btn{
      background:#ffffff;
      color:#0f172a;
      border:1px solid #cfd8e3;
    }

    .valint-cancel-btn:hover{
      background:#edf5ff;
      color:#0b65d8;
    }

    /* =========================
       TABLA PRO
    ========================= */
    .valint-table-wrap{
      max-height:70vh;
      overflow:auto;
      border:1px solid #dbe6f4;
      border-radius:14px;
      background:#fff;
    }

    .valint-table{
      width:100%;
      min-width:1100px;
    }

    .valint-table th,
    .valint-table td{
      font-size:.78rem;
      padding:9px;
      word-break:break-word;
    }

    .valint-table thead th{
      position:sticky;
      top:0;
      z-index:10;
      background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
      color:#fff !important;
      font-weight:900;
      text-align:center;
    }

    .valint-table tbody tr:nth-child(even){
      background:#f8fbff;
    }

    .valint-table tbody tr:hover{
      background:#eef6ff;
    }

    /* =========================
       RESPONSIVE
    ========================= */
    @media (max-width:768px){
      .valint-header-overlay{
        flex-direction:column;
        text-align:center;
        gap:10px;
      }

      .valint-header-overlay::before{
        margin:0;
      }

      .valint-header-actions .btn,
      .valint-bottom-actions .btn{
        width:100%;
      }
    }
    </style>
    """
    inner = render_template_string(
        html,
        edit_item=edit_item,
        items=items,
        solo_lectura=solo_lectura
    )
    return render_template_string(BASE, content=Markup(inner))

@app.route('/valor_integridad/delete')
@login_required
def valor_integridad_delete():
    user = User.query.filter_by(username=session['username']).first()
    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros de la tabla de integridad.", "danger")
        return redirect(url_for('valor_integridad'))
    
    rid = request.args.get('id', type=int)
    it = ValoracionIntegridad.query.get(rid)
    if it:
        db.session.delete(it)
        db.session.commit()
        flash("Eliminado correctamente.", "success")
    else:
        flash("Registro no encontrado.", "danger")
    return redirect(url_for('valor_integridad'))

# =========================
# Valor Disponibilidad
# =========================

@app.route('/valor_disponibilidad', methods=['GET', 'POST'])
@login_required
def valor_disponibilidad():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores"):
            flash("No tiene permiso para ver los registros de proveedores.", "danger")
            return redirect(url_for('proveedores_menu'))
        read_only = False

    # 3) Definir si es solo lectura (auditor)
    solo_lectura = (user.role == 'auditor')

    # 4) Si es auditor e intenta hacer POST, bloquear
    if request.method == 'POST' and solo_lectura:
        flash("El rol Auditor no puede modificar la tabla de valoración de disponibilidad.", "danger")
        return redirect(url_for('valor_disponibilidad'))

    # 5) Crear / Editar: solo si NO es solo lectura
    if request.method == 'POST' and not solo_lectura:
        rid = request.form.get('id')
        nivel_txt = (request.form.get('nivel') or "").strip()
        descripcion = (request.form.get('descripcion') or "").strip()
        impacto = (request.form.get('impacto') or "").strip()
        clasificacion = (request.form.get('clasificacion') or "").strip()
        try:
            nivel_num = int(request.form.get('nivel_num') or 0)
        except ValueError:
            nivel_num = 0

        if not (nivel_txt and descripcion and impacto and clasificacion):
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for('valor_disponibilidad'))
        if nivel_num < 1 or nivel_num > 5:
            flash("El nivel numérico debe estar entre 1 y 5.", "danger")
            return redirect(url_for('valor_disponibilidad'))

        if rid:
            it = ValoracionDisponibilidad.query.get(int(rid))
            if not it:
                flash("Registro no encontrado.", "danger")
                return redirect(url_for('valor_disponibilidad'))
        else:
            it = ValoracionDisponibilidad()

        it.nivel = nivel_txt
        it.descripcion = descripcion
        it.impacto = impacto
        it.clasificacion = clasificacion
        it.nivel_num = nivel_num

        db.session.add(it)
        db.session.commit()
        flash("Guardado correctamente.", "success")
        return redirect(url_for('valor_disponibilidad'))

    # GET
    edit_id = request.args.get('edit', type=int)
    edit_item = ValoracionDisponibilidad.query.get(edit_id) if edit_id else None
    items = ValoracionDisponibilidad.query.order_by(
        ValoracionDisponibilidad.nivel_num.asc(),
        ValoracionDisponibilidad.id.desc()
    ).all()

    html = """
    <div class="valdisp-shell">

      <!-- CABECERA -->
      <div class="valdisp-header-card">
        <div class="valdisp-header-overlay">
          <div class="valdisp-header-text">
            <h3 class="valdisp-title m-0">Tabla de Valoración — Disponibilidad</h3>
            <div class="valdisp-subtitle">
              Configuración de niveles, clasificación e impacto para la valoración de disponibilidad de activos
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="valdisp-header-actions">
    
      </div>

      <!-- FORMULARIO -->
      {% if not solo_lectura %}
      <div class="valdisp-card mb-3">
        <div class="valdisp-card-body">

          <form method="post" action="{{ url_for('valor_disponibilidad') }}">
            {% if edit_item %}
              <input type="hidden" name="id" value="{{ edit_item.id }}">
            {% endif %}

            <div class="row g-3">

              <div class="col-md-3">
                <label class="form-label">Nivel (texto)</label>
                <input type="text"
                       name="nivel"
                       class="form-control"
                       required
                       placeholder="Alta / Media / Baja / etc."
                       value="{{ edit_item.nivel if edit_item else '' }}">
              </div>

              <div class="col-md-2">
                <label class="form-label">Nivel (numérico 1–5)</label>
                <input type="number"
                       name="nivel_num"
                       class="form-control"
                       min="1"
                       max="5"
                       required
                       value="{{ edit_item.nivel_num if edit_item else '' }}"
                       placeholder="1 a 5">
              </div>

              <div class="col-md-4">
                <label class="form-label">Clasificación (texto)</label>
                <input type="text"
                       name="clasificacion"
                       class="form-control"
                       required
                       placeholder="Crítico / Importante / Normal / etc."
                       value="{{ edit_item.clasificacion if edit_item else '' }}">
              </div>

              <div class="col-md-12">
                <label class="form-label">Impacto</label>
                <textarea name="impacto"
                          class="form-control"
                          rows="2"
                          required
                          placeholder="Descripción del impacto, ejemplos, alcance...">{{ edit_item.impacto if edit_item else '' }}</textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Descripción</label>
                <textarea name="descripcion"
                          class="form-control"
                          rows="2"
                          required
                          placeholder="Definición del nivel, ejemplos, alcance...">{{ edit_item.descripcion if edit_item else '' }}</textarea>
              </div>

            </div>

            <div class="valdisp-bottom-actions">

              <button type="submit" class="btn btn-success rounded-pill px-4 fw-bold">
                {% if edit_item %}Guardar cambios{% else %}Agregar{% endif %}
              </button>

              {% if edit_item %}
                <a href="{{ url_for('valor_disponibilidad') }}"
                   class="btn rounded-pill px-4 fw-bold valdisp-cancel-btn">
                  Cancelar
                </a>
              {% endif %}

            </div>

          </form>

        </div>
      </div>
      {% endif %}

      <!-- TABLA -->
      <style>
        .badge-n1 { background:#2ecc71; }
        .badge-n2 { background:#f1c40f; color:#111; }
        .badge-n3 { background:#e74c3c; }
        .badge-n4 { background:#8e2c2c; }
        .badge-n5 { background:#8e44ad; }
      </style>

      <div class="valdisp-card">
        <div class="valdisp-card-body">

          <div class="valdisp-table-wrap">
            <div class="table-responsive">

              <table class="table table-bordered table-sm align-middle valdisp-table mb-0">

                <thead class="table-secondary">
                  <tr class="text-center">
                    <th style="width:16%">Nivel (texto)</th>
                    <th style="width:8%">Nivel<br>numérico</th>
                    <th>Descripción</th>
                    <th style="width:18%">Impacto</th>
                    <th style="width:20%">Clasificación (color por nivel)</th>
                    <th style="width:16%">Acciones</th>
                  </tr>
                </thead>

                <tbody>

                {% for it in items %}
                  {% set cls = 'badge-n' ~ (it.nivel_num if it.nivel_num in [1,2,3,4,5] else 3) %}

                  <tr>

                    <td><b>{{ it.nivel }}</b></td>

                    <td class="text-center">
                      {{ it.nivel_num }}
                    </td>

                    <td class="small">
                      {{ it.descripcion }}
                    </td>

                    <td>
                      {{ it.impacto }}
                    </td>

                    <td class="text-center">
                      <span class="badge {{ cls }} rounded-pill px-3 py-2">
                        {{ it.clasificacion }}
                      </span>
                    </td>

                    <td class="text-center">

                      {% if not solo_lectura %}

                        <a href="{{ url_for('valor_disponibilidad', edit=it.id) }}"
                           class="btn btn-warning btn-sm rounded-pill px-3">
                          Editar
                        </a>

                        <a href="{{ url_for('valor_disponibilidad_delete', id=it.id) }}"
                           class="btn btn-danger btn-sm rounded-pill px-3"
                           onclick="return confirm('¿Eliminar este registro?');">
                          Eliminar
                        </a>

                      {% else %}

                        <span class="text-muted small">Solo lectura</span>

                      {% endif %}

                    </td>

                  </tr>

                {% endfor %}

                {% if items|length == 0 %}
                  <tr>
                    <td colspan="6" class="text-center text-muted py-4">
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

      .valdisp-shell{
        width:96%;
        max-width:1600px;
        margin:10px auto 24px auto;
      }

      .valdisp-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:95px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .valdisp-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .valdisp-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .valdisp-header-overlay::before{
        content:"🕒";
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
      }

      .valdisp-header-text{
        max-width:1100px;
        width:100%;
      }

      .valdisp-header-text::before{
        content:"SGSI · Valoración de Disponibilidad";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .valdisp-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .valdisp-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .valdisp-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin:10px 0 14px;
        flex-wrap:wrap;
      }

      .valdisp-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .valdisp-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .valdisp-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .valdisp-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .valdisp-card-body{
        padding:18px;
      }

      .valdisp-card .form-label{
        font-weight:800;
        color:#25324a;
        font-size:.78rem;
      }

      .valdisp-card .form-control,
      .valdisp-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .valdisp-card textarea{
        min-height:70px;
      }

      .valdisp-card .form-control:focus,
      .valdisp-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }

      .valdisp-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .valdisp-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .valdisp-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .valdisp-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      .valdisp-table-wrap{
        max-height:70vh;
        overflow:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#fff;
      }

      .valdisp-table{
        width:100%;
        min-width:1100px;
      }

      .valdisp-table th,
      .valdisp-table td{
        font-size:.78rem;
        padding:9px;
        word-break:break-word;
      }

      .valdisp-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#fff !important;
        font-weight:900;
        text-align:center;
      }

      .valdisp-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .valdisp-table tbody tr:hover{
        background:#eef6ff;
      }

      .badge{
        border-radius:999px;
        font-size:.72rem;
        padding:.38rem .65rem;
        font-weight:900;
      }

      .btn.rounded-pill{
        border-radius:999px !important;
      }

      .valdisp-card .btn{
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        font-weight:900;
      }

      @media (max-width:992px){
        .valdisp-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .valdisp-header-card{
          min-height:88px;
        }

        .valdisp-title{
          font-size:1.20rem;
        }

        .valdisp-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .valdisp-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .valdisp-header-overlay::before{
          margin:0;
        }

        .valdisp-header-actions .btn,
        .valdisp-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        edit_item=edit_item,
        items=items,
        solo_lectura=solo_lectura
    )
    return render_template_string(BASE, content=Markup(inner))

@app.route('/valor_disponibilidad/delete')
@login_required
def valor_disponibilidad_delete():
    user = User.query.filter_by(username=session['username']).first()
    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros de la tabla de disponibilidad.", "danger")
        return redirect(url_for('valor_disponibilidad'))
    
    rid = request.args.get('id', type=int)
    it = ValoracionDisponibilidad.query.get(rid)
    if it:
        db.session.delete(it)
        db.session.commit()
        flash("Eliminado correctamente.", "success")
    else:
        flash("Registro no encontrado.", "danger")
    return redirect(url_for('valor_disponibilidad'))

# =========================
# Valor Criticidad del Activo
# =========================

@app.route('/valor_criticidad_activo', methods=['GET', 'POST'])
@login_required
def valor_criticidad_activo():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores"):
            flash("No tiene permiso para ver los registros de proveedores.", "danger")
            return redirect(url_for('proveedores_menu'))
        read_only = False

    # 3) Definir si es solo lectura (auditor)
    solo_lectura = (user.role == 'auditor')

    # 5) Crear / Editar: solo si NO es solo lectura
    if request.method == 'POST' and not solo_lectura:
        rid = request.form.get('id')
        nivel_texto = (request.form.get('nivel_texto') or "").strip()
        try:
            nivel_num = int(request.form.get('nivel_num') or 0)
        except ValueError:
            nivel_num = 0

        if not nivel_texto:
            flash("El campo 'Nivel de Criticidad' (texto) es obligatorio.", "danger")
            return redirect(url_for('valor_criticidad_activo'))
        if nivel_num < 1 or nivel_num > 5:
            flash("El 'Nivel de criticidad' numérico debe estar entre 1 y 5.", "danger")
            return redirect(url_for('valor_criticidad_activo'))

        if rid:
            it = ValoracionCriticidadActivo.query.get(int(rid))
            if not it:
                flash("Registro no encontrado.", "danger")
                return redirect(url_for('valor_criticidad_activo'))
        else:
            it = ValoracionCriticidadActivo()

        it.nivel_texto = nivel_texto
        it.nivel_num = nivel_num

        db.session.add(it)
        db.session.commit()
        flash("Guardado correctamente.", "success")
        return redirect(url_for('valor_criticidad_activo'))

    # GET: listar y soportar edición
    edit_id = request.args.get('edit', type=int)
    edit_item = ValoracionCriticidadActivo.query.get(edit_id) if edit_id else None
    items = ValoracionCriticidadActivo.query.order_by(
        ValoracionCriticidadActivo.nivel_num.asc(),
        ValoracionCriticidadActivo.id.desc()
    ).all()

    html = """
    <div class="valcrit-shell">

      <!-- CABECERA -->
      <div class="valcrit-header-card">
        <div class="valcrit-header-overlay">
          <div class="valcrit-header-text">
            <h3 class="valcrit-title m-0">Niveles de Criticidad del Activo</h3>
            <div class="valcrit-subtitle">
              Configuración de niveles de criticidad para la valoración de activos del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="valcrit-header-actions">
        
      </div>

      <!-- FORMULARIO -->
      {% if not solo_lectura %}
      <div class="valcrit-card mb-3">
        <div class="valcrit-card-body">
          <form method="post" action="{{ url_for('valor_criticidad_activo') }}">
            {% if edit_item %}
              <input type="hidden" name="id" value="{{ edit_item.id }}">
            {% endif %}

            <div class="row g-3">

              <div class="col-md-3">
                <label class="form-label">Nivel de criticidad (numérico 1–5)</label>
                <input type="number"
                       name="nivel_num"
                       class="form-control"
                       min="1"
                       max="5"
                       required
                       value="{{ edit_item.nivel_num if edit_item else '' }}"
                       placeholder="1 a 5">
              </div>

              <div class="col-md-9">
                <label class="form-label">Nivel de Criticidad (texto)</label>
                <input type="text"
                       name="nivel_texto"
                       class="form-control"
                       required
                       placeholder="Bajo / Medio / Alto / Crítico / etc."
                       value="{{ edit_item.nivel_texto if edit_item else '' }}">
              </div>

            </div>

            <div class="valcrit-bottom-actions">
              <button type="submit" class="btn btn-success rounded-pill px-4 fw-bold">
                {% if edit_item %}Guardar cambios{% else %}Agregar{% endif %}
              </button>

              {% if edit_item %}
                <a href="{{ url_for('valor_criticidad_activo') }}"
                   class="btn rounded-pill px-4 fw-bold valcrit-cancel-btn">
                  Cancelar
                </a>
              {% endif %}
            </div>

          </form>
        </div>
      </div>
      {% endif %}

      <!-- TABLA -->
      <div class="valcrit-card">
        <div class="valcrit-card-body">

          <div class="valcrit-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-sm align-middle valcrit-table mb-0">
                <thead class="table-secondary">
                  <tr class="text-center">
                    <th style="width:14%">Nivel (numérico)</th>
                    <th>Nivel de Criticidad (texto)</th>
                    <th style="width:18%">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {% for it in items %}
                    <tr>
                      <td class="text-center"><b>{{ it.nivel_num }}</b></td>
                      <td>{{ it.nivel_texto }}</td>
                      <td class="text-center">
                        {% if not solo_lectura %}
                          <a href="{{ url_for('valor_criticidad_activo', edit=it.id) }}"
                             class="btn btn-warning btn-sm rounded-pill px-3">
                            Editar
                          </a>
                          <a href="{{ url_for('valor_criticidad_activo_delete', id=it.id) }}"
                             class="btn btn-danger btn-sm rounded-pill px-3"
                             onclick="return confirm('¿Eliminar este registro?');">
                            Eliminar
                          </a>
                        {% else %}
                          <span class="text-muted small">Solo lectura</span>
                        {% endif %}
                      </td>
                    </tr>
                  {% endfor %}

                  {% if items|length == 0 %}
                    <tr>
                      <td colspan="3" class="text-center text-muted py-4">
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

      .valcrit-shell{
        width:96%;
        max-width:1600px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HEADER SGSI MODERNO
      ========================= */
      .valcrit-header-card{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:16px 24px;
        min-height:95px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .valcrit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .valcrit-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .valcrit-header-overlay::before{
        content:"⚙️";
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
      }

      .valcrit-header-text{
        max-width:1100px;
        width:100%;
      }

      .valcrit-header-text::before{
        content:"SGSI · Valoración de Criticidad";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .valcrit-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .valcrit-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES
      ========================= */
      .valcrit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin:10px 0 14px;
        flex-wrap:wrap;
      }

      .valcrit-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .valcrit-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .valcrit-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      /* =========================
         CARD
      ========================= */
      .valcrit-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .valcrit-card-body{
        padding:18px;
      }

      /* =========================
         FORMULARIOS
      ========================= */
      .valcrit-card .form-label{
        font-weight:800;
        color:#25324a;
        font-size:.78rem;
      }

      .valcrit-card .form-control,
      .valcrit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .valcrit-card textarea{
        min-height:70px;
      }

      .valcrit-card .form-control:focus,
      .valcrit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }

      /* =========================
         TABLA
      ========================= */
      .valcrit-table-wrap{
        max-height:70vh;
        overflow:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#fff;
      }

      .valcrit-table{
        width:100%;
        min-width:900px;
      }

      .valcrit-table th,
      .valcrit-table td{
        font-size:.78rem;
        padding:9px;
        word-break:break-word;
      }

      .valcrit-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#fff !important;
        font-weight:900;
        text-align:center;
      }

      .valcrit-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .valcrit-table tbody tr:hover{
        background:#eef6ff;
      }

      /* =========================
         BOTONES INFERIORES
      ========================= */
      .valcrit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .valcrit-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
      }

      .valcrit-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .valcrit-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      /* =========================
         RESPONSIVE
      ========================= */
      @media (max-width:992px){
        .valcrit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .valcrit-title{
          font-size:1.20rem;
        }

        .valcrit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .valcrit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .valcrit-header-overlay::before{
          margin:0;
        }

        .valcrit-header-actions .btn,
        .valcrit-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        edit_item=edit_item,
        items=items,
        solo_lectura=solo_lectura
    )
    return render_template_string(BASE, content=Markup(inner))

@app.route('/valor_criticidad_activo/delete')
@login_required
def valor_criticidad_activo_delete():
    user = User.query.filter_by(username=session['username']).first()
    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar niveles de criticidad del activo.", "danger")
        return redirect(url_for('valor_criticidad_activo'))
    
    rid = request.args.get('id', type=int)
    it = ValoracionCriticidadActivo.query.get(rid)
    if it:
        db.session.delete(it)
        db.session.commit()
        flash("Eliminado correctamente.", "success")
    else:
        flash("Registro no encontrado.", "danger")
    return redirect(url_for('valor_criticidad_activo'))



# ============================================================================================================================================
#                                                               Fin del Módulo Gestión de Activos
# ============================================================================================================================================

# ==========================================================================================================================================
#                                                       Módulo de Gestión de Accesos
# ==========================================================================================================================================

# ==========================
# ENTRADA DIRECTA — Gestión de Accesos
# ==========================
@app.route('/accesos_menu')
@login_required
def accesos_menu():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Gestión de Accesos"):
        flash("No tiene permiso para acceder al módulo de Gestión de Accesos.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('accesos_matriz'))


# =================================
# Estados de los usuarios
# =================================
@app.route('/accesos_estados', methods=['GET', 'POST'])
@login_required
def accesos_estados():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede acceder al submódulo de estados de usuarios.", "danger")
        return redirect(url_for('accesos_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Accesos"):
        flash("No tiene permiso para gestionar estados de usuarios.", "danger")
        return redirect(url_for('accesos_matriz'))

    solo_lectura = False

    if request.method == 'POST' and not solo_lectura:
        accion = request.form.get('accion')

        if accion == 'crear':
            nombre = (request.form.get('nombre') or '').strip()
            if not nombre:
                flash("El nombre del estado es obligatorio.", "danger")
            else:
                if not EstadoUsuarioAcceso.query.filter_by(nombre=nombre).first():
                    db.session.add(EstadoUsuarioAcceso(nombre=nombre))
                    db.session.commit()
                    flash("Estado creado correctamente.", "success")
                else:
                    flash("Ese estado ya existe.", "warning")

        elif accion == 'eliminar':
            rid = request.form.get('id', type=int)
            est = EstadoUsuarioAcceso.query.get(rid)
            if est:
                en_uso = GestionAcceso.query.filter_by(estado_id=est.id).count()
                if en_uso > 0:
                    flash("No se puede eliminar el estado porque está en uso.", "danger")
                else:
                    db.session.delete(est)
                    db.session.commit()
                    flash("Estado eliminado.", "success")

        return redirect(url_for('accesos_estados'))

    estados = EstadoUsuarioAcceso.query.order_by(EstadoUsuarioAcceso.nombre.asc()).all()

    html = """
    <div class="accestado-shell">

      <div class="accestado-header-card">
        <div class="accestado-header-overlay">
          <div class="accestado-header-text">
            <h3 class="accestado-title m-0">Estados de los Usuarios</h3>
            <div class="accestado-subtitle">
              Configuración de estados para la gestión de accesos de usuarios del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="accestado-header-actions">
        <a href="{{ url_for('accesos_matriz') }}"
           class="btn rounded-pill px-4 fw-bold accestado-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="accestado-card mb-3">
        <div class="accestado-card-body">
          <form method="post" class="row g-3 align-items-end">

            <div class="col-md-6">
              <label class="form-label">Nombre del estado</label>
              <input name="nombre" class="form-control" {% if solo_lectura %}disabled{% endif %}>
            </div>

            <div class="col-md-6">
              {% if not solo_lectura %}
                <button class="btn btn-success rounded-pill px-4 fw-bold"
                        name="accion"
                        value="crear"
                        type="submit">
                  Agregar
                </button>
              {% else %}
                <span class="text-warning small">Solo lectura.</span>
              {% endif %}
            </div>

          </form>
        </div>
      </div>

      <div class="accestado-card">
        <div class="accestado-card-body">
          <div class="accestado-table-wrap">
            <div class="table-responsive">
              <table class="table table-sm table-bordered align-middle mb-0 accestado-table">
                <thead class="table-secondary">
                  <tr>
                    <th>Estado</th>
                    <th style="width:20%">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {% for e in estados %}
                    <tr>
                      <td>{{ e.nombre }}</td>
                      <td>
                        {% if not solo_lectura %}
                          <form method="post"
                                style="display:inline;"
                                onsubmit="return confirm('¿Eliminar este estado?');">
                            <input type="hidden" name="id" value="{{ e.id }}">
                            <button class="btn btn-danger btn-sm rounded-pill px-3"
                                    name="accion"
                                    value="eliminar"
                                    type="submit">
                              Eliminar
                            </button>
                          </form>
                        {% else %}
                          <span class="text-muted small">Solo lectura</span>
                        {% endif %}
                      </td>
                    </tr>
                  {% endfor %}

                  {% if estados|length == 0 %}
                    <tr>
                      <td colspan="2" class="text-center text-muted py-4">
                        Sin estados configurados
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

      .accestado-shell{
        width:96%;
        max-width:1350px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HEADER SGSI UNIFICADO
      ========================= */
      .accestado-header-card{
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

      .accestado-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .accestado-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .accestado-header-overlay::before{
        content:"👤";
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
      }

      .accestado-header-text{
        width:100%;
      }

      .accestado-header-text::before{
        content:"SGSI · Estado de Accesos";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .accestado-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .accestado-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES SUPERIORES
      ========================= */
      .accestado-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .accestado-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .accestado-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .accestado-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD PRINCIPAL
      ========================= */
      .accestado-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .accestado-card-body{
        padding:18px;
      }

      /* =========================
         FORMULARIOS
      ========================= */
      .accestado-card .form-label{
        font-weight:800;
        color:#25324a;
        font-size:.78rem;
      }

      .accestado-card .form-control{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .accestado-card .form-control:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }

      /* =========================
         TABLA PRO SGSI
      ========================= */
      .accestado-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid rgba(0,0,0,.08);
        border-radius:14px;
        background:#ffffff;
      }

      .accestado-table{
        width:100%;
        min-width:750px;
      }

      .accestado-table th,
      .accestado-table td{
        white-space:normal;
        word-break:break-word;
        vertical-align:middle;
        font-size:.82rem;
        padding:10px;
      }

      .accestado-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:#dbeafe !important;
        color:#0f172a;
        font-weight:900;
        text-align:center;
      }

      .accestado-table tbody tr:hover{
        background:rgba(59,130,246,.06);
      }

      /* =========================
         RESPONSIVE
      ========================= */
      @media (max-width:992px){
        .accestado-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .accestado-header-card{
          min-height:88px;
        }

        .accestado-title{
          font-size:1.20rem;
        }

        .accestado-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .accestado-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .accestado-header-overlay::before{
          margin:0;
        }

        .accestado-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(html, estados=estados, solo_lectura=solo_lectura)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Agregar acceso
# ==========================
@app.route('/accesos/new', methods=['GET','POST'])
@login_required
def accesos_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar accesos.", "danger")
        return redirect(url_for('accesos_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Accesos"):
        flash("No tiene permiso para agregar accesos.", "danger")
        return redirect(url_for('accesos_matriz'))

    areas   = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()
    estados = EstadoUsuarioAcceso.query.order_by(EstadoUsuarioAcceso.nombre.asc()).all()
    niveles = ["Alto", "Medio", "Bajo"]

    if request.method == 'POST':
        it = GestionAcceso(
            id_acceso        = (request.form.get('id_acceso') or '').strip(),
            rol_usuario      = (request.form.get('rol_usuario') or '').strip(),
            usuario          = (request.form.get('usuario') or '').strip(),
            area_id          = request.form.get('area_id', type=int),
            aplicacion       = (request.form.get('aplicacion') or '').strip(),
            tipo_acceso      = (request.form.get('tipo_acceso') or '').strip(),
            rol_tecnico_app  = (request.form.get('rol_tecnico_app') or '').strip(),
            nivel_privilegio = (request.form.get('nivel_privilegio') or '').strip(),
            justificacion    = (request.form.get('justificacion') or '').strip(),
            aprobado_por     = (request.form.get('aprobado_por') or '').strip(),
            gestionado_por   = (request.form.get('gestionado_por') or '').strip(),
            fecha_alta       = request.form.get('fecha_alta') or '',
            fecha_baja       = request.form.get('fecha_baja') or '',
            estado_id        = request.form.get('estado_id', type=int),
            evidencia        = (request.form.get('evidencia') or '').strip(),
        )

        db.session.add(it)

        files = request.files.getlist('evidencias')
        for f in files:
            if not f or not f.filename:
                continue
            if not is_allowed_pdf(f.filename):
                flash(f"Archivo no permitido (solo PDF): {f.filename}", "danger")
                continue

            store_name = unique_store_name(f.filename)
            path = os.path.join(app.config['UPLOAD_GESTION_ACCESOS_DIR'], store_name)
            f.save(path)

            ev = GestionAccesoEvidencia(
                registro=it,
                filename=store_name,
                original_name=secure_filename(f.filename),
                mime='application/pdf',
                size=os.path.getsize(path)
            )
            db.session.add(ev)

        db.session.commit()
        flash("Acceso registrado correctamente.", "success")
        return redirect(url_for('accesos_matriz'))

    html = """
    <div class="accesoadd-shell">

      <div class="accesoadd-header-card">
        <div class="accesoadd-header-overlay">
          <div class="accesoadd-header-text">
            <h3 class="accesoadd-title m-0">Agregar Acceso</h3>
            <div class="accesoadd-subtitle">
              Registro y gestión de accesos de usuarios, privilegios, aprobaciones y evidencias del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="accesoadd-header-actions">
        <a href="{{ url_for('accesos_matriz') }}"
           class="btn rounded-pill px-4 fw-bold accesoadd-back-btn">
          ⬅ Volver a la Matriz
        </a>


      </div>

      <div class="accesoadd-card">
        <div class="accesoadd-card-body">
          <form method="post" enctype="multipart/form-data">
            <div class="row g-3">

              <div class="col-md-3">
                <label class="form-label">ID</label>
                <input class="form-control" name="id_acceso" required>
              </div>

              <div class="col-md-3">
                <label class="form-label">Rol del Usuario</label>
                <input class="form-control" name="rol_usuario">
              </div>

              <div class="col-md-3">
                <label class="form-label">Usuario</label>
                <input class="form-control" name="usuario">
              </div>

              <div class="col-md-3">
                <label class="form-label">Área</label>
                <select name="area_id" class="form-select">
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}">{{ a.area }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Aplicación / Sistema</label>
                <input class="form-control" name="aplicacion">
              </div>

              <div class="col-md-4">
                <label class="form-label">Tipo de Acceso</label>
                <input class="form-control" name="tipo_acceso">
              </div>

              <div class="col-md-4">
                <label class="form-label">Rol Técnico en App</label>
                <input class="form-control" name="rol_tecnico_app">
              </div>

              <div class="col-md-4">
                <label class="form-label">Nivel de Privilegio</label>
                <select name="nivel_privilegio" class="form-select">
                  <option value="">-- Seleccione --</option>
                  {% for n in niveles %}
                    <option>{{ n }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Justificación del Acceso</label>
                <textarea class="form-control" name="justificacion" rows="2"></textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Aprobado por</label>
                <input class="form-control" name="aprobado_por">
              </div>

              <div class="col-md-4">
                <label class="form-label">Gestionado por</label>
                <input class="form-control" name="gestionado_por">
              </div>

              <div class="col-md-2">
                <label class="form-label">Fecha de Alta</label>
                <input type="date" class="form-control" name="fecha_alta">
              </div>

              <div class="col-md-2">
                <label class="form-label">Fecha de Baja</label>
                <input type="date" class="form-control" name="fecha_baja">
              </div>

              <div class="col-md-4">
                <label class="form-label">Estado</label>
                <select name="estado_id" class="form-select">
                  <option value="">-- Seleccione --</option>
                  {% for e in estados %}
                    <option value="{{ e.id }}">{{ e.nombre }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Evidencia (texto)</label>
                <textarea class="form-control" name="evidencia" rows="2"></textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Evidencias PDF</label>
                <input type="file" name="evidencias" class="form-control" accept=".pdf" multiple>
                <small class="text-muted">Puede adjuntar uno o varios PDFs.</small>
              </div>

            </div>

            <div class="accesoadd-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>
              <a href="{{ url_for('accesos_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold accesoadd-cancel-btn">
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

      .accesoadd-shell{
        width:96%;
        max-width:1550px;
        margin:10px auto 24px auto;
      }

      .accesoadd-header-card{
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

      .accesoadd-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .accesoadd-header-overlay{
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

      .accesoadd-header-overlay::before{
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

      .accesoadd-header-text{
        max-width:1100px;
        width:100%;
      }

      .accesoadd-header-text::before{
        content:"SGSI · Gestión de Accesos";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .accesoadd-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .accesoadd-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .accesoadd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .accesoadd-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .accesoadd-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .accesoadd-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .accesoadd-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .accesoadd-card-body{
        padding:18px;
      }

      .accesoadd-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .accesoadd-card .form-control,
      .accesoadd-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .accesoadd-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .accesoadd-card .form-control:focus,
      .accesoadd-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }

      .accesoadd-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .accesoadd-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .accesoadd-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .accesoadd-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .accesoadd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .accesoadd-header-card{
          min-height:88px;
        }

        .accesoadd-title{
          font-size:1.20rem;
        }

        .accesoadd-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .accesoadd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .accesoadd-header-overlay::before{
          margin:0;
        }

        .accesoadd-header-actions .btn,
        .accesoadd-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, areas=areas, estados=estados, niveles=niveles)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Matriz de accesos
# ==========================
@app.route('/accesos_matriz')
@login_required
def accesos_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Gestión de Accesos"):
            flash("No tiene permiso para ver la matriz de accesos.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    filtro_usuario = (request.args.get('usuario') or '').strip()
    filtro_area = (request.args.get('area') or '').strip()
    filtro_tipo_acceso = (request.args.get('tipo_acceso') or '').strip()
    filtro_nivel_privilegio = (request.args.get('nivel_privilegio') or '').strip()
    filtro_estado = (request.args.get('estado') or '').strip()

    query = (
        GestionAcceso.query
        .options(
            selectinload(GestionAcceso.area),
            selectinload(GestionAcceso.estado),
            selectinload(GestionAcceso.evidencias)
        )
    )

    if filtro_usuario:
        query = query.filter(GestionAcceso.usuario == filtro_usuario)

    if filtro_area:
        query = query.filter(GestionAcceso.area.has(area=filtro_area))

    if filtro_tipo_acceso:
        query = query.filter(GestionAcceso.tipo_acceso == filtro_tipo_acceso)

    if filtro_nivel_privilegio:
        query = query.filter(GestionAcceso.nivel_privilegio == filtro_nivel_privilegio)

    if filtro_estado:
        query = query.filter(GestionAcceso.estado.has(nombre=filtro_estado))

    items = query.order_by(GestionAcceso.id.desc()).all()

    opciones_usuario = [
        x[0] for x in db.session.query(GestionAcceso.usuario)
        .filter(GestionAcceso.usuario.isnot(None))
        .filter(GestionAcceso.usuario != '')
        .distinct()
        .order_by(GestionAcceso.usuario.asc())
        .all()
    ]

    opciones_tipo_acceso = [
        x[0] for x in db.session.query(GestionAcceso.tipo_acceso)
        .filter(GestionAcceso.tipo_acceso.isnot(None))
        .filter(GestionAcceso.tipo_acceso != '')
        .distinct()
        .order_by(GestionAcceso.tipo_acceso.asc())
        .all()
    ]

    opciones_nivel_privilegio = [
        x[0] for x in db.session.query(GestionAcceso.nivel_privilegio)
        .filter(GestionAcceso.nivel_privilegio.isnot(None))
        .filter(GestionAcceso.nivel_privilegio != '')
        .distinct()
        .order_by(GestionAcceso.nivel_privilegio.asc())
        .all()
    ]

    opciones_area = sorted({
        it.area.area.strip()
        for it in (
            GestionAcceso.query
            .options(selectinload(GestionAcceso.area))
            .all()
        )
        if it.area and it.area.area and it.area.area.strip()
    })

    opciones_estado = sorted({
        it.estado.nombre.strip()
        for it in (
            GestionAcceso.query
            .options(selectinload(GestionAcceso.estado))
            .all()
        )
        if it.estado and it.estado.nombre and it.estado.nombre.strip()
    })

    total_filtrados = len(items)
    total_general = GestionAcceso.query.count()

    html = """
    <div class="accesomat-shell">

      <div class="accesomat-header-card">
        <div class="accesomat-header-overlay">
          <div class="accesomat-header-text">
            <h3 class="accesomat-title m-0">Gestión de Accesos</h3>
            <div class="accesomat-subtitle">
              Visualización resumida de accesos, privilegios, estados y evidencias del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="accesomat-header-actions">
        

        {% if not read_only %}
          <a href="{{ url_for('accesos_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            ➕ Agregar Acceso
          </a>

          <a href="{{ url_for('accesos_estados') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            👤 Estados de Usuarios
          </a>
        {% else %}
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            ➕ Agregar Acceso
          </button>

          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            👤 Estados de Usuarios
          </button>
        {% endif %}
      </div>

      <div class="accesomat-filter-card">
        <div class="accesomat-filter-body">
          <form method="get" action="{{ url_for('accesos_matriz') }}">
            <div class="row g-2 align-items-end">

              <div class="col-md-3">
                <label class="form-label fw-bold">Usuario</label>
                <select name="usuario" class="form-select rounded-3">
                  <option value="">Todos</option>
                  {% for op in opciones_usuario %}
                    <option value="{{ op }}" {% if filtro_usuario == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label fw-bold">Área</label>
                <select name="area" class="form-select rounded-3">
                  <option value="">Todas</option>
                  {% for op in opciones_area %}
                    <option value="{{ op }}" {% if filtro_area == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label fw-bold">Tipo de Acceso</label>
                <select name="tipo_acceso" class="form-select rounded-3">
                  <option value="">Todos</option>
                  {% for op in opciones_tipo_acceso %}
                    <option value="{{ op }}" {% if filtro_tipo_acceso == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label fw-bold">Nivel de Privilegio</label>
                <select name="nivel_privilegio" class="form-select rounded-3">
                  <option value="">Todos</option>
                  {% for op in opciones_nivel_privilegio %}
                    <option value="{{ op }}" {% if filtro_nivel_privilegio == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label fw-bold">Estado</label>
                <select name="estado" class="form-select rounded-3">
                  <option value="">Todos</option>
                  {% for op in opciones_estado %}
                    <option value="{{ op }}" {% if filtro_estado == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-12">
                <div class="d-flex gap-2 flex-wrap justify-content-end">
                  <button type="submit" class="btn btn-primary rounded-pill px-4 fw-bold">Filtrar</button>
                  <a href="{{ url_for('accesos_matriz') }}" class="btn btn-secondary rounded-pill px-4 fw-bold">Limpiar</a>
                </div>
              </div>

            </div>
          </form>
        </div>
      </div>

      <div class="accesomat-card">
        <div class="accesomat-topbar">
          <div>
            <h5 class="accesomat-top-title mb-1">Resumen de registros</h5>
            <div class="accesomat-top-note">
              La matriz presenta los campos más importantes. Para revisar el registro completo usa el botón <strong>Ver detalle</strong>.
            </div>
          </div>
          <div class="accesomat-counter-badge">
            Registros filtrados: {{ total_filtrados }} | Total general: {{ total_general }}
          </div>
        </div>

        <div class="accesomat-card-body">
          <div class="accesomat-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-hover align-middle accesomat-table mb-0">
                <colgroup>
                  <col style="width: 8%;">
                  <col style="width: 12%;">
                  <col style="width: 12%;">
                  <col style="width: 12%;">
                  <col style="width: 12%;">
                  <col style="width: 12%;">
                  <col style="width: 10%;">
                  <col style="width: 10%;">
                  <col style="width: 12%;">
                </colgroup>

                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Usuario</th>
                    <th>Área</th>
                    <th>Aplicación</th>
                    <th>Tipo de Acceso</th>
                    <th>Nivel de Privilegio</th>
                    <th>Estado</th>
                    <th>Evidencias</th>
                    <th class="accesomat-col-acciones">Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  {% for it in items %}
                    <tr>
                      <td class="text-center">{{ it.id_acceso or '—' }}</td>
                      <td class="accesomat-cell-main">
                        <div class="accesomat-main-text">{{ it.usuario or '—' }}</div>
                      </td>
                      <td>{{ it.area.area if it.area else '—' }}</td>
                      <td>{{ it.aplicacion or '—' }}</td>
                      <td>{{ it.tipo_acceso or '—' }}</td>
                      <td class="text-center">{{ it.nivel_privilegio or '—' }}</td>
                      <td class="text-center">
                        {{ it.estado.nombre if it.estado else '—' }}
                      </td>
                      <td class="text-center">
                        {% set total_ev = it.evidencias|length %}
                        {% if total_ev > 0 %}
                          <span class="badge bg-primary">{{ total_ev }} PDF{{ 's' if total_ev != 1 else '' }}</span>
                        {% else %}
                          <span class="text-muted">—</span>
                        {% endif %}
                      </td>

                      <td class="text-center accesomat-col-acciones">
                        <div class="accesomat-actions-wrap">
                          <a href="{{ url_for('accesos_detalle', id=it.id) }}"
                             class="btn btn-info btn-sm rounded-pill accesomat-btn-action fw-bold text-white">
                            Ver detalle
                          </a>

                          {% if not read_only %}
                            <a href="{{ url_for('accesos_edit', id=it.id) }}"
                               class="btn btn-warning btn-sm rounded-pill accesomat-btn-action fw-bold">
                              Editar
                            </a>

                            <a href="{{ url_for('accesos_delete', id=it.id) }}"
                               class="btn btn-danger btn-sm rounded-pill accesomat-btn-action fw-bold"
                               onclick="return confirm('¿Eliminar este acceso?');">
                              Eliminar
                            </a>
                          {% else %}
                            <span class="badge bg-secondary accesomat-badge-readonly">Solo lectura</span>
                          {% endif %}
                        </div>
                      </td>
                    </tr>
                  {% endfor %}

                  {% if items|length == 0 %}
                    <tr>
                      <td colspan="9" class="text-center text-muted py-5">
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

      .accesomat-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .accesomat-header-card{
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

      .accesomat-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .accesomat-header-overlay{
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

      .accesomat-header-overlay::before{
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

      .accesomat-header-text{
        max-width:1100px;
        width:100%;
      }

      .accesomat-header-text::before{
        content:"SGSI · Matriz de Accesos";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .accesomat-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .accesomat-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .accesomat-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .accesomat-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .accesomat-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .accesomat-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .accesomat-filter-card,
      .accesomat-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .accesomat-filter-card{
        margin-bottom:14px;
      }

      .accesomat-filter-body{
        padding:14px 16px;
      }

      .accesomat-filter-body .form-label{
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
        font-weight:800;
      }

      .accesomat-filter-body .form-select,
      .accesomat-filter-body .form-control{
        min-height:36px;
        height:36px;
        font-size:.80rem;
        border:1px solid #d9e3f0;
        border-radius:9px;
        background:#f8fafc;
        box-shadow:none;
      }

      .accesomat-filter-body .btn{
        border-radius:10px !important;
        min-height:36px;
        padding:7px 18px !important;
        font-size:.80rem;
        font-weight:900;
      }

      .accesomat-filter-body .form-select:focus,
      .accesomat-filter-body .form-control:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .accesomat-topbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:14px 16px 0 16px;
        flex-wrap:wrap;
      }

      .accesomat-top-title{
        color:#0f172a;
        font-weight:950;
        font-size:.92rem;
      }

      .accesomat-top-note{
        color:#475569;
        font-size:.78rem;
      }

      .accesomat-counter-badge{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:7px 14px;
        font-size:.78rem;
        box-shadow:0 8px 16px rgba(15,23,42,.16);
      }

      .accesomat-card-body{
        padding:12px 16px 16px 16px;
      }

      .accesomat-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#fff;
      }

      .accesomat-table{
        min-width:1500px;
        table-layout:fixed;
        margin-bottom:0;
      }

      .accesomat-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border-color:rgba(0,0,0,.08);
      }

      .accesomat-table th,
      .accesomat-table td{
        vertical-align:top;
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .accesomat-table td{
        border-bottom:1px solid #e5edf7;
      }

      .accesomat-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .accesomat-table tbody tr:hover{
        background:#eef6ff;
      }

      .accesomat-cell-main .accesomat-main-text{
        font-weight:900;
        color:#0f172a;
      }

      .accesomat-col-acciones,
      .accesomat-table th.accesomat-col-acciones,
      .accesomat-table td.accesomat-col-acciones{
        min-width:190px !important;
        width:190px !important;
        text-align:center;
        vertical-align:middle;
      }

      .accesomat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .accesomat-btn-action{
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

      .accesomat-badge-readonly{
        font-size:.70rem;
        padding:5px 10px;
        border-radius:999px;
        white-space:nowrap;
        font-weight:900;
      }

      @media (max-width:992px){
        .accesomat-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .accesomat-header-card{
          min-height:88px;
        }

        .accesomat-title{
          font-size:1.20rem;
        }

        .accesomat-filter-body,
        .accesomat-card-body{
          padding:12px;
        }

        .accesomat-topbar{
          padding:12px 14px 0 14px;
        }
      }

      @media (max-width:768px){
        .accesomat-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .accesomat-header-overlay::before{
          margin:0;
        }

        .accesomat-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        opciones_usuario=opciones_usuario,
        opciones_area=opciones_area,
        opciones_tipo_acceso=opciones_tipo_acceso,
        opciones_nivel_privilegio=opciones_nivel_privilegio,
        opciones_estado=opciones_estado,
        filtro_usuario=filtro_usuario,
        filtro_area=filtro_area,
        filtro_tipo_acceso=filtro_tipo_acceso,
        filtro_nivel_privilegio=filtro_nivel_privilegio,
        filtro_estado=filtro_estado,
        total_filtrados=total_filtrados,
        total_general=total_general
    )
    return render_template_string(BASE, content=Markup(inner))

# ==========================
# Detalle de acceso
# ==========================

@app.route('/accesos/detalle/<int:id>')
@login_required
def accesos_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Gestión de Accesos"):
            flash("No tiene permiso para ver el detalle del acceso.", "danger")
            return redirect(url_for('accesos_menu'))
        read_only = False

    item = (
        GestionAcceso.query
        .options(
            selectinload(GestionAcceso.area),
            selectinload(GestionAcceso.estado),
            selectinload(GestionAcceso.evidencias)
        )
        .get_or_404(id)
    )

    html = """
    <div class="accdet-shell">

      <!-- CABECERA -->
      <div class="accdet-header-card">
        <div class="accdet-header-overlay">
          <div class="accdet-header-text">
            <h3 class="accdet-title m-0">Detalle del Acceso</h3>
            <div class="accdet-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <!-- BOTONES -->
      <div class="accdet-header-actions">
        <a href="{{ url_for('accesos_matriz') }}"
           class="btn rounded-pill px-4 fw-bold accdet-back-btn">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('accesos_edit', id=item.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="accdet-card">
        <div class="accdet-card-body">

          <div class="accdet-section">
            <div class="accdet-section-title">Información principal</div>
            <div class="row g-3">

              <div class="col-md-3">
                <div class="accdet-field">
                  <div class="accdet-label">ID</div>
                  <div class="accdet-value">{{ item.id_acceso or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="accdet-field">
                  <div class="accdet-label">Rol del Usuario</div>
                  <div class="accdet-value">{{ item.rol_usuario or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="accdet-field">
                  <div class="accdet-label">Usuario</div>
                  <div class="accdet-value">{{ item.usuario or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="accdet-field">
                  <div class="accdet-label">Área</div>
                  <div class="accdet-value">{{ item.area.area if item.area else '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="accdet-field">
                  <div class="accdet-label">Aplicación / Sistema</div>
                  <div class="accdet-value">{{ item.aplicacion or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="accdet-field">
                  <div class="accdet-label">Tipo de Acceso</div>
                  <div class="accdet-value">{{ item.tipo_acceso or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="accdet-field">
                  <div class="accdet-label">Rol Técnico en App</div>
                  <div class="accdet-value">{{ item.rol_tecnico_app or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <div class="accdet-section">
            <div class="accdet-section-title">Privilegios y seguimiento</div>
            <div class="row g-3">

              <div class="col-md-3">
                <div class="accdet-field">
                  <div class="accdet-label">Nivel de Privilegio</div>
                  <div class="accdet-value">{{ item.nivel_privilegio or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="accdet-field">
                  <div class="accdet-label">Estado</div>
                  <div class="accdet-value">{{ item.estado.nombre if item.estado else '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="accdet-field">
                  <div class="accdet-label">Fecha de Alta</div>
                  <div class="accdet-value">{{ item.fecha_alta or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="accdet-field">
                  <div class="accdet-label">Fecha de Baja</div>
                  <div class="accdet-value">{{ item.fecha_baja or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="accdet-field">
                  <div class="accdet-label">Aprobado por</div>
                  <div class="accdet-value">{{ item.aprobado_por or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="accdet-field">
                  <div class="accdet-label">Gestionado por</div>
                  <div class="accdet-value">{{ item.gestionado_por or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <div class="accdet-section">
            <div class="accdet-section-title">Justificación y evidencias</div>
            <div class="row g-3">

              <div class="col-md-12">
                <div class="accdet-field">
                  <div class="accdet-label">Justificación del Acceso</div>
                  <div class="accdet-value">{{ item.justificacion or '—' }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="accdet-field">
                  <div class="accdet-label">Evidencia (texto)</div>
                  <div class="accdet-value">{{ item.evidencia or '—' }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="accdet-field">
                  <div class="accdet-label">Evidencias PDF</div>

                  {% if item.evidencias %}
                    <div class="accdet-ev-grid">
                      {% for ev in item.evidencias %}
                        <div class="accdet-file-card">
                          <div class="accdet-file-left">
                            <div class="accdet-file-icon">PDF</div>
                            <div class="accdet-file-meta">
                              <a href="{{ url_for('accesos_evidencia_view', evi_id=ev.id, next='accesos_detalle', reg_id=item.id) }}" class="accdet-file-name">
                                {{ ev.original_name }}
                              </a>
                              <div class="accdet-file-size">{{ (ev.size or 0) // 1024 }} KB</div>
                            </div>
                          </div>
                        </div>
                      {% endfor %}
                    </div>
                  {% else %}
                    <div class="accdet-value">—</div>
                  {% endif %}
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

      .accdet-shell{
        width:96%;
        max-width:1200px;
        margin:10px auto 24px auto;
      }

      .accdet-header-card{
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

      .accdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .accdet-header-overlay{
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

      .accdet-header-overlay::before{
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

      .accdet-header-text{
        max-width:1000px;
        width:100%;
        transform:none;
      }

      .accdet-header-text::before{
        content:"SGSI · Detalle de Acceso";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .accdet-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .accdet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .accdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .accdet-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .accdet-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .accdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .accdet-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .accdet-card-body{
        padding:18px;
      }

      .accdet-section{
        margin-bottom:14px;
        background:#fff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .accdet-section:last-child{
        margin-bottom:0;
      }

      .accdet-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      .accdet-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        min-height:78px;
        height:100%;
      }

      .accdet-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .accdet-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .accdet-ev-grid{
        display:grid;
        gap:10px;
      }

      .accdet-file-card{
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

      .accdet-file-left{
        display:flex;
        align-items:center;
        gap:7px;
        min-width:0;
      }

      .accdet-file-icon{
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

      .accdet-file-meta{
        min-width:0;
      }

      .accdet-file-name{
        display:block;
        font-size:.78rem;
        font-weight:900;
        color:#1d4ed8;
        text-decoration:none;
        word-break:break-word;
      }

      .accdet-file-name:hover{
        text-decoration:underline;
      }

      .accdet-file-size{
        font-size:.70rem;
        color:#475569;
        margin-top:2px;
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
        .accdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .accdet-header-card{
          min-height:88px;
        }

        .accdet-title{
          font-size:1.20rem;
        }

        .accdet-card-body{
          padding:8px 7px;
        }

        .accdet-section{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .accdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .accdet-header-overlay::before{
          margin:0;
        }

        .accdet-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        item=item,
        read_only=read_only
    )
    return render_template_string(BASE, content=Markup(inner))

# ==========================
# Editar Accesos
# ==========================

@app.route('/accesos/edit/<int:id>', methods=['GET','POST'])
@login_required
def accesos_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Gestión de Accesos")
    ):
        flash("No tiene permiso para editar accesos.", "danger")
        return redirect(url_for('accesos_matriz'))

    item    = GestionAcceso.query.get_or_404(id)
    areas   = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()
    estados = EstadoUsuarioAcceso.query.order_by(EstadoUsuarioAcceso.nombre.asc()).all()
    niveles = ["Alto", "Medio", "Bajo"]

    if request.method == 'POST':
        item.id_acceso        = (request.form.get('id_acceso') or '').strip()
        item.rol_usuario      = (request.form.get('rol_usuario') or '').strip()
        item.usuario          = (request.form.get('usuario') or '').strip()
        item.area_id          = request.form.get('area_id', type=int)
        item.aplicacion       = (request.form.get('aplicacion') or '').strip()
        item.tipo_acceso      = (request.form.get('tipo_acceso') or '').strip()
        item.rol_tecnico_app  = (request.form.get('rol_tecnico_app') or '').strip()
        item.nivel_privilegio = (request.form.get('nivel_privilegio') or '').strip()
        item.justificacion    = (request.form.get('justificacion') or '').strip()
        item.aprobado_por     = (request.form.get('aprobado_por') or '').strip()
        item.gestionado_por   = (request.form.get('gestionado_por') or '').strip()
        item.fecha_alta       = request.form.get('fecha_alta') or ''
        item.fecha_baja       = request.form.get('fecha_baja') or ''
        item.estado_id        = request.form.get('estado_id', type=int)
        item.evidencia        = (request.form.get('evidencia') or '').strip()

        # Nuevas evidencias PDF
        files = request.files.getlist('evidencias')
        for f in files:
            if not f or not f.filename:
                continue
            if not is_allowed_pdf(f.filename):
                flash(f"Archivo no permitido (solo PDF): {f.filename}", "danger")
                continue

            upload_dir = app.config.get('UPLOAD_GESTION_ACCESOS_DIR')
            if not upload_dir:
                raise RuntimeError("No está configurada la carpeta UPLOAD_GESTION_ACCESOS_DIR.")

            os.makedirs(upload_dir, exist_ok=True)

            store_name = unique_store_name(f.filename)
            path = os.path.join(upload_dir, store_name)
            f.save(path)

            ev = GestionAccesoEvidencia(
                registro=item,
                filename=store_name,
                original_name=secure_filename(f.filename),
                mime='application/pdf',
                size=os.path.getsize(path)
            )
            db.session.add(ev)

        db.session.commit()
        flash("Acceso actualizado correctamente.", "success")
        return redirect(url_for('accesos_matriz'))

    html = """
    <div class="accesoedit-shell">

      <!-- CABECERA -->
      <div class="accesoedit-header-card">
        <div class="accesoedit-header-overlay">
          <div class="accesoedit-header-text">
            <h3 class="accesoedit-title m-0">Editar Acceso</h3>
            <div class="accesoedit-subtitle">
              Actualización de privilegios, roles, justificaciones, estados y evidencias de acceso del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="accesoedit-header-actions">
        <a href="{{ url_for('accesos_matriz') }}"
           class="btn rounded-pill px-5 fw-bold accesoedit-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <!-- TARJETA -->
      <div class="accesoedit-card">
        <div class="accesoedit-card-body">

          <form method="post" enctype="multipart/form-data">

            <div class="row g-3">

              <div class="col-md-3">
                <label class="form-label">ID</label>
                <input class="form-control" name="id_acceso" required value="{{ item.id_acceso or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Rol del Usuario</label>
                <input class="form-control" name="rol_usuario" value="{{ item.rol_usuario or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Usuario</label>
                <input class="form-control" name="usuario" value="{{ item.usuario or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Área</label>
                <select name="area_id" class="form-select">
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}" {% if item.area_id == a.id %}selected{% endif %}>
                      {{ a.area }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Aplicación / Sistema</label>
                <input class="form-control" name="aplicacion" value="{{ item.aplicacion or '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Tipo de Acceso</label>
                <input class="form-control" name="tipo_acceso" value="{{ item.tipo_acceso or '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Rol Técnico en App</label>
                <input class="form-control" name="rol_tecnico_app" value="{{ item.rol_tecnico_app or '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Nivel de Privilegio</label>
                <select name="nivel_privilegio" class="form-select">
                  <option value="">-- Seleccione --</option>
                  {% for n in niveles %}
                    <option value="{{ n }}" {% if (item.nivel_privilegio or '') == n %}selected{% endif %}>{{ n }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Justificación del Acceso</label>
                <textarea class="form-control" name="justificacion" rows="2">{{ item.justificacion or '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Aprobado por</label>
                <input class="form-control" name="aprobado_por" value="{{ item.aprobado_por or '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Gestionado por</label>
                <input class="form-control" name="gestionado_por" value="{{ item.gestionado_por or '' }}">
              </div>

              <div class="col-md-2">
                <label class="form-label">Fecha de Alta</label>
                <input type="date" class="form-control" name="fecha_alta" value="{{ item.fecha_alta or '' }}">
              </div>

              <div class="col-md-2">
                <label class="form-label">Fecha de Baja</label>
                <input type="date" class="form-control" name="fecha_baja" value="{{ item.fecha_baja or '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Estado</label>
                <select name="estado_id" class="form-select">
                  <option value="">-- Seleccione --</option>
                  {% for e in estados %}
                    <option value="{{ e.id }}" {% if item.estado_id == e.id %}selected{% endif %}>{{ e.nombre }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Evidencia (texto)</label>
                <textarea class="form-control" name="evidencia" rows="2">{{ item.evidencia or '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Agregar Evidencias PDF</label>
                <input type="file" name="evidencias" class="form-control" accept=".pdf" multiple>
                <small class="text-muted">Puede adjuntar uno o varios PDFs.</small>
              </div>

              <div class="col-12">

                <hr>

                <h6 class="mb-2 fw-bold">📎 Evidencias existentes</h6>

                {% if item.evidencias %}

                  <ul class="mb-0 list-unstyled">

                    {% for ev in item.evidencias %}

                      <li class="accesoedit-evidence-row"
                          id="ev-row-{{ ev.id }}">

                        <div>
                          <a href="{{ url_for('accesos_evidencia_view', evi_id=ev.id, next='accesos_edit', reg_id=item.id) }}">
                            {{ ev.original_name }}
                          </a>
                          <span class="text-muted small">
                            ({{ (ev.size or 0) // 1024 }} KB)
                          </span>
                        </div>

                        <button type="button"
                                class="btn btn-outline-danger btn-sm rounded-pill px-3"
                                onclick="eliminarEvidenciaAcceso({{ ev.id }})">
                          Eliminar PDF
                        </button>

                      </li>

                    {% endfor %}

                  </ul>

                {% else %}

                  <div class="text-muted">
                    No hay evidencias PDF cargadas.
                  </div>

                {% endif %}

              </div>

            </div>

            <div class="accesoedit-bottom-actions">

              <button class="btn btn-success rounded-pill px-4 fw-bold"
                      type="submit">
                Guardar cambios
              </button>

              <a href="{{ url_for('accesos_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold accesoedit-cancel-btn">
                Cancelar
              </a>

            </div>

          </form>

        </div>
      </div>

    </div>

    <script>

    async function eliminarEvidenciaAcceso(eviId) {

      if (!confirm('¿Eliminar esta evidencia?')) return;

      try {

        const resp = await fetch(`/accesos/evidencia/${eviId}/delete`,{
          method:'POST',
          headers:{'X-Requested-With':'XMLHttpRequest'}
        });

        if(resp.ok){

          const row=document.getElementById(`ev-row-${eviId}`);

          if(row) row.remove();

        }else{

          alert('No se pudo eliminar la evidencia.');

        }

      }catch(err){

        console.error(err);
        alert('Error de conexión al eliminar la evidencia.');

      }

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

      .accesoedit-shell{
        width:96%;
        max-width:1200px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HEADER SGSI MODERNO
      ========================= */
      .accesoedit-header-card{
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

      .accesoedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .accesoedit-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .accesoedit-header-overlay::before{
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

      .accesoedit-header-text{
        max-width:1000px;
        width:100%;
      }

      .accesoedit-header-text::before{
        content:"SGSI · Edición de Acceso";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .accesoedit-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
      }

      .accesoedit-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES SUPERIORES
      ========================= */
      .accesoedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .accesoedit-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .accesoedit-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .accesoedit-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      /* =========================
         CARD PRINCIPAL
      ========================= */
      .accesoedit-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .accesoedit-card-body{
        padding:18px;
      }

      .accesoedit-section-title{
        font-weight:950;
        font-size:.90rem;
        color:#0b4a8f;
        padding:10px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin-bottom:14px;
      }

      /* =========================
         FORMULARIOS
      ========================= */
      .accesoedit-card .form-label{
        font-weight:800;
        font-size:.78rem;
        color:#101827;
        margin-bottom:5px;
      }

      .accesoedit-card .form-control,
      .accesoedit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .accesoedit-card textarea.form-control{
        min-height:80px;
      }

      .accesoedit-card .form-control:focus,
      .accesoedit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }

      /* =========================
         EVIDENCIAS
      ========================= */
      .accesoedit-evidence-row{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        background:linear-gradient(180deg,#ffffff,#f8fbff);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:10px 12px;
        margin-bottom:8px;
        box-shadow:0 6px 14px rgba(15,23,42,.08);
        flex-wrap:wrap;
      }

      .accesoedit-evidence-name{
        font-size:.78rem;
        font-weight:800;
        color:#1d4ed8;
      }

      /* =========================
         ACCIONES
      ========================= */
      .accesoedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:12px;
        margin-top:22px;
        flex-wrap:wrap;
      }

      .accesoedit-cancel-btn{
        background:#ffffff;
        color:#000;
        border:1px solid #cfd8e3;
      }

      .accesoedit-cancel-btn:hover{
        background:#f3f4f6;
      }

      .accesoedit-save-btn{
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      /* =========================
         RESPONSIVE
      ========================= */
      @media (max-width:992px){
        .accesoedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .accesoedit-title{
          font-size:1.20rem;
        }

        .accesoedit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .accesoedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .accesoedit-header-overlay::before{
          margin:0;
        }

        .accesoedit-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        item=item,
        areas=areas,
        estados=estados,
        niveles=niveles
    )
    return render_template_string(BASE, content=Markup(inner))

# ==========================
# Eliminar
# ==========================

@app.route('/accesos/delete/<int:id>')
@login_required
def accesos_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Gestión de Accesos")
    ):
        flash("No tiene permiso para eliminar accesos.", "danger")
        return redirect(url_for('accesos_matriz'))

    item = GestionAcceso.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash("Acceso eliminado.", "success")
    return redirect(url_for('accesos_matriz'))

# ==========================
# Evidencias
# ==========================

@app.route('/accesos/evidencia/<int:evi_id>/file')
@login_required
def accesos_evidencia_file(evi_id):
    evi = GestionAccesoEvidencia.query.get_or_404(evi_id)
    fullpath = os.path.join(app.config['UPLOAD_GESTION_ACCESOS_DIR'], evi.filename)

    if not os.path.isfile(fullpath):
        abort(404)

    return send_file(
        fullpath,
        mimetype=evi.mime or 'application/pdf',
        as_attachment=False,
        download_name=evi.original_name or evi.filename,
        conditional=True
    )

# ==========================
# Ver Evidencia — Gestión de Accesos
# ==========================
@app.route('/accesos/evidencia/<int:evi_id>/view')
@login_required
def accesos_evidencia_view(evi_id):
    evi = GestionAccesoEvidencia.query.get_or_404(evi_id)

    path = os.path.join(app.config['UPLOAD_GESTION_ACCESOS_DIR'], evi.filename)
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

    back_label_map = {
        'accesos_matriz': '⬅ Volver a la Matriz',
        'accesos_menu': '⬅ Volver al Menú de Accesos',
        'menu': '⬅ Volver al menú principal',
    }

    allowed_back = set(back_label_map.keys())

    if next_ep in allowed_back:
        back_url = url_for(next_ep)
        back_label = back_label_map[next_ep]
    else:
        back_url = request.referrer or url_for('accesos_matriz')
        back_label = '⬅ Volver'

    # =========================
    # Conversión Office -> PDF
    # =========================
    pdf_converted_name = None
    if is_office:
        try:
            converted_dir = app.config.get(
                'UPLOAD_GESTION_ACCESOS_CONVERTED_DIR',
                os.path.join(app.root_path, 'static', 'converted_accesos_evidencias')
            )
            os.makedirs(converted_dir, exist_ok=True)

            pdf_converted_path = ensure_pdf_from_office(path, output_dir=converted_dir)

            if pdf_converted_path and os.path.isfile(pdf_converted_path):
                pdf_converted_name = os.path.basename(pdf_converted_path)
        except Exception:
            pdf_converted_name = None

    inner_html = """
    <div class="accevi-shell">

      <div class="accevi-header-actions">
        <a href="{{ back_url }}"
           class="btn rounded-pill px-4 py-2 fw-bold accevi-back-btn">
          {{ back_label }}
        </a>

        <div class="accevi-file-pill" title="{{ original_name }}">
          📎 {{ original_name }}
        </div>
      </div>

      <div class="accevi-card">
        <div class="accevi-card-body">

          {% if is_pdf %}
            <div class="accevi-pdf-container">
              <iframe id="pdfFrame"
                      src="{{ url_for('accesos_evidencia_file', evi_id=evi_id) }}#zoom=page-width"
                      title="Visor PDF"></iframe>
            </div>

          {% elif pdf_converted_name %}
            <div class="accevi-pdf-container">
              <iframe id="pdfFrame"
                      src="{{ url_for('accesos_evidencia_convertido', filename=pdf_converted_name) }}#zoom=page-width"
                      title="Visor PDF convertido"></iframe>
            </div>

            <div class="accevi-extra-actions">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('accesos_evidencia_file', evi_id=evi_id) }}">
                Abrir archivo original
              </a>
            </div>

          {% elif is_image %}
            <div class="text-center p-3">
              <img src="{{ url_for('accesos_evidencia_file', evi_id=evi_id) }}"
                   alt="{{ original_name }}"
                   class="img-fluid rounded-4 shadow-sm"
                   style="max-height: 78vh; object-fit: contain;">
            </div>

          {% elif is_office %}
            <div class="alert alert-warning m-2 rounded-4">
              No fue posible generar una vista previa interna del archivo Office.
              Verifica que LibreOffice esté instalado en el servidor.
            </div>

            <div class="accevi-extra-actions">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('accesos_evidencia_file', evi_id=evi_id) }}">
                Abrir / descargar archivo original
              </a>
            </div>

          {% else %}
            <div class="alert alert-info m-2 rounded-4">
              Este tipo de archivo (<b>{{ ext }}</b>) no se puede previsualizar.
              Puedes abrirlo o descargarlo.
            </div>

            <div class="accevi-extra-actions">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('accesos_evidencia_file', evi_id=evi_id) }}">
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

      .accevi-shell{
        width:96%;
        max-width:1500px;
        margin:22px auto 30px auto;
      }

      .accevi-header-actions{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        flex-wrap:wrap;
        margin-bottom:16px;
      }

      .accevi-back-btn{
        background:#ffffff;
        color:#000000;
        border:2px solid #ffffff;
        box-shadow:0 4px 10px rgba(0,0,0,.10);
      }

      .accevi-back-btn:hover{
        background:#f3f4f6;
        color:#000000;
        border-color:#f3f4f6;
      }

      .accevi-file-pill{
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

      .accevi-card{
        background:rgba(255,255,255,.88)!important;
        border-radius:18px;
        backdrop-filter:blur(6px);
        box-shadow:0 10px 24px rgba(0,0,0,.18);
        overflow:hidden;
      }

      .accevi-card-body{
        padding:8px 7px;
      }

      .accevi-pdf-container{
        height:min(82vh,1000px);
        min-height:600px;
        width:100%;
      }

      .accevi-pdf-container iframe{
        width:100%;
        height:100%;
        border:1px solid #dee2e6;
        border-radius:16px;
        background:#fff;
      }

      .accevi-extra-actions{
        text-align:center;
        margin-top:14px;
      }

      @media (max-width:992px){
        .accevi-shell{
          width:98%;
          margin:14px auto 24px auto;
        }

        .accevi-header-actions{
          flex-direction:column;
          align-items:stretch;
        }

        .accevi-file-pill{
          max-width:100%;
        }

        .accevi-card-body{
          padding:10px;
        }

        .accevi-pdf-container{
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

@app.route('/accesos/evidencia/convertido/<path:filename>')
@login_required
def accesos_evidencia_convertido(filename):
    converted_dir = app.config.get(
        'UPLOAD_GESTION_ACCESOS_CONVERTED_DIR',
        os.path.join(app.root_path, 'static', 'converted_accesos_evidencias')
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

@app.route('/accesos/evidencia/<int:evi_id>/delete', methods=['POST'])
@login_required
def accesos_evidencia_delete(evi_id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Gestión de Accesos")
    ):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"ok": False, "error": "No autorizado"}), 403
        flash("No tiene permiso para eliminar evidencias.", "danger")
        return redirect(url_for('accesos_matriz'))

    evi = GestionAccesoEvidencia.query.get_or_404(evi_id)
    path = os.path.join(app.config['UPLOAD_GESTION_ACCESOS_DIR'], evi.filename)

    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as ex:
        print("Error eliminando archivo físico:", ex)

    reg_id = evi.registro_id
    db.session.delete(evi)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"ok": True})

    flash("Evidencia eliminada.", "success")
    return redirect(url_for('accesos_edit', id=reg_id))

# ==========================================================================================================================================
#                                                       Fin Módulo de Gestión de Accesos
# ==========================================================================================================================================


# ==========================================================================================================================================
#                                                       Módulo de Revisión de Accesos
# ==========================================================================================================================================

# ==========================
# ENTRADA DIRECTA — Revisión de Accesos
# ==========================
@app.route('/revision_accesos_menu')
@login_required
def revision_accesos_menu():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Revisión de Accesos"):
        flash("No tiene permiso para acceder al módulo de revisión de accesos.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('revision_accesos_matriz'))


# ===========================
# Agregar revisión de accesos
# ===========================
@app.route('/revision_accesos/new', methods=['GET', 'POST'])
@login_required
def revision_accesos_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('revision_accesos_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Revisión de Accesos"):
        flash("No tiene permiso para agregar registro de revisión de accesos.", "danger")
        return redirect(url_for('revision_accesos_matriz'))

    if request.method == 'POST':
        it = RevisionAccesoRegistro(
            usuario_rol     = (request.form.get('usuario_rol') or '').strip(),
            aplicacion      = (request.form.get('aplicacion') or '').strip(),
            tipo_acceso     = (request.form.get('tipo_acceso') or '').strip(),
            revisado_por    = (request.form.get('revisado_por') or '').strip(),
            fecha_revision  = request.form.get('fecha_revision') or '',
            sigue_necesario = (request.form.get('sigue_necesario') or '').strip(),
            observaciones   = (request.form.get('observaciones') or '').strip(),
        )
        db.session.add(it)
        db.session.commit()
        flash("Revisión de acceso registrada.", "success")
        return redirect(url_for('revision_accesos_matriz'))

    html = """
    <div class="revadd-shell">

      <div class="revadd-header-card">
        <div class="revadd-header-overlay">
          <div class="revadd-header-text">
            <h3 class="revadd-title m-0">Agregar Revisión de Acceso</h3>
            <div class="revadd-subtitle">
              Registro de revisiones periódicas de accesos para validar vigencia, necesidad y cumplimiento dentro del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="revadd-header-actions">
        <a href="{{ url_for('revision_accesos_matriz') }}"
           class="btn rounded-pill px-4 fw-bold revadd-back-btn">
          ⬅ Volver a la Matriz
        </a>


      </div>

      <div class="revadd-card">
        <div class="revadd-card-body">
          <form method="post">

            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Usuario / Rol</label>
                <input class="form-control" name="usuario_rol" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Aplicación</label>
                <input class="form-control" name="aplicacion" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Tipo de Acceso</label>
                <select class="form-select" name="tipo_acceso" required>
                  <option value="">-- Seleccione --</option>
                  {% for t in tipos_acceso %}
                    <option value="{{ t }}">{{ t }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Revisado por</label>
                <input class="form-control" name="revisado_por" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date" class="form-control" name="fecha_revision" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">¿Sigue Siendo Necesario?</label>
                <select class="form-select" name="sigue_necesario" required>
                  <option value="">-- Seleccione --</option>
                  {% for v in valores_si_no %}
                    <option value="{{ v }}">{{ v }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-12">
                <label class="form-label">Observaciones</label>
                <textarea class="form-control" name="observaciones" rows="2"></textarea>
              </div>

            </div>

            <div class="revadd-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>

              <a href="{{ url_for('revision_accesos_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold revadd-cancel-btn">
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

      .revadd-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      .revadd-header-card{
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

      .revadd-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .revadd-header-overlay{
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

      .revadd-header-overlay::before{
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

      .revadd-header-text{
        max-width:1100px;
        width:100%;
      }

      .revadd-header-text::before{
        content:"SGSI · Revisión de Accesos";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .revadd-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .revadd-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .revadd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .revadd-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .revadd-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .revadd-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .revadd-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .revadd-card-body{
        padding:18px;
      }

      .revadd-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .revadd-card .form-control,
      .revadd-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .revadd-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .revadd-card .form-control:focus,
      .revadd-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }

      .revadd-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .revadd-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .revadd-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .revadd-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .revadd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .revadd-header-card{
          min-height:88px;
        }

        .revadd-title{
          font-size:1.20rem;
        }

        .revadd-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .revadd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .revadd-header-overlay::before{
          margin:0;
        }

        .revadd-header-actions .btn,
        .revadd-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        tipos_acceso=REVISION_TIPOS_ACCESO,
        valores_si_no=REVISION_SI_NO
    )
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Matriz Revisión de Accesos
# ==========================
@app.route('/revision_accesos_matriz')
@login_required
def revision_accesos_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Revisión de Accesos"):
            flash("No tiene permiso para ver la revisión de accesos.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    filtro_usuario = (request.args.get('usuario') or '').strip()
    filtro_aplicacion = (request.args.get('aplicacion') or '').strip()
    filtro_sigue_necesario = (request.args.get('sigue_necesario') or '').strip()

    query = RevisionAccesoRegistro.query

    if filtro_usuario:
        query = query.filter(RevisionAccesoRegistro.usuario_rol == filtro_usuario)

    if filtro_aplicacion:
        query = query.filter(RevisionAccesoRegistro.aplicacion == filtro_aplicacion)

    if filtro_sigue_necesario:
        query = query.filter(RevisionAccesoRegistro.sigue_necesario == filtro_sigue_necesario)

    items = query.order_by(RevisionAccesoRegistro.id.desc()).all()

    opciones_usuario = [
        x[0] for x in db.session.query(RevisionAccesoRegistro.usuario_rol)
        .filter(RevisionAccesoRegistro.usuario_rol.isnot(None))
        .filter(RevisionAccesoRegistro.usuario_rol != '')
        .distinct()
        .order_by(RevisionAccesoRegistro.usuario_rol.asc())
        .all()
    ]

    opciones_aplicacion = [
        x[0] for x in db.session.query(RevisionAccesoRegistro.aplicacion)
        .filter(RevisionAccesoRegistro.aplicacion.isnot(None))
        .filter(RevisionAccesoRegistro.aplicacion != '')
        .distinct()
        .order_by(RevisionAccesoRegistro.aplicacion.asc())
        .all()
    ]

    opciones_sigue_necesario = [
        x[0] for x in db.session.query(RevisionAccesoRegistro.sigue_necesario)
        .filter(RevisionAccesoRegistro.sigue_necesario.isnot(None))
        .filter(RevisionAccesoRegistro.sigue_necesario != '')
        .distinct()
        .order_by(RevisionAccesoRegistro.sigue_necesario.asc())
        .all()
    ]

    total_filtrados = len(items)
    total_general = RevisionAccesoRegistro.query.count()

    html = """
    <div class="revmat-shell">

      <div class="revmat-header-card">
        <div class="revmat-header-overlay">
          <div class="revmat-header-text">
            <h3 class="revmat-title m-0">Revisión de Accesos</h3>
            <div class="revmat-subtitle">
              Visualización resumida de revisiones periódicas de accesos para validar necesidad, vigencia y control dentro del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="revmat-header-actions">
        

        {% if not read_only %}
          <a href="{{ url_for('revision_accesos_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            ➕ Agregar Revisión
          </a>
        {% else %}
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            ➕ Agregar Revisión
          </button>
        {% endif %}
      </div>

      <div class="revmat-filter-card">
        <div class="revmat-filter-body">
          <form method="get" action="{{ url_for('revision_accesos_matriz') }}">
            <div class="row g-2 align-items-end">

              <div class="col-md-4">
                <label class="form-label fw-bold">Usuario / Rol</label>
                <select name="usuario" class="form-select rounded-3">
                  <option value="">Todos</option>
                  {% for op in opciones_usuario %}
                    <option value="{{ op }}" {% if filtro_usuario == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label fw-bold">Aplicación</label>
                <select name="aplicacion" class="form-select rounded-3">
                  <option value="">Todas</option>
                  {% for op in opciones_aplicacion %}
                    <option value="{{ op }}" {% if filtro_aplicacion == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label fw-bold">¿Sigue siendo necesario?</label>
                <select name="sigue_necesario" class="form-select rounded-3">
                  <option value="">Todos</option>
                  {% for op in opciones_sigue_necesario %}
                    <option value="{{ op }}" {% if filtro_sigue_necesario == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-12">
                <div class="d-flex gap-2 flex-wrap justify-content-end">
                  <button type="submit" class="btn btn-primary rounded-pill px-4 fw-bold">Filtrar</button>
                  <a href="{{ url_for('revision_accesos_matriz') }}"
                     class="btn btn-secondary rounded-pill px-4 fw-bold">Limpiar</a>
                </div>
              </div>

            </div>
          </form>
        </div>
      </div>

      <div class="revmat-card">

        <div class="revmat-topbar">
          <div>
            <h5 class="revmat-top-title mb-1">Resumen de revisiones</h5>
            <div class="revmat-top-note">
              La matriz muestra los campos principales. Para consultar toda la información usa el botón <strong>Ver detalle</strong>.
            </div>
          </div>
          <div class="revmat-counter-badge">
            Registros filtrados: {{ total_filtrados }} | Total general: {{ total_general }}
          </div>
        </div>

        <div class="revmat-card-body">
          <div class="revmat-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-hover align-middle revmat-table mb-0">
                <colgroup>
                  <col style="width: 20%;">
                  <col style="width: 18%;">
                  <col style="width: 16%;">
                  <col style="width: 14%;">
                  <col style="width: 12%;">
                  <col style="width: 20%;">
                </colgroup>

                <thead>
                  <tr>
                    <th>Usuario / Rol</th>
                    <th>Aplicación</th>
                    <th>Tipo de Acceso</th>
                    <th>Fecha de Revisión</th>
                    <th>¿Sigue siendo necesario?</th>
                    <th class="revmat-col-acciones">Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  {% for it in items %}
                    <tr>
                      <td>{{ it.usuario_rol or '—' }}</td>
                      <td>{{ it.aplicacion or '—' }}</td>
                      <td>{{ it.tipo_acceso or '—' }}</td>
                      <td class="text-center">{{ it.fecha_revision or '—' }}</td>
                      <td class="text-center">{{ it.sigue_necesario or '—' }}</td>

                      <td class="text-center revmat-col-acciones">
                        <div class="revmat-actions-wrap">
                          <a href="{{ url_for('revision_accesos_detalle', id=it.id) }}"
                             class="btn btn-info btn-sm rounded-pill revmat-btn-action text-white fw-bold">
                            Ver detalle
                          </a>

                          {% if not read_only %}
                            <a href="{{ url_for('revision_accesos_edit', id=it.id) }}"
                               class="btn btn-warning btn-sm rounded-pill revmat-btn-action fw-bold">
                              Editar
                            </a>

                            <a href="{{ url_for('revision_accesos_delete', id=it.id) }}"
                               class="btn btn-danger btn-sm rounded-pill revmat-btn-action fw-bold"
                               onclick="return confirm('¿Eliminar este registro de revisión?');">
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
                      <td colspan="6" class="text-center text-muted py-5">
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

      .revmat-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .revmat-header-card{
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

      .revmat-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .revmat-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .revmat-header-overlay::before{
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

      .revmat-header-text{
        max-width:1100px;
        width:100%;
      }

      .revmat-header-text::before{
        content:"SGSI · Matriz de Revisión de Accesos";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .revmat-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .revmat-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .revmat-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .revmat-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .revmat-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .revmat-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .revmat-filter-card,
      .revmat-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .revmat-filter-card{
        margin-bottom:14px;
      }

      .revmat-filter-body{
        padding:14px 16px;
      }

      .revmat-filter-body .form-label{
        font-size:.78rem;
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
      }

      .revmat-filter-body .form-select,
      .revmat-filter-body .form-control{
        min-height:36px;
        height:36px;
        font-size:.80rem;
        border-radius:9px;
        border:1px solid #d9e3f0;
        background:#f8fafc;
      }

      .revmat-filter-body .btn{
        border-radius:10px !important;
        min-height:36px;
        padding:7px 18px !important;
        font-size:.80rem;
        font-weight:900;
      }

      .revmat-filter-body .form-select:focus,
      .revmat-filter-body .form-control:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .revmat-topbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:14px 16px 0 16px;
        flex-wrap:wrap;
      }

      .revmat-top-title{
        color:#0f172a;
        font-weight:950;
        font-size:.92rem;
      }

      .revmat-top-note{
        color:#475569;
        font-size:.78rem;
      }

      .revmat-counter-badge{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:7px 14px;
        font-size:.78rem;
        box-shadow:0 8px 16px rgba(15,23,42,.16);
      }

      .revmat-card-body{
        padding:12px 16px 16px 16px;
      }

      .revmat-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#fff;
      }

      .revmat-table{
        min-width:1300px;
        table-layout:fixed;
        margin-bottom:0;
      }

      .revmat-table thead th{
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

      .revmat-table th,
      .revmat-table td{
        vertical-align:top;
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .revmat-table td{
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .revmat-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .revmat-table tbody tr:hover{
        background:#eef6ff;
      }

      .revmat-table th.revmat-col-acciones,
      .revmat-table td.revmat-col-acciones,
      .revmat-col-acciones{
        width:190px !important;
        min-width:190px !important;
        max-width:190px !important;
        text-align:center;
        vertical-align:middle;
      }

      .revmat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .revmat-btn-action{
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

      .revmat-actions-wrap .badge{
        font-size:.70rem;
        padding:5px 10px;
        border-radius:999px;
        font-weight:900;
        white-space:nowrap;
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .btn.rounded-pill{
        border-radius:999px !important;
      }

      @media (max-width:992px){
        .revmat-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .revmat-header-card{
          min-height:88px;
        }

        .revmat-title{
          font-size:1.20rem;
        }

        .revmat-filter-body,
        .revmat-card-body{
          padding:12px;
        }

        .revmat-topbar{
          padding:12px 14px 0 14px;
        }

        .revmat-table th.revmat-col-acciones,
        .revmat-table td.revmat-col-acciones,
        .revmat-col-acciones{
          width:170px !important;
          min-width:170px !important;
          max-width:170px !important;
        }
      }

      @media (max-width:768px){
        .revmat-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .revmat-header-overlay::before{
          margin:0;
        }

        .revmat-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        opciones_usuario=opciones_usuario,
        opciones_aplicacion=opciones_aplicacion,
        opciones_sigue_necesario=opciones_sigue_necesario,
        filtro_usuario=filtro_usuario,
        filtro_aplicacion=filtro_aplicacion,
        filtro_sigue_necesario=filtro_sigue_necesario,
        total_filtrados=total_filtrados,
        total_general=total_general
    )
    return render_template_string(BASE, content=Markup(inner))

# ==========================
# Detalle revisión de accesos
# ==========================

@app.route('/revision_accesos/detalle/<int:id>')
@login_required
def revision_accesos_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Revisión de Accesos"):
            flash("No tiene permiso para ver el detalle de la revisión de accesos.", "danger")
            return redirect(url_for('revision_accesos_menu'))
        read_only = False

    it = RevisionAccesoRegistro.query.get_or_404(id)

    html = """
    <div class="revdet-shell">

      <!-- CABECERA -->
      <div class="revdet-header-card">
        <div class="revdet-header-overlay">
          <div class="revdet-header-text">
            <h3 class="revdet-title m-0">Detalle de la Revisión de Acceso</h3>
            <div class="revdet-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <!-- BOTONES -->
      <div class="revdet-header-actions">
        <a href="{{ url_for('revision_accesos_matriz') }}"
           class="btn rounded-pill px-4 fw-bold revdet-back-btn">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('revision_accesos_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <!-- TARJETA -->
      <div class="revdet-card">
        <div class="revdet-card-body">

          <div class="revdet-section">
            <div class="revdet-section-title">Información principal</div>
            <div class="row g-3">

              <div class="col-md-4">
                <div class="revdet-field">
                  <div class="revdet-label">Usuario / Rol</div>
                  <div class="revdet-value">{{ it.usuario_rol or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="revdet-field">
                  <div class="revdet-label">Aplicación</div>
                  <div class="revdet-value">{{ it.aplicacion or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="revdet-field">
                  <div class="revdet-label">Tipo de Acceso</div>
                  <div class="revdet-value">{{ it.tipo_acceso or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <div class="revdet-section">
            <div class="revdet-section-title">Control y validación</div>
            <div class="row g-3">

              <div class="col-md-4">
                <div class="revdet-field revdet-field-compact">
                  <div class="revdet-label">Revisado por</div>
                  <div class="revdet-value revdet-value-compact">{{ it.revisado_por or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="revdet-field revdet-field-compact">
                  <div class="revdet-label">Fecha de Revisión</div>
                  <div class="revdet-value revdet-value-compact">{{ it.fecha_revision or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="revdet-field revdet-field-compact">
                  <div class="revdet-label">¿Sigue siendo necesario?</div>
                  <div class="revdet-value revdet-value-compact">{{ it.sigue_necesario or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <div class="revdet-section">
            <div class="revdet-section-title">Observaciones</div>
            <div class="row g-3">

              <div class="col-md-12">
                <div class="revdet-field">
                  <div class="revdet-label">Observaciones</div>
                  <div class="revdet-value">{{ it.observaciones or '—' }}</div>
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

      .revdet-shell{
        width:96%;
        max-width:1200px;
        margin:10px auto 24px auto;
      }

      .revdet-header-card{
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

      .revdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .revdet-header-overlay{
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

      .revdet-header-overlay::before{
        content:"🔎";
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

      .revdet-header-text{
        max-width:1000px;
        width:100%;
        transform:none;
      }

      .revdet-header-text::before{
        content:"SGSI · Detalle de Revisión";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .revdet-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .revdet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .revdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .revdet-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .revdet-back-btn{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .revdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .revdet-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .revdet-card-body{
        padding:18px;
      }

      .revdet-section{
        margin-bottom:14px;
        background:#fff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .revdet-section:last-child{
        margin-bottom:0;
      }

      .revdet-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      .revdet-field{
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

      .revdet-field-compact{
        min-height:78px;
        justify-content:center;
        align-items:center;
        text-align:center;
      }

      .revdet-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .revdet-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .revdet-value-compact{
        font-weight:900;
        font-size:.80rem;
        line-height:1.2;
      }

      .revdet-section .row.g-3{
        --bs-gutter-x:.8rem;
        --bs-gutter-y:.8rem;
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

      .revdet-soft-box{
        background:#eef5ff;
        border:1px solid #d9eaff;
        border-radius:14px;
        padding:12px 14px;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      @media (max-width:992px){
        .revdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .revdet-header-card{
          min-height:88px;
        }

        .revdet-title{
          font-size:1.20rem;
        }

        .revdet-card-body{
          padding:8px 7px;
        }

        .revdet-section{
          padding:12px;
        }

        .revdet-field,
        .revdet-field-compact{
          min-height:72px;
        }
      }

      @media (max-width:768px){
        .revdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .revdet-header-overlay::before{
          margin:0;
        }

        .revdet-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        it=it,
        read_only=read_only
    )
    return render_template_string(BASE, content=Markup(inner))

# ==========================
# Editar revision de accesos
# ==========================

@app.route('/revision_accesos/edit/<int:id>', methods=['GET','POST'])
@login_required
def revision_accesos_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Revisión de Accesos")
    ):
        flash("No tiene permiso para editar registros de la revisión de accesos.", "danger")
        return redirect(url_for('revision_accesos_matriz'))


    item = RevisionAccesoRegistro.query.get_or_404(id)

    if request.method == 'POST':
        item.usuario_rol     = (request.form.get('usuario_rol') or '').strip()
        item.aplicacion      = (request.form.get('aplicacion') or '').strip()
        item.tipo_acceso     = (request.form.get('tipo_acceso') or '').strip()
        item.revisado_por    = (request.form.get('revisado_por') or '').strip()
        item.fecha_revision  = request.form.get('fecha_revision') or ''
        item.sigue_necesario = (request.form.get('sigue_necesario') or '').strip()
        item.observaciones   = (request.form.get('observaciones') or '').strip()

        db.session.commit()
        flash("Revisión de acceso actualizada.", "success")
        return redirect(url_for('revision_accesos_matriz'))

    html = """
    <div class="revedit-shell">

      <!-- CABECERA -->
      <div class="revedit-header-card">
        <div class="revedit-header-overlay">
          <div class="revedit-header-text">
            <h3 class="revedit-title m-0">Editar Revisión de Acceso</h3>
            <div class="revedit-subtitle">
              Actualización de revisiones de acceso para validar necesidad, vigencia y control dentro del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="revedit-header-actions">
        <a href="{{ url_for('revision_accesos_matriz') }}"
           class="btn rounded-pill px-5 fw-bold revedit-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <!-- TARJETA -->
      <div class="revedit-card">
        <div class="revedit-card-body">
          <form method="post">

            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Usuario / Rol</label>
                <input class="form-control"
                       name="usuario_rol"
                       value="{{ item.usuario_rol or '' }}"
                       required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Aplicación</label>
                <input class="form-control"
                       name="aplicacion"
                       value="{{ item.aplicacion or '' }}"
                       required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Tipo de Acceso</label>
                <select class="form-select" name="tipo_acceso" required>
                  {% for t in tipos_acceso %}
                    <option value="{{ t }}" {% if item.tipo_acceso==t %}selected{% endif %}>
                      {{ t }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Revisado por</label>
                <input class="form-control"
                       name="revisado_por"
                       value="{{ item.revisado_por or '' }}"
                       required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date"
                       class="form-control"
                       name="fecha_revision"
                       value="{{ item.fecha_revision or '' }}"
                       required>
              </div>

              <div class="col-md-4">
                <label class="form-label">¿Sigue Siendo Necesario?</label>
                <select class="form-select" name="sigue_necesario" required>
                  {% for v in valores_si_no %}
                    <option value="{{ v }}" {% if item.sigue_necesario==v %}selected{% endif %}>
                      {{ v }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-12">
                <label class="form-label">Observaciones</label>
                <textarea class="form-control"
                          name="observaciones"
                          rows="2">{{ item.observaciones or '' }}</textarea>
              </div>

            </div>

            <div class="revedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>

              <a href="{{ url_for('revision_accesos_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold revedit-cancel-btn">
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

      .revedit-shell{
        width:96%;
        max-width:1200px;
        margin:10px auto 24px auto;
      }

      .revedit-header-card{
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

      .revedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .revedit-header-overlay{
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

      .revedit-header-overlay::before{
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

      .revedit-header-text{
        max-width:1000px;
        width:100%;
        transform:none;
      }

      .revedit-header-text::before{
        content:"SGSI · Edición de Revisión";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .revedit-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .revedit-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      .revedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .revedit-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .revedit-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .revedit-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .revedit-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .revedit-card-body{
        padding:18px;
      }

      .revedit-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 14px 0;
      }

      .revedit-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .revedit-card .form-control,
      .revedit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .revedit-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .revedit-card .form-control:focus,
      .revedit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .revedit-card .input-group-text{
        border-radius:0 9px 9px 0;
        border:1px solid #d9e3f0;
        background:#eef5ff;
        color:#0b4a8f;
        font-weight:900;
      }

      .revedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
      }

      .revedit-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .revedit-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .revedit-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .revedit-save-btn{
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .revedit-soft-box{
        background:#eef5ff;
        border:1px solid #d9eaff;
        border-radius:14px;
        padding:12px 14px;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      @media (max-width:992px){
        .revedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .revedit-header-card{
          min-height:88px;
        }

        .revedit-title{
          font-size:1.20rem;
        }

        .revedit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .revedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .revedit-header-overlay::before{
          margin:0;
        }

        .revedit-header-actions .btn,
        .revedit-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        item=item,
        tipos_acceso=REVISION_TIPOS_ACCESO,
        valores_si_no=REVISION_SI_NO
    )
    return render_template_string(BASE, content=Markup(inner))

# ==========================
# Eliminar
# ==========================

@app.route('/revision_accesos/delete/<int:id>')
@login_required
def revision_accesos_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (user.role != 'admin' and not verificar_permiso(user, "Revisión de Accesos")
    ):
        flash("No tiene permiso para eliminar registros de la revisión de accesos.", "danger")
        return redirect(url_for('revision_accesos_matriz'))

    item = RevisionAccesoRegistro.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash("Revisión de acceso eliminada.", "success")
    return redirect(url_for('revision_accesos_matriz'))

# ==========================================================================================================================================
#                                                       Fin Módulo de Revisión de Accesos
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                               Módulo Control de Cambios
# ==========================================================================================================================================


class CambioRFCRegistro(db.Model):
    __tablename__ = 'cambio_rfc_registro'

    id = db.Column(db.Integer, primary_key=True)

    # --- Información general ---
    ticket = db.Column(db.String(50), nullable=False)
    fecha_solicitud = db.Column(db.Date, nullable=False)

    responsable_solicitud_id = db.Column(db.Integer, nullable=True)  # FK opcional
    responsable_solicitud_nombre = db.Column(db.String(150))
    responsable_solicitud_cargo = db.Column(db.String(150))

    # --- Información del cambio ---
    descripcion = db.Column(db.Text)          # Qué se requiere
    antecedentes = db.Column(db.Text)        # Por qué se requiere
    objetivo = db.Column(db.Text)            # Qué se busca lograr
    alcance = db.Column(db.Text)
    ambiente = db.Column(db.String(30))      # Producción / Contingencia
    partes_interesadas = db.Column(db.Text)
    recursos_necesarios = db.Column(db.Text)

    estado_seguridad = db.Column(db.String(80), default="Pendiente de aprobación por seguridad")

    aprueba_seguridad_fecha = db.Column(db.Date, nullable=True)
    aprueba_seguridad_nombre = db.Column(db.String(255), nullable=True)
    aprueba_seguridad_cargo = db.Column(db.String(255), nullable=True)
    aprueba_seguridad_observacion = db.Column(db.Text, nullable=True)

    tipo_cambio = db.Column(db.String(30))   # Planificado / No planificado / Tipificado
    prioridad = db.Column(db.String(10))     # Alta / Media / Baja

    # --- Aprobación del cambio ---
    ajustes_requeridos = db.Column(db.String(2))     # 'Si' / 'No'
    cambios_requeridos = db.Column(db.Text)

    # Revisa
    revisa_persona_id = db.Column(db.Integer)
    revisa_nombre = db.Column(db.String(150))
    revisa_cargo = db.Column(db.String(150))
    revisa_observaciones = db.Column(db.Text)
    revisa_fecha = db.Column(db.Date)

    # Aprueba (Comité)
    aprueba_persona_id = db.Column(db.Integer)
    aprueba_nombre = db.Column(db.String(150))
    aprueba_cargo = db.Column(db.String(150))
    aprueba_observaciones = db.Column(db.Text)
    aprueba_fecha = db.Column(db.Date)

    # Implementa
    implementa_persona_id = db.Column(db.Integer)
    implementa_nombre = db.Column(db.String(150))
    implementa_cargo = db.Column(db.String(150))
    implementa_observaciones = db.Column(db.Text)
    implementa_fecha = db.Column(db.Date)

    # Seguimiento del cambio
    cambio_eficaz = db.Column(db.String(2))   # 'Si' / 'No'
    descripcion_seguimiento = db.Column(db.Text)

    # Relación con evidencias
    evidencias = db.relationship('CambioRFCEvidencia', backref='rfc', lazy=True)


# =========================
# DETALLE — Evaluación de riesgos RFC
# =========================
class CambioRFCRiesgo(db.Model):
    __tablename__ = 'cambio_rfc_riesgo'

    id = db.Column(db.Integer, primary_key=True)
    rfc_id = db.Column(db.Integer, db.ForeignKey('cambio_rfc_registro.id'), nullable=False, index=True)

    sistema_procedente = db.Column(db.Text, nullable=True)
    riesgo = db.Column(db.Text, nullable=True)
    impacto = db.Column(db.Text, nullable=True)
    controles_aplicar = db.Column(db.Text, nullable=True)
    responsable_riesgo = db.Column(db.Text, nullable=True)

    rfc = db.relationship('CambioRFCRegistro', backref=db.backref(
        'riesgos',
        lazy=True,
        cascade='all, delete-orphan'
    ))

# =========================
# DETALLE — Plan de pruebas RFC
# =========================
class CambioRFCPlanPruebas(db.Model):
    __tablename__ = 'cambio_rfc_plan_pruebas'

    id = db.Column(db.Integer, primary_key=True)
    rfc_id = db.Column(db.Integer, db.ForeignKey('cambio_rfc_registro.id'), nullable=False, index=True)

    actividad = db.Column(db.Text, nullable=True)
    fecha_inicio = db.Column(db.String(30), nullable=True)   # o DateTime si luego quieres tiparlo mejor
    fecha_fin = db.Column(db.String(30), nullable=True)
    responsable = db.Column(db.Text, nullable=True)
    entregables = db.Column(db.Text, nullable=True)
    acciones = db.Column(db.Text, nullable=True)

    rfc = db.relationship('CambioRFCRegistro', backref=db.backref(
        'planes_pruebas',
        lazy=True,
        cascade='all, delete-orphan'
    ))


# =========================
# DETALLE — Rollback RFC
# =========================
class CambioRFCRollback(db.Model):
    __tablename__ = 'cambio_rfc_rollback'

    id = db.Column(db.Integer, primary_key=True)
    rfc_id = db.Column(db.Integer, db.ForeignKey('cambio_rfc_registro.id'), nullable=False, index=True)

    actividad = db.Column(db.Text, nullable=True)
    responsable = db.Column(db.Text, nullable=True)
    ejecucion = db.Column(db.Text, nullable=True)

    rfc = db.relationship('CambioRFCRegistro', backref=db.backref(
        'rollbacks',
        lazy=True,
        cascade='all, delete-orphan'
    ))


# =========================
# DETALLE — Actividades implementadas RFC
# =========================
class CambioRFCImplementacion(db.Model):
    __tablename__ = 'cambio_rfc_implementacion'

    id = db.Column(db.Integer, primary_key=True)
    rfc_id = db.Column(db.Integer, db.ForeignKey('cambio_rfc_registro.id'), nullable=False, index=True)

    actividad = db.Column(db.Text, nullable=True)
    responsable = db.Column(db.Text, nullable=True)
    fecha = db.Column(db.String(20), nullable=True)
    ejecucion = db.Column(db.Text, nullable=True)
    tiempo_monitoreo = db.Column(db.String(120), nullable=True)
    fecha_aprobacion = db.Column(db.String(20), nullable=True)
    fecha_tentativa_cierre = db.Column(db.String(20), nullable=True)
    fecha_real_cierre = db.Column(db.String(20), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)

    rfc = db.relationship('CambioRFCRegistro', backref=db.backref(
        'implementaciones',
        lazy=True,
        cascade='all, delete-orphan'
    ))
        

class CambioRFCEvidencia(db.Model):
    __tablename__ = 'cambio_rfc_evidencia'

    id = db.Column(db.Integer, primary_key=True)
    rfc_id = db.Column(db.Integer, db.ForeignKey('cambio_rfc_registro.id'), nullable=False)

    filename = db.Column(db.String(255), nullable=False)      # nombre interno
    original_name = db.Column(db.String(255), nullable=False) # nombre original
    mime = db.Column(db.String(100))
    size = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

def asegurar_columnas_aprobacion_seguridad_rfc():
    with app.app_context():
        inspector = db.inspect(db.engine)
        table_name = CambioRFCRegistro.__tablename__

        columnas = [c["name"] for c in inspector.get_columns(table_name)]

        alteraciones = []

        if "estado_seguridad" not in columnas:
            alteraciones.append(
                "ALTER TABLE {} ADD COLUMN estado_seguridad VARCHAR(80) DEFAULT 'Pendiente de aprobación por seguridad'".format(table_name)
            )

        if "aprueba_seguridad_fecha" not in columnas:
            alteraciones.append(
                "ALTER TABLE {} ADD COLUMN aprueba_seguridad_fecha DATE".format(table_name)
            )

        if "aprueba_seguridad_nombre" not in columnas:
            alteraciones.append(
                "ALTER TABLE {} ADD COLUMN aprueba_seguridad_nombre VARCHAR(255)".format(table_name)
            )

        if "aprueba_seguridad_cargo" not in columnas:
            alteraciones.append(
                "ALTER TABLE {} ADD COLUMN aprueba_seguridad_cargo VARCHAR(255)".format(table_name)
            )

        if "aprueba_seguridad_observacion" not in columnas:
            alteraciones.append(
                "ALTER TABLE {} ADD COLUMN aprueba_seguridad_observacion TEXT".format(table_name)
            )

        for sql in alteraciones:
            db.session.execute(db.text(sql))

        db.session.commit()

# ==========================
# ENTRADA DIRECTA — RFC
# ==========================
@app.route('/rfc_menu')
@login_required
def rfc_menu():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Gestión de Cambios (RFC)"):
        flash("No tiene permiso para acceder al módulo de gestión de cambios.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('rfc_matriz'))

# =========================
# AGREGAR — RFC
# =========================
@app.route('/rfc/new', methods=['GET', 'POST'])
@login_required
def rfc_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('rfc_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Cambios (RFC)"):
        flash("No tiene permiso para agregar cambios.", "danger")
        return redirect(url_for('rfc_matriz'))
    
    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()

    if request.method == 'POST':
        # --- Información general ---
        ticket = (request.form.get('ticket') or '').strip()
        fecha_solicitud = parse_date_safe(request.form.get('fecha_solicitud'))

        if not fecha_solicitud:
            flash("La fecha de solicitud es obligatoria y debe tener formato válido.", "danger")
            return redirect(url_for('rfc_new'))

        responsable_id = request.form.get('responsable_solicitud_id', type=int)

        resp_nombre = ''
        resp_cargo = ''
        if responsable_id:
            a = AreaEmpresa.query.get(responsable_id)
            if a:
                resp_nombre = getattr(a, 'responsable_nombre', '') or ''
                resp_cargo  = getattr(a, 'responsable_cargo', '') or ''

        # --- Información del cambio ---
        descripcion  = (request.form.get('descripcion') or '').strip()
        antecedentes = (request.form.get('antecedentes') or '').strip()
        objetivo     = (request.form.get('objetivo') or '').strip()
        alcance      = (request.form.get('alcance') or '').strip()
        ambiente     = (request.form.get('ambiente') or '').strip()
        partes       = (request.form.get('partes_interesadas') or '').strip()
        recursos     = (request.form.get('recursos_necesarios') or '').strip()
        tipo_cambio  = (request.form.get('tipo_cambio') or '').strip()
        prioridad    = (request.form.get('prioridad') or '').strip()

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

        # --- Aprobación del cambio ---
        ajustes_req   = (request.form.get('ajustes_requeridos') or '').strip()
        cambios_req   = (request.form.get('cambios_requeridos') or '').strip()

        # Revisa
        revisa_id    = request.form.get('revisa_persona_id', type=int)
        revisa_obs   = (request.form.get('revisa_observaciones') or '').strip()
        revisa_fecha = parse_date_safe(request.form.get('revisa_fecha'))
        revisa_nombre = revisa_cargo = ''
        if revisa_id:
            ar = AreaEmpresa.query.get(revisa_id)
            if ar:
                revisa_nombre = getattr(ar, 'responsable_nombre', '') or ''
                revisa_cargo  = getattr(ar, 'responsable_cargo', '') or ''

        # Aprueba (comité)
        aprueba_id    = request.form.get('aprueba_persona_id', type=int)
        aprueba_obs   = (request.form.get('aprueba_observaciones') or '').strip()
        aprueba_fecha = parse_date_safe(request.form.get('aprueba_fecha'))
        aprueba_nombre = aprueba_cargo = ''
        if aprueba_id:
            aa = AreaEmpresa.query.get(aprueba_id)
            if aa:
                aprueba_nombre = getattr(aa, 'responsable_nombre', '') or ''
                aprueba_cargo  = getattr(aa, 'responsable_cargo', '') or ''

        # Implementa
        impl_id_pers    = request.form.get('implementa_persona_id', type=int)
        impl_obs_pers   = (request.form.get('implementa_observaciones') or '').strip()
        impl_fecha_pers = parse_date_safe(request.form.get('implementa_fecha'))
        implementa_nombre = implementa_cargo = ''
        if impl_id_pers:
            ai = AreaEmpresa.query.get(impl_id_pers)
            if ai:
                implementa_nombre = getattr(ai, 'responsable_nombre', '') or ''
                implementa_cargo  = getattr(ai, 'responsable_cargo', '') or ''

        # Seguimiento
        cambio_eficaz = (request.form.get('cambio_eficaz') or '').strip()
        desc_seg      = (request.form.get('descripcion_seguimiento') or '').strip()

        # Crear registro
        rfc = CambioRFCRegistro(
            ticket=ticket,
            fecha_solicitud=fecha_solicitud,
            responsable_solicitud_id=responsable_id,
            responsable_solicitud_nombre=resp_nombre,
            responsable_solicitud_cargo=resp_cargo,

            descripcion=descripcion,
            antecedentes=antecedentes,
            objetivo=objetivo,
            alcance=alcance,
            ambiente=ambiente,
            partes_interesadas=partes,
            recursos_necesarios=recursos,
            tipo_cambio=tipo_cambio,
            prioridad=prioridad,

            ajustes_requeridos=ajustes_req,
            cambios_requeridos=cambios_req,
            estado_seguridad="Pendiente de aprobación por seguridad",
            revisa_persona_id=revisa_id,
            revisa_nombre=revisa_nombre,
            revisa_cargo=revisa_cargo,
            revisa_observaciones=revisa_obs,
            revisa_fecha=revisa_fecha,

            aprueba_persona_id=aprueba_id,
            aprueba_nombre=aprueba_nombre,
            aprueba_cargo=aprueba_cargo,
            aprueba_observaciones=aprueba_obs,
            aprueba_fecha=aprueba_fecha,

            implementa_persona_id=impl_id_pers,
            implementa_nombre=implementa_nombre,
            implementa_cargo=implementa_cargo,
            implementa_observaciones=impl_obs_pers,
            implementa_fecha=impl_fecha_pers,

            cambio_eficaz=cambio_eficaz,
            descripcion_seguimiento=desc_seg
        )

        db.session.add(rfc)
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
                    rfc_id=rfc.id,
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
                    rfc_id=rfc.id,
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
                    rfc_id=rfc.id,
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

            # Los campos del capítulo solo se guardan en el PRIMER registro
            tmon          = impl_tmon_unico if i == 0 else ''
            fecha_apr     = impl_fap_unica if i == 0 else ''
            fecha_tent    = impl_ftc_unica if i == 0 else ''
            fecha_real    = impl_frc_unica if i == 0 else ''
            observaciones = impl_obs_unica if i == 0 else ''

            if any([actividad, responsable, fecha, ejecucion, tmon, fecha_apr, fecha_tent, fecha_real, observaciones]):
                db.session.add(CambioRFCImplementacion(
                    rfc_id=rfc.id,
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

        # Evidencias (PDF)
        files = request.files.getlist('evidencias')
        for f in files:
            if not f or not f.filename:
                continue
            if not is_allowed_pdf_rfc(f.filename):
                flash(f"Archivo no permitido (solo PDF): {f.filename}", "danger")
                continue

            store_name = unique_store_name(f.filename)
            path = os.path.join(app.config['UPLOAD_RFC_DIR'], store_name)
            f.save(path)

            ev = CambioRFCEvidencia(
                rfc=rfc,
                filename=store_name,
                original_name=secure_filename(f.filename),
                mime='application/pdf',
                size=os.path.getsize(path)
            )
            db.session.add(ev)

        db.session.commit()
        flash("Solicitud de cambio (RFC) registrada.", "success")
        return redirect(url_for('rfc_matriz'))

    # GET – formulario
    html = """
    <div class="rfcadd-shell">

      <!-- CABECERA -->
      <div class="rfcadd-header-card">
        <div class="rfcadd-header-overlay">
          <div class="rfcadd-header-text">
            <h3 class="rfcadd-title m-0">Agregar Solicitud de Cambios (RFC)</h3>
            <div class="rfcadd-subtitle">
              Registro, evaluación, aprobación, implementación y seguimiento de solicitudes de cambio del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="rfcadd-header-actions">
        <a href="{{ url_for('rfc_menu') }}"
           class="btn rounded-pill px-5 fw-bold rfcadd-back-btn">
          ⬅ Volver a la Matriz Solicitud de Cambios
        </a>
      </div>

      <!-- TARJETA PRINCIPAL -->
      <div class="rfcadd-card">
        <div class="rfcadd-card-body">

          <form method="post" enctype="multipart/form-data">
            <div class="row g-3">

              <!-- Información general -->
              <div class="col-12">
                <div class="rfcadd-section-title">Información general</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Ticket o No. de solicitud</label>
                <input type="text" name="ticket" class="form-control" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha Solicitud</label>
                <input type="date" name="fecha_solicitud" class="form-control" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Responsable de la solicitud (Nombre responsable del área)</label>
                <select name="responsable_solicitud_id"
                        id="responsable_solicitud_id"
                        class="form-select"
                        onchange="fillCargoDesdeArea('responsable_solicitud_id','responsable_solicitud_cargo')">
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}" data-cargo="{{ a.responsable_cargo or '' }}">
                      {{ a.responsable_nombre }}
                    </option>
                  {% endfor %}
                </select>

                <input type="text"
                       id="responsable_solicitud_cargo"
                       class="form-control mt-1"
                       placeholder="Cargo (Responsable de área)"
                       readonly>
              </div>

              <!-- Información del cambio -->
              <div class="col-12 mt-3">
                <div class="rfcadd-section-title">Información del cambio</div>
              </div>

              <div class="col-12">
                <label class="form-label">Descripción (Qué se requiere)</label>
                <textarea name="descripcion" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-12">
                <label class="form-label">Antecedentes (Por qué se requiere)</label>
                <textarea name="antecedentes" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-12">
                <label class="form-label">Objetivo (Qué se busca lograr)</label>
                <textarea name="objetivo" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-12">
                <label class="form-label">Alcance</label>
                <textarea name="alcance" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Ambiente</label>
                <select name="ambiente" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Producción">Producción</option>
                  <option value="Contingencia">Contingencia</option>
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Tipo de cambio</label>
                <select name="tipo_cambio" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Planificado (normal)">Planificado (normal)</option>
                  <option value="No planificado (emergencia)">No planificado (emergencia)</option>
                  <option value="Tipificado (recurrente)">Tipificado (recurrente)</option>
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Prioridad del cambio</label>
                <select name="prioridad" id="prioridad" class="form-select" onchange="setPrioridadColor()">
                  <option value="">-- Seleccione --</option>
                  <option value="Alta">Alta</option>
                  <option value="Media">Media</option>
                  <option value="Baja">Baja</option>
                </select>
                <small id="prioridad_badge" class="badge mt-1">Sin definir</small>
              </div>

              <div class="col-12">
                <label class="form-label">Partes interesadas impactadas</label>
                <textarea name="partes_interesadas" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-12">
                <label class="form-label">Recursos necesarios</label>
                <textarea name="recursos_necesarios" class="form-control" rows="2"></textarea>
              </div>

              <!-- Evaluación de riesgos -->
              <div class="col-12 mt-3">
                <div class="d-flex justify-content-between align-items-center">
                  <div class="rfcadd-section-title mb-0">Evaluación de riesgos</div>
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
                  <div class="rfcadd-section-title mb-0">Plan de pruebas (si aplica)</div>
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
                  <div class="rfcadd-section-title mb-0">Plan de Marcha Atrás (Rollback)</div>
                  <button type="button" class="btn btn-outline-primary btn-sm rounded-pill" onclick="addRollbackRow()">
                    + Agregar registro
                  </button>
                </div>
              </div>

              <div class="col-12">
                <div id="rollback-container"></div>
              </div>

              <!-- Actividades implementadas -->
              <div class="col-12 mt-3">
                <div class="d-flex justify-content-between align-items-center">
                  <div class="rfcadd-section-title mb-0">Actividades implementadas del cambio</div>
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
                      <input type="text" name="impl_tiempo_monitoreo_unico" class="form-control">
                    </div>

                    <div class="col-md-3">
                      <label class="form-label">Fecha aprobación</label>
                      <input type="date" name="impl_fecha_aprobacion_unica" class="form-control">
                    </div>

                    <div class="col-md-3">
                      <label class="form-label">Fecha tentativa cierre</label>
                      <input type="date" name="impl_fecha_tentativa_cierre_unica" class="form-control">
                    </div>

                    <div class="col-md-3">
                      <label class="form-label">Fecha real cierre</label>
                      <input type="date" name="impl_fecha_real_cierre_unica" class="form-control">
                    </div>

                    <div class="col-md-12">
                      <label class="form-label">Observaciones</label>
                      <textarea name="impl_observaciones_unicas" class="form-control" rows="2"></textarea>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Aprobación del cambio -->
              <div class="col-12 mt-3">
                <div class="rfcadd-section-title">Aprobación del cambio</div>
              </div>

              <div class="col-md-3">
                <label class="form-label">Se requiere realizar ajustes?</label>
                <select name="ajustes_requeridos" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Si">Si</option>
                  <option value="No">No</option>
                </select>
              </div>

              <div class="col-md-9">
                <label class="form-label">Cambios requeridos (si se requieren)</label>
                <textarea name="cambios_requeridos" class="form-control" rows="2"></textarea>
              </div>

              <!-- Revisa -->
              <div class="col-12 mt-2">
                <div class="rfcadd-subsection-title">Revisa</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre responsable del área</label>
                <select name="revisa_persona_id"
                        id="revisa_persona_id"
                        class="form-select"
                        onchange="fillCargoDesdeArea('revisa_persona_id','revisa_cargo')">
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}" data-cargo="{{ a.responsable_cargo or '' }}">
                      {{ a.responsable_nombre }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Cargo (Responsable de área)</label>
                <input type="text" id="revisa_cargo" class="form-control" readonly>
              </div>

              <div class="col-md-4">
                <label class="form-label">Observaciones</label>
                <textarea name="revisa_observaciones" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha revisión</label>
                <input type="date" name="revisa_fecha" class="form-control">
              </div>

              <!-- Aprueba -->
              <div class="col-12 mt-2">
                <div class="rfcadd-subsection-title">Aprueba (Comité de cambios)</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre responsable del área</label>
                <select name="aprueba_persona_id"
                        id="aprueba_persona_id"
                        class="form-select"
                        onchange="fillCargoDesdeArea('aprueba_persona_id','aprueba_cargo')">
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}" data-cargo="{{ a.responsable_cargo or '' }}">
                      {{ a.responsable_nombre }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Cargo (Responsable de área)</label>
                <input type="text" id="aprueba_cargo" class="form-control" readonly>
              </div>

              <div class="col-md-4">
                <label class="form-label">Observaciones</label>
                <textarea name="aprueba_observaciones" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha revisión</label>
                <input type="date" name="aprueba_fecha" class="form-control">
              </div>

              <!-- Implementa -->
              <div class="col-12 mt-2">
                <div class="rfcadd-subsection-title">Implementa</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre responsable del área</label>
                <select name="implementa_persona_id"
                        id="implementa_persona_id"
                        class="form-select"
                        onchange="fillCargoDesdeArea('implementa_persona_id','implementa_cargo')">
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}" data-cargo="{{ a.responsable_cargo or '' }}">
                      {{ a.responsable_nombre }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Cargo (Responsable de área)</label>
                <input type="text" id="implementa_cargo" class="form-control" readonly>
              </div>

              <div class="col-md-4">
                <label class="form-label">Observaciones</label>
                <textarea name="implementa_observaciones" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha revisión</label>
                <input type="date" name="implementa_fecha" class="form-control">
              </div>

              <!-- Seguimiento -->
              <div class="col-12 mt-3">
                <div class="rfcadd-section-title">Seguimiento del cambio</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">¿El cambio fue eficaz?</label>
                <select name="cambio_eficaz" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Si">Si</option>
                  <option value="No">No</option>
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Descripción del seguimiento</label>
                <textarea name="descripcion_seguimiento" class="form-control" rows="2"></textarea>
              </div>

              <!-- Evidencias -->
              <div class="col-12 mt-3">
                <label class="form-label">Evidencias (PDF, puedes adjuntar varios)</label>

                <input
                  type="file"
                  id="evidencias"
                  name="evidencias"
                  accept=".pdf"
                  multiple
                  class="form-control"
                  onchange="acumularEvidenciasRFC(this)"
                >
                <small class="text-muted">
                  Puedes seleccionar varios a la vez o ir agregando en varias rondas.
                </small>

                <div id="lista_evidencias_nuevas" class="mt-2"></div>
              </div>

            </div>

            <div class="rfcadd-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>
              <a href="{{ url_for('rfc_menu') }}"
                 class="btn rounded-pill px-4 fw-bold rfcadd-cancel-btn">
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

      .rfcadd-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .rfcadd-header-card{
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

      .rfcadd-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .rfcadd-header-overlay{
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

      .rfcadd-header-overlay::before{
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

      .rfcadd-header-text{
        max-width:1200px;
        width:100%;
      }

      .rfcadd-header-text::before{
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

      .rfcadd-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .rfcadd-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .rfcadd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .rfcadd-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .rfcadd-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .rfcadd-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .rfcadd-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .rfcadd-card-body{
        padding:18px;
      }

      .rfcadd-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .rfcadd-card .form-control,
      .rfcadd-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .rfcadd-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .rfcadd-card .form-control:focus,
      .rfcadd-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .rfcadd-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .rfcadd-subsection-title{
        font-weight:900;
        font-size:.82rem;
        color:#25324a;
        padding:9px 12px;
        background:#f8fbff;
        border-radius:12px;
        border:1px solid #dbe6f4;
        margin-bottom:10px;
      }

      .dynamic-block{
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%) !important;
        border:1px solid #dbe6f4 !important;
        border-radius:14px !important;
        box-shadow:0 6px 14px rgba(15,23,42,.08);
        padding:12px !important;
      }

      .rfcadd-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
      }

      .rfcadd-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .rfcadd-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .rfcadd-cancel-btn:hover{
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
        .rfcadd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .rfcadd-header-card{
          min-height:88px;
        }

        .rfcadd-title{
          font-size:1.20rem;
        }

        .rfcadd-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .rfcadd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .rfcadd-header-overlay::before{
          margin:0;
        }

        .rfcadd-header-actions .btn,
        .rfcadd-bottom-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      function setPrioridadColor(){
        const sel = document.getElementById('prioridad');
        const badge = document.getElementById('prioridad_badge');
        if(!sel || !badge) return;
        badge.className = 'badge mt-1';
        const val = sel.value || '';
        if (val === 'Alta'){
          badge.classList.add('badge-prio-alta');
          badge.innerText = 'Alta';
        } else if (val === 'Media'){
          badge.classList.add('badge-prio-media');
          badge.innerText = 'Media';
        } else if (val === 'Baja'){
          badge.classList.add('badge-prio-baja');
          badge.innerText = 'Baja';
        } else {
          badge.innerText = 'Sin definir';
        }
      }

      function fillCargoDesdeArea(selectId, cargoInputId){
        const sel = document.getElementById(selectId);
        const opt = sel && sel.selectedOptions && sel.selectedOptions[0];
        const cargo = opt ? (opt.getAttribute('data-cargo') || '') : '';

        const inpCar = document.getElementById(cargoInputId);
        if (inpCar) inpCar.value = cargo;
      }
    </script>

    <script>
      let evidenciasRFCBufferDT = new DataTransfer();

      function renderListaEvidenciasRFC() {
        const cont = document.getElementById('lista_evidencias_nuevas');
        if (!cont) return;

        cont.innerHTML = '';
        if (evidenciasRFCBufferDT.files.length === 0) {
          cont.innerHTML = '<div class="text-muted small">No hay archivos seleccionados</div>';
          return;
        }

        for (let i = 0; i < evidenciasRFCBufferDT.files.length; i++) {
          const f = evidenciasRFCBufferDT.files[i];
          const row = document.createElement('div');
          row.className = 'd-flex align-items-center justify-content-between mb-1';
          row.innerHTML = `
            <span class="text-truncate small" style="max-width:260px;">📎 ${f.name}</span>
            <button type="button"
                    class="btn btn-link text-danger p-0 small"
                    onclick="removeEvidenciaRFC(${i})">
              🗑️
            </button>
          `;
          cont.appendChild(row);
        }
      }

      function acumularEvidenciasRFC(inputEl) {
        for (const f of inputEl.files) {
          evidenciasRFCBufferDT.items.add(f);
        }
        inputEl.files = evidenciasRFCBufferDT.files;
        renderListaEvidenciasRFC();
      }

      function removeEvidenciaRFC(index) {
        const tmp = new DataTransfer();
        for (let i = 0; i < evidenciasRFCBufferDT.files.length; i++) {
          if (i !== index) {
            tmp.items.add(evidenciasRFCBufferDT.files[i]);
          }
        }
        evidenciasRFCBufferDT = tmp;

        const inputEl = document.getElementById('evidencias');
        if (inputEl) {
          inputEl.files = evidenciasRFCBufferDT.files;
        }
        renderListaEvidenciasRFC();
      }

      window.addEventListener('DOMContentLoaded', () => {
        renderListaEvidenciasRFC();
      });
    </script>

    <script>
      function removeDynamicBlock(btn){
        const block = btn.closest('.dynamic-block');
        if (block) block.remove();
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

    </script>

    <script>
      function addRiesgoRow(data = {}) {
        const container = document.getElementById('riesgos-container');
        const div = document.createElement('div');
        div.className = 'dynamic-block border rounded p-3 mb-3 bg-light';

        div.innerHTML = `
          <div class="d-flex justify-content-between align-items-center mb-2">
            <strong>Registro evaluación de riesgo</strong>
            <button type="button" class="btn btn-outline-danger btn-sm rounded-pill" onclick="removeDynamicBlock(this)">
              Eliminar
            </button>
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
    </script>
    """
    inner = render_template_string(html, areas=areas)
    return render_template_string(BASE, content=Markup(inner))

