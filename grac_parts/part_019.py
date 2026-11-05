@app.route("/proveedores/scorecard/parametros", methods=["GET", "POST"])
@login_required
def proveedores_scorecard_parametros():
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para parametrizar Scorecard.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no puede modificar parámetros.", "danger")
        return redirect(url_for("proveedores_scorecard_dashboard"))

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        accion = request.form.get("accion")

        if accion == "guardar_parametros":
            claves_numericas = [
                "peso_dns",
                "peso_ip",
                "peso_kali",
                "peso_incidentes",
                "peso_darkweb",
                "darkweb_score_sin_hallazgos",
                "darkweb_score_1_2",
                "darkweb_score_3_5",
                "darkweb_score_mas_5",
                "darkweb_score_credenciales_confirmadas",
            ]

            for clave in claves_numericas:
                valor = request.form.get(clave, type=float)
                if valor is None:
                    valor = scorecard_get_param(clave, 0)

                cur.execute("""
                    INSERT INTO scorecard_parametros (clave, valor, descripcion)
                    VALUES (?, ?, ?)
                    ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor
                """, (
                    clave,
                    valor,
                    clave.replace("_", " ").title()
                ))

            conn.commit()

            registrar_log(
                getattr(user, "username", "Sistema"),
                "Actualizó parámetros generales del Scorecard de Proveedores"
            )

            flash("Parámetros generales actualizados correctamente.", "success")
            conn.close()
            return redirect(url_for("proveedores_scorecard_parametros"))

        elif accion == "agregar_riesgo":
            nombre = (request.form.get("nombre_riesgo") or "").strip()
            score_min = request.form.get("score_min", type=float)
            color_bootstrap = (request.form.get("color_bootstrap") or "secondary").strip()
            orden = request.form.get("orden", type=int) or 0

            if not nombre:
                flash("Debe indicar el nombre del nivel de riesgo.", "danger")
                conn.close()
                return redirect(url_for("proveedores_scorecard_parametros"))

            if score_min is None:
                flash("Debe indicar el score mínimo del nivel de riesgo.", "danger")
                conn.close()
                return redirect(url_for("proveedores_scorecard_parametros"))

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

            registrar_log(
                getattr(user, "username", "Sistema"),
                f"Agregó nivel de riesgo Scorecard: {nombre} desde {score_min}"
            )

            flash("Nivel de riesgo agregado correctamente.", "success")
            conn.close()
            return redirect(url_for("proveedores_scorecard_parametros"))

        elif accion == "actualizar_riesgos":
            ids = request.form.getlist("risk_id")

            for rid in ids:
                nombre = (request.form.get(f"nombre_{rid}") or "").strip()
                score_min = request.form.get(f"score_min_{rid}", type=float)
                color_bootstrap = (request.form.get(f"color_{rid}") or "secondary").strip()
                orden = request.form.get(f"orden_{rid}", type=int) or 0
                activo = 1 if request.form.get(f"activo_{rid}") else 0

                if not nombre:
                    continue

                if score_min is None:
                    score_min = 0

                cur.execute("""
                    UPDATE scorecard_risk_levels
                    SET nombre = ?, score_min = ?, color_bootstrap = ?, orden = ?, activo = ?
                    WHERE id = ?
                """, (
                    nombre,
                    score_min,
                    color_bootstrap,
                    orden,
                    activo,
                    rid
                ))

            conn.commit()

            registrar_log(
                getattr(user, "username", "Sistema"),
                "Actualizó niveles dinámicos de riesgo del Scorecard"
            )

            flash("Niveles de riesgo actualizados correctamente.", "success")
            conn.close()
            return redirect(url_for("proveedores_scorecard_parametros"))

        elif accion == "eliminar_riesgo":
            rid = request.form.get("risk_id_delete", type=int)

            if rid:
                cur.execute("DELETE FROM scorecard_risk_levels WHERE id = ?", (rid,))
                conn.commit()

                registrar_log(
                    getattr(user, "username", "Sistema"),
                    f"Eliminó nivel de riesgo Scorecard ID {rid}"
                )

                flash("Nivel de riesgo eliminado correctamente.", "success")

            conn.close()
            return redirect(url_for("proveedores_scorecard_parametros"))

    cur.execute("SELECT * FROM scorecard_parametros ORDER BY clave ASC")
    rows = cur.fetchall()

    cur.execute("""
        SELECT *
        FROM scorecard_risk_levels
        ORDER BY score_min DESC, orden ASC, id ASC
    """)
    risk_levels = cur.fetchall()

    conn.close()

    params = {r["clave"]: r for r in rows}

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
        max-width:1500px;
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
        content:"SGSI · Parámetros Scorecard";
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
        margin-bottom:18px;
      }

      .param-section-title,
      .card h5,
      .card h6{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }

      .soft-table-wrap,
      .table-responsive{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        background:#ffffff;
        border-radius:14px;
        border:1px solid #dbe6f4;
        box-shadow:0 12px 24px rgba(15,23,42,.10);
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

      .risk-help{
        font-size:.86rem;
        color:#607086;
        font-weight:700;
        line-height:1.45;
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
        <h1 class="score-header-text">Parametrización Scorecard de Proveedores</h1>
      </div>

      <div class="score-card">
        <form method="POST">
          <input type="hidden" name="accion" value="guardar_parametros">

          <h5 class="param-section-title">1. Pesos del Score Total</h5>

          <div class="alert alert-info">
            La suma recomendada es 100%. Si la suma cambia, el sistema normaliza automáticamente los pesos.
          </div>

          <div class="row g-3 mb-4">
            {% for key,label in [
              ('peso_dns','DNS Health (%)'),
              ('peso_ip','IP Reputation (%)'),
              ('peso_kali','Kali Linux (%)'),
              ('peso_incidentes','Incidentes / Brechas (%)'),
              ('peso_darkweb','Dark Web Exposure (%)')
            ] %}
            <div class="col-md">
              <label class="form-label fw-bold">{{ label }}</label>
              <input type="number" step="0.01" min="0" max="100" name="{{ key }}" class="form-control"
                     value="{{ params[key].valor if key in params else 0 }}">
            </div>
            {% endfor %}
          </div>

          <hr>

          <h5 class="param-section-title">2. Score Dark Web / Exposure Intelligence</h5>

          <div class="alert alert-secondary">
            Fuentes consultadas: <strong>Have I Been Pwned + GDELT + búsqueda OSINT</strong>.
          </div>

          <div class="row g-3 mb-4">
            {% for key,label in [
              ('darkweb_score_sin_hallazgos','Sin hallazgos'),
              ('darkweb_score_1_2','1 a 2 hallazgos'),
              ('darkweb_score_3_5','3 a 5 hallazgos'),
              ('darkweb_score_mas_5','Más de 5 hallazgos'),
              ('darkweb_score_credenciales_confirmadas','Credenciales confirmadas')
            ] %}
            <div class="col-md">
              <label class="form-label fw-bold">{{ label }}</label>
              <input type="number" step="0.01" min="0" max="100" name="{{ key }}" class="form-control"
                     value="{{ params[key].valor if key in params else 0 }}">
            </div>
            {% endfor %}
          </div>

          <div class="d-flex justify-content-end">
            <button class="btn btn-primary rounded-pill px-4">
              💾 Guardar parámetros generales
            </button>
          </div>
        </form>
      </div>

      <div class="score-card">
        <h5 class="param-section-title">3. Agregar nivel de riesgo</h5>

        <form method="POST">
          <input type="hidden" name="accion" value="agregar_riesgo">

          <div class="row g-3 align-items-end">
            <div class="col-md-4">
              <label class="form-label fw-bold">Nombre del nivel</label>
              <input type="text" name="nombre_riesgo" class="form-control" placeholder="Ej: Aceptable, Moderado, Alto, Crítico" required>
            </div>

            <div class="col-md-2">
              <label class="form-label fw-bold">Score mínimo</label>
              <input type="number" step="0.01" min="0" max="100" name="score_min" class="form-control" required>
            </div>

            <div class="col-md-3">
              <label class="form-label fw-bold">Color Bootstrap</label>
              <select name="color_bootstrap" class="form-select">
                <option value="success">Verde / success</option>
                <option value="warning text-dark">Amarillo / warning</option>
                <option value="danger">Rojo / danger</option>
                <option value="dark">Negro / dark</option>
                <option value="secondary">Gris / secondary</option>
                <option value="primary">Azul / primary</option>
                <option value="info text-dark">Info / info</option>
              </select>
            </div>

            <div class="col-md-1">
              <label class="form-label fw-bold">Orden</label>
              <input type="number" name="orden" class="form-control" value="0">
            </div>

            <div class="col-md-2">
              <button class="btn btn-success rounded-pill w-100">
                ➕ Agregar
              </button>
            </div>
          </div>

          <div class="risk-help mt-2">
            El sistema evalúa desde el score más alto hacia abajo. Ejemplo: Aceptable desde 85, Moderado desde 70, Elevado desde 50, Crítico desde 0.
          </div>
        </form>
      </div>

      <div class="score-card">
        <h5 class="param-section-title">4. Niveles de riesgo configurados</h5>

        <form method="POST">
          <input type="hidden" name="accion" value="actualizar_riesgos">

          <div class="soft-table-wrap">
            <div class="table-responsive">
              <table class="table table-hover align-middle mb-0">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nombre</th>
                    <th>Score mínimo</th>
                    <th>Color</th>
                    <th>Orden</th>
                    <th>Activo</th>
                    <th>Eliminar</th>
                  </tr>
                </thead>
                <tbody>
                  {% for r in risk_levels %}
                  <tr>
                    <td>
                      #{{ r.id }}
                      <input type="hidden" name="risk_id" value="{{ r.id }}">
                    </td>

                    <td>
                      <input type="text" name="nombre_{{ r.id }}" class="form-control" value="{{ r.nombre }}">
                    </td>

                    <td>
                      <input type="number" step="0.01" min="0" max="100" name="score_min_{{ r.id }}" class="form-control" value="{{ r.score_min }}">
                    </td>

                    <td>
                      <select name="color_{{ r.id }}" class="form-select">
                        {% for val,label in [
                          ('success','Verde / success'),
                          ('warning text-dark','Amarillo / warning'),
                          ('danger','Rojo / danger'),
                          ('dark','Negro / dark'),
                          ('secondary','Gris / secondary'),
                          ('primary','Azul / primary'),
                          ('info text-dark','Info / info')
                        ] %}
                          <option value="{{ val }}" {% if r.color_bootstrap == val %}selected{% endif %}>{{ label }}</option>
                        {% endfor %}
                      </select>
                    </td>

                    <td>
                      <input type="number" name="orden_{{ r.id }}" class="form-control" value="{{ r.orden or 0 }}">
                    </td>

                    <td class="text-center">
                      <input type="checkbox" name="activo_{{ r.id }}" class="form-check-input" {% if r.activo %}checked{% endif %}>
                    </td>

                    <td>
                      <button type="submit"
                              formaction="{{ url_for('proveedores_scorecard_parametros') }}"
                              formmethod="POST"
                              name="accion"
                              value="eliminar_riesgo"
                              class="btn btn-sm btn-outline-danger rounded-pill"
                              onclick="this.form.risk_id_delete.value='{{ r.id }}'; return confirm('¿Eliminar este nivel de riesgo?');">
                        Eliminar
                      </button>
                    </td>
                  </tr>
                  {% else %}
                  <tr>
                    <td colspan="7" class="text-center text-muted py-4">
                      No hay niveles de riesgo configurados.
                    </td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>

          <input type="hidden" name="risk_id_delete" value="">

          <div class="d-flex justify-content-between mt-3">
            <a href="{{ url_for('proveedores_scorecard_dashboard') }}" class="btn btn-outline-secondary rounded-pill px-4">
              Volver
            </a>

            <button class="btn btn-primary rounded-pill px-4">
              💾 Guardar niveles de riesgo
            </button>
          </div>
        </form>
      </div>
    </div>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            params=params,
            risk_levels=risk_levels
        ))
    )


# =============================================================================
#            SCORECARD TERCEROS INDEPENDIENTE
#            DNS HEALTH / IP REPUTATION / HACKER CHATTER / ESCANEO KALI PROPIO
# =============================================================================


SCORECARD_PROPONENTES_DB_PATH = os.path.join(app.instance_path, "scorecard_proponentes.db")
SCORECARD_PROPONENTES_UPLOAD_DIR = os.path.join(app.instance_path, "scorecard_proponentes_outputs")
os.makedirs(SCORECARD_PROPONENTES_UPLOAD_DIR, exist_ok=True)


# ============================================================
# DB INDEPENDIENTE SCORECARD PROPONENTES
# ============================================================

