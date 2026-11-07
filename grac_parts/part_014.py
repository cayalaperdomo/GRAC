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


@app.route("/chatgpt_view", methods=["GET"])
@login_required
def chatgpt_view():
    html = """
    <div class="chatsgsi-shell">

      <div class="chatsgsi-header-card">
        <div class="chatsgsi-header-overlay">
          <div class="chatsgsi-header-text">
            <h3 class="chatsgsi-title m-0">Asistente SGSI (ChatGPT)</h3>
            <div class="chatsgsi-subtitle">
              Consulta dudas, orientación y apoyo sobre tu SGSI directamente desde el asistente integrado.
            </div>
          </div>
        </div>
      </div>

      <div class="chatsgsi-card p-0">
        <div class="chatsgsi-card-header">
          Chat con el asistente
        </div>

        <div class="chatsgsi-card-body">

          <div id="chat-box" class="chatsgsi-box"></div>

          <div class="d-flex gap-2 mt-3">
            <input type="text"
                   id="user-input"
                   class="form-control"
                   placeholder="Escribe tu pregunta sobre el SGSI..."
                   autocomplete="off">

            <button id="chat-send-btn"
                    class="chat-send-clean"
                    type="button"
                    onclick="consultarAIChatGPT()">
              Enviar
            </button>
          </div>

        </div>
      </div>
    </div>

    <script>
      window.SGSI_DISABLE_GLOBAL_LOADER = true;
      window.SGSI_PROGRESS_GLOBAL_DISABLED = true;

      function ocultarLoaderChatGPT() {
        const ids = [
          'SGSI_PROGRESS_GLOBAL',
          'sgsi-progress-global',
          'global-loader',
          'loader',
          'loadingOverlay',
          'progressOverlay',
          'progressGlobal',
          'SGSI_PROGRESS_OVERLAY'
        ];

        ids.forEach(function(id) {
          const el = document.getElementById(id);
          if (el) {
            el.style.display = 'none';
            el.style.visibility = 'hidden';
            el.style.opacity = '0';
            el.style.pointerEvents = 'none';
          }
        });
      }

      function appendMessage(text, who) {
        const chatBox = document.getElementById('chat-box');

        const wrapper = document.createElement('div');
        wrapper.className = 'mb-2 d-flex ' + (who === 'user' ? 'justify-content-end' : 'justify-content-start');

        const bubble = document.createElement('div');
        bubble.className = 'px-3 py-2 rounded-3 chatsgsi-bubble ' + (who === 'user' ? 'chatsgsi-user' : 'chatsgsi-bot');
        bubble.style.maxWidth = '75%';
        bubble.innerText = text;

        wrapper.appendChild(bubble);
        chatBox.appendChild(wrapper);
        chatBox.scrollTop = chatBox.scrollHeight;
      }

      async function consultarAIChatGPT() {
        ocultarLoaderChatGPT();

        const userInput = document.getElementById('user-input');
        const sendBtn = document.getElementById('chat-send-btn');
        const chatBox = document.getElementById('chat-box');

        const text = (userInput.value || '').trim();
        if (!text) return false;

        appendMessage(text, 'user');

        userInput.value = '';
        userInput.focus();

        sendBtn.disabled = true;
        sendBtn.innerText = 'Consultando IA...';

        const thinkingId = 'thinking-' + Date.now();

        const thinkingDiv = document.createElement('div');
        thinkingDiv.id = thinkingId;
        thinkingDiv.className = 'mb-2 d-flex justify-content-start';
        thinkingDiv.innerHTML = '<div class="px-3 py-2 rounded-3 chatsgsi-bubble chatsgsi-thinking text-muted small">Pensando...</div>';

        chatBox.appendChild(thinkingDiv);
        chatBox.scrollTop = chatBox.scrollHeight;

        const controller = new AbortController();

        // 300 segundos para evitar corte prematuro del chat
        const timeoutId = setTimeout(function() {
          controller.abort();
        }, 300000);

        try {
          const resp = await fetch("{{ url_for('chatgpt_api') }}", {
            method: "POST",
            credentials: "same-origin",
            signal: controller.signal,
            headers: {
              "Content-Type": "application/json",
              "X-No-Loader": "1"
            },
            body: JSON.stringify({
              message: text
            })
          });

          clearTimeout(timeoutId);

          const raw = await resp.text();

          let data = {};
          try {
            data = JSON.parse(raw);
          } catch (e) {
            data = {
              error: "Respuesta no válida del servidor: " + raw.substring(0, 300)
            };
          }

          const t = document.getElementById(thinkingId);
          if (t) t.remove();

          if (!resp.ok) {
            appendMessage("⚠ Error HTTP " + resp.status + ": " + (data.error || raw), 'bot');
          } else if (data.reply) {
            appendMessage(data.reply, 'bot');
          } else if (data.error) {
            appendMessage("⚠ " + data.error, 'bot');
          } else {
            appendMessage("No se recibió una respuesta válida del asistente.", 'bot');
          }

        } catch (err) {
          clearTimeout(timeoutId);

          const t = document.getElementById(thinkingId);
          if (t) t.remove();

          if (err.name === 'AbortError') {
            appendMessage("⚠ La consulta tardó demasiado. Valida que OpenRouter/Ollama esté activo y que el modelo responda correctamente.", 'bot');
          } else {
            appendMessage("⚠ Error de conexión consultando la IA: " + err.message, 'bot');
          }

          console.error(err);

        } finally {
          sendBtn.disabled = false;
          sendBtn.innerText = 'Enviar';
          userInput.focus();
          ocultarLoaderChatGPT();
        }

        return false;
      }

      document.addEventListener('DOMContentLoaded', function() {
        ocultarLoaderChatGPT();

        const userInput = document.getElementById('user-input');

        userInput.addEventListener('keydown', function(e) {
          if (e.key === 'Enter') {
            e.preventDefault();
            consultarAIChatGPT();
          }
        });

        userInput.focus();
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

      #SGSI_PROGRESS_GLOBAL,
      #sgsi-progress-global,
      #global-loader,
      #loader,
      #loadingOverlay,
      #progressOverlay,
      #progressGlobal,
      #SGSI_PROGRESS_OVERLAY{
        display:none !important;
        visibility:hidden !important;
        opacity:0 !important;
        pointer-events:none !important;
      }

      .chatsgsi-shell{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .chatsgsi-header-card{
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

      .chatsgsi-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .chatsgsi-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .chatsgsi-header-overlay::before{
        content:"🤖";
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

      .chatsgsi-header-text::before{
        content:"SGSI · Asistente Inteligente";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .chatsgsi-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
      }

      .chatsgsi-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
      }

      .chatsgsi-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .chatsgsi-card-header{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#ffffff;
        font-weight:950;
        padding:14px 18px;
      }

      .chatsgsi-card-body{
        padding:18px;
        overflow:hidden;
      }

      .chatsgsi-box{
        height:500px;
        border:1px solid #e2ebf5;
        border-radius:14px;
        padding:12px;
        overflow:auto;
        background:#f8fbff;
      }

      .chatsgsi-bubble{
        box-shadow:0 4px 12px rgba(15,23,42,.08);
        border-radius:14px;
        padding:10px 14px;
        margin-bottom:8px;
        max-width:85%;
        overflow-wrap:break-word;
        word-break:break-word;
        line-height:1.45;
        font-size:.90rem;
      }

      .chatsgsi-user{
        background:linear-gradient(135deg,#0b4a8f,#1d5fae);
        color:#ffffff;
        margin-left:auto;
      }

      .chatsgsi-bot,
      .chatsgsi-thinking{
        background:#ffffff;
        border:1px solid #e2ebf5;
        color:#334155;
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

      .chat-send-clean{
        border:none;
        border-radius:999px;
        min-width:110px;
        padding:0 22px;
        background:#198754;
        color:#ffffff;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .chat-send-clean:disabled{
        opacity:.75;
        cursor:not-allowed;
      }

      @media (max-width:992px){
        .chatsgsi-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .chatsgsi-box{
          height:420px;
        }
      }

      @media (max-width:768px){
        .chatsgsi-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .chatsgsi-header-overlay::before{
          margin:0;
        }

        .chatsgsi-title,
        .chatsgsi-subtitle{
          text-align:center;
        }

        .chatsgsi-bubble{
          max-width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(html)
    return render_template_string(BASE, content=Markup(inner))


# ==========================================================================================================================================
#                                                               Fin del Módulo ChatBox
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                               Módulo Nivel de Madurez ISO 27001:2022
# ==========================================================================================================================================

def calcular_progreso_formulario(preguntas, form_data=None, respuestas_db=None):
    """
    Retorna: (respondidas, total, porcentaje)
    - form_data: request.form
    - respuestas_db: dict {pregunta_id: {"opcion": "...", "comentario": "..."}}
    """
    total = sum(1 for p in preguntas if p.tipo == "q")
    respondidas = 0

    for p in preguntas:
        if p.tipo != "q":
            continue

        opcion = ""
        if form_data is not None:
            opcion = (form_data.get(f"r_{p.id}") or "").strip()
        elif respuestas_db is not None:
            opcion = (respuestas_db.get(p.id, {}).get("opcion") or "").strip()

        if opcion:
            respondidas += 1

    porcentaje = int(round((respondidas / total) * 100)) if total > 0 else 0
    return respondidas, total, porcentaje


def obtener_borrador_madurez(user_id):
    """
    Busca el borrador activo más reciente del usuario.
    """
    if not user_id:
        return None

    return (
        MadurezRun.query
        .filter(
            MadurezRun.user_id == user_id,
            MadurezRun.estado == "BORRADOR"
        )
        .order_by(MadurezRun.updated_at.desc().nullslast(), MadurezRun.id.desc())
        .first()
    )


def cargar_respuestas_run(run_id):
    """
    Retorna dict:
    {
      pregunta_id: {"opcion": "...", "comentario": "..."}
    }
    """
    out = {}
    if not run_id:
        return out

    rows = (
        MadurezRespuesta.query
        .filter_by(run_id=run_id)
        .all()
    )

    for r in rows:
        out[r.pregunta_id] = {
            "opcion": (r.opcion or "").strip(),
            "comentario": (r.comentario or "").strip()
        }

    return out

def normalize_control_code(v) -> str:
    """
    Convierte el código de control de ANEXO A a texto estable:
    - Si Excel lo convirtió a fecha (05/06/2026) => "5.6"
    - Si viene numérico 5.1 => "5.1"
    - Si viene string => strip()
    """
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""

    # pandas Timestamp / datetime
    if isinstance(v, (pd.Timestamp, datetime, date)):
        # Excel te lo convirtió a fecha "05/06/2026" => day=5 month=6 => "5.6"
        return f"{int(v.day)}.{int(v.month)}"

    # numérico (float/int)
    if isinstance(v, (int, float, np.number)):
        s = str(v)
        return s.rstrip("0").rstrip(".")  # "5.0" -> "5", "5.10" -> "5.1"

    # texto
    return str(v).strip()

# ==========================
# IA HARDENING (NO CONDICIONAL)
# ==========================
_CONDITIONAL_PATTERNS = [
    r"\bpodr[ií]a\b",
    r"\bdeber[ií]a\b",
    r"\bser[ií]a\b",
    r"\bquiz[aá]s\b",
    r"\btal\s+vez\b",
    r"\bposiblemente\b",
    r"\bpuede\s+que\b",
    r"\bes\s+posible\s+que\b",
    r"\bprobablemente\b",
    r"\bse\s+recomendar[ií]a\b",
    r"\bse\s+podr[ií]a\b",
]

def harden_no_conditionals(text: str) -> str:
    """
    Normaliza salida IA para evitar lenguaje condicional.
    Reemplaza por redacción verificable (imperativo/indicativo).
    """
    s = (text or "").strip()

    # Reemplazos directos (pragmáticos)
    replacements = {
        "podría": "puede",
        "podria": "puede",
        "debería": "debe",
        "deberia": "debe",
        "sería": "es",
        "seria": "es",
        "quizás": "",
        "quizas": "",
        "tal vez": "",
        "posiblemente": "",
        "puede que": "se requiere que",
        "es posible que": "se requiere que",
        "probablemente": "",
        "se recomendaría": "se recomienda",
        "se recomendaria": "se recomienda",
        "se podría": "se debe",
        "se podria": "se debe",
    }

    # Aplica reemplazos case-insensitive básicos
    for k, v in replacements.items():
        s = re.sub(rf"\b{k}\b", v, s, flags=re.IGNORECASE)

    # Limpieza de dobles espacios
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)

    # Si aún quedan patrones condicionales, los corta por seguridad
    for pat in _CONDITIONAL_PATTERNS:
        s = re.sub(pat, "", s, flags=re.IGNORECASE)

    s = re.sub(r"[ \t]{2,}", " ", s).strip()
    return s

def _b64_to_rl_image(b64: str, width: float = 6.8*inch):
    if not b64:
        return None
    try:
        raw = base64.b64decode(b64)
        bio = io.BytesIO(raw)
        img = Image(bio)
        # conserva ratio
        iw, ih = img.imageWidth, img.imageHeight
        if iw and ih:
            ratio = ih / float(iw)
            img.drawWidth = width
            img.drawHeight = width * ratio
        else:
            img.drawWidth = width
        return img
    except Exception:
        return None

def _p(text: str, styles, style_name="BodyText"):
    t = (text or "").strip()
    t = t.replace("\n", "<br/>")
    return Paragraph(t, styles[style_name])

def _badge_color_for_score(pct: float):
    try:
        p = float(pct or 0)
    except Exception:
        p = 0.0
    if p >= 80: return colors.HexColor("#198754")  # verde
    if p >= 60: return colors.HexColor("#0d6efd")  # azul
    if p >= 40: return colors.HexColor("#ffc107")  # amarillo
    return colors.HexColor("#dc3545")              # rojo

def _badge_color_for_gap(level: str):
    lvl = (level or "").strip().lower()
    if lvl == "bajo": return colors.HexColor("#198754")
    if lvl == "medio": return colors.HexColor("#ffc107")
    if lvl == "alto": return colors.HexColor("#dc3545")
    if lvl in ("critico", "crítico"): return colors.HexColor("#212529")
    return colors.HexColor("#6c757d")


def gap_from_maturity_pct(pct_madurez: float) -> dict:
    """
    Brecha = 100 - madurez.
    Retorna: {gap_pct, nivel_brecha, interpretacion}
    """
    p = _to_float(pct_madurez, 0.0)
    # clamp
    if p < 0: p = 0.0
    if p > 100: p = 100.0

    gap_pct = round(100.0 - p, 2)
    gl = get_gap_level_for_pct(gap_pct)
    return {
        "gap_pct": gap_pct,
        "nivel_brecha": gl.get("nivel_brecha", ""),
        "interpretacion": gl.get("interpretacion", ""),
    }

def ensure_control_ai_fields(data: dict, kpi: dict = None) -> dict:
    """
    Garantiza que estado_actual, estado_requerido y plan_accion_sugerido
    existan y tengan contenido suficiente, sin crear campos adicionales.
    """
    if not isinstance(data, dict):
        data = {}

    ea = harden_no_conditionals(to_text(data.get("estado_actual")).strip())
    er = harden_no_conditionals(to_text(data.get("estado_requerido")).strip())
    pa = harden_no_conditionals(to_text(data.get("plan_accion_sugerido")).strip())

    if not ea:
        ea = (
            "El control presenta implementación parcial con evidencia disponible en varios requisitos evaluados. "
            "Sin embargo, aún existen brechas en consistencia operativa, seguimiento periódico y trazabilidad "
            "de los aspectos que no están completamente cerrados."
        )

    if not er:
        er = (
            "El control debe operar con un proceso definido, evidencia verificable, revisión periódica, "
            "seguimiento de brechas y sostenibilidad en el tiempo, asegurando que todos los requisitos "
            "aplicables se mantengan cubiertos de forma consistente."
        )

    if not pa:
        pa = (
            "1. Formalizar y documentar el proceso asociado al control con responsables y criterios de revisión.\n"
            "2. Cerrar las brechas identificadas en estados PARCIAL, NO y SIN_MARCAR mediante evidencia verificable.\n"
            "3. Establecer seguimiento periódico con revisión de vigencia, resultados y oportunidades de mejora."
        )

    return {
        "estado_actual": ea,
        "estado_requerido": er,
        "plan_accion_sugerido": pa
    }

def rl_pct_chip_cell(pct: float, label: str, style, chip_w=0.10*inch):
    """
    Celda compuesta: [chip color | texto % (madurez)].
    - chip_w controla qué tan pequeño queda el color al lado del porcentaje.
    """
    chip_color = rl_badge_bg_for_pct(pct)
    txt_color = rl_badge_fg_for_pct(pct)

    inner = Table(
        [["", Paragraph(xml_escape(label), style)]],
        colWidths=[chip_w, None]
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), chip_color),
        ("TEXTCOLOR",  (1,0), (1,0), txt_color),

        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING",(0,0), (-1,-1), 0),
        ("TOPPADDING",  (0,0), (-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),

        # opcional: un poquito de aire a la izquierda del texto
        ("LEFTPADDING", (1,0), (1,0), 4),
    ]))
    return inner

def pdf_questions_table(items_c: list):
    # Encabezados iguales a UI
    data = [[
        "Capítulo", "Ref", "Estado", "Pregunta/Requisito",
        "Comentarios", "Procesos", "%Brecha", "Nivel brecha", "Interpretación"
    ]]

    # Limita para evitar PDFs gigantescos (puedes subirlo si quieres)
    items_sorted = sorted(items_c or [], key=lambda x: int(x.get("row", 0) or 0))
    for it in items_sorted[:500]:
        st = (it.get("status") or "").strip()
        if st == "SIN_MARCAR":
            st_vis = ""
        else:
            st_vis = st

        bp = it.get("brecha_pct", None)
        bp_txt = "" if bp is None else f"{float(bp):.0f}%"

        data.append([
            str(it.get("sheet","") or ""),
            str(it.get("ref","") or "—"),
            st_vis,
            str(it.get("requisito","") or ""),
            str(it.get("comment","") or ""),
            str(it.get("procesos","") or ""),
            bp_txt,
            str(it.get("brecha_nivel","") or ""),
            str(it.get("brecha_interp","") or ""),
        ])

    t = Table(data, colWidths=[
        1.0*inch, 0.7*inch, 0.75*inch, 3.0*inch,
        1.6*inch, 1.2*inch, 0.7*inch, 0.9*inch, 2.0*inch
    ])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0b1b2b")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 8),
        ("FONTSIZE", (0,1), (-1,-1), 7),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("GRID", (0,0), (-1,-1), 0.25, colors.lightgrey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.HexColor("#f7f7f7")]),
    ]))
    return t


def control_ai_is_complete(d: dict) -> bool:
    """
    True si existen las 3 llaves y tienen texto.
    """
    if not isinstance(d, dict):
        return False
    return bool((d.get("estado_actual") or "").strip()) and bool((d.get("estado_requerido") or "").strip()) and bool((d.get("plan_accion_sugerido") or "").strip())


def summarize_plan_action(text: str) -> str:
    """
    Plan de acción sugerido (MUY resumido):
    - 1 sola frase (1 línea)
    - Sin responsable
    - Sin bullets
    - Sin tiempos 0–30 / 31–60 / 61–90
    - Sin detalle por ítem
    """
    s = (text or "").strip()
    if not s:
        return ""

    s = s.replace("\r\n", "\n").replace("\r", "\n")

    # Quitar referencias a fases/tiempos
    s = re.sub(r"\b0[\-–]\s*30\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\b31[\-–]\s*60\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\b61[\-–]\s*90\b", "", s, flags=re.IGNORECASE)

    # Quitar líneas con "responsable" explícito (por si la IA lo trae)
    s = re.sub(r"(?i)\bresponsable\s*:\s*.*", "", s).strip()

    # Extraer posibles líneas (si venía con bullets) y quedarnos con ideas
    lines = []
    for ln in s.split("\n"):
        ln = ln.strip().lstrip("•-–\t ").strip()
        if ln:
            lines.append(ln)

    # Si es un párrafo, partir por frases
    if len(lines) <= 1:
        chunks = re.split(r"[.;]\s+", s)
        lines = [c.strip().lstrip("•-–\t ").strip() for c in chunks if c.strip()]

    # Deduplicar
    uniq = []
    seen = set()
    for ln in lines:
        key = re.sub(r"\s+", " ", ln.lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(ln)
        if len(uniq) >= 8:
            break

    # Elegir 2–3 acciones genéricas (sin detalle por ítem)
    verbs = ("definir", "documentar", "establecer", "implementar", "actualizar",
             "formalizar", "evidenciar", "medir", "revisar", "aprobar", "registrar", "cerrar")
    prioritized = sorted(
        uniq,
        key=lambda t: (0 if any(t.lower().startswith(v) for v in verbs) else 1, len(t))
    )

    # Construir 1 sola frase “macro”
    # Si la IA venía muy específica, igual lo compactamos.
    macro_actions = []

    for ln in prioritized:
        t = re.sub(r"\s{2,}", " ", (ln or "").strip())

        # Elimina rastros de "Responsable ..." en medio de la frase
        t = re.sub(r"(?i)\bresponsable\b.*", "", t).strip()

        # Evitar frases ultra-específicas por ítem: si menciona "ítem", "subítem", "pregunta", las ignoramos
        if re.search(r"(?i)\bítem\b|\bsub[ií]tem\b|\bpregunta\b", t):
            continue

        if t:
            macro_actions.append(t)
        if len(macro_actions) >= 3:
            break

    # Si no hay material usable, usar una frase estándar
    if not macro_actions:
        return (
            "Definir y documentar el proceso del control, cerrar las brechas (NO/PARCIAL/SIN_MARCAR) con evidencia verificable y "
            "establecer revisión periódica con medición y seguimiento."
        )

    # Unir en una sola frase, sin bullets
    joined = "; ".join(macro_actions)

    # Asegurar cierre con punto
    joined = joined.rstrip(" .;")
    joined = joined + "."

    # Recortar si es demasiado largo
    if len(joined) > 220:
        joined = joined[:220].rstrip() + "…"

    return joined

def build_control_support_text(items: list, max_lines: int = 40) -> str:
    """
    Construye el bloque 'soporte' para IA con preguntas/requisitos del control.
    Prioriza brechas (NO/PARCIAL/SIN_MARCAR) y luego SI.
    Incluye comentario/procesos si existen. Excluye NA.
    """
    if not items:
        return "N/A"

    # Solo aplicables y no NA
    applicable = [
        x for x in (items or [])
        if x.get("applicable", True) and (x.get("status") != "NA")
    ]

    def _prio(st: str) -> int:
        st = (st or "").strip()
        if st in ("NO", "SIN_MARCAR"):
            return 0
        if st == "PARCIAL":
            return 1
        if st == "SI":
            return 2
        return 3

    # Orden: primero brechas, luego SI; dentro por fila
    applicable_sorted = sorted(
        applicable,
        key=lambda x: (_prio(x.get("status")), int(x.get("row", 0) or 0))
    )

    lines = []
    for it in applicable_sorted[:max_lines]:
        st = (it.get("status") or "").strip()
        ref = (it.get("ref") or "—").strip()
        req = (it.get("requisito") or "").strip()
        com = (it.get("comment") or "").strip()
        prc = (it.get("procesos") or "").strip()

        extra = []
        if com:
            extra.append(f"comentarios: {com}")
        if prc:
            extra.append(f"procesos: {prc}")

        extra_txt = (" | " + " ; ".join(extra)) if extra else ""
        if req:
            lines.append(f"- [{st}] ({ref}) {req}{extra_txt}")

    return "\n".join(lines) if lines else "N/A"


def is_control_optimo(kpi: dict) -> bool:
    """
    True si el control se considera Óptimo por porcentaje o por etiqueta de madurez.
    - pct >= 80
    - madurez == 'optimo' (ignorando tildes y mayúsculas)
    """
    try:
        pctv = float((kpi or {}).get("pct", 0) or 0)
    except Exception:
        pctv = 0.0

    mad = ((kpi or {}).get("madurez") or "").strip().lower()
    mad = unicodedata.normalize("NFD", mad)
    mad = "".join(ch for ch in mad if unicodedata.category(ch) != "Mn")  # quita tildes

    return (pctv >= 80) or (mad == "optimo")


def build_ai_methodology_iso27001(company_name: str) -> str:
    """
    Texto auditoría-ready. No usa condicional. Orientado a ISO 27001:2022.
    """
    txt = f"""
