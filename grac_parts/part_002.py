def enviar_credenciales_email(destino, username, password, nombre_completo=None):
    cfg = get_email_config()

    SMTP_HOST = cfg.get("SMTP_HOST")
    SMTP_PORT = int(cfg.get("SMTP_PORT") or 465)
    SMTP_USER = cfg.get("SMTP_USER")
    SMTP_PASS = cfg.get("SMTP_PASS")
    SMTP_FROM = cfg.get("SMTP_FROM") or SMTP_USER
    APP_NAME  = cfg.get("APP_NAME") or "SGSI"

    if not SMTP_HOST:
        raise RuntimeError("Falta SMTP_HOST en la configuración.")
    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("Faltan credenciales SMTP (SMTP_USER/SMTP_PASS).")
    if not destino:
        raise RuntimeError("Correo destino vacío.")

    nombre_saludo = (nombre_completo or username or "").strip()

    msg = EmailMessage()
    msg["Subject"] = f"Credenciales de acceso - {APP_NAME}"
    msg["From"] = SMTP_FROM
    msg["To"] = destino
    msg.set_content(
        f"""Hola {nombre_saludo},

Se ha creado tu usuario en {APP_NAME}.

Usuario: {username}
Contraseña temporal: {password}

Por seguridad, cambia tu contraseña al ingresar.

Saludos,
{APP_NAME}
"""
    )

    context_ssl = ssl._create_unverified_context()

    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context_ssl, timeout=30) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context_ssl)
            smtp.ehlo()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)

# ============================================================================================================================================
#                                                               Fin módulo de envio del password
# ============================================================================================================================================


# ============================================================================================================================================
#                                                               Generar Password Seguro
# ============================================================================================================================================

def generar_password_seguro(longitud=10):
    if longitud < 10:
        raise ValueError("La contraseña debe tener mínimo 10 caracteres")

    mayuscula = secrets.choice(string.ascii_uppercase)
    minuscula = secrets.choice(string.ascii_lowercase)
    digito = secrets.choice(string.digits)
    especial = secrets.choice("!@#$%&*_-+=?")

    resto = ''.join(
        secrets.choice(
            string.ascii_letters + string.digits + "!@#$%&*_-+=?"
        )
        for _ in range(longitud - 4)
    )

    # Mezclar todo
    password_lista = list(mayuscula + minuscula + digito + especial + resto)
    secrets.SystemRandom().shuffle(password_lista)

    return ''.join(password_lista)


# ============================================================================================================================================
#                                                               Fin Generar Password Seguro
# ============================================================================================================================================


# ============================================================================================================================================
#                                                               Módulo de Gestión de Usuarios
# ============================================================================================================================================

MODULES = [
    "Análisis de Riesgos de Procesos con IA",
    "Declaración de Aplicabilidad",
    "Gestión de Riesgos",
    "Objetivos del Sistema de Gestión",
    "Planes de acción del SGSI",
    "Listado Maestro de Documentos",
    "Gestión de Activos de Información",
    "Inventario de Software",
    "Inventario de IA",
    "Inventario de Información",
    "Inventario de Datos Personales",
    "Inventario Físico",
    "Tablas de Valoración",
    "Dueños de Información",
    "Registro de Incidentes",
    "Planes de Respuesta a Incidentes",
    "Centro de Alertas",
    "Configuración Parámetros de la Empresa",
    "Gestión de Cambios (RFC)",
    "Registro de Proveedores",
    "Registro de Comunicaciones",
    "Plan de Concientización y Formación",
    "Seguimiento del Plan de Formación",
    "Campañas de Concientización",
    "Requisitos Legales",
    "Partes Interesadas",
    "Registro de Vulnerabilidades",
    "Pruebas SAST",
    "Modelamiento de Amenazas",
    "Superficie de Ataque y Escenarios",
    "Plan de Remediación",
    "Plan de Competencias",
    "Contexto Interno",
    "Contexto Externo",
    "DOFA",
    "PESI",
    "Informe Revisión por la Dirección",
    "Gestión de Accesos",
    "Continuidad del Negocio (BCP/DRP)",
    "Revisión de Accesos",
    "Cuestionarios de Proponentes",
    "Cuestionario de proveedores web",
    "Listas Restrictivas",
    "Security Scorecard de Terceros",
    "Nivel de madurez ISO 27001:2022",
    "Nivel de Madurez NIST CSF V.2.0",
    "Nivel de Madurez protección de datos personales",
    "Nivel de Madurez PCI-DSS",
    "Nivel de madurez SOC 2",
    "Nivel de Madurez ISO 22301",
    "Nivel de Madurez Gestión de Inteligencia Artificial",
    "Modelamiento de Amenazas",
    "Cumplimiento Continuo",
    "Métricas",
    "Reportes",
    "Logs de Auditoría",
    "Aplicación móvil",
]


# ============================================================
# DB ALTERNA PARA PERFIL DE USUARIOS
# NO MODIFICA LA TABLA user NI sgsi.db
# ============================================================

USUARIOS_PERFIL_DB_PATH = os.path.join(app.instance_path, "usuarios_perfil.db")