def get_scorecard_proponentes_db_connection():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(SCORECARD_PROPONENTES_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_scorecard_proponentes_db():
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    # ===== PARAMETROS =====
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_parametros (
            clave TEXT PRIMARY KEY,
            valor REAL NOT NULL,
            descripcion TEXT
        )
    """)

    # ===== NIVELES DE RIESGO =====
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

        ("darkweb_score_sin_hallazgos", 100, "Sin hallazgos de riesgo"),
        ("darkweb_score_bajo", 90, "Hallazgos de severidad Baja"),
        ("darkweb_score_medio", 75, "Hallazgos de severidad Media"),
        ("darkweb_score_alto", 55, "Hallazgos de severidad Alta"),
        ("darkweb_score_critico", 25, "Hallazgos de severidad Crítica"),
        ("darkweb_score_credenciales_confirmadas", 20, "Credenciales confirmadas"),

        ("dns_score_a_ok", 100, "Registro A/CNAME OK"),
        ("dns_score_a_no_detectado", 0, "Registro A/CNAME no detectado"),
        ("dns_score_mx_ok", 100, "MX OK"),
        ("dns_score_mx_no_detectado", 70, "MX no detectado"),
        ("dns_score_ns_ok", 100, "NS OK"),
        ("dns_score_ns_no_detectado", 0, "NS no detectado"),
        ("dns_score_spf_ok", 100, "SPF OK"),
        ("dns_score_spf_no_configurado", 0, "SPF no configurado"),
        ("dns_score_dmarc_ok", 100, "DMARC OK"),
        ("dns_score_dmarc_p_none", 70, "DMARC p=none"),
        ("dns_score_dmarc_no_configurado", 0, "DMARC no configurado"),
    ]

    for clave, valor, descripcion in parametros_default:
        cur.execute("""
            INSERT OR IGNORE INTO scorecard_parametros (clave, valor, descripcion)
            VALUES (?, ?, ?)
        """, (clave, valor, descripcion))

    # ===== RISK LEVELS =====
    cur.execute("SELECT COUNT(*) FROM scorecard_risk_levels")
    if cur.fetchone()[0] == 0:
        niveles = [
            ("Bajo", 85, "success", 1),
            ("Medio", 70, "warning text-dark", 2),
            ("Alto", 50, "danger", 3),
            ("Crítico", 0, "dark", 4),
        ]

        for n in niveles:
            cur.execute("""
                INSERT INTO scorecard_risk_levels
                (nombre, score_min, color_bootstrap, orden, activo, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                n[0], n[1], n[2], n[3], 1,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

    conn.commit()
    conn.close()

init_scorecard_proponentes_db()


def migrar_scorecard_proponentes_informe_ai():
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(scorecard_proponentes_runs)")
    cols = [r["name"] for r in cur.fetchall()]

    if "informe_ejecutivo_ai" not in cols:
        cur.execute("ALTER TABLE scorecard_proponentes_runs ADD COLUMN informe_ejecutivo_ai TEXT")

    if "informe_ejecutivo_editado" not in cols:
        cur.execute("ALTER TABLE scorecard_proponentes_runs ADD COLUMN informe_ejecutivo_editado TEXT")

    if "informe_ejecutivo_fecha" not in cols:
        cur.execute("ALTER TABLE scorecard_proponentes_runs ADD COLUMN informe_ejecutivo_fecha TEXT")

    if "informe_ejecutivo_usuario" not in cols:
        cur.execute("ALTER TABLE scorecard_proponentes_runs ADD COLUMN informe_ejecutivo_usuario TEXT")

    conn.commit()
    conn.close()


migrar_scorecard_proponentes_informe_ai()

def migrar_scorecard_proponentes_herramientas_kali():
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(scorecard_proponentes_runs)")
    cols = [r["name"] for r in cur.fetchall()]

    if "herramientas_kali" not in cols:
        cur.execute("ALTER TABLE scorecard_proponentes_runs ADD COLUMN herramientas_kali TEXT")

    conn.commit()
    conn.close()

migrar_scorecard_proponentes_herramientas_kali()


SCORECARD_PROPONENTES_HERRAMIENTAS_KALI_VALIDAS = [
    "nmap",
    "whatweb",
    "nikto",
    "testssl",
    "nuclei",
    "zap"
]


def scorecard_proponentes_normalizar_herramientas_kali(lista):
    herramientas = []

    for h in lista or []:
        h = (h or "").strip().lower()
        if h in SCORECARD_PROPONENTES_HERRAMIENTAS_KALI_VALIDAS and h not in herramientas:
            herramientas.append(h)

    if not herramientas:
        herramientas = ["nmap", "nikto", "nuclei"]

    return herramientas


def scorecard_proponentes_label_herramientas_kali(herramientas):
    labels = {
        "nmap": "Nmap",
        "whatweb": "WhatWeb",
        "nikto": "Nikto",
        "testssl": "testssl",
        "nuclei": "Nuclei",
        "zap": "OWASP ZAP Full Scan"
    }

    return ", ".join(labels.get(h, h) for h in herramientas or [])

# ============================================================
# PERMISOS - SCORECARD PROPONENTES / TERCEROS
# ============================================================

SCORECARD_PROPONENTES_PERMISO = "Security Scorecard de Terceros"


def scorecard_proponentes_user_permiso():
    user = User.query.get(session.get("user_id"))

    if not user:
        return None, False, False

    if user.role == "admin":
        return user, True, False

    if user.role == "auditor":
        return user, True, True

    if verificar_permiso(user, SCORECARD_PROPONENTES_PERMISO):
        return user, True, False

    return user, False, False


# ============================================================
# UTILIDADES PROPONENTES
# ============================================================

def scorecard_proponentes_run_dir(run_id, dominio):
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", dominio or "target")
    path = os.path.join(SCORECARD_PROPONENTES_UPLOAD_DIR, f"scorecard_proponente_{run_id}_{safe}")
    os.makedirs(path, exist_ok=True)
    return path


def scorecard_proponentes_output_file(run_dir, herramienta, ext="txt"):
    herramienta = re.sub(r"[^a-zA-Z0-9_.-]+", "_", herramienta or "output")
    return os.path.join(run_dir, f"{herramienta}.{ext}")


def scorecard_proponentes_set_progress(run_id, pct=None, stage=None, tool=None, estado=None, error=None):
    conn = get_scorecard_proponentes_db_connection()
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
        cur.execute(f"""
            UPDATE scorecard_proponentes_runs
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        conn.commit()

    conn.close()


def guardar_scorecard_proponentes_finding(run_id, item):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_proponentes_findings
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


def guardar_scorecard_proponentes_output(run_id, herramienta, comando, archivo_salida, exit_code, duracion):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_proponentes_outputs
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


def guardar_scorecard_proponentes_incidente(run_id, proponente_nombre, dominio, item):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_proponentes_incidents
        (run_id, proponente_nombre, dominio, fuente, titulo, url,
         fecha_incidente, severidad, descripcion, detalle_json, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        proponente_nombre,
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


def guardar_scorecard_proponentes_darkweb_exposure(run_id, proponente_nombre, dominio, item):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_proponentes_darkweb_exposures
        (run_id, proponente_nombre, dominio, fuente, tipo_exposicion,
         indicador, severidad, fecha, evidencia, recomendacion, url,
         credencial_confirmada, detalle_json, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        proponente_nombre,
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

# ============================================================
# DNS HEALTH PARAMETRIZABLE - PROPONENTES
# ============================================================

def evaluar_dns_health_proponentes_scorecard(dominio):
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

    scores_componentes = []

    def add(control, estado, riesgo, puntaje, evidencia, recomendacion, regla):
        scores_componentes.append(float(puntaje or 0))
        findings.append({
            "categoria": "DNS Health",
            "herramienta": "DNS Resolver",
            "control": control,
            "estado": estado,
            "riesgo": riesgo,
            "severidad": riesgo,
            "score": puntaje,
            "evidencia": evidencia,
            "recomendacion": recomendacion,
            "detalle": {
                "regla_calculo": regla,
                "modelo_score": "DNS Health parametrizable por control: A/CNAME, MX, NS, SPF y DMARC."
            }
        })

    if registros_a:
        puntaje = scorecard_proponentes_get_param("dns_score_a_ok", 100)
        add("Registro A", "OK", "Bajo", puntaje,
            f"{dominio_original}: " + ", ".join(registros_a[:8]),
            "Mantener monitoreo de resolución pública.",
            f"Registro A detectado → Score {puntaje}")
    elif registros_cname:
        puntaje = scorecard_proponentes_get_param("dns_score_a_ok", 100)
        add("Registro A/CNAME", "OK por CNAME", "Bajo", puntaje,
            f"{dominio_original} apunta por CNAME a: " + ", ".join(registros_cname[:8]),
            "Mantener monitoreo de resolución pública y destino CNAME autorizado.",
            f"Registro CNAME detectado → Score {puntaje}")
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_a_no_detectado", 0)
        add("Registro A", "No detectado", "Alto", puntaje,
            f"No se encontraron registros A ni CNAME para {dominio_original}.",
            "Validar publicación DNS del dominio o subdominio evaluado.",
            f"Registro A/CNAME no detectado → Score {puntaje}")

    if registros_mx:
        puntaje = scorecard_proponentes_get_param("dns_score_mx_ok", 100)
        add("MX", "OK", "Bajo", puntaje,
            f"{dominio_base}: " + ", ".join(registros_mx[:8]),
            "Mantener proveedores MX autorizados.",
            f"MX detectado → Score {puntaje}")
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_mx_no_detectado", 70)
        add("MX", "No detectado en dominio base", "Bajo", puntaje,
            f"No se encontraron registros MX para {dominio_base}. Esto puede ser aceptable si el dominio no recibe correo.",
            "Confirmar si el proveedor usa este dominio para correo. Si lo usa, configurar MX.",
            f"MX no detectado → Score {puntaje}")

    if registros_ns:
        puntaje = scorecard_proponentes_get_param("dns_score_ns_ok", 100)
        add("NS", "OK", "Bajo", puntaje,
            f"{dominio_base}: " + ", ".join(registros_ns[:8]),
            "Mantener gobierno sobre la administración DNS.",
            f"NS detectado → Score {puntaje}")
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_ns_no_detectado", 0)
        add("NS", "No detectado en dominio base", "Medio", puntaje,
            f"No se encontraron registros NS para {dominio_base}.",
            "Validar delegación DNS del dominio base.",
            f"NS no detectado → Score {puntaje}")

    if spf_ok:
        puntaje = scorecard_proponentes_get_param("dns_score_spf_ok", 100)
        add("SPF", "OK", "Bajo", puntaje,
            f"Se detectó registro SPF en {dominio_base}.",
            "Evitar configuraciones demasiado permisivas como +all.",
            f"SPF detectado → Score {puntaje}")
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_spf_no_configurado", 0)
        add("SPF", "No configurado en dominio base", "Alto", puntaje,
            f"No se encontró TXT con v=spf1 en {dominio_base}.",
            "Configurar SPF para mitigar spoofing si el dominio envía correo.",
            f"SPF no configurado → Score {puntaje}")

    if not dmarc_ok:
        puntaje = scorecard_proponentes_get_param("dns_score_dmarc_no_configurado", 0)
        add("DMARC", "No configurado en dominio base", "Alto", puntaje,
            f"No se encontró _dmarc.{dominio_base}.",
            "Configurar DMARC con política gradual.",
            f"DMARC no configurado → Score {puntaje}")
    elif dmarc_policy == "none":
        puntaje = scorecard_proponentes_get_param("dns_score_dmarc_p_none", 70)
        add("DMARC", "Configurado p=none", "Medio", puntaje,
            f"DMARC existe en _dmarc.{dominio_base}, pero está en modo monitoreo.",
            "Avanzar gradualmente a quarantine o reject.",
            f"DMARC p=none → Score {puntaje}")
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_dmarc_ok", 100)
        add("DMARC", "OK", "Bajo", puntaje,
            f"Política DMARC en _dmarc.{dominio_base}: {dmarc_policy or 'definida'}.",
            "Mantener monitoreo DMARC.",
            f"DMARC enforce detectado → Score {puntaje}")

    score = round(sum(scores_componentes) / len(scores_componentes), 2) if scores_componentes else 0
    return max(0, min(100, score)), findings

# ============================================================
# INCIDENT HISTORY PROPONENTES
# ============================================================

def evaluar_incident_history_proponentes_scorecard(run_id, proponente_nombre, dominio):
    incidentes = consultar_incidentes_osint_scorecard(proponente_nombre, dominio)

    for item in incidentes:
        guardar_scorecard_proponentes_incidente(run_id, proponente_nombre, dominio, item)

    total = len(incidentes)
    score, riesgo = scorecard_score_incidentes(incidentes)

    evidencia = (
        f"Se identificaron {total} referencias públicas o históricas asociadas a incidentes, brechas, ransomware, leaks o ataques."
        if total else
        "No se identificaron referencias públicas relevantes de brechas o incidentes en la consulta OSINT básica."
    )

    guardar_scorecard_proponentes_finding(run_id, {
        "categoria": "Incident History",
        "herramienta": "Catálogo histórico + OSINT Público",
        "control": "Brechas e incidentes de seguridad",
        "estado": "Con hallazgos" if total else "Sin hallazgos",
        "riesgo": riesgo,
        "severidad": riesgo,
        "score": score,
        "evidencia": evidencia,
        "recomendacion": (
            "Validar manualmente las fuentes públicas encontradas, solicitar explicación formal al proponente "
            "y pedir evidencia de remediación, mejoras de seguridad y controles posteriores al incidente."
            if total else
            "Mantener monitoreo periódico de noticias e incidentes públicos."
        )
    })

    return score, riesgo, total

def scorecard_proponentes_score_hacker_chatter_por_severidad(
    total_hallazgos,
    credencial_confirmada=False,
    severidad_max="Bajo"
):
    total_hallazgos = int(total_hallazgos or 0)
    severidad_max = (severidad_max or "Bajo").strip()

    if total_hallazgos <= 0:
        return (
            scorecard_proponentes_get_param("darkweb_score_sin_hallazgos", 100),
            "Bajo",
            "Sin hallazgos de riesgo. Score parametrizado aplicado."
        )

    if credencial_confirmada:
        return (
            scorecard_proponentes_get_param("darkweb_score_credenciales_confirmadas", 20),
            "Crítico",
            "Credenciales confirmadas detectadas. Se aplica score crítico parametrizado."
        )

    if severidad_max in ["Crítico", "Critico", "Critical"]:
        return (
            scorecard_proponentes_get_param("darkweb_score_critico", 25),
            "Crítico",
            "Se detectó severidad máxima Crítica. Score parametrizado aplicado."
        )

    if severidad_max in ["Alto", "Alta", "High"]:
        return (
            scorecard_proponentes_get_param("darkweb_score_alto", 55),
            "Alto",
            "Se detectó severidad máxima Alta. Score parametrizado aplicado."
        )

    if severidad_max in ["Medio", "Media", "Medium"]:
        return (
            scorecard_proponentes_get_param("darkweb_score_medio", 75),
            "Medio",
            "Se detectó severidad máxima Media. Score parametrizado aplicado."
        )

    return (
        scorecard_proponentes_get_param("darkweb_score_bajo", 90),
        "Bajo",
        "Solo se detectaron hallazgos de severidad Baja. Score parametrizado aplicado."
    )

# ============================================================
# HACKER CHATTER / EXPOSURE INTELLIGENCE PROPONENTES
# SCORING POR SEVERIDAD MÁXIMA
# ============================================================

def evaluar_hacker_chatter_proponentes_scorecard(run_id, proponente_nombre, dominio, ip):
    scorecard_proponentes_set_progress(
        run_id,
        pct=30,
        stage="Consultando Hacker Chatter / Exposure Intelligence",
        tool="OSINT / APIs Proponentes"
    )

    hallazgos = []

    # ============================================================
    # LeakCheck independiente Proponentes
    # ============================================================
    try:
        api_key_leakcheck = scorecard_proponentes_get_api_key("leakcheck")

        if api_key_leakcheck:
            dominio_base = obtener_dominio_base(dominio)

            resp = requests.get(
                f"https://leakcheck.io/api/v2/query/{dominio_base}",
                params={"type": "domain", "limit": 100},
                headers={"Accept": "application/json", "X-API-Key": api_key_leakcheck},
                timeout=25
            )

            if resp.status_code == 200:
                data = resp.json() or {}
                found, results = scorecard_leakcheck_extraer_resultados(data)

                if found > 0:
                    hallazgos.append({
                        "fuente": "LeakCheck API - Proponentes",
                        "tipo_exposicion": "Credenciales / identidades filtradas",
                        "indicador": f"{dominio_base} - {found} registros encontrados",
                        "severidad": "Crítico" if found > 10 else "Alto" if found > 2 else "Medio",
                        "fecha": datetime.now().strftime("%Y-%m-%d"),
                        "evidencia": f"LeakCheck reportó {found} registros reales asociados al dominio {dominio_base}.",
                        "recomendacion": "Solicitar al proponente investigación formal, rotación de credenciales, MFA obligatorio y evidencia de remediación.",
                        "url": "https://leakcheck.io/",
                        "credencial_confirmada": True,
                        "detalle": {
                            "found": found,
                            "raw_passwords_omitted": True,
                            "penaliza_score": True,
                            "fuente_valida": True
                        }
                    })

            elif resp.status_code in [400, 401, 403, 422, 429]:
                hallazgos.append({
                    **scorecard_api_error_item(
                        "LeakCheck API - Proponentes",
                        f"HTTP {resp.status_code}: {resp.text[:300]}"
                    ),
                    "detalle": {
                        "no_penaliza_score": True,
                        "api_error": True,
                        "fuente_valida": False
                    }
                })

    except Exception as e:
        hallazgos.append({
            **scorecard_api_error_item("LeakCheck API - Proponentes", repr(e)),
            "detalle": {
                "no_penaliza_score": True,
                "api_error": True,
                "fuente_valida": False
            }
        })

    # ============================================================
    # HIBP independiente Proponentes
    # ============================================================
    try:
        api_key_hibp = scorecard_proponentes_get_api_key("hibp")

        if api_key_hibp:
            dominio_base = obtener_dominio_base(dominio)

            headers = {
                "hibp-api-key": api_key_hibp,
                "User-Agent": "GRAC-SGSI-Scorecard-Proponentes/1.0",
                "Accept": "application/json"
            }

            resp = requests.get(
                f"https://haveibeenpwned.com/api/v3/breacheddomain/{dominio_base}",
                params={"truncateResponse": "false"},
                headers=headers,
                timeout=25
            )

            if resp.status_code == 200:
                data = resp.json() or {}
                total_accounts = len(data.keys()) if isinstance(data, dict) else 0

                if total_accounts > 0:
                    hallazgos.append({
                        "fuente": "Have I Been Pwned API - Proponentes",
                        "tipo_exposicion": "Cuentas del dominio en brechas",
                        "indicador": f"{dominio_base} - {total_accounts} cuentas afectadas",
                        "severidad": "Crítico" if total_accounts > 10 else "Alto" if total_accounts > 2 else "Medio",
                        "fecha": datetime.now().strftime("%Y-%m-%d"),
                        "evidencia": f"HIBP reportó {total_accounts} cuentas reales del dominio {dominio_base} asociadas a brechas.",
                        "recomendacion": "Exigir al proponente revisión de cuentas afectadas, rotación de credenciales, MFA y detección de password reuse.",
                        "url": "https://haveibeenpwned.com/",
                        "credencial_confirmada": True,
                        "detalle": {
                            "total_accounts": total_accounts,
                            "raw_accounts_masked": True,
                            "penaliza_score": True,
                            "fuente_valida": True
                        }
                    })

            elif resp.status_code == 404:
                pass

            elif resp.status_code in [400, 401, 403, 429]:
                hallazgos.append({
                    **scorecard_api_error_item(
                        "Have I Been Pwned API - Proponentes",
                        f"HTTP {resp.status_code}: dominio no verificado, API key inválida, cuota o rate limit."
                    ),
                    "detalle": {
                        "no_penaliza_score": True,
                        "api_error": True,
                        "fuente_valida": False
                    }
                })

    except Exception as e:
        hallazgos.append({
            **scorecard_api_error_item("Have I Been Pwned API - Proponentes", repr(e)),
            "detalle": {
                "no_penaliza_score": True,
                "api_error": True,
                "fuente_valida": False
            }
        })

    # ============================================================
    # Shodan independiente Proponentes
    # ============================================================
    try:
        api_key_shodan = scorecard_proponentes_get_api_key("shodan")

        if api_key_shodan and ip:
            resp = requests.get(
                f"https://api.shodan.io/shodan/host/{ip}",
                params={"key": api_key_shodan},
                timeout=25
            )

            if resp.status_code == 200:
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

                        cves.append({
                            "cve": cve,
                            "cvss": cvss
                        })

                critical_cves = [x for x in cves if x["cvss"] >= 9]
                high_cves = [x for x in cves if 7 <= x["cvss"] < 9]

                if critical_cves:
                    severidad = "Crítico"
                elif high_cves or len(cves) > 0:
                    severidad = "Alto"
                else:
                    severidad = "Bajo"

                if cves:
                    hallazgos.append({
                        "fuente": "Shodan API - Proponentes",
                        "tipo_exposicion": "CVEs / servicios vulnerables expuestos",
                        "indicador": f"{ip} - CVEs: {len(cves)} - Puertos: {', '.join(str(p) for p in ports[:20])}",
                        "severidad": severidad,
                        "fecha": datetime.now().strftime("%Y-%m-%d"),
                        "evidencia": f"Shodan reportó {len(cves)} CVEs reales para la IP {ip}.",
                        "recomendacion": "Validar exposición de servicios, aplicar parches, cerrar puertos innecesarios y corregir CVEs.",
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
                            "country": data.get("country_name"),
                            "penaliza_score": True,
                            "fuente_valida": True
                        }
                    })

                elif ports:
                    hallazgos.append({
                        "fuente": "Shodan API - Proponentes",
                        "tipo_exposicion": "Servicios observados sin CVEs",
                        "indicador": f"{ip} - puertos observados: {', '.join(str(p) for p in ports[:20])}",
                        "severidad": "Bajo",
                        "fecha": datetime.now().strftime("%Y-%m-%d"),
                        "evidencia": f"Shodan reportó {len(ports)} puertos observados, pero sin CVEs asociadas.",
                        "recomendacion": "Validar que los servicios expuestos sean esperados. No penaliza score por ausencia de CVEs.",
                        "url": f"https://www.shodan.io/host/{ip}",
                        "credencial_confirmada": False,
                        "detalle": {
                            "ip": ip,
                            "ports": ports,
                            "hostnames": hostnames,
                            "cves": [],
                            "no_penaliza_score": True,
                            "fuente_valida": True,
                            "informativo": True
                        }
                    })

            elif resp.status_code == 404:
                pass

            elif resp.status_code in [400, 401, 403, 429]:
                hallazgos.append({
                    **scorecard_api_error_item(
                        "Shodan API - Proponentes",
                        f"HTTP {resp.status_code}: API key inválida, sin créditos o rate limit."
                    ),
                    "detalle": {
                        "no_penaliza_score": True,
                        "api_error": True,
                        "fuente_valida": False
                    }
                })

    except Exception as e:
        hallazgos.append({
            **scorecard_api_error_item("Shodan API - Proponentes", repr(e)),
            "detalle": {
                "no_penaliza_score": True,
                "api_error": True,
                "fuente_valida": False
            }
        })

    # ============================================================
    # OSINT público informativo
    # ============================================================
    for fuente_func, nombre_fuente in [
        (consultar_hacker_chatter_gdelt_scorecard, "GDELT"),
        (consultar_certificados_ct_scorecard, "crt.sh"),
        (consultar_github_exposure_scorecard, "GitHub OSINT"),
    ]:
        try:
            if nombre_fuente == "GDELT":
                items = fuente_func(proponente_nombre, dominio)
            elif nombre_fuente == "GitHub OSINT":
                items = fuente_func(proponente_nombre, dominio)
            else:
                items = fuente_func(dominio)

            for item in items or []:
                detalle = item.get("detalle") if isinstance(item.get("detalle"), dict) else {}
                detalle["no_penaliza_score"] = True
                detalle["informativo_osint"] = True
                detalle["fuente_valida"] = True
                item["detalle"] = detalle
                item["credencial_confirmada"] = False
                hallazgos.append(item)

        except Exception as e:
            print(f"Error {nombre_fuente} proponentes:", repr(e))

    # ============================================================
    # Clasificación final por severidad máxima
    # ============================================================

    severidad_orden = {
        "Bajo": 1,
        "Medio": 2,
        "Alto": 3,
        "Crítico": 4,
        "Critico": 4
    }

    severidad_max = "Bajo"
    credencial_confirmada = False
    total_riesgo = 0
    total_info = 0
    total_cves = 0
    fuentes_penalizadas = []
    fuentes_informativas = []

    for item in hallazgos:
        detalle = item.get("detalle") or {}

        penaliza = bool(detalle.get("penaliza_score"))
        no_penaliza = bool(detalle.get("no_penaliza_score"))

        if penaliza and not no_penaliza:
            total_riesgo += 1
            fuentes_penalizadas.append(item.get("fuente") or "Fuente no identificada")

            sev = item.get("severidad") or "Bajo"
            if severidad_orden.get(sev, 0) > severidad_orden.get(severidad_max, 0):
                severidad_max = sev

            if item.get("credencial_confirmada"):
                credencial_confirmada = True

            try:
                if isinstance(detalle, dict):
                    total_cves += len(detalle.get("cves") or [])
            except Exception:
                pass
        else:
            total_info += 1
            fuentes_informativas.append(item.get("fuente") or "Fuente informativa")

        guardar_scorecard_proponentes_darkweb_exposure(
            run_id,
            proponente_nombre,
            dominio,
            item
        )

    score, riesgo, regla_score = scorecard_proponentes_score_hacker_chatter_por_severidad(
        total_riesgo,
        credencial_confirmada=credencial_confirmada,
        severidad_max=severidad_max
    )

    estado = "Con hallazgos de riesgo" if total_riesgo else "Sin hallazgos de riesgo"

    evidencia = (
        f"Se identificaron {total_riesgo} hallazgos válidos que penalizan el score "
        f"y {total_info} hallazgos informativos que no afectan el cálculo. "
        f"Severidad máxima detectada: {severidad_max}. "
        f"Regla aplicada: {regla_score} "
        f"Fuentes que penalizan: {', '.join(sorted(set(fuentes_penalizadas))) if fuentes_penalizadas else 'Ninguna'}."
    )

    recomendacion = (
        "Validar hallazgos con el proponente, solicitar evidencias de remediación, rotación de credenciales, "
        "MFA, hardening, cierre de servicios expuestos y confirmación formal de contención."
        if total_riesgo else
        "No se encontraron hallazgos válidos que afecten el score. Mantener monitoreo periódico."
    )

    guardar_scorecard_proponentes_finding(run_id, {
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
            "fuentes_penalizadas": list(sorted(set(fuentes_penalizadas))),
            "fuentes_informativas": list(sorted(set(fuentes_informativas))),
            "api_scope": "proponentes_independiente",
            "regla_calculo": regla_score,
            "modelo_score": "Scoring por severidad máxima: Sin hallazgos, Bajo, Medio, Alto, Crítico o Credenciales confirmadas."
        }
    })

    scorecard_proponentes_set_progress(
        run_id,
        pct=40,
        stage="Hacker Chatter / Exposure Intelligence finalizado",
        tool=None
    )

    return score, riesgo, total_riesgo, credencial_confirmada

# ============================================================
# KALI SCAN INDEPENDIENTE PROPONENTES
# ============================================================

# ============================================================
# KALI SCORECARD PROPONENTES USANDO EL MISMO MOTOR DE
# REGISTRO DE VULNERABILIDADES
# ============================================================

def scorecard_proponentes_map_severidad_vuln(sev):
    sev = (sev or "").strip()

    if sev in ["Crítica", "Critica", "Critical"]:
        return "Crítico"

    if sev in ["Alta", "High"]:
        return "Alto"

    if sev in ["Media", "Medium"]:
        return "Medio"

    return "Bajo"


def scorecard_proponentes_score_kali_desde_findings(findings):
    criticas = 0
    altas = 0
    medias = 0
    bajas = 0

    for f in findings:
        sev = (f.severidad or "").strip()

        if sev in ["Crítica", "Critica"]:
            criticas += 1
        elif sev == "Alta":
            altas += 1
        elif sev == "Media":
            medias += 1
        else:
            bajas += 1

    descuento = (criticas * 25) + (altas * 15) + (medias * 7) + (bajas * 3)
    score = 100 - min(100, descuento)

    return max(0, min(100, score)), {
        "criticas": criticas,
        "altas": altas,
        "medias": medias,
        "bajas": bajas,
        "total": len(findings)
    }


def scorecard_proponentes_copiar_findings_vuln(scorecard_run_id, vuln_run_id):
    findings = VulnerabilityScanFinding.query.filter_by(
        run_id=vuln_run_id
    ).order_by(VulnerabilityScanFinding.id.asc()).all()

    for f in findings:
        riesgo = scorecard_proponentes_map_severidad_vuln(f.severidad)

        guardar_scorecard_proponentes_finding(scorecard_run_id, {
            "categoria": "Kali Linux Scan",
            "herramienta": f.fuente or "Kali Linux",
            "control": f.titulo or "Hallazgo técnico",
            "estado": "Detectado",
            "riesgo": riesgo,
            "severidad": riesgo,
            "score": (
                20 if riesgo == "Crítico"
                else 45 if riesgo == "Alto"
                else 70 if riesgo == "Medio"
                else 100
            ),
            "evidencia": f.evidencia or f.descripcion or "Hallazgo detectado por el motor de vulnerabilidades.",
            "recomendacion": f.recomendacion_base or "Validar el hallazgo, aplicar remediación y repetir el escaneo.",
            "archivo_salida": "",
            "detalle": {
                "vulnerability_scan_run_id": vuln_run_id,
                "vulnerability_finding_id": f.id,
                "fuente_original": f.fuente,
                "titulo_original": f.titulo,
                "severidad_original": f.severidad,
                "cvss": f.cvss,
                "cve": f.cve,
                "puerto": f.puerto,
                "protocolo": f.protocolo,
                "servicio": f.servicio
            }
        })

    return findings

def scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, vuln_run_id, min_pct=45, max_pct=95):
    vuln_run = VulnerabilityScanRun.query.get(vuln_run_id)
    if not vuln_run:
        return

    vuln_pct = int(vuln_run.progress_pct or 0)
    mapped_pct = min_pct + int((vuln_pct / 100) * (max_pct - min_pct))

    stage = vuln_run.current_stage or "Ejecutando escaneo Kali Linux"
    tool = vuln_run.current_tool or "Kali Linux"

    if tool == "dispatcher":
        tool = "Inicializando"

    scorecard_proponentes_set_progress(
        scorecard_run_id,
        pct=mapped_pct,
        stage=stage,
        tool=tool,
        estado="ejecutando"
    )


def ejecutar_scan_web_scorecard_proponentes_sin_whatweb(
    run,
    cfg,
    run_dir,
    crear_vulns=False,
    crear_planes=False,
    scorecard_run_id=None
):
    target = normalizar_target_para_scan(run.target)
    host = extraer_host_de_target(target)
    logs = []

    try:
        herramientas = json.loads(run.herramientas or "[]")
    except Exception:
        herramientas = []

    herramientas = scorecard_proponentes_normalizar_herramientas_kali(herramientas)

    # =========================
    # NMAP
    # =========================
    if "nmap" in herramientas:
        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=10, stage="Ejecutando Nmap", tool="nmap")
        db.session.commit()

        if scorecard_run_id:
            scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        if host:
            res_nmap = ejecutar_nmap(run.id, cfg, host, run_dir)
            logs.append(f"[NMAP]\nSTDOUT:\n{res_nmap['stdout']}\nSTDERR:\n{res_nmap['stderr']}\n")

            findings = parse_nmap_xml(run_dir)
            guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

    # =========================
    # WHATWEB
    # =========================
    if "whatweb" in herramientas:
        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=25, stage="Ejecutando WhatWeb", tool="whatweb")
        db.session.commit()

        if scorecard_run_id:
            scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        res_whatweb = ejecutar_whatweb(run.id, cfg, target, run_dir)
        logs.append(f"[WHATWEB]\nSTDOUT:\n{res_whatweb['stdout']}\nSTDERR:\n{res_whatweb['stderr']}\n")

        findings = parse_txt_findings_generic(
            scan_output_file(run_dir, "whatweb_scan", "txt"),
            "whatweb"
        )
        guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

    # =========================
    # NIKTO
    # =========================
    if "nikto" in herramientas:
        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=40, stage="Ejecutando Nikto", tool="nikto")
        db.session.commit()

        if scorecard_run_id:
            scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        res_nikto = ejecutar_nikto(run.id, cfg, target, run_dir)
        logs.append(f"[NIKTO]\nSTDOUT:\n{res_nikto['stdout']}\nSTDERR:\n{res_nikto['stderr']}\n")

        findings = parse_txt_findings_generic(
            scan_output_file(run_dir, "nikto_scan", "txt"),
            "nikto"
        )
        guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

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

        scan_set_progress(run.id, pct=55, stage="Ejecutando testssl", tool="testssl")
        db.session.commit()

        if scorecard_run_id:
            scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        res_testssl = ejecutar_testssl(run.id, cfg, ssl_target, run_dir)
        logs.append(f"[TESTSSL]\nSTDOUT:\n{res_testssl['stdout']}\nSTDERR:\n{res_testssl['stderr']}\n")

        findings = parse_txt_findings_generic(
            scan_output_file(run_dir, "testssl_scan", "txt"),
            "testssl"
        )
        guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

    # =========================
    # NUCLEI
    # =========================
    if "nuclei" in herramientas:
        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=70, stage="Ejecutando Nuclei", tool="nuclei")
        db.session.commit()

        if scorecard_run_id:
            scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        res_nuclei = ejecutar_nuclei(run.id, cfg, target, run_dir)
        logs.append(f"[NUCLEI]\nSTDOUT:\n{res_nuclei['stdout']}\nSTDERR:\n{res_nuclei['stderr']}\n")

        findings = parse_nuclei_jsonl(run_dir)
        guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

    # =========================
    # OWASP ZAP FULL SCAN
    # =========================
    if "zap" in herramientas:
        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=85, stage="Ejecutando OWASP ZAP Full Scan", tool="zap")
        db.session.commit()

        if scorecard_run_id:
            scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        res_zap = ejecutar_zap(run.id, cfg, target, run_dir)
        logs.append(f"[OWASP_ZAP_FULL_SCAN]\nSTDOUT:\n{res_zap['stdout']}\nSTDERR:\n{res_zap['stderr']}\n")

        findings = parse_zap_findings(run_dir)
        guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

    if scorecard_run_id:
        scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

    return logs


def ejecutar_full_scan_scorecard_proponentes_sin_whatweb(run_id, scorecard_run_id, crear_vulns=False, crear_planes=False):
    run = VulnerabilityScanRun.query.get_or_404(run_id)

    run.estado = "ejecutando"
    run.fecha_inicio = datetime.utcnow()
    run.progress_pct = 1
    run.current_tool = "Inicializando"
    run.current_stage = "Preparando herramientas de escaneo"
    run.cancel_requested = False
    run.stopped_by_user = False
    run.active_pid = None
    run.active_command = None
    db.session.commit()

    scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

    run_dir = scan_run_dir(run.id, run.target)
    log_path = scan_output_file(run_dir, "scan_log", "txt")

    try:
        cfg = _scan_cfg()

        faltantes = validar_herramientas_scan(cfg)
        if faltantes:
            raise RuntimeError("Herramientas no encontradas: " + " | ".join(faltantes))

        if run.target_type == "url":
            logs = ejecutar_scan_web_scorecard_proponentes_sin_whatweb(
                run,
                cfg,
                run_dir,
                crear_vulns,
                crear_planes,
                scorecard_run_id=scorecard_run_id
            )
        else:
            logs = ejecutar_scan_ip(
                run,
                cfg,
                run_dir,
                crear_vulns,
                crear_planes
            )

        scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

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

            scorecard_proponentes_set_progress(
                scorecard_run_id,
                pct=99,
                stage="Escaneo Kali detenido",
                tool=None,
                estado="error",
                error="Escaneo detenido por el usuario."
            )

            return {"ok": False, "stopped": True}

        scan_set_progress(run.id, pct=95, stage="Consolidando resultados", tool="sync")
        scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(logs or []))

        run = VulnerabilityScanRun.query.get(run.id)
        run.archivo_log = log_path
        run.salida_consola = ("\n\n".join(logs or []))[:20000]

        resumir_hallazgos_run(run)

        run.estado = "finalizado"
        run.progress_pct = 100
        run.current_stage = "Escaneo Kali finalizado"
        run.current_tool = None
        run.active_pid = None
        run.active_command = None
        run.fecha_fin = datetime.utcnow()
        db.session.commit()

        scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        try:
            pdf_path = build_vulnerability_scan_pdf(run.id)
            run.archivo_reporte_pdf = pdf_path
            db.session.commit()
        except Exception:
            pass

        return {
            "ok": True,
            "findings": run.total_hallazgos or 0,
            "vulns": run.created_vulns or 0,
            "planes": run.created_plans or 0
        }

    except Exception as e:
        tb = traceback.format_exc()

        run = VulnerabilityScanRun.query.get(run_id)
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

        scorecard_proponentes_set_progress(
            scorecard_run_id,
            pct=100,
            stage="Error ejecutando Kali",
            tool=None,
            estado="error",
            error=tb
        )

        return {"ok": False, "error": str(e)}

def ejecutar_scorecard_proponentes_kali_independiente(run_id, dominio):
    scorecard_proponentes_set_progress(
        run_id,
        pct=45,
        stage="Inicializando escaneo Kali con herramientas seleccionadas",
        tool="Inicializando",
        estado="ejecutando"
    )

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM scorecard_proponentes_runs
        WHERE id = ?
    """, (run_id,))

    scorecard_run = cur.fetchone()
    conn.close()

    if not scorecard_run:
        raise RuntimeError("Scorecard de Proponentes no encontrado.")

    herramientas_kali = []

    try:
        if "herramientas_kali" in scorecard_run.keys() and scorecard_run["herramientas_kali"]:
            herramientas_kali = json.loads(scorecard_run["herramientas_kali"] or "[]")
    except Exception:
        herramientas_kali = []

    if not herramientas_kali:
        try:
            resumen_tmp = json.loads(scorecard_run["resumen_json"] or "{}")
            herramientas_kali = resumen_tmp.get("herramientas_kali") or []
        except Exception:
            herramientas_kali = []

    herramientas_kali = scorecard_proponentes_normalizar_herramientas_kali(herramientas_kali)

    target = target_url_scorecard(dominio)
    target_type = detectar_tipo_objetivo(target)
    cfg = _scan_cfg()

    vuln_run = VulnerabilityScanRun(
        target=normalizar_target_para_scan(target) if target_type == "url" else target,
        target_type=target_type,
        scan_mode="scorecard_proponentes",
        scanner_mode=cfg.modo,
        estado="ejecutando",
        fecha_inicio=datetime.utcnow(),
        fecha_fin=None,
        ejecutado_por=scorecard_run["usuario"] or "Sistema",
        responsable_asignado=scorecard_run["usuario"] or "Sistema",
        progress_pct=1,
        current_stage="Encolando escaneo Scorecard de Terceros",
        current_tool="Inicializando",
        cancel_requested=False,
        stopped_by_user=False,
        findings_streamed=0,
        created_vulns=0,
        created_plans=0,
        herramientas=json.dumps(herramientas_kali, ensure_ascii=False)
    )

    db.session.add(vuln_run)
    db.session.commit()

    scorecard_proponentes_set_progress(
        run_id,
        pct=50,
        stage="Escaneo Kali iniciado con: " + scorecard_proponentes_label_herramientas_kali(herramientas_kali),
        tool="Kali Linux"
    )

    try:
        ejecutar_full_scan_scorecard_proponentes_sin_whatweb(
            vuln_run.id,
            run_id,
            crear_vulns=False,
            crear_planes=False
        )

        vuln_run = VulnerabilityScanRun.query.get(vuln_run.id)

        findings = scorecard_proponentes_copiar_findings_vuln(
            run_id,
            vuln_run.id
        )

        score_kali, resumen_kali = scorecard_proponentes_score_kali_desde_findings(findings)

        conn = get_scorecard_proponentes_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT score_dns, score_ip, score_incidentes, score_darkweb, resumen_json
            FROM scorecard_proponentes_runs
            WHERE id = ?
        """, (run_id,))

        row = cur.fetchone()

        score_dns = float(row["score_dns"] or 0) if row else 0
        score_ip = float(row["score_ip"] or 0) if row else 0
        score_incidentes = float(row["score_incidentes"] or 100) if row else 100
        score_darkweb = float(row["score_darkweb"] or 100) if row else 100

        score_total = scorecard_proponentes_calcular_total(
            score_dns,
            score_ip,
            score_kali,
            score_incidentes,
            score_darkweb,
            incluir_kali=True
        )

        nivel = nivel_riesgo_scorecard_proponentes(score_total)

        try:
            resumen_base = json.loads(row["resumen_json"] or "{}") if row else {}
        except Exception:
            resumen_base = {}

        resumen_final = {
            **resumen_base,
            "dns_score": score_dns,
            "ip_score": score_ip,
            "kali_score": score_kali,
            "kali_ejecutado": True,
            "kali_motor": "Registro de Vulnerabilidades",
            "herramientas_kali": herramientas_kali,
            "herramientas_kali_label": scorecard_proponentes_label_herramientas_kali(herramientas_kali),
            "vulnerability_scan_run_id": vuln_run.id,
            "incident_score": score_incidentes,
            "darkweb_score": score_darkweb,
            "score_total": score_total,
            "nivel_riesgo": nivel,
            "kali": resumen_kali
        }

        salida = vuln_run.salida_consola or ""

        cur.execute("""
            UPDATE scorecard_proponentes_runs
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
            "Escaneo Kali finalizado con herramientas: " + scorecard_proponentes_label_herramientas_kali(herramientas_kali),
            None,
            json.dumps(resumen_final, ensure_ascii=False),
            salida[:25000],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            run_id
        ))

        conn.commit()
        conn.close()

        guardar_scorecard_proponentes_output(
            run_id,
            "Registro de Vulnerabilidades",
            f"VulnerabilityScanRun #{vuln_run.id} | Herramientas: {scorecard_proponentes_label_herramientas_kali(herramientas_kali)}",
            vuln_run.archivo_log or "",
            0,
            0
        )

    except Exception as e:
        tb = traceback.format_exc()

        scorecard_proponentes_set_progress(
            run_id,
            pct=100,
            stage="Error ejecutando Kali con herramientas seleccionadas",
            tool=None,
            estado="error",
            error=tb
        )

        raise e


