@app.route('/modelamiento_amenazas/no_mapeados/<int:id>/delete')
@app.route('/vulnerabilidades/threat_model/unmapped/<int:id>/delete')
@login_required
def threat_model_unmapped_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros.", "danger")
        return redirect(url_for('threat_model_unmapped_view'))

    if user.role != 'admin' and not verificar_permiso(user, "Modelamiento de Amenazas"):
        flash("No tiene permiso para eliminar hallazgos no mapeados.", "danger")
        return redirect(url_for('threat_model_unmapped_view'))

    item = ThreatModelUnmapped.query.get_or_404(id)

    try:
        db.session.delete(item)
        db.session.commit()
        flash("Hallazgo no mapeado eliminado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"No fue posible eliminar el hallazgo no mapeado: {str(e)}", "danger")

    return redirect(url_for('threat_model_unmapped_view'))


# ==========================
# Eliminar por filtros — No Mapeados MITRE
# ==========================

@app.route('/modelamiento_amenazas/no_mapeados/delete_filtrados', methods=['POST'])
@app.route('/vulnerabilidades/threat_model/unmapped/delete_filtrados', methods=['POST'])
@login_required
def threat_model_unmapped_delete_filtrados():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros.", "danger")
        return redirect(url_for('threat_model_unmapped_view'))

    if user.role != 'admin' and not verificar_permiso(user, "Modelamiento de Amenazas"):
        flash("No tiene permiso para eliminar hallazgos no mapeados.", "danger")
        return redirect(url_for('threat_model_unmapped_view'))

    filtro_herramienta = (request.form.get('herramienta') or '').strip()
    filtro_severidad = (request.form.get('severidad') or '').strip()
    filtro_texto = (request.form.get('texto') or '').strip()

    q = ThreatModelUnmapped.query

    if filtro_herramienta:
        q = q.filter(ThreatModelUnmapped.herramienta == filtro_herramienta)

    if filtro_severidad:
        q = q.filter(ThreatModelUnmapped.severidad == filtro_severidad)

    if filtro_texto:
        q = q.filter(
            db.or_(
                ThreatModelUnmapped.titulo.ilike(f"%{filtro_texto}%"),
                ThreatModelUnmapped.descripcion.ilike(f"%{filtro_texto}%"),
                ThreatModelUnmapped.evidencia.ilike(f"%{filtro_texto}%")
            )
        )

    registros = q.all()

    if not registros:
        flash("No se encontraron hallazgos no mapeados con los filtros aplicados.", "warning")
        return redirect(url_for(
            'threat_model_unmapped_view',
            herramienta=filtro_herramienta,
            severidad=filtro_severidad,
            texto=filtro_texto
        ))

    try:
        total = len(registros)

        for item in registros:
            db.session.delete(item)

        db.session.commit()
        flash(f"Se eliminaron {total} hallazgos no mapeados correctamente.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"No fue posible eliminar los hallazgos no mapeados filtrados: {str(e)}", "danger")

    return redirect(url_for('threat_model_unmapped_view'))

@app.route('/modelamiento_amenazas/no_mapeados/clasificar', methods=['POST'])
@login_required
def threat_model_unmapped_classify():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede generar clasificaciones complementarias.", "danger")
        return redirect(url_for('threat_model_unmapped_view'))

    if user.role != 'admin' and not verificar_permiso(user, "Modelamiento de Amenazas"):
        flash("No tiene permiso para clasificar hallazgos no mapeados.", "danger")
        return redirect(url_for('menu'))

    filtro_herramienta = (request.form.get('herramienta') or '').strip()
    filtro_severidad = (request.form.get('severidad') or '').strip()
    filtro_texto = (request.form.get('texto') or '').strip()

    q = ThreatModelUnmapped.query

    if filtro_herramienta:
        q = q.filter(ThreatModelUnmapped.herramienta == filtro_herramienta)

    if filtro_severidad:
        q = q.filter(ThreatModelUnmapped.severidad == filtro_severidad)

    if filtro_texto:
        q = q.filter(
            db.or_(
                ThreatModelUnmapped.titulo.ilike(f"%{filtro_texto}%"),
                ThreatModelUnmapped.descripcion.ilike(f"%{filtro_texto}%"),
                ThreatModelUnmapped.evidencia.ilike(f"%{filtro_texto}%")
            )
        )

    registros = q.order_by(ThreatModelUnmapped.id.desc()).all()

    if not registros:
        flash("No hay hallazgos no mapeados para clasificar con los filtros aplicados.", "warning")
        return redirect(url_for(
            'threat_model_unmapped_view',
            herramienta=filtro_herramienta,
            severidad=filtro_severidad,
            texto=filtro_texto
        ))

    try:
        total = 0

        for item in registros:
            guardar_clasificacion_complementaria_unmapped(item)
            total += 1

        db.session.commit()

        flash(
            f"Se generó clasificación complementaria para {total} hallazgo(s) no mapeado(s).",
            "success"
        )

    except Exception as e:
        db.session.rollback()
        flash(f"No fue posible generar la clasificación complementaria: {str(e)}", "danger")

    return redirect(url_for(
        'threat_model_unmapped_complementary_view',
        herramienta=filtro_herramienta,
        severidad=filtro_severidad,
        texto=filtro_texto
    ))


@app.route('/modelamiento_amenazas/no_mapeados/clasificacion_complementaria')
@login_required
def threat_model_unmapped_complementary_view():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Modelamiento de Amenazas"):
        flash("No tiene permiso para acceder a la clasificación complementaria.", "danger")
        return redirect(url_for('menu'))

    read_only = True if user.role == 'auditor' else False

    filtro_herramienta = (request.args.get('herramienta') or '').strip()
    filtro_severidad = (request.args.get('severidad') or '').strip()
    filtro_texto = (request.args.get('texto') or '').strip()

    q = ThreatModelUnmapped.query.options(
        selectinload(ThreatModelUnmapped.clasificacion_complementaria)
    )

    if filtro_herramienta:
        q = q.filter(ThreatModelUnmapped.herramienta == filtro_herramienta)

    if filtro_severidad:
        q = q.filter(ThreatModelUnmapped.severidad == filtro_severidad)

    if filtro_texto:
        q = q.filter(
            db.or_(
                ThreatModelUnmapped.titulo.ilike(f"%{filtro_texto}%"),
                ThreatModelUnmapped.descripcion.ilike(f"%{filtro_texto}%"),
                ThreatModelUnmapped.evidencia.ilike(f"%{filtro_texto}%")
            )
        )

    items = q.order_by(ThreatModelUnmapped.id.desc()).all()

    body = """
    <div class="glass-card p-4 mt-2">

      <div class="unmapped-topbar">
        <div>
          <div class="section-title mb-1">🧩 Clasificación complementaria de No Mapeados MITRE</div>
          <div class="text-muted small">
            Clasificación técnica y ejecutiva contra OWASP, CWE, CAPEC, ISO 27001 y NIST CSF 2.0.
          </div>
        </div>

        <div class="unmapped-extra-actions">
          <a href="{{ url_for('threat_model_unmapped_view') }}"
             class="btn btn-outline-secondary rounded-pill px-4">
            ← Volver a No Mapeados
          </a>

          <a href="{{ url_for('threat_model_dashboard') }}"
             class="btn btn-outline-primary rounded-pill px-4">
            ← Dashboard
          </a>
        </div>
      </div>

      <form method="get" class="row g-3 mb-3">
        <div class="col-md-3">
          <label class="form-label">Herramienta</label>
          <select name="herramienta" class="form-select">
            <option value="">-- Todas --</option>
            {% for op in ['registro_vulnerabilidades','nikto','nessus','nuclei','nmap','testssl','owasp_zap','zap'] %}
              <option value="{{ op }}" {% if filtro_herramienta == op %}selected{% endif %}>
                {{ op|upper }}
              </option>
            {% endfor %}
          </select>
        </div>

        <div class="col-md-3">
          <label class="form-label">Severidad</label>
          <select name="severidad" class="form-select">
            <option value="">-- Todas --</option>
            {% for op in ['Crítica', 'Alta', 'Media', 'Baja'] %}
              <option value="{{ op }}" {% if filtro_severidad == op %}selected{% endif %}>
                {{ op }}
              </option>
            {% endfor %}
          </select>
        </div>

        <div class="col-md-4">
          <label class="form-label">Texto</label>
          <input type="text"
                 name="texto"
                 class="form-control"
                 value="{{ filtro_texto }}"
                 placeholder="Buscar palabra o patrón...">
        </div>

        <div class="col-md-2">
          <label class="form-label d-block">&nbsp;</label>
          <div class="unmapped-filter-actions">
            <button class="btn btn-primary rounded-pill px-3" type="submit">
              Filtrar
            </button>

            <a href="{{ url_for('threat_model_unmapped_complementary_view') }}"
               class="btn btn-outline-secondary rounded-pill px-3">
              Limpiar
            </a>
          </div>
        </div>
      </form>

      <div class="soft-table-wrap">
        <div class="table-responsive px-3 pb-3 pt-3">
          <table class="table table-hover align-middle soft-table mb-0">

            <colgroup>
              <col class="col-id">
              <col class="col-hallazgo">
              <col class="col-severidad">
              <col class="col-owasp">
              <col class="col-cwe">
              <col class="col-capec">
              <col class="col-iso">
              <col class="col-nist">
              <col class="col-confianza">
              <col class="col-recomendacion">
            </colgroup>

            <thead>
              <tr>
                <th>ID</th>
                <th>Hallazgo</th>
                <th>Severidad</th>
                <th>OWASP</th>
                <th>CWE</th>
                <th>CAPEC</th>
                <th>ISO 27001</th>
                <th>NIST CSF</th>
                <th>Confianza</th>
                <th>Recomendación</th>
              </tr>
            </thead>

            <tbody>
              {% for it in items %}
                {% set c = it.clasificacion_complementaria %}
                <tr>
                  <td class="text-center fw-bold">{{ it.id }}</td>

                  <td class="small">
                    <b>{{ it.titulo }}</b>
                    <div class="text-muted mt-1">{{ it.herramienta|upper }}</div>
                  </td>

                  <td class="text-center">
                    {{ badge_severidad_html(it.severidad) }}
                  </td>

                  <td class="small">
                    {{ c.owasp_category if c else 'Pendiente' }}
                  </td>

                  <td class="small">
                    {% if c %}
                      <b>{{ c.cwe_id }}</b><br>{{ c.cwe_name }}
                    {% else %}
                      Pendiente
                    {% endif %}
                  </td>

                  <td class="small">
                    {% if c %}
                      <b>{{ c.capec_id }}</b><br>{{ c.capec_name }}
                    {% else %}
                      Pendiente
                    {% endif %}
                  </td>

                  <td class="small">
                    {% if c %}
                      <b>{{ c.iso_control }}</b><br>{{ c.iso_control_name }}
                    {% else %}
                      Pendiente
                    {% endif %}
                  </td>

                  <td class="small">
                    {% if c %}
                      <b>{{ c.nist_function }}</b><br>{{ c.nist_category }}
                    {% else %}
                      Pendiente
                    {% endif %}
                  </td>

                  <td class="text-center fw-bold">
                    {{ c.confianza if c else '—' }}{% if c %}%{% endif %}
                  </td>

                  <td class="small recommend-cell">
                    {% if c %}
                      {{ c.recomendacion }}
                      <details class="mt-2">
                        <summary>Ver razón</summary>
                        <div class="text-muted mt-1">{{ c.rationale }}</div>
                      </details>
                    {% else %}
                      <span class="text-muted">Sin clasificar.</span>
                    {% endif %}
                  </td>
                </tr>

              {% else %}
                <tr>
                  <td colspan="10" class="text-center text-muted py-4">
                    No hay hallazgos no mapeados para mostrar.
                  </td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <style>
      body a.btn{
        visibility:visible;
      }

      body a.btn[href="#"],
      body a.btn[href=""],
      body a.btn[onclick*="matriz"],
      body a.btn[href*="matriz_mitre"],
      body a.btn[href*="/modelamiento_amenazas/matriz_mitre"]{
        display:none !important;
      }

      .vuln-scan-shell > .text-center > a.btn,
      .vuln-scan-shell > div.text-center > a.btn,
      .threat-shell > .text-center > a.btn{
        display:none !important;
      }

      .unmapped-topbar{
        display:flex;
        justify-content:space-between;
        align-items:flex-start;
        gap:14px;
        flex-wrap:wrap;
        margin-bottom:18px;
        padding-bottom:14px;
        border-bottom:1px solid rgba(15,23,42,.08);
      }

      .unmapped-extra-actions{
        display:flex;
        flex-wrap:wrap;
        justify-content:flex-end;
        gap:6px;
      }

      .unmapped-extra-actions .btn{
        font-size:.82rem;
        font-weight:900;
        min-height:32px;
        border-radius:999px !important;
        padding:0 18px !important;
        display:flex;
        align-items:center;
        justify-content:center;
        white-space:nowrap;
        box-shadow:0 8px 18px rgba(37,99,235,.12);
        transition:all .18s ease;
      }

      .unmapped-extra-actions .btn:hover{
        transform:translateY(-1px);
      }

      .unmapped-filter-actions{
        display:flex;
        flex-direction:column;
        gap:7px;
        align-items:stretch;
      }

      .unmapped-filter-actions .btn{
        width:100%;
        min-height:36px;
        font-size:.68rem;
        font-weight:900;
        border-radius:999px !important;
      }

      .soft-table-wrap{
        border-radius:18px;
        overflow:hidden;
        border:1px solid rgba(15,23,42,.08);
        background:#ffffff;
        box-shadow:0 8px 24px rgba(15,23,42,.05);
      }

      .soft-table{
        width:100%;
        min-width:1420px;
        table-layout:fixed;
        margin-bottom:0 !important;
      }

      .col-id{ width:64px; }
      .col-hallazgo{ width:170px; }
      .col-severidad{ width:110px; }
      .col-owasp{ width:170px; }
      .col-cwe{ width:160px; }
      .col-capec{ width:160px; }
      .col-iso{ width:150px; }
      .col-nist{ width:160px; }
      .col-confianza{ width:110px; }
      .col-recomendacion{ width:366px; }

      .soft-table thead th{
        background:linear-gradient(135deg,#1d4ed8,#2563eb);
        color:#ffffff;
        font-weight:900;
        font-size:.68rem;
        text-align:center;
        border:none !important;
        padding:13px 8px;
        vertical-align:middle;
        white-space:normal;
        line-height:1.15;
      }

      .soft-table tbody td{
        vertical-align:top;
        padding:13px 9px;
        border-color:#eef2f7 !important;
        font-size:.80rem;
        line-height:1.35;
        overflow-wrap:break-word;
        word-break:normal;
      }

      .soft-table tbody tr:hover{
        background:#f8fbff;
      }

      .recommend-cell{
        white-space:normal !important;
        word-break:normal !important;
        overflow-wrap:break-word !important;
        line-height:1.5 !important;
        color:#334155;
      }

      .recommend-cell details{
        margin-top:10px;
      }

      .recommend-cell summary{
        font-size:.72rem;
        font-weight:900;
      }

      .soft-table .badge{
        font-size:.68rem;
        font-weight:900;
        border-radius:999px;
        padding:6px 10px;
        white-space:nowrap;
      }

      .soft-table details{
        cursor:pointer;
      }

      .soft-table summary{
        font-size:.72rem;
        font-weight:800;
        color:#2563eb;
        outline:none;
      }

      .soft-table summary:hover{
        color:#1d4ed8;
      }

      .form-control,
      .form-select{
        border-radius:14px !important;
        min-height:44px;
        border:1px solid #dbe4f0;
        box-shadow:none !important;
        font-size:.84rem;
        font-weight:600;
      }

      .form-control:focus,
      .form-select:focus{
        border-color:#3b82f6;
        box-shadow:0 0 0 .15rem rgba(59,130,246,.12) !important;
      }

      .section-title{
        font-size:1.1rem;
        font-weight:900;
        color:#0b4a8f;
      }

      @media (max-width:992px){
        .soft-table{
          min-width:1320px;
        }

        .col-id{ width:58px; }
        .col-hallazgo{ width:155px; }
        .col-severidad{ width:100px; }
        .col-owasp{ width:150px; }
        .col-cwe{ width:145px; }
        .col-capec{ width:145px; }
        .col-iso{ width:135px; }
        .col-nist{ width:145px; }
        .col-confianza{ width:100px; }
        .col-recomendacion{ width:342px; }

        .soft-table thead th{
          font-size:.70rem;
          padding:11px 7px;
        }

        .soft-table tbody td{
          font-size:.74rem;
          padding:10px 7px;
        }
      }

      @media (max-width:768px){
        .unmapped-topbar{
          flex-direction:column;
          align-items:stretch;
        }

        .unmapped-extra-actions{
          width:100%;
          flex-direction:column;
        }

        .unmapped-extra-actions .btn,
        .unmapped-filter-actions .btn{
          width:100%;
        }

        .soft-table-wrap{
          overflow-x:auto;
        }
      }
    </style>

    <script>
      document.addEventListener('DOMContentLoaded', function(){

        const elementos = document.querySelectorAll('a, button');

        elementos.forEach(function(el){
          const texto = (el.innerText || el.textContent || '').trim().toLowerCase();

          if(
            texto.includes('volver a la matriz') ||
            texto.includes('⬅ volver a la matriz') ||
            texto.includes('↩ volver a la matriz')
          ){
            el.remove();
          }
        });

      });
    </script>
    """

    return vuln_scan_shell(
        "Clasificación complementaria No Mapeados",
        render_template_string(
            body,
            items=items,
            filtro_herramienta=filtro_herramienta,
            filtro_severidad=filtro_severidad,
            filtro_texto=filtro_texto,
            read_only=read_only,
            badge_severidad_html=badge_severidad_html
        )
    )

# ==========================================================================================================================================
#                                                       Fin del Módulo de Amenazas
# ==========================================================================================================================================


# ==========================================================================================================================================
#                                                               Módulo Plan de Remediación
# ==========================================================================================================================================

def _build_fernet():
    digest = hashlib.sha256(JIRA_CRYPTO_SECRET.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)

def jira_encrypt_token(token: str) -> str:
    if not token:
        return ""
    f = _build_fernet()
    return f.encrypt(token.encode("utf-8")).decode("utf-8")

def jira_decrypt_token(token_enc: str) -> str:
    if not token_enc:
        return ""
    f = _build_fernet()
    return f.decrypt(token_enc.encode("utf-8")).decode("utf-8")

def get_jira_config() -> JiraConfig:
    cfg = JiraConfig.query.first()
    if not cfg:
        cfg = JiraConfig(
            enabled=False,
            base_url="",
            email="",
            project_key="SGSI",
            issue_type="Task",
            api_token_enc=""
        )
        db.session.add(cfg)
        db.session.commit()
    return cfg

def jira_get_runtime_config():
    cfg = get_jira_config()

    if not cfg.enabled:
        raise RuntimeError("La integración con Jira está deshabilitada.")

    if not cfg.base_url or not cfg.email or not cfg.project_key or not cfg.issue_type:
        raise RuntimeError("La configuración Jira está incompleta.")

    token = jira_decrypt_token(cfg.api_token_enc or "")
    if not token:
        raise RuntimeError("No hay API token Jira configurado.")

    return {
        "base_url": cfg.base_url.rstrip("/"),
        "email": cfg.email.strip(),
        "token": token,
        "project_key": cfg.project_key.strip(),
        "issue_type": cfg.issue_type.strip(),
    }

def jira_headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

def jira_auth():
    cfg = jira_get_runtime_config()
    return HTTPBasicAuth(cfg["email"], cfg["token"])

def jira_buscar_usuarios_asignables(query_text=""):
    """
    Consulta los usuarios que Jira permite asignar al proyecto configurado.

    IMPORTANTE:
    - Si query_text está vacío, Jira devuelve todos los usuarios asignables.
    - maxResults evita que la lista quede limitada al valor pequeño por defecto.
    """
    cfg = jira_get_runtime_config()

    url = f"{cfg['base_url']}/rest/api/3/user/assignable/search"
    params = {
        "project": cfg["project_key"],
        "query": (query_text or "").strip(),
        "startAt": 0,
        "maxResults": 1000
    }

    resp = requests.get(
        url,
        headers=jira_headers(),
        auth=jira_auth(),
        params=params,
        timeout=25
    )

    if resp.status_code >= 300:
        raise RuntimeError(f"Error buscando usuarios Jira: {resp.status_code} - {resp.text}")

    data = resp.json() or []
    if not isinstance(data, list):
        raise RuntimeError("Jira respondió con un formato inesperado al consultar usuarios asignables.")

    return data


def jira_normalizar_usuario_asignable(usuario):
    """Convierte un usuario retornado por Jira en una estructura simple."""
    if not usuario:
        return {
            "accountId": "",
            "displayName": ""
        }

    return {
        "accountId": usuario.get("accountId") or "",
        "displayName": usuario.get("displayName") or usuario.get("emailAddress") or usuario.get("accountId") or ""
    }


def jira_resolver_nombre_usuario(account_id: str, query_text: str = "") -> str:
    """Obtiene el nombre visible de un usuario Jira a partir del accountId."""
    if not account_id:
        return ""

    try:
        # Primero intenta con el texto sugerido y, si no aparece, consulta la lista completa.
        consultas = []
        query_limpia = (query_text or "").strip()
        if query_limpia:
            consultas.append(query_limpia)
        consultas.append("")

        for consulta in consultas:
            usuarios = jira_buscar_usuarios_asignables(consulta)
            for usuario in usuarios:
                if usuario.get("accountId") == account_id:
                    return usuario.get("displayName") or usuario.get("emailAddress") or account_id
    except Exception:
        pass

    return ""


def cargar_usuarios_jira_para_formulario(query_text: str = ""):
    """
    Carga TODOS los usuarios asignables de Jira para los formularios.

    Antes se enviaba el responsable SGSI como filtro. Cuando el responsable era,
    por ejemplo, "Administrador", Jira devolvía cero coincidencias y el selector
    aparecía vacío. Ahora se consulta siempre la lista completa y, cuando existe
    un texto de búsqueda, sus coincidencias se muestran primero sin ocultar a los
    demás usuarios asignables.
    """
    try:
        query_limpia = (query_text or "").strip()
        usuarios_combinados = []

        # Coincidencias sugeridas primero (si se recibió un responsable/nombre).
        if query_limpia:
            try:
                usuarios_combinados.extend(
                    jira_buscar_usuarios_asignables(query_limpia)
                )
            except Exception as e:
                print("ADVERTENCIA: No fue posible filtrar usuarios Jira:", e)

        # Siempre cargar la lista completa para que el selector nunca quede vacío
        # solamente porque el responsable SGSI no coincide con un usuario Jira.
        usuarios_combinados.extend(
            jira_buscar_usuarios_asignables("")
        )

        usuarios_normalizados = []
        account_ids_vistos = set()

        for usuario in usuarios_combinados:
            normalizado = jira_normalizar_usuario_asignable(usuario)
            account_id = (normalizado.get("accountId") or "").strip()

            if not account_id or account_id in account_ids_vistos:
                continue

            account_ids_vistos.add(account_id)
            usuarios_normalizados.append(normalizado)

        return usuarios_normalizados

    except Exception as e:
        print("ADVERTENCIA: No fue posible cargar usuarios Jira:", e)
        return []


def asignar_usuario_jira_a_plan(plan, account_id: str, assignee_name: str = ""):
    """
    Guarda en el plan el usuario Jira seleccionado para esa remediación.
    No usa un correo global de asignación; cada plan conserva su propio accountId.
    """
    if not plan:
        return

    account_id = (account_id or "").strip()
    assignee_name = (assignee_name or "").strip()

    plan.jira_account_id = account_id or None

    if account_id:
        plan.jira_assignee_name = assignee_name or jira_resolver_nombre_usuario(
            account_id,
            getattr(plan, "responsable", "") or ""
        ) or None
    else:
        plan.jira_assignee_name = None

def jira_crear_issue_plan(plan_id: int):
    cfg = jira_get_runtime_config()

    plan = PlanRemediacion.query.get_or_404(plan_id)
    vuln = VulnerabilidadRegistro.query.get_or_404(plan.vulnerabilidad_id)

    if plan.jira_issue_key:
        return {
            "already_exists": True,
            "issue_key": plan.jira_issue_key
        }

    summary = f"[{vuln.codigo or 'VULN'}] Remediación - {plan.prioridad or 'Media'}"
    description_adf = jira_adf_descripcion_plan(vuln, plan)

    payload = {
        "fields": {
            "project": {
                "key": cfg["project_key"]
            },
            "summary": summary[:255],
            "issuetype": {
                "name": cfg["issue_type"]
            },
            "description": description_adf
        }
    }

    # Fecha de remediación -> Due date estándar de Jira
    if plan.fecha_remediacion:
        payload["fields"]["duedate"] = plan.fecha_remediacion.strftime("%Y-%m-%d")

    # Asignación por cada punto de remediación.
    # NO se usa un correo global para todos los tickets.
    if plan.jira_account_id:
        payload["fields"]["assignee"] = {
            "accountId": plan.jira_account_id
        }

    url = f"{cfg['base_url']}/rest/api/3/issue"

    resp = requests.post(
        url,
        headers=jira_headers(),
        auth=jira_auth(),
        json=payload,
        timeout=30
    )

    if resp.status_code >= 300:
        raise RuntimeError(
            "Error creando issue Jira: "
            f"{resp.status_code} - {resp.text} | payload={json.dumps(payload, ensure_ascii=False)}"
        )

    data = resp.json()
    issue_key = data.get("key")
    issue_id = data.get("id")
    issue_url = f"{cfg['base_url']}/browse/{issue_key}" if issue_key else None

    plan.jira_issue_key = issue_key
    plan.jira_issue_id = issue_id
    plan.jira_issue_url = issue_url
    plan.jira_status = "Creado"

    if plan.jira_account_id and not plan.jira_assignee_name:
        plan.jira_assignee_name = jira_resolver_nombre_usuario(
            plan.jira_account_id,
            plan.responsable or ""
        ) or plan.jira_account_id

    plan.jira_synced_at = datetime.utcnow()

    db.session.commit()

    return {
        "already_exists": False,
        "issue_key": issue_key,
        "issue_id": issue_id,
        "issue_url": issue_url
    }

def jira_actualizar_issue_plan(plan_id: int):
    cfg = jira_get_runtime_config()

    plan = PlanRemediacion.query.get_or_404(plan_id)
    vuln = VulnerabilidadRegistro.query.get_or_404(plan.vulnerabilidad_id)

    if not plan.jira_issue_key:
        raise RuntimeError("El plan no tiene issue Jira asociado.")

    payload = {
        "fields": {
            "summary": f"[{vuln.codigo or 'VULN'}] Remediación - {plan.prioridad or 'Media'}"[:255],
            "description": jira_adf_descripcion_plan(vuln, plan)
        }
    }

    # Fecha de remediación del módulo -> Due date de Jira
    if plan.fecha_remediacion:
        payload["fields"]["duedate"] = plan.fecha_remediacion.strftime("%Y-%m-%d")
    else:
        payload["fields"]["duedate"] = None

    if plan.jira_account_id:
        payload["fields"]["assignee"] = {
            "accountId": plan.jira_account_id
        }
    else:
        payload["fields"]["assignee"] = None

    url = f"{cfg['base_url']}/rest/api/3/issue/{plan.jira_issue_key}"

    resp = requests.put(
        url,
        headers=jira_headers(),
        auth=jira_auth(),
        json=payload,
        timeout=30
    )

    if resp.status_code >= 300:
        raise RuntimeError(f"Error actualizando issue Jira: {resp.status_code} - {resp.text}")

    plan.jira_synced_at = datetime.utcnow()
    db.session.commit()

    return True

def jira_sync_plan(plan_id: int):
    cfg = jira_get_runtime_config()

    plan = PlanRemediacion.query.get_or_404(plan_id)
    if not plan.jira_issue_key:
        raise RuntimeError("El plan no tiene issue Jira asociado.")

    url = f"{cfg['base_url']}/rest/api/3/issue/{plan.jira_issue_key}"

    resp = requests.get(
        url,
        headers=jira_headers(),
        auth=jira_auth(),
        timeout=25
    )

    if resp.status_code >= 300:
        raise RuntimeError(f"Error consultando issue Jira: {resp.status_code} - {resp.text}")

    data = resp.json()
    fields = data.get("fields") or {}
    status_obj = fields.get("status") or {}
    assignee_obj = fields.get("assignee") or {}

    plan.jira_status = status_obj.get("name") or "—"
    plan.jira_assignee_name = assignee_obj.get("displayName") or plan.jira_assignee_name

    # Due date de Jira -> fecha_remediacion del módulo
    duedate = fields.get("duedate")
    if duedate:
        try:
            plan.fecha_remediacion = datetime.strptime(duedate, "%Y-%m-%d").date()
        except Exception:
            pass
    else:
        plan.fecha_remediacion = None

    plan.jira_synced_at = datetime.utcnow()

    sincronizar_vulnerabilidad_desde_plan(plan)

    db.session.commit()
    return plan.jira_status

def sincronizar_vulnerabilidad_desde_plan(plan: PlanRemediacion):
    if not plan or not plan.vulnerabilidad_id:
        return

    vuln = VulnerabilidadRegistro.query.get(plan.vulnerabilidad_id)
    if not vuln:
        return

    if (plan.estado or "").strip().lower() == "cerrado":
        vuln.estado = "Cerrado"
        vuln.fecha_cierre = plan.fecha_remediacion
    else:
        vuln.estado = "Abierto"
        vuln.fecha_cierre = None

    db.session.flush()
    
# ==========================
# ENTRADA DIRECTA — Plan de Remediación
# ==========================
@app.route('/plan_remediacion_menu')
@login_required
def plan_remediacion_menu():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Plan de Remediación"):
        flash("No tiene permiso para acceder al módulo de plan de remediación.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('plan_remediacion_matriz'))

@app.route('/plan_remediacion/ai_sugerir/<int:vuln_id>', methods=['GET'])
@login_required
def plan_remediacion_ai_sugerir(vuln_id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede generar acciones correctivas con IA.", "danger")
        return redirect(url_for('plan_remediacion_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Plan de Remediación"):
        flash("No tiene permiso para usar IA en plan de remediación.", "danger")
        return redirect(url_for('plan_remediacion_matriz'))

    vuln = VulnerabilidadRegistro.query.get_or_404(vuln_id)

    hallazgo = {
        "titulo": vuln.codigo or "Hallazgo sin código",
        "descripcion": vuln.descripcion_vulnerabilidad or "",
        "fuente": getattr(vuln, "fuente", "") or "",
        "severidad": getattr(vuln, "clasificacion", "") or "",
        "cve": getattr(vuln, "cve", "") or "",
        "cvss": str(getattr(vuln, "cvss", "") or ""),
        "puerto": getattr(vuln, "puerto", "") or "",
        "servicio": getattr(vuln, "servicio", "") or "",
        "evidencia": getattr(vuln, "observaciones", "") or "",
        "recomendacion_base": ""
    }

    sug = sugerir_remediacion_ai(hallazgo)
    print("DEBUG REMEDIACION SUGERIDA:", sug)

    flash("✅ Sugerencia de remediación generada con IA.", "success")
    return redirect(url_for(
        'plan_remediacion_new',
        vulnerabilidad_id=vuln.id,
        accion_correctiva_ai=sug.get("accion_correctiva", ""),
        prioridad_ai=sug.get("prioridad", ""),
        recursos_ai=sug.get("recursos_necesarios", ""),
        responsable_ai=(getattr(vuln, "responsable", "") or "")
    ))

# ==========================
# Agregar Remediación
# ==========================
@app.route('/plan_remediacion/new', methods=['GET', 'POST'])
@login_required
def plan_remediacion_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('plan_remediacion_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Plan de Remediación"):
        flash("No tiene permiso para agregar registro de plan de remediación.", "danger")
        return redirect(url_for('plan_remediacion_matriz'))

    vulnerabilidades = VulnerabilidadRegistro.query.order_by(
        VulnerabilidadRegistro.codigo.asc()
    ).all()

    jira_users = cargar_usuarios_jira_para_formulario()

    vuln_id_prefill = request.args.get('vulnerabilidad_id', type=int)
    accion_correctiva_ai = (request.args.get('accion_correctiva_ai') or '').strip()
    prioridad_ai = (request.args.get('prioridad_ai') or '').strip()
    recursos_ai = (request.args.get('recursos_ai') or '').strip()
    responsable_ai = (request.args.get('responsable_ai') or '').strip()

    if request.method == 'POST':
        vuln_id = request.form.get('vulnerabilidad_id', type=int)
        accion_correctiva = (request.form.get('accion_correctiva') or '').strip()
        responsable = (request.form.get('responsable') or '').strip()
        prioridad = (request.form.get('prioridad') or '').strip()
        recursos_necesarios = (request.form.get('recursos_necesarios') or '').strip()
        estado = (request.form.get('estado') or '').strip()
        fecha_objetivo_str = (request.form.get('fecha_objetivo') or '').strip()
        fecha_remediacion_str = (request.form.get('fecha_remediacion') or '').strip()
        jira_account_id = (request.form.get('jira_account_id') or '').strip()
        jira_assignee_name = (request.form.get('jira_assignee_name') or '').strip()

        fecha_objetivo = None
        if fecha_objetivo_str:
            try:
                fecha_objetivo = datetime.strptime(fecha_objetivo_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha objetivo inválida.", "danger")
                return redirect(url_for('plan_remediacion_new'))

        fecha_remediacion = None
        if fecha_remediacion_str:
            try:
                fecha_remediacion = datetime.strptime(fecha_remediacion_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de remediación inválida.", "danger")
                return redirect(url_for('plan_remediacion_new'))

        if not all([vuln_id, accion_correctiva, responsable, prioridad, estado]):
            flash("Campos obligatorios: ID Vulnerabilidad, Acción Correctiva, Responsable, Prioridad y Estado.", "danger")
            return redirect(url_for('plan_remediacion_new'))

        it = PlanRemediacion(
            vulnerabilidad_id=vuln_id,
            accion_correctiva=accion_correctiva,
            responsable=responsable,
            prioridad=prioridad,
            fecha_objetivo=fecha_objetivo,
            fecha_remediacion=fecha_remediacion,
            recursos_necesarios=recursos_necesarios,
            estado=estado
        )

        asignar_usuario_jira_a_plan(
            it,
            jira_account_id,
            jira_assignee_name
        )

        db.session.add(it)
        db.session.flush()

        sincronizar_vulnerabilidad_desde_plan(it)

        db.session.commit()
        flash("Plan de remediación registrado.", "success")
        return redirect(url_for('plan_remediacion_matriz'))

    html = """
    <div class="remadd-shell">

      <div class="remadd-header-card">
        <div class="remadd-header-overlay">
          <div class="remadd-header-text">
            <h3 class="remadd-title m-0">Agregar Plan de Remediación</h3>
            <div class="remadd-subtitle">
              Registro de acciones correctivas para mitigar vulnerabilidades identificadas, incluyendo responsables, prioridades, fechas y recursos necesarios
            </div>
          </div>
        </div>
      </div>

      <div class="remadd-header-actions">
        <a href="{{ url_for('plan_remediacion_matriz') }}"
           class="btn rounded-pill px-4 fw-bold remadd-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="remadd-card">
        <div class="remadd-card-body">

          <form method="post">
            <div class="row g-3">

              <div class="col-12">
                <div class="remadd-section-title">Información del plan de remediación</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">ID de Vulnerabilidad</label>
                <select name="vulnerabilidad_id" id="vulnerabilidad_id" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  {% for v in vulnerabilidades %}
                    <option value="{{ v.id }}" {% if vuln_id_prefill == v.id %}selected{% endif %}>
                      {{ v.codigo }} — {{ (v.descripcion_vulnerabilidad or '')[:60] }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Acción Correctiva</label>
                <textarea name="accion_correctiva" class="form-control" rows="2" required>{{ accion_correctiva_ai }}</textarea>
              </div>

              <div class="col-md-12">
                <div class="d-flex justify-content-center">
                  <button type="button"
                          class="btn btn-primary rounded-pill px-4 fw-bold"
                          onclick="generarAccionAI()">
                    🤖 Generar acción correctiva con IA
                  </button>
                </div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Responsable</label>
                <input name="responsable" class="form-control" value="{{ responsable_ai }}" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Prioridad</label>
                <select name="prioridad" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  <option value="Crítica" {% if prioridad_ai == 'Crítica' %}selected{% endif %}>Crítica</option>
                  <option value="Alta" {% if prioridad_ai == 'Alta' %}selected{% endif %}>Alta</option>
                  <option value="Media" {% if prioridad_ai == 'Media' %}selected{% endif %}>Media</option>
                  <option value="Baja" {% if prioridad_ai == 'Baja' %}selected{% endif %}>Baja</option>
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha Objetivo</label>
                <input type="date" name="fecha_objetivo" class="form-control">
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha de Remediación</label>
                <input type="date" name="fecha_remediacion" class="form-control">
              </div>

              <div class="col-md-12">
                <label class="form-label">Recursos Necesarios</label>
                <textarea name="recursos_necesarios" class="form-control" rows="2">{{ recursos_ai }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Estado</label>
                <select name="estado" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  <option value="Abierto">Abierto</option>
                  <option value="Cerrado">Cerrado</option>
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Asignado en Jira para esta remediación</label>
                <select name="jira_account_id" id="jira_account_id" class="form-select" onchange="actualizarNombreJira(this)">
                  <option value="">-- Sin asignar en Jira --</option>
                  {% for ju in jira_users %}
                    <option value="{{ ju.accountId }}" data-name="{{ ju.displayName }}">
                      {{ ju.displayName }}
                    </option>
                  {% endfor %}
                </select>
                <input type="hidden" name="jira_assignee_name" id="jira_assignee_name" value="">
                <div class="form-text">
                  Este usuario se usará solo para el ticket Jira de esta remediación.
                </div>
              </div>

            </div>

            <div class="remadd-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>

              <a href="{{ url_for('plan_remediacion_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold remadd-cancel-btn">
                Cancelar
              </a>
            </div>

          </form>

        </div>
      </div>
    </div>

    <script>
      function generarAccionAI() {
        const vulnId = document.getElementById('vulnerabilidad_id').value;
        if (!vulnId) {
          alert('Seleccione primero la vulnerabilidad.');
          return;
        }
        window.location.href = "/plan_remediacion/ai_sugerir/" + vulnId;
      }

      function actualizarNombreJira(select){
        const opt = select.options[select.selectedIndex];
        const hidden = document.getElementById('jira_assignee_name');
        if(hidden){
          hidden.value = opt ? (opt.getAttribute('data-name') || '') : '';
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

      .remadd-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      .remadd-header-card{
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

      .remadd-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .remadd-header-overlay{
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

      .remadd-header-overlay::before{
        content:"🛠️";
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

      .remadd-header-text{
        max-width:1100px;
        width:100%;
      }

      .remadd-header-text::before{
        content:"SGSI · Nueva Remediación";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .remadd-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .remadd-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .remadd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .remadd-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .remadd-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .remadd-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .remadd-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .remadd-card-body{
        padding:18px;
      }

      .remadd-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .remadd-card .form-control,
      .remadd-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .remadd-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .remadd-card .form-control:focus,
      .remadd-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .remadd-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .remadd-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
      }

      .remadd-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .remadd-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .remadd-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .remadd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .remadd-header-card{
          min-height:88px;
        }

        .remadd-title{
          font-size:1.20rem;
        }

        .remadd-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .remadd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .remadd-header-overlay::before{
          margin:0;
        }

        .remadd-header-actions .btn,
        .remadd-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        vulnerabilidades=vulnerabilidades,
        vuln_id_prefill=vuln_id_prefill,
        accion_correctiva_ai=accion_correctiva_ai,
        prioridad_ai=prioridad_ai,
        recursos_ai=recursos_ai,
        responsable_ai=responsable_ai,
        jira_users=jira_users
    )
    return render_template_string(BASE, content=Markup(inner))

# ==========================
# Matriz remediaciones
# ==========================
@app.route('/plan_remediacion_matriz', methods=['GET'])
@login_required
def plan_remediacion_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Plan de Remediación"):
            flash("No tiene permiso para ver los registros de plan de remediación.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    filtro_prioridad = (request.args.get('prioridad') or '').strip()
    filtro_estado = (request.args.get('estado') or '').strip()

    q = (
        PlanRemediacion.query
        .join(VulnerabilidadRegistro)
    )

    if filtro_prioridad:
        q = q.filter(PlanRemediacion.prioridad == filtro_prioridad)

    if filtro_estado:
        q = q.filter(PlanRemediacion.estado == filtro_estado)

    items = (
        q.add_entity(VulnerabilidadRegistro)
         .order_by(PlanRemediacion.id.desc())
         .all()
    )

    prioridad_choices = ["Crítica", "Alta", "Media", "Baja"]
    estado_choices = ["Abierto", "Cerrado"]

    html = """
    <div class="remmat-shell">

      <div class="remmat-header-card">
        <div class="remmat-header-overlay">
          <div class="remmat-header-text">
            <h3 class="remmat-title m-0">Plan de Remediación</h3>
            <div class="remmat-subtitle">
              Visualización resumida de acciones de remediación para vulnerabilidades identificadas
            </div>
          </div>
        </div>
      </div>

      <div class="remmat-header-actions">

        {% if not read_only %}
          <a href="{{ url_for('plan_remediacion_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            ➕ Agregar Plan de Remediación
          </a>

          <a href="{{ url_for('jira_config_view') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            🎫 Configuración Jira
          </a>
        {% else %}
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            ➕ Agregar Plan de Remediación
          </button>

          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            🎫 Configuración Jira
          </button>
        {% endif %}
      </div>

      <div class="remmat-filter-card">
        <div class="remmat-filter-body">

          <form method="get" id="remmatFiltroForm">
            <div class="row g-2 align-items-end">

              <div class="col-md-4">
                <label class="form-label fw-bold">Filtrar por Prioridad</label>
                <select name="prioridad" class="form-select rounded-3">
                  <option value="">-- Todas --</option>
                  {% for op in prioridad_choices %}
                    <option value="{{ op }}" {% if filtro_prioridad == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label fw-bold">Filtrar por Estado</label>
                <select name="estado" class="form-select rounded-3">
                  <option value="">-- Todos --</option>
                  {% for op in estado_choices %}
                    <option value="{{ op }}" {% if filtro_estado == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <div class="d-flex gap-2 flex-wrap remmat-filter-actions">
                  <button type="submit" class="btn btn-primary rounded-pill px-4 fw-bold">
                    Filtrar
                  </button>

                  <a href="{{ url_for('plan_remediacion_matriz') }}"
                     class="btn btn-secondary rounded-pill px-4 fw-bold">
                    Limpiar
                  </a>

                  {% if not read_only %}
                    <button type="button"
                            class="btn btn-danger rounded-pill px-4 fw-bold"
                            onclick="eliminarRemediacionesFiltradas()">
                      Eliminar filtrados
                    </button>
                  {% else %}
                    <button type="button"
                            class="btn btn-secondary rounded-pill px-4 fw-bold"
                            disabled
                            title="Auditor: solo lectura">
                      Eliminar filtrados
                    </button>
                  {% endif %}
                </div>
              </div>

            </div>
          </form>

          <form method="post"
                id="remmatDeleteFiltradosForm"
                action="{{ url_for('plan_remediacion_delete_filtrados') }}"
                style="display:none;">
            <input type="hidden" name="prioridad" value="{{ filtro_prioridad }}">
            <input type="hidden" name="estado" value="{{ filtro_estado }}">
          </form>

        </div>
      </div>

      <div class="remmat-card">
        <div class="remmat-topbar">
          <div>
            <h5 class="remmat-top-title mb-1">Resumen de remediaciones</h5>
            <div class="remmat-top-note">
              La matriz muestra los campos principales. Para consultar toda la información usa el botón <strong>Ver detalle</strong>.
            </div>
          </div>
          <div class="remmat-counter-badge">
            Total registros: {{ items|length }}
          </div>
        </div>

        <div class="remmat-card-body">
          <div class="remmat-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-hover align-middle remmat-table mb-0">
                <colgroup>
                  <col style="width: 10%;">
                  <col style="width: 28%;">
                  <col style="width: 14%;">
                  <col style="width: 14%;">
                  <col style="width: 12%;">
                  <col style="width: 12%;">
                  <col style="width: 10%;">
                  <col style="width: 22%;">
                </colgroup>

                <thead>
                  <tr>
                    <th>ID Vulnerabilidad</th>
                    <th>Acción correctiva</th>
                    <th>Responsable</th>
                    <th>Asignado Jira</th>
                    <th>Prioridad</th>
                    <th>Fecha objetivo</th>
                    <th>Estado</th>
                    <th class="remmat-col-acciones">Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  {% for pr, vul in items %}
                  <tr>

                    <td class="text-center">{{ vul.codigo or '—' }}</td>

                    <td class="remmat-cell-main">
                      <div class="remmat-main-text">{{ pr.accion_correctiva or '—' }}</div>
                    </td>

                    <td>{{ pr.responsable or '—' }}</td>

                    <td>{{ pr.jira_assignee_name or '—' }}</td>

                    <td class="text-center">
                      {% if pr.prioridad == 'Crítica' %}
                        <span class="badge bg-dark">Crítica</span>
                      {% elif pr.prioridad == 'Alta' %}
                        <span class="badge bg-danger">Alta</span>
                      {% elif pr.prioridad == 'Media' %}
                        <span class="badge bg-warning text-dark">Media</span>
                      {% elif pr.prioridad == 'Baja' %}
                        <span class="badge bg-success">Baja</span>
                      {% else %}
                        <span class="badge bg-secondary">{{ pr.prioridad or '—' }}</span>
                      {% endif %}
                    </td>

                    <td class="text-center">{{ pr.fecha_objetivo or '—' }}</td>

                    <td class="text-center">
                      {% if pr.estado == 'Abierto' %}
                        <span class="badge bg-primary">Abierto</span>
                      {% elif pr.estado == 'Cerrado' %}
                        <span class="badge bg-success">Cerrado</span>
                      {% else %}
                        <span class="badge bg-secondary">{{ pr.estado or '—' }}</span>
                      {% endif %}
                    </td>

                    <td class="text-center remmat-col-acciones">
                      <div class="remmat-actions-wrap">

                        <a href="{{ url_for('plan_remediacion_detalle', id=pr.id) }}"
                           class="btn btn-info btn-sm rounded-pill remmat-btn-action text-white fw-bold">
                           Ver detalle
                        </a>

                        {% if not read_only %}
                          <a href="{{ url_for('plan_remediacion_edit', id=pr.id) }}"
                             class="btn btn-warning btn-sm rounded-pill remmat-btn-action fw-bold">
                             Editar
                          </a>

                          <a href="{{ url_for('plan_remediacion_delete', id=pr.id) }}"
                             class="btn btn-danger btn-sm rounded-pill remmat-btn-action fw-bold"
                             onclick="return confirm('¿Eliminar este plan de remediación?');">
                             Eliminar
                          </a>

                          {% if pr.jira_issue_key %}
                            <a href="{{ pr.jira_issue_url }}"
                               class="btn btn-dark btn-sm rounded-pill remmat-btn-action fw-bold"
                               target="_blank">
                               Abrir Jira
                            </a>

                            <a href="{{ url_for('plan_remediacion_jira_sync', id=pr.id) }}"
                               class="btn btn-primary btn-sm rounded-pill remmat-btn-action fw-bold">
                               Sync Jira
                            </a>
                          {% else %}
                            <a href="{{ url_for('plan_remediacion_jira', id=pr.id) }}"
                               class="btn btn-primary btn-sm rounded-pill remmat-btn-action fw-bold">
                               Jira
                            </a>
                          {% endif %}
                        {% else %}
                          <span class="badge bg-secondary">Solo lectura</span>
                        {% endif %}

                      </div>
                    </td>

                  </tr>
                  {% endfor %}

                  {% if items|length == 0 %}
                    <tr>
                      <td colspan="8" class="text-center text-muted py-5">
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
    </div>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .remmat-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .remmat-header-card{
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

      .remmat-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .remmat-header-overlay{
        display:flex;
        align-items:center;
        gap:14px;
        position:relative;
        z-index:1;
      }

      .remmat-header-overlay::before{
        content:"📋";
        width:54px;
        height:54px;
        border-radius:14px;
        background:#fff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.4rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
      }

      .remmat-header-text::before{
        content:"SGSI · Plan de Remediación";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .remmat-title{
        color:#fff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
      }

      .remmat-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
      }

      .remmat-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .remmat-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .remmat-filter-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 10px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        margin-bottom:14px;
      }

      .remmat-filter-body{
        padding:8px 7px;
      }

      .remmat-filter-body .form-label{
        font-weight:800;
        font-size:.78rem;
        color:#25324a;
      }

      .remmat-filter-body .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .remmat-filter-body .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }

      .remmat-filter-actions{
        align-items:center;
      }

      .remmat-filter-actions .btn{
        min-height:32px;
        font-size:.80rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.12);
      }

      .remmat-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .remmat-topbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        padding:16px;
        flex-wrap:wrap;
      }

      .remmat-counter-badge{
        background:linear-gradient(135deg,#0f172a,#1e3a8a);
        color:#fff;
        border-radius:999px;
        padding:8px 14px;
        font-weight:900;
      }

      .remmat-card-body{
        padding:8px 7px;
      }

      .remmat-table-wrap{
        border-radius:16px;
        overflow:auto;
        background:#fff;
        border:1px solid #e2e8f0;
        box-shadow:0 6px 16px rgba(0,0,0,.08);
      }

      .remmat-table{
        min-width:1400px;
      }

      .remmat-table thead th{
        background:#3f86d6 !important;
        color:#fff;
        font-weight:900;
        font-size:.78rem;
        text-align:center;
      }

      .remmat-table td{
        font-size:.82rem;
      }

      .remmat-table tbody tr:hover{
        background:rgba(63,134,214,.08);
      }

      .remmat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
      }

      .remmat-btn-action{
        min-width:110px;
        font-size:.75rem;
      }

      @media (max-width:768px){
        .remmat-header-overlay{
          flex-direction:column;
          text-align:center;
        }

        .remmat-header-actions .btn,
        .remmat-filter-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      function eliminarRemediacionesFiltradas(){
        const total = {{ items|length }};

        if(total <= 0){
          alert('No hay registros para eliminar con los filtros aplicados.');
          return false;
        }

        const prioridad = "{{ filtro_prioridad }}";
        const estado = "{{ filtro_estado }}";

        let mensaje = '¿Está seguro de eliminar los registros filtrados?\\n\\n';
        mensaje += 'Total registros a eliminar: ' + total + '\\n';

        if(prioridad){
          mensaje += 'Prioridad: ' + prioridad + '\\n';
        }

        if(estado){
          mensaje += 'Estado: ' + estado + '\\n';
        }

        if(!prioridad && !estado){
          mensaje += '\\nADVERTENCIA: No hay filtros aplicados. Se eliminarán TODOS los planes de remediación.\\n';
        }

        mensaje += '\\nEsta acción no se puede deshacer.';

        if(confirm(mensaje)){
          const form = document.getElementById('remmatDeleteFiltradosForm');
          if(form){
            form.submit();
          }
        }

        return false;
      }
    </script>
    """

    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        prioridad_choices=prioridad_choices,
        estado_choices=estado_choices,
        filtro_prioridad=filtro_prioridad,
        filtro_estado=filtro_estado
    )

    return render_template_string(BASE, content=Markup(inner))

# ==========================
# Detalle plan de remediación
# ==========================

@app.route('/plan_remediacion/detalle/<int:id>')
@login_required
def plan_remediacion_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Plan de Remediación"):
            flash("No tiene permiso para ver el detalle del plan de remediación.", "danger")
            return redirect(url_for('plan_remediacion_menu'))
        read_only = False

    pr = (
        PlanRemediacion.query
        .options(selectinload(PlanRemediacion.vulnerabilidad))
        .get_or_404(id)
    )

    vul = pr.vulnerabilidad

    html = """
    <div class="remdet-shell">

      <!-- CABECERA -->
      <div class="remdet-header-card">
        <div class="remdet-header-overlay">
          <div class="remdet-header-text">
            <h3 class="remdet-title m-0">Detalle del Plan de Remediación</h3>
            <div class="remdet-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <!-- BOTONES -->
      <div class="remdet-header-actions">
        <a href="{{ url_for('plan_remediacion_matriz') }}"
           class="btn rounded-pill px-4 fw-bold remdet-back-btn">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('plan_remediacion_edit', id=pr.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <!-- TARJETA -->
      <div class="remdet-card">
        <div class="remdet-card-body">

          <!-- SECCIÓN 1 -->
          <div class="remdet-section">
            <div class="remdet-section-title">Información general</div>
            <div class="row g-3">

              <div class="col-md-3">
                <div class="remdet-field remdet-field-compact">
                  <div class="remdet-label">ID Vulnerabilidad</div>
                  <div class="remdet-value remdet-value-compact">{{ vul.codigo if vul else '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="remdet-field remdet-field-compact">
                  <div class="remdet-label">Prioridad</div>
                  <div class="remdet-value remdet-value-compact">
                    {% if pr.prioridad == 'Crítica' %}
                      <span class="badge bg-dark">Crítica</span>
                    {% elif pr.prioridad == 'Alta' %}
                      <span class="badge bg-danger">Alta</span>
                    {% elif pr.prioridad == 'Media' %}
                      <span class="badge bg-warning text-dark">Media</span>
                    {% elif pr.prioridad == 'Baja' %}
                      <span class="badge bg-success">Baja</span>
                    {% else %}
                      <span class="badge bg-secondary">{{ pr.prioridad or '—' }}</span>
                    {% endif %}
                  </div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="remdet-field remdet-field-compact">
                  <div class="remdet-label">Estado</div>
                  <div class="remdet-value remdet-value-compact">
                    {% if pr.estado == 'Abierto' %}
                      <span class="badge bg-primary">Abierto</span>
                    {% elif pr.estado == 'Cerrado' %}
                      <span class="badge bg-success">Cerrado</span>
                    {% else %}
                      <span class="badge bg-secondary">{{ pr.estado or '—' }}</span>
                    {% endif %}
                  </div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="remdet-field remdet-field-compact">
                  <div class="remdet-label">Responsable</div>
                  <div class="remdet-value remdet-value-compact">{{ pr.responsable or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="remdet-field remdet-field-compact">
                  <div class="remdet-label">Fecha objetivo</div>
                  <div class="remdet-value remdet-value-compact">{{ pr.fecha_objetivo or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="remdet-field remdet-field-compact">
                  <div class="remdet-label">Fecha remediación</div>
                  <div class="remdet-value remdet-value-compact">{{ pr.fecha_remediacion or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <!-- SECCIÓN 2 -->
          <div class="remdet-section">
            <div class="remdet-section-title">Acción y recursos</div>
            <div class="row g-3">

              <div class="col-md-12">
                <div class="remdet-field">
                  <div class="remdet-label">Acción correctiva</div>
                  <div class="remdet-value remdet-value-lg">{{ pr.accion_correctiva or '—' }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="remdet-field">
                  <div class="remdet-label">Recursos necesarios</div>
                  <div class="remdet-value">{{ pr.recursos_necesarios or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <!-- SECCIÓN 3 -->
          <div class="remdet-section">
            <div class="remdet-section-title">Integración con Jira</div>
            <div class="row g-3">

              <div class="col-md-4">
                <div class="remdet-field remdet-field-compact">
                  <div class="remdet-label">Issue Key</div>
                  <div class="remdet-value remdet-value-compact">{{ pr.jira_issue_key or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="remdet-field remdet-field-compact">
                  <div class="remdet-label">Estado Jira</div>
                  <div class="remdet-value remdet-value-compact">{{ pr.jira_status or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="remdet-field remdet-field-compact">
                  <div class="remdet-label">Asignado a</div>
                  <div class="remdet-value remdet-value-compact">{{ pr.jira_assignee_name or '—' }}</div>
                </div>
              </div>

              {% if pr.jira_issue_url %}
              <div class="col-md-12">
                <div class="remdet-field">
                  <div class="remdet-label">Enlace Jira</div>
                  <div class="remdet-value">
                    <a href="{{ pr.jira_issue_url }}" target="_blank">Abrir ticket en Jira</a>
                  </div>
                </div>
              </div>
              {% endif %}

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

      .remdet-shell{
        width:96%;
        max-width:1200px;
        margin:10px auto 24px auto;
      }

      .remdet-header-card{
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

      .remdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .remdet-header-overlay{
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

      .remdet-header-overlay::before{
        content:"🔎️";
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

      .remdet-header-text{
        max-width:1000px;
        width:100%;
        display:block;
        transform:none;
      }

      .remdet-header-text::before{
        content:"SGSI · Detalle de Remediación";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .remdet-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .remdet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .remdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .remdet-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .remdet-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .remdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .remdet-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .remdet-card-body{
        padding:18px;
      }

      .remdet-section{
        margin-bottom:14px;
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .remdet-section:last-child{
        margin-bottom:0;
      }

      .remdet-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      .remdet-field{
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

      .remdet-field-compact{
        min-height:78px;
        justify-content:center;
        align-items:center;
        text-align:center;
      }

      .remdet-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .remdet-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .remdet-value-lg{
        font-size:.90rem;
        font-weight:900;
        color:#0f172a;
      }

      .remdet-value-compact{
        font-weight:900;
        font-size:.80rem;
        line-height:1.2;
      }

      .remdet-value .badge,
      .remdet-value-compact .badge{
        font-size:.70rem;
        padding:5px 10px;
        border-radius:999px;
        white-space:nowrap;
        display:inline-block;
        font-weight:900;
      }

      .remdet-section .row.g-3{
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
        background:#ffffff;
      }

      .remdet-soft-box{
        background:#eef5ff;
        border:1px solid #d9eaff;
        border-radius:14px;
        padding:12px 14px;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      @media (max-width:992px){
        .remdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .remdet-header-card{
          min-height:88px;
        }

        .remdet-title{
          font-size:1.20rem;
        }

        .remdet-card-body{
          padding:8px 7px;
        }

        .remdet-section{
          padding:12px;
        }

        .remdet-field,
        .remdet-field-compact{
          min-height:72px;
        }
      }

      @media (max-width:768px){
        .remdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .remdet-header-overlay::before{
          margin:0;
        }

        .remdet-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        pr=pr,
        vul=vul,
        read_only=read_only
    )
    return render_template_string(BASE, content=Markup(inner))



# ==========================
# Editar Remediación
# ==========================

@app.route('/plan_remediacion/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def plan_remediacion_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede editar registros.", "danger")
        return redirect(url_for('plan_remediacion_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Plan de Remediación"):
        flash("No tiene permiso para editar registros.", "danger")
        return redirect(url_for('plan_remediacion_menu'))

    item = PlanRemediacion.query.get_or_404(id)

    vulnerabilidades = VulnerabilidadRegistro.query.order_by(
        VulnerabilidadRegistro.codigo.asc()
    ).all()

    jira_users = cargar_usuarios_jira_para_formulario(item.responsable or "")

    if request.method == 'POST':
        vuln_id = request.form.get('vulnerabilidad_id', type=int)
        accion_correctiva = (request.form.get('accion_correctiva') or '').strip()
        responsable = (request.form.get('responsable') or '').strip()
        prioridad = (request.form.get('prioridad') or '').strip()
        recursos_necesarios = (request.form.get('recursos_necesarios') or '').strip()
        estado = (request.form.get('estado') or '').strip()
        fecha_objetivo_str = (request.form.get('fecha_objetivo') or '').strip()
        fecha_remediacion_str = (request.form.get('fecha_remediacion') or '').strip()
        jira_account_id = (request.form.get('jira_account_id') or '').strip()
        jira_assignee_name = (request.form.get('jira_assignee_name') or '').strip()

        fecha_objetivo = None
        if fecha_objetivo_str:
            try:
                fecha_objetivo = datetime.strptime(fecha_objetivo_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha objetivo inválida.", "danger")
                return redirect(url_for('plan_remediacion_edit', id=id))

        fecha_remediacion = None
        if fecha_remediacion_str:
            try:
                fecha_remediacion = datetime.strptime(fecha_remediacion_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de remediación inválida.", "danger")
                return redirect(url_for('plan_remediacion_edit', id=id))

        if not all([vuln_id, accion_correctiva, responsable, prioridad, estado]):
            flash("Campos obligatorios: ID Vulnerabilidad, Acción Correctiva, Responsable, Prioridad y Estado.", "danger")
            return redirect(url_for('plan_remediacion_edit', id=id))
        
        item.vulnerabilidad_id = vuln_id
        item.accion_correctiva = accion_correctiva
        item.responsable = responsable
        item.prioridad = prioridad
        item.fecha_objetivo = fecha_objetivo
        item.fecha_remediacion = fecha_remediacion
        item.recursos_necesarios = recursos_necesarios
        item.estado = estado

        asignar_usuario_jira_a_plan(
            item,
            jira_account_id,
            jira_assignee_name
        )

        sincronizar_vulnerabilidad_desde_plan(item)

        db.session.commit()
        if item.jira_issue_key:
            try:
                jira_actualizar_issue_plan(item.id)
                flash("Plan actualizado y sincronizado con Jira.", "success")
            except Exception as e:
                flash(f"Plan actualizado, pero no se pudo sincronizar Jira: {str(e)}", "warning")
        else:
            flash("Plan de remediación actualizado.", "success")

        return redirect(url_for('plan_remediacion_matriz'))

    html = """
    <div class="remedit-shell">

      <!-- CABECERA -->
      <div class="remedit-header-card">
        <div class="remedit-header-overlay">
          <div class="remedit-header-text">
            <h3 class="remedit-title m-0">Editar Plan de Remediación</h3>
            <div class="remedit-subtitle">
              Actualización de acciones correctivas definidas para mitigar vulnerabilidades identificadas, incluyendo responsables, prioridades, fechas y recursos necesarios
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="remedit-header-actions">
        <a href="{{ url_for('plan_remediacion_matriz') }}"
           class="btn rounded-pill px-5 fw-bold remedit-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <!-- TARJETA -->
      <div class="remedit-card">
        <div class="remedit-card-body">

          <form method="post">
            <div class="row g-3">

              <div class="col-12">
                <div class="remedit-section-title">Información del plan de remediación</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">ID de Vulnerabilidad</label>
                <select name="vulnerabilidad_id" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  {% for v in vulnerabilidades %}
                    <option value="{{ v.id }}" {% if item.vulnerabilidad_id == v.id %}selected{% endif %}>
                      {{ v.codigo }} — {{ (v.descripcion_vulnerabilidad or '')[:60] }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Acción Correctiva</label>
                <textarea name="accion_correctiva" class="form-control" rows="2" required>{{ item.accion_correctiva or '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Responsable</label>
                <input name="responsable" class="form-control" value="{{ item.responsable or '' }}" required>
              </div>

              <div class="col-md-4">
                  <label class="form-label">Prioridad</label>
                  <select name="prioridad" class="form-select" required>
                    <option value="">-- Seleccione --</option>
                    <option value="Crítica" {% if item.prioridad == 'Crítica' %}selected{% endif %}>Crítica</option>
                    <option value="Alta" {% if item.prioridad == 'Alta' %}selected{% endif %}>Alta</option>
                    <option value="Media" {% if item.prioridad == 'Media' %}selected{% endif %}>Media</option>
                    <option value="Baja" {% if item.prioridad == 'Baja' %}selected{% endif %}>Baja</option>
                  </select>
                </div>

              <div class="col-md-4">
                <label class="form-label">Fecha Objetivo</label>
                <input type="date"
                       name="fecha_objetivo"
                       class="form-control"
                       value="{{ item.fecha_objetivo.strftime('%Y-%m-%d') if item.fecha_objetivo else '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha de Remediación</label>
                <input type="date"
                       name="fecha_remediacion"
                       class="form-control"
                       value="{{ item.fecha_remediacion.strftime('%Y-%m-%d') if item.fecha_remediacion else '' }}">
              </div>

              <div class="col-md-12">
                <label class="form-label">Recursos Necesarios</label>
                <textarea name="recursos_necesarios" class="form-control" rows="2">{{ item.recursos_necesarios or '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Estado</label>
                <select name="estado" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  <option value="Abierto" {% if item.estado == 'Abierto' %}selected{% endif %}>Abierto</option>
                  <option value="Cerrado" {% if item.estado == 'Cerrado' %}selected{% endif %}>Cerrado</option>
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Asignado en Jira para esta remediación</label>
                <select name="jira_account_id" id="jira_account_id" class="form-select" onchange="actualizarNombreJira(this)">
                  <option value="">-- Sin asignar en Jira --</option>
                  {% for ju in jira_users %}
                    <option value="{{ ju.accountId }}"
                            data-name="{{ ju.displayName }}"
                            {% if item.jira_account_id == ju.accountId %}selected{% endif %}>
                      {{ ju.displayName }}
                    </option>
                  {% endfor %}
                </select>
                <input type="hidden"
                       name="jira_assignee_name"
                       id="jira_assignee_name"
                       value="{{ item.jira_assignee_name or '' }}">
                <div class="form-text">
                  Este usuario se usará solo para el ticket Jira de esta remediación.
                </div>
              </div>

            </div>

            <div class="remedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>

              <a href="{{ url_for('plan_remediacion_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold remedit-cancel-btn">
                Cancelar
              </a>
            </div>
          </form>

        </div>
      </div>
    </div>

    <script>
      function actualizarNombreJira(select){
        const opt = select.options[select.selectedIndex];
        const hidden = document.getElementById('jira_assignee_name');
        if(hidden){
          hidden.value = opt ? (opt.getAttribute('data-name') || '') : '';
        }
      }

      document.addEventListener('DOMContentLoaded', function(){
        const sel = document.getElementById('jira_account_id');
        if(sel){
          actualizarNombreJira(sel);
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

      .remedit-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      .remedit-header-card{
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

      .remedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .remedit-header-overlay{
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

      .remedit-header-overlay::before{
        content:"🛠️";
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

      .remedit-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .remedit-header-text::before{
        content:"SGSI · Edición de Plan de Remediación";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .remedit-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .remedit-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .remedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .remedit-header-actions .btn,
      .remedit-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .remedit-back-btn,
      .remedit-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .remedit-back-btn:hover,
      .remedit-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .remedit-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .remedit-card-body{
        padding:18px;
      }

      .remedit-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .remedit-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .remedit-card .form-control,
      .remedit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .remedit-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .remedit-card .form-control:focus,
      .remedit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .remedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
        width:100%;
      }

      .remedit-card .btn{
        font-weight:900;
      }

      @media (max-width:992px){
        .remedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .remedit-header-card{
          min-height:88px;
        }

        .remedit-title{
          font-size:1.20rem;
        }

        .remedit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .remedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .remedit-header-overlay::before{
          margin:0;
        }

        .remedit-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .remedit-header-actions .btn,
        .remedit-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        item=item,
        vulnerabilidades=vulnerabilidades,
        jira_users=jira_users
    )
    return render_template_string(BASE, content=Markup(inner))

# ==========================
# Eliminar
# ==========================

@app.route('/plan_remediacion/<int:id>/delete')
@login_required
def plan_remediacion_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros.", "danger")
        return redirect(url_for('plan_remediacion_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Plan de Remediación"):
        flash("No tiene permiso para eliminar registros.", "danger")
        return redirect(url_for('plan_remediacion_menu'))

    item = PlanRemediacion.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()

    flash("Plan de remediación eliminado.", "success")
    return redirect(url_for('plan_remediacion_matriz'))

# ==========================
# Eliminar Remediaciones por filtros
# ==========================

@app.route('/plan_remediacion/delete_filtrados', methods=['POST'])
@login_required
def plan_remediacion_delete_filtrados():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros.", "danger")
        return redirect(url_for('plan_remediacion_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Plan de Remediación"):
        flash("No tiene permiso para eliminar planes de remediación.", "danger")
        return redirect(url_for('plan_remediacion_matriz'))

    filtro_prioridad = (request.form.get('prioridad') or '').strip()
    filtro_estado = (request.form.get('estado') or '').strip()

    if not filtro_prioridad and not filtro_estado:
        flash("Debe aplicar al menos un filtro para eliminar por grupo.", "warning")
        return redirect(url_for('plan_remediacion_matriz'))

    try:
        q = PlanRemediacion.query

        if filtro_prioridad:
            q = q.filter(PlanRemediacion.prioridad == filtro_prioridad)

        if filtro_estado:
            q = q.filter(PlanRemediacion.estado == filtro_estado)

        planes = q.all()

        if not planes:
            flash("No se encontraron planes para eliminar con los filtros seleccionados.", "warning")
            return redirect(url_for(
                'plan_remediacion_matriz',
                prioridad=filtro_prioridad,
                estado=filtro_estado
            ))

        vuln_ids = list(set([p.vulnerabilidad_id for p in planes if p.vulnerabilidad_id]))
        total = len(planes)

        for p in planes:
            db.session.delete(p)

        db.session.flush()

        for vuln_id in vuln_ids:
            vuln = VulnerabilidadRegistro.query.get(vuln_id)
            if not vuln:
                continue

            planes_restantes = PlanRemediacion.query.filter_by(
                vulnerabilidad_id=vuln_id
            ).all()

            if not planes_restantes:
                vuln.estado = "Abierto"
                vuln.fecha_cierre = None
            else:
                cerrado = next(
                    (x for x in planes_restantes if (x.estado or '').strip().lower() == 'cerrado'),
                    None
                )

                if cerrado:
                    vuln.estado = "Cerrado"
                    vuln.fecha_cierre = cerrado.fecha_remediacion
                else:
                    vuln.estado = "Abierto"
                    vuln.fecha_cierre = None

        db.session.commit()

        flash(f"Se eliminaron {total} planes de remediación con los filtros seleccionados.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"No fue posible eliminar los planes filtrados: {str(e)}", "danger")

    return redirect(url_for('plan_remediacion_matriz'))


# ==========================
# Jira - formulario modal / popup lógico
# ==========================

@app.route('/plan_remediacion/<int:id>/jira', methods=['GET', 'POST'])
@login_required
def plan_remediacion_jira(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede integrar con Jira.", "danger")
        return redirect(url_for('plan_remediacion_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Plan de Remediación"):
        flash("No tiene permiso para integrar con Jira.", "danger")
        return redirect(url_for('plan_remediacion_matriz'))

    plan = PlanRemediacion.query.get_or_404(id)
    vuln = VulnerabilidadRegistro.query.get_or_404(plan.vulnerabilidad_id)

    if request.method == 'POST':
        jira_assignee_name = (request.form.get('jira_assignee_name') or '').strip()
        jira_account_id = (request.form.get('jira_account_id') or '').strip()

        if not jira_account_id:
            flash("Debe seleccionar el usuario Jira asignado para esta remediación.", "danger")
            return redirect(url_for('plan_remediacion_jira', id=id))

        try:
            asignar_usuario_jira_a_plan(
                plan,
                jira_account_id,
                jira_assignee_name
            )
            db.session.commit()

            res = jira_crear_issue_plan(plan.id)

            if res.get("already_exists"):
                flash(f"El plan ya tiene ticket Jira asociado: {res.get('issue_key')}", "info")
            else:
                flash(f"Ticket Jira creado correctamente: {res.get('issue_key')}", "success")

            return redirect(url_for('plan_remediacion_matriz'))

        except Exception as e:
            flash(f"No se pudo crear el ticket en Jira: {str(e)}", "danger")
            return redirect(url_for('plan_remediacion_matriz'))

    # GET: mostrar TODOS los usuarios asignables del proyecto Jira.
    # No se filtra por responsable SGSI porque dicho texto puede no existir en Jira
    # (por ejemplo, "Administrador") y dejaría el selector vacío.
    usuarios_jira = cargar_usuarios_jira_para_formulario()

    html = """
    <div class="jira-shell">

      <!-- CABECERA -->
      <div class="jira-header-card">
        <div class="jira-header-overlay">
          <div class="jira-header-text">
            <h3 class="jira-title m-0">🎫 Enviar Plan a Jira</h3>
            <div class="jira-subtitle">
              Creación automática de un ticket en Jira para el seguimiento del plan de remediación asociado a una vulnerabilidad identificada
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="jira-header-actions">
        <a href="{{ url_for('plan_remediacion_matriz') }}"
           class="btn rounded-pill px-5 fw-bold jira-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <!-- TARJETA -->
      <div class="jira-card">
        <div class="jira-card-body">

          <form method="post">
            <div class="row g-3">

              <div class="col-12">
                <div class="jira-section-title">Información del plan</div>
              </div>

              <div class="col-md-12">
                <div class="alert alert-info jira-plan-info">
                  <b>Plan:</b> {{ plan.id }}<br>
                  <b>Vulnerabilidad:</b> {{ vuln.codigo or '—' }}<br>
                  <b>Responsable SGSI:</b> {{ plan.responsable or '—' }}<br>
                  <b>Prioridad:</b> {{ plan.prioridad or '—' }}
                </div>
              </div>

              <div class="col-md-12">
                <label class="form-label">Asignar este ticket Jira a</label>
                <select name="jira_account_id"
                        id="jira_account_id"
                        class="form-select"
                        required
                        onchange="actualizarNombreJira(this)">
                  <option value="">-- Seleccione usuario Jira asignable --</option>
                  {% for u in usuarios_jira %}
                    <option value="{{ u.accountId }}"
                            data-name="{{ u.displayName }}"
                            {% if plan.jira_account_id == u.accountId %}selected{% endif %}>
                      {{ u.displayName }}
                    </option>
                  {% endfor %}
                </select>
                <input type="hidden"
                       name="jira_assignee_name"
                       id="jira_assignee_name"
                       value="{{ plan.jira_assignee_name or '' }}">
                <small class="text-muted">
                  La asignación queda guardada solo para este punto de remediación.
                </small>
              </div>

              {% if usuarios_jira %}
              <div class="col-12">
                <div class="jira-section-title">Usuarios disponibles en Jira</div>
              </div>

              <div class="col-md-12">
                <div class="table-responsive jira-table-box">
                  <table class="table table-bordered table-sm align-middle">
                    <thead class="jira-table-head">
                      <tr>
                        <th>Nombre</th>
                        <th>Account ID</th>
                      </tr>
                    </thead>
                    <tbody>
                      {% for u in usuarios_jira %}
                      <tr>
                        <td>{{ u.displayName or '—' }}</td>
                        <td class="small">{{ u.accountId or '—' }}</td>
                      </tr>
                      {% endfor %}
                    </tbody>
                  </table>
                </div>
              </div>
              {% endif %}

            </div>

            <div class="jira-bottom-actions">
              <button class="btn btn-primary rounded-pill px-4 fw-bold" type="submit">
                Crear Ticket en Jira
              </button>

              <a href="{{ url_for('plan_remediacion_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold jira-cancel-btn">
                Cancelar
              </a>
            </div>
          </form>

        </div>
      </div>
    </div>

    <script>
      function actualizarNombreJira(select){
        const opt = select.options[select.selectedIndex];
        const hidden = document.getElementById('jira_assignee_name');
        if(hidden){
          hidden.value = opt ? (opt.getAttribute('data-name') || '') : '';
        }
      }

      document.addEventListener('DOMContentLoaded', function(){
        const sel = document.getElementById('jira_account_id');
        if(sel){
          actualizarNombreJira(sel);
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

      .jira-shell{
        width:96%;
        max-width:1200px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HEADER SGSI MODERNO
      ========================= */
      .jira-header-card{
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

      .jira-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .jira-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        position:relative;
        z-index:1;
      }

      .jira-header-overlay::before{
        content:"📊";
        width:54px;
        height:54px;
        border-radius:14px;
        background:#fff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.4rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .jira-header-text::before{
        content:"SGSI · Integración Jira";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .jira-title{
        color:#fff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
      }

      .jira-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
      }

      /* =========================
         BOTONES
      ========================= */
      .jira-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .jira-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .jira-back-btn{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .jira-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      /* =========================
         CARD
      ========================= */
      .jira-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .jira-card-body{
        padding:18px;
      }

      .jira-section-title{
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
      .form-label{
        font-weight:800;
        font-size:.78rem;
        color:#25324a;
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

      /* =========================
         TABLA MODERNA
      ========================= */
      .jira-table-box{
        background:#fff;
        border-radius:16px;
        border:1px solid #e2e8f0;
        overflow:hidden;
        box-shadow:0 6px 16px rgba(0,0,0,.08);
      }

      .jira-table-box table{
        margin-bottom:0;
      }

      .jira-table-box thead th{
        background:#3f86d6 !important;
        color:#fff !important;
        font-weight:900;
        font-size:.78rem;
        text-align:center;
        border:none;
      }

      .jira-table-box td{
        font-size:.82rem;
        vertical-align:middle;
      }

      .jira-table-box tbody tr:hover{
        background:rgba(63,134,214,.08);
      }

      /* =========================
         ACCIONES
      ========================= */
      .jira-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
      }

      .jira-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .jira-cancel-btn{
        background:#fff;
        border:1px solid #cfd8e3;
      }

      .jira-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      /* =========================
         RESPONSIVE
      ========================= */
      @media (max-width:768px){
        .jira-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .jira-header-actions .btn,
        .jira-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, plan=plan, vuln=vuln, usuarios_jira=usuarios_jira)
    return render_template_string(BASE, content=Markup(inner))


@app.route('/plan_remediacion/<int:id>/jira_sync')
@login_required
def plan_remediacion_jira_sync(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede sincronizar Jira.", "danger")
        return redirect(url_for('plan_remediacion_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Plan de Remediación"):
        flash("No tiene permiso para sincronizar Jira.", "danger")
        return redirect(url_for('plan_remediacion_matriz'))

    try:
        status_name = jira_sync_plan(id)
        flash(f"Estado Jira sincronizado correctamente: {status_name}", "success")
    except Exception as e:
        flash(f"No se pudo sincronizar con Jira: {str(e)}", "danger")

    return redirect(url_for('plan_remediacion_matriz'))


@app.route('/plan_remediacion/jira/config', methods=['GET', 'POST'])
@login_required
def jira_config_view():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede modificar la configuración Jira.", "danger")
        return redirect(url_for('plan_remediacion_menu'))

    if user.role != 'admin' and not verificar_permiso(user, "Plan de Remediación"):
        flash("No tiene permiso para configurar Jira.", "danger")
        return redirect(url_for('plan_remediacion_menu'))

    cfg = get_jira_config()

    if request.method == 'POST':
        cfg.enabled = bool(request.form.get('enabled'))
        cfg.base_url = (request.form.get('base_url') or '').strip()
        cfg.email = (request.form.get('email') or '').strip()
        cfg.project_key = (request.form.get('project_key') or '').strip()
        cfg.issue_type = (request.form.get('issue_type') or 'Task').strip()

        nuevo_token = (request.form.get('api_token') or '').strip()
        if nuevo_token:
            cfg.api_token_enc = jira_encrypt_token(nuevo_token)

        db.session.commit()
        flash("Configuración Jira guardada correctamente.", "success")
        return redirect(url_for('jira_config_view'))

    html = """
    <div class="jiracfg-shell">

      <!-- CABECERA -->
      <div class="jiracfg-header-card">
        <div class="jiracfg-header-overlay">
          <div class="jiracfg-header-text">
            <h3 class="jiracfg-title m-0">Configuración Jira</h3>
            <div class="jiracfg-subtitle">
              Parámetros de integración entre el SGSI y Jira para la gestión automática de tickets de remediación
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="jiracfg-header-actions">
        <a href="{{ url_for('plan_remediacion_menu') }}"
           class="btn rounded-pill px-5 fw-bold jiracfg-back-btn">
          ⬅ Volver al Menú Plan de Remediación
        </a>
      </div>

      <!-- TARJETA -->
      <div class="jiracfg-card">
        <div class="jiracfg-card-body">

          <form method="post">
            <div class="row g-3">

              <div class="col-12">
                <div class="jiracfg-section-title">Configuración de conexión</div>
              </div>

              <div class="col-md-3">
                <div class="form-check mt-4">
                  <input class="form-check-input"
                         type="checkbox"
                         name="enabled"
                         id="enabled"
                         {% if cfg.enabled %}checked{% endif %}>
                  <label class="form-check-label fw-bold" for="enabled">
                    Habilitar integración Jira
                  </label>
                </div>
              </div>

              <div class="col-md-9">
                <label class="form-label">Base URL Jira</label>
                <input name="base_url"
                       class="form-control"
                       value="{{ cfg.base_url or '' }}"
                       placeholder="https://tuempresa.atlassian.net"
                       required>
              </div>

              <div class="col-md-6">
                <label class="form-label">Correo Jira</label>
                <input name="email"
                       class="form-control"
                       value="{{ cfg.email or '' }}"
                       placeholder="usuario@empresa.com"
                       required>
              </div>

              <div class="col-md-3">
                <label class="form-label">Proyecto</label>
                <input name="project_key"
                       class="form-control"
                       value="{{ cfg.project_key or 'SGSI' }}"
                       required>
              </div>

              <div class="col-md-3">
                <label class="form-label">Tipo de issue</label>
                <input name="issue_type"
                       class="form-control"
                       value="{{ cfg.issue_type or 'Task' }}"
                       required>
              </div>

              <div class="col-12">
                <div class="jiracfg-section-title">Seguridad</div>
              </div>

              <div class="col-md-12">
                <label class="form-label">API Token Jira</label>
                <input name="api_token"
                       type="password"
                       class="form-control"
                       placeholder="Ingrese nuevo token solo si desea cambiarlo">
                <small class="text-muted">
                  El token se almacena cifrado en la base de datos. Si deja este campo vacío, se conserva el actual.
                </small>
              </div>

            </div>

            <div class="jiracfg-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar configuración
              </button>

              <a href="{{ url_for('plan_remediacion_menu') }}"
                 class="btn rounded-pill px-4 fw-bold jiracfg-cancel-btn">
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

      .jiracfg-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      .jiracfg-header-card{
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

      .jiracfg-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .jiracfg-header-overlay{
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

      .jiracfg-header-overlay::before{
        content:"🎫f";
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

      .jiracfg-header-text{
        max-width:1100px;
        width:100%;
        display:block;
        transform:none;
      }

      .jiracfg-header-text::before{
        content:"SGSI · Configuración Jira";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .jiracfg-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .jiracfg-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .jiracfg-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .jiracfg-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .jiracfg-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .jiracfg-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .jiracfg-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .jiracfg-card-body{
        padding:18px;
      }

      .jiracfg-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .form-control,
      .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .form-control:focus,
      .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .jiracfg-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
      }

      .jiracfg-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .jiracfg-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .jiracfg-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .btn.rounded-pill{
        border-radius:10px !important;
      }

      .jiracfg-card .btn-primary,
      .jiracfg-card .btn-success,
      .jiracfg-card .btn-outline-secondary{
        font-weight:900;
      }

      @media (max-width:992px){
        .jiracfg-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .jiracfg-header-card{
          min-height:88px;
        }

        .jiracfg-title{
          font-size:1.20rem;
        }

        .jiracfg-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .jiracfg-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .jiracfg-header-overlay::before{
          margin:0;
        }

        .jiracfg-header-actions .btn,
        .jiracfg-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, cfg=cfg)
    return render_template_string(BASE, content=Markup(inner))

# ==========================================================================================================================================
#                                                           Fin Módulo Plan de Remediación
# ==========================================================================================================================================

# ==========================================================================================================================================
# MÓDULO COMPLETO — CAMPAÑAS DE CONCIENTIZACIÓN
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                      MÓDULO INDEPENDIENTE — CAMPAÑAS DE CONCIENTIZACIÓN
#                                      GRAC / SGSI — Capítulo: Competencias y Cultura
# ==========================================================================================================================================

import os
import re
import json
import sqlite3
import requests
from datetime import datetime
from markupsafe import Markup, escape
from flask import request, redirect, url_for, flash, render_template_string, jsonify

# ============================================================
# CONFIGURACIÓN DB INDEPENDIENTE
# ============================================================

CAMP_CONC_MODULE_NAME = "Campañas de Concientización"

CAMP_CONC_DB_PATH = os.path.join(app.instance_path, "campanias_concientizacion.db")
os.makedirs(app.instance_path, exist_ok=True)


def get_camp_conc_db_connection():
    conn = sqlite3.connect(CAMP_CONC_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_campanias_concientizacion_db():
    conn = get_camp_conc_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS campanias_concientizacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date TEXT,
            participants INTEGER DEFAULT 0,
            target_area TEXT,
            target_division TEXT,
            generated_options_json TEXT,
            selected_option_index INTEGER,
            selected_title TEXT,
            selected_category TEXT,
            selected_format TEXT,
            selected_duration TEXT,
            selected_level TEXT,
            selected_objective TEXT,
            selected_justification TEXT,
            detailed_plan_json TEXT,
            status TEXT DEFAULT 'Generada',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            plan_diseno_id INTEGER,
            registered_at TEXT
        )
    """)

    # Migración defensiva por si el módulo ya existe y faltan columnas.
    cur.execute("PRAGMA table_info(campanias_concientizacion)")
    cols = {r[1] for r in cur.fetchall()}

    required_cols = {
        "session_date": "TEXT",
        "participants": "INTEGER DEFAULT 0",
        "target_area": "TEXT",
        "target_division": "TEXT",
        "generated_options_json": "TEXT",
        "selected_option_index": "INTEGER",
        "selected_title": "TEXT",
        "selected_category": "TEXT",
        "selected_format": "TEXT",
        "selected_duration": "TEXT",
        "selected_level": "TEXT",
        "selected_objective": "TEXT",
        "selected_justification": "TEXT",
        "detailed_plan_json": "TEXT",
        "status": "TEXT DEFAULT 'Generada'",
        "created_by": "TEXT",
        "created_at": "TEXT",
        "updated_at": "TEXT",
        "plan_diseno_id": "INTEGER",
        "registered_at": "TEXT",
    }

    for col, ddl in required_cols.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE campanias_concientizacion ADD COLUMN {col} {ddl}")

    conn.commit()
    conn.close()


init_campanias_concientizacion_db()


# ============================================================
# SEGURIDAD / PERMISOS
# ============================================================

def camp_conc_current_user():
    try:
        return User.query.get(session.get("user_id"))
    except Exception:
        return None


def camp_conc_can_read(user):
    if not user:
        return False
    if user.role in ("admin", "auditor"):
        return True
    # Permiso nuevo; también acepta el permiso anterior para no romper usuarios existentes.
    return (
        verificar_permiso(user, CAMP_CONC_MODULE_NAME)
        or verificar_permiso(user, "Plan de Concientización y Formación")
        or verificar_permiso(user, "Seguimiento del Plan de Formación")
    )


def camp_conc_can_write(user):
    if not user:
        return False
    if user.role == "auditor":
        return False
    if user.role == "admin":
        return True
    return (
        verificar_permiso(user, CAMP_CONC_MODULE_NAME)
        or verificar_permiso(user, "Plan de Concientización y Formación")
    )


def camp_conc_require_read():
    user = camp_conc_current_user()
    if not camp_conc_can_read(user):
        flash("No tiene permiso para acceder al módulo de Campañas de Concientización.", "danger")
        return None, redirect(url_for("menu"))
    return user, None


def camp_conc_require_write():
    user = camp_conc_current_user()
    if user and user.role == "auditor":
        flash("El rol Auditor solo puede consultar este módulo.", "danger")
        return None, redirect(url_for("campanias_concientizacion_matriz"))
    if not camp_conc_can_write(user):
        flash("No tiene permiso para modificar Campañas de Concientización.", "danger")
        return None, redirect(url_for("menu"))
    return user, None


# ============================================================
# UTILIDADES
# ============================================================

def camp_conc_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def camp_conc_parse_json(value, default=None):
    if default is None:
        default = {}
    if not value:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def camp_conc_extract_json(text):
    """
    Limpia respuestas de IA con fences ```json y extrae JSON válido.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("La IA no devolvió contenido.")

    text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text.strip()).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    # Intento: arreglo JSON dentro del texto.
    m = re.search(r"(\[[\s\S]*\])", text)
    if m:
        return json.loads(m.group(1))

    # Intento: objeto JSON dentro del texto.
    m = re.search(r"(\{[\s\S]*\})", text)
    if m:
        return json.loads(m.group(1))

    raise ValueError("No fue posible interpretar la respuesta de IA como JSON válido.")


def camp_conc_call_ai(system_prompt, user_prompt, max_tokens=1200):
    """
    Helper unificado para este módulo.
    IMPORTANTE:
    - Para OpenRouter usa ai_text_general().
    - Para Ollama usa llamada directa con timeout mayor y num_predict controlado.
    - Así evitamos errores por timeout cuando se genera la campaña completa.
    """
    return campania_ai_text(
        prompt=user_prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens
    )

def camp_conc_format_value(value, level=0):
    """
    Convierte dict/list/string en HTML limpio para detalle.
    """
    if value is None:
        return '<span class="text-muted">—</span>'

    if isinstance(value, dict):
        parts = ['<div class="campdet-structured">']
        for k, v in value.items():
            key = escape(str(k).replace("_", " ").capitalize())
            parts.append(f'<div class="campdet-struct-item level-{level}">')
            parts.append(f'<div class="campdet-struct-key">{key}</div>')
            parts.append(f'<div class="campdet-struct-value">{camp_conc_format_value(v, level + 1)}</div>')
            parts.append('</div>')
        parts.append('</div>')
        return "".join(parts)

    if isinstance(value, list):
        parts = ['<ul class="campdet-list">']
        for item in value:
            parts.append(f"<li>{camp_conc_format_value(item, level + 1)}</li>")
        parts.append("</ul>")
        return "".join(parts)

    text = str(value).strip()
    if not text:
        return '<span class="text-muted">—</span>'

    text = escape(text)
    text = str(text).replace("\n", "<br>")
    return text


def camp_conc_status_badge(status):
    status = (status or "Generada").strip()
    if status == "Ejecutada":
        return '<span class="badge bg-success">Ejecutada</span>'
    if status == "En ejecución":
        return '<span class="badge bg-primary">En ejecución</span>'
    if status == "Cancelada":
        return '<span class="badge bg-danger">Cancelada</span>'
    if status == "Planificada":
        return '<span class="badge bg-warning text-dark">Planificada</span>'
    return f'<span class="badge bg-secondary">{escape(status)}</span>'


def camp_conc_user_name(user):
    if not user:
        return "Sistema"
    for attr in ("nombre", "name", "username", "email"):
        val = getattr(user, attr, None)
        if val:
            return str(val)
    return "Usuario"


def camp_conc_fetch_one(session_id):
    conn = get_camp_conc_db_connection()
    row = conn.execute("SELECT * FROM campanias_concientizacion WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return row


def camp_conc_get_used_topics(exclude_id=None):
    conn = get_camp_conc_db_connection()
    if exclude_id:
        rows = conn.execute("""
            SELECT selected_title, selected_category
            FROM campanias_concientizacion
            WHERE selected_title IS NOT NULL
              AND TRIM(selected_title) <> ''
              AND id <> ?
            ORDER BY id DESC
            LIMIT 30
        """, (exclude_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT selected_title, selected_category
            FROM campanias_concientizacion
            WHERE selected_title IS NOT NULL
              AND TRIM(selected_title) <> ''
            ORDER BY id DESC
            LIMIT 30
        """).fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "title": r["selected_title"] or "",
            "category": r["selected_category"] or ""
        })
    return result


def camp_conc_obtener_areas_y_divisiones():
    """
    Toma las áreas y divisiones desde el módulo Estructura Organizacional.
    Usa:
    - AreaEmpresa.area
    - AreaEmpresa.divisiones
    - DivisionEmpresa.nombre_division
    """
    areas = []
    divisiones_por_area = {}

    try:
        areas_db = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()

        for a in areas_db:
            nombre_area = (getattr(a, "area", "") or "").strip()
            if not nombre_area:
                continue

            areas.append(nombre_area)
            divisiones_por_area.setdefault(nombre_area, [])

            for d in (getattr(a, "divisiones", []) or []):
                nombre_div = (getattr(d, "nombre_division", "") or "").strip()
                if nombre_div and nombre_div not in divisiones_por_area[nombre_area]:
                    divisiones_por_area[nombre_area].append(nombre_div)

            divisiones_por_area[nombre_area].sort(key=lambda s: s.lower())

        areas = sorted(set(areas), key=lambda s: s.lower())

    except Exception as e:
        print("ERROR camp_conc_obtener_areas_y_divisiones:", repr(e))
        areas = []
        divisiones_por_area = {}

    return areas, divisiones_por_area


def camp_conc_area_options(areas, selected=""):
    selected = (selected or "").strip()
    parts = ['<option value="">-- Seleccione área --</option>']
    parts.append('<option value="Todas las áreas" ' + ('selected' if selected == "Todas las áreas" else '') + '>Todas las áreas</option>')

    for area in areas:
        sel = "selected" if area == selected else ""
        parts.append(f'<option value="{escape(area)}" {sel}>{escape(area)}</option>')

    if selected and selected != "Todas las áreas" and selected not in areas:
        parts.append(f'<option value="{escape(selected)}" selected>{escape(selected)}</option>')

    return "".join(parts)


def camp_conc_division_options(divisiones_por_area, area="", selected=""):
    area = (area or "").strip()
    selected = (selected or "").strip()
    divisiones = divisiones_por_area.get(area, [])

    parts = ['<option value="">-- Seleccione división --</option>']
    parts.append('<option value="Todas las divisiones" ' + ('selected' if selected == "Todas las divisiones" else '') + '>Todas las divisiones</option>')

    for division in divisiones:
        sel = "selected" if division == selected else ""
        parts.append(f'<option value="{escape(division)}" {sel}>{escape(division)}</option>')

    if selected and selected != "Todas las divisiones" and selected not in divisiones:
        parts.append(f'<option value="{escape(selected)}" selected>{escape(selected)}</option>')

    return "".join(parts)


def camp_conc_area_division_js(divisiones_por_area, area_id="target_area", division_id="target_division"):
    data = json.dumps(divisiones_por_area or {}, ensure_ascii=False)

    return f"""
    <script>
      (function(){{
        const divisionesPorArea = {data};

        function actualizarDivisionCampania(){{
          const areaSelect = document.getElementById("{area_id}");
          const divisionSelect = document.getElementById("{division_id}");

          if(!areaSelect || !divisionSelect){{
            return;
          }}

          const area = areaSelect.value || "";
          const actual = divisionSelect.getAttribute("data-selected") || divisionSelect.value || "";
          const divisiones = divisionesPorArea[area] || [];

          divisionSelect.innerHTML = "";

          const optBase = document.createElement("option");
          optBase.value = "";
          optBase.textContent = "-- Seleccione división --";
          divisionSelect.appendChild(optBase);

          const optTodas = document.createElement("option");
          optTodas.value = "Todas las divisiones";
          optTodas.textContent = "Todas las divisiones";
          divisionSelect.appendChild(optTodas);

          if(area && area !== "Todas las áreas"){{
            divisiones.forEach(function(nombre){{
              const opt = document.createElement("option");
              opt.value = nombre;
              opt.textContent = nombre;

              if(nombre === actual){{
                opt.selected = true;
              }}

              divisionSelect.appendChild(opt);
            }});
          }}

          if(actual && actual !== "Todas las divisiones" && !divisiones.includes(actual)){{
            const optActual = document.createElement("option");
            optActual.value = actual;
            optActual.textContent = actual;
            optActual.selected = true;
            divisionSelect.appendChild(optActual);
          }}

          if(actual === "Todas las divisiones"){{
            optTodas.selected = true;
          }}
        }}

        document.addEventListener("DOMContentLoaded", function(){{
          const areaSelect = document.getElementById("{area_id}");
          const divisionSelect = document.getElementById("{division_id}");

          if(areaSelect && divisionSelect){{
            actualizarDivisionCampania();

            areaSelect.addEventListener("change", function(){{
              divisionSelect.setAttribute("data-selected", "");
              actualizarDivisionCampania();
            }});
          }}
        }});
      }})();
    </script>
    """


def campania_ai_text(prompt: str, system_prompt: str = "", max_tokens: int = 900) -> str:
    """
    Llamada IA optimizada para Campañas de Concientización.

    Corrige el error:
    HTTPConnectionPool(host='localhost', port=11434): Read timed out. (read timeout=300)

    Motivo:
    El helper global ai_text_general() usa timeout 300 para Ollama y puede no alcanzar
    cuando se pide una campaña completa en JSON.

    Esta función:
    - Usa timeout 600 para Ollama.
    - Limita num_predict para evitar respuestas demasiado largas que bloqueen el modelo.
    - Mantiene OpenRouter usando ai_text_general().
    - Devuelve errores claros, sin mostrar "Acceso denegado" cuando realmente es timeout.
    """
    provider = "openrouter"
    try:
        if "get_ai_provider" in globals():
            provider = (get_ai_provider() or "openrouter").strip().lower()
    except Exception:
        provider = "openrouter"

    if provider == "ollama":
        if "requests" not in globals():
            raise RuntimeError("Falta importar requests. Agrega: import requests")

        base_url = "http://localhost:11434"
        model = "llama3.1"

        try:
            if "get_ollama_base_url" in globals():
                base_url = (get_ollama_base_url() or base_url).strip().rstrip("/")
            if "get_ollama_model" in globals():
                model = (get_ollama_model() or model).strip()
        except Exception:
            pass

        if not base_url:
            raise RuntimeError("No hay URL de Ollama configurada.")
        if not model:
            raise RuntimeError("No hay modelo de Ollama configurado.")

        full_prompt = (prompt or "").strip()
        if system_prompt:
            full_prompt = (system_prompt or "").strip() + "\n\n" + full_prompt

        # Controla la longitud. Si num_predict es muy alto, Ollama se queda procesando
        # y Flask termina mostrando timeout.
        try:
            requested_predict = int(max_tokens or 900)
        except Exception:
            requested_predict = 900

        num_predict = max(500, min(requested_predict, 1600))

        try:
            resp = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.12,
                        "num_predict": num_predict,
                        "top_p": 0.85,
                        "num_ctx": 4096
                    }
                },
                timeout=600
            )
            resp.raise_for_status()

            data = resp.json() or {}
            texto = (data.get("response") or "").strip()

            if not texto:
                raise RuntimeError("Ollama respondió sin contenido.")

            if "limpiar_texto_ia_global" in globals():
                return limpiar_texto_ia_global(texto)

            return texto.strip()

        except requests.exceptions.ReadTimeout:
            raise RuntimeError(
                "Ollama tardó demasiado generando la campaña. "
                "Se recomienda usar un modelo más liviano, reducir el tamaño del prompt "
                "o cambiar temporalmente el proveedor IA a OpenRouter."
            )
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "No fue posible conectar con Ollama. Verifica que Ollama esté encendido "
                "y que la URL configurada sea correcta."
            )
        finally:
            try:
                if "liberar_memoria_ollama_seguro" in globals():
                    liberar_memoria_ollama_seguro()
            except Exception:
                pass

    if "ai_text_general" not in globals():
        raise RuntimeError(
            "No existe ai_text_general() en Programasgsi2.py. "
            "Debes pegar este módulo después de las funciones globales de IA."
        )

    return ai_text_general(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=max_tokens
    )


# ============================================================
# PROMPTS IA
# ============================================================

def camp_conc_build_system_prompt_options():
    return """
Eres un consultor senior de ciberseguridad, awareness, cultura organizacional y SGSI.
Debes proponer campañas o charlas de concientización en seguridad alineadas con ISO 27001,
especialmente con competencia, toma de conciencia, formación, cultura de seguridad y mejora continua.

Responde SIEMPRE en JSON válido, sin texto adicional.
La salida debe ser un arreglo JSON de exactamente 5 objetos.
Cada objeto debe tener estas claves exactas:
- "titulo"
- "categoria_tema"
- "objetivo"
- "justificacion"
- "formato"
- "duracion_sugerida"
- "nivel_publico"

Reglas:
1. Las propuestas deben ser ejecutivas, profesionales y aptas para entorno corporativo.
2. Deben adaptarse al área objetivo y a la cantidad de participantes.
3. Deben ser distintas entre sí.
4. NO deben repetir campañas o charlas ya realizadas en meses anteriores.
5. Tampoco deben ser demasiado parecidas semánticamente a campañas ya realizadas.
6. Si un tema previo fue phishing, no propongas spear phishing, fraude por correo o suplantación por correo.
7. Si un tema previo fue contraseñas/MFA, no propongas otro sobre credenciales o autenticación segura.
8. Deben ser viables para una campaña mensual empresarial.
9. En el título no uses numeración inicial.
10. Deben priorizar temas prácticos, medibles y alineados a riesgos reales del negocio.
11. "categoria_tema" debe ser una categoría corta y consistente, por ejemplo:
    phishing, ingenieria_social, autenticacion_y_contrasenas,
    informacion_sensible_y_clasificacion, correo_y_mensajeria_segura,
    malware_y_ransomware, control_de_acceso, teletrabajo_y_dispositivos,
    navegacion_y_web_segura, clean_desk_y_entorno_fisico, cultura_general_seguridad.
"""


def camp_conc_build_user_prompt_options(session_date, participants, target_area, exclude_id=None):
    used_topics = camp_conc_get_used_topics(exclude_id=exclude_id)

    if used_topics:
        used_topics_text = "\n".join([
            f"- Título: {x.get('title') or ''} | Categoría: {x.get('category') or ''}"
            for x in used_topics
        ])
    else:
        used_topics_text = "- No hay campañas previas registradas."

    return f"""
Genera 5 opciones de campañas o charlas de concientización en seguridad para GRAC/SGSI.

Datos de entrada:
- Fecha de la campaña mensual: {session_date}
- Número de participantes: {participants}
- Área objetivo: {target_area}

Campañas o charlas ya utilizadas que NO se deben repetir ni parecer demasiado:
{used_topics_text}

Criterios:
- Enfocar las opciones al contexto corporativo y al área indicada.
- Considerar si el grupo es pequeño, mediano o grande.
- El tono debe ser ejecutivo y profesional.
- Debe estar alineado con ISO 27001, cultura de seguridad y toma de conciencia.
- Priorizar campañas con impacto práctico, recordación y posibilidad de seguimiento.
- Evitar el mismo título y temas semánticamente muy similares.
"""


def camp_conc_build_system_prompt_detail():
    return """
Eres un consultor senior experto en ciberseguridad, cultura organizacional, awareness y SGSI.
Debes desarrollar una campaña de concientización COMPLETA, lista para ejecutar en una empresa.

Responde SIEMPRE en JSON válido, sin texto adicional.
La salida debe ser un objeto JSON con estas claves exactas:
- "temario_detallado"
- "plan_de_accion"
- "como_abordarlo"
- "pasos_a_seguir"
- "evaluacion_efectividad"

INSTRUCCIONES OBLIGATORIAS:
1. No entregues respuestas cortas ni genéricas.
2. La campaña debe ser ejecutable y servir como evidencia de auditoría ISO 27001.
3. Debe considerar el área objetivo y el número de participantes.
4. Debe incluir acciones antes, durante y después de la campaña.
5. Debe incluir comunicación, sensibilización, refuerzo y seguimiento.
6. Debe incluir responsables sugeridos, materiales, canales, frecuencia y evidencias.
7. Debe incluir métricas, indicadores, metas y acciones correctivas.
8. Si existe charla, taller o sesión presencial, la actividad principal debe durar máximo 2 horas.
9. Si requiere más profundidad, distribuye el esfuerzo en cápsulas, piezas, refuerzos, simulaciones y seguimiento.
10. En evaluación de efectividad debes incluir pruebas reales controladas cuando apliquen:
    phishing, smishing, ingeniería social, vishing, validación de identidad,
    clasificación de información, manejo seguro de datos o respuesta ante incidentes.
11. Las pruebas deben ser éticas, controladas, autorizadas y documentadas.
"""


def camp_conc_build_user_prompt_detail(row, option):
    return f"""
Desarrolla de forma COMPLETA una campaña de concientización de seguridad para GRAC/SGSI.

DATOS DE ENTRADA:
- Fecha de ejecución: {row['session_date']}
- Número de participantes: {row['participants']}
- Área objetivo: {row['target_area']}
- División objetivo: {row['target_division'] if 'target_division' in row.keys() else ''}
- Tema elegido: {option.get('titulo') or ''}
- Categoría: {option.get('categoria_tema') or ''}
- Objetivo base: {option.get('objetivo') or ''}
- Formato sugerido: {option.get('formato') or ''}
- Duración sugerida: {option.get('duracion_sugerida') or ''}
- Nivel de público: {option.get('nivel_publico') or ''}

NECESITO QUE NO SOLO EXPLIQUES EL TEMA.
NECESITO QUE CONSTRUYAS LA CAMPAÑA COMO TAL.

Incluye como mínimo:
1. Temario detallado y mensajes clave.
2. Plan de acción completo.
3. Cómo abordarla metodológicamente.
4. Pasos antes, durante y después.
5. Evaluación de efectividad.

Además contempla:
- objetivo general,
- objetivos específicos,
- alcance,
- público objetivo,
- duración sugerida,
- cronograma,
- responsables,
- materiales,
- recursos,
- piezas de comunicación,
- canales de difusión,
- actividades de sensibilización,
- actividad principal,
- actividad de refuerzo,
- mecanismos de seguimiento,
- evidencias para auditoría,
- indicadores,
- metas y acciones de mejora.

El resultado debe ser muy detallado, profesional, práctico y listo para ejecutar.
"""


def camp_conc_generate_options(session_date, participants, target_area, exclude_id=None):
    raw = camp_conc_call_ai(
        camp_conc_build_system_prompt_options(),
        camp_conc_build_user_prompt_options(session_date, participants, target_area, exclude_id=exclude_id),
        max_tokens=1600
    )
    data = camp_conc_extract_json(raw)

    if not isinstance(data, list):
        raise ValueError("La IA no devolvió una lista de opciones.")

    cleaned = []
    for item in data[:5]:
        if not isinstance(item, dict):
            continue
        cleaned.append({
            "titulo": str(item.get("titulo") or "").strip(),
            "categoria_tema": str(item.get("categoria_tema") or "").strip(),
            "objetivo": str(item.get("objetivo") or "").strip(),
            "justificacion": str(item.get("justificacion") or "").strip(),
            "formato": str(item.get("formato") or "").strip(),
            "duracion_sugerida": str(item.get("duracion_sugerida") or "").strip(),
            "nivel_publico": str(item.get("nivel_publico") or "").strip(),
        })

    if len(cleaned) == 0:
        raise ValueError("La IA no generó opciones válidas.")

    return cleaned



def camp_conc_build_fallback_detail(row, option, error_msg=""):
    """
    Plan base en caso de timeout de Ollama.
    Permite que el usuario no pierda el flujo y conserve una campaña ejecutable.
    """
    titulo = option.get("titulo") or "Campaña de concientización en seguridad"
    categoria = option.get("categoria_tema") or "cultura_general_seguridad"
    objetivo = option.get("objetivo") or "Fortalecer la toma de conciencia en seguridad de la información."
    formato = option.get("formato") or "Charla/taller práctico"
    duracion = option.get("duracion_sugerida") or "Máximo 2 horas para actividad principal"
    area = row["target_area"] or "Área objetivo"
    division = ""
    try:
        division = row["target_division"] or ""
    except Exception:
        division = ""
    participantes = row["participants"] or 0
    fecha = row["session_date"] or "Fecha por definir"

    return {
        "temario_detallado": {
            "tema": titulo,
            "categoria": categoria,
            "objetivo_general": objetivo,
            "publico_objetivo": f"{area} / {division or 'Todas las divisiones'} - {participantes} participantes",
            "duracion": duracion,
            "mensajes_clave": [
                "La seguridad de la información es responsabilidad de todos.",
                "Las conductas seguras reducen incidentes operativos, reputacionales y regulatorios.",
                "Todo evento sospechoso debe reportarse oportunamente por los canales definidos."
            ],
            "contenidos": [
                "Contexto del riesgo asociado al tema seleccionado.",
                "Buenas prácticas aplicables al rol del área objetivo.",
                "Errores frecuentes y señales de alerta.",
                "Casos prácticos o ejemplos corporativos.",
                "Canales de reporte y responsabilidades del colaborador."
            ]
        },
        "plan_de_accion": {
            "antes": [
                "Definir responsable de la campaña y validar alcance con el líder del área.",
                "Preparar invitación, pieza de comunicación y material de apoyo.",
                "Confirmar fecha, canal, lista de asistentes y evidencias requeridas."
            ],
            "durante": [
                "Realizar apertura con contexto del SGSI y objetivo de la campaña.",
                "Ejecutar actividad principal con duración máxima de 2 horas si es presencial.",
                "Aplicar ejercicios prácticos, preguntas de validación o mini casos.",
                "Registrar asistencia y recopilar dudas o hallazgos."
            ],
            "despues": [
                "Enviar refuerzo con mensajes clave y material de consulta.",
                "Aplicar evaluación de aprendizaje o efectividad.",
                "Consolidar resultados, evidencias y acciones de mejora."
            ],
            "responsables_sugeridos": [
                "Líder SGSI",
                "Gestión Humana / Formación",
                "Líder del área objetivo",
                "Equipo de Seguridad de la Información"
            ]
        },
        "como_abordarlo": {
            "metodologia": "Enfoque práctico, participativo y orientado a comportamientos seguros observables.",
            "canales": [
                "Sesión presencial o virtual",
                "Correo corporativo",
                "Infografía o pieza visual",
                "Intranet o canal interno de comunicaciones"
            ],
            "materiales": [
                "Presentación ejecutiva",
                "Lista de asistencia",
                "Evaluación corta",
                "Guía de buenas prácticas",
                "Evidencia fotográfica o captura de sesión si aplica"
            ],
            "enfoque_por_area": f"Adaptar ejemplos y casos al contexto operativo de {area} y la división {division or 'Todas las divisiones'}."
        },
        "pasos_a_seguir": [
            "Crear cronograma de campaña.",
            "Aprobar contenido con el responsable SGSI.",
            "Convocar participantes.",
            "Ejecutar campaña.",
            "Aplicar evaluación.",
            "Registrar evidencias.",
            "Definir acciones de mejora si el resultado no cumple la meta."
        ],
        "evaluacion_efectividad": {
            "indicadores": [
                "% de asistencia",
                "% de aprobación de evaluación",
                "% de colaboradores que identifican correctamente señales de alerta",
                "Número de reportes oportunos posteriores a la campaña"
            ],
            "metas": [
                "Asistencia mínima del 90%",
                "Aprobación mínima del 80%",
                "Cierre de acciones de mejora en máximo 30 días"
            ],
            "pruebas_controladas": [
                "Aplicar cuestionario práctico posterior a la campaña.",
                "Ejecutar simulación ética y autorizada si el tema lo permite.",
                "Documentar resultados, desviaciones y lecciones aprendidas."
            ],
            "evidencias_a_conservar": [
                "Lista de asistencia",
                "Material presentado",
                "Resultados de evaluación",
                "Comunicaciones enviadas",
                "Acta o registro de ejecución",
                "Acciones correctivas o mejoras"
            ],
            "nota": (
                "Este plan fue generado en modo base porque la IA/Ollama no respondió a tiempo. "
                + (f"Detalle técnico: {error_msg}" if error_msg else "")
            )
        }
    }


def camp_conc_generate_detail(row, option):
    """
    Genera el plan completo.
    Cambio clave:
    Antes llamaba a camp_conc_call_ai() con max_tokens=2500.
    Ahora usa el helper optimizado y, si Ollama se demora, crea un plan base ejecutable
    para que el módulo no se bloquee.
    """
    try:
        raw = camp_conc_call_ai(
            camp_conc_build_system_prompt_detail(),
            camp_conc_build_user_prompt_detail(row, option),
            max_tokens=1600
        )
        data = camp_conc_extract_json(raw)

        if not isinstance(data, dict):
            raise ValueError("La IA no devolvió un plan detallado válido.")

        return data

    except Exception as e:
        # Fallback controlado para evitar que el flujo se rompa por timeout de Ollama.
        return camp_conc_build_fallback_detail(row, option, error_msg=str(e))



def camp_conc_pretty_label(value):
    """
    Convierte claves técnicas o mixtas en etiquetas legibles.
    """
    value = str(value or "").strip()
    if not value:
        return ""

    # Mantiene etiquetas ya escritas con mayúsculas/tildes, pero limpia guiones bajos.
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"\s+", " ", value).strip()

    # Normaliza algunas etiquetas comunes.
    mapa = {
        "titulo": "Título",
        "objetivo": "Objetivo",
        "contenido": "Contenido",
        "fecha": "Fecha",
        "actividad": "Actividad",
        "responsable": "Responsable",
        "materiales": "Materiales",
        "metodologia": "Metodología",
        "canales": "Canales",
        "indicadores": "Indicadores",
        "metas": "Metas",
        "evidencias": "Evidencias",
        "publico objetivo": "Público objetivo",
        "objetivo general": "Objetivo general",
        "objetivos especificos": "Objetivos específicos",
        "objetivos específicos": "Objetivos específicos",
        "duracion": "Duración",
        "duración": "Duración",
        "recursos": "Recursos",
        "cronograma": "Cronograma",
    }

    key = value.lower()
    return mapa.get(key, value[:1].upper() + value[1:])


def camp_conc_format_plain_block(value, indent=0):
    """
    Convierte dict/list/string de la IA en texto ejecutivo legible.
    Evita que el campo descripción del Plan de Concientización quede con JSON crudo.
    """
    tab = "  " * indent

    if value is None:
        return ""

    if isinstance(value, str):
        clean = re.sub(r"\s+", " ", value.strip())
        return clean

    if isinstance(value, (int, float, bool)):
        return str(value)

    if isinstance(value, list):
        lines = []

        for idx, item in enumerate(value, start=1):
            if isinstance(item, dict):
                titulo = (
                    item.get("Título")
                    or item.get("titulo")
                    or item.get("Titulo")
                    or item.get("actividad")
                    or item.get("Actividad")
                    or item.get("nombre")
                    or item.get("Nombre")
                    or f"Punto {idx}"
                )

                lines.append(f"{tab}{idx}. {camp_conc_format_plain_block(titulo)}")

                for k, v in item.items():
                    if str(k).lower() in ("título", "titulo", "nombre"):
                        continue

                    formatted = camp_conc_format_plain_block(v, indent + 1)
                    if formatted:
                        label = camp_conc_pretty_label(k)
                        if "\n" in formatted:
                            lines.append(f"{tab}   {label}:")
                            for line in formatted.splitlines():
                                if line.strip():
                                    lines.append(f"{tab}   {line}")
                        else:
                            lines.append(f"{tab}   {label}: {formatted}")

                lines.append("")

            elif isinstance(item, list):
                nested = camp_conc_format_plain_block(item, indent + 1)
                if nested:
                    lines.append(f"{tab}{idx}.")
                    lines.append(nested)
                    lines.append("")

            else:
                formatted = camp_conc_format_plain_block(item, indent)
                if formatted:
                    lines.append(f"{tab}{idx}. {formatted}")

        return "\n".join(lines).strip()

    if isinstance(value, dict):
        lines = []

        # Si el dict tiene un título principal, lo muestra primero.
        titulo = (
            value.get("Título")
            or value.get("titulo")
            or value.get("Titulo")
            or value.get("tema")
            or value.get("Tema")
        )

        if titulo:
            lines.append(camp_conc_format_plain_block(titulo))
            lines.append("")

        for k, v in value.items():
            if str(k).lower() in ("título", "titulo", "tema"):
                continue

            formatted = camp_conc_format_plain_block(v, indent + 1)
            if not formatted:
                continue

            label = camp_conc_pretty_label(k)

            if isinstance(v, (list, dict)):
                lines.append(f"{tab}{label}:")
                lines.append(formatted)
                lines.append("")
            else:
                lines.append(f"{tab}{label}: {formatted}")

        return "\n".join(lines).strip()

    return str(value).strip()


def camp_conc_text_from_detail(detail):
    """
    Convierte el detalle JSON de la campaña en texto bonito para registrarlo
    en el campo Descripción del Plan de Concientización y Formación.

    Antes se guardaba como JSON crudo:
    [
      {"Título": "...", "Objetivo": "..."}
    ]

    Ahora se guarda como texto ejecutivo:
    1. Título
       Objetivo: ...
       Contenido: ...
    """
    if not detail:
        return ""

    partes = []

    orden = [
        ("TEMARIO DETALLADO", "temario_detallado"),
        ("PLAN DE ACCIÓN", "plan_de_accion"),
        ("CÓMO ABORDARLO", "como_abordarlo"),
        ("PASOS A SEGUIR", "pasos_a_seguir"),
        ("EVALUACIÓN DE EFECTIVIDAD", "evaluacion_efectividad"),
    ]

    for titulo, key in orden:
        val = detail.get(key)
        if not val:
            continue

        texto = camp_conc_format_plain_block(val).strip()

        if texto:
            partes.append(f"{titulo}\n{'=' * len(titulo)}\n{texto}")

    return "\n\n".join(partes).strip()


def camp_conc_duration_to_hours(value):
    """
    Convierte una duración textual de la campaña en horas enteras para el
    módulo Plan de Concientización y Formación.
    """
    text = (value or "").lower().strip()

    # Casos tipo "90 minutos"
    if "min" in text:
        nums = re.findall(r"\d+", text)
        if nums:
            try:
                minutes = int(nums[0])
                return max(1, min(8, round(minutes / 60) or 1))
            except Exception:
                pass

    nums = re.findall(r"\d+", text)
    if nums:
        try:
            h = int(nums[0])
            return max(1, min(h, 8))
        except Exception:
            pass

    return 2


def camp_conc_normalize_plan_area(value):
    """
    Mantiene el área como texto para dirigida_area. Si el módulo destino maneja
    listas cerradas, el usuario podrá ajustar el valor desde edición.
    """
    return (value or "").strip()



# ============================================================
# ENTRADA / MENÚ
# ============================================================

@app.route("/campanias_concientizacion_menu")
@login_required
def campanias_concientizacion_menu():
    user, resp = camp_conc_require_read()
    if resp:
        return resp
    return redirect(url_for("campanias_concientizacion_matriz"))


# ============================================================
# MATRIZ
# ============================================================

@app.route("/campanias_concientizacion")
@app.route("/campanias_concientizacion_matriz")
@login_required
def campanias_concientizacion_matriz():
    user, resp = camp_conc_require_read()
    if resp:
        return resp

    read_only = not camp_conc_can_write(user)

    filtro_estado = (request.args.get("estado") or "").strip()
    filtro_area = (request.args.get("area") or "").strip()
    filtro_division = (request.args.get("division") or "").strip()

    conn = get_camp_conc_db_connection()

    where = []
    params = []

    if filtro_estado:
        where.append("status = ?")
        params.append(filtro_estado)

    if filtro_area:
        where.append("LOWER(target_area) LIKE ?")
        params.append(f"%{filtro_area.lower()}%")

    if filtro_division:
        where.append("LOWER(COALESCE(target_division, '')) LIKE ?")
        params.append(f"%{filtro_division.lower()}%")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    rows = conn.execute(f"""
        SELECT *
        FROM campanias_concientizacion
        {where_sql}
        ORDER BY id DESC
    """, params).fetchall()

    resumen = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'Ejecutada' THEN 1 ELSE 0 END) AS ejecutadas,
            SUM(CASE WHEN status = 'Planificada' THEN 1 ELSE 0 END) AS planificadas,
            SUM(CASE WHEN status = 'En ejecución' THEN 1 ELSE 0 END) AS en_ejecucion
        FROM campanias_concientizacion
    """).fetchone()

    areas = conn.execute("""
        SELECT DISTINCT target_area
        FROM campanias_concientizacion
        WHERE target_area IS NOT NULL AND TRIM(target_area) <> ''
        ORDER BY target_area ASC
    """).fetchall()

    divisiones = conn.execute("""
        SELECT DISTINCT target_division
        FROM campanias_concientizacion
        WHERE target_division IS NOT NULL AND TRIM(target_division) <> ''
        ORDER BY target_division ASC
    """).fetchall()

    conn.close()

    total = int(resumen["total"] or 0)
    ejecutadas = int(resumen["ejecutadas"] or 0)
    planificadas = int(resumen["planificadas"] or 0)
    en_ejecucion = int(resumen["en_ejecucion"] or 0)
    cumplimiento = round((ejecutadas / total) * 100, 1) if total else 0

    rows_html = []

    for r in rows:
        acciones = [
            f"""
            <a href="{url_for('campanias_concientizacion_detalle', id=r['id'])}"
               class="btn btn-info btn-sm rounded-pill campmat-btn-action text-white fw-bold"
               data-no-progress="true">
              Ver detalle
            </a>
            """
        ]

        if not read_only:
            acciones.append(
                f"""
                <a href="{url_for('campanias_concientizacion_opciones', id=r['id'])}"
                   class="btn btn-primary btn-sm rounded-pill campmat-btn-action fw-bold">
                  Opciones AI
                </a>
                """
            )
            acciones.append(
                f"""
                <a href="{url_for('campanias_concientizacion_edit', id=r['id'])}"
                   class="btn btn-warning btn-sm rounded-pill campmat-btn-action text-dark fw-bold"
                   data-no-progress="true">
                  Editar
                </a>
                """
            )

            if r["plan_diseno_id"]:
                acciones.append(
                    f"""
                    <a href="{url_for('plan_diseno_edit', id=r['plan_diseno_id'])}"
                       class="btn btn-success btn-sm rounded-pill campmat-btn-action fw-bold"
                       data-no-progress="true"
                       title="Esta campaña ya fue registrada en el Plan de Concientización y Formación">
                      Registrado
                    </a>
                    """
                )
            elif r["selected_title"] and r["detailed_plan_json"]:
                acciones.append(
                    f"""
                    <form method="post"
                          action="{url_for('campanias_concientizacion_registrar_plan_diseno', id=r['id'])}"
                          onsubmit="return confirm('¿Registrar esta campaña en el Plan de Concientización y Formación?');"
                          data-no-progress="true"
                          style="margin:0;">
                      <button type="submit"
                              class="btn btn-success btn-sm rounded-pill campmat-btn-action fw-bold"
                              data-no-progress="true">
                        Registrar
                      </button>
                    </form>
                    """
                )
            else:
                acciones.append(
                    """
                    <button type="button"
                            class="btn btn-secondary btn-sm rounded-pill campmat-btn-action fw-bold"
                            disabled
                            title="Primero debes seleccionar una opción y generar la campaña completa">
                      Registrar
                    </button>
                    """
                )

            acciones.append(
                f"""
                <form method="post"
                      action="{url_for('campanias_concientizacion_delete', id=r['id'])}"
                      onsubmit="return confirm('¿Eliminar esta campaña de concientización?');"
                      style="margin:0;">
                  <button type="submit"
                          class="btn btn-danger btn-sm rounded-pill campmat-btn-action fw-bold"
                          data-no-progress="true">
                    Eliminar
                  </button>
                </form>
                """
            )
        else:
            acciones.append('<span class="badge bg-secondary">Solo lectura</span>')

        title = r["selected_title"] or "Sin tema seleccionado"
        category = r["selected_category"] or "—"
        rows_html.append(f"""
        <tr>
          <td class="text-center fw-bold">{escape(str(r['id']))}</td>
          <td class="text-center">{escape(r['session_date'] or '—')}</td>
          <td>{escape(r['target_area'] or '—')}</td>
          <td>{escape(r['target_division'] or '—')}</td>
          <td class="text-center">{escape(str(r['participants'] or 0))}</td>
          <td>
            <div class="campmat-title-topic">{escape(title)}</div>
            <div class="campmat-topic-category">{escape(category)}</div>
          </td>
          <td class="text-center">{Markup(camp_conc_status_badge(r['status']))}</td>
          <td class="text-center campmat-col-acciones">
            <div class="campmat-actions-wrap">
              {''.join(acciones)}
            </div>
          </td>
        </tr>
        """)

    if not rows_html:
        rows_html.append("""
        <tr>
          <td colspan="8" class="text-center text-muted py-5">
            No se encontraron campañas con los filtros aplicados.
          </td>
        </tr>
        """)

    agregar_btn = ""
    if not read_only:
        agregar_btn = f"""
        <a href="{url_for('campanias_concientizacion_new')}"
           class="btn btn-primary rounded-pill px-5 fw-bold">
          ➕ Nueva campaña AI
        </a>
        """

    estados = ["Generada", "Planificada", "En ejecución", "Ejecutada", "Cancelada"]

    html = f"""
    <div class="campmat-shell">

      <div class="campmat-header-card">
        <div class="campmat-header-overlay">
          <div class="campmat-header-text">
            <h3 class="campmat-title m-0">Campañas de Concientización</h3>
            <div class="campmat-subtitle">
              Gestión mensual de campañas de cultura, toma de conciencia y awareness de seguridad alineadas con ISO 27001
            </div>
          </div>
        </div>
      </div>

      <div class="campmat-header-actions">
        {agregar_btn}
      </div>

      <div class="campmat-kpi-grid">
        <div class="campmat-kpi-card">
          <div class="campmat-kpi-label">Total campañas</div>
          <div class="campmat-kpi-value">{total}</div>
        </div>
        <div class="campmat-kpi-card">
          <div class="campmat-kpi-label">Planificadas</div>
          <div class="campmat-kpi-value">{planificadas}</div>
        </div>
        <div class="campmat-kpi-card">
          <div class="campmat-kpi-label">En ejecución</div>
          <div class="campmat-kpi-value">{en_ejecucion}</div>
        </div>
        <div class="campmat-kpi-card">
          <div class="campmat-kpi-label">% Ejecutadas</div>
          <div class="campmat-kpi-value">{cumplimiento}%</div>
        </div>
      </div>

      <div class="campmat-filter-card">
        <form method="get">
          <div class="row g-2 align-items-end">
            <div class="col-md-3">
              <label class="form-label fw-bold">Estado</label>
              <select name="estado" class="form-select">
                <option value="">-- Todos --</option>
                {''.join([f'<option value="{escape(e)}" {"selected" if filtro_estado == e else ""}>{escape(e)}</option>' for e in estados])}
              </select>
            </div>
            <div class="col-md-3">
              <label class="form-label fw-bold">Área</label>
              <select name="area" class="form-select">
                <option value="">-- Todas --</option>
                {''.join([f'<option value="{escape(a["target_area"])}" {"selected" if filtro_area == a["target_area"] else ""}>{escape(a["target_area"])}</option>' for a in areas])}
              </select>
            </div>
            <div class="col-md-3">
              <label class="form-label fw-bold">División</label>
              <select name="division" class="form-select">
                <option value="">-- Todas --</option>
                {''.join([f'<option value="{escape(d["target_division"])}" {"selected" if filtro_division == d["target_division"] else ""}>{escape(d["target_division"])}</option>' for d in divisiones])}
              </select>
            </div>
            <div class="col-md-3">
              <div class="d-flex gap-2 flex-wrap">
                <button class="btn btn-primary rounded-pill px-4 fw-bold" type="submit">Filtrar</button>
                <a class="btn btn-secondary rounded-pill px-4 fw-bold" href="{url_for('campanias_concientizacion_matriz')}" data-no-progress="true">Limpiar</a>
              </div>
            </div>
          </div>
        </form>
      </div>

      <div class="campmat-card">
        <div class="campmat-topbar">
          <div>
            <h5 class="campmat-top-title mb-1">Matriz de campañas</h5>
            <div class="campmat-top-note">
              Cada registro puede generar 5 opciones con AI y convertir una opción en campaña completa ejecutable.
            </div>
          </div>
          <div class="campmat-counter-badge">Total registros: {len(rows)}</div>
        </div>

        <div class="campmat-card-body">
          <div class="table-responsive campmat-table-wrap">
            <table class="table table-bordered table-hover align-middle mb-0 campmat-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Fecha</th>
                  <th>Área objetivo</th>
                  <th>División</th>
                  <th>Participantes</th>
                  <th>Tema seleccionado</th>
                  <th>Estado</th>
                  <th class="campmat-col-acciones">Acciones</th>
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

    {camp_conc_common_css("campmat")}
    """

    return render_template_string(BASE, content=Markup(html))


# ============================================================
# NUEVA CAMPAÑA — GENERA 5 OPCIONES
# ============================================================

@app.route("/campanias_concientizacion/new", methods=["GET", "POST"])
@login_required
def campanias_concientizacion_new():
    user, resp = camp_conc_require_write()
    if resp:
        return resp

    if request.method == "POST":
        session_date = (request.form.get("session_date") or "").strip()
        participants_raw = (request.form.get("participants") or "").strip()
        target_area = (request.form.get("target_area") or "").strip()
        target_division = (request.form.get("target_division") or "").strip()

        if not session_date or not participants_raw or not target_area or not target_division:
            flash("Campos obligatorios: fecha, participantes, área objetivo y división.", "danger")
            return redirect(url_for("campanias_concientizacion_new"))

        try:
            participants = int(participants_raw)
            if participants <= 0:
                raise ValueError()
        except Exception:
            flash("El número de participantes debe ser numérico y mayor a cero.", "danger")
            return redirect(url_for("campanias_concientizacion_new"))

        try:
            options = camp_conc_generate_options(session_date, participants, target_area)

            conn = get_camp_conc_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO campanias_concientizacion (
                    session_date, participants, target_area, target_division,
                    generated_options_json, status, created_by, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_date,
                participants,
                target_area,
                target_division,
                json.dumps(options, ensure_ascii=False),
                "Generada",
                camp_conc_user_name(user),
                camp_conc_now(),
                camp_conc_now()
            ))
            session_id = cur.lastrowid
            conn.commit()
            conn.close()

            flash("Las 5 opciones de campaña fueron generadas correctamente.", "success")
            return redirect(url_for("campanias_concientizacion_opciones", id=session_id))

        except Exception as e:
            flash(f"No fue posible generar las opciones con AI: {str(e)}", "danger")
            return redirect(url_for("campanias_concientizacion_new"))

    areas_org, divisiones_por_area = camp_conc_obtener_areas_y_divisiones()
    area_options = camp_conc_area_options(areas_org)
    division_options = camp_conc_division_options(divisiones_por_area)

    html = f"""
    <div class="campform-shell">

      <div class="campform-header-card">
        <div class="campform-header-overlay">
          <div class="campform-header-text">
            <h3 class="campform-title m-0">Nueva Campaña de Concientización</h3>
            <div class="campform-subtitle">
              Genera 5 opciones de campañas mensuales con AI, evitando repetir temas ya ejecutados o demasiado similares
            </div>
          </div>
        </div>
      </div>

      <div class="campform-header-actions">
        <a href="{url_for('campanias_concientizacion_matriz')}"
           class="btn rounded-pill px-5 fw-bold campform-back-btn" data-no-progress="true">
          ⬅ Volver a la matriz
        </a>
      </div>

      <div class="campform-card">
        <div class="campform-card-body">
          <form method="post" data-progress-text="Generando 5 opciones de campaña con AI...">
            <div class="row g-3">
              <div class="col-12">
                <div class="campform-section-title">Datos base de la campaña mensual</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha de concientización</label>
                <input type="date" name="session_date" class="form-control" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Número de participantes</label>
                <input type="number" name="participants" class="form-control" min="1" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Área a concientizar</label>
                <select name="target_area" id="target_area" class="form-select" required>
                  {area_options}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">División a concientizar</label>
                <select name="target_division" id="target_division" class="form-select" data-selected="" required>
                  {division_options}
                </select>
              </div>

              <div class="col-12">
                <div class="campform-info-box">
                  La AI considerará campañas previas registradas para evitar repetición de temas como phishing,
                  credenciales, ingeniería social u otros temas similares ya utilizados.
                </div>
              </div>
            </div>

            <div class="campform-bottom-actions">
              <button class="btn btn-primary rounded-pill px-5 fw-bold" type="submit">
                🤖 Generar 5 opciones con AI
              </button>
              <a href="{url_for('campanias_concientizacion_matriz')}"
                 class="btn rounded-pill px-5 fw-bold campform-cancel-btn" data-no-progress="true">
                Cancelar
              </a>
            </div>
          </form>
        </div>
      </div>
    </div>

    {camp_conc_area_division_js(divisiones_por_area)}
    {camp_conc_common_css("campform")}
    """

    return render_template_string(BASE, content=Markup(html))


# ============================================================
# OPCIONES AI
# ============================================================

@app.route("/campanias_concientizacion/<int:id>/opciones", methods=["GET"])
@login_required
def campanias_concientizacion_opciones(id):
    user, resp = camp_conc_require_read()
    if resp:
        return resp

    read_only = not camp_conc_can_write(user)
    row = camp_conc_fetch_one(id)
    if not row:
        flash("No se encontró la campaña.", "danger")
        return redirect(url_for("campanias_concientizacion_matriz"))

    options = camp_conc_parse_json(row["generated_options_json"], default=[])

    cards = []

    for idx, opt in enumerate(options):
        if not isinstance(opt, dict):
            continue

        selected = row["selected_option_index"] == idx
        selected_badge = '<span class="badge bg-success">Seleccionada</span>' if selected else ""

        action = ""
        if not read_only:
            action = f"""
            <form method="post"
                  action="{url_for('campanias_concientizacion_select', id=row['id'])}"
                  data-progress-text="Generando campaña completa con AI..."
                  class="mt-3">
              <input type="hidden" name="option_index" value="{idx}">
              <button class="btn btn-primary rounded-pill px-4 fw-bold w-100" type="submit">
                ✅ Seleccionar y generar campaña completa
              </button>
            </form>
            """

        cards.append(f"""
        <div class="col-lg-6">
          <div class="campopt-card h-100">
            <div class="d-flex justify-content-between gap-2 align-items-start">
              <div class="campopt-card-title">{escape(opt.get('titulo') or 'Sin título')}</div>
              {selected_badge}
            </div>
            <div class="campopt-chip">{escape(opt.get('categoria_tema') or 'Sin categoría')}</div>

            <div class="campopt-block">
              <div class="campopt-label">Objetivo</div>
              <div class="campopt-text">{escape(opt.get('objetivo') or '—')}</div>
            </div>

            <div class="campopt-block">
              <div class="campopt-label">Justificación</div>
              <div class="campopt-text">{escape(opt.get('justificacion') or '—')}</div>
            </div>

            <div class="campopt-meta">
              <span>Formato: {escape(opt.get('formato') or '—')}</span>
              <span>Duración: {escape(opt.get('duracion_sugerida') or '—')}</span>
              <span>Nivel: {escape(opt.get('nivel_publico') or '—')}</span>
            </div>

            {action}
          </div>
        </div>
        """)

    if not cards:
        cards.append("""
        <div class="col-12">
          <div class="alert alert-warning mb-0">No hay opciones generadas para esta campaña.</div>
        </div>
        """)

    regen_btn = ""
    if not read_only:
        regen_btn = f"""
        <form method="post"
              action="{url_for('campanias_concientizacion_regenerar_opciones', id=row['id'])}"
              data-progress-text="Regenerando 5 opciones de campaña con AI..."
              style="display:inline;">
          <button class="btn btn-warning rounded-pill px-4 fw-bold" type="submit">
            🔄 Regenerar opciones
          </button>
        </form>
        """

    detail_btn = ""
    if row["detailed_plan_json"]:
        detail_btn = f"""
        <a href="{url_for('campanias_concientizacion_detalle', id=row['id'])}"
           class="btn btn-info text-white rounded-pill px-4 fw-bold" data-no-progress="true">
          Ver campaña completa
        </a>
        """

    html = f"""
    <div class="campopt-shell">

      <div class="campopt-header-card">
        <div class="campopt-header-overlay">
          <div class="campopt-header-text">
            <h3 class="campopt-title m-0">Opciones de Campaña AI</h3>
            <div class="campopt-subtitle">
              Selecciona una opción para convertirla en campaña completa, ejecutable y auditable
            </div>
          </div>
        </div>
      </div>

      <div class="campopt-header-actions">
        <a href="{url_for('campanias_concientizacion_matriz')}"
           class="btn rounded-pill px-4 fw-bold campopt-back-btn" data-no-progress="true">
          ⬅ Volver a la matriz
        </a>
        {detail_btn}
        {regen_btn}
      </div>

      <div class="campopt-summary">
        <div><strong>Fecha:</strong> {escape(row['session_date'] or '—')}</div>
        <div><strong>Área:</strong> {escape(row['target_area'] or '—')}</div>
        <div><strong>División:</strong> {escape(row['target_division'] or '—')}</div>
        <div><strong>Participantes:</strong> {escape(str(row['participants'] or 0))}</div>
        <div><strong>Estado:</strong> {Markup(camp_conc_status_badge(row['status']))}</div>
      </div>

      <div class="row g-3">
        {''.join(cards)}
      </div>
    </div>

    {camp_conc_common_css("campopt")}
    """

    return render_template_string(BASE, content=Markup(html))


@app.route("/campanias_concientizacion/<int:id>/regenerar_opciones", methods=["POST"])
@login_required
def campanias_concientizacion_regenerar_opciones(id):
    user, resp = camp_conc_require_write()
    if resp:
        return resp

    row = camp_conc_fetch_one(id)
    if not row:
        flash("No se encontró la campaña.", "danger")
        return redirect(url_for("campanias_concientizacion_matriz"))

    try:
        options = camp_conc_generate_options(
            row["session_date"],
            int(row["participants"] or 0),
            row["target_area"],
            exclude_id=id
        )

        conn = get_camp_conc_db_connection()
        conn.execute("""
            UPDATE campanias_concientizacion
            SET generated_options_json = ?,
                selected_option_index = NULL,
                selected_title = NULL,
                selected_category = NULL,
                selected_format = NULL,
                selected_duration = NULL,
                selected_level = NULL,
                selected_objective = NULL,
                selected_justification = NULL,
                detailed_plan_json = NULL,
                status = 'Generada',
                updated_at = ?
            WHERE id = ?
        """, (json.dumps(options, ensure_ascii=False), camp_conc_now(), id))
        conn.commit()
        conn.close()

        flash("Opciones regeneradas correctamente.", "success")
    except Exception as e:
        flash(f"No fue posible regenerar opciones: {str(e)}", "danger")

    return redirect(url_for("campanias_concientizacion_opciones", id=id))


@app.route("/campanias_concientizacion/<int:id>/seleccionar", methods=["POST"])
@login_required
def campanias_concientizacion_select(id):
    user, resp = camp_conc_require_write()
    if resp:
        return resp

    row = camp_conc_fetch_one(id)
    if not row:
        flash("No se encontró la campaña.", "danger")
        return redirect(url_for("campanias_concientizacion_matriz"))

    try:
        option_index = int(request.form.get("option_index"))
    except Exception:
        flash("Opción inválida.", "danger")
        return redirect(url_for("campanias_concientizacion_opciones", id=id))

    options = camp_conc_parse_json(row["generated_options_json"], default=[])

    if option_index < 0 or option_index >= len(options):
        flash("La opción seleccionada no existe.", "danger")
        return redirect(url_for("campanias_concientizacion_opciones", id=id))

    option = options[option_index]

    try:
        detail = camp_conc_generate_detail(row, option)

        conn = get_camp_conc_db_connection()
        conn.execute("""
            UPDATE campanias_concientizacion
            SET selected_option_index = ?,
                selected_title = ?,
                selected_category = ?,
                selected_format = ?,
                selected_duration = ?,
                selected_level = ?,
                selected_objective = ?,
                selected_justification = ?,
                detailed_plan_json = ?,
                status = 'Planificada',
                updated_at = ?
            WHERE id = ?
        """, (
            option_index,
            option.get("titulo") or "",
            option.get("categoria_tema") or "",
            option.get("formato") or "",
            option.get("duracion_sugerida") or "",
            option.get("nivel_publico") or "",
            option.get("objetivo") or "",
            option.get("justificacion") or "",
            json.dumps(detail, ensure_ascii=False),
            camp_conc_now(),
            id
        ))
        conn.commit()
        conn.close()

        flash("Campaña completa generada correctamente.", "success")
        return redirect(url_for("campanias_concientizacion_detalle", id=id))

    except Exception as e:
        flash(f"No fue posible generar la campaña completa con IA: {str(e)}", "danger")
        return redirect(url_for("campanias_concientizacion_opciones", id=id))


# ============================================================
# DETALLE
# ============================================================

@app.route("/campanias_concientizacion/<int:id>/detalle", methods=["GET"])
@login_required
def campanias_concientizacion_detalle(id):
    user, resp = camp_conc_require_read()
    if resp:
        return resp

    read_only = not camp_conc_can_write(user)
    row = camp_conc_fetch_one(id)
    if not row:
        flash("No se encontró la campaña.", "danger")
        return redirect(url_for("campanias_concientizacion_matriz"))

    detail = camp_conc_parse_json(row["detailed_plan_json"], default={})

    if not detail:
        detail_html = """
        <div class="alert alert-warning mb-0">
          Esta campaña aún no tiene plan completo generado. Ingresa a <strong>Opciones AI</strong> y selecciona una opción.
        </div>
        """
    else:
        sections = [
            ("Temario detallado", "temario_detallado"),
            ("Plan de acción", "plan_de_accion"),
            ("Cómo abordarlo", "como_abordarlo"),
            ("Pasos a seguir", "pasos_a_seguir"),
            ("Evaluación de efectividad", "evaluacion_efectividad"),
        ]

        section_html = []
        for title, key in sections:
            section_html.append(f"""
            <div class="campdet-section">
              <div class="campdet-section-title">{escape(title)}</div>
              <div class="campdet-section-body">{camp_conc_format_value(detail.get(key))}</div>
            </div>
            """)
        detail_html = "".join(section_html)

    edit_btn = ""
    regen_btn = ""
    if not read_only:
        edit_btn = f"""
        <a href="{url_for('campanias_concientizacion_edit', id=row['id'])}"
           class="btn btn-warning rounded-pill px-4 fw-bold" data-no-progress="true">
          Editar
        </a>
        """
        if row["selected_option_index"] is not None:
            regen_btn = f"""
            <form method="post"
                  action="{url_for('campanias_concientizacion_regenerar_detalle', id=row['id'])}"
                  data-progress-text="Regenerando campaña completa con AI..."
                  style="display:inline;">
              <button class="btn btn-primary rounded-pill px-4 fw-bold" type="submit">
                🔄 Regenerar detalle AI
              </button>
            </form>
            """

    html = f"""
    <div class="campdet-shell">

      <div class="campdet-header-card">
        <div class="campdet-header-overlay">
          <div class="campdet-header-text">
            <h3 class="campdet-title m-0">Detalle de Campaña de Concientización</h3>
            <div class="campdet-subtitle">
              Campaña completa lista para ejecutar y conservar como evidencia de toma de conciencia del SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="campdet-header-actions">
        <a href="{url_for('campanias_concientizacion_matriz')}"
           class="btn rounded-pill px-4 fw-bold campdet-back-btn" data-no-progress="true">
          ⬅ Volver a la matriz
        </a>
        <a href="{url_for('campanias_concientizacion_opciones', id=row['id'])}"
           class="btn btn-info text-white rounded-pill px-4 fw-bold" data-no-progress="true">
          Ver opciones
        </a>
        {edit_btn}
        {regen_btn}
      </div>

      <div class="campdet-card">
        <div class="campdet-card-body">
          <div class="campdet-section">
            <div class="campdet-section-title">Información general</div>
            <div class="row g-3">
              <div class="col-md-3"><div class="campdet-field"><div class="campdet-label">Fecha</div><div class="campdet-value">{escape(row['session_date'] or '—')}</div></div></div>
              <div class="col-md-3"><div class="campdet-field"><div class="campdet-label">Participantes</div><div class="campdet-value">{escape(str(row['participants'] or 0))}</div></div></div>
              <div class="col-md-3"><div class="campdet-field"><div class="campdet-label">Área objetivo</div><div class="campdet-value">{escape(row['target_area'] or '—')}</div></div></div>
              <div class="col-md-3"><div class="campdet-field"><div class="campdet-label">División objetivo</div><div class="campdet-value">{escape(row['target_division'] or '—')}</div></div></div>
              <div class="col-md-3"><div class="campdet-field"><div class="campdet-label">Estado</div><div class="campdet-value">{Markup(camp_conc_status_badge(row['status']))}</div></div></div>

              <div class="col-md-6"><div class="campdet-field"><div class="campdet-label">Tema seleccionado</div><div class="campdet-value fw-bold">{escape(row['selected_title'] or '—')}</div></div></div>
              <div class="col-md-3"><div class="campdet-field"><div class="campdet-label">Categoría</div><div class="campdet-value">{escape(row['selected_category'] or '—')}</div></div></div>
              <div class="col-md-3"><div class="campdet-field"><div class="campdet-label">Formato</div><div class="campdet-value">{escape(row['selected_format'] or '—')}</div></div></div>

              <div class="col-md-6"><div class="campdet-field"><div class="campdet-label">Objetivo</div><div class="campdet-value">{escape(row['selected_objective'] or '—')}</div></div></div>
              <div class="col-md-6"><div class="campdet-field"><div class="campdet-label">Justificación</div><div class="campdet-value">{escape(row['selected_justification'] or '—')}</div></div></div>
            </div>
          </div>

          {detail_html}
        </div>
      </div>
    </div>

    {camp_conc_common_css("campdet")}
    """

    return render_template_string(BASE, content=Markup(html))


@app.route("/campanias_concientizacion/<int:id>/regenerar_detalle", methods=["POST"])
@login_required
def campanias_concientizacion_regenerar_detalle(id):
    user, resp = camp_conc_require_write()
    if resp:
        return resp

    row = camp_conc_fetch_one(id)
    if not row:
        flash("No se encontró la campaña.", "danger")
        return redirect(url_for("campanias_concientizacion_matriz"))

    options = camp_conc_parse_json(row["generated_options_json"], default=[])
    option_index = row["selected_option_index"]

    if option_index is None or option_index < 0 or option_index >= len(options):
        flash("Primero debes seleccionar una opción de campaña.", "warning")
        return redirect(url_for("campanias_concientizacion_opciones", id=id))

    try:
        option = options[option_index]
        detail = camp_conc_generate_detail(row, option)

        conn = get_camp_conc_db_connection()
        conn.execute("""
            UPDATE campanias_concientizacion
            SET detailed_plan_json = ?, updated_at = ?
            WHERE id = ?
        """, (json.dumps(detail, ensure_ascii=False), camp_conc_now(), id))
        conn.commit()
        conn.close()

        flash("Detalle AI regenerado correctamente.", "success")
    except Exception as e:
        flash(f"No fue posible regenerar el detalle con IA: {str(e)}", "danger")

    return redirect(url_for("campanias_concientizacion_detalle", id=id))


# ============================================================
# EDITAR
# ============================================================

@app.route("/campanias_concientizacion/<int:id>/edit", methods=["GET", "POST"])
@login_required
def campanias_concientizacion_edit(id):
    user, resp = camp_conc_require_write()
    if resp:
        return resp

    row = camp_conc_fetch_one(id)
    if not row:
        flash("No se encontró la campaña.", "danger")
        return redirect(url_for("campanias_concientizacion_matriz"))

    if request.method == "POST":
        session_date = (request.form.get("session_date") or "").strip()
        participants_raw = (request.form.get("participants") or "").strip()
        target_area = (request.form.get("target_area") or "").strip()
        target_division = (request.form.get("target_division") or "").strip()
        selected_title = (request.form.get("selected_title") or "").strip()
        selected_category = (request.form.get("selected_category") or "").strip()
        selected_format = (request.form.get("selected_format") or "").strip()
        selected_duration = (request.form.get("selected_duration") or "").strip()
        selected_level = (request.form.get("selected_level") or "").strip()
        status = (request.form.get("status") or "").strip()

        if not session_date or not participants_raw or not target_area or not target_division or not status:
            flash("Campos obligatorios: fecha, participantes, área objetivo, división y estado.", "danger")
            return redirect(url_for("campanias_concientizacion_edit", id=id))

        try:
            participants = int(participants_raw)
            if participants <= 0:
                raise ValueError()
        except Exception:
            flash("Participantes debe ser numérico y mayor a cero.", "danger")
            return redirect(url_for("campanias_concientizacion_edit", id=id))

        conn = get_camp_conc_db_connection()
        conn.execute("""
            UPDATE campanias_concientizacion
            SET session_date = ?,
                participants = ?,
                target_area = ?,
                target_division = ?,
                selected_title = ?,
                selected_category = ?,
                selected_format = ?,
                selected_duration = ?,
                selected_level = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            session_date,
            participants,
            target_area,
            target_division,
            selected_title,
            selected_category,
            selected_format,
            selected_duration,
            selected_level,
            status,
            camp_conc_now(),
            id
        ))
        conn.commit()
        conn.close()

        flash("Campaña actualizada correctamente.", "success")
        return redirect(url_for("campanias_concientizacion_detalle", id=id))

    estados = ["Generada", "Planificada", "En ejecución", "Ejecutada", "Cancelada"]
    areas_org, divisiones_por_area = camp_conc_obtener_areas_y_divisiones()
    area_options = camp_conc_area_options(areas_org, row["target_area"] or "")
    division_options = camp_conc_division_options(divisiones_por_area, row["target_area"] or "", row["target_division"] or "")

    html = f"""
    <div class="campform-shell">

      <div class="campform-header-card">
        <div class="campform-header-overlay">
          <div class="campform-header-text">
            <h3 class="campform-title m-0">Editar Campaña de Concientización</h3>
            <div class="campform-subtitle">
              Actualiza datos principales, estado y tema seleccionado de la campaña
            </div>
          </div>
        </div>
      </div>

      <div class="campform-header-actions">
        <a href="{url_for('campanias_concientizacion_detalle', id=row['id'])}"
           class="btn rounded-pill px-5 fw-bold campform-back-btn" data-no-progress="true">
          ⬅ Volver al detalle
        </a>
      </div>

      <div class="campform-card">
        <div class="campform-card-body">
          <form method="post">
            <div class="row g-3">
              <div class="col-12">
                <div class="campform-section-title">Información general</div>
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha de concientización</label>
                <input type="date" name="session_date" class="form-control" value="{escape(row['session_date'] or '')}" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Número de participantes</label>
                <input type="number" name="participants" class="form-control" min="1" value="{escape(str(row['participants'] or 0))}" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Área objetivo</label>
                <select name="target_area" id="target_area" class="form-select" required>
                  {area_options}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">División objetivo</label>
                <select name="target_division" id="target_division" class="form-select" data-selected="{escape(row['target_division'] or '')}" required>
                  {division_options}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Estado</label>
                <select name="status" class="form-select" required>
                  {''.join([f'<option value="{escape(e)}" {"selected" if (row["status"] or "") == e else ""}>{escape(e)}</option>' for e in estados])}
                </select>
              </div>

              <div class="col-md-8">
                <label class="form-label">Tema seleccionado</label>
                <input type="text" name="selected_title" class="form-control" value="{escape(row['selected_title'] or '')}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Categoría</label>
                <input type="text" name="selected_category" class="form-control" value="{escape(row['selected_category'] or '')}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Formato</label>
                <input type="text" name="selected_format" class="form-control" value="{escape(row['selected_format'] or '')}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Duración sugerida</label>
                <input type="text" name="selected_duration" class="form-control" value="{escape(row['selected_duration'] or '')}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Nivel público</label>
                <input type="text" name="selected_level" class="form-control" value="{escape(row['selected_level'] or '')}">
              </div>
            </div>

            <div class="campform-bottom-actions">
              <button class="btn btn-success rounded-pill px-5 fw-bold" type="submit">
                Guardar cambios
              </button>
              <a href="{url_for('campanias_concientizacion_detalle', id=row['id'])}"
                 class="btn rounded-pill px-5 fw-bold campform-cancel-btn" data-no-progress="true">
                Cancelar
              </a>
            </div>
          </form>
        </div>
      </div>
    </div>

    {camp_conc_area_division_js(divisiones_por_area)}
    {camp_conc_common_css("campform")}
    """

    return render_template_string(BASE, content=Markup(html))



# ============================================================
# REGISTRAR EN PLAN DE CONCIENTIZACIÓN Y FORMACIÓN
# ============================================================

@app.route("/campanias_concientizacion/<int:id>/registrar_plan_diseno", methods=["POST"])
@login_required
def campanias_concientizacion_registrar_plan_diseno(id):
    user, resp = camp_conc_require_write()
    if resp:
        return resp

    if user.role != "admin" and not verificar_permiso(user, "Plan de Concientización y Formación"):
        flash("No tiene permiso para registrar información en el Plan de Concientización y Formación.", "danger")
        return redirect(url_for("campanias_concientizacion_matriz"))

    row = camp_conc_fetch_one(id)
    if not row:
        flash("No se encontró la campaña.", "danger")
        return redirect(url_for("campanias_concientizacion_matriz"))

    if row["plan_diseno_id"]:
        flash("Esta campaña ya fue registrada previamente en el Plan de Concientización y Formación.", "warning")
        try:
            return redirect(url_for("plan_diseno_edit", id=row["plan_diseno_id"]))
        except Exception:
            return redirect(url_for("campanias_concientizacion_matriz"))

    if not row["selected_title"] or not row["detailed_plan_json"]:
        flash("Primero debes seleccionar una opción y generar la campaña completa.", "warning")
        return redirect(url_for("campanias_concientizacion_opciones", id=id))

    if "PlanDisenoRegistro" not in globals():
        flash("No fue posible registrar: no se encontró el modelo PlanDisenoRegistro en Programasgsi2.py.", "danger")
        return redirect(url_for("campanias_concientizacion_matriz"))

    detail = camp_conc_parse_json(row["detailed_plan_json"], default={})

    descripcion = camp_conc_text_from_detail(detail)
    if not descripcion:
        descripcion = (
            f"Campaña de concientización generada desde GRAC.\\n\\n"
            f"Tema: {row['selected_title'] or ''}\\n"
            f"Objetivo: {row['selected_objective'] or ''}\\n"
            f"Justificación: {row['selected_justification'] or ''}"
        )

    horas = camp_conc_duration_to_hours(row["selected_duration"])

    try:
        it = PlanDisenoRegistro(
            tema_capacitacion=(row["selected_title"] or "").strip(),
            descripcion=descripcion,
            horas=horas,
            dirigida_area=camp_conc_normalize_plan_area(row["target_area"]),
            dirigida_division=(row["target_division"] or "").strip(),
            fecha_programada=(row["session_date"] or "").strip(),
            fecha_ejecucion="",
            responsable=camp_conc_user_name(user),
            metodologia=(row["selected_format"] or "Campaña de concientización").strip(),
            evidencia="",
            observaciones=(
                "Registro generado automáticamente desde el módulo Campañas de Concientización. "
                f"ID campaña origen: {row['id']} | "
                f"Categoría: {row['selected_category'] or '—'} | "
                f"División: {row['target_division'] or '—'} | "
                f"Nivel público: {row['selected_level'] or '—'}"
            )
        )

        db.session.add(it)
        db.session.flush()

        plan_id = it.id

        conn = get_camp_conc_db_connection()
        conn.execute("""
            UPDATE campanias_concientizacion
            SET plan_diseno_id = ?,
                registered_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (plan_id, camp_conc_now(), camp_conc_now(), id))
        conn.commit()
        conn.close()

        db.session.commit()

        flash("Campaña registrada correctamente en el Plan de Concientización y Formación.", "success")
        return redirect(url_for("plan_diseno_edit", id=plan_id))

    except Exception as e:
        db.session.rollback()
        flash(f"No fue posible registrar la campaña en el Plan de Concientización y Formación: {str(e)}", "danger")
        return redirect(url_for("campanias_concientizacion_matriz"))


# ============================================================
# ELIMINAR
# ============================================================

@app.route("/campanias_concientizacion/<int:id>/delete", methods=["POST"])
@login_required
def campanias_concientizacion_delete(id):
    user, resp = camp_conc_require_write()
    if resp:
        return resp

    conn = get_camp_conc_db_connection()
    row = conn.execute("SELECT id FROM campanias_concientizacion WHERE id = ?", (id,)).fetchone()

    if not row:
        conn.close()
        flash("No se encontró la campaña.", "warning")
        return redirect(url_for("campanias_concientizacion_matriz"))

    conn.execute("DELETE FROM campanias_concientizacion WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash("Campaña eliminada correctamente.", "success")
    return redirect(url_for("campanias_concientizacion_matriz"))


# ============================================================
# API SIMPLE PARA DASHBOARD / FUTURAS MÉTRICAS
# ============================================================

@app.route("/campanias_concientizacion/api/resumen")
@login_required
def campanias_concientizacion_api_resumen():
    user, resp = camp_conc_require_read()
    if resp:
        return jsonify({"ok": False, "error": "No autorizado"}), 403

    conn = get_camp_conc_db_connection()
    r = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'Ejecutada' THEN 1 ELSE 0 END) AS ejecutadas,
            SUM(CASE WHEN status = 'Planificada' THEN 1 ELSE 0 END) AS planificadas,
            SUM(CASE WHEN status = 'En ejecución' THEN 1 ELSE 0 END) AS en_ejecucion,
            COUNT(DISTINCT target_area) AS areas
        FROM campanias_concientizacion
    """).fetchone()
    conn.close()

    total = int(r["total"] or 0)
    ejecutadas = int(r["ejecutadas"] or 0)

    return jsonify({
        "ok": True,
        "total": total,
        "ejecutadas": ejecutadas,
        "planificadas": int(r["planificadas"] or 0),
        "en_ejecucion": int(r["en_ejecucion"] or 0),
        "areas": int(r["areas"] or 0),
        "cumplimiento": round((ejecutadas / total) * 100, 1) if total else 0
    })


# ============================================================
# CSS COMÚN DEL MÓDULO
# ============================================================

def camp_conc_common_css(prefix):
    return f"""
    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .{prefix}-shell{{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }}

      .{prefix}-header-card{{
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

      .{prefix}-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .{prefix}-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }}

      .{prefix}-header-overlay::before{{
        content:"🎯";
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

      .{prefix}-header-text::before{{
        content:"SGSI · Competencias y Cultura";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .{prefix}-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }}

      .{prefix}-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .{prefix}-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .{prefix}-header-actions .btn,
      .{prefix}-bottom-actions .btn{{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .{prefix}-back-btn,
      .{prefix}-cancel-btn{{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }}

      .{prefix}-back-btn:hover,
      .{prefix}-cancel-btn:hover{{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }}

      .{prefix}-card,
      .{prefix}-filter-card{{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        margin-bottom:14px;
      }}

      .{prefix}-card-body,
      .{prefix}-filter-card{{
        padding:16px;
      }}

      .{prefix}-topbar{{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:16px;
        border-bottom:1px solid #e6eef8;
        flex-wrap:wrap;
      }}

      .{prefix}-top-title{{
        font-weight:950;
        color:#0f172a;
      }}

      .{prefix}-top-note{{
        font-size:.80rem;
        color:#475569;
      }}

      .{prefix}-counter-badge{{
        background:linear-gradient(135deg,#0f172a,#1e3a8a);
        color:#fff;
        border-radius:999px;
        padding:8px 14px;
        font-weight:900;
        font-size:.82rem;
      }}

      .{prefix}-table-wrap{{
        border-radius:16px;
        overflow:auto;
        background:#fff;
        border:1px solid #e2e8f0;
        box-shadow:0 6px 16px rgba(0,0,0,.08);
      }}

      .{prefix}-table{{
        min-width:1250px;
      }}

      .{prefix}-table thead th{{
        background:#3f86d6 !important;
        color:#fff;
        font-weight:900;
        font-size:.78rem;
        text-align:center;
        vertical-align:middle;
      }}

      .{prefix}-table td{{
        font-size:.82rem;
        vertical-align:middle;
      }}

      .{prefix}-actions-wrap{{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
      }}

      .{prefix}-btn-action{{
        min-width:120px;
        font-size:.74rem;
      }}

      .{prefix}-title-topic{{
        font-weight:900;
        color:#0f172a;
        line-height:1.25;
      }}

      .{prefix}-topic-category{{
        display:inline-block;
        margin-top:4px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        color:#0b4a8f;
        border-radius:999px;
        padding:3px 9px;
        font-size:.70rem;
        font-weight:900;
      }}

      .{prefix}-kpi-grid{{
        display:grid;
        grid-template-columns:repeat(4,minmax(0,1fr));
        gap:12px;
        margin-bottom:14px;
      }}

      .{prefix}-kpi-card{{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        border:1px solid rgba(219,230,244,.9);
        box-shadow:0 10px 22px rgba(15,23,42,.16);
        padding:16px;
        text-align:center;
      }}

      .{prefix}-kpi-label{{
        font-size:.68rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
      }}

      .{prefix}-kpi-value{{
        font-size:1.65rem;
        font-weight:950;
        color:#0f172a;
        line-height:1.1;
      }}

      .{prefix}-section-title{{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }}

      .{prefix}-bottom-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
      }}

      .{prefix}-card .form-label,
      .{prefix}-filter-card .form-label{{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }}

      .{prefix}-card .form-control,
      .{prefix}-card .form-select,
      .{prefix}-filter-card .form-control,
      .{prefix}-filter-card .form-select{{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }}

      .{prefix}-card .form-control:focus,
      .{prefix}-card .form-select:focus,
      .{prefix}-filter-card .form-control:focus,
      .{prefix}-filter-card .form-select:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }}

      .{prefix}-info-box{{
        border-radius:14px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:12px 14px;
        color:#334155;
        font-size:.82rem;
        line-height:1.45;
      }}

      .campopt-summary{{
        background:rgba(255,255,255,.96);
        border:1px solid rgba(219,230,244,.9);
        border-radius:18px;
        padding:14px 16px;
        box-shadow:0 10px 22px rgba(15,23,42,.14);
        display:grid;
        grid-template-columns:repeat(4,minmax(0,1fr));
        gap:10px;
        margin-bottom:14px;
        font-size:.82rem;
      }}

      .campopt-card{{
        background:rgba(255,255,255,.97);
        border:1px solid #dbe6f4;
        border-radius:18px;
        padding:16px;
        box-shadow:0 10px 22px rgba(15,23,42,.14);
      }}

      .campopt-card-title{{
        font-weight:950;
        color:#0f172a;
        font-size:1rem;
        line-height:1.25;
      }}

      .campopt-chip{{
        display:inline-block;
        margin:8px 0 10px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        color:#0b4a8f;
        border-radius:999px;
        padding:4px 10px;
        font-size:.72rem;
        font-weight:900;
      }}

      .campopt-block{{
        margin-top:10px;
      }}

      .campopt-label{{
        font-size:.70rem;
        font-weight:950;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.35px;
        margin-bottom:3px;
      }}

      .campopt-text{{
        font-size:.82rem;
        color:#334155;
        line-height:1.42;
      }}

      .campopt-meta{{
        display:flex;
        gap:6px;
        flex-wrap:wrap;
        margin-top:12px;
      }}

      .campopt-meta span{{
        background:#f8fafc;
        border:1px solid #e2e8f0;
        border-radius:999px;
        padding:4px 9px;
        font-size:.70rem;
        font-weight:800;
        color:#475569;
      }}

      .campdet-section{{
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        margin-bottom:14px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }}

      .campdet-section-title{{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }}

      .campdet-field{{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        min-height:86px;
        height:100%;
      }}

      .campdet-label,
      .campdet-struct-key{{
        font-size:.70rem;
        font-weight:950;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }}

      .campdet-value,
      .campdet-section-body,
      .campdet-struct-value{{
        color:#101827;
        font-size:.84rem;
        line-height:1.48;
        word-break:break-word;
      }}

      .campdet-list{{
        margin:4px 0 8px 18px;
        padding:0;
      }}

      .campdet-list li{{
        margin-bottom:6px;
      }}

      .campdet-struct-item{{
        border-left:3px solid #d9eaff;
        padding-left:10px;
        margin:9px 0;
      }}

      @media (max-width:992px){{
        .{prefix}-kpi-grid,
        .campopt-summary{{
          grid-template-columns:repeat(2,minmax(0,1fr));
        }}
      }}

      @media (max-width:768px){{
        .{prefix}-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .{prefix}-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .{prefix}-header-overlay::before{{
          margin:0;
        }}

        .{prefix}-header-actions .btn,
        .{prefix}-bottom-actions .btn{{
          width:100%;
        }}

        .{prefix}-kpi-grid,
        .campopt-summary{{
          grid-template-columns:1fr;
        }}
      }}
    </style>
    """

# ==========================================================================================================================================
#                                                  Fin Módulo de Camapañas de Concientización 
# ==========================================================================================================================================

# =================================================================================================================================================
#                                           Módulo de Plan de Concientización y Formación INGRESO DIRECTO A LA MATRIZ
# =================================================================================================================================================
@app.route('/plan_diseno_menu', methods=['GET'])
@login_required
def plan_diseno_menu():
    user = User.query.get(session.get('user_id'))

    # Permisos correctos
    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Plan de Concientización y Formación"):
        flash("No tiene permiso para acceder al Plan de Concientización y Formación.", "danger")
        return redirect(url_for('capacitacion_menu'))

    return redirect(url_for('plan_diseno_matriz'))


# Alias corto opcional
@app.route('/plan_diseno', methods=['GET'])
@login_required
def plan_diseno_redirect():
    return redirect(url_for('plan_diseno_matriz'))


# =========================
# Obtener áreas y divisiones
# =========================
def obtener_areas_y_divisiones_plan():
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
# AGREGAR — Plan de Concientización y Formación
# =========================
@app.route('/plan_diseno/new', methods=['GET', 'POST'])
@login_required
def plan_diseno_new():

    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros del plan.", "danger")
        return redirect(url_for('plan_diseno_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Plan de Concientización y Formación"):
        flash("No tiene permiso para agregar registros del plan.", "danger")
        return redirect(url_for('plan_diseno_matriz'))

    areas, divisiones_por_area = obtener_areas_y_divisiones_plan()

    if request.method == 'POST':
        it = PlanDisenoRegistro(
            tema_capacitacion=(request.form.get('tema_capacitacion') or '').strip(),
            descripcion=(request.form.get('descripcion') or '').strip(),
            horas=request.form.get('horas', type=int) or 0,
            dirigida_area=(request.form.get('dirigida_area') or '').strip(),
            dirigida_division=(request.form.get('dirigida_division') or '').strip(),
            fecha_programada=request.form.get('fecha_programada') or '',
            fecha_ejecucion=request.form.get('fecha_ejecucion') or '',
            responsable=(request.form.get('responsable') or '').strip(),
            metodologia=(request.form.get('metodologia') or '').strip(),
            evidencia=(request.form.get('evidencia') or '').strip(),
            observaciones=(request.form.get('observaciones') or '').strip(),
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
            path = os.path.join(app.config['UPLOAD_PLAN_DISENO_DIR'], store_name)
            f.save(path)

            ev = PlanDisenoEvidencia(
                registro=it,
                filename=store_name,
                original_name=secure_filename(f.filename),
                mime='application/pdf',
                size=os.path.getsize(path)
            )
            db.session.add(ev)

        db.session.commit()
        flash("Registro del plan guardado.", "success")
        return redirect(url_for('plan_diseno_matriz'))

    html = """
    <div class="plandis-shell">

      <div class="plandis-header-card">
        <div class="plandis-header-overlay">
          <div class="plandis-header-text">
            <h3 class="plandis-title m-0">Agregar Plan de Concientización</h3>
            <div class="plandis-subtitle">
              Registro de actividades del plan de concientización y formación, incluyendo tema, público objetivo, fechas, responsable, metodología y evidencias
            </div>
          </div>
        </div>
      </div>

      <div class="plandis-header-actions">
        <a href="{{ url_for('plan_diseno_matriz') }}"
           class="btn rounded-pill px-5 fw-bold plandis-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="plandis-card">
        <div class="plandis-card-body">
          <form method="post" enctype="multipart/form-data">
            <div class="row g-3">

              <div class="col-12">
                <div class="plandis-section-title">Información de la actividad</div>
              </div>

              <div class="col-md-6">
                <label class="form-label">Tema de la capacitación</label>
                <input class="form-control" name="tema_capacitacion" required>
              </div>

              <div class="col-md-6">
                <label class="form-label"># Horas</label>
                <input type="number" class="form-control" name="horas" min="0" value="0">
              </div>

              <div class="col-md-12">
                <label class="form-label">Descripción</label>
                <textarea class="form-control" name="descripcion" rows="2"></textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Dirigida a (área)</label>
                <select class="form-select" name="dirigida_area" id="dirigida_area" onchange="cargarDivisionesPlan()" required>
                  <option value="">-- Seleccione --</option>
                  <option value="Todas las áreas">Todas las áreas</option>
                  {% for a in areas %}
                    <option value="{{ a }}">{{ a }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Dirigida a (división)</label>
                <select class="form-select" name="dirigida_division" id="dirigida_division" required>
                  <option value="">-- Seleccione --</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha programada</label>
                <input type="date" class="form-control" name="fecha_programada">
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha ejecución</label>
                <input type="date" class="form-control" name="fecha_ejecucion">
              </div>

              <div class="col-md-6">
                <label class="form-label">Responsable</label>
                <input class="form-control" name="responsable">
              </div>

              <div class="col-md-6">
                <label class="form-label">Metodología medición, evaluación y eficacia</label>
                <textarea class="form-control" name="metodologia" rows="2"></textarea>
              </div>

              <div class="col-12">
                <div class="plandis-section-title">Evidencias y observaciones</div>
              </div>

              <div class="col-md-6">
                <label class="form-label">Evidencias PDF (puede adjuntar varios)</label>
                <input
                  type="file"
                  id="evidencias"
                  name="evidencias"
                  accept=".pdf"
                  multiple
                  class="form-control"
                  onchange="acumularEvidencias(this)"
                >
                <small class="text-muted">
                  Puedes seleccionar varios a la vez o ir agregando en varias rondas.
                </small>

                <div id="lista_evidencias_nuevas" class="mt-2"></div>
              </div>

              <div class="col-md-6">
                <label class="form-label">Observaciones</label>
                <textarea class="form-control" name="observaciones" rows="2"></textarea>
              </div>

            </div>

            <div class="plandis-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>

              <a class="btn rounded-pill px-4 fw-bold plandis-cancel-btn"
                 href="{{ url_for('plan_diseno_matriz') }}">
                Cancelar
              </a>
            </div>
          </form>
        </div>
      </div>
    </div>

    <script>
      const DIVISIONES_POR_AREA_PLAN = {{ divisiones_por_area|tojson }};

      function cargarDivisionesPlan() {
        const areaSelect = document.getElementById('dirigida_area');
        const divisionSelect = document.getElementById('dirigida_division');
        const area = (areaSelect.value || '').trim();

        divisionSelect.innerHTML = '';

        const optDefault = document.createElement('option');
        optDefault.value = '';
        optDefault.textContent = '-- Seleccione --';
        divisionSelect.appendChild(optDefault);

        const optTodas = document.createElement('option');
        optTodas.value = 'Todas las divisiones';
        optTodas.textContent = 'Todas las divisiones';
        divisionSelect.appendChild(optTodas);

        if (!area) {
          return;
        }

        if (area === 'Todas las áreas') {
          return;
        }

        const divisiones = DIVISIONES_POR_AREA_PLAN[area] || [];

        divisiones.forEach(function(div) {
          const opt = document.createElement('option');
          opt.value = div;
          opt.textContent = div;
          divisionSelect.appendChild(opt);
        });
      }

      document.addEventListener('DOMContentLoaded', function() {
        cargarDivisionesPlan();
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

      .plandis-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HEADER SGSI UNIFICADO (CORREGIDO)
      ========================= */
      .plandis-header-card{
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

      .plandis-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .plandis-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .plandis-header-overlay::before{
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

      .plandis-header-text{
        max-width:1200px;
      }

      .plandis-header-text::before{
        content:"SGSI · Plan de Disposición";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .plandis-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .plandis-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES SUPERIORES
      ========================= */
      .plandis-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .plandis-header-actions .btn,
      .plandis-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .plandis-back-btn,
      .plandis-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .plandis-back-btn:hover,
      .plandis-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD PRINCIPAL
      ========================= */
      .plandis-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .plandis-card-body{
        padding:18px;
      }

      /* =========================
         FORMULARIOS
      ========================= */
      .plandis-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .plandis-card .form-control,
      .plandis-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .plandis-card textarea.form-control{
        min-height:70px;
      }

      .plandis-card .form-control:focus,
      .plandis-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }

      /* =========================
         SECCIONES
      ========================= */
      .plandis-section-title{
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
         EVIDENCIAS (MEJORADO)
      ========================= */
      #lista_evidencias_nuevas .d-flex{
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
        border:1px solid #dbe6f4;
        border-radius:12px;
        padding:10px 12px;
        box-shadow:0 6px 14px rgba(15,23,42,.08);
      }

      /* =========================
         BOTONES INFERIORES
      ========================= */
      .plandis-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
        width:100%;
      }

      /* =========================
         RESPONSIVE
      ========================= */
      @media (max-width:768px){
        .plandis-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .plandis-header-overlay::before{
          margin:0;
        }

        .plandis-header-actions .btn,
        .plandis-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        areas=areas,
        divisiones_por_area=divisiones_por_area
    )
    return render_template_string(BASE, content=Markup(inner))


# =========================
# MATRIZ — Plan de Concientización y Formación
# =========================
@app.route('/plan_diseno_matriz', methods=['GET'])
@login_required
def plan_diseno_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Plan de Concientización y Formación"):
            flash("No tiene permiso para ver la Matriz del Plan de Concientización y Formación.", "danger")
            return redirect(url_for('capacitacion_menu'))
        read_only = False

    items = (
        PlanDisenoRegistro.query
        .options(selectinload(PlanDisenoRegistro.evidencias))
        .order_by(PlanDisenoRegistro.id.desc())
        .all()
    )

    rows_html = []

    for it in items:
        tema = escape(it.tema_capacitacion or '—')
        fecha_programada = escape(it.fecha_programada or '—')
        fecha_ejecucion = escape(it.fecha_ejecucion or '—')
        responsable = escape(it.responsable or '—')
        metodologia = escape(it.metodologia or '—')

        acciones = [
            f'''
            <a href="{url_for('plan_diseno_detalle', id=it.id)}"
               class="btn btn-info btn-sm rounded-pill plancapmat-btn-action text-white fw-bold"
               data-no-progress="true">
              Ver detalle
            </a>
            '''
        ]

        if not read_only:
            acciones.append(
                f'''
                <a href="{url_for('plan_diseno_edit', id=it.id)}"
                   class="btn btn-warning btn-sm rounded-pill plancapmat-btn-action text-dark fw-bold"
                   data-no-progress="true">
                  Editar
                </a>
                '''
            )

            acciones.append(
                f'''
                <form method="post"
                      action="{url_for('plan_diseno_delete', id=it.id)}"
                      onsubmit="return confirm('¿Desea eliminar este registro?');"
                      style="margin:0;"
                      data-no-progress="true">
                  <button type="submit"
                          class="btn btn-danger btn-sm rounded-pill plancapmat-btn-action fw-bold"
                          data-no-progress="true">
                    Eliminar
                  </button>
                </form>
                '''
            )
        else:
            acciones.append('<span class="badge bg-secondary">Solo lectura</span>')

        rows_html.append(f"""
        <tr>
          <td>{tema}</td>
          <td>{fecha_programada}</td>
          <td>{fecha_ejecucion}</td>
          <td>{responsable}</td>
          <td class="small">{metodologia}</td>
          <td class="text-center plancapmat-col-acciones">
            <div class="plancapmat-actions-wrap">
              {''.join(acciones)}
            </div>
          </td>
        </tr>
        """)

    if not rows_html:
        rows_html.append("""
        <tr>
          <td colspan="6" class="text-center text-muted py-5">
            Sin registros
          </td>
        </tr>
        """)

    agregar_btn_header = ""
    if not read_only:
        agregar_btn_header = f'''
          <a href="{url_for('plan_diseno_new')}"
             class="btn btn-primary rounded-pill fw-bold"
             data-no-progress="true">
            ➕ Agregar registro
          </a>
        '''

    html = f"""
    <div class="plancapmat-shell">

      <div class="plancapmat-header-card">
        <div class="plancapmat-header-overlay">
          <div class="plancapmat-header-text">
            <h3 class="plancapmat-title m-0">Plan de Concientización y Formación</h3>
            <div class="plancapmat-subtitle">
              Visualización resumida de actividades de capacitación, concientización y formación del SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="plancapmat-card">
        <div class="plancapmat-topbar">
          <div>
            <h5 class="plancapmat-top-title mb-1">Resumen de actividades</h5>
            <div class="plancapmat-top-note">
              La matriz muestra los campos principales. Para consultar toda la información usa el botón <strong>Ver detalle</strong>.
            </div>
          </div>

          <div class="d-flex align-items-center gap-2 flex-wrap">
            <div class="plancapmat-counter-badge">
              Total registros: {len(items)}
            </div>
            {agregar_btn_header}
          </div>
        </div>

        <div class="plancapmat-card-body">
          <div class="plancapmat-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-hover align-middle plancapmat-table mb-0">
                <colgroup>
                  <col style="width: 20%;">
                  <col style="width: 12%;">
                  <col style="width: 12%;">
                  <col style="width: 16%;">
                  <col style="width: 24%;">
                  <col style="width: 16%;">
                </colgroup>

                <thead>
                  <tr>
                    <th>Tema de la capacitación</th>
                    <th>Fecha programada</th>
                    <th>Fecha ejecución</th>
                    <th>Responsable</th>
                    <th>Metodología medición, evaluación y eficacia</th>
                    <th class="plancapmat-col-acciones">Acciones</th>
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

    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .plancapmat-shell{{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }}

      .plancapmat-header-card{{
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

      .plancapmat-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .plancapmat-header-overlay{{
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

      .plancapmat-header-overlay::before{{
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
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .plancapmat-header-text{{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .plancapmat-header-text::before{{
        content:"SGSI · Matriz de Plan de Capacitación";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .plancapmat-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }}

      .plancapmat-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .plancapmat-card{{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }}

      .plancapmat-topbar{{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:14px;
        padding:16px 16px 0 16px;
        flex-wrap:wrap;
      }}

      .plancapmat-top-title{{
        color:#0f172a;
        font-weight:950;
        font-size:.92rem;
      }}

      .plancapmat-top-note{{
        color:#475569;
        font-size:.78rem;
      }}

      .plancapmat-counter-badge{{
        background:linear-gradient(135deg,#0f172a,#1e3a8a);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:8px 14px;
        box-shadow:0 8px 18px rgba(0,0,0,.15);
      }}

      .plancapmat-card-body{{
        padding:14px 16px 16px 16px;
      }}

      .plancapmat-table-wrap{{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }}

      .plancapmat-table{{
        min-width:1180px;
        table-layout:fixed;
        margin-bottom:0;
      }}

      .plancapmat-table thead th{{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal;
      }}

      .plancapmat-table th,
      .plancapmat-table td{{
        vertical-align:top;
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
      }}

      .plancapmat-table td{{
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }}

      .plancapmat-table tbody tr:nth-child(even){{
        background:#f8fbff;
      }}

      .plancapmat-table tbody tr:hover{{
        background:#eef6ff;
      }}

      .plancapmat-col-acciones{{
        width:180px !important;
        min-width:180px !important;
        text-align:center;
        vertical-align:middle !important;
      }}

      .plancapmat-actions-wrap{{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }}

      .plancapmat-btn-action,
      .plancapmat-actions-wrap .badge{{
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

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      .btn.rounded-pill{{
        border-radius:10px !important;
      }}

      .plancapmat-card .btn{{
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        font-weight:900;
      }}
    </style>
    """

    return render_template_string(BASE, content=Markup(html))

# ==========================
# Detalle Plan de Concientización y Formación
# ==========================
@app.route('/plan_diseno/detalle/<int:id>')
@login_required
def plan_diseno_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Plan de Concientización y Formación"):
            flash("No tiene permiso para ver el detalle del plan de concientización y formación.", "danger")
            return redirect(url_for('plan_diseno_matriz'))
        read_only = False

    it = (
        PlanDisenoRegistro.query
        .options(selectinload(PlanDisenoRegistro.evidencias))
        .get_or_404(id)
    )

    html = """
    <div class="plancapdet-shell">

      <div class="plancapdet-header-card">
        <div class="plancapdet-header-overlay">
          <div class="plancapdet-header-text">
            <h3 class="plancapdet-title m-0">Detalle del Plan de Concientización y Formación</h3>
            <div class="plancapdet-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="plancapdet-header-actions">
        <a href="{{ url_for('plan_diseno_matriz') }}"
           class="btn rounded-pill px-4 fw-bold plancapdet-back-btn">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('plan_diseno_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="plancapdet-card">
        <div class="plancapdet-card-body">

          <div class="plancapdet-section">
            <div class="plancapdet-section-title">Información general</div>
            <div class="row g-3">

              <div class="col-md-6">
                <div class="plancapdet-field">
                  <div class="plancapdet-label">Tema de la capacitación</div>
                  <div class="plancapdet-value">{{ it.tema_capacitacion or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="plancapdet-field">
                  <div class="plancapdet-label">Horas</div>
                  <div class="plancapdet-value">{{ it.horas if it.horas is not none else '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="plancapdet-field">
                  <div class="plancapdet-label">Responsable</div>
                  <div class="plancapdet-value">{{ it.responsable or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="plancapdet-field">
                  <div class="plancapdet-label">Dirigida a (área)</div>
                  <div class="plancapdet-value">{{ it.dirigida_area or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="plancapdet-field">
                  <div class="plancapdet-label">Dirigida a (división)</div>
                  <div class="plancapdet-value">{{ it.dirigida_division or '—' }}</div>
                </div>
              </div>

              <div class="col-md-2">
                <div class="plancapdet-field">
                  <div class="plancapdet-label">Fecha programada</div>
                  <div class="plancapdet-value">{{ it.fecha_programada or '—' }}</div>
                </div>
              </div>

              <div class="col-md-2">
                <div class="plancapdet-field">
                  <div class="plancapdet-label">Fecha ejecución</div>
                  <div class="plancapdet-value">{{ it.fecha_ejecucion or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <div class="plancapdet-section">
            <div class="plancapdet-section-title">Descripción y seguimiento</div>
            <div class="row g-3">

              <div class="col-12">
                <div class="plancapdet-field">
                  <div class="plancapdet-label">Descripción</div>
                  <div class="plancapdet-value plancapdet-value-lg">{{ it.descripcion or '—' }}</div>
                </div>
              </div>

              <div class="col-12">
                <div class="plancapdet-field">
                  <div class="plancapdet-label">Metodología medición, evaluación y eficacia</div>
                  <div class="plancapdet-value plancapdet-value-lg">{{ it.metodologia or '—' }}</div>
                </div>
              </div>

              <div class="col-12">
                <div class="plancapdet-field">
                  <div class="plancapdet-label">Observaciones</div>
                  <div class="plancapdet-value plancapdet-value-lg">{{ it.observaciones or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <div class="plancapdet-section">
            <div class="plancapdet-section-title">Archivos asociados</div>

            {% if it.evidencias %}
              <div class="plancapdet-ev-grid">
                {% for ev in it.evidencias %}
                  <div class="plancapdet-file-card">
                    <div class="plancapdet-file-left">
                      <div class="plancapdet-file-icon">PDF</div>
                      <div class="plancapdet-file-meta">
                        <div class="plancapdet-file-label">Evidencia</div>
                        <a href="{{ url_for('plan_diseno_evidencia_view', evi_id=ev.id, next='plan_diseno_detalle', reg_id=it.id) }}"
                           class="plancapdet-file-name">
                          {{ ev.original_name }}
                        </a>
                        <div class="plancapdet-file-size">{{ ((ev.size or 0) / 1024)|round(1) }} KB</div>
                      </div>
                    </div>

                    <div>
                      <a href="{{ url_for('plan_diseno_evidencia_view', evi_id=ev.id, next='plan_diseno_detalle', reg_id=it.id) }}"
                         class="btn btn-outline-primary btn-sm rounded-pill px-3">
                        Ver archivo
                      </a>
                    </div>
                  </div>
                {% endfor %}
              </div>
            {% else %}
              <div class="plancapdet-empty-box">
                No hay archivos asociados a este registro.
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

      .plancapdet-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      .plancapdet-header-card{
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

      .plancapdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .plancapdet-header-overlay{
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

      .plancapdet-header-overlay::before{
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

      .plancapdet-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .plancapdet-header-text::before{
        content:"SGSI · Detalle de Plan de Capacitación";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .plancapdet-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .plancapdet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .plancapdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .plancapdet-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .plancapdet-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .plancapdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .plancapdet-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .plancapdet-card-body{
        padding:18px;
      }

      .plancapdet-section{
        margin-bottom:14px;
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .plancapdet-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      .plancapdet-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        min-height:78px;
        height:100%;
      }

      .plancapdet-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .plancapdet-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .plancapdet-value-lg{
        min-height:72px;
      }

      .plancapdet-ev-grid{
        display:grid;
        grid-template-columns:repeat(auto-fit, minmax(320px, 1fr));
        gap:14px;
      }

      .plancapdet-file-card{
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

      .plancapdet-file-card:hover{
        transform:translateY(-3px);
        box-shadow:0 10px 20px rgba(15,23,42,.13);
      }

      .plancapdet-file-left{
        display:flex;
        align-items:center;
        gap:12px;
        min-width:0;
      }

      .plancapdet-file-icon{
        width:52px;
        height:52px;
        min-width:52px;
        border-radius:12px;
        background:linear-gradient(135deg,#b91c1c,#b91c1c);
        color:#fff;
        display:flex;
        align-items:center;
        justify-content:center;
        font-weight:950;
        font-size:.82rem;
      }

      .plancapdet-file-meta{
        min-width:0;
      }

      .plancapdet-file-label{
        font-size:.70rem;
        color:#475569;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
      }

      .plancapdet-file-name{
        display:block;
        font-weight:900;
        color:#1d4ed8;
        text-decoration:none;
        word-break:break-word;
        font-size:.82rem;
        margin-top:2px;
      }

      .plancapdet-file-name:hover{
        text-decoration:underline;
      }

      .plancapdet-file-size{
        font-size:.70rem;
        color:#475569;
        margin-top:3px;
        font-weight:700;
      }

      .plancapdet-empty-box{
        background:#f8fbff;
        border:1px dashed #b8cce8;
        border-radius:14px;
        padding:16px;
        text-align:center;
        color:#475569;
        font-size:.82rem;
        font-weight:800;
      }

      @media (max-width:992px){
        .plancapdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .plancapdet-header-card{
          min-height:88px;
        }

        .plancapdet-title{
          font-size:1.20rem;
        }

        .plancapdet-card-body{
          padding:8px 7px;
        }

        .plancapdet-file-card{
          flex-direction:column;
          align-items:flex-start;
        }
      }

      @media (max-width:768px){
        .plancapdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .plancapdet-header-overlay::before{
          margin:0;
        }

        .plancapdet-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .plancapdet-header-actions .btn{
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

# =========================
# Edición y Borrado del Plan de capacitación
# =========================