Criterio metodológico de análisis (ISO/IEC 27001:2022)

Este informe presenta los resultados de madurez y brechas del Sistema de Gestión de la Seguridad de la Información (SGSI), calculados a partir de las respuestas del instrumento aplicado y los parámetros de evaluación definidos por la organización.

Los resultados incluyen análisis por capítulo y por control, permitiendo identificar el nivel de cumplimiento y las brechas existentes para apoyar la toma de decisiones y la mejora continua del SGSI.

Consecutivo: {company_name}
"""
    return harden_no_conditionals(txt.strip())

def textarea_escape(s: str) -> str:
    s = s or ""
    s = s.replace("</textarea>", "</tex&#116;area>")
    return xml_escape(s)


def format_executive_summary(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        lines = []
        for x in value:
            t = to_text(x).strip()
            if t:
                if t.startswith(("•", "-", "–")):
                    lines.append(t)
                else:
                    lines.append("• " + t)
        return "\n".join(lines).strip()
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            vt = to_text(v).strip()
            if vt:
                lines.append(f"• {k}: {vt}")
        return "\n".join(lines).strip()
    return to_text(value).strip()

def ratio_text(done, total) -> str:
    try:
        d = int(done or 0)
        t = int(total or 0)
        return f"{d}/{t}"
    except Exception:
        return "0/0"

def format_ai_report(report_value) -> str:
    if report_value is None:
        return ""
    if isinstance(report_value, str):
        return report_value.strip()

    if isinstance(report_value, dict):
        lines = []
        ordered_keys = [k for k in CHAPTER_SHEETS if k in report_value] + [
            k for k in report_value.keys() if k not in CHAPTER_SHEETS
        ]

        for cap in ordered_keys:
            sec = report_value.get(cap)
            if sec is None:
                continue
            lines.append(f"{cap}")
            lines.append("-" * len(cap))

            if isinstance(sec, dict):
                key_map = [
                    ("análisis", "Análisis"),
                    ("analisis", "Análisis"),
                    ("riesgos", "Riesgos"),
                    ("quick_wins", "Quick wins"),
                    ("quickwins", "Quick wins"),
                    ("recomendaciones", "Recomendaciones"),
                    ("acciones", "Acciones"),
                ]
                printed = set()
                for k, label in key_map:
                    if k in sec and k not in printed:
                        txt = to_text(sec.get(k)).strip()
                        if txt:
                            lines.append(f"{label}: {txt}")
                        printed.add(k)

                for k, v in sec.items():
                    if k in printed:
                        continue
                    txt = to_text(v).strip()
                    if txt:
                        lines.append(f"{k.capitalize()}: {txt}")
            else:
                txt = to_text(sec).strip()
                if txt:
                    lines.append(txt)

            lines.append("")
        return "\n".join(lines).strip()

    if isinstance(report_value, list):
        return "\n".join(to_text(x).strip() for x in report_value if to_text(x).strip()).strip()

    return to_text(report_value).strip()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _to_float(x, default=None):
    try:
        if x is None:
            return default
        return float(str(x).strip())
    except Exception:
        return default


def _ranges_overlap(a_min, a_max, b_min, b_max):
    return not (a_max < b_min or b_max < a_min)

def _is_optimo(kpi_dict: dict) -> bool:
                pctv = float(kpi_dict.get("pct", 0) or 0)
                madv = (kpi_dict.get("madurez") or "").strip().lower()
                madv = unicodedata.normalize("NFD", madv)
                madv = "".join(ch for ch in madv if unicodedata.category(ch) != "Mn")
                return (pctv >= 80) or (madv == "optimo")

def get_maturity_label_for_pct(pct: float) -> str:
    pct = _to_float(pct, 0.0)

    rows = (ComplianceMaturityMap.query
            .join(MaturityLevel, ComplianceMaturityMap.maturity_id == MaturityLevel.id)
            .order_by(ComplianceMaturityMap.pct_min.asc(), ComplianceMaturityMap.pct_max.asc())
            .all())

    for r in rows:
        if r.pct_min <= pct <= r.pct_max:
            return r.maturity.madurez if r.maturity else ""
    return ""


def get_gap_level_for_pct(pct_brecha: float) -> dict:
    pct_brecha = _to_float(pct_brecha, 0.0)
    rows = GapLevelConfig.query.order_by(GapLevelConfig.pct_min.asc(), GapLevelConfig.pct_max.asc()).all()
    for r in rows:
        if r.pct_min <= pct_brecha <= r.pct_max:
            return {"nivel_brecha": r.nivel_brecha, "interpretacion": r.interpretacion or ""}
    return {"nivel_brecha": "", "interpretacion": ""}


def norm_txt(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and math.isnan(x):
        return ""
    s = str(x).strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def is_marked_x(val) -> bool:
    s = norm_txt(val)
    if s in ("x", "✓", "si", "sí", "1", "true", "ok"):
        return True
    if isinstance(val, (int, float)) and val == 1:
        return True
    return False


def is_excluded_row(desc: str) -> bool:
    s = norm_txt(desc)
    if "diagnostico" in s:
        return True
    if s.startswith("promedio"):
        return True
    return False


def is_note_row(desc: str) -> bool:
    s = norm_txt(desc)
    if not s:
        return False
    if s.startswith("nota") or s.startswith("notas") or "nota:" in s:
        return True
    return False


def is_grey_header_title(requisito: str) -> bool:
    s = norm_txt(requisito)
    if not s:
        return False
    targets = [
        "no aplica", "n/a", "na",
        "si", "sí",
        "parcial", "parcialmente",
        "no",
        "coment", "observ", "proces", "asociad",
        "estado", "cumplimiento"
    ]
    hits = sum(1 for t in targets if t in s)
    return hits >= 2


def is_title_row_by_marks(ref_txt: str, requisito: str, v_na, v_si, v_pa, v_no, comment: str, procesos: str) -> bool:
    if not requisito:
        return False
    if is_marked_x(v_na) or is_marked_x(v_si) or is_marked_x(v_pa) or is_marked_x(v_no):
        return False
    if (comment or "").strip() or (procesos or "").strip():
        return False
    if is_grey_header_title(requisito):
        return True
    s = norm_txt(requisito)
    header_words = ("criterio", "requisito", "control", "comentarios", "procesos asociados", "evidencia")
    if any(w in s for w in header_words) and len(s) <= 120:
        return True
    return False


def extract_subkey(sheet_name: str, ref_raw: str) -> str:
    ref = (ref_raw or "").strip()
    if not ref:
        return ""
    if "anexo" in norm_txt(sheet_name) or ref.upper().startswith("A"):
        m = re.match(r"^(A\.\d+)", ref.strip(), re.IGNORECASE)
        return m.group(1).upper() if m else ""
    m = re.match(r"^(\d+\.\d+)", ref.strip())
    return m.group(1) if m else ""


def detect_header_item_subitem(df: pd.DataFrame):
    max_scan = min(50, df.shape[0])

    def is_item(s): return s == "item"
    def is_subitem(s): return s == "subitem"
    def is_preg(s): return ("pregunta" in s) or ("requisito" in s)
    def is_na(s): return ("no aplica" in s) or ("n/a" in s) or (s in ("na", "n a"))
    def is_si(s): return s in ("si", "sí")
    def is_parcial(s): return "parcial" in s
    def is_no(s): return s == "no"
    def is_com(s): return ("coment" in s) or ("observ" in s)

    best = None

    for r in range(max_scan):
        col_map = {}
        for c in range(df.shape[1]):
            s = norm_txt(df.iat[r, c])
            if not s:
                continue

            if "item_col" not in col_map and is_item(s):
                col_map["item_col"] = c
            elif "subitem_col" not in col_map and is_subitem(s):
                col_map["subitem_col"] = c
            elif "preg_col" not in col_map and is_preg(s):
                col_map["preg_col"] = c
            elif "na_col" not in col_map and is_na(s):
                col_map["na_col"] = c
            elif "si_col" not in col_map and is_si(s):
                col_map["si_col"] = c
            elif "parcial_col" not in col_map and is_parcial(s):
                col_map["parcial_col"] = c
            elif "no_col" not in col_map and is_no(s):
                col_map["no_col"] = c
            elif "comments_col" not in col_map and is_com(s):
                col_map["comments_col"] = c

        score = 0
        for k in ("item_col", "preg_col"):
            if k in col_map:
                score += 5
        for k in ("na_col", "si_col", "parcial_col", "no_col"):
            if k in col_map:
                score += 2
        if "comments_col" in col_map:
            score += 1

        if best is None or score > best["score"]:
            best = {"score": score, "row": r, "col_map": col_map}

        if ("item_col" in col_map and "preg_col" in col_map and
            "si_col" in col_map and "no_col" in col_map):
            return r, col_map

    if best and best["score"] >= 10 and "item_col" in best["col_map"] and "preg_col" in best["col_map"]:
        return best["row"], best["col_map"]

    return None, None


def _clean_cell_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    s = str(v).strip()
    if s.lower() == "nan":
        return ""
    return s


def eval_status_from_row_item_subitem(df: pd.DataFrame, r: int, col_map: dict):
    item_col = col_map.get("item_col")
    subitem_col = col_map.get("subitem_col")
    preg_col = col_map.get("preg_col")
    na_col = col_map.get("na_col")
    si_col = col_map.get("si_col")
    parcial_col = col_map.get("parcial_col")
    no_col = col_map.get("no_col")
    comments_col = col_map.get("comments_col")

    item_val = df.iat[r, item_col] if item_col is not None and item_col < df.shape[1] else None
    sub_val  = df.iat[r, subitem_col] if subitem_col is not None and subitem_col < df.shape[1] else None
    preg_val = df.iat[r, preg_col] if preg_col is not None and preg_col < df.shape[1] else None

    item_txt = _clean_cell_text(item_val)
    sub_txt  = _clean_cell_text(sub_val)
    preg_txt = _clean_cell_text(preg_val)

    if not item_txt and not preg_txt and not sub_txt:
        return None, None, None, None, None, None, None

    v_na = df.iat[r, na_col] if na_col is not None and na_col < df.shape[1] else None
    v_si = df.iat[r, si_col] if si_col is not None and si_col < df.shape[1] else None
    v_pa = df.iat[r, parcial_col] if parcial_col is not None and parcial_col < df.shape[1] else None
    v_no = df.iat[r, no_col] if no_col is not None and no_col < df.shape[1] else None

    v_co = df.iat[r, comments_col] if comments_col is not None and comments_col < df.shape[1] else None
    comment = _clean_cell_text(v_co)

    if is_marked_x(v_na):
        return item_txt, sub_txt, preg_txt, False, "NA", None, comment

    if is_marked_x(v_si):
        return item_txt, sub_txt, preg_txt, True, "SI", 100, comment

    if is_marked_x(v_pa):
        return item_txt, sub_txt, preg_txt, True, "PARCIAL", 50, comment

    if is_marked_x(v_no):
        return item_txt, sub_txt, preg_txt, True, "NO", 0, comment

    return item_txt, sub_txt, preg_txt, True, "SIN_MARCAR", 0, comment

# ============================================================
# CONTROL ID + GRUPO + AGREGACIÓN POR CONTROL
# ============================================================
def get_control_id(sheet_name: str, ref_txt: str) -> str:
    ref = (ref_txt or "").strip().upper()
    sh = norm_txt(sheet_name)

    if not ref:
        return ""

    if "anexo" in sh or ref.startswith("A."):
        m = re.match(r"^(A\.\d+\.\d+)", ref)
        return m.group(1) if m else "A."

    m = re.match(r"^(\d+\.\d+)", ref)
    return m.group(1) if m else ""


def resolve_control_id(sheet_name: str, item_id: str = "", subitem_id: str = "", ref_txt: str = "") -> str:
    for candidate in (item_id, subitem_id, ref_txt):
        cid = get_control_id(sheet_name, candidate)
        if cid:
            return cid
    return ""


def get_item_subitem_ids(sheet_name: str, ref_txt: str, control_id: str) -> tuple[str, str]:
    ref = (ref_txt or "").strip().upper()
    cid = (control_id or "").strip().upper()
    sh = norm_txt(sheet_name)

    if not ref or not cid:
        return "", ""

    if "anexo" in sh or cid.startswith("A."):
        m4 = re.match(r"^(A\.\d+\.\d+)\.(\d+)\.(\d+)", ref)
        if m4:
            base = m4.group(1)
            item = f"{base}.{m4.group(2)}"
            subitem = f"{item}.{m4.group(3)}"
            return item, subitem

        m3 = re.match(r"^(A\.\d+\.\d+)\.(\d+)", ref)
        if m3:
            item = f"{m3.group(1)}.{m3.group(2)}"
            return item, ""

        m2 = re.match(r"^(A\.\d+\.\d+)", ref)
        if m2:
            return m2.group(1), ""

        return cid, ""

    m4 = re.match(r"^(\d+\.\d+)\.(\d+)\.(\d+)", ref)
    if m4:
        base = m4.group(1)
        item = f"{base}.{m4.group(2)}"
        subitem = f"{item}.{m4.group(3)}"
        return item, subitem

    m3 = re.match(r"^(\d+\.\d+)\.(\d+)", ref)
    if m3:
        item = f"{m3.group(1)}.{m3.group(2)}"
        return item, ""

    m2 = re.match(r"^(\d+\.\d+)", ref)
    if m2:
        return m2.group(1), ""

    return cid, ""


def get_control_group_from_control_id(control_id: str) -> str:
    cid = (control_id or "").strip().upper()
    if not cid:
        return "Sin clasificar"
    if cid.startswith("A."):
        return "Anexo A"

    for group, ids in CONTROL_GROUPS.items():
        if group == "Anexo A":
            continue
        if cid in ids:
            return group

    return "Sin clasificar"


def aggregate_by_control(items: list) -> dict:
    acc = {}

    for it in items or []:
        cid = (it.get("control_id") or "").strip()
        if not cid:
            continue

        if not it.get("applicable", True) or (it.get("status") == "NA"):
            continue

        if cid not in acc:
            acc[cid] = {"total": 0, "done": 0, "score_sum": 0, "counts": {"SI":0,"PARCIAL":0,"NO":0,"SIN_MARCAR":0}}

        acc[cid]["total"] += 1
        st = (it.get("status") or "SIN_MARCAR").strip()
        if st not in acc[cid]["counts"]:
            st = "SIN_MARCAR"
        acc[cid]["counts"][st] += 1

        acc[cid]["score_sum"] += int(it.get("score", 0) or 0)
        if st == "SI":
            acc[cid]["done"] += 1

    out = {}
    for cid, v in acc.items():
        total = v["total"]
        pct = round((v["score_sum"] / (total * 100) * 100) if total else 0.0, 2)
        gap_info = gap_from_maturity_pct(pct)

        out[cid] = {
            "pct": pct,
            "done": v["done"],
            "total": total,
            "counts": v["counts"],
            "group": get_control_group_from_control_id(cid),
            "madurez": get_maturity_label_for_pct(pct),

            # ✅ NUEVO: brecha por control
            "brecha_pct": gap_info["gap_pct"],
            "brecha_nivel": gap_info["nivel_brecha"],
            "brecha_interp": gap_info["interpretacion"],
        }

    ordered = {}
    for cid in CONTROL_ORDER:
        if cid in out:
            ordered[cid] = out[cid]

    annex = sorted([k for k in out.keys() if k.startswith("A.")])
    for cid in annex:
        ordered[cid] = out[cid]

    rest = sorted([k for k in out.keys() if k not in ordered])
    for cid in rest:
        ordered[cid] = out[cid]

    return ordered


def detect_header_and_columns(df: pd.DataFrame):
    max_scan = min(120, df.shape[0])

    def is_ref(s):
        return ("ref" == s) or ("refer" in s) or ("control" in s) or (s == "id") or (s == "codigo")
    def is_preg(s):
        return ("pregunta" in s) or ("preguntas" in s) or ("requisito" in s) or ("criterio" in s) or ("enunciado" in s)
    def is_na(s): return ("no aplica" in s) or ("n/a" in s) or (s in ("na", "n a"))
    def is_si(s): return s in ("si", "sí")
    def is_parcial(s): return "parcial" in s
    def is_no(s): return s == "no"
    def is_com(s): return ("coment" in s) or ("observ" in s) or ("nota" in s)
    def is_proc(s): return ("proces" in s) or ("asociad" in s) or ("document" in s) or ("evidenc" in s)

    best = {"score": -1, "row": 0, "col_map": {}}

    for r in range(max_scan):
        col_map = {}
        for c in range(df.shape[1]):
            s = norm_txt(df.iat[r, c])
            if not s:
                continue

            if "ref_col" not in col_map and is_ref(s):
                col_map["ref_col"] = c
            elif "preg_col" not in col_map and is_preg(s):
                col_map["preg_col"] = c
            elif "na_col" not in col_map and is_na(s):
                col_map["na_col"] = c
            elif "si_col" not in col_map and is_si(s):
                col_map["si_col"] = c
            elif "parcial_col" not in col_map and is_parcial(s):
                col_map["parcial_col"] = c
            elif "no_col" not in col_map and is_no(s):
                col_map["no_col"] = c
            elif "comments_col" not in col_map and is_com(s):
                col_map["comments_col"] = c
            elif "proc_col" not in col_map and is_proc(s):
                col_map["proc_col"] = c

        score = 0
        for k in ("si_col", "no_col"):
            if k in col_map:
                score += 5
        for k in ("na_col", "parcial_col"):
            if k in col_map:
                score += 3
        for k in ("preg_col", "ref_col"):
            if k in col_map:
                score += 3
        if "comments_col" in col_map:
            score += 2
        if "proc_col" in col_map:
            score += 1

        if score > best["score"]:
            best = {"score": score, "row": r, "col_map": col_map}

        if ("si_col" in col_map and "no_col" in col_map and "preg_col" in col_map):
            return r, col_map

    if best["score"] >= 8:
        return best["row"], best["col_map"]

    return 0, {"ref_col": 0, "preg_col": 1, "na_col": 2, "si_col": 3, "parcial_col": 4, "no_col": 5, "comments_col": 6, "proc_col": 7}


def _row_has_any_mark(df, r, col_map):
    for k in ("na_col", "si_col", "parcial_col", "no_col"):
        c = col_map.get(k)
        if c is None or c >= df.shape[1]:
            continue
        if is_marked_x(df.iat[r, c]):
            return True
    return False


def display_estado(status: str) -> str:
    s = (status or "").strip()
    if s == "SIN_MARCAR":
        return ""
    return s


def brecha_pct_from_status(status: str):
    st = (status or "").strip()
    if st == "SI":
        return 0.0
    if st == "PARCIAL":
        return 50.0
    if st == "NO":
        return 100.0
    if st == "SIN_MARCAR":
        return 100.0
    if st == "NA":
        return None
    return 100.0


def eval_status_from_row(df: pd.DataFrame, r: int, col_map: dict, requisito: str, ref_txt: str):
    na_col = col_map.get("na_col")
    si_col = col_map.get("si_col")
    parcial_col = col_map.get("parcial_col")
    no_col = col_map.get("no_col")
    comments_col = col_map.get("comments_col")
    proc_col = col_map.get("proc_col")

    v_na = df.iat[r, na_col] if na_col is not None and na_col < df.shape[1] else None
    v_si = df.iat[r, si_col] if si_col is not None and si_col < df.shape[1] else None
    v_pa = df.iat[r, parcial_col] if parcial_col is not None and parcial_col < df.shape[1] else None
    v_no = df.iat[r, no_col] if no_col is not None and no_col < df.shape[1] else None
    v_co = df.iat[r, comments_col] if comments_col is not None and comments_col < df.shape[1] else None
    v_pr = df.iat[r, proc_col] if proc_col is not None and proc_col < df.shape[1] else None

    comment = _clean_cell_text(v_co)
    procesos = _clean_cell_text(v_pr)

    is_title = is_title_row_by_marks(ref_txt, requisito, v_na, v_si, v_pa, v_no, comment, procesos)
    if is_title:
        return False, "", None, comment, procesos, True

    if is_marked_x(v_na):
        return False, "NA", None, comment, procesos, False

    if is_marked_x(v_si):
        return True, "SI", 100, comment, procesos, False
    if is_marked_x(v_pa):
        return True, "PARCIAL", 50, comment, procesos, False
    if is_marked_x(v_no):
        return True, "NO", 0, comment, procesos, False

    return True, "SIN_MARCAR", 0, comment, procesos, False


def parse_sheet_xls(excel_path: str, sheet_name: str):
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None, engine="xlrd")

    # 1) Intentar formato NUEVO (Item/Subitem/Pregunta…)
    hdr2, col_map2 = detect_header_item_subitem(df)

    # FORMATO NUEVO
    if hdr2 is not None and col_map2 is not None:
        items = []
        last_ref = ""
        last_cid = ""

        for r in range(hdr2 + 1, df.shape[0]):
            item_id, subitem_id, pregunta, applicable, status, score, comment = \
                eval_status_from_row_item_subitem(df, r, col_map2)

            if item_id is None and pregunta is None and subitem_id is None:
                continue

            item_txt = _clean_cell_text(item_id)
            sub_txt  = _clean_cell_text(subitem_id)
            preg_txt = _clean_cell_text(pregunta)
            comm_txt = _clean_cell_text(comment)

            ref_comp = f"{item_txt}{('.' + sub_txt) if sub_txt else ''}".strip()

            if not ref_comp and last_ref:
                ref_comp = last_ref

            has_mark = (status in ("SI", "PARCIAL", "NO", "NA")) or (status == "SIN_MARCAR" and bool(item_txt))
            if (not preg_txt) and (not comm_txt) and (not has_mark):
                continue

            if is_excluded_row(preg_txt) or is_note_row(preg_txt):
                continue

            control_id = resolve_control_id(sheet_name, item_id=item_txt, subitem_id=sub_txt, ref_txt=ref_comp)

            if not control_id and last_cid:
                control_id = last_cid

            if control_id:
                last_cid = control_id
            if ref_comp:
                last_ref = ref_comp

            control_group = get_control_group_from_control_id(control_id)

            it = {
                "sheet": sheet_name,
                "row": r + 1,
                "ref": ref_comp or "—",
                "requisito": preg_txt or "(Sin pregunta / evidencia en comentarios)",
                "applicable": bool(applicable) if applicable is not None else True,
                "status": status or "SIN_MARCAR",
                "score": 0 if score is None else int(score),
                "cumple": (status == "SI"),
                "comment": comm_txt or "",
                "procesos": "",
                "subkey": extract_subkey(sheet_name, ref_comp),
                "control_id": control_id,
                "control_group": control_group,
                "item_id": item_txt,
                "subitem_id": sub_txt,
            }

            bp = brecha_pct_from_status(it["status"])
            it["brecha_pct"] = bp if bp is not None else None
            if bp is not None:
                gl = get_gap_level_for_pct(bp)
                it["brecha_nivel"] = gl.get("nivel_brecha", "")
                it["brecha_interp"] = gl.get("interpretacion", "")
            else:
                it["brecha_nivel"] = ""
                it["brecha_interp"] = ""

            items.append(it)

        applicable_items = [it for it in items if it["applicable"] and it["status"] != "NA"]
        total = len(applicable_items)
        done = sum(1 for it in applicable_items if it["status"] == "SI")
        score_sum = sum(it["score"] for it in applicable_items) if total else 0
        pct = round((score_sum / (total * 100) * 100) if total else 0.0, 2)

        return items, pct, done, total, {}

    # FORMATO GENERAL
    hdr, col_map = detect_header_and_columns(df)

    ref_col = col_map.get("ref_col", 0)
    preg_col = col_map.get("preg_col", 1)

    items = []
    last_ref_txt = ""
    last_cid = ""

    for r in range(hdr + 1, df.shape[0]):
        ref_val = df.iat[r, ref_col] if ref_col is not None and ref_col < df.shape[1] else None
        preg_val = df.iat[r, preg_col] if preg_col is not None and preg_col < df.shape[1] else None

        ref_txt = _clean_cell_text(ref_val)
        requisito = _clean_cell_text(preg_val)

        applicable, status, score, comment, procesos, is_title = eval_status_from_row(
            df, r, col_map, requisito=requisito, ref_txt=ref_txt
        )

        comm_txt = _clean_cell_text(comment)
        proc_txt = _clean_cell_text(procesos)
        has_mark = _row_has_any_mark(df, r, col_map)

        if is_title:
            continue

        if (not requisito) and (not comm_txt) and (not proc_txt) and (not has_mark) and (not ref_txt):
            continue

        if is_excluded_row(requisito) or is_note_row(requisito):
            continue

        if not ref_txt and last_ref_txt:
            ref_txt = last_ref_txt

        control_id = get_control_id(sheet_name, ref_txt)
        if not control_id and last_cid:
            control_id = last_cid

        if ref_txt:
            last_ref_txt = ref_txt
        if control_id:
            last_cid = control_id

        control_group = get_control_group_from_control_id(control_id)

        item = {
            "sheet": sheet_name,
            "row": r + 1,
            "ref": ref_txt or "—",
            "requisito": requisito or "(Sin pregunta / evidencia en comentarios)",
            "applicable": bool(applicable) if applicable is not None else True,
            "status": status or "SIN_MARCAR",
            "score": 0 if score is None else int(score),
            "cumple": (status == "SI"),
            "comment": comm_txt,
            "procesos": proc_txt,
            "subkey": extract_subkey(sheet_name, ref_txt),
            "control_id": control_id,
            "control_group": control_group,
            "item_id": "",
            "subitem_id": "",
        }

        bp = brecha_pct_from_status(item["status"])
        item["brecha_pct"] = bp if bp is not None else None
        if bp is not None:
            gl = get_gap_level_for_pct(bp)
            item["brecha_nivel"] = gl.get("nivel_brecha", "")
            item["brecha_interp"] = gl.get("interpretacion", "")
        else:
            item["brecha_nivel"] = ""
            item["brecha_interp"] = ""

        items.append(item)

    applicable_items = [it for it in items if it["applicable"] and it["status"] != "NA"]
    total = len(applicable_items)
    done = sum(1 for it in applicable_items if it["status"] == "SI")
    score_sum = sum(it["score"] for it in applicable_items) if total else 0
    pct = round((score_sum / (total * 100) * 100) if total else 0.0, 2)

    detail_map = {}
    for it in applicable_items:
        sk = it.get("subkey") or ""
        if not sk:
            continue
        detail_map.setdefault(sk, {"score_sum": 0, "total": 0, "pct": 0.0})
        detail_map[sk]["total"] += 1
        detail_map[sk]["score_sum"] += it["score"]

    for sk, v in detail_map.items():
        v["pct"] = round((v["score_sum"] / (v["total"] * 100) * 100) if v["total"] else 0.0, 2)
        v.pop("score_sum", None)

    return items, pct, done, total, detail_map


# ==========================
# GRÁFICOS
# ==========================
def make_radar_base64(labels, values, title="Araña de madurez", max_label_len=22):
    # 1) recorte general
    labels2 = [l if len(l) <= max_label_len else (l[:max_label_len] + "…") for l in labels]

    # 2) ✅ FIX SOLO para 6 Planificación y 10 Mejora: poner salto de línea
    #    (funciona aunque vengan como "6 Planificación", "6 Planificación (algo)", etc.)
    def _wrap_special(s: str) -> str:
        ss = (s or "").strip()
        low = ss.lower()

        # ✅ número a la IZQUIERDA, misma línea
        if low.startswith("6 ") and "planific" in low:
            return ss  # ya viene correcto: "6 Planificación"

        if low.startswith("10 ") and "mejora" in low:
            return ss  # ya viene correcto: "10 Mejora"

        return ss

    labels2 = [_wrap_special(x) for x in labels2]

    N = len(labels2)
    if N == 0:
        return ""

    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    vals = values + values[:1]
    angs = angles + angles[:1]

    fig = plt.figure(figsize=(6.8, 6.8))
    ax = plt.subplot(111, polar=True)

    ax.plot(angs, vals, linewidth=2)
    ax.fill(angs, vals, alpha=0.22)

    # ✅ más separación entre etiquetas y círculo
    ax.tick_params(axis="x", pad=12)

    # coloca los labels
    ax.set_thetagrids(np.degrees(angles), labels2, fontsize=8)

    # ✅ FIX: rotación + alineación por ángulo para evitar sobreposición visual
    for lbl, ang in zip(ax.get_xticklabels(), angles):
        txt = (lbl.get_text() or "").lower()
        ang_deg = np.degrees(ang)

        # ✅ CASO ESPECIAL: 6 Planificación / 10 Mejora → CENTRADO
        if txt.startswith("6 ") or txt.startswith("10 "):
            lbl.set_rotation(0)                     # horizontal
            lbl.set_horizontalalignment("center")   # 🔥 centrado
            lbl.set_verticalalignment("center")
            lbl.set_rotation_mode("anchor")
            continue
        
            # Rota el texto para que "siga" el círculo y se lea mejor
        # y alinea según el lado (derecha/izquierda) del radar
        if 90 <= ang_deg <= 270:
            lbl.set_horizontalalignment("right")
            lbl.set_rotation(ang_deg + 180)
        else:
            lbl.set_horizontalalignment("left")
            lbl.set_rotation(ang_deg)

        lbl.set_rotation_mode("anchor")

    ax.set_ylim(0, 100)
    ax.set_title(title, y=1.12)

    buf = io.BytesIO()

    # ✅ deja aire arriba para el título (evita que tight_layout lo empuje)
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    fig.savefig(buf, format="png", dpi=170)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")



def make_bar_base64(labels, values, title="Madurez por capítulo", max_label_len=26):
    labs = [l if len(l) <= max_label_len else (l[:max_label_len] + "…") for l in labels]
    if not labs:
        return ""

    fig = plt.figure(figsize=(10.5, 4.2))
    ax = plt.subplot(111)

    x = np.arange(len(labs))
    bars = ax.bar(x, values)

    # ✅ deja aire arriba (dinámico) para que SIEMPRE haya espacio para etiquetas
    vmax = 0
    try:
        vmax = max(float(x) for x in values) if values else 0
    except Exception:
        vmax = 0
    ax.set_ylim(0, max(110, vmax + 12))

    ax.set_xticks(x)
    ax.set_xticklabels(labs, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("%")
    ax.set_title(title, pad=14)

    # ✅ SIEMPRE etiqueta arriba de la barra
    top_y = ax.get_ylim()[1]
    for i, v in enumerate(values):
        try:
            vv = float(v)
            label = f"{vv:.0f}%"
            y = min(vv + 2, top_y - 2)   # arriba, pero sin salirse del marco
            ax.text(i, y, label, ha="center", va="bottom", fontsize=8)
        except Exception:
            pass
    

    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.4)

    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png", dpi=170)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def make_bar_chapters_plus_annexA_with_box_base64(chapter_results: dict, control_results: dict, title: str = "Madurez por capítulo + Anexo A (%)") -> str:
    """
    Gráfico de barras por capítulo (incluye 'Anexo A' como un capítulo más).
    - Usa chapter_results para los capítulos (4–10 y Anexo A).
    - Si chapter_results no trae "Anexo A" o viene en 0, intenta estimarlo desde control_results (promedio de A.*).
    Retorna PNG base64.
    """
    if not isinstance(chapter_results, dict):
        chapter_results = {}

    labels = []
    values = []

    # Orden UI esperado
    ordered = list(CHAPTER_SHEETS)

    # 1) construir valores base desde chapter_results
    for sh in ordered:
        v = chapter_results.get(sh, {}) if isinstance(chapter_results.get(sh, {}), dict) else {}
        pct = v.get("pct", 0)
        try:
            pct = float(pct or 0)
        except Exception:
            pct = 0.0

        labels.append(sh)
        values.append(pct)

    # 2) Si "Anexo A" está vacío o no existe, estimarlo desde control_results (promedio de A.*)
    try:
        idx_annex = labels.index("Anexo A")
    except ValueError:
        idx_annex = -1

    if idx_annex >= 0:
        annex_pct = values[idx_annex]
        if annex_pct == 0.0 and isinstance(control_results, dict):
            a_pcts = []
            for cid, kpi in control_results.items():
                cid_u = str(cid).strip().upper()
                if cid_u.startswith("A."):
                    try:
                        a_pcts.append(float((kpi or {}).get("pct", 0) or 0))
                    except Exception:
                        pass
            if a_pcts:
                values[idx_annex] = round(sum(a_pcts) / len(a_pcts), 2)

    # 3) generar el gráfico
    return make_bar_base64(labels, values, title=title, max_label_len=26)


def make_bar_controls_4_10_base64(control_results: dict) -> str:
    """
    Barras SOLO para controles 4.1..10.2 (los de CONTROL_ORDER).
    """
    # control_results viene como dict: {cid: {"pct":..., ...}}
    labels = []
    values = []

    for cid in CONTROL_ORDER:
        if cid in control_results:
            labels.append(cid)
            values.append(float(control_results[cid].get("pct", 0) or 0))

    return make_bar_base64(labels, values, title="Madurez por control (4–10) (%)", max_label_len=10)


def make_bar_annexA_lowest_base64(control_results: dict, top_n: int = 20) -> str:
    """
    Barras resumidas del Anexo A: muestra los N controles con menor % (peores) para mantenerlo 'resumido'.
    Si no hay A.*, retorna "".
    """
    a_items = []
    for cid, v in (control_results or {}).items():
        cid_u = str(cid).strip().upper()
        if cid_u.startswith("A."):
            pct = float(v.get("pct", 0) or 0)
            a_items.append((cid_u, pct))

    if not a_items:
        return ""

    # Orden ascendente: peores primero (menor %)
    a_items.sort(key=lambda x: x[1])
    a_items = a_items[:max(1, int(top_n))]

    labels = [x[0] for x in a_items]
    values = [x[1] for x in a_items]

    return make_bar_base64(labels, values, title=f"Anexo A – Controles con menor madurez (Top {len(labels)}) (%)", max_label_len=14)

PLAN_SCHEMA_JSON = """
{
  "action_plan": [
    {
      "fase": "0-30|31-60|61-90|90+",
      "capitulo": "Contexto|Liderazgo|Planificación|Soporte|Operación|Evaluación de desempeño|Mejora|Anexo A",
      "requisito": "Requisito ISO 27001:2022 (ej: 6.1, 10.2, A.5.1, etc.) o 'Dominio' si aplica",
      "accion": "Acción detallada, ejecutable, verificable (NO condicional)",
      "evidencia": "Evidencia verificable esperada (política/procedimiento/registro/acta/indicador)",
      "responsable": "Rol responsable (ej: Líder SGSI / Dueño de proceso / TI / RRHH / Riesgos / Alta Dirección)",
      "prioridad": "Alta|Media|Baja"
    }
  ]
}
""".strip()

# ==========================
# IA
# ==========================

def normalize_plan_response(raw: str) -> dict:
    """
    Acepta:
      - {"action_plan":[...]}
      - {"plan":[...]}
      - [{...}, {...}]  <-- lista directa (tu caso)
    Retorna SIEMPRE dict: {"action_plan":[...]} con llaves normalizadas.
    """
    parsed = json.loads((raw or "").strip() or "{}")

    # 1) obtener lista de filas
    if isinstance(parsed, list):
        rows = parsed
    elif isinstance(parsed, dict):
        rows = parsed.get("action_plan") or parsed.get("plan") or parsed.get("acciones") or []
    else:
        rows = []

    if not isinstance(rows, list):
        rows = []

    # 2) normalizar llaves (acentos -> sin acentos) y a tu schema UI
    def _get(r, *keys):
        for k in keys:
            if k in r:
                return r.get(k)
        return None

    cleaned = []
    for r in rows:
        if not isinstance(r, dict):
            continue

        accion = _get(r, "accion", "acción", "Acción", "ACCION")
        proposito = _get(r, "proposito", "propósito", "Propósito", "PROPOSITO")
        evidencia = _get(r, "evidencia", "Evidencia", "EVIDENCIA")
        prioridad = _get(r, "prioridad", "Prioridad", "PRIORIDAD")
        horizonte = _get(r, "horizonte", "Horizonte", "HORIZONTE")
        dependencia = _get(r, "dependencia", "Dependencia", "DEPENDENCIA")
        responsable = _get(r, "responsable", "Responsable", "RESPONSABLE")
        requisito = _get(r, "requisito", "Requisito", "REQUISITO")
        capitulo = _get(r, "capitulo", "capítulo", "Capítulo", "CAPITULO")
        fase = _get(r, "fase", "Fase", "FASE")

        cleaned.append({
            "accion": harden_no_conditionals(to_text(accion)).strip(),
            "proposito": harden_no_conditionals(to_text(proposito)).strip(),
            "evidencia": harden_no_conditionals(to_text(evidencia)).strip(),
            "prioridad": (to_text(prioridad) or "").strip(),
            "horizonte": (to_text(horizonte) or "").strip(),
            "dependencia": harden_no_conditionals(to_text(dependencia)).strip(),
            "responsable": harden_no_conditionals(to_text(responsable)).strip(),
            "requisito": harden_no_conditionals(to_text(requisito)).strip(),
            "capitulo": (to_text(capitulo) or "").strip(),
            "fase": (to_text(fase) or "").strip(),
        })

    return {"action_plan": cleaned}


def get_openai_client():
    """
    Mantiene el mismo nombre para no romper el módulo,
    pero ahora devuelve configuración dinámica para:
    - OpenRouter
    - Ollama
    """
    provider = (get_ai_provider() or "openrouter").strip().lower()

    if provider == "ollama":
        return {
            "provider": "ollama",
            "base_url": (get_ollama_base_url() or "http://localhost:11434").strip().rstrip("/"),
            "model": (get_ollama_model() or "llama3.1").strip()
        }

    api_key = (get_openrouter_api_key() or "").strip()
    if not api_key:
        raise RuntimeError("No hay OPENROUTER_API_KEY configurada. Ve a Administración → OpenRouter API Key.")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://sgsi.local",
            "X-Title": "SGSI ISO 27001 Analyzer"
        }
    )

    return {
        "provider": "openrouter",
        "client": client,
        "model": "openai/gpt-4o-mini"
    }

def openai_call_with_retry(
    client: OpenAI, *, model: str, messages: list, response_format: dict,
    temperature: float = 0.2, max_tokens: int = None, max_retries: int = 6
):
    last_err = None
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
                max_tokens=max_tokens if max_tokens is not None else OPENROUTER_MAX_TOKENS,
            )
        except OpenAIError as e:
            msg = str(e).lower()
            last_err = e
            if "rate_limit" in msg or "429" in msg:
                sleep_s = min(30, (2 ** attempt)) + random.uniform(0.2, 1.0)
                time.sleep(sleep_s)
                continue
            raise
    raise last_err

def ai_json_iso(prompt: str,
                system_prompt: str = "Devuelve SOLO JSON válido. No agregues texto fuera del JSON.",
                model_openrouter: str = "openai/gpt-4o-mini",
                max_tokens: int = None) -> dict:
    """
    Helper IA para ISO 27001.
    Devuelve siempre dict JSON usando:
    - OpenRouter
    - Ollama
    """
    cfg = get_openai_client()
    provider = cfg.get("provider")

    print("DEBUG IA ISO - provider activo:", provider)

    # =========================
    # OLLAMA
    # =========================
    if provider == "ollama":
        base_url = (cfg.get("base_url") or "").rstrip("/")
        model = (cfg.get("model") or "").strip()

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
                    "temperature": 0.2
                }
            },
            timeout=300
        )
        resp.raise_for_status()

        payload = resp.json() or {}

        raw = (payload.get("response") or "").strip()
        if not raw:
            raw = (payload.get("message") or "").strip()

        if not raw:
            raise RuntimeError(f"Ollama respondió sin contenido. Payload: {str(payload)[:500]}")

        print("DEBUG IA ISO - RAW:", raw[:1500])
        return normalize_plan_response(raw)

    # =========================
    # OPENROUTER
    # =========================
    client = cfg["client"]
    model_name = cfg.get("model") or model_openrouter

    resp = openai_call_with_retry(
        client,
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=max_tokens
    )

    raw = (resp.choices[0].message.content or "").strip() or "{}"

    return normalize_plan_response(raw)