def scorecard_proponentes_kali_worker(run_id, dominio):
    with app.app_context():
        try:
            ejecutar_scorecard_proponentes_kali_independiente(run_id, dominio)
        except Exception:
            tb = traceback.format_exc()
            scorecard_proponentes_set_progress(
                run_id,
                pct=100,
                stage="Error en escaneo Kali de Proponentes usando Registro de Vulnerabilidades",
                tool=None,
                estado="error",
                error=tb
            )


# ============================================================
# APIs INDEPENDIENTES SCORECARD PROPONENTES
# ============================================================

def init_scorecard_proponentes_api_db():
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_proponentes_api_keys (
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
        ("leakcheck", "LeakCheck API para Proponentes"),
        ("hibp", "Have I Been Pwned API para Proponentes"),
        ("shodan", "Shodan API para Proponentes"),
    ]

    for proveedor, notas in proveedores_default:
        cur.execute("""
            INSERT OR IGNORE INTO scorecard_proponentes_api_keys
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


init_scorecard_proponentes_api_db()


def scorecard_proponentes_get_api_key(proveedor):
    proveedor = (proveedor or "").strip().lower()

    try:
        conn = get_scorecard_proponentes_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT api_key_encrypted, activo
            FROM scorecard_proponentes_api_keys
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


def scorecard_proponentes_api_status():
    proveedores = ["leakcheck", "hibp", "shodan"]
    estado = {}

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    for proveedor in proveedores:
        cur.execute("""
            SELECT *
            FROM scorecard_proponentes_api_keys
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


def scorecard_proponentes_guardar_api_key(proveedor, api_key, activo, usuario):
    proveedor = (proveedor or "").strip().lower()
    api_key = (api_key or "").strip()

    encrypted = scorecard_encrypt_api_key(api_key) if api_key else ""

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_proponentes_api_keys
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


# ============================================================
# DASHBOARD PROPONENTES / TERCEROS
# ============================================================

@app.route("/proponentes/scorecard")
@login_required
def proponentes_scorecard_dashboard():
    user, allowed, read_only = scorecard_proponentes_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al Security Scorecard de Terceros.", "danger")
        return redirect(url_for("menu"))

    puede_configurar = (
        user.role == "admin"
        or (
            user.role != "auditor"
            and verificar_permiso(user, SCORECARD_PROPONENTES_PERMISO)
        )
    )

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM scorecard_proponentes_runs
        ORDER BY id DESC
        LIMIT 100
    """)
    runs = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS total FROM scorecard_proponentes_runs")
    total_runs = cur.fetchone()["total"] or 0

    cur.execute("""
        SELECT AVG(score_total) AS promedio
        FROM scorecard_proponentes_runs
        WHERE estado = 'finalizado'
    """)
    promedio = cur.fetchone()["promedio"] or 0

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_proponentes_runs
        WHERE nivel_riesgo IN ('Alto', 'Crítico', 'Critico')
    """)
    alto_critico = cur.fetchone()["total"] or 0

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_proponentes_runs
        WHERE estado IN ('pendiente', 'ejecutando')
    """)
    en_ejecucion = cur.fetchone()["total"] or 0

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

      .prop-score-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }

      .prop-score-header-card{
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

      .prop-score-header-card::before{
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

      .prop-score-title{
        display:flex;
        align-items:center;
        justify-content:flex-start;
        gap:14px;
        color:#ffffff;
        position:relative;
        z-index:1;
        width:100%;
      }

      .prop-score-icon{
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
      }

      .prop-score-pill{
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .prop-score-title h2{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .score-action-row{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .score-action-row .btn,
      .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 18px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      /* =========================================================
         BOTON CONFIGURAR API AZUL
      ========================================================= */

      .btn-api-blue{
        background:linear-gradient(135deg,#0b4a8f,#2f7fd1) !important;
        border:none !important;
        color:#ffffff !important;
        border-radius:12px !important;
        min-height:36px !important;
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

      .soft-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .metric-card{
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        box-shadow:0 8px 18px rgba(15,23,42,.10);
        padding:18px;
        height:100%;
      }

      .metric-label{
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
        margin-bottom:8px;
      }

      .metric-value{
        color:#0b4a8f;
        font-size:1.8rem;
        font-weight:950;
        line-height:1;
      }

      .table-wrap{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        background:#ffffff;
        border-radius:14px;
        border:1px solid #dbe6f4;
        box-shadow:0 12px 24px rgba(15,23,42,.10);
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

      .table tbody td{
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

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .acciones-score{
        display:flex;
        justify-content:center;
        gap:6px;
        flex-wrap:wrap;
        min-width:260px;
      }

      .acciones-score .btn{
        padding:6px 10px !important;
        min-height:32px;
        font-size:.74rem;
      }
    </style>

    <div class="prop-score-shell">

      <div class="prop-score-header-card">
        <div class="prop-score-title">
          <div class="prop-score-icon">⚡</div>
          <div>
            <div class="prop-score-pill">SGSI · Scorecard</div>
            <h2>Security Scorecard de Terceros</h2>
          </div>
        </div>
      </div>

      <div class="score-action-row">
        {% if puede_configurar %}
          <a href="{{ url_for('admin_scorecard_proponentes_apis') }}" class="btn btn-api-blue">
              🔐 Configurar APIs
          </a>

          <a href="{{ url_for('proponentes_scorecard_parametros') }}" class="btn btn-secondary">
            ⚙️ Parámetros Scorecard
          </a>
        {% endif %}

        {% if not read_only %}
          <a href="{{ url_for('proponentes_scorecard_scan_nuevo') }}" class="btn btn-primary">
            🚀 Ejecutar Escaneo Scorecard
          </a>
        {% endif %}
      </div>

      <div class="soft-card p-3 mb-4">
        <h6 class="fw-bold text-primary mb-2">FUENTES ENTERPRISE CONFIGURADAS</h6>
        <span class="badge bg-secondary me-1">LeakCheck</span>
        <span class="badge bg-secondary me-1">HIBP</span>
        <span class="badge bg-secondary me-1">Shodan</span>
        <span class="badge bg-info text-dark me-1">OSINT público activo</span>
      </div>

      <div class="row g-3 mb-4">
        <div class="col-md-3">
          <div class="metric-card">
            <div class="metric-label">Evaluaciones Ejecutadas</div>
            <div class="metric-value">{{ total_runs }}</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="metric-card">
            <div class="metric-label">Score Promedio</div>
            <div class="metric-value">{{ "%.1f"|format(promedio) }}%</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="metric-card">
            <div class="metric-label">Riesgos Críticos / No Aceptables</div>
            <div class="metric-value text-danger">{{ alto_critico }}</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="metric-card">
            <div class="metric-label">En Ejecución</div>
            <div class="metric-value text-primary">{{ en_ejecucion }}</div>
          </div>
        </div>
      </div>

      <div class="soft-card p-3">
        <h5 class="fw-bold mb-3">📋 Historial de Scorecard de Terceros</h5>

        <div class="table-wrap">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>ID</th>
                <th>Tercero</th>
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
                <th class="text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {% for r in runs %}
              <tr>
                <td class="fw-bold">#{{ r.id }}</td>
                <td>{{ r.proponente_nombre }}</td>
                <td>{{ r.dominio }}</td>
                <td>{{ r.ip_resuelta or "—" }}</td>
                <td>{{ "%.1f"|format(r.score_dns or 0) }}</td>
                <td>{{ "%.1f"|format(r.score_ip or 0) }}</td>
                <td>{{ "%.1f"|format(r.score_kali or 0) }}</td>
                <td>{{ "%.1f"|format(r.score_darkweb or 100) }}</td>
                <td class="fw-bold">{{ "%.1f"|format(r.score_total or 0) }}</td>
                <td>
                  <span class="badge bg-{{ scorecard_proponentes_badge_color(r.nivel_riesgo or 'Pendiente') }}">
                    {{ r.nivel_riesgo or "Pendiente" }}
                  </span>
                </td>
                <td>
                  {% if r.estado == 'finalizado' %}
                    <span class="badge bg-success">Finalizado</span>
                  {% elif r.estado == 'error' %}
                    <span class="badge bg-danger">Error</span>
                  {% elif r.estado == 'ejecutando' %}
                    <span class="badge bg-primary">Ejecutando</span>
                  {% else %}
                    <span class="badge bg-secondary">{{ r.estado or "Pendiente" }}</span>
                  {% endif %}
                </td>
                <td style="min-width:130px;">
                  <div class="progress" style="height:18px;border-radius:20px;">
                    <div class="progress-bar" style="width:{{ r.progress_pct or 0 }}%;">
                      {{ r.progress_pct or 0 }}%
                    </div>
                  </div>
                </td>
                <td class="text-center">
                  <div class="acciones-score">
                    <a href="{{ url_for('proponentes_scorecard_detalle', scorecard_id=r.id) }}" class="btn btn-sm btn-outline-primary">
                      Ver detalle
                    </a>

                    <a href="{{ url_for('proponentes_scorecard_rating', scorecard_id=r.id) }}" class="btn btn-sm btn-outline-success">
                      📊 Gráfica
                    </a>

                    {% if not read_only %}
                      <form method="POST"
                            action="{{ url_for('proponentes_scorecard_eliminar', scorecard_id=r.id) }}"
                            style="display:inline;"
                            onsubmit="return confirm('¿Seguro que desea eliminar este Security Scorecard de Terceros? Esta acción no se puede deshacer.');">
                        <button type="submit" class="btn btn-sm btn-outline-danger">
                          🗑️ Eliminar
                        </button>
                      </form>
                    {% endif %}
                  </div>
                </td>
              </tr>
              {% else %}
              <tr>
                <td colspan="13" class="text-center text-muted py-4">
                  No existen scorecards de terceros registrados.
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
            total_runs=total_runs,
            promedio=float(promedio or 0),
            alto_critico=alto_critico,
            en_ejecucion=en_ejecucion,
            read_only=read_only,
            user=user,
            puede_configurar=puede_configurar,
            scorecard_proponentes_badge_color=scorecard_proponentes_badge_color
        ))
    )

# ============================================================
# SECURITYSCORECARD GRAC - PROPONENTES
# MISMO DISEÑO QUE PROVEEDORES
# ============================================================

def scorecard_proponentes_rating_letra(score):
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


def scorecard_proponentes_rating_color(score):
    score = float(score or 0)

    if score >= 90:
        return "#087c3d"
    if score >= 80:
        return "#15803d"
    if score >= 70:
        return "#d97706"
    if score >= 60:
        return "#c2410c"
    return "#991b1b"


def scorecard_proponentes_get_trend_data(run):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT fecha_ejecucion, score_total
        FROM scorecard_proponentes_runs
        WHERE LOWER(TRIM(proponente_nombre)) = LOWER(TRIM(?))
          AND estado = 'finalizado'
          AND fecha_ejecucion >= datetime('now', '-30 days')
        ORDER BY fecha_ejecucion ASC
    """, (run["proponente_nombre"],))

    rows = cur.fetchall()
    conn.close()

    data = []
    for r in rows:
        fecha = str(r["fecha_ejecucion"] or "")[:10]
        data.append({
            "fecha": fecha,
            "score_total": round(float(r["score_total"] or 0), 1)
        })

    if not data:
        data.append({
            "fecha": str(run["fecha_ejecucion"] or "")[:10],
            "score_total": round(float(run["score_total"] or 0), 1)
        })

    return data


def scorecard_proponentes_get_monthly_comparison(run):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT substr(fecha_ejecucion, 1, 7) AS mes,
               AVG(score_total) AS score
        FROM scorecard_proponentes_runs
        WHERE LOWER(TRIM(proponente_nombre)) = LOWER(TRIM(?))
          AND estado = 'finalizado'
        GROUP BY substr(fecha_ejecucion, 1, 7)
        ORDER BY mes ASC
        LIMIT 12
    """, (run["proponente_nombre"],))

    rows = cur.fetchall()
    conn.close()

    data = []
    for r in rows:
        data.append({
            "label": r["mes"] or "N/A",
            "score": round(float(r["score"] or 0), 1)
        })

    if not data:
        data.append({
            "label": str(run["fecha_ejecucion"] or "")[:7],
            "score": round(float(run["score_total"] or 0), 1)
        })

    return data


def scorecard_proponentes_get_risk_counts(scorecard_id):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(severidad, riesgo, 'Bajo') AS sev,
               COUNT(*) AS total
        FROM scorecard_proponentes_findings
        WHERE run_id = ?
        GROUP BY COALESCE(severidad, riesgo, 'Bajo')
    """, (scorecard_id,))

    rows = cur.fetchall()
    conn.close()

    counts = {
        "Crítico": 0,
        "Alto": 0,
        "Medio": 0,
        "Bajo": 0
    }

    for r in rows:
        sev = r["sev"] or "Bajo"

        if sev == "Critico":
            sev = "Crítico"

        if sev not in counts:
            sev = "Bajo"

        counts[sev] += int(r["total"] or 0)

    total = sum(counts.values())
    return counts, total


def scorecard_proponentes_issue_summary(scorecard_id):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_proponentes_findings
        WHERE run_id = ?
          AND COALESCE(severidad, riesgo, '') IN ('Crítico', 'Critico')
    """, (scorecard_id,))
    criticos = cur.fetchone()["total"] or 0

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_proponentes_findings
        WHERE run_id = ?
          AND COALESCE(severidad, riesgo, '') = 'Alto'
    """, (scorecard_id,))
    altos = cur.fetchone()["total"] or 0

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_proponentes_findings
        WHERE run_id = ?
          AND categoria = 'Kali Linux Scan'
          AND COALESCE(severidad, riesgo, '') IN ('Crítico', 'Critico', 'Alto', 'Medio')
    """, (scorecard_id,))
    vulnerabilidades = cur.fetchone()["total"] or 0

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_proponentes_darkweb_exposures
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


def scorecard_proponentes_get_recent_findings(scorecard_id, limit=4):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM scorecard_proponentes_findings
        WHERE run_id = ?
        ORDER BY
          CASE COALESCE(severidad, riesgo, '')
            WHEN 'Crítico' THEN 1
            WHEN 'Critico' THEN 1
            WHEN 'Alto' THEN 2
            WHEN 'Medio' THEN 3
            WHEN 'Bajo' THEN 4
            ELSE 5
          END,
          id DESC
        LIMIT ?
    """, (scorecard_id, limit))

    rows = cur.fetchall()
    conn.close()
    return rows


def scorecard_proponentes_get_peer_comparison(run):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT AVG(score_total) AS promedio,
               MAX(score_total) AS mejor
        FROM scorecard_proponentes_runs
        WHERE estado = 'finalizado'
    """)
    row = cur.fetchone()
    conn.close()

    actual = round(float(run["score_total"] or 0), 1)
    promedio = round(float(row["promedio"] or actual), 1) if row else actual
    mejor = round(float(row["mejor"] or actual), 1) if row else actual

    return {
        "actual": actual,
        "promedio": promedio,
        "mejor": mejor
    }

def scorecard_proponentes_build_contexto_informe_ai(scorecard_id):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM scorecard_proponentes_runs WHERE id = ?", (scorecard_id,))
    run = cur.fetchone()

    cur.execute("""
        SELECT categoria, herramienta, control, estado, riesgo, severidad, score, evidencia, recomendacion
        FROM scorecard_proponentes_findings
        WHERE run_id = ?
        ORDER BY
          CASE COALESCE(severidad, riesgo, '')
            WHEN 'Crítico' THEN 1
            WHEN 'Critico' THEN 1
            WHEN 'Alto' THEN 2
            WHEN 'Medio' THEN 3
            WHEN 'Bajo' THEN 4
            ELSE 5
          END,
          id ASC
        LIMIT 25
    """, (scorecard_id,))
    findings = cur.fetchall()

    conn.close()

    if not run:
        return ""

    hallazgos_txt = []
    for f in findings:
        hallazgos_txt.append(
            f"- Categoría: {f['categoria']} | Control: {f['control']} | "
            f"Riesgo: {f['riesgo'] or f['severidad']} | Score: {f['score']} | "
            f"Evidencia: {f['evidencia']} | Recomendación: {f['recomendacion']}"
        )

    return f"""
Genera un informe ejecutivo profesional para una evaluación SecurityScorecard GRAC de un tercero/proponente.

Datos del tercero:
- Nombre: {run['proponente_nombre']}
- Dominio: {run['dominio']}
- IP: {run['ip_resuelta'] or 'No resuelta'}
- Score DNS: {run['score_dns']}
- Score IP Reputation: {run['score_ip']}
- Score Kali: {run['score_kali']}
- Score Incidentes: {run['score_incidentes']}
- Score Dark Web / Exposure Intelligence: {run['score_darkweb']}
- Score Total: {run['score_total']}
- Nivel de Riesgo: {run['nivel_riesgo']}
- Estado: {run['estado']}
- Fecha evaluación: {run['fecha_ejecucion']}

Hallazgos relevantes:
{chr(10).join(hallazgos_txt) if hallazgos_txt else 'No hay hallazgos relevantes registrados.'}

Estructura obligatoria:
1. Resumen ejecutivo
2. Nivel de riesgo y lectura gerencial
3. Principales hallazgos
4. Impacto potencial para la organización
5. Recomendaciones priorizadas
6. Conclusión ejecutiva

Redacta en español, tono formal, claro y orientado a auditoría, SGSI, riesgo de terceros y toma de decisiones.
No uses markdown técnico excesivo ni JSON.
"""


def scorecard_proponentes_generar_informe_ai(scorecard_id):
    prompt = scorecard_proponentes_build_contexto_informe_ai(scorecard_id)

    system_prompt = """
