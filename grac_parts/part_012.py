@app.route('/metricas/configuracion/vulnerabilidades', methods=['GET', 'POST'])
@login_required
def config_param_vulnerabilidades():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('menu'))

    if user.role != 'admin' and not verificar_permiso(user, "Métricas"):
        flash("No tiene permiso para configurar vulnerabilidades.", "danger")
        return redirect(url_for('menu'))

    # Obtener (o crear) la única configuración
    config = MetricasVulnerabilidadesConfig.query.first()
    if not config:
        config = MetricasVulnerabilidadesConfig(
            creado_por_id=user.id if user else None
        )
        db.session.add(config)
        db.session.commit()

    if request.method == 'POST':
        # --------- META ANUAL -----------
        meta_str = (request.form.get('meta_anual_vuln') or '').strip()
        if meta_str:
            try:
                config.meta_anual_activas = float(meta_str)
            except ValueError:
                flash("La meta anual debe ser un número válido.", "danger")
                return redirect(url_for('config_param_vulnerabilidades'))
        else:
            config.meta_anual_activas = None

        # --------- TABLA DE CLASIFICACIONES -----------
        clasificaciones = request.form.getlist('clasificacion[]')
        cantidades      = request.form.getlist('cantidad[]')
        tiempos_cierre  = request.form.getlist('tiempo_cierre[]')  # SLA de cierre

        # Limpiar filas existentes
        config.clasificaciones.clear()

        for cla, cant, t_cierre in zip(clasificaciones, cantidades, tiempos_cierre):
            cla = (cla or '').strip()
            if not cla:
                continue

            try:
                cant_val = int(cant) if cant else None
            except ValueError:
                cant_val = None

            try:
                t_cierre_val = int(t_cierre) if t_cierre else None
            except ValueError:
                t_cierre_val = None

            fila = MetricasVulnerabilidadesClasificacion(
                clasificacion=cla,
                cantidad_aceptada=cant_val,
                # porcentaje_cumplimiento ya no se captura desde pantalla
                porcentaje_cumplimiento=None,
                tiempo_max_cierre_dias=t_cierre_val,
            )
            config.clasificaciones.append(fila)

        db.session.commit()
        flash("Parámetros de vulnerabilidades guardados correctamente.", "success")
        return redirect(url_for('config_param_vulnerabilidades'))

    # --------- GET: preparar datos para el template ----------
    meta_anual_pct = config.meta_anual_activas
    niveles = config.clasificaciones

    content = render_template_string("""
    <div class="vulnpar-shell">

      <!-- CABECERA -->
      <div class="vulnpar-header-card">
        <div class="vulnpar-header-overlay">
          <div class="vulnpar-header-text">
            <h3 class="vulnpar-title m-0">Parámetros de Vulnerabilidades</h3>
            <div class="vulnpar-subtitle">
              Define la cantidad aceptada de vulnerabilidades activas por clasificación,
              la meta anual de vulnerabilidades activas y los tiempos máximos de cierre por criticidad.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="vulnpar-header-actions">
       
      </div>

      <!-- TARJETA PRINCIPAL -->
      <div class="vulnpar-card p-4">

        <div class="vulnpar-section-title">
          Configuración general
        </div>

        <form method="POST">

          <!-- META ANUAL -->
          <div class="mb-4">
            <label for="meta_anual_vuln" class="form-label fw-semibold">
              META ANUAL DE VULNERABILIDADES ACTIVAS A CIERRE DE AÑO (%)
            </label>

            <div class="input-group">
              <input type="number" step="0.01" min="0" max="100"
                     class="form-control"
                     id="meta_anual_vuln" name="meta_anual_vuln"
                     value="{{ meta_anual_pct if meta_anual_pct is not none else '' }}"
                     placeholder="Ej: 10">
              <span class="input-group-text">%</span>
            </div>

            <div class="form-text">
              Porcentaje objetivo de vulnerabilidades activas al cierre del año frente al inventario total.
            </div>
          </div>

          <div class="vulnpar-section-title">
            Parámetros por clasificación de vulnerabilidades
          </div>

          <div class="table-responsive vulnpar-table-wrap">
            <table class="table table-sm align-middle mb-0" id="tabla-vuln-clasificaciones">
              <thead class="vulnpar-table-head">
                <tr>
                  <th style="min-width:140px;">Clasificación</th>
                  <th style="min-width:180px;">
                    Tiempo Máximo de Cierre<br>(días)
                  </th>
                  <th style="min-width:220px;">
                    Cantidad de Vulnerabilidades Activas Mesuales Aceptadas Según Su Clasificación 
                  </th>
                  <th class="text-center" style="width:80px;">Acciones</th>
                </tr>
              </thead>

              <tbody id="body-vuln-clasificaciones">
                {% if niveles %}
                  {% for n in niveles %}
                    <tr>
                      <td>
                        <select name="clasificacion[]" class="form-select">
                          <option value="">-- Seleccione --</option>
                          {% for op in clasif_choices %}
                            <option value="{{ op }}" {% if n.clasificacion == op %}selected{% endif %}>
                              {{ op }}
                            </option>
                          {% endfor %}
                        </select>
                      </td>
                      <td>
                        <input type="number" min="0" step="1"
                               name="tiempo_cierre[]" class="form-control"
                               value="{{ n.tiempo_max_cierre_dias if n.tiempo_max_cierre_dias is not none else '' }}"
                               placeholder="Ej: 7">
                      </td>
                      <td>
                        <input type="number" min="0" step="1"
                               name="cantidad[]" class="form-control"
                               value="{{ n.cantidad_aceptada if n.cantidad_aceptada is not none else '' }}"
                               placeholder="Cantidad aceptada">
                      </td>
                      <td class="text-center">
                        <button type="button"
                                class="btn btn-outline-danger btn-sm rounded-pill px-3"
                                onclick="eliminarFilaVuln(this)">🗑️</button>
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
                            <option value="{{ opcion }}" {% if opcion == op %}selected{% endif %}>
                              {{ opcion }}
                            </option>
                          {% endfor %}
                        </select>
                      </td>
                      <td>
                        <input type="number" min="0" step="1"
                               name="tiempo_cierre[]" class="form-control"
                               placeholder="Ej: 7">
                      </td>
                      <td>
                        <input type="number" min="0" step="1"
                               name="cantidad[]" class="form-control"
                               placeholder="Cantidad aceptada">
                      </td>
                      <td class="text-center">
                        <button type="button"
                                class="btn btn-outline-danger btn-sm rounded-pill px-3"
                                onclick="eliminarFilaVuln(this)">🗑️</button>
                      </td>
                    </tr>
                  {% endfor %}
                {% endif %}
              </tbody>
            </table>
          </div>

          <div class="mt-3 d-flex justify-content-start">
            <button type="button"
                    class="btn btn-outline-primary btn-sm rounded-pill px-4"
                    onclick="agregarFilaVuln()">
              ➕ Agregar clasificación
            </button>
          </div>

          <div class="d-flex justify-content-center mt-4">
            <button type="submit" class="btn btn-success rounded-pill px-4 fw-semibold">
              💾 Guardar parámetros
            </button>
          </div>

        </form>
      </div>
    </div>

    <script>
      function agregarFilaVuln() {
        const tbody = document.getElementById('body-vuln-clasificaciones');
        const filas = tbody.getElementsByTagName('tr');
        const ultima = filas[filas.length - 1];
        const nueva = ultima.cloneNode(true);

        const inputs = nueva.querySelectorAll('input');
        inputs.forEach(input => input.value = '');

        const selects = nueva.querySelectorAll('select');
        selects.forEach(sel => sel.value = '');

        tbody.appendChild(nueva);
      }

      function eliminarFilaVuln(btn) {
        const tbody = document.getElementById('body-vuln-clasificaciones');
        const filas = tbody.getElementsByTagName('tr');
        if (filas.length > 1) {
          btn.closest('tr').remove();
        }
      }
    </script>

    <style>
      body {
        background-image: url('/static/img/ccsgsi.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
      }

      .vulnpar-shell {
        width: 96%;
        max-width: 1200px;
        margin: 26px auto 24px auto;
        overflow: hidden;
      }

      .vulnpar-header-card {
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

      .vulnpar-header-card::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .vulnpar-header-overlay {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        text-align: left;
        position: relative;
        z-index: 1;
        min-width: 0;
      }

      .vulnpar-header-overlay::before {
        content: "🛡️";
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

      .vulnpar-header-text {
        max-width: 1000px;
        min-width: 0;
      }

      .vulnpar-header-text::before {
        content: "SGSI · Parámetros de Vulnerabilidades";
        display: inline-block;
        background: rgba(255,255,255,.18);
        border-radius: 999px;
        padding: 3px 10px;
        font-size: .65rem;
        font-weight: 800;
        margin-bottom: 4px;
        color: #ffffff;
      }

      .vulnpar-title {
        color: #ffffff !important;
        font-weight: 950;
        font-size: 1.32rem;
        line-height: 1.1;
        margin: 0 !important;
        text-shadow: 0 4px 14px rgba(0,0,0,.45);
        overflow-wrap: break-word;
      }

      .vulnpar-subtitle {
        color: rgba(255,255,255,.95);
        font-size: .78rem;
        line-height: 1.25;
        margin-top: 3px;
        overflow-wrap: break-word;
      }

      .vulnpar-header-actions {
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

      .vulnpar-btn-main {
        background: #ffffff;
        color: #0f172a;
        border: 1px solid #cfd8e3;
      }

      .vulnpar-btn-main:hover {
        background: #edf5ff;
        color: #0b65d8;
      }

      .vulnpar-card {
        background: rgba(255,255,255,.96) !important;
        border-radius: 18px;
        backdrop-filter: blur(8px);
        box-shadow: 0 12px 24px rgba(15,23,42,.18);
        border: 1px solid rgba(219,230,244,.9);
        overflow: hidden;
        width: 100%;
        max-width: 100%;
      }

      .vulnpar-card .card-body {
        padding: 22px;
      }

      .vulnpar-section-title {
        font-weight: 950;
        font-size: .95rem;
        color: #0b4a8f;
        margin-bottom: 16px;
        border-bottom: 2px solid rgba(59,130,246,.18);
        padding-bottom: 8px;
        overflow-wrap: break-word;
      }

      .vulnpar-table-wrap {
        border: 1px solid #e2ebf5;
        border-radius: 14px;
        background: #ffffff;
        overflow-x: auto;
        overflow-y: hidden;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.35);
        width: 100%;
        max-width: 100%;
      }

      .vulnpar-table-wrap .table {
        margin-bottom: 0;
        min-width: 780px;
      }

      .vulnpar-table-wrap thead th,
      .vulnpar-table-head th {
        background: #eef5ff !important;
        font-weight: 900;
        color: #0b4a8f;
        border-bottom: 1px solid #d7dee7 !important;
        vertical-align: middle !important;
        white-space: nowrap;
        font-size: .82rem;
      }

      .vulnpar-table-wrap tbody td {
        vertical-align: middle;
        font-size: .85rem;
        color: #334155;
      }

      .vulnpar-table-wrap tbody tr:last-child td {
        border-bottom: none;
      }

      .vulnpar-table-wrap tbody tr:hover {
        background: #f8fbff;
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

      .input-group-text {
        border-radius: 0 10px 10px 0;
        background: #eef5ff;
        border-color: #d9e3f0;
        color: #0b4a8f;
        font-weight: 900;
      }

      .vulnpar-btn-add {
        border-radius: 10px;
        font-weight: 900;
        box-shadow: 0 4px 10px rgba(0,0,0,.08);
      }

      .vulnpar-btn-del {
        border-radius: 10px;
        font-weight: 900;
      }

      h3 {
        color: #ffffff;
        margin: 0;
      }

      @media (max-width: 992px) {
        .vulnpar-shell {
          width: 98%;
          margin: 8px auto 22px auto;
        }

        .vulnpar-title {
          font-size: 1.20rem;
        }

        .vulnpar-subtitle {
          font-size: .76rem;
        }

        .vulnpar-card .card-body {
          padding: 16px;
        }
      }

      @media (max-width: 768px) {
        .vulnpar-header-overlay {
          flex-direction: column;
          text-align: center;
          gap: 10px;
        }

        .vulnpar-header-overlay::before {
          margin: 0;
        }

        .vulnpar-title,
        .vulnpar-subtitle {
          text-align: center;
        }

        .vulnpar-header-actions .btn {
          width: 100%;
        }
      }
    </style>
    """, meta_anual_pct=meta_anual_pct, niveles=niveles, clasif_choices=VULN_CLASIFICACIONES)

    return render_template_string(BASE, content=content)


#=================================
# Configuración de Cultura
#=================================

@app.route('/metricas/configuracion/cultura', methods=['GET', 'POST'])
@login_required
def config_param_cultura():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('menu'))

    if user.role != 'admin' and not verificar_permiso(user, "Métricas"):
        flash("No tiene permiso para configurar cultura.", "danger")
        return redirect(url_for('menu'))
    # Siempre trabajamos sobre ÚNICO registro de configuración
    config = MetricasCulturaConfig.query.first()

    if request.method == 'POST':
        # Leemos los valores del formulario
        meta_general_raw = request.form.get('meta_general') or None
        meta_fi_raw      = request.form.get('meta_fi') or None
        meta_ep_raw      = request.form.get('meta_ep') or None

        # Convertimos a float cuando venga algo
        def to_float(valor):
            if valor is None or valor == '':
                return None
            try:
                return float(valor)
            except ValueError:
                return None

        meta_general = to_float(meta_general_raw)
        meta_fi      = to_float(meta_fi_raw)
        meta_ep      = to_float(meta_ep_raw)

        # Si no existe registro, lo creamos
        if not config:
            config = MetricasCulturaConfig()

        config.meta_general = meta_general
        config.meta_fi      = meta_fi
        config.meta_ep      = meta_ep

        try:
            db.session.add(config)
            db.session.commit()
            flash("Parámetros de Cultura guardados correctamente.", "success")
        except Exception as e:
            db.session.rollback()
            print("Error al guardar configuración de cultura:", e)
            flash("Ocurrió un error al guardar los parámetros de cultura.", "danger")

        return redirect(url_for('config_param_cultura'))

    # GET → mostramos el formulario con los valores guardados (si existen)
    content = render_template_string("""
    <div class="cultcfg-shell">

      <!-- CABECERA -->
      <div class="cultcfg-header-card">
        <div class="cultcfg-header-overlay">
          <div class="cultcfg-header-text">
            <h3 class="cultcfg-title m-0">Parámetros de Cultura de Seguridad / Ciberseguridad</h3>
            <div class="cultcfg-subtitle">
              Define las metas generales e individuales asociadas a la efectividad de la formación
              y la ejecución de la planeación en Cultura de Seguridad.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="cultcfg-header-actions">
    
      </div>

      <!-- TARJETA PRINCIPAL -->
      <div class="cultcfg-card p-4">

        <div class="cultcfg-section-title">
          Configuración de metas
        </div>

        <form method="POST">

          <!-- META GENERAL -->
          <div class="mb-4">
            <label for="meta_general" class="form-label fw-semibold">
              Cumplimiento Programa Capacitación (%)
            </label>

            <div class="input-group">
              <input type="number" step="0.01" min="0" max="100"
                     class="form-control"
                     id="meta_general" name="meta_general"
                     value="{{ config.meta_general if config and config.meta_general is not none else '' }}"
                     placeholder="Ej: 90">
              <span class="input-group-text">%</span>
            </div>

            <div class="form-text">
              Porcentaje global objetivo de cumplimiento de Cultura de Seguridad.
            </div>
          </div>

          <div class="cultcfg-section-title">
            Metas individuales
          </div>

          <!-- META FI -->
          <div class="mb-3">
            <label for="meta_fi" class="form-label fw-semibold">
              Cobertura (%)
            </label>

            <div class="input-group">
              <input type="number" step="0.01" min="0" max="100"
                     class="form-control"
                     id="meta_fi" name="meta_fi"
                     value="{{ config.meta_fi if config and config.meta_fi is not none else '' }}"
                     placeholder="Ej: 85">
              <span class="input-group-text">%</span>
            </div>

            <div class="form-text">
              Meta de la cobertura.
            </div>
          </div>

          <!-- META EP -->
          <div class="mb-3">
            <label for="meta_ep" class="form-label fw-semibold">
              Evaluaciones Eficaces (%)
            </label>

            <div class="input-group">
              <input type="number" step="0.01" min="0" max="100"
                     class="form-control"
                     id="meta_ep" name="meta_ep"
                     value="{{ config.meta_ep if config and config.meta_ep is not none else '' }}"
                     placeholder="Ej: 80">
              <span class="input-group-text">%</span>
            </div>

            <div class="form-text">
              Meta de la eficacia de las evaluaciones.
            </div>
          </div>

          <div class="d-flex justify-content-center mt-4">
            <button type="submit" class="btn btn-success rounded-pill px-4 fw-semibold">
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

      .cultcfg-shell {
        width: 96%;
        max-width: 1200px;
        margin: 26px auto 24px auto;
        overflow: hidden;
      }

      .cultcfg-header-card {
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

      .cultcfg-header-card::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .cultcfg-header-overlay {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        text-align: left;
        position: relative;
        z-index: 1;
        min-width: 0;
      }

      .cultcfg-header-overlay::before {
        content: "🎓";
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

      .cultcfg-header-text {
        max-width: 1000px;
        min-width: 0;
      }

      .cultcfg-header-text::before {
        content: "SGSI · Configuración de Cultura de Seguridad";
        display: inline-block;
        background: rgba(255,255,255,.18);
        border-radius: 999px;
        padding: 3px 10px;
        font-size: .65rem;
        font-weight: 800;
        margin-bottom: 4px;
        color: #ffffff;
      }

      .cultcfg-title {
        color: #ffffff !important;
        font-weight: 950;
        font-size: 1.32rem;
        line-height: 1.1;
        margin: 0 !important;
        text-shadow: 0 4px 14px rgba(0,0,0,.45);
        overflow-wrap: break-word;
      }

      .cultcfg-subtitle {
        color: rgba(255,255,255,.95);
        font-size: .78rem;
        line-height: 1.25;
        margin-top: 3px;
        overflow-wrap: break-word;
      }

      .cultcfg-header-actions {
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

      .cultcfg-btn-main {
        background: #ffffff;
        color: #0f172a;
        border: 1px solid #cfd8e3;
      }

      .cultcfg-btn-main:hover {
        background: #edf5ff;
        color: #0b65d8;
      }

      .cultcfg-card {
        background: rgba(255,255,255,.96) !important;
        border-radius: 18px;
        backdrop-filter: blur(8px);
        box-shadow: 0 12px 24px rgba(15,23,42,.18);
        border: 1px solid rgba(219,230,244,.9);
        overflow: hidden;
        width: 100%;
        max-width: 100%;
      }

      .cultcfg-card .card-body {
        padding: 22px;
      }

      .cultcfg-section-title {
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

      .input-group-text {
        border-radius: 0 10px 10px 0;
        background: #eef5ff;
        border-color: #d9e3f0;
        color: #0b4a8f;
        font-weight: 900;
      }

      .cultcfg-btn-add {
        border-radius: 10px;
        font-weight: 900;
        box-shadow: 0 4px 10px rgba(0,0,0,.08);
      }

      .cultcfg-btn-del {
        border-radius: 10px;
        font-weight: 900;
      }

      h3 {
        color: #ffffff;
        margin: 0;
      }

      @media (max-width: 992px) {
        .cultcfg-shell {
          width: 98%;
          margin: 8px auto 22px auto;
        }

        .cultcfg-title {
          font-size: 1.20rem;
        }

        .cultcfg-subtitle {
          font-size: .76rem;
        }

        .cultcfg-card .card-body {
          padding: 16px;
        }
      }

      @media (max-width: 768px) {
        .cultcfg-header-overlay {
          flex-direction: column;
          text-align: center;
          gap: 10px;
        }

        .cultcfg-header-overlay::before {
          margin: 0;
        }

        .cultcfg-title,
        .cultcfg-subtitle {
          text-align: center;
        }

        .cultcfg-header-actions .btn {
          width: 100%;
        }
      }
    </style>
    """, config=config)

    return render_template_string(BASE, content=content)

#=================================
# Métricas de riesgos
#=================================

# =========================================
# HELPERS MÉTRICAS DE RIESGOS
# =========================================
RISK_ORDER = ["Bajo", "Medio", "Alto", "Muy Alto", "Extremo"]

def _risk_norm_text(v):
    txt = str(v or "").strip().upper()
    txt = (
        txt.replace("Á", "A")
           .replace("É", "E")
           .replace("Í", "I")
           .replace("Ó", "O")
           .replace("Ú", "U")
    )
    return txt

def normalize_level(raw):
    """
    Normaliza niveles de riesgo a:
    Bajo, Medio, Alto, Muy Alto, Extremo
    """
    txt = _risk_norm_text(raw)

    if not txt:
        return ""

    if "EXTREMO" in txt:
        return "Extremo"

    if "MUY ALTO" in txt or "MUYALTO" in txt:
        return "Muy Alto"

    if "MODERADO" in txt or "MEDIO" in txt or "MEDIA" in txt:
        return "Medio"

    if "ALTO" in txt:
        return "Alto"

    if "BAJO" in txt or "BAJA" in txt:
        return "Bajo"

    # fallback si viene valor numérico o texto con número
    try:
        n = int(str(raw).split()[0])
        if 1 <= n <= 4:
            return "Bajo"
        elif n <= 8:
            return "Medio"
        elif n <= 12:
            return "Alto"
        elif n <= 20:
            return "Muy Alto"
        else:
            return "Extremo"
    except Exception:
        pass

    return ""

def level_rank(raw):
    lvl = normalize_level(raw)
    if lvl in RISK_ORDER:
        return RISK_ORDER.index(lvl)
    return -1

def dominant_level(counts_dict):
    """
    Retorna el nivel dominante.
    Si hay empate, devuelve el nivel más alto.
    """
    if not counts_dict:
        return ""

    best_level = ""
    best_count = -1

    for lvl in RISK_ORDER:
        val = int((counts_dict or {}).get(lvl, 0) or 0)
        if val > best_count:
            best_count = val
            best_level = lvl
        elif val == best_count and best_count > 0:
            if level_rank(lvl) > level_rank(best_level):
                best_level = lvl

    return best_level if best_count > 0 else ""

def safe_appetite_level(raw, default="Moderado"):
    lvl = normalize_level(raw)
    if lvl:
        return lvl

    d = normalize_level(default)
    return d or "Medio"

def is_outside_appetite(nivel_residual, apetito):
    """
    Fuera del apetito = residual >= apetito
    """
    return level_rank(nivel_residual) >= level_rank(apetito)

def build_trend_text_dominant(trend_rows):
    inherente = []
    residual = []

    for row in trend_rows:
        inherente.append(
            f"{row['periodo']}: {row['inh_dominante']} ({row['inh_total']})"
        )
        residual.append(
            f"{row['periodo']}: {row['res_dominante']} ({row['res_total']})"
        )

    return {
        "inherente": " | ".join(inherente) if inherente else "Sin datos",
        "residual": " | ".join(residual) if residual else "Sin datos",
    }

# =========================================
# HELPER IA MÉTRICAS (OpenRouter / Ollama)
# =========================================
def ai_text_metricas(prompt: str,
                     system_prompt: str = "Responde en español, de forma ejecutiva, clara y profesional.",
                     temperature: float = 0.3,
                     max_tokens: int = 500,
                     openrouter_model: str = "openai/gpt-4.1-mini") -> str:
    """
    Helper único para métricas.
    Usa el proveedor configurado en Administración:
    - openrouter
    - ollama
    """
    provider = (get_ai_provider() or "openrouter").strip().lower()
    print("DEBUG IA METRICAS - provider activo:", provider)

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

        resp = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            },
            timeout=300
        )
        resp.raise_for_status()

        payload = resp.json() or {}
        print("DEBUG IA METRICAS - OLLAMA RESPONSE JSON:", str(payload)[:1500])

        texto = (payload.get("response") or "").strip()
        if not texto:
            texto = (payload.get("message") or "").strip()

        if not texto:
            raise RuntimeError(f"Ollama respondió sin contenido. Payload: {str(payload)[:500]}")

        return texto

    # =========================
    # OPENROUTER
    # =========================
    api_key = (get_openrouter_api_key() or "").strip()
    if not api_key:
        raise RuntimeError("No hay OPENROUTER_API_KEY configurada en Administración.")

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )

    resp = client.chat.completions.create(
        model=openrouter_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )

    texto = (
        resp.choices[0].message.content.strip()
        if resp and resp.choices and resp.choices[0].message.content
        else ""
    )

    if not texto:
        raise RuntimeError("OpenRouter respondió sin contenido.")

    return texto

