def consultar_listas_restrictivas_global(nombre, tipo_documento=None, numero_documento=None, pais=None):
    """
    Consolida consulta local + externas.
    """
    local_result = consultar_listas_restrictivas_local(
        nombre=nombre,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        pais=pais
    )

    externas = consultar_listas_externas(
        nombre=nombre,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        pais=pais
    )

    detalle_total = []
    if local_result.get("detalle"):
        detalle_total.extend(local_result["detalle"])
    if externas:
        detalle_total.extend(externas)

    detalle_total = sorted(detalle_total, key=lambda x: x.get("score", 0), reverse=True)

    if not detalle_total:
        return {
            "fuente": "Local + Externas",
            "resultado": "Sin coincidencias",
            "nivel_riesgo": "Bajo",
            "score": 0.0,
            "detalle": []
        }

    mejor = detalle_total[0]
    return {
        "fuente": "Local + Externas",
        "resultado": mejor.get("resultado", "Sin coincidencias"),
        "nivel_riesgo": mejor.get("nivel_riesgo", "Bajo"),
        "score": mejor.get("score", 0.0),
        "detalle": detalle_total[:20]
    }

def _resolver_fuente_detectada(resultado):
    """
    Devuelve una cadena con las fuentes reales detectadas, por ejemplo:
    'ONU', 'OFAC', 'Lista Local' o 'OFAC, ONU'
    """
    detalle = resultado.get("detalle") or []

    if not detalle:
        return resultado.get("fuente", "No especificado")

    fuentes = []
    for item in detalle:
        fuente = (item.get("fuente") or "").strip()
        if fuente and fuente not in fuentes:
            fuentes.append(fuente)

    if not fuentes:
        return resultado.get("fuente", "No especificado")

    return ", ".join(fuentes)