Eres un consultor senior de ciberseguridad, SGSI, gestión de riesgos de terceros y auditoría.
Genera un informe ejecutivo profesional, claro y útil para la alta dirección.
No uses JSON.
No uses markdown excesivo.
No inventes hallazgos.
Usa solo la información suministrada.
""".strip()

    return ai_text_general(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=900
    )

@app.route("/proponentes/scorecard/<int:scorecard_id>/rating")
@login_required
def proponentes_scorecard_rating(scorecard_id):
    user, allowed, read_only = scorecard_proponentes_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al Scorecard de Proponentes.", "danger")
        return redirect(url_for("menu"))

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM scorecard_proponentes_runs WHERE id = ?", (scorecard_id,))
    run = cur.fetchone()
    conn.close()

    if not run:
        abort(404)

    score_total = round(float(run["score_total"] or 0), 1)
    letra, texto_rating = scorecard_proponentes_rating_letra(score_total)
    color_rating = scorecard_proponentes_rating_color(score_total)

    trend = scorecard_proponentes_get_trend_data(run)
    monthly = scorecard_proponentes_get_monthly_comparison(run)

    counts, total_riesgos = scorecard_proponentes_get_risk_counts(scorecard_id)
    summary = scorecard_proponentes_issue_summary(scorecard_id)

    recent_findings = scorecard_proponentes_get_recent_findings(scorecard_id, limit=4)
    peer = scorecard_proponentes_get_peer_comparison(run)

    informe_ejecutivo = (
        run["informe_ejecutivo_editado"]
        or run["informe_ejecutivo_ai"]
        or ""
    )

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

    peer_labels = ["Proponente", "Promedio", "Mejor"]
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

      .ssc-card.full{
        grid-column:1 / -1;
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

      .ai-report-card{
        margin-top:9px;
      }

      .ai-report-actions{
        display:flex;
        justify-content:flex-end;
        align-items:center;
        gap:6px;
        flex-wrap:wrap;
      }

      .ai-report-textarea{
        border-radius:14px !important;
        font-size:.86rem;
        font-weight:700;
        line-height:1.45;
        min-height:235px;
        background:#f8fafc;
        color:#334155;
        resize:vertical;
      }

      .ai-report-textarea.ai-editable{
        background:#ffffff;
        border:2px solid #c76b00;
        box-shadow:0 0 0 .15rem rgba(245,158,11,.18);
      }

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
          <a href="{{ url_for('proponentes_scorecard_detalle', scorecard_id=run.id) }}" class="btn btn-outline-secondary px-4">
            Volver al detalle
          </a>

          <div class="d-flex gap-2 flex-wrap">
            <a href="{{ url_for('proponentes_scorecard_rating_pdf', scorecard_id=run.id) }}"
               class="btn btn-danger px-4"
               target="_blank"
               data-no-progress="true">
              📄 PDF
            </a>

            <a href="{{ url_for('proponentes_scorecard_dashboard') }}" class="btn btn-primary px-4">
              Dashboard Scorecard
            </a>
          </div>
      </div>

      <div class="ssc-frame">
        <div class="ssc-top">
          <div class="ssc-card">
            <div class="company-title">{{ run.proponente_nombre or 'Proponente no asociado' }}</div>
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
                Ejecuta varios Scorecards del mismo proponente para ver tendencia real.
              </div>
            {% endif %}
          </div>
        </div>

        <div class="ssc-card ai-report-card full">
          <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
            <div>
              <h5 class="mb-1 fw-bold text-primary">🤖 Informe Ejecutivo AI</h5>
              <div class="small text-muted">
                Generado con el proveedor activo en Administración AI: OpenRouter u Ollama.
              </div>
            </div>

            {% if not read_only %}
              <div class="ai-report-actions">
                <form method="POST"
                      action="{{ url_for('proponentes_scorecard_rating_generar_informe_ai', scorecard_id=run.id) }}"
                      data-progress-text="Generando informe ejecutivo con IA...">
                  <button type="submit" class="btn btn-primary btn-sm">
                    ✨ Generar AI
                  </button>
                </form>

                <button type="button"
                        class="btn btn-warning btn-sm text-dark"
                        onclick="habilitarEdicionInformeAI()">
                  ✏️ Editar Informe
                </button>
              </div>
            {% endif %}
          </div>

          <form method="POST"
                action="{{ url_for('proponentes_scorecard_rating_guardar_informe_ai', scorecard_id=run.id) }}"
                data-progress-text="Guardando informe ejecutivo...">

            <textarea id="informeEjecutivoAI"
                      name="informe_ejecutivo_editado"
                      class="form-control ai-report-textarea"
                      rows="10"
                      readonly>{{ informe_ejecutivo }}</textarea>

            {% if read_only %}
              <div class="alert alert-warning mt-3 mb-0">
                Rol Auditor: puede consultar el informe, pero no puede editarlo.
              </div>
            {% else %}
              <div class="text-end mt-3">
                <button id="btnGuardarInformeAI"
                        class="btn btn-success px-4"
                        style="display:none;">
                  💾 Guardar Informe
                </button>
              </div>
            {% endif %}
          </form>
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
              <div class="section-title">Comparación mensual del proponente</div>
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

      function habilitarEdicionInformeAI(){
        const txt = document.getElementById("informeEjecutivoAI");
        const btn = document.getElementById("btnGuardarInformeAI");

        if(txt){
          txt.removeAttribute("readonly");
          txt.classList.add("ai-editable");
          txt.focus();
        }

        if(btn){
          btn.style.display = "inline-block";
        }
      }

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
          const needleLength = outerRadius - 9;

          const angle = Math.PI + (Math.PI * Math.max(0, Math.min(100, score)) / 100);

          ctx.save();
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

        if(!ctx){
          return;
        }

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
            gauge_canvas_ids=gauge_canvas_ids,
            informe_ejecutivo=informe_ejecutivo,
            read_only=read_only
        ))
    )

@app.route("/proponentes/scorecard/<int:scorecard_id>/rating/pdf")
@login_required
def proponentes_scorecard_rating_pdf(scorecard_id):
    user, allowed, read_only = scorecard_proponentes_user_permiso()

    if not allowed:
        flash("No tiene permiso para generar el PDF del Scorecard.", "danger")
        return redirect(url_for("menu"))

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM scorecard_proponentes_runs WHERE id = ?", (scorecard_id,))
    run = cur.fetchone()

    if not run:
        conn.close()
        abort(404)

    cur.execute("""
        SELECT categoria, herramienta, control, estado, riesgo, severidad, score, evidencia, recomendacion
        FROM scorecard_proponentes_findings
        WHERE run_id = ?
        ORDER BY
          CASE COALESCE(severidad, riesgo, '')
            WHEN 'Crítico' THEN 1
            WHEN 'Critico' THEN 1
            WHEN 'Alto' THEN 2
            WHEN 'Medio' THEN 3
            WHEN 'Bajo' THEN 4
            ELSE 5
          END,
          score ASC,
          id ASC
    """, (scorecard_id,))
    all_findings = cur.fetchall()
    conn.close()

    informe_ejecutivo = (
        run["informe_ejecutivo_editado"]
        or run["informe_ejecutivo_ai"]
        or "No se ha generado informe ejecutivo AI."
    )

    score_total = round(float(run["score_total"] or 0), 1)
    letra, texto_rating = scorecard_proponentes_rating_letra(score_total)

    factores = [
        ("DNS", float(run["score_dns"] or 0)),
        ("IP Rep.", float(run["score_ip"] or 0)),
        ("Kali", float(run["score_kali"] or 0)),
        ("Incidentes", float(run["score_incidentes"] or 100)),
        ("Exposure", float(run["score_darkweb"] or 100)),
    ]

    riesgos_count = {"Crítico": 0, "Alto": 0, "Medio": 0, "Bajo": 0}
    categorias_count = {}

    for f in all_findings:
        sev = f["severidad"] or f["riesgo"] or "Bajo"
        if sev == "Critico":
            sev = "Crítico"
        if sev not in riesgos_count:
            sev = "Bajo"

        riesgos_count[sev] += 1

        cat = f["categoria"] or "Otros"
        categorias_count[cat] = categorias_count.get(cat, 0) + 1

    def clean_txt(txt, max_len=None):
        txt = str(txt or "—")
        txt = txt.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
        txt = re.sub(r"<[^>]+>", " ", txt)
        txt = txt.replace("**", "")
        txt = txt.replace("Conclusión. Ejecutiva", "Conclusión Ejecutiva")
        txt = re.sub(r"\n{3,}", "\n\n", txt)
        txt = re.sub(r"[ \t]+", " ", txt)
        txt = txt.strip()

        if max_len and len(txt) > max_len:
            return txt[:max_len] + "..."
        return txt

    def clean_ai_text(txt):
        txt = clean_txt(txt, None)

        # Elimina encabezados generados por la IA:
        # "Informe Ejecutivo: Evaluación SecurityScorecard GRAC del Tercero/Proponente Yahoo"
        txt = re.sub(
            r"^\s*Informe\s+Ejecutivo\s*:\s*Evaluación\s+SecurityScorecard\s+GRAC\s*(del\s+Tercero\/Proponente\s+[^\n\.]*)?\.?\s*",
            "",
            txt,
            flags=re.IGNORECASE
        )

        # Elimina cualquier línea suelta tipo "del Tercero/Proponente Yahoo"
        txt = re.sub(
            r"^\s*del\s+Tercero\/Proponente\s+[^\n\.]*\.?\s*",
            "",
            txt,
            flags=re.IGNORECASE
        )

        # Elimina "Resumen Ejecutivo" inicial porque el PDF ya lo pone como título
        txt = re.sub(
            r"^\s*Resumen\s+Ejecutivo\s*[:\-]?\s*",
            "",
            txt,
            flags=re.IGNORECASE
        )

        # Normaliza errores de IA
        txt = txt.replace("Conclusión. Ejecutiva", "Conclusión Ejecutiva")

        secciones = [
            "Nivel de Riesgo y Lectura Gerencial",
            "Principales Hallazgos",
            "Impacto Potencial para la Organización",
            "Recomendaciones Priorizadas",
            "Conclusión Ejecutiva",
            "Conclusión"
        ]

        # Fuerza saltos antes/después de títulos
        for titulo in secciones:
            txt = re.sub(
                rf"\s*({re.escape(titulo)})\s*",
                rf"\n\n\1\n",
                txt,
                flags=re.IGNORECASE
            )

        # Quita frases repetidas bajo la sección Principales Hallazgos
        txt = re.sub(
            r"(?i)(\n\s*Principales\s+Hallazgos\s*\n)\s*Los\s+principales\s+hallazgos\s*(de\s+la\s+evaluación\s+son\s*:?)?",
            r"\1",
            txt
        )

        txt = re.sub(
            r"(?i)\bLos\s+principales\s+hallazgos\s*(de\s+la\s+evaluación\s+son\s*:?)?\s*",
            "",
            txt
        )

        # Quita títulos duplicados consecutivos
        for titulo in secciones:
            txt = re.sub(
                rf"(?i)(\n\s*{re.escape(titulo)}\s*\n)(\s*{re.escape(titulo)}\s*\n)+",
                rf"\1",
                txt
            )

        txt = re.sub(r"\n{3,}", "\n\n", txt)
        txt = re.sub(r"[ ]{2,}", " ", txt)

        return txt.strip()

    def p(txt, style, max_len=None):
        return Paragraph(escape(clean_txt(txt, max_len)), style)

    def score_color(v):
        if v >= 85:
            return "#087c3d"
        if v >= 70:
            return "#c76b00"
        if v >= 50:
            return "#c95508"
        return "#b91c1c"

    def fig_to_image(fig, width, height):
        img = BytesIO()
        fig.savefig(
            img,
            format="png",
            dpi=180,
            bbox_inches="tight",
            pad_inches=0.25,
            facecolor="white"
        )
        plt.close(fig)
        img.seek(0)
        return RLImage(img, width=width, height=height)

    # ============================================================
    # GRÁFICAS
    # ============================================================

    fig0, ax0 = plt.subplots(figsize=(3.0, 2.2))
    fig0.patch.set_facecolor("white")
    ax0.pie(
        [score_total, max(0, 100 - score_total)],
        startangle=90,
        counterclock=False,
        colors=[score_color(score_total), "#e5e7eb"],
        wedgeprops={"width": 0.30, "edgecolor": "white"}
    )
    ax0.text(0, 0.12, f"{score_total:.1f}%", ha="center", va="center",
             fontsize=20, fontweight="bold", color="#0f172a")
    ax0.text(0, -0.18, f"Rating {letra}", ha="center", va="center",
             fontsize=10, fontweight="bold", color="#334155")
    ax0.set_title("Score General", fontsize=11, fontweight="bold", color="#062b55", pad=18)
    ax0.axis("equal")
    fig0.subplots_adjust(left=0.06, right=0.94, top=0.76, bottom=0.04)
    chart_score = fig_to_image(fig0, 190, 142)

    fig1, ax1 = plt.subplots(figsize=(6.2, 2.75))
    fig1.patch.set_facecolor("white")

    labels = [x[0] for x in factores]
    values = [x[1] for x in factores]
    bar_colors = [score_color(v) for v in values]

    bars = ax1.barh(labels, values, color=bar_colors, height=0.45)
    ax1.set_xlim(0, 112)
    ax1.set_title("Componentes Evaluados", fontsize=11, fontweight="bold", color="#062b55", pad=18)
    ax1.grid(axis="x", alpha=.16)
    ax1.invert_yaxis()
    ax1.tick_params(axis="both", labelsize=8)

    for bar, v in zip(bars, values):
        ax1.text(
            min(v + 2.5, 104),
            bar.get_y() + bar.get_height() / 2,
            f"{v:.1f}%",
            va="center",
            fontsize=8,
            fontweight="bold",
            color="#0b1220"
        )

    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.spines["left"].set_visible(False)
    fig1.subplots_adjust(left=0.23, right=0.90, top=0.78, bottom=0.16)
    chart_factores = fig_to_image(fig1, 360, 155)

    risk_labs = ["Crítico", "Alto", "Medio", "Bajo"]
    risk_vals = [riesgos_count[x] for x in risk_labs]

    if sum(risk_vals) == 0:
        risk_labs = ["Sin hallazgos"]
        risk_vals = [1]
        risk_colors = ["#087c3d"]
    else:
        risk_colors = ["#7f1d1d", "#b91c1c", "#c76b00", "#087c3d"]

    fig2, ax2 = plt.subplots(figsize=(3.7, 2.85))
    fig2.patch.set_facecolor("white")
    ax2.pie(
        risk_vals,
        labels=None,
        autopct=lambda pct: f"{pct:.0f}%" if pct >= 5 else "",
        startangle=90,
        pctdistance=0.52,
        colors=risk_colors,
        wedgeprops={
            "width": 0.32,
            "edgecolor": "white",
            "linewidth": 1.2
        },
        textprops={
            "fontsize": 8,
            "fontweight": "bold",
            "color": "#0b1220"
        }
    )
    ax2.legend(
        risk_labs,
        loc="center left",
        bbox_to_anchor=(1.32, 0.5),
        fontsize=7,
        frameon=False,
        borderaxespad=0.0
    )
    ax2.set_title("Distribución de Riesgos", fontsize=11, fontweight="bold", color="#062b55", pad=28)
    ax2.axis("equal")
    fig2.subplots_adjust(left=0.02, right=0.60, top=0.74, bottom=0.04)
    chart_riesgos = fig_to_image(fig2, 240, 168)

    cat_items = sorted(categorias_count.items(), key=lambda x: x[1], reverse=True)[:5]

    if not cat_items:
        cat_items = [("Sin hallazgos", 1)]

    fig3, ax3 = plt.subplots(figsize=(5.8, 2.45))
    fig3.patch.set_facecolor("white")

    cat_labels = [x[0][:28] for x in cat_items]
    cat_values = [x[1] for x in cat_items]

    bars = ax3.barh(cat_labels, cat_values, color="#2563eb", height=0.48)
    ax3.set_title("Hallazgos por Categoría", fontsize=11, fontweight="bold", color="#062b55", pad=18)
    ax3.invert_yaxis()
    ax3.grid(axis="x", alpha=.16)
    ax3.tick_params(axis="both", labelsize=8)

    for bar, v in zip(bars, cat_values):
        ax3.text(
            v + 0.08,
            bar.get_y() + bar.get_height() / 2,
            str(v),
            va="center",
            fontsize=8,
            fontweight="bold"
        )

    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)
    ax3.spines["left"].set_visible(False)
    fig3.subplots_adjust(left=0.28, right=0.92, top=0.78, bottom=0.14)
    chart_categorias = fig_to_image(fig3, 350, 145)

    # ============================================================
    # PDF
    # ============================================================

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=18,
        bottomMargin=18
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleSGSI",
        parent=styles["Heading1"],
        fontSize=15,
        leading=17,
        textColor=colors.white,
        alignment=TA_LEFT,
        spaceAfter=0
    )

    subtitle_style = ParagraphStyle(
        "SubtitleSGSI",
        parent=styles["Normal"],
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#dbeafe"),
        alignment=TA_LEFT
    )

    h2_style = ParagraphStyle(
        "H2SGSI",
        parent=styles["Heading2"],
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#062b55"),
        spaceBefore=6,
        spaceAfter=6
    )

    normal_style = ParagraphStyle(
        "NormalSGSI",
        parent=styles["Normal"],
        fontSize=7.2,
        leading=9,
        textColor=colors.HexColor("#101827"),
        spaceAfter=4
    )

    small_style = ParagraphStyle(
        "SmallSGSI",
        parent=styles["Normal"],
        fontSize=6.3,
        leading=7.6,
        textColor=colors.HexColor("#334155")
    )

    label_style = ParagraphStyle(
        "LabelSGSI",
        parent=styles["Normal"],
        fontSize=6.2,
        leading=7.2,
        textColor=colors.HexColor("#0b4a8f"),
        fontName="Helvetica-Bold"
    )

    white_small = ParagraphStyle(
        "WhiteSmall",
        parent=styles["Normal"],
        fontSize=6.5,
        leading=7.5,
        textColor=colors.white
    )

    story = []

    header = Table([
        [
            Paragraph("<b>SecurityScorecard GRAC</b>", title_style),
            Paragraph(
                f"Score: {score_total:.1f}%    Rating: {escape(letra)} - {escape(texto_rating)}    Riesgo: {escape(run['nivel_riesgo'] or '—')}",
                white_small
            )
        ],
        [
            Paragraph("Reporte ejecutivo visual de riesgo de terceros", subtitle_style),
            Paragraph(f"Fecha evaluación: {escape(run['fecha_ejecucion'] or '—')}", white_small)
        ]
    ], colWidths=[470, 350])

    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#062b55")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#062b55")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))

    story.append(header)
    story.append(Spacer(1, 8))

    resumen_table = Table([
        [
            [Paragraph("Tercero", label_style), p(run["proponente_nombre"], small_style, 80)],
            [Paragraph("Dominio", label_style), p(run["dominio"], small_style, 80)],
            [Paragraph("IP", label_style), p(run["ip_resuelta"], small_style, 70)],
            [Paragraph("Estado", label_style), p(run["estado"], small_style, 60)],
        ]
    ], colWidths=[205, 205, 205, 205])

    resumen_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#dbe6f4")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dbe6f4")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    story.append(resumen_table)
    story.append(Spacer(1, 10))

    # ============================================================
    # RESUMEN EJECUTIVO LIMPIO
    # ============================================================

    story.append(Paragraph("Resumen Ejecutivo", h2_style))

    texto_ai_completo = clean_ai_text(informe_ejecutivo)

    secciones = [
        "Nivel de Riesgo y Lectura Gerencial",
        "Principales Hallazgos",
        "Impacto Potencial para la Organización",
        "Recomendaciones Priorizadas",
        "Conclusión Ejecutiva",
        "Conclusión"
    ]

    bloques = [b.strip() for b in texto_ai_completo.split("\n") if b.strip()]

    for bloque in bloques:
        limpio = bloque.strip()

        if limpio.lower() in [s.lower() for s in secciones]:
            story.append(Paragraph(escape(limpio), h2_style))
        else:
            story.append(Paragraph(escape(limpio), normal_style))

    story.append(Spacer(1, 10))

    # ============================================================
    # GRÁFICAS DESPUÉS DEL RESUMEN, SIN HOJA EXCLUSIVA
    # ============================================================

    charts_row_1 = Table(
        [[chart_score, chart_factores, chart_riesgos]],
        colWidths=[205, 390, 225],
        rowHeights=[178]
    )

    charts_row_1.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    story.append(charts_row_1)
    story.append(Spacer(1, 10))

    charts_row_2 = Table([[chart_categorias]], colWidths=[820])
    charts_row_2.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    story.append(charts_row_2)
    story.append(PageBreak())

    # ============================================================
    # HALLAZGOS Y MATRIZ
    # ============================================================

    story.append(header)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Top hallazgos priorizados", h2_style))

    top_findings = all_findings[:7]
    findings_data = [["Categoría", "Control", "Riesgo", "Score", "Recomendación ejecutiva"]]

    for f in top_findings:
        findings_data.append([
            p(f["categoria"], small_style, 45),
            p(f["control"], small_style, 60),
            p(f["riesgo"] or f["severidad"], small_style, 22),
            Paragraph(f"{float(f['score'] or 0):.1f}", small_style),
            p(f["recomendacion"] or f["evidencia"], small_style, 190),
        ])

    findings_table = Table(findings_data, colWidths=[125, 180, 65, 45, 385], repeatRows=1)

    findings_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b4a8f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dbe6f4")),
        ("FONTSIZE", (0, 0), (-1, -1), 6.3),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    story.append(findings_table)
    story.append(Spacer(1, 10))
    story.append(Paragraph("Matriz ejecutiva de componentes", h2_style))

    matriz = [["Componente", "Score", "Estado ejecutivo", "Acción sugerida"]]

    for label, value in factores:
        if value >= 85:
            estado = "Adecuado"
            accion = "Mantener monitoreo periódico."
        elif value >= 70:
            estado = "Monitorear"
            accion = "Validar desviaciones y documentar seguimiento."
        elif value >= 50:
            estado = "Plan de acción"
            accion = "Solicitar remediación y evidencia al tercero."
        else:
            estado = "No aceptable / crítico"
            accion = "Escalar decisión de riesgo y exigir corrección prioritaria."

        matriz.append([
            p(label, small_style, 40),
            Paragraph(f"{value:.1f}%", small_style),
            p(estado, small_style, 60),
            p(accion, small_style, 160),
        ])

    matriz_table = Table(matriz, colWidths=[160, 80, 180, 380])

    matriz_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b4a8f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dbe6f4")),
        ("FONTSIZE", (0, 0), (-1, -1), 6.8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.append(matriz_table)

    doc.build(story)

    buffer.seek(0)

    filename = f"SecurityScorecard_GRAC_ejecutivo_{scorecard_id}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )

@app.route("/proponentes/scorecard/<int:scorecard_id>/rating/informe-ai/generar", methods=["POST"])
@login_required
def proponentes_scorecard_rating_generar_informe_ai(scorecard_id):
    user, allowed, read_only = scorecard_proponentes_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al Scorecard de Proponentes.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no puede generar ni editar el informe ejecutivo AI.", "danger")
        return redirect(url_for("proponentes_scorecard_rating", scorecard_id=scorecard_id))

    informe_ai = scorecard_proponentes_generar_informe_ai(scorecard_id)

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE scorecard_proponentes_runs
        SET informe_ejecutivo_ai = ?,
            informe_ejecutivo_editado = ?,
            informe_ejecutivo_fecha = ?,
            informe_ejecutivo_usuario = ?
        WHERE id = ?
    """, (
        informe_ai,
        informe_ai,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        getattr(user, "username", "Sistema"),
        scorecard_id
    ))

    conn.commit()
    conn.close()

    flash("Informe ejecutivo AI generado correctamente.", "success")
    return redirect(url_for("proponentes_scorecard_rating", scorecard_id=scorecard_id))


@app.route("/proponentes/scorecard/<int:scorecard_id>/rating/informe-ai/guardar", methods=["POST"])
@login_required
def proponentes_scorecard_rating_guardar_informe_ai(scorecard_id):
    user, allowed, read_only = scorecard_proponentes_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al Scorecard de Proponentes.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no puede editar el informe ejecutivo AI.", "danger")
        return redirect(url_for("proponentes_scorecard_rating", scorecard_id=scorecard_id))

    informe = (request.form.get("informe_ejecutivo_editado") or "").strip()

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE scorecard_proponentes_runs
        SET informe_ejecutivo_editado = ?,
            informe_ejecutivo_fecha = ?,
            informe_ejecutivo_usuario = ?
        WHERE id = ?
    """, (
        informe,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        getattr(user, "username", "Sistema"),
        scorecard_id
    ))

    conn.commit()
    conn.close()

    flash("Informe ejecutivo actualizado correctamente.", "success")
    return redirect(url_for("proponentes_scorecard_rating", scorecard_id=scorecard_id))


# ============================================================
# ELIMINAR SCORECARD PROPONENTES
# ============================================================

@app.route("/proponentes/scorecard/<int:scorecard_id>/eliminar", methods=["POST"])
@login_required
def proponentes_scorecard_eliminar(scorecard_id):
    user, allowed, read_only = scorecard_proponentes_user_permiso()

    if not allowed:
        flash("No tiene permiso para eliminar Scorecard de Proponentes.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no puede eliminar scorecards.", "danger")
        return redirect(url_for("proponentes_scorecard_dashboard"))

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM scorecard_proponentes_runs WHERE id = ?", (scorecard_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        flash("Scorecard de Proponente no encontrado.", "warning")
        return redirect(url_for("proponentes_scorecard_dashboard"))

    cur.execute("DELETE FROM scorecard_proponentes_findings WHERE run_id = ?", (scorecard_id,))
    cur.execute("DELETE FROM scorecard_proponentes_outputs WHERE run_id = ?", (scorecard_id,))
    cur.execute("DELETE FROM scorecard_proponentes_incidents WHERE run_id = ?", (scorecard_id,))
    cur.execute("DELETE FROM scorecard_proponentes_darkweb_exposures WHERE run_id = ?", (scorecard_id,))
    cur.execute("DELETE FROM scorecard_proponentes_runs WHERE id = ?", (scorecard_id,))

    conn.commit()
    conn.close()

    flash("Security Scorecard de Terceros eliminado correctamente.", "success")
    return redirect(url_for("proponentes_scorecard_dashboard"))


# ============================================================
# NUEVO SECURITY SCORECARD DE TERCEROS
# Proveedor existente / Proponente manual
# ============================================================

@app.route("/proponentes/scorecard/nuevo", methods=["GET", "POST"])
@login_required
def proponentes_scorecard_scan_nuevo():
    user, allowed, read_only = scorecard_proponentes_user_permiso()

    if not allowed:
        flash("No tiene permiso para ejecutar Security Scorecard de Terceros.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no puede ejecutar nuevos scorecards.", "danger")
        return redirect(url_for("proponentes_scorecard_dashboard"))

    proveedores = ProveedorEvaluacion.query.order_by(ProveedorEvaluacion.nombre_proveedor.asc()).all()

    if request.method == "POST":
        tipo_tercero = (request.form.get("tipo_tercero") or "").strip()
        proveedor_id = request.form.get("proveedor_id")
        proponente_nombre_manual = (request.form.get("proponente_nombre") or "").strip()
        dominio = (request.form.get("dominio") or "").strip()
        ejecutar_kali = bool(request.form.get("ejecutar_kali"))

        herramientas_kali = scorecard_proponentes_normalizar_herramientas_kali(
            request.form.getlist("herramientas_kali")
        )

        proveedor = None
        proveedor_nombre = ""
        proponente_nombre = ""

        if tipo_tercero == "proveedor":
            if not proveedor_id:
                flash("Debe seleccionar un proveedor existente.", "danger")
                return redirect(url_for("proponentes_scorecard_scan_nuevo"))

            proveedor = ProveedorEvaluacion.query.get(proveedor_id)

            if not proveedor:
                flash("El proveedor seleccionado no existe.", "danger")
                return redirect(url_for("proponentes_scorecard_scan_nuevo"))

            proveedor_nombre = proveedor.nombre_proveedor
            proponente_nombre = proveedor_nombre

        else:
            if not proponente_nombre_manual:
                flash("Debe ingresar el nombre del tercero o proponente.", "danger")
                return redirect(url_for("proponentes_scorecard_scan_nuevo"))

            proveedor_id = None
            proveedor_nombre = ""
            proponente_nombre = proponente_nombre_manual

        if not dominio:
            flash("Debe indicar el dominio autorizado del tercero.", "danger")
            return redirect(url_for("proponentes_scorecard_scan_nuevo"))

        if ejecutar_kali and not herramientas_kali:
            flash("Debe seleccionar al menos una herramienta Kali.", "danger")
            return redirect(url_for("proponentes_scorecard_scan_nuevo"))

        ip = resolver_ip_scorecard(dominio)

        score_dns, findings_dns = evaluar_dns_health_proponentes_scorecard(dominio)
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
            current_stage = "Escaneo Kali pendiente con herramientas seleccionadas"

        resumen = {
            "tipo_tercero": tipo_tercero,
            "proveedor_id": proveedor_id,
            "proveedor_nombre": proveedor_nombre,
            "proponente_nombre": proponente_nombre,
            "dns_score": score_dns,
            "ip_score": score_ip,
            "kali_score": score_kali,
            "incident_score": score_incidentes,
            "darkweb_score": score_darkweb,
            "ejecutar_kali": ejecutar_kali,
            "herramientas_kali": herramientas_kali,
            "herramientas_kali_label": scorecard_proponentes_label_herramientas_kali(herramientas_kali)
        }

        conn = get_scorecard_proponentes_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO scorecard_proponentes_runs
            (proponente_nombre, dominio, ip_resuelta,
             score_dns, score_ip, score_kali, score_incidentes, score_darkweb,
             score_total, nivel_riesgo, estado, progress_pct, current_stage,
             current_tool, resumen_json, usuario, fecha_ejecucion, herramientas_kali)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            proponente_nombre,
            dominio,
            ip,
            score_dns,
            score_ip,
            score_kali,
            score_incidentes,
            score_darkweb,
            0,
            "Pendiente",
            estado,
            progress,
            current_stage,
            None,
            json.dumps(resumen, ensure_ascii=False),
            getattr(user, "username", "Sistema"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            json.dumps(herramientas_kali, ensure_ascii=False)
        ))

        run_id = cur.lastrowid
        conn.commit()
        conn.close()

        scorecard_proponentes_set_progress(
            run_id,
            pct=10,
            stage="Guardando hallazgos DNS Health",
            tool="DNS Health"
        )

        for item in findings_dns:
            guardar_scorecard_proponentes_finding(run_id, item)

        scorecard_proponentes_set_progress(
            run_id,
            pct=20,
            stage="Guardando hallazgos IP Reputation",
            tool="IP Reputation"
        )

        for item in findings_ip:
            guardar_scorecard_proponentes_finding(run_id, item)

        try:
            score_incidentes, riesgo_incidentes, total_incidentes = evaluar_incident_history_proponentes_scorecard(
                run_id,
                proponente_nombre,
                dominio
            )
        except Exception:
            score_incidentes = 100

        try:
            score_darkweb, riesgo_darkweb, total_darkweb, credencial_confirmada = evaluar_hacker_chatter_proponentes_scorecard(
                run_id,
                proponente_nombre,
                dominio,
                ip
            )
        except Exception:
            score_darkweb = 100

        if ejecutar_kali:
            conn = get_scorecard_proponentes_db_connection()
            cur = conn.cursor()

            cur.execute("""
                UPDATE scorecard_proponentes_runs
                SET score_incidentes = ?,
                    score_darkweb = ?,
                    estado = ?,
                    progress_pct = ?,
                    current_stage = ?,
                    current_tool = ?,
                    resumen_json = ?
                WHERE id = ?
            """, (
                score_incidentes,
                score_darkweb,
                "pendiente",
                45,
                "Encolando escaneo Kali con herramientas: " + scorecard_proponentes_label_herramientas_kali(herramientas_kali),
                "Kali Linux",
                json.dumps({
                    **resumen,
                    "incident_score": score_incidentes,
                    "darkweb_score": score_darkweb,
                    "herramientas_kali": herramientas_kali,
                    "herramientas_kali_label": scorecard_proponentes_label_herramientas_kali(herramientas_kali)
                }, ensure_ascii=False),
                run_id
            ))

            conn.commit()
            conn.close()

            t = threading.Thread(
                target=scorecard_proponentes_kali_worker,
                args=(run_id, dominio),
                daemon=True
            )
            t.start()

            flash("Scorecard creado. El escaneo Kali se ejecutará con las herramientas seleccionadas.", "success")
            return redirect(url_for("proponentes_scorecard_rating", scorecard_id=run_id))

        score_total = scorecard_proponentes_calcular_total(
            score_dns,
            score_ip,
            score_kali,
            score_incidentes,
            score_darkweb,
            incluir_kali=False
        )

        nivel = nivel_riesgo_scorecard_proponentes(score_total)

        resumen_final = {
            **resumen,
            "incident_score": score_incidentes,
            "darkweb_score": score_darkweb,
            "score_total": score_total,
            "nivel_riesgo": nivel,
            "kali_ejecutado": False
        }

        conn = get_scorecard_proponentes_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE scorecard_proponentes_runs
            SET score_incidentes = ?,
                score_darkweb = ?,
                score_total = ?,
                nivel_riesgo = ?,
                estado = ?,
                progress_pct = ?,
                current_stage = ?,
                current_tool = ?,
                resumen_json = ?,
                fecha_fin = ?
            WHERE id = ?
        """, (
            score_incidentes,
            score_darkweb,
            score_total,
            nivel,
            "finalizado",
            100,
            "Scorecard finalizado sin escaneo Kali",
            None,
            json.dumps(resumen_final, ensure_ascii=False),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            run_id
        ))

        conn.commit()
        conn.close()

        flash("Scorecard ejecutado correctamente.", "success")
        return redirect(url_for("proponentes_scorecard_rating", scorecard_id=run_id))

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .score-new-shell{
        width:96%;
        max-width:1180px;
        margin:26px auto 24px auto;
      }

      .score-new-header{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        border-radius:18px;
        padding:18px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        box-shadow:0 12px 24px rgba(15,23,42,.25);
        margin-bottom:16px;
        color:#fff;
      }

      .score-new-title{
        font-size:1.35rem;
        font-weight:950;
        margin:0;
        color:#fff;
      }

      .score-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        padding:22px;
      }

      .hidden-field{
        display:none;
      }

      .form-label{
        font-weight:900;
        color:#25324a;
        font-size:.82rem;
      }

      .form-control,
      .form-select{
        border-radius:10px;
        min-height:42px;
        border:1px solid #d9e3f0;
        background:#f8fafc;
      }

      .tools-grid{
        display:grid;
        grid-template-columns:repeat(3,minmax(0,1fr));
        gap:12px;
      }

      .tool-check{
        background:#f8fbff;
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px 14px;
        min-height:74px;
        display:flex;
        align-items:flex-start;
        gap:10px;
      }

      .tool-check:hover{
        background:#eef6ff;
        border-color:#9ec5fe;
      }

      .tool-title{
        font-weight:950;
        color:#0b4a8f;
        font-size:.78rem;
      }

      .tool-desc{
        color:#475569;
        font-size:.74rem;
        line-height:1.25;
      }

      .zap-box{
        border-color:#c76b00;
        background:#fff7ed;
      }

      .zap-box .tool-title{
        color:#b45309;
      }

      @media(max-width:768px){
        .tools-grid{
          grid-template-columns:1fr;
        }
      }
    </style>

    <div class="score-new-shell">

      <div class="score-new-header">
        <div>
          <div style="font-size:.72rem;font-weight:900;background:rgba(255,255,255,.18);border-radius:999px;padding:4px 10px;display:inline-block;margin-bottom:6px;">
            SGSI · Security Scorecard
          </div>
          <h2 class="score-new-title">Nuevo Security Scorecard de Terceros</h2>
        </div>
      </div>

      <div class="score-card">

        <form method="post">

          <div class="row g-3">

            <div class="col-md-4">
              <label class="form-label">Tipo de tercero</label>
              <select name="tipo_tercero" id="tipo_tercero" class="form-select" required>
                <option value="">Seleccione...</option>
                <option value="proveedor">Proveedor existente</option>
                <option value="proponente">Nuevo tercero / proponente</option>
              </select>
            </div>

            <div class="col-md-8 hidden-field" id="bloque_proveedor">
              <label class="form-label">Proveedor existente</label>
              <select name="proveedor_id" id="proveedor_id" class="form-select">
                <option value="">Seleccione proveedor...</option>
                {% for p in proveedores %}
                  <option value="{{ p.id }}">{{ p.nombre_proveedor }}</option>
                {% endfor %}
              </select>
            </div>

            <div class="col-md-8 hidden-field" id="bloque_proponente">
              <label class="form-label">Nombre del tercero / proponente</label>
              <input name="proponente_nombre" id="proponente_nombre" class="form-control"
                     placeholder="Ejemplo: Empresa ABC S.A.S.">
            </div>

            <div class="col-md-12">
              <label class="form-label">Dominio autorizado</label>
              <input name="dominio" class="form-control" required
                     placeholder="Ejemplo: tercero.com o https://tercero.com">
            </div>

            <div class="col-12 mt-3">
              <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" name="ejecutar_kali" id="ejecutar_kali" checked>
                <label class="form-check-label fw-bold" for="ejecutar_kali">
                  Ejecutar escaneo técnico Kali / Docker con herramientas seleccionadas
                </label>
              </div>
            </div>

            <div class="col-12" id="bloque_herramientas_kali">
              <label class="form-label">Herramientas de escaneo técnico</label>

              <div class="tools-grid">

                <label class="tool-check">
                  <input type="checkbox" name="herramientas_kali" value="nmap" checked>
                  <div>
                    <div class="tool-title">Nmap</div>
                    <div class="tool-desc">Puertos abiertos y servicios expuestos.</div>
                  </div>
                </label>

                <label class="tool-check">
                  <input type="checkbox" name="herramientas_kali" value="whatweb">
                  <div>
                    <div class="tool-title">WhatWeb</div>
                    <div class="tool-desc">Tecnologías web detectadas.</div>
                  </div>
                </label>

                <label class="tool-check">
                  <input type="checkbox" name="herramientas_kali" value="nikto" checked>
                  <div>
                    <div class="tool-title">Nikto</div>
                    <div class="tool-desc">Hallazgos comunes de seguridad web.</div>
                  </div>
                </label>

                <label class="tool-check">
                  <input type="checkbox" name="herramientas_kali" value="testssl">
                  <div>
                    <div class="tool-title">testssl</div>
                    <div class="tool-desc">Validación TLS/SSL.</div>
                  </div>
                </label>

                <label class="tool-check">
                  <input type="checkbox" name="herramientas_kali" value="nuclei" checked>
                  <div>
                    <div class="tool-title">Nuclei</div>
                    <div class="tool-desc">Templates de vulnerabilidades web.</div>
                  </div>
                </label>

                <label class="tool-check zap-box">
                  <input type="checkbox" name="herramientas_kali" value="zap">
                  <div>
                    <div class="tool-title">OWASP ZAP Full Scan</div>
                    <div class="tool-desc">Spider + Active Scan usando Docker ZAP.</div>
                  </div>
                </label>

              </div>
            </div>

            <div class="col-12">
              <div class="alert alert-warning mb-0">
                <strong>Importante:</strong> use este módulo solo con autorización expresa del proveedor o tercero.
                OWASP ZAP Full Scan puede ser más intrusivo que un escaneo básico.
              </div>
            </div>

            <div class="col-12 d-flex justify-content-between mt-3">
              <a href="{{ url_for('proponentes_scorecard_dashboard') }}" class="btn btn-outline-secondary rounded-pill px-4">
                Volver
              </a>

              <button class="btn btn-warning text-dark rounded-pill px-4 fw-bold">
                🚀 Ejecutar Scorecard
              </button>
            </div>

          </div>

        </form>
      </div>
    </div>

    <script>
      function actualizarTipoTercero(){
        const tipo = document.getElementById("tipo_tercero").value;
        const bloqueProveedor = document.getElementById("bloque_proveedor");
        const bloqueProponente = document.getElementById("bloque_proponente");
        const proveedor = document.getElementById("proveedor_id");
        const proponente = document.getElementById("proponente_nombre");

        if(tipo === "proveedor"){
          bloqueProveedor.classList.remove("hidden-field");
          bloqueProponente.classList.add("hidden-field");
          proveedor.setAttribute("required", "required");
          proponente.removeAttribute("required");
          proponente.value = "";
        }
        else if(tipo === "proponente"){
          bloqueProveedor.classList.add("hidden-field");
          bloqueProponente.classList.remove("hidden-field");
          proveedor.removeAttribute("required");
          proveedor.value = "";
          proponente.setAttribute("required", "required");
        }
        else{
          bloqueProveedor.classList.add("hidden-field");
          bloqueProponente.classList.add("hidden-field");
          proveedor.removeAttribute("required");
          proveedor.value = "";
          proponente.removeAttribute("required");
          proponente.value = "";
        }
      }

      function toggleHerramientasKali(){
        const chk = document.getElementById("ejecutar_kali");
        const bloque = document.getElementById("bloque_herramientas_kali");

        if(!chk || !bloque) return;

        bloque.style.display = chk.checked ? "block" : "none";
      }

      document.addEventListener("DOMContentLoaded", function(){
        const tipo = document.getElementById("tipo_tercero");
        if(tipo){
          tipo.addEventListener("change", actualizarTipoTercero);
          actualizarTipoTercero();
        }

        const kali = document.getElementById("ejecutar_kali");
        if(kali){
          kali.addEventListener("change", toggleHerramientasKali);
          toggleHerramientasKali();
        }
      });
    </script>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            proveedores=proveedores
        ))
    )