@app.route("/metricas/riesgos/tendencia/ai", methods=["POST"])
@login_required
def metricas_riesgos_tendencia_ai():
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El rol Auditor no puede generar análisis IA.", "danger")
        return redirect(url_for("metricas_riesgos"))

    if user.role != "admin" and not verificar_permiso(user, "Métricas"):
        flash("No tiene permiso para ver métricas.", "danger")
        return redirect(url_for("menu"))

    cfg = MetricConfigRiesgos.query.first()
    if not cfg:
        flash("Primero configure parámetros de riesgos.", "warning")
        return redirect(url_for("menu"))

    tendencia = cfg.tendencia_tiempo or "mensual"
    riesgos = [r for r in Riesgo.query.all() if not bool(getattr(r, "archivado", False))]

    trend = defaultdict(lambda: {
        "inherente": {lvl: 0 for lvl in RISK_ORDER},
        "residual": {lvl: 0 for lvl in RISK_ORDER},
    })

    for r in riesgos:
        dt = parse_any_date(r.fecha_identificacion) or parse_any_date(r.fecha_revision)
        if not dt:
            continue

        pk = period_key(dt, tendencia)
        lvl_inh = normalize_level(r.riesgo_inherente)
        lvl_res = normalize_level(r.riesgo_residual)

        if lvl_inh in trend[pk]["inherente"]:
            trend[pk]["inherente"][lvl_inh] += 1

        if lvl_res in trend[pk]["residual"]:
            trend[pk]["residual"][lvl_res] += 1

    trend_rows = []
    for pk in sorted(trend.keys()):
        inh_dom = dominant_level(trend[pk]["inherente"])
        res_dom = dominant_level(trend[pk]["residual"])

        trend_rows.append({
            "periodo": pk,
            "inh_dominante": inh_dom or "Sin dato",
            "res_dominante": res_dom or "Sin dato",
            "inh_total": sum(trend[pk]["inherente"].values()),
            "res_total": sum(trend[pk]["residual"].values()),
        })

    base = build_trend_text_dominant(trend_rows)

    try:
        prompt = f"""
Eres un analista senior de riesgos. Redacta un análisis ejecutivo de tendencia, profesional y claro.

Período analizado: {tendencia}

Debes producir:
1. Un párrafo sobre la tendencia del riesgo INHERENTE, basado en el NIVEL DOMINANTE por período.
2. Un párrafo sobre la tendencia del riesgo RESIDUAL, basado en el NIVEL DOMINANTE por período.
3. Una conclusión final de una sola línea.

Datos base (nivel dominante y totales por período):
INHERENTE: {base["inherente"]}
RESIDUAL: {base["residual"]}

Reglas:
- No inventes datos.
- No inventes causas no evidenciadas.
- Usa lenguaje ejecutivo.
- Responde en máximo 3 párrafos.
"""
        text_ai = ai_text_metricas(
            prompt=prompt,
            system_prompt="Eres un experto en métricas de riesgos corporativos. Responde en español con enfoque ejecutivo.",
            temperature=0.3,
            max_tokens=500,
            openrouter_model="openai/gpt-4.1-mini"
        ).strip()

        text_ai = limpiar_texto_ia_global(text_ai)

        cfg.tendencia_ai_text = text_ai
        cfg.tendencia_ai_updated_at = datetime.utcnow()
        db.session.commit()

        flash("Análisis IA de tendencia generado.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"No se pudo generar IA: {e}", "danger")

    return redirect(url_for("metricas_riesgos"))

@app.route("/metricas/riesgos/tendencia/guardar", methods=["POST"])
@login_required
def metricas_riesgos_tendencia_guardar():
    user = User.query.get(session.get("user_id"))

    if user.role == "auditor":
        flash("El rol Auditor no puede editar análisis.", "danger")
        return redirect(url_for("metricas_riesgos"))

    if user.role != "admin" and not verificar_permiso(user, "Métricas"):
        flash("No tiene permiso para editar métricas.", "danger")
        return redirect(url_for("menu"))

    cfg = MetricConfigRiesgos.query.first()
    if not cfg:
        flash("Primero configure parámetros de riesgos.", "warning")
        return redirect(url_for("metricas_riesgos"))

    texto = limpiar_texto_ia_global(
        (request.form.get("tendencia_ai_text") or "").strip()
    )

    try:
        cfg.tendencia_ai_text = texto
        cfg.tendencia_ai_updated_at = datetime.utcnow()
        db.session.commit()
        flash("Análisis de tendencia actualizado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"No se pudo guardar el análisis: {e}", "danger")

    return redirect(url_for("metricas_riesgos"))

# =========================================================
# Metricas de Riesgos
# =========================================================

@app.route("/metricas/riesgos", methods=["GET"])
@login_required
def metricas_riesgos():
    user = User.query.get(session.get("user_id"))

    # Permisos
    if user.role == "auditor":
        read_only = True
    else:
        if user.role != "admin" and not verificar_permiso(user, "Métricas"):
            flash("No tiene permiso para ver métricas.", "danger")
            return redirect(url_for("menu"))
        read_only = False

    # Config de métricas de riesgos
    cfg = MetricConfigRiesgos.query.first()
    apetito = safe_appetite_level(
        (cfg.apetito_residual_definido if cfg else None),
        default="Moderado"
    )
    tendencia = (cfg.tendencia_tiempo if cfg else "mensual") or "mensual"

    riesgos_all = Riesgo.query.all()

    total_archivados = sum(1 for r in riesgos_all if bool(getattr(r, "archivado", False)))
    total_activos = len(riesgos_all) - total_archivados

    riesgos = [r for r in riesgos_all if not bool(getattr(r, "archivado", False))]

    profile = {
        "inherente": {lvl: 0 for lvl in RISK_ORDER},
        "residual": {lvl: 0 for lvl in RISK_ORDER},
    }

    outside_appetite_count = 0
    top_candidates = []

    by_tipo = defaultdict(int)

    for r in riesgos_all:
        tipo = (
            (r.tipo_riesgo or "").strip()
            or (getattr(r, "dimension_seguridad", "") or "").strip()
            or "Sin clasificar"
        )
        by_tipo[tipo] += 1

    trend = defaultdict(lambda: {
        "inherente": {lvl: 0 for lvl in RISK_ORDER},
        "residual": {lvl: 0 for lvl in RISK_ORDER},
    })

    for r in riesgos:
        lvl_inh = normalize_level(r.riesgo_inherente)
        lvl_res = normalize_level(r.riesgo_residual)

        if lvl_inh in profile["inherente"]:
            profile["inherente"][lvl_inh] += 1

        if lvl_res in profile["residual"]:
            profile["residual"][lvl_res] += 1

        if lvl_res and apetito and is_outside_appetite(lvl_res, apetito):
            outside_appetite_count += 1
            top_candidates.append(r)

        dt = parse_any_date(r.fecha_identificacion) or parse_any_date(r.fecha_revision)
        if dt:
            pk = period_key(dt, tendencia)

            if lvl_inh in trend[pk]["inherente"]:
                trend[pk]["inherente"][lvl_inh] += 1

            if lvl_res in trend[pk]["residual"]:
                trend[pk]["residual"][lvl_res] += 1

    def impact_value(rr: Riesgo) -> int:
        try:
            return int(rr.impacto_res or 0)
        except Exception:
            return int(rr.impacto or 0) if rr.impacto else 0

    top_candidates_sorted = sorted(
        top_candidates,
        key=lambda rr: (level_rank(rr.riesgo_residual), impact_value(rr)),
        reverse=True
    )[:5]

    trend_rows = []
    for pk in sorted(trend.keys()):
        inh_dom = dominant_level(trend[pk]["inherente"])
        res_dom = dominant_level(trend[pk]["residual"])

        trend_rows.append({
            "periodo": pk,
            "inh_dominante": inh_dom or "Sin dato",
            "res_dominante": res_dom or "Sin dato",
            "inh_total": sum(trend[pk]["inherente"].values()),
            "res_total": sum(trend[pk]["residual"].values()),
        })

    tipo_rows = sorted(
        [{"tipo": k, "total": v} for k, v in by_tipo.items()],
        key=lambda x: (x["total"], x["tipo"]),
        reverse=True
    )

    trend_text = build_trend_text_dominant(trend_rows)

    content = render_template_string("""
    <div class="riskmet-shell">

      <!-- CABECERA -->
      <div class="riskmet-header-card">
        <div class="riskmet-header-overlay">
          <div class="riskmet-header-text">
            <h3 class="riskmet-title m-0">Métricas de Riesgos</h3>
            <div class="riskmet-subtitle">
              Visualiza el perfil global de riesgos, el apetito residual definido,
              la tendencia en el tiempo y la distribución por tipo de riesgo.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="riskmet-header-actions">
        
      </div>

      <!-- RESUMEN -->
      <div class="text-black riskmet-summary mb-4">
        <span>Apetito residual: <b>{{ apetito }}</b></span>
        <span class="mx-2">·</span>
        <span>Tendencia: <b>{{ tendencia_label }}</b></span>
      </div>

      <!-- KPIS -->
      <div class="row g-3 mb-4">
        <div class="col-md-4">
          <div class="riskmet-card p-4 h-100">
            <div class="riskmet-kpi-label">Riesgos fuera del apetito</div>
            <div class="riskmet-kpi-value">{{ outside_appetite_count }}</div>
            <div class="text-muted small">Residual ≥ apetito ({{ apetito }})</div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="riskmet-card p-4 h-100">
            <div class="riskmet-kpi-label">Riesgos activos</div>
            <div class="riskmet-kpi-value">{{ total_activos }}</div>
            <div class="text-muted small">No archivados</div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="riskmet-card p-4 h-100">
            <div class="riskmet-kpi-label">Riesgos archivados</div>
            <div class="riskmet-kpi-value">{{ total_archivados }}</div>
            <div class="text-muted small">Histórico</div>
          </div>
        </div>
      </div>

      <!-- 1 PERFIL GLOBAL -->
      <div class="riskmet-card p-4 mb-4">
        <div class="riskmet-section-title">
          1) Perfil de riesgo global
        </div>

        <div class="table-responsive riskmet-table-wrap">
          <table class="table table-sm align-middle mb-0">
            <thead class="riskmet-table-head">
              <tr>
                <th>Criterio</th>
                <th>Total Inherente</th>
                <th>Total Residual</th>
              </tr>
            </thead>
            <tbody>
              {% for lvl in order %}
              <tr>
                <td><b>{{ lvl }}</b></td>
                <td>{{ profile.inherente[lvl] }}</td>
                <td>{{ profile.residual[lvl] }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <!-- 2 TOP 5 -->
      <div class="riskmet-card p-4 mb-4">
        <div class="riskmet-section-title">
          2) Top 5 riesgos críticos
        </div>

        <p class="text-muted mb-3">Muestra riesgos con residual ≥ apetito ({{ apetito }}).</p>

        <div class="table-responsive riskmet-table-wrap">
          <table class="table table-sm align-middle mb-0">
            <thead class="riskmet-table-head">
              <tr>
                <th>Riesgo</th>
                <th>Nivel Residual</th>
                <th>Impacto</th>
                <th>Tipo de Riesgo</th>
                <th>Dueño</th>
              </tr>
            </thead>
            <tbody>
              {% if top5|length == 0 %}
                <tr><td colspan="5" class="text-muted">No hay riesgos fuera del apetito para mostrar.</td></tr>
              {% endif %}
              {% for r in top5 %}
              <tr>
                <td>{{ r.riesgo }}</td>
                <td><b>{{ norm(r.riesgo_residual) }}</b></td>
                <td>{{ r.impacto_res_label or r.impacto_res or r.impacto or '' }}</td>
                <td>{{ r.tipo_riesgo or 'Sin clasificar' }}</td>
                <td>{{ r.propietario_riesgo or r.responsable or '' }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <!-- 3 TENDENCIA -->
      <div class="riskmet-card p-4 mb-4">
        <div class="riskmet-section-title">
          3) Tendencia en el tiempo
        </div>

        <p class="text-muted mb-3">
          Seleccione período: <b>{{ tendencia_label }}</b> (según configuración).
        </p>

        {% if not read_only %}
        <form method="POST" action="{{ url_for('metricas_riesgos_tendencia_ai') }}" class="mb-3">
          <button class="btn btn-outline-primary rounded-pill px-4" type="submit">
            🤖 Generar análisis IA (Tendencia)
          </button>
        </form>
        {% endif %}

        <div class="alert alert-light border-0 rounded-4">
          <div class="fw-semibold mb-2">Análisis de tendencia (texto base)</div>

          <div class="mb-2">
            <span class="badge bg-secondary">Inherente</span>
            <div class="mt-1">{{ trend_text["inherente"] }}</div>
          </div>

          <div>
            <span class="badge bg-secondary">Residual</span>
            <div class="mt-1">{{ trend_text["residual"] }}</div>
          </div>
        </div>

        <div class="table-responsive riskmet-table-wrap">
          <table class="table table-sm align-middle mb-0">
            <thead class="riskmet-table-head">
              <tr>
                <th>Período</th>
                <th>Nivel dominante (Inherente)</th>
                <th>Nivel dominante (Residual)</th>
                <th>Total Inh</th>
                <th>Total Res</th>
              </tr>
            </thead>
            <tbody>
              {% if trend_rows|length == 0 %}
                <tr><td colspan="5" class="text-muted">No hay datos con fecha para construir tendencia.</td></tr>
              {% endif %}
              {% for row in trend_rows %}
              <tr>
                <td><b>{{ row.periodo }}</b></td>
                <td>{{ row.inh_dominante }}</td>
                <td>{{ row.res_dominante }}</td>
                <td class="text-center">{{ row.inh_total }}</td>
                <td class="text-center">{{ row.res_total }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>

        <div class="mt-3">
          <div class="fw-semibold mb-2">Análisis IA (guardado)</div>

          <form method="POST" action="{{ url_for('metricas_riesgos_tendencia_guardar') }}" id="formTendenciaRiesgos">
            <div class="mb-3">
              <textarea
                name="tendencia_ai_text"
                id="tendenciaRiesgosBox"
                class="form-control riskmet-ia-textarea"
                rows="10"
                readonly>{% if cfg and cfg.tendencia_ai_text %}{{ cfg.tendencia_ai_text }}{% endif %}</textarea>
            </div>

            {% if cfg and cfg.tendencia_ai_text %}
              <div class="text-muted small mb-3">
                Última actualización:
                {{ cfg.tendencia_ai_updated_at.strftime('%Y-%m-%d %H:%M') if cfg.tendencia_ai_updated_at else '—' }}
              </div>
            {% else %}
              <div class="text-muted mb-3">
                Aún no se ha generado ningún análisis IA de tendencia.
              </div>
            {% endif %}

            {% if not read_only %}
            <div class="riskmet-edit-actions">
              <button type="button"
                      id="btnEditarTendenciaRiesgos"
                      class="btn btn-warning rounded-pill px-4 fw-bold text-dark">
                ✏️ Editar
              </button>

              <button type="button"
                      id="btnCancelarTendenciaRiesgos"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold d-none">
                Cancelar
              </button>

              <button type="submit"
                      id="btnGuardarTendenciaRiesgos"
                      class="btn btn-success rounded-pill px-4 fw-bold d-none">
                💾 Guardar análisis
              </button>
            </div>
            {% endif %}
          </form>
        </div>
      </div>

      <!-- 4 TIPO -->
      <div class="riskmet-card p-4 mb-4">
        <div class="riskmet-section-title">
          4) Total de riesgos por Tipo de Riesgo
        </div>

        <div class="table-responsive riskmet-table-wrap">
          <table class="table table-sm align-middle mb-0">
            <thead class="riskmet-table-head">
              <tr>
                <th>Tipo de Riesgo</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {% if tipo_rows|length == 0 %}
                <tr><td colspan="2" class="text-muted">No hay datos para tipo de riesgo.</td></tr>
              {% endif %}
              {% for tr in tipo_rows %}
              <tr>
                <td>{{ tr.tipo }}</td>
                <td><b>{{ tr.total }}</b></td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
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

      .riskmet-shell{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
      }

      .riskmet-header-card{
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

      .riskmet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .riskmet-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .riskmet-header-overlay::before{
        content:"📊";
        width:54px;
        height:54px;
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

      .riskmet-header-text{
        max-width:1000px;
      }

      .riskmet-header-text::before{
        content:"SGSI · Métricas de Riesgo";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .riskmet-title{
        color:#ffffff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
      }

      .riskmet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
      }

      .riskmet-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        padding:20px;
      }

      .riskmet-section-title{
        font-weight:950;
        color:#0b4a8f;
        margin-bottom:16px;
      }

      .riskmet-table-wrap{
        border-radius:14px;
        overflow:hidden;
        background:#fff;
      }

      .riskmet-table-wrap thead th{
        background:#1d5fa9;
        color:#fff;
        font-weight:900;
      }

      .riskmet-table-wrap tbody tr:hover{
        background:#eef6ff;
      }
    </style>

    <script>
      (function() {
        const box = document.getElementById("tendenciaRiesgosBox");
        const btnEditar = document.getElementById("btnEditarTendenciaRiesgos");
        const btnCancelar = document.getElementById("btnCancelarTendenciaRiesgos");
        const btnGuardar = document.getElementById("btnGuardarTendenciaRiesgos");

        if (!box || !btnEditar || !btnCancelar || !btnGuardar) return;

        const valorOriginal = box.value;

        btnEditar.addEventListener("click", function() {
          box.removeAttribute("readonly");
          box.focus();
          btnEditar.classList.add("d-none");
          btnCancelar.classList.remove("d-none");
          btnGuardar.classList.remove("d-none");
        });

        btnCancelar.addEventListener("click", function() {
          box.value = valorOriginal;
          box.setAttribute("readonly", "readonly");
          btnEditar.classList.remove("d-none");
          btnCancelar.classList.add("d-none");
          btnGuardar.classList.add("d-none");
        });
      })();
    </script>
    """,
    apetito=apetito,
    tendencia_label=tendencia.capitalize(),
    tendencia=tendencia,
    outside_appetite_count=outside_appetite_count,
    total_activos=total_activos,
    total_archivados=total_archivados,
    profile=profile,
    order=RISK_ORDER,
    top5=top_candidates_sorted,
    norm=normalize_level,
    trend_rows=trend_rows,
    trend_text=trend_text,
    cfg=cfg,
    tipo_rows=tipo_rows,
    read_only=read_only
    )

    return render_template_string(
        BASE,
        content=content,
        apetito=apetito,
        tendencia_label=tendencia.capitalize(),
        tendencia=tendencia,
        outside_appetite_count=outside_appetite_count,
        total_activos=total_activos,
        total_archivados=total_archivados,
        profile=profile,
        order=RISK_ORDER,
        top5=top_candidates_sorted,
        norm=normalize_level,
        trend_rows=trend_rows,
        trend_text=trend_text,
        cfg=cfg,
        tipo_rows=tipo_rows,
        read_only=read_only
    )

# =========================
# Analisis con AI
# =========================

def generar_analisis_incidente_ai(m, eta_objetivo, tiempos_por_clas):
    try:
        meta_clas = tiempos_por_clas.get(m.clasificacion or "", {}) if tiempos_por_clas else {}

        objetivo_mtcd = meta_clas.get("mtcd_horas")
        objetivo_mtir = meta_clas.get("mtir_horas")

        prompt = f"""
Eres un analista experto en gestión de incidentes de seguridad de la información.

Analiza el siguiente incidente y redacta un análisis ejecutivo breve, claro y profesional en español.

Datos del incidente:
- ID incidente: {m.id}
- Fecha registro: {m.fecha_registro}
- Descripción: {m.descripcion_incidente}
- Responsable: {m.cargo_responsable}
- Clasificación: {m.clasificacion}
- Requiere contención: {"Sí" if m.requiere_contencion else "No"}
- Tiempo MTCD ejecutado (horas): {m.tiempo_mtcd_horas}
- Cumplimiento MTCD (%): {m.cumplimiento_mtcd}
- Objetivo MTCD (horas): {objetivo_mtcd}
- Requiere recuperación: {"Sí" if m.requiere_recuperacion else "No"}
- Tiempo MTIR ejecutado (horas): {m.tiempo_mtir_horas}
- Cumplimiento MTIR (%): {m.cumplimiento_mtir}
- Objetivo MTIR (horas): {objetivo_mtir}
- Cumplimiento global (%): {m.cumplimiento_global}
- Meta objetivo global (%): {eta_objetivo}

Instrucciones:
1. Resume el desempeño del incidente.
2. Indica si cumplió o no con los tiempos esperados.
3. Explica brevemente los hallazgos más relevantes.
4. Da una recomendación puntual de mejora.
5. Responde en máximo 2 párrafos.
"""

        texto = ai_text_metricas(
            prompt=prompt,
            system_prompt="Eres un experto en métricas e incidentes de seguridad. Responde en español, de forma ejecutiva y profesional.",
            temperature=0.3,
            max_tokens=350,
            openrouter_model="openai/gpt-4.1-mini"
        ).strip()

        texto = limpiar_texto_ia_global(texto)

        return texto or "No fue posible generar un análisis automático para este incidente."

    except Exception as e:
        return f"No fue posible generar el análisis automático del incidente. Detalle técnico: {str(e)}"

# =========================
# Matriz Métricas de Incidentes (simplificada)
# =========================

@app.route('/metricas/incidentes/matriz')
@login_required
def metricas_incidente_matriz():
    from datetime import datetime, date
    import sqlite3

    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Métricas"):
        flash("No tiene permiso para ingresar al módulo de métricas de incidentes.", "danger")
        return redirect(url_for('menu'))

    # ==========================
    # Filtros
    # ==========================
    clasificacion_filtro = (request.args.get('clasificacion') or '').strip()
    year_raw = (request.args.get('year') or '').strip()
    year = int(year_raw) if year_raw.isdigit() else None

    # ==========================
    # Configuración de tiempos por clasificación
    # ==========================
    clasif_nombres, tiempos_por_clas = get_config_incidentes_map()

    config = MetricConfigIncidentes.query.first()
    eta_objetivo = config.eta_objetivo if config else None

    # ==========================
    # Leer incidentes desde SQLite
    # ==========================
    init_incidentes_db()
    conn = get_incidentes_db_connection()
    c = conn.cursor()

    sql = """
        SELECT
            id,
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
        FROM registro_incidentes
        WHERE fecha_alerta IS NOT NULL
    """
    params = []

    if year is not None:
        inicio = f"{year:04d}-01-01 00:00"
        fin    = f"{year + 1:04d}-01-01 00:00"
        sql += " AND fecha_alerta >= ? AND fecha_alerta < ? "
        params.extend([inicio, fin])

    if clasificacion_filtro:
        sql += " AND UPPER(COALESCE(clasificacion_incidente,'')) = UPPER(?) "
        params.append(clasificacion_filtro)

    sql += " ORDER BY fecha_alerta DESC "

    c.execute(sql, params)
    rows = c.fetchall()

    # ==========================
    # Años disponibles
    # ==========================
    c.execute("""
        SELECT MIN(fecha_alerta), MAX(fecha_alerta)
        FROM registro_incidentes
        WHERE fecha_alerta IS NOT NULL
    """)
    min_max = c.fetchone()

    # ==========================
    # Clasificaciones disponibles para filtro
    # ==========================
    c.execute("""
        SELECT DISTINCT TRIM(clasificacion_incidente) AS clasificacion
        FROM registro_incidentes
        WHERE clasificacion_incidente IS NOT NULL
          AND TRIM(clasificacion_incidente) <> ''
        ORDER BY clasificacion
    """)
    clasificaciones_db = [r["clasificacion"] for r in c.fetchall() if r["clasificacion"]]

    conn.close()

    year_options = [year]
    if min_max and min_max[0] and min_max[1]:
        try:
            min_y = int(str(min_max[0])[:4])
            max_y = int(str(min_max[1])[:4])
            if min_y <= max_y:
                year_options = list(range(min_y, max_y + 1))
        except Exception:
            year_options = [year]

    clasificaciones_filtro = []
    for x in (clasif_nombres or []):
        if x and x not in clasificaciones_filtro:
            clasificaciones_filtro.append(x)
    for x in clasificaciones_db:
        if x and x not in clasificaciones_filtro:
            clasificaciones_filtro.append(x)

    # ==========================
    # Construcción de métricas
    # ==========================
    items = []

    for row in rows:
        m = construir_metrica_desde_incidente_row(row, tiempos_por_clas)

        fecha_reg = m.fecha_registro or datetime.utcnow()
        desc_inc = (m.descripcion_incidente or "").strip() or "Sin descripción"

        met_db = MetricaIncidente.query.filter_by(incidente_id=m.id).first()

        if not met_db:
            met_db = MetricaIncidente(
                incidente_id=m.id,
                analisis=None
            )
            db.session.add(met_db)

        # Refrescar SIEMPRE desde registro_incidentes
        met_db.fecha_registro = fecha_reg
        met_db.descripcion_incidente = desc_inc
        met_db.cargo_responsable = m.cargo_responsable
        met_db.clasificacion = m.clasificacion

        met_db.requiere_contencion = m.requiere_contencion
        met_db.tiempo_mtcd_horas = m.tiempo_mtcd_horas
        met_db.cumplimiento_mtcd = m.cumplimiento_mtcd

        met_db.requiere_recuperacion = m.requiere_recuperacion
        met_db.tiempo_mtir_horas = m.tiempo_mtir_horas
        met_db.cumplimiento_mtir = m.cumplimiento_mtir

        met_db.cumplimiento_global = m.cumplimiento_global

        db.session.commit()

        # ✅ YA NO generar IA automáticamente aquí
        m.metrica_id = met_db.id
        m.analisis = met_db.analisis
        m.cumplimiento_global = met_db.cumplimiento_global

        items.append(m)

    html = render_template_string("""
    <div class="minc-shell">

      <!-- CABECERA -->
      <div class="minc-header-card">
        <div class="minc-header-overlay">
          <div class="minc-header-text">
            <h3 class="minc-title m-0">Matriz de Métricas de Incidentes</h3>
            <div class="minc-subtitle">
              Consulta las métricas principales por incidente y accede al detalle completo del registro.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTONES -->
      <div class="minc-header-actions">
        
      </div>

      <!-- FILTROS -->
      <div class="minc-card p-4 mb-3">
        <div class="minc-section-title">
          Filtros de búsqueda
        </div>

        <form method="get" class="row g-3 align-items-end">
          <div class="col-md-3">
              <label class="form-label">Año</label>
              <select name="year" class="form-select">
                <option value="" {% if not request.args.get('year') %}selected{% endif %}>Todos</option>
                {% for y in year_options %}
                  <option value="{{ y }}" {% if y == year %}selected{% endif %}>{{ y }}</option>
                {% endfor %}
              </select>
            </div>

          <div class="col-md-4">
            <label class="form-label">Clasificación del incidente</label>
            <select name="clasificacion" class="form-select">
              <option value="">Todas</option>
              {% for c in clasificaciones_filtro %}
                <option value="{{ c }}" {% if clasificacion_filtro == c %}selected{% endif %}>{{ c }}</option>
              {% endfor %}
            </select>
          </div>

          <div class="col-md-5 d-flex gap-2 flex-wrap">
            <button type="submit" class="btn btn-primary rounded-pill px-4">
              Aplicar filtros
            </button>

            <a href="{{ url_for('metricas_incidente_matriz') }}"
               class="btn btn-outline-secondary rounded-pill px-4">
              Limpiar
            </a>
          </div>
        </form>
      </div>

      <!-- MATRIZ -->
      <div class="minc-card p-3">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
          <div class="minc-section-title mb-0">
            Resultados de métricas por incidente
          </div>

          <div class="minc-total-badge">
            Total de registros: {{ items|length }}
          </div>
        </div>

        <div class="minc-table-wrap">
          <div class="table-responsive">
            <table class="table table-sm table-bordered align-middle minc-table mb-0">
              <thead class="text-center">
                <tr>
                  <th style="min-width:150px;">Fecha y hora</th>
                  <th style="min-width:180px;">Clasificación del incidente</th>
                  <th style="min-width:340px;">Descripción del incidente</th>
                  <th style="min-width:140px;">Cumplimiento</th>
                  <th style="min-width:330px;">Análisis</th>
                  <th style="min-width:250px;">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {% for m in items %}
                  <tr>
                    <td class="text-center">
                      {{ m.fecha_registro.strftime("%Y-%m-%d %H:%M") if m.fecha_registro else '—' }}
                    </td>

                    <td class="text-center">
                      {{ m.clasificacion or '—' }}
                    </td>

                    <td class="text-start">
                      {{ m.descripcion_incidente or 'Sin descripción' }}
                    </td>

                    <td class="text-center">
                      {% set val = m.cumplimiento_global %}
                      {% if val is not none %}
                        {% if eta_objetivo is not none %}
                          {% if val >= eta_objetivo %}
                            <span class="badge bg-success minc-badge">
                              {{ "%.2f"|format(val) }} %
                            </span>
                          {% else %}
                            <span class="badge bg-danger minc-badge">
                              {{ "%.2f"|format(val) }} %
                            </span>
                          {% endif %}
                        {% else %}
                          <span class="badge bg-primary minc-badge">
                            {{ "%.2f"|format(val) }} %
                          </span>
                        {% endif %}
                      {% else %}
                        <span class="text-muted">—</span>
                      {% endif %}
                    </td>

                    <td class="text-start">
                      <div class="minc-analisis-preview">
                        {{ m.analisis or 'No hay análisis generado.' }}
                      </div>
                    </td>

                    <td class="text-center">
                      <div class="d-flex flex-column gap-1 align-items-center">
                        <a href="{{ url_for('metricas_incidente_detalle', incidente_id=m.id) }}"
                           class="btn btn-sm btn-outline-primary rounded-pill">
                          🔍 Detalle
                        </a>

                        {% if user.role != 'auditor' %}
                        <a href="{{ url_for('metricas_incidente_analisis', incidente_id=m.id, regen=1) }}"
                           class="btn btn-sm btn-outline-warning rounded-pill"
                           onclick="showLoader()">
                          🤖 Generar AI
                        </a>

                        <a href="{{ url_for('metricas_incidente_analisis', incidente_id=m.id) }}"
                           class="btn btn-sm btn-outline-secondary rounded-pill">
                          ✏️ Editar
                        </a>
                        {% endif %}
                      </div>
                    </td>
                  </tr>
                {% endfor %}

                {% if items|length == 0 %}
                  <tr>
                    <td colspan="6" class="text-center text-muted py-4">
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

      .minc-shell{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
      }

      /* 🔥 HEADER SGSI MODERNO */
      .minc-header-card{
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

      .minc-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .minc-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .minc-header-overlay::before{
        content:"⚠️";
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

      .minc-header-text{
        max-width:1000px;
      }

      .minc-header-text::before{
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

      .minc-title{
        color:#ffffff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
      }

      .minc-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
      }

      /* BOTONES */
      .minc-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .minc-btn-main{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .minc-btn-main:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      /* CARD */
      .minc-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        padding:20px;
      }

      .minc-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
      }

      .minc-total-badge{
        background:#eef5ff;
        color:#0b4a8f;
        font-weight:900;
        border-radius:999px;
        padding:6px 12px;
        font-size:.78rem;
      }

      /* TABLA */
      .minc-table-wrap{
        max-height:72vh;
        overflow:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#fff;
      }

      .minc-table{
        width:100%;
        min-width:1200px;
      }

      .minc-table thead th{
        position:sticky;
        top:0;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1);
        color:#fff;
        font-weight:900;
        font-size:.78rem;
        text-align:center;
      }

      .minc-table td{
        font-size:.82rem;
        padding:10px;
      }

      .minc-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .minc-table tbody tr:hover{
        background:#eef6ff;
      }

      .minc-analisis-preview{
        max-height:96px;
        overflow:auto;
        white-space:pre-wrap;
        font-size:.82rem;
      }

      .minc-badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      /* FORMULARIOS */
      .form-control,
      .form-select{
        border-radius:10px;
        border:1px solid #d9e3f0;
        background:#f8fafc;
      }

      .form-control:focus,
      .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
      }

      /* RESPONSIVE */
      @media (max-width:992px){
        .minc-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .minc-title{
          font-size:1.20rem;
        }

        .minc-subtitle{
          font-size:.68rem;
        }
      }

      @media (max-width:768px){
        .minc-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .minc-header-overlay::before{
          margin:0;
        }

        .minc-title,
        .minc-subtitle{
          text-align:center;
        }

        .minc-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """,
    year=year,
    year_options=year_options,
    clasificacion_filtro=clasificacion_filtro,
    clasificaciones_filtro=clasificaciones_filtro,
    items=items,
    eta_objetivo=eta_objetivo,
    user=user)

    return render_template_string(BASE, content=Markup(html))


# ==================================
# Detalle de incidente para métricas
# ==================================

@app.route('/metricas/incidentes/<int:incidente_id>/detalle')
@login_required
def metricas_incidente_detalle(incidente_id):
    import sqlite3

    row = cargar_incidente_por_id(incidente_id)
    if not row:
        flash("No se encontró el incidente solicitado.", "warning")
        return redirect(url_for('metricas_incidente_matriz'))

    clasif_nombres, tiempos_por_clas = get_config_incidentes_map()
    m = construir_metrica_desde_incidente_row(row, tiempos_por_clas)

    met = MetricaIncidente.query.filter_by(incidente_id=incidente_id).first()
    if not met:
        met = MetricaIncidente(incidente_id=incidente_id, analisis=None)
        db.session.add(met)

    met.fecha_registro = m.fecha_registro or datetime.utcnow()
    met.descripcion_incidente = (m.descripcion_incidente or "").strip() or "Sin descripción"
    met.cargo_responsable = m.cargo_responsable
    met.clasificacion = m.clasificacion

    met.requiere_contencion = m.requiere_contencion
    met.tiempo_mtcd_horas = m.tiempo_mtcd_horas
    met.cumplimiento_mtcd = m.cumplimiento_mtcd

    met.requiere_recuperacion = m.requiere_recuperacion
    met.tiempo_mtir_horas = m.tiempo_mtir_horas
    met.cumplimiento_mtir = m.cumplimiento_mtir

    met.cumplimiento_global = m.cumplimiento_global

    db.session.commit()

    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Métricas"):
        flash("No tiene permiso para ver el detalle del incidente.", "danger")
        return redirect(url_for('menu'))

    init_incidentes_db()
    conn = get_incidentes_db_connection()
    c = conn.cursor()

    c.execute("""
        SELECT
            id,
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
        FROM registro_incidentes
        WHERE id = ?
        LIMIT 1
    """, (incidente_id,))

    row = c.fetchone()
    conn.close()

    if not row:
        flash("No se encontró el incidente solicitado.", "warning")
        return redirect(url_for('metricas_incidente_matriz'))

    met = MetricaIncidente.query.filter_by(incidente_id=incidente_id).first()

    html = render_template_string("""
    <div class="mind-shell">

      <!-- CABECERA -->
      <div class="mind-header-card">
        <div class="mind-header-overlay">
          <div class="mind-header-text">
            <h3 class="mind-title m-0">Detalle del Incidente</h3>
            <div class="mind-subtitle">
              Consulta completa del registro del incidente y su análisis de métricas.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTONES -->
      <div class="mind-header-actions">
        <a href="{{ url_for('metricas_incidente_matriz') }}"
           class="btn mind-btn-main rounded-pill px-4 fw-bold">
          ⬅️ Volver a la Matriz
        </a>
      </div>

      <!-- INFORMACIÓN GENERAL -->
      <div class="mind-card p-4 mb-3">
        <div class="mind-section-title">Información general del incidente</div>

        <div class="row g-3">
          <div class="col-md-4">
            <label class="mind-label">ID interno</label>
            <div class="mind-value">{{ row["id"] or '—' }}</div>
          </div>

          <div class="col-md-4">
            <label class="mind-label">ID incidente</label>
            <div class="mind-value">{{ row["id_incidente"] or '—' }}</div>
          </div>

          <div class="col-md-4">
            <label class="mind-label">Fecha y hora de alerta</label>
            <div class="mind-value">{{ row["fecha_alerta"] or '—' }}</div>
          </div>

          <div class="col-md-6">
            <label class="mind-label">Nombre de la alerta</label>
            <div class="mind-value">{{ row["nombre_alerta"] or '—' }}</div>
          </div>

          <div class="col-md-6">
            <label class="mind-label">Clasificación del incidente</label>
            <div class="mind-value">{{ row["clasificacion_incidente"] or '—' }}</div>
          </div>

          <div class="col-md-6">
            <label class="mind-label">Cargo responsable</label>
            <div class="mind-value">{{ row["cargo_responsable"] or '—' }}</div>
          </div>

          <div class="col-md-3">
            <label class="mind-label">Estado</label>
            <div class="mind-value">{{ row["estado"] or '—' }}</div>
          </div>

          <div class="col-md-3">
            <label class="mind-label">Prioridad</label>
            <div class="mind-value">{{ row["prioridad"] or '—' }}</div>
          </div>

          <div class="col-md-12">
            <label class="mind-label">Descripción del incidente</label>
            <div class="mind-box">{{ row["descripcion_alerta"] or '—' }}</div>
          </div>
        </div>
      </div>

      <!-- CONTEXTO DEL EVENTO -->
      <div class="mind-card p-4 mb-3">
        <div class="mind-section-title">Contexto del evento</div>

        <div class="row g-3">
          <div class="col-md-4">
            <label class="mind-label">Atacante</label>
            <div class="mind-value">{{ row["atacante"] or '—' }}</div>
          </div>

          <div class="col-md-4">
            <label class="mind-label">Ubicación del atacante</label>
            <div class="mind-value">{{ row["ubicacion_atacante"] or '—' }}</div>
          </div>

          <div class="col-md-4">
            <label class="mind-label">Principio afectado</label>
            <div class="mind-value">{{ row["principio"] or '—' }}</div>
          </div>

          <div class="col-md-6">
            <label class="mind-label">Tipo de recurso afectado</label>
            <div class="mind-value">{{ row["tipo_recurso_afectado"] or '—' }}</div>
          </div>

          <div class="col-md-6">
            <label class="mind-label">Nombre del recurso / ID</label>
            <div class="mind-value">{{ row["nombre_recurso_id"] or '—' }}</div>
          </div>
        </div>
      </div>

      <!-- CONTENCIÓN -->
      <div class="mind-card p-4 mb-3">
        <div class="mind-section-title">Contención</div>

        <div class="row g-3">
          <div class="col-md-4">
            <label class="mind-label">¿Requiere contención?</label>
            <div class="mind-value">
              {% if row["se_requiere_contencion"] in [1, '1', 'SI', 'Sí', 'si', 'sí', True] %}
                Sí
              {% elif row["se_requiere_contencion"] in [0, '0', 'NO', 'No', 'no', False] %}
                No
              {% else %}
                {{ row["se_requiere_contencion"] if row["se_requiere_contencion"] is not none else '—' }}
              {% endif %}
            </div>
          </div>

          <div class="col-md-4">
            <label class="mind-label">Fecha y hora de contención</label>
            <div class="mind-value">{{ row["fecha_hora_contencion"] or '—' }}</div>
          </div>

          <div class="col-md-4">
            <label class="mind-label">Cumplimiento MTCD</label>
            <div class="mind-value">
              {% if met and met.cumplimiento_mtcd is not none %}
                {{ "%.2f"|format(met.cumplimiento_mtcd) }} %
              {% else %}
                —
              {% endif %}
            </div>
          </div>

          <div class="col-md-12">
            <label class="mind-label">Descripción de contención</label>
            <div class="mind-box">{{ row["descripcion_contencion"] or '—' }}</div>
          </div>
        </div>
      </div>

      <!-- RECUPERACIÓN -->
      <div class="mind-card p-4 mb-3">
        <div class="mind-section-title">Recuperación</div>

        <div class="row g-3">
          <div class="col-md-4">
            <label class="mind-label">¿Requiere recuperación?</label>
            <div class="mind-value">
              {% if row["se_requiere_recuperacion"] in [1, '1', 'SI', 'Sí', 'si', 'sí', True] %}
                Sí
              {% elif row["se_requiere_recuperacion"] in [0, '0', 'NO', 'No', 'no', False] %}
                No
              {% else %}
                {{ row["se_requiere_recuperacion"] if row["se_requiere_recuperacion"] is not none else '—' }}
              {% endif %}
            </div>
          </div>

          <div class="col-md-4">
            <label class="mind-label">Fecha y hora de recuperación</label>
            <div class="mind-value">{{ row["fecha_hora_recuperacion"] or '—' }}</div>
          </div>

          <div class="col-md-4">
            <label class="mind-label">Cumplimiento MTIR</label>
            <div class="mind-value">
              {% if met and met.cumplimiento_mtir is not none %}
                {{ "%.2f"|format(met.cumplimiento_mtir) }} %
              {% else %}
                —
              {% endif %}
            </div>
          </div>

          <div class="col-md-12">
            <label class="mind-label">Descripción de recuperación</label>
            <div class="mind-box">{{ row["descripcion_recuperacion"] or '—' }}</div>
          </div>
        </div>
      </div>

      <!-- CIERRE Y MÉTRICAS -->
      <div class="mind-card p-4">
        <div class="mind-section-title">Cierre y análisis</div>

        <div class="row g-3">
          <div class="col-md-4">
            <label class="mind-label">Fecha de cierre</label>
            <div class="mind-value">{{ row["fecha_cierre"] or '—' }}</div>
          </div>

          <div class="col-md-4">
            <label class="mind-label">Cumplimiento global</label>
            <div class="mind-value">
              {% if met and met.cumplimiento_global is not none %}
                {{ "%.2f"|format(met.cumplimiento_global) }} %
              {% else %}
                —
              {% endif %}
            </div>
          </div>

          <div class="col-md-4">
            <label class="mind-label">Responsable métrica</label>
            <div class="mind-value">{{ met.cargo_responsable if met and met.cargo_responsable else (row["cargo_responsable"] or '—') }}</div>
          </div>

          <div class="col-md-12">
            <label class="mind-label">Descripción de cierre</label>
            <div class="mind-box">{{ row["descripcion_cierre"] or '—' }}</div>
          </div>

          <div class="col-md-12">
            <label class="mind-label">Análisis</label>
            <div class="mind-box">{{ met.analisis if met and met.analisis else 'No hay análisis generado.' }}</div>
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

      .mind-shell{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
      }

      .mind-header-card{
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

      .mind-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .mind-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .mind-header-overlay::before{
        content:"🔍";
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

      .mind-header-text{
        max-width:1000px;
      }

      .mind-header-text::before{
        content:"SGSI · Detalle de Incidente";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .mind-title{
        color:#ffffff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
      }

      .mind-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
      }

      .mind-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .mind-btn-main{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .mind-btn-main:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      .mind-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .mind-card .card-body{
        padding:22px;
      }

      .mind-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
      }

      .mind-label{
        font-weight:900;
        font-size:.82rem;
        color:#334155;
        margin-bottom:6px;
        display:block;
      }

      .mind-value,
      .mind-box{
        background:#f8fafc;
        border:1px solid #dbe6f4;
        border-radius:12px;
        padding:10px 12px;
        color:#0b1220;
        font-size:.90rem;
        line-height:1.4;
      }

      .mind-value{
        min-height:44px;
      }

      .mind-box{
        min-height:90px;
        white-space:pre-wrap;
      }

      .form-control,
      .form-select{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
      }

      .form-control:focus,
      .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .mind-soft-box{
        background:rgba(59,130,246,.08);
        border:1px solid rgba(59,130,246,.12);
        border-radius:14px;
        padding:14px 16px;
      }

      @media (max-width:992px){
        .mind-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .mind-title{
          font-size:1.20rem;
        }

        .mind-subtitle{
          font-size:.68rem;
        }

        .mind-card .card-body{
          padding:16px;
        }

        .mind-value,
        .mind-box{
          font-size:.78rem;
        }
      }

      @media (max-width:768px){
        .mind-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .mind-header-overlay::before{
          margin:0;
        }

        .mind-title,
        .mind-subtitle{
          text-align:center;
        }

        .mind-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, row=row, met=met)

    return render_template_string(BASE, content=Markup(html))

# ==================================
# Análisis editable de métrica incidente
# ==================================

@app.route('/metricas/incidentes/<int:incidente_id>/analisis', methods=['GET', 'POST'])
@login_required
def metricas_incidente_analisis(incidente_id):
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Métricas"):
        flash("No tiene permiso para acceder al análisis del incidente.", "danger")
        return redirect(url_for('menu'))

    row = cargar_incidente_por_id(incidente_id)
    if not row:
        flash("No se encontró el incidente solicitado.", "warning")
        return redirect(url_for('metricas_incidente_matriz'))

    clasif_nombres, tiempos_por_clas = get_config_incidentes_map()
    m = construir_metrica_desde_incidente_row(row, tiempos_por_clas)

    config = MetricConfigIncidentes.query.first()
    eta_objetivo = config.eta_objetivo if config else None

    met = MetricaIncidente.query.filter_by(incidente_id=incidente_id).first()
    if not met:
        met = MetricaIncidente(
            incidente_id=incidente_id,
            analisis=None
        )
        db.session.add(met)

    met.fecha_registro = m.fecha_registro or datetime.utcnow()
    met.descripcion_incidente = (m.descripcion_incidente or "").strip() or "Sin descripción"
    met.cargo_responsable = m.cargo_responsable
    met.clasificacion = m.clasificacion
    met.requiere_contencion = m.requiere_contencion
    met.tiempo_mtcd_horas = m.tiempo_mtcd_horas
    met.cumplimiento_mtcd = m.cumplimiento_mtcd
    met.requiere_recuperacion = m.requiere_recuperacion
    met.tiempo_mtir_horas = m.tiempo_mtir_horas
    met.cumplimiento_mtir = m.cumplimiento_mtir
    met.cumplimiento_global = m.cumplimiento_global
    db.session.commit()

    if request.method == 'POST':
        if user.role == 'auditor':
            flash("El rol Auditor no puede editar análisis.", "danger")
            return redirect(url_for('metricas_incidente_analisis', incidente_id=incidente_id))

        nuevo = (request.form.get('analisis') or "").strip()
        try:
            met.analisis = nuevo
            db.session.commit()
            flash("Análisis actualizado correctamente.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"No se pudo guardar el análisis: {e}", "danger")

        return redirect(url_for('metricas_incidente_analisis', incidente_id=incidente_id))

    regen = request.args.get('regen', type=int, default=0)

    if regen == 1:
        if user.role == 'auditor':
            flash("El rol Auditor no puede generar análisis con AI.", "danger")
            return redirect(url_for('metricas_incidente_analisis', incidente_id=incidente_id))

        try:
            met.analisis = generar_analisis_incidente_ai(m, eta_objetivo, tiempos_por_clas)
            db.session.commit()
            flash("Análisis generado correctamente con AI.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"No se pudo generar el análisis con AI: {e}", "danger")

        return redirect(url_for('metricas_incidente_analisis', incidente_id=incidente_id))

    html = render_template_string("""
    <div class="miia-shell">

      <div class="miia-header-card">
        <div class="miia-header-overlay">
          <div class="miia-header-text">
            <h3 class="miia-title m-0">Análisis de Métrica del Incidente</h3>
            <div class="miia-subtitle">
              Edición y generación manual del análisis para el incidente seleccionado.
            </div>
          </div>
        </div>
      </div>

      <div class="miia-header-actions">
        <a href="{{ url_for('metricas_incidente_matriz') }}"
           class="btn miia-btn-main rounded-pill px-4 fw-bold">
          ⬅️ Volver a la Matriz
        </a>

        {% if user.role != 'auditor' %}
        <a href="{{ url_for('metricas_incidente_analisis', incidente_id=incidente_id, regen=1) }}"
           class="btn btn-outline-warning rounded-pill px-4 fw-bold"
           onclick="showLoader()">
          🤖 Generar análisis con AI
        </a>
        {% endif %}
      </div>

      <div class="miia-card p-4">
        <div class="miia-section-title">Información base del incidente</div>

        <div class="row g-3 mb-4">
          <div class="col-md-3">
            <label class="miia-label">Fecha y hora</label>
            <div class="miia-value">{{ met.fecha_registro.strftime("%Y-%m-%d %H:%M") if met.fecha_registro else '—' }}</div>
          </div>

          <div class="col-md-3">
            <label class="miia-label">Clasificación</label>
            <div class="miia-value">{{ met.clasificacion or '—' }}</div>
          </div>

          <div class="col-md-3">
            <label class="miia-label">Responsable</label>
            <div class="miia-value">{{ met.cargo_responsable or '—' }}</div>
          </div>

          <div class="col-md-3">
            <label class="miia-label">Cumplimiento global</label>
            <div class="miia-value">
              {% if met.cumplimiento_global is not none %}
                {{ "%.2f"|format(met.cumplimiento_global) }} %
              {% else %}
                —
              {% endif %}
            </div>
          </div>

          <div class="col-md-12">
            <label class="miia-label">Descripción del incidente</label>
            <div class="miia-box">{{ met.descripcion_incidente or 'Sin descripción' }}</div>
          </div>
        </div>

        <div class="miia-section-title">Análisis</div>

        <form method="POST" id="formAnalisisIncidente">
          <div class="mb-3">
            <textarea
              name="analisis"
              id="analisisIncidenteBox"
              class="form-control miia-textarea"
              rows="14"
              readonly>{{ met.analisis or '' }}</textarea>
          </div>

          {% if user.role != 'auditor' %}
          <div class="miia-edit-actions">
            <button type="button"
                    id="btnEditarAnalisisInc"
                    class="btn btn-warning rounded-pill px-4 fw-bold text-dark">
              ✏️ Editar
            </button>

            <button type="button"
                    id="btnCancelarAnalisisInc"
                    class="btn btn-outline-secondary rounded-pill px-4 fw-bold d-none">
              Cancelar
            </button>

            <button type="submit"
                    id="btnGuardarAnalisisInc"
                    class="btn btn-success rounded-pill px-4 fw-bold d-none">
              💾 Guardar análisis
            </button>
          </div>
          {% endif %}
        </form>
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

      .miia-shell{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
      }

      .miia-header-card{
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

      .miia-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .miia-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .miia-header-overlay::before{
        content:"🤖";
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

      .miia-header-text{
        max-width:1000px;
      }

      .miia-header-text::before{
        content:"SGSI · Análisis IA de Incidente";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .miia-title{
        color:#ffffff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
      }

      .miia-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
      }

      .miia-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .miia-btn-main{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .miia-btn-main:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      .miia-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .miia-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
      }

      .miia-label{
        font-weight:900;
        font-size:.82rem;
        color:#334155;
        margin-bottom:6px;
        display:block;
      }

      .miia-value,
      .miia-box{
        background:#f8fafc;
        border:1px solid #dbe6f4;
        border-radius:12px;
        padding:10px 12px;
        color:#0b1220;
        font-size:.90rem;
        line-height:1.4;
      }

      .miia-value{
        min-height:44px;
      }

      .miia-box{
        min-height:90px;
        white-space:pre-wrap;
      }

      .miia-textarea{
        min-height:320px;
        line-height:1.45;
        resize:vertical;
        padding:14px 16px;
        background:#f8fafc;
        border-radius:12px;
        border:1px solid #dbe6f4;
      }

      .miia-textarea[readonly]{
        background:#f8fafc;
        color:#374151;
        cursor:default;
      }

      .miia-edit-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
      }

      .form-control{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
      }

      .form-control:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      @media (max-width:992px){
        .miia-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .miia-title{
          font-size:1.20rem;
        }

        .miia-subtitle{
          font-size:.68rem;
        }
      }

      @media (max-width:768px){
        .miia-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .miia-header-overlay::before{
          margin:0;
        }

        .miia-title,
        .miia-subtitle{
          text-align:center;
        }

        .miia-header-actions .btn{
          width:100%;
        }
      }
    </style>

    {% if user.role != 'auditor' %}
    <script>
      (function() {
        const box = document.getElementById("analisisIncidenteBox");
        const btnEditar = document.getElementById("btnEditarAnalisisInc");
        const btnCancelar = document.getElementById("btnCancelarAnalisisInc");
        const btnGuardar = document.getElementById("btnGuardarAnalisisInc");

        if (!box || !btnEditar || !btnCancelar || !btnGuardar) return;

        const valorOriginal = box.value;

        btnEditar.addEventListener("click", function() {
          box.removeAttribute("readonly");
          box.focus();
          btnEditar.classList.add("d-none");
          btnCancelar.classList.remove("d-none");
          btnGuardar.classList.remove("d-none");
        });

        btnCancelar.addEventListener("click", function() {
          box.value = valorOriginal;
          box.setAttribute("readonly", "readonly");
          btnEditar.classList.remove("d-none");
          btnCancelar.classList.add("d-none");
          btnGuardar.classList.add("d-none");
        });
      })();
    </script>
    {% endif %}
    """,
    met=met,
    incidente_id=incidente_id,
    user=user)

    return render_template_string(BASE, content=Markup(html))

# =========================
# Analisis
# =========================

@app.route('/metricas/incidentes/<int:id>/analisis', methods=['GET'])
@login_required
def metricas_incidente_ver_analisis(id):
    # Primero intenta buscar por ID de la métrica
    met = MetricaIncidente.query.get(id)

    # Si no existe, intenta buscar por incidente_id
    if not met:
        met = MetricaIncidente.query.filter_by(incidente_id=id).first()

    if not met:
        flash("No se encontró el análisis del incidente solicitado.", "warning")
        return redirect(url_for('metricas_incidente_matriz'))

    html = render_template_string("""
    <div class="container mt-4" style="max-width: 1000px;">

      <div class="card shadow-sm border-0 rounded-4">
        <div class="card-body p-4">

          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
            <h3 class="m-0 text-primary">📘 Análisis Completo del Incidente</h3>

            <a href="{{ url_for('metricas_incidente_matriz') }}"
               class="btn btn-secondary rounded-pill px-4">
              ⬅ Volver a la Matriz
            </a>
          </div>

          <hr>

          <div class="mb-3">
            <strong>ID métrica:</strong> {{ met.id }}
          </div>

          <div class="mb-3">
            <strong>ID incidente:</strong> {{ met.incidente_id }}
          </div>

          <div class="mb-3">
            <strong>Fecha de registro:</strong>
            {{ met.fecha_registro.strftime("%Y-%m-%d %H:%M") if met.fecha_registro else '—' }}
          </div>

          <div class="mb-3">
            <strong>Clasificación:</strong> {{ met.clasificacion or '—' }}
          </div>

          <div class="mb-3">
            <strong>Responsable:</strong> {{ met.cargo_responsable or '—' }}
          </div>

          <div class="mb-3">
            <strong>Descripción del incidente:</strong>
            <div class="mt-2 p-3 rounded-3 bg-light border" style="white-space: pre-wrap;">
              {{ met.descripcion_incidente or 'Sin descripción' }}
            </div>
          </div>

          <div class="mb-3">
            <strong>Análisis:</strong>
            <div class="mt-2 p-3 rounded-3 bg-light border" style="white-space: pre-wrap;">
              {{ met.analisis or 'No hay análisis generado.' }}
            </div>
          </div>

        </div>
      </div>
    </div>

    <style>
      body{
        background:#b0b6bf !important;
        background-image:none !important;
      }
    </style>
    """, met=met)

    return render_template_string(BASE, content=Markup(html))

# =========================
# Eliminar
# =========================

@app.route('/metricas/incidentes/<int:id>/delete', methods=['POST'])
@login_required
def metricas_incidente_delete(id):
    met = MetricaIncidente.query.get_or_404(id)
    try:
        db.session.delete(met)
        db.session.commit()
        flash("Métrica de incidente eliminada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        print("Error al eliminar métrica de incidente:", e)
        flash("Ocurrió un error al eliminar la métrica.", "danger")

    return redirect(url_for('metricas_incidente_matriz'))

#==========================================
# Métricas de Vulnerabilidades
#==========================================

# =========================================
# HELPERS 
# =========================================

from datetime import date, datetime, timedelta

def _to_date_only(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value

def _primer_dia_mes(anio: int, mes: int) -> date:
    return date(anio, mes, 1)

def _ultimo_dia_mes(anio: int, mes: int) -> date:
    if mes == 12:
        return date(anio, 12, 31)
    return date(anio, mes + 1, 1) - timedelta(days=1)

def vulnerabilidad_activa_en_mes(v, anio: int, mes: int) -> bool:
    """
    Cuenta la vulnerabilidad en un mes si estuvo abierta en cualquier día
    entre fecha_identificacion y fecha_cierre.
    Si no tiene fecha_cierre y sigue abierta, se toma hasta hoy.
    """
    fi = _to_date_only(v.fecha_identificacion)
    if not fi:
        return False

    fc = _to_date_only(v.fecha_cierre)
    fin_intervalo = fc or date.today()

    inicio_mes = _primer_dia_mes(anio, mes)
    fin_mes = _ultimo_dia_mes(anio, mes)

    return fi <= fin_mes and fin_intervalo >= inicio_mes

def construir_metrica_vuln_activas_mensual(year: int, config, vulnerabilidades):
    """
    Devuelve:
      detalle_mensual = {
        1: {
          "filas": [
             {
               "clasificacion": "Crítica",
               "cantidad_aceptada": 2,
               "cantidad_real": 4,
               "cumple": False,
               "excedente": 2
             }
          ]
        },
        ...
      }

      alertas = [
        {
          "mes": 1,
          "clasificacion": "Crítica",
          "cantidad_aceptada": 2,
          "cantidad_real": 4,
          "excedente": 2
        }
      ]
    """
    detalle_mensual = {}
    alertas = []

    filas_cfg = []
    if config:
        filas_cfg = list(config.clasificaciones or [])

    for mes in range(1, 13):
        filas_mes = []

        for fila_cfg in filas_cfg:
            clasif = (fila_cfg.clasificacion or "").strip()
            if not clasif:
                continue

            cantidad_aceptada = int(fila_cfg.cantidad_aceptada or 0)
            cantidad_real = 0

            for v in vulnerabilidades:
                if normalizar_clasificacion(v.clasificacion) != normalizar_clasificacion(clasif):
                    continue

                if vulnerabilidad_activa_en_mes(v, year, mes):
                    cantidad_real += 1

            cumple = cantidad_real <= cantidad_aceptada
            excedente = max(0, cantidad_real - cantidad_aceptada)

            fila = {
                "clasificacion": clasif,
                "cantidad_aceptada": cantidad_aceptada,
                "cantidad_real": cantidad_real,
                "cumple": cumple,
                "excedente": excedente,
            }
            filas_mes.append(fila)

            if not cumple:
                alertas.append({
                    "mes": mes,
                    "clasificacion": clasif,
                    "cantidad_aceptada": cantidad_aceptada,
                    "cantidad_real": cantidad_real,
                    "excedente": excedente,
                })

        detalle_mensual[mes] = {"filas": filas_mes}

    return detalle_mensual, alertas


@app.route('/metricas/vulnerabilidades', methods=['GET', 'POST'])
@login_required
def metricas_vulnerabilidades():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Métricas"):
        flash("No tiene permiso para ingresar al módulo de métricas de vulnerabilidades.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == 'auditor')

    # -----------------------------
    # 1) Filtro de año
    # -----------------------------
    year = request.args.get('year', type=int)
    today = date.today()
    if not year:
        year = today.year

    # -----------------------------
    # 1.1) Guardar edición manual del resumen ejecutivo
    # -----------------------------
    if request.method == 'POST':
        if read_only:
            flash("El rol Auditor no puede editar análisis.", "danger")
            return redirect(url_for('metricas_vulnerabilidades', year=year))

        accion = (request.form.get('accion') or '').strip()

        if accion == 'guardar_resumen_ejecutivo':
            year_post = request.form.get('year', type=int) or year
            texto_resumen = limpiar_texto_ia_global(
                (request.form.get('analisis_resumen_ejecutivo') or '').strip()
            )

            analisis_vuln_manual_map = session.get('analisis_vuln_manual_map', {})
            analisis_vuln_manual_map[str(year_post)] = texto_resumen
            session['analisis_vuln_manual_map'] = analisis_vuln_manual_map

            flash("Resumen ejecutivo actualizado correctamente.", "success")
            return redirect(url_for('metricas_vulnerabilidades', year=year_post))

    # -----------------------------
    # 2) Cargar configuración SLA
    # -----------------------------
    config = MetricasVulnerabilidadesConfig.query.first()

    sla_por_clas_norm = {}

    if config:
        for fila in config.clasificaciones:
            key = normalizar_clasificacion(fila.clasificacion)
            if key and fila.tiempo_max_cierre_dias is not None:
                sla_por_clas_norm[key] = fila.tiempo_max_cierre_dias

    def get_sla_dias(cls_raw):
        key = normalizar_clasificacion(cls_raw)
        if not key:
            return None
        return sla_por_clas_norm.get(key)

    # -----------------------------
    # 3) Cargar vulnerabilidades
    # -----------------------------
    inicio_dt = datetime(year, 1, 1)
    fin_dt    = datetime(year + 1, 1, 1)

    cerradas = (
        VulnerabilidadRegistro.query
        .filter(VulnerabilidadRegistro.estado == 'Cerrado')
        .filter(VulnerabilidadRegistro.fecha_identificacion.isnot(None))
        .filter(
            db.or_(
                db.and_(
                    VulnerabilidadRegistro.fecha_cierre.isnot(None),
                    VulnerabilidadRegistro.fecha_cierre >= inicio_dt,
                    VulnerabilidadRegistro.fecha_cierre < fin_dt,
                ),
                db.and_(
                    VulnerabilidadRegistro.fecha_cierre.is_(None),
                    VulnerabilidadRegistro.fecha_identificacion >= inicio_dt,
                    VulnerabilidadRegistro.fecha_identificacion < fin_dt,
                )
            )
        )
        .all()
    )

    abiertas = (
        VulnerabilidadRegistro.query
        .filter(VulnerabilidadRegistro.estado == 'Abierto')
        .filter(VulnerabilidadRegistro.fecha_identificacion.isnot(None))
        .all()
    )

    todas_con_fecha = (
        VulnerabilidadRegistro.query
        .filter(VulnerabilidadRegistro.fecha_identificacion.isnot(None))
        .all()
    )

    # -----------------------------
    # 4) Métrica mensual de activas por clasificación
    # -----------------------------
    metricas_activas_mensual, alertas_activas_mensual = construir_metrica_vuln_activas_mensual(
        year=year,
        config=config,
        vulnerabilidades=todas_con_fecha
    )

    # -----------------------------
    # 5) Clasificar vulnerabilidades cerradas por año y mes
    # -----------------------------
    cerradas_anio = []
    anio_por_clas = {}
    anio_dentro_tiempo = 0
    anio_fuera_tiempo = 0

    mensual = {}
    cerradas_fuera_sla = []
    cerradas_fuera_por_clas = {}

    for v in cerradas:
        cierre = v.fecha_cierre or v.fecha_identificacion
        if not cierre:
            continue

        if cierre.year != year:
            continue

        cerradas_anio.append(v)

        cls_label = v.clasificacion or 'Sin clasificar'
        sla_dias = get_sla_dias(v.clasificacion)

        dias_cierre = None
        if v.fecha_identificacion:
            dias_cierre = (cierre - v.fecha_identificacion).days
            if dias_cierre < 0:
                dias_cierre = 0

        data_anio = anio_por_clas.setdefault(cls_label, {
            'sla_dias': sla_dias,
            'dentro': 0,
            'fuera': 0
        })

        if sla_dias is not None and dias_cierre is not None:
            if dias_cierre <= sla_dias:
                anio_dentro_tiempo += 1
                data_anio['dentro'] += 1
            else:
                anio_fuera_tiempo += 1
                data_anio['fuera'] += 1

                cierre_eff = cierre
                cerradas_fuera_sla.append({
                    "codigo": v.codigo,
                    "clasificacion": cls_label,
                    "responsable": v.responsable,
                    "fecha_identificacion": v.fecha_identificacion,
                    "fecha_cierre": cierre_eff,
                    "dias_cierre": dias_cierre,
                    "sla_dias": sla_dias,
                })

                info = cerradas_fuera_por_clas.setdefault(cls_label, {
                    "sla_dias": sla_dias,
                    "cantidad": 0
                })
                info["cantidad"] += 1

        m = cierre.month
        data_mes = mensual.setdefault(m, {
            'total': 0,
            'dentro': 0,
            'fuera': 0
        })
        data_mes['total'] += 1

        if sla_dias is not None and dias_cierre is not None:
            if dias_cierre <= sla_dias:
                data_mes['dentro'] += 1
            else:
                data_mes['fuera'] += 1

    total_cerradas_anio = len(cerradas_anio)
    pct_anio_dentro = round((anio_dentro_tiempo * 100.0 / total_cerradas_anio), 2) if total_cerradas_anio > 0 else 0.0
    pct_anio_fuera  = round((anio_fuera_tiempo  * 100.0 / total_cerradas_anio), 2) if total_cerradas_anio > 0 else 0.0

    # -----------------------------
    # 6) Backlog abiertas vencidas
    # -----------------------------
    vencidas = []
    vencidas_por_clas = {}

    for v in abiertas:
        cls_label = v.clasificacion or 'Sin clasificar'
        sla_dias = get_sla_dias(v.clasificacion)

        if sla_dias is None or not v.fecha_identificacion:
            continue

        fi = v.fecha_identificacion
        if hasattr(fi, "date"):
            fi = fi.date()

        dias_abierta = (today - fi).days

        if dias_abierta > sla_dias:
            vencidas.append({
                'codigo': v.codigo,
                'clasificacion': cls_label,
                'responsable': v.responsable,
                'fecha_identificacion': v.fecha_identificacion,
                'dias_abierta': dias_abierta,
                'sla_dias': sla_dias
            })

            info = vencidas_por_clas.setdefault(cls_label, {
                'sla_dias': sla_dias,
                'cantidad': 0
            })
            info['cantidad'] += 1

    # -----------------------------
    # 7) Inyectar análisis guardados por código
    # -----------------------------
    codigos_vencidas = [x["codigo"] for x in vencidas]
    analisis_map = {}

    if codigos_vencidas:
        regs = VulnerabilidadAnalisis.query.filter(
            VulnerabilidadAnalisis.codigo.in_(codigos_vencidas)
        ).all()
        analisis_map = {r.codigo: (r.analisis or "") for r in regs}

    for x in vencidas:
        x["analisis"] = analisis_map.get(x["codigo"], "")

    codigos_cerradas = [x["codigo"] for x in cerradas_fuera_sla]
    analisis_map_cerradas = {}

    if codigos_cerradas:
        regs = VulnerabilidadAnalisis.query.filter(
            VulnerabilidadAnalisis.codigo.in_(codigos_cerradas)
        ).all()
        analisis_map_cerradas = {r.codigo: (r.analisis or "") for r in regs}

    for x in cerradas_fuera_sla:
        x["analisis"] = analisis_map_cerradas.get(x["codigo"], "")

    # -----------------------------
    # 8) Años disponibles
    # -----------------------------
    years_in_db = (
        db.session.query(
            db.func.min(VulnerabilidadRegistro.fecha_identificacion),
            db.func.max(VulnerabilidadRegistro.fecha_identificacion)
        ).first()
    )

    year_options = []
    if years_in_db and years_in_db[0] and years_in_db[1]:
        min_year = years_in_db[0].year
        max_year = years_in_db[1].year
        for y in range(min_year, max_year + 1):
            year_options.append(y)
    else:
        year_options = [year]

    year_from_query = request.args.get('year', type=int)
    if year_from_query is None:
        if year_options:
            year = max(year_options)
    else:
        if year not in year_options and year_options:
            year = max(year_options)

    # -----------------------------
    # 9) IA SOLO POR BOTÓN
    # -----------------------------
    analisis_ia = None
    generar_ai = request.args.get('generar_ai', type=int, default=0)

    if generar_ai == 1 and not read_only:
        datos_metricas = {
            "anio": year,
            "resumen_anual": {
                "total_cerradas": total_cerradas_anio,
                "dentro_sla": anio_dentro_tiempo,
                "fuera_sla": anio_fuera_tiempo,
                "pct_dentro": pct_anio_dentro,
                "pct_fuera": pct_anio_fuera,
            },
            "resumen_mensual": {
                m: {
                    "total": data["total"],
                    "dentro": data["dentro"],
                    "fuera": data["fuera"],
                }
                for m, data in mensual.items()
            },
            "metricas_activas_mensual": {
                m: data["filas"]
                for m, data in metricas_activas_mensual.items()
            },
            "backlog": {
                "total_vencidas": len(vencidas),
                "por_clasificacion": {
                    cls: {
                        "sla_dias": data["sla_dias"],
                        "cantidad": data["cantidad"],
                    }
                    for cls, data in vencidas_por_clas.items()
                },
            },
        }

        try:
             
            analisis_ia = ai_text_metricas(prompt = f"""
        Eres un experto en gestión de vulnerabilidades y ciberseguridad.

        Analiza las siguientes métricas del año {datos_metricas["anio"]} y genera un resumen ejecutivo claro, profesional y útil para dirección.

        Incluye:
        1. Evaluación del cumplimiento de SLA.
        2. Principales problemas identificados.
        3. Riesgos operativos derivados.
        4. Evaluación del backlog (vulnerabilidades abiertas vencidas).
        5. Conclusión ejecutiva clara.

        DATOS:
        {datos_metricas}

        REGLAS:
        - No inventes información.
        - No uses lenguaje condicional.
        - Redacción ejecutiva.
        - Máximo 4 párrafos.
        """)
            analisis_ia = limpiar_texto_ia_global(analisis_ia or "")

            analisis_vuln_manual_map = session.get('analisis_vuln_manual_map', {})
            analisis_vuln_manual_map[str(year)] = analisis_ia
            session['analisis_vuln_manual_map'] = analisis_vuln_manual_map
            
        except Exception as e:
            print("Error al generar análisis IA métricas de vulnerabilidades:", e)
            analisis_ia = None

    analisis_vuln_manual_map = session.get('analisis_vuln_manual_map', {})
    analisis_manual_year = analisis_vuln_manual_map.get(str(year), None)
    if analisis_manual_year is not None:
        analisis_ia = analisis_manual_year

    inner = render_template_string("""
    <div class="vulnmet-shell">

      <div class="vulnmet-header-card">
        <div class="vulnmet-header-overlay">
          <div class="vulnmet-header-text">
            <h3 class="vulnmet-title m-0">Métricas de Tiempos de Cierre de Vulnerabilidades</h3>
            <div class="vulnmet-subtitle">
              Análisis del cumplimiento de tiempos de cierre (SLA) por clasificación,
              con vista mensual del año seleccionado y backlog de vulnerabilidades abiertas vencidas.
            </div>
          </div>
        </div>
      </div>

      <div class="vulnmet-header-actions">
        
      </div>

      <div class="vulnmet-card p-4 mb-3">
        <div class="vulnmet-section-title">Filtros</div>

        <form method="get" class="row g-3 align-items-end">
          <div class="col-md-3">
            <label class="form-label fw-semibold">Año</label>
            <select class="form-select" name="year">
              {% for y in year_options %}
                <option value="{{ y }}" {% if y == year %}selected{% endif %}>{{ y }}</option>
              {% endfor %}
            </select>
          </div>

          <div class="col-md-3">
            <button type="submit"
                    class="btn btn-primary rounded-pill px-4"
                    onclick="showLoader()">
              Aplicar filtros
            </button>
          </div>
        </form>
      </div>

      <div class="vulnmet-card p-4 mt-4">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
          <div class="vulnmet-section-title mb-0">
            🤖 Análisis IA (Resumen ejecutivo)
          </div>

          <div class="d-flex flex-wrap gap-2">
            {% if read_only %}
              <button type="button"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold"
                      disabled
                      title="El perfil Auditor no puede generar análisis con AI">
                Generar análisis con AI
              </button>
            {% else %}
              <a href="{{ url_for('metricas_vulnerabilidades', year=year, generar_ai=1) }}"
                 class="btn btn-outline-primary rounded-pill px-4 fw-bold"
                 onclick="showLoader()">
                Generar análisis con AI
              </a>
            {% endif %}
          </div>
        </div>

        <form method="POST" id="formResumenEjecutivoVuln">
          <input type="hidden" name="accion" value="guardar_resumen_ejecutivo">
          <input type="hidden" name="year" value="{{ year }}">

          <div class="mb-3">
            <textarea
              name="analisis_resumen_ejecutivo"
              id="resumenEjecutivoBox"
              class="form-control vulnmet-resumen-textarea"
              rows="10"
              readonly>{% if analisis_ia %}{{ analisis_ia }}{% endif %}</textarea>
          </div>

          {% if not analisis_ia %}
            <div class="text-muted mb-3">Aún no se ha generado el análisis IA para este año.</div>
          {% endif %}

          <div class="vulnmet-edit-actions">
            {% if read_only %}
              <button type="button"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold"
                      disabled
                      title="El perfil Auditor no puede editar análisis">
                ✏️ Editar
              </button>

              <button type="button"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold"
                      disabled
                      title="El perfil Auditor no puede cancelar edición">
                Cancelar
              </button>

              <button type="button"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold"
                      disabled
                      title="El perfil Auditor no puede guardar análisis">
                💾 Guardar análisis
              </button>
            {% else %}
              <button type="button"
                      id="btnEditarResumen"
                      class="btn btn-warning rounded-pill px-4 fw-bold text-dark">
                ✏️ Editar
              </button>

              <button type="button"
                      id="btnCancelarResumen"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold d-none">
                Cancelar
              </button>

              <button type="submit"
                      id="btnGuardarResumen"
                      class="btn btn-success rounded-pill px-4 fw-bold d-none">
                💾 Guardar análisis
              </button>
            {% endif %}
          </div>
        </form>
      </div>

      <div class="vulnmet-card p-4 mt-4">
        <div class="vulnmet-section-title">
          Cantidad de Vulnerabilidades Activas Mesuales Aceptadas Según Su Clasificación
        </div>

        <div class="table-responsive vulnmet-table-wrap">
          <table class="table table-sm table-bordered align-middle mb-0">
            <thead class="vulnmet-table-head text-center">
              <tr>
                <th>Mes</th>
                <th>Clasificación</th>
                <th>Cantidad aceptada</th>
                <th>Cantidad real activa</th>
                <th>Excedente</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {% for mes in range(1,13) %}
                {% set data_mes = metricas_activas_mensual.get(mes, {"filas": []}) %}
                {% if data_mes.filas %}
                  {% for fila in data_mes.filas %}
                    <tr class="text-center">
                      <td>{{ "%02d"|format(mes) }}</td>
                      <td>{{ fila.clasificacion }}</td>
                      <td>{{ fila.cantidad_aceptada }}</td>
                      <td class="{% if not fila.cumple %}text-danger fw-bold{% endif %}">
                        {{ fila.cantidad_real }}
                      </td>
                      <td class="{% if fila.excedente > 0 %}text-danger fw-bold{% endif %}">
                        {{ fila.excedente }}
                      </td>
                      <td>
                        {% if fila.cumple %}
                          <span class="badge bg-success">Cumple</span>
                        {% else %}
                          <span class="badge bg-danger">Incumple</span>
                        {% endif %}
                      </td>
                    </tr>
                  {% endfor %}
                {% else %}
                  <tr>
                    <td>{{ "%02d"|format(mes) }}</td>
                    <td colspan="5" class="text-center text-muted">No hay datos configurados.</td>
                  </tr>
                {% endif %}
              {% endfor %}
            </tbody>
          </table>
        </div>

        <div class="vulnmet-section-title mt-4">
          Alertas mensuales por exceso de vulnerabilidades activas
        </div>

        <div class="table-responsive vulnmet-table-wrap">
          <table class="table table-sm table-bordered align-middle mb-0">
            <thead class="vulnmet-table-head text-center">
              <tr>
                <th>Mes</th>
                <th>Clasificación</th>
                <th>Cantidad aceptada</th>
                <th>Cantidad real</th>
                <th>Excedente</th>
              </tr>
            </thead>
            <tbody>
              {% for a in alertas_activas_mensual %}
                <tr class="text-center">
                  <td>{{ "%02d"|format(a.mes) }}</td>
                  <td>{{ a.clasificacion }}</td>
                  <td>{{ a.cantidad_aceptada }}</td>
                  <td class="text-danger fw-bold">{{ a.cantidad_real }}</td>
                  <td class="text-danger fw-bold">{{ a.excedente }}</td>
                </tr>
              {% endfor %}
              {% if alertas_activas_mensual|length == 0 %}
                <tr>
                  <td colspan="5" class="text-center text-muted">
                    No se presentan excesos mensuales frente a la cantidad aceptada configurada.
                  </td>
                </tr>
              {% endif %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="vulnmet-card p-4 mt-4">
        <div class="vulnmet-section-title">
          Cumplimiento mensual por tiempos de cierre (detalle anual {{ year }})
        </div>

        <div class="table-responsive vulnmet-table-wrap">
          <table class="table table-sm table-bordered align-middle mb-0">
            <thead class="vulnmet-table-head text-center">
              <tr>
                <th>Mes</th>
                <th>Cerradas en el mes</th>
                <th>Dentro del tiempo</th>
                <th>Fuera de tiempo</th>
                <th>% dentro</th>
                <th>% fuera</th>
              </tr>
            </thead>
            <tbody>
              {% for m in range(1,13) %}
                {% set data = mensual.get(m) %}
                {% if data %}
                  {% set total = data.total %}
                  {% set dentro = data.dentro %}
                  {% set fuera = data.fuera %}
                  {% set pct_dentro = (dentro * 100.0 / total) if total > 0 else 0 %}
                  {% set pct_fuera = (fuera * 100.0 / total) if total > 0 else 0 %}
                {% else %}
                  {% set total = 0 %}
                  {% set dentro = 0 %}
                  {% set fuera = 0 %}
                  {% set pct_dentro = 0 %}
                  {% set pct_fuera = 0 %}
                {% endif %}
                <tr class="text-center">
                  <td>{{ "%02d"|format(m) }}</td>
                  <td>{{ total }}</td>
                  <td class="text-success fw-semibold">{{ dentro }}</td>
                  <td class="text-danger fw-semibold">{{ fuera }}</td>
                  <td>{{ "%.2f"|format(pct_dentro) }} %</td>
                  <td>{{ "%.2f"|format(pct_fuera) }} %</td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="vulnmet-card p-4 mt-4">
        <div class="vulnmet-section-title">
          📌 Vulnerabilidades cerradas fuera de SLA (año {{ year }})
        </div>

        <div class="table-responsive vulnmet-table-wrap mb-3">
          <table class="table table-sm table-bordered align-middle w-100 mb-0">
            <thead class="vulnmet-table-head text-center">
              <tr>
                <th>Clasificación</th>
                <th>SLA (días)</th>
                <th>Cantidad</th>
              </tr>
            </thead>
            <tbody>
              {% for cls, data in cerradas_fuera_por_clas.items() %}
                <tr class="text-center">
                  <td>{{ cls }}</td>
                  <td>{{ data.sla_dias }}</td>
                  <td class="text-danger fw-semibold">{{ data.cantidad }}</td>
                </tr>
              {% endfor %}
              {% if cerradas_fuera_por_clas|length == 0 %}
                <tr>
                  <td colspan="3" class="text-center text-muted">
                    No hay vulnerabilidades cerradas fuera de SLA en el año seleccionado.
                  </td>
                </tr>
              {% endif %}
            </tbody>
          </table>
        </div>

        <div class="table-responsive vulnmet-table-wrap">
          <table class="table table-sm table-bordered align-middle w-100 mb-0">
            <thead class="vulnmet-table-head text-center">
              <tr>
                <th>Código</th>
                <th>Clasificación</th>
                <th>Responsable</th>
                <th>Fecha identificación</th>
                <th>Fecha cierre</th>
                <th>Días cierre</th>
                <th>SLA (días)</th>
                <th>Análisis</th>
              </tr>
            </thead>
            <tbody>
              {% for v in cerradas_fuera_sla %}
                <tr class="text-center">
                  <td>{{ v.codigo }}</td>
                  <td>{{ v.clasificacion }}</td>
                  <td>{{ v.responsable or '—' }}</td>
                  <td>{{ v.fecha_identificacion.strftime('%Y-%m-%d') if v.fecha_identificacion else '—' }}</td>
                  <td>{{ v.fecha_cierre.strftime('%Y-%m-%d') if v.fecha_cierre else '—' }}</td>
                  <td class="text-danger fw-semibold">{{ v.dias_cierre }}</td>
                  <td>{{ v.sla_dias }}</td>
                  <td class="text-start" style="white-space: normal;">
                    {% if v.analisis %}
                      <div class="small text-truncate" style="max-width: 340px;">
                        {{ v.analisis }}
                      </div>
                    {% else %}
                      <span class="text-muted small">Sin análisis.</span>
                    {% endif %}

                    <div class="d-flex flex-wrap gap-1 mt-1">
                      <a href="{{ url_for('metricas_vulnerabilidades_ver_analisis', codigo=v.codigo, modo='cerrada') }}"
                         class="btn btn-sm btn-outline-primary rounded-pill"
                         onclick="showLoader()">
                        👁️ Ver completo
                      </a>

                      {% if read_only %}
                        <button type="button"
                                class="btn btn-sm btn-outline-secondary rounded-pill"
                                disabled
                                title="El perfil Auditor no puede generar análisis con AI">
                          🤖 Generar análisis con AI
                        </button>
                      {% else %}
                        <a href="{{ url_for('metricas_vulnerabilidades_ver_analisis', codigo=v.codigo, modo='cerrada', regen=1) }}"
                           class="btn btn-sm btn-outline-warning rounded-pill"
                           onclick="showLoader()">
                          🤖 Generar análisis con AI
                        </a>
                      {% endif %}
                    </div>
                  </td>
                </tr>
              {% endfor %}
              {% if cerradas_fuera_sla|length == 0 %}
                <tr>
                  <td colspan="8" class="text-center text-muted">
                    No hay vulnerabilidades cerradas fuera de SLA en el año seleccionado.
                  </td>
                </tr>
              {% endif %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="vulnmet-card p-4 mt-4 mb-4">
        <div class="vulnmet-section-title">
          Backlog de vulnerabilidades abiertas vencidas (fuera de SLA)
        </div>

        <div class="table-responsive vulnmet-table-wrap mb-3">
          <table class="table table-sm table-bordered align-middle w-100 mb-0">
            <thead class="vulnmet-table-head text-center">
              <tr>
                <th>Clasificación</th>
                <th>SLA (días)</th>
                <th>Cantidad vencidas</th>
              </tr>
            </thead>
            <tbody>
              {% for cls, data in vencidas_por_clas.items() %}
                <tr class="text-center">
                  <td>{{ cls }}</td>
                  <td>{{ data.sla_dias }}</td>
                  <td class="text-danger fw-semibold">{{ data.cantidad }}</td>
                </tr>
              {% endfor %}
              {% if vencidas_por_clas|length == 0 %}
                <tr>
                  <td colspan="3" class="text-center text-muted">
                    No hay vulnerabilidades abiertas vencidas fuera de SLA.
                  </td>
                </tr>
              {% endif %}
            </tbody>
          </table>
        </div>

        <div class="table-responsive vulnmet-table-wrap">
          <table class="table table-sm table-bordered align-middle w-100 mb-0">
            <thead class="vulnmet-table-head text-center">
              <tr>
                <th>Código</th>
                <th>Clasificación</th>
                <th>Responsable</th>
                <th>Fecha identificación</th>
                <th>Días abierta</th>
                <th>SLA (días)</th>
                <th>Análisis</th>
              </tr>
            </thead>
            <tbody>
              {% for v in vencidas %}
                <tr class="text-center">
                  <td>{{ v.codigo }}</td>
                  <td>{{ v.clasificacion }}</td>
                  <td>{{ v.responsable or '—' }}</td>
                  <td>{{ v.fecha_identificacion.strftime('%Y-%m-%d') if v.fecha_identificacion else '—' }}</td>
                  <td class="text-danger fw-semibold">{{ v.dias_abierta }}</td>
                  <td>{{ v.sla_dias }}</td>
                  <td class="text-start" style="white-space: normal; min-width: 260px;">
                    {% if v.analisis %}
                      <div class="small text-truncate" style="max-width: 300px;">
                        {{ v.analisis }}
                      </div>
                    {% else %}
                      <span class="text-muted small">Sin análisis.</span>
                    {% endif %}

                    <div class="d-flex flex-wrap gap-1 mt-1">
                      <a href="{{ url_for('metricas_vulnerabilidades_ver_analisis', codigo=v.codigo, modo='abierta') }}"
                         class="btn btn-sm btn-outline-primary rounded-pill"
                         onclick="showLoader()">
                        👁️ Ver completo
                      </a>

                      {% if read_only %}
                        <button type="button"
                                class="btn btn-sm btn-outline-secondary rounded-pill"
                                disabled
                                title="El perfil Auditor no puede generar análisis con AI">
                          🤖 Generar análisis con AI
                        </button>
                      {% else %}
                        <a href="{{ url_for('metricas_vulnerabilidades_ver_analisis', codigo=v.codigo, modo='abierta', regen=1) }}"
                           class="btn btn-sm btn-outline-warning rounded-pill"
                           onclick="showLoader()">
                          🤖 Generar análisis con AI
                        </a>
                      {% endif %}
                    </div>
                  </td>
                </tr>
              {% endfor %}
              {% if vencidas|length == 0 %}
                <tr>
                  <td colspan="7" class="text-center text-muted">
                    No hay vulnerabilidades abiertas vencidas fuera de SLA.
                  </td>
                </tr>
              {% endif %}
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <script>
      (function() {
        const box = document.getElementById("resumenEjecutivoBox");
        const btnEditar = document.getElementById("btnEditarResumen");
        const btnCancelar = document.getElementById("btnCancelarResumen");
        const btnGuardar = document.getElementById("btnGuardarResumen");

        if (!box || !btnEditar || !btnCancelar || !btnGuardar) return;

        const valorOriginal = box.value;

        btnEditar.addEventListener("click", function() {
          box.removeAttribute("readonly");
          box.focus();
          btnEditar.classList.add("d-none");
          btnCancelar.classList.remove("d-none");
          btnGuardar.classList.remove("d-none");
        });

        btnCancelar.addEventListener("click", function() {
          box.value = valorOriginal;
          box.setAttribute("readonly", "readonly");
          btnEditar.classList.remove("d-none");
          btnCancelar.classList.add("d-none");
          btnGuardar.classList.add("d-none");
        });
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

      .vulnmet-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }

      .vulnmet-header-card{
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

      .vulnmet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .vulnmet-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .vulnmet-header-overlay::before{
        content:"🛡️";
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

      .vulnmet-header-text{
        max-width:1200px;
      }

      .vulnmet-header-text::before{
        content:"SGSI · Métricas de Vulnerabilidades";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .vulnmet-title{
        color:#ffffff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
      }

      .vulnmet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
      }

      .vulnmet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .vulnmet-btn-main{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .vulnmet-btn-main:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      .vulnmet-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        margin-bottom:18px;
      }

      .vulnmet-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
      }

      .form-control,
      .form-select,
      textarea.form-control{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
      }

      .form-control:focus,
      .form-select:focus,
      textarea.form-control:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .vulnmet-resumen-textarea{
        min-height:240px;
        line-height:1.45;
        resize:vertical;
        padding:14px 16px;
        background:#f8fafc;
        white-space:pre-wrap;
      }

      .vulnmet-resumen-textarea[readonly]{
        background:#f8fafc;
        color:#374151;
        cursor:default;
      }

      .vulnmet-edit-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin-top:8px;
      }

      .vulnmet-table-wrap{
        max-height:72vh;
        overflow:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .vulnmet-table-wrap .table{
        margin-bottom:0;
      }

      .vulnmet-table-head th,
      .vulnmet-table-wrap .table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1);
        color:#ffffff;
        font-size:.78rem;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border:none;
        padding:9px 8px;
      }

      .vulnmet-table-wrap .table td{
        vertical-align:middle;
        font-size:.82rem;
        padding:9px 8px;
        border-color:#e5edf7;
        color:#101827;
      }

      .vulnmet-table-wrap .table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .vulnmet-table-wrap .table tbody tr:hover{
        background:#eef6ff;
      }

      .alert{
        border-radius:14px !important;
      }

      h3{
        color:#ffffff;
        margin:0;
      }

      @media (max-width:992px){
        .vulnmet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .vulnmet-title{
          font-size:1.20rem;
        }

        .vulnmet-subtitle{
          font-size:.68rem;
        }

        .vulnmet-card{
          padding:14px !important;
        }

        .vulnmet-table-wrap .table td,
        .vulnmet-table-head th{
          font-size:.82rem;
          padding:8px 6px;
        }

        .vulnmet-resumen-textarea{
          min-height:200px;
        }
      }

      @media (max-width:768px){
        .vulnmet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .vulnmet-header-overlay::before{
          margin:0;
        }

        .vulnmet-title,
        .vulnmet-subtitle{
          text-align:center;
        }

        .vulnmet-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """,
    year=year,
    year_options=year_options,
    mensual=mensual,
    vencidas=vencidas,
    vencidas_por_clas=vencidas_por_clas,
    analisis_ia=analisis_ia,
    cerradas_fuera_sla=cerradas_fuera_sla,
    cerradas_fuera_por_clas=cerradas_fuera_por_clas,
    metricas_activas_mensual=metricas_activas_mensual,
    alertas_activas_mensual=alertas_activas_mensual,
    read_only=read_only
    )

    return render_template_string(BASE, content=Markup(inner))

#=================================
# Análisis
#=================================

@app.route('/metricas/vulnerabilidades/<string:codigo>/analisis', methods=['GET', 'POST'])
@login_required
def metricas_vulnerabilidades_ver_analisis(codigo):
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Métricas"):
        flash("No tiene permiso para acceder al análisis de vulnerabilidades.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == 'auditor')

    vuln = VulnerabilidadRegistro.query.filter_by(codigo=codigo).first_or_404()
    modo = request.args.get("modo", "abierta")

    config = MetricasVulnerabilidadesConfig.query.first()
    sla_por_clas_norm = {}
    if config:
        for fila in config.clasificaciones:
            key = normalizar_clasificacion(fila.clasificacion)
            if key and fila.tiempo_max_cierre_dias is not None:
                sla_por_clas_norm[key] = fila.tiempo_max_cierre_dias

    key = normalizar_clasificacion(vuln.clasificacion)
    sla_dias = sla_por_clas_norm.get(key)

    today = date.today()

    fi = vuln.fecha_identificacion
    if fi and hasattr(fi, "date"):
        fi = fi.date()

    dias_abierta = 0
    if fi:
        dias_abierta = (today - fi).days
        if dias_abierta < 0:
            dias_abierta = 0

    cierre_eff = vuln.fecha_cierre or vuln.fecha_identificacion
    if isinstance(cierre_eff, datetime):
        cierre_eff = cierre_eff.date()

    dias_cierre = 0
    if modo == "cerrada":
        dias_cierre = (cierre_eff - fi).days if (fi and cierre_eff) else 0
        if dias_cierre < 0:
            dias_cierre = 0

    reg = VulnerabilidadAnalisis.query.filter_by(codigo=codigo).first()
    if not reg:
        reg = VulnerabilidadAnalisis(codigo=codigo, analisis=None)
        db.session.add(reg)
        db.session.commit()

    if request.method == 'POST':
        if read_only:
            flash("El rol Auditor no puede editar análisis.", "danger")
            return redirect(url_for('metricas_vulnerabilidades_ver_analisis', codigo=codigo, modo=modo))

        reg.analisis = limpiar_texto_ia_global(
            (request.form.get("analisis") or "").strip()
        )
        db.session.commit()
        flash("Análisis actualizado correctamente.", "success")
        return redirect(
            url_for(
                'metricas_vulnerabilidades_ver_analisis',
                codigo=codigo,
                modo=modo
            )
        )

    regen = request.args.get('regen', type=int, default=0)

    if regen == 1:
        if read_only:
            flash("El rol Auditor no puede generar análisis con AI.", "danger")
            return redirect(url_for('metricas_vulnerabilidades_ver_analisis', codigo=codigo, modo=modo))

        try:
            if modo == "cerrada":
                reg.analisis = ai_text_metricas(prompt=f"""
            Eres un experto en gestión de vulnerabilidades.

            Analiza esta vulnerabilidad cerrada:

            Código: {vuln.codigo}
            Clasificación: {vuln.clasificacion}
            Días de cierre: {dias_cierre}
            SLA: {sla_dias}

            Debes:
            1. Indicar si hubo incumplimiento del SLA.
            2. Explicar el impacto operativo.
            3. Identificar la causa probable sin inventar información.
            4. Dar una recomendación concreta.

            Máximo 2 párrafos.
            """)
            else:
                reg.analisis = ai_text_metricas(prompt=f"""
            Eres un experto en gestión de vulnerabilidades.

            Analiza esta vulnerabilidad abierta:

            Código: {vuln.codigo}
            Clasificación: {vuln.clasificacion}
            Responsable: {vuln.responsable}
            Días abierta: {dias_abierta}
            SLA: {sla_dias}

            Debes:
            1. Evaluar si está fuera de SLA.
            2. Explicar el impacto operativo.
            3. Indicar el riesgo asociado al retraso.
            4. Dar una recomendación puntual.

            Máximo 2 párrafos.
            """)

            reg.analisis = limpiar_texto_ia_global((reg.analisis or "").strip())
            db.session.commit()
            flash("Análisis generado correctamente con IA.", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"No se pudo generar el análisis con IA: {e}", "danger")

    inner = render_template_string("""
    <div class="vulna-shell">

      <div class="vulna-header-card">
        <div class="vulna-header-overlay">
          <div class="vulna-header-text">
            <h3 class="vulna-title m-0">Análisis por Código de Vulnerabilidad</h3>
            <div class="vulna-subtitle">
              Código: <b>{{ vuln.codigo }}</b>
              {% if modo == 'cerrada' %}
                · Modo: <b>Cerrada</b>
              {% else %}
                · Modo: <b>Abierta</b>
              {% endif %}
            </div>
          </div>
        </div>
      </div>

      <div class="vulna-header-actions mb-3">
        <a href="{{ url_for('metricas_vulnerabilidades') }}"
           class="btn btn-secondary rounded-pill px-4 fw-bold">
          ⬅️ Volver
        </a>

        {% if read_only %}
          <button type="button"
                  class="btn btn-outline-secondary rounded-pill px-4 fw-bold"
                  disabled
                  title="El perfil Auditor no puede generar análisis con AI">
            🤖 Generar análisis con AI
          </button>
        {% else %}
          <a href="{{ url_for('metricas_vulnerabilidades_ver_analisis', codigo=vuln.codigo, modo=modo, regen=1) }}"
             class="btn btn-primary rounded-pill px-4 fw-bold"
             onclick="showLoader()">
            🤖 Generar análisis con AI
          </a>
        {% endif %}
      </div>

      <div class="vulna-card p-4">
        <div class="row g-3 mb-4">
          <div class="col-md-3">
            <div class="vulna-info-box">
              <div class="vulna-info-label">Clasificación</div>
              <div class="vulna-info-value">{{ vuln.clasificacion or 'Sin clasificar' }}</div>
            </div>
          </div>

          <div class="col-md-3">
            <div class="vulna-info-box">
              <div class="vulna-info-label">Responsable</div>
              <div class="vulna-info-value">{{ vuln.responsable or 'No asignado' }}</div>
            </div>
          </div>

          <div class="col-md-3">
            <div class="vulna-info-box">
              <div class="vulna-info-label">SLA (días)</div>
              <div class="vulna-info-value">{{ sla_dias if sla_dias is not none else 'No definido' }}</div>
            </div>
          </div>

          <div class="col-md-3">
            <div class="vulna-info-box">
              <div class="vulna-info-label">
                {% if modo == 'cerrada' %}Días cierre{% else %}Días abierta{% endif %}
              </div>
              <div class="vulna-info-value">
                {% if modo == 'cerrada' %}{{ dias_cierre }}{% else %}{{ dias_abierta }}{% endif %}
              </div>
            </div>
          </div>
        </div>

        <form method="POST" id="formAnalisisVuln">
          <div class="mb-3">
            <label class="form-label fw-bold">Análisis</label>
            <textarea
              name="analisis"
              id="analisisBox"
              class="form-control vulna-textarea"
              rows="15"
              readonly>{{ reg.analisis or '' }}</textarea>
          </div>

          <div class="vulna-edit-actions">
            {% if read_only %}
              <button type="button"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold"
                      disabled
                      title="El perfil Auditor no puede editar análisis">
                ✏️ Editar
              </button>

              <button type="button"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold"
                      disabled
                      title="El perfil Auditor no puede cancelar edición">
                Cancelar
              </button>

              <button type="button"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold"
                      disabled
                      title="El perfil Auditor no puede guardar análisis">
                💾 Guardar análisis
              </button>
            {% else %}
              <button type="button"
                      id="btnEditarAnalisis"
                      class="btn btn-warning rounded-pill px-4 fw-bold text-dark">
                ✏️ Editar
              </button>

              <button type="button"
                      id="btnCancelarAnalisis"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold d-none">
                Cancelar
              </button>

              <button type="submit"
                      id="btnGuardarAnalisis"
                      class="btn btn-success rounded-pill px-4 fw-bold d-none">
                💾 Guardar análisis
              </button>
            {% endif %}
          </div>
        </form>
      </div>

    </div>

    <script>
      (function() {
        const box = document.getElementById("analisisBox");
        const btnEditar = document.getElementById("btnEditarAnalisis");
        const btnCancelar = document.getElementById("btnCancelarAnalisis");
        const btnGuardar = document.getElementById("btnGuardarAnalisis");

        if (!box || !btnEditar || !btnCancelar || !btnGuardar) return;

        const valorOriginal = box.value;

        btnEditar.addEventListener("click", function() {
          box.removeAttribute("readonly");
          box.focus();
          btnEditar.classList.add("d-none");
          btnCancelar.classList.remove("d-none");
          btnGuardar.classList.remove("d-none");
        });

        btnCancelar.addEventListener("click", function() {
          box.value = valorOriginal;
          box.setAttribute("readonly", "readonly");
          btnEditar.classList.remove("d-none");
          btnCancelar.classList.add("d-none");
          btnGuardar.classList.add("d-none");
        });
      })();
    </script>
    <style>
      body {
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .vulna-shell {
        width:96%;
        max-width:1250px;
        margin:26px auto 24px auto;
      }

      .vulna-header-card {
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

      .vulna-header-card::before {
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .vulna-header-overlay {
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .vulna-header-overlay::before {
        content:"🔍";
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

      .vulna-header-text {
        max-width:1000px;
      }

      .vulna-header-text::before {
        content:"SGSI · Análisis por Código de Vulnerabilidad";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .vulna-title {
        color:#ffffff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
      }

      .vulna-subtitle {
        color:rgba(255,255,255,.95);
        font-size:.78rem;
      }

      .vulna-header-actions {
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .btn {
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .vulna-card {
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .vulna-info-box {
        background:rgba(59,130,246,.08);
        border:1px solid rgba(59,130,246,.12);
        border-radius:14px;
        padding:14px 16px;
        height:100%;
      }

      .vulna-info-label {
        font-size:.82rem;
        color:#334155;
        font-weight:900;
        margin-bottom:5px;
        line-height:1.15;
      }

      .vulna-info-value {
        font-size:.98rem;
        color:#0b4a8f;
        font-weight:950;
        line-height:1.2;
        word-break:break-word;
      }

      .form-control,
      .form-select,
      textarea.form-control {
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
      }

      .form-control:focus,
      .form-select:focus,
      textarea.form-control:focus {
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .vulna-textarea {
        min-height:320px;
        line-height:1.45;
        resize:vertical;
        padding:14px 16px;
        background:#f8fafc;
      }

      .vulna-textarea[readonly] {
        background:#f8fafc;
        color:#374151;
        cursor:default;
      }

      .vulna-edit-actions {
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin-top:8px;
      }

      h3 {
        color:#ffffff;
        margin:0;
      }

      @media (max-width:992px) {
        .vulna-shell {
          width:98%;
          margin:8px auto 22px auto;
        }

        .vulna-title {
          font-size:1.20rem;
        }

        .vulna-subtitle {
          font-size:.68rem;
        }

        .vulna-card {
          padding:14px !important;
        }

        .vulna-info-value {
          font-size:.92rem;
        }

        .vulna-textarea {
          min-height:260px;
        }
      }

      @media (max-width:768px) {
        .vulna-header-overlay {
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .vulna-header-overlay::before {
          margin:0;
        }

        .vulna-title,
        .vulna-subtitle {
          text-align:center;
        }

        .vulna-header-actions .btn {
          width:100%;
        }
      }
    </style>
    """,
    vuln=vuln,
    reg=reg,
    modo=modo,
    sla_dias=sla_dias,
    dias_abierta=dias_abierta,
    dias_cierre=dias_cierre,
    read_only=read_only)

    return render_template_string(BASE, content=Markup(inner))

#=================================
# Guardar análisis
#=================================

@app.route('/metricas/vulnerabilidades/guardar_analisis', methods=['POST'])
@login_required
def guardar_analisis_vulnerabilidades():
    texto = limpiar_texto_ia_global(
        request.form.get('analisis_texto', '').strip()
    )

    if not texto:
        flash("El análisis no puede estar vacío.", "warning")
        return redirect(url_for('metricas_vulnerabilidades'))

    # OPCIÓN 1: SIN GUARDAR EN BD (solo muestra el análisis mientras se mantenga en pantalla)
    #           Para una versión inicial, simplemente volvemos con un flash.
    #           Luego puedo ayudarte a agregar tabla persistente si quieres.
    
    session['analisis_vuln_manual'] = texto  # Se mantiene mientras dura la sesión
    flash("Análisis actualizado correctamente.", "success")
    return redirect(url_for('metricas_vulnerabilidades'))


# ===============================
# Métrica de Cultura 
# ===============================

class CulturaMetricaView:
    """
    Objeto ligero para construir filas calculadas en memoria
    y usarlas en la plantilla Jinja como si fueran registros.
    """
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class CulturaAnalisisAI(db.Model):
    __tablename__ = "cultura_analisis_ai"

    id = db.Column(db.Integer, primary_key=True)
    anio = db.Column(db.Integer, nullable=False, unique=True, index=True)
    analisis = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ===============================
# Helper de cálculo - Cultura
# ===============================

def generar_analisis_cultura_resumen_ai(year: int, registros: list) -> str:
    """
    Genera un resumen ejecutivo anual de la métrica de cultura
    a partir de los registros mensuales calculados en memoria.
    Compatible con Ollama / OpenRouter usando ai_text_metricas.
    """
    if not registros:
        return "No hay datos suficientes para generar un análisis de cultura."

    resumen = []
    total_inducciones = 0
    total_reinducciones = 0
    total_cumplen_programa = 0
    total_cumplen_cobertura = 0
    total_cumplen_eficacia = 0
    total_registros = 0

    for r in registros:
        total_inducciones += int(getattr(r, "total_inducciones", 0) or 0)
        total_reinducciones += int(getattr(r, "total_reinducciones", 0) or 0)
        total_cumplen_programa += int(getattr(r, "cumplen_cumplimiento", 0) or 0)
        total_cumplen_cobertura += int(getattr(r, "cumplen_cobertura", 0) or 0)
        total_cumplen_eficacia += int(getattr(r, "cumplen_eficacia", 0) or 0)
        total_registros += int(getattr(r, "total_registros_mes", 0) or 0)

        resumen.append({
            "anio": getattr(r, "anio", ""),
            "mes": getattr(r, "mes", ""),
            "inducciones": getattr(r, "total_inducciones", 0),
            "reinducciones": getattr(r, "total_reinducciones", 0),
            "cumplen_programa": getattr(r, "cumplen_cumplimiento", 0),
            "cumplen_cobertura": getattr(r, "cumplen_cobertura", 0),
            "cumplen_eficacia": getattr(r, "cumplen_eficacia", 0),
            "pct_programa": getattr(r, "pct_cumplimiento", 0),
            "pct_cobertura": getattr(r, "pct_cobertura", 0),
            "pct_eficacia": getattr(r, "pct_eficacia", 0),
        })

    prompt = f"""
Eres un analista experto en cultura de seguridad y ciberseguridad.

Analiza las métricas anuales consolidadas de cultura del año {year}.

Totales del año:
- Inducciones efectuadas: {total_inducciones}
- Reinducciones efectuadas: {total_reinducciones}
- Registros evaluados: {total_registros}
- Cumplen Programa de Capacitación: {total_cumplen_programa}
- Cumplen Cobertura: {total_cumplen_cobertura}
- Cumplen Evaluaciones Eficaces: {total_cumplen_eficacia}

Detalle mensual:
{resumen}

Instrucciones:
1. Redacta un resumen ejecutivo claro.
2. Menciona fortalezas y brechas.
3. Indica si hay mejora, estabilidad o deterioro.
4. Propón recomendaciones concretas.

Responde en ESPAÑOL, en máximo 10 líneas, texto corrido, sin viñetas ni títulos.
""".strip()

    try:
        texto = ai_text_metricas(
            prompt=prompt,
            system_prompt="Eres un experto en cultura de seguridad, formación y métricas de concientización. Responde en español, con enfoque ejecutivo y profesional.",
            temperature=0.3,
            max_tokens=700,
            openrouter_model="openai/gpt-4.1-mini"
        ).strip()

        if not texto:
            texto = "No se pudo generar automáticamente el análisis de cultura."

        return texto

    except Exception as e:
        print("Error al generar análisis IA de cultura:", e)
        return f"No se pudo generar automáticamente el análisis de cultura. Detalle: {e}"

def parse_fecha_plan_cf(valor):
    """
    Convierte fecha_programada a date.
    Soporta:
    - date
    - datetime
    - str: 'YYYY-MM-DD', 'YYYY-MM-DD HH:MM:SS', 'YYYY-MM-DDTHH:MM:SS'
    """
    if not valor:
        return None

    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor

    if isinstance(valor, datetime):
        return valor.date()

    if isinstance(valor, str):
        txt = valor.strip()
        if not txt:
            return None

        formatos = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
        ]

        for fmt in formatos:
            try:
                return datetime.strptime(txt, fmt).date()
            except ValueError:
                continue

    return None

def calcular_metricas_cultura_desde_plan_cf(anio: int, mes: int):
    """
    Calcula la métrica mensual de cultura directamente desde PlanCFRegistro.

    NUEVAS REGLAS:
    1) Contar cuántas inducciones se efectuaron en el mes
    2) Contar cuántas reinducciones se efectuaron en el mes
    3) Contar cuántos registros del mes cumplen:
       - Cumplimiento Programa Capacitación (%) >= parámetro configurado
       - Cobertura (%) >= parámetro configurado
       - Evaluaciones Eficaces (%) >= parámetro configurado
    """

    registros_all = (
        PlanCFRegistro.query
        .filter(PlanCFRegistro.fecha_programada.isnot(None))
        .order_by(PlanCFRegistro.id.desc())
        .all()
    )

    registros_mes = []
    for r in registros_all:
        fecha_prog = parse_fecha_plan_cf(r.fecha_programada)
        if not fecha_prog:
            continue
        if fecha_prog.year == anio and fecha_prog.month == mes:
            registros_mes.append(r)

    config_cultura = MetricasCulturaConfig.query.first()

    meta_cumplimiento = config_cultura.meta_general if config_cultura and config_cultura.meta_general is not None else None
    meta_cobertura = config_cultura.meta_fi if config_cultura and config_cultura.meta_fi is not None else None
    meta_eficacia = config_cultura.meta_ep if config_cultura and config_cultura.meta_ep is not None else None

    total_registros_mes = len(registros_mes)

    # =========================================
    # 1) Cuántas inducciones se efectuaron
    # =========================================
    total_inducciones = 0

    # =========================================
    # 2) Cuántas reinducciones se efectuaron
    # =========================================
    total_reinducciones = 0

    # =========================================
    # 3) Cuántos cumplen cada indicador
    # =========================================
    cumplen_cumplimiento = 0
    cumplen_cobertura = 0
    cumplen_eficacia = 0

    for r in registros_mes:
        tipo = (getattr(r, "tipo_capacitacion", "") or "").strip().lower()

        if tipo == "inducción":
            total_inducciones += 1
        elif tipo == "reinducción":
            total_reinducciones += 1

        cumplimiento_pct = float(getattr(r, "cumplimiento_pct", 0) or 0)
        cobertura_pct = float(getattr(r, "cobertura_pct", 0) or 0)
        eficaces_pct = float(getattr(r, "eficaces_pct", 0) or 0)

        if meta_cumplimiento is not None and cumplimiento_pct >= float(meta_cumplimiento):
            cumplen_cumplimiento += 1

        if meta_cobertura is not None and cobertura_pct >= float(meta_cobertura):
            cumplen_cobertura += 1

        if meta_eficacia is not None and eficaces_pct >= float(meta_eficacia):
            cumplen_eficacia += 1

    # Porcentajes de cumplimiento mensual de cada indicador
    pct_cumplimiento = round((cumplen_cumplimiento / total_registros_mes) * 100.0, 2) if total_registros_mes > 0 else 0.0
    pct_cobertura = round((cumplen_cobertura / total_registros_mes) * 100.0, 2) if total_registros_mes > 0 else 0.0
    pct_eficacia = round((cumplen_eficacia / total_registros_mes) * 100.0, 2) if total_registros_mes > 0 else 0.0

    return {
        "anio": int(anio),
        "mes": int(mes),
        "total_registros_mes": int(total_registros_mes),
        "total_inducciones": int(total_inducciones),
        "total_reinducciones": int(total_reinducciones),
        "cumplen_cumplimiento": int(cumplen_cumplimiento),
        "cumplen_cobertura": int(cumplen_cobertura),
        "cumplen_eficacia": int(cumplen_eficacia),
        "pct_cumplimiento": pct_cumplimiento,
        "pct_cobertura": pct_cobertura,
        "pct_eficacia": pct_eficacia,
        "meta_cumplimiento": float(meta_cumplimiento) if meta_cumplimiento is not None else None,
        "meta_cobertura": float(meta_cobertura) if meta_cobertura is not None else None,
        "meta_eficacia": float(meta_eficacia) if meta_eficacia is not None else None,
    }

def obtener_periodos_cultura_desde_plan_cf():
    """
    Devuelve lista de tuplas (anio, mes) existentes en PlanCFRegistro
    usando fecha_programada, aunque venga como texto.
    """
    filas = (
        db.session.query(PlanCFRegistro.fecha_programada)
        .filter(PlanCFRegistro.fecha_programada.isnot(None))
        .order_by(PlanCFRegistro.id.desc())
        .all()
    )

    vistos = set()
    periodos = []

    for (fecha_prog_raw,) in filas:
        fecha_prog = parse_fecha_plan_cf(fecha_prog_raw)
        if not fecha_prog:
            continue

        anio = fecha_prog.year
        mes = fecha_prog.month
        clave = (anio, mes)

        if clave not in vistos:
            vistos.add(clave)
            periodos.append(clave)

    return periodos

def analizar_metricas_cultura_ia(registro: "MetricasCultura") -> str:
    """
    Genera un análisis ejecutivo mensual de la métrica de cultura
    usando IA, compatible con Ollama / OpenRouter.
    """
    nombre_mes = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }.get(registro.mes, str(registro.mes))

    prompt = f"""
Eres responsable de cultura y seguridad de la información.
Analiza la siguiente métrica mensual de cultura de seguridad.

Año: {registro.anio}
Mes: {nombre_mes}
Cantidad de personas contratadas: {registro.personas_contratadas}
Total de personas con formación aprobada inicialmente: {registro.formacion_inicial_aprobada}
Total de personas con reinducción: {registro.personas_reinduccion}
Total de personas con reinducción aprobada: {registro.reinduccion_aprobada}
Meta alcanzada de formación (%): {registro.meta_formacion:.2f}
Actividades SI planeadas: {registro.actividades_planeadas}
Actividades SI ejecutadas: {registro.actividades_ejecutadas}
Meta alcanzada de actividades (%): {registro.meta_actividades:.2f}
Resultado de la meta u objetivo general (%): {registro.resultado_meta_general:.2f}

Escribe un análisis mensual de la métrica, en máximo 10 líneas, en español, donde incluyas:
- lectura general del resultado del mes
- si las metas de formación y actividades se ven cumplidas o no
- riesgos o brechas relevantes
- recomendaciones concretas para el siguiente mes

Responde solo con texto corrido, en uno o dos párrafos, sin viñetas ni títulos.
""".strip()

    try:
        texto = ai_text_metricas(
            prompt=prompt,
            system_prompt="Eres un experto en cultura de seguridad y métricas de concientización. Responde en español, de forma ejecutiva, clara y profesional.",
            temperature=0.2,
            max_tokens=500,
            openrouter_model="openai/gpt-4.1-mini"
        ).strip()

        if not texto:
            texto = "No se pudo generar automáticamente el análisis mensual de la métrica. Por favor, edítalo manualmente."

        return texto

    except Exception as e:
        print("Error al generar análisis mensual IA de cultura:", e)
        return f"No se pudo generar automáticamente el análisis mensual de la métrica. Detalle: {e}"

def recalcular_metricas_cultura(
    personas_contratadas: int,
    formacion_inicial_aprob: int,
    personas_reinduccion: int,
    reinduccion_aprobada: int,
    actividades_planeadas: int,
    actividades_ejecutadas: int
):
    """
    Reglas actuales:

    1) Promedio meta formación =
       (Total asistentes del mes / Total personas contratadas) * 100

    2) Meta alcanzada de planeación =
       (Actividades SI planeadas / Actividades SI ejecutadas) * 100

    3) Resultado meta / objetivo general =
       (Promedio meta formación + Meta alcanzada de planeación) / 2
    """

    personas_contratadas = int(personas_contratadas or 0)
    formacion_inicial_aprob = int(formacion_inicial_aprob or 0)
    personas_reinduccion = int(personas_reinduccion or 0)
    reinduccion_aprobada = int(reinduccion_aprobada or 0)
    actividades_planeadas = int(actividades_planeadas or 0)
    actividades_ejecutadas = int(actividades_ejecutadas or 0)

    # 1) Promedio meta formación
    if personas_contratadas > 0:
        meta_formacion = (formacion_inicial_aprob / personas_contratadas) * 100.0
    else:
        meta_formacion = 0.0

    if meta_formacion < 0:
        meta_formacion = 0.0

    # 2) Meta alcanzada de planeación
    if actividades_ejecutadas > 0:
        meta_actividades = (actividades_planeadas / actividades_ejecutadas) * 100.0
    else:
        meta_actividades = 0.0

    if meta_actividades < 0:
        meta_actividades = 0.0

    # 3) Resultado general
    resultado_meta_general = (meta_formacion + meta_actividades) / 2.0

    if resultado_meta_general < 0:
        resultado_meta_general = 0.0

    return {
        "meta_formacion": round(meta_formacion, 2),
        "meta_actividades": round(meta_actividades, 2),
        "resultado_meta_general": round(resultado_meta_general, 2),
    }



# ===============================
# Métrica de Cultura - Matriz
# ===============================

@app.route("/metricas/cultura/matriz", methods=["GET", "POST"])
@login_required
def metricas_cultura_matriz():
    user = User.query.get(session.get('user_id'))

    # El auditor sí puede ingresar al módulo en modo consulta
    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Métricas"):
        flash("No tiene permiso para ingresar a métricas de cultura.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == 'auditor')

    # ============================
    # 1) Leer filtros
    # ============================
    year_param = request.args.get("year", "", type=str)
    month_param = request.args.get("month", "", type=str)

    year_selected = None
    month_selected = None

    if year_param and year_param != "all":
        try:
            year_selected = int(year_param)
        except ValueError:
            year_selected = None

    if month_param and month_param != "all":
        try:
            month_selected = int(month_param)
        except ValueError:
            month_selected = None

    # ============================
    # 2) Obtener periodos desde PlanCFRegistro
    # ============================
    periodos = obtener_periodos_cultura_desde_plan_cf()

    periodos_filtrados = []
    for anio, mes in periodos:
        if year_selected is not None and anio != year_selected:
            continue
        if month_selected is not None and mes != month_selected:
            continue
        periodos_filtrados.append((anio, mes))

    periodos_filtrados.sort(key=lambda x: (x[0], x[1]), reverse=True)

    # ============================
    # 3) Construir registros mensuales
    # ============================
    registros = []

    total_inducciones = 0
    total_reinducciones = 0
    total_cumplen_cumplimiento = 0
    total_cumplen_cobertura = 0
    total_cumplen_eficacia = 0
    total_registros_mes = 0

    for anio, mes in periodos_filtrados:
        vals = calcular_metricas_cultura_desde_plan_cf(anio, mes)

        total_inducciones += int(vals["total_inducciones"] or 0)
        total_reinducciones += int(vals["total_reinducciones"] or 0)
        total_cumplen_cumplimiento += int(vals["cumplen_cumplimiento"] or 0)
        total_cumplen_cobertura += int(vals["cumplen_cobertura"] or 0)
        total_cumplen_eficacia += int(vals["cumplen_eficacia"] or 0)
        total_registros_mes += int(vals["total_registros_mes"] or 0)

        registros.append(CulturaMetricaView(
            anio=vals["anio"],
            mes=vals["mes"],
            total_registros_mes=vals["total_registros_mes"],
            total_inducciones=vals["total_inducciones"],
            total_reinducciones=vals["total_reinducciones"],
            cumplen_cumplimiento=vals["cumplen_cumplimiento"],
            cumplen_cobertura=vals["cumplen_cobertura"],
            cumplen_eficacia=vals["cumplen_eficacia"],
            pct_cumplimiento=vals["pct_cumplimiento"],
            pct_cobertura=vals["pct_cobertura"],
            pct_eficacia=vals["pct_eficacia"],
            meta_cumplimiento=vals["meta_cumplimiento"],
            meta_cobertura=vals["meta_cobertura"],
            meta_eficacia=vals["meta_eficacia"],
        ))

    total_periodos = len(registros)

    year_options = sorted(list({anio for anio, _ in periodos}), reverse=False)
    if not year_options:
        year_options = [date.today().year]

    config_cultura = MetricasCulturaConfig.query.first()

   # ============================
    # 4) Resumen IA por año (persistido en BD)
    # ============================
    year_ai = year_selected if year_selected is not None else (
        periodos_filtrados[0][0] if periodos_filtrados else date.today().year
    )

    analisis_row = CulturaAnalisisAI.query.filter_by(anio=year_ai).first()
    if not analisis_row:
        analisis_row = CulturaAnalisisAI(anio=year_ai, analisis="")
        db.session.add(analisis_row)
        db.session.commit()

    if request.method == "POST":
        if read_only:
            flash("El rol Auditor no puede editar análisis.", "danger")
            return redirect(url_for(
                "metricas_cultura_matriz",
                year=year_selected or "all",
                month=month_selected or "all"
            ))

        accion = (request.form.get("accion") or "").strip()

        if accion == "guardar_resumen_cultura":
            texto = (request.form.get("analisis_cultura_resumen") or "").strip()
            try:
                analisis_row.analisis = texto
                analisis_row.updated_at = datetime.utcnow()
                db.session.commit()
                flash("Análisis de cultura actualizado correctamente.", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"No se pudo guardar el análisis de cultura: {e}", "danger")

            return redirect(url_for(
                "metricas_cultura_matriz",
                year=year_selected or "all",
                month=month_selected or "all"
            ))

    generar_ai = request.args.get("generar_ai", type=int, default=0)
    analisis_cultura_resumen = analisis_row.analisis or ""

    if generar_ai == 1 and not read_only:
        try:
            analisis_cultura_resumen = generar_analisis_cultura_resumen_ai(year_ai, registros)
            analisis_row.analisis = analisis_cultura_resumen
            analisis_row.updated_at = datetime.utcnow()
            db.session.commit()

            if analisis_cultura_resumen.startswith("No se pudo generar"):
                flash(analisis_cultura_resumen, "warning")
            else:
                flash("Análisis IA de cultura generado correctamente.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"No se pudo generar o guardar el análisis IA de cultura: {e}", "danger")

    inner = render_template_string("""
    <div class="cultmet-shell">

      <div class="cultmet-header-card">
        <div class="cultmet-header-overlay">
          <div class="cultmet-header-text">
            <h3 class="cultmet-title m-0">Métricas de Cultura de Seguridad</h3>
            <div class="cultmet-subtitle">
              Seguimiento mensual de inducciones, reinducciones y cumplimiento de indicadores
              de capacitación, cobertura y evaluaciones eficaces.
            </div>
          </div>
        </div>
      </div>

      <div class="cultmet-header-actions">
        
      </div>

      <div class="cultmet-card p-4 mb-3">
        <div class="cultmet-section-title">Filtros</div>

        <form method="get" class="row g-3 align-items-end">
          <div class="col-md-3">
            <label class="form-label fw-semibold">Año</label>
            <select name="year" class="form-select">
              <option value="all" {% if year_selected is none %}selected{% endif %}>Todos</option>
              {% for y in year_options %}
                <option value="{{ y }}" {% if year_selected == y %}selected{% endif %}>{{ y }}</option>
              {% endfor %}
            </select>
          </div>

          <div class="col-md-3">
            <label class="form-label fw-semibold">Mes</label>
            <select name="month" class="form-select">
              <option value="all" {% if month_selected is none %}selected{% endif %}>Todos</option>
              {% for m in range(1,13) %}
                <option value="{{ m }}" {% if month_selected == m %}selected{% endif %}>
                  {{ "%02d"|format(m) }}
                </option>
              {% endfor %}
            </select>
          </div>

          <div class="col-md-3">
            <button type="submit" class="btn btn-primary rounded-pill px-4">
              Aplicar filtros
            </button>
          </div>
        </form>
      </div>

      <!-- RESUMEN IA -->
      <div class="cultmet-card p-4 mb-3">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
          <div class="cultmet-section-title mb-0">🤖 Análisis IA (Resumen ejecutivo)</div>

          <div class="d-flex flex-wrap gap-2">
            {% if read_only %}
              <button type="button"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold"
                      disabled
                      title="El perfil Auditor no puede generar análisis con AI">
                Generar análisis con AI
              </button>
            {% else %}
              <a href="{{ url_for('metricas_cultura_matriz', year=year_selected or 'all', month=month_selected or 'all', generar_ai=1) }}"
                 class="btn btn-outline-primary rounded-pill px-4 fw-bold">
                Generar análisis con AI
              </a>
            {% endif %}
          </div>
        </div>

        <form method="POST" id="formResumenCultura">
          <input type="hidden" name="accion" value="guardar_resumen_cultura">

          <div class="mb-3">
            <textarea
              name="analisis_cultura_resumen"
              id="resumenCulturaBox"
              class="form-control cultmet-resumen-textarea"
              rows="8"
              readonly>{% if analisis_cultura_resumen %}{{ analisis_cultura_resumen }}{% endif %}</textarea>
          </div>

          {% if not analisis_cultura_resumen %}
            <div class="text-muted mb-3">Aún no se ha generado el análisis IA de cultura para el filtro seleccionado.</div>
          {% endif %}

          <div class="cultmet-edit-actions">
            {% if read_only %}
              <button type="button"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold"
                      disabled
                      title="El perfil Auditor no puede editar análisis">
                ✏️ Editar
              </button>

              <button type="button"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold"
                      disabled
                      title="El perfil Auditor no puede cancelar edición">
                Cancelar
              </button>

              <button type="button"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold"
                      disabled
                      title="El perfil Auditor no puede guardar análisis">
                💾 Guardar análisis
              </button>
            {% else %}
              <button type="button"
                      id="btnEditarResumenCultura"
                      class="btn btn-warning rounded-pill px-4 fw-bold text-dark">
                ✏️ Editar
              </button>

              <button type="button"
                      id="btnCancelarResumenCultura"
                      class="btn btn-outline-secondary rounded-pill px-4 fw-bold d-none">
                Cancelar
              </button>

              <button type="submit"
                      id="btnGuardarResumenCultura"
                      class="btn btn-success rounded-pill px-4 fw-bold d-none">
                💾 Guardar análisis
              </button>
            {% endif %}
          </div>
        </form>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-md-2">
          <div class="cultmet-summary-card">
            <div class="cultmet-summary-label">Períodos</div>
            <div class="cultmet-summary-value">{{ total_periodos }}</div>
          </div>
        </div>
        <div class="col-md-2">
          <div class="cultmet-summary-card">
            <div class="cultmet-summary-label">Inducciones</div>
            <div class="cultmet-summary-value">{{ total_inducciones }}</div>
          </div>
        </div>
        <div class="col-md-2">
          <div class="cultmet-summary-card">
            <div class="cultmet-summary-label">Reinducciones</div>
            <div class="cultmet-summary-value">{{ total_reinducciones }}</div>
          </div>
        </div>
        <div class="col-md-2">
          <div class="cultmet-summary-card">
            <div class="cultmet-summary-label">Cumplen programa</div>
            <div class="cultmet-summary-value">{{ total_cumplen_cumplimiento }}</div>
          </div>
        </div>
        <div class="col-md-2">
          <div class="cultmet-summary-card">
            <div class="cultmet-summary-label">Cumplen cobertura</div>
            <div class="cultmet-summary-value">{{ total_cumplen_cobertura }}</div>
          </div>
        </div>
        <div class="col-md-2">
          <div class="cultmet-summary-card">
            <div class="cultmet-summary-label">Cumplen eficaces</div>
            <div class="cultmet-summary-value">{{ total_cumplen_eficacia }}</div>
          </div>
        </div>
      </div>

      <div class="cultmet-card p-4 mb-4">
        <div class="cultmet-section-title">
          Métricas mensuales
        </div>

        {% if registros|length == 0 %}
          <div class="cultmet-empty-box">
            No hay datos en PlanCFRegistro para los filtros seleccionados.
          </div>
        {% else %}
          <div class="cultmet-metric-grid">
            {% for r in registros %}

              {% set clase_prog = "cultmet-pill-neutral" %}
              {% if r.meta_cumplimiento is not none %}
                {% if r.pct_cumplimiento < r.meta_cumplimiento %}
                  {% set clase_prog = "cultmet-pill-danger" %}
                {% else %}
                  {% set clase_prog = "cultmet-pill-success" %}
                {% endif %}
              {% endif %}

              {% set clase_cov = "cultmet-pill-neutral" %}
              {% if r.meta_cobertura is not none %}
                {% if r.pct_cobertura < r.meta_cobertura %}
                  {% set clase_cov = "cultmet-pill-danger" %}
                {% else %}
                  {% set clase_cov = "cultmet-pill-success" %}
                {% endif %}
              {% endif %}

              {% set clase_efi = "cultmet-pill-neutral" %}
              {% if r.meta_eficacia is not none %}
                {% if r.pct_eficacia < r.meta_eficacia %}
                  {% set clase_efi = "cultmet-pill-danger" %}
                {% else %}
                  {% set clase_efi = "cultmet-pill-success" %}
                {% endif %}
              {% endif %}

              <div class="cultmet-metric-card">

                <div class="cultmet-metric-top">
                  <div>
                    <div class="cultmet-period-label">Resumen mensual</div>
                    <div class="cultmet-period-value">
                      {{ r.anio }} · {{ "%02d"|format(r.mes) }}
                    </div>
                  </div>

                  <div class="cultmet-period-badge">
                    {{ "%02d"|format(r.mes) }}/{{ r.anio }}
                  </div>
                </div>

                <div class="cultmet-metric-section">
                  <div class="cultmet-metric-section-title">Cantidad de capacitaciones efectuadas en el mes</div>

                  <div class="cultmet-mini-grid two-cols">
                    <div class="cultmet-mini-box">
                      <div class="cultmet-mini-label">Inducciones efectuadas</div>
                      <div class="cultmet-mini-value">{{ r.total_inducciones }}</div>
                    </div>

                    <div class="cultmet-mini-box">
                      <div class="cultmet-mini-label">Reinducciones efectuadas</div>
                      <div class="cultmet-mini-value">{{ r.total_reinducciones }}</div>
                    </div>
                  </div>
                </div>

                <div class="cultmet-metric-section">
                  <div class="cultmet-metric-section-title">Cumplimiento mensual de indicadores</div>

                  <div class="cultmet-kpi-grid">
                    <div class="cultmet-kpi-box">
                      <div class="cultmet-kpi-label">Cumplimiento Programa Capacitación</div>
                      <div class="cultmet-kpi-value {{ 'text-danger' if 'danger' in clase_prog else 'text-success' if 'success' in clase_prog else 'text-primary' }}">
                        {{ r.cumplen_cumplimiento }}/{{ r.total_registros_mes }}
                      </div>
                      <div class="cultmet-kpi-sub">
                        {{ "%.2f"|format(r.pct_cumplimiento) }} %
                      </div>
                      <div class="cultmet-kpi-pill {{ clase_prog }}">
                        {% if r.meta_cumplimiento is not none %}
                          Meta: {{ "%.2f"|format(r.meta_cumplimiento) }} %
                        {% else %}
                          Sin meta
                        {% endif %}
                      </div>
                    </div>

                    <div class="cultmet-kpi-box">
                      <div class="cultmet-kpi-label">Cobertura</div>
                      <div class="cultmet-kpi-value {{ 'text-danger' if 'danger' in clase_cov else 'text-success' if 'success' in clase_cov else 'text-primary' }}">
                        {{ r.cumplen_cobertura }}/{{ r.total_registros_mes }}
                      </div>
                      <div class="cultmet-kpi-sub">
                        {{ "%.2f"|format(r.pct_cobertura) }} %
                      </div>
                      <div class="cultmet-kpi-pill {{ clase_cov }}">
                        {% if r.meta_cobertura is not none %}
                          Meta: {{ "%.2f"|format(r.meta_cobertura) }} %
                        {% else %}
                          Sin meta
                        {% endif %}
                      </div>
                    </div>

                    <div class="cultmet-kpi-box cultmet-kpi-box-main">
                      <div class="cultmet-kpi-label">Evaluaciones Eficaces</div>
                      <div class="cultmet-kpi-value {{ 'text-danger' if 'danger' in clase_efi else 'text-success' if 'success' in clase_efi else 'text-primary' }}">
                        {{ r.cumplen_eficacia }}/{{ r.total_registros_mes }}
                      </div>
                      <div class="cultmet-kpi-sub">
                        {{ "%.2f"|format(r.pct_eficacia) }} %
                      </div>
                      <div class="cultmet-kpi-pill {{ clase_efi }}">
                        {% if r.meta_eficacia is not none %}
                          Meta: {{ "%.2f"|format(r.meta_eficacia) }} %
                        {% else %}
                          Sin meta
                        {% endif %}
                      </div>
                    </div>
                  </div>
                </div>

              </div>

            {% endfor %}
          </div>
        {% endif %}
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

      .cultmet-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .cultmet-header-card{
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

      .cultmet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .cultmet-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }

      .cultmet-header-overlay::before{
        content:"🎓";
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

      .cultmet-header-text{
        max-width:1000px;
        min-width:0;
      }

      .cultmet-header-text::before{
        content:"SGSI · Métricas de Cultura y Concienciación";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .cultmet-title{
        color:#ffffff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
        overflow-wrap:break-word;
      }

      .cultmet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        overflow-wrap:break-word;
      }

      .cultmet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .cultmet-btn-main{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .cultmet-btn-main:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      .cultmet-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .cultmet-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
        overflow-wrap:break-word;
      }

      .form-control,
      .form-select,
      textarea.form-control{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
      }

      .form-control:focus,
      .form-select:focus,
      textarea.form-control:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .cultmet-resumen-textarea{
        min-height:220px;
        line-height:1.45;
        resize:vertical;
        padding:14px 16px;
        background:#f8fafc;
        white-space:pre-wrap;
      }

      .cultmet-resumen-textarea[readonly]{
        background:#f8fafc;
        color:#374151;
        cursor:default;
      }

      .cultmet-edit-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin-top:8px;
      }

      .cultmet-empty-box{
        background:rgba(248,249,250,.96);
        border:1px dashed #ced4da;
        border-radius:14px;
        padding:22px;
        text-align:center;
        color:#4b5563;
        font-weight:700;
      }

      .cultmet-summary-card,
      .cultmet-metric-card{
        background:#ffffff;
        border:1px solid rgba(59,130,246,.14);
        border-radius:16px;
        padding:16px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
        height:100%;
        min-width:0;
        width:100%;
        max-width:100%;
        overflow:hidden;
      }

      .cultmet-summary-card{
        text-align:center;
      }

      .cultmet-summary-label,
      .cultmet-mini-label,
      .cultmet-kpi-label,
      .cultmet-period-label{
        font-size:.80rem;
        color:#475569;
        font-weight:900;
        line-height:1.15;
        overflow-wrap:break-word;
        word-break:normal;
      }

      .cultmet-summary-value,
      .cultmet-mini-value,
      .cultmet-kpi-value{
        color:#0b4a8f;
        font-weight:950;
        line-height:1;
        overflow-wrap:break-word;
        word-break:normal;
      }

      .cultmet-summary-value{
        font-size:1.50rem;
      }

      .cultmet-metric-grid{
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(420px,1fr));
        gap:18px;
        width:100%;
        max-width:100%;
        overflow:hidden;
      }

      .cultmet-metric-top{
        display:flex;
        justify-content:space-between;
        align-items:flex-start;
        gap:12px;
        margin-bottom:14px;
        padding-bottom:12px;
        border-bottom:1px solid rgba(59,130,246,.14);
        min-width:0;
      }

      .cultmet-period-value{
        font-size:1.15rem;
        color:#101827;
        font-weight:950;
        line-height:1.1;
        overflow-wrap:break-word;
      }

      .cultmet-period-badge{
        background:#eef5ff;
        color:#0b4a8f;
        border:1px solid #cfe0ff;
        border-radius:999px;
        padding:7px 12px;
        font-size:.82rem;
        font-weight:900;
        white-space:nowrap;
        flex-shrink:0;
      }

      .cultmet-metric-section{
        margin-top:14px;
        min-width:0;
      }

      .cultmet-metric-section-title{
        font-size:.92rem;
        font-weight:950;
        color:#334155;
        margin-bottom:10px;
        overflow-wrap:break-word;
      }

      .cultmet-mini-grid{
        display:grid;
        grid-template-columns:repeat(4,minmax(0,1fr));
        gap:10px;
        width:100%;
        max-width:100%;
      }

      .cultmet-mini-grid.two-cols{
        grid-template-columns:repeat(2,minmax(0,1fr));
      }

      .cultmet-mini-box{
        background:#f8fbff;
        border:1px solid #e2ebf5;
        border-radius:14px;
        padding:12px;
        min-height:88px;
        min-width:0;
        width:100%;
        max-width:100%;
        overflow:hidden;
      }

      .cultmet-mini-value{
        font-size:1.15rem;
        color:#101827;
      }

      /* =========================
         KPI CORREGIDO
         ========================= */
      .cultmet-kpi-grid{
        display:grid;
        grid-template-columns:repeat(3,minmax(0,1fr));
        gap:12px;
        margin-top:4px;
        width:100%;
        max-width:100%;
        overflow:hidden;
      }

      .cultmet-kpi-box{
        background:linear-gradient(180deg,#ffffff 0%,#f9fbff 100%);
        border:1px solid #dbe5ef;
        border-radius:16px;
        padding:8px 7px;
        text-align:center;
        min-height:170px;
        display:flex;
        flex-direction:column;
        justify-content:center;
        min-width:0;
        width:100%;
        max-width:100%;
        overflow:hidden;
      }

      .cultmet-kpi-box-main{
        background:linear-gradient(180deg,#f8fbff 0%,#eef5ff 100%);
        border:1px solid #bfd6ff;
        grid-column:span 1;
        min-width:0;
        width:100%;
        max-width:100%;
      }

      .cultmet-kpi-value{
        font-size:1.65rem;
        margin-bottom:8px;
      }

      .cultmet-kpi-sub{
        font-size:.82rem;
        color:#4b5563;
        font-weight:800;
        margin-bottom:10px;
        overflow-wrap:break-word;
      }

      .cultmet-kpi-pill{
        display:inline-flex;
        justify-content:center;
        align-items:center;
        align-self:center;
        border-radius:999px;
        padding:6px 12px;
        font-size:.68rem;
        font-weight:900;
        white-space:normal;
        overflow-wrap:break-word;
        word-break:normal;
        text-align:center;
        max-width:100%;
        min-width:0;
      }

      .cultmet-pill-success{
        background:#d1fae5;
        color:#065f46;
        border:1px solid #a7f3d0;
      }

      .cultmet-pill-danger{
        background:#fee2e2;
        color:#991b1b;
        border:1px solid #fecaca;
      }

      .cultmet-pill-neutral{
        background:#e5e7eb;
        color:#374151;
        border:1px solid #d1d5db;
      }

      h3{
        color:#ffffff;
        margin:0;
      }

      @media (max-width:1200px){
        .cultmet-kpi-grid{
          grid-template-columns:1fr;
        }
      }

      @media (max-width:992px){
        .cultmet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .cultmet-title{
          font-size:1.20rem;
        }

        .cultmet-subtitle{
          font-size:.68rem;
        }

        .cultmet-metric-grid,
        .cultmet-mini-grid,
        .cultmet-mini-grid.two-cols{
          grid-template-columns:1fr;
        }

        .cultmet-period-badge{
          font-size:.74rem;
          padding:6px 10px;
        }

        .cultmet-kpi-value{
          font-size:1.35rem;
        }
      }

      @media (max-width:768px){
        .cultmet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .cultmet-header-overlay::before{
          margin:0;
        }

        .cultmet-title,
        .cultmet-subtitle{
          text-align:center;
        }

        .cultmet-header-actions .btn{
          width:100%;
        }
      }
    </style>

    {% if not read_only %}
    <script>
      (function() {
        const box = document.getElementById("resumenCulturaBox");
        const btnEditar = document.getElementById("btnEditarResumenCultura");
        const btnCancelar = document.getElementById("btnCancelarResumenCultura");
        const btnGuardar = document.getElementById("btnGuardarResumenCultura");

        if (!box || !btnEditar || !btnCancelar || !btnGuardar) return;

        const valorOriginal = box.value;

        btnEditar.addEventListener("click", function() {
          box.removeAttribute("readonly");
          box.focus();
          btnEditar.classList.add("d-none");
          btnCancelar.classList.remove("d-none");
          btnGuardar.classList.remove("d-none");
        });

        btnCancelar.addEventListener("click", function() {
          box.value = valorOriginal;
          box.setAttribute("readonly", "readonly");
          btnEditar.classList.remove("d-none");
          btnCancelar.classList.add("d-none");
          btnGuardar.classList.add("d-none");
        });
      })();
    </script>
    {% endif %}
    """,
    year_selected=year_selected,
    month_selected=month_selected,
    year_options=year_options,
    registros=registros,
    config_cultura=config_cultura,
    total_periodos=total_periodos,
    total_inducciones=total_inducciones,
    total_reinducciones=total_reinducciones,
    total_cumplen_cumplimiento=total_cumplen_cumplimiento,
    total_cumplen_cobertura=total_cumplen_cobertura,
    total_cumplen_eficacia=total_cumplen_eficacia,
    analisis_cultura_resumen=analisis_cultura_resumen,
    year_ai=year_ai,
    read_only=read_only
    )

    return render_template_string(BASE, content=Markup(inner))

@app.route("/metricas/cultura/analisis/<int:id>", methods=["GET"])
@login_required
def metricas_cultura_ver_analisis(id):
    registro = MetricasCultura.query.get_or_404(id)

    inner = render_template_string("""
    <div class="container mt-4">
      <a href="{{ url_for('metricas_cultura_matriz') }}" class="btn btn-secondary mb-3 rounded-pill">
        ⬅️ Volver al Módulo de la Métrica de Cultura
      </a>

      <div class="card shadow-sm border-0 rounded-4">
        <div class="card-body">
          <h4 class="card-title mb-3">
            Análisis mensual de la métrica – {{ registro.anio }}-{{ "%02d"|format(registro.mes) }}
          </h4>

          <p>
            <strong>Cantidad personas contratadas:</strong> {{ registro.personas_contratadas }}<br>
            <strong>Meta alcanzada de formación:</strong> {{ "%.2f"|format(registro.meta_formacion or 0) }} %<br>
            <strong>Meta alcanzada de planeación:</strong> {{ "%.2f"|format(registro.meta_actividades or 0) }} %<br>
            <strong>Resultado meta / objetivo general:</strong> {{ "%.2f"|format(registro.resultado_meta_general or 0) }} %
          </p>

          <hr>

          <h5>Texto completo del análisis mensual</h5>
          <div class="mt-3 p-3 border rounded shadow-sm"
                 style="white-space: pre-wrap; font-family: 'Courier New', monospace; font-size: 14px; line-height: 1.45;">
              {% if registro.analisis_mensual %}
                {{ registro.analisis_mensual.replace("\\n", "\n") | safe }}
              {% else %}
                <span class="text-muted">Sin análisis registrado para este mes.</span>
              {% endif %}
           </div>

          <div class="mt-4 d-flex justify-content-end gap-2">
            <a href="{{ url_for('metricas_cultura_editar_analisis', id=registro.id) }}"
               class="btn btn-outline-primary rounded-pill">
              ✏️ Editar análisis
            </a>
            <a href="{{ url_for('metricas_cultura_matriz') }}"
               class="btn btn-secondary rounded-pill">
              Cerrar
            </a>
          </div>
        </div>
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
      .card {
        background: rgba(255, 255, 255, 0.92) !important;
        border-radius: 18px;
        backdrop-filter: blur(5px);
      }
      h3, h4, h5 { color: #003366 !important; }
    </style>
    """, registro=registro)

    return render_template_string(BASE, content=Markup(inner))


# ===============================
# Métrica de Cultura - Editar análisis mensual
# ===============================

@app.route("/metricas/cultura/<int:id>/analisis", methods=["GET", "POST"])
@login_required
def metricas_cultura_editar_analisis(id):
    registro = MetricasCultura.query.get_or_404(id)

    if request.method == "POST":
        nuevo_texto = (request.form.get("analisis_mensual") or "").strip()
        registro.analisis_mensual = nuevo_texto
        db.session.commit()
        flash("Análisis mensual de la métrica actualizado correctamente.", "success")
        return redirect(url_for("metricas_cultura_matriz"))

    inner = render_template_string("""
    <div class="container mt-4">
      <a href="{{ url_for('metricas_cultura_matriz') }}" class="btn btn-secondary mb-3 rounded-pill">
        ⬅️ Volver a la Matriz de la Métrica de Cultura
      </a>

      <div class="card shadow-sm border-0 rounded-4">
        <div class="card-body">
          <h4 class="card-title mb-3">📝 Análisis mensual de la métrica de cultura</h4>

          <p class="text-muted mb-2">
            Año: <strong>{{ registro.anio }}</strong> &nbsp;·&nbsp;
            Mes: <strong>{{ "%02d"|format(registro.mes) }}</strong>
          </p>

          <form method="post">
            <div class="mb-3">
              <label class="form-label">ANÁLISIS MENSUAL DE LA MÉTRICA</label>
              <textarea name="analisis_mensual" class="form-control" rows="8">{{ registro.analisis_mensual or '' }}</textarea>
            </div>

            <div class="d-flex justify-content-end gap-2">
              <a href="{{ url_for('metricas_cultura_matriz') }}"
                 class="btn btn-outline-secondary rounded-pill">
                Cancelar
              </a>
              <button type="submit" class="btn btn-success rounded-pill">
                💾 Guardar cambios
              </button>
            </div>
          </form>
        </div>
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
      .card {
        background: rgba(255, 255, 255, 0.92) !important;
        border-radius: 18px;
        backdrop-filter: blur(5px);
      }
    </style>
    """, registro=registro)

    return render_template_string(BASE, content=Markup(inner))

# ===============================
# Métrica de Mejora
# ===============================

@app.route('/metricas/mejora')
@login_required
def metricas_mejora_planes():
    user = User.query.get(session.get('user_id'))

    # permisos (mismo criterio de tu menú)
    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Métricas"):
            flash("No tiene permiso para ingresar al módulo de métricas.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    # Normalizadores (por si vienen vacíos o con espacios)
    estado = func.lower(func.trim(MejoraPlanRegistro.estado_actividad))
    eficacia = func.lower(func.trim(MejoraPlanRegistro.eficacia))
    tipo = func.lower(func.trim(MejoraPlanRegistro.tipo_accion))

    # ---------
    # Conteos base
    # ---------
    total = db.session.query(func.count(MejoraPlanRegistro.id)).scalar() or 0

    abiertos = db.session.query(func.count(MejoraPlanRegistro.id)).filter(estado == "abierto").scalar() or 0
    cerrados = db.session.query(func.count(MejoraPlanRegistro.id)).filter(estado == "cerrado").scalar() or 0

    # Eficacia (recomendado: contar solo cerrados)
    eficaces = db.session.query(func.count(MejoraPlanRegistro.id)).filter(estado == "cerrado", eficacia == "sí").scalar() or 0
    no_eficaces = db.session.query(func.count(MejoraPlanRegistro.id)).filter(estado == "cerrado", eficacia == "no").scalar() or 0
    sin_eficacia = db.session.query(func.count(MejoraPlanRegistro.id)).filter(
        estado == "cerrado",
        (MejoraPlanRegistro.eficacia == None) | (func.trim(MejoraPlanRegistro.eficacia) == "")
    ).scalar() or 0

    # Tipo de acción (sobre todo el universo)
    correctivos = db.session.query(func.count(MejoraPlanRegistro.id)).filter(tipo == "correctiva").scalar() or 0
    mejoras = db.session.query(func.count(MejoraPlanRegistro.id)).filter(tipo == "mejora").scalar() or 0
    sin_tipo = db.session.query(func.count(MejoraPlanRegistro.id)).filter(
        (MejoraPlanRegistro.tipo_accion == None) | (func.trim(MejoraPlanRegistro.tipo_accion) == "")
    ).scalar() or 0

    # % de eficacia (solo cerrados con eficacia definida)
    cerrados_con_eficacia = (eficaces + no_eficaces)
    pct_eficacia = round((eficaces / cerrados_con_eficacia) * 100, 2) if cerrados_con_eficacia else 0.0

    html = render_template_string("""
    <div class="mejmet-shell">

      <!-- CABECERA -->
      <div class="mejmet-header-card">
        <div class="mejmet-header-overlay">
          <div class="mejmet-header-text">
            <h3 class="mejmet-title m-0">️Métricas – Planes de Mejora</h3>
            <div class="mejmet-subtitle">
              Seguimiento del estado, eficacia y tipología de los planes de mejora
              registrados en el sistema de gestión.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="mejmet-header-actions">
        
      </div>

      <div class="row g-3">

        <!-- KPI TOTAL -->
        <div class="col-lg-4 col-md-6">
          <div class="mejmet-kpi-card text-center">
            <div class="fw-bold">Total planes</div>
            <div class="mejmet-kpi">{{ total }}</div>
          </div>
        </div>

        <!-- KPI ESTADO -->
        <div class="col-lg-4 col-md-6">
          <div class="mejmet-kpi-card text-center">
            <div class="fw-bold">Abiertos</div>
            <div class="mejmet-kpi text-warning">{{ abiertos }}</div>
            <div class="text-muted small">Cerrados: {{ cerrados }}</div>
          </div>
        </div>

        <!-- KPI EFICACIA -->
        <div class="col-lg-4 col-md-12">
          <div class="mejmet-kpi-card text-center">
            <div class="fw-bold">Eficacia (solo cerrados)</div>

            <div class="d-flex justify-content-center gap-4 mt-2 flex-wrap">

              <div>
                <div class="h2 mb-0 text-success">{{ eficaces }}</div>
                <div class="small text-muted">Eficaces</div>
              </div>

              <div>
                <div class="h2 mb-0 text-danger">{{ no_eficaces }}</div>
                <div class="small text-muted">No eficaces</div>
              </div>

              <div>
                <div class="h2 mb-0">{{ sin_eficacia }}</div>
                <div class="small text-muted">Sin evaluar</div>
              </div>

            </div>

            <div class="mt-2 text-muted small">
              % eficacia: <b>{{ pct_eficacia }}%</b>
              (sobre cerrados con evaluación)
            </div>

          </div>
        </div>

        <!-- TIPO DE ACCIÓN -->
        <div class="col-12">

          <div class="mejmet-card p-4">

            <div class="mejmet-section-title">
              Tipo de acción (universo total)
            </div>

            <div class="row g-3">

              <div class="col-md-4 text-center">
                <div class="h2 mb-0 text-primary">{{ correctivos }}</div>
                <div class="small text-muted">Correctivos</div>
              </div>

              <div class="col-md-4 text-center">
                <div class="h2 mb-0 text-success">{{ mejoras }}</div>
                <div class="small text-muted">Mejora</div>
              </div>

              <div class="col-md-4 text-center">
                <div class="h2 mb-0">{{ sin_tipo }}</div>
                <div class="small text-muted">Sin tipo</div>
              </div>

            </div>

            <hr>

            <div class="d-flex justify-content-center">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('mejora_matriz') }}"
                 onclick="showLoader()">
                Ver matriz de planes
              </a>
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

      .mejmet-shell{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .mejmet-header-card{
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

      .mejmet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .mejmet-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }

      .mejmet-header-overlay::before{
        content:"📈";
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

      .mejmet-header-text{
        max-width:1000px;
        min-width:0;
      }

      .mejmet-header-text::before{
        content:"SGSI · Métricas de Mejora Continua";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .mejmet-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }

      .mejmet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }

      .mejmet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .mejmet-btn-main{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .mejmet-btn-main:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      .mejmet-kpi-card{
        background:#ffffff;
        border:1px solid rgba(59,130,246,.14);
        border-radius:16px;
        padding:18px 16px;
        text-align:center;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
        height:100%;
        min-width:0;
        width:100%;
        max-width:100%;
        overflow:hidden;
      }

      .mejmet-kpi-label{
        font-size:.80rem;
        color:#475569;
        font-weight:900;
        line-height:1.15;
        margin-bottom:8px;
        overflow-wrap:break-word;
      }

      .mejmet-kpi{
        color:#0b4a8f;
        font-weight:950;
        line-height:1;
        font-size:1.70rem;
        overflow-wrap:break-word;
      }

      .mejmet-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .mejmet-card .card-body{
        padding:22px;
      }

      .mejmet-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
        overflow-wrap:break-word;
      }

      .form-control,
      .form-select{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
      }

      .form-control:focus,
      .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .mejmet-soft-box{
        background:#f8fbff;
        border:1px solid #e2ebf5;
        border-radius:14px;
        padding:14px 16px;
        min-width:0;
        max-width:100%;
        overflow:hidden;
        overflow-wrap:break-word;
      }

      h3{
        color:#ffffff;
        margin:0;
      }

      @media (max-width:992px){
        .mejmet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .mejmet-title{
          font-size:1.20rem;
        }

        .mejmet-subtitle{
          font-size:.68rem;
        }

        .mejmet-card .card-body{
          padding:16px;
        }

        .mejmet-kpi{
          font-size:1.45rem;
        }
      }

      @media (max-width:768px){
        .mejmet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .mejmet-header-overlay::before{
          margin:0;
        }

        .mejmet-title,
        .mejmet-subtitle{
          text-align:center;
        }

        .mejmet-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """,
    total=total,
    abiertos=abiertos,
    cerrados=cerrados,
    eficaces=eficaces,
    no_eficaces=no_eficaces,
    sin_eficacia=sin_eficacia,
    pct_eficacia=pct_eficacia,
    correctivos=correctivos,
    mejoras=mejoras,
    sin_tipo=sin_tipo
    )

    return render_template_string(BASE, content=Markup(html))


# ==========================================================================================================================================
#                                                               Fin Módulo Métricas
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                               Módulo de Plan de Acción del SGSI
# ==========================================================================================================================================

# =========================
# ENTRADA DIRECTA — Plan de Acción del SGSI
# =========================
@app.route('/mejora_menu')
@login_required
def mejora_menu():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Planes de acción del SGSI"):
        flash("No tiene permiso para acceder a los planes de acción del SGSI (Mejora).", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('planes_accion_dashboard'))


# =========================
# EVIDENCIA — Descargar
# =========================
@app.route('/mejora/evidencia/<int:evi_id>')
@login_required
def mejora_evidencia_download(evi_id):
    ev = MejoraPlanEvidencia.query.get_or_404(evi_id)
    upload_dir = get_upload_mejora_dir()
    return send_from_directory(
        directory=upload_dir,
        path=ev.filename,
        as_attachment=True,
        download_name=ev.original_name,
        mimetype=ev.mime or 'application/pdf'
    )


# =========================
# EVIDENCIA — RAW
# =========================
@app.route('/mejora/evidencia/<int:evi_id>/raw')
@login_required
def mejora_evidencia_raw(evi_id):
    ev = MejoraPlanEvidencia.query.get_or_404(evi_id)
    fullpath = os.path.join(get_upload_mejora_dir(), ev.filename)

    if not os.path.isfile(fullpath):
        abort(404)

    resp = send_file(
        fullpath,
        mimetype=ev.mime or 'application/pdf',
        download_name=ev.original_name,
        as_attachment=False
    )
    resp.headers['Content-Disposition'] = f'inline; filename="{ev.original_name}"'
    return resp


# =========================
# EVIDENCIA — VISOR
# =========================
@app.route('/mejora/evidencia/<int:evi_id>/ver')
@login_required
def mejora_evidencia_view(evi_id):
    ev = MejoraPlanEvidencia.query.get_or_404(evi_id)

    fullpath = os.path.join(get_upload_mejora_dir(), ev.filename)
    if not os.path.isfile(fullpath):
        abort(404)

    next_ep = request.args.get('next')
    reg_id = request.args.get('reg_id', type=int)

    if next_ep == 'mejora_detalle' and reg_id:
        back_url = url_for('mejora_detalle', id=reg_id)
        back_label = '⬅ Volver al Detalle'
    elif next_ep == 'mejora_edit' and reg_id:
        back_url = url_for('mejora_edit', id=reg_id)
        back_label = '⬅ Volver a Edición'
    else:
        back_url = url_for('mejora_matriz')
        back_label = '⬅ Volver a la Matriz'

    html = """
    <div class="mejevi-shell">
      <div class="mejevi-header-actions">
        <a href="{{ back_url }}" class="btn rounded-pill px-4 py-2 fw-bold mejevi-back-btn">
          {{ back_label }}
        </a>
        <div class="mejevi-file-pill" title="{{ original_name }}">📎 {{ original_name }}</div>
      </div>

      <div class="mejevi-card">
        <div class="mejevi-card-body">
          <iframe src="{{ url_for('mejora_evidencia_raw', evi_id=evi_id) }}" class="mejevi-frame"></iframe>
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

      .mejevi-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 30px auto;
      }

      .mejevi-header-actions{
        display:flex;
        justify-content:center;
        align-items:center;
        gap:12px;
        flex-wrap:wrap;
        margin-bottom:16px;
      }

      .mejevi-back-btn{
        background:#ffffff;
        color:#000000;
        border:2px solid #ffffff;
        box-shadow:0 4px 10px rgba(0,0,0,.10);
      }

      .mejevi-back-btn:hover{
        background:#f3f4f6;
        color:#000000;
        border-color:#f3f4f6;
      }

      .mejevi-file-pill{
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

      .mejevi-card{
        background:rgba(248,252,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(6px);
        box-shadow:0 10px 24px rgba(0,0,0,.18);
        overflow:hidden;
      }

      .mejevi-card-body{
        padding:16px;
      }

      .mejevi-frame{
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
            html,
            back_url=back_url,
            back_label=back_label,
            evi_id=evi_id,
            original_name=ev.original_name or ev.filename
        ))
    )


# =========================
# EVIDENCIA — Eliminar
# =========================
@app.route('/mejora/evidencia/<int:evi_id>/delete', methods=['POST'])
@login_required
def mejora_evidencia_delete(evi_id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (user.role != 'admin' and not verificar_permiso(user, "Planes de acción del SGSI")):
        flash("No tiene permiso para eliminar evidencias.", "danger")
        return redirect(url_for('mejora_matriz'))

    ev = MejoraPlanEvidencia.query.get_or_404(evi_id)
    plan_id = ev.plan_id

    try:
        path = os.path.join(get_upload_mejora_dir(), ev.filename)
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

    db.session.delete(ev)
    db.session.commit()
    flash("Evidencia eliminada correctamente.", "success")
    return redirect(url_for('mejora_edit', id=plan_id))


# =========================
# AGREGAR PLAN
# =========================
@app.route('/mejora/new', methods=['GET','POST'])
@login_required
def mejora_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros de planes de acción.", "danger")
        return redirect(url_for('mejora_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Planes de acción del SGSI"):
        flash("No tiene permiso para agregar registros de planes de acción del SGSI.", "danger")
        return redirect(url_for('mejora_matriz'))

    if request.method == 'POST':
        it = MejoraPlanRegistro(
            fecha                     = request.form.get('fecha') or '',
            descripcion_incumplimiento= (request.form.get('descripcion_incumplimiento') or '').strip(),
            causa                     = (request.form.get('causa') or '').strip(),
            tipo_accion               = request.form.get('tipo_accion') or '',
            plan_accion               = (request.form.get('plan_accion') or '').strip(),
            termino_ejecucion         = request.form.get('termino_ejecucion') or '',
            fecha_ejecucion_propuesta = request.form.get('fecha_ejecucion_propuesta') or '',
            responsable               = (request.form.get('responsable') or '').strip(),
            estado_actividad          = request.form.get('estado_actividad') or '',
            fecha_cierre              = request.form.get('fecha_cierre') or '',
            eficacia                  = request.form.get('eficacia') or '',
            observacion_eficacia      = (request.form.get('observacion_eficacia') or '').strip(),
        )

        db.session.add(it)
        db.session.flush()

        files = request.files.getlist('evidencias')
        for f in files:
            if not f or not f.filename:
                continue
            if not is_allowed_pdf(f.filename):
                flash(f"Archivo no permitido (solo PDF): {f.filename}", "danger")
                continue

            store_name = unique_store_name(f.filename)
            upload_dir = get_upload_mejora_dir()
            path = os.path.join(upload_dir, store_name)
            f.save(path)

            ev = MejoraPlanEvidencia(
                plan=it,
                filename=store_name,
                original_name=secure_filename(f.filename),
                mime='application/pdf',
                size=os.path.getsize(path)
            )
            db.session.add(ev)

        db.session.commit()
        flash("Plan de acción guardado.", "success")
        return redirect(url_for('mejora_matriz'))

    html = """
    <div class="mejadd-shell">

      <div class="mejadd-header-card">
        <div class="mejadd-header-overlay">
          <div class="mejadd-header-text">
            <h3 class="mejadd-title m-0">Agregar Plan de Acción</h3>
            <div class="mejadd-subtitle">
              Registra acciones correctivas o de mejora bajo el ciclo PHVA: planear, hacer, verificar y actuar
            </div>
          </div>
        </div>
      </div>

      <div class="mejadd-header-actions">
        <a href="{{ url_for('mejora_matriz') }}"
           class="btn rounded-pill px-5 fw-bold mejadd-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="mejadd-card">
        <div class="mejadd-card-body">
          <form method="post" enctype="multipart/form-data">
            <div class="row g-3">

              <div class="col-12">
                <div class="mejadd-section-title">Planear</div>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha</label>
                <input type="date" name="fecha" class="form-control">
              </div>

              <div class="col-md-9">
                <label class="form-label">Descripción o incumplimiento</label>
                <textarea name="descripcion_incumplimiento" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Causa</label>
                <textarea name="causa" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Tipo de acción</label>
                <select name="tipo_accion" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Correctiva">Correctiva</option>
                  <option value="Mejora">Mejora</option>
                </select>
              </div>

              <div class="col-md-12">
                <label class="form-label">Plan de acción</label>
                <textarea name="plan_accion" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-12">
                <div class="mejadd-section-title">Hacer</div>
              </div>

              <div class="col-md-3">
                <label class="form-label">Término de ejecución</label>
                <select name="termino_ejecucion" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Corto plazo">Corto plazo</option>
                  <option value="Mediano plazo">Mediano plazo</option>
                  <option value="Largo plazo">Largo plazo</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de ejecución propuesta</label>
                <input type="date" name="fecha_ejecucion_propuesta" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Responsable</label>
                <input name="responsable" class="form-control">
              </div>

              <div class="col-12">
                <div class="mejadd-section-title">Verificar</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Estado de la actividad</label>
                <select name="estado_actividad" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Abierto">Abierto</option>
                  <option value="Cerrado">Cerrado</option>
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha de cierre</label>
                <input type="date" name="fecha_cierre" class="form-control">
              </div>

              <div class="col-md-4">
                <label class="form-label">Evidencias PDF (puede adjuntar varios)</label>
                <input type="file"
                       id="evidencias"
                       name="evidencias"
                       accept=".pdf"
                       multiple
                       class="form-control"
                       onchange="acumularEvidencias(this)">
                <small class="text-muted">
                  Puedes seleccionar varios a la vez o ir agregando en varias rondas.
                </small>
                <div id="lista_evidencias_nuevas" class="mt-2"></div>
              </div>

              <div class="col-12">
                <div class="mejadd-section-title">Actuar</div>
              </div>

              <div class="col-md-3">
                <label class="form-label">Eficacia (Sí / No)</label>
                <select name="eficacia" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Sí">Sí</option>
                  <option value="No">No</option>
                </select>
              </div>

              <div class="col-md-9">
                <label class="form-label">Observación de eficacia</label>
                <textarea name="observacion_eficacia" class="form-control" rows="2"></textarea>
              </div>

            </div>

            <div class="mejadd-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">Guardar</button>
              <a class="btn rounded-pill px-4 fw-bold mejadd-cancel-btn"
                 href="{{ url_for('mejora_matriz') }}"
                 onclick="showLoader()">Cancelar</a>
            </div>
          </form>
        </div>
      </div>
    </div>

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

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .mejadd-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }

      .mejadd-header-card{
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

      .mejadd-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .mejadd-header-overlay{
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

      .mejadd-header-overlay::before{
        content:"➕";
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

      .mejadd-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .mejadd-header-text::before{
        content:"SGSI · Mejora Continua";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .mejadd-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .mejadd-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .mejadd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .mejadd-header-actions .btn,
      .mejadd-back-btn,
      .mejadd-cancel-btn,
      .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .mejadd-back-btn,
      .mejadd-cancel-btn{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }

      .mejadd-back-btn:hover,
      .mejadd-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }

      .mejadd-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .mejadd-card-body,
      .mejadd-card .card-body{
        padding:22px;
      }

      .mejadd-section-title,
      .card h5,
      .card h6{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
      }

      .mejadd-section-title{
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }

      .mejadd-card .form-label,
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

      .mejadd-card .form-control,
      .mejadd-card .form-select,
      .form-control,
      .form-select{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }

      .mejadd-card textarea.form-control,
      textarea.form-control{
        min-height:90px;
      }

      .mejadd-card .form-control:focus,
      .mejadd-card .form-select:focus,
      .form-control:focus,
      .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }

      .mejadd-bottom-actions{
        display:flex;
        justify-content:center;
        gap:12px;
        margin-top:26px;
        flex-wrap:wrap;
        width:100%;
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      @media (max-width:992px){
        .mejadd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .mejadd-header-card{
          min-height:88px;
        }

        .mejadd-title{
          font-size:1.20rem;
        }

        .mejadd-subtitle{
          font-size:.68rem;
        }

        .mejadd-card-body,
        .mejadd-card .card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .mejadd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .mejadd-header-overlay::before{
          margin:0;
        }

        .mejadd-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .mejadd-title,
        .mejadd-subtitle{
          text-align:center;
        }

        .mejadd-header-actions .btn,
        .mejadd-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html)
    return render_template_string(BASE, content=Markup(inner))


# =========================
# MATRIZ PLAN DE MEJORA
# =========================
@app.route('/mejora_matriz', methods=['GET'])
@login_required
def mejora_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Planes de acción del SGSI"):
            flash("No tiene permiso para ver la Matriz de planes de acción del SGSI.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    filtro_tipo_accion = (request.args.get('tipo_accion') or '').strip()
    filtro_estado_actividad = (request.args.get('estado_actividad') or '').strip()
    filtro_eficacia = (request.args.get('eficacia') or '').strip()

    query = MejoraPlanRegistro.query.options(selectinload(MejoraPlanRegistro.evidencias))

    if filtro_tipo_accion:
        query = query.filter(MejoraPlanRegistro.tipo_accion == filtro_tipo_accion)

    if filtro_estado_actividad:
        query = query.filter(MejoraPlanRegistro.estado_actividad == filtro_estado_actividad)

    if filtro_eficacia:
        query = query.filter(MejoraPlanRegistro.eficacia == filtro_eficacia)

    items = query.order_by(MejoraPlanRegistro.id.desc()).all()

    opciones_tipo_accion = [
        x[0] for x in db.session.query(MejoraPlanRegistro.tipo_accion)
        .filter(MejoraPlanRegistro.tipo_accion.isnot(None))
        .filter(MejoraPlanRegistro.tipo_accion != '')
        .distinct()
        .order_by(MejoraPlanRegistro.tipo_accion.asc())
        .all()
    ]

    opciones_estado_actividad = [
        x[0] for x in db.session.query(MejoraPlanRegistro.estado_actividad)
        .filter(MejoraPlanRegistro.estado_actividad.isnot(None))
        .filter(MejoraPlanRegistro.estado_actividad != '')
        .distinct()
        .order_by(MejoraPlanRegistro.estado_actividad.asc())
        .all()
    ]

    opciones_eficacia = [
        x[0] for x in db.session.query(MejoraPlanRegistro.eficacia)
        .filter(MejoraPlanRegistro.eficacia.isnot(None))
        .filter(MejoraPlanRegistro.eficacia != '')
        .distinct()
        .order_by(MejoraPlanRegistro.eficacia.asc())
        .all()
    ]

    total_filtrados = len(items)
    total_general = MejoraPlanRegistro.query.count()

    html = """
    <div class="mejmat-shell">

      <div class="mejmat-header-card">
        <div class="mejmat-header-overlay">
          <div class="mejmat-header-text">
            <h3 class="mejmat-title m-0">Planes de Acción del SGSI</h3>
            <div class="mejmat-subtitle">
              Visualización resumida de planes de acción del SGSI bajo el ciclo PHVA
            </div>
          </div>
        </div>
      </div>

      <div class="mejmat-header-actions">
        

        {% if not read_only %}
        <a href="{{ url_for('mejora_new') }}"
           class="btn btn-primary rounded-pill px-4 fw-bold"
           onclick="showLoader()">
          ➕ Agregar Registro
        </a>
        {% endif %}
      </div>

      <div class="mejmat-topbar-card">
        <div class="mejmat-topbar-title">Resumen de planes de acción</div>
        <div class="mejmat-topbar-subtitle">
          Total registros: <strong>{{ total_general }}</strong>
          &nbsp; | &nbsp;
          Mostrando: <strong>{{ total_filtrados }}</strong>
        </div>
      </div>

      <div class="mejmat-filter-card">
        <div class="mejmat-filter-head">Filtros de búsqueda</div>
        <div class="mejmat-filter-body">
          <form method="get" action="{{ url_for('mejora_matriz') }}">
            <div class="row g-2 align-items-end">

              <div class="col-md-4">
                <label class="form-label mejmat-label">Tipo de acción</label>
                <select name="tipo_accion" class="form-select form-select-sm mejmat-input-sm">
                  <option value="">Todos</option>
                  {% for op in opciones_tipo_accion %}
                    <option value="{{ op }}" {% if filtro_tipo_accion == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label mejmat-label">Estado de la actividad</label>
                <select name="estado_actividad" class="form-select form-select-sm mejmat-input-sm">
                  <option value="">Todos</option>
                  {% for op in opciones_estado_actividad %}
                    <option value="{{ op }}" {% if filtro_estado_actividad == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label mejmat-label">Eficacia</label>
                <select name="eficacia" class="form-select form-select-sm mejmat-input-sm">
                  <option value="">Todos</option>
                  {% for op in opciones_eficacia %}
                    <option value="{{ op }}" {% if filtro_eficacia == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-1">
                <div class="d-flex gap-2 mejmat-filter-actions flex-column">
                  <button type="submit" class="btn btn-primary btn-sm rounded-pill px-3 w-100 fw-bold">
                    Filtrar
                  </button>
                  <a href="{{ url_for('mejora_matriz') }}"
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

      <div class="mejmat-card">
        <div class="mejmat-card-body">
          <div class="table-responsive mejmat-table-wrap">
            <table class="table table-hover align-middle mejmat-table mb-0">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Descripción o incumplimiento</th>
                  <th>Tipo de acción</th>
                  <th>Responsable</th>
                  <th>Estado actividad</th>
                  <th>Eficacia</th>
                  <th class="mejmat-col-acciones">Acciones</th>
                </tr>
              </thead>

              <tbody>
                {% for it in items %}
                  <tr>
                    <td class="text-center">{{ it.fecha or '—' }}</td>
                    <td>{{ it.descripcion_incumplimiento or '—' }}</td>
                    <td class="text-center">{{ it.tipo_accion or '—' }}</td>
                    <td>{{ it.responsable or '—' }}</td>

                    <td class="text-center">
                      {% if it.estado_actividad == 'Abierto' %}
                        <span class="badge bg-primary">Abierto</span>
                      {% elif it.estado_actividad == 'Cerrado' %}
                        <span class="badge bg-success">Cerrado</span>
                      {% else %}
                        <span class="badge bg-secondary">{{ it.estado_actividad or '—' }}</span>
                      {% endif %}
                    </td>

                    <td class="text-center">
                      {% if it.eficacia == 'Sí' %}
                        <span class="badge bg-success">Sí</span>
                      {% elif it.eficacia == 'No' %}
                        <span class="badge bg-danger">No</span>
                      {% else %}
                        <span class="badge bg-secondary">{{ it.eficacia or '—' }}</span>
                      {% endif %}
                    </td>

                    <td class="text-center mejmat-col-acciones">
                      <div class="mejmat-actions-wrap">
                        <a href="{{ url_for('mejora_detalle', id=it.id) }}"
                           class="btn btn-info btn-sm rounded-pill mejmat-btn-action text-white fw-bold"
                           onclick="showLoader()">
                          Ver detalle
                        </a>

                        {% if not read_only %}
                          <a href="{{ url_for('mejora_edit', id=it.id) }}"
                             class="btn btn-warning btn-sm rounded-pill mejmat-btn-action fw-bold"
                             onclick="showLoader()">
                            Editar
                          </a>

                          <a href="{{ url_for('mejora_delete', id=it.id) }}"
                             class="btn btn-danger btn-sm rounded-pill mejmat-btn-action fw-bold"
                             onclick="return confirm('¿Eliminar este plan de acción?');">
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
                    <td colspan="7" class="text-center text-muted py-5">Sin registros</td>
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

      .mejmat-shell{
        width:96%;
        max-width:1650px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .mejmat-header-card{
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

      .mejmat-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .mejmat-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }

      .mejmat-header-overlay::before{
        content:"📈";
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

      .mejmat-header-text{
        max-width:1100px;
        min-width:0;
      }

      .mejmat-header-text::before{
        content:"SGSI · Matriz de Mejora Continua";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .mejmat-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }

      .mejmat-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }

      .mejmat-header-actions{
        display:flex;
        justify-content:center;
        align-items:center;
        flex-wrap:wrap;
        gap:10px;
        margin:10px 0 14px;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .mejmat-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .mejmat-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#cfd8e3;
      }

      .mejmat-topbar-card{
        background:rgba(255,255,255,.96);
        border-radius:16px;
        box-shadow:0 8px 18px rgba(15,23,42,.10);
        border:1px solid rgba(219,230,244,.9);
        padding:12px 16px;
        margin-bottom:12px;
        overflow:hidden;
      }

      .mejmat-topbar-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        overflow-wrap:break-word;
      }

      .mejmat-topbar-subtitle{
        font-size:.82rem;
        color:#475569;
        font-weight:700;
        overflow-wrap:break-word;
      }

      .mejmat-filter-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.16);
        border:1px solid rgba(219,230,244,.9);
        margin-bottom:14px;
        overflow:hidden;
      }

      .mejmat-filter-head{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#ffffff;
        font-weight:950;
        font-size:.85rem;
        padding:10px 14px;
      }

      .mejmat-filter-body{
        padding:12px 14px;
      }

      .mejmat-label{
        font-weight:900;
        font-size:.75rem;
        color:#334155;
        margin-bottom:4px;
      }

      .mejmat-input-sm{
        min-height:32px !important;
        height:32px !important;
        font-size:.75rem !important;
        border-radius:10px !important;
        padding:.2rem .55rem !important;
        border:1px solid #d9e3f0 !important;
        background:#f8fafc !important;
      }

      .mejmat-input-sm:focus{
        border-color:#3f86d6 !important;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff !important;
      }

      .mejmat-filter-actions .btn{
        font-size:.75rem;
        min-height:32px;
      }

      .mejmat-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .mejmat-card-body{
        padding:14px 16px;
      }

      .mejmat-table-wrap{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        width:100%;
        max-width:100%;
        border-radius:14px;
        border:1px solid #e2ebf5;
        background:#ffffff;
      }

      .mejmat-table{
        margin-bottom:0;
        min-width:1250px;
      }

      .mejmat-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:#eef5ff !important;
        color:#0b4a8f !important;
        font-weight:950;
        font-size:.80rem;
        border-bottom:1px solid #d7dee7 !important;
        padding:9px 8px;
        white-space:nowrap;
        vertical-align:middle;
      }

      .mejmat-table td{
        font-size:.82rem;
        padding:9px 8px;
        vertical-align:middle;
        color:#334155;
      }

      .mejmat-table tbody tr:hover{
        background:#f8fbff;
      }

      .mejmat-col-acciones{
        width:170px;
        min-width:170px;
        text-align:center;
      }

      .mejmat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:5px;
        align-items:center;
      }

      .mejmat-btn-action{
        font-size:.72rem;
        padding:4px 10px;
        min-width:115px;
        text-align:center;
        border-radius:10px !important;
        font-weight:900;
      }

      h3{
        color:#ffffff;
        margin:0;
      }

      @media (max-width:992px){
        .mejmat-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .mejmat-title{
          font-size:1.20rem;
        }

        .mejmat-subtitle{
          font-size:.68rem;
        }

        .mejmat-card-body{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .mejmat-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .mejmat-header-overlay::before{
          margin:0;
        }

        .mejmat-title,
        .mejmat-subtitle{
          text-align:center;
        }

        .mejmat-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        opciones_tipo_accion=opciones_tipo_accion,
        opciones_estado_actividad=opciones_estado_actividad,
        opciones_eficacia=opciones_eficacia,
        filtro_tipo_accion=filtro_tipo_accion,
        filtro_estado_actividad=filtro_estado_actividad,
        filtro_eficacia=filtro_eficacia,
        total_filtrados=total_filtrados,
        total_general=total_general
    )
    return render_template_string(BASE, content=Markup(inner))


# =========================
# DETALLE PLAN
# =========================
@app.route('/mejora/detalle/<int:id>')
@login_required
def mejora_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Planes de acción del SGSI"):
            flash("No tiene permiso para ver el detalle del plan de acción.", "danger")
            return redirect(url_for('mejora_matriz'))
        read_only = False

    it = (
        MejoraPlanRegistro.query
        .options(selectinload(MejoraPlanRegistro.evidencias))
        .get_or_404(id)
    )

    html = """
    <div class="mejdet-shell">

      <div class="mejdet-header-card">
        <div class="mejdet-header-overlay">
          <div class="mejdet-header-text">
            <h3 class="mejdet-title m-0">Detalle del Plan de Acción</h3>
            <div class="mejdet-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="mejdet-header-actions">
        <a href="{{ url_for('mejora_matriz') }}"
           class="btn rounded-pill px-4 fw-bold mejdet-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('mejora_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold"
             onclick="showLoader()">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="mejdet-card">
        <div class="mejdet-card-body">
          <div class="row g-3">

            <div class="col-12"><div class="mejdet-section-title">Planear</div></div>
            <div class="col-md-3"><div class="mejdet-block"><div class="mejdet-label">Fecha</div><div class="mejdet-value">{{ it.fecha or '—' }}</div></div></div>
            <div class="col-md-9"><div class="mejdet-block"><div class="mejdet-label">Descripción o incumplimiento</div><div class="mejdet-value">{{ it.descripcion_incumplimiento or '—' }}</div></div></div>
            <div class="col-md-6"><div class="mejdet-block"><div class="mejdet-label">Causa</div><div class="mejdet-value">{{ it.causa or '—' }}</div></div></div>
            <div class="col-md-3"><div class="mejdet-block"><div class="mejdet-label">Tipo de acción</div><div class="mejdet-value">{{ it.tipo_accion or '—' }}</div></div></div>
            <div class="col-md-12"><div class="mejdet-block"><div class="mejdet-label">Plan de acción</div><div class="mejdet-value">{{ it.plan_accion or '—' }}</div></div></div>

            <div class="col-12"><div class="mejdet-section-title">Hacer</div></div>
            <div class="col-md-3"><div class="mejdet-block"><div class="mejdet-label">Término de ejecución</div><div class="mejdet-value">{{ it.termino_ejecucion or '—' }}</div></div></div>
            <div class="col-md-3"><div class="mejdet-block"><div class="mejdet-label">Fecha de ejecución propuesta</div><div class="mejdet-value">{{ it.fecha_ejecucion_propuesta or '—' }}</div></div></div>
            <div class="col-md-3"><div class="mejdet-block"><div class="mejdet-label">Responsable</div><div class="mejdet-value">{{ it.responsable or '—' }}</div></div></div>

            <div class="col-12"><div class="mejdet-section-title">Verificar</div></div>
            <div class="col-md-4"><div class="mejdet-block"><div class="mejdet-label">Estado actividad</div><div class="mejdet-value">{{ it.estado_actividad or '—' }}</div></div></div>
            <div class="col-md-4"><div class="mejdet-block"><div class="mejdet-label">Fecha cierre</div><div class="mejdet-value">{{ it.fecha_cierre or '—' }}</div></div></div>

            <div class="col-12"><div class="mejdet-section-title">Actuar</div></div>
            <div class="col-md-3"><div class="mejdet-block"><div class="mejdet-label">Eficacia</div><div class="mejdet-value">{{ it.eficacia or '—' }}</div></div></div>
            <div class="col-md-9"><div class="mejdet-block"><div class="mejdet-label">Observación de eficacia</div><div class="mejdet-value">{{ it.observacion_eficacia or '—' }}</div></div></div>

            <div class="col-12"><div class="mejdet-section-title">Evidencias</div></div>
            <div class="col-12">
              {% if it.evidencias %}
                <div class="row g-3">
                  {% for ev in it.evidencias %}
                  <div class="col-md-6">
                    <div class="mejdet-file-card">
                      <div class="mejdet-file-meta">
                        <div class="mejdet-file-label">Archivo</div>
                        <a class="mejdet-file-name"
                           href="{{ url_for('mejora_evidencia_view', evi_id=ev.id, next='mejora_detalle', reg_id=it.id) }}">
                          {{ ev.original_name or ev.filename }}
                        </a>
                        <div class="mejdet-file-size">{{ (ev.size / 1024)|round(1) if ev.size else 0 }} KB</div>
                      </div>
                    </div>
                  </div>
                  {% endfor %}
                </div>
              {% else %}
                <div class="mejdet-empty-box">No hay evidencias cargadas.</div>
              {% endif %}
            </div>

          </div>

          <div class="mejdet-bottom-actions">
            <a href="{{ url_for('mejora_matriz') }}"
               class="btn rounded-pill px-4 fw-bold mejdet-cancel-btn"
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

      .mejdet-shell{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .mejdet-header-card{
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

      .mejdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .mejdet-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }

      .mejdet-header-overlay::before{
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

      .mejdet-header-text{
        max-width:1100px;
        min-width:0;
      }

      .mejdet-header-text::before{
        content:"SGSI · Detalle de Mejora";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .mejdet-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }

      .mejdet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }

      .mejdet-header-actions{
        display:flex;
        justify-content:center;
        gap:12px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .mejdet-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .mejdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      .mejdet-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .mejdet-card-body{
        padding:22px;
      }

      .mejdet-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:10px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
        overflow-wrap:break-word;
      }

      .mejdet-block{
        background:#f8fbff!important;
        border:1px solid #e2ebf5!important;
        border-radius:14px!important;
        box-shadow:0 4px 10px rgba(0,0,0,.05);
        padding:14px 16px;
        margin-bottom:12px;
        min-width:0;
        overflow:hidden;
      }

      .mejdet-label{
        font-weight:900;
        color:#334155;
        margin-bottom:4px;
        font-size:.85rem;
      }

      .mejdet-value{
        color:#475569;
        white-space:pre-wrap;
        word-break:break-word;
        font-size:.86rem;
      }

      .mejdet-file-card{
        background:#f8fbff;
        border:1px solid #e2ebf5;
        border-radius:14px;
        padding:12px 14px;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
        flex-wrap:wrap;
      }

      .mejdet-file-meta{
        min-width:0;
        flex:1;
      }

      .mejdet-file-label{
        font-size:.75rem;
        color:#475569;
        font-weight:800;
      }

      .mejdet-file-name{
        display:block;
        font-size:.90rem;
        font-weight:900;
        color:#0b4a8f;
        text-decoration:none;
        word-break:break-word;
      }

      .mejdet-file-name:hover{
        text-decoration:underline;
      }

      .mejdet-file-size{
        font-size:.75rem;
        color:#475569;
        margin-top:2px;
      }

      .mejdet-empty-box{
        background:rgba(255,255,255,.85);
        border:1px dashed #cfd8e3;
        border-radius:14px;
        padding:18px;
        text-align:center;
        color:#475569;
        font-weight:700;
      }

      .mejdet-bottom-actions{
        display:flex;
        justify-content:center;
        gap:12px;
        margin-top:26px;
        flex-wrap:wrap;
      }

      .mejdet-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .mejdet-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      h3{
        color:#ffffff;
        margin:0;
      }

      @media (max-width:992px){
        .mejdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .mejdet-title{
          font-size:1.20rem;
        }

        .mejdet-subtitle{
          font-size:.68rem;
        }

        .mejdet-card-body{
          padding:16px;
        }
      }

      @media (max-width:768px){
        .mejdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .mejdet-header-overlay::before{
          margin:0;
        }

        .mejdet-title,
        .mejdet-subtitle{
          text-align:center;
        }

        .mejdet-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, it=it, read_only=read_only)
    return render_template_string(BASE, content=Markup(inner))


# =========================
# EDITAR PLAN
# =========================
@app.route('/mejora/edit/<int:id>', methods=['GET','POST'])
@login_required
def mejora_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede editar registros de planes de acción.", "danger")
        return redirect(url_for('mejora_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Planes de acción del SGSI"):
        flash("No tiene permiso para editar registros de planes de acción del SGSI.", "danger")
        return redirect(url_for('mejora_matriz'))

    it = (
        MejoraPlanRegistro.query
        .options(selectinload(MejoraPlanRegistro.evidencias))
        .get_or_404(id)
    )

    if request.method == 'POST':
        it.fecha = request.form.get('fecha') or ''
        it.descripcion_incumplimiento = (request.form.get('descripcion_incumplimiento') or '').strip()
        it.causa = (request.form.get('causa') or '').strip()
        it.tipo_accion = request.form.get('tipo_accion') or ''
        it.plan_accion = (request.form.get('plan_accion') or '').strip()
        it.termino_ejecucion = request.form.get('termino_ejecucion') or ''
        it.fecha_ejecucion_propuesta = request.form.get('fecha_ejecucion_propuesta') or ''
        it.responsable = (request.form.get('responsable') or '').strip()
        it.estado_actividad = request.form.get('estado_actividad') or ''
        it.fecha_cierre = request.form.get('fecha_cierre') or ''
        it.eficacia = request.form.get('eficacia') or ''
        it.observacion_eficacia = (request.form.get('observacion_eficacia') or '').strip()

        files = request.files.getlist('evidencias')
        for f in files:
            if not f or not f.filename:
                continue
            if not is_allowed_pdf(f.filename):
                flash(f"Archivo no permitido (solo PDF): {f.filename}", "danger")
                continue

            store_name = unique_store_name(f.filename)
            upload_dir = get_upload_mejora_dir()
            path = os.path.join(upload_dir, store_name)
            f.save(path)

            ev = MejoraPlanEvidencia(
                plan=it,
                filename=store_name,
                original_name=secure_filename(f.filename),
                mime='application/pdf',
                size=os.path.getsize(path)
            )
            db.session.add(ev)

        db.session.commit()
        flash("Plan de acción actualizado.", "success")
        return redirect(url_for('mejora_matriz'))

    html = """
    <div class="mejedit-shell">

      <div class="mejedit-header-card">
        <div class="mejedit-header-overlay">
          <div class="mejedit-header-text">
            <h3 class="mejedit-title m-0">Editar Plan de Acción</h3>
            <div class="mejedit-subtitle">
              Actualiza acciones correctivas o de mejora bajo el ciclo PHVA
            </div>
          </div>
        </div>
      </div>

      <div class="mejedit-header-actions">
        <a href="{{ url_for('mejora_matriz') }}"
           class="btn rounded-pill px-5 fw-bold mejedit-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="mejedit-card">
        <div class="mejedit-card-body">

          <form method="post" enctype="multipart/form-data">
            <div class="row g-3">

              <div class="col-12">
                <div class="mejedit-section-title">Planear</div>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha</label>
                <input type="date" name="fecha" class="form-control" value="{{ it.fecha or '' }}">
              </div>

              <div class="col-md-9">
                <label class="form-label">Descripción o incumplimiento</label>
                <textarea name="descripcion_incumplimiento" class="form-control" rows="2">{{ it.descripcion_incumplimiento or '' }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Causa</label>
                <textarea name="causa" class="form-control" rows="2">{{ it.causa or '' }}</textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Tipo de acción</label>
                <select name="tipo_accion" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Correctiva" {% if it.tipo_accion == 'Correctiva' %}selected{% endif %}>Correctiva</option>
                  <option value="Mejora" {% if it.tipo_accion == 'Mejora' %}selected{% endif %}>Mejora</option>
                </select>
              </div>

              <div class="col-md-12">
                <label class="form-label">Plan de acción</label>
                <textarea name="plan_accion" class="form-control" rows="2">{{ it.plan_accion or '' }}</textarea>
              </div>

              <div class="col-12">
                <div class="mejedit-section-title">Hacer</div>
              </div>

              <div class="col-md-3">
                <label class="form-label">Término de ejecución</label>
                <select name="termino_ejecucion" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Corto plazo" {% if it.termino_ejecucion == 'Corto plazo' %}selected{% endif %}>Corto plazo</option>
                  <option value="Mediano plazo" {% if it.termino_ejecucion == 'Mediano plazo' %}selected{% endif %}>Mediano plazo</option>
                  <option value="Largo plazo" {% if it.termino_ejecucion == 'Largo plazo' %}selected{% endif %}>Largo plazo</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de ejecución propuesta</label>
                <input type="date" name="fecha_ejecucion_propuesta" class="form-control" value="{{ it.fecha_ejecucion_propuesta or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Responsable</label>
                <input name="responsable" class="form-control" value="{{ it.responsable or '' }}">
              </div>

              <div class="col-12">
                <div class="mejedit-section-title">Verificar</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Estado de la actividad</label>
                <select name="estado_actividad" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Abierto" {% if it.estado_actividad == 'Abierto' %}selected{% endif %}>Abierto</option>
                  <option value="Cerrado" {% if it.estado_actividad == 'Cerrado' %}selected{% endif %}>Cerrado</option>
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha de cierre</label>
                <input type="date" name="fecha_cierre" class="form-control" value="{{ it.fecha_cierre or '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Agregar nuevas evidencias (PDF)</label>
                <input type="file"
                       id="evidencias"
                       name="evidencias"
                       accept=".pdf"
                       multiple
                       class="form-control"
                       onchange="acumularEvidencias(this)">
                <small class="text-muted">
                  Puedes seleccionar varios a la vez o ir agregando en varias rondas.
                </small>
                <div id="lista_evidencias_nuevas" class="mt-2"></div>
              </div>

              <div class="col-12">
                <div class="mejedit-section-title">Actuar</div>
              </div>

              <div class="col-md-3">
                <label class="form-label">Eficacia (Sí / No)</label>
                <select name="eficacia" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Sí" {% if it.eficacia == 'Sí' %}selected{% endif %}>Sí</option>
                  <option value="No" {% if it.eficacia == 'No' %}selected{% endif %}>No</option>
                </select>
              </div>

              <div class="col-md-9">
                <label class="form-label">Observación de eficacia</label>
                <textarea name="observacion_eficacia" class="form-control" rows="2">{{ it.observacion_eficacia or '' }}</textarea>
              </div>

            </div>

            <div class="mejedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>
              <a class="btn rounded-pill px-4 fw-bold mejedit-cancel-btn"
                 href="{{ url_for('mejora_matriz') }}"
                 onclick="showLoader()">Cancelar</a>
            </div>
          </form>

          <div class="mejedit-evidencias-wrap mt-4">
            <label class="form-label">Evidencias existentes</label>
            {% if it.evidencias %}
              <div class="row g-3">
                {% for ev in it.evidencias %}
                <div class="col-md-6">
                  <div class="mejedit-file-card">
                    <div class="mejedit-file-meta">
                      <div class="mejedit-file-label">Archivo</div>
                      <a class="mejedit-file-name"
                         href="{{ url_for('mejora_evidencia_view', evi_id=ev.id, next='mejora_edit', reg_id=it.id) }}">
                        {{ ev.original_name or ev.filename }}
                      </a>
                      <div class="mejedit-file-size">{{ (ev.size / 1024)|round(1) if ev.size else 0 }} KB</div>
                    </div>

                    <form method="post"
                          action="{{ url_for('mejora_evidencia_delete', evi_id=ev.id) }}"
                          onsubmit="return confirm('¿Eliminar esta evidencia?');">
                      <button type="submit" class="btn btn-sm btn-danger rounded-pill">
                        Eliminar
                      </button>
                    </form>
                  </div>
                </div>
                {% endfor %}
              </div>
            {% else %}
              <div class="mejedit-empty-box">No hay evidencias cargadas.</div>
            {% endif %}
          </div>

        </div>
      </div>
    </div>

    <script>
      let evidenciasBufferDT = new DataTransfer();

      function renderListaEvidencias() {
        const cont = document.getElementById('lista_evidencias_nuevas');
        if (!cont) return;

        cont.innerHTML = '';
        if (evidenciasBufferDT.files.length === 0) {
          cont.innerHTML = '<div class="text-muted small">No hay archivos nuevos seleccionados</div>';
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

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .mejedit-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .mejedit-header-card{
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

      .mejedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .mejedit-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }

      .mejedit-header-overlay::before{
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

      .mejedit-header-text{
        max-width:1100px;
        min-width:0;
      }

      .mejedit-header-text::before{
        content:"SGSI · Edición de Mejora Continua";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .mejedit-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }

      .mejedit-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }

      .mejedit-header-actions{
        display:flex;
        justify-content:center;
        gap:12px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .mejedit-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .mejedit-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#cfd8e3;
      }

      .mejedit-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .mejedit-card-body{
        padding:22px;
      }

      .mejedit-card .form-label{
        font-weight:900;
        color:#334155;
        margin-bottom:6px;
        font-size:.86rem;
      }

      .mejedit-card .form-control,
      .mejedit-card .form-select{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
      }

      .mejedit-card textarea.form-control{
        min-height:90px;
        resize:vertical;
      }

      .mejedit-card .form-control:focus,
      .mejedit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .mejedit-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:10px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
        overflow-wrap:break-word;
      }

      .mejedit-file-card{
        background:#f8fbff;
        border:1px solid #e2ebf5;
        border-radius:14px;
        padding:12px 14px;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
        flex-wrap:wrap;
      }

      .mejedit-file-meta{
        min-width:0;
        flex:1;
      }

      .mejedit-file-label{
        font-size:.75rem;
        color:#475569;
        font-weight:800;
      }

      .mejedit-file-name{
        display:block;
        font-size:.90rem;
        font-weight:900;
        color:#0b4a8f;
        text-decoration:none;
        word-break:break-word;
      }

      .mejedit-file-name:hover{
        text-decoration:underline;
      }

      .mejedit-file-size{
        font-size:.75rem;
        color:#475569;
        margin-top:2px;
      }

      .mejedit-empty-box{
        background:rgba(255,255,255,.85);
        border:1px dashed #cfd8e3;
        border-radius:14px;
        padding:18px;
        text-align:center;
        color:#475569;
        font-weight:700;
      }

      .mejedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:12px;
        margin-top:26px;
        flex-wrap:wrap;
        width:100%;
      }

      .mejedit-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .mejedit-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#cfd8e3;
      }

      h3{
        color:#ffffff;
        margin:0;
      }

      @media (max-width:992px){
        .mejedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .mejedit-title{
          font-size:1.20rem;
        }

        .mejedit-subtitle{
          font-size:.68rem;
        }

        .mejedit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .mejedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .mejedit-header-overlay::before{
          margin:0;
        }

        .mejedit-title,
        .mejedit-subtitle{
          text-align:center;
        }

        .mejedit-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, it=it)
    return render_template_string(BASE, content=Markup(inner))


# =========================
# ELIMINAR PLAN
# =========================
@app.route('/mejora/delete/<int:id>')
@login_required
def mejora_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (user.role != 'admin' and not verificar_permiso(user, "Planes de acción del SGSI")):
        flash("No tiene permiso para eliminar registros de planes de acción.", "danger")
        return redirect(url_for('mejora_matriz'))

    it = MejoraPlanRegistro.query.options(selectinload(MejoraPlanRegistro.evidencias)).get_or_404(id)

    for ev in it.evidencias:
        try:
            p = os.path.join(get_upload_mejora_dir(), ev.filename)
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

    db.session.delete(it)
    db.session.commit()
    flash("Plan de acción eliminado correctamente.", "success")
    return redirect(url_for('mejora_matriz'))

# ==========================================================================================================================================
#                                                               Fin Módulo de Planes de Acción del SGSI
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                               Módulo ChatBox
# ==========================================================================================================================================

@app.route('/chatgpt_api', methods=['POST'])
@login_required
def chatgpt_api():
    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()

    if not user_msg:
        return jsonify({"error": "Mensaje vacío"}), 400

    try:
        print("[CHATGPT_API] Mensaje recibido:", user_msg)

        prompt = f"""
Actúa como asistente experto del SGSI GRAC.

Responde de forma clara, práctica y profesional.
Si la pregunta es sobre seguridad de la información, ISO 27001, NIST, PCI-DSS, BCP/DRP,
riesgos, auditoría, proveedores, incidentes, vulnerabilidades o gobierno de seguridad,
entrega una respuesta orientada a implementación.

Pregunta del usuario:
{user_msg}

Instrucciones:
- Responde en español.
- Sé concreto.
- No generes respuestas excesivamente largas.
- Máximo 600 palabras.
"""

        respuesta = chat_ai(
            prompt=prompt,
            model="openai/gpt-4o-mini"
        )

        print("[CHATGPT_API] Respuesta generada correctamente")

        if not respuesta or not str(respuesta).strip():
            respuesta = "No se recibió respuesta de la IA."

        return jsonify({"reply": respuesta})

    except Exception as e:
        print("[CHATGPT_API ERROR]:", repr(e))

        return jsonify({
            "error": "No fue posible consultar la IA en este momento. Detalle técnico: " + repr(e)
        }), 500