def cargar_fuente_lista_desde_archivo(file_storage, fuente_default="Carga Archivo"):
    if not file_storage or not file_storage.filename:
        return 0, 0

    if not allowed_listas_file(file_storage.filename):
        raise ValueError("Archivo no permitido. Use .txt o .csv")

    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit('.', 1)[1].lower()

    contenido = file_storage.read()
    if isinstance(contenido, bytes):
        contenido = contenido.decode('utf-8', errors='ignore')

    insertados = 0
    omitidos = 0

    conn = get_listas_db_connection()
    cur = conn.cursor()

    if ext == 'txt':
        lineas = [ln.strip() for ln in contenido.splitlines() if ln.strip()]
        for linea in lineas:
            partes = [p.strip() for p in linea.split('|')]
            nombre = partes[0] if len(partes) > 0 else ''
            numero_documento = partes[1] if len(partes) > 1 else ''
            pais = partes[2] if len(partes) > 2 else ''
            categoria = partes[3] if len(partes) > 3 else ''

            if not nombre:
                omitidos += 1
                continue

            cur.execute("""
                INSERT INTO listas_restrictivas_fuente (
                    fuente, nombre, alias, tipo_documento, numero_documento, pais,
                    categoria, observaciones, activo, fecha_actualizacion
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Sí', ?)
            """, (
                fuente_default,
                nombre,
                '',
                '',
                numero_documento,
                pais,
                categoria,
                f'Cargado desde archivo plano: {filename}',
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            insertados += 1

    elif ext == 'csv':
        reader = csv.DictReader(io.StringIO(contenido))
        for row in reader:
            nombre = (row.get('nombre') or '').strip()
            alias = (row.get('alias') or '').strip()
            tipo_documento = (row.get('tipo_documento') or '').strip()
            numero_documento = (row.get('numero_documento') or '').strip()
            pais = (row.get('pais') or '').strip()
            categoria = (row.get('categoria') or '').strip()
            observaciones = (row.get('observaciones') or '').strip()

            if not nombre:
                omitidos += 1
                continue

            cur.execute("""
                INSERT INTO listas_restrictivas_fuente (
                    fuente, nombre, alias, tipo_documento, numero_documento, pais,
                    categoria, observaciones, activo, fecha_actualizacion
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Sí', ?)
            """, (
                fuente_default,
                nombre,
                alias,
                tipo_documento,
                numero_documento,
                pais,
                categoria,
                observaciones,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            insertados += 1

    conn.commit()
    conn.close()

    return insertados, omitidos

def get_consulta_lista_by_id(consulta_id):
    conn = get_listas_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM listas_restrictivas_consultas
        WHERE id = ?
    """, (consulta_id,))
    row = cur.fetchone()
    conn.close()
    return row


def delete_consulta_lista_by_id(consulta_id):
    conn = get_listas_db_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM listas_restrictivas_consultas
        WHERE id = ?
    """, (consulta_id,))
    conn.commit()
    cambios = cur.rowcount
    conn.close()
    return cambios > 0


def consultar_listas_restrictivas_local(nombre, tipo_documento=None, numero_documento=None, pais=None):
    conn = get_listas_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM listas_restrictivas_fuente
        WHERE activo = 'Sí'
    """)
    rows = cur.fetchall()
    conn.close()

    mejor = None
    coincidencias = []

    for r in rows:
        score_nombre = _score_nombre_lista(nombre, r["nombre"])
        documento_match = False

        if numero_documento and r["numero_documento"]:
            documento_match = (str(numero_documento).strip() == str(r["numero_documento"]).strip())

        score_final = 100.0 if documento_match else score_nombre
        resultado, nivel = _clasificar_resultado_lista(score_final, documento_match=documento_match)

        item = {
            "id": r["id"],
            "fuente": r["fuente"],
            "nombre": r["nombre"],
            "alias": r["alias"],
            "tipo_documento": r["tipo_documento"],
            "numero_documento": r["numero_documento"],
            "pais": r["pais"],
            "categoria": r["categoria"],
            "observaciones": r["observaciones"],
            "score": score_final,
            "resultado": resultado,
            "nivel_riesgo": nivel
        }

        if documento_match or score_final >= 80:
            coincidencias.append(item)

        if mejor is None or score_final > mejor["score"]:
            mejor = item

    if not mejor or mejor["score"] < 80:
        return {
            "fuente": "Lista Local",
            "resultado": "Sin coincidencias",
            "nivel_riesgo": "Bajo",
            "score": 0.0,
            "detalle": []
        }

    coincidencias = sorted(coincidencias, key=lambda x: x["score"], reverse=True)

    return {
        "fuente": "Lista Local",
        "resultado": mejor["resultado"],
        "nivel_riesgo": mejor["nivel_riesgo"],
        "score": mejor["score"],
        "detalle": coincidencias[:10]
    }

def registrar_consulta_lista_db(origen, proveedor_id, nombre_consultado, tipo_documento, numero_documento,
                                pais, fuente, resultado, nivel_riesgo, score, detalle,
                                observaciones, usuario):
    fecha_consulta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_listas_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO listas_restrictivas_consultas (
            origen, proveedor_id, nombre_consultado, tipo_documento, numero_documento, pais,
            fuente, resultado, nivel_riesgo, score_coincidencia,
            detalle_json, observaciones, usuario, fecha_consulta
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        origen,
        proveedor_id,
        nombre_consultado,
        tipo_documento,
        numero_documento,
        pais,
        fuente,
        resultado,
        nivel_riesgo,
        score,
        json.dumps(detalle, ensure_ascii=False),
        observaciones,
        usuario,
        fecha_consulta
    ))
    conn.commit()
    conn.close()

    if proveedor_id:
        upsert_estado_lista_proveedor(
            proveedor_id=proveedor_id,
            resultado=resultado,
            riesgo=nivel_riesgo,
            score=score,
            fecha_consulta=fecha_consulta,
            fuente=fuente
        )

    return fecha_consulta

@app.route('/listas_restrictivas', methods=['GET'])
@login_required
def listas_restrictivas_home():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Listas Restrictivas"):
            flash("No tiene permiso para acceder al módulo de Listas Restrictivas.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    conn = get_listas_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) AS total_base
        FROM listas_restrictivas_fuente
        WHERE activo = 'Sí'
    """)
    total_base = cur.fetchone()["total_base"]

    cur.execute("""
        SELECT COUNT(*) AS total_consultas
        FROM listas_restrictivas_consultas
    """)
    total_consultas = cur.fetchone()["total_consultas"]

    cur.execute("""
        SELECT id, fecha_consulta, nombre_consultado, resultado
        FROM listas_restrictivas_consultas
        ORDER BY fecha_consulta DESC, id DESC
        LIMIT 20
    """)
    ultimas_consultas = cur.fetchall()
    conn.close()

    html = """
    <div class="lr-shell">

      <!-- HEADER -->
      <div class="lr-header-card">
        <div class="lr-header-overlay">
          <div class="lr-header-text">
            <h3 class="lr-title m-0">Módulo de Listas Restrictivas</h3>
            <div class="lr-subtitle">
              Consulta consolidada contra listas externas y base local, administración de fuentes y trazabilidad histórica
            </div>
          </div>
        </div>
      </div>

      <!-- KPIs -->
      <div class="row g-3 mb-3">
        <div class="col-md-4">
          <div class="lr-kpi-card">
            <div class="lr-kpi-label">Registros activos base local</div>
            <div class="lr-kpi-value text-danger">{{ total_base }}</div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="lr-kpi-card">
            <div class="lr-kpi-label">Consultas realizadas</div>
            <div class="lr-kpi-value text-primary">{{ total_consultas }}</div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="lr-kpi-card">
            <div class="lr-kpi-label">Fuentes consultadas</div>
            <div class="lr-kpi-value text-dark">Local + Externas</div>
          </div>
        </div>
      </div>

      <!-- ACCIONES -->
      <div class="row g-3 mb-3">
        <div class="col-md-6">
          <div class="lr-action-card">
            <div class="lr-action-icon"><i class="bi bi-search"></i></div>
            <div class="lr-action-title">Consultar listas restrictivas</div>
            <div class="lr-action-desc">
              Realice búsqueda contra base local y listas externas como OFAC y ONU.
            </div>

            <div class="mt-3">
              <a href="{{ url_for('listas_restrictivas_consulta_manual') }}"
                 class="btn btn-primary rounded-pill px-4 fw-bold">
                Ir a consultar
              </a>
            </div>
          </div>
        </div>

        <div class="col-md-6">
          <div class="lr-action-card">
            <div class="lr-action-icon"><i class="bi bi-database"></i></div>
            <div class="lr-action-title">Administrar base local</div>
            <div class="lr-action-desc">
              Cree registros manuales o cargue archivos TXT / CSV.
            </div>

            <div class="mt-3">
              {% if current_user.role == 'admin' %}
              <a href="{{ url_for('listas_restrictivas_base') }}"
                 class="btn btn-primary rounded-pill px-4 fw-bold">
                Ir a la base
              </a>
              {% else %}
              <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
                Solo administrador
              </button>
              {% endif %}
            </div>
          </div>
        </div>
      </div>

      <!-- TABLA -->
      <div class="lr-table-card">
        <div class="lr-table-card-body">

          <h5 class="fw-bold mb-3">Últimas consultas</h5>

          {% if ultimas_consultas %}
          <div class="table-responsive">
            <table class="table table-bordered align-middle lr-table">
              <thead>
                <tr class="text-center">
                  <th>Fecha</th>
                  <th>Nombre</th>
                  <th>Resultado</th>
                  <th>Acciones</th>
                </tr>
              </thead>

              <tbody>
                {% for r in ultimas_consultas %}
                <tr>
                  <td>{{ r['fecha_consulta'] }}</td>
                  <td>{{ r['nombre_consultado'] }}</td>

                  <td class="text-center">
                    {% if r['resultado'] == 'Sin coincidencias' %}
                      <span class="badge bg-success">{{ r['resultado'] }}</span>
                    {% elif r['resultado'] == 'Coincidencia probable' %}
                      <span class="badge bg-warning text-dark">{{ r['resultado'] }}</span>
                    {% else %}
                      <span class="badge bg-danger">{{ r['resultado'] }}</span>
                    {% endif %}
                  </td>

                  <td class="text-center">
                    <a href="{{ url_for('listas_restrictivas_detalle', consulta_id=r['id']) }}"
                       class="btn btn-sm btn-primary rounded-pill px-3 fw-bold">
                      Ver
                    </a>
                  </td>
                </tr>
                {% endfor %}
              </tbody>

            </table>
          </div>
          {% else %}
          <div class="alert alert-info">No hay consultas registradas.</div>
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

      .lr-shell{
        width:96%;
        max-width:1700px;
        margin:10px auto 24px auto;
      }

      .lr-header-card{
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

      .lr-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .lr-header-overlay{
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

      .lr-header-overlay::before{
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

      .lr-header-text,
      .lr-header-overlay > div{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .lr-header-text::before,
      .lr-header-overlay > div::before{
        content:"SGSI · Listas Restrictivas";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .lr-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .lr-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .lr-kpi-card,
      .lr-action-card,
      .lr-table-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        height:100%;
      }

      .lr-kpi-card{
        padding:18px;
        text-align:center;
      }

      .lr-kpi-label{
        color:#475569;
        font-weight:900;
        font-size:.78rem;
        text-transform:uppercase;
        letter-spacing:.35px;
        margin-bottom:8px;
      }

      .lr-kpi-value{
        font-size:1.85rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1.1;
      }

      .lr-action-card{
        padding:18px;
        text-align:center;
        transition:all .2s ease;
      }

      .lr-action-card:hover{
        transform:translateY(-3px);
        box-shadow:0 16px 28px rgba(15,23,42,.22);
      }

      .lr-action-icon{
        width:52px;
        height:52px;
        border-radius:14px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.55rem;
        margin:0 auto 10px auto;
      }

      .lr-action-title{
        font-weight:950;
        font-size:.92rem;
        color:#0f172a;
      }

      .lr-action-desc{
        color:#475569;
        font-size:.78rem;
        margin-top:6px;
        line-height:1.35;
      }

      .lr-table-card-body{
        padding:14px 16px 16px 16px;
      }

      .lr-table-wrap,
      .table-responsive{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .lr-table{
        margin-bottom:0;
      }

      .lr-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border:none !important;
        font-size:.78rem;
        padding:9px 8px;
      }

      .lr-table th,
      .lr-table td{
        vertical-align:middle;
        font-size:.82rem;
        padding:9px 8px;
        word-break:break-word;
      }

      .lr-table td{
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .lr-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .lr-table tbody tr:hover td{
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

      .lr-shell .btn{
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      @media (max-width:992px){
        .lr-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .lr-header-card{
          min-height:88px;
        }

        .lr-title{
          font-size:1.20rem;
        }

        .lr-table-card-body{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .lr-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .lr-header-overlay::before{
          margin:0;
        }

        .lr-header-text::before,
        .lr-header-overlay > div::before{
          margin-left:auto;
          margin-right:auto;
        }
      }
    </style>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            html,
            total_base=total_base,
            total_consultas=total_consultas,
            ultimas_consultas=ultimas_consultas,
            read_only=read_only
        ))
    )

@app.route('/listas_restrictivas/detalle/<int:consulta_id>', methods=['GET'])
@login_required
def listas_restrictivas_detalle(consulta_id):
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Listas Restrictivas"):
        flash("No tiene permiso para ver el detalle de listas restrictivas.", "danger")
        return redirect(url_for('menu'))

    consulta = get_consulta_lista_by_id(consulta_id)
    if not consulta:
        flash("La consulta seleccionada no existe.", "danger")
        return redirect(url_for('listas_restrictivas_home'))

    html = """
    <div class="lr-shell">

      <div class="lr-header-card">
        <div class="lr-header-overlay">
          <div class="lr-header-text">
            <h3 class="lr-title m-0">Detalle de Consulta de Listas Restrictivas</h3>
            <div class="lr-subtitle">
              Información completa de la consulta seleccionada
            </div>
          </div>
        </div>
      </div>

      <div class="lr-detail-card">
        <div class="lr-detail-card-body">

          <div class="row g-3">
            <div class="col-md-6">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Fecha</div>
                <div class="lr-detail-value">{{ consulta['fecha_consulta'] }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Origen</div>
                <div class="lr-detail-value">{{ consulta['origen'] }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Nombre consultado</div>
                <div class="lr-detail-value">{{ consulta['nombre_consultado'] }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Detectado o Consultado en</div>
                <div class="lr-detail-value">{{ consulta['fuente'] or 'No especificado' }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Resultado</div>
                <div class="lr-detail-value">
                  {% if consulta['resultado'] == 'Sin coincidencias' %}
                    <span class="badge bg-success fs-6">{{ consulta['resultado'] }}</span>
                  {% elif consulta['resultado'] == 'Coincidencia probable' %}
                    <span class="badge bg-warning text-dark fs-6">{{ consulta['resultado'] }}</span>
                  {% else %}
                    <span class="badge bg-danger fs-6">{{ consulta['resultado'] }}</span>
                  {% endif %}
                </div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Riesgo</div>
                <div class="lr-detail-value">{{ consulta['nivel_riesgo'] }}</div>
              </div>
            </div>

            <div class="col-md-4">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Score</div>
                <div class="lr-detail-value">{{ '%.2f'|format(consulta['score_coincidencia'] or 0) }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Tipo documento</div>
                <div class="lr-detail-value">{{ consulta['tipo_documento'] or '' }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="lr-detail-box">
                <div class="lr-detail-label">Número documento</div>
                <div class="lr-detail-value">{{ consulta['numero_documento'] or '' }}</div>
              </div>
            </div>

            <div class="col-md-12">
              <div class="lr-detail-box">
                <div class="lr-detail-label">País</div>
                <div class="lr-detail-value">{{ consulta['pais'] or '' }}</div>
              </div>
            </div>
          </div>

          <div class="lr-actions mt-4">
            <a href="{{ url_for('listas_restrictivas_home') }}"
               class="btn lr-back-btn rounded-pill px-4 fw-bold">
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

      .lr-shell{
        width:96%;
        max-width:1250px;
        margin:26px auto 24px auto;
      }

      .lr-header-card{
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

      .lr-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .lr-header-overlay{
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

      .lr-header-overlay::before{
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

      .lr-header-text{
        max-width:1100px;
        width:100%;
      }

      .lr-header-text::before{
        content:"SGSI · Detalle Listas Restrictivas";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .lr-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .lr-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .lr-detail-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .lr-detail-card-body{
        padding:22px;
      }

      .lr-detail-box{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:14px 16px;
        height:100%;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .lr-detail-label{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
        margin-bottom:6px;
      }

      .lr-detail-value{
        color:#101827;
        font-size:.90rem;
        line-height:1.38;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .lr-actions{
        display:flex;
        gap:10px;
        justify-content:center;
        flex-wrap:wrap;
        margin-top:18px;
      }

      .lr-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .lr-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .lr-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .badge{
        border-radius:999px;
        font-size:.82rem;
        padding:.42rem .75rem;
        font-weight:900;
      }

      .btn.rounded-pill{
        border-radius:10px !important;
      }

      @media (max-width:992px){
        .lr-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .lr-header-card{
          min-height:88px;
        }

        .lr-title{
          font-size:1.20rem;
        }

        .lr-detail-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .lr-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .lr-header-overlay::before{
          margin:0;
        }

        .lr-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .lr-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(html, consulta=consulta))
    )

@app.route('/listas_restrictivas/eliminar/<int:consulta_id>', methods=['POST'])
@login_required
def listas_restrictivas_eliminar(consulta_id):
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and not verificar_permiso(user, "Listas Restrictivas"):
        flash("No tiene permiso para eliminar consultas de listas restrictivas.", "danger")
        return redirect(url_for('menu'))

    consulta = get_consulta_lista_by_id(consulta_id)
    if not consulta:
        flash("La consulta seleccionada no existe.", "danger")
        return redirect(url_for('listas_restrictivas_home'))

    nombre_consultado = consulta["nombre_consultado"]
    eliminado = delete_consulta_lista_by_id(consulta_id)

    if eliminado:
        registrar_log(
            session.get('username', 'Sistema'),
            f"Consulta de listas restrictivas eliminada. ID {consulta_id} - {nombre_consultado}"
        )
        flash("Consulta eliminada correctamente.", "success")
    else:
        flash("No fue posible eliminar la consulta.", "danger")

    return redirect(url_for('listas_restrictivas_home'))

DOCUMENTOS_POR_PAIS = {
    "Colombia": [
        "Cédula de ciudadanía",
        "Cédula de extranjería",
        "NIT",
        "NUIP",
        "Pasaporte",
        "PEP",
        "PPT",
        "Registro civil",
        "Tarjeta de identidad"
    ],
    "Canadá": [
        "Driver License",
        "Health Card",
        "Passport",
        "Permanent Resident Card",
        "SIN",
        "Tax Number"
    ],
    "Estados Unidos": [
        "Driver License",
        "Passport",
        "SSN",
        "State ID",
        "Tax ID"
    ],
    "México": [
        "CURP",
        "INE",
        "Pasaporte",
        "RFC"
    ],
    "Perú": [
        "Carné de extranjería",
        "DNI",
        "Pasaporte",
        "RUC"
    ],
    "Ecuador": [
        "Cédula",
        "Pasaporte",
        "RUC"
    ],
    "Chile": [
        "Cédula de identidad",
        "Pasaporte",
        "RUT"
    ],
    "Argentina": [
        "CUIL",
        "CUIT",
        "DNI",
        "Pasaporte"
    ],
    "Brasil": [
        "CPF",
        "CNPJ",
        "Passaporte",
        "RG"
    ],
    "España": [
        "DNI",
        "NIE",
        "Pasaporte"
    ],
    "Panamá": [
        "Cédula",
        "Pasaporte",
        "RUC"
    ],
    "Venezuela": [
        "Cédula de identidad",
        "Pasaporte",
        "RIF"
    ],
    "Otro": [
        "Documento nacional",
        "ID fiscal",
        "Pasaporte",
        "Otro"
    ]
}


@app.route('/listas_restrictivas/consulta', methods=['GET', 'POST'])
@login_required
def listas_restrictivas_consulta_manual():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede ejecutar consultas manuales de listas restrictivas.", "danger")
        return redirect(url_for('listas_restrictivas_home'))

    if user.role != 'admin' and not verificar_permiso(user, "Listas Restrictivas"):
        flash("No tiene permiso para consultar listas restrictivas.", "danger")
        return redirect(url_for('menu'))

    resultado = None
    nombre = ''
    tipo_documento = ''
    numero_documento = ''
    pais = 'Colombia'
    observaciones = ''

    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        tipo_documento = (request.form.get('tipo_documento') or '').strip()
        numero_documento = (request.form.get('numero_documento') or '').strip()
        pais = (request.form.get('pais') or 'Colombia').strip()
        observaciones = (request.form.get('observaciones') or '').strip()

        if not nombre:
            flash("Debe ingresar el nombre a consultar.", "danger")
            return redirect(url_for('listas_restrictivas_consulta_manual'))

        resultado = consultar_listas_restrictivas_global(
            nombre=nombre,
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            pais=pais
        )

        fuente_detectada = _resolver_fuente_detectada(resultado)

        registrar_consulta_lista_db(
            origen='manual',
            proveedor_id=None,
            nombre_consultado=nombre,
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            pais=pais,
            fuente=fuente_detectada,
            resultado=resultado["resultado"],
            nivel_riesgo=resultado["nivel_riesgo"],
            score=resultado["score"],
            detalle=resultado["detalle"],
            observaciones=observaciones,
            usuario=(user.username if user else "Sistema")
        )

        registrar_log(
            session.get('username', 'Sistema'),
            f"Consulta manual listas restrictivas: {nombre}. Detectado en: {fuente_detectada}. Resultado: {resultado['resultado']} ({resultado['nivel_riesgo']})"
        )

    html = """
    <div class="lr-shell">

      <div class="lr-header-card">
        <div class="lr-header-overlay">
          <div class="lr-header-text">
            <h3 class="lr-title m-0">Consulta Manual de Listas Restrictivas</h3>
            <div class="lr-subtitle">
              Validación consolidada contra listas externas y base local de listas restrictivas
            </div>
          </div>
        </div>
      </div>

      <div class="lr-form-card">
        <div class="lr-form-card-body">
          <form method="post" class="row g-3" id="formConsultaListas">

            <div class="col-md-6">
              <label class="lr-label">Nombre / Razón social</label>
              <input type="text"
                     name="nombre"
                     class="form-control lr-input"
                     value="{{ nombre }}"
                     required>
            </div>

            <div class="col-md-3">
              <label class="lr-label">País</label>
              <select name="pais" id="pais" class="form-select lr-input" onchange="actualizarTiposDocumento()">
                {% for p in documentos_por_pais.keys() %}
                  <option value="{{ p }}" {% if pais == p %}selected{% endif %}>{{ p }}</option>
                {% endfor %}
              </select>
            </div>

            <div class="col-md-3">
              <label class="lr-label">Tipo documento</label>
              <select name="tipo_documento" id="tipo_documento" class="form-select lr-input">
                <option value="">Seleccione...</option>
              </select>
            </div>

            <div class="col-md-4">
              <label class="lr-label">Número documento</label>
              <input type="text"
                     name="numero_documento"
                     class="form-control lr-input"
                     value="{{ numero_documento }}">
            </div>

            <div class="col-12">
              <div class="lr-actions">
                <button type="submit" class="btn btn-primary rounded-pill px-4 fw-bold" id="btnConsultarListas">
                  Consultar
                </button>

                <a href="{{ url_for('listas_restrictivas_home') }}"
                   class="btn lr-back-btn rounded-pill px-4 fw-bold">
                  Volver
                </a>
              </div>
            </div>

          </form>
        </div>
      </div>

      {% if resultado %}
      <div class="lr-result-card">
        <div class="lr-result-card-body">

          <div class="row g-3 mb-3">
            <div class="col-md-3">
              <div class="lr-kpi-card">
                <div class="lr-kpi-label">Detectado o Consultado en</div>
                <div class="lr-kpi-value-sm">{{ _resolver_fuente_detectada(resultado) }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="lr-kpi-card">
                <div class="lr-kpi-label">Resultado</div>
                <div class="mt-2">
                  {% if resultado['resultado'] == 'Sin coincidencias' %}
                    <span class="badge bg-success fs-6">{{ resultado['resultado'] }}</span>
                  {% elif resultado['resultado'] == 'Coincidencia probable' %}
                    <span class="badge bg-warning text-dark fs-6">{{ resultado['resultado'] }}</span>
                  {% else %}
                    <span class="badge bg-danger fs-6">{{ resultado['resultado'] }}</span>
                  {% endif %}
                </div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="lr-kpi-card">
                <div class="lr-kpi-label">Nivel de riesgo</div>
                <div class="lr-kpi-value-sm">{{ resultado['nivel_riesgo'] }}</div>
              </div>
            </div>

            <div class="col-md-3">
              <div class="lr-kpi-card">
                <div class="lr-kpi-label">Score</div>
                <div class="lr-kpi-value">{{ '%.2f'|format(resultado['score'] or 0) }}</div>
              </div>
            </div>
          </div>

          {% if resultado['detalle'] %}
          <div class="lr-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered align-middle lr-table mb-0">
                <thead>
                  <tr class="text-center">
                    <th>Fuente</th>
                    <th>Nombre</th>
                    <th>Documento</th>
                    <th>País</th>
                    <th>Categoría</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {% for d in resultado['detalle'] %}
                  <tr>
                    <td>{{ d['fuente'] }}</td>
                    <td>{{ d['nombre'] }}</td>
                    <td>{{ d['numero_documento'] or '' }}</td>
                    <td>{{ d['pais'] or '' }}</td>
                    <td>{{ d['categoria'] or '' }}</td>
                    <td class="text-center fw-bold">{{ '%.2f'|format(d['score'] or 0) }}</td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>
          {% else %}
          <div class="alert alert-info mb-0">
            No se encontraron coincidencias detalladas para mostrar.
          </div>
          {% endif %}

        </div>
      </div>
      {% endif %}

    </div>

    <!-- POPUP DE PROGRESO -->
    <div class="lr-loading-overlay" id="lrLoadingOverlay" aria-hidden="true">
      <div class="lr-loading-modal">
        <div class="lr-loading-icon-wrap">
          <div class="lr-loading-spinner"></div>
        </div>

        <div class="lr-loading-title">Consultando listas restrictivas</div>
        <div class="lr-loading-subtitle">
          Estamos validando coincidencias en listas externas y base local. No cierre esta ventana.
        </div>

        <div class="lr-progress">
          <div class="lr-progress-bar" id="lrProgressBar"></div>
        </div>

        <div class="lr-progress-text" id="lrProgressText">Iniciando consulta...</div>
      </div>
    </div>

    <script>
      const DOCUMENTOS_POR_PAIS = {{ documentos_por_pais | tojson }};
      const tipoDocumentoActual = {{ tipo_documento | tojson }};

      function actualizarTiposDocumento() {
        const paisSelect = document.getElementById("pais");
        const tipoDocumentoSelect = document.getElementById("tipo_documento");

        if (!paisSelect || !tipoDocumentoSelect) return;

        const pais = paisSelect.value;
        const opciones = DOCUMENTOS_POR_PAIS[pais] || DOCUMENTOS_POR_PAIS["Otro"] || [];

        tipoDocumentoSelect.innerHTML = '<option value="">Seleccione...</option>';

        opciones.forEach(function(opcion) {
          const opt = document.createElement("option");
          opt.value = opcion;
          opt.textContent = opcion;

          if (tipoDocumentoActual && tipoDocumentoActual === opcion) {
            opt.selected = true;
          }

          tipoDocumentoSelect.appendChild(opt);
        });
      }

      function mostrarPopupConsulta() {
        const overlay = document.getElementById("lrLoadingOverlay");
        const bar = document.getElementById("lrProgressBar");
        const text = document.getElementById("lrProgressText");

        if (!overlay || !bar || !text) return;

        overlay.classList.add("show");
        overlay.setAttribute("aria-hidden", "false");

        let progreso = 8;
        bar.style.width = progreso + "%";
        text.textContent = "Preparando parámetros de consulta...";

        const etapas = [
          { p: 20, t: "Validando información ingresada..." },
          { p: 38, t: "Consultando listas locales..." },
          { p: 56, t: "Consultando listas externas..." },
          { p: 74, t: "Analizando coincidencias encontradas..." },
          { p: 88, t: "Consolidando resultado final..." },
          { p: 96, t: "Finalizando consulta..." }
        ];

        let idx = 0;

        window.lrConsultaInterval = setInterval(() => {
          if (idx < etapas.length) {
            progreso = etapas[idx].p;
            bar.style.width = progreso + "%";
            text.textContent = etapas[idx].t;
            idx++;
          } else {
            clearInterval(window.lrConsultaInterval);
          }
        }, 700);
      }

      document.addEventListener("DOMContentLoaded", function() {
        actualizarTiposDocumento();

        const form = document.getElementById("formConsultaListas");
        const btn = document.getElementById("btnConsultarListas");

        if (form && btn) {
          form.addEventListener("submit", function(e) {
            const nombreInput = form.querySelector('input[name="nombre"]');
            if (!nombreInput || !nombreInput.value.trim()) {
              return;
            }

            btn.disabled = true;
            btn.innerHTML = 'Consultando...';
            mostrarPopupConsulta();
          });
        }
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

      .lr-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }

      .lr-header-card{
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

      .lr-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .lr-header-overlay{
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

      .lr-header-overlay::before{
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

      .lr-header-text{
        max-width:1200px;
        width:100%;
      }

      .lr-header-text::before{
        content:"SGSI · Consulta Listas Restrictivas";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .lr-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .lr-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .lr-form-card,
      .lr-result-card,
      .lr-kpi-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        margin-bottom:16px;
      }

      .lr-form-card-body,
      .lr-result-card-body{
        padding:22px;
      }

      .lr-label{
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

      .lr-input{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }

      .lr-input:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }

      .lr-actions{
        display:flex;
        gap:10px;
        justify-content:center;
        flex-wrap:wrap;
        margin-top:14px;
      }

      .lr-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .lr-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .lr-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .lr-kpi-card{
        padding:16px;
        text-align:center;
        height:100%;
      }

      .lr-kpi-label{
        color:#475569;
        font-weight:900;
        font-size:.72rem;
        text-transform:uppercase;
        letter-spacing:.35px;
        margin-bottom:8px;
      }

      .lr-kpi-value{
        font-size:1.85rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1.1;
      }

      .lr-kpi-value-sm{
        font-size:.92rem;
        font-weight:900;
        color:#0b1220;
        word-break:break-word;
      }

      .lr-table-wrap,
      .table-responsive{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .lr-table{
        margin-bottom:0;
      }

      .lr-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border:none !important;
        font-size:.78rem;
        padding:9px 8px;
      }

      .lr-table th,
      .lr-table td{
        vertical-align:middle;
        font-size:.82rem;
        padding:9px 8px;
        word-break:break-word;
      }

      .lr-table td{
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .lr-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .lr-table tbody tr:hover td{
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

      .lr-loading-overlay{
        position:fixed;
        inset:0;
        background:rgba(15,23,42,.48);
        backdrop-filter:blur(6px);
        display:flex;
        align-items:center;
        justify-content:center;
        z-index:9999;
        opacity:0;
        visibility:hidden;
        transition:all .25s ease;
      }

      .lr-loading-overlay.show{
        opacity:1;
        visibility:visible;
      }

      .lr-loading-modal{
        width:min(92vw,520px);
        background:rgba(255,255,255,.96);
        border-radius:24px;
        box-shadow:0 24px 60px rgba(0,0,0,.28);
        padding:28px 24px 24px 24px;
        text-align:center;
        border:1px solid rgba(255,255,255,.7);
      }

      .lr-loading-icon-wrap{
        display:flex;
        justify-content:center;
        margin-bottom:14px;
      }

      .lr-loading-spinner{
        width:54px;
        height:54px;
        border-radius:50%;
        border:4px solid rgba(63,134,214,.18);
        border-top-color:#3f86d6;
        animation:lrSpin .9s linear infinite;
      }

      @keyframes lrSpin{
        to{ transform:rotate(360deg); }
      }

      .lr-loading-title{
        font-size:1.15rem;
        font-weight:950;
        color:#0f172a;
        margin-bottom:6px;
      }

      .lr-loading-subtitle{
        color:#475569;
        font-size:.94rem;
        margin-bottom:18px;
      }

      .lr-progress{
        width:100%;
        height:14px;
        background:#e5eefb;
        border-radius:999px;
        overflow:hidden;
        box-shadow:inset 0 1px 3px rgba(0,0,0,.08);
      }

      .lr-progress-bar{
        width:0%;
        height:100%;
        background:linear-gradient(90deg,#2f6fb6 0%,#3f86d6 55%,#5aa3ea 100%);
        border-radius:999px;
        transition:width .45s ease;
      }

      .lr-progress-text{
        margin-top:12px;
        color:#334155;
        font-size:.92rem;
        font-weight:700;
      }

      @media (max-width:992px){
        .lr-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .lr-header-card{
          min-height:88px;
        }

        .lr-title{
          font-size:1.20rem;
        }

        .lr-form-card-body,
        .lr-result-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .lr-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .lr-header-overlay::before{
          margin:0;
        }

        .lr-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .lr-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            html,
            resultado=resultado,
            nombre=nombre,
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            pais=pais,
            observaciones=observaciones,
            documentos_por_pais=DOCUMENTOS_POR_PAIS,
            _resolver_fuente_detectada=_resolver_fuente_detectada
        ))
    )

@app.route('/listas_restrictivas/base', methods=['GET', 'POST'])
@login_required
def listas_restrictivas_base():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin':
        flash("Solo el administrador puede gestionar la base de listas restrictivas.", "danger")
        return redirect(url_for('menu'))

    if request.method == 'POST':
        archivo_fuente = request.files.get('archivo_fuente')
        if archivo_fuente and archivo_fuente.filename:
            try:
                insertados, omitidos = cargar_fuente_lista_desde_archivo(
                    archivo_fuente,
                    fuente_default="Carga Archivo"
                )
                flash(f"Archivo procesado correctamente. Insertados: {insertados}. Omitidos: {omitidos}.", "success")
                return redirect(url_for('listas_restrictivas_base'))
            except Exception as e:
                flash(f"Error cargando archivo plano: {str(e)}", "danger")
                return redirect(url_for('listas_restrictivas_base'))
        fuente = (request.form.get('fuente') or '').strip() or 'Lista Local'
        nombre = (request.form.get('nombre') or '').strip()
        alias = (request.form.get('alias') or '').strip()
        tipo_documento = (request.form.get('tipo_documento') or '').strip()
        numero_documento = (request.form.get('numero_documento') or '').strip()
        pais = (request.form.get('pais') or '').strip()
        categoria = (request.form.get('categoria') or '').strip()
        observaciones = (request.form.get('observaciones') or '').strip()

        if not nombre:
            flash("El nombre del registro es obligatorio.", "danger")
            return redirect(url_for('listas_restrictivas_base'))

        conn = get_listas_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO listas_restrictivas_fuente (
                fuente, nombre, alias, tipo_documento, numero_documento, pais,
                categoria, observaciones, activo, fecha_actualizacion
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Sí', ?)
        """, (
            fuente, nombre, alias, tipo_documento, numero_documento, pais,
            categoria, observaciones, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()

        flash("Registro agregado a la base independiente de listas restrictivas.", "success")
        return redirect(url_for('listas_restrictivas_base'))

    conn = get_listas_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM listas_restrictivas_fuente
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()

    html = """
    <div class="lr-shell">

      <!-- HEADER -->
      <div class="lr-header-card">
        <div class="lr-header-overlay">
          <div class="lr-header-text">
            <h3 class="lr-title m-0">Base de Listas Restrictivas</h3>
            <div class="lr-subtitle">
              Administración de listas locales + carga masiva por archivo plano
            </div>
          </div>
        </div>
      </div>

      <!-- FORMULARIO GENERAL -->
      <form method="post" enctype="multipart/form-data" class="row g-3">

        <!-- CARGA ARCHIVO -->
        <div class="col-12">
          <div class="card shadow-sm border-0 rounded-4">
            <div class="card-body">
              <h5 class="fw-bold mb-2">📂 Carga por archivo plano</h5>

              <p class="text-muted mb-2">
                Puede cargar archivos <strong>.txt</strong> o <strong>.csv</strong>
              </p>

              <p class="text-muted small mb-2">
                TXT: <code>nombre|documento|pais|categoria</code>
              </p>

              <p class="text-muted small mb-3">
                CSV: columnas → nombre, alias, tipo_documento, numero_documento, pais, categoria, observaciones
              </p>

              <input type="file" name="archivo_fuente" class="form-control" accept=".txt,.csv">
            </div>
          </div>
        </div>

        <!-- FORMULARIO MANUAL -->
        <div class="col-12">
          <div class="card shadow-sm border-0 rounded-4">
            <div class="card-body">

              <h5 class="fw-bold mb-3">➕ Registro manual</h5>

              <div class="row g-3">
                <div class="col-md-3">
                  <label class="form-label fw-bold">Fuente</label>
                  <input name="fuente" class="form-control">
                </div>

                <div class="col-md-5">
                  <label class="form-label fw-bold">Nombre</label>
                  <input name="nombre" class="form-control" required>
                </div>

                <div class="col-md-4">
                  <label class="form-label fw-bold">Alias</label>
                  <input name="alias" class="form-control">
                </div>

                <div class="col-md-3">
                  <label class="form-label fw-bold">Tipo documento</label>
                  <input name="tipo_documento" class="form-control">
                </div>

                <div class="col-md-3">
                  <label class="form-label fw-bold">Número documento</label>
                  <input name="numero_documento" class="form-control">
                </div>

                <div class="col-md-3">
                  <label class="form-label fw-bold">País</label>
                  <input name="pais" class="form-control">
                </div>

                <div class="col-md-3">
                  <label class="form-label fw-bold">Categoría</label>
                  <input name="categoria" class="form-control">
                </div>

                <div class="col-12">
                  <label class="form-label fw-bold">Observaciones</label>
                  <textarea name="observaciones" class="form-control" rows="2"></textarea>
                </div>

                <div class="col-12 text-center">
                  <button type="submit" class="btn btn-danger rounded-pill px-4 fw-bold">
                    Guardar
                  </button>

                  <a href="{{ url_for('listas_restrictivas_home') }}"
                     class="btn btn-light rounded-pill px-4 fw-bold">
                    Volver
                  </a>
                </div>
              </div>

            </div>
          </div>
        </div>

      </form>

      <!-- TABLA -->
      <div class="card shadow-sm border-0 rounded-4 mt-3">
        <div class="card-body">

          <h5 class="fw-bold mb-3">📊 Base actual</h5>

          <div class="table-responsive lr-table-container">
            <table class="table table-bordered align-middle lr-table">
              <thead>
                <tr class="text-center">
                  <th>ID</th>
                  <th>Fuente</th>
                  <th>Nombre</th>
                  <th>Documento</th>
                  <th>País</th>
                  <th>Categoría</th>
                  <th>Estado</th>
                  <th>Actualización</th>
                </tr>
              </thead>

              <tbody>
                {% for r in rows %}
                <tr>
                  <td>{{ r['id'] }}</td>
                  <td>{{ r['fuente'] }}</td>
                  <td>{{ r['nombre'] }}</td>
                  <td>{{ r['numero_documento'] or '' }}</td>
                  <td>{{ r['pais'] or '' }}</td>
                  <td>{{ r['categoria'] or '' }}</td>
                  <td>
                    {% if r['activo'] == 'Sí' %}
                      <span class="badge bg-success">Activo</span>
                    {% else %}
                      <span class="badge bg-secondary">Inactivo</span>
                    {% endif %}
                  </td>
                  <td>{{ r['fecha_actualizacion'] or '' }}</td>
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

      .lr-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }

      .lr-header-card{
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

      .lr-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .lr-header-overlay{
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

      .lr-header-overlay::before{
        content:"📚";
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

      .lr-header-text,
      .lr-header-overlay > div{
        max-width:1200px;
        width:100%;
      }

      .lr-header-text::before,
      .lr-header-overlay > div::before{
        content:"SGSI · Base Local Listas Restrictivas";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .lr-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .lr-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .card-body{
        padding:18px;
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

      .lr-table-container{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .lr-table-container::-webkit-scrollbar{
        width:10px;
        height:10px;
      }

      .lr-table-container::-webkit-scrollbar-thumb{
        background:#2f7fd1;
        border-radius:10px;
      }

      .lr-table-container::-webkit-scrollbar-track{
        background:#edf4ff;
      }

      .lr-table{
        margin-bottom:0;
      }

      .lr-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border:none !important;
        font-size:.78rem;
        padding:9px 8px;
      }

      .lr-table th,
      .lr-table td{
        vertical-align:middle;
        font-size:.82rem;
        padding:9px 8px;
        word-break:break-word;
      }

      .lr-table td{
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .lr-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .lr-table tbody tr:hover{
        background:#eef6ff;
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .btn,
      .btn.rounded-pill{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      @media (max-width:992px){
        .lr-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .lr-header-card{
          min-height:88px;
        }

        .lr-title{
          font-size:1.20rem;
        }

        .card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .lr-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .lr-header-overlay::before{
          margin:0;
        }

        .lr-header-text::before,
        .lr-header-overlay > div::before{
          margin-left:auto;
          margin-right:auto;
        }

        .btn{
          width:100%;
        }
      }
    </style>
    """

    return render_template_string(BASE, content=Markup(render_template_string(html, rows=rows)))

@app.route('/listas_restrictivas/proveedor/<int:proveedor_id>/consultar', methods=['POST'])
@login_required
def listas_restrictivas_consultar_proveedor(proveedor_id):
    user = User.query.get(session.get('user_id'))
    proveedor = ProveedorEvaluacion.query.get_or_404(proveedor_id)

    if user.role == 'auditor':
        flash("El rol Auditor no puede ejecutar consultas de listas restrictivas.", "danger")
        return redirect(url_for('proveedores_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Listas Restrictivas"):
        flash("No tiene permiso para consultar listas restrictivas.", "danger")
        return redirect(url_for('menu'))

    nombre = (proveedor.nombre_proveedor or '').strip()
    pais = (proveedor.pais_origen or proveedor.pais_servicio or '').strip()
    tipo_documento = ''
    numero_documento = ''

    if not nombre:
        flash("El proveedor no tiene nombre para realizar la consulta.", "danger")
        return redirect(url_for('proveedores_edit', id=proveedor.id))

    resultado = consultar_listas_restrictivas_global(
        nombre=nombre,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        pais=pais
    )

    fuente_detectada = _resolver_fuente_detectada(resultado)

    registrar_consulta_lista_db(
        origen='proveedor',
        proveedor_id=proveedor.id,
        nombre_consultado=nombre,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        pais=pais,
        fuente=fuente_detectada,
        resultado=resultado["resultado"],
        nivel_riesgo=resultado["nivel_riesgo"],
        score=resultado["score"],
        detalle=resultado["detalle"],
        observaciones="Consulta ejecutada desde proveedor hacia módulo independiente de listas restrictivas",
        usuario=(user.username if user else "Sistema")
    )

    registrar_log(
        session.get('username', 'Sistema'),
        f"Consulta proveedor a listas restrictivas. Proveedor {proveedor.id} - {nombre}. Detectado en: {fuente_detectada}. Resultado: {resultado['resultado']} ({resultado['nivel_riesgo']})"
    )

    return redirect(url_for('listas_restrictivas_historial_proveedor', proveedor_id=proveedor.id))


@app.route('/listas_restrictivas/proveedor/<int:proveedor_id>/historial', methods=['GET'])
@login_required
def listas_restrictivas_historial_proveedor(proveedor_id):
    user = User.query.get(session.get('user_id'))
    proveedor = ProveedorEvaluacion.query.get_or_404(proveedor_id)

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Listas Restrictivas"):
        flash("No tiene permiso para ver el historial de listas restrictivas del proveedor.", "danger")
        return redirect(url_for('menu'))

    historial = get_historial_lista_proveedor(proveedor.id)
    estado = get_estado_lista_proveedor(proveedor.id)

    html = """
    <div class="provlist-shell">
      <div class="provlist-header-card">
        <div class="provlist-header-overlay">
          <div class="provlist-header-text">
            <h3 class="provlist-title m-0">🚨 Historial de Listas Restrictivas del Proveedor</h3>
            <div class="provlist-subtitle">
              Proveedor: <strong>{{ proveedor.nombre_proveedor }}</strong>
            </div>
          </div>
        </div>
      </div>

      <div class="provlist-actions">
        <a href="{{ url_for('proveedores_matriz') }}" class="btn rounded-pill px-4 fw-bold provlist-back-btn">
          ⬅ Volver a la Matriz
        </a>
        <a href="{{ url_for('proveedores_detalle', id=proveedor.id) }}" class="btn btn-primary rounded-pill px-4 fw-bold">
          Ver detalle del proveedor
        </a>
        <a href="{{ url_for('listas_restrictivas_home') }}" class="btn btn-danger rounded-pill px-4 fw-bold">
          Ir al módulo de listas restrictivas
        </a>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-md-4">
          <div class="card shadow-sm border-0 rounded-4 h-100">
            <div class="card-body text-center">
              <div class="text-muted">Último resultado</div>
              <div class="mt-2">
                {% if estado and estado['resultado'] == 'Sin coincidencias' %}
                  <span class="badge bg-success fs-6">{{ estado['resultado'] }}</span>
                {% elif estado and estado['resultado'] == 'Coincidencia probable' %}
                  <span class="badge bg-warning text-dark fs-6">{{ estado['resultado'] }}</span>
                {% elif estado and estado['resultado'] == 'Coincidencia exacta' %}
                  <span class="badge bg-danger fs-6">{{ estado['resultado'] }}</span>
                {% else %}
                  <span class="badge bg-secondary fs-6">Sin consultar</span>
                {% endif %}
              </div>
            </div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="card shadow-sm border-0 rounded-4 h-100">
            <div class="card-body text-center">
              <div class="text-muted">Nivel de riesgo</div>
              <div class="display-6 fw-bold text-danger">{{ estado['riesgo'] if estado else '—' }}</div>
            </div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="card shadow-sm border-0 rounded-4 h-100">
            <div class="card-body text-center">
              <div class="text-muted">Último score</div>
              <div class="display-6 fw-bold text-primary">
                {{ '%.2f'|format(estado['score'] or 0) if estado else '0.00' }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="provlist-card">
        <div class="provlist-card-body">
          {% if historial %}
          <div class="table-responsive">
            <table class="table table-bordered align-middle provlist-table">
              <thead>
                <tr class="text-center">
                  <th>Fecha</th>
                  <th>Nombre consultado</th>
                  <th>Fuente</th>
                  <th>Resultado</th>
                  <th>Riesgo</th>
                  <th>Score</th>
                  <th>Usuario</th>
                  <th>Detalle</th>
                </tr>
              </thead>
              <tbody>
                {% for h in historial %}
                <tr>
                  <td>{{ h['fecha_consulta'] }}</td>
                  <td>{{ h['nombre_consultado'] }}</td>
                  <td>{{ h['fuente'] }}</td>
                  <td>
                    {% if h['resultado'] == 'Sin coincidencias' %}
                      <span class="badge bg-success">{{ h['resultado'] }}</span>
                    {% elif h['resultado'] == 'Coincidencia probable' %}
                      <span class="badge bg-warning text-dark">{{ h['resultado'] }}</span>
                    {% else %}
                      <span class="badge bg-danger">{{ h['resultado'] }}</span>
                    {% endif %}
                  </td>
                  <td>{{ h['nivel_riesgo'] }}</td>
                  <td>{{ '%.2f'|format(h['score_coincidencia'] or 0) }}</td>
                  <td>{{ h['usuario'] or 'Sistema' }}</td>
                  <td style="min-width:320px;">
                    <pre style="white-space:pre-wrap;margin:0;">{{ h['detalle_json'] }}</pre>
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
          {% else %}
            <div class="alert alert-info mb-0">
              No hay consultas registradas para este proveedor.
            </div>
          {% endif %}
        </div>
      </div>
    </div>

    <style>
      .provlist-shell{width:96%;max-width:1700px;margin:10px auto 30px auto;}
      .provlist-header-card{
        background: linear-gradient(135deg, #b91c1c 0%, #b91c1c 55%, #ef4444 100%);
        min-height: 88px; border-radius: 18px; overflow: hidden;
        box-shadow: 0 12px 28px rgba(0,0,0,.22); margin-bottom: 14px;
      }
      .provlist-header-overlay{
        width:100%;height:100%;display:flex;align-items:center;justify-content:center;
        text-align:center;padding:10px 22px;background:rgba(0,0,0,.08);
      }
      .provlist-title{color:#fff;font-weight:900;font-size:1.35rem;}
      .provlist-subtitle{color:rgba(255,255,255,.96);font-size:.86rem;margin-top:4px;}
      .provlist-card{
        background: rgba(248,252,255,.96);
        border-radius: 18px; backdrop-filter: blur(6px);
        box-shadow: 0 10px 24px rgba(0,0,0,.16);
      }
      .provlist-card-body{padding:16px;}
      .provlist-actions{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-bottom:14px;}
      .provlist-back-btn{background:#fff;color:#000;border:2px solid #fff;}
      .provlist-table thead th{
        background:#fee2e2 !important;
        color:#7f1d1d;
        font-weight:800;
        text-align:center;
        vertical-align:middle;
      }
    </style>
    """

    inner = render_template_string(
        html,
        proveedor=proveedor,
        historial=historial,
        estado=estado
    )
    return render_template_string(BASE, content=Markup(inner))

# ==========================================================================================================================================
#                                                   Fin Módulo de Listas Restrictivas
# ==========================================================================================================================================

# ==========================================================================================================================================
#                  MODULO SCORECARD PROVEEDORES INDEPENDIENTE - DNS HEALTH / IP REPUTATION / ESCANEO KALI PROPIO
# ==========================================================================================================================================


try:
    import dns.resolver
except Exception:
    dns = None

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception:
    Fernet = None
    InvalidToken = Exception

try:
    from leakcheck_api import LeakCheckAPI_v2
except Exception:
    LeakCheckAPI_v2 = None


SCORECARD_DB_PATH = os.path.join(app.instance_path, "scorecard_proveedores.db")
SCORECARD_UPLOAD_DIR = os.path.join(app.instance_path, "scorecard_outputs")
os.makedirs(SCORECARD_UPLOAD_DIR, exist_ok=True)


# ============================================================
# DB INDEPENDIENTE SCORECARD
# ============================================================

def get_scorecard_db_connection():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(SCORECARD_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_scorecard_db():
    os.makedirs(app.instance_path, exist_ok=True)

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proveedor_id INTEGER,
            proveedor_nombre TEXT,
            dominio TEXT NOT NULL,
            ip_resuelta TEXT,
            score_dns REAL DEFAULT 0,
            score_ip REAL DEFAULT 0,
            score_kali REAL DEFAULT 0,
            score_incidentes REAL DEFAULT 100,
            score_darkweb REAL DEFAULT 100,
            score_total REAL DEFAULT 0,
            nivel_riesgo TEXT,
            estado TEXT DEFAULT 'pendiente',
            progress_pct INTEGER DEFAULT 0,
            current_stage TEXT,
            current_tool TEXT,
            modo_kali TEXT,
            herramientas_json TEXT,
            resumen_json TEXT,
            salida_consola TEXT,
            error_detalle TEXT,
            usuario TEXT,
            fecha_ejecucion TEXT NOT NULL,
            fecha_inicio TEXT,
            fecha_fin TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            categoria TEXT NOT NULL,
            herramienta TEXT,
            control TEXT,
            estado TEXT,
            riesgo TEXT,
            severidad TEXT,
            score REAL DEFAULT 0,
            evidencia TEXT,
            recomendacion TEXT,
            archivo_salida TEXT,
            detalle_json TEXT,
            fecha TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_outputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            herramienta TEXT NOT NULL,
            comando TEXT,
            archivo_salida TEXT,
            exit_code INTEGER,
            duracion_segundos REAL DEFAULT 0,
            fecha TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            proveedor_id INTEGER,
            proveedor_nombre TEXT,
            dominio TEXT,
            fuente TEXT,
            titulo TEXT,
            url TEXT,
            fecha_incidente TEXT,
            severidad TEXT,
            descripcion TEXT,
            detalle_json TEXT,
            fecha_registro TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_darkweb_exposures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            proveedor_id INTEGER,
            proveedor_nombre TEXT,
            dominio TEXT,
            fuente TEXT,
            tipo_exposicion TEXT,
            indicador TEXT,
            severidad TEXT,
            fecha TEXT,
            evidencia TEXT,
            recomendacion TEXT,
            url TEXT,
            credencial_confirmada INTEGER DEFAULT 0,
            detalle_json TEXT,
            fecha_registro TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_parametros (
            clave TEXT PRIMARY KEY,
            valor REAL NOT NULL,
            descripcion TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_risk_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            score_min REAL NOT NULL DEFAULT 0,
            color_bootstrap TEXT DEFAULT 'secondary',
            orden INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1,
            fecha_creacion TEXT NOT NULL
        )
    """)

    parametros_default = [
        ("peso_dns", 20, "Peso DNS Health"),
        ("peso_ip", 15, "Peso IP Reputation"),
        ("peso_kali", 35, "Peso Kali Linux"),
        ("peso_incidentes", 15, "Peso Incidentes/Brechas"),
        ("peso_darkweb", 15, "Peso Dark Web / Exposure Intelligence"),
        ("darkweb_score_sin_hallazgos", 100, "Sin hallazgos"),
        ("darkweb_score_1_2", 80, "1 a 2 hallazgos"),
        ("darkweb_score_3_5", 60, "3 a 5 hallazgos"),
        ("darkweb_score_mas_5", 40, "Más de 5 hallazgos"),
        ("darkweb_score_credenciales_confirmadas", 20, "Credenciales confirmadas"),
    ]

    for clave, valor, descripcion in parametros_default:
        cur.execute("""
            INSERT OR IGNORE INTO scorecard_parametros (clave, valor, descripcion)
            VALUES (?, ?, ?)
        """, (clave, valor, descripcion))

    cur.execute("SELECT COUNT(*) AS total FROM scorecard_risk_levels")
    total_risk_levels = cur.fetchone()["total"]

    if total_risk_levels == 0:
        niveles_default = [
            ("Bajo", 85, "success", 1),
            ("Medio", 70, "warning text-dark", 2),
            ("Alto", 50, "danger", 3),
            ("Crítico", 0, "dark", 4),
        ]

        for nombre, score_min, color_bootstrap, orden in niveles_default:
            cur.execute("""
                INSERT INTO scorecard_risk_levels
                (nombre, score_min, color_bootstrap, orden, activo, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                nombre,
                score_min,
                color_bootstrap,
                orden,
                1,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

    conn.commit()

    # Migración ligera si la base ya existía
    cur.execute("PRAGMA table_info(scorecard_runs)")
    cols = [r["name"] for r in cur.fetchall()]

    if "score_incidentes" not in cols:
        cur.execute("ALTER TABLE scorecard_runs ADD COLUMN score_incidentes REAL DEFAULT 100")
        conn.commit()

    if "score_darkweb" not in cols:
        cur.execute("ALTER TABLE scorecard_runs ADD COLUMN score_darkweb REAL DEFAULT 100")
        conn.commit()

    conn.close()


init_scorecard_db()

def init_scorecard_enterprise_api_db():
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proveedor TEXT NOT NULL UNIQUE,
            api_key_encrypted TEXT,
            activo INTEGER DEFAULT 0,
            notas TEXT,
            actualizado_por TEXT,
            fecha_actualizacion TEXT NOT NULL
        )
    """)

    proveedores_default = [
        ("leakcheck", "LeakCheck API"),
        ("hibp", "Have I Been Pwned API"),
        ("shodan", "Shodan API"),
    ]

    for proveedor, notas in proveedores_default:
        cur.execute("""
            INSERT OR IGNORE INTO scorecard_api_keys
            (proveedor, api_key_encrypted, activo, notas, actualizado_por, fecha_actualizacion)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            proveedor,
            "",
            0,
            notas,
            "Sistema",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    conn.commit()
    conn.close()


# Ejecutar una vez al cargar el módulo.
init_scorecard_enterprise_api_db()


# ============================================================
# PERMISOS
# ============================================================

def scorecard_user_permiso():
    user = User.query.get(session.get("user_id"))

    if not user:
        return None, False, False

    read_only = user.role == "auditor"

    if user.role != "admin" and user.role != "auditor" and not verificar_permiso(user, "Registro de Proveedores"):
        return user, False, read_only

    return user, True, read_only


# ============================================================
# UTILIDADES BASE
# ============================================================

def limpiar_dominio_scorecard(valor):
    valor = (valor or "").strip().lower()
    valor = re.sub(r"^https?://", "", valor)
    valor = valor.split("/")[0]
    valor = valor.split(":")[0]
    valor = valor.strip()
    return valor


def scorecard_get_crypto_master_key():
    """
    Genera una llave Fernet derivada del SECRET_KEY de Flask.
    No usa variables de entorno.

    Recomendación:
    - Asegúrate de tener app.secret_key estable en producción.
    - Si cambias app.secret_key, las API keys cifradas antes no se podrán descifrar.
    """
    if Fernet is None:
        return None

    import base64
    import hashlib

    raw_secret = str(getattr(app, "secret_key", "") or "GRAC_SCORECARD_LOCAL_SECRET").encode("utf-8")
    salt = b"GRAC_SCORECARD_API_KEYS_V1"
    digest = hashlib.sha256(raw_secret + salt).digest()
    return base64.urlsafe_b64encode(digest)


def scorecard_encrypt_api_key(api_key):
    api_key = (api_key or "").strip()

    if not api_key:
        return ""

    key = scorecard_get_crypto_master_key()

    if not key:
        # Fallback controlado si cryptography no está instalada.
        # No recomendado, pero evita romper el sistema.
        return "plain:" + api_key

    f = Fernet(key)
    return f.encrypt(api_key.encode("utf-8")).decode("utf-8")


def scorecard_decrypt_api_key(api_key_encrypted):
    api_key_encrypted = (api_key_encrypted or "").strip()

    if not api_key_encrypted:
        return ""

    if api_key_encrypted.startswith("plain:"):
        return api_key_encrypted.replace("plain:", "", 1)

    key = scorecard_get_crypto_master_key()

    if not key:
        return ""

    try:
        f = Fernet(key)
        return f.decrypt(api_key_encrypted.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""
    except Exception:
        return ""


def scorecard_mask_api_key(api_key):
    api_key = (api_key or "").strip()

    if not api_key:
        return "No configurada"

    if len(api_key) <= 8:
        return api_key[:2] + "***"

    return api_key[:4] + "****" + api_key[-4:]


def scorecard_get_enterprise_api_key(proveedor):
    proveedor = (proveedor or "").strip().lower()

    try:
        conn = get_scorecard_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT api_key_encrypted, activo
            FROM scorecard_api_keys
            WHERE proveedor = ?
            LIMIT 1
        """, (proveedor,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return ""

        if int(row["activo"] or 0) != 1:
            return ""

        return scorecard_decrypt_api_key(row["api_key_encrypted"])

    except Exception:
        return ""


def scorecard_api_status():
    proveedores = ["leakcheck", "hibp", "shodan"]
    estado = {}

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    for proveedor in proveedores:
        cur.execute("""
            SELECT *
            FROM scorecard_api_keys
            WHERE proveedor = ?
            LIMIT 1
        """, (proveedor,))
        row = cur.fetchone()

        if row:
            api_key = scorecard_decrypt_api_key(row["api_key_encrypted"])
            estado[proveedor] = {
                "activo": int(row["activo"] or 0) == 1,
                "configurada": bool(api_key),
                "mask": scorecard_mask_api_key(api_key),
                "fecha": row["fecha_actualizacion"],
                "notas": row["notas"] or ""
            }
        else:
            estado[proveedor] = {
                "activo": False,
                "configurada": False,
                "mask": "No configurada",
                "fecha": "",
                "notas": ""
            }

    conn.close()
    return estado


def scorecard_guardar_api_key(proveedor, api_key, activo, usuario):
    proveedor = (proveedor or "").strip().lower()
    api_key = (api_key or "").strip()

    encrypted = scorecard_encrypt_api_key(api_key) if api_key else ""

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_api_keys
        (proveedor, api_key_encrypted, activo, notas, actualizado_por, fecha_actualizacion)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(proveedor) DO UPDATE SET
            api_key_encrypted = excluded.api_key_encrypted,
            activo = excluded.activo,
            actualizado_por = excluded.actualizado_por,
            fecha_actualizacion = excluded.fecha_actualizacion
    """, (
        proveedor,
        encrypted,
        1 if activo and api_key else 0,
        proveedor,
        usuario,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def scorecard_mask_email(email):
    email = (email or "").strip()

    if not email:
        return ""

    if "@" not in email:
        return email[:2] + "***" if len(email) > 2 else "***"

    user, domain = email.split("@", 1)
    if len(user) <= 2:
        user_mask = user[:1] + "***"
    else:
        user_mask = user[:2] + "***"

    return f"{user_mask}@{domain}"


def scorecard_mask_indicator(value):
    value = str(value or "").strip()

    if not value:
        return ""

    if "@" in value:
        return scorecard_mask_email(value)

    if len(value) <= 8:
        return value[:2] + "***"

    return value[:4] + "***" + value[-3:]


def scorecard_api_error_item(fuente, detalle):
    """
    Retorna item informativo.
    Este tipo NO debe bajar score.
    """
    return {
        "fuente": fuente,
        "tipo_exposicion": "API no disponible / error controlado",
        "indicador": fuente,
        "severidad": "Bajo",
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "evidencia": str(detalle)[:700],
        "recomendacion": "Validar API key, cuota, plan activo, conectividad y permisos del servicio.",
        "url": "",
        "credencial_confirmada": False,
        "detalle": {"error": str(detalle), "no_penaliza_score": True}
    }



def target_url_scorecard(dominio):
    dominio = limpiar_dominio_scorecard(dominio)
    return "https://" + dominio


def resolver_ip_scorecard(dominio):
    try:
        return socket.gethostbyname(dominio)
    except Exception:
        return ""


def scorecard_risk_levels_activos():
    try:
        conn = get_scorecard_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT *
            FROM scorecard_risk_levels
            WHERE activo = 1
            ORDER BY score_min DESC, orden ASC, id ASC
        """)
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def nivel_riesgo_scorecard(score):
    score = float(score or 0)
    niveles = scorecard_risk_levels_activos()

    if not niveles:
        if score >= 85:
            return "Bajo"
        if score >= 70:
            return "Medio"
        if score >= 50:
            return "Alto"
        return "Crítico"

    for nivel in niveles:
        if score >= float(nivel["score_min"] or 0):
            return nivel["nombre"]

    return niveles[-1]["nombre"]


def scorecard_badge_color(nivel_nombre):
    try:
        conn = get_scorecard_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT color_bootstrap
            FROM scorecard_risk_levels
            WHERE nombre = ?
            LIMIT 1
        """, (nivel_nombre,))
        row = cur.fetchone()
        conn.close()
        return row["color_bootstrap"] if row else "secondary"
    except Exception:
        return "secondary"


def scorecard_run_dir(run_id, dominio):
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", dominio or "target")
    path = os.path.join(SCORECARD_UPLOAD_DIR, f"scorecard_{run_id}_{safe}")
    os.makedirs(path, exist_ok=True)
    return path


def scorecard_output_file(run_dir, herramienta, ext="txt"):
    herramienta = re.sub(r"[^a-zA-Z0-9_.-]+", "_", herramienta or "output")
    return os.path.join(run_dir, f"{herramienta}.{ext}")


def scorecard_set_progress(run_id, pct=None, stage=None, tool=None, estado=None, error=None):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    updates = []
    params = []

    if pct is not None:
        updates.append("progress_pct = ?")
        params.append(max(0, min(100, int(pct))))

    if stage is not None:
        updates.append("current_stage = ?")
        params.append(stage)

    if tool is not None:
        updates.append("current_tool = ?")
        params.append(tool)

    if estado is not None:
        updates.append("estado = ?")
        params.append(estado)

    if error is not None:
        updates.append("error_detalle = ?")
        params.append(error)

    if updates:
        params.append(run_id)
        cur.execute(f"UPDATE scorecard_runs SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    conn.close()


def guardar_scorecard_finding(run_id, item):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_findings
        (run_id, categoria, herramienta, control, estado, riesgo, severidad, score,
         evidencia, recomendacion, archivo_salida, detalle_json, fecha)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        item.get("categoria"),
        item.get("herramienta"),
        item.get("control"),
        item.get("estado"),
        item.get("riesgo"),
        item.get("severidad"),
        float(item.get("score") or 0),
        item.get("evidencia"),
        item.get("recomendacion"),
        item.get("archivo_salida"),
        json.dumps(item, ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def guardar_scorecard_output(run_id, herramienta, comando, archivo_salida, exit_code, duracion):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_outputs
        (run_id, herramienta, comando, archivo_salida, exit_code, duracion_segundos, fecha)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        herramienta,
        comando,
        archivo_salida,
        int(exit_code or 0),
        float(duracion or 0),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


# ============================================================
# DNS HEALTH
# ============================================================

def dns_txt_scorecard(nombre):
    if dns is None:
        return []

    try:
        answers = dns.resolver.resolve(nombre, "TXT", lifetime=5)
        return [str(x.to_text()).strip('"') for x in answers]
    except Exception:
        return []


def dns_any_scorecard(nombre, tipo):
    if dns is None:
        return []

    try:
        answers = dns.resolver.resolve(nombre, tipo, lifetime=5)
        return [str(x.to_text()) for x in answers]
    except Exception:
        return []


def evaluar_dns_health_scorecard(dominio):
    """
    Evalúa DNS Health corrigiendo falsos positivos por subdominios.

    - A/CNAME se evalúa sobre el dominio ingresado.
    - MX, NS, SPF y DMARC se evalúan sobre dominio base.
    """

    score = 100
    findings = []

    dominio_original = limpiar_dominio_scorecard(dominio)
    dominio_base = obtener_dominio_base(dominio_original)

    registros_a = dns_any_scorecard(dominio_original, "A")

    registros_cname = []
    if not registros_a:
        registros_cname = dns_any_scorecard(dominio_original, "CNAME")

    registros_mx = dns_any_scorecard(dominio_base, "MX")
    registros_ns = dns_any_scorecard(dominio_base, "NS")

    txt_root = dns_txt_scorecard(dominio_base)
    txt_dmarc = dns_txt_scorecard(f"_dmarc.{dominio_base}")

    spf_ok = any("v=spf1" in x.lower() for x in txt_root)
    dmarc_ok = any("v=dmarc1" in x.lower() for x in txt_dmarc)

    dmarc_policy = ""
    for item in txt_dmarc:
        low = item.lower()
        if "p=reject" in low:
            dmarc_policy = "reject"
        elif "p=quarantine" in low:
            dmarc_policy = "quarantine"
        elif "p=none" in low:
            dmarc_policy = "none"

    def add(control, estado, riesgo, puntaje, evidencia, recomendacion):
        findings.append({
            "categoria": "DNS Health",
            "herramienta": "DNS Resolver",
            "control": control,
            "estado": estado,
            "riesgo": riesgo,
            "severidad": riesgo,
            "score": puntaje,
            "evidencia": evidencia,
            "recomendacion": recomendacion
        })

    if registros_a:
        add(
            "Registro A",
            "OK",
            "Bajo",
            100,
            f"{dominio_original}: " + ", ".join(registros_a[:8]),
            "Mantener monitoreo de resolución pública."
        )
    elif registros_cname:
        add(
            "Registro A/CNAME",
            "OK por CNAME",
            "Bajo",
            100,
            f"{dominio_original} apunta por CNAME a: " + ", ".join(registros_cname[:8]),
            "Mantener monitoreo de resolución pública y destino CNAME autorizado."
        )
    else:
        score -= 20
        add(
            "Registro A",
            "No detectado",
            "Alto",
            0,
            f"No se encontraron registros A ni CNAME para {dominio_original}.",
            "Validar publicación DNS del dominio o subdominio evaluado."
        )

    if registros_mx:
        add(
            "MX",
            "OK",
            "Bajo",
            100,
            f"{dominio_base}: " + ", ".join(registros_mx[:8]),
            "Mantener proveedores MX autorizados."
        )
    else:
        # No todos los dominios web reciben correo. Por eso queda bajo y solo descuenta 5.
        score -= 5
        add(
            "MX",
            "No detectado en dominio base",
            "Bajo",
            70,
            f"No se encontraron registros MX para {dominio_base}. Esto puede ser aceptable si el dominio no recibe correo.",
            "Confirmar si el proveedor usa este dominio para correo. Si lo usa, configurar MX."
        )

    if registros_ns:
        add(
            "NS",
            "OK",
            "Bajo",
            100,
            f"{dominio_base}: " + ", ".join(registros_ns[:8]),
            "Mantener gobierno sobre la administración DNS."
        )
    else:
        score -= 10
        add(
            "NS",
            "No detectado en dominio base",
            "Medio",
            0,
            f"No se encontraron registros NS para {dominio_base}.",
            "Validar delegación DNS del dominio base."
        )

    if spf_ok:
        add(
            "SPF",
            "OK",
            "Bajo",
            100,
            f"Se detectó registro SPF en {dominio_base}.",
            "Evitar configuraciones demasiado permisivas como +all."
        )
    else:
        score -= 20
        add(
            "SPF",
            "No configurado en dominio base",
            "Alto",
            0,
            f"No se encontró TXT con v=spf1 en {dominio_base}.",
            "Configurar SPF para mitigar spoofing si el dominio envía correo."
        )

    if not dmarc_ok:
        score -= 30
        add(
            "DMARC",
            "No configurado en dominio base",
            "Alto",
            0,
            f"No se encontró _dmarc.{dominio_base}.",
            "Configurar DMARC con política gradual."
        )
    elif dmarc_policy == "none":
        score -= 10
        add(
            "DMARC",
            "Configurado p=none",
            "Medio",
            70,
            f"DMARC existe en _dmarc.{dominio_base}, pero está en modo monitoreo.",
            "Avanzar gradualmente a quarantine o reject."
        )
    else:
        add(
            "DMARC",
            "OK",
            "Bajo",
            100,
            f"Política DMARC en _dmarc.{dominio_base}: {dmarc_policy or 'definida'}.",
            "Mantener monitoreo DMARC."
        )

    return max(0, min(100, score)), findings


# ============================================================
# IP REPUTATION
# ============================================================

def reverse_ip_scorecard(ip):
    try:
        parts = ip.split(".")
        if len(parts) != 4:
            return ""
        return ".".join(reversed(parts))
    except Exception:
        return ""


def evaluar_ip_reputation_scorecard(ip):
    score = 100
    findings = []

    if not ip:
        return 0, [{
            "categoria": "IP Reputation",
            "herramienta": "DNSBL",
            "control": "Resolución IP",
            "estado": "No resuelta",
            "riesgo": "Alto",
            "severidad": "Alto",
            "score": 0,
            "evidencia": "No se pudo resolver IP.",
            "recomendacion": "Validar dominio objetivo."
        }]

    zonas = [
        "zen.spamhaus.org",
        "bl.spamcop.net",
        "dnsbl.sorbs.net",
        "b.barracudacentral.org"
    ]

    reversed_ip = reverse_ip_scorecard(ip)
    listada = []

    if dns is not None and reversed_ip:
        for zona in zonas:
            consulta = f"{reversed_ip}.{zona}"
            try:
                dns.resolver.resolve(consulta, "A", lifetime=4)
                listada.append(zona)
            except Exception:
                pass

    if listada:
        score -= min(90, len(listada) * 25)
        findings.append({
            "categoria": "IP Reputation",
            "herramienta": "DNSBL",
            "control": "Blacklist",
            "estado": "Listada",
            "riesgo": "Alto",
            "severidad": "Alto",
            "score": max(0, score),
            "evidencia": "IP listada en: " + ", ".join(listada),
            "recomendacion": "Solicitar remediación al proveedor y revisar reputación del servicio."
        })
    else:
        findings.append({
            "categoria": "IP Reputation",
            "herramienta": "DNSBL",
            "control": "Blacklist",
            "estado": "OK",
            "riesgo": "Bajo",
            "severidad": "Bajo",
            "score": 100,
            "evidencia": "No se detectó la IP en las listas consultadas.",
            "recomendacion": "Mantener monitoreo de reputación."
        })

    return max(0, min(100, score)), findings


# ============================================================
# KALI SCAN INDEPENDIENTE
# ============================================================

def scorecard_cfg_get(cfg, *names, default=None):
    for name in names:
        try:
            value = getattr(cfg, name)
            if value not in [None, ""]:
                return value
        except Exception:
            pass
    return default


def scorecard_kali_modo(cfg):
    modo = str(scorecard_cfg_get(cfg, "modo", "scanner_mode", default="local") or "local").lower()
    if "rem" in modo or "ssh" in modo or "kali" in modo:
        return "remoto"
    return "local"


def scorecard_tool_path(cfg, tool):
    mapping = {
        "nmap": ["nmap_path", "path_nmap", "ruta_nmap"],
        "whatweb": ["whatweb_path", "path_whatweb", "ruta_whatweb"],
        "nikto": ["nikto_path", "path_nikto", "ruta_nikto"],
        "nuclei": ["nuclei_path", "path_nuclei", "ruta_nuclei"],
        "testssl": ["testssl_path", "path_testssl", "ruta_testssl", "testssl_sh_path"],
    }

    for attr in mapping.get(tool, []):
        value = scorecard_cfg_get(cfg, attr)
        if value:
            return value

    return tool if tool != "testssl" else "testssl"


def scorecard_run_command(cfg, cmd_list, timeout=180):
    """
    Ejecuta comando local o remoto usando la configuración de Kali existente.
    No usa tablas ni pantallas de vulnerabilidades.
    """
    modo = scorecard_kali_modo(cfg)

    if modo == "remoto":
        ssh_host = scorecard_cfg_get(cfg, "ssh_host", "host", "kali_host", "remote_host")
        ssh_user = scorecard_cfg_get(cfg, "ssh_user", "usuario", "kali_user", "remote_user")
        ssh_port = scorecard_cfg_get(cfg, "ssh_port", "port", "kali_port", default="22")
        ssh_key = scorecard_cfg_get(cfg, "ssh_key", "ssh_key_path", "kali_key")

        if not ssh_host:
            raise RuntimeError("La configuración Kali remota no tiene host SSH definido.")

        destino = f"{ssh_user}@{ssh_host}" if ssh_user else ssh_host
        remote_cmd = " ".join(shlex.quote(str(x)) for x in cmd_list)

        ssh_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-p", str(ssh_port)]

        if ssh_key:
            ssh_cmd += ["-i", str(ssh_key)]

        ssh_cmd += [destino, remote_cmd]

        start = time.time()
        proc = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        duracion = round(time.time() - start, 2)
        salida = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")

        return {
            "cmd": " ".join(ssh_cmd),
            "exit_code": proc.returncode,
            "output": salida,
            "duracion": duracion
        }

    start = time.time()
    proc = subprocess.run(
        [str(x) for x in cmd_list],
        capture_output=True,
        text=True,
        timeout=timeout
    )

    duracion = round(time.time() - start, 2)
    salida = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")

    return {
        "cmd": " ".join(str(x) for x in cmd_list),
        "exit_code": proc.returncode,
        "output": salida,
        "duracion": duracion
    }


def scorecard_detectar_severidades(texto):
    texto_low = (texto or "").lower()

    crit = len(re.findall(r"\bcritical\b|\bcrítico\b|\bcritico\b", texto_low))
    high = len(re.findall(r"\bhigh\b|\balto\b", texto_low))
    med = len(re.findall(r"\bmedium\b|\bmedio\b|\bmoderado\b", texto_low))
    low = len(re.findall(r"\blow\b|\bbajo\b", texto_low))

    return {
        "criticas": crit,
        "altas": high,
        "medias": med,
        "bajas": low
    }


def scorecard_score_kali_desde_resumen(resumen):
    criticas = int(resumen.get("criticas") or 0)
    altas = int(resumen.get("altas") or 0)
    medias = int(resumen.get("medias") or 0)
    bajas = int(resumen.get("bajas") or 0)
    errores = int(resumen.get("errores") or 0)

    descuento = (criticas * 25) + (altas * 15) + (medias * 7) + (bajas * 3) + (errores * 2)
    return max(0, 100 - min(100, descuento))


# ============================================================
# OWASP ZAP NORMAL (BASELINE)
# ============================================================

def scorecard_severity_from_text(texto):
    texto = (texto or "").lower()

    if any(x in texto for x in ["critical", "crítico", "critico"]):
        return "Crítico"

    if any(x in texto for x in ["high", "alto"]):
        return "Alto"

    if any(x in texto for x in ["medium", "medio"]):
        return "Medio"

    return "Bajo"


def ejecutar_scorecard_zap_baseline(run_id, dominio):
    run_dir = scorecard_run_dir(run_id, dominio)

    out_html = os.path.join(run_dir, "zap_scan.html")
    out_txt = os.path.join(run_dir, "zap_scan.txt")

    url = target_url_scorecard(dominio)

    docker_image = "ghcr.io/zaproxy/zaproxy:stable"

    cmd = [
        "bash",
        "-lc",
        (
            f"rm -f {shlex.quote(out_html)} {shlex.quote(out_txt)}; "

            f"echo '[OWASP_ZAP] BASELINE iniciado' > {shlex.quote(out_txt)}; "

            f"docker run --rm "
            f"-v {shlex.quote(run_dir)}:/zap/wrk/:rw "
            f"{docker_image} "
            f"zap-baseline.py "
            f"-t {shlex.quote(url)} "
            f"-r zap_scan.html "
            f"-I "
            f">> {shlex.quote(out_txt)} 2>&1; "

            f"ls -lh {shlex.quote(out_html)} {shlex.quote(out_txt)} 2>&1"
        )
    ]

    start = time.time()

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=900
    )

    duracion = round(time.time() - start, 2)

    salida = (proc.stdout or "") + "\n" + (proc.stderr or "")

    guardar_scorecard_output(
        run_id,
        "OWASP ZAP",
        " ".join(cmd),
        out_html,
        proc.returncode,
        duracion
    )

    return {
        "exit_code": proc.returncode,
        "output": salida,
        "html": out_html,
        "txt": out_txt
    }


def parse_scorecard_zap_findings(run_id, dominio):
    findings = []

    run_dir = scorecard_run_dir(run_id, dominio)

    html_file = os.path.join(run_dir, "zap_scan.html")
    txt_file = os.path.join(run_dir, "zap_scan.txt")

    if os.path.exists(html_file):

        try:
            with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            patrones = re.findall(
                r'<h3[^>]*>(.*?)</h3>(.*?)(?=<h3|</body>|</html>)',
                content,
                re.I | re.S
            )

            for titulo_raw, bloque in patrones:

                titulo = html.unescape(
                    re.sub(r'<.*?>', '', titulo_raw)
                ).strip()

                if not titulo:
                    continue

                risk = "Medium"

                risk_match = re.search(
                    r'Risk.*?<td[^>]*>(.*?)</td>',
                    bloque,
                    re.I | re.S
                )

                if risk_match:
                    risk = html.unescape(
                        re.sub(r'<.*?>', '', risk_match.group(1))
                    ).strip()

                desc = ""

                desc_match = re.search(
                    r'Description.*?<td[^>]*>(.*?)</td>',
                    bloque,
                    re.I | re.S
                )

                if desc_match:
                    desc = html.unescape(
                        re.sub(r'<.*?>', ' ', desc_match.group(1))
                    ).strip()

                severidad = scorecard_severity_from_text(
                    risk + " " + titulo + " " + desc
                )

                findings.append({
                    "categoria": "OWASP ZAP",
                    "herramienta": "OWASP ZAP",
                    "control": titulo[:250],
                    "estado": "Hallazgo detectado",
                    "riesgo": severidad,
                    "severidad": severidad,
                    "score": (
                        20 if severidad == "Crítico"
                        else 45 if severidad == "Alto"
                        else 70 if severidad == "Medio"
                        else 90
                    ),
                    "evidencia": (
                        f"OWASP ZAP identificó: {titulo}\n\n"
                        f"{desc[:2500]}"
                    ),
                    "recomendacion": (
                        "Validar el hallazgo reportado por OWASP ZAP y aplicar remediación."
                    ),
                    "archivo_salida": html_file,
                    "detalle": {
                        "titulo": titulo,
                        "risk": risk
                    }
                })

        except Exception as e:

            findings.append({
                "categoria": "OWASP ZAP",
                "herramienta": "OWASP ZAP",
                "control": "Error parseando ZAP",
                "estado": "Error",
                "riesgo": "Medio",
                "severidad": "Medio",
                "score": 50,
                "evidencia": str(e),
                "recomendacion": "Validar parser OWASP ZAP.",
                "archivo_salida": html_file,
                "detalle": {}
            })

    if not findings and os.path.exists(txt_file):

        try:
            with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = [x.strip() for x in f.readlines() if x.strip()]

            for ln in lines:

                low = ln.lower()

                if any(x in low for x in [
                    "fail-new:",
                    "warn-new:",
                    "x-frame-options",
                    "content-security-policy",
                    "cookie",
                    "missing",
                    "server leaks",
                    "strict-transport-security"
                ]):

                    severidad = scorecard_severity_from_text(ln)

                    findings.append({
                        "categoria": "OWASP ZAP",
                        "herramienta": "OWASP ZAP",
                        "control": ln[:250],
                        "estado": "Hallazgo detectado",
                        "riesgo": severidad,
                        "severidad": severidad,
                        "score": (
                            20 if severidad == "Crítico"
                            else 45 if severidad == "Alto"
                            else 70 if severidad == "Medio"
                            else 90
                        ),
                        "evidencia": ln[:2500],
                        "recomendacion": "Validar hallazgo reportado por OWASP ZAP.",
                        "archivo_salida": txt_file,
                        "detalle": {}
                    })

        except Exception:
            pass

    return findings


def ejecutar_scorecard_kali_independiente(run_id, dominio):
    cfg = _scan_cfg()
    run_dir = scorecard_run_dir(run_id, dominio)
    url = target_url_scorecard(dominio)
    ip = resolver_ip_scorecard(dominio)

    modo = scorecard_kali_modo(cfg)

    herramientas = {
        "nmap": scorecard_tool_path(cfg, "nmap"),
        "whatweb": scorecard_tool_path(cfg, "whatweb"),
        "nikto": scorecard_tool_path(cfg, "nikto"),
        "nuclei": scorecard_tool_path(cfg, "nuclei"),
        "testssl": scorecard_tool_path(cfg, "testssl"),
        "zap": "Docker OWASP ZAP Baseline"
    }

    conn = get_scorecard_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE scorecard_runs
        SET modo_kali = ?,
            herramientas_json = ?,
            estado = ?,
            fecha_inicio = ?,
            progress_pct = ?,
            current_stage = ?,
            current_tool = ?
        WHERE id = ?
    """, (
        modo,
        json.dumps(herramientas, ensure_ascii=False),
        "ejecutando",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        45,
        "Inicializando escaneo Kali independiente",
        "dispatcher",
        run_id
    ))
    conn.commit()
    conn.close()

    logs = []
    resumen_global = {
        "criticas": 0,
        "altas": 0,
        "medias": 0,
        "bajas": 0,
        "errores": 0,
        "herramientas": {}
    }

    comandos = []

    # ============================================================
    # OWASP ZAP NORMAL / BASELINE
    # ============================================================
    try:
        scorecard_set_progress(
            run_id,
            pct=50,
            stage="Ejecutando OWASP ZAP normal",
            tool="OWASP ZAP"
        )

        zap_result = ejecutar_scorecard_zap_baseline(run_id, dominio)
        zap_findings = parse_scorecard_zap_findings(run_id, dominio)

        resumen_zap = {
            "exit_code": zap_result.get("exit_code"),
            "archivo_html": zap_result.get("html"),
            "archivo_txt": zap_result.get("txt"),
            "hallazgos": len(zap_findings),
            "severidades": {
                "criticas": 0,
                "altas": 0,
                "medias": 0,
                "bajas": 0
            }
        }

        for item in zap_findings:
            guardar_scorecard_finding(run_id, item)

            sev = item.get("severidad")

            if sev == "Crítico":
                resumen_global["criticas"] += 1
                resumen_zap["severidades"]["criticas"] += 1
            elif sev == "Alto":
                resumen_global["altas"] += 1
                resumen_zap["severidades"]["altas"] += 1
            elif sev == "Medio":
                resumen_global["medias"] += 1
                resumen_zap["severidades"]["medias"] += 1
            else:
                resumen_global["bajas"] += 1
                resumen_zap["severidades"]["bajas"] += 1

        resumen_global["herramientas"]["OWASP ZAP"] = resumen_zap

        logs.append(
            "\n\n===== OWASP ZAP NORMAL =====\n" +
            (zap_result.get("output") or "")[:5000]
        )

    except Exception as e:
        resumen_global["errores"] += 1
        error_text = traceback.format_exc()

        resumen_global["herramientas"]["OWASP ZAP"] = {
            "exit_code": 99,
            "archivo": "",
            "duracion": 0,
            "severidades": {
                "criticas": 0,
                "altas": 0,
                "medias": 1,
                "bajas": 0
            },
            "error": str(e)
        }

        guardar_scorecard_finding(run_id, {
            "categoria": "OWASP ZAP",
            "herramienta": "OWASP ZAP",
            "control": "Ejecución OWASP ZAP",
            "estado": "Error",
            "riesgo": "Medio",
            "severidad": "Medio",
            "score": 50,
            "evidencia": str(e),
            "recomendacion": "Validar Docker, permisos del usuario y disponibilidad de la imagen OWASP ZAP.",
            "archivo_salida": "",
            "detalle": {"error": str(e)}
        })

        logs.append(f"\n\n===== OWASP ZAP ERROR =====\n{error_text[:5000]}")

    # ============================================================
    # NMAP
    # ============================================================
    if ip:
        comandos.append(("Nmap", [
            herramientas["nmap"],
            "-Pn",
            "-sV",
            "--top-ports",
            "100",
            ip
        ], 240))

    # ============================================================
    # WHATWEB
    # ============================================================
    comandos.append(("WhatWeb", [
        herramientas["whatweb"],
        "--no-errors",
        url
    ], 180))

    # ============================================================
    # NIKTO
    # ============================================================
    comandos.append(("Nikto", [
        herramientas["nikto"],
        "-host",
        url,
        "-nointeractive"
    ], 300))

    # ============================================================
    # NUCLEI
    # ============================================================
    comandos.append(("Nuclei", [
        herramientas["nuclei"],
        "-u",
        url,
        "-severity",
        "critical,high,medium,low",
        "-silent"
    ], 420))

    # ============================================================
    # TESTSSL
    # ============================================================
    comandos.append(("testssl", [
        herramientas["testssl"],
        "--fast",
        "--warnings",
        "batch",
        url
    ], 420))

    total_tools = len(comandos)

    for idx, (nombre, cmd, timeout) in enumerate(comandos, start=1):
        pct = 55 + int((idx / max(total_tools, 1)) * 35)

        scorecard_set_progress(
            run_id,
            pct=pct,
            stage=f"Ejecutando {nombre}",
            tool=nombre
        )

        archivo = scorecard_output_file(run_dir, nombre.lower(), "txt")

        try:
            resultado = scorecard_run_command(cfg, cmd, timeout=timeout)

            with open(archivo, "w", encoding="utf-8", errors="ignore") as f:
                f.write(resultado.get("output") or "")

            guardar_scorecard_output(
                run_id,
                nombre,
                resultado.get("cmd"),
                archivo,
                resultado.get("exit_code"),
                resultado.get("duracion")
            )

            salida = resultado.get("output") or ""
            severidades = scorecard_detectar_severidades(salida)

            for k in ["criticas", "altas", "medias", "bajas"]:
                resumen_global[k] += severidades.get(k, 0)

            resumen_global["herramientas"][nombre] = {
                "exit_code": resultado.get("exit_code"),
                "archivo": archivo,
                "duracion": resultado.get("duracion"),
                "severidades": severidades
            }

            riesgo = "Bajo"

            if severidades["criticas"] > 0:
                riesgo = "Crítico"
            elif severidades["altas"] > 0:
                riesgo = "Alto"
            elif severidades["medias"] > 0:
                riesgo = "Medio"

            evidencia = salida[:1200] if salida else "La herramienta no retornó hallazgos relevantes."

            guardar_scorecard_finding(run_id, {
                "categoria": "Kali Linux Scan",
                "herramienta": nombre,
                "control": f"Ejecución {nombre}",
                "estado": (
                    "Ejecutado"
                    if resultado.get("exit_code") in [0, None]
                    else f"Finalizó con código {resultado.get('exit_code')}"
                ),
                "riesgo": riesgo,
                "severidad": riesgo,
                "score": (
                    100 if riesgo == "Bajo"
                    else 70 if riesgo == "Medio"
                    else 45 if riesgo == "Alto"
                    else 20
                ),
                "evidencia": evidencia,
                "recomendacion": "Revisar la salida técnica y validar remediación con el proveedor.",
                "archivo_salida": archivo,
                "detalle": resumen_global["herramientas"][nombre]
            })

            logs.append(f"\n\n===== {nombre} =====\n{salida[:5000]}")

        except Exception as e:
            resumen_global["errores"] += 1
            error_text = traceback.format_exc()

            with open(archivo, "w", encoding="utf-8", errors="ignore") as f:
                f.write(error_text)

            guardar_scorecard_output(
                run_id,
                nombre,
                " ".join(str(x) for x in cmd),
                archivo,
                99,
                0
            )

            guardar_scorecard_finding(run_id, {
                "categoria": "Kali Linux Scan",
                "herramienta": nombre,
                "control": f"Ejecución {nombre}",
                "estado": "Error",
                "riesgo": "Medio",
                "severidad": "Medio",
                "score": 50,
                "evidencia": str(e),
                "recomendacion": "Validar instalación, rutas y conectividad con Kali.",
                "archivo_salida": archivo,
                "detalle": {"error": str(e)}
            })

            logs.append(f"\n\n===== {nombre} ERROR =====\n{error_text[:5000]}")

    score_kali = scorecard_score_kali_desde_resumen(resumen_global)

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT score_dns, score_ip, score_incidentes, score_darkweb, resumen_json
        FROM scorecard_runs
        WHERE id = ?
    """, (run_id,))

    row = cur.fetchone()

    score_dns = float(row["score_dns"] or 0) if row else 0
    score_ip = float(row["score_ip"] or 0) if row else 0
    score_incidentes = float(row["score_incidentes"] or 100) if row else 100
    score_darkweb = float(row["score_darkweb"] or 100) if row else 100

    score_total = scorecard_calcular_total(
        score_dns,
        score_ip,
        score_kali,
        score_incidentes,
        score_darkweb,
        incluir_kali=True
    )

    nivel = nivel_riesgo_scorecard(score_total)

    resumen_base = {}

    try:
        resumen_base = json.loads(row["resumen_json"] or "{}") if row else {}
    except Exception:
        resumen_base = {}

    resumen_final = {
        **resumen_base,
        "dns_score": score_dns,
        "ip_score": score_ip,
        "kali_score": score_kali,
        "incident_score": score_incidentes,
        "darkweb_score": score_darkweb,
        "score_total": score_total,
        "nivel_riesgo": nivel,
        "kali": resumen_global
    }

    cur.execute("""
        UPDATE scorecard_runs
        SET score_kali = ?,
            score_total = ?,
            nivel_riesgo = ?,
            estado = ?,
            progress_pct = ?,
            current_stage = ?,
            current_tool = ?,
            resumen_json = ?,
            salida_consola = ?,
            fecha_fin = ?
        WHERE id = ?
    """, (
        score_kali,
        score_total,
        nivel,
        "finalizado",
        100,
        "Escaneo Scorecard finalizado",
        None,
        json.dumps(resumen_final, ensure_ascii=False),
        ("\n".join(logs))[:25000],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        run_id
    ))

    conn.commit()
    conn.close()



def scorecard_kali_worker(run_id, dominio):
    with app.app_context():
        try:
            ejecutar_scorecard_kali_independiente(run_id, dominio)
        except Exception as e:
            tb = traceback.format_exc()
            scorecard_set_progress(
                run_id,
                pct=100,
                stage="Error en escaneo Kali independiente",
                tool=None,
                estado="error",
                error=tb
            )

def scorecard_get_param(clave, default):
    try:
        conn = get_scorecard_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT valor
            FROM scorecard_parametros
            WHERE clave = ?
        """, (clave,))
        row = cur.fetchone()
        conn.close()

        if row:
            return float(row["valor"])

        return float(default)

    except Exception:
        return float(default)


def scorecard_risk_levels_activos():
    try:
        conn = get_scorecard_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT *
            FROM scorecard_risk_levels
            WHERE activo = 1
            ORDER BY score_min DESC, orden ASC, id ASC
        """)
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def nivel_riesgo_scorecard(score):
    score = float(score or 0)
    niveles = scorecard_risk_levels_activos()

    if not niveles:
        if score >= 85:
            return "Bajo"
        if score >= 70:
            return "Medio"
        if score >= 50:
            return "Alto"
        return "Crítico"

    for nivel in niveles:
        if score >= float(nivel["score_min"] or 0):
            return nivel["nombre"]

    return niveles[-1]["nombre"]


def scorecard_badge_color(nivel_nombre):
    try:
        conn = get_scorecard_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT color_bootstrap
            FROM scorecard_risk_levels
            WHERE nombre = ?
            LIMIT 1
        """, (nivel_nombre,))
        row = cur.fetchone()
        conn.close()

        if row:
            return row["color_bootstrap"]

        return "secondary"

    except Exception:
        return "secondary"


def scorecard_calcular_total(score_dns, score_ip, score_kali, score_incidentes, score_darkweb=100, incluir_kali=True):
    """
    Calcula score total.

    Si incluir_kali=False, Kali NO participa en el score.
    Esto evita castigar cuando no se ejecutó el escaneo Kali.
    """

    peso_dns = scorecard_get_param("peso_dns", 20)
    peso_ip = scorecard_get_param("peso_ip", 15)
    peso_kali = scorecard_get_param("peso_kali", 35)
    peso_incidentes = scorecard_get_param("peso_incidentes", 15)
    peso_darkweb = scorecard_get_param("peso_darkweb", 15)

    componentes = [
        (float(score_dns or 0), peso_dns),
        (float(score_ip or 0), peso_ip),
        (float(score_incidentes or 0), peso_incidentes),
        (float(score_darkweb or 0), peso_darkweb),
    ]

    if incluir_kali:
        componentes.append((float(score_kali or 0), peso_kali))

    total_pesos = sum(peso for _, peso in componentes)

    if total_pesos <= 0:
        return 0

    total = sum(valor * peso for valor, peso in componentes) / total_pesos
    return round(max(0, min(100, total)), 2)


def scorecard_score_incidentes(incidentes):
    """
    Calcula score por severidad, no solo por cantidad.

    Reglas:
    - Sin incidentes: 100
    - Crítico: 20
    - Alto: 55
    - Medio: 75
    - Bajo: 90

    Si hay varios incidentes, toma la severidad más alta.
    """

    incidentes = incidentes or []

    if not incidentes:
        return 100, "Bajo"

    severidad_orden = {
        "Bajo": 1,
        "Medio": 2,
        "Alto": 3,
        "Crítico": 4,
        "Critico": 4
    }

    severidad_max = "Bajo"

    for item in incidentes:
        sev = item.get("severidad") or "Bajo"
        if severidad_orden.get(sev, 0) > severidad_orden.get(severidad_max, 0):
            severidad_max = sev

    if severidad_max in ["Crítico", "Critico"]:
        return 20, "Crítico"

    if severidad_max == "Alto":
        return 55, "Alto"

    if severidad_max == "Medio":
        return 75, "Medio"

    return 90, "Bajo"

def scorecard_brechas_historicas_demo(proveedor_nombre, dominio):
    """
    Catálogo mínimo de brechas históricas conocidas para pruebas/demo.

    Motivo:
    Las búsquedas OSINT tipo GDELT son dinámicas y pueden no devolver incidentes
    antiguos en cada ejecución. Por eso, para validar el funcionamiento del
    módulo, se agrega un catálogo controlado de casos conocidos.
    """

    proveedor_norm = (proveedor_nombre or "").strip().lower()
    dominio_limpio = limpiar_dominio_scorecard(dominio)
    dominio_base = obtener_dominio_base(dominio_limpio)

    incidentes = []

    # Equifax 2017
    if (
        "equifax" in proveedor_norm
        or dominio_base == "equifax.com"
        or dominio_limpio.endswith(".equifax.com")
    ):
        incidentes.append({
            "fuente": "FTC / Caso histórico conocido",
            "titulo": "Equifax Data Breach 2017",
            "url": "https://www.ftc.gov/enforcement/refunds/equifax-data-breach-settlement",
            "fecha_incidente": "2017-09",
            "severidad": "Crítico",
            "descripcion": (
                "Equifax anunció en 2017 una brecha de datos que expuso información personal "
                "de aproximadamente 147 millones de personas. Se registra como incidente histórico "
                "crítico para validar el Scorecard."
            )
        })

    # Yahoo 2013-2014
    if (
        "yahoo" in proveedor_norm
        or dominio_base == "yahoo.com"
        or dominio_limpio.endswith(".yahoo.com")
    ):
        incidentes.append({
            "fuente": "Caso histórico conocido",
            "titulo": "Yahoo Data Breaches 2013-2014",
            "url": "https://www.sec.gov/newsroom/press-releases/2018-71",
            "fecha_incidente": "2013-2014",
            "severidad": "Crítico",
            "descripcion": (
                "Yahoo tuvo brechas históricas de gran escala reportadas públicamente. "
                "Se registra como incidente histórico crítico para pruebas de Scorecard."
            )
        })

    # Marriott / Starwood 2018
    if (
        "marriott" in proveedor_norm
        or "starwood" in proveedor_norm
        or dominio_base == "marriott.com"
        or dominio_limpio.endswith(".marriott.com")
    ):
        incidentes.append({
            "fuente": "Caso histórico conocido",
            "titulo": "Marriott / Starwood Data Breach 2018",
            "url": "https://www.ftc.gov/business-guidance/blog/2024/10/ftc-says-marriott-starwood-data-breaches-resulted-poor-security-practices",
            "fecha_incidente": "2018",
            "severidad": "Crítico",
            "descripcion": (
                "Marriott/Starwood tuvo una brecha de datos ampliamente reportada. "
                "Se registra como incidente histórico crítico para pruebas de Scorecard."
            )
        })

    # Dropbox 2012
    if (
        "dropbox" in proveedor_norm
        or dominio_base == "dropbox.com"
        or dominio_limpio.endswith(".dropbox.com")
    ):
        incidentes.append({
            "fuente": "Caso histórico conocido",
            "titulo": "Dropbox Credential Exposure 2012",
            "url": "https://blogs.dropbox.com/dropbox/2016/08/resetting-passwords-to-keep-your-files-safe/",
            "fecha_incidente": "2012",
            "severidad": "Alto",
            "descripcion": (
                "Dropbox reportó un incidente histórico asociado a credenciales. "
                "Se registra como incidente alto para pruebas de Scorecard."
            )
        })

    return incidentes


def guardar_scorecard_incidente(run_id, proveedor_id, proveedor_nombre, dominio, item):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_incidents
        (run_id, proveedor_id, proveedor_nombre, dominio, fuente, titulo, url,
         fecha_incidente, severidad, descripcion, detalle_json, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        proveedor_id,
        proveedor_nombre,
        dominio,
        item.get("fuente"),
        item.get("titulo"),
        item.get("url"),
        item.get("fecha_incidente"),
        item.get("severidad"),
        item.get("descripcion"),
        json.dumps(item, ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def consultar_incidentes_osint_scorecard(proveedor_nombre, dominio):
    """
    Consulta incidentes de seguridad.

    1. Primero usa catálogo histórico controlado para pruebas/demo.
    2. Luego consulta GDELT para noticias públicas recientes o indexadas.
    """

    incidentes = []
    incidentes.extend(scorecard_brechas_historicas_demo(proveedor_nombre, dominio))

    try:
        terminos = []

        proveedor_nombre = (proveedor_nombre or "").strip()
        dominio_limpio = limpiar_dominio_scorecard(dominio)
        dominio_base = obtener_dominio_base(dominio_limpio)

        if proveedor_nombre and proveedor_nombre != "Proveedor no asociado":
            terminos.append(f'"{proveedor_nombre}" "data breach"')
            terminos.append(f'"{proveedor_nombre}" "cybersecurity incident"')
            terminos.append(f'"{proveedor_nombre}" "ransomware"')
            terminos.append(f'"{proveedor_nombre}" "data leak"')
            terminos.append(f'"{proveedor_nombre}" "security breach"')

        if dominio_base:
            terminos.append(f'"{dominio_base}" "data breach"')
            terminos.append(f'"{dominio_base}" "security incident"')
            terminos.append(f'"{dominio_base}" "ransomware"')
            terminos.append(f'"{dominio_base}" "leak"')
            terminos.append(f'"{dominio_base}" "breach"')

        query = " OR ".join(terminos[:10])

        if query:
            resp = requests.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params={
                    "query": query,
                    "mode": "ArtList",
                    "format": "json",
                    "maxrecords": 20,
                    "sort": "HybridRel"
                },
                timeout=20
            )

            if resp.status_code == 200:
                data = resp.json() or {}
                articles = data.get("articles") or []

                vistos = set((i.get("url") or "").lower() for i in incidentes if i.get("url"))

                for art in articles:
                    titulo = (art.get("title") or "").strip()
                    link = (art.get("url") or "").strip()

                    if not titulo or not link:
                        continue

                    key = link.lower()
                    if key in vistos:
                        continue

                    vistos.add(key)

                    texto = f"{titulo} {art.get('domain','')} {art.get('seendate','')} {art.get('sourceCountry','')}".lower()

                    severidad = "Medio"

                    if any(x in texto for x in ["ransomware", "breach", "data breach", "leak", "stolen", "compromised"]):
                        severidad = "Alto"

                    if any(x in texto for x in ["massive", "millions", "critical", "extortion", "class action", "settlement"]):
                        severidad = "Crítico"

                    incidentes.append({
                        "fuente": art.get("sourceCountry") or "GDELT / Noticias públicas",
                        "titulo": titulo[:500],
                        "url": link,
                        "fecha_incidente": scorecard_normalizar_fecha(art.get("seendate")),
                        "severidad": severidad,
                        "descripcion": (art.get("domain") or "")[:500]
                    })

    except Exception as e:
        print("Error consultando incidentes OSINT Scorecard:", repr(e))

    return incidentes


def evaluar_incident_history_scorecard(run_id, proveedor_id, proveedor_nombre, dominio):
    incidentes = consultar_incidentes_osint_scorecard(proveedor_nombre, dominio)

    for item in incidentes:
        guardar_scorecard_incidente(run_id, proveedor_id, proveedor_nombre, dominio, item)

    total = len(incidentes)
    score, riesgo = scorecard_score_incidentes(incidentes)

    evidencia = (
        f"Se identificaron {total} referencias públicas o históricas asociadas a incidentes, brechas, ransomware, leaks o ataques."
        if total else
        "No se identificaron referencias públicas relevantes de brechas o incidentes en la consulta OSINT básica."
    )

    guardar_scorecard_finding(run_id, {
        "categoria": "Incident History",
        "herramienta": "Catálogo histórico + OSINT Público",
        "control": "Brechas e incidentes de seguridad",
        "estado": "Con hallazgos" if total else "Sin hallazgos",
        "riesgo": riesgo,
        "severidad": riesgo,
        "score": score,
        "evidencia": evidencia,
        "recomendacion": (
            "Validar manualmente las fuentes públicas encontradas, solicitar explicación formal al proveedor "
            "y pedir evidencia de remediación, mejoras de seguridad y controles posteriores al incidente."
            if total else
            "Mantener monitoreo periódico de noticias e incidentes públicos."
        )
    })

    return score, riesgo, total

def scorecard_normalizar_fecha(valor):
    try:
        valor = str(valor or "").strip()
        if not valor:
            return ""
        if len(valor) >= 8 and valor[:8].isdigit():
            return f"{valor[:4]}-{valor[4:6]}-{valor[6:8]}"
        return valor[:30]
    except Exception:
        return ""


def scorecard_leakcheck_extraer_resultados(data):
    if data is None:
        return 0, []

    if isinstance(data, list):
        return len(data), data

    if not isinstance(data, dict):
        return 0, []

    result = data.get("result") or data.get("results") or data.get("data") or []

    if isinstance(result, dict):
        tmp = []
        for k, v in result.items():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        item["_account"] = k
                        tmp.append(item)
                    else:
                        tmp.append({"_account": k, "value": item})
            elif isinstance(v, dict):
                v["_account"] = k
                tmp.append(v)
            else:
                tmp.append({"_account": k, "value": v})
        result = tmp

    if not isinstance(result, list):
        result = []

    found = data.get("found")
    if found is None:
        found = data.get("total")
    if found is None:
        found = len(result)

    try:
        found = int(found or 0)
    except Exception:
        found = len(result)

    return found, result


def consultar_leakcheck_hibrido_scorecard(proveedor_nombre, dominio):
    hallazgos = []

    api_key = scorecard_get_enterprise_api_key("leakcheck")
    if not api_key:
        return hallazgos

    try:
        dominio_base = obtener_dominio_base(dominio)

        if not dominio_base:
            return hallazgos

        if LeakCheckAPI_v2 is not None:
            api = LeakCheckAPI_v2(api_key=api_key)
            data = api.lookup(query=dominio_base, query_type="domain", limit=100)
        else:
            resp = requests.get(
                f"https://leakcheck.io/api/v2/query/{dominio_base}",
                params={"type": "domain", "limit": 100},
                headers={"Accept": "application/json", "X-API-Key": api_key},
                timeout=25
            )

            if resp.status_code in [400, 401, 403, 422, 429]:
                return [scorecard_api_error_item("LeakCheck API", f"HTTP {resp.status_code}: {resp.text[:300]}")]

            if resp.status_code != 200:
                return []

            data = resp.json() or {}

        found, results = scorecard_leakcheck_extraer_resultados(data)

        if found <= 0:
            return hallazgos

        fuentes = []
        muestras = []

        for item in results[:25]:
            if not isinstance(item, dict):
                continue

            src = item.get("source") or item.get("sources") or item.get("breach") or item.get("database")
            if isinstance(src, dict):
                src_name = src.get("name") or src.get("breach") or src.get("title") or "Fuente no informada"
                fecha = src.get("breach_date") or src.get("date") or ""
            elif isinstance(src, list):
                src_name = ", ".join([str(x) for x in src[:3]])
                fecha = ""
            else:
                src_name = str(src or "Fuente no informada")
                fecha = item.get("breach_date") or item.get("date") or ""

            cuenta = (
                item.get("email")
                or item.get("username")
                or item.get("login")
                or item.get("_account")
                or item.get("value")
                or ""
            )

            if src_name and src_name not in fuentes:
                fuentes.append(src_name)

            muestras.append({
                "cuenta_mascarada": scorecard_mask_indicator(cuenta),
                "fuente": src_name,
                "fecha": fecha,
                "password_omitido": True
            })

        severidad = "Medio"
        if found > 2:
            severidad = "Alto"
        if found > 10:
            severidad = "Crítico"

        hallazgos.append({
            "fuente": "LeakCheck API",
            "tipo_exposicion": "Credenciales / identidades filtradas",
            "indicador": f"{dominio_base} - {found} registros encontrados",
            "severidad": severidad,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "evidencia": (
                f"LeakCheck reportó {found} registros asociados al dominio {dominio_base}. "
                f"Fuentes detectadas: {', '.join(fuentes[:8]) if fuentes else 'No informadas'}."
            ),
            "recomendacion": (
                "Solicitar al proveedor investigación formal, rotación de credenciales, MFA obligatorio, "
                "bloqueo de password reuse y evidencia de remediación."
            ),
            "url": "https://leakcheck.io/",
            "credencial_confirmada": True,
            "detalle": {
                "found": found,
                "fuentes": fuentes[:20],
                "muestras_mascaradas": muestras,
                "raw_passwords_omitted": True
            }
        })

    except Exception as e:
        hallazgos.append(scorecard_api_error_item("LeakCheck API", repr(e)))

    return hallazgos


def consultar_hibp_hibrido_scorecard(proveedor_nombre, dominio):
    hallazgos = []

    api_key = scorecard_get_enterprise_api_key("hibp")
    if not api_key:
        return hallazgos

    try:
        dominio_base = obtener_dominio_base(dominio)

        if not dominio_base:
            return hallazgos

        headers = {
            "hibp-api-key": api_key,
            "User-Agent": "GRAC-SGSI-Scorecard/1.0",
            "Accept": "application/json"
        }

        resp = requests.get(
            f"https://haveibeenpwned.com/api/v3/breacheddomain/{dominio_base}",
            params={"truncateResponse": "false"},
            headers=headers,
            timeout=25
        )

        if resp.status_code == 404:
            return hallazgos

        if resp.status_code in [400, 401, 403, 429]:
            return [scorecard_api_error_item("Have I Been Pwned API", f"HTTP {resp.status_code}: dominio no verificado, API key inválida, cuota o rate limit.")]

        if resp.status_code != 200:
            return hallazgos

        data = resp.json() or {}

        if not isinstance(data, dict) or not data:
            return hallazgos

        total_accounts = len(data.keys())
        breach_names = {}
        muestras = []

        for account, breaches in list(data.items())[:25]:
            breach_list = breaches or []
            muestras.append({
                "account": scorecard_mask_email(account),
                "breaches": breach_list[:10]
            })
            for b in breach_list:
                breach_names[b] = breach_names.get(b, 0) + 1

        top_breaches = sorted(breach_names.items(), key=lambda x: x[1], reverse=True)[:8]

        severidad = "Medio"
        if total_accounts > 2:
            severidad = "Alto"
        if total_accounts > 10:
            severidad = "Crítico"

        hallazgos.append({
            "fuente": "Have I Been Pwned API",
            "tipo_exposicion": "Cuentas del dominio en brechas",
            "indicador": f"{dominio_base} - {total_accounts} cuentas afectadas",
            "severidad": severidad,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "evidencia": (
                f"HIBP reportó {total_accounts} cuentas del dominio {dominio_base} asociadas a brechas. "
                f"Brechas más frecuentes: {', '.join([x[0] for x in top_breaches])}."
            ),
            "recomendacion": (
                "Exigir al proveedor revisión de cuentas afectadas, rotación de credenciales, MFA y detección de password reuse."
            ),
            "url": "https://haveibeenpwned.com/",
            "credencial_confirmada": True,
            "detalle": {
                "total_accounts": total_accounts,
                "top_breaches": top_breaches,
                "samples_masked": muestras,
                "raw_accounts_masked": True
            }
        })

    except Exception as e:
        hallazgos.append(scorecard_api_error_item("Have I Been Pwned API", repr(e)))

    return hallazgos


def consultar_shodan_hibrido_scorecard(ip, dominio):
    hallazgos = []

    api_key = scorecard_get_enterprise_api_key("shodan")
    if not api_key:
        return hallazgos

    if not ip:
        return hallazgos

    try:
        resp = requests.get(
            f"https://api.shodan.io/shodan/host/{ip}",
            params={"key": api_key},
            timeout=25
        )

        if resp.status_code == 404:
            return hallazgos

        if resp.status_code in [400, 401, 403, 429]:
            return [scorecard_api_error_item("Shodan API", f"HTTP {resp.status_code}: API key inválida, sin créditos o rate limit.")]

        if resp.status_code != 200:
            return hallazgos

        data = resp.json() or {}
        ports = data.get("ports") or []
        vulns = data.get("vulns") or {}
        hostnames = data.get("hostnames") or []

        cves = []
        if isinstance(vulns, dict):
            for cve, detail in vulns.items():
                cvss = 0
                try:
                    if isinstance(detail, dict):
                        cvss = float(detail.get("cvss") or 0)
                except Exception:
                    cvss = 0
                cves.append({"cve": cve, "cvss": cvss})

        critical_cves = [x for x in cves if x["cvss"] >= 9]
        high_cves = [x for x in cves if 7 <= x["cvss"] < 9]

        if critical_cves:
            severidad = "Crítico"
        elif high_cves or len(cves) > 0:
            severidad = "Alto"
        elif len(ports) >= 8:
            severidad = "Medio"
        else:
            severidad = "Bajo"

        if ports or cves:
            hallazgos.append({
                "fuente": "Shodan API",
                "tipo_exposicion": "Servicios expuestos / CVEs",
                "indicador": f"{ip} - puertos: {', '.join(str(p) for p in ports[:20])}",
                "severidad": severidad,
                "fecha": datetime.now().strftime("%Y-%m-%d"),
                "evidencia": (
                    f"Shodan reportó {len(ports)} puertos observados y {len(cves)} CVEs para la IP {ip}. "
                    f"Hostnames: {', '.join(hostnames[:5])}."
                ),
                "recomendacion": (
                    "Validar exposición de servicios, cerrar puertos innecesarios, aplicar hardening y corregir CVEs."
                ),
                "url": f"https://www.shodan.io/host/{ip}",
                "credencial_confirmada": False,
                "detalle": {
                    "ip": ip,
                    "ports": ports,
                    "hostnames": hostnames,
                    "cves": cves[:50],
                    "critical_cves": critical_cves[:20],
                    "high_cves": high_cves[:20],
                    "org": data.get("org"),
                    "isp": data.get("isp"),
                    "country": data.get("country_name")
                }
            })

    except Exception as e:
        hallazgos.append(scorecard_api_error_item("Shodan API", repr(e)))

    return hallazgos


def scorecard_score_hacker_chatter(total_hallazgos, credencial_confirmada=False, severidad_max="Bajo"):
    total_hallazgos = int(total_hallazgos or 0)

    if credencial_confirmada:
        return scorecard_get_param("darkweb_score_credenciales_confirmadas", 20), "Crítico"

    if total_hallazgos <= 0:
        return scorecard_get_param("darkweb_score_sin_hallazgos", 100), "Bajo"

    if total_hallazgos <= 2:
        base = scorecard_get_param("darkweb_score_1_2", 80)
        riesgo = "Medio"
    elif total_hallazgos <= 5:
        base = scorecard_get_param("darkweb_score_3_5", 60)
        riesgo = "Alto"
    else:
        base = scorecard_get_param("darkweb_score_mas_5", 40)
        riesgo = "Crítico"

    if severidad_max == "Crítico":
        base = min(base, 35)
        riesgo = "Crítico"
    elif severidad_max == "Alto":
        base = min(base, 55)
        if riesgo in ["Bajo", "Medio"]:
            riesgo = "Alto"

    return max(0, min(100, float(base))), riesgo


def guardar_scorecard_darkweb_exposure(run_id, proveedor_id, proveedor_nombre, dominio, item):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_darkweb_exposures
        (run_id, proveedor_id, proveedor_nombre, dominio, fuente, tipo_exposicion,
         indicador, severidad, fecha, evidencia, recomendacion, url,
         credencial_confirmada, detalle_json, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        proveedor_id,
        proveedor_nombre,
        dominio,
        item.get("fuente"),
        item.get("tipo_exposicion"),
        item.get("indicador"),
        item.get("severidad"),
        item.get("fecha"),
        item.get("evidencia"),
        item.get("recomendacion"),
        item.get("url"),
        1 if item.get("credencial_confirmada") else 0,
        json.dumps(item, ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def consultar_hacker_chatter_gdelt_scorecard(proveedor_nombre, dominio):
    hallazgos = []

    try:
        terminos = []
        proveedor_nombre = (proveedor_nombre or "").strip()
        dominio_limpio = limpiar_dominio_scorecard(dominio)
        dominio_base = obtener_dominio_base(dominio_limpio)

        palabras = [
            "leak", "leaked", "credential", "credentials", "password", "dump",
            "database dump", "paste", "breached", "compromised", "ransomware",
            "extortion", "exploit", "hacker forum", "for sale", "stealer logs", "infostealer"
        ]

        if proveedor_nombre and proveedor_nombre != "Proveedor no asociado":
            for palabra in palabras[:12]:
                terminos.append(f'"{proveedor_nombre}" "{palabra}"')

        if dominio_base:
            for palabra in palabras:
                terminos.append(f'"{dominio_base}" "{palabra}"')

        query = " OR ".join(terminos[:22])
        if not query:
            return []

        resp = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={"query": query, "mode": "ArtList", "format": "json", "maxrecords": 30, "sort": "HybridRel"},
            timeout=20
        )

        if resp.status_code != 200:
            return []

        data = resp.json() or {}
        articles = data.get("articles") or []
        vistos = set()

        for art in articles:
            titulo = (art.get("title") or "").strip()
            url = (art.get("url") or "").strip()
            if not titulo or not url:
                continue
            if url.lower() in vistos:
                continue
            vistos.add(url.lower())

            texto = f"{titulo} {art.get('domain','')} {art.get('seendate','')}".lower()

            severidad = "Medio"
            tipo = "Mención pública de exposición"

            if any(x in texto for x in ["credential", "credentials", "password", "dump", "database dump", "leaked database", "stealer", "infostealer"]):
                severidad = "Alto"
                tipo = "Posible fuga de credenciales o datos"

            if any(x in texto for x in ["ransomware", "extortion", "for sale", "hacker forum", "compromised"]):
                severidad = "Crítico"
                tipo = "Hacker chatter crítico / posible compromiso"

            hallazgos.append({
                "fuente": art.get("sourceCountry") or "GDELT / Noticias públicas",
                "tipo_exposicion": tipo,
                "indicador": titulo[:500],
                "severidad": severidad,
                "fecha": scorecard_normalizar_fecha(art.get("seendate")),
                "evidencia": f"Mención pública relacionada con exposición: {titulo[:700]}",
                "recomendacion": "Validar la fuente, solicitar aclaración formal al proveedor y exigir evidencias de contención si aplica.",
                "url": url,
                "credencial_confirmada": False,
                "detalle": art
            })

    except Exception as e:
        print("Error consultando Hacker Chatter GDELT Scorecard:", repr(e))

    return hallazgos


def consultar_certificados_ct_scorecard(dominio):
    """
    Fuente segura: crt.sh.
    No es dark web, pero ayuda a detectar superficie expuesta:
    subdominios publicados en Certificate Transparency.
    """
    hallazgos = []

    try:
        dominio = limpiar_dominio_scorecard(dominio)
        if not dominio:
            return []

        resp = requests.get(
            "https://crt.sh/",
            params={"q": f"%.{dominio}", "output": "json"},
            timeout=20
        )

        if resp.status_code != 200:
            return []

        try:
            data = resp.json() or []
        except Exception:
            return []

        vistos = set()
        subdominios = []

        for item in data[:100]:
            name_value = (item.get("name_value") or "").strip()
            for raw in name_value.splitlines():
                sub = raw.strip().lower().replace("*.", "")
                if sub.endswith(dominio) and sub not in vistos:
                    vistos.add(sub)
                    subdominios.append(sub)

        total = len(subdominios)

        if total >= 20:
            severidad = "Medio"
            evidencia = f"Se identificaron {total} subdominios en Certificate Transparency. Ejemplos: {', '.join(subdominios[:15])}"
            recomendacion = "Revisar si los subdominios publicados están autorizados y si exponen servicios no aprobados."
        elif total > 0:
            severidad = "Bajo"
            evidencia = f"Se identificaron {total} subdominios públicos en Certificate Transparency. Ejemplos: {', '.join(subdominios[:10])}"
            recomendacion = "Mantener inventario de subdominios públicos y monitoreo de exposición."
        else:
            return []

        hallazgos.append({
            "fuente": "crt.sh / Certificate Transparency",
            "tipo_exposicion": "Superficie pública expuesta",
            "indicador": f"Subdominios públicos detectados para {dominio}",
            "severidad": severidad,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "evidencia": evidencia,
            "recomendacion": recomendacion,
            "url": f"https://crt.sh/?q=%25.{dominio}",
            "credencial_confirmada": False,
            "detalle": {"total_subdominios": total, "subdominios_muestra": subdominios[:50]}
        })

    except Exception as e:
        print("Error consultando crt.sh Scorecard:", repr(e))

    return hallazgos


def consultar_github_exposure_scorecard(proveedor_nombre, dominio):
    hallazgos = []

    try:
        dominio_limpio = limpiar_dominio_scorecard(dominio)
        dominio_base = obtener_dominio_base(dominio_limpio)
        proveedor_nombre = (proveedor_nombre or "").strip()

        queries = []

        if dominio_base:
            queries.append(f'"{dominio_base}" password')
            queries.append(f'"{dominio_base}" api_key')
            queries.append(f'"{dominio_base}" secret')
            queries.append(f'"{dominio_base}" token')
            queries.append(f'"{dominio_base}" private_key')

        if proveedor_nombre and proveedor_nombre != "Proveedor no asociado":
            queries.append(f'"{proveedor_nombre}" password')
            queries.append(f'"{proveedor_nombre}" api_key')
            queries.append(f'"{proveedor_nombre}" secret')

        vistos = set()

        for q in queries[:7]:
            resp = requests.get(
                "https://api.github.com/search/code",
                params={"q": q, "per_page": 5},
                headers={"Accept": "application/vnd.github+json"},
                timeout=15
            )

            if resp.status_code not in [200, 403, 422]:
                continue

            if resp.status_code in [403, 422]:
                break

            data = resp.json() or {}
            items = data.get("items") or []

            for it in items:
                html_url = (it.get("html_url") or "").strip()
                repo = ((it.get("repository") or {}).get("full_name") or "").strip()
                path = (it.get("path") or "").strip()

                if not html_url or html_url.lower() in vistos:
                    continue

                vistos.add(html_url.lower())

                hallazgos.append({
                    "fuente": "GitHub Search pública",
                    "tipo_exposicion": "Posible exposición en repositorio público",
                    "indicador": f"{repo}/{path}"[:500],
                    "severidad": "Alto",
                    "fecha": datetime.now().strftime("%Y-%m-%d"),
                    "evidencia": "Se encontró una posible mención pública asociada a secretos, tokens, API keys o contraseñas. Debe validarse manualmente.",
                    "recomendacion": "Validar repositorio, revocar secretos expuestos y solicitar remediación formal al proveedor.",
                    "url": html_url,
                    "credencial_confirmada": False,
                    "detalle": {"repository": repo, "path": path, "html_url": html_url, "raw_secret_omitted": True}
                })

    except Exception as e:
        print("Error consultando GitHub Exposure Scorecard:", repr(e))

    return hallazgos


def deduplicar_hacker_chatter_items(items):
    dedup = []
    vistos = set()

    for item in items:
        key = (
            (item.get("url") or "").strip().lower()
            or
            (item.get("fuente", "") + "|" + item.get("indicador", "")).strip().lower()
        )

        if not key or key in vistos:
            continue

        vistos.add(key)
        dedup.append(item)

    return dedup


def evaluar_darkweb_exposure_scorecard(run_id, proveedor_id, proveedor_nombre, dominio):
    scorecard_set_progress(
        run_id,
        pct=25,
        stage="Consultando Hacker Chatter / Exposure Intelligence híbrido",
        tool="Enterprise + OSINT"
    )

    dominio_limpio = limpiar_dominio_scorecard(dominio)
    ip = resolver_ip_scorecard(dominio_limpio)

    hallazgos = []

    # APIs Enterprise: solo se usan si tienen API Key activa.
    hallazgos.extend(consultar_leakcheck_hibrido_scorecard(proveedor_nombre, dominio_limpio))
    hallazgos.extend(consultar_hibp_hibrido_scorecard(proveedor_nombre, dominio_limpio))
    hallazgos.extend(consultar_shodan_hibrido_scorecard(ip, dominio_limpio))

    # OSINT público: siempre activo.
    hallazgos.extend(consultar_hacker_chatter_gdelt_scorecard(proveedor_nombre, dominio_limpio))
    hallazgos.extend(consultar_certificados_ct_scorecard(dominio_limpio))
    hallazgos.extend(consultar_github_exposure_scorecard(proveedor_nombre, dominio_limpio))

    hallazgos = deduplicar_hacker_chatter_items(hallazgos)

    severidad_orden = {"Bajo": 1, "Medio": 2, "Alto": 3, "Crítico": 4}
    severidad_max = "Bajo"
    credencial_confirmada = False
    total_cves = 0
    fuentes_activas = []
    hallazgos_riesgo = []
    hallazgos_info = []

    for item in hallazgos:
        tipo = (item.get("tipo_exposicion") or "").lower()
        es_info = "api no disponible" in tipo or "error controlado" in tipo

        if es_info:
            hallazgos_info.append(item)
        else:
            hallazgos_riesgo.append(item)

        if not es_info:
            sev = item.get("severidad") or "Bajo"
            if severidad_orden.get(sev, 0) > severidad_orden.get(severidad_max, 0):
                severidad_max = sev

            if item.get("credencial_confirmada"):
                credencial_confirmada = True

            detalle = item.get("detalle") or {}
            if isinstance(detalle, dict):
                total_cves += len(detalle.get("cves") or [])

        fuente = item.get("fuente") or ""
        if fuente and fuente not in fuentes_activas:
            fuentes_activas.append(fuente)

        guardar_scorecard_darkweb_exposure(
            run_id,
            proveedor_id,
            proveedor_nombre,
            dominio_limpio,
            item
        )

    total_riesgo = len(hallazgos_riesgo)
    total_info = len(hallazgos_info)

    score, riesgo = scorecard_score_hacker_chatter(
        total_riesgo,
        credencial_confirmada=credencial_confirmada,
        severidad_max=severidad_max
    )

    if total_cves >= 1 and score > 70:
        score = 70
        riesgo = "Medio"

    if total_cves >= 5 and score > 55:
        score = 55
        riesgo = "Alto"

    if severidad_max == "Crítico":
        score = min(score, 35)
        riesgo = "Crítico"

    if total_riesgo:
        evidencia = (
            f"Se identificaron {total_riesgo} señales de exposición/hacker chatter. "
            f"Severidad máxima: {severidad_max}. "
            f"Fuentes: {', '.join(fuentes_activas[:8])}. "
            f"Credenciales confirmadas: {'sí' if credencial_confirmada else 'no'}. "
            f"CVEs observadas: {total_cves}."
        )
        recomendacion = (
            "Validar hallazgos, solicitar descargos al proveedor, rotar credenciales, activar MFA, "
            "corregir CVEs, reducir exposición pública y exigir evidencia de remediación."
        )
        estado = "Con hallazgos"
    else:
        evidencia = (
            "No se identificaron señales de riesgo relevantes. "
            "Las APIs sin configurar fueron omitidas automáticamente y OSINT público se mantuvo activo."
        )
        if total_info:
            evidencia += f" Hay {total_info} aviso(s) informativos de API no disponible."
        recomendacion = "Mantener monitoreo periódico y configurar APIs enterprise si se requiere mayor profundidad."
        estado = "Sin hallazgos"

    api_estado = scorecard_api_status()

    guardar_scorecard_finding(run_id, {
        "categoria": "Hacker Chatter / Exposure Intelligence",
        "herramienta": "LeakCheck + HIBP + Shodan + GDELT + crt.sh + GitHub",
        "control": "Credenciales, identidades, brechas, CVEs, chatter y superficie expuesta",
        "estado": estado,
        "riesgo": riesgo,
        "severidad": riesgo,
        "score": score,
        "evidencia": evidencia,
        "recomendacion": recomendacion,
        "detalle": {
            "total_hallazgos_riesgo": total_riesgo,
            "total_hallazgos_info": total_info,
            "severidad_max": severidad_max,
            "credencial_confirmada": credencial_confirmada,
            "total_cves": total_cves,
            "fuentes_activas": fuentes_activas,
            "apis_configuradas": {
                "leakcheck": api_estado["leakcheck"]["activo"] and api_estado["leakcheck"]["configurada"],
                "hibp": api_estado["hibp"]["activo"] and api_estado["hibp"]["configurada"],
                "shodan": api_estado["shodan"]["activo"] and api_estado["shodan"]["configurada"]
            }
        }
    })

    scorecard_set_progress(
        run_id,
        pct=40,
        stage="Hacker Chatter / Exposure Intelligence híbrido finalizado",
        tool=None
    )

    return score, riesgo, total_riesgo, credencial_confirmada

def obtener_dominio_base(dominio):
    """
    Obtiene dominio base para evaluar SPF, DMARC, MX y NS.

    Ejemplos:
    - www.amazon.com      -> amazon.com
    - mail.google.com     -> google.com
    - app.empresa.com.co  -> empresa.com.co
    """
    try:
        dominio = limpiar_dominio_scorecard(dominio)

        if not dominio:
            return ""

        partes = dominio.split(".")

        if len(partes) <= 2:
            return dominio

        tlds_compuestos = {
            "com.co", "net.co", "org.co", "edu.co", "gov.co", "mil.co",
            "com.mx", "net.mx", "org.mx", "gob.mx", "edu.mx",
            "com.br", "net.br", "org.br", "gov.br",
            "com.ar", "net.ar", "org.ar", "gob.ar",
            "com.pe", "net.pe", "org.pe", "gob.pe",
            "com.ec", "net.ec", "org.ec", "gob.ec",
            "com.cl", "net.cl", "org.cl", "gob.cl",
            "co.uk", "com.au", "com.es"
        }

        ultimos_dos = ".".join(partes[-2:])
        ultimos_tres = ".".join(partes[-3:])

        if ultimos_dos in tlds_compuestos and len(partes) >= 3:
            return ultimos_tres

        return ultimos_dos

    except Exception:
        return dominio


# ===============================
# RUTA DE CONFIGURACIÓN API KEYS
# ===============================

@app.route("/proveedores/scorecard/apis", methods=["GET", "POST"])
@login_required
def proveedores_scorecard_apis():
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder a la configuración del Scorecard.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no puede modificar API Keys.", "danger")
        return redirect(url_for("proveedores_scorecard_dashboard"))

    if user.role != "admin":
        flash("Solo el administrador puede configurar API Keys del Scorecard.", "danger")
        return redirect(url_for("proveedores_scorecard_dashboard"))

    if request.method == "POST":
        accion = request.form.get("accion", "").strip()

        proveedores = ["leakcheck", "hibp", "shodan"]

        for proveedor in proveedores:
            if accion == f"guardar_{proveedor}":
                api_key = request.form.get(f"{proveedor}_api_key", "").strip()
                activo = bool(request.form.get(f"{proveedor}_activo"))

                if not api_key:
                    flash(f"Debe ingresar una API Key para {proveedor.upper()} o desactivar el servicio.", "warning")
                    return redirect(url_for("proveedores_scorecard_apis"))

                scorecard_guardar_api_key(
                    proveedor,
                    api_key,
                    activo,
                    getattr(user, "username", "Sistema")
                )

                registrar_log(
                    getattr(user, "username", "Sistema"),
                    f"Actualizó API Key cifrada para Scorecard: {proveedor}"
                )

                flash(f"API Key de {proveedor.upper()} guardada cifrada correctamente.", "success")
                return redirect(url_for("proveedores_scorecard_apis"))

            if accion == f"eliminar_{proveedor}":
                scorecard_guardar_api_key(
                    proveedor,
                    "",
                    False,
                    getattr(user, "username", "Sistema")
                )

                registrar_log(
                    getattr(user, "username", "Sistema"),
                    f"Eliminó API Key cifrada para Scorecard: {proveedor}"
                )

                flash(f"API Key de {proveedor.upper()} eliminada correctamente.", "success")
                return redirect(url_for("proveedores_scorecard_apis"))

        flash("Acción no reconocida.", "warning")
        return redirect(url_for("proveedores_scorecard_apis"))

    estado = scorecard_api_status()

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .score-shell{
        width:96%;
        max-width:1280px;
        margin:26px auto 30px auto;
      }

      .score-header-card{
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

      .score-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .score-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .score-header-overlay::before{
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

      .score-header-text{
        color:#ffffff !important;
        font-size:1.32rem;
        font-weight:950;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .score-header-text::before{
        content:"SGSI · Scorecard Enterprise";
        display:block;
        width:max-content;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
        text-shadow:none;
      }

      .api-card{
        background:rgba(255,255,255,.96);
        border:1px solid rgba(219,230,244,.9);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        padding:20px;
        height:100%;
      }

      .api-title{
        font-weight:950;
        color:#0b4a8f;
        margin-bottom:4px;
      }

      .api-sub{
        color:#475569;
        font-size:.9rem;
        font-weight:700;
        margin-bottom:14px;
      }

      .api-mask{
        background:#eef5ff;
        border:1px solid #d9eaff;
        color:#0b4a8f;
        border-radius:10px;
        padding:8px 10px;
        font-weight:900;
        margin-bottom:12px;
      }

      .form-control{
        border-radius:12px;
        font-weight:700;
      }

      .btn{
        border-radius:999px !important;
        font-weight:900;
      }
    </style>

    <div class="score-shell">
      <div class="score-header-card">
        <div class="score-header-overlay">
          <h1 class="score-header-text">Configuración API Keys — Scorecard de Seguridad de Proveedores</h1>
        </div>
      </div>

      <div class="d-flex justify-content-between mb-3">
        <a href="{{ url_for('proveedores_scorecard_dashboard') }}" class="btn btn-outline-secondary px-4">
          Volver
        </a>
      </div>

      <div class="alert alert-info">
        Las API Keys se guardan <strong>cifradas</strong> en la base de datos del Scorecard.
        Si una API no está configurada o está inactiva, el módulo la omite sin generar error.
      </div>

      <div class="row g-3">
        <div class="col-md-4">
          <div class="api-card">
            <h4 class="api-title">LeakCheck</h4>
            <div class="api-sub">Credenciales, identidades y registros filtrados.</div>

            <div class="api-mask">
              Estado:
              {% if estado.leakcheck.activo and estado.leakcheck.configurada %}
                <span class="badge bg-success">Activo</span>
              {% else %}
                <span class="badge bg-secondary">Inactivo</span>
              {% endif %}
              <br>
              Key: {{ estado.leakcheck.mask }}
            </div>

            <form method="POST">
              <input type="hidden" name="accion" value="guardar_leakcheck">
              <div class="mb-2">
                <label class="form-label fw-bold">API Key LeakCheck</label>
                <input type="password" name="leakcheck_api_key" class="form-control" placeholder="Ingrese nueva API Key">
              </div>
              <div class="form-check form-switch mb-3">
                <input class="form-check-input" type="checkbox" name="leakcheck_activo" id="leakcheck_activo"
                  {% if estado.leakcheck.activo %}checked{% endif %}>
                <label class="form-check-label fw-bold" for="leakcheck_activo">Activar LeakCheck</label>
              </div>
              <button class="btn btn-primary w-100 mb-2">Guardar LeakCheck</button>
            </form>

            <form method="POST" onsubmit="return confirm('¿Eliminar API Key LeakCheck?');">
              <input type="hidden" name="accion" value="eliminar_leakcheck">
              <button class="btn btn-outline-danger w-100">Eliminar Key</button>
            </form>
          </div>
        </div>

        <div class="col-md-4">
          <div class="api-card">
            <h4 class="api-title">Have I Been Pwned</h4>
            <div class="api-sub">Brechas asociadas a dominios verificados.</div>

            <div class="api-mask">
              Estado:
              {% if estado.hibp.activo and estado.hibp.configurada %}
                <span class="badge bg-success">Activo</span>
              {% else %}
                <span class="badge bg-secondary">Inactivo</span>
              {% endif %}
              <br>
              Key: {{ estado.hibp.mask }}
            </div>

            <form method="POST">
              <input type="hidden" name="accion" value="guardar_hibp">
              <div class="mb-2">
                <label class="form-label fw-bold">API Key HIBP</label>
                <input type="password" name="hibp_api_key" class="form-control" placeholder="Ingrese nueva API Key">
              </div>
              <div class="form-check form-switch mb-3">
                <input class="form-check-input" type="checkbox" name="hibp_activo" id="hibp_activo"
                  {% if estado.hibp.activo %}checked{% endif %}>
                <label class="form-check-label fw-bold" for="hibp_activo">Activar HIBP</label>
              </div>
              <button class="btn btn-primary w-100 mb-2">Guardar HIBP</button>
            </form>

            <form method="POST" onsubmit="return confirm('¿Eliminar API Key HIBP?');">
              <input type="hidden" name="accion" value="eliminar_hibp">
              <button class="btn btn-outline-danger w-100">Eliminar Key</button>
            </form>
          </div>
        </div>

        <div class="col-md-4">
          <div class="api-card">
            <h4 class="api-title">Shodan</h4>
            <div class="api-sub">Puertos, exposición pública y CVEs por IP.</div>

            <div class="api-mask">
              Estado:
              {% if estado.shodan.activo and estado.shodan.configurada %}
                <span class="badge bg-success">Activo</span>
              {% else %}
                <span class="badge bg-secondary">Inactivo</span>
              {% endif %}
              <br>
              Key: {{ estado.shodan.mask }}
            </div>

            <form method="POST">
              <input type="hidden" name="accion" value="guardar_shodan">
              <div class="mb-2">
                <label class="form-label fw-bold">API Key Shodan</label>
                <input type="password" name="shodan_api_key" class="form-control" placeholder="Ingrese nueva API Key">
              </div>
              <div class="form-check form-switch mb-3">
                <input class="form-check-input" type="checkbox" name="shodan_activo" id="shodan_activo"
                  {% if estado.shodan.activo %}checked{% endif %}>
                <label class="form-check-label fw-bold" for="shodan_activo">Activar Shodan</label>
              </div>
              <button class="btn btn-primary w-100 mb-2">Guardar Shodan</button>
            </form>

            <form method="POST" onsubmit="return confirm('¿Eliminar API Key Shodan?');">
              <input type="hidden" name="accion" value="eliminar_shodan">
              <button class="btn btn-outline-danger w-100">Eliminar Key</button>
            </form>
          </div>
        </div>
      </div>
    </div>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(body, estado=estado))
    )

# ============================================================
# DASHBOARD
# ============================================================

@app.route("/proveedores/scorecard")
@login_required
def proveedores_scorecard_dashboard():
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al Scorecard de Proveedores.", "danger")
        return redirect(url_for("menu"))

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM scorecard_runs
        ORDER BY id DESC
        LIMIT 200
    """)
    runs = cur.fetchall()

    cur.execute("SELECT COUNT(*) total FROM scorecard_runs")
    total = cur.fetchone()["total"] or 0

    cur.execute("SELECT AVG(score_total) promedio FROM scorecard_runs WHERE estado = 'finalizado'")
    promedio = cur.fetchone()["promedio"] or 0

    niveles_riesgo_activos = scorecard_risk_levels_activos()
    niveles_malos = [
        n["nombre"] for n in niveles_riesgo_activos
        if float(n["score_min"] or 0) <= 50
    ]

    if niveles_malos:
        placeholders = ",".join(["?"] * len(niveles_malos))
        cur.execute(f"""
            SELECT COUNT(*) total
            FROM scorecard_runs
            WHERE nivel_riesgo IN ({placeholders})
        """, niveles_malos)
        alto_critico = cur.fetchone()["total"] or 0
    else:
        alto_critico = 0

    conn.close()

    api_estado = scorecard_api_status()

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .score-shell{
        width:96%;
        max-width:1720px;
        margin:26px auto 24px auto;
      }

      .score-header-card{
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

      .score-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 14px
          );
        pointer-events:none;
      }

      .score-header-overlay{
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

      .score-header-overlay::before{
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
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .score-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
        color:#ffffff !important;
        font-size:1.32rem;
        font-weight:950;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .score-header-text::before{
        content:"SGSI · Scorecard";
        display:block;
        width:max-content;
        max-width:100%;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
        text-shadow:none;
      }

      .score-kpi{
        padding:18px;
        border-radius:18px;
        background:rgba(255,255,255,.96);
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .score-kpi .label{
        font-size:.72rem;
        color:#0b4a8f;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:6px 10px;
        border-radius:10px;
        display:inline-block;
        margin-bottom:8px;
      }

      .score-kpi .value{
        font-size:2rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1.1;
      }

      .soft-table-wrap{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        overflow:hidden;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .score-table-scroll{
        max-height:620px;
        overflow:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .table{
        margin-bottom:0;
      }

      .table thead th{
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
      }

      .table tbody td,
      .table td{
        vertical-align:middle !important;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
        white-space:nowrap;
      }

      .table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .table tbody tr:hover{
        background:#eef6ff;
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      /* ======================================================
         BOTON API AZUL SGSI
      ====================================================== */
      .btn-api-blue{
        background:linear-gradient(135deg,#0b4a8f,#2f7fd1) !important;
        border:none !important;
        color:#ffffff !important;
        border-radius:999px !important;
        padding:10px 22px !important;
        font-size:.84rem !important;
        font-weight:900 !important;
        box-shadow:0 10px 22px rgba(20,89,166,.35) !important;
        transition:all .18s ease-in-out;
      }

      .btn-api-blue:hover{
        background:linear-gradient(135deg,#0f4f97,#266fbb) !important;
        color:#ffffff !important;
        transform:translateY(-1px);
        box-shadow:0 14px 26px rgba(20,89,166,.45) !important;
      }

      .btn-api-blue:focus,
      .btn-api-blue:active{
        background:linear-gradient(135deg,#0f4f97,#266fbb) !important;
        color:#ffffff !important;
        outline:none !important;
        box-shadow:0 0 0 .18rem rgba(47,127,209,.25) !important;
      }

      .api-mini{
        background:rgba(255,255,255,.96);
        border:1px solid rgba(219,230,244,.9);
        border-radius:16px;
        padding:12px 14px;
        box-shadow:0 8px 18px rgba(15,23,42,.12);
        margin-bottom:14px;
      }

      .api-mini-title{
        font-weight:950;
        color:#0b4a8f;
        font-size:.84rem;
        text-transform:uppercase;
      }
    </style>

    <div class="score-shell">
      <div class="score-header-card">
        <div class="score-header-overlay">
          <h1 class="score-header-text">Scorecard de Seguridad de Proveedores</h1>
        </div>
      </div>

      <div class="d-flex justify-content-end mb-3 gap-2 flex-wrap">
        {% if not read_only %}
            {% if user.role == 'admin' %}
              <a href="{{ url_for('admin_scorecard_proponentes_apis') }}" class="btn btn-api-blue">
                🔐 Configurar APIs
              </a>
            {% endif %}

            <a href="{{ url_for('proveedores_scorecard_parametros') }}" class="btn btn-secondary rounded-pill px-4">
              ⚙️ Parámetros Scorecard
            </a>

            <a href="{{ url_for('proveedores_scorecard_scan_nuevo') }}" class="btn btn-primary rounded-pill px-4">
              🚀 Ejecutar Escaneo Scorecard
            </a>
        {% endif %}
      </div>

      <div class="api-mini">
        <div class="api-mini-title mb-2">Fuentes Enterprise configuradas</div>
        <span class="badge bg-{% if api_estado.leakcheck.activo and api_estado.leakcheck.configurada %}success{% else %}secondary{% endif %}">
          LeakCheck
        </span>
        <span class="badge bg-{% if api_estado.hibp.activo and api_estado.hibp.configurada %}success{% else %}secondary{% endif %}">
          HIBP
        </span>
        <span class="badge bg-{% if api_estado.shodan.activo and api_estado.shodan.configurada %}success{% else %}secondary{% endif %}">
          Shodan
        </span>
        <span class="badge bg-info text-dark">OSINT público activo</span>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-md-4">
          <div class="score-kpi">
            <div class="label">Evaluaciones ejecutadas</div>
            <div class="value">{{ total }}</div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="score-kpi">
            <div class="label">Score promedio</div>
            <div class="value">{{ "%.1f"|format(promedio) }}%</div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="score-kpi">
            <div class="label">Riesgos críticos / no aceptables</div>
            <div class="value">{{ alto_critico }}</div>
          </div>
        </div>
      </div>

      <div class="soft-table-wrap p-3">
        <div class="table-responsive score-table-scroll">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>ID</th>
                <th>Proveedor</th>
                <th>Dominio</th>
                <th>IP</th>
                <th>DNS</th>
                <th>IP Rep.</th>
                <th>Kali</th>
                <th>Hacker Chatter</th>
                <th>Total</th>
                <th>Riesgo</th>
                <th>Estado</th>
                <th>Progreso</th>
                <th>Fecha</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {% for r in runs %}
              <tr>
                <td>#{{ r.id }}</td>
                <td>{{ r.proveedor_nombre or '—' }}</td>
                <td>{{ r.dominio }}</td>
                <td>{{ r.ip_resuelta or '—' }}</td>
                <td>{{ "%.1f"|format(r.score_dns or 0) }}%</td>
                <td>{{ "%.1f"|format(r.score_ip or 0) }}%</td>
                <td>{{ "%.1f"|format(r.score_kali or 0) }}%</td>
                <td>{{ "%.1f"|format(r.score_darkweb or 100) }}%</td>
                <td><strong>{{ "%.1f"|format(r.score_total or 0) }}%</strong></td>
                <td>
                  <span class="badge bg-{{ scorecard_badge_color(r.nivel_riesgo) }}">
                    {{ r.nivel_riesgo or 'Pendiente' }}
                  </span>
                </td>
                <td>{{ r.estado }}</td>
                <td>{{ r.progress_pct or 0 }}%</td>
                <td>{{ r.fecha_ejecucion }}</td>
                <td>
                  <div class="d-flex gap-1 flex-wrap">
                    <a class="btn btn-sm btn-outline-primary rounded-pill"
                       href="{{ url_for('proveedores_scorecard_detalle', scorecard_id=r.id) }}">
                      Ver
                    </a>

                    <a class="btn btn-sm btn-outline-success rounded-pill"
                        href="{{ url_for('proveedores_scorecard_rating', scorecard_id=r.id) }}">
                       Gráfica
                    </a>

                    {% if not read_only %}
                    <form method="POST"
                          action="{{ url_for('proveedores_scorecard_eliminar', scorecard_id=r.id) }}"
                          onsubmit="return confirm('¿Está seguro de eliminar este Scorecard? Esta acción no se puede deshacer.');"
                          style="display:inline;">
                      <button type="submit" class="btn btn-sm btn-outline-danger rounded-pill">
                        Eliminar
                      </button>
                    </form>
                    {% endif %}
                  </div>
                </td>
              </tr>
              {% else %}
              <tr>
                <td colspan="14" class="text-center text-muted py-4">
                  No hay evaluaciones de scorecard registradas.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            runs=runs,
            total=total,
            promedio=promedio,
            alto_critico=alto_critico,
            read_only=read_only,
            user=user,
            api_estado=api_estado,
            scorecard_badge_color=scorecard_badge_color
        ))
    )



# ============================================================
# NUEVA PANTALLA EXCLUSIVA DE ESCANEO SCORECARD
# ============================================================

@app.route("/proveedores/scorecard/scan/nuevo", methods=["GET", "POST"])
@login_required
def proveedores_scorecard_scan_nuevo():
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para ejecutar Scorecard de Proveedores.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no puede ejecutar scorecards.", "danger")
        return redirect(url_for("proveedores_scorecard_dashboard"))

    proveedores = ProveedorEvaluacion.query.order_by(ProveedorEvaluacion.nombre_proveedor.asc()).all()

    if request.method == "POST":
        proveedor_id = request.form.get("proveedor_id", type=int)
        dominio = limpiar_dominio_scorecard(request.form.get("dominio"))
        ejecutar_kali = bool(request.form.get("ejecutar_kali"))

        if not dominio:
            flash("Debe indicar el dominio autorizado del proveedor.", "danger")
            return redirect(url_for("proveedores_scorecard_scan_nuevo"))

        proveedor = ProveedorEvaluacion.query.get(proveedor_id) if proveedor_id else None
        proveedor_nombre = proveedor.nombre_proveedor if proveedor else "Proveedor no asociado"

        ip = resolver_ip_scorecard(dominio)

        score_dns, findings_dns = evaluar_dns_health_scorecard(dominio)
        score_ip, findings_ip = evaluar_ip_reputation_scorecard(ip)

        score_kali = 0
        score_incidentes = 100
        score_darkweb = 100

        estado = "finalizado"
        progress = 100
        current_stage = "Scorecard finalizado sin escaneo Kali"

        if ejecutar_kali:
            estado = "pendiente"
            progress = 1
            current_stage = "Escaneo Kali pendiente"

        score_total = scorecard_calcular_total(
            score_dns,
            score_ip,
            score_kali,
            score_incidentes,
            score_darkweb,
            incluir_kali=ejecutar_kali
        )
        nivel = nivel_riesgo_scorecard(score_total)

        resumen = {
            "dns_score": score_dns,
            "ip_score": score_ip,
            "kali_score": score_kali,
            "incident_score": score_incidentes,
            "darkweb_score": score_darkweb,
            "score_total": score_total,
            "nivel_riesgo": nivel,
            "ejecutar_kali": ejecutar_kali
        }

        conn = get_scorecard_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO scorecard_runs
            (proveedor_id, proveedor_nombre, dominio, ip_resuelta,
             score_dns, score_ip, score_kali, score_incidentes, score_darkweb,
             score_total, nivel_riesgo, estado, progress_pct, current_stage,
             current_tool, resumen_json, usuario, fecha_ejecucion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            proveedor_id,
            proveedor_nombre,
            dominio,
            ip,
            score_dns,
            score_ip,
            score_kali,
            score_incidentes,
            score_darkweb,
            score_total,
            nivel,
            estado,
            progress,
            current_stage,
            None,
            json.dumps(resumen, ensure_ascii=False),
            getattr(user, "username", "Sistema"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        scorecard_id = cur.lastrowid
        conn.commit()
        conn.close()

        for item in findings_dns + findings_ip:
            guardar_scorecard_finding(scorecard_id, item)

        score_incidentes, riesgo_incidentes, total_incidentes = evaluar_incident_history_scorecard(
            scorecard_id,
            proveedor_id,
            proveedor_nombre,
            dominio
        )

        score_darkweb, riesgo_darkweb, total_darkweb, credencial_confirmada = evaluar_darkweb_exposure_scorecard(
            scorecard_id,
            proveedor_id,
            proveedor_nombre,
            dominio
        )

        score_total = scorecard_calcular_total(
            score_dns,
            score_ip,
            score_kali,
            score_incidentes,
            score_darkweb,
            incluir_kali=ejecutar_kali
        )
        nivel = nivel_riesgo_scorecard(score_total)

        resumen = {
            "dns_score": score_dns,
            "ip_score": score_ip,
            "kali_score": score_kali,
            "incident_score": score_incidentes,
            "darkweb_score": score_darkweb,
            "total_incidentes": total_incidentes,
            "total_darkweb": total_darkweb,
            "riesgo_incidentes": riesgo_incidentes,
            "riesgo_darkweb": riesgo_darkweb,
            "credencial_confirmada": credencial_confirmada,
            "score_total": score_total,
            "nivel_riesgo": nivel,
            "ejecutar_kali": ejecutar_kali,
            "fuentes_darkweb": "GDELT + crt.sh + GitHub Search pública"
        }

        conn = get_scorecard_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE scorecard_runs
            SET score_incidentes = ?, score_darkweb = ?, score_total = ?,
                nivel_riesgo = ?, resumen_json = ?
            WHERE id = ?
        """, (
            score_incidentes,
            score_darkweb,
            score_total,
            nivel,
            json.dumps(resumen, ensure_ascii=False),
            scorecard_id
        ))
        conn.commit()
        conn.close()

        if ejecutar_kali:
            hilo = threading.Thread(
                target=scorecard_kali_worker,
                args=(scorecard_id, dominio),
                daemon=True
            )
            hilo.start()

        registrar_log(
            getattr(user, "username", "Sistema"),
            f"Ejecutó Scorecard proveedor con Hacker Chatter / Exposure Intelligence: {proveedor_nombre} - {dominio}"
        )

        flash("Scorecard creado correctamente. Se validó DNS, reputación IP, incidentes, Hacker Chatter / Exposure Intelligence y Kali si fue seleccionado.", "success")
        return redirect(url_for("proveedores_scorecard_detalle", scorecard_id=scorecard_id))

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .score-shell{
        width:96%;
        max-width:1150px;
        margin:26px auto 24px auto;
      }

      .score-header-card{
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

      .score-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      /* ✅ LOGO A LA IZQUIERDA */
      .score-header-card::after{
        content:"⚙️";
        order:-1;
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
        position:relative;
        z-index:1;
      }

      .score-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
        color:#ffffff !important;
        font-size:1.32rem;
        font-weight:950;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
        position:relative;
        z-index:1;
      }

      .score-header-text::before{
        content:"SGSI · Configuración Scorecard";
        display:block;
        width:max-content;
        max-width:100%;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
        text-shadow:none;
      }

      .score-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
        padding:24px;
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

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      @media (max-width:992px){
        .score-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .score-header-card{
          min-height:88px;
        }

        .score-header-text{
          font-size:1.20rem;
        }

        .score-card,
        .card{
          padding:16px;
        }
      }

      @media (max-width:768px){
        .score-header-card{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .score-header-card::after{
          margin:0;
        }

        .score-header-text,
        .score-header-text::before{
          text-align:center;
          margin-left:auto;
          margin-right:auto;
        }
      }
    </style>

    <div class="score-shell">
      <div class="score-header-card">
        <h1 class="score-header-text">Nuevo Escaneo Scorecard de Proveedor</h1>
      </div>

      <div class="score-card">
        <form method="POST" data-progress-text="Creando Scorecard y ejecutando validaciones...">
          <div class="mb-3">
            <label class="form-label fw-bold">Proveedor</label>
            <select name="proveedor_id" class="form-select">
              <option value="">Proveedor no asociado</option>
              {% for p in proveedores %}
                <option value="{{ p.id }}">{{ p.nombre_proveedor }}</option>
              {% endfor %}
            </select>
          </div>

          <div class="mb-3">
            <label class="form-label fw-bold">Dominio / URL autorizada</label>
            <input name="dominio" class="form-control" placeholder="ejemplo.com" required>
          </div>

          <div class="alert alert-info">
            <strong>Validaciones incluidas:</strong><br>
            DNS Health, IP Reputation, Incidentes/Brechas,
            <strong>Hacker Chatter / Exposure Intelligence</strong>
            mediante <strong>GDELT + crt.sh + GitHub Search pública</strong>,
            y Kali Linux si se selecciona.
          </div>

          <div class="form-check form-switch mb-4">
            <input class="form-check-input" type="checkbox" name="ejecutar_kali" id="ejecutar_kali" checked>
            <label class="form-check-label fw-bold" for="ejecutar_kali">
              Ejecutar escaneo Kali independiente: Nmap, WhatWeb, Nikto, Nuclei y testssl
            </label>
          </div>

          <div class="d-flex justify-content-between">
            <a href="{{ url_for('proveedores_scorecard_dashboard') }}" class="btn btn-outline-secondary rounded-pill px-4">Volver</a>
            <button class="btn btn-primary rounded-pill px-4">🚀 Ejecutar Scorecard</button>
          </div>
        </form>
      </div>
    </div>
    """

    return render_template_string(BASE, content=Markup(render_template_string(body, proveedores=proveedores)))


# ============================================================
# DETALLE SCORECARD
# ============================================================

@app.route("/proveedores/scorecard/<int:scorecard_id>/estado")
@login_required
def proveedores_scorecard_estado(scorecard_id):
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        return jsonify({
            "ok": False,
            "error": "No tiene permiso para consultar el estado del Scorecard."
        }), 403

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, estado, progress_pct, current_stage, current_tool,
               score_total, score_dns, score_ip, score_kali,
               score_incidentes, score_darkweb, nivel_riesgo, error_detalle
        FROM scorecard_runs
        WHERE id = ?
    """, (scorecard_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({
            "ok": False,
            "error": "Scorecard no encontrado."
        }), 404

    estado = row["estado"] or "pendiente"
    progress_pct = int(row["progress_pct"] or 0)

    return jsonify({
        "ok": True,
        "id": row["id"],
        "estado": estado,
        "progress_pct": progress_pct,
        "current_stage": row["current_stage"] or "—",
        "current_tool": row["current_tool"] or "—",
        "score_total": round(float(row["score_total"] or 0), 1),
        "score_dns": round(float(row["score_dns"] or 0), 1),
        "score_ip": round(float(row["score_ip"] or 0), 1),
        "score_kali": round(float(row["score_kali"] or 0), 1),
        "score_incidentes": round(float(row["score_incidentes"] or 100), 1),
        "score_darkweb": round(float(row["score_darkweb"] or 100), 1),
        "nivel_riesgo": row["nivel_riesgo"] or "Pendiente",
        "error_detalle": row["error_detalle"] or ""
    })


# ============================================================
# DETALLE SCORECARD - CON BARRA DE PROGRESO AUTOREFRESH
# REEMPLAZA COMPLETA TU FUNCIÓN proveedores_scorecard_detalle()
# ============================================================

@app.route("/proveedores/scorecard/<int:scorecard_id>")
@login_required
def proveedores_scorecard_detalle(scorecard_id):
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al Scorecard de Proveedores.", "danger")
        return redirect(url_for("menu"))

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM scorecard_runs WHERE id = ?", (scorecard_id,))
    run = cur.fetchone()

    if not run:
        conn.close()
        abort(404)

    cur.execute("""
        SELECT *
        FROM scorecard_findings
        WHERE run_id = ?
          AND categoria <> 'Kali Linux Scan'
        ORDER BY
          CASE categoria
            WHEN 'Hacker Chatter / Exposure Intelligence' THEN 1
            WHEN 'Incident History' THEN 2
            WHEN 'DNS Health' THEN 3
            WHEN 'IP Reputation' THEN 4
            ELSE 5
          END,
          id ASC
    """, (scorecard_id,))
    findings = cur.fetchall()

    cur.execute("""
        SELECT *
        FROM scorecard_incidents
        WHERE run_id = ?
        ORDER BY
          CASE severidad
            WHEN 'Crítico' THEN 1
            WHEN 'Alto' THEN 2
            WHEN 'Medio' THEN 3
            WHEN 'Bajo' THEN 4
            ELSE 5
          END,
          id ASC
    """, (scorecard_id,))
    incidentes = cur.fetchall()

    cur.execute("""
        SELECT *
        FROM scorecard_darkweb_exposures
        WHERE run_id = ?
        ORDER BY
          CASE severidad
            WHEN 'Crítico' THEN 1
            WHEN 'Alto' THEN 2
            WHEN 'Medio' THEN 3
            WHEN 'Bajo' THEN 4
            ELSE 5
          END,
          id ASC
    """, (scorecard_id,))
    hacker_chatter = cur.fetchall()

    cur.execute("""
        SELECT COUNT(*) total
        FROM scorecard_findings
        WHERE run_id = ?
          AND categoria = 'Kali Linux Scan'
    """, (scorecard_id,))
    total_kali = cur.fetchone()["total"] or 0

    conn.close()

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .score-shell{
        width:96%;
        max-width:1650px;
        margin:26px auto 24px auto;
      }

      .score-header-card{
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

      .score-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .score-header-card::after{
        content:"📈";
        order:-1;
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
        position:relative;
        z-index:1;
      }

      .score-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
        color:#ffffff !important;
        font-size:1.32rem;
        font-weight:950;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
        position:relative;
        z-index:1;
      }

      .score-header-text::before{
        content:"SGSI · Scorecard Hacker Chatter";
        display:block;
        width:max-content;
        max-width:100%;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
        text-shadow:none;
      }

      .score-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
        padding:20px;
      }

      .score-main{
        font-size:3rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1;
      }

      .score-table-scroll{
        max-height:520px;
        overflow:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .table{
        margin-bottom:0;
      }

      .table thead th{
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
      }

      .table tbody td,
      .table td{
        vertical-align:middle !important;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .table tbody tr:hover{
        background:#eef6ff;
      }

      .incident-title,
      .chatter-text{
        min-width:360px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
        line-height:1.45;
      }

      .score-progress-box{
        background:rgba(59,130,246,.08);
        border:1px solid rgba(59,130,246,.12);
        border-radius:14px;
        padding:12px 14px;
        margin:10px 0 12px 0;
      }

      .score-progress-head{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
        margin-bottom:8px;
      }

      .score-progress-title{
        font-weight:950;
        color:#0b4a8f;
      }

      .score-live-dot{
        display:inline-block;
        width:9px;
        height:9px;
        border-radius:999px;
        background:#ffc107;
        margin-right:6px;
        box-shadow:0 0 0 rgba(255,193,7,.8);
        animation:scorePulse 1.4s infinite;
      }

      @keyframes scorePulse{
        0%{box-shadow:0 0 0 0 rgba(255,193,7,.8);}
        70%{box-shadow:0 0 0 9px rgba(255,193,7,0);}
        100%{box-shadow:0 0 0 0 rgba(255,193,7,0);}
      }

      .progress{
        background:rgba(0,0,0,.08);
        box-shadow:inset 0 2px 6px rgba(0,0,0,.16);
        height:22px;
        border-radius:999px;
        overflow:hidden;
      }

      .progress-bar{
        font-size:.78rem;
        font-weight:900;
        letter-spacing:.4px;
        transition:width .55s ease;
      }

      .score-autorefresh-note{
        font-size:.82rem;
        color:#607086;
        font-weight:800;
        margin-top:7px;
      }

      .score-error-box{
        display:none;
        border-radius:12px;
        padding:10px 12px;
        background:rgba(220,53,69,.08);
        border:1px solid rgba(220,53,69,.18);
        color:#842029;
        font-weight:800;
        margin-top:10px;
        white-space:pre-wrap;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      @media (max-width:992px){
        .score-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .score-header-card{
          min-height:88px;
        }

        .score-header-text{
          font-size:1.20rem;
        }

        .score-card,
        .card{
          padding:16px;
        }

        .score-main{
          font-size:2.35rem;
        }
      }

      @media (max-width:768px){
        .score-header-card{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .score-header-card::after{
          margin:0;
        }

        .score-header-text,
        .score-header-text::before{
          text-align:center;
          margin-left:auto;
          margin-right:auto;
        }

        .score-progress-head{
          flex-direction:column;
          align-items:flex-start;
        }
      }
    </style>

    <div class="score-shell">
      <div class="score-header-card">
        <h1 class="score-header-text">Detalle Scorecard de Proveedor</h1>
      </div>

      <div class="d-flex justify-content-between mb-3">
        <a href="{{ url_for('proveedores_scorecard_dashboard') }}" class="btn btn-outline-secondary rounded-pill px-4">Volver</a>

        <div class="d-flex gap-2 flex-wrap">
          <a href="{{ url_for('proveedores_scorecard_rating', scorecard_id=run.id) }}"
             class="btn btn-success rounded-pill px-4">
            📊 SecurityScorecard Proveedores
          </a>

          {% if read_only %}
            <button class="btn btn-warning rounded-pill px-4" disabled title="El rol Auditor no tiene acceso al detalle Kali Linux">
              🧪 Ver Detalle Kali Linux
              {% if total_kali %}
                <span class="badge bg-dark ms-1">{{ total_kali }}</span>
              {% endif %}
            </button>
          {% else %}
            <a href="{{ url_for('proveedores_scorecard_kali_detalle', scorecard_id=run.id) }}"
               class="btn btn-warning rounded-pill px-4">
              🧪 Ver Detalle Kali Linux
              {% if total_kali %}
                <span class="badge bg-dark ms-1">{{ total_kali }}</span>
              {% endif %}
            </a>
          {% endif %}

          <a href="{{ url_for('proveedores_scorecard_detalle', scorecard_id=run.id) }}"
             class="btn btn-primary rounded-pill px-4">
            🔄 Actualizar
          </a>
        </div>
      </div>

      <div class="score-card mb-3">
        <div class="row align-items-center">
          <div class="col-md-4 text-center">
            <div class="score-main" id="score-total-main">{{ "%.1f"|format(run.score_total or 0) }}%</div>
            <span id="score-risk-badge" class="badge bg-{{ scorecard_badge_color(run.nivel_riesgo) }} fs-6">
              Riesgo {{ run.nivel_riesgo or 'Pendiente' }}
            </span>
          </div>

          <div class="col-md-8">
            <h4 class="fw-bold">{{ run.proveedor_nombre or 'Proveedor no asociado' }}</h4>

            <p class="mb-1"><strong>Dominio:</strong> {{ run.dominio }}</p>
            <p class="mb-1"><strong>IP:</strong> {{ run.ip_resuelta or '—' }}</p>

            <div class="score-progress-box">
              <div class="score-progress-head">
                <div class="score-progress-title">
                  <span id="score-live-dot" class="score-live-dot"
                    style="{% if run.estado in ['finalizado', 'error'] %}display:none;{% endif %}">
                  </span>
                  Estado:
                  <span id="score-estado-badge"
                        class="badge bg-{% if run.estado == 'finalizado' %}success{% elif run.estado == 'error' %}danger{% else %}warning text-dark{% endif %}">
                    {{ run.estado|capitalize }}
                  </span>
                </div>

                <div class="fw-bold text-primary">
                  Progreso: <span id="score-progress-text">{{ run.progress_pct or 0 }}</span>%
                </div>
              </div>

              <div class="progress">
                <div id="score-progress-bar"
                  class="progress-bar progress-bar-striped
                  {% if run.estado == 'finalizado' %}bg-success
                  {% elif run.estado == 'error' %}bg-danger
                  {% else %}bg-warning text-dark progress-bar-animated{% endif %}"
                  role="progressbar"
                  style="width: {{ run.progress_pct or 0 }}%;"
                  aria-valuenow="{{ run.progress_pct or 0 }}"
                  aria-valuemin="0"
                  aria-valuemax="100">
                  {{ run.progress_pct or 0 }}%
                </div>
              </div>

              <div id="score-autorefresh-note" class="score-autorefresh-note">
                {% if run.estado in ['finalizado', 'error'] %}
                  Actualización automática detenida porque el proceso está {{ run.estado }}.
                {% else %}
                  La barra se actualiza automáticamente cada 3 segundos.
                {% endif %}
              </div>

              <div id="score-error-box" class="score-error-box"></div>
            </div>

            <p class="mb-1"><strong>Etapa:</strong> <span id="score-current-stage">{{ run.current_stage or '—' }}</span></p>
            <p class="mb-1"><strong>Herramienta actual:</strong> <span id="score-current-tool">{{ run.current_tool or '—' }}</span></p>
            <p class="mb-0"><strong>Fecha:</strong> {{ run.fecha_ejecucion }}</p>
          </div>
        </div>
      </div>

      <div class="score-card mb-3">
        <h5 class="fw-bold mb-3">🕵️ Hacker Chatter / Inteligencia de Exposición</h5>

        <div class="alert alert-info">
          Esta sección consolida señales públicas y fuentes enterprise configuradas:
          credenciales, brechas, CVEs, menciones públicas, exposición en repositorios y superficie pública.
        </div>

        <div class="table-responsive score-table-scroll">
          <table class="table table-hover align-middle">
            <thead>
              <tr>
                <th>Fuente</th>
                <th>Tipo</th>
                <th>Indicador</th>
                <th>Severidad</th>
                <th>Fecha</th>
                <th>Evidencia</th>
                <th>Recomendación</th>
                <th>URL</th>
              </tr>
            </thead>
            <tbody>
              {% for h in hacker_chatter %}
              <tr>
                <td>{{ h.fuente or '—' }}</td>
                <td>{{ h.tipo_exposicion or '—' }}</td>
                <td class="chatter-text">{{ h.indicador or '—' }}</td>
                <td>
                  <span class="badge bg-{{ scorecard_badge_color(h.severidad) }}">
                    {{ h.severidad or '—' }}
                  </span>
                </td>
                <td>{{ h.fecha or '—' }}</td>
                <td class="chatter-text">{{ h.evidencia or '—' }}</td>
                <td class="chatter-text">{{ h.recomendacion or '—' }}</td>
                <td>
                  {% if h.url %}
                    <a href="{{ h.url }}" target="_blank" class="btn btn-sm btn-outline-primary rounded-pill">Abrir</a>
                  {% else %}
                    —
                  {% endif %}
                </td>
              </tr>
              {% else %}
              <tr>
                <td colspan="8" class="text-center text-muted py-4">
                  No se identificaron señales públicas relevantes de exposición.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="score-card mb-3">
        <h5 class="fw-bold mb-3">🚨 Brechas o incidentes públicos identificados</h5>
        <div class="table-responsive score-table-scroll">
          <table class="table table-hover align-middle">
            <thead>
              <tr>
                <th>Fuente</th>
                <th>Título / Evento</th>
                <th>Fecha</th>
                <th>Severidad</th>
                <th>Descripción</th>
                <th>URL</th>
              </tr>
            </thead>
            <tbody>
              {% for i in incidentes %}
              <tr>
                <td>{{ i.fuente or '—' }}</td>
                <td class="incident-title">{{ i.titulo or '—' }}</td>
                <td>{{ i.fecha_incidente or '—' }}</td>
                <td>
                  <span class="badge bg-{{ scorecard_badge_color(i.severidad) }}">
                    {{ i.severidad or '—' }}
                  </span>
                </td>
                <td>{{ i.descripcion or '—' }}</td>
                <td>
                  {% if i.url %}
                    <a href="{{ i.url }}" target="_blank" class="btn btn-sm btn-outline-primary rounded-pill">Abrir</a>
                  {% else %}
                    —
                  {% endif %}
                </td>
              </tr>
              {% else %}
              <tr>
                <td colspan="6" class="text-center text-muted py-4">
                  No se identificaron brechas o incidentes públicos asociados al proveedor.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="score-card mb-3">
        <h5 class="fw-bold mb-3">Hallazgos consolidados del Scorecard</h5>
        <div class="table-responsive score-table-scroll">
          <table class="table table-hover align-middle">
            <thead>
              <tr>
                <th>Categoría</th>
                <th>Herramienta</th>
                <th>Control</th>
                <th>Estado</th>
                <th>Riesgo</th>
                <th>Score</th>
                <th>Evidencia</th>
                <th>Recomendación</th>
              </tr>
            </thead>
            <tbody>
              {% for f in findings %}
              <tr>
                <td>{{ f.categoria }}</td>
                <td>{{ f.herramienta or '—' }}</td>
                <td>{{ f.control }}</td>
                <td>{{ f.estado }}</td>
                <td>
                  <span class="badge bg-{{ scorecard_badge_color(f.riesgo) }}">
                    {{ f.riesgo }}
                  </span>
                </td>
                <td>{{ "%.1f"|format(f.score or 0) }}%</td>
                <td class="chatter-text">{{ f.evidencia }}</td>
                <td class="chatter-text">{{ f.recomendacion }}</td>
              </tr>
              {% else %}
              <tr>
                <td colspan="8" class="text-center text-muted">Sin hallazgos registrados.</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <script>
      (function(){
        const estadoUrl = "{{ url_for('proveedores_scorecard_estado', scorecard_id=run.id) }}";
        const detalleUrl = "{{ url_for('proveedores_scorecard_detalle', scorecard_id=run.id) }}";

        const progressBar = document.getElementById("score-progress-bar");
        const progressText = document.getElementById("score-progress-text");
        const estadoBadge = document.getElementById("score-estado-badge");
        const currentStage = document.getElementById("score-current-stage");
        const currentTool = document.getElementById("score-current-tool");
        const totalMain = document.getElementById("score-total-main");
        const riskBadge = document.getElementById("score-risk-badge");
        const liveDot = document.getElementById("score-live-dot");
        const note = document.getElementById("score-autorefresh-note");
        const errorBox = document.getElementById("score-error-box");

        let finishedAlready = ["finalizado", "error"].includes("{{ run.estado }}");
        let intervalId = null;
        let reloadScheduled = false;

        function setBadgeEstado(estado){
          estadoBadge.className = "badge";

          if(estado === "finalizado"){
            estadoBadge.classList.add("bg-success");
            estadoBadge.textContent = "Finalizado";
          }else if(estado === "error"){
            estadoBadge.classList.add("bg-danger");
            estadoBadge.textContent = "Error";
          }else{
            estadoBadge.classList.add("bg-warning", "text-dark");
            estadoBadge.textContent = estado.charAt(0).toUpperCase() + estado.slice(1);
          }
        }

        function setProgressBar(estado, pct){
          pct = Math.max(0, Math.min(100, parseInt(pct || 0)));

          progressText.textContent = pct;
          progressBar.style.width = pct + "%";
          progressBar.setAttribute("aria-valuenow", pct);
          progressBar.textContent = pct + "%";

          progressBar.className = "progress-bar progress-bar-striped";

          if(estado === "finalizado"){
            progressBar.classList.add("bg-success");
          }else if(estado === "error"){
            progressBar.classList.add("bg-danger");
          }else{
            progressBar.classList.add("bg-warning", "text-dark", "progress-bar-animated");
          }
        }

        function setRiskBadge(nivel){
          riskBadge.textContent = "Riesgo " + (nivel || "Pendiente");
        }

        async function refreshScorecardEstado(){
          try{
            const response = await fetch(estadoUrl, {
              method: "GET",
              headers: {
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest"
              },
              cache: "no-store"
            });

            if(!response.ok){
              return;
            }

            const data = await response.json();

            if(!data.ok){
              return;
            }

            const estado = data.estado || "pendiente";

            setBadgeEstado(estado);
            setProgressBar(estado, data.progress_pct);

            currentStage.textContent = data.current_stage || "—";
            currentTool.textContent = data.current_tool || "—";

            totalMain.textContent = Number(data.score_total || 0).toFixed(1) + "%";
            setRiskBadge(data.nivel_riesgo);

            if(estado === "error"){
              if(liveDot){ liveDot.style.display = "none"; }
              note.textContent = "Actualización automática detenida porque el proceso terminó con error.";
              if(data.error_detalle){
                errorBox.style.display = "block";
                errorBox.textContent = data.error_detalle.substring(0, 1200);
              }
              if(intervalId){ clearInterval(intervalId); }
            }

            if(estado === "finalizado"){
              if(liveDot){ liveDot.style.display = "none"; }
              note.textContent = "Proceso finalizado. Actualizando tablas de hallazgos automáticamente...";

              if(intervalId){ clearInterval(intervalId); }

              if(!reloadScheduled && !finishedAlready){
                reloadScheduled = true;
                setTimeout(function(){
                  window.location.href = detalleUrl;
                }, 1600);
              }
            }

          }catch(e){
            console.warn("No se pudo refrescar el estado del Scorecard:", e);
          }
        }

        if(!finishedAlready){
          refreshScorecardEstado();
          intervalId = setInterval(refreshScorecardEstado, 3000);
        }
      })();
    </script>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            run=run,
            findings=findings,
            incidentes=incidentes,
            hacker_chatter=hacker_chatter,
            total_kali=total_kali,
            read_only=read_only,
            scorecard_badge_color=scorecard_badge_color
        ))
    )



def scorecard_rating_letra(score):
    score = float(score or 0)

    if score >= 90:
        return "A", "Excelente"
    if score >= 80:
        return "B", "Bueno"
    if score >= 70:
        return "C", "Aceptable"
    if score >= 60:
        return "D", "Débil"
    return "F", "Crítico"


def scorecard_rating_color(score):
    score = float(score or 0)

    if score >= 85:
        return "#176b2c"
    if score >= 70:
        return "#c48a00"
    if score >= 50:
        return "#c2410c"
    return "#991b1b"


def scorecard_parse_fecha(fecha):
    try:
        if not fecha:
            return None

        fecha = str(fecha).strip()

        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
            try:
                return datetime.strptime(fecha[:19], fmt)
            except Exception:
                pass

        return None
    except Exception:
        return None


def scorecard_get_trend_data(run):
    dominio = limpiar_dominio_scorecard(run["dominio"])
    dominio_base = obtener_dominio_base(dominio)
    proveedor_id = run["proveedor_id"]

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    if proveedor_id:
        cur.execute("""
            SELECT id, score_total, score_dns, score_ip, score_kali, score_incidentes, score_darkweb,
                   nivel_riesgo, fecha_ejecucion, estado
            FROM scorecard_runs
            WHERE proveedor_id = ?
              AND estado IN ('finalizado', 'error')
            ORDER BY id ASC
        """, (proveedor_id,))
    else:
        cur.execute("""
            SELECT id, score_total, score_dns, score_ip, score_kali, score_incidentes, score_darkweb,
                   nivel_riesgo, fecha_ejecucion, estado
            FROM scorecard_runs
            WHERE lower(dominio) LIKE ?
              AND estado IN ('finalizado', 'error')
            ORDER BY id ASC
        """, (f"%{dominio_base.lower()}%",))

    rows = cur.fetchall()
    conn.close()

    hoy = datetime.now()
    limite = hoy - timedelta(days=30)

    puntos = []

    for r in rows:
        dt = scorecard_parse_fecha(r["fecha_ejecucion"])

        if not dt:
            continue

        if dt < limite:
            continue

        puntos.append({
            "id": r["id"],
            "fecha": dt.strftime("%d/%m"),
            "fecha_full": dt.strftime("%Y-%m-%d %H:%M"),
            "score_total": round(float(r["score_total"] or 0), 1),
            "score_dns": round(float(r["score_dns"] or 0), 1),
            "score_ip": round(float(r["score_ip"] or 0), 1),
            "score_kali": round(float(r["score_kali"] or 0), 1),
            "score_incidentes": round(float(r["score_incidentes"] or 100), 1),
            "score_darkweb": round(float(r["score_darkweb"] or 100), 1),
            "nivel_riesgo": r["nivel_riesgo"] or "Pendiente"
        })

    if len(puntos) < 2:
        puntos = []

        for r in rows[-12:]:
            dt = scorecard_parse_fecha(r["fecha_ejecucion"])

            if not dt:
                continue

            puntos.append({
                "id": r["id"],
                "fecha": dt.strftime("%d/%m"),
                "fecha_full": dt.strftime("%Y-%m-%d %H:%M"),
                "score_total": round(float(r["score_total"] or 0), 1),
                "score_dns": round(float(r["score_dns"] or 0), 1),
                "score_ip": round(float(r["score_ip"] or 0), 1),
                "score_kali": round(float(r["score_kali"] or 0), 1),
                "score_incidentes": round(float(r["score_incidentes"] or 100), 1),
                "score_darkweb": round(float(r["score_darkweb"] or 100), 1),
                "nivel_riesgo": r["nivel_riesgo"] or "Pendiente"
            })

    return puntos


def scorecard_get_risk_counts(run_id):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(severidad, riesgo, 'Bajo') AS sev, COUNT(*) AS total
        FROM scorecard_findings
        WHERE run_id = ?
        GROUP BY COALESCE(severidad, riesgo, 'Bajo')
    """, (run_id,))
    findings = cur.fetchall()

    cur.execute("""
        SELECT COALESCE(severidad, 'Bajo') AS sev, COUNT(*) AS total
        FROM scorecard_darkweb_exposures
        WHERE run_id = ?
        GROUP BY COALESCE(severidad, 'Bajo')
    """, (run_id,))
    exposures = cur.fetchall()

    cur.execute("""
        SELECT COALESCE(severidad, 'Bajo') AS sev, COUNT(*) AS total
        FROM scorecard_incidents
        WHERE run_id = ?
        GROUP BY COALESCE(severidad, 'Bajo')
    """, (run_id,))
    incidents = cur.fetchall()

    conn.close()

    counts = {
        "Crítico": 0,
        "Alto": 0,
        "Medio": 0,
        "Bajo": 0
    }

    def normalizar(sev):
        sev = (sev or "Bajo").strip()
        if sev in ["Critico", "Crítico", "critical", "Critical"]:
            return "Crítico"
        if sev in ["Alto", "high", "High"]:
            return "Alto"
        if sev in ["Medio", "medium", "Medium", "Moderado"]:
            return "Medio"
        return "Bajo"

    for grupo in [findings, exposures, incidents]:
        for row in grupo:
            counts[normalizar(row["sev"])] += int(row["total"] or 0)

    total = sum(counts.values())

    return counts, total


def scorecard_get_recent_findings(run_id, limit=5):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT categoria, herramienta, control, estado, riesgo, severidad, score, evidencia, recomendacion, fecha
        FROM scorecard_findings
        WHERE run_id = ?
        ORDER BY
          CASE COALESCE(severidad, riesgo)
            WHEN 'Crítico' THEN 1
            WHEN 'Critico' THEN 1
            WHEN 'Alto' THEN 2
            WHEN 'Medio' THEN 3
            WHEN 'Bajo' THEN 4
            ELSE 5
          END,
          id DESC
        LIMIT ?
    """, (run_id, limit))

    rows = cur.fetchall()
    conn.close()

    return rows


def scorecard_get_peer_comparison(run):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT AVG(score_total) AS promedio
        FROM scorecard_runs
        WHERE estado = 'finalizado'
          AND score_total > 0
    """)
    promedio = cur.fetchone()["promedio"] or 0

    cur.execute("""
        SELECT MAX(score_total) AS mejor
        FROM scorecard_runs
        WHERE estado = 'finalizado'
          AND score_total > 0
    """)
    mejor = cur.fetchone()["mejor"] or 0

    conn.close()

    return {
        "actual": round(float(run["score_total"] or 0), 1),
        "promedio": round(float(promedio or 0), 1),
        "mejor": round(float(mejor or 0), 1)
    }



def scorecard_get_monthly_comparison(run):
    dominio = limpiar_dominio_scorecard(run["dominio"])
    dominio_base = obtener_dominio_base(dominio)
    proveedor_id = run["proveedor_id"]

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    if proveedor_id:
        cur.execute("""
            SELECT fecha_ejecucion, score_total
            FROM scorecard_runs
            WHERE proveedor_id = ?
              AND estado = 'finalizado'
              AND score_total > 0
            ORDER BY fecha_ejecucion ASC
        """, (proveedor_id,))
    else:
        cur.execute("""
            SELECT fecha_ejecucion, score_total
            FROM scorecard_runs
            WHERE lower(dominio) LIKE ?
              AND estado = 'finalizado'
              AND score_total > 0
            ORDER BY fecha_ejecucion ASC
        """, (f"%{dominio_base.lower()}%",))

    rows = cur.fetchall()
    conn.close()

    meses = {}

    for r in rows:
        dt = scorecard_parse_fecha(r["fecha_ejecucion"])
        if not dt:
            continue

        key = dt.strftime("%Y-%m")
        label = dt.strftime("%m/%Y")

        if key not in meses:
            meses[key] = {
                "label": label,
                "scores": []
            }

        meses[key]["scores"].append(float(r["score_total"] or 0))

    data = []

    for key in sorted(meses.keys())[-12:]:
        values = meses[key]["scores"]
        avg = sum(values) / len(values) if values else 0
        data.append({
            "label": meses[key]["label"],
            "score": round(avg, 1)
        })

    return data


def scorecard_issue_summary(scorecard_id):
    """
    Resumen real para la vista SecurityScorecard GRAC.

    - Riesgos críticos: hallazgos con severidad Crítico/Critico
    - Riesgos altos: hallazgos con severidad Alto
    - Vulnerabilidades: hallazgos de Kali Linux con severidad Alto/Crítico
    - Servicios expuestos: hallazgos de Shodan o tipo_exposicion relacionado con servicios/puertos/CVEs
    """

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    # Riesgos críticos en hallazgos consolidados
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_findings
        WHERE run_id = ?
          AND COALESCE(severidad, riesgo, '') IN ('Crítico', 'Critico')
    """, (scorecard_id,))
    criticos = cur.fetchone()["total"] or 0

    # Riesgos altos en hallazgos consolidados
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_findings
        WHERE run_id = ?
          AND COALESCE(severidad, riesgo, '') = 'Alto'
    """, (scorecard_id,))
    altos = cur.fetchone()["total"] or 0

    # Vulnerabilidades reales desde Kali Linux
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_findings
        WHERE run_id = ?
          AND categoria = 'Kali Linux Scan'
          AND COALESCE(severidad, riesgo, '') IN ('Crítico', 'Critico', 'Alto', 'Medio')
    """, (scorecard_id,))
    vulnerabilidades = cur.fetchone()["total"] or 0

    # Servicios expuestos desde Shodan / Exposure
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_darkweb_exposures
        WHERE run_id = ?
          AND (
                LOWER(COALESCE(fuente, '')) LIKE '%shodan%'
             OR LOWER(COALESCE(tipo_exposicion, '')) LIKE '%servicio%'
             OR LOWER(COALESCE(tipo_exposicion, '')) LIKE '%puerto%'
             OR LOWER(COALESCE(tipo_exposicion, '')) LIKE '%cve%'
             OR LOWER(COALESCE(indicador, '')) LIKE '%puerto%'
             OR LOWER(COALESCE(evidencia, '')) LIKE '%puerto%'
          )
    """, (scorecard_id,))
    servicios_expuestos = cur.fetchone()["total"] or 0

    conn.close()

    return {
        "criticos": int(criticos),
        "altos": int(altos),
        "vulnerabilidades": int(vulnerabilidades),
        "servicios_expuestos": int(servicios_expuestos)
    }


@app.route("/proveedores/scorecard/<int:scorecard_id>/rating")
@login_required
def proveedores_scorecard_rating(scorecard_id):
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al Scorecard de Proveedores.", "danger")
        return redirect(url_for("menu"))

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM scorecard_runs WHERE id = ?", (scorecard_id,))
    run = cur.fetchone()
    conn.close()

    if not run:
        abort(404)

    score_total = round(float(run["score_total"] or 0), 1)
    letra, texto_rating = scorecard_rating_letra(score_total)
    color_rating = scorecard_rating_color(score_total)

    trend = scorecard_get_trend_data(run)
    monthly = scorecard_get_monthly_comparison(run)

    counts, total_riesgos = scorecard_get_risk_counts(scorecard_id)
    summary = scorecard_issue_summary(scorecard_id)

    recent_findings = scorecard_get_recent_findings(scorecard_id, limit=4)
    peer = scorecard_get_peer_comparison(run)

    risk_factor_scores = [
        {"label": "Salud DNS", "score": round(float(run["score_dns"] or 0), 1), "canvas": "gaugeDns"},
        {"label": "Reputación IP", "score": round(float(run["score_ip"] or 0), 1), "canvas": "gaugeIp"},
        {"label": "Kali Linux", "score": round(float(run["score_kali"] or 0), 1), "canvas": "gaugeKali"},
        {"label": "Incidentes / Brechas", "score": round(float(run["score_incidentes"] or 100), 1), "canvas": "gaugeIncidentes"},
        {"label": "Exposición / Hacker Chatter", "score": round(float(run["score_darkweb"] or 100), 1), "canvas": "gaugeDarkweb"},
    ]

    trend_labels = [x["fecha"] for x in trend]
    trend_scores = [x["score_total"] for x in trend]

    monthly_labels = [x["label"] for x in monthly]
    monthly_scores = [x["score"] for x in monthly]

    risk_labels = ["Crítico", "Alto", "Medio", "Bajo"]
    risk_values = [
        counts.get("Crítico", 0),
        counts.get("Alto", 0),
        counts.get("Medio", 0),
        counts.get("Bajo", 0)
    ]

    peer_labels = ["Proveedor", "Promedio", "Mejor"]
    peer_values = [peer["actual"], peer["promedio"], peer["mejor"]]

    gauge_labels = [x["label"] for x in risk_factor_scores]
    gauge_scores = [x["score"] for x in risk_factor_scores]
    gauge_canvas_ids = [x["canvas"] for x in risk_factor_scores]

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .rating-shell{
        width:96%;
        max-width:1480px;
        margin:26px auto 24px auto;
      }

      .score-header-card{
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

      .score-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .score-header-card::after{
        content:"📊";
        order:-1;
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
        position:relative;
        z-index:1;
      }

      .score-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
        color:#ffffff !important;
        font-size:1.32rem;
        font-weight:950;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
        position:relative;
        z-index:1;
      }

      .score-header-text::before{
        content:"SGSI · Rating Scorecard";
        display:block;
        width:max-content;
        max-width:100%;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
        text-shadow:none;
      }

      .action-bar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:10px;
        margin:10px 0 14px;
        flex-wrap:wrap;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        padding:.48rem 1.05rem;
        font-size:.86rem;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .ssc-frame{
        background:rgba(245,248,252,.96);
        border:1px solid rgba(219,230,244,.9);
        border-radius:18px;
        padding:12px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
      }

      .ssc-card{
        background:rgba(255,255,255,.985);
        border:1px solid #dbe6f4;
        border-radius:14px;
        box-shadow:0 6px 14px rgba(15,23,42,.075);
        padding:10px 12px;
        height:100%;
        overflow:hidden;
      }

      .ssc-top{
        display:grid;
        grid-template-columns:.95fr .50fr 1.25fr;
        gap:7px;
        align-items:stretch;
      }

      .company-title{
        font-size:1.05rem;
        font-weight:950;
        color:#172033;
        margin-bottom:6px;
        line-height:1.1;
      }

      .company-meta{
        font-size:.68rem;
        font-weight:800;
        color:#334155;
        margin-bottom:2px;
        line-height:1.22;
      }

      .rating-circle{
        width:108px;
        height:108px;
        border-radius:50%;
        margin:0 auto;
        background:{{ color_rating }};
        color:#fff;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 22px rgba(15,23,42,.22);
        border:4px solid rgba(255,255,255,.55);
      }

      .rating-letter{
        font-size:2.75rem;
        line-height:.82;
        font-weight:950;
      }

      .rating-score{
        font-size:1.26rem;
        font-weight:950;
        margin-top:5px;
      }

      .rating-label{
        margin-top:6px;
        padding:3px 8px;
        border-radius:999px;
        background:#eef5ff;
        border:1px solid #d8e9ff;
        color:#0b4a8f;
        font-size:.64rem;
        font-weight:950;
        text-align:center;
        line-height:1.1;
      }

      .section-title{
        font-size:.80rem;
        font-weight:950;
        color:#0b4a8f;
        margin-bottom:5px;
        line-height:1.1;
      }

      .chart-box{
        height:118px;
        position:relative;
      }

      .chart-box-small{
        height:132px;
        position:relative;
      }

      .empty-note{
        border-radius:9px;
        background:#fff7ed;
        border:1px solid #fed7aa;
        color:#9a3412;
        padding:5px 7px;
        font-weight:800;
        font-size:.66rem;
        margin-top:5px;
        line-height:1.15;
      }

      .issue-card{
        margin-top:9px;
        padding:8px 10px;
      }

      .issue-row{
        display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:7px;
      }

      .issue-pill{
        border:1px solid #dbe6f4;
        border-radius:10px;
        padding:6px 8px;
        background:#fff;
        display:flex;
        align-items:center;
        gap:6px;
        font-weight:900;
        color:#1e293b;
        font-size:.70rem;
        min-height:34px;
      }

      .issue-dot{
        width:20px;
        height:20px;
        border-radius:7px;
        color:#fff;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:.62rem;
        font-weight:950;
        flex:0 0 auto;
      }

      .dot-critical{background:#991b1b;}
      .dot-high{background:#c2410c;}
      .dot-medium{background:#d97706;}
      .dot-low{background:#0b4a8f;}

      .main-grid{
        display:grid;
        grid-template-columns:.98fr 1.02fr;
        gap:7px;
        margin-top:9px;
      }

      .left-stack,
      .right-stack{
        display:grid;
        gap:7px;
      }

      .right-stack{
        grid-template-columns:1fr 1fr;
      }

      .right-stack .full{
        grid-column:1 / -1;
      }

      .gauge-grid{
        display:grid;
        grid-template-columns:repeat(5,1fr);
        gap:6px;
      }

      .gauge-card{
        border:1px solid rgba(190,210,235,.95);
        border-radius:14px;
        background:
          radial-gradient(circle at 50% 20%,rgba(255,255,255,.98),rgba(241,247,255,.96) 58%,rgba(230,239,252,.95) 100%);
        padding:7px 7px 6px 7px;
        min-height:124px;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:flex-start;
        overflow:hidden;
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,.95),
          0 7px 16px rgba(15,23,42,.10);
        position:relative;
      }

      .gauge-card::before{
        content:"";
        position:absolute;
        top:5px;
        left:8px;
        right:8px;
        height:24px;
        background:linear-gradient(180deg,rgba(255,255,255,.80),rgba(255,255,255,0));
        border-radius:999px;
        pointer-events:none;
      }

      .gauge-title{
        width:100%;
        text-align:center;
        font-size:.62rem;
        font-weight:950;
        color:#17365d;
        line-height:1.08;
        min-height:24px;
        margin-bottom:1px;
        display:flex;
        align-items:center;
        justify-content:center;
        position:relative;
        z-index:2;
      }

      .gauge-canvas-wrap{
        width:100%;
        height:76px;
        position:relative;
        z-index:2;
      }

      .gauge-score{
        margin-top:-5px;
        font-size:1rem;
        font-weight:950;
        color:#0f3769;
        line-height:1;
        position:relative;
        z-index:2;
      }

      .gauge-state{
        margin-top:3px;
        font-size:.56rem;
        font-weight:950;
        border-radius:999px;
        padding:2px 8px;
        line-height:1;
        position:relative;
        z-index:2;
        border:1px solid rgba(255,255,255,.8);
        box-shadow:0 3px 8px rgba(15,23,42,.10);
      }

      .gauge-state.bajo{
        background:#dcfce7;
        color:#166534;
      }

      .gauge-state.medio{
        background:#fef3c7;
        color:#92400e;
      }

      .gauge-state.alto{
        background:#ffedd5;
        color:#9a3412;
      }

      .gauge-state.critico{
        background:#fee2e2;
        color:#991b1b;
      }

      .finding-table{
        width:100%;
        border-collapse:separate;
        border-spacing:0;
      }

      .finding-table th{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:950;
        padding:5px 6px;
        font-size:.66rem;
        line-height:1.1;
      }

      .finding-table td{
        border-bottom:1px solid #edf2f7;
        padding:5px 6px;
        font-size:.66rem;
        font-weight:700;
        vertical-align:middle;
        line-height:1.12;
      }

      .finding-table td:first-child{
        max-width:230px;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
      }

      .severity-badge{
        border-radius:999px;
        padding:3px 7px;
        color:#fff;
        font-size:.60rem;
        font-weight:950;
        display:inline-block;
        line-height:1;
      }

      .sev-critical{background:#991b1b;}
      .sev-high{background:#c2410c;}
      .sev-medium{background:#d97706;}
      .sev-low{background:#0b4a8f;}

      @media(max-width:1200px){
        .ssc-top,
        .main-grid,
        .right-stack{
          grid-template-columns:1fr;
        }

        .right-stack .full{
          grid-column:auto;
        }

        .chart-box,
        .chart-box-small{
          height:150px;
        }

        .gauge-grid{
          grid-template-columns:repeat(3,1fr);
        }
      }

      @media(max-width:720px){
        .score-header-card{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .score-header-card::after{
          margin:0;
        }

        .score-header-text,
        .score-header-text::before{
          text-align:center;
          margin-left:auto;
          margin-right:auto;
        }

        .issue-row{
          grid-template-columns:repeat(2,1fr);
        }

        .gauge-grid{
          grid-template-columns:repeat(2,1fr);
        }

        .score-header-text{
          font-size:1.20rem;
        }
      }
    </style>

    <div class="rating-shell">
      <div class="score-header-card">
        <h1 class="score-header-text">SecurityScorecard GRAC</h1>
      </div>

      <div class="action-bar">
        <a href="{{ url_for('proveedores_scorecard_detalle', scorecard_id=run.id) }}" class="btn btn-outline-secondary px-4">
          Volver al detalle
        </a>

        <a href="{{ url_for('proveedores_scorecard_dashboard') }}" class="btn btn-primary px-4">
          Dashboard Scorecard
        </a>
      </div>

      <div class="ssc-frame">
        <div class="ssc-top">
          <div class="ssc-card">
            <div class="company-title">{{ run.proveedor_nombre or 'Proveedor no asociado' }}</div>
            <div class="company-meta"><strong>Dominio:</strong> {{ run.dominio }}</div>
            <div class="company-meta"><strong>IP:</strong> {{ run.ip_resuelta or '—' }}</div>
            <div class="company-meta"><strong>Fecha evaluación:</strong> {{ run.fecha_ejecucion }}</div>
            <div class="company-meta"><strong>Estado:</strong> {{ run.estado }}</div>
          </div>

          <div class="ssc-card text-center">
            <div class="rating-circle">
              <div class="rating-letter">{{ letra }}</div>
              <div class="rating-score">{{ "%.1f"|format(score_total) }}</div>
            </div>
            <div class="rating-label">Calificación de seguridad · {{ texto_rating }}</div>
          </div>

          <div class="ssc-card">
            <div class="section-title">Tendencia del score — últimos 30 días</div>
            <div class="chart-box">
              <canvas id="trendChart"></canvas>
            </div>
            {% if trend|length < 2 %}
              <div class="empty-note">
                Ejecuta varios Scorecards del mismo proveedor para ver tendencia real.
              </div>
            {% endif %}
          </div>
        </div>

        <div class="ssc-card issue-card">
          <div class="section-title">Resumen de hallazgos</div>
          <div class="issue-row">
            <div class="issue-pill">
              <span class="issue-dot dot-critical">{{ summary.criticos }}</span>
              Riesgos críticos
            </div>
            <div class="issue-pill">
              <span class="issue-dot dot-high">{{ summary.altos }}</span>
              Riesgos altos
            </div>
            <div class="issue-pill">
              <span class="issue-dot dot-medium">{{ summary.vulnerabilidades }}</span>
              Vulnerabilidades
            </div>
            <div class="issue-pill">
              <span class="issue-dot dot-low">{{ summary.servicios_expuestos }}</span>
              Servicios expuestos
            </div>
          </div>
        </div>

        <div class="main-grid">
          <div class="left-stack">
            <div class="ssc-card">
              <div class="section-title">Factores de riesgo</div>

              <div class="gauge-grid">
                {% for f in risk_factor_scores %}
                <div class="gauge-card">
                  <div class="gauge-title">{{ f.label }}</div>
                  <div class="gauge-canvas-wrap">
                    <canvas id="{{ f.canvas }}"></canvas>
                  </div>
                  <div class="gauge-score">{{ "%.1f"|format(f.score) }}</div>
                  <div class="gauge-state
                    {% if f.score >= 85 %}bajo
                    {% elif f.score >= 70 %}medio
                    {% elif f.score >= 50 %}alto
                    {% else %}critico{% endif %}">
                    {% if f.score >= 85 %}
                      Bajo
                    {% elif f.score >= 70 %}
                      Medio
                    {% elif f.score >= 50 %}
                      Alto
                    {% else %}
                      Crítico
                    {% endif %}
                  </div>
                </div>
                {% endfor %}
              </div>
            </div>

            <div class="ssc-card">
              <div class="section-title">Hallazgos recientes</div>
              <table class="finding-table">
                <thead>
                  <tr>
                    <th>Hallazgo</th>
                    <th>Severidad</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {% for f in recent_findings %}
                  {% set sev = f.severidad or f.riesgo or 'Bajo' %}
                  <tr>
                    <td title="{{ f.control or f.categoria }}">{{ f.control or f.categoria }}</td>
                    <td>
                      <span class="severity-badge
                        {% if sev in ['Crítico','Critico'] %}sev-critical
                        {% elif sev == 'Alto' %}sev-high
                        {% elif sev == 'Medio' %}sev-medium
                        {% else %}sev-low{% endif %}">
                        {{ sev }}
                      </span>
                    </td>
                    <td>{{ f.estado or 'Abierto' }}</td>
                  </tr>
                  {% else %}
                  <tr>
                    <td colspan="3" class="text-center text-muted">Sin hallazgos registrados.</td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>

          <div class="right-stack">
            <div class="ssc-card">
              <div class="section-title">Desglose de riesgo</div>
              <div class="chart-box-small">
                <canvas id="riskChart"></canvas>
              </div>
            </div>

            <div class="ssc-card">
              <div class="section-title">Comparación con pares</div>
              <div class="chart-box-small">
                <canvas id="peerChart"></canvas>
              </div>
            </div>

            <div class="ssc-card full">
              <div class="section-title">Comparación mensual del proveedor</div>
              <div class="chart-box-small">
                <canvas id="monthlyChart"></canvas>
              </div>
              {% if monthly|length < 2 %}
                <div class="empty-note">
                  Para comparar por mes, ejecuta evaluaciones en meses diferentes o carga históricos.
                </div>
              {% endif %}
            </div>
          </div>
        </div>
      </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <script>
      const trendLabels = {{ trend_labels|tojson }};
      const trendScores = {{ trend_scores|tojson }};
      const riskLabels = {{ risk_labels|tojson }};
      const riskValues = {{ risk_values|tojson }};
      const peerLabels = {{ peer_labels|tojson }};
      const peerValues = {{ peer_values|tojson }};
      const monthlyLabels = {{ monthly_labels|tojson }};
      const monthlyScores = {{ monthly_scores|tojson }};

      const gaugeLabels = {{ gauge_labels|tojson }};
      const gaugeScores = {{ gauge_scores|tojson }};
      const gaugeCanvasIds = {{ gauge_canvas_ids|tojson }};

      function chartBaseOptions(maxY=true){
        return {
          responsive: true,
          maintainAspectRatio: false,
          layout: { padding: 0 },
          scales: maxY ? {
            y: {
              min: 0,
              max: 100,
              ticks: { stepSize: 25, font: { size: 9 } },
              grid: { lineWidth: .5 }
            },
            x: {
              ticks: { font: { size: 9 }, maxRotation: 0, autoSkip: true },
              grid: { display: false }
            }
          } : {},
          plugins: {
            legend: { display: false },
            tooltip: { bodyFont: { size: 10 }, titleFont: { size: 10 } }
          }
        }
      }

      function gaugeState(score){
        score = Number(score || 0);
        if(score >= 85){ return 'Bajo'; }
        if(score >= 70){ return 'Medio'; }
        if(score >= 50){ return 'Alto'; }
        return 'Crítico';
      }

      const gaugeNeedlePlugin = {
        id: 'gaugeNeedlePlugin',
        afterDatasetDraw(chart, args, pluginOptions){
          if(chart.config.type !== 'doughnut' || !chart.config.options.plugins.gaugeNeedle){
            return;
          }

          const score = Number(chart.config.options.plugins.gaugeNeedle.score || 0);
          const ctx = chart.ctx;
          const meta = chart.getDatasetMeta(0);
          if(!meta || !meta.data || !meta.data[0]){
            return;
          }

          const arc = meta.data[0];
          const x = arc.x;
          const y = arc.y;
          const outerRadius = arc.outerRadius;
          const innerRadius = arc.innerRadius;
          const needleLength = outerRadius - 9;

          const angle = Math.PI + (Math.PI * Math.max(0, Math.min(100, score)) / 100);

          ctx.save();

          // sombra de aguja
          ctx.translate(x, y);
          ctx.rotate(angle);

          ctx.beginPath();
          ctx.moveTo(-5, 2);
          ctx.lineTo(needleLength, 0);
          ctx.lineTo(-5, -2);
          ctx.closePath();
          ctx.fillStyle = 'rgba(15,23,42,.28)';
          ctx.fill();

          ctx.beginPath();
          ctx.moveTo(-6, 3);
          ctx.lineTo(needleLength - 2, 0);
          ctx.lineTo(-6, -3);
          ctx.closePath();
          ctx.fillStyle = '#172033';
          ctx.fill();

          ctx.restore();

          // centro
          ctx.save();
          ctx.beginPath();
          ctx.arc(x, y, 8, 0, Math.PI * 2);
          ctx.fillStyle = '#ffffff';
          ctx.shadowColor = 'rgba(15,23,42,.25)';
          ctx.shadowBlur = 7;
          ctx.shadowOffsetY = 2;
          ctx.fill();

          ctx.beginPath();
          ctx.arc(x, y, 4.5, 0, Math.PI * 2);
          ctx.fillStyle = '#172033';
          ctx.shadowBlur = 0;
          ctx.fill();
          ctx.restore();

          // etiquetas 0 / 50 / 100
          ctx.save();
          ctx.fillStyle = '#475569';
          ctx.font = '700 8px Arial';
          ctx.textAlign = 'center';
          ctx.fillText('0', x - outerRadius + 12, y + 12);
          ctx.fillText('50', x, y - outerRadius + 16);
          ctx.fillText('100', x + outerRadius - 12, y + 12);
          ctx.restore();
        }
      };

      Chart.register(gaugeNeedlePlugin);

      function buildGauge(canvasId, score, label){
        const ctx = document.getElementById(canvasId);
        if(!ctx){ return; }

        score = Math.max(0, Math.min(100, Number(score || 0)));

        new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: ['Crítico', 'Alto', 'Medio', 'Bajo'],
            datasets: [{
              data: [50, 20, 15, 15],
              backgroundColor: ['#991b1b', '#c2410c', '#d97706', '#087c3d'],
              borderColor: '#ffffff',
              borderWidth: 2,
              circumference: 180,
              rotation: 270,
              cutout: '68%',
              borderRadius: 5
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
              padding: {
                top: 4,
                left: 2,
                right: 2,
                bottom: 0
              }
            },
            plugins: {
              legend: { display: false },
              tooltip: { enabled: false },
              gaugeNeedle: {
                score: score
              }
            }
          }
        });
      }

      function buildAllGauges(){
        for(let i = 0; i < gaugeCanvasIds.length; i++){
          buildGauge(gaugeCanvasIds[i], gaugeScores[i], gaugeLabels[i]);
        }
      }

      function buildTrend(){
        const ctx = document.getElementById('trendChart');

        new Chart(ctx, {
          type: 'line',
          data: {
            labels: trendLabels,
            datasets: [{
              label: 'Score',
              data: trendScores,
              tension: 0.35,
              fill: true,
              borderWidth: 2,
              pointRadius: 3,
              pointHoverRadius: 4
            }]
          },
          options: chartBaseOptions(true)
        });
      }

      function buildRisk(){
        const ctx = document.getElementById('riskChart');

        new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: riskLabels,
            datasets: [{
              data: riskValues,
              backgroundColor: ['#991b1b', '#c2410c', '#d97706', '#0b4a8f'],
              borderWidth: 1
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '58%',
            layout: { padding: 0 },
            plugins: {
              legend: {
                position: 'right',
                labels: {
                  boxWidth: 9,
                  font: { size: 9 },
                  padding: 6
                }
              },
              tooltip: {
                bodyFont: { size: 10 },
                titleFont: { size: 10 }
              }
            }
          }
        });
      }

      function buildPeer(){
        const ctx = document.getElementById('peerChart');

        new Chart(ctx, {
          type: 'bar',
          data: {
            labels: peerLabels,
            datasets: [{
              label: 'Score',
              data: peerValues,
              backgroundColor: ['#087c3d', '#334155', '#0b4a8f'],
              borderWidth: 1
            }]
          },
          options: chartBaseOptions(true)
        });
      }

      function buildMonthly(){
        const ctx = document.getElementById('monthlyChart');

        new Chart(ctx, {
          type: 'line',
          data: {
            labels: monthlyLabels,
            datasets: [{
              label: 'Score mensual',
              data: monthlyScores,
              tension: 0.35,
              fill: false,
              borderWidth: 2,
              pointRadius: 3
            }]
          },
          options: chartBaseOptions(true)
        });
      }

      buildAllGauges();
      buildTrend();
      buildRisk();
      buildPeer();
      buildMonthly();
    </script>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            run=run,
            score_total=score_total,
            letra=letra,
            texto_rating=texto_rating,
            color_rating=color_rating,
            trend=trend,
            monthly=monthly,
            summary=summary,
            counts=counts,
            total_riesgos=total_riesgos,
            recent_findings=recent_findings,
            risk_factor_scores=risk_factor_scores,
            trend_labels=trend_labels,
            trend_scores=trend_scores,
            risk_labels=risk_labels,
            risk_values=risk_values,
            peer_labels=peer_labels,
            peer_values=peer_values,
            monthly_labels=monthly_labels,
            monthly_scores=monthly_scores,
            gauge_labels=gauge_labels,
            gauge_scores=gauge_scores,
            gauge_canvas_ids=gauge_canvas_ids
        ))
    )

@app.route("/proveedores/scorecard/<int:scorecard_id>/eliminar", methods=["POST"])
@login_required
def proveedores_scorecard_eliminar(scorecard_id):
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para eliminar Scorecards.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no puede eliminar Scorecards.", "danger")
        return redirect(url_for("proveedores_scorecard_dashboard"))

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM scorecard_runs WHERE id = ?", (scorecard_id,))
    run = cur.fetchone()

    if not run:
        conn.close()
        flash("No se encontró el Scorecard seleccionado.", "warning")
        return redirect(url_for("proveedores_scorecard_dashboard"))

    cur.execute("DELETE FROM scorecard_findings WHERE run_id = ?", (scorecard_id,))
    cur.execute("DELETE FROM scorecard_outputs WHERE run_id = ?", (scorecard_id,))
    cur.execute("DELETE FROM scorecard_incidents WHERE run_id = ?", (scorecard_id,))
    cur.execute("DELETE FROM scorecard_darkweb_exposures WHERE run_id = ?", (scorecard_id,))
    cur.execute("DELETE FROM scorecard_runs WHERE id = ?", (scorecard_id,))

    conn.commit()
    conn.close()

    registrar_log(
        getattr(user, "username", "Sistema"),
        f"Eliminó Scorecard de proveedor ID {scorecard_id}: {run['proveedor_nombre']} - {run['dominio']}"
    )

    flash("Scorecard eliminado correctamente.", "success")
    return redirect(url_for("proveedores_scorecard_dashboard"))

@app.route("/proveedores/scorecard/<int:scorecard_id>/kali")
@login_required
def proveedores_scorecard_kali_detalle(scorecard_id):
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al detalle Kali del Scorecard.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no tiene acceso al detalle técnico Kali Linux.", "warning")
        return redirect(url_for("proveedores_scorecard_detalle", scorecard_id=scorecard_id))

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM scorecard_runs WHERE id = ?", (scorecard_id,))
    run = cur.fetchone()

    if not run:
        conn.close()
        abort(404)

    cur.execute("""
        SELECT *
        FROM scorecard_findings
        WHERE run_id = ?
          AND categoria = 'Kali Linux Scan'
        ORDER BY 
          CASE riesgo
            WHEN 'Crítico' THEN 1
            WHEN 'Alto' THEN 2
            WHEN 'Medio' THEN 3
            WHEN 'Bajo' THEN 4
            ELSE 5
          END,
          herramienta ASC,
          id ASC
    """, (scorecard_id,))
    findings_kali = cur.fetchall()

    cur.execute("""
        SELECT *
        FROM scorecard_outputs
        WHERE run_id = ?
        ORDER BY id ASC
    """, (scorecard_id,))
    outputs = cur.fetchall()

    conn.close()

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .score-shell{
        width:96%;
        max-width:1650px;
        margin:26px auto 24px auto;
      }

      .score-header-card{
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

      .score-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .score-header-overlay{
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

      .score-header-overlay::before{
        content:"🧪";
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

      .score-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
        color:#ffffff !important;
        font-size:1.32rem;
        font-weight:950;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
        position:relative;
        z-index:1;
      }

      .score-header-text::before{
        content:"SGSI · Resultados Kali Linux";
        display:block;
        width:max-content;
        max-width:100%;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
        text-shadow:none;
      }

      .score-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
        padding:20px;
      }

      .soft-table-wrap{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        overflow:hidden;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .kali-table-scroll{
        max-height:620px;
        overflow:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .table{
        margin-bottom:0;
      }

      .table thead th{
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
      }

      .table tbody td,
      .table td{
        vertical-align:top !important;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .table tbody tr:hover{
        background:#eef6ff;
      }

      .evidence-cell{
        min-width:520px;
        max-width:760px;
        white-space:pre-wrap;
        font-size:.86rem;
        line-height:1.45;
      }

      .recommend-cell{
        min-width:360px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
        line-height:1.45;
      }

      pre{
        white-space:pre-wrap;
        max-height:520px;
        overflow:auto;
        background:#0b1f33;
        color:#dceeff;
        padding:16px;
        border-radius:14px;
        font-size:.84rem;
        border:1px solid rgba(255,255,255,.12);
        box-shadow:inset 0 1px 0 rgba(255,255,255,.08);
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      @media (max-width:992px){
        .score-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .score-header-card{
          min-height:88px;
        }

        .score-header-text{
          font-size:1.20rem;
        }

        .score-card,
        .card{
          padding:16px;
        }

        .evidence-cell{
          min-width:420px;
        }
      }

      @media (max-width:768px){
        .score-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .score-header-overlay::before{
          margin:0;
        }

        .score-header-text,
        .score-header-text::before{
          text-align:center;
          margin-left:auto;
          margin-right:auto;
        }
      }
    </style>

    <div class="score-shell">
      <div class="score-header-card">
        <div class="score-header-overlay">
          <h1 class="score-header-text">Detalle Escaneo Kali Linux — Scorecard Proveedor</h1>
        </div>
      </div>

      <div class="d-flex justify-content-between mb-3">
        <a href="{{ url_for('proveedores_scorecard_detalle', scorecard_id=run.id) }}"
           class="btn btn-outline-secondary rounded-pill px-4">
          Volver al Scorecard
        </a>

        <a href="{{ url_for('proveedores_scorecard_kali_detalle', scorecard_id=run.id) }}"
           class="btn btn-primary rounded-pill px-4">
          🔄 Actualizar
        </a>
      </div>

      <div class="score-card mb-3">
        <div class="row">
          <div class="col-md-8">
            <h4 class="fw-bold mb-2">{{ run.proveedor_nombre or 'Proveedor no asociado' }}</h4>
            <p class="mb-1"><strong>Dominio:</strong> {{ run.dominio }}</p>
            <p class="mb-1"><strong>IP:</strong> {{ run.ip_resuelta or '—' }}</p>
            <p class="mb-1"><strong>Estado:</strong> {{ run.estado }}</p>
            <p class="mb-1"><strong>Etapa:</strong> {{ run.current_stage or '—' }}</p>
            <p class="mb-0"><strong>Herramienta actual:</strong> {{ run.current_tool or '—' }}</p>
          </div>
          <div class="col-md-4 text-center">
            <div class="fs-1 fw-bold text-primary">{{ "%.1f"|format(run.score_kali or 0) }}%</div>
            <div class="fw-bold text-muted">Score Kali Linux</div>
          </div>
        </div>
      </div>

      <div class="soft-table-wrap mb-3">
        <div class="p-3 pb-0">
          <h5 class="fw-bold mb-2">Vulnerabilidades / hallazgos detectados por Kali</h5>
        </div>

        <div class="table-responsive kali-table-scroll">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>ID</th>
                <th>Herramienta</th>
                <th>Control</th>
                <th>Estado</th>
                <th>Riesgo</th>
                <th>Score</th>
                <th>Evidencia técnica</th>
                <th>Recomendación</th>
                <th>Archivo</th>
              </tr>
            </thead>
            <tbody>
              {% for f in findings_kali %}
              <tr>
                <td>#{{ f.id }}</td>
                <td><strong>{{ f.herramienta or '—' }}</strong></td>
                <td>{{ f.control or '—' }}</td>
                <td>{{ f.estado or '—' }}</td>
                <td>
                  <span class="badge bg-{{ 'success' if f.riesgo == 'Bajo' else 'warning text-dark' if f.riesgo == 'Medio' else 'danger' }}">
                    {{ f.riesgo or '—' }}
                  </span>
                </td>
                <td>{{ "%.1f"|format(f.score or 0) }}%</td>
                <td class="evidence-cell">{{ f.evidencia or '—' }}</td>
                <td class="recommend-cell">{{ f.recomendacion or '—' }}</td>
                <td style="min-width:260px;">{{ f.archivo_salida or '—' }}</td>
              </tr>
              {% else %}
              <tr>
                <td colspan="9" class="text-center text-muted py-4">
                  No hay hallazgos Kali registrados para este Scorecard.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="soft-table-wrap mb-3">
        <div class="p-3 pb-0">
          <h5 class="fw-bold mb-2">Salidas por herramienta</h5>
        </div>

        <div class="table-responsive kali-table-scroll">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>Herramienta</th>
                <th>Exit Code</th>
                <th>Duración</th>
                <th>Comando</th>
                <th>Archivo salida</th>
              </tr>
            </thead>
            <tbody>
              {% for o in outputs %}
              <tr>
                <td><strong>{{ o.herramienta }}</strong></td>
                <td>{{ o.exit_code }}</td>
                <td>{{ "%.1f"|format(o.duracion_segundos or 0) }} s</td>
                <td style="min-width:520px; white-space:pre-wrap;">{{ o.comando or '—' }}</td>
                <td style="min-width:320px;">{{ o.archivo_salida or '—' }}</td>
              </tr>
              {% else %}
              <tr>
                <td colspan="5" class="text-center text-muted py-4">
                  No hay salidas técnicas registradas.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      {% if run.salida_consola %}
      <div class="score-card">
        <h5 class="fw-bold mb-3">Log consolidado del escaneo Kali</h5>
        <pre>{{ run.salida_consola }}</pre>
      </div>
      {% endif %}
    </div>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            run=run,
            findings_kali=findings_kali,
            outputs=outputs
        ))
    )

def scorecard_score_darkweb(total_hallazgos, credencial_confirmada=False):
    if credencial_confirmada:
        return scorecard_get_param("darkweb_score_credenciales_confirmadas", 20), "Crítico"

    total_hallazgos = int(total_hallazgos or 0)

    if total_hallazgos <= 0:
        return scorecard_get_param("darkweb_score_sin_hallazgos", 100), "Bajo"
    if total_hallazgos <= 2:
        return scorecard_get_param("darkweb_score_1_2", 80), "Medio"
    if total_hallazgos <= 5:
        return scorecard_get_param("darkweb_score_3_5", 60), "Alto"

    return scorecard_get_param("darkweb_score_mas_5", 40), "Crítico"


def guardar_scorecard_darkweb_exposure(run_id, proveedor_id, proveedor_nombre, dominio, item):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_darkweb_exposures
        (run_id, proveedor_id, proveedor_nombre, dominio, fuente, tipo_exposicion,
         indicador, severidad, fecha, evidencia, recomendacion, url,
         credencial_confirmada, detalle_json, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        proveedor_id,
        proveedor_nombre,
        dominio,
        item.get("fuente"),
        item.get("tipo_exposicion"),
        item.get("indicador"),
        item.get("severidad"),
        item.get("fecha"),
        item.get("evidencia"),
        item.get("recomendacion"),
        item.get("url"),
        1 if item.get("credencial_confirmada") else 0,
        json.dumps(item, ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def consultar_hibp_domain_scorecard(dominio):
    resultados = []
    api_key = os.getenv("HIBP_API_KEY", "").strip()

    if not api_key or not dominio:
        return resultados

    try:
        url = f"https://haveibeenpwned.com/api/v3/breachedDomain/{dominio}"
        headers = {
            "hibp-api-key": api_key,
            "user-agent": "GRAC-Scorecard-SGSI"
        }

        resp = requests.get(url, headers=headers, timeout=20)

        if resp.status_code == 404:
            return []

        if resp.status_code in [401, 403]:
            resultados.append({
                "fuente": "Have I Been Pwned",
                "tipo_exposicion": "Consulta no autorizada / dominio no verificado",
                "indicador": dominio,
                "severidad": "Medio",
                "fecha": "",
                "evidencia": "HIBP requiere API Key válida y dominio verificado para búsqueda por dominio.",
                "recomendacion": "Configurar HIBP_API_KEY y verificar el dominio en Have I Been Pwned.",
                "url": "https://haveibeenpwned.com/API/v3",
                "credencial_confirmada": False
            })
            return resultados

        if resp.status_code != 200:
            return []

        data = resp.json() or {}

        for alias, breaches in data.items():
            correo = f"{alias}@{dominio}"
            breaches = breaches or []

            resultados.append({
                "fuente": "Have I Been Pwned",
                "tipo_exposicion": "Correo corporativo en brecha",
                "indicador": correo,
                "severidad": "Crítico",
                "fecha": "",
                "evidencia": "Brechas asociadas: " + ", ".join(breaches[:10]),
                "recomendacion": "Forzar cambio de contraseña, revisar MFA, validar cuentas activas y solicitar plan de remediación al proveedor.",
                "url": "https://haveibeenpwned.com/",
                "credencial_confirmada": True
            })

    except Exception as e:
        print("Error consultando HIBP Scorecard:", repr(e))

    return resultados


def consultar_darkweb_gdelt_osint_scorecard(proveedor_nombre, dominio):
    resultados = []

    try:
        terminos = []

        if proveedor_nombre and proveedor_nombre != "Proveedor no asociado":
            terminos += [
                f'"{proveedor_nombre}" "dark web"',
                f'"{proveedor_nombre}" "credential leak"',
                f'"{proveedor_nombre}" "password leak"',
                f'"{proveedor_nombre}" "stealer logs"',
                f'"{proveedor_nombre}" "data dump"',
            ]

        if dominio:
            terminos += [
                f'"{dominio}" "dark web"',
                f'"{dominio}" "credential leak"',
                f'"{dominio}" "password leak"',
                f'"{dominio}" "stealer logs"',
                f'"{dominio}" "data dump"',
            ]

        query = " OR ".join(terminos[:8])
        if not query:
            return []

        resp = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={
                "query": query,
                "mode": "ArtList",
                "format": "json",
                "maxrecords": 10,
                "sort": "HybridRel"
            },
            timeout=15
        )

        if resp.status_code != 200:
            return []

        data = resp.json() or {}
        vistos = set()

        for art in data.get("articles") or []:
            titulo = (art.get("title") or "").strip()
            link = (art.get("url") or "").strip()

            if not titulo or not link or link.lower() in vistos:
                continue

            vistos.add(link.lower())

            texto = titulo.lower()
            severidad = "Medio"

            if any(x in texto for x in ["password", "credential", "stealer", "dump", "dark web", "leak"]):
                severidad = "Alto"

            if any(x in texto for x in ["millions", "massive", "critical", "ransomware"]):
                severidad = "Crítico"

            resultados.append({
                "fuente": "GDELT + búsqueda OSINT",
                "tipo_exposicion": "Mención pública de exposición / leak",
                "indicador": dominio or proveedor_nombre,
                "severidad": severidad,
                "fecha": art.get("seendate") or "",
                "evidencia": titulo[:600],
                "recomendacion": "Validar fuente, solicitar confirmación al proveedor y requerir evidencia de contención.",
                "url": link,
                "credencial_confirmada": False
            })

    except Exception as e:
        print("Error consultando GDELT Dark Web OSINT:", repr(e))

    return resultados


def evaluar_darkweb_exposure_scorecard(run_id, proveedor_id, proveedor_nombre, dominio):
    exposiciones = []

    exposiciones += consultar_hibp_domain_scorecard(dominio)
    exposiciones += consultar_darkweb_gdelt_osint_scorecard(proveedor_nombre, dominio)

    vistos = set()
    dedup = []

    for item in exposiciones:
        key = f"{item.get('fuente')}|{item.get('indicador')}|{item.get('url')}|{item.get('evidencia')}".lower()
        if key in vistos:
            continue
        vistos.add(key)
        dedup.append(item)

    for item in dedup:
        guardar_scorecard_darkweb_exposure(run_id, proveedor_id, proveedor_nombre, dominio, item)

    total = len(dedup)
    credencial_confirmada = any(x.get("credencial_confirmada") for x in dedup)
    score, riesgo = scorecard_score_darkweb(total, credencial_confirmada)

    evidencia = (
        f"Fuentes consultadas: Have I Been Pwned + GDELT + búsqueda OSINT. Hallazgos identificados: {total}."
        if total else
        "Fuentes consultadas: Have I Been Pwned + GDELT + búsqueda OSINT. No se identificaron hallazgos de exposición pública o dark web."
    )

    guardar_scorecard_finding(run_id, {
        "categoria": "Dark Web / Exposure Intelligence",
        "herramienta": "Have I Been Pwned + GDELT + búsqueda OSINT",
        "control": "Exposición Dark Web / Leaks",
        "estado": "Con hallazgos" if total else "Sin hallazgos",
        "riesgo": riesgo,
        "severidad": riesgo,
        "score": score,
        "evidencia": evidencia,
        "recomendacion": "Validar fuentes, solicitar explicación al proveedor, rotar credenciales comprometidas y verificar MFA." if total else "Mantener monitoreo periódico."
    })

    return score, riesgo, total, credencial_confirmada