# ============================================================
# ESTADO JSON PROPONENTES
# ============================================================

@app.route("/proponentes/scorecard/<int:scorecard_id>/estado")
@login_required
def proponentes_scorecard_estado(scorecard_id):
    user, allowed, read_only = scorecard_proponentes_user_permiso()

    if not allowed:
        return jsonify({
            "ok": False,
            "error": "No tiene permiso para consultar el estado del Scorecard."
        }), 403

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, estado, progress_pct, current_stage, current_tool,
               score_total, score_dns, score_ip, score_kali,
               score_incidentes, score_darkweb, nivel_riesgo, error_detalle
        FROM scorecard_proponentes_runs
        WHERE id = ?
    """, (scorecard_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({
            "ok": False,
            "error": "Scorecard no encontrado."
        }), 404

    return jsonify({
        "ok": True,
        "id": row["id"],
        "estado": row["estado"] or "pendiente",
        "progress_pct": int(row["progress_pct"] or 0),
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

def scorecard_proponentes_explicar_calculo_riesgo(run):
    try:
        resumen = json.loads(run["resumen_json"] or "{}")
    except Exception:
        resumen = {}

    score_dns = float(run["score_dns"] or 0)
    score_ip = float(run["score_ip"] or 0)
    score_kali = float(run["score_kali"] or 0)
    score_incidentes = float(run["score_incidentes"] or 100)
    score_darkweb = float(run["score_darkweb"] or 100)

    incluir_kali = bool(resumen.get("kali_ejecutado")) or bool(resumen.get("ejecutar_kali") and score_kali > 0)

    peso_dns = scorecard_proponentes_get_param("peso_dns", 20)
    peso_ip = scorecard_proponentes_get_param("peso_ip", 15)
    peso_kali = scorecard_proponentes_get_param("peso_kali", 35)
    peso_incidentes = scorecard_proponentes_get_param("peso_incidentes", 15)
    peso_darkweb = scorecard_proponentes_get_param("peso_darkweb", 15)

    componentes = [
        {"nombre": "DNS Health", "score": score_dns, "peso": peso_dns},
        {"nombre": "IP Reputation / DNSBL", "score": score_ip, "peso": peso_ip},
        {"nombre": "Incidentes / OSINT", "score": score_incidentes, "peso": peso_incidentes},
        {"nombre": "Dark Web / Exposure Intelligence", "score": score_darkweb, "peso": peso_darkweb},
    ]

    if incluir_kali:
        componentes.append({"nombre": "Kali Linux Scan", "score": score_kali, "peso": peso_kali})

    total_pesos = sum(c["peso"] for c in componentes)

    for c in componentes:
        c["aporte"] = round((c["score"] * c["peso"]) / total_pesos, 2) if total_pesos else 0
        c["formula"] = f"({c['score']:.1f} × {c['peso']:.1f}) / {total_pesos:.1f}"

    score_total = round(sum(c["aporte"] for c in componentes), 2)
    nivel = nivel_riesgo_scorecard_proponentes(score_total)

    return {
        "componentes": componentes,
        "total_pesos": total_pesos,
        "score_total": score_total,
        "nivel": nivel,
        "incluye_kali": incluir_kali,
        "formula_general": "Score Total = Σ(Score componente × Peso componente) / Σ(Pesos aplicables)"
    }


# ============================================================
# DETALLE SCORECARD PROPONENTES - MISMO DISEÑO QUE PROVEEDORES
# CON COLOR DE RIESGO SEGÚN PARÁMETROS
# CON EXPLICACIÓN DEL CÁLCULO DEL RIESGO
# ============================================================

@app.route("/proponentes/scorecard/<int:scorecard_id>")
@login_required
def proponentes_scorecard_detalle(scorecard_id):
    user, allowed, read_only = scorecard_proponentes_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al Security Scorecard de Terceros.", "danger")
        return redirect(url_for("menu"))

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM scorecard_proponentes_runs
        WHERE id = ?
    """, (scorecard_id,))
    run = cur.fetchone()

    if not run:
        conn.close()
        abort(404)

    cur.execute("""
        SELECT *
        FROM scorecard_proponentes_findings
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
        FROM scorecard_proponentes_incidents
        WHERE run_id = ?
        ORDER BY
          CASE severidad
            WHEN 'Crítico' THEN 1
            WHEN 'Critico' THEN 1
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
        FROM scorecard_proponentes_darkweb_exposures
        WHERE run_id = ?
        ORDER BY
          CASE severidad
            WHEN 'Crítico' THEN 1
            WHEN 'Critico' THEN 1
            WHEN 'Alto' THEN 2
            WHEN 'Medio' THEN 3
            WHEN 'Bajo' THEN 4
            ELSE 5
          END,
          id ASC
    """, (scorecard_id,))
    hacker_chatter = cur.fetchall()

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_proponentes_findings
        WHERE run_id = ?
          AND categoria = 'Kali Linux Scan'
    """, (scorecard_id,))
    total_kali = cur.fetchone()["total"] or 0

    conn.close()

    # ============================================================
    # EXPLICACIÓN DEL CÁLCULO DEL RIESGO
    # ============================================================
    calculo_riesgo = scorecard_proponentes_explicar_calculo_riesgo(run)

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
        display:grid;
        grid-template-columns:1fr 1fr 1fr 1fr;
        gap:10px;
        margin:10px 0 14px;
        align-items:center;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        padding:.55rem 1.05rem;
        font-size:.78rem;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .score-main-card{
        background:rgba(255,255,255,.97);
        border:1px solid #dbe6f4;
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.16);
        padding:28px 32px;
        margin-bottom:18px;
      }

      .summary-grid{
        display:grid;
        grid-template-columns:.85fr 1.25fr;
        gap:28px;
        align-items:center;
      }

      .score-big{
        text-align:center;
      }

      .score-number{
        font-size:3.8rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1;
      }

      .risk-pill{
        display:inline-block;
        border-radius:999px;
        font-weight:950;
        padding:4px 14px;
        font-size:1rem;
      }

      .risk-pill.bg-warning,
      .risk-pill.text-dark{
        color:#0b1220 !important;
      }

      .company-title{
        font-size:1.55rem;
        font-weight:950;
        color:#172033;
        margin-bottom:8px;
      }

      .company-meta{
        font-size:1rem;
        font-weight:800;
        color:#101827;
        margin-bottom:6px;
      }

      .progress-panel{
        background:#eef5ff;
        border:1px solid #cfe0f7;
        border-radius:14px;
        padding:14px 16px;
        margin:16px 0;
      }

      .progress{
        height:24px;
        border-radius:999px;
        background:#dbeafe;
        overflow:hidden;
      }

      .progress-bar{
        font-weight:950;
        background:
          repeating-linear-gradient(45deg,rgba(255,255,255,.18) 0,rgba(255,255,255,.18) 10px,transparent 10px,transparent 20px),
          linear-gradient(135deg,#198754,#2dbb73);
      }

      .section-card{
        background:rgba(255,255,255,.97);
        border:1px solid #dbe6f4;
        border-radius:18px;
        box-shadow:0 10px 22px rgba(15,23,42,.13);
        padding:18px;
        margin-bottom:18px;
      }

      .section-title{
        color:#0b4a8f;
        font-weight:950;
        margin-bottom:12px;
      }

      .table-wrap{
        max-height:55vh;
        overflow:auto;
        border-radius:14px;
        border:1px solid #dbe6f4;
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
        font-weight:900;
        text-align:center;
        white-space:nowrap;
      }

      .table td{
        font-size:.82rem;
        vertical-align:middle;
      }

      .badge{
        border-radius:999px;
        font-weight:900;
      }

      .calc-risk-box{
        border-radius:16px;
        background:linear-gradient(135deg,#eef6ff,#ffffff);
        border:1px solid #cfe0f7;
        box-shadow:0 8px 18px rgba(15,23,42,.10);
      }

      .calc-risk-box .table thead th{
        position:static !important;
        background:#dbeafe !important;
        color:#0f3f75 !important;
      }

      @media(max-width:1100px){
        .action-bar{
          grid-template-columns:1fr 1fr;
        }

        .summary-grid{
          grid-template-columns:1fr;
        }
      }

      @media(max-width:720px){
        .action-bar{
          grid-template-columns:1fr;
        }
      }
    </style>

    <div class="score-shell">

      <div class="score-header-card">
        <h1 class="score-header-text">Detalle Security Scorecard de Terceros</h1>
      </div>

      <div class="action-bar">
        <a href="{{ url_for('proponentes_scorecard_dashboard') }}" class="btn btn-outline-secondary">
          Volver
        </a>

        <a href="{{ url_for('proponentes_scorecard_rating', scorecard_id=run.id) }}" class="btn btn-success">
          📊 SecurityScorecard Terceros
        </a>

        <a href="{{ url_for('proponentes_scorecard_kali_detalle', scorecard_id=run.id) }}" class="btn btn-warning text-dark">
          🧪 Ver Detalle Kali Linux
        </a>

        <a href="{{ url_for('proponentes_scorecard_detalle', scorecard_id=run.id) }}" class="btn btn-primary">
          🔄 Actualizar
        </a>
      </div>

      <div class="score-main-card">
        <div class="summary-grid">

          <div class="score-big">
            <div id="scoreTotal" class="score-number">{{ "%.1f"|format(run.score_total or 0) }}%</div>

            <div id="riskNivel"
                 class="risk-pill bg-{{ scorecard_proponentes_badge_color(run.nivel_riesgo or 'Pendiente') }}">
              Riesgo {{ run.nivel_riesgo or "Pendiente" }}
            </div>
          </div>

          <div>
            <div class="company-title">{{ run.proponente_nombre }}</div>
            <div class="company-meta"><strong>Dominio:</strong> {{ run.dominio }}</div>
            <div class="company-meta"><strong>IP:</strong> {{ run.ip_resuelta or "—" }}</div>

            <div class="progress-panel">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <div class="fw-bold text-primary">
                  Estado:
                  <span id="estadoBadge" class="badge bg-success">{{ run.estado or "pendiente" }}</span>
                </div>
                <div class="fw-bold text-primary">
                  Progreso: <span id="progressLabel">{{ run.progress_pct or 0 }}</span>%
                </div>
              </div>

              <div class="progress">
                <div id="progressBar" class="progress-bar" style="width:{{ run.progress_pct or 0 }}%;">
                  {{ run.progress_pct or 0 }}%
                </div>
              </div>

              <div id="progressNote" class="mt-2 text-muted fw-bold">
                {% if run.estado == 'finalizado' %}
                  Actualización automática detenida porque el proceso está finalizado.
                {% elif run.estado == 'error' %}
                  Proceso finalizado con error.
                {% else %}
                  Actualizando automáticamente el progreso del Scorecard.
                {% endif %}
              </div>
            </div>

            <div class="company-meta">
              <strong>Etapa:</strong> <span id="currentStage">{{ run.current_stage or "—" }}</span>
            </div>

            <div class="company-meta">
              <strong>Herramienta actual:</strong> <span id="currentTool">{{ run.current_tool or "—" }}</span>
            </div>

            <div class="company-meta">
              <strong>Fecha:</strong> {{ run.fecha_ejecucion }}
            </div>
          </div>

        </div>
      </div>

      <div class="section-card">
        <h5 class="section-title">🧩 Hallazgos Generales</h5>

        <div class="alert alert-primary border-0 shadow-sm mb-3 calc-risk-box">
          <div class="fw-bold mb-2">🧮 Cálculo del Riesgo del Proponente</div>

          <div class="small text-muted mb-2">
            {{ calculo_riesgo.formula_general }}
          </div>

          <div class="table-responsive">
            <table class="table table-sm table-bordered align-middle mb-2">
              <thead class="table-primary">
                <tr>
                  <th>Componente</th>
                  <th class="text-center">Score</th>
                  <th class="text-center">Peso</th>
                  <th class="text-center">Fórmula</th>
                  <th class="text-center">Aporte</th>
                </tr>
              </thead>
              <tbody>
                {% for c in calculo_riesgo.componentes %}
                <tr>
                  <td class="fw-bold">{{ c.nombre }}</td>
                  <td class="text-center">{{ "%.1f"|format(c.score) }}</td>
                  <td class="text-center">{{ "%.1f"|format(c.peso) }}</td>
                  <td class="text-center small">{{ c.formula }}</td>
                  <td class="text-center fw-bold">{{ "%.2f"|format(c.aporte) }}</td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>

          <div class="d-flex flex-wrap gap-2 mt-2">
            <span class="badge bg-primary">
              Score Total: {{ "%.2f"|format(calculo_riesgo.score_total) }}%
            </span>

            <span class="badge bg-{{ scorecard_proponentes_badge_color(calculo_riesgo.nivel) }}">
              Riesgo: {{ calculo_riesgo.nivel }}
            </span>

            {% if calculo_riesgo.incluye_kali %}
              <span class="badge bg-dark">Kali incluido en el cálculo</span>
            {% else %}
              <span class="badge bg-secondary">Kali no incluido</span>
            {% endif %}
          </div>
        </div>

        <div class="table-wrap">
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
                <td>{{ f.herramienta or "—" }}</td>
                <td>{{ f.control or "—" }}</td>
                <td>{{ f.estado or "—" }}</td>
                <td>
                  <span class="badge bg-{{ scorecard_proponentes_badge_color(f.riesgo or f.severidad or 'Bajo') }}">
                    {{ f.riesgo or f.severidad or "Bajo" }}
                  </span>
                </td>
                <td class="fw-bold">{{ "%.1f"|format(f.score or 0) }}</td>
                <td style="min-width:280px;">{{ f.evidencia or "—" }}</td>
                <td style="min-width:280px;">{{ f.recomendacion or "—" }}</td>
              </tr>
              {% else %}
              <tr>
                <td colspan="8" class="text-center text-muted py-4">
                  No hay hallazgos generales registrados.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="section-card">
        <h5 class="section-title">📰 Incidentes / Brechas OSINT</h5>
        <div class="table-wrap">
          <table class="table table-hover align-middle">
            <thead>
              <tr>
                <th>Fuente</th>
                <th>Título</th>
                <th>Fecha</th>
                <th>Severidad</th>
                <th>Descripción</th>
                <th>URL</th>
              </tr>
            </thead>
            <tbody>
              {% for i in incidentes %}
              <tr>
                <td>{{ i.fuente or "—" }}</td>
                <td>{{ i.titulo or "—" }}</td>
                <td>{{ i.fecha_incidente or "—" }}</td>
                <td>
                  <span class="badge bg-{{ scorecard_proponentes_badge_color(i.severidad or 'Bajo') }}">
                    {{ i.severidad or "Bajo" }}
                  </span>
                </td>
                <td style="min-width:320px;">{{ i.descripcion or "—" }}</td>
                <td>
                  {% if i.url %}
                    <a href="{{ i.url }}" target="_blank" class="btn btn-sm btn-outline-primary">Abrir</a>
                  {% else %}
                    —
                  {% endif %}
                </td>
              </tr>
              {% else %}
              <tr>
                <td colspan="6" class="text-center text-muted py-4">
                  No hay incidentes públicos registrados.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="section-card">
        <h5 class="section-title">🕵️ Dark Web / Exposure Intelligence / Hacker Chatter</h5>
        <div class="table-wrap">
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
                <td>{{ h.fuente or "—" }}</td>
                <td>{{ h.tipo_exposicion or "—" }}</td>
                <td>{{ h.indicador or "—" }}</td>
                <td>
                  <span class="badge bg-{{ scorecard_proponentes_badge_color(h.severidad or 'Bajo') }}">
                    {{ h.severidad or "Bajo" }}
                  </span>
                </td>
                <td>{{ h.fecha or "—" }}</td>
                <td style="min-width:300px;">{{ h.evidencia or "—" }}</td>
                <td style="min-width:300px;">{{ h.recomendacion or "—" }}</td>
                <td>
                  {% if h.url %}
                    <a href="{{ h.url }}" target="_blank" class="btn btn-sm btn-outline-primary">Abrir</a>
                  {% else %}
                    —
                  {% endif %}
                </td>
              </tr>
              {% else %}
              <tr>
                <td colspan="8" class="text-center text-muted py-4">
                  No hay exposiciones registradas.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <script>
      const SCORECARD_ESTADO_URL = "{{ url_for('proponentes_scorecard_estado', scorecard_id=run.id) }}";

      function setBadge(estado){
        const badge = document.getElementById("estadoBadge");

        badge.className = "badge";

        if(estado === "finalizado"){
          badge.classList.add("bg-success");
          badge.textContent = "Finalizado";
        }else if(estado === "error"){
          badge.classList.add("bg-danger");
          badge.textContent = "Error";
        }else if(estado === "ejecutando"){
          badge.classList.add("bg-primary");
          badge.textContent = "Ejecutando";
        }else{
          badge.classList.add("bg-secondary");
          badge.textContent = estado || "Pendiente";
        }
      }

      function setRiskColor(nivel){
        const riskNivel = document.getElementById("riskNivel");
        riskNivel.textContent = "Riesgo " + (nivel || "Pendiente");
        riskNivel.className = "risk-pill";

        if(nivel === "Bajo"){
          riskNivel.classList.add("bg-success");
        }else if(nivel === "Medio"){
          riskNivel.classList.add("bg-warning", "text-dark");
        }else if(nivel === "Alto"){
          riskNivel.classList.add("bg-danger");
        }else if(nivel === "Crítico" || nivel === "Critico"){
          riskNivel.classList.add("bg-dark");
        }else{
          riskNivel.classList.add("bg-secondary");
        }
      }

      async function refreshScorecardStatus(){
        try{
          const resp = await fetch(SCORECARD_ESTADO_URL, {cache:"no-store"});
          const data = await resp.json();

          if(!data.ok){
            return;
          }

          const pct = Number(data.progress_pct || 0);

          document.getElementById("progressLabel").textContent = pct;
          document.getElementById("progressBar").style.width = pct + "%";
          document.getElementById("progressBar").textContent = pct + "%";

          document.getElementById("currentStage").textContent = data.current_stage || "—";
          document.getElementById("currentTool").textContent = data.current_tool || "—";
          document.getElementById("scoreTotal").textContent = Number(data.score_total || 0).toFixed(1) + "%";

          setRiskColor(data.nivel_riesgo);
          setBadge(data.estado);

          if(data.estado === "finalizado"){
            document.getElementById("progressNote").textContent = "Actualización automática detenida porque el proceso está finalizado.";
            clearInterval(window.scorecardTimer);
          }

          if(data.estado === "error"){
            document.getElementById("progressNote").textContent = "Proceso finalizado con error.";
            clearInterval(window.scorecardTimer);
          }

        }catch(e){
          console.log("No se pudo actualizar estado Scorecard Proponentes", e);
        }
      }

      {% if run.estado not in ['finalizado', 'error'] %}
        window.scorecardTimer = setInterval(refreshScorecardStatus, 3000);
        refreshScorecardStatus();
      {% endif %}
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
            calculo_riesgo=calculo_riesgo,
            scorecard_proponentes_badge_color=scorecard_proponentes_badge_color
        ))
    )

# ============================================================
# DETALLE KALI LINUX - PROPONENTES
# ============================================================

@app.route("/proponentes/scorecard/<int:scorecard_id>/kali")
@login_required
def proponentes_scorecard_kali_detalle(scorecard_id):
    user, allowed, read_only = scorecard_proponentes_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al detalle Kali de Proponentes.", "danger")
        return redirect(url_for("menu"))

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM scorecard_proponentes_runs
        WHERE id = ?
    """, (scorecard_id,))
    run = cur.fetchone()

    if not run:
        conn.close()
        abort(404)

    cur.execute("""
        SELECT *
        FROM scorecard_proponentes_findings
        WHERE run_id = ?
          AND categoria = 'Kali Linux Scan'
        ORDER BY
          CASE COALESCE(severidad, riesgo, '')
            WHEN 'Crítico' THEN 1
            WHEN 'Critico' THEN 1
            WHEN 'Alto' THEN 2
            WHEN 'Medio' THEN 3
            WHEN 'Bajo' THEN 4
            ELSE 5
          END,
          id ASC
    """, (scorecard_id,))
    kali_findings = cur.fetchall()

    cur.execute("""
        SELECT *
        FROM scorecard_proponentes_outputs
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

      .score-header-card::after{
        content:"🧪";
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
      }

      .score-header-text{
        color:#fff !important;
        font-size:1.32rem;
        font-weight:950;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .score-header-text::before{
        content:"SGSI · Kali Linux Scorecard";
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

      .action-bar{
        display:flex;
        justify-content:space-between;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
      }

      .section-card{
        background:rgba(255,255,255,.97);
        border:1px solid #dbe6f4;
        border-radius:18px;
        box-shadow:0 10px 22px rgba(15,23,42,.13);
        padding:18px;
        margin-bottom:18px;
      }

      .section-title{
        color:#0b4a8f;
        font-weight:950;
        margin-bottom:12px;
      }

      .table-wrap{
        max-height:62vh;
        overflow:auto;
        border-radius:14px;
        border:1px solid #dbe6f4;
      }

      .table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-size:.78rem;
        font-weight:900;
        text-align:center;
        white-space:nowrap;
      }

      .table td{
        font-size:.82rem;
        vertical-align:middle;
      }

      .console-box{
        background:#0f172a;
        color:#d1e7ff;
        border-radius:14px;
        padding:8px 7px;
        max-height:420px;
        overflow:auto;
        font-size:.78rem;
        white-space:pre-wrap;
      }
    </style>

    <div class="score-shell">

      <div class="score-header-card">
        <h1 class="score-header-text">Detalle Kali Linux — Terceros</h1>
      </div>

      <div class="action-bar">
        <a href="{{ url_for('proponentes_scorecard_detalle', scorecard_id=run.id) }}" class="btn btn-outline-secondary px-4">
          Volver al detalle
        </a>

        <a href="{{ url_for('proponentes_scorecard_dashboard') }}" class="btn btn-primary px-4">
          Dashboard Scorecard
        </a>
      </div>

      <div class="section-card">
          <h5 class="section-title">🧾 Información del Escaneo</h5>

          <p class="fw-bold mb-1">Proponente: {{ run.proponente_nombre }}</p>
          <p class="fw-bold mb-1">Dominio: {{ run.dominio }}</p>
          <p class="fw-bold mb-1">IP: {{ run.ip_resuelta or "—" }}</p>
          <p class="fw-bold mb-1">Modo Kali: {{ run.modo_kali or "Motor Registro de Vulnerabilidades" }}</p>
          <p class="fw-bold mb-1">Score Kali: <span id="scoreKali">{{ "%.1f"|format(run.score_kali or 0) }}</span></p>

          <div class="mt-3 p-3 rounded-4" style="background:#eef5ff;border:1px solid #cfe0f7;">
            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
              <div class="fw-bold text-primary">
                Estado:
                <span id="estadoBadge" class="badge bg-primary">{{ run.estado or "pendiente" }}</span>
              </div>

              <div class="fw-bold text-primary">
                Progreso: <span id="progressLabel">{{ run.progress_pct or 0 }}</span>%
              </div>
            </div>

            <div class="progress" style="height:24px;border-radius:999px;background:#dbeafe;overflow:hidden;">
              <div id="progressBar"
                   class="progress-bar progress-bar-striped progress-bar-animated"
                   style="width:{{ run.progress_pct or 0 }}%;font-weight:950;">
                {{ run.progress_pct or 0 }}%
              </div>
            </div>

            <div class="row mt-3">
              <div class="col-md-6">
                <div class="fw-bold text-muted">Etapa actual</div>
                <div id="currentStage" class="fw-bold">{{ run.current_stage or "—" }}</div>
              </div>
              <div class="col-md-6">
                <div class="fw-bold text-muted">Herramienta actual</div>
                <div id="currentTool" class="fw-bold">{{ run.current_tool or "—" }}</div>
              </div>
            </div>

            <div id="progressNote" class="mt-2 text-muted fw-bold">
              {% if run.estado == 'finalizado' %}
                Escaneo Kali finalizado.
              {% elif run.estado == 'error' %}
                Escaneo Kali finalizado con error.
              {% else %}
                Escaneo Kali en ejecución. Esta pantalla se actualiza automáticamente.
              {% endif %}
            </div>
          </div>
        </div>

      <div class="section-card">
        <h5 class="section-title">🧪 Hallazgos Kali Linux</h5>
        <div class="table-wrap">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>Herramienta</th>
                <th>Control</th>
                <th>Estado</th>
                <th>Severidad</th>
                <th>Score</th>
                <th>Evidencia</th>
                <th>Recomendación</th>
                <th>Archivo</th>
              </tr>
            </thead>
            <tbody>
              {% for f in kali_findings %}
              <tr>
                <td>{{ f.herramienta or "—" }}</td>
                <td>{{ f.control or "—" }}</td>
                <td>{{ f.estado or "—" }}</td>
                <td>
                  <span class="badge bg-{{ scorecard_proponentes_badge_color(f.severidad or f.riesgo or 'Bajo') }}">
                    {{ f.severidad or f.riesgo or "Bajo" }}
                  </span>
                </td>
                <td class="fw-bold">{{ "%.1f"|format(f.score or 0) }}</td>
                <td style="min-width:320px;">{{ f.evidencia or "—" }}</td>
                <td style="min-width:320px;">{{ f.recomendacion or "—" }}</td>
                <td style="min-width:240px;">{{ f.archivo_salida or "—" }}</td>
              </tr>
              {% else %}
              <tr>
                <td colspan="8" class="text-center text-muted py-4">
                  No hay hallazgos Kali registrados. Puede que el escaneo no se haya ejecutado.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="section-card">
        <h5 class="section-title">📁 Salidas de Herramientas</h5>
        <div class="table-wrap">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>Herramienta</th>
                <th>Comando</th>
                <th>Exit Code</th>
                <th>Duración</th>
                <th>Archivo</th>
                <th>Fecha</th>
              </tr>
            </thead>
            <tbody>
              {% for o in outputs %}
              <tr>
                <td>{{ o.herramienta or "—" }}</td>
                <td style="min-width:420px;"><code>{{ o.comando or "—" }}</code></td>
                <td>{{ o.exit_code }}</td>
                <td>{{ "%.2f"|format(o.duracion_segundos or 0) }}s</td>
                <td style="min-width:280px;">{{ o.archivo_salida or "—" }}</td>
                <td>{{ o.fecha or "—" }}</td>
              </tr>
              {% else %}
              <tr>
                <td colspan="6" class="text-center text-muted py-4">
                  No hay salidas de herramientas registradas.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      {% if run.salida_consola %}
      <div class="section-card">
        <h5 class="section-title">🖥️ Consola Consolidada</h5>
        <div class="console-box">{{ run.salida_consola }}</div>
      </div>
      {% endif %}

    </div>
    <script>
      const KALI_ESTADO_URL = "{{ url_for('proponentes_scorecard_estado', scorecard_id=run.id) }}";

      function setKaliBadge(estado){
        const badge = document.getElementById("estadoBadge");
        if(!badge){ return; }

        badge.className = "badge";

        if(estado === "finalizado"){
          badge.classList.add("bg-success");
          badge.textContent = "Finalizado";
        }else if(estado === "error"){
          badge.classList.add("bg-danger");
          badge.textContent = "Error";
        }else if(estado === "ejecutando"){
          badge.classList.add("bg-primary");
          badge.textContent = "Ejecutando";
        }else{
          badge.classList.add("bg-secondary");
          badge.textContent = estado || "Pendiente";
        }
      }

      async function refreshKaliStatus(){
        try{
          const resp = await fetch(KALI_ESTADO_URL, {cache:"no-store"});
          const data = await resp.json();

          if(!data.ok){
            return;
          }

          const pct = Number(data.progress_pct || 0);

          document.getElementById("progressLabel").textContent = pct;
          document.getElementById("progressBar").style.width = pct + "%";
          document.getElementById("progressBar").textContent = pct + "%";

          document.getElementById("currentStage").textContent = data.current_stage || "—";
          document.getElementById("currentTool").textContent = data.current_tool || "—";
          document.getElementById("scoreKali").textContent = Number(data.score_kali || 0).toFixed(1);

          setKaliBadge(data.estado);

          if(data.estado === "finalizado"){
            document.getElementById("progressNote").textContent = "Escaneo Kali finalizado.";
            clearInterval(window.kaliTimer);
            setTimeout(() => window.location.reload(), 1200);
          }

          if(data.estado === "error"){
            document.getElementById("progressNote").textContent = "Escaneo Kali finalizado con error.";
            clearInterval(window.kaliTimer);
          }

        }catch(e){
          console.log("No se pudo actualizar el estado Kali Proponentes", e);
        }
      }

      {% if run.estado not in ['finalizado', 'error'] %}
        window.kaliTimer = setInterval(refreshKaliStatus, 3000);
        refreshKaliStatus();
      {% endif %}
    </script>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            run=run,
            kali_findings=kali_findings,
            outputs=outputs,
            scorecard_proponentes_badge_color=scorecard_proponentes_badge_color
        ))
    )

# ============================================================
# ADMIN - CONFIGURACIÓN APIs SCORECARD PROPONENTES / TERCEROS
# ============================================================

@app.route("/admin/scorecard-proponentes/apis", methods=["GET", "POST"])
@login_required
def admin_scorecard_proponentes_apis():
    user, allowed, read_only = scorecard_proponentes_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al Security Scorecard de Terceros.", "danger")
        return redirect(url_for("menu"))

    puede_configurar = (
        user.role == "admin"
        or (
            user.role != "auditor"
            and verificar_permiso(user, SCORECARD_PROPONENTES_PERMISO)
        )
    )

    if not puede_configurar:
        flash("No tiene permiso para configurar las APIs del Scorecard de Terceros.", "danger")
        return redirect(url_for("proponentes_scorecard_dashboard"))

    if request.method == "POST":
        proveedor = (request.form.get("proveedor") or "").strip().lower()
        api_key = (request.form.get("api_key") or "").strip()
        activo = bool(request.form.get("activo"))

        if proveedor not in ["leakcheck", "hibp", "shodan"]:
            flash("Proveedor API no válido.", "danger")
            return redirect(url_for("admin_scorecard_proponentes_apis"))

        scorecard_proponentes_guardar_api_key(
            proveedor,
            api_key,
            activo,
            getattr(user, "username", "admin")
        )

        try:
            registrar_log(
                getattr(user, "username", "admin"),
                f"Actualizó API {proveedor} para Security Scorecard de Terceros"
            )
        except Exception:
            pass

        flash("Configuración de API actualizada correctamente para Terceros.", "success")
        return redirect(url_for("admin_scorecard_proponentes_apis"))

    estado_apis = scorecard_proponentes_api_status()

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .api-prop-shell{
        width:96%;
        max-width:1300px;
        margin:26px auto 24px auto;
      }

      .api-prop-header-card{
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

      .api-prop-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .api-prop-header-overlay{
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

      .api-prop-header-overlay::before{
        content:"🔌";
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

      .api-prop-header-overlay h2{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .api-prop-header-overlay h2::before{
        content:"SGSI · Configuración de APIs Terceros";
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

      .soft-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .api-card{
        background:#ffffff;
        border-radius:16px;
        box-shadow:0 8px 18px rgba(15,23,42,.10);
        padding:18px;
        height:100%;
        border:1px solid #dbe6f4;
      }

      .api-title{
        color:#0b4a8f;
        font-weight:950;
        font-size:1.05rem;
      }

      .api-muted{
        color:#607086;
        font-size:.9rem;
        font-weight:700;
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
        .api-prop-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .api-prop-header-card{
          min-height:88px;
        }

        .api-prop-header-overlay h2{
          font-size:1.20rem;
        }
      }

      @media (max-width:768px){
        .api-prop-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .api-prop-header-overlay::before{
          margin:0;
        }

        .api-prop-header-overlay h2,
        .api-prop-header-overlay h2::before{
          text-align:center;
          margin-left:auto;
          margin-right:auto;
        }
      }
    </style>

    <div class="api-prop-shell">

      <div class="api-prop-header-card">
        <div class="api-prop-header-overlay">
          <h2>APIs — Security Scorecard de Terceros</h2>
        </div>
      </div>

      <div class="d-flex justify-content-between align-items-center mb-3">
        <a href="{{ url_for('proponentes_scorecard_dashboard') }}" class="btn btn-light rounded-pill px-4">
          ⬅ Volver
        </a>
      </div>

      <div class="row g-4">

        <div class="col-md-4">
          <div class="api-card">
            <div class="api-title">LeakCheck API</div>
            <div class="api-muted mb-2">Credenciales filtradas / exposición de identidades.</div>

            <div class="mb-2">
              Estado:
              {% if estado_apis.leakcheck.activo and estado_apis.leakcheck.configurada %}
                <span class="badge bg-success">Activa</span>
              {% elif estado_apis.leakcheck.configurada %}
                <span class="badge bg-warning text-dark">Configurada inactiva</span>
              {% else %}
                <span class="badge bg-secondary">No configurada</span>
              {% endif %}
            </div>

            <div class="mb-3">
              <strong>Key:</strong> {{ estado_apis.leakcheck.mask }}
            </div>

            <form method="POST">
              <input type="hidden" name="proveedor" value="leakcheck">

              <div class="mb-3">
                <label class="form-label fw-bold">Nueva API Key</label>
                <input type="password" name="api_key" class="form-control" placeholder="Pegar API Key LeakCheck">
              </div>

              <div class="form-check form-switch mb-3">
                <input class="form-check-input" type="checkbox" name="activo" id="activo_leakcheck"
                       {% if estado_apis.leakcheck.activo %}checked{% endif %}>
                <label class="form-check-label" for="activo_leakcheck">Activa</label>
              </div>

              <button class="btn btn-primary rounded-pill w-100">
                Guardar LeakCheck
              </button>
            </form>
          </div>
        </div>

        <div class="col-md-4">
          <div class="api-card">
            <div class="api-title">Have I Been Pwned API</div>
            <div class="api-muted mb-2">Brechas por dominio verificado.</div>

            <div class="mb-2">
              Estado:
              {% if estado_apis.hibp.activo and estado_apis.hibp.configurada %}
                <span class="badge bg-success">Activa</span>
              {% elif estado_apis.hibp.configurada %}
                <span class="badge bg-warning text-dark">Configurada inactiva</span>
              {% else %}
                <span class="badge bg-secondary">No configurada</span>
              {% endif %}
            </div>

            <div class="mb-3">
              <strong>Key:</strong> {{ estado_apis.hibp.mask }}
            </div>

            <form method="POST">
              <input type="hidden" name="proveedor" value="hibp">

              <div class="mb-3">
                <label class="form-label fw-bold">Nueva API Key</label>
                <input type="password" name="api_key" class="form-control" placeholder="Pegar API Key HIBP">
              </div>

              <div class="form-check form-switch mb-3">
                <input class="form-check-input" type="checkbox" name="activo" id="activo_hibp"
                       {% if estado_apis.hibp.activo %}checked{% endif %}>
                <label class="form-check-label" for="activo_hibp">Activa</label>
              </div>

              <button class="btn btn-primary rounded-pill w-100">
                Guardar HIBP
              </button>
            </form>
          </div>
        </div>

        <div class="col-md-4">
          <div class="api-card">
            <div class="api-title">Shodan API</div>
            <div class="api-muted mb-2">Servicios expuestos / CVEs / superficie externa.</div>

            <div class="mb-2">
              Estado:
              {% if estado_apis.shodan.activo and estado_apis.shodan.configurada %}
                <span class="badge bg-success">Activa</span>
              {% elif estado_apis.shodan.configurada %}
                <span class="badge bg-warning text-dark">Configurada inactiva</span>
              {% else %}
                <span class="badge bg-secondary">No configurada</span>
              {% endif %}
            </div>

            <div class="mb-3">
              <strong>Key:</strong> {{ estado_apis.shodan.mask }}
            </div>

            <form method="POST">
              <input type="hidden" name="proveedor" value="shodan">

              <div class="mb-3">
                <label class="form-label fw-bold">Nueva API Key</label>
                <input type="password" name="api_key" class="form-control" placeholder="Pegar API Key Shodan">
              </div>

              <div class="form-check form-switch mb-3">
                <input class="form-check-input" type="checkbox" name="activo" id="activo_shodan"
                       {% if estado_apis.shodan.activo %}checked{% endif %}>
                <label class="form-check-label" for="activo_shodan">Activa</label>
              </div>

              <button class="btn btn-primary rounded-pill w-100">
                Guardar Shodan
              </button>
            </form>
          </div>
        </div>

      </div>

    </div>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            estado_apis=estado_apis
        ))
    )

# ============================================================
# ADMIN - PARÁMETROS SCORECARD PROPONENTES
# ============================================================

def init_scorecard_proponentes_parametros_db():
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

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

        ("darkweb_score_sin_hallazgos", 100, "Sin hallazgos de riesgo"),
        ("darkweb_score_bajo", 90, "Hallazgos de severidad Baja"),
        ("darkweb_score_medio", 75, "Hallazgos de severidad Media"),
        ("darkweb_score_alto", 55, "Hallazgos de severidad Alta"),
        ("darkweb_score_critico", 25, "Hallazgos de severidad Crítica"),
        ("darkweb_score_credenciales_confirmadas", 20, "Credenciales confirmadas"),

        ("dns_score_a_ok", 100, "Registro A/CNAME OK"),
        ("dns_score_a_no_detectado", 0, "Registro A/CNAME no detectado"),
        ("dns_score_mx_ok", 100, "MX OK"),
        ("dns_score_mx_no_detectado", 70, "MX no detectado"),
        ("dns_score_ns_ok", 100, "NS OK"),
        ("dns_score_ns_no_detectado", 0, "NS no detectado"),
        ("dns_score_spf_ok", 100, "SPF OK"),
        ("dns_score_spf_no_configurado", 0, "SPF no configurado"),
        ("dns_score_dmarc_ok", 100, "DMARC OK"),
        ("dns_score_dmarc_p_none", 70, "DMARC p=none"),
        ("dns_score_dmarc_no_configurado", 0, "DMARC no configurado"),
    ]

    for clave, valor, descripcion in parametros_default:
        cur.execute("""
            INSERT OR IGNORE INTO scorecard_parametros
            (clave, valor, descripcion)
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
    conn.close()


init_scorecard_proponentes_parametros_db()


def scorecard_proponentes_get_param(clave, default):
    try:
        conn = get_scorecard_proponentes_db_connection()
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

# ============================================================
# DNS HEALTH PARAMETRIZABLE - PROPONENTES
# ============================================================

def init_scorecard_proponentes_dns_params():
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    params = [
        ("dns_score_a_ok", 100, "DNS A/CNAME OK"),
        ("dns_score_a_no_detectado", 0, "DNS A/CNAME no detectado"),

        ("dns_score_mx_ok", 100, "MX OK"),
        ("dns_score_mx_no_detectado", 70, "MX no detectado"),

        ("dns_score_ns_ok", 100, "NS OK"),
        ("dns_score_ns_no_detectado", 0, "NS no detectado"),

        ("dns_score_spf_ok", 100, "SPF OK"),
        ("dns_score_spf_no_configurado", 0, "SPF no configurado"),

        ("dns_score_dmarc_ok", 100, "DMARC OK"),
        ("dns_score_dmarc_p_none", 70, "DMARC p=none"),
        ("dns_score_dmarc_no_configurado", 0, "DMARC no configurado"),
    ]

    for clave, valor, descripcion in params:
        cur.execute("""
            INSERT OR IGNORE INTO scorecard_parametros
            (clave, valor, descripcion)
            VALUES (?, ?, ?)
        """, (clave, valor, descripcion))

    conn.commit()
    conn.close()


init_scorecard_proponentes_dns_params()


def evaluar_dns_health_proponentes_scorecard(dominio):
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

    scores_componentes = []

    def add(control, estado, riesgo, puntaje, evidencia, recomendacion, regla):
        scores_componentes.append(float(puntaje or 0))
        findings.append({
            "categoria": "DNS Health",
            "herramienta": "DNS Resolver",
            "control": control,
            "estado": estado,
            "riesgo": riesgo,
            "severidad": riesgo,
            "score": puntaje,
            "evidencia": evidencia,
            "recomendacion": recomendacion,
            "detalle": {
                "regla_calculo": regla,
                "modelo_score": "DNS Health parametrizable por control: A/CNAME, MX, NS, SPF y DMARC."
            }
        })

    # Registro A / CNAME
    if registros_a:
        puntaje = scorecard_proponentes_get_param("dns_score_a_ok", 100)
        add(
            "Registro A",
            "OK",
            "Bajo",
            puntaje,
            f"{dominio_original}: " + ", ".join(registros_a[:8]),
            "Mantener monitoreo de resolución pública.",
            f"Registro A detectado → Score {puntaje}"
        )
    elif registros_cname:
        puntaje = scorecard_proponentes_get_param("dns_score_a_ok", 100)
        add(
            "Registro A/CNAME",
            "OK por CNAME",
            "Bajo",
            puntaje,
            f"{dominio_original} apunta por CNAME a: " + ", ".join(registros_cname[:8]),
            "Mantener monitoreo de resolución pública y destino CNAME autorizado.",
            f"Registro CNAME detectado → Score {puntaje}"
        )
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_a_no_detectado", 0)
        add(
            "Registro A",
            "No detectado",
            "Alto",
            puntaje,
            f"No se encontraron registros A ni CNAME para {dominio_original}.",
            "Validar publicación DNS del dominio o subdominio evaluado.",
            f"Registro A/CNAME no detectado → Score {puntaje}"
        )

    # MX
    if registros_mx:
        puntaje = scorecard_proponentes_get_param("dns_score_mx_ok", 100)
        add(
            "MX",
            "OK",
            "Bajo",
            puntaje,
            f"{dominio_base}: " + ", ".join(registros_mx[:8]),
            "Mantener proveedores MX autorizados.",
            f"MX detectado → Score {puntaje}"
        )
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_mx_no_detectado", 70)
        add(
            "MX",
            "No detectado en dominio base",
            "Bajo",
            puntaje,
            f"No se encontraron registros MX para {dominio_base}. Esto puede ser aceptable si el dominio no recibe correo.",
            "Confirmar si el proveedor usa este dominio para correo. Si lo usa, configurar MX.",
            f"MX no detectado → Score {puntaje}"
        )

    # NS
    if registros_ns:
        puntaje = scorecard_proponentes_get_param("dns_score_ns_ok", 100)
        add(
            "NS",
            "OK",
            "Bajo",
            puntaje,
            f"{dominio_base}: " + ", ".join(registros_ns[:8]),
            "Mantener gobierno sobre la administración DNS.",
            f"NS detectado → Score {puntaje}"
        )
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_ns_no_detectado", 0)
        add(
            "NS",
            "No detectado en dominio base",
            "Medio",
            puntaje,
            f"No se encontraron registros NS para {dominio_base}.",
            "Validar delegación DNS del dominio base.",
            f"NS no detectado → Score {puntaje}"
        )

    # SPF
    if spf_ok:
        puntaje = scorecard_proponentes_get_param("dns_score_spf_ok", 100)
        add(
            "SPF",
            "OK",
            "Bajo",
            puntaje,
            f"Se detectó registro SPF en {dominio_base}.",
            "Evitar configuraciones demasiado permisivas como +all.",
            f"SPF detectado → Score {puntaje}"
        )
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_spf_no_configurado", 0)
        add(
            "SPF",
            "No configurado en dominio base",
            "Alto",
            puntaje,
            f"No se encontró TXT con v=spf1 en {dominio_base}.",
            "Configurar SPF para mitigar spoofing si el dominio envía correo.",
            f"SPF no configurado → Score {puntaje}"
        )

    # DMARC
    if not dmarc_ok:
        puntaje = scorecard_proponentes_get_param("dns_score_dmarc_no_configurado", 0)
        add(
            "DMARC",
            "No configurado en dominio base",
            "Alto",
            puntaje,
            f"No se encontró _dmarc.{dominio_base}.",
            "Configurar DMARC con política gradual.",
            f"DMARC no configurado → Score {puntaje}"
        )
    elif dmarc_policy == "none":
        puntaje = scorecard_proponentes_get_param("dns_score_dmarc_p_none", 70)
        add(
            "DMARC",
            "Configurado p=none",
            "Medio",
            puntaje,
            f"DMARC existe en _dmarc.{dominio_base}, pero está en modo monitoreo.",
            "Avanzar gradualmente a quarantine o reject.",
            f"DMARC p=none → Score {puntaje}"
        )
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_dmarc_ok", 100)
        add(
            "DMARC",
            "OK",
            "Bajo",
            puntaje,
            f"Política DMARC en _dmarc.{dominio_base}: {dmarc_policy or 'definida'}.",
            "Mantener monitoreo DMARC.",
            f"DMARC enforce detectado → Score {puntaje}"
        )

    if scores_componentes:
        score = round(sum(scores_componentes) / len(scores_componentes), 2)
    else:
        score = 0

    return max(0, min(100, score)), findings

def scorecard_proponentes_risk_levels_activos():
    try:
        conn = get_scorecard_proponentes_db_connection()
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

def scorecard_proponentes_badge_color(nivel_nombre):
    try:
        conn = get_scorecard_proponentes_db_connection()
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



def nivel_riesgo_scorecard_proponentes(score):
    score = float(score or 0)
    niveles = scorecard_proponentes_risk_levels_activos()

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


def scorecard_proponentes_calcular_total(
    score_dns,
    score_ip,
    score_kali,
    score_incidentes,
    score_darkweb=100,
    incluir_kali=False
):
    """
    Calcula el score total de Proponentes.

    REGLA:
    - DNS siempre cuenta.
    - IP Reputation siempre cuenta.
    - Incidentes siempre cuenta.
    - Dark Web / Hacker Chatter siempre cuenta.
    - Kali Linux SOLO cuenta si realmente se ejecutó.
    """

    peso_dns = scorecard_proponentes_get_param("peso_dns", 20)
    peso_ip = scorecard_proponentes_get_param("peso_ip", 15)
    peso_kali = scorecard_proponentes_get_param("peso_kali", 35)
    peso_incidentes = scorecard_proponentes_get_param("peso_incidentes", 15)
    peso_darkweb = scorecard_proponentes_get_param("peso_darkweb", 15)

    componentes = [
        (float(score_dns if score_dns is not None else 0), peso_dns),
        (float(score_ip if score_ip is not None else 0), peso_ip),
        (float(score_incidentes if score_incidentes is not None else 100), peso_incidentes),
        (float(score_darkweb if score_darkweb is not None else 100), peso_darkweb),
    ]

    if incluir_kali:
        componentes.append((float(score_kali if score_kali is not None else 0), peso_kali))

    total_pesos = sum(peso for _, peso in componentes)

    if total_pesos <= 0:
        return 0

    total = sum(valor * peso for valor, peso in componentes) / total_pesos

    return round(max(0, min(100, total)), 2)

def scorecard_proponentes_score_hacker_chatter(
    total_hallazgos,
    credencial_confirmada=False,
    severidad_max="Bajo"
):
    """
    Alineado con Proveedores:
    - OSINT informativo / menciones públicas NO baja score.
    - Solo baja si hay credenciales confirmadas o severidad real Alta/Crítica.
    """

    total_hallazgos = int(total_hallazgos or 0)
    severidad_max = (severidad_max or "Bajo").strip()

    if credencial_confirmada:
        return scorecard_proponentes_get_param(
            "darkweb_score_credenciales_confirmadas",
            20
        ), "Crítico"

    if severidad_max in ["Crítico", "Critico"]:
        return 40, "Crítico"

    if severidad_max == "Alto":
        return 60, "Alto"

    # Menciones OSINT / GDELT / referencias públicas no confirmadas
    # no deben penalizar el score igual que una credencial real.
    return scorecard_proponentes_get_param(
        "darkweb_score_sin_hallazgos",
        100
    ), "Bajo"


def scorecard_proponentes_nivel_riesgo(score):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM scorecard_risk_levels
        WHERE activo = 1
        ORDER BY score_min DESC
    """)

    niveles = cur.fetchall()
    conn.close()

    for n in niveles:
        if score >= n["score_min"]:
            return n["nombre"]

    return "Crítico"

def scorecard_score_hacker_chatter_proponentes(total_hallazgos, credencial_confirmada=False, severidad_max="Bajo"):
    total_hallazgos = int(total_hallazgos or 0)

    if credencial_confirmada:
        return scorecard_proponentes_get_param("darkweb_score_credenciales_confirmadas", 20), "Crítico"

    if total_hallazgos <= 0:
        return scorecard_proponentes_get_param("darkweb_score_sin_hallazgos", 100), "Bajo"

    if total_hallazgos <= 2:
        base = scorecard_proponentes_get_param("darkweb_score_1_2", 80)
        riesgo = "Medio"
    elif total_hallazgos <= 5:
        base = scorecard_proponentes_get_param("darkweb_score_3_5", 60)
        riesgo = "Alto"
    else:
        base = scorecard_proponentes_get_param("darkweb_score_mas_5", 40)
        riesgo = "Crítico"

    if severidad_max == "Crítico":
        base = min(base, 35)
        riesgo = "Crítico"
    elif severidad_max == "Alto":
        base = min(base, 55)
        if riesgo in ["Bajo", "Medio"]:
            riesgo = "Alto"

    return max(0, min(100, float(base))), riesgo



@app.route("/proponentes/scorecard/parametros", methods=["GET", "POST"])
@login_required
def proponentes_scorecard_parametros():
    user, allowed, read_only = scorecard_proponentes_user_permiso()

    if not allowed:
        flash("No tiene permiso para parametrizar Scorecard de Proponentes.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no puede modificar parámetros.", "danger")
        return redirect(url_for("proponentes_scorecard_dashboard"))

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    parametros_base = [
        ("peso_dns", 20, "Peso DNS Health"),
        ("peso_ip", 15, "Peso IP Reputation"),
        ("peso_kali", 35, "Peso Kali Linux"),
        ("peso_incidentes", 15, "Peso Incidentes/Brechas"),
        ("peso_darkweb", 15, "Peso Dark Web / Exposure Intelligence"),

        ("darkweb_score_sin_hallazgos", 100, "Sin hallazgos de riesgo"),
        ("darkweb_score_bajo", 90, "Hallazgos de severidad Baja"),
        ("darkweb_score_medio", 75, "Hallazgos de severidad Media"),
        ("darkweb_score_alto", 55, "Hallazgos de severidad Alta"),
        ("darkweb_score_critico", 25, "Hallazgos de severidad Crítica"),
        ("darkweb_score_credenciales_confirmadas", 20, "Credenciales confirmadas"),

        ("dns_score_a_ok", 100, "Registro A/CNAME OK"),
        ("dns_score_a_no_detectado", 0, "Registro A/CNAME no detectado"),
        ("dns_score_mx_ok", 100, "MX OK"),
        ("dns_score_mx_no_detectado", 70, "MX no detectado"),
        ("dns_score_ns_ok", 100, "NS OK"),
        ("dns_score_ns_no_detectado", 0, "NS no detectado"),
        ("dns_score_spf_ok", 100, "SPF OK"),
        ("dns_score_spf_no_configurado", 0, "SPF no configurado"),
        ("dns_score_dmarc_ok", 100, "DMARC OK"),
        ("dns_score_dmarc_p_none", 70, "DMARC p=none"),
        ("dns_score_dmarc_no_configurado", 0, "DMARC no configurado"),
    ]

    for clave, valor, descripcion in parametros_base:
        cur.execute("""
            INSERT OR IGNORE INTO scorecard_parametros
            (clave, valor, descripcion)
            VALUES (?, ?, ?)
        """, (clave, valor, descripcion))

    conn.commit()

    descripciones = {clave: descripcion for clave, valor, descripcion in parametros_base}

    if request.method == "POST":
        accion = request.form.get("accion")

        if accion == "guardar_parametros":
            claves_numericas = [clave for clave, valor, descripcion in parametros_base]

            for clave in claves_numericas:
                valor = request.form.get(clave, type=float)

                if valor is None:
                    valor = scorecard_proponentes_get_param(clave, 0)

                cur.execute("""
                    INSERT INTO scorecard_parametros
                    (clave, valor, descripcion)
                    VALUES (?, ?, ?)
                    ON CONFLICT(clave) DO UPDATE SET
                        valor = excluded.valor,
                        descripcion = excluded.descripcion
                """, (
                    clave,
                    valor,
                    descripciones.get(clave, clave.replace("_", " ").title())
                ))

            conn.commit()

            try:
                registrar_log(
                    getattr(user, "username", "Sistema"),
                    "Actualizó parámetros generales del Scorecard de Proponentes"
                )
            except Exception:
                pass

            flash("Parámetros generales actualizados correctamente.", "success")
            conn.close()
            return redirect(url_for("proponentes_scorecard_parametros"))

        elif accion == "agregar_riesgo":
            nombre = (request.form.get("nombre_riesgo") or "").strip()
            score_min = request.form.get("score_min", type=float)
            color_bootstrap = (request.form.get("color_bootstrap") or "secondary").strip()
            orden = request.form.get("orden", type=int) or 0

            if not nombre:
                flash("Debe indicar el nombre del nivel de riesgo.", "danger")
                conn.close()
                return redirect(url_for("proponentes_scorecard_parametros"))

            if score_min is None:
                flash("Debe indicar el score mínimo del nivel de riesgo.", "danger")
                conn.close()
                return redirect(url_for("proponentes_scorecard_parametros"))

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

            try:
                registrar_log(
                    getattr(user, "username", "Sistema"),
                    f"Agregó nivel de riesgo Scorecard Proponentes: {nombre} desde {score_min}"
                )
            except Exception:
                pass

            flash("Nivel de riesgo agregado correctamente.", "success")
            conn.close()
            return redirect(url_for("proponentes_scorecard_parametros"))

        elif accion == "actualizar_riesgos":
            ids = request.form.getlist("risk_id")

            for risk_id in ids:
                nombre = (request.form.get(f"nombre_{risk_id}") or "").strip()
                score_min = request.form.get(f"score_min_{risk_id}", type=float)
                color_bootstrap = (request.form.get(f"color_{risk_id}") or "secondary").strip()
                orden = request.form.get(f"orden_{risk_id}", type=int) or 0
                activo = 1 if request.form.get(f"activo_{risk_id}") else 0

                if not nombre or score_min is None:
                    continue

                cur.execute("""
                    UPDATE scorecard_risk_levels
                    SET nombre = ?,
                        score_min = ?,
                        color_bootstrap = ?,
                        orden = ?,
                        activo = ?
                    WHERE id = ?
                """, (
                    nombre,
                    score_min,
                    color_bootstrap,
                    orden,
                    activo,
                    risk_id
                ))

            conn.commit()

            try:
                registrar_log(
                    getattr(user, "username", "Sistema"),
                    "Actualizó niveles de riesgo del Scorecard de Proponentes"
                )
            except Exception:
                pass

            flash("Niveles de riesgo actualizados correctamente.", "success")
            conn.close()
            return redirect(url_for("proponentes_scorecard_parametros"))

        elif accion == "eliminar_riesgo":
            risk_id = request.form.get("risk_id", type=int)

            if risk_id:
                cur.execute("DELETE FROM scorecard_risk_levels WHERE id = ?", (risk_id,))
                conn.commit()

                try:
                    registrar_log(
                        getattr(user, "username", "Sistema"),
                        f"Eliminó nivel de riesgo Scorecard Proponentes ID {risk_id}"
                    )
                except Exception:
                    pass

                flash("Nivel de riesgo eliminado correctamente.", "success")

            conn.close()
            return redirect(url_for("proponentes_scorecard_parametros"))

    parametros = {}

    cur.execute("SELECT * FROM scorecard_parametros")
    for row in cur.fetchall():
        parametros[row["clave"]] = row

    cur.execute("""
        SELECT *
        FROM scorecard_risk_levels
        ORDER BY score_min DESC, orden ASC, id ASC
    """)
    risk_levels = cur.fetchall()

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
        max-width:1450px;
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
        content:"SGSI · Parámetros Scorecard";
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

      .score-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
        padding:22px;
        margin-bottom:18px;
      }

      .section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }

      .param-help{
        font-size:.86rem;
        color:#607086;
        font-weight:700;
        line-height:1.45;
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
        text-align:center;
        padding:9px 8px;
      }

      .table td{
        vertical-align:middle !important;
        font-size:.82rem;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }
    </style>

    <div class="score-shell">

      <div class="score-header-card">
        <h1 class="score-header-text">Parámetros Scorecard de Terceros</h1>
      </div>

      <div class="d-flex justify-content-between align-items-center mb-3">
        <a href="{{ url_for('proponentes_scorecard_dashboard') }}" class="btn btn-light rounded-pill px-4">
          ⬅ Volver
        </a>
      </div>

      <div class="score-card">
        <h5 class="section-title">Parámetros generales de scoring</h5>

        <form method="POST">
          <input type="hidden" name="accion" value="guardar_parametros">

          <div class="row g-3">

            <div class="col-md-4">
              <label class="form-label fw-bold">Peso DNS Health</label>
              <input type="number" step="0.01" name="peso_dns" class="form-control"
                     value="{{ parametros.get('peso_dns').valor if parametros.get('peso_dns') else 20 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">Peso IP Reputation</label>
              <input type="number" step="0.01" name="peso_ip" class="form-control"
                     value="{{ parametros.get('peso_ip').valor if parametros.get('peso_ip') else 15 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">Peso Kali Linux</label>
              <input type="number" step="0.01" name="peso_kali" class="form-control"
                     value="{{ parametros.get('peso_kali').valor if parametros.get('peso_kali') else 35 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">Peso Incidentes / Brechas</label>
              <input type="number" step="0.01" name="peso_incidentes" class="form-control"
                     value="{{ parametros.get('peso_incidentes').valor if parametros.get('peso_incidentes') else 15 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">Peso Dark Web / Exposure Intelligence</label>
              <input type="number" step="0.01" name="peso_darkweb" class="form-control"
                     value="{{ parametros.get('peso_darkweb').valor if parametros.get('peso_darkweb') else 15 }}">
            </div>

          </div>

          <hr>

          <h6 class="fw-bold text-primary">
            Scoring DNS Health
          </h6>

          <div class="param-help mb-3">
            Configuración de scoring por control DNS: A/CNAME, MX, NS, SPF y DMARC.
          </div>

          <div class="row g-3 mt-1">

            <div class="col-md-4">
              <label class="form-label fw-bold">Registro A/CNAME OK</label>
              <input type="number" step="0.01" name="dns_score_a_ok" class="form-control"
                     value="{{ parametros.get('dns_score_a_ok').valor if parametros.get('dns_score_a_ok') else 100 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">Registro A/CNAME No Detectado</label>
              <input type="number" step="0.01" name="dns_score_a_no_detectado" class="form-control"
                     value="{{ parametros.get('dns_score_a_no_detectado').valor if parametros.get('dns_score_a_no_detectado') else 0 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">MX OK</label>
              <input type="number" step="0.01" name="dns_score_mx_ok" class="form-control"
                     value="{{ parametros.get('dns_score_mx_ok').valor if parametros.get('dns_score_mx_ok') else 100 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">MX No Detectado</label>
              <input type="number" step="0.01" name="dns_score_mx_no_detectado" class="form-control"
                     value="{{ parametros.get('dns_score_mx_no_detectado').valor if parametros.get('dns_score_mx_no_detectado') else 70 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">NS OK</label>
              <input type="number" step="0.01" name="dns_score_ns_ok" class="form-control"
                     value="{{ parametros.get('dns_score_ns_ok').valor if parametros.get('dns_score_ns_ok') else 100 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">NS No Detectado</label>
              <input type="number" step="0.01" name="dns_score_ns_no_detectado" class="form-control"
                     value="{{ parametros.get('dns_score_ns_no_detectado').valor if parametros.get('dns_score_ns_no_detectado') else 0 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">SPF OK</label>
              <input type="number" step="0.01" name="dns_score_spf_ok" class="form-control"
                     value="{{ parametros.get('dns_score_spf_ok').valor if parametros.get('dns_score_spf_ok') else 100 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">SPF No Configurado</label>
              <input type="number" step="0.01" name="dns_score_spf_no_configurado" class="form-control"
                     value="{{ parametros.get('dns_score_spf_no_configurado').valor if parametros.get('dns_score_spf_no_configurado') else 0 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">DMARC OK</label>
              <input type="number" step="0.01" name="dns_score_dmarc_ok" class="form-control"
                     value="{{ parametros.get('dns_score_dmarc_ok').valor if parametros.get('dns_score_dmarc_ok') else 100 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">DMARC p=none</label>
              <input type="number" step="0.01" name="dns_score_dmarc_p_none" class="form-control"
                     value="{{ parametros.get('dns_score_dmarc_p_none').valor if parametros.get('dns_score_dmarc_p_none') else 70 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">DMARC No Configurado</label>
              <input type="number" step="0.01" name="dns_score_dmarc_no_configurado" class="form-control"
                     value="{{ parametros.get('dns_score_dmarc_no_configurado').valor if parametros.get('dns_score_dmarc_no_configurado') else 0 }}">
            </div>

          </div>

          <hr>

          <h6 class="fw-bold text-primary">
            Scoring Hacker Chatter / Exposure Intelligence por Severidad
          </h6>

          <div class="param-help mb-3">
            Este scoring se calcula por la severidad máxima detectada:
            Sin hallazgos, Bajo, Medio, Alto, Crítico o Credenciales confirmadas.
          </div>

          <div class="row g-3 mt-1">

            <div class="col-md-4">
              <label class="form-label fw-bold">Sin hallazgos de riesgo</label>
              <input type="number" step="0.01" name="darkweb_score_sin_hallazgos" class="form-control"
                     value="{{ parametros.get('darkweb_score_sin_hallazgos').valor if parametros.get('darkweb_score_sin_hallazgos') else 100 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">Severidad Baja</label>
              <input type="number" step="0.01" name="darkweb_score_bajo" class="form-control"
                     value="{{ parametros.get('darkweb_score_bajo').valor if parametros.get('darkweb_score_bajo') else 90 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">Severidad Media</label>
              <input type="number" step="0.01" name="darkweb_score_medio" class="form-control"
                     value="{{ parametros.get('darkweb_score_medio').valor if parametros.get('darkweb_score_medio') else 75 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">Severidad Alta</label>
              <input type="number" step="0.01" name="darkweb_score_alto" class="form-control"
                     value="{{ parametros.get('darkweb_score_alto').valor if parametros.get('darkweb_score_alto') else 55 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">Severidad Crítica</label>
              <input type="number" step="0.01" name="darkweb_score_critico" class="form-control"
                     value="{{ parametros.get('darkweb_score_critico').valor if parametros.get('darkweb_score_critico') else 25 }}">
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">Credenciales confirmadas</label>
              <input type="number" step="0.01" name="darkweb_score_credenciales_confirmadas" class="form-control"
                     value="{{ parametros.get('darkweb_score_credenciales_confirmadas').valor if parametros.get('darkweb_score_credenciales_confirmadas') else 20 }}">
            </div>

          </div>

          <div class="text-end mt-4">
            <button class="btn btn-primary rounded-pill px-4 fw-bold">
              💾 Guardar Parámetros
            </button>
          </div>
        </form>
      </div>

      <div class="score-card">
        <h5 class="section-title">Niveles de riesgo</h5>

        <form method="POST" class="mb-4">
          <input type="hidden" name="accion" value="agregar_riesgo">

          <div class="row g-3 align-items-end">
            <div class="col-md-3">
              <label class="form-label fw-bold">Nombre</label>
              <input type="text" name="nombre_riesgo" class="form-control" placeholder="Ej: Muy Alto">
            </div>

            <div class="col-md-3">
              <label class="form-label fw-bold">Score mínimo</label>
              <input type="number" step="0.01" name="score_min" class="form-control" placeholder="Ej: 30">
            </div>

            <div class="col-md-3">
              <label class="form-label fw-bold">Color Bootstrap</label>
              <select name="color_bootstrap" class="form-select">
                <option value="success">success</option>
                <option value="warning text-dark">warning text-dark</option>
                <option value="danger">danger</option>
                <option value="dark">dark</option>
                <option value="secondary">secondary</option>
                <option value="primary">primary</option>
                <option value="info text-dark">info text-dark</option>
              </select>
            </div>

            <div class="col-md-2">
              <label class="form-label fw-bold">Orden</label>
              <input type="number" name="orden" class="form-control" value="0">
            </div>

            <div class="col-md-1 d-grid">
              <button class="btn btn-success rounded-pill">+</button>
            </div>
          </div>
        </form>

        <form method="POST">
          <input type="hidden" name="accion" value="actualizar_riesgos">

          <div class="table-responsive">
            <table class="table table-hover align-middle">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre</th>
                  <th>Score mínimo</th>
                  <th>Color</th>
                  <th>Orden</th>
                  <th>Activo</th>
                  <th>Vista</th>
                  <th>Eliminar</th>
                </tr>
              </thead>

              <tbody>
                {% for n in risk_levels %}
                <tr>
                  <td>
                    {{ n.id }}
                    <input type="hidden" name="risk_id" value="{{ n.id }}">
                  </td>

                  <td>
                    <input type="text" name="nombre_{{ n.id }}" class="form-control" value="{{ n.nombre }}">
                  </td>

                  <td>
                    <input type="number" step="0.01" name="score_min_{{ n.id }}" class="form-control" value="{{ n.score_min }}">
                  </td>

                  <td>
                    <select name="color_{{ n.id }}" class="form-select">
                      {% for c in ['success','warning text-dark','danger','dark','secondary','primary','info text-dark'] %}
                        <option value="{{ c }}" {% if n.color_bootstrap == c %}selected{% endif %}>{{ c }}</option>
                      {% endfor %}
                    </select>
                  </td>

                  <td>
                    <input type="number" name="orden_{{ n.id }}" class="form-control" value="{{ n.orden or 0 }}">
                  </td>

                  <td class="text-center">
                    <input type="checkbox" name="activo_{{ n.id }}" {% if n.activo %}checked{% endif %}>
                  </td>

                  <td>
                    <span class="badge bg-{{ n.color_bootstrap }}">{{ n.nombre }}</span>
                  </td>

                  <td>
                    <button type="submit"
                            class="btn btn-sm btn-outline-danger rounded-pill"
                            formaction="{{ url_for('proponentes_scorecard_parametros') }}"
                            formmethod="POST"
                            name="accion"
                            value="eliminar_riesgo"
                            onclick="this.form.risk_id.value='{{ n.id }}'; return confirm('¿Eliminar este nivel de riesgo?');">
                      Eliminar
                    </button>
                  </td>
                </tr>
                {% else %}
                <tr>
                  <td colspan="8" class="text-center text-muted py-4">
                    No hay niveles de riesgo configurados.
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>

          <input type="hidden" name="risk_id" value="">

          <div class="text-end mt-3">
            <button class="btn btn-primary rounded-pill px-4 fw-bold">
              💾 Guardar Niveles de Riesgo
            </button>
          </div>
        </form>
      </div>

    </div>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            parametros=parametros,
            risk_levels=risk_levels
        ))
    )

# ========================================================================================================================================
#                                                   FIN DEL MÓDULO SECURITY SCORECARD 
# ========================================================================================================================================

# ========================================================================================================================================
#                                                   MÓDULO PESI - PLAN ESTRATÉGICO SI
# ========================================================================================================================================

# ============================================================
# DB INDEPENDIENTE PESI
# ============================================================

PESI_DB_PATH = os.path.join(app.instance_path, "pesi.db")


def get_pesi_db_connection():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(PESI_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_pesi_db():
    conn = get_pesi_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pesi_planes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entidad TEXT NOT NULL,
            anio TEXT,
            vigencia_inicio TEXT,
            vigencia_fin TEXT,

            version TEXT DEFAULT '1.0',
            fecha_version TEXT,
            modificacion TEXT,
            versiones_json TEXT,

            objetivo TEXT,
            objetivos_especificos TEXT,
            alcance TEXT,
            documentos_referencia TEXT,
            estado_actual TEXT,
            estrategia_seguridad TEXT,

            estrategias_json TEXT,
            portafolio_json TEXT,
            cronograma_json TEXT,
            presupuesto_json TEXT,

            responsables TEXT,

            elaboro_nombre TEXT,
            elaboro_cargo TEXT,
            reviso_nombre TEXT,
            reviso_cargo TEXT,
            aprobo_nombre TEXT,
            aprobo_cargo TEXT,
            fecha_aprobacion TEXT,

            creado_por TEXT,
            fecha_creacion TEXT,
            fecha_actualizacion TEXT
        )
    """)

    cur.execute("PRAGMA table_info(pesi_planes)")
    cols = [r[1] for r in cur.fetchall()]

    if "versiones_json" not in cols:
        cur.execute("ALTER TABLE pesi_planes ADD COLUMN versiones_json TEXT")

    conn.commit()
    conn.close()


