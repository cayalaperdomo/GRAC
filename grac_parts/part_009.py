@app.route('/vulnerabilidades_matriz')
@login_required
def vulnerabilidades_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
            flash("No tiene permiso para ver la matriz de vulnerabilidades.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    # ==========================
    # Filtros
    # ==========================
    filtro_campo = (request.args.get('campo') or 'activo').strip()
    filtro_valor = (request.args.get('valor') or '').strip()
    filtro_clasificacion = (request.args.get('clasificacion') or '').strip()

    campos_validos = {
        'codigo',
        'activo',
        'cve',
        'clasificacion',
        'responsable',
        'estado',
        'tipo_vulnerabilidad'
    }

    if filtro_campo not in campos_validos:
        filtro_campo = 'activo'

    q = VulnerabilidadRegistro.query.options(
        selectinload(VulnerabilidadRegistro.evidencias)
    )

    if filtro_valor:
        columna = getattr(VulnerabilidadRegistro, filtro_campo, None)
        if columna is not None:
            q = q.filter(columna.ilike(f"%{filtro_valor}%"))

    if filtro_clasificacion:
        q = q.filter(VulnerabilidadRegistro.clasificacion == filtro_clasificacion)

    items = q.order_by(VulnerabilidadRegistro.id.desc()).all()

    html = """
    <div class="vulnmx-shell">

      <!-- CABECERA -->
      <div class="plan-hero">
        <h2 class="plan-title">Registro de Vulnerabilidades</h2>
      </div>

      <!-- BOTONERA SUPERIOR -->
      <div class="volver-center">
        <div class="top-actions-wrap">

          {% if not read_only %}
            <a href="{{ url_for('vulnerabilidad_new') }}"
               class="btn btn-primary rounded-pill px-4 fw-semibold"
               onclick="showLoader()">
              Agregar vulnerabilidad
            </a>
          {% else %}
            <button class="btn btn-secondary rounded-pill px-4 fw-semibold"
                    disabled
                    title="Auditor: solo lectura">
              Agregar vulnerabilidad
            </button>
          {% endif %}

          <!-- DESPLEGABLE KALI PROFESIONAL -->
          <div class="kali-dropdown-wrap">
            <button type="button"
                    class="btn kali-main-btn rounded-pill px-4 fw-semibold"
                    onclick="toggleKaliMenu(event)">
              Kali Linux
              <span class="kali-caret">▾</span>
            </button>

            <div id="kaliVerticalDropdown" class="kali-vertical-dropdown">
              <div class="kali-menu-header">Escaneo con Kali Linux</div>

              {% if not read_only %}
                <a href="{{ url_for('vuln_scan_new') }}"
                   class="kali-menu-item"
                   onclick="showLoader()">
                  Nuevo escaneo
                </a>
              {% else %}
                <button class="kali-menu-item kali-menu-item-disabled"
                        disabled
                        title="Auditor: solo lectura">
                  Nuevo escaneo
                </button>
              {% endif %}

              <a href="{{ url_for('vuln_scan_runs') }}"
                 class="kali-menu-item"
                 onclick="showLoader()">
                Reportes de escaneo
              </a>

              {% if not read_only %}
                <a href="{{ url_for('vuln_scan_config') }}"
                   class="kali-menu-item"
                   onclick="showLoader()">
                  Configuración Kali
                </a>
              {% else %}
                <button class="kali-menu-item kali-menu-item-disabled"
                        disabled
                        title="Auditor: solo lectura">
                  Configuración Kali
                </button>
              {% endif %}
            </div>
          </div>

          <a href="{{ url_for('sast_index') }}"
             class="btn btn-primary rounded-pill px-4 fw-semibold"
             onclick="showLoader()">
            Pruebas SAST
          </a>

        </div>
      </div>

      <!-- TARJETA PRINCIPAL -->
      <div class="vulnmx-card">
        <div class="vulnmx-card-body">

          <!-- FILTROS -->
          <form method="get" class="row g-3 mb-3" id="vulnFiltroForm">
            <div class="col-md-3">
              <label class="form-label fw-bold">Campo</label>
              <select name="campo" class="form-select">
                <option value="activo" {{ 'selected' if filtro_campo == 'activo' else '' }}>Activo</option>
                <option value="codigo" {{ 'selected' if filtro_campo == 'codigo' else '' }}>Código</option>
                <option value="cve" {{ 'selected' if filtro_campo == 'cve' else '' }}>CVE</option>
                <option value="responsable" {{ 'selected' if filtro_campo == 'responsable' else '' }}>Responsable</option>
                <option value="estado" {{ 'selected' if filtro_campo == 'estado' else '' }}>Estado</option>
                <option value="tipo_vulnerabilidad" {{ 'selected' if filtro_campo == 'tipo_vulnerabilidad' else '' }}>Tipo de vulnerabilidad</option>
              </select>
            </div>

            <div class="col-md-4">
              <label class="form-label fw-bold">Buscar</label>
              <input type="text"
                     name="valor"
                     value="{{ filtro_valor }}"
                     class="form-control"
                     placeholder="Digite el valor a buscar">
            </div>

            <div class="col-md-3">
              <label class="form-label fw-bold">Clasificación</label>
              <select name="clasificacion" class="form-select">
                <option value="">-- Todas --</option>
                {% for op in clasif_choices %}
                  <option value="{{ op }}" {{ 'selected' if filtro_clasificacion == op else '' }}>
                    {{ op }}
                  </option>
                {% endfor %}
              </select>
            </div>

            <div class="col-md-2 d-flex align-items-end gap-2 flex-wrap vuln-filter-actions">
              <button class="btn btn-primary rounded-pill" type="submit">
                Filtrar
              </button>

              <a href="{{ url_for('vulnerabilidades_matriz') }}"
                 class="btn btn-secondary rounded-pill">
                Limpiar
              </a>

              {% if not read_only %}
                <button type="button"
                        class="btn btn-danger rounded-pill"
                        onclick="eliminarVulnerabilidadesFiltradas()">
                  Eliminar filtrados
                </button>
              {% else %}
                <button type="button"
                        class="btn btn-secondary rounded-pill"
                        disabled
                        title="Auditor: solo lectura">
                  Eliminar filtrados
                </button>
              {% endif %}
            </div>
          </form>

          <form method="post"
                id="vulnDeleteFiltradosForm"
                action="{{ url_for('vulnerabilidades_delete_filtrados') }}"
                style="display:none;">
            <input type="hidden" name="campo" value="{{ filtro_campo }}">
            <input type="hidden" name="valor" value="{{ filtro_valor }}">
            <input type="hidden" name="clasificacion" value="{{ filtro_clasificacion }}">
          </form>

          <!-- TABLA -->
          <div class="table-responsive">
            <table class="table table-hover align-middle vuln-table">

              <colgroup>
                <col style="width:6%;">
                <col style="width:11%;">
                <col style="width:14%;">
                <col style="width:34%;">
                <col style="width:12%;">
                <col style="width:11%;">
                <col style="width:8%;">
                <col style="width:14%;">
              </colgroup>

              <thead class="table-dark">
                <tr>
                  <th>ID</th>
                  <th>Código</th>
                  <th>Activo</th>
                  <th>Descripción</th>
                  <th>Clasificación</th>
                  <th>Responsable</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>

              <tbody>
                {% for it in items %}
                <tr>
                  <td>{{ it.id }}</td>
                  <td>{{ it.codigo or '' }}</td>
                  <td>{{ it.activo or '' }}</td>
                  <td class="desc-cell">{{ it.descripcion_vulnerabilidad or '' }}</td>
                  <td>{{ it.clasificacion or '' }}</td>
                  <td>{{ it.responsable or '' }}</td>
                  <td>{{ it.estado or '' }}</td>

                  <td class="text-nowrap">
                    <div class="acciones-wrap">

                      <a href="{{ url_for('vulnerabilidad_detalle', id=it.id) }}"
                         class="btn btn-sm btn-info text-white rounded-pill">
                        Ver detalle
                      </a>

                      {% if not read_only %}
                        <a href="{{ url_for('vulnerabilidad_delete', id=it.id) }}"
                           class="btn btn-sm btn-danger rounded-pill"
                           onclick="return confirmarEliminarVulnerabilidad();">
                          Eliminar
                        </a>
                      {% else %}
                        <button class="btn btn-sm btn-secondary rounded-pill"
                                disabled
                                title="Auditor: solo lectura">
                          Eliminar
                        </button>
                      {% endif %}

                    </div>
                  </td>
                </tr>

                {% else %}
                <tr>
                  <td colspan="8" class="text-center text-muted py-4">
                    No se encontraron registros.
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

      .vulnmx-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
        overflow:visible;
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
        content:"SGSI · Matriz de Vulnerabilidades";
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

      .top-actions-wrap{
        width:100%;
        display:flex;
        flex-wrap:wrap;
        gap:10px;
        justify-content:center;
        align-items:flex-start;
        overflow:visible;
      }

      .volver-center .btn,
      .top-actions-wrap .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
        max-width:100%;
      }

      .volver-center .btn-secondary,
      .volver-center .btn-outline-secondary,
      .kali-main-btn{
        background:#ffffff !important;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }

      .volver-center .btn-secondary:hover,
      .volver-center .btn-outline-secondary:hover,
      .kali-main-btn:hover{
        background:#edf5ff !important;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }

      .kali-dropdown-wrap{
        position:relative;
        display:flex;
        flex-direction:column;
        align-items:center;
        overflow:visible;
        z-index:20;
      }

      .kali-caret{
        margin-left:6px;
        font-size:.86rem;
        opacity:.75;
      }

      .kali-vertical-dropdown{
        display:none;
        position:absolute;
        top:100%;
        left:50%;
        transform:translateX(-50%);
        margin-top:8px;
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:14px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        padding:8px;
        z-index:30;
        min-width:240px;
        flex-direction:column;
        align-items:stretch;
        gap:4px;
      }

      .kali-vertical-dropdown.show{
        display:flex;
      }

      .kali-menu-header{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        letter-spacing:.04em;
        padding:7px 10px 8px 10px;
        border-bottom:1px solid #eef2f7;
        margin-bottom:4px;
      }

      .kali-menu-item{
        display:block;
        width:100%;
        text-decoration:none;
        text-align:left;
        background:transparent;
        color:#101827;
        border:none;
        border-radius:10px;
        padding:9px 12px;
        font-size:.80rem;
        font-weight:800;
        transition:all .18s ease;
        white-space:nowrap;
      }

      .kali-menu-item:hover{
        background:#eef5ff;
        color:#0b4a8f;
      }

      .kali-menu-item-disabled{
        color:#9ca3af !important;
        cursor:not-allowed;
      }

      .kali-menu-item-disabled:hover{
        background:transparent !important;
      }

      .vulnmx-card{
        background:rgba(255,255,255,.96);
        backdrop-filter:blur(8px);
        border:1px solid rgba(219,230,244,.9);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .vulnmx-card-body{
        padding:18px;
        overflow:hidden;
      }

      .form-label{
        color:#25324a;
        margin-bottom:4px;
        font-weight:900;
        font-size:.78rem;
      }

      .form-control,
      .form-select{
        border-radius:10px;
        min-height:40px;
        border:1px solid #d9e3f0;
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

      .vuln-filter-actions .btn{
        width:100%;
        min-height:32px;
        padding:7px 12px !important;
        font-size:.68rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.12);
      }

      .table-responsive{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
        width:100%;
        max-width:100%;
      }

      .vuln-table{
        min-width:1180px;
        table-layout:fixed;
        margin-bottom:0;
        background:#ffffff;
      }

      .vuln-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        vertical-align:middle;
        white-space:normal;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        border-color:rgba(0,0,0,.08) !important;
        text-align:center;
        font-size:.78rem;
        padding:9px 8px;
      }

      .vuln-table th,
      .vuln-table td{
        vertical-align:top;
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal;
        word-break:normal;
        overflow-wrap:break-word;
      }

      .vuln-table td{
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }

      .desc-cell{
        min-width:360px;
        line-height:1.45;
        text-align:left;
      }

      .vuln-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .vuln-table tbody tr:hover{
        background:#eef6ff;
      }

      .acciones-wrap{
        display:flex;
        gap:6px;
        flex-wrap:wrap;
        justify-content:center;
        align-items:center;
      }

      .acciones-wrap .btn{
        font-size:.72rem;
        font-weight:900;
        padding:5px 10px;
        white-space:nowrap;
      }

      .table-responsive::-webkit-scrollbar{
        height:11px;
        width:11px;
      }

      .table-responsive::-webkit-scrollbar-track{
        background:#dbe4f0;
        border-radius:12px;
      }

      .table-responsive::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,#5aa3ea 0%,#3f86d6 100%);
        border-radius:12px;
        border:2px solid #dbe4f0;
      }

      .table-responsive{
        scrollbar-width:thin;
        scrollbar-color:#3f86d6 #dbe4f0;
      }

      h3{
        color:#ffffff;
        margin:0;
      }

      @media (max-width:992px){
        .vulnmx-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .plan-hero{
          min-height:88px;
        }

        .plan-title{
          font-size:1.20rem;
        }

        .vulnmx-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
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

        .top-actions-wrap{
          flex-direction:column;
          align-items:stretch;
        }

        .top-actions-wrap .btn,
        .volver-center .btn{
          width:100%;
        }

        .kali-dropdown-wrap{
          width:100%;
        }

        .kali-main-btn{
          width:100%;
        }

        .kali-vertical-dropdown{
          position:static;
          left:auto;
          top:auto;
          transform:none;
          width:100%;
          min-width:100%;
          margin-top:10px;
        }

        .acciones-wrap{
          flex-direction:column;
          align-items:stretch;
        }

        .acciones-wrap .btn{
          width:100%;
        }
      }
    </style>

    <script>
      function toggleKaliMenu(event){
        event.stopPropagation();

        const menu = document.getElementById('kaliVerticalDropdown');
        if(!menu) return;

        menu.classList.toggle('show');
      }

      document.addEventListener('click', function(e){
        const wrap = document.querySelector('.kali-dropdown-wrap');
        const menu = document.getElementById('kaliVerticalDropdown');

        if(!wrap || !menu) return;

        if(!wrap.contains(e.target)){
          menu.classList.remove('show');
        }
      });

      function confirmarEliminarVulnerabilidad(){
        if(typeof hideLoader === 'function'){
          hideLoader();
        }

        return confirm(
          '¿Está seguro de eliminar esta vulnerabilidad?\\n\\n' +
          'También se eliminarán sus evidencias asociadas.\\n' +
          'Esta acción no se puede deshacer.'
        );
      }

      function eliminarVulnerabilidadesFiltradas(){
        const total = {{ items|length }};

        if(total <= 0){
          alert('No hay registros para eliminar con los filtros aplicados.');
          return false;
        }

        const campo = "{{ filtro_campo }}";
        const valor = "{{ filtro_valor }}";
        const clasificacion = "{{ filtro_clasificacion }}";

        let mensaje = '¿Está seguro de eliminar las vulnerabilidades filtradas?\\n\\n';
        mensaje += 'Total registros a eliminar: ' + total + '\\n';

        if(campo && valor){
          mensaje += 'Filtro: ' + campo + ' contiene "' + valor + '"\\n';
        }

        if(clasificacion){
          mensaje += 'Clasificación: ' + clasificacion + '\\n';
        }

        if(!valor && !clasificacion){
          mensaje += '\\nADVERTENCIA: No hay filtros aplicados. Se eliminarán TODAS las vulnerabilidades.\\n';
        }

        mensaje += '\\nTambién se eliminarán evidencias y planes asociados.\\n';
        mensaje += 'Esta acción no se puede deshacer.';

        if(confirm(mensaje)){
          const form = document.getElementById('vulnDeleteFiltradosForm');
          if(form){
            form.submit();
          }
        }

        return false;
      }

      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          document.addEventListener('DOMContentLoaded', function(){
            let stack = document.getElementById('sgsiFlashStack');

            if(!stack){
              stack = document.createElement('div');
              stack.id = 'sgsiFlashStack';
              stack.style.position = 'fixed';
              stack.style.top = '92px';
              stack.style.right = '24px';
              stack.style.zIndex = '999998';
              stack.style.display = 'flex';
              stack.style.flexDirection = 'column';
              stack.style.gap = '10px';
              stack.style.maxWidth = '440px';
              document.body.appendChild(stack);
            }

            const palette = {
              success: ['#ecfdf5', '#087c3d', '#14532d', '✅'],
              warning: ['#fffbeb', '#c76b00', '#78350f', '⚠️'],
              danger:  ['#fef2f2', '#b91c1c', '#7f1d1d', '⛔'],
              info:    ['#eff6ff', '#3f86d6', '#1e3a8a', 'ℹ️']
            };

            {% for category, message in messages %}
              (function(){
                const cfg = palette[{{ category|tojson }}] || palette.info;

                const box = document.createElement('div');
                box.style.background = cfg[0];
                box.style.borderLeft = '6px solid ' + cfg[1];
                box.style.color = cfg[2];
                box.style.borderRadius = '16px';
                box.style.padding = '14px 16px';
                box.style.boxShadow = '0 14px 34px rgba(0,0,0,.22)';
                box.style.fontWeight = '800';
                box.style.fontSize = '.88rem';
                box.style.lineHeight = '1.35';
                box.style.display = 'flex';
                box.style.alignItems = 'flex-start';
                box.style.gap = '10px';

                const icon = document.createElement('div');
                icon.textContent = cfg[3];
                icon.style.fontSize = '1.05rem';

                const text = document.createElement('div');
                text.textContent = {{ message|tojson }};

                const close = document.createElement('button');
                close.type = 'button';
                close.textContent = '×';
                close.style.marginLeft = 'auto';
                close.style.border = '0';
                close.style.background = 'transparent';
                close.style.color = cfg[2];
                close.style.fontSize = '1.2rem';
                close.style.fontWeight = '900';
                close.style.lineHeight = '1';
                close.onclick = function(){
                  box.remove();
                };

                box.appendChild(icon);
                box.appendChild(text);
                box.appendChild(close);
                stack.appendChild(box);

                setTimeout(function(){
                  box.style.transition = 'opacity .25s ease, transform .25s ease';
                  box.style.opacity = '0';
                  box.style.transform = 'translateX(18px)';
                  setTimeout(function(){ box.remove(); }, 280);
                }, 6500);
              })();
            {% endfor %}
          });
        {% endif %}
      {% endwith %}
    </script>
    """

    inner = render_template_string(
        html,
        items=items,
        filtro_campo=filtro_campo,
        filtro_valor=filtro_valor,
        filtro_clasificacion=filtro_clasificacion,
        clasif_choices=VULN_CLASIFICACIONES,
        read_only=read_only
    )

    return render_template_string(BASE, content=Markup(inner))



# ==========================
# Detalle Vulnerabilidad
# ==========================

@app.route('/vulnerabilidades/detalle/<int:id>')
@login_required
def vulnerabilidad_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
            flash("No tiene permiso para ver el detalle de la vulnerabilidad.", "danger")
            return redirect(url_for('vulnerabilidades_matriz'))
        read_only = False

    it = (
        VulnerabilidadRegistro.query
        .options(selectinload(VulnerabilidadRegistro.evidencias))
        .get_or_404(id)
    )

    html = """
    <div class="vulndet-shell">

      <div class="vulndet-header-card">
        <div class="vulndet-header-overlay">
          <div class="vulndet-header-text">
            <h3 class="vulndet-title m-0">Detalle de la Vulnerabilidad</h3>
            <div class="vulndet-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="vulndet-header-actions">
        <a href="{{ url_for('vulnerabilidades_matriz') }}"
           class="btn rounded-pill px-4 fw-bold vulndet-back-btn">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('vulnerabilidad_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="vulndet-card">
        <div class="vulndet-card-body">

          <div class="vulndet-section">
            <div class="vulndet-section-title">Información general</div>
            <div class="row g-3">

              <div class="col-md-3">
                <div class="vulndet-field">
                  <div class="vulndet-label">ID</div>
                  <div class="vulndet-value">{{ it.codigo or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="vulndet-field">
                  <div class="vulndet-label">CVE</div>
                  <div class="vulndet-value">{{ it.cve or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="vulndet-field">
                  <div class="vulndet-label">Clasificación</div>
                  <div class="vulndet-value">{{ it.clasificacion or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="vulndet-field">
                  <div class="vulndet-label">Estado</div>
                  <div class="vulndet-value">{{ it.estado or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="vulndet-field">
                  <div class="vulndet-label">Activo</div>
                  <div class="vulndet-value vulndet-value-lg">{{ it.activo or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="vulndet-field">
                  <div class="vulndet-label">Responsable</div>
                  <div class="vulndet-value">{{ it.responsable or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="vulndet-field">
                  <div class="vulndet-label">Tipo de Vulnerabilidad</div>
                  <div class="vulndet-value">{{ it.tipo_vulnerabilidad or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="vulndet-field">
                  <div class="vulndet-label">Riesgo Residual</div>
                  <div class="vulndet-value">{{ it.riesgo_residual or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <div class="vulndet-section">
            <div class="vulndet-section-title">Descripción y tratamiento</div>
            <div class="row g-3">

              <div class="col-md-12">
                <div class="vulndet-field">
                  <div class="vulndet-label">Descripción de la Vulnerabilidad</div>
                  <div class="vulndet-value">{{ it.descripcion_vulnerabilidad or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <div class="vulndet-section">
              <div class="vulndet-section-title">Evidencias</div>

              {% if it.evidencias %}
                <div class="vulndet-files-grid">
                  {% for ev in it.evidencias %}
                    <div class="vulndet-file-card">
                      <div class="vulndet-file-left">
                        <div class="vulndet-file-icon">PDF</div>
                        <div class="vulndet-file-meta">
                          <div class="vulndet-file-label">Archivo asociado</div>
                          <a href="{{ url_for('vulnerabilidad_evidencia_view', evi_id=ev.id) }}"
                             class="vulndet-file-name">
                            {{ ev.original_name }}
                          </a>
                          <div class="vulndet-file-size">{{ (ev.size or 0) // 1024 }} KB</div>
                        </div>
                      </div>

                      <div class="vulndet-file-actions">
                        <a href="{{ url_for('vulnerabilidad_evidencia_view', evi_id=ev.id) }}"
                           class="btn btn-outline-primary btn-sm rounded-pill px-3">
                          Ver archivo
                        </a>
                      </div>
                    </div>
                  {% endfor %}
                </div>
              {% else %}
                <div class="vulndet-empty-box">
                  No hay archivos asociados a esta vulnerabilidad.
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

      .vulndet-shell{
        width:96%;
        max-width:1250px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .vulndet-header-card{
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

      .vulndet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .vulndet-header-card::after{
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
        font-size:1.4rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
        position:relative;
        z-index:1;
        order:-1;
      }

      .vulndet-header-text{
        position:relative;
        z-index:1;
        max-width:1000px;
        min-width:0;
      }

      .vulndet-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        margin:0 !important;
        overflow-wrap:break-word;
      }

      .vulndet-title::before{
        content:"SGSI · Detalle Vulnerabilidad";
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

      .vulndet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }

      .vulndet-header-actions{
        display:flex;
        justify-content:center;
        gap:12px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .btn,
      .vulndet-back-btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        max-width:100%;
      }

      .vulndet-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        padding:8px 22px;
        font-size:.82rem;
      }

      .vulndet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .vulndet-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }

      .vulndet-card-body{
        padding:20px;
        overflow:hidden;
      }

      .vulndet-section{
        margin-bottom:18px;
        background:#ffffff;
        border:1px solid #e2ebf5;
        border-radius:14px;
        padding:8px 7px;
        box-shadow:0 4px 12px rgba(15,23,42,.06);
        overflow:hidden;
      }

      .vulndet-section-title{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:10px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:6px;
        overflow-wrap:break-word;
      }

      .vulndet-field{
        background:#f8fbff;
        border:1px solid #e2ebf5;
        border-radius:12px;
        padding:12px;
        min-width:0;
        overflow:hidden;
      }

      .vulndet-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        color:#0b4a8f;
        margin-bottom:4px;
        letter-spacing:.03em;
      }

      .vulndet-value{
        color:#334155;
        font-size:.82rem;
        line-height:1.45;
        white-space:pre-wrap;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .vulndet-value-lg{
        font-size:.90rem;
        font-weight:800;
        color:#101827;
      }

      .vulndet-file-card{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        background:#f8fbff;
        border:1px solid #e2ebf5;
        border-radius:12px;
        padding:10px 12px;
        box-shadow:0 4px 10px rgba(15,23,42,.06);
        flex-wrap:wrap;
        overflow:hidden;
      }

      .vulndet-file-name{
        font-size:.82rem;
        font-weight:900;
        color:#0b4a8f;
        text-decoration:none;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .vulndet-file-name:hover{
        text-decoration:underline;
      }

      .vulndet-empty-box{
        background:#f8fbff;
        border:1px dashed #cfd8e3;
        border-radius:12px;
        padding:8px 7px;
        text-align:center;
        font-size:.82rem;
        color:#475569;
        font-weight:700;
      }

      h3{
        color:#ffffff;
        margin:0;
      }

      @media (max-width:992px){
        .vulndet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .vulndet-title{
          font-size:1.20rem;
        }

        .vulndet-card-body{
          padding:16px;
        }
      }

      @media (max-width:768px){
        .vulndet-header-card{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .vulndet-header-card::after{
          margin:0;
        }

        .vulndet-title,
        .vulndet-subtitle{
          text-align:center;
        }

        .vulndet-title::before{
          margin-left:auto;
          margin-right:auto;
        }

        .vulndet-header-actions .btn{
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
# Editar Vulnerabilidades
# ==========================

@app.route('/vulnerabilidad/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def vulnerabilidad_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede editar registros.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        flash("No tiene permiso para editar vulnerabilidades.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    it = VulnerabilidadRegistro.query.get_or_404(id)

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
                return redirect(url_for('vulnerabilidad_edit', id=id))
        
        fecha_cierre_str = (request.form.get('fecha_cierre') or '').strip()
        fecha_cierre = None
        if fecha_cierre_str:
            try:
                fecha_cierre = datetime.strptime(fecha_cierre_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de cierre inválida.", "danger")
                return redirect(url_for('vulnerabilidad_edit', id=id))

        if not all([codigo, activo, descripcion_vulnerabilidad, estado, responsable]):
            flash("Campos obligatorios: ID, Activo, Descripción, Estado y Responsable.", "danger")
            return redirect(url_for('vulnerabilidad_edit', id=id))

        it.codigo = codigo
        it.activo = activo
        it.descripcion_vulnerabilidad = descripcion_vulnerabilidad
        it.cve = cve
        it.cvss = cvss
        it.clasificacion = clasificacion
        it.fecha_identificacion = fecha_identificacion
        it.fecha_cierre = fecha_cierre 
        it.estado = estado
        it.responsable = responsable
        it.riesgo_residual = riesgo_residual

         # Manejar nuevas evidencias subidas en la edición
        files = request.files.getlist('evidencias')
        for f in files:
            if not f or not f.filename:
                continue
            if not is_allowed_pdf(f.filename):
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

        # Actualiza también el modelamiento asociado y sus técnicas MITRE
        sincronizar_vulnerabilidad_con_modelamiento(it)

        db.session.commit()
        flash("Vulnerabilidad actualizada y sincronizada con Modelamiento de Amenazas.", "success")
        return redirect(url_for('vulnerabilidades_matriz'))

    # GET: reutilizamos el mismo formulario de new pero con valores precargados
    html = """
    <div class="vulnedit-shell">

      <!-- CABECERA -->
      <div class="vulnedit-header-card">
        <div class="vulnedit-header-overlay">
          <div class="vulnedit-header-text">
            <h3 class="vulnedit-title m-0">Editar Vulnerabilidad</h3>
            <div class="vulnedit-subtitle">
              Actualización de la vulnerabilidad identificada, incluyendo activo afectado, clasificación, fechas, responsable, riesgo residual y gestión de evidencias
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="vulnedit-header-actions">
        <a href="{{ url_for('vuln_scan_runs') }}"
           class="btn rounded-pill px-5 fw-bold vulnedit-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <!-- TARJETA -->
      <div class="vulnedit-card">
        <div class="vulnedit-card-body">
          <form method="post" enctype="multipart/form-data">
            <div class="row g-3">

              <div class="col-12">
                <div class="vulnedit-section-title">Información de la vulnerabilidad</div>
              </div>

              <div class="col-md-3">
                <label class="form-label">ID (alfanumérico)</label>
                <input name="codigo" class="form-control" value="{{ it.codigo }}" required>
              </div>

              <div class="col-md-9">
                <label class="form-label">Activo</label>
                <input name="activo" class="form-control" value="{{ it.activo }}" required>
              </div>

              <div class="col-md-12">
                <label class="form-label">Descripción de la Vulnerabilidad</label>
                <textarea name="descripcion_vulnerabilidad" class="form-control" rows="2" required>{{ it.descripcion_vulnerabilidad }}</textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">CVE</label>
                <input name="cve" class="form-control" value="{{ it.cve or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">CVSS</label>
                <input name="cvss" class="form-control" value="{{ it.cvss or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Clasificación</label>
                <select name="clasificacion" class="form-select">
                  <option value="">-- Seleccione --</option>
                  {% for op in clasif_choices %}
                    <option value="{{ op }}" {% if it.clasificacion == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de Identificación</label>
                <input type="date"
                       name="fecha_identificacion"
                       class="form-control"
                       value="{{ it.fecha_identificacion.isoformat() if it.fecha_identificacion else '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Estado</label>
                <select name="estado" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  <option value="Abierto" {% if it.estado == 'Abierto' %}selected{% endif %}>Abierto</option>
                  <option value="Cerrado" {% if it.estado == 'Cerrado' %}selected{% endif %}>Cerrado</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de Cierre</label>
                <input type="date"
                       name="fecha_cierre"
                       class="form-control"
                       value="{{ it.fecha_cierre.isoformat() if it.fecha_cierre else '' }}">
              </div>

              <div class="col-md-6">
                <label class="form-label">Responsable</label>
                <input name="responsable" class="form-control" value="{{ it.responsable }}" required>
              </div>

              <div class="col-md-6">
                <label class="form-label">Riesgo Residual</label>
                <textarea name="riesgo_residual" class="form-control" rows="2">{{ it.riesgo_residual or '' }}</textarea>
              </div>

              <!-- EVIDENCIAS EXISTENTES -->
              <div class="col-12 mt-3">
                <div class="vulnedit-section-title">Evidencias existentes</div>

                {% if it.evidencias %}
                  <div class="vulnedit-evidence-list">
                    {% for ev in it.evidencias %}
                      <div class="vulnedit-evidence-item d-flex justify-content-between align-items-center">
                        <div class="d-flex flex-column">
                          <a href="{{ url_for('vulnerabilidad_evidencia_view', evi_id=ev.id) }}" target="_blank">
                            📄 {{ ev.original_name }}
                          </a>
                          <span class="text-muted small">({{ (ev.size or 0) // 1024 }} KB)</span>
                        </div>

                        <a href="{{ url_for('vulnerabilidad_evidencia_delete', evi_id=ev.id) }}"
                           class="btn btn-sm btn-outline-danger rounded-pill px-3"
                           onclick="return confirm('¿Eliminar esta evidencia?');">
                          🗑️ Eliminar
                        </a>
                      </div>
                    {% endfor %}
                  </div>
                {% else %}
                  <div class="text-muted small">No hay evidencias asociadas.</div>
                {% endif %}
              </div>

              <!-- NUEVAS EVIDENCIAS -->
              <div class="col-12 mt-3">
                <div class="vulnedit-section-title">Agregar nuevas evidencias</div>

                <label class="form-label">Nuevas evidencias (múltiples archivos)</label>
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

            <div class="vulnedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>
              <a href="{{ url_for('vulnerabilidades_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold vulnedit-cancel-btn">
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

      .vulnedit-shell{
        width:96%;
        max-width:1200px;
        margin:10px auto 24px auto;
      }

      .vulnedit-header-card{
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

      .vulnedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .vulnedit-header-overlay{
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

      .vulnedit-header-overlay::before{
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

      .vulnedit-header-text{
        max-width:1000px;
        width:100%;
        display:block;
        transform:none;
      }

      .vulnedit-header-text::before{
        content:"SGSI · Edición de Vulnerabilidad";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .vulnedit-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .vulnedit-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .vulnedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .vulnedit-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .vulnedit-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .vulnedit-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .vulnedit-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .vulnedit-card-body{
        padding:18px;
      }

      .vulnedit-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .vulnedit-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .vulnedit-card .form-control,
      .vulnedit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:32px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .vulnedit-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .vulnedit-card .form-control:focus,
      .vulnedit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }

      .vulnedit-card .input-group-text{
        border-radius:0 9px 9px 0;
        border:1px solid #d9e3f0;
        background:#eef5ff;
        color:#0b4a8f;
        font-weight:900;
      }

      .vulnedit-evidence-list{
        display:flex;
        flex-direction:column;
        gap:10px;
      }

      .vulnedit-evidence-item{
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:10px 12px;
        box-shadow:0 6px 14px rgba(15,23,42,.08);
      }

      .vulnedit-evidence-name{
        font-size:.80rem;
        font-weight:900;
        color:#1d4ed8;
        word-break:break-word;
      }

      .vulnedit-evidence-meta{
        font-size:.70rem;
        color:#475569;
        margin-top:4px;
        font-weight:700;
      }

      .vulnedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
        width:100%;
      }

      .vulnedit-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .vulnedit-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .vulnedit-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .vulnedit-save-btn{
        font-weight:900;
      }

      .vulnedit-soft-box{
        background:#eef5ff;
        border:1px solid #d9eaff;
        border-radius:14px;
        padding:12px 14px;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      @media (max-width:992px){
        .vulnedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .vulnedit-header-card{
          min-height:88px;
        }

        .vulnedit-title{
          font-size:1.20rem;
        }

        .vulnedit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .vulnedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .vulnedit-header-overlay::before{
          margin:0;
        }

        .vulnedit-header-actions .btn,
        .vulnedit-bottom-actions .btn{
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
    """
    inner = render_template_string(html, it=it, clasif_choices=VULN_CLASIFICACIONES)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Eliminar
# =========================

@app.route('/vulnerabilidades/evidencia/<int:evi_id>/delete')
@login_required
def vulnerabilidad_evidencia_delete(evi_id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar evidencias.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        flash("No tiene permiso para eliminar evidencias.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    ev = VulnerabilidadEvidencia.query.get_or_404(evi_id)
    vuln_id = ev.vulnerabilidad_id  # asumiendo columna FK

    # borrar archivo físico
    try:
        path = os.path.join(app.config['UPLOAD_VULNERABILIDADES_DIR'], ev.filename)
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

    db.session.delete(ev)
    db.session.commit()
    flash("Evidencia eliminada.", "success")
    return redirect(url_for('vulnerabilidad_edit', id=vuln_id))


# ==========================
# Helpers de relación Vulnerabilidades ↔ Modelamiento de Amenazas
# ==========================

def _normalizar_ids_vulnerabilidad(ids):
    """Retorna una lista limpia de IDs enteros únicos."""
    limpios = []
    vistos = set()

    for valor in ids or []:
        try:
            vid = int(valor)
        except Exception:
            continue

        if vid > 0 and vid not in vistos:
            vistos.add(vid)
            limpios.append(vid)

    return limpios


def eliminar_modelamientos_por_vulnerabilidades(vulnerabilidad_ids):
    """
    Elimina los registros de modelamiento asociados a vulnerabilidades.

    Además de las entradas y técnicas MITRE, elimina los registros de
    ``Clasificación complementaria No Mapeados`` creados automáticamente
    para vulnerabilidades que no pudieron clasificarse en MITRE ATT&CK.
    """
    ids = _normalizar_ids_vulnerabilidad(vulnerabilidad_ids)

    if not ids:
        return 0

    try:
        registros = (
            ThreatModelEntry.query
            .options(selectinload(ThreatModelEntry.tecnicas))
            .filter(ThreatModelEntry.vulnerabilidad_registro_id.in_(ids))
            .all()
        )

        no_mapeados = (
            ThreatModelUnmapped.query
            .filter(
                ThreatModelUnmapped.herramienta == THREAT_MODEL_VULN_SOURCE,
                ThreatModelUnmapped.finding_id.in_(ids)
            )
            .all()
        )

        total = len(registros) + len(no_mapeados)

        for item in registros:
            db.session.delete(item)

        # La clasificación complementaria se elimina por cascade desde
        # ThreatModelUnmapped.clasificacion_complementaria.
        for item in no_mapeados:
            db.session.delete(item)

        return total

    except Exception:
        # Fallback SQL para arranques parciales o bases históricas.
        placeholders = ",".join(str(i) for i in ids)
        if not placeholders:
            return 0

        try:
            db.session.execute(text(f"""
                DELETE FROM threat_model_unmapped_classifications
                WHERE unmapped_id IN (
                    SELECT id
                    FROM threat_model_unmapped
                    WHERE herramienta = '{THREAT_MODEL_VULN_SOURCE}'
                      AND finding_id IN ({placeholders})
                )
            """))

            db.session.execute(text(f"""
                DELETE FROM threat_model_unmapped
                WHERE herramienta = '{THREAT_MODEL_VULN_SOURCE}'
                  AND finding_id IN ({placeholders})
            """))

            db.session.execute(text(f"""
                DELETE FROM threat_model_techniques
                WHERE threat_entry_id IN (
                    SELECT id
                    FROM threat_model_entries
                    WHERE vulnerabilidad_registro_id IN ({placeholders})
                )
            """))

            db.session.execute(text(f"""
                DELETE FROM threat_model_entries
                WHERE vulnerabilidad_registro_id IN ({placeholders})
            """))

            return 0

        except Exception:
            raise



def existe_vulnerabilidad_asociada_a_threat_model(item):
    """
    Valida si un registro de modelamiento tiene una vulnerabilidad vigente asociada.

    Regla funcional:
    - No se permite eliminar manualmente un ID de modelamiento si todavía existe
      la vulnerabilidad relacionada.
    """
    if not item:
        return False

    vuln_id = getattr(item, "vulnerabilidad_registro_id", None)

    if not vuln_id:
        return False

    try:
        return VulnerabilidadRegistro.query.get(int(vuln_id)) is not None
    except Exception:
        return False

# ==========================
# Eliminar Vulnerabilidad
# ==========================

@app.route('/vulnerabilidad/<int:id>/delete')
@login_required
def vulnerabilidad_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        flash("No tiene permiso para eliminar vulnerabilidades.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    db.session.rollback()

    it = VulnerabilidadRegistro.query.get_or_404(id)

    try:
        # ==========================
        # Validar si tiene remediación asociada
        # ==========================
        plan_asociado = PlanRemediacion.query.filter_by(
            vulnerabilidad_id=id
        ).first()

        if plan_asociado:
            flash(
                "No se puede eliminar esta vulnerabilidad porque tiene un plan de remediación asociado. "
                "Primero elimine el plan de remediación correspondiente.",
                "warning"
            )
            return redirect(url_for('vulnerabilidades_matriz'))

        # ==========================
        # Eliminar modelamiento de amenazas asociado
        # ==========================
        total_threat = eliminar_modelamientos_por_vulnerabilidades([id])

        # ==========================
        # Desvincular hallazgos de escaneo
        # ==========================
        try:
            VulnerabilityScanFinding.query.filter_by(
                vulnerabilidad_registro_id=id
            ).update(
                {"vulnerabilidad_registro_id": None},
                synchronize_session=False
            )
        except Exception:
            pass

        # ==========================
        # Eliminar evidencias físicas y BD
        # ==========================
        try:
            for ev in list(getattr(it, "evidencias", []) or []):
                try:
                    filename = getattr(ev, "filename", None)

                    if filename:
                        path = os.path.join(
                            app.config['UPLOAD_VULNERABILIDADES_DIR'],
                            filename
                        )

                        if os.path.exists(path):
                            os.remove(path)

                    db.session.delete(ev)

                except Exception:
                    pass
        except Exception:
            pass

        # ==========================
        # Eliminar vulnerabilidad
        # ==========================
        db.session.delete(it)
        db.session.commit()

        if total_threat:
            flash(
                f"Vulnerabilidad eliminada correctamente. También se eliminaron {total_threat} registro(s) de modelamiento de amenazas asociado(s).",
                "success"
            )
        else:
            flash("Vulnerabilidad eliminada correctamente.", "success")

    except Exception as e:
        db.session.rollback()
        flash(
            "No fue posible eliminar la vulnerabilidad. "
            "Verifique si tiene registros asociados en planes de remediación, evidencias o escaneos.",
            "danger"
        )

    return redirect(url_for('vulnerabilidades_matriz'))

# ==========================
# Eliminar vulnerabilidades por filtros
# ==========================

@app.route('/vulnerabilidades/delete_filtrados', methods=['POST'])
@login_required
def vulnerabilidades_delete_filtrados():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        flash("No tiene permiso para eliminar vulnerabilidades.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    db.session.rollback()

    filtro_campo = (request.form.get('campo') or 'activo').strip()
    filtro_valor = (request.form.get('valor') or '').strip()
    filtro_clasificacion = (request.form.get('clasificacion') or '').strip()

    campos_validos = {
        'codigo',
        'activo',
        'cve',
        'clasificacion',
        'responsable',
        'estado',
        'tipo_vulnerabilidad'
    }

    if filtro_campo not in campos_validos:
        filtro_campo = 'activo'

    q = VulnerabilidadRegistro.query.options(
        selectinload(VulnerabilidadRegistro.evidencias)
    )

    if filtro_valor:
        columna = getattr(VulnerabilidadRegistro, filtro_campo, None)
        if columna is not None:
            q = q.filter(columna.ilike(f"%{filtro_valor}%"))

    if filtro_clasificacion:
        q = q.filter(VulnerabilidadRegistro.clasificacion == filtro_clasificacion)

    registros = q.all()

    if not registros:
        flash("No se encontraron vulnerabilidades para eliminar con los filtros aplicados.", "warning")
        return redirect(url_for(
            'vulnerabilidades_matriz',
            campo=filtro_campo,
            valor=filtro_valor,
            clasificacion=filtro_clasificacion
        ))

    try:
        total = len(registros)
        ids = [int(it.id) for it in registros if it and it.id]

        if not ids:
            flash("No se encontraron IDs válidos para eliminar.", "warning")
            return redirect(url_for('vulnerabilidades_matriz'))

        placeholders = ",".join(str(i) for i in ids)

        # ==========================
        # 1. Eliminar archivos físicos de evidencias
        # ==========================
        try:
            evidencias = VulnerabilidadEvidencia.query.filter(
                VulnerabilidadEvidencia.vulnerabilidad_id.in_(ids)
            ).all()

            for ev in evidencias:
                try:
                    filename = getattr(ev, "filename", None)
                    if filename:
                        path = os.path.join(
                            app.config['UPLOAD_VULNERABILIDADES_DIR'],
                            filename
                        )
                        if os.path.exists(path):
                            os.remove(path)
                except Exception:
                    pass
        except Exception:
            pass

        # ==========================
        # 2. Eliminar evidencias desde el modelo correcto
        # ==========================
        try:
            VulnerabilidadEvidencia.query.filter(
                VulnerabilidadEvidencia.vulnerabilidad_id.in_(ids)
            ).delete(synchronize_session=False)
        except Exception:
            pass

        # ==========================
        # 3. Eliminar planes de remediación asociados
        # ==========================
        try:
            db.session.execute(text(f"""
                DELETE FROM plan_remediacion
                WHERE vulnerabilidad_id IN ({placeholders})
            """))
        except Exception:
            pass

        # ==========================
        # 4. Eliminar modelamiento de amenazas asociado
        # ==========================
        total_threat = eliminar_modelamientos_por_vulnerabilidades(ids)

        # ==========================
        # 5. Desvincular hallazgos de escaneo
        # ==========================
        try:
            db.session.execute(text(f"""
                UPDATE vulnerability_scan_findings
                SET vulnerabilidad_registro_id = NULL
                WHERE vulnerabilidad_registro_id IN ({placeholders})
            """))
        except Exception:
            pass

        # ==========================
        # 6. Eliminar vulnerabilidades
        # ==========================
        db.session.execute(text(f"""
            DELETE FROM vulnerabilidades_registro
            WHERE id IN ({placeholders})
        """))

        db.session.commit()

        if total_threat:
            flash(
                f"Se eliminaron {total} vulnerabilidades correctamente. También se eliminaron {total_threat} registro(s) de modelamiento de amenazas asociado(s).",
                "success"
            )
        else:
            flash(f"Se eliminaron {total} vulnerabilidades correctamente.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"No fue posible eliminar las vulnerabilidades filtradas: {str(e)}", "danger")

    return redirect(url_for('vulnerabilidades_matriz'))

# ==========================
# Archivo físico de evidencia — Vulnerabilidades
# ==========================
@app.route('/vulnerabilidades/evidencia/<int:evi_id>/file')
@login_required
def vulnerabilidad_evidencia_file(evi_id):
    ev = VulnerabilidadEvidencia.query.get_or_404(evi_id)

    file_path = os.path.join(app.config['UPLOAD_VULNERABILIDADES_DIR'], ev.filename)

    if not os.path.exists(file_path):
        flash("El archivo de evidencia no se encuentra en el servidor.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    resp = send_file(
        file_path,
        as_attachment=False,
        download_name=ev.original_name,
        mimetype=ev.mime or 'application/pdf'
    )
    resp.headers['Content-Disposition'] = f'inline; filename="{ev.original_name}"'
    return resp

# ==========================
# Vista de evidencia — Vulnerabilidades
# ==========================
@app.route('/vulnerabilidades/evidencia/<int:evi_id>/view')
@login_required
def vulnerabilidad_evidencia_view(evi_id):
    ev = VulnerabilidadEvidencia.query.get_or_404(evi_id)

    html = """
    <div class="vulevi-shell">

      <!-- CABECERA -->
      <div class="vulevi-header-card">
        <div class="vulevi-header-overlay">
          <div class="vulevi-header-text">
            <h3 class="vulevi-title m-0">📄 Evidencia de Vulnerabilidad</h3>
            <div class="vulevi-subtitle">
              Visualización del archivo adjunto asociado al registro de vulnerabilidad
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="vulevi-header-actions">
        <a href="{{ url_for('vulnerabilidades_matriz') }}"
           class="btn rounded-pill px-5 fw-bold vulevi-back-btn">
          ⬅ Volver a la Matriz de Vulnerabilidades
        </a>
      </div>

      <!-- TARJETA VISOR -->
      <div class="vulevi-card">
        <div class="vulevi-card-body">

          <div class="vulevi-file-bar">
            <div class="vulevi-file-left">
              <div class="vulevi-file-icon">PDF</div>
              <div class="vulevi-file-meta">
                <div class="vulevi-file-label">Archivo de evidencia</div>
                <div class="vulevi-file-name">{{ ev.original_name or 'Evidencia' }}</div>
              </div>
            </div>

            <div class="vulevi-file-actions">
              <a href="{{ url_for('vulnerabilidad_evidencia_file', evi_id=ev.id) }}"
                 target="_blank"
                 class="btn btn-outline-primary rounded-pill px-4 fw-bold">
                Abrir en nueva pestaña
              </a>
            </div>
          </div>

          <div class="vulevi-viewer-wrap">
            <iframe
              src="{{ url_for('vulnerabilidad_evidencia_file', evi_id=ev.id) }}"
              class="vulevi-iframe">
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

      .vulevi-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 30px auto;
      }

      /* =========================
         HEADER ESTÁNDAR SGSI
         ========================= */
      .vulevi-header-card{
        background:#3f86d6;
        height:88px;
        display:flex;
        align-items:center;
        justify-content:center;
        border-radius:18px;
        box-shadow:0 12px 30px rgba(0,0,0,.30);
        overflow:hidden;
        margin-bottom:14px;
      }

      .vulevi-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:flex-start;
        justify-content:center;
        text-align:center;
        padding:8px 24px 6px 24px;
        background:rgba(0,0,0,.08);
      }

      .vulevi-header-text{
        max-width:1100px;
        width:100%;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:flex-start;
        transform:translateY(8px);
      }

      .vulevi-title{
        color:#fff !important;
        font-weight:900;
        font-size:1.38rem;
        line-height:1.10;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        margin:0 !important;
      }

      .vulevi-subtitle{
        color:rgba(255,255,255,.96);
        font-size:.82rem;
        margin-top:4px;
        line-height:1.15;
      }

      /* =========================
         BOTONES
         ========================= */
      .vulevi-header-actions{
        display:flex;
        justify-content:center;
        margin-bottom:16px;
        gap:10px;
        flex-wrap:wrap;
      }

      .vulevi-back-btn{
        background:#ffffff;
        color:#000000;
        border:2px solid #ffffff;
        box-shadow:0 4px 10px rgba(0,0,0,.10);
      }

      .vulevi-back-btn:hover{
        background:#f3f4f6;
        color:#000000;
        border-color:#f3f4f6;
      }

      /* =========================
         CARD PRINCIPAL
         ========================= */
      .vulevi-card{
        background:rgba(255,255,255,.95);
        border-radius:20px;
        backdrop-filter:blur(6px);
        box-shadow:0 14px 30px rgba(0,0,0,.18);
        overflow:hidden;
      }

      .vulevi-card-body{
        padding:18px;
      }

      /* =========================
         BARRA DE ARCHIVO
         ========================= */
      .vulevi-file-bar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:14px;
        flex-wrap:wrap;
        margin-bottom:16px;
        padding:14px 16px;
        background:linear-gradient(180deg,#ffffff 0%,#f8fafc 100%);
        border:1px solid rgba(0,0,0,.06);
        border-radius:16px;
        box-shadow:0 4px 12px rgba(0,0,0,.05);
      }

      .vulevi-file-left{
        display:flex;
        align-items:center;
        gap:12px;
        min-width:0;
      }

      .vulevi-file-icon{
        width:46px;
        height:46px;
        min-width:46px;
        border-radius:12px;
        background:#ef4444;
        color:#fff;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:.82rem;
        font-weight:800;
        box-shadow:0 6px 14px rgba(239,68,68,.22);
      }

      .vulevi-file-meta{
        min-width:0;
      }

      .vulevi-file-label{
        font-size:.78rem;
        color:#475569;
        font-weight:700;
      }

      .vulevi-file-name{
        font-size:.96rem;
        font-weight:800;
        color:#0f172a;
        word-break:break-word;
      }

      /* =========================
         VISOR
         ========================= */
      .vulevi-viewer-wrap{
        height:78vh;
        border:1px solid rgba(0,0,0,.08);
        border-radius:16px;
        overflow:hidden;
        background:#ffffff;
        box-shadow:inset 0 1px 2px rgba(0,0,0,.04);
      }

      .vulevi-iframe{
        width:100%;
        height:100%;
        border:0;
        display:block;
        background:#fff;
      }

      /* =========================
         RESPONSIVE
         ========================= */
      @media (max-width:992px){
        .vulevi-shell{
          width:98%;
          margin:8px auto 24px auto;
        }

        .vulevi-header-card{
          height:84px;
        }

        .vulevi-header-overlay{
          padding:8px 16px 6px 16px;
        }

        .vulevi-header-text{
          transform:translateY(-1px);
        }

        .vulevi-title{
          font-size:1.20rem;
          line-height:1.08;
        }

        .vulevi-subtitle{
          font-size:.68rem;
          line-height:1.12;
        }

        .vulevi-card-body{
          padding:8px 7px;
        }

        .vulevi-viewer-wrap{
          height:72vh;
        }
      }
    </style>
    """

    inner = render_template_string(html, ev=ev)
    return render_template_string(BASE, content=Markup(inner))

# ==========================
# Configuración Kali Linux
# ==========================
@app.route('/vulnerabilidades/scan/config', methods=['GET', 'POST'])
@login_required
def vuln_scan_config():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede modificar la configuración.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        flash("No tiene permiso para configurar el escaneo.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    cfg = _scan_cfg()

    if request.method == 'POST':
        cfg.modo = (request.form.get('modo') or 'local').strip()
        cfg.host = (request.form.get('host') or '').strip() or None
        cfg.puerto_ssh = request.form.get('puerto_ssh', type=int) or 22
        cfg.usuario_ssh = (request.form.get('usuario_ssh') or '').strip() or None
        cfg.password_ssh = (request.form.get('password_ssh') or '').strip() or None
        cfg.ruta_base_remota = (request.form.get('ruta_base_remota') or '').strip() or None

        cfg.ruta_nmap = (request.form.get('ruta_nmap') or '/usr/bin/nmap').strip()
        cfg.ruta_nikto = (request.form.get('ruta_nikto') or '/usr/bin/nikto').strip()
        cfg.ruta_nuclei = (request.form.get('ruta_nuclei') or '/usr/bin/nuclei').strip()
        cfg.ruta_whatweb = (request.form.get('ruta_whatweb') or '/usr/bin/whatweb').strip()
        cfg.ruta_testssl = (request.form.get('ruta_testssl') or '/usr/bin/testssl').strip()
        cfg.ruta_zap = (request.form.get('ruta_zap') or '/usr/share/zaproxy/zap.sh').strip()

        cfg.updated_at = datetime.utcnow()

        db.session.commit()
        flash("Configuración de Kali Linux guardada correctamente.", "success")
        return redirect(url_for('vuln_scan_config'))

    body = """
    <div class="glass-card p-4 mt-2">
      <div class="section-title">⚙️ Configuración del Motor de Escaneo</div>

      <form method="post">
        <div class="row g-3">

          <div class="col-md-4">
            <label class="form-label">Modo de Integración</label>
            <select name="modo" class="form-select">
              <option value="local" {% if cfg.modo == 'local' %}selected{% endif %}>
                Local
              </option>
              <option value="remoto" {% if cfg.modo == 'remoto' %}selected{% endif %}>
                Remoto (otra IP por SSH)
              </option>
            </select>
          </div>

          <div class="col-md-4">
            <label class="form-label">Host Kali Remoto</label>
            <input name="host"
                   class="form-control"
                   value="{{ cfg.host or '' }}"
                   placeholder="192.168.1.50">
          </div>

          <div class="col-md-4">
            <label class="form-label">Puerto SSH</label>
            <input name="puerto_ssh"
                   type="number"
                   class="form-control"
                   value="{{ cfg.puerto_ssh or 22 }}">
          </div>

          <div class="col-md-4">
            <label class="form-label">Usuario SSH</label>
            <input name="usuario_ssh"
                   class="form-control"
                   value="{{ cfg.usuario_ssh or '' }}">
          </div>

          <div class="col-md-4">
            <label class="form-label">Password SSH</label>
            <input name="password_ssh"
                   type="password"
                   class="form-control"
                   value="{{ cfg.password_ssh or '' }}">
          </div>

          <div class="col-md-4">
            <label class="form-label">Ruta Base Remota</label>
            <input name="ruta_base_remota"
                   class="form-control"
                   value="{{ cfg.ruta_base_remota or '/tmp' }}">
          </div>

          <div class="col-md-3">
            <label class="form-label">Ruta Nmap</label>
            <input name="ruta_nmap"
                   class="form-control"
                   value="{{ cfg.ruta_nmap or '/usr/bin/nmap' }}">
          </div>

          <div class="col-md-3">
            <label class="form-label">Ruta Nikto</label>
            <input name="ruta_nikto"
                   class="form-control"
                   value="{{ cfg.ruta_nikto or '/usr/bin/nikto' }}">
          </div>

          <div class="col-md-3">
            <label class="form-label">Ruta Nuclei</label>
            <input name="ruta_nuclei"
                   class="form-control"
                   value="{{ cfg.ruta_nuclei or '/usr/bin/nuclei' }}">
          </div>

          <div class="col-md-3">
            <label class="form-label">Ruta WhatWeb</label>
            <input name="ruta_whatweb"
                   class="form-control"
                   value="{{ cfg.ruta_whatweb or '/usr/bin/whatweb' }}">
          </div>

          <div class="col-md-3">
            <label class="form-label">Ruta testssl</label>
            <input name="ruta_testssl"
                   class="form-control"
                   value="{{ cfg.ruta_testssl or '/usr/bin/testssl' }}">
          </div>

          <div class="col-md-3">
            <label class="form-label">Ruta OWASP ZAP</label>
            <input name="ruta_zap"
                   class="form-control"
                   value="{{ cfg.ruta_zap or '/usr/share/zaproxy/zap.sh' }}"
                   placeholder="/usr/share/zaproxy/zap.sh">
          </div>

          <div class="col-12">
            <div class="toolbar-actions justify-content-center mt-2">
              <button class="btn btn-primary rounded-pill px-4">
                Guardar Configuración
              </button>

              <a href="{{ url_for('vulnerabilidades_matriz') }}"
                 class="btn btn-outline-secondary rounded-pill px-4">
                Cancelar
              </a>
            </div>
          </div>

        </div>
      </form>
    </div>
    """

    return vuln_scan_shell(
        "Configuración de Kali Linux",
        render_template_string(body, cfg=cfg)
    )


# ==========================
# Nuevo escaneo
# ==========================
@app.route('/vulnerabilidades/scan/new', methods=['GET', 'POST'])
@login_required
def vuln_scan_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede ejecutar escaneos.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        flash("No tiene permiso para ejecutar escaneos.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    cfg = _scan_cfg()

    if request.method == 'POST':
        target = (request.form.get('target') or '').strip()
        responsable = (request.form.get('responsable') or '').strip()
        crear_vulns = bool(request.form.get('crear_vulns'))
        crear_planes = bool(request.form.get('crear_planes'))

        # ==========================
        # Herramientas seleccionadas
        # ==========================
        herramientas = request.form.getlist("herramientas")

        herramientas_validas = [
            "nmap",
            "nikto",
            "nuclei",
            "whatweb",
            "testssl",
            "zap"
        ]

        herramientas = [
            h for h in herramientas
            if h in herramientas_validas
        ]

        if not herramientas:
            herramientas = ["nmap"]

        if not target_valido(target):
            flash("Debe ingresar una URL o IP válida.", "danger")
            return redirect(url_for('vuln_scan_new'))

        target_type = detectar_tipo_objetivo(target)

        run = VulnerabilityScanRun(
            target=normalizar_target_para_scan(target) if target_type == "url" else target,
            target_type=target_type,
            scan_mode='full',
            scanner_mode=cfg.modo,
            estado='ejecutando',
            fecha_inicio=datetime.utcnow(),
            fecha_fin=None,
            ejecutado_por=getattr(user, 'username', None),
            responsable_asignado=responsable or getattr(user, 'username', None),
            progress_pct=1,
            current_stage="Encolando escaneo",
            current_tool="dispatcher",
            cancel_requested=False,
            stopped_by_user=False,
            findings_streamed=0,
            created_vulns=0,
            created_plans=0,
            herramientas=json.dumps(herramientas)
        )

        db.session.add(run)
        db.session.commit()

        lanzar_scan_background(
            run.id,
            crear_vulns=crear_vulns,
            crear_planes=crear_planes
        )

        return redirect(url_for('vuln_scan_monitor', run_id=run.id))

    body = """
    <div class="glass-card p-4 mt-2">
      <div class="section-title">🛰️ Nuevo Análisis Automático</div>

      <form method="post">
        <div class="row g-3">

          <div class="col-md-8">
            <label class="form-label">Objetivo a escanear (URL o IP)</label>
            <input name="target"
                   class="form-control"
                   placeholder="https://midominio.com o 192.168.1.10"
                   required>
          </div>

          <div class="col-md-4">
            <label class="form-label">Responsable</label>
            <input name="responsable"
                   class="form-control"
                   value="{{ current_user.username if current_user.is_authenticated else '' }}">
          </div>

          <div class="col-md-4">
            <label class="form-label">Modo configurado</label>
            <input class="form-control" value="{{ cfg.modo }}" readonly>
          </div>

          <div class="col-md-8">
            <label class="form-label">Motor Kali actual</label>
            <input class="form-control"
                   value="{% if cfg.modo == 'local' %}Localhost{% else %}{{ cfg.host or 'No configurado' }}{% endif %}"
                   readonly>
          </div>

          <div class="col-12">
            <div class="glass-card p-3 mb-2 mt-2">
              <div class="section-title">
                🛠️ Herramientas de Escaneo
              </div>

              <div class="row">

                <div class="col-md-4 mb-2">
                  <div class="form-check">
                    <input class="form-check-input"
                           type="checkbox"
                           name="herramientas"
                           value="nmap"
                           id="tool_nmap"
                           checked>
                    <label class="form-check-label fw-semibold" for="tool_nmap">
                      Nmap
                    </label>
                  </div>
                </div>

                <div class="col-md-4 mb-2">
                  <div class="form-check">
                    <input class="form-check-input"
                           type="checkbox"
                           name="herramientas"
                           value="nikto"
                           id="tool_nikto"
                           checked>
                    <label class="form-check-label fw-semibold" for="tool_nikto">
                      Nikto
                    </label>
                  </div>
                </div>

                <div class="col-md-4 mb-2">
                  <div class="form-check">
                    <input class="form-check-input"
                           type="checkbox"
                           name="herramientas"
                           value="nuclei"
                           id="tool_nuclei"
                           checked>
                    <label class="form-check-label fw-semibold" for="tool_nuclei">
                      Nuclei
                    </label>
                  </div>
                </div>

                <div class="col-md-4 mb-2">
                  <div class="form-check">
                    <input class="form-check-input"
                           type="checkbox"
                           name="herramientas"
                           value="whatweb"
                           id="tool_whatweb"
                           checked>
                    <label class="form-check-label fw-semibold" for="tool_whatweb">
                      WhatWeb
                    </label>
                  </div>
                </div>

                <div class="col-md-4 mb-2">
                  <div class="form-check">
                    <input class="form-check-input"
                           type="checkbox"
                           name="herramientas"
                           value="testssl"
                           id="tool_testssl"
                           checked>
                    <label class="form-check-label fw-semibold" for="tool_testssl">
                      testssl
                    </label>
                  </div>
                </div>

                <div class="col-md-4 mb-2">
                  <div class="form-check">
                    <input class="form-check-input"
                           type="checkbox"
                           name="herramientas"
                           value="zap"
                           id="tool_zap"
                           checked>
                    <label class="form-check-label fw-semibold" for="tool_zap">
                      OWASP ZAP
                    </label>
                  </div>
                </div>

              </div>
            </div>
          </div>

          <div class="col-md-6">
            <div class="form-check mt-4">
              <input class="form-check-input"
                     type="checkbox"
                     name="crear_vulns"
                     id="crear_vulns"
                     checked>
              <label class="form-check-label" for="crear_vulns">
                Crear registros en la matriz de vulnerabilidades
              </label>
            </div>
          </div>

          <div class="col-md-6">
            <div class="form-check mt-4">
              <input class="form-check-input"
                     type="checkbox"
                     name="crear_planes"
                     id="crear_planes"
                     checked>
              <label class="form-check-label" for="crear_planes">
                Crear planes de remediación automáticamente
              </label>
            </div>
          </div>

          <div class="col-12 mt-3">
            <div class="toolbar-actions justify-content-center">
              <button class="btn btn-primary rounded-pill px-4">
                Ejecutar Escaneo
              </button>

              <a href="{{ url_for('vulnerabilidades_matriz') }}"
                 class="btn btn-outline-secondary rounded-pill px-4">
                Cancelar
              </a>
            </div>
          </div>

        </div>
      </form>
    </div>

    <div class="glass-card p-3 mt-3">
      <div class="small text-muted">
        <b>Herramientas disponibles:</b>
        Nmap, Nikto, Nuclei, WhatWeb, testssl y OWASP ZAP.
      </div>
    </div>
    """

    return vuln_scan_shell(
        "Análisis Automático de Vulnerabilidades",
        render_template_string(
            body,
            cfg=cfg,
            current_user=current_user
        )
    )

# ==========================
# PANTALLA DE MONITOREO CON BARRA Y BOTÓN PARAR
# ==========================
@app.route('/vulnerabilidades/scan/<int:run_id>/monitor')
@login_required
def vuln_scan_monitor(run_id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede ejecutar escaneos.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        flash("No tiene permiso para monitorear escaneos.", "danger")
        return redirect(url_for('menu'))

    run = VulnerabilityScanRun.query.get_or_404(run_id)

    body = """
    <div class="glass-card p-4 mt-2">
      <div class="section-title">Monitoreo del Escaneo #{{ run.id }}</div>

      <div class="row g-3">
        <div class="col-md-8">
          <label class="form-label">Objetivo</label>
          <input class="form-control" value="{{ run.target }}" readonly>
        </div>
        <div class="col-md-4">
          <label class="form-label">Estado</label>
          <div id="estado_badge">{{ badge_estado_scan_html(run.estado) }}</div>
        </div>

        <div class="col-12">
          <label class="form-label">Etapa actual</label>
          <input class="form-control" id="current_stage" value="{{ run.current_stage or 'Pendiente' }}" readonly>
        </div>

        <div class="col-12">
          <label class="form-label">Progreso</label>
          <div class="progress">
            <div id="progress_bar" class="progress-bar bg-primary" role="progressbar" style="width: {{ run.progress_pct or 0 }}%;">
              {{ run.progress_pct or 0 }}%
            </div>
          </div>
        </div>

        <div class="col-md-3">
          <div class="metric-box">
            <div class="metric-label">Hallazgos en línea</div>
            <div class="metric-value" id="metric_findings">{{ run.findings_streamed or 0 }}</div>
          </div>
        </div>

        <div class="col-md-3">
          <div class="metric-box">
            <div class="metric-label">Vulnerabilidades creadas</div>
            <div class="metric-value" id="metric_vulns">{{ run.created_vulns or 0 }}</div>
          </div>
        </div>

        <div class="col-md-3">
          <div class="metric-box">
            <div class="metric-label">Planes creados</div>
            <div class="metric-value" id="metric_plans">{{ run.created_plans or 0 }}</div>
          </div>
        </div>

        <div class="col-md-3">
          <div class="metric-box">
            <div class="metric-label">Herramienta actual</div>
            <div class="metric-value" id="metric_tool">{{ run.current_tool or '—' }}</div>
          </div>
        </div>

        <div class="col-12">
          <div class="toolbar-actions justify-content-center mt-2">
            <button id="btn_stop" class="btn btn-danger rounded-pill px-4" {% if run.estado not in ['pendiente','ejecutando'] %}disabled{% endif %}>
              ⏹ Parar Escaneo
            </button>

            <a href="{{ url_for('vuln_scan_detail', run_id=run.id) }}"
               class="btn btn-warning rounded-pill px-4"
               id="btn_ver_detalle">
              Ver Detalle
            </a>
          </div>
        </div>
      </div>
    </div>

    <div class="soft-table-wrap mt-3">
      <div class="p-3 pb-0">
        <div class="section-title mb-2">🧾 Hallazgos cargados en línea</div>
      </div>

      <div class="table-responsive px-3 pb-3">
        <table class="table table-hover align-middle soft-table mb-0">
          <thead>
            <tr>
              <th>#</th>
              <th>Fuente</th>
              <th>Título</th>
              <th>Severidad</th>
              <th>Puerto</th>
              <th>Servicio</th>
            </tr>
          </thead>
          <tbody id="tbody_findings">
            {% for f in findings %}
            <tr>
              <td class="text-center fw-bold">{{ loop.index }}</td>
              <td class="text-center">{{ f.fuente }}</td>
              <td class="small">{{ f.titulo }}</td>
              <td class="text-center">{{ badge_severidad_html(f.severidad) }}</td>
              <td class="text-center">{{ f.puerto or '—' }}</td>
              <td class="small">{{ f.servicio or '—' }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>

    <script>
      const RUN_ID = {{ run.id }};

      async function refreshScanStatus() {
        try {
          const r = await fetch(`/vulnerabilidades/scan/${RUN_ID}/status`);
          const data = await r.json();

          document.getElementById('current_stage').value = data.current_stage || '—';

          const bar = document.getElementById('progress_bar');
          bar.style.width = `${data.progress_pct || 0}%`;
          bar.textContent = `${data.progress_pct || 0}%`;

          document.getElementById('metric_findings').textContent = data.findings_streamed || 0;
          document.getElementById('metric_vulns').textContent = data.created_vulns || 0;
          document.getElementById('metric_plans').textContent = data.created_plans || 0;
          document.getElementById('metric_tool').textContent = data.current_tool || '—';
          document.getElementById('estado_badge').innerHTML = data.estado_badge_html || '';

          const tbody = document.getElementById('tbody_findings');
          tbody.innerHTML = '';
          (data.findings || []).forEach((f, idx) => {
            tbody.innerHTML += `
              <tr>
                <td class="text-center fw-bold">${idx + 1}</td>
                <td class="text-center">${f.fuente || '—'}</td>
                <td class="small">${f.titulo || '—'}</td>
                <td class="text-center">${f.severidad_badge_html || '—'}</td>
                <td class="text-center">${f.puerto || '—'}</td>
                <td class="small">${f.servicio || '—'}</td>
              </tr>
            `;
          });

          if (['finalizado', 'error', 'detenido'].includes(data.estado)) {
            document.getElementById('btn_stop').disabled = true;
            return;
          }
        } catch (e) {
          console.error(e);
        }

        setTimeout(refreshScanStatus, 2000);
      }

      document.getElementById('btn_stop').addEventListener('click', async () => {
        if (!confirm('¿Desea detener el escaneo en curso?')) return;

        const r = await fetch(`/vulnerabilidades/scan/${RUN_ID}/stop`, {method:'POST'});
        const data = await r.json();

        if (data.ok) {
          document.getElementById('btn_stop').disabled = true;
        }
      });

      window.addEventListener('DOMContentLoaded', refreshScanStatus);
    </script>
    """

    findings = VulnerabilityScanFinding.query.filter_by(run_id=run.id).order_by(VulnerabilityScanFinding.id.asc()).all()

    return vuln_scan_shell(
        f"Monitoreo del Escaneo #{run.id}",
        render_template_string(
            body,
            run=run,
            findings=findings,
            badge_estado_scan_html=badge_estado_scan_html,
            badge_severidad_html=badge_severidad_html
        )
    )

# ==========================
# NUEVA RUTA JSON DE ESTADO
# ==========================

@app.route('/vulnerabilidades/scan/<int:run_id>/status')
@login_required
def vuln_scan_status(run_id):
    run = VulnerabilityScanRun.query.get_or_404(run_id)
    findings = VulnerabilityScanFinding.query.filter_by(run_id=run.id).order_by(VulnerabilityScanFinding.id.asc()).all()

    payload = {
        "id": run.id,
        "estado": run.estado,
        "estado_badge_html": str(badge_estado_scan_html(run.estado)),
        "progress_pct": run.progress_pct or 0,
        "current_stage": run.current_stage or "",
        "current_tool": run.current_tool or "",
        "findings_streamed": run.findings_streamed or 0,
        "created_vulns": run.created_vulns or 0,
        "created_plans": run.created_plans or 0,
        "findings": [
            {
                "id": f.id,
                "fuente": f.fuente,
                "titulo": f.titulo,
                "severidad": f.severidad,
                "severidad_badge_html": str(badge_severidad_html(f.severidad)),
                "puerto": f.puerto or "—",
                "servicio": f.servicio or "—",
            }
            for f in findings
        ]
    }
    return jsonify(payload)

# ==========================
# NUEVA RUTA “PARAR ESCANEO
# ==========================

@app.route('/vulnerabilidades/scan/<int:run_id>/stop', methods=['POST'])
@login_required
def vuln_scan_stop(run_id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        return jsonify({"ok": False, "error": "No autorizado"}), 403

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        return jsonify({"ok": False, "error": "No autorizado"}), 403

    run = VulnerabilityScanRun.query.get_or_404(run_id)

    if run.estado not in ("pendiente", "ejecutando"):
        return jsonify({"ok": False, "error": "La corrida no está en ejecución"}), 400

    run.cancel_requested = True
    run.current_stage = "Solicitud de detención enviada"
    db.session.commit()

    # Intentar matar el proceso activo local (si existe)
    try:
        if run.active_pid:
            try:
                os.killpg(run.active_pid, signal.SIGTERM)
            except Exception:
                os.kill(run.active_pid, signal.SIGTERM)
    except Exception:
        pass

    # Marcar inmediatamente como detenido
    scan_mark_stopped(run.id, "Escaneo detenido manualmente por el usuario.")

    return jsonify({"ok": True})

# ==========================
# Matriz de corridas
# ==========================
@app.route('/vulnerabilidades/scan/runs')
@login_required
def vuln_scan_runs():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        flash("No tiene permiso para acceder a los reportes de escaneo.", "danger")
        return redirect(url_for('menu'))

    items = VulnerabilityScanRun.query.order_by(VulnerabilityScanRun.id.desc()).all()

    body = """
    <style>
      .scan-actions-cell{
        width:170px;
        min-width:170px;
        max-width:170px;
        text-align:center;
        vertical-align:middle !important;
      }

      .scan-actions-wrap{
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:center;
        gap:6px;
        width:100%;
        max-width:100%;
      }

      .scan-actions-wrap .btn{
        width:100%;
        max-width:125px;
        min-height:28px;
        padding:4px 8px !important;
        font-size:.70rem;
        font-weight:900;
        border-radius:999px !important;
        white-space:nowrap;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .soft-table th:last-child,
      .soft-table td:last-child{
        width:170px;
        min-width:170px;
        max-width:170px;
      }

      .soft-table{
        min-width:1250px;
      }

      @media (max-width:768px){
        .scan-actions-cell{
          width:150px;
          min-width:150px;
          max-width:150px;
        }

        .scan-actions-wrap .btn{
          max-width:115px;
          font-size:.68rem;
        }
      }
    </style>

    <div class="toolbar-actions justify-content-end mb-3">
      {% if user.role != 'auditor' %}
        <a href="{{ url_for('vuln_scan_new') }}" class="btn btn-primary rounded-pill px-4" onclick="showLoader()">
          ➕ Nuevo Escaneo
        </a>
      {% endif %}
    </div>

    <div class="soft-table-wrap">
      <div class="p-3 pb-0">
        <div class="section-title mb-2">Matriz de Reportes de Escaneo</div>
      </div>

      <div class="table-responsive px-3 pb-3">
        <table class="table table-hover align-middle soft-table mb-0">
          <thead>
            <tr>
              <th>ID</th>
              <th>Fecha</th>
              <th>Objetivo</th>
              <th>Tipo</th>
              <th>Modo</th>
              <th>Estado</th>
              <th>Total</th>
              <th>Críticas</th>
              <th>Altas</th>
              <th>Medias</th>
              <th>Bajas</th>
              <th class="scan-actions-cell">Acciones</th>
            </tr>
          </thead>

          <tbody>
            {% for it in items %}
            <tr>
              <td class="text-center fw-bold">{{ it.id }}</td>
              <td class="text-center">{{ it.created_at.strftime('%Y-%m-%d %H:%M') if it.created_at else '—' }}</td>
              <td class="small">{{ it.target }}</td>
              <td class="text-center">{{ it.target_type }}</td>
              <td class="text-center">{{ it.scanner_mode }}</td>
              <td class="text-center">{{ badge_estado_scan_html(it.estado) }}</td>
              <td class="text-center fw-bold">{{ it.total_hallazgos or 0 }}</td>
              <td class="text-center">{{ it.criticas or 0 }}</td>
              <td class="text-center">{{ it.altas or 0 }}</td>
              <td class="text-center">{{ it.medias or 0 }}</td>
              <td class="text-center">{{ it.bajas or 0 }}</td>

              <td class="scan-actions-cell">
                <div class="scan-actions-wrap">

                  {% if it.estado in ['pendiente', 'ejecutando', 'detenido'] %}
                    <a href="{{ url_for('vuln_scan_monitor', run_id=it.id) }}"
                       class="btn btn-primary btn-sm"
                       onclick="showLoader()">
                      Monitorear
                    </a>
                  {% endif %}

                  <a href="{{ url_for('vuln_scan_detail', run_id=it.id) }}"
                     class="btn btn-warning btn-sm"
                     onclick="showLoader()">
                    Ver
                  </a>

                  <a href="{{ url_for('vuln_scan_pdf', run_id=it.id) }}"
                     class="btn btn-success btn-sm"
                     target="_blank">
                    PDF
                  </a>

                  {% if user.role != 'auditor' and it.estado != 'ejecutando' %}
                    <a href="{{ url_for('vuln_scan_delete', run_id=it.id) }}"
                       class="btn btn-danger btn-sm"
                       onclick="return confirm('¿Eliminar esta corrida de escaneo?');">
                      Eliminar
                    </a>
                  {% endif %}

                </div>
              </td>
            </tr>

            {% else %}
            <tr>
              <td colspan="12" class="text-center text-muted py-4">
                No hay corridas registradas.
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    """

    return vuln_scan_shell(
        "Reportes de Escaneo",
        render_template_string(
            body,
            items=items,
            user=user,
            badge_estado_scan_html=badge_estado_scan_html
        )
    )

# ==========================
# Eliminar escaneos
# ==========================

@app.route('/vulnerabilidades/scan/<int:run_id>/delete')
@login_required
def vuln_scan_delete(run_id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar corridas.", "danger")
        return redirect(url_for('vuln_scan_runs'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        flash("No tiene permiso para eliminar corridas.", "danger")
        return redirect(url_for('vuln_scan_runs'))

    run = VulnerabilityScanRun.query.get_or_404(run_id)

    if run.estado in ("pendiente", "ejecutando"):
        flash("No puede eliminar una corrida mientras está en ejecución. Debe detenerla primero.", "danger")
        return redirect(url_for('vuln_scan_runs'))

    # Guardar rutas antes de borrar DB
    paths_to_delete = [
        run.archivo_resumen_json,
        run.archivo_reporte_pdf,
        run.archivo_log,
    ]

    base_dir = None
    try:
        if run.archivo_log:
            base_dir = os.path.dirname(run.archivo_log)
    except Exception:
        base_dir = None

    # Reintentos por bloqueo SQLite
    max_retries = 5
    last_error = None

    for attempt in range(max_retries):
        try:
            # MUY IMPORTANTE: limpiar cualquier transacción previa fallida
            db.session.rollback()

            # Volver a cargar la corrida en sesión limpia
            run = VulnerabilityScanRun.query.get(run_id)
            if not run:
                flash("La corrida ya había sido eliminada.", "info")
                return redirect(url_for('vuln_scan_runs'))

            # Marcar como eliminando para evitar operaciones concurrentes lógicas
            run.current_stage = "Eliminando corrida"
            run.current_tool = None
            run.cancel_requested = True
            run.active_pid = None
            run.active_command = None
            db.session.commit()

            db.session.rollback()

            # Borrado masivo de hallazgos asociados
            VulnerabilityScanFinding.query.filter_by(run_id=run_id).delete(synchronize_session=False)

            # Si tienes otras tablas hijas ligadas al run_id, aquí puedes agregarlas igual
            # Ejemplo:
            # ThreatModelFinding.query.filter_by(scan_run_id=run_id).delete(synchronize_session=False)

            db.session.commit()
            db.session.rollback()

            # Borrar corrida principal
            run = VulnerabilityScanRun.query.get(run_id)
            if run:
                db.session.delete(run)
                db.session.commit()

            # Borrar archivos físicos solo después del commit exitoso
            for path in paths_to_delete:
                try:
                    if path and os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass

            # Borrar directorio si existe
            try:
                if base_dir and os.path.isdir(base_dir):
                    shutil.rmtree(base_dir, ignore_errors=True)
            except Exception:
                pass

            flash("Corrida de escaneo eliminada correctamente.", "success")
            return redirect(url_for('vuln_scan_runs'))

        except Exception as e:
            last_error = e
            print(f"DEBUG DELETE SCAN intento {attempt + 1}/{max_retries}: {e}")
            db.session.rollback()
            time.sleep(1.2)

    flash(f"No se pudo eliminar la corrida por bloqueo de base de datos: {last_error}", "danger")
    return redirect(url_for('vuln_scan_runs'))

# ==========================
# Detalle de corrida
# ==========================
@app.route('/vulnerabilidades/scan/<int:run_id>')
@login_required
def vuln_scan_detail(run_id):
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        flash("No tiene permiso para ver el reporte.", "danger")
        return redirect(url_for('menu'))

    run = VulnerabilityScanRun.query.get_or_404(run_id)
    findings = VulnerabilityScanFinding.query.filter_by(run_id=run.id).order_by(VulnerabilityScanFinding.id.asc()).all()

    body = """
    <div class="toolbar-actions justify-content-end mb-3">
     {% if run.estado in ['pendiente', 'ejecutando', 'detenido'] %}
        <a href="{{ url_for('vuln_scan_monitor', run_id=run.id) }}"
           class="btn btn-primary rounded-pill px-4"
           onclick="showLoader()">
          📡 Monitorear
        </a>
        <a href="{{ url_for('threat_model_asset_view') }}?activo={{ run.target|urlencode }}"
           class="btn btn-primary rounded-pill px-4"
           onclick="showLoader()">
          🧭 MITRE ATT&CK
        </a>
     {% endif %}
      <a href="{{ url_for('vuln_scan_pdf', run_id=run.id) }}" class="btn btn-success rounded-pill px-4" target="_blank">
        📄 PDF
      </a>
      <a href="{{ url_for('vuln_scan_runs') }}" class="btn btn-outline-secondary rounded-pill px-4" onclick="showLoader()">
        ⬅ Volver a Reportes
      </a>
    </div>

    <div class="row g-3 mb-3">
      <div class="col-lg-2 col-md-4 col-6">
        <div class="metric-box">
          <div class="metric-label">Objetivo</div>
          <div class="small fw-bold mt-2">{{ run.target }}</div>
        </div>
      </div>
      <div class="col-lg-2 col-md-4 col-6">
        <div class="metric-box">
          <div class="metric-label">Tipo</div>
          <div class="metric-value">{{ run.target_type }}</div>
        </div>
      </div>
      <div class="col-lg-2 col-md-4 col-6">
        <div class="metric-box">
          <div class="metric-label">Modo</div>
          <div class="metric-value">{{ run.scanner_mode }}</div>
        </div>
      </div>
      <div class="col-lg-2 col-md-4 col-6">
        <div class="metric-box">
          <div class="metric-label">Estado</div>
          <div class="mt-2">{{ badge_estado_scan_html(run.estado) }}</div>
        </div>
      </div>
      <div class="col-lg-2 col-md-4 col-6">
        <div class="metric-box">
          <div class="metric-label">Total Hallazgos</div>
          <div class="metric-value">{{ run.total_hallazgos or 0 }}</div>
        </div>
      </div>
      <div class="col-lg-2 col-md-4 col-6">
        <div class="metric-box">
          <div class="metric-label">Responsable</div>
          <div class="small fw-bold mt-2">{{ run.responsable_asignado or '—' }}</div>
        </div>
      </div>
    </div>

    <div class="row g-3 mb-3">
      <div class="col-md-3"><div class="metric-box"><div class="metric-label">Críticas</div><div class="metric-value">{{ run.criticas or 0 }}</div></div></div>
      <div class="col-md-3"><div class="metric-box"><div class="metric-label">Altas</div><div class="metric-value">{{ run.altas or 0 }}</div></div></div>
      <div class="col-md-3"><div class="metric-box"><div class="metric-label">Medias</div><div class="metric-value">{{ run.medias or 0 }}</div></div></div>
      <div class="col-md-3"><div class="metric-box"><div class="metric-label">Bajas</div><div class="metric-value">{{ run.bajas or 0 }}</div></div></div>
    </div>

    <div class="soft-table-wrap mb-3">
      <div class="p-3 pb-0">
        <div class="section-title mb-2">🧾 Hallazgos del Escaneo</div>
      </div>

      <div class="table-responsive px-3 pb-3">
        <table class="table table-hover align-middle soft-table mb-0">
          <thead>
            <tr>
              <th>#</th>
              <th>Fuente</th>
              <th>Título / Evidencia</th>
              <th>Severidad</th>
              <th>Puerto</th>
              <th>Servicio</th>
              <th>Registro</th>
            </tr>
          </thead>
          <tbody>
            {% for f in findings %}
            <tr>
              <td class="text-center fw-bold">{{ loop.index }}</td>
              <td class="text-center">{{ f.fuente }}</td>
              <td class="small">
                <div class="fw-bold">{{ f.titulo }}</div>
                <div class="text-muted">{{ f.descripcion or '—' }}</div>
                <div class="mt-1"><b>Evidencia:</b> {{ f.evidencia or '—' }}</div>
              </td>
              <td class="text-center">{{ badge_severidad_html(f.severidad) }}</td>
              <td class="text-center">{{ f.puerto or '—' }}</td>
              <td class="small">{{ f.servicio or '—' }}</td>
              <td class="text-center">
                {% if f.vulnerabilidad_registro_id %}
                  <a href="{{ url_for('vulnerabilidad_edit', id=f.vulnerabilidad_registro_id) }}"
                     class="btn btn-warning btn-sm rounded-pill px-3"
                     onclick="showLoader()">
                    Abrir
                  </a>
                {% else %}
                  —
                {% endif %}
              </td>
            </tr>
            {% else %}
            <tr><td colspan="7" class="text-center text-muted py-4">No hay hallazgos cargados.</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>

    {% if run.salida_consola %}
    <div class="glass-card p-4">
      <div class="section-title">Log resumido</div>
      <pre style="white-space: pre-wrap; margin-bottom:0;">{{ run.salida_consola }}</pre>
    </div>
    {% endif %}
    """
    return vuln_scan_shell(
        f"Detalle del Reporte #{run.id}",
        render_template_string(
            body,
            run=run,
            findings=findings,
            badge_estado_scan_html=badge_estado_scan_html,
            badge_severidad_html=badge_severidad_html
        )
    )


# ==========================
# PDF de corrida
# ==========================
@app.route('/vulnerabilidades/scan/<int:run_id>/pdf')
@login_required
def vuln_scan_pdf(run_id):
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        flash("No tiene permiso para descargar el PDF.", "danger")
        return redirect(url_for('menu'))

    run = VulnerabilityScanRun.query.get_or_404(run_id)

    pdf_path = run.archivo_reporte_pdf
    if not pdf_path or not os.path.exists(pdf_path):
        pdf_path = build_vulnerability_scan_pdf(run.id)
        run.archivo_reporte_pdf = pdf_path
        db.session.commit()

    return send_file(
        pdf_path,
        as_attachment=False,
        download_name=f"Reporte_Vulnerabilidades_{run.id}.pdf",
        mimetype="application/pdf"
    )

# ==========================
# Importación del Nessus
# ==========================

@app.route('/vulnerabilidades/threat_model/nessus_import', methods=['GET', 'POST'])
@login_required
def threat_model_nessus_import():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede importar archivos Nessus.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Vulnerabilidades"):
        flash("No tiene permiso para importar archivos Nessus.", "danger")
        return redirect(url_for('vulnerabilidades_matriz'))

    if request.method == 'POST':
        target = (request.form.get('target') or '').strip()
        responsable = (request.form.get('responsable') or '').strip()
        crear_vulns = bool(request.form.get('crear_vulns'))
        crear_planes = bool(request.form.get('crear_planes'))
        archivo = request.files.get('archivo_nessus')

        if not target:
            flash("Debe indicar el activo u objetivo asociado.", "danger")
            return redirect(url_for('threat_model_nessus_import'))

        if not archivo or not archivo.filename.lower().endswith('.nessus'):
            flash("Debe cargar un archivo .nessus válido.", "danger")
            return redirect(url_for('threat_model_nessus_import'))

        cfg = _scan_cfg()

        run = VulnerabilityScanRun(
            target=target,
            target_type='url' if detectar_tipo_objetivo(target) == 'url' else 'ip',
            scan_mode='nessus_import',
            scanner_mode=cfg.modo,
            estado='finalizado',
            fecha_inicio=datetime.utcnow(),
            fecha_fin=datetime.utcnow(),
            ejecutado_por=getattr(user, 'username', None),
            responsable_asignado=responsable or getattr(user, 'username', None),
            progress_pct=100,
            current_stage="Importación Nessus finalizada",
            current_tool="nessus"
        )
        db.session.add(run)
        db.session.commit()

        run_dir = scan_run_dir(run.id, target)
        nessus_path = scan_output_file(run_dir, "nessus_import", "nessus")
        archivo.save(nessus_path)

        findings = parse_nessus_xml(nessus_path)
        guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns=crear_vulns, crear_planes=crear_planes)

        resumir_hallazgos_run(run)
        resumen_path = scan_output_file(run_dir, "summary", "json")
        run.archivo_resumen_json = resumen_path
        run.archivo_log = nessus_path
        run.archivo_reporte_pdf = build_vulnerability_scan_pdf(run.id)
        db.session.commit()

        flash("Archivo Nessus importado correctamente y modelado contra MITRE ATT&CK.", "success")
        return redirect(url_for('threat_model_dashboard'))

    body = """
    <div class="glass-card p-4 mt-2">
      <div class="section-title">📥 Importar archivo Nessus</div>

      <form method="post" enctype="multipart/form-data">
        <div class="row g-3">
          <div class="col-md-6">
            <label class="form-label">Activo / Objetivo</label>
            <input name="target" class="form-control" placeholder="https://midominio.com o 192.168.1.10" required>
          </div>

          <div class="col-md-6">
            <label class="form-label">Responsable</label>
            <input name="responsable" class="form-control" value="{{ current_user.username if current_user.is_authenticated else '' }}">
          </div>

          <div class="col-md-12">
            <label class="form-label">Archivo .nessus</label>
            <input type="file" name="archivo_nessus" class="form-control" accept=".nessus" required>
          </div>

          <div class="col-md-6">
            <div class="form-check mt-3">
              <input class="form-check-input" type="checkbox" name="crear_vulns" id="crear_vulns" checked>
              <label class="form-check-label" for="crear_vulns">Crear registros en la matriz de vulnerabilidades</label>
            </div>
          </div>

          <div class="col-md-6">
            <div class="form-check mt-3">
              <input class="form-check-input" type="checkbox" name="crear_planes" id="crear_planes" checked>
              <label class="form-check-label" for="crear_planes">Crear planes de remediación automáticamente</label>
            </div>
          </div>

          <div class="col-12">
            <div class="toolbar-actions justify-content-center mt-3">
              <button class="btn btn-primary rounded-pill px-4">Importar</button>
              <a href="{{ url_for('vulnerabilidades_matriz') }}" class="btn btn-outline-secondary rounded-pill px-4">Cancelar</a>
            </div>
          </div>
        </div>
      </form>
    </div>
    """
    return vuln_scan_shell("📥 Importación Nessus + MITRE ATT&CK", render_template_string(body, current_user=current_user))

# ==========================================================================================================================================
#                                                           Fin Módulo Registro de Vulnerabilidades
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                       Módulo Modelamiento de Amenazas
# ==========================================================================================================================================


class ThreatModelEntry(db.Model):
    __tablename__ = "threat_model_entries"

    id = db.Column(db.Integer, primary_key=True)

    # Relaciones con tu ecosistema actual
    run_id = db.Column(db.Integer, db.ForeignKey("vulnerability_scan_runs.id", ondelete="SET NULL"), nullable=True)
    finding_id = db.Column(db.Integer, db.ForeignKey("vulnerability_scan_findings.id", ondelete="SET NULL"), nullable=True)
    vulnerabilidad_registro_id = db.Column(
        db.Integer,
        db.ForeignKey("vulnerabilidades_registro.id", ondelete="SET NULL"),
        nullable=True
    )

    # Datos del contexto
    activo = db.Column(db.String(200), nullable=False)
    herramienta = db.Column(db.String(50), nullable=False)   # nikto / nessus / nuclei / nmap / testssl
    vulnerabilidad = db.Column(db.String(500), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    impacto = db.Column(db.Text, nullable=True)

    # Estado
    severidad = db.Column(db.String(20), nullable=True)
    confianza = db.Column(db.Integer, default=70)   # 0..100

    # trazabilidad
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    tecnicas = db.relationship(
        "ThreatModelTechnique",
        backref="threat_entry",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    vulnerabilidad_registro = db.relationship(
        "VulnerabilidadRegistro",
        backref=db.backref("threat_models", lazy="selectin")
    )


class ThreatModelTechnique(db.Model):
    __tablename__ = "threat_model_techniques"

    id = db.Column(db.Integer, primary_key=True)
    threat_entry_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_model_entries.id", ondelete="CASCADE"),
        nullable=False
    )

    mitre_technique_id = db.Column(db.String(20), nullable=False)      # T1190
    mitre_technique_name = db.Column(db.String(255), nullable=False)   # Exploit Public-Facing Application
    mitre_tactic_id = db.Column(db.String(20), nullable=True)          # TA0001
    mitre_tactic_name = db.Column(db.String(100), nullable=False)      # Initial Access

    rationale = db.Column(db.Text, nullable=True)
    score = db.Column(db.Integer, default=50)  # score para Navigator / heatmap

class ThreatModelUnmapped(db.Model):
    __tablename__ = "threat_model_unmapped"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, nullable=True)
    finding_id = db.Column(db.Integer, nullable=True)
    activo = db.Column(db.String(200), nullable=True)
    herramienta = db.Column(db.String(50), nullable=True)
    severidad = db.Column(db.String(20), nullable=True)
    titulo = db.Column(db.String(500), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    evidencia = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
            return f"<ConfigImpactoResidual {self.min}-{self.max} => bajar {self.bajar}>"

class ThreatModelUnmappedClassification(db.Model):
    __tablename__ = "threat_model_unmapped_classifications"

    id = db.Column(db.Integer, primary_key=True)

    unmapped_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_model_unmapped.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    owasp_category = db.Column(db.String(120), nullable=True)
    cwe_id = db.Column(db.String(40), nullable=True)
    cwe_name = db.Column(db.String(255), nullable=True)
    capec_id = db.Column(db.String(40), nullable=True)
    capec_name = db.Column(db.String(255), nullable=True)
    iso_control = db.Column(db.String(120), nullable=True)
    iso_control_name = db.Column(db.String(255), nullable=True)
    nist_function = db.Column(db.String(80), nullable=True)
    nist_category = db.Column(db.String(120), nullable=True)

    recomendacion = db.Column(db.Text, nullable=True)
    rationale = db.Column(db.Text, nullable=True)
    confianza = db.Column(db.Integer, default=50)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    unmapped = db.relationship(
        "ThreatModelUnmapped",
        backref=db.backref(
            "clasificacion_complementaria",
            uselist=False,
            cascade="all, delete-orphan"
        )
    )


def init_threat_model_unmapped_classifications():
    try:
        with app.app_context():
            db.create_all()
    except Exception as e:
        print("No fue posible inicializar threat_model_unmapped_classifications:", repr(e))


init_threat_model_unmapped_classifications()


ATTACK_DOMAIN = "enterprise-attack"

ATTACK_TACTIC_ORDER = [
    "Reconnaissance",
    "Resource Development",
    "Initial Access",
    "Execution",
    "Persistence",
    "Privilege Escalation",
    "Defense Evasion",
    "Credential Access",
    "Discovery",
    "Lateral Movement",
    "Collection",
    "Command and Control",
    "Exfiltration",
    "Impact"
]

MITRE_PENDING_TACTIC = "Pendiente de mapeo MITRE"

MITRE_ATTACK_MAPPING_RULES = [
    # =========================
    # Discovery / Recon
    # =========================
    {
        "keywords": [
            "directory indexing enabled",
            "directory indexing",
            "directory listing",
            "autoindex",
            "index of /",
            "listing of directories",
            "file listing",
            "browseable directory",
            "directory browsing"
        ],
        "patterns": [
            r"\bindex of\s*/",
            r"\bdirectory\s+(listing|indexing|browsing)\b"
        ],
        "technique_id": "T1083",
        "technique_name": "File and Directory Discovery",
        "tactic_id": "TA0007",
        "tactic_name": "Discovery",
        "impacto": "Exposición de información sensible por enumeración de directorios y archivos.",
        "score": 55,
        "confidence": 92,
        "category": "discovery"
    },
    {
        "keywords": [
            "server leaks version",
            "information disclosure",
            "banner disclosure",
            "version disclosure",
            "x-powered-by",
            "server header",
            "trace method",
            "debug enabled",
            "stack trace",
            "verbose error",
            "discloses version",
            "phpinfo",
            "robots.txt"
        ],
        "patterns": [
            r"\b(server|x-powered-by)\b.*\b(version|header)\b",
            r"\b(verbose|debug|stack trace|phpinfo)\b",
            r"\brobots\.txt\b"
        ],
        "technique_id": "T1592",
        "technique_name": "Gather Victim Host Information",
        "tactic_id": "TA0043",
        "tactic_name": "Reconnaissance",
        "impacto": "Divulgación de información útil para reconocimiento y preparación del ataque.",
        "score": 40,
        "confidence": 82,
        "category": "recon"
    },

    # =========================
    # Initial Access
    # =========================
    {
        "keywords": [
            "outdated apache",
            "apache outdated",
            "obsolete apache",
            "old apache version",
            "apache httpd",
            "unsupported apache",
            "apache version",
            "outdated nginx",
            "outdated tomcat",
            "unsupported web server",
            "web server multiple vulnerabilities",
            "multiple vulnerabilities"
        ],
        "patterns": [
            r"\b(apache|nginx|tomcat|iis|httpd)\b.*\b(outdated|obsolete|unsupported|multiple vulnerabilities)\b",
            r"\bunsupported\b.*\b(version|release)\b"
        ],
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic_id": "TA0001",
        "tactic_name": "Initial Access",
        "impacto": "Posible explotación remota sobre aplicación o servicio público expuesto.",
        "score": 80,
        "confidence": 88,
        "category": "public_facing"
    },
    {
        "keywords": [
            "sql injection",
            "sqli",
            "blind sql injection",
            "union select",
            "time based sql injection",
            "error based sql injection"
        ],
        "patterns": [
            r"\bsql\b.*\binjection\b",
            r"\bunion\s+select\b"
        ],
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic_id": "TA0001",
        "tactic_name": "Initial Access",
        "impacto": "Compromiso de la aplicación por explotación de entrada insegura.",
        "score": 96,
        "confidence": 97,
        "category": "public_facing"
    },
    {
        "keywords": [
            "remote code execution",
            "rce",
            "command injection",
            "os command injection",
            "code execution",
            "arbitrary command execution",
            "deserialization",
            "insecure deserialization"
        ],
        "patterns": [
            r"\bremote\b.*\bcode\b.*\bexecution\b",
            r"\brce\b",
            r"\bcommand\b.*\binjection\b",
            r"\bdeserialization\b"
        ],
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic_id": "TA0001",
        "tactic_name": "Initial Access",
        "impacto": "Posible ejecución remota de código sobre la aplicación expuesta.",
        "score": 100,
        "confidence": 98,
        "category": "public_facing"
    },
    {
        "keywords": [
            "authentication bypass",
            "auth bypass",
            "bypass authentication",
            "improper authentication",
            "missing authentication",
            "unauthenticated access",
            "admin panel",
            "admin login",
            "exposed admin panel"
        ],
        "patterns": [
            r"\b(auth|authentication)\b.*\b(bypass|missing|improper)\b",
            r"\bunauthenticated\b.*\b(access|request)\b",
            r"\badmin\b.*\b(panel|login|console)\b"
        ],
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic_id": "TA0001",
        "tactic_name": "Initial Access",
        "impacto": "Acceso no autorizado por bypass o ausencia de autenticación.",
        "score": 95,
        "confidence": 95,
        "category": "public_facing"
    },
    {
        "keywords": [
            "file upload",
            "arbitrary file upload",
            "unrestricted file upload",
            "upload bypass",
            "malicious upload"
        ],
        "patterns": [
            r"\b(file|arbitrary|malicious)\b.*\bupload\b",
            r"\bupload\b.*\b(bypass|unrestricted)\b"
        ],
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic_id": "TA0001",
        "tactic_name": "Initial Access",
        "impacto": "Carga de archivo malicioso con potencial de ejecución remota.",
        "score": 92,
        "confidence": 94,
        "category": "public_facing"
    },

    # =========================
    # Credentials
    # =========================
    {
        "keywords": [
            "default credentials",
            "default password",
            "default login",
            "weak credentials",
            "anonymous login",
            "guest login",
            "guest account",
            "hardcoded credentials"
        ],
        "patterns": [
            r"\bdefault\b.*\b(password|credential|login)\b",
            r"\b(guest|anonymous)\b.*\b(login|access|account)\b"
        ],
        "technique_id": "T1078",
        "technique_name": "Valid Accounts",
        "tactic_id": "TA0001",
        "tactic_name": "Initial Access",
        "impacto": "Acceso indebido mediante cuentas válidas o credenciales por defecto.",
        "score": 85,
        "confidence": 94,
        "category": "credentials"
    },

    # =========================
    # Traversal / Files
    # =========================
    {
        "keywords": [
            "path traversal",
            "directory traversal",
            "../",
            "local file inclusion",
            "lfi",
            "remote file inclusion",
            "rfi",
            "file inclusion",
            "backup file",
            "exposed backup"
        ],
        "patterns": [
            r"\b(path|directory)\b.*\btraversal\b",
            r"\b(local|remote)\b.*\bfile inclusion\b",
            r"\bbackup\b.*\b(file|archive|zip|tar|sql)\b"
        ],
        "technique_id": "T1006",
        "technique_name": "Path Traversal",
        "tactic_id": "TA0009",
        "tactic_name": "Collection",
        "impacto": "Acceso no autorizado a archivos sensibles del sistema o aplicación.",
        "score": 88,
        "confidence": 92,
        "category": "traversal"
    },

    # =========================
    # Execution
    # =========================
    {
        "keywords": [
            "cross-site scripting",
            "xss",
            "stored xss",
            "reflected xss",
            "dom xss"
        ],
        "patterns": [
            r"\bxss\b",
            r"\bcross[\s\-]?site scripting\b"
        ],
        "technique_id": "T1059",
        "technique_name": "Command and Scripting Interpreter",
        "tactic_id": "TA0002",
        "tactic_name": "Execution",
        "impacto": "Ejecución de scripts maliciosos en el contexto del navegador o de la aplicación.",
        "score": 75,
        "confidence": 78,
        "category": "execution"
    },

    # =========================
    # TLS / Weak Config
    # =========================
    {
        "keywords": [
            "tls 1.0",
            "tls 1.1",
            "deprecated protocol",
            "weak cipher",
            "weak ciphers",
            "ssl weak",
            "weak ssl",
            "insecure renegotiation",
            "obsolete ssl",
            "self-signed certificate",
            "expired certificate",
            "certificate expired"
        ],
        "patterns": [
            r"\btls\s*1\.[01]\b",
            r"\bweak\b.*\b(cipher|ciphersuite|ssl|tls)\b",
            r"\b(self signed|expired)\b.*\bcertificate\b"
        ],
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic_id": "TA0001",
        "tactic_name": "Initial Access",
        "impacto": "Debilidad criptográfica o de configuración que incrementa superficie de explotación del servicio expuesto.",
        "score": 50,
        "confidence": 70,
        "category": "tls"
    },

    # =========================
    # Security Headers / Hardening
    # =========================
    {
        "keywords": [
            "missing security header",
            "missing x-frame-options",
            "missing content-security-policy",
            "missing x-content-type-options",
            "cookie without httponly",
            "cookie without secure flag"
        ],
        "patterns": [
            r"\bmissing\b.*\b(header|x frame options|content security policy|x content type options)\b",
            r"\bcookie\b.*\b(httponly|secure)\b"
        ],
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic_id": "TA0001",
        "tactic_name": "Initial Access",
        "impacto": "Configuración insegura que facilita explotación o abuso de la aplicación pública.",
        "score": 45,
        "confidence": 60,
        "category": "hardening"
    }
]

COMPLEMENTARY_CLASSIFICATION_RULES = [
    {
        "keywords": [
            "missing security header",
            "x-frame-options",
            "content-security-policy",
            "x-content-type-options",
            "strict-transport-security",
            "hsts",
            "security header",
            "cookie without httponly",
            "cookie without secure",
            "httponly",
            "secure flag"
        ],
        "patterns": [
            r"\bmissing\b.*\b(header|security header)\b",
            r"\bcontent[\s\-]?security[\s\-]?policy\b",
            r"\bx[\s\-]?frame[\s\-]?options\b",
            r"\bcookie\b.*\b(httponly|secure)\b"
        ],
        "owasp": "A05:2021 - Security Misconfiguration",
        "cwe_id": "CWE-693",
        "cwe_name": "Protection Mechanism Failure",
        "capec_id": "CAPEC-100",
        "capec_name": "Overflow Buffers / Security Mechanism Abuse",
        "iso_control": "A.8.9",
        "iso_control_name": "Gestión de la configuración",
        "nist_function": "Protect",
        "nist_category": "PR.PS - Platform Security",
        "recomendacion": "Definir y aplicar cabeceras de seguridad HTTP, endurecer cookies y validar configuración segura del servicio web.",
        "confianza": 90
    },
    {
        "keywords": [
            "directory listing",
            "directory indexing",
            "index of /",
            "directory browsing",
            "autoindex"
        ],
        "patterns": [
            r"\bindex of\s*/",
            r"\bdirectory\s+(listing|indexing|browsing)\b"
        ],
        "owasp": "A05:2021 - Security Misconfiguration",
        "cwe_id": "CWE-548",
        "cwe_name": "Exposure of Information Through Directory Listing",
        "capec_id": "CAPEC-116",
        "capec_name": "Excavation",
        "iso_control": "A.8.9",
        "iso_control_name": "Gestión de la configuración",
        "nist_function": "Protect",
        "nist_category": "PR.PS - Platform Security",
        "recomendacion": "Deshabilitar el listado de directorios, restringir navegación no autorizada y revisar exposición de archivos sensibles.",
        "confianza": 95
    },
    {
        "keywords": [
            "tls 1.0",
            "tls 1.1",
            "weak cipher",
            "weak ciphers",
            "ssl",
            "deprecated protocol",
            "expired certificate",
            "self-signed certificate",
            "certificate expired"
        ],
        "patterns": [
            r"\btls\s*1\.[01]\b",
            r"\bweak\b.*\b(cipher|ssl|tls)\b",
            r"\b(expired|self signed|self-signed)\b.*\bcertificate\b"
        ],
        "owasp": "A02:2021 - Cryptographic Failures",
        "cwe_id": "CWE-326",
        "cwe_name": "Inadequate Encryption Strength",
        "capec_id": "CAPEC-217",
        "capec_name": "Exploiting Incorrectly Configured SSL/TLS",
        "iso_control": "A.8.24",
        "iso_control_name": "Uso de criptografía",
        "nist_function": "Protect",
        "nist_category": "PR.DS - Data Security",
        "recomendacion": "Deshabilitar protocolos obsoletos, eliminar cifrados débiles y renovar certificados inseguros o vencidos.",
        "confianza": 92
    },
    {
        "keywords": [
            "information disclosure",
            "version disclosure",
            "server leaks version",
            "x-powered-by",
            "banner disclosure",
            "verbose error",
            "stack trace",
            "debug enabled",
            "phpinfo"
        ],
        "patterns": [
            r"\b(version|banner|information)\b.*\b(disclosure|leak)\b",
            r"\bx[\s\-]?powered[\s\-]?by\b",
            r"\b(stack trace|debug|phpinfo)\b"
        ],
        "owasp": "A05:2021 - Security Misconfiguration",
        "cwe_id": "CWE-200",
        "cwe_name": "Exposure of Sensitive Information to an Unauthorized Actor",
        "capec_id": "CAPEC-118",
        "capec_name": "Collect and Analyze Information",
        "iso_control": "A.8.12",
        "iso_control_name": "Prevención de fuga de datos",
        "nist_function": "Identify",
        "nist_category": "ID.RA - Risk Assessment",
        "recomendacion": "Reducir banners, ocultar versiones, deshabilitar mensajes técnicos detallados y controlar la información expuesta.",
        "confianza": 88
    },
    {
        "keywords": [
            "default credentials",
            "default password",
            "weak password",
            "anonymous login",
            "guest login",
            "hardcoded credentials",
            "missing authentication",
            "authentication bypass"
        ],
        "patterns": [
            r"\bdefault\b.*\b(password|credential|login)\b",
            r"\b(anonymous|guest)\b.*\b(login|access)\b",
            r"\bauthentication\b.*\b(bypass|missing|weak)\b"
        ],
        "owasp": "A07:2021 - Identification and Authentication Failures",
        "cwe_id": "CWE-287",
        "cwe_name": "Improper Authentication",
        "capec_id": "CAPEC-115",
        "capec_name": "Authentication Bypass",
        "iso_control": "A.5.17",
        "iso_control_name": "Información de autenticación",
        "nist_function": "Protect",
        "nist_category": "PR.AA - Identity Management, Authentication and Access Control",
        "recomendacion": "Eliminar credenciales por defecto, fortalecer autenticación, aplicar MFA y validar controles de acceso.",
        "confianza": 94
    },
    {
        "keywords": [
            "sql injection",
            "sqli",
            "union select",
            "blind sql injection"
        ],
        "patterns": [
            r"\bsql\b.*\binjection\b",
            r"\bunion\s+select\b"
        ],
        "owasp": "A03:2021 - Injection",
        "cwe_id": "CWE-89",
        "cwe_name": "SQL Injection",
        "capec_id": "CAPEC-66",
        "capec_name": "SQL Injection",
        "iso_control": "A.8.28",
        "iso_control_name": "Codificación segura",
        "nist_function": "Protect",
        "nist_category": "PR.PS - Platform Security",
        "recomendacion": "Usar consultas parametrizadas, validar entradas, aplicar controles ORM seguros y pruebas de seguridad en desarrollo.",
        "confianza": 98
    },
    {
        "keywords": [
            "cross-site scripting",
            "xss",
            "stored xss",
            "reflected xss",
            "dom xss"
        ],
        "patterns": [
            r"\bxss\b",
            r"\bcross[\s\-]?site scripting\b"
        ],
        "owasp": "A03:2021 - Injection",
        "cwe_id": "CWE-79",
        "cwe_name": "Cross-site Scripting",
        "capec_id": "CAPEC-63",
        "capec_name": "Cross-Site Scripting",
        "iso_control": "A.8.28",
        "iso_control_name": "Codificación segura",
        "nist_function": "Protect",
        "nist_category": "PR.PS - Platform Security",
        "recomendacion": "Validar y codificar salidas, aplicar CSP, sanitizar entradas y proteger formularios frente a scripts maliciosos.",
        "confianza": 96
    },
    {
        "keywords": [
            "path traversal",
            "directory traversal",
            "../",
            "local file inclusion",
            "lfi",
            "remote file inclusion",
            "rfi"
        ],
        "patterns": [
            r"\b(path|directory)\b.*\btraversal\b",
            r"\b(local|remote)\b.*\bfile inclusion\b",
            r"\.\./"
        ],
        "owasp": "A01:2021 - Broken Access Control",
        "cwe_id": "CWE-22",
        "cwe_name": "Improper Limitation of a Pathname to a Restricted Directory",
        "capec_id": "CAPEC-126",
        "capec_name": "Path Traversal",
        "iso_control": "A.8.3",
        "iso_control_name": "Restricción de acceso a la información",
        "nist_function": "Protect",
        "nist_category": "PR.AA - Identity Management, Authentication and Access Control",
        "recomendacion": "Restringir rutas permitidas, validar nombres de archivo, aplicar listas blancas y evitar acceso directo a directorios sensibles.",
        "confianza": 96
    },
    {
        "keywords": [
            "remote code execution",
            "rce",
            "command injection",
            "os command injection",
            "arbitrary command execution"
        ],
        "patterns": [
            r"\bremote\b.*\bcode\b.*\bexecution\b",
            r"\brce\b",
            r"\bcommand\b.*\binjection\b"
        ],
        "owasp": "A03:2021 - Injection",
        "cwe_id": "CWE-78",
        "cwe_name": "OS Command Injection",
        "capec_id": "CAPEC-88",
        "capec_name": "OS Command Injection",
        "iso_control": "A.8.28",
        "iso_control_name": "Codificación segura",
        "nist_function": "Protect",
        "nist_category": "PR.PS - Platform Security",
        "recomendacion": "Eliminar ejecución directa de comandos, validar entradas, usar APIs seguras y aislar procesos con mínimos privilegios.",
        "confianza": 98
    }
]


def clasificar_hallazgo_no_mapeado_complementario(item):
    haystack = tm_normalize_text(
        item.titulo,
        item.descripcion,
        item.evidencia,
        item.herramienta,
        item.severidad
    )

    mejor = None
    mejor_score = 0
    razones = []

    for rule in COMPLEMENTARY_CLASSIFICATION_RULES:
        score = 0
        razones_regla = []

        for kw in rule.get("keywords", []):
            kw_norm = tm_normalize_text(kw)
            if kw_norm and kw_norm in haystack:
                score += 12
                razones_regla.append(f"Palabra clave: {kw}")

        for pat in rule.get("patterns", []):
            try:
                if re.search(pat, haystack, re.I):
                    score += 18
                    razones_regla.append(f"Patrón: {pat}")
            except Exception:
                pass

        if score > mejor_score:
            mejor_score = score
            mejor = rule
            razones = razones_regla

    if not mejor:
        return {
            "owasp_category": "Sin clasificación OWASP concluyente",
            "cwe_id": "N/A",
            "cwe_name": "No determinado",
            "capec_id": "N/A",
            "capec_name": "No determinado",
            "iso_control": "A.5.7",
            "iso_control_name": "Inteligencia de amenazas",
            "nist_function": "Identify",
            "nist_category": "ID.RA - Risk Assessment",
            "recomendacion": "Revisar manualmente el hallazgo, validar impacto técnico y definir tratamiento de riesgo.",
            "rationale": "No se encontró una coincidencia fuerte con las reglas complementarias configuradas.",
            "confianza": 35
        }

    confianza = min(100, int(mejor.get("confianza", 50)) + min(10, mejor_score // 10))

    return {
        "owasp_category": mejor.get("owasp"),
        "cwe_id": mejor.get("cwe_id"),
        "cwe_name": mejor.get("cwe_name"),
        "capec_id": mejor.get("capec_id"),
        "capec_name": mejor.get("capec_name"),
        "iso_control": mejor.get("iso_control"),
        "iso_control_name": mejor.get("iso_control_name"),
        "nist_function": mejor.get("nist_function"),
        "nist_category": mejor.get("nist_category"),
        "recomendacion": mejor.get("recomendacion"),
        "rationale": "; ".join(razones) if razones else "Coincidencia por contexto técnico del hallazgo.",
        "confianza": confianza
    }


def guardar_clasificacion_complementaria_unmapped(item):
    data = clasificar_hallazgo_no_mapeado_complementario(item)

    existente = ThreatModelUnmappedClassification.query.filter_by(
        unmapped_id=item.id
    ).first()

    if not existente:
        existente = ThreatModelUnmappedClassification(unmapped_id=item.id)
        db.session.add(existente)

    existente.owasp_category = data.get("owasp_category")
    existente.cwe_id = data.get("cwe_id")
    existente.cwe_name = data.get("cwe_name")
    existente.capec_id = data.get("capec_id")
    existente.capec_name = data.get("capec_name")
    existente.iso_control = data.get("iso_control")
    existente.iso_control_name = data.get("iso_control_name")
    existente.nist_function = data.get("nist_function")
    existente.nist_category = data.get("nist_category")
    existente.recomendacion = data.get("recomendacion")
    existente.rationale = data.get("rationale")
    existente.confianza = data.get("confianza") or 50

    return existente

def tm_normalize_text(*parts):
    txt = " ".join([(str(p) if p is not None else "") for p in parts]).strip().lower()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = txt.replace("_", " ").replace("-", " ")
    txt = re.sub(r"[^a-z0-9./:# ]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def tm_deduplicate_mappings(items):
    unique = OrderedDict()
    for it in items:
        key = (it["technique_id"], it["tactic_id"])
        prev = unique.get(key)
        if not prev or (it.get("confidence", 0) > prev.get("confidence", 0)):
            unique[key] = it
    return list(unique.values())


def tm_map_finding_to_mitre(hallazgo: dict):
    titulo = hallazgo.get("titulo") or ""
    descripcion = hallazgo.get("descripcion") or ""
    evidencia = hallazgo.get("evidencia") or ""
    recomendacion = hallazgo.get("recomendacion_base") or ""
    servicio = hallazgo.get("servicio") or ""
    severidad = (hallazgo.get("severidad") or "").strip()
    cve = (hallazgo.get("cve") or "").strip()

    haystack = tm_normalize_text(titulo, descripcion, evidencia, recomendacion, servicio, cve)
    ctx = tm_detect_context(haystack)
    matches = []

    for rule in MITRE_ATTACK_MAPPING_RULES:
        best_reason = None

        # 1) match por keywords
        matched_keywords = [kw for kw in rule.get("keywords", []) if tm_normalize_text(kw) in haystack]
        if matched_keywords:
            best_reason = f"Coincidencia por palabra clave: {max(matched_keywords, key=len)}"

        # 2) match por regex
        if not best_reason:
            for pat in rule.get("patterns", []):
                if re.search(pat, haystack, re.I):
                    best_reason = f"Coincidencia por patrón regex: {pat}"
                    break

        if best_reason:
            bonus = 0

            # reforzar por contexto
            if rule.get("category") == "public_facing" and ctx["web"]:
                bonus += 4
            if rule.get("category") == "credentials" and ctx["auth"]:
                bonus += 4
            if rule.get("category") in ("traversal", "discovery") and ctx["file"]:
                bonus += 4
            if rule.get("category") == "tls" and ctx["tls"]:
                bonus += 4
            if rule.get("category") == "public_facing" and ctx["code_exec"]:
                bonus += 5

            matches.append({
                "technique_id": rule["technique_id"],
                "technique_name": rule["technique_name"],
                "tactic_id": rule["tactic_id"],
                "tactic_name": rule["tactic_name"],
                "impacto": rule["impacto"],
                "score": min(100, int(rule["score"]) + bonus),
                "confidence": min(100, int(rule["confidence"]) + bonus),
                "rationale": best_reason
            })

    # =========================
    # Fallbacks inteligentes
    # =========================
    if not matches:
        sev_score = tm_score_from_severity(severidad)

        if sev_score >= 80 and ctx["code_exec"]:
            matches.append({
                "technique_id": "T1190",
                "technique_name": "Exploit Public-Facing Application",
                "tactic_id": "TA0001",
                "tactic_name": "Initial Access",
                "impacto": "Posible explotación remota con capacidad de ejecución de código.",
                "score": 98,
                "confidence": 68,
                "rationale": "Fallback por severidad alta/crítica y contexto de ejecución"
            })

        elif sev_score >= 80 and ctx["web"]:
            matches.append({
                "technique_id": "T1190",
                "technique_name": "Exploit Public-Facing Application",
                "tactic_id": "TA0001",
                "tactic_name": "Initial Access",
                "impacto": "Posible explotación de servicio o aplicación pública expuesta.",
                "score": 95 if sev_score >= 90 else 85,
                "confidence": 62,
                "rationale": "Fallback por severidad alta/crítica en contexto web"
            })

        elif sev_score >= 55 and ctx["auth"]:
            matches.append({
                "technique_id": "T1078",
                "technique_name": "Valid Accounts",
                "tactic_id": "TA0001",
                "tactic_name": "Initial Access",
                "impacto": "Posible acceso indebido asociado a autenticación o credenciales.",
                "score": max(sev_score, 70),
                "confidence": 58,
                "rationale": "Fallback por contexto de autenticación/credenciales"
            })

        elif sev_score >= 55 and ctx["file"]:
            matches.append({
                "technique_id": "T1083",
                "technique_name": "File and Directory Discovery",
                "tactic_id": "TA0007",
                "tactic_name": "Discovery",
                "impacto": "Exposición o descubrimiento indebido de directorios y archivos.",
                "score": max(sev_score, 60),
                "confidence": 56,
                "rationale": "Fallback por contexto de archivos/directorios"
            })

        elif ctx["tls"]:
            matches.append({
                "technique_id": "T1190",
                "technique_name": "Exploit Public-Facing Application",
                "tactic_id": "TA0001",
                "tactic_name": "Initial Access",
                "impacto": "Debilidad de configuración TLS/SSL en servicio expuesto.",
                "score": max(sev_score, 45),
                "confidence": 52,
                "rationale": "Fallback por contexto TLS/SSL"
            })

        elif "cve-" in haystack and ctx["web"]:
            matches.append({
                "technique_id": "T1190",
                "technique_name": "Exploit Public-Facing Application",
                "tactic_id": "TA0001",
                "tactic_name": "Initial Access",
                "impacto": "Hallazgo con CVE asociado en contexto de aplicación pública expuesta.",
                "score": max(sev_score, 75),
                "confidence": 55,
                "rationale": "Fallback por presencia de CVE en contexto web"
            })

    return tm_deduplicate_mappings(matches)


def tm_score_from_severity(severidad: str) -> int:
    sev = (severidad or "").strip().lower()
    if sev in ("crítica", "critica"):
        return 100
    if sev == "alta":
        return 80
    if sev == "media":
        return 55
    if sev == "baja":
        return 25
    return 40


def tm_color_from_score(score: int) -> str:
    try:
        s = int(score)
    except Exception:
        s = 50

    if s >= 90:
        return "#b91c1c"
    if s >= 70:
        return "#ea580c"
    if s >= 40:
        return "#ca8a04"
    return "#15803d"

def crear_threat_model_desde_hallazgo(run, hallazgo, vuln=None, finding_rec=None):
    mappings = tm_map_finding_to_mitre(hallazgo)

    print("\n=== DEBUG MITRE ===")
    print("FUENTE:", hallazgo.get("fuente"))
    print("SEVERIDAD:", hallazgo.get("severidad"))
    print("TITULO:", hallazgo.get("titulo"))
    print("MAPPINGS:", mappings)

    if not mappings:
        guardar_threat_model_unmapped(run, hallazgo, finding_rec=finding_rec)
        return None

    impacto_final = None
    max_conf = 0

    for m in mappings:
        if m.get("confidence", 0) > max_conf:
            max_conf = m.get("confidence", 0)
            impacto_final = m.get("impacto")

    entry = ThreatModelEntry(
        run_id=run.id if run else None,
        finding_id=finding_rec.id if finding_rec else None,
        vulnerabilidad_registro_id=vuln.id if vuln else None,
        activo=(run.target if run else hallazgo.get("activo") or "Activo"),
        herramienta=(hallazgo.get("fuente") or "scanner").lower(),
        vulnerabilidad=(hallazgo.get("titulo") or "Hallazgo técnico")[:500],
        descripcion=(hallazgo.get("descripcion") or "")[:5000],
        impacto=(impacto_final or hallazgo.get("recomendacion_base") or "")[:4000],
        severidad=hallazgo.get("severidad"),
        confianza=max_conf or 70
    )
    db.session.add(entry)
    db.session.flush()

    base_score = tm_score_from_severity(hallazgo.get("severidad"))

    for m in mappings:
        score = max(base_score, int(m.get("score", 50)))
        db.session.add(ThreatModelTechnique(
            threat_entry_id=entry.id,
            mitre_technique_id=m["technique_id"],
            mitre_technique_name=m["technique_name"],
            mitre_tactic_id=m["tactic_id"],
            mitre_tactic_name=m["tactic_name"],
            rationale=m.get("rationale"),
            score=score
        ))

    db.session.flush()
    return entry


# ============================================================================
# SINCRONIZACIÓN MATRIZ DE VULNERABILIDADES -> MODELAMIENTO / MITRE ATT&CK
# ============================================================================

THREAT_MODEL_VULN_SOURCE = "registro_vulnerabilidades"


def tm_severidad_desde_vulnerabilidad(vuln):
    """Normaliza la clasificación de la matriz y usa CVSS como respaldo."""
    clasificacion = (getattr(vuln, "clasificacion", None) or "").strip()
    normalizadas = {
        "critica": "Crítica",
        "crítica": "Crítica",
        "alta": "Alta",
        "media": "Media",
        "baja": "Baja",
    }

    clave = tm_normalize_text(clasificacion)
    if clave in normalizadas:
        return normalizadas[clave]

    cvss_raw = str(getattr(vuln, "cvss", None) or "").strip().replace(",", ".")
    match = re.search(r"(?:^|\s)(10(?:\.0+)?|[0-9](?:\.[0-9]+)?)(?:\s|$)", cvss_raw)
    if match:
        try:
            cvss = float(match.group(1))
            if cvss >= 9.0:
                return "Crítica"
            if cvss >= 7.0:
                return "Alta"
            if cvss >= 4.0:
                return "Media"
            return "Baja"
        except Exception:
            pass

    return "Media"


def tm_aliases_mitre_espanol(*textos):
    """Agrega términos equivalentes para reconocer descripciones escritas en español."""
    base = tm_normalize_text(*textos)
    equivalencias = [
        (("inyeccion sql", "inyeccion de sql"), "sql injection"),
        (("inyeccion de comandos", "ejecucion remota de codigo", "ejecucion de codigo", "rce"),
         "remote code execution command injection"),
        (("credenciales por defecto", "contrasena por defecto", "clave por defecto"),
         "default credentials default password"),
        (("credenciales debiles", "contrasena debil", "autenticacion debil"),
         "weak credentials weak password"),
        (("acceso anonimo", "inicio de sesion anonimo"), "anonymous login"),
        (("omision de autenticacion", "bypass de autenticacion", "evasión de autenticacion", "autenticacion ausente"),
         "authentication bypass missing authentication"),
        (("listado de directorios", "indexacion de directorios", "navegacion de directorios"),
         "directory listing directory indexing"),
        (("divulgacion de informacion", "exposicion de informacion", "filtracion de informacion"),
         "information disclosure"),
        (("version expuesta", "divulgacion de version", "cabecera del servidor", "banner expuesto"),
         "version disclosure server header banner disclosure"),
        (("recorrido de directorios", "traversal de rutas", "traversal de directorios"),
         "path traversal directory traversal"),
        (("inclusion local de archivos", "inclusion de archivos locales"), "local file inclusion lfi"),
        (("inclusion remota de archivos", "inclusion de archivos remotos"), "remote file inclusion rfi"),
        (("carga de archivos", "subida de archivos", "carga irrestricta de archivos"),
         "unrestricted file upload arbitrary file upload"),
        (("cross site scripting", "secuencias de comandos entre sitios", "xss"), "cross-site scripting xss"),
        (("tls obsoleto", "ssl obsoleto", "protocolo obsoleto"), "deprecated protocol obsolete ssl"),
        (("cifrado debil", "cifrados debiles", "suite criptografica debil"), "weak cipher weak ciphers"),
        (("certificado vencido", "certificado expirado"), "expired certificate"),
        (("certificado autofirmado", "certificado auto firmado"), "self-signed certificate"),
        (("cabecera de seguridad faltante", "cabeceras de seguridad faltantes", "falta cabecera de seguridad"),
         "missing security header"),
        (("servidor desactualizado", "software obsoleto", "version obsoleta", "version no soportada"),
         "outdated web server unsupported version multiple vulnerabilities"),
    ]

    encontrados = []
    for frases, alias in equivalencias:
        if any(tm_normalize_text(frase) in base for frase in frases):
            encontrados.append(alias)

    return " ".join(encontrados)


def tm_hallazgo_desde_vulnerabilidad(vuln):
    """Convierte una fila de la matriz de vulnerabilidades al formato MITRE interno."""
    codigo = (getattr(vuln, "codigo", None) or f"VULN-{getattr(vuln, 'id', '')}").strip()
    descripcion = (getattr(vuln, "descripcion_vulnerabilidad", None) or "Vulnerabilidad registrada").strip()
    activo = (getattr(vuln, "activo", None) or "Activo").strip()
    cve = (getattr(vuln, "cve", None) or "").strip().upper()
    cvss = (getattr(vuln, "cvss", None) or "").strip()
    riesgo = (getattr(vuln, "riesgo_residual", None) or "").strip()
    estado = (getattr(vuln, "estado", None) or "").strip()
    responsable = (getattr(vuln, "responsable", None) or "").strip()
    aliases_mitre = tm_aliases_mitre_espanol(descripcion, riesgo, activo, cve)

    contexto = [descripcion]
    if cve:
        contexto.append(f"CVE: {cve}")
    if cvss:
        contexto.append(f"CVSS: {cvss}")
    if estado:
        contexto.append(f"Estado: {estado}")
    if responsable:
        contexto.append(f"Responsable: {responsable}")

    return {
        "fuente": THREAT_MODEL_VULN_SOURCE,
        "titulo": f"{codigo} - {descripcion}"[:500],
        "descripcion": " | ".join(contexto)[:5000],
        "evidencia": riesgo[:5000],
        "recomendacion_base": f"{riesgo} {aliases_mitre}".strip()[:5000],
        "servicio": activo[:200],
        "activo": activo[:200],
        "severidad": tm_severidad_desde_vulnerabilidad(vuln),
        "cve": cve,
        "cvss": cvss,
    }


def sincronizar_vulnerabilidad_no_mapeada(vuln, hallazgo, mappings):
    """
    Mantiene sincronizada la vulnerabilidad en
    ``Clasificación complementaria No Mapeados``.

    Reglas:
    - Si la vulnerabilidad tiene una técnica MITRE válida, elimina cualquier
      registro complementario anterior.
    - Si no puede mapearse a MITRE ATT&CK, crea o actualiza un único registro
      ``ThreatModelUnmapped`` con origen ``registro_vulnerabilidades``.
    - Genera automáticamente su clasificación complementaria OWASP, CWE,
      CAPEC, ISO 27001 y NIST CSF 2.0.
    """
    if vuln is None or not getattr(vuln, "id", None):
        return None

    registros = (
        ThreatModelUnmapped.query
        .filter(
            ThreatModelUnmapped.herramienta == THREAT_MODEL_VULN_SOURCE,
            ThreatModelUnmapped.finding_id == int(vuln.id)
        )
        .order_by(ThreatModelUnmapped.id.asc())
        .all()
    )

    # Si ya existe un mapeo MITRE, el registro deja de ser "No Mapeado".
    if mappings:
        for item in registros:
            db.session.delete(item)
        db.session.flush()
        return None

    principal = registros[0] if registros else None

    # Elimina duplicados históricos de la misma vulnerabilidad.
    for duplicado in registros[1:]:
        db.session.delete(duplicado)

    if principal is None:
        principal = ThreatModelUnmapped(
            run_id=None,
            finding_id=int(vuln.id),
            activo=(hallazgo.get("activo") or "Activo")[:200],
            herramienta=THREAT_MODEL_VULN_SOURCE,
            severidad=(hallazgo.get("severidad") or "Media")[:20],
            titulo=(hallazgo.get("titulo") or "Vulnerabilidad registrada")[:500],
            descripcion=(hallazgo.get("descripcion") or "")[:5000],
            evidencia=(hallazgo.get("evidencia") or "")[:5000],
        )
        db.session.add(principal)
    else:
        principal.run_id = None
        principal.finding_id = int(vuln.id)
        principal.activo = (hallazgo.get("activo") or "Activo")[:200]
        principal.herramienta = THREAT_MODEL_VULN_SOURCE
        principal.severidad = (hallazgo.get("severidad") or "Media")[:20]
        principal.titulo = (hallazgo.get("titulo") or "Vulnerabilidad registrada")[:500]
        principal.descripcion = (hallazgo.get("descripcion") or "")[:5000]
        principal.evidencia = (hallazgo.get("evidencia") or "")[:5000]

    db.session.flush()

    # La clasificación complementaria se crea o actualiza automáticamente.
    guardar_clasificacion_complementaria_unmapped(principal)
    db.session.flush()

    return principal


def sincronizar_vulnerabilidad_con_modelamiento(vuln):
    """
    Garantiza que cada vulnerabilidad registrada tenga una entrada propia y
    trazable en Modelamiento de Amenazas.

    Reglas:
    - Siempre existe una entrada canónica con herramienta
      ``registro_vulnerabilidades``.
    - Los registros generados por escáneres se conservan.
    - Las técnicas MITRE de la entrada canónica se reconstruyen de forma
      idempotente.
    - Cuando no existe una coincidencia MITRE confiable, la vulnerabilidad se
      registra automáticamente en ``Clasificación complementaria No Mapeados``.
    """
    if vuln is None:
        return None

    if not getattr(vuln, "id", None):
        db.session.flush()

    hallazgo = tm_hallazgo_desde_vulnerabilidad(vuln)
    severidad = hallazgo.get("severidad") or "Media"

    existentes = (
        ThreatModelEntry.query
        .options(selectinload(ThreatModelEntry.tecnicas))
        .filter_by(vulnerabilidad_registro_id=vuln.id)
        .order_by(ThreatModelEntry.id.asc())
        .all()
    )

    manuales = [
        entry for entry in existentes
        if (entry.herramienta or "").strip().lower() == THREAT_MODEL_VULN_SOURCE
    ]
    manual = manuales[0] if manuales else None

    # Elimina solo duplicados automáticos; conserva modelamientos de escáner.
    for duplicado in manuales[1:]:
        db.session.delete(duplicado)

    # Mantiene actualizados los hallazgos de escáner vinculados.
    for entry in existentes:
        if entry in manuales:
            continue
        entry.activo = hallazgo["activo"]
        entry.vulnerabilidad = hallazgo["titulo"]
        entry.descripcion = hallazgo["descripcion"]
        entry.severidad = severidad
        if (getattr(vuln, "riesgo_residual", None) or "").strip():
            entry.impacto = (vuln.riesgo_residual or "")[:4000]
        entry.updated_at = datetime.utcnow()

    mappings = tm_map_finding_to_mitre(hallazgo)
    impacto_final = (getattr(vuln, "riesgo_residual", None) or "").strip()
    max_conf = 0

    for mapping in mappings:
        conf = int(mapping.get("confidence", 0) or 0)
        if conf > max_conf:
            max_conf = conf
            impacto_final = mapping.get("impacto") or impacto_final

    impacto_entrada = (
        impacto_final or
        "No fue posible clasificar automáticamente esta vulnerabilidad en MITRE ATT&CK. "
        "Se registró en Clasificación complementaria No Mapeados."
    )[:4000]

    if manual is None:
        manual = ThreatModelEntry(
            vulnerabilidad_registro_id=vuln.id,
            activo=hallazgo["activo"],
            herramienta=THREAT_MODEL_VULN_SOURCE,
            vulnerabilidad=hallazgo["titulo"],
            descripcion=hallazgo["descripcion"],
            impacto=impacto_entrada,
            severidad=severidad,
            confianza=max_conf or 0,
        )
        db.session.add(manual)
        db.session.flush()
    else:
        manual.activo = hallazgo["activo"]
        manual.herramienta = THREAT_MODEL_VULN_SOURCE
        manual.vulnerabilidad = hallazgo["titulo"]
        manual.descripcion = hallazgo["descripcion"]
        manual.impacto = impacto_entrada
        manual.severidad = severidad
        manual.confianza = max_conf or 0
        manual.updated_at = datetime.utcnow()

        # Reconstruye solo las técnicas de la entrada canónica.
        manual.tecnicas.clear()
        db.session.flush()

    base_score = tm_score_from_severity(severidad)

    for mapping in mappings:
        manual.tecnicas.append(ThreatModelTechnique(
            mitre_technique_id=mapping["technique_id"],
            mitre_technique_name=mapping["technique_name"],
            mitre_tactic_id=mapping.get("tactic_id"),
            mitre_tactic_name=mapping["tactic_name"],
            rationale=(
                mapping.get("rationale") or
                "Mapeo automático desde la matriz de vulnerabilidades"
            ),
            score=max(base_score, int(mapping.get("score", 50) or 50)),
        ))

    # Crea la clasificación complementaria cuando no existe mapeo MITRE,
    # o elimina el registro complementario si posteriormente logra mapearse.
    sincronizar_vulnerabilidad_no_mapeada(vuln, hallazgo, mappings)

    db.session.flush()
    return manual


def sincronizar_todas_vulnerabilidades_con_modelamiento():
    """
    Sincroniza todas las vulnerabilidades existentes y corrige históricos.

    También garantiza que cada vulnerabilidad sin técnica MITRE tenga un único
    registro en ``Clasificación complementaria No Mapeados``.
    """
    vulnerabilidades = (
        VulnerabilidadRegistro.query
        .order_by(VulnerabilidadRegistro.id.asc())
        .all()
    )

    if not vulnerabilidades:
        return 0

    entradas = (
        ThreatModelEntry.query
        .options(selectinload(ThreatModelEntry.tecnicas))
        .filter(ThreatModelEntry.vulnerabilidad_registro_id.isnot(None))
        .order_by(ThreatModelEntry.id.asc())
        .all()
    )

    manuales_por_vulnerabilidad = defaultdict(list)
    for entry in entradas:
        if (
            entry.vulnerabilidad_registro_id is not None and
            (entry.herramienta or "").strip().lower() == THREAT_MODEL_VULN_SOURCE
        ):
            manuales_por_vulnerabilidad[int(entry.vulnerabilidad_registro_id)].append(entry)

    no_mapeados = (
        ThreatModelUnmapped.query
        .filter(
            ThreatModelUnmapped.herramienta == THREAT_MODEL_VULN_SOURCE,
            ThreatModelUnmapped.finding_id.isnot(None)
        )
        .order_by(ThreatModelUnmapped.id.asc())
        .all()
    )

    no_mapeados_por_vulnerabilidad = defaultdict(list)
    for item in no_mapeados:
        try:
            no_mapeados_por_vulnerabilidad[int(item.finding_id)].append(item)
        except Exception:
            continue

    ids_vigentes = {int(v.id) for v in vulnerabilidades if getattr(v, "id", None)}
    cambios = 0

    # Elimina registros complementarios huérfanos de vulnerabilidades ya borradas.
    for vuln_id, items in list(no_mapeados_por_vulnerabilidad.items()):
        if vuln_id not in ids_vigentes:
            for item in items:
                db.session.delete(item)
                cambios += 1

    for vuln in vulnerabilidades:
        hallazgo = tm_hallazgo_desde_vulnerabilidad(vuln)
        mappings = tm_map_finding_to_mitre(hallazgo)
        manuales = manuales_por_vulnerabilidad.get(int(vuln.id), [])
        complementarios = no_mapeados_por_vulnerabilidad.get(int(vuln.id), [])

        expected_keys = {
            (
                str(mapping.get("technique_id") or "").strip().upper(),
                str(mapping.get("tactic_id") or "").strip().upper(),
            )
            for mapping in mappings
            if mapping.get("technique_id")
        }

        necesita_sincronizacion = len(manuales) != 1

        if len(manuales) == 1:
            manual = manuales[0]
            actual_keys = {
                (
                    str(tech.mitre_technique_id or "").strip().upper(),
                    str(tech.mitre_tactic_id or "").strip().upper(),
                )
                for tech in (manual.tecnicas or [])
            }

            severidad = hallazgo.get("severidad") or "Media"
            datos_desactualizados = any([
                (manual.activo or "") != hallazgo["activo"],
                (manual.vulnerabilidad or "") != hallazgo["titulo"],
                (manual.descripcion or "") != hallazgo["descripcion"],
                (manual.severidad or "") != severidad,
                actual_keys != expected_keys,
            ])
            necesita_sincronizacion = necesita_sincronizacion or datos_desactualizados

        if mappings:
            # Una vulnerabilidad mapeada no debe permanecer en No Mapeados.
            if complementarios:
                necesita_sincronizacion = True
        else:
            # Una vulnerabilidad no mapeada debe tener un único registro y una
            # clasificación complementaria generada.
            if len(complementarios) != 1:
                necesita_sincronizacion = True
            else:
                item = complementarios[0]
                clasificacion = getattr(item, "clasificacion_complementaria", None)
                datos_complementarios_desactualizados = any([
                    (item.activo or "") != hallazgo["activo"],
                    (item.herramienta or "") != THREAT_MODEL_VULN_SOURCE,
                    (item.severidad or "") != (hallazgo.get("severidad") or "Media"),
                    (item.titulo or "") != hallazgo["titulo"],
                    (item.descripcion or "") != hallazgo["descripcion"],
                    (item.evidencia or "") != hallazgo["evidencia"],
                    clasificacion is None,
                ])
                necesita_sincronizacion = (
                    necesita_sincronizacion or
                    datos_complementarios_desactualizados
                )

        if necesita_sincronizacion:
            sincronizar_vulnerabilidad_con_modelamiento(vuln)
            cambios += 1

    if cambios:
        db.session.commit()

    return cambios


def asegurar_sincronizacion_vulnerabilidades_modelamiento():
    """Ejecuta la sincronización automática sin impedir el acceso si ocurre un error."""
    try:
        return sincronizar_todas_vulnerabilidades_con_modelamiento()
    except Exception as exc:
        db.session.rollback()
        print("No fue posible sincronizar vulnerabilidades con MITRE ATT&CK:", repr(exc))
        return 0


# ============================================================
# ACTIVE DIRECTORY -> MODELAMIENTO DE AMENAZAS / MITRE ATT&CK
# ============================================================
THREAT_MODEL_AD_SOURCE = "active_directory"
THREAT_MODEL_AD_MARKER_RE = re.compile(r"\[GRAC-AD-FINDING:(\d+)\]", re.I)


def tm_ad_marker(finding_id):
    try:
        return "[GRAC-AD-FINDING:{}]".format(int(finding_id))
    except Exception:
        return ""


def tm_ad_finding_id(entry):
    """Obtiene el ID externo del hallazgo AD sin reutilizar llaves foráneas de escáneres."""
    if entry is None or (getattr(entry, "herramienta", "") or "").strip().lower() != THREAT_MODEL_AD_SOURCE:
        return None
    for value in (
        getattr(entry, "descripcion", None),
        getattr(entry, "impacto", None),
        getattr(entry, "vulnerabilidad", None),
    ):
        match = THREAT_MODEL_AD_MARKER_RE.search(str(value or ""))
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None
    return None


def tm_ad_source_ready():
    """Confirma que la base y tabla de Gobierno AD están disponibles antes de sincronizar."""
    ad_db_path = os.path.join(app.instance_path, "ad_governance.db")
    if not os.path.exists(ad_db_path):
        return False
    conn = None
    try:
        conn = sqlite3.connect(ad_db_path, timeout=15)
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ad_findings'"
        ).fetchone() is not None
    except sqlite3.Error:
        return False
    finally:
        if conn is not None:
            conn.close()


def sincronizar_active_directory_con_modelamiento():
    """
    Incorpora cada hallazgo activo de Gobierno del Directorio Activo como una
    entrada trazable de Modelamiento de Amenazas.

    La identificación externa se conserva dentro de un marcador técnico en la
    descripción para no mezclar IDs de Active Directory con las llaves foráneas
    de hallazgos producidos por escáneres. La sincronización es idempotente:
    actualiza cambios, elimina duplicados y retira registros que ya no están
    activos en la fuente AD.
    """
    if not tm_ad_source_ready():
        return 0

    collector = globals().get("attack_auto_collect_active_directory")
    if not callable(collector):
        # La función se define más adelante en el archivo y estará disponible
        # durante las solicitudes Flask, una vez cargado completamente el módulo.
        return 0

    records = collector() or []
    existing = (
        ThreatModelEntry.query
        .options(selectinload(ThreatModelEntry.tecnicas))
        .filter(func.lower(ThreatModelEntry.herramienta) == THREAT_MODEL_AD_SOURCE)
        .order_by(ThreatModelEntry.id.asc())
        .all()
    )

    existing_by_id = defaultdict(list)
    for entry in existing:
        finding_id = tm_ad_finding_id(entry)
        if finding_id is not None:
            existing_by_id[int(finding_id)].append(entry)

    source_ids = set()
    changes = 0

    def update_attr(obj, attr, value):
        nonlocal changes
        if getattr(obj, attr) != value:
            setattr(obj, attr, value)
            changes += 1

    for record in records:
        source_ref = str(record.get("source_ref") or "")
        match = re.search(r"(?:^|:)AD:(\d+)$", source_ref, flags=re.I)
        if not match:
            match = re.search(r"(\d+)$", source_ref)
        if not match:
            continue

        finding_id = int(match.group(1))
        source_ids.add(finding_id)
        candidates = existing_by_id.get(finding_id, [])
        entry = candidates[0] if candidates else None

        for duplicate in candidates[1:]:
            db.session.delete(duplicate)
            changes += 1

        severity = attack_auto_normalize_severity(record.get("severity"))
        asset = attack_auto_clean(record.get("asset_name") or "Directorio corporativo", 200)
        vulnerability = attack_auto_clean(
            record.get("vulnerability") or record.get("title") or "Hallazgo de Gobierno del Directorio Activo",
            500,
        )
        marker = tm_ad_marker(finding_id)
        description_parts = [
            attack_auto_clean(record.get("description") or vulnerability, 4300),
            "Estado en Gobierno AD: {}.".format(attack_auto_clean(record.get("status") or "En análisis", 80)),
        ]
        if record.get("existing_controls"):
            description_parts.append("Controles relacionados: {}".format(attack_auto_clean(record.get("existing_controls"), 1200)))
        if record.get("control_weaknesses"):
            description_parts.append("Tratamiento recomendado: {}".format(attack_auto_clean(record.get("control_weaknesses"), 1500)))
        if record.get("evidence"):
            description_parts.append("Evidencia: {}".format(attack_auto_clean(record.get("evidence"), 1200)))
        description_parts.append(marker)
        description = "\n\n".join(part for part in description_parts if part)[:5000]
        impact = attack_auto_clean(
            record.get("consequences") or
            "Compromiso de identidad, persistencia, escalamiento de privilegios y movimiento lateral en el dominio.",
            4000,
        )

        techniques = list(record.get("techniques") or [])
        if not techniques:
            techniques = [
                {
                    "technique_id": "T1078.002",
                    "technique_name": "Valid Accounts: Domain Accounts",
                    "tactic_id": "TA0001",
                    "tactic_name": "Initial Access",
                    "rationale": "El hallazgo puede facilitar el uso indebido de una identidad válida de dominio.",
                    "confidence": 90,
                },
                {
                    "technique_id": "T1098",
                    "technique_name": "Account Manipulation",
                    "tactic_id": "TA0003",
                    "tactic_name": "Persistence",
                    "rationale": "La debilidad de gobierno puede permitir persistencia mediante cambios de cuentas, grupos o privilegios.",
                    "confidence": 82,
                },
            ]

        confidence = max(
            [int(item.get("confidence") or 0) for item in techniques] or [80]
        )

        if entry is None:
            entry = ThreatModelEntry(
                activo=asset,
                herramienta=THREAT_MODEL_AD_SOURCE,
                vulnerabilidad=vulnerability,
                descripcion=description,
                impacto=impact,
                severidad=severity,
                confianza=confidence,
            )
            db.session.add(entry)
            db.session.flush()
            changes += 1
        else:
            update_attr(entry, "activo", asset)
            update_attr(entry, "herramienta", THREAT_MODEL_AD_SOURCE)
            update_attr(entry, "vulnerabilidad", vulnerability)
            update_attr(entry, "descripcion", description)
            update_attr(entry, "impacto", impact)
            update_attr(entry, "severidad", severity)
            update_attr(entry, "confianza", confidence)

        expected = []
        base_score = tm_score_from_severity(severity)
        for item in techniques:
            technique_id = attack_auto_clean(item.get("technique_id"), 20)
            if not technique_id:
                continue
            expected.append((
                technique_id,
                attack_auto_clean(item.get("technique_name") or technique_id, 255),
                attack_auto_clean(item.get("tactic_id"), 20) or None,
                attack_auto_clean(item.get("tactic_name") or "Other", 100),
                attack_auto_clean(item.get("rationale") or "Mapeo desde Gobierno del Directorio Activo", 4000),
                max(base_score, int(item.get("confidence") or confidence or 60)),
            ))

        actual = [
            (
                tech.mitre_technique_id,
                tech.mitre_technique_name,
                tech.mitre_tactic_id,
                tech.mitre_tactic_name,
                tech.rationale or "",
                int(tech.score or 0),
            )
            for tech in (entry.tecnicas or [])
        ]

        if actual != expected:
            entry.tecnicas.clear()
            db.session.flush()
            for technique_id, technique_name, tactic_id, tactic_name, rationale, score in expected:
                entry.tecnicas.append(ThreatModelTechnique(
                    mitre_technique_id=technique_id,
                    mitre_technique_name=technique_name,
                    mitre_tactic_id=tactic_id,
                    mitre_tactic_name=tactic_name,
                    rationale=rationale,
                    score=score,
                ))
            changes += 1

    # Retira del modelamiento los hallazgos que dejaron de estar activos en AD.
    for entry in existing:
        finding_id = tm_ad_finding_id(entry)
        if finding_id is None or int(finding_id) not in source_ids:
            db.session.delete(entry)
            changes += 1

    if changes:
        db.session.commit()
    return changes


def asegurar_sincronizacion_active_directory_modelamiento():
    """Sincroniza Gobierno AD sin impedir el acceso al módulo ante un error externo."""
    try:
        return sincronizar_active_directory_con_modelamiento()
    except Exception as exc:
        db.session.rollback()
        print("No fue posible sincronizar Gobierno del Directorio Activo con Modelamiento de Amenazas:", repr(exc))
        return 0


# ============================================================
# GOBIERNO DE FIREWALL -> MODELAMIENTO DE AMENAZAS / MITRE ATT&CK
# ============================================================
THREAT_MODEL_FIREWALL_SOURCE = "firewall_governance"
THREAT_MODEL_FIREWALL_MARKER_RE = re.compile(r"\[GRAC-FIREWALL-FINDING:(\d+)\]", re.I)


def tm_firewall_marker(finding_id):
    try:
        return "[GRAC-FIREWALL-FINDING:{}]".format(int(finding_id))
    except Exception:
        return ""


def tm_firewall_finding_id(entry):
    """Obtiene el ID externo del hallazgo de firewall almacenado en el marcador técnico."""
    if entry is None or (getattr(entry, "herramienta", "") or "").strip().lower() != THREAT_MODEL_FIREWALL_SOURCE:
        return None
    for value in (
        getattr(entry, "descripcion", None),
        getattr(entry, "impacto", None),
        getattr(entry, "vulnerabilidad", None),
    ):
        match = THREAT_MODEL_FIREWALL_MARKER_RE.search(str(value or ""))
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None
    return None


def tm_firewall_finding_url(entry):
    """Construye un enlace trazable desde Modelamiento hacia el hallazgo original."""
    finding_id = tm_firewall_finding_id(entry)
    finding_model = globals().get("FirewallGovFinding")
    if finding_id is None or finding_model is None:
        return ""
    try:
        finding = db.session.get(finding_model, int(finding_id))
    except Exception:
        finding = finding_model.query.get(int(finding_id))
    if not finding:
        return ""
    return url_for(
        "cumplimiento_continuo_firewall",
        device_id=finding.device_id,
        q=finding.finding_code or finding.id,
    )


def sincronizar_firewall_con_modelamiento():
    """
    Incorpora los hallazgos activos de Gobierno de Firewall como entradas
    trazables de Modelamiento de Amenazas y mantiene su mapeo MITRE ATT&CK.

    La sincronización es idempotente: actualiza cambios, elimina duplicados
    y retira los registros cuya fuente ya no está activa.
    """
    collector = globals().get("attack_auto_collect_firewall")
    finding_model = globals().get("FirewallGovFinding")
    if not callable(collector) or finding_model is None:
        return 0

    records = collector() or []
    source_findings = {
        int(item.id): item
        for item in finding_model.query.filter_by(active=True).order_by(finding_model.id.asc()).all()
    }
    existing = (
        ThreatModelEntry.query
        .options(selectinload(ThreatModelEntry.tecnicas))
        .filter(func.lower(ThreatModelEntry.herramienta) == THREAT_MODEL_FIREWALL_SOURCE)
        .order_by(ThreatModelEntry.id.asc())
        .all()
    )

    existing_by_id = defaultdict(list)
    for entry in existing:
        finding_id = tm_firewall_finding_id(entry)
        if finding_id is not None:
            existing_by_id[int(finding_id)].append(entry)

    source_ids = set()
    changes = 0

    def update_attr(obj, attr, value):
        nonlocal changes
        if getattr(obj, attr) != value:
            setattr(obj, attr, value)
            changes += 1

    for record in records:
        source_ref = str(record.get("source_ref") or "")
        match = re.search(r"(\d+)$", source_ref)
        if not match:
            continue

        finding_id = int(match.group(1))
        finding = source_findings.get(finding_id)
        if finding is None:
            continue

        source_ids.add(finding_id)
        candidates = existing_by_id.get(finding_id, [])
        entry = candidates[0] if candidates else None

        for duplicate in candidates[1:]:
            db.session.delete(duplicate)
            changes += 1

        severity = attack_auto_normalize_severity(record.get("severity") or finding.severity)
        asset = attack_auto_clean(record.get("asset_name") or "Firewall / Perímetro", 200)
        vulnerability = attack_auto_clean(
            record.get("vulnerability") or finding.title or "Hallazgo de Gobierno de Firewall",
            500,
        )
        marker = tm_firewall_marker(finding_id)

        description_parts = [
            attack_auto_clean(record.get("description") or finding.description or vulnerability, 3500),
            "Código: {}. Regla: {}. Estado: {}.".format(
                attack_auto_clean(finding.finding_code or "N/D", 120),
                attack_auto_clean(finding.rule_name or finding.rule_external_id or "N/D", 500),
                attack_auto_clean(finding.status or "Abierto", 80),
            ),
        ]
        if finding.control_mapping:
            description_parts.append(
                "Controles relacionados: {}".format(
                    attack_auto_clean(finding.control_mapping, 1200)
                )
            )
        if finding.recommendation:
            description_parts.append(
                "Tratamiento recomendado: {}".format(
                    attack_auto_clean(finding.recommendation, 1500)
                )
            )
        if finding.technical_detail:
            description_parts.append(
                "Detalle técnico: {}".format(
                    attack_auto_clean(finding.technical_detail, 1200)
                )
            )
        if record.get("evidence"):
            description_parts.append(
                "Evidencia: {}".format(attack_auto_clean(record.get("evidence"), 1200))
            )
        description_parts.append(marker)
        description = "\n\n".join(part for part in description_parts if part)[:5000]

        impact = attack_auto_clean(
            record.get("consequences")
            or "Acceso no autorizado, exposición del perímetro, evasión de controles, movimiento lateral o afectación de servicios.",
            4000,
        )

        techniques = list(record.get("techniques") or [])
        if not techniques:
            techniques = [{
                "technique_id": "T1562.004",
                "technique_name": "Impair Defenses: Disable or Modify System Firewall",
                "tactic_id": "TA0005",
                "tactic_name": "Defense Evasion",
                "rationale": "El hallazgo evidencia una debilidad de configuración o gobierno que puede reducir la eficacia del control perimetral.",
                "confidence": 70,
            }]

        confidence = max([int(item.get("confidence") or 0) for item in techniques] or [70])

        if entry is None:
            entry = ThreatModelEntry(
                activo=asset,
                herramienta=THREAT_MODEL_FIREWALL_SOURCE,
                vulnerabilidad=vulnerability,
                descripcion=description,
                impacto=impact,
                severidad=severity,
                confianza=confidence,
            )
            db.session.add(entry)
            db.session.flush()
            changes += 1
        else:
            update_attr(entry, "activo", asset)
            update_attr(entry, "herramienta", THREAT_MODEL_FIREWALL_SOURCE)
            update_attr(entry, "vulnerabilidad", vulnerability)
            update_attr(entry, "descripcion", description)
            update_attr(entry, "impacto", impact)
            update_attr(entry, "severidad", severity)
            update_attr(entry, "confianza", confidence)

        expected = []
        base_score = tm_score_from_severity(severity)
        seen_techniques = set()
        for item in techniques:
            technique_id = attack_auto_clean(item.get("technique_id"), 20)
            if not technique_id or technique_id in seen_techniques:
                continue
            seen_techniques.add(technique_id)
            expected.append((
                technique_id,
                attack_auto_clean(item.get("technique_name") or technique_id, 255),
                attack_auto_clean(item.get("tactic_id"), 20) or None,
                attack_auto_clean(item.get("tactic_name") or "Other", 100),
                attack_auto_clean(item.get("rationale") or "Mapeo desde Gobierno de Firewall", 4000),
                max(base_score, int(item.get("confidence") or confidence or 60)),
            ))

        actual = [
            (
                tech.mitre_technique_id,
                tech.mitre_technique_name,
                tech.mitre_tactic_id,
                tech.mitre_tactic_name,
                tech.rationale or "",
                int(tech.score or 0),
            )
            for tech in (entry.tecnicas or [])
        ]

        if actual != expected:
            entry.tecnicas.clear()
            db.session.flush()
            for technique_id, technique_name, tactic_id, tactic_name, rationale, score in expected:
                entry.tecnicas.append(ThreatModelTechnique(
                    mitre_technique_id=technique_id,
                    mitre_technique_name=technique_name,
                    mitre_tactic_id=tactic_id,
                    mitre_tactic_name=tactic_name,
                    rationale=rationale,
                    score=score,
                ))
            changes += 1

    for entry in existing:
        finding_id = tm_firewall_finding_id(entry)
        if finding_id is None or int(finding_id) not in source_ids:
            db.session.delete(entry)
            changes += 1

    if changes:
        db.session.commit()
    return changes


def asegurar_sincronizacion_firewall_modelamiento():
    """Sincroniza Gobierno de Firewall sin bloquear el acceso ante un error externo."""
    try:
        return sincronizar_firewall_con_modelamiento()
    except Exception as exc:
        db.session.rollback()
        print("No fue posible sincronizar Gobierno de Firewall con Modelamiento de Amenazas:", repr(exc))
        return 0


# ===================
# Helper
# ===================


def build_attack_layer_from_entries(entries, asset_name="Activo"):
    agg = OrderedDict()

    for entry in entries:
        for tech in entry.tecnicas:
            tid = tech.mitre_technique_id
            current = agg.get(tid)

            score = max(
                int(tech.score or 0),
                tm_score_from_severity(entry.severidad)
            )

            comment = f"[{entry.herramienta}] {entry.vulnerabilidad}"
            if entry.impacto:
                comment += f" | Impacto: {entry.impacto}"

            if not current:
                agg[tid] = {
                    "techniqueID": tid,
                    "score": score,
                    "color": tm_color_from_score(score),
                    "comment": comment[:900],
                    "enabled": True
                }
            else:
                if score > current["score"]:
                    current["score"] = score
                    current["color"] = tm_color_from_score(score)
                if comment not in current["comment"]:
                    current["comment"] = (current["comment"] + " || " + comment)[:900]

    layer = {
        "name": f"Threat Model - {asset_name}",
        "domain": ATTACK_DOMAIN,
        "description": f"Capa MITRE ATT&CK generada automáticamente para {asset_name}",
        "versions": {
            "layer": "4.4",
            "navigator": "4.9.1",
            "attack": "18"
        },
        "layout": {
            "layout": "side",
            "showID": True,
            "showName": True,
            "showAggregateScores": True,
            "countUnscored": False
        },
        "sorting": 3,
        "hideDisabled": False,
        "gradient": {
            "colors": ["#15803d", "#ca8a04", "#ea580c", "#b91c1c"],
            "minValue": 0,
            "maxValue": 100
        },
        "legendItems": [
            {"label": "Bajo", "color": "#15803d"},
            {"label": "Medio", "color": "#ca8a04"},
            {"label": "Alto", "color": "#ea580c"},
            {"label": "Crítico", "color": "#b91c1c"}
        ],
        "techniques": list(agg.values())
    }
    return layer


def build_attack_matrix_view(entries):
    matrix = {t: [] for t in ATTACK_TACTIC_ORDER}
    matrix[MITRE_PENDING_TACTIC] = []

    vulnerabilidades_representadas = set()

    # Primero agrega todas las técnicas MITRE reales.
    for entry in entries:
        tecnicas = list(entry.tecnicas or [])
        if not tecnicas:
            continue

        if entry.vulnerabilidad_registro_id is not None:
            vulnerabilidades_representadas.add(int(entry.vulnerabilidad_registro_id))

        for tech in tecnicas:
            tactic = tech.mitre_tactic_name or "Other"
            matrix.setdefault(tactic, [])
            matrix[tactic].append({
                "entry_id": entry.id,
                "vulnerabilidad_registro_id": entry.vulnerabilidad_registro_id,
                "tool": entry.herramienta,
                "severity": entry.severidad,
                "vulnerability": entry.vulnerabilidad,
                "impacto": entry.impacto,
                "technique_id": tech.mitre_technique_id,
                "technique_name": tech.mitre_technique_name,
                "score": tech.score,
                "rationale": tech.rationale,
                "pending": False,
            })

    # Después incorpora una sola tarjeta pendiente por vulnerabilidad no representada.
    pendientes_vistos = set()
    for entry in entries:
        if entry.tecnicas:
            continue

        vuln_id = entry.vulnerabilidad_registro_id
        if vuln_id is not None:
            vuln_id = int(vuln_id)
            if vuln_id in vulnerabilidades_representadas:
                continue
            clave = ("vulnerabilidad", vuln_id)
        else:
            clave = ("entrada", int(entry.id))

        if clave in pendientes_vistos:
            continue
        pendientes_vistos.add(clave)

        matrix[MITRE_PENDING_TACTIC].append({
            "entry_id": entry.id,
            "vulnerabilidad_registro_id": entry.vulnerabilidad_registro_id,
            "tool": entry.herramienta,
            "severity": entry.severidad,
            "vulnerability": entry.vulnerabilidad,
            "impacto": entry.impacto,
            "technique_id": "PENDIENTE",
            "technique_name": "Pendiente de mapeo MITRE ATT&CK",
            "score": tm_score_from_severity(entry.severidad),
            "rationale": (
                "La vulnerabilidad está registrada y visible, pero aún no existe una "
                "correspondencia técnica confiable con una técnica MITRE ATT&CK."
            ),
            "pending": True,
        })

    for tactic in matrix:
        matrix[tactic] = sorted(
            matrix[tactic],
            key=lambda x: (-(x.get("score") or 0), x.get("technique_id") or "")
        )

    return matrix

def tm_detect_context(haystack: str) -> dict:
    return {
        "web": any(x in haystack for x in [
            "http", "https", "apache", "nginx", "iis", "tomcat",
            "php", "wordpress", "drupal", "joomla", "web", "login", "admin panel"
        ]),
        "tls": any(x in haystack for x in [
            "tls", "ssl", "cipher", "certificate", "renegotiation"
        ]),
        "auth": any(x in haystack for x in [
            "login", "password", "credential", "authentication", "anonymous", "guest"
        ]),
        "file": any(x in haystack for x in [
            "directory", "file", "upload", "traversal", "lfi", "rfi", "../"
        ]),
        "code_exec": any(x in haystack for x in [
            "rce", "remote code execution", "command injection", "code execution"
        ])
    }

def guardar_threat_model_unmapped(run, hallazgo, finding_rec=None):
    rec = ThreatModelUnmapped(
        run_id=run.id if run else None,
        finding_id=finding_rec.id if finding_rec else None,
        activo=(run.target if run else hallazgo.get("activo") or "Activo"),
        herramienta=(hallazgo.get("fuente") or "scanner").lower(),
        severidad=hallazgo.get("severidad"),
        titulo=(hallazgo.get("titulo") or "Hallazgo técnico")[:500],
        descripcion=(hallazgo.get("descripcion") or "")[:5000],
        evidencia=(hallazgo.get("evidencia") or "")[:5000]
    )
    db.session.add(rec)
    db.session.flush()

# ===================
# Dashboard
# ===================

@app.route('/modelamiento_amenazas')
@login_required
def threat_model_dashboard():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Modelamiento de Amenazas"):
        flash("No tiene permiso para acceder al modelamiento de amenazas.", "danger")
        return redirect(url_for('menu'))

    read_only = True if user.role == 'auditor' else False

    # Incluye automáticamente todas las vulnerabilidades existentes de la matriz.
    asegurar_sincronizacion_vulnerabilidades_modelamiento()
    asegurar_sincronizacion_active_directory_modelamiento()
    asegurar_sincronizacion_firewall_modelamiento()

    mapped_count = (
        db.session.query(func.count(func.distinct(ThreatModelEntry.id)))
        .join(ThreatModelTechnique, ThreatModelTechnique.threat_entry_id == ThreatModelEntry.id)
        .scalar() or 0
    )
    pendientes_mitre = ThreatModelEntry.query.filter(~ThreatModelEntry.tecnicas.any()).count()
    unmapped_count = ThreatModelUnmapped.query.count()
    coverage_pct = round((mapped_count / (mapped_count + unmapped_count) * 100), 1) if (mapped_count + unmapped_count) else 0

    filtro_activo = (request.args.get('activo') or '').strip()
    filtro_herramienta = (request.args.get('herramienta') or '').strip()
    filtro_severidad = (request.args.get('severidad') or '').strip()
    filtro_tecnica = (request.args.get('tecnica') or '').strip()

    tecnicas_disponibles = (
        db.session.query(
            ThreatModelTechnique.mitre_technique_id,
            ThreatModelTechnique.mitre_technique_name
        )
        .distinct()
        .order_by(
            ThreatModelTechnique.mitre_technique_id.asc(),
            ThreatModelTechnique.mitre_technique_name.asc()
        )
        .all()
    )

    q = ThreatModelEntry.query.options(selectinload(ThreatModelEntry.tecnicas))

    if filtro_activo:
        q = q.filter(ThreatModelEntry.activo.ilike(f"%{filtro_activo}%"))

    if filtro_herramienta:
        q = q.filter(ThreatModelEntry.herramienta == filtro_herramienta)

    if filtro_severidad:
        q = q.filter(ThreatModelEntry.severidad == filtro_severidad)

    if filtro_tecnica:
        q = q.join(ThreatModelTechnique).filter(
            ThreatModelTechnique.mitre_technique_id == filtro_tecnica
        )

    items = q.distinct().order_by(ThreatModelEntry.id.desc()).all()

    body = """
    <div class="glass-card p-4 mt-2 threat-dashboard-card">
      <div class="section-title threat-dashboard-heading">🎯 Dashboard de Modelamiento de Amenazas</div>

      <!-- Acciones siempre DEBAJO del título, sin superposiciones. -->
      <div class="threat-dashboard-actions-panel">
        <div class="threat-dashboard-actions-label">Acciones del módulo</div>
        <div class="threat-main-actions">
        <a href="{{ url_for('threat_model_asset_view') }}"
           class="btn btn-primary rounded-pill px-4">
          🧭 Matriz MITRE ATT&CK
        </a>

        <a href="{{ url_for('threat_model_dashboard', herramienta='active_directory') }}"
           class="btn btn-outline-dark rounded-pill px-4">
          <i class="bi bi-person-lock"></i> Hallazgos Active Directory
        </a>

        <a href="{{ url_for('threat_model_dashboard', herramienta='firewall_governance') }}"
           class="btn btn-outline-primary rounded-pill px-4">
          <i class="bi bi-shield-lock"></i> Hallazgos Gobierno de Firewall
        </a>

        <a href="{{ url_for('threat_model_unmapped_view') }}"
           class="btn btn-outline-danger rounded-pill px-4">
          🧩 Ver No Mapeados
        </a>

        <a href="{{ url_for('threat_model_unmapped_complementary_view') }}"
           class="btn btn-outline-success rounded-pill px-4">
          🧠 Clasificación Complementaria
        </a>

        {% if not read_only %}
          <a href="{{ url_for('threat_model_export_navigator', activo=filtro_activo) }}"
             class="btn btn-outline-primary rounded-pill px-4">
            ⬇️ Exportar Navigator JSON
          </a>
        {% else %}
          <button type="button"
                  class="btn btn-secondary rounded-pill px-4"
                  disabled
                  title="Auditor: solo lectura. No puede exportar Navigator JSON.">
            ⬇️ Exportar Navigator JSON
          </button>
        {% endif %}

        {% if user.role != 'auditor' %}
          <a href="{{ url_for('threat_model_nessus_import') }}"
             class="btn btn-warning rounded-pill px-4">
            📥 Importar Nessus
          </a>
        {% endif %}
        </div>
      </div>

      <form method="get" class="row g-3 mb-3" id="threatFiltroForm">
        <div class="col-md-3">
          <label class="form-label">Activo</label>
          <input type="text"
                 name="activo"
                 class="form-control"
                 value="{{ filtro_activo }}"
                 placeholder="Servidor, portal, dominio, IP...">
        </div>

        <div class="col-md-2">
          <label class="form-label">Herramienta</label>
          <select name="herramienta" class="form-select">
            <option value="">-- Todas --</option>
            {% for op in ['active_directory','firewall_governance','registro_vulnerabilidades','nikto','nessus','nuclei','nmap','testssl','owasp_zap','zap'] %}
              <option value="{{ op }}" {% if filtro_herramienta == op %}selected{% endif %}>{{ op|upper }}</option>
            {% endfor %}
          </select>
        </div>

        <div class="col-md-2">
          <label class="form-label">Severidad</label>
          <select name="severidad" class="form-select">
            <option value="">-- Todas --</option>
            {% for op in ['Crítica', 'Alta', 'Media', 'Baja'] %}
              <option value="{{ op }}" {% if filtro_severidad == op %}selected{% endif %}>{{ op }}</option>
            {% endfor %}
          </select>
        </div>

        <div class="col-md-3">
          <label class="form-label">Técnica MITRE</label>
          <select name="tecnica" class="form-select">
            <option value="">-- Todas --</option>
            {% for tid, tname in tecnicas_disponibles %}
              <option value="{{ tid }}" {% if filtro_tecnica == tid %}selected{% endif %}>
                {{ tid }} - {{ tname }}
              </option>
            {% endfor %}
          </select>
        </div>

        <div class="col-md-2">
          <label class="form-label d-block">&nbsp;</label>
          <div class="tm-filter-actions">
            <button class="btn btn-primary rounded-pill px-3" type="submit">
              Filtrar
            </button>

            <a href="{{ url_for('threat_model_dashboard') }}"
               class="btn btn-outline-secondary rounded-pill px-3">
              Limpiar
            </a>

            {% if not read_only %}
              <button type="button"
                      class="btn btn-danger rounded-pill px-3"
                      onclick="eliminarThreatModelFiltrados()">
                Eliminar filtrados
              </button>
            {% else %}
              <button type="button"
                      class="btn btn-secondary rounded-pill px-3"
                      disabled
                      title="Auditor: solo lectura">
                Eliminar filtrados
              </button>
            {% endif %}
          </div>
        </div>
      </form>

      <form method="post"
            id="threatDeleteFiltradosForm"
            action="{{ url_for('threat_model_delete_filtrados') }}"
            style="display:none;">
        <input type="hidden" name="activo" value="{{ filtro_activo }}">
        <input type="hidden" name="herramienta" value="{{ filtro_herramienta }}">
        <input type="hidden" name="severidad" value="{{ filtro_severidad }}">
        <input type="hidden" name="tecnica" value="{{ filtro_tecnica }}">
      </form>

      <div class="row g-3 mb-3">
        <div class="col-md-4">
          <div class="metric-box">
            <div class="metric-label">Hallazgos mapeados</div>
            <div class="metric-value">{{ mapped_count }}</div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="metric-box">
            <div class="metric-label">Hallazgos no mapeados</div>
            <div class="metric-value">{{ unmapped_count }}</div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="metric-box">
            <div class="metric-label">Cobertura MITRE</div>
            <div class="metric-value">{{ coverage_pct }}%</div>
          </div>
        </div>
      </div>

      <div class="soft-table-wrap">
        <div class="table-responsive px-3 pb-3 pt-3">
          <table class="table table-hover align-middle soft-table mb-0">
            <thead>
              <tr>
                <th>ID</th>
                <th>Activo</th>
                <th>Herramienta</th>
                <th>Vulnerabilidad</th>
                <th>Severidad</th>
                <th>Técnicas MITRE</th>
                <th>Acciones</th>
              </tr>
            </thead>

            <tbody>
              {% for it in items %}
              <tr>
                <td class="text-center fw-bold">{{ it.id }}</td>
                <td>{{ it.activo }}</td>
                <td class="text-center">{% if it.herramienta == 'active_directory' %}<span class="badge bg-dark">ACTIVE DIRECTORY</span>{% elif it.herramienta == 'firewall_governance' %}<span class="badge bg-primary">GOBIERNO FIREWALL</span>{% else %}{{ it.herramienta|upper }}{% endif %}</td>
                <td class="small">{{ it.vulnerabilidad }}</td>
                <td class="text-center">{{ badge_severidad_html(it.severidad) }}</td>

                <td class="small">
                  {% if it.tecnicas %}
                    {% for t in it.tecnicas %}
                      <div>
                        <b>{{ t.mitre_technique_id }}</b> - {{ t.mitre_technique_name }}
                      </div>
                    {% endfor %}
                  {% else %}
                    <span class="badge bg-warning text-dark">Pendiente de mapeo MITRE</span>
                  {% endif %}
                </td>

                <td class="text-center">
                  <div class="tm-actions-wrap">
                    {% set ad_finding_id = tm_ad_finding_id(it) %}
                    {% if ad_finding_id %}
                      <a href="{{ url_for('adgov.finding_detail', finding_id=ad_finding_id) }}"
                         class="btn btn-outline-dark btn-sm rounded-pill px-3">
                        Ver hallazgo AD
                      </a>
                    {% endif %}
                    {% set firewall_finding_url = tm_firewall_finding_url(it) %}
                    {% if firewall_finding_url %}
                      <a href="{{ firewall_finding_url }}"
                         class="btn btn-outline-primary btn-sm rounded-pill px-3">
                        Ver hallazgo Firewall
                      </a>
                    {% endif %}
                    {% if not read_only %}
                      <a href="{{ url_for('threat_model_delete', id=it.id) }}"
                         class="btn btn-danger btn-sm rounded-pill px-3"
                         onclick="return confirmarEliminarThreatModel();">
                        Eliminar
                      </a>
                    {% else %}
                      <button class="btn btn-secondary btn-sm rounded-pill px-3"
                              disabled
                              title="Auditor: solo lectura">
                        Eliminar
                      </button>
                    {% endif %}
                  </div>
                </td>
              </tr>

              {% else %}
              <tr>
                <td colspan="7" class="text-center text-muted py-4">
                  No hay modelamientos generados.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <style>
      .tm-filter-actions{
        display:flex;
        flex-direction:column;
        gap:7px;
        align-items:stretch;
      }

      .tm-filter-actions .btn{
        width:100%;
        min-height:36px;
        font-size:.68rem;
        font-weight:900;
      }

      /* Presentación uniforme del módulo, igual al orden título > acciones > contenido.
         Las posiciones están en el flujo normal: los botones NO se montan sobre el título. */
      .threat-dashboard-card > .threat-dashboard-heading{
        display:block;
        position:relative;
        z-index:1;
        clear:both;
        width:100%;
        margin-bottom:16px !important;
      }

      .threat-dashboard-card .threat-dashboard-actions-panel{
        display:block;
        position:relative !important;
        inset:auto !important;
        float:none !important;
        transform:none !important;
        clear:both;
        width:100%;
        margin:0 0 20px 0;
        padding:14px 16px 16px;
        background:#f8fbff;
        border:1px solid #d9eaff;
        border-radius:14px;
      }

      .threat-dashboard-card .threat-dashboard-actions-label{
        color:#0b4a8f;
        font-size:.79rem;
        font-weight:900;
        margin-bottom:12px;
      }

      .threat-dashboard-card .threat-main-actions{
        display:grid !important;
        grid-template-columns:repeat(3,minmax(0,1fr));
        align-items:stretch;
        justify-items:stretch;
        gap:10px;
        position:static !important;
        float:none !important;
        transform:none !important;
        width:100%;
      }

      .threat-dashboard-card .threat-main-actions .btn{
        display:flex;
        align-items:center;
        justify-content:center;
        width:100%;
        min-width:0;
        min-height:42px;
        margin:0;
        padding:9px 12px !important;
        white-space:normal;
        text-align:center;
        overflow-wrap:anywhere;
        font-weight:900;
        font-size:.79rem;
        box-shadow:0 8px 18px rgba(0,0,0,.10);
      }

      @media (max-width:1100px){
        .threat-dashboard-card .threat-main-actions{
          grid-template-columns:repeat(2,minmax(0,1fr));
        }
      }

      @media (max-width:650px){
        .threat-dashboard-card .threat-main-actions{
          grid-template-columns:minmax(0,1fr);
        }
        .threat-dashboard-card .threat-dashboard-actions-panel{
          padding:12px;
        }
      }

      .tm-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
      }

      .tm-actions-wrap .btn{
        min-width:120px;
        font-size:.74rem;
        font-weight:900;
      }

      @media (max-width:768px){
        .tm-filter-actions .btn,
        .tm-actions-wrap .btn,
        .threat-main-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      function confirmarEliminarThreatModel(){
        if(typeof hideLoader === 'function'){
          hideLoader();
        }

        return confirm(
          '¿Está seguro de eliminar este registro de modelamiento de amenazas?\\n\\n' +
          'También se eliminarán sus técnicas MITRE asociadas.\\n' +
          'Esta acción no se puede deshacer.'
        );
      }

      function eliminarThreatModelFiltrados(){
        const total = {{ items|length }};

        if(total <= 0){
          alert('No hay registros para eliminar con los filtros aplicados.');
          return false;
        }

        const activo = "{{ filtro_activo }}";
        const herramienta = "{{ filtro_herramienta }}";
        const severidad = "{{ filtro_severidad }}";
        const tecnica = "{{ filtro_tecnica }}";

        let mensaje = '¿Está seguro de eliminar los registros filtrados de modelamiento de amenazas?\\n\\n';
        mensaje += 'Total registros a eliminar: ' + total + '\\n';

        if(activo){ mensaje += 'Activo contiene: ' + activo + '\\n'; }
        if(herramienta){ mensaje += 'Herramienta: ' + herramienta + '\\n'; }
        if(severidad){ mensaje += 'Severidad: ' + severidad + '\\n'; }
        if(tecnica){ mensaje += 'Técnica MITRE: ' + tecnica + '\\n'; }

        if(!activo && !herramienta && !severidad && !tecnica){
          mensaje += '\\nADVERTENCIA: No hay filtros aplicados. Se eliminarán TODOS los registros de modelamiento de amenazas.\\n';
        }

        mensaje += '\\nTambién se eliminarán las técnicas MITRE asociadas.\\n';
        mensaje += 'Esta acción no se puede deshacer.';

        if(confirm(mensaje)){
          const form = document.getElementById('threatDeleteFiltradosForm');
          if(form){ form.submit(); }
        }

        return false;
      }
    </script>
    """

    return vuln_scan_shell(
        "Modelamiento de Amenazas",
        render_template_string(
            body,
            items=items,
            filtro_activo=filtro_activo,
            filtro_herramienta=filtro_herramienta,
            filtro_severidad=filtro_severidad,
            filtro_tecnica=filtro_tecnica,
            tecnicas_disponibles=tecnicas_disponibles,
            user=user,
            read_only=read_only,
            mapped_count=mapped_count,
            unmapped_count=unmapped_count,
            coverage_pct=coverage_pct,
            badge_severidad_html=badge_severidad_html,
            tm_ad_finding_id=tm_ad_finding_id,
            tm_firewall_finding_url=tm_firewall_finding_url
        )
    )


# =================================
# Vista No Mapeados Mittre & Attack 
# =================================

@app.route('/modelamiento_amenazas/no_mapeados')
@login_required
def threat_model_unmapped_view():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Modelamiento de Amenazas"):
        flash("No tiene permiso para acceder a los hallazgos no mapeados.", "danger")
        return redirect(url_for('menu'))

    read_only = True if user.role == 'auditor' else False

    filtro_herramienta = (request.args.get('herramienta') or '').strip()
    filtro_severidad = (request.args.get('severidad') or '').strip()
    filtro_texto = (request.args.get('texto') or '').strip()

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

    items = q.order_by(ThreatModelUnmapped.id.desc()).all()

    body = """
    <div class="glass-card p-4 mt-2">

      <div class="unmapped-topbar">
        <div>
          <div class="section-title mb-1">🧩 Hallazgos no mapeados MITRE</div>
          <div class="text-muted small">
            Consulta y gestión de hallazgos técnicos que aún no fueron asociados a tácticas o técnicas MITRE ATT&CK.
          </div>
        </div>

        <div class="unmapped-extra-actions">
          {% if not read_only %}
            <form method="post"
                  action="{{ url_for('threat_model_unmapped_classify') }}"
                  class="d-inline">
              <input type="hidden" name="herramienta" value="{{ filtro_herramienta }}">
              <input type="hidden" name="severidad" value="{{ filtro_severidad }}">
              <input type="hidden" name="texto" value="{{ filtro_texto }}">

              <button type="submit"
                      class="btn btn-success rounded-pill px-4"
                      onclick="return confirmarClasificacionComplementaria();">
                🧠 Clasificar No Mapeados
              </button>
            </form>
          {% else %}
            <button type="button"
                    class="btn btn-secondary rounded-pill px-4"
                    disabled
                    title="Auditor: solo lectura. No puede clasificar hallazgos.">
              🧠 Clasificar No Mapeados
            </button>
          {% endif %}

          <a href="{{ url_for('threat_model_unmapped_complementary_view') }}"
             class="btn btn-outline-success rounded-pill px-4">
            Ver Clasificación
          </a>

          <a href="{{ url_for('threat_model_dashboard') }}"
             class="btn btn-outline-primary rounded-pill px-4 unmapped-back-btn">
            ← Volver al Dashboard
          </a>
        </div>
      </div>

      <form method="get" class="row g-3 mb-3" id="unmappedFiltroForm">
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

            <a href="{{ url_for('threat_model_unmapped_view') }}"
               class="btn btn-outline-secondary rounded-pill px-3">
              Limpiar
            </a>

            {% if not read_only %}
              <button type="button"
                      class="btn btn-danger rounded-pill px-3"
                      onclick="eliminarUnmappedFiltrados()">
                Eliminar filtrados
              </button>
            {% else %}
              <button type="button"
                      class="btn btn-secondary rounded-pill px-3"
                      disabled
                      title="Auditor: solo lectura">
                Eliminar filtrados
              </button>
            {% endif %}
          </div>
        </div>
      </form>

      <form method="post"
            id="unmappedDeleteFiltradosForm"
            action="{{ url_for('threat_model_unmapped_delete_filtrados') }}"
            style="display:none;">
        <input type="hidden" name="herramienta" value="{{ filtro_herramienta }}">
        <input type="hidden" name="severidad" value="{{ filtro_severidad }}">
        <input type="hidden" name="texto" value="{{ filtro_texto }}">
      </form>

      <div class="soft-table-wrap">
        <div class="table-responsive px-3 pb-3 pt-3">
          <table class="table table-hover align-middle soft-table mb-0">
            <thead>
              <tr>
                <th>ID</th>
                <th>Herramienta</th>
                <th>Severidad</th>
                <th>Título</th>
                <th>Descripción</th>
                <th>Evidencia</th>
                <th>Acciones</th>
              </tr>
            </thead>

            <tbody>
              {% for it in items %}
              <tr>
                <td class="text-center fw-bold">{{ it.id }}</td>
                <td class="text-center">{{ it.herramienta|upper }}</td>
                <td class="text-center">{{ badge_severidad_html(it.severidad) }}</td>
                <td class="small">{{ it.titulo }}</td>
                <td class="small">{{ it.descripcion or '—' }}</td>
                <td class="small">{{ it.evidencia or '—' }}</td>

                <td class="text-center">
                  {% if not read_only %}
                    <a href="{{ url_for('threat_model_unmapped_delete', id=it.id) }}"
                       class="btn btn-danger btn-sm rounded-pill px-3"
                       onclick="return confirmarEliminarUnmapped();">
                      Eliminar
                    </a>
                  {% else %}
                    <button class="btn btn-secondary btn-sm rounded-pill px-3"
                            disabled
                            title="Auditor: solo lectura">
                      Eliminar
                    </button>
                  {% endif %}
                </td>
              </tr>

              {% else %}
              <tr>
                <td colspan="7" class="text-center text-muted py-4">
                  No hay hallazgos no mapeados.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <style>
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

      .unmapped-extra-actions .btn,
      .unmapped-extra-actions form .btn{
        font-size:.82rem;
        font-weight:900;
        min-height:32px;
        display:inline-flex;
        align-items:center;
        justify-content:center;
        white-space:nowrap;
        box-shadow:0 8px 18px rgba(37,99,235,.12);
      }

      .unmapped-back-btn:hover{
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
      }

      @media (max-width:768px){
        .unmapped-topbar{
          align-items:stretch;
        }

        .unmapped-extra-actions,
        .unmapped-extra-actions .btn,
        .unmapped-extra-actions form,
        .unmapped-extra-actions form .btn,
        .unmapped-filter-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      function confirmarClasificacionComplementaria(){
        if(typeof hideLoader === 'function'){
          hideLoader();
        }

        return confirm(
          '¿Desea clasificar los hallazgos no mapeados con OWASP, CWE, CAPEC, ISO 27001 y NIST CSF?\\n\\n' +
          'Se tomarán en cuenta los filtros actuales de herramienta, severidad y texto.'
        );
      }

      function confirmarEliminarUnmapped(){
        if(typeof hideLoader === 'function'){
          hideLoader();
        }

        return confirm(
          '¿Está seguro de eliminar este hallazgo no mapeado?\\n\\n' +
          'Esta acción no se puede deshacer.'
        );
      }

      function eliminarUnmappedFiltrados(){
        const total = {{ items|length }};

        if(total <= 0){
          alert('No hay hallazgos no mapeados para eliminar con los filtros aplicados.');
          return false;
        }

        const herramienta = "{{ filtro_herramienta }}";
        const severidad = "{{ filtro_severidad }}";
        const texto = "{{ filtro_texto }}";

        let mensaje = '¿Está seguro de eliminar los hallazgos no mapeados filtrados?\\n\\n';
        mensaje += 'Total registros a eliminar: ' + total + '\\n';

        if(herramienta){ mensaje += 'Herramienta: ' + herramienta + '\\n'; }
        if(severidad){ mensaje += 'Severidad: ' + severidad + '\\n'; }
        if(texto){ mensaje += 'Texto contiene: ' + texto + '\\n'; }

        if(!herramienta && !severidad && !texto){
          mensaje += '\\nADVERTENCIA: No hay filtros aplicados. Se eliminarán TODOS los hallazgos no mapeados.\\n';
        }

        mensaje += '\\nEsta acción no se puede deshacer.';

        if(confirm(mensaje)){
          const form = document.getElementById('unmappedDeleteFiltradosForm');
          if(form){ form.submit(); }
        }

        return false;
      }
    </script>
    """

    return vuln_scan_shell(
        "No mapeados MITRE",
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

# =====================
# Vista Mittre & Attack 
# =====================

@app.route('/modelamiento_amenazas/matriz_mitre')
@login_required
def threat_model_asset_view():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Modelamiento de Amenazas"):
        flash("No tiene permiso para acceder al modelamiento de amenazas.", "danger")
        return redirect(url_for('menu'))

    read_only = True if user.role == 'auditor' else False

    asegurar_sincronizacion_vulnerabilidades_modelamiento()
    asegurar_sincronizacion_active_directory_modelamiento()
    asegurar_sincronizacion_firewall_modelamiento()

    activo = (request.args.get('activo') or '').strip()

    q = ThreatModelEntry.query.options(selectinload(ThreatModelEntry.tecnicas))

    if activo:
        q = q.filter(ThreatModelEntry.activo.ilike(f"%{activo}%"))

    entries = q.order_by(ThreatModelEntry.id.desc()).all()
    matrix = build_attack_matrix_view(entries)

    total_tecnicas = sum(len(list(entry.tecnicas or [])) for entry in entries)
    pendientes_mitre = len(matrix.get(MITRE_PENDING_TACTIC, []))
    tacticas_con_hallazgos = sum(
        1 for tactic in ATTACK_TACTIC_ORDER if matrix.get(tactic)
    )
    total_tacticas_attack = len(ATTACK_TACTIC_ORDER)
    vulnerabilidades_representadas = len({
        int(entry.vulnerabilidad_registro_id)
        for entry in entries
        if entry.vulnerabilidad_registro_id is not None
    })

    scores = []
    for tactic, items in matrix.items():
        if tactic == MITRE_PENDING_TACTIC:
            continue
        for item in items:
            try:
                scores.append(int(item.get("score") or 0))
            except Exception:
                pass

    score_maximo = max(scores) if scores else 0

    body = """
    <div class="glass-card p-4 mt-2 mitre-shell">

      <div class="mitre-topbar">
        <div>
          <div class="section-title mb-1">🧭 Matriz MITRE ATT&CK</div>
          <div class="small text-muted">
            Visualización completa por táctica. Todas las vulnerabilidades registradas aparecen en la matriz; las que aún no tengan una correspondencia confiable se muestran en la columna Pendiente de mapeo MITRE.
          </div>
        </div>

        <div class="mitre-actions">
          <a href="{{ url_for('threat_model_dashboard') }}"
             class="btn btn-outline-secondary rounded-pill px-4">
            ⬅ Volver
          </a>

          {% if not read_only %}
            <a href="{{ url_for('threat_model_export_navigator') }}{% if activo %}?activo={{ activo|urlencode }}{% endif %}"
               class="btn btn-success rounded-pill px-4 no-progress"
               data-no-progress="true"
               download
               onclick="if(typeof hideSGSIProgress === 'function'){ hideSGSIProgress(); } if(typeof hideLoader === 'function'){ hideLoader(); }">
              ⬇ Exportar Navigator JSON
            </a>
          {% else %}
            <button type="button"
                    class="btn btn-secondary rounded-pill px-4 no-progress"
                    data-no-progress="true"
                    disabled
                    title="Auditor: solo lectura. No puede exportar Navigator JSON.">
              ⬇ Exportar Navigator JSON
            </button>
          {% endif %}
        </div>
      </div>

      <div class="mitre-summary-grid">
        <div class="mitre-summary-card">
          <div class="mitre-summary-label">Tácticas con hallazgos</div>
          <div class="mitre-summary-value">{{ tacticas_con_hallazgos }}</div>
          <div class="mitre-summary-help">de {{ total_tacticas_attack }} tácticas ATT&CK</div>
        </div>

        <div class="mitre-summary-card">
          <div class="mitre-summary-label">Técnicas identificadas</div>
          <div class="mitre-summary-value">{{ total_tecnicas }}</div>
          <div class="mitre-summary-help">mapeadas automáticamente</div>
        </div>

        <div class="mitre-summary-card">
          <div class="mitre-summary-label">Vulnerabilidades visibles</div>
          <div class="mitre-summary-value">{{ vulnerabilidades_representadas }}</div>
          <div class="mitre-summary-help">sincronizadas desde el registro</div>
        </div>

        <div class="mitre-summary-card">
          <div class="mitre-summary-label">Pendientes de mapeo</div>
          <div class="mitre-summary-value">{{ pendientes_mitre }}</div>
          <div class="mitre-summary-help">visibles sin asignación ATT&CK falsa</div>
        </div>

        <div class="mitre-summary-card">
          <div class="mitre-summary-label">Score máximo</div>
          <div class="mitre-summary-value">{{ score_maximo }}</div>
          <div class="mitre-summary-help">prioridad técnica más alta</div>
        </div>
      </div>

      <form method="get" class="mitre-filter-card row g-3 mb-3">
        <div class="col-lg-9 col-md-8">
          <label class="form-label">Activo</label>
          <input type="text"
                 name="activo"
                 value="{{ activo }}"
                 class="form-control"
                 placeholder="Servidor, dominio, web server...">
        </div>

        <div class="col-lg-3 col-md-4">
          <label class="form-label d-block">&nbsp;</label>
          <button class="btn btn-primary rounded-pill px-4 w-100">
            Aplicar filtro
          </button>
        </div>
      </form>

      <div class="mitre-legend">
        <span><i class="mitre-dot mitre-low"></i>Bajo</span>
        <span><i class="mitre-dot mitre-medium"></i>Medio</span>
        <span><i class="mitre-dot mitre-high"></i>Alto</span>
        <span><i class="mitre-dot mitre-critical"></i>Crítico</span>
        <span><i class="mitre-dot mitre-pending"></i>Pendiente de mapeo</span>
        <span class="ms-auto text-muted small">Tip: desplázate horizontalmente para ver todas las tácticas.</span>
      </div>

      <div class="mitre-board-wrap">
        <div class="mitre-board">
          {% for tactic, items in matrix.items() %}
            <div class="mitre-tactic-col {% if not items %}mitre-tactic-empty{% endif %} {% if tactic == pending_tactic_label %}mitre-tactic-pending{% endif %}">
              <div class="mitre-tactic-head">
                <div class="mitre-tactic-title">{{ tactic }}</div>
                <span class="mitre-tactic-count">{{ items|length }}</span>
              </div>

              <div class="mitre-tech-list">
                {% if items %}
                  {% for item in items %}
                    {% set score = item.score or 0 %}
                    {% if item.pending %}
                      {% set sev_class = 'pending' %}
                    {% elif score >= 90 %}
                      {% set sev_class = 'critical' %}
                    {% elif score >= 70 %}
                      {% set sev_class = 'high' %}
                    {% elif score >= 40 %}
                      {% set sev_class = 'medium' %}
                    {% else %}
                      {% set sev_class = 'low' %}
                    {% endif %}

                    <div class="mitre-tech-card {{ sev_class }}">
                      <div class="mitre-tech-id">{{ item.technique_id }}</div>
                      <div class="mitre-tech-name">{{ item.technique_name }}</div>

                      <div class="mitre-tech-meta">
                        <span>{{ item.tool|upper }}</span>
                        <span>{{ item.severity or '—' }}</span>
                        <span>Score {{ item.score or 0 }}</span>
                      </div>

                      <div class="mitre-tech-vuln">
                        {{ item.vulnerability }}
                      </div>

                      {% if item.impacto %}
                        <details class="mitre-impact">
                          <summary>Ver impacto</summary>
                          <div>{{ item.impacto }}</div>
                        </details>
                      {% endif %}

                      {% if item.pending and item.rationale %}
                        <div class="mitre-pending-note">{{ item.rationale }}</div>
                      {% endif %}
                    </div>
                  {% endfor %}
                {% else %}
                  <div class="mitre-empty-state">
                    Sin técnicas mapeadas
                  </div>
                {% endif %}
              </div>
            </div>
          {% endfor %}
        </div>
      </div>

    </div>

    <style>
      .mitre-shell{
        overflow:hidden;
      }

      .mitre-topbar{
        display:flex;
        align-items:flex-start;
        justify-content:space-between;
        gap:14px;
        flex-wrap:wrap;
        margin-bottom:14px;
      }

      .mitre-actions{
        display:flex;
        flex-wrap:wrap;
        justify-content:flex-end;
        gap:6px;
      }

      .mitre-actions .btn{
        font-weight:900;
        box-shadow:0 8px 18px rgba(0,0,0,.10);
      }

      .mitre-actions button[disabled]{
        cursor:not-allowed;
        opacity:.70;
      }

      .mitre-summary-grid{
        display:grid;
        grid-template-columns:repeat(5,minmax(0,1fr));
        gap:12px;
        margin-bottom:14px;
      }

      .mitre-summary-card{
        background:rgba(255,255,255,.92);
        border:1px solid rgba(63,134,214,.22);
        border-radius:18px;
        padding:14px 16px;
        box-shadow:0 10px 24px rgba(0,0,0,.10);
      }

      .mitre-summary-label{
        font-size:.78rem;
        font-weight:900;
        color:#5c6b7d;
        text-transform:uppercase;
        letter-spacing:.04em;
      }

      .mitre-summary-value{
        font-size:1.85rem;
        font-weight:950;
        color:#1d4f8f;
        line-height:1;
        margin-top:6px;
      }

      .mitre-summary-help{
        color:#7c8898;
        font-size:.82rem;
        margin-top:5px;
      }

      .mitre-filter-card{
        background:rgba(248,251,255,.94);
        border:1px solid rgba(63,134,214,.18);
        border-radius:18px;
        padding:12px 12px 14px 12px;
        box-shadow:0 8px 20px rgba(0,0,0,.08);
      }

      .mitre-legend{
        display:flex;
        align-items:center;
        gap:14px;
        flex-wrap:wrap;
        background:rgba(255,255,255,.86);
        border:1px solid rgba(0,0,0,.06);
        border-radius:16px;
        padding:10px 14px;
        margin-bottom:12px;
        font-weight:800;
        font-size:.82rem;
      }

      .mitre-dot{
        display:inline-block;
        width:11px;
        height:11px;
        border-radius:999px;
        margin-right:6px;
        vertical-align:middle;
      }

      .mitre-low{ background:#15803d; }
      .mitre-medium{ background:#ca8a04; }
      .mitre-high{ background:#ea580c; }
      .mitre-critical{ background:#b91c1c; }
      .mitre-pending{ background:#64748b; }

      .mitre-board-wrap{
        width:100%;
        overflow-x:auto;
        overflow-y:hidden;
        padding-bottom:10px;
        border-radius:20px;
        background:linear-gradient(180deg,rgba(255,255,255,.70),rgba(245,248,252,.78));
        border:1px solid rgba(63,134,214,.18);
        box-shadow:inset 0 0 0 1px rgba(255,255,255,.55);
      }

      .mitre-board{
        display:grid;
        grid-template-columns:repeat(15, minmax(245px, 1fr));
        gap:12px;
        min-width:3775px;
        padding:8px 7px;
      }

      .mitre-tactic-col{
        background:rgba(248,252,255,.96);
        border:1px solid rgba(31,73,125,.13);
        border-radius:18px;
        box-shadow:0 10px 24px rgba(0,0,0,.10);
        overflow:hidden;
        min-height:420px;
      }

      .mitre-tactic-empty{
        opacity:.78;
      }

      .mitre-tactic-pending{
        border-color:rgba(100,116,139,.38);
      }

      .mitre-tactic-pending .mitre-tactic-head{
        background:linear-gradient(135deg,#475569 0%,#64748b 100%);
      }

      .mitre-tactic-head{
        position:sticky;
        top:0;
        z-index:2;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:6px;
        padding:12px 12px;
        background:linear-gradient(135deg,#243b53 0%,#304f72 100%);
        color:#fff;
      }

      .mitre-tactic-title{
        font-size:.84rem;
        font-weight:950;
        line-height:1.15;
      }

      .mitre-tactic-count{
        min-width:28px;
        height:24px;
        display:inline-flex;
        align-items:center;
        justify-content:center;
        border-radius:999px;
        background:#3f86d6;
        color:#fff;
        font-weight:950;
        font-size:.78rem;
      }

      .mitre-tech-list{
        padding:10px;
        max-height:680px;
        overflow-y:auto;
      }

      .mitre-tech-card{
        position:relative;
        background:#fff;
        border:1px solid rgba(0,0,0,.08);
        border-left:6px solid #15803d;
        border-radius:16px;
        padding:10px 10px 11px 10px;
        margin-bottom:10px;
        box-shadow:0 8px 18px rgba(0,0,0,.08);
      }

      .mitre-tech-card.low{ border-left-color:#15803d; }
      .mitre-tech-card.medium{ border-left-color:#ca8a04; }
      .mitre-tech-card.high{ border-left-color:#ea580c; }
      .mitre-tech-card.critical{ border-left-color:#b91c1c; }
      .mitre-tech-card.pending{ border-left-color:#64748b; background:#f8fafc; }

      .mitre-tech-id{
        display:inline-flex;
        align-items:center;
        justify-content:center;
        font-size:.68rem;
        font-weight:950;
        color:#1d4f8f;
        background:#eaf3ff;
        border:1px solid rgba(63,134,214,.24);
        border-radius:999px;
        padding:2px 9px;
        margin-bottom:6px;
      }

      .mitre-tech-name{
        font-size:.83rem;
        font-weight:950;
        color:#24364b;
        line-height:1.2;
        margin-bottom:6px;
      }

      .mitre-tech-meta{
        display:flex;
        flex-wrap:wrap;
        gap:5px;
        margin-bottom:7px;
      }

      .mitre-tech-meta span{
        background:#f1f5f9;
        border:1px solid rgba(0,0,0,.05);
        color:#536274;
        border-radius:999px;
        padding:2px 7px;
        font-size:.68rem;
        font-weight:900;
      }

      .mitre-tech-vuln{
        font-size:.74rem;
        color:#5d6877;
        line-height:1.25;
        max-height:54px;
        overflow:auto;
      }

      .mitre-impact{
        margin-top:8px;
        font-size:.72rem;
        color:#536274;
      }

      .mitre-impact summary{
        cursor:pointer;
        font-weight:900;
        color:#1d4f8f;
      }

      .mitre-impact div{
        margin-top:6px;
        background:#f8fafc;
        border-radius:12px;
        padding:8px;
        line-height:1.25;
      }

      .mitre-pending-note{
        margin-top:8px;
        padding:8px;
        border-radius:12px;
        background:#eef2f7;
        color:#475569;
        font-size:.70rem;
        font-weight:750;
        line-height:1.3;
      }

      .mitre-empty-state{
        min-height:120px;
        border:1px dashed rgba(63,134,214,.32);
        border-radius:16px;
        display:flex;
        align-items:center;
        justify-content:center;
        text-align:center;
        color:#8a96a8;
        background:#f8fbff;
        font-size:.8rem;
        font-weight:850;
        padding:12px;
      }

      @media (max-width:992px){
        .mitre-summary-grid{
          grid-template-columns:1fr;
        }

        .mitre-actions{
          width:100%;
          justify-content:flex-start;
        }

        .mitre-actions .btn{
          width:100%;
        }

        .mitre-board{
          grid-template-columns:repeat(15, minmax(230px, 1fr));
          min-width:3575px;
        }
      }
    </style>
    """

    return vuln_scan_shell(
        "Matriz MITRE ATT&CK",
        render_template_string(
            body,
            activo=activo,
            matrix=matrix,
            total_tecnicas=total_tecnicas,
            pendientes_mitre=pendientes_mitre,
            vulnerabilidades_representadas=vulnerabilidades_representadas,
            tacticas_con_hallazgos=tacticas_con_hallazgos,
            total_tacticas_attack=total_tacticas_attack,
            pending_tactic_label=MITRE_PENDING_TACTIC,
            score_maximo=score_maximo,
            read_only=read_only,
            user=user
        )
    )


# =====================
# Export Navigator JSON
# =====================

@app.route('/modelamiento_amenazas/navigator.json')
@app.route('/vulnerabilidades/threat_model/navigator.json')
@login_required
def threat_model_export_navigator():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede exportar Navigator JSON.", "danger")
        return redirect(url_for('threat_model_dashboard'))

    if user.role != 'admin' and not verificar_permiso(user, "Modelamiento de Amenazas"):
        flash("No tiene permiso para exportar la capa Navigator.", "danger")
        return redirect(url_for('menu'))

    asegurar_sincronizacion_vulnerabilidades_modelamiento()
    asegurar_sincronizacion_active_directory_modelamiento()
    asegurar_sincronizacion_firewall_modelamiento()

    activo = (request.args.get('activo') or '').strip()

    q = ThreatModelEntry.query.options(selectinload(ThreatModelEntry.tecnicas))

    if activo:
        q = q.filter(ThreatModelEntry.activo.ilike(f"%{activo}%"))

    entries = q.order_by(ThreatModelEntry.id.desc()).all()

    layer = build_attack_layer_from_entries(entries, asset_name=activo or "Activos")

    bio = BytesIO()
    bio.write(json.dumps(layer, ensure_ascii=False, indent=2).encode("utf-8"))
    bio.seek(0)

    safe_name = safe_scan_slug(activo or "activos")

    return send_file(
        bio,
        mimetype="application/json",
        as_attachment=True,
        download_name=f"mitre_attack_navigator_{safe_name}.json"
    )

# ==========================
# Eliminar entrada individual — Modelamiento de Amenazas
# ==========================

@app.route('/modelamiento_amenazas/<int:id>/delete')
@app.route('/vulnerabilidades/threat_model/<int:id>/delete')
@login_required
def threat_model_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros.", "danger")
        return redirect(url_for('threat_model_dashboard'))

    if user.role != 'admin' and not verificar_permiso(user, "Modelamiento de Amenazas"):
        flash("No tiene permiso para eliminar registros de modelamiento de amenazas.", "danger")
        return redirect(url_for('threat_model_dashboard'))

    db.session.rollback()

    item = ThreatModelEntry.query.get_or_404(id)

    try:
        if existe_vulnerabilidad_asociada_a_threat_model(item):
            flash(
                "No se puede eliminar este registro de modelamiento de amenazas porque existe una vulnerabilidad asociada. "
                "Primero elimine la vulnerabilidad desde la matriz de vulnerabilidades.",
                "warning"
            )
            return redirect(url_for('threat_model_dashboard'))

        db.session.delete(item)
        db.session.commit()
        flash("Registro de modelamiento de amenazas eliminado correctamente.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"No fue posible eliminar el registro: {str(e)}", "danger")

    return redirect(url_for('threat_model_dashboard'))

# ==========================
# Eliminar por filtros — Modelamiento de Amenazas
# ==========================

@app.route('/modelamiento_amenazas/delete_filtrados', methods=['POST'])
@app.route('/vulnerabilidades/threat_model/delete_filtrados', methods=['POST'])
@login_required
def threat_model_delete_filtrados():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros.", "danger")
        return redirect(url_for('threat_model_dashboard'))

    if user.role != 'admin' and not verificar_permiso(user, "Modelamiento de Amenazas"):
        flash("No tiene permiso para eliminar registros de modelamiento de amenazas.", "danger")
        return redirect(url_for('threat_model_dashboard'))

    db.session.rollback()

    filtro_activo = (request.form.get('activo') or '').strip()
    filtro_herramienta = (request.form.get('herramienta') or '').strip()
    filtro_severidad = (request.form.get('severidad') or '').strip()
    filtro_tecnica = (request.form.get('tecnica') or '').strip()

    q = ThreatModelEntry.query

    if filtro_activo:
        q = q.filter(ThreatModelEntry.activo.ilike(f"%{filtro_activo}%"))

    if filtro_herramienta:
        q = q.filter(ThreatModelEntry.herramienta == filtro_herramienta)

    if filtro_severidad:
        q = q.filter(ThreatModelEntry.severidad == filtro_severidad)

    if filtro_tecnica:
        q = q.join(ThreatModelTechnique).filter(
            ThreatModelTechnique.mitre_technique_id == filtro_tecnica
        )

    registros = q.distinct().all()

    if not registros:
        flash("No se encontraron registros para eliminar con los filtros aplicados.", "warning")
        return redirect(url_for(
            'threat_model_dashboard',
            activo=filtro_activo,
            herramienta=filtro_herramienta,
            severidad=filtro_severidad,
            tecnica=filtro_tecnica
        ))

    try:
        eliminables = []
        bloqueados = 0

        for item in registros:
            if existe_vulnerabilidad_asociada_a_threat_model(item):
                bloqueados += 1
            else:
                eliminables.append(item)

        if not eliminables:
            flash(
                "No se eliminó ningún registro de modelamiento porque todos tienen vulnerabilidades asociadas. "
                "Primero elimine las vulnerabilidades desde la matriz de vulnerabilidades.",
                "warning"
            )
            return redirect(url_for(
                'threat_model_dashboard',
                activo=filtro_activo,
                herramienta=filtro_herramienta,
                severidad=filtro_severidad,
                tecnica=filtro_tecnica
            ))

        for item in eliminables:
            db.session.delete(item)

        db.session.commit()

        if bloqueados:
            flash(
                f"Se eliminaron {len(eliminables)} registro(s) de modelamiento sin vulnerabilidad asociada. "
                f"No se eliminaron {bloqueados} porque tienen vulnerabilidades asociadas.",
                "warning"
            )
        else:
            flash(f"Se eliminaron {len(eliminables)} registros de modelamiento de amenazas correctamente.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"No fue posible eliminar los registros filtrados: {str(e)}", "danger")

    return redirect(url_for('threat_model_dashboard'))

# ==========================
# Eliminar individual — No Mapeados MITRE
# ==========================

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