def get_usuarios_perfil_db_connection():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(USUARIOS_PERFIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_usuarios_perfil_db():
    conn = get_usuarios_perfil_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios_perfil (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            nombre_completo TEXT,
            fecha_creacion TEXT,
            fecha_actualizacion TEXT
        )
    """)

    conn.commit()
    conn.close()


def obtener_nombre_usuario_alterno(user_id):
    init_usuarios_perfil_db()

    conn = get_usuarios_perfil_db_connection()
    row = conn.execute("""
        SELECT nombre_completo
        FROM usuarios_perfil
        WHERE user_id = ?
    """, (user_id,)).fetchone()
    conn.close()

    return (row["nombre_completo"] if row else "") or ""


def guardar_nombre_usuario_alterno(user_id, nombre_completo):
    init_usuarios_perfil_db()

    nombre_completo = (nombre_completo or "").strip()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_usuarios_perfil_db_connection()
    cur = conn.cursor()

    existe = cur.execute("""
        SELECT id
        FROM usuarios_perfil
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    if existe:
        cur.execute("""
            UPDATE usuarios_perfil
            SET nombre_completo = ?,
                fecha_actualizacion = ?
            WHERE user_id = ?
        """, (nombre_completo, ahora, user_id))
    else:
        cur.execute("""
            INSERT INTO usuarios_perfil (
                user_id,
                nombre_completo,
                fecha_creacion,
                fecha_actualizacion
            )
            VALUES (?, ?, ?, ?)
        """, (user_id, nombre_completo, ahora, ahora))

    conn.commit()
    conn.close()


def eliminar_nombre_usuario_alterno(user_id):
    init_usuarios_perfil_db()

    conn = get_usuarios_perfil_db_connection()
    conn.execute("""
        DELETE FROM usuarios_perfil
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()


def cargar_perfiles_usuarios_alternos():
    init_usuarios_perfil_db()

    conn = get_usuarios_perfil_db_connection()
    rows = conn.execute("""
        SELECT user_id, nombre_completo
        FROM usuarios_perfil
    """).fetchall()
    conn.close()

    return {
        int(r["user_id"]): (r["nombre_completo"] or "")
        for r in rows
    }


init_usuarios_perfil_db()


@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
def usuarios():
    user = User.query.get(session.get('user_id'))

    if (
        user.role != 'admin'
        and user.role != 'gestor_accesos'
        and not verificar_permiso(user, "Gestión de Usuarios")
    ):
        registrar_log(
            user.username if user else "Desconocido",
            "Intento de acceso no autorizado al módulo Gestión de Usuarios."
        )
        flash("No tiene acceso para este módulo.", "danger")
        return redirect(url_for('menu'))

    usuario_actual = User.query.get(session.get('user_id'))
    es_admin = usuario_actual.role == 'admin'
    es_gestor = usuario_actual.role == 'gestor_accesos'

    accion = None

    if request.method == 'POST':
        accion = request.form.get('accion')

        # ======================
        # CREAR
        # ======================
        if accion == 'crear':
            nombre_completo = (request.form.get('nombre_completo') or "").strip()
            role_nuevo = request.form.get('role') or 'user'
            username = (request.form.get('username') or "").strip()
            email = (request.form.get('email') or "").strip().lower()

            if not username or not email:
                flash("Usuario y correo son obligatorios.", "warning")
                return redirect(url_for('usuarios'))

            if User.query.filter_by(username=username).first():
                flash("Ya existe un usuario con ese nombre.", "danger")
                return redirect(url_for('usuarios'))

            if User.query.filter_by(email=email).first():
                flash("Ya existe un usuario con ese correo.", "danger")
                return redirect(url_for('usuarios'))

            password_auto = generar_password_seguro(10)

            u = User(username=username, email=email, role=role_nuevo)
            u.set_password(password_auto)
            db.session.add(u)
            db.session.commit()

            guardar_nombre_usuario_alterno(u.id, nombre_completo)

            registrar_log(
                usuario_actual.username,
                f"Creación de usuario. Usuario creado: {username}. Perfil asignado: {role_nuevo}."
            )

            try:
                nombre_para_correo = obtener_nombre_usuario_alterno(u.id) or username
                enviar_credenciales_email(email, username, password_auto, nombre_para_correo)
                flash("Usuario creado y contraseña enviada al correo.", "success")
            except Exception as e:
                print("Error enviando correo:", repr(e))
                flash(f"Usuario creado, pero falló el envío de correo: {e}", "warning")

        # ======================
        # EDITAR
        # ======================
        elif accion == 'editar' and (es_admin or es_gestor):
            u = User.query.get(int(request.form['id']))

            if not u:
                flash("Usuario no encontrado.", "danger")
                return redirect(url_for('usuarios'))

            username_anterior = u.username or ""
            email_anterior = u.email or ""
            rol_anterior = u.role or ""
            nombre_anterior = obtener_nombre_usuario_alterno(u.id)

            nuevo_nombre_completo = (request.form.get('nombre_completo') or "").strip()
            nuevo_username = (request.form.get('username') or "").strip()
            nuevo_email = (request.form.get('email') or "").strip().lower()
            nuevo_role = request.form.get('role') or u.role

            nueva_password = (
                request.form.get('password_secure') or
                request.form.get('password') or
                ""
            )

            if not nuevo_username:
                flash("El usuario no puede quedar vacío.", "warning")
                return redirect(url_for('usuarios'))

            if not nuevo_email:
                flash("El correo no puede quedar vacío.", "warning")
                return redirect(url_for('usuarios'))

            existe_username = User.query.filter(
                User.username == nuevo_username,
                User.id != u.id
            ).first()

            if existe_username:
                flash("Ya existe otro usuario con ese nombre.", "danger")
                return redirect(url_for('usuarios'))

            existe_email = User.query.filter(
                User.email == nuevo_email,
                User.id != u.id
            ).first()

            if existe_email:
                flash("El correo ya está en uso por otro usuario.", "danger")
                return redirect(url_for('usuarios'))

            u.username = nuevo_username
            u.email = nuevo_email
            u.role = nuevo_role

            if nueva_password:
                u.set_password(nueva_password)

            db.session.commit()

            guardar_nombre_usuario_alterno(u.id, nuevo_nombre_completo)

            cambios = []

            if nombre_anterior != nuevo_nombre_completo:
                cambios.append(f"nombre: '{nombre_anterior}' → '{nuevo_nombre_completo}'")

            if username_anterior != u.username:
                cambios.append(f"usuario: '{username_anterior}' → '{u.username}'")

            if email_anterior != (u.email or ""):
                cambios.append(f"correo: '{email_anterior}' → '{u.email or ''}'")

            if rol_anterior != u.role:
                cambios.append(f"rol: '{rol_anterior}' → '{u.role}'")

            if nueva_password:
                cambios.append("contraseña actualizada")

            detalle_cambios = "; ".join(cambios) if cambios else "sin cambios visibles"

            registrar_log(
                usuario_actual.username,
                f"Modificación de usuario. Usuario afectado: {u.username}. Cambios realizados: {detalle_cambios}."
            )

            flash("Usuario modificado correctamente.", "success")

        # ======================
        # ELIMINAR
        # ======================
        elif accion == 'eliminar' and (es_admin or es_gestor):
            u = User.query.get_or_404(int(request.form['id']))
            username_eliminado = u.username
            rol_eliminado = u.role

            if u.username == 'Administrador':
                registrar_log(
                    usuario_actual.username,
                    "Intento bloqueado de eliminar el usuario Administrador."
                )
                flash("No se puede eliminar el usuario Administrador.", "danger")
                return redirect(url_for('usuarios'))

            UserPermission.query.filter_by(user_id=u.id).delete()
            eliminar_nombre_usuario_alterno(u.id)

            db.session.delete(u)
            db.session.commit()

            registrar_log(
                usuario_actual.username,
                f"Eliminación de usuario. Usuario eliminado: {username_eliminado}. Perfil que tenía: {rol_eliminado}."
            )

            flash("Usuario eliminado.", "info")

        else:
            registrar_log(
                usuario_actual.username,
                f"Acción no permitida en Gestión de Usuarios. Acción intentada: {accion or 'Sin acción'}."
            )
            flash("Acción no permitida.", "warning")

    usuarios = User.query.order_by(User.id.asc()).all()
    perfiles_usuarios = cargar_perfiles_usuarios_alternos()

    content = render_template_string("""
    <div class="users-shell">

      <div class="users-header-card">
        <div class="users-header-overlay">
          <div class="users-header-text">
            <h3 class="users-title m-0">Gestión de Usuarios</h3>
            <div class="users-subtitle">
              Administra usuarios, nombres, correos, roles, contraseñas y permisos
              de acceso dentro del sistema SGSI.
            </div>
          </div>
        </div>
      </div>

      <div class="users-card p-4 mb-4">
        <div class="users-section-title">
          Usuarios registrados
        </div>

        <div class="table-responsive users-table-wrap">
          <table class="table table-bordered align-middle mb-0">
            <thead class="users-table-head">
              <tr class="text-center">
                <th style="width:70px;">N°</th>
                <th>Nombre completo</th>
                <th>Usuario</th>
                <th>Correo</th>
                <th>Rol</th>
                <th style="min-width:300px;">Acciones</th>
              </tr>
            </thead>

            <tbody>
              {% for u in usuarios %}
                <tr>
                  <td class="text-center fw-bold">
                    {{ loop.index }}
                  </td>

                  <td>
                    <input form="f{{u.id}}"
                           name="nombre_completo"
                           value="{{ perfiles_usuarios.get(u.id, '') }}"
                           class="form-control"
                           autocomplete="off"
                           autocorrect="off"
                           autocapitalize="none"
                           spellcheck="false"
                           placeholder="Nombre completo">
                  </td>

                  <td>
                    <input form="f{{u.id}}"
                           name="username"
                           value="{{u.username}}"
                           class="form-control"
                           autocomplete="off"
                           autocorrect="off"
                           autocapitalize="none"
                           spellcheck="false">
                  </td>

                  <td>
                    <input form="f{{u.id}}"
                           name="email"
                           type="email"
                           value="{{u.email or ''}}"
                           class="form-control"
                           autocomplete="off"
                           autocorrect="off"
                           autocapitalize="none"
                           spellcheck="false">
                  </td>

                  <td>
                    <select form="f{{u.id}}" name="role" class="form-select">
                      <option value="user" {% if u.role=='user' %}selected{% endif %}>Usuario</option>
                      <option value="admin" {% if u.role=='admin' %}selected{% endif %}>Administrador</option>
                      <option value="auditor" {% if u.role=='auditor' %}selected{% endif %}>Auditor</option>
                      <option value="gestor_accesos" {% if u.role=='gestor_accesos' %}selected{% endif %}>Gestor de Accesos</option>
                    </select>
                  </td>

                  <td>
                    <input form="f{{u.id}}"
                           name="password_secure"
                           id="password_secure_{{u.id}}"
                           type="password"
                           placeholder="Nueva contraseña"
                           class="form-control mb-2 user-password-secure"
                           autocomplete="new-password"
                           autocorrect="off"
                           autocapitalize="none"
                           spellcheck="false"
                           data-lpignore="true"
                           data-form-type="other"
                           readonly
                           onfocus="this.removeAttribute('readonly');"
                           onblur="this.setAttribute('readonly','readonly');">

                    <div class="d-flex flex-wrap gap-1">
                      {% if current_role in ['admin', 'gestor_accesos'] %}
                        <button form="f{{u.id}}"
                                type="submit"
                                name="accion"
                                value="editar"
                                class="btn btn-sm btn-primary rounded-pill px-3">
                          Guardar
                        </button>

                        <button form="f{{u.id}}"
                                type="submit"
                                name="accion"
                                value="eliminar"
                                class="btn btn-sm btn-danger rounded-pill px-3"
                                onclick="return confirm('¿Seguro que deseas eliminar este usuario?');">
                          Eliminar
                        </button>
                      {% endif %}

                      {% if u.role == 'user' %}
                        <a href="{{ url_for('editar_permisos', user_id=u.id) }}"
                           class="btn btn-sm btn-warning rounded-pill px-3">
                          Permisos
                        </a>
                      {% endif %}
                    </div>

                    <form id="f{{u.id}}"
                          method="post"
                          autocomplete="off"
                          autocorrect="off"
                          autocapitalize="none"
                          spellcheck="false"
                          style="display:none;">
                      <input type="hidden" name="id" value="{{u.id}}">
                    </form>
                  </td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>

        <div class="users-id-note">
          Nota: el campo N° es consecutivo visual. El ID real del usuario se conserva internamente para permisos y relaciones.
        </div>
      </div>

      <div class="users-card p-4">
        <div class="users-section-title">
          Crear nuevo usuario
        </div>

        <form method="post"
              autocomplete="off"
              autocorrect="off"
              autocapitalize="none"
              spellcheck="false">
          <input type="hidden" name="accion" value="crear">

          <div class="users-create-grid">

            <div class="users-field">
              <label class="form-label">Nombre completo</label>
              <input name="nombre_completo"
                     placeholder="Nombre completo"
                     class="form-control"
                     autocomplete="off"
                     autocorrect="off"
                     autocapitalize="none"
                     spellcheck="false">
            </div>

            <div class="users-field">
              <label class="form-label">Usuario</label>
              <input name="username"
                     placeholder="Usuario"
                     class="form-control"
                     autocomplete="off"
                     autocorrect="off"
                     autocapitalize="none"
                     spellcheck="false"
                     required>
            </div>

            <div class="users-field">
              <label class="form-label">Correo del usuario</label>
              <input name="email"
                     type="email"
                     placeholder="Correo del usuario"
                     class="form-control"
                     autocomplete="off"
                     autocorrect="off"
                     autocapitalize="none"
                     spellcheck="false"
                     required>
            </div>

            {% if current_role in ['admin', 'gestor_accesos'] %}
              <div class="users-field users-role-field">
                <label class="form-label">Rol</label>
                <select name="role" class="form-select">
                  <option value="user">Usuario</option>
                  <option value="admin">Administrador</option>
                  <option value="auditor">Auditor</option>
                  <option value="gestor_accesos">Gestor de Accesos</option>
                </select>
              </div>
            {% endif %}

            <div class="users-create-actions">
              <button type="submit" class="btn btn-success users-create-btn">
                Crear Usuario
              </button>
            </div>

          </div>
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

      input::-ms-reveal,
      input::-ms-clear{
        display:none;
      }

      input[type="password"]::-webkit-credentials-auto-fill-button,
      input[type="password"]::-webkit-textfield-decoration-container{
        display:none !important;
        visibility:hidden;
        pointer-events:none;
      }

      .users-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .users-header-card{
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

      .users-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .users-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }

      .users-header-overlay::before{
        content:"👥";
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

      .users-header-text{
        max-width:1000px;
        min-width:0;
      }

      .users-header-text::before{
        content:"SGSI · Administración de Usuarios";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .users-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }

      .users-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        max-width:100%;
      }

      .users-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .users-card.p-4{
        padding:1.5rem !important;
      }

      .users-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
        overflow-wrap:break-word;
      }

      .users-table-wrap{
        border:1px solid #e2ebf5;
        border-radius:14px;
        background:#ffffff;
        overflow-x:auto;
        overflow-y:hidden;
        width:100%;
        max-width:100%;
      }

      .users-table-wrap .table{
        margin-bottom:0;
        min-width:1250px;
      }

      .users-table-head th{
        background:#eef5ff !important;
        color:#0b4a8f !important;
        font-weight:950;
        vertical-align:middle !important;
        border-bottom:1px solid #d7dee7 !important;
        white-space:nowrap;
        font-size:.82rem;
      }

      table td,
      table th{
        vertical-align:middle !important;
      }

      table td{
        font-size:.85rem;
        color:#334155;
      }

      .form-control,
      .form-select{
        border-radius:10px;
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

      .users-id-note{
        margin-top:10px;
        font-size:.74rem;
        color:#475569;
        font-weight:700;
        text-align:right;
      }

      h3{
        color:#ffffff;
        margin:0;
      }

      .users-create-grid{
        display:grid;
        grid-template-columns:minmax(180px,1fr) minmax(180px,1fr) minmax(230px,1fr) minmax(150px,.65fr);
        gap:16px;
        align-items:end;
        width:100%;
        max-width:100%;
      }

      .users-field{
        min-width:0;
        width:100%;
      }

      .users-role-field{
        min-width:0;
      }

      .users-create-actions{
        grid-column:1 / -1;
        width:100%;
        display:flex;
        justify-content:flex-end;
        align-items:center;
        padding-top:4px;
      }

      .users-create-btn{
        width:190px;
        max-width:100%;
        min-height:44px;
        padding:0 22px !important;
        border-radius:12px !important;
        font-weight:950 !important;
        font-size:.92rem;
        display:flex;
        align-items:center;
        justify-content:center;
        white-space:nowrap;
        box-shadow:0 10px 18px rgba(25,135,84,.22) !important;
      }

      @media (max-width:1200px){
        .users-create-grid{
          grid-template-columns:repeat(2,minmax(220px,1fr));
        }
      }

      @media (max-width:992px){
        .users-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .users-title{
          font-size:1.20rem;
          line-height:1.08;
        }

        .users-subtitle{
          font-size:.68rem;
          line-height:1.12;
        }

        .users-card.p-4{
          padding:1rem !important;
        }

        .users-create-actions{
          justify-content:center;
        }

        .users-create-btn{
          width:100%;
        }

        .users-id-note{
          text-align:center;
        }
      }

      @media (max-width:768px){
        .users-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .users-header-overlay::before{
          margin:0;
        }

        .users-title,
        .users-subtitle{
          text-align:center;
        }

        .users-create-grid{
          grid-template-columns:1fr;
        }
      }
    </style>

    <script>
      document.addEventListener('DOMContentLoaded', function(){

        const passwordFields = document.querySelectorAll('.user-password-secure');

        passwordFields.forEach(function(field){

          field.value = '';

          field.setAttribute('type', 'password');
          field.setAttribute('autocomplete', 'new-password');
          field.setAttribute('autocorrect', 'off');
          field.setAttribute('autocapitalize', 'none');
          field.setAttribute('spellcheck', 'false');
          field.setAttribute('data-lpignore', 'true');
          field.setAttribute('data-form-type', 'other');

          setTimeout(function(){
            field.value = '';
          }, 150);

          field.addEventListener('focus', function(){
            this.removeAttribute('readonly');
            this.setAttribute('type', 'password');
            this.setAttribute('autocomplete', 'new-password');
          });

          field.addEventListener('blur', function(){
            this.setAttribute('readonly', 'readonly');
          });

        });

      });
    </script>
    """,
    usuarios=usuarios,
    current_role=usuario_actual.role,
    perfiles_usuarios=perfiles_usuarios)

    return render_template_string(BASE, content=content)


# =========================
# Crear nueva ruta para editar permisos
# =========================

@app.route('/editar_permisos/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_or_access_manager_required
def editar_permisos(user_id):
    user = User.query.get_or_404(user_id)
    usuario_actual = User.query.get(session.get('user_id'))

    if usuario_actual.role == 'gestor_accesos' and user.role != 'user':
        flash("El Gestor de Accesos solo puede gestionar permisos de usuarios con rol 'Usuario'.", "danger")
        return redirect(url_for('usuarios'))

    modules = MODULES

    if request.method == 'POST':
        permisos_seleccionados = request.form.getlist('permisos')

        try:
            UserPermission.query.filter_by(user_id=user.id).delete()

            for module in modules:
                acceso = module in permisos_seleccionados
                nuevo = UserPermission(
                    user_id=user.id,
                    module_name=module,
                    has_access=acceso
                )
                db.session.add(nuevo)

            db.session.commit()
            flash("Permisos actualizados correctamente", "success")
            return redirect(url_for('usuarios'))

        except Exception as e:
            db.session.rollback()
            flash(f"No se pudieron actualizar los permisos: {e}", "danger")

    user_perms = UserPermission.query.filter_by(user_id=user.id, has_access=True).all()
    user_modules = [p.module_name for p in user_perms]

    content = render_template_string("""
    <div class="perm-shell">

      <div class="perm-header-card">
        <div class="perm-header-overlay">
          <div class="perm-header-text">
            <h3 class="perm-title m-0">Editar Permisos</h3>
            <div class="perm-subtitle">
              Administración de módulos habilitados para el usuario {{ user.username }}
            </div>
          </div>
        </div>
      </div>

      <div class="perm-header-actions">
        <a href="{{ url_for('usuarios') }}"
           class="btn rounded-pill px-4 fw-bold perm-back-btn">
          ⬅ Volver a Usuarios
        </a>
      </div>

      <div class="perm-card">
        <div class="perm-card-body">
          <form method="post">
            <div class="row g-3">
              {% for module in modules %}
                <div class="col-md-6 col-lg-4">
                  <div class="form-check perm-check">
                    <input class="form-check-input"
                           type="checkbox"
                           name="permisos"
                           value="{{ module }}"
                           id="mod_{{ loop.index }}"
                           {% if module in user_modules %}checked{% endif %}>
                    <label class="form-check-label fw-semibold" for="mod_{{ loop.index }}">
                      {{ module }}
                    </label>
                  </div>
                </div>
              {% endfor %}
            </div>

            <div class="perm-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar Permisos
              </button>

              <a href="{{ url_for('usuarios') }}"
                 class="btn rounded-pill px-4 fw-bold perm-cancel-btn">
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

      .perm-shell{
        width:96%;
        max-width:1400px;
        margin:26px auto 24px auto;
      }

      .perm-header-card{
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

      .perm-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .perm-header-overlay{
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

      .perm-header-overlay::before{
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

      .perm-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
      }

      .perm-header-text::before{
        content:"SGSI · Gestión de Permisos";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .perm-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .perm-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .perm-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .perm-header-actions .btn,
      .perm-back-btn,
      .perm-cancel-btn,
      .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .perm-back-btn,
      .perm-cancel-btn{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }

      .perm-back-btn:hover,
      .perm-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }

      .perm-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .perm-card-body,
      .perm-card .card-body{
        padding:20px;
      }

      .perm-check{
        background:#f8fafc;
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:14px 16px 14px 40px;
        min-height:58px;
        box-shadow:0 4px 10px rgba(15,23,42,.05);
      }

      .form-check-input{
        border-color:#9db7d7;
      }

      .form-check-input:checked{
        background-color:#0b4a8f;
        border-color:#0b4a8f;
      }

      .form-check-label{
        font-weight:800;
        color:#101827;
      }

      .perm-bottom-actions{
        display:flex;
        justify-content:center;
        gap:12px;
        margin-top:24px;
        flex-wrap:wrap;
      }

      @media (max-width:992px){
        .perm-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .perm-header-card{
          min-height:88px;
        }

        .perm-title{
          font-size:1.20rem;
        }

        .perm-subtitle{
          font-size:.68rem;
        }

        .perm-card-body,
        .perm-card .card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .perm-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .perm-header-overlay::before{
          margin:0;
        }

        .perm-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .perm-title,
        .perm-subtitle{
          text-align:center;
        }

        .perm-header-actions .btn,
        .perm-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """, user=user, modules=modules, user_modules=user_modules)

    return render_template_string(BASE, content=content)


# =========================
# Función genérica para verificar permisos
# =========================
def verificar_permiso(user, module_name):
    if not user:
        return False

    if user.role == 'admin':
        return True

    if user.role == 'auditor':
        return not auditor_module_blocked(module_name)

    perm = UserPermission.query.filter_by(
        user_id=user.id,
        module_name=module_name
    ).first()

    return bool(perm and perm.has_access)

def verificar_permiso_activos(user, permiso_matriz):
    if not user:
        return False

    if user.role == "admin":
        return True

    if user.role == "auditor":
        return True

    return (
        verificar_permiso(user, "Gestión de Activos de Información")
        or verificar_permiso(user, permiso_matriz)
    )


# ============================================================
# REGLAS GLOBALES DEL ROL AUDITOR
# ============================================================

AUDITOR_MODULES_DENY = {
    "Centro de Alertas",
    "Configuración Parámetros de la Empresa",
    "OpenRouter API Key",
    "Gestión de Usuarios",
    "Aplicación móvil",
}

AUDITOR_ACTIONS_DENY_LABELS = (
    "Agregar",
    "Nuevo",
    "Crear",
    "Configurar",
    "Configuración",
    "Parámetros",
    "Editar",
    "Eliminar",
)


def is_auditor(user):
    return bool(user and getattr(user, "role", None) == "auditor")


def auditor_module_blocked(module_name: str) -> bool:
    return (module_name or "").strip() in AUDITOR_MODULES_DENY


def auditor_can_enter_module(module_name: str) -> bool:
    return not auditor_module_blocked(module_name)


def auditor_is_read_only(user) -> bool:
    return is_auditor(user)


# ============================================================================================================================================
#                                                               Fin Modulo de Gestión de Usuarios
# ============================================================================================================================================

# ============================================================================================================================================
#                                                               MÓDULO LOGS DE AUDITORÍA
# ============================================================================================================================================

@app.route('/admin/logs_auditoria')
@login_required
@admin_required
def logs_auditoria():
    busqueda = (request.args.get("busqueda") or "").strip()
    fecha_desde = (request.args.get("fecha_desde") or "").strip()
    fecha_hasta = (request.args.get("fecha_hasta") or "").strip()

    conn = get_log_db_connection()
    cur = conn.cursor()

    sql = """
        SELECT id, fecha_hora, usuario_transaccion, novedad
        FROM auditoria_logs
        WHERE 1=1
    """
    params = []

    if busqueda:
        sql += """
            AND (
                usuario_transaccion LIKE ?
                OR novedad LIKE ?
            )
        """
        like_value = f"%{busqueda}%"
        params.extend([like_value, like_value])

    if fecha_desde:
        sql += " AND substr(fecha_hora, 1, 10) >= ? "
        params.append(fecha_desde)

    if fecha_hasta:
        sql += " AND substr(fecha_hora, 1, 10) <= ? "
        params.append(fecha_hasta)

    sql += " ORDER BY datetime(fecha_hora) ASC "

    cur.execute(sql, params)
    logs = cur.fetchall()
    conn.close()

    content = render_template_string("""
    <div class="logs-shell">

      <div class="logs-header-card">
        <div class="logs-header-overlay">
          <div class="logs-header-text">
            <h3 class="logs-title m-0">Logs de Auditoría</h3>
            <div class="logs-subtitle">
              Registro de accesos exitosos, accesos fallidos y creación de usuarios del SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="logs-header-actions">
        
      </div>

      <div class="logs-card p-4 mb-4">
        <div class="logs-section-title">Filtros de búsqueda</div>

        <form method="get">
          <div class="row g-3">
            <div class="col-md-4">
              <label class="form-label">Buscar por usuario o novedad</label>
              <input type="text" name="busqueda" value="{{ busqueda }}" class="form-control" placeholder="Ej: acceso fallido, admin, carlos">
            </div>

            <div class="col-md-3">
              <label class="form-label">Fecha desde</label>
              <input type="date" name="fecha_desde" value="{{ fecha_desde }}" class="form-control">
            </div>

            <div class="col-md-3">
              <label class="form-label">Fecha hasta</label>
              <input type="date" name="fecha_hasta" value="{{ fecha_hasta }}" class="form-control">
            </div>

            <div class="col-md-2 d-flex align-items-end">
              <button class="btn btn-primary rounded-pill w-100 fw-bold">Filtrar</button>
            </div>
          </div>
        </form>
      </div>

      <div class="logs-card p-4">
        <div class="logs-section-title d-flex justify-content-between align-items-center flex-wrap gap-2">
          <span>Histórico de logs</span>
          <span class="badge bg-primary">Total: {{ logs|length }}</span>
        </div>

        <div class="table-responsive logs-table-wrap">
          <table class="table table-bordered align-middle mb-0">
            <thead class="logs-table-head">
              <tr class="text-center">
                <th style="width:90px;">ID</th>
                <th style="width:190px;">Fecha y hora</th>
                <th style="width:220px;">Usuario que hizo la transacción</th>
                <th>Novedad</th>
              </tr>
            </thead>
            <tbody>
              {% for log in logs %}
                <tr>
                  <td class="text-center">{{ log["id"] }}</td>
                  <td class="text-center">{{ log["fecha_hora"] }}</td>
                  <td>{{ log["usuario_transaccion"] }}</td>
                  <td>{{ log["novedad"] }}</td>
                </tr>
              {% else %}
                <tr>
                  <td colspan="4" class="text-center text-muted py-4">
                    No hay registros de auditoría para mostrar.
                  </td>
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

      .logs-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .logs-header-card{
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

      .logs-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .logs-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }

      .logs-header-overlay::before{
        content:"🧾";
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

      .logs-header-text{
        max-width:1000px;
        min-width:0;
      }

      .logs-header-text::before{
        content:"SGSI · Auditoría y Trazabilidad";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .logs-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }

      .logs-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }

      .logs-header-actions{
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
        max-width:100%;
      }

      .logs-btn-main{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .logs-btn-main:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      .logs-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .logs-card.p-4{
        padding:1.5rem !important;
      }

      .logs-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
        overflow-wrap:break-word;
      }

      .logs-table-wrap{
        border:1px solid #e2ebf5;
        border-radius:14px;
        background:#ffffff;
        overflow-x:auto;
        overflow-y:hidden;
        width:100%;
        max-width:100%;
      }

      .logs-table-wrap .table{
        margin-bottom:0;
        min-width:980px;
      }

      .logs-table-head th{
        background:#eef5ff !important;
        color:#0b4a8f !important;
        font-weight:950;
        vertical-align:middle !important;
        border-bottom:1px solid #d7dee7 !important;
        white-space:nowrap;
        font-size:.82rem;
      }

      .logs-table-wrap td,
      .logs-table-wrap th{
        vertical-align:middle !important;
      }

      .logs-table-wrap td{
        font-size:.85rem;
        color:#334155;
      }

      .logs-table-wrap tbody tr:hover{
        background:#f8fbff;
      }

      .form-control,
      .form-select{
        border-radius:10px;
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

      h3{
        color:#ffffff;
        margin:0;
      }

      @media (max-width:992px){
        .logs-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .logs-title{
          font-size:1.20rem;
          line-height:1.08;
        }

        .logs-subtitle{
          font-size:.68rem;
          line-height:1.12;
        }

        .logs-card.p-4{
          padding:1rem !important;
        }
      }

      @media (max-width:768px){
        .logs-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .logs-header-overlay::before{
          margin:0;
        }

        .logs-title,
        .logs-subtitle{
          text-align:center;
        }

        .logs-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, logs=logs, busqueda=busqueda, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)

    return render_template_string(BASE, content=content)

# ============================================================================================================================================
#                                                               FIN MÓDULO LOGS DE AUDITORÍA
# ============================================================================================================================================

# ============================================================================================================================================
#                                                               Menu Principal
# ============================================================================================================================================
# AJUSTE: menú activo corregido, Pruebas SAST integrado y botón duplicado removido.

# =====================================================================
# HELPERS TABLERO PRINCIPAL SGSI (VERSIÓN GRANDE + VELOCÍMETRO MEJORADO)
# =====================================================================
from collections import Counter
import base64
import io
import math
import re
import json
import sqlite3
# GRAC-RAM: importación diferida en el bloque de optimización
# GRAC-RAM: importación diferida en el bloque de optimización
from flask import jsonify


def _dashboard_fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        bbox_inches="tight",
        dpi=220,
        facecolor=fig.get_facecolor()
    )
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _dashboard_empty_chart(title="Sin datos", subtitle="No hay información disponible"):
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    ax.axis("off")

    ax.text(
        0.5, 0.62, title,
        ha="center", va="center",
        fontsize=18, fontweight="bold", color="#101827"
    )
    ax.text(
        0.5, 0.42, subtitle,
        ha="center", va="center",
        fontsize=11, color="#4b5563"
    )
    return _dashboard_fig_to_b64(fig)


def _dashboard_gauge_b64(value, title="Cumplimiento", subtitle="Protección de datos personales"):
    try:
        value = float(value or 0)
    except Exception:
        value = 0.0

    value = max(0.0, min(100.0, value))

    fig, ax = plt.subplots(figsize=(8.6, 5.6), subplot_kw={"aspect": "equal"})
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    ax.axis("off")

    # =========================================================
    # GEOMETRÍA
    # Velocímetro superior: 180° (izquierda) a 0° (derecha)
    # =========================================================
    r_outer = 1.22
    band_width = 0.24

    # arco base
    ax.add_patch(
        patches.Wedge(
            (0, 0), r_outer, 0, 180,
            width=band_width,
            facecolor="#e5e7eb",
            edgecolor="none"
        )
    )

    # segmentos de color: izquierda rojo -> derecha azul
    segmentos = [
        (144, 180, "#b91c1c"),  # 0-20
        (108, 144, "#c76b00"),  # 20-40
        (72, 108, "#d39b00"),   # 40-60
        (36, 72, "#0f8a42"),    # 60-80
        (0, 36, "#087ab8"),     # 80-100
    ]

    for a0, a1, color in segmentos:
        ax.add_patch(
            patches.Wedge(
                (0, 0), r_outer, a0, a1,
                width=band_width,
                facecolor=color,
                edgecolor="white",
                linewidth=2.0
            )
        )

    # =========================================================
    # MARCAS Y NÚMEROS ARRIBA
    # 0 izquierda -> 100 derecha
    # =========================================================
    for pct in range(0, 101, 20):
        angle_deg = 180 - (pct / 100.0) * 180.0
        ang = math.radians(angle_deg)

        # marca
        x0, y0 = 0.92 * math.cos(ang), 0.92 * math.sin(ang)
        x1, y1 = 1.08 * math.cos(ang), 1.08 * math.sin(ang)
        ax.plot([x0, x1], [y0, y1], color="#64748b", linewidth=1.5)

        # texto
        tx, ty = 1.36 * math.cos(ang), 1.36 * math.sin(ang)
        ax.text(
            tx, ty, f"{pct}",
            ha="center", va="center",
            fontsize=10.5,
            color="#475569",
            fontweight="bold"
        )

    # =========================================================
    # FLECHA / AGUJA CORRECTA
    # 0 izquierda -> 100 derecha, siempre hacia arriba
    # =========================================================
    angle_deg = 180 - (value / 100.0) * 180.0
    ang = math.radians(angle_deg)

    # aguja principal
    x = 0.83 * math.cos(ang)
    y = 0.83 * math.sin(ang)
    ax.plot([0, x], [0, y], linewidth=4.6, color="#0b1220", solid_capstyle="round", zorder=6)

    # punta triangular para que se vea más bonita
    tip_x = 0.98 * math.cos(ang)
    tip_y = 0.98 * math.sin(ang)

    left_ang = math.radians(angle_deg + 90)
    right_ang = math.radians(angle_deg - 90)

    base_left_x = 0.05 * math.cos(left_ang)
    base_left_y = 0.05 * math.sin(left_ang)
    base_right_x = 0.05 * math.cos(right_ang)
    base_right_y = 0.05 * math.sin(right_ang)

    needle = patches.Polygon(
        [
            (base_left_x, base_left_y),
            (tip_x, tip_y),
            (base_right_x, base_right_y),
        ],
        closed=True,
        facecolor="#0b1220",
        edgecolor="none",
        zorder=7
    )
    ax.add_patch(needle)

    # centro
    ax.add_patch(patches.Circle((0, 0), 0.085, color="#0b1220", zorder=8))
    ax.add_patch(patches.Circle((0, 0), 0.035, color="#ffffff", zorder=9))

    # =========================================================
    # TEXTO CENTRAL
    # =========================================================
    ax.text(
        0, 0.38, f"{value:.1f}%",
        ha="center", va="center",
        fontsize=30,
        fontweight="bold",
        color="#0b1220"
    )

    ax.text(
        0, 0.16, title,
        ha="center", va="center",
        fontsize=14,
        fontweight="bold",
        color="#101827"
    )

    ax.text(
        0, -0.02, subtitle,
        ha="center", va="center",
        fontsize=10.5,
        color="#4b5563"
    )

    ax.set_xlim(-1.50, 1.50)
    ax.set_ylim(-0.18, 1.50)

    return _dashboard_fig_to_b64(fig)

def _dashboard_donut_b64(labels, values, title="", subtitle=""):
    labels = labels or []
    values = values or []

    total = sum(v for v in values if isinstance(v, (int, float)))
    if not labels or not values or total == 0:
        return _dashboard_empty_chart(title or "Sin datos", "No hay información para graficar")

    palette = [
        "#087c3d",
        "#84cc16",
        "#d39b00",
        "#c95508",
        "#b91c1c",
        "#5521a8",
        "#087ab8",
    ]
    colors = [palette[i % len(palette)] for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(8.0, 5.6))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    def _autopct(pct):
        if pct < 4:
            return ""
        return f"{pct:.0f}%"

    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        autopct=_autopct,
        startangle=90,
        counterclock=False,
        colors=colors,
        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
        pctdistance=0.78
    )

    for t in autotexts:
        t.set_fontsize(10)
        t.set_color("#0b1220")
        t.set_fontweight("bold")

    ax.text(
        0, 0.08, str(int(total)),
        ha="center", va="center",
        fontsize=28, fontweight="bold", color="#0b1220"
    )
    ax.text(
        0, -0.14, "Total",
        ha="center", va="center",
        fontsize=10, color="#4b5563"
    )

    legend_labels = [f"{lab}: {val}" for lab, val in zip(labels, values)]
    ax.legend(
        wedges,
        legend_labels,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        fontsize=10,
        frameon=False,
        handlelength=1.2,
        labelspacing=0.8
    )

    if title:
        ax.set_title(title, fontsize=15, fontweight="bold", color="#0b1220", pad=12)
    if subtitle:
        fig.text(0.5, 0.03, subtitle, ha="center", fontsize=10, color="#4b5563")

    ax.set_aspect("equal")
    return _dashboard_fig_to_b64(fig)


def _dashboard_latest_iso_radar():
    try:
        run = AnalysisRun.query.order_by(AnalysisRun.id.desc()).first()
        if not run:
            return _dashboard_empty_chart("Madurez ISO 27001", "Sin datos")

        chapter_results = json.loads(run.chapter_results_json or "{}")

        labels = []
        values = []

        for cap, data in chapter_results.items():
            labels.append(cap[:20])  # evita texto largo
            try:
                values.append(float(data.get("pct", 0)))
            except:
                values.append(0)

        if not labels:
            return _dashboard_empty_chart("Madurez ISO 27001", "Sin datos")

        return generar_radar_grande(labels, values, "Madurez ISO 27001")

    except Exception as e:
        return _dashboard_empty_chart("ISO Error", str(e))

def generar_radar_grande(labels, values, title):
    angles = [n / float(len(labels)) * 2 * math.pi for n in range(len(labels))]
    angles += angles[:1]

    values += values[:1]

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#ffffff")

    ax.plot(angles, values, linewidth=3)
    ax.fill(angles, values, alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11)

    ax.set_yticks([20,40,60,80,100])
    ax.set_yticklabels(["20%","40%","60%","80%","100%"], fontsize=10)

    # 🔥 porcentaje en el centro
    promedio = sum(values[:-1]) / len(values[:-1]) if values else 0
    ax.text(0, 0, f"{promedio:.1f}%", ha='center', va='center',
            fontsize=28, fontweight='bold', color="#0b1220")

    ax.set_title(title, size=16, pad=30, fontweight="bold")

    return _dashboard_fig_to_b64(fig)



def _dashboard_latest_nist_radar():
    try:
        run = (
            NistMadurezRun.query
            .filter(NistMadurezRun.estado == "FINALIZADO")
            .order_by(NistMadurezRun.id.desc())
            .first()
        )

        if not run:
            return _dashboard_empty_chart(
                "Madurez NIST CSF 2.0",
                "No se encontró una revisión NIST finalizada"
            )

        radar = (getattr(run, "radar_overall_b64", None) or "").strip()
        if radar:
            return radar

        resumen = {}
        try:
            resumen = json.loads(run.resumen_json or "{}")
        except Exception:
            resumen = {}

        radar_labels, radar_values = nist_pct_por_funcion(resumen, NIST_FUNC_ORDER)
        if radar_labels and radar_values:
            radar = nist_radar_b64(
                radar_labels,
                radar_values,
                title="Madurez NIST CSF 2.0"
            )
            if radar:
                return radar

    except Exception:
        pass

    return _dashboard_empty_chart(
        "Madurez NIST CSF 2.0",
        "No se encontró una araña NIST disponible"
    )

def _dashboard_latest_iso_data():
    try:
        run = AnalysisRun.query.order_by(AnalysisRun.id.desc()).first()
        if not run:
            return {
                "radar_b64": _dashboard_empty_chart(
                    "Madurez ISO 27001",
                    "No se encontró una araña ISO disponible"
                ),
                "pct": 0.0
            }

        radar = (getattr(run, "radar_overall_b64", None) or "").strip()

        pct_general = 0.0
        try:
            chapter_results = json.loads(run.chapter_results_json or "{}")
            vals = []
            if isinstance(chapter_results, dict):
                for _, data in chapter_results.items():
                    try:
                        vals.append(float((data or {}).get("pct", 0) or 0))
                    except Exception:
                        pass
            if vals:
                pct_general = round(sum(vals) / len(vals), 2)
        except Exception:
            pct_general = 0.0

        if not radar:
            radar = _dashboard_empty_chart(
                "Madurez ISO 27001",
                "No se encontró una araña ISO disponible"
            )

        return {
            "radar_b64": radar,
            "pct": pct_general
        }

    except Exception:
        return {
            "radar_b64": _dashboard_empty_chart(
                "Madurez ISO 27001",
                "No se encontró una araña ISO disponible"
            ),
            "pct": 0.0
        }

def _dashboard_latest_nist_data():
    try:
        run = (
            NistMadurezRun.query
            .filter(NistMadurezRun.estado == "FINALIZADO")
            .order_by(NistMadurezRun.id.desc())
            .first()
        )

        if not run:
            return {
                "radar_b64": _dashboard_empty_chart(
                    "Madurez NIST CSF 2.0",
                    "No se encontró una revisión NIST finalizada"
                ),
                "pct": 0.0
            }

        radar = (getattr(run, "radar_overall_b64", None) or "").strip()
        pct_general = float(run.pct_general or 0)

        if not radar:
            resumen = {}
            try:
                resumen = json.loads(run.resumen_json or "{}")
            except Exception:
                resumen = {}

            radar_labels, radar_values = nist_pct_por_funcion(resumen, NIST_FUNC_ORDER)
            if radar_labels and radar_values:
                radar = nist_radar_b64(
                    radar_labels,
                    radar_values,
                    title="Madurez NIST CSF 2.0"
                )

        if not radar:
            radar = _dashboard_empty_chart(
                "Madurez NIST CSF 2.0",
                "No se encontró una araña NIST disponible"
            )

        return {
            "radar_b64": radar,
            "pct": round(pct_general, 2)
        }

    except Exception:
        return {
            "radar_b64": _dashboard_empty_chart(
                "Madurez NIST CSF 2.0",
                "No se encontró una araña NIST disponible"
            ),
            "pct": 0.0
        }




# ============================================================
# CONSTRUCTOR PERSONAL DEL CENTRO DE CONTROL
# ============================================================
# El catálogo fijo conserva las visualizaciones originales y agrega fuentes
# de madurez y métricas que ya existen en GRAC. Los elementos adicionales
# creados por cada usuario se almacenan en dashboard_custom_widgets.
DASHBOARD_WIDGET_CATALOG = [
    {
        "key": "kpi_iso",
        "kind": "kpi",
        "group": "Indicadores superiores",
        "label": "Indicador ISO 27001",
        "description": "Porcentaje general de madurez ISO 27001.",
        "title": "ISO 27001",
        "subtitle": "Madurez general",
        "icon": "bi-shield-check",
        "color": "blue",
        "value_key": "iso_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_iso_stat",
        "default_enabled": True,
    },
    {
        "key": "kpi_nist",
        "kind": "kpi",
        "group": "Indicadores superiores",
        "label": "Indicador NIST CSF 2.0",
        "description": "Porcentaje general de cumplimiento NIST CSF 2.0.",
        "title": "NIST CSF 2.0",
        "subtitle": "Cumplimiento general",
        "icon": "bi-compass",
        "color": "orange",
        "value_key": "nist_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_nist_stat",
        "default_enabled": True,
    },
    {
        "key": "kpi_datos",
        "kind": "kpi",
        "group": "Indicadores superiores",
        "label": "Indicador de Datos Personales",
        "description": "Nivel general de cumplimiento en protección de datos personales.",
        "title": "Datos Personales",
        "subtitle": "Nivel de cumplimiento",
        "icon": "bi-lock-fill",
        "color": "green",
        "value_key": "datos_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_datos_stat",
        "default_enabled": True,
    },
    {
        "key": "kpi_scorecard",
        "kind": "kpi",
        "group": "Indicadores superiores",
        "label": "Indicador Security Scorecard",
        "description": "Promedio de Security Scorecard de terceros.",
        "title": "Security Scorecard",
        "subtitle": "Score promedio",
        "icon": "bi-shield-fill-check",
        "color": "purple",
        "value_key": "scorecard_terceros_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_scorecard_terceros_stat",
        "default_enabled": True,
    },
    {
        "key": "kpi_pci",
        "kind": "kpi",
        "group": "Madurez y cumplimiento",
        "label": "Madurez PCI-DSS",
        "description": "Nivel promedio general de la última evaluación PCI-DSS.",
        "title": "PCI-DSS",
        "subtitle": "Nivel de madurez",
        "icon": "bi-credit-card-2-front",
        "color": "orange",
        "value_key": "pci_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_pci_stat",
        "default_enabled": False,
    },
    {
        "key": "kpi_soc2",
        "kind": "kpi",
        "group": "Madurez y cumplimiento",
        "label": "Madurez SOC 2",
        "description": "Porcentaje general de la última evaluación de madurez SOC 2.",
        "title": "SOC 2",
        "subtitle": "Nivel de madurez",
        "icon": "bi-patch-check-fill",
        "color": "purple",
        "value_key": "soc2_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_soc2_stat",
        "default_enabled": False,
    },
    {
        "key": "kpi_ai",
        "kind": "kpi",
        "group": "Madurez y cumplimiento",
        "label": "Madurez del Sistema de Gestión de IA",
        "description": "Porcentaje general de la última revisión ISO/IEC 42001 del sistema de gestión de IA.",
        "title": "Gestión de IA",
        "subtitle": "Madurez ISO/IEC 42001",
        "icon": "bi-robot",
        "color": "blue",
        "value_key": "ai_maturity_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_ai_stat",
        "default_enabled": False,
    },
    {
        "key": "kpi_riesgos_activos",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Total de riesgos activos",
        "description": "Cantidad de riesgos no archivados registrados en la matriz.",
        "title": "Riesgos activos",
        "subtitle": "Matriz de riesgos",
        "icon": "bi-exclamation-diamond-fill",
        "color": "orange",
        "value_key": "risks_active_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_risks_active",
        "default_enabled": False,
    },
    {
        "key": "kpi_riesgos_fuera_apetito",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Riesgos fuera del apetito",
        "description": "Riesgos activos cuyo nivel residual supera el apetito configurado.",
        "title": "Fuera del apetito",
        "subtitle": "Riesgo residual",
        "icon": "bi-exclamation-triangle-fill",
        "color": "purple",
        "value_key": "risks_outside_appetite_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_risks_outside",
        "default_enabled": False,
    },
    {
        "key": "kpi_incidentes_abiertos",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Incidentes abiertos",
        "description": "Cantidad de incidentes que todavía no están cerrados o resueltos.",
        "title": "Incidentes abiertos",
        "subtitle": "Gestión de incidentes",
        "icon": "bi-broadcast-pin",
        "color": "orange",
        "value_key": "incidents_open_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_incidents_open",
        "default_enabled": False,
    },
    {
        "key": "kpi_incidentes_cumplimiento",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Cumplimiento promedio de incidentes",
        "description": "Promedio del cumplimiento global MTCD/MTIR calculado en métricas de incidentes.",
        "title": "Cumplimiento incidentes",
        "subtitle": "Promedio MTCD / MTIR",
        "icon": "bi-stopwatch-fill",
        "color": "green",
        "value_key": "incidents_compliance_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_incidents_compliance",
        "default_enabled": False,
    },
    {
        "key": "kpi_vulnerabilidades_abiertas",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Vulnerabilidades abiertas",
        "description": "Cantidad de vulnerabilidades cuyo estado continúa abierto.",
        "title": "Vulnerabilidades abiertas",
        "subtitle": "Gestión de vulnerabilidades",
        "icon": "bi-bug-fill",
        "color": "orange",
        "value_key": "vulnerabilities_open_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_vulns_open",
        "default_enabled": False,
    },
    {
        "key": "kpi_vulnerabilidades_criticas",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Vulnerabilidades críticas abiertas",
        "description": "Cantidad de vulnerabilidades críticas que permanecen abiertas.",
        "title": "Críticas abiertas",
        "subtitle": "Vulnerabilidades",
        "icon": "bi-radioactive",
        "color": "purple",
        "value_key": "vulnerabilities_critical_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_vulns_critical",
        "default_enabled": False,
    },
    {
        "key": "kpi_planes_abiertos",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Planes de acción abiertos",
        "description": "Cantidad de actividades de mejora o acciones correctivas abiertas.",
        "title": "Planes abiertos",
        "subtitle": "Planes de acción",
        "icon": "bi-list-check",
        "color": "blue",
        "value_key": "plans_open_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_plans_open",
        "default_enabled": False,
    },
    {
        "key": "kpi_planes_vencidos",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Planes de acción vencidos",
        "description": "Planes abiertos cuya fecha propuesta de ejecución ya venció.",
        "title": "Planes vencidos",
        "subtitle": "Seguimiento de acciones",
        "icon": "bi-calendar-x-fill",
        "color": "purple",
        "value_key": "plans_overdue_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_plans_overdue",
        "default_enabled": False,
    },
    {
        "key": "kpi_requisitos_no_cumple",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Requisitos legales no cumplidos",
        "description": "Cantidad de requisitos legales con estado No cumple o Incumple.",
        "title": "Requisitos no cumplidos",
        "subtitle": "Cumplimiento legal",
        "icon": "bi-bank2",
        "color": "orange",
        "value_key": "legal_noncompliant_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_legal_noncompliant",
        "default_enabled": False,
    },
    {
        "key": "kpi_proveedores_alta",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Proveedores de criticidad alta",
        "description": "Cantidad de evaluaciones de proveedores clasificadas con criticidad alta.",
        "title": "Proveedores críticos",
        "subtitle": "Criticidad alta",
        "icon": "bi-buildings-fill",
        "color": "purple",
        "value_key": "providers_high_count",
        "suffix": "",
        "decimals": 0,
        "element_id": "dash_providers_high",
        "default_enabled": False,
    },
    {
        "key": "kpi_cultura_seguridad",
        "kind": "kpi",
        "group": "Métricas operativas",
        "label": "Última métrica de cultura de seguridad",
        "description": "Resultado general de la medición más reciente de cultura y formación.",
        "title": "Cultura de seguridad",
        "subtitle": "Último resultado",
        "icon": "bi-people-fill",
        "color": "green",
        "value_key": "security_culture_pct",
        "suffix": "%",
        "decimals": 2,
        "element_id": "dash_security_culture",
        "default_enabled": False,
    },
    {
        "key": "chart_iso",
        "kind": "chart",
        "group": "Gráficas de madurez y cumplimiento",
        "label": "Gráfica de madurez ISO 27001",
        "description": "Araña o gráfica consolidada de madurez ISO 27001.",
        "title": "Madurez ISO 27001",
        "value_key": "iso_pct",
        "suffix": "%",
        "decimals": 2,
        "image_key": "iso_radar_b64",
        "image_id": "dash_iso_radar",
        "default_enabled": True,
    },
    {
        "key": "chart_nist",
        "kind": "chart",
        "group": "Gráficas de madurez y cumplimiento",
        "label": "Gráfica de madurez NIST CSF 2.0",
        "description": "Araña o gráfica consolidada de madurez NIST CSF 2.0.",
        "title": "Madurez NIST CSF 2.0",
        "value_key": "nist_pct",
        "suffix": "%",
        "decimals": 2,
        "image_key": "nist_radar_b64",
        "image_id": "dash_nist_radar",
        "default_enabled": True,
    },
    {
        "key": "chart_datos",
        "kind": "chart",
        "group": "Gráficas de madurez y cumplimiento",
        "label": "Gráfica de Protección de Datos Personales",
        "description": "Medidor del nivel de cumplimiento en protección de datos personales.",
        "title": "Protección de Datos Personales",
        "value_key": "datos_pct",
        "suffix": "%",
        "decimals": 2,
        "image_key": "datos_gauge_b64",
        "image_id": "dash_datos_gauge",
        "default_enabled": True,
    },
    {
        "key": "chart_pci",
        "kind": "chart",
        "group": "Gráficas de madurez y cumplimiento",
        "label": "Gráfica de madurez PCI-DSS",
        "description": "Medidor de la última evaluación de madurez PCI-DSS.",
        "title": "Madurez PCI-DSS",
        "value_key": "pci_pct",
        "suffix": "%",
        "decimals": 2,
        "image_key": "pci_gauge_b64",
        "image_id": "dash_pci_gauge",
        "default_enabled": False,
    },
    {
        "key": "chart_soc2",
        "kind": "chart",
        "group": "Gráficas de madurez y cumplimiento",
        "label": "Gráfica de madurez SOC 2",
        "description": "Araña o medidor de la última evaluación SOC 2.",
        "title": "Madurez SOC 2",
        "value_key": "soc2_pct",
        "suffix": "%",
        "decimals": 2,
        "image_key": "soc2_radar_b64",
        "image_id": "dash_soc2_radar",
        "default_enabled": False,
    },
    {
        "key": "chart_ai",
        "kind": "chart",
        "group": "Gráficas de madurez y cumplimiento",
        "label": "Gráfica del Sistema de Gestión de IA",
        "description": "Araña o medidor de la última revisión ISO/IEC 42001.",
        "title": "Sistema de Gestión de IA",
        "value_key": "ai_maturity_pct",
        "suffix": "%",
        "decimals": 2,
        "image_key": "ai_radar_b64",
        "image_id": "dash_ai_radar",
        "default_enabled": False,
    },
    {
        "key": "chart_riesgos",
        "kind": "chart",
        "group": "Gráficas operativas",
        "label": "Gráfica de Riesgos Residuales",
        "description": "Distribución de los riesgos residuales por nivel.",
        "title": "Riesgos residuales",
        "display_value": "Distribución",
        "image_key": "riesgos_b64",
        "image_id": "dash_riesgos",
        "default_enabled": True,
    },
    {
        "key": "chart_incidentes",
        "kind": "chart",
        "group": "Gráficas operativas",
        "label": "Gráfica de Incidentes",
        "description": "Clasificación consolidada de incidentes de seguridad.",
        "title": "Incidentes",
        "display_value": "Clasificación",
        "image_key": "incidentes_b64",
        "image_id": "dash_incidentes",
        "default_enabled": True,
    },
    {
        "key": "chart_vulnerabilidades",
        "kind": "chart",
        "group": "Gráficas operativas",
        "label": "Gráfica de Vulnerabilidades",
        "description": "Distribución de vulnerabilidades por criticidad.",
        "title": "Vulnerabilidades",
        "display_value": "Criticidad",
        "image_key": "vulnerabilidades_b64",
        "image_id": "dash_vulnerabilidades",
        "default_enabled": True,
    },
    {
        "key": "chart_proveedores",
        "kind": "chart",
        "group": "Gráficas operativas",
        "label": "Gráfica de Proveedores",
        "description": "Distribución de proveedores de acuerdo con su criticidad.",
        "title": "Proveedores",
        "display_value": "Criticidad",
        "image_key": "proveedores_criticidad_b64",
        "image_id": "dash_proveedores_criticidad",
        "default_enabled": True,
    },
    {
        "key": "chart_planes_accion",
        "kind": "chart",
        "group": "Gráficas operativas",
        "label": "Gráfica de Planes de Acción",
        "description": "Estado consolidado de los planes de acción del SGSI.",
        "title": "Planes de acción",
        "display_value": "Estado",
        "image_key": "planes_accion_estado_b64",
        "image_id": "dash_planes_accion_estado",
        "default_enabled": True,
    },
    {
        "key": "chart_requisitos_legales",
        "kind": "chart",
        "group": "Gráficas operativas",
        "label": "Gráfica de Requisitos Legales",
        "description": "Estado de cumplimiento de los requisitos legales registrados.",
        "title": "Requisitos legales",
        "display_value": "Cumplimiento",
        "image_key": "requisitos_legales_estado_b64",
        "image_id": "dash_requisitos_legales_estado",
        "default_enabled": True,
    },
]

DASHBOARD_WIDGET_MAP = {
    item["key"]: dict(item, default_order=index + 1)
    for index, item in enumerate(DASHBOARD_WIDGET_CATALOG)
}

# Fuentes seguras para que cada usuario construya visualizaciones sencillas.
# El usuario únicamente selecciona: 1) fuente de datos y 2) presentación.
# No se permite ingresar SQL, nombres de tablas, código ni expresiones libres.
DASHBOARD_VISUALIZATION_LABELS = {
    "radar": "Araña / radar",
    "gauge": "Velocímetro",
    "donut": "Aro",
    "line": "Línea en el tiempo",
    "pie": "Circular (pie)",
    "bar_vertical": "Barras verticales",
    "bar_horizontal": "Barras horizontales",
    "kpi": "Indicador numérico (anterior)",
}

DASHBOARD_DATA_SOURCE_CATALOG = [
    # Niveles de madurez: araña o velocímetro.
    {"key": "maturity_iso_pct", "group": "Niveles de madurez", "data_kind": "maturity", "label": "Nivel de Madurez — ISO 27001", "description": "Última evaluación de madurez ISO 27001.", "unit": "%", "decimals": 2, "allowed_views": ["radar", "gauge"], "default_title": "Nivel de Madurez — ISO 27001", "default_subtitle": "Última evaluación", "icon": "bi-shield-check", "color": "blue"},
    {"key": "maturity_nist_pct", "group": "Niveles de madurez", "data_kind": "maturity", "label": "Nivel de Madurez — NIST CSF 2.0", "description": "Última evaluación de madurez NIST CSF 2.0.", "unit": "%", "decimals": 2, "allowed_views": ["radar", "gauge"], "default_title": "Nivel de Madurez — NIST CSF 2.0", "default_subtitle": "Última evaluación", "icon": "bi-compass", "color": "orange"},
    {"key": "maturity_data_pct", "group": "Niveles de madurez", "data_kind": "maturity", "label": "Nivel de Madurez — Protección de Datos Personales", "description": "Última evaluación de protección de datos personales.", "unit": "%", "decimals": 2, "allowed_views": ["radar", "gauge"], "default_title": "Nivel de Madurez — Datos Personales", "default_subtitle": "Última evaluación", "icon": "bi-lock-fill", "color": "green"},
    {"key": "maturity_pci_pct", "group": "Niveles de madurez", "data_kind": "maturity", "label": "Nivel de Madurez — PCI-DSS", "description": "Última evaluación de madurez PCI-DSS.", "unit": "%", "decimals": 2, "allowed_views": ["radar", "gauge"], "default_title": "Nivel de Madurez — PCI-DSS", "default_subtitle": "Última evaluación", "icon": "bi-credit-card-2-front", "color": "orange"},
    {"key": "maturity_soc2_pct", "group": "Niveles de madurez", "data_kind": "maturity", "label": "Nivel de Madurez — SOC 2", "description": "Última evaluación de madurez SOC 2.", "unit": "%", "decimals": 2, "allowed_views": ["radar", "gauge"], "default_title": "Nivel de Madurez — SOC 2", "default_subtitle": "Última evaluación", "icon": "bi-patch-check-fill", "color": "purple"},
    {"key": "maturity_ai_pct", "group": "Niveles de madurez", "data_kind": "maturity", "label": "Nivel de Madurez — Sistema de Gestión de Inteligencia Artificial", "description": "Última revisión ISO/IEC 42001 del sistema de gestión de IA.", "unit": "%", "decimals": 2, "allowed_views": ["radar", "gauge"], "default_title": "Nivel de Madurez — Gestión de IA", "default_subtitle": "ISO/IEC 42001", "icon": "bi-robot", "color": "blue"},

    # Distribuciones: aro, pie o barras. También pueden resumirse en velocímetro.
    {"key": "risks_residual_distribution", "group": "Riesgos", "data_kind": "distribution", "label": "Riesgos por nivel residual", "description": "Distribución de los riesgos activos por nivel residual.", "unit": "", "decimals": 0, "allowed_views": ["donut", "pie", "bar_vertical", "bar_horizontal", "gauge"], "default_title": "Riesgos por nivel residual", "default_subtitle": "Distribución de riesgos activos", "icon": "bi-exclamation-diamond-fill", "color": "orange"},
    {"key": "incidents_classification_distribution", "group": "Incidentes", "data_kind": "distribution", "label": "Incidentes por clasificación", "description": "Distribución de incidentes por clasificación o criticidad.", "unit": "", "decimals": 0, "allowed_views": ["donut", "pie", "bar_vertical", "bar_horizontal", "gauge"], "default_title": "Incidentes por clasificación", "default_subtitle": "Gestión de incidentes", "icon": "bi-broadcast-pin", "color": "orange"},
    {"key": "vulnerabilities_severity_distribution", "group": "Vulnerabilidades", "data_kind": "distribution", "label": "Vulnerabilidades por criticidad", "description": "Distribución de vulnerabilidades por nivel de criticidad.", "unit": "", "decimals": 0, "allowed_views": ["donut", "pie", "bar_vertical", "bar_horizontal", "gauge"], "default_title": "Vulnerabilidades por criticidad", "default_subtitle": "Gestión de vulnerabilidades", "icon": "bi-bug-fill", "color": "purple"},
    {"key": "providers_criticality_distribution", "group": "Proveedores", "data_kind": "distribution", "label": "Proveedores por criticidad", "description": "Distribución de proveedores según su criticidad.", "unit": "", "decimals": 0, "allowed_views": ["donut", "pie", "bar_vertical", "bar_horizontal", "gauge"], "default_title": "Proveedores por criticidad", "default_subtitle": "Evaluación de terceros", "icon": "bi-buildings-fill", "color": "purple"},
    {"key": "plans_status_distribution", "group": "Planes y mejora", "data_kind": "distribution", "label": "Planes de acción por estado", "description": "Distribución de planes de acción abiertos, cerrados o sin estado.", "unit": "", "decimals": 0, "allowed_views": ["donut", "pie", "bar_vertical", "bar_horizontal", "gauge"], "default_title": "Planes de acción por estado", "default_subtitle": "Seguimiento de acciones", "icon": "bi-list-check", "color": "blue"},
    {"key": "legal_status_distribution", "group": "Cumplimiento", "data_kind": "distribution", "label": "Requisitos legales por estado", "description": "Distribución de requisitos legales por estado de cumplimiento.", "unit": "", "decimals": 0, "allowed_views": ["donut", "pie", "bar_vertical", "bar_horizontal", "gauge"], "default_title": "Requisitos legales por estado", "default_subtitle": "Cumplimiento legal", "icon": "bi-bank2", "color": "green"},

    # Tendencias: líneas en el tiempo o barras.
    {"key": "risks_timeline", "group": "Líneas en el tiempo", "data_kind": "timeline", "label": "Riesgos registrados en el tiempo", "description": "Cantidad mensual de riesgos identificados.", "unit": "", "decimals": 0, "allowed_views": ["line", "bar_vertical", "bar_horizontal"], "default_title": "Riesgos registrados en el tiempo", "default_subtitle": "Últimos períodos con información", "icon": "bi-graph-up-arrow", "color": "orange"},
    {"key": "incidents_timeline", "group": "Líneas en el tiempo", "data_kind": "timeline", "label": "Incidentes registrados en el tiempo", "description": "Cantidad mensual de incidentes registrados.", "unit": "", "decimals": 0, "allowed_views": ["line", "bar_vertical", "bar_horizontal"], "default_title": "Incidentes registrados en el tiempo", "default_subtitle": "Últimos períodos con información", "icon": "bi-graph-up-arrow", "color": "orange"},
    {"key": "vulnerabilities_timeline", "group": "Líneas en el tiempo", "data_kind": "timeline", "label": "Vulnerabilidades identificadas en el tiempo", "description": "Cantidad mensual de vulnerabilidades identificadas.", "unit": "", "decimals": 0, "allowed_views": ["line", "bar_vertical", "bar_horizontal"], "default_title": "Vulnerabilidades en el tiempo", "default_subtitle": "Últimos períodos con información", "icon": "bi-graph-up-arrow", "color": "purple"},
    {"key": "plans_timeline", "group": "Líneas en el tiempo", "data_kind": "timeline", "label": "Planes de acción registrados en el tiempo", "description": "Cantidad mensual de planes de acción creados.", "unit": "", "decimals": 0, "allowed_views": ["line", "bar_vertical", "bar_horizontal"], "default_title": "Planes de acción en el tiempo", "default_subtitle": "Últimos períodos con información", "icon": "bi-graph-up-arrow", "color": "blue"},
    {"key": "security_culture_timeline", "group": "Líneas en el tiempo", "data_kind": "timeline", "label": "Cultura de seguridad en el tiempo", "description": "Evolución mensual del resultado de cultura y formación.", "unit": "%", "decimals": 2, "allowed_views": ["line", "bar_vertical", "bar_horizontal"], "default_title": "Cultura de seguridad en el tiempo", "default_subtitle": "Resultado mensual", "icon": "bi-people-fill", "color": "green"},

    # Indicadores puntuales: velocímetro o aro.
    {"key": "scorecard_average_pct", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Security Scorecard promedio", "description": "Promedio del score de terceros evaluados.", "unit": "%", "decimals": 2, "allowed_views": ["gauge", "donut"], "default_title": "Security Scorecard promedio", "default_subtitle": "Terceros evaluados", "icon": "bi-shield-fill-check", "color": "purple"},
    {"key": "risks_active_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Riesgos activos", "description": "Cantidad de riesgos no archivados.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Riesgos activos", "default_subtitle": "Matriz de riesgos", "icon": "bi-exclamation-diamond-fill", "color": "orange"},
    {"key": "risks_outside_appetite_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Riesgos fuera del apetito", "description": "Cantidad de riesgos residuales que superan el apetito definido.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Riesgos fuera del apetito", "default_subtitle": "Riesgo residual", "icon": "bi-exclamation-triangle-fill", "color": "purple"},
    {"key": "incidents_open_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Incidentes abiertos", "description": "Cantidad de incidentes sin cierre o resolución.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Incidentes abiertos", "default_subtitle": "Gestión de incidentes", "icon": "bi-broadcast-pin", "color": "orange"},
    {"key": "incidents_compliance_pct", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Cumplimiento promedio MTCD/MTIR", "description": "Promedio de cumplimiento global de las métricas de incidentes.", "unit": "%", "decimals": 2, "allowed_views": ["gauge", "donut"], "default_title": "Cumplimiento MTCD / MTIR", "default_subtitle": "Métricas de incidentes", "icon": "bi-stopwatch-fill", "color": "green"},
    {"key": "vulnerabilities_open_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Vulnerabilidades abiertas", "description": "Cantidad de vulnerabilidades abiertas.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Vulnerabilidades abiertas", "default_subtitle": "Gestión de vulnerabilidades", "icon": "bi-bug-fill", "color": "orange"},
    {"key": "vulnerabilities_critical_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Vulnerabilidades críticas abiertas", "description": "Cantidad de vulnerabilidades críticas no cerradas.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Vulnerabilidades críticas", "default_subtitle": "Abiertas", "icon": "bi-radioactive", "color": "purple"},
    {"key": "plans_open_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Planes de acción abiertos", "description": "Cantidad de planes o actividades de mejora abiertas.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Planes de acción abiertos", "default_subtitle": "Seguimiento", "icon": "bi-list-check", "color": "blue"},
    {"key": "plans_overdue_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Planes de acción vencidos", "description": "Planes abiertos cuya fecha propuesta ya venció.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Planes de acción vencidos", "default_subtitle": "Seguimiento", "icon": "bi-calendar-x-fill", "color": "purple"},
    {"key": "legal_noncompliant_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Requisitos legales no cumplidos", "description": "Cantidad de requisitos en incumplimiento.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Requisitos no cumplidos", "default_subtitle": "Cumplimiento legal", "icon": "bi-bank2", "color": "orange"},
    {"key": "providers_high_count", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Proveedores de criticidad alta", "description": "Cantidad de proveedores clasificados con criticidad alta.", "unit": "", "decimals": 0, "allowed_views": ["gauge", "donut"], "default_title": "Proveedores de criticidad alta", "default_subtitle": "Evaluación de terceros", "icon": "bi-buildings-fill", "color": "purple"},
    {"key": "security_culture_pct", "group": "Indicadores y métricas", "data_kind": "scalar", "label": "Última métrica de cultura de seguridad", "description": "Resultado general más reciente de cultura y formación.", "unit": "%", "decimals": 2, "allowed_views": ["gauge", "donut"], "default_title": "Cultura de seguridad", "default_subtitle": "Último resultado", "icon": "bi-people-fill", "color": "green"},
]

DASHBOARD_DATA_SOURCE_MAP = {item["key"]: dict(item) for item in DASHBOARD_DATA_SOURCE_CATALOG}

DASHBOARD_ALLOWED_COLORS = {
    "blue": "Azul",
    "orange": "Naranja",
    "green": "Verde",
    "purple": "Morado",
}

DASHBOARD_ALLOWED_ICONS = {
    "bi-speedometer2": "Velocímetro",
    "bi-shield-check": "Escudo",
    "bi-robot": "Inteligencia artificial",
    "bi-credit-card-2-front": "PCI-DSS",
    "bi-patch-check-fill": "Cumplimiento",
    "bi-bar-chart-line-fill": "Métricas",
    "bi-graph-up-arrow": "Tendencia",
    "bi-exclamation-triangle-fill": "Alerta",
    "bi-exclamation-diamond-fill": "Riesgos",
    "bi-bug-fill": "Vulnerabilidades",
    "bi-radioactive": "Crítico",
    "bi-broadcast-pin": "Incidentes",
    "bi-stopwatch-fill": "Tiempos",
    "bi-list-check": "Planes de acción",
    "bi-calendar-x-fill": "Vencimiento",
    "bi-bank2": "Requisitos legales",
    "bi-buildings-fill": "Proveedores",
    "bi-people-fill": "Cultura",
    "bi-compass": "NIST",
    "bi-lock-fill": "Datos personales",
    "bi-shield-fill-check": "Scorecard",
}


def _dashboard_default_widget_keys():
    return [item["key"] for item in DASHBOARD_WIDGET_CATALOG if item.get("default_enabled", True)]


def _dashboard_custom_key(widget_id):
    return f"custom:{int(widget_id)}"


def _dashboard_custom_id_from_key(key):
    txt = str(key or "").strip()
    if not txt.startswith("custom:"):
        return None
    try:
        return int(txt.split(":", 1)[1])
    except Exception:
        return None


def _dashboard_dom_id(key):
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", str(key or ""))


def _dashboard_custom_widgets_for_user(user_id):
    if not user_id:
        return []
    try:
        return (
            DashboardCustomWidget.query
            .filter_by(user_id=int(user_id))
            .order_by(DashboardCustomWidget.id.asc())
            .all()
        )
    except Exception as exc:
        print("No se pudieron cargar las visualizaciones personalizadas:", repr(exc))
        return []


def _dashboard_custom_widget_meta(widget):
    source = DASHBOARD_DATA_SOURCE_MAP.get(widget.source_key, {})
    key = _dashboard_custom_key(widget.id)
    view = (widget.widget_type or "gauge").strip().lower()
    kind = "kpi" if view == "kpi" else "chart"
    suffix = widget.suffix if widget.suffix is not None else source.get("unit", "")
    try:
        decimals = max(0, min(int(widget.decimals if widget.decimals is not None else source.get("decimals", 2)), 2))
    except Exception:
        decimals = int(source.get("decimals", 2) or 0)

    return {
        "key": key,
        "dom_id": _dashboard_dom_id(key),
        "kind": kind,
        "group": "Visualizaciones creadas por el usuario",
        "label": source.get("label", widget.title),
        "description": source.get("description", widget.subtitle or "Visualización personalizada."),
        "title": widget.title or source.get("default_title", source.get("label", "Visualización")),
        "subtitle": widget.subtitle or source.get("default_subtitle", ""),
        "icon": widget.icon if widget.icon in DASHBOARD_ALLOWED_ICONS else source.get("icon", "bi-speedometer2"),
        "color": widget.color if widget.color in DASHBOARD_ALLOWED_COLORS else source.get("color", "blue"),
        "source_key": widget.source_key,
        "source_label": source.get("label", widget.source_key),
        "widget_type": view,
        "presentation_label": DASHBOARD_VISUALIZATION_LABELS.get(view, view),
        "target_value": widget.target_value,
        "suffix": suffix or "",
        "decimals": decimals,
        "element_id": f"dash_custom_{widget.id}",
        "image_id": f"dash_custom_chart_{widget.id}",
        "custom": True,
        "custom_id": widget.id,
    }


def _dashboard_available_widget_map(user_id):
    result = {key: dict(meta, dom_id=_dashboard_dom_id(key)) for key, meta in DASHBOARD_WIDGET_MAP.items()}
    for widget in _dashboard_custom_widgets_for_user(user_id):
        meta = _dashboard_custom_widget_meta(widget)
        result[meta["key"]] = meta
    return result


def _dashboard_resolve_widget_meta(user_id, key):
    key = str(key or "").strip()
    if key in DASHBOARD_WIDGET_MAP:
        return dict(DASHBOARD_WIDGET_MAP[key], dom_id=_dashboard_dom_id(key))

    widget_id = _dashboard_custom_id_from_key(key)
    if not widget_id or not user_id:
        return None

    try:
        widget = DashboardCustomWidget.query.filter_by(id=widget_id, user_id=int(user_id)).first()
        return _dashboard_custom_widget_meta(widget) if widget else None
    except Exception:
        return None


def _dashboard_get_selected_keys(user_id):
    defaults = _dashboard_default_widget_keys()
    if not user_id:
        return defaults

    try:
        available = _dashboard_available_widget_map(user_id)
        pref = DashboardPreference.query.filter_by(user_id=int(user_id)).first()
        if not pref:
            return defaults

        raw = json.loads(pref.widget_keys_json or "[]")
        if not isinstance(raw, list):
            return defaults

        selected = []
        seen = set()
        for key in raw:
            key = str(key or "").strip()
            if key in available and key not in seen:
                selected.append(key)
                seen.add(key)
        return selected
    except Exception as exc:
        print("No se pudo cargar la configuración del Centro de Control:", repr(exc))
        return defaults


def _dashboard_save_selected_keys(user_id, selected_keys):
    available = _dashboard_available_widget_map(user_id)
    clean = []
    seen = set()
    for key in selected_keys or []:
        key = str(key or "").strip()
        if key in available and key not in seen:
            clean.append(key)
            seen.add(key)

    pref = DashboardPreference.query.filter_by(user_id=int(user_id)).first()
    if not pref:
        pref = DashboardPreference(user_id=int(user_id))
        db.session.add(pref)
    pref.widget_keys_json = json.dumps(clean, ensure_ascii=False)
    pref.updated_at = datetime.utcnow()
    db.session.commit()
    return clean


def _dashboard_add_key_to_selection(user_id, key):
    selected = _dashboard_get_selected_keys(user_id)
    if key not in selected:
        selected.append(key)
    return _dashboard_save_selected_keys(user_id, selected)


def _dashboard_remove_key_from_selection(user_id, key):
    selected = [item for item in _dashboard_get_selected_keys(user_id) if item != key]
    return _dashboard_save_selected_keys(user_id, selected)


def _dashboard_reset_selected_keys(user_id):
    pref = DashboardPreference.query.filter_by(user_id=int(user_id)).first()
    if pref:
        db.session.delete(pref)
        db.session.commit()
    return _dashboard_default_widget_keys()


def _dashboard_format_value(value, suffix="", decimals=2):
    try:
        number = float(value or 0)
    except Exception:
        number = 0.0
    try:
        decimals = max(0, min(int(decimals), 2))
    except Exception:
        decimals = 2

    if decimals == 0:
        text = f"{int(round(number)):,}".replace(",", ".")
    else:
        text = f"{number:.{decimals}f}"
    suffix = str(suffix or "").strip()
    if suffix == "%":
        return text + "%"
    if suffix:
        return text + " " + suffix
    return text


def _dashboard_prepare_view(selected_keys, payload, user_id=None):
    kpis = []
    charts = []
    custom_payload = payload.get("custom_widgets", {}) or {}

    for key in selected_keys or []:
        meta = _dashboard_resolve_widget_meta(user_id, key)
        if not meta:
            continue

        if meta.get("custom"):
            data = custom_payload.get(key, {}) or {}
            item = dict(meta)
            item["value"] = data.get("value", 0)
            item["display_value"] = data.get("display_value", "")
            if meta.get("kind") == "kpi":
                if not item["display_value"]:
                    item["display_value"] = _dashboard_format_value(item["value"], meta.get("suffix", ""), meta.get("decimals", 2))
                kpis.append(item)
            else:
                item["image"] = data.get("image", "") or _dashboard_empty_chart(item.get("title", "Visualización"), "No hay información disponible")
                charts.append(item)
            continue

        if meta.get("kind") == "kpi":
            item = dict(meta)
            item["value"] = float(payload.get(meta.get("value_key"), 0) or 0)
            item["display_value"] = _dashboard_format_value(item["value"], meta.get("suffix", ""), meta.get("decimals", 2))
            kpis.append(item)
            continue

        item = dict(meta)
        value_key = meta.get("value_key")
        if value_key:
            item["value"] = float(payload.get(value_key, 0) or 0)
            item["display_value"] = _dashboard_format_value(item["value"], meta.get("suffix", "%"), meta.get("decimals", 2))
        else:
            item["value"] = meta.get("display_value", "")
            item["display_value"] = meta.get("display_value", "")
        item["image"] = payload.get(meta.get("image_key"), "") or ""
        charts.append(item)

    return kpis, charts


def _dashboard_latest_pci_data():
    try:
        model = globals().get("PciAnalysisRun")
        if model is not None:
            row = model.query.order_by(model.id.desc()).first()
            if row:
                pct = max(0.0, min(100.0, float(getattr(row, "nivel_promedio_general", 0) or 0)))
                radar = ""
                try:
                    resultados = json.loads(getattr(row, "resultados_json", "{}") or "{}")
                    radar_fn = globals().get("generar_pci_radar_base64")
                    if radar_fn and resultados:
                        radar = radar_fn(resultados) or ""
                except Exception:
                    radar = ""
                return {"pct": pct, "radar_b64": radar}
    except Exception as exc:
        print("No se pudo leer madurez PCI-DSS para el tablero:", repr(exc))
    return {"pct": 0.0, "radar_b64": ""}


def _dashboard_latest_soc2_data():
    try:
        model = globals().get("Soc2MadurezRun")
        if model is not None:
            row = (
                model.query
                .filter(func.upper(model.estado) == "FINALIZADO")
                .order_by(model.id.desc())
                .first()
            ) or model.query.order_by(model.id.desc()).first()
            if row:
                pct = max(0.0, min(100.0, float(getattr(row, "pct_general", 0) or 0)))
                return {"pct": pct, "radar_b64": getattr(row, "radar_overall_b64", None) or ""}
    except Exception as exc:
        print("No se pudo leer madurez SOC 2 para el tablero:", repr(exc))
    return {"pct": 0.0, "radar_b64": ""}


def _dashboard_latest_ai_data():
    db_path = globals().get("AI_MADUREZ_DB_PATH") or os.path.join(app.instance_path, "ai_madurez_42001.db")
    try:
        if not os.path.exists(db_path):
            return {"pct": 0.0, "radar_b64": ""}
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT pct_general, radar_overall_b64
            FROM ai_madurez_runs
            WHERE UPPER(COALESCE(estado, '')) = 'FINALIZADO'
            ORDER BY id DESC LIMIT 1
        """).fetchone()
        if row is None:
            row = conn.execute("""
                SELECT pct_general, radar_overall_b64
                FROM ai_madurez_runs
                ORDER BY id DESC LIMIT 1
            """).fetchone()
        conn.close()
        if row:
            pct = max(0.0, min(100.0, float(row["pct_general"] or 0)))
            return {"pct": pct, "radar_b64": row["radar_overall_b64"] or ""}
    except Exception as exc:
        print("No se pudo leer madurez de Gestión de IA para el tablero:", repr(exc))
    return {"pct": 0.0, "radar_b64": ""}


def _dashboard_latest_data_maturity_data():
    try:
        model = globals().get("DatosMadurezRun")
        if model is None:
            return {"pct": 0.0, "radar_b64": ""}
        row = (
            model.query
            .filter(func.upper(model.estado) == "FINALIZADO")
            .order_by(model.id.desc())
            .first()
        ) or model.query.order_by(model.id.desc()).first()
        if not row:
            return {"pct": 0.0, "radar_b64": ""}
        pct = max(0.0, min(100.0, float(getattr(row, "pct_general", 0) or 0)))
        radar = ""
        try:
            resumen = json.loads(getattr(row, "resumen_json", "{}") or "{}")
            radar_fn = globals().get("generar_radar_datos_base64")
            if radar_fn and resumen:
                radar = radar_fn(resumen) or ""
        except Exception:
            radar = ""
        return {"pct": pct, "radar_b64": radar}
    except Exception as exc:
        print("No se pudo leer madurez de Datos Personales para el tablero:", repr(exc))
        return {"pct": 0.0, "radar_b64": ""}


def _dashboard_maturity_data(source_key):
    if source_key == "maturity_iso_pct":
        data = _dashboard_latest_iso_data() or {}
        return {"pct": float(data.get("pct", 0) or 0), "radar_b64": data.get("radar_b64", "") or ""}
    if source_key == "maturity_nist_pct":
        data = _dashboard_latest_nist_data() or {}
        return {"pct": float(data.get("pct", 0) or 0), "radar_b64": data.get("radar_b64", "") or ""}
    if source_key == "maturity_data_pct":
        return _dashboard_latest_data_maturity_data()
    if source_key == "maturity_pci_pct":
        return _dashboard_latest_pci_data()
    if source_key == "maturity_soc2_pct":
        return _dashboard_latest_soc2_data()
    if source_key == "maturity_ai_pct":
        return _dashboard_latest_ai_data()
    return {"pct": 0.0, "radar_b64": ""}


def _dashboard_risk_rank(raw):
    txt = str(raw or "").strip().upper()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    if "EXTREMO" in txt or "CRITICO" in txt:
        return 5
    if "MUY ALTO" in txt:
        return 4
    if re.search(r"\bALTO\b", txt):
        return 3
    if "MODERADO" in txt or "MEDIO" in txt:
        return 2
    if "BAJO" in txt:
        return 1
    return 0


def _dashboard_active_risks():
    try:
        return [r for r in Riesgo.query.all() if not bool(getattr(r, "archivado", False))]
    except Exception:
        return []


def _dashboard_metric_value(source_key, user_id=None):
    source_key = str(source_key or "").strip()
    try:
        if source_key.startswith("maturity_"):
            return float((_dashboard_maturity_data(source_key) or {}).get("pct", 0) or 0)
        if source_key == "scorecard_average_pct":
            return float(_dashboard_latest_scorecard_terceros_pct() or 0)
        if source_key == "risks_active_count":
            return float(len(_dashboard_active_risks()))
        if source_key == "risks_outside_appetite_count":
            risks = _dashboard_active_risks()
            try:
                cfg = MetricConfigRiesgos.query.first()
                appetite_rank = _dashboard_risk_rank(getattr(cfg, "apetito_residual_definido", "") if cfg else "") or 2
            except Exception:
                appetite_rank = 2
            return float(sum(1 for r in risks if _dashboard_risk_rank(getattr(r, "riesgo_residual", "")) > appetite_rank))
        if source_key == "incidents_open_count":
            db_path = globals().get("INCIDENTES_DB_PATH") or os.path.join(app.instance_path, "incidentes.db")
            if not os.path.exists(db_path):
                return 0.0
            conn = sqlite3.connect(db_path)
            row = conn.execute("""
                SELECT COUNT(*) FROM registro_incidentes
                WHERE UPPER(TRIM(COALESCE(estado, ''))) NOT IN
                      ('CERRADO', 'CERRADA', 'CLOSED', 'RESUELTO', 'RESUELTA')
            """).fetchone()
            conn.close()
            return float(row[0] if row else 0)
        if source_key == "incidents_compliance_pct":
            model = globals().get("MetricaIncidente")
            if model is None:
                return 0.0
            value = db.session.query(func.avg(model.cumplimiento_global)).filter(model.cumplimiento_global.isnot(None)).scalar()
            return float(value or 0)
        if source_key in {"vulnerabilities_open_count", "vulnerabilities_critical_count"}:
            items = VulnerabilidadRegistro.query.all()
            open_items = []
            for item in items:
                estado = str(getattr(item, "estado", "") or "").strip().upper()
                if estado not in {"CERRADO", "CERRADA", "CLOSED", "RESUELTO", "RESUELTA"}:
                    open_items.append(item)
            if source_key == "vulnerabilities_open_count":
                return float(len(open_items))
            return float(sum(1 for item in open_items if "CRIT" in str(getattr(item, "clasificacion", "") or "").upper()))
        if source_key in {"plans_open_count", "plans_overdue_count"}:
            # IMPORTANTE: usar la MISMA fuente del módulo web /planes_accion.
            # Antes el dashboard/mobile consultaba MejoraPlanRegistro (mejora_planes),
            # mientras el módulo real de Planes de Acción usa ContinuousActionPlan
            # en instance/planes_accion.db. Esa diferencia generaba conteos incongruentes.
            items = ContinuousActionPlan.query.order_by(ContinuousActionPlan.id.desc()).limit(10000).all()
            today = date.today()
            effective = [pa_effective_status(item, today) for item in items]

            if source_key == "plans_open_count":
                # Todo plan que todavía requiere seguimiento, incluidos En proceso,
                # Pendiente y Vencido. Se excluyen únicamente estados cerrados/cancelados.
                return float(sum(
                    1 for status in effective
                    if not pa_status_closed(status)
                ))

            return float(sum(1 for status in effective if status == "Vencido"))
        if source_key == "legal_noncompliant_count":
            return float(sum(1 for item in RequisitoLegal.query.all() if "NO CUMPLE" in str(getattr(item, "estado", "") or "").upper() or "INCUMPLE" in str(getattr(item, "estado", "") or "").upper()))
        if source_key == "providers_high_count":
            return float(sum(1 for item in ProveedorEvaluacion.query.all() if "ALTA" in str(getattr(item, "criticidad_texto", "") or "").upper()))
        if source_key == "security_culture_pct":
            model = globals().get("MetricasCultura")
            if model is None:
                return 0.0
            row = model.query.order_by(model.anio.desc(), model.mes.desc(), model.id.desc()).first()
            return float(getattr(row, "resultado_meta_general", 0) or 0) if row else 0.0
    except Exception as exc:
        print(f"No se pudo calcular la fuente {source_key}:", repr(exc))
    return 0.0


def _dashboard_parse_date(raw):
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        if isinstance(raw, date):
            return datetime.combine(raw, datetime.min.time())
    except Exception:
        pass
    txt = str(raw).strip()
    if not txt:
        return None
    txt_iso = txt.replace("Z", "+00:00")
    try:
        value = datetime.fromisoformat(txt_iso)
        if getattr(value, "tzinfo", None):
            value = value.replace(tzinfo=None)
        return value
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(txt[:19], fmt)
        except Exception:
            continue
    return None


_DASHBOARD_MONTHS_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _dashboard_month_label(key):
    try:
        year, month = [int(x) for x in str(key).split("-")[:2]]
        return f"{_DASHBOARD_MONTHS_ES[month - 1]} {year}"
    except Exception:
        return str(key)


def _dashboard_monthly_count_series(values, limit=12):
    counts = Counter()
    for raw in values or []:
        dt_value = _dashboard_parse_date(raw)
        if dt_value:
            counts[dt_value.strftime("%Y-%m")] += 1
    keys = sorted(counts.keys())[-max(1, int(limit or 12)):]
    return [_dashboard_month_label(k) for k in keys], [float(counts[k]) for k in keys]


def _dashboard_distribution_risks():
    labels = ["Bajo", "Medio", "Alto", "Muy Alto", "Extremo"]
    values = {label: 0 for label in labels}
    for item in _dashboard_active_risks():
        rank = _dashboard_risk_rank(getattr(item, "riesgo_residual", ""))
        if rank == 1:
            values["Bajo"] += 1
        elif rank == 2:
            values["Medio"] += 1
        elif rank == 3:
            values["Alto"] += 1
        elif rank == 4:
            values["Muy Alto"] += 1
        elif rank == 5:
            values["Extremo"] += 1
    return labels, [float(values[label]) for label in labels]


def _dashboard_incident_db_rows(columns_candidates):
    db_path = globals().get("INCIDENTES_DB_PATH") or os.path.join(app.instance_path, "incidentes.db")
    if not os.path.exists(db_path):
        return [], None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(registro_incidentes)").fetchall()]
        column = next((candidate for candidate in columns_candidates if candidate in cols), None)
        if not column:
            return [], None
        rows = conn.execute(f"SELECT {column} AS value FROM registro_incidentes WHERE {column} IS NOT NULL AND TRIM(CAST({column} AS TEXT)) <> ''").fetchall()
        return rows, column
    finally:
        conn.close()


def _dashboard_distribution_incidents():
    labels = ["Bajo", "Medio", "Alto", "Crítico"]
    values = {label: 0 for label in labels}
    rows, _ = _dashboard_incident_db_rows(["clasificacion_incidente", "clasificacion", "criticidad", "nivel", "tipo_incidente", "categoria_incidente"])
    for row in rows:
        txt = unicodedata.normalize("NFKD", str(row["value"] or "").upper())
        txt = "".join(c for c in txt if not unicodedata.combining(c))
        if "CRIT" in txt:
            values["Crítico"] += 1
        elif "ALTO" in txt:
            values["Alto"] += 1
        elif "MEDIO" in txt or "MEDIA" in txt or "MODER" in txt:
            values["Medio"] += 1
        elif "BAJO" in txt or "BAJA" in txt:
            values["Bajo"] += 1
    return labels, [float(values[label]) for label in labels]


def _dashboard_distribution_vulnerabilities():
    labels = ["Baja", "Media", "Alta", "Crítica"]
    values = {label: 0 for label in labels}
    try:
        items = VulnerabilidadRegistro.query.all()
    except Exception:
        items = []
    for item in items:
        candidates = [
            getattr(item, "clasificacion", None), getattr(item, "severidad", None),
            getattr(item, "criticidad", None), getattr(item, "nivel_criticidad", None),
            getattr(item, "criticidad_vulnerabilidad", None), getattr(item, "impacto", None),
            getattr(item, "prioridad", None),
        ]
        txt = " ".join(str(v or "") for v in candidates).upper()
        txt = unicodedata.normalize("NFKD", txt)
        txt = "".join(c for c in txt if not unicodedata.combining(c))
        if "CRIT" in txt:
            values["Crítica"] += 1
        elif "ALTA" in txt or "HIGH" in txt:
            values["Alta"] += 1
        elif "MEDIA" in txt or "MEDIUM" in txt or "MODER" in txt:
            values["Media"] += 1
        elif "BAJA" in txt or "LOW" in txt or "INFO" in txt:
            values["Baja"] += 1
    return labels, [float(values[label]) for label in labels]


def _dashboard_distribution_providers():
    labels = ["Muy baja", "Baja", "Media", "Alta"]
    values = {label: 0 for label in labels}
    try:
        items = ProveedorEvaluacion.query.all()
    except Exception:
        items = []
    for item in items:
        txt = str(getattr(item, "criticidad_texto", "") or "").lower()
        if "muy baja" in txt:
            values["Muy baja"] += 1
        elif "baja" in txt:
            values["Baja"] += 1
        elif "media" in txt:
            values["Media"] += 1
        elif "alta" in txt:
            values["Alta"] += 1
    return labels, [float(values[label]) for label in labels]


def _dashboard_distribution_plans():
    # Misma fuente y mismo estado efectivo del módulo /planes_accion.
    labels = ["Abierto", "En proceso", "Vencido", "Cerrado", "Cancelado", "Otros"]
    values = {label: 0 for label in labels}
    try:
        items = ContinuousActionPlan.query.order_by(ContinuousActionPlan.id.desc()).limit(10000).all()
        today = date.today()
    except Exception:
        items = []
        today = date.today()

    for item in items:
        status = pa_effective_status(item, today)
        if status in values and status != "Otros":
            values[status] += 1
        else:
            values["Otros"] += 1
    return labels, [float(values[label]) for label in labels]


def _dashboard_distribution_legal():
    labels = ["Cumple", "Parcial", "No cumple", "Sin estado"]
    values = {label: 0 for label in labels}
    try:
        items = RequisitoLegal.query.all()
    except Exception:
        items = []
    for item in items:
        txt = str(getattr(item, "estado", "") or "").strip().upper()
        if txt == "CUMPLE":
            values["Cumple"] += 1
        elif "PARCIAL" in txt:
            values["Parcial"] += 1
        elif "NO CUMPLE" in txt or "INCUMPLE" in txt:
            values["No cumple"] += 1
        else:
            values["Sin estado"] += 1
    return labels, [float(values[label]) for label in labels]


def _dashboard_timeline_risks():
    return _dashboard_monthly_count_series([getattr(item, "fecha_identificacion", None) for item in _dashboard_active_risks()])


def _dashboard_timeline_incidents():
    rows, _ = _dashboard_incident_db_rows(["fecha_registro", "fecha_incidente", "fecha_reporte", "created_at", "fecha", "fecha_creacion"])
    return _dashboard_monthly_count_series([row["value"] for row in rows])


def _dashboard_timeline_vulnerabilities():
    try:
        items = VulnerabilidadRegistro.query.all()
    except Exception:
        items = []
    values = [getattr(item, "fecha_identificacion", None) or getattr(item, "created_at", None) for item in items]
    return _dashboard_monthly_count_series(values)


def _dashboard_timeline_plans():
    try:
        items = ContinuousActionPlan.query.order_by(ContinuousActionPlan.id.asc()).limit(10000).all()
    except Exception:
        items = []
    values = [getattr(item, "created_at", None) or getattr(item, "due_date", None) for item in items]
    return _dashboard_monthly_count_series(values)


def _dashboard_timeline_culture():
    model = globals().get("MetricasCultura")
    if model is None:
        return [], []
    try:
        rows = model.query.order_by(model.anio.asc(), model.mes.asc(), model.id.asc()).all()
    except Exception:
        return [], []
    values_by_key = {}
    for row in rows:
        try:
            year = int(getattr(row, "anio", 0) or 0)
            month = int(getattr(row, "mes", 0) or 0)
            if year > 0 and 1 <= month <= 12:
                values_by_key[f"{year:04d}-{month:02d}"] = float(getattr(row, "resultado_meta_general", 0) or 0)
        except Exception:
            continue
    keys = sorted(values_by_key.keys())[-12:]
    return [_dashboard_month_label(key) for key in keys], [values_by_key[key] for key in keys]


_DASHBOARD_DISTRIBUTION_SOURCES = {
    "risks_residual_distribution": _dashboard_distribution_risks,
    "incidents_classification_distribution": _dashboard_distribution_incidents,
    "vulnerabilities_severity_distribution": _dashboard_distribution_vulnerabilities,
    "providers_criticality_distribution": _dashboard_distribution_providers,
    "plans_status_distribution": _dashboard_distribution_plans,
    "legal_status_distribution": _dashboard_distribution_legal,
}

_DASHBOARD_TIMELINE_SOURCES = {
    "risks_timeline": _dashboard_timeline_risks,
    "incidents_timeline": _dashboard_timeline_incidents,
    "vulnerabilities_timeline": _dashboard_timeline_vulnerabilities,
    "plans_timeline": _dashboard_timeline_plans,
    "security_culture_timeline": _dashboard_timeline_culture,
}


def _dashboard_source_snapshot(source_key, user_id=None, cache=None):
    if cache is not None and source_key in cache:
        return cache[source_key]
    meta = DASHBOARD_DATA_SOURCE_MAP.get(source_key, {})
    kind = meta.get("data_kind", "scalar")
    result = {
        "source_key": source_key,
        "data_kind": kind,
        "value": 0.0,
        "unit": meta.get("unit", ""),
        "decimals": int(meta.get("decimals", 2) or 0),
        "labels": [],
        "values": [],
        "radar_b64": "",
        "meta": meta,
    }
    try:
        if kind == "maturity":
            data = _dashboard_maturity_data(source_key)
            result["value"] = float(data.get("pct", 0) or 0)
            result["radar_b64"] = data.get("radar_b64", "") or ""
        elif kind == "distribution":
            labels, values = _DASHBOARD_DISTRIBUTION_SOURCES.get(source_key, lambda: ([], []))()
            result["labels"] = list(labels or [])
            result["values"] = [float(v or 0) for v in (values or [])]
            result["value"] = float(sum(result["values"]))
        elif kind == "timeline":
            labels, values = _DASHBOARD_TIMELINE_SOURCES.get(source_key, lambda: ([], []))()
            result["labels"] = list(labels or [])
            result["values"] = [float(v or 0) for v in (values or [])]
            result["value"] = float(result["values"][-1]) if result["values"] else 0.0
        else:
            result["value"] = float(_dashboard_metric_value(source_key, user_id) or 0)
    except Exception as exc:
        print(f"No se pudo construir la fuente visual {source_key}:", repr(exc))
    if cache is not None:
        cache[source_key] = result
    return result


def _dashboard_metric_snapshot(source_key, user_id=None, cache=None):
    return _dashboard_source_snapshot(source_key, user_id, cache)


def _dashboard_nice_scale(value):
    try:
        value = max(0.0, float(value or 0))
    except Exception:
        value = 0.0
    if value <= 0:
        return 10.0
    magnitude = 10 ** math.floor(math.log10(value))
    for factor in (1, 2, 5, 10, 20):
        candidate = factor * magnitude
        if candidate >= value * 1.15:
            return float(candidate)
    return float(10 * magnitude)


def _dashboard_scalar_ring_b64(value, title="", subtitle="", unit="", decimals=2):
    try:
        value = max(0.0, float(value or 0))
    except Exception:
        value = 0.0
    scale = 100.0 if unit == "%" else _dashboard_nice_scale(value)
    current = min(value, scale)
    remaining = max(0.0, scale - current)
    fig, ax = plt.subplots(figsize=(8.0, 5.6))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    ax.pie(
        [current, remaining] if scale > 0 else [0, 1],
        startangle=90,
        counterclock=False,
        colors=["#0b5fa5", "#e7edf4"],
        wedgeprops=dict(width=0.34, edgecolor="white", linewidth=2),
    )
    display = _dashboard_format_value(value, unit, decimals)
    ax.text(0, 0.08, display, ha="center", va="center", fontsize=25, fontweight="bold", color="#0b1220")
    ax.text(0, -0.14, "Valor actual", ha="center", va="center", fontsize=10, color="#64748b")
    if title:
        ax.set_title(title, fontsize=15, fontweight="bold", color="#0b1220", pad=12)
    if subtitle:
        fig.text(0.5, 0.03, subtitle, ha="center", fontsize=10, color="#4b5563")
    ax.set_aspect("equal")
    return _dashboard_fig_to_b64(fig)


def _dashboard_pie_b64(labels, values, title="", subtitle=""):
    labels = list(labels or [])
    values = [float(v or 0) for v in (values or [])]
    if not labels or not values or sum(values) <= 0:
        return _dashboard_empty_chart(title or "Sin datos", "No hay información para graficar")
    palette = ["#087c3d", "#84cc16", "#d39b00", "#c95508", "#b91c1c", "#5521a8", "#087ab8"]
    fig, ax = plt.subplots(figsize=(8.0, 5.6))
    fig.patch.set_facecolor("#ffffff")
    wedges, _, autotexts = ax.pie(
        values,
        labels=None,
        autopct=lambda pct: f"{pct:.0f}%" if pct >= 4 else "",
        startangle=90,
        counterclock=False,
        colors=[palette[i % len(palette)] for i in range(len(labels))],
        wedgeprops=dict(edgecolor="white", linewidth=2),
    )
    for txt in autotexts:
        txt.set_fontsize(9)
        txt.set_fontweight("bold")
    ax.legend(wedges, [f"{label}: {_dashboard_format_value(value, '', 0)}" for label, value in zip(labels, values)], loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False, fontsize=9)
    if title:
        ax.set_title(title, fontsize=15, fontweight="bold", color="#0b1220", pad=12)
    if subtitle:
        fig.text(0.5, 0.03, subtitle, ha="center", fontsize=10, color="#4b5563")
    ax.set_aspect("equal")
    return _dashboard_fig_to_b64(fig)


def _dashboard_bar_b64(labels, values, title="", subtitle="", horizontal=False, unit=""):
    labels = [str(label) for label in (labels or [])]
    values = [float(v or 0) for v in (values or [])]
    if not labels or not values:
        return _dashboard_empty_chart(title or "Sin datos", "No hay información para graficar")
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    positions = list(range(len(labels)))
    palette = ["#0b5fa5", "#16855b", "#d48b0b", "#b44747", "#6c4bc2", "#2386b7"]
    colors = [palette[i % len(palette)] for i in positions]
    if horizontal:
        bars = ax.barh(positions, values, color=colors)
        ax.set_yticks(positions, labels)
        ax.invert_yaxis()
        for bar, value in zip(bars, values):
            ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, "  " + _dashboard_format_value(value, unit, 2 if unit == "%" else 0), va="center", fontsize=9, fontweight="bold")
        ax.grid(axis="x", alpha=.20)
    else:
        bars = ax.bar(positions, values, color=colors)
        ax.set_xticks(positions, labels, rotation=25, ha="right")
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), _dashboard_format_value(value, unit, 2 if unit == "%" else 0), ha="center", va="bottom", fontsize=9, fontweight="bold")
        ax.grid(axis="y", alpha=.20)
    ax.spines[["top", "right"]].set_visible(False)
    if title:
        ax.set_title(title, fontsize=15, fontweight="bold", color="#0b1220", pad=12)
    if subtitle:
        fig.text(0.5, 0.01, subtitle, ha="center", fontsize=9.5, color="#4b5563")
    fig.tight_layout(rect=[0, .05, 1, 1])
    return _dashboard_fig_to_b64(fig)


def _dashboard_line_b64(labels, values, title="", subtitle="", unit=""):
    labels = [str(label) for label in (labels or [])]
    values = [float(v or 0) for v in (values or [])]
    if not labels or not values:
        return _dashboard_empty_chart(title or "Sin datos", "No hay información histórica para graficar")
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    x = list(range(len(labels)))
    ax.plot(x, values, marker="o", linewidth=2.5, markersize=6, color="#0b5fa5")
    ax.fill_between(x, values, [0] * len(values), alpha=.10, color="#0b5fa5")
    ax.set_xticks(x, labels, rotation=28, ha="right")
    ax.grid(axis="y", alpha=.22)
    ax.spines[["top", "right"]].set_visible(False)
    for xi, value in zip(x, values):
        ax.annotate(_dashboard_format_value(value, unit, 2 if unit == "%" else 0), (xi, value), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8.5, fontweight="bold")
    if title:
        ax.set_title(title, fontsize=15, fontweight="bold", color="#0b1220", pad=12)
    if subtitle:
        fig.text(0.5, 0.01, subtitle, ha="center", fontsize=9.5, color="#4b5563")
    fig.tight_layout(rect=[0, .05, 1, 1])
    return _dashboard_fig_to_b64(fig)


def _dashboard_render_custom_visualization(snapshot, view, title, subtitle):
    view = str(view or "gauge").strip().lower()
    kind = snapshot.get("data_kind", "scalar")
    unit = snapshot.get("unit", "")
    decimals = snapshot.get("decimals", 2)
    value = float(snapshot.get("value", 0) or 0)
    labels = snapshot.get("labels", []) or []
    values = snapshot.get("values", []) or []

    if view == "radar":
        return snapshot.get("radar_b64", "") or _dashboard_empty_chart(title, "No se encontró información por dominio para generar la araña")
    if view == "gauge":
        if unit == "%":
            gauge_pct = max(0.0, min(100.0, value))
            gauge_subtitle = subtitle
        else:
            scale = _dashboard_nice_scale(value)
            gauge_pct = max(0.0, min(100.0, (value / scale * 100.0) if scale > 0 else 0.0))
            gauge_subtitle = f"{subtitle} · Valor actual: {_dashboard_format_value(value, unit, decimals)}".strip(" ·")
        return _dashboard_gauge_b64(gauge_pct, title, gauge_subtitle)
    if view == "donut":
        if kind == "distribution":
            return _dashboard_donut_b64(labels, values, title=title, subtitle=subtitle)
        return _dashboard_scalar_ring_b64(value, title, subtitle, unit, decimals)
    if view == "pie":
        return _dashboard_pie_b64(labels, values, title, subtitle)
    if view == "bar_vertical":
        if not labels:
            labels, values = [snapshot.get("meta", {}).get("label", "Valor")], [value]
        return _dashboard_bar_b64(labels, values, title, subtitle, horizontal=False, unit=unit if kind == "timeline" else "")
    if view == "bar_horizontal":
        if not labels:
            labels, values = [snapshot.get("meta", {}).get("label", "Valor")], [value]
        return _dashboard_bar_b64(labels, values, title, subtitle, horizontal=True, unit=unit if kind == "timeline" else "")
    if view == "line":
        return _dashboard_line_b64(labels, values, title, subtitle, unit=unit)
    return ""


def _dashboard_custom_widget_form_data(form):
    source_key = str(form.get("source_key") or "").strip()
    source = DASHBOARD_DATA_SOURCE_MAP.get(source_key)
    if not source:
        return None, "Seleccione una fuente de datos válida."

    widget_type = str(form.get("widget_type") or "").strip().lower()
    allowed = list(source.get("allowed_views", []))
    if widget_type not in allowed:
        return None, "Seleccione una presentación válida para la fuente de datos."

    return {
        "title": source.get("default_title") or source.get("label") or "Visualización",
        "subtitle": source.get("default_subtitle") or "",
        "source_key": source_key,
        "widget_type": widget_type,
        "icon": source.get("icon", "bi-speedometer2"),
        "color": source.get("color", "blue"),
        "target_value": None,
        "suffix": source.get("unit", ""),
        "decimals": int(source.get("decimals", 2) or 0),
    }, None


def _dashboard_build_payload(selected_keys=None, user_id=None):
    if selected_keys is None:
        selected_keys = _dashboard_default_widget_keys()

    selected = {key for key in selected_keys if key in DASHBOARD_WIDGET_MAP}
    selected_custom = [key for key in selected_keys if _dashboard_custom_id_from_key(key)]

    payload = {
        "iso_radar_b64": "", "iso_pct": 0.0,
        "nist_radar_b64": "", "nist_pct": 0.0,
        "datos_gauge_b64": "", "datos_pct": 0.0,
        "scorecard_terceros_pct": 0.0,
        "pci_pct": 0.0, "pci_gauge_b64": "",
        "soc2_pct": 0.0, "soc2_radar_b64": "",
        "ai_maturity_pct": 0.0, "ai_radar_b64": "",
        "risks_active_count": 0.0,
        "risks_outside_appetite_count": 0.0,
        "incidents_open_count": 0.0,
        "incidents_compliance_pct": 0.0,
        "vulnerabilities_open_count": 0.0,
        "vulnerabilities_critical_count": 0.0,
        "plans_open_count": 0.0,
        "plans_overdue_count": 0.0,
        "legal_noncompliant_count": 0.0,
        "providers_high_count": 0.0,
        "security_culture_pct": 0.0,
        "riesgos_b64": "", "incidentes_b64": "", "vulnerabilidades_b64": "",
        "proveedores_criticidad_b64": "", "planes_accion_estado_b64": "",
        "requisitos_legales_estado_b64": "", "custom_widgets": {},
    }

    if selected.intersection({"kpi_iso", "chart_iso"}):
        iso_data = _dashboard_latest_iso_data()
        payload["iso_radar_b64"] = iso_data["radar_b64"] if "chart_iso" in selected else ""
        payload["iso_pct"] = round(float(iso_data["pct"] or 0), 2)
    if selected.intersection({"kpi_nist", "chart_nist"}):
        nist_data = _dashboard_latest_nist_data()
        payload["nist_radar_b64"] = nist_data["radar_b64"] if "chart_nist" in selected else ""
        payload["nist_pct"] = round(float(nist_data["pct"] or 0), 2)
    if selected.intersection({"kpi_datos", "chart_datos"}):
        datos_pct = _dashboard_latest_datos_pct()
        payload["datos_pct"] = round(float(datos_pct or 0), 2)
        if "chart_datos" in selected:
            payload["datos_gauge_b64"] = _dashboard_gauge_b64(datos_pct, "Cumplimiento", "Protección de datos personales")
    if "kpi_scorecard" in selected:
        payload["scorecard_terceros_pct"] = round(float(_dashboard_latest_scorecard_terceros_pct() or 0), 2)
    if selected.intersection({"kpi_pci", "chart_pci"}):
        pci_data = _dashboard_latest_pci_data()
        payload["pci_pct"] = round(float(pci_data.get("pct", 0) or 0), 2)
        if "chart_pci" in selected:
            payload["pci_gauge_b64"] = _dashboard_gauge_b64(payload["pci_pct"], "Madurez", "PCI-DSS")
    if selected.intersection({"kpi_soc2", "chart_soc2"}):
        soc2_data = _dashboard_latest_soc2_data()
        payload["soc2_pct"] = round(float(soc2_data.get("pct", 0) or 0), 2)
        if "chart_soc2" in selected:
            payload["soc2_radar_b64"] = soc2_data.get("radar_b64") or _dashboard_gauge_b64(payload["soc2_pct"], "Madurez", "SOC 2")
    if selected.intersection({"kpi_ai", "chart_ai"}):
        ai_data = _dashboard_latest_ai_data()
        payload["ai_maturity_pct"] = round(float(ai_data.get("pct", 0) or 0), 2)
        if "chart_ai" in selected:
            payload["ai_radar_b64"] = ai_data.get("radar_b64") or _dashboard_gauge_b64(payload["ai_maturity_pct"], "Madurez", "ISO/IEC 42001")

    metric_to_payload = {
        "kpi_riesgos_activos": ("risks_active_count", "risks_active_count"),
        "kpi_riesgos_fuera_apetito": ("risks_outside_appetite_count", "risks_outside_appetite_count"),
        "kpi_incidentes_abiertos": ("incidents_open_count", "incidents_open_count"),
        "kpi_incidentes_cumplimiento": ("incidents_compliance_pct", "incidents_compliance_pct"),
        "kpi_vulnerabilidades_abiertas": ("vulnerabilities_open_count", "vulnerabilities_open_count"),
        "kpi_vulnerabilidades_criticas": ("vulnerabilities_critical_count", "vulnerabilities_critical_count"),
        "kpi_planes_abiertos": ("plans_open_count", "plans_open_count"),
        "kpi_planes_vencidos": ("plans_overdue_count", "plans_overdue_count"),
        "kpi_requisitos_no_cumple": ("legal_noncompliant_count", "legal_noncompliant_count"),
        "kpi_proveedores_alta": ("providers_high_count", "providers_high_count"),
        "kpi_cultura_seguridad": ("security_culture_pct", "security_culture_pct"),
    }
    source_cache = {}
    for widget_key, (payload_key, source_key) in metric_to_payload.items():
        if widget_key in selected:
            payload[payload_key] = _dashboard_metric_snapshot(source_key, user_id, source_cache)["value"]

    if "chart_riesgos" in selected:
        payload["riesgos_b64"] = _dashboard_riesgos_residuales_chart()
    if "chart_incidentes" in selected:
        payload["incidentes_b64"] = _dashboard_incidentes_chart()
    if "chart_vulnerabilidades" in selected:
        payload["vulnerabilidades_b64"] = _dashboard_vulnerabilidades_chart()
    if "chart_proveedores" in selected:
        payload["proveedores_criticidad_b64"] = _dashboard_proveedores_criticidad_chart()
    if "chart_planes_accion" in selected:
        payload["planes_accion_estado_b64"] = _dashboard_planes_accion_estado_chart()
    if "chart_requisitos_legales" in selected:
        payload["requisitos_legales_estado_b64"] = _dashboard_requisitos_legales_estado_chart()

    custom_map = {_dashboard_custom_key(widget.id): widget for widget in _dashboard_custom_widgets_for_user(user_id)}
    for key in selected_custom:
        widget = custom_map.get(key)
        if not widget:
            continue
        meta = _dashboard_custom_widget_meta(widget)
        snapshot = _dashboard_source_snapshot(widget.source_key, user_id, source_cache)
        value = float(snapshot.get("value", 0) or 0)
        data_kind = snapshot.get("data_kind", "scalar")
        if data_kind == "distribution":
            display_value = f"Total {_dashboard_format_value(value, '', 0)}"
        elif data_kind == "timeline":
            display_value = "Último: " + _dashboard_format_value(value, snapshot.get("unit", ""), snapshot.get("decimals", 0))
        else:
            display_value = _dashboard_format_value(value, snapshot.get("unit", ""), snapshot.get("decimals", 2))
        image = ""
        if meta.get("kind") == "chart":
            image = _dashboard_render_custom_visualization(snapshot, widget.widget_type, widget.title, widget.subtitle or "")
        payload["custom_widgets"][key] = {
            "value": value,
            "display_value": display_value,
            "image": image,
            "source_key": widget.source_key,
            "widget_type": widget.widget_type,
        }

    return payload


def _dashboard_latest_datos_pct():
    try:
        run = DatosMadurezRun.query.order_by(DatosMadurezRun.id.desc()).first()
        if run:
            return float(run.pct_general or 0)
    except Exception:
        pass
    return 0.0

def _dashboard_latest_scorecard_terceros_pct():
    """
    Score promedio de Security Scorecard de Terceros.
    Fuente: instance/scorecard_proponentes.db
    Tabla: scorecard_proponentes_runs
    """
    try:
        db_path = os.path.join(app.instance_path, "scorecard_proponentes.db")

        if not os.path.exists(db_path):
            return 0.0

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT AVG(score_total) AS promedio
            FROM scorecard_proponentes_runs
            WHERE estado = 'finalizado'
              AND score_total IS NOT NULL
        """)

        row = cur.fetchone()
        conn.close()

        return round(float(row["promedio"] or 0), 2)

    except Exception as e:
        print("ERROR DASHBOARD SCORECARD TERCEROS:", repr(e))
        return 0.0

def _dashboard_riesgos_residuales_chart():
    try:
        items = Riesgo.query.order_by(Riesgo.id.desc()).all()
    except Exception:
        try:
            items = RiesgoRegistro.query.order_by(RiesgoRegistro.id.desc()).all()
        except Exception:
            items = []

    niveles = ["Bajo", "Medio", "Alto", "Muy Alto", "Extremo"]
    conteos = {k: 0 for k in niveles}

    for it in items:
        raw = (
            getattr(it, "riesgo_residual", None)
            or getattr(it, "nivel_riesgo_residual", None)
            or getattr(it, "riesgo_residual_nivel", None)
            or ""
        )
        txt = str(raw).upper().strip()

        if "EXTREMO" in txt:
            conteos["Extremo"] += 1
        elif "MUY ALTO" in txt:
            conteos["Muy Alto"] += 1
        elif re.search(r"\bALTO\b", txt):
            conteos["Alto"] += 1
        elif "MEDIO" in txt or "MODERADO" in txt:
            conteos["Medio"] += 1
        elif "BAJO" in txt:
            conteos["Bajo"] += 1

    return _dashboard_donut_b64(
        niveles,
        [conteos[n] for n in niveles],
        title="Riesgos residuales",
        subtitle="Distribución por nivel"
    )

def _obtener_columnas_sqlite(db_path, tabla):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({tabla})")
        cols = [row[1] for row in cur.fetchall()]
        conn.close()
        return cols
    except Exception as e:
        print(f"ERROR obteniendo columnas de {tabla}: {e}")
        return []

def _dashboard_incidentes_chart():
    buckets = ["Bajo", "Medio", "Alto", "Crítico"]
    conteos = {k: 0 for k in buckets}

    def norm(txt):
        txt = str(txt or "").strip().upper()
        txt = (
            txt.replace("Á", "A")
               .replace("É", "E")
               .replace("Í", "I")
               .replace("Ó", "O")
               .replace("Ú", "U")
        )
        return txt

    def acumular_clasificacion(raw):
        txt = norm(raw)
        if not txt:
            return

        if "CRIT" in txt:
            conteos["Crítico"] += 1
        elif "ALTO" in txt:
            conteos["Alto"] += 1
        elif "MEDIO" in txt or "MEDIA" in txt or "MODER" in txt:
            conteos["Medio"] += 1
        elif "BAJO" in txt or "BAJA" in txt:
            conteos["Bajo"] += 1

    try:
        db_path = INCIDENTES_DB_PATH
        columnas = _obtener_columnas_sqlite(db_path, "registro_incidentes")

        posibles_columnas = [
            "clasificacion_incidente",
            "clasificacion",
            "criticidad",
            "nivel",
            "tipo_incidente",
            "categoria_incidente"
        ]

        columna_real = next((c for c in posibles_columnas if c in columnas), None)

        if not columna_real:
            print("ERROR DASHBOARD INCIDENTES: no existe una columna válida en registro_incidentes. Columnas encontradas:", columnas)
            return _dashboard_empty_chart(
                "Incidentes por clasificación",
                "No se encontró columna de clasificación en registro_incidentes"
            )

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute(f"""
            SELECT {columna_real}
            FROM registro_incidentes
            WHERE {columna_real} IS NOT NULL
              AND TRIM({columna_real}) <> ''
        """)
        rows = c.fetchall()
        conn.close()

        for row in rows:
            acumular_clasificacion(row[columna_real])

    except Exception as e:
        print("ERROR DASHBOARD INCIDENTES:", str(e))
        return _dashboard_empty_chart(
            "Incidentes por clasificación",
            f"Error consultando registro_incidentes: {str(e)}"
        )

    return _dashboard_donut_b64(
        buckets,
        [conteos[n] for n in buckets],
        title="Incidentes por clasificación",
        subtitle="Fuente: registro_incidentes"
    )


def _dashboard_vulnerabilidades_chart():
    buckets = ["Baja", "Media", "Alta", "Crítica"]
    conteos = {k: 0 for k in buckets}

    def norm_sev(raw):
        txt = str(raw or "").strip().upper()
        txt = (
            txt.replace("Á", "A")
               .replace("É", "E")
               .replace("Í", "I")
               .replace("Ó", "O")
               .replace("Ú", "U")
        )
        return txt

    def acumular(raw):
        txt = norm_sev(raw)
        if not txt:
            return False

        if "CRIT" in txt or "CRITICAL" in txt:
            conteos["Crítica"] += 1
            return True
        elif "ALTA" in txt or "HIGH" in txt:
            conteos["Alta"] += 1
            return True
        elif "MEDIA" in txt or "MEDIUM" in txt or "MODERATE" in txt:
            conteos["Media"] += 1
            return True
        elif "BAJA" in txt or "LOW" in txt or "INFO" in txt:
            conteos["Baja"] += 1
            return True

        return False

    # =========================================================
    # 1) FUENTE PRINCIPAL: MATRIZ DE VULNERABILIDADES
    # =========================================================
    try:
        items = VulnerabilidadRegistro.query.order_by(VulnerabilidadRegistro.id.desc()).all()
    except Exception:
        items = []

    for it in items:
        # probar varios campos posibles del modelo
        candidatos = [
            getattr(it, "clasificacion", None),
            getattr(it, "severidad", None),
            getattr(it, "criticidad", None),
            getattr(it, "nivel_criticidad", None),
            getattr(it, "criticidad_vulnerabilidad", None),
            getattr(it, "impacto", None),
            getattr(it, "prioridad", None),
        ]

        encontrado = False
        for raw in candidatos:
            if acumular(raw):
                encontrado = True
                break

        # fallback adicional: revisar texto libre por si la severidad quedó embebida
        if not encontrado:
            texto_fallback = " ".join([
                str(getattr(it, "titulo", "") or ""),
                str(getattr(it, "nombre", "") or ""),
                str(getattr(it, "descripcion", "") or ""),
                str(getattr(it, "detalle", "") or ""),
            ])
            acumular(texto_fallback)

    # =========================================================
    # 2) FALLBACK: SI LA MATRIZ NO TRAJO CRÍTICAS, USAR HALLAZGOS
    # =========================================================
    if sum(conteos.values()) == 0 or conteos["Crítica"] == 0:
        try:
            findings = VulnerabilityScanFinding.query.order_by(VulnerabilityScanFinding.id.desc()).all()

            conteos_scan = {k: 0 for k in buckets}
            for f in findings:
                txt = norm_sev(getattr(f, "severidad", None))
                if "CRIT" in txt or "CRITICAL" in txt:
                    conteos_scan["Crítica"] += 1
                elif "ALTA" in txt or "HIGH" in txt:
                    conteos_scan["Alta"] += 1
                elif "MEDIA" in txt or "MEDIUM" in txt or "MODERATE" in txt:
                    conteos_scan["Media"] += 1
                elif "BAJA" in txt or "LOW" in txt or "INFO" in txt:
                    conteos_scan["Baja"] += 1

            # solo usar findings si realmente aportan datos
            if sum(conteos_scan.values()) > sum(conteos.values()):
                conteos = conteos_scan

        except Exception:
            pass

    return _dashboard_donut_b64(
        buckets,
        [conteos[n] for n in buckets],
        title="Vulnerabilidades por criticidad",
        subtitle="Fuente: módulo de vulnerabilidades"
    )


def _dashboard_proveedores_criticidad_chart():
    buckets = [
        "Criticidad muy baja",
        "Criticidad baja",
        "Criticidad media",
        "Criticidad alta"
    ]

    conteos = {k: 0 for k in buckets}

    try:
        items = ProveedorEvaluacion.query.order_by(ProveedorEvaluacion.id.desc()).all()

        for it in items:
            raw = str(getattr(it, "criticidad_texto", "") or "").strip().lower()

            if "muy baja" in raw:
                conteos["Criticidad muy baja"] += 1
            elif "baja" in raw:
                conteos["Criticidad baja"] += 1
            elif "media" in raw:
                conteos["Criticidad media"] += 1
            elif "alta" in raw:
                conteos["Criticidad alta"] += 1

    except Exception as e:
        return _dashboard_empty_chart(
            "Proveedores por criticidad",
            f"Error consultando proveedores: {str(e)}"
        )

    return _dashboard_donut_b64(
        buckets,
        [conteos[n] for n in buckets],
        title="Proveedores por criticidad",
        subtitle="Distribución de proveedores según criticidad"
    )


def _dashboard_planes_accion_estado_chart():
    # Fuente única: ContinuousActionPlan / instance/planes_accion.db.
    buckets = ["Abierto", "En proceso", "Vencido", "Cerrado", "Cancelado", "Otros"]
    conteos = {k: 0 for k in buckets}

    try:
        items = ContinuousActionPlan.query.order_by(ContinuousActionPlan.id.desc()).limit(10000).all()
        today = date.today()

        for it in items:
            status = pa_effective_status(it, today)
            if status in conteos and status != "Otros":
                conteos[status] += 1
            else:
                conteos["Otros"] += 1

    except Exception as e:
        return _dashboard_empty_chart(
            "Planes de acción por estado",
            f"Error consultando planes de acción: {str(e)}"
        )

    return _dashboard_donut_b64(
        buckets,
        [conteos[n] for n in buckets],
        title="Planes de acción por estado",
        subtitle="Estado efectivo de los planes de acción del SGSI"
    )


def _dashboard_requisitos_legales_estado_chart():
    buckets = ["Cumple", "Parcial", "No cumple", "Sin estado"]
    conteos = {k: 0 for k in buckets}

    try:
        items = RequisitoLegal.query.order_by(RequisitoLegal.id.desc()).all()

        for it in items:
            raw = str(getattr(it, "estado", "") or "").strip().lower()

            if raw == "cumple":
                conteos["Cumple"] += 1
            elif raw == "parcial":
                conteos["Parcial"] += 1
            elif raw == "no cumple":
                conteos["No cumple"] += 1
            else:
                conteos["Sin estado"] += 1

    except Exception as e:
        return _dashboard_empty_chart(
            "Requisitos legales por estado",
            f"Error consultando requisitos legales: {str(e)}"
        )

    return _dashboard_donut_b64(
        buckets,
        [conteos[n] for n in buckets],
        title="Requisitos legales por estado",
        subtitle="Cumplimiento de requisitos legales aplicables"
    )

# =========================
# Plantilla HTML única (integrada)
# =========================

BASE = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Arkyntech GRAC</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">

  <style>
    :root{
      /* Paleta Arkyntech ajustada: tonos más oscuros y mejor contraste */
      --arky-blue:#062b55;
      --arky-blue-2:#0b4a8f;
      --arky-blue-3:#1d5fae;
      --arky-blue-4:#3f8fd6;
      --arky-soft:#dcecff;
      --arky-soft-2:#c9e3ff;
      --arky-border:#a9cdeb;
      --arky-text:#102a4b;
      --arky-muted:#425f7f;
      --arky-purple:#3f148a;
      --arky-topbar-h:58px;
    }

    html, body{ min-height:100%; }

    body{
      margin:0;
      color:var(--arky-text);
      padding-top:var(--arky-topbar-h);
      background:
        linear-gradient(135deg, rgba(214,232,248,.96) 0%, rgba(202,224,245,.93) 42%, rgba(216,208,242,.86) 100%),
        radial-gradient(circle at 86% 24%, rgba(47,18,102,.23) 0, rgba(47,18,102,.23) 17%, transparent 18%),
        radial-gradient(circle at 6% 88%, rgba(18,84,157,.23) 0, rgba(18,84,157,.23) 22%, transparent 23%),
        url('/static/img/ccsgsi.jpg');
      background-size:cover;
      background-position:center;
      background-attachment:fixed;
      background-repeat:no-repeat;
    }

    body::before{
      content:"";
      position:fixed;
      inset:var(--arky-topbar-h) 0 0 0;
      pointer-events:none;
      z-index:-1;
      background:
        radial-gradient(circle at 96% 22%, rgba(47,18,102,.18), transparent 24%),
        radial-gradient(circle at 2% 76%, rgba(18,84,157,.17), transparent 26%);
    }

    .sgsi-topbar{
      position:fixed;
      top:0;
      left:0;
      right:0;
      height:var(--arky-topbar-h);
      min-height:var(--arky-topbar-h);
      background:rgba(248,252,255,.96);
      backdrop-filter:blur(18px);
      -webkit-backdrop-filter:blur(18px);
      border-bottom:1px solid rgba(207,229,255,.95);
      box-shadow:0 10px 24px rgba(20,89,166,.10);
      z-index:999997;
      overflow:hidden;
    }

    .sgsi-topbar-inner{
      height:var(--arky-topbar-h);
      min-height:var(--arky-topbar-h);
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
      padding:0 18px 0 14px;
      overflow:hidden;
    }

    .sgsi-brand{
      height:var(--arky-topbar-h);
      width:220px;
      min-width:220px;
      display:flex;
      align-items:center;
      justify-content:flex-start;
      text-decoration:none;
      overflow:hidden;
      margin-left:0;
      padding:0;
    }

    .sgsi-logo{
      height:44px;
      width:auto;
      max-width:205px;
      object-fit:contain;
      object-position:left center;
      filter:drop-shadow(0 4px 9px rgba(11,58,110,.14));
      margin:0;
      display:block;
    }

    .sgsi-title{ display:none !important; }
    .sgsi-main-nav{ display:none !important; }

    .sgsi-user-area{
      display:flex;
      align-items:center;
      gap:10px;
      min-width:max-content;
      position:relative;
      z-index:10060;
    }

    .sgsi-topbar,
    .sgsi-topbar-inner{
      overflow:visible !important;
    }

    .sgsi-user-area .dropdown-menu{
      position:absolute !important;
      top:calc(100% + 8px) !important;
      right:0 !important;
      left:auto !important;
      z-index:10070 !important;
      min-width:210px !important;
      margin:0 !important;
      transform:none !important;
    }

    .sgsi-user-area .dropdown-menu.show{
      display:block !important;
      visibility:visible !important;
      opacity:1 !important;
    }

    .sgsi-pill-login{
      border:1px solid var(--arky-border);
      background:#ffffff;
      color:var(--arky-blue) !important;
      border-radius:999px;
      padding:10px 18px;
      font-weight:850;
      text-decoration:none;
      box-shadow:0 8px 18px rgba(20,89,166,.08);
    }

    .sgsi-user-link{
      display:flex;
      align-items:center;
      color:#fff !important;
      background:linear-gradient(135deg, var(--arky-blue) 0%, var(--arky-blue-2) 46%, var(--arky-purple) 100%);
      border-radius:999px;
      padding:5px 12px 5px 6px;
      text-decoration:none;
      box-shadow:0 12px 26px rgba(20,89,166,.24);
      border:1px solid rgba(255,255,255,.38);
    }

    button.sgsi-user-link{
      font-family:inherit;
      line-height:1;
      appearance:none;
      -webkit-appearance:none;
      outline:none;
    }

    button.sgsi-user-link:focus,
    button.sgsi-user-link:focus-visible{
      box-shadow:0 0 0 3px rgba(52,125,220,.30),0 12px 26px rgba(20,89,166,.24);
    }

    .sgsi-user-photo{
      width:32px;
      height:32px;
      object-fit:cover;
      border-radius:50%;
      border:2px solid rgba(255,255,255,.82);
      background:#fff;
    }

    .sgsi-user-name{
      margin-left:7px;
      font-size:.78rem;
      font-weight:850;
      max-width:150px;
      overflow:hidden;
      text-overflow:ellipsis;
      white-space:nowrap;
    }

    .container.py-4{
      max-width:100% !important;
      padding:0 !important;
    }

    .dropdown-menu{
      border:1px solid var(--arky-border);
      border-radius:16px;
      box-shadow:0 18px 36px rgba(20,89,166,.16);
      overflow:hidden;
    }

    @media(max-width:1100px){
      .sgsi-topbar-inner{
        padding:0 12px;
      }

      .sgsi-brand{
        width:190px;
        min-width:190px;
      }

      .sgsi-logo{
        height:40px;
        max-width:180px;
      }
    }

    @media(max-width:575px){
      :root{
        --arky-topbar-h:62px;
      }

      .sgsi-topbar,
      .sgsi-topbar-inner,
      .sgsi-brand{
        height:var(--arky-topbar-h);
        min-height:var(--arky-topbar-h);
      }

      .sgsi-brand{
        width:160px;
        min-width:160px;
      }

      .sgsi-logo{
        height:36px;
        max-width:150px;
      }

      .sgsi-user-name{
        display:none;
      }

      .sgsi-user-link{
        padding:6px;
      }
    }
  </style>
</head>

<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>

{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    <script>
      document.addEventListener("DOMContentLoaded", function () {
        {% for category, message in messages %}
          Swal.fire({
            title: {{ (
              'Error'
              if category == 'danger'
              else 'Proceso exitoso'
              if category == 'success'
              else 'Atención'
              if category == 'warning'
              else 'Información'
            ) | tojson }},
            text: {{ message | tojson }},
            icon: {{ (
              'error'
              if category == 'danger'
              else 'success'
              if category == 'success'
              else 'warning'
              if category == 'warning'
              else 'info'
            ) | tojson }},
            confirmButtonText: "Aceptar",
            confirmButtonColor: "#0b4a8f",
            backdrop: true,
            allowOutsideClick: false
          });
        {% endfor %}
      });
    </script>
  {% endif %}
{% endwith %}

<body>

<header class="sgsi-topbar">
  <div class="container-fluid sgsi-topbar-inner">

    <a class="sgsi-brand" href="{{ url_for('menu') }}" title="Arkyntech GRAC">
      <img src="{{ url_for('static', filename='img/Arkynthec.png') }}" class="sgsi-logo" alt="Arkyntech GRAC">
    </a>

    {% if current_user %}
    <div class="sgsi-user-area dropdown">
      <button class="sgsi-user-link dropdown-toggle" type="button" data-bs-toggle="dropdown" data-bs-auto-close="true" aria-expanded="false" style="cursor:pointer;">
        <img src="{{ url_for('static', filename='uploads/profiles/' ~ current_user.photo_filename)
                     if current_user.photo_filename
                     else url_for('static', filename='img/default_user.png') }}"
             class="sgsi-user-photo" alt="Perfil">
        <span class="sgsi-user-name">{{ current_user.username }}</span>
      </button>

      <ul class="dropdown-menu dropdown-menu-end">
        <li><a class="dropdown-item" href="{{ url_for('perfil') }}">👤 Ver perfil</a></li>
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item text-danger" href="{{ url_for('logout') }}">🚪 Cerrar sesión</a></li>
      </ul>
    </div>
    {% endif %}

  </div>
</header>

<div class="container py-4">
  {{ content|safe }}
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>

</body>
</html>
"""

# ========================================
# Agrupado por secciones (NO cambia rutas)
# ========================================

MENU_SECTIONS = [
    {
        "title": "Gobierno / Dirección",
        "icon": "bi-diagram-3",
        "items": [
            {"label": "Declaración de Aplicabilidad (SoA)", "href": "/soa", "icon": "bi-diagram-3", "btn": "btn-primary", "module": "Contexto Interno"},
            {"label": "Gestión de Riesgos", "href": "/riesgos_menu", "icon": "bi-diagram-3", "btn": "btn-primary", "module": "Gestión de Riesgos"},
            {"label": "Objetivos del Sistema de Gestión", "href": "/objetivos_menu", "icon": "bi-diagram-3", "btn": "btn-primary", "module": "Objetivos del Sistema de Gestión"},
            {"label": "Partes Interesadas", "href": "/partes_menu", "icon": "bi-people-fill", "btn": "btn-primary", "module": "Partes Interesadas"},
            {"label": "Contexto Interno", "href": "/contexto_interno_menu", "icon": "bi-building-fill-gear", "btn": "btn-info text-white", "module": "Contexto Interno"},
            {"label": "Contexto Externo", "href": "/contexto_externo_menu", "icon": "bi-globe2", "btn": "btn-info text-white", "module": "Contexto Externo"},
            {"label": "DOFA", "href": "/dofa_menu", "icon": "bi-grid-3x3-gap-fill", "btn": "btn-info text-white", "module": "DOFA"},
            {"label": "PESI", "href": "/pesi", "icon": "bi-shield-lock-fill", "btn": "btn-primary", "module": "PESI"},
            {"label": "Informe Revisión por la Dirección", "href": "/revision_direccion", "icon": "bi-clipboard-data-fill", "btn": "btn-primary", "module": "Informe Revisión por la Dirección"},
            {"label": "Análisis de Riesgos de Procesos", "href": "/procesos_ia", "icon": "bi-diagram-3", "btn": "btn-primary", "module": "Análisis de Riesgos de Procesos con IA"},
        ],
    },
    {
        "title": "Documentación",
        "icon": "bi-journal-text",
        "items": [
            {"label": "Listado Maestro de Documentos", "href": "/docs_menu", "icon": "bi-file-earmark-text", "btn": "btn-primary", "module": "Listado Maestro de Documentos"},
            {"label": "Registro de Comunicaciones", "href": "/comunicaciones_menu", "icon": "bi-envelope-paper", "btn": "btn-primary", "module": "Registro de Comunicaciones"},
            {"label": "Requisitos Legales", "href": "/requisitos_menu", "icon": "bi-balance-scale", "btn": "btn-primary", "module": "Requisitos Legales"},
        ],
    },
    {
        "title": "Operación y Control",
        "icon": "bi-shield-check",
        "items": [
            {
                "label": "Gestión de Activos de Información",
                "href": "#",
                "icon": "bi-archive",
                "btn": "btn-primary",
                "module": "Gestión de Activos de Información",
                "children": [
                    {
                        "label": "Matrices de Activos",
                        "href": "#",
                        "icon": "bi-box-seam",
                        "btn": "btn-outline-primary",
                        "children": [
                            {
                                "label": "Inventario de Software",
                                "href": "/inventario_software_menu",
                                "icon": "bi-cpu",
                                "btn": "btn-outline-primary",
                                "module": "Inventario de Software"
                            },
                            {
                                "label": "Inventario de IA",
                                "href": "/inventario_ia_menu",
                                "icon": "bi-cpu-fill",
                                "btn": "btn-outline-primary",
                                "module": "Inventario de IA"
                            },
                            {
                                "label": "Inventario de Información",
                                "href": "/inventario_informacion_menu",
                                "icon": "bi-file-earmark-text",
                                "btn": "btn-outline-primary",
                                "module": "Inventario de Información"
                            },
                            {
                                "label": "Inventario de Datos Personales",
                                "href": "/inventario_datos_personales_menu",
                                "icon": "bi-shield-lock",
                                "btn": "btn-outline-primary",
                                "module": "Inventario de Datos Personales"
                            },
                            {
                                "label": "Inventario Físico",
                                "href": "/inventario_fisico_menu",
                                "icon": "bi-pc-display",
                                "btn": "btn-outline-primary",
                                "module": "Inventario Físico"
                            },
                        ]
                    },
                    {
                        "label": "Tablas de Valoración",
                        "href": "#",
                        "icon": "bi-bar-chart-line",
                        "btn": "btn-outline-primary",
                        "module": "Tablas de Valoración",
                                            "children": [
                            {
                                "label": "Confidencialidad",
                                "href": "/valor_confidencialidad",
                                "icon": "bi-lock-fill",
                                "btn": "btn-outline-primary",
                                "module": "Tablas de Valoración"
                            },
                            {
                                "label": "Integridad",
                                "href": "/valor_integridad",
                                "icon": "bi-shield-check",
                                "btn": "btn-outline-primary",
                                "module": "Tablas de Valoración"
                            },
                            {
                                "label": "Disponibilidad",
                                "href": "/valor_disponibilidad",
                                "icon": "bi-clock-history",
                                "btn": "btn-outline-primary",
                                "module": "Tablas de Valoración"
                            },
                            {
                                "label": "Criticidad del Activo",
                                "href": "/valor_criticidad_activo",
                                "icon": "bi-exclamation-diamond-fill",
                                "btn": "btn-outline-primary",
                                "module": "Tablas de Valoración"
                            },
                        ]
                    },
                    {
                        "label": "Dueños de Información",
                        "href": "/duenos_info",
                        "icon": "bi-person-badge",
                        "btn": "btn-outline-primary",
                        "module": "Dueños de Información"
                    },
                ]
            },
            {
                "label": "Gestión de Accesos",
                "href": "/accesos_menu",
                "icon": "bi-shield-lock",
                "btn": "btn-info text-white",
                "module": "Gestión de Accesos"
            },
            {
                "label": "Revisión de Accesos",
                "href": "/revision_accesos_menu",
                "icon": "bi-clipboard-check",
                "btn": "btn-info text-white",
                "module": "Revisión de Accesos"
            },
            {
                "label": "Gestión de Cambios (RFC)",
                "href": "/rfc_menu",
                "icon": "bi-arrow-left-right",
                "btn": "btn-primary",
                "module": "Gestión de Cambios (RFC)"
            },
        ],
    },
    {
        "title": "Gestión de Eventos",
        "icon": "bi-exclamation-triangle",
        "items": [
            {"label": "Centro de Alertas", "href": "/alertas", "icon": "bi-bell-fill", "btn": "btn-warning text-dark", "module": "Centro de Alertas"},
            {"label": "Registro de Incidentes", "href": "/incidentes", "icon": "bi-exclamation-triangle", "btn": "btn-danger", "module": "Registro de Incidentes"},
            {"label": "Planes de Respuesta a Incidentes", "href": "/planes_respuesta_incidentes", "icon": "bi-shield-check", "btn": "btn-primary", "module": "Planes de Respuesta a Incidentes"},
            {"label": "Registro de Vulnerabilidades", "href": "/vulnerabilidades_menu", "icon": "bi-bug", "btn": "btn-danger", "module": "Registro de Vulnerabilidades"},
            {"label": "Modelamiento de Amenazas", "href": "/modelamiento_amenazas", "icon": "bi-diagram-3", "btn": "btn-dark", "module": "Modelamiento de Amenazas"},
            {"label": "Superficie de Ataque y Escenarios", "href": "/superficie_ataque", "icon": "bi-bullseye", "btn": "btn-primary", "module": "Superficie de Ataque y Escenarios"},
            {"label": "Plan de Remediación", "href": "/plan_remediacion_menu", "icon": "bi-tools", "btn": "btn-primary", "module": "Plan de Remediación"},
        ],
    },
    {
        "title": "Competencias y Cultura",
        "icon": "bi-mortarboard",
        "items": [
            {"label": "Campañas de Concientización", "href": "/campanias_concientizacion_menu", "icon": "bi-bullseye", "btn": "btn-primary", "module": "Campañas de Concientización"},
            {"label": "Plan de Concientización y Formación", "href": "/plan_diseno_menu", "icon": "bi-journal-text", "btn": "btn-primary", "module": "Plan de Concientización y Formación"},
            {"label": "Seguimiento Plan de Concientización y Formación", "href": "/plan_cf/menu", "icon": "bi-graph-up", "btn": "btn-info", "module": "Seguimiento del Plan de Formación"},
            {"label": "Plan de Competencia", "href": "/plan_remediacion_competencias_menu", "icon": "bi-person-badge", "btn": "btn-primary", "module": "Plan de Competencias"},

        ],
    },
    {
        "title": "Cadena de Suministro (TPRM)",
        "icon": "bi-truck",
        "items": [
            {
                "label": "Selección de Proponentes",
                "href": "#",
                "icon": "bi-people",
                "btn": "btn-info text-white",
                "children": [
                    {
                        "label": "Ingreso información",
                        "href": "#",
                        "icon": "bi-folder2-open",
                        "btn": "btn-info text-white",
                        "children": [
                            {"label": "Vía web", "href": "/cuestionario_proveedores_web", "icon": "bi-globe", "btn": "btn-info text-white", "module": "Cuestionario de proveedores web"},
                            {"label": "Vía archivo", "href": "/ingreso_informacion_proponente_archivo", "icon": "bi-file-earmark-spreadsheet", "btn": "btn-info text-white", "module": "Cuestionarios de Proponentes"},
                        ],
                    },
                    {"label": "Evaluación de proponentes", "href": "/cuestionarios_proveedores", "icon": "bi-bar-chart-line", "btn": "btn-info text-white", "module": "Cuestionarios de Proponentes"},
                ],
            },
            {"label": "Revisión en Listas Restrictivas", "href": "/listas_restrictivas", "icon": "bi-shield-exclamation", "btn": "btn-danger", "module": "Listas Restrictivas"},
            {"label": "Security Scorecard de Terceros", "href": "/proponentes/scorecard", "icon": "bi-shield-check", "btn": "btn-warning text-dark", "module": "Security Scorecard de Terceros"},
            {"label": "Registro de Proveedores", "href": "/proveedores_menu", "icon": "bi-building", "btn": "btn-primary", "module": "Registro de Proveedores"},
        ],
    },
    {
        "title": "Continuidad del Negocio",
        "icon": "bi-shield-check",
        "items": [
            {"label": "Continuidad del Negocio (BCP/DRP)", "href": "/bcp/dashboard", "icon": "bi-shield-check", "btn": "btn-primary", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "BIA", "href": "/bcp/bia", "icon": "bi-clipboard-data", "btn": "btn-info text-white", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "Procesos Críticos", "href": "/bcp/procesos", "icon": "bi-diagram-3", "btn": "btn-warning", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "Planes de Continuidad", "href": "/bcp/planes", "icon": "bi-journal-text", "btn": "btn-success", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "DRP", "href": "/bcp/drp", "icon": "bi-hdd-network", "btn": "btn-dark", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "Gestión de Crisis", "href": "/bcp/crisis", "icon": "bi-exclamation-triangle", "btn": "btn-danger", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "Simulacros y Pruebas", "href": "/bcp/pruebas", "icon": "bi-play-circle", "btn": "btn-secondary", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "Dependencias Críticas", "href": "/bcp/dependencias", "icon": "bi-link-45deg", "btn": "btn-primary", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "Madurez BCP", "href": "/bcp/madurez", "icon": "bi-graph-up-arrow", "btn": "btn-info", "module": "Continuidad del Negocio (BCP/DRP)"},
            {"label": "Informe Ejecutivo AI", "href": "/bcp/ia/matriz", "icon": "bi-robot", "btn": "btn-info text-white", "module": "Continuidad del Negocio (BCP/DRP)"},
        ]
    },
    {
        "title": "Medición y Mejora",
        "icon": "bi-graph-up-arrow",
        "items": [
            {"label": "Nivel de Madurez ISO-27001:2022", "href": "/madurez", "icon": "bi-speedometer2", "btn": "btn-primary", "module": "Nivel de madurez ISO 27001:2022"},
            {"label": "Nivel de Madurez NIST CSF V.2.0", "href": "/madurez_nist", "icon": "bi-compass", "btn": "btn-primary", "module": "Nivel de Madurez NIST CSF V.2.0"},
            {"label": "Nivel de Madurez Protección de Datos Personales", "href": "/madurez_datos", "icon": "bi-shield-lock", "btn": "btn-primary", "module": "Nivel de Madurez protección de datos personales"},
            {"label": "Nivel de Madurez PCI-DSS", "href": "/madurez_pci", "icon": "bi-credit-card-2-front", "btn": "btn-primary", "module": "Nivel de Madurez PCI-DSS"},
            {"label": "Nivel de Madurez SOC 2", "href": "/madurez_soc2/", "icon": "bi-shield-check", "btn": "btn-primary", "module": "Nivel de madurez SOC 2"},
            {"label": "Nivel de Madurez ISO 22301", "href": "/madurez_iso22301/", "icon": "bi-life-preserver", "btn": "btn-primary", "module": "Nivel de Madurez ISO 22301"},
            {"label": "Nivel de Madurez Gestión de Inteligencia Artificial", "href": "/madurez-ai", "icon": "bi-robot", "btn": "btn-primary", "module": "Nivel de Madurez Gestión de Inteligencia Artificial"},
            {
                "label": "Métricas",
                "href": "#",
                "icon": "bi-graph-up",
                "btn": "btn-info text-white",
                "module": "Métricas",
                "children": [
                    {
                        "label": "Métricas de Riesgos",
                        "href": "/metricas/riesgos",
                        "icon": "bi-exclamation-triangle",
                        "btn": "btn-info text-white",
                        "module": "Métricas"
                    },
                    {
                        "label": "Métricas de Incidentes",
                        "href": "/metricas/incidentes/matriz",
                        "icon": "bi-bell",
                        "btn": "btn-info text-white",
                        "module": "Métricas"
                    },
                    {
                        "label": "Métricas de Vulnerabilidades",
                        "href": "/metricas/vulnerabilidades",
                        "icon": "bi-shield-exclamation",
                        "btn": "btn-info text-white",
                        "module": "Métricas"
                    },
                    {
                        "label": "Métrica Cultura de Seguridad",
                        "href": "/metricas/cultura/matriz",
                        "icon": "bi-mortarboard",
                        "btn": "btn-info text-white",
                        "module": "Métricas"
                    },
                    {"label": "Métricas BCP", "href": "/bcp/metricas", "icon": "bi-bar-chart", "btn": "btn-success", "module": "Continuidad del Negocio (BCP/DRP)"},
                    {
                        "label": "Configuración de Parámetros",
                        "href": "#",
                        "icon": "bi-gear",
                        "btn": "btn-info text-white",
                        "module": "Métricas",
                        "children": [
                            {
                                "label": "Parámetros de Incidentes",
                                "href": "/metricas/configuracion/incidentes",
                                "icon": "bi-bell",
                                "btn": "btn-info text-white",
                                "module": "Métricas"
                            },
                            {
                                "label": "Parámetros de Vulnerabilidades",
                                "href": "/metricas/configuracion/vulnerabilidades",
                                "icon": "bi-shield-exclamation",
                                "btn": "btn-info text-white",
                                "module": "Métricas"
                            },
                            {
                                "label": "Parámetros de Cultura",
                                "href": "/metricas/configuracion/cultura",
                                "icon": "bi-mortarboard",
                                "btn": "btn-info text-white",
                                "module": "Métricas"
                            },
                            {
                                "label": "Parámetros de Riesgos",
                                "href": "/metricas/configuracion/riesgos",
                                "icon": "bi-exclamation-triangle",
                                "btn": "btn-info text-white",
                                "module": "Métricas"
                            }
                        ]
                    }
                ]
            },
        ],
    },
    {
    "title": "Cumplimiento Continuo",
            "icon": "bi-shield-lock",
            "items": [
                {
                    "label": "Dashboard",
                    "href": "/cumplimiento_continuo",
                    "icon": "bi-speedometer2",
                    "btn": "btn-primary",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "Herramienta XDR (Wazuh)",
                    "href": "/cumplimiento_continuo/wazuh",
                    "icon": "bi-plug",
                    "btn": "btn-primary",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "Sincronización",
                    "href": "/cumplimiento_continuo/sincronizacion",
                    "icon": "bi-arrow-repeat",
                    "btn": "btn-warning",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "ISO 27001",
                    "href": "/cumplimiento_continuo/estandar/ISO27001",
                    "icon": "bi-shield-check",
                    "btn": "btn-primary",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "SOC 2",
                    "href": "/cumplimiento_continuo/estandar/SOC2",
                    "icon": "bi-patch-check",
                    "btn": "btn-primary",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "PCI-DSS",
                    "href": "/cumplimiento_continuo/estandar/PCIDSS",
                    "icon": "bi-credit-card-2-front",
                    "btn": "btn-primary",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "NIST CSF 2.0",
                    "href": "/cumplimiento_continuo/estandar/NISTCSF",
                    "icon": "bi-diagram-3",
                    "btn": "btn-primary",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "Evidencias",
                    "href": "/cumplimiento_continuo/evidencias",
                    "icon": "bi-folder-check",
                    "btn": "btn-success",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "Gobierno de Firewall",
                    "href": "/cumplimiento_continuo/firewall",
                    "icon": "bi-bricks",
                    "btn": "btn-danger",
                    "module": "Cumplimiento Continuo"
                },
                {
                    "label": "Gobierno del Directorio Activo",
                    "href": "/cumplimiento_continuo/active_directory/",
                    "icon": "bi-person-lock",
                    "btn": "btn-primary",
                    "module": "Cumplimiento Continuo"
                },
            ],
    },

    {
        "title": "Planes de Acción",
        "icon": "bi-clipboard2-check",
        "items": [
            {
                "label": "Matriz de Planes de Acción",
                "href": "/planes_accion",
                "icon": "bi-list-check",
                "btn": "btn-primary",
                "module": "Planes de acción del SGSI"
            },
        ],
    },
    {
        "title": "Reportes",
        "icon": "bi-mortarboard",
        "items": [
             {"label": "Reportes", "href": "/reportes", "icon": "bi-printer-fill", "btn": "btn-outline-danger", "module": "Reportes"},
         ],
     },
    {
        "title": "Aplicación móvil",
        "icon": "bi-phone",
        "items": [
            {"label": "Descargar aplicación móvil", "desc": "Consulta y descarga GRAC Mobile para Android o iOS.", "href": "/aplicacion_movil", "icon": "bi-phone", "btn": "btn-primary", "module": "Aplicación móvil"},
        ],
    },
    {
        "title": "Administración",
        "icon": "bi-gear",
        "items": [
            {
                "label": "Configuración Parámetros de la Empresa",
                "href": "#",
                "icon": "bi-building-gear",
                "btn": "btn-primary",
                "module": "Configuración Parámetros de la Empresa",
                "children": [
                    {
                        "label": "Estructura Organizacional",
                        "href": "#",
                        "icon": "bi-diagram-3",
                        "btn": "btn-outline-primary",
                        "module": "Configuración Parámetros de la Empresa",
                        "children": [
                            {
                                "label": "Áreas",
                                "href": "/areas_area",
                                "icon": "bi-diagram-3",
                                "btn": "btn-outline-primary",
                                "module": "Configuración Parámetros de la Empresa"
                            },
                            {
                                "label": "Divisiones",
                                "href": "/areas_division",
                                "icon": "bi-diagram-2",
                                "btn": "btn-outline-primary",
                                "module": "Configuración Parámetros de la Empresa"
                            }
                        ]
                    },
                    {
                        "label": "Parámetros Generales",
                        "href": "#",
                        "icon": "bi-gear-wide-connected",
                        "btn": "btn-outline-primary",
                        "module": "Configuración Parámetros de la Empresa",
                        "children": [
                            {
                                "label": "Configuración del Correo",
                                "href": "/config/email",
                                "icon": "bi-envelope-at",
                                "btn": "btn-outline-primary",
                                "module": "Configuración Parámetros de la Empresa"
                            },
                        ]
                    }
                ]
            },
            {"label": "Portal de Proveedores — Conexión", "desc": "Generar código de vinculación de servidores para proveedores.", "href": "/admin/portal_proveedores_conexion", "icon": "bi-shield-lock", "btn": "btn-primary", "module": "Cuestionario de proveedores web", "admin_only": True},
            {"label": "Configuración AI", "desc": "Configurar llave cifrada para IA (solo admin).", "href": "/admin/openrouter_key", "icon": "bi-key-fill", "btn": "btn-warning text-dark", "admin_only": True},
            {"label": "Gestión de Usuarios", "href": "/usuarios", "icon": "bi-people", "btn": "btn-success", "module": "Gestión de Usuarios"},
            {"label": "Aplicación móvil", "desc": "Descarga GRAC Mobile para Android o accede a TestFlight en iOS.", "href": "/admin/mobile-app", "icon": "bi-phone", "btn": "btn-primary", "module": "Aplicación móvil"},
            {"label": "Administración de Alertas", "desc": "Configurar destinatarios, reglas, severidad y frecuencia.", "href": "/admin/alertas", "icon": "bi-bell-fill", "btn": "btn-warning text-dark", "admin_only": True},
            {"label": "Constructor del Centro de Control", "href": "/admin/dashboard_config", "icon": "bi-sliders", "btn": "btn-primary"},
            {"label": "Logs de Auditoría", "href": "/admin/logs_auditoria", "icon": "bi-journal-text", "btn": "btn-dark", "admin_only": True},
            {"label": "Chat con Asistente", "href": "/chatgpt_view", "icon": "bi-chat-dots", "btn": "btn-info text-white", "module": "Chat con Asistente"},
        ],
    },
]

def filtrar_items_menu(items, usuario_actual, seccion_admin=False):
    filtrados = []

    for it in items:
        item_copy = dict(it)
        # En Administración los perfiles Usuario y Auditor solo ven el chat.
        # Este filtro es exclusivo de la sección: no toca otros módulos SGSI.
        if (seccion_admin and usuario_actual.role in ("user", "auditor")
                and item_copy.get("href") != "/chatgpt_view"):
            continue
        children = item_copy.get("children", [])
        module_name = item_copy.get("module")

        permitido = True

        # Admin ve todo
        if usuario_actual.role == "admin":
            permitido = True

        # Solo admin
        elif item_copy.get("admin_only"):
            permitido = False

        # Declaración de Aplicabilidad (SoA)
        elif item_copy.get("href") == "/soa":
            permitido = (
                usuario_actual.role in ("admin", "auditor")
                or verificar_permiso(usuario_actual, "Contexto Interno")
            )

        # Resultados unificados: acceso tanto para quien gestiona la web
        # como para quien evalúa cuestionarios importados por archivo.
        elif item_copy.get("href") == "/cuestionarios_proveedores":
            permitido = (verificar_permiso(usuario_actual, "Cuestionarios de Proponentes")
                         or verificar_permiso(usuario_actual, "Cuestionario de proveedores web"))

        # Módulos normales por nombre
        elif module_name and module_name in MODULES:
            permitido = verificar_permiso(usuario_actual, module_name)

        # Si tiene hijos, se filtran recursivamente
        if children:
            children_filtrados = filtrar_items_menu(children, usuario_actual, seccion_admin=seccion_admin)

            if children_filtrados and permitido:
                item_copy["children"] = children_filtrados
                filtrados.append(item_copy)

            elif children_filtrados and not module_name:
                item_copy["children"] = children_filtrados
                filtrados.append(item_copy)

            else:
                continue
        else:
            if permitido:
                filtrados.append(item_copy)

    return filtrados


# ============================================================
# SEGURIDAD: SOLO CHAT PARA USUARIO Y AUDITOR EN ADMINISTRACIÓN
# ============================================================
@app.before_request
def _sgsi_restringir_administracion_a_chat():
    """Evita acceso por URL o POST a funciones administrativas ocultas del menú."""
    uid = session.get("user_id")
    if not uid:
        return None  # La autenticación conserva su validación original.

    path = (request.path or "/").rstrip("/") or "/"
    # Solo destinos administrativos del menú (sin interferir con otros módulos).
    administrativo = (
        path == "/admin" or path.startswith("/admin/")
        or path == "/usuarios" or path.startswith("/usuarios/")
        or path.startswith("/editar_permisos/")
        or path in {"/areas_area", "/areas_division", "/areas/delete", "/config/email"}
        or (path.startswith("/areas/") and
            (path.endswith("/info") or path.endswith("/divisiones_json")))
    )
    if not administrativo:
        return None

    usuario = db.session.get(User, uid)
    if usuario is None or usuario.role in ("user", "auditor"):
        # Un POST o una consulta directa tampoco puede sortear la restricción.
        abort(403, description="Acceso restringido a Administración. Solo Chat con Asistente.")
    return None


# ============================================================
# MENÚ GLOBAL SGSI SIEMPRE VISIBLE EN TODOS LOS MÓDULOS
# FIX: marca en azul SOLO la opción exacta / más específica
# ============================================================

def _sgsi_build_global_menu_html():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return ""

        usuario_actual = User.query.get(user_id)
        if not usuario_actual:
            return ""

        current_path = (request.path or "/").split("?")[0].rstrip("/")
        if not current_path:
            current_path = "/"

        current_endpoint = (request.endpoint or "").strip()

        # ============================================================
        # Normalizadores
        # ============================================================
        def _norm_path(path):
            path = str(path or "").split("?")[0].strip()
            if not path or path in ("#", "javascript:void(0);"):
                return path
            if not path.startswith("/"):
                path = "/" + path
            path = path.rstrip("/")
            return path or "/"

        def _path_matches(path):
            path = _norm_path(path)
            if not path or path in ("#", "javascript:void(0);"):
                return False

            # Dashboard Cumplimiento Continuo: SOLO exacto
            if path == "/cumplimiento_continuo":
                return current_path == "/cumplimiento_continuo"

            # Dashboard BCP: SOLO exacto
            if path == "/bcp/dashboard":
                return current_path == "/bcp/dashboard"

            # ISO maturity: no debe activar NIST, Datos, PCI, SOC2 ni AI
            if path == "/madurez":
                return current_path == "/madurez" or current_path.startswith("/madurez/")

            return current_path == path or current_path.startswith(path + "/")

        def _endpoint_matches(endpoint_prefix):
            endpoint_prefix = (endpoint_prefix or "").strip()
            if not endpoint_prefix:
                return False

            if current_endpoint == endpoint_prefix:
                return True

            if current_endpoint.startswith(endpoint_prefix + "_"):
                resto = current_endpoint[len(endpoint_prefix) + 1:]

                # Evita falsas coincidencias entre módulos de madurez
                if endpoint_prefix == "madurez" and resto.startswith((
                    "nist",
                    "datos",
                    "pci",
                    "soc2",
                    "iso22301",
                    "ai"
                )):
                    return False

                # Evita que Plan de Remediación se active con Plan de Competencias
                if endpoint_prefix == "plan_remediacion" and resto.startswith("competencias"):
                    return False

                # Evita que BCP dashboard se active con submódulos BCP
                if endpoint_prefix == "bcp" and resto.startswith((
                    "bia",
                    "procesos",
                    "planes",
                    "drp",
                    "crisis",
                    "pruebas",
                    "dependencias",
                    "madurez",
                    "ia",
                    "metricas"
                )):
                    return False

                # Evita que Dashboard de Cumplimiento Continuo se active con submódulos
                if endpoint_prefix == "cumplimiento_continuo" and resto.startswith((
                    "wazuh",
                    "sincronizacion",
                    "firewall",
                    "active_directory",
                    "estandar",
                    "evidencias",
                    "planes"
                )):
                    return False

                return True

            if current_endpoint.endswith("." + endpoint_prefix):
                return True

            return False

        # ============================================================
        # Reglas por label del menú
        # ============================================================
        MENU_ACTIVE_RULES = {
            "Análisis de Riesgos de Procesos con IA": {"paths": ["/procesos_ia"], "endpoints": ["pra_index", "pra_new", "pra_process", "pra_risk", "pra_edit"]},
            # Gobierno / Dirección
            "Declaración de Aplicabilidad (SoA)": {
                "paths": ["/soa"],
                "endpoints": ["soa"]
            },
            "Gestión de Riesgos": {
                "paths": ["/riesgos_menu", "/riesgos", "/riesgo"],
                "endpoints": [
                    "riesgos_menu",
                    "riesgos",
                    "riesgo",
                    "riesgo_matriz",
                    "riesgo_nuevo",
                    "riesgo_editar"
                ]
            },
            "Objetivos del Sistema de Gestión": {
                "paths": ["/objetivos_menu", "/objetivos", "/objetivo"],
                "endpoints": ["objetivos_menu", "objetivos", "objetivo"]
            },
            "Partes Interesadas": {
                "paths": [
                    "/partes_menu",
                    "/partes",
                    "/parte",
                    "/partes_interesadas",
                    "/parte_interesada"
                ],
                "endpoints": [
                    "partes_menu",
                    "partes",
                    "parte",
                    "partes_interesadas",
                    "parte_interesada"
                ]
            },
            "Contexto Interno": {
                "paths": ["/contexto_interno_menu", "/contexto_interno"],
                "endpoints": ["contexto_interno_menu", "contexto_interno"]
            },
            "Contexto Externo": {
                "paths": ["/contexto_externo_menu", "/contexto_externo"],
                "endpoints": ["contexto_externo_menu", "contexto_externo"]
            },
            "DOFA": {
                "paths": ["/dofa_menu", "/dofa"],
                "endpoints": ["dofa_menu", "dofa"]
            },
            "PESI": {
                "paths": ["/pesi"],
                "endpoints": ["pesi"]
            },
            "Informe Revisión por la Dirección": {
                "paths": ["/revision_direccion"],
                "endpoints": ["revision_direccion"]
            },

            # Documentación
            "Listado Maestro de Documentos": {
                "paths": ["/docs_menu", "/docs", "/documentos"],
                "endpoints": ["docs_menu", "docs", "documentos"]
            },
            "Registro de Comunicaciones": {
                "paths": ["/comunicaciones_menu", "/comunicaciones"],
                "endpoints": ["comunicaciones_menu", "comunicaciones"]
            },
            "Requisitos Legales": {
                "paths": [
                    "/requisitos_menu",
                    "/requisitos",
                    "/requisito_legal",
                    "/req_legal"
                ],
                "endpoints": [
                    "requisitos_menu",
                    "requisitos",
                    "requisito_legal",
                    "req_legal"
                ]
            },

            # Operación y Control
            "Gestión de Activos de Información": {
                "paths": [
                    "/inventario_software_menu",
                    "/inventario_software",
                    "/inventario_ia_menu",
                    "/inventario_ia",
                    "/inventario_informacion_menu",
                    "/inventario_informacion",
                    "/inventario_datos_personales_menu",
                    "/inventario_datos_personales",
                    "/inventario_fisico_menu",
                    "/inventario_fisico",
                    "/valor_confidencialidad",
                    "/valor_integridad",
                    "/valor_disponibilidad",
                    "/valor_criticidad_activo",
                    "/duenos_info"
                ],
                "endpoints": [
                    "inventario_software",
                    "inventario_ia",
                    "inventario_informacion",
                    "inventario_datos_personales",
                    "inventario_fisico",
                    "valor_confidencialidad",
                    "valor_integridad",
                    "valor_disponibilidad",
                    "valor_criticidad_activo",
                    "duenos_info"
                ]
            },
            "Matrices de Activos": {
                "paths": [
                    "/inventario_software_menu",
                    "/inventario_software",
                    "/inventario_ia_menu",
                    "/inventario_ia",
                    "/inventario_informacion_menu",
                    "/inventario_informacion",
                    "/inventario_datos_personales_menu",
                    "/inventario_datos_personales",
                    "/inventario_fisico_menu",
                    "/inventario_fisico"
                ],
                "endpoints": [
                    "inventario_software",
                    "inventario_ia",
                    "inventario_informacion",
                    "inventario_datos_personales",
                    "inventario_fisico"
                ]
            },
            "Inventario de Software": {
                "paths": ["/inventario_software_menu", "/inventario_software"],
                "endpoints": ["inventario_software"]
            },
            "Inventario de IA (ISO 42001)": {
                "paths": ["/inventario_ia_menu", "/inventario_ia"],
                "endpoints": ["inventario_ia"]
            },
            "Inventario de Información": {
                "paths": ["/inventario_informacion_menu", "/inventario_informacion"],
                "endpoints": ["inventario_informacion"]
            },
            "Inventario de Datos Personales": {
                "paths": ["/inventario_datos_personales_menu", "/inventario_datos_personales"],
                "endpoints": ["inventario_datos_personales"]
            },
            "Inventario Físico": {
                "paths": ["/inventario_fisico_menu", "/inventario_fisico"],
                "endpoints": ["inventario_fisico"]
            },
            "Tablas de Valoración": {
                "paths": [
                    "/valor_confidencialidad",
                    "/valor_integridad",
                    "/valor_disponibilidad",
                    "/valor_criticidad_activo"
                ],
                "endpoints": [
                    "valor_confidencialidad",
                    "valor_integridad",
                    "valor_disponibilidad",
                    "valor_criticidad_activo"
                ]
            },
            "Confidencialidad": {
                "paths": ["/valor_confidencialidad"],
                "endpoints": ["valor_confidencialidad"]
            },
            "Integridad": {
                "paths": ["/valor_integridad"],
                "endpoints": ["valor_integridad"]
            },
            "Disponibilidad": {
                "paths": ["/valor_disponibilidad"],
                "endpoints": ["valor_disponibilidad"]
            },
            "Criticidad del Activo": {
                "paths": ["/valor_criticidad_activo"],
                "endpoints": ["valor_criticidad_activo"]
            },
            "Dueños de Información": {
                "paths": ["/duenos_info"],
                "endpoints": ["duenos_info"]
            },
            "Gestión de Accesos": {
                "paths": ["/accesos_menu", "/accesos"],
                "endpoints": ["accesos"]
            },
            "Revisión de Accesos": {
                "paths": ["/revision_accesos_menu", "/revision_accesos"],
                "endpoints": ["revision_accesos"]
            },
            "Gestión de Cambios (RFC)": {
                "paths": ["/rfc_menu", "/rfc"],
                "endpoints": ["rfc"]
            },

            # Gestión de Eventos
            "Registro de Incidentes": {
                "paths": ["/incidentes"],
                "endpoints": ["incidentes", "incidente"]
            },
            "Planes de Respuesta a Incidentes": {
                "paths": ["/planes_respuesta_incidentes"],
                "endpoints": ["ir_catalog", "ir_plan_form", "ir_plan_detail", "ir_step_form", "ir_runs", "ir_run_new", "ir_run_detail", "ir_tracking"]
            },
            "Registro de Vulnerabilidades": {
                "paths": ["/vulnerabilidades_menu", "/vulnerabilidades"],
                "endpoints": ["vulnerabilidades", "vulnerabilidad", "vuln"]
            },
            "Pruebas SAST": {
                "paths": [
                    "/pruebas_sast",
                    "/pruebas_sast/informes",
                    "/pruebas_sast/config",
                    "/pruebas_sast/models",
                    "/pruebas_sast/start",
                    "/pruebas_sast/track",
                    "/pruebas_sast/progress",
                    "/pruebas_sast/result",
                    "/pruebas_sast/download"
                ],
                "endpoints": [
                    "sast_index",
                    "sast_reports",
                    "sast_report_detail",
                    "sast_config",
                    "sast_models",
                    "sast_start",
                    "sast_track",
                    "sast_progress",
                    "sast_result",
                    "sast_download_pdf",
                    "sast_download_json"
                ]
            },
            "Modelamiento de Amenazas": {
                "paths": ["/modelamiento_amenazas", "/vulnerabilidades/threat_model"],
                "endpoints": ["threat_model"]
            },
            "Superficie de Ataque y Escenarios": {
                "paths": ["/superficie_ataque"],
                "endpoints": ["attack_auto"]
            },
            "Plan de Remediación": {
                "paths": ["/plan_remediacion_menu", "/plan_remediacion"],
                "endpoints": [
                    "plan_remediacion_menu",
                    "plan_remediacion_matriz",
                    "plan_remediacion_nuevo",
                    "plan_remediacion_edit",
                    "plan_remediacion_detalle",
                    "plan_remediacion_delete",
                    "plan_remediacion_ai_sugerir"
                ]
            },

            # Competencias y Cultura
            "Campañas de Concientización": {
                "paths": [
                    "/campanias_concientizacion_menu",
                    "/campanias_concientizacion",
                    "/campanias_concientizacion_matriz"
                ],
                "endpoints": [
                    "campanias_concientizacion_menu",
                    "campanias_concientizacion",
                    "campanias_concientizacion_matriz"
                ]
            },
            "Plan de Concientización y Formación": {
                "paths": ["/plan_diseno_menu", "/plan_diseno"],
                "endpoints": ["plan_diseno"]
            },
            "Seguimiento Plan de Concientización y Formación": {
                "paths": ["/plan_cf/menu", "/plan_cf"],
                "endpoints": ["plan_cf"]
            },
            "Plan de Competencia": {
                "paths": [
                    "/plan_remediacion_competencias_menu",
                    "/plan_remediacion_competencias"
                ],
                "endpoints": ["plan_remediacion_competencias"]
            },

            # Cadena de Suministro
            "Vía web": {
                "paths": ["/cuestionario_proveedores_web"],
                "endpoints": ["cpw_admin", "cpw_evaluation", "cpw_detail"]
            },
            "Vía archivo": {
                "paths": ["/ingreso_informacion_proponente_archivo"],
                "endpoints": ["ingreso_informacion_proponente_archivo"]
            },
            "Evaluación de proponentes": {
                "paths": ["/cuestionarios_proveedores"],
                "endpoints": ["cuestionarios_proveedores"]
            },
            "Revisión en Listas Restrictivas": {
                "paths": ["/listas_restrictivas"],
                "endpoints": ["listas_restrictivas"]
            },
            "Security Scorecard de Terceros": {
                "paths": ["/proponentes/scorecard"],
                "endpoints": ["scorecard_proponentes", "proponentes"]
            },
            "Registro de Proveedores": {
                "paths": ["/proveedores_menu", "/proveedores"],
                "endpoints": ["proveedores"]
            },

            # Continuidad del Negocio
            "Continuidad del Negocio (BCP/DRP)": {
                "paths": ["/bcp/dashboard"],
                "endpoints": ["bcp_dashboard"],
                "exact": True
            },
            "BIA": {
                "paths": ["/bcp/bia"],
                "endpoints": ["bcp_bia"]
            },
            "Procesos Críticos": {
                "paths": ["/bcp/procesos"],
                "endpoints": ["bcp_procesos"]
            },
            "Planes de Continuidad": {
                "paths": ["/bcp/planes"],
                "endpoints": ["bcp_planes"]
            },
            "DRP": {
                "paths": ["/bcp/drp"],
                "endpoints": ["bcp_drp"]
            },
            "Gestión de Crisis": {
                "paths": ["/bcp/crisis"],
                "endpoints": ["bcp_crisis"]
            },
            "Simulacros y Pruebas": {
                "paths": ["/bcp/pruebas"],
                "endpoints": ["bcp_pruebas"]
            },
            "Dependencias Críticas": {
                "paths": ["/bcp/dependencias"],
                "endpoints": ["bcp_dependencias"]
            },
            "Madurez BCP": {
                "paths": ["/bcp/madurez"],
                "endpoints": ["bcp_madurez"]
            },
            "Informe Ejecutivo AI": {
                "paths": ["/bcp/ia"],
                "endpoints": ["bcp_ia"]
            },
            "Métricas BCP": {
                "paths": ["/bcp/metricas"],
                "endpoints": ["bcp_metricas"]
            },

            # Medición y Mejora
            "Nivel de Madurez ISO-27001:2022": {
                "paths": ["/madurez"],
                "endpoints": ["madurez"]
            },
            "Nivel de Madurez NIST CSF V.2.0": {
                "paths": ["/madurez_nist"],
                "endpoints": ["madurez_nist"]
            },
            "Nivel de Madurez Protección de Datos Personales": {
                "paths": ["/madurez_datos"],
                "endpoints": ["madurez_datos"]
            },
            "Nivel de Madurez PCI-DSS": {
                "paths": ["/madurez_pci"],
                "endpoints": ["madurez_pci"]
            },
            "Nivel de Madurez SOC 2": {
                "paths": ["/madurez_soc2"],
                "endpoints": ["madurez_soc2"]
            },
            "Nivel de Madurez ISO 22301": {
                "paths": ["/madurez_iso22301"],
                "endpoints": ["madurez_iso22301"]
            },
            "Nivel de Madurez Gestión de Inteligencia Artificial": {
                "paths": ["/madurez-ai"],
                "endpoints": ["madurez_ai"]
            },
            "Métricas": {
                "paths": ["/metricas"],
                "endpoints": ["metricas"]
            },
            "Métricas de Riesgos": {
                "paths": ["/metricas/riesgos"],
                "endpoints": ["metricas_riesgos"]
            },
            "Métricas de Incidentes": {
                "paths": ["/metricas/incidentes"],
                "endpoints": ["metricas_incidentes"]
            },
            "Métricas de Vulnerabilidades": {
                "paths": ["/metricas/vulnerabilidades"],
                "endpoints": ["metricas_vulnerabilidades"]
            },
            "Métrica Cultura de Seguridad": {
                "paths": ["/metricas/cultura"],
                "endpoints": ["metricas_cultura"]
            },
            "Métricas Planes de Mejora": {
                "paths": ["/metricas/mejora"],
                "endpoints": ["metricas_mejora"]
            },
            "Configuración de Parámetros": {
                "paths": ["/metricas/configuracion"],
                "endpoints": ["metricas_configuracion"]
            },
            "Parámetros de Incidentes": {
                "paths": ["/metricas/configuracion/incidentes"],
                "endpoints": ["metricas_configuracion_incidentes"]
            },
            "Parámetros de Vulnerabilidades": {
                "paths": ["/metricas/configuracion/vulnerabilidades"],
                "endpoints": ["metricas_configuracion_vulnerabilidades"]
            },
            "Parámetros de Cultura": {
                "paths": ["/metricas/configuracion/cultura"],
                "endpoints": ["metricas_configuracion_cultura"]
            },
            "Parámetros de Riesgos": {
                "paths": ["/metricas/configuracion/riesgos"],
                "endpoints": ["metricas_configuracion_riesgos"]
            },
            "Planes de Acción del Sistema de Gestión (Mejora)": {
                "paths": ["/mejora_menu", "/mejora"],
                "endpoints": ["mejora"]
            },
            "Matriz de Planes de Acción": {
                "paths": ["/planes_accion"],
                "endpoints": ["planes_accion_dashboard"],
                "exact": True
            },
            "Registrar Plan de Acción": {
                "paths": ["/planes_accion/nuevo"],
                "endpoints": ["planes_accion_new"]
            },

            # Reportes
            "Reportes": {
                "paths": ["/reportes"],
                "endpoints": ["reportes"]
            },

            # Cumplimiento Continuo
            "Dashboard": {
                "paths": ["/cumplimiento_continuo"],
                "endpoints": ["cumplimiento_continuo"],
                "exact": True
            },
            "Herramienta XDR (Wazuh)": {
                "paths": ["/cumplimiento_continuo/wazuh"],
                "endpoints": ["cumplimiento_continuo_wazuh"]
            },
            "Sincronización": {
                "paths": ["/cumplimiento_continuo/sincronizacion"],
                "endpoints": ["cumplimiento_continuo_sincronizacion"]
            },
            "Gobierno de Firewall": {
                "paths": ["/cumplimiento_continuo/firewall"],
                "endpoints": ["cumplimiento_continuo_firewall", "fwgov"]
            },
            "ISO 27001": {
                "paths": ["/cumplimiento_continuo/estandar/ISO27001"],
                "endpoints": ["cumplimiento_continuo_estandar"]
            },
            "SOC 2": {
                "paths": ["/cumplimiento_continuo/estandar/SOC2"],
                "endpoints": ["cumplimiento_continuo_estandar"]
            },
            "PCI-DSS": {
                "paths": ["/cumplimiento_continuo/estandar/PCIDSS"],
                "endpoints": ["cumplimiento_continuo_estandar"]
            },
            "NIST CSF 2.0": {
                "paths": ["/cumplimiento_continuo/estandar/NISTCSF"],
                "endpoints": ["cumplimiento_continuo_estandar"]
            },
            "Evidencias": {
                "paths": ["/cumplimiento_continuo/evidencias"],
                "endpoints": ["cumplimiento_continuo_evidencias"]
            },
            "Planes de Acción": {
                "paths": ["/cumplimiento_continuo/planes"],
                "endpoints": ["cumplimiento_continuo_planes"]
            },

            # Administración
            "Configuración Parámetros de la Empresa": {
                "paths": ["/areas_", "/config/email"],
                "endpoints": ["areas", "config_email"]
            },
            "Estructura Organizacional": {
                "paths": ["/areas_area", "/areas_division"],
                "endpoints": ["areas_area", "areas_division"]
            },
            "Áreas": {
                "paths": ["/areas_area"],
                "endpoints": ["areas_area"]
            },
            "Divisiones": {
                "paths": ["/areas_division"],
                "endpoints": ["areas_division"]
            },
            "Parámetros Generales": {
                "paths": ["/config/email"],
                "endpoints": ["config_email"]
            },
            "Configuración del Correo": {
                "paths": ["/config/email"],
                "endpoints": ["config_email"]
            },
            "Gestión de Usuarios": {
                "paths": ["/usuarios"],
                "endpoints": ["usuarios"]
            },
            "Descargar aplicación móvil": {
                "paths": ["/aplicacion_movil"],
                "endpoints": ["aplicacion_movil", "mobile_app_user_download"]
            },
            "Aplicación móvil": {
                "paths": ["/admin/mobile-app"],
                "endpoints": ["admin_mobile_app", "admin_mobile_app_download"]
            },
            "Centro de Alertas": {
                "paths": ["/alertas"],
                "endpoints": ["alert_center"],
                "exact": True
            },
            "Administración de Alertas": {
                "paths": ["/admin/alertas"],
                "endpoints": ["admin_alertas"],
                "exact": True
            },
            "Constructor del Centro de Control": {
                "paths": ["/admin/dashboard_config"],
                "endpoints": ["dashboard_config"],
                "exact": True
            },
            "Logs de Auditoría": {
                "paths": ["/admin/logs_auditoria"],
                "endpoints": ["logs_auditoria"]
            },
            "Chat con Asistente": {
                "paths": ["/chatgpt_view"],
                "endpoints": ["chatgpt_view"]
            },
        }

        # ============================================================
        # Determina la opción activa usando la coincidencia más específica
        # Esto evita que Dashboard (/cumplimiento_continuo) quede activo
        # cuando se entra a /cumplimiento_continuo/sincronizacion, etc.
        # ============================================================
        def _item_candidate_score(item):
            href = _norm_path(item.get("href", ""))
            label = item.get("label", "")
            # Matriz IA y sus formularios: mantener la opción activa.
            if current_path.startswith('/inventario_ia') and item.get('module') == 'Inventario de IA':
                return 10000
            # Centro de Reportes: mantener la opción activa incluso con filtros.
            if (current_path == '/reportes' or current_path.startswith('/reportes/')) and href == '/reportes':
                return 10000
            rules = MENU_ACTIVE_RULES.get(label, {})
            exact = bool(rules.get("exact", False))

            best = -1

            candidate_paths = []
            if href not in ("", "#", "javascript:void(0);"):
                candidate_paths.append(href)

            candidate_paths.extend(rules.get("paths", []) or [])

            for p in candidate_paths:
                p = _norm_path(p)
                if p in ("", "#", "javascript:void(0);"):
                    continue

                if exact:
                    if current_path == p:
                        best = max(best, len(p))
                else:
                    if _path_matches(p):
                        best = max(best, len(p))

            # Endpoint como respaldo. No se usa para distinguir estándares,
            # porque todos pueden compartir cumplimiento_continuo_estandar.
            for ep in rules.get("endpoints", []) or []:
                if _endpoint_matches(ep):
                    if label in ("ISO 27001", "SOC 2", "PCI-DSS", "NIST CSF 2.0"):
                        if best >= 0:
                            best = max(best, 500 + best)
                    else:
                        best = max(best, 100)

            return best

        def _flatten_items(items):
            out = []
            for it in items:
                out.append(it)
                for ch in it.get("children") or []:
                    out.extend(_flatten_items([ch]))
            return out

        # Primero filtra por permisos
        sections = []
        all_leaf_items = []

        for sec in MENU_SECTIONS:
            allowed_items = filtrar_items_menu(
                sec.get("items", []), usuario_actual,
                seccion_admin=(sec.get("title") == "Administración")
            )
            if allowed_items:
                sec2 = dict(sec)
                sec2["items"] = allowed_items
                sections.append(sec2)
                all_leaf_items.extend([
                    x for x in _flatten_items(allowed_items)
                    if not x.get("children")
                ])

        # Calcula el mejor candidato global
        best_item_key = None
        best_score = -1

        for item in all_leaf_items:
            score = _item_candidate_score(item)
            if score > best_score:
                best_score = score
                best_item_key = (
                    item.get("label", ""),
                    _norm_path(item.get("href", ""))
                )

        def _item_is_active(item):
            if item.get("children"):
                return False

            key = (
                item.get("label", ""),
                _norm_path(item.get("href", ""))
            )

            return best_score >= 0 and key == best_item_key

        def _mark_items(items):
            marked = []

            for it in items:
                item = dict(it)
                children = item.get("children") or []

                children_marked = _mark_items(children) if children else []
                item["_children"] = children_marked

                active_self = _item_is_active(item)
                active_child = any(ch.get("_active_tree") for ch in children_marked)

                item["_active"] = active_self
                item["_active_tree"] = active_self or active_child

                marked.append(item)

            return marked

        for sec in sections:
            sec["items"] = _mark_items(sec.get("items", []))
            sec["_active_tree"] = any(it.get("_active_tree") for it in sec["items"])

        return render_template_string("""
        <aside id="sgsiGlobalMenu" class="sgsi-global-menu-wrap">

          <div id="sgsiGlobalMenuToggle" class="sgsi-global-menu-arrow">
            <span class="sgsi-arrow-icon">‹</span>
          </div>

          <div class="sgsi-menu-fixed-shell">

            <div class="sgsi-menu-scroll-only" id="sgsiGlobalMenuScroll">

              <div class="sgsi-global-menu-list">

                <a class="sgsi-global-root-toggle sgsi-global-panel-control-btn {% if center_active %}sgsi-center-active{% endif %}" href="/">
                  <i class="bi bi-speedometer2"></i>
                  <span>Centro de Control</span>
                </a>

                {% macro render_items(items, prefix) %}
                  {% for it in items %}
                    {% set iid = prefix ~ "_item_" ~ loop.index %}

                    {% if it.get("_children") %}
                      <li class="sgsi-global-node">
                        <a class="sgsi-global-item sgsi-global-node-toggle {% if it.get('_active_tree') %}sgsi-active-tree{% endif %}"
                           href="javascript:void(0);"
                           data-target="{{ iid }}">
                          <i class="bi {{ it.get('icon','bi-box') }}"></i>
                          <span>{{ it["label"] }}</span>
                        </a>

                        <ul class="sgsi-global-panel sgsi-global-subpanel {% if it.get('_active_tree') %}sgsi-open{% endif %}" id="{{ iid }}">
                          {{ render_items(it["_children"], iid) }}
                        </ul>
                      </li>
                    {% else %}
                      <li>
                        <a class="sgsi-global-item {% if it.get('_active') %}sgsi-active{% endif %}"
                           href="{{ it.get('href', '#') }}">
                          <i class="bi {{ it.get('icon','bi-box') }}"></i>
                          <span>{{ it["label"] }}</span>
                        </a>
                      </li>
                    {% endif %}
                  {% endfor %}
                {% endmacro %}

                {% for sec in sections %}
                  {% set sid = "global_root_" ~ loop.index %}

                  <div class="sgsi-global-root-item">
                    <button class="btn sgsi-global-root-toggle {% if sec.get('_active_tree') %}sgsi-active-tree{% endif %}"
                            type="button"
                            data-target="{{ sid }}">
                      <i class="bi {{ sec.get('icon', 'bi-grid-1x2') }}"></i>
                      <span>{{ sec["title"] }}</span>
                    </button>

                    <ul class="sgsi-global-panel {% if sec.get('_active_tree') %}sgsi-open{% endif %}" id="{{ sid }}">
                      {{ render_items(sec["items"], sid) }}
                    </ul>
                  </div>
                {% endfor %}

              </div>
            </div>

          </div>
        </aside>

        <style>
          :root{
            /* Menú global unificado con Centro de Control */
            --sgsi-menu-w:245px;
            --sgsi-menu-left:0px;
            --sgsi-topbar-h:var(--arky-topbar-h, 58px);
            --sgsi-content-left:245px;
            --sgsi-card:#ffffff;
            --sgsi-purple:#074883;
            --sgsi-purple-2:#1d5fae;
            --sgsi-lav:#dcecff;
            --sgsi-lav-2:#c9e3ff;
            --sgsi-border:#a9cdeb;
            --sgsi-text:#0f3766;
            --sgsi-muted:#425f7f;
          }

          body{
            padding-left:var(--sgsi-content-left) !important;
          }

          #sgsiGlobalMenu,
          .sgsi-global-menu-wrap{
            position:fixed !important;
            top:var(--sgsi-topbar-h) !important;
            left:var(--sgsi-menu-left) !important;
            width:var(--sgsi-menu-w) !important;
            height:calc(100vh - var(--sgsi-topbar-h)) !important;
            z-index:999990 !important;
            pointer-events:none;
            transition:left .22s ease;
          }

          .sgsi-global-menu-arrow{
            position:absolute;
            right:-13px;
            top:16px;
            width:22px;
            height:50px;
            border-radius:999px;
            background:linear-gradient(135deg,var(--sgsi-purple),var(--sgsi-purple-2));
            color:#ffffff;
            display:flex;
            align-items:center;
            justify-content:center;
            cursor:pointer;
            box-shadow:0 10px 22px rgba(43,0,79,.22);
            border:2px solid #ffffff;
            z-index:20;
            pointer-events:auto;
          }

          .sgsi-global-menu-arrow .sgsi-arrow-icon{
            font-size:26px;
            font-weight:950;
            line-height:1;
            position:relative;
            top:-1px;
          }

          .sgsi-menu-fixed-shell{
            height:100%;
            width:100%;
            padding:8px 7px;
            border-radius:0 18px 18px 0;
            background:linear-gradient(180deg,rgba(238,247,255,.97) 0%,rgba(213,234,255,.95) 48%,rgba(198,222,245,.94) 100%);
            border:1px solid var(--sgsi-border);
            border-left:0;
            box-shadow:10px 0 30px rgba(28,91,160,.18), inset -1px 0 rgba(255,255,255,.65);
            backdrop-filter:blur(14px);
            -webkit-backdrop-filter:blur(14px);
            pointer-events:auto;
            transition:opacity .22s ease, transform .22s ease;
          }

          .sgsi-menu-scroll-only{
            height:100%;
            overflow-y:auto;
            overflow-x:hidden;
            padding-right:2px;
          }

          .sgsi-menu-scroll-only::-webkit-scrollbar{ width:7px; }
          .sgsi-menu-scroll-only::-webkit-scrollbar-thumb{ background:#b8a3d8; border-radius:999px; }
          .sgsi-menu-scroll-only::-webkit-scrollbar-track{ background:#eef4ff; border-radius:999px; }

          .sgsi-global-menu-list{
            display:flex;
            flex-direction:column;
            gap:7px;
          }

          .sgsi-global-root-item{
            display:block;
          }

          .sgsi-global-root-toggle,
          .sgsi-global-item,
          .sgsi-global-node-toggle{
            width:100%;
            display:flex !important;
            align-items:center;
            justify-content:flex-start;
            gap:7px;
            border:1px solid transparent !important;
            text-decoration:none !important;
            text-align:left;
            color:#26384f !important;
            background:transparent !important;
            font-weight:850;
            white-space:normal !important;
            line-height:1.15 !important;
            transition:all .18s ease;
          }

          .sgsi-global-root-toggle{
            font-size:.70rem !important;
            min-height:35px !important;
            padding:7px 8px !important;
            border-radius:11px !important;
          }

          .sgsi-global-item,
          .sgsi-global-node-toggle{
            font-size:.66rem !important;
            padding:6px 7px !important;
            border-radius:10px !important;
          }

          .sgsi-global-root-toggle:hover,
          .sgsi-global-node-toggle:hover{
            background:var(--sgsi-lav) !important;
            color:var(--sgsi-purple) !important;
            border-color:var(--sgsi-border) !important;
          }

          .sgsi-global-item:hover{
            background:#ffffff !important;
            color:var(--sgsi-purple) !important;
            box-shadow:0 8px 16px rgba(43,0,79,.08);
          }

          .sgsi-global-panel-control-btn.sgsi-center-active{
            background:linear-gradient(135deg,var(--sgsi-purple) 0%,var(--sgsi-purple-2) 58%,#3f8fd6 100%) !important;
            color:#ffffff !important;
            border:1px solid rgba(255,255,255,.40) !important;
            box-shadow:0 12px 26px rgba(75,11,130,.24) !important;
          }

          .sgsi-global-panel-control-btn.sgsi-center-active i,
          .sgsi-global-panel-control-btn.sgsi-center-active span{
            color:#ffffff !important;
          }

          .sgsi-global-node-toggle::after{
            content:"⌄";
            margin-left:auto;
            font-size:13px;
            font-weight:950;
            transition:transform .18s ease;
          }

          .sgsi-global-node-toggle.sgsi-active-tree::after{
            transform:rotate(180deg);
          }

          /* Capítulo principal activo */
          .sgsi-global-root-toggle.sgsi-active-tree{
            background:linear-gradient(135deg,var(--sgsi-purple),var(--sgsi-purple-2)) !important;
            color:#ffffff !important;
            border-color:rgba(255,255,255,.42) !important;
            box-shadow:0 8px 18px rgba(44,123,229,.28);
          }

          .sgsi-global-root-toggle.sgsi-active-tree i,
          .sgsi-global-root-toggle.sgsi-active-tree span{
            color:#ffffff !important;
          }

          /* Padres internos activos */
          .sgsi-global-node-toggle.sgsi-active-tree{
            background:linear-gradient(135deg,#c9e3ff,#ffffff) !important;
            color:var(--sgsi-purple) !important;
            border-color:var(--sgsi-border) !important;
          }

          .sgsi-global-node-toggle.sgsi-active-tree i,
          .sgsi-global-node-toggle.sgsi-active-tree span{
            color:var(--sgsi-purple) !important;
          }

          /* Opción final exacta activa */
          .sgsi-global-item.sgsi-active{
            background:linear-gradient(135deg,var(--sgsi-purple),var(--sgsi-purple-2)) !important;
            color:#ffffff !important;
            border-color:rgba(255,255,255,.42) !important;
            box-shadow:0 8px 18px rgba(44,123,229,.28);
          }

          .sgsi-global-item.sgsi-active i,
          .sgsi-global-item.sgsi-active span{
            color:#ffffff !important;
          }

          .sgsi-global-item i,
          .sgsi-global-root-toggle i,
          .sgsi-global-node-toggle i{
            color:inherit !important;
            width:16px;
            text-align:center;
            flex:0 0 auto;
          }

          .sgsi-global-panel{
            display:none;
            list-style:none;
            margin:4px 0 4px 0 !important;
            padding:4px 0 4px 6px !important;
            background:var(--sgsi-lav) !important;
            border:1px solid var(--sgsi-border) !important;
            border-radius:12px !important;
            overflow:visible !important;
          }

          .sgsi-global-subpanel{
            margin-left:5px !important;
            padding-left:8px !important;
            border-left:2px solid #a88fd3 !important;
          }

          .sgsi-global-panel.sgsi-open{
            display:block !important;
          }

          .sgsi-global-panel li{
            list-style:none;
            margin:0 0 3px 0;
            padding:0;
          }

          .sgsi-global-panel .sgsi-global-item,
          .sgsi-global-panel .sgsi-global-node-toggle{
            margin:3px 4px;
            background:rgba(241,247,255,.74) !important;
            border:1px solid rgba(181,205,230,.78) !important;
          }

          .sgsi-global-panel .sgsi-global-item.sgsi-active{
            background:linear-gradient(135deg,var(--sgsi-purple),var(--sgsi-purple-2)) !important;
            border-color:rgba(255,255,255,.42) !important;
          }

          body.sgsi-menu-collapsed{
            padding-left:0 !important;
          }

          body.sgsi-menu-collapsed #sgsiGlobalMenu{
            left:calc((var(--sgsi-menu-w) - 24px) * -1) !important;
          }

          body.sgsi-menu-collapsed #sgsiGlobalMenu .sgsi-menu-fixed-shell{
            opacity:0;
            pointer-events:none;
          }

          body.sgsi-menu-collapsed #sgsiGlobalMenuToggle .sgsi-arrow-icon{
            transform:rotate(180deg);
          }

          @media (max-width:992px){
            :root{
              --sgsi-content-left:0px;
            }

            body{
              padding-left:0 !important;
            }

            #sgsiGlobalMenu{
              left:calc((var(--sgsi-menu-w) - 24px) * -1) !important;
            }

            body:not(.sgsi-menu-collapsed) #sgsiGlobalMenu{
              left:0 !important;
            }
          }
        </style>

        <script>
          (function(){
            const STORAGE_KEY = "sgsi_global_menu_scroll_top";

            function menuScroll(){
              return document.getElementById("sgsiGlobalMenuScroll");
            }

            function saveScroll(){
              const scroller = menuScroll();
              if(scroller){
                localStorage.setItem(STORAGE_KEY, String(scroller.scrollTop || 0));
              }
            }

            function restoreScroll(){
              const scroller = menuScroll();
              if(!scroller) return;

              const saved = parseInt(localStorage.getItem(STORAGE_KEY) || "0", 10);

              if(!isNaN(saved) && saved > 0){
                scroller.scrollTop = saved;
              }
            }

            function toggleMenu(trigger){
              const id = trigger.getAttribute("data-target");
              const panel = id ? document.getElementById(id) : null;

              if(!panel) return;

              const isOpen = panel.classList.contains("sgsi-open");

              if(isOpen){
                trigger.classList.remove("sgsi-active-tree");
                panel.classList.remove("sgsi-open");
              }else{
                trigger.classList.add("sgsi-active-tree");
                panel.classList.add("sgsi-open");
              }

              setTimeout(saveScroll, 80);
            }

            document.querySelectorAll("#sgsiGlobalMenu .sgsi-global-root-toggle, #sgsiGlobalMenu .sgsi-global-node-toggle").forEach(function(toggle){
              toggle.addEventListener("click", function(e){
                if(toggle.classList.contains("sgsi-global-panel-control-btn")) return;
                e.preventDefault();
                e.stopPropagation();
                toggleMenu(toggle);
              });
            });

            document.querySelectorAll("#sgsiGlobalMenu a[href]").forEach(function(link){
              link.addEventListener("click", saveScroll);
            });

            const scroller = menuScroll();

            if(scroller){
              scroller.addEventListener("scroll", saveScroll);
            }

            const menuToggle = document.getElementById("sgsiGlobalMenuToggle");

            if(menuToggle){
              menuToggle.addEventListener("click", function(e){
                e.preventDefault();
                e.stopPropagation();
                document.body.classList.toggle("sgsi-menu-collapsed");
                saveScroll();
              });
            }

            window.addEventListener("beforeunload", saveScroll);

            window.addEventListener("pageshow", function(){
              setTimeout(restoreScroll, 80);
            });

            setTimeout(restoreScroll, 80);
          })();
        </script>
        """, sections=sections, center_active=(current_path == "/"))

    except Exception as e:
        print("Error construyendo menú global SGSI:", repr(e))
        return ""


@app.after_request
def inject_sgsi_global_vertical_menu(response):
    try:
        content_type = response.headers.get("Content-Type", "")

        if "text/html" not in content_type:
            return response

        user_id = session.get("user_id")
        if not user_id:
            return response

        endpoint = request.endpoint or ""

        rutas_excluidas = {
            "login",
            "logout",
            "static",
            "dashboard_status",
            "menu",
            "verificar_otp",
            "configurar_otp"
        }

        # Las pantallas de autenticación y OTP deben mostrarse
        # completamente aisladas del menú, encabezado y navegación interna de GRAC.
        rutas_sin_menu = (
            "/verificar_otp",
            "/configurar_otp",
            "/otp/"
        )

        if endpoint in rutas_excluidas or request.path.startswith(rutas_sin_menu):
            return response

        html = response.get_data(as_text=True)

        if not html or "sgsiGlobalMenu" in html:
            return response

        menu_html = _sgsi_build_global_menu_html()
        if not menu_html:
            return response

        if "</header>" in html:
            html = html.replace("</header>", "</header>\n" + menu_html, 1)
        elif "<body>" in html:
            html = html.replace("<body>", "<body>\n" + menu_html, 1)
        elif "</body>" in html:
            html = html.replace("</body>", menu_html + "\n</body>", 1)
        else:
            html = menu_html + html

        response.set_data(html)
        response.headers["Content-Length"] = str(len(response.get_data()))

    except Exception as e:
        print("No se pudo inyectar menú global SGSI:", repr(e))

    return response




# ============================================================
# ADMINISTRACIÓN: DISEÑO SENCILLO DEL CENTRO DE CONTROL
# ============================================================
@app.route('/admin/dashboard_config', methods=['GET', 'POST'])
@login_required
def dashboard_config():
    usuario_actual = User.query.get(session.get('user_id'))
    if not usuario_actual:
        flash("No fue posible identificar el usuario autenticado.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        action = (request.form.get('action') or 'save').strip().lower()
        try:
            if action in {'create_custom', 'update_custom'}:
                data, error = _dashboard_custom_widget_form_data(request.form)
                if error:
                    flash(error, "danger")
                    return redirect(url_for('dashboard_config'))

                if action == 'create_custom':
                    existing = DashboardCustomWidget.query.filter_by(
                        user_id=usuario_actual.id,
                        source_key=data['source_key'],
                        widget_type=data['widget_type'],
                    ).first()
                    if existing:
                        _dashboard_add_key_to_selection(usuario_actual.id, _dashboard_custom_key(existing.id))
                        flash("Esa fuente ya estaba creada con la misma presentación. Se dejó visible en el Centro de Control.", "info")
                    else:
                        widget = DashboardCustomWidget(user_id=usuario_actual.id, **data)
                        db.session.add(widget)
                        db.session.commit()
                        _dashboard_add_key_to_selection(usuario_actual.id, _dashboard_custom_key(widget.id))
                        flash("Visualización creada y agregada al Centro de Control.", "success")
                else:
                    widget_id = int(request.form.get('custom_id') or 0)
                    widget = DashboardCustomWidget.query.filter_by(id=widget_id, user_id=usuario_actual.id).first()
                    if not widget:
                        flash("La visualización no existe o no pertenece al usuario.", "danger")
                        return redirect(url_for('dashboard_config'))
                    duplicate = DashboardCustomWidget.query.filter(
                        DashboardCustomWidget.user_id == usuario_actual.id,
                        DashboardCustomWidget.source_key == data['source_key'],
                        DashboardCustomWidget.widget_type == data['widget_type'],
                        DashboardCustomWidget.id != widget.id,
                    ).first()
                    if duplicate:
                        flash("Ya existe otra visualización con esa fuente y presentación.", "warning")
                        return redirect(url_for('dashboard_config', edit_widget=widget.id))
                    for field, value in data.items():
                        setattr(widget, field, value)
                    widget.updated_at = datetime.utcnow()
                    db.session.commit()
                    flash("Visualización actualizada correctamente.", "success")

            elif action == 'delete_custom':
                widget_id = int(request.form.get('custom_id') or 0)
                widget = DashboardCustomWidget.query.filter_by(id=widget_id, user_id=usuario_actual.id).first()
                if not widget:
                    flash("La visualización no existe o no pertenece al usuario.", "danger")
                    return redirect(url_for('dashboard_config'))
                key = _dashboard_custom_key(widget.id)
                _dashboard_remove_key_from_selection(usuario_actual.id, key)
                db.session.delete(widget)
                db.session.commit()
                flash("Visualización eliminada.", "success")

            elif action == 'reset':
                _dashboard_reset_selected_keys(usuario_actual.id)
                flash("El Centro de Control volvió a su diseño inicial.", "success")

            else:
                available = _dashboard_available_widget_map(usuario_actual.id)
                default_position = {}
                kind_order = {"kpi": 0, "chart": 1}
                kind_counters = {"kpi": 0, "chart": 0}
                for key, item in available.items():
                    kind = item.get("kind", "chart")
                    kind_counters[kind] = kind_counters.get(kind, 0) + 1
                    default_position[key] = kind_counters[kind]

                seen = set()
                sortable = []
                for key in request.form.getlist('widgets'):
                    key = str(key or '').strip()
                    if key not in available or key in seen:
                        continue
                    seen.add(key)
                    meta = available[key]
                    kind = meta.get("kind", "chart")
                    try:
                        order_value = int(request.form.get(f'order_{key}', default_position.get(key, 1)))
                    except Exception:
                        order_value = default_position.get(key, 1)
                    sortable.append((kind_order.get(kind, 99), max(1, min(order_value, 999)), default_position.get(key, 999), key))

                sortable.sort(key=lambda row: (row[0], row[1], row[2]))
                _dashboard_save_selected_keys(usuario_actual.id, [row[3] for row in sortable])
                flash("Elementos visibles y orden guardados correctamente.", "success")

            try:
                registrar_log(usuario_actual.username, "Actualizó el diseño de su Centro de Control personal.")
            except Exception:
                pass
            return redirect(url_for('dashboard_config'))

        except Exception as exc:
            db.session.rollback()
            flash(f"No se pudo aplicar la configuración: {exc}", "danger")

    selected_keys = _dashboard_get_selected_keys(usuario_actual.id)
    selected_set = set(selected_keys)
    available = _dashboard_available_widget_map(usuario_actual.id)

    position_map = {}
    selected_kind_counters = {"kpi": 0, "chart": 0}
    for key in selected_keys:
        meta = available.get(key)
        if not meta:
            continue
        kind = meta.get("kind", "chart")
        selected_kind_counters[kind] = selected_kind_counters.get(kind, 0) + 1
        position_map[key] = selected_kind_counters[kind]

    group_order = [
        "Indicadores superiores", "Madurez y cumplimiento", "Métricas operativas",
        "Gráficas de madurez y cumplimiento", "Gráficas operativas",
        "Visualizaciones creadas por el usuario", "Elementos creados por el usuario",
    ]
    widget_groups = []
    for group_name in group_order:
        widgets = []
        group_position = 0
        for key, item in available.items():
            if item.get("group") != group_name:
                continue
            group_position += 1
            widget = dict(item)
            widget["key"] = key
            widget["dom_id"] = widget.get("dom_id") or _dashboard_dom_id(key)
            widget["default_order"] = group_position
            widget["presentation_label"] = widget.get("presentation_label") or ("Indicador" if widget.get("kind") == "kpi" else "Gráfica original")
            widgets.append(widget)
        if widgets:
            widget_groups.append({"title": group_name, "widgets": widgets})

    custom_widgets = _dashboard_custom_widgets_for_user(usuario_actual.id)
    custom_rows = []
    for widget in custom_widgets:
        source = DASHBOARD_DATA_SOURCE_MAP.get(widget.source_key, {})
        custom_rows.append({
            "id": widget.id,
            "key": _dashboard_custom_key(widget.id),
            "source_label": source.get("label", widget.source_key),
            "type_label": DASHBOARD_VISUALIZATION_LABELS.get(widget.widget_type, widget.widget_type),
            "visible": _dashboard_custom_key(widget.id) in selected_set,
        })

    edit_widget = None
    edit_id = request.args.get('edit_widget', type=int)
    if edit_id:
        edit_widget = DashboardCustomWidget.query.filter_by(id=edit_id, user_id=usuario_actual.id).first()

    first_source = DASHBOARD_DATA_SOURCE_CATALOG[0]
    if edit_widget:
        edit_source = DASHBOARD_DATA_SOURCE_MAP.get(edit_widget.source_key, first_source)
        allowed = edit_source.get("allowed_views", [])
        current_view = edit_widget.widget_type if edit_widget.widget_type in allowed else (allowed[0] if allowed else "gauge")
        builder_values = {"custom_id": edit_widget.id, "source_key": edit_widget.source_key, "widget_type": current_view}
    else:
        builder_values = {"custom_id": "", "source_key": first_source["key"], "widget_type": first_source.get("allowed_views", ["gauge"])[0]}

    source_groups = []
    names = []
    for source in DASHBOARD_DATA_SOURCE_CATALOG:
        name = source.get("group", "Otras fuentes")
        if name not in names:
            names.append(name)
    for name in names:
        source_groups.append({"title": name, "sources": [dict(item) for item in DASHBOARD_DATA_SOURCE_CATALOG if item.get("group") == name]})

    content = render_template_string("""
    <div class="dashsimple-shell">
      <div class="dashsimple-header">
        <div class="dashsimple-header-icon"><i class="bi bi-grid-1x2-fill"></i></div>
        <div>
          <div class="dashsimple-eyebrow">SGSI · Administración</div>
          <h3>Diseñar Centro de Control</h3>
          <p>Seleccione una fuente de datos y la forma en que desea verla. Nada más.</p>
        </div>
        <a href="{{ url_for('menu') }}" class="btn btn-light rounded-pill px-4 fw-bold ms-auto">
          <i class="bi bi-speedometer2 me-1"></i> Ver Centro de Control
        </a>
      </div>

      <section class="dashsimple-builder" id="customBuilder">
        <div class="dashsimple-builder-title">
          <div>
            <h4>{{ 'Editar visualización' if edit_widget else 'Agregar una visualización' }}</h4>
            <p>Los niveles de madurez permiten araña o velocímetro. Las demás fuentes muestran únicamente las opciones compatibles.</p>
          </div>
          {% if edit_widget %}
            <a href="{{ url_for('dashboard_config') }}#customBuilder" class="btn btn-outline-secondary rounded-pill btn-sm">Cancelar</a>
          {% endif %}
        </div>

        <form method="post" class="dashsimple-two-fields">
          <input type="hidden" name="action" value="{{ 'update_custom' if edit_widget else 'create_custom' }}">
          <input type="hidden" name="custom_id" value="{{ builder.custom_id }}">

          <div class="dashsimple-field">
            <label>1. Fuente de datos</label>
            <select name="source_key" id="dashsimpleSource" class="form-select" required>
              {% for group in source_groups %}
                <optgroup label="{{ group.title }}">
                  {% for source in group.sources %}
                    <option value="{{ source.key }}"
                            data-views="{{ source.allowed_views|join(',') }}"
                            data-kind="{{ source.data_kind }}"
                            data-description="{{ source.description }}"
                            {% if builder.source_key == source.key %}selected{% endif %}>
                      {{ source.label }}
                    </option>
                  {% endfor %}
                </optgroup>
              {% endfor %}
            </select>
            <small id="dashsimpleSourceHelp"></small>
          </div>

          <div class="dashsimple-field">
            <label>2. ¿Cómo lo quiere presentar?</label>
            <select name="widget_type" id="dashsimpleView" class="form-select" required>
              {% for key, label in visualization_options.items() %}
                {% if key != 'kpi' %}
                  <option value="{{ key }}" {% if builder.widget_type == key %}selected{% endif %}>{{ label }}</option>
                {% endif %}
              {% endfor %}
            </select>
            <small id="dashsimpleViewHelp"></small>
          </div>

          <div class="dashsimple-submit">
            <button type="submit" class="btn btn-primary rounded-pill px-4 fw-bold">
              <i class="bi {{ 'bi-save2' if edit_widget else 'bi-plus-circle' }} me-1"></i>
              {{ 'Guardar cambio' if edit_widget else 'Agregar al Centro de Control' }}
            </button>
          </div>
        </form>
      </section>

      {% if custom_rows %}
        <section class="dashsimple-created">
          <div class="dashsimple-section-head">
            <div><h4>Visualizaciones creadas</h4><p>Fuente y presentación seleccionadas por el usuario.</p></div>
            <span class="badge rounded-pill text-bg-primary">{{ custom_rows|length }}</span>
          </div>
          <div class="dashsimple-created-grid">
            {% for row in custom_rows %}
              <div class="dashsimple-created-row">
                <div>
                  <strong>{{ row.source_label }}</strong>
                  <span>{{ row.type_label }}</span>
                  <span class="badge rounded-pill {{ 'text-bg-success' if row.visible else 'text-bg-secondary' }}">{{ 'Visible' if row.visible else 'Oculta' }}</span>
                </div>
                <div class="dashsimple-row-actions">
                  <a href="{{ url_for('dashboard_config', edit_widget=row.id) }}#customBuilder" class="btn btn-outline-primary rounded-pill btn-sm"><i class="bi bi-pencil-square"></i> Editar</a>
                  <form method="post" class="m-0" onsubmit="return confirm('¿Eliminar esta visualización?');">
                    <input type="hidden" name="action" value="delete_custom">
                    <input type="hidden" name="custom_id" value="{{ row.id }}">
                    <button type="submit" class="btn btn-outline-danger rounded-pill btn-sm"><i class="bi bi-trash3"></i> Eliminar</button>
                  </form>
                </div>
              </div>
            {% endfor %}
          </div>
        </section>
      {% endif %}

      <form method="post" id="dashboardConfigForm">
        <section class="dashsimple-current">
          <div class="dashsimple-section-head">
            <div><h4>Qué aparece en el inicio</h4><p>Active, desactive y ordene las visualizaciones del Centro de Control.</p></div>
            <div class="dashsimple-quick-actions">
              <button type="button" id="dashsimpleSelectAll" class="btn btn-outline-primary rounded-pill btn-sm">Seleccionar todo</button>
              <button type="button" id="dashsimpleClearAll" class="btn btn-outline-secondary rounded-pill btn-sm">Desmarcar todo</button>
            </div>
          </div>

          {% for group in widget_groups %}
            <details class="dashsimple-group" {% if group.title in ['Visualizaciones creadas por el usuario','Elementos creados por el usuario'] %}open{% endif %}>
              <summary>{{ group.title }} <span>{{ group.widgets|length }}</span></summary>
              <div class="dashsimple-options">
                {% for widget in group.widgets %}
                  <div class="dashsimple-option">
                    <div class="form-check form-switch">
                      <input class="form-check-input dashboard-widget-check" type="checkbox" role="switch"
                             name="widgets" value="{{ widget.key }}" id="widget_{{ widget.dom_id }}"
                             data-order-id="order_{{ widget.dom_id }}" data-kind="{{ widget.kind }}"
                             {% if widget.key in selected_set %}checked{% endif %}>
                      <label class="form-check-label" for="widget_{{ widget.dom_id }}">
                        <strong>{{ widget.label }}</strong>
                        <span>{{ widget.presentation_label }}</span>
                      </label>
                    </div>
                    <div class="dashsimple-order">
                      <label>Orden</label>
                      <input type="number" min="1" max="99" name="order_{{ widget.key }}"
                             id="order_{{ widget.dom_id }}" class="form-control"
                             value="{{ position_map.get(widget.key, widget.default_order) }}">
                    </div>
                  </div>
                {% endfor %}
              </div>
            </details>
          {% endfor %}
        </section>

        <div class="dashsimple-savebar">
          <button type="submit" name="action" value="reset" class="btn btn-outline-danger rounded-pill"
                  onclick="return confirm('¿Restablecer el Centro de Control al diseño inicial?');">
            <i class="bi bi-arrow-counterclockwise me-1"></i> Restablecer
          </button>
          <button type="submit" name="action" value="save" class="btn btn-success rounded-pill px-4 fw-bold">
            <i class="bi bi-save2 me-1"></i> Guardar lo que aparece
          </button>
        </div>
      </form>
    </div>

    <style>
      body{background-image:url('/static/img/ccsgsi.jpg');background-size:cover;background-position:center;background-attachment:fixed;background-repeat:no-repeat;}
      .dashsimple-shell{width:96%;max-width:1450px;margin:22px auto 36px;}
      .dashsimple-header{display:flex;align-items:center;gap:15px;background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);border-radius:20px;padding:17px 22px;color:#fff;box-shadow:0 16px 32px rgba(15,23,42,.24);margin-bottom:14px;}
      .dashsimple-header-icon{width:54px;height:54px;min-width:54px;border-radius:16px;background:#fff;color:#0b4a8f;display:flex;align-items:center;justify-content:center;font-size:1.35rem;}
      .dashsimple-eyebrow{font-size:.67rem;font-weight:900;text-transform:uppercase;letter-spacing:.06em;opacity:.88;}.dashsimple-header h3{margin:2px 0 3px;color:#fff!important;font-size:1.36rem;font-weight:950;}.dashsimple-header p{margin:0;font-size:.79rem;opacity:.95;}
      .dashsimple-builder,.dashsimple-created,.dashsimple-current,.dashsimple-savebar{background:rgba(255,255,255,.98);border:1px solid #bdd7ee;border-radius:18px;box-shadow:0 12px 28px rgba(15,55,95,.12);}
      .dashsimple-builder{padding:18px 20px;margin-bottom:14px;}.dashsimple-builder-title,.dashsimple-section-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;padding-bottom:12px;border-bottom:1px solid #d7e6f3;margin-bottom:14px;}.dashsimple-builder-title h4,.dashsimple-section-head h4{margin:0;color:#123f72;font-size:1rem;font-weight:950;}.dashsimple-builder-title p,.dashsimple-section-head p{margin:4px 0 0;color:#637991;font-size:.73rem;}
      .dashsimple-two-fields{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr) auto;gap:14px;align-items:end;}.dashsimple-field label{display:block;color:#294d72;font-size:.74rem;font-weight:950;margin-bottom:6px;}.dashsimple-field .form-select{min-height:44px;font-size:.82rem;}.dashsimple-field small{display:block;min-height:18px;margin-top:5px;color:#6a7d91;font-size:.66rem;}.dashsimple-submit .btn{min-height:44px;white-space:nowrap;font-size:.80rem;}
      .dashsimple-created{padding:18px 20px;margin-bottom:14px;}.dashsimple-created-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;}.dashsimple-created-row{border:1px solid #d4e4f1;border-radius:14px;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;gap:12px;background:#fff;}.dashsimple-created-row strong{display:block;color:#173d69;font-size:.81rem;}.dashsimple-created-row span:not(.badge){display:block;color:#6b7f94;font-size:.69rem;margin:3px 0 6px;}.dashsimple-row-actions{display:flex;gap:7px;align-items:center;flex-wrap:wrap;justify-content:flex-end;}
      .dashsimple-current{padding:18px 20px;}.dashsimple-quick-actions{display:flex;gap:8px;flex-wrap:wrap;}.dashsimple-group{border:1px solid #d6e4f0;border-radius:14px;margin-bottom:10px;background:#fbfdff;overflow:hidden;}.dashsimple-group summary{cursor:pointer;padding:12px 14px;color:#173d69;font-size:.80rem;font-weight:950;display:flex;justify-content:space-between;align-items:center;}.dashsimple-group summary span{font-size:.67rem;background:#dcecff;color:#0b4a8f;padding:3px 9px;border-radius:999px;}.dashsimple-options{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;padding:0 12px 12px;}.dashsimple-option{display:flex;align-items:center;justify-content:space-between;gap:12px;border:1px solid #dbe7f1;border-radius:12px;padding:10px 12px;background:#fff;}.dashsimple-option .form-check{display:flex;align-items:flex-start;gap:9px;min-width:0;}.dashsimple-option .form-check-input{width:2.2em;height:1.18em;margin-top:2px;}.dashsimple-option label{min-width:0;}.dashsimple-option strong{display:block;color:#173d69;font-size:.76rem;line-height:1.2;}.dashsimple-option label span{display:block;color:#75869a;font-size:.65rem;margin-top:2px;}.dashsimple-order{width:68px;flex:0 0 68px;text-align:center;}.dashsimple-order label{display:block;font-size:.60rem;font-weight:900;color:#687b90;margin-bottom:3px;}.dashsimple-order input{text-align:center;min-height:34px;padding:4px;font-size:.75rem;font-weight:850;}
      .dashsimple-savebar{margin-top:14px;padding:14px 18px;display:flex;justify-content:flex-end;gap:10px;flex-wrap:wrap;}
      @media(max-width:1050px){.dashsimple-two-fields{grid-template-columns:1fr 1fr;}.dashsimple-submit{grid-column:span 2;}.dashsimple-submit .btn{width:100%;}.dashsimple-options,.dashsimple-created-grid{grid-template-columns:1fr;}}
      @media(max-width:700px){.dashsimple-shell{width:98%;margin-top:8px;}.dashsimple-header{flex-direction:column;text-align:center;}.dashsimple-header .btn{margin-left:0!important;width:100%;}.dashsimple-two-fields{grid-template-columns:1fr;}.dashsimple-submit{grid-column:span 1;}.dashsimple-builder-title,.dashsimple-section-head{flex-direction:column;text-align:center;align-items:center;}.dashsimple-created-row{flex-direction:column;text-align:center;}.dashsimple-row-actions{justify-content:center;}.dashsimple-option{align-items:flex-start;}.dashsimple-savebar .btn{width:100%;}}
    </style>

    <script>
      (function(){
        const source = document.getElementById('dashsimpleSource');
        const view = document.getElementById('dashsimpleView');
        const sourceHelp = document.getElementById('dashsimpleSourceHelp');
        const viewHelp = document.getElementById('dashsimpleViewHelp');
        const checks = Array.from(document.querySelectorAll('.dashboard-widget-check'));
        const selectAll = document.getElementById('dashsimpleSelectAll');
        const clearAll = document.getElementById('dashsimpleClearAll');

        function refreshViews(){
          if(!source || !view) return;
          const option = source.options[source.selectedIndex];
          if(!option) return;
          const allowed = (option.dataset.views || '').split(',').filter(Boolean);
          Array.from(view.options).forEach(function(item){item.disabled = !allowed.includes(item.value);});
          if(!allowed.includes(view.value)){view.value = allowed[0] || '';}
          if(sourceHelp) sourceHelp.textContent = option.dataset.description || '';
          if(viewHelp){
            const kind = option.dataset.kind || '';
            viewHelp.textContent = kind === 'maturity' ? 'Disponible: araña o velocímetro.' : (kind === 'timeline' ? 'Disponible: línea en el tiempo o barras.' : 'Se muestran únicamente las presentaciones compatibles.');
          }
        }

        function renumber(){
          const counters = {kpi:1, chart:1};
          checks.forEach(function(check){
            if(!check.checked) return;
            const kind = check.dataset.kind || 'chart';
            const input = document.getElementById(check.dataset.orderId);
            if(input){input.value = counters[kind] || 1;}
            counters[kind] = (counters[kind] || 1) + 1;
          });
        }

        if(source) source.addEventListener('change', refreshViews);
        if(selectAll) selectAll.addEventListener('click', function(){checks.forEach(function(check){check.checked=true;});renumber();});
        if(clearAll) clearAll.addEventListener('click', function(){checks.forEach(function(check){check.checked=false;});});
        refreshViews();
      })();
    </script>
    """,
    usuario=usuario_actual,
    widget_groups=widget_groups,
    selected_set=selected_set,
    position_map=position_map,
    source_groups=source_groups,
    custom_rows=custom_rows,
    edit_widget=edit_widget,
    builder=builder_values,
    visualization_options=DASHBOARD_VISUALIZATION_LABELS)

    return render_template_string(BASE, content=content, current_user=usuario_actual)


# =========================
# API JSON TABLERO PRINCIPAL
# =========================
@app.route('/dashboard/status', methods=['GET'])
@login_required
def dashboard_status():
    try:
        user_id = session.get("user_id")
        selected_keys = _dashboard_get_selected_keys(user_id)
        payload = _dashboard_build_payload(selected_keys, user_id)
        return jsonify({
            "ok": True,
            "iso_radar_b64": payload.get("iso_radar_b64", ""),
            "iso_pct": float(payload.get("iso_pct", 0) or 0),
            "nist_radar_b64": payload.get("nist_radar_b64", ""),
            "nist_pct": float(payload.get("nist_pct", 0) or 0),
            "datos_gauge_b64": payload.get("datos_gauge_b64", ""),
            "datos_pct": float(payload.get("datos_pct", 0) or 0),
            "scorecard_terceros_pct": float(payload.get("scorecard_terceros_pct", 0) or 0),
            "pci_pct": float(payload.get("pci_pct", 0) or 0),
            "pci_gauge_b64": payload.get("pci_gauge_b64", ""),
            "soc2_pct": float(payload.get("soc2_pct", 0) or 0),
            "soc2_radar_b64": payload.get("soc2_radar_b64", ""),
            "ai_maturity_pct": float(payload.get("ai_maturity_pct", 0) or 0),
            "ai_radar_b64": payload.get("ai_radar_b64", ""),
            "risks_active_count": float(payload.get("risks_active_count", 0) or 0),
            "risks_outside_appetite_count": float(payload.get("risks_outside_appetite_count", 0) or 0),
            "incidents_open_count": float(payload.get("incidents_open_count", 0) or 0),
            "incidents_compliance_pct": float(payload.get("incidents_compliance_pct", 0) or 0),
            "vulnerabilities_open_count": float(payload.get("vulnerabilities_open_count", 0) or 0),
            "vulnerabilities_critical_count": float(payload.get("vulnerabilities_critical_count", 0) or 0),
            "plans_open_count": float(payload.get("plans_open_count", 0) or 0),
            "plans_overdue_count": float(payload.get("plans_overdue_count", 0) or 0),
            "legal_noncompliant_count": float(payload.get("legal_noncompliant_count", 0) or 0),
            "providers_high_count": float(payload.get("providers_high_count", 0) or 0),
            "security_culture_pct": float(payload.get("security_culture_pct", 0) or 0),
            "riesgos_b64": payload.get("riesgos_b64", ""),
            "incidentes_b64": payload.get("incidentes_b64", ""),
            "vulnerabilidades_b64": payload.get("vulnerabilidades_b64", ""),
            "proveedores_criticidad_b64": payload.get("proveedores_criticidad_b64", ""),
            "planes_accion_estado_b64": payload.get("planes_accion_estado_b64", ""),
            "requisitos_legales_estado_b64": payload.get("requisitos_legales_estado_b64", ""),
            "custom_widgets": payload.get("custom_widgets", {}),
            "selected_widgets": selected_keys,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ====================
# Menú principal con tablero compacto
# ====================


# ============================================================================
# GRAC MOBILE — DISTRIBUCIÓN DESDE ADMINISTRACIÓN (ANDROID + IOS TESTFLIGHT)
# ============================================================================
# Android: el APK se almacena fuera de /static y se entrega únicamente a
# usuarios autenticados con permiso "Aplicación móvil".
# iOS: se publica el enlace de invitación de TestFlight (no se almacena IPA).
# El historial se conserva en una DB independiente para no modificar sgsi.db.

MOBILE_RELEASE_DB_PATH = os.path.join(app.instance_path, "mobile_app.db")
MOBILE_RELEASE_DIR = os.path.join(app.instance_path, "mobile_releases")
os.makedirs(MOBILE_RELEASE_DIR, exist_ok=True)

# Un APK release puede superar los 50 MB. La ruta valida además un máximo propio.
app.config["MAX_CONTENT_LENGTH"] = max(
    int(app.config.get("MAX_CONTENT_LENGTH") or 0),
    300 * 1024 * 1024,
)


def get_mobile_release_db_connection():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(MOBILE_RELEASE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_mobile_release_db():
    conn = get_mobile_release_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mobile_releases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            version TEXT NOT NULL,
            build_number INTEGER NOT NULL DEFAULT 1,
            min_version TEXT,
            min_build INTEGER NOT NULL DEFAULT 1,
            mandatory INTEGER NOT NULL DEFAULT 0,
            release_notes TEXT,
            file_name TEXT,
            stored_name TEXT,
            distribution_url TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            published_at TEXT NOT NULL,
            published_by TEXT
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_mobile_releases_platform_active
        ON mobile_releases(platform, is_active, id DESC)
    """)
    conn.commit()
    conn.close()


def _mobile_release_row(release_id):
    conn = get_mobile_release_db_connection()
    row = conn.execute(
        "SELECT * FROM mobile_releases WHERE id = ?",
        (int(release_id),),
    ).fetchone()
    conn.close()
    return row


def _mobile_release_active(platform):
    init_mobile_release_db()
    conn = get_mobile_release_db_connection()
    row = conn.execute("""
        SELECT *
        FROM mobile_releases
        WHERE platform = ? AND is_active = 1
        ORDER BY id DESC
        LIMIT 1
    """, ((platform or "").strip().lower(),)).fetchone()
    conn.close()
    return row


def _mobile_release_history(limit=50):
    init_mobile_release_db()
    conn = get_mobile_release_db_connection()
    rows = conn.execute("""
        SELECT *
        FROM mobile_releases
        ORDER BY published_at DESC, id DESC
        LIMIT ?
    """, (int(limit),)).fetchall()
    conn.close()
    return rows


def _mobile_release_version_tuple(value):
    """Convierte 1.2.3 / 1.2 / v1.2.3 en una tupla comparable."""
    raw = str(value or "0").strip().lower().lstrip("v")
    nums = re.findall(r"\d+", raw)
    parts = [int(x) for x in nums[:4]]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts)


def _mobile_release_is_newer(latest_version, latest_build, current_version, current_build):
    latest_v = _mobile_release_version_tuple(latest_version)
    current_v = _mobile_release_version_tuple(current_version)
    if latest_v != current_v:
        return latest_v > current_v
    return int(latest_build or 0) > int(current_build or 0)


def _mobile_release_is_below_min(current_version, current_build, min_version, min_build):
    min_v = _mobile_release_version_tuple(min_version or "0")
    current_v = _mobile_release_version_tuple(current_version)
    if current_v != min_v:
        return current_v < min_v
    return int(current_build or 0) < int(min_build or 0)


def _mobile_release_qr_data_uri(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        img = qrcode.make(value)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


def _mobile_release_allowed(user):
    if not user:
        return False
    return user.role == "admin" or verificar_permiso(user, "Aplicación móvil")


def _mobile_release_external_download_url(row):
    if not row:
        return None
    if row["platform"] == "ios":
        return (row["distribution_url"] or "").strip() or None
    return url_for("mobile_app_user_download", release_id=row["id"], _external=True)


def _mobile_release_publish(
    *, platform, version, build_number, min_version, min_build,
    mandatory, release_notes, published_by, file_name=None,
    stored_name=None, distribution_url=None,
):
    init_mobile_release_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_mobile_release_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE mobile_releases SET is_active = 0 WHERE platform = ?",
        (platform,),
    )
    cur.execute("""
        INSERT INTO mobile_releases (
            platform, version, build_number, min_version, min_build,
            mandatory, release_notes, file_name, stored_name,
            distribution_url, is_active, published_at, published_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
    """, (
        platform,
        version,
        int(build_number),
        min_version or version,
        int(min_build),
        1 if mandatory else 0,
        release_notes,
        file_name,
        stored_name,
        distribution_url,
        now,
        published_by,
    ))
    release_id = cur.lastrowid
    conn.commit()
    conn.close()
    return release_id


init_mobile_release_db()



# ============================================================================
# GRAC MOBILE — MÓDULO DE CONSULTA Y DESCARGA (WEB / ON-PREMISE)
# Independiente de Administración. Solo lectura, sin publicar ni eliminar.
# Acceso por el permiso individual "Aplicación móvil".
# ============================================================================
@app.route("/aplicacion_movil", methods=["GET"])
@login_required
def aplicacion_movil():
    usuario = User.query.get(session.get("user_id"))
    if not _mobile_release_allowed(usuario):
        abort(403, description="No tiene permiso para acceder al módulo Aplicación móvil.")

    android = _mobile_release_active("android")
    ios = _mobile_release_active("ios")
    android_url = _mobile_release_external_download_url(android)
    ios_url = _mobile_release_external_download_url(ios)
    android_qr = _mobile_release_qr_data_uri(android_url)
    ios_qr = _mobile_release_qr_data_uri(ios_url)

    # Las tarjetas reproducen la información de descarga visible en
    # Administración, SIN formularios de publicación, historial ni edición.
    contenido = render_template_string(r"""
    <div class="grac-mobile-user-shell">
      <div class="grac-mobile-user-hero">
        <div class="grac-mobile-user-icon"><i class="bi bi-phone"></i></div>
        <div>
          <h2>Aplicación móvil</h2>
          <p>Distribución controlada de GRAC Mobile para Android y iOS mediante TestFlight.</p>
        </div>
      </div>
      <div class="row g-3">
        <div class="col-xl-6">
          <div class="card border-0 shadow-sm h-100 grac-mobile-user-card">
            <div class="card-body p-4">
              <div class="d-flex align-items-center gap-3 mb-3">
                <div class="grac-mobile-platform android"><i class="bi bi-android2"></i></div>
                <div><h4 class="mb-0 fw-bold">Android</h4>
                  <div class="text-muted small">Descarga directa del APK publicado en GRAC</div>
                </div>
              </div>
              {% if android %}
              <div class="grac-mobile-version mb-3">
                <div><b>Versión:</b> {{ android['version'] }} · Build {{ android['build_number'] }}</div>
                <div><b>Publicada:</b> {{ android['published_at'] }}</div>
                <div><b>Por:</b> {{ android['published_by'] or '—' }}</div>
                <div><b>Mínima:</b> {{ android['min_version'] or android['version'] }} · Build {{ android['min_build'] }}</div>
                <div><b>Actualización:</b> {% if android['mandatory'] %}<span class="badge bg-danger">Obligatoria</span>{% else %}<span class="badge bg-success">Opcional</span>{% endif %}</div>
              </div>
              <div class="d-flex flex-wrap align-items-center gap-3">
                <a href="{{ android_url }}" class="btn btn-primary rounded-pill px-4" data-no-progress="true"><i class="bi bi-download me-1"></i> Descargar APK</a>
                {% if android_qr %}<img class="grac-mobile-qr" src="{{ android_qr }}" alt="Código QR para descargar Android">{% endif %}
              </div>
              {% else %}<div class="alert alert-warning">Todavía no hay una versión Android publicada en este servidor.</div>{% endif %}
            </div>
          </div>
        </div>
        <div class="col-xl-6">
          <div class="card border-0 shadow-sm h-100 grac-mobile-user-card">
            <div class="card-body p-4">
              <div class="d-flex align-items-center gap-3 mb-3">
                <div class="grac-mobile-platform ios"><i class="bi bi-apple"></i></div>
                <div><h4 class="mb-0 fw-bold">iOS / iPadOS</h4>
                  <div class="text-muted small">Instalación mediante Apple TestFlight</div>
                </div>
              </div>
              {% if ios %}
              <div class="grac-mobile-version mb-3">
                <div><b>Versión:</b> {{ ios['version'] }} · Build {{ ios['build_number'] }}</div>
                <div><b>Publicada:</b> {{ ios['published_at'] }}</div>
                <div><b>Por:</b> {{ ios['published_by'] or '—' }}</div>
                <div><b>Mínima:</b> {{ ios['min_version'] or ios['version'] }} · Build {{ ios['min_build'] }}</div>
                <div><b>Actualización:</b> {% if ios['mandatory'] %}<span class="badge bg-danger">Obligatoria</span>{% else %}<span class="badge bg-success">Opcional</span>{% endif %}</div>
              </div>
              <div class="d-flex flex-wrap align-items-center gap-3">
                <a href="{{ ios_url }}" class="btn btn-dark rounded-pill px-4" target="_blank" rel="noopener noreferrer" data-no-progress="true"><i class="bi bi-apple me-1"></i> Abrir en TestFlight</a>
                {% if ios_qr %}<img class="grac-mobile-qr" src="{{ ios_qr }}" alt="Código QR TestFlight">{% endif %}
              </div>
              {% else %}<div class="alert alert-warning">Todavía no hay un enlace de TestFlight publicado en este servidor.</div>{% endif %}
            </div>
          </div>
        </div>
      </div>
    </div>
    <style>
      .grac-mobile-user-shell{width:96%;max-width:1200px;margin:24px auto 28px;}
      .grac-mobile-user-hero{display:flex;align-items:center;gap:16px;min-height:94px;padding:18px 25px;margin-bottom:18px;color:white;border-radius:20px;background:linear-gradient(115deg,#062b55,#0b4a8f,#226ab5);box-shadow:0 12px 26px rgba(20,60,110,.21);}
      .grac-mobile-user-hero h2{font-size:1.55rem!important;font-weight:850;margin:0 0 4px!important;color:#fff!important;}
      .grac-mobile-user-hero p{font-size:.92rem;margin:0;color:rgba(255,255,255,.94);}
      .grac-mobile-user-icon{width:56px;height:56px;min-width:56px;border-radius:14px;background:white;color:#0b4a8f;display:flex;align-items:center;justify-content:center;font-size:1.6rem;}
      .grac-mobile-user-card{border-radius:22px;overflow:hidden;}
      .grac-mobile-platform{width:60px;height:60px;min-width:60px;border-radius:17px;display:flex;align-items:center;justify-content:center;font-size:2rem;}
      .grac-mobile-platform.android{background:#e7f7ee;color:#198754;}
      .grac-mobile-platform.ios{background:#edf1f5;color:#111827;}
      .grac-mobile-version{background:#f8fafc;border:1px solid #e7edf4;border-radius:16px;padding:16px 20px;line-height:1.85;}
      .grac-mobile-qr{width:135px;height:135px;border-radius:16px;border:1px solid #e3e8ef;padding:8px;background:white;object-fit:contain;}
      @media(max-width:768px){.grac-mobile-user-hero{padding:16px;gap:12px}.grac-mobile-user-hero h2{font-size:1.3rem!important}.grac-mobile-user-shell{width:98%}}
    </style>
    """, android=android, ios=ios,
         android_url=android_url, ios_url=ios_url,
         android_qr=android_qr, ios_qr=ios_qr)
    return render_template_string(BASE, content=Markup(contenido))


@app.route("/aplicacion_movil/descargar/<int:release_id>", methods=["GET"])
@login_required
def mobile_app_user_download(release_id):
    usuario = User.query.get(session.get("user_id"))
    if not _mobile_release_allowed(usuario):
        abort(403, description="No tiene permiso para descargar GRAC Mobile.")

    release = _mobile_release_row(release_id)
    # Solo la versión Android actualmente publicada está disponible al usuario.
    if (not release or release["platform"] != "android"
            or not release["is_active"] or not release["stored_name"]):
        abort(404)
    archivo = safe_join(MOBILE_RELEASE_DIR, release["stored_name"])
    if not archivo or not os.path.isfile(archivo):
        abort(404)

    registrar_log(usuario.username, f"Descargó GRAC Mobile Android versión {release['version']} build {release['build_number']}.")
    return send_file(
        archivo,
        mimetype="application/vnd.android.package-archive",
        as_attachment=True,
        download_name=f"GRAC-Mobile-{release['version']}-build-{release['build_number']}.apk",
        conditional=True,
    )


@app.route("/admin/mobile-app", methods=["GET", "POST"])
@login_required
def admin_mobile_app():
    user = User.query.get(session.get("user_id"))
    if not _mobile_release_allowed(user):
        registrar_log(
            user.username if user else "Desconocido",
            "Intento de acceso no autorizado al módulo Aplicación móvil.",
        )
        flash("No tiene permiso para acceder a Aplicación móvil.", "danger")
        return redirect(url_for("menu"))

    if request.method == "POST":
        # La consulta/descarga es permitida a usuarios con permiso, pero toda
        # publicación, activación o eliminación es exclusiva del administrador.
        if user.role != "admin":
            flash("Solo el administrador puede publicar o modificar versiones.", "danger")
            return redirect(url_for("admin_mobile_app"))

        action = (request.form.get("action") or "").strip().lower()

        if action in {"publish_android", "publish_ios"}:
            platform = "android" if action == "publish_android" else "ios"
            version = (request.form.get("version") or "").strip()
            min_version = (request.form.get("min_version") or version).strip() or version
            notes = (request.form.get("release_notes") or "").strip()
            mandatory = request.form.get("mandatory") == "1"

            try:
                build_number = max(1, int(request.form.get("build_number") or 1))
                min_build = max(1, int(request.form.get("min_build") or 1))
            except Exception:
                flash("El número de build debe ser un entero mayor a cero.", "warning")
                return redirect(url_for("admin_mobile_app"))

            if not version:
                flash("La versión es obligatoria.", "warning")
                return redirect(url_for("admin_mobile_app"))

            file_name = None
            stored_name = None
            distribution_url = None

            if platform == "android":
                if request.content_length and request.content_length > 260 * 1024 * 1024:
                    flash("El APK supera el máximo permitido de 260 MB.", "danger")
                    return redirect(url_for("admin_mobile_app"))

                apk = request.files.get("apk_file")
                if not apk or not apk.filename:
                    flash("Debes seleccionar el archivo APK de Android.", "warning")
                    return redirect(url_for("admin_mobile_app"))

                original = secure_filename(apk.filename)
                if not original.lower().endswith(".apk"):
                    flash("Solo se permite publicar archivos .apk.", "danger")
                    return redirect(url_for("admin_mobile_app"))

                safe_version = re.sub(r"[^0-9A-Za-z._-]+", "-", version).strip("-") or "version"
                stored_name = f"GRAC-Mobile-{safe_version}-{build_number}-{uuid.uuid4().hex[:10]}.apk"
                target = os.path.join(MOBILE_RELEASE_DIR, stored_name)
                apk.save(target)

                if not os.path.isfile(target) or os.path.getsize(target) <= 0:
                    try:
                        if os.path.isfile(target):
                            os.remove(target)
                    except Exception:
                        pass
                    flash("No fue posible guardar el APK.", "danger")
                    return redirect(url_for("admin_mobile_app"))

                file_name = original

            else:
                distribution_url = (request.form.get("testflight_url") or "").strip()
                try:
                    parsed = urlparse(distribution_url)
                except Exception:
                    parsed = None
                if (
                    not parsed
                    or parsed.scheme != "https"
                    or (parsed.netloc or "").lower() != "testflight.apple.com"
                ):
                    flash(
                        "Ingresa un enlace válido de TestFlight, por ejemplo https://testflight.apple.com/join/XXXXXXXX.",
                        "warning",
                    )
                    return redirect(url_for("admin_mobile_app"))

            release_id = _mobile_release_publish(
                platform=platform,
                version=version,
                build_number=build_number,
                min_version=min_version,
                min_build=min_build,
                mandatory=mandatory,
                release_notes=notes,
                published_by=user.username,
                file_name=file_name,
                stored_name=stored_name,
                distribution_url=distribution_url,
            )
            registrar_log(
                user.username,
                f"Publicó GRAC Mobile {platform.upper()} versión {version} build {build_number} (release #{release_id}).",
            )
            flash(
                f"GRAC Mobile {platform.upper()} {version} (build {build_number}) publicado correctamente.",
                "success",
            )
            return redirect(url_for("admin_mobile_app"))

        if action == "activate":
            release_id = request.form.get("release_id", type=int)
            row = _mobile_release_row(release_id)
            if not row:
                flash("La versión indicada no existe.", "warning")
                return redirect(url_for("admin_mobile_app"))
            conn = get_mobile_release_db_connection()
            conn.execute(
                "UPDATE mobile_releases SET is_active = 0 WHERE platform = ?",
                (row["platform"],),
            )
            conn.execute(
                "UPDATE mobile_releases SET is_active = 1 WHERE id = ?",
                (release_id,),
            )
            conn.commit()
            conn.close()
            registrar_log(
                user.username,
                f"Activó GRAC Mobile {row['platform'].upper()} versión {row['version']} build {row['build_number']}.",
            )
            flash("Versión activada correctamente.", "success")
            return redirect(url_for("admin_mobile_app"))

        if action == "delete":
            release_id = request.form.get("release_id", type=int)
            row = _mobile_release_row(release_id)
            if not row:
                flash("La versión indicada no existe.", "warning")
                return redirect(url_for("admin_mobile_app"))
            if row["stored_name"]:
                target = safe_join(MOBILE_RELEASE_DIR, row["stored_name"])
                try:
                    if target and os.path.isfile(target):
                        os.remove(target)
                except Exception as exc:
                    print("No se pudo eliminar APK histórico:", repr(exc))
            conn = get_mobile_release_db_connection()
            conn.execute("DELETE FROM mobile_releases WHERE id = ?", (release_id,))
            conn.commit()
            conn.close()
            registrar_log(
                user.username,
                f"Eliminó release GRAC Mobile #{release_id} ({row['platform']} {row['version']}).",
            )
            flash("Versión eliminada del historial.", "success")
            return redirect(url_for("admin_mobile_app"))

        flash("Acción no reconocida.", "warning")
        return redirect(url_for("admin_mobile_app"))

    android = _mobile_release_active("android")
    ios = _mobile_release_active("ios")
    history = _mobile_release_history(100) if user.role == "admin" else []

    android_url = _mobile_release_external_download_url(android)
    ios_url = _mobile_release_external_download_url(ios)
    android_qr = _mobile_release_qr_data_uri(android_url)
    ios_qr = _mobile_release_qr_data_uri(ios_url)

    inner = render_template_string(r"""
    <div class="container-fluid mobile-admin-shell">
      <!-- CABECERA alineada con los demás módulos de Administración -->
      <div class="mobile-admin-header-card">
        <div class="mobile-admin-header-overlay">
          <div class="mobile-admin-header-icon"><i class="bi bi-phone"></i></div>
          <div class="mobile-admin-header-text">
            <div class="mobile-admin-header-badge">SGSI · Administración</div>
            <h2 class="mobile-admin-title">Aplicación móvil</h2>
            <div class="mobile-admin-subtitle">Distribución controlada de GRAC Mobile para Android y iOS mediante TestFlight.</div>
          </div>
        </div>
      </div>

      <div class="row g-3">
        <div class="col-xl-6">
          <div class="card border-0 shadow-sm h-100">
            <div class="card-body p-4">
              <div class="d-flex align-items-center gap-3 mb-3">
                <div class="mobile-platform-icon android"><i class="bi bi-android2"></i></div>
                <div>
                  <h4 class="mb-0 fw-bold">Android</h4>
                  <div class="text-muted small">Descarga directa del APK publicado en GRAC</div>
                </div>
              </div>
              {% if android %}
                <div class="mobile-version-box mb-3">
                  <div><b>Versión:</b> {{ android['version'] }} · Build {{ android['build_number'] }}</div>
                  <div><b>Publicada:</b> {{ android['published_at'] }}</div>
                  <div><b>Por:</b> {{ android['published_by'] or '—' }}</div>
                  <div><b>Mínima:</b> {{ android['min_version'] or android['version'] }} · Build {{ android['min_build'] }}</div>
                  <div><b>Actualización:</b> {% if android['mandatory'] %}<span class="badge bg-danger">Obligatoria</span>{% else %}<span class="badge bg-success">Opcional</span>{% endif %}</div>
                </div>
                {% if android['release_notes'] %}<div class="alert alert-light border"><b>Novedades:</b><br>{{ android['release_notes'] }}</div>{% endif %}
                <div class="d-flex flex-wrap gap-3 align-items-center">
                  <a class="btn btn-primary rounded-pill px-4" href="{{ android_url }}" data-no-progress="true">
                    <i class="bi bi-download me-1"></i> Descargar APK
                  </a>
                  {% if android_qr %}<img src="{{ android_qr }}" class="mobile-qr" alt="QR Android">{% endif %}
                </div>
              {% else %}
                <div class="alert alert-warning mb-0">Todavía no hay una versión Android publicada.</div>
              {% endif %}
            </div>
          </div>
        </div>

        <div class="col-xl-6">
          <div class="card border-0 shadow-sm h-100">
            <div class="card-body p-4">
              <div class="d-flex align-items-center gap-3 mb-3">
                <div class="mobile-platform-icon ios"><i class="bi bi-apple"></i></div>
                <div>
                  <h4 class="mb-0 fw-bold">iOS / iPadOS</h4>
                  <div class="text-muted small">Instalación mediante Apple TestFlight</div>
                </div>
              </div>
              {% if ios %}
                <div class="mobile-version-box mb-3">
                  <div><b>Versión:</b> {{ ios['version'] }} · Build {{ ios['build_number'] }}</div>
                  <div><b>Publicada:</b> {{ ios['published_at'] }}</div>
                  <div><b>Por:</b> {{ ios['published_by'] or '—' }}</div>
                  <div><b>Mínima:</b> {{ ios['min_version'] or ios['version'] }} · Build {{ ios['min_build'] }}</div>
                  <div><b>Actualización:</b> {% if ios['mandatory'] %}<span class="badge bg-danger">Obligatoria</span>{% else %}<span class="badge bg-success">Opcional</span>{% endif %}</div>
                </div>
                {% if ios['release_notes'] %}<div class="alert alert-light border"><b>Novedades:</b><br>{{ ios['release_notes'] }}</div>{% endif %}
                <div class="d-flex flex-wrap gap-3 align-items-center">
                  <a class="btn btn-dark rounded-pill px-4" href="{{ ios_url }}" target="_blank" rel="noopener" data-no-progress="true">
                    <i class="bi bi-apple me-1"></i> Abrir en TestFlight
                  </a>
                  {% if ios_qr %}<img src="{{ ios_qr }}" class="mobile-qr" alt="QR TestFlight">{% endif %}
                </div>
              {% else %}
                <div class="alert alert-warning mb-0">Todavía no hay un enlace de TestFlight publicado.</div>
              {% endif %}
            </div>
          </div>
        </div>
      </div>

      {% if is_admin %}
      <div class="row g-3 mt-1">
        <div class="col-xl-6">
          <div class="card border-0 shadow-sm h-100">
            <div class="card-header bg-white border-0 pt-4 px-4"><h5 class="fw-bold mb-0">Publicar Android</h5></div>
            <div class="card-body px-4 pb-4">
              <form method="post" enctype="multipart/form-data" data-progress-text="Publicando APK de GRAC Mobile...">
                <input type="hidden" name="action" value="publish_android">
                <div class="row g-3">
                  <div class="col-md-6"><label class="form-label">Versión</label><input class="form-control" name="version" placeholder="0.2.0" required></div>
                  <div class="col-md-6"><label class="form-label">Build</label><input class="form-control" type="number" min="1" name="build_number" value="3" required></div>
                  <div class="col-md-6"><label class="form-label">Versión mínima</label><input class="form-control" name="min_version" placeholder="0.2.0"></div>
                  <div class="col-md-6"><label class="form-label">Build mínimo</label><input class="form-control" type="number" min="1" name="min_build" value="1"></div>
                  <div class="col-12"><label class="form-label">APK</label><input class="form-control" type="file" accept=".apk,application/vnd.android.package-archive" name="apk_file" required></div>
                  <div class="col-12"><label class="form-label">Notas de versión</label><textarea class="form-control" rows="3" name="release_notes" placeholder="Cambios incluidos en esta versión..."></textarea></div>
                  <div class="col-12 form-check ms-2"><input class="form-check-input" type="checkbox" value="1" name="mandatory" id="androidMandatory"><label class="form-check-label" for="androidMandatory">Actualización obligatoria</label></div>
                  <div class="col-12"><button class="btn btn-primary rounded-pill px-4" type="submit"><i class="bi bi-cloud-arrow-up me-1"></i> Publicar Android</button></div>
                </div>
              </form>
            </div>
          </div>
        </div>

        <div class="col-xl-6">
          <div class="card border-0 shadow-sm h-100">
            <div class="card-header bg-white border-0 pt-4 px-4"><h5 class="fw-bold mb-0">Publicar iOS / TestFlight</h5></div>
            <div class="card-body px-4 pb-4">
              <form method="post">
                <input type="hidden" name="action" value="publish_ios">
                <div class="row g-3">
                  <div class="col-md-6"><label class="form-label">Versión</label><input class="form-control" name="version" placeholder="0.2.0" required></div>
                  <div class="col-md-6"><label class="form-label">Build</label><input class="form-control" type="number" min="1" name="build_number" value="3" required></div>
                  <div class="col-md-6"><label class="form-label">Versión mínima</label><input class="form-control" name="min_version" placeholder="0.2.0"></div>
                  <div class="col-md-6"><label class="form-label">Build mínimo</label><input class="form-control" type="number" min="1" name="min_build" value="1"></div>
                  <div class="col-12"><label class="form-label">Enlace público TestFlight</label><input class="form-control" type="url" name="testflight_url" placeholder="https://testflight.apple.com/join/XXXXXXXX" required></div>
                  <div class="col-12"><label class="form-label">Notas de versión</label><textarea class="form-control" rows="3" name="release_notes" placeholder="Cambios incluidos en esta versión..."></textarea></div>
                  <div class="col-12 form-check ms-2"><input class="form-check-input" type="checkbox" value="1" name="mandatory" id="iosMandatory"><label class="form-check-label" for="iosMandatory">Actualización obligatoria</label></div>
                  <div class="col-12"><button class="btn btn-dark rounded-pill px-4" type="submit"><i class="bi bi-apple me-1"></i> Publicar TestFlight</button></div>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>

      <div class="card border-0 shadow-sm mt-3">
        <div class="card-header bg-white border-0 pt-4 px-4 d-flex justify-content-between align-items-center">
          <h5 class="fw-bold mb-0">Historial de versiones</h5>
          <span class="badge bg-light text-dark">{{ history|length }} registros</span>
        </div>
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light"><tr><th>Plataforma</th><th>Versión</th><th>Build</th><th>Publicación</th><th>Estado</th><th>Acciones</th></tr></thead>
            <tbody>
            {% for r in history %}
              <tr>
                <td>{% if r['platform']=='ios' %}<i class="bi bi-apple me-1"></i> iOS{% else %}<i class="bi bi-android2 me-1"></i> Android{% endif %}</td>
                <td>{{ r['version'] }}</td>
                <td>{{ r['build_number'] }}</td>
                <td>{{ r['published_at'] }}<br><small class="text-muted">{{ r['published_by'] or '' }}</small></td>
                <td>{% if r['is_active'] %}<span class="badge bg-success">Activa</span>{% else %}<span class="badge bg-secondary">Histórica</span>{% endif %}</td>
                <td class="text-nowrap">
                  {% if not r['is_active'] %}
                  <form method="post" class="d-inline">
                    <input type="hidden" name="action" value="activate"><input type="hidden" name="release_id" value="{{ r['id'] }}">
                    <button class="btn btn-sm btn-outline-primary rounded-pill" type="submit">Activar</button>
                  </form>
                  {% endif %}
                  <form method="post" class="d-inline" onsubmit="return confirm('¿Eliminar esta versión del historial?');">
                    <input type="hidden" name="action" value="delete"><input type="hidden" name="release_id" value="{{ r['id'] }}">
                    <button class="btn btn-sm btn-outline-danger rounded-pill" type="submit">Eliminar</button>
                  </form>
                </td>
              </tr>
            {% else %}
              <tr><td colspan="6" class="text-center text-muted py-4">No hay versiones publicadas todavía.</td></tr>
            {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
      {% endif %}
    </div>

    <style>
      .mobile-admin-shell{
        width:96%;
        max-width:1100px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }
      .mobile-admin-header-card{
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
      .mobile-admin-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }
      .mobile-admin-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }
      .mobile-admin-header-icon{
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
      .mobile-admin-header-text{
        max-width:900px;
        min-width:0;
      }
      .mobile-admin-header-badge{
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }
      .mobile-admin-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem !important;
        line-height:1.1 !important;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }
      .mobile-admin-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem !important;
        line-height:1.25 !important;
        margin-top:3px;
        overflow-wrap:break-word;
      }
      .mobile-platform-icon{width:54px;height:54px;border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:1.65rem;}
      .mobile-platform-icon.android{background:#e7f7ee;color:#198754;}
      .mobile-platform-icon.ios{background:#edf1f5;color:#111827;}
      .mobile-version-box{background:#f8fafc;border:1px solid #e7edf4;border-radius:16px;padding:14px 16px;line-height:1.75;}
      .mobile-qr{width:118px;height:118px;border-radius:14px;border:1px solid #e3e8ef;padding:6px;background:#fff;}
      .mobile-admin-shell .card{border-radius:20px;overflow:hidden;}
    </style>
    """,
        android=android,
        ios=ios,
        history=history,
        android_url=android_url,
        ios_url=ios_url,
        android_qr=android_qr,
        ios_qr=ios_qr,
        is_admin=(user.role == "admin"),
    )
    return render_template_string(BASE, content=Markup(inner))


@app.route("/admin/mobile-app/download/<int:release_id>")
@login_required
def admin_mobile_app_download(release_id):
    user = User.query.get(session.get("user_id"))
    if not _mobile_release_allowed(user):
        flash("No tiene permiso para descargar GRAC Mobile.", "danger")
        return redirect(url_for("menu"))

    row = _mobile_release_row(release_id)
    if not row or row["platform"] != "android" or not row["stored_name"]:
        abort(404)

    full_path = safe_join(MOBILE_RELEASE_DIR, row["stored_name"])
    if not full_path or not os.path.isfile(full_path):
        abort(404)

    registrar_log(
        user.username,
        f"Descargó GRAC Mobile Android versión {row['version']} build {row['build_number']}.",
    )
    return send_file(
        full_path,
        mimetype="application/vnd.android.package-archive",
        as_attachment=True,
        download_name=f"GRAC-Mobile-{row['version']}-build-{row['build_number']}.apk",
        conditional=True,
    )


@app.route('/')
@login_required
def menu():
    usuario_actual = User.query.get(session.get('user_id'))
    selected_widget_keys = _dashboard_get_selected_keys(session.get('user_id'))
    dashboard = _dashboard_build_payload(selected_widget_keys, session.get('user_id'))
    dashboard_kpis, dashboard_charts = _dashboard_prepare_view(
        selected_widget_keys,
        dashboard,
        session.get('user_id'),
    )

    if usuario_actual and usuario_actual.role == "admin":
        sections = MENU_SECTIONS
    else:
        sections = []
        for sec in MENU_SECTIONS:
            allowed_items = filtrar_items_menu(
                sec.get("items", []), usuario_actual,
                seccion_admin=(sec.get("title") == "Administración")
            )
            if allowed_items:
                sec2 = dict(sec)
                sec2["items"] = allowed_items
                sections.append(sec2)

    content = render_template_string("""
    <div class="soa-shell">

      <div class="sgsi-layout">

        <!-- MENÚ LATERAL COMPLETO -->
        <aside id="sgsiLocalMenu" class="sgsi-leftnav-wrap">

          <div id="sgsiLocalMenuToggle" class="sgsi-leftnav-arrow">
            <span class="sgsi-arrow-icon">‹</span>
          </div>

          <div class="sgsi-leftnav-card">

            <div class="sgsi-leftnav-list">

              <a class="sgsi-leftnav-link sgsi-panel-control-btn" href="/">
                <i class="bi bi-speedometer2"></i>
                <span>Centro de Control</span>
              </a>

              {% macro render_menu_items(items, prefix) %}
                {% for it in items %}
                  {% set item_id = prefix ~ "_item_" ~ loop.index %}

                  {% if it.get("children") %}
                    <li class="sgsi-node">
                      <a class="sgsi-dropdown-item sgsi-node-toggle"
                         href="javascript:void(0);"
                         data-target="{{ item_id }}">
                        <i class="bi {{ it.get('icon','bi-box') }}"></i>
                        <span>{{ it["label"] }}</span>
                      </a>

                      <ul class="sgsi-panel sgsi-subpanel" id="{{ item_id }}">
                        {{ render_menu_items(it["children"], item_id) }}
                      </ul>
                    </li>
                  {% else %}
                    <li>
                      <a class="sgsi-dropdown-item" href="{{ it.get('href', '#') }}">
                        <i class="bi {{ it.get('icon','bi-dot') }}"></i>
                        <span>{{ it["label"] }}</span>
                      </a>
                    </li>
                  {% endif %}
                {% endfor %}
              {% endmacro %}

              {% for sec in sections %}
                {% set sid = "sgsi_root_" ~ loop.index %}

                <div class="sgsi-root-item">
                  <button class="sgsi-leftnav-link sgsi-root-toggle"
                          type="button"
                          data-target="{{ sid }}">
                    <i class="bi {{ sec.get('icon', 'bi-grid-1x2') }}"></i>
                    <span>{{ sec["title"] }}</span>
                  </button>

                  <ul class="sgsi-panel" id="{{ sid }}">
                    {{ render_menu_items(sec["items"], sid) }}
                  </ul>
                </div>
              {% endfor %}

            </div>
          </div>
        </aside>

        <!-- TABLERO -->
        <main class="sgsi-dashboard-zone">

          {% if dashboard_kpis %}
            <section class="sgsi-stats-grid">
              {% for item in dashboard_kpis %}
                <div class="sgsi-stat-card">
                  <div class="sgsi-stat-icon {{ item.color }}">
                    <i class="bi {{ item.icon }}"></i>
                  </div>
                  <div class="sgsi-stat-text">
                    <div class="sgsi-stat-title">{{ item.title }}</div>
                    <div class="sgsi-stat-value {{ item.color }}-text" id="{{ item.element_id }}">
                      {{ item.display_value }}
                    </div>
                    <div class="sgsi-stat-link">{{ item.subtitle }}</div>
                  </div>
                </div>
              {% endfor %}
            </section>
          {% endif %}

          {% if dashboard_charts %}
            <section class="sgsi-dashboard-grid">
              {% for item in dashboard_charts %}
                <div class="sgsi-chart-card">
                  <div class="sgsi-chart-head">
                    <h3>{{ item.title }}</h3>
                    <span>{{ item.display_value }}</span>
                  </div>
                  <div class="sgsi-chart-body">
                    <img id="{{ item.image_id }}"
                         src="data:image/png;base64,{{ item.image }}"
                         class="sgsi-chart-img"
                         alt="{{ item.title }}">
                  </div>
                </div>
              {% endfor %}
            </section>
          {% endif %}

          {% if not dashboard_kpis and not dashboard_charts %}
            <section class="sgsi-dashboard-empty">
              <div class="sgsi-dashboard-empty-icon"><i class="bi bi-layout-wtf"></i></div>
              <h3>Tu Centro de Control no tiene elementos seleccionados</h3>
              <p>Ingresa al diseñador, selecciona una fuente de datos y elige cómo presentarla.</p>
              <a href="{{ url_for('dashboard_config') }}" class="btn btn-primary rounded-pill px-4 fw-bold">
                Construir Centro de Control
              </a>
            </section>
          {% endif %}

        </main>
      </div>
    </div>

    <style>
      :root{
        --sgsi-sidebar-w:245px;
        --sgsi-card:#ffffff;
        --sgsi-purple:#074883;
        --sgsi-purple-2:#1d5fae;
        --sgsi-lav:#dcecff;
        --sgsi-lav-2:#c9e3ff;
        --sgsi-border:#a9cdeb;
        --sgsi-text:#0f3766;
        --sgsi-muted:#425f7f;
      }

      .soa-shell{
        width:100%;
        margin:0 0 34px 0;
      }

      .sgsi-layout{
        display:grid;
        grid-template-columns:var(--sgsi-sidebar-w) minmax(0,1fr);
        gap:16px;
        align-items:start;
        transition:all .22s ease;
      }

      .sgsi-leftnav-wrap{
        position:sticky;
        top:var(--arky-topbar-h, 86px);
        align-self:start;
        z-index:30;
      }

      .sgsi-leftnav-card{
        background:linear-gradient(180deg,rgba(238,247,255,.97) 0%,rgba(213,234,255,.95) 48%,rgba(198,222,245,.94) 100%);
        border:1px solid var(--sgsi-border);
        border-radius:0 18px 18px 0;
        box-shadow:10px 0 30px rgba(28,91,160,.18), inset -1px 0 rgba(255,255,255,.65);
        padding:8px 7px;
        max-height:calc(100vh - var(--arky-topbar-h, 86px)) !important;
        overflow-y:auto !important;
        overflow-x:hidden !important;
        backdrop-filter:blur(14px);
        -webkit-backdrop-filter:blur(14px);
      }

      .sgsi-leftnav-card::-webkit-scrollbar{ width:7px; }
      .sgsi-leftnav-card::-webkit-scrollbar-thumb{ background:#b8a3d8; border-radius:999px; }
      .sgsi-leftnav-card::-webkit-scrollbar-track{ background:#eef4ff; border-radius:999px; }

      .sgsi-leftnav-header{
        display:flex;
        align-items:center;
        gap:10px;
        padding:10px 10px 14px;
        border-bottom:1px solid var(--sgsi-border);
        margin-bottom:12px;
      }

      .sgsi-leftnav-header-icon{
        width:40px;
        height:40px;
        border-radius:14px;
        display:flex;
        align-items:center;
        justify-content:center;
        background:linear-gradient(135deg,var(--sgsi-purple),var(--sgsi-purple-2));
        color:#fff;
        box-shadow:0 10px 22px rgba(75,11,130,.22);
        flex:0 0 auto;
      }

      .sgsi-leftnav-title{
        font-size:.94rem;
        font-weight:950;
        color:var(--sgsi-text);
        line-height:1.1;
      }

      .sgsi-leftnav-subtitle{
        margin-top:3px;
        font-size:.72rem;
        color:var(--sgsi-muted);
        font-weight:750;
        line-height:1.2;
      }

      .sgsi-leftnav-list{
        display:flex;
        flex-direction:column;
        gap:7px;
      }

      .sgsi-leftnav-link{
        width:100%;
        display:flex !important;
        align-items:center;
        justify-content:flex-start;
        gap:7px;
        border:1px solid transparent !important;
        border-radius:14px !important;
        background:transparent !important;
        color:#26384f !important;
        padding:8px 9px !important;
        font-size:.72rem !important;
        font-weight:850 !important;
        white-space:normal !important;
        text-align:left;
        line-height:1.15 !important;
        min-height:36px !important;
        text-decoration:none !important;
        transition:all .18s ease;
      }

      .sgsi-leftnav-link:hover,
      .sgsi-leftnav-link.sgsi-active{
        background:var(--sgsi-lav) !important;
        color:var(--sgsi-purple) !important;
        border-color:var(--sgsi-border) !important;
      }

      .sgsi-panel-control-btn{
        background:linear-gradient(135deg,var(--sgsi-purple) 0%,#1d5fae 58%,#3f8fd6 100%) !important;
        color:#ffffff !important;
        border:1px solid rgba(255,255,255,.40) !important;
        box-shadow:0 12px 26px rgba(75,11,130,.24) !important;
      }

      .sgsi-root-toggle::after,
      .sgsi-node-toggle::after{
        content:"⌄";
        margin-left:auto;
        font-size:13px;
        font-weight:950;
        transition:transform .18s ease;
      }

      .sgsi-root-toggle.sgsi-active::after,
      .sgsi-node-toggle.sgsi-active::after{
        transform:rotate(180deg);
      }

      .sgsi-panel{
        display:none;
        list-style:none;
        margin:6px 0 0 0 !important;
        padding:6px 0 6px 9px !important;
        background:var(--sgsi-lav) !important;
        border:1px solid var(--sgsi-border) !important;
        border-radius:15px !important;
        overflow:visible !important;
      }

      .sgsi-panel.sgsi-open{ display:block !important; }

      .sgsi-subpanel{
        margin-left:5px !important;
        padding-left:8px !important;
        border-left:2px solid #a88fd3 !important;
      }

      .sgsi-dropdown-item{
        display:flex;
        align-items:center;
        gap:6px;
        padding:6px 7px;
        border-radius:12px;
        font-size:.68rem;
        font-weight:800;
        color:#26384f !important;
        white-space:normal;
        line-height:1.16;
        text-decoration:none;
        margin:3px 4px;
        background:rgba(241,247,255,.74);
        border:1px solid rgba(181,205,230,.78);
        transition:all .18s ease;
      }

      .sgsi-dropdown-item:hover,
      .sgsi-dropdown-item.sgsi-active{
        background:#ffffff !important;
        color:var(--sgsi-purple) !important;
        box-shadow:0 8px 16px rgba(43,0,79,.08);
      }

      .sgsi-leftnav-arrow{
        position:absolute;
        right:-13px;
        top:22px;
        width:26px;
        height:58px;
        border-radius:999px;
        background:linear-gradient(135deg,var(--sgsi-purple),#1d5fae);
        color:#ffffff;
        display:flex;
        align-items:center;
        justify-content:center;
        cursor:pointer;
        box-shadow:0 10px 22px rgba(43,0,79,.22);
        border:2px solid #fff;
        z-index:20;
      }

      .sgsi-arrow-icon{
        font-size:26px;
        font-weight:950;
        line-height:1;
        position:relative;
        top:-1px;
      }

      body.sgsi-menu-collapsed .sgsi-layout{
        grid-template-columns:0 minmax(0,1fr);
        gap:0;
      }

      body.sgsi-menu-collapsed .sgsi-leftnav-card{
        opacity:0;
        pointer-events:none;
        transform:translateX(-245px);
      }

      body.sgsi-menu-collapsed .sgsi-leftnav-arrow{
        right:-44px;
      }

      body.sgsi-menu-collapsed .sgsi-arrow-icon{ transform:rotate(180deg); }

      .sgsi-dashboard-zone{ min-width:0; overflow:hidden; }

      .sgsi-dashboard-toolbar{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
        margin:0 0 14px;
        padding:10px 14px;
        border:1px solid var(--sgsi-border);
        border-radius:16px;
        background:rgba(248,252,255,.93);
        box-shadow:0 10px 22px rgba(43,0,79,.07);
      }
      .sgsi-dashboard-toolbar-text{font-size:.74rem;font-weight:900;color:#355777;}
      .sgsi-dashboard-config-btn{font-size:.70rem!important;font-weight:900!important;padding:6px 14px!important;}
      .sgsi-dashboard-empty{
        max-width:760px;
        margin:30px auto;
        padding:42px 24px;
        text-align:center;
        background:rgba(248,252,255,.96);
        border:1px solid var(--sgsi-border);
        border-radius:24px;
        box-shadow:0 18px 34px rgba(43,0,79,.10);
      }
      .sgsi-dashboard-empty-icon{width:64px;height:64px;border-radius:20px;margin:0 auto 14px;display:flex;align-items:center;justify-content:center;background:#eaf3ff;color:#0b4a8f;font-size:1.7rem;}
      .sgsi-dashboard-empty h3{font-size:1.05rem;font-weight:950;color:#173a61;margin-bottom:7px;}
      .sgsi-dashboard-empty p{font-size:.78rem;color:#64788e;margin-bottom:18px;}

      .sgsi-stats-grid{
        width:100%;
        max-width:1160px;
        margin:0 auto 20px auto;
        display:grid;
        grid-template-columns:repeat(auto-fit, minmax(230px, 1fr));
        justify-content:center;
        align-items:stretch;
        gap:14px;
      }

      .sgsi-stat-card{
        width:100%;
        min-width:0;
        min-height:104px;
        padding:16px 14px;
        display:flex;
        align-items:center;
        justify-content:center;
        gap:12px;
        background:rgba(248,252,255,.96);
        border:1px solid var(--sgsi-border);
        border-radius:22px;
        box-shadow:0 18px 34px rgba(43,0,79,.10);
        text-align:center;
        overflow:hidden;
        transition:all .20s ease;
      }

      .sgsi-stat-card:hover{ transform:translateY(-3px); box-shadow:0 24px 42px rgba(43,0,79,.14); }

      .sgsi-stat-icon{
        width:48px;
        height:48px;
        min-width:48px;
        flex:0 0 48px;
        border-radius:16px;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.18rem;
      }

      .sgsi-stat-icon.blue{background:#eef4ff;color:#0f56b3;}
      .sgsi-stat-icon.orange{background:#fff3e8;color:#c95508;}
      .sgsi-stat-icon.green{background:#ecfdf3;color:#087c3d;}
      .sgsi-stat-icon.purple{background:#f2eaff;color:#5521a8;}
      .blue-text{color:#0f56b3 !important;} .orange-text{color:#c95508 !important;} .green-text{color:#087c3d !important;} .purple-text{color:#5521a8 !important;}

      .sgsi-stat-text{ min-width:0; flex:1 1 auto; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; overflow:hidden; }
      .sgsi-stat-title{ width:100%; font-size:.72rem; font-weight:950; color:#17263b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
      .sgsi-stat-value{ width:100%; margin-top:3px; font-size:1.25rem; line-height:1.05; font-weight:950; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
      .sgsi-stat-link{ width:100%; margin-top:5px; color:var(--sgsi-muted); font-size:.65rem; font-weight:850; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

      .sgsi-dashboard-grid{ display:grid; grid-template-columns:repeat(12,minmax(0,1fr)); gap:18px; }
      .sgsi-chart-card{ grid-column:span 4; background:rgba(248,252,255,.96); border:1px solid var(--sgsi-border); border-radius:24px; box-shadow:0 18px 34px rgba(43,0,79,.11); min-height:360px; overflow:hidden; }
      .sgsi-chart-head{ padding:16px 18px 10px 18px; display:flex; justify-content:space-between; gap:10px; border-bottom:1px solid var(--sgsi-border); background:linear-gradient(180deg,#fff 0%,#f2f7ff 100%); }
      .sgsi-chart-head h3{ margin:0; font-size:.92rem; font-weight:950; color:#17263b; }
      .sgsi-chart-head span{ font-size:.72rem; font-weight:900; color:var(--sgsi-purple-2); }
      .sgsi-chart-body{ min-height:295px; display:flex; align-items:center; justify-content:center; padding:10px 14px 16px; }
      .sgsi-chart-img{ width:100%; height:295px; object-fit:contain; }

      @media(max-width:1200px){
        .sgsi-layout{ grid-template-columns:1fr; }
        .sgsi-leftnav-wrap{ position:relative; top:auto; }
        .sgsi-leftnav-card{ max-height:560px !important; }
        .sgsi-stats-grid{ max-width:740px; grid-template-columns:repeat(2, minmax(260px, 1fr)); gap:14px; }
        .sgsi-chart-card{ grid-column:span 6; }
      }

      @media(max-width:991px){
        .sgsi-stats-grid{ max-width:340px; grid-template-columns:minmax(260px, 320px); }
        .sgsi-chart-card{ grid-column:span 12; }
      }
    
      /* Compactar menú local de Centro de Control */
      .sgsi-leftnav-card{
        padding:8px 7px !important;
        border-radius:0 16px 16px 0 !important;
      }
      .sgsi-leftnav-link{
        font-size:.70rem !important;
        min-height:35px !important;
        padding:7px 8px !important;
        border-radius:11px !important;
        gap:6px !important;
      }
      .sgsi-dropdown-item{
        font-size:.66rem !important;
        padding:6px 7px !important;
        border-radius:10px !important;
        gap:6px !important;
      }
      .sgsi-panel{
        margin-top:4px !important;
        padding:4px 0 4px 6px !important;
        border-radius:12px !important;
      }
      .sgsi-leftnav-arrow{
        top:16px !important;
        width:22px !important;
        height:50px !important;
      }

</style>

    <script>
      function sgsiTogglePanel(trigger){
        const id = trigger.getAttribute("data-target");
        const panel = id ? document.getElementById(id) : null;
        if(!panel) return;

        const isOpen = panel.classList.contains("sgsi-open");

        if(isOpen){
          panel.classList.remove("sgsi-open");
          trigger.classList.remove("sgsi-active");
        }else{
          panel.classList.add("sgsi-open");
          trigger.classList.add("sgsi-active");
        }
      }

      document.addEventListener("click", function(e){
        const trigger = e.target.closest(".sgsi-root-toggle, .sgsi-node-toggle");

        if(trigger){
          e.preventDefault();
          e.stopPropagation();
          sgsiTogglePanel(trigger);
          return;
        }

        const menuToggle = e.target.closest("#sgsiLocalMenuToggle");

        if(menuToggle){
          e.preventDefault();
          document.body.classList.toggle("sgsi-menu-collapsed");
        }
      });
    </script>
    """,
    sections=sections,
    dashboard=dashboard,
    dashboard_kpis=dashboard_kpis,
    dashboard_charts=dashboard_charts,
    selected_widget_keys=selected_widget_keys)

    return render_template_string(
        BASE,
        content=content,
        current_user=usuario_actual
    )

# ============================================================================================================================================
#                                                               Fin del Menu Principal
# ============================================================================================================================================


# ============================================================================================================================================
#                                                               Módulo de Áreas de la Empresa
# ============================================================================================================================================




# =========================
# Areas - area
# =========================

@app.route('/areas_area', methods=['GET', 'POST'])
@login_required
def areas_area():
    user = User.query.filter_by(username=session['username']).first()

    if user.role == 'auditor':
        flash("El auditor solo puede consultar información.", "warning")
        return redirect(url_for('areas'))

    # Crear / Editar Área
    if request.method == 'POST':
        rid = request.form.get('id', type=int)

        area = (request.form.get('area') or "").strip()
        responsable_nombre = (request.form.get('responsable_nombre') or "").strip()
        responsable_cargo = (request.form.get('responsable_cargo') or "").strip()

        if not all([area, responsable_nombre, responsable_cargo]):
            flash("Todos los campos del área son obligatorios.", "danger")
            return redirect(url_for('areas_area'))

        if rid:
            item = AreaEmpresa.query.get(rid)
            if not item:
                flash("Área no encontrada.", "danger")
                return redirect(url_for('areas_area'))
        else:
            item = AreaEmpresa()

        item.area = area
        item.responsable_nombre = responsable_nombre
        item.responsable_cargo = responsable_cargo

        db.session.add(item)
        db.session.commit()
        flash("Área guardada correctamente.", "success")
        return redirect(url_for('areas_area'))

    # GET
    edit_id = request.args.get('edit', type=int)
    edit_item = AreaEmpresa.query.get(edit_id) if edit_id else None
    items = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()

    html = """
    <div class="areas-shell">

      <!-- CABECERA -->
      <div class="areas-header-card">
        <div class="areas-header-overlay">
          <div class="areas-header-text">
            <h3 class="areas-title m-0">Áreas de la Empresa</h3>
            <div class="areas-subtitle">
              Administra las áreas organizacionales y asigna el responsable
              principal de cada una junto con su cargo.
            </div>
          </div>
        </div>
      </div>


      <!-- FORMULARIO -->
      <div class="areas-card p-4 mb-3">
        <div class="areas-section-title">
          {% if edit_item %}Editar área{% else %}Registrar nueva área{% endif %}
        </div>

        <form method="post" action="{{ url_for('areas_area') }}">
          {% if edit_item %}
            <input type="hidden" name="id" value="{{ edit_item.id }}">
          {% endif %}

          <div class="row g-3">

            <div class="col-md-4">
              <label class="form-label">Área</label>
              <input type="text"
                     name="area"
                     class="form-control"
                     required
                     value="{{ edit_item.area if edit_item else '' }}">
            </div>

            <div class="col-md-4">
              <label class="form-label">Nombre responsable del área</label>
              <input type="text"
                     name="responsable_nombre"
                     class="form-control"
                     required
                     value="{{ edit_item.responsable_nombre if edit_item else '' }}">
            </div>

            <div class="col-md-4">
              <label class="form-label">Cargo (Responsable de área)</label>
              <input type="text"
                     name="responsable_cargo"
                     class="form-control"
                     required
                     value="{{ edit_item.responsable_cargo if edit_item else '' }}">
            </div>

          </div>

          <div class="mt-4 d-flex justify-content-center gap-2">
            <button type="submit" class="btn btn-success rounded-pill px-4">
              {% if edit_item %}Guardar cambios{% else %}Agregar área{% endif %}
            </button>

            {% if edit_item %}
              <a href="{{ url_for('areas_area') }}"
                 class="btn btn-outline-secondary rounded-pill px-4">
                Cancelar
              </a>
            {% endif %}
          </div>
        </form>
      </div>

      <!-- TABLA -->
      <div class="areas-card p-3">
        <div class="areas-section-title">
          Listado de áreas registradas
        </div>

        <div class="table-responsive areas-table-wrap">
          <table class="table table-bordered table-sm align-middle mb-0">
            <thead class="areas-table-head">
              <tr class="text-center">
                <th>Área</th>
                <th>Responsable del área</th>
                <th>Cargo (Resp.)</th>
                <th style="width:16%; min-width:170px;">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {% for it in items %}
              <tr>
                <td><b>{{ it.area }}</b></td>
                <td>{{ it.responsable_nombre }}</td>
                <td>{{ it.responsable_cargo }}</td>
                <td class="text-center">
                  <a href="{{ url_for('areas_area', edit=it.id) }}"
                     class="btn btn-warning btn-sm rounded-pill px-3">
                    Editar
                  </a>

                  <a href="{{ url_for('areas_delete', id=it.id) }}"
                     class="btn btn-danger btn-sm rounded-pill px-3"
                     onclick="return confirm('¿Eliminar este registro?');">
                    Eliminar
                  </a>
                </td>
              </tr>
              {% endfor %}

              {% if items|length == 0 %}
                <tr>
                  <td colspan="4" class="text-center text-muted">
                    Sin registros
                  </td>
                </tr>
              {% endif %}
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

      .areas-shell{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .areas-header-card{
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

      .areas-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .areas-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }

      .areas-header-overlay::before{
        content:"📦";
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

      .areas-header-text{
        max-width:1000px;
        min-width:0;
      }

      .areas-header-text::before{
        content:"SGSI · Gestión de Áreas";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .areas-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }

      .areas-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }

      .areas-header-actions{
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
        max-width:100%;
      }

      .areas-btn-main{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .areas-btn-main:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      .areas-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .areas-card .card-body{
        padding:22px;
        overflow:hidden;
      }

      .areas-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
        overflow-wrap:break-word;
      }

      .areas-table-wrap{
        border:1px solid #e2ebf5;
        border-radius:14px;
        background:#ffffff;
        overflow-x:auto;
        overflow-y:hidden;
        box-shadow:inset 0 1px 0 rgba(255,255,255,.35);
        width:100%;
        max-width:100%;
      }

      .areas-table-wrap .table{
        margin-bottom:0;
        min-width:780px;
      }

      .areas-table-wrap thead th,
      .areas-table-head th{
        background:#eef5ff !important;
        font-weight:950;
        color:#0b4a8f;
        border-bottom:1px solid #d7dee7 !important;
        vertical-align:middle !important;
        white-space:nowrap;
        font-size:.82rem;
      }

      .areas-table-wrap tbody td{
        vertical-align:middle;
        font-size:.85rem;
        color:#334155;
      }

      .areas-table-wrap tbody tr:last-child td{
        border-bottom:none;
      }

      .areas-table-wrap tbody tr:hover{
        background:#f8fbff;
      }

      .form-control,
      .form-select{
        border-radius:10px;
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

      .input-group-text{
        border-radius:0 10px 10px 0;
        background:#eef5ff;
        border-color:#d9e3f0;
        color:#0b4a8f;
        font-weight:900;
      }

      .areas-soft-box{
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
        .areas-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .areas-title{
          font-size:1.20rem;
        }

        .areas-subtitle{
          font-size:.68rem;
        }

        .areas-card .card-body{
          padding:16px;
        }
      }

      @media (max-width:768px){
        .areas-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .areas-header-overlay::before{
          margin:0;
        }

        .areas-title,
        .areas-subtitle{
          text-align:center;
        }

        .areas-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, edit_item=edit_item, items=items)
    return render_template_string(BASE, content=Markup(inner))

# =========================
# División
# =========================

@app.route('/areas_division', methods=['GET', 'POST'])
@login_required
def areas_division():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El auditor solo puede consultar información.", "warning")
        return redirect(url_for('areas'))

    if user.role != 'admin' and not verificar_permiso(user, "Configuración Parámetros de la Empresa"):
        flash("No tiene permiso para gestionar Divisiones.", "danger")
        return redirect(url_for('areas'))
    
    # Crear / Editar División
    if request.method == 'POST':
        rid = request.form.get('id', type=int)

        area_id = request.form.get('area_id', type=int)
        nombre_division = (request.form.get('nombre_division') or "").strip()
        encargado_nombre = (request.form.get('encargado_nombre') or "").strip()
        encargado_cargo = (request.form.get('encargado_cargo') or "").strip()

        if not all([area_id, nombre_division, encargado_nombre, encargado_cargo]):
            flash("Todos los campos de la división son obligatorios.", "danger")
            return redirect(url_for('areas_division'))

        if not AreaEmpresa.query.get(area_id):
            flash("El área seleccionada no existe.", "danger")
            return redirect(url_for('areas_division'))

        if rid:
            div = DivisionEmpresa.query.get(rid)
            if not div:
                flash("División no encontrada.", "danger")
                return redirect(url_for('areas_division'))
        else:
            div = DivisionEmpresa()

        div.area_id = area_id
        div.nombre_division = nombre_division
        div.encargado_nombre = encargado_nombre
        div.encargado_cargo = encargado_cargo

        db.session.add(div)
        db.session.commit()
        flash("División guardada correctamente.", "success")
        return redirect(url_for('areas_division'))

    # GET
    edit_id = request.args.get('edit', type=int)
    edit_item = DivisionEmpresa.query.get(edit_id) if edit_id else None

    areas_list = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()
    divisiones_list = DivisionEmpresa.query.join(AreaEmpresa).order_by(
        AreaEmpresa.area.asc(), DivisionEmpresa.nombre_division.asc()
    ).all()

    html = """
    <div class="divisiones-shell">

      <!-- CABECERA -->
      <div class="divisiones-header-card">
        <div class="divisiones-header-overlay">
          <div class="divisiones-header-text">
            <h3 class="divisiones-title m-0">Divisiones de la Empresa</h3>
            <div class="divisiones-subtitle">
              Administra las divisiones organizacionales, asociándolas a su área
              y definiendo el encargado principal con su respectivo cargo.
            </div>
          </div>
        </div>
      </div>

      <!-- FORMULARIO -->
      <div class="divisiones-card p-4 mb-3">
        <div class="divisiones-section-title">
          {% if edit_item %}Editar división{% else %}Registrar nueva división{% endif %}
        </div>

        <form method="post" action="{{ url_for('areas_division') }}">
          {% if edit_item %}
            <input type="hidden" name="id" value="{{ edit_item.id }}">
          {% endif %}

          <div class="row g-3">

            <div class="col-md-4">
              <label class="form-label">Área</label>
              <select name="area_id" class="form-select" required>
                <option value="">-- Seleccione un área --</option>
                {% for a in areas_list %}
                  <option value="{{ a.id }}"
                    {% if edit_item and edit_item.area_id == a.id %}selected{% endif %}>
                    {{ a.area }}
                  </option>
                {% endfor %}
              </select>
            </div>

            <div class="col-md-4">
              <label class="form-label">Nombre de la división</label>
              <input type="text"
                     name="nombre_division"
                     class="form-control"
                     required
                     value="{{ edit_item.nombre_division if edit_item else '' }}">
            </div>

            <div class="col-md-4">
              <label class="form-label">Nombre del encargado de la división</label>
              <input type="text"
                     name="encargado_nombre"
                     class="form-control"
                     required
                     value="{{ edit_item.encargado_nombre if edit_item else '' }}">
            </div>

            <div class="col-md-4">
              <label class="form-label">Cargo (Encargado de división)</label>
              <input type="text"
                     name="encargado_cargo"
                     class="form-control"
                     required
                     value="{{ edit_item.encargado_cargo if edit_item else '' }}">
            </div>

          </div>

          <div class="mt-4 d-flex justify-content-center gap-2">
            <button type="submit" class="btn btn-success rounded-pill px-4">
              {% if edit_item %}Guardar cambios{% else %}Agregar división{% endif %}
            </button>

            {% if edit_item %}
              <a href="{{ url_for('areas_division') }}"
                 class="btn btn-outline-secondary rounded-pill px-4">
                Cancelar
              </a>
            {% endif %}
          </div>
        </form>
      </div>

      <!-- TABLA -->
      <div class="divisiones-card p-3">
        <div class="divisiones-section-title">
          Listado de divisiones registradas
        </div>

        <div class="table-responsive divisiones-table-wrap">
          <table class="table table-bordered table-sm align-middle mb-0">
            <thead class="divisiones-table-head">
              <tr class="text-center">
                <th>Área</th>
                <th>División</th>
                <th>Encargado</th>
                <th>Cargo (Enc. Div.)</th>
                <th style="width:16%; min-width:170px;">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {% for d in divisiones_list %}
              <tr>
                <td>{{ d.area.area if d.area else '' }}</td>
                <td><b>{{ d.nombre_division }}</b></td>
                <td>{{ d.encargado_nombre }}</td>
                <td>{{ d.encargado_cargo }}</td>
                <td class="text-center">
                  <a href="{{ url_for('areas_division', edit=d.id) }}"
                     class="btn btn-warning btn-sm rounded-pill px-3">
                    Editar
                  </a>

                  <a href="{{ url_for('division_delete', id=d.id) }}"
                     class="btn btn-danger btn-sm rounded-pill px-3"
                     onclick="return confirm('¿Eliminar esta división?');">
                    Eliminar
                  </a>
                </td>
              </tr>
              {% endfor %}

              {% if divisiones_list|length == 0 %}
                <tr>
                  <td colspan="5" class="text-center text-muted">
                    Sin registros
                  </td>
                </tr>
              {% endif %}
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

      .divisiones-shell{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .divisiones-header-card{
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

      .divisiones-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .divisiones-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }

      .divisiones-header-overlay::before{
        content:"🏛️";
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

      .divisiones-header-text{
        max-width:1000px;
        min-width:0;
      }

      .divisiones-header-text::before{
        content:"SGSI · Gestión de Divisiones";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .divisiones-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }

      .divisiones-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }

      .divisiones-header-actions{
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
        max-width:100%;
      }

      .divisiones-btn-main{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .divisiones-btn-main:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      .divisiones-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .divisiones-card .card-body{
        padding:22px;
        overflow:hidden;
      }

      .divisiones-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
        overflow-wrap:break-word;
      }

      .divisiones-table-wrap{
        border:1px solid #e2ebf5;
        border-radius:14px;
        background:#ffffff;
        overflow-x:auto;
        overflow-y:hidden;
        box-shadow:inset 0 1px 0 rgba(255,255,255,.35);
        width:100%;
        max-width:100%;
      }

      .divisiones-table-wrap .table{
        margin-bottom:0;
        min-width:780px;
      }

      .divisiones-table-wrap thead th,
      .divisiones-table-head th{
        background:#eef5ff !important;
        font-weight:950;
        color:#0b4a8f;
        border-bottom:1px solid #d7dee7 !important;
        vertical-align:middle !important;
        white-space:nowrap;
        font-size:.82rem;
      }

      .divisiones-table-wrap tbody td{
        vertical-align:middle;
        font-size:.85rem;
        color:#334155;
      }

      .divisiones-table-wrap tbody tr:last-child td{
        border-bottom:none;
      }

      .divisiones-table-wrap tbody tr:hover{
        background:#f8fbff;
      }

      .form-control,
      .form-select{
        border-radius:10px;
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

      .input-group-text{
        border-radius:0 10px 10px 0;
        background:#eef5ff;
        border-color:#d9e3f0;
        color:#0b4a8f;
        font-weight:900;
      }

      .divisiones-soft-box{
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
        .divisiones-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .divisiones-title{
          font-size:1.20rem;
        }

        .divisiones-subtitle{
          font-size:.68rem;
        }

        .divisiones-card .card-body{
          padding:16px;
        }
      }

      @media (max-width:768px){
        .divisiones-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .divisiones-header-overlay::before{
          margin:0;
        }

        .divisiones-title,
        .divisiones-subtitle{
          text-align:center;
        }

        .divisiones-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        edit_item=edit_item,
        areas_list=areas_list,
        divisiones_list=divisiones_list
    )
    return render_template_string(BASE, content=Markup(inner))


@app.route('/areas/<int:area_id>/info', methods=['GET'])
@login_required
def areas_info(area_id):
    a = AreaEmpresa.query.get_or_404(area_id)
    # OJO: aquí usamos los nombres reales de tu modelo:
    resp  = getattr(a, 'responsable_nombre', '') or ''
    cargo = getattr(a, 'responsable_cargo', '') or ''
    return jsonify({"responsable": resp, "cargo": cargo})

@app.route('/areas/<int:area_id>/divisiones_json')
@login_required
def areas_divisiones_json(area_id):
    divs = (
        DivisionEmpresa.query
        .filter_by(area_id=area_id)
        .order_by(DivisionEmpresa.nombre_division.asc())
        .all()
    )

    return jsonify({
        "divisiones": [
            {
                "id": d.id,
                "nombre": d.nombre_division
            }
            for d in divs
        ]
    })


@app.route('/areas/delete')
@login_required
def areas_delete():
    rid = request.args.get('id', type=int)
    it = AreaEmpresa.query.get(rid)

    if not it:
        flash("Registro no encontrado.", "danger")
        return redirect(url_for('areas'))

    # 🔎 1) Verificar si el área tiene divisiones asociadas
    divisiones_asociadas = DivisionEmpresa.query.filter_by(area_id=it.id).count()

    if divisiones_asociadas > 0:
        flash(
            "No se puede eliminar el área porque tiene una o varias divisiones asociadas. "
            "Elimina primero las divisiones o reasígnalas.",
            "danger"
        )
        return redirect(url_for('areas'))

    # ✅ 2) Si no tiene divisiones, intentar eliminar
    try:
        db.session.delete(it)
        db.session.commit()
        flash("Área eliminada correctamente.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(
            "No se pudo eliminar el área porque está referenciada en otros módulos "
            "(inventarios, proveedores, etc.).",
            "danger"
        )

    return redirect(url_for('areas'))

    # Si no es área con divisiones asociadas (o es una división), se puede eliminar
    db.session.delete(it)
    db.session.commit()
    flash("Eliminado correctamente.", "success")
    return redirect(url_for('areas'))

@app.route('/divisiones/delete')
@login_required
def division_delete():
    rid = request.args.get('id', type=int)
    d = DivisionEmpresa.query.get(rid)
    if d:
        db.session.delete(d)
        db.session.commit()
        flash("División eliminada correctamente.", "success")
    else:
        flash("División no encontrada.", "danger")
    return redirect(url_for('areas_division'))

# =========================
# Configuración de Correo
# =========================

@app.route("/config/email", methods=["GET", "POST"])
@login_required
@admin_or_access_manager_required
def config_email():
    cfg = EmailConfig.query.first()
    if not cfg:
        cfg = EmailConfig()
        db.session.add(cfg)
        db.session.commit()

    if request.method == "POST":
        cfg.smtp_host = (request.form.get("smtp_host") or "smtp.gmail.com").strip()
        cfg.smtp_port = int(request.form.get("smtp_port") or 587)

        cfg.smtp_user = (request.form.get("smtp_user") or "").strip() or None
        cfg.smtp_pass = (request.form.get("smtp_pass") or "").strip() or None

        cfg.smtp_from = (request.form.get("smtp_from") or "").strip() or None
        cfg.app_name  = (request.form.get("app_name")  or "SGSI").strip()

        if not cfg.smtp_from:
            cfg.smtp_from = cfg.smtp_user

        db.session.commit()
        flash("Configuración SMTP guardada correctamente.", "success")

        # ✅ CORREGIDO: antes decía url_for("areas") y ese endpoint no existe
        return redirect(url_for("config_email"))

    inner = render_template_string("""
    <div class="smtp-shell">

      <div class="smtp-header-card">
        <div class="smtp-header-overlay">
          <div class="smtp-header-text">
            <h3 class="smtp-title m-0">Configuración de correo (SMTP)</h3>
            <div class="smtp-subtitle">
              Configura los parámetros del servidor SMTP para el envío de notificaciones,
              alertas y comunicaciones automáticas del sistema.
            </div>
          </div>
        </div>
      </div>

      <div class="smtp-card p-4">
        <div class="smtp-section-title">
          Parámetros de conexión SMTP
        </div>

        <form method="POST" class="row g-3">

          <div class="col-md-6">
            <label class="form-label">SMTP Host</label>
            <input name="smtp_host"
                   class="form-control"
                   value="{{ cfg.smtp_host or 'smtp.gmail.com' }}"
                   required>
          </div>

          <div class="col-md-6">
            <label class="form-label">SMTP Port</label>
            <input name="smtp_port"
                   type="number"
                   class="form-control"
                   value="{{ cfg.smtp_port or 587 }}"
                   required>
          </div>

          <div class="col-md-6">
            <label class="form-label">SMTP User (correo)</label>
            <input name="smtp_user"
                   type="email"
                   class="form-control"
                   value="{{ cfg.smtp_user or '' }}">
            <div class="form-text">Ej: tu-cuenta@gmail.com</div>
          </div>

          <div class="col-md-6">
            <label class="form-label">SMTP Pass (contraseña de app)</label>
            <input name="smtp_pass"
                   type="password"
                   class="form-control"
                   value="{{ cfg.smtp_pass or '' }}">
            <div class="form-text">En Gmail usa “App Password”, no tu clave normal.</div>
          </div>

          <div class="col-md-6">
            <label class="form-label">From (opcional)</label>
            <input name="smtp_from"
                   type="email"
                   class="form-control"
                   value="{{ cfg.smtp_from or '' }}">
            <div class="form-text">Si queda vacío, se usa SMTP User.</div>
          </div>

          <div class="col-md-6">
            <label class="form-label">Nombre de la app</label>
            <input name="app_name"
                   class="form-control"
                   value="{{ cfg.app_name or 'SGSI' }}"
                   required>
          </div>

          <div class="col-12 d-flex justify-content-center mt-3">
            <button class="btn btn-success rounded-pill px-4">
              💾 Guardar
            </button>
          </div>

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

      .smtp-shell{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .smtp-header-card{
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

      .smtp-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .smtp-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }

      .smtp-header-overlay::before{
        content:"✉️";
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

      .smtp-header-text{
        max-width:1000px;
        min-width:0;
      }

      .smtp-header-text::before{
        content:"SGSI · Configuración SMTP";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .smtp-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }

      .smtp-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        max-width:100%;
      }

      .smtp-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .smtp-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
      }

      .form-control,
      .form-select{
        border-radius:10px;
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

      h3{
        color:#ffffff;
        margin:0;
      }

      @media (max-width:992px){
        .smtp-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .smtp-title{
          font-size:1.20rem;
        }

        .smtp-subtitle{
          font-size:.68rem;
        }
      }

      @media (max-width:768px){
        .smtp-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .smtp-header-overlay::before{
          margin:0;
        }

        .smtp-title,
        .smtp-subtitle{
          text-align:center;
        }
      }
    </style>
    """, cfg=cfg)

    return render_template_string(BASE, content=Markup(inner))


# ============================================================================
# CENTRO DE ALERTAS - CONFIGURACIÓN, EVALUACIÓN Y CORREO
# ============================================================================

ALERT_DEFAULT_RULES = [
    {
        "code": "risks_outside_appetite", "name": "Riesgos fuera del apetito",
        "module": "Riesgos", "metric_key": "risks_outside_appetite_inclusive",
        "operator": ">", "threshold": 0, "severity": "alta", "enabled": True,
        "description": "Riesgos activos cuyo nivel residual es mayor o igual al apetito configurado.",
        "url": "/riesgos",
    },
    {
        "code": "vulnerabilities_critical", "name": "Vulnerabilidades críticas abiertas",
        "module": "Vulnerabilidades", "metric_key": "vulnerabilities_critical_count",
        "operator": ">", "threshold": 0, "severity": "crítica", "enabled": True,
        "description": "Vulnerabilidades críticas que permanecen abiertas.",
        "url": "/vulnerabilidades_menu",
    },
    {
        "code": "vulnerabilities_overdue", "name": "Vulnerabilidades abiertas vencidas (fuera de SLA)",
        "module": "Vulnerabilidades", "metric_key": "vulnerabilities_overdue_count",
        "operator": ">", "threshold": 0, "severity": "alta", "enabled": True,
        "description": "Backlog de vulnerabilidades abiertas que superó el SLA configurado por clasificación.",
        "url": "/vulnerabilidades_menu",
    },
    {
        "code": "incidents_open", "name": "Incidentes abiertos",
        "module": "Incidentes", "metric_key": "incidents_open_count",
        "operator": ">", "threshold": 0, "severity": "alta", "enabled": True,
        "description": "Incidentes cuyo estado todavía no está cerrado o resuelto.",
        "url": "/incidentes",
    },
    {
        "code": "incidents_compliance", "name": "Cumplimiento de incidentes inferior a la meta",
        "module": "Incidentes", "metric_key": "incidents_compliance_pct",
        "operator": "<", "threshold": 90, "severity": "media", "enabled": False,
        "description": "Cumplimiento promedio MTCD/MTIR inferior al porcentaje definido en esta regla.",
        "url": "/metricas/incidentes/matriz",
    },
    {
        "code": "plans_overdue", "name": "Planes de acción vencidos",
        "module": "Planes de acción", "metric_key": "plans_overdue_count",
        "operator": ">", "threshold": 0, "severity": "alta", "enabled": True,
        "description": "Planes cuya fecha objetivo venció y todavía no están cerrados.",
        "url": "/planes_accion",
    },
    {
        "code": "legal_noncompliant", "name": "Requisitos legales incumplidos",
        "module": "Requisitos legales", "metric_key": "legal_noncompliant_count",
        "operator": ">", "threshold": 0, "severity": "alta", "enabled": True,
        "description": "Requisitos legales o contractuales registrados como no cumplidos.",
        "url": "/requisitos_menu",
    },
    {
        "code": "providers_high", "name": "Proveedores de criticidad alta",
        "module": "Proveedores", "metric_key": "providers_high_count",
        "operator": ">", "threshold": 0, "severity": "alta", "enabled": True,
        "description": "Proveedores cuya evaluación presenta criticidad alta.",
        "url": "/proveedores_menu",
    },
    {
        "code": "documents_overdue", "name": "Documentos con revisión vencida",
        "module": "Documentación", "metric_key": "documents_overdue_count",
        "operator": ">", "threshold": 0, "severity": "media", "enabled": True,
        "description": "Documentos vigentes que el Listado Maestro clasifica con estado de revisión Vencido.",
        "url": "/docs/matriz?estado_revision=Vencido",
    },
    {
        "code": "documents_due_soon", "name": "Documentos próximos a vencer",
        "module": "Documentación", "metric_key": "documents_due_soon_count",
        "operator": ">", "threshold": 0, "severity": "media", "enabled": True,
        "description": "Documentos vigentes que el Listado Maestro clasifica como Cercano según la periodicidad configurada para su tipo.",
        "url": "/docs/matriz?estado_revision=Cercano",
    },
    {
        "code": "wazuh_high", "name": "Alertas Wazuh altas o críticas",
        "module": "Cumplimiento continuo", "metric_key": "wazuh_high_count",
        "operator": ">", "threshold": 0, "severity": "crítica", "enabled": True,
        "description": "Alertas Wazuh con nivel de regla igual o superior a 10.",
        "url": "/cumplimiento_continuo/wazuh",
    },
    {
        "code": "firewall_critical", "name": "Hallazgos críticos de firewall",
        "module": "Gobierno de Firewall", "metric_key": "firewall_critical_count",
        "operator": ">", "threshold": 0, "severity": "crítica", "enabled": True,
        "description": "Hallazgos críticos activos y todavía no resueltos en Gobierno de Firewall.",
        "url": "/cumplimiento_continuo/firewall",
    },
    {
        "code": "bcp_backups_failed", "name": "Backups fallidos",
        "module": "Continuidad", "metric_key": "bcp_backups_failed_count",
        "operator": ">", "threshold": 0, "severity": "crítica", "enabled": True,
        "description": "Respaldos fallidos registrados en el módulo BCP/DRP.",
        "url": "/bcp/metricas",
    },
    {
        "code": "bcp_systems_without_drp", "name": "Sistemas críticos sin DRP",
        "module": "Continuidad", "metric_key": "bcp_systems_without_drp_count",
        "operator": ">", "threshold": 0, "severity": "alta", "enabled": True,
        "description": "Sistemas o procesos críticos sin cobertura de recuperación documentada.",
        "url": "/bcp/metricas",
    },
    {
        "code": "iso27001_below_target", "name": "Madurez ISO 27001 inferior a la meta",
        "module": "Madurez", "metric_key": "maturity_iso_pct",
        "operator": "<", "threshold": 60, "severity": "media", "enabled": False,
        "description": "Porcentaje de madurez ISO 27001 inferior a la meta definida en la regla.",
        "url": "/madurez",
    },
]

ALERT_RULE_URLS = {item["code"]: item.get("url", "") for item in ALERT_DEFAULT_RULES}
ALERT_OPERATORS = {">", ">=", "=", "<", "<="}
ALERT_SEVERITIES = {"informativa", "baja", "media", "alta", "crítica"}


def alert_get_config():
    cfg = AlertConfig.query.first()
    if not cfg:
        cfg = AlertConfig()
        db.session.add(cfg)
        db.session.commit()
    return cfg


def alert_seed_defaults():
    """Crea solo las reglas faltantes y conserva toda personalización existente."""
    existing = {row.code for row in AlertRule.query.all()}
    created = 0
    for item in ALERT_DEFAULT_RULES:
        if item["code"] in existing:
            continue
        db.session.add(AlertRule(
            code=item["code"], name=item["name"], module=item["module"],
            description=item["description"], metric_key=item["metric_key"],
            operator=item["operator"], threshold=float(item["threshold"]),
            severity=item["severity"], enabled=bool(item["enabled"]),
            email_enabled=True, repeat_minutes=1440,
        ))
        created += 1
    if created:
        db.session.commit()
    alert_get_config()
    return created


def alert_parse_recipients(raw):
    values = re.split(r"[;,\n\r]+", str(raw or ""))
    valid, invalid = [], []
    pattern = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    for value in values:
        email = value.strip().lower()
        if not email:
            continue
        if pattern.match(email):
            if email not in valid:
                valid.append(email)
        else:
            invalid.append(email)
    return valid, invalid


def alert_compare(value, operator, threshold):
    value = float(value or 0)
    threshold = float(threshold or 0)
    return {
        ">": value > threshold,
        ">=": value >= threshold,
        "=": value == threshold,
        "<": value < threshold,
        "<=": value <= threshold,
    }.get(operator, False)


def alert_plain(value):
    text_value = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    return "".join(ch for ch in text_value if not unicodedata.combining(ch))


def alert_vulnerabilities_overdue_count():
    config = MetricasVulnerabilidadesConfig.query.first()
    if not config:
        return 0.0
    sla_by_level = {}
    for row in (config.clasificaciones or []):
        days = getattr(row, "tiempo_max_cierre_dias", None)
        if days is not None and int(days) >= 0:
            sla_by_level[alert_plain(row.clasificacion)] = int(days)
    if not sla_by_level:
        return 0.0
    today = date.today()
    total = 0
    for item in VulnerabilidadRegistro.query.all():
        status = alert_plain(getattr(item, "estado", ""))
        if status in {"cerrado", "cerrada", "closed", "resuelto", "resuelta"}:
            continue
        identified = getattr(item, "fecha_identificacion", None)
        if isinstance(identified, datetime):
            identified = identified.date()
        if not identified:
            continue
        level = alert_plain(getattr(item, "clasificacion", ""))
        sla_days = sla_by_level.get(level)
        if sla_days is None:
            for configured_level, configured_days in sla_by_level.items():
                if configured_level in level or level in configured_level:
                    sla_days = configured_days
                    break
        if sla_days is not None and identified + datetime_module.timedelta(days=sla_days) < today:
            total += 1
    return float(total)


def alert_documents_by_review_status(status_text):
    """Devuelve los documentos con el mismo estado mostrado en el Listado Maestro."""
    expected = alert_plain(status_text)
    matches = []
    for document in DocMaestroDocumento.query.all():
        # Una versión obsoleta no debe generar alertas de revisión o vigencia.
        if "obsolet" in alert_plain(getattr(document, "estado", "")):
            continue
        try:
            review_status = calcular_estado_revision(document, getattr(document, "tipo", None)) or {}
            current = alert_plain(review_status.get("texto", ""))
        except Exception:
            current = ""
        if current == expected:
            matches.append(document)
    return matches


def alert_documents_overdue_count():
    return float(len(alert_documents_by_review_status("Vencido")))


def alert_documents_due_soon_count():
    return float(len(alert_documents_by_review_status("Cercano")))


def alert_documents_message(metric_key, value):
    """Construye un mensaje identificable para la alerta en pantalla y por correo."""
    if metric_key == "documents_overdue_count":
        status_text = "Vencido"
        summary_text = "con revisión vencida"
    elif metric_key == "documents_due_soon_count":
        status_text = "Cercano"
        summary_text = "próximos a vencer"
    else:
        return None

    documents = alert_documents_by_review_status(status_text)
    labels = []
    for document in documents[:10]:
        code = (getattr(document, "codigo", "") or "").strip()
        name = (getattr(document, "nombre_documento", "") or "Documento sin nombre").strip()
        labels.append(f"{code} - {name}" if code else name)
    detail = "; ".join(labels)
    if len(documents) > 10:
        detail += f"; y {len(documents) - 10} documento(s) adicional(es)"
    base = f"Se detectaron {alert_format_number(value)} documento(s) {summary_text} en el Listado Maestro."
    return f"{base} Documentos: {detail}." if detail else base