init_pesi_db()


# ============================================================
# HELPERS PESI
# ============================================================

def _pesi_user_actual():
    try:
        return User.query.get(session.get("user_id"))
    except Exception:
        return None


def _pesi_permiso():
    user = _pesi_user_actual()

    if not user:
        flash("Debe iniciar sesión.", "danger")
        return None

    if user.role not in ("admin", "auditor") and not verificar_permiso(user, "PESI"):
        flash("No tiene permiso para acceder al módulo PESI.", "danger")
        return None

    return user


def _pesi_default_json():
    versiones = [
        {
            "version": "1.0",
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "modificacion": "Versión inicial del documento"
        }
    ]

    estrategias = [
        {
            "estrategia": "Liderazgo de seguridad de la información",
            "descripcion": "Asegurar que se establezca el Modelo de Seguridad y Privacidad de la Información (MSPI) mediante la aprobación de políticas, lineamientos, roles y responsabilidades."
        },
        {
            "estrategia": "Gestión de riesgos",
            "descripcion": "Determinar, valorar y tratar los riesgos de seguridad de la información mediante controles orientados a reducir efectos indeseados."
        },
        {
            "estrategia": "Concientización",
            "descripcion": "Fortalecer la cultura organizacional en seguridad de la información mediante sensibilización, formación y transferencia de conocimiento."
        },
        {
            "estrategia": "Implementación de controles",
            "descripcion": "Planificar e implementar controles administrativos, tecnológicos y operativos para proteger la información."
        },
        {
            "estrategia": "Gestión de incidentes",
            "descripcion": "Gestionar eventos e incidentes de seguridad de la información mediante identificación, análisis, comunicación, respuesta y mejora."
        }
    ]

    portafolio = [
        {
            "estrategia": "Liderazgo de seguridad de la información",
            "proyecto": "Desarrollar e implementar una política de seguridad de la información.",
            "producto": "Política de Seguridad formalizada e implementada."
        },
        {
            "estrategia": "Gestión de riesgos",
            "proyecto": "Identificar, valorar y clasificar los riesgos asociados a los activos de información.",
            "producto": "Matriz de riesgos de seguridad digital."
        },
        {
            "estrategia": "Concientización",
            "proyecto": "Realizar jornadas de sensibilización a todo el personal.",
            "producto": "Evidencias de sensibilización y resultados de medición."
        },
        {
            "estrategia": "Implementación de controles",
            "proyecto": "Implementar controles de seguridad priorizados.",
            "producto": "Controles implementados y evidenciados."
        },
        {
            "estrategia": "Gestión de incidentes",
            "proyecto": "Definir y formalizar el procedimiento de gestión de incidentes.",
            "producto": "Procedimiento de gestión de incidentes formalizado."
        }
    ]

    cronograma = [
        {
            "anio": "2026",
            "trimestre": "Trimestre 1",
            "actividad": "Realizar diagnóstico de seguridad y privacidad de la información.",
            "responsable": "Responsable de Seguridad Digital",
            "estado": "Planeado"
        }
    ]

    presupuesto = [
        {
            "anio": "2026",
            "proyecto": "Implementación de controles de seguridad priorizados.",
            "inversion": "$ 0"
        }
    ]

    return versiones, estrategias, portafolio, cronograma, presupuesto


def _pesi_json_load(txt, default):
    try:
        data = json.loads(txt or "")
        return data if isinstance(data, list) else default
    except Exception:
        return default


def _pesi_json_dump_from_form(prefix, campos):
    filas = []
    total = int(request.form.get(prefix + "_count") or 0)

    for i in range(total):
        row = {}
        vacia = True

        for campo in campos:
            val = (request.form.get(f"{prefix}_{campo}_{i}") or "").strip()
            row[campo] = val

            if val:
                vacia = False

        if not vacia:
            filas.append(row)

    return json.dumps(filas, ensure_ascii=False)


def _pesi_form_data():
    versiones_json = _pesi_json_dump_from_form(
        "versiones",
        ["version", "fecha", "modificacion"]
    )

    versiones = _pesi_json_load(versiones_json, [])
    primera_version = versiones[0] if versiones else {}

    return {
        "entidad": (request.form.get("entidad") or "").strip(),
        "anio": (request.form.get("anio") or "").strip(),
        "vigencia_inicio": (request.form.get("vigencia_inicio") or "").strip(),
        "vigencia_fin": (request.form.get("vigencia_fin") or "").strip(),

        "version": (primera_version.get("version") or "1.0").strip(),
        "fecha_version": (primera_version.get("fecha") or "").strip(),
        "modificacion": (primera_version.get("modificacion") or "").strip(),
        "versiones_json": versiones_json,

        "objetivo": (request.form.get("objetivo") or "").strip(),
        "objetivos_especificos": (request.form.get("objetivos_especificos") or "").strip(),
        "alcance": (request.form.get("alcance") or "").strip(),
        "documentos_referencia": (request.form.get("documentos_referencia") or "").strip(),
        "estado_actual": (request.form.get("estado_actual") or "").strip(),
        "estrategia_seguridad": (request.form.get("estrategia_seguridad") or "").strip(),

        "estrategias_json": _pesi_json_dump_from_form("estrategias", ["estrategia", "descripcion"]),
        "portafolio_json": _pesi_json_dump_from_form("portafolio", ["estrategia", "proyecto", "producto"]),
        "cronograma_json": _pesi_json_dump_from_form("cronograma", ["anio", "trimestre", "actividad", "responsable", "estado"]),
        "presupuesto_json": _pesi_json_dump_from_form("presupuesto", ["anio", "proyecto", "inversion"]),

        "responsables": (request.form.get("responsables") or "").strip(),

        "elaboro_nombre": (request.form.get("elaboro_nombre") or "").strip(),
        "elaboro_cargo": (request.form.get("elaboro_cargo") or "").strip(),
        "reviso_nombre": (request.form.get("reviso_nombre") or "").strip(),
        "reviso_cargo": (request.form.get("reviso_cargo") or "").strip(),
        "aprobo_nombre": (request.form.get("aprobo_nombre") or "").strip(),
        "aprobo_cargo": (request.form.get("aprobo_cargo") or "").strip(),
        "fecha_aprobacion": (request.form.get("fecha_aprobacion") or "").strip(),
    }


def _pesi_get_plan(plan_id):
    conn = get_pesi_db_connection()
    row = conn.execute("""
        SELECT *
        FROM pesi_planes
        WHERE id = ?
    """, (plan_id,)).fetchone()
    conn.close()

    if not row:
        abort(404)

    plan = dict(row)

    # Compatibilidad con planes ya creados antes de versiones_json
    if not plan.get("versiones_json"):
        plan["versiones_json"] = json.dumps([
            {
                "version": plan.get("version") or "1.0",
                "fecha": plan.get("fecha_version") or "",
                "modificacion": plan.get("modificacion") or "Versión inicial del documento"
            }
        ], ensure_ascii=False)

    return plan


def _pesi_insertar_desde_form(user):
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = _pesi_form_data()

    data["creado_por"] = getattr(user, "username", "Sistema")
    data["fecha_creacion"] = ahora
    data["fecha_actualizacion"] = ahora

    if not data["entidad"]:
        data["entidad"] = "Entidad sin nombre"

    conn = get_pesi_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO pesi_planes (
            entidad, anio, vigencia_inicio, vigencia_fin,
            version, fecha_version, modificacion, versiones_json,
            objetivo, objetivos_especificos, alcance, documentos_referencia,
            estado_actual, estrategia_seguridad,
            estrategias_json, portafolio_json, cronograma_json, presupuesto_json,
            responsables,
            elaboro_nombre, elaboro_cargo, reviso_nombre, reviso_cargo,
            aprobo_nombre, aprobo_cargo, fecha_aprobacion,
            creado_por, fecha_creacion, fecha_actualizacion
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["entidad"], data["anio"], data["vigencia_inicio"], data["vigencia_fin"],
        data["version"], data["fecha_version"], data["modificacion"], data["versiones_json"],
        data["objetivo"], data["objetivos_especificos"], data["alcance"], data["documentos_referencia"],
        data["estado_actual"], data["estrategia_seguridad"],
        data["estrategias_json"], data["portafolio_json"], data["cronograma_json"], data["presupuesto_json"],
        data["responsables"],
        data["elaboro_nombre"], data["elaboro_cargo"], data["reviso_nombre"], data["reviso_cargo"],
        data["aprobo_nombre"], data["aprobo_cargo"], data["fecha_aprobacion"],
        data["creado_por"], data["fecha_creacion"], data["fecha_actualizacion"]
    ))

    nuevo_id = cur.lastrowid
    conn.commit()
    conn.close()

    try:
        registrar_log(data["creado_por"], f"Creó PESI: {data['entidad']}")
    except Exception:
        pass

    return nuevo_id


def _pesi_actualizar_desde_form(plan_id, user):
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = _pesi_form_data()
    data["fecha_actualizacion"] = ahora

    if not data["entidad"]:
        data["entidad"] = "Entidad sin nombre"

    conn = get_pesi_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE pesi_planes
        SET
            entidad = ?,
            anio = ?,
            vigencia_inicio = ?,
            vigencia_fin = ?,

            version = ?,
            fecha_version = ?,
            modificacion = ?,
            versiones_json = ?,

            objetivo = ?,
            objetivos_especificos = ?,
            alcance = ?,
            documentos_referencia = ?,
            estado_actual = ?,
            estrategia_seguridad = ?,

            estrategias_json = ?,
            portafolio_json = ?,
            cronograma_json = ?,
            presupuesto_json = ?,

            responsables = ?,

            elaboro_nombre = ?,
            elaboro_cargo = ?,
            reviso_nombre = ?,
            reviso_cargo = ?,
            aprobo_nombre = ?,
            aprobo_cargo = ?,
            fecha_aprobacion = ?,

            fecha_actualizacion = ?
        WHERE id = ?
    """, (
        data["entidad"], data["anio"], data["vigencia_inicio"], data["vigencia_fin"],
        data["version"], data["fecha_version"], data["modificacion"], data["versiones_json"],
        data["objetivo"], data["objetivos_especificos"], data["alcance"], data["documentos_referencia"],
        data["estado_actual"], data["estrategia_seguridad"],
        data["estrategias_json"], data["portafolio_json"], data["cronograma_json"], data["presupuesto_json"],
        data["responsables"],
        data["elaboro_nombre"], data["elaboro_cargo"], data["reviso_nombre"], data["reviso_cargo"],
        data["aprobo_nombre"], data["aprobo_cargo"], data["fecha_aprobacion"],
        data["fecha_actualizacion"],
        plan_id
    ))

    conn.commit()
    conn.close()

    try:
        registrar_log(getattr(user, "username", "Sistema"), f"Actualizó PESI: {data['entidad']}")
    except Exception:
        pass


def _pesi_plan_default_dict(user):
    versiones, estrategias, portafolio, cronograma, presupuesto = _pesi_default_json()
    anio_actual = datetime.now().year

    return {
        "id": None,
        "entidad": "",
        "anio": str(anio_actual),
        "vigencia_inicio": str(anio_actual),
        "vigencia_fin": str(anio_actual + 1),

        "version": "1.0",
        "fecha_version": datetime.now().strftime("%Y-%m-%d"),
        "modificacion": "Versión inicial del documento",
        "versiones_json": json.dumps(versiones, ensure_ascii=False),

        "objetivo": "Fortalecer la integridad, confidencialidad y disponibilidad de los activos de información de la Entidad, para reducir los riesgos a los que está expuesta la organización hasta niveles aceptables, a partir de la implementación de las estrategias de seguridad digital definidas en este documento.",
        "objetivos_especificos": "Definir y establecer la estrategia de seguridad digital de la entidad.\nDefinir y establecer las necesidades de la entidad para la implementación del Sistema de Gestión de Seguridad de la Información.\nPriorizar los proyectos a implementar para la correcta implementación del SGSI.\nPlanificar la evaluación y seguimiento de los controles y lineamientos implementados.",
        "alcance": "El Plan Estratégico de Seguridad de la Información comparte el alcance definido dentro de la Política General de Seguridad de la Información y contempla los procesos de la entidad. Ajustar según el contexto de cada entidad.",
        "documentos_referencia": "Decreto 612 de 2018.\nResolución 500 de 2021.\nManual de Gobierno Digital – MINTIC.\nModelo de Seguridad y Privacidad de la Información – MINTIC.\nRelacionar otros documentos que el PESI tiene o toma como referencia.",
        "estado_actual": "Describir el estado actual de la entidad respecto a la implementación de los lineamientos de seguridad de la información requeridos por el MSPI. Esta sección permite establecer la línea base y proyectar el mejoramiento del SGSI.",
        "estrategia_seguridad": "La entidad establecerá una estrategia de seguridad digital integrando principios, políticas, procedimientos, guías, manuales, formatos y lineamientos para la gestión de la seguridad de la información, teniendo como premisa la implementación del Modelo de Seguridad y Privacidad de la Información - MSPI.",

        "estrategias_json": json.dumps(estrategias, ensure_ascii=False),
        "portafolio_json": json.dumps(portafolio, ensure_ascii=False),
        "cronograma_json": json.dumps(cronograma, ensure_ascii=False),
        "presupuesto_json": json.dumps(presupuesto, ensure_ascii=False),

        "responsables": "Representante Legal: Aprobar los documentos de alto nivel.\nResponsable de Seguridad Digital / CISO : Coordinar las actividades de implementación del MSPI.",

        "elaboro_nombre": "",
        "elaboro_cargo": "",
        "reviso_nombre": "",
        "reviso_cargo": "",
        "aprobo_nombre": "",
        "aprobo_cargo": "",
        "fecha_aprobacion": "",

        "creado_por": getattr(user, "username", "Sistema"),
        "fecha_creacion": "",
        "fecha_actualizacion": "",
    }


def _pesi_css():
    return """
    <style>
      body {
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .pesi-shell {
        width:96%;
        max-width:1500px;
        margin:26px auto 30px auto;
      }

      .pesi-header-card {
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

      .pesi-header-card::before {
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .pesi-header-overlay {
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

      .pesi-header-overlay::before {
        content:"🧭";
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

      .pesi-header-text {
        max-width:1100px;
        width:100%;
      }

      .pesi-header-text::before {
        content:"SGSI · Plan Estratégico de Seguridad de la Información";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .pesi-title {
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .pesi-subtitle {
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .pesi-card {
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .pesi-section {
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:18px;
        margin-bottom:16px;
        box-shadow:0 8px 18px rgba(15,23,42,.07);
      }

      .section-title {
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }

      .soft-table-wrap,
      .table-responsive {
        overflow-x:auto;
        background:#ffffff;
        border-radius:14px;
        border:1px solid #dbe6f4;
        box-shadow:0 12px 24px rgba(15,23,42,.10);
      }

      .pesi-index-table-wrap {
        max-height:72vh;
        overflow-y:auto;
      }

      .table {
        margin-bottom:0;
      }

      .table thead th {
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
      .table td {
        vertical-align:middle !important;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .table tbody tr:nth-child(even) {
        background:#f8fbff;
      }

      .table tbody tr:hover {
        background:#eef6ff;
      }

      .pesi-edit-table textarea {
        min-width:220px;
        min-height:82px;
      }

      .form-label {
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
      .form-select {
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }

      textarea.form-control {
        min-height:110px;
        resize:vertical;
      }

      .form-control:focus,
      .form-select:focus {
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }

      .approval-box {
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:8px 7px;
        background:#f8fbff;
        box-shadow:0 8px 18px rgba(15,23,42,.07);
        height:100%;
      }

      .approval-box h6 {
        font-weight:950;
        color:#0b4a8f;
        text-transform:uppercase;
        font-size:.82rem;
        margin-bottom:14px;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }

      .btn {
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .btn-primary {
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        border:none !important;
      }

      .btn-success {
        background:linear-gradient(135deg,#16803c,#22a55a) !important;
        border:none !important;
      }

      .btn-danger {
        background:linear-gradient(135deg,#b91c1c,#ef4444) !important;
        border:none !important;
      }

      .pesi-help {
        font-size:.78rem;
        color:#475569;
        margin-top:-8px;
        margin-bottom:12px;
      }

      @media (max-width:992px) {
        .pesi-shell {
          width:98%;
          margin:8px auto 22px auto;
        }

        .pesi-header-card {
          min-height:88px;
        }

        .pesi-title {
          font-size:1.20rem;
        }

        .pesi-subtitle {
          font-size:.68rem;
        }
      }

      @media (max-width:768px) {
        .pesi-header-overlay {
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .pesi-header-overlay::before {
          margin:0;
        }

        .pesi-header-text::before {
          margin-left:auto;
          margin-right:auto;
        }

        .pesi-title,
        .pesi-subtitle {
          text-align:center;
        }
      }
    </style>
    """


def _pesi_render_rows(prefix, rows, campos, labels, readonly=False):
    if not rows:
        rows = [{}]

    html_rows = ""

    for i, row in enumerate(rows):
        html_rows += "<tr>"

        for campo in campos:
            val = escape(row.get(campo, "") or "")
            ro = "readonly disabled" if readonly else ""

            html_rows += f"""
            <td>
              <textarea class="form-control form-control-sm" rows="3" name="{prefix}_{campo}_{i}" {ro}>{val}</textarea>
            </td>
            """

        if not readonly:
            html_rows += """
            <td class="text-center">
              <button type="button" class="btn btn-sm btn-outline-danger rounded-pill" onclick="pesiRemoveRow(this)">
                🗑️
              </button>
            </td>
            """

        html_rows += "</tr>"

    ths = "".join(f"<th>{escape(label)}</th>" for label in labels)

    if not readonly:
        ths += "<th>Acción</th>"

    add_btn = ""
    if not readonly:
        add_btn = f"""
        <button type="button" class="btn btn-sm btn-outline-primary rounded-pill mt-2"
                onclick="pesiAddRow('{prefix}')">
          ➕ Agregar fila
        </button>
        """

    return f"""
    <div class="table-responsive">
      <table class="table table-bordered align-middle pesi-edit-table">
        <thead>
          <tr>{ths}</tr>
        </thead>
        <tbody id="{prefix}_tbody">
          {html_rows}
        </tbody>
      </table>
    </div>

    <input type="hidden" id="{prefix}_count" name="{prefix}_count" value="{len(rows)}">

    {add_btn}
    """


# ============================================================
# RUTAS PESI
# ============================================================

@app.route("/pesi")
@login_required
def pesi_index():
    user = _pesi_permiso()

    if not user:
        return redirect(url_for("menu"))

    conn = get_pesi_db_connection()
    planes = conn.execute("""
        SELECT *
        FROM pesi_planes
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    planes = [dict(p) for p in planes]

    html = """
    <div class="pesi-shell">

      <div class="pesi-header-card">
        <div class="pesi-header-overlay">
          <div class="pesi-header-text">
            <h3 class="pesi-title">PESI — Plan Estratégico de Seguridad de la Información</h3>
            <div class="pesi-subtitle">
              Gobierno / Dirección · Plantilla diligenciable y exportable a PDF
            </div>
          </div>
        </div>
      </div>

      <div class="pesi-card p-4">

        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
          <div>
            <div class="section-title">Planes PESI registrados</div>
            <div class="text-muted small">Desde aquí puedes ver, editar, imprimir o eliminar planes PESI según permisos.</div>
          </div>

          {% if user.role != 'auditor' %}
          <a href="{{ url_for('pesi_nuevo') }}" class="btn btn-primary rounded-pill px-4">
            ➕ Nuevo PESI
          </a>
          {% endif %}
        </div>

        <div class="table-responsive soft-table-wrap pesi-index-table-wrap">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>ID</th>
                <th>Entidad</th>
                <th>Año</th>
                <th>Versión</th>
                <th>Fecha creación</th>
                <th class="text-center">Acciones</th>
              </tr>
            </thead>

            <tbody>
              {% for p in planes %}
              <tr>
                <td>{{ p.id }}</td>
                <td>{{ p.entidad }}</td>
                <td>{{ p.anio or '—' }}</td>
                <td>{{ p.version or '1.0' }}</td>
                <td>{{ p.fecha_creacion or '—' }}</td>
                <td class="text-center">
                  <div class="d-flex justify-content-center gap-2 flex-wrap">

                    <a class="btn btn-sm btn-outline-secondary rounded-pill" href="{{ url_for('pesi_ver', plan_id=p.id) }}">
                      Ver
                    </a>

                    {% if user.role != 'auditor' %}
                    <a class="btn btn-sm btn-outline-primary rounded-pill" href="{{ url_for('pesi_editar', plan_id=p.id) }}">
                      Editar
                    </a>
                    {% endif %}

                    <a class="btn btn-sm btn-danger rounded-pill" data-no-progress="true" href="{{ url_for('pesi_pdf', plan_id=p.id) }}">
                      PDF
                    </a>

                    {% if user.role != 'auditor' %}
                    <form method="POST"
                          action="{{ url_for('pesi_eliminar', plan_id=p.id) }}"
                          class="d-inline"
                          data-no-progress="true"
                          onsubmit="return confirm('¿Seguro que deseas eliminar este PESI? Esta acción no se puede deshacer.');">
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
                <td colspan="6" class="text-center text-muted py-4">
                  No hay planes PESI registrados.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>

      </div>
    </div>
    """

    html += _pesi_css()

    return render_template_string(
        BASE,
        content=Markup(render_template_string(html, planes=planes, user=user))
    )


@app.route("/pesi/nuevo", methods=["GET", "POST"])
@login_required
def pesi_nuevo():
    user = _pesi_permiso()

    if not user:
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El rol auditor solo puede consultar e imprimir PESI.", "warning")
        return redirect(url_for("pesi_index"))

    if request.method == "POST":
        nuevo_id = _pesi_insertar_desde_form(user)
        flash("PESI creado correctamente.", "success")
        return redirect(url_for("pesi_editar", plan_id=nuevo_id))

    plan = _pesi_plan_default_dict(user)
    return _pesi_render_form(plan, user, modo="nuevo")


@app.route("/pesi/<int:plan_id>/ver")
@login_required
def pesi_ver(plan_id):
    user = _pesi_permiso()

    if not user:
        return redirect(url_for("menu"))

    plan = _pesi_get_plan(plan_id)
    return _pesi_render_form(plan, user, modo="ver")


@app.route("/pesi/<int:plan_id>/editar", methods=["GET", "POST"])
@login_required
def pesi_editar(plan_id):
    user = _pesi_permiso()

    if not user:
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El rol auditor no puede editar el PESI.", "warning")
        return redirect(url_for("pesi_ver", plan_id=plan_id))

    plan = _pesi_get_plan(plan_id)

    if request.method == "POST":
        _pesi_actualizar_desde_form(plan_id, user)
        flash("PESI actualizado correctamente.", "success")
        return redirect(url_for("pesi_editar", plan_id=plan_id))

    return _pesi_render_form(plan, user, modo="editar")


@app.route("/pesi/<int:plan_id>/eliminar", methods=["POST"])
@login_required
def pesi_eliminar(plan_id):
    user = _pesi_permiso()

    if not user:
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El rol auditor no puede eliminar planes PESI.", "warning")
        return redirect(url_for("pesi_index"))

    plan = _pesi_get_plan(plan_id)

    conn = get_pesi_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM pesi_planes WHERE id = ?", (plan_id,))
    conn.commit()
    conn.close()

    try:
        registrar_log(getattr(user, "username", "Sistema"), f"Eliminó PESI: {plan.get('entidad')}")
    except Exception:
        pass

    flash("PESI eliminado correctamente.", "success")
    return redirect(url_for("pesi_index"))


# ============================================================
# FORMULARIO PESI
# ============================================================

def _pesi_render_form(plan, user, modo="editar"):
    readonly = (modo == "ver") or (user.role == "auditor")
    ro = "readonly disabled" if readonly else ""
    disabled_submit = "d-none" if readonly else ""

    versiones_default, estrategias_default, portafolio_default, cronograma_default, presupuesto_default = _pesi_default_json()

    versiones_rows = _pesi_json_load(plan.get("versiones_json"), versiones_default)
    estrategias_rows = _pesi_json_load(plan.get("estrategias_json"), estrategias_default)
    portafolio_rows = _pesi_json_load(plan.get("portafolio_json"), portafolio_default)
    cronograma_rows = _pesi_json_load(plan.get("cronograma_json"), cronograma_default)
    presupuesto_rows = _pesi_json_load(plan.get("presupuesto_json"), presupuesto_default)

    versiones_html = _pesi_render_rows(
        "versiones",
        versiones_rows,
        ["version", "fecha", "modificacion"],
        ["Versión", "Fecha", "Modificación"],
        readonly
    )

    estrategias_html = _pesi_render_rows(
        "estrategias",
        estrategias_rows,
        ["estrategia", "descripcion"],
        ["Estrategia / Eje", "Descripción / Objetivo"],
        readonly
    )

    portafolio_html = _pesi_render_rows(
        "portafolio",
        portafolio_rows,
        ["estrategia", "proyecto", "producto"],
        ["Estrategia / Eje", "Proyecto", "Productos esperados"],
        readonly
    )

    cronograma_html = _pesi_render_rows(
        "cronograma",
        cronograma_rows,
        ["anio", "trimestre", "actividad", "responsable", "estado"],
        ["Año", "Trimestre", "Actividad / Proyecto", "Responsable", "Estado"],
        readonly
    )

    presupuesto_html = _pesi_render_rows(
        "presupuesto",
        presupuesto_rows,
        ["anio", "proyecto", "inversion"],
        ["Año", "Proyecto", "Inversión"],
        readonly
    )

    back_url = url_for("pesi_index")

    titulo_modo = {
        "nuevo": "Nuevo PESI",
        "editar": "Editar PESI",
        "ver": "Ver PESI"
    }.get(modo, "PESI")

    pdf_button = ""

    if plan.get("id"):
        pdf_button = f"""
        <a href="{url_for('pesi_pdf', plan_id=plan.get('id'))}" data-no-progress="true" class="btn btn-danger rounded-pill px-4">
          📄 Generar PDF
        </a>
        """

    html = f"""
    <div class="pesi-shell">

      <div class="pesi-header-card">
        <div class="pesi-header-overlay">
          <div class="pesi-header-text">
            <h3 class="pesi-title">PESI — Plan Estratégico de Seguridad de la Información</h3>
            <div class="pesi-subtitle">
              {titulo_modo} · Gobierno / Dirección · Exportación PDF
            </div>
          </div>
        </div>
      </div>

      <form method="POST" class="pesi-card p-4">

        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-4">
          <div>
            <div class="section-title">{titulo_modo}</div>
            <div class="text-muted small">
              {"Consulta en solo lectura." if readonly else "Diligencia los campos y agrega las filas necesarias en cada tabla."}
            </div>
          </div>

          <div class="d-flex gap-2 flex-wrap">
            <a href="{back_url}" class="btn btn-outline-secondary rounded-pill px-4">
              Volver
            </a>

            {pdf_button}

            <button type="submit" class="btn btn-success rounded-pill px-4 {disabled_submit}">
              💾 Guardar PESI
            </button>
          </div>
        </div>

        <div class="row g-3 mb-4">
          <div class="col-md-6">
            <label class="form-label">Nombre de la entidad</label>
            <input class="form-control" name="entidad" value="{escape(plan.get('entidad') or '')}" {ro} required>
          </div>

          <div class="col-md-2">
            <label class="form-label">Año</label>
            <input class="form-control" name="anio" value="{escape(plan.get('anio') or '')}" {ro}>
          </div>

          <div class="col-md-2">
            <label class="form-label">Vigencia inicio</label>
            <input class="form-control" name="vigencia_inicio" value="{escape(plan.get('vigencia_inicio') or '')}" {ro}>
          </div>

          <div class="col-md-2">
            <label class="form-label">Vigencia fin</label>
            <input class="form-control" name="vigencia_fin" value="{escape(plan.get('vigencia_fin') or '')}" {ro}>
          </div>
        </div>

        <div class="pesi-section">
          <div class="section-title">Control de versiones</div>
          <div class="pesi-help">Agrega una fila por cada versión o modificación del documento.</div>
          {versiones_html}
        </div>

        <div class="pesi-section">
          <div class="section-title">1. Objetivo</div>
          <textarea class="form-control" rows="5" name="objetivo" {ro}>{escape(plan.get('objetivo') or '')}</textarea>
        </div>

        <div class="pesi-section">
          <div class="section-title">1.1 Objetivos específicos</div>
          <textarea class="form-control" rows="6" name="objetivos_especificos" {ro}>{escape(plan.get('objetivos_especificos') or '')}</textarea>
        </div>

        <div class="pesi-section">
          <div class="section-title">2. Alcance</div>
          <textarea class="form-control" rows="5" name="alcance" {ro}>{escape(plan.get('alcance') or '')}</textarea>
        </div>

        <div class="pesi-section">
          <div class="section-title">3. Documentos de referencia</div>
          <textarea class="form-control" rows="6" name="documentos_referencia" {ro}>{escape(plan.get('documentos_referencia') or '')}</textarea>
        </div>

        <div class="pesi-section">
          <div class="section-title">4. Estado actual de la entidad respecto al SGSI</div>
          <textarea class="form-control" rows="7" name="estado_actual" {ro}>{escape(plan.get('estado_actual') or '')}</textarea>
        </div>

        <div class="pesi-section">
          <div class="section-title">5. Estrategia de seguridad digital</div>
          <textarea class="form-control" rows="6" name="estrategia_seguridad" {ro}>{escape(plan.get('estrategia_seguridad') or '')}</textarea>
        </div>

        <div class="pesi-section">
          <div class="section-title">5.1 Descripción de las estrategias específicas / ejes</div>
          <div class="pesi-help">Agrega las estrategias necesarias según el PESI de la entidad.</div>
          {estrategias_html}
        </div>

        <div class="pesi-section">
          <div class="section-title">5.2 Portafolio de proyectos / actividades</div>
          <div class="pesi-help">Agrega proyectos, actividades y productos esperados.</div>
          {portafolio_html}
        </div>

        <div class="pesi-section">
          <div class="section-title">5.3 Cronograma de actividades / proyectos</div>
          <div class="pesi-help">Agrega las actividades por año, trimestre, responsable y estado.</div>
          {cronograma_html}
        </div>

        <div class="pesi-section">
          <div class="section-title">5.4 Análisis presupuestal</div>
          <div class="pesi-help">Agrega cada proyecto con su inversión estimada.</div>
          {presupuesto_html}
        </div>

        <div class="pesi-section">
          <div class="section-title">6. Responsables</div>
          <textarea class="form-control" rows="7" name="responsables" {ro}>{escape(plan.get('responsables') or '')}</textarea>
        </div>

        <div class="pesi-section">
          <div class="section-title">7. Aprobación</div>

          <div class="row g-3">
            <div class="col-md-4">
              <div class="approval-box">
                <h6>Elaboró</h6>

                <label class="form-label">Nombre</label>
                <input class="form-control mb-2" name="elaboro_nombre" value="{escape(plan.get('elaboro_nombre') or '')}" {ro}>

                <label class="form-label">Cargo</label>
                <input class="form-control" name="elaboro_cargo" value="{escape(plan.get('elaboro_cargo') or '')}" {ro}>
              </div>
            </div>

            <div class="col-md-4">
              <div class="approval-box">
                <h6>Revisó</h6>

                <label class="form-label">Nombre</label>
                <input class="form-control mb-2" name="reviso_nombre" value="{escape(plan.get('reviso_nombre') or '')}" {ro}>

                <label class="form-label">Cargo</label>
                <input class="form-control" name="reviso_cargo" value="{escape(plan.get('reviso_cargo') or '')}" {ro}>
              </div>
            </div>

            <div class="col-md-4">
              <div class="approval-box">
                <h6>Aprobó</h6>

                <label class="form-label">Nombre</label>
                <input class="form-control mb-2" name="aprobo_nombre" value="{escape(plan.get('aprobo_nombre') or '')}" {ro}>

                <label class="form-label">Cargo</label>
                <input class="form-control mb-2" name="aprobo_cargo" value="{escape(plan.get('aprobo_cargo') or '')}" {ro}>

                <label class="form-label">Fecha</label>
                <input class="form-control" type="date" name="fecha_aprobacion" value="{escape(plan.get('fecha_aprobacion') or '')}" {ro}>
              </div>
            </div>
          </div>
        </div>

        <div class="text-center mt-4">
          <button type="submit" class="btn btn-success rounded-pill px-5 {disabled_submit}">
            💾 Guardar PESI
          </button>
        </div>

      </form>
    </div>

    <script>
      const PESI_TABLES = {{
        versiones: {{
          fields: ["version", "fecha", "modificacion"]
        }},
        estrategias: {{
          fields: ["estrategia", "descripcion"]
        }},
        portafolio: {{
          fields: ["estrategia", "proyecto", "producto"]
        }},
        cronograma: {{
          fields: ["anio", "trimestre", "actividad", "responsable", "estado"]
        }},
        presupuesto: {{
          fields: ["anio", "proyecto", "inversion"]
        }}
      }};

      function pesiAddRow(prefix) {{
        const cfg = PESI_TABLES[prefix];
        if (!cfg) return;

        const tbody = document.getElementById(prefix + "_tbody");
        const countInput = document.getElementById(prefix + "_count");

        if (!tbody || !countInput) return;

        let idx = parseInt(countInput.value || "0");
        let tr = document.createElement("tr");

        cfg.fields.forEach(function(field) {{
          let td = document.createElement("td");
          td.innerHTML = '<textarea class="form-control form-control-sm" rows="3" name="' + prefix + '_' + field + '_' + idx + '"></textarea>';
          tr.appendChild(td);
        }});

        let tdAction = document.createElement("td");
        tdAction.className = "text-center";
        tdAction.innerHTML = '<button type="button" class="btn btn-sm btn-outline-danger rounded-pill" onclick="pesiRemoveRow(this)">🗑️</button>';
        tr.appendChild(tdAction);

        tbody.appendChild(tr);
        countInput.value = idx + 1;
      }}

      function pesiRemoveRow(btn) {{
        const tr = btn.closest("tr");
        const tbody = tr ? tr.parentElement : null;

        if (!tr || !tbody) return;

        if (tbody.querySelectorAll("tr").length <= 1) {{
          tr.querySelectorAll("textarea").forEach(function(t) {{ t.value = ""; }});
          return;
        }}

        tr.remove();
      }}
    </script>
    """

    html += _pesi_css()

    return render_template_string(
        BASE,
        content=Markup(render_template_string(html, plan=plan, user=user))
    )


# ============================================================
# PDF PESI
# ============================================================

